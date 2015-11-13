__FILENAME__ = about
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


from PyQt4 import QtGui, uic

import util


class DialogAbout(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(util.buildResPath('mangle/ui/about.ui'), self)

########NEW FILE########
__FILENAME__ = book
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


from os.path import basename
import os.path
import tempfile
from zipfile import ZipFile

from PyQt4 import QtGui, QtCore, QtXml, uic
from natsort import natsorted

from about import DialogAbout
from convert import DialogConvert
from image import ImageFlags
from options import DialogOptions
import util


class Book(object):
    DefaultDevice = 'Kindle Paperwhite'
    DefaultOutputFormat = 'CBZ only'
    DefaultOverwrite = True
    DefaultImageFlags = ImageFlags.Orient | ImageFlags.Resize | ImageFlags.Quantize


    def __init__(self):
        self.images = []
        self.filename = None
        self.modified = False
        self.title = None
        self.titleSet = False
        self.device = Book.DefaultDevice
        self.overwrite = Book.DefaultOverwrite
        self.imageFlags = Book.DefaultImageFlags
        self.outputFormat = Book.DefaultOutputFormat


    def save(self, filename):
        document = QtXml.QDomDocument()

        root = document.createElement('book')
        document.appendChild(root)

        root.setAttribute('title', self.title)
        root.setAttribute('overwrite', 'true' if self.overwrite else 'false')
        root.setAttribute('device', self.device)
        root.setAttribute('imageFlags', self.imageFlags)
        root.setAttribute('outputFormat', self.outputFormat)

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
        self.outputFormat = root.attribute('outputFormat', Book.DefaultOutputFormat)
        self.imageFlags = int(root.attribute('imageFlags', str(Book.DefaultImageFlags)))
        self.filename = filename
        self.modified = False
        self.images = []

        items = root.elementsByTagName('image')
        if items is None:
            return

        for i in xrange(0, len(items)):
            item = items.at(i).toElement()
            if item.hasAttribute('filename'):
                self.images.append(item.attribute('filename'))


class MainWindowBook(QtGui.QMainWindow):
    def __init__(self, filename=None):
        QtGui.QMainWindow.__init__(self)

        uic.loadUi(util.buildResPath('mangle/ui/book.ui'), self)
        self.listWidgetFiles.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.actionFileNew.triggered.connect(self.onFileNew)
        self.actionFileOpen.triggered.connect(self.onFileOpen)
        self.actionFileSave.triggered.connect(self.onFileSave)
        self.actionFileSaveAs.triggered.connect(self.onFileSaveAs)
        self.actionBookOptions.triggered.connect(self.onBookOptions)
        self.actionBookAddFiles.triggered.connect(self.onBookAddFiles)
        self.actionBookAddDirectory.triggered.connect(self.onBookAddDirectory)
        self.actionBookShiftUp.triggered.connect(self.onBookShiftUp)
        self.actionBookShiftDown.triggered.connect(self.onBookShiftDown)
        self.actionBookRemove.triggered.connect(self.onBookRemove)
        self.actionBookExport.triggered.connect(self.onBookExport)
        self.actionHelpAbout.triggered.connect(self.onHelpAbout)
        self.actionHelpHomepage.triggered.connect(self.onHelpHomepage)
        self.listWidgetFiles.customContextMenuRequested.connect(self.onFilesContextMenu)
        self.listWidgetFiles.itemDoubleClicked.connect(self.onFilesDoubleClick)

        self.book = Book()
        if filename is not None:
            self.loadBook(filename)


    def closeEvent(self, event):
        if not self.saveIfNeeded():
            event.ignore()


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()


    def dropEvent(self, event):
        directories = []
        filenames = []

        for url in event.mimeData().urls():
            filename = url.toLocalFile()
            if self.isImageFile(filename):
                filenames.append(filename)
            elif os.path.isdir(unicode(filename)):
                directories.append(filename)

        self.addImageDirs(directories)
        self.addImageFiles(filenames)


    def onFileNew(self):
        if self.saveIfNeeded():
            self.book = Book()
            self.listWidgetFiles.clear()


    def onFileOpen(self):
        if not self.saveIfNeeded():
            return

        filename = QtGui.QFileDialog.getOpenFileName(
            parent=self,
            caption='Select a book file to open',
            filter='Mangle files (*.mngl);;All files (*.*)'
        )
        if not filename.isNull():
            self.loadBook(self.cleanupBookFile(filename))


    def onFileSave(self):
        self.saveBook(False)


    def onFileSaveAs(self):
        self.saveBook(True)


    def onFilesContextMenu(self, point):
        menu = QtGui.QMenu(self)
        menu.addAction(self.menu_Add.menuAction())

        if len(self.listWidgetFiles.selectedItems()) > 0:
            menu.addAction(self.menu_Shift.menuAction())
            menu.addAction(self.actionBookRemove)

        menu.exec_(self.listWidgetFiles.mapToGlobal(point))


    def onFilesDoubleClick(self, item):
        services = QtGui.QDesktopServices()
        services.openUrl(QtCore.QUrl.fromLocalFile(item.text()))


    def onBookAddFiles(self):
        filenames = QtGui.QFileDialog.getOpenFileNames(
            parent=self,
            caption='Select image file(s) to add',
            filter='Image files (*.jpeg *.jpg *.gif *.png);;Comic files (*.cbz)'
        )
        if(self.containsCbzFile(filenames)):
            self.addCBZFiles(filenames)
        else:
            self.addImageFiles(filenames)


    def onBookAddDirectory(self):
        directory = QtGui.QFileDialog.getExistingDirectory(self, 'Select an image directory to add')
        if not directory.isNull():
            self.book.title = os.path.basename(os.path.normpath(unicode(directory)))
            self.addImageDirs([directory])


    def onBookShiftUp(self):
        self.shiftImageFiles(-1)


    def onBookShiftDown(self):
        self.shiftImageFiles(1)


    def onBookRemove(self):
        self.removeImageFiles()


    def onBookOptions(self):
        dialog = DialogOptions(self, self.book)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            self.book.titleSet = True


    def onBookExport(self):
        if len(self.book.images) == 0:
            QtGui.QMessageBox.warning(self, 'Mangle', 'This book has no images to export')
            return

        if not self.book.titleSet:  # if self.book.title is None:
            dialog = DialogOptions(self, self.book)
            if dialog.exec_() == QtGui.QDialog.Rejected:
                return
            else:
                self.book.titleSet = True

        directory = QtGui.QFileDialog.getExistingDirectory(self, 'Select a directory to export book to')
        if not directory.isNull():
            dialog = DialogConvert(self, self.book, directory)
            dialog.exec_()


    def onHelpHomepage(self):
        services = QtGui.QDesktopServices()
        services.openUrl(QtCore.QUrl('http://foosoft.net/mangle'))


    def onHelpAbout(self):
        dialog = DialogAbout(self)
        dialog.exec_()


    def saveIfNeeded(self):
        if not self.book.modified:
            return True

        result = QtGui.QMessageBox.question(
            self,
            'Mangle',
            'Save changes to the current book?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel,
            QtGui.QMessageBox.Yes
        )

        return (
            result == QtGui.QMessageBox.No or
            result == QtGui.QMessageBox.Yes and self.saveBook()
        )


    def saveBook(self, browse=False):
        if self.book.title is None:
            QtGui.QMessageBox.warning(self, 'Mangle', 'You must specify a title for this book before saving')
            return False

        filename = self.book.filename
        if filename is None or browse:
            filename = QtGui.QFileDialog.getSaveFileName(
                parent=self,
                caption='Select a book file to save as',
                filter='Mangle files (*.mngl);;All files (*.*)'
            )
            if filename.isNull():
                return False
            filename = self.cleanupBookFile(filename)

        try:
            self.book.save(filename)
        except RuntimeError, error:
            QtGui.QMessageBox.critical(self, 'Mangle', str(error))
            return False

        return True


    def loadBook(self, filename):
        try:
            self.book.load(filename)
        except RuntimeError, error:
            QtGui.QMessageBox.critical(self, 'Mangle', str(error))
        else:
            self.listWidgetFiles.clear()
            for image in self.book.images:
                self.listWidgetFiles.addItem(image)


    def shiftImageFile(self, row, delta):
        validShift = (
            (delta > 0 and row < self.listWidgetFiles.count() - delta) or
            (delta < 0 and row >= abs(delta))
        )
        if not validShift:
            return

        item = self.listWidgetFiles.takeItem(row)

        self.listWidgetFiles.insertItem(row + delta, item)
        self.listWidgetFiles.setItemSelected(item, True)

        self.book.modified = True
        self.book.images[row], self.book.images[row + delta] = (
            self.book.images[row + delta], self.book.images[row]
        )


    def shiftImageFiles(self, delta):
        items = self.listWidgetFiles.selectedItems()
        rows = sorted([self.listWidgetFiles.row(item) for item in items])

        for row in rows if delta < 0 else reversed(rows):
            self.shiftImageFile(row, delta)


    def removeImageFiles(self):
        for item in self.listWidgetFiles.selectedItems():
            row = self.listWidgetFiles.row(item)
            self.listWidgetFiles.takeItem(row)
            self.book.images.remove(item.text())
            self.book.modified = True


    def addImageFiles(self, filenames):
        filenamesListed = []
        for i in xrange(0, self.listWidgetFiles.count()):
            filenamesListed.append(self.listWidgetFiles.item(i).text())

        for filename in natsorted(filenames):
            if filename not in filenamesListed:
                filename = QtCore.QString(filename)
                self.listWidgetFiles.addItem(filename)
                self.book.images.append(filename)
                self.book.modified = True

    def addImageDirs(self, directories):
        filenames = []

        for directory in directories:
            for root, _, subfiles in os.walk(unicode(directory)):
                for filename in subfiles:
                    path = os.path.join(root, filename)
                    if self.isImageFile(path):
                        filenames.append(path)

        self.addImageFiles(filenames)

    def addCBZFiles(self, filenames):
        directories = []
        tempDir = tempfile.gettempdir()
        filenames.sort()

        filenamesListed = []
        for i in xrange(0, self.listWidgetFiles.count()):
            filenamesListed.append(self.listWidgetFiles.item(i).text())

        for filename in filenames:
            folderName = os.path.splitext(basename(str(filename)))[0]
            path = tempDir + "/" + folderName + "/"
            cbzFile = ZipFile(str(filename))
            for f in cbzFile.namelist():
                if f.endswith('/'):
                    try:
                        os.makedirs(path + f)
                    except:
                        pass  # the dir exists so we are going to extract the images only.
                else:
                    cbzFile.extract(f, path)
            if os.path.isdir(unicode(path)):  # Add the directories
                directories.append(path)
        
        self.addImageDirs(directories)  # Add the files


    def isImageFile(self, filename):
        imageExts = ['.jpeg', '.jpg', '.gif', '.png']
        filename = unicode(filename)
        return (
            os.path.isfile(filename) and
            os.path.splitext(filename)[1].lower() in imageExts
        )

    def containsCbzFile(self, filenames):
        cbzExts = ['.cbz']
        for filename in filenames:
            filename = unicode(filename)
            result = (
            os.path.isfile(filename) and
            os.path.splitext(filename)[1].lower() in cbzExts
            )
            if result == True:
                return result
        return False     

    def cleanupBookFile(self, filename):
        if len(os.path.splitext(unicode(filename))[1]) == 0:
            filename += '.mngl'
        return filename

########NEW FILE########
__FILENAME__ = cbz
# Copyright (C) 2011  Marek Kubica <marek@xivilization.net>
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


import os.path
from zipfile import ZipFile, ZIP_STORED


class Archive(object):
    def __init__(self, path):
        outputDirectory = os.path.dirname(path)
        outputFileName = '%s.cbz' % os.path.basename(path)
        outputPath = os.path.join(outputDirectory, outputFileName)
        self.zipfile = ZipFile(outputPath, 'w', ZIP_STORED)


    def addFile(self, filename):
        arcname = os.path.basename(filename)
        self.zipfile.write(filename, arcname)


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


    def close(self):
        self.zipfile.close()

########NEW FILE########
__FILENAME__ = convert
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
import shutil

from PyQt4 import QtGui, QtCore
from image import ImageFlags

import cbz
import image
import pdfimage


class DialogConvert(QtGui.QProgressDialog):
    def __init__(self, parent, book, directory):
        QtGui.QProgressDialog.__init__(self)

        self.book = book
        self.bookPath = os.path.join(unicode(directory), unicode(self.book.title))

        self.timer = None
        self.setWindowTitle('Exporting book...')
        self.setMaximum(len(self.book.images))
        self.setValue(0)

        self.archive = None
        if 'CBZ' in self.book.outputFormat:
            self.archive = cbz.Archive(self.bookPath)
        
        self.pdf = None
        if "PDF" in self.book.outputFormat:
            self.pdf = pdfimage.PDFImage(self.bookPath, str(self.book.title), str(self.book.device))



    def showEvent(self, event):
        if self.timer is None:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.onTimer)
            self.timer.start(0)


    def hideEvent(self, event):
        """Called when the dialog finishes processing."""

        # Close the archive if we created a CBZ file
        if self.archive is not None:
            self.archive.close()
        # Close and generate the PDF File
        if self.pdf is not None:
            self.pdf.close()

        # Remove image directory if the user didn't wish for images
        if 'Image' not in self.book.outputFormat:
            shutil.rmtree(self.bookPath)


    def convertAndSave(self, source, target, device, flags, archive, pdf):
        image.convertImage(source, target, device, flags)
        if archive is not None:
            archive.addFile(target)
        if pdf is not None:
            pdf.addImage(target)

                
    def onTimer(self):
        index = self.value()
        target = os.path.join(self.bookPath, '%05d.png' % index)
        source = unicode(self.book.images[index])

        if index == 0:
            try:
                if not os.path.isdir(self.bookPath):
                    os.makedirs(self.bookPath)
            except OSError:
                QtGui.QMessageBox.critical(self, 'Mangle', 'Cannot create directory %s' % self.bookPath)
                self.close()
                return

            try:
                base = os.path.join(self.bookPath, unicode(self.book.title))

                mangaName = base + '.manga'
                if self.book.overwrite or not os.path.isfile(mangaName):
                    manga = open(mangaName, 'w')
                    manga.write('\x00')
                    manga.close()

                mangaSaveName = base + '.manga_save'
                if self.book.overwrite or not os.path.isfile(mangaSaveName):
                    mangaSave = open(base + '.manga_save', 'w')
                    saveData = u'LAST=/mnt/us/pictures/%s/%s' % (self.book.title, os.path.split(target)[1])
                    mangaSave.write(saveData.encode('utf-8'))
                    mangaSave.close()

            except IOError:
                QtGui.QMessageBox.critical(self, 'Mangle', 'Cannot write manga file(s) to directory %s' % self.bookPath)
                self.close()
                return False

        self.setLabelText('Processing %s...' % os.path.split(source)[1])

        try:
            if self.book.overwrite or not os.path.isfile(target):
                device = str(self.book.device)
                flags = self.book.imageFlags
                archive = self.archive
                pdf = self.pdf

                # For right page (if requested)
                if(self.book.imageFlags & ImageFlags.Split):
                    # New path based on modified index
                    target = os.path.join(self.bookPath, '%05d.png' % (index * 2 + 0))
                    self.convertAndSave(source, target, device, flags ^ ImageFlags.Split | ImageFlags.SplitRight, archive, pdf)
                    # Change target once again for left page
                    target = os.path.join(self.bookPath, '%05d.png' % (index * 2 + 1))

                # Convert page
                self.convertAndSave(source, target, device, flags, archive, pdf)

        except RuntimeError, error:
            result = QtGui.QMessageBox.critical(
                self,
                'Mangle',
                str(error),
                QtGui.QMessageBox.Abort | QtGui.QMessageBox.Ignore,
                QtGui.QMessageBox.Ignore
            )
            if result == QtGui.QMessageBox.Abort:
                self.close()
                return

        self.setValue(index + 1)

