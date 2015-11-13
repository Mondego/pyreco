__FILENAME__ = play_wav_in_sys_call
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
play audio via system call

Tested environment:
    Mac OS X 10.6.8
    Linux 3.0 KDE 4.6.5

alsa-utils: /usr/bin/aplay
"""
import os
import threading
import subprocess
import sys


if sys.platform == "darwin":
    player_name = "afplay"
elif sys.platform == "linux2":
    player_name = "aplay"


def _play_audio_t(path):
    path = os.path.realpath(path)

    if sys.platform == "darwin":
        cmd = '%s -q 1 "%s"' % (player_name, path)
    elif sys.platform == "linux2":    
        cmd = '%s "%s"' % (player_name, path)

    os.system(cmd)

def play_audio_t(path):
    t = threading.Thread(target = _play_audio_t, kwargs = {"path" : path})
    t.start()

def play_audio_p(path):
    path = os.path.realpath(path)
    subprocess.call([player_name, path])


if __name__ == "__main__":
#    path = 'if_you_go_away.mp3'
#    play_audio_t(path)

#    path = 'wow.wav'
#    play_audio_p(path)

    from timeit import Timer

    t = Timer("play_audio_p('wow.wav')", "from __main__ import play_audio_p")
    print t.timeit(number=3)

    t = Timer("play_audio_t('wow.wav')", "from __main__ import play_audio_t")
    print t.timeit(number=3)

########NEW FILE########
__FILENAME__ = clipboard
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
clipboard demo

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qclipboard.html    
"""
import platform
import sys
import time

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


def get_platform_name():
    name = None
    while not name:
        try:
            return platform.system()
        except IOError:
            time.sleep(0.1)


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

#        if get_platform_name() == "Darwin":
#            self.setAttribute(QtCore.Qt.WA_MacBrushedMetal, True)


    def show_and_raise(self):
        self.show()
        self.raise_()

    def keyPressEvent(self, evt):
        key = evt.key()
        modifier = evt.modifiers()

        IS_PASTE = (modifier == QtCore.Qt.ControlModifier and key == QtCore.Qt.Key_V)
        if IS_PASTE:
            print 'is_paste'

            clipboard = QtGui.QApplication.clipboard()
            mime_data = clipboard.mimeData()

            print "urls:", [i.toLocalFile() for i in mime_data.urls()]
            print "text:", mime_data.text()
            print "html:", mime_data.html()            

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = flat_button
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
flat button

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qpushbutton.html#flat-prop
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.btn = QtGui.QPushButton("Flat button", self)
        self.btn.setFlat(True)
        self.btn.clicked.connect(self._btn_cb)

    def _btn_cb(self):
        print "clicked"


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = push_button
#!/usr/bin/env python
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class DemoBtn(QtGui.QWidget):
    def __init__(self):
        super(DemoBtn, self).__init__()
        
        x, y, w, h = 500, 200, 120, 50
        self.setGeometry(x, y, w, h)
        
        x, y, w, h = 10, 10, 96, 32
        btn = QtGui.QPushButton("Push button", self)
        btn.setGeometry(x, y, w, h)
        btn.clicked.connect(self._btn_cb)

    def _btn_cb(self):
        print "clicked"

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    demo = DemoBtn()
    demo.show()
    sys.exit(app.exec_())
    
########NEW FILE########
__FILENAME__ = toggle_button
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
demo template

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.toggle_btn = QtGui.QPushButton("Toggle button", self)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.move(100, 100)
        self.toggle_btn.clicked.connect(self._toggle_btn_cb)

    def _toggle_btn_cb(self):
        print "is checked:", self.toggle_btn.isChecked()

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = tool_button
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QToolButton demo

NOTE: you should set a icon for QToolButton

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qtoolbutton.html
"""
import sys
import qcommons

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        qcommons.config_theme_path()

        tool_btn = QtGui.QToolButton(self)
        icon = QtGui.QIcon.fromTheme("edit-find")
        tool_btn.setIcon(icon)
        # the right size for tool button
        # "Choosing the Right Size and Format for Icons: Standard icon sizes for Windows Vista, Windows 7, Mac OS X, Linux GNOME and iPhone"
        # http://www.visualpharm.com/articles/icon_sizes.html
        tool_btn.setIconSize(32, 32)
        tool_btn.move(100, 100)
        tool_btn.clicked.connect(self._tool_btn_cb)

    def _tool_btn_cb(self):
        print 'clicked'

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = calendar
#!/usr/bin/python
# -*- coding: utf-8 -*-

# calendar.py

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()
        
        self.initUI()
        
    def initUI(self):

        self.cal = QtGui.QCalendarWidget(self)
        self.cal.setGridVisible(True)
        self.cal.move(20, 20)
        self.connect(self.cal, QtCore.SIGNAL('selectionChanged()'), 
            self.showDate)

        
        self.label = QtGui.QLabel(self)
        date = self.cal.selectedDate()
        self.label.setText(str(date.toPyDate()))
        self.label.move(130, 260)
        
        self.setWindowTitle('Calendar')  
        self.setGeometry(300, 300, 350, 300)
                
    def showDate(self):
      
        date = self.cal.selectedDate()
        self.label.setText(str(date.toPyDate()))


if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    ex = Example()
    ex.show()
    app.exec_()

########NEW FILE########
__FILENAME__ = checkbox
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QCheckBox demo

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qcheckbox.html
http://doc.qt.nokia.com/latest/qabstractbutton.html
http://doc.qt.nokia.com/latest/qt.html#CheckState-enum
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self._checkbox = QtGui.QCheckBox("CheckBox", self)
        self._checkbox.move(10, 10)
        self._checkbox.stateChanged.connect(self._checkbox_cb)

    def _checkbox_cb(self, state):
        assert QtCore.Qt.Unchecked == 0
        assert QtCore.Qt.Checked == 2
        assert state in (QtCore.Qt.Checked, QtCore.Qt.Unchecked, QtCore.Qt.PartiallyChecked)
        
        print "state:", state


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = combobox
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QComboBox

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QComboBox.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        combo = QtGui.QComboBox(self)
        combo.move(20, 20)

        combo.currentIndexChanged.connect(self._cb_currentIndexChanged)
        combo.highlighted.connect(self._cb_highlighted)

        items = ('', 'Lisp', 'C', 'Objective-C', 'Python', 'Java')
        combo.addItems(items)

    def _cb_currentIndexChanged(self, idx):
        print 'current selected index:', idx

    def _cb_highlighted(self, idx):
        print 'highlighted index:', idx

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())




########NEW FILE########
__FILENAME__ = custom_combobox_item
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
custom the item of QComboBox

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qcombobox.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QComboBox.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        
        self.combo = QtGui.QComboBox(self)
        self.combo.resize(200, 30)
        self.combo.move(20, 60)

        self.combo.currentIndexChanged.connect(self._combo_currentIndexChanged)

        self.items = (
            '',
            ('Lisp', 'lisp.png', 'llll'),
            ('C', 'c.png', 'cccc'),
            ('Objective-C', 'objc.png', 'oooo'),
            ('Python', 'python.png', 'pppp'),
            ('Java', 'java.png', 'jjjj'),
            )
        for i in self.items:
            if isinstance(i, tuple):
                text, icon_path, user_data = i[0], i[1], i[2]
                self.combo.addItem(QtGui.QIcon(icon_path), text, user_data)
                # or
                # self.combo.addItem(text, user_data)
            else:
                self.combo.addItem(i)


    def _combo_currentIndexChanged(self, idx):
        activated_idx = idx

        if idx == -1:
            return
        
        item = self.items[idx]
        if not item:
            return
        
        text, icon_path, user_data = item[0], item[1], item[2]

        matched_idx = self.combo.findData(user_data)
        assert activated_idx == matched_idx

        print
        print "text:", text
        print "icon path:", icon_path
        print "user_data:", user_data


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())




########NEW FILE########
__FILENAME__ = find_item_by_typing
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
find item of QComboBox by typing keyword

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QComboBox.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        
        self.combo = QtGui.QComboBox(self)
        self.combo.resize(200, 30)
        self.combo.move(20, 60)

        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.combo.currentIndexChanged.connect(self._combo_currentIndexChanged)

        self.items = (
            '',
            ('Lisp', 'lisp.png', 'llll'),
            ('C', 'c.png', 'cccc'),
            ('Objective-C', 'objc.png', 'oooo'),
            ('Python', 'python.png', 'pppp'),
            ('Java', 'java.png', 'jjjj'),
            )
        for i in self.items:
            if isinstance(i, tuple):
                fullname, icon_path, user_data = i[0], i[1], i[2]
                text = fullname
                self.combo.addItem(QtGui.QIcon(icon_path), text, user_data)
            else:
                self.combo.addItem(i)

        print self.combo.itemData(0)
        print self.combo.itemData(1)
        print self.combo.itemData(2)

    def _combo_currentIndexChanged(self, idx):
        activated_idx = idx

        if idx == -1:
            return
        
        item = self.items[idx]
        if not item:
            return
        
        text, icon_path, user_data = item[0], item[1], item[2]

        matched_idx = self.combo.findData(user_data)
        assert activated_idx == matched_idx

        print
        print "text:", text
        print "icon path:", icon_path
        print "user_data:", user_data


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = build_in_dialogs
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Build-in dialogs demo

# NOTE: 'title' is invalid on Mac OS X 10.6.* .

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QMessageBox.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


def popup_confirm(parent, msg = None):
    title = "TIPS"
    reply = QtGui.QMessageBox.question(parent, title,
                 msg,
                 QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
    if reply == QtGui.QMessageBox.Yes:
        return True
    else:
        return False

def popup_warning(parent, msg):
    title = "WARNING"
    QtGui.QMessageBox.warning(parent, title, msg, QtGui.QMessageBox.Close)

def popup_error(parent, msg):
    title = "ERROR"
    QtGui.QMessageBox.critical(parent, title, msg, QtGui.QMessageBox.Close)

def popup_about(parent, msg):
    """ This build-in dialog is suck, you should not use it. """
    title = "ABOUT"
    QtGui.QMessageBox.about(parent, title, msg)


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.show_and_raise()

        resp = popup_confirm(self, 'a')
        print 'resp:', resp

        popup_warning(self, 'warning message')

        popup_error(self, 'error message')

        popup_about(self, 'about message: <br />hello PyQt/PySide')

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = custom_simple_dialog
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom simple dialog

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


default_settings = {
    "confirm" : True,
    "x_action_is_quit" : 0,
}


class QuitConfirmDlg(QtGui.QDialog):
    def __init__(self, parent, settings):
        super(QuitConfirmDlg, self).__init__(parent)

        self.resize(400, 250)

        self._settings = settings
        self.setModal(True)

        self.tips_label = QtGui.QLabel("When you click the close button should me:", self)
        self.tips_label.setGeometry(QtCore.QRect(40, 40, 280, 15))

        self.minimize_rbtn = QtGui.QRadioButton("Minimize to system tray", self)
        self.minimize_rbtn.setGeometry(QtCore.QRect(70, 90, 180, 20))

        self.exit_rbtn = QtGui.QRadioButton("Exit program", self)
        self.exit_rbtn.setGeometry(QtCore.QRect(70, 120, 110, 20))

        self.no_confirm_cbox = QtGui.QCheckBox("Don't ask me again", self)
        self.no_confirm_cbox.setGeometry(QtCore.QRect(40, 180, 150, 20))

        self.minimize_rbtn.setChecked(not self._settings['x_action_is_quit'])
        self.exit_rbtn.setChecked(self._settings['x_action_is_quit'])
        self.no_confirm_cbox.setChecked(not self._settings['confirm'])

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()
            return self._settings

    def get_inputs(self):
        self._settings["x_action_is_quit"] = self.exit_rbtn.isChecked()
        self._settings["confirm"] = not self.no_confirm_cbox.isChecked()

        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        dlg = QuitConfirmDlg(parent, settings)
        dlg.show()

        result = dlg.exec_()
        assert result in (QtGui.QDialog.Accepted, QtGui.QDialog.Rejected)
#        if result == QtGui.QDialog.Accepted:
#            btn_val = True
#        else:
#            btn_val = False

        return dlg.get_inputs()


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.settings_btn = QtGui.QPushButton("Settings", self)
        self.settings_btn.clicked.connect(self._settings_btn_clicked)

    def _settings_btn_clicked(self):
        global default_settings
        settings = default_settings
        default_settings = QuitConfirmDlg.popup_and_get_inputs(self, settings)
        print "default_settings:", default_settings

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = custom_simple_dialog_ii
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom simple dialog by template

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


default_settings = {
    "confirm" : True,
    "x_action_is_quit" : 0,
}


class CustomDlg(QtGui.QDialog):
    """
    Custom dialog template.

    You should override there method:
     - __init__
     - get_inputs
     - popup_and_get_inputs
    """
    def __init__(self, parent, settings):
        super(CustomDlg, self).__init__(parent)

        self.resize(400, 250)

        self._settings = settings
        self.setModal(True)

        # add custom sub-widgets here ...

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()
            return self._settings

    def get_inputs(self):
        # update self._settings from custom sub-widgets ...
        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        dlg = CustomDlg(parent, settings)
        dlg.show()
        dlg.exec_()


class QuitConfirmDlg(CustomDlg):
    def __init__(self, parent, settings):
        super(QuitConfirmDlg, self).__init__(parent, settings)

        self.resize(400, 250)

        self.tips_label = QtGui.QLabel("When you click the close button should me:", self)
        self.tips_label.setGeometry(QtCore.QRect(40, 40, 280, 15))

        self.minimize_rbtn = QtGui.QRadioButton("&Minimize to system tray", self)
        self.minimize_rbtn.setGeometry(QtCore.QRect(70, 90, 180, 20))

        self.exit_rbtn = QtGui.QRadioButton("&Exit program", self)
        self.exit_rbtn.setGeometry(QtCore.QRect(70, 120, 110, 20))

        self.no_confirm_cbox = QtGui.QCheckBox("&Don't ask me again", self)
        self.no_confirm_cbox.setGeometry(QtCore.QRect(40, 180, 150, 20))

        self.minimize_rbtn.setChecked(not self._settings['x_action_is_quit'])
        self.exit_rbtn.setChecked(self._settings['x_action_is_quit'])
        self.no_confirm_cbox.setChecked(not self._settings['confirm'])

    def get_inputs(self):
        self._settings["x_action_is_quit"] = self.exit_rbtn.isChecked()
        self._settings["confirm"] = not self.no_confirm_cbox.isChecked()

        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        dlg = QuitConfirmDlg(parent, settings)
        dlg.show()
        dlg.exec_()

        return dlg.get_inputs()


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.settings_btn = QtGui.QPushButton("Settings", self)
        self.settings_btn.clicked.connect(self._settings_btn_clicked)

    def _settings_btn_clicked(self):
        global default_settings
        settings = default_settings
        default_settings = QuitConfirmDlg.popup_and_get_inputs(self, settings)
        print "default_settings:", default_settings

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = get_color_dialog
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Provides a dialog widget for specifying colors

NOTE: it doesn't works on PySide.

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QColorDialog.html
"""
import sys

#try:
#    from PySide import QtCore
#    from PySide import QtGui
#except ImportError:
#    from PyQt4 import QtCore
#    from PyQt4 import QtGui

from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.get_color_btn = QtGui.QPushButton('Specifying colors', self)
        x, y = 10, 10
        self.get_color_btn.move(x, y)
        self.get_color_btn.adjustSize()
        self.get_color_btn.clicked.connect(self._get_color_btn_cb)
        qsize = self.get_color_btn.frameSize()


        self.preview_color = QtGui.QWidget(self)
        x, y, w, h = 10 + qsize.width() + 10, 10, 100, 100
        self.preview_color.setGeometry(x, y, w, h)

        color = QtGui.QColor(0, 0, 0)
        style = "QWidget { background-color: %s; }" % color.name()
        self.preview_color.setStyleSheet(style)

        
    def _get_color_btn_cb(self):
        col = QtGui.QColorDialog.getColor()

        if col.isValid():
            style = "QWidget { background-color: %s; }" % col.name()
            self.preview_color.setStyleSheet(style)


    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = get_file_dialog
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Provides a dialog widget for selecting a file

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QFileDialog.html
"""
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        
        self.text_edit = QtGui.QTextEdit()
        self.setCentralWidget(self.text_edit)
        self.statusBar()
        self.setFocus()
        
#        open_file_action = QtGui.QAction(QtGui.QIcon('open.png'), 'Open', self)
        open_file_action = QtGui.QAction('Open', self)
        open_file_action.setShortcut('Ctrl+O') # `command + O` on Mac OS X 
        open_file_action.setStatusTip('Open new File')
        open_file_action.triggered.connect(self._open_file_cb)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(open_file_action)
        
    def _open_file_cb(self):
        filename, filter = QtGui.QFileDialog.getOpenFileName(parent=self,
                                                             caption='Open file',
                                                             dir=os.getenv("HOME"))
        print 'filename:', filename
        print 'filter:', filter
        
        if os.path.exists(filename):
            buf = open(filename).read()
            self.text_edit.setText(buf)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
    
########NEW FILE########
__FILENAME__ = get_font_dialog
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Provides a dialog widget for selecting a font

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QFont.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


text = '''ABCDEFGHIJKLM
NOPQRSTUVWXYZ
abcdefghijklm
nopqrstuvwxyz
1234567890
'''

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.get_font_btn = QtGui.QPushButton('Specifying colors', self)
        x, y = 10, 10
        self.get_font_btn.move(x, y)
        self.get_font_btn.adjustSize()
        self.get_font_btn.clicked.connect(self._get_font_btn_cb)
        qsize = self.get_font_btn.frameSize()

        self.preview_text = QtGui.QLabel(text, self)
        x, y, w, h = 10, 10 + qsize.height() + 10, 280, 200
        self.preview_text.setGeometry(x, y, w, h)
        self.preview_text.setAlignment(QtCore.Qt.AlignHCenter)


        style = "QLabel { font-size: 28px }"
        self.preview_text.setStyleSheet(style)


        self.font_info_label = QtGui.QLabel(self)
        self.font_info_label.setGeometry(10, 350, 200, 20)

    def _get_font_btn_cb(self):
        qfont, ok = QtGui.QFontDialog.getFont()

        print qfont
        print qfont.family()
        print qfont.style()

        if ok:
            self.preview_text.setFont(qfont)
            
            self.font_info_label.setText(qfont.family())

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = get_input_dialog
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
get input dialog demo

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QInputDialog.html
"""
import sys
import web

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        self.setGeometry(300, 300, 350, 80)

        self.button = QtGui.QPushButton('Popup', self)
        self.button.setFocusPolicy(QtCore.Qt.NoFocus)

        self.button.move(20, 20)
        self.connect(self.button, QtCore.SIGNAL('clicked()'), 
            self._get_input)
        self.setFocus()
        
        self.label = QtGui.QLineEdit(self)
        self.label.move(130, 22)
            
    
    def _get_input(self):
        title, msg = 'Get Input Dialog', 'Enter your name:'
        text, resp = QtGui.QInputDialog.getText(self, title, msg)
        
        if resp:
            self.label.setText(web.safeunicode(text))

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = custom_qtoolbutton_icon
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
custom QToolButton icon

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        path = "mic-64x64.png"
        pix = QtGui.QPixmap(path)
        
        label = QtGui.QLabel(self)
        label.move(10, 10)
        label.setPixmap(pix)


        btn = QtGui.QToolButton(self)
        btn.move(10, 100)
        btn.setIconSize(QtCore.QSize(64, 64))

        # way A
#        btn.setIcon(pix)

        # way B
        icon = QtGui.QIcon(pix)
        act = QtGui.QAction(icon, "Send", self)
        btn.setDefaultAction(act)


        style = "QLabel, QToolButton { border : 1px solid red; }"
        self.setStyleSheet(style)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = icon
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
icon

Tested environment:
    Mac OS X 10.6.8

http://doc.trolltech.com/latest/qicon.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui
    

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        icon = QtGui.QIcon("exit.png")
        lab = QtGui.QLabel('foo', self)
        pixmap = icon.pixmap(32, 32, QtGui.QIcon.Normal, QtGui.QIcon.On)
        lab.setPixmap(pixmap)
        x, y = 10, 10
        lab.move(x, y)

        print "icon:", icon.isNull()


        icon2 = QtGui.QIcon("exit.png")
        lab2 = QtGui.QLabel('foo', self)
        pixmap = icon2.pixmap(32, 32, QtGui.QIcon.Disabled, QtGui.QIcon.Off)
        lab2.setPixmap(pixmap)
        x, y = 10, 110
        lab2.move(x, y)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()


    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = qutils
"""
add custom theme name and search path for fix icon file not found on Mac OS X

Install Oxygen icon on Mac OS X via MacPorts:

    sudo port install oxygen-icons

"""
import sys

try:
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtGui


__all__ = [
    "config_theme_path",
]


def config_theme_path():
    if sys.platform != "darwin":
        return

    theme_name = str(QtGui.QIcon.themeName())

    if theme_name != "Oxygen":
        QtGui.QIcon.setThemeName("Oxygen")


    search_paths = list(QtGui.QIcon.themeSearchPaths())

    custom_path = "/opt/local/share/icons"
    if custom_path not in search_paths:
        search_paths.append(custom_path)

    QtGui.QIcon.setThemeSearchPaths(search_paths)

########NEW FILE########
__FILENAME__ = use_buildin_icon
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
using build-in/factory icon

Tested environment:
    Mac OS X 10.6.8

Install Oxygen icon on Mac OS X via MacPorts:

    sudo port install oxygen-icons

http://doc.trolltech.com/latest/qicon.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QIcon.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


