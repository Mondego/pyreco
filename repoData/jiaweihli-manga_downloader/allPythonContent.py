__FILENAME__ = book
#!/usr/bin/env python

# Copyright (C) 2010  Alex Yatskov
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


import os

import image
import imghdr
from image import ImageFlags
from convert import BookConvert
import shutil

class Book:
    DefaultDevice = 'Kindle 3'
    DefaultOverwrite = True
    DefaultImageFlags = ImageFlags.Orient | ImageFlags.Resize | ImageFlags.Quantize


    def __init__(self):
        self.images = []
        self.filename = None
        self.modified = False
        self.title = None
        self.device = Book.DefaultDevice
        self.overwrite = Book.DefaultOverwrite
        self.imageFlags = Book.DefaultImageFlags


    def save(self, filename):
        document = QtXml.QDomDocument()

        root = document.createElement('book')
        document.appendChild(root)

        root.setAttribute('title', self.title)
        root.setAttribute('overwrite', 'true' if self.overwrite else 'false')
        root.setAttribute('device', self.device)
        root.setAttribute('imageFlags', self.imageFlags)

        for filenameImg in self.images:
            itemImg = document.createElement('image')
            root.appendChild(itemImg)
            itemImg.setAttribute('filename', filenameImg)

        textXml = document.toString(4).toUtf8()

        try:
            fileXml = open(unicode(filename), 'w')
            fileXml.write(textXml)
            fileXml.close()
        except IOError:
            raise RuntimeError('Cannot create book file %s' % filename)

        self.filename = filename
        self.modified = False


    def load(self, filename):
        try:
            fileXml = open(unicode(filename), 'r')
            textXml = fileXml.read()
            fileXml.close()
        except IOError:
            raise RuntimeError('Cannot open book file %s' % filename)

        document = QtXml.QDomDocument()

        if not document.setContent(QtCore.QString.fromUtf8(textXml)):
            raise RuntimeError('Error parsing book file %s' % filename)

        root = document.documentElement()
        if root.tagName() != 'book':
            raise RuntimeError('Unexpected book format in file %s' % filename)

        self.title = root.attribute('title', 'Untitled')
        self.overwrite = root.attribute('overwrite', 'true' if Book.DefaultOverwrite else 'false') == 'true'
        self.device = root.attribute('device', Book.DefaultDevice)
        self.imageFlags = int(root.attribute('imageFlags', str(Book.DefaultImageFlags)))
        self.filename = filename
        self.modified = False
        self.images = []

        items = root.elementsByTagName('image')
        if items == None:
            return

        for i in xrange(0, len(items)):
            item = items.at(i).toElement()
            if item.hasAttribute('filename'):
                self.images.append(item.attribute('filename'))

    def addImageDirs(self, directories):
        filenames = []

        for directory in directories:
             for root, subdirs, subfiles in os.walk(unicode(directory)):
                for filename in subfiles:
                    path = os.path.join(root, filename)
                    if self.isImageFile(path):
                        filenames.append(path)
        filenames.sort()
        self.addImageFiles(filenames)
        return filenames


    def addImageFiles(self, filenames):
		#print len(filenames)
		for filename in filenames:
			if filename not in self.images:
				self.images.append(filename)
				self.modified = True
                
                
    def isImageFile(self, filename):
        imageExts = ['jpeg', 'jpg', 'gif', 'png']

        filetype = None
        
        try:
        	filetype = imghdr.what(str(filename))
        except:
        	return False
        	     
        return (
            os.path.isfile(filename) and
            filetype in imageExts
        )
        

########NEW FILE########
__FILENAME__ = convert
#!/usr/bin/env python

# Copyright (C) 2010  Alex Yatskov
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

import os

import image
import imghdr
import string
import unicodedata

	
class BookConvert():
    
    def __init__(self, book, outputMgr, directory, verbose):
        self.book = book
        self.outputMgr = outputMgr
        self.directory = directory
        self.verbose = verbose
                    
    def Export(self):

    	if not os.path.isdir(self.directory):
    		os.makedirs(self.directory )
    	
    	if (not self.verbose):
			outputIdx = self.outputMgr.createOutputObj("Converting "+self.book.title, len(self.book.images))
		
        for index in range(0,len(self.book.images)):
          directory = os.path.join(unicode(self.directory), unicode(self.book.title))
          source = unicode(self.book.images[index])
          newSource = os.path.join(self.book.images[index]+"."+ imghdr.what(str(source)))    
          target = os.path.join(directory, '%05d.png' % index) 
          if (self.verbose):
              print(str(index) +" Target = " + target)
			
          if index == 0:
            try:
                if not os.path.isdir(directory ):
                    os.makedirs(directory )

            except OSError:
                return

            try:
                base = os.path.join(directory, unicode(self.book.title))
                mangaName = base + '.manga'
                if (self.verbose):
               		print(mangaName)
                if self.book.overwrite or not os.path.isfile(mangaName):
                    manga = open(mangaName, 'w')
                    manga.write('\x00')
                    manga.close()
                    
                mangaSaveName = base + '.manga_save'
                if self.book.overwrite or not os.path.isfile(mangaSaveName):
                    mangaSave = open(base + '.manga_save', 'w')
                    saveData = u'LAST=/mnt/us/pictures/%s/%s' % (self.book.title, os.path.split(target)[1])
                    if (self.verbose):
                        print("SaveData = " + saveData)
                    mangaSave.write(saveData.encode('utf-8'))
                    mangaSave.close()

            except IOError:
                return False
          
          os.renames(source, newSource)
 
          try:
          	
            if self.book.overwrite or not os.path.isfile(target):
                image.convertImage(newSource, target, str(self.book.device), self.book.imageFlags)
                if (self.verbose):
                	print(source + " -> " + target)
                else:	
                	self.outputMgr.updateOutputObj( outputIdx )	

					
          except RuntimeError, error:
              print("ERROR")
          finally:
          	os.renames(newSource, source)
 

########NEW FILE########
__FILENAME__ = ConvertFile
#!/usr/bin/env python

import os, zipfile
import imghdr
import shutil

from book import Book
from convert import BookConvert

class convertFile():
	
	def __init__(self):
		pass
		
	@staticmethod	
	def convert(outputMgr, filePath, outDir, Device, verbose):
		kindleDir = 'images' if Device == 'Kindle 5' else 'Pictures'
		listDir = []
		isDir = os.path.isdir(filePath)

		if (isDir):
			title = os.path.basename(filePath)
			listDir = os.listdir(filePath)
		else:
			listDir.append(filePath)
			title = kindleDir
			
		
		outputBook = Book()
		outputBook.device = Device
		
		if (title == None or title == ""):
			title = kindleDir
		
		files = []
		directories = []
		compressedFiles = []
		

		# Recursively loop through the filesystem
		for filename in listDir:
			if (isDir):
				filename = os.path.join(filePath, filename)
			if (verbose):
				print("Pre-Processing %s." % filename)
			if (os.path.isdir(str(filename))):	
				directories.append(filename)
			else:
				if (outputBook.isImageFile(filename)):
					if (verbose):
						print("ConvertPkg: Found Image %s" % filename)
					files.append(filename)
				else:
					imageExts = ['.cbz', '.zip']
					
					if os.path.splitext(filename)[1].lower() in imageExts:
						compressedFiles.append(filename)
		
				
		if (len(files) > 0):
			files.sort()
			outputBook.addImageFiles(files)
			outputBook.title = title
			bookConvert = BookConvert(outputBook, outputMgr, os.path.abspath(outDir), verbose)
			bookConvert.Export()			
		
		outDir = os.path.join(outDir, title)	
			
		for directory in directories:
			if(verbose):
				print("Converting %s", directory)
			convertFile.convert(outputMgr, directory, outDir, Device, verbose)
		
		for compressedFile in compressedFiles:
			try:
				if(verbose):
					print("Uncompressing %s" % compressedFile)
				z = zipfile.ZipFile(compressedFile, 'r')
			except:
				if (verbose):
					print("Failed to convert %s. Check if it is a valid zipFile." % compressedFile)
				continue
				
			if (isDir):
				temp_dir = os.path.join(filePath, os.path.splitext(os.path.basename(compressedFile))[0])
			else:
				temp_dir = os.path.splitext(compressedFile)[0]
			
			try:			
				os.mkdir(temp_dir)
			except:
				continue
				
			for name in z.namelist():
				tempName = os.path.join(temp_dir, name)
				convertFile.extract_from_zip(name, tempName, z)
			z.close
			convertFile.convert(outputMgr, temp_dir, outDir, Device, verbose)
			if os.path.exists(temp_dir):
				shutil.rmtree(temp_dir)
	
	@staticmethod
	def extract_from_zip( name, dest_path, zip_file ):
		dest_file = open(dest_path, 'wb')
		dest_file.write(zip_file.read(name))
		dest_file.close()

########NEW FILE########
__FILENAME__ = image
#!/usr/bin/env python

# Copyright (C) 2010  Alex Yatskov
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


from PIL import Image, ImageDraw


class ImageFlags:
    Orient = 1 << 0
    Resize = 1 << 1
    Frame = 1 << 2
    Quantize = 1 << 3


class KindleData:
    Palette4 = [
        0x00, 0x00, 0x00,
        0x55, 0x55, 0x55,
        0xaa, 0xaa, 0xaa,
        0xff, 0xff, 0xff
    ]

    Palette15a = [
        0x00, 0x00, 0x00,
        0x11, 0x11, 0x11,
        0x22, 0x22, 0x22,
        0x33, 0x33, 0x33,
        0x44, 0x44, 0x44,
        0x55, 0x55, 0x55,
        0x66, 0x66, 0x66,
        0x77, 0x77, 0x77,
        0x88, 0x88, 0x88,
        0x99, 0x99, 0x99,
        0xaa, 0xaa, 0xaa,
        0xbb, 0xbb, 0xbb,
        0xcc, 0xcc, 0xcc,
        0xdd, 0xdd, 0xdd,
        0xff, 0xff, 0xff,
    ]

    Palette15b = [
        0x00, 0x00, 0x00,
        0x11, 0x11, 0x11,
        0x22, 0x22, 0x22,
        0x33, 0x33, 0x33,
        0x44, 0x44, 0x44,
        0x55, 0x55, 0x55,
        0x77, 0x77, 0x77,
        0x88, 0x88, 0x88,
        0x99, 0x99, 0x99,
        0xaa, 0xaa, 0xaa,
        0xbb, 0xbb, 0xbb,
        0xcc, 0xcc, 0xcc,
        0xdd, 0xdd, 0xdd,
        0xee, 0xee, 0xee,
        0xff, 0xff, 0xff,
    ]

    Palette16 = [
        0x00, 0x00, 0x00,
        0x11, 0x11, 0x11,
        0x22, 0x22, 0x22,
        0x33, 0x33, 0x33,
        0x44, 0x44, 0x44,
        0x55, 0x55, 0x55,
        0x66, 0x66, 0x66,
        0x77, 0x77, 0x77,
        0x88, 0x88, 0x88,
        0x99, 0x99, 0x99,
        0xaa, 0xaa, 0xaa,
        0xbb, 0xbb, 0xbb,
        0xcc, 0xcc, 0xcc,
        0xdd, 0xdd, 0xdd,
        0xee, 0xee, 0xee,
        0xff, 0xff, 0xff,
    ]

    Profiles = {
        'Kindle 1': ((600, 800), Palette4),
        'Kindle 2': ((600, 800), Palette15a),
        'Kindle 3': ((600, 800), Palette15a),
        'Kindle 4': ((600, 800), Palette15b),
        'Kindle 5': ((758, 1024), Palette16),
        'Kindle DX': ((824, 1200), Palette15a),
        'Kindle DXG': ((824, 1200), Palette15a)
    }


def quantizeImage(image, palette):
    colors = len(palette) / 3
    if colors < 256:
        palette = palette + palette[:3] * (256 - colors)

    palImg = Image.new('P', (1, 1))
    palImg.putpalette(palette)

    return image.quantize(palette=palImg)


def resizeImage(image, size):
    widthDev, heightDev = size
    widthImg, heightImg = image.size

    if widthImg <= widthDev and heightImg <= heightDev:
        return image

    ratioImg = float(widthImg) / float(heightImg)
    ratioWidth = float(widthImg) / float(widthDev)
    ratioHeight = float(heightImg) / float(heightDev)

    if ratioWidth > ratioHeight:
        widthImg = widthDev
        heightImg = int(widthDev / ratioImg)
    elif ratioWidth < ratioHeight:
        heightImg = heightDev
        widthImg = int(heightDev * ratioImg)
    else:
        widthImg, heightImg = size

    return image.resize((widthImg, heightImg), Image.ANTIALIAS)


def formatImage(image):
    if image.mode == 'RGB':
        return image
    return image.convert('RGB')


def orientImage(image, size):
    widthDev, heightDev = size
    widthImg, heightImg = image.size

    if (widthImg > heightImg) != (widthDev > heightDev):
        return image.rotate(90, Image.BICUBIC, True)

    return image


