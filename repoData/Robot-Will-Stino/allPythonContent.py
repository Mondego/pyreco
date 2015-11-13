__FILENAME__ = base
#-*- coding: utf-8 -*-
# stino/base.py

import os
import re

from . import constant
from . import textutil
from . import fileutil
from . import sketch

ino_ext_list = ['.ino', '.pde']
build_folder_name_list = ['cores', 'variants', 'system', 'bootloaders']

class ArduinoInfo:
	def __init__(self):
		self.refresh()
		
	def refresh(self):
		self.version_text = getVersionText()
		self.version = getVersion(self.version_text)
		self.genSketchbook()
		self.genPlatformList()
		self.genKeywordList()

	def getSketchbook(self):
		return self.sketchbook

	def getPlatformList(self):
		return self.platform_list

	def getKeywordList(self):
		return self.keyword_list

	def getKeywordRefDict(self):
		return self.keyword_ref_dict

	def getVersion(self):
		return self.version

	def getVersionText(self):
		return self.version_text

	def genSketchbook(self):
		self.sketchbook = getSketchbook()

	def genPlatformList(self):
		self.platform_list = getPlatformList()

	def genKeywordList(self):
		self.keyword_list = []
		for platform in self.platform_list:
			self.keyword_list += getKeywordListFromPlatform(platform)
		self.keyword_ref_dict = getKeywordRefList(self.keyword_list)

class Platform:
	def __init__(self, name):
		self.name = name
		self.core_folder_list = []
		self.board_list = []
		self.programmer_list = []
		self.example = SketchItem(name)
		self.lib_list = []
		self.h_lib_dict = {}

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getCoreFolderList(self):
		return self.core_folder_list

	def setCoreFolderList(self, folder_list):
		self.core_folder_list = folder_list

	def addCoreFolder(self, core_folder):
		self.core_folder_list.append(core_folder)

	def getBoardList(self):
		return self.board_list

	def addBoardList(self, board_list):
		self.board_list += board_list

	def addBoard(self, board):
		self.board_list.append(board)

	def getProgrammerList(self):
		return self.programmer_list

	def addProgrammerList(self, programmer_list):
		self.programmer_list += programmer_list

	def addProgrammer(self, programmer):
		self.programmer_list.append(programmer)

	def getExample(self):
		return self.example

	def setExample(self, example):
		self.example = example

	def getLibList(self):
		return self.lib_list

	def setLibList(self, lib_list):
		self.lib_list = lib_list

	def getHLibDict(self):
		return self.h_lib_dict

	def setHLibDict(self, h_lib_dict):
		self.h_lib_dict = h_lib_dict

class SketchItem:
	def __init__(self, name):
		self.name = name
		self.folder = ''
		self.children = []

	def hasSubItem(self):
		state = False
		if self.children:
			state = True
		return state

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getFolder(self):
		return self.folder

	def setFolder(self, folder):
		self.folder = folder

	def getSubItemList(self):
		return self.children

	def setSubItemList(self, sub_item_list):
		self.children = sub_item_list

	def addSubItem(self, sub_item):
		self.children.append(sub_item)

	def addSubItemList(self, sub_item_list):
		self.children += sub_item_list

class LibItem:
	def __init__(self, name):
		self.name = name
		self.folder = ''
	
	def hasSubItem(self):
		state = False
		if self.children:
			state = True
		return state

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getFolder(self):
		return self.folder

	def setFolder(self, folder):
		self.folder = folder

class Board:
	def __init__(self, name):
		self.name = name
		self.option_list = []
		self.args = {}
		self.folder = ''

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getArgs(self):
		return self.args

	def setArgs(self, args):
		self.args = args

	def getFolder(self):
		return self.folder

	def setFolder(self, folder):
		self.folder = folder

	def getOptionList(self):
		return self.option_list

	def addOption(self, option):
		self.option_list.append(option)

class BoardOption:
	def __init__(self, name):
		self.name = name
		self.item_list = []

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getItemList(self):
		return self.item_list

	def addItem(self, item):
		self.item_list.append(item)

class BoardOptionItem:
	def __init__(self, name):
		self.name = name
		self.args = {}

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getArgs(self):
		return self.args

	def setArgs(self, args):
		self.args = args

class Programmer:
	def __init__(self, name):
		self.name = name
		self.args = {}

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getArgs(self):
		return self.args

	def setArgs(self, args):
		self.args = args

class Keyword:
	def __init__(self, name):
		self.name = name
		self.type = ''
		self.ref = ''

	def getName(self):
		return self.name

	def getType(self):
		return self.type

	def getRef(self):
		return self.ref

	def setName(self, name):
		self.name = name

	def setType(self, keyword_type):
		self.type = keyword_type

	def setRef(self, ref):
		self.ref = ref

def getRealArduinoPath(folder):
	if constant.sys_platform == 'osx':
		folder = os.path.join(folder, 'Contents/Resources/Java')
	return folder

def isArduinoFolder(folder):
	state = False
	if folder and os.path.isdir(folder):
		folder = getRealArduinoPath(folder)
		hardware_path = os.path.join(folder, 'hardware')
		lib_path = os.path.join(folder, 'lib')
		version_file_path = os.path.join(lib_path, 'version.txt')
		if os.path.isdir(hardware_path) and os.path.isfile(version_file_path):
			state = True
	return state

def getArduinoFolder():
	arduino_folder = constant.sketch_settings.get('arduino_folder', '')
	if arduino_folder:
		if not isArduinoFolder(arduino_folder):
			arduino_folder = ''
		else:
			if constant.sys_platform == 'osx':
				arduino_folder = getRealArduinoPath(arduino_folder)
	return arduino_folder

def setArduinoFolder(arduino_folder):
	constant.sketch_settings.set('arduino_folder', arduino_folder)

def isSketchFolder(folder):
	state = False
	file_list = fileutil.listDir(folder, with_dirs = False)
	for cur_file in file_list:
		cur_file_ext = os.path.splitext(cur_file)[1]
		if cur_file_ext in ino_ext_list:
			state = True
			break
	return state

def getDefaultSketchbookFolder():
	document_folder = fileutil.getDocumentFolder()
	sketchbook_folder = os.path.join(document_folder, 'Arduino')
	return sketchbook_folder

def getSketchbookFolder():
	sketchbook_folder = constant.global_settings.get('sketchbook_folder', '')
	if (not sketchbook_folder) or (not os.path.isdir(sketchbook_folder)):
		sketchbook_folder = getDefaultSketchbookFolder()
		setSketchbookFolder(sketchbook_folder)
	checkSketchbookFolder(sketchbook_folder)
	return sketchbook_folder

def setSketchbookFolder(sketchbook_folder):
	constant.global_settings.set('sketchbook_folder', sketchbook_folder)

def checkSketchbookFolder(sketchbook_folder):
	libraries_folder = os.path.join(sketchbook_folder, 'libraries')
	hardware_folder = os.path.join(sketchbook_folder, 'hardware')
	folder_list = [sketchbook_folder, libraries_folder, hardware_folder]

	for folder in folder_list:
		if os.path.isfile(folder):
			os.rename(folder, folder+'.bak')
		if not os.path.exists(folder):
			os.makedirs(folder)

def getRootFolderList():
	sketchbook_folder = getSketchbookFolder()
	arduino_folder = getArduinoFolder()

	folder_list = [sketchbook_folder]
	if arduino_folder:
		folder_list.append(arduino_folder)
	return folder_list

def isCoreFolder(folder):
	state = False
	if os.path.isdir(folder):
		cores_folder = os.path.join(folder, 'cores')
		boards_file = os.path.join(folder, 'boards.txt')
		if os.path.isdir(cores_folder) or os.path.isfile(boards_file):
			state = True
	return state

def getCoreFolderList():
	core_folder_list = []
	folder_list = getRootFolderList()

	for folder in folder_list:
		hardware_folder = os.path.join(folder, 'hardware')
		if not os.path.isdir(hardware_folder):
			continue
		sub_folder_name_list = fileutil.listDir(hardware_folder, with_files = False)
		for sub_folder_name in sub_folder_name_list:
			if sub_folder_name == 'tools':
				continue
			sub_folder = os.path.join(hardware_folder, sub_folder_name)
			if isCoreFolder(sub_folder):
				core_folder_list.append(sub_folder)
			else:
				sub_sub_folder_name_list = fileutil.listDir(sub_folder, with_files = False)
				for sub_sub_folder_name in sub_sub_folder_name_list:
					sub_sub_folder = os.path.join(sub_folder, sub_sub_folder_name)
					if isCoreFolder(sub_sub_folder):
						core_folder_list.append(sub_sub_folder)
	return core_folder_list

def getPlatformNameFromFile(platform_file):
	platform_name = ''
	# opened_file = open(platform_file)
	# lines = opened_file.readlines()
	# opened_file.close()
	lines = fileutil.readFileLines(platform_file)

	for line in lines:
		if 'name=' in line:
			(key, value) = textutil.getKeyValue(line)
			platform_name = value
			break
	return platform_name

def getPlatformNameFromCoreFolder(core_folder):
	platform_name = 'Arduino AVR Boards'
	platform_file = os.path.join(core_folder, 'platform.txt')
	if os.path.isfile(platform_file):
		platform_name = getPlatformNameFromFile(platform_file)
	else:
		cores_folder = os.path.join(core_folder, 'cores')
		arduino_src_folder = os.path.join(cores_folder, 'arduino')
		if not os.path.isdir(arduino_src_folder):
			core_folder_name = os.path.split(core_folder)[1]
			platform_name = core_folder_name[0].upper() + core_folder_name[1:] + ' Boards'
	return platform_name

def getPlatformListFromCoreFolderList():
	platform_list = []
	platform_name_list = []
	name_platform_dict = {}

	root_folder_list = getRootFolderList()
	platform = Platform('General')
	platform.setCoreFolderList(root_folder_list)
	platform_list.append(platform)

	core_folder_list = getCoreFolderList()
	for core_folder in core_folder_list:
		platform_name = getPlatformNameFromCoreFolder(core_folder)
		if platform_name:
			if not platform_name in platform_name_list:
				platform = Platform(platform_name)
				platform_name_list.append(platform_name)
				platform_list.append(platform)
				name_platform_dict[platform_name] = platform
			else:
				platform = name_platform_dict[platform_name]
			platform.addCoreFolder(core_folder)
	return platform_list

def getBoardGeneralBlock(board_block):
	block = []
	for line in board_block:
		if 'menu.' in line:
			break
		block.append(line)
	return block

def getBoardOptionBlock(board_block, menu_option_id):
	block = []
	for line in board_block:
		if menu_option_id in line:
			index = line.index(menu_option_id) + len(menu_option_id) + 1
			block.append(line[index:])
	return block

def splitBoardOptionBlock(board_option_block):
	block_list = []

	item_id_list = []
	for line in board_option_block:
		(key, value) = textutil.getKeyValue(line)
		length = len(key.split('.'))
		if length <= 2 :
			item_id = key
			item_id = item_id.replace('name', '')
			item_id_list.append(item_id)

	for item_id in item_id_list:
		block = []
		for line in board_option_block:
			if item_id in line:
				block.append(line)
		block_list.append(block)
	return block_list

def getBlockInfo(block):
	title_line = block[0]
	(item_id, caption) = textutil.getKeyValue(title_line)
	item_id = item_id.replace('.name', '') + '.'

	args = {}
	for line in block[1:]:
		(key, value) = textutil.getKeyValue(line)
		key = key.replace(item_id, '')
		args[key] = value
	return (caption, args)
	
def getBoardListFromFolder(folder, build_folder_list):
	board_list = []
	boards_file = os.path.join(folder, 'boards.txt')
	if os.path.isfile(boards_file):
		# opened_file = open(boards_file, 'r')
		# lines = opened_file.readlines()
		# opened_file.close()
		lines = fileutil.readFileLines(boards_file)

		board_block_list = textutil.getBlockList(lines)

		board_option_id_list = []
		board_option_caption_dict = {}
		header_block = board_block_list[0]
		for line in header_block:
			(board_option_id, caption) = textutil.getKeyValue(line)
			board_option_id_list.append(board_option_id)
			board_option_caption_dict[board_option_id] = caption

		for board_block in board_block_list[1:]:
			board_general_block = getBoardGeneralBlock(board_block)
			(name, args) = getBlockInfo(board_general_block)

			args['build.cores_folder'] = build_folder_list[0]
			args['build.variants_folder'] = build_folder_list[1]
			args['build.system.path'] = build_folder_list[2]
			args['build.uploaders_folder'] = build_folder_list[3]

			cur_board = Board(name)
			cur_board.setFolder(folder)
			cur_board.setArgs(args)
			for board_option_id in board_option_id_list:
				board_option_block = getBoardOptionBlock(board_block, board_option_id)
				if board_option_block:
					cur_board_option = BoardOption(board_option_caption_dict[board_option_id])
					option_item_block_list = splitBoardOptionBlock(board_option_block)
					for option_item_block in option_item_block_list:
						(name, args) = getBlockInfo(option_item_block)
						cur_option_item = BoardOptionItem(name)
						cur_option_item.setArgs(args)
						cur_board_option.addItem(cur_option_item)
					cur_board.addOption(cur_board_option)
			board_list.append(cur_board)
	return board_list

def getProgrammerListFromFolder(folder):
	programmer_list = []
	programmers_file = os.path.join(folder, 'programmers.txt')
	if os.path.isfile(programmers_file):
		# opened_file = open(programmers_file, 'r')
		# lines = opened_file.readlines()
		# opened_file.close()
		lines = fileutil.readFileLines(programmers_file)

		programmer_block_list = textutil.getBlockList(lines)
		for programmer_block in programmer_block_list:
			if programmer_block:
				(name, args) = getBlockInfo(programmer_block)
				if not 'program.extra_params' in args:
					if 'Parallel' in name:
						value = '-F'
					else:
						value = ''
						if 'communication' in args:
							comm_type = args['communication']
							if comm_type == 'serial':
								port = '{serial.port}'
							else:
								port = comm_type
							value += '-P%s' % port
							value += ' '
						if 'speed' in args:
							if not 'program.speed' in args:
								args['program.speed'] = args['speed']
						if 'program.speed' in args:
							speed = args['program.speed']
							value += '-b%s' % speed
					args['program.extra_params'] = value

				cur_programmer = Programmer(name)
				cur_programmer.setArgs(args)
				programmer_list.append(cur_programmer)
	return programmer_list

def getSketchFromFolder(folder, level = 0):
	folder_name = os.path.split(folder)[1]
	sketch = SketchItem(folder_name)
	has_sub_folder = False

	if level < 4:
		sub_folder_name_list = fileutil.listDir(folder, with_files = False)
		if sub_folder_name_list:
			for sub_folder_name in sub_folder_name_list:
				sub_folder = os.path.join(folder, sub_folder_name)
				sub_sketch = getSketchFromFolder(sub_folder, level + 1)
				if sub_sketch.hasSubItem():
					sketch.addSubItem(sub_sketch)
				elif isSketchFolder(sub_folder):
					sub_sketch.setFolder(sub_folder)
					sketch.addSubItem(sub_sketch)
			has_sub_folder = True

	if not has_sub_folder:
		if isSketchFolder(folder):
			sketch.setFolder(folder)

	if level == 0:
		sub_sketch = SketchItem('-')
		sketch.addSubItem(sub_sketch)
	return sketch

def printSketch(sketch, level = 0):
	caption = sketch.getName()
	if level > 0:
		caption = '\t' * level + '|__' + caption
	if not sketch.hasSubItem():
		caption += ' ('
		caption += sketch.getFolder()
		caption += ')'
	print(caption)

	if sketch.hasSubItem():
		for sub_item in sketch.getSubItemList():
			printSketch(sub_item, level+1)

def getSketchbook():
	sketchbook_folder = getSketchbookFolder()
	sketchbook = getSketchFromFolder(sketchbook_folder)
	sketchbook.setName('Sketchbook')
	return sketchbook

def getGeneralLibraryListFromFolder(folder, platform_name = ''):
	lib_list = []
	libraries_folder = os.path.join(folder, 'libraries')
	if os.path.isdir(libraries_folder):
		sub_folder_name_list = fileutil.listDir(libraries_folder, with_files = False)
		for sub_folder_name in sub_folder_name_list:
			sub_folder = os.path.join(libraries_folder, sub_folder_name)
			lib_item = LibItem(sub_folder_name)
			lib_item.setFolder(sub_folder)

			arch_folder = os.path.join(sub_folder, 'arch')
			if os.path.isdir(arch_folder):
				avr_folder = os.path.join(arch_folder, 'avr')
				sam_folder = os.path.join(arch_folder, 'sam')
				if os.path.isdir(avr_folder):
					if 'AVR' in platform_name:
						lib_list.append(lib_item)
				if os.path.isdir(sam_folder):
					if 'ARM' in platform_name:
						lib_list.append(lib_item)
			else:
				if 'General' in platform_name:
					lib_list.append(lib_item)
	if lib_list:
		lib_item = LibItem('-')
		lib_list.append(lib_item)
	return lib_list

def getPlatformLibraryListFromFolder(folder):
	lib_list = []
	libraries_folder = os.path.join(folder, 'libraries')
	if os.path.isdir(libraries_folder):
		sub_folder_name_list = fileutil.listDir(libraries_folder, with_files = False)
		for sub_folder_name in sub_folder_name_list:
			sub_folder = os.path.join(libraries_folder, sub_folder_name)
			lib_item = LibItem(sub_folder_name)
			lib_item.setFolder(sub_folder)
			lib_list.append(lib_item)
	if lib_list:
		lib_item = LibItem('-')
		lib_list.append(lib_item)
	return lib_list

def getLibraryListFromPlatform(platform_list, platform_id):
	lib_list = []
	platform_general = platform_list[0]
	general_core_folder_list = platform_general.getCoreFolderList()

	cur_platform = platform_list[platform_id]
	core_folder_list = cur_platform.getCoreFolderList()

	platform_name = cur_platform.getName()
	for core_folder in general_core_folder_list:
		lib_list += getGeneralLibraryListFromFolder(core_folder, platform_name)

	if platform_id > 0:
		for core_folder in core_folder_list:
			lib_list += getPlatformLibraryListFromFolder(core_folder)
	return lib_list

def getExampleListFromFolder(folder):
	example_list = []
	libraries_folder = os.path.join(folder, 'libraries')
	examples_folder = os.path.join(folder, 'examples')
	sub_folder_list = [examples_folder, libraries_folder]
	for sub_folder in sub_folder_list:
		if os.path.isdir(sub_folder):
			example = getSketchFromFolder(sub_folder)
			example_list.append(example)
	return example_list

def getExampleFromPlatform(platform):
	name = platform.getName()
	example = SketchItem(name)

	example_list = []
	core_folder_list = platform.getCoreFolderList()
	for core_folder in core_folder_list:
		example_list += getExampleListFromFolder(core_folder)

	for cur_example in example_list:
		sub_example_list = cur_example.getSubItemList()
		example.addSubItemList(sub_example_list)
	return example

def hasCoreSrcFolder(folder):
	state = False
	cores_folder = os.path.join(folder, 'cores')
	if os.path.isdir(cores_folder):
		state = True
	return state

def getCoreSrcFolderFromPlatform(platform):
	core_src_folder = ''
	core_folder_list = platform.getCoreFolderList()
	for core_folder in core_folder_list:
		if hasCoreSrcFolder(core_folder):
			# core_src_folder = os.path.join(core_folder, 'cores')
			core_src_folder = core_folder
			break
	return core_src_folder

def findSubFolderInFolderList(folder_list, sub_folder_name):
	sub_folder = ''

	main_folder = ''
	arduino_folder = getArduinoFolder()
	for cur_folder in folder_list:
		if arduino_folder in cur_folder:
			main_folder = cur_folder
			break

	if main_folder:
		cur_sub_folder = os.path.join(main_folder, sub_folder_name)
		if os.path.isdir(cur_sub_folder):
			sub_folder = cur_sub_folder
	
	if not sub_folder:
		for cur_folder in folder_list:
			cur_sub_folder = os.path.join(cur_folder, sub_folder_name)
			if os.path.isdir(cur_sub_folder):
				sub_folder = cur_sub_folder
				break
	return sub_folder

def getDefaultBuildFolderList(core_folder_list, folder_name_list):
	default_build_folder_list = []
	for folder_name in folder_name_list:
		index = folder_name_list.index(folder_name)
		cur_folder = findSubFolderInFolderList(core_folder_list, folder_name)
		default_build_folder_list.append(cur_folder)
	return default_build_folder_list

def getFolderBuildFolderDict(core_folder_list, folder_name_list):
	folder_build_folder_dict = {}
	default_build_folder_list = getDefaultBuildFolderList(core_folder_list, folder_name_list)
	for core_folder in core_folder_list:
		build_folder_list = []
		for folder_name in folder_name_list:
			index = folder_name_list.index(folder_name)
			cur_folder = os.path.join(core_folder, folder_name)
			if not os.path.isdir(cur_folder):
				cur_folder = default_build_folder_list[index]
			build_folder_list.append(cur_folder)
		folder_build_folder_dict[core_folder] = build_folder_list
	return folder_build_folder_dict

def getPlatformList():
	platform_list = getPlatformListFromCoreFolderList()
	for platform in platform_list:
		platform_name = platform.getName()
		index = platform_list.index(platform)
		core_folder_list = platform.getCoreFolderList()
		folder_build_folder_dict = getFolderBuildFolderDict(core_folder_list, build_folder_name_list)

		example = getExampleFromPlatform(platform)
		lib_list = getLibraryListFromPlatform(platform_list, index)
		h_lib_dict = getHLibDict(lib_list, platform_name)

		platform.setExample(example)
		platform.setLibList(lib_list)
		platform.setHLibDict(h_lib_dict)

		for core_folder in core_folder_list:
			build_folder_list = folder_build_folder_dict[core_folder]
			board_list = getBoardListFromFolder(core_folder, build_folder_list)
			programmer_list = getProgrammerListFromFolder(core_folder)
			platform.addBoardList(board_list)
			platform.addProgrammerList(programmer_list)
	return platform_list

def getVersionText():
	version_text = '1.0.5'
	arduino_root = getArduinoFolder()
	if arduino_root:
		lib_folder = os.path.join(arduino_root, 'lib')
		version_file = os.path.join(lib_folder, 'version.txt')
		if os.path.isfile(version_file):
			# opened_file = open(version_file)
			# lines = opened_file.readlines()
			# opened_file.close()
			lines = fileutil.readFileLines(version_file)
			for line in lines:
				line = line.strip()
				if line:
					version_text = line
					break
	return version_text

def getVersion(version_text):
	version = 105
	patter_text = r'[\d.]+'
	pattern = re.compile(patter_text)
	match = pattern.search(version_text)
	if match:
		version_text = match.group()
		number_list = version_text.split('.')
		version = 0
		power = 0
		for number in number_list:
			number = int(number)
			version += number * (10 ** power)
			power -= 1
		version *= 100
	return int(version)

def getKeywordListFromFile(keywords_file):
	keyword_list = []
	# opened_file = open(keywords_file, 'r')
	# lines = opened_file.readlines()
	# opened_file.close()
	lines = fileutil.readFileLines(keywords_file)

	for line in lines:
		line = line.strip()
		if line and (not '#' in line):
			word_list = re.findall(r'\S+', line)
			if len(word_list) > 1:
				keyword_name = word_list[0]
				if len(word_list) == 3:
					keyword_type = word_list[1]
					keyword_ref = word_list[2]
				elif len(word_list) == 2:
					if 'LITERAL' in word_list[1] or 'KEYWORD' in word_list[1]:
						keyword_type = word_list[1]
						keyword_ref = ''
					else:
						keyword_type = ''
						keyword_ref = word_list[1]
				cur_keyword = Keyword(keyword_name)
				cur_keyword.setType(keyword_type)
				cur_keyword.setRef(keyword_ref)
				keyword_list.append(cur_keyword)
	return keyword_list

def getKeywordListFromCoreFolderList(core_folder_list):
	keyword_list = []
	for core_folder in core_folder_list:
		lib_folder = os.path.join(core_folder, 'lib')
		keywords_file = os.path.join(lib_folder, 'keywords.txt')
		if os.path.isfile(keywords_file):
			cur_keyword_list = getKeywordListFromFile(keywords_file)
			keyword_list += cur_keyword_list
	return keyword_list

def getKeywordListFromLibList(lib_list):
	keyword_list = []
	for lib in lib_list:
		lib_folder = lib.getFolder()
		keywords_file = os.path.join(lib_folder, 'keywords.txt')
		if os.path.isfile(keywords_file):
			cur_keyword_list = getKeywordListFromFile(keywords_file)
			keyword_list += cur_keyword_list
	return keyword_list

def getKeywordListFromPlatform(platform):
	keyword_list = []
	core_folder_list = platform.getCoreFolderList()
	lib_list = platform.getLibList()
	keyword_list += getKeywordListFromCoreFolderList(core_folder_list)
	keyword_list += getKeywordListFromLibList(lib_list)
	return keyword_list

def getKeywordRefList(keyword_list):
	keyword_ref_dict = {}
	for keyword in keyword_list:
		ref = keyword.getRef()
		if ref and ref[0].isupper():
			keyword_name = keyword.getName()
			keyword_ref_dict[keyword_name] = ref
	return keyword_ref_dict

def getUrl(url):
	file_name = url + '.html'
	arduino_folder = getArduinoFolder()
	reference_folder = os.path.join(arduino_folder, 'reference')
	reference_file = os.path.join(reference_folder, file_name)
	if os.path.isfile(reference_file):
		reference_file = reference_file.replace(os.path.sep, '/')
		url = 'file://' + reference_file
	else:
		url = 'http://arduino.cc'
	return url

def getSelectedTextFromView(view):
	selected_text = ''
	region_list = view.sel()
	for region in region_list:
		selected_region = view.word(region)
		selected_text += view.substr(selected_region)
		selected_text += '\n'
	return selected_text

def getWordListFromText(text):
	pattern_text = r'\b\w+\b'
	word_list = re.findall(pattern_text, text)
	return word_list

def getSelectedWordList(view):
	selected_text = getSelectedTextFromView(view)
	word_list = getWordListFromText(selected_text)
	return word_list

def getHLibDict(lib_list, platform_name):
	h_lib_dict = {}
	for lib in lib_list:
		lib_folder = lib.getFolder()
		h_list = sketch.getHSrcFileList(lib_folder, platform_name)
		for h in h_list:
			h_lib_dict[h] = lib_folder
	return h_lib_dict