import qutils


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        # NOTICE: the difference
        print "themeName:", QtGui.QIcon.themeName()
        print "hasThemeIcon:", QtGui.QIcon.hasThemeIcon("edit-undo")

        qutils.config_theme_path()

        print "themeName:", QtGui.QIcon.themeName()
        print "hasThemeIcon:", QtGui.QIcon.hasThemeIcon("edit-undo")
        print

        my_online = QtGui.QIcon("/path/to/my_online.png")
        
        icon = QtGui.QIcon.fromTheme("user-online", my_online)
        print "icon not found:", icon.isNull()
        print "availableSizes:", icon.availableSizes()

        lab = QtGui.QLabel('foo', self)
        pixmap = icon.pixmap(QtCore.QSize(32, 32), QtGui.QIcon.Normal, QtGui.QIcon.On)
        lab.setPixmap(pixmap)
        lab.move(10, 10)


    def show_and_raise(self):
        self.show()
        self.raise_()



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = lineedit
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
demo template

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qlineedit.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.lineedit = QtGui.QLineEdit(self)
        self.lineedit.move(10, 10)

        # required >= Qt 4.7
        self.lineedit.setPlaceholderText("placeholder")


#        http://doc.qt.nokia.com/latest/qlineedit.html#inputMask-prop
#        mac_address_mask = "HH:HH:HH:HH:HH:HH;_"
#        self.lineedit.setInputMask(mac_address_mask)

        self.lineedit.cursorPositionChanged.connect(self._lineedit_cursorPositionChanged)
        self.lineedit.returnPressed.connect(self._lineedit_returnPressed)

        self.setFocus()

    def _lineedit_cursorPositionChanged(self, old, new):
        print old, new

    def _lineedit_returnPressed(self):
        print "text:", self.lineedit.text()

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = textedit
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QTextEdit demo

 - change text in MVC mode
 - custom CSS

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qtextedit.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QTextEdit.html
"""
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui



css = '''
div {
    line-height: 27px;
}
.nickname {
    color: #A52A2A;
    font-weight: bolder;
}
.ts {
    color: #7F7F7F;
}
'''

class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.text_doc = QtGui.QTextDocument()
        self.text_doc.setDefaultStyleSheet(css)

        self.text_edit = QtGui.QTextEdit(self)
        self.setCentralWidget(self.text_edit)
        self.text_edit.setDocument(self.text_doc)
        self.text_edit.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard | QtCore.Qt.TextSelectableByMouse)
#        self.text_edit.setReadOnly(True)
        self.log(msg = ' ')
        self.log(msg = 'hello\nworld')
        self.log(msg = 'hello\nworld')
        self.log(msg = u'中文输入\n法 KDE 桌面环境')
        self.log(msg = 'hello\nworld')
        self.log(msg = 'hello\nworld')
        self.log(msg = 'hello\nworld')
        self.log(msg = 'hello\nworld')

        self.top_btn = QtGui.QPushButton("top", self)
        self.top_btn.move(150, 280)
        self.top_btn.clicked.connect(self.goto_top_btn_clicked)

        self.buttom_btn = QtGui.QPushButton("bottom", self)
        self.buttom_btn.move(150, 300)
        self.buttom_btn.clicked.connect(self.goto_buttom_btn_clicked)
        
        #t = self.text_edit.toHtml()
        
        self.show()

    def goto_top_btn_clicked(self):
        scroll_bar = self.text_edit.verticalScrollBar()
        scroll_bar.setSliderPosition(scroll_bar.minimum())

    def goto_buttom_btn_clicked(self):
        scroll_bar = self.text_edit.verticalScrollBar()
        scroll_bar.setSliderPosition(scroll_bar.maximum())

    def log(self, nickname = 'foo', msg = None):
        t = QtCore.QTime()
        now_time = t.currentTime().toString()

        msg = msg.replace(os.linesep, '<br />')
        log = '''<div><span class="nickname">%s</span>&nbsp;&nbsp;<span class="ts">%s</span><p class="msg">%s</p></div>''' % \
            (nickname, now_time, msg)
        self.text_edit.append(log)

#        t = self.text_doc.toHtml()
#        with open('log.txt', 'w') as f:
#            f.write(t.toUtf8())

#        # buf = t
#        buf = QtCore.QString('<html><body>你好</body></html>'.decode('utf-8'))
#        self.text_doc.setHtml(buf)

#        t = self.text_doc.toHtml()
#        with open('log2.txt', 'w') as f:
#            f.write(t.toUtf8())

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = label
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Label

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QLabel.html
"""
import sys
import web

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        # support basic rich text
        text1 = "Hello, <a href='http://www.pyside.org/'>PySide</a>"
        label1 = QtGui.QLabel(text1, self)
        x, y = 20, 20
        label1.move(x, y)
        label1.linkActivated.connect(self._label1_linkActivated)
        label1.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
    

        label2 = QtGui.QLabel(self)
        x, y = 20, 55
        label2.move(x, y)
        text2 = u'\u4e2d\u6587'
        label2.setText(text2)
        label2.setFrameStyle(QtGui.QFrame.Panel)

        print label1.text(), type(label1.text()), label1.text() == text1
        print label2.text(), type(label2.text()), label2.text() == web.safeunicode(text2)


    def show_and_raise(self):
        self.show()
        self.raise_()

    def _label1_linkActivated(self, link):
        print "you clicked the link:", link

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()


    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = custom_right_click_popup_menu
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom popup menu trigger by right click in QTreeView

Tested environment:
    Mac OS X 10.6.8

http://developer.qt.nokia.com/doc/qt-4.8/qmenu.html#details
http://diotavelli.net/PyQtWiki/Handling%20context%20menus
"""
import sys

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


datas = [
    "a",
    "b",
    "c",
]

class Demo(QtGui.QWidget):
    def __init__(self):

        QtGui.QWidget.__init__(self)

        self.treeView = QtGui.QTreeView()
        self.model = QtGui.QStandardItemModel()
        for name in datas:
            item = QtGui.QStandardItem(name)
            self.model.appendRow(item)
        self.treeView.setModel(self.model)

        self.model.setHorizontalHeaderLabels([self.tr("Object")])

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.treeView)
        self.setLayout(layout)


        self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self._ctx_menu_cb)


        self.popup_menu = QtGui.QMenu(self)

        # menu item
        self.item_add_act = QtGui.QAction("Add", self)
        self.item_add_act.triggered.connect(self.add_cb)
        self.popup_menu.addAction(self.item_add_act)

    def add_cb(self):
        print "add callback"

    def _ctx_menu_cb(self, pos):
        print "pos:", pos

#    def contextMenuEvent(self, event):
#        point = self.mapToGlobal(event.pos())
#        act = self.popup_menu.exec_(point)
#
#        if act == self.item_add_act:
#            print "item add clicked"
#
#        return super(Demo, self).contextMenuEvent(event)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = popup_menu_by_right_click
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
popup menu by right click

Tested environment:
    Mac OS X 10.6.8

http://developer.qt.nokia.com/doc/qt-4.8/qmenu.html#details
http://diotavelli.net/PyQtWiki/Handling%20context%20menus
"""
import sys

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.popup_menu = QtGui.QMenu(self)

        # menu item
        self.item_add_act = QtGui.QAction("Add", self)
        self.item_add_act.triggered.connect(self.add_cb)
        self.popup_menu.addAction(self.item_add_act)

        self.item_delete_act = QtGui.QAction("Delete", self)
        self.item_delete_act.triggered.connect(self.delete_cb)
        self.popup_menu.addAction(self.item_delete_act)

        self.popup_menu.addSeparator()

        self.item_rename_act = QtGui.QAction("Rename", self)
        self.item_rename_act.triggered.connect(self.rename_cb)
        self.popup_menu.addAction(self.item_rename_act)

    def add_cb(self):
        print "add callback"

    def delete_cb(self):
        print "delete callback"

    def rename_cb(self):
        print "rename callback"

    def contextMenuEvent(self, event):
        point = self.mapToGlobal(event.pos())
        act = self.popup_menu.exec_(point)

        if act == self.item_add_act:
            print "item add clicked"
        elif act == self.item_delete_act:
            print "item delete clicked"
        elif act == self.item_rename_act:
            print "item rename clicked"

        return super(Demo, self).contextMenuEvent(event)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = popup_menu_in_treeview
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
popup menu in QTreeView

Tested environment:
    Mac OS X 10.6.8

http://developer.qt.nokia.com/doc/qt-4.8/qmenu.html#details
http://diotavelli.net/PyQtWiki/Handling%20context%20menus
"""
import sys

try:
    from PySide import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


datas = [
    "a",
    "b",
    "c",
]

class Demo(QtGui.QWidget):
    def __init__(self):

        QtGui.QWidget.__init__(self)

        self.treeView = QtGui.QTreeView()
        self.model = QtGui.QStandardItemModel()
        for name in datas:
            item = QtGui.QStandardItem(name)
            self.model.appendRow(item)
        self.treeView.setModel(self.model)

        self.model.setHorizontalHeaderLabels([self.tr("Object")])

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.treeView)
        self.setLayout(layout)


        self.popup_menu = QtGui.QMenu(self)

        # menu item
        self.item_add_act = QtGui.QAction("Add", self)
        self.item_add_act.triggered.connect(self.add_cb)
        self.popup_menu.addAction(self.item_add_act)

    def add_cb(self):
        print "add callback"

    def contextMenuEvent(self, event):
        point = self.mapToGlobal(event.pos())
        widget = QtGui.QApplication.widgetAt(point)
        print "widget:", widget

        act = self.popup_menu.exec_(point)

        if act == self.item_add_act:
            print "item add clicked"

        return super(Demo, self).contextMenuEvent(event)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = popup_multi_levels_menus_by_right_click
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
popup multi levels menu by right click

Tested environment:
    Mac OS X 10.6.8

http://developer.qt.nokia.com/doc/qt-4.8/qmenu.html#details
http://diotavelli.net/PyQtWiki/Handling%20context%20menus
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.popup_menu = QtGui.QMenu(self)

        # sub-menu
        self.sub_menu = self.popup_menu.addMenu("sub-menu")
        print "sub_menu:", self.sub_menu

        self.item_add_act = QtGui.QAction("Add", self)
        self.item_add_act.triggered.connect(self.add_cb)
        self.sub_menu.addAction(self.item_add_act)

    def add_cb(self):
        print "add callback"

    def contextMenuEvent(self, event):
        point = self.mapToGlobal(event.pos())
        act = self.popup_menu.exec_(point)

        if act == self.item_add_act:
            print "item add clicked"

        return super(Demo, self).contextMenuEvent(event)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = pixmap_alpha_channel
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QPixmap alphaChannel

Tested environment:
    Mac OS X 10.6.8


Install Oxygen icon on Mac OS X via MacPorts:

    sudo port install oxygen-icons


http://doc.qt.nokia.com/latest/qpixmap.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QPixmap.html#PySide.QtGui.PySide.QtGui.QPixmap.alphaChannel
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui
    

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        if sys.platform == "darwin":
            QtGui.QIcon.setThemeName("Oxygen")
            QtGui.QIcon.setThemeSearchPaths(["/opt/local/share/icons"])

        icon = QtGui.QIcon.fromTheme("user-online")
#        icon = QtGui.QIcon("online.png")
        
        pix = icon.pixmap(100, 100)
        new_pix = pix.alphaChannel()

        label = QtGui.QLabel(self)
        label.move(10, 10)
        label.setPixmap(pix)

        label2 = QtGui.QLabel(self)
        label2.move(10, 110)
        label2.setPixmap(new_pix)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = pixmap_img_conversion_flags
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QPixmap imageConversionFlags demo

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        path = "captcha.jpg"
        pix = QtGui.QPixmap(path, flags = QtCore.Qt.MonoOnly)

        label = QtGui.QLabel("foo", self)
        label.setPixmap(pix)
        label.move(10, 10)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = progress_bar
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtGui


class Example(QtGui.QWidget):
    def __init__(self):
        super(Example, self).__init__()

        self.pbar = QtGui.QProgressBar(self)
        self.pbar.setGeometry(30, 40, 200, 25)
        self.pbar.setMaximum(0)
        self.pbar.setMinimum(0)

#        self.button = QtGui.QPushButton('Start', self)
#        self.button.setFocusPolicy(QtCore.Qt.NoFocus)
#        self.button.move(40, 80)
#
#        self.connect(self.button, QtCore.SIGNAL('clicked()'),
#            self.doAction)
#
#        self.timer = QtCore.QBasicTimer()
#        self.step = 0
#
#        self.setWindowTitle('ProgressBar')
#        self.setGeometry(300, 300, 250, 150)
        self.show()


#    def timerEvent(self, event):
#
#        if self.step >= 100:
#            self.timer.stop()
#            return
#        self.step = self.step + 1
#        self.pbar.setValue(self.step)
#
#    def doAction(self):
#
#        if self.timer.isActive():
#            self.timer.stop()
#            self.button.setText('Start')
#        else:
#            self.timer.start(100, self)
#            self.button.setText('Stop')


if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    ex = Example()
    assert ex != None
    app.exec_()
########NEW FILE########
__FILENAME__ = slider
#!/usr/bin/python
# -*- coding: utf-8 -*-

# slider.py

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()
        
        self.initUI()
        
    def initUI(self):

        slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        slider.setFocusPolicy(QtCore.Qt.NoFocus)
        slider.setGeometry(30, 40, 100, 30)
        self.connect(slider, QtCore.SIGNAL('valueChanged(int)'), 
            self.changeValue)
        
        self.label = QtGui.QLabel(self)
        self.label.setPixmap(QtGui.QPixmap('mute.png'))
        self.label.setGeometry(160, 40, 80, 30)
        
        self.setWindowTitle('Slider')
        self.setGeometry(300, 300, 250, 150)
        
    
    def changeValue(self, value):

        if value == 0:
            self.label.setPixmap(QtGui.QPixmap('../icons/mute.png'))
        elif value > 0 and value <= 30:
            self.label.setPixmap(QtGui.QPixmap('../icons/min.png'))
        elif value > 30 and value < 80:
            self.label.setPixmap(QtGui.QPixmap('../icons/med.png'))
        else:
            self.label.setPixmap(QtGui.QPixmap('../icons/max.png'))


if __name__ == '__main__':
  
    app = QtGui.QApplication(sys.argv)
    ex = Example()
    ex.show()
    app.exec_()
########NEW FILE########
__FILENAME__ = qspacerItem_demo
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QSpacerItem demo

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QDialog):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)
        
        okBtn = QtGui.QPushButton('ok')
        cancelBtn = QtGui.QPushButton('cancel') 

        btnLayout = QtGui.QHBoxLayout()

        btnLayout.addWidget(okBtn)

        btnLayout.addSpacerItem(QtGui.QSpacerItem(50, 50))

        btnLayout.addWidget(cancelBtn)
        
        layout = QtGui.QGridLayout()

#        layout.addLayout(btnLayout, int row, int column, int rowSpan, int columnSpan, alignment = 0)
        layout.addLayout(btnLayout, 2, 0, 1, 3)
        
        self.setLayout(layout)
        
    def show_and_raise(self):
        self.show()
        self.raise_()

        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show()

    app.exec_()


########NEW FILE########
__FILENAME__ = markup_editor
#!/usr/bin/env python
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
    from PySide import QtWebKit
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui
    from PyQt4 import QtWebKit


class Foo(QtGui.QWidget):
    def __init__(self):
        super(Foo, self).__init__()

        x, y, w, h = 100, 100, 900, 600
        self.setGeometry(x, y, w, h)


        self.source = QtGui.QTextEdit(self)
        self.preview = QtWebKit.QWebView(self)

        self.splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.source)
        self.splitter.addWidget(self.preview)

        self.hbox = QtGui.QHBoxLayout(self)
        self.hbox.addWidget(self.splitter)
        self.setLayout(self.hbox)

        
        self.font = QtGui.QFont("Monaco", 13)
        self.setFont(self.font)
    
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    foo = Foo()
    foo.show()
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = splitter
#!/usr/bin/python
# -*- coding: utf-8 -*-

# ZetCode PyQt4 tutorial
#
# This example shows
# how to use QSplitter widget.
# 
# author: Jan Bodnar
# website: zetcode.com
# last edited: December 2010


from PySide import QtGui, QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()

        self.initUI()


    def initUI(self):

        hbox = QtGui.QHBoxLayout(self)

        topleft = QtGui.QFrame(self)
        topleft.setFrameShape(QtGui.QFrame.StyledPanel)
 
        topright = QtGui.QFrame(self)
        topright.setFrameShape(QtGui.QFrame.StyledPanel)

        bottom = QtGui.QFrame(self)
        bottom.setFrameShape(QtGui.QFrame.StyledPanel)

        splitter1 = QtGui.QSplitter(QtCore.Qt.Horizontal)
        splitter1.addWidget(topleft)
        splitter1.addWidget(topright)

        splitter2 = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(bottom)

        hbox.addWidget(splitter2)
        self.setLayout(hbox)

        self.setWindowTitle('QSplitter')
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
        self.setGeometry(250, 200, 350, 250)
        

def main():

    app = QtGui.QApplication([])
    ex = Example()
    ex.show()
    app.exec_()


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = statusbar
#!/usr/bin/python

# statusbar.py 

import sys
from PyQt4 import QtGui

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.resize(250, 150)
        self.setWindowTitle('statusbar')

        self.statusBar().showMessage('Ready')


app = QtGui.QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = tab
import sys
from PyQt4 import QtCore, QtGui

from ui.ui_chat import Ui_chatWindow


class ChatWindow(QtGui.QWidget, Ui_chatWindow):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setupUi(self)

        self.chat_view = self.chatHistoryTextEdit


        self.convTab.clear()
        self.convTab.setDocumentMode(True)

        self.convTab.currentChanged.connect(self.current_tab_changed)
        self.convTab.tabBar().tabCloseRequested.connect(self.tab_close_requested)

    def add_tab(self, contact_uri):
        if self.isHidden():
            self.show()

        if contact_uri == '10000':
            label = "sys info"
        else:
            label = contact_uri

        chat_input = QtGui.QTextEdit()
        new_idx = self.convTab.addTab(chat_input, QtCore.QString(label))
        self.convTab.setCurrentIndex(new_idx)

        tabbar = self.convTab.tabBar()
        tabbar.setTabData(new_idx, contact_uri)
        #self.convTab.tabBar().setTabData(new_idx, contact_uri)
        #self.focus_on_current_chat_tab()
        self.convTab.setTabBar(tabbar)

        self.contactNameLabel.setText(label)

    def current_tab_changed(self, idx):
        print("current_tab_changed")
        print("current idx: %d" % idx)

        NO_TAB = -1
        if idx == NO_TAB:
            return

        tabbar = self.convTab.tabBar()

        display_name = tabbar.tabText(idx)
        self.contactNameLabel.setText(display_name)

        contact_uri = tabbar.tabData(idx)
        print "type:", contact_uri
        print "contact_uri:", contact_uri.toString()

    def tab_close_requested(self, idx):
        no_input = self.convTab.widget(idx).toPlainText()
        if not no_input:
            self.convTab.removeTab(idx)
        else:
            msg = "Pressing the ESC key will close this conversation. <br />" \
                    "Are you sure you want to continue ?"
            if popup_confirm(self, msg):
                self.convTab.removeTab(idx)

        if not self.convTab.count():
            self.hide()

    def _close_current_tab(self):
        self.convTab.removeTab(self.convTab.currentIndex())
        if not self.convTab.count():
            self.hide()

    def go_to_tab_by_uri(self, contact_uri):
        for idx in xrange(self.convTab.count()):
            tab_uri = str(self.convTab.tabBar().tabData(idx).toString())
            if tab_uri == contact_uri:
                print("go to existed chat tab")
                self.convTab.setCurrentIndex(idx)
                self.focus_on_current_chat_tab()
                return True
        return False


    def keyPressEvent(self, event):
        key = event.key()
        is_goto_prev_tab = (event.modifiers() == QtCore.Qt.ControlModifier) and (key == QtCore.Qt.Key_BracketLeft)
        is_goto_next_tab = (event.modifiers() == QtCore.Qt.ControlModifier) and (key == QtCore.Qt.Key_BracketRight)
        is_send_msg = key == QtCore.Qt.Key_Return
        is_close_tab = key == QtCore.Qt.Key_Escape
        is_switch_tab = (event.modifiers() == QtCore.Qt.ControlModifier) and (key >= QtCore.Qt.Key_1 and key <= QtCore.Qt.Key_9)
        CHAR_START_AT = 48

        if is_close_tab:
            if not self.convTab.count():
                self.hide()
                return

            no_input = self.convTab.currentWidget().toPlainText()
            if not no_input:
                self._close_current_tab()
            else:
                msg = "Pressing the ESC key will close this conversation. <br />" \
                        "Are you sure you want to continue ?"
                if popup_confirm(self, msg):
                    self._close_current_tab()

        elif is_send_msg:
            widget = self.convTab.currentWidget()
            if not widget:
                return
            msg = widget.toPlainText()
            if not msg:
                return
            widget.clear()
            print 'send'

        elif is_switch_tab:
            count = self.convTab.count()
            k = key.real - CHAR_START_AT
            if 1 > k and k > 9:
                return
            if k < count + 1:
                self.convTab.setCurrentIndex(k - 1)
        elif is_goto_prev_tab:
            count = self.convTab.count()
            cur_idx = self.convTab.currentIndex()

            if count == 1:
                return
            elif cur_idx == 0:
                self.convTab.setCurrentIndex(count - 1)
            else:
                self.convTab.setCurrentIndex(cur_idx - 1)
        elif is_goto_next_tab:
            count = self.convTab.count()
            cur_idx = self.convTab.currentIndex()

            if count == 1:
                return
            elif (count - 1) == cur_idx:
                self.convTab.setCurrentIndex(0)
            else:
                self.convTab.setCurrentIndex(cur_idx + 1)

class Main(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self, parent = None)
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.chat_win = ChatWindow()

        self.chat_win.show()

        self.btn = QtGui.QPushButton(self)
        self.btn.clicked.connect(self.show_tab)

        self.add_btn = QtGui.QPushButton('add', self)
        self.add_btn.clicked.connect(self.add_tab)

        self.del_btn = QtGui.QPushButton('del', self)
        self.del_btn.clicked.connect(self.del_tab)

        qh = QtGui.QHBoxLayout()
        qh.addWidget(self.btn)
        qh.addWidget(self.add_btn)
        qh.addWidget(self.del_btn)

        self.setLayout(qh)

        self.show()

        self.c = 1

    def add_tab(self):

        self.chat_win.add_tab(str(self.c))

        self.c += 1
        
    def del_tab(self):
        pass

    def show_tab(self):
        self.chat_win.show()


def main():
    app = QtGui.QApplication(sys.argv)
    main = Main()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()
    
########NEW FILE########
__FILENAME__ = toolbar
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QToolBar and QAction demo

Tested environment:
    Mac OS X 10.6.8


http://doc.qt.nokia.com/latest/qaction.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QToolBar.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QAction.html
http://www.devbean.info/2011/08/native-style-qt-8/

"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

def config_theme_path():
    if sys.platform != "darwin":
        return

    theme_name = str(QtGui.QIcon.themeName())

    if theme_name != "Oxygen":
        QtGui.QIcon.setThemeName("Oxygen")


    search_paths = list(QtGui.QIcon.themeSearchPaths())

    custom_path = "/opt/local/share/icons"
    if custom_path not in search_paths:
        search_paths.append(custom_path)

    QtGui.QIcon.setThemeSearchPaths(search_paths)


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)
        self.setUnifiedTitleAndToolBarOnMac(True)

        config_theme_path()
        icon = QtGui.QIcon.fromTheme('application-exit')

        exit_a = QtGui.QAction(icon, 'Exit', self)
        exit_a.setShortcut('Ctrl+Q')
#        self.connect(exit_a, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        exit_a.triggered.connect(self.close)


        toolbar = self.addToolBar('Exit')
        toolbar.addAction(exit_a)

        self._toolbar = toolbar

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = tray
"""
System tray icon and Prompt on PyQt/PySide application exit

