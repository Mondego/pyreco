__FILENAME__ = loxodo
#!/usr/bin/env python

import sys
import os
import platform

# On Windows CE, use the "ppygui" frontend.
if platform.system() == "Windows" and platform.release() == "CE":
    from src.frontends.ppygui import loxodo
    sys.exit()

# All other platforms use the Config module
from src.config import config

# store base script name, taking special care if we're "frozen" using py2app or py2exe
if hasattr(sys,"frozen") and (sys.platform != 'darwin'):
    config.set_basescript(unicode(sys.executable, sys.getfilesystemencoding()))
else:
    config.set_basescript(unicode(__file__, sys.getfilesystemencoding()))

# If cmdline arguments were given, use the "cmdline" frontend.
if len(sys.argv) > 1:
    from src.frontends.cmdline import loxodo
    sys.exit()

# In all other cases, use the "wx" frontend.    
try:
    import wx
except ImportError, e:
    print >> sys.stderr, 'Could not find wxPython, the wxWidgets Python bindings: %s' % e
    print >> sys.stderr, 'Falling back to cmdline frontend.'
    print >> sys.stderr, ''
    from src.frontends.cmdline import loxodo
    sys.exit()

from src.frontends.wx import loxodo


########NEW FILE########
__FILENAME__ = config
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import platform
from ConfigParser import SafeConfigParser


class Config(object):
    """
    Manages the configuration file
    """
    def __init__(self):
        """
        DEFAULT VALUES
        """
        self._basescript = None
        self.recentvaults = []
        self.pwlength = 10
        self.reduction = False
        self.search_notes = False
        self.search_passwd = False
        self.alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_"

        self._fname = self.get_config_filename()
        self._parser = SafeConfigParser()

        if os.path.exists(self._fname):
            self._parser.read(self._fname)

        if not self._parser.has_section("base"):
            self._parser.add_section("base")

        for num in range(10):
            if (not self._parser.has_option("base", "recentvaults" + str(num))):
                break
            self.recentvaults.append(self._parser.get("base", "recentvaults" + str(num)))

        if self._parser.has_option("base", "alphabet"):
            self.alphabet = int(self._parser.get("base", "alphabet"))

        if self._parser.has_option("base", "pwlength"):
            self.pwlength = int(self._parser.get("base", "pwlength"))

        if self._parser.has_option("base", "alphabetreduction"):
            if self._parser.get("base", "alphabetreduction") == "True":
                self.reduction = True

        if self._parser.has_option("base", "search_notes"):
            if self._parser.get("base", "search_notes") == "True":
                self.search_notes = True

        if self._parser.has_option("base", "search_passwd"):
            if self._parser.get("base", "search_passwd") == "True":
                self.search_passwd = True

        if not os.path.exists(self._fname):
            self.save()

    def set_basescript(self, basescript):
        self._basescript = basescript

    def get_basescript(self):
        return self._basescript

    def save(self):
        if (not os.path.exists(os.path.dirname(self._fname))):
            os.mkdir(os.path.dirname(self._fname))

        # remove duplicates and trim to 10 items
        _saved_recentvaults = []
        for item in self.recentvaults:
            if item in _saved_recentvaults:
                continue
            self._parser.set("base", "recentvaults" + str(len(_saved_recentvaults)), item)
            _saved_recentvaults.append(item)
            if (len(_saved_recentvaults) >= 10):
                break

        self._parser.set("base", "pwlength", str(self.pwlength))
        self._parser.set("base", "alphabetreduction", str(self.reduction))
        self._parser.set("base", "search_notes", str(self.search_notes))
        self._parser.set("base", "search_passwd", str(self.search_passwd))
        filehandle = open(self._fname, 'w')
        self._parser.write(filehandle)
        filehandle.close()

    @staticmethod
    def get_config_filename():
        """
        Returns the full filename of the config file
        """
        base_fname = "loxodo"

        # On Mac OS X, config files go to ~/Library/Application Support/foo/
        if platform.system() == "Darwin":
            base_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
            if os.path.isdir(base_path):
                return os.path.join(base_path, base_fname, base_fname + ".ini")

        # On Microsoft Windows, config files go to $APPDATA/foo/
        if platform.system() in ("Windows", "Microsoft"):
            if ("APPDATA" in os.environ):
                base_path = os.environ["APPDATA"]
                if os.path.isdir(base_path):
                    return os.path.join(base_path, base_fname, base_fname + ".ini")

        # Allow config directory override as per freedesktop.org XDG Base Directory Specification
        if ("XDG_CONFIG_HOME" in os.environ):
            base_path = os.environ["XDG_CONFIG_HOME"]
            if os.path.isdir(base_path):
                return os.path.join(base_path, base_fname, base_fname + ".ini")

        # Default configuration path is ~/.config/foo/
        base_path = os.path.join(os.path.expanduser("~"), ".config")
        if os.path.isdir(base_path):
            return os.path.join(base_path, base_fname, base_fname + ".ini")
        else:
            return os.path.join(os.path.expanduser("~"),"."+ base_fname + ".ini")

config = Config()

########NEW FILE########
__FILENAME__ = loxodo
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import sys
from optparse import OptionParser
from getpass import getpass
import readline
import cmd
import re
import csv
try:
    import pygtk
    import gtk
except ImportError:
    pygtk = None
    gtk = None

from ...vault import Vault
from ...config import config

class InteractiveConsole(cmd.Cmd):

    def __init__(self):
        self.vault = None
        self.vault_file_name = None
        self.vault_password = None
        self.vault_modified = False

        cmd.Cmd.__init__(self)
        if sys.platform == "darwin":
            readline.parse_and_bind('bind ^I rl_complete')
        self.intro = 'Ready for commands. Type "help" or "help <command>" for help, type "quit" to quit.'
        self.prompt = "[none]> "

    def open_vault(self):
        print "Opening " + self.vault_file_name + "..."
        try:
            self.vault_password = getpass("Vault password: ")
        except EOFError:
            print "\n\nBye."
            raise RuntimeError("No password given")
        try:
            self.vault = Vault(self.vault_password, filename=self.vault_file_name)
            self.prompt = "[" + os.path.basename(self.vault_file_name) + "]> "
        except Vault.BadPasswordError:
            print "Bad password."
            raise
        except Vault.VaultVersionError:
            print "This is not a PasswordSafe V3 Vault."
            raise
        except Vault.VaultFormatError:
            print "Vault integrity check failed."
            raise
        print "... Done.\n"

    def postloop(self):
        print

    def emptyline(self):
        pass

    def do_help(self, line):
        """
        Displays this message.
        """
        if line:
            cmd.Cmd.do_help(self, line)
            return

        print "\nCommands:"
        print "  ".join(("ls", "show", "quit", "add", "save", "import"))
        print

    def do_quit(self, line):
        """
        Exits interactive mode.
        """
        self.do_save()
        return True

    def do_save(self, line=None):
        if self.vault_modified and self.vault_file_name and self.vault_password:
            self.vault.write_to_file(self.vault_file_name, self.vault_password)
            self.vault_modified = False
            print "Changes Saved"

    def do_EOF(self, line):
        """
        Exits interactive mode.
        """
        return True

    def do_add(self, line):
        """
        Adds a user to the vault

        Example: add USERNAME [TITLE, [GROUP]]
        """
        if not line:
            cmd.Cmd.do_help(self, "add")
            return

        line = line.split(" ")
        entry = self.vault.Record.create()
        entry.user = line[0]
        if len(line) >= 2:
            entry.title = line[1]
        if len(line) >= 3:
            entry.group = line[2]

        passwd = getpass("Password: ")
        passwd2 = getpass("Re-Type Password: ")
        if passwd != passwd2:
            print "Passwords don't match"
            return

        entry.passwd = passwd

        self.vault.records.append(entry)
        self.vault_modified = True
        print "User Added, but not saved"

    def do_import(self, line):
        """
        Adds a CSV importer, based on CSV file

        Example: /home/user/data.csv
        Columns: Title,User,Password,URL,Group
        """
        if not line:
            cmd.Cmd.do_help(self, "import")
            return

        data = csv.reader(open(line, 'rb'))
        try:
            for row in data:
                entry = self.vault.Record.create()
                entry.title = row[0]
                entry.user = row[1]
                entry.passwd = row[2]
                entry.url = row[3]
                entry.group = row[4]
                self.vault.records.append(entry)
            self.vault_modified = True
            print "Import completed, but not saved."
        except csv.Error, e:
            sys.exit('file %s, line %d: %s' % (line, data.line_num, e))

    def do_ls(self, line):
        """
        Show contents of this Vault. If an argument is added a case insensitive
        search of titles is done, entries can also be specified as regular expressions.
        """
        if not self.vault:
            raise RuntimeError("No vault opened")

        if line is not None:
            vault_records = self.find_titles(line)
        else:
            vault_records = self.vault.records[:]
            vault_records.sort(lambda e1, e2: cmp(e1.title, e2.title))

        if vault_records is None:
            print "No matches found."
            return

        for record in vault_records:
            print record.title.encode('utf-8', 'replace') + " [" + record.user.encode('utf-8', 'replace') + "]"

    def do_show(self, line, echo=True, passwd=False):
        """
        Show the specified entry (including its password).
        A case insenstive search of titles is done, entries can also be specified as regular expressions.
        """
        if not self.vault:
            raise RuntimeError("No vault opened")

        matches = self.find_titles(line)

        if matches is None:
            print 'No entry found for "%s"' % line
            return

        for record in matches:
            if echo is True:
                print """
%s.%s
Username : %s
Password : %s""" % (record.group.encode('utf-8', 'replace'),
                    record.title.encode('utf-8', 'replace'),
                    record.user.encode('utf-8', 'replace'),
                    record.passwd.encode('utf-8', 'replace'))
            else:
                print """
%s.%s
Username : %s""" % (record.group.encode('utf-8', 'replace'),
                    record.title.encode('utf-8', 'replace'),
                    record.user.encode('utf-8', 'replace'))

            if record.notes.strip():
                print "Notes    :\n\t :", record.notes.encode('utf-8', 'replace').replace("\n", "\n\t : "), "\n"

            print ""

            if pygtk is not None and gtk is not None:
                cb = gtk.clipboard_get()
                cb.set_text(record.passwd)
                cb.store()

    def complete_show(self, text, line, begidx, endidx):
        if not text:
            completions = [record.title for record in self.vault.records]
        else:
            fulltext = line[5:]
            lastspace = fulltext.rfind(' ')
            if lastspace == -1:
                completions = [record.title for record in self.vault.records if record.title.upper().startswith(text.upper())]
            else:
                completions = [record.title[lastspace+1:] for record in self.vault.records if record.title.upper().startswith(fulltext.upper())]

        completions.sort(lambda e1, e2: cmp(e1.title, e2.title))
        return completions

    def find_titles(self, regexp):
        "Finds titles, username, group, or combination of all 3 matching a regular expression. (Case insensitive)"
        matches = []
        pat = re.compile(regexp, re.IGNORECASE)
        for record in self.vault.records:
            if pat.match(record.title) is not None:
                matches.append(record)
            elif pat.match(record.user) is not None:
                matches.append(record)
            elif pat.match(record.group) is not None:
                matches.append(record)
            elif pat.match(record.group+"."+record.title+" ["+record.user+"]") is not None:
                matches.append(record)

        if len(matches) == 0:
            return None
        else:
            return matches


def main(argv):
    # Options
    usage = "usage: %prog [options] [Vault.psafe3]"
    parser = OptionParser(usage=usage)
    parser.add_option("-l", "--ls", dest="do_ls", default=False, action="store_true", help="list contents of vault")
    parser.add_option("-s", "--show", dest="do_show", default=None, action="store", type="string", help="show entries matching REGEX", metavar="REGEX")
    parser.add_option("-i", "--interactive", dest="interactive", default=False, action="store_true", help="use command line interface")
    parser.add_option("-p", "--password", dest="passwd", default=False, action="store_true", help="Auto adds password to clipboard. (GTK Only)")
    parser.add_option("-e", "--echo", dest="echo", default=False, action="store_true", help="Causes password to be displayed on the screen")
    (options, args) = parser.parse_args()

    interactiveConsole = InteractiveConsole()

    if (len(args) < 1):
        if (config.recentvaults):
            interactiveConsole.vault_file_name = config.recentvaults[0]
            print "No Vault specified, using " + interactiveConsole.vault_file_name
        else:
            print "No Vault specified, and none found in config."
            sys.exit(2)
    elif (len(args) > 1):
        print "More than one Vault specified"
        sys.exit(2)
    else:
        interactiveConsole.vault_file_name = args[0]

    interactiveConsole.open_vault()
    if options.do_ls:
        interactiveConsole.do_ls("")
    elif options.do_show:
        interactiveConsole.do_show(options.do_show, options.echo, options.passwd)
    else:
        interactiveConsole.cmdloop()

    sys.exit(0)


main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = loxodo
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import sys
import os

sys.path.append(os.path.dirname(__file__))
from .ppygui import api as gui

from ...vault import Vault
        
class VaultFrame(gui.CeFrame):
    def __init__(self):
        gui.CeFrame.__init__(self, title="Loxodo CE", action=("Show", self._on_edit), menu="More...")

        self.cb_menu.append("Exit", callback=self._on_exit)
        self.sipp = gui.SIPPref(self)
        
        sizer = gui.VBox()

        self.list = gui.Table(self, columns=["Group", "Title", "User"])
        self.list.bind(itemactivated=self._on_item_activated)
        self.list.adjust_all()

        sizer.add(self.list, 1)
        self.sizer = sizer

        self.vault_file_name = None
        self.vault_password = None
        self._is_modified = None
        self.vault = None

    def open_vault(self, filename, password):
        """
        Set the Vault that this frame should display.
        """
        self.vault_file_name = None
        self.vault_password = None
        self._is_modified = False
        self.vault = Vault(password, filename=filename)

        self.list.redraw = False
        for record in self.vault.records:
            self.list.rows.append([record.group, record.title, record.user ])
        self.list.redraw = True
        self.list.adjust_all()

        self.vault_file_name = filename
        self.vault_password = password
    
    def _on_edit(self, ev):
        if (len(self.list.rows.selection) < 1):
            return
        index = self.list.rows.selection[0]
        record = self.vault.records[index]
        recordframe = RecordFrame()
        recordframe.set_record(record)
        recordframe.show()

    def _on_item_activated(self, ev):
        self._on_edit(ev)

    def _on_exit(self, ev):
        sys.exit()

class RecordFrame(gui.CeFrame):
    def __init__(self):
        gui.CeFrame.__init__(self, title="Loxodo CE", action=("OK", self._on_ok), menu="More...")
            
        self.cb_menu.append("Exit", callback=self._on_exit)
        self.sipp = gui.SIPPref(self)
        
        sizer = gui.VBox()

        self._table = gui.TBox(6, 2, spacing_x=2, spacing_y=2, cols_expanded=[1], rows_expanded=[5])
        lb_group = gui.Label(self, "Group: ")
        self._table.add(lb_group)
        self._tb_group = gui.Label(self, "")
        self._table.add(self._tb_group)

        lb_title = gui.Label(self, "Title: ")
        self._table.add(lb_title)
        self._tb_title = gui.Label(self, "")
        self._table.add(self._tb_title)

        lb_user = gui.Label(self, "Username: ")
        self._table.add(lb_user)
        self._tb_user = gui.Label(self, "")
        self._table.add(self._tb_user)

        lb_password = gui.Label(self, "Password: ")
        self._table.add(lb_password)
        self._tb_password = gui.Label(self, "")
        self._table.add(self._tb_password)

        lb_url = gui.Label(self, "URL: ")
        self._table.add(lb_url)
        self._tb_url = gui.Label(self, "")
        self._table.add(self._tb_url)

        lb_notes = gui.Label(self, "Notes: ")
        self._table.add(lb_notes)
        self._tb_notes = gui.Label(self, "")
        self._table.add(self._tb_notes)

        sizer.add(self._table, 1)
        self.sizer = sizer

        self._record = None

    def set_record(self, record):
        self._record = record
        self._tb_group.text = self._record.group
        self._tb_title.text = self._record.title
        self._tb_user.text = self._record.user
        self._tb_password.text = self._record.passwd
        self._tb_url.text = self._record.url
        self._tb_notes.text = self._record.notes
    
    def _on_ok(self, ev):
        self.destroy()

    def _on_exit(self, ev):
        sys.exit()

class LoadFrame(gui.CeFrame):
    def __init__(self):
        gui.CeFrame.__init__(self, title="Loxodo CE", action=("Open", self._on_open), menu="More...")
            
        self.cb_menu.append("Exit", callback=self._on_exit)
        self.sipp = gui.SIPPref(self)
        
        sizer = gui.VBox()

        table = gui.TBox(2, 2, spacing_x=2, spacing_y=2)
        lb_vault = gui.Label(self, "Vault: ")
        table.add(lb_vault)

        sizer2 = gui.HBox()
        self._tb_vault = gui.Edit(self, "")
        sizer2.add(self._tb_vault)
        bt_browse = gui.Button(self, "...", action=self._on_browse)
        sizer2.add(bt_browse)

        table.add(sizer2)

        lb_password = gui.Label(self, "Password: ")
        table.add(lb_password)
        self._tb_password = gui.Edit(self, "", password=True)
        table.add(self._tb_password)

        sizer.add(table, 1)
        self.sizer = sizer

    def _on_browse(self, ev):
        ret = gui.FileDialog.open(wildcards=[('Vault (*.psafe3)', '*.psafe3'), ('All (*.*)', '*.*')])
        self._tb_vault.text = ret
        
    def _on_open(self, ev):
        fname = self._tb_vault.text
        passwd = self._tb_password.text.encode('latin1', 'replace')
        vaultframe = VaultFrame()
        vaultframe.open_vault(fname, passwd)
        vaultframe.show()
        #APPLICATION.mainframe = vaultframe

    def _on_exit(self, ev):
        sys.exit()

APPLICATION = None
        
def main():
    APPLICATION = gui.Application(LoadFrame())
    APPLICATION.run()

main()


########NEW FILE########
__FILENAME__ = api
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

#from core import schedule, GuiObject, Event, SizeEvent,\
#    CommandEvent, NotificationEvent, StylusEvent, KeyEvent,

from core import *
from ce import *
from menu import *
from controls import *
from html import *
from sizer import *
from boxing import HBox, VBox, TBox, Spacer
from font import *
from dialog import Dialog
from message import Message
from filedlg import FileDialog
from date import Date, Time
from spin import Spin
from toolbar import ToolBar
from line import HLine, VLine 
from dialoghdr import DialogHeader
from imagelist import ImageList
########NEW FILE########
__FILENAME__ = boxing
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from config import HIRES, HIRES_MULT

class _Wrapper:
    def __init__(self, wrapped, border):
 
        self.wrapped = wrapped
        if HIRES :

            border = tuple(2*val for val in border)
        self.border = border
        
    def size(self, l, t, r, b):
        border = self.border
        
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        w = r-l
        h = b-t
        self.wrapped.move(l, t, w, h)
        
    def get_best_size(self):
        visible = True
        try:
            visible = self.wrapped._visible
        except: pass
        
        if not visible:
            bx, by = 0, 0
        else:
            bx, by = self.wrapped.get_best_size()
        if bx is not None:
            if HIRES:
                bx += (self.border[0]+self.border[2])/2
            else:
                bx += self.border[0]+self.border[2]
        if by is not None:
            if HIRES:
                by += (self.border[1]+self.border[3])/2
            else:
                by += self.border[1]+self.border[3]
        return bx, by
        
    def _hide(self):
        if isinstance(self.wrapped, (_Box, TBox)):
            self.wrapped.hide()
        else:
            self.wrapped.move(0, 0, 0, 0)
        
class _Box:
    def __init__(self, border=(0,0,0,0), spacing=0):
        self._childs = []
        if HIRES :
            border = tuple(2*val for val in border)
            spacing *= 2
            
        self.border = border
        self.spacing = spacing
    
    def add(self, child, coeff=0, border=(0, 0, 0, 0)): 
        self._childs.append((_Wrapper(child, border), coeff))
        
    def addfixed(self, child, dim, border=(0,0,0,0)):
        self._childs.append((_Wrapper(child, border), -dim))
        
    def move(self, l, t, w, h):
        self.size(l, t, l+w, t+h)
        
    def hide(self):
        for ch, dim in self._childs:
            ch._hide()
            
class HBox(_Box):
    
    def size(self, l, t, r, b):
        fixed_size = 0
        total_coeff= 0
        childs = []
        for child, coeff in self._childs:
            bx, by = child.get_best_size()
            if HIRES:
                if bx is not None:
                    bx *= 2
                if by is not None:
                    by *= 2
                    
            if coeff == 0:
                if bx is None:
                    total_coeff += 1
                    childs.append((child, 1, 1, by))
                    continue
                
                fixed_size += bx
                childs.append((child, bx, 0, by))
            elif coeff >0:
                total_coeff += coeff
                childs.append((child, coeff, 1, by))
            else:
                if HIRES:
                    coeff *= 2
                fixed_size -= coeff
                childs.append((child, -coeff, 0, by))
        border = self.border    
        
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        sizerw = r - l
        sizerh = b - t
        hoffset = l
        voffset = t
        fixed_size += self.spacing * (len(childs)-1)
         
        first = True
        for child, coeff, expand, by in childs:
            if not first:
                hoffset += self.spacing
            if expand :
                w = (sizerw - fixed_size) * coeff / total_coeff
            else :
                w = coeff
#            if by is None:
            h = sizerh
            dy = 0
#            else:

#                h = by

#                dy = (sizerh - by) / 2
                
            child.size(hoffset, voffset+dy, hoffset+w, voffset+dy+h)
            hoffset += w
            first = False
        
    def get_best_size(self):
        b_x = 0
        b_y = 0
        h_expand = False
        v_expand = False
        for child, coeff in self._childs:
            if h_expand and v_expand:
                break
                
            if coeff:
                h_expand = True
                
            cx, cy =  child.get_best_size()
            if cx is None:
                h_expand = True
            else:
                b_x += cx
            if cy is None:
                v_expand = True
            else:
                if cy > b_y:
                    b_y = cy
        
                    
        if h_expand:
            b_x = None
        else:
            b_x += (self.border[0]+self.border[2])/HIRES_MULT
            if len(self._childs) > 1:
                b_x += self.spacing * (len(self._childs)-1) / HIRES_MULT
        if v_expand:
            b_y = None 
        else:
            b_y += (self.border[1]+self.border[3])/HIRES_MULT
        return b_x, b_y
        
class VBox(_Box):
    
    def size(self, l, t, r, b):
        fixed_size = 0
        total_coeff= 0
        childs = []
        for child, coeff in self._childs:
            if coeff==0:
                by = child.get_best_size()[1]
                if by is None:
                    total_coeff += 1
                    childs.append((child, 1, 1))
                    continue
                if HIRES:
                    by *= 2
                fixed_size += by
                childs.append((child, by, 0))
            elif coeff > 0:
                total_coeff += coeff
                childs.append((child, coeff, 1))
            else:
                if HIRES:
                    coeff *= 2
                fixed_size -= coeff
                childs.append((child, -coeff, 0))
        
        border = self.border    
           
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        sizerw = r - l
        sizerh = b - t
        hoffset = l
        voffset = t
        fixed_size += self.spacing * (len(childs)-1)
        
        first = True
        for child, coeff, expand in childs:
            if not first:
                voffset += self.spacing
            w = sizerw
            if expand > 0 :
                h = (sizerh - fixed_size) * coeff / total_coeff
            else : 
                h = coeff
            child.size(hoffset, voffset, hoffset+w, voffset+h)
            voffset += h
            first = False
            
    def get_best_size(self):
        b_x = 0
        b_y = 0
        h_expand = False
        v_expand = False
        for child, coeff in self._childs:
            if h_expand and v_expand:
                break
                
            if coeff:
                v_expand = True
                
            cx, cy =  child.get_best_size()
            if cx is None:
                h_expand = True
            else:
                if cx > b_x:
                    b_x = cx
            if cy is None:
                v_expand = True
            else:
                b_y += cy
   
        if h_expand:
            b_x = None
        else:
            b_x += (self.border[0]+self.border[2])/HIRES_MULT
        if v_expand:
            b_y = None 
        else:
            b_y += (self.border[1]+self.border[3])/HIRES_MULT
            if len(self._childs) > 1:
                b_y += self.spacing * (len(self._childs)-1) / HIRES_MULT
        return b_x, b_y
        
class TBox:
    def __init__(self, rows, cols, border=(0,0,0,0),
                 spacing_x=0, spacing_y=0,
                 rows_expanded=[], cols_expanded=[]):
        self._rows = rows
        self._cols = cols
        self._childs = []
        self.border = border
        self._spacing_x = spacing_x# * HIRES_MULT
        self._spacing_y = spacing_y# * HIRES_MULT
        self.rows_expanded = set(rows_expanded)
        self.cols_expanded = set(cols_expanded)
        
    def add(self, child, border=(0,0,0,0)):
        self._childs.append(_Wrapper(child, border))
        
    def hide(self):
        for ch in self._childs:
            ch._hide()
            
    def get_best_size(self):
        rows_widths = [0]*self._rows
        cols_widths = [0]*self._cols
        expand_x = bool(self.cols_expanded)
        expand_y = bool(self.rows_expanded)
        
        for n, child in enumerate(self._childs):
            i, j = n%self._cols, n/self._cols
            
            b_x, b_y = child.get_best_size()
            
            if expand_x:
                pass
            elif b_x is not None:
                if b_x > cols_widths[i]:
                    cols_widths[i] = b_x
            else: 
                expand_x = True
            
            if expand_y:
                pass
            elif b_y is not None:
                if b_y > rows_widths[j]:
                    rows_widths[j] = b_y 
            else:
                expand_y = True    
        if expand_x:
            b_x = None
        else:
            b_x = sum(cols_widths)# * HIRES_MULT
            b_x += self._spacing_x * (self._cols-1)
            b_x += self.border[0]+self.border[2]
        if expand_y:
            b_y = None
        else:
            b_y = sum(rows_widths)# * HIRES_MULT
            b_y += self._spacing_y * (self._rows-1)
            b_y += self.border[1]+self.border[3]
        return b_x, b_y
        
    def size(self, l, t, r, b):
#        rows_widths = [0]*self._rows

#        cols_widths = [0]*self._cols
        rows_expanded = self.rows_expanded  #set()
        cols_expanded = self.cols_expanded#set()
        rows_widths = [None if (i in rows_expanded) else 0 for i in xrange(self._rows)]
        cols_widths = [None if (i in cols_expanded) else 0 for i in xrange(self._cols)]
        for n, child in enumerate(self._childs):
            i, j = n%self._cols, n/self._cols
            b_x, b_y = child.get_best_size()
            
            if cols_widths[i] is None:

                pass
#            if i in cols_expanded:

#                cols_widths[i] = None
            elif b_x is None:
                cols_expanded.add(i)
                cols_widths[i] = None
            elif cols_widths[i] < b_x * HIRES_MULT:
                cols_widths[i] = b_x * HIRES_MULT
            
            if rows_widths[j] is None:

                pass    
#            if j in rows_expanded:

#                pass
            if b_y is None:
                rows_expanded.add(j)
                rows_widths[j] = None
            elif rows_widths[j] < b_y * HIRES_MULT:
                rows_widths[j] = b_y * HIRES_MULT
        
        r_fixed_size = sum(width for width in rows_widths if width is not None)
        c_fixed_size = sum(width for width in cols_widths if width is not None)
        r_fixed_size += self._spacing_y * (self._rows-1) * HIRES_MULT
        c_fixed_size += self._spacing_x * (self._cols-1) * HIRES_MULT
        
        border = self.border    
        if HIRES :

            border = tuple(2*val for val in border)
                
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        
        n_rows_expanded = len(rows_expanded)
        n_cols_expanded = len(cols_expanded)
        if n_rows_expanded:
            h_rows_ex = (b-t-r_fixed_size)/n_rows_expanded 
        if n_cols_expanded:
            w_cols_ex = (r-l-c_fixed_size)/n_cols_expanded
        hoffset = l
        voffset = t
        first_child = True
        for n, child in enumerate(self._childs):
            i, j = n%self._cols, n/self._cols
            
            if not first_child:
                if i == 0:
                    hoffset = l
                    voffset += rows_widths[j-1]
                    voffset += self._spacing_y * HIRES_MULT   
            if i in cols_expanded:
                col_width = w_cols_ex
            else:
                col_width = cols_widths[i]
            if j in rows_expanded:
                row_width = h_rows_ex
            else:
                row_width = rows_widths[j]
            
            child.size(hoffset, voffset, hoffset+col_width, voffset+row_width)  
            hoffset += col_width + self._spacing_x * HIRES_MULT
            first_child = False
            
    def move(self, l, t, w, h):
        self.size(l, t, l+w, t+h)
        
class Spacer:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y
        
    def move(self, l, t, w, h):
        pass
        
    def get_best_size(self):
        return self.x, self.y

########NEW FILE########
__FILENAME__ = ce
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from core import *
from config import HIRES_MULT
from controls import TBBUTTONINFO 
from menu import Menu, PopupMenu, MenuWrapper
from toolbar import ToolBar

# FixMe: Refactor these constants
TBIF_STATE = 0x4
TBSTATE_ENABLED = 0x4
TBSTATE_INDETERMINATE = 0x10

SHFullScreen = cdll.aygshell.SHFullScreen
SHFS_SHOWSIPBUTTON = 0x4
SHFS_HIDESIPBUTTON = 0x8
SHCMBF_HIDESIPBUTTON = 0x4

SHInitExtraControls = cdll.aygshell.SHInitExtraControls
SHInitExtraControls()

class SIPPref(Window):
    '''
    A hidden Window that automatically
    controls the Software Input Panel
    according to the control focused in
    the parent window.
    
    It should be instancied after all
    other controls in the parent window
    '''
    _w32_window_class = "SIPPREF"
    _w32_window_style = WS_CHILD
    _id = -1
    
    def __init__(self, parent):
        Window.__init__(self, parent, visible=False)

def make_sippref(parent):
    CreateWindowEx(0, u"SIPPREF", u"", WS_CHILD, -10, -10, 5, 5, parent._w32_hWnd, IdGenerator.next(), GetModuleHandle(0), 0)
    
class CommandBarItem(GuiObject):
    '''\
    Not implemented yet, will be used for managing the main menubar 
    aka command bar
    '''
    def __init__(self, cb_hWnd, index):
        self.cb_hWnd = cb_hWnd
        self.index = index
        
    def set_text(self, txt):
        tbbi = TBBUTTONINFO()
        tbbi.cbSize = sizeof(tbbi)
        tbbi.dwMask = TBIF_TEXT | 0x80000000
        tbbi.pszText = unicode(txt)
        SendMessage(self.cb_hWnd, WM_USER+64, self.index, byref(tbbi))
    
    def enable(self, val=True):
        tbbi = TBBUTTONINFO()
        tbbi.cbSize = sizeof(tbbi)
        tbbi.dwMask = TBIF_STATE | 0x80000000
        if val:
            tbbi.fsState = TBSTATE_ENABLED
        else:
            tbbi.fsState = TBSTATE_INDETERMINATE
        SendMessage(self.cb_hWnd, WM_USER+64, self.index, byref(tbbi))
    
        
    def disable(self):
        self.enable(False)
        
class CommandBarAction(CommandBarItem):
    '''\
    Not implemented yet, will be used for managing the main menubar 
    aka command bar
    '''
    def __init__(self, cb_hWnd, index, menu_item):
        CommandBarItem.__init__(self, cb_hWnd, index)
        self.menu_item = menu_item
    
    def bind(self, cb):
        self.menu_item.bind(cb)   
        
class CommandBarMenu(CommandBarItem, MenuWrapper):
    '''\
    Not implemented yet, will be used for managing the main menubar 
    aka command bar
    '''
    def __init__(self, cb_hWnd, index, hMenu):
        CommandBarItem.__init__(self, cb_hWnd, index)
        MenuWrapper.__init__(self, hMenu)
    

class CeFrame(Frame):
    '''\
    CeFrame is a frame designed to be a Windows CE compliant window.
    A CeFrame will track the SIP position and size and will automatically
    resize itself to always fit the screen.
    '''
    _dispatchers = {"_activate" : (MSGEventDispatcher, WM_ACTIVATE),
                    "_settingchanged" : (MSGEventDispatcher, WM_SETTINGCHANGE),
                    }
    _dispatchers.update(Frame._dispatchers)
    
    def __init__(self, parent=None, 
                       title="PocketPyGui", 
                       action=None, 
                       menu=None,
                       right_action=None, 
                       tab_traversal=True, 
                       visible=True, 
                       enabled=True, 
                       has_sip=True, 
                       has_toolbar=False):
        '''\
        Arguments :
            - parent: the parent window of this CeFrame.
            - title: the title as appearing in the title bar.
            - action : a tuple ('Label', callback) .
            - menu : the title of the right menu as a string
                     if not None, the menu can be filled via the cb_menu attribute
                     after CeFrame initialization.
        '''
        Frame.__init__(self, parent, title, tab_traversal=tab_traversal, visible=visible, enabled=enabled)
        self.bind(_activate=self._on_activate,
                  _settingchanged=self._on_setting_changed,
                  size=self._on_size)
        if has_toolbar :
            self.toolbar = ToolBar(self)
        else:
            self.toolbar = None
        self.__create_menubar(action, menu, right_action, has_sip)
        
        
    def _on_size(self, ev):
        if ev.wParam == 1:
            self.close()
        else:
            self.layout()
        ev.skip()
        
    def layout(self):
        if self.toolbar is None:
            return Frame.layout(self)
        if self._sizer is not None:
            rc = RECT()
            GetClientRect(self._w32_hWnd, byref(rc))
            self._sizer.size(rc.left, rc.top, rc.right, rc.bottom-24*HIRES_MULT)
            self.toolbar.move(rc.left, rc.bottom-26*HIRES_MULT, rc.right-rc.left, 26*HIRES_MULT)
    
    
    def __create_menubar(self, action, menu, right_action, has_sip):
        mbi = SHMENUBARINFO()
        mbi.cbSize = sizeof(SHMENUBARINFO)
        mbi.hwndParent = self._w32_hWnd
        mbi.hInstRes = GetModuleHandle(0)
        
        slots = []
        
        empty = True
        has_action = False
        has_menu = False
        has_right_action = False
        
        if (action is None) and (menu is None) :
            mbi.dwFlags = SHCMBF_EMPTYBAR
            
        else :
            empty = False
            temp_menu = Menu()
            i = 0
            if action is not None:
                label, cb = action
                action_item = temp_menu.append(label, callback=cb)
                #self.action = CommandBarAction(item, 0)
            else:
                action_item = temp_menu.append("", enabled=False)
              
            if right_action is not None:
                label, cb = right_action
                right_action_item = temp_menu.append(label, callback=cb)
                has_right_action = True
            elif menu is not None:
                sub_menu = PopupMenu()
                temp_menu.append_menu(menu, sub_menu) 
                has_menu = True
                
            mbi.dwFlags = SHCMBF_HMENU
            mbi.nToolBarId = temp_menu._hmenu
            
        if not has_sip:
            mbi.dwFlags |= SHCMBF_HIDESIPBUTTON
        SHCreateMenuBar(byref(mbi))
        self._mb_hWnd = mbi.hwndMB
        
        if not empty:
            self.cb_action = CommandBarAction(mbi.hwndMB, 0, action_item)
            if has_right_action:
                self.cb_right_action = CommandBarAction(mbi.hwndMB, 1, right_action_item)
            elif has_menu:
                tbbi = TBBUTTONINFO()
                tbbi.cbSize = sizeof(tbbi)
                tbbi.dwMask = 0x10 | 0x80000000
                SendMessage(mbi.hwndMB, WM_USER+63, 1, byref(tbbi))
                hMenu = tbbi.lParam         
                self.cb_menu = CommandBarMenu(mbi.hwndMB, 1, hMenu)
        
        rc = RECT()
        GetWindowRect(self._w32_hWnd, byref(rc))
        rcmb = RECT()
        GetWindowRect(self._mb_hWnd, byref(rcmb))
        rc.bottom -= (rcmb.bottom - rcmb.top)
        self.move(rc.left, rc.top, rc.right-rc.left, rc.bottom-rc.top)
        
    def _on_activate(self, event):
        if not hasattr(self, '_shai'):
            self._shai = InitSHActivateInfo()
        SHHandleWMActivate(event.hWnd, event.wParam, event.lParam, byref(self._shai), 0)
    
    def _on_setting_changed(self, event):
        if not hasattr(self, '_shai'):
            self._shai = InitSHActivateInfo()
        SHHandleWMSettingChange(self._w32_hWnd, event.wParam, event.lParam, byref(self._shai))

    def show_sipbutton(self, show=True):
        if show:
            SHFullScreen(self._w32_hWnd, SHFS_SHOWSIPBUTTON)
        else:
            SHFullScreen(self._w32_hWnd, SHFS_HIDESIPBUTTON)
        
    def hide_sipbutton(self):
        self.show_sipbutton(False)

########NEW FILE########
__FILENAME__ = config
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from ctypes import cdll

GetSystemMetrics = cdll.coredll.GetSystemMetrics
SM_CXSCREEN = 0
SM_CYSCREEN = 1

def get_resolution():
    rx = GetSystemMetrics(SM_CXSCREEN)
    ry = GetSystemMetrics(SM_CYSCREEN)
    if ry > rx:
        return rx, ry
    return ry, rx
    
rx, ry = get_resolution()

if rx>320 and ry>240:
    HIRES = True
    HIRES_MULT = 2
else:
    HIRES = False
    HIRES_MULT = 1
########NEW FILE########
__FILENAME__ = controls
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from core import *
from w32comctl import *
from config import HIRES_MULT
from boxing import VBox

__doc__ = '''\
This module contains the core high-level widgets of ppygui.
See also ppygui.html for the HTML control.
'''

class Label(Control):
    '''\
    The Label control displays a static text.
    Events:
        - clicked -> CommandEvent
    '''
    _w32_window_class = "STATIC"
    _w32_window_style = WS_CHILD 
    _dispatchers = {'clicked' : (CMDEventDispatcher, ),
                    }
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, title="", align="left", border=False, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''\
        Arguments:
            - parent: the parent window.
            - title: the text to be displayed.
            - align: the text alignment in its window, can be "left", "center" or "right".
            - border: a boolean that determines if this control should have a border.
        '''
        if align not in ["left", "center", "right"]:
            raise ValueError, 'align not in ["left", "center", "right"]'
            
        orStyle = SS_NOTIFY
        if align == "center":
            orStyle |= SS_CENTER
        elif align == "right":
            orStyle |= SS_RIGHT
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, title, border, visible, enabled, pos, tab_stop=False,  **kw)
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text
        cx, cy = GetTextExtent(dc, text)
        cy = cy*(1+text.count('\n'))
        return 5+cx/HIRES_MULT, 2+cy/HIRES_MULT
        
class Button(Control):
    '''\
    The button control displays a command button,
    it can be a push button, a default button, or
    a check box.
    For a radio button see the RadioButton class
    Events :
        - clicked -> CommandEvent
    '''
    
    _w32_window_class = "BUTTON"
    _w32_window_style = WS_CHILD
    _dispatchers = {'clicked' : (CMDEventDispatcher, )}
    _dispatchers.update(Control._dispatchers)
    _defaultfont = ButtonDefaultFont
    
    def __init__(self, parent, title="", action=None, align="center", style="normal", border=False, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''
        Arguments:
            - title: the text of the button.
            - action: the callback called when the button is clicked (equivalent to button.bind(clicked=callback))
            - align: the text alignment, can be "left", "center" or "right".
            - style:
                - "normal" for a classic push button
                - "default" for a default push button
                - "check" for a check box
            - border: a boolean that determines if this control should have a border.
        '''
        if align not in ["left", "center", "right"]:
            raise ValueError, 'align not in ["left", "center", "right"]'
        if style not in ["normal", "default", "check", "radio"]:
            raise ValueError, 'style not in ["normal", "default", "check", "radio"]'
        orStyle = 0
        self._check = False
        if style == "normal" :
            orStyle |= BS_PUSHBUTTON
        elif style == "default" :
            orStyle |= BS_DEFPUSHBUTTON
        elif style == "check" :
            orStyle |= BS_AUTOCHECKBOX
            self._defaultfont = DefaultFont
            self._check = True
        elif style == "radio" :
            orStyle |= BS_RADIOBUTTON
            self._defaultfont = DefaultFont
        if align == "left":
            orStyle |= BS_LEFT
        elif align == "right":
            orStyle |= BS_RIGHT
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, title, border, visible, enabled, pos, **kw)
        
        if action is not None:
            self.bind(clicked=action)
        
        self._best_size = None
            
    def get_checked(self):
        '''\
        getter for property checked
        '''
        check = self._send_w32_msg(BM_GETCHECK)
        if check == BST_CHECKED :
            return True
        return False
        
    def set_checked(self, check):
        '''\
        setter for property checked
        '''
        if check :
            w32_check = BST_CHECKED
        else :
            w32_check = BST_UNCHECKED
        self._send_w32_msg(BM_SETCHECK, w32_check)
        
    doc_checked = "Returns or set the checked state of a button as a boolean (makes only sense for a button created with check or radio style)"
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, self.text)
        if self._check:
            return 20+cx/HIRES_MULT, 4+cy/HIRES_MULT
        return 10+cx/HIRES_MULT, 10+cy/HIRES_MULT
        

class RadioButton(Button):
    '''
    The RadioButton control displays a classic radio button,
    it belongs to a RadioGroup, which owns mutually exclusive radio buttons,
    and is bound to a value (any python object) that is useful for retrieving in
    the radio group.
    '''
    def __init__(self, parent, title="", align="center", group=None, value=None, border=False, visible=True, enabled=True, selected=False, pos=(-1,-1,-1,-1), **kw):
        '''
        Arguments:
            - title: the text of the button.
            - action: the callback called when the button is clicked (equivalent to button.bind(clicked=callback))
            - align: the text alignment, can be "left", "center" or "right".
            - group: the group of the radio as a RadioGroup instance or None.
            - value: any python object bound to the RadioButton
            - border: a boolean that determines if this control should have a border.
        '''
        Button.__init__(self, parent, title=title, style="radio", action=None, align=align, pos=pos, border=border, visible=visible, enabled=enabled, **kw)
        
        if group is not None:
            if not isinstance(group, RadioGroup):
                raise TypeError("arg group must be a RadioGroup instance or None")
            group._add(self)
            if selected:
                group.selection = self
        self._value = value
    
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        
        font = self._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, self.text)
        return 20 + cx/HIRES_MULT, 4+cy/HIRES_MULT
            
class RadioGroup(GuiObject):
    '''\
    Represents a group of mutually exclusive RadioButton
    Events:
        - update -> NoneType: sent when one of the radio buttons is clicked.
    '''
    
    def __init__(self):
        self._radios = []
        self.updatecb = None
        self._selection = None
        
    def bind(self, update=None):
        self.updatecb = update
        
    def _add(self, button):
        assert isinstance(button, RadioButton)
        self._radios.append(button)
        button.bind(clicked=self._onbuttonclicked)
        
    def get_selection(self):
        '''\
        getter for property selection
        '''
        return self._selection
        
    def set_selection(self, button):
        '''\
        setter for property selection
        '''
        assert button in self._radios #Fixme: raise ValueError instead of assertions
        for radio in self._radios :
            if button is radio :
                radio.checked = True
                self._selection = button
            else :
                radio.checked = False
    
    doc_selection = '''\
    The current selected radio as a Button instance, 
    if the button does not belong to this group it is an error"
    '''  
        
    def get_value(self):
        '''\
        getter for property value
        '''
        if self._selection is not None :
            return self._selection._value
            
    doc_value = "The value of the selected radio button"
        
    def _onbuttonclicked(self, event):
        button = event.window
        self.selection = button
        if self.updatecb is not None:
            self.updatecb(None)
            
class Edit(Control):
    '''\
    The edit control displays an editable text field. 
    Supported events :
        - update -> CommandEvent: sent when the text is updated by the user
    '''
    _w32_window_class = "EDIT"
    _w32_window_style = WS_CHILD
    _dispatchers = {'enter' : (CustomEventDispatcher,),
                    'update' : (CMDEventDispatcher, EN_UPDATE)}
    _dispatchers.update(Control._dispatchers)
    
    
    def __init__(self, parent, text="", align="left", style="normal", password=False, multiline = False, line_wrap=False, readonly=False, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''\
        Arguments:
            - parent : the parent window
            - text : the initial text to display
            - align : the text alignment, can be "left", "center" or "right"
            - style :
                - normal : standard text field
                - number : accept numeric input only
            - password : a boolean that determines if the user input should be masked
            - multiline : a boolean that determines if the text should contain newlines
            - readonly : a boolean that determines if the text should be viewed only
            - border: a boolean that determines if this control should have a border.
        '''
        assert align in ["left", "center", "right"] #Fixme: raise ValueError instead of assertions
        assert style in ["normal", "number"] #idem
        #orStyle = ES_AUTOHSCROLL 
        orStyle = 0
        if style == "number" :
            orStyle |= ES_NUMBER
        if align == "center":
            orStyle |= ES_CENTER
        elif align == "left" :
            orStyle |= ES_LEFT
        elif align == "right":
            orStyle |= ES_RIGHT

        if password :
            orStyle |= ES_PASSWORD
        if multiline :
            self._multiline = True
            orStyle |= WS_VSCROLL | ES_AUTOVSCROLL | ES_MULTILINE | ES_WANTRETURN
            if not line_wrap:
                orStyle |= WS_HSCROLL
        else:
            self._multiline = False
            orStyle |= ES_AUTOHSCROLL
                
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, text, border, visible, enabled, pos)
        self.set(readonly=readonly, **kw)
        self._best_size = None
        
    def _get_best_size(self):
        if self._multiline:
            return None, None
        
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text
        cx, cy = GetTextExtent(dc, text)
        return None, 7+cy/HIRES_MULT
        
    def get_readonly(self):
        '''\
        getter for property readonly
        '''
        style = GetWindowLong(self._w32_hWnd, GWL_STYLE)
        return bool(style & ES_READONLY)
        
    def set_readonly(self, val):
        '''\
        setter for property readonly
        '''
        self._send_w32_msg(EM_SETREADONLY, int(val))
    
    doc_readonly = "The read-only state of the edit as a boolean"
    
    def get_selection(self):
        '''\
        getter for property selection
        '''
        start = LONG()
        stop = LONG()
        self._send_w32_msg(EM_GETSEL, byref(start), byref(stop))
        return start.value, stop.value 
        
    def set_selection(self, val):
        '''\
        setter for property selection
        '''
        start, stop = val
        self._send_w32_msg(EM_SETSEL, start, stop)
    
    doc_selection = "The zero-based index selection as a tuple (start, stop)"

    def append(self, text):
        oldselect = self.selection
        n = self._send_w32_msg(WM_GETTEXTLENGTH)
        self.selection = n, n
        self.selected_text = text
        self.selection = oldselect
        
    def select_all(self):
        self.selection = 0, -1

    def get_modified(self):
        return bool(self._send_w32_msg(EM_GETMODIFY))
        
    def set_modified(self, mod):
        return self._send_w32_msg(EM_SETMODIFY, int(mod))

    def get_selected_text(self):
        txt = self.text
        start, end = self.selection
        return txt[start:end]
        
    def set_selected_text(self, txt):
        self._send_w32_msg(EM_REPLACESEL, 1, unicode(txt))
        
    def can_undo(self):
        '''\
        Return a bool that indicates if the current content can be undone
        '''
        return bool(self._send_w32_msg(EM_CANUNDO))
        
    def undo(self):
        '''\
        Undo the current content
        '''
        self._send_w32_msg(EM_UNDO)
        
    def cut(self):
        '''\
        Cut the current selection in the clipboard
        '''
        self._send_w32_msg(WM_CUT)
        
    def copy(self):
        '''\
        Copy the current selection in the clipboard
        '''
        self._send_w32_msg(WM_COPY)
    
    def paste(self):
        '''\
        Paste the content of the clipboard at the current position
        '''
        self._send_w32_msg(WM_PASTE)
    
    # Not tested    
    def line_from_char(self, i):
        return self._send_w32_msg(EM_LINEFROMCHAR, i)
        
    def line_index(self, i):
        return self._send_w32_msg(EM_LINEINDEX, i)
        
    def line_length(self, i):
        return self._send_w32_msg(EM_LINELENGTH, i)
  
class List(Control):
    '''
    The List control displays a list of choice
    Supported events :
    - choicechanged -> CommandEvent : sent when user selection has changed
    - choiceactivated -> CommandEvent : sent when the user double-click on a choice
    '''
    _w32_window_class = "ListBox"
    _w32_window_style = WS_CHILD | LBS_NOTIFY | WS_VSCROLL | LBS_HASSTRINGS
    _dispatchers = {'selchanged' : (CMDEventDispatcher, LBN_SELCHANGE),
                    'itemactivated' : (CMDEventDispatcher, LBN_DBLCLK)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, choices=[], sort=False, multiple=False, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''
        - choices : the initial possible choices as a list of string
        - sort : True if the choices have to be sorted in alphabetical order
        - multiple : True if the control should allow multiple selection
        ''' 
        orStyle = 0        
        self.multiple = multiple
        if sort :
            orStyle |= LBS_SORT
        if multiple :
            orStyle |= LBS_MULTIPLESEL
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, "", border, visible, enabled, pos)
        
        for choice in choices :
            self.append(choice)
    
        self.set(**kw)
        
    def get_count(self):
        '''
        Returns the number of choices in the control
        '''
        return self._send_w32_msg(LB_GETCOUNT)
        
    doc_count = "The number of choices in the control"
    
    def append(self, choice):
        '''
        Adds the string choice to the list of choices
        '''
        self._send_w32_msg(LB_ADDSTRING, 0, unicode(choice))
        
    def insert(self, i, choice):
        '''
        Inserts the string choice at index i
        '''
        self._send_w32_msg(LB_INSERTSTRING, i, unicode(choice))
           
    def __getitem__(self, i):
        '''
        Returns the choice at index i as a string
        '''
        if not 0<=i<self.count:
            raise IndexError
        textLength = self._send_w32_msg(LB_GETTEXTLEN, i)# + 1
        textBuff = create_unicode_buffer(textLength+1)
        self._send_w32_msg(LB_GETTEXT, i, textBuff)
        return textBuff.value
        
    def __setitem__(self, i, text):
        '''\
        Sets the choice at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
        del self[i]
        self.insert(i, text)
    
    def __delitem__(self, i):
        '''
        Removes the choice at index i
        '''
        self._send_w32_msg(LB_DELETESTRING, i)
        
    def delete_all(self):
        for i in range(self.count):
            del self[0]
            
    def is_multiple(self):
        '''
        Returns True if the Choice control allows 
        multiple selections
        '''
        return self.multiple
        
    def get_selection(self):
        '''
        Returns the current selection as an index or None in a single-choice
        control , or a list of index in a multiple-choice control
        '''  
        if not self.multiple :
            sel = self._send_w32_msg(LB_GETCURSEL)
            if sel >= 0 :
                return sel
        else :
            selections = []
            for i in range(self.count):
                if self._send_w32_msg(LB_GETSEL, i) > 0 :
                    selections.append(i)
            return selections
        
    def set_selection(self, selection):
        '''
        Sets the current selection as a list of index,
        In the case of a single-choice control, it accepts
        an index or will use the first index in the list
        ''' 
        try :
            len(selection)
        except TypeError :
            selection = [selection]
        if not self.multiple :
            return self._send_w32_msg(LB_SETCURSEL, selection[0])
        else :
            self._send_w32_msg(LB_SETSEL, 0, -1)
            for i in selection :
                self._send_w32_msg(LB_SETSEL, 1, i)
        
    doc_selection = "The current selection(s) as a list of index"
    
    def __iter__(self):
        return choiceiterator(self)
    
    
def choiceiterator(choice):
    for i in range(choice.count):
        yield choice[i]

class TableColumns(GuiObject):
    '''
    TableColumns instance are used to manipulate
    the columns of the bounded Table object
    '''
    def __init__(self, list, columns):
        '''
        Do not use this constructor directly
        it is instantiated automatically by Table
        '''
        self._list = list
        self._count = 0
        for title in columns :
            self.append(title)
            
    def __len__(self):
        return self._count
        
    def append(self, title, width=-1, align="left"):
        '''
        Adds a new column to the bounded table
        - title : the text of the column
        - width : the width of the column in pixels, -1 will set the width so that it contains the title
        - align : the alignment of the column, can be "left", "center" or "right"
        Returns the index of the newly created column
        '''
        i = len(self)
        return self.insert(i, title, width, align)

        
    def insert(self, i, title, width=-1, align="left"):
        '''
        Inserts a new column to the bounded table at index i
        - title : the text of the column
        - width : the width of the column in pixels, -1 will set the width so that it contains the title
        - align : the alignment of the column, can be "left", "center" or "right"
        Returns the index of the newly created column
        '''
        if not 0 <= i <= len(self):
            raise IndexError
        assert align in ["left", "center", "right"]
        col = LVCOLUMN()
        col.text = unicode(title)
        col.width = width
        if align == "left" :
            fmt = LVCFMT_LEFT
        elif align == "right" :
            fmt = LVCFMT_RIGHT
        elif align == "center" :
            fmt = LVCFMT_CENTER
            

        col.format = fmt
        self._list._insertcolumn(i, col)
        self._count += 1
        if width == -1 :
            self.adjust(i)
        return i
        
    def set(self, i, title=None, width=None, align=None):
        '''
        Sets the column of the bounded table at index i
        - title : the text of the column
        - width : the width of the column in px
        - align : the alignment of the column, can be "left", "center" or "right" (can produce artifacts)
        '''
        if not 0<=i<len(self):
            raise IndexError
        col = LVCOLUMN()
        if title is not None :
            col.text = title
        if width is not None :
            col.width = width
        if align is not None :
            assert align in ["left", "center", "right"]
            if align == "left" :
                fmt = LVCFMT_LEFT
            elif align == "right" :
                fmt = LVCFMT_RIGHT
            elif align == "center" :
                fmt = LVCFMT_CENTER
                

            col.format = fmt
        self._list._setcolumn(i, col)
        
    def adjust(self, i):
        '''
        Adjust the column width at index i
        to fit the header and all the texts in 
        this column.
        '''        
        if not 0<=i<len(self):
            raise IndexError
        self._list._send_w32_msg(LVM_SETCOLUMNWIDTH, i, -2)
            
    #def remove(self, column):
    #    pass
    def __delitem__(self, i):
        '''
        Removes the column at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._list._send_w32_msg(LVM_DELETECOLUMN, i)
        self._count -= 1
        
class TableRows(GuiObject):
    
    def __init__(self, list):
        '''
        Do not use this constructor directly,
        it is instantiated automatically by Table
        '''
        self._list = list
        self._data = []
    
    def __len__(self):
        return self._list._send_w32_msg(LVM_GETITEMCOUNT)
        
    def append(self, row, data=None):
        '''
        Adds a new row at the end of the list
        - row : a list of string
        - data : any python object that you want to link to the row
        '''
        self.insert(len(self), row, data)
        
    def insert(self, i, row, data=None):
        '''
        Inserts a new row at index i
        - row : a list of string
        - data : any python object that you want to link to the row
        '''
        if not 0<=i<=len(self):
            raise IndexError
        item = LVITEM()
        item.mask = LVIF_TEXT | LVIF_PARAM
        item.iItem = i
        #item.lParam = data
        item.iSubItem = 0
        item.pszText = row[0]
        self._list._insertitem(item)
        for iSubItem in range(len(row) - 1):
            item.mask = LVIF_TEXT
            item.iSubItem = iSubItem + 1
            item.pszText = row[iSubItem + 1]
            self._list._setitem(item)
        
        if i == len(self) - 1:
            self._data.append(data)
        else :
            self._data.insert(i, data)
        
    def __setitem__(self, i, row):
        '''
        Sets the row at index i as a list of string
        '''
        if not 0<=i<len(self):
            raise IndexError
        item = LVITEM()
        item.mask = LVIF_TEXT | LVIF_PARAM
        item.iItem = i
        #item.lParam = data
        item.iSubItem = 0
        item.pszText = row[0]
        self._list._setitem(item)
        for iSubItem in range(len(row) - 1):
            item.mask = LVIF_TEXT
            item.iSubItem = iSubItem + 1
            item.pszText = row[iSubItem + 1]
            self._list._setitem(item)
            
    def setdata(self, i, data):
        '''
        Bind any python object to the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._data[i] = data
        
    def __getitem__(self, i):
        '''
        Returns the row at index i as a list of string
        '''
        if not 0<=i<len(self):
            raise IndexError
        row = []
        for j in range(len(self._list.columns)):
            item = self._list._getitem(i, j)
            row.append(item.pszText)
            
        return row
        
    def getdata(self, i):
        '''
        Returns any python object that was bound to the row or None
        '''
        if not 0<=i<len(self):
            raise IndexError
        return self._data[i]
    
    #TODO: implement image api
    def getimage(self, i):
        pass
        
    def setimage(self, i, image_index):
        pass
        
    def getselected_image(self, i):
        pass
        
    def setselected_image(self, i, image_index):
        pass
    
    def ensure_visible(self, i):
        '''
        Ensures the row at index i is visible
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._send_w32_msg(LVM_ENSUREVISIBLE, i)
    
    def is_selected(self, i):
        '''
        Returns True if the row at index i is selected
        '''
        if not 0<=i<len(self):
            raise IndexError
            
        item = LVITEM()
        item.iItem = i
        item.mask = LVIF_STATE
        item.stateMask = LVIS_SELECTED
        self._list._send_w32_msg(LVM_GETITEM, 0, byref(item))
        return bool(item.state)
        
    def select(self, i):
        '''
        Selects the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        item = LVITEM()
        item.iItem = i
        item.mask = LVIF_STATE
        item.stateMask = LVIS_SELECTED
        item.state = 2
        self._list._send_w32_msg(LVM_SETITEM, 0, byref(item))
    
    def deselect(self, i):
        '''
        deselects the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        item = LVITEM()
        item.iItem = i
        item.mask = LVIF_STATE
        item.stateMask = LVIS_SELECTED
        item.state = 0
        self._list._send_w32_msg(LVM_SETITEM, 0, byref(item))
        
    def get_selection(self):
        '''
        Get the current selections as a list
        of index
        '''
        l = []
        i = -1
        list = self._list
        while 1:
            i = list._send_w32_msg(LVM_GETNEXTITEM, i, LVNI_SELECTED)
            if i != -1:
                l.append(i)
            else:
                break
        return l
        
    def get_selected_count(self):
        return self._list._send_w32_msg(LVM_GETSELECTEDCOUNT)
        
    doc_selected_count = "The number of rows selected as an int (read-only)"
    
    def set_selection(self, selections):
        '''
        Sets the current selections as a list
        of index
        '''
        try :
            len(selections)
        except TypeError:
            selections = [selections]
        for i in xrange(len(self)):
            self.unselect(i)
            
        for i in selections:
            self.select(i)
    
    doc_selection = "The current selection(s) as a list of index"
        
    def __delitem__(self, i):
        '''
        del list.rows[i] : removes the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._list._send_w32_msg(LVM_DELETEITEM, i) 
        del self._data[i]

class Combo(Control):
    _w32_window_class = "COMBOBOX"
    _w32_window_style = WS_CHILD | CBS_AUTOHSCROLL | CBS_DISABLENOSCROLL | WS_VSCROLL
    _dispatchers = {'selchanged' : (CMDEventDispatcher, CBN_SELCHANGE)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, style="edit", sort=False, choices=[], visible=True, enabled=True, pos=(-1,)*4, **kw):
        assert style in ["edit", "list"]
        orStyle = 0
        if style == "edit":
            orStyle |=  CBS_DROPDOWN
        elif style == "list":
            orStyle |= CBS_DROPDOWNLIST
        if sort :
            orStyle |= CBS_SORT
                
        self._w32_window_style |= orStyle
        
        Control.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        for choice in choices :
            self.append(choice)
        self.set(**kw)
        self._best_size = None
        
    def move(self, l, t, w, h):
        Control.move(self, l, t, w, h+(HIRES_MULT*150))
        
    def get_count(self):
        return self._send_w32_msg(CB_GETCOUNT)
        
    def append(self, txt):
        self._send_w32_msg(CB_ADDSTRING, 0, unicode(txt))
        self._best_size = None
        
    def insert(self, i, txt):
        if not 0<=i<self.count:
            raise IndexError
        self._send_w32_msg(CB_INSERTSTRING, i, unicode(txt))
        self._best_size = None
        
    def get_selection(self):
        cursel = self._send_w32_msg(CB_GETCURSEL)
        if cursel != -1 :
            return cursel
            
    def set_selection(self, i):
        if i is None :
            self._send_w32_msg(CB_SETCURSEL, -1)
        else :
            if not 0<=i<self.count:
                raise IndexError
            self._send_w32_msg(CB_SETCURSEL, i)
        
    def drop_down(self, show=True):
        self._send_w32_msg(CB_SHOWDROPDOWN, int(show))
    
    def __getitem__(self, i):
        '''
        Returns the item at index i as a string
        '''
        if not 0<=i<self.count:
            raise IndexError
        textLength = self._send_w32_msg(CB_GETLBTEXTLEN, i)# + 1
        textBuff = create_unicode_buffer(textLength+1)
        self._send_w32_msg(CB_GETLBTEXT, i, textBuff)
        return textBuff.value
        
    def __setitem__(self, i, text):
        '''\
        Sets the choice at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
        del self[i]
        self.insert(i, text)
            
    def __delitem__(self, i):
        if not 0<=i<self.count:
            raise IndexError
        self._send_w32_msg(CB_DELETESTRING, i)    
        self._best_size = None
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, '')
        for i in range(self.count):
            current_cx, cy = GetTextExtent(dc, self[i])
            if current_cx > cx:
                cx = current_cx
        return cx/HIRES_MULT+20, 8+cy/HIRES_MULT

    def get_font(self):
        return Control.get_font(self)
            
    def set_font(self, value):
        Control.set_font(self, value)
        self._best_size = None
        
    def get_best_size(self):
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
            
class TableEvent(NotificationEvent):
    
    def __init__(self, hWnd, nMsg, wParam, lParam):
        NotificationEvent.__init__(self, hWnd, nMsg, wParam, lParam)
        nmlistview = NMLISTVIEW.from_address(lParam)
        self._index = nmlistview.iItem
        self._colindex = nmlistview.iSubItem
        self.new_state = nmlistview.uNewState
        self.changed = nmlistview.uChanged
        self.selected = bool(self.new_state)
        
    def get_index(self):
        return self._index
        
    def get_columnindex(self):
        return self._colindex
            
class TreeEvent(NotificationEvent):
    
    def __init__(self, hWnd, nMsg, wParam, lParam):
        NotificationEvent.__init__(self, hWnd, nMsg, wParam, lParam)
        self.nmtreeview = NMTREEVIEW.from_address(lParam)
        hwnd = self.nmtreeview.hdr.hwndFrom
        self._tree = hwndWindowMap[hwnd]
        
    def get_old_item(self):
        hItem = self.nmtreeview.itemOld.hItem
        if hItem != 0:
            return TreeItem(self._tree, hItem)
        
    def get_new_item(self):
        hItem = self.nmtreeview.itemNew.hItem
        if hItem != 0:
            return TreeItem(self._tree, hItem)
            
class Table(Control):
    '''
    The Table control :
    Columns are manipulated via the TableColumns instance variable columns
    Rows are manipulated via the TableRows instance variable rows
    You can get or set the text at row i, column j by indexing list[i, j] 
    '''
    _w32_window_class = WC_LISTVIEW
    _w32_window_style = WS_CHILD | LVS_REPORT #| LVS_EDITLABELS 

    _dispatchers = {"selchanged" : (NTFEventDispatcher, LVN_ITEMCHANGED, TableEvent),
                    "itemactivated" : (NTFEventDispatcher, LVN_ITEMACTIVATE, TableEvent),
                    }
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, columns=[], autoadjust=False, multiple=False, has_header=True, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''
        - columns : a list of title of the initial columns
        - autoadjust : whether the column width should be automatically adjusted
        - multiple : whether the table should allow multiple rows selection
        - has_header : whether the table displays a header for its columns
        '''
        if not multiple :
            self._w32_window_style |= LVS_SINGLESEL
        if not has_header:
            self._w32_window_style |= LVS_NOCOLUMNHEADER
        
        Control.__init__(self, parent, border=border, visible=visible, enabled=enabled, pos=pos)
        self._set_extended_style(LVS_EX_FULLROWSELECT|LVS_EX_HEADERDRAGDROP|0x10000)
        
        self.columns = TableColumns(self, columns)
        self.rows = TableRows(self)
        self._autoadjust = autoadjust
        
        self._multiple = multiple
        self.set(**kw)
        
    def _set_extended_style(self, ex_style):
        self._send_w32_msg(LVM_SETEXTENDEDLISTVIEWSTYLE, 0, ex_style)
    
    def is_multiple(self):
        return bool(self._multiple)
    
    def _insertcolumn(self, i, col):
        return self._send_w32_msg(LVM_INSERTCOLUMN, i, byref(col))

    def _setcolumn(self, i, col):
        return self._send_w32_msg(LVM_SETCOLUMN, i, byref(col))

    def _insertitem(self, item):
        self._send_w32_msg(LVM_INSERTITEM, 0, byref(item))
        if self._autoadjust:
            self.adjust_all() 
            
    def _setitem(self, item):
        self._send_w32_msg(LVM_SETITEM, 0, byref(item))
        if self._autoadjust:
            self.adjust_all() 
            
    def _getitem(self, i, j):
        item = LVITEM()
        item.mask = LVIF_TEXT | LVIF_PARAM
        item.iItem = i
        item.iSubItem = j
        item.pszText = u" "*1024

        item.cchTextMax = 1024
        self._send_w32_msg(LVM_GETITEM, 0, byref(item))
        return item
        
    def adjust_all(self):
        '''
        Adjusts all columns in the list
        '''
        for i in range(len(self.columns)):
            self.columns.adjust(i)
    
    def __getitem__(self, pos):
        '''
        list[i, j] -> Returns the text at the row i, column j
        '''
        i, j = pos
        if not 0 <= i < len(self.rows):
            raise IndexError
        if not 0 <= j < len(self.columns):
            raise IndexError
                
        item = self._getitem(i, j)
        return item.pszText
        
    def __setitem__(self, pos, val):
        '''
        list[i, j] = txt -> Set the text at the row i, column j to txt
        '''
        i, j = pos
        if not 0 <= i < len(self.rows):
            raise IndexError
        if not 0 <= j < len(self.columns):
            raise IndexError
        
        item = LVITEM()
        item.mask = LVIF_TEXT 
        item.iItem = i
        item.iSubItem = j
        item.pszText = unicode(val)
        self._setitem(item)
        return item
        
    def delete_all(self):
        '''
        Removes all rows of the list
        '''
        del self.rows._data[:]
        self._send_w32_msg(LVM_DELETEALLITEMS)
        if self._autoadjust:
            self.adjust_all() 

        


class TreeItem(GuiObject):
    
    def __init__(self, tree, hItem):
        '''
        Do not use this constructor directly.
        Use Tree and TreeItem methods instead.
        '''
        self._tree = tree
        self._hItem = hItem
        
    def __eq__(self, other):
        return (self._tree is other._tree) \
            and (self._hItem == other._hItem)
        
    def __len__(self):
        for i, item in enumerate(self): 
            pass
        try :
            return i+1
        except NameError:
            return 0
            
    
    def append(self, text, data=None, image=0, selected_image=0):
        '''
        Adds a child item to the TreeItem. 
        '''
        
        return self._tree._insertitem(self._hItem, TVI_LAST, text, data, image, selected_image)
    
    def insert(self, i, text, data=None, image=0, selected_image=0):
        
        if i < 0 :
            raise IndexError
            
        if i == 0:
            return self._tree._insertitem(self._hItem, TVI_FIRST, text, data, image, selected_image)
        hAfter = self[i-1]
        return self._tree._insertitem(self._hItem, hAfter._hItem, text, data, image, selected_image)
    
    def get_parent(self):
        parenthItem = self._tree._send_w32_msg(TVM_GETNEXTITEM, TVGN_PARENT, self._hItem)
        if parenthItem :
            return TreeItem(self._tree, parenthItem)
    
    def expand(self):
        self._tree._send_w32_msg(TVM_EXPAND, TVE_EXPAND, self._hItem)
    
    def collapse(self):
        self._tree._send_w32_msg(TVM_EXPAND, TVE_COLLAPSE, self._hItem)
        
    def toggle(self):
        self._tree._send_w32_msg(TVM_EXPAND, TVE_TOGGLE, self._hItem)
    
#    def isexpanded(self):

#        pass
        
    def select(self):
        self._tree._send_w32_msg(TVM_SELECTITEM, TVGN_CARET, self._hItem)
    
#    def isselected(self):

#        pass
        
    def ensure_visible(self):
        self._tree._send_w32_msg(TVM_ENSUREVISIBLE, 0, self._hItem)
         
    def __getitem__(self, i):
        if i < 0:
            raise IndexError
        for j, item in enumerate(self):
            if j==i :
                return item
        raise IndexError
        
    def get_text(self):
        item = TVITEM()
        item.hItem = self._hItem
        item.mask = TVIF_TEXT
        item.pszText = u" "*1024
        item.cchTextMax = 1024
        self._tree._getitem(item)
        return item.pszText
        
    def set_text(self, txt):
        item = TVITEM()
        item.mask  = TVIF_TEXT
        item.hItem = self._hItem
        item.pszText = unicode(txt)
        return self._tree._setitem(item)
        
    doc_text = "The text of the TreeItem as a string"
    
    def get_data(self):
        item = TVITEM()
        item.hItem = self._hItem
        item.mask  = TVIF_PARAM
        self._tree._getitem(item)
        return self._tree._data[item.lParam][0]
        
    def set_data(self, data):
        olddata = self.data
        self._tree._data.decref(olddata)
        param = self._tree._data.addref(data)
        item = TVITEM()
        item.hItem = self._hItem
        item.mask  = TVIF_PARAM
        item.lParam = param
        self._tree._setitem(item)
        
    doc_data = "The data of the TreeItem as any python object"
        
    def get_image(self):
        item = TVITEM()
        item.mask  = TVIF_IMAGE
        item.hItem = self._hItem
        self._tree._getitem(item)
        return item.iImage
        
    def set_image(self, i):
        item = TVITEM()
        item.mask  = TVIF_IMAGE
        item.hItem = self._hItem
        item.iImage = i
        self._tree._setitem(item)
        
    def get_selected_image(self):
        item = TVITEM()
        item.mask  = TVIF_SELECTEDIMAGE
        item.hItem = self._hItem
        self._tree._getitem(item)
        return item.iSelectedImage
        
    def set_selected_image(self, i):
        item = TVITEM()
        item.mask  = TVIF_SELECTEDIMAGE
        item.hItem = self._hItem
        item.iSelectedImage = i
        self._tree._setitem(item)
        
    def _removedata(self):
        data = self.data
        self._tree._data.decref(data)
        for child in self:
            child._removedata()
        
    def remove(self):
        '''
        Removes the TreeItem instance and all its children from its tree. 
        '''
        self._removedata()
        self._tree._send_w32_msg(TVM_DELETEITEM, 0, self._hItem)
    
    def __iter__(self):
        return _treeitemiterator(self) 
        
    def __delitem__(self, i):
        '''
        del item[i] -> removes the child at index i
        '''
        
        self[i].remove()

    
def _treeitemiterator(treeitem):
    hitem = treeitem._tree._send_w32_msg(TVM_GETNEXTITEM, TVGN_CHILD, treeitem._hItem)
    while hitem :
        yield TreeItem(treeitem._tree, hitem)
        hitem = treeitem._tree._send_w32_msg(TVM_GETNEXTITEM, TVGN_NEXT, hitem)
        
class _TreeDataHolder(dict):
    
    def addref(self, obj):
        idobj = id(obj)
        if idobj in self:
            objj, refs = self[idobj]
            assert objj is obj
            self[idobj] = obj, refs+1
        else :
            self[idobj] = (obj, 1)
        #print dict.__str__(self)
        return idobj
    
    def decref(self, obj):
        idobj = id(obj)
        if idobj in self:
            objj, refs = self[idobj]
            assert objj is obj
            refs -= 1 
            if refs == 0 :
                del self[idobj]
            else :
                self[idobj] = obj, refs
            
            
class Tree(Control):
    '''
    The tree control :
    Insert or get roots with the insertroot and getroots method
    Subsequent changes to the tree are made with the TreeItem instances
    '''
    _w32_window_class = WC_TREEVIEW
    _w32_window_style = WS_CHILD | WS_TABSTOP
                       
    _dispatchers = {"selchanged" : (NTFEventDispatcher, TVN_SELCHANGED, TreeEvent),
                    }
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), has_buttons=True, has_lines=True):
        or_style = 0
        if has_buttons:
            or_style |= TVS_HASBUTTONS
        if has_lines:
            or_style |= TVS_LINESATROOT|TVS_HASLINES
            
        self._w32_window_style |= or_style
        
        Control.__init__(self, parent, border=border, visible=visible, enabled=enabled, pos=pos)
        self._roots = []
        self._data = _TreeDataHolder()
        
    def _getitem(self, item):
        self._send_w32_msg(TVM_GETITEM, 0, byref(item))
        
    def _setitem(self, item):
        self._send_w32_msg(TVM_SETITEM, 0, byref(item))
        
    def _insertitem(self, hParent, hInsertAfter, text, data, image, image_selected):
        #item.mask = TVIF_TEXT | TVIF_PARAM
        item = TVITEM(text=text, param=self._data.addref(data), image=image, selectedImage=image_selected)
        #print 'param :', item.lParam
        insertStruct = TVINSERTSTRUCT()
        insertStruct.hParent = hParent
        insertStruct.hInsertAfter = hInsertAfter
        insertStruct.item = item
        hItem = self._send_w32_msg(TVM_INSERTITEM, 0, byref(insertStruct))
        return TreeItem(self, hItem)
            
    def add_root(self, text, data=None, image=0, selected_image=0):
        '''\
        Insert a new root in the tree
        - text : the text of the root
        - data : the data bound to the root
        Returns the TreeItem instance associated to the root
        '''

        
        root = self._insertitem(TVI_ROOT, TVI_ROOT, text, data, image, selected_image)
        self._roots.append(root)
        return root
    
    def get_roots(self):
        '''\
        Returns the list of roots in the tree
        '''  
        return self._roots

    def delete_all(self):
        '''\
        Deletes all items in the tree
        '''
        for root in self._roots:
            root.remove()
        self._roots = []
    
    def get_selection(self):
        '''\
        Returns a TreeItem instance bound
        to the current selection or None
        '''
        hItem = self._send_w32_msg(TVM_GETNEXTITEM, TVGN_CARET, 0)
        if hItem > 0:
            return TreeItem(self, hItem)
        
    def set_image_list(self, il):
        self._send_w32_msg(TVM_SETIMAGELIST, 0, il._hImageList)
        
class Progress(Control):
    _w32_window_class = PROGRESS_CLASS
    
    def __init__(self, parent, style="normal", orientation="horizontal", range=(0,100), visible=True, enabled=True, pos=(-1,-1,-1,-1)):
        if style not in ["normal", "smooth"]:
            raise ValueError('style not in ["normal", "smooth"]')
        if orientation not in ['horizontal', 'vertical']:
            raise ValueError("orientation not in ['horizontal', 'vertical']")
        
        self._orientation = orientation 
        orStyle = 0
        if style == "smooth" :
            orStyle |= PBS_SMOOTH
        if orientation == "vertical" :
            orStyle |= PBS_VERTICAL
        
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        self.range = range
            
    def set_range(self, range):
        nMinRange, nMaxRange = range
        if nMinRange > 65535 or nMaxRange > 65535:
            return self._send_w32_msg(PBM_SETRANGE32, nMinRange, nMaxRange)
        else:
            return self._send_w32_msg(PBM_SETRANGE, 0, MAKELPARAM(nMinRange, nMaxRange))
            
    def get_range(self):
        minrange = self._send_w32_msg(PBM_GETRANGE, 1)
        maxrange = self._send_w32_msg(PBM_GETRANGE, 0)
        return minrange, maxrange
    
    doc_range = "The range of the progress as a tuple (min, max)"
    
    def set_value(self, newpos):
        return self._send_w32_msg(PBM_SETPOS, newpos, 0)

    def get_value(self):
        return self._send_w32_msg(PBM_GETPOS, 0, 0)
    
    doc_value = "The position of the progress as an int"
    
    def get_best_size(self):
        if self._orientation == 'horizontal':
            return None, 20
        else:
            return 20, None
            
class ScrollEvent(Event):
    def __init__(self, hWnd, nMsg, wParam, lParam):
        Event.__init__(self, lParam, nMsg, wParam, lParam)

class Slider(Control):
    _w32_window_class = TRACKBAR_CLASS
    _w32_window_style = WS_CHILD | TBS_AUTOTICKS | TBS_TOOLTIPS

    _dispatchers = {"_hscroll" : (MSGEventDispatcher, WM_HSCROLL, ScrollEvent),
                    "_vscroll" : (MSGEventDispatcher, WM_VSCROLL, ScrollEvent),
                    "update" : (CustomEventDispatcher,)
                    }
    _dispatchers.update(Control._dispatchers)
                    
                        
    def __init__(self, parent, orientation="horizontal", value=0, range=(0,10), visible=True, enabled=True, pos=(-1,-1,-1,-1)):
        assert orientation in  ['horizontal', 'vertical']
        if orientation == 'horizontal' :
            self._w32_window_style |= TBS_HORZ
        else :
            self._w32_window_style |= TBS_VERT
        self._style = orientation
        Control.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        
        self.bind(_hscroll=self._on_hscroll, 
                  _vscroll=self._on_vscroll)
                  
        clsStyle = GetClassLong(self._w32_hWnd, GCL_STYLE)
        clsStyle &= ~CS_HREDRAW
        clsStyle &= ~CS_VREDRAW
        SetClassLong(self._w32_hWnd, GCL_STYLE, clsStyle)
        
        self.range = range
        self.value = value
    def _on_hscroll(self, ev):
        self.events['update'].call(ev)
        
    def _on_vscroll(self, ev):
        self.events['update'].call(ev)
        
    def get_range(self):
        min = self._send_w32_msg(TBM_GETRANGEMIN)
        max = self._send_w32_msg(TBM_GETRANGEMAX)
        return min, max
        
    def set_range(self, range):
        min, max = range
        self._send_w32_msg(TBM_SETRANGE, 0, MAKELPARAM(min, max))
    
    doc_range = "The range of the slider as a tuple (min, max)"
        
    def get_value(self):
        return self._send_w32_msg(TBM_GETPOS)
        
    def set_value(self, pos):
        self._send_w32_msg(TBM_SETPOS, 1, pos)
    
    doc_value = "The position of the slider as an int"
    
#    def get_pagesize(self):
#        pass
#        
#    def set_pagesize(self, size):
#        pass

    def get_best_size(self):
        if self._style == 'horizontal':
            return None, 25
        else:
            return 25, None


class _TabControl(Control):
    _w32_window_class = WC_TABCONTROL
    #_w32_window_style_ex = 0x10000
    _w32_window_style = WS_VISIBLE | WS_CHILD | TCS_BOTTOM | WS_CLIPSIBLINGS 
    _dispatchers = {"_selchanging" : (NTFEventDispatcher, TCN_SELCHANGING),
                    "_selchange" : (NTFEventDispatcher, TCN_SELCHANGE),
                    }
    _dispatchers.update(Control._dispatchers)
                    
    def __init__(self, parent, pos=(-1,-1,-1,-1)):
        Control.__init__(self, parent, pos=pos)
        self._send_w32_msg(CCM_SETVERSION, COMCTL32_VERSION, 0)
#        self.events['_selchanging'].bind(self._onchanging)
#        self.events['_selchange'].bind(self._onchange)
#        self.events['size'].bind(self._onsize)
        
        
        SetWindowPos(self._w32_hWnd, 0, 0, 0, 0, 0, 1|2|4|20)
        self.update()
        
    def _insertitem(self, i, item):
        self._send_w32_msg(TCM_INSERTITEM, i, byref(item))

    def _getitem(self, index, mask):
        item = TCITEM()
        item.mask = mask
        if self._send_w32_msg(TCM_GETITEM, index, byref(item)):
            return item
        else:
            raise "error"
            
    def _adjustrect(self, fLarger, rc):
        lprect = byref(rc)
        self._send_w32_msg(TCM_ADJUSTRECT, fLarger, lprect) 
           
    def _resizetab(self, tab):
        if tab:
            rc = self.client_rect
            self._adjustrect(0, rc)
            tab.move(rc.left-(2*HIRES_MULT), rc.top-(2*HIRES_MULT), rc.width, rc.height)
            #tab.move(rc.left, rc.top, rc.width, rc.height)
            #SetWindowPos(tab._w32_hWnd, 0, rc.left, rc.top, rc.width, rc.height, 4)
            SetWindowPos(self._w32_hWnd, tab._w32_hWnd, rc.left, rc.top, rc.width, rc.height, 1|2)
            
class NoteBook(Frame):
    def __init__(self, parent, visible=True, enabled=True, pos=(-1,-1,-1,-1)):
        Frame.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        self._tc = _TabControl(self)
        self._tc.bind(_selchanging=self._onchanging, 
                      _selchange=self._onchange,
                      size=self._onsize)
                      
        sizer = VBox((-2,-2,-2,0))
        sizer.add(self._tc)
        self.sizer = sizer
        
    def _onchanging(self, event):
        tab = self[self.selection]
        if tab :
            tab.hide()
        
    def _onchange(self, event):
        tab = self[self.selection]
        if tab :
            self._tc._resizetab(tab)
            tab.show(True)
    
    def _onsize(self, event):
        InvalidateRect(self._w32_hWnd)#, 0, 1)
        if self.selection is not None:
            tab = self[self.selection]
            self._tc._resizetab(tab)
        event.skip()
        
    def get_count(self):
        return self._tc._send_w32_msg(TCM_GETITEMCOUNT)
     
    doc_count = "The number of tab in the notebook"
    
    def append(self, title, tab):
        '''
        Adds a new tab to the notebook
        - title : the title of the tab
        - tab : the child window 
        '''
        self.insert(self.count, title, tab)
        
    def insert(self, i, title, tab):
        '''
        Inserts a new tab in the notebook at index i
        - title : the title of the tab
        - tab : the child window 
        '''
        if not 0<=i<=self.count:
            raise IndexError
        item = TCITEM()
        item.mask = TCIF_TEXT | TCIF_PARAM
        item.pszText = title
        item.lParam = tab._w32_hWnd
        self._tc._insertitem(i, item)
        
        self.selection = i
        return i
        
    def __getitem__(self, i):
        '''
        notebook[i] -> Returns the child window at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
        item = self._tc._getitem(i, TCIF_PARAM)
        return hwndWindowMap.get(item.lParam, None)
        
    def __delitem__(self, i):
        '''
        del notebook[i] -> Removes the tab at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
            
        self._tc._send_w32_msg(TCM_DELETEITEM, i)
        if i == self.count:
            i -= 1
        self._tc._send_w32_msg(TCM_SETCURSEL, i)
        self._onchange(None)
        
    def get_selection(self):
        sel = self._tc._send_w32_msg(TCM_GETCURSEL)
        if sel != -1:
            return sel
        
    def set_selection(self, i):
        if not 0<=i<self.count:
            raise IndexError
        if i == self.selection : return
        self._onchanging(None)
        self._tc._send_w32_msg(TCM_SETCURSEL, i)
        self._onchange(None)
        
    doc_selection =  "The current index of the selected tab"
    
    def set_font(self, font):
        self._tc.font = font
    
    def get_font(self, font):
        return self._tc.font
        
class UpDown(Control):
    _w32_window_class = "msctls_updown32"
    _w32_window_style = WS_VISIBLE | WS_CHILD | UDS_SETBUDDYINT | 0x20 | 8
    _dispatchers = {'deltapos' : (NTFEventDispatcher, UDN_DELTAPOS)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, *args, **kw):
        kw['tab_stop'] = False
        Control.__init__(self, *args, **kw)
        
    def set_buddy(self, buddy):
        self._send_w32_msg(UDM_SETBUDDY, buddy._w32_hWnd)
    
    def set_range(self, range):
        low, high = range
        self._send_w32_msg(UDM_SETRANGE32, int(low), int(high))
        
    def get_best_size(self):
        return 14, 20
        
    def _get_pos(self):
        err = c_ulong()
        ret = self._send_w32_msg(UDM_GETPOS32, 0, byref(err))
        return ret
        
    def _set_pos(self, pos):
        self._send_w32_msg(UDM_SETPOS32, 0, pos)
        
class BusyCursor(GuiObject):
    def __init__(self):
        SetCursor(LoadCursor(0, 32514))
        
    def __del__(self):
        SetCursor(0)

########NEW FILE########
__FILENAME__ = core
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from w32api import *
from ctypes import *
from weakref import WeakValueDictionary
import weakref
from font import *

__doc__ = '''
This module contains the core mechanism of pycegui
'''

class GuiType(type):
    '''\
    The metaclass of GuiObject, useful for automatic property generation
    '''

    def __init__(cls, name, bases, dict):
        # Here we create properties based on
        # the set_xxx/get_xxx methods and
        # doc_xxx attribute of the class we construct.
        type.__init__(cls, name, bases, dict)
        methods = [(name, obj) for name, obj in dict.items() if callable(obj)]  
        properties = {}
        for name, obj in methods :
            if name[:4] in ['get_', 'set_']:
                property_name, meth_type = name[4:], name[:3]
                if not property_name in properties :
                    properties[property_name] = {}

                obj.__doc__ = "%ster for property %s" %(meth_type, property_name) 
                properties[property_name][meth_type] = obj
                doc_name = "doc_%s" %property_name
                
                if doc_name in dict :
                    properties[property_name]['doc'] = dict[doc_name]
                else:
                    properties[property_name]['doc'] = ''
        
        for property_name, property_data in properties.items() :
            prop = _makeprop(property_name, property_data)
            setattr(cls, property_name, prop)
            
        setattr(cls, '_properties', properties)
                
        
        
        
def _makeprop(property_name, property_data):
    # A property factory used to reference
    # property getters and setters as locals
    # of this function
    fget = None
    fset = None
    fdel = None
    
    if 'get' in property_data :
        fget = lambda self : getattr(self, "get_%s" %property_name)()
        
    if 'set' in property_data :
        fset = lambda self, val : getattr(self, "set_%s" %property_name)(val)
        
    doc = property_data.get('doc', None)
    prop = property(fget = fget,
                    fset = fset,
                    fdel = fdel,
                    doc = doc,
                    )
                    
    return prop
    

class GuiObject(object):
    '''\
    The most basic pycegui type. 
    '''
    __metaclass__ = GuiType
    
    def __init__(self, **kw):
        self.set(**kw)
    
    def set(self, **kw):
        '''\
        set(self, prop1=value1, prop2=value2, ...) --> sets the property prop1 to value1, prop2 to value2, ...
        '''
        for option, value in kw.items() :
            try :
                getattr(self, "set_%s" %option)(value)
            except AttributeError:
                raise AttributeError("can't set attribute '%s'" %option)
        
        

# Global objects and procedures
class IdGenerator(object):
    '''
    A global class to generate unique integers
    ids starting from 1001
    '''
    
    current_id = 1000
    recycle = []
    
    @classmethod
    def next(cls):
        if cls.recycle :
            return cls.recycle.pop(0)
        cls.current_id += 1
        return cls.current_id
        
    @classmethod    
    def reuseid(cls, id):
        cls.recycle.append(id)

# The dict which maps HWND to gui.Window instances
hwndWindowMap =  WeakValueDictionary()
hInstance = GetModuleHandle(NULL)
wndClasses = []
# Dict which contains gui.Window data at creation time
createHndlMap = {}

schedulees = {}

WM_SCHEDULE = 0x8000 + 2

class Schedulee():
    '''
    Used internally by PPyGui. Not documented yet
    '''
    def __init__(self, func, args, kw):
        self.func = func
        self.args = args
        self.kw = kw
    
    def apply(self):
        self.func(*self.args, **self.kw)
    
mainframe_hwnd = 0

def schedule(func, args=[], kw={}):
    '''
    Schedule the fuction func
    to be called as function(*args, **kw)
    in the main thread.
    Gui objects are not generally thread
    safe, so a thread should use schedule instead
    of modifying directly the gui
    '''
    schedulee = Schedulee(func, args, kw)
    sid = id(schedulee)
    schedulees[sid] = schedulee
    PostMessage(mainframe_hwnd, WM_SCHEDULE, 0, sid) != 0
    
            
def globalWndProc(hWnd, nMsg, wParam, lParam):
    '''
    Used internally by PPyGui. Not documented yet
    '''

    if nMsg == WM_CREATE:
        createStruct = CREATESTRUCT.from_address(int(lParam))
        window = createHndlMap.get(int(createStruct.lpCreateParams), None)
        if window:
            hwndWindowMap[hWnd] = window
    
    elif nMsg == WM_SCHEDULE:
        sid = lParam
        schedulee = schedulees[sid]
        schedulee.apply()
        del schedulees[sid]
        return 0
    
    elif 306<=nMsg<=312: #Handle WM_CTLCOLOR* messages
        try:
            hbrush=DefWindowProc(hWnd, nMsg, wParam, lParam)
            win = hwndWindowMap[lParam]
            win._on_color(wParam)
            return hbrush
        except:
            return 0
            
    # A WM_ACTIVATE could occur before
    # the callback is bound to the 'activate' signal
    # Handle it statically here
    elif nMsg == WM_ACTIVATE : 
        if hWnd in hwndWindowMap:
            try :
                hwndWindowMap[hWnd]._on_activate(Event(hWnd, nMsg, wParam, lParam))
                return 0
            except:
                pass
       
    handled = False
        
    dispatcher = registeredEventDispatcher.match(hWnd, nMsg, wParam, lParam)
    if dispatcher :
        if dispatcher.isconnected() :
            handled, result = dispatcher.dispatch(hWnd, nMsg, wParam, lParam)
            if handled : return result
            
    win = hwndWindowMap.get(hWnd, None)    
    if win and win._issubclassed:
        return CallWindowProc(win._w32_old_wnd_proc, hWnd, nMsg, wParam, lParam)
    
    return DefWindowProc(hWnd, nMsg, wParam, lParam)

cGlobalWndProc = WNDPROC(globalWndProc)

class RegisteredEventsDispatcher(object):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self):
        self.msged = {}
        self.cmded = {}
        self.ntfed = {}
        self.ntfed2 = {}
        
    def match(self, hWnd, nMsg, wParam, lParam):
        if nMsg == WM_COMMAND :
            cmd = HIWORD(wParam)
            id = LOWORD(wParam)
            #print "debug", cmd, id, lParam
            if cmd == 4096 and id == 1:
                try:
                    win = hwndWindowMap[hWnd]
                    return win.onok()
                except AttributeError:
                    pass
            elif cmd == 4096 and id == 2:
                print 'cancel message'
#                try:
#                    win = hwndWindowMap[hWnd]
#                    win.close()
#                except AttributeError:
#                    pass
              
            try :
                return self.cmded[(id, cmd)]
            except :
                pass
                
        elif nMsg == WM_NOTIFY :
            nmhdr = NMHDR.from_address(int(lParam))
            hWnd = nmhdr.hwndFrom
            code = nmhdr.code
            
            try :
                return self.ntfed[(hWnd, code)]
            except :
                pass
                
            id = nmhdr.idFrom
            try :
                return self.ntfed2[(id, code)]
            except :
                pass
                
            #print 'debug', hWnd, code, nmhdr.idFrom
        elif nMsg in [WM_HSCROLL, WM_VSCROLL]:
            #Scroll messages are sent to parent
            #The source hWnd is lParam 
            try :
                #print "WM_XSCROLL lParam", lParam
                return self.msged[(lParam, nMsg)]
            except :
                pass
        
        else :
            try :
                #if dispatch.w32_hWnd == hWnd and dispatch.nMsg == nMsg :
                return self.msged[(hWnd, nMsg)]
            except :
                pass
                    
    def install(self, dispatcher):
        if isinstance(dispatcher, MSGEventDispatcher):
            self.msged[(dispatcher.w32_hWnd, dispatcher.nMsg)] = dispatcher
        elif isinstance(dispatcher, CMDEventDispatcher):
            self.cmded[(dispatcher._id, dispatcher.cmd)] = dispatcher
        elif isinstance(dispatcher, NTFEventDispatcher):
            self.ntfed[(dispatcher.w32_hWnd, dispatcher.code)] = dispatcher
            if hasattr(dispatcher, '_id'):
                self.ntfed2[(dispatcher._id, dispatcher.code)] = dispatcher
    
    def remove(self, dispatcher):
#        for d in [self.msged, self.cmded, self.ntfed]:
#            for key, disp in d.items() :
#                if disp is dispatcher :
#                    del d[key]
#                    break
                    #return
        if isinstance(dispatcher, MSGEventDispatcher):
            del self.msged[(dispatcher.w32_hWnd, dispatcher.nMsg)]
        elif isinstance(dispatcher, CMDEventDispatcher):
            del self.cmded[(dispatcher._id, dispatcher.cmd)]
        elif isinstance(dispatcher, NTFEventDispatcher):
            del self.ntfed[(dispatcher.w32_hWnd, dispatcher.code)]
            if hasattr(dispatcher, '_id'):
                del self.ntfed2[(dispatcher._id, dispatcher.code)]
            
registeredEventDispatcher = RegisteredEventsDispatcher()

# Events and EventDispatcher objects

class Event(GuiObject):
    '''\
    Basic object that wraps a win32 message, it is often
    the first argument received by a callback.
    Use the read-only properties to have more information about an Event instance.
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self.hWnd = hWnd
        self.nMsg = nMsg
        self.wParam = wParam
        self.lParam = lParam
        self._window = hwndWindowMap.get(hWnd, None)
        self.handled = True
    
    def get_window(self):
        return self._window
        
    doc_window = "Source Window instance that triggered the event"
    
    def skip(self):
        '''\
        Tells the default window procedure to handle the event.
        '''
        self.handled = False
        
class SizeEvent(Event):
    '''\
    An Event that is raised by a window when resized
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self._size = LOWORD(lParam), HIWORD(lParam)
        Event.__init__(self, hWnd, nMsg, wParam, lParam)
        
    def get_size(self):
        return self._size
          
    doc_size = 'The new size of the window as a tuple (widht, height)'
    
class CommandEvent(Event):
    '''\
    An Event that wraps Win32 WM_COMMAND messages
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self.id, self._cmd = LOWORD(wParam), HIWORD(wParam)
        #print lParam
        Event.__init__(self, lParam, nMsg, wParam, lParam)
        
    def get_cmd(self):
        return self._cmd
        
class NotificationEvent(Event):
    '''\
    An Event that wraps Win32 WM_NOTIFY messages
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        nmhdr = NMHDR.from_address(int(lParam))
        hwndFrom = nmhdr.hwndFrom
        self._code = nmhdr.code
        self.nmhdr = nmhdr
        Event.__init__(self, hwndFrom, nMsg, wParam, lParam)
        
    def get_code(self):
        return self._code
        
class StylusEvent(Event):
    '''
    An Event that is raised on interaction of a window with the stylus.
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
       pt = GET_POINT_LPARAM(lParam)
       self._position = pt.x, pt.y
       Event.__init__(self, hWnd, nMsg, wParam, lParam)
       
    def get_position(self):
        return self._position
        
    doc_position = 'The position of the stylus as a tuple (left, top)'
    

class KeyEvent(Event):
    '''
    An event raised when the user press a keyboard
    or move the joystick in the window
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self._key_code = wParam
        self._repeat_count = lParam & 65535
        Event.__init__(self, hWnd, nMsg, wParam, lParam)
        
    def get_key_code(self):
        return self._key_code
    
    doc_key_count = 'The virtual key code of the key pressed'
    
    def get_repeat_count(self):
        return self._repeat_count
     
class CharEvent(Event):
    '''
    An event raised when the user press a keyboard
    or move the joystick in the window
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self._key_code = wParam
        self._repeat_count = lParam & 65535
        Event.__init__(self, hWnd, nMsg, wParam, lParam)
        
    def get_key(self):
        return unichr(self._key_code)

class EventDispatcher(object):
    '''
    Used internally by PPyGui. Not documented yet
    '''
        
    def __init__(self, eventclass = Event) :
        self.eventclass = eventclass 
        self.callback = None
        
    def isconnected(self):
        return bool(self.callback)
    
    def bind(self, callback=None):
        if callback is not None :
            self.callback = callback
    
    def unbind(self):
        self.callback = None
        
    def dispatch(self, hWnd, nMsg, wParam, lParam):
        if self.callback :
            event = self.eventclass(hWnd, nMsg, wParam, lParam)
            res = self.callback(event)
            if res is None:
                res = 0
            return event.handled, res
        return False
        
class CustomEvent(GuiObject):
    def __init__(self, window):
        self.window = window
        
class CustomEventDispatcher(EventDispatcher):
    def call(self, event):
        if self.callback is not None:
            self.callback(event)
        
class MSGEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, win, nMsg, eventclass = Event):
        self.w32_hWnd = win._w32_hWnd
        self.nMsg = nMsg
        EventDispatcher.__init__(self, eventclass)
    
        
class CMDEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, win, cmd=0, eventclass = CommandEvent):
        self._id = win._id
        self.cmd = cmd
        EventDispatcher.__init__(self, eventclass)
    
class MenuEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, id):
        self._id = id
        self.cmd = 0
        EventDispatcher.__init__(self, CommandEvent)
        
class NTFEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, win, code, eventclass = NotificationEvent):
        self.w32_hWnd = win._w32_hWnd
        if hasattr(win, '_id'):
            self._id = win._id
        self.code = code
        EventDispatcher.__init__(self, eventclass)
        
class EventDispatchersMap(dict):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __setitem__(self, i, dispatcher):
        registeredEventDispatcher.install(dispatcher)
        dict.__setitem__(self, i, dispatcher)
        
    def __del__(self):
        for event, dispatcher in self.items():
            registeredEventDispatcher.remove(dispatcher)
        
class Window(GuiObject):
    '''\
    The base class of all displayable elements
    Events:
        - paint -> Event: sent when the window needs repainting
        - close -> Event: sent when the user or os request the window to be closed
        - destroy -> Event: sent when the window is about to be destroyed
        - size -> SizeEvent: sent when the window is resized
        - lbdown -> StylusEvent: sent when the stylus is pressed down on the window 
        - lbmove -> StylusEvent: sent when the stylus is sliding on the window 
        - lbup -> StylusEvent: sent when the stylus is pressed down on the window 
    '''
    
    
    _w32_window_class = None
    _w32_window_style = WS_CHILD
    _w32_window_style_ex = 0
    _w32_window_class_style = CS_HREDRAW | CS_VREDRAW
    _dispatchers = {'paint': (MSGEventDispatcher, WM_PAINT,), 
                    'close' : (MSGEventDispatcher, WM_CLOSE,),
                    'destroy' : (MSGEventDispatcher, WM_DESTROY,),
                    'size' : (MSGEventDispatcher, WM_SIZE, SizeEvent),
                    'lbdown' : (MSGEventDispatcher, WM_LBUTTONDOWN, StylusEvent),
                    'lbmove' : (MSGEventDispatcher, WM_MOUSEMOVE, StylusEvent),
                    'lbup' : (MSGEventDispatcher, WM_LBUTTONUP, StylusEvent),
                    'chardown' : (MSGEventDispatcher, WM_CHAR, CharEvent),
                    'keydown' : (MSGEventDispatcher, WM_KEYDOWN, KeyEvent),
                    'focus' : (MSGEventDispatcher, WM_SETFOCUS,),
                    'lostfocus' : (MSGEventDispatcher, WM_SETFOCUS+1,),
                    'erasebkg' : (MSGEventDispatcher, WM_ERASEBKGND),
                    }
        
    def __init__(self, parent=None, 
                       title="PocketPyGui", 
                       style="normal", 
                       visible=True, 
                       enabled=True, 
                       pos=(-1,-1,-1,-1), 
                       tab_traversal=True, 
                       **kw):
        '''\.
        Arguments:
            - parent: the parent window 
            - title: the title as appearing in the title bar.
            - style: normal or control
            - pos: a tuple (left, top, width, height) that determines the initial position of the window.
              use -1 in any tuple element for default positioning.
              It is strongly recommanded to use the Sizer classes to perform the layout.
            - tab_traversal : whether the Window implements automatic tab/jog-dial 
        '''
        
        #Fixme: clean the legacy venster code.
        windowClassExists = False
        cls = WNDCLASS() # WNDCLASS()
        if self._w32_window_class:
            if GetClassInfo(hInstance, unicode(self._w32_window_class), byref(cls)):
                windowClassExists = True
        
        #determine whether we are going to subclass an existing window class
        #or create a new windowclass
        self._issubclassed = self._w32_window_class and windowClassExists
        
        if not self._issubclassed:
            #if no _window_class_ is given, generate a new one
            className = self._w32_window_class or "pycegui_win_class_%s" % str(id(self.__class__))
            className = unicode(className)
            cls = WNDCLASS() # WNDCLASS()
            cls.cbSize = sizeof(cls)
            cls.lpszClassName = className
            cls.hInstance = hInstance
            cls.lpfnWndProc = cGlobalWndProc
            cls.style = self._w32_window_class_style
            cls.hbrBackground = 1 # Add background customisation
            cls.hIcon = 0
            cls.hCursor = 0
            
            
            ###
            if tab_traversal:
                cls.cbWndExtra = 32
            ###
            wndClasses.append(cls)
            atom = RegisterClass(byref(cls)) # RegisterClass
        else:
            #subclass existing window class.
            className = unicode(self._w32_window_class)
        
        assert style in ["normal", "control"]
        _w32_style = self._w32_window_style
 
        if not parent :
            _w32_style &= ~WS_CHILD
            
        if visible:
            _w32_style |= WS_VISIBLE
            
        self._visible = visible
        defaultorpos = lambda pos : (pos == -1 and [CW_USEDEFAULT] or [pos])[0]
        left, top, width, height = [defaultorpos(p) for p in pos]

        parenthWnd = 0
        if parent :
            parenthWnd = parent._w32_hWnd
          
        menuHandle = 0
        if hasattr(self, '_id'):
            menuHandle = self._id
        
        createHndlMap[id(self)] = self
        self._w32_hWnd = CreateWindowEx(self._w32_window_style_ex,
                              unicode(className),
                              unicode(title),
                              _w32_style,
                              left,
                              top,
                              width,
                              height,
                              parenthWnd,
                              menuHandle,
                              hInstance,
                              id(self))

        if self._issubclassed:
            self._w32_old_wnd_proc = self.__subclass(cGlobalWndProc)
            hwndWindowMap[self._w32_hWnd] = self
        
        self.events = EventDispatchersMap()
        for eventname, dispatchinfo in self._dispatchers.items() :
            dispatchklass = dispatchinfo[0]
            dispatchargs = dispatchinfo[1:]
            self.events[eventname] = dispatchklass(self, *dispatchargs)
        del createHndlMap[id(self)]
        
        GuiObject.__init__(self, **kw)
        self.bind(destroy=self._ondestroy)
        self.enable(enabled)
        
    def bind(self, **kw):
        '''\
        bind(self, event1=callback1, event2=callbac2, ...) -->
        maps gui events to callbacks,
        callbacks are any callable fthat accept a single argument.
        ''' 
        for option, value in kw.items() :
            try:
                self.events[option].bind(value)
            except KeyError :
                raise KeyError("%r has no event '%s'" %(self, option))
        
    def call_base_proc(self, event):
        return CallWindowProc(self._w32_old_wnd_proc, self._w32_hWnd, event.nMsg, event.wParam, event.lParam)
        
    def __subclass(self, newWndProc):
        return SetWindowLong(self._w32_hWnd, GWL_WNDPROC, newWndProc)
        
    def _send_w32_msg(self, nMsg, wParam=0, lParam=0):
        return SendMessage(self._w32_hWnd, nMsg, wParam, lParam)
    
    def get_client_rect(self):
        rc = RECT()
        GetClientRect(self._w32_hWnd, byref(rc))
        return rc
    
    doc_client_rect = 'The window client rect, i.e. the inner rect of the window'
        
    def get_window_rect(self):
        rc = RECT()
        GetWindowRect(self._w32_hWnd, byref(rc))
        return rc
    
    def get_visible(self):
        return self._visible
    
    doc_window_rect = 'The window rect in its parent container'
    
    def get_pos(self):
        rc = self.window_rect
        parent = self.parent
        if parent is not None:
            parent_rc = parent.window_rect
            return rc.left-parent_rc.left, rc.top-parent_rc.top
        return rc.left, rc.top
        
    def set_pos(self, pos):
        left, top = pos
        left = int(left)
        top = int(top) 
        rc = self.window_rect
        
        MoveWindow(self._w32_hWnd, left, top, rc.width, rc.height, 0)
    
    doc_pos = 'The relative window position in its parent container as a tuple (left, top)'
    
    def get_size(self):
        rc = self.client_rect
        return rc.width, rc.height
        
    def set_size(self, size):
        width, height = size
        width = int(width)
        height = int(height)
        left, top = self.pos
        MoveWindow(self._w32_hWnd, left, top, width, height, 0)
    
    doc_size = 'The size of the window as a tuple (width, height)'
        
    def get_parent(self):
        parentHwnd = GetParent(self._w32_hWnd)
        return hwndWindowMap.get(parentHwnd, None)
        
    doc_parent = 'The parent window instance or None for a top window'
    
    def focus(self):
        '''
        Force the focus on this window
        '''
        SetFocus(self._w32_hWnd)
    
    def set_redraw(self, redraw):
        self._send_w32_msg(WM_SETREDRAW, bool(redraw), 0)
        
    doc_redraw = '''\
    The redraw state as a bool. When setting it to
    False, the window will not be repainted, until it
    is set to True again'''

    def get_text(self):
        textLength = self._send_w32_msg(WM_GETTEXTLENGTH)# + 1
        textBuff = u' ' * textLength
        textBuff = create_unicode_buffer(textBuff)
        self._send_w32_msg(WM_GETTEXT, textLength+1, textBuff)
        return textBuff.value
        
    def set_text(self, txt):
        self._send_w32_msg(WM_SETTEXT, 0, unicode(txt))
        
    doc_text = "The text displayed by the control as a string"
        
    def show(self, val=True):
        '''\
        Show or hide the window, depending of the
        boolean value of val. 
        '''
        if val :
            ShowWindow(self._w32_hWnd, SW_SHOW)
        else :
            ShowWindow(self._w32_hWnd, SW_HIDE)
        self._visible = val
            
    def hide(self):
        '''\
        Hide the window. Equivalent to win.show(False)
        '''
        self.show(False)
            
    def enable(self, val=True):
        '''\
        Enable or disable the window, depending of the
        boolean value of val. 
        '''
        EnableWindow(self._w32_hWnd, int(val))
        
    def disable(self):
        '''\
        Disable the window
        '''
        self.enable(False)
        
    def update(self):
        '''\
        Forces the window to be repainted
        '''
        UpdateWindow(self._w32_hWnd)
        
    def move(self, left, top, width, height):
        '''\
        Moves the window to the desired rect (left, top, width, height)
        '''
        MoveWindow(self._w32_hWnd, left, top, width, height, 0)

    def close(self):
        '''
        Programmaticaly request the window to be closed
        '''
        self._send_w32_msg(WM_CLOSE)
        
    def destroy(self):
        '''
        Destroy the window and its child, releasing their resources, and break 
        reference cycle that could be induced by the event system.
        '''
        DestroyWindow(self._w32_hWnd)
    
    def _ondestroy(self, event):
        del self.events
        event.skip()
        
    def bringtofront(self):
        '''\
        Bring the window to foreground
        '''
        SetForegroundWindow(self._w32_hWnd)

class Control(Window):
    '''\
    The base class for common controls.
    It introduces the text and font properties
    '''
    
    _w32_window_style = WS_CHILD
    _defaultfont = DefaultFont
    _w32_window_class_style = 0
    
    def __init__(self, parent, title="", border=False, visible=True, enabled=True, pos=(-1,-1,-1,-1), tab_stop=True, **kw):
        style="control"
        self._id = IdGenerator.next()
        if tab_stop:
            self._w32_window_style |= WS_TABSTOP
        if border:
            self._w32_window_style |= WS_BORDER
        Window.__init__(self, parent, title, style, visible=visible, enabled=enabled, pos=pos)
        self._best_size = None
        self.font = self._defaultfont
        self.set(**kw)
#        self.bind(erasebkg=self._onebkg)
#        
#    def _onebkg(self, ev):
#        return 1
#        #ev.skip()
        
    def get_text(self):
        return Window.get_text(self)
            
    def set_text(self, value):
        Window.set_text(self, value)
        self._best_size = None
        
    def set_font(self, font):
        self._font = font
        self._send_w32_msg(WM_SETFONT, font._hFont, 1)
        self._best_size = None
        
    def get_font(self):
        #return self._send_w32_msg(WM_GETFONT)
        return self._font
        
    doc_font = "The font of the control as a font.Font instance"
        
    def __del__(self):
        #Window.__del__(self)
        IdGenerator.reuseid(self._id)
        
    def _get_best_size(self):
        return None, None
        
    def get_best_size(self):
        if not self._visible:
            return 0,0
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
            
    def _on_color(self, dc):
        if hasattr(self, '_font'):
            SetTextColor(dc, self._font._color)
        
class Frame(Window):
    '''
    Frame extends Window to provide layout facilities.
    You can bind a sizer to a Frame using the sizer property
    '''
    _w32_window_style = Window._w32_window_style | WS_CLIPCHILDREN
    _w32_window_style_ex = 0x10000
    def __init__(self, parent, title="", pos=(-1,-1,-1,-1), visible=True, enabled=True, tab_traversal=True,**kw):
        self._sizer = None
        Window.__init__(self, parent, title, style="normal", pos=pos, visible=visible, enabled=enabled, tab_traversal=tab_traversal, **kw)
        self.events['size'].bind(self._on_size)
        
    def get_sizer(self):
        return self._sizer
        
    def set_sizer(self, sizer):
        if self._sizer is not None:
            self._sizer.hide()
        self._sizer = sizer
        self.layout()
        
    def get_best_size(self):
        if not self._visible:
            return 0, 0
        if self._sizer is not None:
            return self._sizer.get_best_size()
        return None, None
        
    doc_sizer = "A sizer.Sizer, sizer.HSizer or sizer.VSizer instance responsible of the layout"
    
    def layout(self):
        '''\
        Forces the frame to lay its content out with its sizer property. 
        Note it is automatically called anytime the Frame is moved or resized, 
        or when the sizer property is set.
        '''
        if self._sizer is not None:
            rc = RECT()
            GetClientRect(self._w32_hWnd, byref(rc))
            self._sizer.size(rc.left, rc.top, rc.right, rc.bottom)
    
    def _on_size(self, event):
        self.layout()


        
# MessageLoop and Application   

class MessageLoop:
    '''
    Used internally by PPyGui. Not documented yet
    '''
    def __init__(self):
        self.m_filters = {}

    def AddFilter(self, filterFunc):
        self.m_filters[filterFunc] = 1

    def RemoveFilter(self, filterFunc):
        del self.m_filters[filterFunc]
        
    def Run(self):
        msg = MSG()
        lpmsg = byref(msg)
        while GetMessage(lpmsg, 0, 0, 0):
            if not self.PreTranslateMessage(msg):
                if IsDialogMessage(GetActiveWindow(), lpmsg):
                    continue
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)
        global quit
        quit = True
                    
    def PreTranslateMessage(self, msg):
        for filter in self.m_filters.keys():
            if filter(msg):
                return 1
        return 0
    
theMessageLoop = MessageLoop()

def GetMessageLoop():
    return theMessageLoop

class Application(GuiObject):
    '''\
    Each ppygui application should have an instance of Application.
    An Application object has a mainframe property which is usually a 
    ce.CeFrame object, which quits the application when destroyed
    '''
    def __init__(self, mainframe=None):
        self.messageloop = MessageLoop()
        if mainframe is not None:
            self.mainframe = mainframe
            
    def run(self):
        '''\
        Start the main loop of the application.
        It get rids of the nasty busy cursor, 
        whatever PythonCE is launched
        with /nopcceshell or not.
        '''
        try:
            import _pcceshell_support
            _pcceshell_support.Busy(0)
        except ImportError :
            SetCursor(LoadCursor(0, 0))
        return self.messageloop.Run()

    def set_mainframe(self, frame): 
        self._mainframe = frame
        self._mainframe.bind(destroy=lambda event : self.quit())
        global mainframe_hwnd 
        mainframe_hwnd = frame._w32_hWnd
        
        
    def get_mainframe(self):
        return self._mainframe
        
    doc_mainframe ="""\
    The main frame of the application.
    The application will exit when frame is destroyed
    """
        
    
    def quit(self, exitcode = 0):
        """\
        Quits the application with the exit code exitcode
        """
        PostQuitMessage(exitcode)

########NEW FILE########
__FILENAME__ = date
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from w32comctl import *
from config import HIRES_MULT

import datetime

ICC_DATE_CLASSES = 0x100
DTS_TIMEFORMAT = 0x9
DTM_FIRST = 0x1000
DTM_GETSYSTEMTIME = DTM_FIRST+1
DTM_SETSYSTEMTIME = DTM_FIRST+2

DTN_FIRST = 4294966536
DTN_DATETIMECHANGED = DTN_FIRST + 1

class SYSTEMTIME(Structure):
    _fields_ = [("wYear", WORD),
                ("wMonth", WORD),
                ("wDayOfWeek", WORD),
                ("wDay", WORD),
                ("wHour", WORD),
                ("wMinute", WORD),
                ("wSecond", WORD),
                ("wMilliseconds", WORD),]
    
class Date(Control):
    _w32_window_class = "SysDateTimePick32"
    _w32_window_style = WS_CHILD
    _dispatchers = {'update' : (NTFEventDispatcher, DTN_DATETIMECHANGED)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, *args, **kw):
        Control.__init__(self, *args, **kw)
        self._best_size = None
        
    def get_value(self):
        st = SYSTEMTIME()
        self._send_w32_msg(DTM_GETSYSTEMTIME, 0, byref(st))
        return datetime.date(st.wYear, st.wMonth, st.wDay)

    def set_value(self, date):
        st = SYSTEMTIME()
        st.wYear = date.year
        st.wMonth = date.month
        st.wDay = date.day
        self._send_w32_msg(DTM_SETSYSTEMTIME, 0, byref(st))
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text
        cx, cy = GetTextExtent(dc, u'dd/mm/yyyy')
        return 15+cx/HIRES_MULT, 7+cy/HIRES_MULT
        
    def get_font(self):
        return Control.get_font(self)
            
    def set_font(self, value):
        Control.set_font(self, value)
        self._best_size = None
        
    def get_best_size(self):
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
            
class Time(Control):
    _w32_window_class = "SysDateTimePick32"
    _w32_window_style = WS_CHILD | DTS_TIMEFORMAT
    _dispatchers = {'update' : (NTFEventDispatcher, DTN_DATETIMECHANGED)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, *args, **kw):
        Control.__init__(self, *args, **kw)
        self._best_size = None
        
    def get_value(self):
        st = SYSTEMTIME()
        self._send_w32_msg(DTM_GETSYSTEMTIME, 0, byref(st))
        return datetime.time(st.wHour, st.wMinute, st.wSecond)

    def set_value(self, time):
        st = SYSTEMTIME()
        self._send_w32_msg(DTM_GETSYSTEMTIME, 0, byref(st))
        st.wHour = time.hour
        st.wMinute = time.minute
        st.wSecond = time.second
        self._send_w32_msg(DTM_SETSYSTEMTIME, 0, byref(st))
    
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text
        cx, cy = GetTextExtent(dc, u'hh:mm:ss')
        return 15+cx/HIRES_MULT, 7+cy/HIRES_MULT
    
    def get_font(self):
        return Control.get_font(self)
            
    def set_font(self, value):
        Control.set_font(self, value)
        self._best_size = None
        
    def get_best_size(self):
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
                 
def _InitDateControl():
    icc = INITCOMMONCONTROLSEX()
    icc.dwSize = sizeof(INITCOMMONCONTROLSEX)
    icc.dwICC = ICC_DATE_CLASSES 
    InitCommonControlsEx(byref(icc))

_InitDateControl()

########NEW FILE########
__FILENAME__ = dialog
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from ce import CeFrame

SHDoneButton = cdll.aygshell.SHDoneButton 
EnableWindow = cdll.coredll.EnableWindow
IsDialogMessage = cdll.coredll.IsDialogMessageW

class Dialog(CeFrame):    
    _w32_window_class = "DIALOG"
    _w32_window_style = WS_MAXIMIZE
    _w32_window_style_ex = 0x10000
    
    def __init__(self, title, action=None, menu=None, right_action=None, visible=False, enabled=True, has_sip=True, has_ok=True):
        CeFrame.__init__(self, None, title, action=action, menu=menu, right_action=right_action, visible=visible, enabled=enabled, has_sip=has_sip)
        self.bind(close=self._onclose)
        #self.has_ok = has_ok
        self.poppingup = False
        if has_ok:
            SHDoneButton(self._w32_hWnd, 1)
            
    def popup(self, parent=None):
        self._parent = parent
        
        self.show()
        self.bringtofront()
        if self._parent :
            self._parent.disable()
            self._parent.hide()
        
        self.poppingup = True
        while self.poppingup:
            msg = MSG()
            lpmsg = byref(msg)
            if GetMessage(lpmsg, 0, 0, 0):
                
                if IsDialogMessage(self._w32_hWnd, lpmsg):  
                    continue
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)
            else :
                PostQuitMessage()
                return
                
        return self.ret_code
        
    def end(self, code):
        self.ret_code = code
        self.poppingup = False
        if self._parent is not None:
            self._parent.enable()
            self._parent.show()
            self._parent.bringtofront()
            self._parent.focus()
        self.hide()
        
    def onok(self):
        self.end('ok')
        
    def oncancel(self):
        self.end('cancel')
        
    def _onclose(self, event):
#        if self._parent is not None:
#            self._parent.enable()
#            self._parent.show()
#            self._parent.bringtofront()
        self.end('cancel')

########NEW FILE########
__FILENAME__ = dialoghdr
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from controls import Label
from boxing import VBox, Spacer
from font import Font
from line import HLine

GetSysColor = cdll.coredll.GetSysColor
GetSysColor.restype = DWORD

class DialogHeader(Frame):
    def __init__(self, parent, text):
        Frame.__init__(self, parent)
        color = GetSysColor(2|0x40000000)
        r = color &0xff
        g = (color >> 8) &0xff
        b = (color >> 16) &0xff
        color = (r,g,b)
        self.label = Label(self, text, 
                           font=Font(size=8, 
                                     bold=True, 
                                     color=color 
                                     # XXX: Use system prefs instead of hardcoded blue
                                    )
                          )
        self.hline = HLine(self)
        sizer = VBox()
        sizer.add(Spacer(2,4))
        sizer.add(self.label, border=(4,0,0,0))
        sizer.add(Spacer(2,4))
        sizer.add(self.hline)
        self.sizer = sizer
        
    def set_text(self, text):
        self.label.set_text(text)
        
    def get_text(self):
        return self.label.get_text()
########NEW FILE########
__FILENAME__ = filedlg
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from ctypes import *

LPOFNHOOKPROC = c_voidp #TODO

class OPENFILENAME(Structure):
    _fields_ = [("lStructSize", DWORD),
                ("hwndOwner", HWND),
                ("hInstance", HINSTANCE),
                ("lpstrFilter", LPCTSTR),
                ("lpstrCustomFilter", LPTSTR),
                ("nMaxCustFilter", DWORD),
                ("nFilterIndex", DWORD),
                ("lpstrFile", LPTSTR),
                ("nMaxFile", DWORD),
                ("lpstrFileTitle", LPTSTR),
                ("nMaxFileTitle", DWORD),
                ("lpstrInitialDir", LPCTSTR),
                ("lpstrTitle", LPCTSTR),
                ("Flags", DWORD),
                ("nFileOffset", WORD),
                ("nFileExtension", WORD),
                ("lpstrDefExt", LPCTSTR),
                ("lCustData", LPARAM),
                ("lpfnHook", LPOFNHOOKPROC),
                ("lpTemplateName", LPCTSTR),
                ]

try:
    # Detect if tGetFile.dll is present
    tGetFile = cdll.tgetfile.tGetFile
    def GetOpenFileName(ofn):
        return tGetFile(True, ofn)
    def GetSaveFileName(ofn):
        return tGetFile(False, ofn)
except:
    # Else use standard wince function
    GetOpenFileName = windll.coredll.GetOpenFileNameW
    GetSaveFileName = windll.coredll.GetSaveFileNameW

OFN_ALLOWMULTISELECT = 512
OFN_CREATEPROMPT= 0x2000
OFN_ENABLEHOOK =32
OFN_ENABLETEMPLATE= 64
OFN_ENABLETEMPLATEHANDLE= 128
OFN_EXPLORER= 0x80000
OFN_EXTENSIONDIFFERENT= 0x400
OFN_FILEMUSTEXIST =0x1000
OFN_HIDEREADONLY= 4
OFN_LONGNAMES =0x200000
OFN_NOCHANGEDIR= 8
OFN_NODEREFERENCELINKS= 0x100000
OFN_NOLONGNAMES= 0x40000
OFN_NONETWORKBUTTON =0x20000
OFN_NOREADONLYRETURN= 0x8000
OFN_NOTESTFILECREATE= 0x10000
OFN_NOVALIDATE= 256
OFN_OVERWRITEPROMPT= 2
OFN_PATHMUSTEXIST= 0x800
OFN_READONLY= 1
OFN_SHAREAWARE= 0x4000
OFN_SHOWHELP= 16
OFN_SHAREFALLTHROUGH= 2
OFN_SHARENOWARN= 1
OFN_SHAREWARN= 0
OFN_NODEREFERENCELINKS = 0x100000
OFN_PROJECT = 0x400000
OPENFILENAME_SIZE_VERSION_400 = 76

class FileDialog(object):
    
    @classmethod
    def _do_modal(cls, parent, title, wildcards, filename, f, folder=False):
        szPath = u'\0' * 1024
        if parent is None :
            hparent = 0
        else :
            hparent = parent._w32_hWnd
         
        if isinstance(wildcards, dict):
            items = wildcards.items()
        else:
            items = wildcards
        filter = "".join("%s|%s|" %item for item in items)
        filter = filter.replace('|', '\0') + '\0\0'

        ofn = OPENFILENAME()
        if folder:
            ofn.Flags = OFN_PROJECT
        if versionInfo.isMajorMinor(4, 0): #fix for NT4.0
            ofn.lStructSize = OPENFILENAME_SIZE_VERSION_400
        else:
            ofn.lStructSize = sizeof(OPENFILENAME)
        #ofn.lpstrFile = szPath
        filename = unicode(filename)
        filename += u"\0"*(1024-len(filename))
        ofn.lpstrFile = filename
        #ofn.lpstrFileTitle = unicode(filename)
        #ofn.nMaxFileTitle = 1024
        ofn.nMaxFile = 1024
        ofn.hwndOwner = hparent
        ofn.lpstrTitle = unicode(title)
        ofn.lpstrFilter = filter
    
        try:
            #the windows file dialogs change the current working dir of the app
            #if the user selects a file from a different dir
            #this prevents that from happening (it causes al sorts of problems with
            #hardcoded relative paths)
            import os
            cwd = os.getcwd()
            if f(byref(ofn))!= 0:
                return filename[:filename.find('\0')].strip()
            else:
                return
        finally:
            os.chdir(cwd) 
            
    @classmethod
    def open(cls, title="Open", filename="", wildcards={"All (*.*)":"*.*"}, parent=None):
        return cls._do_modal(parent, title, wildcards, filename, GetOpenFileName)
    
    @classmethod
    def openfolder(cls, title="Open", filename="", wildcards={"All (*.*)":"*.*"}, parent=None):
        return cls._do_modal(parent, title, wildcards, filename, GetOpenFileName, folder=True)

    @classmethod    
    def save(cls, title="Save", filename="", wildcards={"All (*.*)":"*.*"}, parent=None):
        return cls._do_modal(parent, title, wildcards, filename, GetSaveFileName)
########NEW FILE########
__FILENAME__ = font
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from w32api import *
from config import HIRES

CreateFontIndirect=windll.coredll.CreateFontIndirectW

class LOGFONT(Structure):
    _fields_ = [("lfHeight", LONG),
                ("lfWidth", LONG),                
                ("lfEscapement", LONG),
                ("lfOrientation", LONG),
                ("lfWeight", LONG),
                ("lfItalic", BYTE),
                ("lfUnderline", BYTE),
                ("lfStrikeOut", BYTE),
                ("lfCharSet", BYTE),
                ("lfOutPrecision", BYTE),
                ("lfClipPrecision", BYTE),
                ("lfQuality", BYTE), 
                ("lfPitchAndFamily", BYTE),
                ("lfFaceName", TCHAR * 32)]

def rgb(r, g, b):
    return r+(g<<8)+(b<<16)
    
class Font(object):
        
    def __init__(self, name='Tahoma', size=9, charset=None,
                 bold=False, italic=False, underline=False, color=(0,0,0) ):
        
        height = int(-size*96/72.0)
        if HIRES :
            height *= 2
            
        lf = LOGFONT()
        lf.lfHeight = height
        if name: lf.lfFaceName = name
        if charset: lf.lfCharSet = self.charsetToInt( charset )
        if bold: lf.lfWeight = 700
        if italic: lf.lfItalic = 1
        if underline : lf.lfUnderline = 1
        self._hFont = CreateFontIndirect(byref(lf))
        self._color = rgb(*color)
        
    def __del__(self):
        DeleteObject(self._hFont)

    def charsetToInt( charset ):
        """
        Map a charset name to a win32 charset identifier for font selection.
        For convenience, the charset passed in can already be a win32 charset int,
        in which case, it is returned unchanged.
        """
        if type(charset) == type(""):
            if CharsetMap.has_key( charset.lower() ):
                return CharsetMap[ charset.lower() ]
        elif type(charset) == type(1):
            return charset
        # don't cause problems, return default charset
        return 1    # default charset

    charsetToInt = staticmethod( charsetToInt )
        
DefaultFont = Font(size=8)
ButtonDefaultFont = Font(size=8, bold=True)

# these are defined in Wingdi.h
CharsetMap = { 'ansi':              0,
               'iso-8859-1':        0,      # actually this is ansi, a superset of iso-8859-1
               'default':           1,
               'symbol':            2,
               'mac':               77,
               'japanese':          128,
               'shift-jis':         128,
               'hangul':            129,
               'hangeul':           129,
               'euc-kr':            129,
               'johab':             130,
               'chinese_gb2312':    134,
               'gb2312':            134,
               'chinese_big5':      136,
               'big5':              136,
               'greek':             161,
               'iso-8859-7':        161,
               'turkish':           162,
               'iso-8859-9':        162,
               'vietnamese':        163,
               'hebrew':            177,
               'iso-8859-8':        177,
               'arabic':            178,
               'iso-8859-6':        178,
               'baltic':            186,
               'iso-8859-4':        186,
               'russian':           204,
               'iso-8859-5':        204,
               'thai':              222,
               'easteurope':        238,
               'iso-8859-2':        238,
               'oem':               255
               }

 	  	 

########NEW FILE########
__FILENAME__ = html
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from ctypes import cdll, Structure, Union

DTM_ADDTEXTW = WM_USER+102
DTM_ENDOFSOURCE = WM_USER + 104
DTM_NAVIGATE = WM_USER + 120
DTM_ZOOMLEVEL = WM_USER + 116
DTM_CLEAR = WM_USER + 113
DTM_ENABLESHRINK = WM_USER + 107
DTM_ENABLECONTEXTMENU = WM_USER + 110

class _U_NM_HTMLVIEW(Union):
    _fields_ = [('dwCookie', DWORD),
                ('dwFlags', DWORD)
                ]
                
class NM_HTMLVIEW(Structure):
    _fields_ = [('hdr', NMHDR),
                ('szTarget', LPCTSTR),
                ('szData', LPCTSTR),
                ('_u', _U_NM_HTMLVIEW),
                ('szExInfo', LPCTSTR),
                ]
    _anonymous_ = ('_u',)

NM_BEFORENAVIGATE = WM_USER + 109

class BeforeNavigateEvent(NotificationEvent):
    def __init__(self, hwnd, nmsg, wparam, lparam):
        NotificationEvent.__init__(self, hwnd, nmsg, wparam, lparam)
        nmhtml = NM_HTMLVIEW.from_address(lparam)
        self._url = nmhtml.szTarget
        
    def get_url(self):
        return self._url
    
class Html(Control):
    _w32_window_class = "DISPLAYCLASS"
    _dispatchers = {"navigate" : (NTFEventDispatcher, NM_BEFORENAVIGATE, BeforeNavigateEvent)
                    }
    _dispatchers.update(Control._dispatchers)
    
    def _addtext(self, txt, plain=False):
        txt=unicode(txt)
        self._send_w32_msg(DTM_ADDTEXTW, int(plain), txt)
        
    def _endofsource(self):
        self._send_w32_msg(DTM_ENDOFSOURCE)
    
    def navigate(self, url):
        url = unicode(url)
        self._send_w32_msg(DTM_NAVIGATE, 0, url)
        
    def set_zoom_level(self, level):
        if not level in range(5):
            raise TypeError, 'level must be in [0,1,2,3,4]'
        self._send_w32_msg(DTM_ZOOMLEVEL, 0, level)
        
    def set_value(self, html):
        self.clear()
        self._addtext(html)
        self._endofsource()
        
    def set_text(self, txt):
        self.clear()
        self._addtext(txt, True)
        self._endofsource()
    
    def clear(self):
        self._send_w32_msg(DTM_CLEAR)
        
    def enablecontextmenu(self, val=True):
        self._send_w32_msg(DTM_ENABLECONTEXTMENU, 0,  MAKELPARAM(0,int(val)))
        
    def enableshrink(self, val=True):
        self._send_w32_msg(DTM_ENABLESHRINK, 0,  MAKELPARAM(0,int(val))) 
    
def _InitHTMLControl():
    cdll.htmlview.InitHTMLControl(GetModuleHandle(0))
    
_InitHTMLControl()
########NEW FILE########
__FILENAME__ = imagelist
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from os.path import abspath
from ppygui.core import *
from ppygui.w32comctl import *

SHLoadDIBitmap = windll.coredll.SHLoadDIBitmap
SHLoadDIBitmap.argtypes = [LPWSTR]

class ImageList(GuiObject):
    def __init__(self, width, height, flags=1):
        self._hImageList = ImageList_Create(width, height, flags, 0, 1)
        
    def add(self, image, colormask=(255,255,255)):
        # WM >= 5.0 only
        # Pocket PC 2003 ImageList_Add function
        # handles DDB only.
        hbmp = SHLoadDIBitmap(abspath(image))
        crmask = rgb(*colormask)
        ImageList_AddMasked(self._hImageList, hbmp, UINT(crmask))
        DeleteObject(hbmp)
        
    def add_from_resource(self, resource_dll, icons, cx, cy, flags=0):
        LoadLibrary(unicode(resource_dll))
        hdll = GetModuleHandle(unicode(resource_dll))
        for i in icons:
            hIcon = LoadImage(hdll, i, IMAGE_ICON, cx, cy, flags)
            ImageList_AddIcon(self._hImageList, hIcon)
            
            
    def __del__(self):
        ImageList_Destroy(self._hImageList)    

def list_icons(dll):
    LoadLibrary(unicode(dll))
    hdll = GetModuleHandle(unicode(dll))
    for i in range(500):
        try:
            hIcon = LoadImage(hdll, i, IMAGE_ICON, 32, 32, 0)
            print i
        except:
            pass

########NEW FILE########
__FILENAME__ = line
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *

class HLine(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.bind(paint=self.on_paint)
        
    def on_paint(self, event):
        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._w32_hWnd, byref(ps))
        rc = self.client_rect
        r, b =  rc.right, rc.bottom
        hpen = CreatePen(0, 2, 0)
        SelectObject(hdc, hpen)
        line = (POINT*2)()
        line[0].x = 0
        line[0].y = b/2
        line[1].x = r
        line[1].y = b/2
        
        Polyline(hdc, line, 2)
        EndPaint(self._w32_hWnd, byref(ps))
        
    def get_best_size(self):
        return None, 1
        
class VLine(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.bind(paint=self.on_paint)
        
    def on_paint(self, event):
        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._w32_hWnd, byref(ps))
        rc = self.client_rect
        r, b =  rc.right, rc.bottom
        hpen = CreatePen(0, 2, 0)
        SelectObject(hdc, hpen)
        
        line = (POINT*2)()
        line[0].x = r/2
        line[0].y = 0
        line[1].x = r/2
        line[1].y = b
        
        Polyline(hdc, line, 2)
        EndPaint(self._w32_hWnd, byref(ps))
        DeleteObject(hpen)
        
    def get_best_size(self):
        return 1, None
########NEW FILE########
__FILENAME__ = menu
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *

class AbstractMenuBase(GuiObject):
    
    def __init__(self):
        if type(self) == AbstractMenuBase :
            raise TypeError("Cannot instantiate an abstract class") 
        self._hmenu = self._create_menu()
        self._items = []
        
    def get_count(self):
        return len(self._items)
        
    def append(self, text, callback=None, enabled=True):
        new_id = IdGenerator.next()
        item = MenuItem(self, new_id)
        AppendMenu(self._hmenu, MF_STRING, new_id, unicode(text))
        item.enable(enabled)
        item.bind(callback)
        self._items.append(item)
        return item
        
    def append_menu(self, text, menu):
        if not isinstance(menu, AbstractMenuBase):
            raise TypeError("arg 1 must be an instance of a subclass of AbstractMenuBase")
        if self._hmenu == menu._hmenu :
            raise ValueError("a menu cannot contain itself")
        AppendMenu(self._hmenu, MF_POPUP, menu._hmenu, unicode(text))
        self._items.append(menu)    
        
    def append_separator(self):
        AppendMenu(self._hmenu, MF_SEPARATOR, 0,0)
        
    def insert(self, i, text, enabled=True):
        pass
        
    def insert_menu(self, i, menu):
        pass
        
    def insert_separator(self, i):
        pass
        
    def __getitem__(self, i):
        return self._items[i]
        
    def __delitem__(self, i):
        if not 0 <=i<self.count:
            raise IndexError 
        #RemoveMenu(self._hmenu, MF_BYPOSITION, i) 
        del self._items[i]
        
    def destroy(self):
        del self._items[:]
        DestroyMenu(self._hmenu)
        
    def __del__(self, ):
        print "del Menu(%i)" %self._hmenu
    
class MenuWrapper(AbstractMenuBase):
    def __init__(self, hmenu):
        self._hmenu = hmenu
        self._items = []
            
class Menu(AbstractMenuBase):
    def _create_menu(self):
        return CreateMenu()
        
class PopupMenu(AbstractMenuBase):
    def _create_menu(self):
        return CreatePopupMenu()
        
    def popup(self, win, x, y):
        return TrackPopupMenuEx(self._hmenu, 0, x, y, win._w32_hWnd, 0)

    
class MenuItem(GuiObject):
    
    def __init__(self, menu, id):
        self._menu = menu
        self._id = id
        self._cmdmap = EventDispatchersMap()
        dispatcher = CMDEventDispatcher(self)
        self._cmdmap["clicked"] = dispatcher
        
    def enable(self, value=True):
        if value :
            EnableMenuItem(self._menu._hmenu, self._id, MF_ENABLED)
        else :
            EnableMenuItem(self._menu._hmenu, self._id, MF_GRAYED)
            
    def disable(self):
        self.enable(False)
        
    def check(self, value=True):
        if value :
            CheckMenuItem(self._menu._hmenu, self._id, MF_CHECKED)
        else :
            CheckMenuItem(self._menu._hmenu, self._id, MF_UNCHECKED)
            
    def uncheck(self):
        self.check(False)
        
    def bind(self, callback):
        self._cmdmap["clicked"].bind(callback)
        
    def __del__(self):
        IdGenerator.reuseid(self._id)
        print "del MenuItem(%i)" %self._id
        
def recon_context(win, event):
    shi = SHRGINFO()
    shi.cbSize = sizeof(SHRGINFO) 
    shi.hwndClient = win._w32_hWnd
    shi.ptDown = POINT(*event.position)
    shi.dwFlags = SHRG_RETURNCMD
    if SHRecognizeGesture(byref(shi)) == GN_CONTEXTMENU :
        return True
    return False 
    
def context_menu(win, event, popmenu):
    rc = win.window_rect
    x, y = event.position
    return popmenu.popup(win, x+rc.left, y+rc.top)
    
########NEW FILE########
__FILENAME__ = message
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *

class Message(object):
    
    @classmethod
    def _makeiconstyle(cls, icon):
        assert icon in ['info', 'question', 'warning', 'error']
        if icon == 'info' :
            return MB_ICONASTERISK
        elif icon == 'question':
            return MB_ICONQUESTION
        elif icon == 'warning':
            return MB_ICONWARNING
        elif icon == 'error':
            return MB_ICONERROR
    
    @classmethod
    def _messagebox(cls, title, caption, style, parent=None):
        if not parent :
            hwnd = 0
        else :
            hwnd = parent._w32_hWnd
            
        return MessageBox(hwnd, unicode(caption), unicode(title), style)
        
    @classmethod
    def ok(cls, title, caption, icon='info', parent=None):
        style = MB_OK
        style |= cls._makeiconstyle(icon)
        cls._messagebox(title, caption, style, parent)
        return 'ok'
        
    @classmethod
    def okcancel(cls, title, caption, icon='info', parent=None):
        style = MB_OKCANCEL
        style |= cls._makeiconstyle(icon)
        res = cls._messagebox(title, caption, style, parent)
        if res == IDOK :
            return 'ok'
        else :
            return 'cancel'
    
    @classmethod        
    def yesno(cls, title, caption, icon='info', parent=None):
        style = MB_YESNO
        style |= cls._makeiconstyle(icon)
        res = cls._messagebox(title, caption, style, parent)
        if res == IDYES :
            return 'yes'
        else : 
            return 'no'
        
    @classmethod        
    def yesnocancel(cls, title, caption, icon='info', parent=None):
        style = MB_YESNOCANCEL
        style |= cls._makeiconstyle(icon)
        res = cls._messagebox(title, caption, style, parent)
        if res == IDYES :
            return 'yes'
        elif res == IDNO : 
            return 'no'
        else :
            return 'cancel'

########NEW FILE########
__FILENAME__ = sizer
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from config import HIRES

__all__ = ['Sizer', 'HSizer', 'VSizer']

class BlankBox:
  '''
  An empty space that you can 
  put in a BoxSizer
  '''
  def size(self, l, t, r, b):
    pass
    
class Box:
    '''
    A box that holds a window.
    It should not be used directly, but it is used 
    when you pass a window to the append 
    method of a BoxSizer.
    '''
    def __init__(self, window, border):
        self.window = window 
        self.border = border
        assert len(border) == 4
    
    def size(self, l, t, r, b):
        l += self.border[0]
        t += self.border[1]
        r -= self.border[2]
        b -= self.border[3]
        w = r-l
        h = b-t
        self.window.move(l, t, w, h)
    
    def get_best_size(self):
        return self.window.get_best_size()
  
class Sizer:
  
  '''
  The base class of the layout system.
  You can append a Window, blank space or another Sizer with a given proportion 
  or a fixed dimension.
  '''
  
  def __init__(self, orientation, border=(0, 0, 0, 0), spacing=0):
    
    '''
    Arguments:
        - orientation: must be 'vertical' or 'horizontal'
        - border: a 4 elements tuple (left, top, bottom, right)
        - spacing: the space in pixels between elements
    '''
    
    self.boxes = []
    self.totalcoeff = 0
    self.totalfixedsize = 0
    if HIRES :
      border = tuple(2*val for val in border)
    self.border = border
    
    assert orientation in ['horizontal', 'vertical']
    self.orientation = orientation
    self.spacing = spacing
    
  def add(self, box, coeff=1, border=(0, 0, 0, 0)):
    '''
    Appends a Window or another Sizer to the Sizer. 
    Arguments:
        - box: the element to add, it must be an instance of Window or Sizer.
        - coeff: represents the proportion of the sizer that will occupy the element.
        - border: a 4 elements tuple (left, top, bottom, right)
    ''' 
    
    if isinstance(box, Window):
      if HIRES :
        border = tuple(2*val for val in border)
      data = [Box(box, border), coeff]
    elif isinstance(box, (BlankBox, Sizer)):
      data = [box, coeff]
    else :
      raise TypeError("arg 1 must be an instance of Window, BlankBox or BoxSizer")
    
    
    if coeff == 0:
        b_x, b_y = box.get_best_size()
        if self.orientation == 'vertical':
            if not b_y:
                return self.add(box, 1, border)
            else:
                return self.addf(box, b_y, border)
        elif self.orientation == 'horizontal':
            if not b_x:
                return self.add(box, 1, border)
            else:
                return self.addf(box, b_x, border)
                
            
    elif coeff > 0 :
      self.totalcoeff += coeff
    else :
      if HIRES:
        coeff *= 2
        data[1] = coeff
      self.totalfixedsize -= coeff
      
    if self.boxes and self.spacing:
        space = self.spacing
        if HIRES:
            space *= 2
        self.boxes.append((BlankBox(), -space))
        self.totalfixedsize += space
        
    self.boxes.append(data)
  
  def addspace(self, coeff=1, border=(0,0,0,0)):
    '''\
    Appends a blank space to the Sizer, 
    Arguments:
        - coeff: represents the proportion of the sizer that will occupy the space.
        - border: a 4 elements tuple (left, top, bottom, right)
    '''
    self.add(BlankBox(), coeff, border)
    
  def addfixed(self, box, dim=20, border=(0,0,0,0)):
    '''
    Appends a Window, another Sizer to the Sizer, 
    Arguments :
        - box: the element to add, it must be an instance of Window or Sizer.
        - dim: represents the size in pixel that will occupy the element.
        - border: a 4 elements tuple (left, top, bottom, right)
    ''' 
    self.add(box, -dim, border)
  
  addf = addfixed
    
  def addfixedspace(self, dim=20, border=(0,0,0,0)):
    '''\
    Appends a blank space to the Sizer, 
    Arguments:
        - dim: represents the size in pixel that will occupy the space.
        - border: a 4 elements tuple (left, top, bottom, right)
    '''
    self.addspace(-dim, border)
  
  addfspace = addfixedspace
  
  def size(self, l, t, r, b):
    
    l += self.border[0]
    t += self.border[1]
    r -= self.border[2]
    b -= self.border[3]
    sizerw = r - l
    sizerh = b - t
    hoffset = l
    voffset = t
    for data in self.boxes:
      box, coeff = data
      if self.orientation == 'vertical' :
        w = sizerw
        if coeff > 0 :
          h = (sizerh - self.totalfixedsize) * coeff / self.totalcoeff
        else : 
          h = -coeff
        box.size(hoffset, voffset, hoffset+w, voffset+h)
        voffset += h
      elif self.orientation == 'horizontal' :
        if coeff > 0 :
          w = (sizerw - self.totalfixedsize) * coeff / self.totalcoeff
        else :
          w = -coeff
        h = sizerh 
        box.size(hoffset, voffset, hoffset+w, voffset+h)
        hoffset += w

class HSizer(Sizer):
  
    def __init__(self, border=(0, 0, 0, 0), spacing=0):
        Sizer.__init__(self, 'horizontal', border, spacing)
        
    def get_best_size(self):
        h_expand = False
        v_expand = False
        
        b_x = 0
        b_y = 0
        for box, coeff in self.boxes:
            cx, cy =  box.get_best_size()
            if cx is None:
                h_expand = True
            else:
                b_x += cx
            if cy is None:
                v_expand = True
            else:
                if cy > b_y:
                    b_y = cy
                    
        if h_expand:
            b_x = None
        if v_expand:
            b_y = None  
        return b_x, b_y
            
class VSizer(Sizer):
  
    def __init__(self, border=(0, 0, 0, 0), spacing=0):
        Sizer.__init__(self, 'vertical', border, spacing)
  
    def get_best_size(self):
        h_expand = False
        v_expand = False
        
        b_x = 0
        b_y = 0
        for box, coeff in self.boxes:
            
            cx, cy =  box.get_best_size()
            print cx, cy
            if cx is None:
                h_expand = True
            else:
                if cx > b_x:
                    b_x = cx
            if cy is None:
                v_expand = True
            else:
                b_y += cy
                    
        if h_expand:
            b_x = None
        if v_expand:
            b_y = None  
        return b_x, b_y
########NEW FILE########
__FILENAME__ = spin
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import Frame, CustomEventDispatcher, \
    GetDC, SelectObject, GetTextExtent, CustomEvent
from config import HIRES_MULT
from controls import Edit, UpDown
from boxing import HBox

class Spin(Frame):
    _dispatchers = {'update' : (CustomEventDispatcher,)}
    _dispatchers.update(Frame._dispatchers)
    
    def __init__(self, parent, range=(0,100), visible=True, enabled=True, **kw):
        Frame.__init__(self, parent, visible=visible, enabled=enabled)
        self._buddy = Edit(self)
        self._ud = UpDown(self)
        self._ud.buddy = self._buddy
        
        self._buddy.bind(update=self._on_edit_update)
        
        sizer = HBox(spacing=-1)
        sizer.add(self._buddy)
        sizer.add(self._ud)
        self.sizer = sizer
        self.set(range=range, **kw)
        self._best_size = None
    
    def get_value(self):
        return self._ud._get_pos()
        
    def set_value(self, val):
        if not self._low <= val <= self._high:
            raise ValueError('Invalid value retrieved by the spin control')
        self._ud._set_pos(val)    
        

    doc_value = 'The displayed int in range'
        
    def _on_edit_update(self, event):
        self.events['update'].call(CustomEvent(self))
        
    def get_range(self):
        return self._low, self._high
        
    def set_range(self, rg):
        self._low, self._high = rg
        self._ud.range = rg
        self._best_size = None
        
    doc_range = 'The range of valid ints as a tuple (low, high)'
        
    def _get_best_size(self):
        #return self.sizer.get_best_size()
        dc = GetDC(self._w32_hWnd)
        font = self._buddy._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, str(self._high))
        return 20 + cx/HIRES_MULT, 7+cy/HIRES_MULT

########NEW FILE########
__FILENAME__ = toolbar
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

import os
from ppygui.core import *
from ppygui.w32comctl import *
from config import HIRES_MULT
SHLoadDIBitmap = windll.coredll.SHLoadDIBitmap
SHLoadDIBitmap.argtypes = [LPWSTR]
TBSTATE_ENABLED = 0x4
CCS_NOPARENTALIGN = 0x8

class BITMAP(Structure):
    _fields_ = [("bmType", LONG),
    		("bmWidth", LONG),
    		("bmHeight", LONG),
    		("bmWidthBytes", LONG),
    		("bmPlanes", WORD),
    		("bmBitsPixel", WORD),
    		("bmBits", LPVOID)]
            
class TBADDBITMAP(Structure):
    _fields_ = [('hInst', HINSTANCE),
                ('nID', INT),]
                
class ToolBar(Window):
    _w32_window_class = "ToolbarWindow32"
    _w32_window_style = WS_CHILD | WS_VISIBLE | CCS_NOPARENTALIGN
                
    def __init__(self, *args, **kw):
        Window.__init__(self, *args, **kw)
        self._buttons = []
        
    def set_imagelist(self, il):
        self._il = il
        self._send_w32_msg(TB_SETIMAGELIST, 0, il._hImageList)
        
    def add_bitmap(self, path, n=1):
        path = os.path.abspath(path)
        path = unicode(path)
        if not os.path.exists(path):
            raise ValueError('Invalid path')
        hbmp = SHLoadDIBitmap(path)
        tbab = TBADDBITMAP(NULL, hbmp)
        self._send_w32_msg(TB_ADDBITMAP, n, byref(tbab))
        
    def add_standard_bitmaps(self):
        tbab = TBADDBITMAP(0xFFFFFFFF, 0)
        self._send_w32_msg(TB_ADDBITMAP, 1, byref(tbab))
        
    def add_button(self, image=0, enabled=True, style='button', action=None):
        tbb = TBBUTTON()
        tbb.iBitmap = image
        if enabled:
            tbb.fsState |= TBSTATE_ENABLED
        if style == 'check':
            tbb.fsStyle = 0x2
        elif style == 'group':
            tbb.fsStyle = 0x2|0x4
        elif style == 'separator':
            tbb.fsStyle = 0x1
        elif style != 'button':
            raise ValueError("%s is not a valid style" %style)
        
        id = IdGenerator.next()
        tbb.idCommand = id
        self._send_w32_msg(TB_BUTTONSTRUCTSIZE, sizeof(TBBUTTON))
        self._send_w32_msg(TB_ADDBUTTONS, 1, byref(tbb))
        button = ToolBarButton(self, id)
        if action is not None:
            button.bind(action)
        self._buttons.append(button)
        
    def get_count(self):
        return len(self._buttons)
        
    def __getitem__(self, i):
        return self._buttons[i]
        
    def __delitem__(self, i):
        if not 0 <= i < self.count:
            raise IndexError(i)
        self._send_w32_msg(TB_DELETEBUTTON, i)
        del self._buttons[i]
        
    def get_best_size(self):
        return None, 24#HIRES_MULT
    
    def move(self, l, t, w, h):
        Window.move(self, l, t-2*HIRES_MULT, w, h+2*HIRES_MULT)
            
class ToolBarButton(GuiObject):
    def __init__(self, toolbar, id):
        self._id = id
        self.toolbar = toolbar
        self._cmdmap = EventDispatchersMap()
        dispatcher = CMDEventDispatcher(self)
        self._cmdmap["clicked"] = dispatcher
        
    def bind(self, callback):
        self._cmdmap["clicked"].bind(callback)
        
    def enable(self, enabled=True):
        self.toolbar._send_w32_msg(TB_ENABLEBUTTON, self._id, MAKELONG(bool(enabled), 0))
        
    def disable(self):
        self.enable(False)
        
    def get_checked(self):
        return bool(self.toolbar._send_w32_msg(TB_ISBUTTONCHECKED, self._id))
        
    def set_checked(self, check):
        self.toolbar._send_w32_msg(TB_CHECKBUTTON, self._id, MAKELONG(bool(check), 0))
        
    
########NEW FILE########
__FILENAME__ = utils
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from ctypes import cdll
import sys

if sys.version_info[0:2] == (2, 4):
    pythonDll = cdll.python24
elif sys.version_info[0:2] == (2, 5):
    pythonDll = cdll.python25
    
def _as_pointer(obj):
    "Increment the refcount of obj, and return a pointer to it"
    ptr = pythonDll.Py_BuildValue("O", id(obj))
    assert ptr == id(obj)
    return ptr

def _from_pointer(ptr):
    if ptr != 0 :
        "Convert a pointer to a Python object, and decrement the refcount of the ptr"
        l = [None]
        # PyList_SetItem consumes a refcount of its 3. argument
        pythonDll.PyList_SetItem(id(l), 0, ptr)
        return l[0]
    else :
        raise ValueError
########NEW FILE########
__FILENAME__ = w32api
## 	   Copyright (c) 2006-2008 Alexandre Delattre
## 	   Copyright (c) 2003 Henk Punt

## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from ctypes import *

#TODO auto ie/comctl detection
WIN32_IE = 0x0550

#TODO: auto unicode selection,
#if unicode:
#  CreateWindowEx = windll.coredll.CreateWindowExW
#else:
#  CreateWindowEx = windll.coredll.CreateWindowExA
#etc, etc


DWORD = c_ulong
HANDLE = c_ulong
UINT = c_uint
BOOL = c_int
HWND = HANDLE
HINSTANCE = HANDLE
HICON = HANDLE
HDC = HANDLE
HCURSOR = HANDLE
HBRUSH = HANDLE
HMENU = HANDLE
HBITMAP = HANDLE
HIMAGELIST = HANDLE
HGDIOBJ = HANDLE
HMETAFILE = HANDLE

ULONG = DWORD
ULONG_PTR = DWORD
UINT_PTR = DWORD
LONG_PTR = DWORD
INT = c_int
LPCTSTR = c_wchar_p
LPTSTR = c_wchar_p
PSTR = c_char_p
LPCSTR = c_char_p
LPCWSTR = c_wchar_p
LPSTR = c_char_p
LPWSTR = c_wchar_p
PVOID = c_void_p
USHORT = c_ushort
WORD = c_ushort
ATOM = WORD
SHORT = c_short
LPARAM = c_ulong
WPARAM = c_uint
LPVOID = c_voidp
LONG = c_long
BYTE = c_byte
TCHAR = c_wchar #TODO depends on unicode/wide conventions
DWORD_PTR = c_ulong #TODO what is this exactly?
INT_PTR = c_ulong  #TODO what is this exactly?
COLORREF = c_ulong
CLIPFORMAT = WORD
FLOAT = c_float
CHAR = c_char
WCHAR = c_wchar

FXPT16DOT16 = c_long
FXPT2DOT30 = c_long
LCSCSTYPE = c_long
LCSGAMUTMATCH = c_long
COLOR16 = USHORT

LRESULT = LONG_PTR

#### Windows version detection ##############################
class OSVERSIONINFO(Structure):
    _fields_ = [("dwOSVersionInfoSize", DWORD),
                ("dwMajorVersion", DWORD),
                ("dwMinorVersion", DWORD),
                ("dwBuildNumber", DWORD),
                ("dwPlatformId", DWORD),
                ("szCSDVersion", TCHAR * 128)]

    def isMajorMinor(self, major, minor):
        return (self.dwMajorVersion, self.dwMinorVersion) == (major, minor)
    
GetVersion = windll.coredll.GetVersionExW
versionInfo = OSVERSIONINFO()
versionInfo.dwOSVersionInfoSize = sizeof(versionInfo)
GetVersion(byref(versionInfo))

def MAKELONG(w1, w2):
    return w1 | (w2 << 16)

MAKELPARAM = MAKELONG

def RGB(r,g,b):
    return r | (g<<8) | (b<<16)

##### Windows Callback functions ################################
WNDPROC = WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)
DialogProc = WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)

CBTProc = WINFUNCTYPE(c_int, c_int, c_int, c_int)
MessageProc = CBTProc

EnumChildProc = WINFUNCTYPE(c_int, HWND, LPARAM)

MSGBOXCALLBACK = WINFUNCTYPE(c_int, HWND, LPARAM) #TODO look up real def

class WNDCLASS(Structure):
    _fields_ = [
                ("style",  UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", INT),
                ("cbWndExtra", INT),
                ("hInstance", HINSTANCE),
                ("hIcon", HICON),
                ("hCursor", HCURSOR),
                ("hbrBackground", HBRUSH),
                ("lpszMenuName", LPCTSTR),
                ("lpszClassName", LPCTSTR),
                ]

class POINT(Structure):
    _fields_ = [("x", LONG),
                ("y", LONG)]

    def __str__(self):
        return "POINT {x: %d, y: %d}" % (self.x, self.y)

POINTL = POINT

class POINTS(Structure):
    _fields_ = [("x", SHORT),
                ("y", SHORT)]
    

PtInRect = windll.coredll.PtInRect

class RECT(Structure):
    _fields_ = [("left", LONG),
                ("top", LONG),
                ("right", LONG),
                ("bottom", LONG)]

    def __str__(self):
        return "RECT {left: %d, top: %d, right: %d, bottom: %d}" % (self.left, self.top,
                                                                    self.right, self.bottom)

    def getHeight(self):
        return self.bottom - self.top

    height = property(getHeight, None, None, "")

    def getWidth(self):
        return self.right - self.left

    width = property(getWidth, None, None, "")

    def getSize(self):
        return self.width, self.height

    size = property(getSize, None, None, "")
    
    def ContainsPoint(self, pt):
        """determines if this RECT contains the given POINT pt
        returns True if pt is in this rect
        """
        return bool(PtInRect(byref(self), pt))
        
RECTL = RECT        

class SIZE(Structure):
    _fields_ = [('cx', LONG),
                ('cy', LONG)]
        
SIZEL = SIZE        
        
    
##class MSG(Structure):
##    _fields_ = [("hWnd", HWND),
##                ("message", UINT),
##                ("wParam", WPARAM),
##                ("lParam", LPARAM),
##                ("time", DWORD),
##                ("pt", POINT)]

##    def __str__(self):
##        return "MSG {%d %d %d %d %d %s}" % (self.hWnd, self.message, self.wParam, self.lParam,
##                                            self.time, str(self.pt))

#Hack: we need to use the same MSG type as ctypes.com.ole uses!
from ctypes.wintypes import MSG
        
class ACCEL(Structure):
    _fields_ = [("fVirt", BYTE),
                ("key", WORD),
                ("cmd", WORD)]
    
class CREATESTRUCT(Structure):
    _fields_ = [("lpCreateParams", LPVOID),
                ("hInstance", HINSTANCE),
                ("hMenu", HMENU),
                ("hwndParent", HWND),
                ("cx", INT),
                ("cy", INT),
                ("x", INT),
                ("y", INT),
                ("style", LONG),
                ("lpszName", LPCTSTR),
                ("lpszClass", LPCTSTR),
                ("dwExStyle", DWORD)]



class NMHDR(Structure):
    _fields_ = [("hwndFrom", HWND),
                ("idFrom", UINT),
                ("code", UINT)]

class PAINTSTRUCT(Structure):
    _fields_ = [("hdc", HDC),
                ("fErase", BOOL),
                ("rcPaint", RECT),
                ("fRestore", BOOL),
                ("fIncUpdate", BOOL),
                ("rgbReserved", c_char * 32)]

    
class MENUITEMINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("fMask", UINT),
                ("fType", UINT),
                ("fState", UINT),                
                ("wID", UINT),
                ("hSubMenu", HMENU),
                ("hbmpChecked", HBITMAP),
                ("hbmpUnchecked", HBITMAP),
                ("dwItemData", ULONG_PTR),
                ("dwTypeData", LPTSTR),                
                ("cch", UINT),
                ("hbmpItem", HBITMAP)]

class DLGTEMPLATE(Structure):
    _pack_ = 2
    _fields_ = [
        ("style", DWORD),
        ("exStyle", DWORD),
        ("cDlgItems", WORD),
        ("x", c_short),
        ("y", c_short),
        ("cx", c_short),
        ("cy", c_short)
    ]

class DLGITEMTEMPLATE(Structure):
    _pack_ = 2
    _fields_ = [
        ("style", DWORD),
        ("exStyle", DWORD),
        ("x", c_short),
        ("y", c_short),
        ("cx", c_short),
        ("cy", c_short),
        ("id", WORD)
    ]

class COPYDATASTRUCT(Structure):
    _fields_ = [
        ("dwData", ULONG_PTR),
        ("cbData", DWORD),
        ("lpData", PVOID)]
    
def LOWORD(dword):
    return dword & 0x0000ffff

def HIWORD(dword):
    return dword >> 16

TRUE = 1
FALSE = 0
NULL = 0

IDI_APPLICATION = 32512

SW_SHOW = 5
SW_SHOWNORMAL = 1
SW_HIDE = 0

EN_CHANGE = 768

MSGS = [('WM_NULL', 0),
        ('WM_CREATE', 1),
        ('WM_CANCELMODE', 31),
        ('WM_CAPTURECHANGED', 533),
        ('WM_CLOSE', 16),
        ('WM_COMMAND', 273),
        ('WM_DESTROY', 2),
        ('WM_ERASEBKGND', 20),
        ('WM_ENABLE', 0xa),
        ('WM_GETFONT', 49),
        ('WM_INITDIALOG', 272),
        ('WM_INITMENUPOPUP', 279),
        ('WM_KEYDOWN', 256),
        ('WM_KEYFIRST', 256),
        ('WM_KEYLAST', 264),
        ('WM_KEYUP', 257),
        ('WM_LBUTTONDBLCLK', 515),
        ('WM_LBUTTONDOWN', 513),
        ('WM_LBUTTONUP', 514),
        ('WM_MBUTTONDBLCLK', 521),
        ('WM_MBUTTONDOWN', 519),
        ('WM_MBUTTONUP', 520),
        ('WM_MENUSELECT', 287),
        ('WM_MOUSEFIRST', 512),
        ('WM_MOUSEHOVER', 673),
        ('WM_MOUSELEAVE', 675),
        ('WM_MOUSEMOVE', 512),
        ('WM_MOVE', 3),
        ('WM_NCCREATE', 129),
        ('WM_NCDESTROY', 130),
        ('WM_NOTIFY', 78),
        ('WM_PAINT', 15),
        ('WM_RBUTTONDBLCLK', 518),
        ('WM_RBUTTONDOWN', 516),
        ('WM_RBUTTONUP', 517),
        ('WM_SETCURSOR', 32),
        ('WM_SETFONT', 48),
        ('WM_SETREDRAW', 11),
        ('WM_SIZE', 5),
        ('WM_SYSKEYDOWN', 260),
        ('WM_SYSKEYUP', 261),
        ('WM_USER', 1024),
        ('WM_WINDOWPOSCHANGED', 71),
        ('WM_WINDOWPOSCHANGING', 70),
        ('WM_SETTEXT', 12),
        ('WM_GETTEXT', 13),
        ('WM_GETTEXTLENGTH', 14),
        ('WM_ACTIVATE', 6),
        ('WM_HSCROLL', 276),
        ('WM_VSCROLL', 277),
        ('WM_CTLCOLORBTN', 309),
        ('WM_CTLCOLORDLG', 310),
        ('WM_CTLCOLOREDIT', 307),
        ('WM_CTLCOLORLISTBOX', 308),
        ('WM_CTLCOLORMSGBOX', 306),
        ('WM_CTLCOLORSCROLLBAR', 311),
        ('WM_CTLCOLORSTATIC', 312),
        ('WM_TIMER', 0x0113),
        ('WM_CONTEXTMENU', 0x007B),
        ('WM_COPYDATA', 0x004A),
        ('WM_SETTINGCHANGE', 0x001A),
        ('WM_SETFOCUS', 0x7),
        ('WM_CHAR', 0x102),
        ]
        
WM_CUT = 0x300
WM_COPY = 0x301
WM_PASTE = 0x302

#insert wm_* msgs as constants in this module:
for key, val in MSGS:
    exec('%s = %d' % (key, val)) #TODO without using 'exec'?

BN_CLICKED    =     0

VK_DOWN = 40
VK_LEFT = 37
VK_RIGHT = 39
VK_DELETE  = 0x2E

CS_HREDRAW = 2
CS_VREDRAW = 1
WHITE_BRUSH = 0

MIIM_STATE= 1
MIIM_ID= 2
MIIM_SUBMENU =4
MIIM_CHECKMARKS= 8
MIIM_TYPE= 16
MIIM_DATA= 32
MIIM_STRING= 64
MIIM_BITMAP= 128
MIIM_FTYPE =256

MFT_BITMAP= 4
MFT_MENUBARBREAK =32
MFT_MENUBREAK= 64
MFT_OWNERDRAW= 256
MFT_RADIOCHECK= 512
MFT_RIGHTJUSTIFY= 0x4000
MFT_SEPARATOR =0x800
MFT_RIGHTORDER= 0x2000L
MFT_STRING = 0

MF_ENABLED    =0
MF_GRAYED     =1
MF_DISABLED   =2
MF_BITMAP     =4
MF_CHECKED    =8
MF_MENUBARBREAK= 32
MF_MENUBREAK  =64
MF_OWNERDRAW  =256
MF_POPUP      =16
MF_SEPARATOR  =0x800
MF_STRING     =0
MF_UNCHECKED  =0
MF_DEFAULT    =4096
MF_SYSMENU    =0x2000
MF_HELP       =0x4000
MF_END        =128
MF_RIGHTJUSTIFY=       0x4000
MF_MOUSESELECT =       0x8000
MF_INSERT= 0
MF_CHANGE= 128
MF_APPEND= 256
MF_DELETE= 512
MF_REMOVE= 4096
MF_USECHECKBITMAPS= 512
MF_UNHILITE= 0
MF_HILITE= 128
MF_BYCOMMAND=  0
MF_BYPOSITION= 1024
MF_UNCHECKED=  0
MF_HILITE =    128
MF_UNHILITE =  0

LOCALE_SYSTEM_DEFAULT =  0x800

MFS_GRAYED        =  0x00000003L
MFS_DISABLED      =  MFS_GRAYED
MFS_CHECKED       =  MF_CHECKED
MFS_HILITE        =  MF_HILITE
MFS_ENABLED       =  MF_ENABLED
MFS_UNCHECKED     =  MF_UNCHECKED
MFS_UNHILITE      =  MF_UNHILITE
MFS_DEFAULT       =  MF_DEFAULT

WS_BORDER	= 0x800000
WS_CAPTION	= 0xc00000
WS_CHILD	= 0x40000000
WS_CHILDWINDOW	= 0x40000000
WS_CLIPCHILDREN = 0x2000000
WS_CLIPSIBLINGS = 0x4000000
WS_DISABLED	= 0x8000000
WS_DLGFRAME	= 0x400000
WS_GROUP	= 0x20000
WS_HSCROLL	= 0x100000
WS_ICONIC	= 0x20000000
WS_MAXIMIZE	= 0x1000000
WS_MAXIMIZEBOX	= 0x10000
WS_MINIMIZE	= 0x20000000
WS_MINIMIZEBOX	= 0x20000
WS_OVERLAPPED	= 0
WS_OVERLAPPEDWINDOW = 0xcf0000
WS_POPUP	= 0x80000000l
WS_POPUPWINDOW	= 0x80880000
WS_SIZEBOX	= 0x40000
WS_SYSMENU	= 0x80000
WS_TABSTOP	= 0x10000
WS_THICKFRAME	= 0x40000
WS_TILED	= 0
WS_TILEDWINDOW	= 0xcf0000
WS_VISIBLE	= 0x10000000
WS_VSCROLL	= 0x200000

WS_EX_TOOLWINDOW = 128
WS_EX_LEFT = 0
WS_EX_LTRREADING = 0
WS_EX_RIGHTSCROLLBAR = 0
WS_EX_WINDOWEDGE = 256
WS_EX_STATICEDGE = 0x20000
WS_EX_CLIENTEDGE = 512
WS_EX_OVERLAPPEDWINDOW   =     0x300
WS_EX_APPWINDOW    =   0x40000

WA_INACTIVE = 0
WA_ACTIVE = 1
WA_CLICKACTIVE = 2

RB_SETBARINFO = WM_USER + 4
RB_GETBANDCOUNT = WM_USER +  12
RB_INSERTBANDA = WM_USER + 1
RB_INSERTBANDW = WM_USER + 10

RB_INSERTBAND = RB_INSERTBANDA

RBBIM_STYLE = 1
RBBIM_COLORS = 2
RBBIM_TEXT = 4
RBBIM_IMAGE = 8
RBBIM_CHILD = 16
RBBIM_CHILDSIZE = 32
RBBIM_SIZE = 64
RBBIM_BACKGROUND = 128
RBBIM_ID = 256
RBBIM_IDEALSIZE = 0x00000200

TPM_CENTERALIGN =4
TPM_LEFTALIGN =0
TPM_RIGHTALIGN= 8
TPM_LEFTBUTTON= 0
TPM_RIGHTBUTTON= 2
TPM_HORIZONTAL= 0
TPM_VERTICAL= 64
TPM_TOPALIGN= 0
TPM_VCENTERALIGN= 16
TPM_BOTTOMALIGN= 32
TPM_NONOTIFY= 128
TPM_RETURNCMD= 256

TBIF_TEXT = 0x00000002

DT_NOPREFIX   =      0x00000800
DT_HIDEPREFIX =      1048576

WH_CBT       =  5
WH_MSGFILTER =  (-1)

I_IMAGENONE = -2
TBSTATE_ENABLED = 4

BTNS_SHOWTEXT = 0x00000040
CW_USEDEFAULT = 0x80000000

COLOR_3DFACE = 15

BF_LEFT      = 1
BF_TOP       = 2
BF_RIGHT     = 4
BF_BOTTOM    = 8

BDR_RAISEDOUTER =      1
BDR_SUNKENOUTER =      2
BDR_RAISEDINNER =      4
BDR_SUNKENINNER =      8
BDR_OUTER    = 3
BDR_INNER    = 0xc
BDR_RAISED   = 5
BDR_SUNKEN   = 10

EDGE_RAISED  = (BDR_RAISEDOUTER|BDR_RAISEDINNER)
EDGE_SUNKEN  = (BDR_SUNKENOUTER|BDR_SUNKENINNER)
EDGE_ETCHED  = (BDR_SUNKENOUTER|BDR_RAISEDINNER)
EDGE_BUMP    = (BDR_RAISEDOUTER|BDR_SUNKENINNER)

IDC_SIZENWSE = 32642
IDC_SIZENESW = 32643
IDC_SIZEWE = 32644
IDC_SIZENS = 32645
IDC_SIZEALL = 32646
IDC_SIZE = 32640
IDC_ARROW = 32512

TCIF_TEXT    =1
TCIF_IMAGE   =2
TCIF_RTLREADING=      4
TCIF_PARAM  = 8


TCS_MULTILINE = 512

MK_LBUTTON    = 1
MK_RBUTTON    = 2
MK_SHIFT      = 4
MK_CONTROL    = 8
MK_MBUTTON    = 16

ILC_COLOR = 0
ILC_COLOR4 = 4
ILC_COLOR8 = 8
ILC_COLOR16 = 16
ILC_COLOR24 = 24
ILC_COLOR32 = 32
ILC_COLORDDB = 254
ILC_MASK = 1
ILC_PALETTE = 2048

IMAGE_BITMAP = 0
IMAGE_ICON = 1

LR_LOADFROMFILE = 16
LR_VGACOLOR = 0x0080
LR_LOADMAP3DCOLORS = 4096
LR_LOADTRANSPARENT = 32

LVSIL_NORMAL = 0
LVSIL_SMALL  = 1
LVSIL_STATE  = 2

TVSIL_NORMAL = 0
TVSIL_STATE  = 2

SRCCOPY = 0xCC0020

GWL_WNDPROC = -4

HWND_BOTTOM = 1
HWND_TOP=0
HWND_TOPMOST=-1

SWP_DRAWFRAME= 32
SWP_FRAMECHANGED= 32
SWP_HIDEWINDOW= 128
SWP_NOACTIVATE= 16
SWP_NOCOPYBITS= 256
SWP_NOMOVE= 2
SWP_NOSIZE= 1
SWP_NOREDRAW= 8
SWP_NOZORDER= 4
SWP_SHOWWINDOW= 64
SWP_NOOWNERZORDER =512
SWP_NOREPOSITION= 512
SWP_NOSENDCHANGING= 1024
SWP_DEFERERASE= 8192
SWP_ASYNCWINDOWPOS=  16384

DCX_WINDOW = 1
DCX_CACHE = 2
DCX_PARENTCLIP = 32
DCX_CLIPSIBLINGS= 16
DCX_CLIPCHILDREN= 8
DCX_NORESETATTRS= 4
DCX_LOCKWINDOWUPDATE= 0x400
DCX_EXCLUDERGN= 64
DCX_INTERSECTRGN =128
DCX_VALIDATE= 0x200000

GCL_STYLE = -26

SB_HORZ       =      0
SB_VERT       =      1
SB_CTL        =      2
SB_BOTH       =      3

SB_LINEUP           =0
SB_LINELEFT         =0
SB_LINEDOWN         =1
SB_LINERIGHT        =1
SB_PAGEUP           =2
SB_PAGELEFT         =2
SB_PAGEDOWN         =3
SB_PAGERIGHT        =3
SB_THUMBPOSITION    =4
SB_THUMBTRACK       =5
SB_TOP              =6
SB_LEFT             =6
SB_BOTTOM           =7
SB_RIGHT            =7
SB_ENDSCROLL        =8

MB_OK                    =   0x00000000
MB_OKCANCEL              =   0x00000001
MB_ABORTRETRYIGNORE      =   0x00000002
MB_YESNOCANCEL           =   0x00000003
MB_YESNO                 =   0x00000004
MB_RETRYCANCEL           =   0x00000005


MB_ICONASTERISK = 64
MB_ICONEXCLAMATION= 0x30
MB_ICONWARNING= 0x30
MB_ICONERROR= 16
MB_ICONHAND= 16
MB_ICONQUESTION= 32
MB_ICONINFORMATION= 64
MB_ICONSTOP= 16
MB_ICONMASK= 240

IDOK          =      1
IDCANCEL      =      2
IDABORT       =      3
IDRETRY       =      4
IDIGNORE      =      5
IDYES         =      6
IDNO          =      7
IDCLOSE       =  8
IDHELP        =  9

COLOR_3DDKSHADOW = 21
COLOR_3DFACE  = 15
COLOR_3DHILIGHT = 20
COLOR_3DHIGHLIGHT= 20
COLOR_3DLIGHT= 22
COLOR_BTNHILIGHT= 20
COLOR_3DSHADOW= 16
COLOR_ACTIVEBORDER =10
COLOR_ACTIVECAPTION= 2
COLOR_APPWORKSPACE= 12
COLOR_BACKGROUND= 1
COLOR_DESKTOP= 1
COLOR_BTNFACE= 15
COLOR_BTNHIGHLIGHT= 20
COLOR_BTNSHADOW= 16
COLOR_BTNTEXT= 18
COLOR_CAPTIONTEXT= 9
COLOR_GRAYTEXT= 17
COLOR_HIGHLIGHT= 13
COLOR_HIGHLIGHTTEXT= 14
COLOR_INACTIVEBORDER= 11
COLOR_INACTIVECAPTION= 3
COLOR_INACTIVECAPTIONTEXT= 19
COLOR_INFOBK= 24
COLOR_INFOTEXT= 23
COLOR_MENU= 4
COLOR_MENUTEXT= 7
COLOR_SCROLLBAR= 0
COLOR_WINDOW= 5
COLOR_WINDOWFRAME= 6
COLOR_WINDOWTEXT= 8
CTLCOLOR_MSGBOX= 0
CTLCOLOR_EDIT= 1
CTLCOLOR_LISTBOX= 2
CTLCOLOR_BTN= 3
CTLCOLOR_DLG= 4
CTLCOLOR_SCROLLBAR= 5
CTLCOLOR_STATIC= 6
CTLCOLOR_MAX= 7


GMEM_FIXED         = 0x0000
GMEM_MOVEABLE      = 0x0002
GMEM_NOCOMPACT     = 0x0010
GMEM_NODISCARD     = 0x0020
GMEM_ZEROINIT      = 0x0040
GMEM_MODIFY        = 0x0080
GMEM_DISCARDABLE   = 0x0100
GMEM_NOT_BANKED    = 0x1000
GMEM_SHARE         = 0x2000
GMEM_DDESHARE      = 0x2000
GMEM_NOTIFY        = 0x4000
GMEM_LOWER         = GMEM_NOT_BANKED
GMEM_VALID_FLAGS   = 0x7F72
GMEM_INVALID_HANDLE= 0x8000

RT_DIALOG        = "5"

CF_TEXT = 1


BS_DEFPUSHBUTTON = 0x01L
BS_GROUPBOX = 0x7

PUSHBUTTON = 0x80
EDITTEXT = 0x81
LTEXT = 0x82
LISTBOX  = 0x83
SCROLLBAR = 0x84
COMBOXBOX = 0x85
ES_MULTILINE = 4
ES_AUTOVSCROLL = 0x40L
ES_AUTOHSCROLL = 0x80L
ES_READONLY    = 0x800
CP_ACP = 0
DS_SETFONT = 0x40
DS_MODALFRAME = 0x80

SYNCHRONIZE  = (0x00100000L)
STANDARD_RIGHTS_REQUIRED = (0x000F0000L)
EVENT_ALL_ACCESS = (STANDARD_RIGHTS_REQUIRED|SYNCHRONIZE|0x3)
MAX_PATH = 260

def GET_XY_LPARAM(lParam):
    x = LOWORD(lParam)
    if x > 32768:
        x = x - 65536
    y = HIWORD(lParam)
    if y > 32768:
        y = y - 65536
        
    return x, y 

def GET_POINT_LPARAM(lParam):
    x, y = GET_XY_LPARAM(lParam)
    return POINT(x, y)

FVIRTKEY  = 0x01
FNOINVERT = 0x02
FSHIFT    = 0x04
FCONTROL  = 0x08
FALT      = 0x10

def ValidHandle(value):
    if value == 0:
        raise WinError()
    else:
        return value

def Fail(value):
    if value == -1:
        raise WinError()
    else:
        return value
    
GetModuleHandle = windll.coredll.GetModuleHandleW
PostQuitMessage= windll.coredll.PostQuitMessage
DefWindowProc = windll.coredll.DefWindowProcW
CallWindowProc = windll.coredll.CallWindowProcW
GetDCEx = windll.coredll.GetDCEx
GetDC = windll.coredll.GetDC
ReleaseDC = windll.coredll.ReleaseDC
LoadIcon = windll.coredll.LoadIconW
DestroyIcon = windll.coredll.DestroyIcon
LoadCursor = windll.coredll.LoadCursorW
#LoadCursor.restype = ValidHandle
LoadImage = windll.coredll.LoadImageW
LoadImage.restype = ValidHandle

RegisterClass = windll.coredll.RegisterClassW
SetCursor = windll.coredll.SetCursor

CreateWindowEx = windll.coredll.CreateWindowExW
CreateWindowEx.restype = ValidHandle

ShowWindow = windll.coredll.ShowWindow
UpdateWindow = windll.coredll.UpdateWindow
EnableWindow = windll.coredll.EnableWindow
GetMessage = windll.coredll.GetMessageW
TranslateMessage = windll.coredll.TranslateMessage
DispatchMessage = windll.coredll.DispatchMessageW
GetWindowRect = windll.coredll.GetWindowRect
MoveWindow = windll.coredll.MoveWindow
DestroyWindow = windll.coredll.DestroyWindow

CreateMenu = windll.coredll.CreateMenu
CreatePopupMenu = windll.coredll.CreatePopupMenu
DestroyMenu = windll.coredll.DestroyMenu
AppendMenu = windll.coredll.AppendMenuW
EnableMenuItem = windll.coredll.EnableMenuItem
CheckMenuItem = windll.coredll.CheckMenuItem
SendMessage = windll.coredll.SendMessageW
PostMessage = windll.coredll.PostMessageW
GetClientRect = windll.coredll.GetClientRect
GetWindowRect = windll.coredll.GetWindowRect
RegisterWindowMessage = windll.coredll.RegisterWindowMessageW
GetParent = windll.coredll.GetParent
GetWindowLong = cdll.coredll.GetWindowLongW
SetWindowLong = windll.coredll.SetWindowLongW
SetClassLong = windll.coredll.SetClassLongW
GetClassLong = windll.coredll.GetClassLongW
SetWindowPos = windll.coredll.SetWindowPos
InvalidateRect = windll.coredll.InvalidateRect
BeginPaint = windll.coredll.BeginPaint
EndPaint = windll.coredll.EndPaint
SetCapture = windll.coredll.SetCapture
GetCapture = windll.coredll.GetCapture
ReleaseCapture = windll.coredll.ReleaseCapture
ScreenToClient = windll.coredll.ScreenToClient
ClientToScreen = windll.coredll.ClientToScreen

IsDialogMessage = cdll.coredll.IsDialogMessageW
GetActiveWindow = cdll.coredll.GetActiveWindow
GetMessagePos = windll.coredll.GetMessagePos
BeginDeferWindowPos = windll.coredll.BeginDeferWindowPos
DeferWindowPos = windll.coredll.DeferWindowPos
EndDeferWindowPos = windll.coredll.EndDeferWindowPos
CreateAcceleratorTable = windll.coredll.CreateAcceleratorTableW
DestroyAcceleratorTable = windll.coredll.DestroyAcceleratorTable



GetModuleHandle = windll.coredll.GetModuleHandleW
GetModuleHandle.restype = ValidHandle
LoadLibrary = windll.coredll.LoadLibraryW
LoadLibrary.restype = ValidHandle
FindResource = windll.coredll.FindResourceW
FindResource.restype = ValidHandle
FindWindow = windll.coredll.FindWindowW
GetForegroundWindow = windll.coredll.GetForegroundWindow
ChildWindowFromPoint = windll.coredll.ChildWindowFromPoint

TrackPopupMenuEx = windll.coredll.TrackPopupMenuEx


GetMenuItemInfo = windll.coredll.GetMenuItemInfoW
GetMenuItemInfo.restype = ValidHandle
GetSubMenu = windll.coredll.GetSubMenu
SetMenuItemInfo = windll.coredll.SetMenuItemInfoW

SetWindowsHookEx = windll.coredll.SetWindowsHookExW
CallNextHookEx = windll.coredll.CallNextHookEx
UnhookWindowsHookEx = windll.coredll.UnhookWindowsHookEx



MessageBox = windll.coredll.MessageBoxW
SetWindowText = windll.coredll.SetWindowTextW

GetFocus = windll.coredll.GetFocus
SetFocus = windll.coredll.SetFocus

OpenClipboard = windll.coredll.OpenClipboard
EmptyClipboard = windll.coredll.EmptyClipboard
SetClipboardData = windll.coredll.SetClipboardData
GetClipboardData = windll.coredll.GetClipboardData
RegisterClipboardFormat = windll.coredll.RegisterClipboardFormatW
CloseClipboard = windll.coredll.CloseClipboard
EnumClipboardFormats = windll.coredll.EnumClipboardFormats
IsClipboardFormatAvailable = windll.coredll.IsClipboardFormatAvailable

GetDlgItem = windll.coredll.GetDlgItem
GetClassName = windll.coredll.GetClassNameW
EndDialog = windll.coredll.EndDialog

GetDesktopWindow = windll.coredll.GetDesktopWindow
MultiByteToWideChar = windll.coredll.MultiByteToWideChar
CreateDialogIndirectParam = windll.coredll.CreateDialogIndirectParamW
DialogBoxIndirectParam = windll.coredll.DialogBoxIndirectParamW



SetTimer = windll.coredll.SetTimer
KillTimer = windll.coredll.KillTimer

IsWindowVisible = windll.coredll.IsWindowVisible

GetCursorPos = windll.coredll.GetCursorPos
SetForegroundWindow = windll.coredll.SetForegroundWindow

GetClassInfo = windll.coredll.GetClassInfoW

OpenEvent = windll.coredll.OpenEventW
CreateEvent = windll.coredll.CreateEventW
GlobalAlloc = windll.coredll.LocalAlloc
GlobalFree = windll.coredll.LocalFree

Ellipse=windll.coredll.Ellipse
SetBkColor=windll.coredll.SetBkColor
GetStockObject = windll.coredll.GetStockObject
LineTo = windll.coredll.LineTo
MoveToEx = windll.coredll.MoveToEx
FillRect = windll.coredll.FillRect
DrawEdge = windll.coredll.DrawEdge
CreateCompatibleDC = windll.coredll.CreateCompatibleDC
CreateCompatibleBitmap = windll.coredll.CreateCompatibleBitmap
CreateCompatibleDC.restype = ValidHandle
SelectObject = windll.coredll.SelectObject
GetObject = windll.coredll.GetObjectW
DeleteObject = windll.coredll.DeleteObject
BitBlt = windll.coredll.BitBlt
StretchBlt = windll.coredll.StretchBlt
GetSysColorBrush = windll.coredll.GetSysColorBrush
#CreateHatchBrush = windll.coredll.CreateHatchBrush
CreatePatternBrush = windll.coredll.CreatePatternBrush
CreateSolidBrush = windll.coredll.CreateSolidBrush
CreateBitmap = windll.coredll.CreateBitmap
PatBlt = windll.coredll.PatBlt
#CreateFont = windll.coredll.CreateFontA
#EnumFontFamiliesEx = windll.coredll.EnumFontFamiliesExA
InvertRect = windll.coredll.InvertRect
DrawFocusRect = windll.coredll.DrawFocusRect
#ExtCreatePen = windll.coredll.ExtCreatePen
CreatePen = windll.coredll.CreatePen
DrawText = windll.coredll.DrawTextW
#TextOut = windll.coredll.TextOutA
CreateDIBSection = windll.coredll.CreateDIBSection
DeleteDC = windll.coredll.DeleteDC
#GetDIBits = windll.coredll.GetDIBits
CreateFontIndirect=windll.coredll.CreateFontIndirectW
Polyline = cdll.coredll.Polyline
FillRect = cdll.coredll.FillRect
SetTextColor = cdll.coredll.SetTextColor



#WinCe api
import ctypes
WM_APP = 0x8000
LineType = POINT*2
SHCMBF_EMPTYBAR = 0x0001
SHCMBF_HIDDEN = 0x0002

SHCMBF_HIDESIPBUTTON = 0x0004
SHCMBF_COLORBK = 0x0008
SHCMBF_HMENU = 0x0010
SPI_SETSIPINFO = 224
SPI_GETSIPINFO = 225

DrawMenuBar = ctypes.windll.coredll.DrawMenuBar
CommandBar_Create = ctypes.windll.commctrl.CommandBar_Create
SHCreateMenuBar = ctypes.windll.aygshell.SHCreateMenuBar
SHSipInfo = ctypes.windll.aygshell.SHSipInfo


class SIPINFO(ctypes.Structure) :

  _fields_ = [('cbSize', DWORD),('fdwFlags', DWORD),
              ('rcVisibleDesktop',RECT), ('rcSipRect', RECT),
              ('dwImDataSize', DWORD), ('pvImData', LPVOID)]

class SHMENUBARINFO(ctypes.Structure):

  _fields_ = [('cbSize', DWORD), ('hwndParent', HWND),
              ('dwFlags', DWORD), ('nToolBarId',UINT),
              ('hInstRes', HINSTANCE), ('nBmpId', INT),
              ('cBmpImages', INT), ('hwndMB', HWND),
              ('clrBk', COLORREF)]

class SHRGINFO(ctypes.Structure) :

  _fields_ = [('cbSize', DWORD), ('hwndClient', HWND),
              ('ptDown', POINT), ('dwFlags', DWORD)]

class SHACTIVATEINFO(ctypes.Structure) :
  _fields_ = [('cbSize', DWORD), ('hwndLastFocus', HWND),
              ('fSipUp', UINT,1), ('fSipOnDeactivation',UINT,1),
              ('fActive', UINT,1), ('fReserved', UINT,29)]

class SHINITDLGINFO(ctypes.Structure) :
  _fields_ = [('dwMask', DWORD), ('hDlg', HWND), ('dwFlags', DWORD) ]

SHInitDialog = ctypes.windll.aygshell.SHInitDialog
SHRecognizeGesture = ctypes.windll.aygshell.SHRecognizeGesture

SHRG_RETURNCMD = 1
GN_CONTEXTMENU = 1000
SHIDIF_DONEBUTTON = 1
SHIDIF_SIZEDLGFULLSCREEN = 4

try : 
  SHHandleWMActivate = ctypes.windll.aygshell.SHHandleWMActivate
  SHHandleWMSettingChange = ctypes.windll.aygshell.SHHandleWMSettingChange
except : # WinCe 4.20 bugfix (Thanks to Jan Ischebeck)
  SHHandleWMActivate = ctypes.windll.aygshell[84]
  SHHandleWMSettingChange = ctypes.windll.aygshell[83]
   
def InitSHActivateInfo():
  shai = SHACTIVATEINFO()
  ctypes.memset(byref(shai), 0, ctypes.sizeof(SHACTIVATEINFO))
  shai.cbSize = ctypes.sizeof(SHACTIVATEINFO)
  return shai
  
GetTextExtentExPointW = cdll.coredll.GetTextExtentExPointW

class SIZE(Structure):
    _fields_ = [('cx', LONG),
                ('cy', LONG)]
    
def GetTextExtent(hdc, string):
    n = len(string)
    size = SIZE()
    GetTextExtentExPointW(hdc, string, n, 0, 0, 0, byref(size))
    return size.cx, size.cy
########NEW FILE########
__FILENAME__ = w32comctl
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from w32api import *

ATL_IDW_BAND_FIRST = 0xEB00
HTREEITEM = HANDLE
HIMAGELIST = HANDLE

UINT_MAX = (1l << 32)

LVCF_FMT     =1
LVCF_WIDTH   =2
LVCF_TEXT    =4
LVCF_SUBITEM =8
LVCF_IMAGE= 16
LVCF_ORDER= 32

TVIF_TEXT    = 1
TVIF_IMAGE   =2
TVIF_PARAM   =4
TVIF_STATE   =8
TVIF_HANDLE = 16
TVIF_SELECTEDIMAGE  = 32
TVIF_CHILDREN      =  64
TVIF_INTEGRAL      =  0x0080
TVIF_DI_SETITEM    =  0x1000

LVIF_TEXT   = 1
LVIF_IMAGE  = 2
LVIF_PARAM  = 4
LVIF_STATE  = 8
LVIF_DI_SETITEM =  0x1000

LVIS_SELECTED = 0x0002

COMCTL32_VERSION = 0x020c
CCM_FIRST = 0x2000
CCM_SETVERSION = CCM_FIRST+0x7
CCM_GETVERSION = CCM_FIRST+0x8
TCS_BOTTOM = 0x2

class MaskedStructureType(Structure.__class__):
    def __new__(cls, name, bases, dct):
        fields = []
        for field in dct['_fields_']:
            fields.append((field[0], field[1]))
            if len(field) == 4: #masked field
                dct[field[3]] = property(None,
                                         lambda self, val, field = field:
                                         self.setProperty(field[0], field[2], val))
        dct['_fields_'] = fields
        return Structure.__class__.__new__(cls, name, bases, dct)
    
class MaskedStructure(Structure):
    __metaclass__ = MaskedStructureType
    _fields_ = []

    def setProperty(self, name, mask, value):
        setattr(self, self._mask_, getattr(self, self._mask_) | mask)
        setattr(self, name, value)

    def clear(self):
        setattr(self, self._mask_, 0)
        
class NMCBEENDEDIT(Structure):
    _fields_ = [("hdr", NMHDR),
                ("fChanged", BOOL),
                ("iNewSelection", INT),
                ("szText", POINTER(TCHAR)),
                ("iWhy", INT)]

class LVCOLUMN(MaskedStructure):
    _mask_ = 'mask'
    _fields_ = [("mask", UINT),
                ("fmt", INT, LVCF_FMT, "format"),
                ("cx", INT, LVCF_WIDTH, 'width'),
                ("pszText", LPTSTR, LVCF_TEXT, 'text'),
                ("cchTextMax", INT),
                ("iSubItem", INT),
                ("iImage", INT),
                ("iOrder", INT)]

class LVITEM(Structure):
    _fields_ = [("mask", UINT),
                ("iItem", INT),
                ("iSubItem", INT),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR),
                ("cchTextMax", INT),
                ("iImage", INT),
                ("lParam", LPARAM),
                ("iIndent", INT)]

class LV_DISPINFO(Structure):
    _fields_ = [("hdr", NMHDR),
                ("item", LVITEM)]
    

class TV_ITEMEX(MaskedStructure):
    _mask_ = 'mask'
    _fields_ = [("mask", UINT),
                ("hItem", HTREEITEM),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR, TVIF_TEXT, 'text'),
                ("cchTextMax", INT),
                ("iImage", INT, TVIF_IMAGE, 'image'),
                ("iSelectedImage", INT, TVIF_SELECTEDIMAGE, 'selectedImage'),
                ("cChildren", INT, TVIF_CHILDREN, 'children'),
                ("lParam", LPARAM, TVIF_PARAM, 'param'),
                ("iIntegral", INT)]

class TVITEMOLD(Structure):
    _fields_ = [("mask", UINT),
                ("hItem", HTREEITEM),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR),
                ("cchTextMax", INT),
                ("iImage", INT),
                ("iSelectedImage", INT),
                ("cChildren", INT),
                ("lParam", LPARAM)]

class TVITEM(MaskedStructure):
    _mask_ = 'mask'
    _fields_ = [("mask", UINT),
                ("hItem", HTREEITEM),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR, TVIF_TEXT, 'text'),
                ("cchTextMax", INT),
                ("iImage", INT, TVIF_IMAGE,'image'),
                ("iSelectedImage", INT, TVIF_SELECTEDIMAGE, 'selectedImage'),
                ("cChildren", INT, TVIF_CHILDREN,'children'), 
                ("lParam", LPARAM, TVIF_PARAM,'param')]

class TBBUTTON(Structure):
    _fields_ = [("iBitmap", INT),
                ("idCommand", INT),
                ("fsState", BYTE),
                ("fsStyle", BYTE),
                #("bReserved", BYTE * 2),
                ("dwData", DWORD_PTR),
                ("iString", INT_PTR)]

class TBBUTTONINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("dwMask", DWORD),
                ("idCommand", INT),
                ("iImage", INT),
                ("fsState", BYTE),
                ("fsStyle", BYTE),
                ("cx", WORD),
                ("lParam", DWORD_PTR),
                ("pszText", LPTSTR),
                ("cchText", INT)]

class TVINSERTSTRUCT(Structure):
    _fields_ = [("hParent", HTREEITEM),
                ("hInsertAfter", HTREEITEM),
                ("item", TVITEM)]

class TCITEM(Structure):
    _fields_ = [("mask", UINT),
                ("dwState", DWORD),
                ("dwStateMask", DWORD),
                ("pszText", LPTSTR),
                ("cchTextMax", INT),
                ("iImage", INT),
                ("lParam", LPARAM)]

class NMTREEVIEW(Structure):
    _fields_ = [("hdr", NMHDR),
                ("action", UINT),
                ("itemOld", TVITEM),
                ("itemNew", TVITEM),
                ("ptDrag", POINT)]

class NMLISTVIEW(Structure):
    _fields_ = [("hrd", NMHDR),
                ("iItem", INT),
                ("iSubItem", INT),
                ("uNewState", UINT),
                ("uOldState", UINT),
                ("uChanged", UINT),
                ("ptAction", POINT),
                ("lParam", LPARAM)]
    
class INITCOMMONCONTROLSEX(Structure):
    _fields_ = [("dwSize", DWORD),
                ("dwICC", DWORD)]

class REBARINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("fMask", UINT),
                ("himl", HIMAGELIST)]

class REBARBANDINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("fMask", UINT),
                ("fStyle", UINT),
                ("clrFore", COLORREF),
                ("clrBack", COLORREF),
                ("lpText", LPTSTR),
                ("cch", UINT),
                ("iImage", INT),
                ("hwndChild", HWND),
                ("cxMinChild", UINT),
                ("cyMinChild", UINT),
                ("cx", UINT),
                ("hbmBack", HBITMAP),
                ("wID", UINT),
                ("cyChild", UINT),
                ("cyMaxChild", UINT),
                ("cyIntegral", UINT),
                ("cxIdeal", UINT),
                ("lParam", LPARAM),
                ("cxHeader", UINT)]

class NMTOOLBAR(Structure):
    _fields_ = [("hdr", NMHDR),
                ("iItem", INT),
                ("tbButton", TBBUTTON),
                ("cchText", INT),
                ("pszText", LPTSTR),
                ("rcButton", RECT)]

class NMTBHOTITEM(Structure):
    _fields_ = [("hdr", NMHDR),
                ("idOld", INT),
                ("idNew", INT),
                ("dwFlags", DWORD)]

class PBRANGE(Structure):
    _fields_ = [("iLow", INT),
                ("iHigh", INT)]
    
class NMITEMACTIVATE(Structure):
    _fields_ = [("hdr", NMHDR),
                ("iItem", c_int),
                ("iSubItem", c_int),
                ("uNewState", UINT),
                ("uOldState", UINT),
                ("uChanged", UINT),
                ("ptAction", POINT),
                ("lParam", LPARAM),
                ("uKeyFlags", UINT)]

NM_FIRST    =   UINT_MAX

SBS_BOTTOMALIGN = 4
SBS_HORZ = 0
SBS_LEFTALIGN = 2
SBS_RIGHTALIGN = 4
SBS_SIZEBOX = 8
SBS_SIZEBOXBOTTOMRIGHTALIGN = 4
SBS_SIZEBOXTOPLEFTALIGN = 2
SBS_SIZEGRIP = 16
SBS_TOPALIGN = 2
SBS_VERT = 1

CCS_NODIVIDER =	64
CCS_NOPARENTALIGN = 8
CCS_NORESIZE = 4
CCS_TOP = 1


CBS_DROPDOWN = 2

RBBS_BREAK = 1
RBBS_FIXEDSIZE = 2
RBBS_CHILDEDGE = 4
RBBS_HIDDEN = 8
RBBS_NOVERT = 16
RBBS_FIXEDBMP = 32
RBBS_VARIABLEHEIGHT = 64
RBBS_GRIPPERALWAYS = 128
RBBS_NOGRIPPER = 256

RBS_TOOLTIPS = 256
RBS_VARHEIGHT = 512
RBS_BANDBORDERS = 1024
RBS_FIXEDORDER = 2048

RBS_REGISTERDROP = 4096
RBS_AUTOSIZE = 8192
RBS_VERTICALGRIPPER = 16384
RBS_DBLCLKTOGGLE = 32768

RBN_FIRST	= ((UINT_MAX) - 831)
RBN_HEIGHTCHANGE = RBN_FIRST

TBSTYLE_FLAT = 2048
TBSTYLE_LIST = 4096
TBSTYLE_DROPDOWN = 8
TBSTYLE_TRANSPARENT = 0x8000
TBSTYLE_REGISTERDROP = 0x4000
TBSTYLE_BUTTON = 0x0000
TBSTYLE_AUTOSIZE = 0x0010
    
TB_ADDBITMAP = 0x0413
TB_ENABLEBUTTON = 0x401
TB_CHECKBUTTON = 0x402
TB_ISBUTTONCHECKED = WM_USER+10
TB_BUTTONSTRUCTSIZE = WM_USER+30
TB_ADDBUTTONS       = WM_USER+20
TB_INSERTBUTTONA    = WM_USER + 21
TB_INSERTBUTTON     = WM_USER + 21
TB_BUTTONCOUNT      = WM_USER + 24
TB_GETITEMRECT      = WM_USER + 29
TB_SETBUTTONINFOW  =  WM_USER + 64
TB_SETBUTTONINFOA  =  WM_USER + 66
TB_SETBUTTONINFO   =  TB_SETBUTTONINFOA
TB_SETIMAGELIST    =  WM_USER + 48
TB_SETDRAWTEXTFLAGS =  WM_USER + 70
TB_PRESSBUTTON       = WM_USER + 3
TB_GETRECT        =      (WM_USER + 51)
TB_SETHOTITEM   =        (WM_USER + 72)
TB_HITTEST     =         (WM_USER + 69)
TB_GETHOTITEM  =         (WM_USER + 7)
TB_SETBUTTONSIZE     =  (WM_USER + 31)
TB_AUTOSIZE          =  (WM_USER + 33)
TB_DELETEBUTTON = WM_USER + 22

TVIF_TEXT    = 1
TVIF_IMAGE   =2
TVIF_PARAM   =4
TVIF_STATE   =8
TVIF_HANDLE = 16
TVIF_SELECTEDIMAGE  = 32
TVIF_CHILDREN      =  64
TVIF_INTEGRAL      =  0x0080
TVIF_DI_SETITEM    =  0x1000
 
TVI_ROOT     = 0xFFFF0000l
TVI_FIRST    = 0xFFFF0001l
TVI_LAST     = 0xFFFF0002l
TVI_SORT     = 0xFFFF0003l

TVGN_CHILD   =  4
TVGN_NEXT    =  1
TVGN_ROOT    =  0
TVGN_CARET   =           0x0009

TVIS_FOCUSED = 1
TVIS_SELECTED =       2
TVIS_CUT    = 4
TVIS_DROPHILITED   =  8
TVIS_BOLD  =  16
TVIS_EXPANDED      =  32
TVIS_EXPANDEDONCE  =  64
TVIS_OVERLAYMASK   =  0xF00
TVIS_STATEIMAGEMASK = 0xF000
TVIS_USERMASK      =  0xF000

TV_FIRST = 0x1100
TVM_INSERTITEMA =     TV_FIRST
TVM_INSERTITEMW =    (TV_FIRST+50)
TVM_INSERTITEM = TVM_INSERTITEMW
TVM_SETIMAGELIST =    (TV_FIRST+9)
TVM_DELETEITEM   =   (TV_FIRST+1)
TVM_GETNEXTITEM   =   (TV_FIRST+10)
TVM_EXPAND =   (TV_FIRST+2)
TVM_GETITEMSTATE=        (TV_FIRST + 39)
TVM_ENSUREVISIBLE=       (TV_FIRST + 20)
TVM_SELECTITEM=          (TV_FIRST + 11)
TVM_SETITEMA=            (TV_FIRST + 13)
TVM_SETITEMW =           (TV_FIRST + 63)
TVM_SETITEM= TVM_SETITEMW
TVM_GETITEMA=            (TV_FIRST + 12)
TVM_GETITEMW =           (TV_FIRST + 62)
TVM_GETITEM = TVM_GETITEMW


TVS_HASBUTTONS =       1
TVS_HASLINES = 2
TVS_LINESATROOT =      4
TVS_EDITLABELS  =      8
TVS_DISABLEDRAGDROP =  16
TVS_SHOWSELALWAYS =   32
TVS_CHECKBOXES =  256
TVS_TOOLTIPS = 128
TVS_RTLREADING = 64
TVS_TRACKSELECT = 512
TVS_FULLROWSELECT = 4096
TVS_INFOTIP = 2048
TVS_NONEVENHEIGHT = 16384
TVS_NOSCROLL  = 8192
TVS_SINGLEEXPAND  =1024
TVS_NOHSCROLL   =     0x8000

CBEN_FIRST  =  (UINT_MAX) - 800
CBEN_ENDEDITA = CBEN_FIRST - 5
CBEN_ENDEDITW = CBEN_FIRST - 6
CBEN_ENDEDIT = CBEN_ENDEDITA

# trackbar styles
TBS_AUTOTICKS =           0x0001
TBS_VERT =                0x0002
TBS_HORZ =                0x0000
TBS_TOP =                 0x0004
TBS_BOTTOM =              0x0000
TBS_LEFT =                0x0004
TBS_RIGHT =               0x0000
TBS_BOTH =                0x0008
TBS_NOTICKS =             0x0010
TBS_ENABLESELRANGE =      0x0020
TBS_FIXEDLENGTH =         0x0040
TBS_NOTHUMB =             0x0080
TBS_TOOLTIPS =            0x0100

# trackbar messages
TBM_GETPOS =              (WM_USER)
TBM_GETRANGEMIN =         (WM_USER+1)
TBM_GETRANGEMAX =         (WM_USER+2)
TBM_GETTIC =              (WM_USER+3)
TBM_SETTIC =              (WM_USER+4)
TBM_SETPOS =              (WM_USER+5)
TBM_SETRANGE =            (WM_USER+6)
TBM_SETRANGEMIN =         (WM_USER+7)
TBM_SETRANGEMAX =         (WM_USER+8)
TBM_CLEARTICS =           (WM_USER+9)
TBM_SETSEL =              (WM_USER+10)
TBM_SETSELSTART =         (WM_USER+11)
TBM_SETSELEND =           (WM_USER+12)
TBM_GETPTICS =            (WM_USER+14)
TBM_GETTICPOS =           (WM_USER+15)
TBM_GETNUMTICS =          (WM_USER+16)
TBM_GETSELSTART =         (WM_USER+17)
TBM_GETSELEND =           (WM_USER+18)
TBM_CLEARSEL =            (WM_USER+19)
TBM_SETTICFREQ =          (WM_USER+20)
TBM_SETPAGESIZE =         (WM_USER+21)
TBM_GETPAGESIZE =         (WM_USER+22)
TBM_SETLINESIZE =         (WM_USER+23)
TBM_GETLINESIZE =         (WM_USER+24)
TBM_GETTHUMBRECT =        (WM_USER+25)
TBM_GETCHANNELRECT =      (WM_USER+26)
TBM_SETTHUMBLENGTH =      (WM_USER+27)
TBM_GETTHUMBLENGTH =      (WM_USER+28)
TBM_SETTOOLTIPS =         (WM_USER+29)
TBM_GETTOOLTIPS =         (WM_USER+30)
TBM_SETTIPSIDE =          (WM_USER+31)
TBM_SETBUDDY =            (WM_USER+32) 
TBM_GETBUDDY =            (WM_USER+33) 

# trackbar top-side flags
TBTS_TOP =                0
TBTS_LEFT =               1
TBTS_BOTTOM =             2
TBTS_RIGHT =              3


TB_LINEUP =               0
TB_LINEDOWN =             1
TB_PAGEUP =               2
TB_PAGEDOWN =             3
TB_THUMBPOSITION =        4
TB_THUMBTRACK =           5
TB_TOP =                  6
TB_BOTTOM =               7
TB_ENDTRACK =             8

# trackbar custom draw item specs
TBCD_TICS =    0x0001
TBCD_THUMB =   0x0002
TBCD_CHANNEL = 0x0003



STATUSCLASSNAME = u"msctls_statusbar32"

REBARCLASSNAMEW = u"ReBarWindow32"
REBARCLASSNAMEA = u"ReBarWindow32"
REBARCLASSNAME = REBARCLASSNAMEA

PROGRESS_CLASSW = u"msctls_progress32"
PROGRESS_CLASSA = u"msctls_progress32"
PROGRESS_CLASS = PROGRESS_CLASSA

TRACKBAR_CLASSW = u"msctls_trackbar32"
TRACKBAR_CLASSA = u"msctls_trackbar32"
TRACKBAR_CLASS = TRACKBAR_CLASSA


EDIT = u"edit"
BUTTON = u"button"

WC_COMBOBOXEXW = u"ComboBoxEx32"
WC_COMBOBOXEXA = u"ComboBoxEx32"
WC_COMBOBOXEX = WC_COMBOBOXEXA

WC_TREEVIEWA = u"SysTreeView32"
WC_TREEVIEWW = u"SysTreeView32"
WC_TREEVIEW = WC_TREEVIEWA

WC_LISTVIEWA = u"SysListView32"
WC_LISTVIEWW = u"SysListView32"
WC_LISTVIEW = WC_LISTVIEWA

TOOLBARCLASSNAMEW = u"ToolbarWindow32"
TOOLBARCLASSNAMEA = u"ToolbarWindow32"
TOOLBARCLASSNAME = TOOLBARCLASSNAMEA

WC_TABCONTROLA =    u"SysTabControl32"
WC_TABCONTROLW =      u"SysTabControl32"
WC_TABCONTROL = WC_TABCONTROLA

LVS_ICON    = 0
LVS_REPORT   =1
LVS_SMALLICON =       2
LVS_LIST    = 3
LVS_TYPEMASK= 3
LVS_SINGLESEL=        4
LVS_SHOWSELALWAYS=    8
LVS_SORTASCENDING =   16
LVS_SORTDESCENDING =  32
LVS_SHAREIMAGELISTS = 64
LVS_NOLABELWRAP     = 128
LVS_AUTOARRANGE     = 256
LVS_EDITLABELS      = 512
LVS_NOSCROLL= 0x2000
LVS_TYPESTYLEMASK  =  0xfc00
LVS_ALIGNTOP= 0
LVS_ALIGNLEFT =       0x800
LVS_ALIGNMASK  =      0xc00
LVS_OWNERDRAWFIXED=   0x400
LVS_NOCOLUMNHEADER =  0x4000
LVS_NOSORTHEADER   =  0x8000
LVS_OWNERDATA =4096
LVS_EX_CHECKBOXES= 4
LVS_EX_FULLROWSELECT= 32
LVS_EX_GRIDLINES =1
LVS_EX_HEADERDRAGDROP= 16
LVS_EX_ONECLICKACTIVATE= 64
LVS_EX_SUBITEMIMAGES= 2
LVS_EX_TRACKSELECT= 8
LVS_EX_TWOCLICKACTIVATE= 128
LVS_EX_FLATSB       = 0x00000100
LVS_EX_REGIONAL     = 0x00000200
LVS_EX_INFOTIP      = 0x00000400
LVS_EX_UNDERLINEHOT = 0x00000800
LVS_EX_UNDERLINECOLD= 0x00001000
LVS_EX_MULTIWORKAREAS =       0x00002000
LVS_EX_LABELTIP     = 0x00004000
LVS_EX_BORDERSELECT = 0x00008000

LVIS_FOCUSED         =   0x0001
LVIS_SELECTED        =   0x0002
LVIS_CUT             =   0x0004
LVIS_DROPHILITED     =   0x0008
LVIS_ACTIVATING      =   0x0020

LVIS_OVERLAYMASK      =  0x0F00
LVIS_STATEIMAGEMASK   =  0xF000

LVM_FIRST = 0x1000
LVM_INSERTCOLUMNA = (LVM_FIRST+27)
LVM_INSERTCOLUMNW = (LVM_FIRST+97)
LVM_INSERTCOLUMN = LVM_INSERTCOLUMNW
LVM_INSERTITEMA = (LVM_FIRST+7)
LVM_SETITEMA = (LVM_FIRST+6)
LVM_INSERTITEMW = (LVM_FIRST+77)
LVM_SETITEMW = (LVM_FIRST+76)
LVM_INSERTITEM = LVM_INSERTITEMW
LVM_SETITEM = LVM_SETITEMW
LVM_DELETEALLITEMS =  (LVM_FIRST + 9)
LVM_SETITEMSTATE  =  (LVM_FIRST + 43)
LVM_GETITEMCOUNT  =  (LVM_FIRST + 4)
LVM_SETITEMCOUNT  =  (LVM_FIRST + 47)
LVM_GETITEMSTATE   =  (LVM_FIRST + 44)
LVM_GETSELECTEDCOUNT =   (LVM_FIRST + 50)
LVM_SETCOLUMNA  =        (LVM_FIRST + 26)
LVM_SETCOLUMNW  =        (LVM_FIRST + 96)
LVM_SETCOLUMN = LVM_SETCOLUMNW
LVM_SETCOLUMNWIDTH =  (LVM_FIRST + 30)
LVM_GETITEMA   =         (LVM_FIRST + 5)
LVM_GETITEMW   =         (LVM_FIRST + 75)
LVM_GETITEM = LVM_GETITEMW
LVM_SETEXTENDEDLISTVIEWSTYLE = (LVM_FIRST + 54)
LVM_GETNEXTITEM = (LVM_FIRST + 12)
LVS_SHAREIL = 0x4
LVM_SETIMAGELIST = (LVM_FIRST + 3)

LVNI_SELECTED = 0x2

LVN_FIRST = (UINT_MAX) - 100
LVN_ITEMCHANGING    =    (LVN_FIRST-0)
LVN_ITEMCHANGED     =    (LVN_FIRST-1)
LVN_INSERTITEM      =    (LVN_FIRST-2)
LVN_DELETEITEM       =   (LVN_FIRST-3)
LVN_DELETEALLITEMS    =  (LVN_FIRST-4)
LVN_BEGINLABELEDITA   =  (LVN_FIRST-5)
LVN_BEGINLABELEDITW   =  (LVN_FIRST-75)
LVN_ENDLABELEDITA     =  (LVN_FIRST-6)
LVN_ENDLABELEDITW     =  (LVN_FIRST-76)
LVN_COLUMNCLICK       =  (LVN_FIRST-8)
LVN_BEGINDRAG         =  (LVN_FIRST-9)
LVN_BEGINRDRAG        =  (LVN_FIRST-11)
LVN_GETDISPINFO = (LVN_FIRST - 77)

NM_OUTOFMEMORY    =      (NM_FIRST-1)
NM_CLICK          =      (NM_FIRST-2)   
NM_DBLCLK         =      (NM_FIRST-3)
NM_RETURN         =      (NM_FIRST-4)
NM_RCLICK         =      (NM_FIRST-5)   
NM_RDBLCLK        =      (NM_FIRST-6)
NM_SETFOCUS       =      (NM_FIRST-7)
NM_KILLFOCUS      =      (NM_FIRST-8)
NM_CUSTOMDRAW     =      (NM_FIRST-12)
NM_HOVER          =      (NM_FIRST-13)
NM_NCHITTEST      =      (NM_FIRST-14)  
NM_KEYDOWN        =      (NM_FIRST-15)  
NM_RELEASEDCAPTURE=      (NM_FIRST-16)
NM_SETCURSOR      =      (NM_FIRST-17)  
NM_CHAR           =      (NM_FIRST-18)  

LVCFMT_LEFT = 0
LVCFMT_RIGHT= 1
LVCFMT_CENTER   =     2
LVCFMT_JUSTIFYMASK =  3
LVCFMT_BITMAP_ON_RIGHT =4096
LVCFMT_COL_HAS_IMAGES = 32768
LVCFMT_IMAGE =2048


ICC_LISTVIEW_CLASSES =1
ICC_TREEVIEW_CLASSES =2
ICC_BAR_CLASSES      =4
ICC_TAB_CLASSES      =8
ICC_UPDOWN_CLASS =16
ICC_PROGRESS_CLASS =32
ICC_HOTKEY_CLASS =64
ICC_ANIMATE_CLASS= 128
ICC_WIN95_CLASSES= 255
ICC_DATE_CLASSES =256
ICC_USEREX_CLASSES =512
ICC_COOL_CLASSES =1024
ICC_INTERNET_CLASSES =2048
ICC_PAGESCROLLER_CLASS =4096
ICC_NATIVEFNTCTL_CLASS= 8192

TCN_FIRST  =  (UINT_MAX) -550
TCN_LAST   =  (UINT_MAX) -580
TCN_KEYDOWN   =  TCN_FIRST
TCN_SELCHANGE =        (TCN_FIRST-1)
TCN_SELCHANGING  =     (TCN_FIRST-2)

TVE_COLLAPSE =1
TVE_EXPAND   =2
TVE_TOGGLE   =3
TVE_COLLAPSERESET   = 0x8000

TCM_FIRST   = 0x1300
TCM_INSERTITEMA  =    (TCM_FIRST+7)
TCM_INSERTITEMW  =   (TCM_FIRST+62)
TCM_INSERTITEM = TCM_INSERTITEMW
TCM_ADJUSTRECT = (TCM_FIRST+40)
TCM_GETCURSEL   =     (TCM_FIRST+11)
TCM_SETCURSEL   =     (TCM_FIRST+12)
TCM_GETITEMA = (TCM_FIRST+5)
TCM_GETITEMW = (TCM_FIRST+60)
TCM_GETITEM = TCM_GETITEMW
TCM_DELETEITEM = (TCM_FIRST + 8)
TCM_GETITEMCOUNT = (TCM_FIRST + 4)

TVN_FIRST  =  ((UINT_MAX)-400)
TVN_LAST   =  ((UINT_MAX)-499)
TVN_ITEMEXPANDINGA =  (TVN_FIRST-5)
TVN_ITEMEXPANDINGW =  (TVN_FIRST-54)
TVN_ITEMEXPANDING = TVN_ITEMEXPANDINGW
TVN_SELCHANGEDA  =    (TVN_FIRST-2)
TVN_SELCHANGEDW  =    (TVN_FIRST-51)
TVN_SELCHANGED  =  TVN_SELCHANGEDW
TVN_DELETEITEMA  =     (TVN_FIRST-9)
TVN_DELETEITEMW  =    (TVN_FIRST-58)
TVN_DELETEITEM = TVN_DELETEITEMW


ES_LEFT = 0
ES_CENTER  = 1
ES_RIGHT    =   0x0002
ES_MULTILINE   = 0x0004
ES_UPPERCASE  =  0x0008
ES_LOWERCASE =   0x0010
ES_PASSWORD   =  0x0020
ES_AUTOVSCROLL = 0x0040
ES_AUTOHSCROLL  =0x0080
ES_NOHIDESEL   = 0x0100
ES_COMBOBOX 	=0x0200
ES_OEMCONVERT  = 0x0400
ES_READONLY    = 0x0800
ES_WANTRETURN  = 0x1000

SB_SIMPLE =   (WM_USER+9)
SB_SETTEXTA = (WM_USER+1)
SB_SETTEXTW = (WM_USER+11)
SB_SETTEXT = SB_SETTEXTW

SBT_OWNERDRAW   =     0x1000
SBT_NOBORDERS   =     256
SBT_POPOUT   = 512
SBT_RTLREADING =      1024
SBT_OWNERDRAW  =      0x1000
SBT_NOBORDERS  =      256
SBT_POPOUT   = 512
SBT_RTLREADING = 1024
SBT_TOOLTIPS = 0x0800

TBN_FIRST          =  ((UINT_MAX)-700)
TBN_DROPDOWN       =     (TBN_FIRST - 10)
TBN_HOTITEMCHANGE  =  (TBN_FIRST - 13)
TBDDRET_DEFAULT       =  0
TBDDRET_NODEFAULT     =  1
TBDDRET_TREATPRESSED  =  2

PBS_SMOOTH   = 0x01
PBS_VERTICAL = 0x04

CCM_FIRST      = 0x2000 # Common control shared messages
CCM_SETBKCOLOR = (CCM_FIRST + 1)

PBM_SETRANGE    = (WM_USER+1)
PBM_SETPOS      = (WM_USER+2)
PBM_DELTAPOS    = (WM_USER+3)
PBM_SETSTEP     = (WM_USER+4)
PBM_STEPIT      = (WM_USER+5)
PBM_SETRANGE32  = (WM_USER+6)
PBM_GETRANGE    = (WM_USER+7)
PBM_GETPOS      = (WM_USER+8)
PBM_SETBARCOLOR = (WM_USER+9)
PBM_SETBKCOLOR  = CCM_SETBKCOLOR


# ListBox Messages
LB_ADDSTRING = 384
LB_INSERTSTRING = 385
LB_DELETESTRING = 386
LB_RESETCONTENT = 388
LB_GETCOUNT = 395
LB_SETTOPINDEX = 407
LB_GETCURSEL =  0x0188

# ComboBox styles
CBS_DROPDOWN         = 0x0002L
CBS_DROPDOWNLIST      =0x0003L
CBS_AUTOHSCROLL       =0x0040L
CBS_OEMCONVERT      =  0x0080L
CBS_SORT             = 0x0100L
CBS_HASSTRINGS       = 0x0200L
CBS_NOINTEGRALHEIGHT = 0x0400L
CBS_DISABLENOSCROLL  = 0x0800L
CBS_UPPERCASE         =  0x2000L
CBS_LOWERCASE          = 0x4000L

ImageList_Create = windll.coredll.ImageList_Create
ImageList_Destroy = windll.coredll.ImageList_Destroy
ImageList_Add = windll.coredll.ImageList_Add
ImageList_AddMasked = windll.coredll.ImageList_AddMasked
#ImageList_AddIcon = windll.coredll.ImageList_AddIcon
ImageList_SetBkColor = windll.coredll.ImageList_SetBkColor
ImageList_ReplaceIcon = windll.coredll.ImageList_ReplaceIcon

def ImageList_AddIcon(a, b):
    return ImageList_ReplaceIcon(a, -1, b)

InitCommonControlsEx = windll.commctrl.InitCommonControlsEx

# Nouveautes

# Static control 

SS_LEFT = 0x00000000L
SS_CENTER = 0x00000001L
SS_RIGHT = 0x00000002L
SS_ICON = 0x00000003L
SS_LEFTNOWORDWRAP = 0x0000000CL
SS_BITMAP = 0x0000000EL
SS_NOPREFIX = 0x00000080L
SS_CENTERIMAGE = 0x00000200L
SS_NOTIFY = 0x00000100L
STN_CLICKED = 0
STN_ENABLE = 2
STN_DISABLE = 3
STM_SETIMAGE = 0x0172
STM_GETIMAGE = 0x0173

# Button control

BS_PUSHBUTTON = 0x00000000L
BS_DEFPUSHBUTTON = 0x00000001L
BS_CHECKBOX = 0x00000002L
BS_AUTOCHECKBOX = 0x00000003L
BS_RADIOBUTTON = 0x00000004L
BS_3STATE = 0x00000005L
BS_AUTO3STATE = 0x00000006L
BS_GROUPBOX = 0x00000007L
BS_AUTORADIOBUTTON = 0x00000009L
BS_OWNERDRAW = 0x0000000BL
BS_LEFTTEXT = 0x00000020L
BS_TEXT = 0x00000000L
BS_LEFT = 0x00000100L
BS_RIGHT = 0x00000200L
BS_CENTER = 0x00000300L
BS_TOP = 0x00000400L
BN_CLICKED = 0
BN_PAINT = 1
BN_DBLCLK = 5
BN_SETFOCUS = 6
BN_KILLFOCUS = 7
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BM_GETSTATE = 0x00F2
BM_SETSTATE = 0x00F3
BM_SETSTYLE = 0x00F4
BM_CLICK = 0x00F5
BST_UNCHECKED = 0x0000
BST_CHECKED = 0x0001
BST_INDETERMINATE = 0x0002
BST_PUSHED = 0x0004
BST_FOCUS = 0x0008

# Edit control

ES_LEFT = 0x0000L
ES_CENTER = 0x0001L
ES_RIGHT = 0x0002L
ES_MULTILINE = 0x0004L
ES_UPPERCASE = 0x0008L
ES_LOWERCASE = 0x0010L
ES_PASSWORD = 0x0020L
ES_AUTOVSCROLL = 0x0040L
ES_AUTOHSCROLL = 0x0080L
ES_NOHIDESEL = 0x0100L
ES_COMBOBOX = 0x0200L
ES_OEMCONVERT = 0x0400L
ES_READONLY = 0x0800L
ES_WANTRETURN = 0x1000L
ES_NUMBER = 0x2000L
EN_SETFOCUS = 0x0100
EN_KILLFOCUS = 0x0200
EN_CHANGE = 0x0300
EN_UPDATE = 0x0400
EN_ERRSPACE = 0x0500
EN_MAXTEXT = 0x0501
EN_HSCROLL = 0x0601
EN_VSCROLL = 0x0602
EC_LEFTMARGIN = 0x0001
EC_RIGHTMARGIN = 0x0002
EC_USEFONTINFO = 0xffff
EM_GETSEL = 0x00B0
EM_SETSEL = 0x00B1
EM_GETRECT = 0x00B2
EM_SETRECT = 0x00B3
EM_SETRECTNP = 0x00B4
EM_SCROLL = 0x00B5
EM_LINESCROLL = 0x00B6
EM_SCROLLCARET = 0x00B7
EM_GETMODIFY = 0x00B8
EM_SETMODIFY = 0x00B9
EM_GETLINECOUNT = 0x00BA
EM_LINEINDEX = 0x00BB
EM_LINELENGTH = 0x00C1
EM_REPLACESEL = 0x00C2
EM_GETLINE = 0x00C4
EM_LIMITTEXT = 0x00C5
EM_CANUNDO = 0x00C6
EM_UNDO = 0x00C7
EM_FMTLINES = 0x00C8
EM_LINEFROMCHAR = 0x00C9
EM_SETTABSTOPS = 0x00CB
EM_SETPASSWORDCHAR = 0x00CC
EM_EMPTYUNDOBUFFER = 0x00CD
EM_GETFIRSTVISIBLELINE = 0x00CE
EM_SETREADONLY = 0x00CF
EM_GETPASSWORDCHAR = 0x00D2
EM_SETMARGINS = 0x00D3
EM_GETMARGINS = 0x00D4
EM_SETLIMITTEXT = EM_LIMITTEXT
EM_GETLIMITTEXT = 0x00D5
EM_POSFROMCHAR = 0x00D6
EM_CHARFROMPOS = 0x00D7

# List Box control

LB_OKAY = 0
LB_ERR = (-1)
LB_ERRSPACE = (-2)
LBN_ERRSPACE = (-2)
LBN_SELCHANGE = 1
LBN_DBLCLK = 2
LBN_SELCANCEL = 3
LBN_SETFOCUS = 4
LBN_KILLFOCUS = 5
LB_ADDSTRING = 0x0180
LB_INSERTSTRING = 0x0181
LB_DELETESTRING = 0x0182
LB_SELITEMRANGEEX = 0x0183
LB_RESETCONTENT = 0x0184
LB_SETSEL = 0x0185
LB_SETCURSEL = 0x0186
LB_GETSEL = 0x0187
LB_GETCURSEL = 0x0188
LB_GETTEXT = 0x0189
LB_GETTEXTLEN = 0x018A
LB_GETCOUNT = 0x018B
LB_SELECTSTRING = 0x018C
LB_GETTOPINDEX = 0x018E
LB_FINDSTRING = 0x018F
LB_GETSELCOUNT = 0x0190
LB_GETSELITEMS = 0x0191
LB_SETTABSTOPS = 0x0192
LB_GETHORIZONTALEXTENT = 0x0193
LB_SETHORIZONTALEXTENT = 0x0194
LB_SETCOLUMNWIDTH = 0x0195
LB_SETTOPINDEX = 0x0197
LB_GETITEMRECT = 0x0198
LB_GETITEMDATA = 0x0199
LB_SETITEMDATA = 0x019A
LB_SELITEMRANGE = 0x019B
LB_SETANCHORINDEX = 0x019C
LB_GETANCHORINDEX = 0x019D
LB_SETCARETINDEX = 0x019E
LB_GETCARETINDEX = 0x019F
LB_SETITEMHEIGHT = 0x01A0
LB_GETITEMHEIGHT = 0x01A1
LB_FINDSTRINGEXACT = 0x01A2
LB_SETLOCALE = 0x01A5
LB_GETLOCALE = 0x01A6
LB_INITSTORAGE = 0x01A8
LB_ITEMFROMPOINT = 0x01A9
LB_RESERVED0x01C0 = 0x01C0
LB_RESERVED0x01C1 = 0x01C1
LB_MSGMAX = 0x01C9
LB_MSGMAX = 0x01A8
LBS_NOTIFY = 0x0001L
LBS_SORT = 0x0002L
LBS_NOREDRAW = 0x0004L
LBS_MULTIPLESEL = 0x0008L
LBS_HASSTRINGS = 0x0040L
LBS_USETABSTOPS = 0x0080L
LBS_NOINTEGRALHEIGHT = 0x0100L
LBS_MULTICOLUMN = 0x0200L
LBS_WANTKEYBOARDINPUT = 0x0400L
LBS_EXTENDEDSEL = 0x0800L
LBS_DISABLENOSCROLL = 0x1000L
LBS_NODATA = 0x2000L
LBS_NOSEL = 0x4000L
LBS_STANDARD = (LBS_NOTIFY | LBS_SORT | WS_VSCROLL | WS_BORDER)
LBS_EX_CONSTSTRINGDATA = 0x00000002L

LVM_DELETECOLUMN = (LVM_FIRST + 28) 

CB_OKAY = 0
CB_ERR = (-1)
CB_ERRSPACE = (-2)
CBN_ERRSPACE = (-1)
CBN_SELCHANGE = 1
CBN_DBLCLK = 2
CBN_SETFOCUS = 3
CBN_KILLFOCUS = 4
CBN_EDITCHANGE = 5
CBN_EDITUPDATE = 6
CBN_DROPDOWN = 7
CBN_CLOSEUP = 8
CBN_SELENDOK = 9
CBN_SELENDCANCEL = 10
CBS_DROPDOWN = 0x0002L
CBS_DROPDOWNLIST = 0x0003L
CBS_AUTOHSCROLL = 0x0040L
CBS_OEMCONVERT = 0x0080L
CBS_SORT = 0x0100L
CBS_HASSTRINGS = 0x0200L
CBS_NOINTEGRALHEIGHT = 0x0400L
CBS_DISABLENOSCROLL = 0x0800L
CBS_UPPERCASE = 0x2000L
CBS_LOWERCASE = 0x4000L
CBS_EX_CONSTSTRINGDATA = 0x00000002L
CB_GETEDITSEL = 0x0140
CB_LIMITTEXT = 0x0141
CB_SETEDITSEL = 0x0142
CB_ADDSTRING = 0x0143
CB_DELETESTRING = 0x0144
CB_GETCOUNT = 0x0146
CB_GETCURSEL = 0x0147
CB_GETLBTEXT = 0x0148
CB_GETLBTEXTLEN = 0x0149
CB_INSERTSTRING = 0x014A
CB_RESETCONTENT = 0x014B
CB_FINDSTRING = 0x014C
CB_SELECTSTRING = 0x014D
CB_SETCURSEL = 0x014E
CB_SHOWDROPDOWN = 0x014F
CB_GETITEMDATA = 0x0150
CB_SETITEMDATA = 0x0151
CB_GETDROPPEDCONTROLRECT = 0x0152
CB_SETITEMHEIGHT = 0x0153
CB_GETITEMHEIGHT = 0x0154
CB_SETEXTENDEDUI = 0x0155
CB_GETEXTENDEDUI = 0x0156
CB_GETDROPPEDSTATE = 0x0157
CB_FINDSTRINGEXACT = 0x0158
CB_SETLOCALE = 0x0159
CB_GETLOCALE = 0x015A
CB_GETTOPINDEX = 0x015b
CB_SETTOPINDEX = 0x015c
CB_GETHORIZONTALEXTENT = 0x015d
CB_SETHORIZONTALEXTENT = 0x015e
CB_GETDROPPEDWIDTH = 0x015f
CB_SETDROPPEDWIDTH = 0x0160
CB_INITSTORAGE = 0x0161
CB_GETCOMBOBOXINFO = 0x0162
CB_MSGMAX = 0x0163
CB_MSGMAX = 0x015B

LVCFMT_LEFT = 0x0000
LVCFMT_RIGHT = 0x0001
LVCFMT_CENTER = 0x0002

LVS_SINGLESEL = 0x0004
LVM_DELETEITEM = (LVM_FIRST + 8)
LVM_ENSUREVISIBLE = (LVM_FIRST + 19)
LVN_ITEMACTIVATE = LVN_FIRST - 14

TVGN_PARENT = 0x3
TVGN_PREVIOUS = 0x2

TBS_HORZ = 0x0
TBS_VERT = 0x2

COMCTL32_VERSION = 0x020c
CCM_FIRST = 0x2000
CCM_SETVERSION = CCM_FIRST+0x7
CCM_GETVERSION = CCM_FIRST+0x8
TCS_BOTTOM = 0x2 


UDS_SETBUDDYINT = 2
UDM_SETBUDDY = WM_USER + 105
UDM_GETBUDDY = WM_USER + 106
UDM_SETRANGE32 = WM_USER + 111
UDM_GETRANGE32 = WM_USER + 112
UDM_SETPOS32 = WM_USER + 113
UDM_GETPOS32 = WM_USER + 114

UDN_DELTAPOS = 4294966574

########NEW FILE########
__FILENAME__ = api
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

#from core import schedule, GuiObject, Event, SizeEvent,\

#    CommandEvent, NotificationEvent, StylusEvent, KeyEvent,

from core import *
from ce import *
from menu import *
from controls import *
from html import *
from sizer import *
from boxing import HBox, VBox, TBox, Spacer
from font import *
from dialog import Dialog
from message import Message
from filedlg import FileDialog
from date import Date, Time
from spin import Spin
from toolbar import ToolBar
from line import HLine, VLine 
from dialoghdr import DialogHeader
from imagelist import ImageList

########NEW FILE########
__FILENAME__ = boxing
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from config import HIRES, HIRES_MULT

class _Wrapper:
    def __init__(self, wrapped, border):
 
        self.wrapped = wrapped
        if HIRES :

            border = tuple(2*val for val in border)
        self.border = border
        
    def size(self, l, t, r, b):
        border = self.border
        
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        w = r-l
        h = b-t
        self.wrapped.move(l, t, w, h)
        
    def get_best_size(self):
        visible = True
        try:
            visible = self.wrapped._visible
        except: pass
        
        if not visible:
            bx, by = 0, 0
        else:
            bx, by = self.wrapped.get_best_size()
        if bx is not None:
            if HIRES:
                bx += (self.border[0]+self.border[2])/2
            else:
                bx += self.border[0]+self.border[2]
        if by is not None:
            if HIRES:
                by += (self.border[1]+self.border[3])/2
            else:
                by += self.border[1]+self.border[3]
        return bx, by
        
class _Box:
    def __init__(self, border=(0,0,0,0), spacing=0):
        self._childs = []
        if HIRES :
            border = tuple(2*val for val in border)
            spacing *= 2
            
        self.border = border
        self.spacing = spacing
    
    def add(self, child, coeff=0, border=(0, 0, 0, 0)): 
        self._childs.append((_Wrapper(child, border), coeff))
        
    def addfixed(self, child, dim, border=(0,0,0,0)):
        self._childs.append((_Wrapper(child, border), -dim))
        
    def move(self, l, t, w, h):
        self.size(l, t, l+w, t+h)
        
class HBox(_Box):
    
    def size(self, l, t, r, b):
        fixed_size = 0
        total_coeff= 0
        childs = []
        for child, coeff in self._childs:
            bx, by = child.get_best_size()
            if HIRES:
                if bx is not None:
                    bx *= 2
                if by is not None:
                    by *= 2
                    
            if coeff == 0:
                if bx is None:
                    total_coeff += 1
                    childs.append((child, 1, 1, by))
                    continue
                
                fixed_size += bx
                childs.append((child, bx, 0, by))
            elif coeff >0:
                total_coeff += coeff
                childs.append((child, coeff, 1, by))
            else:
                if HIRES:
                    coeff *= 2
                fixed_size -= coeff
                childs.append((child, -coeff, 0, by))
        border = self.border    
        
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        sizerw = r - l
        sizerh = b - t
        hoffset = l
        voffset = t
        fixed_size += self.spacing * (len(childs)-1)
         
        first = True
        for child, coeff, expand, by in childs:
            if not first:
                hoffset += self.spacing
            if expand :
                w = (sizerw - fixed_size) * coeff / total_coeff
            else :
                w = coeff
#            if by is None:
            h = sizerh
            dy = 0
#            else:

#                h = by

#                dy = (sizerh - by) / 2
                
            child.size(hoffset, voffset+dy, hoffset+w, voffset+dy+h)
            hoffset += w
            first = False
        
    def get_best_size(self):
        b_x = 0
        b_y = 0
        h_expand = False
        v_expand = False
        for child, coeff in self._childs:
            if h_expand and v_expand:
                break
                
            if coeff:
                h_expand = True
                
            cx, cy =  child.get_best_size()
            if cx is None:
                h_expand = True
            else:
                b_x += cx
            if cy is None:
                v_expand = True
            else:
                if cy > b_y:
                    b_y = cy
        
                    
        if h_expand:
            b_x = None
        else:
            b_x += (self.border[0]+self.border[2])/HIRES_MULT
            if len(self._childs) > 1:
                b_x += self.spacing * (len(self._childs)-1) / HIRES_MULT
        if v_expand:
            b_y = None 
        else:
            b_y += (self.border[1]+self.border[3])/HIRES_MULT
        return b_x, b_y
        
class VBox(_Box):
    
    def size(self, l, t, r, b):
        fixed_size = 0
        total_coeff= 0
        childs = []
        for child, coeff in self._childs:
            if coeff==0:
                by = child.get_best_size()[1]
                if by is None:
                    total_coeff += 1
                    childs.append((child, 1, 1))
                    continue
                if HIRES:
                    by *= 2
                fixed_size += by
                childs.append((child, by, 0))
            elif coeff > 0:
                total_coeff += coeff
                childs.append((child, coeff, 1))
            else:
                if HIRES:
                    coeff *= 2
                fixed_size -= coeff
                childs.append((child, -coeff, 0))
        
        border = self.border    
           
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        sizerw = r - l
        sizerh = b - t
        hoffset = l
        voffset = t
        fixed_size += self.spacing * (len(childs)-1)
        
        first = True
        for child, coeff, expand in childs:
            if not first:
                voffset += self.spacing
            w = sizerw
            if expand > 0 :
                h = (sizerh - fixed_size) * coeff / total_coeff
            else : 
                h = coeff
            child.size(hoffset, voffset, hoffset+w, voffset+h)
            voffset += h
            first = False
            
    def get_best_size(self):
        b_x = 0
        b_y = 0
        h_expand = False
        v_expand = False
        for child, coeff in self._childs:
            if h_expand and v_expand:
                break
                
            if coeff:
                v_expand = True
                
            cx, cy =  child.get_best_size()
            if cx is None:
                h_expand = True
            else:
                if cx > b_x:
                    b_x = cx
            if cy is None:
                v_expand = True
            else:
                b_y += cy
   
        if h_expand:
            b_x = None
        else:
            b_x += (self.border[0]+self.border[2])/HIRES_MULT
        if v_expand:
            b_y = None 
        else:
            b_y += (self.border[1]+self.border[3])/HIRES_MULT
            if len(self._childs) > 1:
                b_y += self.spacing * (len(self._childs)-1) / HIRES_MULT
        return b_x, b_y
        
class TBox:
    def __init__(self, rows, cols, border=(0,0,0,0),
                 spacing_x=0, spacing_y=0,
                 rows_expanded=[], cols_expanded=[]):
        self._rows = rows
        self._cols = cols
        self._childs = []
        self.border = border
        self._spacing_x = spacing_x# * HIRES_MULT
        self._spacing_y = spacing_y# * HIRES_MULT
        self.rows_expanded = set(rows_expanded)
        self.cols_expanded = set(cols_expanded)
        
    def add(self, child, border=(0,0,0,0)):
        self._childs.append(_Wrapper(child, border))
        
    def get_best_size(self):
        rows_widths = [0]*self._rows
        cols_widths = [0]*self._cols
        expand_x = bool(self.cols_expanded)
        expand_y = bool(self.rows_expanded)
        
        for n, child in enumerate(self._childs):
            i, j = n%self._cols, n/self._cols
            
            b_x, b_y = child.get_best_size()
            
            if expand_x:
                pass
            elif b_x is not None:
                if b_x > cols_widths[i]:
                    cols_widths[i] = b_x
            else: 
                expand_x = True
            
            if expand_y:
                pass
            elif b_y is not None:
                if b_y > rows_widths[j]:
                    rows_widths[j] = b_y 
            else:
                expand_y = True    
        if expand_x:
            b_x = None
        else:
            b_x = sum(cols_widths)# * HIRES_MULT
            b_x += self._spacing_x * (self._cols-1)
            b_x += self.border[0]+self.border[2]
        if expand_y:
            b_y = None
        else:
            b_y = sum(rows_widths)# * HIRES_MULT
            b_y += self._spacing_y * (self._rows-1)
            b_y += self.border[1]+self.border[3]
        return b_x, b_y
        
    def size(self, l, t, r, b):
#        rows_widths = [0]*self._rows

#        cols_widths = [0]*self._cols
        rows_expanded = self.rows_expanded  #set()
        cols_expanded = self.cols_expanded#set()
        rows_widths = [None if (i in rows_expanded) else 0 for i in xrange(self._rows)]
        cols_widths = [None if (i in cols_expanded) else 0 for i in xrange(self._cols)]
        for n, child in enumerate(self._childs):
            i, j = n%self._cols, n/self._cols
            b_x, b_y = child.get_best_size()
            
            if cols_widths[i] is None:

                pass
#            if i in cols_expanded:

#                cols_widths[i] = None
            elif b_x is None:
                cols_expanded.add(i)
                cols_widths[i] = None
            elif cols_widths[i] < b_x * HIRES_MULT:
                cols_widths[i] = b_x * HIRES_MULT
            
            if rows_widths[j] is None:

                pass    
#            if j in rows_expanded:

#                pass
            if b_y is None:
                rows_expanded.add(j)
                rows_widths[j] = None
            elif rows_widths[j] < b_y * HIRES_MULT:
                rows_widths[j] = b_y * HIRES_MULT
        
        r_fixed_size = sum(width for width in rows_widths if width is not None)
        c_fixed_size = sum(width for width in cols_widths if width is not None)
        r_fixed_size += self._spacing_y * (self._rows-1) * HIRES_MULT
        c_fixed_size += self._spacing_x * (self._cols-1) * HIRES_MULT
        
        border = self.border    
        if HIRES :

            border = tuple(2*val for val in border)
                
        l += border[0]
        t += border[1]
        r -= border[2]
        b -= border[3]
        
        n_rows_expanded = len(rows_expanded)
        n_cols_expanded = len(cols_expanded)
        if n_rows_expanded:
            h_rows_ex = (b-t-r_fixed_size)/n_rows_expanded 
        if n_cols_expanded:
            w_cols_ex = (r-l-c_fixed_size)/n_cols_expanded
        hoffset = l
        voffset = t
        first_child = True
        for n, child in enumerate(self._childs):
            i, j = n%self._cols, n/self._cols
            
            if not first_child:
                if i == 0:
                    hoffset = l
                    voffset += rows_widths[j-1]
                    voffset += self._spacing_y * HIRES_MULT   
            if i in cols_expanded:
                col_width = w_cols_ex
            else:
                col_width = cols_widths[i]
            if j in rows_expanded:
                row_width = h_rows_ex
            else:
                row_width = rows_widths[j]
            
            child.size(hoffset, voffset, hoffset+col_width, voffset+row_width)  
            hoffset += col_width + self._spacing_x * HIRES_MULT
            first_child = False
            
    def move(self, l, t, w, h):
        self.size(l, t, l+w, t+h)
        
class Spacer:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y
        
    def move(self, l, t, w, h):
        pass
        
    def get_best_size(self):
        return self.x, self.y

########NEW FILE########
__FILENAME__ = ce
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from core import *
from config import HIRES_MULT
from controls import Label, Button
from menu import Menu, PopupMenu, MenuWrapper
from boxing import HBox, VBox, Spacer
#from toolbar import ToolBar

class SIPPref:
    '''
    A hidden Window that automatically
    controls the Software Input Panel
    according to the control focused in
    the parent window.
    
    It should be instancied after all
    other controls in the parent window
    '''
    def __init__(self, parent):
        pass
    
def make_sippref(parent):
    CreateWindowEx(0, u"SIPPREF", u"", WS_CHILD, -10, -10, 5, 5, parent._w32_hWnd, IdGenerator.next(), GetModuleHandle(0), 0)
    
class CommandBarItem(GuiObject):
    '''\
    Not implemented yet, will be used for managing the main menubar 
    aka command bar
    '''
    def __init__(self, cb_hWnd, index):
        self.cb_hWnd = cb_hWnd
        self.index = index
        
    def set_text(self, txt):
        tbbi = TBBUTTONINFO()
        tbbi.cbSize = sizeof(tbbi)
        tbbi.dwMask = TBIF_TEXT | 0x80000000
        tbbi.pszText = unicode(txt)
        SendMessage(self.cb_hWnd, WM_USER+64, self.index, byref(tbbi))
    
    def enable(self, val=True):
        tbbi = TBBUTTONINFO()
        tbbi.cbSize = sizeof(tbbi)
        tbbi.dwMask = TBIF_STATE | 0x80000000
        if val:
            tbbi.fsState = TBSTATE_ENABLED
        else:
            tbbi.fsState = TBSTATE_INDETERMINATE
        SendMessage(self.cb_hWnd, WM_USER+64, self.index, byref(tbbi))
    
        
    def disable(self):
        self.enable(False)
        
##class CommandBarAction(CommandBarItem):
##    '''\
##    Not implemented yet, will be used for managing the main menubar 
##    aka command bar
##    '''
##    def __init__(self, cb_hWnd, index, menu_item):
##        CommandBarItem.__init__(self, cb_hWnd, index)
##        self.menu_item = menu_item
##    
##    def bind(self, cb):
##        self.menu_item.bind(cb)   
##        
##class CommandBarMenu(CommandBarItem, MenuWrapper):
##    '''\
##    Not implemented yet, will be used for managing the main menubar 
##    aka command bar
##    '''
##    def __init__(self, cb_hWnd, index, hMenu):
##        CommandBarItem.__init__(self, cb_hWnd, index)
##        MenuWrapper.__init__(self, hMenu)

class CommandBarAction(Button):
    def __init__(self, parent, name, action):
        Button.__init__(self, parent, name, action)

    def bind(self, clicked=None, **kw):
        Button.bind(self, clicked=clicked, **kw)
        
class CommandBarMenuWrapper(Button):
    def __init__(self, parent, title, menu=None):
        Button.__init__(self, parent, title, action=self.on_click)
        self.menu = menu
        
    def on_click(self, ev):
        x, y = self.parent.pos
        dx, dy = self.pos
        self.menu.popup(self, x+dx, y+dy)
    

class CeFrame(Frame):
    '''\
    CeFrame is a frame designed to be a Windows CE compliant window.
    A CeFrame will track the SIP position and size and will automatically
    resize itself to always fit the screen.
    '''
    _dispatchers = {"_activate" : (MSGEventDispatcher, WM_ACTIVATE),
                    "_settingchanged" : (MSGEventDispatcher, WM_SETTINGCHANGE),
                    }
    _dispatchers.update(Frame._dispatchers)

    _w32_window_style = WS_OVERLAPPED
    
    def __init__(self, parent=None, title="PocketPyGui", action=None, menu=None, tab_traversal=True, visible=True, enabled=True, has_sip=True, has_toolbar=False):
        '''\
        Arguments :
            - parent: the parent window of this CeFrame.
            - title: the title as appearing in the title bar.
            - action : a tuple ('Label', callback) .
            - menu : the title of the right menu as a string
                     if not None, the menu can be filled via the cb_menu attribute
                     after CeFrame initialization.
        '''
        Frame.__init__(self, parent, title, tab_traversal=tab_traversal, visible=visible, enabled=enabled, pos=(-1,-1,240, 320))
        self.title_label = Label(self, title=title)

##        if has_ok:
##            self.top_right_button = gui.Button(self, 'Ok', action=lambda ev: self.onok())
##        else:
        self._create_tr_button()

        if action is None:
            self.cb_action = Spacer(0, 0)#Button(self)
        else:
            name, callback = action
            self.cb_action = CommandBarAction(self, name, action=callback)

        self.cb_menu = PopupMenu()
        if menu is None:
            self._cb_menu = Spacer(0, 0)
        else:
            self._cb_menu = CommandBarMenuWrapper(self, menu, self.cb_menu)

        hbox = HBox()
        hbox.add(self.title_label, 1)
        hbox.add(self.top_right_button)

        hbox2 = HBox()
        hbox2.add(self.cb_action, 1)
        hbox2.add(self._cb_menu, 1)
        
        vbox = VBox()
        vbox.add(hbox)
        vbox.add(Spacer())
        vbox.add(hbox2)
        

        self._sizer = vbox
        self.layout()
        InvalidateRect(self._w32_hWnd, 0, 0)

    def _create_tr_button(self):
        self.top_right_button = Button(self, 'X', action=lambda ev: self.close())

    def set_sizer(self, sizer):
        hbox = HBox()
        hbox.add(self.title_label, 1)
        hbox.add(self.top_right_button)

        hbox2 = HBox()
        hbox2.add(self.cb_action, 1)
        hbox2.add(self._cb_menu, 1)
        
        vbox = VBox()
        vbox.add(hbox)
        vbox.add(sizer, 1)
        vbox.add(hbox2)
        

        self._sizer = vbox
        self.layout()
        InvalidateRect(self._w32_hWnd, 0, 0)
        
    def onok(self):
        pass
    
    def show_sipbutton(self, show=True):
        if show:
            SHFullScreen(self._w32_hWnd, SHFS_SHOWSIPBUTTON)
        else:
            SHFullScreen(self._w32_hWnd, SHFS_HIDESIPBUTTON)
        
    def hide_sipbutton(self):
        self.show_sipbutton(False)

########NEW FILE########
__FILENAME__ = config
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

HIRES = False
HIRES_MULT = 1

########NEW FILE########
__FILENAME__ = controls
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from core import *
from w32comctl import *
from config import HIRES_MULT
from boxing import VBox

__doc__ = '''\
This module contains the core high-level widgets of ppygui.
See also ppygui.html for the HTML control.
'''

class Label(Control):
    '''\
    The Label control displays a static text.
    Events:
        - clicked -> CommandEvent
    '''
    _w32_window_class = "STATIC"
    _w32_window_style = WS_CHILD 
    _dispatchers = {'clicked' : (CMDEventDispatcher, ),
                    }
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, title="", align="left", border=False, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''\
        Arguments:
            - parent: the parent window.
            - title: the text to be displayed.
            - align: the text alignment in its window, can be "left", "center" or "right".
            - border: a boolean that determines if this control should have a border.
        '''
        if align not in ["left", "center", "right"]:
            raise ValueError, 'align not in ["left", "center", "right"]'
            
        orStyle = SS_NOTIFY
        if align == "center":
            orStyle |= SS_CENTER
        elif align == "right":
            orStyle |= SS_RIGHT
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, title, border, visible, enabled, pos, tab_stop=False,  **kw)
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text or '|'
        cx, cy = GetTextExtent(dc, text)
        cy = cy*(1+text.count('\n'))
        return 5+cx/HIRES_MULT, 6+cy/HIRES_MULT
        
class Button(Control):
    '''\
    The button control displays a command button,
    it can be a push button, a default button, or
    a check box.
    For a radio button see the RadioButton class
    Events :
        - clicked -> CommandEvent
    '''
    
    _w32_window_class = "BUTTON"
    _w32_window_style = WS_CHILD
    _dispatchers = {'clicked' : (CMDEventDispatcher, )}
    _dispatchers.update(Control._dispatchers)
    _defaultfont = ButtonDefaultFont
    
    def __init__(self, parent, title="", action=None, align="center", style="normal", border=False, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''
        Arguments:
            - title: the text of the button.
            - action: the callback called when the button is clicked (equivalent to button.bind(clicked=callback))
            - align: the text alignment, can be "left", "center" or "right".
            - style:
                - "normal" for a classic push button
                - "default" for a default push button
                - "check" for a check box
            - border: a boolean that determines if this control should have a border.
        '''
        if align not in ["left", "center", "right"]:
            raise ValueError, 'align not in ["left", "center", "right"]'
        if style not in ["normal", "default", "check", "radio"]:
            raise ValueError, 'style not in ["normal", "default", "check", "radio"]'
        orStyle = 0
        self._check = False
        if style == "normal" :
            orStyle |= BS_PUSHBUTTON
        elif style == "default" :
            orStyle |= BS_DEFPUSHBUTTON
        elif style == "check" :
            orStyle |= BS_AUTOCHECKBOX
            self._defaultfont = DefaultFont
            self._check = True
        elif style == "radio" :
            orStyle |= BS_RADIOBUTTON
            self._defaultfont = DefaultFont
        if align == "left":
            orStyle |= BS_LEFT
        elif align == "right":
            orStyle |= BS_RIGHT
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, title, border, visible, enabled, pos, **kw)
        
        if action is not None:
            self.bind(clicked=action)
        
        self._best_size = None
            
    def get_checked(self):
        '''\
        getter for property checked
        '''
        check = self._send_w32_msg(BM_GETCHECK)
        if check == BST_CHECKED :
            return True
        return False
        
    def set_checked(self, check):
        '''\
        setter for property checked
        '''
        if check :
            w32_check = BST_CHECKED
        else :
            w32_check = BST_UNCHECKED
        self._send_w32_msg(BM_SETCHECK, w32_check)
        
    doc_checked = "Returns or set the checked state of a button as a boolean (makes only sense for a button created with check or radio style)"
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, self.text)
        if self._check:
            return 20+cx/HIRES_MULT, 4+cy/HIRES_MULT
        return 10+cx/HIRES_MULT, 10+cy/HIRES_MULT
        

class RadioButton(Button):
    '''
    The RadioButton control displays a classic radio button,
    it belongs to a RadioGroup, which owns mutually exclusive radio buttons,
    and is bound to a value (any python object) that is useful for retrieving in
    the radio group.
    '''
    def __init__(self, parent, title="", align="center", group=None, value=None, border=False, visible=True, enabled=True, selected=False, pos=(-1,-1,-1,-1), **kw):
        '''
        Arguments:
            - title: the text of the button.
            - action: the callback called when the button is clicked (equivalent to button.bind(clicked=callback))
            - align: the text alignment, can be "left", "center" or "right".
            - group: the group of the radio as a RadioGroup instance or None.
            - value: any python object bound to the RadioButton
            - border: a boolean that determines if this control should have a border.
        '''
        Button.__init__(self, parent, title=title, style="radio", action=None, align=align, pos=pos, border=border, visible=visible, enabled=enabled, **kw)
        
        if group is not None:
            if not isinstance(group, RadioGroup):
                raise TypeError("arg group must be a RadioGroup instance or None")
            group._add(self)
            if selected:
                group.selection = self
        self._value = value
    
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        
        font = self._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, self.text)
        return 20 + cx/HIRES_MULT, 4+cy/HIRES_MULT
            
class RadioGroup(GuiObject):
    '''\
    Represents a group of mutually exclusive RadioButton
    Events:
        - update -> NoneType: sent when one of the radio buttons is clicked.
    '''
    
    def __init__(self):
        self._radios = []
        self.updatecb = None
        self._selection = None
        
    def bind(self, update=None):
        self.updatecb = update
        
    def _add(self, button):
        assert isinstance(button, RadioButton)
        self._radios.append(button)
        button.bind(clicked=self._onbuttonclicked)
        
    def get_selection(self):
        '''\
        getter for property selection
        '''
        return self._selection
        
    def set_selection(self, button):
        '''\
        setter for property selection
        '''
        assert button in self._radios #Fixme: raise ValueError instead of assertions
        for radio in self._radios :
            if button is radio :
                radio.checked = True
                self._selection = button
            else :
                radio.checked = False
    
    doc_selection = '''\
    The current selected radio as a Button instance, 
    if the button does not belong to this group it is an error"
    '''  
        
    def get_value(self):
        '''\
        getter for property value
        '''
        if self._selection is not None :
            return self._selection._value
            
    doc_value = "The value of the selected radio button"
        
    def _onbuttonclicked(self, event):
        button = event.window
        self.selection = button
        if self.updatecb is not None:
            self.updatecb(None)
            
class Edit(Control):
    '''\
    The edit control displays an editable text field. 
    Supported events :
        - update -> CommandEvent: sent when the text is updated by the user
    '''
    _w32_window_class = "EDIT"
    _w32_window_style = WS_CHILD
    _dispatchers = {'enter' : (CustomEventDispatcher,),
                    'update' : (CMDEventDispatcher, EN_UPDATE)}
    _dispatchers.update(Control._dispatchers)
    
    
    def __init__(self, parent, text="", align="left", style="normal", password=False, multiline = False, line_wrap=False, readonly=False, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''\
        Arguments:
            - parent : the parent window
            - text : the initial text to display
            - align : the text alignment, can be "left", "center" or "right"
            - style :
                - normal : standard text field
                - number : accept numeric input only
            - password : a boolean that determines if the user input should be masked
            - multiline : a boolean that determines if the text should contain newlines
            - readonly : a boolean that determines if the text should be viewed only
            - border: a boolean that determines if this control should have a border.
        '''
        assert align in ["left", "center", "right"] #Fixme: raise ValueError instead of assertions
        assert style in ["normal", "number"] #idem
        #orStyle = ES_AUTOHSCROLL 
        orStyle = 0
        if style == "number" :
            orStyle |= ES_NUMBER
        if align == "center":
            orStyle |= ES_CENTER
        elif align == "left" :
            orStyle |= ES_LEFT
        elif align == "right":
            orStyle |= ES_RIGHT

        if password :
            orStyle |= ES_PASSWORD
        if multiline :
            self._multiline = True
            orStyle |= WS_VSCROLL | ES_AUTOVSCROLL | ES_MULTILINE | ES_WANTRETURN
            if not line_wrap:
                orStyle |= WS_HSCROLL
        else:
            self._multiline = False
            orStyle |= ES_AUTOHSCROLL
                
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, text, border, visible, enabled, pos)
        self.set(readonly=readonly, **kw)
        self._best_size = None
        
    def _get_best_size(self):
        if self._multiline:
            return None, None
        
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text or '|'
        cx, cy = GetTextExtent(dc, text)
        return None, 7+cy/HIRES_MULT
        
    def get_readonly(self):
        '''\
        getter for property readonly
        '''
        style = GetWindowLong(self._w32_hWnd, GWL_STYLE)
        return bool(style & ES_READONLY)
        
    def set_readonly(self, val):
        '''\
        setter for property readonly
        '''
        self._send_w32_msg(EM_SETREADONLY, int(val))
    
    doc_readonly = "The read-only state of the edit as a boolean"
    
    def get_selection(self):
        '''\
        getter for property selection
        '''
        start = LONG()
        stop = LONG()
        self._send_w32_msg(EM_GETSEL, byref(start), byref(stop))
        return start.value, stop.value 
        
    def set_selection(self, val):
        '''\
        setter for property selection
        '''
        start, stop = val
        self._send_w32_msg(EM_SETSEL, start, stop)
    
    doc_selection = "The zero-based index selection as a tuple (start, stop)"

    def append(self, text):
        oldselect = self.selection
        n = self._send_w32_msg(WM_GETTEXTLENGTH)
        self.selection = n, n
        self.selected_text = text
        self.selection = oldselect
        
    def select_all(self):
        self.selection = 0, -1

    def get_modified(self):
        return bool(self._send_w32_msg(EM_GETMODIFY))
        
    def set_modified(self, mod):
        return self._send_w32_msg(EM_SETMODIFY, int(mod))

    def get_selected_text(self):
        txt = self.text
        start, end = self.selection
        return txt[start:end]
        
    def set_selected_text(self, txt):
        self._send_w32_msg(EM_REPLACESEL, 1, unicode(txt))
        
    def can_undo(self):
        '''\
        Return a bool that indicates if the current content can be undone
        '''
        return bool(self._send_w32_msg(EM_CANUNDO))
        
    def undo(self):
        '''\
        Undo the current content
        '''
        self._send_w32_msg(EM_UNDO)
        
    def cut(self):
        '''\
        Cut the current selection in the clipboard
        '''
        self._send_w32_msg(WM_CUT)
        
    def copy(self):
        '''\
        Copy the current selection in the clipboard
        '''
        self._send_w32_msg(WM_COPY)
    
    def paste(self):
        '''\
        Paste the content of the clipboard at the current position
        '''
        self._send_w32_msg(WM_PASTE)
    
    # Not tested    
    def line_from_char(self, i):
        return self._send_w32_msg(EM_LINEFROMCHAR, i)
        
    def line_index(self, i):
        return self._send_w32_msg(EM_LINEINDEX, i)
        
    def line_length(self, i):
        return self._send_w32_msg(EM_LINELENGTH, i)
  
class List(Control):
    '''
    The List control displays a list of choice
    Supported events :
    - choicechanged -> CommandEvent : sent when user selection has changed
    - choiceactivated -> CommandEvent : sent when the user double-click on a choice
    '''
    _w32_window_class = "ListBox"
    _w32_window_style = WS_CHILD | LBS_NOTIFY | WS_VSCROLL | LBS_HASSTRINGS
    _dispatchers = {'selchanged' : (CMDEventDispatcher, LBN_SELCHANGE),
                    'itemactivated' : (CMDEventDispatcher, LBN_DBLCLK)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, choices=[], sort=False, multiple=False, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''
        - choices : the initial possible choices as a list of string
        - sort : True if the choices have to be sorted in alphabetical order
        - multiple : True if the control should allow multiple selection
        ''' 
        orStyle = 0        
        self.multiple = multiple
        if sort :
            orStyle |= LBS_SORT
        if multiple :
            orStyle |= LBS_MULTIPLESEL
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, "", border, visible, enabled, pos)
        
        for choice in choices :
            self.append(choice)
    
        self.set(**kw)
        
    def get_count(self):
        '''
        Returns the number of choices in the control
        '''
        return self._send_w32_msg(LB_GETCOUNT)
        
    doc_count = "The number of choices in the control"
    
    def append(self, choice):
        '''
        Adds the string choice to the list of choices
        '''
        self._send_w32_msg(LB_ADDSTRING, 0, unicode(choice))
        
    def insert(self, i, choice):
        '''
        Inserts the string choice at index i
        '''
        self._send_w32_msg(LB_INSERTSTRING, i, unicode(choice))
           
    def __getitem__(self, i):
        '''
        Returns the choice at index i as a string
        '''
        if not 0<=i<self.count:
            raise IndexError
        textLength = self._send_w32_msg(LB_GETTEXTLEN, i)# + 1
        textBuff = create_unicode_buffer(textLength+1)
        self._send_w32_msg(LB_GETTEXT, i, textBuff)
        return textBuff.value
        
    def __setitem__(self, i, text):
        '''\
        Sets the choice at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
        del self[i]
        self.insert(i, text)
    
    def __delitem__(self, i):
        '''
        Removes the choice at index i
        '''
        self._send_w32_msg(LB_DELETESTRING, i)
        
    def delete_all(self):
        for i in range(self.count):
            del self[0]
            
    def is_multiple(self):
        '''
        Returns True if the Choice control allows 
        multiple selections
        '''
        return self.multiple
        
    def get_selection(self):
        '''
        Returns the current selection as an index or None in a single-choice
        control , or a list of index in a multiple-choice control
        '''  
        if not self.multiple :
            sel = self._send_w32_msg(LB_GETCURSEL)
            if sel >= 0 :
                return sel
        else :
            selections = []
            for i in range(self.count):
                if self._send_w32_msg(LB_GETSEL, i) > 0 :
                    selections.append(i)
            return selections
        
    def set_selection(self, selection):
        '''
        Sets the current selection as a list of index,
        In the case of a single-choice control, it accepts
        an index or will use the first index in the list
        ''' 
        try :
            len(selection)
        except TypeError :
            selection = [selection]
        if not self.multiple :
            return self._send_w32_msg(LB_SETCURSEL, selection[0])
        else :
            self._send_w32_msg(LB_SETSEL, 0, -1)
            for i in selection :
                self._send_w32_msg(LB_SETSEL, 1, i)
        
    doc_selection = "The current selection(s) as a list of index"
    
    def __iter__(self):
        return choiceiterator(self)
    
    
def choiceiterator(choice):
    for i in range(choice.count):
        yield choice[i]

class TableColumns(GuiObject):
    '''
    TableColumns instance are used to manipulate
    the columns of the bounded Table object
    '''
    def __init__(self, list, columns):
        '''
        Do not use this constructor directly
        it is instantiated automatically by Table
        '''
        self._list = list
        self._count = 0
        for title in columns :
            self.append(title)
            
    def __len__(self):
        return self._count
        
    def append(self, title, width=-1, align="left"):
        '''
        Adds a new column to the bounded table
        - title : the text of the column
        - width : the width of the column in pixels, -1 will set the width so that it contains the title
        - align : the alignment of the column, can be "left", "center" or "right"
        Returns the index of the newly created column
        '''
        i = len(self)
        return self.insert(i, title, width, align)

        
    def insert(self, i, title, width=-1, align="left"):
        '''
        Inserts a new column to the bounded table at index i
        - title : the text of the column
        - width : the width of the column in pixels, -1 will set the width so that it contains the title
        - align : the alignment of the column, can be "left", "center" or "right"
        Returns the index of the newly created column
        '''
        if not 0 <= i <= len(self):
            raise IndexError
        assert align in ["left", "center", "right"]
        col = LVCOLUMN()
        col.text = unicode(title)
        col.width = width
        if align == "left" :
            fmt = LVCFMT_LEFT
        elif align == "right" :
            fmt = LVCFMT_RIGHT
        elif align == "center" :
            fmt = LVCFMT_CENTER
            

        col.format = fmt
        self._list._insertcolumn(i, col)
        self._count += 1
        if width == -1 :
            self.adjust(i)
        return i
        
    def set(self, i, title=None, width=None, align=None):
        '''
        Sets the column of the bounded table at index i
        - title : the text of the column
        - width : the width of the column in px
        - align : the alignment of the column, can be "left", "center" or "right" (can produce artifacts)
        '''
        if not 0<=i<len(self):
            raise IndexError
        col = LVCOLUMN()
        if title is not None :
            col.text = title
        if width is not None :
            col.width = width
        if align is not None :
            assert align in ["left", "center", "right"]
            if align == "left" :
                fmt = LVCFMT_LEFT
            elif align == "right" :
                fmt = LVCFMT_RIGHT
            elif align == "center" :
                fmt = LVCFMT_CENTER
                

            col.format = fmt
        self._list._setcolumn(i, col)
        
    def adjust(self, i):
        '''
        Adjust the column width at index i
        to fit the header and all the texts in 
        this column.
        '''        
        if not 0<=i<len(self):
            raise IndexError
        self._list._send_w32_msg(LVM_SETCOLUMNWIDTH, i, -2)
            
    #def remove(self, column):
    #    pass
    def __delitem__(self, i):
        '''
        Removes the column at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._list._send_w32_msg(LVM_DELETECOLUMN, i)
        self._count -= 1
        
class TableRows(GuiObject):
    
    def __init__(self, list):
        '''
        Do not use this constructor directly,
        it is instantiated automatically by Table
        '''
        self._list = list
        self._data = []
    
    def __len__(self):
        return self._list._send_w32_msg(LVM_GETITEMCOUNT)
        
    def append(self, row, data=None):
        '''
        Adds a new row at the end of the list
        - row : a list of string
        - data : any python object that you want to link to the row
        '''
        self.insert(len(self), row, data)
        
    def insert(self, i, row, data=None):
        '''
        Inserts a new row at index i
        - row : a list of string
        - data : any python object that you want to link to the row
        '''
        if not 0<=i<=len(self):
            raise IndexError
        item = LVITEM()
        item.mask = LVIF_TEXT | LVIF_PARAM
        item.iItem = i
        #item.lParam = data
        item.iSubItem = 0
        item.pszText = row[0]
        self._list._insertitem(item)
        for iSubItem in range(len(row) - 1):
            item.mask = LVIF_TEXT
            item.iSubItem = iSubItem + 1
            item.pszText = row[iSubItem + 1]
            self._list._setitem(item)
        
        if i == len(self) - 1:
            self._data.append(data)
        else :
            self._data.insert(i, data)
        
    def __setitem__(self, i, row):
        '''
        Sets the row at index i as a list of string
        '''
        if not 0<=i<len(self):
            raise IndexError
        item = LVITEM()
        item.mask = LVIF_TEXT | LVIF_PARAM
        item.iItem = i
        #item.lParam = data
        item.iSubItem = 0
        item.pszText = row[0]
        self._list._setitem(item)
        for iSubItem in range(len(row) - 1):
            item.mask = LVIF_TEXT
            item.iSubItem = iSubItem + 1
            item.pszText = row[iSubItem + 1]
            self._list._setitem(item)
            
    def setdata(self, i, data):
        '''
        Bind any python object to the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._data[i] = data
        
    def __getitem__(self, i):
        '''
        Returns the row at index i as a list of string
        '''
        if not 0<=i<len(self):
            raise IndexError
        row = []
        for j in range(len(self._list.columns)):
            item = self._list._getitem(i, j)
            row.append(item.pszText)
            
        return row
        
    def getdata(self, i):
        '''
        Returns any python object that was bound to the row or None
        '''
        if not 0<=i<len(self):
            raise IndexError
        return self._data[i]
    
    #TODO: implement image api
    def getimage(self, i):
        pass
        
    def setimage(self, i, image_index):
        pass
        
    def getselected_image(self, i):
        pass
        
    def setselected_image(self, i, image_index):
        pass
    
    def ensure_visible(self, i):
        '''
        Ensures the row at index i is visible
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._send_w32_msg(LVM_ENSUREVISIBLE, i)
    
    def is_selected(self, i):
        '''
        Returns True if the row at index i is selected
        '''
        if not 0<=i<len(self):
            raise IndexError
            
        item = LVITEM()
        item.iItem = i
        item.mask = LVIF_STATE
        item.stateMask = LVIS_SELECTED
        self._list._send_w32_msg(LVM_GETITEM, 0, byref(item))
        return bool(item.state)
        
    def select(self, i):
        '''
        Selects the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        item = LVITEM()
        item.iItem = i
        item.mask = LVIF_STATE
        item.stateMask = LVIS_SELECTED
        item.state = 2
        self._list._send_w32_msg(LVM_SETITEM, 0, byref(item))
    
    def deselect(self, i):
        '''
        deselects the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        item = LVITEM()
        item.iItem = i
        item.mask = LVIF_STATE
        item.stateMask = LVIS_SELECTED
        item.state = 0
        self._list._send_w32_msg(LVM_SETITEM, 0, byref(item))
        
    def get_selection(self):
        '''
        Get the current selections as a list
        of index
        '''
        l = []
        i = -1
        list = self._list
        while 1:
            i = list._send_w32_msg(LVM_GETNEXTITEM, i, LVNI_SELECTED)
            if i != -1:
                l.append(i)
            else:
                break
        return l
        
    def get_selected_count(self):
        return self._list._send_w32_msg(LVM_GETSELECTEDCOUNT)
        
    doc_selected_count = "The number of rows selected as an int (read-only)"
    
    def set_selection(self, selections):
        '''
        Sets the current selections as a list
        of index
        '''
        try :
            len(selections)
        except TypeError:
            selections = [selections]
        for i in xrange(len(self)):
            self.unselect(i)
            
        for i in selections:
            self.select(i)
    
    doc_selection = "The current selection(s) as a list of index"
        
    def __delitem__(self, i):
        '''
        del list.rows[i] : removes the row at index i
        '''
        if not 0<=i<len(self):
            raise IndexError
        self._list._send_w32_msg(LVM_DELETEITEM, i) 
        del self._data[i]

class Combo(Control):
    _w32_window_class = "COMBOBOX"
    _w32_window_style = WS_CHILD | WS_VSCROLL #| CBS_AUTOHSCROLL | CBS_DISABLENOSCROLL
    _dispatchers = {'selchanged' : (CMDEventDispatcher, CBN_SELCHANGE)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, style="edit", sort=False, choices=[], visible=True, enabled=True, pos=(-1,)*4, **kw):
        assert style in ["edit", "list"]
        orStyle = 0
        if style == "edit":
            orStyle |=  CBS_DROPDOWN
        elif style == "list":
            orStyle |= CBS_DROPDOWNLIST
        if sort :
            orStyle |= CBS_SORT
                
        self._w32_window_style |= orStyle
        
        Control.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        for choice in choices :
            self.append(choice)
        self.set(**kw)
        self._best_size = None
        
    def move(self, l, t, w, h):
        Control.move(self, l, t, w, h+(HIRES_MULT*150))
        
    def get_count(self):
        return self._send_w32_msg(CB_GETCOUNT)
        
    def append(self, txt):
        self._send_w32_msg(CB_ADDSTRING, 0, unicode(txt))
        self._best_size = None
        
    def insert(self, i, txt):
        if not 0<=i<self.count:
            raise IndexError
        self._send_w32_msg(CB_INSERTSTRING, i, unicode(txt))
        self._best_size = None
        
    def get_selection(self):
        cursel = self._send_w32_msg(CB_GETCURSEL)
        if cursel != -1 :
            return cursel
            
    def set_selection(self, i):
        if i is None :
            self._send_w32_msg(CB_SETCURSEL, -1)
        else :
            if not 0<=i<self.count:
                raise IndexError
            self._send_w32_msg(CB_SETCURSEL, i)
        
    def drop_down(self, show=True):
        self._send_w32_msg(CB_SHOWDROPDOWN, int(show))
    
    def __getitem__(self, i):
        '''
        Returns the item at index i as a string
        '''
        if not 0<=i<self.count:
            raise IndexError
        textLength = self._send_w32_msg(CB_GETLBTEXTLEN, i)# + 1
        textBuff = create_unicode_buffer(textLength+1)
        self._send_w32_msg(CB_GETLBTEXT, i, textBuff)
        return textBuff.value
        
    def __setitem__(self, i, text):
        '''\
        Sets the choice at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
        del self[i]
        self.insert(i, text)
            
    def __delitem__(self, i):
        if not 0<=i<self.count:
            raise IndexError
        self._send_w32_msg(CB_DELETESTRING, i)    
        self._best_size = None
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, '')
        for i in range(self.count):
            current_cx, cy = GetTextExtent(dc, self[i])
            if current_cx > cx:
                cx = current_cx
        return cx/HIRES_MULT+20, 8+cy/HIRES_MULT

    def get_font(self):
        return Control.get_font(self)
            
    def set_font(self, value):
        Control.set_font(self, value)
        self._best_size = None
        
    def get_best_size(self):
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
            
class TableEvent(NotificationEvent):
    
    def __init__(self, hWnd, nMsg, wParam, lParam):
        NotificationEvent.__init__(self, hWnd, nMsg, wParam, lParam)
        nmlistview = NMLISTVIEW.from_address(lParam)
        self._index = nmlistview.iItem
        self._colindex = nmlistview.iSubItem
        self.new_state = nmlistview.uNewState
        self.changed = nmlistview.uChanged
        self.selected = bool(self.new_state)
        
    def get_index(self):
        return self._index
        
    def get_columnindex(self):
        return self._colindex
            
class TreeEvent(NotificationEvent):
    
    def __init__(self, hWnd, nMsg, wParam, lParam):
        NotificationEvent.__init__(self, hWnd, nMsg, wParam, lParam)
        self.nmtreeview = NMTREEVIEW.from_address(lParam)
        hwnd = self.nmtreeview.hdr.hwndFrom
        self._tree = hwndWindowMap[hwnd]
        
    def get_old_item(self):
        hItem = self.nmtreeview.itemOld.hItem
        if hItem != 0:
            return TreeItem(self._tree, hItem)
        
    def get_new_item(self):
        hItem = self.nmtreeview.itemNew.hItem
        if hItem != 0:
            return TreeItem(self._tree, hItem)
            
class Table(Control):
    '''
    The Table control :
    Columns are manipulated via the TableColumns instance variable columns
    Rows are manipulated via the TableRows instance variable rows
    You can get or set the text at row i, column j by indexing list[i, j] 
    '''
    _w32_window_class = WC_LISTVIEW
    _w32_window_style = WS_CHILD | LVS_REPORT #| LVS_EDITLABELS 

    _dispatchers = {"selchanged" : (NTFEventDispatcher, LVN_ITEMCHANGED, TableEvent),
                    "itemactivated" : (NTFEventDispatcher, LVN_ITEMACTIVATE, TableEvent),
                    }
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, columns=[], autoadjust=False, multiple=False, has_header=True, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), **kw):
        '''
        - columns : a list of title of the initial columns
        - autoadjust : whether the column width should be automatically adjusted
        - multiple : whether the table should allow multiple rows selection
        - has_header : whether the table displays a header for its columns
        '''
        if not multiple :
            self._w32_window_style |= LVS_SINGLESEL
        if not has_header:
            self._w32_window_style |= LVS_NOCOLUMNHEADER
        
        Control.__init__(self, parent, border=border, visible=visible, enabled=enabled, pos=pos)
        self._set_extended_style(LVS_EX_FULLROWSELECT|LVS_EX_HEADERDRAGDROP|0x10000)
        
        self.columns = TableColumns(self, columns)
        self.rows = TableRows(self)
        self._autoadjust = autoadjust
        
        self._multiple = multiple
        self.set(**kw)
        
    def _set_extended_style(self, ex_style):
        self._send_w32_msg(LVM_SETEXTENDEDLISTVIEWSTYLE, 0, ex_style)
    
    def is_multiple(self):
        return bool(self._multiple)
    
    def _insertcolumn(self, i, col):
        return self._send_w32_msg(LVM_INSERTCOLUMN, i, byref(col))

    def _setcolumn(self, i, col):
        return self._send_w32_msg(LVM_SETCOLUMN, i, byref(col))

    def _insertitem(self, item):
        self._send_w32_msg(LVM_INSERTITEM, 0, byref(item))
        if self._autoadjust:
            self.adjust_all() 
            
    def _setitem(self, item):
        self._send_w32_msg(LVM_SETITEM, 0, byref(item))
        if self._autoadjust:
            self.adjust_all() 
            
    def _getitem(self, i, j):
        item = LVITEM()
        item.mask = LVIF_TEXT | LVIF_PARAM
        item.iItem = i
        item.iSubItem = j
        item.pszText = u" "*1024

        item.cchTextMax = 1024
        self._send_w32_msg(LVM_GETITEM, 0, byref(item))
        return item
        
    def adjust_all(self):
        '''
        Adjusts all columns in the list
        '''
        for i in range(len(self.columns)):
            self.columns.adjust(i)
    
    def __getitem__(self, pos):
        '''
        list[i, j] -> Returns the text at the row i, column j
        '''
        i, j = pos
        if not 0 <= i < len(self.rows):
            raise IndexError
        if not 0 <= j < len(self.columns):
            raise IndexError
                
        item = self._getitem(i, j)
        return item.pszText
        
    def __setitem__(self, pos, val):
        '''
        list[i, j] = txt -> Set the text at the row i, column j to txt
        '''
        i, j = pos
        if not 0 <= i < len(self.rows):
            raise IndexError
        if not 0 <= j < len(self.columns):
            raise IndexError
        
        item = LVITEM()
        item.mask = LVIF_TEXT 
        item.iItem = i
        item.iSubItem = j
        item.pszText = unicode(val)
        self._setitem(item)
        return item
        
    def delete_all(self):
        '''
        Removes all rows of the list
        '''
        del self.rows._data[:]
        self._send_w32_msg(LVM_DELETEALLITEMS)
        if self._autoadjust:
            self.adjust_all() 

        


class TreeItem(GuiObject):
    
    def __init__(self, tree, hItem):
        '''
        Do not use this constructor directly.
        Use Tree and TreeItem methods instead.
        '''
        self._tree = tree
        self._hItem = hItem
        
    def __eq__(self, other):
        return (self._tree is other._tree) \
            and (self._hItem == other._hItem)
        
    def __len__(self):
        for i, item in enumerate(self): 
            pass
        try :
            return i+1
        except NameError:
            return 0
            
    
    def append(self, text, data=None, image=0, selected_image=0):
        '''
        Adds a child item to the TreeItem. 
        '''
        
        return self._tree._insertitem(self._hItem, TVI_LAST, text, data, image, selected_image)
    
    def insert(self, i, text, data=None, image=0, selected_image=0):
        
        if i < 0 :
            raise IndexError
            
        if i == 0:
            return self._tree._insertitem(self._hItem, TVI_FIRST, text, data, image, selected_image)
        hAfter = self[i-1]
        return self._tree._insertitem(self._hItem, hAfter, text, data, image, image_selected)
    
    def get_parent(self):
        parenthItem = self._tree._send_w32_msg(TVM_GETNEXTITEM, TVGN_PARENT, self._hItem)
        if parenthItem :
            return TreeItem(self._tree, parenthItem)
    
    def expand(self):
        self._tree._send_w32_msg(TVM_EXPAND, TVE_EXPAND, self._hItem)
    
    def collapse(self):
        self._tree._send_w32_msg(TVM_EXPAND, TVE_COLLAPSE, self._hItem)
        
    def toggle(self):
        self._tree._send_w32_msg(TVM_EXPAND, TVE_TOGGLE, self._hItem)
    
#    def isexpanded(self):

#        pass
        
    def select(self):
        self._tree._send_w32_msg(TVM_SELECTITEM, TVGN_CARET, self._hItem)
    
#    def isselected(self):

#        pass
        
    def ensure_visible(self):
        self._tree._send_w32_msg(TVM_ENSUREVISIBLE, 0, self._hItem)
         
    def __getitem__(self, i):
        if i < 0:
            raise IndexError
        for j, item in enumerate(self):
            if j==i :
                return item
        raise IndexError
        
    def get_text(self):
        item = TVITEM()
        item.hItem = self._hItem
        item.mask = TVIF_TEXT
        item.pszText = u" "*1024
        item.cchTextMax = 1024
        self._tree._getitem(item)
        return item.pszText
        
    def set_text(self, txt):
        item = TVITEM()
        item.mask  = TVIF_TEXT
        item.hItem = self._hItem
        item.pszText = unicode(txt)
        return self._tree._setitem(item)
        
    doc_text = "The text of the TreeItem as a string"
    
    def get_data(self):
        item = TVITEM()
        item.hItem = self._hItem
        item.mask  = TVIF_PARAM
        self._tree._getitem(item)
        return self._tree._data[item.lParam][0]
        
    def set_data(self, data):
        olddata = self.data
        self._tree._data.decref(olddata)
        param = self._tree._data.addref(data)
        item = TVITEM()
        item.hItem = self._hItem
        item.mask  = TVIF_PARAM
        item.lParam = param
        self._tree._setitem(item)
        
    doc_data = "The data of the TreeItem as any python object"
        
    def get_image(self):
        item = TVITEM()
        item.mask  = TVIF_IMAGE
        item.hItem = self._hItem
        self._tree._getitem(item)
        return item.iImage
        
    def set_image(self, i):
        item = TVITEM()
        item.mask  = TVIF_IMAGE
        item.hItem = self._hItem
        item.iImage = i
        self._tree._setitem(item)
        
    def get_selected_image(self):
        item = TVITEM()
        item.mask  = TVIF_SELECTEDIMAGE
        item.hItem = self._hItem
        self._tree._getitem(item)
        return item.iSelectedImage
        
    def set_selected_image(self, i):
        item = TVITEM()
        item.mask  = TVIF_SELECTEDIMAGE
        item.hItem = self._hItem
        item.iSelectedImage = i
        self._tree._setitem(item)
        
    def _removedata(self):
        data = self.data
        self._tree._data.decref(data)
        for child in self:
            child._removedata()
        
    def remove(self):
        '''
        Removes the TreeItem instance and all its children from its tree. 
        '''
        self._removedata()
        self._tree._send_w32_msg(TVM_DELETEITEM, 0, self._hItem)
    
    def __iter__(self):
        return _treeitemiterator(self) 
        
    def __delitem__(self, i):
        '''
        del item[i] -> removes the child at index i
        '''
        
        self[i].remove()

    
def _treeitemiterator(treeitem):
    hitem = treeitem._tree._send_w32_msg(TVM_GETNEXTITEM, TVGN_CHILD, treeitem._hItem)
    while hitem :
        yield TreeItem(treeitem._tree, hitem)
        hitem = treeitem._tree._send_w32_msg(TVM_GETNEXTITEM, TVGN_NEXT, hitem)
        
class _TreeDataHolder(dict):
    
    def addref(self, obj):
        idobj = id(obj)
        if idobj in self:
            objj, refs = self[idobj]
            assert objj is obj
            self[idobj] = obj, refs+1
        else :
            self[idobj] = (obj, 1)
        #print dict.__str__(self)
        return idobj
    
    def decref(self, obj):
        idobj = id(obj)
        if idobj in self:
            objj, refs = self[idobj]
            assert objj is obj
            refs -= 1 
            if refs == 0 :
                del self[idobj]
            else :
                self[idobj] = obj, refs
            
            
class Tree(Control):
    '''
    The tree control :
    Insert or get roots with the insertroot and getroots method
    Subsequent changes to the tree are made with the TreeItem instances
    '''
    _w32_window_class = WC_TREEVIEW
    _w32_window_style = WS_CHILD | WS_TABSTOP
                       
    _dispatchers = {"selchanged" : (NTFEventDispatcher, TVN_SELCHANGED, TreeEvent),
                    }
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, parent, border=True, visible=True, enabled=True, pos=(-1,-1,-1,-1), has_buttons=True, has_lines=True):
        or_style = 0
        if has_buttons:
            or_style |= TVS_HASBUTTONS
        if has_lines:
            or_style |= TVS_LINESATROOT|TVS_HASLINES
            
        self._w32_window_style |= or_style
        
        Control.__init__(self, parent, border=border, visible=visible, enabled=enabled, pos=pos)
        self._roots = []
        self._data = _TreeDataHolder()
        
    def _getitem(self, item):
        self._send_w32_msg(TVM_GETITEM, 0, byref(item))
        
    def _setitem(self, item):
        self._send_w32_msg(TVM_SETITEM, 0, byref(item))
        
    def _insertitem(self, hParent, hInsertAfter, text, data, image, image_selected):
        #item.mask = TVIF_TEXT | TVIF_PARAM
        item = TVITEM(text=text, param=self._data.addref(data), image=image, selectedImage=image_selected)
        #print 'param :', item.lParam
        insertStruct = TVINSERTSTRUCT()
        insertStruct.hParent = hParent
        insertStruct.hInsertAfter = hInsertAfter
        insertStruct.item = item
        hItem = self._send_w32_msg(TVM_INSERTITEM, 0, byref(insertStruct))
        return TreeItem(self, hItem)
            
    def add_root(self, text, data=None, image=0, selected_image=0):
        '''\
        Insert a new root in the tree
        - text : the text of the root
        - data : the data bound to the root
        Returns the TreeItem instance associated to the root
        '''

        
        root = self._insertitem(TVI_ROOT, TVI_ROOT, text, data, image, selected_image)
        self._roots.append(root)
        return root
    
    def get_roots(self):
        '''\
        Returns the list of roots in the tree
        '''  
        return self._roots

    def delete_all(self):
        '''\
        Deletes all items in the tree
        '''
        for root in self._roots:
            root.remove()
        self._roots = []
    
    def get_selection(self):
        '''\
        Returns a TreeItem instance bound
        to the current selection or None
        '''
        hItem = self._send_w32_msg(TVM_GETNEXTITEM, TVGN_CARET, 0)
        if hItem > 0:
            return TreeItem(self, hItem)
        
    def set_image_list(self, il):
        self._send_w32_msg(TVM_SETIMAGELIST, 0, il._hImageList)
        
class Progress(Control):
    _w32_window_class = PROGRESS_CLASS
    
    def __init__(self, parent, style="normal", orientation="horizontal", range=(0,100), visible=True, enabled=True, pos=(-1,-1,-1,-1)):
        if style not in ["normal", "smooth"]:
            raise ValueError('style not in ["normal", "smooth"]')
        if orientation not in ['horizontal', 'vertical']:
            raise ValueError("orientation not in ['horizontal', 'vertical']")
        
        self._orientation = orientation 
        orStyle = 0
        if style == "smooth" :
            orStyle |= PBS_SMOOTH
        if orientation == "vertical" :
            orStyle |= PBS_VERTICAL
        
        self._w32_window_style |= orStyle
        Control.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        self.range = range
            
    def set_range(self, range):
        nMinRange, nMaxRange = range
        if nMinRange > 65535 or nMaxRange > 65535:
            return self._send_w32_msg(PBM_SETRANGE32, nMinRange, nMaxRange)
        else:
            return self._send_w32_msg(PBM_SETRANGE, 0, MAKELPARAM(nMinRange, nMaxRange))
            
    def get_range(self):
        minrange = self._send_w32_msg(PBM_GETRANGE, 1)
        maxrange = self._send_w32_msg(PBM_GETRANGE, 0)
        return minrange, maxrange
    
    doc_range = "The range of the progress as a tuple (min, max)"
    
    def set_value(self, newpos):
        return self._send_w32_msg(PBM_SETPOS, newpos, 0)

    def get_value(self):
        return self._send_w32_msg(PBM_GETPOS, 0, 0)
    
    doc_value = "The position of the progress as an int"
    
    def get_best_size(self):
        if self._orientation == 'horizontal':
            return None, 20
        else:
            return 20, None
            
class ScrollEvent(Event):
    def __init__(self, hWnd, nMsg, wParam, lParam):
        Event.__init__(self, lParam, nMsg, wParam, lParam)

class Slider(Control):
    _w32_window_class = TRACKBAR_CLASS
    _w32_window_style = WS_CHILD | TBS_AUTOTICKS | TBS_TOOLTIPS

    _dispatchers = {"_hscroll" : (MSGEventDispatcher, WM_HSCROLL, ScrollEvent),
                    "_vscroll" : (MSGEventDispatcher, WM_VSCROLL, ScrollEvent),
                    "update" : (CustomEventDispatcher,)
                    }
    _dispatchers.update(Control._dispatchers)
                    
                        
    def __init__(self, parent, orientation="horizontal", value=0, range=(0,10), visible=True, enabled=True, pos=(-1,-1,-1,-1)):
        assert orientation in  ['horizontal', 'vertical']
        if orientation == 'horizontal' :
            self._w32_window_style |= TBS_HORZ
        else :
            self._w32_window_style |= TBS_VERT
        self._style = orientation
        Control.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        
        self.bind(_hscroll=self._on_hscroll, 
                  _vscroll=self._on_vscroll)
                  
        clsStyle = GetClassLong(self._w32_hWnd, GCL_STYLE)
        clsStyle &= ~CS_HREDRAW
        clsStyle &= ~CS_VREDRAW
        SetClassLong(self._w32_hWnd, GCL_STYLE, clsStyle)
        
        self.range = range
        self.value = value
    def _on_hscroll(self, ev):
        self.events['update'].call(ev)
        
    def _on_vscroll(self, ev):
        self.events['update'].call(ev)
        
    def get_range(self):
        min = self._send_w32_msg(TBM_GETRANGEMIN)
        max = self._send_w32_msg(TBM_GETRANGEMAX)
        return min, max
        
    def set_range(self, range):
        min, max = range
        self._send_w32_msg(TBM_SETRANGE, 0, MAKELPARAM(min, max))
    
    doc_range = "The range of the slider as a tuple (min, max)"
        
    def get_value(self):
        return self._send_w32_msg(TBM_GETPOS)
        
    def set_value(self, pos):
        self._send_w32_msg(TBM_SETPOS, 1, pos)
    
    doc_value = "The position of the slider as an int"
    
#    def get_pagesize(self):

#        pass

#        

#    def set_pagesize(self, size):

#        pass

    def get_best_size(self):
        if self._style == 'horizontal':
            return None, 25
        else:
            return 25, None


class _TabControl(Control):
    _w32_window_class = WC_TABCONTROL
    #_w32_window_style_ex = 0x10000
    _w32_window_style = WS_VISIBLE | WS_CHILD | TCS_BOTTOM | WS_CLIPSIBLINGS 
    _dispatchers = {"_selchanging" : (NTFEventDispatcher, TCN_SELCHANGING),
                    "_selchange" : (NTFEventDispatcher, TCN_SELCHANGE),
                    }
    _dispatchers.update(Control._dispatchers)
                    
    def __init__(self, parent, pos=(-1,-1,-1,-1)):
        Control.__init__(self, parent, pos=pos)
        #self._send_w32_msg(CCM_SETVERSION, COMCTL32_VERSION, 0)
#        self.events['_selchanging'].bind(self._onchanging)

#        self.events['_selchange'].bind(self._onchange)

#        self.events['size'].bind(self._onsize)
        
        
        SetWindowPos(self._w32_hWnd, 0, 0, 0, 0, 0, 1|2|4|20)
        #self.update()
        InvalidateRect(self._w32_hWnd, 0, 0)
        
    def _insertitem(self, i, item):
        self._send_w32_msg(TCM_INSERTITEM, i, byref(item))

    def _getitem(self, index, mask):
        item = TCITEM()
        item.mask = mask
        if self._send_w32_msg(TCM_GETITEM, index, byref(item)):
            return item
        else:
            raise "error"
            
    def _adjustrect(self, fLarger, rc):
        lprect = byref(rc)
        self._send_w32_msg(TCM_ADJUSTRECT, fLarger, lprect) 
           
    def _resizetab(self, tab):
        if tab:
            rc = self.client_rect
            self._adjustrect(0, rc)
            tab.move(rc.left-(2*HIRES_MULT), rc.top-(2*HIRES_MULT), rc.width, rc.height)
            #tab.move(rc.left, rc.top, rc.width, rc.height)
            #SetWindowPos(tab._w32_hWnd, 0, rc.left, rc.top, rc.width, rc.height, 4)
            SetWindowPos(self._w32_hWnd, tab._w32_hWnd, rc.left, rc.top, rc.width, rc.height, 1|2)
            
class NoteBook(Frame):
    def __init__(self, parent, visible=True, enabled=True, pos=(-1,-1,-1,-1)):
        Frame.__init__(self, parent, visible=visible, enabled=enabled, pos=pos)
        self._tc = _TabControl(self)
        self._tc.bind(_selchanging=self._onchanging, 
                      _selchange=self._onchange,
                      size=self._onsize)
                      
        sizer = VBox((-2,-2,-2,0))
        sizer.add(self._tc)
        self.sizer = sizer
        
        
    def _onchanging(self, event):
        tab = self[self.selection]
        if tab :
            tab.hide()
        
    def _onchange(self, event):
        tab = self[self.selection]
        if tab :
            self._tc._resizetab(tab)
            tab.show(True)
    
    def _onsize(self, event):
        InvalidateRect(self._w32_hWnd, 0, 0)
        if self.selection is not None:
            tab = self[self.selection]
            self._tc._resizetab(tab)
        event.skip()
        
    def get_count(self):
        return self._tc._send_w32_msg(TCM_GETITEMCOUNT)
     
    doc_count = "The number of tab in the notebook"
    
    def append(self, title, tab):
        '''
        Adds a new tab to the notebook
        - title : the title of the tab
        - tab : the child window 
        '''
        self.insert(self.count, title, tab)
        
    def insert(self, i, title, tab):
        '''
        Inserts a new tab in the notebook at index i
        - title : the title of the tab
        - tab : the child window 
        '''
        if not 0<=i<=self.count:
            raise IndexError
        item = TCITEM()
        item.mask = TCIF_TEXT | TCIF_PARAM
        item.pszText = title
        item.lParam = tab._w32_hWnd
        self._tc._insertitem(i, item)
        
        self.selection = i
        return i
        
    def __getitem__(self, i):
        '''
        notebook[i] -> Returns the child window at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
        item = self._tc._getitem(i, TCIF_PARAM)
        return hwndWindowMap.get(item.lParam, None)
        
    def __delitem__(self, i):
        '''
        del notebook[i] -> Removes the tab at index i
        '''
        if not 0<=i<self.count:
            raise IndexError
            
        self._tc._send_w32_msg(TCM_DELETEITEM, i)
        if i == self.count:
            i -= 1
        self._tc._send_w32_msg(TCM_SETCURSEL, i)
        self._onchange(None)
        
    def get_selection(self):
        sel = self._tc._send_w32_msg(TCM_GETCURSEL)
        if sel != -1:
            return sel
        
    def set_selection(self, i):
        if not 0<=i<self.count:
            raise IndexError
        if i == self.selection : return
        self._onchanging(None)
        self._tc._send_w32_msg(TCM_SETCURSEL, i)
        self._onchange(None)
        
    doc_selection =  "The current index of the selected tab"
    
    def set_font(self, font):
        self._tc.font = font
    
    def get_font(self, font):
        return self._tc.font
        
class UpDown(Control):
    _w32_window_class = "msctls_updown32"
    _w32_window_style = WS_VISIBLE | WS_CHILD | UDS_SETBUDDYINT | 0x20 | 8
    _dispatchers = {'deltapos' : (NTFEventDispatcher, UDN_DELTAPOS)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, *args, **kw):
        kw['tab_stop'] = False
        Control.__init__(self, *args, **kw)
        
    def set_buddy(self, buddy):
        self._send_w32_msg(UDM_SETBUDDY, buddy._w32_hWnd)
    
    def set_range(self, range):
        low, high = range
        self._send_w32_msg(UDM_SETRANGE32, int(low), int(high))
        
    def get_best_size(self):
        return 14, 20
        
    def _get_pos(self):
        err = c_ulong()

        ret = self._send_w32_msg(UDM_GETPOS32, 0, byref(err))
        return ret
        
    def _set_pos(self, pos):
        self._send_w32_msg(UDM_SETPOS32, 0, pos)
        
class BusyCursor(GuiObject):
    def __init__(self):
        SetCursor(LoadCursor(0, 32514))
        
    def __del__(self):
        SetCursor(0)

########NEW FILE########
__FILENAME__ = converttonwin32
import re 


def convert(path):
    f = open(path)
    FUNCTION_RE = re.compile(r'(\S*?)\s*=\s*\w+dll.\w+.(\S*)')

    import ctypes

    dlls = \
    {
        'user32' : ctypes.windll.user32,
        'shell32' : ctypes.windll.shell32,
        'kernel32' : ctypes.windll.kernel32,
        'gdi32' : ctypes.windll.gdi32,
        'comctl32' : ctypes.windll.comctl32,
    }

    dlls_items = dlls.items()

    buffer = []
    for line in f.readlines():
        match = FUNCTION_RE.match(line)
        if match:
            function_name, function_w32_name = match.groups()
            #print function_name, function_w32_name
            dll_found = False
            for dll_name, dll in dlls_items:
                try:
                    getattr(dll, function_w32_name)
                except AttributeError:
                    continue
                else:
                    line = '%s = windll.%s.%s\n'\
                        %(function_name, dll_name, function_w32_name)
                    dll_found = True
                    break
            if not dll_found:
                line = '#%s' %line
                print '%s ignored' %function_name

        buffer.append(line)

    code= ''.join(buffer)
    open(path, 'w').write(code)

convert('filedlg.py')

########NEW FILE########
__FILENAME__ = core
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from w32api import *
from ctypes import *
from weakref import WeakValueDictionary
import weakref
from font import *

__doc__ = '''
This module contains the core mechanism of pycegui
'''

class GuiType(type):
    '''\
    The metaclass of GuiObject, useful for automatic property generation
    '''

    def __init__(cls, name, bases, dict):
        # Here we create properties based on
        # the set_xxx/get_xxx methods and
        # doc_xxx attribute of the class we construct.
        type.__init__(cls, name, bases, dict)
        methods = [(name, obj) for name, obj in dict.items() if callable(obj)]  
        properties = {}
        for name, obj in methods :
            if name[:4] in ['get_', 'set_']:
                property_name, meth_type = name[4:], name[:3]
                if not property_name in properties :
                    properties[property_name] = {}

                obj.__doc__ = "%ster for property %s" %(meth_type, property_name) 
                properties[property_name][meth_type] = obj
                doc_name = "doc_%s" %property_name
                
                if doc_name in dict :
                    properties[property_name]['doc'] = dict[doc_name]
                else:
                    properties[property_name]['doc'] = ''
        
        for property_name, property_data in properties.items() :
            prop = _makeprop(property_name, property_data)
            setattr(cls, property_name, prop)
            
        setattr(cls, '_properties', properties)
                
        
        
        
def _makeprop(property_name, property_data):
    # A property factory used to reference
    # property getters and setters as locals
    # of this function
    fget = None
    fset = None
    fdel = None
    
    if 'get' in property_data :
        fget = lambda self : getattr(self, "get_%s" %property_name)()
        
    if 'set' in property_data :
        fset = lambda self, val : getattr(self, "set_%s" %property_name)(val)
        
    doc = property_data.get('doc', None)
    prop = property(fget = fget,
                    fset = fset,
                    fdel = fdel,
                    doc = doc,
                    )
                    
    return prop
    

class GuiObject(object):
    '''\
    The most basic pycegui type. 
    '''
    __metaclass__ = GuiType
    
    def __init__(self, **kw):
        self.set(**kw)
    
    def set(self, **kw):
        '''\
        set(self, prop1=value1, prop2=value2, ...) --> sets the property prop1 to value1, prop2 to value2, ...
        '''
        for option, value in kw.items() :
            try :
                getattr(self, "set_%s" %option)(value)
            except AttributeError:
                raise AttributeError("can't set attribute '%s'" %option)
        
        

# Global objects and procedures
class IdGenerator(object):
    '''
    A global class to generate unique integers
    ids starting from 1000
    '''
    
    current_id = 999
    recycle = []
    
    @classmethod
    def next(cls):
        if cls.recycle :
            return cls.recycle.pop(0)
        cls.current_id += 1
        return cls.current_id
        
    @classmethod    
    def reuseid(cls, id):
        cls.recycle.append(id)

# The dict which maps HWND to gui.Window instances
hwndWindowMap =  WeakValueDictionary()
hInstance = GetModuleHandle(NULL)
wndClasses = []
# Dict which contains gui.Window data at creation time
createHndlMap = {}

schedulees = {}

WM_SCHEDULE = 0x8000 + 2

class Schedulee():
    '''
    Used internally by PPyGui. Not documented yet
    '''
    def __init__(self, func, args, kw):
        self.func = func
        self.args = args
        self.kw = kw
    
    def apply(self):
        self.func(*self.args, **self.kw)
    
mainframe_hwnd = 0

def schedule(func, args=[], kw={}):
    '''
    Schedule the fuction func
    to be called as function(*args, **kw)
    in the main thread.
    Gui objects are not generally thread
    safe, so a thread should use schedule instead
    of modifying directly the gui
    '''
    schedulee = Schedulee(func, args, kw)
    sid = id(schedulee)
    schedulees[sid] = schedulee
    PostMessage(mainframe_hwnd, WM_SCHEDULE, 0, sid) != 0
    
            
def globalWndProc(hWnd, nMsg, wParam, lParam):
    '''
    Used internally by PPyGui. Not documented yet
    '''

    if nMsg == WM_CREATE:
        createStruct = CREATESTRUCT.from_address(int(lParam))
        window = createHndlMap.get(int(createStruct.lpCreateParams), None)
        if window:
            hwndWindowMap[hWnd] = window
    
    elif nMsg == WM_SCHEDULE:
        sid = lParam
        schedulee = schedulees[sid]
        schedulee.apply()
        del schedulees[sid]
        return 0
    
    elif 306<=nMsg<=312: #Handle WM_CTLCOLOR* messages
        try:
            hbrush=DefWindowProc(hWnd, nMsg, wParam, lParam)
            win = hwndWindowMap[lParam]
            win._on_color(wParam)
            return hbrush
        except:
            #print "nocolor"
            #raise
            #SetTextColor
            return 5
            
    # A WM_ACTIVATE could occur before
    # the callback is bound to the 'activate' signal
    # Handle it statically here
    elif nMsg == WM_ACTIVATE : 
        if hWnd in hwndWindowMap:
            try :
                hwndWindowMap[hWnd]._on_activate(Event(hWnd, nMsg, wParam, lParam))
                return 0
            except:
                pass
       
    handled = False
        
    dispatcher = registeredEventDispatcher.match(hWnd, nMsg, wParam, lParam)
    if dispatcher :
        if dispatcher.isconnected() :
            handled, result = dispatcher.dispatch(hWnd, nMsg, wParam, lParam)
            if handled : return result
            
    win = hwndWindowMap.get(hWnd, None)    
    if win and win._issubclassed:
        return CallWindowProc(win._w32_old_wnd_proc, hWnd, nMsg, wParam, lParam)
    
    return DefWindowProc(hWnd, nMsg, wParam, lParam)

cGlobalWndProc = WNDPROC(globalWndProc)

class RegisteredEventsDispatcher(object):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self):
        self.msged = {}
        self.cmded = {}
        self.ntfed = {}
        self.ntfed2 = {}
        
    def match(self, hWnd, nMsg, wParam, lParam):
        if nMsg == WM_COMMAND :
            cmd = HIWORD(wParam)
            id = LOWORD(wParam)
            #print cmd, id
            if cmd == 4096 and id == 1:
                try:
                    win = hwndWindowMap[hWnd]
                    return win.onok()
                except AttributeError:
                    pass
            elif cmd == 4096 and id == 2:
                print 'cancel message'
#                try:

#                    win = hwndWindowMap[hWnd]

#                    win.close()

#                except AttributeError:

#                    pass
              
            try :
                return self.cmded[(id, cmd)]
            except :
                pass
                
        elif nMsg == WM_NOTIFY :
            nmhdr = NMHDR.from_address(int(lParam))
            hWnd = nmhdr.hwndFrom
            code = nmhdr.code
            
            try :
                return self.ntfed[(hWnd, code)]
            except :
                pass
                
            id = nmhdr.idFrom
            try :
                return self.ntfed2[(id, code)]
            except :
                pass
                
            #print 'debug', hWnd, code, nmhdr.idFrom
        elif nMsg in [WM_HSCROLL, WM_VSCROLL]:
            #Scroll messages are sent to parent
            #The source hWnd is lParam 
            try :
                #print "WM_XSCROLL lParam", lParam
                return self.msged[(lParam, nMsg)]
            except :
                pass
        
        else :
            try :
                #if dispatch.w32_hWnd == hWnd and dispatch.nMsg == nMsg :
                return self.msged[(hWnd, nMsg)]
            except :
                pass
                    
    def install(self, dispatcher):
        if isinstance(dispatcher, MSGEventDispatcher):
            self.msged[(dispatcher.w32_hWnd, dispatcher.nMsg)] = dispatcher
        elif isinstance(dispatcher, CMDEventDispatcher):
            self.cmded[(dispatcher._id, dispatcher.cmd)] = dispatcher
        elif isinstance(dispatcher, NTFEventDispatcher):
            self.ntfed[(dispatcher.w32_hWnd, dispatcher.code)] = dispatcher
            if hasattr(dispatcher, '_id'):
                self.ntfed2[(dispatcher._id, dispatcher.code)] = dispatcher
    
    def remove(self, dispatcher):
#        for d in [self.msged, self.cmded, self.ntfed]:

#            for key, disp in d.items() :

#                if disp is dispatcher :

#                    del d[key]

#                    break
                    #return
        if isinstance(dispatcher, MSGEventDispatcher):
            del self.msged[(dispatcher.w32_hWnd, dispatcher.nMsg)]
        elif isinstance(dispatcher, CMDEventDispatcher):
            del self.cmded[(dispatcher._id, dispatcher.cmd)]
        elif isinstance(dispatcher, NTFEventDispatcher):
            del self.ntfed[(dispatcher.w32_hWnd, dispatcher.code)]
            if hasattr(dispatcher, '_id'):
                del self.ntfed2[(dispatcher._id, dispatcher.code)]
            
registeredEventDispatcher = RegisteredEventsDispatcher()

# Events and EventDispatcher objects

class Event(GuiObject):
    '''\
    Basic object that wraps a win32 message, it is often
    the first argument received by a callback.
    Use the read-only properties to have more information about an Event instance.
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self.hWnd = hWnd
        self.nMsg = nMsg
        self.wParam = wParam
        self.lParam = lParam
        self._window = hwndWindowMap.get(hWnd, None)
        self.handled = True
    
    def get_window(self):
        return self._window
        
    doc_window = "Source Window instance that triggered the event"
    
    def skip(self):
        '''\
        Tells the default window procedure to handle the event.
        '''
        self.handled = False
        
class SizeEvent(Event):
    '''\
    An Event that is raised by a window when resized
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self._size = LOWORD(lParam), HIWORD(lParam)
        Event.__init__(self, hWnd, nMsg, wParam, lParam)
        
    def get_size(self):
        return self._size
          
    doc_size = 'The new size of the window as a tuple (widht, height)'
    
class CommandEvent(Event):
    '''\
    An Event that wraps Win32 WM_COMMAND messages
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self.id, self._cmd = LOWORD(wParam), HIWORD(wParam)
        #print lParam
        Event.__init__(self, lParam, nMsg, wParam, lParam)
        
    def get_cmd(self):
        return self._cmd
        
class NotificationEvent(Event):
    '''\
    An Event that wraps Win32 WM_NOTIFY messages
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        nmhdr = NMHDR.from_address(int(lParam))
        hwndFrom = nmhdr.hwndFrom
        self._code = nmhdr.code
        self.nmhdr = nmhdr
        Event.__init__(self, hwndFrom, nMsg, wParam, lParam)
        
    def get_code(self):
        return self._code
        
class StylusEvent(Event):
    '''
    An Event that is raised on interaction of a window with the stylus.
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
       pt = GET_POINT_LPARAM(lParam)
       self._position = pt.x, pt.y
       Event.__init__(self, hWnd, nMsg, wParam, lParam)
       
    def get_position(self):
        return self._position
        
    doc_position = 'The position of the stylus as a tuple (left, top)'
    

class KeyEvent(Event):
    '''
    An event raised when the user press a keyboard
    or move the joystick in the window
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self._key_code = wParam
        self._repeat_count = lParam & 65535
        Event.__init__(self, hWnd, nMsg, wParam, lParam)
        
    def get_key_code(self):
        return self._key_code
    
    doc_key_count = 'The virtual key code of the key pressed'
    
    def get_repeat_count(self):
        return self._repeat_count
     
class CharEvent(Event):
    '''
    An event raised when the user press a keyboard
    or move the joystick in the window
    '''
    def __init__(self, hWnd, nMsg, wParam, lParam):
        self._key_code = wParam
        self._repeat_count = lParam & 65535
        Event.__init__(self, hWnd, nMsg, wParam, lParam)
        
    def get_key(self):
        return unichr(self._key_code)

class EventDispatcher(object):
    '''
    Used internally by PPyGui. Not documented yet
    '''
        
    def __init__(self, eventclass = Event) :
        self.eventclass = eventclass 
        self.callback = None
        
    def isconnected(self):
        return bool(self.callback)
    
    def bind(self, callback=None):
        if callback is not None :
            self.callback = callback
    
    def unbind(self):
        self.callback = None
        
    def dispatch(self, hWnd, nMsg, wParam, lParam):
        if self.callback :
            event = self.eventclass(hWnd, nMsg, wParam, lParam)
            res = self.callback(event)
            if res is None:
                res = 0
            return event.handled, res
        return False
        
class CustomEvent(GuiObject):
    def __init__(self, window):
        self.window = window
        
class CustomEventDispatcher(EventDispatcher):
    def call(self, event):
        if self.callback is not None:
            self.callback(event)
        
class MSGEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, win, nMsg, eventclass = Event):
        self.w32_hWnd = win._w32_hWnd
        self.nMsg = nMsg
        EventDispatcher.__init__(self, eventclass)
    
        
class CMDEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, win, cmd=0, eventclass = CommandEvent):
        self._id = win._id
        self.cmd = cmd
        EventDispatcher.__init__(self, eventclass)
    
class MenuEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, id):
        self._id = id
        self.cmd = 0
        EventDispatcher.__init__(self, CommandEvent)
        
class NTFEventDispatcher(EventDispatcher):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __init__(self, win, code, eventclass = NotificationEvent):
        self.w32_hWnd = win._w32_hWnd
        if hasattr(win, '_id'):
            self._id = win._id
        self.code = code
        EventDispatcher.__init__(self, eventclass)
        
class EventDispatchersMap(dict):
    '''
    Used internally by PPyGui. Not documented yet
    '''
    
    def __setitem__(self, i, dispatcher):
        registeredEventDispatcher.install(dispatcher)
        dict.__setitem__(self, i, dispatcher)
        
    def __del__(self):
        for event, dispatcher in self.items():
            registeredEventDispatcher.remove(dispatcher)
        
class Window(GuiObject):
    '''\
    The base class of all displayable elements
    Events:
        - paint -> Event: sent when the window needs repainting
        - close -> Event: sent when the user or os request the window to be closed
        - destroy -> Event: sent when the window is about to be destroyed
        - size -> SizeEvent: sent when the window is resized
        - lbdown -> StylusEvent: sent when the stylus is pressed down on the window 
        - lbmove -> StylusEvent: sent when the stylus is sliding on the window 
        - lbup -> StylusEvent: sent when the stylus is pressed down on the window 
    '''
    
    
    _w32_window_class = None
    _w32_window_style = WS_CHILD
    _w32_window_style_ex = 0
    _w32_window_class_style = CS_HREDRAW | CS_VREDRAW
    _background = 1
    _dispatchers = {'paint': (MSGEventDispatcher, WM_PAINT,), 
                    'close' : (MSGEventDispatcher, WM_CLOSE,),
                    'destroy' : (MSGEventDispatcher, WM_DESTROY,),
                    'size' : (MSGEventDispatcher, WM_SIZE, SizeEvent),
                    'lbdown' : (MSGEventDispatcher, WM_LBUTTONDOWN, StylusEvent),
                    'lbmove' : (MSGEventDispatcher, WM_MOUSEMOVE, StylusEvent),
                    'lbup' : (MSGEventDispatcher, WM_LBUTTONUP, StylusEvent),
                    'chardown' : (MSGEventDispatcher, WM_CHAR, CharEvent),
                    'keydown' : (MSGEventDispatcher, WM_KEYDOWN, KeyEvent),
                    'focus' : (MSGEventDispatcher, WM_SETFOCUS,),
                    'lostfocus' : (MSGEventDispatcher, WM_SETFOCUS+1,),
                    'erasebkg' : (MSGEventDispatcher, WM_ERASEBKGND),
                    }
        
    def __init__(self, parent=None, 
                       title="PocketPyGui", 
                       style="normal", 
                       visible=True, 
                       enabled=True, 
                       pos=(-1,-1,-1,-1), 
                       tab_traversal=True, 
                       **kw):
        '''\.
        Arguments:
            - parent: the parent window 
            - title: the title as appearing in the title bar.
            - style: normal or control
            - pos: a tuple (left, top, width, height) that determines the initial position of the window.
              use -1 in any tuple element for default positioning.
              It is strongly recommanded to use the Sizer classes to perform the layout.
            - tab_traversal : whether the Window implements automatic tab/jog-dial 
        '''
        
        #Fixme: clean the legacy venster code.
        windowClassExists = False
        cls = WNDCLASS() # WNDCLASS()
        if self._w32_window_class:
            if GetClassInfo(hInstance, unicode(self._w32_window_class), byref(cls)):
                windowClassExists = True
        
        #determine whether we are going to subclass an existing window class
        #or create a new windowclass
        self._issubclassed = self._w32_window_class and windowClassExists
        
        if not self._issubclassed:
            #if no _window_class_ is given, generate a new one
            className = self._w32_window_class or "pycegui_win_class_%s" % str(id(self.__class__))
            className = unicode(className)
            cls = WNDCLASS() # WNDCLASS()
            cls.cbSize = sizeof(cls)
            cls.lpszClassName = className
            cls.hInstance = hInstance
            cls.lpfnWndProc = cGlobalWndProc
            cls.style = self._w32_window_class_style
            cls.hbrBackground = self._background # Add background customisation
            cls.hIcon = 0
            cls.hCursor = 0
            
            
            ###
            if tab_traversal:
                cls.cbWndExtra = 32
            ###
            wndClasses.append(cls)
            atom = RegisterClass(byref(cls)) # RegisterClass
        else:
            #subclass existing window class.
            className = unicode(self._w32_window_class)
        
        assert style in ["normal", "control"]
        _w32_style = self._w32_window_style
 
        if not parent :
            _w32_style &= ~WS_CHILD
            
        if visible:
            _w32_style |= WS_VISIBLE
            
        self._visible = visible
        defaultorpos = lambda pos : (pos == -1 and [CW_USEDEFAULT] or [pos])[0]
        left, top, width, height = [defaultorpos(p) for p in pos]

        parenthWnd = 0
        if parent :
            parenthWnd = parent._w32_hWnd
          
        menuHandle = 0
        if hasattr(self, '_id'):
            menuHandle = self._id
        
        createHndlMap[id(self)] = self
        self._w32_hWnd = CreateWindowEx(self._w32_window_style_ex,
                              unicode(className),
                              unicode(title),
                              _w32_style,
                              left,
                              top,
                              width,
                              height,
                              parenthWnd,
                              menuHandle,
                              hInstance,
                              id(self))

        if self._issubclassed:
            self._w32_old_wnd_proc = self.__subclass(cGlobalWndProc)
            hwndWindowMap[self._w32_hWnd] = self
        
        self.events = EventDispatchersMap()
        for eventname, dispatchinfo in self._dispatchers.items() :
            dispatchklass = dispatchinfo[0]
            dispatchargs = dispatchinfo[1:]
            self.events[eventname] = dispatchklass(self, *dispatchargs)
        del createHndlMap[id(self)]
        
        GuiObject.__init__(self, **kw)
        self.bind(destroy=self._ondestroy)
        self.enable(enabled)
        
    def bind(self, **kw):
        '''\
        bind(self, event1=callback1, event2=callbac2, ...) -->
        maps gui events to callbacks,
        callbacks are any callable fthat accept a single argument.
        ''' 
        for option, value in kw.items() :
            try:
                self.events[option].bind(value)
            except KeyError :
                raise KeyError("%r has no event '%s'" %(self, option))
        
    def call_base_proc(self, event):
        return CallWindowProc(self._w32_old_wnd_proc, self._w32_hWnd, event.nMsg, event.wParam, event.lParam)
        
    def __subclass(self, newWndProc):
        return SetWindowLong(self._w32_hWnd, GWL_WNDPROC, newWndProc)
        
    def _send_w32_msg(self, nMsg, wParam=0, lParam=0):
        return SendMessage(self._w32_hWnd, nMsg, wParam, lParam)
    
    def get_client_rect(self):
        rc = RECT()
        GetClientRect(self._w32_hWnd, byref(rc))
        return rc
    
    doc_client_rect = 'The window client rect, i.e. the inner rect of the window'
        
    def get_window_rect(self):
        rc = RECT()
        GetWindowRect(self._w32_hWnd, byref(rc))
        return rc
    
    def get_visible(self):
        return self._visible
    
    doc_window_rect = 'The window rect in its parent container'
    
    def get_pos(self):
        rc = self.window_rect
        parent = self.parent
        if parent is not None:
            parent_rc = parent.window_rect
            return rc.left-parent_rc.left, rc.top-parent_rc.top
        return rc.left, rc.top
        
    def set_pos(self, pos):
        left, top = pos
        left = int(left)
        top = int(top) 
        rc = self.window_rect
        
        MoveWindow(self._w32_hWnd, left, top, rc.width, rc.height, 0)
    
    doc_pos = 'The relative window position in its parent container as a tuple (left, top)'
    
    def get_size(self):
        rc = self.client_rect
        return rc.width, rc.height
        
    def set_size(self, size):
        width, height = size
        width = int(width)
        height = int(height)
        left, top = self.pos
        MoveWindow(self._w32_hWnd, left, top, width, height, 0)
    
    doc_size = 'The size of the window as a tuple (width, height)'
        
    def get_parent(self):
        parentHwnd = GetParent(self._w32_hWnd)
        return hwndWindowMap.get(parentHwnd, None)
        
    doc_parent = 'The parent window instance or None for a top window'
    
    def focus(self):
        '''
        Force the focus on this window
        '''
        SetFocus(self._w32_hWnd)
    
    def set_redraw(self, redraw):
        self._send_w32_msg(WM_SETREDRAW, bool(redraw), 0)
        
    doc_redraw = '''\
    The redraw state as a bool. When setting it to
    False, the window will not be repainted, until it
    is set to True again'''

    def get_text(self):
        textLength = self._send_w32_msg(WM_GETTEXTLENGTH)# + 1
        textBuff = u' ' * textLength
        textBuff = create_unicode_buffer(textBuff)
        self._send_w32_msg(WM_GETTEXT, textLength+1, textBuff)
        return textBuff.value
        
    def set_text(self, txt):
        self._send_w32_msg(WM_SETTEXT, 0, unicode(txt))
        
    doc_text = "The text displayed by the control as a string"
        
    def show(self, val=True):
        '''\
        Show or hide the window, depending of the
        boolean value of val. 
        '''
        if val :
            ShowWindow(self._w32_hWnd, SW_SHOW)
        else :
            ShowWindow(self._w32_hWnd, SW_HIDE)
        self._visible = val
            
    def hide(self):
        '''\
        Hide the window. Equivalent to win.show(False)
        '''
        self.show(False)
            
    def enable(self, val=True):
        '''\
        Enable or disable the window, depending of the
        boolean value of val. 
        '''
        EnableWindow(self._w32_hWnd, bool(val))
        
    def disable(self):
        '''\
        Disable the window
        '''
        self.enable(False)
        
    def update(self):
        '''\
        Forces the window to be repainted
        '''
        UpdateWindow(self._w32_hWnd)
        
    def move(self, left, top, width, height):
        '''\
        Moves the window to the desired rect (left, top, width, height)
        '''
        MoveWindow(self._w32_hWnd, left, top, width, height, 0)

    def close(self):
        '''
        Programmaticaly request the window to be closed
        '''
        self._send_w32_msg(WM_CLOSE)
        
    def destroy(self):
        '''
        Destroy the window and its child, releasing their resources, and break 
        reference cycle that could be induced by the event system.
        '''
        DestroyWindow(self._w32_hWnd)
    
    def _ondestroy(self, event):
        del self.events
        event.skip()
        
    def bringtofront(self):
        '''\
        Bring the window to foreground
        '''
        SetForegroundWindow(self._w32_hWnd)

class Control(Window):
    '''\
    The base class for common controls.
    It introduces the text and font properties
    '''
    
    _w32_window_style = WS_CHILD
    _defaultfont = DefaultFont
    _w32_window_class_style = 0
    
    def __init__(self, parent, title="", border=False, visible=True, enabled=True, pos=(-1,-1,-1,-1), tab_stop=True, **kw):
        style="control"
        self._id = IdGenerator.next()
        if tab_stop:
            self._w32_window_style |= WS_TABSTOP
        if border:
            self._w32_window_style |= WS_BORDER
        Window.__init__(self, parent, title, style, visible=visible, enabled=enabled, pos=pos)
        self._best_size = None
        self.font = self._defaultfont
        self.set(**kw)
#        self.bind(erasebkg=self._onebkg)

#        

#    def _onebkg(self, ev):

#        return 1

#        #ev.skip()
        
    def get_text(self):
        return Window.get_text(self)
            
    def set_text(self, value):
        Window.set_text(self, value)
        self._best_size = None
        
    def set_font(self, font):
        self._font = font
        self._send_w32_msg(WM_SETFONT, font._hFont, 1)
        self._best_size = None
        
    def get_font(self):
        #return self._send_w32_msg(WM_GETFONT)
        return self._font
        
    doc_font = "The font of the control as a font.Font instance"
        
    def __del__(self):
        #Window.__del__(self)
        IdGenerator.reuseid(self._id)
        
    def _get_best_size(self):
        return None, None
        
    def get_best_size(self):
        if not self._visible:
            return 0,0
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
            
    def _on_color(self, dc):
        if hasattr(self, '_font'):
            SetTextColor(dc, self._font._color)
        
class Frame(Window):
    '''
    Frame extends Window to provide layout facilities.
    You can bind a sizer to a Frame using the sizer property
    '''
    _background = 16
    _w32_window_style = Window._w32_window_style #| WS_CLIPCHILDREN
    _w32_window_style_ex = 0x10000
    def __init__(self, parent, title="", pos=(-1,-1,-1,-1), visible=True, enabled=True, tab_traversal=True,**kw):
        self._sizer = None
        Window.__init__(self, parent, title, style="normal", pos=pos, visible=visible, enabled=enabled, tab_traversal=tab_traversal, **kw)
        self.events['size'].bind(self._on_size)
        
    def get_sizer(self):
        return self._sizer
        
    def set_sizer(self, sizer):
        self._sizer = sizer
        self.layout()
        
    def get_best_size(self):
        if not self._visible:
            return 0, 0
        if self._sizer is not None:
            return self._sizer.get_best_size()
        return None, None
        
    doc_sizer = "A sizer.Sizer, sizer.HSizer or sizer.VSizer instance responsible of the layout"
    
    def layout(self):
        '''\
        Forces the frame to lay its content out with its sizer property. 
        Note it is automatically called anytime the Frame is moved or resized, 
        or when the sizer property is set.
        '''
        if self._sizer is not None:
            rc = RECT()
            GetClientRect(self._w32_hWnd, byref(rc))
            self._sizer.size(rc.left, rc.top, rc.right, rc.bottom)
        InvalidateRect(self._w32_hWnd, 0, 0)
        
    def _on_size(self, event):
        self.layout()


        
# MessageLoop and Application   

class MessageLoop:
    '''
    Used internally by PPyGui. Not documented yet
    '''
    def __init__(self):
        self.m_filters = {}

    def AddFilter(self, filterFunc):
        self.m_filters[filterFunc] = 1

    def RemoveFilter(self, filterFunc):
        del self.m_filters[filterFunc]
        
    def Run(self):
        msg = MSG()
        lpmsg = byref(msg)
        while GetMessage(lpmsg, 0, 0, 0):
            if not self.PreTranslateMessage(msg):
                if IsDialogMessage(GetActiveWindow(), lpmsg):
                    continue
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)
        global quit
        quit = True
                    
    def PreTranslateMessage(self, msg):
        for filter in self.m_filters.keys():
            if filter(msg):
                return 1
        return 0
    
theMessageLoop = MessageLoop()

def GetMessageLoop():
    return theMessageLoop

class Application(GuiObject):
    '''\
    Each ppygui application should have an instance of Application.
    An Application object has a mainframe property which is usually a 
    ce.CeFrame object, which quits the application when destroyed
    '''
    def __init__(self, mainframe=None):
        self.messageloop = MessageLoop()
        if mainframe is not None:
            self.mainframe = mainframe
            
    def run(self):
        '''\
        Start the main loop of the application.
        It get rids of the nasty busy cursor, 
        whatever PythonCE is launched
        with /nopcceshell or not.
        '''
        try:
            import _pcceshell_support
            _pcceshell_support.Busy(0)
        except ImportError :
            SetCursor(LoadCursor(0, 0))
        return self.messageloop.Run()

    def set_mainframe(self, frame): 
        self._mainframe = frame
        self._mainframe.bind(destroy=lambda event : self.quit())
        global mainframe_hwnd 
        mainframe_hwnd = frame._w32_hWnd
        
        
    def get_mainframe(self):
        return self._mainframe
        
    doc_mainframe ="""\
    The main frame of the application.
    The application will exit when frame is destroyed
    """
        
    
    def quit(self, exitcode = 0):
        """\
        Quits the application with the exit code exitcode
        """
        PostQuitMessage(exitcode)

########NEW FILE########
__FILENAME__ = date
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from w32comctl import *
from config import HIRES_MULT

import datetime

ICC_DATE_CLASSES = 0x100
DTS_TIMEFORMAT = 0x9
DTM_FIRST = 0x1000
DTM_GETSYSTEMTIME = DTM_FIRST+1
DTM_SETSYSTEMTIME = DTM_FIRST+2

DTN_FIRST = 4294966536
DTN_DATETIMECHANGED = DTN_FIRST + 1

class SYSTEMTIME(Structure):
    _fields_ = [("wYear", WORD),
                ("wMonth", WORD),
                ("wDayOfWeek", WORD),
                ("wDay", WORD),
                ("wHour", WORD),
                ("wMinute", WORD),
                ("wSecond", WORD),
                ("wMilliseconds", WORD),]
    
class Date(Control):
    _w32_window_class = "SysDateTimePick32"
    _w32_window_style = WS_CHILD
    _dispatchers = {'update' : (NTFEventDispatcher, DTN_DATETIMECHANGED)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, *args, **kw):
        Control.__init__(self, *args, **kw)
        self._best_size = None
        
    def get_value(self):
        st = SYSTEMTIME()
        self._send_w32_msg(DTM_GETSYSTEMTIME, 0, byref(st))
        return datetime.date(st.wYear, st.wMonth, st.wDay)

    def set_value(self, date):
        st = SYSTEMTIME()
        st.wYear = date.year
        st.wMonth = date.month
        st.wDay = date.day
        self._send_w32_msg(DTM_SETSYSTEMTIME, 0, byref(st))
        
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text
        cx, cy = GetTextExtent(dc, u'dd/mm/yyyy')
        return 15+cx/HIRES_MULT, 7+cy/HIRES_MULT
        
    def get_font(self):
        return Control.get_font(self)
            
    def set_font(self, value):
        Control.set_font(self, value)
        self._best_size = None
        
    def get_best_size(self):
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
            
class Time(Control):
    _w32_window_class = "SysDateTimePick32"
    _w32_window_style = WS_CHILD | DTS_TIMEFORMAT
    _dispatchers = {'update' : (NTFEventDispatcher, DTN_DATETIMECHANGED)}
    _dispatchers.update(Control._dispatchers)
    
    def __init__(self, *args, **kw):
        Control.__init__(self, *args, **kw)
        self._best_size = None
        
    def get_value(self):
        st = SYSTEMTIME()
        self._send_w32_msg(DTM_GETSYSTEMTIME, 0, byref(st))
        return datetime.time(st.wHour, st.wMinute, st.wSecond)

    def set_value(self, time):
        st = SYSTEMTIME()
        self._send_w32_msg(DTM_GETSYSTEMTIME, 0, byref(st))
        st.wHour = time.hour
        st.wMinute = time.minute
        st.wSecond = time.second
        self._send_w32_msg(DTM_SETSYSTEMTIME, 0, byref(st))
    
    def _get_best_size(self):
        dc = GetDC(self._w32_hWnd)
        font = self._font._hFont
        SelectObject(dc, font)
        text = self.text
        cx, cy = GetTextExtent(dc, u'hh:mm:ss')
        return 15+cx/HIRES_MULT, 7+cy/HIRES_MULT
    
    def get_font(self):
        return Control.get_font(self)
            
    def set_font(self, value):
        Control.set_font(self, value)
        self._best_size = None
        
    def get_best_size(self):
        if self._best_size is None:
            best_size = self._get_best_size()
            self._best_size = best_size
            return best_size
        else:
            return self._best_size
                 
def _InitDateControl():
    icc = INITCOMMONCONTROLSEX()
    icc.dwSize = sizeof(INITCOMMONCONTROLSEX)
    icc.dwICC = ICC_DATE_CLASSES 
    InitCommonControlsEx(byref(icc))

_InitDateControl()

########NEW FILE########
__FILENAME__ = dialog
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from ce import CeFrame
from controls import Button
 
EnableWindow = windll.user32.EnableWindow
IsDialogMessage = windll.user32.IsDialogMessageW

class Dialog(CeFrame):    
    #_w32_window_class = "DIALOG"
    #_w32_window_style = WS_MAXIMIZE
    #_w32_window_style_ex = 0x10000
    
    def __init__(self, title, action=None, menu=None, visible=False, enabled=True, has_sip=True, has_ok=True):
        self.has_ok = has_ok
        CeFrame.__init__(self, None, title, action=action, menu=menu, visible=visible, enabled=enabled, has_sip=has_sip)
        self.bind(close=self._onclose)
        #self.has_ok = has_ok
        self.poppingup = False
        

    def _create_tr_button(self):
        if self.has_ok:
            self.top_right_button = Button(self, 'Ok', action=lambda ev: self.onok())
        else:
            CeFrame._create_tr_button(self)
            

            
    def popup(self, parent=None):
        self._parent = parent
        
        self.show()
        self.bringtofront()
        if self._parent :
            self._parent.disable()
            #self._parent.hide()
        
        self.poppingup = True
        while self.poppingup:
            msg = MSG()
            lpmsg = byref(msg)
            if GetMessage(lpmsg, 0, 0, 0):
                
                if IsDialogMessage(self._w32_hWnd, lpmsg):  
                    continue
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)
            else :
                PostQuitMessage()
                return
                
        return self.ret_code
        
    def end(self, code):
        self.ret_code = code
        self.poppingup = False
        if self._parent is not None:
            self._parent.enable()
            #self._parent.show()
            self._parent.bringtofront()
            self._parent.focus()
        self.hide()
        
    def onok(self):
        self.end('ok')
        
    def oncancel(self):
        self.end('cancel')
        
    def _onclose(self, event):
#        if self._parent is not None:

#            self._parent.enable()

#            self._parent.show()

#            self._parent.bringtofront()
        self.end('cancel')

########NEW FILE########
__FILENAME__ = dialoghdr
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from controls import Label
from boxing import VBox, Spacer
from font import Font
from line import HLine

class DialogHeader(Frame):
    def __init__(self, parent, text):
        Frame.__init__(self, parent)
        self.label = Label(self, text, 
                           font=Font(size=8, 
                                     bold=True, 
                                     color=(0,0,255) 
                                     # XXX: Use system prefs instead of hardcoded blue
                                    )
                          )
        self.hline = HLine(self)
        sizer = VBox()
        sizer.add(Spacer(2,4))
        sizer.add(self.label, border=(4,0,0,0))
        sizer.add(Spacer(2,4))
        sizer.add(self.hline)
        self.sizer = sizer
        
    def set_text(self, text):
        self.label.set_text(text)
        
    def get_text(self):
        return self.label.get_text()
########NEW FILE########
__FILENAME__ = filedlg
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from ctypes import *

LPOFNHOOKPROC = c_voidp #TODO

class OPENFILENAME(Structure):
    _fields_ = [("lStructSize", DWORD),
                ("hwndOwner", HWND),
                ("hInstance", HINSTANCE),
                ("lpstrFilter", LPCTSTR),
                ("lpstrCustomFilter", LPTSTR),
                ("nMaxCustFilter", DWORD),
                ("nFilterIndex", DWORD),
                ("lpstrFile", LPTSTR),
                ("nMaxFile", DWORD),
                ("lpstrFileTitle", LPTSTR),
                ("nMaxFileTitle", DWORD),
                ("lpstrInitialDir", LPCTSTR),
                ("lpstrTitle", LPCTSTR),
                ("Flags", DWORD),
                ("nFileOffset", WORD),
                ("nFileExtension", WORD),
                ("lpstrDefExt", LPCTSTR),
                ("lCustData", LPARAM),
                ("lpfnHook", LPOFNHOOKPROC),
                ("lpTemplateName", LPCTSTR),
                ]

try:
    # Detect if tGetFile.dll is present
    tGetFile = cdll.tgetfile.tGetFile
    def GetOpenFileName(ofn):
        return tGetFile(True, ofn)
    def GetSaveFileName(ofn):
        return tGetFile(False, ofn)
except:
    # Else use standard wince function
    GetOpenFileName = windll.comdlg32.GetOpenFileNameW
    GetSaveFileName = windll.comdlg32.GetSaveFileNameW

OFN_ALLOWMULTISELECT = 512
OFN_CREATEPROMPT= 0x2000
OFN_ENABLEHOOK =32
OFN_ENABLETEMPLATE= 64
OFN_ENABLETEMPLATEHANDLE= 128
OFN_EXPLORER= 0x80000
OFN_EXTENSIONDIFFERENT= 0x400
OFN_FILEMUSTEXIST =0x1000
OFN_HIDEREADONLY= 4
OFN_LONGNAMES =0x200000
OFN_NOCHANGEDIR= 8
OFN_NODEREFERENCELINKS= 0x100000
OFN_NOLONGNAMES= 0x40000
OFN_NONETWORKBUTTON =0x20000
OFN_NOREADONLYRETURN= 0x8000
OFN_NOTESTFILECREATE= 0x10000
OFN_NOVALIDATE= 256
OFN_OVERWRITEPROMPT= 2
OFN_PATHMUSTEXIST= 0x800
OFN_READONLY= 1
OFN_SHAREAWARE= 0x4000
OFN_SHOWHELP= 16
OFN_SHAREFALLTHROUGH= 2
OFN_SHARENOWARN= 1
OFN_SHAREWARN= 0
OFN_NODEREFERENCELINKS = 0x100000
OFN_PROJECT = 0x400000
OPENFILENAME_SIZE_VERSION_400 = 76

class FileDialog(object):
    
    @classmethod
    def _do_modal(cls, parent, title, wildcards, filename, f, folder=False):
        szPath = u'\0' * 1024
        if parent is None :
            hparent = 0
        else :
            hparent = parent._w32_hWnd
            
        filter = "".join("%s|%s|" %item for item in wildcards.items())
        filter = filter.replace('|', '\0') + '\0\0'

        ofn = OPENFILENAME()
        if folder:
            ofn.Flags = OFN_PROJECT
        if versionInfo.isMajorMinor(4, 0): #fix for NT4.0
            ofn.lStructSize = OPENFILENAME_SIZE_VERSION_400
        else:
            ofn.lStructSize = sizeof(OPENFILENAME)
        #ofn.lpstrFile = szPath
        filename = unicode(filename)
        filename += u"\0"*(1024-len(filename))
        ofn.lpstrFile = filename
        #ofn.lpstrFileTitle = unicode(filename)
        #ofn.nMaxFileTitle = 1024
        ofn.nMaxFile = 1024
        ofn.hwndOwner = hparent
        ofn.lpstrTitle = unicode(title)
        ofn.lpstrFilter = filter
    
        try:
            #the windows file dialogs change the current working dir of the app
            #if the user selects a file from a different dir
            #this prevents that from happening (it causes al sorts of problems with
            #hardcoded relative paths)
            import os
            cwd = os.getcwd()
            if f(byref(ofn))!= 0:
                return filename[:filename.find('\0')].strip()
            else:
                return
        finally:
            os.chdir(cwd) 
            
    @classmethod
    def open(cls, title="Open", filename="", wildcards={"All (*.*)":"*.*"}, parent=None):
        return cls._do_modal(parent, title, wildcards, filename, GetOpenFileName)
    
    @classmethod
    def openfolder(cls, title="Open", filename="", wildcards={"All (*.*)":"*.*"}, parent=None):
        return cls._do_modal(parent, title, wildcards, filename, GetOpenFileName, folder=True)

    @classmethod    
    def save(cls, title="Save", filename="", wildcards={"All (*.*)":"*.*"}, parent=None):
        return cls._do_modal(parent, title, wildcards, filename, GetSaveFileName)

########NEW FILE########
__FILENAME__ = font
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from w32api import *
from config import HIRES

CreateFontIndirect=windll.gdi32.CreateFontIndirectW

class LOGFONT(Structure):
    _fields_ = [("lfHeight", LONG),
                ("lfWidth", LONG),                
                ("lfEscapement", LONG),
                ("lfOrientation", LONG),
                ("lfWeight", LONG),
                ("lfItalic", BYTE),
                ("lfUnderline", BYTE),
                ("lfStrikeOut", BYTE),
                ("lfCharSet", BYTE),
                ("lfOutPrecision", BYTE),
                ("lfClipPrecision", BYTE),
                ("lfQuality", BYTE), 
                ("lfPitchAndFamily", BYTE),
                ("lfFaceName", TCHAR * 32)]

def rgb(r, g, b):
    return r+(g<<8)+(b<<16)
    
class Font(object):
        
    def __init__(self, name="Tahoma", size=9, bold=False, italic=False, color=(0,0,0), underline=False):
        
        height = int(-size*96/72.0)
        if HIRES :
            height *= 2
            
        lf = LOGFONT()
        lf.lfHeight = height
        lf.lfFaceName = name
        if bold :
            lf.lfWeight = 700
        if italic :
            lf.lfItalic = 1
        if underline :
            lf.lfUnderline = 1
        
        self._hFont = CreateFontIndirect(byref(lf))
        self._color = rgb(*color)
        
    def __del__(self):
        DeleteObject(self._hFont)
        
DefaultFont = Font(size=8)
ButtonDefaultFont = Font(size=8, bold=True)

########NEW FILE########
__FILENAME__ = html
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from ctypes import cdll, Structure, Union

DTM_ADDTEXTW = WM_USER+102
DTM_ENDOFSOURCE = WM_USER + 104
DTM_NAVIGATE = WM_USER + 120
DTM_ZOOMLEVEL = WM_USER + 116
DTM_CLEAR = WM_USER + 113
DTM_ENABLESHRINK = WM_USER + 107
DTM_ENABLECONTEXTMENU = WM_USER + 110

class _U_NM_HTMLVIEW(Union):
    _fields_ = [('dwCookie', DWORD),
                ('dwFlags', DWORD)
                ]
                
class NM_HTMLVIEW(Structure):
    _fields_ = [('hdr', NMHDR),
                ('szTarget', LPCTSTR),
                ('szData', LPCTSTR),
                ('_u', _U_NM_HTMLVIEW),
                ('szExInfo', LPCTSTR),
                ]
    _anonymous_ = ('_u',)

NM_BEFORENAVIGATE = WM_USER + 109

class BeforeNavigateEvent(NotificationEvent):
    def __init__(self, hwnd, nmsg, wparam, lparam):
        NotificationEvent.__init__(self, hwnd, nmsg, wparam, lparam)
        nmhtml = NM_HTMLVIEW.from_address(lparam)
        self._url = nmhtml.szTarget
        
    def get_url(self):
        return self._url
    
class Html(Control):
    _w32_window_class = "DISPLAYCLASS"
    _dispatchers = {"navigate" : (NTFEventDispatcher, NM_BEFORENAVIGATE, BeforeNavigateEvent)
                    }
    _dispatchers.update(Control._dispatchers)
    
    def _addtext(self, txt, plain=False):
        txt=unicode(txt)
        self._send_w32_msg(DTM_ADDTEXTW, int(plain), txt)
        
    def _endofsource(self):
        self._send_w32_msg(DTM_ENDOFSOURCE)
    
    def navigate(self, url):
        url = unicode(url)
        self._send_w32_msg(DTM_NAVIGATE, 0, url)
        
    def set_zoom_level(self, level):
        if not level in range(5):
            raise TypeError, 'level must be in [0,1,2,3,4]'
        self._send_w32_msg(DTM_ZOOMLEVEL, 0, level)
        
    def set_value(self, html):
        self.clear()
        self._addtext(html)
        self._endofsource()
        
    def set_text(self, txt):
        self.clear()
        self._addtext(txt, True)
        self._endofsource()
    
    def clear(self):
        self._send_w32_msg(DTM_CLEAR)
        
    def enablecontextmenu(self, val=True):
        self._send_w32_msg(DTM_ENABLECONTEXTMENU, 0,  MAKELPARAM(0,int(val)))
        
    def enableshrink(self, val=True):
        self._send_w32_msg(DTM_ENABLESHRINK, 0,  MAKELPARAM(0,int(val))) 
    
def _InitHTMLControl():
    cdll.htmlview.InitHTMLControl(GetModuleHandle(0))
    
#_InitHTMLControl()

########NEW FILE########
__FILENAME__ = imagelist
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE


from os.path import abspath
from ppygui.core import *
from ppygui.w32comctl import *

LoadImageW = windll.user32.LoadImageW
def SHLoadDIBitmap(path):
    return LoadImageW(0, unicode(path), 0, 0,0,0x10)

class ImageList(GuiObject):
    def __init__(self, width, height, flags=1):
        self._hImageList = ImageList_Create(width, height, flags, 0, 1)
        
    def add(self, image, colormask=(255,255,255)):
        # WM >= 5.0 only
        # Pocket PC 2003 ImageList_Add function
        # handles DDB only.
        hbmp = SHLoadDIBitmap(abspath(image))
        crmask = rgb(*colormask)
        ImageList_AddMasked(self._hImageList, hbmp, UINT(crmask))
        DeleteObject(hbmp)
        
    def add_from_resource(self, resource_dll, icons, cx, cy, flags=0):
        LoadLibrary(unicode(resource_dll))
        hdll = GetModuleHandle(unicode(resource_dll))
        for i in icons:
            hIcon = LoadImage(hdll, i, IMAGE_ICON, cx, cy, flags)
            ImageList_AddIcon(self._hImageList, hIcon)
            
            
    def __del__(self):
        ImageList_Destroy(self._hImageList)    

def list_icons(dll):
    LoadLibrary(unicode(dll))
    hdll = GetModuleHandle(unicode(dll))
    for i in range(500):
        try:
            hIcon = LoadImage(hdll, i, IMAGE_ICON, 32, 32, 0)
            print i
        except:

            pass

########NEW FILE########
__FILENAME__ = line
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *

class HLine(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.bind(paint=self.on_paint)
        
    def on_paint(self, event):
        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._w32_hWnd, byref(ps))
        rc = self.client_rect
        r, b =  rc.right, rc.bottom
        hpen = CreatePen(0, 2, 0)
        SelectObject(hdc, hpen)
        line = (POINT*2)()
        line[0].x = 0
        line[0].y = b/2
        line[1].x = r
        line[1].y = b/2
        
        Polyline(hdc, line, 2)
        EndPaint(self._w32_hWnd, byref(ps))
        
    def get_best_size(self):
        return None, 1
        
class VLine(Window):
    def __init__(self, parent):
        Window.__init__(self, parent)
        self.bind(paint=self.on_paint)
        
    def on_paint(self, event):
        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._w32_hWnd, byref(ps))
        rc = self.client_rect
        r, b =  rc.right, rc.bottom
        hpen = CreatePen(0, 2, 0)
        SelectObject(hdc, hpen)
        
        line = (POINT*2)()
        line[0].x = r/2
        line[0].y = 0
        line[1].x = r/2
        line[1].y = b
        
        Polyline(hdc, line, 2)
        EndPaint(self._w32_hWnd, byref(ps))
        DeleteObject(hpen)
        
    def get_best_size(self):
        return 1, None
########NEW FILE########
__FILENAME__ = menu
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *

class AbstractMenuBase(GuiObject):
    
    def __init__(self):
        if type(self) == AbstractMenuBase :
            raise TypeError("Cannot instantiate an abstract class") 
        self._hmenu = self._create_menu()
        self._items = []
        
    def get_count(self):
        return len(self._items)
        
    def append(self, text, callback=None, enabled=True):
        new_id = IdGenerator.next()
        item = MenuItem(self, new_id)
        AppendMenu(self._hmenu, MF_STRING, new_id, unicode(text))
        item.enable(enabled)
        item.bind(callback)
        self._items.append(item)
        return item
        
    def append_menu(self, text, menu):
        if not isinstance(menu, AbstractMenuBase):
            raise TypeError("arg 1 must be an instance of a subclass of AbstractMenuBase")
        if self._hmenu == menu._hmenu :
            raise ValueError("a menu cannot contain itself")
        AppendMenu(self._hmenu, MF_POPUP, menu._hmenu, unicode(text))
        self._items.append(menu)    
        
    def append_separator(self):
        AppendMenu(self._hmenu, MF_SEPARATOR, 0,0)
        
    def insert(self, i, text, enabled=True):
        pass
        
    def insert_menu(self, i, menu):
        pass
        
    def insert_separator(self, i):
        pass
        
    def __getitem__(self, i):
        return self._items[i]
        
    def __delitem__(self, i):
        if not 0 <=i<self.count:
            raise IndexError 
        #RemoveMenu(self._hmenu, MF_BYPOSITION, i) 
        del self._items[i]
        
    def destroy(self):
        del self._items[:]
        DestroyMenu(self._hmenu)
        
    def __del__(self, ):
        print "del Menu(%i)" %self._hmenu
    
class MenuWrapper(AbstractMenuBase):
    def __init__(self, hmenu):
        self._hmenu = hmenu
        self._items = []
            
class Menu(AbstractMenuBase):
    def _create_menu(self):
        return CreateMenu()
        
class PopupMenu(AbstractMenuBase):
    def _create_menu(self):
        return CreatePopupMenu()
        
    def popup(self, win, x, y):
        return TrackPopupMenuEx(self._hmenu, 0, x, y, win._w32_hWnd, 0)

    
class MenuItem(GuiObject):
    
    def __init__(self, menu, id):
        self._menu = menu
        self._id = id
        self._cmdmap = EventDispatchersMap()
        dispatcher = CMDEventDispatcher(self)
        self._cmdmap["clicked"] = dispatcher
        
    def enable(self, value=True):
        if value :
            EnableMenuItem(self._menu._hmenu, self._id, MF_ENABLED)
        else :
            EnableMenuItem(self._menu._hmenu, self._id, MF_GRAYED)
            
    def disable(self):
        self.enable(False)
        
    def check(self, value=True):
        if value :
            CheckMenuItem(self._menu._hmenu, self._id, MF_CHECKED)
        else :
            CheckMenuItem(self._menu._hmenu, self._id, MF_UNCHECKED)
            
    def uncheck(self):
        self.check(False)
        
    def bind(self, callback):
        self._cmdmap["clicked"].bind(callback)
        
    def __del__(self):
        IdGenerator.reuseid(self._id)
        print "del MenuItem(%i)" %self._id
        
def recon_context(win, event):
    shi = SHRGINFO()
    shi.cbSize = sizeof(SHRGINFO) 
    shi.hwndClient = win._w32_hWnd
    shi.ptDown = POINT(*event.position)
    shi.dwFlags = SHRG_RETURNCMD
    if SHRecognizeGesture(byref(shi)) == GN_CONTEXTMENU :
        return True
    return False 
    
def context_menu(win, event, popmenu):
    rc = win.window_rect
    x, y = event.position
    return popmenu.popup(win, x+rc.left, y+rc.top)
    
########NEW FILE########
__FILENAME__ = message
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *

class Message(object):
    
    @classmethod
    def _makeiconstyle(cls, icon):
        assert icon in ['info', 'question', 'warning', 'error']
        if icon == 'info' :
            return MB_ICONASTERISK
        elif icon == 'question':
            return MB_ICONQUESTION
        elif icon == 'warning':
            return MB_ICONWARNING
        elif icon == 'error':
            return MB_ICONERROR
    
    @classmethod
    def _messagebox(cls, title, caption, style, parent=None):
        if not parent :
            hwnd = 0
        else :
            hwnd = parent._w32_hWnd
            
        return MessageBox(hwnd, unicode(caption), unicode(title), style)
        
    @classmethod
    def ok(cls, title, caption, icon='info', parent=None):
        style = MB_OK
        style |= cls._makeiconstyle(icon)
        cls._messagebox(title, caption, style, parent)
        return 'ok'
        
    @classmethod
    def okcancel(cls, title, caption, icon='info', parent=None):
        style = MB_OKCANCEL
        style |= cls._makeiconstyle(icon)
        res = cls._messagebox(title, caption, style, parent)
        if res == IDOK :
            return 'ok'
        else :
            return 'cancel'
    
    @classmethod        
    def yesno(cls, title, caption, icon='info', parent=None):
        style = MB_YESNO
        style |= cls._makeiconstyle(icon)
        res = cls._messagebox(title, caption, style, parent)
        if res == IDYES :
            return 'yes'
        else : 
            return 'no'
        
    @classmethod        
    def yesnocancel(cls, title, caption, icon='info', parent=None):
        style = MB_YESNOCANCEL
        style |= cls._makeiconstyle(icon)
        res = cls._messagebox(title, caption, style, parent)
        if res == IDYES :
            return 'yes'
        elif res == IDNO : 
            return 'no'
        else :
            return 'cancel'

########NEW FILE########
__FILENAME__ = sizer
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import *
from config import HIRES

__all__ = ['Sizer', 'HSizer', 'VSizer']

class BlankBox:
  '''
  An empty space that you can 
  put in a BoxSizer
  '''
  def size(self, l, t, r, b):
    pass
    
class Box:
    '''
    A box that holds a window.
    It should not be used directly, but it is used 
    when you pass a window to the append 
    method of a BoxSizer.
    '''
    def __init__(self, window, border):
        self.window = window 
        self.border = border
        assert len(border) == 4
    
    def size(self, l, t, r, b):
        l += self.border[0]
        t += self.border[1]
        r -= self.border[2]
        b -= self.border[3]
        w = r-l
        h = b-t
        self.window.move(l, t, w, h)
    
    def get_best_size(self):
        return self.window.get_best_size()
  
class Sizer:
  
  '''
  The base class of the layout system.
  You can append a Window, blank space or another Sizer with a given proportion 
  or a fixed dimension.
  '''
  
  def __init__(self, orientation, border=(0, 0, 0, 0), spacing=0):
    
    '''
    Arguments:
        - orientation: must be 'vertical' or 'horizontal'
        - border: a 4 elements tuple (left, top, bottom, right)
        - spacing: the space in pixels between elements
    '''
    
    self.boxes = []
    self.totalcoeff = 0
    self.totalfixedsize = 0
    if HIRES :
      border = tuple(2*val for val in border)
    self.border = border
    
    assert orientation in ['horizontal', 'vertical']
    self.orientation = orientation
    self.spacing = spacing
    
  def add(self, box, coeff=1, border=(0, 0, 0, 0)):
    '''
    Appends a Window or another Sizer to the Sizer. 
    Arguments:
        - box: the element to add, it must be an instance of Window or Sizer.
        - coeff: represents the proportion of the sizer that will occupy the element.
        - border: a 4 elements tuple (left, top, bottom, right)
    ''' 
    
    if isinstance(box, Window):
      if HIRES :
        border = tuple(2*val for val in border)
      data = [Box(box, border), coeff]
    elif isinstance(box, (BlankBox, Sizer)):
      data = [box, coeff]
    else :
      raise TypeError("arg 1 must be an instance of Window, BlankBox or BoxSizer")
    
    
    if coeff == 0:
        b_x, b_y = box.get_best_size()
        if self.orientation == 'vertical':
            if not b_y:
                return self.add(box, 1, border)
            else:
                return self.addf(box, b_y, border)
        elif self.orientation == 'horizontal':
            if not b_x:
                return self.add(box, 1, border)
            else:
                return self.addf(box, b_x, border)
                
            
    elif coeff > 0 :
      self.totalcoeff += coeff
    else :
      if HIRES:
        coeff *= 2
        data[1] = coeff
      self.totalfixedsize -= coeff
      
    if self.boxes and self.spacing:
        space = self.spacing
        if HIRES:
            space *= 2
        self.boxes.append((BlankBox(), -space))
        self.totalfixedsize += space
        
    self.boxes.append(data)
  
  def addspace(self, coeff=1, border=(0,0,0,0)):
    '''\
    Appends a blank space to the Sizer, 
    Arguments:
        - coeff: represents the proportion of the sizer that will occupy the space.
        - border: a 4 elements tuple (left, top, bottom, right)
    '''
    self.add(BlankBox(), coeff, border)
    
  def addfixed(self, box, dim=20, border=(0,0,0,0)):
    '''
    Appends a Window, another Sizer to the Sizer, 
    Arguments :
        - box: the element to add, it must be an instance of Window or Sizer.
        - dim: represents the size in pixel that will occupy the element.
        - border: a 4 elements tuple (left, top, bottom, right)
    ''' 
    self.add(box, -dim, border)
  
  addf = addfixed
    
  def addfixedspace(self, dim=20, border=(0,0,0,0)):
    '''\
    Appends a blank space to the Sizer, 
    Arguments:
        - dim: represents the size in pixel that will occupy the space.
        - border: a 4 elements tuple (left, top, bottom, right)
    '''
    self.addspace(-dim, border)
  
  addfspace = addfixedspace
  
  def size(self, l, t, r, b):
    
    l += self.border[0]
    t += self.border[1]
    r -= self.border[2]
    b -= self.border[3]
    sizerw = r - l
    sizerh = b - t
    hoffset = l
    voffset = t
    for data in self.boxes:
      box, coeff = data
      if self.orientation == 'vertical' :
        w = sizerw
        if coeff > 0 :
          h = (sizerh - self.totalfixedsize) * coeff / self.totalcoeff
        else : 
          h = -coeff
        box.size(hoffset, voffset, hoffset+w, voffset+h)
        voffset += h
      elif self.orientation == 'horizontal' :
        if coeff > 0 :
          w = (sizerw - self.totalfixedsize) * coeff / self.totalcoeff
        else :
          w = -coeff
        h = sizerh 
        box.size(hoffset, voffset, hoffset+w, voffset+h)
        hoffset += w

  def move(self, l, t, w, h):
    self.size(l, t, l+w, t+h)
    
class HSizer(Sizer):
  
    def __init__(self, border=(0, 0, 0, 0), spacing=0):
        Sizer.__init__(self, 'horizontal', border, spacing)
        
    def get_best_size(self):
        h_expand = False
        v_expand = False
        
        b_x = 0
        b_y = 0
        for box, coeff in self.boxes:
            cx, cy =  box.get_best_size()
            if cx is None:
                h_expand = True
            else:
                b_x += cx
            if cy is None:
                v_expand = True
            else:
                if cy > b_y:
                    b_y = cy
                    
        if h_expand:
            b_x = None
        if v_expand:
            b_y = None  
        return b_x, b_y
            
class VSizer(Sizer):
  
    def __init__(self, border=(0, 0, 0, 0), spacing=0):
        Sizer.__init__(self, 'vertical', border, spacing)
  
    def get_best_size(self):
        h_expand = False
        v_expand = False
        
        b_x = 0
        b_y = 0
        for box, coeff in self.boxes:
            
            cx, cy =  box.get_best_size()
            print cx, cy
            if cx is None:
                h_expand = True
            else:
                if cx > b_x:
                    b_x = cx
            if cy is None:
                v_expand = True
            else:
                b_y += cy
                    
        if h_expand:
            b_x = None
        if v_expand:
            b_y = None  
        return b_x, b_y

########NEW FILE########
__FILENAME__ = spin
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from core import Frame, CustomEventDispatcher, \
    GetDC, SelectObject, GetTextExtent, CustomEvent
from config import HIRES_MULT
from controls import Edit, UpDown
from boxing import HBox

class Spin(Frame):
    _dispatchers = {'update' : (CustomEventDispatcher,)}
    _dispatchers.update(Frame._dispatchers)
    
    def __init__(self, parent, range=(0,100), visible=True, enabled=True, **kw):
        Frame.__init__(self, parent, visible=visible, enabled=enabled)
        self._buddy = Edit(self)
        self._ud = UpDown(self)
        self._ud.buddy = self._buddy
        
        self._buddy.bind(update=self._on_edit_update)
        
        sizer = HBox(spacing=-1)
        sizer.add(self._buddy)
        sizer.add(self._ud)
        self.sizer = sizer
        self.set(range=range, **kw)
        self._best_size = None
    
    def get_value(self):
        return self._ud._get_pos()
        
    def set_value(self, val):
        if not self._low <= val <= self._high:
            raise ValueError('Invalid value retrieved by the spin control')
        self._ud._set_pos(val)    
        

    doc_value = 'The displayed int in range'
        
    def _on_edit_update(self, event):
        self.events['update'].call(CustomEvent(self))
        
    def get_range(self):
        return self._low, self._high
        
    def set_range(self, rg):
        self._low, self._high = rg
        self._ud.range = rg
        self._best_size = None
        
    doc_range = 'The range of valid ints as a tuple (low, high)'
        
    def _get_best_size(self):
        #return self.sizer.get_best_size()
        dc = GetDC(self._w32_hWnd)
        font = self._buddy._font._hFont
        SelectObject(dc, font)
        cx, cy = GetTextExtent(dc, str(self._high))
        return 20 + cx/HIRES_MULT, 7+cy/HIRES_MULT

########NEW FILE########
__FILENAME__ = toolbar
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

import os
from ppygui.core import *
from ppygui.w32comctl import *
from config import HIRES_MULT
#SHLoadDIBitmap = windll.coredll.SHLoadDIBitmap
#SHLoadDIBitmap.argtypes = [LPWSTR]
LoadImageW = windll.user32.LoadImageW

def SHLoadDIBitmap(path):
    return LoadImageW(0, unicode(path), 0, 0,0,0x10)
    

TBSTATE_ENABLED = 0x4
CCS_NOPARENTALIGN = 0x8

class BITMAP(Structure):
    _fields_ = [("bmType", LONG),
    		("bmWidth", LONG),
    		("bmHeight", LONG),
    		("bmWidthBytes", LONG),
    		("bmPlanes", WORD),
    		("bmBitsPixel", WORD),
    		("bmBits", LPVOID)]
            
class TBADDBITMAP(Structure):
    _fields_ = [('hInst', HINSTANCE),
                ('nID', INT),]
                
class ToolBar(Window):
    _w32_window_class = "ToolbarWindow32"
    _w32_window_style = WS_CHILD | WS_VISIBLE | CCS_NOPARENTALIGN
                
    def __init__(self, *args, **kw):
        Window.__init__(self, *args, **kw)
        self._buttons = []
        
    def set_imagelist(self, il):
        self._il = il
        self._send_w32_msg(TB_SETIMAGELIST, 0, il._hImageList)
            
    def add_bitmap(self, path, n=1):
        path = os.path.abspath(path)
        path = unicode(path)
        if not os.path.exists(path):
            raise ValueError('Invalid path')
        hbmp = SHLoadDIBitmap(path)
        tbab = TBADDBITMAP(NULL, hbmp)
        self._send_w32_msg(TB_ADDBITMAP, n, byref(tbab))
        
    def add_standard_bitmaps(self):
        tbab = TBADDBITMAP(0xFFFFFFFF, 0)
        self._send_w32_msg(TB_ADDBITMAP, 1, byref(tbab))
        
    def add_button(self, image=0, enabled=True, style='button', action=None):
        tbb = TBBUTTON()
        tbb.iBitmap = image
        if enabled:
            tbb.fsState |= TBSTATE_ENABLED
        if style == 'check':
            tbb.fsStyle = 0x2
        elif style == 'group':
            tbb.fsStyle = 0x2|0x4
        elif style == 'separator':
            tbb.fsStyle = 0x1
        elif style != 'button':
            raise ValueError("%s is not a valid style" %style)
        
        id = IdGenerator.next()
        tbb.idCommand = id
        self._send_w32_msg(TB_BUTTONSTRUCTSIZE, sizeof(TBBUTTON))
        self._send_w32_msg(TB_ADDBUTTONS, 1, byref(tbb))
        button = ToolBarButton(self, id)
        if action is not None:
            button.bind(action)
        self._buttons.append(button)
        
    def get_count(self):
        return len(self._buttons)
        
    def __getitem__(self, i):
        return self._buttons[i]
        
    def __delitem__(self, i):
        if not 0 <= i < self.count:
            raise IndexError(i)
        self._send_w32_msg(TB_DELETEBUTTON, i)
        del self._buttons[i]
        
    def get_best_size(self):
        return None, 24*HIRES_MULT
    
    def move(self, l, t, w, h):
        Window.move(self, l, t-2*HIRES_MULT, w, h+2*HIRES_MULT)
            
class ToolBarButton(GuiObject):
    def __init__(self, toolbar, id):
        self._id = id
        self.toolbar = toolbar
        self._cmdmap = EventDispatchersMap()
        dispatcher = CMDEventDispatcher(self)
        self._cmdmap["clicked"] = dispatcher
        
    def bind(self, callback):
        self._cmdmap["clicked"].bind(callback)
        
    def enable(self, enabled=True):
        self.toolbar._send_w32_msg(TB_ENABLEBUTTON, self._id, MAKELONG(bool(enabled), 0))
        
    def disable(self):
        self.enable(False)
        
    def get_checked(self):
        return bool(self.toolbar._send_w32_msg(TB_ISBUTTONCHECKED, self._id))
        
    def set_checked(self, check):
        self.toolbar._send_w32_msg(TB_CHECKBUTTON, self._id, MAKELONG(bool(check), 0))
        
    

########NEW FILE########
__FILENAME__ = utils
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from ctypes import cdll
import sys

if sys.version_info[0:2] == (2, 4):
    pythonDll = cdll.python24
elif sys.version_info[0:2] == (2, 5):
    pythonDll = cdll.python25
    
def _as_pointer(obj):
    "Increment the refcount of obj, and return a pointer to it"
    ptr = pythonDll.Py_BuildValue("O", id(obj))
    assert ptr == id(obj)
    return ptr

def _from_pointer(ptr):
    if ptr != 0 :
        "Convert a pointer to a Python object, and decrement the refcount of the ptr"
        l = [None]
        # PyList_SetItem consumes a refcount of its 3. argument
        pythonDll.PyList_SetItem(id(l), 0, ptr)
        return l[0]
    else :
        raise ValueError
########NEW FILE########
__FILENAME__ = w32api
## 	   Copyright (c) 2006-2008 Alexandre Delattre
## 	   Copyright (c) 2003 Henk Punt

## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from ctypes import *

#TODO auto ie/comctl detection
WIN32_IE = 0x0550

#TODO: auto unicode selection,
#if unicode:
#  CreateWindowEx = windll.coredll.CreateWindowExW
#else:
#  CreateWindowEx = windll.coredll.CreateWindowExA
#etc, etc


DWORD = c_ulong
HANDLE = c_ulong
UINT = c_uint
BOOL = c_int
HWND = HANDLE
HINSTANCE = HANDLE
HICON = HANDLE
HDC = HANDLE
HCURSOR = HANDLE
HBRUSH = HANDLE
HMENU = HANDLE
HBITMAP = HANDLE
HIMAGELIST = HANDLE
HGDIOBJ = HANDLE
HMETAFILE = HANDLE

ULONG = DWORD
ULONG_PTR = DWORD
UINT_PTR = DWORD
LONG_PTR = DWORD
INT = c_int
LPCTSTR = c_wchar_p
LPTSTR = c_wchar_p
PSTR = c_char_p
LPCSTR = c_char_p
LPCWSTR = c_wchar_p
LPSTR = c_char_p
LPWSTR = c_wchar_p
PVOID = c_void_p
USHORT = c_ushort
WORD = c_ushort
ATOM = WORD
SHORT = c_short
LPARAM = c_ulong
WPARAM = c_uint
LPVOID = c_voidp
LONG = c_long
BYTE = c_byte
TCHAR = c_wchar #TODO depends on unicode/wide conventions
DWORD_PTR = c_ulong #TODO what is this exactly?
INT_PTR = c_ulong  #TODO what is this exactly?
COLORREF = c_ulong
CLIPFORMAT = WORD
FLOAT = c_float
CHAR = c_char
WCHAR = c_wchar

FXPT16DOT16 = c_long
FXPT2DOT30 = c_long
LCSCSTYPE = c_long
LCSGAMUTMATCH = c_long
COLOR16 = USHORT

LRESULT = LONG_PTR

#### Windows version detection ##############################
class OSVERSIONINFO(Structure):
    _fields_ = [("dwOSVersionInfoSize", DWORD),
                ("dwMajorVersion", DWORD),
                ("dwMinorVersion", DWORD),
                ("dwBuildNumber", DWORD),
                ("dwPlatformId", DWORD),
                ("szCSDVersion", TCHAR * 128)]

    def isMajorMinor(self, major, minor):
        return (self.dwMajorVersion, self.dwMinorVersion) == (major, minor)
    
GetVersion = windll.kernel32.GetVersionExW
versionInfo = OSVERSIONINFO()
versionInfo.dwOSVersionInfoSize = sizeof(versionInfo)
GetVersion(byref(versionInfo))

def MAKELONG(w1, w2):
    return w1 | (w2 << 16)

MAKELPARAM = MAKELONG

def RGB(r,g,b):
    return r | (g<<8) | (b<<16)

##### Windows Callback functions ################################
WNDPROC = WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)
DialogProc = WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)

CBTProc = WINFUNCTYPE(c_int, c_int, c_int, c_int)
MessageProc = CBTProc

EnumChildProc = WINFUNCTYPE(c_int, HWND, LPARAM)

MSGBOXCALLBACK = WINFUNCTYPE(c_int, HWND, LPARAM) #TODO look up real def

class WNDCLASS(Structure):
    _fields_ = [
                ("style",  UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", INT),
                ("cbWndExtra", INT),
                ("hInstance", HINSTANCE),
                ("hIcon", HICON),
                ("hCursor", HCURSOR),
                ("hbrBackground", HBRUSH),
                ("lpszMenuName", LPCTSTR),
                ("lpszClassName", LPCTSTR),
                ]

class POINT(Structure):
    _fields_ = [("x", LONG),
                ("y", LONG)]

    def __str__(self):
        return "POINT {x: %d, y: %d}" % (self.x, self.y)

POINTL = POINT

class POINTS(Structure):
    _fields_ = [("x", SHORT),
                ("y", SHORT)]
    

PtInRect = windll.user32.PtInRect

class RECT(Structure):
    _fields_ = [("left", LONG),
                ("top", LONG),
                ("right", LONG),
                ("bottom", LONG)]

    def __str__(self):
        return "RECT {left: %d, top: %d, right: %d, bottom: %d}" % (self.left, self.top,
                                                                    self.right, self.bottom)

    def getHeight(self):
        return self.bottom - self.top

    height = property(getHeight, None, None, "")

    def getWidth(self):
        return self.right - self.left

    width = property(getWidth, None, None, "")

    def getSize(self):
        return self.width, self.height

    size = property(getSize, None, None, "")
    
    def ContainsPoint(self, pt):
        """determines if this RECT contains the given POINT pt
        returns True if pt is in this rect
        """
        return bool(PtInRect(byref(self), pt))
        
RECTL = RECT        

class SIZE(Structure):
    _fields_ = [('cx', LONG),
                ('cy', LONG)]
        
SIZEL = SIZE        
        
    
##class MSG(Structure):
##    _fields_ = [("hWnd", HWND),
##                ("message", UINT),
##                ("wParam", WPARAM),
##                ("lParam", LPARAM),
##                ("time", DWORD),
##                ("pt", POINT)]

##    def __str__(self):
##        return "MSG {%d %d %d %d %d %s}" % (self.hWnd, self.message, self.wParam, self.lParam,
##                                            self.time, str(self.pt))

#Hack: we need to use the same MSG type as ctypes.com.ole uses!
from ctypes.wintypes import MSG
        
class ACCEL(Structure):
    _fields_ = [("fVirt", BYTE),
                ("key", WORD),
                ("cmd", WORD)]
    
class CREATESTRUCT(Structure):
    _fields_ = [("lpCreateParams", LPVOID),
                ("hInstance", HINSTANCE),
                ("hMenu", HMENU),
                ("hwndParent", HWND),
                ("cx", INT),
                ("cy", INT),
                ("x", INT),
                ("y", INT),
                ("style", LONG),
                ("lpszName", LPCTSTR),
                ("lpszClass", LPCTSTR),
                ("dwExStyle", DWORD)]



class NMHDR(Structure):
    _fields_ = [("hwndFrom", HWND),
                ("idFrom", UINT),
                ("code", UINT)]

class PAINTSTRUCT(Structure):
    _fields_ = [("hdc", HDC),
                ("fErase", BOOL),
                ("rcPaint", RECT),
                ("fRestore", BOOL),
                ("fIncUpdate", BOOL),
                ("rgbReserved", c_char * 32)]

    
class MENUITEMINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("fMask", UINT),
                ("fType", UINT),
                ("fState", UINT),                
                ("wID", UINT),
                ("hSubMenu", HMENU),
                ("hbmpChecked", HBITMAP),
                ("hbmpUnchecked", HBITMAP),
                ("dwItemData", ULONG_PTR),
                ("dwTypeData", LPTSTR),                
                ("cch", UINT),
                ("hbmpItem", HBITMAP)]

class DLGTEMPLATE(Structure):
    _pack_ = 2
    _fields_ = [
        ("style", DWORD),
        ("exStyle", DWORD),
        ("cDlgItems", WORD),
        ("x", c_short),
        ("y", c_short),
        ("cx", c_short),
        ("cy", c_short)
    ]

class DLGITEMTEMPLATE(Structure):
    _pack_ = 2
    _fields_ = [
        ("style", DWORD),
        ("exStyle", DWORD),
        ("x", c_short),
        ("y", c_short),
        ("cx", c_short),
        ("cy", c_short),
        ("id", WORD)
    ]

class COPYDATASTRUCT(Structure):
    _fields_ = [
        ("dwData", ULONG_PTR),
        ("cbData", DWORD),
        ("lpData", PVOID)]
    
def LOWORD(dword):
    return dword & 0x0000ffff

def HIWORD(dword):
    return dword >> 16

TRUE = 1
FALSE = 0
NULL = 0

IDI_APPLICATION = 32512

SW_SHOW = 5
SW_SHOWNORMAL = 1
SW_HIDE = 0

EN_CHANGE = 768

MSGS = [('WM_NULL', 0),
        ('WM_CREATE', 1),
        ('WM_CANCELMODE', 31),
        ('WM_CAPTURECHANGED', 533),
        ('WM_CLOSE', 16),
        ('WM_COMMAND', 273),
        ('WM_DESTROY', 2),
        ('WM_ERASEBKGND', 20),
        ('WM_ENABLE', 0xa),
        ('WM_GETFONT', 49),
        ('WM_INITDIALOG', 272),
        ('WM_INITMENUPOPUP', 279),
        ('WM_KEYDOWN', 256),
        ('WM_KEYFIRST', 256),
        ('WM_KEYLAST', 264),
        ('WM_KEYUP', 257),
        ('WM_LBUTTONDBLCLK', 515),
        ('WM_LBUTTONDOWN', 513),
        ('WM_LBUTTONUP', 514),
        ('WM_MBUTTONDBLCLK', 521),
        ('WM_MBUTTONDOWN', 519),
        ('WM_MBUTTONUP', 520),
        ('WM_MENUSELECT', 287),
        ('WM_MOUSEFIRST', 512),
        ('WM_MOUSEHOVER', 673),
        ('WM_MOUSELEAVE', 675),
        ('WM_MOUSEMOVE', 512),
        ('WM_MOVE', 3),
        ('WM_NCCREATE', 129),
        ('WM_NCDESTROY', 130),
        ('WM_NOTIFY', 78),
        ('WM_PAINT', 15),
        ('WM_RBUTTONDBLCLK', 518),
        ('WM_RBUTTONDOWN', 516),
        ('WM_RBUTTONUP', 517),
        ('WM_SETCURSOR', 32),
        ('WM_SETFONT', 48),
        ('WM_SETREDRAW', 11),
        ('WM_SIZE', 5),
        ('WM_SYSKEYDOWN', 260),
        ('WM_SYSKEYUP', 261),
        ('WM_USER', 1024),
        ('WM_WINDOWPOSCHANGED', 71),
        ('WM_WINDOWPOSCHANGING', 70),
        ('WM_SETTEXT', 12),
        ('WM_GETTEXT', 13),
        ('WM_GETTEXTLENGTH', 14),
        ('WM_ACTIVATE', 6),
        ('WM_HSCROLL', 276),
        ('WM_VSCROLL', 277),
        ('WM_CTLCOLORBTN', 309),
        ('WM_CTLCOLORDLG', 310),
        ('WM_CTLCOLOREDIT', 307),
        ('WM_CTLCOLORLISTBOX', 308),
        ('WM_CTLCOLORMSGBOX', 306),
        ('WM_CTLCOLORSCROLLBAR', 311),
        ('WM_CTLCOLORSTATIC', 312),
        ('WM_TIMER', 0x0113),
        ('WM_CONTEXTMENU', 0x007B),
        ('WM_COPYDATA', 0x004A),
        ('WM_SETTINGCHANGE', 0x001A),
        ('WM_SETFOCUS', 0x7),
        ('WM_CHAR', 0x102),
        ]
        
WM_CUT = 0x300
WM_COPY = 0x301
WM_PASTE = 0x302

#insert wm_* msgs as constants in this module:
for key, val in MSGS:
    exec('%s = %d' % (key, val)) #TODO without using 'exec'?

BN_CLICKED    =     0

VK_DOWN = 40
VK_LEFT = 37
VK_RIGHT = 39
VK_DELETE  = 0x2E

CS_HREDRAW = 2
CS_VREDRAW = 1
WHITE_BRUSH = 0

MIIM_STATE= 1
MIIM_ID= 2
MIIM_SUBMENU =4
MIIM_CHECKMARKS= 8
MIIM_TYPE= 16
MIIM_DATA= 32
MIIM_STRING= 64
MIIM_BITMAP= 128
MIIM_FTYPE =256

MFT_BITMAP= 4
MFT_MENUBARBREAK =32
MFT_MENUBREAK= 64
MFT_OWNERDRAW= 256
MFT_RADIOCHECK= 512
MFT_RIGHTJUSTIFY= 0x4000
MFT_SEPARATOR =0x800
MFT_RIGHTORDER= 0x2000L
MFT_STRING = 0

MF_ENABLED    =0
MF_GRAYED     =1
MF_DISABLED   =2
MF_BITMAP     =4
MF_CHECKED    =8
MF_MENUBARBREAK= 32
MF_MENUBREAK  =64
MF_OWNERDRAW  =256
MF_POPUP      =16
MF_SEPARATOR  =0x800
MF_STRING     =0
MF_UNCHECKED  =0
MF_DEFAULT    =4096
MF_SYSMENU    =0x2000
MF_HELP       =0x4000
MF_END        =128
MF_RIGHTJUSTIFY=       0x4000
MF_MOUSESELECT =       0x8000
MF_INSERT= 0
MF_CHANGE= 128
MF_APPEND= 256
MF_DELETE= 512
MF_REMOVE= 4096
MF_USECHECKBITMAPS= 512
MF_UNHILITE= 0
MF_HILITE= 128
MF_BYCOMMAND=  0
MF_BYPOSITION= 1024
MF_UNCHECKED=  0
MF_HILITE =    128
MF_UNHILITE =  0

LOCALE_SYSTEM_DEFAULT =  0x800

MFS_GRAYED        =  0x00000003L
MFS_DISABLED      =  MFS_GRAYED
MFS_CHECKED       =  MF_CHECKED
MFS_HILITE        =  MF_HILITE
MFS_ENABLED       =  MF_ENABLED
MFS_UNCHECKED     =  MF_UNCHECKED
MFS_UNHILITE      =  MF_UNHILITE
MFS_DEFAULT       =  MF_DEFAULT

WS_BORDER	= 0x800000
WS_CAPTION	= 0xc00000
WS_CHILD	= 0x40000000
WS_CHILDWINDOW	= 0x40000000
WS_CLIPCHILDREN = 0x2000000
WS_CLIPSIBLINGS = 0x4000000
WS_DISABLED	= 0x8000000
WS_DLGFRAME	= 0x400000
WS_GROUP	= 0x20000
WS_HSCROLL	= 0x100000
WS_ICONIC	= 0x20000000
WS_MAXIMIZE	= 0x1000000
WS_MAXIMIZEBOX	= 0x10000
WS_MINIMIZE	= 0x20000000
WS_MINIMIZEBOX	= 0x20000
WS_OVERLAPPED	= 0
WS_OVERLAPPEDWINDOW = 0xcf0000
WS_POPUP	= 0x80000000l
WS_POPUPWINDOW	= 0x80880000
WS_SIZEBOX	= 0x40000
WS_SYSMENU	= 0x80000
WS_TABSTOP	= 0x10000
WS_THICKFRAME	= 0x40000
WS_TILED	= 0
WS_TILEDWINDOW	= 0xcf0000
WS_VISIBLE	= 0x10000000
WS_VSCROLL	= 0x200000

WS_EX_TOOLWINDOW = 128
WS_EX_LEFT = 0
WS_EX_LTRREADING = 0
WS_EX_RIGHTSCROLLBAR = 0
WS_EX_WINDOWEDGE = 256
WS_EX_STATICEDGE = 0x20000
WS_EX_CLIENTEDGE = 512
WS_EX_OVERLAPPEDWINDOW   =     0x300
WS_EX_APPWINDOW    =   0x40000

WA_INACTIVE = 0
WA_ACTIVE = 1
WA_CLICKACTIVE = 2

RB_SETBARINFO = WM_USER + 4
RB_GETBANDCOUNT = WM_USER +  12
RB_INSERTBANDA = WM_USER + 1
RB_INSERTBANDW = WM_USER + 10

RB_INSERTBAND = RB_INSERTBANDA

RBBIM_STYLE = 1
RBBIM_COLORS = 2
RBBIM_TEXT = 4
RBBIM_IMAGE = 8
RBBIM_CHILD = 16
RBBIM_CHILDSIZE = 32
RBBIM_SIZE = 64
RBBIM_BACKGROUND = 128
RBBIM_ID = 256
RBBIM_IDEALSIZE = 0x00000200

TPM_CENTERALIGN =4
TPM_LEFTALIGN =0
TPM_RIGHTALIGN= 8
TPM_LEFTBUTTON= 0
TPM_RIGHTBUTTON= 2
TPM_HORIZONTAL= 0
TPM_VERTICAL= 64
TPM_TOPALIGN= 0
TPM_VCENTERALIGN= 16
TPM_BOTTOMALIGN= 32
TPM_NONOTIFY= 128
TPM_RETURNCMD= 256

TBIF_TEXT = 0x00000002

DT_NOPREFIX   =      0x00000800
DT_HIDEPREFIX =      1048576

WH_CBT       =  5
WH_MSGFILTER =  (-1)

I_IMAGENONE = -2
TBSTATE_ENABLED = 4

BTNS_SHOWTEXT = 0x00000040
CW_USEDEFAULT = 0x80000000

COLOR_3DFACE = 15

BF_LEFT      = 1
BF_TOP       = 2
BF_RIGHT     = 4
BF_BOTTOM    = 8

BDR_RAISEDOUTER =      1
BDR_SUNKENOUTER =      2
BDR_RAISEDINNER =      4
BDR_SUNKENINNER =      8
BDR_OUTER    = 3
BDR_INNER    = 0xc
BDR_RAISED   = 5
BDR_SUNKEN   = 10

EDGE_RAISED  = (BDR_RAISEDOUTER|BDR_RAISEDINNER)
EDGE_SUNKEN  = (BDR_SUNKENOUTER|BDR_SUNKENINNER)
EDGE_ETCHED  = (BDR_SUNKENOUTER|BDR_RAISEDINNER)
EDGE_BUMP    = (BDR_RAISEDOUTER|BDR_SUNKENINNER)

IDC_SIZENWSE = 32642
IDC_SIZENESW = 32643
IDC_SIZEWE = 32644
IDC_SIZENS = 32645
IDC_SIZEALL = 32646
IDC_SIZE = 32640
IDC_ARROW = 32512

TCIF_TEXT    =1
TCIF_IMAGE   =2
TCIF_RTLREADING=      4
TCIF_PARAM  = 8


TCS_MULTILINE = 512

MK_LBUTTON    = 1
MK_RBUTTON    = 2
MK_SHIFT      = 4
MK_CONTROL    = 8
MK_MBUTTON    = 16

ILC_COLOR = 0
ILC_COLOR4 = 4
ILC_COLOR8 = 8
ILC_COLOR16 = 16
ILC_COLOR24 = 24
ILC_COLOR32 = 32
ILC_COLORDDB = 254
ILC_MASK = 1
ILC_PALETTE = 2048

IMAGE_BITMAP = 0
IMAGE_ICON = 1

LR_LOADFROMFILE = 16
LR_VGACOLOR = 0x0080
LR_LOADMAP3DCOLORS = 4096
LR_LOADTRANSPARENT = 32

LVSIL_NORMAL = 0
LVSIL_SMALL  = 1
LVSIL_STATE  = 2

TVSIL_NORMAL = 0
TVSIL_STATE  = 2

SRCCOPY = 0xCC0020

GWL_WNDPROC = -4

HWND_BOTTOM = 1
HWND_TOP=0
HWND_TOPMOST=-1

SWP_DRAWFRAME= 32
SWP_FRAMECHANGED= 32
SWP_HIDEWINDOW= 128
SWP_NOACTIVATE= 16
SWP_NOCOPYBITS= 256
SWP_NOMOVE= 2
SWP_NOSIZE= 1
SWP_NOREDRAW= 8
SWP_NOZORDER= 4
SWP_SHOWWINDOW= 64
SWP_NOOWNERZORDER =512
SWP_NOREPOSITION= 512
SWP_NOSENDCHANGING= 1024
SWP_DEFERERASE= 8192
SWP_ASYNCWINDOWPOS=  16384

DCX_WINDOW = 1
DCX_CACHE = 2
DCX_PARENTCLIP = 32
DCX_CLIPSIBLINGS= 16
DCX_CLIPCHILDREN= 8
DCX_NORESETATTRS= 4
DCX_LOCKWINDOWUPDATE= 0x400
DCX_EXCLUDERGN= 64
DCX_INTERSECTRGN =128
DCX_VALIDATE= 0x200000

GCL_STYLE = -26

SB_HORZ       =      0
SB_VERT       =      1
SB_CTL        =      2
SB_BOTH       =      3

SB_LINEUP           =0
SB_LINELEFT         =0
SB_LINEDOWN         =1
SB_LINERIGHT        =1
SB_PAGEUP           =2
SB_PAGELEFT         =2
SB_PAGEDOWN         =3
SB_PAGERIGHT        =3
SB_THUMBPOSITION    =4
SB_THUMBTRACK       =5
SB_TOP              =6
SB_LEFT             =6
SB_BOTTOM           =7
SB_RIGHT            =7
SB_ENDSCROLL        =8

MB_OK                    =   0x00000000
MB_OKCANCEL              =   0x00000001
MB_ABORTRETRYIGNORE      =   0x00000002
MB_YESNOCANCEL           =   0x00000003
MB_YESNO                 =   0x00000004
MB_RETRYCANCEL           =   0x00000005


MB_ICONASTERISK = 64
MB_ICONEXCLAMATION= 0x30
MB_ICONWARNING= 0x30
MB_ICONERROR= 16
MB_ICONHAND= 16
MB_ICONQUESTION= 32
MB_ICONINFORMATION= 64
MB_ICONSTOP= 16
MB_ICONMASK= 240

IDOK          =      1
IDCANCEL      =      2
IDABORT       =      3
IDRETRY       =      4
IDIGNORE      =      5
IDYES         =      6
IDNO          =      7
IDCLOSE       =  8
IDHELP        =  9

COLOR_3DDKSHADOW = 21
COLOR_3DFACE  = 15
COLOR_3DHILIGHT = 20
COLOR_3DHIGHLIGHT= 20
COLOR_3DLIGHT= 22
COLOR_BTNHILIGHT= 20
COLOR_3DSHADOW= 16
COLOR_ACTIVEBORDER =10
COLOR_ACTIVECAPTION= 2
COLOR_APPWORKSPACE= 12
COLOR_BACKGROUND= 1
COLOR_DESKTOP= 1
COLOR_BTNFACE= 15
COLOR_BTNHIGHLIGHT= 20
COLOR_BTNSHADOW= 16
COLOR_BTNTEXT= 18
COLOR_CAPTIONTEXT= 9
COLOR_GRAYTEXT= 17
COLOR_HIGHLIGHT= 13
COLOR_HIGHLIGHTTEXT= 14
COLOR_INACTIVEBORDER= 11
COLOR_INACTIVECAPTION= 3
COLOR_INACTIVECAPTIONTEXT= 19
COLOR_INFOBK= 24
COLOR_INFOTEXT= 23
COLOR_MENU= 4
COLOR_MENUTEXT= 7
COLOR_SCROLLBAR= 0
COLOR_WINDOW= 5
COLOR_WINDOWFRAME= 6
COLOR_WINDOWTEXT= 8
CTLCOLOR_MSGBOX= 0
CTLCOLOR_EDIT= 1
CTLCOLOR_LISTBOX= 2
CTLCOLOR_BTN= 3
CTLCOLOR_DLG= 4
CTLCOLOR_SCROLLBAR= 5
CTLCOLOR_STATIC= 6
CTLCOLOR_MAX= 7


GMEM_FIXED         = 0x0000
GMEM_MOVEABLE      = 0x0002
GMEM_NOCOMPACT     = 0x0010
GMEM_NODISCARD     = 0x0020
GMEM_ZEROINIT      = 0x0040
GMEM_MODIFY        = 0x0080
GMEM_DISCARDABLE   = 0x0100
GMEM_NOT_BANKED    = 0x1000
GMEM_SHARE         = 0x2000
GMEM_DDESHARE      = 0x2000
GMEM_NOTIFY        = 0x4000
GMEM_LOWER         = GMEM_NOT_BANKED
GMEM_VALID_FLAGS   = 0x7F72
GMEM_INVALID_HANDLE= 0x8000

RT_DIALOG        = "5"

CF_TEXT = 1


BS_DEFPUSHBUTTON = 0x01L
BS_GROUPBOX = 0x7

PUSHBUTTON = 0x80
EDITTEXT = 0x81
LTEXT = 0x82
LISTBOX  = 0x83
SCROLLBAR = 0x84
COMBOXBOX = 0x85
ES_MULTILINE = 4
ES_AUTOVSCROLL = 0x40L
ES_AUTOHSCROLL = 0x80L
ES_READONLY    = 0x800
CP_ACP = 0
DS_SETFONT = 0x40
DS_MODALFRAME = 0x80

SYNCHRONIZE  = (0x00100000L)
STANDARD_RIGHTS_REQUIRED = (0x000F0000L)
EVENT_ALL_ACCESS = (STANDARD_RIGHTS_REQUIRED|SYNCHRONIZE|0x3)
MAX_PATH = 260

def GET_XY_LPARAM(lParam):
    x = LOWORD(lParam)
    if x > 32768:
        x = x - 65536
    y = HIWORD(lParam)
    if y > 32768:
        y = y - 65536
        
    return x, y 

def GET_POINT_LPARAM(lParam):
    x, y = GET_XY_LPARAM(lParam)
    return POINT(x, y)

FVIRTKEY  = 0x01
FNOINVERT = 0x02
FSHIFT    = 0x04
FCONTROL  = 0x08
FALT      = 0x10

def ValidHandle(value):
    if value == 0:
        raise WinError()
    else:
        return value

def Fail(value):
    if value == -1:
        raise WinError()
    else:
        return value
    
GetModuleHandle = windll.kernel32.GetModuleHandleW
PostQuitMessage = windll.user32.PostQuitMessage
DefWindowProc = windll.user32.DefWindowProcW
CallWindowProc = windll.user32.CallWindowProcW
GetDCEx = windll.user32.GetDCEx
GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
LoadIcon = windll.user32.LoadIconW
DestroyIcon = windll.user32.DestroyIcon
LoadCursor = windll.user32.LoadCursorW
#LoadCursor.restype = ValidHandle
LoadImage = windll.user32.LoadImageW
LoadImage.restype = ValidHandle

RegisterClass = windll.user32.RegisterClassW
SetCursor = windll.user32.SetCursor

CreateWindowEx = windll.user32.CreateWindowExW
CreateWindowEx.restype = ValidHandle

ShowWindow = windll.user32.ShowWindow
UpdateWindow = windll.user32.UpdateWindow
EnableWindow = windll.user32.EnableWindow
GetMessage = windll.user32.GetMessageW
TranslateMessage = windll.user32.TranslateMessage
DispatchMessage = windll.user32.DispatchMessageW
GetWindowRect = windll.user32.GetWindowRect
MoveWindow = windll.user32.MoveWindow
DestroyWindow = windll.user32.DestroyWindow

CreateMenu = windll.user32.CreateMenu
CreatePopupMenu = windll.user32.CreatePopupMenu
DestroyMenu = windll.user32.DestroyMenu
AppendMenu = windll.user32.AppendMenuW
EnableMenuItem = windll.user32.EnableMenuItem
CheckMenuItem = windll.user32.CheckMenuItem
SendMessage = windll.user32.SendMessageW
PostMessage = windll.user32.PostMessageW
GetClientRect = windll.user32.GetClientRect
GetWindowRect = windll.user32.GetWindowRect
RegisterWindowMessage = windll.user32.RegisterWindowMessageW
GetParent = windll.user32.GetParent
GetWindowLong = windll.user32.GetWindowLongW
SetWindowLong = windll.user32.SetWindowLongW
SetClassLong = windll.user32.SetClassLongW
GetClassLong = windll.user32.GetClassLongW
SetWindowPos = windll.user32.SetWindowPos
InvalidateRect = windll.user32.InvalidateRect
BeginPaint = windll.user32.BeginPaint
EndPaint = windll.user32.EndPaint
SetCapture = windll.user32.SetCapture
GetCapture = windll.user32.GetCapture
ReleaseCapture = windll.user32.ReleaseCapture
ScreenToClient = windll.user32.ScreenToClient
ClientToScreen = windll.user32.ClientToScreen

IsDialogMessage = windll.user32.IsDialogMessageW
GetActiveWindow = windll.user32.GetActiveWindow
GetMessagePos = windll.user32.GetMessagePos
BeginDeferWindowPos = windll.user32.BeginDeferWindowPos
DeferWindowPos = windll.user32.DeferWindowPos
EndDeferWindowPos = windll.user32.EndDeferWindowPos
CreateAcceleratorTable = windll.user32.CreateAcceleratorTableW
DestroyAcceleratorTable = windll.user32.DestroyAcceleratorTable



GetModuleHandle = windll.kernel32.GetModuleHandleW
GetModuleHandle.restype = ValidHandle
LoadLibrary = windll.kernel32.LoadLibraryW
LoadLibrary.restype = ValidHandle
FindResource = windll.kernel32.FindResourceW
FindResource.restype = ValidHandle
FindWindow = windll.user32.FindWindowW
GetForegroundWindow = windll.user32.GetForegroundWindow
ChildWindowFromPoint = windll.user32.ChildWindowFromPoint

TrackPopupMenuEx = windll.user32.TrackPopupMenuEx


GetMenuItemInfo = windll.user32.GetMenuItemInfoW
GetMenuItemInfo.restype = ValidHandle
GetSubMenu = windll.user32.GetSubMenu
SetMenuItemInfo = windll.user32.SetMenuItemInfoW

SetWindowsHookEx = windll.user32.SetWindowsHookExW
CallNextHookEx = windll.user32.CallNextHookEx
UnhookWindowsHookEx = windll.user32.UnhookWindowsHookEx



MessageBox = windll.user32.MessageBoxW
SetWindowText = windll.user32.SetWindowTextW

GetFocus = windll.user32.GetFocus
SetFocus = windll.user32.SetFocus

OpenClipboard = windll.user32.OpenClipboard
EmptyClipboard = windll.user32.EmptyClipboard
SetClipboardData = windll.user32.SetClipboardData
GetClipboardData = windll.user32.GetClipboardData
RegisterClipboardFormat = windll.user32.RegisterClipboardFormatW
CloseClipboard = windll.user32.CloseClipboard
EnumClipboardFormats = windll.user32.EnumClipboardFormats
IsClipboardFormatAvailable = windll.user32.IsClipboardFormatAvailable

GetDlgItem = windll.user32.GetDlgItem
GetClassName = windll.user32.GetClassNameW
EndDialog = windll.user32.EndDialog

GetDesktopWindow = windll.user32.GetDesktopWindow
MultiByteToWideChar = windll.kernel32.MultiByteToWideChar
CreateDialogIndirectParam = windll.user32.CreateDialogIndirectParamW
DialogBoxIndirectParam = windll.user32.DialogBoxIndirectParamW



SetTimer = windll.user32.SetTimer
KillTimer = windll.user32.KillTimer

IsWindowVisible = windll.user32.IsWindowVisible

GetCursorPos = windll.user32.GetCursorPos
SetForegroundWindow = windll.user32.SetForegroundWindow

GetClassInfo = windll.user32.GetClassInfoW

OpenEvent = windll.kernel32.OpenEventW
CreateEvent = windll.kernel32.CreateEventW
GlobalAlloc = windll.kernel32.LocalAlloc
GlobalFree = windll.kernel32.LocalFree

Ellipse = windll.gdi32.Ellipse
SetBkColor = windll.gdi32.SetBkColor
GetStockObject = windll.gdi32.GetStockObject
LineTo = windll.gdi32.LineTo
MoveToEx = windll.gdi32.MoveToEx
FillRect = windll.user32.FillRect
DrawEdge = windll.user32.DrawEdge
CreateCompatibleDC = windll.gdi32.CreateCompatibleDC
CreateCompatibleBitmap = windll.gdi32.CreateCompatibleBitmap
CreateCompatibleDC.restype = ValidHandle
SelectObject = windll.gdi32.SelectObject
GetObject = windll.gdi32.GetObjectW
DeleteObject = windll.gdi32.DeleteObject
BitBlt = windll.gdi32.BitBlt
StretchBlt = windll.gdi32.StretchBlt
GetSysColorBrush = windll.user32.GetSysColorBrush
#CreateHatchBrush = windll.gdi32.CreateHatchBrush
CreatePatternBrush = windll.gdi32.CreatePatternBrush
CreateSolidBrush = windll.gdi32.CreateSolidBrush
CreateBitmap = windll.gdi32.CreateBitmap
PatBlt = windll.gdi32.PatBlt
#CreateFont = windll.gdi32.CreateFontA
#EnumFontFamiliesEx = windll.gdi32.EnumFontFamiliesExA
InvertRect = windll.user32.InvertRect
DrawFocusRect = windll.user32.DrawFocusRect
#ExtCreatePen = windll.gdi32.ExtCreatePen
CreatePen = windll.gdi32.CreatePen
DrawText = windll.user32.DrawTextW
#TextOut = windll.gdi32.TextOutA
CreateDIBSection = windll.gdi32.CreateDIBSection
DeleteDC = windll.gdi32.DeleteDC
#GetDIBits = windll.gdi32.GetDIBits
CreateFontIndirect = windll.gdi32.CreateFontIndirectW
Polyline = windll.gdi32.Polyline
FillRect = windll.user32.FillRect
SetTextColor = windll.gdi32.SetTextColor



#WinCe api
import ctypes
WM_APP = 0x8000
LineType = POINT*2
SHCMBF_EMPTYBAR = 0x0001
SHCMBF_HIDDEN = 0x0002

SHCMBF_HIDESIPBUTTON = 0x0004
SHCMBF_COLORBK = 0x0008
SHCMBF_HMENU = 0x0010
SPI_SETSIPINFO = 224
SPI_GETSIPINFO = 225

DrawMenuBar = windll.user32.DrawMenuBar
GetTextExtentExPointW = windll.gdi32.GetTextExtentExPointW

class SIZE(Structure):
    _fields_ = [('cx', LONG),
                ('cy', LONG)]
    
def GetTextExtent(hdc, string):
    n = len(string)
    size = SIZE()
    GetTextExtentExPointW(hdc, string, n, 0, 0, 0, byref(size))
    return size.cx, size.cy

########NEW FILE########
__FILENAME__ = w32comctl
## Copyright (c) Alexandre Delattre 2008
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE

from w32api import *

ATL_IDW_BAND_FIRST = 0xEB00
HTREEITEM = HANDLE
HIMAGELIST = HANDLE

UINT_MAX = (1l << 32)

LVCF_FMT     =1
LVCF_WIDTH   =2
LVCF_TEXT    =4
LVCF_SUBITEM =8
LVCF_IMAGE= 16
LVCF_ORDER= 32

TVIF_TEXT    = 1
TVIF_IMAGE   =2
TVIF_PARAM   =4
TVIF_STATE   =8
TVIF_HANDLE = 16
TVIF_SELECTEDIMAGE  = 32
TVIF_CHILDREN      =  64
TVIF_INTEGRAL      =  0x0080
TVIF_DI_SETITEM    =  0x1000

LVIF_TEXT   = 1
LVIF_IMAGE  = 2
LVIF_PARAM  = 4
LVIF_STATE  = 8
LVIF_DI_SETITEM =  0x1000

LVIS_SELECTED = 0x0002

COMCTL32_VERSION = 0x020c
CCM_FIRST = 0x2000
CCM_SETVERSION = CCM_FIRST+0x7
CCM_GETVERSION = CCM_FIRST+0x8
TCS_BOTTOM = 0x2

class MaskedStructureType(Structure.__class__):
    def __new__(cls, name, bases, dct):
        fields = []
        for field in dct['_fields_']:
            fields.append((field[0], field[1]))
            if len(field) == 4: #masked field
                dct[field[3]] = property(None,
                                         lambda self, val, field = field:
                                         self.setProperty(field[0], field[2], val))
        dct['_fields_'] = fields
        return Structure.__class__.__new__(cls, name, bases, dct)
    
class MaskedStructure(Structure):
    __metaclass__ = MaskedStructureType
    _fields_ = []

    def setProperty(self, name, mask, value):
        setattr(self, self._mask_, getattr(self, self._mask_) | mask)
        setattr(self, name, value)

    def clear(self):
        setattr(self, self._mask_, 0)
        
class NMCBEENDEDIT(Structure):
    _fields_ = [("hdr", NMHDR),
                ("fChanged", BOOL),
                ("iNewSelection", INT),
                ("szText", POINTER(TCHAR)),
                ("iWhy", INT)]

class LVCOLUMN(MaskedStructure):
    _mask_ = 'mask'
    _fields_ = [("mask", UINT),
                ("fmt", INT, LVCF_FMT, "format"),
                ("cx", INT, LVCF_WIDTH, 'width'),
                ("pszText", LPTSTR, LVCF_TEXT, 'text'),
                ("cchTextMax", INT),
                ("iSubItem", INT),
                ("iImage", INT),
                ("iOrder", INT)]

class LVITEM(Structure):
    _fields_ = [("mask", UINT),
                ("iItem", INT),
                ("iSubItem", INT),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR),
                ("cchTextMax", INT),
                ("iImage", INT),
                ("lParam", LPARAM),
                ("iIndent", INT)]

class LV_DISPINFO(Structure):
    _fields_ = [("hdr", NMHDR),
                ("item", LVITEM)]
    

class TV_ITEMEX(MaskedStructure):
    _mask_ = 'mask'
    _fields_ = [("mask", UINT),
                ("hItem", HTREEITEM),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR, TVIF_TEXT, 'text'),
                ("cchTextMax", INT),
                ("iImage", INT, TVIF_IMAGE, 'image'),
                ("iSelectedImage", INT, TVIF_SELECTEDIMAGE, 'selectedImage'),
                ("cChildren", INT, TVIF_CHILDREN, 'children'),
                ("lParam", LPARAM, TVIF_PARAM, 'param'),
                ("iIntegral", INT)]

class TVITEMOLD(Structure):
    _fields_ = [("mask", UINT),
                ("hItem", HTREEITEM),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR),
                ("cchTextMax", INT),
                ("iImage", INT),
                ("iSelectedImage", INT),
                ("cChildren", INT),
                ("lParam", LPARAM)]

class TVITEM(MaskedStructure):
    _mask_ = 'mask'
    _fields_ = [("mask", UINT),
                ("hItem", HTREEITEM),
                ("state", UINT),
                ("stateMask", UINT),
                ("pszText", LPTSTR, TVIF_TEXT, 'text'),
                ("cchTextMax", INT),
                ("iImage", INT, TVIF_IMAGE,'image'),
                ("iSelectedImage", INT, TVIF_SELECTEDIMAGE, 'selectedImage'),
                ("cChildren", INT, TVIF_CHILDREN,'children'), 
                ("lParam", LPARAM, TVIF_PARAM,'param')]

class TBBUTTON(Structure):
    _fields_ = [("iBitmap", INT),
                ("idCommand", INT),
                ("fsState", BYTE),
                ("fsStyle", BYTE),
                #("bReserved", BYTE * 2),
                ("dwData", DWORD_PTR),
                ("iString", INT_PTR)]

class TBBUTTONINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("dwMask", DWORD),
                ("idCommand", INT),
                ("iImage", INT),
                ("fsState", BYTE),
                ("fsStyle", BYTE),
                ("cx", WORD),
                ("lParam", DWORD_PTR),
                ("pszText", LPTSTR),
                ("cchText", INT)]

class TVINSERTSTRUCT(Structure):
    _fields_ = [("hParent", HTREEITEM),
                ("hInsertAfter", HTREEITEM),
                ("item", TVITEM)]

class TCITEM(Structure):
    _fields_ = [("mask", UINT),
                ("dwState", DWORD),
                ("dwStateMask", DWORD),
                ("pszText", LPTSTR),
                ("cchTextMax", INT),
                ("iImage", INT),
                ("lParam", LPARAM)]

class NMTREEVIEW(Structure):
    _fields_ = [("hdr", NMHDR),
                ("action", UINT),
                ("itemOld", TVITEM),
                ("itemNew", TVITEM),
                ("ptDrag", POINT)]

class NMLISTVIEW(Structure):
    _fields_ = [("hrd", NMHDR),
                ("iItem", INT),
                ("iSubItem", INT),
                ("uNewState", UINT),
                ("uOldState", UINT),
                ("uChanged", UINT),
                ("ptAction", POINT),
                ("lParam", LPARAM)]
    
class INITCOMMONCONTROLSEX(Structure):
    _fields_ = [("dwSize", DWORD),
                ("dwICC", DWORD)]

class REBARINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("fMask", UINT),
                ("himl", HIMAGELIST)]

class REBARBANDINFO(Structure):
    _fields_ = [("cbSize", UINT),
                ("fMask", UINT),
                ("fStyle", UINT),
                ("clrFore", COLORREF),
                ("clrBack", COLORREF),
                ("lpText", LPTSTR),
                ("cch", UINT),
                ("iImage", INT),
                ("hwndChild", HWND),
                ("cxMinChild", UINT),
                ("cyMinChild", UINT),
                ("cx", UINT),
                ("hbmBack", HBITMAP),
                ("wID", UINT),
                ("cyChild", UINT),
                ("cyMaxChild", UINT),
                ("cyIntegral", UINT),
                ("cxIdeal", UINT),
                ("lParam", LPARAM),
                ("cxHeader", UINT)]

class NMTOOLBAR(Structure):
    _fields_ = [("hdr", NMHDR),
                ("iItem", INT),
                ("tbButton", TBBUTTON),
                ("cchText", INT),
                ("pszText", LPTSTR),
                ("rcButton", RECT)]

class NMTBHOTITEM(Structure):
    _fields_ = [("hdr", NMHDR),
                ("idOld", INT),
                ("idNew", INT),
                ("dwFlags", DWORD)]

class PBRANGE(Structure):
    _fields_ = [("iLow", INT),
                ("iHigh", INT)]
    
class NMITEMACTIVATE(Structure):
    _fields_ = [("hdr", NMHDR),
                ("iItem", c_int),
                ("iSubItem", c_int),
                ("uNewState", UINT),
                ("uOldState", UINT),
                ("uChanged", UINT),
                ("ptAction", POINT),
                ("lParam", LPARAM),
                ("uKeyFlags", UINT)]

NM_FIRST    =   UINT_MAX

SBS_BOTTOMALIGN = 4
SBS_HORZ = 0
SBS_LEFTALIGN = 2
SBS_RIGHTALIGN = 4
SBS_SIZEBOX = 8
SBS_SIZEBOXBOTTOMRIGHTALIGN = 4
SBS_SIZEBOXTOPLEFTALIGN = 2
SBS_SIZEGRIP = 16
SBS_TOPALIGN = 2
SBS_VERT = 1

CCS_NODIVIDER =	64
CCS_NOPARENTALIGN = 8
CCS_NORESIZE = 4
CCS_TOP = 1


CBS_DROPDOWN = 2

RBBS_BREAK = 1
RBBS_FIXEDSIZE = 2
RBBS_CHILDEDGE = 4
RBBS_HIDDEN = 8
RBBS_NOVERT = 16
RBBS_FIXEDBMP = 32
RBBS_VARIABLEHEIGHT = 64
RBBS_GRIPPERALWAYS = 128
RBBS_NOGRIPPER = 256

RBS_TOOLTIPS = 256
RBS_VARHEIGHT = 512
RBS_BANDBORDERS = 1024
RBS_FIXEDORDER = 2048

RBS_REGISTERDROP = 4096
RBS_AUTOSIZE = 8192
RBS_VERTICALGRIPPER = 16384
RBS_DBLCLKTOGGLE = 32768

RBN_FIRST	= ((UINT_MAX) - 831)
RBN_HEIGHTCHANGE = RBN_FIRST

TBSTYLE_FLAT = 2048
TBSTYLE_LIST = 4096
TBSTYLE_DROPDOWN = 8
TBSTYLE_TRANSPARENT = 0x8000
TBSTYLE_REGISTERDROP = 0x4000
TBSTYLE_BUTTON = 0x0000
TBSTYLE_AUTOSIZE = 0x0010
    
TB_ADDBITMAP = 0x0413
TB_ENABLEBUTTON = 0x401
TB_CHECKBUTTON = 0x402
TB_ISBUTTONCHECKED = WM_USER+10
TB_BUTTONSTRUCTSIZE = WM_USER+30
TB_ADDBUTTONS       = WM_USER+20
TB_INSERTBUTTONA    = WM_USER + 21
TB_INSERTBUTTON     = WM_USER + 21
TB_BUTTONCOUNT      = WM_USER + 24
TB_GETITEMRECT      = WM_USER + 29
TB_SETBUTTONINFOW  =  WM_USER + 64
TB_SETBUTTONINFOA  =  WM_USER + 66
TB_SETBUTTONINFO   =  TB_SETBUTTONINFOA
TB_SETIMAGELIST    =  WM_USER + 48
TB_SETDRAWTEXTFLAGS =  WM_USER + 70
TB_PRESSBUTTON       = WM_USER + 3
TB_GETRECT        =      (WM_USER + 51)
TB_SETHOTITEM   =        (WM_USER + 72)
TB_HITTEST     =         (WM_USER + 69)
TB_GETHOTITEM  =         (WM_USER + 7)
TB_SETBUTTONSIZE     =  (WM_USER + 31)
TB_AUTOSIZE          =  (WM_USER + 33)
TB_DELETEBUTTON = WM_USER + 22

TVIF_TEXT    = 1
TVIF_IMAGE   =2
TVIF_PARAM   =4
TVIF_STATE   =8
TVIF_HANDLE = 16
TVIF_SELECTEDIMAGE  = 32
TVIF_CHILDREN      =  64
TVIF_INTEGRAL      =  0x0080
TVIF_DI_SETITEM    =  0x1000
 
TVI_ROOT     = 0xFFFF0000l
TVI_FIRST    = 0xFFFF0001l
TVI_LAST     = 0xFFFF0002l
TVI_SORT     = 0xFFFF0003l

TVGN_CHILD   =  4
TVGN_NEXT    =  1
TVGN_ROOT    =  0
TVGN_CARET   =           0x0009

TVIS_FOCUSED = 1
TVIS_SELECTED =       2
TVIS_CUT    = 4
TVIS_DROPHILITED   =  8
TVIS_BOLD  =  16
TVIS_EXPANDED      =  32
TVIS_EXPANDEDONCE  =  64
TVIS_OVERLAYMASK   =  0xF00
TVIS_STATEIMAGEMASK = 0xF000
TVIS_USERMASK      =  0xF000

TV_FIRST = 0x1100
TVM_INSERTITEMA =     TV_FIRST
TVM_INSERTITEMW =    (TV_FIRST+50)
TVM_INSERTITEM = TVM_INSERTITEMW
TVM_SETIMAGELIST =    (TV_FIRST+9)
TVM_DELETEITEM   =   (TV_FIRST+1)
TVM_GETNEXTITEM   =   (TV_FIRST+10)
TVM_EXPAND =   (TV_FIRST+2)
TVM_GETITEMSTATE=        (TV_FIRST + 39)
TVM_ENSUREVISIBLE=       (TV_FIRST + 20)
TVM_SELECTITEM=          (TV_FIRST + 11)
TVM_SETITEMA=            (TV_FIRST + 13)
TVM_SETITEMW =           (TV_FIRST + 63)
TVM_SETITEM= TVM_SETITEMW
TVM_GETITEMA=            (TV_FIRST + 12)
TVM_GETITEMW =           (TV_FIRST + 62)
TVM_GETITEM = TVM_GETITEMW


TVS_HASBUTTONS =       1
TVS_HASLINES = 2
TVS_LINESATROOT =      4
TVS_EDITLABELS  =      8
TVS_DISABLEDRAGDROP =  16
TVS_SHOWSELALWAYS =   32
TVS_CHECKBOXES =  256
TVS_TOOLTIPS = 128
TVS_RTLREADING = 64
TVS_TRACKSELECT = 512
TVS_FULLROWSELECT = 4096
TVS_INFOTIP = 2048
TVS_NONEVENHEIGHT = 16384
TVS_NOSCROLL  = 8192
TVS_SINGLEEXPAND  =1024
TVS_NOHSCROLL   =     0x8000

CBEN_FIRST  =  (UINT_MAX) - 800
CBEN_ENDEDITA = CBEN_FIRST - 5
CBEN_ENDEDITW = CBEN_FIRST - 6
CBEN_ENDEDIT = CBEN_ENDEDITA

# trackbar styles
TBS_AUTOTICKS =           0x0001
TBS_VERT =                0x0002
TBS_HORZ =                0x0000
TBS_TOP =                 0x0004
TBS_BOTTOM =              0x0000
TBS_LEFT =                0x0004
TBS_RIGHT =               0x0000
TBS_BOTH =                0x0008
TBS_NOTICKS =             0x0010
TBS_ENABLESELRANGE =      0x0020
TBS_FIXEDLENGTH =         0x0040
TBS_NOTHUMB =             0x0080
TBS_TOOLTIPS =            0x0100

# trackbar messages
TBM_GETPOS =              (WM_USER)
TBM_GETRANGEMIN =         (WM_USER+1)
TBM_GETRANGEMAX =         (WM_USER+2)
TBM_GETTIC =              (WM_USER+3)
TBM_SETTIC =              (WM_USER+4)
TBM_SETPOS =              (WM_USER+5)
TBM_SETRANGE =            (WM_USER+6)
TBM_SETRANGEMIN =         (WM_USER+7)
TBM_SETRANGEMAX =         (WM_USER+8)
TBM_CLEARTICS =           (WM_USER+9)
TBM_SETSEL =              (WM_USER+10)
TBM_SETSELSTART =         (WM_USER+11)
TBM_SETSELEND =           (WM_USER+12)
TBM_GETPTICS =            (WM_USER+14)
TBM_GETTICPOS =           (WM_USER+15)
TBM_GETNUMTICS =          (WM_USER+16)
TBM_GETSELSTART =         (WM_USER+17)
TBM_GETSELEND =           (WM_USER+18)
TBM_CLEARSEL =            (WM_USER+19)
TBM_SETTICFREQ =          (WM_USER+20)
TBM_SETPAGESIZE =         (WM_USER+21)
TBM_GETPAGESIZE =         (WM_USER+22)
TBM_SETLINESIZE =         (WM_USER+23)
TBM_GETLINESIZE =         (WM_USER+24)
TBM_GETTHUMBRECT =        (WM_USER+25)
TBM_GETCHANNELRECT =      (WM_USER+26)
TBM_SETTHUMBLENGTH =      (WM_USER+27)
TBM_GETTHUMBLENGTH =      (WM_USER+28)
TBM_SETTOOLTIPS =         (WM_USER+29)
TBM_GETTOOLTIPS =         (WM_USER+30)
TBM_SETTIPSIDE =          (WM_USER+31)
TBM_SETBUDDY =            (WM_USER+32) 
TBM_GETBUDDY =            (WM_USER+33) 

# trackbar top-side flags
TBTS_TOP =                0
TBTS_LEFT =               1
TBTS_BOTTOM =             2
TBTS_RIGHT =              3


TB_LINEUP =               0
TB_LINEDOWN =             1
TB_PAGEUP =               2
TB_PAGEDOWN =             3
TB_THUMBPOSITION =        4
TB_THUMBTRACK =           5
TB_TOP =                  6
TB_BOTTOM =               7
TB_ENDTRACK =             8

# trackbar custom draw item specs
TBCD_TICS =    0x0001
TBCD_THUMB =   0x0002
TBCD_CHANNEL = 0x0003



STATUSCLASSNAME = u"msctls_statusbar32"

REBARCLASSNAMEW = u"ReBarWindow32"
REBARCLASSNAMEA = u"ReBarWindow32"
REBARCLASSNAME = REBARCLASSNAMEA

PROGRESS_CLASSW = u"msctls_progress32"
PROGRESS_CLASSA = u"msctls_progress32"
PROGRESS_CLASS = PROGRESS_CLASSA

TRACKBAR_CLASSW = u"msctls_trackbar32"
TRACKBAR_CLASSA = u"msctls_trackbar32"
TRACKBAR_CLASS = TRACKBAR_CLASSA


EDIT = u"edit"
BUTTON = u"button"

WC_COMBOBOXEXW = u"ComboBoxEx32"
WC_COMBOBOXEXA = u"ComboBoxEx32"
WC_COMBOBOXEX = WC_COMBOBOXEXA

WC_TREEVIEWA = u"SysTreeView32"
WC_TREEVIEWW = u"SysTreeView32"
WC_TREEVIEW = WC_TREEVIEWA

WC_LISTVIEWA = u"SysListView32"
WC_LISTVIEWW = u"SysListView32"
WC_LISTVIEW = WC_LISTVIEWA

TOOLBARCLASSNAMEW = u"ToolbarWindow32"
TOOLBARCLASSNAMEA = u"ToolbarWindow32"
TOOLBARCLASSNAME = TOOLBARCLASSNAMEA

WC_TABCONTROLA =    u"SysTabControl32"
WC_TABCONTROLW =      u"SysTabControl32"
WC_TABCONTROL = WC_TABCONTROLA

LVS_ICON    = 0
LVS_REPORT   =1
LVS_SMALLICON =       2
LVS_LIST    = 3
LVS_TYPEMASK= 3
LVS_SINGLESEL=        4
LVS_SHOWSELALWAYS=    8
LVS_SORTASCENDING =   16
LVS_SORTDESCENDING =  32
LVS_SHAREIMAGELISTS = 64
LVS_NOLABELWRAP     = 128
LVS_AUTOARRANGE     = 256
LVS_EDITLABELS      = 512
LVS_NOSCROLL= 0x2000
LVS_TYPESTYLEMASK  =  0xfc00
LVS_ALIGNTOP= 0
LVS_ALIGNLEFT =       0x800
LVS_ALIGNMASK  =      0xc00
LVS_OWNERDRAWFIXED=   0x400
LVS_NOCOLUMNHEADER =  0x4000
LVS_NOSORTHEADER   =  0x8000
LVS_OWNERDATA =4096
LVS_EX_CHECKBOXES= 4
LVS_EX_FULLROWSELECT= 32
LVS_EX_GRIDLINES =1
LVS_EX_HEADERDRAGDROP= 16
LVS_EX_ONECLICKACTIVATE= 64
LVS_EX_SUBITEMIMAGES= 2
LVS_EX_TRACKSELECT= 8
LVS_EX_TWOCLICKACTIVATE= 128
LVS_EX_FLATSB       = 0x00000100
LVS_EX_REGIONAL     = 0x00000200
LVS_EX_INFOTIP      = 0x00000400
LVS_EX_UNDERLINEHOT = 0x00000800
LVS_EX_UNDERLINECOLD= 0x00001000
LVS_EX_MULTIWORKAREAS =       0x00002000
LVS_EX_LABELTIP     = 0x00004000
LVS_EX_BORDERSELECT = 0x00008000

LVIS_FOCUSED         =   0x0001
LVIS_SELECTED        =   0x0002
LVIS_CUT             =   0x0004
LVIS_DROPHILITED     =   0x0008
LVIS_ACTIVATING      =   0x0020

LVIS_OVERLAYMASK      =  0x0F00
LVIS_STATEIMAGEMASK   =  0xF000

LVM_FIRST = 0x1000
LVM_INSERTCOLUMNA = (LVM_FIRST+27)
LVM_INSERTCOLUMNW = (LVM_FIRST+97)
LVM_INSERTCOLUMN = LVM_INSERTCOLUMNW
LVM_INSERTITEMA = (LVM_FIRST+7)
LVM_SETITEMA = (LVM_FIRST+6)
LVM_INSERTITEMW = (LVM_FIRST+77)
LVM_SETITEMW = (LVM_FIRST+76)
LVM_INSERTITEM = LVM_INSERTITEMW
LVM_SETITEM = LVM_SETITEMW
LVM_DELETEALLITEMS =  (LVM_FIRST + 9)
LVM_SETITEMSTATE  =  (LVM_FIRST + 43)
LVM_GETITEMCOUNT  =  (LVM_FIRST + 4)
LVM_SETITEMCOUNT  =  (LVM_FIRST + 47)
LVM_GETITEMSTATE   =  (LVM_FIRST + 44)
LVM_GETSELECTEDCOUNT =   (LVM_FIRST + 50)
LVM_SETCOLUMNA  =        (LVM_FIRST + 26)
LVM_SETCOLUMNW  =        (LVM_FIRST + 96)
LVM_SETCOLUMN = LVM_SETCOLUMNW
LVM_SETCOLUMNWIDTH =  (LVM_FIRST + 30)
LVM_GETITEMA   =         (LVM_FIRST + 5)
LVM_GETITEMW   =         (LVM_FIRST + 75)
LVM_GETITEM = LVM_GETITEMW
LVM_SETEXTENDEDLISTVIEWSTYLE = (LVM_FIRST + 54)
LVM_GETNEXTITEM = (LVM_FIRST + 12)
LVS_SHAREIL = 0x4
LVM_SETIMAGELIST = (LVM_FIRST + 3)

LVNI_SELECTED = 0x2

LVN_FIRST = (UINT_MAX) - 100
LVN_ITEMCHANGING    =    (LVN_FIRST-0)
LVN_ITEMCHANGED     =    (LVN_FIRST-1)
LVN_INSERTITEM      =    (LVN_FIRST-2)
LVN_DELETEITEM       =   (LVN_FIRST-3)
LVN_DELETEALLITEMS    =  (LVN_FIRST-4)
LVN_BEGINLABELEDITA   =  (LVN_FIRST-5)
LVN_BEGINLABELEDITW   =  (LVN_FIRST-75)
LVN_ENDLABELEDITA     =  (LVN_FIRST-6)
LVN_ENDLABELEDITW     =  (LVN_FIRST-76)
LVN_COLUMNCLICK       =  (LVN_FIRST-8)
LVN_BEGINDRAG         =  (LVN_FIRST-9)
LVN_BEGINRDRAG        =  (LVN_FIRST-11)
LVN_GETDISPINFO = (LVN_FIRST - 77)

NM_OUTOFMEMORY    =      (NM_FIRST-1)
NM_CLICK          =      (NM_FIRST-2)   
NM_DBLCLK         =      (NM_FIRST-3)
NM_RETURN         =      (NM_FIRST-4)
NM_RCLICK         =      (NM_FIRST-5)   
NM_RDBLCLK        =      (NM_FIRST-6)
NM_SETFOCUS       =      (NM_FIRST-7)
NM_KILLFOCUS      =      (NM_FIRST-8)
NM_CUSTOMDRAW     =      (NM_FIRST-12)
NM_HOVER          =      (NM_FIRST-13)
NM_NCHITTEST      =      (NM_FIRST-14)  
NM_KEYDOWN        =      (NM_FIRST-15)  
NM_RELEASEDCAPTURE=      (NM_FIRST-16)
NM_SETCURSOR      =      (NM_FIRST-17)  
NM_CHAR           =      (NM_FIRST-18)  

LVCFMT_LEFT = 0
LVCFMT_RIGHT= 1
LVCFMT_CENTER   =     2
LVCFMT_JUSTIFYMASK =  3
LVCFMT_BITMAP_ON_RIGHT =4096
LVCFMT_COL_HAS_IMAGES = 32768
LVCFMT_IMAGE =2048


ICC_LISTVIEW_CLASSES =1
ICC_TREEVIEW_CLASSES =2
ICC_BAR_CLASSES      =4
ICC_TAB_CLASSES      =8
ICC_UPDOWN_CLASS =16
ICC_PROGRESS_CLASS =32
ICC_HOTKEY_CLASS =64
ICC_ANIMATE_CLASS= 128
ICC_WIN95_CLASSES= 255
ICC_DATE_CLASSES =256
ICC_USEREX_CLASSES =512
ICC_COOL_CLASSES =1024
ICC_INTERNET_CLASSES =2048
ICC_PAGESCROLLER_CLASS =4096
ICC_NATIVEFNTCTL_CLASS= 8192

TCN_FIRST  =  (UINT_MAX) -550
TCN_LAST   =  (UINT_MAX) -580
TCN_KEYDOWN   =  TCN_FIRST
TCN_SELCHANGE =        (TCN_FIRST-1)
TCN_SELCHANGING  =     (TCN_FIRST-2)

TVE_COLLAPSE =1
TVE_EXPAND   =2
TVE_TOGGLE   =3
TVE_COLLAPSERESET   = 0x8000

TCM_FIRST   = 0x1300
TCM_INSERTITEMA  =    (TCM_FIRST+7)
TCM_INSERTITEMW  =   (TCM_FIRST+62)
TCM_INSERTITEM = TCM_INSERTITEMW
TCM_ADJUSTRECT = (TCM_FIRST+40)
TCM_GETCURSEL   =     (TCM_FIRST+11)
TCM_SETCURSEL   =     (TCM_FIRST+12)
TCM_GETITEMA = (TCM_FIRST+5)
TCM_GETITEMW = (TCM_FIRST+60)
TCM_GETITEM = TCM_GETITEMW
TCM_DELETEITEM = (TCM_FIRST + 8)
TCM_GETITEMCOUNT = (TCM_FIRST + 4)

TVN_FIRST  =  ((UINT_MAX)-400)
TVN_LAST   =  ((UINT_MAX)-499)
TVN_ITEMEXPANDINGA =  (TVN_FIRST-5)
TVN_ITEMEXPANDINGW =  (TVN_FIRST-54)
TVN_ITEMEXPANDING = TVN_ITEMEXPANDINGW
TVN_SELCHANGEDA  =    (TVN_FIRST-2)
TVN_SELCHANGEDW  =    (TVN_FIRST-51)
TVN_SELCHANGED  =  TVN_SELCHANGEDW
TVN_DELETEITEMA  =     (TVN_FIRST-9)
TVN_DELETEITEMW  =    (TVN_FIRST-58)
TVN_DELETEITEM = TVN_DELETEITEMW


ES_LEFT = 0
ES_CENTER  = 1
ES_RIGHT    =   0x0002
ES_MULTILINE   = 0x0004
ES_UPPERCASE  =  0x0008
ES_LOWERCASE =   0x0010
ES_PASSWORD   =  0x0020
ES_AUTOVSCROLL = 0x0040
ES_AUTOHSCROLL  =0x0080
ES_NOHIDESEL   = 0x0100
ES_COMBOBOX 	=0x0200
ES_OEMCONVERT  = 0x0400
ES_READONLY    = 0x0800
ES_WANTRETURN  = 0x1000

SB_SIMPLE =   (WM_USER+9)
SB_SETTEXTA = (WM_USER+1)
SB_SETTEXTW = (WM_USER+11)
SB_SETTEXT = SB_SETTEXTW

SBT_OWNERDRAW   =     0x1000
SBT_NOBORDERS   =     256
SBT_POPOUT   = 512
SBT_RTLREADING =      1024
SBT_OWNERDRAW  =      0x1000
SBT_NOBORDERS  =      256
SBT_POPOUT   = 512
SBT_RTLREADING = 1024
SBT_TOOLTIPS = 0x0800

TBN_FIRST          =  ((UINT_MAX)-700)
TBN_DROPDOWN       =     (TBN_FIRST - 10)
TBN_HOTITEMCHANGE  =  (TBN_FIRST - 13)
TBDDRET_DEFAULT       =  0
TBDDRET_NODEFAULT     =  1
TBDDRET_TREATPRESSED  =  2

PBS_SMOOTH   = 0x01
PBS_VERTICAL = 0x04

CCM_FIRST      = 0x2000 # Common control shared messages
CCM_SETBKCOLOR = (CCM_FIRST + 1)

PBM_SETRANGE    = (WM_USER+1)
PBM_SETPOS      = (WM_USER+2)
PBM_DELTAPOS    = (WM_USER+3)
PBM_SETSTEP     = (WM_USER+4)
PBM_STEPIT      = (WM_USER+5)
PBM_SETRANGE32  = (WM_USER+6)
PBM_GETRANGE    = (WM_USER+7)
PBM_GETPOS      = (WM_USER+8)
PBM_SETBARCOLOR = (WM_USER+9)
PBM_SETBKCOLOR  = CCM_SETBKCOLOR


# ListBox Messages
LB_ADDSTRING = 384
LB_INSERTSTRING = 385
LB_DELETESTRING = 386
LB_RESETCONTENT = 388
LB_GETCOUNT = 395
LB_SETTOPINDEX = 407
LB_GETCURSEL =  0x0188

# ComboBox styles
CBS_DROPDOWN         = 0x0002L
CBS_DROPDOWNLIST      =0x0003L
CBS_AUTOHSCROLL       =0x0040L
CBS_OEMCONVERT      =  0x0080L
CBS_SORT             = 0x0100L
CBS_HASSTRINGS       = 0x0200L
CBS_NOINTEGRALHEIGHT = 0x0400L
CBS_DISABLENOSCROLL  = 0x0800L
CBS_UPPERCASE         =  0x2000L
CBS_LOWERCASE          = 0x4000L

ImageList_Create = windll.comctl32.ImageList_Create
ImageList_Destroy = windll.comctl32.ImageList_Destroy
ImageList_Add = windll.comctl32.ImageList_Add
ImageList_AddMasked = windll.comctl32.ImageList_AddMasked
#ImageList_AddIcon = windll.comctl32.ImageList_AddIcon
ImageList_SetBkColor = windll.comctl32.ImageList_SetBkColor
ImageList_ReplaceIcon = windll.comctl32.ImageList_ReplaceIcon

def ImageList_AddIcon(a, b):
    return ImageList_ReplaceIcon(a, -1, b)

InitCommonControlsEx = windll.comctl32.InitCommonControlsEx

# Nouveautes

# Static control 

SS_LEFT = 0x00000000L
SS_CENTER = 0x00000001L
SS_RIGHT = 0x00000002L
SS_ICON = 0x00000003L
SS_LEFTNOWORDWRAP = 0x0000000CL
SS_BITMAP = 0x0000000EL
SS_NOPREFIX = 0x00000080L
SS_CENTERIMAGE = 0x00000200L
SS_NOTIFY = 0x00000100L
STN_CLICKED = 0
STN_ENABLE = 2
STN_DISABLE = 3
STM_SETIMAGE = 0x0172
STM_GETIMAGE = 0x0173

# Button control

BS_PUSHBUTTON = 0x00000000L
BS_DEFPUSHBUTTON = 0x00000001L
BS_CHECKBOX = 0x00000002L
BS_AUTOCHECKBOX = 0x00000003L
BS_RADIOBUTTON = 0x00000004L
BS_3STATE = 0x00000005L
BS_AUTO3STATE = 0x00000006L
BS_GROUPBOX = 0x00000007L
BS_AUTORADIOBUTTON = 0x00000009L
BS_OWNERDRAW = 0x0000000BL
BS_LEFTTEXT = 0x00000020L
BS_TEXT = 0x00000000L
BS_LEFT = 0x00000100L
BS_RIGHT = 0x00000200L
BS_CENTER = 0x00000300L
BS_TOP = 0x00000400L
BN_CLICKED = 0
BN_PAINT = 1
BN_DBLCLK = 5
BN_SETFOCUS = 6
BN_KILLFOCUS = 7
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BM_GETSTATE = 0x00F2
BM_SETSTATE = 0x00F3
BM_SETSTYLE = 0x00F4
BM_CLICK = 0x00F5
BST_UNCHECKED = 0x0000
BST_CHECKED = 0x0001
BST_INDETERMINATE = 0x0002
BST_PUSHED = 0x0004
BST_FOCUS = 0x0008

# Edit control

ES_LEFT = 0x0000L
ES_CENTER = 0x0001L
ES_RIGHT = 0x0002L
ES_MULTILINE = 0x0004L
ES_UPPERCASE = 0x0008L
ES_LOWERCASE = 0x0010L
ES_PASSWORD = 0x0020L
ES_AUTOVSCROLL = 0x0040L
ES_AUTOHSCROLL = 0x0080L
ES_NOHIDESEL = 0x0100L
ES_COMBOBOX = 0x0200L
ES_OEMCONVERT = 0x0400L
ES_READONLY = 0x0800L
ES_WANTRETURN = 0x1000L
ES_NUMBER = 0x2000L
EN_SETFOCUS = 0x0100
EN_KILLFOCUS = 0x0200
EN_CHANGE = 0x0300
EN_UPDATE = 0x0400
EN_ERRSPACE = 0x0500
EN_MAXTEXT = 0x0501
EN_HSCROLL = 0x0601
EN_VSCROLL = 0x0602
EC_LEFTMARGIN = 0x0001
EC_RIGHTMARGIN = 0x0002
EC_USEFONTINFO = 0xffff
EM_GETSEL = 0x00B0
EM_SETSEL = 0x00B1
EM_GETRECT = 0x00B2
EM_SETRECT = 0x00B3
EM_SETRECTNP = 0x00B4
EM_SCROLL = 0x00B5
EM_LINESCROLL = 0x00B6
EM_SCROLLCARET = 0x00B7
EM_GETMODIFY = 0x00B8
EM_SETMODIFY = 0x00B9
EM_GETLINECOUNT = 0x00BA
EM_LINEINDEX = 0x00BB
EM_LINELENGTH = 0x00C1
EM_REPLACESEL = 0x00C2
EM_GETLINE = 0x00C4
EM_LIMITTEXT = 0x00C5
EM_CANUNDO = 0x00C6
EM_UNDO = 0x00C7
EM_FMTLINES = 0x00C8
EM_LINEFROMCHAR = 0x00C9
EM_SETTABSTOPS = 0x00CB
EM_SETPASSWORDCHAR = 0x00CC
EM_EMPTYUNDOBUFFER = 0x00CD
EM_GETFIRSTVISIBLELINE = 0x00CE
EM_SETREADONLY = 0x00CF
EM_GETPASSWORDCHAR = 0x00D2
EM_SETMARGINS = 0x00D3
EM_GETMARGINS = 0x00D4
EM_SETLIMITTEXT = EM_LIMITTEXT
EM_GETLIMITTEXT = 0x00D5
EM_POSFROMCHAR = 0x00D6
EM_CHARFROMPOS = 0x00D7

# List Box control

LB_OKAY = 0
LB_ERR = (-1)
LB_ERRSPACE = (-2)
LBN_ERRSPACE = (-2)
LBN_SELCHANGE = 1
LBN_DBLCLK = 2
LBN_SELCANCEL = 3
LBN_SETFOCUS = 4
LBN_KILLFOCUS = 5
LB_ADDSTRING = 0x0180
LB_INSERTSTRING = 0x0181
LB_DELETESTRING = 0x0182
LB_SELITEMRANGEEX = 0x0183
LB_RESETCONTENT = 0x0184
LB_SETSEL = 0x0185
LB_SETCURSEL = 0x0186
LB_GETSEL = 0x0187
LB_GETCURSEL = 0x0188
LB_GETTEXT = 0x0189
LB_GETTEXTLEN = 0x018A
LB_GETCOUNT = 0x018B
LB_SELECTSTRING = 0x018C
LB_GETTOPINDEX = 0x018E
LB_FINDSTRING = 0x018F
LB_GETSELCOUNT = 0x0190
LB_GETSELITEMS = 0x0191
LB_SETTABSTOPS = 0x0192
LB_GETHORIZONTALEXTENT = 0x0193
LB_SETHORIZONTALEXTENT = 0x0194
LB_SETCOLUMNWIDTH = 0x0195
LB_SETTOPINDEX = 0x0197
LB_GETITEMRECT = 0x0198
LB_GETITEMDATA = 0x0199
LB_SETITEMDATA = 0x019A
LB_SELITEMRANGE = 0x019B
LB_SETANCHORINDEX = 0x019C
LB_GETANCHORINDEX = 0x019D
LB_SETCARETINDEX = 0x019E
LB_GETCARETINDEX = 0x019F
LB_SETITEMHEIGHT = 0x01A0
LB_GETITEMHEIGHT = 0x01A1
LB_FINDSTRINGEXACT = 0x01A2
LB_SETLOCALE = 0x01A5
LB_GETLOCALE = 0x01A6
LB_INITSTORAGE = 0x01A8
LB_ITEMFROMPOINT = 0x01A9
LB_RESERVED0x01C0 = 0x01C0
LB_RESERVED0x01C1 = 0x01C1
LB_MSGMAX = 0x01C9
LB_MSGMAX = 0x01A8
LBS_NOTIFY = 0x0001L
LBS_SORT = 0x0002L
LBS_NOREDRAW = 0x0004L
LBS_MULTIPLESEL = 0x0008L
LBS_HASSTRINGS = 0x0040L
LBS_USETABSTOPS = 0x0080L
LBS_NOINTEGRALHEIGHT = 0x0100L
LBS_MULTICOLUMN = 0x0200L
LBS_WANTKEYBOARDINPUT = 0x0400L
LBS_EXTENDEDSEL = 0x0800L
LBS_DISABLENOSCROLL = 0x1000L
LBS_NODATA = 0x2000L
LBS_NOSEL = 0x4000L
LBS_STANDARD = (LBS_NOTIFY | LBS_SORT | WS_VSCROLL | WS_BORDER)
LBS_EX_CONSTSTRINGDATA = 0x00000002L

LVM_DELETECOLUMN = (LVM_FIRST + 28) 

CB_OKAY = 0
CB_ERR = (-1)
CB_ERRSPACE = (-2)
CBN_ERRSPACE = (-1)
CBN_SELCHANGE = 1
CBN_DBLCLK = 2
CBN_SETFOCUS = 3
CBN_KILLFOCUS = 4
CBN_EDITCHANGE = 5
CBN_EDITUPDATE = 6
CBN_DROPDOWN = 7
CBN_CLOSEUP = 8
CBN_SELENDOK = 9
CBN_SELENDCANCEL = 10
CBS_DROPDOWN = 0x0002L
CBS_DROPDOWNLIST = 0x0003L
CBS_AUTOHSCROLL = 0x0040L
CBS_OEMCONVERT = 0x0080L
CBS_SORT = 0x0100L
CBS_HASSTRINGS = 0x0200L
CBS_NOINTEGRALHEIGHT = 0x0400L
CBS_DISABLENOSCROLL = 0x0800L
CBS_UPPERCASE = 0x2000L
CBS_LOWERCASE = 0x4000L
CBS_EX_CONSTSTRINGDATA = 0x00000002L
CB_GETEDITSEL = 0x0140
CB_LIMITTEXT = 0x0141
CB_SETEDITSEL = 0x0142
CB_ADDSTRING = 0x0143
CB_DELETESTRING = 0x0144
CB_GETCOUNT = 0x0146
CB_GETCURSEL = 0x0147
CB_GETLBTEXT = 0x0148
CB_GETLBTEXTLEN = 0x0149
CB_INSERTSTRING = 0x014A
CB_RESETCONTENT = 0x014B
CB_FINDSTRING = 0x014C
CB_SELECTSTRING = 0x014D
CB_SETCURSEL = 0x014E
CB_SHOWDROPDOWN = 0x014F
CB_GETITEMDATA = 0x0150
CB_SETITEMDATA = 0x0151
CB_GETDROPPEDCONTROLRECT = 0x0152
CB_SETITEMHEIGHT = 0x0153
CB_GETITEMHEIGHT = 0x0154
CB_SETEXTENDEDUI = 0x0155
CB_GETEXTENDEDUI = 0x0156
CB_GETDROPPEDSTATE = 0x0157
CB_FINDSTRINGEXACT = 0x0158
CB_SETLOCALE = 0x0159
CB_GETLOCALE = 0x015A
CB_GETTOPINDEX = 0x015b
CB_SETTOPINDEX = 0x015c
CB_GETHORIZONTALEXTENT = 0x015d
CB_SETHORIZONTALEXTENT = 0x015e
CB_GETDROPPEDWIDTH = 0x015f
CB_SETDROPPEDWIDTH = 0x0160
CB_INITSTORAGE = 0x0161
CB_GETCOMBOBOXINFO = 0x0162
CB_MSGMAX = 0x0163
CB_MSGMAX = 0x015B

LVCFMT_LEFT = 0x0000
LVCFMT_RIGHT = 0x0001
LVCFMT_CENTER = 0x0002

LVS_SINGLESEL = 0x0004
LVM_DELETEITEM = (LVM_FIRST + 8)
LVM_ENSUREVISIBLE = (LVM_FIRST + 19)
LVN_ITEMACTIVATE = LVN_FIRST - 14

TVGN_PARENT = 0x3
TVGN_PREVIOUS = 0x2

TBS_HORZ = 0x0
TBS_VERT = 0x2

COMCTL32_VERSION = 0x020c
CCM_FIRST = 0x2000
CCM_SETVERSION = CCM_FIRST+0x7
CCM_GETVERSION = CCM_FIRST+0x8
TCS_BOTTOM = 0x2 


UDS_SETBUDDYINT = 2
UDM_SETBUDDY = WM_USER + 105
UDM_GETBUDDY = WM_USER + 106
UDM_SETRANGE32 = WM_USER + 111
UDM_GETRANGE32 = WM_USER + 112
UDM_SETPOS32 = WM_USER + 113
UDM_GETPOS32 = WM_USER + 114

UDN_DELTAPOS = 4294966574

########NEW FILE########
__FILENAME__ = loadframe
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import wx
from wx.lib import filebrowsebutton

from .wxlocale import _
from .vaultframe import VaultFrame
from ...vault import Vault
from ...config import config


class LoadFrame(wx.Frame):
    """
    Displays the "welcome" dialog which lets the user open a Vault.
    """
    def __init__(self, *args, **kwds):
        # begin wxGlade: ChooseVaultFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.panel_1 = wx.Panel(self, -1)
        self._lb_passwd = wx.StaticText(self.panel_1, -1, _("Password") + ":")
        self._tc_passwd = wx.TextCtrl(self.panel_1, -1, "", style=wx.TE_PASSWORD)
        self.bitmap_1 = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap(os.path.join(os.path.dirname(os.path.realpath(config.get_basescript())), "resources", "loxodo-icon.png"), wx.BITMAP_TYPE_ANY))
        self._fb_filename = filebrowsebutton.FileBrowseButtonWithHistory(self.panel_1, -1, size=(450, -1),  changeCallback = self._on_pickvault, labelText = _("Vault") + ":")
        if (config.recentvaults):
            self._fb_filename.SetHistory(config.recentvaults, 0)
        self.static_line_1 = wx.StaticLine(self.panel_1, -1)

        self.SetTitle("Loxodo - " + _("Open Vault"))

        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.VERTICAL)

        sizer_3.Add(self.bitmap_1, 1, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        sizer_3.Add(self._fb_filename, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 5)

        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5.Add(self._lb_passwd, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer_5.Add(self._tc_passwd, 1, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        sizer_3.Add(sizer_5, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)

        sizer_3.Add(self.static_line_1, 0, wx.TOP|wx.EXPAND, 10)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btn = wx.Button(self.panel_1, wx.ID_NEW)
        wx.EVT_BUTTON(self, wx.ID_NEW, self._on_new)
        btnsizer.Add(btn, 0, wx.TOP | wx.RIGHT, 10)
        btn = wx.Button(self.panel_1, wx.ID_OPEN)
        wx.EVT_BUTTON(self, wx.ID_OPEN, self._on_open)
        btn.SetDefault()
        btnsizer.Add(btn, 0, wx.TOP | wx.RIGHT, 10)
        sizer_3.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM, 5)

        self.panel_1.SetSizer(sizer_3)
        sizer_2.Add(self.panel_1, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(sizer_2)
        sizer_2.Fit(self)
        self.Layout()
        self.SetMinSize(self.GetSize())
        self.SetMaxSize((-1, self.GetSize().height))
        self._tc_passwd.SetFocus()

    def _on_pickvault(self, evt):
        pass

    def _on_new(self, dummy):
        password = self._tc_passwd.GetValue().encode('latin1', 'replace')

        filename = self._fb_filename.GetValue()
        wildcard = "|".join((_("Vault") + " (*.psafe3)", "*.psafe3", _("All files") + " (*.*)", "*.*"))
        dialog = wx.FileDialog(self, message = _("Save new Vault as..."), defaultFile = filename, wildcard = wildcard, style = wx.SAVE | wx.OVERWRITE_PROMPT)
        if dialog.ShowModal() != wx.ID_OK:
            return
        filename = dialog.GetPath()
        dialog.Destroy()

        Vault.create(password, filename=filename)
        self._fb_filename.SetValue(filename)

        dial = wx.MessageDialog(self,
                                _('A new Vault has been created using the given password. You can now proceed to open the Vault.'),
                                _('Vault Created'),
                                wx.OK | wx.ICON_INFORMATION
                                )
        dial.ShowModal()
        dial.Destroy()
        self._tc_passwd.SetFocus()
        self._tc_passwd.SelectAll()

    def _on_open(self, dummy):
        try:
            password = self._tc_passwd.GetValue().encode('latin1', 'replace')
            vaultframe = VaultFrame(None, -1, "")
            vaultframe.open_vault(self._fb_filename.GetValue(), password)
            config.recentvaults.insert(0, self._fb_filename.GetValue())
            config.save()
            self.Hide()
            vaultframe.Show()
            self.Destroy()
        except Vault.BadPasswordError:
            vaultframe.Destroy()
            dial = wx.MessageDialog(self,
                                    _('The given password does not match the Vault'),
                                    _('Bad Password'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()
            self._tc_passwd.SetFocus()
            self._tc_passwd.SelectAll()
        except Vault.VaultVersionError:
            vaultframe.Destroy()
            dial = wx.MessageDialog(self,
                                    _('This is not a PasswordSafe V3 Vault'),
                                    _('Bad Vault'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()
        except Vault.VaultFormatError:
            vaultframe.Destroy()
            dial = wx.MessageDialog(self,
                                    _('Vault integrity check failed'),
                                    _('Bad Vault'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()


########NEW FILE########
__FILENAME__ = loxodo
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import wx

from .wxlocale import _
from .wxlocale import setup_wx_locale
from .loadframe import LoadFrame


def main():
    app = wx.App(False)
    setup_wx_locale()
    mainframe = LoadFrame(None, -1, "")
    app.SetTopWindow(mainframe)
    mainframe.Show()
    app.MainLoop()


main()


########NEW FILE########
__FILENAME__ = mergeframe
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import wx

from .wxlocale import _


class MergeFrame(wx.Dialog):
    """
    Displays a list of Vault Records for interactive merge of Vaults.
    """
    def __init__(self, parent, oldrecord_newrecord_reason_pairs):
        wx.Dialog.__init__(self, parent, -1, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.panel = wx.Panel(self, -1)

        _sz_main = wx.BoxSizer(wx.VERTICAL)

        _lb_text = wx.StaticText(self.panel, -1, _("Select the Records to merge into this Vault") + ":")
        _sz_main.Add(_lb_text)

        self._cl_records = wx.CheckListBox(self.panel, -1)
        self._cl_records.AppendItems(['"' + newrecord.title + '" (' + reason + ')' for (oldrecord, newrecord, reason) in oldrecord_newrecord_reason_pairs])
        for i in range(len(oldrecord_newrecord_reason_pairs)):
            self._cl_records.Check(i)
        _sz_main.Add(self._cl_records, 1, wx.EXPAND | wx.GROW)

        _ln_line = wx.StaticLine(self.panel, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        _sz_main.Add(_ln_line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self.panel, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btn = wx.Button(self.panel, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        _sz_main.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM, 5)

        self.panel.SetSizer(_sz_main)
        _sz_frame = wx.BoxSizer()
        _sz_frame.Add(self.panel, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(_sz_frame)

        self.SetTitle("Loxodo - " + _("Merge Vault Records"))
        self.Layout()

        self.Fit()
        self.SetMinSize(self.GetSize())

        self._vault_record = None
        self.refresh_subscriber = None

        self.oldrecord_newrecord_reason_pairs = oldrecord_newrecord_reason_pairs

    def get_checked_items(self):
        return [self.oldrecord_newrecord_reason_pairs[i] for i in range(len(self.oldrecord_newrecord_reason_pairs)) if self._cl_records.IsChecked(i)]


########NEW FILE########
__FILENAME__ = recordframe
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import platform
import random
import struct
import wx

from .wxlocale import _
from ...config import config


class RecordFrame(wx.Dialog):
    """
    Displays (and lets the user edit) a single Vault Record.
    """
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        wx.EVT_CLOSE(self, self._on_frame_close)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_escape)

        self.panel = wx.Panel(self, -1)

        _sz_main = wx.BoxSizer(wx.VERTICAL)
        _sz_fields = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        _sz_fields.AddGrowableCol(1)
        _sz_fields.AddGrowableRow(5)
        self._tc_title = self._add_a_textcontrol(_sz_fields, _("Title") + ":", "")
        self._tc_group = self._add_a_textcontrol(_sz_fields, _("Group") + ":", "")
        self._tc_user = self._add_a_textcontrol(_sz_fields, _("Username") + ":", "")
        (self._tc_passwd, self._tc_passwd_alt, self._bt_showhide) = self._add_a_passwdfield(_sz_fields, _("Password") + ":", "")
        self._tc_url = self._add_a_textcontrol(_sz_fields, _("URL") + ":", "")
        self._tc_notes = self._add_a_textbox(_sz_fields, _("Notes") + ":", "")
        _sz_main.Add(_sz_fields, 1, wx.EXPAND | wx.GROW)

        _ln_line = wx.StaticLine(self.panel, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        _sz_main.Add(_ln_line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self.panel, wx.ID_CANCEL)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self._on_cancel)
        btnsizer.AddButton(btn)
        btn = wx.Button(self.panel, wx.ID_OK)
        wx.EVT_BUTTON(self, wx.ID_OK, self._on_ok)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        _sz_main.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM, 5)

        self.panel.SetSizer(_sz_main)
        _sz_frame = wx.BoxSizer()
        _sz_frame.Add(self.panel, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(_sz_frame)

        self.SetTitle("Loxodo - " + _("Edit Vault Record"))
        self.Layout()

        self.Fit()
        sz = self.GetSize()
        sz[1] = sz[1] + 100
        self.SetMinSize(sz)

        self.set_initial_focus()

        self._vault_record = None

    def _add_a_textcontrol(self, parent_sizer, label, default_value, extrastyle=0):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5)
        control = wx.TextCtrl(self.panel, -1, default_value, style=extrastyle, size=(128, -1))
        parent_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        return control

    def _add_a_passwdfield(self, parent_sizer, label, default_value):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5)
        r_container = wx.BoxSizer()
        parent_sizer.Add(r_container, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        r_masked = wx.TextCtrl(self.panel, -1, default_value, style=wx.PASSWORD, size=(128, -1))
        r_container.Add(r_masked, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.EXPAND, 0)
        r_shown = wx.TextCtrl(self.panel, -1, default_value, size=(128, -1))
        r_shown.Hide()
        r_container.Add(r_shown, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.EXPAND, 0)
        r_toggle = wx.Button(self.panel, wx.ID_MORE, _("(un)mask"))
        wx.EVT_BUTTON(self, wx.ID_MORE, self._on_toggle_passwd_mask)
        r_container.Add(r_toggle, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.SHRINK|wx.LEFT, 10)
        r_generate = wx.Button(self.panel, wx.ID_REPLACE, _("generate"))
        wx.EVT_BUTTON(self, wx.ID_REPLACE, self._on_generate_passwd)
        r_container.Add(r_generate, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.SHRINK|wx.LEFT, 10)
        return (r_masked, r_shown, r_toggle)

    def _add_a_textbox(self, parent_sizer, label, default_value):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALL|wx.ALIGN_TOP|wx.ALIGN_RIGHT, 5)
        control = wx.TextCtrl(self.panel, -1, default_value, style=wx.TE_MULTILINE, size=(128, 128))
        parent_sizer.Add(control, 1, wx.ALIGN_TOP|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        return control

    @staticmethod
    def _crlf_to_native(text):
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        return text

    @staticmethod
    def _native_to_crlf(text):
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")
        text = text.replace("\n", "\r\n")
        return text

    def update_fields(self):
        """
        Update fields from source
        """
        if (self._vault_record is not None):
            self._tc_group.SetValue(self._vault_record.group)
            self._tc_title.SetValue(self._vault_record.title)
            self._tc_user.SetValue(self._vault_record.user)
            self._tc_passwd.SetValue(self._vault_record.passwd)
            self._tc_url.SetValue(self._vault_record.url)
            self._tc_notes.SetValue(self._crlf_to_native(self._vault_record.notes))

    def _apply_changes(self, dummy):
        """
        Update source from fields
        """
        if (not self._vault_record is None):
            self._vault_record.group = self._tc_group.Value
            self._vault_record.title = self._tc_title.Value
            self._vault_record.user = self._tc_user.Value
            self._vault_record.passwd = self._tc_passwd.Value
            self._vault_record.url = self._tc_url.Value
            self._vault_record.notes = self._native_to_crlf(self._tc_notes.Value)

    def _on_cancel(self, dummy):
        """
        Event handler: Fires when user chooses this button.
        """
        self.EndModal(wx.ID_CANCEL);

    def _on_ok(self, evt):
        """
        Event handler: Fires when user chooses this button.
        """
        self._apply_changes(evt)
        self.EndModal(wx.ID_OK);

    def _on_toggle_passwd_mask(self, dummy):
        _tmp = self._tc_passwd
        _passwd = _tmp.GetValue()
        self._tc_passwd = self._tc_passwd_alt
        self._tc_passwd_alt = _tmp
        self._tc_passwd.Show()
        self._tc_passwd_alt.Hide()
        self._tc_passwd.GetParent().Layout()
        self._tc_passwd.SetValue(_passwd)
        if (self._tc_passwd_alt.FindFocus() == self._tc_passwd_alt):
            self._tc_passwd.SetFocus()

    def _on_generate_passwd(self, dummy):
        _pwd = self.generate_password(alphabet=config.alphabet,pwd_length=config.pwlength,allow_reduction=config.reduction)
        self._tc_passwd.SetValue(_pwd)

    @staticmethod
    def _urandom(count):
        try:
            return os.urandom(count)
        except NotImplementedError:
            retval = ""
            for dummy in range(count):
                retval += struct.pack("<B", random.randint(0, 0xFF))
            return retval

    @staticmethod
    def generate_password(alphabet="abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_", pwd_length=8, allow_reduction=False):
        # remove some easy-to-mistake characters
        if allow_reduction:
            for _chr in "0OjlI1":
                alphabet = alphabet.replace(_chr, "")

        # iteratively pick one character from this alphabet to assemble password
        last_chr = "x"
        pwd = ""
        for dummy in range(pwd_length):
            # temporarily reduce alphabet to avoid easy-to-mistake character pairs
            alphabet2 = alphabet
            if allow_reduction:
                for _chr in ('cl', 'mn', 'nm', 'nn', 'rn', 'vv', 'VV'):
                    if last_chr == _chr[0]:
                        alphabet2 = alphabet.replace(_chr[1],"")

            _chr = alphabet2[int(len(alphabet2) / 256.0 * ord(RecordFrame._urandom(1)))]
            pwd += _chr
            last_chr = _chr

        return pwd

    def _on_frame_close(self, dummy):
        """
        Event handler: Fires when user closes the frame
        """
        self.EndModal(wx.ID_CANCEL);

    def _on_escape(self, evt):
        """
        Event handler: Fires when user presses a key
        """
        # If "Escape" was pressed, hide the frame
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL);
            return

        # Ignore all other keys
        evt.Skip()

    def set_initial_focus(self):
        self._tc_title.SetFocus()
        self._tc_title.SelectAll()

    def _set_vault_record(self, vault_record):
        self._vault_record = vault_record
        self.update_fields()

    def _get_vault_record(self):
        return self._vault_record

    vault_record = property(_get_vault_record, _set_vault_record)


########NEW FILE########
__FILENAME__ = settings
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import platform
import random
import struct
import wx

from .wxlocale import _
from ...config import config


class Settings(wx.Dialog):
    """
    Displays (and lets the user edit) a single Vault Record.
    """
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent)
        wx.EVT_CLOSE(self, self._on_frame_close)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_escape)

        self.panel = wx.Panel(self, -1)

        _sz_main = wx.BoxSizer(wx.VERTICAL)
        _sz_fields = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        _sz_fields.AddGrowableCol(1)
        _sz_fields.AddGrowableRow(5)

        self._search_notes = self._add_a_checkbox(_sz_fields,_("Search inside notes") + ":")
        self._search_passwd = self._add_a_checkbox(_sz_fields,_("Search inside passwords") + ":")

        self._sc_length = self._add_a_spincontrol(_sz_fields, _("Generated Password Length") + ":",4,128)

        _sz_main.Add(_sz_fields, 1, wx.EXPAND | wx.GROW)

        self._cb_reduction = self._add_a_checkbox(_sz_fields,_("Avoid easy to mistake chars") + ":")

        self._tc_alphabet = self._add_a_textcontrol(_sz_fields,_("Alphabet")+ ":",config.alphabet)

        _ln_line = wx.StaticLine(self.panel, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        _sz_main.Add(_ln_line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()
        btn = wx.Button(self.panel, wx.ID_CANCEL)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self._on_cancel)
        btnsizer.AddButton(btn)
        btn = wx.Button(self.panel, wx.ID_OK)
        wx.EVT_BUTTON(self, wx.ID_OK, self._on_ok)
        btn.SetDefault()
        btnsizer.AddButton(btn)
        btnsizer.Realize()
        _sz_main.Add(btnsizer, 0, wx.ALIGN_RIGHT | wx.TOP | wx.BOTTOM, 5)

        self.panel.SetSizer(_sz_main)
        _sz_frame = wx.BoxSizer()
        _sz_frame.Add(self.panel, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(_sz_frame)

        self.SetTitle("Loxodo - " + _("Settings"))
        self.Layout()

        self.Fit()
        self.SetMinSize(self.GetSize())

        self.set_initial_focus()
        self.update_fields()

    def _add_a_checkbox(self, parent_sizer, label, extrastyle=0):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5)
        control =        wx.CheckBox(self.panel,-1)
        parent_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        return control

    def _add_a_spincontrol(self, parent_sizer, label, min, max, extrastyle=0):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5)
        control = wx.SpinCtrl(self.panel, -1, style=extrastyle, size=(12, -1))
        control.SetRange(min,max)
        parent_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        return control

    def _add_a_textcontrol(self, parent_sizer, label, default_value, extrastyle=0):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5)
        control = wx.TextCtrl(self.panel, -1, default_value, style=extrastyle, size=(128, -1))
        parent_sizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        return control

    def _add_a_textbox(self, parent_sizer, label, default_value):
        _label = wx.StaticText(self.panel, -1, label, style=wx.ALIGN_RIGHT)
        parent_sizer.Add(_label, 0, wx.ALL|wx.ALIGN_TOP|wx.ALIGN_RIGHT, 5)
        control = wx.TextCtrl(self.panel, -1, default_value, style=wx.TE_MULTILINE, size=(128, -1))
        parent_sizer.Add(control, 1, wx.ALIGN_TOP|wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 5)
        return control

    def update_fields(self):
        """
        Update fields from source
        """
        self._sc_length.SetValue(config.pwlength)
        self._tc_alphabet.SetValue(config.alphabet)
        self._cb_reduction.SetValue(config.reduction)
        self._search_notes.SetValue(config.search_notes)
        self._search_passwd.SetValue(config.search_passwd)

    def _apply_changes(self, dummy):
        """
        Update source from fields
        """
        config.pwlength = self._sc_length.GetValue()
        config.reduction = self._cb_reduction.GetValue()
        config.search_notes = self._search_notes.GetValue()
        config.search_passwd = self._search_passwd.GetValue()
        config.alphabet = self._tc_alphabet.GetValue()
        config.save()

    def _on_cancel(self, dummy):
        """
        Event handler: Fires when user chooses this button.
        """
        self.EndModal(wx.ID_CANCEL);

    def _on_ok(self, evt):
        """
        Event handler: Fires when user chooses this button.
        """
        self._apply_changes(evt)
        self.EndModal(wx.ID_OK);

    def _on_frame_close(self, dummy):
        """
        Event handler: Fires when user closes the frame
        """
        self.EndModal(wx.ID_CANCEL);

    def _on_escape(self, evt):
        """
        Event handler: Fires when user presses a key
        """
        # If "Escape" was pressed, hide the frame
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL);
            return

        # Ignore all other keys
        evt.Skip()

    def set_initial_focus(self):
        self._sc_length.SetFocus()


########NEW FILE########
__FILENAME__ = vaultframe
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import os
import wx

from .wxlocale import _
from ...vault import Vault
from ...config import config
from .recordframe import RecordFrame
from .mergeframe import MergeFrame
from .settings import Settings


class VaultFrame(wx.Frame):
    """
    Displays (and lets the user edit) the Vault.
    """
    class VaultListCtrl(wx.ListCtrl):
        """
        wx.ListCtrl that contains the contents of a Vault.
        """
        def __init__(self, *args, **kwds):
            wx.ListCtrl.__init__(self, *args, **kwds)
            self.vault = None
            self._filterstring = ""
            self.displayed_entries = []
            self.InsertColumn(0, _("Title"))
            self.InsertColumn(1, _("Username"))
            self.InsertColumn(2, _("Group"))
            self.SetColumnWidth(0, 256)
            self.SetColumnWidth(1, 128)
            self.SetColumnWidth(2, 256)
            self.sort_function = lambda e1, e2: cmp(e1.group.lower(), e2.group.lower())
            self.update_fields()

        def OnGetItemText(self, item, col):
            """
            Return display text for entries of a virtual list

            Overrides the base classes' method.
            """
            # Workaround for obscure wxPython behaviour that leads to an empty wx.ListCtrl sometimes calling OnGetItemText
            if (item < 0) or (item >= len(self.displayed_entries)):
              return "--"

            if (col == 0):
                return self.displayed_entries[item].title
            if (col == 1):
                return self.displayed_entries[item].user
            if (col == 2):
                return self.displayed_entries[item].group
            return "--"

        def update_fields(self):
            """
            Update the visual representation of list.

            Extends the base classes' method.
            """
            if not self.vault:
                self.displayed_entries = []
                return
            self.displayed_entries = [record for record in self.vault.records if self.filter_record(record)]

            self.displayed_entries.sort(self.sort_function)
            self.SetItemCount(len(self.displayed_entries))
            wx.ListCtrl.Refresh(self)

        def filter_record(self,record):
            if record.title.lower().find(self._filterstring.lower()) >= 0:
               return True

            if record.group.lower().find(self._filterstring.lower()) >= 0:
               return True

            if record.user.lower().find(self._filterstring.lower()) >= 0:
               return True

            if config.search_notes:
             if record.notes.lower().find(self._filterstring.lower()) >= 0:
                return True

            if config.search_passwd:
             if record.passwd.find(self._filterstring) >= 0:
                return True

            return False

        def set_vault(self, vault):
            """
            Set the Vault this control should display.
            """
            self.vault = vault
            self.update_fields()
            self.select_first()

        def set_filter(self, filterstring):
            """
            Sets a filter string to limit the displayed entries
            """
            self._filterstring = filterstring
            self.update_fields()
            self.select_first()

        def deselect_all(self):
            """
            De-selects all items
            """
            while (self.GetFirstSelected() != -1):
                self.Select(self.GetFirstSelected(), False)

        def select_first(self):
            """
            Selects and focuses the first item (if there is one)
            """
            self.deselect_all()
            if (self.GetItemCount() > 0):
                self.Select(0, True)
                self.Focus(0)


    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        wx.EVT_CLOSE(self, self._on_frame_close)

        self.panel = wx.Panel(self, -1)

        self._searchbox = wx.SearchCtrl(self.panel, size=(200, -1))
        self._searchbox.ShowCancelButton(True)
        self.list = self.VaultListCtrl(self.panel, -1, size=(640, 240), style=wx.LC_REPORT|wx.SUNKEN_BORDER|wx.LC_VIRTUAL|wx.LC_EDIT_LABELS)
        self.list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self._on_list_contextmenu)
        self.list.Bind(wx.EVT_RIGHT_UP, self._on_list_contextmenu)

        self.statusbar = self.CreateStatusBar(1, wx.ST_SIZEGRIP)

        # Set up menus
        filemenu = wx.Menu()
        temp_id = wx.NewId()
        filemenu.Append(temp_id, _("Change &Password") + "...")
        wx.EVT_MENU(self, temp_id, self._on_change_password)
        temp_id = wx.NewId()
        filemenu.Append(temp_id, _("&Merge Records from") + "...")
        wx.EVT_MENU(self, temp_id, self._on_merge_vault)
        filemenu.Append(wx.ID_ABOUT, _("&About"))
        wx.EVT_MENU(self, wx.ID_ABOUT, self._on_about)
        filemenu.Append(wx.ID_PREFERENCES, _("&Settings"))
        wx.EVT_MENU(self, wx.ID_PREFERENCES, self._on_settings)
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT, _("E&xit"))
        wx.EVT_MENU(self, wx.ID_EXIT, self._on_exit)
        self._recordmenu = wx.Menu()
        self._recordmenu.Append(wx.ID_ADD, _("&Add\tCtrl+A"))
        wx.EVT_MENU(self, wx.ID_ADD, self._on_add)
        self._recordmenu.Append(wx.ID_DELETE, _("&Delete\tCtrl+Back"))
        wx.EVT_MENU(self, wx.ID_DELETE, self._on_delete)
        self._recordmenu.AppendSeparator()
        self._recordmenu.Append(wx.ID_PROPERTIES, _("&Edit\tCtrl+E"))
        wx.EVT_MENU(self, wx.ID_PROPERTIES, self._on_edit)
        self._recordmenu.AppendSeparator()
        temp_id = wx.NewId()
        self._recordmenu.Append(temp_id, _("Copy &Username\tCtrl+U"))
        wx.EVT_MENU(self, temp_id, self._on_copy_username)
        temp_id = wx.NewId()
        self._recordmenu.Append(temp_id, _("Copy &Password\tCtrl+P"))
        wx.EVT_MENU(self, temp_id, self._on_copy_password)
        temp_id = wx.NewId()
        self._recordmenu.Append(temp_id, _("Open UR&L\tCtrl+L"))
        wx.EVT_MENU(self, temp_id, self._on_open_url)
        menu_bar = wx.MenuBar()
        menu_bar.Append(filemenu, _("&Vault"))
        menu_bar.Append(self._recordmenu, _("&Record"))
        self.SetMenuBar(menu_bar)

        self.SetTitle("Loxodo - " + _("Vault Contents"))
        self.statusbar.SetStatusWidths([-1])
        statusbar_fields = [""]
        for i in range(len(statusbar_fields)):
            self.statusbar.SetStatusText(statusbar_fields[i], i)

        sizer = wx.BoxSizer(wx.VERTICAL)
        _rowsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_search_cancel, self._searchbox)
        self.Bind(wx.EVT_TEXT, self._on_search_do, self._searchbox)
        self._searchbox.Bind(wx.EVT_CHAR, self._on_searchbox_char)

        _rowsizer.Add(self._searchbox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 5)
        sizer.Add(_rowsizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer.Add(self.list, 1, wx.EXPAND, 0)
        self.panel.SetSizer(sizer)
        _sz_frame = wx.BoxSizer()
        _sz_frame.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(_sz_frame)

        sizer.Fit(self)
        self.Layout()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_list_item_activated, self.list)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self._on_list_item_label_edit, self.list)
        self.Bind(wx.EVT_LIST_COL_CLICK, self._on_list_column_click, self.list)

        self._searchbox.SetFocus()

        self.vault_file_name = None
        self.vault_password = None
        self.vault = None
        self._is_modified = False

    def mark_modified(self):
        self._is_modified = True
        if ((self.vault_file_name is not None) and (self.vault_password is not None)):
            self.save_vault(self.vault_file_name, self.vault_password)
        self.list.update_fields()

    def open_vault(self, filename, password):
        """
        Set the Vault that this frame should display.
        """
        self.vault_file_name = None
        self.vault_password = None
        self._is_modified = False
        self.vault = Vault(password, filename=filename)
        self.list.set_vault(self.vault)
        self.vault_file_name = filename
        self.vault_password = password
        self.statusbar.SetStatusText(_("Read Vault contents from disk"), 0)

    def save_vault(self, filename, password):
        """
        Write Vault contents to disk.
        """
        try:
            self._is_modified = False
            self.vault_file_name = filename
            self.vault_password = password
            self.vault.write_to_file(filename, password)
            self.statusbar.SetStatusText(_("Wrote Vault contents to disk"), 0)
        except RuntimeError:
            dial = wx.MessageDialog(self,
                                    _("Could not write Vault contents to disk"),
                                    _("Error writing to disk"),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()

    def _clear_clipboard(self, match_text = None):
        if match_text:
            if not wx.TheClipboard.Open():
                raise RuntimeError(_("Could not open clipboard"))
            try:
                clip_object = wx.TextDataObject()
                if wx.TheClipboard.GetData(clip_object):
                    if clip_object.GetText() != match_text:
                        return
            finally:
                wx.TheClipboard.Close()
        wx.TheClipboard.Clear()
        self.statusbar.SetStatusText(_('Cleared clipboard'), 0)

    def _copy_to_clipboard(self, text, duration = None):
        if not wx.TheClipboard.Open():
            raise RuntimeError(_("Could not open clipboard"))
        try:
            clip_object = wx.TextDataObject(text)
            wx.TheClipboard.SetData(clip_object)
            if duration:
                wx.FutureCall(duration * 1000, self._clear_clipboard, text)
        finally:
            wx.TheClipboard.Close()

    def _on_list_item_activated(self, event):
        """
        Event handler: Fires when user double-clicks a list entry.
        """
        index = event.GetIndex()
        self.list.deselect_all()
        self.list.Select(index, True)
        self.list.Focus(index)
        self._on_copy_password(None)

    def _on_list_item_label_edit(self, event):
        """
        Event handler: Fires when user edits an entry's label.
        """
        if event.IsEditCancelled():
            return
        index = event.GetIndex()
        entry = self.list.displayed_entries[index]
        label_str = event.GetLabel()
        if entry.title == label_str:
            return
        old_title = entry.title
        entry.title = label_str
        self.list.update_fields()
        self.statusbar.SetStatusText(_('Changed title of "%s"') % old_title, 0)
        self.mark_modified()

    def _on_list_column_click(self, event):
        """
        Event handler: Fires when user clicks on the list header.
        """
        col = event.GetColumn()
        if (col == 0):
            self.list.sort_function = lambda e1, e2: cmp(e1.title.lower(), e2.title.lower())
        if (col == 1):
            self.list.sort_function = lambda e1, e2: cmp(e1.user.lower(), e2.user.lower())
        if (col == 2):
            self.list.sort_function = lambda e1, e2: cmp(e1.group.lower(), e2.group.lower())
        self.list.update_fields()

    def _on_list_contextmenu(self, dummy):
        self.PopupMenu(self._recordmenu)

    def _on_about(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        gpl_v2 = """This program is free software; you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program;
if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA."""

        developers = (
                      "Christoph Sommer",
                      "Bjorn Edstrom (Python Twofish)",
                      "Brian Gladman (C Twofish)",
                      "Tim Kuhlman",
                      "David Eckhoff",
                      "Nick Verbeck"
                      )

        about = wx.AboutDialogInfo()
        about.SetIcon(wx.Icon(os.path.join(os.path.dirname(os.path.realpath(config.get_basescript())), "resources", "loxodo-icon.png"), wx.BITMAP_TYPE_PNG, 128, 128))
        about.SetName("Loxodo")
        about.SetVersion("0.0-git")
        about.SetCopyright("Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>")
        about.SetWebSite("http://www.christoph-sommer.de/loxodo")
        about.SetLicense(gpl_v2)
        about.SetDevelopers(developers)
        wx.AboutBox(about)

    def _on_settings(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        settings = Settings(self)
        settings.ShowModal()
        settings.Destroy()
        self.list.update_fields()

    def _on_change_password(self, dummy):

        # FIXME: choose new SALT, B1-B4, IV values on password change? Conflicting Specs!

        dial = wx.PasswordEntryDialog(self,
                                _("New password"),
                                _("Change Vault Password")
                                )
        retval = dial.ShowModal()
        password_new = dial.Value.encode('latin1', 'replace')
        dial.Destroy()
        if retval != wx.ID_OK:
            return

        dial = wx.PasswordEntryDialog(self,
                                _("Re-enter new password"),
                                _("Change Vault Password")
                                )
        retval = dial.ShowModal()
        password_new_confirm = dial.Value.encode('latin1', 'replace')
        dial.Destroy()
        if retval != wx.ID_OK:
            return
        if password_new_confirm != password_new:
            dial = wx.MessageDialog(self,
                                    _('The given passwords do not match'),
                                    _('Bad Password'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()
            return

        self.vault_password = password_new
        self.statusbar.SetStatusText(_('Changed Vault password'), 0)
        self.mark_modified()

    def _on_merge_vault(self, dummy):
        wildcard = "|".join((_("Vault") + " (*.psafe3)", "*.psafe3", _("All files") + " (*.*)", "*.*"))
        dialog = wx.FileDialog(self, message = _("Open Vault..."), defaultFile = self.vault_file_name, wildcard = wildcard, style = wx.FD_OPEN)
        if dialog.ShowModal() != wx.ID_OK:
            return
        filename = dialog.GetPath()
        dialog.Destroy()

        dial = wx.PasswordEntryDialog(self,
                                _("Password"),
                                _("Open Vault...")
                                )
        retval = dial.ShowModal()
        password = dial.Value.encode('latin1', 'replace')
        dial.Destroy()
        if retval != wx.ID_OK:
            return

        merge_vault = None
        try:
            merge_vault = Vault(password, filename=filename)
        except Vault.BadPasswordError:
            dial = wx.MessageDialog(self,
                                    _('The given password does not match the Vault'),
                                    _('Bad Password'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()
            return
        except Vault.VaultVersionError:
            dial = wx.MessageDialog(self,
                                    _('This is not a PasswordSafe V3 Vault'),
                                    _('Bad Vault'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()
            return
        except Vault.VaultFormatError:
            dial = wx.MessageDialog(self,
                                    _('Vault integrity check failed'),
                                    _('Bad Vault'),
                                    wx.OK | wx.ICON_ERROR
                                    )
            dial.ShowModal()
            dial.Destroy()
            return

        oldrecord_newrecord_reason_pairs = []  # list of (oldrecord, newrecord, reason) tuples to merge
        for record in merge_vault.records:
            # check if corresponding record exists in current Vault
            my_record = None
            for record2 in self.vault.records:
                if record2.is_corresponding(record):
                    my_record = record2
                    break

            # record is new
            if not my_record:
                oldrecord_newrecord_reason_pairs.append((None, record, _("new")))
                continue

            # record is more recent
            if record.is_newer_than(my_record):
                oldrecord_newrecord_reason_pairs.append((my_record, record, _('updates "%s"') % my_record.title))
                continue

        dial = MergeFrame(self, oldrecord_newrecord_reason_pairs)
        retval = dial.ShowModal()
        oldrecord_newrecord_reason_pairs = dial.get_checked_items()
        dial.Destroy()
        if retval != wx.ID_OK:
            return

        for (oldrecord, newrecord, reason) in oldrecord_newrecord_reason_pairs:
            if oldrecord:
                oldrecord.merge(newrecord)
            else:
                self.vault.records.append(newrecord)
        self.mark_modified()

    def _on_exit(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        self.Close(True)  # Close the frame.

    def _on_edit(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        index = self.list.GetFirstSelected()
        if (index is None):
            return
        entry = self.list.displayed_entries[index]

        recordframe = RecordFrame(self)
        recordframe.vault_record = entry
        if recordframe.ShowModal() != wx.ID_CANCEL:
            self.mark_modified()
        recordframe.Destroy()

    def _on_add(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        entry = self.vault.Record.create()

        recordframe = RecordFrame(self)
        recordframe.vault_record = entry
        if recordframe.ShowModal() != wx.ID_CANCEL:
            self.vault.records.append(entry)
            self.mark_modified()
        recordframe.Destroy()

    def _on_delete(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        index = self.list.GetFirstSelected()
        if (index == -1):
            return
        entry = self.list.displayed_entries[index]

        if ((entry.user != "") or (entry.passwd != "")):
            dial = wx.MessageDialog(self,
                                    _("Are you sure you want to delete this record? It contains a username or password and there is no way to undo this action."),
                                    _("Really delete record?"),
                                    wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION
                                    )
            retval = dial.ShowModal()
            dial.Destroy()
            if retval != wx.ID_YES:
                return

        self.vault.records.remove(entry)
        self.mark_modified()

    def _on_copy_username(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        index = self.list.GetFirstSelected()
        if (index == -1):
            return
        entry = self.list.displayed_entries[index]
        try:
            self._copy_to_clipboard(entry.user)
            self.statusbar.SetStatusText(_('Copied username of "%s" to clipboard') % entry.title, 0)
        except RuntimeError:
            self.statusbar.SetStatusText(_('Error copying username of "%s" to clipboard') % entry.title, 0)

    def _on_copy_password(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        index = self.list.GetFirstSelected()
        if (index == -1):
            return
        entry = self.list.displayed_entries[index]
        try:
            self._copy_to_clipboard(entry.passwd, duration=10)
            self.statusbar.SetStatusText(_('Copied password of "%s" to clipboard') % entry.title, 0)
        except RuntimeError:
            self.statusbar.SetStatusText(_('Error copying password of "%s" to clipboard') % entry.title, 0)

    def _on_open_url(self, dummy):
        """
        Event handler: Fires when user chooses this menu item.
        """
        index = self.list.GetFirstSelected()
        if (index == -1):
            return
        entry = self.list.displayed_entries[index]
        try:
            import webbrowser
            webbrowser.open(entry.url)
        except ImportError:
            self.statusbar.SetStatusText(_('Could not load python module "webbrowser" needed to open "%s"') % entry.url, 0)

    def _on_search_do(self, dummy):
        """
        Event handler: Fires when user interacts with search field
        """
        self.list.set_filter(self._searchbox.GetValue())

    def _on_search_cancel(self, dummy):
        """
        Event handler: Fires when user interacts with search field
        """
        self._searchbox.SetValue("")

    def _on_frame_close(self, dummy):
        """
        Event handler: Fires when user closes the frame
        """
        self.Destroy()

    def _on_searchbox_char(self, evt):
        """
        Event handler: Fires when user presses a key in self._searchbox
        """
        # If "Enter" was pressed, ignore key and copy password of first match
        if evt.GetKeyCode() == wx.WXK_RETURN:
            self._on_copy_password(None)
            return

        # If "Escape" was pressed, ignore key and clear the Search box
        if evt.GetKeyCode() == wx.WXK_ESCAPE:
            self._on_search_cancel(None)
            return

        # If "Up" or "Down" was pressed, ignore key and focus self.list
        if evt.GetKeyCode() in (wx.WXK_UP, wx.WXK_DOWN):
            self.list.SetFocus()
            return

        # Ignore all other keys
        evt.Skip()


########NEW FILE########
__FILENAME__ = wxlocale
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import wx
import os
from ...config import config

_ = wx.GetTranslation
LOXODO_LOCALE = None


def setup_wx_locale():
    """
    Set up internationalization support.
    """
    if 'unicode' not in wx.PlatformInfo:
        print "Warning: You need a unicode build of wxPython to run this application. Continuing anyway."
    try:
        localedir = os.path.join(os.path.dirname(os.path.realpath(config.get_basescript())), "locale")
        domain = "loxodo"

        from locale import getdefaultlocale
        langid = wx.LANGUAGE_DEFAULT
        try:
            (lang_name, dummy) = getdefaultlocale()
        except ValueError:
            pass
        else:
            if lang_name:
                langid = wx.Locale.FindLanguageInfo(lang_name).Language
        global LOXODO_LOCALE
        LOXODO_LOCALE = wx.Locale(langid)
        LOXODO_LOCALE.AddCatalogLookupPathPrefix(localedir)
        LOXODO_LOCALE.AddCatalog(domain)
    except:
        print "Warning: Setting up internationalization support failed. Continuing anyway."


########NEW FILE########
__FILENAME__ = twofish
## twofish.py - pure Python implementation of the Twofish algorithm.
## Bjorn Edstrom <be@bjrn.se> 13 december 2007.
##
## Copyrights
## ==========
##
## This code is a derived from an implementation by Dr Brian Gladman 
## (gladman@seven77.demon.co.uk) which is subject to the following license.
## This Python implementation is not subject to any other license.
##
##/* This is an independent implementation of the encryption algorithm:   */
##/*                                                                      */
##/*         Twofish by Bruce Schneier and colleagues                     */
##/*                                                                      */
##/* which is a candidate algorithm in the Advanced Encryption Standard   */
##/* programme of the US National Institute of Standards and Technology.  */
##/*                                                                      */
##/* Copyright in this implementation is held by Dr B R Gladman but I     */
##/* hereby give permission for its free direct or derivative use subject */
##/* to acknowledgment of its origin and compliance with any conditions   */
##/* that the originators of t he algorithm place on its exploitation.    */
##/*                                                                      */
##/* My thanks to Doug Whiting and Niels Ferguson for comments that led   */
##/* to improvements in this implementation.                              */
##/*                                                                      */
##/* Dr Brian Gladman (gladman@seven77.demon.co.uk) 14th January 1999     */
##
## The above copyright notice must not be removed.
##
## Information
## ===========
##
## Anyone thinking of using this code should reconsider. It's slow.
## Try python-mcrypt instead. In case a faster library is not installed
## on the target system, this code can be used as a portable fallback.

# pylint: disable-all

block_size = 16
key_size = 32

class Twofish:
    
    def __init__(self, key=None):
        """Twofish."""

        if key:
            self.set_key(key)


    def set_key(self, key):
        """Init."""
        
        key_len = len(key)
        if key_len not in [16, 24, 32]:
            # XXX: add padding?
            raise KeyError, "key must be 16, 24 or 32 bytes"
        if key_len % 4:
            # XXX: add padding?
            raise KeyError, "key not a multiple of 4"
        if key_len > 32:
            # XXX: prune?
            raise KeyError, "key_len > 32"
        
        self.context = TWI()
        
        key_word32 = [0] * 32
        i = 0
        while key:
            key_word32[i] = struct.unpack("<L", key[0:4])[0]
            key = key[4:]
            i += 1

        set_key(self.context, key_word32, key_len)

        
    def decrypt(self, block):
        """Decrypt blocks."""
        
        if len(block) % 16:
            raise ValueError, "block size must be a multiple of 16"

        plaintext = ''
        
        while block:
            a, b, c, d = struct.unpack("<4L", block[:16])
            temp = [a, b, c, d]
            decrypt(self.context, temp)
            plaintext += struct.pack("<4L", *temp)
            block = block[16:]
            
        return plaintext

        
    def encrypt(self, block):
        """Encrypt blocks."""

        if len(block) % 16:
            raise ValueError, "block size must be a multiple of 16"

        ciphertext = ''
        
        while block:
            a, b, c, d = struct.unpack("<4L", block[0:16])
            temp = [a, b, c, d]
            encrypt(self.context, temp)
            ciphertext += struct.pack("<4L", *temp)
            block = block[16:]
            
        return ciphertext


    def get_name(self):
        """Return the name of the cipher."""
        
        return "Twofish"


    def get_block_size(self):
        """Get cipher block size in bytes."""
        
        return 16

    
    def get_key_size(self):
        """Get cipher key size in bytes."""
        
        return 32


#
# Private.
#

import struct
import sys

WORD_BIGENDIAN = 0
if sys.byteorder == 'big':
    WORD_BIGENDIAN = 1

def rotr32(x, n):
    return (x >> n) | ((x << (32 - n)) & 0xFFFFFFFF)

def rotl32(x, n):
    return ((x << n) & 0xFFFFFFFF) | (x >> (32 - n))

def byteswap32(x):
    return ((x & 0xff) << 24) | (((x >> 8) & 0xff) << 16) | \
           (((x >> 16) & 0xff) << 8) | ((x >> 24) & 0xff)

class TWI:
    def __init__(self):
        self.k_len = 0 # word32
        self.l_key = [0]*40 # word32
        self.s_key = [0]*4 # word32
        self.qt_gen = 0 # word32
        self.q_tab = [[0]*256, [0]*256] # byte
        self.mt_gen = 0 # word32
        self.m_tab = [[0]*256, [0]*256, [0]*256, [0]*256] # word32
        self.mk_tab = [[0]*256, [0]*256, [0]*256, [0]*256] # word32

def byte(x, n):
    return (x >> (8 * n)) & 0xff

tab_5b = [0, 90, 180, 238]
tab_ef = [0, 238, 180, 90]
ror4 = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]
ashx = [0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12, 5, 14, 7]
qt0 = [[8, 1, 7, 13, 6, 15, 3, 2, 0, 11, 5, 9, 14, 12, 10, 4],
       [2, 8, 11, 13, 15, 7, 6, 14, 3, 1, 9, 4, 0, 10, 12, 5]]
qt1 = [[14, 12, 11, 8, 1, 2, 3, 5, 15, 4, 10, 6, 7, 0, 9, 13],
       [1, 14, 2, 11, 4, 12, 3, 7, 6, 13, 10, 5, 15, 9, 0, 8]]
qt2 = [[11, 10, 5, 14, 6, 13, 9, 0, 12, 8, 15, 3, 2, 4, 7, 1],
       [4, 12, 7, 5, 1, 6, 9, 10, 0, 14, 13, 8, 2, 11, 3, 15]]
qt3 = [[13, 7, 15, 4, 1, 2, 6, 14, 9, 11, 3, 0, 8, 5, 12, 10],
       [11, 9, 5, 1, 12, 3, 13, 14, 6, 4, 7, 15, 2, 0, 8, 10]]

def qp(n, x): # word32, byte
    n %= 0x100000000
    x %= 0x100
    a0 = x >> 4;
    b0 = x & 15;
    a1 = a0 ^ b0;
    b1 = ror4[b0] ^ ashx[a0];
    a2 = qt0[n][a1];
    b2 = qt1[n][b1];
    a3 = a2 ^ b2;
    b3 = ror4[b2] ^ ashx[a2];
    a4 = qt2[n][a3];
    b4 = qt3[n][b3];
    return (b4 << 4) | a4;

def gen_qtab(pkey):
    for i in xrange(256):
        pkey.q_tab[0][i] = qp(0, i)
        pkey.q_tab[1][i] = qp(1, i)
        
def gen_mtab(pkey):
    for i in xrange(256):
        f01 = pkey.q_tab[1][i]
        f01 = pkey.q_tab[1][i];
        f5b = ((f01) ^ ((f01) >> 2) ^ tab_5b[(f01) & 3]);
        fef = ((f01) ^ ((f01) >> 1) ^ ((f01) >> 2) ^ tab_ef[(f01) & 3]);
        pkey.m_tab[0][i] = f01 + (f5b << 8) + (fef << 16) + (fef << 24);
        pkey.m_tab[2][i] = f5b + (fef << 8) + (f01 << 16) + (fef << 24);

        f01 = pkey.q_tab[0][i];
        f5b = ((f01) ^ ((f01) >> 2) ^ tab_5b[(f01) & 3]);
        fef = ((f01) ^ ((f01) >> 1) ^ ((f01) >> 2) ^ tab_ef[(f01) & 3]);
        pkey.m_tab[1][i] = fef + (fef << 8) + (f5b << 16) + (f01 << 24);
        pkey.m_tab[3][i] = f5b + (f01 << 8) + (fef << 16) + (f5b << 24);

def gen_mk_tab(pkey, key):
    if pkey.k_len == 2:
        for i in xrange(256):
            by = i % 0x100
            pkey.mk_tab[0][i] = pkey.m_tab[0][pkey.q_tab[0][pkey.q_tab[0][by] ^ byte(key[1],0)] ^ byte(key[0],0)];
            pkey.mk_tab[1][i] = pkey.m_tab[1][pkey.q_tab[0][pkey.q_tab[1][by] ^ byte(key[1],1)] ^ byte(key[0],1)];
            pkey.mk_tab[2][i] = pkey.m_tab[2][pkey.q_tab[1][pkey.q_tab[0][by] ^ byte(key[1],2)] ^ byte(key[0],2)];
            pkey.mk_tab[3][i] = pkey.m_tab[3][pkey.q_tab[1][pkey.q_tab[1][by] ^ byte(key[1],3)] ^ byte(key[0],3)];
    if pkey.k_len == 3:
        for i in xrange(256):
            by = i % 0x100
            pkey.mk_tab[0][i] = pkey.m_tab[0][pkey.q_tab[0][pkey.q_tab[0][pkey.q_tab[1][by] ^ byte(key[2], 0)] ^ byte(key[1], 0)] ^ byte(key[0], 0)];
            pkey.mk_tab[1][i] = pkey.m_tab[1][pkey.q_tab[0][pkey.q_tab[1][pkey.q_tab[1][by] ^ byte(key[2], 1)] ^ byte(key[1], 1)] ^ byte(key[0], 1)];
            pkey.mk_tab[2][i] = pkey.m_tab[2][pkey.q_tab[1][pkey.q_tab[0][pkey.q_tab[0][by] ^ byte(key[2], 2)] ^ byte(key[1], 2)] ^ byte(key[0], 2)];
            pkey.mk_tab[3][i] = pkey.m_tab[3][pkey.q_tab[1][pkey.q_tab[1][pkey.q_tab[0][by] ^ byte(key[2], 3)] ^ byte(key[1], 3)] ^ byte(key[0], 3)];
    if pkey.k_len == 4:
        for i in xrange(256):
            by = i % 0x100
            pkey.mk_tab[0][i] = pkey.m_tab[0][pkey.q_tab[0][pkey.q_tab[0][pkey.q_tab[1][pkey.q_tab[1][by] ^ byte(key[3], 0)] ^ byte(key[2], 0)] ^ byte(key[1], 0)] ^ byte(key[0], 0)];
            pkey.mk_tab[1][i] = pkey.m_tab[1][pkey.q_tab[0][pkey.q_tab[1][pkey.q_tab[1][pkey.q_tab[0][by] ^ byte(key[3], 1)] ^ byte(key[2], 1)] ^ byte(key[1], 1)] ^ byte(key[0], 1)];
            pkey.mk_tab[2][i] = pkey.m_tab[2][pkey.q_tab[1][pkey.q_tab[0][pkey.q_tab[0][pkey.q_tab[0][by] ^ byte(key[3], 2)] ^ byte(key[2], 2)] ^ byte(key[1], 2)] ^ byte(key[0], 2)];
            pkey.mk_tab[3][i] = pkey.m_tab[3][pkey.q_tab[1][pkey.q_tab[1][pkey.q_tab[0][pkey.q_tab[1][by] ^ byte(key[3], 3)] ^ byte(key[2], 3)] ^ byte(key[1], 3)] ^ byte(key[0], 3)];

def h_fun(pkey, x, key):
    b0 = byte(x, 0);
    b1 = byte(x, 1);
    b2 = byte(x, 2);
    b3 = byte(x, 3);
    if pkey.k_len >= 4:
        b0 = pkey.q_tab[1][b0] ^ byte(key[3], 0);
        b1 = pkey.q_tab[0][b1] ^ byte(key[3], 1);
        b2 = pkey.q_tab[0][b2] ^ byte(key[3], 2);
        b3 = pkey.q_tab[1][b3] ^ byte(key[3], 3);
    if pkey.k_len >= 3:
        b0 = pkey.q_tab[1][b0] ^ byte(key[2], 0);
        b1 = pkey.q_tab[1][b1] ^ byte(key[2], 1);
        b2 = pkey.q_tab[0][b2] ^ byte(key[2], 2);
        b3 = pkey.q_tab[0][b3] ^ byte(key[2], 3);
    if pkey.k_len >= 2:
        b0 = pkey.q_tab[0][pkey.q_tab[0][b0] ^ byte(key[1], 0)] ^ byte(key[0], 0);
        b1 = pkey.q_tab[0][pkey.q_tab[1][b1] ^ byte(key[1], 1)] ^ byte(key[0], 1);
        b2 = pkey.q_tab[1][pkey.q_tab[0][b2] ^ byte(key[1], 2)] ^ byte(key[0], 2);
        b3 = pkey.q_tab[1][pkey.q_tab[1][b3] ^ byte(key[1], 3)] ^ byte(key[0], 3);      
    return pkey.m_tab[0][b0] ^ pkey.m_tab[1][b1] ^ pkey.m_tab[2][b2] ^ pkey.m_tab[3][b3];   

def mds_rem(p0, p1):
    i, t, u = 0, 0, 0
    for i in xrange(8):
        t = p1 >> 24
        p1 = ((p1 << 8) & 0xffffffff) | (p0 >> 24)
        p0 = (p0 << 8) & 0xffffffff
        u = (t << 1) & 0xffffffff
        if t & 0x80:
            u ^= 0x0000014d
        p1 ^= t ^ ((u << 16) & 0xffffffff)
        u ^= (t >> 1)
        if t & 0x01:
            u ^= 0x0000014d >> 1
        p1 ^= ((u << 24) & 0xffffffff) | ((u << 8) & 0xffffffff)
    return p1

def set_key(pkey, in_key, key_len):
    pkey.qt_gen = 0
    if not pkey.qt_gen:
        gen_qtab(pkey)
        pkey.qt_gen = 1
    pkey.mt_gen = 0
    if not pkey.mt_gen:
        gen_mtab(pkey)
        pkey.mt_gen = 1
    pkey.k_len = (key_len * 8) / 64

    a = 0
    b = 0
    me_key = [0,0,0,0]
    mo_key = [0,0,0,0]
    for i in xrange(pkey.k_len):
        if WORD_BIGENDIAN:
            a = byteswap32(in_key[i + 1])
            me_key[i] = a            
            b = byteswap32(in_key[i + i + 1])
        else:
            a = in_key[i + i]
            me_key[i] = a            
            b = in_key[i + i + 1]
        mo_key[i] = b
        pkey.s_key[pkey.k_len - i - 1] = mds_rem(a, b);
    for i in xrange(0, 40, 2):
        a = (0x01010101 * i) % 0x100000000;
        b = (a + 0x01010101) % 0x100000000;
        a = h_fun(pkey, a, me_key);
        b = rotl32(h_fun(pkey, b, mo_key), 8);
        pkey.l_key[i] = (a + b) % 0x100000000;
        pkey.l_key[i + 1] = rotl32((a + 2 * b) % 0x100000000, 9);
    gen_mk_tab(pkey, pkey.s_key)

def encrypt(pkey, in_blk):
    blk = [0, 0, 0, 0]

    if WORD_BIGENDIAN:
        blk[0] = byteswap32(in_blk[0]) ^ pkey.l_key[0];
        blk[1] = byteswap32(in_blk[1]) ^ pkey.l_key[1];
        blk[2] = byteswap32(in_blk[2]) ^ pkey.l_key[2];
        blk[3] = byteswap32(in_blk[3]) ^ pkey.l_key[3];
    else:
        blk[0] = in_blk[0] ^ pkey.l_key[0];
        blk[1] = in_blk[1] ^ pkey.l_key[1];
        blk[2] = in_blk[2] ^ pkey.l_key[2];
        blk[3] = in_blk[3] ^ pkey.l_key[3];        

    for i in xrange(8):
        t1 = ( pkey.mk_tab[0][byte(blk[1],3)] ^ pkey.mk_tab[1][byte(blk[1],0)] ^ pkey.mk_tab[2][byte(blk[1],1)] ^ pkey.mk_tab[3][byte(blk[1],2)] ); 
        t0 = ( pkey.mk_tab[0][byte(blk[0],0)] ^ pkey.mk_tab[1][byte(blk[0],1)] ^ pkey.mk_tab[2][byte(blk[0],2)] ^ pkey.mk_tab[3][byte(blk[0],3)] );
        
        blk[2] = rotr32(blk[2] ^ ((t0 + t1 + pkey.l_key[4 * (i) + 8]) % 0x100000000), 1);
        blk[3] = rotl32(blk[3], 1) ^ ((t0 + 2 * t1 + pkey.l_key[4 * (i) + 9]) % 0x100000000);

        t1 = ( pkey.mk_tab[0][byte(blk[3],3)] ^ pkey.mk_tab[1][byte(blk[3],0)] ^ pkey.mk_tab[2][byte(blk[3],1)] ^ pkey.mk_tab[3][byte(blk[3],2)] ); 
        t0 = ( pkey.mk_tab[0][byte(blk[2],0)] ^ pkey.mk_tab[1][byte(blk[2],1)] ^ pkey.mk_tab[2][byte(blk[2],2)] ^ pkey.mk_tab[3][byte(blk[2],3)] );
        
        blk[0] = rotr32(blk[0] ^ ((t0 + t1 + pkey.l_key[4 * (i) + 10]) % 0x100000000), 1);
        blk[1] = rotl32(blk[1], 1) ^ ((t0 + 2 * t1 + pkey.l_key[4 * (i) + 11]) % 0x100000000);         

    if WORD_BIGENDIAN:
        in_blk[0] = byteswap32(blk[2] ^ pkey.l_key[4]);
        in_blk[1] = byteswap32(blk[3] ^ pkey.l_key[5]);
        in_blk[2] = byteswap32(blk[0] ^ pkey.l_key[6]);
        in_blk[3] = byteswap32(blk[1] ^ pkey.l_key[7]);
    else:
        in_blk[0] = blk[2] ^ pkey.l_key[4];
        in_blk[1] = blk[3] ^ pkey.l_key[5];
        in_blk[2] = blk[0] ^ pkey.l_key[6];
        in_blk[3] = blk[1] ^ pkey.l_key[7];
        
    return

def decrypt(pkey, in_blk):
    blk = [0, 0, 0, 0]
    
    if WORD_BIGENDIAN:
        blk[0] = byteswap32(in_blk[0]) ^ pkey.l_key[4];
        blk[1] = byteswap32(in_blk[1]) ^ pkey.l_key[5];
        blk[2] = byteswap32(in_blk[2]) ^ pkey.l_key[6];
        blk[3] = byteswap32(in_blk[3]) ^ pkey.l_key[7];
    else:
        blk[0] = in_blk[0] ^ pkey.l_key[4];
        blk[1] = in_blk[1] ^ pkey.l_key[5];
        blk[2] = in_blk[2] ^ pkey.l_key[6];
        blk[3] = in_blk[3] ^ pkey.l_key[7];    

    for i in xrange(7, -1, -1):
        t1 = ( pkey.mk_tab[0][byte(blk[1],3)] ^ pkey.mk_tab[1][byte(blk[1],0)] ^ pkey.mk_tab[2][byte(blk[1],1)] ^ pkey.mk_tab[3][byte(blk[1],2)] )
        t0 = ( pkey.mk_tab[0][byte(blk[0],0)] ^ pkey.mk_tab[1][byte(blk[0],1)] ^ pkey.mk_tab[2][byte(blk[0],2)] ^ pkey.mk_tab[3][byte(blk[0],3)] )

        blk[2] = rotl32(blk[2], 1) ^ ((t0 + t1 + pkey.l_key[4 * (i) + 10]) % 0x100000000)
        blk[3] = rotr32(blk[3] ^ ((t0 + 2 * t1 + pkey.l_key[4 * (i) + 11]) % 0x100000000), 1)

        t1 = ( pkey.mk_tab[0][byte(blk[3],3)] ^ pkey.mk_tab[1][byte(blk[3],0)] ^ pkey.mk_tab[2][byte(blk[3],1)] ^ pkey.mk_tab[3][byte(blk[3],2)] )
        t0 = ( pkey.mk_tab[0][byte(blk[2],0)] ^ pkey.mk_tab[1][byte(blk[2],1)] ^ pkey.mk_tab[2][byte(blk[2],2)] ^ pkey.mk_tab[3][byte(blk[2],3)] )

        blk[0] = rotl32(blk[0], 1) ^ ((t0 + t1 + pkey.l_key[4 * (i) + 8]) % 0x100000000)
        blk[1] = rotr32(blk[1] ^ ((t0 + 2 * t1 + pkey.l_key[4 * (i) + 9]) % 0x100000000), 1)        

    if WORD_BIGENDIAN:
        in_blk[0] = byteswap32(blk[2] ^ pkey.l_key[0]);
        in_blk[1] = byteswap32(blk[3] ^ pkey.l_key[1]);
        in_blk[2] = byteswap32(blk[0] ^ pkey.l_key[2]);
        in_blk[3] = byteswap32(blk[1] ^ pkey.l_key[3]);
    else:
        in_blk[0] = blk[2] ^ pkey.l_key[0];
        in_blk[1] = blk[3] ^ pkey.l_key[1];
        in_blk[2] = blk[0] ^ pkey.l_key[2];
        in_blk[3] = blk[1] ^ pkey.l_key[3];
    return

__testkey = '\xD4\x3B\xB7\x55\x6E\xA3\x2E\x46\xF2\xA2\x82\xB7\xD4\x5B\x4E\x0D\x57\xFF\x73\x9D\x4D\xC9\x2C\x1B\xD7\xFC\x01\x70\x0C\xC8\x21\x6F'
__testdat = '\x90\xAF\xE9\x1B\xB2\x88\x54\x4F\x2C\x32\xDC\x23\x9B\x26\x35\xE6'
assert 'l\xb4V\x1c@\xbf\n\x97\x05\x93\x1c\xb6\xd4\x08\xe7\xfa' == Twofish(__testkey).encrypt(__testdat)
assert __testdat == Twofish(__testkey).decrypt('l\xb4V\x1c@\xbf\n\x97\x05\x93\x1c\xb6\xd4\x08\xe7\xfa')


########NEW FILE########
__FILENAME__ = twofish_cbc
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import twofish
import operator


class TwofishCBC:
    """
    Cipher-block chaining (CBC) Twofish operation mode.
    """
    def __init__(self, key, init_vec=0):
        """
        Set the key to be used for en-/de-cryption and optionally specify an initialization vector (aka seed/salt).
        """
        self.twofish = twofish.Twofish()
        self.twofish.set_key(key)
        self.state = init_vec

    def encrypt(self, plaintext):
        """
        Encrypt the given string using Twofish CBC.
        """
        if len(plaintext) % 16:
            raise RuntimeError("Twofish ciphertext length must be a multiple of 16")
        ciphertext = ""
        while len(plaintext) >= 16:
            block = self.twofish.encrypt(self._xor_block(plaintext[0:16], self.state))
            ciphertext += block
            plaintext = plaintext[16:]
            self.state = block
        return ciphertext

    def decrypt(self, ciphertext):
        """
        Decrypt the given string using Twofish CBC.
        """
        if len(ciphertext) % 16:
            raise RuntimeError("Twofish ciphertext length must be a multiple of 16")
        plaintext = ""
        while len(ciphertext) >= 16:
            block = ciphertext[0:16]
            plaintext += self._xor_block(self.twofish.decrypt(block), self.state)
            ciphertext = ciphertext[16:]
            self.state = block
        return plaintext

    @staticmethod
    def _xor_block(text1, text2):
        """
        Return the bitwise xor of two arbitrary-length blocks of data
        """
        return "".join(
                       map(
                           lambda c1, c2: chr(operator.xor(ord(c1), ord(c2))),
                           text1,
                           text2
                           )
                       )


def test_twofish_cbc():
    __testkey = "Now Testing Crypto-Functions...."
    __testivc = "Initialization V"
    __testenc = "Passing nonsense through crypt-API, will then do assertion check"
    __testdec = "\x38\xd1\xe3\xb1\xe6\x0d\x41\xa7\xe7\xba\xf1\xeb\x34\x4b\xc3\xdb\x88\x38\xf5\x47\x41\x15\x3f\x26\xa4\x2d\x53\xd8\xd2\x80\x25\x0a\xf3\xe4\xbe\xe4\xba\xe1\xeb\x18\x18\x66\x8a\xa6\xe2\xd0\x2b\x6e\x62\x36\x91\xf7\x72\x28\x5e\xc6\x40\x89\x70\x91\x2c\x35\x71\x39"
    assert TwofishCBC(__testkey, __testivc).decrypt(__testenc) == __testdec
    assert TwofishCBC(__testkey, __testivc).encrypt(__testdec) == __testenc


test_twofish_cbc()


########NEW FILE########
__FILENAME__ = twofish_ecb
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import twofish


class TwofishECB:
    """
    Electronic codebook (ECB) Twofish operation mode.
    """
    def __init__(self, key):
        """
        Set the key to be used for en-/de-cryption.
        """
        self.twofish = twofish.Twofish()
        self.twofish.set_key(key)

    def encrypt(self, plaintext):
        """
        Encrypt the given string using Twofish ECB.
        """
        if len(plaintext) % 16:
            raise RuntimeError("Twofish plaintext length must be a multiple of 16")
        ciphertext = ""
        while len(plaintext) >= 16:
            ciphertext += self.twofish.encrypt(plaintext[0:16])
            plaintext = plaintext[16:]
        return ciphertext

    def decrypt(self, ciphertext):
        """
        Decrypt the given string using Twofish ECB.
        """
        if len(ciphertext) % 16:
            raise RuntimeError("Twofish ciphertext length must be a multiple of 16")
        plaintext = ""
        while len(ciphertext) >= 16:
            plaintext += self.twofish.decrypt(ciphertext[0:16])
            ciphertext = ciphertext[16:]
        return plaintext


def test_twofish_ecb():
    __testkey = "Now Testing Crypto-Functions...."
    __testenc = "Passing nonsense through crypt-API, will then do assertion check"
    __testdec = "\x71\xbf\x8a\xc5\x8f\x6c\x2d\xce\x9d\xdb\x85\x82\x5b\x25\xe3\x8d\xd8\x59\x86\x34\x28\x7b\x58\x06\xca\x42\x3d\xab\xb7\xee\x56\x6f\xd3\x90\xd6\x96\xd5\x94\x8c\x70\x38\x05\xf8\xdf\x92\xa4\x06\x2f\x32\x7f\xbd\xd7\x05\x41\x32\xaa\x60\xfd\x18\xf4\x42\x15\x15\x56"
    assert TwofishECB(__testkey).decrypt(__testenc) == __testdec
    assert TwofishECB(__testkey).encrypt(__testdec) == __testenc


test_twofish_ecb()


########NEW FILE########
__FILENAME__ = vault
#
# Loxodo -- Password Safe V3 compatible Password Vault
# Copyright (C) 2008 Christoph Sommer <mail@christoph-sommer.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import hashlib
import struct
from hmac import HMAC
import random
import os
import tempfile
import time
import uuid

from .twofish.twofish_ecb import TwofishECB
from .twofish.twofish_cbc import TwofishCBC

class Vault(object):
    """
    Represents a collection of password Records in PasswordSafe V3 format.

    The on-disk represenation of the Vault is described in the following file:
    http://passwordsafe.svn.sourceforge.net/viewvc/passwordsafe/trunk/pwsafe/pwsafe/docs/formatV3.txt?revision=2139
    """
    def __init__(self, password, filename=None):
        self.f_tag = None
        self.f_salt = None
        self.f_iter = None
        self.f_sha_ps = None
        self.f_b1 = None
        self.f_b2 = None
        self.f_b3 = None
        self.f_b4 = None
        self.f_iv = None
        self.f_hmac = None
        self.header = self.Header()
        self.records = []
        if not filename:
            self._create_empty(password)
        else:
            self._read_from_file(filename, password)

    class BadPasswordError(RuntimeError):
        pass

    class VaultFormatError(RuntimeError):
        pass

    class VaultVersionError(VaultFormatError):
        pass

    class Field(object):
        """
        Contains the raw, on-disk representation of a record's field.
        """
        def __init__(self, raw_type, raw_len, raw_value):
            self.raw_type = raw_type
            self.raw_len = raw_len
            self.raw_value = raw_value

        def is_equal(self, field):
            """
            Return True if this Field and the given one are of the same type and both contain the same value.
            """
            return self.raw_type == field.raw_type and self.raw_value == field.raw_value

    class Header(object):
        """
        Contains the fields of a Vault header.
        """
        def __init__(self):
            self.raw_fields = {}

        def add_raw_field(self, raw_field):
            self.raw_fields[raw_field.raw_type] = raw_field

    class Record(object):
        """
        Contains the fields of an individual password record.
        """
        def __init__(self):
            self.raw_fields = {}
            self._uuid = None
            self._group = ""
            self._title = ""
            self._user = ""
            self._notes = ""
            self._passwd = ""
            self._last_mod = 0
            self._url = ""

        @staticmethod
        def create():
            record = Vault.Record()
            record.uuid = uuid.uuid4()
            record.last_mod = int(time.time())
            return record

        def add_raw_field(self, raw_field):
            self.raw_fields[raw_field.raw_type] = raw_field
            if (raw_field.raw_type == 0x01):
                self._uuid = uuid.UUID(bytes_le=raw_field.raw_value)
            if (raw_field.raw_type == 0x02):
                self._group = raw_field.raw_value.decode('utf_8', 'replace')
            if (raw_field.raw_type == 0x03):
                self._title = raw_field.raw_value.decode('utf_8', 'replace')
            if (raw_field.raw_type == 0x04):
                self._user = raw_field.raw_value.decode('utf_8', 'replace')
            if (raw_field.raw_type == 0x05):
                self._notes = raw_field.raw_value.decode('utf_8', 'replace')
            if (raw_field.raw_type == 0x06):
                self._passwd = raw_field.raw_value.decode('utf_8', 'replace')
            if ((raw_field.raw_type == 0x0c) and (raw_field.raw_len == 4)):
                self._last_mod = struct.unpack("<L", raw_field.raw_value)[0]
            if (raw_field.raw_type == 0x0d):
                self._url = raw_field.raw_value.decode('utf_8', 'replace')

        def mark_modified(self):
            self.last_mod = int(time.time())

        # TODO: refactor Record._set_xyz methods to be less repetitive

        def _get_uuid(self):
            return self._uuid

        def _set_uuid(self, value):
            self._uuid = value
            raw_id = 0x01
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, 0, "")
            self.raw_fields[raw_id].raw_value = value.bytes_le
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def _get_group(self):
            return self._group

        def _set_group(self, value):
            self._group = value
            raw_id = 0x02
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, len(value), value)
            self.raw_fields[raw_id].raw_value = value.encode('utf_8', 'replace')
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def _get_title(self):
            return self._title

        def _set_title(self, value):
            self._title = value
            raw_id = 0x03
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, len(value), value)
            self.raw_fields[raw_id].raw_value = value.encode('utf_8', 'replace')
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def _get_user(self):
            return self._user

        def _set_user(self, value):
            self._user = value
            raw_id = 0x04
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, len(value), value)
            self.raw_fields[raw_id].raw_value = value.encode('utf_8', 'replace')
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def _get_notes(self):
            return self._notes

        def _set_notes(self, value):
            self._notes = value
            raw_id = 0x05
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, len(value), value)
            self.raw_fields[raw_id].raw_value = value.encode('utf_8', 'replace')
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def _get_passwd(self):
            return self._passwd

        def _set_passwd(self, value):
            self._passwd = value
            raw_id = 0x06
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, len(value), value)
            self.raw_fields[raw_id].raw_value = value.encode('utf_8', 'replace')
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def _get_last_mod(self):
            return self._last_mod

        def _set_last_mod(self, value):
            assert type(value) == int
            self._last_mod = value
            raw_id = 0x0c
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, 0, "0")
            self.raw_fields[raw_id].raw_value = struct.pack("<L", value)
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)

        def _get_url(self):
            return self._url

        def _set_url(self, value):
            self._url = value
            raw_id = 0x0d
            if (raw_id not in self.raw_fields):
                self.raw_fields[raw_id] = Vault.Field(raw_id, len(value), value)
            self.raw_fields[raw_id].raw_value = value.encode('utf_8', 'replace')
            self.raw_fields[raw_id].raw_len = len(self.raw_fields[raw_id].raw_value)
            self.mark_modified()

        def is_corresponding(self, record):
            """
            Return True if Records are the same, based on either UUIDs (if available) or title
            """
            if not self.uuid or not record.uuid:
                return self.title == record.title
            return self.uuid == record.uuid

        def is_newer_than(self, record):
            """
            Return True if this Record's last modifed date is later than the given one's.
            """
            return self.last_mod > record.last_mod

        def merge(self, record):
            """
            Merge in fields from another Record, replacing existing ones
            """
            self.raw_fields = {}
            for field in record.raw_fields.values():
                self.add_raw_field(field)


        uuid = property(_get_uuid, _set_uuid)
        group = property(_get_group, _set_group)
        title = property(_get_title, _set_title)
        user = property(_get_user, _set_user)
        notes = property(_get_notes, _set_notes)
        passwd = property(_get_passwd, _set_passwd)
        last_mod = property(_get_last_mod, _set_last_mod)
        url = property(_get_url, _set_url)

        def __cmp__(self, other):
            """
            Compare Based on Group, then by Title
            """
            return cmp(self._group+self._title, other._group+other._title)

    @staticmethod
    def _stretch_password(password, salt, iterations):
        """
        Generate the SHA-256 value of a password after several rounds of stretching.

        The algorithm is described in the following paper:
        [KEYSTRETCH Section 4.1] http://www.schneier.com/paper-low-entropy.pdf
        """
        sha = hashlib.sha256()
        sha.update(password)
        sha.update(salt)
        stretched_password = sha.digest()
        for dummy in range(iterations):
            stretched_password = hashlib.sha256(stretched_password).digest()
        return stretched_password

    def _read_field_tlv(self, filehandle, cipher):
        """
        Return one field of a vault record by reading from the given file handle.
        """
        data = filehandle.read(16)
        if (not data) or (len(data) < 16):
            raise self.VaultFormatError("EOF encountered when parsing record field")
        if data == "PWS3-EOFPWS3-EOF":
            return None
        data = cipher.decrypt(data)
        raw_len = struct.unpack("<L", data[0:4])[0]
        raw_type = struct.unpack("<B", data[4])[0]
        raw_value = data[5:]
        if (raw_len > 11):
            for dummy in range((raw_len+4)//16):
                data = filehandle.read(16)
                if (not data) or (len(data) < 16):
                    raise self.VaultFormatError("EOF encountered when parsing record field")
                raw_value += cipher.decrypt(data)
        raw_value = raw_value[:raw_len]
        return self.Field(raw_type, raw_len, raw_value)

    @staticmethod
    def _urandom(count):
        try:
            return os.urandom(count)
        except NotImplementedError:
            retval = ""
            for dummy in range(count):
                retval += struct.pack("<B", random.randint(0, 0xFF))
            return retval

    def _write_field_tlv(self, filehandle, cipher, field):
        """
        Write one field of a vault record using the given file handle.
        """
        if (field is None):
            filehandle.write("PWS3-EOFPWS3-EOF")
            return

        assert len(field.raw_value) == field.raw_len

        raw_len = struct.pack("<L", field.raw_len)
        raw_type = struct.pack("<B", field.raw_type)
        raw_value = field.raw_value

        # Assemble TLV block and pad to 16-byte boundary
        data = raw_len + raw_type + raw_value
        if (len(data) % 16 != 0):
            pad_count = 16 - (len(data) % 16)
            data += self._urandom(pad_count)

        data = cipher.encrypt(data)

        filehandle.write(data)

    @staticmethod
    def create(password, filename):
        vault = Vault(password)
        vault.write_to_file(filename, password)

    def _create_empty(self, password):

        assert type(password) != unicode

        self.f_tag = 'PWS3'
        self.f_salt = Vault._urandom(32)
        self.f_iter = 2048
        stretched_password = self._stretch_password(password, self.f_salt, self.f_iter)
        self.f_sha_ps = hashlib.sha256(stretched_password).digest()

        cipher = TwofishECB(stretched_password)
        self.f_b1 = cipher.encrypt(Vault._urandom(16))
        self.f_b2 = cipher.encrypt(Vault._urandom(16))
        self.f_b3 = cipher.encrypt(Vault._urandom(16))
        self.f_b4 = cipher.encrypt(Vault._urandom(16))
        key_k = cipher.decrypt(self.f_b1) + cipher.decrypt(self.f_b2)
        key_l = cipher.decrypt(self.f_b3) + cipher.decrypt(self.f_b4)

        self.f_iv = Vault._urandom(16)

        hmac_checker = HMAC(key_l, "", hashlib.sha256)
        cipher = TwofishCBC(key_k, self.f_iv)

        # No records yet

        self.f_hmac = hmac_checker.digest()

    def _read_from_file(self, filename, password):
        """
        Initialize all class members by loading the contents of a Vault stored in the given file.
        """
        assert type(password) != unicode

        filehandle = file(filename, 'rb')

        # read boilerplate

        self.f_tag = filehandle.read(4)  # TAG: magic tag
        if (self.f_tag != 'PWS3'):
            raise self.VaultVersionError("Not a PasswordSafe V3 file")

        self.f_salt = filehandle.read(32)  # SALT: SHA-256 salt
        self.f_iter = struct.unpack("<L", filehandle.read(4))[0]  # ITER: SHA-256 keystretch iterations
        stretched_password = self._stretch_password(password, self.f_salt, self.f_iter)  # P': the stretched key
        my_sha_ps = hashlib.sha256(stretched_password).digest()

        self.f_sha_ps = filehandle.read(32) # H(P'): SHA-256 hash of stretched passphrase
        if (self.f_sha_ps != my_sha_ps):
            raise self.BadPasswordError("Wrong password")

        self.f_b1 = filehandle.read(16)  # B1
        self.f_b2 = filehandle.read(16)  # B2
        self.f_b3 = filehandle.read(16)  # B3
        self.f_b4 = filehandle.read(16)  # B4

        cipher = TwofishECB(stretched_password)
        key_k = cipher.decrypt(self.f_b1) + cipher.decrypt(self.f_b2)
        key_l = cipher.decrypt(self.f_b3) + cipher.decrypt(self.f_b4)

        self.f_iv = filehandle.read(16)  # IV: initialization vector of Twofish CBC

        hmac_checker = HMAC(key_l, "", hashlib.sha256)
        cipher = TwofishCBC(key_k, self.f_iv)

        # read header

        while (True):
            field = self._read_field_tlv(filehandle, cipher)
            if not field:
                break
            if field.raw_type == 0xff:
                break
            self.header.add_raw_field(field)
            hmac_checker.update(field.raw_value)

        # read fields

        current_record = self.Record()
        while (True):
            field = self._read_field_tlv(filehandle, cipher)
            if not field:
                break
            if field.raw_type == 0xff:
                self.records.append(current_record)
                current_record = self.Record()
            else:
                hmac_checker.update(field.raw_value)
                current_record.add_raw_field(field)

        # read HMAC

        self.f_hmac = filehandle.read(32)  # HMAC: used to verify Vault's integrity

        my_hmac = hmac_checker.digest()
        if (self.f_hmac != my_hmac):
            raise self.VaultFormatError("File integrity check failed")

        self.records.sort()
        filehandle.close()

    def write_to_file(self, filename, password):
        """
        Store contents of this Vault into a file.
        """
        assert type(password) != unicode

        _last_save = struct.pack("<L", int(time.time()))
        self.header.raw_fields[0x04] = self.Field(0x04, len(_last_save), _last_save)
        _what_saved = "Loxodo 0.0-git".encode("utf_8", "replace")
        self.header.raw_fields[0x06] = self.Field(0x06, len(_what_saved), _what_saved)

        # write to temporary file first
        (osfilehandle, tmpfilename) = tempfile.mkstemp('.part', os.path.basename(filename) + ".", os.path.dirname(filename), text=False)
        filehandle = os.fdopen(osfilehandle, "wb")

        # FIXME: choose new SALT, B1-B4, IV values on each file write? Conflicting Specs!

        # write boilerplate

        filehandle.write(self.f_tag)
        filehandle.write(self.f_salt)
        filehandle.write(struct.pack("<L", self.f_iter))

        stretched_password = self._stretch_password(password, self.f_salt, self.f_iter)
        self.f_sha_ps = hashlib.sha256(stretched_password).digest()
        filehandle.write(self.f_sha_ps)

        filehandle.write(self.f_b1)
        filehandle.write(self.f_b2)
        filehandle.write(self.f_b3)
        filehandle.write(self.f_b4)

        cipher = TwofishECB(stretched_password)
        key_k = cipher.decrypt(self.f_b1) + cipher.decrypt(self.f_b2)
        key_l = cipher.decrypt(self.f_b3) + cipher.decrypt(self.f_b4)

        filehandle.write(self.f_iv)

        hmac_checker = HMAC(key_l, "", hashlib.sha256)
        cipher = TwofishCBC(key_k, self.f_iv)

        end_of_record = self.Field(0xff, 0, "")

        for field in self.header.raw_fields.values():
            self._write_field_tlv(filehandle, cipher, field)
            hmac_checker.update(field.raw_value)
        self._write_field_tlv(filehandle, cipher, end_of_record)
        hmac_checker.update(end_of_record.raw_value)

        for record in self.records:
            for field in record.raw_fields.values():
                self._write_field_tlv(filehandle, cipher, field)
                hmac_checker.update(field.raw_value)
            self._write_field_tlv(filehandle, cipher, end_of_record)
            hmac_checker.update(end_of_record.raw_value)

        self._write_field_tlv(filehandle, cipher, None)

        self.f_hmac = hmac_checker.digest()
        filehandle.write(self.f_hmac)
        filehandle.close()

        try:
            tmpvault = Vault(password, filename=tmpfilename)
        except RuntimeError:
            os.remove(tmpfilename)
            raise self.VaultFormatError("File integrity check failed")

        # after writing the temporary file, replace the original file with it
        try:
            os.remove(filename)
        except OSError:
            pass
        os.rename(tmpfilename, filename)


########NEW FILE########
