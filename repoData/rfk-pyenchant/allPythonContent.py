__FILENAME__ = CmdLineChecker
# pyenchant
#
# Copyright (C) 2004-2008, Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

    enchant.checker.CmdLineChecker:  Command-Line spell checker
    
    This module provides the class CmdLineChecker, which interactively
    spellchecks a piece of text by interacting with the user on the
    command line.  It can also be run as a script to spellcheck a file.

"""

import sys

from enchant.checker import SpellChecker
from enchant.utils import printf

class CmdLineChecker:
    """A simple command-line spell checker.
    
    This class implements a simple command-line spell checker.  It must
    be given a SpellChecker instance to operate on, and interacts with
    the user by printing instructions on stdout and reading commands from
    stdin.
    """
    _DOC_ERRORS = ["stdout","stdin"]

    def __init__(self):
        self._stop = False
        self._checker = None
        
    def set_checker(self,chkr):
        self._checker = chkr
    
    def get_checker(self,chkr):
        return self._checker
        
    def run(self):
        """Run the spellchecking loop."""
        self._stop = False
        for err in self._checker:
            self.error = err
            printf(["ERROR:", err.word.encode('utf8')])
            printf(["HOW ABOUT:", err.suggest()])
            status = self.read_command()
            while not status and not self._stop:
                status = self.read_command()
            if self._stop:
                break
        printf(["DONE"])
    
    def print_help(self):
        printf(["0..N:    replace with the numbered suggestion"])
        printf(["R0..rN:  always replace with the numbered suggestion"])
        printf(["i:       ignore this word"])
        printf(["I:       always ignore this word"])
        printf(["a:       add word to personal dictionary"])
        printf(["e:       edit the word"])
        printf(["q:       quit checking"])
        printf(["h:       print this help message"])
        printf(["----------------------------------------------------"])
        printf(["HOW ABOUT:", self.error.suggest()])
    
    def read_command(self):
        try:
            cmd = raw_input(">> ") # Python 2.x
        except NameError:
            cmd = input(">> ") # Python 3.x
        cmd = cmd.strip()
        
        if cmd.isdigit():
            repl = int(cmd)
            suggs = self.error.suggest()
            if repl >= len(suggs):
                printf(["No suggestion number", repl])
                return False
            printf(["Replacing '%s' with '%s'" % (self.error.word,suggs[repl])])
            self.error.replace(suggs[repl])
            return True
        
        if cmd[0] == "R":
            if not cmd[1:].isdigit():
                printf(["Badly formatted command (try 'help')"])
                return False
            repl = int(cmd[1:])
            suggs = self.error.suggest()
            if repl >= len(suggs):
                printf(["No suggestion number", repl])
                return False
            self.error.replace_always(suggs[repl])
            return True
        
        if cmd == "i":
            return True
        
        if cmd == "I":
            self.error.ignore_always()
            return True
            
        if cmd == "a":
            self.error.add()
            return True
        
        if cmd == "e":
            repl = raw_input("New Word: ")
            self.error.replace(repl.strip())
            return True
             
        if cmd == "q":
            self._stop = True
            return True
        
        if "help".startswith(cmd.lower()):
            self.print_help()
            return False
        
        printf(["Badly formatted command (try 'help')"])
        return False
        
    def run_on_file(self,infile,outfile=None,enc=None):
        """Run spellchecking on the named file.
        This method can be used to run the spellchecker over the named file.
        If <outfile> is not given, the corrected contents replace the contents
        of <infile>.  If <outfile> is given, the corrected contents will be
        written to that file.  Use "-" to have the contents written to stdout.
        If <enc> is given, it specifies the encoding used to read the
        file's contents into a unicode string.  The output will be written
        in the same encoding.
        """
        inStr = "".join(file(infile,"r").readlines())
        if enc is not None:
            inStr = inStr.decode(enc)
        self._checker.set_text(inStr)
        self.run()
        outStr = self._checker.get_text()
        if enc is not None:
            outStr = outStr.encode(enc)
        if outfile is None:
            outF = file(infile,"w")
        elif outfile == "-":
            outF = sys.stdout
        else:
            outF = file(outfile,"w")
        outF.write(outStr)
        outF.close()
    run_on_file._DOC_ERRORS = ["outfile","infile","outfile","stdout"]
        
def _run_as_script():
    """Run the command-line spellchecker as a script.
    This function allows the spellchecker to be invoked from the command-line
    to check spelling in a file.
    """
    # Check necessary command-line options
    from optparse import OptionParser
    op = OptionParser()
    op.add_option("-o","--output",dest="outfile",metavar="FILE",
                      help="write changes into FILE")
    op.add_option("-l","--lang",dest="lang",metavar="TAG",default="en_US",
                      help="use language idenfified by TAG")
    op.add_option("-e","--encoding",dest="enc",metavar="ENC",
                      help="file is unicode with encoding ENC")
    (opts,args) = op.parse_args()
    # Sanity check
    if len(args) < 1:
        raise ValueError("Must name a file to check")
    if len(args) > 1:
        raise ValueError("Can only check a single file")
    # Create and run the checker
    chkr = SpellChecker(opts.lang)
    cmdln = CmdLineChecker()
    cmdln.set_checker(chkr)
    cmdln.run_on_file(args[0],opts.outfile,opts.enc)
    

    
if __name__ == "__main__":
    _run_as_script()

########NEW FILE########
__FILENAME__ = GtkSpellCheckerDialog
# GtkSpellCheckerDialog for pyenchant
#
# Copyright (C) 2004-2005, Fredrik Corneliusson
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#

import gtk
import gobject

from enchant.utils import printf, unicode

#   columns
COLUMN_SUGGESTION = 0
def create_list_view(col_label,):
    # create list widget
    list_ = gtk.ListStore(str)
    list_view = gtk.TreeView(model=list_)
    
    list_view.set_rules_hint(True)
    list_view.get_selection().set_mode(gtk.SELECTION_SINGLE)
    # Add Colums
    renderer = gtk.CellRendererText()
    renderer.set_data("column", COLUMN_SUGGESTION)
    column = gtk.TreeViewColumn(col_label, renderer,text=COLUMN_SUGGESTION)
    list_view.append_column(column)
    return list_view


class GtkSpellCheckerDialog(gtk.Window):
    def __init__(self, *args,**kwargs):
        gtk.Window.__init__(self,*args,**kwargs)
        self.set_title('Spell check')
        self.set_default_size(350, 200)

        self._checker = None
        self._numContext = 40

        self.errors = None

        # create accel group
        accel_group = gtk.AccelGroup()
        self.add_accel_group(accel_group)

        # list of widgets to disable if there's no spell error left
        self._conditional_widgets = []
        conditional = self._conditional_widgets.append

        # layout
        mainbox = gtk.VBox(spacing=5)
        hbox = gtk.HBox(spacing=5)
        self.add(mainbox)
        mainbox.pack_start(hbox,padding=5)
        
        box1 = gtk.VBox(spacing=5)
        hbox.pack_start(box1,padding=5)
        conditional(box1)

        # unreconized word
        text_view_lable = gtk.Label('Unreconized word')
        text_view_lable.set_justify(gtk.JUSTIFY_LEFT)
        box1.pack_start(text_view_lable,False,False)

        text_view = gtk.TextView()
        text_view.set_wrap_mode(gtk.WRAP_WORD)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        self.error_text = text_view.get_buffer()
        text_buffer = text_view.get_buffer()
        text_buffer.create_tag("fg_black", foreground="black")
        text_buffer.create_tag("fg_red", foreground="red")

        box1.pack_start(text_view)

        # Change to
        change_to_box = gtk.HBox()
        box1.pack_start(change_to_box,False,False)

        change_to_label = gtk.Label('Change to:')
        self.replace_text = gtk.Entry()
        text_view_lable.set_justify(gtk.JUSTIFY_LEFT)
        change_to_box.pack_start(change_to_label,False,False)
        change_to_box.pack_start(self.replace_text)

        # scrolled window
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        box1.pack_start(sw)

        self.suggestion_list_view = create_list_view('Suggestions')
        self.suggestion_list_view.connect("button_press_event", self._onButtonPress)
        self.suggestion_list_view.connect("cursor-changed", self._onSuggestionChanged)
        sw.add(self.suggestion_list_view)

        #---Buttons---#000000#FFFFFF----------------------------------------------------
        button_box = gtk.VButtonBox()
        hbox.pack_start(button_box, False, False)

        # Ignore
        button = gtk.Button("Ignore")
        button.connect("clicked", self._onIgnore)
        button.add_accelerator("activate", accel_group,
                            gtk.keysyms.Return, 0, gtk.ACCEL_VISIBLE)
        button_box.pack_start(button)
        conditional(button)

        # Ignore all
        button = gtk.Button("Ignore All")
        button.connect("clicked", self._onIgnoreAll)
        button_box.pack_start(button)
        conditional(button)

        # Replace
        button = gtk.Button("Replace")
        button.connect("clicked", self._onReplace)
        button_box.pack_start(button)
        conditional(button)

        # Replace all
        button = gtk.Button("Replace All")
        button.connect("clicked", self._onReplaceAll)
        button_box.pack_start(button)
        conditional(button)

        # Recheck button
        button = gtk.Button("_Add")
        button.connect("clicked", self._onAdd)

        button_box.pack_start(button)
        conditional(button)

        # Close button
        button = gtk.Button(stock=gtk.STOCK_CLOSE)
        button.connect("clicked", self._onClose)
        button.add_accelerator("activate", accel_group,
                            gtk.keysyms.Escape, 0, gtk.ACCEL_VISIBLE)
        button_box.pack_end(button)

        # dictionary label
        self._dict_lable = gtk.Label('')
        mainbox.pack_start(self._dict_lable,False,False,padding=5)

        mainbox.show_all()

    def _onIgnore(self,w,*args):
        printf(["ignore"])
        self._advance()

    def _onIgnoreAll(self,w,*args):
        printf(["ignore all"])
        self._checker.ignore_always()
        self._advance()

    def _onReplace(self,*args):
        printf(["Replace"])
        repl = self._getRepl()
        self._checker.replace(repl)
        self._advance()

    def _onReplaceAll(self,*args):
        printf(["Replace all"])
        repl = self._getRepl()
        self._checker.replace_always(repl)
        self._advance()

    def _onAdd(self,*args):
        """Callback for the "add" button."""
        self._checker.add()
        self._advance()

    def _onClose(self,w,*args):
        self.emit('delete_event',gtk.gdk.Event(gtk.gdk.BUTTON_PRESS))
        return True

    def _onButtonPress(self,widget,event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            printf(["Double click!"])
            self._onReplace()
            
    def _onSuggestionChanged(self,widget,*args):
        selection = self.suggestion_list_view.get_selection()
        model, iter = selection.get_selected()
        if iter:
            suggestion = model.get_value(iter, COLUMN_SUGGESTION)
            self.replace_text.set_text(suggestion)

    def _getRepl(self):
        """Get the chosen replacement string."""
        repl = self.replace_text.get_text()
        repl = self._checker.coerce_string(repl)
        return repl

    def _fillSuggestionList(self,suggestions):
        model = self.suggestion_list_view.get_model()
        model.clear()
        for suggestion in suggestions:
            value = unicode("%s"%(suggestion,))
            model.append([value,])

    def setSpellChecker(self,checker):
        assert checker,'checker cant be None'
        self._checker = checker
        self._dict_lable.set_text('Dictionary:%s'%(checker.dict.tag,))

    def getSpellChecker(self,checker):
        return self._checker

    def updateUI(self):
        self._advance()

    def _disableButtons(self):
        for w in self._conditional_widgets:
            w.set_sensitive(False)

    def _enableButtons(self):
        for w in self._conditional_widgets:
            w.set_sensitive(True)
    
    def _advance(self):
        """Advance to the next error.
        This method advances the SpellChecker to the next error, if
        any.  It then displays the error and some surrounding context,
        and well as listing the suggested replacements.
        """
        # Disable interaction if no checker
        if self._checker is None:
            self._disableButtons()
            self.emit('check-done')
            return

        # Advance to next error, disable if not available
        try:
            self._checker.next()
        except StopIteration:
            self._disableButtons()
            self.error_text.set_text("")
            self._fillSuggestionList([])
            self.replace_text.set_text("")
            return
        self._enableButtons()
        
        # Display error context with erroneous word in red
        self.error_text.set_text('')
        iter = self.error_text.get_iter_at_offset(0)
        append = self.error_text.insert_with_tags_by_name
        

        lContext = self._checker.leading_context(self._numContext)
        tContext = self._checker.trailing_context(self._numContext)
        append(iter, lContext, 'fg_black')
        append(iter, self._checker.word, 'fg_red')
        append(iter, tContext, 'fg_black')

        # Display suggestions in the replacements list
        suggs = self._checker.suggest()
        self._fillSuggestionList(suggs)
        if suggs: self.replace_text.set_text(suggs[0])
        else:     self.replace_text.set_text("")


def _test():
    from enchant.checker import SpellChecker
    text = "This is sme text with a fw speling errors in it. Here are a fw more to tst it ut."
    printf(["BEFORE:", text])
    chk_dlg = GtkSpellCheckerDialog()
    chk_dlg.show()
    chk_dlg.connect('delete_event', gtk.main_quit)

    chkr = SpellChecker("en_US",text)

    chk_dlg.setSpellChecker(chkr)
    chk_dlg.updateUI()
    gtk.main()

if __name__ == "__main__":
    _test()


########NEW FILE########
__FILENAME__ = tests
# pyenchant
#
# Copyright (C) 2004-2009, Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

    enchant.checker.tests:  Unittests for enchant SpellChecker class
    
"""