NOTE: We don't catch closeEvent cause by command-q on Mac.

Tested environment:
    Mac OS X 10.6.8
"""
import json
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


default_settings = {
    "confirm" : True,
    "x_action_is_quit" : False,
}

default_settings_path = 'settings.json'
logo_path = "qt-logo.png"


def save_settings(settings, path=default_settings_path):
    with open(path, 'w') as f:
        buf = json.dumps(settings)
        f.write(buf)

def load_settings(path=default_settings_path):
    if os.path.exists(path):
        with open(path) as f:
            c = f.read()
            settings = json.loads(c)
    else:
        global default_settings
        settings = default_settings

    return settings


class CustomDlg(QtGui.QDialog):
    """
    Custom dialog template.

    You should override there method:
     - __init__
     - get_inputs
     - popup_and_get_inputs
    """
    def __init__(self, parent, settings):
        super(CustomDlg, self).__init__(parent)

        self.resize(400, 250)

        self._settings = settings
        self.setModal(True)

        # add custom sub-widgets here ...

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()
            return self._settings

    def get_inputs(self):
        # update self._settings from custom sub-widgets ...
        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        dlg = CustomDlg(parent, settings)
        dlg.show()
        dlg.exec_()


class QuitConfirmDlg(CustomDlg):
    def __init__(self, parent, settings):
        super(QuitConfirmDlg, self).__init__(parent, settings)

        self.resize(400, 250)

        self.tips_label = QtGui.QLabel("When you click the close button should me:", self)
        self.tips_label.setGeometry(40, 40, 280, 15)

        self.minimize_rbtn = QtGui.QRadioButton("&Minimize to system tray", self)
        self.minimize_rbtn.setGeometry(70, 90, 180, 20)

        self.exit_rbtn = QtGui.QRadioButton("&Exit program", self)
        self.exit_rbtn.setGeometry(70, 120, 110, 20)

        self.no_confirm_cbox = QtGui.QCheckBox("&Don't ask me again", self)
        self.no_confirm_cbox.setGeometry(40, 180, 150, 20)

        self.minimize_rbtn.setChecked(not self._settings['x_action_is_quit'])
        self.exit_rbtn.setChecked(self._settings['x_action_is_quit'])
        self.no_confirm_cbox.setChecked(not self._settings['confirm'])

    def get_inputs(self):
        self._settings["x_action_is_quit"] = self.exit_rbtn.isChecked()
        self._settings["confirm"] = not self.no_confirm_cbox.isChecked()

        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        dlg = QuitConfirmDlg(parent, settings)
        dlg.show()
        dlg.exec_()

        return dlg.get_inputs()


class Demo(QtGui.QMainWindow):
    def __init__(self, logo_icon):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.settings = load_settings(default_settings_path)

        self.sys_tray_icon = QtGui.QSystemTrayIcon(parent=self)
        self.sys_tray_icon.setIcon(logo_icon)
        self.sys_tray_icon.activated.connect(self.on_sys_tray_icon_clicked)
        self.sys_tray_icon.messageClicked.connect(self.on_sys_tray_icon_msg_clicked)
        self.sys_tray_icon.show()
        
#        self.sys_tray_icon_show_msg('title', 'msg')

    def show_and_raise(self):
        self.show()
        self.raise_()

    @staticmethod
    def confirm_quit(main_win, close_evt=None):
        if main_win.settings["confirm"]:
            QuitConfirmDlg.popup_and_get_inputs(main_win, main_win.settings)
            save_settings(main_win.settings)

        if main_win.settings['x_action_is_quit']:
            if close_evt:
                close_evt.accept()

            return True
        else:
            if close_evt:
                close_evt.ignore()

            main_win.hide()

            return False

    def closeEvent(self, evt):
        self.confirm_quit(self, evt)

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)
 
        if close_win_cmd_w or close_win_esc:
            self.close()

    def on_sys_tray_icon_clicked(self, activation_reason):
        assert activation_reason in (
            QtGui.QSystemTrayIcon.Trigger,
            QtGui.QSystemTrayIcon.DoubleClick,
            QtGui.QSystemTrayIcon.MiddleClick)

        self.show_and_raise()

    def on_sys_tray_icon_msg_clicked(self, *args, **kwargs):
        print 'msg clicked'

    def sys_tray_icon_show_msg(self, title, msg,
                               icon = QtGui.QSystemTrayIcon.MessageIcon(),
                               msecs = 10000):
        if self.sys_tray_icon.supportsMessages():
            self.sys_tray_icon.showMessage(title, msg, icon, msecs)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    logo_icon = QtGui.QIcon(logo_path)
    app.setWindowIcon(logo_icon)

    main = Demo(logo_icon=logo_icon)
    main.show_and_raise()
    
    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = tray_catch_cmd_q
"""
System tray icon and Prompt on PyQt/PySide application exit

NOTE: We do catch closeEvent cause by command-q on Mac,
    this feature bring a bug here, it could listen user clicks application icon/dock icon.

Tested environment:
    Mac OS X 10.6.8

See also:
 - http://lists.trolltech.com/qt-interest/2007-06/msg00820.html
"""
import json
import os
import sys
import threading

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class PeriodicExecutorOnce(threading.Thread):
    def __init__(self, interval, func, *args, **kwargs):
        threading.Thread.__init__(self, name = "PeriodicExecutor")
        self._interval = interval
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._finished = threading.Event()

    def cancel(self):
        self._finished.set()

    def run(self):
        self._finished.wait(self._interval)
        self._func(*self._args, **self._kwargs)
        self._finished.set()


default_settings = {
    "confirm" : True,
    "x_action_is_quit" : 0,
}

default_settings_path = 'settings.json'


def save_settings(settings, path=default_settings_path):
    with open(path, 'w') as f:
        buf = json.dumps(settings)
        f.write(buf)

def load_settings(path=default_settings_path):
    if os.path.exists(path):
        with open(path) as f:
            c = f.read()
            settings = json.loads(c)
    else:
        global default_settings
        settings = default_settings

    return settings


def confirm_quit(main_win, close_evt=None):
    if main_win.settings["confirm"]:
        if main_win.settings['x_action_is_quit']:
            save_settings(main_win.settings)

            if close_evt:
                close_evt.accept()

            return True
        else:
            if close_evt:
                close_evt.ignore()

            main_win.hide()

            return False


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.settings = load_settings(default_settings_path)

        self._press_cmd_q = None
        self._last_key = None
        self._last_modifiers = None

        self._confirm_quit_t = None


    def _confirm_quit(self):
        if confirm_quit(self):
            save_settings(self.settings)

            QtCore.QCoreApplication.instance().quit()

    def keyReleaseEvent(self, evt):
        key = evt.key()

        if hasattr(QtCore.Qt.Key_Control, 'real'):
            # compitable with PyQt
            if key == QtCore.Qt.Key_Control.real:
                self._last_modifiers = QtCore.Qt.ControlModifier

            if key == QtCore.Qt.Key_Q.real:
                self._last_key = QtCore.Qt.Key_Q
        else:
            # compitable with PySide
            if key == QtCore.Qt.Key_Control:
                self._last_modifiers = QtCore.Qt.ControlModifier

            if key == QtCore.Qt.Key_Q:
                self._last_key = QtCore.Qt.Key_Q

        press_cmd_q = (self._last_modifiers == QtCore.Qt.ControlModifier) and (self._last_key == QtCore.Qt.Key_Q)

        if press_cmd_q:
            if confirm_quit(self, evt):
                QtCore.QCoreApplication.instance().quit()
                
            self._press_cmd_q = True
            self._last_key = None
            self._last_modifiers = None

            self._confirm_quit_t.cancel()

        super(Demo, self).keyReleaseEvent(evt)

    def event(self, evt):
        e_type = evt.type()

        if e_type == QtCore.QEvent.Close:
            self._confirm_quit_t = PeriodicExecutorOnce(0.1, self._confirm_quit)
            self._confirm_quit_t.start()

            evt.ignore()
            return False
        else:
            return super(Demo, self).event(evt)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    main = Demo()

    main.show()
    main.raise_()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = badge_button
#!/usr/bin/env python
"""
Qt Notification Badge

References

 - http://th30z.blogspot.com/2008/10/cocoa-notification-badge_127.html
 - http://khertan.net/blog/qbadgebutton_a_qpushbutton_with_a_badge_counter

origin version it here
http://khertan.net/blog/qbadgebutton_a_qpushbutton_with_a_badge_counter
"""
import sys

try:
    from PySide import QtGui, QtCore
except ImportError:
    from PyQt4 import QtGui, QtCore
    
 
class QBadgeButton(QtGui.QPushButton): 
    def __init__(self, icon = None, text = None, parent = None):
        if icon:
            QtGui.QPushButton.__init__(self, icon, text, parent)
        elif text:
            QtGui.QPushButton.__init__(self, text, parent)
        else:
            QtGui.QPushButton.__init__(self, parent)
 
        self.badge_counter = 0
        self.badge_size = 50
 
        self.redGradient = QtGui.QRadialGradient(0.0, 0.0, 17.0, self.badge_size - 3, self.badge_size - 3);
        self.redGradient.setColorAt(0.0, QtGui.QColor(0xe0, 0x84, 0x9b));
        self.redGradient.setColorAt(0.5, QtGui.QColor(0xe9, 0x34, 0x43));
        self.redGradient.setColorAt(1.0, QtGui.QColor(0xdc, 0x0c, 0x00));
 
    def setSize(self, size):
        self.badge_size = size
 
    def setCounter(self, counter):
        self.badge_counter = counter
        self.update()
 
    def paintEvent(self, event):
        QtGui.QPushButton.paintEvent(self, event)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
 
        if self.badge_counter > 0:
            point = self.rect().topRight()
            self.drawBadge(p,
                           point.x()-self.badge_size - 1,
                           point.y() + 1,
                           self.badge_size,
                           str(self.badge_counter),
                           QtGui.QBrush(self.redGradient))
 
    def fillEllipse(self, painter, x, y, size, brush):
        path = QtGui.QPainterPath()
        path.addEllipse(x, y, size, size);
        painter.fillPath(path, brush);
 
    def drawBadge(self, painter, x, y, size, text, brush):
        painter.setFont(QtGui.QFont(painter.font().family(), 11, QtGui.QFont.Bold))
 
        while ((size - painter.fontMetrics().width(text)) < 10):
            pointSize = painter.font().pointSize() - 1
            weight = QtGui.QFont.Normal if (pointSize < 8) else QtGui.QFont.Bold
            painter.setFont(QtGui.QFont(painter.font().family(), painter.font().pointSize() - 1, weight))
 
        shadowColor = QtGui.QColor(0, 0, 0, size)
        self.fillEllipse(painter, x + 1, y, size, shadowColor)
        self.fillEllipse(painter, x - 1, y, size, shadowColor)
        self.fillEllipse(painter, x, y + 1, size, shadowColor)
        self.fillEllipse(painter, x, y - 1, size, shadowColor)
 
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2));
        self.fillEllipse(painter, x, y, size - 3, brush)
        painter.drawEllipse(x, y, size - 3, size - 3)
 
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 1));
        painter.drawText(x, y, size - 2, size - 2, QtCore.Qt.AlignCenter, text);
 
        
class QToolBadgeButton(QtGui.QToolButton):
    def __init__(self, parent = None):
        QtGui.QToolButton.__init__(self, parent)
 
        self.badge_counter = 0
        self.badge_size = 25
 
        self.redGradient = QtGui.QRadialGradient(0.0, 0.0, 17.0, self.badge_size - 3, self.badge_size - 3);
        self.redGradient.setColorAt(0.0, QtGui.QColor(0xe0, 0x84, 0x9b));
        self.redGradient.setColorAt(0.5, QtGui.QColor(0xe9, 0x34, 0x43));
        self.redGradient.setColorAt(1.0, QtGui.QColor(0xdc, 0x0c, 0x00));
 
    def setSize(self, size):
        self.badge_size = size
 
    def setCounter(self, counter):
        self.badge_counter = counter
 
    def paintEvent(self, event):
        QtGui.QToolButton.paintEvent(self, event)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.badge_counter > 0:
            point = self.rect().topRight()
            self.drawBadge(p,
                           point.x()-self.badge_size, point.y(),
                           self.badge_size,
                           str(self.badge_counter),
                           QtGui.QBrush(self.redGradient))
 
    def fillEllipse(self, painter, x, y, size, brush):
        path = QtGui.QPainterPath()
        path.addEllipse(x, y, size, size);
        painter.fillPath(path, brush);
 
    def drawBadge(self, painter, x, y, size, text, brush):
        painter.setFont(QtGui.QFont(painter.font().family(), 11, QtGui.QFont.Bold))
 
        while ((size - painter.fontMetrics().width(text)) < 10):
            pointSize = painter.font().pointSize() - 1
            weight = QtGui.QFont.Normal if (pointSize < 8) else QtGui.QFont.Bold
            painter.setFont(QtGui.QFont(painter.font().family(), painter.font().pointSize() - 1, weight))
 
        shadowColor = QtGui.QColor(0, 0, 0, size)
        self.fillEllipse(painter, x + 1, y, size, shadowColor)
        self.fillEllipse(painter, x - 1, y, size, shadowColor)
        self.fillEllipse(painter, x, y + 1, size, shadowColor)
        self.fillEllipse(painter, x, y - 1, size, shadowColor)
 
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2));
        self.fillEllipse(painter, x, y, size - 3, brush)
        painter.drawEllipse(x, y, size - 2, size - 2)
 
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 1));
        painter.drawText(x, y, size - 2, size - 2, QtCore.Qt.AlignCenter, text);
 
        
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    win = QtGui.QMainWindow()
 
    toolbar = QtGui.QToolBar('Toolbar')
    win.addToolBar(QtCore.Qt.BottomToolBarArea, toolbar)
    b = QToolBadgeButton(win)
    b.setText("test")
    b.setCounter(22)
    toolbar.addWidget(b)
 
    w = QBadgeButton(parent=win)
    w.setText("test")
    w.setCounter(22)
    win.setCentralWidget(w)
    win.show()
 
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = im_sign_in_window
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
IM sign in window

Tested environment:
    Mac OS X 10.6.8

https://bitbucket.org/shugelee/iblah/
"""
import sys
import webbrowser

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 600, 300
        self.setGeometry(x, y, w, h)


        account_label = QtGui.QLabel("Cellphone No./Fetion No./E-Mail:", self)
        x, y, w, h = 40, 40, 221, 30
        account_label.setGeometry(x, y, w, h)

        self.account_combox = QtGui.QComboBox(self)
        self.account_combox.setEditable(True)
        self.account_combox.setGeometry(70, 70, 200, 26)
        self.connect(self.account_combox, QtCore.SIGNAL('currentIndexChanged(QString)'),
                     self._account_combox_currentIndexChanged)


#        sign_up_link = 'https://feixin.10086.cn/account/register'
        sign_up_link = "#"
        text = '<a href="%s">Sign Up</a>' % sign_up_link
        sign_up_label = QtGui.QLabel(text, self)
        sign_up_label.setGeometry(300, 70, 130, 30)
        sign_up_label.linkActivated.connect(self._show_sign_up_dlg)


        passwd_label = QtGui.QLabel("Password:", self)
        passwd_label.setGeometry(40, 110, 62, 30)

        self.passwd_lineedit = QtGui.QLineEdit(self)
        self.passwd_lineedit.setGeometry(70, 140, 200, 22)


#        reset_passwd_link = 'http://my.feixin.10086.cn/password/find/'
        reset_passwd_link = "#"
        text = "<a href='%s'>Reset Password</a>" % reset_passwd_link
        reset_passwd_label = QtGui.QLabel(text, self)
        reset_passwd_label.setGeometry(300, 140, 130, 30)
        reset_passwd_label.linkActivated.connect(self._on_reset_passwd_label_clicked)
        reset_passwd_tips = 'CMCC user could send "p" to 12520 to reset password'
        reset_passwd_label.setToolTip(reset_passwd_tips)


        self.remember_me_checkbox = QtGui.QCheckBox("Remember me", self)
        self.remember_me_checkbox.setGeometry(40, 180, 140, 20)


        self.sign_in_btn = QtGui.QPushButton("Sign In", self)
        self.sign_in_btn.setGeometry(170, 210, 114, 32)


        report_bugs_link = '#'
        text = '<a href="%s">Report Bugs</a>' % report_bugs_link
        self.report_bugs_label = QtGui.QLabel(text, self)
        self.report_bugs_label.setGeometry(490, 210, 100, 30)
        self.report_bugs_label.linkActivated.connect(self.report_bugs_cb)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def report_bugs_cb(self, link):
#        webbrowser.open_new_tab(link)
        print "link:", link

    def _show_sign_up_dlg(self, link):
#        webbrowser.open_new_tab(link)
        print "link:", link
    
    def _on_reset_passwd_label_clicked(self, link):
#        webbrowser.open_new_tab(link)
        print "link:", link

    def _account_combox_currentIndexChanged(self, text):
        if not text:
            self.passwd_lineedit.setText("")
        else:
            pass


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = demo_oop_tpl
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
demo template

Tested environment:
    Mac OS X 10.6.8
"""
import sys

from PySide import QtCore, QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = demo_simple_tpl
import sys
from PySide import QtGui

app = QtGui.QApplication(sys.argv)

win = QtGui.QWidget()
x, y, w, h = 100, 100, 200, 50
win.setGeometry(x, y, w, h)
label = QtGui.QLabel("hello", win)
label.move(10, 10)

win.show()
win.raise_()

sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = copy_txt_of_btn_between_wins_in_dnd
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
copy the text of button from a window to b window in DND

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/dnd.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class DragWidget(QtGui.QPushButton):
    def __init__(self, parent=None):
        super(DragWidget, self).__init__('DND me', parent)

    def mousePressEvent(self, evt):
        if not self.geometry().contains(evt.pos()):
            return

        if evt.button() == QtCore.Qt.MouseButton.LeftButton:
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.text())

            drag = QtGui.QDrag(self)
            drag.setMimeData(mime_data)

#            drag.exec_() # show nothing while drag move
#            drag.exec_(QtCore.Qt.CopyAction) # show a `Plus/Copy icon' while drag move

            # These flags support drag it from PySide application internal to external.
            # for example, drag this into Finder on Mac OS X, it will auto creates a text file,
            # both file name and content are 'DND me'.
            drag.exec_(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)


class ChatWin(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ChatWin, self).__init__()
        self.demo = parent

        x, y, w, h = 200, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.setAcceptDrops(True)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, evt):
        evt.accept()
        if evt.mimeData().hasFormat('text/plain'):
            evt.accept()
        else:
            evt.ignore()

    def dropEvent(self, evt):
        evt.accept()
        mime_data = evt.mimeData()

        print 'text:', mime_data.data('text/plain')


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.btn = DragWidget(self)
        self.btn.move(10, 10)

        self.setAcceptDrops(True)

        self.chat_win = ChatWin(self)
        self.chat_win.show_and_raise()


    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, drag_enter_evt):
        mime_data = drag_enter_evt.mimeData()
        if mime_data.hasFormat('text/plain'):
            drag_enter_evt.acceptProposedAction()

    def dragMoveEvent(self, evt):
#        print 'dragMoveEvent', evt.pos()

        if self.btn.geometry().contains(evt.pos()):
            evt.ignore()

    def dropEvent(self, drop_evt):
        mime_data = drop_evt.mimeData()
        if not self.btn.geometry().contains(drop_evt.pos()) and \
            mime_data.hasFormat('text/plain'):

            print 'text:', mime_data.data('text/plain')

            drop_evt.accept()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = copy_txt_of_btn_in_dnd
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
copy the text of button in DND

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/dnd.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class DragWidget(QtGui.QPushButton):
    def __init__(self, parent=None):
        super(DragWidget, self).__init__('DND me', parent)

    def mousePressEvent(self, evt):
        if not self.geometry().contains(evt.pos()):
            return

        if evt.button() == QtCore.Qt.MouseButton.LeftButton:
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.text())

            drag = QtGui.QDrag(self)
            drag.setMimeData(mime_data)

#            drag.exec_() # show nothing while drag move
#            drag.exec_(QtCore.Qt.CopyAction) # show a `Plus/Copy icon' while drag move

            # These flags support drag it from PySide application internal to external.
            # for example, drag this into Finder on Mac OS X, it will auto creates a text file,
            # both file name and content are 'DND me'.
            drag.exec_(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.btn = DragWidget(self)
        self.btn.move(10, 10)

        self.setAcceptDrops(True)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, drag_enter_evt):
        mime_data = drag_enter_evt.mimeData()
        if mime_data.hasFormat('text/plain'):
            drag_enter_evt.acceptProposedAction()

    def dragMoveEvent(self, evt):
#        print 'dragMoveEvent', evt.pos()

        if self.btn.geometry().contains(evt.pos()):
            evt.ignore()

    def dropEvent(self, drop_evt):
        mime_data = drop_evt.mimeData()
        if not self.btn.geometry().contains(drop_evt.pos()) and \
            mime_data.hasFormat('text/plain'):

            print 'text:', mime_data.data('text/plain')

            drop_evt.accept()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = dnd_file_into_app_complex
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
DND file into application

Tested environment:
    Mac OS X 10.6.8

This script copy from official PySide/PyQt examples.
"""
import os
import sys