########NEW FILE########
__FILENAME__ = image
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

from PIL import Image, ImageDraw


class ImageFlags:
    Orient = 1 << 0
    Resize = 1 << 1
    Frame = 1 << 2
    Quantize = 1 << 3
    Stretch = 1 << 4
    Split = 1 << 5
    SplitRight = 1 << 6


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

    Profiles = {
        'Kindle 1': ((600, 800), Palette4),
        'Kindle 2': ((600, 800), Palette15a),
        'Kindle 3': ((600, 800), Palette15a),
        'Kindle 4': ((600, 800), Palette15b),
        'Kindle 5': ((600, 800), Palette15b),
        'Kindle DX': ((824, 1200), Palette15a),
        'Kindle DXG': ((824, 1200), Palette15a),
        'Kindle Touch': ((600, 800), Palette15a), 
        'Kindle Paperwhite': ((758, 1024), Palette15b) # resolution given in manual, see http://kindle.s3.amazonaws.com/Kindle_Paperwhite_Users_Guide.pdf
    }
    
    
def splitLeft(image):
    widthImg, heightImg = image.size
    
    return image.crop((0, 0, widthImg / 2, heightImg))


def splitRight(image):
    widthImg, heightImg = image.size
    
    return image.crop((widthImg / 2, 0, widthImg, heightImg))