def newSketch(sketch_name):
	sketch_file = ''
	sketchbook_folder = getSketchbookFolder()
	sketch_folder = os.path.join(sketchbook_folder, sketch_name)

	if not os.path.exists(sketch_folder):
		os.makedirs(sketch_folder)
		file_name = sketch_name + '.ino'
		sketch_file = os.path.join(sketch_folder, file_name)

		text = '// %s\n\n' % file_name
		text += 'void setup() {\n\n'
		text += '}\n\n'
		text += 'void loop() {\n\n'
		text += '}\n\n'
		fileutil.writeFile(sketch_file, text)
	return sketch_file
########NEW FILE########
__FILENAME__ = compiler
#-*- coding: utf-8 -*-
# stino/compiler.py

import os
import re
import threading
import subprocess

import sublime

from . import fileutil
from . import textutil
from . import constant
from . import serial
from . import base
from . import preprocess
from . import sketch
from . import console

ram_size_dict = {}
ram_size_dict['attiny44'] = '256'
ram_size_dict['attiny45'] = '256'
ram_size_dict['attiny84'] = '512'
ram_size_dict['attiny85'] = '512'
ram_size_dict['atmega8'] = '1024'
ram_size_dict['atmega168'] = '1024'
ram_size_dict['atmega328p'] = '2048'
ram_size_dict['atmega644'] = '4096'
ram_size_dict['atmega644p'] = '4096'
ram_size_dict['atmega1284'] = '16384'
ram_size_dict['atmega1284p'] = '16384'
ram_size_dict['atmega1280'] = '4096'
ram_size_dict['atmega2560'] = '8196'
ram_size_dict['atmega32u4'] = '2560'
ram_size_dict['at90usb162'] = '512'
ram_size_dict['at90usb646'] = '4096'
ram_size_dict['at90usb1286'] = '8192'
ram_size_dict['cortex-m3'] = '98304'
ram_size_dict['cortex-m4'] = '16384'

class Args:
	def __init__(self, cur_project, arduino_info):
		self.args = getFullArgs(cur_project, arduino_info)

	def getArgs(self):
		return self.args

class Command:
	def __init__(self, command):
		self.in_file = ''
		self.out_file = ''
		self.command = command
		self.calc_size = False
		self.stdout = ''
		self.out_text = ''

	def run(self, output_console):
		output_console.printText(self.out_text)
		if self.out_file:
			message = 'Creating %s...\n' % self.out_file
			output_console.printText(message)

		cur_command = formatCommand(self.command)
		compile_proc = subprocess.Popen(cur_command, stdout = subprocess.PIPE,
			stderr = subprocess.PIPE, shell = True)
		result = compile_proc.communicate()
		return_code = compile_proc.returncode
		stdout = result[0].decode(constant.sys_encoding).replace('\r', '')
		stderr = result[1].decode(constant.sys_encoding).replace('\r', '')
		self.stdout = stdout

		show_compilation_output = constant.sketch_settings.get('show_compilation_output', False)
		if show_compilation_output:
			output_console.printText(self.command)
			output_console.printText('\n')
			output_console.printText(stdout)
		output_console.printText(stderr)
		return return_code

	def isSizeCommand(self):
		return self.calc_size

	def setSizeCommand(self):
		self.calc_size = True

	def getOutFile(self):
		return self.out_file

	def getCommand(self):
		return self.command

	def getStdout(self):
		return self.stdout

	def setInFile(self, in_file):
		self.in_file = in_file

	def setOutFile(self, out_file):
		self.out_file = out_file

	def setCommand(self, command):
		self.command = command

	def setOutputText(self, text):
		self.out_text = text

class Compiler:
	def __init__(self, arduino_info, cur_project, args):
		self.arduino_info = arduino_info
		self.cur_project = cur_project
		self.args = args.getArgs()
		self.output_console = console.Console(cur_project.getName())
		self.no_error = True
		self.is_finished = False
		self.prepare()

	def getOutputConsole(self):
		return self.output_console

	def isFinished(self):
		return self.is_finished

	def noError(self):
		return self.no_error

	def prepare(self):
		self.command_list = []
		if self.args:
			self.command_list = genCommandList(self.args, self.cur_project, self.arduino_info)

	def run(self):
		if self.command_list:
			compilation_thread = threading.Thread(target=self.compile)
			compilation_thread.start()
		else:
			self.no_error = False
			self.is_finished = True
			self.output_console.printText('Please choose the Ardunio Application Folder.')

	def compile(self):
		self.output_console.printText('Compiling %s...\n' % self.cur_project.getName())
		for cur_command in self.command_list:
			return_code = cur_command.run(self.output_console)
			if return_code > 0:
				self.output_console.printText('[Stino - Error %d]\n' % return_code)
				self.no_error = False
				break
			else:
				if cur_command.isSizeCommand():
					stdout = cur_command.getStdout()
					printSizeInfo(self.output_console, stdout, self.args)
		if self.no_error:
			self.output_console.printText('[Stino - Done compiling.]\n')
		self.is_finished = True

def getChosenArgs(arduino_info):
	args = {}
	platform_list = arduino_info.getPlatformList()
	if len(platform_list) > 1:
		platform_id = constant.sketch_settings.get('platform', -1)
		if not ((platform_id > 0) and (platform_id < len(platform_list))):
			platform_id = 1
			cur_platform = platform_list[platform_id]
			platform_name = cur_platform.getName()
			constant.sketch_settings.set('platform', platform_id)
			constant.sketch_settings.set('platform_name', platform_name)
		selected_platform = platform_list[platform_id]
		board_list = selected_platform.getBoardList()
		board_id = constant.sketch_settings.get('board', -1)
		if board_list:
			serial_port = getSelectedSerialPort()
			args['serial.port'] = serial_port

			if not (board_id > -1 or board_id < len(board_list)):
				board_id = 0
				constant.sketch_settings.set('board', board_id)
			selected_board = board_list[board_id]
			args.update(selected_board.getArgs())

			board_option_list = selected_board.getOptionList()
			if board_option_list:
				board_option_key = '%d.%d' % (platform_id, board_id)
				board_option_dict = constant.sketch_settings.get('board_option', {})

				if board_option_key in board_option_dict:
					option_item_id_list = board_option_dict[board_option_key]
					if len(option_item_id_list) < len(board_option_list):
						option_item_id_list = []
				else:
					option_item_id_list = []

				if not option_item_id_list:
					for board_option in board_option_list:
						option_item_id_list.append(0)

				for board_option in board_option_list:
					index = board_option_list.index(board_option)
					option_item_id = option_item_id_list[index]
					option_item_list = board_option.getItemList()
					option_item = option_item_list[option_item_id]
					option_item_args = option_item.getArgs()
					args.update(option_item_args)

			if 'build.vid' in args:
				if not 'build.extra_flags' in args:
					args['build.extra_flags'] = '-DUSB_VID={build.vid} -DUSB_PID={build.pid}'

			if 'bootloader.path' in args:
				bootloader_path = args['bootloader.path']
				if 'bootloader.file' in args:
					bootloader_file = args['bootloader.file']
					bootloader_file = bootloader_path + '/' + bootloader_file
					args['bootloader.file'] = bootloader_file

			programmer_list = selected_platform.getProgrammerList()
			if programmer_list:
				platform_programmer_dict = constant.sketch_settings.get('programmer', {})
				if str(platform_id) in platform_programmer_dict:
					programmer_id = platform_programmer_dict[str(platform_id)]
				else:
					programmer_id = 0
				programmer = programmer_list[programmer_id]
				programmer_args = programmer.getArgs()
				args.update(programmer_args)

			platform_file = getPlatformFile(arduino_info)
			args = addBuildUsbValue(args, platform_file)
			args = replaceAllDictValue(args)

			if not 'upload.maximum_ram_size' in args:
				args['upload.maximum_ram_size'] = '0'
				if 'build.mcu' in args:
					build_mcu = args['build.mcu']
					if build_mcu in ram_size_dict:
						args['upload.maximum_ram_size'] = ram_size_dict[build_mcu]

			if 'build.elide_constructors' in args:
				if args['build.elide_constructors'] == 'true':
					args['build.elide_constructors'] = '-felide-constructors'
				else:
					args['build.elide_constructors'] = ''
			if 'build.cpu' in args:
				args['build.mcu'] = args['build.cpu']
			if 'build.gnu0x' in args:
				if args['build.gnu0x'] == 'true':
					args['build.gnu0x'] = '-std=gnu++0x'
				else:
					args['build.gnu0x'] = ''
			if 'build.cpp0x' in args:
				if args['build.cpp0x'] == 'true':
					args['build.cpp0x'] = '-std=c++0x'
				else:
					args['build.cpp0x'] = ''
	return args

def getSelectedSerialPort():
	serial_port = 'no_serial_port'
	serial_port_list = serial.getSerialPortList()
	if serial_port_list:
		serial_port_id = constant.sketch_settings.get('serial_port', -1)
		if not (serial_port_id > -1 and serial_port_id < len(serial_port_list)):
			serial_port_id = 0
			constant.sketch_settings.set('serial_port', serial_port_id)
		serial_port = serial_port_list[serial_port_id]
	return serial_port

def getReplaceTextList(text):
	pattern_text = r'\{\S+?}'
	pattern = re.compile(pattern_text)
	replace_text_list = pattern.findall(text)
	return replace_text_list

def replaceValueText(value_text, args_dict):
	replace_text_list = getReplaceTextList(value_text)
	for replace_text in replace_text_list:
		key = replace_text[1:-1]
		if key in args_dict:
			value = args_dict[key]
		else:
			value = ''
		value_text = value_text.replace(replace_text, value)
	return value_text

def replaceAllDictValue(args_dict):
	for key in args_dict:
		value_text = args_dict[key]
		value_text = replaceValueText(value_text, args_dict)
		args_dict[key] = value_text
	return args_dict

def addBuildUsbValue(args, platform_file):
	lines = fileutil.readFileLines(platform_file)
	for line in lines:
		line = line.strip()
		if line and not '#' in line:
			(key, value) = textutil.getKeyValue(line)
			if 'extra_flags' in key:
				continue
			if 'build.' in key:
				if 'usb_manufacturer' in key:
					if not value:
						value = 'unknown'
				value = replaceValueText(value, args)

				if constant.sys_platform == 'windows':
					value = value.replace('"', '\\"')
					value = value.replace('\'', '"')
				args[key] = value
	return args

def getDefaultArgs(cur_project, arduino_info):
	core_folder = getCoreFolder(arduino_info)

	arduino_folder = base.getArduinoFolder()
	ide_path = os.path.join(arduino_folder, 'hardware')
	project_name = cur_project.getName()
	serial_port = getSelectedSerialPort()
	archive_file = 'core.a'
	build_system_path = os.path.join(core_folder, 'system')
	arduino_version = arduino_info.getVersion()
	build_folder = getBuildFolder(cur_project)

	args = {}
	args['runtime.ide.path'] = arduino_folder
	args['ide.path'] = ide_path
	args['build.project_name'] = project_name
	args['serial.port.file'] = serial_port
	args['archive_file'] = archive_file
	args['software'] = 'ARDUINO'
	args['runtime.ide.version'] = '%d' % arduino_version
	args['source_file'] = '{source_file}'
	args['object_file'] = '{object_file}'
	args['object_files'] = '{object_files}'
	args['includes'] = '{includes}'
	args['build.path'] = build_folder
	return args

def getBuildFolder(cur_project):
	build_folder = constant.sketch_settings.get('build_folder', '')
	if not (build_folder and os.path.isdir(build_folder)):
		document_folder = fileutil.getDocumentFolder()
		build_folder = os.path.join(document_folder, 'Arduino_Build')
	project_name = cur_project.getName()
	build_folder = os.path.join(build_folder, project_name)
	checkBuildFolder(build_folder)
	return build_folder

def checkBuildFolder(build_folder):
	if os.path.isfile(build_folder):
		os.remove(build_folder)
	if not os.path.exists(build_folder):
		os.makedirs(build_folder)
	file_name_list = fileutil.listDir(build_folder, with_dirs = False)
	for file_name in file_name_list:
		file_ext = os.path.splitext(file_name)[1]
		if file_ext in ['.d']:
			cur_file = os.path.join(build_folder, file_name)
			os.remove(cur_file)

def getDefaultPlatformFile(arduino_info):
	file_name = 'arduino_avr.txt'
	platform_file = ''
	platform_list = arduino_info.getPlatformList()
	platform_id = constant.sketch_settings.get('platform', 1)
	platform = platform_list[platform_id]
	platform_name = platform.getName()

	if 'Arduino ARM' in platform_name:
		file_name = 'arduino_arm.txt'
	elif 'Teensy' in platform_name:
		board_list = platform.getBoardList()
		board_id = constant.sketch_settings.get('board', 0)
		board = board_list[board_id]
		board_name = board.getName()
		board_version = float(board_name.split()[1])
		if board_version >= 3.0:
			file_name = 'teensy_arm.txt'
		else:
			file_name = 'teensy_avr.txt'
	elif 'Zpuino' in platform_name:
		file_name = 'zpuino.txt'
	platform_file = os.path.join(constant.compile_root, file_name)
	return platform_file

def getCoreFolder(arduino_info):
	platform_list = arduino_info.getPlatformList()
	platform_id = constant.sketch_settings.get('platform', -1)
	if not ((platform_id > 0) and (platform_id < len(platform_list))):
		platform_id = 1
		cur_platform = platform_list[platform_id]
		platform_name = cur_platform.getName()
		constant.sketch_settings.set('platform', platform_id)
		constant.sketch_settings.set('platform_name', platform_name)
	platform = platform_list[platform_id]

	core_folder = ''
	core_folder_list = platform.getCoreFolderList()
	for cur_core_folder in core_folder_list:
		platform_file = os.path.join(cur_core_folder, 'platform.txt')
		if os.path.isfile(platform_file):
			core_folder = cur_core_folder
			break
	return core_folder

def getPlatformFile(arduino_info):
	core_folder = getCoreFolder(arduino_info)
	if core_folder:
		platform_file = os.path.join(core_folder, 'platform.txt')
	else:
		platform_file = getDefaultPlatformFile(arduino_info)
	return platform_file

def splitPlatformFile(platform_file):
	text = fileutil.readFile(platform_file)
	index = text.index('recipe.')
	text_header = text[:index]
	text_body = text[index:]
	return (text_header, text_body)

def getPlatformArgs(platform_text, args):
	lines = platform_text.split('\n')

	for line in lines:
		line = line.strip()
		if line and not '#' in line:
			(key, value) = textutil.getKeyValue(line)
			value = replaceValueText(value, args)

			if 'tools.avrdude.' in key:
				key = key.replace('tools.avrdude.', '')
			if 'tools.bossac.' in key:
				key = key.replace('tools.bossac.', '')
			if 'tools.teensy.' in key:
				key = key.replace('tools.teensy.', '')
			if 'params.' in key:
				key = key.replace('params.', '')
			if constant.sys_platform == 'linux':
				if '.linux' in key:
					key = key.replace('.linux', '')

			show_upload_output = constant.sketch_settings.get('show_upload_output', False)
			if not show_upload_output:
				if '.quiet' in key:
					key = key.replace('.quiet', '.verbose')

			if '.verbose' in key:
				verify_code = constant.sketch_settings.get('verify_code', False)
				if verify_code:
					value += ' -V'

			if key == 'build.extra_flags':
				if key in args:
					continue
			args[key] = value
	return args

def getFullArgs(cur_project, arduino_info):
	args = {}
	board_args = getChosenArgs(arduino_info)
	if board_args:
		default_args = getDefaultArgs(cur_project, arduino_info)
		args.update(default_args)
		args.update(board_args)

		platform_file = getPlatformFile(arduino_info)
		(platform_text_header, platform_text_body) = splitPlatformFile(platform_file)
		args = getPlatformArgs(platform_text_header, args)

		variant_folder = args['build.variants_folder']
		cores_folder = args['build.cores_folder']
		build_core = args['build.core']
		build_core_folder = os.path.join(cores_folder, build_core)
		args['build.core_folder'] = build_core_folder

		if 'build.variant' in args:
			build_variant = args['build.variant']
			build_variant_folder = os.path.join(variant_folder, build_variant)
			args['build.variant.path'] = build_variant_folder
		else:
			args['build.variant.path'] = build_core_folder

		if 'compiler.path' in args:
			compiler_path = args['compiler.path']
		else:
			runtime_ide_path = args['runtime.ide.path']
			compiler_path = runtime_ide_path + '/hardware/tools/avr/bin/'
		compiler_c_cmd = args['compiler.c.cmd']
		if constant.sys_platform == 'windows':
			compiler_c_cmd += '.exe'
		compiler_c_cmd_file = os.path.join(compiler_path, compiler_c_cmd)
		if os.path.isfile(compiler_c_cmd_file):
			args['compiler.path'] = compiler_path
		else:
			args['compiler.path'] = ''

		extra_flags = constant.sketch_settings.get('extra_flag', '')
		if 'build.extra_flags' in args:
			build_extra_flags = args['build.extra_flags']
		else:
			build_extra_flags = ''
		if extra_flags:
			build_extra_flags += ' '
			build_extra_flags += extra_flags
		args['build.extra_flags'] = build_extra_flags

		args = getPlatformArgs(platform_text_body, args)
	return args

def getLibFolderListFromProject(cur_project, arduino_info):
	lib_folder_list = []

	platform_list = arduino_info.getPlatformList()
	platform_id = constant.sketch_settings.get('platform', 1)
	general_platform = platform_list[0]
	selected_platform = platform_list[platform_id]
	general_h_lib_dict = general_platform.getHLibDict()
	selected_h_lib_dict = selected_platform.getHLibDict()

	ino_src_file_list = cur_project.getInoSrcFileList()
	c_src_file_list = cur_project.getCSrcFileList()
	h_list = preprocess.getHListFromSrcList(ino_src_file_list + c_src_file_list)
	for h in h_list:
		lib_folder = ''
		if h in selected_h_lib_dict:
			lib_folder = selected_h_lib_dict[h]
		elif h in general_h_lib_dict:
			lib_folder = general_h_lib_dict[h]
		if lib_folder:
			if not lib_folder in lib_folder_list:
				lib_folder_list.append(lib_folder)
	return lib_folder_list

def genBuildCppFile(build_folder, cur_project, arduino_info):
	project_name = cur_project.getName()
	cpp_file_name = project_name + '.ino.cpp'
	cpp_file = os.path.join(build_folder, cpp_file_name)
	ino_src_file_list = cur_project.getInoSrcFileList()
	arduino_version = arduino_info.getVersion()

	doMunge = not constant.sketch_settings.get('set_bare_gcc_only', False)
	preprocess.genCppFileFromInoFileList(cpp_file, ino_src_file_list, arduino_version, preprocess=doMunge)

	return cpp_file

def genIncludesPara(build_folder, project_folder, core_folder_list, compiler_include_folder):
	folder_list = sketch.getFolderListFromFolderList(core_folder_list)
	include_folder_list = []
	include_folder_list.append(build_folder)
	include_folder_list.append(project_folder)
	include_folder_list.append(compiler_include_folder)
	include_folder_list += folder_list

	includes = ''
	for include_folder in include_folder_list:
		includes += '"-I%s" ' % include_folder
	return includes

def getCompileCommand(c_file, args, includes_para):
	build_folder = args['build.path']
	file_name = os.path.split(c_file)[1]
	file_ext = os.path.splitext(c_file)[1]

	obj_file_name = file_name + '.o'
	obj_file = os.path.join(build_folder, obj_file_name)

	if file_ext in ['.S']:
		command = args['recipe.S.o.pattern']
	elif file_ext in ['.c']:
		command = args['recipe.c.o.pattern']
	else:
		command = args['recipe.cpp.o.pattern']

	command = command.replace('{includes}', includes_para)
	command = command.replace('{source_file}', c_file)
	command = command.replace('{object_file}', obj_file)

	cur_command = Command(command)
	cur_command.setInFile(c_file)
	cur_command.setOutFile(obj_file)
	return cur_command

def getCompileCommandList(c_file_list, args, includes_para):
	command_list = []
	for c_file in c_file_list:
		cur_command = getCompileCommand(c_file, args, includes_para)
		command_list.append(cur_command)
	return command_list

def getArCommand(args, core_command_list):
	build_folder = args['build.path']
	archive_file_name = args['archive_file']
	archive_file = os.path.join(build_folder, archive_file_name)

	object_files = ''
	for core_command in core_command_list:
		core_obj_file = core_command.getOutFile()
		object_files += '"%s" ' % core_obj_file
	object_files = object_files[:-1]

	command_text = args['recipe.ar.pattern']
	command_text = command_text.replace('"{object_file}"', object_files)
	ar_command = Command(command_text)
	ar_command.setOutFile(archive_file)
	return ar_command

def getElfCommand(args, project_command_list):
	build_folder = args['build.path']
	project_name = args['build.project_name']
	elf_file_name = project_name + '.elf'
	elf_file = os.path.join(build_folder, elf_file_name)

	object_files = ''
	for project_command in project_command_list:
		project_obj_file = project_command.getOutFile()
		object_files += '"%s" ' % project_obj_file
	object_files = object_files[:-1]

	command_text = args['recipe.c.combine.pattern']
	command_text = command_text.replace('{object_files}', object_files)
	elf_command = Command(command_text)
	elf_command.setOutFile(elf_file)
	return elf_command

def getEepCommand(args):
	build_folder = args['build.path']
	project_name = args['build.project_name']
	eep_file_name = project_name + '.eep'
	eep_file = os.path.join(build_folder, eep_file_name)

	command_text = args['recipe.objcopy.eep.pattern']
	eep_command = Command(command_text)
	eep_command.setOutFile(eep_file)
	return eep_command

def getHexCommand(args):
	command_text = args['recipe.objcopy.hex.pattern']
	hex_command = Command(command_text)

	build_folder = args['build.path']
	project_name = args['build.project_name']
	ext = command_text[-5:-1]
	hex_file_name = project_name + ext
	hex_file = os.path.join(build_folder, hex_file_name)
	hex_command.setOutFile(hex_file)
	return hex_command

def getSizeCommand(args):
	command_text = args['recipe.size.pattern']
	command_text = command_text.replace('-A', '')
	command_text = command_text.replace('.hex', '.elf')
	size_command = Command(command_text)
	size_command.setSizeCommand()
	return size_command

def genCommandList(args, cur_project, arduino_info):
	build_folder = args['build.path']
	project_folder = cur_project.getFolder()
	build_cpp_file = genBuildCppFile(build_folder, cur_project, arduino_info)

	build_core_folder = args['build.core_folder']
	build_variant_folder = args['build.variant.path']
	lib_folder_list = getLibFolderListFromProject(cur_project, arduino_info)
	core_folder_list = [build_core_folder, build_variant_folder] + lib_folder_list

	compiler_bin_folder = args['compiler.path']
	compiler_folder = os.path.split(compiler_bin_folder)[0]
	compiler_folder = os.path.split(compiler_folder)[0]
	compiler_name = os.path.split(compiler_folder)[1]
	compiler_folder = os.path.join(compiler_folder, compiler_name)
	compiler_include_folder = os.path.join(compiler_folder, 'include')
	compiler_include_folder = compiler_include_folder.replace('/', os.path.sep)
	# core_folder_list.append(compiler_include_folder)

	includes_para = genIncludesPara(build_folder, project_folder, core_folder_list, compiler_include_folder)
	project_C_file_list = [build_cpp_file] + cur_project.getCSrcFileList()  + cur_project.getAsmSrcFileList()
	core_C_file_list = sketch.getCSrcFileListFromFolderList(core_folder_list) + sketch.getAsmSrcFileListFromFolderList(core_folder_list)

	project_command_list = getCompileCommandList(project_C_file_list, args, includes_para)
	core_command_list = getCompileCommandList(core_C_file_list, args, includes_para)
	ar_command = getArCommand(args, core_command_list)
	elf_command = getElfCommand(args, project_command_list)
	eep_command = getEepCommand(args)
	hex_command = getHexCommand(args)
	size_command = getSizeCommand(args)

	full_compilation = constant.sketch_settings.get('full_compilation', True)
	archive_file_name = args['archive_file']
	archive_file = os.path.join(build_folder, archive_file_name)
	if not os.path.isfile(archive_file):
		full_compilation = True

	command_list = []
	command_list += project_command_list
	if full_compilation:
		if os.path.isfile(archive_file):
			os.remove(archive_file)
		command_list += core_command_list
		command_list.append(ar_command)
	command_list.append(elf_command)
	if args['recipe.objcopy.eep.pattern']:
		command_list.append(eep_command)
	command_list.append(hex_command)
	command_list.append(size_command)
	return command_list

def getCommandList(cur_project, arduino_info):
	command_list = []
	args = getFullArgs(cur_project, arduino_info)
	if args:
		command_list = genCommandList(args, cur_project, arduino_info)
	return command_list

def printSizeInfo(output_console, stdout, args):
	flash_size_key = 'upload.maximum_size'
	ram_size_key = 'upload.maximum_ram_size'
	max_flash_size = int(args[flash_size_key])
	max_ram_size = int(args[ram_size_key])

	size_line = stdout.split('\n')[-2].strip()
	info_list = re.findall(r'\S+', size_line)
	text_size = int(info_list[0])
	data_size = int(info_list[1])
	bss_size = int(info_list[2])


	flash_size = text_size + data_size
	ram_size = data_size + bss_size

	flash_percent = float(flash_size) / max_flash_size * 100
	text = 'Binary sketch size: %d bytes (of a %d byte maximum, %.2f percent).\n' % (flash_size, max_flash_size, flash_percent)
	if max_ram_size > 0:
		ram_percent = float(ram_size) / max_ram_size * 100
		text += 'Estimated memory use: %d bytes (of a %d byte maximum, %.2f percent).\n' % (ram_size, max_ram_size, ram_percent)
	output_console.printText(text)

def formatCommand(command):
	if constant.sys_version < 3:
		if constant.sys_platform == 'windows':
			command = command.replace('/"', '"')
			command = command.replace('/', os.path.sep)
			command = '"' + command + '"'
	if constant.sys_version < 3:
		if isinstance(command, unicode):
			command = command.encode(constant.sys_encoding)
	return command

########NEW FILE########
__FILENAME__ = console
#-*- coding: utf-8 -*-
# stino/console.py

import sublime

import threading