#PWD = os.path.dirname(os.path.realpath(__file__))
#parent_path = os.path.dirname(PWD)
#if parent_path not in sys.path:
#    sys.path.insert(0, parent_path)


from PySide import QtCore
from PySide import QtGui


class DropArea(QtGui.QLabel):
    def __init__(self, parent):
        super(DropArea, self).__init__(parent)

        self.setMinimumSize(200, 200)
#        self.setFrameStyle(QtGui.QFrame.Sunken | QtGui.QFrame.StyledPanel)
#        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)
        self.clear()

    def dragEnterEvent(self, evt):

        self.setText("<drop content>")
        self.setBackgroundRole(QtGui.QPalette.Highlight)

        evt.acceptProposedAction()
#        self.emit changed(evt.mimeData())
        self.emit(QtCore.SIGNAL("changed( QString )"), evt.mimeData())

    def dragMoveEvent(self, evt):
        evt.acceptProposedAction()

    def dropEvent(self, evt):
        mime_data = evt.mimeData()

        if mime_data.hasImage():
            self.setPixmap(mime_data.imageData())
        elif mime_data.hasHtml():
            self.setText(mime_data.html())
            self.setTextFormat(QtCore.Qt.RichText)
        elif mime_data.hasText():
            self.setText(mime_data.text())
            self.setTextFormat(QtCore.Qt.PlainText)
        elif mime_data.hasUrls():
            urls = mime_data.urls()

            text = ""

            for url in urls:
                text += url + " "

            self.setText(text)

        else:
            self.setText("Cannot display data")

        self.setBackgroundRole(QtGui.QPalette.Dark)
        evt.acceptProposedAction()

    def dragLeaveEvent(self, evt):
        self.clear()
        evt.accept()

    def clear(self):
        self.setText("<drop content>")
        self.setBackgroundRole(QtGui.QPalette.Dark)
        self.emit(QtCore.SIGNAL("changed()"))


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        buf = "This example accepts drags from other applications " + \
            "and displays the MIME types provided by the drag object."
        lab = QtGui.QLabel(buf, self)
        lab.setWordWrap(True)
        lab.adjustSize()

        dropArea = DropArea(self)
        self.connect(dropArea, QtCore.SIGNAL('changed(mime_data)'), self.updateFormatsTable)

        self.formatsTable = QtGui.QTableWidget(self)
        self.formatsTable.setColumnCount(2)
        self.formatsTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        labels = ('Format', 'Content')
        self.formatsTable.setHorizontalHeaderLabels(labels)
        self.formatsTable.horizontalHeader().setStretchLastSection(True)
        
            
        clearButton = QtGui.QPushButton("Clear")
        quitButton = QtGui.QPushButton("Quit")
    
        buttonBox = QtGui.QDialogButtonBox()
        buttonBox.addButton(clearButton, QtGui.QDialogButtonBox.ActionRole)
        buttonBox.addButton(quitButton, QtGui.QDialogButtonBox.RejectRole)

        quitButton.pressed.connect(self.close)
        self.connect(clearButton, QtCore.SIGNAL('pressed()'), dropArea, QtCore.SLOT('clear()'))

        mainLayout = QtGui.QVBoxLayout(self)
        mainLayout.addWidget(lab)
        mainLayout.addWidget(dropArea)
        mainLayout.addWidget(self.formatsTable)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
    
        self.setWindowTitle("Drop Site")
        self.setMinimumSize(350, 500)

    def updateFormatsTable(self, mime_data):
        self.formatsTable.setRowCount(0)

        if not mime_data:
            return

        for format in mime_data.formats():
            format_item = QtGui.QTableWidgetItem(format)
            format_item.setFlags(QtCore.Qt.ItemIsEnabled)
            format_item.setTextAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

            if format == 'text/plain':
                text = mime_data.text().simplified()
            elif format == 'text/html':
                text = mime_data.html().simplified()
            elif format == 'text/uri-list':
                text = ""
                for i in mime_data.urls():
                    text += ' ' + i
            else:
                text = 'binary data'

            row = self.formatsTable.rowCount()
            self.formatsTable.insertRow(row)
            self.formatsTable.setItem(row, 0, QtGui.QTableWidgetItem(format))
            self.formatsTable.setItem(row, 1, QtGui.QTableWidgetItem(text))

        self.formatsTable.resizeColumnsToContents(0)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = dnd_file_into_win
#!/usr/bin/env python
"""
DND file into window

Tested environment:
    Mac OS X 10.6.8
"""
import sys
import logging
from PySide import QtGui

logging.getLogger().setLevel(logging.DEBUG)


def print_data(mime_data, msg_prefix = ""):
    if mime_data.hasImage():
        msg = repr(mime_data.imageData())
    elif mime_data.hasHtml():
        msg = repr(mime_data.html())
    elif mime_data.hasText():
        msg = repr(mime_data.text())
    elif mime_data.hasUrls():
        msg = repr(mime_data.urls())
    else:
        raise Exception("unexpected mime data")

    logging.info(msg_prefix + msg)


class DropArea(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(DropArea, self).__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, evt):
#        mime_data = evt.mimeData()
#        print_data(mime_data)

        evt.acceptProposedAction()

    def dragMoveEvent(self, evt):
#        mime_data = evt.mimeData()
#        print_data(mime_data)

        evt.acceptProposedAction()

    def dropEvent(self, evt):
        mime_data = evt.mimeData()
        print_data(mime_data, msg_prefix="drop ")

        evt.acceptProposedAction()

    def dragLeaveEvent(self, evt):
#        mime_data = evt.mimeData()
#        print_data(mime_data)

        evt.accept()

    def main(self):
        self.show()
        self.raise_()


app = QtGui.QApplication(sys.argv)

win = DropArea()
win.main()

sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = export_txt_of_btn_in_dnd
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
copy the text of button from internal to external in DND

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/dnd.html
file:///opt/local/share/doc/qt4/html/dnd.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class DragWidget(QtGui.QPushButton):
    def __init__(self, parent=None):
        super(DragWidget, self).__init__('DND me', parent)

    def mousePressEvent(self, evt):
        if not self.geometry().contains(evt.pos()):
            return

        if evt.button() == QtCore.Qt.MouseButton.LeftButton:
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.text())

            drag = QtGui.QDrag(self)
            drag.setMimeData(mime_data)

#            drag.exec_() # show nothing while drag move
#            drag.exec_(QtCore.Qt.CopyAction) # show a `Plus/Copy icon' while drag move

            # These flags support drag it from PySide application internal to external.
            # for example, drag this into Finder on Mac OS X, it will auto creates a text file,
            # both file name and content are 'DND me'.
            drag.exec_(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.btn = DragWidget(self)
        self.btn.move(10, 10)

        self.setAcceptDrops(True)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, drag_enter_evt):
        mime_data = drag_enter_evt.mimeData()
        if mime_data.hasFormat('text/plain'):
            drag_enter_evt.acceptProposedAction()

    def dragMoveEvent(self, evt):
        print 'dragMoveEvent', evt.pos()

        if self.btn.geometry().contains(evt.pos()):
            evt.ignore()

    def dropEvent(self, drop_evt):
        mime_data = drop_evt.mimeData()
        if not self.btn.geometry().contains(drop_evt.pos()) and \
            mime_data.hasFormat('text/plain'):

            print 'text:', mime_data.data('text/plain')

            drop_evt.accept()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = move_btn_in_dnd
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
move a button in DND I

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/dnd.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class DragWidget(QtGui.QPushButton):
    def __init__(self, parent=None):
        super(DragWidget, self).__init__('DND me', parent)

    def mousePressEvent(self, evt):
        if evt.button() == QtCore.Qt.MouseButton.LeftButton:
            mime_data = QtCore.QMimeData()
            mime_data.setText(self.text())

            drag = QtGui.QDrag(self)
            drag.setMimeData(mime_data)
            drag.exec_(QtCore.Qt.MoveAction)


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.btn = DragWidget(self)
        self.btn.move(10, 10)

        self.setAcceptDrops(True)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, drag_enter_evt):
        mime_data = drag_enter_evt.mimeData()
        if mime_data.hasFormat('text/plain'):
            drag_enter_evt.acceptProposedAction()

    def dragMoveEvent(self, evt):
        print 'dragMoveEvent', evt.pos()

        self.btn.move(evt.pos())


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = hello
#/usr/bin/env python
import sys

from PySide import QtGui

app = QtGui.QApplication(sys.argv)

hello = QtGui.QLabel("hello Qt")
hello.show()
x, y, w, h = 100, 100, 100, 100
hello.setGeometry(x, y, w, h)

sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = show_full_width_form_punctuation
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
show Full width form punctuation

Tested environment:
    Mac OS X 10.6.8

http://developer.qt.nokia.com/forums/viewthread/12102/        
"""
import sys


try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

from PyQt4 import QtCore
from PyQt4 import QtGui

start = u'\u3001'
end = u'\u301E'
buf = ""
for i in xrange(ord(start), ord(end)):
#    print hex(i), unichr(i)
    buf += unichr(i)



buf = (
    u'\u3001',
    u'\u3002',
    u'\u300a',    
    u'\u300b',
    u'\u300d',
    u'\u300e',
    u'\u300f')
buf = '\n'.join(buf)

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        te = QtGui.QTextEdit(self)
        te.move(10, 10)

        te.setText(buf)

#        font = QtGui.QFont("STHeiti", 24)
#        te.setFont(font)

    def show_and_raise(self):
        self.show()
        self.raise_()



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = display_jpg_img
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
display jpeg image

Tested environment:
    Mac OS X 10.6.8
"""

import os
import sys

from PySide import QtGui

PWD = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(PWD)
IM_RES_PATH = os.path.join(os.path.dirname(parent_path), "image_resources")


file_path = os.path.join(IM_RES_PATH, "captcha.jpg")


app = QtGui.QApplication(sys.argv)

x, y, w, h = 100, 100, 200, 200
label = QtGui.QLabel()
label.setGeometry(x, y, w, h)
pixmap = QtGui.QPixmap(file_path)
label.setPixmap(pixmap)
label.move(10, 10)
label.show()

sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = display_png_file_with_grayscale
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
display png file with GrayScaled feature

Tested environment:
    Mac OS X 10.6.8
"""
import os
import sys
from PySide import QtGui

PWD = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(PWD)
IM_RES_PATH = os.path.join(os.path.dirname(parent_path), "image_resources")


def to_grayscaled(path):
    origin = QtGui.QPixmap(path)

    img = origin.toImage()
    for i in xrange(origin.width()):
        for j in xrange(origin.height()):
            col = img.pixel(i, j)
            gray = QtGui.qGray(col)
            img.setPixel(i, j, QtGui.qRgb(gray, gray, gray))

    dst = origin.fromImage(img)
    return dst


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        online_path = os.path.join(IM_RES_PATH, 'online-50x50.png')
        self.label = QtGui.QLabel('online', self)
        pix = QtGui.QPixmap(online_path)
        self.label.setPixmap(pix)
        self.label.move(10, 10)

        offline_path = os.path.join(IM_RES_PATH, 'offline-50x50.png')
        self.label = QtGui.QLabel('offline', self)
        pix = QtGui.QPixmap(offline_path)
        self.label.setPixmap(pix)
        self.label.move(10, 70)

        online_grayscale_path = os.path.join(IM_RES_PATH, 'online-50x50.png')
        self.label = QtGui.QLabel('offline', self)
        pix = to_grayscaled(online_grayscale_path)
        self.label.setPixmap(pix)
        self.label.move(10, 130)


    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = pil_to_qpixmap
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QPixmap load image by PIL, pil2qpixmap

Tested environment:
    Mac OS X 10.6.8

References

 - http://stackoverflow.com/questions/6756820/python-pil-image-tostring
 - http://qt-project.org/forums/viewthread/5866
"""
import os
import sys

from PIL import Image
from PySide import QtGui


PWD = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(PWD)
IM_RES_PATH = os.path.join(os.path.dirname(parent_path), "image_resources")
file_path = os.path.join(IM_RES_PATH, "captcha.jpg")


def pil2pixmap(file_path):
    im = Image.open(fp = file_path)
    if im.mode == "RGB":
        pass
    elif im.mode == "L":
        im = im.convert("RGBA")
    data = im.tostring('raw', "RGBA")
    qim = QtGui.QImage(data, im.size[0], im.size[1], QtGui.QImage.Format_ARGB32)
    pixmap = QtGui.QPixmap.fromImage(qim)
    return pixmap


app = QtGui.QApplication(sys.argv)

x, y, w, h = 100, 100, 200, 200
label = QtGui.QLabel()
label.setGeometry(x, y, w, h)

pixmap = pil2pixmap(file_path)
label.setPixmap(pixmap)

label.move(10, 10)
label.show()

sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = drawing_brush
#!/usr/bin/python
# -*- coding: utf-8 -*-

# brushes.py

import sys
from PySide import QtGui, QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()

        self.setGeometry(300, 300, 355, 280)
        self.setWindowTitle('Brushes')

    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
        
        qp.begin(self)
        self.drawBrushes(qp)
        qp.end()
        
    def drawBrushes(self, qp):

        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        qp.setBrush(brush)
        qp.drawRect(10, 15, 90, 60)

        brush.setStyle(QtCore.Qt.Dense1Pattern)
        qp.setBrush(brush)
        qp.drawRect(130, 15, 90, 60)

        brush.setStyle(QtCore.Qt.Dense2Pattern)
        qp.setBrush(brush)
        qp.drawRect(250, 15, 90, 60)

        brush.setStyle(QtCore.Qt.Dense3Pattern)
        qp.setBrush(brush)
        qp.drawRect(10, 105, 90, 60)

        brush.setStyle(QtCore.Qt.DiagCrossPattern)
        qp.setBrush(brush)
        qp.drawRect(10, 105, 90, 60)

        brush.setStyle(QtCore.Qt.Dense5Pattern)
        qp.setBrush(brush)
        qp.drawRect(130, 105, 90, 60)

        brush.setStyle(QtCore.Qt.Dense6Pattern)
        qp.setBrush(brush)
        qp.drawRect(250, 105, 90, 60)

        brush.setStyle(QtCore.Qt.HorPattern)
        qp.setBrush(brush)
        qp.drawRect(10, 195, 90, 60)

        brush.setStyle(QtCore.Qt.VerPattern)
        qp.setBrush(brush)
        qp.drawRect(130, 195, 90, 60)

        brush.setStyle(QtCore.Qt.BDiagPattern)
        qp.setBrush(brush)
        qp.drawRect(250, 195, 90, 60)


app = QtGui.QApplication(sys.argv)
ex = Example()
ex.show()
app.exec_()
########NEW FILE########
__FILENAME__ = drawing_color
#!/usr/bin/python
# -*- coding: utf-8 -*-

# colors.py

import sys, random
from PySide import QtGui, QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()

        self.setGeometry(300, 300, 350, 280)
        self.setWindowTitle('Colors')

    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
        qp.begin(self)
        
        self.drawRectangles(qp)
        
        qp.end()
        
    def drawRectangles(self, qp):

        color = QtGui.QColor(0, 0, 0)
        color.setNamedColor('#d4d4d4')
        qp.setPen(color)

        qp.setBrush(QtGui.QColor(255, 0, 0, 80))
        qp.drawRect(10, 15, 90, 60)

        qp.setBrush(QtGui.QColor(255, 0, 0, 160))
        qp.drawRect(130, 15, 90, 60)

        qp.setBrush(QtGui.QColor(255, 0, 0, 255))
        qp.drawRect(250, 15, 90, 60)

        qp.setBrush(QtGui.QColor(10, 163, 2, 55))
        qp.drawRect(10, 105, 90, 60)

        qp.setBrush(QtGui.QColor(160, 100, 0, 255))
        qp.drawRect(130, 105, 90, 60)

        qp.setBrush(QtGui.QColor(60, 100, 60, 255))
        qp.drawRect(250, 105, 90, 60)

        qp.setBrush(QtGui.QColor(50, 50, 50, 255))
        qp.drawRect(10, 195, 90, 60)

        qp.setBrush(QtGui.QColor(50, 150, 50, 255))
        qp.drawRect(130, 195, 90, 60)

        qp.setBrush(QtGui.QColor(223, 135, 19, 255))
        qp.drawRect(250, 195, 90, 60)


app = QtGui.QApplication(sys.argv)
ex = Example()
ex.show()
app.exec_()
########NEW FILE########
__FILENAME__ = drawing_pen
#!/usr/bin/python
# -*- coding: utf-8 -*-

# penstyles.py

import sys
from PySide import QtGui, QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()

        self.setGeometry(300, 300, 280, 270)
        self.setWindowTitle('penstyles')

    def paintEvent(self, e):
      
        qp = QtGui.QPainter()

        qp.begin(self)        
        self.doDrawing(qp)        
        qp.end()
        
    def doDrawing(self, qp):

        pen = QtGui.QPen(QtCore.Qt.black, 2, QtCore.Qt.SolidLine)

        qp.setPen(pen)
        qp.drawLine(20, 40, 250, 40)

        pen.setStyle(QtCore.Qt.DashLine)
        qp.setPen(pen)
        qp.drawLine(20, 80, 250, 80)

        pen.setStyle(QtCore.Qt.DashDotLine)
        qp.setPen(pen)
        qp.drawLine(20, 120, 250, 120)

        pen.setStyle(QtCore.Qt.DotLine)
        qp.setPen(pen)
        qp.drawLine(20, 160, 250, 160)

        pen.setStyle(QtCore.Qt.DashDotDotLine)
        qp.setPen(pen)
        qp.drawLine(20, 200, 250, 200)

        pen.setStyle(QtCore.Qt.CustomDashLine)
        pen.setDashPattern([1, 4, 5, 4])
        qp.setPen(pen)
        qp.drawLine(20, 240, 250, 240)
        

app = QtGui.QApplication(sys.argv)
ex = Example()
ex.show()
app.exec_()
########NEW FILE########
__FILENAME__ = drawing_points
#!/usr/bin/python
# -*- coding: utf-8 -*-

# points.py

import sys, random
from PySide import QtGui, QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Points')

    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawPoints(qp)
        qp.end()
        
    def drawPoints(self, qp):
      
        qp.setPen(QtCore.Qt.red)
        size = self.size()
        
        for i in range(1000):
            x = random.randint(1, size.width()-1)
            y = random.randint(1, size.height()-1)
            qp.drawPoint(x, y)

app = QtGui.QApplication(sys.argv)
ex = Example()
ex.show()
app.exec_()
########NEW FILE########
__FILENAME__ = drawing_txt
#!/usr/bin/python
# -*- coding: utf-8 -*-

# drawtext.py

import sys
from PySide import QtGui, QtCore


class Example(QtGui.QWidget):
  
    def __init__(self):
        super(Example, self).__init__()
        
        self.initUI()
        
    def initUI(self):

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Draw Text')

        self.text = u'中文天下'

    def paintEvent(self, event):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawText(event, qp)
        qp.end()


    def drawText(self, event, qp):
      
        qp.setPen(QtGui.QColor(168, 34, 3))
        qp.setFont(QtGui.QFont('Decorative', 20))
        qp.drawText(event.rect(), QtCore.Qt.AlignCenter, self.text)

app = QtGui.QApplication(sys.argv)
ex = Example()
ex.show()
app.exec_()
########NEW FILE########
__FILENAME__ = get_supported_image_formats
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
get PySide supported image formats

If it doesn't contains 'jpeg'/'jpg', you have to re-install jpeg/openjpeg and qt packages

    brew install jpeg
    brew install openjpeg
    brew install qt

Tested environment:
    Mac OS X 10.6.8