def frameImage(image, foreground, background, size):
    widthDev, heightDev = size
    widthImg, heightImg = image.size

    pastePt = (
        max(0, (widthDev - widthImg) / 2),
        max(0, (heightDev - heightImg) / 2)
    )

    corner1 = (
        pastePt[0] - 1,
        pastePt[1] - 1
    )

    corner2 = (
        pastePt[0] + widthImg + 1,
        pastePt[1] + heightImg + 1
    )

    imageBg = Image.new(image.mode, size, background)
    imageBg.paste(image, pastePt)

    draw = ImageDraw.Draw(imageBg)
    draw.rectangle([corner1, corner2], outline=foreground)

    return imageBg


def convertImage(source, target, device, flags):
    try:
        size, palette = KindleData.Profiles[device]
    except KeyError:
        raise RuntimeError('Unexpected output device %s' % device)

    try:
        image = Image.open(source)
    except IOError:
        raise RuntimeError('Cannot read image file %s' % source)

    image = formatImage(image)
    if flags & ImageFlags.Orient:
        image = orientImage(image, size)
    if flags & ImageFlags.Resize:
        image = resizeImage(image, size)
    if flags & ImageFlags.Frame:
        image = frameImage(image, tuple(palette[:3]), tuple(palette[-3:]), size)
    if flags & ImageFlags.Quantize:
        image = quantizeImage(image, palette)

    try:
        image.save(target)
    except IOError:
        raise RuntimeError('Cannot write image file %s' % target)

########NEW FILE########
__FILENAME__ = manga
#!/usr/bin/env python

# Copyright (C) 2010  
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

##########

import optparse
import os
import sys
try:
	import socks
	NO_SOCKS = False
except ImportError:
	NO_SOCKS = True
import socket
try:
	from bs4 import BeautifulSoup
	HAVE_SOUP = True
except ImportError:
	HAVE_SOUP = False

##########

from parsers.thread import SiteParserThread
from util import fixFormatting, isImageLibAvailable
from xmlparser import MangaXmlParser
from outputManager.progressBarManager import progressBarManager
##########

VERSION = 'v0.8.8'

siteDict = {
		''  : '[mf]',
		'1' : '[mf]',
		'2' : '[mr]',
		'3' : '[mp]',
		'4' : '[mh]',
					}
if HAVE_SOUP:
	siteDict['5'] = '[bt]'

##########

class InvalidSite(Exception):
	pass

def printLicenseInfo():
		print( "\nProgram: Copyright (c) 2010. GPL v3 (http://www.gnu.org/licenses/gpl.html)." )
		print( "Icon:      Copyright (c) 2006. GNU Free Document License v1.2 (Author:Kasuga)." )
		print( "           http://ja.wikipedia.org/wiki/%E5%88%A9%E7%94%A8%E8%80%85:Kasuga\n" )
		
##########
		
def main():
	printLicenseInfo()
	
	# for easier parsing, adds free --help and --version
	# optparse (v2.3-v2.7) was chosen over argparse (v2.7+) for compatibility (and relative similarity) reasons 
	# and over getopt(v?) for additional functionality
	parser = optparse.OptionParser(	usage='usage: %prog [options] <manga name>', 
					version=('Manga Downloader %s' % VERSION)									)
					
	parser.set_defaults(	
				all_chapters_FLAG = False,
				auto = False,
				conversion_FLAG = False,
				convert_Directory = False,
				device = 'Kindle 3',
				downloadFormat = '.cbz', 
				downloadPath = 'DEFAULT_VALUE', 
				inputDir = None,
				outputDir = 'DEFAULT_VALUE',
				overwrite_FLAG = False,
				verbose_FLAG = False,
				timeLogging_FLAG = False,
				maxChapterThreads = 3,
				useShortName = False,
				spaceToken = '.',
				proxy = None	
				)
				
	parser.add_option(	'--all', 
				action = 'store_true', 
				dest = 'all_chapters_FLAG', 
				help = 'Download all available chapters.'										)
				
	parser.add_option(	'-d', '--directory', 
				dest = 'downloadPath', 
				help = 'The destination download directory.  Defaults to the directory of the script.'					)
				
	parser.add_option(	'--overwrite', 
				action = 'store_true', 
				dest = 'overwrite_FLAG', 
				help = 'Overwrites previous copies of downloaded chapters.'								)

	parser.add_option(	'--verbose', 
				action = 'store_true', 
				dest = 'verbose_FLAG', 
				help = 'Verbose Output.'								)
				
	parser.add_option(	'-x','--xml', 
				dest = 'xmlfile_path', 
				help = 'Parses the .xml file and downloads all chapters newer than the last chapter downloaded for the listed mangas.'	)
	
	parser.add_option(	'-c', '--convertFiles', 
				action = 'store_true', 
				dest = 'conversion_FLAG', 
				help = 'Converts downloaded files to a Format/Size acceptable to the device specified by the --device parameter.'				)

	parser.add_option( 	'--device', 
				dest = 'device', 
				help = 'Specifies the conversion device. Omitting this option default to %default.'				)
	
	parser.add_option( 	'--convertDirectory', 
				action = 'store_true', 
				dest = 'convert_Directory', 
				help = 'Converts the image files stored in the directory specified by --inputDirectory. Stores the converted images in the directory specified by --outputDirectory'	)
	
	parser.add_option( 	'--inputDirectory', 
				dest = 'inputDir', 
				help = 'The directory containing the images to convert when --convertDirectory is specified.'					)
	
	parser.add_option( 	'--outputDirectory', 
				dest = 'outputDir', 
				help = 'The directory to store the images when --convertDirectory is specified.'					)				
											
	parser.add_option(	'-z', '--zip', 
				action = 'store_const', 
				dest = 'downloadFormat', 
				const = '.zip', 
				help = 'Downloads using .zip compression.  Omitting this option defaults to %default.'					)
	
	parser.add_option(	'-t', '--threads', 
				dest = 'maxChapterThreads', 
				help = 'Limits the number of chapter threads to the value specified.'					)
	
	parser.add_option(	'--timeLogging', 
				action = 'store_true', 
				dest = 'timeLogging_FLAG', 
				help = 'Output time logging.'					)	

	parser.add_option(	'--useShortName', 
				action = 'store_true', 
				dest = 'useShortName_FLAG', 
				help = 'To support devices that limit the size of the filename, this parameter uses a short name'				)				

	parser.add_option( 	'--spaceToken', 
				dest = 'spaceToken', 
				help = 'Specifies the character used to replace spaces in the manga name.'				)				
	
	parser.add_option( 	'--proxy', 
				dest = 'proxy', 
				help = 'Specifies the proxy.'				)				
					
	(options, args) = parser.parse_args()
	
	try:
		options.maxChapterThreads = int(options.maxChapterThreads)
	except:
		options.maxChapterThreads = 2
	
	if (options.maxChapterThreads <= 0):
		options.maxChapterThreads = 2;
		
	if(len(args) == 0 and ( not (options.convert_Directory or options.xmlfile_path != None) )):
		parser.error('Manga not specified.')
	
	#if(len(args) > 1):
	#	parser.error('Possible multiple mangas specified, please select one.  (Did you forget to put quotes around a multi-word manga?)')
	
	SetDownloadPathToName_Flag = False
	SetOutputPathToDefault_Flag = False
	if(len(args) > 0):
		
		# Default Directory is the ./MangaName
		if (options.downloadPath == 'DEFAULT_VALUE'):
			SetDownloadPathToName_Flag = True

			
		# Default outputDir is the ./MangaName
		if (options.outputDir == 'DEFAULT_VALUE'):
			SetOutputPathToDefault_Flag = True


	PILAvailable = isImageLibAvailable()
	# Check if PIL Library is available if either of convert Flags are set 
	if ((not PILAvailable)  and (options.convert_Directory or options.conversion_FLAG)):
		print ("\nConversion Functionality Not available.\nMust install the PIL (Python Image Library)")
		sys.exit()
	else:
		if (PILAvailable):
			from ConvertPackage.ConvertFile import convertFile
	
	if (options.convert_Directory):	
		options.inputDir = os.path.abspath(options.inputDir)
	
	# Changes the working directory to the script location
	if (os.path.dirname(sys.argv[0]) != ""):
		os.chdir(os.path.dirname(sys.argv[0]))

	options.outputMgr = progressBarManager()
	options.outputMgr.start()
	try:
		if (options.convert_Directory):
			if ( options.outputDir == 'DEFAULT_VALUE' ):
				options.outputDir = '.'
			print("Converting Files: %s" % options.inputDir)	
			convertFile.convert(options.outputMgr, options.inputDir, options.outputDir, options.device, options.verbose_FLAG)
	
		elif options.xmlfile_path != None:
			xmlParser = MangaXmlParser(options)
			xmlParser.downloadManga()
		else:
			threadPool = []
			for manga in args:
				print( manga )
				options.manga = manga
			
				if SetDownloadPathToName_Flag:		
					options.downloadPath = ('./' + fixFormatting(options.manga, options.spaceToken))
            
				if SetOutputPathToDefault_Flag:	
					options.outputDir = options.downloadPath 
			
				options.downloadPath = os.path.realpath(options.downloadPath) + os.sep
			
				# site selection
				if HAVE_SOUP:
					print('\nWhich site?\n(1) MangaFox\n(2) MangaReader\n(3) MangaPanda\n(4) MangaHere\n(5) Batoto\n')
				else:
					print('\nWhich site?\n(1) MangaFox\n(2) MangaReader\n(3) MangaPanda\n(4) MangaHere\n')
	
				# Python3 fix - removal of raw_input()
				try:
					site = raw_input()
				except NameError:
					site = input()

				try:
					options.site = siteDict[site]
				except KeyError:
					raise InvalidSite('Site selection invalid.')	
			
				threadPool.append(SiteParserThread(options, None, None))
            
			for thread in threadPool: 
				thread.start()
				thread.join()
	finally:
		# Must always stop the manager
		options.outputMgr.stop()
		
		
if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = manga2
import argparse

from redux.metasite import MetaSite
from redux.site.mangafox import MangaFox
from redux.site.mangahere import MangaHere
from redux.site.mangapanda import MangaPanda
from redux.site.mangareader import MangaReader


def main():
    parser = argparse.ArgumentParser(description='Download manga.')
    subparsers = parser.add_subparsers()
    add_list_subparser(subparsers)
    add_download_subparser(subparsers)

    args = parser.parse_args()
    args.func(args)


def add_list_subparser(subparsers):
    parser = subparsers.add_parser('list', help='list all chapters')
    parser.add_argument('series', help='series name')
    parser.set_defaults(func=itemize)


def add_download_subparser(subparsers):
    parser = subparsers.add_parser('download', help='download some chapters')
    parser.add_argument('series', help='series name')
    parser.add_argument('chapters', help='a quoted string of comma delimited numbers or ranges')
    parser.set_defaults(func=download)


def itemize(args):
    chapters = MetaSite([MangaFox, MangaHere, MangaPanda, MangaReader])\
        .series(args.series).chapters

    for chapter_number, meta_chapter in chapters.items():
        print("(%s) %s" % (chapter_number, meta_chapter.title))


def download(args):
    return


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

# The outputManager synchronizes the output display for all the various threads

#####################
import threading

class outputStruct():
	def __init__( self ):
		self.id = 0
		self.updateObjSem = None
		self.title = ""
		self.numOfInc = 0	

class outputManager( threading.Thread ):
	def __init__( self ):
		threading.Thread.__init__(self)
		self.outputObjs = dict()
		self.outputListLock = threading.Lock()
		
		# Used to assign the next id for an output object
		self.nextId = 0  
		
		self.isAlive = True
		
	def createOutputObj( self, name, numberOfIncrements ):
		raise NotImplementedError('Should have implemented this')	
	
	def updateOutputObj( self, objectId ):
		raise NotImplementedError('Should have implemented this')	
	
	def run (self):
		raise NotImplementedError('Should have implemented this')
	
	def stop(self):
		self.isAlive = False
	
########NEW FILE########
__FILENAME__ = progressbar
#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
#
# progressbar  - Text progressbar library for python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Text progressbar library for python.

This library provides a text mode progressbar. This is typically used
to display the progress of a long running operation, providing a
visual clue that processing is underway.

The ProgressBar class manages the progress, and the format of the line
is given by a number of widgets. A widget is an object that may
display diferently depending on the state of the progress. There are
three types of widget:
- a string, which always shows itself;
- a ProgressBarWidget, which may return a diferent value every time
it's update method is called; and
- a ProgressBarWidgetHFill, which is like ProgressBarWidget, except it
expands to fill the remaining width of the line.

The progressbar module is very easy to use, yet very powerful. And
automatically supports features like auto-resizing when available.
"""

from __future__ import division

__author__ = "Nilton Volpato"
__author_email__ = "first-name dot last-name @ gmail.com"
__date__ = "2006-05-07"
__version__ = "2.3-dev"

import sys, time, os
from array import array
try:
    from fcntl import ioctl
    import termios
except ImportError:
    pass
import signal
try:
    basestring
except NameError:
    basestring = (str,)

class ProgressBarWidget(object):
    """This is an element of ProgressBar formatting.

    The ProgressBar object will call it's update value when an update
    is needed. It's size may change between call, but the results will
    not be good if the size changes drastically and repeatedly.
    """
    def update(self, pbar):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made.

        At least this function must be overriden."""
        pass