from . import constant

class Console:
	def __init__(self, name = 'stino_console'):
		self.name = name
		self.panel = None
		self.show_text = ''

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def printText(self, text):
		self.show_text += text
		if constant.sys_version < 3:
			show_thread = threading.Thread(target=self.show)
			show_thread.start()
		else:
			self.update()

	def show(self):
		sublime.set_timeout(self.update, 0)

	def update(self):
		window = sublime.active_window()
		if window:
			if not self.panel:
				if constant.sys_version < 3:
					self.panel = window.get_output_panel(self.name)
				else:
					self.panel = window.create_output_panel(self.name)

		if not self.panel is None:
			if self.show_text:
				text = self.show_text
				self.panel.run_command('panel_output', {'text': text})
				self.show_text = ''
				panel_name = 'output.' + self.name
				window.run_command("show_panel", {"panel": panel_name})
				
########NEW FILE########
__FILENAME__ = constant
#-*- coding: utf-8 -*-
# stino/constant.py

import os
import sys
import locale
import codecs

import sublime

from . import preference

baudrate_list = ['300', '1200', '2400', '4800', '9600', '14400', 
		'19200', '28800', '38400', '57600', '115200']
line_ending_caption_list = ['None', 'Newline', 'Carriage return', 'Both NL & CR']
line_ending_list = ['', '\n', '\r', '\r\n']
display_mode_list = ['Text', 'Ascii', 'Hex']

def getSTVersion():
	ST_version_text = sublime.version()
	ST_version = int(ST_version_text) / 1000
	return ST_version

def getSysPlatform():
	# platform may be "osx", "linux" or "windows"
	sys_platform = sublime.platform()
	return sys_platform

def getSysEncoding():
	sys_platform = getSysPlatform()
	if sys_platform == 'osx':
		sys_encoding = 'utf-8'
	else:
		sys_encoding = codecs.lookup(locale.getpreferredencoding()).name
	return sys_encoding

def getSysLanguage():
	sys_language = locale.getdefaultlocale()[0]
	if not sys_language:
		sys_language = 'en'
	else:
		sys_language = sys_language.lower()
	return sys_language

def getStinoRoot():
	if sys_version < 3:
		stino_root = os.getcwd()
	else:
		for module_key in sys.modules:
			if 'StinoStarter' in module_key:
				stino_module = sys.modules[module_key]
				break
		stino_root = os.path.split(stino_module.__file__)[0]
	return stino_root

ST_version = getSTVersion()
sys_version = int(sys.version[0])
sys_platform = getSysPlatform()
sys_encoding = getSysEncoding()
sys_language = getSysLanguage()

stino_root = getStinoRoot()
app_root = os.path.join(stino_root, 'app')
config_root = os.path.join(stino_root, 'config')
language_root = os.path.join(stino_root, 'language')
compile_root = os.path.join(stino_root, 'compile')

global_settings = preference.Setting(stino_root, 'stino.global_settings')
sketch_settings = preference.Setting(stino_root, 'stino.settings')

serial_in_use_list = []
serial_monitor_dict = {}

########NEW FILE########
__FILENAME__ = fileutil
#-*- coding: utf-8 -*-
# stino/fileutil.py

import sublime
import os
import sys
import codecs
import locale

sys_version = int(sys.version[0])
sys_platform = sublime.platform()

if sys_platform == 'osx':
	sys_encoding = 'utf-8'
else:
	sys_encoding = codecs.lookup(locale.getpreferredencoding()).name

def getWinVolumeList():
	vol_list = []
	for label in range(65, 91):
		vol = chr(label) + ':\\'
		if os.path.isdir(vol):
			vol_list.append(vol)
	return vol_list

def getOSRootList():
	root_list = []
	if sys_platform == 'windows':
		root_list = getWinVolumeList()
	else:
		root_list = ['/']
	return root_list

def getDocumentFolder():
	if sys_platform == 'windows':
		if sys_version < 3:
			import _winreg as winreg
		else:
			import winreg
		key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,\
	            r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',)
		document_folder = winreg.QueryValueEx(key, 'Personal')[0]
	elif sys_platform == 'osx':
		home_folder = os.getenv('HOME')
		document_folder = os.path.join(home_folder, 'Documents')
	else:
		document_folder = os.getenv('HOME')
	return document_folder

def listDir(folder, with_files = True, with_dirs = True):
	if sys_version < 3:
		if not isinstance(folder, unicode):
			folder = folder.decode(sys_encoding)

	file_list = []
	if os.path.isdir(folder):
		try:
			original_file_list = os.listdir(folder)
		except IOError:
			pass
		else:
			for cur_file in original_file_list:
				if cur_file[0] == '$' or cur_file[0] == '.' or cur_file == 'CVS' or '.tmp' in cur_file:
					continue
				cur_file_path = os.path.join(folder, cur_file)
				if os.path.isdir(cur_file_path):
					if with_dirs:
						file_list.append(cur_file)
				else:
					if with_files:
						file_list.append(cur_file)
	file_list.sort()
	return file_list

def enterNextLevel(index, folder_list, level, top_folder_list):
	chosen_folder = folder_list[index]
	chosen_folder = os.path.normpath(chosen_folder)
	if level > 0:
		if index == 1:
			level -= 1
		elif index > 1:
			level += 1
	else:
		level += 1

	if level == 0:
		sub_folder_list = top_folder_list
	else:
		if level == 1 or index > 0:
			try:
				sub_folder_name_list = listDir(chosen_folder, with_files = False)
			except IOError:
				level -= 1
				sub_folder_list = folder_list
			else:
				sub_folder_list = []
				sub_folder_list.append('Select current folder (%s)' % chosen_folder)
				sub_folder_list.append(os.path.join(chosen_folder, '..'))
				for sub_folder_name in sub_folder_name_list:
					sub_folder = os.path.join(chosen_folder, sub_folder_name)
					sub_folder_list.append(sub_folder)
		else:
			sub_folder_list = folder_list
	return (sub_folder_list, level)

def getFolderNameList(folder_list):
	folder_name_list = []
	index = 0
	for folder in folder_list:
		if index == 0:
			folder_name_list.append(folder)
		else:
			folder_name = os.path.split(folder)[1]
			if not folder_name:
				folder_name = folder
			folder_name_list.append(folder_name)
		index += 1

	if sys_version < 3:
		new_list = []
		for folder_name in folder_name_list:
			new_list.append(folder_name)
		folder_name_list = new_list
	return folder_name_list

def getFileListOfExt(folder, ext_list):
	file_list = []
	file_name_list = listDir(folder, with_dirs = False)
	for file_name in file_name_list:
		file_ext = os.path.splitext(file_name)[1]
		if file_ext in ext_list:
			cur_file = os.path.join(folder, file_name)
			file_list.append(cur_file)
	return file_list

def readFile(cur_file, encoding = 'utf-8'):
	text = ''
	if sys_version < 3:
		opened_file = codecs.open(cur_file, 'r', encoding = encoding)
		text = opened_file.read()
		opened_file.close()
	else:
		opened_file = open(cur_file, 'r', encoding = encoding)
		text = opened_file.read()
		opened_file.close()
	return text

def readFileLines(cur_file):
	text =readFile(cur_file)
	lines = text.splitlines(True)
	return lines

def writeFile(cur_file, text, encoding = 'utf-8'):
	if sys_version < 3:
		opened_file = codecs.open(cur_file, 'w', encoding = encoding)
		opened_file.write(text)
		opened_file.close()
	else:
		opened_file = open(cur_file, 'w', encoding = encoding)
		opened_file.write(text)
		opened_file.close()

########NEW FILE########
__FILENAME__ = language
#-*- coding: utf-8 -*-
# stino/language.py

import os
import re

from . import constant
from . import fileutil
from . import textutil

class LanguageItem:
	def __init__(self):
		self.name = ''
		self.en_name = ''
		self.country = ''
		self.file_name = ''
		self.file = ''
	
	def setName(self, name):
		self.name = name

	def setEnName(self, en_name):
		self.en_name = en_name

	def setCountry(self, country):
		self.country = country

	def setFileName(self, file_name):
		self.file_name = file_name

	def setFile(self, lang_file):
		self.file = lang_file

	def getName(self):
		return self.name

	def getEnName(self):
		return self.en_name

	def getCountry(self):
		return self.country

	def getFileName(self):
		return self.file_name

	def getFile(self):
		return self.file

	def getCaption(self):
		if self.country:
			caption = '%s (%s)-%s' % (self.name, self.en_name, self.country)
		else:
			caption = '%s (%s)' % (self.name, self.en_name)
		return caption

class Language:
	def __init__(self):
		self.total_language_filename_list = []
		self.total_language_item_list = []
		self.language_item_list = []
		self.trans_dict = {}
		self.genLanguageItemList()
		self.setDefaultLanguage()
		self.genDefaultTransDict()
		self.genDefaultLangFile()
		self.refresh()

	def refresh(self):
		self.genTransDict()

	def genTotalLanguageItemList(self):
		iso_file = os.path.join(constant.config_root, 'ISO639_1')
		# opened_file = open(iso_file, 'r', encoding='utf-8')
		# lines = opened_file.readlines()
		# opened_file.close()
		lines = fileutil.readFileLines(iso_file)
		for line in lines:
			line = line.strip()
			if line:
				info_list = line.split('=')
				file_name = info_list[0].strip()
				en_name = info_list[1].strip()
				name = info_list[2].strip()
				lang_item = LanguageItem()
				lang_item.setName(name)
				lang_item.setEnName(en_name)
				lang_item.setFileName(file_name)
				self.total_language_item_list.append(lang_item)
				self.total_language_filename_list.append(file_name)

	def getLanguageItemList(self):
		return self.language_item_list

	def genLanguageItemList(self):
		self.genTotalLanguageItemList()
		lang_file_name_list = fileutil.listDir(constant.language_root, with_dirs = False)
		for lang_file_name in lang_file_name_list:
			if lang_file_name in self.total_language_filename_list:
				lang_file = os.path.join(constant.language_root, lang_file_name)
				index = self.total_language_filename_list.index(lang_file_name)
				lang_item = self.total_language_item_list[index]
				lang_item.setFile(lang_file)
				self.language_item_list.append(lang_item)

	def setDefaultLanguage(self):
		chosen_language = constant.global_settings.get('language', -1)
		if chosen_language > -1:
			if chosen_language < len(self.language_item_list):
				return

		for lang_item in self.language_item_list:
			file_name = lang_item.getFileName()
			if file_name == constant.sys_language:
				index = self.language_item_list.index(lang_item)
				constant.global_settings.set('language', index)
				break

	def genDefaultTransDict(self):
		pattern_text = r"translate\('([\S\s]+?)'"
		pattern = re.compile(pattern_text)

		self.trans_dict = {}
		py_starter_file = os.path.join(constant.stino_root, 'StinoStarter.py')
		py_menu_file = os.path.join(constant.app_root, 'menu.py')
		py_file_list = [py_starter_file, py_menu_file]
		for py_file in py_file_list:
			# opened_file = open(py_file, 'r')
			# text = opened_file.read()
			# opened_file.close()
			text = fileutil.readFile(py_file)
			trans_str_list = pattern.findall(text)
			for trans_str in trans_str_list:
				self.trans_dict[trans_str] = trans_str

	def genTransDict(self):
		chosen_language = constant.global_settings.get('language', -1)
		if chosen_language > -1:
			if chosen_language < len(self.language_item_list):
				language_item = self.language_item_list[chosen_language]
				lang_file = language_item.getFile()
				# opened_file = open(lang_file, 'r', encoding='utf-8')
				# lines = opened_file.readlines()
				# opened_file.close()
				lines = fileutil.readFileLines(lang_file)

				block_list = textutil.getBlockList(lines, sep = 'msgid')
				for block in block_list:
					if block:
						for line in block:
							index = line.index('"')
							cur_str = line[index+1:]
							cur_str = cur_str[:-1]
							if 'msgid' in line:
								key = cur_str
							elif 'msgstr' in line:
								value = cur_str
						self.trans_dict[key] = value

	def genDefaultLangFile(self):
		lang_file = os.path.join(constant.language_root, 'default')

		text = '# This file was auto generated. Do not edit this file.\n\n'
		text += '# LANGUAGE: {language} ({language})\n'
		text += '# {language} translations for Stino Plugin.\n'
		text += '# Copyright (C) 2012-2013 Robot-Will\n'
		text += '# This file is distributed under the same license as the Stino Plugin.\n'
		text += '# {translator} {EMAIL@ADDRESS}\n'
		text += '#\n\n'
		for trans_str in self.trans_dict:
			text += 'msgid "%s"\n' % trans_str
			text += 'msgstr "%s"\n\n' % trans_str

		# opened_file = open(lang_file, 'w')
		# opened_file.write(text)
		# opened_file.close()
		fileutil.writeFile(lang_file, text)

	def translate(self, text, para_list = []):
		if text in self.trans_dict:
			text = self.trans_dict[text]
		for para in para_list:
			index = para_list.index(para)
			replaced_text = '{%d}' % index
			text = text.replace(replaced_text, para)
		return text
########NEW FILE########
__FILENAME__ = menu
#-*- coding: utf-8 -*-
# stino/menu.py

import os
import json

from . import constant
from . import fileutil
from . import serial

class MainMenu:
	def __init__(self, language, arduino_info, file_name):
		self.language = language
		self.file = os.path.join(constant.stino_root, file_name)
		self.arduino_info = arduino_info
		self.menu = MenuItem('Main Menu')
		self.refresh()

	def getMenu(self):
		return self.menu

	def printMenu(self):
		printMenu(self.menu)

	def buildMenu(self):
		self.menu = buildMainMenu(self.language, self.arduino_info)

	def genFile(self):
		data = convertMenuToData(self.menu)
		text = json.dumps(data, indent = 4)
		# opened_file = open(self.file, 'w')
		# opened_file.write(text)
		# opened_file.close()
		fileutil.writeFile(self.file, text)

	def refresh(self):
		self.buildMenu()
		self.genFile()

class MenuItem:
	def __init__(self, caption = '-'):
		self.caption = caption
		self.id = caption.lower()
		self.mnemonic = None
		self.children = []
		self.command = None
		self.checkbox = False
		self.args = None

	def hasSubmenu(self):
		state = False
		if self.children:
			state = True
		return state

	def getCaption(self):
		return self.caption

	def getMnemonic(self):
		return self.mnemonic

	def getId(self):
		return self.id

	def getCommand(self):
		return self.command

	def getCheckbox(self):
		return self.checkbox

	def getArgs(self):
		return self.args

	def getSubmenu(self):
		return self.children

	def addMenuItem(self, menu_item):
		self.children.append(menu_item)

	def addMenuGroup(self, menu_group):
		if self.hasSubmenu():
			seperator = MenuItem()
			self.addMenuItem(seperator)
		self.children += menu_group.getGroup()

	def setCaption(self, caption):
		self.caption = caption

	def setMnemonic(self, mnemonic):
		self.mnemonic = mnemonic

	def setId(self, ID):
		self.id = ID

	def setCommand(self, command):
		self.command = command

	def setCheckbox(self):
		self.checkbox = True

	def setArgs(self, args):
		self.args = args

	def getSubmenuItem(caption):
		subitem = None
		for item in self.children:
			if item.getCaption() == caption:
				subitem = item
		return subitem

class MenuItemGroup:
	def __init__(self):
		self.group = []

	def clear(self):
		self.group = []

	def hasMenuItem(self):
		state = False
		if self.group:
			state = True
		return state

	def addMenuItem(self, menu_item):
		self.group.append(menu_item)

	def removeMenuItem(self, menu_item):
		if menu_item in self.group:
			self.group.remove(menu_item)

	def getGroup(self):
		return self.group

def printMenu(menu, level = 0):
	caption = menu.getCaption()
	if level > 0:
		caption = '\t' * level + '|__' + caption
	print(caption)

	if menu.hasSubmenu():
		for submenu in menu.getSubmenu():
			printMenu(submenu, level+1)

def buildMenuFromSketch(sketch):
	name = sketch.getName()
	cur_menu = MenuItem(name)
	if sketch.hasSubItem():
		for sub_sketch in sketch.getSubItemList():
			sub_menu_item = buildMenuFromSketch(sub_sketch)
			cur_menu.addMenuItem(sub_menu_item)
	else:
		folder = sketch.getFolder()
		if folder:
			command = 'open_sketch'
			args = {'folder' : folder}
			cur_menu.setCommand(command)
			cur_menu.setArgs(args)
	return cur_menu

def buildSketchbookMenu(language, arduino_info):
	sketchbook = arduino_info.getSketchbook()
	sketchbook.setName(language.translate('Sketchbook'))
	sketchbook_menu = buildMenuFromSketch(sketchbook)
	return sketchbook_menu

def buildLibraryMenu(language, arduino_info):
	library_menu = MenuItem(language.translate('Import Library'))
	platform_list = arduino_info.getPlatformList()
	for platform in platform_list:
		name = platform.getName()
		sub_menu_item = MenuItem(name)
		lib_list = platform.getLibList()
		for lib in lib_list:
			lib_name = lib.getName()
			lib_menu_item = MenuItem(lib_name)
			lib_folder = lib.getFolder()
			command = 'import_library'
			lib_args = {'folder' : lib_folder}
			lib_menu_item.setCommand(command)
			lib_menu_item.setArgs(lib_args)
			sub_menu_item.addMenuItem(lib_menu_item)
		library_menu.addMenuItem(sub_menu_item)
	return library_menu

def buildExampleMenu(language, arduino_info):
	example_menu = MenuItem(language.translate('Examples'))
	platform_list = arduino_info.getPlatformList()
	for platform in platform_list:
		cur_example = platform.getExample()
		sub_menu_item = buildMenuFromSketch(cur_example)
		example_menu.addMenuItem(sub_menu_item)
	return example_menu

def buildBoardMenuList(arduino_info):
	board_menu_list = []
	platform_list = arduino_info.getPlatformList()
	for platform in platform_list:
		platform_id = platform_list.index(platform)
		name = platform.getName()
		board_menu = MenuItem(name)
		board_list = platform.getBoardList()
		if board_list:
			for cur_board in board_list:
				board_id = board_list.index(cur_board)
				board_name = cur_board.getName()
				board_menu_item = MenuItem(board_name)
				command = 'choose_board'
				board_args = {'platform' : platform_id, 'board': board_id}
				board_menu_item.setCommand(command)
				board_menu_item.setArgs(board_args)
				board_menu_item.setCheckbox()
				board_menu.addMenuItem(board_menu_item)
			board_menu_list.append(board_menu)
	return board_menu_list

def buildBoardOptionMenuList(arduino_info):
	board_option_menu_list = []
	platform_id = constant.sketch_settings.get('platform', -1)
	board_id = constant.sketch_settings.get('board', -1)
	if platform_id > -1:
		platform_list = arduino_info.getPlatformList()
		if platform_id < len(platform_list):
			platform = platform_list[platform_id]
			board_list = platform.getBoardList()
			if board_id < len(board_list):
				board = board_list[board_id]
				board_option_list = board.getOptionList()
				for board_option in board_option_list:
					board_option_id = board_option_list.index(board_option)
					board_option_name = board_option.getName()
					board_option_menu = MenuItem(board_option_name)
					board_option_item_list = board_option.getItemList()
					for board_option_item in board_option_item_list:
						board_option_item_id = board_option_item_list.index(board_option_item)
						board_option_item_name = board_option_item.getName()
						board_option_item_menu = MenuItem(board_option_item_name)
						command = 'choose_board_option'
						args = {'board_option' : board_option_id, 'board_option_item' : board_option_item_id}
						board_option_item_menu.setCommand(command)
						board_option_item_menu.setArgs(args)
						board_option_item_menu.setCheckbox()
						board_option_menu.addMenuItem(board_option_item_menu)
					board_option_menu_list.append(board_option_menu)
	return board_option_menu_list

def buildProgrammerMenu(language, arduino_info):
	programmer_menu = MenuItem(language.translate('Programmer'))
	platform_id = chosen_platform = constant.sketch_settings.get('platform', -1)
	if platform_id > -1:
		platform_list = arduino_info.getPlatformList()
		if platform_id < len(platform_list):
			platform = platform_list[platform_id]

			programmer_list = platform.getProgrammerList()
			if programmer_list:
				for cur_programmer in programmer_list:
					programmer_id = programmer_list.index(cur_programmer)
					programmer_name = cur_programmer.getName()
					programmer_menu_item = MenuItem(programmer_name)
					command = 'choose_programmer'
					programmer_args = {'platform' : platform_id, 'programmer': programmer_id}
					programmer_menu_item.setCommand(command)
					programmer_menu_item.setArgs(programmer_args)
					programmer_menu_item.setCheckbox()
					programmer_menu.addMenuItem(programmer_menu_item)
	return programmer_menu

def buildSerialPortMenu(language):
	serial_port_menu = MenuItem(language.translate('Serial Port'))

	serial_port_list = serial.getSerialPortList()
	for serial_port in serial_port_list:
		serial_port_item = MenuItem(serial_port)
		index = serial_port_list.index(serial_port)
		args = {'serial_port' : index}
		serial_port_item.setCommand('choose_serial_port')
		serial_port_item.setArgs(args)
		serial_port_item.setCheckbox()
		serial_port_menu.addMenuItem(serial_port_item)
	return serial_port_menu

def buildLineEndingMenu(language):
	line_ending_menu = MenuItem(language.translate('Line Ending'))
	for line_ending_caption in constant.line_ending_caption_list:
		sub_menu = MenuItem(line_ending_caption)
		line_ending_caption_id = constant.line_ending_caption_list.index(line_ending_caption)
		args = {'line_ending' : line_ending_caption_id}
		sub_menu.setCommand('choose_line_ending')
		sub_menu.setArgs(args)
		sub_menu.setCheckbox()
		line_ending_menu.addMenuItem(sub_menu)
	return line_ending_menu

def buildDisplayModeMenu(language):
	display_mode_menu = MenuItem(language.translate('Display as'))
	for display_mode in constant.display_mode_list:
		sub_menu = MenuItem(display_mode)
		display_mode_id = constant.display_mode_list.index(display_mode)
		args = {'display_mode' : display_mode_id}
		sub_menu.setCommand('choose_display_mode')
		sub_menu.setArgs(args)
		sub_menu.setCheckbox()
		display_mode_menu.addMenuItem(sub_menu)
	return display_mode_menu

def buildBaudrateMenu(language):
	baudrate_menu = MenuItem(language.translate('Baudrate'))
	for baudrate in constant.baudrate_list:
		sub_menu = MenuItem(baudrate)
		baudrate_id = constant.baudrate_list.index(baudrate)
		args = {'baudrate' : baudrate_id}
		sub_menu.setCommand('choose_baudrate')
		sub_menu.setArgs(args)
		sub_menu.setCheckbox()
		baudrate_menu.addMenuItem(sub_menu)
	return baudrate_menu

def buildSerialMonitorMenu(language):
	serial_monitor_menu = MenuItem(language.translate('Serial Monitor'))
	start_menu = MenuItem(language.translate('Start'))
	start_menu.setCommand('start_serial_monitor')
	stop_menu = MenuItem(language.translate('Stop'))
	stop_menu.setCommand('stop_serial_monitor')
	send_menu = MenuItem(language.translate('Send'))
	send_menu.setCommand('send_serial_text')
	line_ending_menu = buildLineEndingMenu(language)
	display_mode_menu = buildDisplayModeMenu(language)
	baudrate_menu = buildBaudrateMenu(language)
	serial_monitor_menu.addMenuItem(start_menu)
	serial_monitor_menu.addMenuItem(stop_menu)
	serial_monitor_menu.addMenuItem(send_menu)
	serial_monitor_menu.addMenuItem(baudrate_menu)
	serial_monitor_menu.addMenuItem(line_ending_menu)
	serial_monitor_menu.addMenuItem(display_mode_menu)
	return serial_monitor_menu

def buildLanguageMenu(language):
	language_menu = MenuItem(language.translate('Language'))

	language_item_list = language.getLanguageItemList()
	for language_item in language_item_list:
		caption = language_item.getCaption()
		language_menu_item = MenuItem(caption)
		index = language_item_list.index(language_item)
		args = {'language' : index}
		language_menu_item.setCommand('choose_language')
		language_menu_item.setArgs(args)
		language_menu_item.setCheckbox()
		language_menu.addMenuItem(language_menu_item)
	return language_menu

def buildSettingMenu(language):
	setting_menu = MenuItem(language.translate('Preferences'))

	select_arduino_folder_menu = MenuItem(language.translate('Select Arduino Application Folder'))
	select_arduino_folder_menu.setCommand('choose_arduino_folder')

	change_sketchbook_folder_menu = MenuItem(language.translate('Change Sketchbook Folder'))
	change_sketchbook_folder_menu.setCommand('change_sketchbook_folder')

	change_build_folder_menu = MenuItem(language.translate('Select Build Folder'))
	change_build_folder_menu.setCommand('choose_build_folder')


	language_menu = buildLanguageMenu(language)

	setting_menu.addMenuItem(select_arduino_folder_menu)
	setting_menu.addMenuItem(change_sketchbook_folder_menu)
	setting_menu.addMenuItem(change_build_folder_menu)
	setting_menu.addMenuItem(language_menu)
	return setting_menu

def buildReferenceMenu(language):
	references_menu = MenuItem(language.translate('References'))
	getting_started_menu = MenuItem(language.translate('Getting Started'))
	getting_started_menu.setCommand('open_ref')
	args = {'url': 'Guide_index'}
	getting_started_menu.setArgs(args)

	troubleshooting_menu = MenuItem(language.translate('Troubleshooting'))
	troubleshooting_menu.setCommand('open_ref')
	args = {'url': 'Guide_Troubleshooting'}
	troubleshooting_menu.setArgs(args)

	ref_menu = MenuItem(language.translate('Reference'))
	ref_menu.setCommand('open_ref')
	args = {'url': 'index'}
	ref_menu.setArgs(args)

	find_menu = MenuItem(language.translate('Find in Reference'))
	find_menu.setCommand('find_in_reference')

	faq_menu = MenuItem(language.translate('Frequently Asked Questions'))
	faq_menu.setCommand('open_ref')
	args = {'url': 'FAQ'}
	faq_menu.setArgs(args)

	website_menu = MenuItem(language.translate('Visit Arduino Website'))
	website_menu.setCommand('open_url')
	args = {'url': 'http://arduino.cc'}
	website_menu.setArgs(args)

	references_menu.addMenuItem(getting_started_menu)
	references_menu.addMenuItem(troubleshooting_menu)
	references_menu.addMenuItem(ref_menu)
	references_menu.addMenuItem(find_menu)
	references_menu.addMenuItem(faq_menu)
	references_menu.addMenuItem(website_menu)
	return references_menu