"""

from PySide import QtGui

fmts = [str(i) for i in QtGui.QImageReader.supportedImageFormats()]
print fmts
########NEW FILE########
__FILENAME__ = qaction
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QAction and QKeySequence demo

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qwidget.html#events
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        del_contact = "Ctrl+Shift+d"
        key_seq = QtGui.QKeySequence(del_contact)

        act = QtGui.QAction(self)
        act.setShortcut(key_seq)
        
        self.addAction(act)
        act.triggered.connect(self._short_cut_cb)

    def _short_cut_cb(self):
        print "_short_cut_cb"


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = listen_key
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
listen key

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qwidget.html#events
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def keyPressEvent(self, evt):
        key = evt.key()
        modifier = evt.modifiers()
        DELETE_BUDDY = (modifier == QtCore.Qt.ControlModifier) and (key == QtCore.Qt.Key_Backspace)

        if DELETE_BUDDY:
            print 'pressed CMD - delete'

    def mouseDoubleClickEvent(self, evt):
        print "mouseDoubleClickEvent"


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = listen_left_click_on_label
#!/usr/bin/python
# -*- coding: utf-8 -*-
from functools import wraps
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


def left_click(func, parent):
    @wraps(func)
    def wrapper(evt):
        QtGui.QLabel.mousePressEvent(parent, evt)
        if evt.button() == QtCore.Qt.LeftButton:
            parent.emit(QtCore.SIGNAL('leftClicked()'))
        func(evt)
    return wrapper


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        pic_path = ""
        pix = QtGui.QPixmap(pic_path)

        label = QtGui.QLabel()
        label.move(10, 10)
        label.setPixmap(pix)
        label.mousePressEvent = left_click(label.mousePressEvent, label)

        self.connect(label, QtCore.SIGNAL('leftClicked()'), self.on_left_clicked)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def on_left_clicked(self):
        print 'left clicked'


def main():
    app = QtGui.QApplication(sys.argv)
    demo = Demo()
    demo.show_and_raise()
    app.exec_()


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = qshortcut
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
shortcut

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        btn = QtGui.QToolButton(self)
        btn.setGeometry(10, 10, 100, 100)
        btn.clicked.connect(self._act_cb)

        del_contact = "Ctrl+Shift+h"

        # it couldn't catch delete by default
#        del_contact = "Ctrl+Shift+Delete"

        key_seq = QtGui.QKeySequence(del_contact)
        btn.setShortcut(key_seq)

    def _act_cb(self):
        print "_act_cb"

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = absolute_position_layout
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Absolute position layout demo

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 100
        self.setGeometry(x, y, w, h)


        label1 = QtGui.QLabel('hello', self)
        x, y = 10, 10
        label1.move(x, y)
        label1.resize(200, 30)


        text = str(label1.frameSize())
        label1.setText(text)

        # PySide.QtCore.QSize(200, 30) --> x, y
        print 'label1:', text


        label2 = QtGui.QLabel('world', self)
        x, y = 20, 40
        label2.move(x, y)
        label2.resize(300, 30)

        text = str(label2.geometry())
        label2.setText(text)

        # PySide.QtCore.QRect(20, 40, 300, 30) --> x, y, w, h
        print 'label2:', text


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    app.exec_()


########NEW FILE########
__FILENAME__ = auto_adjust_size_to_fit_img
#!/usr/bin/env python
"""
demo template

Tested environment:
    Mac OS X 10.6.8
"""
import os, sys
from PySide import QtCore, QtGui

PWD = os.path.dirname(os.path.realpath(__file__))
img_res_prefix = os.path.join(os.path.dirname(PWD), "image_resources")

files = [
    os.path.join(img_res_prefix, "Mac.png"),
    os.path.join(img_res_prefix, "Ubuntu.png"),
    ]
g_cursor = 0

def get_next_img_file_path():
    global g_cursor
    g_cursor += 1
    if g_cursor == 2:
        g_cursor = 0
    return files[g_cursor]

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 400, 400
        self.setGeometry(x, y, w, h)
        self.setStyleSheet("QLabel { border: 1px solid red; }")

        self.label = QtGui.QLabel("hello", self)
        self.label.move(20, 20)

        self.btn = QtGui.QPushButton("switch without adjusting size", self)
        self.btn.clicked.connect(self._btn_cb)
        self.btn.move(50, 300)

        self.btn_adjust = QtGui.QPushButton("switch with adjusting size", self)
        self.btn_adjust.clicked.connect(self._btn_adjust_cb)
        self.btn_adjust.move(50, 350)

    def _btn_cb(self, *args, **kwargs):
        pix = QtGui.QPixmap(get_next_img_file_path())

        print "QPixmap size = ", pix.size()
        print "QLabel size = ", self.label.size()
        self.label.setPixmap(pix)
        print "QLabel size (setPixmap called) = ", self.label.size()

    def _btn_adjust_cb(self, *args, **kwargs):
        pix = QtGui.QPixmap(get_next_img_file_path())

        print "QPixmap size = ", pix.size()
        print "QLabel size = ", self.label.size()
        self.label.setPixmap(pix)
        self.label.adjustSize()
        print "QLabel size (setPixmap && adjustSize called) = ", self.label.size()

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = central_widget_in_main_win
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Central widget in main window

Tested environment:
    Mac OS X 10.6.8


http://www.pyside.org/docs/pyside/PySide/QtGui/QMainWindow.html#qt-main-window-framework
http://doc.qt.nokia.com/latest/qmainwindow.html#qt-main-window-framework
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

    
class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        textEdit = QtGui.QTextEdit(self)
        self.setCentralWidget(textEdit)


    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = custom_margin_spacing
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom margin and spacing of box layout

Tested environment:
    Mac OS X 10.6.8


http://doc.qt.nokia.com/latest/layout.html
http://doc.qt.nokia.com/latest/qlayout.html

http://www.pyside.org/docs/pyside/PySide/QtGui/QLayout.html
"""
import os
import sys

PWD = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(PWD)
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        vbox = QtGui.QVBoxLayout(self)

        chat_history = QtGui.QTextEdit(self)
        w, h = 100, 100
        chat_history.setMinimumSize(w, h)
        vbox.addWidget(chat_history)

        input_win = QtGui.QTextEdit(self)
        w, h = 100, 100
        input_win.setMinimumSize(w, h)
        vbox.addWidget(input_win)


        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)

        self.setLayout(vbox)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = horizontolly_layout
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
horizontally layout

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        hbox = QtGui.QHBoxLayout(self)

        btn1 = QtGui.QPushButton('btn 1', self)
        hbox.addWidget(btn1)

        btn2 = QtGui.QPushButton('btn 2', self)
        hbox.addWidget(btn2)

        btn3 = QtGui.QPushButton('btn 3', self)
        hbox.addWidget(btn3)

        btn4 = QtGui.QPushButton('btn 4', self)
        hbox.addWidget(btn4)

        self.setLayout(hbox)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = layout_in_box_with_attr_stretch
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
layout in box with attribute stretch demo

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore4
    from PyQt4 import QtGui


class Demo(QtGui.QDialog):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        vbox = QtGui.QVBoxLayout()


        hbox1 = QtGui.QHBoxLayout()
        vbox.addLayout(hbox1)

        a_btn = QtGui.QPushButton('A')
        hbox1.addWidget(a_btn)

        b_btn = QtGui.QPushButton('B')
        hbox1.addWidget(b_btn)


        hbox2 = QtGui.QHBoxLayout()
        vbox.addLayout(hbox2)

#        使用 QHBoxLayout 布局，默认是左右平均分布放置
#        设置 Stretch 属性后，两个按钮会靠右放置，而且随着窗口大小的改变，也是靠右
        hbox2.addStretch()

        c_btn = QtGui.QPushButton('C')
        hbox2.addWidget(c_btn)

        d_btn = QtGui.QPushButton('D')
        hbox2.addWidget(d_btn)
        

        self.setLayout(vbox)
        
    def show_and_raise(self):
        self.show()
        self.raise_()

        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show()

    app.exec_()


########NEW FILE########
__FILENAME__ = layout_in_form
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
layout in form

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        form = QtGui.QFormLayout(self)

        name_label = QtGui.QLabel("Name", self)
        name_lineedit = QtGui.QLineEdit(self)
        form.addRow(name_label, name_lineedit)

        age_label = QtGui.QLabel("Age", self)
        age_lineedit = QtGui.QLineEdit(self)
        form.addRow(age_label, age_lineedit)

        location_label = QtGui.QLabel("Location", self)
        location_lineedit = QtGui.QLineEdit(self)
        form.addRow(location_label, location_lineedit)


        self.setLayout(form)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = layout_in_grid
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
lay out in Gird demo

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        title = QtGui.QLabel('Title')
        author = QtGui.QLabel('Author')
        review = QtGui.QLabel('Review')

        titleEdit = QtGui.QLineEdit()
        authorEdit = QtGui.QLineEdit()
        reviewEdit = QtGui.QTextEdit()

        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(title, 1, 0)
        grid.addWidget(titleEdit, 1, 1)

        grid.addWidget(author, 2, 0)
        grid.addWidget(authorEdit, 2, 1)

        grid.addWidget(review, 3, 0)
        grid.addWidget(reviewEdit, 3, 1, 5, 1)
        
        self.setLayout(grid)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = layout_in_nest
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
layout in nest

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class BeNestWidget(QtGui.QWidget):
    def __init__(self, container):
        super(BeNestWidget, self).__init__()

        container.addWidget(self)

        hbox = QtGui.QHBoxLayout(self)

        a_btn = QtGui.QPushButton("d", self)
        hbox.addWidget(a_btn)

        b_tn = QtGui.QPushButton("e", self)
        hbox.addWidget(b_tn)

        c_btn = QtGui.QPushButton("f", self)
        hbox.addWidget(c_btn)

        self.setLayout(hbox)


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        vbox = QtGui.QVBoxLayout(self)

        a_btn = QtGui.QPushButton("a", self)
        vbox.addWidget(a_btn)

        b_tn = QtGui.QPushButton("b", self)
        vbox.addWidget(b_tn)

        c_btn = QtGui.QPushButton("c", self)
        vbox.addWidget(c_btn)

        self.bn_widget = BeNestWidget(container = vbox)


        self.setLayout(vbox)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = spacer_Item
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
QSpacerItem demo

Tested environment:
    Mac OS X 10.6.8
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QDialog):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)
        
        hbox = QtGui.QHBoxLayout()
        
        a_btn = QtGui.QPushButton('a')
        hbox.addWidget(a_btn)

        hbox.addSpacerItem(QtGui.QSpacerItem(100, 50))

        b_btn = QtGui.QPushButton('b')
        hbox.addWidget(b_btn)

        style = "QPushButton { border: 3px solid red }; "
        self.setStyleSheet(style)
                
        self.setLayout(hbox)
        
    def show_and_raise(self):
        self.show()
        self.raise_()

        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show()

    app.exec_()


########NEW FILE########
__FILENAME__ = vertically_layout
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
vertically layout demo

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        vbox = QtGui.QVBoxLayout(self)

        btn1 = QtGui.QPushButton('btn 1', self)
        vbox.addWidget(btn1)

        btn2 = QtGui.QPushButton('btn 2', self)
        vbox.addWidget(btn2)

        btn3 = QtGui.QPushButton('btn 3', self)
        vbox.addWidget(btn3)

        btn4 = QtGui.QPushButton('btn 4', self)
        vbox.addWidget(btn4)

        self.setLayout(vbox)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = contact_locator
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
contact list locator

Tested environment:
    Mac OS X 10.6.8

"""
import re
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


datas_ = (
    ('C', 'c.png', 'c'),
    ('C#', 'csharp.png', 'csharp'),
    ('Lisp', 'lisp.png', 'lisp'),
    ('Objective-C', 'objc.png', 'objc'),
    ('Perl', 'perl.png', 'perl'),
    ('Ruby', 'ruby.png', 'ruby'),
    ('Python', 'python.png', 'py'),
    ('Java', 'java.png', 'java'),
    ('JavaScript', 'javascript.png', 'js')
)


class Magic:
    def __init__(self, fullname, icon_path, pid):
        self.fullname = fullname
        self.icon_path = icon_path
        self.pid = pid
    
    def __repr__(self):
        return "<Magic %s>" % self.fullname

    
class MagicBox(object):
    def __init__(self):
        self._magics = set()

        for i in datas_:
            fullname, logo_path, pid = i[0], i[1], i[2]
            magic = Magic(fullname, logo_path, pid)
            self._magics.add(magic)
            
        self._cache = list(self._magics)

    @property
    def magics_count(self):
        return len(self._magics)

    @property
    def all_magics(self):
        return self._magics
    
    @property
    def magics(self):
        return self._cache

    def filter_list_by_keyword(self, keyword):
        self._cache = [i
                      for i in self._magics
                          if i.fullname.find(keyword) != -1 or \
                             re.match(keyword, i.fullname, re.I)]


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, magic_box):
        super(ListModel, self).__init__()
        self.magic_box = magic_box

    def rowCount(self, parent):
        return len(self.magic_box.magics)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        magic = self.magic_box.magics[index.row()]
        fullname, icon_path, user_data = magic.fullname, magic.icon_path, magic.pid

        if role == QtCore.Qt.DisplayRole:
            return fullname

        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(icon_path)

#        elif role == QtCore.Qt.BackgroundColorRole:
#            return QtGui.QBrush(QtGui.QColor("#d4d4d4"))

        return None


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.magic_box = MagicBox()

        
        self.lineedit = QtGui.QLineEdit(self)
        self.lineedit.resize(200, 30)
        self.lineedit.move(10, 10)

        self.lineedit.returnPressed.connect(self._lineedit_returnPressed)
        self.lineedit.textChanged.connect(self._lineedit_textChanged)

            
        self.list_view = QtGui.QListView(self)
        self.list_view.setGeometry(10, 50, 280, 300)
        
        self.list_model = ListModel(self.magic_box)
        self.list_view.setModel(self.list_model)

    def _lineedit_textChanged(self, text):
        print "text changed:", text

        self.magic_box.filter_list_by_keyword(text)
        self.list_view.update()

    def _lineedit_returnPressed(self):
        text = self.lineedit.text()

        print "return press:", text
        print "magics:", self.magic_box.magics


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())



########NEW FILE########
__FILENAME__ = editable_listview
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
editable item in QListView

Tested environment:
    Mac OS X 10.6.8

http://developer.qt.nokia.com/doc/qt-4.7/qabstractlistmodel.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

    

class ListModel(QtCore.QAbstractListModel):
    def __init__(self, data_items):
        super(ListModel, self).__init__()
        self.data_items = data_items

    def rowCount(self, parent):
        return len(self.data_items)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        name = self.data_items[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return name

        return None

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            row = index.row()
            self.data_items[row] = value

        return super(ListModel, self).setData(index, value, role)


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.list_view = QtGui.QListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

        data_sources = ['a', 'b', 'c']
        list_model = ListModel(data_sources)
        self.list_view.setModel(list_model)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = simple_listview_with_icon
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom QListView

This script demonstrates
 - custom icon for item
 - construct a container for simple file manager(such as Finder/Explorer/Nautilus)

Tested environment:
    Mac OS X 10.6.8

Docs
 - http://www.pyside.org/docs/pyside/PySide/QtGui/QAbstractItemView.html
 - http://www.pyside.org/docs/pyside/PySide/QtGui/QListView.html
 - http://doc.qt.nokia.com/latest/model-view-programming.html
"""
import glob
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None


def create_data_source():
    logos = glob.glob('*.png')
    return [(os.path.splitext(i)[0], i) for i in logos]


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.list_view = QtGui.QListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

        self.data_sources = create_data_source()
        list_model = ListModel(self.data_sources)
        self.list_view.setModel(list_model)

        # size
        self.list_view.setIconSize(QtCore.QSize(50, 50))
        self.list_view.setSpacing(5)
        self.list_view.setUniformItemSizes(True)

        # view mode
        # uncomment follow line, to construct a container for simple file manager(such as Finder/Explorer/Nautilus)
#        self.list_view.setViewMode(QtGui.QListView.IconMode)

        # interactive
#        self.list_view.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.list_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)


    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = simple_listview_with_icon_filter
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom QListView


This script demonstrates

 - custom icon for item
 - change item data at runtime

Tested environment:
    Mac OS X 10.6.8

Docs
 - http://www.pyside.org/docs/pyside/PySide/QtGui/QAbstractItemView.html
 - http://www.pyside.org/docs/pyside/PySide/QtGui/QListView.html
 - http://doc.qt.nokia.com/latest/model-view-programming.html
"""
import glob
import os
import sys

#try:
#    from PySide import QtCore
#    from PySide import QtGui
#except ImportError:
#    from PyQt4 import QtCore
#    from PyQt4 import QtGui

from PyQt4 import QtCore
from PyQt4 import QtGui


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
#        print ">>> rowCount"
#        print 'parent:', parent,
#        print ', row:', parent.row(),
#        print ', column:', parent.column(),
#        print ', internalPointer:', parent.internalPointer()
        
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
#        print ">>> data"
#        print 'isValid:', index.isValid(),
#        print ', row:', index.row(),
#        print ', column:', index.column(),
#        print ', is Qt.DisplayRole:', role == QtCore.Qt.DisplayRole

        if not index.isValid():
            return None

        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None


def create_data_source():
    logos = glob.glob('*.png')
    return [(os.path.splitext(i)[0], i) for i in logos]


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.list_view = QtGui.QListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

        self.data_sources = create_data_source()
        list_model = ListModel(self.data_sources)
        self.list_view.setModel(list_model)

        # size
        self.list_view.setIconSize(QtCore.QSize(50, 50))
        self.list_view.setSpacing(5)
        self.list_view.setUniformItemSizes(True)

        # view
#        self.list_view.setViewMode(QtGui.QListView.IconMode)

        # interactive
        self.list_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        # more advanced controlling on selection
#        self.selection_model = self.list_view.selectionModel()
#        self.selection_model.currentChanged.connect(self._selection_model_currentChanged)


        self.lineedit = QtGui.QLineEdit(self)
        self.lineedit.move(5, 260)
        self.lineedit.textEdited.connect(self._lineedit_textEdited)


    def _lineedit_textEdited(self, text):
        if not text:
            self.list_view.clearSelection()
        else:
            self.list_view.keyboardSearch(text)
            idx = self.list_view.currentIndex()
            if idx.isValid():
                if len(self.data_sources) - 1 >= idx.row():
                    self.data_sources.pop(idx.row())
                    self.list_view.update()

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = get_dropped_item_modelindex_in_listview
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Get dropped item's ModelIndex in QListView

Tested environment:
    Mac OS X 10.6.8

Docs

 - http://doc.qt.nokia.com/latest/model-view-programming.html#using-drag-and-drop-with-item-views
 - file:///opt/local/share/doc/qt4/html/qabstractitemmodel.html#dropMimeData
"""
import glob
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None

    def flags(self, idx):
        if idx.isValid():
            return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def dropMimeData(self, data, action, row, column, parent_idx):
        """
        NOTICE: Although the specified row, column
        and parent indicate the location of an item in the model where the operation ended,
        it is the responsibility of the view to
        provide a suitable location for where the data should be inserted.
        """
#        print data, action, row, column, parent_idx
        return super(ListModel, self).dropMimeData(data, action, row, column, parent_idx)

    def mimeData(self, idxes):
        # NOTE: create mime data from ancestor method for fixed crash bug on PySide
        mime_data = super(ListModel, self).mimeData(idxes)

        encoded_data = ""

        for idx in idxes:
            if idx.isValid():
                encoded_data += '\r\n' + self.data(idx, role = QtCore.Qt.DisplayRole)

        mime_data.setData('text/plain', encoded_data)

        return mime_data



class ListView(QtGui.QListView):
    def __init__(self, parent=None):
        super(ListView, self).__init__(parent)

        self.data_sources = create_data_source()
        list_model = ListModel(self.data_sources)
        self.setModel(list_model)

        # size
        self.setIconSize(QtCore.QSize(50, 50))
        self.setSpacing(5)
        self.setUniformItemSizes(True)

        # view
        self.setDropIndicatorShown(True)

        # interactive in DND mode
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def dropEvent(self, evt):
        mime_data = evt.mimeData()

        if mime_data.hasFormat('text/plain'):
            buf = mime_data.data('text/plain')
            print "source == self:", evt.source() == self
            print 'mime data:', repr(buf)

            target_idx = self.indexAt(evt.pos())
            print "dropped at row:%d, col:%d:" % (target_idx.row(), target_idx.column())

        return super(ListView, self).dropEvent(evt)


def create_data_source():
    logos = glob.glob('*.png')
    return [(os.path.splitext(i)[0], i) for i in logos]


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.list_view = ListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = listview
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom QListView

This script demonstrates

 - DND item
 - sort item

Tested environment:
    Mac OS X 10.6.8

Docs

 - http://doc.qt.nokia.com/latest/model-view-programming.html#using-drag-and-drop-with-item-views

 - Qt - QAbstractItemView, PySide - QListView
 - Qt - QAbstractItemModel, PySide - QAbstractItemModel
"""
import glob
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None

    def flags(self, idx):
        if idx.isValid():
            return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, idxes):
        # NOTE: create mime data from ancestor method for fixed crash bug on PySide
        mime_data = super(ListModel, self).mimeData(idxes)

        encoded_data = ""

        for idx in idxes:
            if idx.isValid():
                encoded_data += '\r\n' + self.data(idx, role = QtCore.Qt.DisplayRole)

        mime_data.setData('text/plain', encoded_data)

        return mime_data



class ListView(QtGui.QListView):
    def __init__(self, parent=None):
        super(ListView, self).__init__(parent)

        self.data_sources = create_data_source()
        list_model = ListModel(self.data_sources)
        self.setModel(list_model)

        # size
        self.setIconSize(QtCore.QSize(50, 50))
        self.setSpacing(5)
        self.setUniformItemSizes(True)

        # view
        self.setDropIndicatorShown(True)

        # interactive in DND mode
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def dropEvent(self, evt):
        mime_data = evt.mimeData()

        if mime_data.hasFormat('text/plain'):
            buf = mime_data.data('text/plain')
            print 'pos:', evt.pos()
            print "source == self:", evt.source() == self
            print 'mime data:', repr(buf)

        return super(ListView, self).dropEvent(evt)


def create_data_source():
    logos = glob.glob('*.png')
    return [(os.path.splitext(i)[0], i) for i in logos]


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.list_view = ListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = listview_with_bugs
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom QListView


This script demonstrates

 - DND item
 - sort item

Tested environment:
    Mac OS X 10.6.8

Docs

 - http://doc.qt.nokia.com/latest/model-view-programming.html#using-drag-and-drop-with-item-views

 - Qt - QAbstractItemView, PySide - QListView
 - Qt - QAbstractItemModel, PySide - QAbstractItemModel


"""
import glob
import os
import sys