class ProgressBarWidgetHFill(object):
    """This is a variable width element of ProgressBar formatting.

    The ProgressBar object will call it's update value, informing the
    width this object must the made. This is like TeX \\hfill, it will
    expand to fill the line. You can use more than one in the same
    line, and they will all have the same width, and together will
    fill the line.
    """
    def update(self, pbar, width):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made. The parameter width is the total
        horizontal width the widget must have.

        At least this function must be overriden."""
        pass


class ETA(ProgressBarWidget):
    "Widget for the Estimated Time of Arrival"
    def format_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
    def update(self, pbar):
        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)

class FileTransferSpeed(ProgressBarWidget):
    "Widget for showing the transfer speed (useful for file transfers)."
    def __init__(self, unit='B'):
        self.unit = unit
        self.fmt = '%6.2f %s'
        self.prefixes = ['', 'K', 'M', 'G', 'T', 'P']
    def update(self, pbar):
        if pbar.seconds_elapsed < 2e-6:#== 0:
            bps = 0.0
        else:
            bps = pbar.currval / pbar.seconds_elapsed
        spd = bps
        for u in self.prefixes:
            if spd < 1000:
                break
            spd /= 1000
        return self.fmt % (spd, u + self.unit + '/s')

class RotatingMarker(ProgressBarWidget):
    "A rotating marker for filling the bar of progress."
    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1
    def update(self, pbar):
        if pbar.finished:
            return self.markers[0]
        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]

class Percentage(ProgressBarWidget):
    "Just the percentage done."
    def update(self, pbar):
        return '%3d%%' % pbar.percentage()

class SimpleProgress(ProgressBarWidget):
    "Returns what is already done and the total, e.g.: '5 of 47'"
    def __init__(self, sep=' of '):
        self.sep = sep
    def update(self, pbar):
        return '%d%s%d' % (pbar.currval, self.sep, pbar.maxval)

class Bar(ProgressBarWidgetHFill):
    "The bar of progress. It will stretch to fill the line."
    def __init__(self, marker='#', left='|', right='|'):
        self.marker = marker
        self.left = left
        self.right = right
    def _format_marker(self, pbar):
        if isinstance(self.marker, basestring):
            return self.marker
        else:
            return self.marker.update(pbar)
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth // 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m * marked_width).ljust(cwidth) + self.right)
        return bar

class ReverseBar(Bar):
    "The reverse bar of progress, or bar of regress. :)"
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth // 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m*marked_width).rjust(cwidth) + self.right)
        return bar

default_widgets = [Percentage(), ' ', Bar()]
class ProgressBar(object):
    """This is the ProgressBar class, it updates and prints the bar.

    A common way of using it is like:
    >>> pbar = ProgressBar().start()
    >>> for i in xrange(100):
    ...    # do something
    ...    pbar.update(i+1)
    ...
    >>> pbar.finish()

    You can also use a progressbar as an iterator:
    >>> progress = ProgressBar()
    >>> for i in progress(some_iterable):
    ...    # do something
    ...

    But anything you want to do is possible (well, almost anything).
    You can supply different widgets of any type in any order. And you
    can even write your own widgets! There are many widgets already
    shipped and you should experiment with them.

    The term_width parameter must be an integer or None. In the latter case
    it will try to guess it, if it fails it will default to 80 columns.

    When implementing a widget update method you may access any
    attribute or function of the ProgressBar object calling the
    widget's update method. The most important attributes you would
    like to access are:
    - currval: current value of the progress, 0 <= currval <= maxval
    - maxval: maximum (and final) value of the progress
    - finished: True if the bar has finished (reached 100%), False o/w
    - start_time: the time when start() method of ProgressBar was called
    - seconds_elapsed: seconds elapsed since start_time
    - percentage(): percentage of the progress [0..100]. This is a method.

    The attributes above are unlikely to change between different versions,
    the other ones may change or cease to exist without notice, so try to rely
    only on the ones documented above if you are extending the progress bar.
    """

    __slots__ = ('currval', 'fd', 'finished', 'last_update_time', 'maxval',
                 'next_update', 'num_intervals', 'seconds_elapsed',
                 'signal_set', 'start_time', 'term_width', 'update_interval',
                 'widgets', '_iterable')

    _DEFAULT_MAXVAL = 100

    def __init__(self, maxval=None, widgets=default_widgets, term_width=None,
                 fd=sys.stderr):
        self.maxval = maxval
        self.widgets = widgets
        self.fd = fd
        self.signal_set = False
        if term_width is not None:
            self.term_width = term_width
        else:
            try:
                self._handle_resize(None, None)
                signal.signal(signal.SIGWINCH, self._handle_resize)
                self.signal_set = True
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                self.term_width = int(os.environ.get('COLUMNS', 80)) - 1

        self.currval = 0
        self.finished = False
        self.start_time = None
        self.last_update_time = None
        self.seconds_elapsed = 0
        self._iterable = None

    def __call__(self, iterable):
        try:
            self.maxval = len(iterable)
        except TypeError:
            # If the iterable has no length, then rely on the value provided
            # by the user, otherwise fail.
            if not (isinstance(self.maxval, (int, long)) and self.maxval > 0):
                raise RuntimeError('Could not determine maxval from iterable. '
                                   'You must explicitly provide a maxval.')
        self._iterable = iter(iterable)
        self.start()
        return self

    def __iter__(self):
        return self

    def next(self):
        try:
            next = self._iterable.next()
            self.update(self.currval + 1)
            return next
        except StopIteration:
            self.finish()
            raise

    def _handle_resize(self, signum, frame):
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = w

    def percentage(self):
        "Returns the percentage of the progress."
        return self.currval * 100.0 / self.maxval

    def _format_widgets(self):
        r = []
        hfill_inds = []
        num_hfill = 0
        currwidth = 0
        for i, w in enumerate(self.widgets):
            if isinstance(w, ProgressBarWidgetHFill):
                r.append(w)
                hfill_inds.append(i)
                num_hfill += 1
            elif isinstance(w, basestring):
                r.append(w)
                currwidth += len(w)
            else:
                weval = w.update(self)
                currwidth += len(weval)
                r.append(weval)
        for iw in hfill_inds:
            widget_width = int((self.term_width - currwidth) // num_hfill)
            r[iw] = r[iw].update(self, widget_width)
        return r

    def _format_line(self):
        return ''.join(self._format_widgets()).ljust(self.term_width)

    def _next_update(self):
        return int((int(self.num_intervals *
                        (self.currval / self.maxval)) + 1) *
                   self.update_interval)

    def _need_update(self):
        """Returns true when the progressbar should print an updated line.

        You can override this method if you want finer grained control over
        updates.

        The current implementation is optimized to be as fast as possible and
        as economical as possible in the number of updates. However, depending
        on your usage you may want to do more updates. For instance, if your
        progressbar stays in the same percentage for a long time, and you want
        to update other widgets, like ETA, then you could return True after
        some time has passed with no updates.

        Ideally you could call self._format_line() and see if it's different
        from the previous _format_line() call, but calling _format_line() takes
        around 20 times more time than calling this implementation of
        _need_update().
        """
        return self.currval >= self.next_update

    def update(self, value):
        "Updates the progress bar to a new value."
        assert 0 <= value <= self.maxval, '0 <= %d <= %d' % (value, self.maxval)
        self.currval = value
        if not self._need_update():
            return
        if self.start_time is None:
            raise RuntimeError('You must call start() before calling update()')
        now = time.time()
        self.seconds_elapsed = now - self.start_time
        self.next_update = self._next_update()
        self.fd.write(self._format_line() + '\r')
        self.last_update_time = now

    def start(self):
        """Starts measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:
        >>> pbar = ProgressBar().start()
        >>> for i in xrange(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        """
        if self.maxval is None:
            self.maxval = self._DEFAULT_MAXVAL
        assert self.maxval > 0

        self.num_intervals = max(100, self.term_width)
        self.update_interval = self.maxval / self.num_intervals
        self.next_update = 0

        self.start_time = self.last_update_time = time.time()
        self.update(0)
        return self

    def finish(self):
        """Used to tell the progress is finished."""
        self.finished = True
        self.update(self.maxval)
        self.fd.write('\n')
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)

########NEW FILE########
__FILENAME__ = progressBarManager
#!/usr/bin/env python

# The progressBarManager synchronizes the progress bars for the program

#####################

from outputManager.base import *
from outputManager.progressbar import *
import time

class progressBarManager(outputManager):
	def __init__( self ):
		outputManager.__init__(self)
		
	def createOutputObj( self, title, numberOfPages ):
		outputObj = outputStruct()
		outputObj.updateObjSem = threading.Semaphore(0)
		outputObj.title = title

		outputObj.numOfInc = numberOfPages
		
		# Aquiring the List Lock to protect the dictionary structured
		self.outputListLock.acquire(True)
		
		id = self.nextId 
		self.nextId = self.nextId + 1
		outputObj.id = id
		self.outputObjs[id] = outputObj
		
		#  Releasing lock
		self.outputListLock.release()
		
		return id
		
	def updateOutputObj( self, objectId ):
		self.releaseSemaphore(objectId)	
	
	def getNextIdx(self):
		index = None
		
		self.outputListLock.acquire(True)
		if (len(self.outputObjs) > 0):
			keys = self.outputObjs.iterkeys()
			for key in keys:
				index = key
				break 
		self.outputListLock.release()
		
		return index
		
	def removeOuputObj(self, index):
		self.outputListLock.acquire(True)
		del self.outputObjs[index]
		self.outputListLock.release()
	
	def acquireSemaphore(self, index):
		# Get a pointer to the semaphore
		# Lock the list to protect the interior map structure while 
		# retrieving the pointer to the semaphore
		self.outputListLock.acquire(True)
		sem = self.outputObjs[index].updateObjSem
		self.outputListLock.release()
		
		sem.acquire()
		
		return
	
	def releaseSemaphore(self, index):
		# Get a pointer to the semaphore
		# Lock the list to protect the interior map structure while 
		# retrieving the pointer to the semaphore
		self.outputListLock.acquire(True)
		sem = self.outputObjs[index].updateObjSem
		self.outputListLock.release()
		
		sem.release()
	
	def run (self):
		while(self.isAlive):
			# Sleep to give priority to another thread
			time.sleep(0)
			index = self.getNextIdx()
			if (index != None):
				widgets = ['%s: ' % self.outputObjs[index].title, Percentage(), ' ', Bar(), ' ', ETA(), ]
				progressBar = ProgressBar(widgets=widgets, maxval=self.outputObjs[index].numOfInc).start()
				
				for i in range(self.outputObjs[index].numOfInc):
					self.acquireSemaphore(index)
					progressBar.update( i + 1 )
				print ("\n")
				self.removeOuputObj(index)
					
			
			
			

########NEW FILE########
__FILENAME__ = animea
#!/usr/bin/env python

####################################################################
# For more detailed comments look at MangaFoxParser
#
# The code for this sites is similar enough to not need
# explanation, but dissimilar enough to not warrant any further OOP
####################################################################

####################

import os
import re

#####################

from parsers.base import SiteParserBase
from util import getSourceCode

#####################

class Animea(SiteParserBase):

	##########
	#Animea check
	#	url = 'http://www.google.com/search?q=site:manga.animea.net+' + '+'.join(manga.split())
	#	source_code = urllib.urlopen(url).read()
	#	try:
	#		siteHome = re.compile('a href="(http://manga.animea.net/.*?.html)"').search(source_code).group(1)
	#	except AttributeError:
	#		total_chapters.append(0)
	#		keywords.append('')
	#	else:
	#		manga = re.compile('a href="http://manga.animea.net/(.*?).html"').search(source_code).group(1)
	#		url = siteHome
	#		source_code = urllib.urlopen(url).read()			
	#		total_chapters.append(int(re.compile('http://manga.animea.net/' + manga + '-chapter-(.*?).html').search(source_code).group(1)))
	#		keywords.append(manga)
	
	#	print('Finished Animea check.')
	#return (site, total_chapters)
	
	#	winningIndex = 1
	#	winningIndex = 0
	#	return (websites[0], keywords[winningIndex], misc[0])
	#	return (websites[winningIndex], keywords[winningIndex], chapters, chapter_list_array_decrypted)		
	##########

	def downloadAnimea(self, manga, chapter_start, chapter_end, download_path, download_format):
		for current_chapter in range(chapter_start, chapter_end + 1):	
			manga_chapter_prefix = manga.lower().replace('-', '_') + '_' + str(current_chapter).zfill(3)
			if (os.path.exists(download_path + manga_chapter_prefix + '.cbz') or os.path.exists(download_path + manga_chapter_prefix + '.zip')) and overwrite_FLAG == False:
				print('Chapter ' + str(current_chapter) + ' already downloaded, skipping to next chapter...')
				continue;
			url = 'http://manga.animea.net/'+ manga + '-chapter-' + str(current_chapter) + '-page-1.html'
			source = getSourceCode(url)
			max_pages = int(re.compile('of (.*?)</title>').search(source).group(1))
		
			for page in range(1, max_pages + 1):
				url = 'http://manga.animea.net/'+ manga + '-chapter-' + str(current_chapter) + '-page-' + str(page) + '.html'
				source = getSourceCode(url)
				img_url = re.compile('img src="(http.*?.[jp][pn]g)"').search(source).group(1)
				print('Chapter ' + str(current_chapter) + ' / ' + 'Page ' + str(page))
				print(img_url)
				downloadImage(img_url, os.path.join('mangadl_tmp', manga_chapter_prefix + '_' + str(page).zfill(3)))

			compress(manga_chapter_prefix, download_path, max_pages, download_format)

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

#####################

import imghdr
import os
import re
import shutil
import tempfile
import threading
import time
import zipfile

#####################

try:
	import urllib
except ImportError:
	import urllib.parse as urllib

#####################

from util import * 

#####################

class SiteParserBase:

#####	
	# typical misspelling of title and/or manga removal
	class MangaNotFound(Exception):
		
		def __init__(self, errorMsg=''):
			self.errorMsg = 'Manga not found. %s' % errorMsg
		
		def __str__(self):
			return self.errorMsg
	
	# XML file config reports nothing to do
	class NoUpdates(Exception):

		def __init__(self, errorMsg=''):
			self.errorMsg = 'No updates. %s' % errorMsg

		def __str__(self):
			return self.errorMsg
		
#####

	def __init__(self,optDict):
		for elem in vars(optDict):
			setattr(self, elem, getattr(optDict, elem))
		self.chapters = []
		self.chapters_to_download = []
		self.tempFolder = tempfile.mkdtemp()
		self.garbageImages = {}
		
		# should be defined by subclasses
		self.re_getImage = None
		self.re_getMaxPages = None
		self.isPrependMangaName = False

	# this takes care of removing the temp directory after the last successful download
	def __del__(self):
		try:
			shutil.rmtree(self.tempFolder)
		except:
			pass
		if len(self.garbageImages) > 0:
			print('\nSome images were not downloaded due to unavailability on the site or temporary ip banning:\n')
			for elem in self.garbageImages.keys():
				print('Manga keyword: %s' % elem)
				print('Pages: %s' % self.garbageImages[elem])
#####	
		
	def downloadChapter(self):
		raise NotImplementedError('Should have implemented this')		
		
	def parseSite(self):
		raise NotImplementedError('Should have implemented this')
#####
	
	def compress(self, mangaChapterPrefix, max_pages):
		"""
		Looks inside the temporary directory and zips up all the image files.
		"""
		if self.verbose_FLAG:
			print('Compressing...')
		
		compressedFile = os.path.join(self.tempFolder, mangaChapterPrefix) + self.downloadFormat
			
		z = zipfile.ZipFile( compressedFile, 'w')
		
		for page in range(1, max_pages + 1):	
			tempPath = os.path.join(self.tempFolder, mangaChapterPrefix + '_' + str(page).zfill(3))
			# we got an image file
			if os.path.exists(tempPath) is True and imghdr.what(tempPath) != None:
				z.write( tempPath, mangaChapterPrefix + '_' + str(page).zfill(3) + '.' + imghdr.what(tempPath))
			# site has thrown a 404 because image unavailable or using anti-leeching
			else:
				if mangaChapterPrefix not in self.garbageImages:
					self.garbageImages[mangaChapterPrefix] = [page]
				else:
					self.garbageImages[mangaChapterPrefix].append(page)
				
		z.close()
		
		if self.overwrite_FLAG == True:
			priorPath = os.path.join(self.downloadPath, mangaChapterPrefix) + self.downloadFormat
			if os.path.exists(priorPath):
				os.remove(priorPath)
		
		shutil.move(compressedFile, self.downloadPath)
		
		# The object conversionQueue (singleton) stores the path to every compressed file that  
		# has been downloaded. This object is used by the conversion code to convert the downloaded images
		# to the format specified by the Device errorMsg
		
		compressedFile = os.path.basename(compressedFile)
		compressedFile = os.path.join(self.downloadPath, compressedFile)
		return compressedFile
	
	def downloadImage(self, downloadThread, page, pageUrl, manga_chapter_prefix):
		"""
		Given a page URL to download from, it searches using self.imageRegex
		to parse out the image URL, and downloads and names it using 
		manga_chapter_prefix and page.
		"""

		# while loop to protect against server denies for requests
		# note that disconnects are already handled by getSourceCode, we use a 
		# regex to parse out the image URL and filter out garbage denies
		maxRetries = 5
		waitRetryTime = 5
		while True:
			try:
				if (self.verbose_FLAG):
					print(pageUrl)
				source_code = getSourceCode(pageUrl, self.proxy)
				img_url = self.__class__.re_getImage.search(source_code).group(1)
				if (self.verbose_FLAG):
					print("Image URL: %s" % img_url)
			except AttributeError:
				if (maxRetries == 0):
					if (not self.verbose_FLAG):
						self.outputMgr.updateOutputObj( downloadThread.outputIdx )
					return	
				else:
					# random dist. for further protection against anti-leech
					# idea from wget
					time.sleep(random.uniform(0.5*waitRetryTime, 1.5*waitRetryTime))
					maxRetries -= 1
			else:
				break

		# Remove the 'http://' before encoding, otherwise the '://' would be 
		# encoded as well				
#		img_url = 'http://' + urllib.quote(img_url.split('//')[1])
		
		if self.verbose_FLAG:
			print(img_url)
		
		# Loop to protect against server denies for requests and/or minor disconnects
		while True:
			try:
				temp_path = os.path.join(self.tempFolder, manga_chapter_prefix + '_' + str(page).zfill(3))
				urllib.urlretrieve(img_url, temp_path)
			except IOError:
				pass
			else:
				break
		if (not self.verbose_FLAG):
			self.outputMgr.updateOutputObj( downloadThread.outputIdx )
	
	def processChapter(self, downloadThread, current_chapter):
		"""
		Calculates prefix for filenames, creates download directory if
		nonexistent, checks to see if chapter previously downloaded, returns
		data critical to downloadChapter()
		"""
		
		# Do not need to ZeroFill the manga name because this should be consistent 
		# MangaFox already prepends the manga name
		if self.useShortName_FLAG:
			if (not self.isPrependMangaName):
				manga_chapter_prefix = fixFormatting(self.manga, self.spaceToken)+ self.spaceToken + zeroFillStr(fixFormatting(self.chapters[current_chapter][2], self.spaceToken), 3)
			else:	
				manga_chapter_prefix = zeroFillStr(fixFormatting(self.chapters[current_chapter][2], self.spaceToken), 3)
		else:
			manga_chapter_prefix = fixFormatting(self.manga, self.spaceToken) + '.' +  self.site + '.' + zeroFillStr(fixFormatting(self.chapters[current_chapter][1].decode('utf-8'), self.spaceToken), 3)

		
		# we already have it
		if os.path.exists(os.path.join(self.downloadPath, manga_chapter_prefix) + self.downloadFormat) and self.overwrite_FLAG == False:
			print(self.chapters[current_chapter][1].decode('utf-8') + ' already downloaded, skipping to next chapter...')
			return

		SiteParserBase.DownloadChapterThread.acquireSemaphore()
		if (self.timeLogging_FLAG):
			print(manga_chapter_prefix + " (Start Time): " + str(time.time()))
		# get the URL of the chapter homepage
		url = self.chapters[current_chapter][0]
		
		# mangafox .js sometimes leaves up invalid chapters
		if (url == None):
			return
		
		if (self.verbose_FLAG):
			print("PrepareDownload: " + url)
		
		source = getSourceCode(url, self.proxy)

		max_pages = int(self.__class__.re_getMaxPages.search(source).group(1))
		
		if (self.verbose_FLAG):
				print ("Pages: "+ str(max_pages))
		if (not self.verbose_FLAG):
			downloadThread.outputIdx = self.outputMgr.createOutputObj(manga_chapter_prefix, max_pages)

		self.downloadChapter(downloadThread, max_pages, url, manga_chapter_prefix, current_chapter)
		
		# Post processing 
		# Release locks/semaphores
		# Zip Them up
		self.postDownloadProcessing(manga_chapter_prefix, max_pages)	
	
	def selectChapters(self, chapters):
		"""
		Prompts user to select list of chapters to be downloaded from total list.
		"""
		
		# this is the array form of the chapters we want
		chapterArray = []
		
		if(self.all_chapters_FLAG == False):
			inputChapterString = raw_input('\nDownload which chapters?\n')
			
		if(self.all_chapters_FLAG == True or inputChapterString.lower() == 'all'):
			print('\nDownloading all chapters...')
			for i in range(0, len(chapters)):
				chapterArray.append(i)
		else:
			# parsing user input
			
			# ignore whitespace, split using comma delimiters
			chapter_list_array = inputChapterString.replace(' ', '').split(',')
			
			for i in chapter_list_array:
				iteration = re.search('([0-9]*)-([0-9]*)', i)
				
				# it's a range
				if(iteration is not None):
					for j in range((int)(iteration.group(1)), (int)(iteration.group(2)) + 1):
						chapterArray.append(j - 1)
				# it's a single chapter
				else:
					chapterArray.append((int)(i) - 1)
		return chapterArray
	
	def selectFromResults(self, results):
		"""
		Basic error checking for manga titles, queries will return a list of all mangas that 
		include the query, case-insensitively.
		"""
		
		found = False
		
		# Translate the manga name to lower case
		# Need to handle if it contains NonASCII characters
		actualName = (self.manga.decode('utf-8')).lower()
		
		# each element in results is a 2-tuple
		# elem[0] contains a keyword or string that needs to be passed back (generally the URL to the manga homepage)
		# elem[1] contains the manga name we'll be using
		# When asking y/n, we pessimistically only accept 'y'
		
		for elem in results:
			proposedName = (elem[1].decode('utf-8')).lower()
			
			if actualName in proposedName:
				# manual mode
				if (not self.auto):
					print(elem[1])
				
				# exact match
				if proposedName == actualName:
					self.manga = elem[1]
					keyword = elem[0]
					found = True
					break
				else:
					# only request input in manual mode
					if (not self.auto):
						print('Did you mean: %s? (y/n)' % elem[1])
						answer = raw_input();
	
						if (answer == 'y'):
							self.manga = elem[1]
							keyword = elem[0]
							found = True
							break
		if (not found):
			raise self.MangaNotFound('No strict match found. Check query.')
		return keyword
	
	chapterThreadSemaphore = None
	
	class DownloadChapterThread( threading.Thread ):
		def __init__ ( self, siteParser, chapter):
			threading.Thread.__init__(self)
			self.siteParser = siteParser
			self.chapter = chapter
			self.isThreadFailed = False
			self.outputIdx = -1
			
		@staticmethod
		def initSemaphore(value):
			global chapterThreadSemaphore
			chapterThreadSemaphore = threading.Semaphore(value)
			
		@staticmethod
		def acquireSemaphore():
			global chapterThreadSemaphore
			
			if (chapterThreadSemaphore == None):
				raise FatalError('Semaphore not initialized')
				
			chapterThreadSemaphore.acquire()
			
		@staticmethod
		def releaseSemaphore():	
			global chapterThreadSemaphore
			
			if (chapterThreadSemaphore == None):
				raise FatalError('Semaphore not initialized')
				
			chapterThreadSemaphore.release()
			
		def run (self):
			try:
				self.siteParser.processChapter(self, self.chapter)	
			except Exception as exception:
				# Assume semaphore has not been release
				# This assumption could be faulty if the error was thrown in the compression function
				# The worst case is that releasing the semaphore would allow one more thread to 
				# begin downloading than it should
				#
				# If the semaphore was not released before the exception, it could cause deadlock
				chapterThreadSemaphore.release()
				self.isThreadFailed = True
				raise FatalError("Thread crashed while downloading chapter: %s" % str(exception))
	
	def download(self):
		threadPool = []
		isAllPassed = True
		SiteParserBase.DownloadChapterThread.initSemaphore(self.maxChapterThreads)
		if (self.verbose_FLAG):
			print("Number of Threads: %d " % self.maxChapterThreads)
		"""
		for loop that goes through the chapters we selected.
		"""
		
		for current_chapter in self.chapters_to_download:
			thread = SiteParserBase.DownloadChapterThread(self, current_chapter)
			threadPool.append(thread)
			thread.start()
				
		while (len(threadPool) > 0):
			thread = threadPool.pop()
			while (thread.isAlive()):
				# Yields control to whomever is waiting 
				time.sleep(0)
			if (isAllPassed and thread.isThreadFailed):
				isAllPassed = False
		
		return isAllPassed

	def postDownloadProcessing(self, manga_chapter_prefix, max_pages):
		if (self.timeLogging_FLAG):
			print("%s (End Time): %s" % (manga_chapter_prefix, str(time.time())))

		SiteParserBase.DownloadChapterThread.releaseSemaphore()
		compressedFile = self.compress(manga_chapter_prefix, max_pages)
		self.convertChapter( compressedFile )	
	
	def convertChapter(self, compressedFile):
		# Check if the conversion flag is set
		if ( self.conversion_FLAG ):
			if (not isImageLibAvailable()):
				print("PIL (Python Image Library) not available.")
			else:	
				from ConvertPackage.ConvertFile import convertFile
				if (self.verbose_FLAG):
					print ("Compressed File "+str(compressedFile))							
				
				if (compressedFile != None and self.outputDir != None):
					convertFile.convert(self.outputMgr, compressedFile, self.outputDir, self.device, self.verbose_FLAG)

########NEW FILE########
__FILENAME__ = batoto
#!/usr/bin/python

import re
import string
from bs4 import BeautifulSoup

from parsers.base import SiteParserBase
from util import fixFormatting, getSourceCode

class Batoto(SiteParserBase):
    class PointlessThing2:
        def __init__(self):
            self.r = 0
        def group(self, x):
            return self.r

    class PointlessThing1:
        def search(self, source):
            soup = BeautifulSoup(source)
            ol = soup.find("select", id="page_select")("option")
            a = Batoto.PointlessThing2()
            a.r = len(ol)
            return a

    re_getMaxPages = PointlessThing1() # This is a terrible hack.
    re_getImage = re.compile("<img id=\"comic_page\".*?src=\"([^\"]+)\"")

    def __init__(self, optDict):
        SiteParserBase.__init__(self, optDict)

    def get_next_url(self, c):
        s = getSourceCode(c, self.proxy)
        soup = BeautifulSoup(s)
        l = soup.find("img", title="Next Chapter").parent
        return l['href']

    def parseSite(self):
        print("Beginning Batoto check: {}".format(self.manga))

        url = "http://www.batoto.net/search?name={}&name_cond=c".format('+'.join(self.manga.split()))
        s = getSourceCode(url, self.proxy)
        soup = BeautifulSoup(s)
        a = soup.find("div", id="comic_search_results")
        r = a.tbody.find_all("tr")[1:]
        seriesl = []
        try:
            for i in r:
                u = i.td.a['href']
                t = i.td.a.img.next_sibling[1:]
                seriesl.append((u,t.encode('utf-8')))
        except TypeError:
            # signifies no manga found
            raise self.MangaNotFound("Nonexistent.")
            
        manga = self.selectFromResults(seriesl)
        if self.verbose_FLAG:
            print(manga)
        mname = [i for i in seriesl if i[0] == manga][0][1]
        s = getSourceCode(manga, self.proxy)
        soup = BeautifulSoup(s)
        t = soup.find("table", class_="chapters_list").tbody
        cl = t.find_all("tr", class_="lang_English")
        self.chapters = [[]]
        cnum = self.chapters[0]
        for i in cl:
            u = i.td.a['href']
            t = i.td.a.img.next_sibling[1:]
            g = i.find_all("td")[2].get_text().strip()
            try:
                c = float(re.search("ch([\d.]+)", u).group(1))
            except AttributeError:
                c = 0
            tu = (u,t,g,c)
            if len(cnum) == 0 or cnum[0][3] == c:
                cnum.append(tu)
            else:
                self.chapters.append([])
                cnum = self.chapters[-1]
                cnum.append(tu)
        self.chapters.reverse()
        sc = None
        for i in self.chapters:
            if len(i) == 1 or sc == None:
                if sc != None and sc[2] != i[0][2]:
                    if self.verbose_FLAG:
                        print("switched to {} at {}".format(i[0][2], i[0][3]))
                sc = i[0]
                del i[1:]
                continue
            ll = [n for n in i if n[2] == sc[2]]
            if len(ll) != 1:
                c = self.get_next_url(sc[0])
                i[0] = [n for n in i if n[0] == c][0]
                if self.verbose_FLAG:
                    print("Anomaly at chapter {} ({} matches, chose {})".format(i[0][3], len(ll), i[0][2]))
                del i[1:]
                sc = i[0]
                continue
            i[0] = ll[0]
            sc = i[0]
            del i[1:]
        self.chapters = [i[0] for i in self.chapters]
        for n,c in enumerate(self.chapters):
            print("{:03d}. {}".format(n+1, c[1].encode('utf-8')))
        self.chapters_to_download = self.selectChapters(self.chapters)

    def downloadChapter(self, downloadThread, max_pages, url, manga_chapter_prefix, current_chapter):
        """We ignore max_pages, because you can't regex-search that under Batoto."""
        s = getSourceCode(url, self.proxy)
        soup = BeautifulSoup(s)
        ol = soup.find("select", id="page_select")("option")
        n = 1
        for i in ol:
            if self.verbose_FLAG:
                print(i['value'])
            self.downloadImage(downloadThread, n, i['value'], manga_chapter_prefix)
            n += 1

########NEW FILE########
__FILENAME__ = factory
#!/usr/bin/env python

#####################

from parsers.mangafox import MangaFox
from parsers.mangareader import MangaReader
from parsers.mangapanda import MangaPanda
from parsers.mangahere import MangaHere
try:
	from bs4 import BeautifulSoup
	from parsers.batoto import Batoto
except ImportError:
	Batoto = None

#####################

class SiteParserFactory():
	"""
	Chooses the right subclass function to call.
	"""
	@staticmethod
	def getInstance(options):
		ParserClass = {
				'[mf]'        : MangaFox,
				'[mr]'        : MangaReader,
				'[mp]'        : MangaPanda,
				'[mh]'        : MangaHere, 
			        '[bt]'        : Batoto,
				'MangaFox'    : MangaFox,
				'MangaReader' : MangaReader,
				'MangaPanda'  : MangaPanda,
				'MangaHere'   : MangaHere,
			        'Batoto'      : Batoto,

				}.get(options.site, None)

		if not ParserClass:
			raise NotImplementedError( "Site Not Supported" )

		return ParserClass(options)

########NEW FILE########
__FILENAME__ = mangafox
#!/usr/bin/env python

####################

import re
import string

#####################

from parsers.base import SiteParserBase
from util import fixFormatting, getSourceCode

#####################

class MangaFox(SiteParserBase):
	re_getSeries = re.compile('a href="http://.*?mangafox.*?/manga/([^/]*)/[^"]*?" class=[^>]*>([^<]*)</a>')
	#re_getSeries = re.compile('a href="/manga/([^/]*)/[^"]*?" class=[^>]*>([^<]*)</a>')
	#re_getChapters = re.compile('"(.*?Ch.[\d.]*)[^"]*","([^"]*)"')
	re_getImage = re.compile('"><img src="([^"]*)"')
	re_getMaxPages = re.compile('var total_pages=([^;]*?);')
	
	def fixFormatting(self, s):
		
		for i in string.punctuation:
			s = s.replace(i, " ")
		
		p = re.compile( '\s+')
		s = p.sub( ' ', s )
		
		s = s.lower().strip().replace(' ', '_')
		return s
		
	def parseSite(self):
		"""
		Parses list of chapters and URLs associated with each one for the given manga and site.
		"""
		
		print('Beginning MangaFox check: %s' % self.manga)

		# jump straight to expected URL and test if manga removed
		url = 'http://mangafox.me/manga/%s/' % self.fixFormatting( self.manga )
		if self.verbose_FLAG:
			print(url)
		
		source, redirectURL = getSourceCode(url, self.proxy, True)

		if (redirectURL != url or source is None or 'the page you have requested cannot be found' in source):
			# Could not find the manga page by guessing 
			# Use the website search
			url = 'http://mangafox.me/search.php?name_method=bw&name=%s&is_completed=&advopts=1' % '+'.join(self.manga.split())
			if self.verbose_FLAG:
				print(url)
			try:
				source = getSourceCode(url, self.proxy)
				seriesResults = []
				if source is not None:
					seriesResults = MangaFox.re_getSeries.findall(source)
				
				if ( 0 == len(seriesResults) ):
					url = 'http://mangafox.me/search.php?name_method=cw&name=%s&is_completed=&advopts=1' % '+'.join(self.manga.split())
					if self.verbose_FLAG:
						print(url)
					source = getSourceCode(url, self.proxy)
					if source is not None:
						seriesResults = MangaFox.re_getSeries.findall(source)
					
			# 0 results
			except AttributeError:
				raise self.MangaNotFound('It doesn\'t exist, or cannot be resolved by autocorrect.')
			else:	
				keyword = self.selectFromResults(seriesResults)
				if self.verbose_FLAG:
					print ("Keyword: %s" % keyword)
				url = 'http://mangafox.me/manga/%s/' % keyword	
				if self.verbose_FLAG:
					print ("URL: %s" % url)				
				source = getSourceCode(url, self.proxy)
				
				if (source is None):
					raise self.MangaNotFound('Search Failed to find Manga.')		
		else:
			# The Guess worked
			keyword = self.fixFormatting( self.manga )
			if self.verbose_FLAG:
				print ("Keyword: %s" % keyword)
		

		if('it is not available in Manga Fox.' in source):
			raise self.MangaNotFound('It has been removed.')
			

		# that's nice of them
		#url = 'http://mangafox.me/cache/manga/%s/chapters.js' % keyword
		#source = getSourceCode(url, self.proxy)
		
		# chapters is a 2-tuple
		# chapters[0] contains the chapter URL
		# chapters[1] contains the chapter title
			
		isChapterOnly = False
		
		# can't pre-compile this because relies on class name
		re_getChapters = re.compile('a href="http://.*?mangafox.*?/manga/%s/(v[\d]+)/(c[\d]+)/[^"]*?" title' % keyword)
		self.chapters = re_getChapters.findall(source)
		if not self.chapters:
			if self.verbose_FLAG:
				print ("Trying chapter only regex")
			isChapterOnly = True
			re_getChapters = re.compile('a href="http://.*?mangafox.*?/manga/%s/(c[\d]+)/[^"]*?" title' % keyword)
			self.chapters = re_getChapters.findall(source)
			
		self.chapters.reverse()
			
		# code used to both fix URL from relative to absolute as well as verify last downloaded chapter for XML component
		lowerRange = 0
			
		if isChapterOnly:
			for i in range(0, len(self.chapters)):
				if self.verbose_FLAG:
					print("%s" % self.chapters[i])
				if (not self.auto):
					print('(%i) %s' % (i + 1, self.chapters[i]))
				else:
					if (self.lastDownloaded == self.chapters[i]):
						lowerRange = i + 1
												
				self.chapters[i] = ('http://mangafox.me/manga/%s/%s' % (keyword, self.chapters[i]), self.chapters[i], self.chapters[i])

		else:				
			for i in range(0, len(self.chapters)):
				if self.verbose_FLAG:
					print("%s %s" % (self.chapters[i][0], self.chapters[i][1]))
				self.chapters[i] = ('http://mangafox.me/manga/%s/%s/%s' % (keyword, self.chapters[i][0], self.chapters[i][1]), self.chapters[i][0] + "." + self.chapters[i][1], self.chapters[i][1])
				if (not self.auto):
					print('(%i) %s' % (i + 1, self.chapters[i][1]))
				else:
					if (self.lastDownloaded == self.chapters[i][1]):
						lowerRange = i + 1

		# this might need to be len(self.chapters) + 1, I'm unsure as to whether python adds +1 to i after the loop or not
		upperRange = len(self.chapters)
			
		# which ones do we want?
		if (not self.auto):
			self.chapters_to_download = self.selectChapters(self.chapters)
		# XML component
		else:
			if ( lowerRange == upperRange):
				raise self.NoUpdates
				
			for i in range (lowerRange, upperRange):
				self.chapters_to_download.append(i)
		return 		
	
	def downloadChapter(self, downloadThread, max_pages, url, manga_chapter_prefix, current_chapter):
		for page in range(1, max_pages + 1):
			if (self.verbose_FLAG):
				print(self.chapters[current_chapter][1] + ' | ' + 'Page %i / %i' % (page, max_pages))

			pageUrl = '%s/%i.html' % (url, page)
			self.downloadImage(downloadThread, page, pageUrl, manga_chapter_prefix)

########NEW FILE########
__FILENAME__ = mangahere
#!/usr/bin/env python

####################

import re
import string
import time

#####################

from parsers.base import SiteParserBase
from util import fixFormatting, getSourceCode

#####################

class MangaHere(SiteParserBase):
	re_getSeries = re.compile('a href="http://.*?mangahere.*?/manga/([^/]*)/[^"]*?" class=[^>]*>([^<]*)</a>')
	#re_getSeries = re.compile('a href="/manga/([^/]*)/[^"]*?" class=[^>]*>([^<]*)</a>')
	#re_getChapters = re.compile('"(.*?Ch.[\d.]*)[^"]*","([^"]*)"')
	re_getImage = re.compile('<img src="([^"]*.jpg)[^"]*"')
	re_getMaxPages = re.compile('var total_pages = ([^;]*?);')
	
	def fixFormatting(self, s):
		
		for i in string.punctuation:
			s = s.replace(i, " ")
		
		p = re.compile( '\s+')
		s = p.sub( ' ', s )
		
		s = s.lower().strip().replace(' ', '_')
		return s
		
	def parseSite(self):
		"""
		Parses list of chapters and URLs associated with each one for the given manga and site.
		"""
		
		print('Beginning MangaHere check: %s' % self.manga)

		# jump straight to expected URL and test if manga removed
		url = 'http://www.mangahere.com/manga/%s/' % self.fixFormatting( self.manga )
		if self.verbose_FLAG:
			print(url)
		source = getSourceCode(url, self.proxy)
		
		if (source is None or 'the page you have requested can' in source):
			# do a 'begins-with' search, then a 'contains' search
			url = 'http://www.mangahere.com/search.php?name=%s' % '+'.join(self.manga.split())
			if self.verbose_FLAG:
				print(url)

			try:
				source = getSourceCode(url, self.proxy)
				if('Sorry you have just searched, please try 5 seconds later.' in source):
					print('Searched too soon, waiting 5 seconds...')
					time.sleep(5)
				seriesResults = MangaHere.re_getSeries.findall(source)
				
				seriesResults = []
				if source is not None:
					seriesResults = MangaHere.re_getSeries.findall(source)
					
				if (0 == len(seriesResults) ):
					url = 'http://www.mangahere.com/search.php?name=%s' % '+'.join(self.manga.split())
					if self.verbose_FLAG:
						print(url)
					source = getSourceCode(url, self.proxy)
					if source is not None:
						seriesResults = MangaHere.re_getSeries.findall(source)
          
			# 0 results
			except AttributeError:
				raise self.MangaNotFound('It doesn\'t exist, or cannot be resolved by autocorrect.')
			else:	
				keyword = self.selectFromResults(seriesResults)
				if self.verbose_FLAG:
					print ("Keyword: %s" % keyword)
				url = 'http://www.mangahere.com/manga/%s/' % keyword
				if self.verbose_FLAG:
					print(url)
				source = getSourceCode(url, self.proxy)
		
		else:
			# The Guess worked
			keyword = self.fixFormatting( self.manga )
			if self.verbose_FLAG:
				print ("Keyword: %s" % keyword)
		
		
		# other check for manga removal if our initial guess for the name was wrong
		if('it is not available in.' in source):
			raise self.MangaNotFound('It has been removed.')
		
		# that's nice of them
		#url = 'http://www.mangahere.com/cache/manga/%s/chapters.js' % keyword
		#source = getSourceCode(url, self.proxy)
	
		# chapters is a 2-tuple
		# chapters[0] contains the chapter URL
		# chapters[1] contains the chapter title
		
		isChapterOnly = False
		
		# can't pre-compile this because relies on class name
		re_getChapters = re.compile('a.*?href="http://.*?mangahere.*?/manga/%s/(v[\d]+)/(c[\d]+(\.[\d]+)?)/[^"]*?"' % keyword)
		self.chapters = re_getChapters.findall(source)
		if not self.chapters:
			if self.verbose_FLAG:
				print ("Trying chapter only regex")
			isChapterOnly = True
			re_getChapters = re.compile('a.*?href="http://.*?mangahere.*?/manga/%s/(c[\d]+(\.[\d]+)?)/[^"]*?"' % keyword)
			self.chapters = re_getChapters.findall(source)
		
		self.chapters.reverse()
		
		# code used to both fix URL from relative to absolute as well as verify last downloaded chapter for XML component
		lowerRange = 0
		
		if isChapterOnly:
			for i in range(0, len(self.chapters)):
				if self.verbose_FLAG:
					print("%s" % self.chapters[i][0])
				if (self.auto):
					if (self.lastDownloaded == self.chapters[i][0]):
						lowerRange = i + 1
												
				self.chapters[i] = ('http://www.mangahere.com/manga/%s/%s' % (keyword, self.chapters[i][0]), self.chapters[i][0], self.chapters[i][0])

		else:				
			for i in range(0, len(self.chapters)):
				if self.verbose_FLAG:
					print("%s %s" % (self.chapters[i][0], self.chapters[i][1]))
				self.chapters[i] = ('http://www.mangahere.com/manga/%s/%s/%s' % (keyword, self.chapters[i][0], self.chapters[i][1]), self.chapters[i][0] + "." + self.chapters[i][1], self.chapters[i][1])
				if (self.auto):
					if (self.lastDownloaded == self.chapters[i][1]):
						lowerRange = i + 1

		# this might need to be len(self.chapters) + 1, I'm unsure as to whether python adds +1 to i after the loop or not
		upperRange = len(self.chapters)
		
		# Validate whether the last chapter is a
		if (self.verbose_FLAG):
			print(self.chapters[upperRange - 1])
			print("Validating chapter: %s" % self.chapters[upperRange - 1][0])
		source = getSourceCode(self.chapters[upperRange - 1][0], self.proxy)
		
		if ('not available yet' in source):
			# If the last chapter is not available remove it from the list
			del self.chapters[upperRange - 1]
			upperRange = upperRange - 1;

		
		# which ones do we want?
		if (not self.auto):
			for i in range(0, upperRange):
				if isChapterOnly:
					print('(%i) %s' % (i + 1, self.chapters[i][0]))
				else:
					print('(%i) %s' % (i + 1, self.chapters[i][1]))
				
			self.chapters_to_download = self.selectChapters(self.chapters)
		# XML component
		else:
			if ( lowerRange == upperRange):
				raise self.NoUpdates
			
			for i in range (lowerRange, upperRange):
				self.chapters_to_download.append(i)
		return 		
	
	def downloadChapter(self, downloadThread, max_pages, url, manga_chapter_prefix, current_chapter):
		for page in range(1, max_pages + 1):
			if (self.verbose_FLAG):
				print(self.chapters[current_chapter][1] + ' | ' + 'Page %i / %i' % (page, max_pages))

			pageUrl = '%s/%i.html' % (url, page)
			self.downloadImage(downloadThread, page, pageUrl, manga_chapter_prefix)

########NEW FILE########
__FILENAME__ = mangapanda
#!/usr/bin/env python

####################################################################
# For more detailed comments look at MangaFoxParser
#
# The code for this sites is similar enough to not need
# explanation, but dissimilar enough to not warrant any further OOP
####################################################################

####################

import re

#####################

from parsers.base import SiteParserBase
from util import getSourceCode

#####################

class MangaPanda(SiteParserBase):

	re_getSeries = re.compile('<li><a href="([^"]*)">([^<]*)</a>')
	re_getChapters = re.compile('<a href="([^"]*)">([^<]*)</a>([^<]*)</td>')
	re_getPage = re.compile("<option value=\"([^']*?)\"[^>]*>\s*(\d*)</option>")
	re_getImage = re.compile('img id="img" .* src="([^"]*)"')
	re_getMaxPages = re.compile('</select> of (\d*)(\s)*</div>')

	def parseSite(self):
		print('Beginning MangaPanda check: %s' % self.manga)
		
		url = 'http://www.mangapanda.com/alphabetical'

		source = getSourceCode(url, self.proxy)
		allSeries = MangaPanda.re_getSeries.findall(source[source.find('series_col'):])

		keyword = self.selectFromResults(allSeries)

		url = 'http://www.mangapanda.com%s' % keyword
		source = getSourceCode(url, self.proxy)

		self.chapters = MangaPanda.re_getChapters.findall(source)
		
		lowerRange = 0
	
		for i in range(0, len(self.chapters)):
			self.chapters[i] = ('http://www.mangapanda.com%s' % self.chapters[i][0], '%s%s' % (self.chapters[i][1], self.chapters[i][2]), self.chapters[i][1])
			if (not self.auto):
				print('(%i) %s' % (i + 1, self.chapters[i][1]))
			else:
				if (self.lastDownloaded == self.chapters[i][1]):
					lowerRange = i + 1
		
		# this might need to be len(self.chapters) + 1, I'm unsure as to whether python adds +1 to i after the loop or not
		upperRange = len(self.chapters)
		self.isPrependMangaName = False				
		if (not self.auto):
			self.chapters_to_download = self.selectChapters(self.chapters)
		else:
			if (lowerRange == upperRange):
				raise self.NoUpdates
			
			for i in range (lowerRange, upperRange):
				self.chapters_to_download .append(i)
		
		self.isPrependMangaName = True
		
		return 
	
	def downloadChapter(self, downloadThread, max_pages, url, manga_chapter_prefix, current_chapter):
		pageIndex = 0
		for page in MangaPanda.re_getPage.findall(getSourceCode(url, self.proxy)):
			if (self.verbose_FLAG):
				print(self.chapters[current_chapter][1] + ' | ' + 'Page %s / %i' % (page[1], max_pages))

			pageUrl = 'http://www.mangapanda.com' + page[0]
			self.downloadImage(downloadThread, page[1], pageUrl, manga_chapter_prefix)
			pageIndex = pageIndex + 1

########NEW FILE########
__FILENAME__ = mangareader
#!/usr/bin/env python

####################################################################
# For more detailed comments look at MangaFoxParser
#
# The code for this sites is similar enough to not need
# explanation, but dissimilar enough to not warrant any further OOP
####################################################################

####################

import re

#####################

from parsers.base import SiteParserBase
from util import getSourceCode

#####################

class MangaReader(SiteParserBase):

	re_getSeries = re.compile('<li><a href="([^"]*)">([^<]*)</a>')
	re_getChapters = re.compile('<a href="([^"]*)">([^<]*)</a>([^<]*)</td>')
	re_getPage = re.compile("<option value=\"([^']*?)\"[^>]*>\s*(\d*)</option>")
	re_getImage = re.compile('img id="img" .* src="([^"]*)"')
	re_getMaxPages = re.compile('</select> of (\d*)(\s)*</div>')

	def parseSite(self):
		print('Beginning MangaReader check: %s' % self.manga)
		
		url = 'http://www.mangareader.net/alphabetical'

		source = getSourceCode(url, self.proxy)
		allSeries = MangaReader.re_getSeries.findall(source[source.find('series_col'):])

		keyword = self.selectFromResults(allSeries)

		url = 'http://www.mangareader.net%s' % keyword
		source = getSourceCode(url, self.proxy)

		self.chapters = MangaReader.re_getChapters.findall(source)
		
		lowerRange = 0
	
		for i in range(0, len(self.chapters)):
			self.chapters[i] = ('http://www.mangareader.net%s' % self.chapters[i][0], '%s%s' % (self.chapters[i][1], self.chapters[i][2]), self.chapters[i][1])
			if (not self.auto):
				print('(%i) %s' % (i + 1, self.chapters[i][1]))
			else:
				if (self.lastDownloaded == self.chapters[i][1].decode('utf-8')):
					lowerRange = i + 1
		
		# this might need to be len(self.chapters) + 1, I'm unsure as to whether python adds +1 to i after the loop or not
		upperRange = len(self.chapters)
		self.isPrependMangaName = False				
		if (not self.auto):
			self.chapters_to_download = self.selectChapters(self.chapters)
		else:
			if (lowerRange == upperRange):
				raise self.NoUpdates
			
			for i in range (lowerRange, upperRange):
				self.chapters_to_download .append(i)
		
		self.isPrependMangaName = True
		
		return 
	
	def downloadChapter(self, downloadThread, max_pages, url, manga_chapter_prefix, current_chapter):
		pageIndex = 0
		for page in MangaReader.re_getPage.findall(getSourceCode(url, self.proxy)):
			if (self.verbose_FLAG):
				print(self.chapters[current_chapter][1] + ' | ' + 'Page %s / %i' % (page[1], max_pages))

			pageUrl = 'http://www.mangareader.net' + page[0]
			self.downloadImage(downloadThread, page[1], pageUrl, manga_chapter_prefix)
			pageIndex = pageIndex + 1

########NEW FILE########
__FILENAME__ = thread
#!/usr/bin/env python

#####################

import datetime
import threading
import time
import os
try:
	import socks
	NO_SOCKS = False
except ImportError:
	NO_SOCKS = True
import socket
#####################

from parsers.base import SiteParserBase
from parsers.factory import SiteParserFactory
from util import isImageLibAvailable, updateNode

#####################

class SiteParserThread( threading.Thread ):

	def __init__ ( self, optDict, dom, node ):
		threading.Thread.__init__(self)
		self.uptodate_FLAG = False
		
		for elem in vars(optDict):
			setattr(self, elem, getattr(optDict, elem))
			
		self.dom = dom
		self.node = node
		self.siteParser = SiteParserFactory.getInstance(self)
				
		try:
			self.siteParser.parseSite()
			# create download directory if not found
			try:
				if os.path.exists(self.downloadPath) is False:
					os.makedirs(self.downloadPath)
			except OSError:
				print("""Unable to create download directory. There may be a file 
					with the same name, or you may not have permissions to write 
					there.""")
				raise

		except self.siteParser.NoUpdates:
			self.uptodate_FLAG = True
			print ("Manga ("+self.manga+") up-to-date.")
		print('\n')
			
	def run (self):
		success = False
		if (self.uptodate_FLAG):
			return		
			
		try:
			for current_chapter in self.siteParser.chapters:
				#print "Current Chapter =" + str(current_chapter[0])
				iLastChap = current_chapter[1]
		
			success = self.siteParser.download()
			
		except SiteParserBase.MangaNotFound as Instance:
			print("Error: Manga ("+self.manga+")")
			print(Instance)
			print("\n")
			return 
		
		# Update the XML File only when all the chapters successfully download. If 1 of n chapters failed 
		# to download, the next time the script is run the script will try to download all n chapters. However,
		# autoskipping (unless the user specifies the --overwrite Flag) should skip the chapters that were already
		# downloaded so little additional time should be added.
			
		if self.xmlfile_path != None and success:
			updateNode(self.dom, self.node, 'LastChapterDownloaded', str(iLastChap))
			self.updateTimestamp()	
		
	def updateTimestamp(self):
		t = datetime.datetime.today()
		timeStamp = "%d-%02d-%02d %02d:%02d:%02d" % (t.year, t.month, t.day, t.hour, t.minute, t.second)
		
		updateNode(self.dom, self.node, 'timeStamp', timeStamp)

########NEW FILE########
__FILENAME__ = decorators
import functools

# :SEE: http://wiki.python.org/moin/PythonDecoratorLibrary/#Alternate_memoize_as_nested_functions
def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]

    return memoizer