def buildSketchMenuGroup(language, arduino_info):
	new_sketch_menu = MenuItem(language.translate('New Sketch'))
	new_sketch_menu.setCommand('new_sketch')

	sketch_menu_group = MenuItemGroup()
	sketchbook_menu = buildSketchbookMenu(language, arduino_info)
	examples_menu = buildExampleMenu(language, arduino_info)

	sketch_menu_group.addMenuItem(new_sketch_menu)
	sketch_menu_group.addMenuItem(sketchbook_menu)
	sketch_menu_group.addMenuItem(examples_menu)
	return sketch_menu_group

def buildLibraryMenuGroup(language, arduino_info):
	library_menu_group = MenuItemGroup()
	import_lib_menu = buildLibraryMenu(language, arduino_info)

	show_sketch_folder_menu = MenuItem(language.translate('Show Sketch Folder'))
	show_sketch_folder_menu.setCommand('show_sketch_folder')
	library_menu_group.addMenuItem(import_lib_menu)
	library_menu_group.addMenuItem(show_sketch_folder_menu)
	return library_menu_group

def buildDebugMenuGroup(language):
	debug_menu_group = MenuItemGroup()
	extra_flag_menu = MenuItem(language.translate('Extra Flags'))
	extra_flag_menu.setCommand('set_extra_flag')

	compile_menu = MenuItem(language.translate('Verify/Compile'))
	compile_menu.setCommand('compile_sketch')

	upload_menu = MenuItem(language.translate('Upload'))
	upload_menu.setCommand('upload_sketch')

	programmer_upload_menu = MenuItem(language.translate('Upload by Using Programmer'))
	programmer_upload_menu.setCommand('upload_using_programmer')

	debug_menu_group.addMenuItem(extra_flag_menu)
	debug_menu_group.addMenuItem(compile_menu)
	debug_menu_group.addMenuItem(upload_menu)
	debug_menu_group.addMenuItem(programmer_upload_menu)
	return debug_menu_group

def buildBoardMenuGroup(arduino_info):
	board_menu_group = MenuItemGroup()
	board_menu_list = buildBoardMenuList(arduino_info)
	board_option_menu_list = buildBoardOptionMenuList(arduino_info)
	sub_menu_list = board_menu_list + board_option_menu_list
	for sub_menu in sub_menu_list:
		board_menu_group.addMenuItem(sub_menu)
	return board_menu_group

def buildProgrammerMenuGroup(language, arduino_info):
	programmer_menu_group = MenuItemGroup()
	programmer_menu = buildProgrammerMenu(language, arduino_info)
	programmer_menu_group.addMenuItem(programmer_menu)

	burn_bootloader_menu = MenuItem(language.translate('Burn Bootloader'))
	burn_bootloader_menu.setCommand('burn_bootloader')
	programmer_menu_group.addMenuItem(burn_bootloader_menu)
	return programmer_menu_group

def buildSerialMenuGroup(language):
	serial_menu_group = MenuItemGroup()
	serial_port_menu = buildSerialPortMenu(language)
	serial_monitor_menu = buildSerialMonitorMenu(language)
	serial_menu_group.addMenuItem(serial_port_menu)
	serial_menu_group.addMenuItem(serial_monitor_menu)
	return serial_menu_group

def buildToolsMenuGroup(language):
	tools_menu_group = MenuItemGroup()
	auto_format_menu = MenuItem(language.translate('Auto Format'))
	auto_format_menu.setCommand('auto_format')

	archive_sketch_menu = MenuItem(language.translate('Archive Sketch'))
	archive_sketch_menu.setCommand('archive_sketch')

	tools_menu_group.addMenuItem(auto_format_menu)
	tools_menu_group.addMenuItem(archive_sketch_menu)
	return tools_menu_group

def buildSettingMenuGroup(language):
	setting_menu_group = MenuItemGroup()
	setting_menu = buildSettingMenu(language)

	global_setting_menu = MenuItem(language.translate('Global Setting'))
	global_setting_menu.setCommand('set_global_setting')
	global_setting_menu.setCheckbox()

	full_compilation_menu = MenuItem(language.translate('Full Compilation'))
	full_compilation_menu.setCommand('set_full_compilation')
	full_compilation_menu.setCheckbox()


	bare_gcc_only_menu = MenuItem(language.translate('Bare GCC Build (No Arduino code-munging)'))
	bare_gcc_only_menu.setCommand('set_bare_gcc_only')
	bare_gcc_only_menu.setCheckbox()

	show_compilation_menu = MenuItem(language.translate('Compilation'))
	show_compilation_menu.setCommand('show_compilation_output')
	show_compilation_menu.setCheckbox()

	show_upload_menu = MenuItem(language.translate('Upload'))
	show_upload_menu.setCommand('show_upload_output')
	show_upload_menu.setCheckbox()

	show_verbose_output_menu = MenuItem(language.translate('Show Verbose Output'))
	show_verbose_output_menu.addMenuItem(show_compilation_menu)
	show_verbose_output_menu.addMenuItem(show_upload_menu)

	verify_code_menu = MenuItem(language.translate('Verify Code after Upload'))
	verify_code_menu.setCommand('verify_code')
	verify_code_menu.setCheckbox()

	setting_menu_group.addMenuItem(setting_menu)
	setting_menu_group.addMenuItem(global_setting_menu)
	setting_menu_group.addMenuItem(bare_gcc_only_menu)
	setting_menu_group.addMenuItem(full_compilation_menu)
	setting_menu_group.addMenuItem(show_verbose_output_menu)
	setting_menu_group.addMenuItem(verify_code_menu)
	return setting_menu_group

def buildHelpMenuGroup(language):
	help_menu_group = MenuItemGroup()
	references_menu = buildReferenceMenu(language)
	about_menu = MenuItem(language.translate('About Stino'))
	about_menu.setCommand('about_stino')

	help_menu_group.addMenuItem(references_menu)
	help_menu_group.addMenuItem(about_menu)
	return help_menu_group

# Build Main Menu
def buildPreferenceMenu(language):
	preference_menu = MenuItem('Preferences')
	preference_menu.setMnemonic('n')

	show_arduino_menu = MenuItem(language.translate('Show Arduino Menu'))
	show_arduino_menu.setCommand('show_arduino_menu')
	show_arduino_menu.setCheckbox()


	preference_menu.addMenuItem(show_arduino_menu)
	return preference_menu

def buildArduinoMenu(language, arduino_info):
	arduino_menu = MenuItem('Arduino')
	sketch_menu_group = buildSketchMenuGroup(language, arduino_info)
	library_menu_group = buildLibraryMenuGroup(language, arduino_info)
	debug_menu_group = buildDebugMenuGroup(language)
	board_menu_group = buildBoardMenuGroup(arduino_info)
	programmer_menu_group = buildProgrammerMenuGroup(language, arduino_info)
	serial_menu_group = buildSerialMenuGroup(language)
	tools_menu_group = buildToolsMenuGroup(language)
	setting_menu_group = buildSettingMenuGroup(language)
	help_menu_group = buildHelpMenuGroup(language)

	arduino_menu.addMenuGroup(sketch_menu_group)
	arduino_menu.addMenuGroup(library_menu_group)
	arduino_menu.addMenuGroup(debug_menu_group)
	arduino_menu.addMenuGroup(board_menu_group)
	arduino_menu.addMenuGroup(programmer_menu_group)
	arduino_menu.addMenuGroup(serial_menu_group)
	arduino_menu.addMenuGroup(tools_menu_group)
	arduino_menu.addMenuGroup(setting_menu_group)
	arduino_menu.addMenuGroup(help_menu_group)
	return arduino_menu

def buildMainMenu(language, arduino_info):
	main_menu = MenuItem('Main Menu')

	show_arduino_menu = constant.global_settings.get('show_arduino_menu', True)
	preference_menu = buildPreferenceMenu(language)
	main_menu.addMenuItem(preference_menu)

	if show_arduino_menu:
		arduino_menu = buildArduinoMenu(language, arduino_info)
		main_menu.addMenuItem(arduino_menu)
	return main_menu

def convertMenuToData(cur_menu, level = 0):
	caption = cur_menu.getCaption()
	sub_menu_list = cur_menu.getSubmenu()
	if sub_menu_list:
		sub_data_list = []
		for sub_menu in sub_menu_list:
			sub_data = convertMenuToData(sub_menu, level + 1)
			if sub_data:
				sub_data_list.append(sub_data)
		if level > 0:
			menu_id = cur_menu.getId()
			menu_mnemonic = cur_menu.getMnemonic()
			data = {}
			data['caption'] = caption
			data['id'] = menu_id
			data['mnemonic'] = menu_mnemonic
			data['children'] = sub_data_list
		else:
			data = sub_data_list
	else:
		data = {}
		command = cur_menu.getCommand()
		if command or caption == '-':
			args = cur_menu.getArgs()
			checkbox = cur_menu.getCheckbox()
			data['caption'] = caption
			data['command'] = command
			if args:
				data['args'] = args
			if checkbox:
				data['checkbox'] = checkbox
	return data


########NEW FILE########
__FILENAME__ = preference
#-*- coding: utf-8 -*-
# stino/preference.py

import os
import sys
import json

import sublime

from . import fileutil

sys_version = int(sys.version[0])

def getStinoRoot():
	if sys_version < 3:
		stino_root = os.getcwd()
	else:
		for module_key in sys.modules:
			if 'StinoStarter' in module_key:
				stino_module = sys.modules[module_key]
				break
		stino_root = os.path.split(stino_module.__file__)[0]
	return stino_root

def getStPackageRoot():
	st_packages_folder = sublime.packages_path()
	if not st_packages_folder:
		stino_folder = getStinoRoot()
		st_data_folder = stino_folder.split('Data')[-1]
		st_data_folder = stino_folder.split(st_data_folder)[0]
		st_packages_folder = os.path.join(st_data_folder, 'Packages')
	return st_packages_folder

class Setting:
	def __init__(self, default_folder, file_name):
		self.settings_dict = {}
		self.default_folder = default_folder
		self.file_name = file_name
		self.default_file = os.path.join(default_folder, file_name)
		self.file = self.default_file
		self.loadSettingsFile()

	def loadSettingsFile(self):
		if os.path.isfile(self.file):
			text = fileutil.readFile(self.file)
			self.settings_dict = json.loads(text)

	def saveSettingsFile(self):
		text = json.dumps(self.settings_dict, sort_keys = True, indent = 4)
		fileutil.writeFile(self.file, text)

	def get(self, key, default_value = None):
		if key in self.settings_dict:
			value = self.settings_dict[key]
		else:
			value = default_value

		try:
			value + 'string'
		except TypeError:
			pass
		else:
			stino_folder = getStinoRoot()
			st_package_folder = getStPackageRoot()
			value = value.replace('${stino_root}', stino_folder)
			value = value.replace('${packages}', st_package_folder)
		return value

	def set(self, key, value):
		self.settings_dict[key] = value
		self.saveSettingsFile()

	def changeFolder(self, folder):
		if not os.path.isdir(folder):
			self.file = self.default_file
		else:
			self.file = os.path.join(folder, self.file_name)

		if os.path.isfile(self.file):
			self.loadSettingsFile()
		else:
			self.saveSettingsFile()
########NEW FILE########
__FILENAME__ = preprocess
#-*- coding: utf-8 -*-
# stino/preprocess.py

import re

from . import fileutil

c_keyword_list = ['if', 'elif', 'else', 'while', 'for', 'switch', 'case']

def getPatternList(src_text, pattern_text):
	pattern = re.compile(pattern_text, re.M|re.S)
	pattern_list = pattern.findall(src_text)
	return pattern_list

def getSingleLineCommentList(src_text):
	pattern_text = r'//.*?$'
	comment_list = getPatternList(src_text, pattern_text)
	return comment_list

def getMultiLineCommentList(src_text):
	pattern_text = r'/\*.*?\*/'
	comment_list = getPatternList(src_text, pattern_text)
	return comment_list

def getStringList(src_text):
	pattern_text = r'"(?:[^"\\"]|\\.)*?"' # double-quoted string
	string_list = getPatternList(src_text, pattern_text)
	return string_list

def getPreProcessorList(src_text):
	pattern_text = r'^#.*?$' # pre-processor directive
	pre_processor_list = getPatternList(src_text, pattern_text)
	return pre_processor_list

def getIncludeList(src_text):
	pattern_text = r'#include\s+?["<]\S+?[>"]'
	include_list = getPatternList(src_text, pattern_text)
	return include_list

def getDeclarationList(src_text):
	pattern_text = r'^\s*[\w\[\]\*]+\s+[&\[\]\*\w\s]+\([&,\[\]\*\w\s]*\)(?=\s*?;)'
	declaration_list = getPatternList(src_text, pattern_text)
	return declaration_list

def getFunctionList(src_text):
	pattern_text = r'^\s*([\w\[\]\*]+\s+[&\[\]\*\w\s]+\([&,\[\]\*\w\s]*\))(?=\s*?\{)'
	function_list = getPatternList(src_text, pattern_text)
	return function_list

def removeCertainTypeText(src_text, cur_type):
	if cur_type == 'single-comment':
		text_list = getSingleLineCommentList(src_text)
	elif cur_type == 'multi-comment':
		text_list = getMultiLineCommentList(src_text)
	elif cur_type == 'string':
		text_list = getStringList(src_text)
	text_list.sort(key=lambda x:len(x))
	text_list.reverse()
	for text in text_list:
		src_text = src_text.replace(text, '')
	return src_text

def genFunctionList(src_text):
	function_list = []
	src_text = removeCertainTypeText(src_text, 'multi-comment')
	src_text = removeCertainTypeText(src_text, 'single-comment')
	src_text = removeCertainTypeText(src_text, 'string')
	org_func_list = getFunctionList(src_text)
	for org_func in org_func_list:
		is_not_function = False
		word_list = re.findall(r'\b\w+\b', org_func)
		for word in word_list:
			if word in c_keyword_list:
				is_not_function = True
				break
		if is_not_function:
			continue
		else:
			function_list.append(org_func)
	return function_list

def splitSrcText(src_text):
	function_list = genFunctionList(src_text)
	if function_list:
		first_function = function_list[0]
		index = src_text.index(first_function)
		src_text_header = src_text[:index]
		src_text_body = src_text[index:]
	else:
		src_text_header = src_text
		src_text_body = ''
	return (src_text_header, src_text_body)

def genIncludeList(src_text):
	src_text = removeCertainTypeText(src_text, 'multi-comment')
	src_text = removeCertainTypeText(src_text, 'single-comment')
	include_list = getIncludeList(src_text)
	return include_list

def getHList(src_text):
	pattern_text = r'#include\s+?["<](\S+?)[>"]'
	h_list = getPatternList(src_text, pattern_text)
	return h_list

def genHList(src_text):
	src_text = removeCertainTypeText(src_text, 'single-comment')
	src_text = removeCertainTypeText(src_text, 'multi-comment')
	h_list = getHList(src_text)
	return h_list

def isMainSrcFile(src_file):
	state = False
	src_text = fileutil.readFile(src_file)

	has_setup = False
	has_loop = False
	function_list = genFunctionList(src_text)
	for function in function_list:
		if 'setup' in function:
			has_setup = True
		if 'loop' in function:
			has_loop = True
	if has_setup and has_loop:
		state = True
	return state

def getMainSrcFile(src_file_list):
	main_src_file = src_file_list[0]
	for src_file in src_file_list:
		if isMainSrcFile(src_file):
			main_src_file = src_file
			break
	return main_src_file

def sortSrcFileList(src_file_list):
	main_src_file = getMainSrcFile(src_file_list)
	src_file_list.remove(main_src_file)
	new_file_list = [main_src_file] + src_file_list
	return new_file_list

def genFunctionListFromFile(src_file):
	text = fileutil.readFile(src_file)
	function_list = genFunctionList(text)
	return function_list

def genFunctionListFromSrcList(src_file_list):
	function_list = []
	for src_file in src_file_list:
		function_list += genFunctionListFromFile(src_file)
	return function_list

def getInsertText(src_file_list):
	insert_text = '\n'
	function_list = genFunctionListFromSrcList(src_file_list)

	for function in function_list:
		if (' setup' in function) or (' loop' in function):
			continue
		insert_text += '%s;\n' % function
	insert_text += '\n'
	return insert_text

def genCppFileFromInoFileList(cpp_file, ino_src_file_list, arduino_version, preprocess=True):
	cpp_text = ''

	if preprocess:
		if arduino_version < 100:
			include_text = '#include <WProgram.h>\n'
		else:
			include_text = '#include <Arduino.h>\n'

		cpp_text += include_text

		if ino_src_file_list:
			insert_text = getInsertText(ino_src_file_list)
			main_src_file = ino_src_file_list[0]
			src_text = fileutil.readFile(main_src_file)

			function_list = genFunctionList(src_text)
			if function_list:
				first_function = function_list[0]
				index = src_text.index(first_function)
				header_text = src_text[:index]
				body_text = src_text[index:]
			else:
				index = len(src_text)
				header_text = src_text
				body_text = ''

			cpp_text += header_text
			cpp_text += insert_text
			cpp_text += body_text

			for src_file in ino_src_file_list[1:]:
				src_text = fileutil.readFile(src_file)
				cpp_text += src_text

	# Don't do any preprocessing at all
	else:

		if len(ino_src_file_list) != 1:
			raise ValueError("Too many source files! Only one \".ino\" file is supported")

		main_src_file = ino_src_file_list[0]
		cpp_text = fileutil.readFile(main_src_file)

	fileutil.writeFile(cpp_file, cpp_text)

def getHListFromSrcList(ino_src_list):
	h_list = []
	for ino_src in ino_src_list:
		text = fileutil.readFile(ino_src)
		h_list += genHList(text)
	return h_list

########NEW FILE########
__FILENAME__ = serialposix
#!/usr/bin/env python
#
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# module for serial IO for POSIX compatible systems, like Linux
# see __init__.py
#
# (C) 2001-2010 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# parts based on code from Grant B. Edwards  <grante@visi.com>:
#  ftp://ftp.visi.com/users/grante/python/PosixSerial.py
#
# references: http://www.easysw.com/~mike/serial/serial.html

import sys, os, fcntl, termios, struct, select, errno, time
from .serialutil import *

# Do check the Python version as some constants have moved.
if (sys.hexversion < 0x020100f0):
    import TERMIOS
else:
    TERMIOS = termios

if (sys.hexversion < 0x020200f0):
    import FCNTL
else:
    FCNTL = fcntl

# try to detect the OS so that a device can be selected...
# this code block should supply a device() and set_special_baudrate() function
# for the platform
plat = sys.platform.lower()

if   plat[:5] == 'linux':    # Linux (confirmed)

    def device(port):
        return '/dev/ttyS%d' % port

    ASYNC_SPD_MASK = 0x1030
    ASYNC_SPD_CUST = 0x0030

    def set_special_baudrate(port, baudrate):
        import array
        buf = array.array('i', [0] * 32)

        # get serial_struct
        FCNTL.ioctl(port.fd, TERMIOS.TIOCGSERIAL, buf)

        # set custom divisor
        buf[6] = buf[7] / baudrate

        # update flags
        buf[4] &= ~ASYNC_SPD_MASK
        buf[4] |= ASYNC_SPD_CUST

        # set serial_struct
        try:
            res = FCNTL.ioctl(port.fd, TERMIOS.TIOCSSERIAL, buf)
        except IOError:
            raise ValueError('Failed to set custom baud rate: %r' % baudrate)

    baudrate_constants = {
        0:       0,  # hang up
        50:      1,
        75:      2,
        110:     3,
        134:     4,
        150:     5,
        200:     6,
        300:     7,
        600:     10,
        1200:    11,
        1800:    12,
        2400:    13,
        4800:    14,
        9600:    15,
        19200:   16,
        38400:   17,
        57600:   10001,
        115200:  10002,
        230400:  10003,
        460800:  10004,
        500000:  10005,
        576000:  10006,
        921600:  10007,
        1000000: 10010,
        1152000: 10011,
        1500000: 10012,
        2000000: 10013,
        2500000: 10014,
        3000000: 10015,
        3500000: 10016,
        4000000: 10017
    }

elif plat == 'cygwin':       # cygwin/win32 (confirmed)

    def device(port):
        return '/dev/com%d' % (port + 1)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat == 'openbsd3':    # BSD (confirmed)

    def device(port):
        return '/dev/ttyp%d' % port

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:3] == 'bsd' or  \
     plat[:7] == 'freebsd' or \
     plat[:7] == 'openbsd':  # BSD (confirmed for freebsd4: cuaa%d)

    def device(port):
        return '/dev/cuad%d' % port

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:6] == 'darwin':   # OS X

    version = os.uname()[2].split('.')
    # Tiger or above can support arbitrary serial speeds
    if int(version[0]) >= 8:
        def set_special_baudrate(port, baudrate):
            # use IOKit-specific call to set up high speeds
            import array, fcntl
            buf = array.array('i', [baudrate])
            IOSSIOSPEED = 0x80045402 #_IOW('T', 2, speed_t)
            fcntl.ioctl(port.fd, IOSSIOSPEED, buf, 1)
    else: # version < 8
        def set_special_baudrate(port, baudrate):
            raise ValueError("baud rate not supported")

    def device(port):
        return '/dev/cuad%d' % port

    baudrate_constants = {}


elif plat[:6] == 'netbsd':   # NetBSD 1.6 testing by Erk

    def device(port):
        return '/dev/dty%02d' % port

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:4] == 'irix':     # IRIX (partially tested)

    def device(port):
        return '/dev/ttyf%d' % (port+1) #XXX different device names depending on flow control

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:2] == 'hp':       # HP-UX (not tested)

    def device(port):
        return '/dev/tty%dp0' % (port+1)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:5] == 'sunos':    # Solaris/SunOS (confirmed)

    def device(port):
        return '/dev/tty%c' % (ord('a')+port)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

elif plat[:3] == 'aix':      # AIX

    def device(port):
        return '/dev/tty%d' % (port)

    def set_special_baudrate(port, baudrate):
        raise ValueError("sorry don't know how to handle non standard baud rate on this platform")

    baudrate_constants = {}

else:
    # platform detection has failed...
    sys.stderr.write("""\
don't know how to number ttys on this system.
! Use an explicit path (eg /dev/ttyS1) or send this information to
! the author of this module:

sys.platform = %r
os.name = %r
serialposix.py version = %s

also add the device name of the serial port and where the
counting starts for the first serial port.
e.g. 'first serial port: /dev/ttyS0'
and with a bit luck you can get this module running...
""" % (sys.platform, os.name, VERSION))
    # no exception, just continue with a brave attempt to build a device name
    # even if the device name is not correct for the platform it has chances
    # to work using a string with the real device name as port parameter.
    def device(portum):
        return '/dev/ttyS%d' % portnum
    def set_special_baudrate(port, baudrate):
        raise SerialException("sorry don't know how to handle non standard baud rate on this platform")
    baudrate_constants = {}
    #~ raise Exception, "this module does not run on this platform, sorry."

# whats up with "aix", "beos", ....
# they should work, just need to know the device names.


# load some constants for later use.
# try to use values from TERMIOS, use defaults from linux otherwise
TIOCMGET  = hasattr(TERMIOS, 'TIOCMGET') and TERMIOS.TIOCMGET or 0x5415
TIOCMBIS  = hasattr(TERMIOS, 'TIOCMBIS') and TERMIOS.TIOCMBIS or 0x5416
TIOCMBIC  = hasattr(TERMIOS, 'TIOCMBIC') and TERMIOS.TIOCMBIC or 0x5417
TIOCMSET  = hasattr(TERMIOS, 'TIOCMSET') and TERMIOS.TIOCMSET or 0x5418

#TIOCM_LE = hasattr(TERMIOS, 'TIOCM_LE') and TERMIOS.TIOCM_LE or 0x001
TIOCM_DTR = hasattr(TERMIOS, 'TIOCM_DTR') and TERMIOS.TIOCM_DTR or 0x002
TIOCM_RTS = hasattr(TERMIOS, 'TIOCM_RTS') and TERMIOS.TIOCM_RTS or 0x004
#TIOCM_ST = hasattr(TERMIOS, 'TIOCM_ST') and TERMIOS.TIOCM_ST or 0x008
#TIOCM_SR = hasattr(TERMIOS, 'TIOCM_SR') and TERMIOS.TIOCM_SR or 0x010

TIOCM_CTS = hasattr(TERMIOS, 'TIOCM_CTS') and TERMIOS.TIOCM_CTS or 0x020
TIOCM_CAR = hasattr(TERMIOS, 'TIOCM_CAR') and TERMIOS.TIOCM_CAR or 0x040
TIOCM_RNG = hasattr(TERMIOS, 'TIOCM_RNG') and TERMIOS.TIOCM_RNG or 0x080
TIOCM_DSR = hasattr(TERMIOS, 'TIOCM_DSR') and TERMIOS.TIOCM_DSR or 0x100
TIOCM_CD  = hasattr(TERMIOS, 'TIOCM_CD') and TERMIOS.TIOCM_CD or TIOCM_CAR
TIOCM_RI  = hasattr(TERMIOS, 'TIOCM_RI') and TERMIOS.TIOCM_RI or TIOCM_RNG
#TIOCM_OUT1 = hasattr(TERMIOS, 'TIOCM_OUT1') and TERMIOS.TIOCM_OUT1 or 0x2000
#TIOCM_OUT2 = hasattr(TERMIOS, 'TIOCM_OUT2') and TERMIOS.TIOCM_OUT2 or 0x4000
TIOCINQ   = hasattr(TERMIOS, 'FIONREAD') and TERMIOS.FIONREAD or 0x541B

TIOCM_zero_str = struct.pack('I', 0)
TIOCM_RTS_str = struct.pack('I', TIOCM_RTS)
TIOCM_DTR_str = struct.pack('I', TIOCM_DTR)

TIOCSBRK  = hasattr(TERMIOS, 'TIOCSBRK') and TERMIOS.TIOCSBRK or 0x5427
TIOCCBRK  = hasattr(TERMIOS, 'TIOCCBRK') and TERMIOS.TIOCCBRK or 0x5428