#try:
#    from PySide import QtCore
#    from PySide import QtGui
#except ImportError:
#    from PyQt4 import QtCore
#    from PyQt4 import QtGui

from PyQt4 import QtCore
from PyQt4 import QtGui


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None

    def flags(self, idx):
        if idx.isValid():
            return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    # DND
    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, idxes):
        super(ListModel, self).mimeData(idxes)

        mime_data = QtCore.QMimeData()

        encoded_data = ""

        for idx in idxes:
            if idx.isValid():
                encoded_data += '\r\n' + self.data(idx, role = QtCore.Qt.DisplayRole)

        mime_data.setData('text/plain', encoded_data)

        return mime_data


class ListView(QtGui.QListView):
    def __init__(self, parent=None):
        super(ListView, self).__init__(parent)

        self.data_sources = create_data_source()
        list_model = ListModel(self.data_sources)
        self.setModel(list_model)

        # size
        self.setIconSize(QtCore.QSize(50, 50))
        self.setSpacing(5)
        self.setUniformItemSizes(True)

        # view
        self.setDropIndicatorShown(True)

        # interactive in DND mode
        self.setMovement(QtGui.QListView.Free)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, evt):
        if evt.mimeData().hasFormat('text/plain'):
            print self.childAt(evt.pos())
            
            if evt.source() == self:
                evt.setDropAction(QtCore.Qt.MoveAction)
                evt.accept()
            else:
                evt.acceptProposedAction()
        else:
            evt.ignore()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, evt):
        evt.accept()
        mime_data = evt.mimeData()

        print mime_data.data('text/plain')


def create_data_source():
    logos = glob.glob('*.png')
    return [(os.path.splitext(i)[0], i) for i in logos]


class ChatWin(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ChatWin, self).__init__()
        self.demo = parent

        x, y, w, h = 200, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.setAcceptDrops(True)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, evt):
        evt.accept()
        if evt.mimeData().hasFormat('text/plain'):
            evt.accept()
        else:
            evt.ignore()

    def dropEvent(self, evt):
        evt.accept()
        mime_data = evt.mimeData()
        
        print mime_data.data('text/plain')

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.list_view = ListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

        self.lineedit = QtGui.QLineEdit(self)
        self.lineedit.move(5, 260)
        self.lineedit.textEdited.connect(self._lineedit_textEdited)


        self.chat_win = ChatWin(self)
        self.chat_win.show_and_raise()


    def _lineedit_textEdited(self, text):
        if not text:
            self.list_view.clearSelection()
        else:
            self.list_view.keyboardSearch(text)
            idx = self.list_view.currentIndex()

            if idx.isValid():
                if len(self.list_view.data_sources) - 1 >= idx.row():
                    self.list_view.data_sources.pop(idx.row())
                    self.list_view.update()

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = listview_with_dnd
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Custom QListView

This script demonstrates
 - DND item
 - DND item from window A to window B

Tested environment:
    Mac OS X 10.6.8

Docs

 - http://doc.qt.nokia.com/latest/model-view-programming.html#using-drag-and-drop-with-item-views

 - Qt - QAbstractItemView, PySide - QListView
 - Qt - QAbstractItemModel, PySide - QAbstractItemModel
 - PySide - QMimeData

"""
import glob
import os
import sys

#try:
#    from PySide import QtCore
#    from PySide import QtGui
#except ImportError:
#    from PyQt4 import QtCore
#    from PyQt4 import QtGui

from PyQt4 import QtCore
from PyQt4 import QtGui


class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None

    def flags(self, idx):
        if idx.isValid():
            return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsDropEnabled |\
                   QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    # DND
    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, idxes):
        super(ListModel, self).mimeData(idxes)

        mime_data = QtCore.QMimeData()

        encoded_data = ""

        for idx in idxes:
            if idx.isValid():
                encoded_data += '\r\n' + self.data(idx, role = QtCore.Qt.DisplayRole)

        mime_data.setData('text/plain', encoded_data)

        return mime_data


class ListView(QtGui.QListView):
    def __init__(self, parent=None):
        super(ListView, self).__init__(parent)

        self.data_sources = create_data_source()
        list_model = ListModel(self.data_sources)
        self.setModel(list_model)

        # size
        self.setIconSize(QtCore.QSize(50, 50))
        self.setSpacing(5)
        self.setUniformItemSizes(True)

        # view
        self.setDropIndicatorShown(True)

        # interactive in DND mode
        self.setMovement(QtGui.QListView.Free)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)

#    def dragEnterEvent(self, evt):
#        evt.accept()
#        if evt.mimeData().hasFormat('text/plain'):
#            evt.accept()
#        else:
#            evt.ignore()
#
#    def dropEvent(self, evt):
#        evt.accept()
#        mime_data = evt.mimeData()
#
#        print mime_data.data('text/plain')


def create_data_source():
    logos = glob.glob('*.png')
    return [(os.path.splitext(i)[0], i) for i in logos]


class ChatWin(QtGui.QWidget):
    def __init__(self, parent=None):
        super(ChatWin, self).__init__()
        self.demo = parent

        x, y, w, h = 200, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.setAcceptDrops(True)

    def show_and_raise(self):
        self.show()
        self.raise_()

    def dragEnterEvent(self, evt):
        evt.accept()
        if evt.mimeData().hasFormat('text/plain'):
            evt.accept()
        else:
            evt.ignore()

    def dropEvent(self, evt):
        evt.accept()
        mime_data = evt.mimeData()
        
        print mime_data.data('text/plain')

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        self.list_view = ListView(self)
        x, y, w, h = 5, 5, 290, 250
        self.list_view.setGeometry(x, y, w, h)

        self.lineedit = QtGui.QLineEdit(self)
        self.lineedit.move(5, 260)
        self.lineedit.textEdited.connect(self._lineedit_textEdited)


        self.chat_win = ChatWin(self)
        self.chat_win.show_and_raise()


    def _lineedit_textEdited(self, text):
        if not text:
            self.list_view.clearSelection()
        else:
            self.list_view.keyboardSearch(text)
            idx = self.list_view.currentIndex()
            if idx.isValid():
                if len(self.list_view.data_sources) - 1 >= idx.row():
                    self.list_view.data_sources.pop(idx.row())
                    self.list_view.update()



    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = simple_contact_list
#!/usr/bin/env python
import sys
from PySide import QtGui, QtCore

FIRST_COLUMN = 0

class UserPresence:
    OFFLINE = 0
    ONLINE = 400

class Object:
    GROUP = 1
    USER = 2

class User():
    def __init__(self, uri, nickname, group = None):
        self._type = Object.USER
        self.uri = uri
        self.nickname = nickname
        self.group = group

    def get_type(self):
        return self._type

    def get_display_name(self):
        return self.nickname


class Group():
    def __init__(self, gid, gname, users = None):
        self._type = Object.GROUP
        self.gid = gid
        self.gname = gname
        self.user_list = []

        if users:
            for user in users:
                self.add_user(user)

    def add_user(self, user):
        if user not in self.user_list:
            self.user_list.append(user)

    def count(self):
        return len(self.user_list)

    def get_user_by_row(self, row):
        return self.user_list[row]

    def get_user_by_uri(self, uri):
        for user in self.user_list:
            if user.uri == uri:
                return user

    def get_display_name(self):
        return self.gname

    def get_type(self):
        return self._type


class GroupAgent:
    def __init__(self, groups = None):
        self.group_list = []

        if groups:
            for group in groups:
                self.add_group(group)

    def add_group(self, group):
        self.group_list.append(group)

    def count(self):
        return len(self.group_list)

    def get_group_by_row(self, row):
        return self.group_list[row]

    def index(self, group):
        return self.group_list.index(group)

    def get_user_by_uri(self, uri):
        for group in self.group_list:
            user = group.get_user_by_uri(uri)
            if user:
                return user


class Model(QtCore.QAbstractItemModel):
    COLUMN_COUNT = 1
    def __init__(self, group_agent):
        QtCore.QAbstractItemModel.__init__(self)
        self.group_agent = group_agent

    def columnCount(self, parent_idx):
        if not parent_idx.isValid():
            return self.COLUMN_COUNT

        parent_obj = parent_idx.internalPointer()
        return parent_obj.count()

    def rowCount(self, parent_idx):
        if not parent_idx.isValid():
            return self.group_agent.count()

        parent_obj = parent_idx.internalPointer()
        if parent_obj.get_type() == Object.GROUP:
            return parent_obj.count()

        return 0

    def index(self, row, column, parent_idx):
        assert column != None
        if not parent_idx.isValid():
            group = self.group_agent.get_group_by_row(row)
            return self.createIndex(row, column, group)

        parent_obj = parent_idx.internalPointer()
        if parent_obj.get_type() == Object.GROUP:
            item = parent_obj.get_user_by_row(row)
            return self.createIndex(row, column, item)

        return QtCore.QModelIndex()

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()

        obj = index.internalPointer()
        obj_type = obj.get_type()

        if role == QtCore.Qt.DisplayRole:
            if obj.get_type() in (Object.GROUP, Object.USER):
                return QtCore.QVariant(obj.get_display_name())

        elif role == QtCore.Qt.UserRole:
            if obj_type == Object.GROUP:
                return QtCore.QVariant(obj.gid)
            elif obj_type == Object.USER:
                return QtCore.QVariant(obj.uri)

        elif role == QtCore.Qt.ToolTipRole:
            if obj_type == Object.USER:
                tool_tip = "%s (URI: %s)" % (obj.get_display_name(), obj.uri)
                return QtCore.QVariant(tool_tip)

        elif role == QtCore.Qt.DecorationRole:
            if obj_type == Object.USER:
                return QtGui.QPixmap("../icons/exit.png")

        return QtCore.QVariant()

    def parent(self, child_index):
        if not child_index.isValid():
            return QtCore.QModelIndex()

        obj = child_index.internalPointer()
        if obj.get_type() == Object.USER:
            parent_obj = obj.group
            row = self.group_agent.index(parent_obj)
            return self.createIndex(row, FIRST_COLUMN, parent_obj)

        return QtCore.QModelIndex()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

def create_group_agent():
    group_a = Group('10', 'Group A')
    for i in [('123', 'Mery'),
            ('132', 'Lily'),
            ('321', 'May')]:
        group_a.add_user(User(i[0], i[1], group_a))

    group_b = Group('20', 'Group B')
    user = User('213', 'Joe', group_b)
    group_b.add_user(user)

    ga = GroupAgent()
    ga.add_group(group_a)
    ga.add_group(group_b)
    return ga

class App(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        x, y, w, h = 300, 300, 300, 200
        self.setGeometry(x, y, w, h)

        self.tv = QtGui.QTreeView(self)

        self.ga = create_group_agent()
        self.model = Model(self.ga)

        self.tv.setHeaderHidden(True)
        self.tv.setModel(self.model)

        self.selection_model = self.tv.selectionModel()
        self.selection_model.currentRowChanged.connect(self.current_row_changed)

        user = self.ga.get_user_by_uri("123")
#        print user.__dict__
        user.nickname = "foo"

    def current_row_changed(self, current_idx, prev_idx):
        assert prev_idx != None
        item = current_idx.internalPointer()

        if item.get_type() != Object.USER:
            return

        #print item.get_display_name()
#        print self.model.itemData(current_idx)


qa = QtGui.QApplication(sys.argv)
app = App()
app.show()
assert app != None
qa.exec_()

########NEW FILE########
__FILENAME__ = tree-in-model-view
#!/usr/bin/env python
import sys
#try:
#    from PySide import QtGui, QtCore
#except ImportError:
#    from PySide import QtGui, QtCore

from PySide import QtGui, QtCore

FIRST_COLUMN = 0

class UserPresence:
    OFFLINE = 0
    ONLINE = 400

class Object:
    GROUP = 1
    USER = 2

class User():
    def __init__(self, uri, nickname, group = None):
        self._type = Object.USER
        self.uri = uri
        self.nickname = nickname
        self.group = group

    def get_type(self):
        return self._type

    def get_display_name(self):
        return self.nickname


class Group():
    def __init__(self, gid, gname, users = None):
        self._type = Object.GROUP
        self.gid = gid
        self.gname = gname
        self.user_list = []

        if users:
            for user in users:
                self.add_user(user)

    def add_user(self, user):
        if user not in self.user_list:
            self.user_list.append(user)

    def count(self):
        return len(self.user_list)

    def get_user_by_row(self, row):
        return self.user_list[row]

    def get_user_by_uri(self, uri):
        for user in self.user_list:
            if user.uri == uri:
                return user

    def get_display_name(self):
        return self.gname

    def get_type(self):
        return self._type


class GroupAgent:
    def __init__(self, groups = None):
        self.group_list = []

        if groups:
            for group in groups:
                self.add_group(group)

    def add_group(self, group):
        self.group_list.append(group)

    def count(self):
        return len(self.group_list)

    def get_group_by_row(self, row):
        return self.group_list[row]

    def index(self, group):
        return self.group_list.index(group)

    def get_user_by_uri(self, uri):
        for group in self.group_list:
            user = group.get_user_by_uri(uri)
            if user:
                return user


class Model(QtCore.QAbstractItemModel):
    COLUMN_COUNT = 1
    def __init__(self, group_agent):
        QtCore.QAbstractItemModel.__init__(self)
        self.group_agent = group_agent

    def columnCount(self, parent_idx):
        if not parent_idx.isValid():
            return self.COLUMN_COUNT

        parent_obj = parent_idx.internalPointer()
        return parent_obj.count()

    def rowCount(self, parent_idx):
        if not parent_idx.isValid():
            return self.group_agent.count()

        parent_obj = parent_idx.internalPointer()
        if parent_obj.get_type() == Object.GROUP:
            return parent_obj.count()

        return 0

    def index(self, row, column, parent_idx):
        assert column != None
        if not parent_idx.isValid():
            group = self.group_agent.get_group_by_row(row)
            return self.createIndex(row, column, group)

        parent_obj = parent_idx.internalPointer()
        if parent_obj.get_type() == Object.GROUP:
            item = parent_obj.get_user_by_row(row)
            return self.createIndex(row, column, item)

        return QtCore.QModelIndex()

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()

        obj = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            if obj.get_type() in (Object.GROUP, Object.USER):
                return QtCore.QVariant(obj.get_display_name())

        elif role == QtCore.Qt.UserRole:
            obj_type = obj.get_type()
            if obj_type == Object.GROUP:
                return QtCore.QVariant(obj.gid)
            elif obj_type == Object.USER:
                return QtCore.QVariant(obj.uri)

        return QtCore.QVariant()

    def parent(self, child_index):
        if not child_index.isValid():
            return QtCore.QModelIndex()

        obj = child_index.internalPointer()
        if obj.get_type() == Object.USER:
            parent_obj = obj.group
            row = self.group_agent.index(parent_obj)
            return self.createIndex(row, FIRST_COLUMN, parent_obj)

        return QtCore.QModelIndex()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

def create_group_agent():
    group_a = Group('10', 'Group A')
    for i in [('123', 'Mery'),
            ('132', 'Lily'),
            ('321', 'May')]:
        group_a.add_user(User(i[0], i[1], group_a))

    group_b = Group('20', 'Group B')
    user = User('213', 'Joe', group_b)
    group_b.add_user(user)

    ga = GroupAgent()
    ga.add_group(group_a)
    ga.add_group(group_b)
    return ga

class Demo(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

        x, y, w, h = 300, 300, 300, 200
        self.setGeometry(x, y, w, h)

        self.tv = QtGui.QTreeView(self)

        self.ga = create_group_agent()
        model = Model(self.ga)

        self.tv.setHeaderHidden(True)
        self.tv.setModel(model)

        self.selection_model = self.tv.selectionModel()
        self.selection_model.currentRowChanged.connect(self.current_row_changed)

        user = self.ga.get_user_by_uri("123")
#        print user.__dict__
        user.nickname = "foo"

    def current_row_changed(self, current_idx, prev_idx):
        assert prev_idx != None
        item = current_idx.internalPointer()

        if item.get_type() != Object.USER:
            return

        print item.get_display_name()


if __name__ == "__main__":
    qa = QtGui.QApplication(sys.argv)

    app = Demo()
    app.show()
    qa.exec_()

########NEW FILE########
__FILENAME__ = markdown_editor
#!/usr/bin/env python
#-*- coding:utf8 -*-
import sys
import web

try:
    from PySide import QtCore
    from PySide import QtGui
    from PySide import QtWebKit
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui
    from PyQt4 import QtWebKit


buf = '<msg id="2825" type="0" show-once="0"> <validity begin="2010-12-25 16:00:00.000" end="2015-10-26 15:59:59.000"/> <content type="text/plain">尊敬的用户，您的手机已停机，这将影响您使用飞信的部分功能。为了您的正常使用，请尽快充值。</content> <url style="auto:0;">http://space.fetion.com.cn/redirection/count/203</url> </msg>'

DEFAULT_STYLE = """
* {
font-family: Monaco;
font-size: 12px;
}
"""


class Foo(QtGui.QWidget):
    def __init__(self):
        super(Foo, self).__init__()

        x, y, w, h = 100, 100, 900, 600
        self.setGeometry(x, y, w, h)
        

        self.source = QtGui.QTextEdit(self)
#        self.preview = QtWebKit.QWebView(self)
        self.preview = QtGui.QTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setFrameShape(QtGui.QFrame.NoFrame)

        qd = QtGui.QTextDocument()
        qd.setDefaultStyleSheet(DEFAULT_STYLE)

        self.preview.setDocument(qd)

        self.splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.source)
        self.splitter.addWidget(self.preview)


#        widget = self.splitter.widget(0)
#        policy = widget.sizePolicy()
#        policy.setHorizontalStretch(1)
#        policy.setVerticalStretch(1)
#        widget.setSizePolicy(policy)

        self.hbox = QtGui.QHBoxLayout(self)
        self.hbox.setContentsMargins(0, 0, 0, 0)
        self.hbox.setSpacing(0)
        self.hbox.addWidget(self.splitter)
        self.setLayout(self.hbox)

        
        self.font = QtGui.QFont("Monaco", 12)
        self.setFont(self.font)


        self.source.textChanged.connect(self.source_text_changed)
        
        self.source.setText(web.safeunicode(buf))

    def source_text_changed(self):
        buf = self.source.toPlainText()
#        import markdown
#        buf = markdown.markdown(buf)
        self.preview.setHtml(buf)
        
    
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    foo = Foo()
    foo.show()
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = foo
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
demo template

Tested environment:
    Mac OS X 10.6.8
"""
import sys
from PySide import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = foo
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
use a ridiculous workaround way make image/jpeg works in .app

Tested environment:
    Mac OS X 10.6.8

Reference:

 http://www.thetoryparty.com/2009/08/27/pyqt-and-py2app-seriously-i-dont-know-what-to-do-with-you-when-youre-like-this/

"""
import os
import sys

try:
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtGui


from PIL import Image
import cStringIO

def jpg2png(path):
    img = Image.open(path)
    mem = cStringIO.StringIO()
    img.save(mem, format = "png")
    return mem


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        path = os.path.join(os.getenv("HOME"), "Desktop", "t.jpg")
        pix = QtGui.QPixmap()
        mem_file_obj = jpg2png(path)
        pix.loadFromData(mem_file_obj.getvalue())

        label = QtGui.QLabel(self)
        label.move(10, 10)
        label.setPixmap(pix)


    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = btn
#!/usr/bin/env python
#coding:utf-8
import sys
from PyQt4 import QtGui
from PyQt4 import QtCore

class Button(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)
        
        x, y, w, h = 190, 190, 96, 32
        login_btn = QtGui.QPushButton("Quit", self)
        login_btn.setGeometry(x, y, w, h)
        
        login_btn.clicked.connect(self.do_quit)

    def do_quit(self):
        QtGui.qApp.quit()
        
def main():
    app = QtGui.QApplication(sys.argv)
    btn = Button()
    btn.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()
    
########NEW FILE########
__FILENAME__ = qthreadutils
__all__ = [
    "kill_qthread",
    "QT",
    "QTKiller"
    ]


import time

from PySide import QtCore


def kill_qthread(t):
    if not t:
        return

    t.terminate()
#    t.wait()


class QT(QtCore.QThread):
    def __init__(self, func, *args, **kwargs):
        QtCore.QThread.__init__(self)
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._return = None

    def run(self):
        self._return = self._func(*self._args, **self._kwargs)
        self.emit(QtCore.SIGNAL("thread_finished()"))

    def get_return(self):
        return self._return


class QTKiller(QtCore.QThread):
    def __init__(self, target_t, timeout = 10):
        QtCore.QThread.__init__(self)
        self._target_t = target_t
        self._timeout = timeout

    def run(self):
        i = 0
        while i < self._timeout:
            time.sleep(1)
            self.emit(QtCore.SIGNAL("thread_running()"))
            i += 1
        self.emit(QtCore.SIGNAL("kill_qthread()"))
        while not self._target_t.isFinished():
            time.sleep(0.1)

########NEW FILE########
__FILENAME__ = qutils
"""
add custom theme name and search path for fix icon file not found on Mac OS X

Install Oxygen icon on Mac OS X via MacPorts:

    sudo port install oxygen-icons