import unittest

import enchant
import enchant.tokenize
from enchant.utils import *
from enchant.errors import *
from enchant.checker import *


class TestChecker(unittest.TestCase):
    """TestCases for checking behaviour of SpellChecker class."""
    
    def test_basic(self):
        """Test a basic run of the SpellChecker class."""
        text = """This is sme text with a few speling erors in it. Its gret
        for checking wheather things are working proprly with the SpellChecker
        class. Not gret for much elss though."""
        chkr = SpellChecker("en_US",text=text)
        for n,err in enumerate(chkr):
            if n == 0:
                # Fix up "sme" -> "some" properly
                self.assertEqual(err.word,"sme")
                self.assertEqual(err.wordpos,8)
                self.assertTrue("some" in err.suggest())
                err.replace("some")
            if n == 1:
                # Ignore "speling"
                self.assertEqual(err.word,"speling")
            if n == 2:
                # Check context around "erors", and replace
                self.assertEqual(err.word,"erors")
                self.assertEqual(err.leading_context(5),"ling ")
                self.assertEqual(err.trailing_context(5)," in i")
                err.replace(raw_unicode("errors"))
            if n == 3:
                # Replace-all on gret as it appears twice
                self.assertEqual(err.word,"gret")
                err.replace_always("great")
            if n == 4:
                # First encounter with "wheather", move offset back
                self.assertEqual(err.word,"wheather")
                err.set_offset(-1*len(err.word))
            if n == 5:
                # Second encounter, fix up "wheather'
                self.assertEqual(err.word,"wheather")
                err.replace("whether")
            if n == 6:
                # Just replace "proprly", but also add an ignore
                # for "SpellChecker"
                self.assertEqual(err.word,"proprly")
                err.replace("properly")
                err.ignore_always("SpellChecker")
            if n == 7:
                # The second "gret" should have been replaced
                # So it's now on "elss"
                self.assertEqual(err.word,"elss")
                err.replace("else")
            if n > 7:
                self.fail("Extraneous spelling errors were found")
        text2 = """This is some text with a few speling errors in it. Its great
        for checking whether things are working properly with the SpellChecker
        class. Not great for much else though."""
        self.assertEqual(chkr.get_text(),text2)

    def test_filters(self):
        """Test SpellChecker with the 'filters' argument."""
        text = """I contain WikiWords that ShouldBe skipped by the filters"""
        chkr = SpellChecker("en_US",text=text,
                            filters=[enchant.tokenize.WikiWordFilter])
        for err in chkr:
            # There are no errors once the WikiWords are skipped
            self.fail("Extraneous spelling errors were found")
        self.assertEqual(chkr.get_text(),text)

    def test_chunkers(self):
        """Test SpellChecker with the 'chunkers' argument."""
        text = """I contain <html a=xjvf>tags</html> that should be skipped"""
        chkr = SpellChecker("en_US",text=text,
                            chunkers=[enchant.tokenize.HTMLChunker])
        for err in chkr:
            # There are no errors when the <html> tag is skipped
            self.fail("Extraneous spelling errors were found")
        self.assertEqual(chkr.get_text(),text)

    def test_chunkers_and_filters(self):
        """Test SpellChecker with the 'chunkers' and 'filters' arguments."""
        text = """I contain <html a=xjvf>tags</html> that should be skipped
                  along with a <a href='http://example.com/">link to
                  http://example.com/</a> that should also be skipped"""
        # There are no errors when things are correctly skipped
        chkr = SpellChecker("en_US",text=text,
                            filters=[enchant.tokenize.URLFilter],
                            chunkers=[enchant.tokenize.HTMLChunker])
        for err in chkr:
            self.fail("Extraneous spelling errors were found")
        self.assertEqual(chkr.get_text(),text)
        # The "html" is an error when not using HTMLChunker
        chkr = SpellChecker("en_US",text=text,
                            filters=[enchant.tokenize.URLFilter])
        for err in chkr:
            self.assertEqual(err.word,"html")
            break
        self.assertEqual(chkr.get_text(),text)
        # The "http" from the URL is an error when not using URLFilter
        chkr = SpellChecker("en_US",text=text,
                            chunkers=[enchant.tokenize.HTMLChunker])
        for err in chkr:
            self.assertEqual(err.word,"http")
            break
        self.assertEqual(chkr.get_text(),text)
        
    def test_unicode(self):
        """Test SpellChecker with a unicode string."""
        text = raw_unicode("""I am a unicode strng with unicode erors.""")
        chkr = SpellChecker("en_US",text)
        for n,err in enumerate(chkr):
            if n == 0:
                self.assertEqual(err.word,raw_unicode("unicode"))
                self.assertEqual(err.wordpos,7)
                chkr.ignore_always()
            if n == 1:
                self.assertEqual(err.word,raw_unicode("strng"))
                chkr.replace_always("string")
                self.assertEqual(chkr._replace_words[raw_unicode("strng")],raw_unicode("string"))
            if n == 2:
                self.assertEqual(err.word,raw_unicode("erors"))
                chkr.replace("erros")
                chkr.set_offset(-6)
            if n == 3:
                self.assertEqual(err.word,raw_unicode("erros"))
                chkr.replace("errors")
        self.assertEqual(n,3)
        self.assertEqual(chkr.get_text(),raw_unicode("I am a unicode string with unicode errors."))

    def test_chararray(self):
        """Test SpellChecker with a character array as input."""
        # Python 3 does not provide 'c' array type
        if str is unicode:
           atype = 'u'
        else:
           atype = 'c'
        text = "I wll be stord in an aray"
        txtarr = array.array(atype,text)
        chkr = SpellChecker("en_US",txtarr)
        for (n,err) in enumerate(chkr):
            if n == 0:
                self.assertEqual(err.word,"wll")
                self.assertEqual(err.word.__class__,str)
            if n == 1:
                self.assertEqual(err.word,"stord")
                txtarr[err.wordpos:err.wordpos+len(err.word)] = array.array(atype,"stored")
                chkr.set_offset(-1*len(err.word))
            if n == 2:
                self.assertEqual(err.word,"aray")
                chkr.replace("array")
        self.assertEqual(n,2)
        if str is unicode:
          self.assertEqual(txtarr.tounicode(),"I wll be stored in an array")
        else:
          self.assertEqual(txtarr.tostring(),"I wll be stored in an array")

    def test_pwl(self):
        """Test checker loop with PWL."""
        from enchant import DictWithPWL
        d = DictWithPWL("en_US",None,None)
        txt = "I am sme text to be cheked with personal list of cheked words"
        chkr = SpellChecker(d,txt)
        for n,err in enumerate(chkr):
            if n == 0:
                self.assertEqual(err.word,"sme")
            if n == 1:
                self.assertEqual(err.word,"cheked")
                chkr.add()
        self.assertEqual(n,1)

    def test_bug2785373(self):
        """Testcases for bug #2785373."""
        c = SpellChecker(enchant.Dict("en"),"")
        c.set_text("So, one dey when I wes 17, I left.")
        for err in c:
            pass
        c = SpellChecker(enchant.Dict("en"),"")
        c.set_text(raw_unicode("So, one dey when I wes 17, I left."))
        for err in c:
            pass

    def test_default_language(self):
        lang = get_default_language()
        if lang is None:
            self.assertRaises(DefaultLanguageNotFoundError,SpellChecker)
        else:
            checker = SpellChecker()
            self.assertEqual(checker.lang,lang)

    def test_replace_with_shorter_string(self):
        """Testcase for replacing with a shorter string (bug #10)"""
        text = ". I Bezwaar tegen verguning."
        chkr = SpellChecker("en_US",text)
        for i,err in enumerate(chkr):
            err.replace("SPAM")
            assert i < 3
        self.assertEquals(chkr.get_text(),". I SPAM SPAM SPAM.")

    def test_replace_with_empty_string(self):
        """Testcase for replacing with an empty string (bug #10)"""
        text = ". I Bezwaar tegen verguning."
        chkr = SpellChecker("en_US",text)
        for i,err in enumerate(chkr):
            err.replace("")
            assert i < 3
        self.assertEquals(chkr.get_text(),". I   .")


 

########NEW FILE########
__FILENAME__ = wxSpellCheckerDialog
# pyenchant
#
# Copyright (C) 2004-2008, Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
# Major code cleanup and re-write thanks to Phil Mayes, 2007
#
"""

    enchant.checker.wxSpellCheckerDialog: wxPython spellchecker interface
    
    This module provides the class wxSpellCheckerDialog, which provides
    a wxPython dialog that can be used as an interface to a spell checking
    session.  Currently it is intended as a proof-of-concept and demonstration
    class, but it should be suitable for general-purpose use in a program.
    
    The class must be given an enchant.checker.SpellChecker object with
    which to operate.  It can (in theory...) be used in modal and non-modal
    modes.  Use Show() when operating on an array of characters as it will
    modify the array in place, meaning other work can be done at the same
    time.  Use ShowModal() when operating on a static string.

"""
_DOC_ERRORS = ["ShowModal"]

import wx

from enchant.utils import printf

