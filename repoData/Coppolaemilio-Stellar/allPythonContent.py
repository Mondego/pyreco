__FILENAME__ = Stellar
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2014 Emilio Coppola
#
# This file is part of Stellar.
#
# Stellar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stellar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stellar.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, subprocess
from PyQt4 import QtGui, QtCore
sys.path.append("tools")
import treeview
import toolbar

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.projectdir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'example')
        self.eeldir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'eel','eel')
        if sys.platform == "win32":
            self.eeldir += '.exe'

        self.treeView = treeview.TreeView(self)

        self.output = QtGui.QTextEdit()
        self.output.setReadOnly(True)
        self.font = QtGui.QFont()
        self.font.setFamily('Monaco')
        self.font.setStyleHint(QtGui.QFont.Monospace)
        self.font.setFixedPitch(True)
        self.output.setFont(self.font)

        self.mdi = QtGui.QMdiArea()
        self.mdi.setViewMode(self.mdi.TabbedView)
        self.mdi.setTabsClosable(True)
        self.mdi.setTabsMovable(True)
        backf = QtGui.QBrush(QtGui.QPixmap(os.path.join('images','background.png')))
        self.mdi.setBackground(backf)

        self.toolBar = self.addToolBar(toolbar.ToolBar(self))

        self.statusBar().showMessage('Ready', 2000)

        self.vsplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.vsplitter.addWidget(self.mdi)
        self.vsplitter.addWidget(self.output)
        self.output.hide()
        self.c_displayed=False
        splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.treeView)
        splitter.addWidget(self.vsplitter)

        self.setCentralWidget(splitter)
        self.setWindowTitle("Stellar - " + os.path.basename(self.projectdir))
        self.resize(640, 480)

        self.show()

def main():
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join('images','icon.png')))
    app.setStyle(QtGui.QStyleFactory.create("plastique"))
    f = open(os.path.join('themes','default.css'))
    style = f.read()
    f.close()
    app.setStyleSheet(style)
    mw = MainWindow()
    mw.raise_() #Making the window get focused on OSX
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()    

########NEW FILE########
__FILENAME__ = docreader
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2014 Emilio Coppola
#
# This file is part of Stellar.
#
# Stellar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stellar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stellar.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore, QtGui, QtWebKit
import os, sys
from PyQt4.QtGui import QFont

if sys.version_info.major == 2:
    str = unicode    

class DocReader(QtGui.QDialog):
    def __init__(self, main):
        super(DocReader, self).__init__(main)
        self.main = main

        if os.path.exists(os.path.join('..','images')):
        	img_path=os.path.join('..','images')
        else:
        	img_path=os.path.join('images')

        self.toolbar = QtGui.QToolBar('Documentation Toolbar')


        self.ContainerGrid = QtGui.QGridLayout(self)
        self.ContainerGrid.setMargin (0)
        self.ContainerGrid.setSpacing(0)

        self.webkit = QtWebKit.QWebView()

        self.ContainerGrid.addWidget(self.toolbar)
        self.ContainerGrid.addWidget(self.webkit)

        self.setLayout(self.ContainerGrid)

        url = "docs/index.html"
        self.webkit.load(QtCore.QUrl(url))
        self.webkit.show()

class Editor(QtGui.QMainWindow):
    def __init__(self):
        super(Editor, self).__init__()
        target="none"
        pathtofile="stellar.png"

        self.ShowFrame = QtGui.QFrame()
        self.showlayout = QtGui.QGridLayout()
        self.showlayout.setMargin(0)

        self.docreader = DocReader(self, target, pathtofile)

        self.showlayout.addWidget(self.docreader)
        self.ShowFrame.setLayout(self.showlayout)

        self.setCentralWidget(self.ShowFrame)
        self.setWindowTitle("Stellar - DocReader")
        self.resize(640, 480)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    mainWin = Editor()
    mainWin.show()
    mainWin.raise_() #Making the window get focused on OSX
    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = imageviewer
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2014 Emilio Coppola
#
# This file is part of Stellar.
#
# Stellar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stellar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stellar.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore, QtGui
import os, sys
from PyQt4.QtGui import QFont