def post_hookable(cls):
    cls.post_hook()
    return cls
########NEW FILE########
__FILENAME__ = image
class Image:
    def __init__(self, url):
        self.url = url

########NEW FILE########
__FILENAME__ = hasurl
from redux.helper.decorators import memoize
from redux.helper.util import Util


class HasUrl(object):
    @property
    @memoize
    def source(self):
        return Util.getSourceCode(self.url)

########NEW FILE########
__FILENAME__ = util
import gzip
import io
import random
import re
import time

try:
    import socks

    NO_SOCKS = False
except ImportError:
    NO_SOCKS = True
import socket

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

try:
    import HTMLParser
except ImportError:
    import html.parser as HTMLParser


class Util:
    @staticmethod
    def getSourceCode(url, proxy=None, returnRedirctUrl=False, maxRetries=1, waitRetryTime=1):
        """
        :rtype: str

        Loop to get around server denies for info or minor disconnects.
        """
        if (proxy != None):
            if (NO_SOCKS):
                raise RuntimeError('socks library required to use proxy (e.g. SocksiPy)')
            proxySettings = proxy.split(':')
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4, proxySettings[0], int(proxySettings[1]),
                                  True)
            socket.socket = socks.socksocket
        ret = None
        request = urllib2.Request(url, headers={
            'User-agent': """Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.3 (KHTML,
            like Gecko) Chrome/6.0.472.14 Safari/534.3""",
            'Accept-encoding': 'gzip'
        })
        while (ret == None):
            try:
                f = urllib2.urlopen(request)
                encoding = f.headers.get('Content-Encoding')
                if encoding == None:
                    ret = f.read()
                else:
                    if encoding.upper() == 'GZIP':
                        compressedstream = io.BytesIO(f.read())
                        gzipper = gzip.GzipFile(fileobj=compressedstream)
                        ret = gzipper.read()
                    else:
                        raise RuntimeError('Unknown HTTP Encoding returned')
            except urllib2.URLError:
                if (maxRetries == 0):
                    break
                else:
                    # random dist. for further protection against anti-leech
                    # idea from wget
                    time.sleep(random.uniform(0.5 * waitRetryTime, 1.5 * waitRetryTime))
                    maxRetries -= 1
        ret = str(ret)
        if returnRedirctUrl:
            return ret, f.geturl()
        else:
            return ret

    @staticmethod
    def normalize_value(s):
        """
        :rtype: str
        """
        try:
            float(s)
        except ValueError:
            return s
        else:
            return str(int(float(s)) if int(float(s)) == float(s) else float(s))

    @staticmethod
    # :SEE: http://stackoverflow.com/a/8940266/759714
    def natural_sort(l, key=lambda s: s):
        """
        :rtype: list

        Return a copy of the list in natural alphanumeric order.
        """

        def get_alphanum_key_func(key):
            convert = lambda text: int(text) if text.isdigit() else text
            return lambda s: [convert(c) for c in re.split('([0-9]+)', key(s))]

        sort_key = get_alphanum_key_func(key)
        return sorted(l, key=sort_key)

    @staticmethod
    # :SEE: http://stackoverflow.com/a/275246/759714
    def unescape(s):
        """
        :rtype: str
        """
        return HTMLParser.HTMLParser().unescape(s)