class wxSpellCheckerDialog(wx.Dialog):
    """Simple spellcheck dialog for wxPython
    
    This class implements a simple spellcheck interface for wxPython,
    in the form of a dialog.  It's intended mainly of an example of
    how to do this, although it should be useful for applications that
    just need a simple graphical spellchecker.
    
    To use, a SpellChecker instance must be created and passed to the
    dialog before it is shown:

        >>> dlg = wxSpellCheckerDialog(None,-1,"")
        >>> chkr = SpellChecker("en_AU",text)
        >>> dlg.SetSpellChecker(chkr)
        >>> dlg.Show()
    
    This is most useful when the text to be checked is in the form of
    a character array, as it will be modified in place as the user
    interacts with the dialog.  For checking strings, the final result
    will need to be obtained from the SpellChecker object:
        
        >>> dlg = wxSpellCheckerDialog(None,-1,"")
        >>> chkr = SpellChecker("en_AU",text)
        >>> dlg.SetSpellChecker(chkr)
        >>> dlg.ShowModal()
        >>> text = dlg.GetSpellChecker().get_text()
    
    Currently the checker must deal with strings of the same type as
    returned by wxPython - unicode or normal string depending on the
    underlying system.  This needs to be fixed, somehow...
    """
    _DOC_ERRORS = ["dlg","chkr","dlg","SetSpellChecker","chkr","dlg",
                   "dlg","chkr","dlg","SetSpellChecker","chkr","dlg",
                   "ShowModal","dlg","GetSpellChecker"]
 
    # Remember dialog size across invocations by storing it on the class
    sz = (300,70)

    def __init__(self, parent=None,id=-1,title="Checking Spelling..."):
        wx.Dialog.__init__(self, parent, id, title, size=wxSpellCheckerDialog.sz, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self._numContext = 40
        self._checker = None
        self._buttonsEnabled = True
        self.error_text = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH)
        self.replace_text = wx.TextCtrl(self, -1, "", style=wx.TE_PROCESS_ENTER)
        self.replace_list = wx.ListBox(self, -1, style=wx.LB_SINGLE)
        self.InitLayout()
        wx.EVT_LISTBOX(self,self.replace_list.GetId(),self.OnReplSelect)
        wx.EVT_LISTBOX_DCLICK(self,self.replace_list.GetId(),self.OnReplace)

    def InitLayout(self):
        """Lay out controls and add buttons."""
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        txtSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        replaceSizer = wx.BoxSizer(wx.HORIZONTAL)
        txtSizer.Add(wx.StaticText(self, -1, "Unrecognised Word:"), 0, wx.LEFT|wx.TOP, 5)
        txtSizer.Add(self.error_text, 1, wx.ALL|wx.EXPAND, 5)
        replaceSizer.Add(wx.StaticText(self, -1, "Replace with:"), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        replaceSizer.Add(self.replace_text, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        txtSizer.Add(replaceSizer, 0, wx.EXPAND, 0)
        txtSizer.Add(self.replace_list, 2, wx.ALL|wx.EXPAND, 5)
        sizer.Add(txtSizer, 1, wx.EXPAND, 0)
        self.buttons = []
        for label, action, tip in (\
            ("Ignore", self.OnIgnore, "Ignore this word and continue"),
            ("Ignore All", self.OnIgnoreAll, "Ignore all instances of this word and continue"),
            ("Replace", self.OnReplace, "Replace this word"),
            ("Replace All", self.OnReplaceAll, "Replace all instances of this word"),
            ("Add", self.OnAdd, "Add this word to the dictionary"),
            ("Done", self.OnDone, "Finish spell-checking and accept changes"),
            ):
            btn = wx.Button(self, -1, label)
            btn.SetToolTip(wx.ToolTip(tip))
            btnSizer.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 4)
            btn.Bind(wx.EVT_BUTTON, action)
            self.buttons.append(btn)
        sizer.Add(btnSizer, 0, wx.ALL|wx.EXPAND, 5)
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        sizer.Fit(self)

    def Advance(self):
        """Advance to the next error.

        This method advances the SpellChecker to the next error, if
        any.  It then displays the error and some surrounding context,
        and well as listing the suggested replacements.
        """
        # Disable interaction if no checker
        if self._checker is None:
            self.EnableButtons(False)
            return False
        # Advance to next error, disable if not available
        try:
            self._checker.next()
        except StopIteration:
            self.EnableButtons(False)
            self.error_text.SetValue("")
            self.replace_list.Clear()
            self.replace_text.SetValue("")
            if self.IsModal(): # test needed for SetSpellChecker call
                # auto-exit when checking complete
                self.EndModal(wx.ID_OK)
            return False
        self.EnableButtons()
        # Display error context with erroneous word in red.
        # Restoring default style was misbehaving under win32, so
        # I am forcing the rest of the text to be black.
        self.error_text.SetValue("")
        self.error_text.SetDefaultStyle(wx.TextAttr(wx.BLACK))
        lContext = self._checker.leading_context(self._numContext)
        self.error_text.AppendText(lContext)
        self.error_text.SetDefaultStyle(wx.TextAttr(wx.RED))
        self.error_text.AppendText(self._checker.word)
        self.error_text.SetDefaultStyle(wx.TextAttr(wx.BLACK))
        tContext = self._checker.trailing_context(self._numContext)
        self.error_text.AppendText(tContext)
        # Display suggestions in the replacements list
        suggs = self._checker.suggest()
        self.replace_list.Set(suggs)
        self.replace_text.SetValue(suggs and suggs[0] or '')
        return True

    def EnableButtons(self, state=True):
        """Enable the checking-related buttons"""
        if state != self._buttonsEnabled:
            for btn in self.buttons[:-1]:
                btn.Enable(state)
            self._buttonsEnabled = state

    def GetRepl(self):
        """Get the chosen replacement string."""
        repl = self.replace_text.GetValue()
        return repl

    def OnAdd(self, evt):
        """Callback for the "add" button."""
        self._checker.add()
        self.Advance()

    def OnDone(self, evt):
        """Callback for the "close" button."""
        wxSpellCheckerDialog.sz = self.error_text.GetSizeTuple()
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Close()

    def OnIgnore(self, evt):
        """Callback for the "ignore" button.
        This simply advances to the next error.
        """
        self.Advance()

    def OnIgnoreAll(self, evt):
        """Callback for the "ignore all" button."""
        self._checker.ignore_always()
        self.Advance()

    def OnReplace(self, evt):
        """Callback for the "replace" button."""
        repl = self.GetRepl()
        if repl:
            self._checker.replace(repl)
        self.Advance()

    def OnReplaceAll(self, evt):
        """Callback for the "replace all" button."""
        repl = self.GetRepl()
        self._checker.replace_always(repl)
        self.Advance()

    def OnReplSelect(self, evt):
        """Callback when a new replacement option is selected."""
        sel = self.replace_list.GetSelection()
        if sel == -1:
            return
        opt = self.replace_list.GetString(sel)
        self.replace_text.SetValue(opt)

    def GetSpellChecker(self):
        """Get the spell checker object."""
        return self._checker

    def SetSpellChecker(self,chkr):
        """Set the spell checker, advancing to the first error.
        Return True if error(s) to correct, else False."""
        self._checker = chkr
        return self.Advance()


def _test():
    class TestDialog(wxSpellCheckerDialog):
        def __init__(self,*args):
            wxSpellCheckerDialog.__init__(self,*args)
            wx.EVT_CLOSE(self,self.OnClose)
        def OnClose(self,evnt):
            chkr = dlg.GetSpellChecker()
            if chkr is not None:
                printf(["AFTER:", chkr.get_text()])
            self.Destroy()
    from enchant.checker import SpellChecker
    text = "This is sme text with a fw speling errors in it. Here are a fw more to tst it ut."
    printf(["BEFORE:", text])
    app = wx.PySimpleApp()
    dlg = TestDialog()
    chkr = SpellChecker("en_US",text)
    dlg.SetSpellChecker(chkr)
    dlg.Show()
    app.MainLoop()

if __name__ == "__main__":
    _test()


########NEW FILE########
__FILENAME__ = errors
# pyenchant
#
# Copyright (C) 2004-2008, Ryan Kelly
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPsE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""
enchant.errors:  Error class definitions for the enchant library
================================================================

All error classes are defined in this separate sub-module, so that they
can safely be imported without causing circular dependencies.

"""

class Error(Exception):
    """Base exception class for the enchant module."""
    pass

class DictNotFoundError(Error):
    """Exception raised when a requested dictionary could not be found."""
    pass

class TokenizerNotFoundError(Error):
    """Exception raised when a requested tokenizer could not be found."""
    pass

class DefaultLanguageNotFoundError(Error):
    """Exception raised when a default language could not be found."""
    pass

########NEW FILE########
__FILENAME__ = pypwl
# pyenchant
#
# Copyright (C) 2004-2011 Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

pypwl:  pure-python personal word list in the style of Enchant
==============================================================

This module provides a pure-python version of the personal word list
functionality found in the spellchecking package Enchant.  While the
same effect can be achieved (with better performance) using the python
bindings for Enchant, it requires a C extension.

This pure-python implementation uses the same algorithm but without any
external dependencies or C code (in fact, it was the author's original
prototype for the C version found in Enchant).

"""

from __future__ import generators

import os
import warnings

class Trie:
    """Class implementing a trie-based dictionary of words.

    A Trie is a recursive data structure storing words by their prefix.
    "Fuzzy matching" can be done by allowing a certain number of missteps
    when traversing the Trie.
    """
    
    def __init__(self,words=()):
        self._eos = False    # whether I am the end of a word
        self._keys = {}      # letters at this level of the trie
        for w in words:
            self.insert(w)
    
    def insert(self,word):
        if word == "":
            self._eos = True
        else:
            key = word[0]
            try:
                subtrie = self[key]
            except KeyError:
                subtrie = Trie()
                self[key] = subtrie
            subtrie.insert(word[1:])

    def remove(self,word):
        if word == "":
            self._eos = False
        else:
            key = word[0]
            try:
                subtrie = self[key]
            except KeyError:
                pass
            else:
                subtrie.remove(word[1:])
    
    def search(self,word,nerrs=0):
        """Search for the given word, possibly making errors.
        
        This method searches the trie for the given <word>, making
        precisely <nerrs> errors.  It returns a list of words found.
        """
        res = []
        # Terminate if we've run out of errors
        if nerrs < 0:
            return res
        # Precise match at the end of the word
        if nerrs == 0 and word == "":
            if self._eos:
                res.append("")
        # Precisely match word[0]
        try:
            subtrie = self[word[0]]
            subres = subtrie.search(word[1:],nerrs)
            for w in subres:
                w2 = word[0] + w
                if w2 not in res:
                  res.append(w2)
        except (IndexError, KeyError):
            pass
        # match with deletion of word[0]
        try:
            subres = self.search(word[1:],nerrs-1)
            for w in subres:
                if w not in res:
                    res.append(w)
        except (IndexError,):
            pass
        # match with insertion before word[0]
        try:
            for k in self._keys:
                subres = self[k].search(word,nerrs-1)
                for w in subres:
                    w2 = k+w
                    if w2 not in res:
                        res.append(w2)
        except (IndexError,KeyError):
            pass
        # match on substitution of word[0]
        try:
            for k in self._keys:
                subres = self[k].search(word[1:],nerrs-1)
                for w in subres:
                    w2 = k+w
                    if w2 not in res:
                        res.append(w2)
        except (IndexError,KeyError):
            pass
        # All done!
        return res
    search._DOC_ERRORS = ["nerrs"]
        
    def __getitem__(self,key):
        return self._keys[key]
        
    def __setitem__(self,key,val):
        self._keys[key] = val

    def __iter__(self):
        if self._eos:
            yield ""
        for k in self._keys:
            for w2 in self._keys[k]:
                yield k + w2


class PyPWL:
    """Pure-python implementation of Personal Word List dictionary.
    This class emulates the PWL objects provided by PyEnchant, but
    implemented purely in python.
    """
    
    def __init__(self,pwl=None):
        """PyPWL constructor.
        This method takes as its only argument the name of a file
        containing the personal word list, one word per line.  Entries
        will be read from this file, and new entries will be written to
        it automatically.

        If <pwl> is not specified or None, the list is maintained in
        memory only.
        """
        self.provider = None
        self._words = Trie()
        if pwl is not None:
            self.pwl = os.path.abspath(pwl)
            self.tag = self.pwl
            pwlF = file(pwl)
            for ln in pwlF:
                word = ln.strip()
                self.add_to_session(word)
            pwlF.close()
        else:
            self.pwl = None
            self.tag = "PyPWL"
                
    def check(self,word):
        """Check spelling of a word.
        
        This method takes a word in the dictionary language and returns
        True if it is correctly spelled, and false otherwise.
        """
        res = self._words.search(word)
        return bool(res)
    
    def suggest(self,word):
        """Suggest possible spellings for a word.
        
        This method tries to guess the correct spelling for a given
        word, returning the possibilities in a list.
        """
        limit = 10
        maxdepth = 5
        # Iterative deepening until we get enough matches
        depth = 0
        res = self._words.search(word,depth)
        while len(res) < limit and depth < maxdepth:
            depth += 1
            for w in self._words.search(word,depth):
                if w not in res:
                    res.append(w)
        # Limit number of suggs
        return res[:limit]
    
    def add(self,word):
        """Add a word to the user's personal dictionary.
        For a PWL, this means appending it to the file.
        """
        if self.pwl is not None:
            pwlF = file(self.pwl,"a")
            pwlF.write("%s\n" % (word.strip(),))
            pwlF.close()
        self.add_to_session(word)

    def add_to_pwl(self,word):
        """Add a word to the user's personal dictionary.
        For a PWL, this means appending it to the file.
        """
        warnings.warn("PyPWL.add_to_pwl is deprecated, please use PyPWL.add",
                      category=DeprecationWarning,stacklevel=2)
        self.add(word)

    def remove(self,word):
        """Add a word to the user's personal exclude list."""
        # There's no exclude list for a stand-alone PWL.
        # Just remove it from the list.
        self._words.remove(word)
        if self.pwl is not None:
            pwlF = file(self.pwl,"wt")
            for w in self._words:
                pwlF.write("%s\n" % (w.strip(),))
            pwlF.close()

    def add_to_session(self,word):
        """Add a word to the session list."""
        self._words.insert(word)
                    
    def is_in_session(self,word):
        """Check whether a word is in the session list."""
        warnings.warn("PyPWL.is_in_session is deprecated, please use PyPWL.is_added",category=DeprecationWarning)
        # Consider all words to be in the session list
        return self.check(word)
    
    def store_replacement(self,mis,cor):
        """Store a replacement spelling for a miss-spelled word.
        
        This method makes a suggestion to the spellchecking engine that the 
        miss-spelled word <mis> is in fact correctly spelled as <cor>.  Such
        a suggestion will typically mean that <cor> appears early in the
        list of suggested spellings offered for later instances of <mis>.
        """
        # Too much work for this simple spellchecker
        pass
    store_replacement._DOC_ERRORS = ["mis","mis"]

    def is_added(self,word):
        """Check whether a word is in the personal word list."""
        return self.check(word)

    def is_removed(self,word):
        """Check whether a word is in the personal exclude list."""
        return False

    #  No-op methods to support internal use as a Dict() replacement

    def _check_this(self,msg):
        pass

    def _free(self):
        pass



########NEW FILE########
__FILENAME__ = tests
# pyenchant
#
# Copyright (C) 2004-2009, Ryan Kelly
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPsE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

    enchant.tests:  testcases for pyenchant

"""

import os
import sys
import unittest
import pickle
try:
    import subprocess
except ImportError:
    subprocess = None

import enchant
from enchant import *
from enchant import _enchant as _e
from enchant.utils import unicode, raw_unicode, printf, trim_suggestions


def runcmd(cmd):
    if subprocess is not None:
        kwds = dict(stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        p = subprocess.Popen(cmd,**kwds)
        (stdout,stderr) = p.communicate()
        if p.returncode:
            if sys.version_info[0] >= 3:
                stderr = stderr.decode(sys.getdefaultencoding(),"replace")
            sys.stderr.write(stderr)
        return p.returncode
    else:
        return os.system(cmd)


class TestBroker(unittest.TestCase):
    """Test cases for the proper functioning of Broker objects.

    These tests assume that there is at least one working provider
    with a dictionary for the "en_US" language.
    """
    
    def setUp(self):
        self.broker = Broker()
    
    def tearDown(self):
        del self.broker

    def test_HasENUS(self):
        """Test that the en_US language is available."""
        self.assertTrue(self.broker.dict_exists("en_US"))
    
    def test_LangsAreAvail(self):
        """Test whether all advertised languages are in fact available."""
        for lang in self.broker.list_languages():
            if not self.broker.dict_exists(lang):
                assert False, "language '"+lang+"' advertised but non-existent"
            
    def test_ProvsAreAvail(self):
        """Test whether all advertised providers are in fact available."""
        for (lang,prov) in self.broker.list_dicts():
            self.assertTrue(self.broker.dict_exists(lang))
            if not self.broker.dict_exists(lang):
                assert False, "language '"+lang+"' advertised but non-existent"
            if prov not in self.broker.describe():
                assert False, "provier '"+str(prov)+"' advertised but non-existent"
    
    def test_ProvOrdering(self):
        """Test that provider ordering works correctly."""
        langs = {}
        provs = []
        # Find the providers for each language, and a list of all providers
        for (tag,prov) in self.broker.list_dicts():
            # Skip hyphenation dictionaries installed by OOo
            if tag.startswith("hyph_") and prov.name == "myspell":
                continue
            # Canonicalize separators
            tag = tag.replace("-","_")
            langs[tag] = []
            # NOTE: we are excluding Zemberek here as it appears to return
            #       a broker for any language, even nonexistent ones
            if prov not in provs and prov.name != "zemberek":
                provs.append(prov)
        for prov in provs:
            for tag in langs:
                b2 = Broker()
                b2.set_ordering(tag,prov.name)
                try:
                  d = b2.request_dict(tag)
                  if d.provider != prov:
                    raise ValueError()
                  langs[tag].append(prov)
                except:
                  pass
        # Check availability using a single entry in ordering
        for tag in langs:
            for prov in langs[tag]:
                b2 = Broker()
                b2.set_ordering(tag,prov.name)
                d = b2.request_dict(tag)
                self.assertEqual((d.provider,tag),(prov,tag))
                del d
                del b2
        # Place providers that dont have the language in the ordering
        for tag in langs:
            for prov in langs[tag]:
                order = prov.name
                for prov2 in provs:
                    if prov2 not in langs[tag]:
                        order = prov2.name + "," + order
                b2 = Broker()
                b2.set_ordering(tag,order)
                d = b2.request_dict(tag)
                self.assertEqual((d.provider,tag,order),(prov,tag,order))
                del d
                del b2

    def test_UnicodeTag(self):
        """Test that unicode language tags are accepted"""
        d1 = self.broker._request_dict_data(raw_unicode("en_US"))
        self.assertTrue(d1)
        _e.broker_free_dict(self.broker._this,d1)
        d1 = Dict(raw_unicode("en_US"))
        self.assertTrue(d1)

    def test_GetSetParam(self):
        try:
            self.broker.get_param("pyenchant.unittest")
        except AttributeError:
            return
        self.assertEqual(self.broker.get_param("pyenchant.unittest"),None)
        self.broker.set_param("pyenchant.unittest","testing")
        self.assertEqual(self.broker.get_param("pyenchant.unittest"),"testing")
        self.assertEqual(Broker().get_param("pyenchant.unittest"),None)


class TestDict(unittest.TestCase):
    """Test cases for the proper functioning of Dict objects.
    These tests assume that there is at least one working provider
    with a dictionary for the "en_US" language.
    """
        
    def setUp(self):
        self.dict = Dict("en_US")
    
    def tearDown(self):
        del self.dict

    def test_HasENUS(self):
        """Test that the en_US language is available through default broker."""
        self.assertTrue(dict_exists("en_US"))
    
    def test_check(self):
        """Test that check() works on some common words."""
        self.assertTrue(self.dict.check("hello"))
        self.assertTrue(self.dict.check("test"))
        self.assertFalse(self.dict.check("helo"))
        self.assertFalse(self.dict.check("testt"))
        
    def test_broker(self):
        """Test that the dict's broker is set correctly."""
        self.assertTrue(self.dict._broker is enchant._broker)
    
    def test_tag(self):
        """Test that the dict's tag is set correctly."""
        self.assertEqual(self.dict.tag,"en_US")
    
    def test_suggest(self):
        """Test that suggest() gets simple suggestions right."""
        self.assertTrue(self.dict.check("hello"))
        self.assertTrue("hello" in self.dict.suggest("helo"))

    def test_suggestHang1(self):
        """Test whether suggest() hangs on some inputs (Bug #1404196)"""
        self.assertTrue(len(self.dict.suggest("Thiis")) >= 0)
        self.assertTrue(len(self.dict.suggest("Thiiis")) >= 0)
        self.assertTrue(len(self.dict.suggest("Thiiiis")) >= 0)

    def test_unicode1(self):
        """Test checking/suggesting for unicode strings"""
        # TODO: find something that actually returns suggestions
        us1 = raw_unicode(r"he\u2149lo")
        self.assertTrue(type(us1) is unicode)
        self.assertFalse(self.dict.check(us1))
        for s in self.dict.suggest(us1):
            self.assertTrue(type(s) is unicode)

    def test_session(self):
        """Test that adding words to the session works as required."""
        self.assertFalse(self.dict.check("Lozz"))
        self.assertFalse(self.dict.is_added("Lozz"))
        self.dict.add_to_session("Lozz")
        self.assertTrue(self.dict.is_added("Lozz"))
        self.assertTrue(self.dict.check("Lozz"))
        self.dict.remove_from_session("Lozz")
        self.assertFalse(self.dict.check("Lozz"))
        self.assertFalse(self.dict.is_added("Lozz"))
        self.dict.remove_from_session("hello")
        self.assertFalse(self.dict.check("hello"))
        self.assertTrue(self.dict.is_removed("hello"))
        self.dict.add_to_session("hello")

    def test_AddRemove(self):
        """Test adding/removing from default user dictionary."""
        nonsense = "kxhjsddsi"
        self.assertFalse(self.dict.check(nonsense))
        self.dict.add(nonsense)
        self.assertTrue(self.dict.is_added(nonsense))
        self.assertTrue(self.dict.check(nonsense))
        self.dict.remove(nonsense)
        self.assertFalse(self.dict.is_added(nonsense))
        self.assertFalse(self.dict.check(nonsense))
        self.dict.remove("pineapple")
        self.assertFalse(self.dict.check("pineapple"))
        self.assertTrue(self.dict.is_removed("pineapple"))
        self.assertFalse(self.dict.is_added("pineapple"))
        self.dict.add("pineapple")
        self.assertTrue(self.dict.check("pineapple"))
    
    def test_DefaultLang(self):
        """Test behaviour of default language selection."""
        defLang = utils.get_default_language()
        if defLang is None:
            # If no default language, shouldnt work
            self.assertRaises(Error,Dict)
        else:
            # If there is a default language, should use it
            # Of course, no need for the dict to actually exist
            try:
                d = Dict()
                self.assertEqual(d.tag,defLang)
            except DictNotFoundError:
                pass

    def test_pickling(self):
        """Test that pickling doensn't corrupt internal state."""
        d1 = Dict("en")
        self.assertTrue(d1.check("hello"))
        d2 = pickle.loads(pickle.dumps(d1))
        self.assertTrue(d1.check("hello"))
        self.assertTrue(d2.check("hello"))
        d1._free()
        self.assertTrue(d2.check("hello"))


class TestPWL(unittest.TestCase):
    """Test cases for the proper functioning of PWLs and DictWithPWL objects.
    These tests assume that there is at least one working provider
    with a dictionary for the "en_US" language.
    """    
    
    def setUp(self):
        self._tempDir = self._mkdtemp()
        self._fileName = "pwl.txt"
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self._tempDir)

    def _mkdtemp(self):
        import tempfile
        return tempfile.mkdtemp()

    def _path(self,nm=None):
        if nm is None:
          nm = self._fileName
        nm = os.path.join(self._tempDir,nm)
        if not os.path.exists(nm):
          open(nm,'w').close()
        return nm

    def setPWLContents(self,contents):
        """Set the contents of the PWL file."""
        pwlFile = open(self._path(),"w")
        for ln in contents:
            pwlFile.write(ln)
            pwlFile.write("\n")
        pwlFile.flush()
        pwlFile.close()
        
    def getPWLContents(self):
        """Retrieve the contents of the PWL file."""
        pwlFile = open(self._path(),"r")
        contents = pwlFile.readlines()
        pwlFile.close()
        return [c.strip() for c in contents]
    
    def test_check(self):
        """Test that basic checking works for PWLs."""
        self.setPWLContents(["Sazz","Lozz"])
        d = request_pwl_dict(self._path())
        self.assertTrue(d.check("Sazz"))
        self.assertTrue(d.check("Lozz"))
        self.assertFalse(d.check("hello"))

    def test_UnicodeFN(self):
        """Test that unicode PWL filenames are accepted."""
        d = request_pwl_dict(unicode(self._path()))
        self.assertTrue(d)

    def test_add(self):
        """Test that adding words to a PWL works correctly."""
        d = request_pwl_dict(self._path())
        self.assertFalse(d.check("Flagen"))
        d.add("Esquilax")
        d.add("Esquilam")
        self.assertTrue(d.check("Esquilax"))
        self.assertTrue("Esquilax" in self.getPWLContents())
        self.assertTrue(d.is_added("Esquilax"))
        
    def test_suggestions(self):
        """Test getting suggestions from a PWL."""
        self.setPWLContents(["Sazz","Lozz"])
        d = request_pwl_dict(self._path())
        self.assertTrue("Sazz" in d.suggest("Saz"))
        self.assertTrue("Lozz" in d.suggest("laz"))
        self.assertTrue("Sazz" in d.suggest("laz"))
        d.add("Flagen")
        self.assertTrue("Flagen" in d.suggest("Flags"))
        self.assertFalse("sazz" in d.suggest("Flags"))
    
    def test_DWPWL(self):
        """Test functionality of DictWithPWL."""
        self.setPWLContents(["Sazz","Lozz"])
        d = DictWithPWL("en_US",self._path(),self._path("pel.txt"))
        self.assertTrue(d.check("Sazz"))
        self.assertTrue(d.check("Lozz"))
        self.assertTrue(d.check("hello"))
        self.assertFalse(d.check("helo"))
        self.assertFalse(d.check("Flagen"))
        d.add("Flagen")
        self.assertTrue(d.check("Flagen"))
        self.assertTrue("Flagen" in self.getPWLContents())
        self.assertTrue("Flagen" in d.suggest("Flagn"))
        self.assertTrue("hello" in d.suggest("helo"))
        d.remove("hello")
        self.assertFalse(d.check("hello"))
        self.assertTrue("hello" not in d.suggest("helo"))
        d.remove("Lozz")
        self.assertFalse(d.check("Lozz"))

    def test_DWPWL_empty(self):
        """Test functionality of DictWithPWL using transient dicts."""
        d = DictWithPWL("en_US",None,None)
        self.assertTrue(d.check("hello"))
        self.assertFalse(d.check("helo"))
        self.assertFalse(d.check("Flagen"))
        d.add("Flagen")
        self.assertTrue(d.check("Flagen"))
        d.remove("hello")
        self.assertFalse(d.check("hello"))
        d.add("hello")
        self.assertTrue(d.check("hello"))

    def test_PyPWL(self):
        """Test our pure-python PWL implementation."""
        d = PyPWL()
        self.assertTrue(list(d._words) == [])
        d.add("hello")
        d.add("there")
        d.add("duck")
        ws = list(d._words)
        self.assertTrue(len(ws) == 3)
        self.assertTrue("hello" in ws)
        self.assertTrue("there" in ws)
        self.assertTrue("duck" in ws)
        d.remove("duck")
        d.remove("notinthere")
        ws = list(d._words)
        self.assertTrue(len(ws) == 2)
        self.assertTrue("hello" in ws)
        self.assertTrue("there" in ws)

    def test_UnicodeCharsInPath(self):
        """Test that unicode chars in PWL paths are accepted."""
        self._fileName = raw_unicode(r"test_\xe5\xe4\xf6_ing")
        d = request_pwl_dict(self._path())
        self.assertTrue(d)