"""
__all__ = [
    "config_theme_path",
    "icon2pix",
]


import sys

from PySide import QtCore, QtGui


def config_theme_path():
    if sys.platform != "darwin":
        return

    theme_name = str(QtGui.QIcon.themeName())

    if theme_name != "Oxygen":
        QtGui.QIcon.setThemeName("Oxygen")


    search_paths = list(QtGui.QIcon.themeSearchPaths())

    custom_path = "/opt/local/share/icons"
    if custom_path not in search_paths:
        search_paths.append(custom_path)

    QtGui.QIcon.setThemeSearchPaths(search_paths)


def icon2pix(icon, size = QtCore.QSize(30, 30), grayscaled = True):
    if grayscaled:
        return icon.pixmap(size, mode = QtGui.QIcon.Disabled)
    else:
        return icon.pixmap(size)

########NEW FILE########
__FILENAME__ = qwinutils
#!/usr/bin/env python
"""
enhance and wrap window for using convenience

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qdesktopwidget.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QWidget.html
"""

__all__ = [
    "auto_set_geometry",
    "AutoSaveGeo",
    "CustomDlg",
    "CustomWin",
    "CustomSheetWin",
    ]


import json
import os

from PySide import QtGui, QtCore


class AutoSaveGeo(QtGui.QMainWindow):
    """ auto save (window) widget geometry before it destroy, and restore its geometry at next time. """
    def __init__(self, user_data_path, w = 300, h = 500, parent = None):
        super(AutoSaveGeo, self).__init__(parent)

        self.resize(w, h)

        self.user_data_path = user_data_path
        if self.user_data_path:
            self._load_win_geo()
    
    def closeEvent(self, evt):
        if hasattr(self, "user_data_path") and self.user_data_path:
            self._save_win_geo()

        return super(AutoSaveGeo, self).closeEvent(evt)

    def _save_win_geo(self):
        config_path = os.path.join(self.user_data_path, "win_geometry.json")

        if not os.path.exists(self.user_data_path):
            os.makedirs(self.user_data_path)

        if os.path.exists(config_path):
            f = file(config_path)
            buf = f.read()
            f.close()
        else:
            buf = None

        datas = None
        if buf:
            datas = json.loads(buf)

        if not datas:
            datas = {}

        win_geo_data = dict(
             x = self.x(),
             y = self.y(),
             w = self.width(),
             h = self.height())

        datas[self.__class__.__name__] = win_geo_data

        path = config_path
        content = json.dumps(datas)

        f = file(path, "w")
        f.write(content)
        f.close()
    
    def _load_win_geo(self):
        config_path = os.path.join(self.user_data_path, "win_geometry.json")

        if not os.path.exists(self.user_data_path):
            os.makedirs(self.user_data_path)

        desktop = QtGui.QApplication.desktop()
        x = desktop.width() / 2
        y = (desktop.height() - self.height()) / 2
        w = self.width()
        h = self.height()

        if os.path.exists(config_path):
            f = file(config_path)
            buf = f.read()
            f.close()
        else:
            buf = None

        datas = None
        if buf:
            datas = json.loads(buf)

        if datas:
            cls_name = self.__class__.__name__
            geo = datas.get(cls_name)

            if geo:
                x, y, w, h = geo['x'], geo['y'], geo['w'], geo['h']

        self.setGeometry(x, y, w, h)


class CustomDlg(QtGui.QDialog):
    """
    Custom dialog template.

    You should override there method:
     - __init__
     - get_inputs
     - popup_and_get_inputs
    """
    def __init__(self, parent, settings):
        """ You should override this method """
        super(CustomDlg, self).__init__(parent)

        self.resize(400, 250)

        self._settings = settings

        # add custom sub-widgets here ...

    def show_and_raise(self):
        self.show()
        self.raise_()

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()
            return self._settings

    def get_inputs(self):
        """ You should override this method
        update self._settings from custom sub-widgets ...
        """
        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        """ You should override this method """
        dlg = CustomDlg(parent, settings)
        dlg.show()
        dlg.exec_()

        return dlg.get_inputs()


class CustomWin(QtGui.QWidget):
    """
    Custom window template.

    You should override there method:
     - __init__
     - get_inputs
     - popup_and_get_inputs
    """
    def __init__(self, parent, settings):
        """ You should override this method """
        super(CustomWin, self).__init__(parent)

        self.resize(400, 250)

        self._settings = settings

        # add custom sub-widgets here ...

    def show_and_raise(self):
        self.show()
        self.raise_()

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()
            return self._settings

    def get_inputs(self):
        """ You should override this method
        update self._settings from custom sub-widgets ...
        """
        return self._settings

    @staticmethod
    def popup_and_get_inputs(parent, settings):
        """ You should override this method """
        dlg = CustomWin(parent, settings)
        dlg.show()

        return dlg.get_inputs()


class CustomSheetWin(QtGui.QWidget):
    def __init__(self, parent = None):
        super(CustomSheetWin, self).__init__(parent)
        self.resize(400, 300)
        self.setWindowFlags(QtCore.Qt.Sheet)

    def closeEvent(self, evt):
        self.emit(QtCore.SIGNAL("sheet_window_close( QWidget * )"), self)
        return QtGui.QWidget.closeEvent(self, evt)

    def emit_and_close(self, signal_name = "sheet_window_close_with_accept( QWidget * )"):
        self.close()
        self.emit(QtCore.SIGNAL(signal_name), self)

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()

        return super(CustomSheetWin, self).keyPressEvent(evt)


_auto_set_geometry_offset_is_zero_if_mare_then = 5
_auto_set_geometry_offset_last_x = 0
_auto_set_geometry_offset_step = 20

def _get_offset_for_auto_set_geometry():
    global _auto_set_geometry_offset_is_zero_if_mare_then
    global _auto_set_geometry_offset_last_x
    global _auto_set_geometry_offset_step

    if _auto_set_geometry_offset_last_x > 0:
        th = _auto_set_geometry_offset_last_x / _auto_set_geometry_offset_step
        if th >= _auto_set_geometry_offset_is_zero_if_mare_then:
            _auto_set_geometry_offset_last_x = 0
        else:
            _auto_set_geometry_offset_last_x += _auto_set_geometry_offset_step
    else:
        _auto_set_geometry_offset_last_x += _auto_set_geometry_offset_step

    offset_x = offset_y = _auto_set_geometry_offset_last_x

    return offset_x, offset_y

def auto_set_geometry(primary, secondary):
    """ auto set the geometry of secondary window base on primary window geometry """
    desktop = QtGui.QApplication.desktop()

    px = primary.x()
    primary_in_left_screen = (desktop.width() / 2 - primary.width() / 2) >= px

    if primary_in_left_screen:
        secondary_x_start = px + primary.width() + (_auto_set_geometry_offset_step / 4)
    else:
        secondary_x_start = px - primary.width() - (_auto_set_geometry_offset_step / 4)

    secondary_y_start = (desktop.height() / 2) - (secondary.height() / 2) - _auto_set_geometry_offset_step

    offset_x, offset_y = _get_offset_for_auto_set_geometry()

    secondary.move(secondary_x_start + offset_x, secondary_y_start + offset_y)



def test_use_custom_dlg():
    class CustomDlgDemo(AutoSaveGeo):
        def __init__(self, parent = None, user_data_path = None):
            super(CustomDlgDemo, self).__init__(parent = parent, user_data_path = user_data_path)

            settings = {}
            new_settings = CustomDlg.popup_and_get_inputs(parent = self, settings = settings)
            print "new_settings:", new_settings

        def show_and_raise(self):
            self.show()
            self.raise_()

    app_name = "foo"
    #tmp_path = os.getenv("TMP") or "/tmp"
    PWD = os.path.dirname(os.path.realpath(__file__))
    tmp_path = PWD
    app_data_path = os.path.join(tmp_path, app_name)

    app = QtGui.QApplication(sys.argv)
    demo = CustomDlgDemo(user_data_path = app_data_path)
    demo.show_and_raise()
    sys.exit(app.exec_())


def test_use_auto_set_secondary_win_geometry():
    class SecondaryWindow(QtGui.QWidget):
        def __init__(self, name = ""):
            super(SecondaryWindow, self).__init__()
            self.setWindowTitle('Window #%s' % name)

            self.resize(200, 200)

        def keyPressEvent(self, evt):
            close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
            close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

            if close_win_cmd_w or close_win_esc:
                self.close()

    class AutoSetGeoDemo(QtGui.QWidget):
        def __init__(self):
            super(AutoSetGeoDemo, self).__init__()

            x, y, w, h = 500, 200, 300, 400
            self.setGeometry(x, y, w, h)

            btn = QtGui.QPushButton("create", self)
            btn.clicked.connect(self._btn_cb)
            btn.move(20, 20)

            # following is optional
            self.win_list = []

        def _btn_cb(self):
            # following is optional
            win_name = str(len(self.win_list))

            secondary_win_obj = SecondaryWindow(name = win_name)
            auto_set_geometry(primary = self, secondary = secondary_win_obj)
            secondary_win_obj.show()

            # following is optional
            self.win_list.append(secondary_win_obj)


        def show_and_raise(self):
            self.show()
            self.raise_()

    app = QtGui.QApplication(sys.argv)
    demo = AutoSetGeoDemo()
    demo.show_and_raise()
    sys.exit(app.exec_())


#if __name__ == "__main__":
#    test_use_custom_dlg()
#    test_use_auto_set_secondary_win_geometry()
########NEW FILE########
__FILENAME__ = add_group
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'add_group.ui'
#
# Created: Thu Jan 26 22:22:29 2012
#      by: PyQt4 UI code generator 4.8.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(400, 110)
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Add Group", None, QtGui.QApplication.UnicodeUTF8))
        self.label = QtGui.QLabel(Form)
        self.label.setGeometry(QtCore.QRect(0, 20, 200, 20))
        self.label.setText(QtGui.QApplication.translate("Form", "Enter group name:", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName(_fromUtf8("label"))
        self.pushButton = QtGui.QPushButton(Form)
        self.pushButton.setGeometry(QtCore.QRect(290, 60, 90, 32))
        self.pushButton.setText(QtGui.QApplication.translate("Form", "Add", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.pushButton_2 = QtGui.QPushButton(Form)
        self.pushButton_2.setGeometry(QtCore.QRect(200, 60, 90, 32))
        self.pushButton_2.setText(QtGui.QApplication.translate("Form", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))
        self.lineEdit = QtGui.QLineEdit(Form)
        self.lineEdit.setGeometry(QtCore.QRect(210, 20, 144, 22))
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        pass


########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
import sys

try:
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtGui

from add_group import Ui_Form


class Demo(QtGui.QWidget, Ui_Form):
    def __init__(self, parent = None):
        super(Demo, self).__init__(parent)

        self.setupUi(self)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = auto_create_qrc
#!/usr/bin/env python
"""
auto scan resources file and create Qt resource(qrc) file for PySide/PyQt project

Usage:
    python auto_create_qrc.py your_pictures_path > bar.qrc

    pyside-rcc -no-compress bar.qrc -o bar.py # if you use PySide

    pyrcc4-2.7 -no-compress bar.qrc -o bar.py # if you use PyQt

Author: Shuge Lee <shuge.lee@gmail.com>
License: MIT License
"""
import os
import re
import sys

PWD = os.path.dirname(os.path.realpath(__file__))


# the function strips copy from web.utils.strips

iters = [list, tuple]
import __builtin__
if hasattr(__builtin__, 'set'):
    iters.append(set)
if hasattr(__builtin__, 'frozenset'):
    iters.append(set)
if sys.version_info < (2,6): # sets module deprecated in 2.6
    try:
        from sets import Set
        iters.append(Set)
    except ImportError:
        pass

class _hack(tuple): pass
iters = _hack(iters)
iters.__doc__ = """
A list of iterable items (like lists, but not strings). Includes whichever
of lists, tuples, sets, and Sets are available in this version of Python.
"""


def _strips(direction, text, remove):
    if isinstance(remove, iters):
        for subr in remove:
            text = _strips(direction, text, subr)
        return text

    if direction == 'l':
        if text.startswith(remove):
            return text[len(remove):]
    elif direction == 'r':
        if text.endswith(remove):
            return text[:-len(remove)]
    else:
        raise ValueError, "Direction needs to be r or l."
    return text

def rstrips(text, remove):
    """
    removes the string `remove` from the right of `text`

        >>> rstrips("foobar", "bar")
        'foo'

    """
    return _strips('r', text, remove)

def lstrips(text, remove):
    """
    removes the string `remove` from the left of `text`

        >>> lstrips("foobar", "foo")
        'bar'
        >>> lstrips('http://foo.org/', ['http://', 'https://'])
        'foo.org/'
        >>> lstrips('FOOBARBAZ', ['FOO', 'BAR'])
        'BAZ'
        >>> lstrips('FOOBARBAZ', ['BAR', 'FOO'])
        'BARBAZ'

    """
    return _strips('l', text, remove)

def strips(text, remove):
    """
    removes the string `remove` from the both sides of `text`

        >>> strips("foobarfoo", "foo")
        'bar'
    """
    return rstrips(lstrips(text, remove), remove)



def tree(top = '.',
         filters = None,
         output_prefix = None,
         max_level = 4,
         followlinks = False,
         top_info = False,
         report = True):
    # The Element of filters should be a callable object or
    # is a byte array object of regular expression pattern.
    topdown = True
    total_directories = 0
    total_files = 0

    top_fullpath = os.path.realpath(top)
    top_par_fullpath_prefix = os.path.dirname(top_fullpath)

    if top_info:
        lines = top_fullpath
    else:
        lines = ""

    if filters is None:
        _default_filter = lambda x : not x.startswith(".")
        filters = [_default_filter]

    for root, dirs, files in os.walk(top = top_fullpath, topdown = topdown, followlinks = followlinks):
        assert root != dirs

        if max_level is not None:
            cur_dir = strips(root, top_fullpath)
            path_levels = strips(cur_dir, "/").count("/")
            if path_levels > max_level:
                continue

        total_directories += len(dirs)
        total_files += len(files)

        for filename in files:
            for _filter in filters:
                if callable(_filter):
                    if not _filter(filename):
                        total_files -= 1
                        continue
                elif not re.search(_filter, filename, re.UNICODE):
                    total_files -= 1
                    continue

                if output_prefix is None:
                    cur_file_fullpath = os.path.join(top_par_fullpath_prefix, root, filename)
                else:
                    buf = strips(os.path.join(root, filename), top_fullpath)
                    if output_prefix != "''":
                        cur_file_fullpath = os.path.join(output_prefix, buf.strip('/'))
                    else:
                        cur_file_fullpath = buf

                lines = "%s%s%s" % (lines, os.linesep, cur_file_fullpath)

    lines = lines.lstrip(os.linesep)

    if report:
        report = "%d directories, %d files" % (total_directories, total_files)
        lines = "%s%s%s" % (lines, os.linesep * 2, report)

    return lines



def scan_files(src_path = ".", output_prefix = "./"):
    filters = ['.(png|jpg|gif)$']
    report = False
    lines = tree(src_path, filters = filters, output_prefix = output_prefix, report = report)

    lines = lines.split('\n')
    if "" in lines:
        lines.remove("")

    return lines


QRC_TPL = """<!DOCTYPE RCC><RCC version="1.0">
<qresource>
%s
</qresource>
</RCC>"""

def create_qrc_body(lines):
    buf = ["<file>%s</file>" % i for i in lines]
    buf = "\n".join(buf)
    buf = QRC_TPL % buf

    return buf

def get_realpath(path):
    if os.path.islink(path) and not os.path.isabs(path):
        PWD = os.path.realpath(os.curdir)
        path = os.path.join(PWD, path)
    else:
        path = os.path.realpath(path)
    return path

def create_qrc(src_path, output_prefix, dst_file = None):
    src_path = get_realpath(src_path)

    lines = scan_files(src_path, output_prefix)
    buf = create_qrc_body(lines)

    if dst_file:
        parent = os.path.dirname(dst_file)
        if not os.path.exists(parent):
            os.makedirs(parent)

        f = file(dst_file, "w")
        f.write(buf)
        f.close()
    else:
        sys.stdout.write(buf)

        
if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) not in (1, 2):
        msg = "Usage: " + '\n'
        msg += "python auto_create_qrc.py <src_path>" + '\n'
        msg += "python auto_create_qrc.py <src_path> <output_prefix>"
        sys.stdout.write('\n' + msg + '\n')
        sys.exit(-1)

    src_path = args[0]
    if len(args) == 1:
        output_prefix = "./"
    else:
        output_prefix = args[1]

    create_qrc(src_path, output_prefix)

########NEW FILE########
__FILENAME__ = foo
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Qt resource system usage

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/resources.html
http://doc.qt.nokia.com/latest/rcc.html
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


import bar


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        pix = QtGui.QPixmap(":/resources/icons/camera.png")
        label = QtGui.QLabel(self)
        label.setPixmap(pix)
        label.move(10, 10)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = detect_env_for_report_bug
#!/usr/bin/python
"""
Detect platform name and SIP/Python/PyQt/PySide version.

Tested environment:

    OS X 10.6.8
    Ubuntu 12.04 LTS

References:
 - http://www.pyside.org/docs/pyside/pysideversion.html