########NEW FILE########
__FILENAME__ = metasite
from collections import OrderedDict

from underscore import _

from redux.helper.decorators import memoize
from redux.helper.util import Util


class MetaSite(object):
    def __init__(self, modules=[], options={}):
        self.modules = modules
        self.options = options

    @memoize
    def series(self, name):
        """
        :type name: str
        :rtype: MetaSeries
        """
        return MetaSite.MetaSeries(self, name)

    class MetaSeries(object):
        def __init__(self, site, name):
            """
            :type site: MetaSite
            :type name: str
            """
            self.site = site
            self.name = name

        @property
        @memoize
        def chapters(self):
            """
            :rtype: OrderedDict of (str, MetaChapter)
            """
            all_chapters = _.flatten([
                site.series(self.name).chapters for site in self.site.modules
            ])

            chapter_map = OrderedDict(
                Util.natural_sort(
                    _.groupBy(all_chapters, lambda chapter, index: chapter.chapter).items(),
                    key=lambda t: t[0]
                )
            )

            return OrderedDict(
                (chapter, MetaSite.MetaChapter(self, chapter, choices)) for chapter, choices in
                chapter_map.items())

    class MetaChapter(object):
        def __init__(self, series, chapter, choices):
            """
            :type series: MetaSeries
            :type chapter: str
            :type choices: list of redux.site.mangasite.MangaSite.Chapter
            """
            self.series = series
            self.chapter = chapter
            self.choices = choices

        @property
        @memoize
        def title(self):
            """
            :rtype: str
            """
            return (_(self.choices).chain()
                    .map(lambda chapter, *args: chapter.title)
                    .sortBy(lambda title, *args: len(title))
                    .last().value()
            )

        @property
        @memoize
        def first_available_choice(self):
            """
            :rtype: redux.site.mangasite.MangaSite.Chapter
            """
            return _(self.choices).find(
                lambda chapter, *args: (_(chapter.pages).chain()
                                        .map(lambda page, *args: page.image)
                                        .all(lambda image, *args: image is not None).value()
                )
            )

        @property
        @memoize
        def pages(self):
            """
            :rtype: list of redux.site.mangasite.MangaSite.Page
            """
            return self.first_available_choice.pages