class TestUtils(unittest.TestCase):
    """Test cases for various utility functions."""

    def test_trim_suggestions(self):
        word = "gud"
        suggs = ["good","god","bad+"]
        self.assertEquals(trim_suggestions(word,suggs,40),["god","good","bad+"])
        self.assertEquals(trim_suggestions(word,suggs,4),["god","good","bad+"])
        self.assertEquals(trim_suggestions(word,suggs,3),["god","good","bad+"])
        self.assertEquals(trim_suggestions(word,suggs,2),["god","good"])
        self.assertEquals(trim_suggestions(word,suggs,1),["god"])
        self.assertEquals(trim_suggestions(word,suggs,0),[])


class TestDocStrings(unittest.TestCase):
    """Test the spelling on all docstrings we can find in this module.

    This serves two purposes - to provide a lot of test data for the
    checker routines, and to make sure we don't suffer the embarrassment
    of having spelling errors in a spellchecking package!
    """

    WORDS = ["spellchecking","utf","dict","unicode","bytestring","bytestrings",
             "str","pyenchant","ascii", "utils","setup","distutils","pkg",
             "filename", "tokenization", "tuple", "tuples", "tokenizer",
             "tokenizers","testcase","testcases","whitespace","wxpython",
             "spellchecker","dialog","urls","wikiwords","enchantobject",
             "providerdesc", "spellcheck", "pwl", "aspell", "myspell",
             "docstring", "docstrings", "stopiteration", "pwls","pypwl",
             "dictwithpwl","skippable","dicts","dict's","filenames",
             "trie","api","ctypes","wxspellcheckerdialog","stateful",
             "cmdlinechecker","spellchecks","callback","clunkier","iterator",
             "ispell","cor","backends"]

    def test_docstrings(self):
        """Test that all our docstrings are error-free."""
        import enchant
        import enchant.utils
        import enchant.pypwl
        import enchant.tokenize
        import enchant.tokenize.en
        import enchant.checker
        import enchant.checker.CmdLineChecker
        try:
            import enchant.checker.GtkSpellCheckerDialog
        except ImportError:
            pass
        try:
            import enchant.checker.wxSpellCheckerDialog
        except ImportError:
            pass
        errors = []
        #  Naive recursion here would blow the stack, instead we
        #  simulate it with our own stack
        tocheck = [enchant]
        checked = []
        while tocheck:
            obj = tocheck.pop()
            checked.append(obj)
            newobjs = list(self._check_docstrings(obj,errors))
            tocheck.extend([obj for obj in newobjs if obj not in checked])
        self.assertEqual(len(errors),0)

    def _check_docstrings(self,obj,errors):
        import enchant
        if hasattr(obj,"__doc__"):
            skip_errors = [w for w in getattr(obj,"_DOC_ERRORS",[])]
            chkr = enchant.checker.SpellChecker("en_AU",obj.__doc__,filters=[enchant.tokenize.URLFilter])
            for err in chkr:
                if len(err.word) == 1:
                    continue
                if err.word.lower() in self.WORDS:
                    continue
                if skip_errors and skip_errors[0] == err.word:
                    skip_errors.pop(0)
                    continue
                errors.append((obj,err.word,err.wordpos))
                msg = "\nDOCSTRING SPELLING ERROR: %s %s %d %s\n" % (obj,err.word,err.wordpos,chkr.suggest())
                printf([msg],file=sys.stderr)
        #  Find and yield all child objects that should be checked
        for name in dir(obj):
            if name.startswith("__"):
                continue
            child = getattr(obj,name)
            if hasattr(child,"__file__"):
                if not hasattr(globals(),"__file__"):
                    continue
                if not child.__file__.startswith(os.path.dirname(__file__)):
                    continue
            else:
                cmod = getattr(child,"__module__",None)
                if not cmod:
                    cclass = getattr(child,"__class__",None)
                    cmod = getattr(cclass,"__module__",None)
                if cmod and not cmod.startswith("enchant"):
                    continue
            yield child