def quantizeImage(image, palette):
    colors = len(palette) / 3
    if colors < 256:
        palette = palette + palette[:3] * (256 - colors)

    palImg = Image.new('P', (1, 1))
    palImg.putpalette(palette)

    return image.quantize(palette=palImg)


def stretchImage(image, size):
    widthDev, heightDev = size
    return image.resize((widthDev, heightDev), Image.ANTIALIAS)

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


def loadImage(source):
    try:
        return Image.open(source)
    except IOError:
        raise RuntimeError('Cannot read image file %s' % source)
    

def saveImage(image, target):
    try:
        image.save(target)
    except IOError:
        raise RuntimeError('Cannot write image file %s' % target)


def convertImage(source, target, device, flags):
    try:
        size, palette = KindleData.Profiles[device]
    except KeyError:
        raise RuntimeError('Unexpected output device %s' % device)
    # Load image from source path
    image = loadImage(source)
    # Format according to palette
    image = formatImage(image)
    # Apply flag transforms
    if flags & ImageFlags.SplitRight:
        image = splitRight(image)
    if flags & ImageFlags.Split:
        image = splitLeft(image)
    if flags & ImageFlags.Orient:
        image = orientImage(image, size)
    if flags & ImageFlags.Resize:
        image = resizeImage(image, size)
    if flags & ImageFlags.Stretch:
        image = stretchImage(image, size)
    if flags & ImageFlags.Frame:
        image = frameImage(image, tuple(palette[:3]), tuple(palette[-3:]), size)
    if flags & ImageFlags.Quantize:
        image = quantizeImage(image, palette)

    saveImage(image, target)