########NEW FILE########
__FILENAME__ = aftv
import re

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from redux.helper.decorators import memoize
from redux.helper.util import Util
from redux.site.mangasite import MangaSite


class Aftv(MangaSite):
    class Chapter(MangaSite.Chapter):
        @property
        def volume(self):
            return None

        @property
        def pages(self):
            if self.url.endswith('.html'):
                page_base_url = re.sub('(\d+)-(\d+)-(\d+)', '\\1-\\2-{index}', self.url)
            else:
                page_base_url = self.url + '/{index}'

            return [self.series.site.Page(self, page_base_url.format(index=index)) for index in
                    range(1, self.number_of_pages + 1)]

    class Series(MangaSite.Series):
        CHAPTER_FROM_SOURCE_REGEX = re.compile(
            '<a href="(?P<path>[^"]*)">[^<]*</a>[^:]*: (?P<title>[^<]*)</td>')

        class Metadata(object):
            def __init__(self, name1, picture_link, name2, author_name, path, id):
                self.name = name1
                self.picture_link = picture_link
                self.author_name = author_name
                self.path = path
                self.id = id

        @property
        def normalized_name(self):
            return self.metadata.name

        @property
        def chapters(self):
            ret = [self.site.Chapter(self, Util.unescape(match.group('title') or ''),
                                     self.TEMPLATE_URL.format(path=match.group('path'))) for match
                   in self.CHAPTER_FROM_SOURCE_REGEX.finditer(self.source)]

            return ret

        @property
        def url(self):
            return self.TEMPLATE_URL.format(path=self.metadata.path)

        @property
        @memoize
        def metadata(self):
            url = self.TEMPLATE_URL.format(
                path=('/actions/search/?q={name}'.format(name=self.name.replace(' ', '+'))))

            lines = urllib2.urlopen(url)
            first_result = str(lines.readline())

            return self.Metadata(*first_result.split('|'))