class TestInstallEnv(unittest.TestCase):
    """Run all testcases in a variety of install environments."""
   
    def setUp(self):
        self._tempDir = self._mkdtemp()
        self._insDir = "build"
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self._tempDir)

    def _mkdtemp(self):
        import tempfile
        return tempfile.mkdtemp()

    def install(self):
        import os, sys, shutil
        insdir = os.path.join(self._tempDir,self._insDir)
        os.makedirs(insdir)
        shutil.copytree("enchant",os.path.join(insdir,"enchant"))

    def runtests(self):
        import os, sys
        insdir = os.path.join(self._tempDir,self._insDir)
        if str is not unicode and isinstance(insdir,unicode):
            insdir = insdir.encode(sys.getfilesystemencoding())
        os.environ["PYTHONPATH"] = insdir
        script = os.path.join(insdir,"enchant","__init__.py")
        res = runcmd("\"%s\" %s" % (sys.executable,script,))
        self.assertEqual(res,0)

    def test_basic(self):
        """Test proper functioning of TestInstallEnv suite."""
        self.install()
        self.runtests()
    test_basic._DOC_ERRORS = ["TestInstallEnv"]

    def test_UnicodeInstallPath(self):
        """Test installation in a path containing unicode chars."""
        self._insDir = raw_unicode(r'test_\xe5\xe4\xf6_ing')
        self.install()
        self.runtests()


class TestPy2exe(unittest.TestCase):
    """Run all testcases inside a py2exe executable"""
    _DOC_ERRORS = ["py","exe"]
   
    def setUp(self):
        self._tempDir = self._mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self._tempDir)

    def test_py2exe(self):
        """Test pyenchant running inside a py2exe executable."""
        import os, sys, shutil
        from os import path
        from os.path import dirname
        try:
            import py2exe
        except ImportError:
            return
        os.environ["PYTHONPATH"] = dirname(dirname(__file__))
        setup_py = path.join(dirname(__file__),"..","tools","setup.py2exe.py")
        if not path.exists(setup_py):
            return
        buildCmd = '%s %s -q py2exe --dist-dir="%s"'
        buildCmd = buildCmd % (sys.executable,setup_py,self._tempDir)
        res = runcmd(buildCmd)
        self.assertEqual(res,0)
        testCmd = self._tempDir + "\\test_pyenchant.exe"
        self.assertTrue(os.path.exists(testCmd))
        res = runcmd(testCmd)
        self.assertEqual(res,0)
    test_py2exe._DOC_ERRORS = ["py","exe"]
        
    def _mkdtemp(self):
        import tempfile
        return tempfile.mkdtemp()


def buildtestsuite(recurse=True):
    from enchant.checker.tests import TestChecker
    from enchant.tokenize.tests import TestTokenization, TestFilters
    from enchant.tokenize.tests import TestTokenizeEN
    suite = unittest.TestSuite()
    if recurse:
        suite.addTest(unittest.makeSuite(TestInstallEnv))
        suite.addTest(unittest.makeSuite(TestPy2exe))
    suite.addTest(unittest.makeSuite(TestBroker))
    suite.addTest(unittest.makeSuite(TestDict))
    suite.addTest(unittest.makeSuite(TestPWL))
    suite.addTest(unittest.makeSuite(TestUtils))
    suite.addTest(unittest.makeSuite(TestDocStrings))
    suite.addTest(unittest.makeSuite(TestChecker))
    suite.addTest(unittest.makeSuite(TestTokenization))
    suite.addTest(unittest.makeSuite(TestTokenizeEN))
    suite.addTest(unittest.makeSuite(TestFilters))
    return suite


def runtestsuite(recurse=False):
    return unittest.TextTestRunner(verbosity=0).run(buildtestsuite(recurse=recurse))


########NEW FILE########
__FILENAME__ = en
# pyenchant
#
# Copyright (C) 2004-2008, Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

    enchant.tokenize.en:    Tokenizer for the English language
    
    This module implements a PyEnchant text tokenizer for the English
    language, based on very simple rules.