########NEW FILE########
__FILENAME__ = options
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


from PyQt4 import QtGui, uic

from image import ImageFlags
import util


class DialogOptions(QtGui.QDialog):
    def __init__(self, parent, book):
        QtGui.QDialog.__init__(self, parent)

        uic.loadUi(util.buildResPath('mangle/ui/options.ui'), self)
        self.accepted.connect(self.onAccept)

        self.book = book
        self.moveOptionsToDialog()


    def onAccept(self):
        self.moveDialogToOptions()


    def moveOptionsToDialog(self):
        self.lineEditTitle.setText(self.book.title or 'Untitled')
        self.comboBoxDevice.setCurrentIndex(max(self.comboBoxDevice.findText(self.book.device), 0))
        self.comboBoxFormat.setCurrentIndex(max(self.comboBoxFormat.findText(self.book.outputFormat), 0))
        self.checkboxOverwrite.setChecked(self.book.overwrite)
        self.checkboxOrient.setChecked(self.book.imageFlags & ImageFlags.Orient)
        self.checkboxResize.setChecked(self.book.imageFlags & ImageFlags.Resize)
        self.checkboxStretch.setChecked(self.book.imageFlags & ImageFlags.Stretch)
        self.checkboxQuantize.setChecked(self.book.imageFlags & ImageFlags.Quantize)
        self.checkboxFrame.setChecked(self.book.imageFlags & ImageFlags.Frame)


    def moveDialogToOptions(self):
        title = self.lineEditTitle.text()
        device = self.comboBoxDevice.currentText()
        outputFormat = self.comboBoxFormat.currentText()
        overwrite = self.checkboxOverwrite.isChecked()

        imageFlags = 0
        if self.checkboxOrient.isChecked():
            imageFlags |= ImageFlags.Orient
        if self.checkboxResize.isChecked():
            imageFlags |= ImageFlags.Resize
        if self.checkboxStretch.isChecked():
            imageFlags |= ImageFlags.Stretch
        if self.checkboxQuantize.isChecked():
            imageFlags |= ImageFlags.Quantize
        if self.checkboxFrame.isChecked():
            imageFlags |= ImageFlags.Frame
        if self.checkboxSplit.isChecked():
            imageFlags |= ImageFlags.Split

        modified = (
            self.book.title != title or
            self.book.device != device or
            self.book.overwrite != overwrite or
            self.book.imageFlags != imageFlags or
            self.book.outputFormat != outputFormat
        )

        if modified:
            self.book.modified = True
            self.book.title = title
            self.book.device = device
            self.book.overwrite = overwrite
            self.book.imageFlags = imageFlags
            self.book.outputFormat = outputFormat