if sys.version_info.major == 2:
    str = unicode    

class ImageEditor(QtGui.QDialog):
    def __init__(self, main, name, filename):
        super(ImageEditor, self).__init__(main)
        self.main = main
        self.filename = filename

        if os.path.exists(os.path.join('..','images')):
        	img_path=os.path.join('..','images')
        else:
        	img_path=os.path.join('images')

        self.fitToWindowAct = QtGui.QAction("&Fit to Window", self,
                enabled=False, checkable=True, shortcut="Ctrl+F",
                triggered=self.fitToWindow)
        self.zoomInAct = QtGui.QAction("Zoom &In (25%)", self,
                shortcut="Ctrl++", enabled=True, triggered=self.zoomIn)

        self.zoomOutAct = QtGui.QAction("Zoom &Out (25%)", self,
                shortcut="Ctrl+-", enabled=True, triggered=self.zoomOut)

        self.normalSizeAct = QtGui.QAction("&Normal Size", self,
                shortcut="Ctrl+S", enabled=True, triggered=self.normalSize)

        saveAction = QtGui.QAction(QtGui.QIcon(os.path.join(img_path, 'save.png')), 'Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect(self.save_file)
        self.toolbar = QtGui.QToolBar('Image Toolbar')
        self.toolbar.setIconSize(QtCore.QSize(16, 16))
        self.toolbar.addAction(self.zoomInAct)
        self.toolbar.addAction(self.zoomOutAct)
        self.toolbar.addAction(self.normalSizeAct)

        self.ContainerGrid = QtGui.QGridLayout(self)
        self.ContainerGrid.setMargin (0)
        self.ContainerGrid.setSpacing(0)

        self.imageLabel = QtGui.QLabel()
        self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.imageLabel.setStyleSheet('background-image: url(../images/transparent.png);')
        self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored,
                QtGui.QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)
        self.open_image(filename)

        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setBackgroundRole(QtGui.QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)

        self.ContainerGrid.addWidget(self.toolbar)
        self.ContainerGrid.addWidget(self.scrollArea)

        self.setLayout(self.ContainerGrid)


    def open_image(self, filename):
        fileName = filename
        if fileName:
            image = QtGui.QImage(fileName)
            if image.isNull():
                QtGui.QMessageBox.information(self, "Image Viewer",
                        "Cannot load %s." % fileName)
                return

            self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(image))
            self.scaleFactor = 1.0

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

        #self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        #self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 10.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.1)

    def save_file(self):
        with open(self.filename, 'w') as f:
            f.write(self.textedit.toPlainText())
        self.main.statusBar().showMessage(os.path.basename(str(self.filename))+' saved!', 2000)

class Editor(QtGui.QMainWindow):
    def __init__(self):
        super(Editor, self).__init__()
        target="none"
        pathtofile="stellar.png"

        self.ShowFrame = QtGui.QFrame()
        self.showlayout = QtGui.QGridLayout()
        self.showlayout.setMargin(0)

        self.textedit = ImageEditor(self, target, pathtofile)

        self.showlayout.addWidget(self.textedit)
        self.ShowFrame.setLayout(self.showlayout)

        self.setCentralWidget(self.ShowFrame)
        self.setWindowTitle("Stellar - TImageEditor")
        self.resize(640, 480)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    mainWin = Editor()
    mainWin.show()
    mainWin.raise_() #Making the window get focused on OSX
    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = scripteditor
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2014 Emilio Coppola
#
# This file is part of Stellar.
#
# Stellar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stellar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stellar.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore, QtGui
import os, sys
from PyQt4.QtGui import QFont

if sys.version_info.major == 2:
    str = unicode    
class Highlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(Highlighter, self).__init__(parent)
        
        self.color_0 = QtGui.QColor(249, 38,  144)
        self.color_1 = QtGui.QColor(102, 217, 239)
        self.color_2 = QtGui.QColor(117, 113, 94 )#comments
        self.color_3 = QtGui.QColor(230, 219, 102)
        self.color_4 = QtGui.QColor(166,226,46)
        self.color_5 = QtGui.QColor(174,129,255)
        self.color_6 = QtGui.QColor(253,151,32)

        group1Format = QtGui.QTextCharFormat()
        group1Format.setForeground(self.color_0)
        group1Patterns = ["\\bimport\\b", '\\bif\\b', '\\belse\\b',
                          "\\bfor\\b", "\\bswitch\\b" , "\\bcase\\b",
                          "\\bbreak\\b", "\\breturn\\b", "\\bwhile\\b",
                          "\\blocal\\b"]

        self.highlightingRules = [(QtCore.QRegExp(pattern), group1Format)
                for pattern in group1Patterns]


        keywordFormat = QtGui.QTextCharFormat()
        keywordFormat.setForeground(self.color_1)
        keywordPatterns = ["\\bchar\\b", "\\bclass\\b", "\\bconst\\b",
                "\\bdouble\\b", "\\benum\\b", "\\bexplicit\\b", "\\bfriend\\b",
                "\\binline\\b", "\\bint\\b", "\\blong\\b", "\\bnamespace\\b",
                "\\boperator\\b", "\\bprivate\\b", "\\bprotected\\b",
                "\\bpublic\\b", "\\bshort\\b", "\\bsignals\\b", "\\bsigned\\b",
                "\\bslots\\b", "\\bstatic\\b", "\\bstruct\\b",
                "\\btemplate\\b", "\\btypedef\\b", "\\btypename\\b",
                "\\bunion\\b", "\\bunsigned\\b", "\\bvirtual\\b", "\\bvoid\\b",
                "\\bvolatile\\b"]

        self.highlightingRules += [(QtCore.QRegExp(pattern), keywordFormat)
                for pattern in keywordPatterns]

        classFormat = QtGui.QTextCharFormat()
        classFormat.setForeground(self.color_4)
        self.highlightingRules.append((QtCore.QRegExp("\\bQ[A-Za-z]+\\b"),
                classFormat))

        numberFormat = QtGui.QTextCharFormat()
        numberFormat.setForeground(self.color_5)
        numberPatterns = ['\\b[+-]?[0-9]+[lL]?\\b', '\\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\\b',
        '\\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\\b', '\\btrue\\b', '\\bfalse\\b']
        self.highlightingRules += [(QtCore.QRegExp(pattern), numberFormat)
                for pattern in numberPatterns]

        singleLineCommentFormat = QtGui.QTextCharFormat()
        singleLineCommentFormat.setForeground(self.color_2)
        self.highlightingRules.append((QtCore.QRegExp("//[^\n]*"),
                singleLineCommentFormat))

        self.multiLineCommentFormat = QtGui.QTextCharFormat()
        self.multiLineCommentFormat.setForeground(self.color_2)

        quotationFormat = QtGui.QTextCharFormat()
        quotationFormat.setForeground(self.color_3)
        self.highlightingRules.append((QtCore.QRegExp("\".*\""),
                quotationFormat))

        functionFormat = QtGui.QTextCharFormat()
        functionFormat.setForeground(self.color_1)
        self.highlightingRules.append((QtCore.QRegExp("\\b[A-Za-z0-9_]+(?=\\()"),
                functionFormat))

        self.commentStartExpression = QtCore.QRegExp("/\\*")
        self.commentEndExpression = QtCore.QRegExp("\\*/")

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)

        while startIndex >= 0:
            endIndex = self.commentEndExpression.indexIn(text, startIndex)

            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + self.commentEndExpression.matchedLength()

            self.setFormat(startIndex, commentLength,
                    self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text,
                    startIndex + commentLength);