"""

import unicodedata

import enchant.tokenize
from enchant.utils import unicode


class tokenize(enchant.tokenize.tokenize):
    """Iterator splitting text into words, reporting position.
    
    This iterator takes a text string as input, and yields tuples
    representing each distinct word found in the text.  The tuples
    take the form:
        
        (<word>,<pos>)
        
    Where <word> is the word string found and <pos> is the position
    of the start of the word within the text.
    
    The optional argument <valid_chars> may be used to specify a
    list of additional characters that can form part of a word.
    By default, this list contains only the apostrophe ('). Note that
    these characters cannot appear at the start or end of a word.
    """

    _DOC_ERRORS = ["pos","pos"]
    
    def __init__(self,text,valid_chars=("'",)):
        self._valid_chars = valid_chars
        self._text = text
        self._offset = 0
        # Select proper implementation of self._consume_alpha.
        # 'text' isn't necessarily a string (it could be e.g. a mutable array)
        # so we can't use isinstance(text,unicode) to detect unicode.
        # Instead we typetest the first character of the text.
        # If there's no characters then it doesn't matter what implementation
        # we use since it won't be called anyway. 
        try:
            char1 = text[0]
        except IndexError:
            self._consume_alpha = self._consume_alpha_b
        else:
            if isinstance(char1,unicode):
                self._consume_alpha = self._consume_alpha_u
            else:
                self._consume_alpha = self._consume_alpha_b
    
    def _consume_alpha_b(self,text,offset):
        """Consume an alphabetic character from the given bytestring.

        Given a bytestring and the current offset, this method returns
        the number of characters occupied by the next alphabetic character
        in the string.  Non-ASCII bytes are interpreted as utf-8 and can
        result in multiple characters being consumed.
        """
        assert offset < len(text)
        if text[offset].isalpha():
            return 1
        elif text[offset] >= "\x80":
            return self._consume_alpha_utf8(text,offset)
        return 0

    def _consume_alpha_utf8(self,text,offset):
        """Consume a sequence of utf8 bytes forming an alphabetic character."""
        incr = 2
        u = ""
        while not u and incr <= 4:
            try:
                try:
                    #  In the common case this will be a string
                    u = text[offset:offset+incr].decode("utf8")
                except AttributeError:
                    #  Looks like it was e.g. a mutable char array.
                    try:
                        s = text[offset:offset+incr].tostring()
                    except AttributeError:
                        s = "".join([c for c in text[offset:offset+incr]])
                    u = s.decode("utf8")
            except UnicodeDecodeError:
                incr += 1
        if not u:
            return 0
        if u.isalpha():
            return incr
        if unicodedata.category(u)[0] == "M":
            return incr
        return 0

    def _consume_alpha_u(self,text,offset):
        """Consume an alphabetic character from the given unicode string.

        Given a unicode string and the current offset, this method returns
        the number of characters occupied by the next alphabetic character
        in the string.  Trailing combining characters are consumed as a
        single letter.
        """
        assert offset < len(text)
        incr = 0
        if text[offset].isalpha():
            incr = 1
            while offset + incr < len(text):
                if unicodedata.category(text[offset+incr])[0] != "M":
                    break
                incr += 1
        return incr

    def next(self):
        text = self._text
        offset = self._offset
        while offset < len(text):
            # Find start of next word (must be alpha)
            while offset < len(text):
                incr = self._consume_alpha(text,offset)
                if incr:
                    break
                offset += 1
            curPos = offset
            # Find end of word using, allowing valid_chars
            while offset < len(text):
                incr = self._consume_alpha(text,offset)
                if not incr:
                    if text[offset] in self._valid_chars:
                        incr = 1
                    else:
                        break
                offset += incr
            # Return if word isnt empty
            if(curPos != offset):
                # Make sure word doesn't end with a valid_char
                while text[offset-1] in self._valid_chars:
                    offset = offset - 1
                self._offset = offset
                return (text[curPos:offset],curPos)
        self._offset = offset
        raise StopIteration()


########NEW FILE########
__FILENAME__ = tests
# pyenchant
#
# Copyright (C) 2004-2008, Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

    enchant.tokenize.tests:  unittests for enchant tokenization functions.

"""

import unittest
import array

from enchant.tokenize import *
from enchant.tokenize.en import tokenize as tokenize_en
from enchant.utils import raw_unicode, unicode, bytes


class TestTokenization(unittest.TestCase):
    """TestCases for testing the basic tokenization functionality."""
    
    def test_basic_tokenize(self):
        """Simple regression test for basic white-space tokenization."""
        input = """This is a paragraph.  It's not very special, but it's designed
2 show how the splitter works with many-different combos
of words. Also need to "test" the (handling) of 'quoted' words."""
        output = [
                  ("This",0),("is",5),("a",8),("paragraph",10),("It's",22),
                  ("not",27),("very",31),("special",36),("but",45),("it's",49),
                  ("designed",54),("2",63), ("show",65),("how",70),("the",74),
                  ("splitter",78),("works",87),("with",93),("many-different",98),
                  ("combos",113),("of",120),("words",123),
                  ("Also",130),("need",135),
                  ("to",140),("test",144),("the",150),("handling",155),
                  ("of",165),("quoted",169),("words",177)
                 ]
        self.assertEqual(output,[i for i in basic_tokenize(input)])
        for (itmO,itmV) in zip(output,basic_tokenize(input)):
            self.assertEqual(itmO,itmV)

    def test_tokenize_strip(self):
        """Test special-char-stripping edge-cases in basic_tokenize."""
        input = "((' <this> \"\" 'text' has (lots) of (special chars} >>]"
        output = [ ("<this>",4),("text",15),("has",21),("lots",26),("of",32),
                   ("special",36),("chars}",44),(">>",51)]
        self.assertEqual(output,[i for i in basic_tokenize(input)])
        for (itmO,itmV) in zip(output,basic_tokenize(input)):
            self.assertEqual(itmO,itmV)
            
    def test_wrap_tokenizer(self):
        """Test wrapping of one tokenizer with another."""
        input = "this-string will be split@according to diff'rnt rules"
        from enchant.tokenize import en
        tknzr = wrap_tokenizer(basic_tokenize,en.tokenize)
        tknzr = tknzr(input)
        self.assertEqual(tknzr._tokenizer.__class__,basic_tokenize)
        self.assertEqual(tknzr._tokenizer.offset,0)
        for (n,(word,pos)) in enumerate(tknzr):
            if n == 0:
                self.assertEqual(pos,0)
                self.assertEqual(word,"this")
            if n == 1:
                self.assertEqual(pos,5)
                self.assertEqual(word,"string")
            if n == 2:
                self.assertEqual(pos,12)
                self.assertEqual(word,"will")
                # Test setting offset to a previous token
                tknzr.set_offset(5)
                self.assertEqual(tknzr.offset,5)
                self.assertEqual(tknzr._tokenizer.offset,5)
                self.assertEqual(tknzr._curtok.__class__,empty_tokenize)
            if n == 3:
                self.assertEqual(word,"string")
                self.assertEqual(pos,5)
            if n == 4:
                self.assertEqual(pos,12)
                self.assertEqual(word,"will")
            if n == 5:
                self.assertEqual(pos,17)
                self.assertEqual(word,"be")
                # Test setting offset past the current token
                tknzr.set_offset(20)
                self.assertEqual(tknzr.offset,20)
                self.assertEqual(tknzr._tokenizer.offset,20)
                self.assertEqual(tknzr._curtok.__class__,empty_tokenize)
            if n == 6:
                self.assertEqual(pos,20)
                self.assertEqual(word,"split")
            if n == 7:
                self.assertEqual(pos,26)
                self.assertEqual(word,"according")
                # Test setting offset to middle of current token
                tknzr.set_offset(23)
                self.assertEqual(tknzr.offset,23)
                self.assertEqual(tknzr._tokenizer.offset,23)
                self.assertEqual(tknzr._curtok.offset,3)
            if n == 8:
                self.assertEqual(pos,23)
                self.assertEqual(word,"it")
            # OK, I'm pretty happy with the behaviour, no need to
            # continue testing the rest of the string



class TestFilters(unittest.TestCase):
    """TestCases for the various Filter subclasses."""
    
    text = """this text with http://url.com and SomeLinksLike
              ftp://my.site.com.au/some/file AndOthers not:/quite.a.url
              with-an@aemail.address as well"""
    
    def setUp(self):
        pass
    
    def test_URLFilter(self):
        """Test filtering of URLs"""
        tkns = get_tokenizer("en_US",filters=(URLFilter,))(self.text)
        out = [t for t in tkns]
        exp = [("this",0),("text",5),("with",10),("and",30),
               ("SomeLinksLike",34),("AndOthers",93),("not",103),("quite",108),
               ("a",114),("url",116),("with",134),("an",139),("aemail",142),
               ("address",149),("as",157),("well",160)]
        self.assertEqual(out,exp)
        
    def test_WikiWordFilter(self):
        """Test filtering of WikiWords"""
        tkns = get_tokenizer("en_US",filters=(WikiWordFilter,))(self.text)
        out = [t for t in tkns]
        exp = [("this",0),("text",5),("with",10),("http",15),("url",22),("com",26),
               ("and",30), ("ftp",62),("my",68),("site",71),("com",76),("au",80),
               ("some",83),("file",88),("not",103),("quite",108),
               ("a",114),("url",116),("with",134),("an",139),("aemail",142),
               ("address",149),("as",157),("well",160)]
        self.assertEqual(out,exp)
        
    def test_EmailFilter(self):
        """Test filtering of email addresses"""
        tkns = get_tokenizer("en_US",filters=(EmailFilter,))(self.text)
        out = [t for t in tkns]
        exp = [("this",0),("text",5),("with",10),("http",15),("url",22),("com",26),
               ("and",30),("SomeLinksLike",34),
               ("ftp",62),("my",68),("site",71),("com",76),("au",80),
               ("some",83),("file",88),("AndOthers",93),("not",103),("quite",108),
               ("a",114),("url",116),
               ("as",157),("well",160)]
        self.assertEqual(out,exp)
        
    def test_CombinedFilter(self):
        """Test several filters combined"""
        tkns=get_tokenizer("en_US",filters=(URLFilter,WikiWordFilter,EmailFilter))(self.text)
        out = [t for t in tkns]
        exp = [("this",0),("text",5),("with",10),
               ("and",30),("not",103),("quite",108),
               ("a",114),("url",116),
               ("as",157),("well",160)]
        self.assertEqual(out,exp)


class TestChunkers(unittest.TestCase):
    """TestCases for the various Chunker subclasses."""
    
    def test_HTMLChunker(self):
        """Test filtering of URLs"""
        text = """hello<html><head><title>my title</title></head><body>this is a
                <b>simple</b> HTML document for <p> test<i>ing</i> purposes</p>.
                It < contains > various <-- special characters.
                """
        tkns = get_tokenizer("en_US",chunkers=(HTMLChunker,))(text)
        out = [t for t in tkns]
        exp = [("hello",0),("my",24),("title",27),("this",53),("is",58),
               ("a",61),("simple",82),("HTML",93),("document",98),("for",107),
               ("test",115),("ing",122),("purposes",130),("It",160),
               ("contains",165),("various",176),("special",188),
               ("characters",196)]
        self.assertEqual(out,exp)
        for (word,pos) in out:
            self.assertEqual(text[pos:pos+len(word)],word)



class TestTokenizeEN(unittest.TestCase):
    """TestCases for checking behaviour of English tokenization."""
    
    def test_tokenize_en(self):
        """Simple regression test for English tokenization."""
        input = """This is a paragraph.  It's not very special, but it's designed
2 show how the splitter works with many-different combos
of words. Also need to "test" the handling of 'quoted' words."""
        output = [
                  ("This",0),("is",5),("a",8),("paragraph",10),("It's",22),
                  ("not",27),("very",31),("special",36),("but",45),("it's",49),
                  ("designed",54),("show",65),("how",70),("the",74),
                  ("splitter",78),("works",87),("with",93),("many",98),
                  ("different",103),("combos",113),("of",120),("words",123),
                  ("Also",130),("need",135),
                  ("to",140),("test",144),("the",150),("handling",154),
                  ("of",163),("quoted",167),("words",175)
                 ]
        for (itmO,itmV) in zip(output,tokenize_en(input)):
            self.assertEqual(itmO,itmV)

    def test_unicodeBasic(self):
        """Test tokenization of a basic unicode string."""
        input = raw_unicode(r"Ik ben ge\u00EFnteresseerd in de co\u00F6rdinatie van mijn knie\u00EBn, maar kan niet \u00E9\u00E9n \u00E0 twee enqu\u00EAtes vinden die recht doet aan mijn carri\u00E8re op Cura\u00E7ao")
        output = input.split(" ")
        output[8] = output[8][0:-1]
        for (itmO,itmV) in zip(output,tokenize_en(input)):
            self.assertEqual(itmO,itmV[0])
            self.assertTrue(input[itmV[1]:].startswith(itmO))

    def test_unicodeCombining(self):
        """Test tokenization with unicode combining symbols."""
        input = raw_unicode(r"Ik ben gei\u0308nteresseerd in de co\u00F6rdinatie van mijn knie\u00EBn, maar kan niet e\u0301e\u0301n \u00E0 twee enqu\u00EAtes vinden die recht doet aan mijn carri\u00E8re op Cura\u00E7ao")
        output = input.split(" ")
        output[8] = output[8][0:-1]
        for (itmO,itmV) in zip(output,tokenize_en(input)):
            self.assertEqual(itmO,itmV[0])
            self.assertTrue(input[itmV[1]:].startswith(itmO))

    def test_utf8_bytes(self):
        """Test tokenization of UTF8-encoded bytes (bug #2500184)."""
        # Python3 doesn't support bytestrings, don't run this test
        if str is unicode:
            return
        input = "A r\xc3\xa9sum\xc3\xa9, also spelled resum\xc3\xa9 or resume"
        output = input.split(" ")
        output[1] = output[1][0:-1]
        for (itmO,itmV) in zip(output,tokenize_en(input)):
            self.assertEqual(itmO,itmV[0])
            self.assertTrue(input[itmV[1]:].startswith(itmO))

    def test_utf8_bytes_at_end(self):
        """Test tokenization of UTF8-encoded bytes at end of word."""
        # Python3 doesn't support bytestrings, don't run this test
        if str is unicode:
            return
        input = "A r\xc3\xa9sum\xc3\xa9, also spelled resum\xc3\xa9 or resume"
        output = input.split(" ")
        output[1] = output[1][0:-1]
        for (itmO,itmV) in zip(output,tokenize_en(input)):
            self.assertEqual(itmO,itmV[0])

    def test_utf8_bytes_in_an_array(self):
        """Test tokenization of UTF8-encoded bytes stored in an array."""
        # Python3 doesn't support bytestrings, don't run this test
        if str is unicode:
            return
        input = "A r\xc3\xa9sum\xc3\xa9, also spelled resum\xc3\xa9 or resume"
        output = input.split(" ")
        output[1] = output[1][0:-1]
        input = array.array('c',input)
        output = [array.array('c',w) for w in output]
        for (itmO,itmV) in zip(output,tokenize_en(array.array('c',input))):
            self.assertEqual(itmO,itmV[0])
            self.assertEqual(input[itmV[1]:itmV[1]+len(itmV[0])],itmO)

    def test_bug1591450(self):
        """Check for tokenization regressions identified in bug #1591450."""
        input = """Testing <i>markup</i> and {y:i}so-forth...leading dots and trail--- well, you get-the-point. Also check numbers: 999 1,000 12:00 .45. Done?"""
        output = [
                  ("Testing",0),("i",9),("markup",11),("i",19),("and",22),
                  ("y",27),("i",29),("so",31),("forth",34),("leading",42),
                  ("dots",50),("and",55),("trail",59),("well",68),
                  ("you",74),("get",78),("the",82),("point",86),
                  ("Also",93),("check",98),("numbers",104),("Done",134),
                 ]
        for (itmO,itmV) in zip(output,tokenize_en(input)):
            self.assertEqual(itmO,itmV)

    def test_bug2785373(self):
        """Testcases for bug #2785373"""
        input = "So, one dey when I wes 17, I left."
        for _ in tokenize_en(input):
            pass
        input = raw_unicode("So, one dey when I wes 17, I left.")
        for _ in tokenize_en(input):
            pass

    def test_finnish_text(self):
        """Test tokenizing some Finnish text.

        This really should work since there are no special rules to apply,
        just lots of non-ascii characters.
        """
        inputT = raw_unicode('T\\xe4m\\xe4 on kappale. Eip\\xe4 ole kovin 2 nen, mutta tarkoitus on n\\xe4ytt\\xe4\\xe4 miten sanastaja \\ntoimii useiden-erilaisten sanarypp\\xe4iden kimpussa.\\nPit\\xe4\\xe4p\\xe4 viel\\xe4 \'tarkistaa\' sanat jotka "lainausmerkeiss\\xe4". Heittomerkki ja vaa\'an.\\nUlkomaisia sanoja s\\xfcss, spa\\xdf.')
        outputT = [
(raw_unicode('T\\xe4m\\xe4'),0), (raw_unicode('on'),5), (raw_unicode('kappale'),8), (raw_unicode('Eip\\xe4'),17), (raw_unicode('ole'),22), (raw_unicode('kovin'),26), (raw_unicode('nen'),34), (raw_unicode('mutta'),39), (raw_unicode('tarkoitus'),45), (raw_unicode('on'),55), (raw_unicode('n\\xe4ytt\\xe4\\xe4'),58), (raw_unicode('miten'),66), (raw_unicode('sanastaja'),72), (raw_unicode('toimii'),83), (raw_unicode('useiden'),90), (raw_unicode('erilaisten'),98), (raw_unicode('sanarypp\\xe4iden'),109), (raw_unicode('kimpussa'),123), (raw_unicode('Pit\\xe4\\xe4p\\xe4'),133), (raw_unicode('viel\\xe4'),141), (raw_unicode('tarkistaa'),148), (raw_unicode('sanat'),159), (raw_unicode('jotka'),165), (raw_unicode('lainausmerkeiss\\xe4'),172), (raw_unicode('Heittomerkki'),191), (raw_unicode('ja'),204), (raw_unicode("vaa'an"),207), (raw_unicode('Ulkomaisia'),215), (raw_unicode('sanoja'),226), (raw_unicode('s\\xfcss'),233), (raw_unicode('spa\\xdf'),239),]
        for (itmO,itmV) in zip(outputT,tokenize_en(inputT)):
            self.assertEqual(itmO,itmV)


########NEW FILE########
__FILENAME__ = utils
# pyenchant
#
# Copyright (C) 2004-2008 Ryan Kelly
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
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

enchant.utils:    Misc utilities for the enchant package
========================================================
    
This module provides miscellaneous utilities for use with the
enchant spellchecking package.  Currently available functionality
includes:
        
    * string/unicode compatibility wrappers
    * functions for dealing with locale/language settings
    * ability to list supporting data files (win32 only)
    * functions for bundling supporting data files from a build
      
"""

import os
import sys
import codecs

from enchant.errors import *

# Attempt to access local language information
try:
    import locale
except ImportError:
    locale = None


#
#  Unicode/Bytes compatabilty wrappers.
#
#  These allow us to support both Python 2.x and Python 3.x from
#  the same codebase.
#
#  We provide explicit type objects "bytes" and "unicode" that can be
#  used to construct instances of the appropriate type.  The class
#  "EnchantStr" derives from the default "str" type and implements the
#  necessary logic for encoding/decoding as strings are passed into
#  the underlying C library (where they must always be utf-8 encoded
#  byte strings).
#

try:
    unicode = unicode
except NameError:
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring

def raw_unicode(raw):
    """Make a unicode string from a raw string.

    This function takes a string containing unicode escape characters,
    and returns the corresponding unicode string.  Useful for writing
    unicode string literals in your python source while being upwards-
    compatible with Python 3.  For example, instead of doing this:

      s = u"hello\u2149"  # syntax error in Python 3

    Or this:

      s = "hello\u2149"   # not what you want in Python 2.x

    You can do this:

      s = raw_unicode(r"hello\u2149")  # works everywhere!

    """
    return raw.encode("utf8").decode("unicode-escape")


def raw_bytes(raw):
    """Make a bytes object out of a raw string.

    This is analogous to raw_unicode, but processes byte escape characters
    to produce a bytes object.
    """
    return codecs.escape_decode(raw)[0]
        

class EnchantStr(str):
    """String subclass for interfacing with enchant C library.

    This class encapsulates the logic for interfacing between python native
    string/unicode objects and the underlying enchant library, which expects
    all strings to be UTF-8 character arrays.  It is a subclass of the
    default string class 'str' - on Python 2.x that makes it an ascii string,
    on Python 3.x it is a unicode object.

    Initialise it with a string or unicode object, and use the encode() method
    to obtain an object suitable for passing to the underlying C library.
    When strings are read back into python, use decode(s) to translate them
    back into the appropriate python-level string type.

    This allows us to following the common Python 2.x idiom of returning
    unicode when unicode is passed in, and byte strings otherwise.  It also
    lets the interface be upwards-compatible with Python 3, in which string
    objects are unicode by default.
    """

    def __new__(cls,value):
        """EnchantStr data constructor.

        This method records whether the initial string was unicode, then
        simply passes it along to the default string constructor.
        """
        if type(value) is unicode:
            was_unicode = True
            if str is not unicode:
                value = value.encode("utf-8")
        else:
            was_unicode = False
            if str is not bytes:
                raise Error("Don't pass bytestrings to pyenchant")
        self = str.__new__(cls,value)
        self._was_unicode = was_unicode
        return self

    def encode(self):
        """Encode this string into a form usable by the enchant C library."""
        if str is unicode:
          return str.encode(self,"utf-8")
        else:
          return self

    def decode(self,value):
        """Decode a string returned by the enchant C library."""
        if self._was_unicode:
          if str is unicode:
            # On some python3 versions, ctypes converts c_char_p
            # to str() rather than bytes()   
            if isinstance(value,str):
                value = value.encode()
            return value.decode("utf-8")
          else:
            return value.decode("utf-8")
        else:
          return value


def printf(values,sep=" ",end="\n",file=None):
    """Compatability wrapper from print statement/function.

    This function is a simple Python2/Python3 compatability wrapper
    for printing to stdout.
    """
    if file is None:
        file = sys.stdout
    file.write(sep.join(map(str,values)))
    file.write(end)


try:
    next = next
except NameError:
    def next(iter):
        """Compatability wrapper for advancing an iterator."""
        return iter.next()

try:
    xrange = xrange
except NameError:
    xrange = range


#
#  Other useful functions.
#


def levenshtein(s1, s2):
    """Calculate the Levenshtein distance between two strings.

    This is straight from Wikipedia.
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if not s1:
        return len(s2)
 
    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
 
    return previous_row[-1]



def trim_suggestions(word,suggs,maxlen,calcdist=None):
    """Trim a list of suggestions to a maximum length.

    If the list of suggested words is too long, you can use this function
    to trim it down to a maximum length.  It tries to keep the "best"
    suggestions based on similarity to the original word.

    If the optional "calcdist" argument is provided, it must be a callable
    taking two words and returning the distance between them.  It will be
    used to determine which words to retain in the list.  The default is
    a simple Levenshtein distance.
    """
    if calcdist is None:
        calcdist = levenshtein
    decorated = [(calcdist(word,s),s) for s in suggs]
    decorated.sort()
    return [s for (l,s) in decorated[:maxlen]]
    


def get_default_language(default=None):
    """Determine the user's default language, if possible.
    
    This function uses the 'locale' module to try to determine
    the user's preferred language.  The return value is as
    follows:
        
        * if a locale is available for the LC_MESSAGES category,
          that language is used
        * if a default locale is available, that language is used
        * if the keyword argument <default> is given, it is used
        * if nothing else works, None is returned
        
    Note that determining the user's language is in general only
    possible if they have set the necessary environment variables
    on their system.
    """
    try:
        import locale
        tag = locale.getlocale()[0]
        if tag is None:
            tag = locale.getdefaultlocale()[0]
            if tag is None:
                raise Error("No default language available")
        return tag
    except Exception:
        pass
    return default
get_default_language._DOC_ERRORS = ["LC"]


def get_resource_filename(resname):
    """Get the absolute path to the named resource file.

    This serves widely the same purpose as pkg_resources.resource_filename(),
    but tries to avoid loading pkg_resources unless we're actually in
    an egg.
    """
    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path,resname)
    if os.path.exists(path):
        return path
    if hasattr(sys, "frozen"):
        exe_path = sys.executable
        if not isinstance(exe_path, unicode):
            exe_path = unicode(exe_path,sys.getfilesystemencoding())
        exe_dir = os.path.dirname(exe_path)
        path = os.path.join(exe_dir, resname)
        if os.path.exists(path):
            return path
    else:
        import pkg_resources
        try:
            path = pkg_resources.resource_filename("enchant",resname)
        except KeyError:
            pass
        else:
            path = os.path.abspath(path)
            if os.path.exists(path):
                return path
    raise Error("Could not locate resource '%s'" % (resname,))