class PosixSerial(SerialBase):
    """Serial port class POSIX implementation. Serial port configuration is 
    done with termios and fcntl. Runs on Linux and many other Un*x like
    systems."""

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        self.fd = None
        # open
        try:
            self.fd = os.open(self.portstr, os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        except Exception as msg:
            self.fd = None
            raise SerialException("could not open port %s: %s" % (self._port, msg))
        #~ fcntl.fcntl(self.fd, FCNTL.F_SETFL, 0)  # set blocking

        try:
            self._reconfigurePort()
        except:
            try:
                os.close(self.fd)
            except:
                # ignore any exception when closing the port
                # also to keep original exception that happened when setting up
                pass
            self.fd = None
            raise
        else:
            self._isOpen = True
        #~ self.flushInput()


    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if self.fd is None:
            raise SerialException("Can only operate on a valid file descriptor")
        custom_baud = None

        vmin = vtime = 0                # timeout is done via select
        if self._interCharTimeout is not None:
            vmin = 1
            vtime = int(self._interCharTimeout * 10)
        try:
            orig_attr = termios.tcgetattr(self.fd)
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = orig_attr
        except termios.error as msg:      # if a port is nonexistent but has a /dev file, it'll fail here
            raise SerialException("Could not configure port: %s" % msg)
        # set up raw mode / no echo / binary
        cflag |=  (TERMIOS.CLOCAL|TERMIOS.CREAD)
        lflag &= ~(TERMIOS.ICANON|TERMIOS.ECHO|TERMIOS.ECHOE|TERMIOS.ECHOK|TERMIOS.ECHONL|
                     TERMIOS.ISIG|TERMIOS.IEXTEN) #|TERMIOS.ECHOPRT
        for flag in ('ECHOCTL', 'ECHOKE'): # netbsd workaround for Erk
            if hasattr(TERMIOS, flag):
                lflag &= ~getattr(TERMIOS, flag)

        oflag &= ~(TERMIOS.OPOST)
        iflag &= ~(TERMIOS.INLCR|TERMIOS.IGNCR|TERMIOS.ICRNL|TERMIOS.IGNBRK)
        if hasattr(TERMIOS, 'IUCLC'):
            iflag &= ~TERMIOS.IUCLC
        if hasattr(TERMIOS, 'PARMRK'):
            iflag &= ~TERMIOS.PARMRK

        # setup baud rate
        try:
            ispeed = ospeed = getattr(TERMIOS, 'B%s' % (self._baudrate))
        except AttributeError:
            try:
                ispeed = ospeed = baudrate_constants[self._baudrate]
            except KeyError:
                #~ raise ValueError('Invalid baud rate: %r' % self._baudrate)
                # may need custom baud rate, it isn't in our list.
                ispeed = ospeed = getattr(TERMIOS, 'B38400')
                try:
                    custom_baud = int(self._baudrate) # store for later
                except ValueError:
                    raise ValueError('Invalid baud rate: %r' % self._baudrate)
                else:
                    if custom_baud < 0:
                        raise ValueError('Invalid baud rate: %r' % self._baudrate)

        # setup char len
        cflag &= ~TERMIOS.CSIZE
        if self._bytesize == 8:
            cflag |= TERMIOS.CS8
        elif self._bytesize == 7:
            cflag |= TERMIOS.CS7
        elif self._bytesize == 6:
            cflag |= TERMIOS.CS6
        elif self._bytesize == 5:
            cflag |= TERMIOS.CS5
        else:
            raise ValueError('Invalid char len: %r' % self._bytesize)
        # setup stopbits
        if self._stopbits == STOPBITS_ONE:
            cflag &= ~(TERMIOS.CSTOPB)
        elif self._stopbits == STOPBITS_ONE_POINT_FIVE:
            cflag |=  (TERMIOS.CSTOPB)  # XXX same as TWO.. there is no POSIX support for 1.5
        elif self._stopbits == STOPBITS_TWO:
            cflag |=  (TERMIOS.CSTOPB)
        else:
            raise ValueError('Invalid stop bit specification: %r' % self._stopbits)
        # setup parity
        iflag &= ~(TERMIOS.INPCK|TERMIOS.ISTRIP)
        if self._parity == PARITY_NONE:
            cflag &= ~(TERMIOS.PARENB|TERMIOS.PARODD)
        elif self._parity == PARITY_EVEN:
            cflag &= ~(TERMIOS.PARODD)
            cflag |=  (TERMIOS.PARENB)
        elif self._parity == PARITY_ODD:
            cflag |=  (TERMIOS.PARENB|TERMIOS.PARODD)
        else:
            raise ValueError('Invalid parity: %r' % self._parity)
        # setup flow control
        # xonxoff
        if hasattr(TERMIOS, 'IXANY'):
            if self._xonxoff:
                iflag |=  (TERMIOS.IXON|TERMIOS.IXOFF) #|TERMIOS.IXANY)
            else:
                iflag &= ~(TERMIOS.IXON|TERMIOS.IXOFF|TERMIOS.IXANY)
        else:
            if self._xonxoff:
                iflag |=  (TERMIOS.IXON|TERMIOS.IXOFF)
            else:
                iflag &= ~(TERMIOS.IXON|TERMIOS.IXOFF)
        # rtscts
        if hasattr(TERMIOS, 'CRTSCTS'):
            if self._rtscts:
                cflag |=  (TERMIOS.CRTSCTS)
            else:
                cflag &= ~(TERMIOS.CRTSCTS)
        elif hasattr(TERMIOS, 'CNEW_RTSCTS'):   # try it with alternate constant name
            if self._rtscts:
                cflag |=  (TERMIOS.CNEW_RTSCTS)
            else:
                cflag &= ~(TERMIOS.CNEW_RTSCTS)
        # XXX should there be a warning if setting up rtscts (and xonxoff etc) fails??

        # buffer
        # vmin "minimal number of characters to be read. = for non blocking"
        if vmin < 0 or vmin > 255:
            raise ValueError('Invalid vmin: %r ' % vmin)
        cc[TERMIOS.VMIN] = vmin
        # vtime
        if vtime < 0 or vtime > 255:
            raise ValueError('Invalid vtime: %r' % vtime)
        cc[TERMIOS.VTIME] = vtime
        # activate settings
        if [iflag, oflag, cflag, lflag, ispeed, ospeed, cc] != orig_attr:
            termios.tcsetattr(self.fd, TERMIOS.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])

        # apply custom baud rate, if any
        if custom_baud is not None:
            set_special_baudrate(self, custom_baud)

    def close(self):
        """Close port"""
        if self._isOpen:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            self._isOpen = False

    def makeDeviceName(self, port):
        return device(port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        #~ s = fcntl.ioctl(self.fd, TERMIOS.FIONREAD, TIOCM_zero_str)
        s = fcntl.ioctl(self.fd, TIOCINQ, TIOCM_zero_str)
        return struct.unpack('I',s)[0]

    # select based implementation, proved to work on many systems
    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if not self._isOpen: raise portNotOpenError
        read = bytearray()
        while len(read) < size:
            ready,_,_ = select.select([self.fd],[],[], self._timeout)
            # If select was used with a timeout, and the timeout occurs, it
            # returns with empty lists -> thus abort read operation.
            # For timeout == 0 (non-blocking operation) also abort when there
            # is nothing to read.
            if not ready:
                break   # timeout
            buf = os.read(self.fd, size-len(read))
            # read should always return some data as select reported it was
            # ready to read when we get to this point.
            if not buf:
                # Disconnected devices, at least on Linux, show the
                # behavior that they are always ready to read immediately
                # but reading returns nothing.
                raise SerialException('device reports readiness to read but returned no data (device disconnected?)')
            read.extend(buf)
        return bytes(read)

    def write(self, data):
        """Output the given string over the serial port."""
        if not self._isOpen: raise portNotOpenError
        t = len(data)
        d = data
        if self._writeTimeout is not None and self._writeTimeout > 0:
            timeout = time.time() + self._writeTimeout
        else:
            timeout = None
        while t > 0:
            try:
                n = os.write(self.fd, d)
                if timeout:
                    # when timeout is set, use select to wait for being ready
                    # with the time left as timeout
                    timeleft = timeout - time.time()
                    if timeleft < 0:
                        raise writeTimeoutError
                    _, ready, _ = select.select([], [self.fd], [], timeleft)
                    if not ready:
                        raise writeTimeoutError
                d = d[n:]
                t = t - n
            except OSError as v:
                if v.errno != errno.EAGAIN:
                    raise SerialException('write failed: %s' % (v,))
        return len(data)

    def flush(self):
        """Flush of file like objects. In this case, wait until all data
           is written."""
        self.drainOutput()

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        termios.tcflush(self.fd, TERMIOS.TCIFLUSH)

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self._isOpen: raise portNotOpenError
        termios.tcflush(self.fd, TERMIOS.TCOFLUSH)

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given duration."""
        if not self._isOpen: raise portNotOpenError
        termios.tcsendbreak(self.fd, int(duration/0.25))

    def setBreak(self, level=1):
        """Set break: Controls TXD. When active, no transmitting is possible."""
        if self.fd is None: raise portNotOpenError
        if level:
            fcntl.ioctl(self.fd, TIOCSBRK)
        else:
            fcntl.ioctl(self.fd, TIOCCBRK)

    def setRTS(self, level=1):
        """Set terminal status line: Request To Send"""
        if not self._isOpen: raise portNotOpenError
        if level:
            fcntl.ioctl(self.fd, TIOCMBIS, TIOCM_RTS_str)
        else:
            fcntl.ioctl(self.fd, TIOCMBIC, TIOCM_RTS_str)

    def setDTR(self, level=1):
        """Set terminal status line: Data Terminal Ready"""
        if not self._isOpen: raise portNotOpenError
        if level:
            fcntl.ioctl(self.fd, TIOCMBIS, TIOCM_DTR_str)
        else:
            fcntl.ioctl(self.fd, TIOCMBIC, TIOCM_DTR_str)

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_CTS != 0

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_DSR != 0

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_RI != 0

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self._isOpen: raise portNotOpenError
        s = fcntl.ioctl(self.fd, TIOCMGET, TIOCM_zero_str)
        return struct.unpack('I',s)[0] & TIOCM_CD != 0

    # - - platform specific - - - -

    def drainOutput(self):
        """internal - not portable!"""
        if not self._isOpen: raise portNotOpenError
        termios.tcdrain(self.fd)

    def nonblocking(self):
        """internal - not portable!"""
        if not self._isOpen: raise portNotOpenError
        fcntl.fcntl(self.fd, FCNTL.F_SETFL, os.O_NONBLOCK)

    def fileno(self):
        """For easier use of the serial port instance with select.
           WARNING: this function is not portable to different platforms!"""
        if not self._isOpen: raise portNotOpenError
        return self.fd

    def flowControl(self, enable):
        """manually control flow - when hardware or software flow control is
        enabled"""
        if not self._isOpen: raise portNotOpenError
        if enable:
            termios.tcflow(self.fd, TERMIOS.TCION)
        else:
            termios.tcflow(self.fd, TERMIOS.TCIOFF)


# assemble Serial class with the platform specifc implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derrive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(PosixSerial, FileLike):
        pass
else:
    # io library present
    class Serial(PosixSerial, io.RawIOBase):
        pass

class PosixPollSerial(Serial):
    """poll based read implementation. not all systems support poll properly.
    however this one has better handling of errors, such as a device
    disconnecting while it's in use (e.g. USB-serial unplugged)"""

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if self.fd is None: raise portNotOpenError
        read = bytearray()
        poll = select.poll()
        poll.register(self.fd, select.POLLIN|select.POLLERR|select.POLLHUP|select.POLLNVAL)
        if size > 0:
            while len(read) < size:
                # print "\tread(): size",size, "have", len(read)    #debug
                # wait until device becomes ready to read (or something fails)
                for fd, event in poll.poll(self._timeout*1000):
                    if event & (select.POLLERR|select.POLLHUP|select.POLLNVAL):
                        raise SerialException('device reports error (poll)')
                    #  we don't care if it is select.POLLIN or timeout, that's
                    #  handled below
                buf = os.read(self.fd, size - len(read))
                read.extend(buf)
                if ((self._timeout is not None and self._timeout >= 0) or 
                    (self._interCharTimeout is not None and self._interCharTimeout > 0)) and not buf:
                    break   # early abort on timeout
        return bytes(read)


if __name__ == '__main__':
    s = Serial(0,
                 baudrate=19200,        # baud rate
                 bytesize=EIGHTBITS,    # number of data bits
                 parity=PARITY_EVEN,    # enable parity checking
                 stopbits=STOPBITS_ONE, # number of stop bits
                 timeout=3,             # set a timeout value, None for waiting forever
                 xonxoff=0,             # enable software flow control
                 rtscts=0,              # enable RTS/CTS flow control
               )
    s.setRTS(1)
    s.setDTR(1)
    s.flushInput()
    s.flushOutput()
    s.write('hello')
    sys.stdout.write('%r\n' % s.read(5))
    sys.stdout.write('%s\n' % s.inWaiting())
    del s


########NEW FILE########
__FILENAME__ = serialutil
#! python
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# see __init__.py
#
# (C) 2001-2010 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt

# compatibility for older Python < 2.6

import sys
sys_version = int(sys.version[0])

try:
    bytes
    bytearray
except (NameError, AttributeError):
    # Python older than 2.6 do not have these types. Like for Python 2.6 they
    # should behave like str. For Python older than 3.0 we want to work with
    # strings anyway, only later versions have a true bytes type.
    bytes = str
    # bytearray is a mutable type that is easily turned into an instance of
    # bytes
    class bytearray(list):
        # for bytes(bytearray()) usage
        def __str__(self): return ''.join(self)
        def __repr__(self): return 'bytearray(%r)' % ''.join(self)
        # append automatically converts integers to characters
        def append(self, item):
            if isinstance(item, str):
                list.append(self, item)
            else:
                list.append(self, chr(item))
        # +=
        def __iadd__(self, other):
            for byte in other:
                self.append(byte)
            return self

        def __getslice__(self, i, j):
            return bytearray(list.__getslice__(self, i, j))

        def __getitem__(self, item):
            if isinstance(item, slice):
                return bytearray(list.__getitem__(self, item))
            else:
                return ord(list.__getitem__(self, item))

        def __eq__(self, other):
            if isinstance(other, basestring):
                other = bytearray(other)
            return list.__eq__(self, other)

# all Python versions prior 3.x convert str([17]) to '[17]' instead of '\x11'
# so a simple bytes(sequence) doesn't work for all versions
def to_bytes(seq):
    """convert a sequence to a bytes type"""
    b = bytearray()
    for item in seq:
        b.append(item)  # this one handles int and str
    return bytes(b)

# create control bytes
XON  = to_bytes([17])
XOFF = to_bytes([19])

CR = to_bytes([13])
LF = to_bytes([10])


PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE = 'N', 'E', 'O', 'M', 'S'
STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO = (1, 1.5, 2)
FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS = (5, 6, 7, 8)

PARITY_NAMES = {
    PARITY_NONE:  'None',
    PARITY_EVEN:  'Even',
    PARITY_ODD:   'Odd',
    PARITY_MARK:  'Mark',
    PARITY_SPACE: 'Space',
}


class SerialException(IOError):
    """Base class for serial port related exceptions."""


class SerialTimeoutException(SerialException):
    """Write timeouts give an exception"""


writeTimeoutError = SerialTimeoutException("Write timeout")
portNotOpenError = ValueError('Attempting to use a port that is not open')


class FileLike(object):
    """An abstract file like class.

    This class implements readline and readlines based on read and
    writelines based on write.
    This class is used to provide the above functions for to Serial
    port objects.

    Note that when the serial port was opened with _NO_ timeout that
    readline blocks until it sees a newline (or the specified size is
    reached) and that readlines would never return and therefore
    refuses to work (it raises an exception in this case)!
    """

    def __init__(self):
        self.closed = True

    def close(self):
        self.closed = True

    # so that ports are closed when objects are discarded
    def __del__(self):
        """Destructor.  Calls close()."""
        # The try/except block is in case this is called at program
        # exit time, when it's possible that globals have already been
        # deleted, and then the close() call might fail.  Since
        # there's nothing we can do about such failures and they annoy
        # the end users, we suppress the traceback.
        try:
            self.close()
        except:
            pass

    def writelines(self, sequence):
        for line in sequence:
            self.write(line)

    def flush(self):
        """flush of file like objects"""
        pass

    # iterator for e.g. "for line in Serial(0): ..." usage
    def next(self):
        line = self.readline()
        if not line: raise StopIteration
        return line

    def __iter__(self):
        return self

    def readline(self, size=None, eol=LF):
        """read a line which is terminated with end-of-line (eol) character
        ('\n' by default) or until timeout."""
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
                if size is not None and len(line) >= size:
                    break
            else:
                break
        return bytes(line)

    def readlines(self, sizehint=None, eol=LF):
        """read a list of lines, until timeout.
        sizehint is ignored."""
        if self.timeout is None:
            raise ValueError("Serial port MUST have enabled timeout for this function!")
        leneol = len(eol)
        lines = []
        while True:
            line = self.readline(eol=eol)
            if line:
                lines.append(line)
                if line[-leneol:] != eol:    # was the line received with a timeout?
                    break
            else:
                break
        return lines

    def xreadlines(self, sizehint=None):
        """Read lines, implemented as generator. It will raise StopIteration on
        timeout (empty read). sizehint is ignored."""
        while True:
            line = self.readline()
            if not line: break
            yield line

    # other functions of file-likes - not used by pySerial

    #~ readinto(b)

    def seek(self, pos, whence=0):
        raise IOError("file is not seekable")

    def tell(self):
        raise IOError("file is not seekable")

    def truncate(self, n=None):
        raise IOError("file is not seekable")

    def isatty(self):
        return False


class SerialBase(object):
    """Serial port base class. Provides __init__ function and properties to
       get/set port settings."""

    # default values, may be overridden in subclasses that do not support all values
    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200, 230400, 460800, 500000,
                 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000,
                 3000000, 3500000, 4000000)
    BYTESIZES = (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)
    PARITIES  = (PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE)
    STOPBITS  = (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)

    def __init__(self,
                 port = None,           # number of device, numbering starts at
                                        # zero. if everything fails, the user
                                        # can specify a device string, note
                                        # that this isn't portable anymore
                                        # port will be opened if one is specified
                 baudrate=9600,         # baud rate
                 bytesize=EIGHTBITS,    # number of data bits
                 parity=PARITY_NONE,    # enable parity checking
                 stopbits=STOPBITS_ONE, # number of stop bits
                 timeout=None,          # set a timeout value, None to wait forever
                 xonxoff=False,         # enable software flow control
                 rtscts=False,          # enable RTS/CTS flow control
                 writeTimeout=None,     # set a timeout for writes
                 dsrdtr=False,          # None: use rtscts setting, dsrdtr override if True or False
                 interCharTimeout=None  # Inter-character timeout, None to disable
                 ):
        """Initialize comm port object. If a port is given, then the port will be
           opened immediately. Otherwise a Serial port object in closed state
           is returned."""

        self._isOpen   = False
        self._port     = None           # correct value is assigned below through properties
        self._baudrate = None           # correct value is assigned below through properties
        self._bytesize = None           # correct value is assigned below through properties
        self._parity   = None           # correct value is assigned below through properties
        self._stopbits = None           # correct value is assigned below through properties
        self._timeout  = None           # correct value is assigned below through properties
        self._writeTimeout = None       # correct value is assigned below through properties
        self._xonxoff  = None           # correct value is assigned below through properties
        self._rtscts   = None           # correct value is assigned below through properties
        self._dsrdtr   = None           # correct value is assigned below through properties
        self._interCharTimeout = None   # correct value is assigned below through properties

        # assign values using get/set methods using the properties feature
        self.port     = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity   = parity
        self.stopbits = stopbits
        self.timeout  = timeout
        self.writeTimeout = writeTimeout
        self.xonxoff  = xonxoff
        self.rtscts   = rtscts
        self.dsrdtr   = dsrdtr
        self.interCharTimeout = interCharTimeout

        if port is not None:
            self.open()

    def isOpen(self):
        """Check if the port is opened."""
        return self._isOpen

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    # TODO: these are not really needed as the is the BAUDRATES etc. attribute...
    # maybe i remove them before the final release...

    def getSupportedBaudrates(self):
        return [(str(b), b) for b in self.BAUDRATES]

    def getSupportedByteSizes(self):
        return [(str(b), b) for b in self.BYTESIZES]

    def getSupportedStopbits(self):
        return [(str(b), b) for b in self.STOPBITS]

    def getSupportedParities(self):
        return [(PARITY_NAMES[b], b) for b in self.PARITIES]

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def setPort(self, port):
        """Change the port. The attribute portstr is set to a string that
           contains the name of the port."""

        was_open = self._isOpen
        if was_open: self.close()
        if port is not None:
            if sys_version < 3:
                if isinstance(port, str) or isinstance(port, unicode):
                    self.portstr = port
                else:
                    self.portstr = self.makeDeviceName(port)
            else:
                if isinstance(port, str):
                    self.portstr = port
                else:
                    self.portstr = self.makeDeviceName(port)
        else:
            self.portstr = None
        self._port = port
        self.name = self.portstr
        if was_open: self.open()

    def getPort(self):
        """Get the current port setting. The value that was passed on init or using
           setPort() is passed back. See also the attribute portstr which contains
           the name of the port as a string."""
        return self._port

    port = property(getPort, setPort, doc="Port setting")


    def setBaudrate(self, baudrate):
        """Change baud rate. It raises a ValueError if the port is open and the
        baud rate is not possible. If the port is closed, then the value is
        accepted and the exception is raised when the port is opened."""
        try:
            self._baudrate = int(baudrate)
        except TypeError:
            raise ValueError("Not a valid baudrate: %r" % (baudrate,))
        else:
            if self._isOpen:  self._reconfigurePort()

    def getBaudrate(self):
        """Get the current baud rate setting."""
        return self._baudrate

    baudrate = property(getBaudrate, setBaudrate, doc="Baud rate setting")


    def setByteSize(self, bytesize):
        """Change byte size."""
        if bytesize not in self.BYTESIZES: raise ValueError("Not a valid byte size: %r" % (bytesize,))
        self._bytesize = bytesize
        if self._isOpen: self._reconfigurePort()

    def getByteSize(self):
        """Get the current byte size setting."""
        return self._bytesize

    bytesize = property(getByteSize, setByteSize, doc="Byte size setting")


    def setParity(self, parity):
        """Change parity setting."""
        if parity not in self.PARITIES: raise ValueError("Not a valid parity: %r" % (parity,))
        self._parity = parity
        if self._isOpen: self._reconfigurePort()

    def getParity(self):
        """Get the current parity setting."""
        return self._parity

    parity = property(getParity, setParity, doc="Parity setting")


    def setStopbits(self, stopbits):
        """Change stop bits size."""
        if stopbits not in self.STOPBITS: raise ValueError("Not a valid stop bit size: %r" % (stopbits,))
        self._stopbits = stopbits
        if self._isOpen: self._reconfigurePort()

    def getStopbits(self):
        """Get the current stop bits setting."""
        return self._stopbits

    stopbits = property(getStopbits, setStopbits, doc="Stop bits setting")


    def setTimeout(self, timeout):
        """Change timeout setting."""
        if timeout is not None:
            try:
                timeout + 1     # test if it's a number, will throw a TypeError if not...
            except TypeError:
                raise ValueError("Not a valid timeout: %r" % (timeout,))
            if timeout < 0: raise ValueError("Not a valid timeout: %r" % (timeout,))
        self._timeout = timeout
        if self._isOpen: self._reconfigurePort()

    def getTimeout(self):
        """Get the current timeout setting."""
        return self._timeout

    timeout = property(getTimeout, setTimeout, doc="Timeout setting for read()")


    def setWriteTimeout(self, timeout):
        """Change timeout setting."""
        if timeout is not None:
            if timeout < 0: raise ValueError("Not a valid timeout: %r" % (timeout,))
            try:
                timeout + 1     #test if it's a number, will throw a TypeError if not...
            except TypeError:
                raise ValueError("Not a valid timeout: %r" % timeout)

        self._writeTimeout = timeout
        if self._isOpen: self._reconfigurePort()

    def getWriteTimeout(self):
        """Get the current timeout setting."""
        return self._writeTimeout

    writeTimeout = property(getWriteTimeout, setWriteTimeout, doc="Timeout setting for write()")


    def setXonXoff(self, xonxoff):
        """Change XON/XOFF setting."""
        self._xonxoff = xonxoff
        if self._isOpen: self._reconfigurePort()

    def getXonXoff(self):
        """Get the current XON/XOFF setting."""
        return self._xonxoff

    xonxoff = property(getXonXoff, setXonXoff, doc="XON/XOFF setting")

    def setRtsCts(self, rtscts):
        """Change RTS/CTS flow control setting."""
        self._rtscts = rtscts
        if self._isOpen: self._reconfigurePort()

    def getRtsCts(self):
        """Get the current RTS/CTS flow control setting."""
        return self._rtscts

    rtscts = property(getRtsCts, setRtsCts, doc="RTS/CTS flow control setting")

    def setDsrDtr(self, dsrdtr=None):
        """Change DsrDtr flow control setting."""
        if dsrdtr is None:
            # if not set, keep backwards compatibility and follow rtscts setting
            self._dsrdtr = self._rtscts
        else:
            # if defined independently, follow its value
            self._dsrdtr = dsrdtr
        if self._isOpen: self._reconfigurePort()

    def getDsrDtr(self):
        """Get the current DSR/DTR flow control setting."""
        return self._dsrdtr

    dsrdtr = property(getDsrDtr, setDsrDtr, "DSR/DTR flow control setting")

    def setInterCharTimeout(self, interCharTimeout):
        """Change inter-character timeout setting."""
        if interCharTimeout is not None:
            if interCharTimeout < 0: raise ValueError("Not a valid timeout: %r" % interCharTimeout)
            try:
                interCharTimeout + 1     # test if it's a number, will throw a TypeError if not...
            except TypeError:
                raise ValueError("Not a valid timeout: %r" % interCharTimeout)

        self._interCharTimeout = interCharTimeout
        if self._isOpen: self._reconfigurePort()

    def getInterCharTimeout(self):
        """Get the current inter-character timeout setting."""
        return self._interCharTimeout

    interCharTimeout = property(getInterCharTimeout, setInterCharTimeout, doc="Inter-character timeout setting for read()")

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    _SETTINGS = ('baudrate', 'bytesize', 'parity', 'stopbits', 'xonxoff',
            'dsrdtr', 'rtscts', 'timeout', 'writeTimeout', 'interCharTimeout')

    def getSettingsDict(self):
        """Get current port settings as a dictionary. For use with
        applySettingsDict"""
        return dict([(key, getattr(self, '_'+key)) for key in self._SETTINGS])

    def applySettingsDict(self, d):
        """apply stored settings from a dictionary returned from
        getSettingsDict. it's allowed to delete keys from the dictionary. these
        values will simply left unchanged."""
        for key in self._SETTINGS:
            if d[key] != getattr(self, '_'+key):   # check against internal "_" value
                setattr(self, key, d[key])          # set non "_" value to use properties write function

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def __repr__(self):
        """String representation of the current port settings and its state."""
        return "%s<id=0x%x, open=%s>(port=%r, baudrate=%r, bytesize=%r, parity=%r, stopbits=%r, timeout=%r, xonxoff=%r, rtscts=%r, dsrdtr=%r)" % (
            self.__class__.__name__,
            id(self),
            self._isOpen,
            self.portstr,
            self.baudrate,
            self.bytesize,
            self.parity,
            self.stopbits,
            self.timeout,
            self.xonxoff,
            self.rtscts,
            self.dsrdtr,
        )


    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -
    # compatibility with io library

    def readable(self): return True
    def writable(self): return True
    def seekable(self): return False
    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        try:
            b[:n] = data
        except TypeError as err:
            import array
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array('b', data)
        return n