"""

if __name__ == "__main__":
    import sys
    import platform
    import PySide
    from PySide import QtCore

    print 'Platform: %s' % sys.platform
    print "Python version: %s" % platform.python_version()
    print "Qt version: %s" % QtCore.__version__
    print "PySide version: %s" % PySide.__version__

########NEW FILE########
__FILENAME__ = diff_qstr_qvar_basestring
#coding:utf-8
import sys
from PyQt4 import QtCore

SHUGE_DEFAULT_ENCODING = 'utf-8'

def to_unicode_obj(obj, is_filename = False):
    """ Convert string to unicode object.

    Arguments:
    - `is_filename`: set this True if `obj` is get from Microsoft Windows file
                  system, such as os.listdir. """

    if is_filename and sys.platform == "win32":
        file_sys_encoding = sys.getfilesystemencoding()
        return obj.decode(file_sys_encoding)

    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding = SHUGE_DEFAULT_ENCODING)
    return obj

txt = 'hello world'
print QtCore.QString(txt) == txt
print QtCore.QString(txt) == QtCore.QVariant(txt)
print QtCore.QVariant(txt) == txt
print QtCore.QVariant(txt).toString() == txt

txt = to_unicode_obj('hello world')
print QtCore.QString(txt) == txt
print QtCore.QString(txt) == QtCore.QVariant(txt)
print QtCore.QVariant(txt) == txt
print QtCore.QVariant(txt).toString() == txt

txt = '中文'
print QtCore.QString(txt) == txt
print QtCore.QString(txt) == QtCore.QVariant(txt)
print QtCore.QVariant(txt) == txt
print QtCore.QVariant(txt).toString() == txt

txt = to_unicode_obj('中文')
print QtCore.QString(txt) == txt
print QtCore.QString(txt) == QtCore.QVariant(txt)
print QtCore.QVariant(txt) == txt
print QtCore.QVariant(txt).toString() == txt


########NEW FILE########
__FILENAME__ = tetris
#!/usr/bin/python

# tetris.py

import sys
import random
from PyQt4 import QtCore, QtGui


class Tetris(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.setGeometry(300, 300, 180, 380)
        self.setWindowTitle('Tetris')
        self.tetrisboard = Board(self)
    
        self.setCentralWidget(self.tetrisboard)
    
        self.statusbar = self.statusBar()
        self.connect(self.tetrisboard, QtCore.SIGNAL("messageToStatusbar(QString)"),
            self.statusbar, QtCore.SLOT("showMessage(QString)"))
    
        self.tetrisboard.start()
        self.center()

    def center(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2,
        (screen.height() - size.height()) / 2)

class Board(QtGui.QFrame):
    BoardWidth = 10
    BoardHeight = 22
    Speed = 300

    def __init__(self, parent):
        QtGui.QFrame.__init__(self, parent)

        self.timer = QtCore.QBasicTimer()
        self.isWaitingAfterLine = False
        self.curPiece = Shape()
        self.nextPiece = Shape()
        self.curX = 0
        self.curY = 0
        self.numLinesRemoved = 0
        self.board = []

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.isStarted = False
        self.isPaused = False
        self.clearBoard()

        self.nextPiece.setRandomShape()

    def shapeAt(self, x, y):
        return self.board[(y * Board.BoardWidth) + x]

    def setShapeAt(self, x, y, shape):
        self.board[(y * Board.BoardWidth) + x] = shape

    def squareWidth(self):
        return self.contentsRect().width() / Board.BoardWidth

    def squareHeight(self):
        return self.contentsRect().height() / Board.BoardHeight

    def start(self):
        if self.isPaused:
            return

        self.isStarted = True
        self.isWaitingAfterLine = False
        self.numLinesRemoved = 0
        self.clearBoard()

        self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"),
        str(self.numLinesRemoved))

        self.newPiece()
        self.timer.start(Board.Speed, self)

    def pause(self):
        if not self.isStarted:
            return

        self.isPaused = not self.isPaused
        if self.isPaused:
            self.timer.stop()
            self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"), "paused")
        else:
            self.timer.start(Board.Speed, self)
            self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"),
            str(self.numLinesRemoved))

        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        rect = self.contentsRect()

        boardTop = rect.bottom() - Board.BoardHeight * self.squareHeight()

        for i in range(Board.BoardHeight):
            for j in range(Board.BoardWidth):
                shape = self.shapeAt(j, Board.BoardHeight - i - 1)
                if shape != Tetrominoes.NoShape:
                    self.drawSquare(painter,
                        rect.left() + j * self.squareWidth(),
                        boardTop + i * self.squareHeight(), shape)

        if self.curPiece.shape() != Tetrominoes.NoShape:
            for i in range(4):
                x = self.curX + self.curPiece.x(i)
                y = self.curY - self.curPiece.y(i)
                self.drawSquare(painter, rect.left() + x * self.squareWidth(),
                    boardTop + (Board.BoardHeight - y - 1) * self.squareHeight(),
                    self.curPiece.shape())

    def keyPressEvent(self, event):
        if not self.isStarted or self.curPiece.shape() == Tetrominoes.NoShape:
            QtGui.QWidget.keyPressEvent(self, event)
            return

        key = event.key()
        if key == QtCore.Qt.Key_P:
            self.pause()
            return
    
        if self.isPaused:
            return
        elif key == QtCore.Qt.Key_Left:
            self.tryMove(self.curPiece, self.curX - 1, self.curY)
        elif key == QtCore.Qt.Key_Right:
            self.tryMove(self.curPiece, self.curX + 1, self.curY)
        elif key == QtCore.Qt.Key_Down:
            self.tryMove(self.curPiece.rotatedRight(), self.curX, self.curY)
        elif key == QtCore.Qt.Key_Up:
            self.tryMove(self.curPiece.rotatedLeft(), self.curX, self.curY)
        elif key == QtCore.Qt.Key_Space:
            self.dropDown()
        elif key == QtCore.Qt.Key_D:
            self.oneLineDown()
        else:
            QtGui.QWidget.keyPressEvent(self, event)

    def timerEvent(self, event):
        if event.timerId() == self.timer.timerId():
            if self.isWaitingAfterLine:
                self.isWaitingAfterLine = False
                self.newPiece()
            else:
                self.oneLineDown()
        else:
            QtGui.QFrame.timerEvent(self, event)

    def clearBoard(self):
        for i in range(Board.BoardHeight * Board.BoardWidth):
            self.board.append(Tetrominoes.NoShape)

    def dropDown(self):
        newY = self.curY
        while newY > 0:
            if not self.tryMove(self.curPiece, self.curX, newY - 1):
                break
            newY -= 1

        self.pieceDropped()

    def oneLineDown(self):
        if not self.tryMove(self.curPiece, self.curX, self.curY - 1):
            self.pieceDropped()

    def pieceDropped(self):
        for i in range(4):
            x = self.curX + self.curPiece.x(i)
            y = self.curY - self.curPiece.y(i)
            self.setShapeAt(x, y, self.curPiece.shape())

        self.removeFullLines()

        if not self.isWaitingAfterLine:
            self.newPiece()

    def removeFullLines(self):
        numFullLines = 0

        rowsToRemove = []

        for i in range(Board.BoardHeight):
            n = 0
            for j in range(Board.BoardWidth):
                if not self.shapeAt(j, i) == Tetrominoes.NoShape:
                    n = n + 1
    
            if n == 10:
                rowsToRemove.append(i)
    
        rowsToRemove.reverse()
    
        for m in rowsToRemove:
            for k in range(m, Board.BoardHeight):
                for l in range(Board.BoardWidth):
                        self.setShapeAt(l, k, self.shapeAt(l, k + 1))
    
            numFullLines = numFullLines + len(rowsToRemove)
    
            if numFullLines > 0:
                self.numLinesRemoved = self.numLinesRemoved + numFullLines
                self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"),
            str(self.numLinesRemoved))
                self.isWaitingAfterLine = True
                self.curPiece.setShape(Tetrominoes.NoShape)
                self.update()

    def newPiece(self):
        self.curPiece = self.nextPiece
        self.nextPiece.setRandomShape()
        self.curX = Board.BoardWidth / 2 + 1
        self.curY = Board.BoardHeight - 1 + self.curPiece.minY()

        if not self.tryMove(self.curPiece, self.curX, self.curY):
            self.curPiece.setShape(Tetrominoes.NoShape)
            self.timer.stop()
            self.isStarted = False
            self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"), "Game over")



    def tryMove(self, newPiece, newX, newY):
        for i in range(4):
            x = newX + newPiece.x(i)
            y = newY - newPiece.y(i)
            if x < 0 or x >= Board.BoardWidth or y < 0 or y >= Board.BoardHeight:
                return False
            if self.shapeAt(x, y) != Tetrominoes.NoShape:
                return False

        self.curPiece = newPiece
        self.curX = newX
        self.curY = newY
        self.update()
        return True

    def drawSquare(self, painter, x, y, shape):
        colorTable = [0x000000, 0xCC6666, 0x66CC66, 0x6666CC,
                      0xCCCC66, 0xCC66CC, 0x66CCCC, 0xDAAA00]

        color = QtGui.QColor(colorTable[shape])
        painter.fillRect(x + 1, y + 1, self.squareWidth() - 2,
        self.squareHeight() - 2, color)

        painter.setPen(color.light())
        painter.drawLine(x, y + self.squareHeight() - 1, x, y)
        painter.drawLine(x, y, x + self.squareWidth() - 1, y)

        painter.setPen(color.dark())
        painter.drawLine(x + 1, y + self.squareHeight() - 1,
            x + self.squareWidth() - 1, y + self.squareHeight() - 1)
        painter.drawLine(x + self.squareWidth() - 1,
        y + self.squareHeight() - 1, x + self.squareWidth() - 1, y + 1)


class Tetrominoes(object):
    NoShape = 0
    ZShape = 1
    SShape = 2
    LineShape = 3
    TShape = 4
    SquareShape = 5
    LShape = 6
    MirroredLShape = 7


class Shape(object):
    coordsTable = (
        ((0, 0), (0, 0), (0, 0), (0, 0)),
        ((0, -1), (0, 0), (-1, 0), (-1, 1)),
        ((0, -1), (0, 0), (1, 0), (1, 1)),
        ((0, -1), (0, 0), (0, 1), (0, 2)),
        ((-1, 0), (0, 0), (1, 0), (0, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((-1, -1), (0, -1), (0, 0), (0, 1)),
        ((1, -1), (0, -1), (0, 0), (0, 1))
    )

    def __init__(self):
        self.coords = [[0, 0] for i in range(4)]
        self.pieceShape = Tetrominoes.NoShape

        self.setShape(Tetrominoes.NoShape)

    def shape(self):
        return self.pieceShape

    def setShape(self, shape):
        table = Shape.coordsTable[shape]
        for i in range(4):
            for j in range(2):
                self.coords[i][j] = table[i][j]

        self.pieceShape = shape

    def setRandomShape(self):
        self.setShape(random.randint(1, 7))

    def x(self, index):
        return self.coords[index][0]

    def y(self, index):
        return self.coords[index][1]

    def setX(self, index, x):
        self.coords[index][0] = x

    def setY(self, index, y):
        self.coords[index][1] = y

    def minX(self):
        m = self.coords[0][0]
        for i in range(4):
            m = min(m, self.coords[i][0])

        return m

    def maxX(self):
        m = self.coords[0][0]
        for i in range(4):
            m = max(m, self.coords[i][0])

        return m

    def minY(self):
        m = self.coords[0][1]
        for i in range(4):
            m = min(m, self.coords[i][1])

        return m

    def maxY(self):
        m = self.coords[0][1]
        for i in range(4):
            m = max(m, self.coords[i][1])

        return m

    def rotatedLeft(self):
        if self.pieceShape == Tetrominoes.SquareShape:
            return self

        result = Shape()
        result.pieceShape = self.pieceShape
        for i in range(4):
            result.setX(i, self.y(i))
            result.setY(i, -self.x(i))

        return result

    def rotatedRight(self):
        if self.pieceShape == Tetrominoes.SquareShape:
            return self

        result = Shape()
        result.pieceShape = self.pieceShape
        for i in range(4):
            result.setX(i, -self.y(i))
            result.setY(i, self.x(i))

        return result


app = QtGui.QApplication(sys.argv)
tetris = Tetris()
tetris.show()
sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = cocoa_textured_window
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Cocoa textured window

Tested environment:
    Mac OS X 10.6.8

http://stackoverflow.com/questions/1413337/cocoa-textured-window-in-qt
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.setUnifiedTitleAndToolBarOnMac(True)
    demo.setAttribute(QtCore.Qt.WA_MacBrushedMetal, True)
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = css_style
"""
Qt Style Sheet
"""
import sys
from PySide import QtGui

app = QtGui.QApplication(sys.argv)

win = QtGui.QWidget()
x, y, w, h = 100, 100, 200, 50
win.setGeometry(x, y, w, h)

label = QtGui.QLabel("hello", win)
label.move(10, 10)


css = "QLabel { border: 1px solid red; color: blue; }"
win.setStyleSheet(css)

win.show()
win.raise_()

sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = disable_highlight
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
disable highlight focused widget

Tested environment:
    Mac OS X 10.6.8

http://stackoverflow.com/questions/1987546/qt4-stylesheets-and-focus-rect
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)


        # highlight
        tv = QtGui.QTreeView(self)
        tv.setGeometry(10, 10, 100, 100)


        # disable highlight
        tv2 = QtGui.QTreeView(self)
        tv2.setGeometry(10, 110, 100, 100)

        tv2.setFrameShape(QtGui.QFrame.NoFrame)
        tv2.setFrameShadow(QtGui.QFrame.Plain)
        tv2.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = font
import os
import sys

try:
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtGui


def get_best_qfont():
    IS_GNOME = os.getenv("GDMSESSION") and os.getenv("GDMSESSION") == "gnome"

    font = None

    if sys.platform == "linux2" and IS_GNOME:
        font = QtGui.QFont("WenQuanYi Zen Hei", 12) # 'DejaVu Sans'
    return font

def auto_set_qfont(widget, font=None):
    qfont = font or get_best_qfont()
    if qfont:
        widget.setFont(qfont)


class Main(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self, parent = None)
        
        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)
        
        self.label = QtGui.QLabel('hello world', self)
        qf = QtGui.QFont("Times", 12, QtGui.QFont.Bold)
        self.label.setFont(qf)
        self.label.move(10, 10)
        
        self.show()


def main():
    app = QtGui.QApplication(sys.argv)
    main = Main()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()
    
########NEW FILE########
__FILENAME__ = auto_config_geo_for_multiple_wins_app
#!/usr/bin/env python
"""
auto place secondary window next to primary window

Tested environment:
    Mac OS X 10.6.8

http://www.pyside.org/docs/pyside/PySide/QtGui/QWidget.html
http://www.pyside.org/docs/pyside/PySide/QtCore/QRect.html
http://doc.qt.nokia.com/latest/qdesktopwidget.html
"""
import sys


try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class AnotherWindow(QtGui.QWidget):
    def __init__(self, primary_win):
        super(AnotherWindow, self).__init__()
        self.setWindowTitle('Another Window')

        w, h = 300, 400
        self.resize(w, h)

        self.primary_win = primary_win

    def smart_place(self):
        screen = QtGui.QApplication.desktop()

        primary_win_pos = 'right'
        if self.primary_win.x() < screen.width():
            left_screen = QtCore.QRect(0, 0, screen.width() / 2, screen.height())
            if left_screen.contains(self.primary_win.pos()) or left_screen.contains(self.primary_win.geometry().topRight()):
                primary_win_pos = 'left'

        y = (screen.height() - self.height() - 100) / 2
        if primary_win_pos == 'left':
            x = self.primary_win.x() + self.primary_win.width()
        else:
            x = self.primary_win.x() - self.width()

        self.move(x, y)

    def show(self):
        self.smart_place()
            
        super(AnotherWindow, self).show()


class Demo(QtGui.QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()
        self.resize(300, 300)

        self.show_another_win_btn = QtGui.QPushButton("show", self)
        self.show_another_win_btn.clicked.connect(self._show_another_win_btn_cb)
        self.show_another_win_btn.move(10, 10)

        self.another_win = None

    def _show_another_win_btn_cb(self):
        if not self.another_win:
            self.another_win = AnotherWindow(primary_win = self)

        self.another_win.show()

    def show_and_raise(self):
        self.show()
        self.raise_()



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = auto_save_win_geometry
#!/usr/bin/env python
"""
auto save window geometry

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qdesktopwidget.html
http://www.pyside.org/docs/pyside/PySide/QtGui/QWidget.html
"""
import json
import os
import sys
import web


try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


app_name = "foo"
#tmp_path = os.getenv("TMP") or "/tmp"
PWD = os.path.dirname(os.path.realpath(__file__))
tmp_path = PWD
app_data_path = os.path.join(tmp_path, app_name)


class AutoSaveGeo(QtGui.QWidget):
    def __init__(self, w = 300, h = 500, parent = None, user_data_path = None):
        super(AutoSaveGeo, self).__init__(parent)

        self.resize(w, h)

        self.user_data_path = user_data_path
        if self.user_data_path:
            self._load_win_geo()
    
    def closeEvent(self, evt):
        if hasattr(self, "user_data_path") and self.user_data_path:
            self._save_win_geo()
            
        return super(AutoSaveGeo, self).closeEvent(evt)

    def _save_win_geo(self):
        config_path = os.path.join(self.user_data_path, "win_geometry.json")

        if not os.path.exists(self.user_data_path):
            os.makedirs(self.user_data_path)

        if os.path.exists(config_path):
            f = file(config_path)
            buf = f.read()
            f.close()
        else:
            buf = None

        datas = None
        if buf:
            datas = json.loads(buf)

        if not datas:
            datas = {}

        win_geo_data = dict(
             x = self.x(),
             y = self.y(),
             w = self.width(),
             h = self.height())

        datas[self.__class__.__name__] = win_geo_data

        buf = json.dumps(datas)
        web.utils.safewrite(config_path, buf)

    
    def _load_win_geo(self):
        config_path = os.path.join(self.user_data_path, "win_geometry.json")

        if not os.path.exists(self.user_data_path):
            os.makedirs(self.user_data_path)

        desktop = QtGui.QApplication.desktop()
        x = desktop.width() / 2
        y = (desktop.height() - self.height()) / 2
        w = self.width()
        h = self.height()

        if os.path.exists(config_path):
            f = file(config_path)
            buf = f.read()
            f.close()
        else:
            buf = None

        datas = None
        if buf:
            datas = json.loads(buf)

        if datas:
            cls_name = self.__class__.__name__
            geo = datas.get(cls_name)

            if geo:
                x, y, w, h = geo['x'], geo['y'], geo['w'], geo['h']

        self.setGeometry(x, y, w, h)


class Demo(AutoSaveGeo):
    def __init__(self, parent = None, user_data_path = None):
        super(Demo, self).__init__(parent = parent, user_data_path = user_data_path)

    def show_and_raise(self):
        self.show()
        self.raise_()



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo(user_data_path = app_data_path)
    demo.show_and_raise()

    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = auto_set_secondary_window_geometry
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
auto set the geometry of secondary window base on primary window geometry 

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


_auto_set_geometry_offset_is_zero_if_mare_then = 5
_auto_set_geometry_offset_last_x = 0
_auto_set_geometry_offset_step = 10

def get_offset_for_auto_set_gemetry():
    global _auto_set_geometry_offset_is_zero_if_mare_then
    global _auto_set_geometry_offset_last_x
    global _auto_set_geometry_offset_step

    if _auto_set_geometry_offset_last_x > 0:
        th = _auto_set_geometry_offset_last_x / _auto_set_geometry_offset_step
        if th >= _auto_set_geometry_offset_is_zero_if_mare_then:
            _auto_set_geometry_offset_last_x = 0
        else:
            _auto_set_geometry_offset_last_x += _auto_set_geometry_offset_step
    else:
        _auto_set_geometry_offset_last_x += _auto_set_geometry_offset_step

    offset_x = offset_y = _auto_set_geometry_offset_last_x

    return offset_x, offset_y

def auto_set_geometry(primary, secondary):
    desktop = QtGui.QApplication.desktop()

    px = primary.x()
    primary_in_left_screen = desktop.width() / 2 + primary.width() / 2 >= px

    if primary_in_left_screen:
        secondary_x_start = px + primary.width() + 5
    else:
        secondary_x_start = px - primary.width() - 5
    secondary_y_start = (desktop.height() - secondary.height()) / 2

    offset_x, offset_y = get_offset_for_auto_set_gemetry()

    secondary.move(secondary_x_start + offset_x, secondary_y_start + offset_y)


class SecondaryWindow(QtGui.QWidget):
    def __init__(self, name = ""):
        super(SecondaryWindow, self).__init__()
        self.setWindowTitle('Window #%s' % name)

        self.resize(200, 200)

    def keyPressEvent(self, evt):
        close_win_cmd_w = (evt.key() == QtCore.Qt.Key_W and evt.modifiers() == QtCore.Qt.ControlModifier)
        close_win_esc = (evt.key() == QtCore.Qt.Key_Escape)

        if close_win_cmd_w or close_win_esc:
            self.close()

            
class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        btn = QtGui.QPushButton("create", self)
        btn.clicked.connect(self._btn_cb)
        btn.move(20, 20)

        # following is optional
        self.win_list = []

    def _btn_cb(self):
        # following is optional
        win_name = str(len(self.win_list))

        secondary_win_obj = SecondaryWindow(name = win_name)
        auto_set_geometry(primary = self, secondary = secondary_win_obj)
        secondary_win_obj.show()

        # following is optional
        self.win_list.append(secondary_win_obj)


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = bounce_app_icon
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
demo template

Tested environment:
    Mac OS X 10.6.8

http://doc.qt.nokia.com/latest/qapplication.html#alert
"""
import sys
import time
import threading

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        def foo():
            time.sleep(2)
            QtGui.QApplication.alert(self)

        t = threading.Thread(target=foo)
        t.start()


    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = collect_data_for_analysing_user_behaves
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
collect data for analysing user behaves

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

    def show_and_raise(self):
        self.show()
        self.raise_()

        
def lastWindowClosed():
    print "lastWindowClosed"


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    QtGui.QWidget.connect(app, QtCore.SIGNAL("lastWindowClosed()"), lastWindowClosed)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = custom_window_icon
#!/usr/bin/env python
"""
custom application window icon

Tested environment:
    Mac OS X 10.6.8
"""
import os
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


PWD = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(PWD, "qt-logo.png")


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        icon = QtGui.QIcon(icon_path)
        self.setWindowIcon(icon)

    def show_and_raise(self):
        self.show()
        self.raise_()

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    icon = QtGui.QIcon(icon_path)
    app.setWindowIcon(icon)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = custom_win_flags
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
demo template

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class SheetWin(QtGui.QWidget):
    def __init__(self, parent = None):
        super(SheetWin, self).__init__(parent)

        self.setWindowFlags(QtCore.Qt.Sheet)


        btn = QtGui.QPushButton("close", self)
        btn.move(10, 10)
        btn.clicked.connect(self.close)
        

class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        btn = QtGui.QPushButton("btn", self)
        btn.clicked.connect(self.btn_cb)

    def btn_cb(self):
        sw_obj = SheetWin(self)
        sw_obj.show()

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = notify_primary_win_while_sheet_win_has_closed
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
notify primary window/main thread sheet window has closed

Tested environment:
    Mac OS X 10.6.8
    
"""
import sys

try:
    from PySide import QtCore
    from PySide import QtGui
except ImportError:
    from PyQt4 import QtCore
    from PyQt4 import QtGui


class SheetWin(QtGui.QWidget):
    def __init__(self, parent = None):
        super(SheetWin, self).__init__(parent)

        self.setWindowFlags(QtCore.Qt.Sheet)


        btn = QtGui.QPushButton("close", self)
        btn.move(10, 10)
        btn.clicked.connect(self.close)

        self._settings = {"name" : "a", "age" : "b"}

    def closeEvent(self, evt):
        print "closeEvent"

        self.emit(QtCore.SIGNAL("sheet_win_close( QWidget * )"), self)

        return super(SheetWin, self).closeEvent(evt)


class Demo(QtGui.QWidget):
    def __init__(self):
        super(Demo, self).__init__()

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        btn = QtGui.QPushButton("btn", self)
        btn.clicked.connect(self.btn_cb)

    def btn_cb(self):
        sw_obj = SheetWin(self)
        sw_obj.show()

        self.connect(sw_obj, QtCore.SIGNAL("sheet_win_close( QWidget * )"), self._sw_cb)

    def _sw_cb(self, sw_obj):
        print "_sw_cb", sw_obj

    def show_and_raise(self):
        self.show()
        self.raise_()



if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = Demo()
    demo.show_and_raise()

    sys.exit(app.exec_())
########NEW FILE########
__FILENAME__ = switching_multiple wins_in_im
#!/usr/bin/env python
#-*- coding:utf8 -*-
"""
switching multiple windows in instant message application
"""
import sys

#from PySide import QtCore
from PySide import QtGui


class ContactListWidow(QtGui.QWidget):
    def __init__(self, sign_in_win):
        super(ContactListWidow, self).__init__()
        self.setWindowTitle('ContactListWidow')

        x, y, w, h = 200, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.sign_in_win = sign_in_win

        self.switch_btn = QtGui.QPushButton('switch', self)
        self.switch_btn.clicked.connect(self._switch_btn_cb)
        self.switch_btn.move(10, 10)

    def _switch_btn_cb(self):
        self.close()
        self.sign_in_win.show()

    def show_and_raise(self):
        self.show()
        self.raise_()


class SignInWin(QtGui.QMainWindow):
    def __init__(self):
        super(SignInWin, self).__init__()
        self.setWindowTitle('SignInWin')

        x, y, w, h = 500, 200, 300, 400
        self.setGeometry(x, y, w, h)

        self.switch_btn = QtGui.QPushButton('switch', self)
        self.switch_btn.clicked.connect(self._switch_btn_cb)
        self.switch_btn.move(10, 10)

        self.cat_list_win = None

    def _switch_btn_cb(self):
        self.close()

        if not self.cat_list_win:
            self.cat_list_win = ContactListWidow(self)

        self.cat_list_win.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.raise_()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    demo = SignInWin()
    demo.show_and_raise()

    sys.exit(app.exec_())


########NEW FILE########