def win32_data_files():
    """Get list of supporting data files, for use with setup.py
    
    This function returns a list of the supporting data files available
    to the running version of PyEnchant.  This is in the format expected
    by the data_files argument of the distutils setup function.  It's
    very useful, for example, for including the data files in an executable
    produced by py2exe.
    
    Only really tested on the win32 platform (it's the only platform for
    which we ship our own supporting data files)
    """
    #  Include the main enchant DLL
    try:
        libEnchant = get_resource_filename("libenchant.dll")
    except Error:
        libEnchant = get_resource_filename("libenchant-1.dll")
    mainDir = os.path.dirname(libEnchant)
    dataFiles = [('',[libEnchant])]
    #  And some specific supporting DLLs
    for dll in os.listdir(mainDir):
        if not dll.endswith(".dll"):
            continue
        for prefix in ("iconv","intl","libglib","libgmodule"):
            if dll.startswith(prefix):
                break
        else:
            continue
        dataFiles[0][1].append(os.path.join(mainDir,dll))
    #  And anything found in the supporting data directories
    dataDirs = ("share/enchant/myspell","share/enchant/ispell","lib/enchant")
    for dataDir in dataDirs:
        files = []
        fullDir = os.path.join(mainDir,os.path.normpath(dataDir))
        for fn in os.listdir(fullDir):
            fullFn = os.path.join(fullDir,fn)
            if os.path.isfile(fullFn):
                files.append(fullFn)
        dataFiles.append((dataDir,files))
    return dataFiles
win32_data_files._DOC_ERRORS = ["py","py","exe"]


########NEW FILE########
__FILENAME__ = _enchant
# pyenchant
#
# Copyright (C) 2004-2008, Ryan Kelly
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPsE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# In addition, as a special exception, you are
# given permission to link the code of this program with
# non-LGPL Spelling Provider libraries (eg: a MSFT Office
# spell checker backend) and distribute linked combinations including
# the two.  You must obey the GNU Lesser General Public License in all
# respects for all of the code used other than said providers.  If you modify
# this file, you may extend this exception to your version of the
# file, but you are not obligated to do so.  If you do not wish to
# do so, delete this exception statement from your version.
#
"""

    enchant._enchant:  ctypes-based wrapper for enchant C library

    This module implements the low-level interface to the underlying
    C library for enchant.  The interface is based on ctypes and tries 
    to do as little as possible while making the higher-level components
    easier to write.

    The following conveniences are provided that differ from the underlying
    C API:

        * the "enchant" prefix has been removed from all functions, since
          python has a proper module system
        * callback functions do not take a user_data argument, since
          python has proper closures that can manage this internally
        * string lengths are not passed into functions such as dict_check,
          since python strings know how long they are

"""

import sys, os, os.path
from ctypes import *
from ctypes.util import find_library

from enchant import utils
from enchant.errors import *
from enchant.utils import unicode

# Locate and load the enchant dll.
# We've got several options based on the host platform.

e = None

def _e_path_possibilities():
    """Generator yielding possible locations of the enchant library."""
    yield os.environ.get("PYENCHANT_LIBRARY_PATH")
    yield find_library("enchant")
    yield find_library("libenchant")
    yield find_library("libenchant-1")
    if sys.platform == 'darwin':
         # enchant lib installed by macports
         yield "/opt/local/lib/libenchant.dylib"


# On win32 we ship a bundled version of the enchant DLLs.
# Use them if they're present.
if sys.platform == "win32":
    e_path = None
    try:
        e_path = utils.get_resource_filename("libenchant.dll")
    except (Error,ImportError):
         try:
            e_path = utils.get_resource_filename("libenchant-1.dll")
         except (Error,ImportError):
            pass
    if e_path is not None:
        # We need to use LoadLibraryEx with LOAD_WITH_ALTERED_SEARCH_PATH so
        # that we don't accidentally suck in other versions of e.g. glib.
        if not isinstance(e_path,unicode):
            e_path = unicode(e_path,sys.getfilesystemencoding())
        LoadLibraryEx = windll.kernel32.LoadLibraryExW
        LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008
        e_handle = LoadLibraryEx(e_path,None,LOAD_WITH_ALTERED_SEARCH_PATH)
        if not e_handle:
            raise WinError()
        e = CDLL(e_path,handle=e_handle)


# On darwin we ship a bundled version of the enchant DLLs.
# Use them if they're present.
if e is None and sys.platform == "darwin":
  try:
      e_path = utils.get_resource_filename("lib/libenchant.1.dylib")
  except (Error,ImportError):
      pass
  else:
      # Enchant doesn't natively support relocatable binaries on OSX.
      # We fake it by patching the enchant source to expose a char**, which
      # we can write the runtime path into ourelves.
      e = CDLL(e_path)
      try:
          e_dir = os.path.dirname(os.path.dirname(e_path))
          prefix_dir = POINTER(c_char_p).in_dll(e,"enchant_prefix_dir_p")
          prefix_dir.contents = c_char_p(e_dir)
      except AttributeError:
          e = None


# Not found yet, search various standard system locations.
if e is None:
    for e_path in _e_path_possibilities():
        if e_path is not None:
            try:
                e = cdll.LoadLibrary(e_path)
            except OSError:
                pass
            else:
                break


# No usable enchant install was found :-(
if e is None:
   raise ImportError("enchant C library not found")


# Define various callback function types

def CALLBACK(restype,*argtypes):
    """Factory for generating callback function prototypes.

    This is factored into a factory so I can easily change the definition
    for experimentation or debugging.
    """
    return CFUNCTYPE(restype,*argtypes)

t_broker_desc_func = CALLBACK(None,c_char_p,c_char_p,c_char_p,c_void_p)
t_dict_desc_func = CALLBACK(None,c_char_p,c_char_p,c_char_p,c_char_p,c_void_p)


# Simple typedefs for readability

t_broker = c_void_p
t_dict = c_void_p


# Now we can define the types of each function we are going to use

broker_init = e.enchant_broker_init
broker_init.argtypes = []
broker_init.restype = t_broker

broker_free = e.enchant_broker_free
broker_free.argtypes = [t_broker]
broker_free.restype = None

broker_request_dict = e.enchant_broker_request_dict
broker_request_dict.argtypes = [t_broker,c_char_p]
broker_request_dict.restype = t_dict

broker_request_pwl_dict = e.enchant_broker_request_pwl_dict
broker_request_pwl_dict.argtypes = [t_broker,c_char_p]
broker_request_pwl_dict.restype = t_dict

broker_free_dict = e.enchant_broker_free_dict
broker_free_dict.argtypes = [t_broker,t_dict]
broker_free_dict.restype = None