########NEW FILE########
__FILENAME__ = pdfimage
# Copyright (C) 2012  Cristian Lizana <cristian@lizana.in>
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


import os.path

from reportlab.pdfgen import canvas

from image import KindleData


class PDFImage(object):
    def __init__(self, path, title, device):
        outputDirectory = os.path.dirname(path)
        outputFileName = '%s.pdf' % os.path.basename(path)
        outputPath = os.path.join(outputDirectory, outputFileName)
        self.currentDevice = device
        self.bookTitle = title
        self.pageSize = KindleData.Profiles[self.currentDevice][0]
        # pagesize could be letter or A4 for standarization but we need to control some image sizes
        self.canvas = canvas.Canvas(outputPath, pagesize=self.pageSize)
        self.canvas.setAuthor("Mangle")
        self.canvas.setTitle(self.bookTitle)
        self.canvas.setSubject("Created for " + self.currentDevice)


    def addImage(self, filename):
        self.canvas.drawImage(filename, 0, 0, width=self.pageSize[0], height=self.pageSize[1], preserveAspectRatio=True, anchor='c')
        self.canvas.showPage()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.canvas.save()

########NEW FILE########
__FILENAME__ = util
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


import os.path
import sys


def buildResPath(relative):
    directory = os.path.dirname(os.path.realpath(sys.argv[0]))
    return os.path.join(directory, relative)

########NEW FILE########