########NEW FILE########
__FILENAME__ = mangafox
import re

from redux.site.noez import Noez


class MangaFox(Noez):
    class Chapter(Noez.Chapter):
        VOLUME_AND_CHAPTER_FROM_URL_REGEX = re.compile(
            'http://mangafox.me/manga/[^/]*/(v(?P<volume>[^/]*)/)?c(?P<chapter>[^/]*)')
        TOTAL_PAGES_FROM_SOURCE_REGEX = re.compile('var total_pages=(?P<count>[^;]*?);')

    class Page(Noez.Page):
        IMAGE_FROM_SOURCE_REGEX = re.compile('"><img src="(?P<link>[^"]*)"')

    class Series(Noez.Series):
        CHAPTER_FROM_SOURCE_REGEX = re.compile(
            'a href="(?P<url>[^"]*)" title=.*?(title nowrap">(?P<title>[^<]*))?<\/span>', re.DOTALL)
        TEMPLATE_URL = 'http://mangafox.me/manga/{name}/'

########NEW FILE########
__FILENAME__ = mangahere
import re

from redux.site.noez import Noez


class MangaHere(Noez):
    class Chapter(Noez.Chapter):
        VOLUME_AND_CHAPTER_FROM_URL_REGEX = re.compile(
            'http://www.mangahere.com/manga/[^/]*/(v(?P<volume>[^/]*)/)?c(?P<chapter>[^/]*)')
        TOTAL_PAGES_FROM_SOURCE_REGEX = re.compile('var total_pages = (?P<count>[^;]*?);')

    class Page(Noez.Page):
        IMAGE_FROM_SOURCE_REGEX = re.compile('<img src="(?P<link>[^"]*.jpg)[^"]*"')

    class Series(Noez.Series):
        CHAPTER_FROM_SOURCE_REGEX = re.compile(
            '0077" href="(?P<url>[^"]*)" >.*?<span class="mr6">[^<]*?</span>(?P<title>.*?)</span>',
            re.DOTALL)
        TEMPLATE_URL = 'http://www.mangahere.com/manga/{name}/'

########NEW FILE########
__FILENAME__ = mangapanda
import re

from redux.site.aftv import Aftv


class MangaPanda(Aftv):
    class Chapter(Aftv.Chapter):
        VOLUME_AND_CHAPTER_FROM_URL_REGEX = re.compile(
            'http://www.mangapanda.com/((\d+)-(\d+)-(\d+)/)?[^/]+/(chapter-)?(?P<chapter>\d+)(\
            .html)?')
        TOTAL_PAGES_FROM_SOURCE_REGEX = re.compile('</select> of (?P<count>\d*)(\s)*</div>')

    class Page(Aftv.Page):
        IMAGE_FROM_SOURCE_REGEX = re.compile('img id="img" .*? src="(?P<link>[^"]*)"')

    class Series(Aftv.Series):
        TEMPLATE_URL = 'http://www.mangapanda.com{path}'

########NEW FILE########
__FILENAME__ = mangareader
import re

from redux.site.aftv import Aftv


class MangaReader(Aftv):
    class Chapter(Aftv.Chapter):
        VOLUME_AND_CHAPTER_FROM_URL_REGEX = re.compile(
            'http://www.mangareader.net/((\d+)-(\d+)-(\d+)/)?[^/]+/(chapter-)?(?P<chapter>\d+)(\
            .html)?')
        TOTAL_PAGES_FROM_SOURCE_REGEX = re.compile('</select> of (?P<count>\d*)(\s)*</div>')

    class Page(Aftv.Page):
        IMAGE_FROM_SOURCE_REGEX = re.compile('img id="img" .*? src="(?P<link>[^"]*)"')

    class Series(Aftv.Series):
        TEMPLATE_URL = 'http://www.mangareader.net{path}'

########NEW FILE########
__FILENAME__ = mangasite
import abc
from abc import ABCMeta

from redux.helper.decorators import memoize
from redux.helper.image import Image
from redux.helper.traits.hasurl import HasUrl
from redux.helper.util import Util


class MangaSite(object):
    __metaclass__ = ABCMeta

    @classmethod
    @memoize
    def series(cls, name):
        return cls.Series(cls, name)

    class Chapter(HasUrl):
        __metaclass__ = ABCMeta

        VOLUME_AND_CHAPTER_FROM_URL_REGEX = NotImplemented
        TOTAL_PAGES_FROM_SOURCE_REGEX = NotImplemented
        CHAPTER_TITLE_FROM_SOURCE_REGEX = NotImplemented

        def __init__(self, series, title, url):
            """
            :type series: Series
            :type title: str
            :type url: str
            """
            self.series = series
            self.title = title
            self.url = url

        @property
        @memoize
        def volume(self):
            """
            :rtype: str or None
            """
            match = self.VOLUME_AND_CHAPTER_FROM_URL_REGEX.match(self.url)

            if match is not None and match.group('volume') is not None:
                return Util.normalize_value(match.group('volume'))
            else:
                return None

        @property
        @memoize
        def chapter(self):
            """
            :rtype: str or None
            """
            match = self.VOLUME_AND_CHAPTER_FROM_URL_REGEX.match(self.url)

            if match is not None and match.group('chapter') is not None:
                return Util.normalize_value(match.group('chapter'))
            else:
                return None

        @property
        @memoize
        def number_of_pages(self):
            """
            :rtype: int
            """
            return int(self.TOTAL_PAGES_FROM_SOURCE_REGEX.search(self.source).group('count'))

        @abc.abstractproperty
        @memoize
        def pages(self):
            """
            :rtype: list of Page
            """
            pass

    class Page(HasUrl):
        __metaclass__ = ABCMeta

        IMAGE_FROM_SOURCE_REGEX = NotImplemented

        def __init__(self, chapter, url):
            """
            :type chapter: Chapter
            :type url: str
            """
            self.chapter = chapter
            self.url = url

        @property
        @memoize
        def image(self):
            """
            :rtype: Image or None
            """
            return Image(str(self.IMAGE_FROM_SOURCE_REGEX.search(self.source).group(
                'link'))) if self.IMAGE_FROM_SOURCE_REGEX.search(self.source) is not None else None

    class Series(HasUrl):
        __metaclass__ = ABCMeta

        CHAPTER_FROM_SOURCE_REGEX = NotImplemented
        TEMPLATE_URL = NotImplemented

        def __init__(self, site, name):
            """
            :type site: MangaSite
            :type name: str
            """
            self.site = site
            self.name = name

        @property
        @memoize
        def url(self):
            """
            :rtype: str
            """
            return self.TEMPLATE_URL.format(name=self.normalized_name)

        @abc.abstractproperty
        @memoize
        def normalized_name(self):
            """
            :rtype: str
            """
            pass

        @abc.abstractproperty
        @memoize
        def chapters(self):
            """
            :rtype: list of Chapter
            """
            pass