broker_dict_exists = e.enchant_broker_dict_exists
broker_dict_exists.argtypes = [t_broker,c_char_p]
broker_free_dict.restype = c_int

broker_set_ordering = e.enchant_broker_set_ordering
broker_set_ordering.argtypes = [t_broker,c_char_p,c_char_p]
broker_set_ordering.restype = None

broker_get_error = e.enchant_broker_get_error
broker_get_error.argtypes = [t_broker]
broker_get_error.restype = c_char_p

broker_describe1 = e.enchant_broker_describe
broker_describe1.argtypes = [t_broker,t_broker_desc_func,c_void_p]
broker_describe1.restype = None
def broker_describe(broker,cbfunc):
    def cbfunc1(*args):
        cbfunc(*args[:-1])
    broker_describe1(broker,t_broker_desc_func(cbfunc1),None)

broker_list_dicts1 = e.enchant_broker_list_dicts
broker_list_dicts1.argtypes = [t_broker,t_dict_desc_func,c_void_p]
broker_list_dicts1.restype = None
def broker_list_dicts(broker,cbfunc):
    def cbfunc1(*args):
        cbfunc(*args[:-1])
    broker_list_dicts1(broker,t_dict_desc_func(cbfunc1),None)

try:
    broker_get_param = e.enchant_broker_get_param
except AttributeError:
    #  Make the lookup error occur at runtime
    def broker_get_param(broker,param_name):
        return e.enchant_broker_get_param(param_name)
else:
    broker_get_param.argtypes = [t_broker,c_char_p]
    broker_get_param.restype = c_char_p

try:
    broker_set_param = e.enchant_broker_set_param
except AttributeError:
    #  Make the lookup error occur at runtime
    def broker_set_param(broker,param_name):
        return e.enchant_broker_set_param(param_name)
else:
    broker_set_param.argtypes = [t_broker,c_char_p,c_char_p]
    broker_set_param.restype = None

try:
    get_version = e.enchant_get_version
except AttributeError:
    #  Make the lookup error occur at runtime
    def get_version():
        return e.enchant_get_version()
else:
    get_version.argtypes = []
    get_version.restype = c_char_p


dict_check1 = e.enchant_dict_check
dict_check1.argtypes = [t_dict,c_char_p,c_size_t]
dict_check1.restype = c_int
def dict_check(dict,word):
    return dict_check1(dict,word,len(word))

dict_suggest1 = e.enchant_dict_suggest
dict_suggest1.argtypes = [t_dict,c_char_p,c_size_t,POINTER(c_size_t)]
dict_suggest1.restype = POINTER(c_char_p)
def dict_suggest(dict,word):
    numSuggsP = pointer(c_size_t(0))
    suggs_c = dict_suggest1(dict,word,len(word),numSuggsP)
    suggs = []
    n = 0
    while n < numSuggsP.contents.value:
        suggs.append(suggs_c[n])
        n = n + 1
    if numSuggsP.contents.value > 0:
        dict_free_string_list(dict,suggs_c)
    return suggs

dict_add1 = e.enchant_dict_add
dict_add1.argtypes = [t_dict,c_char_p,c_size_t]
dict_add1.restype = None
def dict_add(dict,word):
    return dict_add1(dict,word,len(word))

dict_add_to_pwl1 = e.enchant_dict_add
dict_add_to_pwl1.argtypes = [t_dict,c_char_p,c_size_t]
dict_add_to_pwl1.restype = None
def dict_add_to_pwl(dict,word):
    return dict_add_to_pwl1(dict,word,len(word))

dict_add_to_session1 = e.enchant_dict_add_to_session
dict_add_to_session1.argtypes = [t_dict,c_char_p,c_size_t]
dict_add_to_session1.restype = None
def dict_add_to_session(dict,word):
    return dict_add_to_session1(dict,word,len(word))

dict_remove1 = e.enchant_dict_remove
dict_remove1.argtypes = [t_dict,c_char_p,c_size_t]
dict_remove1.restype = None
def dict_remove(dict,word):
    return dict_remove1(dict,word,len(word))

dict_remove_from_session1 = e.enchant_dict_remove_from_session
dict_remove_from_session1.argtypes = [t_dict,c_char_p,c_size_t]
dict_remove_from_session1.restype = c_int
def dict_remove_from_session(dict,word):
    return dict_remove_from_session1(dict,word,len(word))

dict_is_added1 = e.enchant_dict_is_added
dict_is_added1.argtypes = [t_dict,c_char_p,c_size_t]
dict_is_added1.restype = c_int
def dict_is_added(dict,word):
    return dict_is_added1(dict,word,len(word))

dict_is_removed1 = e.enchant_dict_is_removed
dict_is_removed1.argtypes = [t_dict,c_char_p,c_size_t]
dict_is_removed1.restype = c_int
def dict_is_removed(dict,word):
    return dict_is_removed1(dict,word,len(word))

dict_is_in_session1 = e.enchant_dict_is_in_session
dict_is_in_session1.argtypes = [t_dict,c_char_p,c_size_t]
dict_is_in_session1.restype = c_int
def dict_is_in_session(dict,word):
    return dict_is_in_session1(dict,word,len(word))

dict_store_replacement1 = e.enchant_dict_store_replacement
dict_store_replacement1.argtypes = [t_dict,c_char_p,c_size_t,c_char_p,c_size_t]
dict_store_replacement1.restype = None
def dict_store_replacement(dict,mis,cor):
    return dict_store_replacement1(dict,mis,len(mis),cor,len(cor))

dict_free_string_list = e.enchant_dict_free_string_list
dict_free_string_list.argtypes = [t_dict,POINTER(c_char_p)]
dict_free_string_list.restype = None

dict_get_error = e.enchant_dict_get_error
dict_get_error.argtypes = [t_dict]
dict_get_error.restype = c_char_p

dict_describe1 = e.enchant_dict_describe
dict_describe1.argtypes = [t_dict,t_dict_desc_func,c_void_p]
dict_describe1.restype = None
def dict_describe(dict,cbfunc):
    def cbfunc1(tag,name,desc,file,data):
        cbfunc(tag,name,desc,file)
    dict_describe1(dict,t_dict_desc_func(cbfunc1),None)



########NEW FILE########
__FILENAME__ = shootout
#!python
#
#  Written by Ryan Kelly, 2005.  This script is placed in the public domain.
#
# Arrange a short shootout to determine the best spellchecker of them all!!
#
# This script runs a batch of tests against each enchant spellchecker
# provider, collecting statistics as it goes.  The tests are read from
# a text file, one per line, of the format "<mis> <cor>" where <mis>
# is the misspelled word and <cor> the correct spelling.  Each must be
# a single word.
#
# The statistics printed at the end of the run are:
#
#    EXISTED:    percentage of correct words which the provider
#                reported as being correct
#
#    SUGGESTED:  percentage of misspelled words for which the correct
#                spelling was suggested
#
#    SUGGP:      percentage of misspelled words whose correct spelling
#                existed, for which the correct spelling was suggested
#                (this is simply 100*SUGGESTED/EXISTED)
#
#    FIRST:      percentage of misspelled words for which the correct
#                spelling was the first suggested correction.
#
#    FIRST5:     percentage of misspelled words for which the correct
#                spelling was in the first five suggested corrections
# 
#    FIRST10:    percentage of misspelled words for which the correct
#                spelling was in the first ten suggested corrections
#
#    AVERAGE DIST TO CORRECTION:  the average location of the correct
#                                 spelling within the suggestions list,
#                                 over those words for which the correct
#                                 spelling was found
# 

import enchant
import enchant.utils

# List of providers to test
# Providers can also be named "pypwl:<encode>" where <encode> is
# the encoding function to use for PyPWL.  All PyPWL instances
# will use <wordsfile> as their word list
providers = ("aspell","pypwl",)

# File containing test cases, and the language they are in
# A suitable file can be found at http://aspell.net/test/batch0.tab
datafile = "batch0.tab"
lang = "en_US"
#wordsfile = "/usr/share/dict/words"
wordsfile = "words"

# Corrections to make the the 'correct' words in the tests
# This is so we can use unmodified tests published by third parties
corrections = (("caesar","Caesar"),("confucianism","Confucianism"),("february","February"),("gandhi","Gandhi"),("muslims","Muslims"),("israel","Israel"))

# List of dictionary objects to test
dicts = []
# Number of correct words missed by each dictionary
missed = []
# Number of corrections not suggested by each dictionary
incorrect = []
# Number of places to find correct suggestion, or -1 if not found
dists = []

# Create each dictionary object
for prov in providers:
    if prov == "pypwl":
        d = enchant.request_pwl_dict(wordsfile)
    else:
        b = enchant.Broker()
        b.set_ordering(lang,prov)
        d = b.request_dict(lang)
        if not d.provider.name == prov:
          raise RuntimeError("Provider '%s' has no dictionary for '%s'"%(prov,lang))
        del b
    dicts.append(d)
    missed.append([])
    incorrect.append([])
    dists.append([])
    
# Actually run the tests
testcases = file(datafile,"r")
testnum = 0
for testcase in testcases:
    # Skip lines starting with "#"
    if testcase[0] == "#":
        continue
    # Split into words
    words = testcase.split()
    # Skip tests that have multi-word corrections
    if len(words) > 2:
        continue
    cor = words[1].strip(); mis = words[0].strip()
    # Make any custom corrections
    for (old,new) in corrections:
        if old == cor:
            cor = new
            break
    # Actually do the test
    testnum += 1 
    print "TEST", testnum, ":", mis, "->", cor
    for dictnum,dict in enumerate(dicts):
        # Check whether it contains the correct word
        if not dict.check(cor):
            missed[dictnum].append(cor)
        # Check on the suggestions provided
        suggs = dict.suggest(mis)
	if cor not in suggs:
            incorrect[dictnum].append((mis,cor))
            dists[dictnum].append(-1)
        else:
            dists[dictnum].append(suggs.index(cor))
numtests = testnum

# Print a report for each provider
for pnum,prov in enumerate(providers):
    print "======================================="
    exdists = [d for d in dists[pnum] if d >= 0]
    print "PROVIDER:", prov
    print "  EXISTED: %.1f"%(((numtests - len(missed[pnum]))*100.0)/numtests,)
    print "  SUGGESTED: %.1f"%((len(exdists)*100.0)/numtests,)
    print "  SUGGP: %.1f"%((len(exdists)*100.0)/(numtests - len(missed[pnum])),)
    print "  FIRST: %.1f"%((len([d for d in exdists if d == 0])*100.0)/numtests,)
    print "  FIRST5: %.1f"%((len([d for d in exdists if d < 5])*100.0)/numtests,)
    print "  FIRST10: %.1f"%((len([d for d in exdists if d < 10])*100.0)/numtests,)
    print "  AVERAGE DIST TO CORRECTION: %.2f" % (float(sum(exdists))/len(exdists),)
print "======================================="



########NEW FILE########
__FILENAME__ = test_multiprocessing

import os
import enchant
from multiprocessing import Pool


def do_something(words):
    d = enchant.Dict('en-US')
    for word in words:
        d.check(word)
    return True


def will_block():
    words = ["hello" for i in range(1000)]
    input = [words for i in range(1000)]
    print('Starting')
    pool = Pool(10)
    for i, result in enumerate(pool.imap_unordered(do_something, input)):
        print ('Done {0}: {1}'.format(i, result))
    print('Finished')


if __name__ == '__main__':
    will_block()


########NEW FILE########
__FILENAME__ = wx_example


import wx

from enchant.checker import SpellChecker
from enchant.checker.wxSpellCheckerDialog import wxSpellCheckerDialog

# Retreive the text to be checked
text = "this is some smple text with a few erors in it"
print "[INITIAL TEXT:]", text

# Need to have an App before any windows will be shown
app = wx.PySimpleApp()

# Construct the dialog, and the SpellChecker it is to use
dlg = wxSpellCheckerDialog(None)
chkr = SpellChecker("en_US",text)
dlg.SetSpellChecker(chkr)

# Display the dialog, allowing user interaction
if dlg.ShowModal() == wx.ID_OK:
    # Checking completed successfully
    # Retreive the modified text
    print "[FINAL TEXT:]", chkr.get_text()
else:
    # Checking was cancelled
    print "[CHECKING CANCELLED]"
    



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyEnchant documentation build configuration file, created by
# sphinx-quickstart on Thu Apr 28 20:41:16 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

os.environ["PYENCHANT_IGNORE_MISSING_LIB"] = "1"
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import enchant

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              'hyde.ext.plugins.sphinx']

try:
    import sphinxcontrib.spelling
except ImportError:
    pass
else:
    extensions.append("sphinxcontrib.spelling")

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = '_sphinx_index'

# General information about the project.
project = u'PyEnchant'
copyright = u'2011, Ryan Kelly'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = enchant.__version__
# The full version, including alpha/beta/rc tags.
release = enchant.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
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
pygments_style = 'default'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
html_static_path = ['_static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyEnchantdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'PyEnchant.tex', u'PyEnchant Documentation',
   u'Ryan Kelly', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