class ScriptEditor(QtGui.QDialog):
    def __init__(self, main, name, filename):
        super(ScriptEditor, self).__init__(main)
        self.main = main
        self.filename = filename
        self.title = filename

        if os.path.exists(os.path.join('..','images')):
        	img_path=os.path.join('..','images')
        else:
        	img_path=os.path.join('images')

        saveAction = QtGui.QAction(QtGui.QIcon(os.path.join(img_path, 'save.png')), 'Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect(self.save_file)

        importAction = QtGui.QAction(QtGui.QIcon(os.path.join(img_path, 'open.png')), 'Import', self)
        importAction.triggered.connect(self.import_file)

        tabAction = QtGui.QAction(QtGui.QIcon(os.path.join(img_path, 'open.png')), 'Tab', self)
        tabAction.triggered.connect(self.handleTest)

        fontAction = QtGui.QAction(QtGui.QIcon(os.path.join(img_path, 'font.png')), 'Font', self)
        fontAction.triggered.connect(self.fontChange)

        self.toolbar = QtGui.QToolBar('Script Toolbar')
        self.toolbar.setIconSize(QtCore.QSize(16, 16))
        self.toolbar.addAction(saveAction)
        self.toolbar.addAction(importAction)
        self.toolbar.addAction(tabAction)
        self.toolbar.addAction(fontAction)

        with open(filename, 'r') as content_file:
            self.content = content_file.read()
        
        self.font = QtGui.QFont()
        self.font.setFamily('ClearSans')
        self.font.setStyleHint(QtGui.QFont.Monospace)
        self.font.setFixedPitch(True)
        self.font.setPointSize(int(13))

        self.ContainerGrid = QtGui.QGridLayout(self)
        self.ContainerGrid.setMargin (0)
        self.ContainerGrid.setSpacing(0)

        self.textedit = QtGui.QTextEdit()
        self.textedit.setTabStopWidth(40)
        self.textedit.insertPlainText(self.content)
        self.textedit.moveCursor(QtGui.QTextCursor.Start)
        self.textedit.setLineWrapMode(0)
        self.textedit.setFont(self.font)

        self.linenumbers=QtGui.QTextEdit()
        numbers= 999
        for number in range(numbers):
            self.linenumbers.insertPlainText(str(number+1)+'\n')
        self.linenumbers.setFont(self.font)
        self.linenumbers.verticalScrollBar().setValue( 0) #FIXME
        self.textedit.verticalScrollBar().valueChanged.connect(
            self.linenumbers.verticalScrollBar().setValue)
        self.linenumbers.verticalScrollBar().valueChanged.connect(
            self.textedit.verticalScrollBar().value)
        self.linenumbers.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.linenumbers.setReadOnly (True)
        self.linenumbers.moveCursor(QtGui.QTextCursor.Start)
        self.linenumbers.setStyleSheet("color:rgb(117, 113, 94)")
        self.linenumbers.setTextColor(QtGui.QColor(117, 113, 94 ))

        self.widget = QtGui.QWidget()
        self.layout=QtGui.QHBoxLayout(self.widget)
        self.layout.addWidget(self.linenumbers)
        self.layout.addWidget(self.textedit)
        self.layout.setContentsMargins(0,0,0,0)
        self.linenumbers.setMaximumWidth(38)

        self.ContainerGrid.addWidget(self.toolbar)
        self.ContainerGrid.addWidget(self.widget)

        self.setLayout(self.ContainerGrid)

        self.highlighter = Highlighter(self.textedit.document())

    def handleTest(self):
        tab = "\t"
        cursor = self.textedit.textCursor()

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(end)
        cursor.movePosition(cursor.EndOfLine)
        end = cursor.position()

        cursor.setPosition(start)
        cursor.movePosition(cursor.StartOfLine)
        start = cursor.position()
        print cursor.position(), end

        while cursor.position() < end:
            cursor.movePosition(cursor.StartOfLine)
            cursor.insertText(tab)
            end += tab.count(end)
            cursor.movePosition(cursor.EndOfLine)

    def save_file(self):
        with open(self.filename, 'w') as f:
            f.write(self.textedit.toPlainText())
        self.main.statusBar().showMessage(os.path.basename(str(self.filename))+' saved!', 2000)

    def import_file(self):
        target = str(QtGui.QFileDialog.getOpenFileName(self, "Select File"))
        with open(target, 'r') as f:
            self.textedit.setText(f.read())
        self.main.statusBar().showMessage(str(target)+' Imported!', 2000)

    def fontChange(self):
        font, ok = QtGui.QFontDialog.getFont(self.font)
        if ok:
            self.textedit.setFont(font)

class Editor(QtGui.QMainWindow):
    def __init__(self):
        super(Editor, self).__init__()
        target="none"
        pathtofile="scripteditor.py"

        self.ShowFrame = QtGui.QFrame()
        self.showlayout = QtGui.QGridLayout()
        self.showlayout.setMargin(0)

        self.textedit = ScriptEditor(self, target, pathtofile)

        self.showlayout.addWidget(self.textedit)
        self.ShowFrame.setLayout(self.showlayout)

        self.setCentralWidget(self.ShowFrame)
        self.setWindowTitle("TextEditor - " + self.textedit.title )
        self.resize(640, 480)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    f = open('../themes/default.css')
    style = f.read()
    f.close()
    app.setStyleSheet(style)
    app.setStyle(QtGui.QStyleFactory.create("plastique"))
    mainWin = Editor()
    mainWin.show()
    mainWin.raise_() #Making the window get focused on OSX
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = toolbar
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2014 Emilio Coppola
#
# This file is part of Stellar.
#
# Stellar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stellar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stellar.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore, QtGui
import os, sys, subprocess
import docreader


class ToolBar(QtGui.QToolBar):
    def __init__(self, main):
        super(ToolBar, self).__init__(main)
        self.main = main

        # func, img, title, hotkey
        funcs = [[self.open_folder, 'stellar_1.png', 'Stellar', False], 
                [self.open_folder, 'open.png', 'Open', False],
                [self.run_project, 'run.png', 'Run', 'Ctrl+B'],
                [self.main.treeView.add_file, 'addfile.png', 'Add file', False],
                [self.main.treeView.add_directory, 'addfolder.png', 'Add folder', False],
                [QtGui.qApp.quit, 'close.png', 'Exit', 'Ctrl+Q'],
                [self.open_documentation, 'documentation.png', 'Documentation', 'F1'],
                [self.toggle_console, 'output.png', 'Show output', False]]

        for i,x in enumerate(funcs):
            action = QtGui.QAction(QtGui.QIcon(os.path.join('images', x[1])), x[2], self)
            action.triggered.connect(x[0])
            if x[3]!=False:
                action.setShortcut(x[3])
            self.addAction(action)
            if i == 5:
                spacer = QtGui.QWidget() 
                spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding) 
                self.addWidget(spacer)


        self.setMovable(False) 


    def toggle_console(self):
        self.main.c_displayed = not self.main.c_displayed
        self.main.output.setVisible(self.main.c_displayed)

    def open_folder(self):
        target = str(QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))
        if target:
            self.root = self.main.treeView.fileSystemModel.setRootPath(target)
            self.main.treeView.setRootIndex(self.root)
            self.main.projectdir = target

    def open_documentation(self):
        self.w = docreader.DocReader(self.main)
        self.w.setWindowTitle("Documentation")
        self.w.setGeometry(QtCore.QRect(100, 100, 400, 200))
        self.w.show()

    def run_project(self):
        self.main.statusBar().showMessage('Running project...', 2000)
        eel = self.main.eeldir
        f = 'main'
        os.chdir(self.main.projectdir)
        args = [eel, f]
        if sys.platform=="win32":
            eelbox = subprocess.Popen([eel, f], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out = eelbox.stdout.read()
            self.main.output.setText(out)
            self.main.output.moveCursor(QtGui.QTextCursor.End)
            self.main.statusBar().showMessage('Done!', 2000)

########NEW FILE########
__FILENAME__ = treeview
#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2014 Emilio Coppola
#
# This file is part of Stellar.
#
# Stellar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Stellar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Stellar.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore, QtGui
import os, sys, shutil
import scripteditor
import imageviewer

class TreeView(QtGui.QTreeView):
    def __init__(self, main):
        super(TreeView, self).__init__(main)
        self.main = main
        self.fileSystemModel = QtGui.QFileSystemModel(self)
        self.fileSystemModel.setReadOnly(False)
        self.clicked.connect(self.on_treeView_clicked)
        self.abstractitem = QtGui.QAbstractItemView
        self.setDragDropMode(self.abstractitem.InternalMove)
        self.connect (self,
                QtCore.SIGNAL ("currentTextChanged(const QString&)"),
                QtGui.qApp.quit)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.root = self.fileSystemModel.setRootPath(self.main.projectdir)
        self.setModel(self.fileSystemModel)
        self.setRootIndex(self.root)
        self.setColumnHidden(1, True)
        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)
        self.header().close()  
        self.indexItem=""
        self.connect(self,QtCore.SIGNAL('customContextMenuRequested(QPoint)'), self.doMenu)

        renameAction = QtGui.QAction('Rename', self)
        renameAction.triggered.connect(self.rename_file)

        self.deleteFileAction = QtGui.QAction('Delete', self)
        self.editFileAction = QtGui.QAction('Edit', self)

        self.deleteFileAction.triggered.connect(self.delete_file)
        self.editFileAction.triggered.connect(self.edit_file)

        self.popMenu = QtGui.QMenu()
        self.popMenu.addAction(self.editFileAction)
        self.popMenu.addAction(renameAction)
        self.popMenu.addAction(self.deleteFileAction)
        self.popMenu.addSeparator()

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def on_treeView_clicked(self, index):
        self.indexItem = self.fileSystemModel.index(index.row(), 0, index.parent())
        filePath = self.fileSystemModel.filePath(self.indexItem)
        fileName = self.fileSystemModel.fileName(self.indexItem)

    def doMenu(self, point):
        target=self.fileSystemModel.filePath(self.indexItem)
        if os.path.isdir(target):
            self.deleteFileAction.setText("Delete Folder")
        else:
            self.deleteFileAction.setText("Delete File")
        self.popMenu.exec_( self.mapToGlobal(point) )

    def edit(self, index, trigger, event):
        if trigger == QtGui.QAbstractItemView.DoubleClicked:
            self.edit_file()
            return False
        return QtGui.QTreeView.edit(self, index, trigger, event)

    def edit_file(self):
        target=str(self.abstractitem.currentIndex(self.main.treeView).data().toString())
        filePath = self.fileSystemModel.filePath(self.indexItem)
        sufix = filePath[-4:]

        if sufix == ".exe":
            reply = QtGui.QMessageBox.question(self, "Not assigned", 
                         "Stellar does not have a progam to edit this kind of file, would you like to choose one?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)            
        if sufix in [".png", ".jpg", ".bmp"]:
            self.main.window = imageviewer.ImageEditor(self.main, target, filePath)
            self.main.window.setWindowTitle(target)
            self.main.mdi.addSubWindow(self.main.window)
            self.main.window.setVisible(True)
        else:
            self.main.window = scripteditor.ScriptEditor(self.main, target, filePath)
            self.main.window.setWindowTitle(os.path.basename(str(self.main.window.title)))
            self.main.mdi.addSubWindow(self.main.window)
            self.main.window.setVisible(True)

    def delete_file(self):
        f = filePath = self.fileSystemModel.filePath(self.indexItem)
        if os.path.isdir(f):
            delete_msg = "Delete folder "+f+"?"
        else:
            delete_msg = "Delete file "+f+" Continue?"
        
        reply = QtGui.QMessageBox.warning(self, 'Confirm', 
                         delete_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            try:
                os.remove(str(f))
            except:
                self.delete_folder(f)
                
    def delete_folder(self, f):
        try:
            os.rmdir(str(f))
        except:
            shutil.rmtree(str(f))

    def add_file(self):
        with open(os.path.join(self.main.projectdir, "NewFile"), 'w') as f:
            f.write("")

    def add_directory(self):
        directory = os.path.join(self.main.projectdir, "NewDirectory")
        if not os.path.exists(directory):
            os.makedirs(directory)

    def rename_file(self):
        index = self.abstractitem.currentIndex(self.main.treeView)
        return QtGui.QTreeView.edit(self, index)

########NEW FILE########