########NEW FILE########
__FILENAME__ = noez
import re
import string

from redux.helper.util import Util
from redux.site.mangasite import MangaSite


class Noez(MangaSite):
    class Chapter(MangaSite.Chapter):
        @property
        def pages(self):
            return [
                self.series.site.Page(self, '{url}/{index}.html'.format(url=self.url, index=index))
                for index in range(1, self.number_of_pages + 1)]

    class Series(MangaSite.Series):
        @property
        def normalized_name(self):
            def fixFormatting(s):
                for i in string.punctuation:
                    s = s.replace(i, " ")
                p = re.compile('\s+')
                s = p.sub(' ', s)
                s = s.lower().strip().replace(' ', '_')
                return s

            return fixFormatting(self.name)

        @property
        def chapters(self):
            ret = [self.site.Chapter(self, Util.unescape(match.group('title') or ''),
                                     match.group('url')) for match in
                   self.CHAPTER_FROM_SOURCE_REGEX.finditer(self.source)]
            ret.reverse()

            return ret

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

####################

import gzip
import io
import random
import re
import string
import time
try:
	import socks
	NO_SOCKS = False
except ImportError:
	NO_SOCKS = True
import socket
###################

try:
	import urllib2
except ImportError:
	import urllib.request as urllib2

####################

# overwrite user agent for spoofing, enable GZIP
urlReqHeaders = {	'User-agent':	"""Mozilla/5.0 (X11; U; Linux i686; 
					en-US) AppleWebKit/534.3 (KHTML, like 
					Gecko) Chrome/6.0.472.14 Safari/534.3""",
			'Accept-encoding':'gzip'				}

####################

# something seriously wrong happened
class FatalError(Exception):
	pass

def fixFormatting(s, spaceToken):
	"""
	Special character fix for filesystem paths.
	"""
	
	for i in string.punctuation:
		if(i != '-' and i != spaceToken):
			s = s.replace(i, '')
	return s.lower().lstrip(spaceToken).strip().replace(' ', spaceToken)

def getSourceCode(url, proxy, returnRedirctUrl = False, maxRetries=1, waitRetryTime=1):
	"""
	Loop to get around server denies for info or minor disconnects.
	"""
	if (proxy is not None):
		if (NO_SOCKS):
			raise FatalError('socks library required to use proxy (e.g. SocksiPy)')
		proxySettings = proxy.split(':')
		socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4, proxySettings[0], int(proxySettings[1]), True)
		socket.socket = socks.socksocket
				
	global urlReqHeaders
	
	ret = None
	request = urllib2.Request(url, headers=urlReqHeaders) 
	
	while (ret == None): 
		try:
			f = urllib2.urlopen(request)
			encoding = f.headers.get('Content-Encoding')
					
			if encoding == None:
				ret = f.read()
			else:
				if encoding.upper() == 'GZIP': 
					compressedstream = io.BytesIO(f.read()) 
					gzipper = gzip.GzipFile(fileobj=compressedstream)
					ret = gzipper.read()
				else:
					raise FatalError('Unknown HTTP Encoding returned')
		except urllib2.URLError:
			if (maxRetries == 0):
				break
			else:
				# random dist. for further protection against anti-leech
				# idea from wget
				time.sleep(random.uniform(0.5*waitRetryTime, 1.5*waitRetryTime))
				maxRetries -= 1

	if returnRedirctUrl:
		return ret, f.geturl()
	else:
		return ret

def isImageLibAvailable():
	try:
		from ConvertPackage.ConvertFile import convertFile
		return True
	except ImportError:
		return False

def zeroFillStr(inputString, numOfZeros):
	return re.sub(	'\d+', 
					lambda matchObj:
						# string formatting trick to zero-pad 
						('%0' + str(numOfZeros) + 'i') % int(matchObj.group(0)), 
					inputString	)

#=========================
#
# XML Helper Functions
#
#=========================

def getText(node):
	rc = []
	for node in node.childNodes:
		if node.nodeType == node.TEXT_NODE:
			rc.append(node.data)		
			
		return ''.join(rc)
#		return ''.join([node.data for node in nodelist if node.nodeType == node.TEXT_NODE])			

def setText(dom, node, text):
	for currNode in node.childNodes:
		if currNode.nodeType == currNode.TEXT_NODE:
			currNode.data = text
			return

	# If this code is executed, it means that the loop failed to find a text node
	# A new text needs to be created and appended to this node
	textNode = dom.createTextNode(text) 	
	node.appendChild(textNode)

def updateNode(dom, node, tagName, text):
	text = text.decode('utf-8')
	if (len(node.getElementsByTagName(tagName)) > 0):
		updateNode = node.getElementsByTagName(tagName)[0]
	else:
		# Node Currently Does have a timeStamp Node Must add one
		updateNode = dom.createElement(tagName)
		node.appendChild(updateNode)
		
	setText(dom, updateNode, text) 	
	

########NEW FILE########
__FILENAME__ = xmlparser
#!/usr/bin/env python

######################

from xml.dom import minidom

######################

from parsers.thread import SiteParserThread
from util import fixFormatting, getText
import os
######################

class MangaXmlParser:
	def __init__(self, optDict):
		self.options = optDict
		for elem in vars(optDict):
			setattr(self, elem, getattr(optDict, elem))

	def downloadManga(self):
		print("Parsing XML File...")
		if (self.verbose_FLAG):
			print("XML Path = %s" % self.xmlfile_path)
 
		dom = minidom.parse(self.xmlfile_path)
		
		threadPool = []
		self.options.auto = True
		
		SetOutputPathToName_Flag = False
		# Default OutputDir is the ./MangaName
		if (self.options.outputDir == 'DEFAULT_VALUE'):
			SetOutputPathToName_Flag = True
			
		for node in dom.getElementsByTagName("MangaSeries"):
			seriesOptions = self.options
			seriesOptions.manga = getText(node.getElementsByTagName('name')[0])
			seriesOptions.site = getText(node.getElementsByTagName('HostSite')[0])
			
			try:
				lastDownloaded = getText(node.getElementsByTagName('LastChapterDownloaded')[0])
			except IndexError:
				lastDownloaded = ""
			
			try:
				download_path =	getText(node.getElementsByTagName('downloadPath')[0])
			except IndexError:
				download_path = ('./' + fixFormatting(seriesOptions.manga))
			
			if self.options.downloadPath != 'DEFAULT_VALUE' and not os.path.isabs(download_path):
				download_path = os.path.join(self.options.downloadPath, download_path)
			
			seriesOptions.downloadPath = download_path
			seriesOptions.lastDownloaded = lastDownloaded
			if SetOutputPathToName_Flag:
				seriesOptions.outputDir = download_path
			
			# Because the SiteParserThread constructor parses the site to retrieve which chapters to 
			# download the following code would be faster
			
			# thread = SiteParserThread(self.options, dom, node)
			# thread.start()
			# threadPool.append(thread)
			
			# Need to remove the loop which starts the thread's downloading. The disadvantage is that the 
			# the print statement would intermingle with the progress bar. It would be very difficult to 
			# understand what was happening. Do not believe this change is worth it.
			
			threadPool.append(SiteParserThread(seriesOptions, dom, node))
		
		for thread in threadPool: 
			thread.start()
			thread.join()

		#print (dom.toxml())		
		#Backs up file
		backupFileName = self.xmlfile_path + "_bak"
		os.rename(self.xmlfile_path, backupFileName)
		f = open(self.xmlfile_path, 'w')
		outputStr = dom.toxml()
		outputStr = outputStr.encode('utf-8')
		f.write(outputStr) 
		
		# The file was succesfully saved and now remove backup
		os.remove(backupFileName)

########NEW FILE########
__FILENAME__ = test_mangaFox
from unittest import TestCase

from redux.site.mangafox import MangaFox


class TestMangaFox(TestCase):
    SERIES = MangaFox.series('gantz')
    CHAPTERS = SERIES.chapters

    def test_chapter_count(self):
        self.assertEqual(len(TestMangaFox.CHAPTERS), 386)

    def test_chapter_title(self):
        self.assertEqual(TestMangaFox.CHAPTERS[-2].title, 'Lightning Counterstrike')

    def test_chapter_pages(self):
        self.assertEqual(len(TestMangaFox.CHAPTERS[0].pages), 43)

    def test_for_image_url(self):
        url = TestMangaFox.CHAPTERS[0].pages[0].image.url
        self.assertTrue(len(url) > 0)
        self.assertEqual(url[:7], 'http://')

########NEW FILE########
__FILENAME__ = test_mangaHere
from unittest import TestCase

from redux.site.mangahere import MangaHere


class TestMangaHere(TestCase):
    SERIES = MangaHere.series('gantz')
    CHAPTERS = SERIES.chapters

    def test_chapter_count(self):
        self.assertEqual(len(TestMangaHere.SERIES.chapters), 377)

    def test_chapter_title(self):
        self.assertEqual(TestMangaHere.CHAPTERS[-2].title, 'Lightning Counterstrike')

    def test_chapter_pages(self):
        self.assertEqual(len(TestMangaHere.CHAPTERS[0].pages), 43)

    def test_for_image_url(self):
        url = TestMangaHere.CHAPTERS[0].pages[0].image.url
        self.assertTrue(len(url) > 0)
        self.assertEqual(url[:7], 'http://')

########NEW FILE########
__FILENAME__ = test_mangaPanda
from unittest import TestCase

from redux.site.mangapanda import MangaPanda


class TestMangaPanda(TestCase):
    SERIES = MangaPanda.series('gantz')
    CHAPTERS = SERIES.chapters

    def test_chapter_count(self):
        self.assertEqual(len(TestMangaPanda.SERIES.chapters), 383)

    def test_chapter_title(self):
        self.assertEqual(TestMangaPanda.CHAPTERS[-2].title, 'Lightning Counterstrike')

    def test_chapter_pages(self):
        self.assertEqual(len(TestMangaPanda.CHAPTERS[0].pages), 43)

    def test_for_image_url(self):
        url = TestMangaPanda.CHAPTERS[0].pages[0].image.url
        self.assertTrue(len(url) > 0)
        self.assertEqual(url[:7], 'http://')

########NEW FILE########
__FILENAME__ = test_mangaReader
from unittest import TestCase

from redux.site.mangareader import MangaReader


class TestMangaReader(TestCase):
    SERIES = MangaReader.series('gantz')
    CHAPTERS = SERIES.chapters

    def test_chapter_count(self):
        self.assertEqual(len(TestMangaReader.SERIES.chapters), 383)

    def test_chapter_title(self):
        self.assertEqual(TestMangaReader.CHAPTERS[-2].title, 'Lightning Counterstrike')

    def test_chapter_pages(self):
        self.assertEqual(len(TestMangaReader.CHAPTERS[0].pages), 43)

    def test_for_image_url(self):
        url = TestMangaReader.CHAPTERS[0].pages[0].image.url
        self.assertTrue(len(url) > 0)
        self.assertEqual(url[:7], 'http://')

########NEW FILE########
__FILENAME__ = test_metasite
from unittest import TestCase

from src.redux.metasite import MetaSite
from src.redux.site.mangafox import MangaFox
from src.redux.site.mangahere import MangaHere
from src.redux.site.mangapanda import MangaPanda
from src.redux.site.mangareader import MangaReader


class TestMetaSite(TestCase):
    SITE = MetaSite(dict())
    SITE.modules = [MangaFox, MangaHere, MangaPanda, MangaReader]

    CHAPTERS = SITE.series('death note').chapters

    def test_chapter_length(self):
        self.assertEqual(len(TestMetaSite.CHAPTERS), 112)

    def test_chapter_title(self):
        chapter = TestMetaSite.CHAPTERS['42']
        self.assertEqual(chapter.title, 'Heaven')

    def test_image_existence(self):
        self.assertIsNotNone(TestMetaSite.CHAPTERS['22'].pages[2].image.url)

########NEW FILE########