if __name__ == '__main__':
    import sys
    s = SerialBase()
    sys.stdout.write('port name:  %s\n' % s.portstr)
    sys.stdout.write('baud rates: %s\n' % s.getSupportedBaudrates())
    sys.stdout.write('byte sizes: %s\n' % s.getSupportedByteSizes())
    sys.stdout.write('parities:   %s\n' % s.getSupportedParities())
    sys.stdout.write('stop bits:  %s\n' % s.getSupportedStopbits())
    sys.stdout.write('%s\n' % s)

########NEW FILE########
__FILENAME__ = serialwin32
#! python
# Python Serial Port Extension for Win32, Linux, BSD, Jython
# serial driver for win32
# see __init__.py
#
# (C) 2001-2011 Chris Liechti <cliechti@gmx.net>
# this is distributed under a free software license, see license.txt
#
# Initial patch to use ctypes by Giovanni Bajo <rasky@develer.com>

import ctypes
from . import win32

from .serialutil import *


def device(portnum):
    """Turn a port number into a device name"""
    return 'COM%d' % (portnum+1) # numbers are transformed to a string


class Win32Serial(SerialBase):
    """Serial port implementation for Win32 based on ctypes."""

    BAUDRATES = (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                 9600, 19200, 38400, 57600, 115200)

    def __init__(self, *args, **kwargs):
        self.hComPort = None
        self._rtsToggle = False
        SerialBase.__init__(self, *args, **kwargs)

    def open(self):
        """Open port with current settings. This may throw a SerialException
           if the port cannot be opened."""
        if self._port is None:
            raise SerialException("Port must be configured before it can be used.")
        if self._isOpen:
            raise SerialException("Port is already open.")
        # the "\\.\COMx" format is required for devices other than COM1-COM8
        # not all versions of windows seem to support this properly
        # so that the first few ports are used with the DOS device name
        port = self.portstr
        try:
            if port.upper().startswith('COM') and int(port[3:]) > 8:
                port = '\\\\.\\' + port
        except ValueError:
            # for like COMnotanumber
            pass
        self.hComPort = win32.CreateFile(port,
               win32.GENERIC_READ | win32.GENERIC_WRITE,
               0, # exclusive access
               None, # no security
               win32.OPEN_EXISTING,
               win32.FILE_ATTRIBUTE_NORMAL | win32.FILE_FLAG_OVERLAPPED,
               0)
        if self.hComPort == win32.INVALID_HANDLE_VALUE:
            self.hComPort = None    # 'cause __del__ is called anyway
            raise SerialException("could not open port %s: %s" % (self.portstr, ctypes.WinError()))

        # Setup a 4k buffer
        win32.SetupComm(self.hComPort, 4096, 4096)

        # Save original timeout values:
        self._orgTimeouts = win32.COMMTIMEOUTS()
        win32.GetCommTimeouts(self.hComPort, ctypes.byref(self._orgTimeouts))

        self._rtsState = win32.RTS_CONTROL_ENABLE
        self._dtrState = win32.DTR_CONTROL_ENABLE

        self._reconfigurePort()

        # Clear buffers:
        # Remove anything that was there
        win32.PurgeComm(self.hComPort,
                            win32.PURGE_TXCLEAR | win32.PURGE_TXABORT |
                            win32.PURGE_RXCLEAR | win32.PURGE_RXABORT)

        self._overlappedRead = win32.OVERLAPPED()
        self._overlappedRead.hEvent = win32.CreateEvent(None, 1, 0, None)
        self._overlappedWrite = win32.OVERLAPPED()
        #~ self._overlappedWrite.hEvent = win32.CreateEvent(None, 1, 0, None)
        self._overlappedWrite.hEvent = win32.CreateEvent(None, 0, 0, None)
        self._isOpen = True

    def _reconfigurePort(self):
        """Set communication parameters on opened port."""
        if not self.hComPort:
            raise SerialException("Can only operate on a valid port handle")

        # Set Windows timeout values
        # timeouts is a tuple with the following items:
        # (ReadIntervalTimeout,ReadTotalTimeoutMultiplier,
        #  ReadTotalTimeoutConstant,WriteTotalTimeoutMultiplier,
        #  WriteTotalTimeoutConstant)
        if self._timeout is None:
            timeouts = (0, 0, 0, 0, 0)
        elif self._timeout == 0:
            timeouts = (win32.MAXDWORD, 0, 0, 0, 0)
        else:
            timeouts = (0, 0, int(self._timeout*1000), 0, 0)
        if self._timeout != 0 and self._interCharTimeout is not None:
            timeouts = (int(self._interCharTimeout * 1000),) + timeouts[1:]

        if self._writeTimeout is None:
            pass
        elif self._writeTimeout == 0:
            timeouts = timeouts[:-2] + (0, win32.MAXDWORD)
        else:
            timeouts = timeouts[:-2] + (0, int(self._writeTimeout*1000))
        win32.SetCommTimeouts(self.hComPort, ctypes.byref(win32.COMMTIMEOUTS(*timeouts)))

        win32.SetCommMask(self.hComPort, win32.EV_ERR)

        # Setup the connection info.
        # Get state and modify it:
        comDCB = win32.DCB()
        win32.GetCommState(self.hComPort, ctypes.byref(comDCB))
        comDCB.BaudRate = self._baudrate

        if self._bytesize == FIVEBITS:
            comDCB.ByteSize     = 5
        elif self._bytesize == SIXBITS:
            comDCB.ByteSize     = 6
        elif self._bytesize == SEVENBITS:
            comDCB.ByteSize     = 7
        elif self._bytesize == EIGHTBITS:
            comDCB.ByteSize     = 8
        else:
            raise ValueError("Unsupported number of data bits: %r" % self._bytesize)

        if self._parity == PARITY_NONE:
            comDCB.Parity       = win32.NOPARITY
            comDCB.fParity      = 0 # Disable Parity Check
        elif self._parity == PARITY_EVEN:
            comDCB.Parity       = win32.EVENPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        elif self._parity == PARITY_ODD:
            comDCB.Parity       = win32.ODDPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        elif self._parity == PARITY_MARK:
            comDCB.Parity       = win32.MARKPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        elif self._parity == PARITY_SPACE:
            comDCB.Parity       = win32.SPACEPARITY
            comDCB.fParity      = 1 # Enable Parity Check
        else:
            raise ValueError("Unsupported parity mode: %r" % self._parity)

        if self._stopbits == STOPBITS_ONE:
            comDCB.StopBits     = win32.ONESTOPBIT
        elif self._stopbits == STOPBITS_ONE_POINT_FIVE:
            comDCB.StopBits     = win32.ONE5STOPBITS
        elif self._stopbits == STOPBITS_TWO:
            comDCB.StopBits     = win32.TWOSTOPBITS
        else:
            raise ValueError("Unsupported number of stop bits: %r" % self._stopbits)

        comDCB.fBinary          = 1 # Enable Binary Transmission
        # Char. w/ Parity-Err are replaced with 0xff (if fErrorChar is set to TRUE)
        if self._rtscts:
            comDCB.fRtsControl  = win32.RTS_CONTROL_HANDSHAKE
        elif self._rtsToggle:
            comDCB.fRtsControl  = win32.RTS_CONTROL_TOGGLE
        else:
            comDCB.fRtsControl  = self._rtsState
        if self._dsrdtr:
            comDCB.fDtrControl  = win32.DTR_CONTROL_HANDSHAKE
        else:
            comDCB.fDtrControl  = self._dtrState

        if self._rtsToggle:
            comDCB.fOutxCtsFlow     = 0
        else:
            comDCB.fOutxCtsFlow     = self._rtscts
        comDCB.fOutxDsrFlow     = self._dsrdtr
        comDCB.fOutX            = self._xonxoff
        comDCB.fInX             = self._xonxoff
        comDCB.fNull            = 0
        comDCB.fErrorChar       = 0
        comDCB.fAbortOnError    = 0
        comDCB.XonChar          = XON
        comDCB.XoffChar         = XOFF

        if not win32.SetCommState(self.hComPort, ctypes.byref(comDCB)):
            raise ValueError("Cannot configure port, some setting was wrong. Original message: %s" % ctypes.WinError())

    #~ def __del__(self):
        #~ self.close()

    def close(self):
        """Close port"""
        if self._isOpen:
            if self.hComPort:
                # Restore original timeout values:
                win32.SetCommTimeouts(self.hComPort, self._orgTimeouts)
                # Close COM-Port:
                win32.CloseHandle(self.hComPort)
                win32.CloseHandle(self._overlappedRead.hEvent)
                win32.CloseHandle(self._overlappedWrite.hEvent)
                self.hComPort = None
            self._isOpen = False

    def makeDeviceName(self, port):
        return device(port)

    #  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -

    def inWaiting(self):
        """Return the number of characters currently in the input buffer."""
        flags = win32.DWORD()
        comstat = win32.COMSTAT()
        if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
            raise SerialException('call to ClearCommError failed')
        return comstat.cbInQue

    def read(self, size=1):
        """Read size bytes from the serial port. If a timeout is set it may
           return less characters as requested. With no timeout it will block
           until the requested number of bytes is read."""
        if not self.hComPort: raise portNotOpenError
        if size > 0:
            win32.ResetEvent(self._overlappedRead.hEvent)
            flags = win32.DWORD()
            comstat = win32.COMSTAT()
            if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
                raise SerialException('call to ClearCommError failed')
            if self.timeout == 0:
                n = min(comstat.cbInQue, size)
                if n > 0:
                    buf = ctypes.create_string_buffer(n)
                    rc = win32.DWORD()
                    err = win32.ReadFile(self.hComPort, buf, n, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
                    if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
                        raise SerialException("ReadFile failed (%s)" % ctypes.WinError())
                    err = win32.WaitForSingleObject(self._overlappedRead.hEvent, win32.INFINITE)
                    read = buf.raw[:rc.value]
                else:
                    read = bytes()
            else:
                buf = ctypes.create_string_buffer(size)
                rc = win32.DWORD()
                err = win32.ReadFile(self.hComPort, buf, size, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
                if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
                    raise SerialException("ReadFile failed (%s)" % ctypes.WinError())
                err = win32.GetOverlappedResult(self.hComPort, ctypes.byref(self._overlappedRead), ctypes.byref(rc), True)
                read = buf.raw[:rc.value]
        else:
            read = bytes()
        return bytes(read)

    def write(self, data):
        """Output the given string over the serial port."""
        if not self.hComPort: raise portNotOpenError
        #~ if not isinstance(data, (bytes, bytearray)):
            #~ raise TypeError('expected %s or bytearray, got %s' % (bytes, type(data)))
        # convert data (needed in case of memoryview instance: Py 3.1 io lib), ctypes doesn't like memoryview
        data = bytes(data)
        if data:
            #~ win32event.ResetEvent(self._overlappedWrite.hEvent)
            n = win32.DWORD()
            err = win32.WriteFile(self.hComPort, data, len(data), ctypes.byref(n), self._overlappedWrite)
            if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
                raise SerialException("WriteFile failed (%s)" % ctypes.WinError())
            if self._writeTimeout != 0: # if blocking (None) or w/ write timeout (>0)
                # Wait for the write to complete.
                #~ win32.WaitForSingleObject(self._overlappedWrite.hEvent, win32.INFINITE)
                err = win32.GetOverlappedResult(self.hComPort, self._overlappedWrite, ctypes.byref(n), True)
                if n.value != len(data):
                    raise writeTimeoutError
            return n.value
        else:
            return 0


    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        if not self.hComPort: raise portNotOpenError
        win32.PurgeComm(self.hComPort, win32.PURGE_RXCLEAR | win32.PURGE_RXABORT)

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        if not self.hComPort: raise portNotOpenError
        win32.PurgeComm(self.hComPort, win32.PURGE_TXCLEAR | win32.PURGE_TXABORT)

    def sendBreak(self, duration=0.25):
        """Send break condition. Timed, returns to idle state after given duration."""
        if not self.hComPort: raise portNotOpenError
        import time
        win32.SetCommBreak(self.hComPort)
        time.sleep(duration)
        win32.ClearCommBreak(self.hComPort)

    def setBreak(self, level=1):
        """Set break: Controls TXD. When active, to transmitting is possible."""
        if not self.hComPort: raise portNotOpenError
        if level:
            win32.SetCommBreak(self.hComPort)
        else:
            win32.ClearCommBreak(self.hComPort)

    def setRTS(self, level=1):
        """Set terminal status line: Request To Send"""
        if not self.hComPort: raise portNotOpenError
        if level:
            self._rtsState = win32.RTS_CONTROL_ENABLE
            win32.EscapeCommFunction(self.hComPort, win32.SETRTS)
        else:
            self._rtsState = win32.RTS_CONTROL_DISABLE
            win32.EscapeCommFunction(self.hComPort, win32.CLRRTS)

    def setDTR(self, level=1):
        """Set terminal status line: Data Terminal Ready"""
        if not self.hComPort: raise portNotOpenError
        if level:
            self._dtrState = win32.DTR_CONTROL_ENABLE
            win32.EscapeCommFunction(self.hComPort, win32.SETDTR)
        else:
            self._dtrState = win32.DTR_CONTROL_DISABLE
            win32.EscapeCommFunction(self.hComPort, win32.CLRDTR)

    def _GetCommModemStatus(self):
        stat = win32.DWORD()
        win32.GetCommModemStatus(self.hComPort, ctypes.byref(stat))
        return stat.value

    def getCTS(self):
        """Read terminal status line: Clear To Send"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_CTS_ON & self._GetCommModemStatus() != 0

    def getDSR(self):
        """Read terminal status line: Data Set Ready"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_DSR_ON & self._GetCommModemStatus() != 0

    def getRI(self):
        """Read terminal status line: Ring Indicator"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_RING_ON & self._GetCommModemStatus() != 0

    def getCD(self):
        """Read terminal status line: Carrier Detect"""
        if not self.hComPort: raise portNotOpenError
        return win32.MS_RLSD_ON & self._GetCommModemStatus() != 0

    # - - platform specific - - - -

    def setXON(self, level=True):
        """Platform specific - set flow state."""
        if not self.hComPort: raise portNotOpenError
        if level:
            win32.EscapeCommFunction(self.hComPort, win32.SETXON)
        else:
            win32.EscapeCommFunction(self.hComPort, win32.SETXOFF)

    def outWaiting(self):
        """return how many characters the in the outgoing buffer"""
        flags = win32.DWORD()
        comstat = win32.COMSTAT()
        if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
            raise SerialException('call to ClearCommError failed')
        return comstat.cbOutQue

    # functions useful for RS-485 adapters
    def setRtsToggle(self, rtsToggle):
        """Change RTS toggle control setting."""
        self._rtsToggle = rtsToggle
        if self._isOpen: self._reconfigurePort()

    def getRtsToggle(self):
        """Get the current RTS toggle control setting."""
        return self._rtsToggle

    rtsToggle = property(getRtsToggle, setRtsToggle, doc="RTS toggle control setting")


# assemble Serial class with the platform specific implementation and the base
# for file-like behavior. for Python 2.6 and newer, that provide the new I/O
# library, derive from io.RawIOBase
try:
    import io
except ImportError:
    # classic version with our own file-like emulation
    class Serial(Win32Serial, FileLike):
        pass
else:
    # io library present
    class Serial(Win32Serial, io.RawIOBase):
        pass


# Nur Testfunktion!!
if __name__ == '__main__':
    s = Serial(0)
    sys.stdout.write("%s\n" % s)

    s = Serial()
    sys.stdout.write("%s\n" % s)

    s.baudrate = 19200
    s.databits = 7
    s.close()
    s.port = 0
    s.open()
    sys.stdout.write("%s\n" % s)


########NEW FILE########
__FILENAME__ = win32
from ctypes import *
from ctypes.wintypes import HANDLE
from ctypes.wintypes import BOOL
from ctypes.wintypes import LPCWSTR
_stdcall_libraries = {}
_stdcall_libraries['kernel32'] = WinDLL('kernel32')
from ctypes.wintypes import DWORD
from ctypes.wintypes import WORD
from ctypes.wintypes import BYTE

INVALID_HANDLE_VALUE = HANDLE(-1).value

# some details of the windows API differ between 32 and 64 bit systems..
def is_64bit():
    """Returns true when running on a 64 bit system"""
    return sizeof(c_ulong) != sizeof(c_void_p)

# ULONG_PTR is a an ordinary number, not a pointer and contrary to the name it
# is either 32 or 64 bits, depending on the type of windows...
# so test if this a 32 bit windows...
if is_64bit():
    # assume 64 bits
    ULONG_PTR = c_int64
else:
    # 32 bits
    ULONG_PTR = c_ulong


class _SECURITY_ATTRIBUTES(Structure):
    pass
LPSECURITY_ATTRIBUTES = POINTER(_SECURITY_ATTRIBUTES)


try:
    CreateEventW = _stdcall_libraries['kernel32'].CreateEventW
except AttributeError:
    # Fallback to non wide char version for old OS...
    from ctypes.wintypes import LPCSTR
    CreateEventA = _stdcall_libraries['kernel32'].CreateEventA
    CreateEventA.restype = HANDLE
    CreateEventA.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCSTR]
    CreateEvent=CreateEventA

    CreateFileA = _stdcall_libraries['kernel32'].CreateFileA
    CreateFileA.restype = HANDLE
    CreateFileA.argtypes = [LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]
    CreateFile = CreateFileA
else:
    CreateEventW.restype = HANDLE
    CreateEventW.argtypes = [LPSECURITY_ATTRIBUTES, BOOL, BOOL, LPCWSTR]
    CreateEvent = CreateEventW # alias

    CreateFileW = _stdcall_libraries['kernel32'].CreateFileW
    CreateFileW.restype = HANDLE
    CreateFileW.argtypes = [LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]
    CreateFile = CreateFileW # alias

class _OVERLAPPED(Structure):
    pass
OVERLAPPED = _OVERLAPPED

class _COMSTAT(Structure):
    pass
COMSTAT = _COMSTAT

class _DCB(Structure):
    pass
DCB = _DCB

class _COMMTIMEOUTS(Structure):
    pass
COMMTIMEOUTS = _COMMTIMEOUTS

GetLastError = _stdcall_libraries['kernel32'].GetLastError
GetLastError.restype = DWORD
GetLastError.argtypes = []

LPOVERLAPPED = POINTER(_OVERLAPPED)
LPDWORD = POINTER(DWORD)

GetOverlappedResult = _stdcall_libraries['kernel32'].GetOverlappedResult
GetOverlappedResult.restype = BOOL
GetOverlappedResult.argtypes = [HANDLE, LPOVERLAPPED, LPDWORD, BOOL]

ResetEvent = _stdcall_libraries['kernel32'].ResetEvent
ResetEvent.restype = BOOL
ResetEvent.argtypes = [HANDLE]

LPCVOID = c_void_p

WriteFile = _stdcall_libraries['kernel32'].WriteFile
WriteFile.restype = BOOL
WriteFile.argtypes = [HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED]

LPVOID = c_void_p

ReadFile = _stdcall_libraries['kernel32'].ReadFile
ReadFile.restype = BOOL
ReadFile.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED]

CloseHandle = _stdcall_libraries['kernel32'].CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = [HANDLE]

ClearCommBreak = _stdcall_libraries['kernel32'].ClearCommBreak
ClearCommBreak.restype = BOOL
ClearCommBreak.argtypes = [HANDLE]

LPCOMSTAT = POINTER(_COMSTAT)

ClearCommError = _stdcall_libraries['kernel32'].ClearCommError
ClearCommError.restype = BOOL
ClearCommError.argtypes = [HANDLE, LPDWORD, LPCOMSTAT]

SetupComm = _stdcall_libraries['kernel32'].SetupComm
SetupComm.restype = BOOL
SetupComm.argtypes = [HANDLE, DWORD, DWORD]

EscapeCommFunction = _stdcall_libraries['kernel32'].EscapeCommFunction
EscapeCommFunction.restype = BOOL
EscapeCommFunction.argtypes = [HANDLE, DWORD]

GetCommModemStatus = _stdcall_libraries['kernel32'].GetCommModemStatus
GetCommModemStatus.restype = BOOL
GetCommModemStatus.argtypes = [HANDLE, LPDWORD]

LPDCB = POINTER(_DCB)

GetCommState = _stdcall_libraries['kernel32'].GetCommState
GetCommState.restype = BOOL
GetCommState.argtypes = [HANDLE, LPDCB]

LPCOMMTIMEOUTS = POINTER(_COMMTIMEOUTS)

GetCommTimeouts = _stdcall_libraries['kernel32'].GetCommTimeouts
GetCommTimeouts.restype = BOOL
GetCommTimeouts.argtypes = [HANDLE, LPCOMMTIMEOUTS]

PurgeComm = _stdcall_libraries['kernel32'].PurgeComm
PurgeComm.restype = BOOL
PurgeComm.argtypes = [HANDLE, DWORD]

SetCommBreak = _stdcall_libraries['kernel32'].SetCommBreak
SetCommBreak.restype = BOOL
SetCommBreak.argtypes = [HANDLE]

SetCommMask = _stdcall_libraries['kernel32'].SetCommMask
SetCommMask.restype = BOOL
SetCommMask.argtypes = [HANDLE, DWORD]

SetCommState = _stdcall_libraries['kernel32'].SetCommState
SetCommState.restype = BOOL
SetCommState.argtypes = [HANDLE, LPDCB]

SetCommTimeouts = _stdcall_libraries['kernel32'].SetCommTimeouts
SetCommTimeouts.restype = BOOL
SetCommTimeouts.argtypes = [HANDLE, LPCOMMTIMEOUTS]

WaitForSingleObject = _stdcall_libraries['kernel32'].WaitForSingleObject
WaitForSingleObject.restype = DWORD
WaitForSingleObject.argtypes = [HANDLE, DWORD]

ONESTOPBIT = 0 # Variable c_int
TWOSTOPBITS = 2 # Variable c_int
ONE5STOPBITS = 1

NOPARITY = 0 # Variable c_int
ODDPARITY = 1 # Variable c_int
EVENPARITY = 2 # Variable c_int
MARKPARITY = 3
SPACEPARITY = 4

RTS_CONTROL_HANDSHAKE = 2 # Variable c_int
RTS_CONTROL_DISABLE = 0 # Variable c_int
RTS_CONTROL_ENABLE = 1 # Variable c_int
RTS_CONTROL_TOGGLE = 3 # Variable c_int
SETRTS = 3
CLRRTS = 4

DTR_CONTROL_HANDSHAKE = 2 # Variable c_int
DTR_CONTROL_DISABLE = 0 # Variable c_int
DTR_CONTROL_ENABLE = 1 # Variable c_int
SETDTR = 5
CLRDTR = 6

MS_DSR_ON = 32 # Variable c_ulong
EV_RING = 256 # Variable c_int
EV_PERR = 512 # Variable c_int
EV_ERR = 128 # Variable c_int
SETXOFF = 1 # Variable c_int
EV_RXCHAR = 1 # Variable c_int
GENERIC_WRITE = 1073741824 # Variable c_long
PURGE_TXCLEAR = 4 # Variable c_int
FILE_FLAG_OVERLAPPED = 1073741824 # Variable c_int
EV_DSR = 16 # Variable c_int
MAXDWORD = 4294967295 # Variable c_uint
EV_RLSD = 32 # Variable c_int
ERROR_IO_PENDING = 997 # Variable c_long
MS_CTS_ON = 16 # Variable c_ulong
EV_EVENT1 = 2048 # Variable c_int
EV_RX80FULL = 1024 # Variable c_int
PURGE_RXABORT = 2 # Variable c_int
FILE_ATTRIBUTE_NORMAL = 128 # Variable c_int
PURGE_TXABORT = 1 # Variable c_int
SETXON = 2 # Variable c_int
OPEN_EXISTING = 3 # Variable c_int
MS_RING_ON = 64 # Variable c_ulong
EV_TXEMPTY = 4 # Variable c_int
EV_RXFLAG = 2 # Variable c_int
MS_RLSD_ON = 128 # Variable c_ulong
GENERIC_READ = 2147483648 # Variable c_ulong
EV_EVENT2 = 4096 # Variable c_int
EV_CTS = 8 # Variable c_int
EV_BREAK = 64 # Variable c_int
PURGE_RXCLEAR = 8 # Variable c_int
INFINITE = 0xFFFFFFFF


class N11_OVERLAPPED4DOLLAR_48E(Union):
    pass
class N11_OVERLAPPED4DOLLAR_484DOLLAR_49E(Structure):
    pass
N11_OVERLAPPED4DOLLAR_484DOLLAR_49E._fields_ = [
    ('Offset', DWORD),
    ('OffsetHigh', DWORD),
]

PVOID = c_void_p

N11_OVERLAPPED4DOLLAR_48E._anonymous_ = ['_0']
N11_OVERLAPPED4DOLLAR_48E._fields_ = [
    ('_0', N11_OVERLAPPED4DOLLAR_484DOLLAR_49E),
    ('Pointer', PVOID),
]
_OVERLAPPED._anonymous_ = ['_0']
_OVERLAPPED._fields_ = [
    ('Internal', ULONG_PTR),
    ('InternalHigh', ULONG_PTR),
    ('_0', N11_OVERLAPPED4DOLLAR_48E),
    ('hEvent', HANDLE),
]
_SECURITY_ATTRIBUTES._fields_ = [
    ('nLength', DWORD),
    ('lpSecurityDescriptor', LPVOID),
    ('bInheritHandle', BOOL),
]
_COMSTAT._fields_ = [
    ('fCtsHold', DWORD, 1),
    ('fDsrHold', DWORD, 1),
    ('fRlsdHold', DWORD, 1),
    ('fXoffHold', DWORD, 1),
    ('fXoffSent', DWORD, 1),
    ('fEof', DWORD, 1),
    ('fTxim', DWORD, 1),
    ('fReserved', DWORD, 25),
    ('cbInQue', DWORD),
    ('cbOutQue', DWORD),
]
_DCB._fields_ = [
    ('DCBlength', DWORD),
    ('BaudRate', DWORD),
    ('fBinary', DWORD, 1),
    ('fParity', DWORD, 1),
    ('fOutxCtsFlow', DWORD, 1),
    ('fOutxDsrFlow', DWORD, 1),
    ('fDtrControl', DWORD, 2),
    ('fDsrSensitivity', DWORD, 1),
    ('fTXContinueOnXoff', DWORD, 1),
    ('fOutX', DWORD, 1),
    ('fInX', DWORD, 1),
    ('fErrorChar', DWORD, 1),
    ('fNull', DWORD, 1),
    ('fRtsControl', DWORD, 2),
    ('fAbortOnError', DWORD, 1),
    ('fDummy2', DWORD, 17),
    ('wReserved', WORD),
    ('XonLim', WORD),
    ('XoffLim', WORD),
    ('ByteSize', BYTE),
    ('Parity', BYTE),
    ('StopBits', BYTE),
    ('XonChar', c_char),
    ('XoffChar', c_char),
    ('ErrorChar', c_char),
    ('EofChar', c_char),
    ('EvtChar', c_char),
    ('wReserved1', WORD),
]
_COMMTIMEOUTS._fields_ = [
    ('ReadIntervalTimeout', DWORD),
    ('ReadTotalTimeoutMultiplier', DWORD),
    ('ReadTotalTimeoutConstant', DWORD),
    ('WriteTotalTimeoutMultiplier', DWORD),
    ('WriteTotalTimeoutConstant', DWORD),
]
__all__ = ['GetLastError', 'MS_CTS_ON', 'FILE_ATTRIBUTE_NORMAL',
           'DTR_CONTROL_ENABLE', '_COMSTAT', 'MS_RLSD_ON',
           'GetOverlappedResult', 'SETXON', 'PURGE_TXABORT',
           'PurgeComm', 'N11_OVERLAPPED4DOLLAR_48E', 'EV_RING',
           'ONESTOPBIT', 'SETXOFF', 'PURGE_RXABORT', 'GetCommState',
           'RTS_CONTROL_ENABLE', '_DCB', 'CreateEvent',
           '_COMMTIMEOUTS', '_SECURITY_ATTRIBUTES', 'EV_DSR',
           'EV_PERR', 'EV_RXFLAG', 'OPEN_EXISTING', 'DCB',
           'FILE_FLAG_OVERLAPPED', 'EV_CTS', 'SetupComm',
           'LPOVERLAPPED', 'EV_TXEMPTY', 'ClearCommBreak',
           'LPSECURITY_ATTRIBUTES', 'SetCommBreak', 'SetCommTimeouts',
           'COMMTIMEOUTS', 'ODDPARITY', 'EV_RLSD',
           'GetCommModemStatus', 'EV_EVENT2', 'PURGE_TXCLEAR',
           'EV_BREAK', 'EVENPARITY', 'LPCVOID', 'COMSTAT', 'ReadFile',
           'PVOID', '_OVERLAPPED', 'WriteFile', 'GetCommTimeouts',
           'ResetEvent', 'EV_RXCHAR', 'LPCOMSTAT', 'ClearCommError',
           'ERROR_IO_PENDING', 'EscapeCommFunction', 'GENERIC_READ',
           'RTS_CONTROL_HANDSHAKE', 'OVERLAPPED',
           'DTR_CONTROL_HANDSHAKE', 'PURGE_RXCLEAR', 'GENERIC_WRITE',
           'LPDCB', 'CreateEventW', 'SetCommMask', 'EV_EVENT1',
           'SetCommState', 'LPVOID', 'CreateFileW', 'LPDWORD',
           'EV_RX80FULL', 'TWOSTOPBITS', 'LPCOMMTIMEOUTS', 'MAXDWORD',
           'MS_DSR_ON', 'MS_RING_ON',
           'N11_OVERLAPPED4DOLLAR_484DOLLAR_49E', 'EV_ERR',
           'ULONG_PTR', 'CreateFile', 'NOPARITY', 'CloseHandle']

########NEW FILE########
__FILENAME__ = serial
#-*- coding: utf-8 -*-
# stino/serial.py

import os
import threading
import time

from . import constant
from . import pyserial

class SerialListener:
	def __init__(self, menu):
		self.menu = menu
		self.serial_list = []
		self.is_alive = False

	def start(self):
		if not self.is_alive:
			self.is_alive = True
			listener_thread = threading.Thread(target=self.update)
			listener_thread.start()

	def update(self):
		while self.is_alive:
			pre_serial_list = self.serial_list
			self.serial_list = getSerialPortList()
			if self.serial_list != pre_serial_list:
				self.menu.refresh()
			time.sleep(1)

	def stop(self):
		self.is_alive = False

def getSerialPortList():
	serial_port_list = []
	has_ports = False
	if constant.sys_platform == "windows":
		if constant.sys_version < 3:
			import _winreg as winreg
		else:
			import winreg
		path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
		try:
			reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path,)
			has_ports = True
		except WindowsError:
			pass

		if has_ports:
			for i in range(128):
				try:
					name,value,type = winreg.EnumValue(reg,i)
				except WindowsError:
					pass
				else:
					serial_port_list.append(value)
	else:
		if constant.sys_platform == 'osx':
			dev_names = ['tty.', 'cu.']
		else:
			dev_names = ['ttyACM', 'ttyUSB']
		
		serial_port_list = []
		dev_path = '/dev'
		dev_file_list = os.listdir(dev_path)
		for dev_file in dev_file_list:
			for dev_name in dev_names:
				if dev_name in dev_file:
					dev_file_path = os.path.join(dev_path, dev_file)
					serial_port_list.append(dev_file_path)
	return serial_port_list

def isSerialAvailable(serial_port):
	state = False
	serial = pyserial.Serial()
	serial.port = serial_port
	try:
		serial.open()
	except pyserial.serialutil.SerialException:
		pass
	except UnicodeDecodeError:
		pass
	else:
		if serial.isOpen():
			state = True
			serial.close()
	return state

def getSelectedSerialPort():
	serial_list = getSerialPortList()
	serial_port_id = constant.sketch_settings.get('serial_port', -1)

	serial_port = 'no_serial_port'
	if serial_list:
		try:
			serial_port = serial_list[serial_port_id]
		except IndexError:
			serial_port = serial_list[0]
	return serial_port
########NEW FILE########
__FILENAME__ = serial_monitor
#-*- coding: utf-8 -*-
# stino/serial_monitor.py

import threading
import time

import sublime

from . import constant
from . import serial
from . import pyserial

class MonitorView:
	def __init__(self, name = 'Serial Monitor'):
		self.name = name
		self.show_text = ''
		self.window = sublime.active_window()
		self.view = findInOpendView(self.name)
		if not self.view:
			self.view = self.window.new_file()
			self.view.set_name(self.name)
		self.raiseToFront()

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

	def getWindow(self):
		return self.window

	def getView(self):
		return self.view

	def printText(self, text):
		self.show_text += text
		if constant.sys_version < 3: 
			show_thread = threading.Thread(target=self.show)
			show_thread.start()
		else:
			self.update()

	def show(self):
		sublime.set_timeout(self.update, 0)

	def update(self):
		if self.show_text:
			text = self.show_text
			self.view.run_command('panel_output', {'text': text})
			self.show_text = ''

	def raiseToFront(self):
		self.window.focus_view(self.view)

class SerialMonitor:
	def __init__(self, serial_port):
		self.port = serial_port
		self.serial = pyserial.Serial()
		self.serial.port = serial_port

		self.is_alive = False
		self.name = 'Serial Monitor - ' + serial_port
		self.view = MonitorView(self.name)

	def isRunning(self):
		return self.is_alive

	def start(self):
		if not self.is_alive:
			baudrate_id = constant.sketch_settings.get('baudrate', 4)
			baudrate = int(constant.baudrate_list[baudrate_id])
			self.serial.baudrate = baudrate
			if serial.isSerialAvailable(self.port):
				self.serial.open()
				self.is_alive = True
				monitor_thread = threading.Thread(target=self.receive)
				monitor_thread.start()
			else:
				display_text = 'Serial port {0} already in use. Try quitting any programs that may be using it.'
				msg = display_text
				msg = msg.replace('{0}', self.port)
				self.view.printText(msg)

	def stop(self):
		self.is_alive = False

	def receive(self):
		length_before = 0
		while self.is_alive:
			number = self.serial.inWaiting()
			if number > 0:
				in_text = self.serial.read(number)
				length_in_text = len(in_text)
				in_text = convertMode(in_text, length_before)
				self.view.printText(in_text)

				length_before += length_in_text
				length_before %= 20
			time.sleep(0.01)
		self.serial.close()

	def send(self, out_text):
		line_ending_id = constant.sketch_settings.get('line_ending', 0)
		line_ending = constant.line_ending_list[line_ending_id]
		out_text += line_ending
		
		self.view.printText('[SEND] ' + out_text + '\n')
		out_text = out_text.encode('utf-8', 'replace')
		self.serial.write(out_text)
		
def isMonitorView(view):
	state = ''
	name = view.name()
	if name:
		if 'Serial Monitor - ' in name:
			state = True
	return state

def findInOpendView(view_name):
	opened_view = None
	found = False
	windows = sublime.windows()
	for window in windows:
		views = window.views()
		for view in views:
			name = view.name()
			if name == view_name:
				opened_view = view
				found = True
				break
		if found:
			break
	return opened_view

def convertMode(in_text, str_len = 0):
	text = u''
	display_mode = constant.sketch_settings.get('display_mode', 0)
	if display_mode == 0:
		text = in_text.decode('utf-8', 'replace')
	elif display_mode == 1:
		for character in in_text:
			text += chr(character)
	elif display_mode == 2:
		for (index, character) in enumerate(in_text):
			text += u'%02X ' % character
			if (index + str_len + 1) % 10 == 0:
				text += '\t'
			if (index + str_len + 1) % 20 == 0:
				text += '\n'
	return text
########NEW FILE########
__FILENAME__ = sketch
#-*- coding: utf-8 -*-
# stino/sketch.py

import os

import sublime

from . import constant
from . import fileutil
from . import preprocess

h_src_ext_list = ['.h']
ino_src_ext_list = ['.ino', '.pde']
c_src_ext_list = ['.c', '.cpp']
asm_src_ext_list = ['.asm', '.S']
src_ext_list = ['.ino', '.pde', '.c', '.cpp', '.asm', '.S']

class Project:
	def __init__(self, folder):
		self.setFolder(folder)
		
	def getFolder(self):
		return self.folder

	def getName(self):
		return self.name

	def getHSrcFileList(self):
		return self.h_file_list

	def getInoSrcFileList(self):
		return self.ino_src_file_list

	def getCSrcFileList(self):
		return self.c_src_file_list

	def getAsmSrcFileList(self):
		return self.asm_src_file_list

	def setFolder(self, folder):
		self.folder = folder
		self.name = os.path.split(folder)[1]
		self.h_src_file_list = fileutil.getFileListOfExt(folder, h_src_ext_list)
		self.c_src_file_list = fileutil.getFileListOfExt(folder, c_src_ext_list)
		self.asm_src_file_list = fileutil.getFileListOfExt(folder, asm_src_ext_list)
		self.ino_src_file_list = fileutil.getFileListOfExt(folder, ino_src_ext_list)
		if self.ino_src_file_list:
			self.ino_src_file_list = preprocess.sortSrcFileList(self.ino_src_file_list)

class SrcFile:
	def __init__(self):
		self.view = None
		self.sketch_name = ''
		self.view_name = ''
		self.file_name = ''
		self.folder = ''
		self.file_ext = ''

	def getFolder(self):
		return self.folder

	def getView(self):
		return self.view

	def getViewName(self):
		return self.view_name

	def getFileName(self):
		return self.file_name

	def getSketchName(self):
		return self.sketch_name

	def setView(self, view):
		self.view = view
		self.view_name = view.name()
		self.file_name = view.file_name()
		if self.file_name:
			self.folder = os.path.split(self.file_name)[0]
			self.file_ext = os.path.splitext(self.file_name)[1]
		else:
			self.folder = ''
			self.file_ext = ''

		if self.isSrcFile():
			self.sketch_name = os.path.split(self.folder)[1]
		else:
			self.sketch_name = ''

	def isSrcFile(self):
		state = False
		if self.file_ext in src_ext_list:
			state = True
		return state

def isSrcFile(cur_file):
	state = False
	ext = os.path.splitext(cur_file)[1]
	if ext in src_ext_list:
		state = True
	return state

def openSketchFolder(sketch_folder):	
	src_file_list = []
	if os.path.isdir(sketch_folder):
		file_name_list = fileutil.listDir(sketch_folder, with_dirs = False)
		for file_name in file_name_list:
			cur_file = os.path.join(sketch_folder, file_name)
			if isSrcFile(cur_file):
				src_file_list.append(cur_file)

	if src_file_list:
		sublime.run_command('new_window')
		window = sublime.windows()[-1]
		for src_file in src_file_list:
			window.open_file(src_file)

		addFolderToProject(window, sketch_folder)

def addFolderToProject(window, folder):
	if os.path.isdir(folder):	
		project_data = window.project_data()
		
		if not project_data:
			project_data = {'folders': []}
		
		project_data['folders'].append({'follow_symlinks': True, 'path': folder})
		window.set_project_data(project_data)
		
def importLibrary(view, lib_folder):
	include_text = '\n'
	H_src_file_list = getHSrcFileList(lib_folder)
	if H_src_file_list:
		for H_src_file in H_src_file_list:
			cur_text = '#include "' + H_src_file + '"\n'
			include_text += cur_text
		view.run_command('insert_include', {'include_text': include_text})

def isHSrcFile(cur_file):
	state = False
	ext = os.path.splitext(cur_file)[1]
	if ext in h_src_ext_list:
		state = True
	return state

def getHSrcFileListFromFolder(lib_folder):
	H_src_file_list = []
	folder_name_list = fileutil.listDir(lib_folder, with_files = False)
	file_name_list = fileutil.listDir(lib_folder,with_dirs = False)

	for folder_name in folder_name_list:
		if folder_name.lower() == 'examples':
			continue
		cur_folder = os.path.join(lib_folder, folder_name)
		sub_H_src_file_list = getHSrcFileList(cur_folder)
		for sub_H_src_file in sub_H_src_file_list:
			sub_H_src_file = folder_name + '/' + sub_H_src_file
			H_src_file_list.append(sub_H_src_file)
	
	for file_name in file_name_list:
		cur_file = os.path.join(lib_folder, file_name)
		if isHSrcFile(cur_file):
			H_src_file_list.append(file_name)
	return H_src_file_list

def getHSrcFileList(lib_folder, platform_name = ''):
	H_src_file_list = []
	lib_folder_list = expandCoreFolder(lib_folder, platform_name)

	for lib_folder in lib_folder_list:
		H_src_file_list += getHSrcFileListFromFolder(lib_folder)
	return H_src_file_list

def isCSrcFile(cur_file):
	state = False
	ext = os.path.splitext(cur_file)[1]
	if ext in c_src_ext_list:
		state = True
	return state

def getCSrcFileListFromFolder(core_folder, level = 0):
	C_src_file_list = []
	folder_name_list = fileutil.listDir(core_folder, with_files = False)
	file_name_list = fileutil.listDir(core_folder,with_dirs = False)

	if level < 1:
		for folder_name in folder_name_list:
			if folder_name.lower() == 'examples':
				continue
			cur_folder = os.path.join(core_folder, folder_name)
			sub_C_src_file_list = getCSrcFileListFromFolder(cur_folder, level + 1)
			C_src_file_list += sub_C_src_file_list
	
	for file_name in file_name_list:
		cur_file = os.path.join(core_folder, file_name)
		if isCSrcFile(cur_file):
			C_src_file_list.append(cur_file)
	return C_src_file_list

def getCSrcFileListFromFolderList(core_folder_list):
	C_src_file_list = []
	core_folder_list = expandCorFolderList(core_folder_list)
	for core_folder in core_folder_list:
		sub_C_src_file_list = getCSrcFileListFromFolder(core_folder)
		C_src_file_list += sub_C_src_file_list
	return C_src_file_list

def isAsmSrcFile(cur_file):
	state = False
	ext = os.path.splitext(cur_file)[1]
	if ext in asm_src_ext_list:
		state = True
	return state

def getAsmSrcFileListFromFolder(core_folder, level = 0):
	asm_src_file_list = []
	folder_name_list = fileutil.listDir(core_folder, with_files = False)
	file_name_list = fileutil.listDir(core_folder,with_dirs = False)

	if level < 1:
		for folder_name in folder_name_list:
			if folder_name.lower() == 'examples':
				continue
			cur_folder = os.path.join(core_folder, folder_name)
			sub_asm_src_file_list = getAsmSrcFileListFromFolder(cur_folder, level + 1)
			asm_src_file_list += sub_asm_src_file_list
	
	for file_name in file_name_list:
		cur_file = os.path.join(core_folder, file_name)
		if isAsmSrcFile(cur_file):
			asm_src_file_list.append(cur_file)
	return asm_src_file_list

def getAsmSrcFileListFromFolderList(core_folder_list):
	asm_src_file_list = []
	core_folder_list = expandCorFolderList(core_folder_list)
	for core_folder in core_folder_list:
		sub_asm_src_file_list = getAsmSrcFileListFromFolder(core_folder)
		asm_src_file_list += sub_asm_src_file_list
	return asm_src_file_list

def getFolderListFromFolder(core_folder, level = 0):
	folder_list = [core_folder]
	if level < 1:
		folder_name_list = fileutil.listDir(core_folder, with_files = False)
		for folder_name in folder_name_list:
			if folder_name.lower() == 'examples':
				continue
			cur_folder = os.path.join(core_folder, folder_name)
			folder_list += getFolderListFromFolder(cur_folder, level + 1)
	return folder_list

def getFolderListFromFolderList(core_folder_list):
	folder_list = []
	core_folder_list = expandCorFolderList(core_folder_list)
	for core_folder in core_folder_list:
		folder_list += getFolderListFromFolder(core_folder)
	return folder_list

def expandCoreFolder(lib_folder, platform_name = ''):
	lib_folder_list = []
	if not platform_name:
		platform_name = constant.sketch_settings.get('platform_name', 'General')

	arduino_folder = constant.sketch_settings.get('arduino_folder', '')
	lib_src_folder = os.path.join(lib_folder, 'src')
	if not os.path.isdir(lib_src_folder) or (os.path.isdir(lib_src_folder) and not arduino_folder in lib_src_folder ):
		lib_folder_list.append(lib_folder)
	else:
		lib_folder_list.append(lib_src_folder)
		arch_folder = os.path.join(lib_folder, 'arch')
		avr_folder = os.path.join(arch_folder, 'avr')
		sam_folder = os.path.join(arch_folder, 'sam')
		if 'AVR' in platform_name:
			if os.path.isdir(avr_folder):
				lib_folder_list.append(avr_folder)
		if 'ARM' in platform_name:
			if os.path.isdir(sam_folder):
				lib_folder_list.append(sam_folder)
	return lib_folder_list

def expandCorFolderList(core_folder_list, platform_name = ''):
	folder_list = []
	for core_folder in core_folder_list:
		folder_list += expandCoreFolder(core_folder, platform_name)
	return folder_list

def isInEditor(view):
	view_name = view.name()
	file_name = view.file_name()
	state = False
	if view_name or file_name:
		state = True
	return state

########NEW FILE########
__FILENAME__ = syntax
#-*- coding: utf-8 -*-
# stino/syntax.py

import os

from . import constant
from . import fileutil

class Syntax:
	def __init__(self, arduino_info, file_name):
		self.arduino_info = arduino_info
		self.file_name = file_name
		self.constant_keyword_list = []
		self.common_keyword_list = []
		self.function_keyword_list = []
		self.refresh()

	def refresh(self):
		self.classifyKeywordList()
		self.genFile()

	def classifyKeywordList(self):
		keyword_list = self.arduino_info.getKeywordList()
		for keyword in keyword_list:
			keyword_name = keyword.getName()
			if len(keyword_name) > 1:
				keyword_type = keyword.getType()
				if keyword_type:
					if 'LITERAL' in keyword_type:
						self.constant_keyword_list.append(keyword)
					elif keyword_type == 'KEYWORD1':
						self.common_keyword_list.append(keyword)
					else:
						self.function_keyword_list.append(keyword)

	def genFile(self):
		text = ''
		text += genDictBlock(self.constant_keyword_list, 'constant.arduino')
		text += genDictBlock(self.common_keyword_list, 'storage.modifier.arduino')
		text += genDictBlock(self.function_keyword_list, 'support.function.arduino')

		temp_file = os.path.join(constant.config_root, 'syntax')
		# opened_file = open(temp_file, 'r')
		# syntax_text = opened_file.read()
		# opened_file.close()
		syntax_text = fileutil.readFile(temp_file)

		syntax_text = syntax_text.replace('(_$dict$_)', text)
		syntax_file = os.path.join(constant.stino_root, self.file_name)
		# opened_file = open(syntax_file, 'w')
		# opened_file.write(syntax_text)
		# opened_file.close()
		fileutil.writeFile(syntax_file, syntax_text)

def genDictBlock(keyword_list, description):
	dict_text = ''
	if keyword_list:
		dict_text += '\t' * 2
		dict_text += '<dict>\n'
		dict_text += '\t' * 3
		dict_text += '<key>match</key>\n'
		dict_text += '\t' * 3
		dict_text += '<string>\\b('
		for keyword in keyword_list:
			dict_text += keyword.getName()
			dict_text += '|'
		dict_text = dict_text[:-1]
		dict_text += ')\\b</string>\n'
		dict_text += '\t' * 3
		dict_text += '<key>name</key>\n'
		dict_text += '\t' * 3
		dict_text += '<string>'
		dict_text += description
		dict_text += '</string>\n'
		dict_text += '\t' * 2
		dict_text += '</dict>\n'
	return dict_text
########NEW FILE########
__FILENAME__ = textutil
#-*- coding: utf-8 -*-
# stino/textutil.py

def getKeyValue(line):
	line = line.strip()
	if '=' in line:
		index = line.index('=')
		key = line[:index].strip()
		value = line[(index+1):].strip()
	else:
		key = ''
		value = ''
	return (key, value)

def getBlockList(lines, sep = '.name'):
	block_list = []
	block = []
	for line in lines:
		line = line.strip()
		if line and (not '#' in line):
			if (sep in line) and (not '.menu' in line):
				block_list.append(block)
				block = [line]
			else:
				block.append(line)
	block_list.append(block)
	return block_list
########NEW FILE########
__FILENAME__ = tools
#-*- coding: utf-8 -*-
# stino/tools.py

import os
import zipfile

from . import fileutil

def archiveSketch(source_folder, target_file):
	os.chdir(source_folder)
	file_name_list = fileutil.listDir(source_folder, with_dirs = False)
	try:
		opened_zipfile = zipfile.ZipFile(target_file, 'w' ,zipfile.ZIP_DEFLATED)
	except IOError:
		return_code = 1
	else:
		for file_name in file_name_list:
			opened_zipfile.write(file_name)
		opened_zipfile.close()
		return_code = 0
	return return_code

########NEW FILE########
__FILENAME__ = uploader
#-*- coding: utf-8 -*-
# stino/uploader.py

import threading
import time

from . import constant
from . import compiler
from . import console
from . import serial
from . import pyserial

class Uploader:
	def __init__(self, args, cur_compiler, mode = 'upload'):
		self.args = args.getArgs()
		self.mode = mode
		self.compiler = cur_compiler
		self.command_list = []
		self.output_console = cur_compiler.getOutputConsole()
		self.no_error = True

		upload_command_text = ''
		if mode == 'upload':
			if 'upload.pattern' in self.args:
				upload_command_text = self.args['upload.pattern']
		elif mode == 'programmer':
			if 'program.pattern' in self.args:
				upload_command_text = self.args['program.pattern']

		if upload_command_text:
			upload_command = compiler.Command(upload_command_text)
			upload_command.setOutputText('Uploading...\n')
			self.command_list.append(upload_command)

		if 'reboot.pattern' in self.args:
			reboot_command_text = self.args['reboot.pattern']
			reboot_command = compiler.Command(reboot_command_text)
			self.command_list.append(reboot_command)

	def run(self):
		if self.command_list:
			upload_thread = threading.Thread(target=self.upload)
			upload_thread.start()
		else:
			self.no_error = False

	def upload(self):
		while not self.compiler.isFinished():
			time.sleep(0.5)
		if not self.compiler.noError():
			return

		serial_port = serial.getSelectedSerialPort()
		
		serial_monitor = None
		if serial_port in constant.serial_in_use_list:
			serial_monitor = constant.serial_monitor_dict[serial_port]
			serial_monitor.stop()

		force_to_reset = False
		if self.mode == 'upload':
			if 'bootloader.file' in self.args:
				if 'caterina' in self.args['bootloader.file'].lower():
					force_to_reset = True
			elif self.args.get('upload.use_1200bps_touch', 'false') == 'true':
				force_to_reset = True

			if force_to_reset:
				pre_serial_port = serial_port
				wait_for_upload_port = self.args.get('upload.wait_for_upload_port', 'false') == 'true'
				serial_port = resetSerial(pre_serial_port, self.output_console, wait_for_upload_port)
				if self.args['cmd'] != 'avrdude':
					if serial_port.startswith('/dev/'):
						serial_port = serial_port[5:]
				if serial_port:
					for cur_command in self.command_list:
						command_text = cur_command.getCommand()
						command_text = command_text.replace(pre_serial_port, serial_port)
						cur_command.setCommand(command_text)

		for cur_command in self.command_list:
			return_code = cur_command.run(self.output_console)
			if return_code > 0:
				self.output_console.printText('[Stino - Error %d]\n' % return_code)
				self.no_error = False
				break

		if self.no_error:
			self.output_console.printText('[Stino - Done uploading.]\n')

		if force_to_reset:
			time.sleep(5)

		if serial_monitor:
			serial_monitor.start()

def touchSerialPort(serial_port, baudrate):
	cur_serial = pyserial.Serial()
	cur_serial.port = serial_port
	cur_serial.baudrate = baudrate
	cur_serial.bytesize = pyserial.EIGHTBITS
	cur_serial.stopbits = pyserial.STOPBITS_ONE
	cur_serial.parity = pyserial.PARITY_NONE
	cur_serial.open()
	cur_serial.close()

def resetSerial(serial_port, output_console, wait_for_upload_port):
	show_upload_output = constant.sketch_settings.get('show_upload_output', False)

	caterina_serial_port = ''
	before_serial_list = serial.getSerialPortList()
	if serial_port in before_serial_list:
		non_serial_list = before_serial_list[:]
		non_serial_list.remove(serial_port)

		if show_upload_output:
			msg = 'Forcing reset using 1200bps open/close on port %s.\n' % serial_port
			output_console.printText(msg)
		touchSerialPort(serial_port, 1200)

		if not wait_for_upload_port:
			time.sleep(0.4)
			return serial_port

		# Scanning for available ports seems to open the port or
		# otherwise assert DTR, which would cancel the WDT reset if
		# it happened within 250 ms. So we wait until the reset should
		# have already occured before we start scanning.
		if constant.sys_platform == 'windows':
			time.sleep(3)
		else:
			time.sleep(0.3)

		# Wait for a port to appear on the list
		elapsed = 0
		while (elapsed < 10000):
			now_serial_list = serial.getSerialPortList()
			diff_serial_list = diffList(now_serial_list, non_serial_list)

			if show_upload_output:
				msg = 'Ports {%s}/{%s} => {%s}\n' % (before_serial_list, now_serial_list, 
					diff_serial_list)
				output_console.printText(msg)
			if len(diff_serial_list) > 0:
				caterina_serial_port = diff_serial_list[0]
				if show_upload_output:
					msg = 'Found new upload port: %s.\n' % caterina_serial_port
					output_console.printText(msg)
				break

			# Keep track of port that disappears
			# before_serial_list = now_serial_list
			time.sleep(0.25)
			elapsed += 250

			# On Windows, it can take a long time for the port to disappear and
			# come back, so use a longer time out before assuming that the selected
			# port is the bootloader (not the sketch).
			if (((constant.sys_platform != 'windows' and elapsed >= 500) 
				or elapsed >= 5000) and (serial_port in now_serial_list)):
				if show_upload_output:
					msg = 'Uploading using selected port: %s.\n' % serial_port
					output_console.printText(msg)
				caterina_serial_port = serial_port
				break

		if not caterina_serial_port:
			msg = 'Couldn\'t find a Leonardo on the selected port.\nCheck that you have the correct port selected.\nIf it is correct, try pressing the board\'s reset button after initiating the upload.\n'
			output_console.printText(msg)
	return caterina_serial_port

class Bootloader:
	def __init__(self, cur_project, args):
		self.args = args.getArgs()
		erase_command_text = self.args['erase.pattern']
		burn_command_text = self.args['bootloader.pattern']
		erase_command = compiler.Command(erase_command_text)
		burn_command = compiler.Command(burn_command_text)
		self.command_list = [erase_command, burn_command]
		self.output_console = console.Console(cur_project.getName())

	def start(self):
		upload_thread = threading.Thread(target=self.burn)
		upload_thread.start()

	def burn(self):
		for cur_command in self.command_list:
			return_code = cur_command.run(self.output_console)
			if return_code > 0:
				self.output_console.printText('[Error %d]\n' % return_code)
				break

def diffList(now_list, before_list):
	diff_list = now_list
	for before_item in before_list:
		if before_item in diff_list:
			diff_list.remove(before_item)
	return diff_list

########NEW FILE########
__FILENAME__ = StinoStarter
#-*- coding: utf-8 -*-
# StinoStarter.py

import os
import sublime
import sublime_plugin

st_version = int(sublime.version())
if st_version < 3000:
	import app
else:
	from . import app

class SketchListener(sublime_plugin.EventListener):
	def on_activated(self, view):
		pre_active_sketch = app.constant.global_settings.get('active_sketch', '')

		if not app.sketch.isInEditor(view):
			return

		app.active_file.setView(view)
		active_sketch = app.active_file.getSketchName()
		app.constant.global_settings.set('active_sketch', active_sketch)

		if app.active_file.isSrcFile():
			app.active_serial_listener.start()
			temp_global = app.constant.global_settings.get('temp_global', False)
			if temp_global:
				app.constant.global_settings.set('global_settings', False)
				app.constant.global_settings.set('temp_global', False)
			global_settings = app.constant.global_settings.get('global_settings', True)
			if not global_settings:
				if not (active_sketch == pre_active_sketch):
					folder = app.active_file.getFolder()
					app.constant.sketch_settings.changeFolder(folder)
					app.arduino_info.refresh()
					app.main_menu.refresh()
		else:
			app.active_serial_listener.stop()
			global_settings = app.constant.global_settings.get('global_settings', True)
			if not global_settings:
				app.constant.global_settings.set('global_settings', True)
				app.constant.global_settings.set('temp_global', True)
				folder = app.constant.stino_root
				app.constant.sketch_settings.changeFolder(folder)
				app.arduino_info.refresh()
				app.main_menu.refresh()

	def on_close(self, view):
		if app.serial_monitor.isMonitorView(view):
			name = view.name()
			serial_port = name.split('-')[1].strip()
			if serial_port in app.constant.serial_in_use_list:
				cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
				cur_serial_monitor.stop()
				app.constant.serial_in_use_list.remove(serial_port)

class ShowArduinoMenuCommand(sublime_plugin.WindowCommand):
	def run(self):
		show_arduino_menu = not app.constant.global_settings.get('show_arduino_menu', True)
		app.constant.global_settings.set('show_arduino_menu', show_arduino_menu)
		app.main_menu.refresh()

	def is_checked(self):
		state = app.constant.global_settings.get('show_arduino_menu', True)
		return state

class NewSketchCommand(sublime_plugin.WindowCommand):
	def run(self):
		caption = app.i18n.translate('Name for New Sketch')
		self.window.show_input_panel(caption, '', self.on_done, None, None)

	def on_done(self, input_text):
		sketch_name = input_text
		if sketch_name:
			sketch_file = app.base.newSketch(sketch_name)
			if sketch_file:
				self.window.open_file(sketch_file)
				app.arduino_info.refresh()
				app.main_menu.refresh()
			else:
				app.output_console.printText('A sketch (or folder) named "%s" already exists. Could not create the sketch.\n' % sketch_name)

class OpenSketchCommand(sublime_plugin.WindowCommand):
	def run(self, folder):
		app.sketch.openSketchFolder(folder)

class ImportLibraryCommand(sublime_plugin.WindowCommand):
	def run(self, folder):
		view = app.active_file.getView()
		self.window.active_view().run_command('save')
		app.sketch.importLibrary(view, folder)

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class ShowSketchFolderCommand(sublime_plugin.WindowCommand):
	def run(self):
		folder = app.active_file.getFolder()
		url = 'file://' + folder
		sublime.run_command('open_url', {'url': url})

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class SetExtraFlagCommand(sublime_plugin.WindowCommand):
	def run(self):
		extra_flag = app.constant.sketch_settings.get('extra_flag', '')
		caption = app.i18n.translate('Extra compilation flags:')
		self.window.show_input_panel(caption, extra_flag, self.on_done, None, None)

	def on_done(self, input_text):
		extra_flag = input_text
		app.constant.sketch_settings.set('extra_flag', extra_flag)

class CompileSketchCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.active_view().run_command('save')
		cur_folder = app.active_file.getFolder()
		cur_project = app.sketch.Project(cur_folder)

		args = app.compiler.Args(cur_project, app.arduino_info)
		compiler = app.compiler.Compiler(app.arduino_info, cur_project, args)
		compiler.run()

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class UploadSketchCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.active_view().run_command('save')
		cur_folder = app.active_file.getFolder()
		cur_project = app.sketch.Project(cur_folder)

		args = app.compiler.Args(cur_project, app.arduino_info)
		compiler = app.compiler.Compiler(app.arduino_info, cur_project, args)
		compiler.run()
		uploader = app.uploader.Uploader(args, compiler)
		uploader.run()

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class UploadUsingProgrammerCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.active_view().run_command('save')
		cur_folder = app.active_file.getFolder()
		cur_project = app.sketch.Project(cur_folder)

		args = app.compiler.Args(cur_project, app.arduino_info)
		compiler = app.compiler.Compiler(app.arduino_info, cur_project, args)
		compiler.run()
		uploader = app.uploader.Uploader(args, compiler, mode = 'programmer')
		uploader.run()

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			platform_list = app.arduino_info.getPlatformList()
			platform_id = app.constant.sketch_settings.get('platform', -1)
			if (platform_id > 0) and (platform_id < len(platform_list)):
				platform = platform_list[platform_id]
				programmer_list = platform.getProgrammerList()
				if programmer_list:
					state = True
		return state

class ChooseBoardCommand(sublime_plugin.WindowCommand):
	def run(self, platform, board):
		cur_platform = app.arduino_info.getPlatformList()[platform]
		app.constant.sketch_settings.set('platform', platform)
		app.constant.sketch_settings.set('platform_name', cur_platform.getName())
		app.constant.sketch_settings.set('board', board)
		app.main_menu.refresh()
		app.constant.sketch_settings.set('full_compilation', True)

	def is_checked(self, platform, board):
		state = False
		chosen_platform = app.constant.sketch_settings.get('platform', -1)
		chosen_board = app.constant.sketch_settings.get('board', -1)
		if platform == chosen_platform and board == chosen_board:
			state = True
		return state

class ChooseBoardOptionCommand(sublime_plugin.WindowCommand):
	def run(self, board_option, board_option_item):
		has_setted = False
		chosen_platform = app.constant.sketch_settings.get('platform')
		chosen_board = app.constant.sketch_settings.get('board')
		board_id = str(chosen_platform) + '.' + str(chosen_board)
		board_option_settings = app.constant.sketch_settings.get('board_option', {})
		if board_id in board_option_settings:
			cur_board_option_setting = board_option_settings[board_id]
			if board_option < len(cur_board_option_setting):
				has_setted = True

		if not has_setted:
			platform_list = app.arduino_info.getPlatformList()
			cur_platform = platform_list[chosen_platform]
			board_list = cur_platform.getBoardList()
			cur_board = board_list[chosen_board]
			board_option_list = cur_board.getOptionList()
			board_option_list_number = len(board_option_list)
			cur_board_option_setting = []
			for i in range(board_option_list_number):
				cur_board_option_setting.append(0)

		cur_board_option_setting[board_option] = board_option_item
		board_option_settings[board_id] = cur_board_option_setting
		app.constant.sketch_settings.set('board_option', board_option_settings)
		app.constant.sketch_settings.set('full_compilation', True)

	def is_checked(self, board_option, board_option_item):
		state = False
		chosen_platform = app.constant.sketch_settings.get('platform', -1)
		chosen_board = app.constant.sketch_settings.get('board', -1)
		board_id = str(chosen_platform) + '.' + str(chosen_board)
		board_option_settings = app.constant.sketch_settings.get('board_option', {})
		if board_id in board_option_settings:
			cur_board_option_setting = board_option_settings[board_id]
			if board_option < len(cur_board_option_setting):
				chosen_board_option_item = cur_board_option_setting[board_option]
				if board_option_item == chosen_board_option_item:
					state = True
		return state

class ChooseProgrammerCommand(sublime_plugin.WindowCommand):
	def run(self, platform, programmer):
		programmer_settings = app.constant.sketch_settings.get('programmer', {})
		programmer_settings[str(platform)] = programmer
		app.constant.sketch_settings.set('programmer', programmer_settings)

	def is_checked(self, platform, programmer):
		state = False
		programmer_settings = app.constant.sketch_settings.get('programmer', {})
		if str(platform) in programmer_settings:
			chosen_programmer = programmer_settings[str(platform)]
			if programmer == chosen_programmer:
				state = True
		return state

class BurnBootloaderCommand(sublime_plugin.WindowCommand):
	def run(self):
		cur_folder = app.active_file.getFolder()
		cur_project = app.sketch.Project(cur_folder)

		args = app.compiler.Args(cur_project, app.arduino_info)
		bootloader = app.uploader.Bootloader(cur_project, args)
		bootloader.burn()

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class ChooseSerialPortCommand(sublime_plugin.WindowCommand):
	def run(self, serial_port):
		app.constant.sketch_settings.set('serial_port', serial_port)

	def is_checked(self, serial_port):
		state = False
		chosen_serial_port = app.constant.sketch_settings.get('serial_port', -1)
		if serial_port == chosen_serial_port:
			state = True
		return state

class StartSerialMonitorCommand(sublime_plugin.WindowCommand):
	def run(self):
		serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
		serial_port_list = app.serial.getSerialPortList()
		serial_port = serial_port_list[serial_port_id]
		if serial_port in app.constant.serial_in_use_list:
			cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
		else:
			cur_serial_monitor = app.serial_monitor.SerialMonitor(serial_port)
			app.constant.serial_in_use_list.append(serial_port)
			app.constant.serial_monitor_dict[serial_port] = cur_serial_monitor
		cur_serial_monitor.start()
		self.window.run_command('send_serial_text')

	def is_enabled(self):
		state = False
		serial_port_list = app.serial.getSerialPortList()
		if serial_port_list:
			serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
			serial_port = serial_port_list[serial_port_id]
			if serial_port in app.constant.serial_in_use_list:
				cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
				if not cur_serial_monitor.isRunning():
					state = True
			else:
				state = True
		return state

class StopSerialMonitorCommand(sublime_plugin.WindowCommand):
	def run(self):
		serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
		serial_port_list = app.serial.getSerialPortList()
		serial_port = serial_port_list[serial_port_id]
		cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
		cur_serial_monitor.stop()

	def is_enabled(self):
		state = False
		serial_port_list = app.serial.getSerialPortList()
		if serial_port_list:
			serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
			serial_port = serial_port_list[serial_port_id]
			if serial_port in app.constant.serial_in_use_list:
				cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
				if cur_serial_monitor.isRunning():
					state = True
		return state

class SendSerialTextCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.caption = 'Send'
		self.window.show_input_panel(self.caption, '', self.on_done, None, None)

	def on_done(self, input_text):
		serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
		serial_port_list = app.serial.getSerialPortList()
		serial_port = serial_port_list[serial_port_id]
		cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
		cur_serial_monitor.send(input_text)
		self.window.show_input_panel(self.caption, '', self.on_done, None, None)

	def is_enabled(self):
		state = False
		serial_port_list = app.serial.getSerialPortList()
		if serial_port_list:
			serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
			serial_port = serial_port_list[serial_port_id]
			if serial_port in app.constant.serial_in_use_list:
				cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
				if cur_serial_monitor.isRunning():
					state = True
		return state

class ChooseLineEndingCommand(sublime_plugin.WindowCommand):
	def run(self, line_ending):
		app.constant.sketch_settings.set('line_ending', line_ending)

	def is_checked(self, line_ending):
		state = False
		chosen_line_ending = app.constant.sketch_settings.get('line_ending', 0)
		if line_ending == chosen_line_ending:
			state = True
		return state

class ChooseDisplayModeCommand(sublime_plugin.WindowCommand):
	def run(self, display_mode):
		app.constant.sketch_settings.set('display_mode', display_mode)

	def is_checked(self, display_mode):
		state = False
		chosen_display_mode = app.constant.sketch_settings.get('display_mode', 0)
		if display_mode == chosen_display_mode:
			state = True
		return state

class ChooseBaudrateCommand(sublime_plugin.WindowCommand):
	def run(self, baudrate):
		app.constant.sketch_settings.set('baudrate', baudrate)

	def is_checked(self, baudrate):
		state = False
		chosen_baudrate = app.constant.sketch_settings.get('baudrate', -1)
		if baudrate == chosen_baudrate:
			state = True
		return state

	def is_enabled(self):
		state = True
		serial_port_list = app.serial.getSerialPortList()
		if serial_port_list:
			serial_port_id = app.constant.sketch_settings.get('serial_port', 0)
			serial_port = serial_port_list[serial_port_id]
			if serial_port in app.constant.serial_in_use_list:
				cur_serial_monitor = app.constant.serial_monitor_dict[serial_port]
				if cur_serial_monitor.isRunning():
					state = False
		return state

class AutoFormatCommand(sublime_plugin.WindowCommand):
	def run(self):
		self.window.run_command('reindent', {'single_line': False})

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class ArchiveSketchCommand(sublime_plugin.WindowCommand):
	def run(self):
		root_list = app.fileutil.getOSRootList()
		self.top_folder_list = root_list
		self.folder_list = self.top_folder_list
		self.level = 0
		self.show_panel()

	def show_panel(self):
		folder_name_list = app.fileutil.getFolderNameList(self.folder_list)
		sublime.set_timeout(lambda: self.window.show_quick_panel(folder_name_list, self.on_done), 10)

	def on_done(self, index):
		is_finished = False
		if index == -1:
			return

		if self.level != 0 and index == 0:
			chosen_folder = self.folder_list[index]
			chosen_folder = chosen_folder.split('(')[1]
			chosen_folder = chosen_folder[:-1]

			source_folder = app.active_file.getFolder()
			sketch_name = app.active_file.getSketchName()
			zip_file_name = sketch_name + '.zip'
			zip_file = os.path.join(chosen_folder, zip_file_name)
			return_code = app.tools.archiveSketch(source_folder, zip_file)
			if return_code == 0:
				app.output_console.printText(app.i18n.translate('Writing {0} done.\n', [zip_file]))
			else:
				app.output_console.printText(app.i18n.translate('Writing {0} failed.\n', [zip_file]))
		else:
			(self.folder_list, self.level) = app.fileutil.enterNextLevel(index, self.folder_list, self.level, self.top_folder_list)
			self.show_panel()

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class ChooseArduinoFolderCommand(sublime_plugin.WindowCommand):
	def run(self):
		root_list = app.fileutil.getOSRootList()
		self.top_folder_list = root_list
		self.folder_list = self.top_folder_list
		self.level = 0
		self.show_panel()

	def show_panel(self):
		folder_name_list = app.fileutil.getFolderNameList(self.folder_list)
		sublime.set_timeout(lambda: self.window.show_quick_panel(folder_name_list, self.on_done), 10)

	def on_done(self, index):
		is_finished = False
		if index == -1:
			return

		chosen_folder = self.folder_list[index]
		if app.base.isArduinoFolder(chosen_folder):
			app.output_console.printText(app.i18n.translate('Arduino Application is found at {0}.\n', [chosen_folder]))
			app.constant.sketch_settings.set('arduino_folder', chosen_folder)
			app.arduino_info.refresh()
			app.main_menu.refresh()
			app.output_console.printText('Arduino %s.\n' % app.arduino_info.getVersionText())
			app.constant.sketch_settings.set('full_compilation', True)
		else:
			(self.folder_list, self.level) = app.fileutil.enterNextLevel(index, self.folder_list, self.level, self.top_folder_list)
			self.show_panel()

class ChangeSketchbookFolderCommand(sublime_plugin.WindowCommand):
	def run(self):
		root_list = app.fileutil.getOSRootList()
		self.top_folder_list = root_list
		self.folder_list = self.top_folder_list
		self.level = 0
		self.show_panel()

	def show_panel(self):
		folder_name_list = app.fileutil.getFolderNameList(self.folder_list)
		sublime.set_timeout(lambda: self.window.show_quick_panel(folder_name_list, self.on_done), 10)

	def on_done(self, index):
		is_finished = False
		if index == -1:
			return

		if self.level != 0 and index == 0:
			chosen_folder = self.folder_list[index]
			chosen_folder = chosen_folder.split('(')[1]
			chosen_folder = chosen_folder[:-1]
			app.output_console.printText(app.i18n.translate('Sketchbook is changed to {0}.\n', [chosen_folder]))
			app.constant.global_settings.set('sketchbook_folder', chosen_folder)
			app.arduino_info.refresh()
			app.main_menu.refresh()
			app.constant.sketch_settings.set('full_compilation', True)
		else:
			(self.folder_list, self.level) = app.fileutil.enterNextLevel(index, self.folder_list, self.level, self.top_folder_list)
			self.show_panel()

class ChooseBuildFolderCommand(sublime_plugin.WindowCommand):
	def run(self):
		root_list = app.fileutil.getOSRootList()
		self.top_folder_list = root_list
		self.folder_list = self.top_folder_list
		self.level = 0
		self.show_panel()

	def show_panel(self):
		folder_name_list = app.fileutil.getFolderNameList(self.folder_list)
		sublime.set_timeout(lambda: self.window.show_quick_panel(folder_name_list, self.on_done), 10)

	def on_done(self, index):
		is_finished = False
		if index == -1:
			return

		if self.level != 0 and index == 0:
			chosen_folder = self.folder_list[index]
			chosen_folder = chosen_folder.split('(')[1]
			chosen_folder = chosen_folder[:-1]
			app.output_console.printText(app.i18n.translate('Build folder is changed to {0}.\n', [chosen_folder]))
			app.constant.sketch_settings.set('build_folder', chosen_folder)
			app.constant.sketch_settings.set('full_compilation', True)
		else:
			(self.folder_list, self.level) = app.fileutil.enterNextLevel(index, self.folder_list, self.level, self.top_folder_list)
			self.show_panel()

class ChooseLanguageCommand(sublime_plugin.WindowCommand):
	def run(self, language):
		pre_language = app.constant.global_settings.get('language', -1)
		if language != pre_language:
			app.constant.global_settings.set('language', language)
			app.i18n.refresh()
			app.main_menu.refresh()

	def is_checked(self, language):
		state = False
		chosen_language = app.constant.global_settings.get('language', -1)
		if language == chosen_language:
			state = True
		return state

class SetGlobalSettingCommand(sublime_plugin.WindowCommand):
	def run(self):
		if app.active_file.isSrcFile():
			global_settings = not app.constant.global_settings.get('global_settings', True)
			app.constant.global_settings.set('global_settings', global_settings)

			if global_settings:
				folder = app.constant.stino_root
			else:
				folder = app.active_file.getFolder()
			app.constant.sketch_settings.changeFolder(folder)
			app.arduino_info.refresh()
			app.main_menu.refresh()
		else:
			temp_global = not app.constant.global_settings.get('temp_global', False)
			app.constant.global_settings.set('temp_global', temp_global)

	def is_checked(self):
		state = app.constant.global_settings.get('global_settings', True)
		return state

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class SetFullCompilationCommand(sublime_plugin.WindowCommand):
	def run(self):
		full_compilation = not app.constant.sketch_settings.get('full_compilation', True)
		app.constant.sketch_settings.set('full_compilation', full_compilation)

	def is_checked(self):
		state = app.constant.sketch_settings.get('full_compilation', True)
		return state

class ShowCompilationOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		show_compilation_output = not app.constant.sketch_settings.get('show_compilation_output', False)
		app.constant.sketch_settings.set('show_compilation_output', show_compilation_output)

	def is_checked(self):
		state = app.constant.sketch_settings.get('show_compilation_output', False)
		return state

class ShowUploadOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		show_upload_output = not app.constant.sketch_settings.get('show_upload_output', False)
		app.constant.sketch_settings.set('show_upload_output', show_upload_output)

	def is_checked(self):
		state = app.constant.sketch_settings.get('show_upload_output', False)
		return state

class SetBareGccOnlyCommand(sublime_plugin.WindowCommand):
	def run(self):
		set_bare_gcc_only = not app.constant.sketch_settings.get('set_bare_gcc_only', False)
		app.constant.sketch_settings.set('set_bare_gcc_only', set_bare_gcc_only)

	def is_checked(self):
		state = app.constant.sketch_settings.get('set_bare_gcc_only', False)
		return state

class VerifyCodeCommand(sublime_plugin.WindowCommand):
	def run(self):
		verify_code = not app.constant.sketch_settings.get('verify_code', False)
		app.constant.sketch_settings.set('verify_code', verify_code)

	def is_checked(self):
		state = app.constant.sketch_settings.get('verify_code', False)
		return state


class OpenRefCommand(sublime_plugin.WindowCommand):
	def run(self, url):
		url = app.base.getUrl(url)
		sublime.run_command('open_url', {'url': url})

class FindInReferenceCommand(sublime_plugin.WindowCommand):
	def run(self):
		ref_list = []
		keyword_ref_dict = app.arduino_info.getKeywordRefDict()
		view = app.active_file.getView()
		selected_word_list = app.base.getSelectedWordList(view)
		for selected_word in selected_word_list:
			if selected_word in keyword_ref_dict:
				ref = keyword_ref_dict[selected_word]
				if not ref in ref_list:
					ref_list.append(ref)
		for ref in ref_list:
			url = app.base.getUrl(ref)
			sublime.run_command('open_url', {'url': url})

	def is_enabled(self):
		state = False
		if app.active_file.isSrcFile():
			state = True
		return state

class AboutStinoCommand(sublime_plugin.WindowCommand):
	def run(self):
		sublime.run_command('open_url', {'url': 'https://github.com/Robot-Will/Stino'})

class PanelOutputCommand(sublime_plugin.TextCommand):
	def run(self, edit, text):
		pos = self.view.size()
		self.view.insert(edit, pos, text)
		self.view.show(pos)

class InsertIncludeCommand(sublime_plugin.TextCommand):
	def run(self, edit, include_text):
		view_size = self.view.size()
		region = sublime.Region(0, view_size)
		src_text = self.view.substr(region)
		include_list = app.preprocess.genIncludeList(src_text)
		if include_list:
			last_include = include_list[-1]
			index = src_text.index(last_include) + len(last_include)
		else:
			index = 0
		self.view.insert(edit, index, include_text)

########NEW FILE########
