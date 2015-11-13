__FILENAME__ = PAIMEIdiff
#
# PaiMei
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: PAIMEIdiff.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''
import wx
import _PAIMEIdiff
import sys
import os
sys.path.append("modules/_PAIMEIdiff/DiffModules")

# begin wxGlade: dependencies
# end wxGlade

class PAIMEIdiff(wx.Panel):
    '''
    The bin diff module panel.
    '''
    
    documented_variables = {
    }
    pida_modules = {}
    def __init__(self, *args, **kwds):
        # begin wxGlade: PAIMEIdiff.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.log_splitter               = wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_BORDER)
        self.log_window                 = wx.Panel(self.log_splitter, -1)
        self.top_window                 = wx.Panel(self.log_splitter, -1)
        self.matchbook                  = wx.Notebook(self.top_window, -1, style=0)
        self.matchbook_unmatched_a      = wx.Panel(self.matchbook, -1)
        self.matchbook_matched          = wx.Panel(self.matchbook, -1)
        self.module_b_sizer_staticbox   = wx.StaticBox(self, -1, "Module B")
        self.module_a_sizer_staticbox   = wx.StaticBox(self, -1, "Module A")
        
               
        self.module_a                   = _PAIMEIdiff.ExplorerTreeCtrl.ExplorerTreeCtrl(self, -1, top=self, style=wx.TR_HAS_BUTTONS|wx.TR_LINES_AT_ROOT|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER, name="A")
        self.module_a_load              = wx.Button(self, -1, "Load")
        self.module_b                   = _PAIMEIdiff.ExplorerTreeCtrl.ExplorerTreeCtrl(self, -1, top=self, style=wx.TR_HAS_BUTTONS|wx.TR_LINES_AT_ROOT|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER, name="B")
        self.module_b_load              = wx.Button(self, -1, "Load")
                                        
        self.MatchedAListCtrl           = _PAIMEIdiff.MatchedListCtrl.MatchedListCtrl(self.matchbook_matched, -1, top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER | wx.LC_SINGLE_SEL )
        self.MatchedBListCtrl           = _PAIMEIdiff.MatchedListCtrl.MatchedListCtrl(self.matchbook_matched, -1, top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER | wx.LC_SINGLE_SEL )
        self.UnMatchedAListCtrl         = _PAIMEIdiff.UnmatchedListCtrl.UnmatchedListCtrl(self.matchbook_unmatched_a, -1,top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER | wx.LC_SINGLE_SEL )
        self.UnMatchedBListCtrl         = _PAIMEIdiff.UnmatchedListCtrl.UnmatchedListCtrl(self.matchbook_unmatched_a, -1,top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER | wx.LC_SINGLE_SEL )
        
        self.configure                  = wx.Button(self.top_window, -1, "Configure")
        self.execute                    = wx.Button(self.top_window, -1, "Execute")
        self.exp                        = wx.Button(self.top_window, -1, "Export")
        self.info                       = wx.TextCtrl(self.top_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)
        self.log                        = wx.TextCtrl(self.log_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)
        
        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        
        #flag to tell us to ignore insignificant variables
        self.ignore_insignificant = 0
        #flag tells us to loop until we don't have a change
        self.loop_until_change  = 0
        
        #our default values for the insiginificant functions
        self.insignificant_function = (1,1,1,1)
        #our default value for the insignificant basic block
        self.insignificant_bb = 2
        #function pointer tables its where functions get registered
        self.match_function_table       = {}
        self.match_basic_block_table    = {}
        self.diff_function_table        = {}
        self.diff_basic_block_table     = {}
        self.used_match_function_table       = {}
        self.used_match_basic_block_table    = {}
        self.used_diff_function_table        = {}
        self.used_diff_basic_block_table     = {}
        #table contains references to all the modules related to diffing/matching
        self.module_table               = {}
        #our list that contains the matched functions
        self.matched_list       = _PAIMEIdiff.MatchedList.MatchedList(parent=self) 
        self.unmatched_list     = _PAIMEIdiff.UnmatchedList.UnmatchedList()
        
        self.insig_a_list       = []
        self.insig_b_list       = []
        self.module_a_name      = ""
        self.module_b_name      = ""
        
        self.crc_table = {}
     
        self.list_book  = kwds["parent"]             # handle to list book.
        self.main_frame = self.list_book.top         # handle to top most frame.
        
        self.crc_build_table()
        
        
       
                     
        # log window bindings.
        self.Bind(wx.EVT_TEXT_MAXLEN,   self.OnMaxLogLengthReached, self.log)
        self.Bind(wx.EVT_BUTTON,        self.module_a.load_module,  self.module_a_load)
        self.Bind(wx.EVT_BUTTON,        self.module_b.load_module,  self.module_b_load)
        self.Bind(wx.EVT_BUTTON,        self.on_configure,          self.configure)
        self.Bind(wx.EVT_BUTTON,        self.on_execute,            self.execute)
        self.Bind(wx.EVT_BUTTON,        self.on_export,             self.exp)
        
        
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelectedA,      self.MatchedAListCtrl)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelectedB,      self.MatchedBListCtrl)
        #self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.MatchedAListCtrl.OnListItemRightClick,  self.MatchedAListCtrl)
        self.MatchedAListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.MatchedAListCtrl.OnRightClick)
        self.MatchedBListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.MatchedBListCtrl.OnRightClick)
         
        self.UnMatchedAListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.UnMatchedAListCtrl.OnRightClick)
        self.UnMatchedBListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.UnMatchedBListCtrl.OnRightClick)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelectedUnmatchA,      self.UnMatchedAListCtrl)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelectedUnmatchB,      self.UnMatchedBListCtrl)
        
        
        self.msg("PaiMei Binary Diffing Engine")
        self.msg("Module by Peter Silberman\n")
        
        #dynamically load the matching/diffing modules
        for mod in os.listdir("modules/_PAIMEIdiff/DiffModules"):
            if mod.endswith(".py") and mod != "defines.py":
                try:
                    module       = mod.replace(".py", "")
                    exec("from %s import *" % module)

                    exec("%s(parent=self)" % module)

                    
                except:
                    import traceback
                    traceback.print_exc(file=sys.stdout)

                    
   
    ####################################################################################################################
    def __set_properties(self):
        # begin wxGlade: PAIMEIdiff.__set_properties
        self.info.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        self.log.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        # end wxGlade

	####################################################################################################################
    def __do_layout(self):
        # begin wxGlade: PAIMEIdiff.__do_layout
        overall = wx.BoxSizer(wx.HORIZONTAL)
        log_window_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_window_sizer = wx.BoxSizer(wx.VERTICAL)
        middle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        actions_sizer = wx.GridSizer(2, 2, 0, 0)
        sizer_9 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_11 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        modules_sizer = wx.BoxSizer(wx.VERTICAL)
        module_b_sizer = wx.StaticBoxSizer(self.module_b_sizer_staticbox, wx.VERTICAL)
        module_a_sizer = wx.StaticBoxSizer(self.module_a_sizer_staticbox, wx.VERTICAL)
        module_a_sizer.Add(self.module_a, 2, wx.EXPAND, 0)
        module_a_sizer.Add(self.module_a_load, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        modules_sizer.Add(module_a_sizer, 1, wx.EXPAND, 0)
        module_b_sizer.Add(self.module_b, 2, wx.EXPAND, 0)
        module_b_sizer.Add(self.module_b_load, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        modules_sizer.Add(module_b_sizer, 1, wx.EXPAND, 0)
        overall.Add(modules_sizer, 1, wx.EXPAND, 0)
        sizer_12.Add(self.MatchedAListCtrl, 1, wx.EXPAND, 0)
        sizer_12.Add(self.MatchedBListCtrl, 1, wx.EXPAND, 0)
        sizer_3.Add(sizer_12, 1, wx.EXPAND, 0)
        self.matchbook_matched.SetAutoLayout(True)
        self.matchbook_matched.SetSizer(sizer_3)
        sizer_3.Fit(self.matchbook_matched)
        sizer_3.SetSizeHints(self.matchbook_matched)
        sizer_11.Add(self.UnMatchedAListCtrl, 1, wx.EXPAND, 0)
        sizer_11.Add(self.UnMatchedBListCtrl, 1, wx.EXPAND, 0)
        sizer_9.Add(sizer_11, 1, wx.EXPAND, 0)
        self.matchbook_unmatched_a.SetAutoLayout(True)
        self.matchbook_unmatched_a.SetSizer(sizer_9)
        sizer_9.Fit(self.matchbook_unmatched_a)
        sizer_9.SetSizeHints(self.matchbook_unmatched_a)
        self.matchbook.AddPage(self.matchbook_matched, "Matched")
        self.matchbook.AddPage(self.matchbook_unmatched_a, "Unmatched Functions")
        top_window_sizer.Add(self.matchbook, 4, wx.EXPAND, 0)
        actions_sizer.Add(self.configure, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        actions_sizer.Add(self.execute, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        actions_sizer.Add(self.exp, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        middle_sizer.Add(actions_sizer, 1, wx.EXPAND, 0)
        middle_sizer.Add(self.info, 1, wx.EXPAND, 0)
        top_window_sizer.Add(middle_sizer, 1, wx.EXPAND, 0)
        self.top_window.SetAutoLayout(True)
        self.top_window.SetSizer(top_window_sizer)
        top_window_sizer.Fit(self.top_window)
        top_window_sizer.SetSizeHints(self.top_window)
        log_window_sizer.Add(self.log, 1, wx.EXPAND, 0)
        self.log_window.SetAutoLayout(True)
        self.log_window.SetSizer(log_window_sizer)
        log_window_sizer.Fit(self.log_window)
        log_window_sizer.SetSizeHints(self.log_window)
        self.log_splitter.SplitHorizontally(self.top_window, self.log_window)
        overall.Add(self.log_splitter, 3, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        # end wxGlade

# end of class PAIMEIdiff



    ####################################################################################################################
    def _get_status (self):
        '''
        Return the text to display in the status bar on page change.
        '''

        return "Binary Diffing Engine"

        
    ####################################################################################################################
    def _set_status (self, msg):
        '''
        Set the text to display in the status bar.
        '''

        self.main_frame.status_bar.SetStatusText(msg, 1)


    ####################################################################################################################
    def OnMaxLogLengthReached (self, event):
        '''
        Clear the log window when the max length is reach.
        
        @todo: Make this smarter by maybe only clearing half the lines.
        '''
        
        self.log.SetValue("")


    ####################################################################################################################
    def err (self, message):
        '''
        Write an error message to log window.
        '''

        self.log.AppendText("[!] %s\n" % message)


    ####################################################################################################################
    def msg (self, message):
        '''
        Write a log message to log window.
        '''

        self.log.AppendText("[*] %s\n" % message)
    ####################################################################################################################
    def on_configure(self, event):
        '''
        Display the configure dialog box
        '''
        dlg = _PAIMEIdiff.DiffConfigureDlg.DiffConfigureDlg(parent=self)
        dlg.ShowModal()
        
    ####################################################################################################################
    def on_export(self, event):
        '''
        Export the diffing results to an html web page
        '''
        dlg = wx.DirDialog(self, "Choose a directory:",
                          style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() != wx.ID_OK:
            self.err("You need to select a directory to output the report to")
        else:
            path = dlg.GetPath() + "\\"
            report = _PAIMEIdiff.PAIMEIDiffReport.PAIMEIDiffReport(self,path)
            report.generate_report()
        
    ####################################################################################################################
    def on_execute(self, event):
        '''
        Execute the matching/diffing algorithms.
        '''
        self.msg("Using an Insignificant function definition of %d:%d:%d:%d" % self.insignificant_function)
        self.msg("Using an Insignificant BB definition of %d" % self.insignificant_bb)
        mod_a = self.pida_modules[self.module_a_name]
        mod_b = self.pida_modules[self.module_b_name]
        
        mm = _PAIMEIdiff.ModuleMatcher.ModuleMatcher(self,mod_a,mod_b)
        mm.match_modules()
        md = _PAIMEIdiff.ModuleDiffer.ModuleDiffer(self)
        md.diff_modules()
        self.msg("Number of different functions: %d" % self.matched_list.num_different_functions)
        self.DisplayMatched()
        self.DisplayUnmatched()
        
        
    ####################################################################################################################
    def OnListItemSelectedA(self, evt):
        curr = evt.m_itemIndex
        self.MatchedBListCtrl.curr = curr
        self.MatchedAListCtrl.curr = curr
        item = self.MatchedBListCtrl.GetItem(curr)
        item.m_stateMask = wx.LIST_STATE_SELECTED  
        item.m_state     = wx.LIST_STATE_SELECTED  
        self.MatchedBListCtrl.SetItem(item)
        self.MatchedBListCtrl.EnsureVisible(curr)
        
    ####################################################################################################################        
    def OnListItemSelectedB(self, evt):
        curr = evt.m_itemIndex
        self.MatchedBListCtrl.curr = curr
        self.MatchedAListCtrl.curr = curr
        item = self.MatchedAListCtrl.GetItem(curr)
        item.m_stateMask = wx.LIST_STATE_SELECTED  
        item.m_state     = wx.LIST_STATE_SELECTED  
        self.MatchedAListCtrl.SetItem(item)
        self.MatchedAListCtrl.EnsureVisible(curr)

    ####################################################################################################################
    def OnListItemSelectedUnmatchA(self,evt):
        self.UnMatchedAListCtrl.curr = evt.m_itemIndex
        
    ####################################################################################################################
    def OnListItemSelectedUnmatchB(self,evt):
        self.UnMatchedBListCtrl.curr = evt.m_itemIndex
        
    ####################################################################################################################
    def manual_match_function(self):
        '''
        Allows the user to manually match functions
        '''
        if self.UnMatchedAListCtrl.curr == -1 and self.UnMatchedAListCtrl.curr <= self.UnMatchedAListCtrl.GetItemCount():
            self.err("Please select a function in unmatched module a to match with unmatched module b")
            return
        if self.UnMatchedBListCtrl.curr == -1 and self.UnMatchedBListCtrl.curr <= self.UnMatchedBListCtrl.GetItemCount():
            self.err("Please select a function in unmatched module b to match with unmatched module a")
            return
            
        func_a = self.UnMatchedAListCtrl.function_list[ self.UnMatchedAListCtrl.curr ]
        func_b = self.UnMatchedBListCtrl.function_list[ self.UnMatchedBListCtrl.curr ]
        
        del self.UnMatchedAListCtrl.function_list[ self.UnMatchedAListCtrl.curr ]
        del self.UnMatchedBListCtrl.function_list[ self.UnMatchedBListCtrl.curr ]
        
        self.UnMatchedAListCtrl.DeleteItem( self.UnMatchedAListCtrl.curr )
        self.UnMatchedBListCtrl.DeleteItem( self.UnMatchedBListCtrl.curr )
        
        
        self.matched_list.add_matched_function(func_a, func_b, "Manual")
        
        
        self.MatchedAListCtrl.add_function(func_a,-1)
        self.MatchedBListCtrl.add_function(func_b,-1)


    ####################################################################################################################
    def unmatch_function(self):
        '''
        Allows the user to un matched previously matched functions
        '''
        if self.MatchedAListCtrl.curr == -1 and self.MatchedAListCtrl.curr <= self.MatchedAListCtrl.GetItemCount():
            self.err("Please select a function in module a to unmatch")
            return
        if self.MatchedBListCtrl.curr == -1 and self.MatchedBListCtrl.curr <= self.MatchedBListCtrl.GetItemCount():
            self.err("Please select a function in module b to unmatch")
            return

        (func_a, func_b) = self.matched_list.unmatch_function( self.MatchedAListCtrl.curr )
                
        self.MatchedAListCtrl.DeleteItem( self.MatchedAListCtrl.curr )
        self.MatchedBListCtrl.DeleteItem( self.MatchedBListCtrl.curr )

        self.UnMatchedAListCtrl.add_function(func_a,-1)
        self.UnMatchedBListCtrl.add_function(func_b,-1)

        

    
    def crc_build_table(self):
        '''
        Build the CRC table to be used in our CRC checksumming

        '''
        crc = 0
        polynomial = 0xEDB88320L
        i = 0
        j = 0
        for i in range(i, 256,1):
            crc = i
            j = 8
            while j > 0:
                if crc & 1:
                    crc = (crc >> 1) ^ polynomial
                else:
                    crc >>= 1
                j-=1
            self.crc_table[ i ] = crc

    def register_match_function(self, function, ref):
        '''
        Register a function to be used in the function matching phase.
        '''
        self.match_function_table[ ref.module_name ] = function
    
    def register_match_basic_block(self, function, ref):
        '''
        Register a function to be used in the basic block matching phase.
        '''
        self.match_basic_block_table[ ref.module_name ] = function
        
    def register_diff_function(self, function, ref):
        '''
        Register a function to be used in the function diffing phase.
        '''
        self.diff_function_table[ ref.module_name ] = function
        
    def register_diff_basic_block(self, function, ref):
        '''
        Register a function to be used in the basic block diffing phase.
        '''
        self.diff_basic_block_table[ ref.module_name ] = function
        
    def register_module(self, ref):
        '''
        Register a module thats being used in the fuction/basic block diffing/matching.
        '''
        self.module_table[ ref.module_name ] = ref

    def DisplayMatched(self):
        '''
        Display the matched functions.
        '''
        self.MatchedAListCtrl.DeleteAllItems()
        self.MatchedBListCtrl.DeleteAllItems()
        i = 0
        while i < self.matched_list.num_matched_functions:
            (func_a, func_b) = self.matched_list.matched_functions[i]
            #print "%s %s %d" % (func_a.name, func_b.name, i)
            self.MatchedAListCtrl.add_function(func_a,i)
            self.MatchedBListCtrl.add_function(func_b,i)
            i+=1
            
    def DisplayUnmatched(self):
        '''
        Display the un matched functions.
        '''
        self.UnMatchedAListCtrl.DeleteAllItems()
        self.UnMatchedBListCtrl.DeleteAllItems()
        i = 0
        while i < len(self.unmatched_list.unmatched_module_a):
            self.UnMatchedAListCtrl.add_function(self.unmatched_list.unmatched_module_a[i],i)
            i+=1
        i = 0
        while i < len(self.unmatched_list.unmatched_module_b):
            self.UnMatchedBListCtrl.add_function(self.unmatched_list.unmatched_module_b[i],i)
            i+=1    
            
########NEW FILE########
__FILENAME__ = PAIMEIdocs
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PAIMEIdocs.py 231 2008-07-21 22:43:36Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.html as html

class PAIMEIdocs(wx.Panel):
    '''
    '''

    sections = {
                   "General":   "../docs/index.html",
                   "PyDbg":     "../docs/PyDBG/class-tree.html",
                   "PIDA":      "../docs/PIDA/class-tree.html",
                   "pGRAPH":    "../docs/pGRAPH/class-tree.html",
                   "Utilities": "../docs/Utilities/class-tree.html",
               }

    list_book  = None     # handle to list book.
    main_frame = None     # handle to top most frame.
    selection  = None     # selected help section.

    def __init__ (self, *args, **kwds):
        self.choices = self.sections.keys()
        self.choices.sort()

        # begin wxGlade: PAIMEIdocs.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.navigation_staticbox = wx.StaticBox(self, -1, "Navigate")
        self.section_dropdown     = wx.Choice(self, -1, choices=self.choices)
        self.load                 = wx.Button(self, -1, "Load")
        self.back                 = wx.Button(self, -1, "Back")
        self.forward              = wx.Button(self, -1, "Forward")
        self.html_help            = html.HtmlWindow(self, -1)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.list_book  = kwds["parent"]            # handle to list book.
        self.main_frame = self.list_book.top        # handle to top most frame.

        # bind the dropdown.
        self.Bind(wx.EVT_CHOICE, self.on_section_choice, self.section_dropdown)

        # bind the buttons
        self.Bind(wx.EVT_BUTTON, self.on_back,    self.back)
        self.Bind(wx.EVT_BUTTON, self.on_forward, self.forward)
        self.Bind(wx.EVT_BUTTON, self.on_load,    self.load)

        # load the default top-level documentation page.
        self.html_help.LoadPage(self.sections["General"])


    ####################################################################################################################
    def __set_properties (self):
        # begin wxGlade: PAIMEIdocs.__set_properties
        self.section_dropdown.SetSelection(-1)
        # end wxGlade


    ####################################################################################################################
    def __do_layout (self):
        # begin wxGlade: PAIMEIdocs.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        navigation = wx.StaticBoxSizer(self.navigation_staticbox, wx.HORIZONTAL)
        navigation.Add(self.section_dropdown, 0, wx.ADJUST_MINSIZE, 0)
        navigation.Add(self.load, 0, wx.ADJUST_MINSIZE, 0)
        navigation.Add(self.back, 0, wx.ADJUST_MINSIZE, 0)
        navigation.Add(self.forward, 0, wx.ADJUST_MINSIZE, 0)
        overall.Add(navigation, 0, wx.EXPAND, 0)
        overall.Add(self.html_help, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        # end wxGlade


    ####################################################################################################################
    def on_back (self, event):
        self.html_help.HistoryBack()


    ####################################################################################################################
    def on_forward (self, event):
        self.html_help.HistoryForward()


    ####################################################################################################################
    def on_load (self, event):
        if not self.selection:
            return

        self.html_help.LoadPage(self.main_frame.cwd + "/" + self.sections[self.selection])


    ####################################################################################################################
    def on_section_choice (self, event):
        self.selection = event.GetString()

########NEW FILE########
__FILENAME__ = PAIMEIexplorer
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PAIMEIexplorer.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.html as html

import sys

import _PAIMEIexplorer

#######################################################################################################################
class PAIMEIexplorer (wx.Panel):
    '''
    The PIDA module explorer panel.
    '''

    documented_properties = {
        "pida_modules"           : "Dictionary of loaded PIDA modules.",
        "pida_copy(module_name)" : "Copy the specified module from pstalker to the explorer pane.",
    }

    list_book    = None      # handle to list book.
    main_frame   = None      # handle to top most frame.
    pida_modules = {}        # dictionary of loaded PIDA modules.

    def __init__(self, *args, **kwds):
        # begin wxGlade: PAIMEIexplorer.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.log_splitter                = wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_BORDER)
        self.log_window                  = wx.Panel(self.log_splitter, -1)
        self.top_window                  = wx.Panel(self.log_splitter, -1)
        self.disassmbly_column_staticbox = wx.StaticBox(self.top_window, -1, "Disassembly")
        self.special_column_staticbox    = wx.StaticBox(self.top_window, -1, "Special")
        self.browser_column_staticbox    = wx.StaticBox(self.top_window, -1, "Browser")
        self.pida_modules_static         = wx.StaticText(self.top_window, -1, "PIDA Modules")
        self.pida_modules_list           = _PAIMEIexplorer.PIDAModulesListCtrl.PIDAModulesListCtrl(self.top_window, -1, top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
        self.add_module                  = wx.Button(self.top_window, -1, "Add Module(s)")
        self.explorer                    = _PAIMEIexplorer.ExplorerTreeCtrl.ExplorerTreeCtrl(self.top_window, -1, top=self, style=wx.TR_HAS_BUTTONS|wx.TR_LINES_AT_ROOT|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER)
        self.disassembly                 = _PAIMEIexplorer.HtmlWindow.HtmlWindow(self.top_window, -1, top=self, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.special                     = wx.TextCtrl(self.top_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.log                         = wx.TextCtrl(self.log_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # set the default sash position to be 100 pixels from the bottom (small log window).
        self.log_splitter.SetSashPosition(-100)

        self.list_book    = kwds["parent"]             # handle to list book.
        self.main_frame   = self.list_book.top         # handle to top most frame.

        # log window bindings.
        self.Bind(wx.EVT_TEXT_MAXLEN, self.OnMaxLogLengthReached, self.log)

        # explorer tree ctrl.
        self.explorer.Bind(wx.EVT_TREE_ITEM_ACTIVATED,   self.explorer.on_item_activated)
        self.explorer.Bind(wx.EVT_TREE_SEL_CHANGED,      self.explorer.on_item_sel_changed)
        self.explorer.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.explorer.on_item_right_click)
        self.explorer.Bind(wx.EVT_RIGHT_UP,              self.explorer.on_item_right_click)
        self.explorer.Bind(wx.EVT_RIGHT_DOWN,            self.explorer.on_item_right_down)

        # pida modules list ctrl.
        self.Bind(wx.EVT_BUTTON,                                self.pida_modules_list.on_add_module, self.add_module)
        self.pida_modules_list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.pida_modules_list.on_right_click)
        self.pida_modules_list.Bind(wx.EVT_RIGHT_UP,            self.pida_modules_list.on_right_click)
        self.pida_modules_list.Bind(wx.EVT_RIGHT_DOWN,          self.pida_modules_list.on_right_down)
        self.pida_modules_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.pida_modules_list.on_activated)

        self.msg("PaiMei Explorer")
        self.msg("Module by Pedram Amini\n")


    ####################################################################################################################
    def __set_properties (self):
        # set the max length to whatever the widget supports (typically 32k).
        self.log.SetMaxLength(0)

        # begin wxGlade: PAIMEIexplorer.__set_properties
        self.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.pida_modules_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.pida_modules_list.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.add_module.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.explorer.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.special.SetFont(wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Courier"))
        self.log.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        self.log_splitter.SetMinimumPaneSize(25)
        # end wxGlade


    ####################################################################################################################
    def __do_layout (self):
        # begin wxGlade: PAIMEIexplorer.__do_layout
        overall = wx.BoxSizer(wx.HORIZONTAL)
        log_window_sizer = wx.BoxSizer(wx.HORIZONTAL)
        columns = wx.BoxSizer(wx.HORIZONTAL)
        special_column = wx.StaticBoxSizer(self.special_column_staticbox, wx.VERTICAL)
        disassmbly_column = wx.StaticBoxSizer(self.disassmbly_column_staticbox, wx.VERTICAL)
        browser_column = wx.StaticBoxSizer(self.browser_column_staticbox, wx.VERTICAL)
        browser_column.Add(self.pida_modules_static, 0, wx.ADJUST_MINSIZE, 0)
        browser_column.Add(self.pida_modules_list, 1, wx.EXPAND, 0)
        browser_column.Add(self.add_module, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        browser_column.Add(self.explorer, 5, wx.EXPAND, 0)
        columns.Add(browser_column, 1, wx.EXPAND, 0)
        disassmbly_column.Add(self.disassembly, 1, wx.GROW, 0)
        columns.Add(disassmbly_column, 2, wx.EXPAND, 0)
        special_column.Add(self.special, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        columns.Add(special_column, 1, wx.EXPAND, 0)
        self.top_window.SetAutoLayout(True)
        self.top_window.SetSizer(columns)
        columns.Fit(self.top_window)
        columns.SetSizeHints(self.top_window)
        log_window_sizer.Add(self.log, 1, wx.EXPAND, 0)
        self.log_window.SetAutoLayout(True)
        self.log_window.SetSizer(log_window_sizer)
        log_window_sizer.Fit(self.log_window)
        log_window_sizer.SetSizeHints(self.log_window)
        self.log_splitter.SplitHorizontally(self.top_window, self.log_window)
        overall.Add(self.log_splitter, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        # end wxGlade


    ####################################################################################################################
    def OnMaxLogLengthReached (self, event):
        '''
        Clear the log window when the max length is reach.

        @todo: Make this smarter by maybe only clearing half the lines.
        '''

        self.log.SetValue("")


    ####################################################################################################################
    def err (self, message):
        '''
        Write an error message to log window.
        '''

        self.log.AppendText("[!] %s\n" % message)


    ####################################################################################################################
    def msg (self, message):
        '''
        Write a log message to log window.
        '''

        self.log.AppendText("[*] %s\n" % message)


    ####################################################################################################################
    def pida_copy (self, module_name):
        '''
        Load the specified module name from the pstalker module directly into the explorer tree control.

        @type  module_name: String
        @param module_name: Name of module to copy and load from pstalker module.
        '''

        other = self.main_frame.modules["pstalker"].pida_modules

        if not other.has_key(module_name):
            self.err("Specified module name %s, not found." % module_name)
            return

        self.pida_modules[module_name] = other[module_name]

        # determine the function and basic block counts for this module.
        function_count    = len(self.pida_modules[module_name].nodes)
        basic_block_count = 0

        for function in self.pida_modules[module_name].nodes.values():
            basic_block_count += len(function.nodes)

        idx = len(self.pida_modules) - 1
        self.pida_modules_list.InsertStringItem(idx, "")
        self.pida_modules_list.SetStringItem(idx, 0, "%d" % function_count)
        self.pida_modules_list.SetStringItem(idx, 1, "%d" % basic_block_count)
        self.pida_modules_list.SetStringItem(idx, 2, module_name)
########NEW FILE########
__FILENAME__ = PAIMEIextender
#
# Paimei Python Console Module
# Copyright (C) 2007 Cameron Hotchkies <chotchkies@tippingpoint.com>
#
# $Id: PAIMEIextender.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Cameron Hotchkies
@license:      GNU General Public License 2.0 or later
@contact:      chotchkies@tippingpoint.com
@organization: www.tippingpoint.com
'''

import wx.py as py
import wx

#######################################################################################################################
class PAIMEIextender(wx.Panel):

    crust = None
    
    def __init__(self, *args, **kwds):
        intro = 'PAIMEI Extender interactive shell. Based on wx.pycrust %s' % py.version.VERSION
    
        wx.Panel.__init__(self, *args, **kwds)
    
        overall_sizer = wx.BoxSizer(wx.HORIZONTAL)        
        
        self.crust = py.crust.Crust(self, intro=intro)
        
        overall_sizer.Add(self.crust, 1, wx.EXPAND, 0)
        
        self.SetSizer(overall_sizer)

    
########NEW FILE########
__FILENAME__ = PAIMEIfilefuzz
#
# Paimei File Fuzzing Module
# Copyright (C) 2006 Cody Pierce <cpierce@tippingpoint.com>
#
# $Id: PAIMEIfilefuzz.py 228 2007-10-22 20:14:10Z cody $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Cody Pierce
@license:      GNU General Public License 2.0 or later
@contact:      cpierce@tippingpoint.com
@organization: www.tippingpoint.com
'''

import sys, os, thread, time, datetime, copy, struct, smtplib, shutil
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

try:
    import win32api, win32con
    dynamic = True
except:
    dynamic = False
    
import wx
import wx.lib.filebrowsebutton as filebrowse
import wx.lib.newevent

import utils
from pydbg import *
from pydbg.defines import *

(ThreadEventUpdate, EVT_THREAD_UPDATE) = wx.lib.newevent.NewEvent()
(ThreadEventLog, EVT_THREAD_LOG) = wx.lib.newevent.NewEvent()
(ThreadEventEnd, EVT_THREAD_END) = wx.lib.newevent.NewEvent()

#import _PAIMEIfilefuzz

class TestCase:
    def __init__(self, main_window, program_name, timeout, file_list):
        self.main_window = main_window
        self.program_name = program_name
        self.program_type = ""
        self.program_cache = {}
        self.crash_dir = self.main_window.destination + '\\' + 'crashes'
        self.timeout = timeout
        self.file_list = file_list
        self.pydbg = ""
        self.stats = {}
        self.running = False
        self.paused = False
        self.current_pos = 0
        self.current_file = ""
        
        self.first_chance = self.main_window.first_chance
        self.show_window = self.main_window.show_window
        
        # Handles our email settings
        self.email_on = self.main_window.email_on
        self.email_to = self.main_window.email_to
        self.email_from = self.main_window.email_from
        self.email_server = self.main_window.email_server
        
    def Start(self):
        if not self.program_name and dynamic:
            evt = ThreadEventLog(msg = "Trying to dynamically do program launching")
            wx.PostEvent(self.main_window, evt)
            
            self.program_type = "Dynamic"
        else:
            self.program_type = "Static"
        
        self.running = True
               
        try:
            thread.start_new_thread(self.Run, ())
        except:
            evt = ThreadEventLog(msg = "Problem Starting Thread")
            wx.PostEvent(self.main_window, evt)
            self.End(-1)
    
    def Pause(self):
        self.paused = True
    
    def UnPause(self):
        self.paused = False
                
    def Stop(self):
        self.running = False

    def End(self, rc):
        self.rc = rc
        
        try:
            self.pydbg.terminate_process()
        except:
            pass
                    
        evt = ThreadEventEnd()
        wx.PostEvent(self.main_window, evt)

        return self.rc

    def Run(self):
        self.stats["files_ran"] = self.main_window.files_ran
        self.stats["files_left"] = self.main_window.files_left
        self.stats["end_time"] = self.main_window.end_time
        self.stats["num_crashes"] = 0
        self.stats["num_read"] = 0
        self.stats["num_write"] = 0
        self.stats["last_crash_addr"] = 0x00000000
        
        for item in self.file_list:
            if not self.running:
                evt = ThreadEventLog(msg = "Fuzzer thread stopping")
                wx.PostEvent(self.main_window, evt)
                self.End(-1)
                break
            
            if self.paused:
                evt = ThreadEventLog(msg = "Fuzzer thread paused")
                wx.PostEvent(self.main_window, evt)    
                
                while self.paused:
                    time.sleep(1)
            
            for key in item.keys():
                dbg = pydbg()
                
                self.current_pos = key
                self.current_file = item[key]

                evt = ThreadEventUpdate(pos = self.current_pos, stats = self.stats)
                wx.PostEvent(self.main_window, evt)
                
                # Run pydbg shit
                dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, self.ExceptionHandler)
                dbg.set_callback(EXCEPTION_GUARD_PAGE, self.GuardHandler)

                if self.program_type == "Dynamic":
                    extension = "." + self.current_file.split(".")[-1]
                    
                    evt = ThreadEventLog(msg = "Checking extension %s" % extension)
                    wx.PostEvent(self.main_window, evt)
                    
                    if self.program_cache.has_key(extension):
                        command = self.program_cache[extension]
                    else:
                        command = self.get_handler(extension, self.current_file)
                        self.program_cache[extension] = command
                    
                    if not command:
                        evt = ThreadEventLog(msg = "Couldnt find proper handler.")
                        wx.PostEvent(self.main_window, evt)
                        
                        continue
                    else:
                        try:
                            dbg.load(command, "\"" + self.current_file + "\"", show_window=self.show_window)
                        except pdx, x:
                            evt = ThreadEventLog(msg = "Problem Starting Program (%s): %s %s" % (x. __str__(), self.program_name, self.current_file))
                            wx.PostEvent(self.main_window, evt)
                else:   
                    try:
                        dbg.load(self.program_name, "\"" + self.current_file + "\"", show_window=self.show_window)
                    except pdx, x:
                        evt = ThreadEventLog(msg = "Problem Starting Program (%s): %s %s" % (x. __str__(), self.program_name, self.current_file))
                        wx.PostEvent(self.main_window, evt)
                    
                # Create watchdog thread
                try:
                    thread.start_new_thread(self.Watch, (dbg, self.current_file))
                except:
                    evt = ThreadEventLog(msg = "Problem Starting Thread")
                    wx.PostEvent(self.main_window, evt)
                    self.End(-1)
                
                #Continue execution
                try:
                    dbg.debug_event_loop()
                except pdx, x:
                    evt = ThreadEventLog(msg = "Problem in debug_Event_loop() (%s): %s %s" % (x.__str__(), self.program_name, self.current_file))
                    wx.PostEvent(self.main_window, evt)

                self.stats["files_ran"] += 1
                self.stats["files_left"] -= 1
                self.stats["end_time"] -= self.timeout
        
        # Finished fuzz run
        evt = ThreadEventUpdate(pos = key, stats = self.stats)
        wx.PostEvent(self.main_window, evt)

        evt = ThreadEventLog(msg = "Finished fuzzing!")
        wx.PostEvent(self.main_window, evt)
        
        self.main_window.msgbox("Finished fuzzing!")
        
        evt = ThreadEventLog(msg = "=" * 85)
        wx.PostEvent(self.main_window, evt)
        
        self.End(0)
        
    def Watch(self, pydbg, current_file):
        time.sleep(self.timeout)
        
        if pydbg.debugger_active:
	        try:
	            pydbg.terminate_process()
	        except pdx, x:
	            evt = ThreadEventLog(msg = "Couldnt Terminate Process (%s): %s %s" % (x.__str__(), self.program_name, current_file))
	            wx.PostEvent(self.main_window, evt)
	            
	            return 1
	        
	        return DBG_CONTINUE

    def GuardHandler(self, pydbg):
        evt = ThreadEventLog(msg = "[!] Guard page hit @ 0x%08x" % (pydbg.exception_address))
        wx.PostEvent(self.main_window, evt)
        
        return DBG_EXCEPTION_NOT_HANDLED
    
    def ExceptionHandler(self, pydbg):
        if pydbg.dbg.u.Exception.dwFirstChance and not self.first_chance:
            evt = ThreadEventLog(msg = "!!! Passing on first chance exception (%d) !!!" % pydbg.dbg.u.Exception.dwFirstChance)
            wx.PostEvent(self.main_window, evt)
            return DBG_EXCEPTION_NOT_HANDLED
        
        exception_address = pydbg.exception_address
        write_violation   = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionInformation[0]
        violation_address = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionInformation[1]
        
        crash_bin = utils.crash_binning.crash_binning()
        crash_bin.record_crash(pydbg)

        # Lets move the file to our crashes directory
        if not os.path.isdir(self.crash_dir):
            try:
                os.mkdir(self.crash_dir)
            except:
                evt = ThreadEventLog(msg = "Could not create crash directory")
                wx.PostEvent(self.main_window, evt)
        
        try:
            shutil.copyfile(self.main_window.destination + '\\' + self.current_file, self.crash_dir + "\\" + self.current_file)
        except:
            evt = ThreadEventLog(msg = "Could not copy %s to %s" % (self.main_window.destination + '\\' + self.current_file, self.crash_dir + "\\" + self.current_file))
            wx.PostEvent(self.main_window, evt)
                
        logmessage = "\n\n[!] %s caused an access violation\n" % self.current_file
        logmessage += crash_bin.crash_synopsis()
        
        self.stats["num_crashes"] += 1
        self.stats["last_crash_addr"] = "%08x" % pydbg.dbg.u.Exception.ExceptionRecord.ExceptionAddress
        
        if write_violation:
            self.stats["num_write"] += 1
        else:
            self.stats["num_read"] += 1
           
        evt = ThreadEventLog(msg = logmessage)
        wx.PostEvent(self.main_window, evt)
        time.sleep(self.timeout)
        
        evt = ThreadEventUpdate(pos = self.current_pos, stats = self.stats)
        wx.PostEvent(self.main_window, evt)
        
        if self.email_on:
            self.mail_exception(logmessage)
        
        try:
            pydbg.terminate_process()
        except pdx, x:
            evt = ThreadEventLog(msg = "Couldnt Terminate Process (%s): %s %s" % (x.__str__(), self.program_name, self.current_file))
            wx.PostEvent(self.main_window, evt)
        
        return DBG_CONTINUE

    def mail_exception(self, message):
        msg = MIMEMultipart()
        msg.attach(MIMEText(message))
        
        msg["Subject"] = "PAIMEI File Fuzz %s" % (self.current_file)
        msg["From"]    = self.email_from
        msg["To"]      = self.email_to
        msg["Date"]    = formatdate(localtime=True)
        
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(self.current_file,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                       % os.path.basename(self.current_file))
        msg.attach(part)
        
        s = smtplib.SMTP()
        s.connect(self.email_server, 25)
        s.sendmail(self.email_from, self.email_to, msg.as_string())
        s.close()
        
        
    def get_handler(self, extension, current_file):
        handler = ""
        
        key = win32api.RegOpenKey(win32con.HKEY_CLASSES_ROOT, "%s" % extension)
        
        try:
            (handler, junk) = win32api.RegQueryValueEx(key, "")
        except:
            return ""
        
        command = ""
        
        try:
            key = win32api.RegOpenKey(win32con.HKEY_CLASSES_ROOT, "%s\\shell\\open\\command" % handler)
        except:
            return ""
        
        try:
            (command, junk) = win32api.RegQueryValueEx(key, "")
        except:
            return ""
        
        # This needs to be enhanced
        newcommand = command.rsplit(" ", 1)[0]
        
        return newcommand
        
#######################################################################################################################
class PAIMEIfilefuzz(wx.Panel):
    
    running              = False
    paused               = False
    first_chance         = True
    show_window          = True
    
    file_list_pos        = 0
    byte_length          = 0
    files_ran            = 0
    files_left           = 0
    num_crashes          = 0
    percent_crashes      = 0
    most_hit_addr        = 0x00000000
    most_hit_crashes     = 0
    last_crash_addr      = 0x00000000
    num_read             = 0
    num_write            = 0
    start_time           = 0
    running_time         = "00:00:00"
    end_time             = "00:00:00"
    logfile              = ""

    # This handles the setup of the email
    email_on             = True
    email_from           = "tsrt@tippingpoint.com"
    email_to             = "fuzz.results@gmail.com"
    email_server         = "usut001.3com.com"
    
    def __init__(self, *args, **kwds):
        # begin wxGlade: PAIMEIfilefuzz.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        
        self.list_book  = kwds["parent"]             # handle to list book.
        self.pydbg = copy.copy(self.list_book.top.pydbg)      # handle to top most frame.
        
        self.main_splitter = wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_BORDER)
        
        self.log_window_pane = wx.Panel(self.main_splitter, -1)
        self.main_window_pane = wx.Panel(self.main_splitter, -1)
        
        self.setup_sizer_staticbox = wx.StaticBox(self.main_window_pane, -1, "Setup")
        self.setup_right_staticbox = wx.StaticBox(self.main_window_pane, -1, "Byte Modifications")

        self.file_inspector_staticbox = wx.StaticBox(self.main_window_pane, -1, "File Inspector")
        
        self.progress_sizer_staticbox = wx.StaticBox(self.main_window_pane, -1, "Progress")
        self.statistics_sizer_staticbox = wx.StaticBox(self.main_window_pane, -1, "Statistics")
        self.fuzz_sizer_staticbox = wx.StaticBox(self.main_window_pane, -1, "Fuzz")
        
        self.program_name_label = wx.StaticText(self.main_window_pane, -1, "Program Name")
        self.program_name_control = filebrowse.FileBrowseButtonWithHistory(self.main_window_pane, -1, size=(500, -1), labelText = "")
        self.program_name_control.SetHistory([])
        
        self.source_name_label = wx.StaticText(self.main_window_pane, -1, "Source File Name")
        self.source_name_control = filebrowse.FileBrowseButtonWithHistory(self.main_window_pane, -1, size=(500, -1), labelText = "")
        self.source_name_control.SetHistory([])
        
        self.destination_label = wx.StaticText(self.main_window_pane, -1, "Destination Directory")
        self.destination_control = filebrowse.DirBrowseButton(self.main_window_pane, -1, size=(500, -1), labelText = "")
        
        self.hex_label = wx.StaticText(self.main_window_pane, -1, "Hex Bytes")
        self.hex_control = wx.TextCtrl(self.main_window_pane, -1, "")
        
        self.start_label = wx.StaticText(self.main_window_pane, -1, "Range Start")
        self.start_control = wx.TextCtrl(self.main_window_pane, -1, "")
        self.start_control.SetMaxLength(7)
        
        self.end_label = wx.StaticText(self.main_window_pane, -1, "Range End")
        self.end_control = wx.TextCtrl(self.main_window_pane, -1, "")
        self.end_control.SetMaxLength(7)
        
        self.timeout_label = wx.StaticText(self.main_window_pane, -1, "Timeout (secs)")
        self.timer_control = wx.TextCtrl(self.main_window_pane, -1, "")
        self.timer_control.SetMaxLength(7)
        
        self.file_view_control = wx.TextCtrl(self.main_window_pane, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        
        self.file_list_box_control = wx.ListBox(self.main_window_pane, -1, choices=[], style=wx.LB_SINGLE)
        self.file_list_refresh_button = wx.Button(self.main_window_pane, -1, "Refresh List")
        
        self.generate_button_control = wx.Button(self.main_window_pane, -1, "Generate")
        self.run_button_control = wx.Button(self.main_window_pane, -1, "Run")
        self.stop_button_control = wx.Button(self.main_window_pane, -1, "Stop")
        
        self.stat_crashes_label = wx.StaticText(self.main_window_pane, -1, "# Crashes:")
        self.stat_crashes = wx.StaticText(self.main_window_pane, -1, "0 / 0%", style=wx.ALIGN_RIGHT)
        self.stat_num_read_label = wx.StaticText(self.main_window_pane, -1, "# Read Violations:")
        self.stat_num_read = wx.StaticText(self.main_window_pane, -1, "0 / 0%", style=wx.ALIGN_RIGHT)
        self.stat_num_write_label = wx.StaticText(self.main_window_pane, -1, "# Write Violations:")
        self.stat_num_write = wx.StaticText(self.main_window_pane, -1, "0 / 0%", style=wx.ALIGN_RIGHT)
        self.stat_running_time_label = wx.StaticText(self.main_window_pane, -1, "Running Time:")
        self.stat_running_time = wx.StaticText(self.main_window_pane, -1, "00:00:00", style=wx.ALIGN_RIGHT)
        self.stat_end_eta_label = wx.StaticText(self.main_window_pane, -1, "Estimated Completion:")
        self.stat_end_eta = wx.StaticText(self.main_window_pane, -1, "00:00:00", style=wx.ALIGN_RIGHT)
        self.stat_last_violaton_label = wx.StaticText(self.main_window_pane, -1, "Last Violation Address:")
        self.stat_last_violation = wx.StaticText(self.main_window_pane, -1, "N/A", style=wx.ALIGN_RIGHT)
        
        self.progress_text_label = wx.StaticText(self.main_window_pane, -1, "File 0 / 0")
        self.progress_gauge_control = wx.Gauge(self.main_window_pane, -1, 100, style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        
        self.log = wx.TextCtrl(self.log_window_pane, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)

        self.__set_properties()
        self.__do_layout()

        #self.Bind(wx.EVT_BUTTON, self.OnHistory, self.history_button_control)
        #self.Bind(wx.EVT_BUTTON, self.OnSave, self.save_button_control)
        #self.Bind(wx.EVT_BUTTON, self.OnLoad, self.Load)
        self.Bind(wx.EVT_LISTBOX, self.OnFileList, self.file_list_box_control)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, self.file_list_refresh_button)
        self.Bind(wx.EVT_BUTTON, self.OnGenerate, self.generate_button_control)
        self.Bind(wx.EVT_BUTTON, self.OnRun, self.run_button_control)
        self.Bind(wx.EVT_BUTTON, self.OnStop, self.stop_button_control)
        
        # Thread events
        self.Bind(EVT_THREAD_UPDATE, self.OnThreadUpdate)
        self.Bind(EVT_THREAD_LOG, self.OnThreadLog)
        self.Bind(EVT_THREAD_END, self.OnThreadEnd)

        self.msg("PaiMei File Fuzz")
        self.msg("Module by Cody Pierce\n")

    def __set_properties(self):
        self.hex_control.SetMinSize((50, -1))
        self.hex_control.SetToolTipString("Byte to use in test case")
        self.start_control.SetMinSize((75, -1))
        self.start_control.SetToolTipString("Start byte location in test case")
        self.end_control.SetMinSize((75, -1))
        self.end_control.SetToolTipString("End byte location of test case")
        self.timer_control.SetMinSize((75, -1))
        self.timer_control.SetToolTipString("Number of seconds to wait before killing program")
        
        self.file_view_control.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Terminal"))
        self.file_view_control.SetToolTipString("Hex dump of file")
        
        self.generate_button_control.SetToolTipString("Generate test cases based on options")
        self.run_button_control.SetToolTipString("Run the test cases in destination directory")
        self.stop_button_control.SetToolTipString("Stop running test cases")

        self.log.SetToolTipString("Log window of file fuzzer")
        self.log.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))

    def __do_layout(self):
        overall_sizer = wx.BoxSizer(wx.HORIZONTAL)
        log_window_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_window_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        fuzz_sizer = wx.StaticBoxSizer(self.fuzz_sizer_staticbox, wx.VERTICAL)
        statistics_sizer = wx.StaticBoxSizer(self.statistics_sizer_staticbox, wx.HORIZONTAL)
        statistics_grid_sizer = wx.GridSizer(6, 2, 0, 0)
        setup_sizer = wx.StaticBoxSizer(self.setup_sizer_staticbox, wx.VERTICAL)
        progress_sizer = wx.StaticBoxSizer(self.progress_sizer_staticbox, wx.VERTICAL)
        
        file_inspector = wx.StaticBoxSizer(self.file_inspector_staticbox, wx.HORIZONTAL)
        
        setup_columns = wx.BoxSizer(wx.HORIZONTAL)
        setup_right = wx.StaticBoxSizer(self.setup_right_staticbox, wx.VERTICAL)
        setup_left = wx.BoxSizer(wx.VERTICAL)
        setup_left.Add(self.program_name_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_left.Add(self.program_name_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_left.Add(self.source_name_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_left.Add(self.source_name_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_left.Add(self.destination_label, 0, wx.ADJUST_MINSIZE, 0)
        setup_left.Add(self.destination_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_columns.Add(setup_left, 3, wx.EXPAND, 0)
        setup_right.Add(self.hex_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.hex_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.start_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.start_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.end_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.end_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.timeout_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_right.Add(self.timer_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_columns.Add(setup_right, 1, wx.EXPAND, 0)
        setup_sizer.Add(setup_columns, 1, wx.EXPAND, 0)
        file_inspector.Add(self.file_view_control, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_sizer.Add(file_inspector, 2, wx.EXPAND, 0)
        progress_sizer.Add(self.progress_text_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        progress_sizer.Add(self.progress_gauge_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        setup_sizer.Add(progress_sizer, 0, wx.EXPAND, 0)
        main_window_sizer.Add(setup_sizer, 2, wx.EXPAND, 0)
        fuzz_sizer.Add(self.file_list_box_control, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        fuzz_sizer.Add(self.file_list_refresh_button, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        fuzz_sizer.Add(self.generate_button_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        fuzz_sizer.Add(self.run_button_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        fuzz_sizer.Add(self.stop_button_control, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_crashes_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_crashes, 0, wx.EXPAND|wx.ALIGN_RIGHT|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_num_read_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_num_read, 0, wx.EXPAND|wx.ALIGN_RIGHT|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_num_write_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_num_write, 0, wx.EXPAND|wx.ALIGN_RIGHT|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_running_time_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_running_time, 0, wx.EXPAND|wx.ALIGN_RIGHT|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_end_eta_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_end_eta, 0, wx.EXPAND|wx.ALIGN_RIGHT|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_last_violaton_label, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        statistics_grid_sizer.Add(self.stat_last_violation, 0, wx.EXPAND|wx.ALIGN_RIGHT|wx.ADJUST_MINSIZE, 0)
        statistics_sizer.Add(statistics_grid_sizer, 1, wx.EXPAND, 0)
        fuzz_sizer.Add(statistics_sizer, 1, wx.EXPAND, 0)
        main_window_sizer.Add(fuzz_sizer, 1, wx.EXPAND, 0)
        self.main_window_pane.SetAutoLayout(True)
        self.main_window_pane.SetSizer(main_window_sizer)
        main_window_sizer.Fit(self.main_window_pane)
        main_window_sizer.SetSizeHints(self.main_window_pane)
        log_window_sizer.Add(self.log, 1, wx.EXPAND, 0)
        self.log_window_pane.SetAutoLayout(True)
        self.log_window_pane.SetSizer(log_window_sizer)
        log_window_sizer.Fit(self.log_window_pane)
        log_window_sizer.SetSizeHints(self.log_window_pane)
        self.main_splitter.SplitHorizontally(self.main_window_pane, self.log_window_pane)
        overall_sizer.Add(self.main_splitter, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall_sizer)
        overall_sizer.Fit(self)
        overall_sizer.SetSizeHints(self)
        
        self.Layout()

    def OnStop(self, event):
        if self.running:
            self.running = False
            self.test_case_thread.Stop()
        else:
            event.Skip()
            
    def OnFileList(self, event):
        self.get_file_view()
        
    def OnRefresh(self, event):
        if self.running:
            return -1
            
        if self.destination_control.GetValue() == "":
            self.msgbox("Directory is not set")
            return -1
            
        self.destination = self.destination_control.GetValue()
        if not os.path.isdir(self.destination):
            self.msgbox("Destination directory does not exist")
            return -1
        
        while self.file_list_box_control.GetCount() > 0:
            self.file_list_box_control.Delete(0)

        filenames = os.listdir(self.destination)
        filenames.sort(cmp=self.numerifile)
        
        for file in filenames:
            self.file_list_box_control.Append(self.destination + "\\" + file)
        
        self.file_list_pos = self.file_list_box_control.GetCount() - 1
        
    def OnGenerate(self, event):
        if self.running:
            return -1

        if self.source_name_control.GetValue() == "" or self.destination_control.GetValue() == "" or self.hex_control.GetValue() == "":
           self.msgbox("Please enter all data!")
           return -1
           
        self.source_name = self.source_name_control.GetValue()
        if not os.path.isfile(self.source_name):
            self.msgbox("Source file does not exist")
            return -1
        
        # We store new history for control
        history = self.source_name_control.GetHistory()
        history.append(self.source_name)
        self.source_name_control.SetHistory(history)
        
        self.destination = self.destination_control.GetValue()
        if not os.path.isdir(self.destination):
            self.msgbox("Destination directory does not exist")
            return -1
            
        self.byte = self.hex_control.GetValue()
        
        if self.start_control.GetValue() == "":
            self.start = 0
        else:
            self.start = int(self.start_control.GetValue())
            
        if self.end_control.GetValue() == "":
            self.end = os.path.getsize(self.source_name)
        else:
            self.end = int(self.end_control.GetValue())
            
        if self.start > self.end:
            self.msgbox("Please make start < end jerk")
            return(-1)
        
        while self.file_list_box_control.GetCount() > 0:
            self.file_list_box_control.Delete(0)
            
        self.generate_files(self.source_name, self.destination, self.byte, self.start, self.end)

    def OnRun(self, event):
        if self.running and not self.paused:
            self.paused = True
            self.test_case_thread.Pause()
            self.run_button_control.SetLabel("UnPause")
            return -1
        elif self.running and self.paused:
            self.paused = False
            self.test_case_thread.UnPause()
            self.run_button_control.SetLabel("Pause")
            return -1
        
        if self.program_name_control.GetValue() == "" and not dynamic:
            self.msgbox("Please enter program name")
            return(-1)
            
        if self.timer_control.GetValue() == "" or self.timer_control.GetValue() <= 0:
            self.msgbox("Please enter all data!")
            return(-1)
         
        if self.file_list_pos < 0:
            self.msgbox("Nothing in file list")
            return(-1)
        
        self.running = True
        self.paused = False
        
        self.program_name = self.program_name_control.GetValue()
        
        # We store new history for control
        history = self.program_name_control.GetHistory()
        history.append(self.program_name)
        self.program_name_control.SetHistory(history)
        
        self.timeout = int(self.timer_control.GetValue())
        
        # This should be an option, but since we are moving to the new ui i wont waste my time
        if not self.logfile:
            self.logfile = open(self.destination + "\\" + "filefuzz.log", "a")
            
        self.msg("================================ %s ================================" % self.format_date())
        
        if self.start_control.GetValue() == "":
            self.start = 0
        else:
            self.start = int(self.start_control.GetValue())
            
        if self.end_control.GetValue() == "":
            self.end = self.file_list_pos + 1
        else:
            self.end = int(self.end_control.GetValue())
            
        if self.start > self.end:
            self.msgbox("Please make start < end jerk")
            return(-1)

        self.file_list = []
        
        #for count in xrange(self.start, self.end, 1):
        for count in range(self.file_list_box_control.GetCount()):
            testcase = {}
            testcase[count] = self.file_list_box_control.GetString(count)
            self.file_list.append(testcase)

        # Update stats
        self.files_ran = self.start
        self.files_left = self.end

        self.start_time = int(time.time())
        self.end_time = (self.end - self.start) * self.timeout

        self.update_stats()
        
        # Update gauge
        self.progress_text_label.SetLabel("File: %d / %d" % (self.start, self.end))
        
        self.test_case_thread = TestCase(self, self.program_name, self.timeout, self.file_list)
        self.test_case_thread.Start()
        self.run_button_control.SetLabel("Pause")
        self.msg("Started fuzz thread")
        
    def OnHistory(self, event):
        if self.running:
            return -1
            
        self.msg("Event handler `OnHistory' not implemented")
        event.Skip()

    def OnSave(self, event):
        if self.running:
            return -1
            
        self.msg("Event handler `OnSave' not implemented")
        event.Skip()

    def OnLoad(self, event):
        if self.running:
            return -1
            
        self.msg("Event handler `OnLoad' not implemented")
        event.Skip()
                
    def OnThreadUpdate(self, event):
        self.file_list_box_control.SetSelection(event.pos)
        self.get_file_view()
        
        # Update Stats
        self.files_ran = event.stats["files_ran"]
        self.files_left = event.stats["files_left"]
        self.num_crashes = event.stats["num_crashes"]
        self.num_read = event.stats["num_read"]
        self.num_write = event.stats["num_write"]
        self.end_time = event.stats["end_time"]
        self.last_crash_addr = event.stats["last_crash_addr"]
        
        self.update_stats()
        
        # Update Gauge
        self.progress_text_label.SetLabel("File: %d / %d" % (self.files_ran, self.end))
        self.progress_gauge_control.SetValue(int((float(self.files_ran) / float(self.end)) * 100))
        
    def OnThreadLog(self, event):
        self.msg(event.msg)
    
    def OnThreadEnd(self, event):
        self.running = False
        self.paused = False
        self.run_button_control.SetLabel("Run")
        self.msg("Thread has ended!")
            
    ####################################################################################################################
    def err (self, message):
        '''
        Write an error message to log window.
        '''

        self.log.AppendText("[!] %s\n" % message)


    ####################################################################################################################
    def msg (self, message):
        '''
        Write a log message to log window.
        '''

        if self.logfile:
            self.logfile.write("[*] %s\n" % message)
            self.logfile.flush()
        
        self.log.AppendText("[*] %s\n" % message)
    
    def msgbox(self, message):
        dlg = wx.MessageDialog(self, message,
                               '',
                               wx.OK | wx.ICON_INFORMATION
                               #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                               )
        dlg.ShowModal()
        dlg.Destroy()
        
    def update_stats(self):
        # Update stats
        
        # Crash shit
        self.stat_crashes.SetLabel("%-d / %-d%%" % (self.num_crashes, int((float(self.num_crashes) / float(self.end)) * 100)))
        self.stat_num_read.SetLabel("%d / %d%%" % (self.num_read, int((float(self.num_read) / float(self.end)) * 100)))
        self.stat_num_write.SetLabel("%d / %d%%" % (self.num_write, int((float(self.num_write) / float(self.end)) * 100)))
        self.stat_last_violation.SetLabel("0x%s" % self.last_crash_addr)
        
        # Time shit
        self.stat_running_time.SetLabel("%s" % self.seconds_strtime(int(time.time()) - self.start_time))
        self.stat_end_eta.SetLabel("%s" % self.seconds_strtime(self.end_time))

    def generate_files(self, source_name, destination, outbyte, start, end):
        '''
        Generates the test cases
        '''
        self.byte_length, rem = divmod(len(outbyte) - 2, 2)
        if rem:
            self.byte_length += 1
        
        current_file = 1
        
        # Update gauge
        self.progress_text_label.SetLabel("File: %d / %d" % (current_file, ((end - start) / self.byte_length) + 1))
        
        # Get progress bar range
        self.progress_gauge_control.SetValue(0)
        
        extension = source_name.split(".")[-1]
        infile = open(source_name, 'rb')
        
        contents = infile.read()
        
        for byte in xrange(start, end+1, self.byte_length):
            newcontents = ""
            
            newfile = str(byte) + "." + extension
            
            # Set the current file
            self.progress_text_label.SetLabel("File: %d / %d" % (current_file, ((end - start) / self.byte_length) + 1))
            
            # Open new file
            outfile = open(destination + "\\" + newfile, 'wb')
            
            # Write up to byte
            newcontents = contents[0:byte]
            # Write byte/s
            if self.byte_length <= 1:
                newcontents += struct.pack(">B", int(outbyte, 16))
            elif self.byte_length <= 2:
                newcontents += struct.pack(">H", int(outbyte, 16))
            elif self.byte_length <= 4:
                newcontents += struct.pack(">L", int(outbyte, 16))
            elif self.byte_length <= 8:
                newcontents += struct.pack(">Q", int(outbyte, 16))
            
            # Write from byte on
            newcontents += contents[byte+self.byte_length:]
            
            outfile.write(newcontents)
            outfile.close
            
            self.file_list_box_control.Append(destination + "\\" + newfile)
            self.progress_gauge_control.SetValue(int((float(current_file) / float(((end - start) / self.byte_length) + 1)) * 100))
            current_file += 1
                
        self.file_list_pos = self.file_list_box_control.GetCount() - 1
            
            
        infile.close()
        
        self.msg("File Generation Completed Successfully!")
            
    def run_fuzz(self, start, end):
        
        # Set static stats
        self.start_time = int(time.time())
        self.end_time = (end - start) * self.timeout
        for count in xrange(start, end, 1):    
       
            self.file_list_box_control.SetSelection(count)
            self.get_file_view()
            self.current_file_name = self.file_list_box_control.GetStringSelection()
            
            # Update gauge
            self.progress_text_label.SetLabel("File: %d / %d" % (count, self.file_list_pos))
            
            # Update stats
            self.stat_files_ran.SetLabel("%d" % count)
            self.stat_files_left.SetLabel("%d" % ((self.file_list_pos) - count))
            self.stat_running_time.SetLabel(self.seconds_strtime(int(time.time()) - self.start_time))
            self.stat_end_eta.SetLabel(self.seconds_strtime((end - count) * self.timeout))
            
            # Create thread
            test_case_thread = TestCase(self)
            test_case_thread.Start()
            test_case_thread.Join(self.timeout)

            wx.Yield()

            # Update gauge
            self.progress_gauge_control.SetValue(int((float(count) / float(self.file_list_pos)) * 100))
            
        # Update final gauges
        self.progress_text_label.SetLabel("File: %d / %d" % (0, 0))
        self.stat_running_time.SetLabel(self.seconds_strtime(int(time.time()) - self.start_time))
        self.stat_end_eta.SetLabel("00:00:00")
        self.progress_gauge_control.SetValue(0)
        
    def get_file_view(self):
        fullpath = self.file_list_box_control.GetStringSelection()

        if not os.path.isfile(fullpath):
            self.msg("File is not a file!")
            return -1
        
        try:
            filehandle = open(fullpath, 'rb')
        except:
            self.msg("Couldnt open %s" % fullpath)
            return -1
        
        try:
            filecontents = filehandle.read()
        except:
            self.msg("Couldnt read %s" % fullpath)
            
            filehandle.close()
            
            return -1
        
        try:    
            filehandle.close()
        except:
            self.msg("Couldnt close %s" % fullpath)
            return -1
        
        try:
            filename = os.path.basename(fullpath)
            filesize = os.path.getsize(fullpath)
            filebyte = int(filename.split(".")[0])
        except:
            self.msg("Error getting file stats!")
            return -1
        
        if filebyte < 256:
            start = 0
        else:
            start = filebyte - 256
        
        while start % 16 != 0:
            start -= 1
            
        if filebyte > filesize - 256:
            end = filesize
        else:
            end = filebyte + 256
        
        # Clear control
        self.file_view_control.Clear()
        
        counter = 0
        bytepos = 0
        length  = 0
        
        for filepos in xrange(start, end, 1):
            byte = filecontents[filepos]

            if counter == 0:
                self.file_view_control.AppendText("0x%08x: " % filepos,)
                counter += 1
            
            if filepos == filebyte or length > 0:
                bytepos = self.file_view_control.GetInsertionPoint()
                self.file_view_control.SetStyle(bytepos, bytepos, wx.TextAttr("RED", "WHITE"))
                
                if length != 0:
                    length = length - 1
                else:
                    length = self.byte_length - 1
            elif byte == "\x00":
                self.file_view_control.SetStyle(self.file_view_control.GetInsertionPoint(), self.file_view_control.GetInsertionPoint(), wx.TextAttr("GREY", "WHITE"))
            else:
                #self.file_view_control.SetStyle(-1, -1, self.file_view_control.GetDefaultStyle())
                self.file_view_control.SetStyle(-1, -1, wx.TextAttr("BLACK", "WHITE"))
                 
            if counter < 16:
                self.file_view_control.AppendText("0x%02x " % ord(byte),)
                counter += 1
            else:
                self.file_view_control.AppendText("0x%02x\n" % ord(byte))
                counter = 0

        self.file_view_control.ShowPosition(bytepos)
    
    def format_date(self):
        return time.strftime("%m/%d/%Y %H:%M:%S", time.gmtime())
        
    def seconds_strtime(self, seconds):
        hour = seconds / 3600   
        minutes = (seconds - (hour * 3600)) / 60
        seconds = (seconds - (hour * 3600) - (minutes * 60))

        return "%02d:%02d:%02d" % (hour, minutes, seconds)           
    
    def numerifile(self, x, y):
        try:
            x = int(x[:x.rfind(".")]) 
            y = int(y[:y.rfind(".")]) 
        except:
            return 1
            
        if   x  < y: return -1
        elif x == y: return 0
        else:        return 1
########NEW FILE########
__FILENAME__ = PAIMEIpeek
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PAIMEIpeek.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import sys
import MySQLdb
import time

import _PAIMEIpeek

from pydbg import *
from pydbg.defines import *

import utils

########################################################################################################################
class PAIMEIpeek(wx.Panel):
    '''
    The Process Peeker module panel.
    '''

    documented_properties = {
        "boron_tag"  : "Optional string to search context dumps for and alarm the user if found.",
        "log_file"   : "Optional filename to save a copy of all log output to.",
        "module"     : "MySQLdb object for currently selection module.",
        "quiet"      : "Boolean flag controlling whether or not to log context dumps during run-time.",
        "track_recv" : "Boolean flag controlling whether or not to capture and log recv() / recvfrom() data.",
        "watch"      : "Instead of attaching to or loading a target process, this option allows you to specify a process name to continuously watch for and attach to as soon as it is spawned. The process name is case insensitive, but you *must* specify the full name and extension. Example: winmine.exe",
    }

    boron_tag  = ""
    log_file   = ""
    module     = None
    quiet      = False
    track_recv = True
    watch      = None

    # attach target.
    pid    = proc = load = None
    detach = False

    def __init__(self, *args, **kwds):
        # begin wxGlade: PAIMEIpeek.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.log_splitter                  = wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_BORDER)
        self.log_window                    = wx.Panel(self.log_splitter, -1)
        self.top_window                    = wx.Panel(self.log_splitter, -1)
        self.hit_list_column_staticbox     = wx.StaticBox(self.top_window, -1, "Hits")
        self.peek_data_container_staticbox = wx.StaticBox(self.top_window, -1, "Peek Point Data")
        self.recon_column_staticbox        = wx.StaticBox(self.top_window, -1, "RECON")
        self.select_module                 = wx.Button(self.top_window, -1, "Select Module")
        self.add_recon_point               = wx.Button(self.top_window, -1, "Add RECON Point")
        self.set_options                   = wx.Button(self.top_window, -1, "Options")
        self.attach_detach                 = wx.Button(self.top_window, -1, "Peek!")
        self.recon                         = _PAIMEIpeek.ReconListCtrl.ReconListCtrl(self.top_window, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_HRULES|wx.SUNKEN_BORDER, top=self)
        self.hit_list                      = wx.ListBox(self.top_window, -1, choices=[])
        self.peek_data                     = wx.TextCtrl(self.top_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)
        self.log                           = wx.TextCtrl(self.log_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)
        self.percent_analyzed_static       = wx.StaticText(self.top_window, -1, "RECON Points Reviewed:")
        self.percent_analyzed              = wx.Gauge(self.top_window, -1, 100, style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.list_book  = kwds["parent"]             # handle to list book.
        self.main_frame = self.list_book.top         # handle to top most frame.

        # move the log splitter sash down.
        self.log_splitter.SetSashPosition(-200, redraw=True)

        # log window bindings.
        self.Bind(wx.EVT_TEXT_MAXLEN, self.on_log_max_length_reached, self.log)

        # hide the ID and depth columns (oh yeah, very ollydbg-ish).
        self.recon.SetColumnWidth(0, 0)
        self.recon.SetColumnWidth(2, 0)

        # button bindings
        self.Bind(wx.EVT_BUTTON, self.on_button_select_module,   self.select_module)
        self.Bind(wx.EVT_BUTTON, self.on_button_add_recon_point, self.add_recon_point)
        self.Bind(wx.EVT_BUTTON, self.on_button_set_options,     self.set_options)
        self.Bind(wx.EVT_BUTTON, self.on_button_attach_detach,   self.attach_detach)

        # list box bindings.
        self.Bind(wx.EVT_LISTBOX, self.on_hit_list_select, self.hit_list)

        # recon list control bindings.
        self.recon.Bind(wx.EVT_LIST_ITEM_SELECTED,  self.recon.on_select)
        self.recon.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.recon.on_right_click)
        self.recon.Bind(wx.EVT_RIGHT_UP,            self.recon.on_right_click)
        self.recon.Bind(wx.EVT_RIGHT_DOWN,          self.recon.on_right_down)
        self.recon.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.recon.on_activated)

        self.msg("PaiMei Peeker")
        self.msg("Module by Pedram Amini\n")


    ####################################################################################################################
    def __set_properties(self):
        # begin wxGlade: PAIMEIpeek.__set_properties
        self.select_module.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.add_recon_point.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.set_options.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.attach_detach.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.recon.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.peek_data.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        self.log.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        self.percent_analyzed_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.percent_analyzed.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        # end wxGlade


    ####################################################################################################################
    def __do_layout(self):
        # begin wxGlade: PAIMEIpeek.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        log_window_sizer = wx.BoxSizer(wx.HORIZONTAL)
        columns = wx.BoxSizer(wx.HORIZONTAL)
        peek_data_container = wx.StaticBoxSizer(self.peek_data_container_staticbox, wx.HORIZONTAL)
        hit_list_column = wx.StaticBoxSizer(self.hit_list_column_staticbox, wx.HORIZONTAL)
        recon_column = wx.StaticBoxSizer(self.recon_column_staticbox, wx.VERTICAL)
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.Add(self.select_module, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        button_row.Add(self.add_recon_point, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        button_row.Add(self.set_options, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        button_row.Add(self.attach_detach, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        recon_column.Add(button_row, 0, wx.EXPAND, 0)
        recon_column.Add(self.recon, 1, wx.EXPAND, 0)
        recon_column.Add(self.percent_analyzed_static, 0, wx.EXPAND, 0)
        recon_column.Add(self.percent_analyzed, 0, wx.EXPAND, 0)
        columns.Add(recon_column, 1, wx.EXPAND, 0)
        hit_list_column.Add(self.hit_list, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        columns.Add(hit_list_column, 0, wx.EXPAND, 0)
        peek_data_container.Add(self.peek_data, 1, wx.EXPAND, 0)
        columns.Add(peek_data_container, 1, wx.EXPAND, 0)
        self.top_window.SetAutoLayout(True)
        self.top_window.SetSizer(columns)
        columns.Fit(self.top_window)
        columns.SetSizeHints(self.top_window)
        log_window_sizer.Add(self.log, 1, wx.EXPAND, 0)
        self.log_window.SetAutoLayout(True)
        self.log_window.SetSizer(log_window_sizer)
        log_window_sizer.Fit(self.log_window)
        log_window_sizer.SetSizeHints(self.log_window)
        self.log_splitter.SplitHorizontally(self.top_window, self.log_window)
        overall.Add(self.log_splitter, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        # end wxGlade


    ####################################################################################################################
    def err (self, message):
        '''
        Write an error message to log window.
        '''

        self.log.AppendText("[!] %s\n" % message)


    ####################################################################################################################
    def msg (self, message):
        '''
        Write a log message to log window.
        '''

        self.log.AppendText("[*] %s\n" % message)

        # if a log file was specified, write the message to it as well.
        if self.log_file:
            try:
                fh = open(self.log_file, "a+")
                fh.write(message + "\n")
                fh.close()
            except:
                self.err("Failed writing to log file '%s'. Closing log." % self.log_file)
                self.log_file = None


    ####################################################################################################################
    def handler_access_violation (self, dbg):
        '''
        '''

        crash_bin = utils.crash_binning()
        crash_bin.record_crash(dbg)

        self.msg(crash_bin.crash_synopsis())
        dbg.terminate_process()


    ####################################################################################################################
    def handler_breakpoint (self, dbg):
        '''
        On the first breakpoint set all the other breakpoints on the recon points. If track_recg is enabled then
        establish hooks on the winsock functions. On subsequent breakpoints, record them appropriately.
        '''

        #
        # first breakpoint, set hooks and breakpoints on recon points.
        #

        if dbg.first_breakpoint:
            if self.track_recv:
                self.hooks = utils.hook_container()

                # ESP                 +4         +8       +C        +10
                # int recv     (SOCKET s, char *buf, int len, int flags)
                # int recvfrom (SOCKET s, char *buf, int len, int flags, struct sockaddr *from, int *fromlen)
                # we want these:                ^^^      ^^^

                try:
                    ws2_recv = dbg.func_resolve("ws2_32",  "recv")
                    self.hooks.add(dbg, ws2_recv, 4, None, self.socket_logger_ws2_recv)
                except:
                    pass

                try:
                    ws2_recvfrom = dbg.func_resolve("ws2_32",  "recvfrom")
                    self.hooks.add(dbg, ws2_recvfrom, 4, None, self.socket_logger_ws2_recvfrom)
                except:
                    pass

                try:
                    wsock_recv = dbg.func_resolve("wsock32", "recv")
                    self.hooks.add(dbg, wsock_recv, 4, None, self.socket_logger_wsock_recv)
                except:
                    pass

                try:
                    wsock_recvfrom = dbg.func_resolve("wsock32", "recvfrom")
                    self.hooks.add(dbg, wsock_recvfrom, 4, None, self.socket_logger_wsock_recvfrom)
                except:
                    pass

            # retrieve list of recon points.
            cursor = self.main_frame.mysql.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT id, offset, stack_depth FROM pp_recon WHERE module_id = '%d'" % self.module["id"])

            # create a mapping of addresses to recon MySQL objects.
            self.addr_to_recon = {}
            for row in cursor.fetchall():
                self.addr_to_recon[self.module["base"] + row["offset"]] = row

            # set breakpoints at each recon point.
            self.dbg.bp_set(self.addr_to_recon.keys())
            self.msg("Watching %d points" % len(self.addr_to_recon))

            # close the MySQL cursor and continue execution.
            cursor.close()
            return DBG_CONTINUE

        #
        # subsequent breakpoints are recon hits ... export to db.
        #

        # grab the current context.
        context_dump = dbg.dump_context(stack_depth=self.addr_to_recon[dbg.context.Eip]["stack_depth"], print_dots=False)

        # display the context if the 'quiet' option is not enabled.
        if not self.quiet:
            self.msg(context_dump)

        # no boron tag match by default.
        boron_found = ""

        # if it was specified, search for the boron tag in the current context.
        if self.boron_tag:
            if context_dump.lower().find(self.boron_tag.lower()) != -1:
                boron_found = self.boron_tag

                # update the boron tag field of the pp_recon table to reflect that a hit was made.
                cursor = self.main_frame.mysql.cursor()
                cursor.execute("UPDATE pp_recon SET boron_tag='%s' WHERE id='%d'" % (boron_found, self.addr_to_recon[dbg.context.Eip]["id"]))
                cursor.close()

                if not self.quiet:
                    self.msg(">>>>>>>>>>>>>>>>>>>> BORON TAG FOUND IN ABOVE CONTEXT DUMP <<<<<<<<<<<<<<<<<<<<")


        # retrieve the context list with 'hex_dump' enabled to store in the database.
        context_list = dbg.dump_context_list(stack_depth=4, hex_dump=True)

        sql  = " INSERT INTO pp_hits"
        sql += " SET recon_id     = '%d'," % self.addr_to_recon[dbg.context.Eip]["id"]
        sql += "     module_id    = '%d'," % self.module["id"]
        sql += "     timestamp    = '%d'," % int(time.time())
        sql += "     tid          = '%d'," % dbg.dbg.dwThreadId
        sql += "     eax          = '%d'," % dbg.context.Eax
        sql += "     ebx          = '%d'," % dbg.context.Ebx
        sql += "     ecx          = '%d'," % dbg.context.Ecx
        sql += "     edx          = '%d'," % dbg.context.Edx
        sql += "     edi          = '%d'," % dbg.context.Edi
        sql += "     esi          = '%d'," % dbg.context.Esi
        sql += "     ebp          = '%d'," % dbg.context.Ebp
        sql += "     esp          = '%d'," % dbg.context.Esp
        sql += "     esp_4        = '%d'," % context_list["esp+04"]["value"]
        sql += "     esp_8        = '%d'," % context_list["esp+08"]["value"]
        sql += "     esp_c        = '%d'," % context_list["esp+0c"]["value"]
        sql += "     esp_10       = '%d'," % context_list["esp+10"]["value"]
        sql += "     eax_deref    = '%s'," % context_list["eax"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     ebx_deref    = '%s'," % context_list["ebx"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     ecx_deref    = '%s'," % context_list["ecx"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     edx_deref    = '%s'," % context_list["edx"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     edi_deref    = '%s'," % context_list["edi"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     esi_deref    = '%s'," % context_list["esi"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     ebp_deref    = '%s'," % context_list["ebp"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     esp_deref    = '%s'," % context_list["esp"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     esp_4_deref  = '%s'," % context_list["esp+04"]["desc"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     esp_8_deref  = '%s'," % context_list["esp+08"]["desc"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     esp_c_deref  = '%s'," % context_list["esp+0c"]["desc"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     esp_10_deref = '%s'," % context_list["esp+10"]["desc"].replace("\\", "\\\\").replace("'", "\\'")
        sql += "     boron_tag    = '%s'," % boron_found
        sql += "     base         = '%d' " % self.module["base"]

        cursor = self.main_frame.mysql.cursor()
        cursor.execute(sql)
        cursor.close()

        return DBG_CONTINUE


    ####################################################################################################################
    def handler_user_callback (self, dbg):
        '''
        '''

        # we try/except this as sometimes there is a recursion error that we don't care about.
        try:    wx.Yield()
        except: pass

        if self.detach:
            self.detach = False
            self.dbg.detach()

    ####################################################################################################################
    def on_button_add_recon_point (self, event):
        # a console-wide username must be specified for this action.
        if not self.main_frame.username:
            self.err("You must tell PaiMei who you are to continue with this action.")
            return

        # can't do anything if a module isn't loaded.
        if not self.module:
            self.err("You must load a module first.")
            return

        dlg = _PAIMEIpeek.AddReconDlg.AddReconDlg(parent=self)
        dlg.ShowModal()


    ####################################################################################################################
    def on_button_attach_detach (self, event):
        '''
        Present a dialog box with process list / load controls and begin monitoring the selected target.
        '''

        #
        # if we are already peeking and this button was hit, then step peeking and return.
        #

        if self.attach_detach.GetLabel() == "Stop":
            self.detach = True
            self.attach_detach.SetLabel("Peek!")

            # refresh the list.
            self.recon.load(self.module["id"])
            return

        #
        # it's peeking time.
        #

        # can't do anything if a module isn't loaded.
        if not self.module:
            self.err("You must load a module first.")
            return

        dlg = _PAIMEIpeek.PyDbgDlg.PyDbgDlg(parent=self)

        if dlg.ShowModal() != wx.ID_CANCEL:
            # create a new debugger instance..
            if hasattr(self.main_frame.pydbg, "port"):
                self.dbg = pydbg_client(self.main_frame.pydbg.host, self.main_frame.pydbg.port)
            else:
                self.dbg = pydbg()

            self.dbg.set_callback(EXCEPTION_BREAKPOINT,       self.handler_breakpoint)
            self.dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, self.handler_access_violation)
            self.dbg.set_callback(USER_CALLBACK_DEBUG_EVENT,  self.handler_user_callback)

            if self.load:
                self.dbg.load(self.load)
            else:
                self.dbg.attach(self.pid)

            self.attach_detach.SetLabel("Stop")
            self.dbg.run()


    ####################################################################################################################
    def on_button_select_module (self, event):
        '''
        Utilize the MySQL connection to retrieve the list of available modules from pp_modules.
        '''

        mysql = self.main_frame.mysql

        if not mysql:
            self.err("No available connection to MySQL server.")
            return

        busy = wx.BusyInfo("Loading... please wait.")
        wx.Yield()

        # step through the hits for this tag id.
        hits = mysql.cursor(MySQLdb.cursors.DictCursor)
        hits.execute("SELECT id, name FROM pp_modules ORDER BY name ASC")

        choices = {}
        for hit in hits.fetchall():
            choices[hit["name"]] = hit["id"]

        dlg = wx.SingleChoiceDialog(self, "", "Select Module", choices.keys(), wx.CHOICEDLG_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetStringSelection()
            id   = choices[name]

            self.msg("Loading %s" % name)
            self.recon.load(id)

        dlg.Destroy()


    ####################################################################################################################
    def on_button_set_options (self, event):
        '''
        Instantiate a dialog that will bubble set options back into our class vars.
        '''

        dlg = _PAIMEIpeek.PeekOptionsDlg.PeekOptionsDlg(parent=self)
        dlg.ShowModal()


    ####################################################################################################################
    def on_hit_list_select (self, event, id=None):
        '''
        A line item in the hit list control was selected, load the details for the hit.
        '''

        if not id:
            hit_id = event.GetClientData()
        else:
            hit_id = id

        cursor = self.main_frame.mysql.cursor(MySQLdb.cursors.DictCursor)

        try:
            cursor.execute("SELECT * FROM pp_hits WHERE id = '%d'" % hit_id)
            hit = cursor.fetchone()
        except:
            self.err("MySQL query failed.")
            return

        separator = "-" * 72

        context_dump  = "ID: %04x\n" % hit["id"]

        if hit["boron_tag"]:
            context_dump += ">>>>>>>>>> BORON TAG HIT: %s\n" % hit["boron_tag"]

        context_dump += "\n"
        context_dump += "%s\nEAX: %08x (%10d)\n%s\n\n" % (separator, hit["eax"], hit["eax"], hit["eax_deref"])
        context_dump += "%s\nEBX: %08x (%10d)\n%s\n\n" % (separator, hit["ebx"], hit["ebx"], hit["ebx_deref"])
        context_dump += "%s\nECX: %08x (%10d)\n%s\n\n" % (separator, hit["ecx"], hit["ecx"], hit["ecx_deref"])
        context_dump += "%s\nEDX: %08x (%10d)\n%s\n\n" % (separator, hit["edx"], hit["edx"], hit["edx_deref"])
        context_dump += "%s\nEDI: %08x (%10d)\n%s\n\n" % (separator, hit["edi"], hit["edi"], hit["edi_deref"])
        context_dump += "%s\nESI: %08x (%10d)\n%s\n\n" % (separator, hit["esi"], hit["esi"], hit["esi_deref"])
        context_dump += "%s\nEBP: %08x (%10d)\n%s\n\n" % (separator, hit["ebp"], hit["ebp"], hit["ebp_deref"])
        context_dump += "%s\nESP: %08x (%10d)\n%s\n\n" % (separator, hit["esp"], hit["esp"], hit["esp_deref"])

        context_dump += "%s\nESP +04: %08x (%10d)\n%s\n\n" % (separator, hit["esp_4"],  hit["esp_4"],  hit["esp_4_deref"])
        context_dump += "%s\nESP +08: %08x (%10d)\n%s\n\n" % (separator, hit["esp_8"],  hit["esp_8"],  hit["esp_8_deref"])
        context_dump += "%s\nESP +0C: %08x (%10d)\n%s\n\n" % (separator, hit["esp_c"],  hit["esp_c"],  hit["esp_c_deref"])
        context_dump += "%s\nESP +10: %08x (%10d)\n%s\n\n" % (separator, hit["esp_10"], hit["esp_10"], hit["esp_10_deref"])

        self.peek_data.SetValue(context_dump)


    ####################################################################################################################
    def on_log_max_length_reached (self, event):
        '''
        Clear the log window when the max length is reach.

        @todo: Make this smarter by maybe only clearing half the lines.
        '''

        self.log.SetValue("")


    ####################################################################################################################
    def socket_logger_ws2_recv (self, dbg, args, ret):
        '''
        Hook container call back.
        '''

        self.msg("ws2_32.recv(buf=%08x, len=%d)" % (args[1], args[2]))
        self.msg("Actually received %d bytes:" % ret)
        self.msg(dbg.hex_dump(dbg.read(args[1], ret)))


    ####################################################################################################################
    def socket_logger_ws2_recvfrom (self, dbg, args, ret):
        '''
        Hook container call back.
        '''

        self.msg("ws2_32.recvfrom(buf=%08x, len=%d)" % (args[1], args[2]))
        self.msg("Actually received %d bytes:" % ret)
        self.msg(dbg.hex_dump(dbg.read(args[1], ret)))


    ####################################################################################################################
    def socket_logger_wsock_recv (self, dbg, args, ret):
        '''
        Hook container call back.
        '''

        self.msg("wsock32.recv(buf=%08x, len=%d)" % (args[1], args[2]))
        self.msg("Actually received %d bytes:" % ret)
        self.msg(dbg.hex_dump(dbg.read(args[1], ret)))


    ####################################################################################################################
    def socket_logger_wsock_recvfrom (self, dbg, args, ret):
        '''
        Hook container call back.
        '''

        self.msg("wsock32.recvfrom(buf=%08x, len=%d)" % (args[1], args[2]))
        self.msg("Actually received %d bytes:" % ret)
        self.msg(dbg.hex_dump(dbg.read(args[1], ret)))
########NEW FILE########
__FILENAME__ = PAIMEIpstalker
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PAIMEIpstalker.py 241 2010-04-05 20:45:22Z rgovostes $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.lib.filebrowsebutton as filebrowse
import sys

import _PAIMEIpstalker

########################################################################################################################
class PAIMEIpstalker(wx.Panel):
    '''
    The Process Stalker module panel.
    '''

    documented_properties = {
        "pida_modules"          : "Dictionary of loaded PIDA modules.",
        "filter_list"           : "List of (target, tag ID) tuples to filter from stalk.",
        "stalk_tag"             : "ID of tag to use for stalk.",
        "function_count"        : "Total number of loaded functions.",
        "basic_block_count"     : "Total number of loaded basic blocks.",
        "hit_function_count"    : "Total number of hit functions.",
        "hit_basic_block_count" : "Total number of hit basic blocks.",
        "print_bps"             : "Boolean flag controlling whether or not to log individual breakpoints hits. This is an advanced option for which no GUI control exists. It is useful for removing the GUI latency in situations where stalking is producing a large volume of breakpoint hits.",
        "watch"                 : "Instead of attaching to or loading a target process, this option allows you to specify a process name to continuously watch for and attach to as soon as it is spawned. The process name is case insensitive, but you *must* specify the full name and extension. Example: winmine.exe",
    }

    list_book             = None        # handle to list book.
    main_frame            = None        # handle to top most frame.
    pida_modules          = {}          # dictionary of loaded PIDA modules.
    filter_list           = []          # list of (target, tag ID) tuples to filter from stalk.
    stalk_tag             = None        # ID of tag to use for stalk.
    function_count        = 0           # total number of loaded functions.
    basic_block_count     = 0           # total number of loaded basic blocks.
    hit_function_count    = 0           # total number of hit functions.
    hit_basic_block_count = 0           # total number of hit basic blocks.
    print_bps             = True        # flag controlling whether or not to log individual breakpoints hits.
    watch                 = None

    def __init__ (self, *args, **kwds):
        # begin wxGlade: PAIMEIpstalker.__init__
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        self.log_splitter                 = wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_BORDER)
        self.log_window                   = wx.Panel(self.log_splitter, -1)
        self.top_window                   = wx.Panel(self.log_splitter, -1)
        self.hits_column                  = wx.SplitterWindow(self.top_window, -1, style=wx.SP_3D|wx.SP_BORDER)
        self.hit_dereference              = wx.Panel(self.hits_column, -1)
        self.hit_list                     = wx.Panel(self.hits_column, -1)
        self.hit_list_container_staticbox = wx.StaticBox(self.hit_list, -1, "Data Exploration")
        self.log_container_staticbox      = wx.StaticBox(self.hit_dereference, -1, "Dereferenced Data")
        self.pydbg_column_staticbox       = wx.StaticBox(self.top_window, -1, "Data Capture")
        self.targets_column_staticbox     = wx.StaticBox(self.top_window, -1, "Data Sources")
        self.retrieve_targets             = wx.Button(self.top_window, -1, "Refresh Target List")
        self.targets                      = _PAIMEIpstalker.TargetsTreeCtrl.TargetsTreeCtrl(self.top_window, -1, top=self, style=wx.TR_HAS_BUTTONS|wx.TR_LINES_AT_ROOT|wx.TR_DEFAULT_STYLE|wx.SUNKEN_BORDER)
        self.pida_modules_static          = wx.StaticText(self.top_window, -1, "PIDA Modules")
        self.pida_modules_list            = _PAIMEIpstalker.PIDAModulesListCtrl.PIDAModulesListCtrl(self.top_window, -1, top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
        self.add_module                   = wx.Button(self.top_window, -1, "Add Module(s)")
        self.hits                         = _PAIMEIpstalker.HitsListCtrl.HitsListCtrl(self.hit_list, -1, top=self, style=wx.LC_REPORT|wx.LC_HRULES|wx.SUNKEN_BORDER)
        self.coverage_functions_static    = wx.StaticText(self.hit_list, -1, "Functions:")
        self.coverage_functions           = wx.Gauge(self.hit_list, -1, 100, style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        self.basic_blocks_coverage_static = wx.StaticText(self.hit_list, -1, "Basic Blocks:")
        self.coverage_basic_blocks        = wx.Gauge(self.hit_list, -1, 100, style=wx.GA_HORIZONTAL|wx.GA_SMOOTH)
        self.hit_details                  = wx.TextCtrl(self.hit_dereference, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.retrieve_list                = wx.Button(self.top_window, -1, "Refresh Process List")
        self.process_list                 = _PAIMEIpstalker.ProcessListCtrl.ProcessListCtrl(self.top_window, -1, top=self, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
        self.load_target                  = filebrowse.FileBrowseButton(self.top_window, -1, labelText="Load: ", fileMask="*.exe", fileMode=wx.OPEN, toolTip="Specify the target executable to load")
        self.coverage_depth               = wx.RadioBox(self.top_window, -1, "Coverage Depth", choices=["Functions", "Basic Blocks"], majorDimension=0, style=wx.RA_SPECIFY_ROWS)
        self.restore_breakpoints          = wx.CheckBox(self.top_window, -1, "Restore BPs")
        self.heavy                        = wx.CheckBox(self.top_window, -1, "Heavy")
        self.ignore_first_chance          = wx.CheckBox(self.top_window, -1, "Unhandled Only")
        self.attach_detach                = wx.Button(self.top_window, -1, "Start Stalking")
        self.log                          = wx.TextCtrl(self.log_window, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_LINEWRAP)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.list_book  = kwds["parent"]             # handle to list book.
        self.main_frame = self.list_book.top         # handle to top most frame.

        # default status message.
        self.status_msg = "Process Stalker"

        # log window bindings.
        self.Bind(wx.EVT_TEXT_MAXLEN, self.OnMaxLogLengthReached, self.log)

        # targets / tags tree ctrl.
        self.Bind(wx.EVT_BUTTON,                        self.targets.on_retrieve_targets, self.retrieve_targets)
        self.targets.Bind(wx.EVT_TREE_ITEM_ACTIVATED,   self.targets.on_target_activated)
        self.targets.Bind(wx.EVT_TREE_SEL_CHANGED,      self.targets.on_target_sel_changed)
        self.targets.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.targets.on_target_right_click)
        self.targets.Bind(wx.EVT_RIGHT_UP,              self.targets.on_target_right_click)
        self.targets.Bind(wx.EVT_RIGHT_DOWN,            self.targets.on_target_right_down)

        # pida modules list ctrl.
        self.Bind(wx.EVT_BUTTON,                                self.pida_modules_list.on_add_module, self.add_module)
        self.pida_modules_list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.pida_modules_list.on_right_click)
        self.pida_modules_list.Bind(wx.EVT_RIGHT_UP,            self.pida_modules_list.on_right_click)
        self.pida_modules_list.Bind(wx.EVT_RIGHT_DOWN,          self.pida_modules_list.on_right_down)

        # hit list ctrl.
        self.hits.Bind(wx.EVT_LIST_ITEM_SELECTED, self.hits.on_select)

        # process list ctrl.
        self.Bind(wx.EVT_BUTTON, self.process_list.on_retrieve_list,  self.retrieve_list)
        self.Bind(wx.EVT_BUTTON, self.process_list.on_attach_detach,  self.attach_detach)
        self.process_list.Bind(wx.EVT_LIST_ITEM_SELECTED,             self.process_list.on_select)

        # unselect targets
        self.targets.UnselectAll()

        self.msg("PaiMei Process Stalker")
        self.msg("Module by Pedram Amini\n")


    ####################################################################################################################
    def __set_properties (self):
        # set the max length to whatever the widget supports (typically 32k).
        self.log.SetMaxLength(0)

        # begin wxGlade: PAIMEIpstalker.__set_properties
        self.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        self.retrieve_targets.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.targets.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.pida_modules_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.pida_modules_list.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.add_module.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.hits.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.coverage_functions_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.coverage_functions.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.basic_blocks_coverage_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.coverage_basic_blocks.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.hit_details.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "Courier"))
        self.hits_column.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.retrieve_list.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.process_list.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.load_target.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.coverage_depth.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.coverage_depth.SetSelection(0)
        self.restore_breakpoints.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.heavy.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.heavy.SetValue(1)
        self.ignore_first_chance.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.ignore_first_chance.SetValue(1)
        self.attach_detach.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.top_window.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.log.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        self.log_splitter.SetMinimumPaneSize(25)
        # end wxGlade


    ####################################################################################################################
    def __do_layout (self):
        # begin wxGlade: PAIMEIpstalker.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        log_window_sizer = wx.BoxSizer(wx.HORIZONTAL)
        columns = wx.BoxSizer(wx.HORIZONTAL)
        pydbg_column = wx.StaticBoxSizer(self.pydbg_column_staticbox, wx.VERTICAL)
        stalk_options = wx.BoxSizer(wx.HORIZONTAL)
        log_container = wx.StaticBoxSizer(self.log_container_staticbox, wx.HORIZONTAL)
        hit_list_container = wx.StaticBoxSizer(self.hit_list_container_staticbox, wx.VERTICAL)
        percent_coverage = wx.BoxSizer(wx.HORIZONTAL)
        basic_blocks_block = wx.BoxSizer(wx.VERTICAL)
        functions_block = wx.BoxSizer(wx.VERTICAL)
        targets_column = wx.StaticBoxSizer(self.targets_column_staticbox, wx.VERTICAL)
        targets_column.Add(self.retrieve_targets, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        targets_column.Add(self.targets, 4, wx.EXPAND, 0)
        targets_column.Add(self.pida_modules_static, 0, wx.ADJUST_MINSIZE, 0)
        targets_column.Add(self.pida_modules_list, 2, wx.EXPAND, 0)
        targets_column.Add(self.add_module, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        columns.Add(targets_column, 1, wx.EXPAND, 0)
        hit_list_container.Add(self.hits, 3, wx.EXPAND, 0)
        functions_block.Add(self.coverage_functions_static, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        functions_block.Add(self.coverage_functions, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        percent_coverage.Add(functions_block, 1, wx.EXPAND, 0)
        percent_coverage.Add((50, 20), 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        basic_blocks_block.Add(self.basic_blocks_coverage_static, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        basic_blocks_block.Add(self.coverage_basic_blocks, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        percent_coverage.Add(basic_blocks_block, 1, wx.EXPAND, 0)
        hit_list_container.Add(percent_coverage, 0, wx.EXPAND, 0)
        self.hit_list.SetAutoLayout(True)
        self.hit_list.SetSizer(hit_list_container)
        hit_list_container.Fit(self.hit_list)
        hit_list_container.SetSizeHints(self.hit_list)
        log_container.Add(self.hit_details, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.hit_dereference.SetAutoLayout(True)
        self.hit_dereference.SetSizer(log_container)
        log_container.Fit(self.hit_dereference)
        log_container.SetSizeHints(self.hit_dereference)
        self.hits_column.SplitHorizontally(self.hit_list, self.hit_dereference)
        columns.Add(self.hits_column, 2, wx.EXPAND, 0)
        pydbg_column.Add(self.retrieve_list, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        pydbg_column.Add(self.process_list, 5, wx.EXPAND, 0)
        pydbg_column.Add(self.load_target, 0, wx.EXPAND, 0)
        pydbg_column.Add(self.coverage_depth, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        stalk_options.Add(self.restore_breakpoints, wx.EXPAND, wx.ADJUST_MINSIZE, 0)
        stalk_options.Add(self.heavy, wx.EXPAND, wx.ADJUST_MINSIZE, 0)
        stalk_options.Add(self.ignore_first_chance, wx.EXPAND, wx.ADJUST_MINSIZE, 0)
        pydbg_column.Add((5, 10), 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        pydbg_column.Add(stalk_options, 0, wx.EXPAND, 0)
        pydbg_column.Add((5, 10), 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        pydbg_column.Add(self.attach_detach, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        columns.Add(pydbg_column, 1, wx.EXPAND, 0)
        self.top_window.SetAutoLayout(True)
        self.top_window.SetSizer(columns)
        columns.Fit(self.top_window)
        columns.SetSizeHints(self.top_window)
        log_window_sizer.Add(self.log, 1, wx.EXPAND, 0)
        self.log_window.SetAutoLayout(True)
        self.log_window.SetSizer(log_window_sizer)
        log_window_sizer.Fit(self.log_window)
        log_window_sizer.SetSizeHints(self.log_window)
        self.log_splitter.SplitHorizontally(self.top_window, self.log_window)
        overall.Add(self.log_splitter, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        # end wxGlade


    ####################################################################################################################
    def _get_status (self):
        '''
        Return the text to display in the status bar on page change.
        '''

        return self.status_msg


    ####################################################################################################################
    def _set_status (self, status_msg):
        '''
        Set the text to display in the status bar.
        '''

        self.status_msg = status_msg
        self.main_frame.status_bar.SetStatusText(self.status_msg, 1)


    ####################################################################################################################
    def OnMaxLogLengthReached (self, event):
        '''
        Clear the log window when the max length is reach.

        @todo: Make this smarter by maybe only clearing half the lines.
        '''

        self.log.SetValue("")


    ####################################################################################################################
    def err (self, message):
        '''
        Write an error message to log window.
        '''

        self.log.AppendText("[!] %s\n" % message)


    ####################################################################################################################
    def msg (self, message):
        '''
        Write a log message to log window.
        '''

        self.log.AppendText("[*] %s\n" % message)


    ####################################################################################################################
    def update_gauges (self):
        '''
        '''

        self.coverage_functions_static.SetLabel("Functions: %d / %d" % (self.hit_function_count, self.function_count))
        self.basic_blocks_coverage_static.SetLabel("Basic Blocks: %d / %d" % (self.hit_basic_block_count, self.basic_block_count))

        msg = ""

        if self.function_count:
            percent = int((float(self.hit_function_count) / float(self.function_count)) * 100)
            msg += "Function coverage at %d%%. " % percent
        else:
            percent = 0

        self.coverage_functions.SetValue(percent)

        if self.basic_block_count:
            percent = int((float(self.hit_basic_block_count) / float(self.basic_block_count)) * 100)
            msg += "Basic block coverage at %d%%." % percent
        else:
            percent = 0

        if msg:
            self.msg(msg)

        self.coverage_basic_blocks.SetValue(percent)

########NEW FILE########
__FILENAME__ = DiffConfigureDlg
#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# generated by wxGlade 0.4.1 on Fri Sep 08 21:01:42 2006
#
# $Id: DiffConfigureDlg.py 194 2007-04-05 15:31:53Z cameron $
#

import wx
import os
import re
import sys
import InsignificantConfigDlg


FUNCTION_LEVEL    = 0x0001
BASIC_BLOCK_LEVEL = 0x0002

alpha = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']

class DiffConfigureDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: DiffConfigureDlg.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.sizer_6_staticbox = wx.StaticBox(self, -1, "Configuration Options")
        self.label_1 = wx.StaticText(self, -1, "Supported Function Matching Algorithms:")
        self.FunctionMatchListCtrl = wx.ListBox(self, -1, choices=[])
        self.label_3 = wx.StaticText(self, -1, "Supported Basic Block Matching Algorithms:")
        self.BasicBlockMatchListCtrl = wx.ListBox(self, -1, choices=[])
        self.label_5 = wx.StaticText(self, -1, "Supported Function Diffing Algorithms:")
        self.FunctionDiffListCtrl = wx.ListBox(self, -1, choices=[])
        self.ImportButton = wx.Button(self, -1, "Import")
        self.ExportButton = wx.Button(self, -1, "Export")
        self.InsignificantCheckBox = wx.CheckBox(self, -1, "Use Insignificant Settings")
        self.MatchCheckBox = wx.CheckBox(self, -1, "Match Until No Change")
        self.DefineButton = wx.Button(self, -1, "Define Insignificant Settings")
        self.DoneButton = wx.Button(self, -1, "Done")
        self.CancelButton = wx.Button(self, -1, "Cancel")
        self.label_2 = wx.StaticText(self, -1, "Currently Used Function Matching Algorithms:")
        self.UsedFunctionMatchListCtrl = wx.ListBox(self, -1, choices=[])
        self.label_4 = wx.StaticText(self, -1, "Currently Used Basic Block Matching Algorithms:")
        self.UsedBasicBlockMatchListCtrl = wx.ListBox(self, -1, choices=[])
        self.label_6 = wx.StaticText(self, -1, "Currently Used Function Diffing Algorithms:")
        self.UsedFunctionDiffListCtrl = wx.ListBox(self, -1, choices=[])

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        
        self.parent = kwds["parent"]
  
  
        #fill out the list boxes
        self.MatchCheckBox.SetValue( self.parent.loop_until_change)
        self.InsignificantCheckBox.SetValue(self.parent.ignore_insignificant)
  
        i = 0        
        for method in self.parent.module_table.values():
            if method.attributes["Level"] & FUNCTION_LEVEL and method.attributes["Match"]:
                self.FunctionMatchListCtrl.Insert(method.module_name, i)
                i+=1
            
        i = 0        
        for method in self.parent.module_table.values():
            if method.attributes["Level"] & BASIC_BLOCK_LEVEL and method.attributes["Match"]:
                self.BasicBlockMatchListCtrl.Insert(method.module_name, i)
                i+=1

        i = 0        
        for method in self.parent.module_table.values():
            if method.attributes["Level"] & FUNCTION_LEVEL and method.attributes["Diff"]:
                self.FunctionDiffListCtrl.Insert(method.module_name, i)
                i+=1
            

        
        
        
        
        
        try:
            i = 0        
            for method in sorted(self.parent.used_match_function_table.keys()):
                self.UsedFunctionMatchListCtrl.Insert(method[1:], i)
                i+=1
        except:
            pass
    
    
        try:
            i = 0        
            for method in sorted(self.parent.used_match_basic_block_table.keys()):
                self.UsedBasicBlockMatchListCtrl.Insert(method[1:], i)
                i+=1
        except:
            pass
    
        try:
            i = 0        
            for method in sorted(self.parent.used_diff_function_table.keys()):
                self.UsedFunctionDiffListCtrl.Insert(method[1:], i)
                i+=1
        except:
            pass

                    
       
                
                
        #setup our event handlers
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_function_match_dbl_clk,                self.FunctionMatchListCtrl)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_basic_block_match_dbl_clk,             self.BasicBlockMatchListCtrl)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_function_diff_dbl_clk,                 self.FunctionDiffListCtrl)
       
       
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_function_used_match_dbl_clk,                self.UsedFunctionMatchListCtrl)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_basic_block_used_match_dbl_clk,             self.UsedBasicBlockMatchListCtrl)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_function_used_diff_dbl_clk,                 self.UsedFunctionDiffListCtrl)

        self.Bind(wx.EVT_BUTTON,         self.on_done,                          self.DoneButton)
        self.Bind(wx.EVT_BUTTON,         self.on_cancel,                        self.CancelButton)
        self.Bind(wx.EVT_BUTTON,         self.on_insignificant_config,          self.DefineButton)
        self.Bind(wx.EVT_BUTTON,         self.on_export,                        self.ExportButton)
        self.Bind(wx.EVT_BUTTON,         self.on_import,                        self.ImportButton)       



    def __set_properties(self):
        # begin wxGlade: DiffConfigureDlg.__set_properties
        self.SetTitle("Configure PAIMEIDiff")
        self.label_1.SetBackgroundColour(wx.Colour(236, 233, 216))
        self.label_3.SetBackgroundColour(wx.Colour(236, 233, 216))
        self.label_5.SetBackgroundColour(wx.Colour(236, 233, 216))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: DiffConfigureDlg.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5 = wx.BoxSizer(wx.VERTICAL)
        sizer_6 = wx.StaticBoxSizer(self.sizer_6_staticbox, wx.HORIZONTAL)
        sizer_7 = wx.BoxSizer(wx.VERTICAL)
        sizer_8 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_4.Add(self.label_1, 0, wx.ADJUST_MINSIZE, 0)
        sizer_4.Add(self.FunctionMatchListCtrl, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_4.Add(self.label_3, 0, wx.ADJUST_MINSIZE, 0)
        sizer_4.Add(self.BasicBlockMatchListCtrl, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_4.Add(self.label_5, 0, wx.ADJUST_MINSIZE, 0)
        sizer_4.Add(self.FunctionDiffListCtrl, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_3.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_7.Add(self.ImportButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7.Add(self.ExportButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7.Add(self.InsignificantCheckBox, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7.Add(self.MatchCheckBox, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7.Add(self.DefineButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_8.Add(self.DoneButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_8.Add(self.CancelButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7.Add(sizer_8, 1, wx.EXPAND, 0)
        sizer_6.Add(sizer_7, 1, wx.EXPAND, 0)
        sizer_3.Add(sizer_6, 1, wx.EXPAND, 0)
        sizer_5.Add(self.label_2, 0, wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.UsedFunctionMatchListCtrl, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.label_4, 0, wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.UsedBasicBlockMatchListCtrl, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.label_6, 0, wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.UsedFunctionDiffListCtrl, 2, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_3.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_3, 1, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 2, wx.ALL|wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        sizer_1.SetSizeHints(self)
        self.Layout()
        # end wxGlade



    def on_function_match_dbl_clk           (self, evt):   
        selected = self.FunctionMatchListCtrl.GetStringSelection()
        self.UsedFunctionMatchListCtrl.Insert(selected,self.UsedFunctionMatchListCtrl.GetCount())

    def on_basic_block_match_dbl_clk        (self, evt):
        selected = self.BasicBlockMatchListCtrl.GetStringSelection()
        self.UsedBasicBlockMatchListCtrl.Insert(selected,self.UsedBasicBlockMatchListCtrl.GetCount())
    
    def on_function_diff_dbl_clk            (self, evt):
        selected = self.FunctionDiffListCtrl.GetStringSelection()
        self.UsedFunctionDiffListCtrl.Insert(selected,self.UsedFunctionDiffListCtrl.GetCount())
    
    

    
    def on_function_used_match_dbl_clk      (self, evt):
        self.UsedFunctionMatchListCtrl.Delete( self.UsedFunctionMatchListCtrl.GetSelection() )
    
    def on_basic_block_used_match_dbl_clk   (self, evt):
        self.UsedBasicBlockMatchListCtrl.Delete( self.UsedBasicBlockMatchListCtrl.GetSelection() )

    
    def on_function_used_diff_dbl_clk       (self, evt):
        self.UsedFunctionDiffListCtrl.Delete( self.UsedFunctionDiffListCtrl.GetSelection() )

        

    ####################################################################################################################
    def on_done(self, event):
        
        
        if self.UsedFunctionMatchListCtrl.GetCount() == 0 and self.UsedBasicBlockMatchListCtrl.GetCount():
            self.parent.err("You need to select a method to be used in the matching phase.")
            return
        
        if self.UsedFunctionDiffListCtrl.GetCount() == 0 and self.UsedBasicBlockDiffListCtrl.GetCount():
            self.parent.err("You need to select a method to be used for in the diffing phase.")
            return
        
   
        i = 0
        num = self.UsedFunctionMatchListCtrl.GetCount()
        for i in xrange(num):
            try:
                self.parent.used_match_function_table[ alpha[i] + self.UsedFunctionMatchListCtrl.GetString(i) ] = self.parent.match_function_table[ self.UsedFunctionMatchListCtrl.GetString(i) ]
            except:
                self.parent.msg("Failed to find \'%s\' handler for function matching table" % self.UsedFunctionMatchListCtrl.GetString(i))
        
        i = 0
        num = self.UsedBasicBlockMatchListCtrl.GetCount()
        for i in xrange(num):
            try:
                self.parent.used_match_basic_block_table[ alpha[i] + self.UsedBasicBlockMatchListCtrl.GetString(i) ] = self.parent.match_basic_block_table[ self.UsedBasicBlockMatchListCtrl.GetString(i) ]
            except:
                self.parent.msg("Failed to find \'%s\' handler for basic block matching table" % self.UsedBasicBlockMatchListCtrl.GetString(i))
        
        
        i = 0
        num = self.UsedFunctionDiffListCtrl.GetCount()
        for i in xrange(num):
            try:
                self.parent.used_diff_function_table[ alpha[i] + self.UsedFunctionDiffListCtrl.GetString(i) ] = self.parent.diff_function_table[ self.UsedFunctionDiffListCtrl.GetString(i) ]
            except:
                self.parent.msg("Failed to find \'%s\' handler for function diff table" % self.UsedFunctionDiffListCtrl.GetString(i))
        
        
      
    
        self.parent.ignore_insignificant = self.InsignificantCheckBox.GetValue()
        self.parent.loop_until_change = self.MatchCheckBox.GetValue()
        self.Destroy()
        
    ####################################################################################################################
    def on_cancel(self, event):
        self.Destroy()
    
    
    ####################################################################################################################
    def on_insignificant_config(self, event):
        dlg = InsignificantConfigDlg.InsignificantConfigDlg(parent=self)
        dlg.ShowModal()    

    ####################################################################################################################
    def on_export(self, event):
        dlg = wx.FileDialog(                                    \
            self,                                               \
            message     = "Select where to save file",          \
            defaultDir  = os.getcwd(),                          \
            defaultFile = "",                                   \
            wildcard    = "*.dcfg",                             \
            style       = wx.SAVE | wx.CHANGE_DIR  \
        )
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = dlg.GetPath()
        dcfg_file = open(path,"w")
        i = 0
        num = self.UsedFunctionMatchListCtrl.GetCount()
        
        for i in xrange(num):
            dcfg_file.write("function_match_method=%s\n" % self.UsedFunctionMatchListCtrl.GetString(i))
        
        i = 0
        num = self.UsedBasicBlockMatchListCtrl.GetCount()
        for i in xrange(num):
            dcfg_file.write("bb_match_method=%s\n" % self.UsedBasicBlockMatchListCtrl.GetString(i))
                
        i = 0
        num = self.UsedFunctionDiffListCtrl.GetCount()
        for i in xrange(num):
            dcfg_file.write("function_diff_method=%s\n" % self.UsedFunctionDiffListCtrl.GetString(i))
        
   
                
            
        val = self.MatchCheckBox.GetValue()
        dcfg_file.write("NoChange=%d\n" % val)
        val = self.InsignificantCheckBox.GetValue()
        dcfg_file.write("IgnoreInsig=%d\n" % val)
        dcfg_file.write("InsigFunc=%d:%d:%d:%d\n" % self.parent.insignificant_function)
        dcfg_file.write("InsigBB=%d\n" % self.parent.insignificant_bb)
        dcfg_file.close()		
        
    ####################################################################################################################
    def on_import(self, event):
        dlg = wx.FileDialog(                                    \
            self,                                               \
            message     = "Select DCFG file",                   \
            defaultDir  = os.getcwd(),                          \
            defaultFile = "",                                   \
            wildcard    = "*.dcfg",                             \
            style       = wx.OPEN | wx.CHANGE_DIR               \
        )
        if dlg.ShowModal() != wx.ID_OK:
            return
        path = dlg.GetPath()
        dcfg_file = open(path, "r")
        for line in dcfg_file:
            line = line.upper().strip().replace(" ","")
            if line.find("FUNCTION_MATCH_METHOD") != -1:
                p = re.compile("FUNCTION_MATCH_METHOD=(\w+)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid method" % line)
                else:
                    for n in self.parent.match_function_table.keys():
                        if n.upper() == m.group(1):
                            self.UsedFunctionMatchListCtrl.Insert( n, self.UsedFunctionMatchListCtrl.GetCount())
            elif line.find("BB_MATCH_METHOD") != -1:
                p = re.compile("BB_MATCH_METHOD=(\w+)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid method" % line)
                else:
                    for n in self.parent.match_basic_block_table.keys():
                        if n.upper() == m.group(1):
                            self.UsedBasicBlockMatchListCtrl.Insert(n, self.UsedBasicBlockMatchListCtrl.GetCount())
            elif line.find("FUNCTION_DIFF_METHOD") != -1:
                p = re.compile("FUNCTION_DIFF_METHOD=(\w+)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid method" % line)
                else:
                    for n in self.parent.diff_function_table.keys():
                        if n.upper() == m.group(1):
                            self.UsedFunctionDiffListCtrl.Insert( n, self.UsedFunctionDiffListCtrl.GetCount())
            elif line.find("NOCHANGE") != -1:
                p = re.compile("NOCHANGE=(\d)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid value" % line)
                else:
                    try:
                        val = int(m.group(1))
                        self.MatchCheckBox.SetValue(val)
                    except:
                        self.parent.err("Could not convert %s to int" % m.group(1))
            elif line.find("IGNOREINSIG") != -1:
                p = re.compile("IGNOREINSIG=(\d)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid value" % line)
                else:
                    try:
                        val = int(m.group(1))
                        self.InsignificantCheckBox.SetValue(val)
                    except:
                        self.parent.err("Could not convert %s to int" % m.group(1))
            elif line.find("INSIGFUNC") != -1:
                p = re.compile("INSIGFUNC=(\d+):(\d+):(\d+):(\d+)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid value" % line)
                else:
                    try:
                        func_i = (int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4)))
                    except:
                        self.parent.err("Could not turn %s into insiginifcant function definition" % line)
                        func_i = (1,1,1,1)
                    self.parent.msg("Set (%d:%d:%d:%d) as insignificant functiond definition" % func_i)    
                    self.parent.insignificant_function = func_i
            elif line.find("INSIGBB") != -1:
                p = re.compile("INSIGBB=(\d+)$")
                m = p.match(line)
                if not m:
                    self.parent.err("%s is not a valid value" % line)
                else:
                    try:
                        bb_i = int(m.group(1) )
                    except:
                        self.parent.err("Could not turn %s into insiginifcant function definition" % line)
                        bb_i = 2
                    if bb_i < 0:
                        bb_i = 2
                    self.parent.msg("Set %d as insignificant bb definition" % bb_i)    
                    self.parent.insignificant_bb = bb_i
            

########NEW FILE########
__FILENAME__ = api
#
# $Id: api.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class api:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "API"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "API module uses the api calls as a signature"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_LOW
        
        self.parent.register_match_function(    self.match_function_by_api,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_api, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_api,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_api(self, function_a, function_b):
        if len(function_a.ext["PAIMEIDiffFunction"].refs_api) <= 1 or len(function_b.ext["PAIMEIDiffFunction"].refs_api) <= 1:
            return 0
        if len(function_a.ext["PAIMEIDiffFunction"].refs_api) != len(function_b.ext["PAIMEIDiffFunction"].refs_api):
            return 0
            
        matched = 0
        for call_a in function_a.ext["PAIMEIDiffFunction"].refs_api:
            ea, api_call_a = call_a
            for call_b in function_b.ext["PAIMEIDiffFunction"].refs_api:
                ea, api_call_b = call_b
                if api_call_a == api_call_b:
                    matched = 1
                    break
            if not matched:
                return 0
            matched = 0
        return 1
        
    def match_basic_block_by_api(self, bb_a, bb_b):
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_api) != len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_api):
            return 0
            
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_api) <= 0 or len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_api) <= 0:
            return 0

        matched = 0
        for call_a in bb_a.ext["PAIMEIDiffBasicBlock"].refs_api:
            ea, api_call_a = call_a
            for call_b in bb_b.ext["PAIMEIDiffBasicBlock"].refs_api:
                ea, api_call_b = call_b
                if api_call_a == api_call_b:
                    matched = 1
                    break
            if not matched:
                return 0
            matched = 0
        return 1    
        
    def diff_function_by_api(self, function_a, function_b):
        if len(function_a.ext["PAIMEIDiffFunction"].refs_api) <= 1 or len(function_b.ext["PAIMEIDiffFunction"].refs_api) <= 1:
            return 0
        
        if len(function_a.ext["PAIMEIDiffFunction"].refs_api) != len(function_b.ext["PAIMEIDiffFunction"].refs_api):
            return 1
        matched = 0
        for call_a in function_a.ext["PAIMEIDiffFunction"].refs_api:
            ea, api_call_a = call_a
            for call_b in function_b.ext["PAIMEIDiffFunction"].refs_api:
                ea, api_call_b = call_b
                if api_call_a == api_call_b:
                    matched = 1
                    break
            if not matched:
                return 1
            matched = 0
        return 0
        

########NEW FILE########
__FILENAME__ = arg_var
#
# $Id: arg_var.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class arg_var:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "Arg_Var"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "Stack Frame module uses the functions stack frame as a signature"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_LOW        
        
        self.parent.register_match_function(    self.match_function_by_stack_arg_var,    self )   # register a function matching routine
        self.parent.register_diff_function(     self.diff_function_by_stack_arg_var,     self )   # register a function diffing routine
        self.parent.register_match_basic_block( self.match_basic_block_by_stack_arg_var, self )   # register a basic block matching routine

        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_stack_arg_var(self, function_a, function_b):
        if function_a.arg_size  == function_b.arg_size and function_a.num_args == function_b.num_args:
            if function_a.local_var_size == function_b.local_var_size and function_a.num_local_vars == function_b.num_local_vars:
                return 1
        return 0
        
    def diff_function_by_stack_arg_var(self, function_a, function_b):
        if function_a.arg_size  == function_b.arg_size and function_a.num_args == function_b.num_args:
            if function_a.local_var_size == function_b.local_var_size and function_a.num_local_vars == function_b.num_local_vars:
                return 0
        return 1
    def match_basic_block_by_stack_arg_var(self, bb_a, bb_b):
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_args) == 0 and len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_vars) == 0:
            return 0
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_args) == 0 and len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_vars) == 0:
            return 0
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_args) == len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_args) and len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_vars) == len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_vars):
            return 1
        else:
            return 0
            
########NEW FILE########
__FILENAME__ = constants
#
# $Id: constants.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class constants:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "Constants"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "Constants module uses the constants in the functions as signatures"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_LOW
        
        
        self.parent.register_match_function(    self.match_function_by_const,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_const, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_const,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_const(self, function_a, function_b):
        if len(function_a.ext["PAIMEIDiffFunction"].refs_constants) <= 1 or len(function_b.ext["PAIMEIDiffFunction"].refs_constants) <= 1:
            return 0
        if len(function_a.ext["PAIMEIDiffFunction"].refs_constants) != len(function_b.ext["PAIMEIDiffFunction"].refs_constants):
            return 0
        matched = 0
        for constant_a in function_a.ext["PAIMEIDiffFunction"].refs_constants:
            for constant_b in function_b.ext["PAIMEIDiffFunction"].refs_constants:
                if constant_a == constant_b:
                    matched = 1
                    break
            if not matched:
                return 0
            matched = 0
        return 1
        
    def match_basic_block_by_const(self, bb_a, bb_b):
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_constants) <= 1 or len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_constants) <= 1:
            if bb_a.num_instructions < 4 or bb_b.num_instructions < 4:
                return 0
        matched = 0
        
        if len(bb_a.ext["PAIMEIDiffBasicBlock"].refs_constants) != len(bb_b.ext["PAIMEIDiffBasicBlock"].refs_constants):
            return 0
            
        for constant_a in bb_a.ext["PAIMEIDiffBasicBlock"].refs_constants:
            for constant_b in bb_b.ext["PAIMEIDiffBasicBlock"].refs_constants:
                if constant_a == constant_b:
                    matched = 1
                    break
            if not matched:
                return 0
            matched = 0
        return 1   
        
    def diff_function_by_const(self, function_a, function_b):
        if len(function_a.ext["PAIMEIDiffFunction"].refs_constants) <= 1 or len(function_b.ext["PAIMEIDiffFunction"].refs_constants) <= 1:
            return 0
        matched = 0
        if len(function_a.ext["PAIMEIDiffFunction"].refs_constants) != len(function_b.ext["PAIMEIDiffFunction"].refs_constants):
            return 1
            
        for constant_a in function_a.ext["PAIMEIDiffFunction"].refs_constants:
            for constant_b in function_b.ext["PAIMEIDiffFunction"].refs_constants:
                if constant_a == constant_b:
                    matched = 1
                    break
            if not matched:
                return 1
            matched = 0
        return 0
        

########NEW FILE########
__FILENAME__ = crc
#
# $Id: crc.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class crc:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "CRC"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "CRC module uses the crc signature"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_HIGH
        
        self.parent.register_match_function(    self.match_function_by_crc,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_crc, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_crc,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_crc(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].crc == function_b.ext["PAIMEIDiffFunction"].crc:
            return 1
        else:
            return 0
        
    def match_basic_block_by_crc(self, bb_a, bb_b):
        if bb_a.ext["PAIMEIDiffBasicBlock"].crc == bb_b.ext["PAIMEIDiffBasicBlock"].crc:
            return 1
        else:
            return 0
        
    def diff_function_by_crc(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].crc != function_b.ext["PAIMEIDiffFunction"].crc:
            return 0
        else:
            return 0
        

########NEW FILE########
__FILENAME__ = defines
#
# $Id: defines.py 194 2007-04-05 15:31:53Z cameron $
#
FUNCTION_LEVEL    = 0x0001
BASIC_BLOCK_LEVEL = 0x0002
ACCURACY_HIGH     = 0x0003
ACCURACY_LOW      = 0x0004
########NEW FILE########
__FILENAME__ = name
#
# $Id: name.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class name:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 0             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "Name"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "Name module matches using symbols"
        self.date        = "09/15/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_HIGH
        
        self.parent.register_match_function(    self.match_function_by_name,    self )   # register a function matching routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_name(self, function_a, function_b):
#        fd = open("name.out", "a+")
#        fd.write("%s %s\n" % (function_a.name, function_b.name))
        if function_a.name.lower() == function_b.name.lower():
#            fd.write("\t\tMatched\n\n")
#            fd.close()
            return 1
        else:
#            fd.write("\n\n")
#            fd.close()
            return 0
        

########NEW FILE########
__FILENAME__ = neci
#
# $Id: neci.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class neci:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "NECI"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "NECI module uses the node edge call instruction count"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_HIGH
        
        self.parent.register_match_function(    self.match_function_by_neci,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_neci, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_neci,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_neci(self, function_a, function_b):           
        if function_a.ext["PAIMEIDiffFunction"].neci == function_b.ext["PAIMEIDiffFunction"].neci:
            return 1
        else:
            return 0
        
    def match_basic_block_by_neci(self, bb_a, bb_b):
        if bb_a.ext["PAIMEIDiffBasicBlock"].eci == bb_b.ext["PAIMEIDiffBasicBlock"].eci:
            return 1
        else:
            return 0    
        
    def diff_function_by_neci(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].neci != function_b.ext["PAIMEIDiffFunction"].neci:
            return 1
        else:
            return 0
        

########NEW FILE########
__FILENAME__ = size
#
# $Id: size.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class size:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "Size"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "Size uses the size of the function as a signature"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_LOW
        
        self.parent.register_match_function(    self.match_function_by_size,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_size, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_size,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_size(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].size == function_b.ext["PAIMEIDiffFunction"].size:
            return 1
        else:
            return 0
        
    def match_basic_block_by_size(self, bb_a, bb_b):
        if bb_a.ext["PAIMEIDiffBasicBlock"].size == bb_b.ext["PAIMEIDiffBasicBlock"].size:
            return 1
        else:
            return 0    
        
    def diff_function_by_size(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].size != function_b.ext["PAIMEIDiffFunction"].size:
            return 1
        else:
            return 0
        

########NEW FILE########
__FILENAME__ = smart_md5
#
# $Id: smart_md5.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class smart_md5:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "Smart_MD5"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "Smart MD5  module implements an algorithm that tokenizes the instructions to create a smart signature."
        self.date        = "09/08/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_HIGH
        
        self.parent.register_match_function(    self.match_function_by_smart_md5,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_smart_md5, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_smart_md5,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_smart_md5(self, function_a, function_b):
        if not function_a.ext.has_key("PAIMEIDiffFunction") or not function_b.ext.has_key("PAIMEIDiffFunction"):
            return 0
        if function_a.ext["PAIMEIDiffFunction"].smart_md5 == function_b.ext["PAIMEIDiffFunction"].smart_md5:
            return 1
        else:
            return 0
        
    def match_basic_block_by_smart_md5(self, bb_a, bb_b):
        if bb_a.ext["PAIMEIDiffBasicBlock"].smart_md5 == bb_b.ext["PAIMEIDiffBasicBlock"].smart_md5:
            return 1
        else:
            return 0    
        
    def diff_function_by_smart_md5(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].smart_md5 != function_b.ext["PAIMEIDiffFunction"].smart_md5:
            return 1
        else:
            return 0
        

########NEW FILE########
__FILENAME__ = spp
#
# $Id: spp.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class spp:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL | BASIC_BLOCK_LEVEL   # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "SPP"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "SPP module implements the Small Prime Product method developed by halvar"
        self.date        = "09/08/06"
        self.homepage    = "http://www.openrce.org"
        self.links       = "http://www.sabre-security.com"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_HIGH
        
        
        self.parent.register_match_function(    self.match_function_by_spp,    self )   # register a function matching routine
        self.parent.register_match_basic_block( self.match_basic_block_by_spp, self )   # register a basic block matching routine
        self.parent.register_diff_function(     self.diff_function_by_spp,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_spp(self, function_a, function_b):
        if not function_a.ext.has_key("PAIMEIDiffFunction") or not function_b.ext.has_key("PAIMEIDiffFunction"):
            return 0
            
        if function_a.ext["PAIMEIDiffFunction"].spp == function_b.ext["PAIMEIDiffFunction"].spp:
            return 1
        else:
            return 0
        
    def match_basic_block_by_spp(self, bb_a, bb_b):
        if bb_a.ext["PAIMEIDiffBasicBlock"].spp == bb_b.ext["PAIMEIDiffBasicBlock"].spp:
            return 1
        else:
            return 0    
        
    def diff_function_by_spp(self, function_a, function_b):
        if function_a.ext["PAIMEIDiffFunction"].spp != function_b.ext["PAIMEIDiffFunction"].spp:
            return 1
        else:
            return 0
        

########NEW FILE########
__FILENAME__ = stack_frame
#
# $Id: stack_frame.py 194 2007-04-05 15:31:53Z cameron $
#

from defines import *

class stack_frame:
    def __init__(self, parent=None):
        self.attributes = {}                    # initialize attributes
        
        self.attributes["Match"] = 1            # Match attribute set to 1 tells the main program we can be used to match 
        self.attributes["Diff"] = 1             # Diff  attribute set to 1 tells the main program we can be used to diff
        self.attributes["Level"] = FUNCTION_LEVEL # these flags indicated we can diff/match both functions and basic blocks
        self.parent = parent                    # set up the parent
        
        self.module_name = "Stack_Frame"                # give the module a name
        self.author      = "Peter Silberman"    # author name
        self.description = "Stack Frame module uses the functions stack frame as a signature"
        self.date        = "09/22/06"
        self.homepage    = "http://www.openrce.org"
        self.contact     = "peter.silberman@gmail.com"
        self.accuracy    = ACCURACY_LOW        
        
        self.parent.register_match_function(    self.match_function_by_stack_frame,    self )   # register a function matching routine
        self.parent.register_diff_function(     self.diff_function_by_stack_frame,     self )   # register a function diffing routine
        self.parent.register_module(self)                                               # register our module in the module table
        
    def match_function_by_stack_frame(self, function_a, function_b):
        if function_a.frame_size == function_b.frame_size:
            return 1
        else:
            return 0
        
    def diff_function_by_stack_frame(self, function_a, function_b):
        if function_a.frame_size != function_b.frame_size:
            return 1
        else:
            return 0
            
########NEW FILE########
__FILENAME__ = ExplorerTreeCtrl
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: ExplorerTreeCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import re
import MySQLdb
import sys
import os
import time
import PAIMEIDiffFunction
import pida



class ExplorerTreeCtrl (wx.TreeCtrl):
    '''
    Our custom tree control.
    '''

    def __init__ (self, parent, id, pos=None, size=None, style=None, top=None, name=None):
        wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
        self.top            = top
        self.selected       = None
        self.module_name    = ""
        
        self.ctrl_name = name
        
        # setup our custom tree list control.
        self.icon_list        = wx.ImageList(16, 16)
        self.icon_folder      = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, (16, 16)))
        self.icon_folder_open = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER, (16, 16)))
        self.icon_tag         = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16, 16)))
        self.icon_selected    = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FIND,        wx.ART_OTHER, (16, 16)))
        self.icon_filtered    = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_CUT,         wx.ART_OTHER, (16, 16)))

        self.SetImageList(self.icon_list)

        self.root = self.AddRoot("Modules")
        self.root_module = None
        self.SetPyData(self.root, None)
        self.SetItemImage(self.root, self.icon_folder,      wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root, self.icon_folder_open, wx.TreeItemIcon_Expanded)



    ####################################################################################################################
    def load_module (self, module_name):
        '''
        Load the specified module into the tree.
        '''
        dlg = wx.FileDialog(                                    \
            self,                                               \
            message     = "Select PIDA module",                 \
            defaultDir  = os.getcwd(),                          \
            defaultFile = "",                                   \
            wildcard    = "*.PIDA",                             \
            style       = wx.OPEN | wx.CHANGE_DIR | wx.MULTIPLE \
        )
        
        if dlg.ShowModal() != wx.ID_OK:
            return

        for path in dlg.GetPaths():

            module_name = path[path.rfind("\\")+1:path.rfind(".pida")].lower()
            
            if self.top.pida_modules.has_key(module_name):
                self.top.err("Module %s already loaded ... skipping." % module_name)
                continue
    
            busy = wx.BusyInfo("Loading module ... stand by.")
            wx.Yield()
            
            start = time.time()
       
            #if they want to diff a new module remove the current module
            if self.root_module != None:
                del self.top.pida_modules[self.module_name]
                self.remove_module()
                
            self.top.pida_modules[module_name] = pida.load(path)
            
            #if we are tree a then we load the module name into module_a_name and visa versa
            if self.ctrl_name == "A":
                self.top.module_a_name = module_name
            else:
                self.top.module_b_name = module_name
                
            #set the current module name
            self.module_name = module_name
            
            tree_module = self.AppendItem(self.root, module_name)
            
            self.root_module = tree_module
            
            self.SetPyData(tree_module, self.top.pida_modules[module_name])
            self.SetItemImage(tree_module, self.icon_folder,      wx.TreeItemIcon_Normal)
            self.SetItemImage(tree_module, self.icon_folder_open, wx.TreeItemIcon_Expanded)
        
            sorted_functions = [f.id for f in self.top.pida_modules[module_name].nodes.values() if not f.is_import]
            sorted_functions.sort()
        
            for func_key in sorted_functions:
                #add our extension into the loaded module
                self.top.pida_modules[module_name].nodes[func_key].ext["PAIMEIDiffFunction"] = PAIMEIDiffFunction.PAIMEIDiffFunction(self.top.pida_modules[module_name].nodes[func_key], self.top.pida_modules[module_name], self.top)
                function = self.top.pida_modules[module_name].nodes[func_key]
                tree_function = self.AppendItem(tree_module, "%08x - %s" % (function.ea_start, function.name))
                self.SetPyData(tree_function, self.top.pida_modules[module_name].nodes[func_key])
                self.SetItemImage(tree_function, self.icon_folder,      wx.TreeItemIcon_Normal)
                self.SetItemImage(tree_function, self.icon_folder_open, wx.TreeItemIcon_Expanded)
                
                sorted_bbs = function.nodes.keys()
                sorted_bbs.sort()
        

            self.Expand(self.root)
            self.top.msg("Loaded %d function(s) in PIDA module '%s' in %.2f seconds." % (len(self.top.pida_modules[module_name].nodes), module_name, round(time.time() - start, 3)))
                
               
            
    ####################################################################################################################
    def remove_module (self):
        '''
        Remove the module from the TreeCtrl
        '''
        if not self.root_module:
            return
            
        self.DeleteChildren(self.root_module)
        self.Delete(self.root_module)    
                  


########NEW FILE########
__FILENAME__ = FunctionViewDifferDlg
# -*- coding: ISO-8859-1 -*-
# generated by wxGlade 0.4.1 on Sun Jun 04 13:39:07 2006
#
# $Id: FunctionViewDifferDlg.py 194 2007-04-05 15:31:53Z cameron $
#


import wx
import FunctionViewDiffListCtrl
import FunctionViewStatsListCtrl
# begin wxGlade: dependencies
# end wxGlade

class FunctionViewDifferDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.function_a = []
        self.function_a_current = 0
        
        self.function_b = []
        self.function_b_current = 0
        
        self.parent = kwds["parent"]
        # begin wxGlade: FunctionViewDifferDlg.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.THICK_FRAME
        wx.Dialog.__init__(self, *args, **kwds)
        self.FunctionViewADiffListCtrl  = FunctionViewDiffListCtrl.FunctionViewDiffListCtrl(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER,top=self.parent,dlg=self,ctrl="A")
        self.FunctionViewBDiffListCtrl  = FunctionViewDiffListCtrl.FunctionViewDiffListCtrl(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER,top=self.parent,dlg=self,ctrl="B")
        self.FunctionViewStatsAListCtrl = FunctionViewStatsListCtrl.FunctionViewStatsListCtrl(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER,top=self.parent,name="A")
        self.FunctionViewStatsBListCtrl = FunctionViewStatsListCtrl.FunctionViewStatsListCtrl(self, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.SUNKEN_BORDER,top=self.parent,name="B")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        

        self.FunctionViewADiffListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.FunctionViewADiffListCtrl.OnItemSelect)
        self.FunctionViewADiffListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.FunctionViewADiffListCtrl.OnRightClick)
        
        self.FunctionViewBDiffListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.FunctionViewBDiffListCtrl.OnItemSelect)
        self.FunctionViewBDiffListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.FunctionViewBDiffListCtrl.OnRightClick)
        
        
        
        
    def __set_properties(self):
        # begin wxGlade: FunctionViewDifferDlg.__set_properties
        self.SetTitle("dialog_1")
        self.SetSize((796, 418))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: FunctionViewDifferDlg.__do_layout
        sizer_9 = wx.BoxSizer(wx.VERTICAL)
        sizer_11 = wx.BoxSizer(wx.VERTICAL)
        sizer_12 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_10 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_23 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_23.Add(self.FunctionViewADiffListCtrl, 1, wx.EXPAND, 0)
        sizer_23.Add(self.FunctionViewBDiffListCtrl, 1, wx.EXPAND, 0)
        sizer_10.Add(sizer_23, 1, wx.EXPAND, 0)
        sizer_9.Add(sizer_10, 1, wx.ALL|wx.EXPAND, 0)
        sizer_12.Add(self.FunctionViewStatsAListCtrl, 1, wx.ALL|wx.EXPAND, 0)
        sizer_12.Add(self.FunctionViewStatsBListCtrl, 1, wx.ALL|wx.EXPAND, 0)
        sizer_11.Add(sizer_12, 1, wx.ALL|wx.EXPAND, 0)
        sizer_9.Add(sizer_11, 1, wx.ALL|wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_9)
        self.Layout()
        # end wxGlade

# end of class FunctionViewDifferDlg



########NEW FILE########
__FILENAME__ = FunctionViewDiffListCtrl
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: FunctionViewDiffListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

sys.path.append("..")

import pida

class FunctionViewDiffListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None,dlg=None,ctrl=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES | wx.LC_SINGLE_SEL )
        self.top=top
        self.dlg=dlg
        self.parent = parent
        self.ctrl_name = ctrl
        self.curr = 0

        ListCtrlAutoWidthMixin.__init__(self)

        self.InsertColumn(0, ctrl + ": EA")
        self.InsertColumn(1, ctrl + ": Mnem")
        self.InsertColumn(2, ctrl + ": Op 1")
        self.InsertColumn(3, ctrl + ": Op 2")
        self.InsertColumn(4, ctrl + ": Matched")
        self.InsertColumn(5, ctrl + ": Match Method")
        self.InsertColumn(6, ctrl + ": Match Value")
        self.InsertColumn(7, ctrl + ": Basic Block EA")

        
        self.load_function()
    
    ####################################################################################################################
    def load_function(self, man_func=None):
        '''
        load function into the list ctrl
        '''
        if man_func != None:
            func = man_func
        elif self.ctrl_name == "A":
            function = self.top.matched_list.matched_functions[ self.top.MatchedAListCtrl.curr ]
            (func,func_b) = function
            self.dlg.function_a.append(func)
            self.dlg.function_a_current+=1
           
        elif self.ctrl_name == "B":
            function = self.top.matched_list.matched_functions[ self.top.MatchedBListCtrl.curr ]
            (func_a,func) = function
            self.dlg.function_b.append(func)
            self.dlg.function_b_current+=1
           
        self.DeleteAllItems()
        i = 0
        spacer = 0
        idx = 0
        max_num = func.num_instructions + len(func.nodes.values())
        
        while i <= max_num:
            self.InsertStringItem(idx, "")
            self.SetStringItem(idx, 0, "")
            self.SetStringItem(idx, 1, "")
            self.SetStringItem(idx, 2, "")
            self.SetStringItem(idx, 3, "")
            self.SetStringItem(idx, 4, "")
            self.SetStringItem(idx, 5, "")
            self.SetStringItem(idx, 6, "")
            self.SetStringItem(idx, 7, "")
            self.SetStringItem(idx, 8, "")
            self.SetStringItem(idx, 9, "")
            self.SetStringItem(idx, 10, "")
            self.SetStringItem(idx, 11, "")
            self.SetStringItem(idx, 12, "")
            self.SetStringItem(idx, 13, "")
            self.SetStringItem(idx, 14, "")
            self.SetStringItem(idx, 15, "")
            i+=1
        i = 0
        idx = 0
        bb_count = 0
        for bb in func.sorted_nodes():
            for ii in bb.sorted_instructions():
                self.SetStringItem(idx, 0, "0x%08x" % ii.ea)
                self.SetStringItem(idx, 1, "%s" % ii.mnem)
                self.SetStringItem(idx, 2, "%s" % ii.op1)
                self.SetStringItem(idx, 3, "%s" % ii.op2)
                if bb.ext["PAIMEIDiffBasicBlock"].matched:
                    self.SetStringItem(idx, 4, "Yes")
                    self.SetStringItem(idx, 5, "%s" % bb.ext["PAIMEIDiffBasicBlock"].match_method)
                    if bb.ext["PAIMEIDiffBasicBlock"].match_method == "SPP":
                        self.SetStringItem(idx, 6, "0x%08x" % bb.ext["PAIMEIDiffBasicBlock"].spp)
                    elif bb.ext["PAIMEIDiffBasicBlock"].match_method == "NECI":
                        pass
                    elif bb.ext["PAIMEIDiffBasicBlock"].match_method == "API":
                        call_str = ""
                        for call in func.ext["PAIMEIDiffFunction"].refs_api:
                            (ea,c) = call
                            if call_str == "":
                                call_str += c
                            else:
                                call_str += ":" + c
                        self.SetStringItem(idx, 6, "%s" % call_str)
                    elif bb.ext["PAIMEIDiffBasicBlock"].match_method == "Constants":
                        const_str = ""
                        for const_s in bb.ext["PAIMEIDiffBasicBlock"].refs_constants:
                            if const_str == "":
                                const_str += str(const_s)
                            else:
                                const_str += ":" + str(const_s)
                        self.SetStringItem(idx, 6, "%s" % const_str)   
                else:
                    self.SetStringItem(idx, 4, "No")
                    self.SetStringItem(idx, 5, "")
                
                self.SetStringItem(idx, 7, "0x%08x" % bb.ea_start)
                if bb.ext["PAIMEIDiffBasicBlock"].ignore:
                    item = self.GetItem(idx)
                    item.SetTextColour(wx.LIGHT_GREY)
                    self.SetItem(item)
                elif not bb.ext["PAIMEIDiffBasicBlock"].matched:
                    item = self.GetItem(idx)
                    item.SetTextColour(wx.RED)
                    self.SetItem(item)
                idx+=1
            idx+=1

    ####################################################################################################################       
    def OnItemSelect(self,evt):
        self.curr = evt.m_itemIndex
        if self.ctrl_name == "A":
            if self.curr < self.dlg.FunctionViewBDiffListCtrl.GetItemCount():
                self.dlg.FunctionViewBDiffListCtrl.curr = self.curr
                item = self.dlg.FunctionViewBDiffListCtrl.GetItem(self.curr)
                item.m_stateMask = wx.LIST_STATE_SELECTED  
                item.m_state     = wx.LIST_STATE_SELECTED  
                self.dlg.FunctionViewBDiffListCtrl.SetItem(item)
                self.dlg.FunctionViewBDiffListCtrl.EnsureVisible(self.curr)
        else:
            if self.curr < self.dlg.FunctionViewADiffListCtrl.GetItemCount():
                self.dlg.FunctionViewADiffListCtrl.curr = self.curr
                item = self.dlg.FunctionViewADiffListCtrl.GetItem(self.curr)
                item.m_stateMask = wx.LIST_STATE_SELECTED  
                item.m_state     = wx.LIST_STATE_SELECTED  
                self.dlg.FunctionViewADiffListCtrl.SetItem(item)
                self.dlg.FunctionViewADiffListCtrl.EnsureVisible(self.curr)
        
        
    
    
    ####################################################################################################################
    def OnRightClick(self, event):
        if not hasattr(self, "popupID1"):
            self.popupID1 = wx.NewId()
            self.popupID2 = wx.NewId()
    

            self.Bind(wx.EVT_MENU, self.view_basic_block, id=self.popupID1)
            self.Bind(wx.EVT_MENU, self.view_function, id=self.popupID2)
  

        # make a menu
        menu = wx.Menu()
        # add some items
        menu.Append(self.popupID1, "View Basic Block Stats")
        menu.Append(self.popupID2, "View Function Stats")
 

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()

    ####################################################################################################################        
    def view_basic_block(self, event):
        #self.curr = event.m_itemIndex
        
        item = self.GetItem(self.curr, 7)
            
        bb = item.GetText()
        
        if len(bb) == 0:
            return

        if self.ctrl_name == "A":
            self.dlg.FunctionViewStatsAListCtrl.load_basic_block_stats(bb)
        else:
            self.dlg.FunctionViewStatsBListCtrl.load_basic_block_stats(bb)
    
    ####################################################################################################################
    def view_function(self,event):
        if self.ctrl_name == "A":
            self.dlg.FunctionViewStatsAListCtrl.load_function_stats()
        else:
            self.dlg.FunctionViewStatsBListCtrl.load_function_stats()
            
    ####################################################################################################################
    def OnDoubleClick(self,event):
        item = self.GetItem(self.curr, 1)
        mnem = item.GetText()
        if mnem == "call":
            item = self.GetItem(self.curr, 2)
            dest = item.GetText()
            i = 0
            while i < len(self.top.matched_list.matched_functions):
                func_a, func_b = self.top.matched_list.matched_functions[i]
                if self.ctrl_name == "A":
                    func = func_a
                elif self.ctrl_name == "B":
                    func = func_b
                if func.name == dest:
                    self.load_function(func)
                    break
                i+=1
########NEW FILE########
__FILENAME__ = FunctionViewDlg
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: FunctionViewDlg.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import FunctionViewListCtrl
import FunctionViewStatsListCtrl

# begin wxGlade: dependencies
# end wxGlade

class FunctionViewDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: FunctionViewDlg.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.parent = kwds["parent"]
        self.FunctionViewListCtrl = FunctionViewListCtrl.FunctionViewListCtrl(self, -1, top=self.parent, style=wx.LC_REPORT|wx.SUNKEN_BORDER | wx.LC_SINGLE_SEL )
        self.FunctionViewStatsListCtrl = FunctionViewStatsListCtrl.FunctionViewStatsListCtrl(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER, name="U",top=self.parent)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.FunctionViewListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.FunctionViewListCtrl.OnRightClick)
        self.FunctionViewListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.FunctionViewListCtrl.OnItemSelect)


    def __set_properties(self):
        # begin wxGlade: FunctionViewDlg.__set_properties
        self.SetTitle("Function View")
        self.SetSize((761, 466))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: FunctionViewDlg.__do_layout
        sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_16 = wx.BoxSizer(wx.VERTICAL)
        sizer_16.Add(self.FunctionViewListCtrl, 1, wx.EXPAND, 0)
        sizer_16.Add(self.FunctionViewStatsListCtrl, 1, wx.EXPAND, 0)
        sizer_15.Add(sizer_16, 1, wx.EXPAND, 0)
        sizer_14.Add(sizer_15, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_14)
        self.Layout()
        # end wxGlade

# end of class FunctionViewDlg



########NEW FILE########
__FILENAME__ = FunctionViewListCtrl
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: FunctionViewListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time


from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin



sys.path.append("..")

import pida

class FunctionViewListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES | wx.LC_SINGLE_SEL)
        self.top=top
        self.parent = parent
        self.curr = 0
        ListCtrlAutoWidthMixin.__init__(self)
        self.InsertColumn(0,  "EA")
        self.InsertColumn(1,  "Mnem")
        self.InsertColumn(2,  "Op 1")
        self.InsertColumn(3,  "Op 2")
        self.load_function()

    def load_function(self):
        func = self.top.function_list[ self.top.curr ]
        idx = 0
        for bb in func.sorted_nodes():
            for inst in bb.sorted_instructions():
                self.InsertStringItem(idx, "")
                self.SetStringItem(idx, 0, "0x%08x" % inst.ea)            
                self.SetStringItem(idx, 1, "%s" % inst.mnem)
                self.SetStringItem(idx, 2, "%s" % inst.op1)
                self.SetStringItem(idx, 3, "%s" % inst.op2)
                idx+=1
            self.InsertStringItem(idx, "")
            self.SetStringItem(idx, 0, "")            
            self.SetStringItem(idx, 1, "")
            self.SetStringItem(idx, 2, "")
            self.SetStringItem(idx, 3, "")
            idx+=1

    ####################################################################################################################
    def OnRightClick(self, event):
        if not hasattr(self, "popupID1"):
            self.popupID1 = wx.NewId()
            self.popupID2 = wx.NewId()
    

            self.Bind(wx.EVT_MENU, self.view_basic_block, id=self.popupID1)
            self.Bind(wx.EVT_MENU, self.view_function, id=self.popupID2)
  

        # make a menu
        menu = wx.Menu()
        # add some items
        menu.Append(self.popupID1, "View Basic Block Stats")
        menu.Append(self.popupID2, "View Function Stats")
 

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()
        
    def view_basic_block(self, event):
        #self.curr = event.m_itemIndex
        item = self.GetItem(self.curr, 0)
        bb = item.GetText()
        print bb
        if len(bb) == 0:
            return
        self.parent.FunctionViewStatsListCtrl.load_basic_block_stats(bb)
    
    def view_function(self,event):
        self.parent.FunctionViewStatsListCtrl.load_function_stats()
    
    def OnItemSelect(self,evt):
        self.curr = evt.m_itemIndex
        if self.curr <= self.GetItemCount():
            self.curr = self.curr
            item = self.GetItem(self.curr)
            item.m_stateMask = wx.LIST_STATE_SELECTED  
            item.m_state     = wx.LIST_STATE_SELECTED  
            self.SetItem(item)
            self.EnsureVisible(self.curr)


########NEW FILE########
__FILENAME__ = FunctionViewStatsListCtrl
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: FunctionViewStatsListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

sys.path.append("..")

import pida

class FunctionViewStatsListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None, name=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES )
        self.top=top
        self.name_ctrl = name
        self.parent = parent

        ListCtrlAutoWidthMixin.__init__(self)

        self.InsertColumn(0,  "Field")
        self.InsertColumn(1,  "Value")

    ####################################################################################################################        
    def load_function_stats(self):
        '''
        load the function stats like signatures name extra
        '''
        self.DeleteAllItems()
        idx = 0
        if self.name_ctrl == "A":
            function = self.top.matched_list.matched_functions[ self.top.MatchedAListCtrl.curr ]
            (func,func_b) = function
        elif self.name_ctrl == "B":
            function = self.top.matched_list.matched_functions[ self.top.MatchedBListCtrl.curr ]
            (func_a,func) = function
        else:
            func = self.parent.parent.function_list[ self.parent.parent.curr]
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Name")
        self.SetStringItem(idx, 1, "%s" % func.name)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "EA Start")
        self.SetStringItem(idx, 1, "0x%08x" % func.ea_start)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "EA End")
        self.SetStringItem(idx, 1, "0x%08x" % func.ea_end)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Instruction Count")
        self.SetStringItem(idx, 1, "%d" % func.num_instructions)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "BB Count")
        self.SetStringItem(idx, 1, "%d" % len(func.nodes.values()))
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Call Count")
        self.SetStringItem(idx, 1, "%d" % func.ext["PAIMEIDiffFunction"].num_calls)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Stack Frame")
        self.SetStringItem(idx, 1, "%d" % func.frame_size)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Size")
        self.SetStringItem(idx, 1, "%d" % func.ext["PAIMEIDiffFunction"].size)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Num Local Vars")
        self.SetStringItem(idx, 1, "%d" % func.num_local_vars)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Num Arguments")
        self.SetStringItem(idx, 1, "%d" % func.num_args)
        idx+=1
        
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Local Var Size")
        self.SetStringItem(idx, 1, "%d" % func.local_var_size)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Arg Size")
        self.SetStringItem(idx, 1, "%d" % func.arg_size)
        idx+=1
        
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "SPP")
        self.SetStringItem(idx, 1, "0x%08x" % func.ext["PAIMEIDiffFunction"].spp)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Smart MD5")
        self.SetStringItem(idx, 1, "%s" % func.ext["PAIMEIDiffFunction"].smart_md5)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "CRC")
        self.SetStringItem(idx, 1, "0x%08x" % func.ext["PAIMEIDiffFunction"].crc)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "NECI")
        self.SetStringItem(idx, 1, "%d:%d:%d:%d" % func.ext["PAIMEIDiffFunction"].neci)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Recursive Call Count")
        self.SetStringItem(idx, 1, "%d" % len(func.ext["PAIMEIDiffFunction"].recursive))
        idx+=1
        self.InsertStringItem(idx, "")
        str_str = ""
        for s in func.ext["PAIMEIDiffFunction"].refs_strings:
            if str_str == "":
                str_str += str(s)
            else:
                str_str += ":" + str(s)
        self.SetStringItem(idx, 0, "String References")
        self.SetStringItem(idx, 1, "%s" % str_str)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Constants References")
        const_str = ""
        for const_s in func.ext["PAIMEIDiffFunction"].refs_constants:
            if const_str == "":
                const_str += str(const_s)
            else:
                const_str += ":" + str(const_s)
        self.SetStringItem(idx, 1, "%s" % const_str)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "API Calls")
        call_str = ""
        for call in func.ext["PAIMEIDiffFunction"].refs_api:
            (ea,c) = call
            if call_str == "":
                call_str += c
            else:
                call_str += ":" + c
        self.SetStringItem(idx, 1, "%s" % call_str)
        idx+=1
        
        
    ####################################################################################################################
    def load_basic_block_stats(self, bb_start):
        '''
        load the basic block specific statistics
        '''
        self.DeleteAllItems()
        idx = 0
       
        if self.name_ctrl == "A":
            function = self.top.matched_list.matched_functions[ self.top.MatchedAListCtrl.curr ]
            (func,func_b) = function
        elif self.name_ctrl == "B":
            function = self.top.matched_list.matched_functions[ self.top.MatchedBListCtrl.curr ]
            (func_a, func) = function
        else:
            func = self.parent.parent.function_list[ self.parent.parent.curr]

#        print "A %d: func: %s" % (self.top.MatchedAListCtrl.curr , func.name)
#        print "B %d: func: %s" % (self.top.MatchedBListCtrl.curr , func.name)


        bb = None
        start=""

        for bb in func.sorted_nodes():
            start = str(hex(bb.ea_start)) 

            
            if len(start) != 10:
                d = 10 - len(start) 
                start = "0x" + "0" * 2 + start[2:]                
#            print "%s == %s" % (start, bb_start)
            if start == bb_start:
#                print "found"
                break
        if bb == None:
            for bb in func.sorted_nodes():
                start = hex(bb.ea_start)
                end   = hex(bb.ea_end)
                bb_s = hex(bb_start)
                if bb_s >= start and bb_s <= end:
                    break
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Name")
        self.SetStringItem(idx, 1, "%s" % func.name)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "EA Start")
        self.SetStringItem(idx, 1, "0x%08x" % bb.ea_start)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "EA End")
        self.SetStringItem(idx, 1, "0x%08x" % bb.ea_end)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Instruction Count")
        self.SetStringItem(idx, 1, "%d" % bb.num_instructions)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Call Count")
        self.SetStringItem(idx, 1, "%d" % bb.ext["PAIMEIDiffBasicBlock"].num_calls)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Size")
        self.SetStringItem(idx, 1, "%d" % bb.ext["PAIMEIDiffBasicBlock"].size)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "SPP")
        self.SetStringItem(idx, 1, "0x%08x" % bb.ext["PAIMEIDiffBasicBlock"].spp)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Smart MD5")
        self.SetStringItem(idx, 1, "%s" % bb.ext["PAIMEIDiffBasicBlock"].smart_md5)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "CRC")
        self.SetStringItem(idx, 1, "0x%08x" % bb.ext["PAIMEIDiffBasicBlock"].crc)
        idx+=1
        self.InsertStringItem(idx, "")
        str_str = ""
        for s in bb.ext["PAIMEIDiffBasicBlock"].refs_strings:
            if str_str == "":
                str_str += str(s)
            else:
                str_str += ":" + str(s)
        self.SetStringItem(idx, 0, "String References")
        self.SetStringItem(idx, 1, "%s" % str_str)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "Constants References")
        const_str = ""
        for const_s in bb.ext["PAIMEIDiffBasicBlock"].refs_constants:
            if const_str == "":
                const_str += str(const_s)
            else:
                const_str += ":" + str(const_s)
        self.SetStringItem(idx, 1, "%s" % const_str)
        idx+=1
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "API Calls")
        call_str = ""
        for call in bb.ext["PAIMEIDiffBasicBlock"].refs_api:
            (ea,s) = call
            if call_str == "":
                call_str += s
            else:
                call_str += ":" + s
        self.SetStringItem(idx, 1, "%s" % call_str)
        idx+=1

########NEW FILE########
__FILENAME__ = InsigList
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: InsigList.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

class InsigList:
    def __init__(self):
        self.insig_module_a = []
        self.insig_module_b = []
        
    ####################################################################################################################    
    def add_to_unmatched_a(self, func):
        self.insig_module_a.append(func)
        
    ####################################################################################################################
    def add_to_unmatched_b(self, func):
        self.insig_module_b.append(func)
    
    ####################################################################################################################
    def remove_unmatched_a(self, i):
        func = self.insig_module_a[ i ]
        del self.insig_module_a[ i ]
        return func

    ####################################################################################################################
    def remove_unmatched_b(self, i):
        func = self.insig_module_b[ i ]
        del self.insig_module_b[ i ]
        return func
            

        

            

########NEW FILE########
__FILENAME__ = InsignificantConfigDlg
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: InsignificantConfigDlg.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import re
# begin wxGlade: dependencies
# end wxGlade

class InsignificantConfigDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]
        # begin wxGlade: InsignificantConfigDlg.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.sizer_20_staticbox = wx.StaticBox(self, -1, "Insignificant Basic Block")
        self.sizer_19_staticbox = wx.StaticBox(self, -1, "Insignificant Function")
        self.label_1 = wx.StaticText(self, -1, "Function Definition should look like a NECI. \n(Num Nodes: Num Edges: Num Calls: Num Instructions) \ndefault is 1:1:1:1")
        s = "%s:%s:%s:%s" % self.parent.parent.insignificant_function
        self.FuncTxtCtrl = wx.TextCtrl(self, -1, s)
        self.label_2 = wx.StaticText(self, -1, "Basic Block definition is only the instruction count. \nDefault is 2. ")
        self.BBTxtCtrl  = wx.TextCtrl(self, -1, str(self.parent.parent.insignificant_bb))
        self.DoneButton = wx.Button(self, -1, "Done")
        self.CancelButton = wx.Button(self, -1, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade
        self.function_def = self.parent.parent.insignificant_function
        self.bb_def       = self.parent.parent.insignificant_bb
        
        self.Bind(wx.EVT_BUTTON,         self.on_done,          self.DoneButton)
        self.Bind(wx.EVT_BUTTON,         self.on_cancel,        self.CancelButton)

    def __set_properties(self):
        # begin wxGlade: InsignificantConfigDlg.__set_properties
        self.SetTitle("Insignificant Function/BB Configuration")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: InsignificantConfigDlg.__do_layout
        sizer_17 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_18 = wx.BoxSizer(wx.VERTICAL)
        sizer_22 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_20 = wx.StaticBoxSizer(self.sizer_20_staticbox, wx.HORIZONTAL)
        sizer_21 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_19 = wx.StaticBoxSizer(self.sizer_19_staticbox, wx.HORIZONTAL)
        sizer_19.Add(self.label_1, 0, wx.ADJUST_MINSIZE, 0)
        sizer_19.Add(self.FuncTxtCtrl, 0, wx.ADJUST_MINSIZE, 0)
        sizer_18.Add(sizer_19, 1, wx.EXPAND, 0)
        sizer_21.Add(self.label_2, 0, wx.ADJUST_MINSIZE, 0)
        sizer_21.Add(self.BBTxtCtrl, 0, wx.ADJUST_MINSIZE, 0)
        sizer_20.Add(sizer_21, 1, wx.EXPAND, 0)
        sizer_18.Add(sizer_20, 1, wx.EXPAND, 0)
        sizer_22.Add(self.DoneButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_22.Add(self.CancelButton, 0, wx.ADJUST_MINSIZE, 0)
        sizer_18.Add(sizer_22, 1, wx.EXPAND, 0)
        sizer_17.Add(sizer_18, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_17)
        sizer_17.Fit(self)
        sizer_17.SetSizeHints(self)
        self.Layout()
        # end wxGlade
    
    ####################################################################################################################
    def on_done(self, event):
        func = self.FuncTxtCtrl.GetValue()
        bb = self.BBTxtCtrl.GetValue()
        

        try:
            bb_i = int(bb)
        except:
            self.parent.parent.err("%s is not an integer reverting to default" % bb)
            bb_i = 2
            
        if bb_i < 0:
            self.parent.parent.err("%d is a negative reverting to default" % bb_i)
            bb_i = 2        

        
        x = func.split(":")
        p = re.compile("(\d+):(\d+):(\d+):(\d+)")
        m = p.match(func)
        if not m:
            self.parent.parent.err("Failed to parse %s reverting to default" % func)
        else:
            try:
                func_i = (int(x[0]), int(x[1]), int(x[2]), int(x[3]))
            except:
                self.parent.parent.err("%s is not an integer reverting to default" % func)
                func_i = (1,1,1,1)
        
        self.parent.parent.insignificant_function = func_i
        self.parent.parent.insignificant_bb = bb_i
        self.Destroy()

    ####################################################################################################################
    def on_cancel(self,event):
        self.Destroy()
    
# end of class InsignificantConfigDlg
    


########NEW FILE########
__FILENAME__ = MatchedList
# $Id: MatchedList.py 194 2007-04-05 15:31:53Z cameron $





class MatchedList:
    '''
    Instantiated from PAIMEIdiff, this is the class that will keep track of all the matched functions, and perform
    all the utility functions like unmatching matching marking as matched etc.
    '''
    def __init__(self, parent=None):
        self.matched_functions      = []    # a list of tuples containing (function_a, function_b) that have been matched
        self.num_matched_functions  = 0     # number of functions matched
        self.num_ignored_functions  = 0     # number of ignored functions
        self.num_matched_basic_block = 0    # number of basic blocks matched
        self.num_ignored_basic_block = 0    # number of basic blocks ignored
        self.num_different_functions = 0    # number of different functions
        self.parent                 = parent

    ####################################################################################################################        
    def add_matched_function(self, function_a, function_b, matched_method):
        '''
        Add two functions to the matched list
        '''
        function_a.ext["PAIMEIDiffFunction"].matched            = function_b.ext["PAIMEIDiffFunction"].matched  = 1
        function_a.ext["PAIMEIDiffFunction"].match_method       = matched_method
        function_b.ext["PAIMEIDiffFunction"].match_method       = matched_method
        function_a.ext["PAIMEIDiffFunction"].matched_ea         = function_b.ea_start
        function_b.ext["PAIMEIDiffFunction"].matched_ea         = function_a.ea_start
        function_a.ext["PAIMEIDiffFunction"].matched_function   = function_b
        function_b.ext["PAIMEIDiffFunction"].matched_function   = function_a
        self.matched_functions.append( (function_a, function_b))
        self.num_matched_functions+=1
        
    ####################################################################################################################                                
    def mark_function_all_bb_matched(self, idx):
        (function_a, function_b) = self.matched_functions[idx]
        function_a.ext["PAIMEIDiffFunction"].all_bb_matched = function_b.ext["PAIMEIDiffFunction"].all_bb_matched = 1
        self.matched_functions[idx] = (function_a, function_b
        )                                     
    ####################################################################################################################
    def remove_matched_functions(self, i):
        '''
        Remove a set of functions from the matched list and return them
        '''
        matched = self.matched_functions.pop(i)
        return matched
        
    ####################################################################################################################
    def mark_basic_block_matched(self,i, bb_a_index, bb_b_index, match_method):
        '''
        Mark a basic block in each function as matched
        '''
        (function_a, function_b) = self.matched_functions[i]
        
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].matched       = function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].matched = 1
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].match_method  = match_method
        function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].match_method  = match_method
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].matched_ea    = function_b.sorted_nodes()[bb_b_index].ea_start
        function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].matched_ea    = function_a.sorted_nodes()[bb_a_index].ea_start
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].matched_bb    = function_b.sorted_nodes()[bb_b_index]
        function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].matched_bb    = function_a.sorted_nodes()[bb_a_index]
        
        function_a.ext["PAIMEIDiffFunction"].num_bb_id += 1
        function_b.ext["PAIMEIDiffFunction"].num_bb_id += 1
        
        
        self.matched_functions[i] = (function_a, function_b)
        self.num_matched_basic_block +=1

     
    ####################################################################################################################        
    def mark_basic_block_ignored(self, i, bb_a_index, bb_b_index):
        '''
        Mark a basic block in two functions as ignored
        ''' 
        (function_a, function_b) = self.matched_functions[i]   
        if bb_a_index != -1:
            function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].ignore = 1
            function_a.ext["PAIMEIDiffFunction"].num_bb_id += 1
            
        if bb_b_index != -1:
            function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].ignore = 1
            function_b.ext["PAIMEIDiffFunction"].num_bb_id += 1    
            
        self.matched_functions[i] = (function_a, function_b)
        self.num_ignored_basic_block+=1
    
    ####################################################################################################################    
    def mark_function_as_different(self, i):
        '''
        Mark two matched functions as different
        '''
        (function_a, function_b) = self.matched_functions[i]   
        function_a.ext["PAIMEIDiffFunction"].different = function_b.ext["PAIMEIDiffFunction"].different = 1   
        self.parent.msg("%s != %s" % (function_a.name, function_b.name))     
        self.matched_functions[i] = (function_a, function_b)
        self.num_different_functions+=1
    
    ####################################################################################################################        
    def unmark_function_as_different(self, i):
        '''
        Mark two matched functions as different
        '''
        (function_a, function_b) = self.matched_functions[i]   
        function_a.ext["PAIMEIDiffFunction"].different = function_b.ext["PAIMEIDiffFunction"].different = 0        
        self.matched_functions[i] = (function_a, function_b)
        self.num_different_functions-=1
    
    ####################################################################################################################
    def mark_basic_block_as_different(self, i, bb_a_index, bb_b_index):
        '''
        Mark a basic block that has been matched as different
        '''        
        (function_a, function_b) = self.matched_functions[i]   
        function_a.sorted_nodes()[bb_a_index]["PAIMEIDiffBasicBlock"].different = function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].different = 1        
        self.matched_functions[i] = (function_a, function_b)

    ####################################################################################################################
    def unmatch_basic_block(self, i, bb_a_index):
        '''
        Mark a previously matched basic block as unmatched
        '''
        (function_a, function_b) = self.matched_functions[i]
        
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].matched       = function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].matched = 0
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].match_method  = ""
        function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].match_method  = ""
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].matched_ea    = 0
        function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].matched_ea    = 0
        function_a.sorted_nodes()[bb_a_index].ext["PAIMEIDiffBasicBlock"].matched_bb    = None
        function_b.sorted_nodes()[bb_b_index].ext["PAIMEIDiffBasicBlock"].matched_bb    = None
        self.matched_functions[i] = (function_a, function_b)

    ####################################################################################################################
    def unmatch_function(self, i):
        '''
        Mark a previously matched set of functions as unmatched and remove them from the list
        '''
        (function_a, function_b) = self.matched_functions[i]
        function_a.ext["PAIMEIDiffFunction"].matched = function_b.ext["PAIMEIDiffFunction"].matched = 0
        function_a.ext["PAIMEIDiffFunction"].match_method = ""
        function_b.ext["PAIMEIDiffFunction"].match_method = ""
        function_a.ext["PAIMEIDiffFunction"].matched_ea   = 0
        function_b.ext["PAIMEIDiffFunction"].matched_ea   = 0
        function_a.ext["PAIMEIDiffFunction"].matched_function = None
        function_b.ext["PAIMEIDiffFunction"].matched_function = None
        del self.matched_functions[i]
        self.num_matched_functions-=1
        return (function_a, function_b)


########NEW FILE########
__FILENAME__ = MatchedListCtrl
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: MatchedListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time


from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import wx.lib.mixins.listctrl as listmix

import FunctionViewDifferDlg

sys.path.append("..")

import pida

class MatchedListCtrl (wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.ColumnSorterMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES | wx.LC_SINGLE_SEL)
        self.top=top

        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.ColumnSorterMixin.__init__(self, 3)
        self.curr = -1
        
        self.itemDataMap = {}       
        
        self.InsertColumn(0,  "Function Name")
        self.InsertColumn(1,  "Start EA")
        self.InsertColumn(2,  "End EA")
        self.InsertColumn(3,  "Size")
        self.InsertColumn(4,  "Instruction Count")
        self.InsertColumn(5,  "BB Count")
        self.InsertColumn(6,  "Call Count")
        self.InsertColumn(7,  "Edge Count")
        self.InsertColumn(8,  "Match Method")
        self.InsertColumn(9,  "Match Value")
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick)

    ####################################################################################################################
    def SortListItems(self, col=-1, ascending=1): 
        pass
    ####################################################################################################################    
    def OnColClick(self,event):
        event.Skip()  
          
    
    ####################################################################################################################
    def add_function(self, func, idx):
        '''
        Add a function the matched list box
        '''
        if idx == -1:
            idx = self.GetItemCount()
        idx = self.GetItemCount()
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "%s" % func.name)
        self.SetStringItem(idx, 1, "0x%08x" % func.ea_start)
        self.SetStringItem(idx, 2, "0x%08x" % func.ea_end)
        self.SetStringItem(idx, 3, "%d" % func.ext["PAIMEIDiffFunction"].size)
        self.SetStringItem(idx, 4, "%d" % func.num_instructions)
        self.SetStringItem(idx, 5, "%d" % len(func.nodes))
        self.SetStringItem(idx, 6, "%d" % func.ext["PAIMEIDiffFunction"].num_calls)
        self.SetStringItem(idx, 7, "%d" % 1)
        self.SetStringItem(idx, 8, "%s" % func.ext["PAIMEIDiffFunction"].match_method)
        
        if "SPP" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "0x%08x" % func.ext["PAIMEIDiffFunction"].spp)
        elif "Smart MD5" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "%s" % func.ext["PAIMEIDiffFunction"].smart_md5)
        elif "NECI" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "%d:%d:%d:%d" % func.ext["PAIMEIDiffFunction"].neci)
        elif "Proximity" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "")
        elif "Name" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "%s" % func.name)
        elif "API Call" == func.ext["PAIMEIDiffFunction"].match_method:
            call_str = ""
            for call in func.ext["PAIMEIDiffFunction"].refs_api:
                (ea,s) = call
                if call_str == "":
                    call_str += s
                else:
                    call_str += ":" + s
            self.SetStringItem(idx, 9, "%s" % call_str)
        elif "Constants" == func.ext["PAIMEIDiffFunction"].match_method:
            const_str = ""
            for const_s in func.ext["PAIMEIDiffFunction"].refs_constants:
                if const_str == "":
                    const_str += str(const_s)
                else:
                    const_str += ":" + str(const_s)
            self.SetStringItem(idx, 9, "%s" % const_str)
        elif "CRC" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "0x%08x" % func.ext["PAIMEIDiffFunction"].crc)
        elif "Stack Frame" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "%d" % func.frame_size)
        elif "String References" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "")
        elif "Recursive Calls" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "")
        elif "Arg Var Size Count" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "%d:%d:%d:%d" % (func.arg_size, func.num_args, func.local_var_size, func.num_local_vars )  )
        elif "Call To Call From" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "")
        elif "Size" == func.ext["PAIMEIDiffFunction"].match_method:
            self.SetStringItem(idx, 9, "%d" % func.ext["PAIMEIDiffFunction"].size)
        
        self.itemDataMap[func.ea_start] = func.ea_start
        self.SetItemData(idx, func.ea_start)
                       
        if func.ext["PAIMEIDiffFunction"].different:
            item = self.GetItem(idx)
            item.SetTextColour(wx.RED)
            self.SetItem(item)
            
        #self.function_list.append( func )
         
    ####################################################################################################################         
    def OnRightClick(self, event):
        item = self.GetItem(self.curr)
        if not hasattr(self, "popupID1"):
            self.popupID1 = wx.NewId()
            self.popupID2 = wx.NewId()
            self.popupID3 = wx.NewId()
            self.popupID4 = wx.NewId()

            self.Bind(wx.EVT_MENU, self.view_match_diff_functions, id=self.popupID1)
            self.Bind(wx.EVT_MENU, self.unmatch_functions, id=self.popupID2)
            self.Bind(wx.EVT_MENU, self.unmark_different, id=self.popupID3)
            self.Bind(wx.EVT_MENU, self.mark_different, id=self.popupID4)

           

        # make a menu
        menu = wx.Menu()
        # add some items
        menu.Append(self.popupID1, "View Matched/Diff Functions")
        menu.Append(self.popupID2, "Unmatch Functions")
        menu.Append(self.popupID3, "Unmark as Different")        
        menu.Append(self.popupID4, "Mark as Different")


        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()
        
    ####################################################################################################################        
    def view_match_diff_functions(self, event):
        '''
        Display the matched/diffed functions dialog box
        '''
        dlg = FunctionViewDifferDlg.FunctionViewDifferDlg(parent=self.top)
        dlg.ShowModal()
        
    ####################################################################################################################
    def unmatch_functions(self, event):
        '''
        Unmatch selected function
        '''
        self.top.unmatch_function()

    ####################################################################################################################
    def mark_different(self, event):
        '''
        Mark selected function as different
        '''     
        item = self.top.MatchedBListCtrl.GetItem( self.top.MatchedAListCtrl.curr)
        item.SetTextColour(wx.RED)
        self.top.MatchedBListCtrl.SetItem(item)
        
        item = self.top.MatchedAListCtrl.GetItem( self.top.MatchedAListCtrl.curr)
        item.SetTextColour(wx.RED)
        self.top.MatchedAListCtrl.SetItem(item)
        
        self.top.matched_list.mark_function_as_different(self.top.MatchedAListCtrl.curr)
        


        
    ####################################################################################################################
    def unmark_different(self,event):
        '''
        Unmark selected function as different
        '''
        item = self.top.MatchedBListCtrl.GetItem( self.top.MatchedAListCtrl.curr)
        item.SetTextColour(wx.BLACK)
        self.top.MatchedBListCtrl.SetItem(item)
        
        item = self.top.MatchedAListCtrl.GetItem( self.top.MatchedAListCtrl.curr)
        item.SetTextColour(wx.BLACK)
        self.top.MatchedAListCtrl.SetItem(item)
        
        self.top.matched_list.unmark_function_as_different(self.top.MatchedAListCtrl.curr)
        

    ####################################################################################################################        
    def GetListCtrl(self):
        return self
########NEW FILE########
__FILENAME__ = ModuleDiffer

# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: ModuleDiffer.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import time
import wx

import pida

class ModuleDiffer:
    def __init__(self, parent):
        self.parent = parent
        
    ####################################################################################################################
    def diff_modules(self):
        i = 0
        idx = 0
        busy = wx.BusyInfo("Diffing basic blocks...stand by.")
        wx.Yield()
        start = time.time()
            
        while i < len(self.parent.used_diff_function_table):
#            print "Applying %s algorithm" % (sorted(self.parent.used_diff_function_table.keys())[i][1:])
            idx = 0
            while idx < len(self.parent.matched_list.matched_functions):
                (func_a,func_b) = self.parent.matched_list.matched_functions[idx]
                if func_a.ext["PAIMEIDiffFunction"].num_bb_id != len(func_a.sorted_nodes()) or func_b.ext["PAIMEIDiffFunction"].num_bb_id != len(func_b.sorted_nodes()):
                    if func_a.ext["PAIMEIDiffFunction"].spp != func_b.ext["PAIMEIDiffFunction"].spp and func_a.ext["PAIMEIDiffFunction"].smart_md5 != func_b.ext["PAIMEIDiffFunction"].smart_md5 and func_a.ext["PAIMEIDiffFunction"].neci != func_b.ext["PAIMEIDiffFunction"].neci:
                        if not func_a.ext["PAIMEIDiffFunction"].different and not func_b.ext["PAIMEIDiffFunction"].different and self.parent.used_diff_function_table[ sorted(self.parent.used_diff_function_table.keys())[i] ](func_a,func_b):
#                    if self.parent.used_diff_function_table[ sorted(self.parent.used_diff_function_table.keys())[i] ](func_a,func_b):
#                        print "Diff: %s %s marked as different due to %s" % (func_a.name, func_b.name, sorted(self.parent.used_diff_function_table.keys())[i][1:])
                            self.parent.matched_list.mark_function_as_different(idx)
#                        else:
#                            print "Passing due to not different on %s %s" % (func_a.name, func_b.name)
#                    else:
#                        print "Passing due to SSP or Smart MD5 on %s %s" % ( func_a.name, func_b.name)
#                else:
#                    print "Passing on %s (%d == %d) %s (%d == %d)" % (func_a.name,func_a.ext["PAIMEIDiffFunction"].num_bb_id,len(func_a.sorted_nodes()), func_b.name, func_b.ext["PAIMEIDiffFunction"].num_bb_id, len(func_b.sorted_nodes()))
                idx+=1
            i+=1
        self.parent.msg("Diffed module in %.2f seconds." % (round(time.time() - start, 3) ) ) 

########NEW FILE########
__FILENAME__ = ModuleMatcher
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: ModuleMatcher.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import time
import wx

import pida

class ModuleMatcher:
    def __init__(self, parent, mod_a, mod_b):
        self.parent = parent
        self.mod_a = mod_a # module a
        self.mod_b = mod_b # module b
        (self.ignore_num_nodes, self.ignore_num_edges, self.ignore_num_calls, self.ignore_num_instructions) = self.parent.insignificant_function
        self.ignore_bb = self.parent.insignificant_bb
        self.proximity_start = 0
    
    ####################################################################################################################        
    def prune_insig(self):
        '''
        remove the insignificant functions from the listing
        '''
        i = 0
        remove_count = 0
        
        while i < len(self.mod_a.nodes):
            if self.mod_a.nodes.values()[i].is_import:
                del self.mod_a.nodes[ self.mod_a.nodes.keys()[i] ]
                remove_count+=1
            elif self.is_function_insignificant(self.mod_a.nodes.values()[i]):
                del self.mod_a.nodes[ self.mod_a.nodes.keys()[i] ]
                remove_count+=1
            else:
                i+=1
        self.parent.msg("Removed %d insignificant functions from module a" % remove_count)
        
        i = 0
        remove_count = 0
        while i < len(self.mod_b.nodes):
            if self.mod_b.nodes.values()[i].is_import:
                del self.mod_b.nodes[ self.mod_b.nodes.keys()[i] ]
                remove_count+=1
            elif self.is_function_insignificant(self.mod_b.nodes.values()[i]):
                del self.mod_b.nodes[ self.mod_b.nodes.keys()[i] ]
                remove_count+=1
            else:
                i+=1        
        self.parent.msg("Removed %d insignificant functions from module b" % remove_count)
        
    ####################################################################################################################        
    def is_function_insignificant(self, function):
        if function.ext["PAIMEIDiffFunction"].num_calls <= self.ignore_num_calls and function.num_instructions <= self.ignore_num_instructions and len(function.nodes.values()) <= self.ignore_num_nodes:
            return 1
        else:
            return 0           
            
    ####################################################################################################################
    def match_modules(self):
        self.parent.msg("Before removing functions in a: %d" % len(self.mod_a.nodes))
        self.parent.msg("Before removing functions in b: %d" % len(self.mod_b.nodes))
        self.prune_insig()
        self.parent.msg("After removing functions in a: %d" % len(self.mod_a.nodes))
        self.parent.msg("After removing functions in b: %d" % len(self.mod_b.nodes))
        busy = wx.BusyInfo("matching modules...stand by.")
        wx.Yield()
        start = time.time()
        self.match_by_functions()
        
        self.parent.msg("matched %d function(s) in %.2f seconds." % (self.parent.matched_list.num_matched_functions, round(time.time() - start, 3) ) ) 
        busy = wx.BusyInfo("matching basic blocks...stand by.")
        wx.Yield()
        start = time.time()
        self.match_basic_block()
        self.parent.msg("matched %d basic block(s) and ignored %d basic block(s) in %.2f seconds." % (self.parent.matched_list.num_matched_basic_block, self.parent.matched_list.num_ignored_basic_block, round(time.time() - start, 3) ) ) 
        i = 0
        while i < len(self.mod_a.nodes.values()):
            self.parent.unmatched_list.add_to_unmatched_a(self.mod_a.nodes.values()[i])
            i+=1
        i = 0
        while i < len(self.mod_b.nodes.values()):
            self.parent.unmatched_list.add_to_unmatched_b(self.mod_b.nodes.values()[i])
            i+=1

    ####################################################################################################################
    def match_by_functions(self):
        curr_change = 0 # will keep track of the changes that have been found during the current iteration
        prev_change = 1 # will store the previous number of changes that occured in the last iteration
        match_num = found = dup = 0 # flags
        a = b = 0 # counter
        saved_a = saved_b = 0
        # while there is still a change
        
        num_functions = len(self.parent.used_match_function_table)
        match_functions = sorted(self.parent.used_match_function_table.keys())
        
        
        while prev_change != curr_change:
 #           print "Func: %d %d" % (prev_change, curr_change)
            i = 0               # reset counter
            prev_change = curr_change
            curr_change = 0     # reset counter
            
            # loop through all the algorithms
            while i < num_functions:
                    self.parent.msg("Method: %s" % match_functions[i][1:])
                    b = 0
                    # get the name of the algorithm
                    name = match_functions[i]
                    
                    # for all the functions in module b
                    while b < len(self.mod_b.nodes.values()):
                        a = 0            
                        
                        #for all the functions in module b
                        while a < len(self.mod_a.nodes.values()):
                            # match function_a to function_b 
                            if self.parent.used_match_function_table[ name ](self.mod_a.nodes.values()[a], self.mod_b.nodes.values()[b]):
                                # if we found a match to function b using function a then we save the state
                                if not dup:
                                    found = 1
                                    saved_a = a
                                    saved_b = b
                                    func_a = self.mod_a.nodes.values()[a]
                                    func_b = self.mod_b.nodes.values()[b]
                                    if self.parent.module_table[name [1:]].accuracy == 0x003:
                                        break
                                else:
                                    # if we have already found a match to function b and we find a second one
                                    # then we need to set the dup flag to indicate this iteration is invalid
                                    dup = 1 
                                    break
                            a+=1
                        
                        # if we found a match and there was no duplicated match then mark the functions as matched
                        if found and not dup:
                            curr_change+=1
                            # add functions to matched list
                            self.parent.matched_list.add_matched_function(func_a, func_b, name[1:])
                            key = self.mod_a.nodes.keys()[saved_a]
                            del self.mod_a.nodes[ key ]
                            key = self.mod_b.nodes.keys()[saved_b]
                            del self.mod_b.nodes[ key ]
                        else:
                            # we only add one to b if we did not find a match 
                            b+=1
                        found = dup = 0
                    
                    # after one complete iteration over all functions we call the proximity function                        
                    curr_change += self.match_function_by_proximity()
                    i+=1

    
    ####################################################################################################################
    def match_basic_block(self):
        
        i = idx = 0
        a = b =0
        dup = found = 0
        saved_a = saved_b = 0
        total_bb = 0
        prev_change = 1
        curr_change = 0
        
        #num_bb_matched = 0 
        #num_bb_a_ignored = 0
        #num_bb_b_ignored = 0
        
        match_basic_block_funcs = sorted(self.parent.used_match_basic_block_table.keys())
        num_functions = len(self.parent.used_match_basic_block_table)
        num_matched_functions =  len(self.parent.matched_list.matched_functions)
        
        while prev_change != curr_change:
            prev_change = curr_change
#            print "BB: %d %d" % (prev_change, curr_change)
            curr_change = 0
            idx = 0
            # for every pair of matched functions
            while idx < num_matched_functions:
                # get the functions
                (func_a, func_b) = self.parent.matched_list.matched_functions[idx]
                
                func_b_sorted_nodes = func_b.sorted_nodes()
                func_a_sorted_nodes = func_a.sorted_nodes()

                len_a = len(func_a_sorted_nodes)
                len_b = len(func_b_sorted_nodes)
                     
                #self.parent.msg("Matching basic blocks for %s:%d and %s:%d" % (func_a.name,len_a, func_b.name, len_b)) 
                
                
                #num_bb_matched = 0
                #num_bb_a_ignored = 0
                #num_bb_b_ignored = 0
                i = 0
                # loop through every basic block algorithm
                while i < num_functions:
                    if func_b.ext["PAIMEIDiffFunction"].num_bb_id == len_b or func_a.ext["PAIMEIDiffFunction"].num_bb_id == len_a:
                        break
                    # tell the user what method we are applying to the basic blocks
                    #self.parent.msg("BB Method: %s" % sorted(self.parent.used_match_basic_block_table.keys())[i][1:]) 
                    b = 0                            
                    # for all the basic blocks in function b
                    while b < len_b:
                        #print "B: %d" % b
                        if func_b.ext["PAIMEIDiffFunction"].num_bb_id == len_b:
                            break
                        a = 0

                        if func_b_sorted_nodes[b].ext["PAIMEIDiffBasicBlock"].ignore or func_b_sorted_nodes[b].ext["PAIMEIDiffBasicBlock"].matched:
                            b+=1
                            continue
                        elif func_b_sorted_nodes[b].num_instructions <= self.ignore_bb:
                            self.parent.matched_list.mark_basic_block_ignored(idx, -1, b)
                            b+=1
                            continue
                        elif func_b.ext["PAIMEIDiffFunction"].num_bb_id == len_b:
                            b+=1
                            break
                            
                        # for all basic blocks in function a                        
                        while a < len_a:
                            #print "A: %d" % a
                            if func_a.ext["PAIMEIDiffFunction"].num_bb_id == len_a:
                                break
                            #(func_a, func_b) = self.parent.matched_list.matched_functions[idx]
                            if func_a_sorted_nodes[a].ext["PAIMEIDiffBasicBlock"].ignore or func_a_sorted_nodes[a].ext["PAIMEIDiffBasicBlock"].matched:
                                a+=1
                                continue
                            elif func_a_sorted_nodes[a].num_instructions <= self.ignore_bb:
                                self.parent.matched_list.mark_basic_block_ignored(idx, a, -1)
                                a+=1
                                continue
                            elif func_a.ext["PAIMEIDiffFunction"].num_bb_id == len_a:
                                a+=1
                                break
                            
                            # call the basic block matching algorithm                                 
#                            if self.parent.used_match_basic_block_table[ sorted(self.parent.used_match_basic_block_table.keys())[i]](func_a.sorted_nodes()[a], func_b.sorted_nodes()[b]):
                            
                            if self.parent.used_match_basic_block_table[ match_basic_block_funcs[i] ](func_a_sorted_nodes[a], func_b_sorted_nodes[b]):
                                
                                # if there are no dups save state
                                if not dup:
                                    found = 1
                                    saved_a = a
                                    saved_b = b
                                else:
                                    # a previous match was found indicate there is a duplication
                                    dup = 1
                                    break
                            a+=1         
                        
                        # if a match was found and there was no duplication                                                           
                        if found and not dup:
                            #num_bb_matched += 1
                            curr_change += 1
                            # mark the basic block as matched
                            self.parent.matched_list.mark_basic_block_matched(idx, saved_a, saved_b, match_basic_block_funcs[i][1:] )
                            
                        found = dup = 0    
                        b+=1
                    #print "%s: a(%d + %d) == %d and %s: b(%d + %d) == %d" % (func_a.name, num_bb_a_ignored, num_bb_matched, len(func_a.sorted_nodes()), func_b.name, num_bb_b_ignored, num_bb_matched, len(func_b.sorted_nodes()))                                     
                    #self.parent.msg("Exiting i") 
                    i+=1           
                    #return
                    
                #self.parent.msg("Exiting idx") 
                idx+=1            
                #return
        
    ####################################################################################################################
    def is_basic_block_insignificant(self, func, i):
        if func.sorted_nodes()[i].ext["PAIMEIDiffBasicBlock"].ignore or func.sorted_nodes()[i].ext["PAIMEIDiffBasicBlock"].matched:
            return 1
            
        if func.sorted_nodes()[i].num_instructions <= self.ignore_bb:
            return 2

        if func.ext["PAIMEIDiffFunction"].num_bb_id == len(func.sorted_nodes()):
            return 3
        return 0
    
    ####################################################################################################################
    def match_function_by_proximity(self):
        '''
        take all matched functions and scan for calls within the functions, if we find a call to a function within the module
        we check to make sure function_b has the same call and then we take both functions that are called and considered them
        matched.

        @author: Peter Silberman
        '''
        
        matched_count = 0
        a = 0
        inst_list_a = []
        i = self.proximity_start
        #print "Entering proximity %d" % len(self.matched_functions)
        while i < len(self.parent.matched_list.matched_functions):
            function_a, function_b = self.parent.matched_list.matched_functions[i]
            #there are not same number of basic blocks ignore the function
            if len(function_a.nodes) != len(function_b.nodes):
                i+=1
                continue
            a = 0
            while a < len(function_a.nodes):
                inst_list_a = function_a.sorted_nodes()[a].sorted_instructions()
                if len(function_b.sorted_nodes()[a].sorted_instructions()) != len(inst_list_a):
                    break
                #print "Checking %s" % function_a.name
                inst_list_b = function_b.sorted_nodes()[a].sorted_instructions()
                for index_a,inst_a in enumerate(inst_list_a):
                    if inst_a.mnem == "call" and inst_a.refs_api == None:
                        #print "Found a call in %s at index %d" % (function_a.name, index_a)
                        proximity_from_entry = inst_a.ext["PAIMEIDiffInstruction"].distance_entry
                        proximity_from_exit  = inst_a.ext["PAIMEIDiffInstruction"].distance_exit
                        #print "Entry: %d Exit: %d index: %d" % (proximity_from_entry,proximity_from_exit, index_a)
                        #print "==> Entry: %d Exit: %d mnem: %s" % (inst_list_b[index_a].ext["PAIMEIDiffInstruction"].distance_entry, inst_list_b[index_a].ext["PAIMEIDiffInstruction"].distance_exit, inst_list_b[index_a].mnem)
                        #if inst_list_b[index_a].ext["PAIMEIDiffInstruction"].distance_entry == proximity_from_entry:
                        if inst_list_b[index_a].mnem == "call" and inst_list_b[index_a].refs_api == None:
                            new_function_a,key_a = self.get_function(self.mod_a, inst_a.op1)
                            #print "Looking for %s" % inst_a.op1
                            new_function_b,key_b = self.get_function(self.mod_b, inst_list_b[index_a].op1)
                            #print "Looking for %s" % inst_list_b[index_a].op1
                            if new_function_b != None and new_function_a != None:
                                self.parent.matched_list.matched_functions[i] = (function_a, function_b)
                                self.parent.matched_list.add_matched_function(new_function_a, new_function_b, "Proximity")
                                matched_count += 1
                                del self.mod_a.nodes[key_a]
                                del self.mod_b.nodes[key_b]
                            else:
                                break
                a+=1
            i+=1
        self.proximity_start += (i - self.proximity_start) 
        return matched_count
        
    ####################################################################################################################
    def get_function(self, module, function_name):
        '''
        get an instance of the function class given the function name and the module

        @author: Peter Silberman

        @type   module:  module
        @param  module:  module
        @type   function_name:  string
        @param  function_name:  the name of the function to get

        @rtype: tuple
        @return: None, or the function_a, and the index
        '''
        i = 0
        while i < len(module.nodes.values()):
            if module.nodes.values()[i].name == function_name:
                return (module.nodes.values()[i], module.nodes.keys()[i])
            i+=1
        return (None,None)
        
    
########NEW FILE########
__FILENAME__ = PAIMEIDiffBasicBlock
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: PAIMEIDiffBasicBlock.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import md5
import pida
import PAIMEIDiffInstruction



class PAIMEIDiffBasicBlock:
    def __init__(self, basic_block, function, bb_num, parent):
        self.pida_basic_block   = basic_block                           # reference to the pida basic block class                                                   
        self.pida_function      = function                              # reference to the pida function class
        
        self.spp                = 1                                     # initially spp value is given 1
        self.smart_md5          = ""            
        self.changed            = 0                                     # flag used in diffing    
        self.match_method       = ""                                    # method used to match the basic blocks
        self.matched            = 0                                     # flag used to indicated the basic block is matched
        self.matched_ea         = None                                  # the ea that corresponds to the match basic block
        self.matched_bb         = None                                  # a reference to the basic block class that this basic block as matched to
        self.ignore             = 0                                     # an ignore flag to indicate that the basic block is to be ignored
        self.different          = 0                                     # a flag to indicate the basic block is different
        self.num_calls          = 0                                     # number of calls in the basic block
        self.num_instructions   = 0                                     # number of instructions in the basic block
        self.refs_api           = []                                    # a list of api's referenced within the basic block
        self.refs_constants     = []                                    # a list of constants that are referenced within the basic block
        self.refs_vars          = []                                    # a list of vars referenced in the basic block
        self.refs_args          = []                                    # a list of args referenced in the basic block
        self.ea_end             = self.pida_basic_block.ea_end          # the ea end of the basic block
        self.ea_start           = self.pida_basic_block.ea_start        # the ea start of the basic block
        self.size               = self.pida_basic_block.ea_end - self.pida_basic_block.ea_start # the size of the basic block
        self.eci                = None                                  # the edge call instruction count
        self.crc                = 0xFFFFFFFFL                           # initially crc value
        self.refs_strings       = []                                    # a list of strings referenced in the basic block
        self.touched            = 0 
        self.parent             = parent
        
        index = bb_num
        
        self.num_instructions = self.pida_basic_block.num_instructions
        
        for ii in self.pida_basic_block.sorted_instructions():

            ii.ext["PAIMEIDiffInstruction"] = PAIMEIDiffInstruction.PAIMEIDiffInstruction(ii, self.pida_basic_block, self.pida_function)

            #Calculate spp
            self.spp *= ii.ext["PAIMEIDiffInstruction"].prime

            #Fill out distance entry/exit points
            ii.ext["PAIMEIDiffInstruction"].distance_entry = index
            ii.ext["PAIMEIDiffInstruction"].distance_exit = self.pida_function.num_instructions - index
            index+=1

            # count calls
            if ii.mnem == "call":
                self.num_calls +=1
            # store api calls
            if ii.refs_api:
                self.refs_api.append( ii.refs_api )
            # store constants
            if ii.refs_constant != None:
                self.refs_constants.append(ii.refs_constant)
            # store references to args
            if ii.refs_arg:
                self.refs_args.append(ii.refs_arg)
            # store references to vars
            if ii.refs_var:
                self.refs_vars.append(ii.refs_var)
            
            # store references to strings
            if ii.refs_string:
                self.refs_strings.append(ii.refs_string)
        
        # generate eci signature                
        self.eci = ( self.pida_function.edges_from(self.pida_basic_block.ea_start), self.num_calls, len(self.pida_basic_block.instructions.values()))
        
        # generate smart md5 signature
        self.generate_smart_md5()
        
        # calculate the crc signature
        #self.crc_calculate()
        
    ####################################################################################################################    
    def generate_smart_md5(self):
        '''
        Generate the smart md5 signature for the function
        '''
        alpha = []
        for inst in self.pida_basic_block.sorted_instructions():
            instruction = inst.mnem
            if len(instruction) <= 1 or instruction == "nop":
                continue
            elif instruction == "cmp" or instruction == "test":
                alpha.append("comparision")
            elif instruction[0] == "j":
                if instruction == "jg" or instruction == "jge" or instruction == "jl" or instruction == "jle" or instruction == "jng" or instruction == "jnge" or instruction == "jnl" or instruction == "jnle" or instruction == "jno" or instruction == "jns" or instruction == "jo" or instruction == "js":
                    alpha.append("jmp_signed")
                else:
                    alpha.append("jmp_unsigned")
            else:
                alpha.append(instruction)
        alpha.sort()
        digest_str = ""
        m = md5.new()
        for char in alpha:
            digest_str += char
        m.update( digest_str ) 
        self.smart_md5 = m.hexdigest()

        
    ####################################################################################################################
    def crc_calculate(self):
        '''
        Loop through the function and create to create CRC sig
        '''
        #for bb in self.pida_function.sorted_nodes():
        for inst in self.pida_basic_block.sorted_instructions():                    
            size = len(inst.bytes)
            i = 0
            while i < len(inst.bytes):
                byte = inst.bytes[i]
                self.crc = (self.crc >> 8) ^ self.parent.crc_table[ ( self.crc ^ byte ) & 0xFFL ]
                i+=1
        self.crc = self.crc ^ 0xFFFFFFFFL
########NEW FILE########
__FILENAME__ = PAIMEIDiffFunction
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: PAIMEIDiffFunction.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import PAIMEIDiffBasicBlock
import PAIMEIDiffInstruction
import pida
import time

class PAIMEIDiffFunction:
    def __init__(self, function, module, parent):
        self.pida_function      = function                  # a reference to the pida function class
        self.pida_module        = module                    # a reference to the pida module class
        self.matched            = 0                         # flag to indicate if the function was matched
        self.matched_ea         = None                      # stores the corresponding ea_start of the matched function
        self.matched_function   = None                      # stores the corresponding pida function class of the matched function
        self.match_method       = ""                        # the method used to match
        self.different          = 0                         # flag used to indicate if the function is different
        self.spp                = 1                         # the initial value of the SPP
        self.smart_md5          = ""                        # smart md5
        self.crc_table          = {}                        # the crc table 
        self.crc                = 0xFFFFFFFFL               # the crc signature of the whole function
        self.neci               = []                        # the neci of the function
        self.recursive          = []                        # not use atm
        self.num_calls          = 0                         # number of calls throughout the function
        self.size               = self.pida_function.ea_end - self.pida_function.ea_start   # size of the function
        self.refs_constants     = []                        # a list of constants referenced throughout the function
        self.refs_api           = []                        # a list of api calls referenced throughout the function
        self.refs_strings       = []                        # a list of strings referenced throughout the function
        self.num_bb_id          = 0                         # number of basic blocks identified and ignored

        count = 0
        self.crc_table = parent.crc_table
#        start = time.time()
        
        # fill in all the pertinent information needed for diffing
        for bb in self.pida_function.sorted_nodes():
            bb.ext["PAIMEIDiffBasicBlock"] = PAIMEIDiffBasicBlock.PAIMEIDiffBasicBlock(bb, self.pida_function, count, self)    
            self.smart_md5 += bb.ext["PAIMEIDiffBasicBlock"].smart_md5
            self.spp *= bb.ext["PAIMEIDiffBasicBlock"].spp
            count += len(bb.instructions)
            self.num_calls  += bb.ext["PAIMEIDiffBasicBlock"].num_calls
            if bb.ext["PAIMEIDiffBasicBlock"].refs_constants != None:
                for const in bb.ext["PAIMEIDiffBasicBlock"].refs_constants:
                    self.refs_constants.append( const )
            if bb.ext["PAIMEIDiffBasicBlock"].refs_api != None:
                for api in bb.ext["PAIMEIDiffBasicBlock"].refs_api:
                    self.refs_api.append( api )
            if bb.ext["PAIMEIDiffBasicBlock"].refs_strings != None:
                for s in bb.ext["PAIMEIDiffBasicBlock"].refs_strings:
                    self.refs_strings.append( s )


        self.neci = ( len(self.pida_function.nodes), len( self.pida_module.edges_from( self.pida_function.ea_start) ), self.num_calls, self.pida_function.num_instructions)
        self.crc_calculate()
#        parent.msg("Loaded %s PAIMEIDiffFunction in %.2f seconds." % (function.name, round(time.time() - start, 3) ) ) 

        
    ####################################################################################################################
    def crc_calculate(self):
        '''
        Loop through the function and create to create CRC sig
        '''
        crc = 0xFFFFFFFFL
        
        for bb in self.pida_function.sorted_nodes():
            crc = 0xFFFFFFFFL
            for inst in bb.sorted_instructions():                    
                size = len(inst.bytes)
                i = 0
                while i < len(inst.bytes):
                    byte = inst.bytes[i]
                    self.crc = (self.crc >> 8) ^ self.crc_table[ ( self.crc ^ byte ) & 0xFFL ]
                    crc = (crc >> 8) ^ self.crc_table[ ( crc ^ byte ) & 0xFFL ]
                    i+=1
            crc = crc ^ 0xFFFFFFFFL               
            bb.ext["PAIMEIDiffBasicBlock"].crc = crc
#            if bb.ext["PAIMEIDiffBasicBlock"].crc == crc:
#                print "CRC 0x%08x != CRC 0x%08x" % (crc, bb.ext["PAIMEIDiffBasicBlock"].crc)
        self.crc = self.crc ^ 0xFFFFFFFFL
########NEW FILE########
__FILENAME__ = PAIMEIDiffInstruction
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: PAIMEIDiffInstruction.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import pida


prime_numbers = \
[
    2,       3,    5,    7,   11,   13,   17,   19,   23,   29,   31,   37,   41,   43,   47,   53,   59,   61,
    67,     71,   73,   79,   83,   89,   97,  101,  103,  107,  109,  113,  127,  131,  137,  139,  149,  151,
    157,   163,  167,  173,  179,  181,  191,  193,  197,  199,  211,  223,  227,  229,  233,  239,  241,  251,
    257,   263,  269,  271,  277,  281,  283,  293,  307,  311,  313,  317,  331,  337,  347,  349,  353,  359,
    367,   373,  379,  383,  389,  397,  401,  409,  419,  421,  431,  433,  439,  443,  449,  457,  461,  463,
    467,   479,  487,  491,  499,  503,  509,  521,  523,  541,  547,  557,  563,  569,  571,  577,  587,  593,
    599,   601,  607,  613,  617,  619,  631,  641,  643,  647,  653,  659,  661,  673,  677,  683,  691,  701,
    709,   719,  727,  733,  739,  743,  751,  757,  761,  769,  773,  787,  797,  809,  811,  821,  823,  827,
    829,   839,  853,  857,  859,  863,  877,  881,  883,  887,  907,  911,  919,  929,  937,  941,  947,  953,
    967,   971,  977,  983,  991,  997, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063, 1069,
    1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163, 1171, 1181, 1187, 1193, 1201, 1213,
    1217, 1223, 1229, 1231, 1237, 1249, 1259, 1277, 1279, 1283, 1289, 1291, 1297, 1301, 1303, 1307, 1319, 1321,
    1327, 1361, 1367, 1373, 1381, 1399, 1409, 1423, 1427, 1429, 1433, 1439, 1447, 1451, 1453, 1459, 1471, 1481,
    1483, 1487, 1489, 1493, 1499, 1511, 1523, 1531, 1543, 1549, 1553, 1559, 1567, 1571, 1579, 1583, 1597, 1601,
    1607, 1609, 1613, 1619
]
#
#modified by Peter
#
prime_jmp_unsigned = 1949      
prime_jmp_signed   = 1987      
prime_cmp          = 1999 


class PAIMEIDiffInstruction:
    def __init__(self, inst, basic_block, func):
        self.pida_instruction       = inst              # reference to the original pida instruction class
        self.pida_basic_block       = basic_block       # reference to the original pida basic block class
        self.function               = func              # reference to the original pida function class
        self.prime                  = 1                 # set prime to 1
        self.match_method           = ""                # set our match method to nothing (may not be used)
        self.matched                = 0                 # set our matched flag to zero
        self.matched_ea             = None              # set our matched_ea to None or BADADDR
        self.matched_instruction    = None              # set our matched_instruction to None
        self.distance_entry         = None              # set our distance entry to None
        self.distance_exit          = None              # set our distance exit to None
        self.get_prime()                                # get the prime representation of this instruction

    ####################################################################################################################
    def get_prime(self):
        #if the instruction is <= 1 then its invalid and just set the prime to 1
        if len(self.pida_instruction.mnem) <= 1:
            self.prime = 1
        elif self.pida_instruction.mnem == "cmp" or self.pida_instruction.mnem == "test":
            self.prime = prime_cmp
        elif self.pida_instruction.mnem == "jmp" or self.pida_instruction.mnem == "ret" or self.pida_instruction.mnem == "retn":
            self.prime = 1
        elif self.pida_instruction.mnem[0] == "j":
            if self.pida_instruction.mnem == "jg" or self.pida_instruction.mnem == "jge" or self.pida_instruction.mnem == "jl" or self.pida_instruction.mnem == "jle" or self.pida_instruction.mnem == "jng" or self.pida_instruction.mnem == "jnge" or self.pida_instruction.mnem == "jnl" or self.pida_instruction.mnem == "jnle" or self.pida_instruction.mnem == "jno" or self.pida_instruction.mnem == "jns" or self.pida_instruction.mnem == "jo" or self.pida_instruction.mnem == "js":
                self.prime = prime_jmp_signed
            else:
                self.prime = prime_jmp_unsigned
        else:  
            self.prime = prime_numbers[ self.pida_instruction.bytes[0] ] 
########NEW FILE########
__FILENAME__ = PAIMEIDiffReport
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: PAIMEIDiffReport.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''


import sys
import os
import wx
from time import *

BEGIN_HTML =   "<HTML>\n" \
               "<HEAD>\n" \
               "<TITLE>\n" \
               "PAIMEIDiff v1.0\n" \
               "</TITLE>\n" \
               "</HEAD>\n" \
               "<BODY>\n" 

END_HTML = "</BODY>\n" \
           "</HTML>\n"

HEADER = "<center><h1>PAIMEIDiff %s Report %s</h1></center>\n"

BEGIN_TABLE = "<table border=%d borderwidth=%d><tr><td>\n"

BEGIN_TABLE_WIDTH = "<table border=%d borderwidth=%d width=%d><tr><td>\n"

BEGIN_TABLE_WIDTH_ALIGN = "<table border=%d borderwidth=%d width=%d align=%s><tr><td>\n"

END_TABLE = "</td>\n" \
            "</tr>\n" \
            "</table>\n"

BEGIN_TR = "<tr>\n"

BEGIN_TD = "<td>\n"

END_TR = "</tr>\n"

END_TD = "</td>\n"

FONT_SIZE = "<font face=%s size=%d>\n"

FONT_COLOR = "<font color=%s>\n"
                    
BR = "<br>\n"

HR = "<hr>\n"

PAR = "<p>\n"

BEGIN_BOLD = "<b>\n"

END_BOLD = "</b>\n"

BEGIN_ITALIC = "<i>\n"

END_ITALIC = "</i>\n"

BEGIN_LINK = "<a href=\"%s\">\n"

A_NAME = "<a name=\"%s\">\n"

END_LINK = "</a>\n"

BEGIN_LIST = "<ul>\n"

END_LIST = "</ul>\n"

BEGIN_LI = "<li>\n"

END_LI = "</li>\n"



default_integer_color = "red"

default_font_color = "black"

default_address_color = "green"

default_disasm_color = "blue"

class PAIMEIDiffReport:
    def __init__(self, parent, path):
        self.parent = parent
        self.report_name = ""
        self.path = path

    ####################################################################################################################
    def generate_unmatched_b(self):
        name = self.path + self.parent.module_b_name + "_unmatched_b.html"
        out_file = open(name, "w")
        out_file.write(BEGIN_HTML)
        time_date = strftime("%a %b %d %H:%M:%S %Y",gmtime())
        out_file.write(HEADER % (self.parent.module_b_name,time_date) )
        #start main
        out_file.write(BEGIN_TABLE % (0,0) )
        
        #setup menu
        out_file.write(BEGIN_TABLE % (0,0) )
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + ".html") )
        out_file.write( "Matched" + END_LINK + BR)
        #write link to Un-Matched A
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + "_unmatched_a.html") )
        out_file.write( "Un-Matched A" + END_LINK + BR)
        #write link to Un-Matched B
        out_file.write( BEGIN_BOLD + "Un-Matched B" + END_BOLD + BR)
        #write link to Statistics
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + "_statistics.html" ))
        out_file.write( "Statistics" + END_LINK + BR)
        #end table
        out_file.write(END_TABLE)
        
        #write </td><td>
        out_file.write(END_TD + BEGIN_TD)
        
        #write module table
        out_file.write(BEGIN_TABLE_WIDTH % (0,0,600))
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write("Un-Matched Module B (%s) Functions" % self.parent.module_b_name) 
        out_file.write(END_TD + END_TR)
        #loop through all the matched function names
        for func_b in self.parent.UnMatchedBListCtrl.function_list:
            out_file.write(BEGIN_TR + BEGIN_TD)
            out_file.write(BEGIN_LINK % ("#" + func_b.name))
            out_file.write(FONT_SIZE % ("Tahoma",2) )
            out_file.write("%s" % func_b.name)
            out_file.write(END_LINK)
            out_file.write(END_TD + END_TR)
            
        out_file.write(END_TABLE)
        #end main table
        out_file.write(END_TABLE)
        i = 0
        while i < len( self.parent.UnMatchedBListCtrl.function_list):
            func_b =  self.parent.UnMatchedBListCtrl.function_list[i]
            out_file.write(BEGIN_TABLE_WIDTH_ALIGN % (0,0,600,"center") )
            out_file.writelines( self.generate_function_header(func_b))
            out_file.write( END_TD + END_TR)
            out_file.write(HR)
            a=0
            for bb in func_b.sorted_nodes():
                out_file.write(BEGIN_TR + BEGIN_TD)
                out_file.writelines( self.generate_bb_header(bb) )
                out_file.write(END_TD + END_TR + BEGIN_TR + BEGIN_TD)
                out_file.writelines( self.generate_instruction_text( bb) )
                out_file.write(END_TD + END_TR)
                a+=1
            i+=1
        out_file.write(END_TABLE)
        out_file.write(END_HTML)
        out_file.close()
    
    ####################################################################################################################
    def generate_unmatched_a(self):
        name = self.path + self.parent.module_a_name + "_unmatched_a.html"
        out_file = open(name, "w")
        out_file.write(BEGIN_HTML)
        time_date = strftime("%a %b %d %H:%M:%S %Y",gmtime())
        out_file.write(HEADER % (self.parent.module_a_name,time_date) )
        #start main
        out_file.write(BEGIN_TABLE % (0,0) )
        
        #setup menu
        out_file.write(BEGIN_TABLE % (0,0) )
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + ".html") )
        out_file.write( "Matched" + END_LINK + BR)
        #write link to Un-Matched A
        out_file.write( BEGIN_BOLD + "Un-Matched A" + END_BOLD + BR)
        #write link to Un-Matched B
        out_file.write( BEGIN_LINK % (self.parent.module_b_name + "_unmatched_b.html") )
        out_file.write( "Un-Matched B" + END_LINK + BR)
        #write link to Statistics
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + "_statistics.html" ))
        out_file.write( "Statistics" + END_LINK + BR)
        #end table
        out_file.write(END_TABLE)
        
        #write </td><td>
        out_file.write(END_TD + BEGIN_TD)
        
        #write module table
        out_file.write(BEGIN_TABLE_WIDTH % (0,0,600))
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write("Un-Matched Module A (%s) Functions" % self.parent.module_a_name) 
        out_file.write(END_TD + END_TR)
        #loop through all the matched function names
        for func_a in  self.parent.UnMatchedAListCtrl.function_list:
            out_file.write(BEGIN_TR + BEGIN_TD)
            out_file.write(BEGIN_LINK % ("#" + func_a.name))
            out_file.write(FONT_SIZE % ("Tahoma",2) )
            out_file.write("%s" % func_a.name)
            out_file.write(END_LINK)
            out_file.write(END_TD + END_TR)
            
        out_file.write(END_TABLE)
        #end main table
        out_file.write(END_TABLE)
        i = 0
        while i < len( self.parent.UnMatchedAListCtrl.function_list):
            func_a = self.parent.UnMatchedAListCtrl.function_list[i]
    
            out_file.write(BEGIN_TABLE_WIDTH_ALIGN % (0,0,600,"center") )
            out_file.writelines( self.generate_function_header(func_a))
            out_file.write( END_TD + END_TR)
            out_file.write(HR)
            a=0
            for bb in func_a.sorted_nodes():
                out_file.write(BEGIN_TR + BEGIN_TD)
                out_file.writelines( self.generate_bb_header(bb) )
                out_file.write(END_TD + END_TR + BEGIN_TR + BEGIN_TD)
                out_file.writelines( self.generate_instruction_text( bb) )
                out_file.write(END_TD + END_TR)
                a+=1
            i+=1
        out_file.write(END_TABLE)
        out_file.write(END_HTML)
        out_file.close()
    ####################################################################################################################
    def generate_report(self):
        self.report_name = self.path + "%s.html" % self.parent.module_a_name
        out_file = open(self.report_name, "w")
        out_file.write(BEGIN_HTML)
        time_date = strftime("%a %b %d %H:%M:%S %Y",gmtime())
        out_file.write(HEADER % (self.parent.module_a_name,time_date) )
        #start main
        out_file.write(BEGIN_TABLE % (0,0) )
        
        #setup menu
        out_file.write(BEGIN_TABLE % (0,0) )
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write( BEGIN_BOLD + "Matched" + END_BOLD + BR)
        #write link to Un-Matched A
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + "_unmatched_a.html") )
        out_file.write( "Un-Matched A" + END_LINK + BR)
        #write link to Un-Matched B
        out_file.write( BEGIN_LINK % (self.parent.module_b_name + "_unmatched_b.html") )
        out_file.write( "Un-Matched B" + END_LINK + BR)
        #write link to Statistics
        out_file.write( BEGIN_LINK % (self.parent.module_a_name + "_statistics.html" ))
        out_file.write( "Statistics" + END_LINK + BR)
        #end table
        out_file.write(END_TABLE)
        
        #write </td><td>
        out_file.write(END_TD + BEGIN_TD)
        
        #write module table
        out_file.write(BEGIN_TABLE_WIDTH % (0,0,600))
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write("Matched Module A (%s) Functions" % self.parent.module_a_name) 
        out_file.write(END_TD + BEGIN_TD)
        out_file.write(FONT_SIZE % ("Tahoma",2) )
        out_file.write("Matched Module B (%s) Functions" % self.parent.module_b_name)
        out_file.write(END_TD + END_TR)
        #loop through all the matched function names
        for (func_a,func_b) in self.parent.matched_list.matched_functions:
            out_file.write(BEGIN_TR + BEGIN_TD)
            out_file.write(BEGIN_LINK % ("#" + func_a.name))
            out_file.write(FONT_SIZE % ("Tahoma",2) )
            if func_a.ext["PAIMEIDiffFunction"].different:
                out_file.write("%s" % (func_a.name + "-DIFFERENT"))
            else:
                out_file.write("%s" % func_a.name)
            out_file.write(END_LINK)
            out_file.write(END_TD + BEGIN_TD)
            out_file.write(BEGIN_LINK % ("#" + func_a.name))
            out_file.write(FONT_SIZE % ("Tahoma",2) )
            if func_a.ext["PAIMEIDiffFunction"].different:
                out_file.write("%s" % (func_b.name + "-DIFFERENT"))
            else:
                out_file.write("%s" % func_b.name)
            out_file.write(END_LINK)
            out_file.write(END_TD + END_TR)
            
        out_file.write(END_TABLE)
        
        out_file.write(END_TD + END_TR + BEGIN_TR + BEGIN_TD)
        #end main table
        out_file.write(END_TABLE)
        i = 0
        a = 0
        b = 0
        bb_count = 0
        while i < len(self.parent.matched_list.matched_functions):
            out_file.write(BEGIN_TABLE_WIDTH_ALIGN % (0,0,600,"center"))
        
            func_a,func_b = self.parent.matched_list.matched_functions[i]
            out_file.write(BEGIN_TABLE_WIDTH_ALIGN % (0,0,600,"center") )
            out_file.writelines( self.generate_function_header(func_a) )    
            out_file.write(END_TD + END_TR)     
            for bb in func_a.sorted_nodes():
                out_file.write(BEGIN_TR + BEGIN_TD)
                out_file.writelines(self.generate_bb_header(bb))
                out_file.write(END_TD + END_TR + BEGIN_TR + BEGIN_TD)
                out_file.writelines(self.generate_instruction_text(bb))
                out_file.write(END_TD + END_TR)
            out_file.write(END_TABLE)
            
            out_file.write(END_TD + BEGIN_TD)
            
            out_file.write(BEGIN_TABLE_WIDTH_ALIGN % (0,0,600,"center") )
            out_file.writelines( self.generate_function_header(func_b) )    
            out_file.write(END_TD + END_TR) 
            for bb in func_b.sorted_nodes():
                out_file.write(BEGIN_TR + BEGIN_TD)
                out_file.writelines(self.generate_bb_header(bb))
                out_file.write(END_TD + END_TR + BEGIN_TR + BEGIN_TD)
                out_file.writelines(self.generate_instruction_text(bb))
                out_file.write(END_TD + END_TR)
            out_file.write(END_TABLE)
                       
            out_file.write(END_TABLE)
            i+=1
            
                
        out_file.write(END_HTML)
        out_file.close()
        self.generate_unmatched_a()
        self.generate_unmatched_b()
    
    ################################################################################################################
    def get_unmatched_bb(self, func):
        i = 0
        while i < len(func.nodes.values()):
            if not func.nodes.values()[i].ext["PAIMEIDiffBasicBlock"].touched:
                if not func.nodes.values()[i].ext["PAIMEIDiffBasicBlock"].matched or func.nodes.values()[i].ext["PAIMEIDiffBasicBlock"].ignore:
                    func.nodes.values()[i].ext["PAIMEIDiffBasicBlock"].touched = 1
                    return func.nodes.values()[i]
            i+=1
        return None
        
    ####################################################################################################################
    def generate_function_header(self, func):
        lines = []
        lines.append( FONT_SIZE % ("Tahoma",2))
        lines.append(A_NAME % func.name)
        lines.append(END_LINK)
        if not func.ext["PAIMEIDiffFunction"].different:
            lines.append( "<h2>" + BEGIN_BOLD + func.name + END_BOLD + "</h2>" + BR)
        else:
            lines.append( "<h2>" + BEGIN_BOLD + func.name + "-DIFFERENT"+ END_BOLD + "</h2>" + BR)
        lines.append(BEGIN_LIST)
        
        lines.append( BEGIN_LI + "BB Count: " + FONT_COLOR % default_integer_color)
        lines.append( "%d" % len(func.nodes.values()))
        lines.append(FONT_COLOR  % default_font_color)
        lines.append(END_LI)
        
        lines.append( BEGIN_LI + "Instruction Count: " + FONT_COLOR % default_integer_color)
        lines.append("%d" % func.num_instructions)
        lines.append(FONT_COLOR % default_font_color)
        lines.append( END_LI)
        
        lines.append( BEGIN_LI + "Call Count: " + FONT_COLOR % default_integer_color)
        lines.append("%d" % func.ext["PAIMEIDiffFunction"].num_calls)
        lines.append(FONT_COLOR % default_font_color)
        lines.append(END_LI)
        
        lines.append( BEGIN_LI + "Size: " + FONT_COLOR % default_integer_color)
        lines.append("%d" % func.ext["PAIMEIDiffFunction"].size)
        lines.append(FONT_COLOR % default_font_color)
        lines.append(END_LI)
        
        lines.append(END_LIST)
        return lines
        
    ####################################################################################################################
    def generate_bb_header(self, bb):
        lines = []
        lines.append(FONT_SIZE % ("Tahoma",1) )
        lines.append(A_NAME % ( str(bb.ea_start) ) )
        lines.append(END_LINK)
        
        lines.append("Instruction Count: " + FONT_COLOR % default_integer_color)
        lines.append("%d" % bb.num_instructions)
        lines.append(FONT_COLOR % default_font_color)
        lines.append(BR)
        
        lines.append("Call Count: " + FONT_COLOR % default_integer_color)
        lines.append("%d" % bb.ext["PAIMEIDiffBasicBlock"].num_calls)
        lines.append(FONT_COLOR % default_font_color)
        lines.append(BR)
        
        lines.append("Size: " + FONT_COLOR % default_integer_color)
        lines.append("%d" % bb.ext["PAIMEIDiffBasicBlock"].size)
        lines.append(FONT_COLOR % default_font_color)
        lines.append(BR)

        return lines
        
    ####################################################################################################################
    def generate_instruction_text(self, bb):
        lines = []
        lines.append(FONT_SIZE % ("Tahoma",2) )
        for inst in bb.sorted_instructions():
            if bb.ext["PAIMEIDiffBasicBlock"].ignore or bb.num_instructions <= self.parent.insignificant_bb:
                lines.append(FONT_COLOR % "DarkGray")
                lines.append("0x%08x\n" % inst.ea)
                lines.append(FONT_COLOR % "DarkGray")
                lines.append("%s\n" %inst.disasm)
                lines.append(BR)
            elif not bb.ext["PAIMEIDiffBasicBlock"].matched:
                lines.append(FONT_COLOR % "red")
                lines.append("0x%08x\n" % inst.ea)
                lines.append(FONT_COLOR % "red")
                lines.append("%s\n" %inst.disasm)
                lines.append(BR)
            else:
                lines.append(FONT_COLOR % default_address_color)
                lines.append("0x%08x\n" % inst.ea)
                lines.append(FONT_COLOR % default_disasm_color)
                lines.append("%s\n" %inst.disasm)
                lines.append(BR)
            
        return lines
        
########NEW FILE########
__FILENAME__ = UnmatchedList
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: UnmatchedList.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

class UnmatchedList:
    def __init__(self):
        self.unmatched_module_a = []
        self.unmatched_module_b = []

    ####################################################################################################################    
    def add_to_unmatched_a(self, func):
        self.unmatched_module_a.append(func)

    ####################################################################################################################
    def add_to_unmatched_b(self, func):
        self.unmatched_module_b.append(func)

    ####################################################################################################################
    def remove_unmatched_a(self, i):
        func = self.unmatched_module_a[ i ]
        del self.unmatched_module_a[ i ]
        return func

    ####################################################################################################################
    def remove_unmatched_b(self, i):
        func = self.unmatched_module_b[ i ]
        del self.unmatched_module_b[ i ]
        return func
        

            

########NEW FILE########
__FILENAME__ = UnmatchedListCtrl
#
# PAIMEIdiff
# Copyright (C) 2006 Peter Silberman <peter.silberman@gmail.com>
#
# $Id: UnmatchedListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Peter Silberman
@license:      GNU General Public License 2.0 or later
@contact:      peter.silberman@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

import FunctionViewDlg

sys.path.append("..")


import pida

class UnmatchedListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES | wx.LC_SINGLE_SEL)
        self.top=top
        
        ListCtrlAutoWidthMixin.__init__(self)
        
        self.curr = -1
        
        self.function_list = []

        self.InsertColumn(0,  "Function Name")
        self.InsertColumn(1,  "Start EA")
        self.InsertColumn(2,  "End EA")
        self.InsertColumn(3,  "Size")
        self.InsertColumn(4,  "Instruction Count")
        self.InsertColumn(5,  "BB Count")
        self.InsertColumn(6,  "Call Count")
        self.InsertColumn(7,  "Edge Count")

    ####################################################################################################################
    def OnRightClick(self, event):
        if not hasattr(self, "popupID1"):
            self.popupID1 = wx.NewId()
            self.popupID2 = wx.NewId()
    

            self.Bind(wx.EVT_MENU, self.match_function, id=self.popupID1)
            self.Bind(wx.EVT_MENU, self.view_function, id=self.popupID2)
  

        # make a menu
        menu = wx.Menu()
        # add some items
        menu.Append(self.popupID1, "Manually Match Function")
        menu.Append(self.popupID2, "View Function")
 

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()

    ####################################################################################################################
    def add_function(self, func, idx):
        '''
        Add function to list ctrl
        '''
        if idx == -1:
            idx = self.GetItemCount()
        self.InsertStringItem(idx, "")
        self.SetStringItem(idx, 0, "%s" % func.name)
        self.SetStringItem(idx, 1, "0x%08x" % func.ea_start)
        self.SetStringItem(idx, 2, "0x%08x" % func.ea_end)
        self.SetStringItem(idx, 3, "%d" % func.ext["PAIMEIDiffFunction"].size)
        self.SetStringItem(idx, 4, "%d" % func.num_instructions)
        self.SetStringItem(idx, 5, "%d" % len(func.nodes))
        self.SetStringItem(idx, 6, "%d" % func.ext["PAIMEIDiffFunction"].num_calls)
        self.SetStringItem(idx, 7, "%d" % 1)
        self.function_list.append( func )
    
    ####################################################################################################################
    def match_function(self, event):
        '''
        match the function manually
        '''
        self.top.manual_match_function()
        
    ####################################################################################################################
    def view_function(self,event):
        dlg = FunctionViewDlg.FunctionViewDlg(parent=self)
        dlg.ShowModal()
        
########NEW FILE########
__FILENAME__ = ExplorerTreeCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: ExplorerTreeCtrl.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import re
import MySQLdb

import pida

class ExplorerTreeCtrl (wx.TreeCtrl):
    '''
    Our custom tree control.
    '''

    def __init__ (self, parent, id, pos=None, size=None, style=None, top=None):
        wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
        self.top            = top
        self.selected       = None
        self.used_for_stalk = None

        # setup our custom tree list control.
        self.icon_list        = wx.ImageList(16, 16)
        self.icon_folder      = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, (16, 16)))
        self.icon_folder_open = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER, (16, 16)))
        self.icon_tag         = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16, 16)))
        self.icon_selected    = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FIND,        wx.ART_OTHER, (16, 16)))
        self.icon_filtered    = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_CUT,         wx.ART_OTHER, (16, 16)))

        self.SetImageList(self.icon_list)

        self.root = self.AddRoot("Modules")
        self.SetPyData(self.root, None)
        self.SetItemImage(self.root, self.icon_folder,      wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root, self.icon_folder_open, wx.TreeItemIcon_Expanded)


    ####################################################################################################################
    def on_item_activated (self, event):
        '''
        Make record of the selected target/tag combination.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)

        # module selected.
        if type(selected) == pida.module:
            pass

        # function selected.
        elif type(selected) == pida.function:
            disasm = """
            <html>
                <body text=#eeeeee bgcolor=#000000>
                <font size=4><b>%s</b></font>
                <font face=courier size=2>
            """ % (selected.name)

            for bb in selected.sorted_nodes():
                disasm += "<p>"

                # chunked block.
                if selected.ea_start > bb.ea_start > selected.ea_end:
                    disasm += "<font color=blue>CHUNKED BLOCK --------------------</font><br>"

                for ins in bb.sorted_instructions():
                    ins_disasm = ins.disasm
                    ins_disasm = re.sub("(?P<op>^j..?)\s", "<font color=yellow>\g<op> </font>", ins_disasm)
                    ins_disasm = re.sub("(?P<op>^call)\s", "<font color=red>\g<op> </font>",    ins_disasm)

                    disasm += "<font color=#999999>%08x</font>&nbsp;&nbsp;%s<br>" % (ins.ea, ins_disasm)

            disasm += "</font></body></html>"

            self.top.disassembly.SetPage(disasm)

        # basic block selected.
        elif type(selected) == pida.basic_block:
            pass


    ####################################################################################################################
    def on_item_right_click (self, event):
        if not self.selected:
            return

        if not self.x or not self.y:
            return

        selected = self.GetPyData(self.selected)

        ###
        ### root node.
        ###

        if selected == None:
            return

        ###
        ### module node.
        ###

        elif type(selected) == pida.module:
            # we only have to do this once, that is what the hasattr() check is for.
            if not hasattr(self, "right_click_popup_remove_module"):
                self.right_click_popup_remove_module = wx.NewId()

                self.Bind(wx.EVT_MENU, self.on_right_click_popup_remove_module, id=self.right_click_popup_remove_module)

            # make a menu.
            menu = wx.Menu()
            menu.Append(self.right_click_popup_remove_module, "Remove Module")

            self.PopupMenu(menu, (self.x, self.y))
            menu.Destroy()

        ###
        ### function node.
        ###

        elif type(selected) == pida.function:
            # we only have to do this once, that is what the hasattr() check is for.
            if not hasattr(self, "right_click_popup_graph_function"):
                self.right_click_popup_graph_function = wx.NewId()

                self.Bind(wx.EVT_MENU, self.on_right_click_popup_graph_function, id=self.right_click_popup_graph_function)

            # make a menu.
            menu = wx.Menu()
            menu.Append(self.right_click_popup_graph_function, "Graph Function")

            self.PopupMenu(menu, (self.x, self.y))
            menu.Destroy()

        ###
        ### basic block node.
        ###

        elif type(selected) == pida.function:
            return


    ####################################################################################################################
    def on_item_right_down (self, event):
        '''
        Grab the x/y coordinates when the right mouse button is clicked.
        '''

        self.x = event.GetX()
        self.y = event.GetY()

        item, flags = self.HitTest((self.x, self.y))

        if flags & wx.TREE_HITTEST_ONITEM:
            self.SelectItem(item)
        else:
            self.x = None
            self.y = None


    ####################################################################################################################
    def on_item_sel_changed (self, event):
        '''
        Update the current selected tree control item on every selection change.
        '''

        self.selected = event.GetItem()


    ####################################################################################################################
    def load_module (self, module_name):
        '''
        Load the specified module into the tree.
        '''

        tree_module = self.AppendItem(self.root, module_name)
        self.SetPyData(tree_module, self.top.pida_modules[module_name])
        self.SetItemImage(tree_module, self.icon_folder,      wx.TreeItemIcon_Normal)
        self.SetItemImage(tree_module, self.icon_folder_open, wx.TreeItemIcon_Expanded)

        sorted_functions = [f.ea_start for f in self.top.pida_modules[module_name].nodes.values() if not f.is_import]
        sorted_functions.sort()

        for func_key in sorted_functions:
            function = self.top.pida_modules[module_name].nodes[func_key]
            
            tree_function = self.AppendItem(tree_module, "%08x - %s" % (function.ea_start, function.name))
            self.SetPyData(tree_function, self.top.pida_modules[module_name].nodes[func_key])
            self.SetItemImage(tree_function, self.icon_folder,      wx.TreeItemIcon_Normal)
            self.SetItemImage(tree_function, self.icon_folder_open, wx.TreeItemIcon_Expanded)

            sorted_bbs = function.nodes.keys()
            sorted_bbs.sort()

            for bb_key in sorted_bbs:
                bb = function.nodes[bb_key]

                tree_bb = self.AppendItem(tree_function, "%08x" % bb.ea_start)
                self.SetPyData(tree_bb, function.nodes[bb_key])
                self.SetItemImage(tree_bb, self.icon_tag, wx.TreeItemIcon_Normal)

        self.Expand(self.root)


    ####################################################################################################################
    def on_right_click_popup_graph_function (self, event):
        '''
        Right click event handler for popup add graph function menu selection.
        '''

        if not self.selected:
            return

        selected  = self.GetPyData(self.selected)
        udraw     = self.top.main_frame.udraw

        if not udraw:
            self.top.err("No available connection to uDraw(Graph) server.")
            return

        try:
            udraw.graph_new(selected)
        except:
            self.top.main_frame.udraw = None
            self.top.err("Connection to uDraw(Graph) server severed.")


    ####################################################################################################################
    def on_right_click_popup_remove_module (self, event):
        '''
        Right click event handler for popup add remove module menu selection.
        '''

        if not self.selected:
            return

        self.DeleteChildren(self.selected)
        self.Delete(self.selected)
########NEW FILE########
__FILENAME__ = HtmlWindow
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: HtmlWindow.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.html as html

class HtmlWindow (html.HtmlWindow):
    def __init__ (self, parent, id, pos=None, size=None, style=None, top=None):
        html.HtmlWindow.__init__(self, parent, id, style=style)
        self.top = top

        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)


    ####################################################################################################################
    def on_scroll (self, event):
        event.Skip()

########NEW FILE########
__FILENAME__ = PIDAModulesListCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PIDAModulesListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

sys.path.append("..")

import pida

class PIDAModulesListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES )
        self.top=top

        ListCtrlAutoWidthMixin.__init__(self)

        self.InsertColumn(0,  "# Func")
        self.InsertColumn(1,  "# BB")
        self.InsertColumn(2,  "PIDA Module")

    ####################################################################################################################
    def on_activated (self, event):
        '''
        Load the PIDA module into the browser tree ctrl.
        '''

        idx    = self.GetFirstSelected()
        module = self.GetItem(idx, 2).GetText()

        self.top.explorer.load_module(module)


    ####################################################################################################################
    def on_add_module (self, event):
        '''
        Load a PIDA module into memory.
        '''

        dlg = wx.FileDialog(                                    \
            self,                                               \
            message     = "Select PIDA module",                 \
            defaultDir  = os.getcwd(),                          \
            defaultFile = "",                                   \
            wildcard    = "*.PIDA",                             \
            style       = wx.OPEN | wx.CHANGE_DIR | wx.MULTIPLE \
        )

        if dlg.ShowModal() != wx.ID_OK:
            return

        for path in dlg.GetPaths():
            try:
                module_name = path[path.rfind("\\")+1:path.rfind(".pida")].lower()

                if self.top.pida_modules.has_key(module_name):
                    self.top.err("Module %s already loaded ... skipping." % module_name)
                    continue

                # deprecated - replaced by progress dialog.
                #busy = wx.BusyInfo("Loading %s ... stand by." % module_name)
                #wx.Yield()

                start  = time.time()
                module = pida.load(path, progress_bar="wx")

                if not module:
                    self.top.msg("Loading of PIDA module '%s' cancelled by user." % module_name)
                    return

                else:
                    self.top.pida_modules[module_name] = module
                    self.top.msg("Loaded PIDA module '%s' in %.2f seconds." % (module_name, round(time.time() - start, 3)))

                # determine the function and basic block counts for this module.
                function_count    = len(self.top.pida_modules[module_name].nodes)
                basic_block_count = 0

                for function in self.top.pida_modules[module_name].nodes.values():
                    basic_block_count += len(function.nodes)

                idx = len(self.top.pida_modules) - 1
                self.InsertStringItem(idx, "")
                self.SetStringItem(idx, 0, "%d" % function_count)
                self.SetStringItem(idx, 1, "%d" % basic_block_count)
                self.SetStringItem(idx, 2, module_name)

                self.SetColumnWidth(2, wx.LIST_AUTOSIZE)
            except:
                self.top.err("FAILED LOADING MODULE: %s. Possibly corrupt or version mismatch?" % module_name)
                if self.top.pida_modules.has_key(module_name):
                    del(self.top.pida_modules[module_name])


    ####################################################################################################################
    def on_right_click (self, event):
        '''
        When an item in the PIDA module list is right clicked, display a context menu.
        '''

        if not self.x or not self.y:
            return

        # we only have to do this once, that is what the hasattr() check is for.
        if not hasattr(self, "right_click_popup_remove"):
            self.right_click_popup_remove = wx.NewId()
            self.Bind(wx.EVT_MENU, self.on_right_click_popup_remove, id=self.right_click_popup_remove)

        # make a menu.
        menu = wx.Menu()
        menu.Append(self.right_click_popup_remove, "Remove")

        self.PopupMenu(menu, (self.x, self.y))
        menu.Destroy()


    ####################################################################################################################
    def on_right_click_popup_remove (self, event):
        '''
        Right click event handler for popup remove menu selection.
        '''

        idx    = self.GetFirstSelected()
        module = self.GetItem(idx, 2).GetText()

        del(self.top.pida_modules[module])
        self.DeleteItem(idx)


    ####################################################################################################################
    def on_right_down (self, event):
        '''
        Grab the x/y coordinates when the right mouse button is clicked.
        '''

        self.x = event.GetX()
        self.y = event.GetY()

        item, flags = self.HitTest((self.x, self.y))

        if flags & wx.LIST_HITTEST_ONITEM:
            self.Select(item)
        else:
            self.x = None
            self.y = None
########NEW FILE########
__FILENAME__ = AddReconDlg
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: AddReconDlg.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.lib.dialogs
import MySQLdb

class AddReconDlg (wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]

        # begin wxGlade: AddRecon.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.stack_depth_static_staticbox = wx.StaticBox(self, -1, "Stack Depth:")
        self.reason_static_staticbox = wx.StaticBox(self, -1, "Reason:")
        self.notes_sizer_staticbox = wx.StaticBox(self, -1, "Notes:")
        self.address_static_staticbox = wx.StaticBox(self, -1, "Address:")
        self.address = wx.TextCtrl(self, -1, "")
        self.stack_depth = wx.SpinCtrl(self, -1, "3", min=0, max=99)
        self.reason = wx.TextCtrl(self, -1, "")
        self.notes = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.HSCROLL)
        self.save = wx.Button(self, -1, "Save")
        self.cancel = wx.Button(self, wx.ID_CANCEL)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.Bind(wx.EVT_BUTTON, self.on_button_save, self.save)


    def __set_properties(self):
        # begin wxGlade: AddRecon.__set_properties
        self.SetTitle("Add Recon Point")
        self.SetSize((500, 400))
        self.notes.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        # end wxGlade


    def __do_layout(self):
        # begin wxGlade: AddRecon.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        notes_sizer = wx.StaticBoxSizer(self.notes_sizer_staticbox, wx.HORIZONTAL)
        reason_static = wx.StaticBoxSizer(self.reason_static_staticbox, wx.HORIZONTAL)
        stack_depth_static = wx.StaticBoxSizer(self.stack_depth_static_staticbox, wx.HORIZONTAL)
        address_static = wx.StaticBoxSizer(self.address_static_staticbox, wx.HORIZONTAL)
        address_static.Add(self.address, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(address_static, 1, wx.EXPAND, 0)
        stack_depth_static.Add(self.stack_depth, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(stack_depth_static, 1, wx.EXPAND, 0)
        reason_static.Add(self.reason, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(reason_static, 1, wx.EXPAND, 0)
        notes_sizer.Add(self.notes, 3, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(notes_sizer, 4, wx.EXPAND, 0)
        buttons_sizer.Add(self.save, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        buttons_sizer.Add(self.cancel, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(buttons_sizer, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        self.Layout()
        # end wxGlade


    ####################################################################################################################
    def on_button_save (self, event):
        '''
        Grab the form values and add a new entry to the database.
        '''

        try:
            address = long(self.address.GetLineText(0), 16)
        except:
            dlg = wx.MessageDialog(self, "Invalid 'address' value, expecting a DWORD. Ex: 0xdeadbeef", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        try:
            stack_depth = int(self.stack_depth.GetValue())
        except:
            dlg = wx.MessageDialog(self, "Must specify an integer for 'stack depth'.", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        reason = self.reason.GetLineText(0)
        notes  = self.notes.GetValue()

        # must at least have a reason. notes are optional.
        if not reason:
            dlg = wx.MessageDialog(self, "Must specify a 'reason'.", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        sql  = " INSERT INTO pp_recon"
        sql += " SET module_id   = '%d',"  % self.parent.module["id"]
        sql += "     offset      = '%d',"  % (address - self.parent.module["base"])
        sql += "     stack_depth = '%d',"  % stack_depth
        sql += "     reason      = '%s',"  % reason.replace("\\", "\\\\").replace("'", "\\'")
        sql += "     status      = 'new',"
        sql += "     username    = '%s',"  % self.parent.main_frame.username
        sql += "     notes       = '%s'"   % notes.replace("\\", "\\\\").replace("'", "\\'")

        cursor = self.parent.main_frame.mysql.cursor()

        try:
            cursor.execute(sql)
        except MySQLdb.Error, e:
            msg  = "MySQL error %d: %s\n" % (e.args[0], e.args[1])
            msg += sql
            dlg = wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Failed Adding RECON Point")
            dlg.ShowModal()
            return

        # reload the recon list control. we reload instead of updating the control to partially solve
        # contention issues when multiple users are hitting the database at the same time.
        self.parent.recon.load(self.parent.module["id"])
        self.Destroy()
########NEW FILE########
__FILENAME__ = EditReconDlg
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: EditReconDlg.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.lib.dialogs
import MySQLdb

class EditReconDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent   = kwds["parent"]
        self.top      = self.parent.top
        self.choices  = ["new", "uncontrollable", "clear", "unsure", "vulnerable"]

        # begin wxGlade: EditReconDlg.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.stack_depth_static_staticbox = wx.StaticBox(self, -1, "Stack Depth:")
        self.reason_static_staticbox = wx.StaticBox(self, -1, "Reason:")
        self.status_static_staticbox = wx.StaticBox(self, -1, "Status")
        self.username_static_staticbox = wx.StaticBox(self, -1, "Username")
        self.notes_sizer_staticbox = wx.StaticBox(self, -1, "Notes:")
        self.address_static_staticbox = wx.StaticBox(self, -1, "Address:")
        self.address = wx.TextCtrl(self, -1, "")
        self.stack_depth = wx.SpinCtrl(self, -1, "3", min=0, max=99)
        self.reason = wx.TextCtrl(self, -1, "")
        self.status = wx.Choice(self, -1, choices=self.choices)
        self.username = wx.TextCtrl(self, -1, "")
        self.notes = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.HSCROLL)
        self.save = wx.Button(self, -1, "Save")
        self.cancel = wx.Button(self, wx.ID_CANCEL)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # event bindings.
        self.Bind(wx.EVT_BUTTON, self.on_button_save, self.save)


    def __set_properties(self):
        # begin wxGlade: EditReconDlg.__set_properties
        self.SetTitle("Edit Recon Point")
        self.SetSize((500, 500))
        self.status.SetSelection(-1)
        self.notes.SetFont(wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Lucida Console"))
        # end wxGlade


    def __do_layout(self):
        # begin wxGlade: EditReconDlg.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        notes_sizer = wx.StaticBoxSizer(self.notes_sizer_staticbox, wx.HORIZONTAL)
        username_static = wx.StaticBoxSizer(self.username_static_staticbox, wx.HORIZONTAL)
        status_static = wx.StaticBoxSizer(self.status_static_staticbox, wx.HORIZONTAL)
        reason_static = wx.StaticBoxSizer(self.reason_static_staticbox, wx.HORIZONTAL)
        stack_depth_static = wx.StaticBoxSizer(self.stack_depth_static_staticbox, wx.HORIZONTAL)
        address_static = wx.StaticBoxSizer(self.address_static_staticbox, wx.HORIZONTAL)
        address_static.Add(self.address, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(address_static, 1, wx.EXPAND, 0)
        stack_depth_static.Add(self.stack_depth, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(stack_depth_static, 1, wx.EXPAND, 0)
        reason_static.Add(self.reason, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(reason_static, 1, wx.EXPAND, 0)
        status_static.Add(self.status, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(status_static, 1, wx.EXPAND, 0)
        username_static.Add(self.username, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(username_static, 1, wx.EXPAND, 0)
        notes_sizer.Add(self.notes, 3, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(notes_sizer, 4, wx.EXPAND, 0)
        buttons_sizer.Add(self.save, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        buttons_sizer.Add(self.cancel, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(buttons_sizer, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        self.Layout()
        # end wxGlade


    ####################################################################################################################
    def on_button_save (self, event):
        '''
        Grab the form values and add a new entry to the database.
        '''

        try:
            address = long(self.address.GetLineText(0), 16)
        except:
            dlg = wx.MessageDialog(self, "Invalid 'address' value, expecting a DWORD. Ex: 0xdeadbeef", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        try:
            stack_depth = int(self.stack_depth.GetValue())
        except:
            dlg = wx.MessageDialog(self, "Must specify an integer for 'stack depth'.", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        status   = self.choices[self.status.GetSelection()]
        username = self.username.GetLineText(0)
        reason   = self.reason.GetLineText(0)
        notes    = self.notes.GetValue()

        # must at least have a reason. notes are optional.
        if not reason:
            dlg = wx.MessageDialog(self, "Must specify a 'reason'.", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        sql  = " UPDATE pp_recon"
        sql += " SET module_id   = '%d',"  % self.top.module["id"]
        sql += "     offset      = '%d',"  % (address - self.top.module["base"])
        sql += "     stack_depth = '%d',"  % stack_depth
        sql += "     reason      = '%s',"  % reason.replace("\\", "\\\\").replace("'", "\\'")
        sql += "     status      = '%s',"  % status
        sql += "     username    = '%s',"  % username
        sql += "     notes       = '%s'"   % notes.replace("\\", "\\\\").replace("'", "\\'")
        sql += " WHERE id = '%d'"          % self.recon_id

        cursor = self.top.main_frame.mysql.cursor()

        try:
            cursor.execute(sql)
        except MySQLdb.Error, e:
            msg  = "MySQL error %d: %s\n" % (e.args[0], e.args[1])
            msg += sql
            dlg = wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Failed Adding RECON Point")
            dlg.ShowModal()

        # reload the recon list control. we reload instead of updating the control to partially solve
        # contention issues when multiple users are hitting the database at the same time.
        self.top.recon.load(self.top.module["id"])
        self.Destroy()


    ####################################################################################################################
    def propagate (self, recon_id):
        '''
        Propagate the control values from the database. We grab from the database as opposed the the reconlistrctrl
        to ensure that we get the latest goods.
        '''

        # save this for later.
        self.recon_id = recon_id


        # create a mysql cursor and grab the db entry for this recon id.
        cursor = self.top.main_frame.mysql.cursor(MySQLdb.cursors.DictCursor)

        try:
            cursor.execute("SELECT * FROM pp_recon WHERE id = '%d'" % recon_id)
        except MySQLdb.Error, e:
            msg  = "MySQL error %d: %s\n" % (e.args[0], e.args[1])
            msg += sql
            dlg = wx.lib.dialogs.ScrolledMessageDialog(self, msg, "Failed Editing RECON Point")
            dlg.ShowModal()
            self.Destroy()

        recon = cursor.fetchone()
        self.address.SetValue("0x%08x" % (recon["offset"] + self.top.module["base"]))
        self.stack_depth.SetValue(recon["stack_depth"])
        self.reason.SetValue(recon["reason"])
        self.status.SetSelection(self.choices.index(recon["status"]))
        self.username.SetValue(recon["username"])
        self.notes.SetValue(recon["notes"])


########NEW FILE########
__FILENAME__ = PeekOptionsDlg
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PeekOptionsDlg.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.lib.filebrowsebutton as filebrowse

class PeekOptionsDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]
        # begin wxGlade: PeekOptionsDlg.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.log_static_staticbox = wx.StaticBox(self, -1, "Save log output to disk")
        self.boron_tag_static_staticbox = wx.StaticBox(self, -1, "Boron Tag")
        self.flags_static_staticbox = wx.StaticBox(self, -1, "Flags")
        self.quiet = wx.CheckBox(self, -1, "Disable run-time context dumps.")
        self.track_recv = wx.CheckBox(self, -1, "Enable recv() and recvfrom() hit logging.")
        self.log_file = filebrowse.FileBrowseButton(self, -1, labelText="", fileMask="*.txt", fileMode=wx.SAVE, toolTip="Specify the filename to save log output to")
        self.boron_tag = wx.TextCtrl(self, -1, "")
        self.ok = wx.Button(self, -1, "Ok")
        self.cancel = wx.Button(self, wx.ID_CANCEL)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # event bindings.
        self.Bind(wx.EVT_BUTTON, self.on_button_ok, self.ok)

        # set default control values.
        self.boron_tag.SetValue(self.parent.boron_tag)
        self.log_file.SetValue(self.parent.log_file)
        self.quiet.SetValue(self.parent.quiet)
        self.track_recv.SetValue(self.parent.track_recv)


    def __set_properties(self):
        # begin wxGlade: PeekOptionsDlg.__set_properties
        self.SetTitle("Peek Options")
        self.track_recv.SetValue(1)
        self.ok.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: PeekOptionsDlg.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        boron_tag_static = wx.StaticBoxSizer(self.boron_tag_static_staticbox, wx.HORIZONTAL)
        log_static = wx.StaticBoxSizer(self.log_static_staticbox, wx.HORIZONTAL)
        flags_static = wx.StaticBoxSizer(self.flags_static_staticbox, wx.HORIZONTAL)
        flags = wx.BoxSizer(wx.VERTICAL)
        flags.Add(self.quiet, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        flags.Add(self.track_recv, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        flags_static.Add(flags, 1, wx.EXPAND, 0)
        overall.Add(flags_static, 1, wx.EXPAND, 0)
        log_static.Add(self.log_file, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(log_static, 1, wx.EXPAND, 0)
        boron_tag_static.Add(self.boron_tag, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(boron_tag_static, 1, wx.EXPAND, 0)
        button_sizer.Add(self.ok, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        button_sizer.Add(self.cancel, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(button_sizer, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        self.Layout()
        # end wxGlade


    ####################################################################################################################
    def on_button_ok (self, event):
        '''
        Grab the form values and bubble them up to the parent module.
        '''

        self.parent.quiet      = self.quiet.GetValue()
        self.parent.track_recv = self.track_recv.GetValue()
        self.parent.log_file   = self.log_file.GetValue()
        self.parent.boron_tag  = self.boron_tag.GetLineText(0)

        self.Destroy()


########NEW FILE########
__FILENAME__ = ProcessListCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: ProcessListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import copy

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from pydbg import *
import utils

class ProcessListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin):
    '''
    Our custom list control containing a sortable list of PIDs and process names.
    '''

    FUNCTIONS    = utils.process_stalker.FUNCTIONS
    BASIC_BLOCKS = utils.process_stalker.BASIC_BLOCKS

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES )
        self.top                 = top
        self.selected_pid        = 0
        self.selected_proc       = None

        ListCtrlAutoWidthMixin.__init__(self)

        self.items_sort_map = {}
        self.itemDataMap    = self.items_sort_map

        ColumnSorterMixin.__init__(self, 2)

        self.InsertColumn(0, "PID")
        self.InsertColumn(1, "Process")


    ####################################################################################################################
    def GetListCtrl (self):
        '''
        Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        '''

        return self


    ####################################################################################################################
    def on_retrieve_list (self, event):
        pydbg = self.top.main_frame.pydbg

        self.DeleteAllItems()

        idx = 0
        for (pid, proc) in pydbg.enumerate_processes():
            # ignore system processes.
            if pid < 10:
                continue

            self.InsertStringItem(idx, "")
            self.SetStringItem(idx, 0, "%d" % pid)
            self.SetStringItem(idx, 1, proc)

            self.items_sort_map[idx] = (pid, proc)
            self.SetItemData(idx, idx)

            idx += 1


    ####################################################################################################################
    def on_select (self, event):
        '''
        '''

        self.selected_pid  = int(self.GetItem(event.m_itemIndex, 0).GetText())
        self.selected_proc =     self.GetItem(event.m_itemIndex, 1).GetText()
########NEW FILE########
__FILENAME__ = PyDbgDlg
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PyDbgDlg.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import wx.lib.filebrowsebutton as filebrowse

import _PAIMEIpeek

########################################################################################################################
class PyDbgDlg(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]

        # begin wxGlade: PyDbgDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.retrieve_list  = wx.Button(self, -1, "Retrieve List")
        self.process_list   = _PAIMEIpeek.ProcessListCtrl.ProcessListCtrl(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER, top=self.parent)
        self.load_target    = filebrowse.FileBrowseButton(self, -1, labelText="", fileMask="*.exe", fileMode=wx.OPEN, toolTip="Specify the target executable to load")
        self.attach_or_load = wx.Button(self, -1, "Attach / Load")
        self.cancel         = wx.Button(self, wx.ID_CANCEL)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # event bindings.
        self.Bind(wx.EVT_BUTTON, self.process_list.on_retrieve_list, self.retrieve_list)
        self.Bind(wx.EVT_BUTTON, self.on_attach_or_load, self.attach_or_load)
        self.process_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.process_list.on_select)


    ####################################################################################################################
    def __set_properties(self):
        # begin wxGlade: PyDbgDialog.__set_properties
        self.SetTitle("Select Target")
        self.SetSize((300, 500))
        self.retrieve_list.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.process_list.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.attach_or_load.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        # end wxGlade


    ####################################################################################################################
    def __do_layout(self):
        # begin wxGlade: PyDbgDialog.__do_layout
        overall = wx.BoxSizer(wx.VERTICAL)
        overall.Add(self.retrieve_list, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(self.process_list, 1, wx.EXPAND, 0)
        overall.Add(self.load_target, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        button_bar = wx.BoxSizer(wx.HORIZONTAL)
        button_bar.Add(self.attach_or_load, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        button_bar.Add(self.cancel, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(button_bar, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        self.Layout()
        # end wxGlade


    ####################################################################################################################
    def on_attach_or_load (self, event):
        '''
        Bubble up the attach or load target to the main PAIMEIpeek module.
        '''

        self.parent.load = self.load_target.GetValue()
        self.parent.pid  = self.process_list.selected_pid
        self.parent.proc = self.process_list.selected_proc
        
        if not self.parent.load and not self.parent.pid and not self.parent.proc:
            dlg = wx.MessageDialog(self, "You haven't selected a process to load or attach to.", "Error", wx.OK | wx.ICON_WARNING)
            dlg.ShowModal()
            return

        self.Destroy()
########NEW FILE########
__FILENAME__ = ReconListCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: ReconListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

import MySQLdb
import time

import _PAIMEIpeek

class ReconListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin):
    '''
    Our custom list control containing the various recon points and relevant notes.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=style)
        self.parent  = parent
        self.top     = top

        ListCtrlAutoWidthMixin.__init__(self)

        self.items_sort_map = {}
        self.itemDataMap    = self.items_sort_map

        ColumnSorterMixin.__init__(self, 8)

        self.InsertColumn(0, "ID")
        self.InsertColumn(1, "Address")
        self.InsertColumn(2, "Depth")
        self.InsertColumn(3, "Status")
        self.InsertColumn(4, "Username")
        self.InsertColumn(5, "# Hits")
        self.InsertColumn(6, "Boron Tag")
        self.InsertColumn(7, "Reason")


    ####################################################################################################################
    def GetListCtrl (self):
        '''
        Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        '''

        return self


    ####################################################################################################################
    def load (self, id):
        self.DeleteAllItems()

        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        try:
            busy = wx.BusyInfo("Loading... please wait.")
            wx.Yield()
        except:
            pass

        # instantiate a mysql cursor.
        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)

        # retrieve the module info.
        cursor.execute("SELECT * FROM pp_modules WHERE id = '%d'" % id)
        module = cursor.fetchone()

        # save the selected module DB entry to the top.
        self.top.module = module

        # step through the recon entries for this module id.
        cursor.execute("SELECT * FROM pp_recon WHERE module_id = '%d' ORDER BY offset ASC" % id)

        idx = reviewed = 0
        for recon in cursor.fetchall():
            address = module["base"] + recon["offset"]

            # count the number of hits under this recon point.
            c = mysql.cursor(MySQLdb.cursors.DictCursor)
            c.execute("SELECT COUNT(id) AS count FROM pp_hits WHERE recon_id = '%d'" % recon["id"])
            num_hits = c.fetchone()["count"]
            c.close()

            self.InsertStringItem(idx, "")
            self.SetStringItem(idx, 0, "%04x" % recon["id"])
            self.SetStringItem(idx, 1, "%08x" % address)
            self.SetStringItem(idx, 2, "%d" % recon["stack_depth"])
            self.SetStringItem(idx, 3, recon["status"])
            self.SetStringItem(idx, 4, recon["username"])
            self.SetStringItem(idx, 5, "%d" % num_hits)
            self.SetStringItem(idx, 6, recon["boron_tag"])
            self.SetStringItem(idx, 7, recon["reason"])

            # create an entry for the column sort map.
            self.SetItemData(idx, idx)
            self.items_sort_map[idx] = (recon["id"], address, recon["stack_depth"], recon["status"], recon["username"], num_hits, recon["boron_tag"], recon["reason"])

            if recon["status"] in ["uncontrollable", "clear", "vulnerable"]:
                reviewed += 1

            idx += 1

        # update % coverage gauge.
        self.top.percent_analyzed_static.SetLabel("%d of %d RECON Points Reviewed:" % (reviewed, idx))
        percent = int((float(reviewed) / float(idx)) * 100)
        self.top.percent_analyzed.SetValue(percent)

        cursor.close()


    ####################################################################################################################
    def on_activated (self, event):
        '''
        Load the PIDA module into the browser tree ctrl.
        '''

        recon_id = long(self.GetItem(event.m_itemIndex, 0).GetText(), 16)
        dlg      = _PAIMEIpeek.EditReconDlg.EditReconDlg(parent=self)

        dlg.propagate(recon_id)
        dlg.ShowModal()


    ####################################################################################################################
    def on_right_click (self, event):
        '''
        When an item in the recon list is right clicked, display a context menu.
        '''

        if not self.x or not self.y:
            return

        # we only have to do this once, that is what the hasattr() check is for.
        if not hasattr(self, "right_click_popup_refresh"):
            self.right_click_popup_refresh     = wx.NewId()
            self.right_click_popup_edit        = wx.NewId()
            self.right_click_popup_self_assign = wx.NewId()
            self.right_click_popup_delete      = wx.NewId()

            self.Bind(wx.EVT_MENU, self.on_right_click_popup_refresh,     id=self.right_click_popup_refresh)
            self.Bind(wx.EVT_MENU, self.on_right_click_popup_edit,        id=self.right_click_popup_edit)
            self.Bind(wx.EVT_MENU, self.on_right_click_popup_self_assign, id=self.right_click_popup_self_assign)
            self.Bind(wx.EVT_MENU, self.on_right_click_popup_delete,      id=self.right_click_popup_delete)

        # make a menu.
        menu = wx.Menu()
        menu.Append(self.right_click_popup_refresh, "&Refresh List")
        menu.AppendSeparator()
        menu.Append(self.right_click_popup_edit, "&Edit Recon Point")
        menu.Append(self.right_click_popup_self_assign, "Assign to &Self")
        menu.AppendSeparator()
        menu.Append(self.right_click_popup_delete, "Delete")

        self.PopupMenu(menu, (self.x, self.y))
        menu.Destroy()


    ####################################################################################################################
    def on_right_click_popup_delete (self, event):
        '''
        Right click event handler for popup delete menu selection.
        '''

        recon_id = self.selected_id

        # make sure the user is sure about this action.
        dlg = wx.MessageDialog(self, 'Delete the selected recon point?', 'Are you sure?', wx.YES_NO | wx.ICON_QUESTION)

        if dlg.ShowModal() != wx.ID_YES:
            return

        cursor = self.top.main_frame.mysql.cursor()
        cursor.execute("DELETE FROM pp_recon WHERE id = '%d'" % recon_id)
        cursor.close()

        # reload the recon list control. we reload instead of updating the control to partially solve
        # contention issues when multiple users are hitting the database at the same time.
        self.load(self.top.module["id"])

    ####################################################################################################################
    def on_right_click_popup_edit (self, event):
        '''
        Right click event handler for popup edit menu selection.
        '''

        recon_id = self.selected_id
        dlg      = _PAIMEIpeek.EditReconDlg.EditReconDlg(parent=self)

        dlg.propagate(recon_id)
        dlg.ShowModal()


    ####################################################################################################################
    def on_right_click_popup_refresh (self, event):
        '''
        Right click event handler for popup refresh list.
        '''

        self.load(self.top.module["id"])


    ####################################################################################################################
    def on_right_click_popup_self_assign (self, event):
        '''
        Right click event handler for popup assign item to self selection.
        '''

        if not self.top.main_frame.username:
            self.top.err("You must tell PaiMei who you are first.")
            return

        cursor   = self.top.main_frame.mysql.cursor()
        recon_id = self.selected_id

        cursor.execute("UPDATE pp_recon SET username = '%s' WHERE id = '%d'" % (self.top.main_frame.username, recon_id))

        # reload the recon list control. we reload instead of updating the control to partially solve
        # contention issues when multiple users are hitting the database at the same time.
        self.load(self.top.module["id"])


    ####################################################################################################################
    def on_right_down (self, event):
        '''
        Grab the x/y coordinates when the right mouse button is clicked.
        '''

        self.x = event.GetX()
        self.y = event.GetY()

        item, flags = self.HitTest((self.x, self.y))

        if flags & wx.LIST_HITTEST_ONITEM:
            self.Select(item)
        else:
            self.x = None
            self.y = None


    ####################################################################################################################
    def on_select (self, event):
        '''
        A line item in the recon list control was selected, load the hits list.
        '''

        recon_id         = long(self.GetItem(event.m_itemIndex, 0).GetText(), 16)
        self.selected_id = recon_id

        # clear the hit list control.
        self.top.hit_list.Set("")

        # load the list of hits for this recon_id.
        # select DESC so when we insert it re-sorts to ASC.
        try:
            cursor = self.top.main_frame.mysql.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("SELECT id, timestamp FROM pp_hits WHERE recon_id = '%d' ORDER BY timestamp, id DESC" % recon_id)
        except:
            self.top.err("MySQL query failed. Connection dropped?")
            return

        hit = False
        for hit in cursor.fetchall():
            timestamp = time.strftime("%m/%d/%Y %H:%M.%S", time.localtime(hit["timestamp"]))

            # timestamps are returned from the DB in reverse order and placed in ASC order by this command.
            self.top.hit_list.Insert(timestamp, 0)

            # associate the needed ID with this inserted item.
            self.top.hit_list.SetClientData(0, hit["id"])

        # select the first entry in the hit list.
        if hit:
            self.top.on_hit_list_select(None, hit["id"])
            self.top.hit_list.Select(0)
        else:
            self.top.peek_data.SetValue("")
########NEW FILE########
__FILENAME__ = export_idc_dialog
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: export_idc_dialog.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import os
import wx
import wx.lib.colourselect as csel
import MySQLdb
import time

########################################################################################################################
class export_idc_dialog (wx.Dialog):
    '''
    Export the stalked informaton for the specified tag id into an IDC file.
    '''

    FUNCTIONS    = 0
    BASIC_BLOCKS = 1

    OVERRIDE     = 0
    IGNORE       = 1
    BLEND        = 2

    def __init__(self, *args, **kwds):
        self.parent    = kwds["parent"]
        self.top       = kwds["top"]
        self.tag_id    = kwds["tag_id"]
        self.target_id = kwds["target_id"]

        # we remove our added dictionary args as wxDialog will complain about them if we don't.
        del(kwds["top"])
        del(kwds["tag_id"])
        del(kwds["target_id"])

        # begin wxGlade: export_idc_dialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.misc_staticbox  = wx.StaticBox(self, -1, "Miscellaneous Options")
        self.select_color    = csel.ColourSelect(self, -1, "Select Color", (0, 0, 60))
        self.color_depth     = wx.RadioBox(self, -1, "Color Depth", choices=["Functions", "Basic Blocks"], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.existing_colors = wx.RadioBox(self, -1, "Existing Colors", choices=["Override", "Ignore", "Blend"], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.add_comments    = wx.CheckBox(self, -1, "Add context data as comments")
        self.add_marks       = wx.CheckBox(self, -1, "Mark positions")
        self.ida_logo        = wx.StaticBitmap(self, -1, wx.Bitmap(self.top.main_frame.cwd + "/images/ida.bmp", wx.BITMAP_TYPE_ANY))
        self.export_idc      = wx.Button(self, -1, "Export IDC")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # event handlers.
        self.Bind(wx.EVT_BUTTON, self.on_export_idc, self.export_idc)


    ####################################################################################################################
    def __set_properties(self):
        # begin wxGlade: export_idc_dialog.__set_properties
        self.SetTitle("Export to IDC")
        self.color_depth.SetSelection(1)
        self.existing_colors.SetSelection(1)
        # end wxGlade


    ####################################################################################################################
    def __do_layout(self):
        # begin wxGlade: export_idc_dialog.__do_layout
        overall = wx.BoxSizer(wx.HORIZONTAL)
        right = wx.BoxSizer(wx.VERTICAL)
        left = wx.BoxSizer(wx.VERTICAL)
        misc = wx.StaticBoxSizer(self.misc_staticbox, wx.VERTICAL)
        left.Add(self.select_color, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        left.Add(self.color_depth, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        left.Add(self.existing_colors, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        misc.Add(self.add_comments, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        misc.Add(self.add_marks, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        left.Add(misc, 1, wx.EXPAND, 0)
        overall.Add(left, 1, wx.EXPAND, 0)
        right.Add(self.ida_logo, 0, wx.ADJUST_MINSIZE, 0)
        right.Add(self.export_idc, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        overall.Add(right, 0, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(overall)
        overall.Fit(self)
        overall.SetSizeHints(self)
        self.Layout()
        # end wxGlade


    ####################################################################################################################
    def on_export_idc (self, event):
        '''
        '''

        # ensure a MySQL connection is available.
        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        # prompt the user for the IDC filename.
        dlg = wx.FileDialog(                                            \
            self,                                                       \
            message     = "IDC Filename",                               \
            defaultDir  = os.getcwd(),                                  \
            defaultFile = "",                                           \
            wildcard    = "*.idc",                                      \
            style       = wx.SAVE | wx.OVERWRITE_PROMPT | wx.CHANGE_DIR \
        )

        if dlg.ShowModal() != wx.ID_OK:
            self.top.msg("Export cancelled by user")
            self.Destroy()
            return

        # attempt to open the file and write the IDC header.
        try:
            filename = dlg.GetPath()
            idc      = open(filename, "w+")

            idc.write(self.idc_header)
        except:
            self.top.msg("Unable to open requested file: %s" % filename)
            self.Destroy()
            return

        self.Destroy()
        busy = wx.BusyInfo("Generating IDC script ... stand by.")
        wx.Yield()

        # extract the various dialog options.
        # IDA reads colors in reverse, ie: instead of #RRGGBB it understands 0xBBGGRR.
        wxcolor = self.select_color.GetColour()
        color   = "0x%02x%02x%02x" % (wxcolor.Blue(), wxcolor.Green(), wxcolor.Red())

        existing_colors = self.existing_colors.GetSelection()
        color_depth     = self.color_depth.GetSelection()
        add_comments    = self.add_comments.GetValue()
        add_marks       = self.add_marks.GetValue()

        # step through the hits for this tag id.
        hits = mysql.cursor(MySQLdb.cursors.DictCursor)
        hits.execute("SELECT hits.*, tags.tag FROM cc_hits AS hits, cc_tags AS tags WHERE hits.tag_id = '%d' AND tags.id = '%d' ORDER BY module ASC" % (self.tag_id, self.tag_id))

        current_module = ""
        base_modified  = False

        for hit in hits.fetchall():
            # if function level color depth was specified and the current hit is not for a function, ignore it.
            if color_depth == self.FUNCTIONS and not hit["is_function"]:
                continue

            # ensure we are working in the right module.
            if hit["module"] != current_module:
                if current_module != "":
                    idc.write("}\n")

                current_module = hit["module"]
                idc.write("\n    if (tolower(this_module) == \"%s\")\n    {\n" % current_module.lower())
                base_modified = False

            # if the base address for any hit in this module is 0, then set base to 0.
            if not hit["base"] and not base_modified:
                idc.write("        // no base for this module.\n")
                idc.write("        base = 0;\n\n");
                base_modified = True

            if add_comments:
                comment  = "[#%d] %s\n" % (hit["num"], time.ctime(hit["timestamp"]))
                comment += "eax: %08x (%10d) -> %s\n" % (hit["eax"], hit["eax"], hit["eax_deref"])
                comment += "ebx: %08x (%10d) -> %s\n" % (hit["ebx"], hit["ebx"], hit["ebx_deref"])
                comment += "ecx: %08x (%10d) -> %s\n" % (hit["ecx"], hit["ecx"], hit["ecx_deref"])
                comment += "edx: %08x (%10d) -> %s\n" % (hit["edx"], hit["edx"], hit["edx_deref"])
                comment += "edi: %08x (%10d) -> %s\n" % (hit["edi"], hit["edi"], hit["edi_deref"])
                comment += "esi: %08x (%10d) -> %s\n" % (hit["esi"], hit["esi"], hit["esi_deref"])
                comment += "ebp: %08x (%10d) -> %s\n" % (hit["ebp"], hit["ebp"], hit["ebp_deref"])
                comment += "esp: %08x (%10d) -> %s\n" % (hit["esp"], hit["esp"], hit["esp_deref"])
                comment += "+04: %08x (%10d) -> %s\n" % (hit["esp_4"],  hit["esp_4"],  hit["esp_4_deref"])
                comment += "+08: %08x (%10d) -> %s\n" % (hit["esp_8"],  hit["esp_8"],  hit["esp_8_deref"])
                comment += "+0C: %08x (%10d) -> %s\n" % (hit["esp_c"],  hit["esp_c"],  hit["esp_c_deref"])
                comment += "+10: %08x (%10d) -> %s"   % (hit["esp_10"], hit["esp_10"], hit["esp_10_deref"])

                comment = comment.replace('"', '\\"')

                idx = 0
                for line in comment.split("\n"):
                    idc.write("        ExtLinA(base + 0x%08x, %d, \"%s\");\n" % (hit["eip"] - hit["base"], idx, line))
                    idx += 1

            prefix = ""

            if existing_colors != self.BLEND:
                idc.write("\n        color = %s;" % color)

            if existing_colors == self.IGNORE:
                idc.write("\n        if (GetColor(base + 0x%08x, CIC_ITEM) == DEFCOLOR)" % (hit["eip"] - hit["base"]))
                prefix = "    "
            elif existing_colors == self.BLEND:
                idc.write("\n        color = blend_color(GetColor(base + 0x%08x, CIC_ITEM), %s);" % (hit["eip"] - hit["base"], color))

            if color_depth == self.FUNCTIONS:
                idc.write("\n%s        SetColor(base + 0x%08x, CIC_FUNC, color);\n\n" % (prefix, hit["eip"] - hit["base"]))
            else:
                idc.write("\n%s        assign_block_color_to(base + 0x%08x, color);\n\n" % (prefix, hit["eip"] - hit["base"]))

            if add_marks:
                idc.write("        MarkPosition(base + 0x%08x, 1,1,1, next_mark, \"tag: %s hit #%05d\");\n" % (hit["eip"] - hit["base"], hit["tag"], hit["num"]))
                idc.write("        next_mark++;\n\n");

        idc.write("    }\n")
        idc.write("}\n")
        idc.close()


    ####################################################################################################################
    '''
    Stock header with support functions and declarations for IDC export.
    '''

    idc_header = """//
// AUTO-GENERATED BY PAIMEI
// http://www.openrce.org
//

#include <idc.idc>

// convenience wrapper around assign_color_to() that will automatically resolve the 'start' and 'end' arguments with
// the start and end address of the block containing ea.
static assign_block_color_to (ea, color)
{
    auto block_start, block_end;

    block_start = find_block_start(ea);
    block_end   = find_block_end(ea);

    if (block_start == BADADDR || block_end == BADADDR)
        return BADADDR;

    assign_color_to(block_start, block_end, color);
}

// the core color assignment routine.
static assign_color_to (start, end, color)
{
    auto ea;

    if (start != end)
    {
        for (ea = start; ea < end; ea = NextNotTail(ea))
            SetColor(ea, CIC_ITEM, color);
    }
    else
    {
        SetColor(start, CIC_ITEM, color);
    }
}

// returns address of start of block if found, BADADDR on error.
static find_block_start (current_ea)
{
    auto ea, prev_ea;
    auto xref_type;

    // walk up from current ea.
    for (ea = current_ea; ea != BADADDR; ea = PrevNotTail(ea))
    {
        prev_ea = PrevNotTail(ea);

        // if prev_ea is the start of the function, we've found the start of the block.
        if (GetFunctionAttr(ea, FUNCATTR_START) == prev_ea)
            return prev_ea;

        // if there is a code reference *from* prev_ea or *to* ea.
        if (Rfirst0(prev_ea) != BADADDR || RfirstB0(ea) != BADADDR)
        {
            xref_type = XrefType();

            // block start found if the code reference was a JMP near or JMP far.
            if (xref_type == fl_JN || xref_type == fl_JF)
                return ea;
        }
    }

    return BADADDR;
}

// returns address of end of block if found, BADADDR on error.
static find_block_end (current_ea)
{
    auto ea, next_ea;
    auto xref_type;

    // walk down from current ea.
    for (ea = current_ea; ea != BADADDR; ea = NextNotTail(ea))
    {
        next_ea = NextNotTail(ea);

        // if next_ea is the start of the function, we've found the end of the block.
        if (GetFunctionAttr(ea, FUNCATTR_END) == next_ea)
            return next_ea;

        // if there is a code reference *from* ea or *to* next_ea.
        if (Rfirst0(ea) != BADADDR || RfirstB0(next_ea) != BADADDR)
        {
            xref_type = XrefType();

            // block end found if the code reference was a JMP near or JMP far.
            if (xref_type == fl_JN || xref_type == fl_JF)
                return next_ea;
        }
    }

    return BADADDR;
}

// return the lower case version of 'str'.
static tolower (str)
{
    auto i, c, new;

    new = "";

    for (i = 0; i < strlen(str); i++)
    {
        c = substr(str, i, i + 1);

        if (ord(c) >= 0x41 && ord(c) <= 0x5a)
            c = form("%s", ord(c) + 32);

        new = new + c;
    }

    return new;
}

// return the blended color between 'old' and 'new'.
static blend_color (old, new)
{
    auto r, g, b, bold, gold, rold, bnew, gnew, rnew;

    bold = (old & 0xFF0000) >> 16;
    gold = (old & 0x00FF00) >> 8;
    rold = (old & 0x0000FF);

    bnew = (new & 0xFF0000) >> 16;
    gnew = (new & 0x00FF00) >> 8;
    rnew = (new & 0x0000FF);

    b    = (bold + (bnew - bold) / 2) & 0xFF;
    g    = (gold + (gnew - gold) / 2) & 0xFF;
    r    = (rold + (rnew - rold) / 2) & 0xFF;

    return (b << 16) + (g << 8) + r;
}

// return the next empty Mark slot
static get_marked_next()
{
    auto slot;
    slot = 1;

    // loop until we find an empty slot
    while(GetMarkedPos(slot) != -1)
        slot++;

    return slot;
}

// executed on script load.
static main()
{
    auto base, color, this_module, next_mark;

    base        = MinEA() - 0x1000;    // cheap hack
    this_module = GetInputFile();
    next_mark = get_marked_next();
"""

########NEW FILE########
__FILENAME__ = HitsListCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: HitsListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import MySQLdb
import time

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

class HitsListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin):
    '''
    Our custom list control containing the hits for the current target/tag.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES )
        self.top           = top
        self.hits_by_index = {}
        self.eips          = []
        self.last_focused  = None

        ListCtrlAutoWidthMixin.__init__(self)

        self.items_sort_map = {}
        self.itemDataMap    = self.items_sort_map

        ColumnSorterMixin.__init__(self, 7)

        self.InsertColumn(0, "#")
        self.InsertColumn(1, "Time")
        self.InsertColumn(2, "EIP")
        self.InsertColumn(3, "TID")
        self.InsertColumn(4, "Module")
        self.InsertColumn(5, "Func?")
        self.InsertColumn(6, "Tag")


    ####################################################################################################################
    def append_hits (self, tag_id):
        '''
        '''

        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        busy = wx.BusyInfo("Loading... please wait.")
        wx.Yield()

        # step through the hits for this tag id.
        hits = mysql.cursor(MySQLdb.cursors.DictCursor)
        hits.execute("SELECT hits.*, tags.tag FROM cc_hits AS hits, cc_tags AS tags WHERE hits.tag_id = '%d' AND tags.id = '%d' ORDER BY num ASC" % (tag_id, tag_id))

        idx      = len(self.hits_by_index)
        hitlist  = hits.fetchall()

        # XXX - need to fix this logic, it craps out some times
        try:
            min_time = min([h["timestamp"] for h in hitlist if h["timestamp"] != 0])
        except:
            min_time = 0

        for hit in hitlist:
            self.hits_by_index[idx] = hit

            if self.eips.count(hit["eip"]) == 0:
                if hit["is_function"]:
                    self.top.hit_function_count += 1

                self.top.hit_basic_block_count += 1

            if hit["is_function"]: is_function = "Y"
            else:                  is_function = ""

            timestamp = int(hit["timestamp"]) - min_time

            self.InsertStringItem(idx, "")
            self.SetStringItem(idx, 0, "%d"   % hit["num"])
            self.SetStringItem(idx, 1, "+%ds" % timestamp)
            self.SetStringItem(idx, 2, "%08x" % hit["eip"])
            self.SetStringItem(idx, 3, "%d"   % hit["tid"])
            self.SetStringItem(idx, 4,          hit["module"])
            self.SetStringItem(idx, 5, "%s"   % is_function)
            self.SetStringItem(idx, 6,          hit["tag"])

            self.items_sort_map[idx] = ( \
                int(hit["num"]),
                "+%ds" % timestamp,
                "%08x" % hit["eip"],
                int(hit["tid"]),
                hit["module"],
                "%s"   % is_function,
                hit["tag"])

            self.SetItemData(idx, idx)

            self.eips.append(hit["eip"])
            idx += 1

        self.top.update_gauges()


    ####################################################################################################################
    def focus_item_by_address (self, address):
        '''
        '''

        # find the first occurence of address in the list and set the focus on it.
        for (idx, hit) in self.hits_by_index.items():
            if hit["eip"] == address:
                state = state_mask = wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED
                self.SetItemState(idx, state, state_mask)
                self.EnsureVisible(idx)

                if self.last_focused:
                    self.SetItemState(self.last_focused, 0, state_mask)

                self.last_focused = idx
                break


    ####################################################################################################################
    def GetListCtrl (self):
        '''
        Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        '''

        return self


    ####################################################################################################################
    def load_hits (self, tag_id):
        '''
        '''

        # reset the global counters.
        self.top.hit_function_count    = 0
        self.top.hit_basic_block_count = 0

        # reset the hits by index dictionary and hit eip cache.
        self.hits_by_index = {}
        self.eips          = []

        # clear the list.
        self.DeleteAllItems()

        self.append_hits(tag_id)


    ####################################################################################################################
    def on_select (self, event):
        self.selected = event.GetItem()

        hit = self.hits_by_index[self.GetItemData(self.selected.GetId())]

        separator = "-" * 72

        context_dump  = "%s\n" % time.ctime(hit["timestamp"])
        context_dump += "EIP: %08x\n" % hit["eip"]
        context_dump += "EAX: %08x (%10d) -> %s\n" % (hit["eax"], hit["eax"], hit["eax_deref"])
        context_dump += "EBX: %08x (%10d) -> %s\n" % (hit["ebx"], hit["ebx"], hit["ebx_deref"])
        context_dump += "ECX: %08x (%10d) -> %s\n" % (hit["ecx"], hit["ecx"], hit["ecx_deref"])
        context_dump += "EDX: %08x (%10d) -> %s\n" % (hit["edx"], hit["edx"], hit["edx_deref"])
        context_dump += "EDI: %08x (%10d) -> %s\n" % (hit["edi"], hit["edi"], hit["edi_deref"])
        context_dump += "ESI: %08x (%10d) -> %s\n" % (hit["esi"], hit["esi"], hit["esi_deref"])
        context_dump += "EBP: %08x (%10d) -> %s\n" % (hit["ebp"], hit["ebp"], hit["ebp_deref"])
        context_dump += "ESP: %08x (%10d) -> %s\n" % (hit["esp"], hit["esp"], hit["esp_deref"])

        context_dump += "+04: %08x (%10d) -> %s\n" % (hit["esp_4"],  hit["esp_4"],  hit["esp_4_deref"])
        context_dump += "+08: %08x (%10d) -> %s\n" % (hit["esp_8"],  hit["esp_8"],  hit["esp_8_deref"])
        context_dump += "+0C: %08x (%10d) -> %s\n" % (hit["esp_c"],  hit["esp_c"],  hit["esp_c_deref"])
        context_dump += "+10: %08x (%10d) -> %s\n" % (hit["esp_10"], hit["esp_10"], hit["esp_10_deref"])

        self.top.hit_details.SetValue(context_dump)

        # if a udraw connection is available, bring the selected node into focus.
        self.top.targets.udraw_focus_node_by_address(hit["eip"])
########NEW FILE########
__FILENAME__ = PIDAModulesListCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: PIDAModulesListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import os
import sys
import time

from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

sys.path.append("..")

import pida

class PIDAModulesListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin):
    '''
    Our custom list control containing loaded pida modules.
    '''

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES )
        self.top=top

        ListCtrlAutoWidthMixin.__init__(self)

        self.InsertColumn(0,  "# Func")
        self.InsertColumn(1,  "# BB")
        self.InsertColumn(2,  "PIDA Module")


    ####################################################################################################################
    def on_add_module (self, event):
        '''
        Load a PIDA module into memory.
        '''

        dlg = wx.FileDialog(                                    \
            self,                                               \
            message     = "Select PIDA module",                 \
            defaultDir  = os.getcwd(),                          \
            defaultFile = "",                                   \
            wildcard    = "*.PIDA",                             \
            style       = wx.OPEN | wx.CHANGE_DIR | wx.MULTIPLE \
        )

        if dlg.ShowModal() != wx.ID_OK:
            return

        for path in dlg.GetPaths():
            try:
                module_name = path[path.rfind("\\")+1:path.rfind(".pida")].lower()

                if self.top.pida_modules.has_key(module_name):
                    self.top.err("Module %s already loaded ... skipping." % module_name)
                    continue

                # deprecated - replaced by progress dialog.
                #busy = wx.BusyInfo("Loading %s ... stand by." % module_name)
                #wx.Yield()

                start  = time.time()
                module = pida.load(path, progress_bar="wx")

                if not module:
                    self.top.msg("Loading of PIDA module '%s' cancelled by user." % module_name)
                    return

                elif module == -1:
                    raise Exception

                else:
                    self.top.pida_modules[module_name] = module
                    self.top.msg("Loaded PIDA module '%s' in %.2f seconds." % (module_name, round(time.time() - start, 3)))

                # add the function / basic blocks to the global count.
                function_count    = len(self.top.pida_modules[module_name].nodes)
                basic_block_count = 0

                for function in self.top.pida_modules[module_name].nodes.values():
                    basic_block_count += len(function.nodes)

                self.top.function_count    += function_count
                self.top.basic_block_count += basic_block_count

                self.top.update_gauges()

                idx = len(self.top.pida_modules) - 1
                self.InsertStringItem(idx, "")
                self.SetStringItem(idx, 0, "%d" % function_count)
                self.SetStringItem(idx, 1, "%d" % basic_block_count)
                self.SetStringItem(idx, 2, module_name)

                self.SetColumnWidth(2, wx.LIST_AUTOSIZE)
            except:
                self.top.err("FAILED LOADING MODULE: %s. Possibly corrupt or version mismatch?" % module_name)
                if self.top.pida_modules.has_key(module_name):
                    del(self.top.pida_modules[module_name])


    ####################################################################################################################
    def on_right_click (self, event):
        '''
        When an item in the PIDA module list is right clicked, display a context menu.
        '''

        if not self.x or not self.y:
            return

        # we only have to do this once, that is what the hasattr() check is for.
        if not hasattr(self, "right_click_popup_remove"):
            self.right_click_popup_remove = wx.NewId()
            self.Bind(wx.EVT_MENU, self.on_right_click_popup_remove, id=self.right_click_popup_remove)

        # make a menu.
        menu = wx.Menu()
        menu.Append(self.right_click_popup_remove, "Remove")

        self.PopupMenu(menu, (self.x, self.y))
        menu.Destroy()


    ####################################################################################################################
    def on_right_click_popup_remove (self, event):
        '''
        Right click event handler for popup remove menu selection.
        '''

        idx    = self.GetFirstSelected()
        module = self.GetItem(idx, 2).GetText()

        # add the function / basic blocks to the global count.
        self.top.function_count -= len(self.top.pida_modules[module].nodes)

        for function in self.top.pida_modules[module].nodes.values():
            self.top.basic_block_count -= len(function.nodes)

        self.top.update_gauges()

        del(self.top.pida_modules[module])
        self.DeleteItem(idx)


    ####################################################################################################################
    def on_right_down (self, event):
        '''
        Grab the x/y coordinates when the right mouse button is clicked.
        '''

        self.x = event.GetX()
        self.y = event.GetY()

        item, flags = self.HitTest((self.x, self.y))

        if flags & wx.LIST_HITTEST_ONITEM:
            self.Select(item)
        else:
            self.x = None
            self.y = None

########NEW FILE########
__FILENAME__ = ProcessListCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: ProcessListCtrl.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from pydbg import *
import utils

class ProcessListCtrl (wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin):
    '''
    Our custom list control containing a sortable list of PIDs and process names.
    '''

    FUNCTIONS    = utils.process_stalker.FUNCTIONS
    BASIC_BLOCKS = utils.process_stalker.BASIC_BLOCKS

    def __init__(self, parent, id, pos=None, size=None, style=None, top=None):
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT | wx.SIMPLE_BORDER | wx.LC_HRULES )
        self.top                 = top
        self.restore_breakpoints = False
        self.selected_pid        = 0
        self.selected_proc       = None
        self.process_stalker     = None

        ListCtrlAutoWidthMixin.__init__(self)

        self.items_sort_map = {}
        self.itemDataMap    = self.items_sort_map

        ColumnSorterMixin.__init__(self, 2)

        self.InsertColumn(0, "PID")
        self.InsertColumn(1, "Process")


    ####################################################################################################################
    def GetListCtrl (self):
        '''
        Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        '''

        return self


    ####################################################################################################################
    def on_attach_detach (self, event):
        '''
        This is the meat and potatoes. Grab the coverage depth, attach to the selected process, load the appropriate
        modules ... etc etc.
        '''

        ###
        ### detaching ...
        ###

        if self.process_stalker:
            self.process_stalker.detach = True
            self.process_stalker        = None

            self.top.attach_detach.SetLabel("Start Stalking")
            return

        ###
        ### attaching / loading ...
        ###

        # sanity checking.
        if not len(self.top.pida_modules):
            self.top.err("You must load at least one PIDA file.")
            return

        if not self.top.stalk_tag:
            self.top.err("You must select a tag for code coverage data storage.")
            return

        # pull the value from the load target control, if anything is specified.
        load_value = self.top.load_target.GetValue().rstrip(" ").lstrip(" ")

        if not self.selected_pid and not load_value and not self.top.watch:
            self.top.err("You must select a target process or executable to stalk.")
            return

        for module in self.top.pida_modules:
            self.top.msg("Stalking module %s" % module)

        # create a new debugger instance for this stalk.
        if hasattr(self.top.main_frame.pydbg, "port"):
            dbg = pydbg_client(self.top.main_frame.pydbg.host, self.top.main_frame.pydbg.port)
        else:
            dbg = pydbg()

        # we are loading a target to stalk. (filled load control takes precedence over selected process)
        if load_value:
            # look for a quotation mark, any quotation mark will do but if there is one present we also need to know
            # the location of the second one, so just start off by looking for that now.
            second_quote = load_value.find('"', 1)

            if second_quote != -1:
                load   = load_value[1:second_quote]
                args   = load_value[second_quote+1:]
                attach = None
            else:
                load   = load_value
                args   = None
                attach = None

            main = load

            if main.rfind("\\"):
                main = main[main.rfind("\\")+1:]

        elif self.top.watch:
            process_found = False

            self.top.msg("Watching for process: %s" % self.top.watch)

            while not process_found:
                for (pid, proc_name) in dbg.enumerate_processes():
                    wx.Yield()
                    if proc_name.lower() == self.top.watch.lower():
                        process_found = True
                        break

            self.top.msg("Found target process at %d (0x04x)" % (pid, pid))

            attach = pid
            main   = proc_name.lower()
            load   = None
            args   = None

        # we are attaching a target to stalk.
        else:
            attach = self.selected_pid
            main   = self.selected_proc.lower()
            load   = None
            args   = None

        self.process_stalker = utils.process_stalker(                       \
            attach              = attach,                                   \
            load                = load,                                     \
            args                = args,                                     \
            filter_list         = self.top.filter_list,                     \
            heavy               = self.top.heavy.GetValue(),                \
            ignore_first_chance = self.top.ignore_first_chance.GetValue(),  \
            log                 = self.top.msg,                             \
            main                = main,                                     \
            mysql               = self.top.main_frame.mysql,                \
            pida_modules        = self.top.pida_modules,                    \
            pydbg               = dbg,                                      \
            print_bps           = self.top.print_bps,                       \
            restore             = self.top.restore_breakpoints.GetValue(),  \
            tag_id              = self.top.stalk_tag["id"],                 \
            target_id           = self.top.stalk_tag["target_id"],          \
            depth               = self.top.coverage_depth.GetSelection()    \
        )

        self.top.attach_detach.SetLabel("Stop Stalking")
        self.process_stalker.stalk()

        # reset state after stalking is finished.
        self.top.attach_detach.SetLabel("Start Stalking")
        self.process_stalker = None


    ####################################################################################################################
    def on_retrieve_list (self, event):
        pydbg = self.top.main_frame.pydbg

        self.DeleteAllItems()

        idx = 0
        for (pid, proc) in pydbg.enumerate_processes():
            # ignore system processes.
            if pid < 10:
                continue

            self.InsertStringItem(idx, "")
            self.SetStringItem(idx, 0, "%d" % pid)
            self.SetStringItem(idx, 1, proc)

            self.items_sort_map[idx] = (pid, proc)
            self.SetItemData(idx, idx)

            idx += 1


    ####################################################################################################################
    def on_select (self, event):
        '''
        '''

        self.selected_pid  = int(self.GetItem(event.m_itemIndex, 0).GetText())
        self.selected_proc =     self.GetItem(event.m_itemIndex, 1).GetText()
########NEW FILE########
__FILENAME__ = TargetsTreeCtrl
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: TargetsTreeCtrl.py 231 2008-07-21 22:43:36Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx

import MySQLdb
import thread

import export_idc_dialog
import target_properties
import utils
import pgraph

class TargetsTreeCtrl (wx.TreeCtrl):
    '''
    Our custom tree control containing targets and tags from column one.
    '''

    def __init__ (self, parent, id, pos=None, size=None, style=None, top=None):
        wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
        self.top            = top
        self.selected       = None
        self.used_for_stalk = None

        # udraw sync class variables.
        self.cc                   = None
        self.udraw                = None
        self.udraw_last_color     = None
        self.udraw_last_color_id  = None
        self.udraw_last_selected  = None
        self.udraw_base_graph     = None
        self.udraw_current_graph  = None
        self.udraw_hit_funcs      = []
        self.udraw_in_function    = False

        # setup our custom target tree list control.
        self.icon_list        = wx.ImageList(16, 16)
        self.icon_folder      = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, (16, 16)))
        self.icon_folder_open = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER, (16, 16)))
        self.icon_tag         = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16, 16)))
        self.icon_selected    = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_FIND,        wx.ART_OTHER, (16, 16)))
        self.icon_filtered    = self.icon_list.Add(wx.ArtProvider_GetBitmap(wx.ART_CUT,         wx.ART_OTHER, (16, 16)))

        self.SetImageList(self.icon_list)

        self.root = self.AddRoot("Available Targets")
        self.SetPyData(self.root, None)
        self.SetItemImage(self.root, self.icon_folder,      wx.TreeItemIcon_Normal)
        self.SetItemImage(self.root, self.icon_folder_open, wx.TreeItemIcon_Expanded)


    ####################################################################################################################
    def on_right_click_popup_add_tag (self, event):
        '''
        Right click event handler for popup add tag menu selection.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)
        mysql    = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        dlg = wx.TextEntryDialog(self, "Enter name of new tag:", "Add Tag", "")

        if dlg.ShowModal() != wx.ID_OK:
            return

        tag_name = dlg.GetValue()
        tag_name = tag_name.replace("\\", "\\\\").replace("'", "\\'")

        new_tag = mysql.cursor()
        new_tag.execute("INSERT INTO cc_tags SET target_id = '%d', tag = '%s', notes = ''" % (selected["id"], tag_name))

        # refresh the targets list.
        self.on_retrieve_targets(None)

        dlg.Destroy()


    ####################################################################################################################
    def on_right_click_popup_add_target (self, event):
        '''
        Right click event handler for popup add target menu selection.
        '''

        if not self.selected:
            return

        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        dlg = wx.TextEntryDialog(self, "Enter name of new target:", "Add Target", "")

        if dlg.ShowModal() != wx.ID_OK:
            return

        target_name = dlg.GetValue()
        target_name = target_name.replace("\\", "\\\\").replace("'", "\\'")

        new_target = mysql.cursor()
        new_target.execute("INSERT INTO cc_targets SET target = '%s', notes = ''" % target_name)

        # refresh the targets list.
        self.on_retrieve_targets(None)

        dlg.Destroy()


    ####################################################################################################################
    def on_right_click_popup_append_hits (self, event):
        '''
        Right click event handler for popup append hits menu selection.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)

        self.top.hits.append_hits(selected["id"])


    ####################################################################################################################
    def on_right_click_popup_clear_tag (self, event):
        '''
        Right click event handler for popup clear tag menu selection.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)
        mysql    = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        dlg = wx.MessageDialog(self, "Erase the recorded data under: %s?\n" % selected["tag"], "Confirm", wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)

        if dlg.ShowModal() == wx.ID_NO:
            return

        dlg.Destroy()

        cursor = self.top.main_frame.mysql.cursor()
        cursor.execute("DELETE FROM cc_hits WHERE tag_id = '%d'" % selected["id"])


    ####################################################################################################################
    def on_right_click_popup_expand_tag (self, event):
        '''
        Right click event handler for popup expand tag menu selection.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)
        mysql    = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        dlg = wx.MessageDialog(self, "Expand out the basic blocks under: %s?\n" % selected["tag"], "Confirm", wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)

        if dlg.ShowModal() == wx.ID_NO:
            return

        dlg.Destroy()

        busy = wx.BusyInfo("Expanding tag ... please wait.")
        wx.Yield()

        cc = utils.code_coverage.code_coverage(mysql=mysql)
        cc.import_mysql(selected["target_id"], selected["id"])

        no_modules = []
        new_hits   = []

        for ea in cc.hits.keys():
            hit = cc.hits[ea][0]

            # we are expanding out all the basic blocks of the hit functions.
            if not hit.is_function:
                continue

            # if we don't have the module for this hit, continue to the next one.
            if not self.top.pida_modules.has_key(hit.module):
                if not no_modules.count(hit.module):
                    no_modules.append(hit.module)
                    self.top.err("Necessary module '%s' for part of tag expansion missing, ignoring." % hit.module)
                continue

            # rebase the module if necessary.
            self.top.pida_modules[hit.module].rebase(hit.base)

            # grab the appropriate PIDA function.
            function = self.top.pida_modules[hit.module].functions[hit.eip]

            for bb_ea in function.basic_blocks.keys():
                if not cc.hits.has_key(bb_ea):
                    ccs             = utils.code_coverage.__code_coverage_struct__()
                    ccs.eip         = bb_ea
                    ccs.tid         = 0
                    ccs.num         = cc.num
                    ccs.timestamp   = 0
                    ccs.module      = hit.module
                    ccs.base        = hit.base
                    ccs.is_function = 0

                    new_hits.append(ccs)

                    # increment the internal counter.
                    cc.num += 1

        # manually propagate the new hits into the code coverage data structure.
        for ccs in new_hits:
            if not cc.hits.has_key(ccs.eip):
                cc.hits[ccs.eip] = []

            cc.hits[ccs.eip].append(ccs)

        # clear the current database entries and upload the new ones.
        cc.clear_mysql(selected["target_id"], selected["id"])
        cc.export_mysql(selected["target_id"], selected["id"])

        self.top.msg("Tag expansion complete, added %d new entries." % len(new_hits))


    ####################################################################################################################
    def on_right_click_popup_delete_tag (self, event):
        '''
        Right click event handler for popup delete tag menu selection.
        '''

        if not self.selected:
            return

        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        selected = self.GetPyData(self.selected)

        dlg = wx.MessageDialog(self, "Delete tag: %s?" % selected["tag"], "Confirm", wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)

        if dlg.ShowModal() == wx.ID_YES:
            cursor = mysql.cursor()
            cursor.execute("DELETE FROM cc_hits WHERE tag_id = '%d'" % selected["id"])
            cursor.execute("DELETE FROM cc_tags where     id = '%d'" % selected["id"])

            # refresh the targets list.
            self.on_retrieve_targets(None)

        dlg.Destroy()


    ####################################################################################################################
    def on_right_click_popup_delete_target (self, event):
        '''
        Right click event handler for popup delete target menu selection.
        '''

        if not self.selected:
            return

        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        selected = self.GetPyData(self.selected)

        dlg = wx.MessageDialog(self, "Delete target: %s?" % selected["target"], "Confirm", wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)
        if dlg.ShowModal() == wx.ID_YES:
            cursor = mysql.cursor()
            cursor.execute("DELETE FROM cc_targets WHERE id     = '%d'" % selected["id"])
            cursor.execute("DELETE FROM cc_hits WHERE target_id = '%d'" % selected["id"])
            cursor.execute("DELETE FROM cc_tags WHERE target_id = '%d'" % selected["id"])

            # refresh the targets list.
            self.on_retrieve_targets(None)

        dlg.Destroy()


    ####################################################################################################################
    def on_right_click_popup_load_hits (self, event):
        '''
        Right click event handler for popup load hits menu selection.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)

        self.top.hits.load_hits(selected["id"])


    ####################################################################################################################
    def on_right_click_popup_load_hits_all (self, event):
        '''
        Right click event handler for popup load all hits menu selection.
        '''

        if not self.selected:
            return

        (child, cookie) = self.GetFirstChild(self.selected)
        first_child     = child

        while child:
            data = self.GetPyData(child)

            if child == first_child:
                self.top.hits.load_hits(data["id"])
            else:
                self.top.hits.append_hits(data["id"])

            (child, cookie) = self.GetNextChild(child, cookie)


    ####################################################################################################################
    def on_right_click_popup_export_idc (self, event):
        '''
        Right click event handler for popup export IDA Python menu selection.
        '''

        if not self.selected:
            return

        data = self.GetPyData(self.selected)

        dlg = export_idc_dialog.export_idc_dialog(parent=self, top=self.top, tag_id=data["id"], target_id=data["target_id"])
        dlg.ShowModal()


    ####################################################################################################################
    def on_right_click_popup_filter_tag (self, event):
        '''
        Right click event handler for popup filter tag menu selection.
        '''

        if not self.selected:
            return

        # if the current item being marked for filtering, was the previous stalk ... clear it.
        if self.selected == self.used_for_stalk:
            self.used_for_stalk = None

        data             = self.GetPyData(self.selected)
        data["filtered"] = True

        self.SetPyData(self.selected, data)

        # set the icon for the selected item for filter.
        self.SetItemImage(self.selected, self.icon_filtered, wx.TreeItemIcon_Normal)

        # add the target / tag id pair to the top level filtered list.
        pair = (data["target_id"], data["id"])

        if not self.top.filter_list.count(pair):
            self.top.filter_list.append(pair)


    ####################################################################################################################
    def on_right_click_popup_properties (self, event):
        '''
        Right click event handler for popup export IDA Python menu selection.
        '''

        if not self.selected:
            return

        data = self.GetPyData(self.selected)

        dlg = target_properties.target_properties(parent=self, top=self.top, tag_id=data["id"], target_id=data["target_id"])
        dlg.ShowModal()


    ####################################################################################################################
    def on_right_click_popup_unfilter_tag (self, event):
        '''
        Right click event handler for popup unfilter tag menu selection.
        '''

        if not self.selected:
            return

        data = self.GetPyData(self.selected)
        del(data["filtered"])

        self.SetPyData(self.selected, data)

        # set the icon for the selected item for normal.
        self.SetItemImage(self.selected, self.icon_tag, wx.TreeItemIcon_Normal)

        # remove the target / tag id pair from the top level filtered list.
        self.top.filter_list.remove((data["target_id"], data["id"]))


    ####################################################################################################################
    def on_right_click_popup_use_for_stalk (self, event):
        '''
        Right click event handler for popup use for stalk menu selection.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)
        mysql    = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        # ensure the selected tag doesn't already contain data.
        cursor = mysql.cursor()
        cursor.execute("SELECT COUNT(tag_id) AS count FROM cc_hits WHERE tag_id = '%d'" % selected["id"])
        hit_count = cursor.fetchall()[0][0]

        # if it does, ensure the user wants to overwrite the existing data.
        if hit_count != 0:
            dlg = wx.MessageDialog(self, "Selected tag already contains %d hits, overwrite?" % hit_count, "Confirm", wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)

            if dlg.ShowModal() == wx.ID_YES:
                cursor = mysql.cursor()
                cursor.execute("DELETE FROM cc_hits WHERE tag_id = '%d'" % selected["id"])
                dlg.Destroy()
            else:
                dlg.Destroy()
                return

        # clear the icon from the last item selected for stalking.
        if self.used_for_stalk:
            self.SetItemImage(self.used_for_stalk, self.icon_tag, wx.TreeItemIcon_Normal)

        # set the icon for the selected item for stalking.
        self.SetItemImage(self.selected, self.icon_selected, wx.TreeItemIcon_Normal)
        self.used_for_stalk = self.selected

        # grab the data structure for the selected item.
        data = self.GetPyData(self.selected)

        self.top.stalk_tag = data
        self.top.msg("Using '%s' as stalking tag." % data["tag"])


    ####################################################################################################################
    def on_right_click_popup_sync_udraw (self, event):
        '''
        Right click event handler for popup synchronize with uDraw menu selection.
        '''

        if not self.selected:
            return

        selected   = self.GetPyData(self.selected)
        self.udraw = self.top.main_frame.udraw
        mysql      = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        if not self.udraw:
            self.top.err("No available connection to uDraw(Graph) server.")
            return

        self.udraw.set_command_handler("node_double_click",      self.on_udraw_node_double_click)
        self.udraw.set_command_handler("node_selections_labels", self.on_udraw_node_selections_labels)

        self.cc = utils.code_coverage.code_coverage(mysql=mysql)
        self.cc.import_mysql(selected["target_id"], selected["id"])

        self.udraw_last_color     = None
        self.udraw_last_color_id  = None
        self.udraw_last_selected  = None
        self.udraw_base_graph     = None
        self.udraw_current_graph  = None
        self.udraw_hit_funcs      = []
        self.udraw_in_function    = False
        no_modules                = []

        for hit_list in self.cc.hits.values():
            hit = hit_list[0]

            # we can't graph what we don't have a module loaded for.
            if not self.top.pida_modules.has_key(hit.module):
                if not no_modules.count(hit.module):
                    no_modules.append(hit.module)
                    self.top.err("Necessary module '%s' to build part of graph missing, ignoring." % hit.module)
                continue

            # rebase the module if necessary.
            if hit.base and hit.base != self.top.pida_modules[hit.module].base:
                self.top.msg("Rebasing %s..." % hit.module)
                self.top.pida_modules[hit.module].rebase(hit.base)
                self.top.msg("Done. Rebased to %08x" % self.top.pida_modules[hit.module].base)

            # initially we are only going to graph the hit functions. so determine the function containing the hit.
            function = self.top.pida_modules[hit.module].find_function(hit.eip)

            if not function:
                self.top.err("Function containing %08x not found?!?" % hit.eip)
                continue

            # don't need to count functions more then once.
            if self.udraw_hit_funcs.count(function.ea_start):
                continue

            self.udraw_hit_funcs.append(function.ea_start)

            if not self.udraw_base_graph:
                self.udraw_base_graph = self.top.pida_modules[hit.module].graph_proximity(function.ea_start, 1, 1)
            else:
                tmp = self.top.pida_modules[hit.module].graph_proximity(function.ea_start, 1, 1)
                self.udraw_base_graph.graph_cat(tmp)

            # highlight the hit functions.
            self.udraw_base_graph.nodes[function.ea_start].color = 0xFF8000

        # if there is no graph to display, return.
        if not self.udraw_base_graph:
            self.top.err("Generated graph contains nothing to display.")
            return

        # set the initial function proximity graph and the current graph and display it.
        self.udraw_current_graph = self.udraw_base_graph
        self.udraw.graph_new(self.udraw_current_graph)

        # thread out the udraw connector message loop.
        thread.start_new_thread(self.udraw.message_loop, (None, None))


    ####################################################################################################################
    def on_retrieve_targets (self, event):
        '''
        Connect to the specified MySQL database, retrieve the target/tag list and propogate our custom list control.
        '''

        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        # make a record of the currently selected item so that we can unfold back to it in the event that we are simply
        # refreshing the tree control.
        selected = self.GetSelection()
        restore  = None

        if selected:
            selected = self.GetPyData(selected)

        # clear out the tree.
        self.DeleteChildren(self.root)

        if self.top.filter_list or self.top.stalk_tag:
            self.top.msg("Resetting filter list and stalk tag.")
            self.top.filter_list = []
            self.top.stalk_tag   = None

        # step through the list of targets.
        targets = mysql.cursor(MySQLdb.cursors.DictCursor)
        targets.execute("SELECT id, target FROM cc_targets ORDER BY target ASC")

        for target in targets.fetchall():
            target_to_append = self.AppendItem(self.root, target["target"])

            # if a previous item was selected, and it matches the id of the target we are adding, then set this
            # entry as the restore item.
            if selected and selected.has_key("target") and selected["id"] == target["id"]:
                restore = target_to_append

            self.SetPyData(target_to_append, target)
            self.SetItemImage(target_to_append, self.icon_folder,      wx.TreeItemIcon_Normal)
            self.SetItemImage(target_to_append, self.icon_folder_open, wx.TreeItemIcon_Expanded)

            # step through the tags for this target.
            tags = mysql.cursor(MySQLdb.cursors.DictCursor)
            tags.execute("SELECT id, target_id, tag FROM cc_tags WHERE target_id = '%d' ORDER BY tag ASC" % target["id"])

            for tag in tags.fetchall():
                tag_to_append = self.AppendItem(target_to_append, tag["tag"])

                # if a previous item was selected, and it matches the id of the tag we are adding, then set this entry
                # as the restore item.
                if selected and selected.has_key("tag") and selected["id"] == tag["id"]:
                    restore = tag_to_append

                self.SetPyData(tag_to_append, tag)
                self.SetItemImage(tag_to_append, self.icon_tag, wx.TreeItemIcon_Normal)

        # expand the tree.
        self.Expand(self.root)

        # if there was a previously selected item and it was found in the refreshed list, select it.
        if restore:
            self.SelectItem(restore)


    ####################################################################################################################
    def on_target_activated (self, event):
        '''
        Make record of the selected target/tag combination.
        '''

        if not self.selected:
            return

        selected = self.GetPyData(self.selected)

        # root node.
        if selected == None:
            pass

        # target node.
        elif selected.has_key("target"):
            pass

        # tag node.
        elif selected.has_key("tag"):
            pass


    ####################################################################################################################
    def on_target_right_click (self, event):
        if not self.selected:
            return

        # there's some weird case where if you click fast enough .x/.y don't exist. this catches that.
        try:
            if not self.x or not self.y:
                raise Exception
        except:
            return

        selected = self.GetPyData(self.selected)

        # root node.
        if selected == None:
            # we only have to do this once, that is what the hasattr() check is for.
            if not hasattr(self, "right_click_popup_add_target"):
                self.right_click_popup_add_target = wx.NewId()
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_add_target, id=self.right_click_popup_add_target)

            # make a menu.
            menu = wx.Menu()
            menu.Append(self.right_click_popup_add_target, "Add Target")

            self.PopupMenu(menu, (self.x, self.y))
            menu.Destroy()

        # target node.
        elif selected.has_key("target"):
            # we only have to do this once, that is what the hasattr() check is for.
            if not hasattr(self, "right_click_popup_add_tag"):
                self.right_click_popup_add_tag       = wx.NewId()
                self.right_click_popup_delete_target = wx.NewId()
                self.right_click_popup_load_hits_all = wx.NewId()

                self.Bind(wx.EVT_MENU, self.on_right_click_popup_add_tag,       id=self.right_click_popup_add_tag)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_delete_target, id=self.right_click_popup_delete_target)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_load_hits_all, id=self.right_click_popup_load_hits_all)

            # make a menu.
            menu = wx.Menu()
            menu.Append(self.right_click_popup_add_tag, "Add Tag")
            menu.AppendSeparator()
            menu.Append(self.right_click_popup_load_hits_all, "Load All Hits")
            menu.AppendSeparator()
            menu.Append(self.right_click_popup_delete_target, "Delete Target")

            self.PopupMenu(menu, (self.x, self.y))
            menu.Destroy()

        # tag node.
        elif selected.has_key("tag"):
            # we only have to do this once, that is what the hasattr() check is for.
            if not hasattr(self, "right_click_popup_load_hits"):
                self.right_click_popup_load_hits     = wx.NewId()
                self.right_click_popup_append_hits   = wx.NewId()
                self.right_click_popup_export_idc    = wx.NewId()
                self.right_click_popup_sync_udraw    = wx.NewId()
                self.right_click_popup_use_for_stalk = wx.NewId()
                self.right_click_popup_filter_tag    = wx.NewId()
                self.right_click_popup_unfilter_tag  = wx.NewId()
                self.right_click_popup_clear_tag     = wx.NewId()
                self.right_click_popup_expand_tag    = wx.NewId()
                self.right_click_popup_properties    = wx.NewId()
                self.right_click_popup_delete_tag    = wx.NewId()

                self.Bind(wx.EVT_MENU, self.on_right_click_popup_load_hits,     id=self.right_click_popup_load_hits)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_append_hits,   id=self.right_click_popup_append_hits)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_export_idc,    id=self.right_click_popup_export_idc)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_sync_udraw,    id=self.right_click_popup_sync_udraw)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_use_for_stalk, id=self.right_click_popup_use_for_stalk)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_filter_tag,    id=self.right_click_popup_filter_tag)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_unfilter_tag,  id=self.right_click_popup_unfilter_tag)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_clear_tag,     id=self.right_click_popup_clear_tag)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_expand_tag,    id=self.right_click_popup_expand_tag)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_properties,    id=self.right_click_popup_properties)
                self.Bind(wx.EVT_MENU, self.on_right_click_popup_delete_tag,    id=self.right_click_popup_delete_tag)

            # make a menu.
            menu = wx.Menu()
            menu.Append(self.right_click_popup_load_hits, "Load Hits")
            menu.Append(self.right_click_popup_append_hits, "Append Hits")
            menu.Append(self.right_click_popup_export_idc, "Export to IDA")
            menu.Append(self.right_click_popup_sync_udraw, "Sync with uDraw")
            menu.AppendSeparator()
            menu.Append(self.right_click_popup_use_for_stalk, "Use for Stalking")

            if selected.has_key("filtered"):
                menu.Append(self.right_click_popup_unfilter_tag, "Remove Tag Filter")
            else:
                menu.Append(self.right_click_popup_filter_tag, "Filter Tag")

            menu.Append(self.right_click_popup_clear_tag, "Clear Tag")
            menu.Append(self.right_click_popup_expand_tag, "Expand Tag")
            menu.Append(self.right_click_popup_properties, "Target/Tag Properties")
            menu.AppendSeparator()
            menu.Append(self.right_click_popup_delete_tag, "Delete Tag")

            self.PopupMenu(menu, (self.x, self.y))
            menu.Destroy()


    ####################################################################################################################
    def on_target_right_down (self, event):
        '''
        Grab the x/y coordinates when the right mouse button is clicked.
        '''

        self.x = event.GetX()
        self.y = event.GetY()

        item, flags = self.HitTest((self.x, self.y))

        if flags & wx.TREE_HITTEST_ONITEM:
            self.SelectItem(item)
        else:
            self.x = None
            self.y = None


    ####################################################################################################################
    def on_target_sel_changed (self, event):
        '''
        Update the current selected tree control item on every selection change.
        '''

        self.selected = event.GetItem()


    ####################################################################################################################
    def on_udraw_node_selections_labels (self, udraw, args):
        '''
        uDraw callback handler for node selection.
        '''

        try:
            self.udraw_last_selected = args
            selected = long(self.udraw_last_selected[0], 16)
        except:
            return

        # update the focus in the hit list control.
        self.top.hits.focus_item_by_address(selected)

        # highlight the selected node in udraw.
        self.udraw_focus_node_by_address(selected)


    ####################################################################################################################
    def on_udraw_node_double_click (self, udraw, args):
        '''
        uDraw callback handler for node double click.
        '''

        selected = long(self.udraw_last_selected[0], 16)

        # if the activated node is a hit function, expand it.
        if selected in self.udraw_hit_funcs:
            self.udraw_change_view(selected, base=self.udraw_in_function)


    ####################################################################################################################
    def udraw_change_view (self, selected, base=False):
        '''
        Swap the current view with a function view / the calculated base graph.
        '''

        # back out to base graph.
        if base:
            self.udraw_current_graph = self.udraw_base_graph
            self.udraw_in_function   = False
            window_title             = ""

        # drill down into a function
        else:
            self.udraw_current_graph = self.udraw_base_graph.nodes[selected]
            self.udraw_in_function   = True
            window_title             = self.udraw_base_graph.nodes[selected].name

            # highlight the hit basic blocks within the function.
            for hit_list in self.cc.hits.values():
                hit = hit_list[0]

                if self.udraw_current_graph.nodes.has_key(hit.eip):
                    self.udraw_current_graph.nodes[hit.eip].color = 0xFF8000

        # render the new graph.
        self.udraw.graph_new(self.udraw_current_graph)
        self.udraw.window_title(window_title)
        self.udraw_focus_node_by_address(selected)


    ####################################################################################################################
    def udraw_focus_node_by_address (self, address):
        '''
        Focus and highlight the requested node. Restore the original color of any previously focused node.

        @type  address: DWORD
        @param address: Address of node to focus and highlight
        '''

        # if there is no connection to udraw, return.
        if not self.udraw_current_graph or not self.udraw:
            return

        # restore the last highlighted nodes color.
        if self.udraw_last_color:
            try:
                self.udraw.change_element_color("node", self.udraw_last_color_id, self.udraw_last_color)
                self.udraw_last_color = self.udraw_last_color_id = None
            except:
                self.top.err("Connection to uDraw severed.")
                self.udraw = None
                return

        # if the current view doesn't have the requested address.
        if not self.udraw_current_graph.nodes.has_key(address):
            # determine if it belongs to one of the hit functions.
            containing_function = None

            for hit_func in self.udraw_hit_funcs:
                if address in self.udraw_base_graph.nodes[hit_func].nodes.keys():
                    containing_function = hit_func

            # if the address could not be found in any of the hit functions, then return.
            if not containing_function:
                self.top.err("Could not locate containing function for %08x" % address)
                return

            # switch to function view.
            if containing_function == address:
                self.udraw_change_view(containing_function, base=True)
            else:
                self.udraw_change_view(containing_function, base=False)

        try:
            # save the color and id for restoring in the next iteration.
            self.udraw_last_color     = self.udraw_current_graph.nodes[address].color
            self.udraw_last_color_id  = address

            # focus and highlight the requested node.
            self.udraw.focus_node(address)
            self.udraw.change_element_color("node", address, 0x0080FF)
        except:
            self.top.err("Unable to locate %08x" % address)
########NEW FILE########
__FILENAME__ = target_properties
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: target_properties.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import MySQLdb

########################################################################################################################
class target_properties (wx.Dialog):
    '''
    View and update the properties of any given target/tag combination.
    '''

    def __init__(self, *args, **kwds):
        self.parent    = kwds["parent"]
        self.top       = kwds["top"]
        self.tag_id    = kwds["tag_id"]
        self.target_id = kwds["target_id"]

        # we remove our added dictionary args as wxDialog will complain about them if we don't.
        del(kwds["top"])
        del(kwds["tag_id"])
        del(kwds["target_id"])

        # ensure a MySQL connection is available.
        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        # begin wxGlade: target_properties.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.target_id_static = wx.StaticText(self, -1, "Target: %d" % self.target_id)
        self.target           = wx.TextCtrl(self, -1, "")
        self.tag_id_static    = wx.StaticText(self, -1, "Tag: %d" % self.tag_id)
        self.tag              = wx.TextCtrl(self, -1, "")
        self.notes_static     = wx.StaticText(self, -1, "Notes:")
        self.notes            = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        self.apply_changes    = wx.Button(self, -1, "Apply Changes")
        self.close            = wx.Button(self, -1, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        # event handlers.
        self.Bind(wx.EVT_BUTTON, self.on_apply_changes, self.apply_changes)
        self.Bind(wx.EVT_BUTTON, self.on_close,         self.close)

        # initialize the text controls with the most recent content from the database.
        cursor = mysql.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT tags.*, targets.target FROM cc_targets AS targets, cc_tags AS tags WHERE tags.id = '%d' and targets.id = '%d'" % (self.tag_id, self.target_id))
        hit = cursor.fetchall()[0]
        self.target.SetValue("%s" % hit["target"])
        self.tag.SetValue("%s" % hit["tag"])
        self.notes.SetValue("%s" % hit["notes"])


    ####################################################################################################################
    def __set_properties(self):
        # begin wxGlade: target_properties.__set_properties
        self.SetTitle("Target Properties")
        self.SetSize((500, 300))
        self.target.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Courier New"))
        self.tag.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Courier New"))
        self.notes.SetFont(wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Courier New"))
        # end wxGlade


    ####################################################################################################################
    def __do_layout(self):
        # begin wxGlade: target_properties.__do_layout
        sizer_14 = wx.BoxSizer(wx.VERTICAL)
        sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_14.Add(self.target_id_static, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_14.Add(self.target, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_14.Add(self.tag_id_static, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_14.Add(self.tag, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_14.Add(self.notes_static, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_14.Add(self.notes, 4, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_15.Add(self.apply_changes, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_15.Add(self.close, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_14.Add(sizer_15, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_14)
        self.Layout()
        # end wxGlade


    ####################################################################################################################
    def on_apply_changes (self, event):
        '''
        Commit changes to database.
        '''

        # ensure a MySQL connection is available.
        mysql = self.top.main_frame.mysql

        if not mysql:
            self.top.err("No available connection to MySQL server.")
            return

        # grab and SQL sanitize the text fields from the dialog.
        target = self.target.GetLineText(0).replace("\\", "\\\\").replace("'", "\\'")
        tag    = self.tag.GetLineText(0).replace("\\", "\\\\").replace("'", "\\'")
        notes  = self.notes.GetValue().replace("\\", "\\\\").replace("'", "\\'")

        cursor = mysql.cursor()
        cursor.execute("UPDATE cc_targets SET target = '%s' WHERE id = '%d'" % (target, self.target_id))
        cursor.execute("UPDATE cc_tags SET tag = '%s', notes = '%s' WHERE id = '%d' AND target_id = '%d'" % (tag, notes, self.tag_id, self.target_id))

        # refresh the targets list.
        self.parent.on_retrieve_targets(None)

        # close the dialog.
        self.Destroy()


    ####################################################################################################################
    def on_close (self, event):
        '''
        Ignore any changes and close the dialog.
        '''

        self.Destroy()
########NEW FILE########
__FILENAME__ = about
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: about.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx

class about(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]
        
        # begin wxGlade: about.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.about_logo = wx.StaticBitmap(self, -1, wx.Bitmap(self.parent.cwd + "/images/about.bmp", wx.BITMAP_TYPE_ANY))
        self.about = wx.TextCtrl(self, -1, "PaiMei Console\n\nCopyright 2006 Pedram Amini\n<pedram.amini@gmail.com>\n\nhttp://www.openrce.org", style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        self.ok = wx.Button(self, -1, "Close")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_close, self.ok)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: about.__set_properties
        self.SetTitle("About PaiMei")
        self.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.about.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.ok.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: about.__do_layout
        sizer_8 = wx.BoxSizer(wx.VERTICAL)
        sizer_8.Add(self.about_logo, 0, wx.ADJUST_MINSIZE, 0)
        sizer_8.Add(self.about, 5, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_8.Add(self.ok, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_8)
        sizer_8.Fit(self)
        sizer_8.SetSizeHints(self)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_close(self, event): # wxGlade: about.<event_handler>
        self.Destroy()



########NEW FILE########
__FILENAME__ = mysql_connect_dialog
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: mysql_connect_dialog.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import MySQLdb

class mysql_connect_dialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]

        # begin wxGlade: mysql_connect_dialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.mysql_logo = wx.StaticBitmap(self, -1, wx.Bitmap(self.parent.cwd + "/images/mysql.bmp", wx.BITMAP_TYPE_ANY))
        self.host_static = wx.StaticText(self, -1, "MySQL Host:")
        self.username_static = wx.StaticText(self, -1, "MySQL User:")
        self.password_static = wx.StaticText(self, -1, "MySQL Passwd:")
        self.connect = wx.Button(self, -1, "Connect")

        # if the main frame already contains mysql values, then use them.
        if self.parent.mysql_host:     self.host = wx.TextCtrl(self, -1, self.parent.mysql_host)
        else:                          self.host = wx.TextCtrl(self, -1, "localhost")

        if self.parent.mysql_username: self.username = wx.TextCtrl(self, -1, self.parent.mysql_username)
        else:                          self.username = wx.TextCtrl(self, -1, "root")

        if self.parent.mysql_password: self.password = wx.TextCtrl(self, -1, self.parent.mysql_password, style=wx.TE_PASSWORD)
        else:                          self.password = wx.TextCtrl(self, -1, "", style=wx.TE_PASSWORD)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_connect, self.connect)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: mysql_connect_dialog.__set_properties
        self.SetTitle("MySQL Connect")
        self.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.host_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.host.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.username_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.username.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.password_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.password.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.connect.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.connect.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: mysql_connect_dialog.__do_layout
        sizer_4 = wx.BoxSizer(wx.VERTICAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        mysql_options = wx.GridSizer(3, 2, 0, 0)
        sizer_5.Add(self.mysql_logo, 0, wx.ADJUST_MINSIZE, 0)
        sizer_5.Add((10, 20), 0, wx.ADJUST_MINSIZE, 0)
        mysql_options.Add(self.host_static, 0, wx.ADJUST_MINSIZE, 0)
        mysql_options.Add(self.host, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        mysql_options.Add(self.username_static, 0, wx.ADJUST_MINSIZE, 0)
        mysql_options.Add(self.username, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        mysql_options.Add(self.password_static, 0, wx.ADJUST_MINSIZE, 0)
        mysql_options.Add(self.password, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(mysql_options, 0, wx.EXPAND, 0)
        sizer_4.Add(sizer_5, 1, wx.EXPAND, 0)
        sizer_4.Add(self.connect, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_4)
        sizer_4.Fit(self)
        sizer_4.SetSizeHints(self)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_connect(self, event): # wxGlade: mysql_connect_dialog.<event_handler>
        host     = self.host.GetLineText(0)
        username = self.username.GetLineText(0)
        password = self.password.GetLineText(0)

        # bubble up the form values to the main frame for possible persistent storage.
        self.parent.mysql_host     = host
        self.parent.mysql_username = username
        self.parent.mysql_password = password

        self.mysql_connect(host, username, password)
        self.Destroy()

    def mysql_connect (self, host, username, password):
        try:
            self.parent.mysql = MySQLdb.connect(host=host, user=username, passwd=password, db="paimei")
        except MySQLdb.OperationalError, err:
            self.parent.status_bar.SetStatusText("Failed connecting to MySQL server: %s" % err[1])
            return

        self.parent.status_bar.SetStatusText("Successfully connected to MySQL server at %s." % host)
        self.parent.status_bar.SetStatusText("MySQL: %s" % host, 2)
########NEW FILE########
__FILENAME__ = pydbg_locale_dialog
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: pydbg_locale_dialog.py 210 2007-08-02 00:15:19Z pedram $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import sys

sys.path.append("..")

from pydbg import *

class pydbg_locale_dialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]

        # begin wxGlade: pydbg_locale_dialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.pydbg_logo = wx.StaticBitmap(self, -1, wx.Bitmap(self.parent.cwd + "/images/pydbg.bmp", wx.BITMAP_TYPE_ANY))
        self.host_static = wx.StaticText(self, -1, "Host:")
        self.port_static = wx.StaticText(self, -1, "Port:")
        self.set_locale = wx.Button(self, -1, "Set Locale")

        # if the main_frame already contains pydbg locale values, use them.
        if self.parent.pydbg_host: self.host = wx.TextCtrl(self, -1, self.parent.pydbg_host)
        else:                      self.host = wx.TextCtrl(self, -1, "localhost")

        if self.parent.pydbg_port: self.port = wx.TextCtrl(self, -1, str(self.parent.pydbg_port))
        else:                      self.port = wx.TextCtrl(self, -1, "")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_set_locale, self.set_locale)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: pydbg_locale_dialog.__set_properties
        self.SetTitle("PyDbg Locale")
        self.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.host_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.host.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.port_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.port.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.set_locale.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: pydbg_locale_dialog.__do_layout
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        pydbg_options = wx.GridSizer(2, 2, 0, 0)
        sizer_7.Add(self.pydbg_logo, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7.Add((10, 20), 0, wx.ADJUST_MINSIZE, 0)
        pydbg_options.Add(self.host_static, 0, wx.ADJUST_MINSIZE, 0)
        pydbg_options.Add(self.host, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        pydbg_options.Add(self.port_static, 0, wx.ADJUST_MINSIZE, 0)
        pydbg_options.Add(self.port, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_6.Add(pydbg_options, 0, wx.EXPAND, 0)
        sizer_6.Add(self.set_locale, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_7.Add(sizer_6, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_7)
        sizer_7.Fit(self)
        sizer_7.SetSizeHints(self)
        self.Layout()
        self.Centre()
        # end wxGlade

    def on_set_locale(self, event): # wxGlade: pydbg_locale_dialog.<event_handler>
        try:
            host = self.host.GetLineText(0)
            port = int(self.port.GetLineText(0))
        except:
            pass

        # bubble up the form values to the main frame for possible persistent storage.
        self.parent.pydbg_host = host
        self.parent.pydbg_port = port

        self.pydbg_set_locale(host, port)
        self.Destroy()

    def pydbg_set_locale (self, host, port):
        if host not in ("localhost", "127.0.0.1") and type(port) is int:
            try:
                self.parent.pydbg = pydbg_client(host, port)
                self.parent.status_bar.SetStatusText("Successfully connected to PyDbg server on %s:%d" % (host, port))
                self.parent.status_bar.SetStatusText("PyDbg: %s" % host, 3)
            except:
                self.parent.status_bar.SetStatusText("Failed connecting to PyDbg server on %s:%d" % (host, port))
        else:
            self.parent.pydbg = pydbg()
########NEW FILE########
__FILENAME__ = udraw_connect_dialog
#
# PaiMei
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: udraw_connect_dialog.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import wx
import sys

sys.path.append("..")

import utils

class udraw_connect_dialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        self.parent = kwds["parent"]

        # begin wxGlade: udraw_connect_dialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.udraw_logo = wx.StaticBitmap(self, -1, wx.Bitmap(self.parent.cwd + "/images/udraw.bmp", wx.BITMAP_TYPE_ANY))
        self.host_static = wx.StaticText(self, -1, "Host:")
        self.port_static = wx.StaticText(self, -1, "Port:")
        self.connect = wx.Button(self, -1, "Connect")

        # if the main_frame already contains udraw values, use them.
        if self.parent.udraw_host: self.host = wx.TextCtrl(self, -1, self.parent.udraw_host)
        else:                      self.host = wx.TextCtrl(self, -1, "127.0.0.1")

        if self.parent.udraw_port: self.port = wx.TextCtrl(self, -1, str(self.parent.udraw_port))
        else:                      self.port = wx.TextCtrl(self, -1, "2542")

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.on_connect, self.connect)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: udraw_connect_dialog.__set_properties
        self.SetTitle("uDraw(Graph) Connect")
        self.host_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.host.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.port_static.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.port.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.connect.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, "MS Shell Dlg 2"))
        self.connect.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: udraw_connect_dialog.__do_layout
        sizer_7_copy = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6_copy = wx.BoxSizer(wx.VERTICAL)
        udraw_options = wx.GridSizer(2, 2, 0, 0)
        sizer_7_copy.Add(self.udraw_logo, 0, wx.ADJUST_MINSIZE, 0)
        sizer_7_copy.Add((10, 20), 0, wx.ADJUST_MINSIZE, 0)
        udraw_options.Add(self.host_static, 0, wx.ADJUST_MINSIZE, 0)
        udraw_options.Add(self.host, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        udraw_options.Add(self.port_static, 0, wx.ADJUST_MINSIZE, 0)
        udraw_options.Add(self.port, 1, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_6_copy.Add(udraw_options, 0, wx.EXPAND, 0)
        sizer_6_copy.Add(self.connect, 0, wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        sizer_7_copy.Add(sizer_6_copy, 1, wx.EXPAND, 0)
        self.SetAutoLayout(True)
        self.SetSizer(sizer_7_copy)
        sizer_7_copy.Fit(self)
        sizer_7_copy.SetSizeHints(self)
        self.Layout()
        # end wxGlade

    def on_connect(self, event): # wxGlade: udraw_connect_dialog.<event_handler>
        try:
            host = self.host.GetLineText(0)
            port = int(self.port.GetLineText(0))
        except:
            self.parent.status_bar.SetStatusText("Invalid hostname / port combination")
            self.Destroy()
            return

        # bubble up the form values to the main frame for possible persistent storage.
        self.parent.udraw_host = host
        self.parent.udraw_port = port

        self.udraw_connect(host, port)
        self.Destroy()

    def udraw_connect (self, host, port):
        try:
            self.parent.udraw = utils.udraw_connector(host, port)
        except:
            self.parent.status_bar.SetStatusText("Failed connecting to uDraw(Graph) server.")
            return

        self.parent.status_bar.SetStatusText("Successfully connected to uDraw(Graph) server at %s." % host)
        self.parent.status_bar.SetStatusText("uDraw: %s" % host, 4)
########NEW FILE########
__FILENAME__ = crash_bin_explorer
#!c:\\python\\python.exe

"""
Crash Bin Explorer
Copyright (C) 2007 Pedram Amini <pedram.amini@gmail.com>

$Id: crash_bin_explorer.py 231 2008-07-21 22:43:36Z pedram.amini $

Description:
    Command line utility for exploring the results stored in serialized crash bin files. You can list all crashes
    categorized in buckets, view the details of a specific crash, or generate a graph of all crashes and crash paths
    based on stack-walk information.

    The 'extra' field is what specifies the test case number. It's up to you to label your test cases in however manner
    is appropriate to you.
"""

import getopt
import sys

import utils
import pgraph

USAGE = "\nUSAGE: crashbin_explorer.py <xxx.crashbin>"                                      \
        "\n    [-t|--test id]     dump the crash synopsis for a specific test case id"      \
        "\n    [-g|--graph name] generate a graph of all crash paths, save to 'name'.udg\n"

#
# parse command line options.
#

try:
    if len(sys.argv) < 2:
        raise Exception

    opts, args = getopt.getopt(sys.argv[2:], "t:g:", ["test=", "graph="])
except:
    print USAGE
    sys.exit(1)

test_id = graph_name = graph = None

for opt, arg in opts:
    if opt in ("-t", "--test"):  test_id    = arg
    if opt in ("-g", "--graph"): graph_name = arg

try:
    crashbin = utils.crash_binning.crash_binning()
    crashbin.import_file(sys.argv[1])
except:
    print "unable to open crashbin: '%s'." % sys.argv[1]
    sys.exit(1)

#
# display the full crash dump of a specific test case
#

if test_id:
    for bin, crashes in crashbin.bins.iteritems():
        for crash in crashes:
            if test_id == crash.extra:
                print crashbin.crash_synopsis(crash)
                sys.exit(0)

#
# display an overview of all recorded crashes.
#

if graph_name:
    graph = pgraph.graph()

for bin, crashes in crashbin.bins.iteritems():
    synopsis = crashbin.crash_synopsis(crashes[0]).split("\n")[0]

    if graph:
        crash_node       = pgraph.node(crashes[0].exception_address)
        crash_node.count = len(crashes)
        crash_node.label = "[%d] %s.%08x" % (crash_node.count, crashes[0].exception_module, crash_node.id)
        graph.add_node(crash_node)

    print "[%d] %s" % (len(crashes), synopsis)
    print "\t",

    for crash in crashes:
        if graph:
            last = crash_node.id
            for entry in crash.stack_unwind:
                address = long(entry.split(":")[1], 16)
                n = graph.find_node("id", address)

                if not n:
                    n       = pgraph.node(address)
                    n.count = 1
                    n.label = "[%d] %s" % (n.count, entry)
                    graph.add_node(n)
                else:
                    n.count += 1
                    n.label = "[%d] %s" % (n.count, entry)

                edge = pgraph.edge(n.id, last)
                graph.add_edge(edge)
                last = n.id
        print "%s," % crash.extra,

    print "\n"

if graph:
    fh = open("%s.udg" % graph_name, "w+")
    fh.write(graph.render_graph_udraw())
    fh.close()
########NEW FILE########
__FILENAME__ = debuggee_procedure_call
#!c:\python\python.exe

#
# PyDbg Debuggee Procedure Call Hack
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: debuggee_procedure_call.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import sys
import struct
import utils

from pydbg import *
from pydbg.defines import *

class __global:
    def __repr__ (self):
        rep = ""

        for key, val in self.__dict__.items():
            if type(val) is int:
                rep += "  %s: 0x%08x, %d\n" % (key, val, val)
            else:
                rep += "  %s: %s\n" % (key, val)

        return rep

allocations   = []           # allocated (address, size) tuples.
cmd_num       = 0            # keep track of executed commands.
glob          = __global()   # provide the user with a globally accessible persistent storage space.
saved_context = None         # saved thread context prior to CALL insertion.
dbg           = pydbg()      # globally accessible pydbg instance.
container     = None         # address of memory allocated for instruction container.

# enable / disable logging here.
#log = lambda x: sys.stdout.write("> " + x + "\n")
log = lambda x: None


########################################################################################################################
def alloc (size):
    '''
    Convenience wrapper around pydbg.virtual_alloc() for easily allocation of read/write memory. This routine maintains
    the global "allocations" table.

    @type  size: Long
    @param size: Size of MEM_COMMIT / PAGE_READWRITE memory to allocate.

    @rtype:  DWORD
    @return: Address of allocated memory.
    '''

    global dbg, allocations

    if not size:
        return

    address = dbg.virtual_alloc(None, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE)

    # make a record of the address/size tuple in the global allocations table.
    allocations.append((address, size))

    return address


########################################################################################################################
def handle_av (dbg):
    '''
    As we are mucking around with process state and calling potentially unknown subroutines, it is likely that we may
    cause an access violation. We register this handler to provide some useful information about the cause.
    '''

    crash_bin = utils.crash_binning.crash_binning()
    crash_bin.record_crash(dbg)

    print crash_bin.crash_synopsis()
    dbg.terminate_process()


########################################################################################################################
def handle_bp (dbg):
    '''
    This callback handler is responsible for establishing and maintaining the command-read loop. This handler seizes
    control-flow at the first chance breakpoint.

    At the command prompt, any Python statement can be executed. To store variables persistently across iterations over
    this routine, use the "glob" global object shell. The built in commands include:

        DONE, GO, G

    For continuing the process. And for calling arbitrary procedures:

        dpc(address, *args, **kwargs)

    For more information, see the inline documentation for dpc(). Note: You *can not* directly assign the return value
    from dpc(). You must explicitly assign Eax, example:

        var = dpc(0xdeadbeef, "pedram")     # INCORRECT

        dpc(0xdeadbeef, "pedram")           # CORRECT
        var = dbg.context.Eax

    @see: dpc()
    '''

    global allocations, cmd_num, saved_context, glob

    log("breakpoint hit")

    if not dbg.first_breakpoint:
        # examine the return value.
        ret      = dbg.context.Eax
        byte_ord = ret & 0xFF
        status   = "procedure call returned: %d 0x%08x" % (ret, ret)
        deref    = dbg.smart_dereference(ret, print_dots=False)

        if byte_ord >= 32 and byte_ord <= 126:
            status += " '%c'" % byte_ord

        if deref != "N/A":
            status += " -> %s" % deref

        print status

    # when we first get control, save the context of the thread we are about to muck around with.
    if not saved_context:
        saved_context = dbg.get_thread_context(dbg.h_thread)

    # command loop.
    while 1:
        try:
            command = raw_input("\n[%03d] CMD> " % cmd_num)
        except:
            return DBG_CONTINUE

        if type(command) is str:
            # cleanup and let the process continue execution.
            if command.upper() in ["DONE", "GO", "G"]:
                dbg.set_thread_context(saved_context)
                free_all()
                break

        try:
            exec(command)
            cmd_num += 1
    
            # implicit "GO" after dpc() commands.
            if type(command) is str and command.lower().startswith("dpc"):
                break
        except:
            sys.stderr.write("failed executing: '%s'.\n" % command)

    log("continuing process")
    return DBG_CONTINUE


########################################################################################################################
def free (address_to_free):
    '''
    Convenience wrapper around pydbg.virtual_free() for easily releasing allocated memory. This routine maintains
    the global "allocations" table.

    @type  address: DWORD
    @param address: Address of memory chunk to free.
    '''

    global dbg, allocations

    for address, size in allocations:
        if address == address_to_free:
            dbg.virtual_free(address, size, MEM_DECOMMIT)

            # remove the address/size tuple from the global allocations table.
            allocations.remove((address, size))


########################################################################################################################
def free_all ():
    '''
    Free all entries in the global allocations table. Useful for when you have done a bunch of testing and want to
    release all the allocated memory.
    '''

    global allocations

    while len(allocations):
        for address, size in allocations:
            free(address)


########################################################################################################################
def dpc (address, *args, **kwargs):
    '''
    This routine is the real core of the script. Given an address and arguments it will allocate and initialize space
    in the debuggee for storing the necessary instructions and arguments and then redirect EIP from the current thread
    to the newly created instructions. A breakpoint is written after the assembled instruction set that is caught by
    our breakpoint handler which re-prompts the user for further commands. Note: You *can not* directly assign the
    return value from dpc(). You must explicitly assign Eax, example:

        var = dpc(0xdeadbeef, "pedram")     # INCORRECT

        dpc(0xdeadbeef, "pedram")           # CORRECT
        var = dbg.context.Eax

    @type  address: DWORD
    @param address: Address of procedure to call.
    @type  args:    List
    @param args:    Arguments to pass to procedure.
    @type  kwargs:  Dictionary (Keys can be one of EAX, EBX, ECX, EDX, ESI, EDI, ESP, EBP, EIP)
    @param kwargs:  Register values to set prior to calling procedure.
    '''

    global dbg, allocations, container

    PUSH = "\x68"
    CALL = "\xE8"
    INT3 = "\xCC"

    # XXX - freeing an address that bp_del is later trying to work on.
    if container:
        pass #free(container)

    # allocate some space for our new instructions and update EIP to point into that new space.
    container = eip = alloc(512)
    dbg.context.Eip = eip

    dbg.set_register("EIP", eip)

    log("setting EIP of thread %d to 0x%08x" % (dbg.dbg.dwThreadId, eip))

    # args are pushed in reverse order, make it a list and reverse it.
    args = list(args)
    args.reverse()

    for arg in args:
        log("processing argument: %s" % arg)

        # if the argument is a string. allocate memory for the string, write it and set the arg to point to the string.
        if type(arg) is str:
            string_address = alloc(len(arg))
            log("  allocated %d bytes for string at %08x" % (len(arg), string_address))
            dbg.write(string_address, arg)
            arg = string_address

        # assemble and write the PUSH instruction.
        assembled = PUSH + struct.pack("<L", arg)
        log("  %08x: PUSH 0x%08x" % (eip, arg))
        dbg.write(eip, assembled)
        eip += len(assembled)

    for reg, arg in kwargs.items():
        log("processing register %s argument: %s" % (reg, arg))

        if reg.upper() not in ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "ESP", "EBP", "EIP"):
            sys.stderr.write(">   invalid register specified: %s\n" % reg)
            continue

        # if the argument is a string. allocate memory for the string, write it and set the arg to point to the string.
        if type(arg) is str:
            string_address = alloc(len(arg))
            log("  allocated %d bytes for string at %08x" % (len(arg), string_address))
            dbg.write(string_address, arg)
            arg = string_address

        # set the appropriate register to contain the argument value.
        dbg.set_register(reg, arg)

    # assemble and write the CALL instruction.
    relative_address = (address - eip - 5)  # -5 for the length of the CALL instruction
    assembled        = CALL + struct.pack("<L", relative_address)

    log("%08x: CALL 0x%08x" % (eip, relative_address))
    dbg.write(eip, assembled)
    eip += len(assembled)

    # set a breakpoint after the call.
    log("setting breakpoint after CALL at %08x" % eip)
    dbg.bp_set(eip, restore=False)


########################################################################################################################
def show_all ():
    '''
    Print a hex dump for all of the tracked allocations.
    '''

    global dbg, allocations

    for address, size in allocations:
        print dbg.hex_dump(dbg.read(address, size), address)


########################################################################################################################
if len(sys.argv) != 2:
    sys.stderr.write("USAGE: debuggee_procedure_call.py <process name | pid>\n")
    sys.exit(1)

dbg.set_callback(EXCEPTION_BREAKPOINT,       handle_bp)
dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, handle_av)

try:
    pid          = int(sys.argv[1])
    found_target = True
except:
    found_target = False
    for (pid, proc_name) in dbg.enumerate_processes():
        if proc_name.lower() == sys.argv[1]:
            found_target = True
            break

print "attaching to %d" % pid

if found_target:
    dbg.attach(pid)
    dbg.debug_event_loop()
else:
    sys.stderr.write("target '%s' not found.\n" % sys.argv[1])
########NEW FILE########
__FILENAME__ = demo_live_graphing
#!c:\python\python.exe

# $Id: demo_live_graphing.py 194 2007-04-05 15:31:53Z cameron $

import thread
import sys
import time

import pida
import pgraph
import utils

from pydbg import *
from pydbg.defines import *


# globals
udraw       = None
first_graph = True
vonage      = None
last_graph  = None
last_center = None

########################################################################################################################

def udraw_node_double_click (udraw, args):
    print "udraw_node_double_click"
    print args

########################################################################################################################

def breakpoint_handler (pydbg):
    global udraw, first_graph, vonage, last_graph, last_center

    if pydbg.first_breakpoint:
        return DBG_CONTINUE

    exception_address = pydbg.exception_address
    
    if first_graph:
        print "drawing graph"
        first_graph = False
        
        last_graph = vonage.graph_proximity(exception_address, 0, 1)
        udraw.graph_new(last_graph)
        #udraw.change_element_color("node", exception_address, 0xFF8000)
        #last_center = exception_address
    else:
        print "updating graph"
        proximity = vonage.graph_proximity(exception_address, 0, 1)
        proximity.graph_sub(last_graph)
        last_graph.graph_cat(proximity)
        udraw.graph_update(proximity)
        #udraw.change_element_color("node", last_center, 0xEEF7FF)
        #udraw.change_element_color("node", exception_address, 0xFF8000)

    # remove the breakpoint once we've hit it.
    pydbg.bp_del(exception_address)

    return DBG_CONTINUE

########################################################################################################################

udraw = utils.udraw_connector()
udraw.set_command_handler("node_double_click", udraw_node_double_click)

# thread out the udraw connector message loop.
thread.start_new_thread(udraw.message_loop, (None, None))

start = time.time()
print "loading vonage.exe.pida ...",
vonage = pida.load("vonage.exe.pida")
print "done. completed in %.02f seconds." % (time.time() - start)

dbg = pydbg()
dbg.set_callback(EXCEPTION_BREAKPOINT, breakpoint_handler)
for (pid, proc) in dbg.enumerate_processes():
    if proc.lower().startswith("x-pro-vonage"):
        break

if not proc.lower().startswith("x-pro-vonage"):
    print "vonage not found"
    sys.exit(1)

dbg.attach(pid)

bps = [function.ea_start for function in vonage.nodes.values() if not function.is_import]
print "setting breakpoints on %d of %d functions" % (len(bps), len(vonage.nodes.values()))
dbg.bp_set(bps, restore=False)

dbg.debug_event_loop()
########NEW FILE########
__FILENAME__ = codenomicrap
#!c:\python\python.exe

#
# Codenomicrap - Codenomicon Test Arbiter
#
# $Id: codenomicrap.py 218 2007-08-29 16:47:56Z pedram $
#

import time
import thread

from pydbg import *
from pydbg.defines import *

# pydbg server IP address and port.
pydbg_host = "10.0.0.1"
pydbg_port = 7373

# target start command.
target_start_command = "vmrun revertToSnapshot xxxx"

# target name. this is the string that will show up in process enumeration for pydbg to look for / attach to.
target_name = "RegSvr.exe"

# codenomicon command line. one format string token is supported to insert the test case number.
codenomicon_command_line = "java -jar sip231.jar --index %d- --to-uri sip:user@192.168.59.131 --from-uri sip:user@localhost --transport tcp"

########################################################################################################################
### SHOULD NOT NEED TO MODIFY BELOW THIS LINE
########################################################################################################################

# global counters.
test_number = crash_number = 1

# global health flag.
target_healthy = True

# time to wait between test cases for a crash.
crash_wait_time = 3

# vmware snapshot revert time.
vmware_revert_wait_time = 60 * 3

########################################################################################################################

def access_violation_handler (debugger, dbg, context):
    global test_number
    global crash_number
    global target_healthy

    print
    print "test case #%d caused access violation #%d" % (test_number, crash_number)
    print

    exception_address = dbg.u.Exception.ExceptionRecord.ExceptionAddress
    write_violation   = dbg.u.Exception.ExceptionRecord.ExceptionInformation[0]
    violation_address = dbg.u.Exception.ExceptionRecord.ExceptionInformation[1]

    # disassemble the instruction the exception occured at.
    disasm = debugger.disasm(exception_address)

    crash_log = open("crash-%d.log" % crash_number, "w+")

    crash_log.write("ACCESS VIOLATION @%08x: %s\n" % (exception_address, disasm))

    if write_violation:
        crash_log.write("violation when attempting to write to %08x\n" % violation_address)
    else:
        crash_log.write("violation when attempting to read from %08x\n" % violation_address)

    mbi = debugger.virtual_query(violation_address)

    crash_log.write("page permissions of violation address: %08x\n" % mbi.Protect)
    crash_log.write("\n")
    crash_log.write(debugger.dump_context(context))
    crash_log.write("\n")
    crash_log.write("call stack at time of crash:\n")

    for address in debugger.stack_unwind():
        crash_log.write("%08x\n" % address)

    crash_log.write("\n")
    crash_log.write("SEH chain at time of crash:\n")

    for address in debugger.seh_unwind():
        crash_log.write("%08x\n" % address)

    crash_log.close()

    # kill this process.
    debugger.terminate_process()

    crash_number  += 1
    target_healthy = false


def start_debugger (debugger, pid):
    debugger.set_callback(EXCEPTION_ACCESS_VIOLATION, access_violation_handler)
    debugger.attach(pid)
    debugger.debug_event_loop()

########################################################################################################################

while 1:
    # start up the target.
    os.system(target_start_command)

    # give the target some time to start up.
    time.sleep(vmware_revert_wait_time)

    debugger = pydbg_client(pydbg_host, pydbg_port)

    for (pid, proc) in debugger.enumerate_processes():
        if proc.lower() == target_name:
            break

    # thread out the debugger.
    thread.start_new_thread(start_debugger, (debugger, pid))

    # loop through test cases while the target is healthy, if it dies the main loop will restart it.
    while target_healthy:
        # generate a test case.
        start = int(time.time())
        os.system(codenomicon_command_line % test_number)
        print "test case #%d took %d seconds to transmit.\r" % (test_number, int(time.time()) - start),

        # give the target a window of opportunity to crash before moving on.
        time.sleep(crash_wait_time)

        # increment the test count
        test_number += 1

    print "target is not healthy ... restarting."

########NEW FILE########
__FILENAME__ = fuzzie
#!c:\python\python.exe

#
# FuzzIE - Internet Explorer CSS Fuzzing Arbiter
#
# $Id: fuzzie.py 218 2007-08-29 16:47:56Z pedram $
#
# REFERENCES:
#
#   - http://msdn.microsoft.com/workshop/browser/webbrowser/reference/objects/internetexplorer.asp
#   - http://bakemono/mediawiki/index.php/Internet_Explorer_Object_Model
#

import os
import time
import thread
from win32com.client import Dispatch

from pydbg import *
from pydbg.defines import *

kernel32        = windll.kernel32
user32          = windll.user32
CLSID           = "{9BA05972-F6A8-11CF-A442-00A0C90A8F39}"
SW_SHOW         = 5

test_number     = 1            # global test number.
crash_number    = 1            # global crash count.
crash_wait_time = 2            # seconds to wait for a crash before moving to next test case.
path            = "fuzzie"     # path to fuzzie directory (assumes c:\).
ie_ok           = True         # global.

########################################################################################################################

def access_violation_handler (debugger, dbg, context):
    global test_number
    global crash_number
    global ie_ok

    print
    print "test case #%d caused access violation #%d" % (test_number, crash_number)
    print

    exception_address = dbg.u.Exception.ExceptionRecord.ExceptionAddress
    write_violation   = dbg.u.Exception.ExceptionRecord.ExceptionInformation[0]
    violation_address = dbg.u.Exception.ExceptionRecord.ExceptionInformation[1]

    # disassemble the instruction the exception occured at.
    disasm = debugger.disasm(exception_address)

    crash_log = open("bin-%d\\crash.log" % crash_number, "w+")

    crash_log.write("ACCESS VIOLATION @%08x: %s\n" % (exception_address, disasm))

    if write_violation:
        crash_log.write("violation when attempting to write to %08x\n" % violation_address)
    else:
        crash_log.write("violation when attempting to read from %08x\n" % violation_address)

    mbi = debugger.virtual_query(violation_address)

    crash_log.write("page permissions of violation address: %08x\n" % mbi.Protect)
    crash_log.write("\n")
    crash_log.write(debugger.dump_context(context))
    crash_log.write("\n")
    crash_log.write("call stack at time of crash:\n")

    for address in debugger.stack_unwind():
        crash_log.write("%08x\n" % address)

    crash_log.write("\n")
    crash_log.write("SEH chain at time of crash:\n")

    for address in debugger.seh_unwind():
        crash_log.write("%08x\n" % address)

    crash_log.close()

    # kill this process.
    debugger.terminate_process()

    crash_number += 1

    # flag the main loop that IE has to be restarted.
    ie_ok = False

    return


def start_debugger (debugger, pid):
    debugger.set_callback(EXCEPTION_ACCESS_VIOLATION, access_violation_handler)
    debugger.attach(pid)
    debugger.debug_event_loop()

########################################################################################################################

while 1:
    # start up IE.
    kernel32.WinExec("c:\\program files\\internet explorer\\iexplore.exe http://bakemono", SW_SHOW)

    # give IE some time to start up.
    time.sleep(1)

    debugger = pydbg()

    for (pid, proc) in debugger.enumerate_processes():
        if proc.lower == "iexplore.exe":
            break

    # thread out debugger.
    thread.start_new_thread(start_debugger, (debugger, pid))

    # IE is healthy and running.
    ie_ok = True

    # ensure the appropriate bin directory exists.
    try:
        os.mkdir("bin-%d" % crash_number)
    except:
        1   # do nothing

    # grab a COM handle to the IE instance we spawned.
    start = int(time.time())
    for ie in Dispatch(CLSID):
        ie_pid = c_ulong()
        user32.GetWindowThreadProcessId(ie.HWND, byref(ie_pid))
        if ie_pid.value == pid:
            break
    print "dispatch took %d seconds.\r" % (int(time.time()) - start),

    # loop through test cases while IE is healthy, if it dies the main loop we restart it.
    while ie_ok:
        # generate a test case.
        start = int(time.time())
        os.system("c:\\ruby\\bin\\ruby.exe bnf_reader.rb > bin-%d\\%d.html" % (crash_number, test_number))
        print "test case gen #%d took %d seconds.\r" % (test_number, int(time.time()) - start),

        # make IE navigate to the generated test case.
        try:
            ie.Navigate("file:///c:/fuzzie/bin-%d/%d.html" % (crash_number, test_number))
        except:
            print
            print "no instance of IE found"
            ie_ok = False

        # give IE a window of opportunity to crash before moving on.
        time.sleep(crash_wait_time)

        # increment the test count
        test_number += 1

    print "IE is not ok ... restarting."

########NEW FILE########
__FILENAME__ = file_access_tracker
#!/usr/bin/env python

'''
    File Access Tracker
    
    Copyright (C) 2006 Cody Pierce <codyrpierce@gmail.com>
    
    Description: This PyDbg script will attempt to track files being read
    or written too during execution. This is especially useful when
    tracking file format vulnerabilities. It is not perfect, and is
    dependent on the size of the file, and method of reading. Libraries
    can be added for tracking, and multiple heaps can also be monitored.

'''

######################################################################
#
# Includes
#
######################################################################

import sys
import os
import struct
import time

from pydbg import *
from pydbg.defines import *
from ctypes import *
import utils


DUPLICATE_SAME_ACCESS = 0x00000002
FILE_CURRENT          = 0x00000001

kernel32 = windll.kernel32

######################################################################
#
# Our data classes
#
######################################################################

class Breakpoint:
    breakpoints = []
    def __init__(self, address):
        self.address = address
    
        return True
    
    def set_breakpoint(self, dbg):
        dbg.bp_set(self.address)
        breakpoints.append(self.address)
       
        return True

######################################################################

class Handle:
    def __init__(self, handle):
        self.handle = handle
        
        return True
        
    def get_handle(self):
        return self.handle

######################################################################
    
class Buffer:
    def __init__(self, address):
        self.address = address
        self.buffer = ""
        
        return True

    def get_address(self):
        return self.address

    def get_buffer(self):
        return self.buffer

######################################################################
#
# Our function breakpoint handlers
#
######################################################################

def handler_breakpoint(dbg):
    if dbg.first_breakpoint:
        if not set_library_hooks(dbg):
            print "[!] Couldnt set breakpoints"
    
            sys.exit(-1)
    
    return DBG_CONTINUE

def restore_guards(dbg): 
    dbg.page_guard_restore() 
    
    return DBG_CONTINUE
    
def handler_buffer(dbg):
    if not dbg.memory_breakpoint_hit:
        return DBG_CONTINUE
    
    module = dbg.addr_to_module(dbg.exception_address).szModule
    for buffer in xrange(0, len(dbg.buffers)):
        if dbg.bp_is_ours_mem(dbg.buffers[buffer]["address"]):
            if module in dbg.filters:
                # We filter some dlls
                return DBG_CONTINUE
            
            if dbg.buffers[buffer]["last_hit"] == dbg.exception_address and dbg.violation_address <= dbg.buffers[buffer]["last_addr"] + 4:
                dbg.buffers[buffer]["loop_count"] -= 1
            else:
                dbg.buffers[buffer]["loop_count"] = dbg.loop_limit
            
            dbg.buffers[buffer]["last_addr"] = dbg.violation_address
            dbg.buffers[buffer]["last_hit"] = dbg.exception_address
            
            if dbg.buffers[buffer]["loop_count"] <= 0:
                #print "[!] Looping"
                                
                return DBG_CONTINUE
            
            print "[*] BP on buffer [%s] [0x%08x] [0x%08x %s]" % (module, dbg.violation_address, dbg.exception_address, dbg.disasm(dbg.exception_address))
            
            #if dbg.mnemonic.startswith("rep"):
            #    dbg.page_guard_clear()
            #    dbg.bp_set(dbg.exception_address + dbg.instruction.length, restore=False, handler=restore_guards)

            dbg.bp_del_mem(dbg.buffers[buffer]["address"])
            #dbg.buffers.remove(dbg.buffers[buffer])
            
            return DBG_CONTINUE
    
    return DBG_CONTINUE

def handler_ReadFile(dbg, args, ret):
    buffer = {"address":args[1],
              "id":0,
              "loop_count":dbg.loop_limit,
              "size":dbg.flip_endian_dword(dbg.read_process_memory(args[3], 4)),
              "handler":handler_buffer,
              "last_addr":0x0,
              "last_hit":0x0}
    hi = args[0]
    requested_bytes = args[2]
    
    for lib in xrange(0, len(dbg.library)):
        if dbg.library[lib]["func"] == "ReadFile":
            break
        
    
    for handle in dbg.handles:
        if handle["id"] == hi:
            if dbg.filename.lower() in handle["filename"].lower():
                dbg.library[lib]["hit"] += 1
                buffer["id"] = dbg.library[lib]["hit"]
                if trackbuffer and buffer["id"] != dbg.trackbuffer:
                    
                    return DBG_CONTINUE
                
                print "[*] ReadFile %s [%d] [%d] Req:%d Read:%d\n[0x%08x][%s]" % (handle["filename"], buffer["id"], handle["id"], requested_bytes, buffer["size"], buffer["address"], dbg.smart_dereference(buffer["address"]))
                
                # print call stack, 15 calls deep
                print "CALL STACK:"
                call_stack = dbg.stack_unwind()
                call_stack.reverse()
                for address in call_stack[:15]:
                    print "%s: 0x%08x" % (dbg.addr_to_module(address).szModule, address)
                print "...\n---------------------"

                for dbgbuffer in dbg.buffers:
                    if buffer["address"] == dbgbuffer:
                        # We already have this buffer
                        return DBG_CONTINUE
                
                dbg.buffers.append(buffer)
                
                # Set up bp on buffer for future use
                if dbg.trackbuffer:
                    dbg.bp_set_mem(buffer["address"], buffer["size"], handler=buffer["handler"])
    
            break
    
    return DBG_CONTINUE

def incremental_read (dbg, addr, length):
    data = ""
    while length:
        try:
            data += dbg.read_process_memory(addr, 1)
        except:
            break

        addr   += 1
        length -= 1

    return data
        

def handler_CreateFileW(dbg, args, ret):
    handle = { "id":0,
               "filename":"",
               "pos":0
             }
    
    filename = dbg.get_unicode_string(incremental_read(dbg, args[0], 255))

    if filename:
        if dbg.filename.lower() in filename.lower():
            print "[*] CreateFileW %s returned 0x%x" % (filename, ret)
    else:
        return DBG_CONTINUE    
    
    handle["id"] = ret
    handle["filename"] = filename
    handle["handle"] = get_handle(dbg, ret)
    
    dbg.handles.append(handle)
    
    return DBG_CONTINUE

def handler_MapViewOfFile(dbg, args, ret):
    print "[*] MapViewOfFile [%x] return [0x%08x]"% (args[0], ret)
    
    return DBG_CONTINUE

def handler_SetFilePointerEx(dbg, args, ret):
    
    return DBG_CONTINUE

def handler_GetFileSizeEx(dbg, args, ret):
    
    return DBG_CONTINUE

def handler__read(dbg, args, ret):
    
    return DBG_CONTINUE

######################################################################
#
# Various set up routines before exection
#
######################################################################

def attach_target_proc(dbg, procname, filename):
    imagename = procname.rsplit('\\')[-1]
    print "[*] Trying to attach to existing %s" % imagename
    for (pid, name) in dbg.enumerate_processes():
        if imagename in name.lower():
            try:
                print "[*] Attaching to %s (%d)" % (name, pid)
                dbg.attach(pid)
            except:
                print "[!] Problem attaching to %s" % name
                
                return False
            
            return True
    
    try:
        print "[*] Trying to load %s %s" % (procname, filename)
        dbg.load(procname, "\"" + filename + "\"")
        
    except:
        print "[!] Problem loading %s %s" % (procname, filename)
        
        return False
    
    return True
     

def set_library_hooks(dbg):
    dbg.hooks = utils.hook_container()
    for lib in dbg.library:
        if not lib["on"]:
            continue
        
        address = dbg.func_resolve(lib["dll"], lib["func"])
        print "[*] Setting hook @ 0x%08x %s!%s" % (address, lib["dll"], lib["func"])
        try:
            dbg.hooks.add(dbg, address, lib["args"], None, lib["handler"])
        except:
            print "[!] Problem setting hook @ 0x%08x %s!%s" % (address, lib["dll"], lib["func"])
            
            return False
    
    return True

def get_handle(dbg, id):
    duped = HANDLE()
    if not kernel32.DuplicateHandle(dbg.h_process, id, kernel32.GetCurrentProcess(), byref(duped), 0, False, DUPLICATE_SAME_ACCESS):
        
        return False
    
    return duped

def close_handle(dbg, id):
    if not kernel32.CloseHandle(handle):
        return False
    
    for hi in xrange(0, len(dbg.handles)):
        if dbg.handles[hi]["id"] == id:
            dbg.handles.remove(hi)
            
            return True

    print "[!] Couldnt find handle id 0x%x" % id
    
    return False

######################################################################
#
# Static variables
#
######################################################################
filters = ["kernel32.dll", "user32.dll", "msvcrt.dll", "ntdll.dll"]
 
library = [{ "id":0,
             "dll":"kernel32",
             "func":"ReadFile",
             "handler":handler_ReadFile,
             "args":5,
             "hit":0,
             "on":True
           },
           { "id":1,
             "dll":"kernel32",
             "func":"CreateFileW",
             "handler":handler_CreateFileW,
             "args":7,
             "hit":0,
             "on":True
           },
           { "id":2,
             "dll":"kernel32",
             "func":"MapViewOfFile",
             "handler":handler_MapViewOfFile,
             "args":5,
             "on":False
           },
           { "id":3,  
             "dll":"kernel32",
             "func":"SetFilePointerEx",
             "handler":handler_SetFilePointerEx,
             "args":4,
             "on":False
           },
           { "id":4,
              "dll":"kernel32",
              "func":"GetFileSizeEx",
              "handler":handler_GetFileSizeEx,
              "args":2,
              "on":False
           },
           { "id":5,
             "dll":"msvcrt",
             "func":"_read",
             "handler":handler__read,
             "args":3,
             "on":True
           }]

handles = []
buffers = []
dbg = ""
loop_limit = 10

######################################################################
#
# Command line arguments
#
######################################################################

if len(sys.argv) < 3:
    print "Usage: %s <process name> <file name to track> [buffer to track]" % sys.argv[0]
    
    sys.exit(-1)

procname = sys.argv[1].lower()
filename = sys.argv[2].lower()
trackbuffer = False

if len(sys.argv) == 4:
    trackbuffer = int(sys.argv[3])

dbg = pydbg()
dbg.filters = filters
dbg.library = library
dbg.handles = handles
dbg.buffers = buffers
dbg.hooks = ""
dbg.procname = procname
dbg.filename = filename
dbg.loop_limit = loop_limit
dbg.trackbuffer = trackbuffer

dbg.set_callback(EXCEPTION_BREAKPOINT, handler_breakpoint)

if not attach_target_proc(dbg, procname, filename):
    print "[!] Couldnt load/attach to %s" % procname
    
    sys.exit(-1)

dbg.debug_event_loop()

print "\nBuffers hit:\n"
for buf in dbg.buffers:
    print "%d" % buf["id"]
    print "=" * 72
    print "Address:      0x%08x" % buf["address"]
    print "Size:         0x%x" % buf["size"]
    print "Last Address: 0x%08x" % buf["last_addr"]
    print "Last Hit:     0x%08x\n" % buf["last_hit"]
########NEW FILE########
__FILENAME__ = file_fuzz_tickler
#!c:\python\python.exe

"""
File Fuzz Tickler
Copyright (C) 2007 Pedram Amini <pedram.amini@gmail.com>

$Id: file_fuzz_tickler.py 222 2007-09-07 20:47:02Z pedram $

Description:
    Say you are fuzzing a file and you find a crash when corrupting a byte at offset X. You take a look at the crash
    dump and it doesn't look very promising. That is when this script comes in. Before you head down the painful path
    of tracking down the issue and determining if it is exploitable or not, apply some brute force:

        - add the original (base line) violating file to the crash bin.
        - fuzz through every 'smart' value at offset X
        - revert byte(s) at offset X to original which caused crash and fuzz through every 'smart' value at offset X-n
        - revert byte(s) at offset X-n to original and fuzz through every 'smart' value at offset X+1
        - choose random values for positions x-8 through x+8 and fuzz 100 times
        - each of these 1,020 test cases is stored in a crash bin so you can easily step through the different crash
          paths. explore with crash_bin_explorer.py utility
"""

import os
import sys
import utils
import struct
import random

from pydbg import *
from pydbg.defines import *

# globals.
try:
    USAGE            = "file_fuzz_ticker.py <parent program> <target file> <offending offset (dec.)> <fuzz width>\n"
    PUSH             = "\x68"
    CALL             = "\xE8"
    KILL_DELAY       = 5000     # milliseconds
    crash_bin        = utils.crash_binning.crash_binning()
    fuzz_library     = []
    max_num          = None
    struct_lengths   = {1:"B", 2:"H", 4:"L"}
    extra            = None

    # argument parsing.
    parent_program   = sys.argv[1]
    target_file      = sys.argv[2]
    offending_offset = int(sys.argv[3])
    fuzz_width       = int(sys.argv[4])
    extension        = "." + target_file.rsplit(".")[-1]
except:
    sys.stderr.write(USAGE)
    sys.exit(1)

# ensure path to parent program is sane.
if not os.path.exists(parent_program):
    sys.stderr.write("Path to parent program invalid: %s\n\n" % parent_program)
    sys.stderr.write(USAGE)
    sys.exit(1)

# ensure path to target file is sane.
if not os.path.exists(target_file):
    sys.stderr.write("Path to target file invalid: %s\n\n" % target_file)
    sys.stderr.write(USAGE)
    sys.exit(1)


########################################################################################################################
def add_integer_boundaries (integer):
    '''
    Add the supplied integer and border cases to the integer fuzz heuristics library.
    '''
    global fuzz_library, fuzz_width, max_num

    for i in xrange(-10, 10):
        case = integer + i

        # ensure the border case falls within the valid range for this field.
        if 0 <= case <= max_num:
            if case not in fuzz_library:
                fuzz_library.append(case)


def av_handler (dbg):
    global crash_bin, extra

    crash_bin.record_crash(dbg, extra)
    dbg.terminate_process()

    return DBG_CONTINUE


def bp_handler (dbg):
    # on initial break-in, create a new thread in the target process which executes:
    #   Sleep(sleep_time);
    #   ExitProcess(69);
    if dbg.first_breakpoint:
        insert_threaded_timer(dbg)

    # this shouldn't happen, but i'd like to know if it does.
    else:
        raw_input("how did we get here?....")

    return DBG_CONTINUE


def do_pydbg_dance (proggie, the_file):
    dbg = pydbg()
    dbg.load(proggie, the_file, show_window=False)
    dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, av_handler)
    dbg.set_callback(EXCEPTION_BREAKPOINT,       bp_handler)

    dbg.run()


def insert_threaded_timer (dbg):
    # resolve the addresses of kernel32.Sleep() and kernel32.ExitProcess()
    Sleep       = dbg.func_resolve_debuggee("kernel32", "Sleep")
    ExitProcess = dbg.func_resolve_debuggee("kernel32", "ExitProcess")

    # allocate some memory for our instructions.
    thread_address = address = dbg.virtual_alloc(None, 512, MEM_COMMIT, PAGE_EXECUTE_READWRITE)

    # assemble and write: PUSH sleep_time
    assembled = PUSH + struct.pack("<L", KILL_DELAY)
    dbg.write(address, assembled)
    address += len(assembled)

    # assemble and write: CALL kernel32.Sleep()
    relative_address = (Sleep - address - 5)  # -5 for the length of the CALL instruction
    assembled = CALL + struct.pack("<L", relative_address)
    dbg.write(address, assembled)
    address += len(assembled)

    # assemble and write: PUSH 69 (exit code)
    assembled = PUSH + struct.pack("<L", 69)
    dbg.write(address, assembled)
    address += len(assembled)

    # assemble and write: CALL kernel32.ExitProcess()
    relative_address = (ExitProcess - address - 5)  # -5 for the length of the CALL instruction
    assembled = CALL + struct.pack("<L", relative_address)
    dbg.write(address, assembled)
    address += len(assembled)

    # start a remote thread
    if not windll.kernel32.CreateRemoteThread(dbg.h_process, None, 0, thread_address, 0, 0, None):
        raise pdx("CreateRemoteThread() failed.", True)
########################################################################################################################


print "[*] tickling target file %s" % target_file
print "[*] through %s" % parent_program
print "[*] at mutant offset %d (0x%x)" % (offending_offset-1, offending_offset-1)
print "[*] with fuzz width %d" % fuzz_width

# initialize our fuzz library based on fuzz width.
max_num = 2** (fuzz_width * 8) - 1

add_integer_boundaries(0)
add_integer_boundaries(max_num / 2)
add_integer_boundaries(max_num / 3)
add_integer_boundaries(max_num / 4)
add_integer_boundaries(max_num / 8)
add_integer_boundaries(max_num / 16)
add_integer_boundaries(max_num / 32)
add_integer_boundaries(max_num)

print "[*] fuzz library initialized with %d entries" % len(fuzz_library)

# add the base line crash to the crash bin.
extra  = "BASELINE"
do_pydbg_dance(parent_program, target_file)

# read and store original data from target file.
fh   = open(target_file, "rb")
data = fh.read()
fh.close()


###########################################################
# fuzz through all possible fuzz values at offending offset.
###

print "[*] fuzzing at offending offset"
i = 0

for value in fuzz_library:
    extra  = "offending: 0x%x" % value
    top    = data[:offending_offset]
    bottom = data[ offending_offset + fuzz_width:]
    middle = struct.pack(">" + struct_lengths[fuzz_width], value)

    tmp_file = open("fuzz_tickle_tmp" + extension, "wb+")
    tmp_file.write(top + middle + bottom)
    tmp_file.close()

    assert(os.stat("fuzz_tickle_tmp" + extension).st_size != 0)
    assert(len(top + middle + bottom) == len(data))
    assert((top + middle + bottom)[offending_offset] == middle)

    do_pydbg_dance(parent_program, "fuzz_tickle_tmp" + extension)

    i       += 1
    crashes  = 0

    for bin in crash_bin.bins.itervalues():
        crashes += len(bin)

    print "\tcompleted %d of %d in this set (bins: %d, crashes: %d)\r" % (i, len(fuzz_library), len(crash_bin.bins), crashes),


###########################################################
# now fuzz through all possible fuzz values at offending offset - fuzz_width.
###

print "\n[*] fuzzing at offending offset - fuzz width"
i = 0
new_offset = offending_offset - fuzz_width

for value in fuzz_library:
    extra  = "offending-fuzz_width: 0x%x" % value
    top    = data[:new_offset]
    bottom = data[ new_offset + fuzz_width:]
    middle = struct.pack(">" + struct_lengths[fuzz_width], value)

    tmp_file = open("fuzz_tickle_tmp" + extension, "wb+")
    tmp_file.write(top + middle + bottom)
    tmp_file.close()

    assert(os.stat("fuzz_tickle_tmp" + extension).st_size != 0)
    assert(len(top + middle + bottom) == len(data))

    do_pydbg_dance("fuzz_tickle_tmp" + extension)

    i       += 1
    crashes  = 0

    for bin in crash_bin.bins.itervalues():
        crashes += len(bin)

    print "\tcompleted %d of %d in this set (bins: %d, crashes: %d)\r" % (i, len(fuzz_library), len(crash_bin.bins), crashes),


###########################################################
# now fuzz through all possible fuzz values at offending offset + fuzz_width.
###

print "\n[*] fuzzing at offending offset + fuzz width"
i = 0
new_offset = offending_offset + fuzz_width

for value in fuzz_library:
    extra  = "offending+fuzz_width: 0x%x" % value
    top    = data[:new_offset]
    bottom = data[ new_offset + fuzz_width:]
    middle = struct.pack(">" + struct_lengths[fuzz_width], value)

    tmp_file = open("fuzz_tickle_tmp" + extension, "wb+")
    tmp_file.write(top + middle + bottom)
    tmp_file.close()

    assert(os.stat("fuzz_tickle_tmp" + extension).st_size != 0)
    assert(len(top + middle + bottom) == len(data))

    do_pydbg_dance("fuzz_tickle_tmp" + extension)

    i       += 1
    crashes  = 0

    for bin in crash_bin.bins.itervalues():
        crashes += len(bin)

    print "\tcompleted %d of %d in this set (bins: %d, crashes: %d)\r" % (i, len(fuzz_library), len(crash_bin.bins), crashes),


###########################################################
# now do some random fuzzing around the offending offset.
###

print "\n[*] fuzzing with random data at offending offset +/- 8"

for i in xrange(100):
    extra  = "random: "
    top    = data[:offending_offset - 8]
    bottom = data[ offending_offset + 8:]
    middle = ""

    for o in xrange(16):
        byte    = random.randint(0, 255)
        middle += chr(byte)
        extra  += "%02x " % byte

    tmp_file = open("fuzz_tickle_tmp" + extension, "wb+")
    tmp_file.write(top + middle + bottom)
    tmp_file.close()

    assert(os.stat("fuzz_tickle_tmp" + extension).st_size != 0)
    assert(len(top + middle + bottom) == len(data))

    do_pydbg_dance(parent_program, "fuzz_tickle_tmp" + extension)

    crashes = 0

    for bin in crash_bin.bins.itervalues():
        crashes += len(bin)

    print "\tcompleted %d of %d in this set (bins: %d, crashes: %d)\r" % (i, len(fuzz_library), len(crash_bin.bins), crashes),


###########################################################
# print synopsis.
###

crashes = 0
for bin in crash_bin.bins.itervalues():
    crashes += len(bin)

print
print "[*] fuzz tickling complete."
print "[*] crash bin contains %d crashes across %d containers" % (crashes, len(crash_bin.bins))
print "[*] saving crash bin to file_fuzz_tickler.crash_bin"

crash_bin.export_file("file_fuzz_tickler.crash_bin")

# unlink the temporary file.
os.unlink("fuzz_tickle_tmp" + extension)
########NEW FILE########
__FILENAME__ = heap_trace
#!c:\python\python.exe

# $Id: heap_trace.py 231 2008-07-21 22:43:36Z pedram.amini $

# TODO - need to add race condition testing and hook de-activation testing.

from pydbg import *
from pydbg.defines import *

import pgraph
import utils

import sys
import getopt

USAGE = "USAGE: heap_trace.py <-p|--pid PID> | <-l|--load filename>"                \
        "\n    [-g|--graph]            enable graphing"                             \
        "\n    [-m|--monitor]          enabe heap integrity checking"               \
        "\n    [-h|--host udraw host]  udraw host (for graphing), def:127.0.0.1"    \
        "\n    [-o|--port udraw port]  udraw port (for graphing), def:2542"

ERROR = lambda msg: sys.stderr.write("ERROR> " + msg + "\n") or sys.exit(1)

class __alloc:
    call_stack = []
    size       = 0


def access_violation (dbg):
    crash_bin = utils.crash_binning.crash_binning()
    crash_bin.record_crash(dbg)

    print "***** process access violated *****"
    print crash_bin.crash_synopsis()
    dbg.terminate_process()


def dll_load_handler (dbg):
    global hooks

    try:
        last_dll = dbg.get_system_dll(-1)
    except:
        return

    if last_dll.name.lower() == "ntdll.dll":
        addrRtlAllocateHeap   = dbg.func_resolve_debuggee("ntdll", "RtlAllocateHeap")
        addrRtlFreeHeap       = dbg.func_resolve_debuggee("ntdll", "RtlFreeHeap")
        addrRtlReAllocateHeap = dbg.func_resolve_debuggee("ntdll", "RtlReAllocateHeap")

        hooks.add(dbg, addrRtlAllocateHeap,   3, None, RtlAllocateHeap)
        hooks.add(dbg, addrRtlFreeHeap,       3, None, RtlFreeHeap)
        hooks.add(dbg, addrRtlReAllocateHeap, 4, None, RtlReAllocateHeap)

        print "rtl heap manipulation routines successfully hooked"

    return DBG_CONTINUE


def graph_connect (dbg, buff_addr, size, realloc=False):
    global count, graph
    count += 1

    eip = dbg.context.Eip

    allocator = pgraph.node(eip)
    allocated = pgraph.node(buff_addr)

    allocator.label = "%08x" % eip
    allocated.label = "%d" % size
    allocated.size  = size

    allocator.color = 0xFFAC59

    if realloc:
        allocated.color = 0x46FF46
    else:
        allocated.color = 0x59ACFF

    graph.add_node(allocator)
    graph.add_node(allocated)

    edge = pgraph.edge(allocator.id, allocated.id)
    edge.label = "%d" % count

    graph.add_edge(edge)


def graph_update (id, focus_first=False):
    global graph, udraw

    if udraw:
        if focus_first:
            udraw.focus_node(id)

        udraw.graph_new(graph)

        if not focus_first:
            udraw.focus_node(id)


def monitor_add (dbg, address, size):
    global monitor, allocs

    if not monitor:
        return

    alloc            = __alloc()
    alloc.size       = size
    alloc.call_stack = dbg.stack_unwind()
    allocs[address]  = alloc

    dbg.bp_set_mem(address+size+1, 1, handler=monitor_bp)


def monitor_bp (dbg):
    global allocs

    print "heap bound exceeded at %08x by %08x" % (dbg.violation_address, dbg.exception_address)

    for call in dbg.stack_unwind():
        print "\t%08x" % call

    # determine which chunk was violated.
    for addr, alloc in allocs.iteritems():
        if addr + alloc.size < dbg.violation_address < addr + alloc.size + 4:
            violated_chunk = addr
            break

    print "violated chunk:"

    print "0x%08x: %d" % (violated_chunk, allocs[violated_chunk].size)

    for call in allocs[violated_chunk].call_stack:
        print "\t%08x" % call

    raw_input("")

    # XXX - add check for Rtl addresses in call stack and ignore


def monitor_print ():
    for addr, alloc in allocs.iteritems():
        print "0x%08x: %d" % (addr, alloc.size)

        for call in alloc.call_stack:
            print "\t%08x" % call


def monitor_remove (dbg, address):
    global monitor, allocs

    if not monitor:
        return

    del allocs[address]
    monitor_print()


def outstanding_bytes ():
    outstanding = 0

    for node in graph.nodes.values():
        if hasattr(node, "size"):
            outstanding += node.size

    return outstanding


def RtlAllocateHeap (dbg, args, ret):
    global graph

    # heap id, flags, size
    print "[%04d] %08x: RtlAllocateHeap(%08x, %08x, %d) == %08x" % (len(graph.nodes), dbg.context.Eip, args[0], args[1], args[2], ret)

    monitor_add(dbg, ret, args[2])

    graph_connect(dbg, ret, args[2])
    graph_update(dbg.context.Eip)


def RtlFreeHeap (dbg, args, ret):
    global graph

    # heap id, flags, address
    print "[%04d] %08x: RtlFreeHeap(%08x, %08x, %08x) == %08x" % (len(graph.nodes), dbg.context.Eip, args[0], args[1], args[2], ret)
    print "%d bytes outstanding" % outstanding_bytes()

    monitor_remove(dbg, args[2])

    for edge in graph.edges_to(args[2]):
        graph.del_edge(edge.id)

    graph.del_node(args[2])
    graph_update(args[2], True)


def RtlReAllocateHeap (dbg, args, ret):
    global graph

    # heap id, flags, address, new size
    print "[%04d] %08x: RtlReAllocateHeap(%08x, %08x, %08x, %d) == %08x" % (len(graph.nodes), dbg.context.Eip, args[0], args[1], args[2], args[3], ret)

    monitor_remove(dbg, args[2])
    monitor_add(dbg, ret, args[3])

    graph.del_node(args[2])
    graph_connect(dbg, ret, args[3], realloc=True)
    graph_update(dbg.context.Eip)


# parse command line options.
try:
    opts, args = getopt.getopt(sys.argv[1:], "gh:o:l:mp:", ["graph", "host=", "monitor", "port=", "pid="])
except getopt.GetoptError:
    ERROR(USAGE)

count    = 0
udraw    = False
host     = "127.0.0.1"
port     = 2542
filename = None
pid      = None
udraw    = None
graph    = pgraph.graph()
hooks    = utils.hook_container()
monitor  = False
allocs   = {}

for opt, arg in opts:
    if opt in ("-g", "--graph"):   udraw    = True
    if opt in ("-h", "--host"):    host     = arg
    if opt in ("-o", "--port"):    port     = int(arg)
    if opt in ("-l", "--load"):    filename = arg
    if opt in ("-p", "--pid"):     pid      = int(arg)
    if opt in ("-m", "--monitor"): monitor = True

if not pid and not filename:
    ERROR(USAGE)

if udraw:
    udraw = utils.udraw_connector(host, port)
    print "connection to udraw established..."

dbg = pydbg()

if pid:
    dbg.attach(pid)
else:
    dbg.load(filename)

dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, access_violation)
dbg.set_callback(LOAD_DLL_DEBUG_EVENT,       dll_load_handler)

dbg.run()
########NEW FILE########
__FILENAME__ = just_in_time_debugger
#!c:\\python\\python.exe

"""
PyDbg Just-In-Time Debugger
Copyright (C) 2007 Pedram Amini <pedram.amini@gmail.com>

$Id: just_in_time_debugger.py 213 2007-08-22 23:31:42Z pedram $

To install:
    Create a registry string value named "Debugger" with the following value:
    
        "c:\python\python.exe" "c:\vmfarm\shared\paimei\jit_test.py" %ld %ld

    Under the following key:
        
        HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AeDebug
"""

import sys
import utils

from pydbg         import *
from pydbg.defines import *

# globals.
pid     = int(sys.argv[1])
h_event = int(sys.argv[2])
proc    = None
log     = r"c:\pydbg_jit.txt"

# skip the OS supplied breakpoint event and set the offending event to the signaled state.
def bp_handler (dbg):
    global h_event

    windll.kernel32.SetEvent(h_event)
    return DBG_CONTINUE

# print the crashing PID, proc name, crash synopsis and module list to disk.
def av_handler (dbg):
    global pid, proc, log

    fh = open(log, "a+")
    fh.write("\n" + "-"*80 + "\n")
    fh.write("PyDbg caught access violation in PID: %d, PROC: %s\n" % (pid, proc))

    crash_bin = utils.crash_binning.crash_binning()
    crash_bin.record_crash(dbg)

    fh.write(crash_bin.crash_synopsis())

    fh.write("MODULE ENUMERATION\n")
    for name, base in dbg.enumerate_modules():
        fh.write("\t %08x: %s\n" % (base, name))

    fh.close()
    dbg.terminate_process()
    return DBG_CONTINUE

# hello pydbg.
dbg = pydbg()

# determine the process name by matching the violating PID.
for epid, eproc in dbg.enumerate_processes():
    if epid == pid:
        proc = eproc
        break

# register a breakpoint handler to skip the OS supplied breakpoint and register an AV handler to catch the exception.
dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, av_handler)
dbg.set_callback(EXCEPTION_BREAKPOINT,       bp_handler)
dbg.attach(pid)
dbg.run()

########NEW FILE########
__FILENAME__ = mem_diff
import os
import sys
import difflib
import code
import struct
import shelve

import pydbg


def monitor_updates (md):
    # grab the snapshot keys and sort alphabetically (we assume this is the correct order)
    snap_keys =  md.snapshots.keys()
    snap_keys.sort()
    
    for i in xrange(len(snap_keys)):
        self.diff(snap_keys[i], snap_keys[i+1])


class memory_differ:
    def __init__ (self, pid):
        """
        instantiate an internal pydbg instance and open a handle to the target process. we are not actually attaching!
        """
        
        self.dbg       = pydbg.pydbg()
        self.snapshots = {}

        # get debug privileges and open the target process. 
        self.dbg.get_debug_privileges()
        self.dbg.open_process(int(pid))


    def byte_diff_count (self, a, b):
        """
        assumes a and b are of the same length.
        """
        
        max_len = max(len(a), len(b))
        min_len = min(len(a), len(b))
        changes = max_len - min_len

        for idx in xrange(min_len):
            if a[idx] != b[idx]:
                changes += 1

        return changes


    def diff (self, key_a, key_b):
        """
        step through each block in snapshot-b and contrast with each block in snapshot-a.
        """

        a = self.snapshots[key_a]
        b = self.snapshots[key_b]

        diffs = []

        for address_b, block_b in b.iteritems():
            if address_b not in a.keys():
                diffs.append("new block in %s @%08x:%d" % (key_b, address_b, len(block_b.data)))
            else:
                block_a = a[address_b]
                tuple_a = (key_a, block_a.mbi.BaseAddress, len(block_a.data))
                tuple_b = (key_b, block_b.mbi.BaseAddress, len(block_b.data))

                if block_a.data == block_b.data:
                    diffs.append("%s.%08x:%d == %s.%08x:%d" % (tuple_a + tuple_b))
                else:
                    diff_count = (self.byte_diff_count(block_a.data, block_b.data), )
                    diffs.append("%s.%08x:%d != %s.%08x:%d [%d]" % (tuple_a + tuple_b + diff_count))

        return diffs
        

    def del_snap (self, key):
        del(self.snapshots[key])
        return self


    def export_block (self, block, filename, format="binary"):
        if format == "ascii":
            data = self.dbg.hex_dump(block.data)
            mode = "w+"
        else:
            data = block.data
            mode = "wb+"

        fh = open(filename, mode)
        fh.write(data)
        fh.close()
        
        return self

        
    def export_snap (self, key, path, prefix="", suffix="", ext="bin", format="binary"):
        if format != "binary" and ext == "bin":
            ext = "txt"

        for address, block in self.snapshots[key].iteritems():
            self.export_block(block, "%s/%s%08x%s.%s" % (path, prefix, address, suffix, ext), format)

        return self


    def find_all_occurences (self, needle, haystack, idx=0):
        found = []
        
        while 1:
            idx = haystack.find(needle, idx)
    
            if idx == -1:
                break
            
            found.append(idx)
            idx += len(needle)
    
        return found


    def get_snap (self, key):
        return self.snapshots[key]


    def load (self, filename):
        sh = shelve.open(filename, flag='r', protocol=2)

        # snag the snapshot key and remove it from the shelve.
        key = sh["key"]

        snapshot = {}
        for address, block in sh.iteritems():
            # the one NON address/block pair is the key/name pair, so skip that one.
            if address == "key":
                continue

            snapshot[int(address, 16)] = block

        self.snapshots[key] = snapshot
        sh.close()
        return self


    def save (self, key, filename):
        # clear out existing shelve.
        if os.path.exists(filename):
            os.unlink(filename)
        
        # open a new shelve and store the key.
        sh        = shelve.open(filename, flag='n', writeback=True, protocol=2)
        sh["key"] = key

        # we store the snapshot dictionary piece by piece to avoid out of memory conditions.
        for address, block in self.snapshots[key].iteritems():
            sh["%08x" % address] = block
            sh.sync()
    
        sh.close()
        return self


    def snap (self, key):
        """
        take a memory snapshot of the target process save the resulting dictionary to the internal snapshot dictionary
        under the specified key
        """
        
        self.dbg.process_snapshot(mem_only=True)

        snapshot = {}
        for block in self.dbg.memory_snapshot_blocks:
            snapshot[block.mbi.BaseAddress] = block
        
        self.snapshots[key] = snapshot
        return self


    def search (self, key, value, length="L"):
        matches = []

        for address, block in self.snapshots[key].iteritems():
            indices = []

            if type(value) in [int, long]:
                for endian in [">", "<"]:
                    indices.extend(self.find_all_occurences(struct.pack("%c%c" % (endian, length), value), block.data))
            else:
                indices.extend(self.find_all_occurences(value, block.data))
            
            for idx in indices:
                matches.append((address + idx, self.dbg.hex_dump(block.data[idx-32:idx+32], address + idx - 32)))

        return matches


########################################################################################################################
import readline
import rlcompleter

md = memory_differ(sys.argv[1])

imported_objects = {}
readline.set_completer(rlcompleter.Completer(imported_objects).complete)
readline.parse_and_bind("tab:complete")
code.interact(banner="Memory Differ\nSee dir(md) for help", local=locals())
    
"""
print "snapped %d blocks" % len(md.get_snap("a"))
raw_input("enter to take snap-B: ")
md.snap("b")
print "snapped %d blocks" % len(md.get_snap("b"))

print "diffing..."
for diff in md.diff("a", "b"):
    print diff

print "exporting..."
md.export_snap("a", "mem_diffs", suffix="_a")
md.export_snap("b", "mem_diffs", suffix="_b")
"""

########NEW FILE########
__FILENAME__ = null_selector_mem_monitor_poc
#!c:\\python\\python.exe

"""
Null Selector Mem-Monitor Proof of Concept
Copyright (C) 2007 Pedram Amini <pedram.amini@gmail.com>

$Id: null_selector_mem_monitor_poc.py 214 2007-08-23 05:48:44Z pedram $

Description:
    Pydbg implementation of skape's null selector mem-monitor technique:

        http://www.uninformed.org/?v=7&a=1

    I forget how functional this is, or if it even really works.

TODO (performance improvements):
    - intelligently skip over REP sequences
"""

from pydbg import *
from pydbg.defines import *

def evaluate_expression (dbg):
    expression = dbg.disasm(dbg.exception_address)

    for reg in ["eax", "ebx", "ecx", "edx", "ebp", "esi", "edi"]:
        expression = expression.replace(reg, "%d" % dbg.get_register(reg))

    return eval(expression[expression.index('[')+1:expression.index(']')])

def set_selectors(dbg, val, thread_id=None):
    if thread_id:
        thread_ids = [thread_id]
    else:
        thread_ids = dbg.enumerate_threads()

    for tid in thread_ids:
        handle  = dbg.open_thread(tid)
        context = dbg.get_thread_context(handle)
        context.SegDs = val
        context.SegEs = val
        dbg.set_thread_context(context, handle)
        dbg.close_handle(handle)

def entry_point (dbg):
    print "%08x: %s" % (dbg.exception_address, dbg.disasm(dbg.exception_address))
    print "%08x" % dbg.context.SegDs
    set_selectors(dbg, 0)
    return DBG_CONTINUE

def av_handler (dbg):
    if dbg.write_violation:
        direction = "write to"
    else:
        direction = "read from"

    #print "AV: %08x via %s %08x" % (dbg.exception_address, direction, evaluate_expression(dbg))
    #print dbg.dump_context()

    set_selectors(dbg, 0x23, dbg.dbg.dwThreadId)

    if dbg.mnemonic.startswith("rep"):
        dbg.bp_set(dbg.exception_address + dbg.instruction.length, handler=nullify_selectors)
    else:
        dbg.single_step(True)

    return DBG_CONTINUE

def nullify_selectors (dbg):
    set_selectors(dbg, 0, dbg.dbg.dwThreadId)
    return DBG_CONTINUE

def thread_handler (dbg):
    set_selectors(dbg, 0, dbg.dbg.dwThreadId)
    return DBG_CONTINUE

dbg = pydbg()
dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, av_handler)
dbg.set_callback(EXCEPTION_SINGLE_STEP,      nullify_selectors)
dbg.set_callback(CREATE_THREAD_DEBUG_EVENT,  thread_handler)

dbg.load(r"c:\windows\system32\calc.exe")
dbg.bp_set(0x01012475, handler=entry_point)

dbg.run()

########NEW FILE########
__FILENAME__ = ollydbg_receiver
#!c:\python\python.exe

#
# OllyDbg Receiver
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: ollydbg_receiver.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import thread
import sys
import time
import socket
import os
import getopt

from ctypes import *
from SendKeys import SendKeys

import pida
import pgraph
import utils

USAGE = "ollydbg_receiver.py [-h | --host <udraw host>] [-p | --port <udraw port>] [-i | --ida_sync]"

PURE_PROXIMITY       = 0
PERSISTANT_PROXIMITY = 1
COLOR_VISITED        = 0x0080FF
COLOR_CURRENT        = 0xFF8000

# globals.
udraw                = None
host                 = "0.0.0.0"
port                 = 7033
udraw_host           = "127.0.0.1"
udraw_port           = 2542
modules              = {}
mode                 = PERSISTANT_PROXIMITY
hits                 = []
udraw_call_graph     = None
udraw_cfg            = None
new_graph            = True
last_bb              = 0
ida_sync             = False
ida_handle           = None

########################################################################################################################

def udraw_node_selections_labels (udraw, args):
    print "udraw_node_selections_labels", args


def udraw_node_double_click (udraw, args):
    print "udraw_node_double_click", args


WNDENUMPROC = CFUNCTYPE(c_int, c_int, c_int)
SW_SHOW     = 5

def enum_windows_proc (hwnd, lparam):
    global ida_handle

    title = create_string_buffer(1024)
    
    windll.user32.GetWindowTextA(hwnd, title, 255)
    
    if title.value.lower().count(module.lower()) and not ida_handle:
        ida_handle = hwnd

########################################################################################################################

# parse command line options.
try:
    opts, args = getopt.getopt(sys.argv[1:], "h:ip:", ["host=","ida_sync","port="])
except getopt.GetoptError:
    sys.stderr.write(USAGE + "\n\n")
    sys.exit(1)

for o, a in opts:
    if o in ("-h", "--host"):     udraw_host = a
    if o in ("-p", "--port"):     udraw_port = int(a)
    if o in ("-i", "--ida_sync"): ida_sync   = True

try:
    udraw = utils.udraw_connector(udraw_host, udraw_port)
    udraw.set_command_handler("node_double_click",      udraw_node_double_click)
    udraw.set_command_handler("node_selections_labels", udraw_node_selections_labels)

    # thread out the udraw connector message loop.
    thread.start_new_thread(udraw.message_loop, (None, None))
except socket.error, err:
    sys.stderr.write("Socket error: %s.\nIs uDraw(Graph) running on %s:%d?\n" % (err[1], udraw_host, udraw_port))
    udraw = None
    
    # nothing to do... exit.
    if not ida_sync:
        sys.exit(1)

try:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
except:
    sys.stderr.write("unable to bind to %s:%d\n" % (host, port))
    sys.exit(1)

# accept connections.
while 1:
    print "ollydbg receiver waiting for connection"

    if mode == PURE_PROXIMITY:
        print "mode: pure proximity graphing"
    else:
        print "module: persistant proximity graphing"

    (client, client_address) = server.accept()

    print "client connected."

    # connected client message handling loop.
    while 1:
        try:
            received = client.recv(128)
        except:
            print "connection severed."
            break

        try:
            (module, offset) = received.split(":")

            module = module.lower()
            offset = long(offset, 16)
        except:
            print "malformed data received: '%s'" % received
            continue

        #
        # if an IDA window containing the module is open, update the address.
        #

        if ida_sync:
            if not ida_handle:
                try:    windll.user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
                except: pass
                    
            windll.user32.SetForegroundWindow(ida_handle)
            windll.user32.ShowWindow(ida_handle, SW_SHOW)
            #SendKeys("+{F2}Jump+9MinEA+9+0{+}0x%08x+0;{TAB}" % (offset-0x1000), pause=0)
            SendKeys("+{F2}Jump+9MinEA+9+0{+}0x000279e7+0;{TAB}{ENTER}", pause=0)
            print "jumping to offset 0x%08x in %s" % ((offset-0x1000), module)


        #
        # ENSURE UDRAW IS PRESENT
        #
        
        if not udraw:
            continue

        # if we haven't already loaded the specified module, do so now.
        if not modules.has_key(module):
            for name in os.listdir("."):
                name = name.lower()

                if name.startswith(module) and name.endswith(".pida"):
                    start = time.time()
                    print "loading %s ..." % name
                    modules[module] = pida.load(name, progress_bar="ascii")
                    print "done. completed in %.02f" % (time.time() - start)

        # if the module wasn't found, ignore the command.
        if not modules.has_key(module):
            continue

        module  = modules[module]
        ea      = module.base + offset

        # determine which function the address lies in.
        function = module.find_function(ea)

        if not function:
            print "unrecognized address: %08x" % ea
            continue

        # determine which basic block the address lies in.
        bb = module.functions[function.ea_start].find_basic_block(ea)

        if not bb:
            print "unrecognized address: %08x" % ea
            continue

        # if the hit basic block has not already been recorded, do so now.
        if not hits.count(bb.ea_start):
            hits.append(bb.ea_start)

        #
        # CALL GRAPH VIEW
        #

        if function.ea_start == ea:
            # generate new call graph.
            if not udraw_call_graph or mode == PURE_PROXIMITY:
                udraw_call_graph = module.graph_proximity(function.ea_start, 1, 1)

            # add new node and node proximity to current call graph.
            else:
                proximity = module.graph_proximity(function.ea_start, 1, 1)
                proximity.graph_sub(udraw_call_graph)
                udraw_call_graph.graph_cat(proximity)

            current_graph = udraw_call_graph
            new_graph     = True

        #
        # CONTROL FLOW GRAPH VIEW
        #

        else:
            # generate new cfg.
            if not udraw_cfg or not udraw_cfg.find_node("id", bb.ea_start):
                udraw_cfg = module.functions[function.ea_start]
                new_graph = True

            current_graph = udraw_cfg

        # if we in the same graph and in the same basic block, then no graph update is required.
        if not new_graph and bb.ea_start == last_bb:
            continue

        # save the current basic block address as the last bb to be hit.
        last_bb = bb.ea_start

        # color all the previously hit nodes appropriately.
        for ea in current_graph.nodes.keys():
            if hits.count(ea):
                current_graph.nodes[ea].color = COLOR_VISITED

        # color the current node.
        current_graph.nodes[bb.ea_start].color = COLOR_CURRENT

        try:
            print "ea: %08x, bb: %08x, func: %08x" % (ea, bb.ea_start, function.ea_start)

            # XXX - graph updates are not working correctly, so we generate a new graph every time.

            new_graph = False
            udraw.graph_new(current_graph)

            #if new_graph:
            #    udraw.graph_new(current_graph)
            #    new_graph = False
            #else:
            #    udraw.graph_update(current_graph)

            udraw.window_title(function.name)
            udraw.change_element_color("node", bb.ea_start, COLOR_CURRENT)
            udraw.focus_node(bb.ea_start, animated=True)
        except:
            print "connection severed."
            break
########NEW FILE########
__FILENAME__ = cluster
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: cluster.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import node

class cluster (object):
    '''
    '''

    id    = None
    nodes = []

    ####################################################################################################################
    def __init__ (self, id=None):
        '''
        Class constructor.
        '''

        self.id    = id
        self.nodes = []


   ####################################################################################################################
    def add_node (self, node):
        '''
        Add a node to the cluster.

        @type  node: pGRAPH Node
        @param node: Node to add to cluster
        '''

        self.nodes.append(node)

        return self


    ####################################################################################################################
    def del_node (self, node_id):
        '''
        Remove a node from the cluster.

        @type  node_id: pGRAPH Node
        @param node_id: Node to remove from cluster
        '''

        for node in self.nodes:
            if node.id == node_id:
                self.nodes.remove(node)
                break

        return self


    ####################################################################################################################
    def find_node (self, attribute, value):
        '''
        Find and return the node with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Node, if attribute / value pair is matched. None otherwise.
        '''

        for node in self.nodes:
            if hasattr(node, attribute):
                if getattr(node, attribute) == value:
                    return node

        return None


    ####################################################################################################################
    def render (self):
        pass
########NEW FILE########
__FILENAME__ = edge
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: edge.py 230 2007-12-21 18:27:53Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

class edge (object):
    '''
    '''

    id    = None
    src   = None
    dst   = None

    # general graph attributes.
    color = 0x000000
    label = ""

    # gml relevant attributes.
    gml_arrow       = "none"
    gml_stipple     = 1
    gml_line_width  = 1.0

    ####################################################################################################################
    def __init__ (self, src, dst, label=""):
        '''
        Class constructor.

        @type  src: Mixed
        @param src: Edge source
        @type  dst: Mixed
        @param dst: Edge destination
        '''

        # the unique id for any edge (provided that duplicates are not allowed) is the combination of the source and
        # the destination stored as a long long.
        self.id  = (src << 32) + dst
        self.src = src
        self.dst = dst

        # general graph attributes.
        self.color = 0x000000
        self.label = label

        # gml relevant attributes.
        self.gml_arrow       = "none"
        self.gml_stipple     = 1
        self.gml_line_width  = 1.0


    ####################################################################################################################
    def render_edge_gml (self, graph):
        '''
        Render an edge description suitable for use in a GML file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current edge

        @rtype:  String
        @return: GML edge description
        '''

        src = graph.find_node("id", self.src)
        dst = graph.find_node("id", self.dst)

        # ensure nodes exist at the source and destination of this edge.
        if not src or not dst:
            return ""

        edge  = '  edge [\n'
        edge += '    source %d\n'          % src.number
        edge += '    target %d\n'          % dst.number
        edge += '    generalization 0\n'
        edge += '    graphics [\n'
        edge += '      type "line"\n'
        edge += '      arrow "%s"\n'       % self.gml_arrow
        edge += '      stipple %d\n'       % self.gml_stipple
        edge += '      lineWidth %f\n'     % self.gml_line_width
        edge += '      fill "#%06x"\n'     % self.color
        edge += '    ]\n'
        edge += '  ]\n'

        return edge


    ####################################################################################################################
    def render_edge_graphviz (self, graph):
        '''
        Render an edge suitable for use in a Pydot graph using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current edge

        @rtype:  pydot.Edge()
        @return: Pydot object representing edge
        '''

        import pydot

        # no need to validate if nodes exist for src/dst. graphviz takes care of that for us transparently.

        dot_edge = pydot.Edge(self.src, self.dst)

        if self.label:
            dot_edge.label = self.label

        dot_edge.color = "#%06x" % self.color

        return dot_edge


    ####################################################################################################################
    def render_edge_udraw (self, graph):
        '''
        Render an edge description suitable for use in a GML file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current edge

        @rtype:  String
        @return: GML edge description
        '''

        src = graph.find_node("id", self.src)
        dst = graph.find_node("id", self.dst)

        # ensure nodes exist at the source and destination of this edge.
        if not src or not dst:
            return ""

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        udraw  = 'l("%08x->%08x",'                  % (self.src, self.dst)
        udraw +=   'e("",'                          # open edge
        udraw +=     '['                            # open attributes
        udraw +=       'a("EDGECOLOR","#%06x"),'    % self.color
        udraw +=       'a("OBJECT","%s")'           % self.label
        udraw +=     '],'                           # close attributes
        udraw +=     'r("%08x")'                    % self.dst
        udraw +=   ')'                              # close edge
        udraw += ')'                                # close element

        return udraw


    ####################################################################################################################
    def render_edge_udraw_update (self):
        '''
        Render an edge update description suitable for use in a GML file using the set internal attributes.

        @rtype:  String
        @return: GML edge update description
        '''

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        udraw  = 'new_edge("%08x->%08x","",'      % (self.src, self.dst)
        udraw +=   '['
        udraw +=     'a("EDGECOLOR","#%06x"),'    % self.color
        udraw +=       'a("OBJECT","%s")'         % self.label
        udraw +=   '],'
        udraw +=   '"%08x","%08x"'                % (self.src, self.dst)
        udraw += ')'

        return udraw
########NEW FILE########
__FILENAME__ = graph
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: graph.py 231 2008-07-21 22:43:36Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

from node    import node
from edge    import edge
from cluster import cluster

import copy

class graph (object):
    '''
    Abstract graph class. Graphs can be added and subtracted from one another. Iteration steps through nodes.

    @todo: Add support for clusters
    @todo: Potentially swap node list with a node dictionary for increased performance
    '''

    id       = None
    clusters = None
    edges    = None
    nodes    = None


    ####################################################################################################################
    def __init__ (self, _id=None):
        if _id != None:
            self.id = _id
        else:
            self.id = id(self)

        self.nodes    = {}
        self.edges    = {}
        self.clusters = []
        self.history  = []


    ####################################################################################################################
    '''
    Function aliases.
    
    Note we don't implement these like so:
    
        self.add_graph = self.graph_cat
        self.del_graph = self.graph_sub

    Because it will break the pickle process.
    '''

    def add_graph (self, other_graph):
        return self.graph_cat(other_graph)


    def del_graph (self, other_graph):
        return self.graph_sub(other_graph)


    ####################################################################################################################
    def __add__ (self, other_graph):
        new_graph = copy.copy(self)
        new_graph.add_graph(other_graph)

        return new_graph


    ####################################################################################################################
    def __sub__ (self, other_graph):
        new_graph = copy.copy(self)
        new_graph.del_graph(other_graph)

        return new_graph


    ####################################################################################################################
    def add_cluster (self, cluster):
        '''
        Add a pgraph cluster to the graph.

        @type  cluster: pGRAPH Cluster
        @param cluster: Cluster to add to graph
        '''

        self.clusters.append(cluster)

        return self


    ####################################################################################################################
    def add_edge (self, edge, prevent_dups=True):
        '''
        Add a pgraph edge to the graph. Ensures a node exists for both the source and destination of the edge.

        @type  edge:         pGRAPH Edge
        @param edge:         Edge to add to graph
        @type  prevent_dups: Boolean
        @param prevent_dups: (Optional, Def=True) Flag controlling whether or not the addition of duplicate edges is ok
        '''

        if prevent_dups:
            if self.edges.has_key(edge.id):
                return self

        # ensure the source and destination nodes exist.
        if self.find_node("id", edge.src) and self.find_node("id", edge.dst):
            self.edges[edge.id] = edge

        return self


    ####################################################################################################################
    def add_node (self, node):
        '''
        Add a pgraph node to the graph. Ensures a node with the same id does not already exist in the graph.

        @type  node: pGRAPH Node (or list of nodes)
        @param node: Node (or list of nodes) to add to graph
        '''

        # this logic allows you to pass a list of nodes in.
        if type(node) is list:
            for x in node:
                self.add_node(x)

            return

        node.number = len(self.nodes)

        if not self.nodes.has_key(node.id):
            self.nodes[node.id] = node

            if len(self.history) == 2:
                self.history.pop(0)

            self.history.append(node)

        return self


    ####################################################################################################################
    def create_edge (self, label=""):
        '''
        Convenience routine for creating an edge between the last two added nodes.
        '''

        if not len(self.history) == 2:
            return

        e = edge(self.history[0].id, self.history[1].id, label)
        self.add_edge(e)

        return e


    ####################################################################################################################
    def create_node (self, _id=None, label=""):
        '''
        Convenience routine for quickly creating and adding a node in one step.
        '''

        n = node(_id, label)
        self.add_node(n)

        return n


    ####################################################################################################################
    def del_cluster (self, id):
        '''
        Remove a cluster from the graph.

        @type  id: Mixed
        @param id: Identifier of cluster to remove from graph
        '''

        for cluster in self.clusters:
            if cluster.id == id:
                self.clusters.remove(cluster)
                break

        return self


    ####################################################################################################################
    def del_edge (self, id=None, src=None, dst=None):
        '''
        Remove an edge from the graph. There are two ways to call this routine, with an edge id::

            graph.del_edge(id)

        or by specifying the edge source and destination::

            graph.del_edge(src=source, dst=destination)

        @type  id:  Mixed
        @param id:  (Optional) Identifier of edge to remove from graph
        @type  src: Mixed
        @param src: (Optional) Source of edge to remove from graph
        @type  dst: Mixed
        @param dst: (Optional) Destination of edge to remove from graph
        '''

        if not id:
            id = (src << 32) + dst

        if self.edges.has_key(id):
            del self.edges[id]

        return self


    ####################################################################################################################
    def del_node (self, node_id):
        '''
        Remove a node from the graph.

        @type  node_id: Mixed
        @param node_id: Identifier of node to remove from graph
        '''

        if self.nodes.has_key(node_id):
            del self.nodes[node_id]

        return self


    ####################################################################################################################
    def edges_from (self, id):
        '''
        Enumerate the edges from the specified node.

        @type  id: Mixed
        @param id: Identifier of node to enumerate edges from

        @rtype:  List
        @return: List of edges from the specified node
        '''

        return [edge for edge in self.edges.values() if edge.src == id]


    ####################################################################################################################
    def edges_to (self, id):
        '''
        Enumerate the edges to the specified node.

        @type  id: Mixed
        @param id: Identifier of node to enumerate edges to

        @rtype:  List
        @return: List of edges to the specified node
        '''

        return [edge for edge in self.edges.values() if edge.dst == id]


    ####################################################################################################################
    def find_cluster (self, attribute, value):
        '''
        Find and return the cluster with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Cluster, if attribute / value pair is matched. None otherwise.
        '''

        for cluster in self.clusters:
            if hasattr(cluster, attribute):
                if getattr(cluster, attribute) == value:
                    return cluster

        return None


    ####################################################################################################################
    def find_cluster_by_node (self, attribute, value):
        '''
        Find and return the cluster that contains the node with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Cluster, if node with attribute / value pair is matched. None otherwise.
        '''

        for cluster in self.clusters:
            for node in cluster:
                if hasattr(node, attribute):
                    if getattr(node, attribute) == value:
                        return cluster

        return None


    ####################################################################################################################
    def find_edge (self, attribute, value):
        '''
        Find and return the edge with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Edge, if attribute / value pair is matched. None otherwise.
        '''

        # if the attribute to search for is the id, simply return the edge from the internal hash.
        if attribute == "id" and self.edges.has_key(value):
            return self.edges[value]

        # step through all the edges looking for the given attribute/value pair.
        else:
            for edges in self.edges.values():
                if hasattr(edge, attribute):
                    if getattr(edge, attribute) == value:
                        return edge

        return None


    ####################################################################################################################
    def find_node (self, attribute, value):
        '''
        Find and return the node with the specified attribute / value pair.

        @type  attribute: String
        @param attribute: Attribute name we are looking for
        @type  value:     Mixed
        @param value:     Value of attribute we are looking for

        @rtype:  Mixed
        @return: Node, if attribute / value pair is matched. None otherwise.
        '''

        # if the attribute to search for is the id, simply return the node from the internal hash.
        if attribute == "id" and self.nodes.has_key(value):
            return self.nodes[value]

        # step through all the nodes looking for the given attribute/value pair.
        else:
            for node in self.nodes.values():
                if hasattr(node, attribute):
                    if getattr(node, attribute) == value:
                        return node

        return None


    ####################################################################################################################
    def graph_cat (self, other_graph):
        '''
        Concatenate the other graph into the current one.

        @todo:  Add support for clusters
        @alias: add_graph()

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to concatenate into this one.
        '''

        for other_node in other_graph.nodes.values():
            self.add_node(other_node)

        for other_edge in other_graph.edges.values():
            self.add_edge(other_edge)

        return self


    ####################################################################################################################
    def graph_down (self, from_node_id, max_depth=-1):
        '''
        Create a new graph, looking down, from the specified node id to the specified depth.

        @type  from_node_id: pgraph.node
        @param from_node_id: Node to use as start of down graph
        @type  max_depth:    Integer
        @param max_depth:    (Optional, Def=-1) Number of levels to include in down graph (-1 for infinite)

        @rtype:  pgraph.graph
        @return: Down graph around specified node.
        '''

        down_graph = graph()

        from_node  = self.find_node("id", from_node_id)

        if not from_node:
            print "unable to resolve node %08x" % from_node_id
            raise Exception

        levels_to_process = []
        current_depth     = 1

        levels_to_process.append([from_node])

        for level in levels_to_process:
            next_level = []

            if current_depth > max_depth and max_depth != -1:
                break

            for node in level:
                down_graph.add_node(copy.copy(node))

                for edge in self.edges_from(node.id):

                    to_add = self.find_node("id", edge.dst)

                    if not down_graph.find_node("id", edge.dst):
                        next_level.append(to_add)

                    down_graph.add_node(copy.copy(to_add))
                    down_graph.add_edge(copy.copy(edge))

            if next_level:
                levels_to_process.append(next_level)

            current_depth += 1

        return down_graph


    ####################################################################################################################
    def graph_intersect (self, other_graph):
        '''
        Remove all elements from the current graph that do not exist in the other graph.

        @todo: Add support for clusters

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to intersect with
        '''

        for node in self.nodes.values():
            if not other_graph.find_node("id", node.id):
                self.del_node(node.id)

        for edge in self.edges.values():
            if not other_graph.find_edge("id", edge.id):
                self.del_edge(edge.id)

        return self


    ####################################################################################################################
    def graph_proximity (self, center_node_id, max_depth_up=2, max_depth_down=2):
        '''
        Create a proximity graph centered around the specified node.

        @type  center_node_id: pgraph.node
        @param center_node_id: Node to use as center of proximity graph
        @type  max_depth_up:   Integer
        @param max_depth_up:   (Optional, Def=2) Number of upward levels to include in proximity graph
        @type  max_depth_down: Integer
        @param max_depth_down: (Optional, Def=2) Number of downward levels to include in proximity graph

        @rtype:  pgraph.graph
        @return: Proximity graph around specified node.
        '''

        prox_graph = self.graph_down(center_node_id, max_depth_down)
        prox_graph.add_graph(self.graph_up(center_node_id, max_depth_up))

        return prox_graph


    ####################################################################################################################
    def graph_sub (self, other_graph):
        '''
        Remove the elements shared between the current graph and other graph from the current
        graph.

        @todo:  Add support for clusters
        @alias: del_graph()

        @type  other_graph: pgraph.graph
        @param other_graph: Graph to diff/remove against
        '''

        for other_node in other_graph.nodes.values():
            self.del_node(other_node.id)

        for other_edge in other_graph.edges.values():
            self.del_edge(None, other_edge.src, other_edge.dst)

        return self


    ####################################################################################################################
    def graph_up (self, from_node_id, max_depth=-1):
        '''
        Create a new graph, looking up, from the specified node id to the specified depth.

        @type  from_node_id: pgraph.node
        @param from_node_id: Node to use as start of up graph
        @type  max_depth:    Integer
        @param max_depth:    (Optional, Def=-1) Number of levels to include in up graph (-1 for infinite)

        @rtype:  pgraph.graph
        @return: Up graph to the specified node.
        '''

        up_graph  = graph()
        from_node = self.find_node("id", from_node_id)

        levels_to_process = []
        current_depth     = 1

        levels_to_process.append([from_node])

        if not self.nodes:
            print "Error: nodes == null"

        for level in levels_to_process:
            next_level = []

            if current_depth > max_depth and max_depth != -1:
                break

            for node in level:
                up_graph.add_node(copy.copy(node))

                for edge in self.edges_to(node.id):
                    to_add = self.find_node("id", edge.src)

                    if not up_graph.find_node("id", edge.src):
                        next_level.append(to_add)

                    up_graph.add_node(copy.copy(to_add))
                    up_graph.add_edge(copy.copy(edge))

            if next_level:
                levels_to_process.append(next_level)

            current_depth += 1

        return up_graph


    ####################################################################################################################
    def render_graph_gml (self):
        '''
        Render the GML graph description.

        @rtype:  String
        @return: GML graph description.
        '''

        gml  = 'Creator "pGRAPH - Pedram Amini <pedram.amini@gmail.com>"\n'
        gml += 'directed 1\n'

        # open the graph tag.
        gml += 'graph [\n'

        # add the nodes to the GML definition.
        for node in self.nodes.values():
            gml += node.render_node_gml(self)

        # add the edges to the GML definition.
        for edge in self.edges.values():
            gml += edge.render_edge_gml(self)

        # close the graph tag.
        gml += ']\n'

        """
        XXX - TODO: Complete cluster rendering
        # if clusters exist.
        if len(self.clusters):
            # open the rootcluster tag.
            gml += 'rootcluster [\n'

            # add the clusters to the GML definition.
            for cluster in self.clusters:
                gml += cluster.render()

            # add the clusterless nodes to the GML definition.
            for node in self.nodes:
                if not self.find_cluster_by_node("id", node.id):
                    gml += '    vertex "%d"\n' % node.id

            # close the rootcluster tag.
            gml += ']\n'
        """

        return gml


    ####################################################################################################################
    def render_graph_graphviz (self):
        '''
        Render the graphviz graph structure.

        @rtype:  pydot.Dot
        @return: Pydot object representing entire graph
        '''

        import pydot

        dot_graph = pydot.Dot()

        for node in self.nodes.values():
            dot_graph.add_node(node.render_node_graphviz(self))

        for edge in self.edges.values():
            dot_graph.add_edge(edge.render_edge_graphviz(self))

        return dot_graph


    ####################################################################################################################
    def render_graph_udraw (self):
        '''
        Render the uDraw graph description.

        @rtype:  String
        @return: uDraw graph description.
        '''

        udraw = '['

        # render each of the nodes in the graph.
        # the individual nodes will handle their own edge rendering.
        for node in self.nodes.values():
            udraw += node.render_node_udraw(self)
            udraw += ','

        # trim the extraneous comment and close the graph.
        udraw = udraw[0:-1] + ']'

        return udraw


    ####################################################################################################################
    def render_graph_udraw_update (self):
        '''
        Render the uDraw graph update description.

        @rtype:  String
        @return: uDraw graph description.
        '''

        udraw = '['

        for node in self.nodes.values():
            udraw += node.render_node_udraw_update()
            udraw += ','

        for edge in self.edges.values():
            udraw += edge.render_edge_udraw_update()
            udraw += ','

        # trim the extraneous comment and close the graph.
        udraw = udraw[0:-1] + ']'

        return udraw


    ####################################################################################################################
    def update_node_id (self, current_id, new_id):
        '''
        Simply updating the id attribute of a node will sever the edges to / from the given node. This routine will
        correctly update the edges as well.

        @type  current_id: Long
        @param current_id: Current ID of node whose ID we want to update
        @type  new_id:     Long
        @param new_id:     New ID to update to.
        '''

        if not self.nodes.has_key(current_id):
            return

        # update the node.
        node = self.nodes[current_id]
        del self.nodes[current_id]
        node.id = new_id
        self.nodes[node.id] = node

        # update the edges.
        for edge in [edge for edge in self.edges.values() if current_id in (edge.src, edge.dst)]:
            del self.edges[edge.id]

            if edge.src == current_id:
                edge.src = new_id
            if edge.dst == current_id:
                edge.dst = new_id

            edge.id = (edge.src << 32) + edge.dst

            self.edges[edge.id] = edge


    ####################################################################################################################
    def sorted_nodes (self):
        '''
        Return a list of the nodes within the graph, sorted by id.

        @rtype:  List
        @return: List of nodes, sorted by id.
        '''

        node_keys = self.nodes.keys()
        node_keys.sort()

        return [self.nodes[key] for key in node_keys]

########NEW FILE########
__FILENAME__ = node
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: node.py 231 2008-07-21 22:43:36Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

class node (object):
    '''
    '''

    id     = 0
    number = 0

    # general graph attributes
    color        = 0xEEF7FF
    border_color = 0xEEEEEE
    label        = ""
    shape        = "box"

    # gml relevant attributes.
    gml_width       = 0.0
    gml_height      = 0.0
    gml_pattern     = "1"
    gml_stipple     = 1
    gml_line_width  = 1.0
    gml_type        = "rectangle"
    gml_width_shape = 1.0

    # udraw relevant attributes.
    udraw_image     = None
    udraw_info      = ""

    ####################################################################################################################
    def __init__ (self, _id=None, label=""):
        '''
        '''

        if _id != None:
            self.id = _id
        else:
            self.id = id(self)

        self.number = 0

        # general graph attributes
        self.color        = 0xEEF7FF
        self.border_color = 0xEEEEEE
        self.label        = label
        self.shape        = "box"

        # gml relevant attributes.
        self.gml_width       = 0.0
        self.gml_height      = 0.0
        self.gml_pattern     = "1"
        self.gml_stipple     = 1
        self.gml_line_width  = 1.0
        self.gml_type        = "rectangle"
        self.gml_width_shape = 1.0


    ####################################################################################################################
    def render_node_gml (self, graph):
        '''
        Render a node description suitable for use in a GML file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: GML node description.
        '''

        # GDE does not like lines longer then approx 250 bytes. within their their own GML files you won't find lines
        # longer then approx 210 bytes. wo we are forced to break long lines into chunks.
        chunked_label = ""
        cursor        = 0

        while cursor < len(self.label):
            amount = 200

            # if the end of the current chunk contains a backslash or double-quote, back off some.
            if cursor + amount < len(self.label):
                while self.label[cursor+amount] == '\\' or self.label[cursor+amount] == '"':
                    amount -= 1

            chunked_label += self.label[cursor:cursor+amount] + "\\\n"
            cursor        += amount

        # if node width and height were not explicitly specified, make a best effort guess to create something nice.
        if not self.gml_width:
            self.gml_width = len(self.label) * 10

        if not self.gml_height:
            self.gml_height = len(self.label.split()) * 20

        # construct the node definition.
        node  = '  node [\n'
        node += '    id %d\n'                       % self.number
        node += '    template "oreas:std:rect"\n'
        node += '    label "'
        node += '<!--%08x-->\\\n'                   % self.id
        node += chunked_label + '"\n'
        node += '    graphics [\n'
        node += '      w %f\n'                      % self.gml_width
        node += '      h %f\n'                      % self.gml_height
        node += '      fill "#%06x"\n'              % self.color
        node += '      line "#%06x"\n'              % self.border_color
        node += '      pattern "%s"\n'              % self.gml_pattern
        node += '      stipple %d\n'                % self.gml_stipple
        node += '      lineWidth %f\n'              % self.gml_line_width
        node += '      type "%s"\n'                 % self.gml_type
        node += '      width %f\n'                  % self.gml_width_shape
        node += '    ]\n'
        node += '  ]\n'

        return node


    ####################################################################################################################
    def render_node_graphviz (self, graph):
        '''
        Render a node suitable for use in a Pydot graph using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  pydot.Node
        @return: Pydot object representing node
        '''

        import pydot

        dot_node = pydot.Node(self.id)

        dot_node.label     = '<<font face="lucida console">%s</font>>' % self.label.rstrip("\r\n")
        dot_node.label     = dot_node.label.replace("\\n", '<br/>')
        dot_node.shape     = self.shape
        dot_node.color     = "#%06x" % self.color
        dot_node.fillcolor = "#%06x" % self.color

        return dot_node


    ####################################################################################################################
    def render_node_udraw (self, graph):
        '''
        Render a node description suitable for use in a uDraw file using the set internal attributes.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: uDraw node description.
        '''

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        # if an image was specified for this node, update the shape and include the image tag.
        if self.udraw_image:
            self.shape  = "image"
            udraw_image = 'a("IMAGE","%s"),' % self.udraw_image
        else:
            udraw_image = ""

        udraw  = 'l("%08x",'                            % self.id
        udraw +=   'n("",'                              # open node
        udraw +=     '['                                # open attributes
        udraw +=       udraw_image
        udraw +=       'a("_GO","%s"),'                 % self.shape
        udraw +=       'a("COLOR","#%06x"),'            % self.color
        udraw +=       'a("OBJECT","%s"),'              % self.label
        udraw +=       'a("FONTFAMILY","courier"),'
        udraw +=       'a("INFO","%s"),'                % self.udraw_info
        udraw +=       'a("BORDER","none")'
        udraw +=     '],'                               # close attributes
        udraw +=     '['                                # open edges

        edges = graph.edges_from(self.id)

        for edge in edges:
            udraw += edge.render_edge_udraw(graph)
            udraw += ','

        if edges:
            udraw = udraw[0:-1]

        udraw += ']))'

        return udraw


    ####################################################################################################################
    def render_node_udraw_update (self):
        '''
        Render a node update description suitable for use in a uDraw file using the set internal attributes.

        @rtype:  String
        @return: uDraw node update description.
        '''

        # translate newlines for uDraw.
        self.label = self.label.replace("\n", "\\n")

        # if an image was specified for this node, update the shape and include the image tag.
        if self.udraw_image:
            self.shape  = "image"
            udraw_image = 'a("IMAGE","%s"),' % self.udraw_image
        else:
            udraw_image = ""

        udraw  = 'new_node("%08x","",'                % self.id
        udraw +=   '['
        udraw +=     udraw_image
        udraw +=     'a("_GO","%s"),'                 % self.shape
        udraw +=     'a("COLOR","#%06x"),'            % self.color
        udraw +=     'a("OBJECT","%s"),'              % self.label
        udraw +=     'a("FONTFAMILY","courier"),'
        udraw +=     'a("INFO","%s"),'                % self.udraw_info
        udraw +=     'a("BORDER","none")'
        udraw +=   ']'
        udraw += ')'

        return udraw
########NEW FILE########
__FILENAME__ = basic_block
#
# PIDA Basic Block
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: basic_block.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

try:
    from idaapi   import *
    from idautils import *
    from idc      import *
except:
    pass

import pgraph

from instruction import *
from defines     import *

class basic_block (pgraph.node):
    '''
    '''

    id               = None
    ea_start         = None
    ea_end           = None
    depth            = None
    analysis         = None
    function         = None
    instructions     = {}
    num_instructions = 0
    ext              = {}

    ####################################################################################################################
    def __init__ (self, ea_start, ea_end, depth=DEPTH_FULL, analysis=ANALYSIS_NONE, function=None):
        '''
        Analyze the basic block from ea_start to ea_end.

        @see: defines.py

        @type  ea_start: DWORD
        @param ea_start: Effective address of start of basic block (inclusive)
        @type  ea_end:   DWORD
        @param ea_end:   Effective address of end of basic block (inclusive)
        @type  depth:    Integer
        @param depth:    (Optional, Def=DEPTH_FULL) How deep to analyze the module
        @type  analysis: Integer
        @param analysis: (Optional, Def=ANALYSIS_NONE) Which extra analysis options to enable
        @type  function: pida.function
        @param function: (Optional, Def=None) Pointer to parent function container
        '''

        # run the parent classes initialization routine first.
        super(basic_block, self).__init__(ea_start)

        heads = [head for head in Heads(ea_start, ea_end + 1) if isCode(GetFlags(head))]

        self.id               = ea_start
        self.ea_start         = ea_start
        self.ea_end           = ea_end
        self.depth            = depth
        self.analysis         = analysis
        self.function         = function
        self.num_instructions = len(heads)
        self.instructions     = {}
        self.ext              = {}

        # convenience alias.
        self.nodes = self.instructions

        # bubble up the instruction count to the function. this is in a try except block to catch situations where the
        # analysis was not bubbled down from a function.
        try:
            self.function.num_instructions += self.num_instructions
        except:
            pass

        if self.depth & DEPTH_INSTRUCTIONS:
            for ea in heads:
                self.instructions[ea] = instr = instruction(ea, self.analysis, self)


    ####################################################################################################################
    def overwrites_register (self, register):
        '''
        Indicates if the given register is modified by this block.

        @type  register: String
        @param register: The text representation of the register

        @rtype:  Boolean
        @return: True if the register is modified by any instruction in this block.
        '''

        for ins in self.instructions.values():
            if ins.overwrites_register(register):
                return True

        return False


    ####################################################################################################################
    def ordered_instructions(self):
        '''
        TODO: deprecated by sorted_instructions().
        '''

        temp = [key for key in self.instructions.keys()]
        temp.sort()
        return [self.instructions[key] for key in temp]


    ####################################################################################################################
    def render_node_gml (self, graph):
        '''
        Overload the default node.render_node_gml() routine to create a custom label. Pass control to the default
        node renderer and then return the merged content.

        @rtype:  String
        @return: Contents of rendered node.
        '''

        self.label  = "<span style='font-family: Courier New; font-size: 10pt; color: #000000'>"
        self.label += "<p><font color=#004080><b>%08x</b></font></p>" % self.ea_start

        self.gml_height = 45

        for instruction in self.sorted_instructions():
            colored_instruction = instruction.disasm.split()

            if colored_instruction[0] == "call":
                colored_instruction[0] = "<font color=#FF8040>" + colored_instruction[0] + "</font>"
            else:
                colored_instruction[0] = "<font color=#004080>" + colored_instruction[0] + "</font>"

            colored_instruction = " ".join(colored_instruction)

            self.label += "<font color=#999999>%08x</font>&nbsp;&nbsp;%s<br>" % (instruction.ea, colored_instruction)

            try:    instruction_length = len(instruction.disasm)
            except: instruction_length = 0

            try:    comment_length = len(instruction.comment)
            except: comment_length = 0

            required_width = (instruction_length + comment_length + 10) * 10

            if required_width > self.gml_width:
                self.gml_width = required_width

            self.gml_height += 20

        self.label += "</span>"

        return super(basic_block, self).render_node_gml(graph)


    ####################################################################################################################
    def render_node_graphviz (self, graph):
        '''
        Overload the default node.render_node_graphviz() routine to create a custom label. Pass control to the default
        node renderer and then return the merged content.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  pydot.Node()
        @return: Pydot object representing node
        '''

        self.label = ""
        self.shape = "box"

        for instruction in self.sorted_instructions():
            self.label += "%08x  %s\\n" % (instruction.ea, instruction.disasm)

        return super(basic_block, self).render_node_graphviz(graph)


    ####################################################################################################################
    def render_node_udraw (self, graph):
        '''
        Overload the default node.render_node_udraw() routine to create a custom label. Pass control to the default
        node renderer and then return the merged content.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: Contents of rendered node.
        '''

        self.label = ""

        for instruction in self.sorted_instructions():
            self.label += "%08x  %s\\n" % (instruction.ea, instruction.disasm)

        return super(basic_block, self).render_node_udraw(graph)


    ####################################################################################################################
    def render_node_udraw_update (self):
        '''
        Overload the default node.render_node_udraw_update() routine to create a custom label. Pass control to the
        default node renderer and then return the merged content.

        @rtype:  String
        @return: Contents of rendered node.
        '''

        self.label = ""

        for instruction in self.sorted_instructions():
            self.label += "%08x  %s\\n" % (instruction.ea, instruction.disasm)

        return super(basic_block, self).render_node_udraw_update()


    ####################################################################################################################
    def sorted_instructions (self):
        '''
        Return a list of the instructions within the graph, sorted by id.

        @rtype:  List
        @return: List of instructions, sorted by id.
        '''

        instruction_keys = self.instructions.keys()
        instruction_keys.sort()

        return [self.instructions[key] for key in instruction_keys]
########NEW FILE########
__FILENAME__ = defines
#
# pGRAPH
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: defines.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

PIDA_VERSION       = 0x1337

DEPTH_FUNCTIONS    = 0x0001
DEPTH_BASIC_BLOCKS = 0x0002
DEPTH_INSTRUCTIONS = 0x0004
DEPTH_FULL         = DEPTH_FUNCTIONS | DEPTH_BASIC_BLOCKS | DEPTH_INSTRUCTIONS

ANALYSIS_NONE      = 0x0000
ANALYSIS_IMPORTS   = 0x0001
ANALYSIS_RPC       = 0x0002
ANALYSIS_FULL      = ANALYSIS_IMPORTS | ANALYSIS_RPC

prime_numbers = \
[
    2,       3,    5,    7,   11,   13,   17,   19,   23,   29,   31,   37,   41,   43,   47,   53,   59,   61,
    67,     71,   73,   79,   83,   89,   97,  101,  103,  107,  109,  113,  127,  131,  137,  139,  149,  151,
    157,   163,  167,  173,  179,  181,  191,  193,  197,  199,  211,  223,  227,  229,  233,  239,  241,  251,
    257,   263,  269,  271,  277,  281,  283,  293,  307,  311,  313,  317,  331,  337,  347,  349,  353,  359,
    367,   373,  379,  383,  389,  397,  401,  409,  419,  421,  431,  433,  439,  443,  449,  457,  461,  463,
    467,   479,  487,  491,  499,  503,  509,  521,  523,  541,  547,  557,  563,  569,  571,  577,  587,  593,
    599,   601,  607,  613,  617,  619,  631,  641,  643,  647,  653,  659,  661,  673,  677,  683,  691,  701,
    709,   719,  727,  733,  739,  743,  751,  757,  761,  769,  773,  787,  797,  809,  811,  821,  823,  827,
    829,   839,  853,  857,  859,  863,  877,  881,  883,  887,  907,  911,  919,  929,  937,  941,  947,  953,
    967,   971,  977,  983,  991,  997, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063, 1069,
    1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163, 1171, 1181, 1187, 1193, 1201, 1213,
    1217, 1223, 1229, 1231, 1237, 1249, 1259, 1277, 1279, 1283, 1289, 1291, 1297, 1301, 1303, 1307, 1319, 1321,
    1327, 1361, 1367, 1373, 1381, 1399, 1409, 1423, 1427, 1429, 1433, 1439, 1447, 1451, 1453, 1459, 1471, 1481,
    1483, 1487, 1489, 1493, 1499, 1511, 1523, 1531, 1543, 1549, 1553, 1559, 1567, 1571, 1579, 1583, 1597, 1601,
    1607, 1609, 1613, 1619
]
########NEW FILE########
__FILENAME__ = function
#
# PIDA Function
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: function.py 251 2011-01-01 14:43:47Z my.name.is.sober $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

try:
    from idaapi   import *
    from idautils import *
    from idc      import *
except:
    pass

import pgraph

from basic_block import *
from defines     import *

class function (pgraph.graph, pgraph.node):
    '''
    '''

    # GHETTO - we want to store the actual function to function edge start address.
    outbound_eas     = {}

    depth            = None
    analysis         = None
    module           = None
    num_instructions = 0

    id               = None
    ea_start         = None
    ea_end           = None
    name             = None
    is_import        = False
    flags            = None

    rpc_uuid         = None
    rpc_opcode       = None

    saved_reg_size   = 0
    frame_size       = 0
    ret_size         = 0

    local_vars       = {}
    local_var_size   = 0
    num_local_vars   = 0

    args             = {}
    arg_size         = 0
    num_args         = 0
    chunks           = []

    ext              = {}

    ####################################################################################################################
    def __init__ (self, ea_start, depth=DEPTH_FULL, analysis=ANALYSIS_NONE, module=None):
        '''
        Analyze all the function chunks associated with the function starting at ea_start.
        self.fill(ea_start).

        @see: defines.py

        @type  ea_start: DWORD
        @param ea_start: Effective address of start of function (inclusive)
        @type  depth:    Integer
        @param depth:    (Optional, Def=DEPTH_FULL) How deep to analyze the module
        @type  analysis: Integer
        @param analysis: (Optional, Def=ANALYSIS_NONE) Which extra analysis options to enable
        @type  module:   pida.module
        @param module:   (Optional, Def=None) Pointer to parent module container
        '''

        # GHETTO - we want to store the actual function to function edge start address.
        self.outbound_eas     = {}

        self.depth            = depth
        self.analysis         = analysis
        self.module           = module
        self.id               = None
        self.ea_start         = None
        self.ea_end           = None
        self.name             = None
        self.is_import        = False
        self.flags            = None
        self.rpc_uuid         = None
        self.rpc_opcode       = None
        self.saved_reg_size   = 0
        self.frame_size       = 0
        self.ret_size         = 0
        self.local_vars       = {}
        self.local_var_size   = 0
        self.num_local_vars   = 0
        self.args             = {}
        self.arg_size         = 0
        self.num_args         = 0
        self.chunks           = []
        self.ext              = {}
        self.num_instructions = 0

        # convenience alias.
        self.basic_blocks = self.nodes

        # grab the ida function and frame structures.
        func_struct  = get_func(ea_start)
        frame_struct = get_frame(func_struct)

        # grab the function flags.
        self.flags = GetFunctionFlags(ea_start)

        # if we're not in a "real" function. set the id and ea_start manually and stop analyzing.
        if not func_struct or self.flags & FUNC_LIB or self.flags & FUNC_STATIC:
            pgraph.graph.__init__(self, ea_start)
            pgraph.node.__init__ (self, ea_start)

            self.id         = ea_start
            self.ea_start   = ea_start
            self.ea_end     = ea_start
            self.name       = get_name(ea_start, ea_start)
            self.is_import  = True

            return

        # run the parent classes initialization routine first.
        pgraph.graph.__init__(self, func_struct.startEA)
        pgraph.node.__init__ (self, func_struct.startEA)

        self.id             = func_struct.startEA
        self.ea_start       = func_struct.startEA
        self.ea_end         = PrevAddr(func_struct.endEA)
        self.name           = GetFunctionName(self.ea_start)
        self.saved_reg_size = func_struct.frregs
        self.frame_size     = get_frame_size(func_struct)
        self.ret_size       = get_frame_retsize(func_struct)
        self.local_var_size = func_struct.frsize
        self.chunks         = [(self.ea_start, self.ea_end)]

        self.__init_args_and_local_vars__()

        if self.depth & DEPTH_BASIC_BLOCKS:
            self.__init_basic_blocks__()


    ####################################################################################################################
    def __init_args_and_local_vars__ (self):
        '''
        Calculate the total size of arguments, # of arguments and # of local variables. Update the internal class member
        variables appropriately.
        '''

        # grab the ida function and frame structures.
        func_struct  = get_func(self.ea_start)
        frame_struct = get_frame(func_struct)

        if not frame_struct:
            return

        argument_boundary = self.local_var_size + self.saved_reg_size + self.ret_size
        frame_offset      = 0

        for i in xrange(0, frame_struct.memqty):
            end_offset = frame_struct.get_member(i).soff

            if i == frame_struct.memqty - 1:
                begin_offset = frame_struct.get_member(i).eoff
            else:
                begin_offset = frame_struct.get_member(i+1).soff

            frame_offset += (begin_offset - end_offset)

            # grab the name of the current local variable or argument.
            name = get_member_name(frame_struct.get_member(i).id)

            if name == None:
                continue

            if frame_offset > argument_boundary:
                self.args[end_offset] = name
            else:
                # if the name starts with a space, then ignore it as it is either the stack saved ebp or eip.
                # XXX - this is a pretty ghetto check.
                if not name.startswith(" "):
                    self.local_vars[end_offset] = name

        self.arg_size       = frame_offset - argument_boundary
        self.num_args       = len(self.args)
        self.num_local_vars = len(self.local_vars)


    ####################################################################################################################
    def __init_basic_blocks__ (self):
        '''
        Enumerate the basic block boundaries for the current function and store them in a graph structure.
        
        '''
        import copy
        self.chunks = self.__init_collect_function_chunks__()
        contained_heads = sum([[ea for ea in Heads(chunk_start, chunk_end)] for (chunk_start, chunk_end) in self.chunks],list())
        blocks = []        
        edges = []
        
        for (chunk_start, chunk_end) in self.chunks:

            curr_start = chunk_start
            # enumerate the nodes.
            for ea in Heads(chunk_start, chunk_end):
                # ignore data heads.
                if not isCode(GetFlags(ea)):
                    curr_start = NextNotTail(ea)
                    continue

                next_ea       = NextNotTail(ea)
                branches_to_next = self._branches_to(next_ea)       
                branches_from = self._branches_from(ea)
                is_retn = idaapi.is_ret_insn(ea)
                
                if is_retn or not isCode(GetFlags(next_ea)):
                    blocks.append((curr_start,ea))
                    curr_start = next_ea  #this will be handled if still not code
                    
        
                elif len(branches_from) > 0:
                    blocks.append((curr_start,ea))
                    curr_start = next_ea
                    
                    for branch in branches_from:
                        if branch not in contained_heads:
                            continue
                        if len(branches_from) == 1:  color = 0x0000FF
                        elif branch == next_ea:      color = 0xFF0000
                        else:                        color = 0x00FF00
                        edges.append((curr_start, branch, color))
                 
                elif len(branches_to_next)> 0:
                    blocks.append((curr_start,ea))
                    curr_start = next_ea
                    # draw an "implicit" branch.
                    edges.append((ea, next_ea, 0x0000FF))
                    
        basicBlocks = [basic_block(bs,be,self.depth, self.analysis, self)\
                        for (bs,be) in blocks]
        map(self.add_node,basicBlocks)
        
        for (src, dst, color) in edges:
            edge = pgraph.edge(src, dst)
            edge.color = color
            self.add_edge(edge)


    ####################################################################################################################
    def __init_collect_function_chunks__ (self):
        '''
        Generate and return the list of function chunks (including the main one) for the current function. Ripped from
        idb2reml (Ero Carerra).

        @rtype:  List
        @return: List of function chunks (start, end tuples) for the current function.
        '''

        chunks   = []
        iterator = func_tail_iterator_t(get_func(self.ea_start))
        status   = iterator.main()

        while status:
            chunk = iterator.chunk()
            chunks.append((chunk.startEA, chunk.endEA))
            status = iterator.next()

        return chunks


    ####################################################################################################################
    def _branches_from (self, ea):
        '''
        Enumerate and return the list of branches from the supplied address, *including* the next logical instruction.
        Part of the reason why we even need this function is that the "flow" argument to CodeRefsFrom does not appear
        to be functional.

        @type  ea: DWORD
        @param ea: Effective address of instruction to enumerate jumps from.

        @rtype:  List
        @return: List of branches from the specified address.
        '''

        if is_call_insn(ea):
            return []

        xrefs = list(CodeRefsFrom(ea, 1))

        # if the only xref from ea is next ea, then return nothing.
        if len(xrefs) == 1 and xrefs[0] == NextNotTail(ea):
            xrefs = []

        return xrefs


    ####################################################################################################################
    def _branches_to (self, ea):
        '''
        Enumerate and return the list of branches to the supplied address, *excluding* the previous logical instruction.
        Part of the reason why we even need this function is that the "flow" argument to CodeRefsTo does not appear to
        be functional.

        @type  ea: DWORD
        @param ea: Effective address of instruction to enumerate jumps to.

        @rtype:  List
        @return: List of branches to the specified address.
        '''

        xrefs        = []
        prev_ea      = PrevNotTail(ea)
        prev_code_ea = prev_ea

        while not isCode(GetFlags(prev_code_ea)):
            prev_code_ea = PrevNotTail(prev_code_ea)

        for xref in list(CodeRefsTo(ea, 1)):
            if not is_call_insn(xref) and xref not in [prev_ea, prev_code_ea]:
                xrefs.append(xref)

        return xrefs


    ####################################################################################################################
    def find_basic_block (self, ea):
        '''
        Locate and return the basic block that contains the specified address.

        @type  ea: DWORD
        @param ea: An address within the basic block to find

        @rtype:  pida.basic_block
        @return: The basic block that contains the given address or None if not found.
        '''

        for bb in self.nodes.values():
            if bb.ea_start <= ea <= bb.ea_end:
                return bb

        return None


    ####################################################################################################################
    def render_node_gml (self, graph):
        '''
        Overload the default node.render_node_gml() routine to create a custom label. Pass control to the default
        node renderer and then return the merged content.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: Contents of rendered node.
        '''

        self.label  = "<span style='font-family: Courier New; font-size: 10pt; color: #000000'>"
        self.label += "<p><font color=#004080><b>%08x %s</b></font></p>" % (self.ea_start, self.name)

        self.gml_height = 100
        self.gml_width  = (len(self.name) + 10) * 10

        if not self.is_import:
            self.label += "<b>size</b>: <font color=#FF8040>%d</font><br>" % (self.ea_end - self.ea_start)
            self.label += "<b>arguments</b>:<br>"

            for key, arg in self.args.items():
                self.label += "&nbsp;&nbsp;&nbsp;&nbsp;[%02x]%s<br>" % (key, arg)

                required_width = (len(arg) + 10) * 10

                if required_width > self.gml_width:
                    self.gml_width = required_width

                self.gml_height += 20

            self.label += "<b>local variables</b>:<br>"

            for key, var in self.local_vars.items():
                self.label += "&nbsp;&nbsp;&nbsp;&nbsp;[%02x] %s<br>" % (key, var)

                required_width = (len(var) + 10) * 10

                if required_width > self.gml_width:
                    self.gml_width = required_width

                self.gml_height += 20

        self.label += "</span>"

        return super(function, self).render_node_gml(graph)


    ####################################################################################################################
    def render_node_graphviz (self, graph):
        '''
        Overload the default node.render_node_graphviz() routine to create a custom label. Pass control to the default
        node renderer and then return the merged content.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  pydot.Node()
        @return: Pydot object representing node
        '''

        self.shape = "ellipse"

        if self.is_import:
            self.label = "%s" % (self.name)
        else:
            self.label  = "%08x %s\\n" % (self.ea_start, self.name)
            self.label += "size: %d"   % (self.ea_end - self.ea_start)

        return super(function, self).render_node_graphviz(graph)


    ####################################################################################################################
    def render_node_udraw (self, graph):
        '''
        Overload the default node.render_node_udraw() routine to create a custom label. Pass control to the default
        node renderer and then return the merged content.

        @type  graph: pgraph.graph
        @param graph: Top level graph object containing the current node

        @rtype:  String
        @return: Contents of rendered node.
        '''

        if self.is_import:
            self.label = "%s" % (self.name)
        else:
            self.label  = "%08x %s\\n" % (self.ea_start, self.name)
            self.label += "size: %d"   % (self.ea_end - self.ea_start)

        return super(function, self).render_node_udraw(graph)


    ####################################################################################################################
    def render_node_udraw_update (self):
        '''
        Overload the default node.render_node_udraw_update() routine to create a custom label. Pass control to the
        default node renderer and then return the merged content.

        @rtype:  String
        @return: Contents of rendered node.
        '''

        if self.is_import:
            self.label = "%s" % (self.name)
        else:
            self.label  = "%08x %s\\n" % (self.ea_start, self.name)
            self.label += "size: %d"   % (self.ea_end - self.ea_start)

        return super(function, self).render_node_udraw_update()
########NEW FILE########
__FILENAME__ = instruction
#
# PIDA Instruction
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: instruction.py 257 2011-07-20 14:38:59Z chanleeyee@gmail.com $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

try:
    import idautils
    from idaapi   import *
    from idautils import *
    from idc      import *
except:
    pass

from defines import *

class instruction:
    '''
    '''

    ea             = None                          # effective address of instruction
    analysis       = None                          # analysis options
    basic_block    = None                          # pointer to parent container
    disasm         = None                          # sanitized disassembly at instruction
    comment        = ""                            # comment at instruction EA

    bytes          = []                            # instruction raw bytes, mnemonic and operands
    mnem           = None
    op1            = None
    op2            = None
    op3            = None

    refs_string    = None                          # string, if any, that this instruction references
    refs_api       = None                          # known API, if any, that this instruction references
    refs_arg       = None                          # argument, if any, that this instruction references
    refs_constant  = None                          # constant value, if any, that this instruction references
    refs_var       = None                          # local variable, if any, that this instruction references

    ext            = {}

    ####################################################################################################################
    def __init__ (self, ea, analysis=0, basic_block=None):
        '''
        Analyze the instruction at ea.

        @see: defines.py

        @type  ea:          DWORD
        @param ea:          Effective address of instruction to analyze
        @type  analysis:    Integer
        @param analysis:    (Optional, Def=ANALYSIS_NONE) Which extra analysis options to enable
        @type  basic_block: pgraph.basic_block
        @param basic_block: (Optional, Def=None) Pointer to parent basic block container
        '''

        self.ea          = ea                            # effective address of instruction
        self.analysis    = analysis                      # analysis options
        self.basic_block = basic_block                   # pointer to parent container
        self.disasm      = self.get_disasm(ea)           # sanitized disassembly at instruction
        self.comment     = Comment(ea)
        self.ext         = {}

        # raw instruction bytes.
        self.bytes = []

        # instruction mnemonic and operands.
        self.mnem = GetMnem(ea)
        self.op1  = GetOpnd(ea, 0)
        self.op2  = GetOpnd(ea, 1)
        self.op3  = GetOpnd(ea, 2)

        for address in xrange(ea, ItemEnd(ea)):
            self.bytes.append(Byte(address))

        # XXX - this is a dirty hack to determine if and any API reference.
        xref  = Dfirst(self.ea)
        flags = GetFunctionFlags(xref)

        if xref == BADADDR:
            xref  = get_first_cref_from(ea)
            flags = GetFunctionFlags(xref)

        if SegName(xref) == ".idata":
            name = get_name(xref, xref)

            if name and get_name_ea(BADADDR, name) != BADADDR:
                self.refs_api = (get_name_ea(BADADDR, name), name)

        self.refs_string   = None
        self.refs_arg      = self._get_arg_ref()
        self.refs_constant = self._get_constant_ref()
        self.refs_var      = self._get_var_ref()


    ####################################################################################################################
    def _get_arg_ref (self):
        '''
        Return the stack offset of the argument referenced, if any, by the instruction.

        @author: Peter Silberman

        @rtype:  Mixed
        @return: Referenced argument stack offset or None.
        '''

        func = get_func(self.ea)

        if not func:
            return None

        # determine if either of the operands references a stack offset.
        op_num = 0
        offset = calc_stkvar_struc_offset(func, self.ea, 0)

        if offset == BADADDR:
            op_num = 1
            offset = calc_stkvar_struc_offset(func, self.ea, 1)

            if offset == BADADDR:
                return None

        # for some reason calc_stkvar_struc_offset detects constant values as an index into the stack struct frame. we
        # implement this check to ignore this false positive.
        # XXX - may want to look into why this is the case later.
        if self._get_constant_ref(op_num):
            return None

        if self.basic_block.function.args.has_key(offset):
            return self.basic_block.function.args[offset]

        return None


    ####################################################################################################################
    def _get_constant_ref (self, opnum=0):
        '''
        Return the constant value, if any, reference by the instruction.

        @author: Peter Silberman

        @rtype:  Mixed
        @return: Integer value of referenced constant, otherwise None.
        '''

        if idaapi.IDA_SDK_VERSION >=600:
            instruction = idaapi.cmd.ea
        else:
            instruction = idaapi.get_current_instruction()

        if not instruction:
            return None

        if opnum:
            if idaapi.IDA_SDK_VERSION >=600:
                op0 = idautils.DecodeInstruction(instruction)[opnum]
            else:
                op0 = idaapi.get_instruction_operand(instruction, opnum)

            if op0.value and op0.type == o_imm and GetStringType(self.ea) == None:
                return op0.value

        else:
            if idaapi.IDA_SDK_VERSION >=600:
                op0 = idautils.DecodeInstruction(instruction)[0]
            else:
                op0 = idaapi.get_instruction_operand(instruction, 0)

            if op0.value and op0.type == o_imm and GetStringType(self.ea) == None:
                return op0.value

            if idaapi.IDA_SDK_VERSION >=600:
                op1 = idautils.DecodeInstruction(instruction)[1]
            else:
                op1 = idaapi.get_instruction_operand(instruction, 1)

            if op1.value and op1.type == o_imm and GetStringType(self.ea) == None:
                return op1.value

        return None


    ####################################################################################################################
    def _get_var_ref (self):
        '''
        Return the stack offset of the local variable referenced, if any, by the instruction.

        @author: Peter Silberman

        @rtype:  Mixed
        @return: Referenced local variable stack offset or None.
        '''

        func = get_func(self.ea)

        if not func:
            return None

        # determine if either of the operands references a stack offset.
        op_num = 0
        offset = calc_stkvar_struc_offset(func, self.ea, 0)

        if offset == BADADDR:
            op_num = 1
            offset = calc_stkvar_struc_offset(func, self.ea, 1)

            if offset == BADADDR:
                return None

        if self.basic_block.function.local_vars.has_key(offset):
            return self.basic_block.function.local_vars[offset]

        return None


    ####################################################################################################################
    def flag_dependency (first_instruction, second_instruction):
        '''
        Determine if one instruction can affect flags used by the other instruction.

        @author: Cameron Hotchkies

        @type   first_instruction:  instruction
        @param  first_instruction:  The first instruction to check
        @type   second_instruction: instruction
        @param  second_instruction: The second instruction to check

        @rtype: Integer
        @return: 0 for no effect, 1 for first affects second, 2 for second affects first, 3 for both can affect
        '''

        if first_instruction.mnem in instruction.FLAGGED_OPCODES and second_instruction.mnem in instruction.FLAGGED_OPCODES:
            ret_val = 0

            # if neither opcodes set any flags, they can be ignored
            if instruction.FLAGGED_OPCODES[first_instruction.mnem]  & instruction.__SET_MASK > 0 and \
               instruction.FLAGGED_OPCODES[second_instruction.mnem] & instruction.__SET_MASK > 0:
                return 0

            setter = instruction.FLAGGED_OPCODES[first_instruction.mnem]  & instruction.__SET_MASK
            tester = instruction.FLAGGED_OPCODES[second_instruction.mnem] & instruction.__TEST_MASK

            if setter & (tester << 16) > 0:
                ret_val += 1

            setter = instruction.FLAGGED_OPCODES[second_instruction.mnem] & instruction.__SET_MASK
            tester = instruction.FLAGGED_OPCODES[first_instruction.mnem]  & instruction.__TEST_MASK

            if setter & (tester << 16) > 0:
                ret_val += 2

            return ret_val

        return 0


    ####################################################################################################################
    def get_disasm (self, ea):
        '''
        A GetDisasm() wrapper that strips comments and extraneous whitespace.

        @type  ea: DWORD
        @param ea: Effective address of instruction to analyze

        @rtype:  String
        @return: Sanitized disassembly at ea.
        '''

        disasm = GetDisasm(ea)

        # if the disassembled line contains a comment. then strip it and the trailing whitespace.
        if disasm.count(";"):
            disasm = disasm[0:disasm.index(";")].rstrip(" ")

        # shrink whitespace.
        while disasm.count("  "):
            disasm = disasm.replace("  ", " ")

        return disasm


    ####################################################################################################################
    def get_string_reference (self, ea):
        '''
        If the specified instruction references a string, get and return the contents of that string.
        Currently supports:

        @todo: XXX - Add more supported string types.

        @type  ea: DWORD
        @param ea: Effective address of instruction to analyze

        @rtype:  Mixed
        @return: ASCII representation of string referenced from ea if found, None otherwise.
        '''

        dref = Dfirst(ea)
        s    = ""

        if dref == BADADDR:
            return None

        string_type = GetStringType(dref)

        if string_type == ASCSTR_C:
            while True:
                byte = Byte(dref)

                if byte == 0 or byte < 32 or byte > 126:
                    break

                s    += chr(byte)
                dref += 1

        return s


    ####################################################################################################################
    def is_conditional_branch (self):
        '''
        Check if the instruction is a conditional branch. (x86 specific)

        @author: Cameron Hotchkies

        @rtype:  Boolean
        @return: True if the instruction is a conditional branch, False otherwise.
        '''

        if len(self.mnem) and self.mnem[0] == 'j' and self.mnem != "jmp":
            return True

        return False


    ####################################################################################################################
    def overwrites_register (self, register):
        '''
        Indicates if the given register is modified by this instruction. This does not check for all modifications,
        just lea, mov and pop into the specific register.

        @author: Cameron Hotchkies

        @type   register: String
        @param  register: The text representation of the register

        @rtype: Boolean
        @return: True if the register is modified
        '''

        if self.mnem == "mov" or self.mnem == "pop" or self.mnem == "lea":
            if self.op1 == register:
                return True

        if self.mnem == "xor" and self.op1 == self.op2 and self.op1 == register:
            return True

        if register == "eax" and self.mnem == "call":
            return True

        return False


    ####################################################################################################################
    ### constants for flag-using instructions (ripped from bastard)
    ###

    __TEST_CARRY  =   0x0001
    __TEST_ZERO   =   0x0002
    __TEST_OFLOW  =   0x0004
    __TEST_DIR    =   0x0008
    __TEST_SIGN   =   0x0010
    __TEST_PARITY =   0x0020
    __TEST_NCARRY =   0x0100
    __TEST_NZERO  =   0x0200
    __TEST_NOFLOW =   0x0400
    __TEST_NDIR   =   0x0800
    __TEST_NSIGN  =   0x1000
    __TEST_NPARITY=   0x2000
    __TEST_SFEQOF =   0x4000
    __TEST_SFNEOF =   0x8000
    __TEST_ALL    =   __TEST_CARRY | __TEST_ZERO |  __TEST_OFLOW | __TEST_SIGN |  __TEST_PARITY

    __SET_CARRY   =   0x00010000
    __SET_ZERO    =   0x00020000
    __SET_OFLOW   =   0x00040000
    __SET_DIR     =   0x00080000
    __SET_SIGN    =   0x00100000
    __SET_PARITY  =   0x00200000
    __SET_NCARRY  =   0x01000000
    __SET_NZERO   =   0x02000000
    __SET_NOFLOW  =   0x04000000
    __SET_NDIR    =   0x08000000
    __SET_NSIGN   =   0x10000000
    __SET_NPARITY =   0x20000000
    __SET_SFEQOF  =   0x40000000
    __SET_SFNEOF  =   0x80000000
    __SET_ALL     =   __SET_CARRY | __SET_ZERO |  __SET_OFLOW | __SET_SIGN |  __SET_PARITY

    __TEST_MASK   =   0x0000FFFF
    __SET_MASK    =   0xFFFF0000


    ####################################################################################################################
    ### flag-using instructions in a dictionary (ripped from bastard)
    ###

    FLAGGED_OPCODES = \
    {
        "add"      : __SET_ALL,
        "or"       : __SET_ALL,
        "adc"      : __TEST_CARRY | __SET_ALL,
        "sbb"      : __TEST_CARRY | __SET_ALL,
        "and"      : __SET_ALL,
        "daa"      : __TEST_CARRY | __SET_CARRY | __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "sub"      : __SET_ALL,
        "das"      : __TEST_CARRY | __SET_CARRY | __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "xor"      : __SET_ALL,
        "aaa"      : __SET_CARRY,
        "cmp"      : __SET_ALL,
        "aas"      : __SET_CARRY,
        "inc"      : __SET_ZERO | __SET_OFLOW | __SET_SIGN | __SET_PARITY,
        "dec"      : __SET_ZERO | __SET_OFLOW | __SET_SIGN | __SET_PARITY,
        "arpl"     : __SET_ZERO,
        "imul"     : __SET_CARRY | __SET_OFLOW,
        "jo"       : __TEST_OFLOW,
        "jno"      : __TEST_NOFLOW,
        "jbe"      : __TEST_CARRY | __TEST_ZERO,
        "ja"       : __TEST_NCARRY | __TEST_NZERO,
        "js"       : __TEST_SIGN,
        "jns"      : __TEST_NSIGN,
        "jl"       : __TEST_SFNEOF,
        "jge"      : __TEST_SFEQOF,
        "jle"      : __TEST_ZERO | __TEST_SFNEOF,
        "jg"       : __TEST_NZERO | __TEST_SFEQOF,
        "test"     : __SET_ALL,
        "sahf"     : __SET_CARRY | __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "into"     : __TEST_OFLOW,
        "iret"     : __SET_ALL,
        "aam"      : __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "aad"      : __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "cmc"      : __SET_CARRY,
        "clc"      : __SET_NCARRY,
        "stc"      : __SET_CARRY,
        "cld"      : __SET_NDIR,
        "std"      : __SET_DIR,
        "lsl"      : __SET_ZERO,
        "ucomiss"  : __SET_ALL,
        "comiss"   : __SET_ALL,
        "cmovo"    : __TEST_OFLOW,
        "cmovno"   : __TEST_NOFLOW,
        "cmovbe"   : __TEST_CARRY | __TEST_ZERO,
        "cmova"    : __TEST_NCARRY | __TEST_NZERO,
        "cmovs"    : __TEST_SIGN,
        "cmovns"   : __TEST_NSIGN,
        "cmovl"    : __TEST_OFLOW | __TEST_SIGN,
        "cmovge"   : __TEST_OFLOW | __TEST_SIGN,
        "cmovle"   : __TEST_ZERO | __TEST_OFLOW | __TEST_SIGN,
        "cmovg"    : __TEST_OFLOW | __TEST_SIGN | __TEST_NZERO,
        "seto"     : __TEST_OFLOW,
        "setno"    : __TEST_OFLOW,
        "setbe"    : __TEST_CARRY | __TEST_ZERO,
        "seta"     : __TEST_CARRY | __TEST_ZERO,
        "sets"     : __TEST_SIGN,
        "setns"    : __TEST_SIGN,
        "setl"     : __TEST_OFLOW | __TEST_SIGN,
        "setge"    : __TEST_OFLOW | __TEST_SIGN,
        "setle"    : __TEST_ZERO | __TEST_OFLOW | __TEST_SIGN,
        "setg"     : __TEST_ZERO | __TEST_OFLOW | __TEST_SIGN,
        "bt"       : __SET_CARRY,
        "shld"     : __SET_CARRY | __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "rsm"      : __SET_ALL,
        "bts"      : __SET_CARRY,
        "shrd"     : __SET_CARRY | __SET_ZERO | __SET_SIGN | __SET_PARITY,
        "cmpxchg"  : __SET_ALL,
        "btr"      : __SET_CARRY,
        "btc"      : __SET_CARRY,
        "bsf"      : __SET_ZERO,
        "bsr"      : __SET_ZERO,
        "xadd"     : __SET_ALL,
        "verr"     : __SET_ZERO,
        "verw"     : __SET_ZERO,
        "rol"      : __SET_CARRY | __SET_OFLOW,
        "ror"      : __SET_CARRY | __SET_OFLOW,
        "rcl"      : __TEST_CARRY | __SET_CARRY | __SET_OFLOW,
        "rcr"      : __TEST_CARRY | __SET_CARRY | __SET_OFLOW,
        "shl"      : __SET_ALL,
        "shr"      : __SET_ALL,
        "sal"      : __SET_ALL,
        "sar"      : __SET_ALL,
        "neg"      : __SET_ALL,
        "mul"      : __SET_CARRY | __SET_OFLOW,
        "fcom"     : __SET_CARRY | __SET_ZERO | __SET_PARITY,
        "fcomp"    : __SET_CARRY | __SET_ZERO | __SET_PARITY,
        "fcomp"    : __TEST_CARRY | __SET_CARRY | __SET_PARITY,
        "fcmovb"   : __TEST_CARRY,
        "fcmove"   : __TEST_ZERO,
        "fcmovbe"  : __TEST_CARRY | __TEST_ZERO,
        "fcmovu"   : __TEST_PARITY,
        "fcmovnb"  : __TEST_NCARRY,
        "fcmovne"  : __TEST_NZERO,
        "fcmovnbe" : __TEST_NCARRY | __TEST_NZERO,
        "fcmovnu"  : __TEST_NPARITY,
        "fcomi"    : __SET_CARRY | __SET_ZERO | __SET_PARITY,
        "fcomip"   : __SET_CARRY | __SET_ZERO | __SET_PARITY
    }

########NEW FILE########
__FILENAME__ = module
#
# PIDA Module
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: module.py 235 2009-10-17 16:18:11Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

try:
    from idaapi   import *
    from idautils import *
    from idc      import *
except:
    pass

import sys
import pgraph

from function import *
from defines  import *

class module (pgraph.graph):
    '''
    '''

    name      = None
    base      = None
    depth     = None
    analysis  = None
    signature = None
    ext       = {}

    ####################################################################################################################
    def __init__ (self, name="", signature=None, depth=DEPTH_FULL, analysis=ANALYSIS_NONE):
        '''
        Analysis of an IDA database requires the instantiation of this class and will handle, depending on the requested
        depth, the analysis of all functions, basic blocks, instructions and more specifically which analysis techniques
        to apply. For the full list of ananylsis options see defines.py. Specifying ANALYSIS_IMPORTS will require an
        extra one-time scan through the entire structure to propogate functions (nodes) and cross references (edges) for
        each reference API call. Specifying ANALYSIS_RPC will require an extra one-time scan through the entire IDA
        database and will propogate additional function level attributes.

        The signature attribute was added for use in the PaiMei process stalker module, for ensuring that a loaded
        DLL is equivalent to the PIDA file with matching name. Setting breakpoints in a non-matching module is
        obviously no good.

        @see: defines.py

        @type  name:      String
        @param name:      (Optional) Module name
        @type  signature: String
        @param signature: (Optional) Unique file signature to associate with module
        @type  depth:     Integer
        @param depth:     (Optional, Def=DEPTH_FULL) How deep to analyze the module
        @type  analysis:  Integer
        @param analysis:  (Optional, Def=ANALYSIS_NONE) Which extra analysis options to enable
        '''

        # run the parent classes initialization routine first.
        super(module, self).__init__(name)

        self.name      = name
        self.base      = MinEA() - 0x1000      # XXX - cheap hack
        self.depth     = depth
        self.analysis  = analysis
        self.signature = signature
        self.ext       = {}
        self.log       = True

        # convenience alias.
        self.functions = self.nodes

        # enumerate and add the functions within the module.
        if self.log:
            print "Analyzing functions..."

        for ea in Functions(MinEA(), MaxEA()):
            func = function(ea, self.depth, self.analysis, self)
            func.shape = "ellipse"
            self.add_node(func)

        # enumerate and add nodes for each import within the module.
        if self.depth & DEPTH_INSTRUCTIONS and self.analysis & ANALYSIS_IMPORTS:
            if self.log:
                print"Enumerating imports..."

            self.__init_enumerate_imports__()

        # enumerate and propogate attributes for any discovered RPC interfaces.
        if self.analysis & ANALYSIS_RPC:
            if self.log:
                print "Enumerating RPC interfaces..."

            self.__init_enumerate_rpc__()

        # enumerate and add the intramodular cross references.
        if self.log:
            print "Enumerating intramodular cross references..."

        for func in self.nodes.values():
            xrefs = list(CodeRefsTo(func.ea_start, 0))
            xrefs.extend(list(DataRefsTo(func.ea_start)))

            for ref in xrefs:
                from_func = get_func(ref)

                if from_func:
                    # GHETTO - add the actual source EA to the function.
                    if not self.nodes[from_func.startEA].outbound_eas.has_key(ref):
                        self.nodes[from_func.startEA].outbound_eas[ref] = []

                    self.nodes[from_func.startEA].outbound_eas[ref].append(func.ea_start)

                    edge = pgraph.edge(from_func.startEA, func.ea_start)

                    self.add_edge(edge)


    ####################################################################################################################
    def __init_enumerate_imports__ (self):
        '''
        Enumerate and add nodes / edges for each import within the module. This routine will pass through the entire
        module structure.
        '''

        for func in self.nodes.values():
            for bb in func.nodes.values():
                for instruction in bb.instructions.values():
                    if instruction.refs_api:
                        (address, api) = instruction.refs_api

                        node = function(address, module=self)
                        node.color = 0xB4B4DA
                        self.add_node(node)

                        edge = pgraph.edge(func.ea_start, address)
                        self.add_edge(edge)


    ####################################################################################################################
    def __init_enumerate_rpc__ (self):
        '''
        Enumerate all RPC interfaces and add additional properties to the RPC functions. This routine will pass through
        the entire IDA database. This was entirely ripped from my RPC enumeration IDC script::

            http://www.openrce.org/downloads/details/3/RPC%20Enumerator

        The approach appears to be stable enough.
        '''

        # walk through the entire database.
        # we don't just look at .text as .rdata also been spotted to house RPC structs.
        for loop_ea in Heads(MinEA(), MaxEA()):
            ea     = loop_ea;
            length = Byte(ea);
            magic  = Dword(ea + 0x18);

            # RPC_SERVER_INTERFACE found.
            if length == 0x44 and magic == 0x8A885D04:
                # grab the rpc interface uuid.
                uuid = ""
                for x in xrange(ea+4, ea+4+16):
                    uuid += chr(Byte(x))

                # jump to MIDL_SERVER_INFO.
                ea = Dword(ea + 0x3C);

                # jump to DispatchTable.
                ea = Dword(ea + 0x4);

                # enumerate the dispatch routines.
                opcode = 0
                while 1:
                    addr = Dword(ea)

                    if addr == BADADDR:
                        break

                    # sometimes ida doesn't correctly get the function start thanks to the whole 'mov reg, reg' noop
                    # nonsense. so try the next instruction.
                    if not len(GetFunctionName(addr)):
                        addr = NextNotTail(addr)

                    if not len(GetFunctionName(addr)):
                        break

                    if self.nodes.has_key(addr):
                        self.nodes[addr].rpc_uuid   = self.uuid_bin_to_string(uuid)
                        self.nodes[addr].rpc_opcode = opcode
                    else:
                        print "PIDA.MODULE> No function node for RPC routine @%08X" % addr

                    ea     += 4
                    opcode += 1


    ####################################################################################################################
    def find_function (self, ea):
        '''
        Locate and return the function that contains the specified address.

        @type  ea: DWORD
        @param ea: An address within the function to find

        @rtype:  pida.function
        @return: The function that contains the given address or None if not found.
        '''

        for func in self.nodes.values():
            # this check is necessary when analysis_depth == DEPTH_FUNCTIONS
            if func.ea_start == ea:
                return func

            for bb in func.nodes.values():
                if bb.ea_start <= ea <= bb.ea_end:
                    return func

        return None


    ####################################################################################################################
    def next_ea (self, ea=None):
        '''
        Return the instruction after to the one at ea. You can call this routine without an argument after the first
        call. The overall structure of PIDA was not really designed for this kind of functionality, so this is kind of
        a hack.

        @todo: See if I can do this better.

        @type  ea: (Optional, def=Last EA) Dword
        @param ea: Address of instruction to return next instruction from or -1 if not found.
        '''

        if not ea and self.current_ea:
            ea = self.current_ea

        function = self.find_function(ea)

        if not function:
            return -1

        ea_list = []

        for bb in function.nodes.values():
            ea_list.extend(bb.instructions.keys())

        ea_list.sort()

        try:
            idx = ea_list.index(ea)

            if idx == len(ea_list) - 1:
                raise Exception
        except:
            return -1

        self.current_ea = ea_list[idx + 1]
        return self.current_ea


    ####################################################################################################################
    def prev_ea (self, ea=None):
        '''
        Within the function that contains ea, return the instruction prior to the one at ea. You can call this routine
        without an argument after the first call. The overall structure of PIDA was not really designed for this kind of
        functionality, so this is kind of a hack.

        @todo: See if I can do this better.

        @type  ea: (Optional, def=Last EA) Dword
        @param ea: Address of instruction to return previous instruction to or None if not found.
        '''

        if not ea and self.current_ea:
            ea = self.current_ea

        function = self.find_function(ea)

        if not function:
            return -1

        ea_list = []

        for bb in function.nodes.values():
            ea_list.extend(bb.instructions.keys())

        ea_list.sort()

        try:
            idx = ea_list.index(ea)

            if idx == 0:
                raise Exception
        except:
            return -1

        self.current_ea = ea_list[idx - 1]
        return self.current_ea


    ####################################################################################################################
    def rebase (self, new_base):
        '''
        Rebase the module and all components with the new base address. This routine will check if the current and
        requested base addresses are equivalent, so you do not have to worry about checking that yourself.

        @type  new_base: Dword
        @param new_base: Address to rebase module to
        '''

        # nothing to do.
        if new_base == self.base:
            return

        # rebase each function in the module.
        for function in self.nodes.keys():
            self.nodes[function].id       = self.nodes[function].id       - self.base + new_base
            self.nodes[function].ea_start = self.nodes[function].ea_start - self.base + new_base
            self.nodes[function].ea_end   = self.nodes[function].ea_end   - self.base + new_base

            function = self.nodes[function]

            # rebase each basic block in the function.
            for bb in function.nodes.keys():
                function.nodes[bb].id       = function.nodes[bb].id       - self.base + new_base
                function.nodes[bb].ea_start = function.nodes[bb].ea_start - self.base + new_base
                function.nodes[bb].ea_end   = function.nodes[bb].ea_end   - self.base + new_base

                bb = function.nodes[bb]

                # rebase each instruction in the basic block.
                for ins in bb.instructions.keys():
                    bb.instructions[ins].ea = bb.instructions[ins].ea - self.base + new_base

                # fixup the instructions dictionary.
                old_dictionary  = bb.instructions
                bb.instructions = {}

                for key, val in old_dictionary.items():
                    bb.instructions[key - self.base + new_base] = val

            # fixup the functions dictionary.
            old_dictionary = function.nodes
            function.nodes = {}

            for key, val in old_dictionary.items():
                function.nodes[val.id] = val

            # rebase each edge between the basic blocks in the function.
            for edge in function.edges.keys():
                function.edges[edge].src =  function.edges[edge].src - self.base + new_base
                function.edges[edge].dst =  function.edges[edge].dst - self.base + new_base
                function.edges[edge].id  = (function.edges[edge].src << 32) + function.edges[edge].dst

            # fixup the edges dictionary.
            old_dictionary = function.edges
            function.edges = {}

            for key, val in old_dictionary.items():
                function.edges[val.id] = val

        # fixup the modules dictionary.
        old_dictionary = self.nodes
        self.nodes     = {}

        for key, val in old_dictionary.items():
            self.nodes[val.id] = val

        # rebase each edge between the functions in the module.
        for edge in self.edges.keys():
            self.edges[edge].src =  self.edges[edge].src - self.base + new_base
            self.edges[edge].dst =  self.edges[edge].dst - self.base + new_base
            self.edges[edge].id  = (self.edges[edge].src << 32) + self.edges[edge].dst

        # finally update the base address of the module.
        self.base = new_base


    ####################################################################################################################
    def uuid_bin_to_string (self, uuid):
        '''
        Convert the binary representation of a UUID to a human readable string.

        @type  uuid: Raw
        @param uuid: Raw binary bytes consisting of the UUID

        @rtype:  String
        @return: Human readable string representation of UUID.
        '''

        import struct

        (block1, block2, block3) = struct.unpack("<LHH", uuid[:8])
        (block4, block5, block6) = struct.unpack(">HHL", uuid[8:16])

        return "%08x-%04x-%04x-%04x-%04x%08x" % (block1, block2, block3, block4, block5, block6)
########NEW FILE########
__FILENAME__ = pida_dump
#
# IDA Python PIDA Database Generation Script
# Dumps the current IDB into a .PIDA file.
#
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: pida_dump.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import time
import pida

depth    = None
analysis = pida.ANALYSIS_NONE

while not depth:
    depth = AskStr("full", "Depth to analyze? (full, functions|func, basic blocks|bb)")
    
    if depth:
        depth = depth.lower()

    if   depth in ["full"]:                depth = pida.DEPTH_FULL
    elif depth in ["functions", "func"]:   depth = pida.DEPTH_FUNCTIONS
    elif depth in ["basic blocks", "bb"]:  depth = pida.DEPTH_BASIC_BLOCKS
    else:
        Warning("Unsupported depth: %s\n\nValid options include:\n\t- full\n\t- functions\n\t- basic blocks" % depth)
        depth = None

choice = AskYN(1, "Propogate nodes and edges for API calls (imports)?")

if choice == 1:
    analysis |= pida.ANALYSIS_IMPORTS

choice = AskYN(1, "Enumerate RPC interfaces and dispatch routines?")

if choice == 1:
    analysis |= pida.ANALYSIS_RPC


output_file = AskFile(1, GetInputFile() + ".pida", "Save PIDA file to?")

if not output_file:
    Warning("Cancelled.")
else:
    print "Analyzing IDB..."
    start = time.time()

    try:
        signature = pida.signature(GetInputFilePath())
    except:
        print "PIDA.DUMP> Could not calculate signature for %s, perhaps the file was moved?" % GetInputFilePath()
        signature = ""

    module = pida.module(GetInputFile(), signature, depth, analysis)
    print "Done. Completed in %f seconds.\n" % round(time.time() - start, 3)

    print "Saving to file...",
    start = time.time()
    pida.dump(output_file, module, progress_bar="ascii")
    print "Done. Completed in %f seconds." % round(time.time() - start, 3)

    # clean up memory.
    # XXX - this is not working...
    del(module)
########NEW FILE########
__FILENAME__ = pida_load
#
# IDA Python PIDA Database Loading Script
#
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: pida_load.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import time
import pida

pida_name = AskFile(0, GetInputFile() + ".pida", "Load PIDA file from?")

if not pida_name:
    Warning("Cancelled.")
else:
    start = time.time()
    print "Loading %s" % pida_name
    module = pida.load(pida_name, progress_bar="ascii")
    print "Done. Completed in %f seconds." % round(time.time() - start, 3)

########NEW FILE########
__FILENAME__ = proc_peek
#!c:\python\python.exe

#
# Proc Peek
#
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: proc_peek.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import sys
import getopt
import struct
import time
import traceback
import utils

from pydbg import *
from pydbg.defines import *

USAGE = "DEPRECATED: See PAIMEIpeek\n"                                                      \
        "\nUSAGE: proc_peek.py "                                                            \
        "\n    <-r|--recon RECON FILE> name of proc_peek_recon output file"                 \
        "\n    [-p|--pid PID]          pid to attach to (must specify this or watch)"       \
        "\n    [-w|--watch PROC]       target name to watch for and attach to"              \
        "\n    [-i|--ignore PID]       ignore a specific PID when watching for a target"    \
        "\n    [-n|--noint]            disable interactive prompts"                         \
        "\n    [-q|--quiet]            disable run-time context dumps"                      \
        "\n    [-l|--log LOG FILE]     report to file instead of screen"                    \
        "\n    [-h|--host REMOTE HOST] connect to a pydbg server"                           \
        "\n    [-b|--boron KEYWORD]    alert us when a keyword is found within the context" \
        "\n    [-t|--track_recv]       enable recv() and recvfrom() hit logging"

ERR = lambda msg: sys.stderr.write("ERR> " + msg + "\n") or sys.exit(1)

# globals.
peek_points = {}

ws2_recv = ws2_recvfrom = wsock_recv = wsock_recvfrom = None
retaddr = buffer = length = None

# peek point structure.
class peek_point:
    stack_depth = 0
    comment     = ""
    contexts    = []
    hit_count   = 0
    disabled    = 0


########################################################################################################################
### helper functions
########################################################################################################################


def boron_scan (ea, context_dump):
    """
    scans the context dump at ea for the command line specified boron tag. if found adds a comment to the peek point
    which is later output to the updated recon file. the passed in context dump should have been generated with
    prints_dots=False.
    """

    global peek_points
    global quiet, boron, noint     # command line flags.

    if not boron:
        return

    if context_dump.lower().find(boron) != -1:
        if not quiet:
            print ">>>>>>>>>>> boron tag '%s' was found ... adding comment." % boron

        boron_comment = " // " + "boron hit on '%s'" % boron

        # ensure comment doesn't already exist.
        if peek_points[ea].comment.find(boron_comment) == -1:
            peek_points[ea].comment += boron_comment

        if not noint:
            raw_input("enter to continue...")


def process_pp_hit (dbg):
    """
    if the hit peek point was not disabled, process it by incrementing the hit count, appending a new context dump and,
    depending on specified command line options, printing output to screen or interactively prompting the user for
    actions such as commenting or disabling the hit peek point.
    """

    global peek_points
    global quiet, noint     # command line flags.

    ea = dbg.exception_address

    if peek_points[ea].disabled > 0:
        return

    peek_points[ea].hit_count += 1

    dump = dbg.dump_context(stack_depth=peek_points[ea].stack_depth, print_dots=False)

    if not quiet:
        print
        print "hit #%d: %s" % (peek_points[ea].hit_count, peek_points[ea].comment)
        print dump

    # check for the existence of a boron tag in our current context.
    boron_scan(ea, dump)

    # check if the user wishes to start ignoring this peek point.
    hit_count = peek_points[ea].hit_count

    if not noint and peek_points[ea].disabled != -1 and hit_count in (5, 10, 20, 50, 75, 100, 150):
        print ">>>>>>>>>>> this peek point was hit %d times, disable it?" % hit_count

        try:
            key = raw_input("<y|n|v|q>[c] y=yes, n=no, v=never, c=comment> ")

            if key.lower() == "q":
                dbg.detach()
                return

            if key.lower() == "v":
                peek_points[ea].disabled = -1

            if key.lower().startswith("y"):
                peek_points[ea].disabled = hit_count

            if key.lower() in ("yc", "nc"):
                peek_points[ea].comment += " // " + raw_input("add comment> ")
        except:
            pass

    peek_points[ea].contexts.append(dump)


def track_recv_enter (dbg):
    """
    this function is called when a winsock function we wish to track is first hit. the return address, buffer size and
    buffer length are retrieved and a breakpoint is set on the return address for track_recv_exit() to handle.
    """

    # used in tracking hits to recv()/recvfrom()
    global ws2_recv, ws2_recvfrom, wsock_recv, wsock_recvfrom, retaddr, buffer, length

    ea = dbg.exception_address

    # ensure we are at the start of one of the winsock recv functions.
    if ea not in (ws2_recv, ws2_recvfrom, wsock_recv, wsock_recvfrom):
        return

    # ESP                 +4         +8       +C        +10
    # int recv     (SOCKET s, char *buf, int len, int flags)
    # int recvfrom (SOCKET s, char *buf, int len, int flags, struct sockaddr *from, int *fromlen)
    # we want these:                ^^^      ^^^

    retaddr = dbg.read_process_memory(dbg.context.Esp, 4)
    retaddr = struct.unpack("<L", retaddr)[0]

    buffer  = dbg.read_process_memory(dbg.context.Esp + 0x8, 4)
    buffer  = struct.unpack("<L", buffer)[0]

    length  = dbg.read_process_memory(dbg.context.Esp + 0xC, 4)
    length  = struct.unpack("<L", length)[0]

    if   ea == ws2_recv:       print "%08x call ws2.recv():"       % retaddr
    elif ea == ws2_recvfrom:   print "%08x call ws2.recvfrom():"   % retaddr
    elif ea == wsock_recv:     print "%08x call wsock.recv():"     % retaddr
    elif ea == wsock_recvfrom: print "%08x call wsock.recvfrom():" % retaddr

    dbg.bp_set(retaddr)


def track_recv_exit (dbg):
    """
    this function 'hooks' the return address of hit winsock routines and displays the contents of the received data.
    """

    global retaddr, buffer, length      # used in tracking hits to recv()/recvfrom()

    ea = dbg.exception_address

    if ea == retaddr:
        print "called from %08x with buf length: %d (0x%08x)" % (retaddr, length, length)
        print "actually received: %d (0x%08x)" % (dbg.context.Eax, dbg.context.Eax)

        if dbg.context.Eax != 0xFFFFFFFF:
            # grab the contents of the buffer based on the number of actual bytes read (from EAX).
            buffer = dbg.read_process_memory(buffer, dbg.context.Eax)

            print dbg.hex_dump(buffer)
            print

        dbg.bp_del(retaddr)

        retaddr = buffer = length = None


########################################################################################################################
### callback handlers.
########################################################################################################################


def handler_breakpoint (dbg):
    global peek_points

    # command line flags.
    global track_recv

    # used in tracking hits to recv()/recvfrom()
    global ws2_recv, ws2_recvfrom, wsock_recv, wsock_recvfrom

    # set all our breakpoints on the first windows driven break point.
    if dbg.first_breakpoint:
        # set breakpoints on our peek points.
        print "setting breakpoints on %d peek points" % len(peek_points.keys())
        dbg.bp_set(peek_points.keys())

        # if we want to track recv()/recvfrom(), do so.
        if track_recv:
            print "tracking calls to recv()/recvfrom() in ws2_32 and wsock32 ..."
            ws2_recv       = dbg.func_resolve("ws2_32",  "recv")
            ws2_recvfrom   = dbg.func_resolve("ws2_32",  "recvfrom")
            wsock_recv     = dbg.func_resolve("wsock32", "recv")
            wsock_recvfrom = dbg.func_resolve("wsock32", "recvfrom")

            try:    dbg.bp_set(ws2_recv)
            except: pass

            try:    dbg.bp_set(ws2_recvfrom)
            except: pass

            try:    dbg.bp_set(wsock_recv)
            except: pass

            try:    dbg.bp_set(wsock_recvfrom)
            except: pass

        return DBG_CONTINUE

    if track_recv:
        track_recv_enter(dbg)
        track_recv_exit (dbg)

    if peek_points.has_key(dbg.exception_address):
        process_pp_hit(dbg)

    return DBG_CONTINUE


def handler_access_violation (dbg):
    print "***** ACCESS VIOLATION *****"

    crash_bin = utils.crash_binning.crash_binning()
    crash_bin.record_crash(dbg)

    print crash_bin.crash_synopsis()
    raw_input(" >>>>>>>>>> press key to continue <<<<<<<<<<<< ")
    dbg.terminate_process()


########################################################################################################################
### entry point
########################################################################################################################


# parse command line options.
try:
    opts, args = getopt.getopt(sys.argv[1:], "b:h:i:l:np:qr:tw:", \
        ["boron=", "host=", "ignore=", "log=", "noint", "pid=", "quiet", "recon=", "track_recv", "watch="])
except getopt.GetoptError:
    ERR(USAGE)

boron = pid = host = ignore = track_recv = quiet = noint = recon = watch = log_filename = log_file = None

for opt, arg in opts:
    if opt in ("-b", "--boron"):      boron          = arg
    if opt in ("-h", "--host"):       host           = arg
    if opt in ("-i", "--ignore"):     ignore         = int(arg)
    if opt in ("-l", "--log"):        log_filename   = arg
    if opt in ("-n", "--noint"):      noint          = True
    if opt in ("-p", "--pid"):        pid            = int(arg)
    if opt in ("-q", "--quiet"):      quiet          = True
    if opt in ("-r", "--recon"):      recon_filename = arg
    if opt in ("-t", "--track_recv"): track_recv     = True
    if opt in ("-w", "--watch"):      watch          = arg

if (not pid and not watch) or not recon_filename:
    ERR(USAGE)

# bail early if a log file was specified and we are unable to open it.
if log_filename:
    try:
        log_file = open(log_filename, "w+")
    except:
        ERR("failed opening %s for writing" % log_filename)

# read the list of peek points from the recon file.
try:
    fh = open(recon_filename)
except:
    ERR(USAGE)

for line in fh.readlines():
    line = line.rstrip("\r")
    line = line.rstrip("\n")

    # ignore commented out lines.
    if line[0] == "#":
        continue

    (address, stack_depth, comment) = line.split(":", 2)

    address     = long(address, 16)
    stack_depth = int(stack_depth)

    pp = peek_point()

    pp.stack_depth = stack_depth
    pp.comment     = comment
    pp.contexts    = []
    pp.hit_count   = 0

    peek_points[address] = pp

fh.close()

# if a remote host was specified, instantiate a pydbg client.
if host:
    print "peeking on remote host %s:7373" % host
    dbg = pydbg_client(host, 7373)
else:
    print "peeking locally"
    dbg = pydbg()

dbg.set_callback(EXCEPTION_BREAKPOINT,       handler_breakpoint)
dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, handler_access_violation)

try:
    # if specified, watch for the target process.
    if watch:
        print "watching for process: %s" % watch

        if ignore:
            print "ignoring PID %d" % ignore

        while watch:
            for (pid, name) in dbg.enumerate_processes():
                # ignore the optionally specified PID.
                if pid == ignore:
                    continue

                # if a name match was found, attach to the PID and continue.
                if name.find(".") != -1:
                    name = name.split(".")[0]

                if name.lower() == watch.lower():
                    print "process %s found on pid %d" % (name, pid)
                    watch = None
                    break

            time.sleep(1)

    # attach to the process and enter the debug event loop.
    # our first chance breakpoint handler will set the appropriate breakpoints.
    dbg.attach(pid)
    dbg.debug_event_loop()
except pdx, x:
    sys.stderr.write(x.__str__() + "\n")
    traceback.print_exc()


########################################################################################################################
### reporting
########################################################################################################################


print "debugger detached ... generating reports"

# determine whether we log to screen or file.
if log_file:
    write_line = lambda x: log_file.write("%s\n" % x)
else:
    write_line = lambda x: sys.stdout.write("%s\n" % x)

for address in peek_points:
    pp = peek_points[address]

    if len(pp.contexts) == 0:
        continue

    write_line("")
    write_line("*" * 80)
    write_line("peek point @%08x (%s) hit %d times" % (address, pp.comment, len(pp.contexts)))

    if pp.disabled:
        write_line("disabled at hit #%d" % pp.disabled)

    for context in pp.contexts:
        write_line(context)
        write_line("")

    write_line("*" * 80)
    write_line("")

if log_file:
    log_file.close()

# output the new recon file if we are in interactive mode or if a boron tag was specified.
if not noint or boron:
    try:
        new_recon_filename = recon_filename + ".%d" % pid
        new_recon          = open(new_recon_filename, "w+")
    except:
        ERR("failed opening %s for writing" % new_recon_filename)

    for address in peek_points:
        pp = peek_points[address]

        if pp.disabled:
            new_recon.write("#%08x:%d:%s\n" % (address, pp.stack_depth, pp.comment))
        else:
            new_recon.write("%08x:%d:%s\n" % (address, pp.stack_depth, pp.comment))

    new_recon.close()
########NEW FILE########
__FILENAME__ = proc_peek_recon
#
# IDA Python Proc Peek Recon
# Locate all potentially interesting points and dump to file.
#
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: proc_peek_recon.py 236 2010-03-05 18:16:17Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

from idaapi   import *
from idautils import *
from idc      import *

########################################################################################################################
### Support Functions
###

def get_arg (ea, arg_num):
    arg_index = 1

    while True:
        ea = PrevNotTail(ea)

        if GetMnem(ea) == "push":
            if arg_index == arg_num:
                dref = Dfirst(ea)

                if dref == BADADDR:
                    return dref

                return read_string(dref)

            arg_index += 1


def instruction_match (ea, mnem=None, op1=None, op2=None, op3=None):
    if mnem and mnem != GetMnem(ea):
        return False

    if op1 and op1 != GetOpnd(ea, 0): return False
    if op2 and op2 != GetOpnd(ea, 1): return False
    if op3 and op3 != GetOpnd(ea, 2): return False

    return True


def disasm_match (ea, needle):
    disasm_line = GetDisasm(ea)

    # collapse whitespace
    while disasm_line.find("  ") != -1:
        disasm_line = disasm_line.replace("  ", " ")

    if disasm_line.find(needle) == -1:
        return False

    return True


def read_string (ea):
    s = ""

    while True:
        byte = Byte(ea)

        if byte == 0 or byte < 32 or byte > 126:
            break

        s  += chr(byte)
        ea += 1

    return s


def token_count (format_string):
    return format_string.count("%") - format_string.count("%%")


########################################################################################################################
### Meat and Potatoes
###

peek_filename = AskFile(1, "*.recon", "Proc Peek Recon Filename?")
peek_file     = open(peek_filename, "w+")

#ida_log   = lambda x: None
ida_log    = lambda x: sys.stdout.write(x + "\n")
write_line = lambda x: peek_file.write("%s\n" % x)

window = state = found_ea = processed = 0

ida_log("searching for inline memcpy()'s and sign extended moves (movsx).")

for ea in Heads(MinEA(), MaxEA()):
    processed += 1

    # we don't care about instructions within known library routines.
    if GetFunctionFlags(ea) and GetFunctionFlags(ea) & FUNC_LIB:
        continue

    if disasm_match(ea, "movsx"):
        ida_log("%08x: found sign extended move" % ea)
        write_line("%08x:3:sign extended move" % ea)

    if state == 0 and instruction_match(ea, "shr", "ecx", "2"):
        state  = 1
        window = 0

    elif state == 1 and disasm_match(ea, "rep movsd"):
        state    = 2
        window   = 0
        found_ea = ea

    elif state == 2 and instruction_match(ea, "and", "ecx", "3"):
        state  = 3
        window = 0

    elif state == 3 and disasm_match(ea, "rep movsb"):
        ida_log("%08x: found memcpy" % found_ea)
        set_cmt(found_ea, "inline memcpy()", False)
        write_line("%08x:5:inline memcpy" % found_ea)
        found_ea = state = window = 0

    if window > 15:
        state = window = 0

    if state != 0:
        window += 1

ida_log("done. looked at %d heads." % processed)
ida_log("looking for potentially interesting API calls now.")

# format of functions dictionary is function name: format string arg number
# fill this from google search: +run-time.library +security.note site:msdn.microsoft.com
functions = \
{
    "fread"        : {},
    "gets"         : {},
    "lstrcat"      : {},
    "lstrcpy"      : {},
    "mbscat"       : {},
    "mbscpy"       : {},
    "mbsncat"      : {},
    "memcpy"       : {},
   #"snprintf"     : {"fs_arg": 3},
   #"snwprintf"    : {"fs_arg": 3},
    "sprintf"      : {"fs_arg": 2},
    "sscanf"       : {"fs_arg": 2},
    "strcpy"       : {},
    "strcat"       : {},
    "StrCatBuf"    : {},
    "strncat"      : {},
    "swprintf"     : {"fs_arg": 2},
    "swscanf"      : {"fs_arg": 2},
    "vfprintf"     : {"fs_arg": 2},
    "vfwprintf"    : {"fs_arg": 2},
    "vprintf"      : {"fs_arg": 1},
    "vwprintf"     : {"fs_arg": 1},
    "vsprintf"     : {"fs_arg": 2},
   #"vsnprintf"    : {"fs_arg": 3},
   #"vsnwprintf"   : {"fs_arg": 3},
    "vswprintf"    : {"fs_arg": 2},
    "wcscat"       : {},
    "wcsncat"      : {},
    "wcscpy"       : {},
    "wsprintfA"    : {"fs_arg": 2},
    "wsprintfW"    : {"fs_arg": 2},
    "wvsprintfA"   : {"fs_arg": 2},
    "wvsprintfW"   : {"fs_arg": 2},
}

prefixes  = ["", "_", "__imp_", "__imp__"]

# for every function we are interested in.
for func in functions:
    # enumerate all possible prefixes.
    for prefix in prefixes:
        full_name = prefix + func
        location  = LocByName(full_name)

        if location == BADADDR:
            continue

        ida_log("enumerating xrefs to %s" % full_name)

        for xref in list(CodeRefsTo(location, True)) + list(DataRefsTo(location)):
            if GetMnem(xref) in ("call", "jmp"):
                # ensure the xref does not exist within a known library routine.
                if GetFunctionFlags(ea) and GetFunctionFlags(xref) & FUNC_LIB:
                    continue

                ###
                ### peek a call with format string arguments
                ###

                if functions[func].has_key("fs_arg"):
                    fs_arg = functions[func]["fs_arg"]

                    format_string = get_arg(xref, fs_arg)

                    # format string must be resolved at runtime.
                    if format_string == BADADDR:
                        ida_log("%08x format string must be resolved at runtime" % xref)
                        write_line("%08x:10:%s" % (xref, func))

                    # XXX - we have to escape '%' chars here otherwise 'print', which wraps around 'Message()' will
                    #       incorrectly dereference from the stack and potentially crash the script.
                    else:
                        format_string = str(format_string).replace("%", "%%")

                        # format string found.
                        if format_string.find("%s") != -1:
                            format_string = format_string.replace("\n", "")
                            ida_log("%08x favorable format string found '%s'" % (xref, format_string))
                            write_line("%08x:%d:%s %s" % (xref, token_count(format_string)+fs_arg, func, format_string))

                ###
                ### peek a non format string call
                ###

                else:
                    ida_log("%08x found call to '%s'" % (xref, func))
                    write_line("%08x:3:%s" % (xref, func))

peek_file.close()
print "done."
########NEW FILE########
__FILENAME__ = proc_peek_recon_db
#
# IDA Python Proc Peek Recon
# Locate all potentially interesting points and dump to file.
#
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: proc_peek_recon_db.py 231 2008-07-21 22:43:36Z pedram.amini $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

from idaapi   import *
from idautils import *
from idc      import *

import MySQLdb

########################################################################################################################
### Support Functions
###

def get_arg (ea, arg_num):
    arg_index = 1

    while True:
        ea = PrevNotTail(ea)

        if GetMnem(ea) == "push":
            if arg_index == arg_num:
                dref = Dfirst(ea)

                if dref == BADADDR:
                    return dref

                return read_string(dref)

            arg_index += 1


def instruction_match (ea, mnem=None, op1=None, op2=None, op3=None):
    if mnem and mnem != GetMnem(ea):
        return False

    if op1 and op1 != GetOpnd(ea, 0): return False
    if op2 and op2 != GetOpnd(ea, 1): return False
    if op3 and op3 != GetOpnd(ea, 2): return False

    return True


def disasm_match (ea, needle):
    disasm_line = GetDisasm(ea)

    # collapse whitespace
    while disasm_line.find("  ") != -1:
        disasm_line = disasm_line.replace("  ", " ")

    if disasm_line.find(needle) == -1:
        return False

    return True


def read_string (ea):
    s = ""

    while True:
        byte = Byte(ea)

        if byte == 0 or byte < 32 or byte > 126:
            break

        s  += chr(byte)
        ea += 1

    return s


def token_count (format_string):
    return format_string.count("%") - format_string.count("%%")


def ida_log (message):
    print "RECON> " + message


def add_recon (mysql, module_id, offset, stack_depth, reason, status):
    # escape single quotes and backslashes in fields that might have them.
    reason = reason.replace("\\", "\\\\").replace("'", "\\'")

    sql  = " INSERT INTO pp_recon"
    sql += " SET module_id   = '%d'," % module_id
    sql += "     offset      = '%d'," % offset
    sql += "     stack_depth = '%d'," % stack_depth
    sql += "     reason      = '%s'," % reason
    sql += "     status      = '%s',"  % status
    sql += "     notes       = ''"

    cursor = mysql.cursor()

    try:
        cursor.execute(sql)
    except MySQLdb.Error, e:
        ida_log("MySQL error %d: %s" % (e.args[0], e.args[1]))
        ida_log(sql)
        return False

    cursor.close()
    return True


########################################################################################################################
### Meat and Potatoes
###

def meat_and_potatoes (mysql):
    # init some local vars.
    window = state = found_ea = processed = 0

    # calculate the current modules base address.
    # XXX - cheap hack, the subtraction is for the PE header size.
    base_address = MinEA() - 0x1000

    # create a database entry for the current module.
    cursor = mysql.cursor()

    try:
        cursor.execute("INSERT INTO pp_modules SET name = '%s', base = '%d', notes = ''" % (GetInputFile(), base_address))
    except MySQLdb.Error, e:
        ida_log("MySQL error %d: %s" % (e.args[0], e.args[1]))
        ida_log(sql)
        return

    # save the module ID we just created.
    module_id = cursor.lastrowid

    cursor.close()

    ida_log("searching for inline memcpy()'s and sign extended moves (movsx).")
    for ea in Heads(MinEA(), MaxEA()):
        processed += 1

        # we don't care about instructions within known library routines.
        if GetFunctionFlags(ea) and GetFunctionFlags(ea) & FUNC_LIB:
            continue

        if disasm_match(ea, "movsx"):
            ida_log("%08x: found sign extended move" % ea)

            if not add_recon(mysql, module_id, ea - base_address, 3, "sign extended mov", "new"):
                return

        if state == 0 and instruction_match(ea, "shr", "ecx", "2"):
            # this is a good place to watch the inline strcpy since it gets executed only once and we can see the
            # original size value prior to division by 4.
            state    = 1
            window   = 0
            found_ea = ea

        elif state == 1 and disasm_match(ea, "rep movsd"):
            state    = 2
            window   = 0

        elif state == 2 and instruction_match(ea, "and", "ecx", "3"):
            state  = 3
            window = 0

        elif state == 3 and disasm_match(ea, "rep movsb"):
            ida_log("%08x: found memcpy" % found_ea)
            set_cmt(found_ea, "inline memcpy()", False)

            if not add_recon(mysql, module_id, found_ea - base_address, 5, "inline memcpy", "new"):
                return

            found_ea = state = window = 0

        if window > 15:
            state = window = 0

        if state != 0:
            window += 1

    ida_log("done. looked at %d heads." % processed)
    ida_log("looking for potentially interesting API calls now.")

    # format of functions dictionary is function name: format string arg number
    # XXX - fill this from google search: +run-time.library +security.note site:msdn.microsoft.com
    functions = \
    {
        "fread"        : {},
        "gets"         : {},
        "lstrcat"      : {},
        "lstrcpy"      : {},
        "mbscat"       : {},
        "mbscpy"       : {},
        "mbsncat"      : {},
        "memcpy"       : {},
       #"snprintf"     : {"fs_arg": 3},
       #"snwprintf"    : {"fs_arg": 3},
        "sprintf"      : {"fs_arg": 2},
        "sscanf"       : {"fs_arg": 2},
        "strcpy"       : {},
        "strcat"       : {},
        "StrCatBuf"    : {},
        "strncat"      : {},
        "swprintf"     : {"fs_arg": 2},
        "swscanf"      : {"fs_arg": 2},
        "vfprintf"     : {"fs_arg": 2},
        "vfwprintf"    : {"fs_arg": 2},
        "vprintf"      : {"fs_arg": 1},
        "vwprintf"     : {"fs_arg": 1},
        "vsprintf"     : {"fs_arg": 2},
       #"vsnprintf"    : {"fs_arg": 3},
       #"vsnwprintf"   : {"fs_arg": 3},
        "vswprintf"    : {"fs_arg": 2},
        "wcscat"       : {},
        "wcsncat"      : {},
        "wcscpy"       : {},
        "wsprintfA"    : {"fs_arg": 2},
        "wsprintfW"    : {"fs_arg": 2},
        "wvsprintfA"   : {"fs_arg": 2},
        "wvsprintfW"   : {"fs_arg": 2},
    }

    prefixes  = ["", "_", "__imp_", "__imp__"]

    # for every function we are interested in.
    for func in functions:
        # enumerate all possible prefixes.
        for prefix in prefixes:
            full_name = prefix + func
            location  = LocByName(full_name)

            if location == BADADDR:
                continue

            ida_log("enumerating xrefs to %s" % full_name)

            for xref in CodeRefsTo(location, True) + DataRefsTo(location):
                if GetMnem(xref) in ("call", "jmp"):
                    # ensure the xref does not exist within a known library routine.
                    flags = GetFunctionFlags(xref)
                    if flags:
                        if flags & FUNC_LIB:
                            continue

                    ###
                    ### peek a call with format string arguments
                    ###

                    if functions[func].has_key("fs_arg"):
                        fs_arg = functions[func]["fs_arg"]

                        format_string = get_arg(xref, fs_arg)

                        # format string must be resolved at runtime.
                        if format_string == BADADDR:
                            ida_log("%08x format string must be resolved at runtime" % xref)

                            if not add_recon(mysql, module_id, xref - base_address, 10, func, "new"):
                                return

                        # XXX - we have to escape '%' chars here otherwise 'print', which wraps around 'Message()' will
                        #       incorrectly dereference from the stack and potentially crash the script.
                        else:
                            format_string = str(format_string).replace("%", "%%")

                            # format string found.
                            if format_string.find("%s") != -1:
                                format_string = format_string.replace("\n", "")
                                ida_log("%08x favorable format string found '%s'" % (xref, format_string))

                                if not add_recon(mysql, module_id, xref - base_address, token_count(format_string)+fs_arg, "%s %s" % (func, format_string), "new"):
                                    return

                    ###
                    ### peek a non format string call
                    ###

                    else:
                        ida_log("%08x found call to '%s'" % (xref, func))

                        if not add_recon(mysql, module_id, xref - base_address, 3, func, "new"):
                            return

    ida_log("done.")


########################################################################################################################
### MySQL Connectivity
###

def mysql_connect ():
    mysql_host = None
    mysql_user = None
    mysql_pass = None

    if not mysql_host:
        mysql_host = AskStr("localhost", "MySQL IP address or hostname:")

        if not mysql_host:
            return -1

    if not mysql_user:
        mysql_user = AskStr("root", "MySQL username:")

        if not mysql_user:
            return -1

    if not mysql_pass:
        mysql_pass = AskStr("", "MySQL password:")

        if not mysql_pass:
            return -1

    # connect to mysql
    try:
        mysql = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_pass, db="paimei")
    except MySQLdb.OperationalError, err:
        ida_log("failed connecting to MySQL server: %s" % err[1])
        mysql = None

    return mysql


########################################################################################################################
### main()
###

def main ():
    mysql = mysql_connect()

    if mysql == -1:
        ida_log("cancelled by user.")
    elif mysql == None:
        # error message already printed.
        return
    else:
        meat_and_potatoes(mysql)
        mysql.close()

main()
########NEW FILE########
__FILENAME__ = push_pop_unpacker
#!c:\\python\\python.exe

"""
Push/Pop "Unpacker" (ie: auto OEP finder)
Copyright (C) 2007 Pedram Amini <pedram.amini@gmail.com>

$Id: push_pop_unpacker.py 214 2007-08-23 05:48:44Z pedram $

Description:
    This is a quick and dirty PyDbg implementation of a known generic technique for stopping an unpacker at OEP. In
    essence the script does the following. Single step the packed executable until a PUSHA(D) is discovered. Step over
    the PUSHA(D) instruction and set a hardware breakpoint somewhere in the stack-range of the pushed data. Continue
    execution until the breakpoint is hit, usually due to a POPA(D). This is at or near the OEP. Works against UPX,
    ASPack, I believe NSPack and others.

    This script was written during Ero and I's 2007 Reverse Engineering class at BlackHat:

        http://www.blackhat.com/html/bh-usa-07/train-bh-us-07-pa.html
"""

from pydbg         import *
from pydbg.defines import *

import os
import sys
import pefile

try:
    target  = sys.argv[1]
    monitor = None
except:
    sys.stderr.write("push_pop_unpacker.py <exe to unpack>\n")
    sys.exit(1)

if not os.path.exists(target):
    sys.stderr.write("%s not found.\n" % target)
    sys.exit(1)

def end_of_packer (dbg):
    print "%08x: end of packer reached?!?" % dbg.exception_address
    dbg.terminate_process()
    return DBG_CONTINUE

def set_stack_bp (dbg):
    global monitor
    print "current ESP: %08x" % dbg.context.Esp
    print "setting hw bp at: %08x" % monitor
    dbg.bp_set_hw(monitor, 4, HW_ACCESS, handler=end_of_packer, restore=False)

    return DBG_CONTINUE

def set_stack_bp_helper (dbg):
    global monitor
    monitor = dbg.context.Esp - 4

    print "setting breakpoint to call set_stack_bp() with monitor at %08x" % monitor
    dbg.bp_set(dbg.exception_address + dbg.instruction.length, handler=set_stack_bp, restore=False)

def entry_point (dbg):
    disasm = dbg.disasm(dbg.exception_address)
    print "%08x: %s" % (dbg.exception_address, disasm)

    if not disasm.startswith("pusha"):
        dbg.single_step(True)
    else:
        set_stack_bp_helper(dbg)

    return DBG_CONTINUE

def single_step (dbg):
    disasm = dbg.disasm(dbg.exception_address)
    print "%08x: %s" % (dbg.exception_address, disasm)

    if not disasm.startswith("pusha"):
        dbg.single_step(True)
    else:
        set_stack_bp_helper(dbg)

    return DBG_CONTINUE


# find the entry point for this bad boy.
pe = pefile.PE(target)
ep = pe.OPTIONAL_HEADER.AddressOfEntryPoint + pe.OPTIONAL_HEADER.ImageBase

dbg = pydbg()
dbg.set_callback(EXCEPTION_SINGLE_STEP, single_step)
dbg.load(target)
dbg.bp_set(ep, handler=entry_point, restore=False)
dbg.run()
########NEW FILE########
__FILENAME__ = pydbgc
#!c:\python\python.exe

"""
PyDbg Just-In-Time Debugger
Copyright (C) 2006 Cody Pierce <codyrpierce@gmail.com>

$Id: pydbgc.py 233 2009-02-12 19:01:53Z codyrpierce $

Description:
    This quick and dirty hack gives you a PyDbg command line console with WinDbg-esque commands. One of the cooler
    features of this hack is the ability to step backwards. Yes really, you can step backwards.
"""


import sys, struct, string, re, signal

# This should point to paimei if its not in site-packages
#sys.path.append("C:\\code\\python\\paimei")

from ctypes import *
kernel32 = windll.kernel32

from pydbg import *
from pydbg.defines import *

class PydbgClient:
    ####################################################################################################################
    def __init__(self, dbg="", attach_breakpoint=True):
        self.dbg = dbg
        self.attach_breakpoint = attach_breakpoint

        self.steps = []
        self.breakpoints = []

        self.commands = []
        self.commands.append({"command": "bc",   "description": "Clear breakpoints",                  "handler": self.clear_breakpoints})
        self.commands.append({"command": "bd",   "description": "Delete a breakpoint (ex: db 2)",     "handler": self.delete_breakpoint})
        self.commands.append({"command": "bl",   "description": "List breakpoints",                   "handler": self.list_breakpoints})
        self.commands.append({"command": "bp",   "description": "Set a breakpoint (ex: bp 7ffdb000)", "handler": self.breakpoint})
        self.commands.append({"command": "dc",   "description": "Dump Data Charactes",                "handler": self.dump_data_characters})
        self.commands.append({"command": "dd",   "description": "Dump Data",                          "handler": self.dump_data})
        self.commands.append({"command": "g",    "description": "Resume Execution",                   "handler": self.go})
        self.commands.append({"command": "h",    "description": "Help",                               "handler": self.print_help})
        self.commands.append({"command": "help", "description": "Help",                               "handler": self.print_help})
        self.commands.append({"command": "k",    "description": "Call Stack",                         "handler": self.call_stack})
        self.commands.append({"command": "quit", "description": "Quit",                               "handler": self.quit})
        self.commands.append({"command": "r",    "description": "Modify a register (ex: r eax=10)",   "handler": self.register})
        self.commands.append({"command": "s",    "description": "Single Step",                        "handler": self.single_step})
        self.commands.append({"command": "sb",   "description": "Single Step Backwards",              "handler": self.step_back})
        self.commands.append({"command": "seh",  "description": "Current SEH",                        "handler": self.seh})
        self.commands.append({"command": "u",    "description": "Disassemble (ex: u 7ffdb000",        "handler": self.disassemble})


    ####################################################################################################################
    def breakpoint_handler(self, dbg):
        self.dbg = dbg

        # Initial module bp
        if dbg.first_breakpoint:
            if self.attach_breakpoint:
                signal.signal(signal.SIGBREAK, self.interrupt_handler)
                self.command_line()

            return DBG_CONTINUE

        self.command_line()

        return DBG_CONTINUE


    ####################################################################################################################
    def single_step_handler(self, dbg):
        self.dbg = dbg

        self.command_line()

        return DBG_CONTINUE


    ####################################################################################################################
    def interrupt_handler(self, signum, frame):
        #
        # I gotta figure out how to get a signal in pydbg back here
        sys.stdout.write("\n[*] Catching signal %d\n" % signum)
        if not kernel32.DebugBreakProcess(self.dbg.h_process):
            sys.stdout.write("[!] Problem breaking into process\n")

        return DBG_CONTINUE


    ####################################################################################################################
    def record_step(self):
        step = {}
        stack = ""
        (stacktop, stackbottom) = self.dbg.stack_range()
        current = stackbottom

        stack = self.dbg.read(current, stacktop - stackbottom)

        step["context"] = self.dbg.context
        step["stacktop"] = stacktop
        step["stackbottom"] = stackbottom
        step["stack"] = stack

        self.steps.append(step)

        return 0


    ####################################################################################################################
    def command_line(self):
        self.print_state()

        while True:
            sys.stdout.write("pydbgc> ")
            commandline = sys.stdin.readline().rstrip('\n')
            if re.search(' ', commandline):
                (command, args) = commandline.split(' ', 1)
            else:
                command = commandline
                args = ""

            rc = self.process_command(command, args)

            if rc == 1:
                return True

            sys.stdout.write("\n")

        return False


    ####################################################################################################################
    def print_state(self):
        #address = self.dbg.exception_address
        address = self.get_reg_value("eip")
        instruction = self.dbg.get_instruction(address)

        '''
        eax=7ffdf000 ebx=00000001 ecx=00000002 edx=00000003 esi=00000004 edi=00000005
        eip=7c901230 esp=0092ffcc ebp=0092fff4 iopl=0         nv up ei pl zr na pe nc
        cs=001b  ss=0023  ds=0023  es=0023  fs=0038  gs=0000             efl=00000246
        ntdll!DbgBreakPoint:
        7c901230 cc              int     3
        '''

        try:
            module = self.dbg.addr_to_module(address).szModule
        except:
            module = "N/A"

        sys.stdout.write("\n")
        sys.stdout.write("eax=%08x ebx=%08x ecx=%08x edx=%08x esi=%08x edi=%08x\n" %
        (self.get_reg_value("eax"), self.get_reg_value("ebx"), self.get_reg_value("ecx"),
        self.get_reg_value("edx"), self.get_reg_value("esi"), self.get_reg_value("edi")))
        sys.stdout.write("eip=%08x esp=%08x ebp=%08x\n\n" %
        (self.get_reg_value("eip"), self.get_reg_value("esp"), self.get_reg_value("ebp")))
        sys.stdout.write("%s!%08x  %s\n\n" %
        (module, address, self.dbg.disasm(address)))

        return 0


    ####################################################################################################################
    def process_command(self, command, args):
        for c in self.commands:
            if command == c["command"]:
                rc = c["handler"](args)
                return rc

        sys.stdout.write("Unknown command %s" % command)

        return -1


    ####################################################################################################################
    def go(self, *arguments, **keywords):
        self.dbg.single_step(False)
        sys.stdout.write("\nContinuing\n")

        return 1


    ####################################################################################################################
    def breakpoint(self, *arguments, **keywords):
        try:
            address = string.atol(arguments[0], 16)
        except:
            sys.stdout.write("Syntax error\n")
            return -1

        self.dbg.bp_set(address, restore=True, handler=self.breakpoint_handler)
        self.breakpoints.append(address)

        return 0


    ####################################################################################################################
    def disassemble(self, *arguments, **keywords):
        try:
            address = string.atol(arguments[0], 16)
        except:
            sys.stdout.write("Syntax error\n")
            return -1

        sys.stdout.write(self.dbg.disasm(address))

        return 0


    ####################################################################################################################
    def list_breakpoints(self, *arguments, **keywords):
        for i in xrange(0, len(self.breakpoints)):
            address = self.breakpoints[i]
            sys.stdout.write("[%d] %s!%08x\n" %
            (i, self.dbg.addr_to_module(address).szModule, address))

        return 0


    ####################################################################################################################
    def clear_breakpoints(self, *arguments, **keywords):
        for address in self.breakpoints:
            self.dbg.bp_del(address)

        self.breakpoints = []

        return 0


    ####################################################################################################################
    def delete_breakpoint(self, *arguments, **keywords):
        try:
            bp = int(arguments[0])
        except:
            sys.stdout.write("Syntax error\n")
            return -1

        self.dbg.bp_del(self.breakpoints[bp])
        self.breakpoints.remove(self.breakpoints[bp])

        return 0


    ####################################################################################################################
    def single_step(self, *arguments, **keywords):
        self.record_step()

        self.dbg.single_step(True)

        return 1


    ####################################################################################################################
    def step_back(self, *arguments, **keywords):
        step = self.steps.pop()
        context = step["context"]
        stack = step["stack"]

        current = step["stackbottom"]
        self.dbg.write(current, stack)

        self.dbg.set_thread_context(context)
        self.print_state()

        return 0


    ####################################################################################################################
    def register(self, *arguments, **keywords):
        arg1 = arguments[0].strip()

        if not re.search('=', arg1):
            self.print_state()

            return 0

        try:
            (register, value) = re.split('=', arg1)
            register = register.strip()
            value = string.atol(value.strip())
        except:
            sys.stdout.write("Syntax error\n")
            return -1

        self.set_reg_value(register, value)

        return 0


    ####################################################################################################################
    def dump_data(self, *arguments, **keywords):
        display = 128
        length = 0
        arg1 = arguments[0].strip()

        try:
            if re.search('\+', arg1):
                (address, offset) = arg1.split('+', 1)
                if re.search('[g-x]', address, re.I):
                    address = self.get_reg_value(address)
                else:
                    address = string.atol(address.stip(), 16)

                address = address + int(offset.strip())
            elif re.search('-', arg1):
                (address, offset) = arg1.split('-', 1)
                address = string.atol(address.strip(), 16) - int(offset.strip())
            else:
                if re.search('[g-x]', arg1, re.I):
                    address = self.get_reg_value(arg1)
                else:
                    address = string.atol(arg1, 16)
        except:
            sys.stdout.write("Syntax error\n")
            return -1


        while length <= display:
            if not length % 32:
                sys.stdout.write("\n%08x: " % (address + length))
            else:
                sys.stdout.write(" ")

            try:
                bytes = self.dbg.read(address + length, 4)
                sys.stdout.write("%08x" % (self.dbg.flip_endian_dword(bytes)))
            except:
                sys.stdout.write("????????")

            length += 4

        sys.stdout.write("\n")

        return 0


    ####################################################################################################################
    def dump_data_characters(self, *arguments, **keywords):
        # Todo

        return 0


    ####################################################################################################################
    def call_stack(self, *arguments, **keywords):
        callstack = self.dbg.stack_unwind()

        for address in callstack:
            sys.stdout.write("%s!%x\n" % (self.dbg.addr_to_module(address).szModule, address))

        return 0


    ####################################################################################################################
    def seh(self, *arguments, **keywords):
        seh = self.dbg.seh_unwind()

        for address, handler in seh:
            sys.stdout.write("%x:  %x\n" % (address, handler))

        return 0


    ####################################################################################################################
    def quit(self, *arguments, **keywords):
        self.clear_breakpoints()
        self.steps = []
        
        return 1


    ####################################################################################################################
    def print_help(self, *arguments, **keywords):
        sys.stdout.write("\n")
        for command in self.commands:
            sys.stdout.write("\t%s:\t%s\n" % (command["command"], command["description"]))

        return 0


    ####################################################################################################################
    def get_reg_value(self, register):
        context = self.dbg.get_thread_context(self.dbg.h_thread)

        if   register == "eax" or register == 0: return context.Eax
        elif register == "ecx" or register == 1: return context.Ecx
        elif register == "edx" or register == 2: return context.Edx
        elif register == "ebx" or register == 3: return context.Ebx
        elif register == "esp" or register == 4: return context.Esp
        elif register == "ebp" or register == 5: return context.Ebp
        elif register == "esi" or register == 6: return context.Esi
        elif register == "edi" or register == 7: return context.Edi
        elif register == "eip" or register == 8: return context.Eip

        return False


    ####################################################################################################################
    def set_reg_value(self, register, value):
        context = self.dbg.get_thread_context(self.dbg.h_thread)

        if   register == "eax" or register == 0: context.Eax = value
        elif register == "ecx" or register == 1: context.Ecx = value
        elif register == "edx" or register == 2: context.Edx = value
        elif register == "ebx" or register == 3: context.Ebx = value
        elif register == "esp" or register == 4: context.Esp = value
        elif register == "ebp" or register == 5: context.Ebp = value
        elif register == "esi" or register == 6: context.Esi = value
        elif register == "edi" or register == 7: context.Edi = value
        elif register == "eip" or register == 8: context.Eip = value

        self.dbg.set_thread_context(context)

        return True


########################################################################################################################


if __name__ == "__main__":
    def attach_target_proc(dbg, procname):
        '''
        Attaches to procname if it finds it otherwise loads.
        '''
        
        imagename = procname.rsplit('\\')[-1]
        print "[*] Trying to attach to existing %s" % imagename
        for (pid, name) in dbg.enumerate_processes():
            if imagename in name:
                try:
                    print "[*] Attaching to %s (%d)" % (name, pid)
                    dbg.attach(pid)
                except:
                    print "[!] Problem attaching to %s" % name

                    return False

                return True

        try:
            print "[*] Trying to load %s" % (procname)
            dbg.load(procname, "")

        except:
            print "[!] Problem loading %s" % (procname)

            return False

        return True

    ####################################################################################################################
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print "%s <process name> [attach breakpoint]" % sys.argv[0]
        sys.exit(-1)
    elif len(sys.argv) == 3:
        option = int(sys.argv[2])

        if option == 1:
            ab = True
        else:
            ab = False

    process = sys.argv[1]

    dbg = pydbg()
    pydbgc = PydbgClient(attach_breakpoint=ab)
    dbg.pydbgc = pydbgc

    dbg.set_callback(EXCEPTION_BREAKPOINT, dbg.pydbgc.breakpoint_handler)
    dbg.set_callback(EXCEPTION_SINGLE_STEP, dbg.pydbgc.single_step_handler)

    if not attach_target_proc(dbg, process):
        print "[!] Couldnt load/attach to %s" % process

        sys.exit(-1)

    dbg.debug_event_loop()
########NEW FILE########
__FILENAME__ = pydbg_server
#!c:\python\python.exe

#
# PyDBG
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: pydbg_server.py 194 2007-04-05 15:31:53Z cameron $
#

'''
@author:       Pedram Amini
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import socket
import sys
import threading
import cPickle
import getopt

from pydbg import *
from pydbg.defines import *

# null either of these by setting to lambda x: None
err = lambda msg: sys.stderr.write("[!] " + msg + "\n") or sys.exit(1)
log = lambda msg: sys.stdout.write("[*] " + msg + "\n")


########################################################################################################################


class pydbg_server_thread (threading.Thread):
    def __init__ (self, client, client_address):
        threading.Thread.__init__(self)
        self.client         = client
        self.client_address = client_address
        self.pydbg          = pydbg(cs=True)
        self.connected      = True


    def callback_handler_wrapper (self, pydbg):
        try:
            # non client/server access to dbg/context are done via member variables. in client/server mode however, we
            # must excplicity pass these back to the client.
            self.pickle_send(("callback", pydbg.dbg, pydbg.context))
        except:
            return DBG_CONTINUE

        # enter a read loop, exiting when the client sends the "DONE" moniker.
        while 1:
            try:
                pickled = self.pickle_recv()
            except:
                return DBG_CONTINUE

            # XXX - this try except block should not be needed. look into the cause of why there is an out of order
            #       recv at some later point.
            try:
                (method, (args, kwargs)) = pickled
            except:
                break

            ret_message = False

            # client is done handling the exception.
            if method == "**DONE**":
                return args

            else:
                # resolve a pointer to the requested method.
                method_pointer = None

                try:
                    exec("method_pointer = self.pydbg.%s" % method)
                except:
                    pass

                if method_pointer:
                    try:
                        ret_message = method_pointer(*args, **kwargs)
                    except pdx, x:
                        ret_message = ("exception", x.__str__())

            try:
                self.pickle_send(ret_message)
            except:
                return DBG_CTONINUE


    def pickle_recv (self):
        try:
            length   = long(self.client.recv(4), 16)
            received = self.client.recv(length)

            return cPickle.loads(received)
        except:
            log("connection severed to %s:%d" % (self.client_address[0], self.client_address[1]))
            self.connected = False
            self.pydbg.set_debugger_active(False)
            raise Exception


    def pickle_send (self, data):
        print "sending", data
        data = cPickle.dumps(data)

        try:
            self.client.send("%04x" % len(data))
            self.client.send(data)
        except:
            log("connection severed to %s:%d" % (self.client_address[0], self.client_address[1]))
            self.connected = False
            self.pydbg.set_debugger_active(False)
            raise Exception


    def run (self):
        log("connection received from: %s:%d" % (self.client_address[0], self.client_address[1]))

        while self.connected:
            try:
                pickled = self.pickle_recv()
            except:
                break

            # XXX - this try except block should not be needed. look into the cause of why there is an out of order
            #       recv at some later point.
            try:
                (method, (args, kwargs)) = pickled
                print method, args, kwargs
            except:
                continue

            ret_message = False

            # if client requested the set_callback method.
            if method == "set_callback":
                self.pydbg.set_callback(args, self.callback_handler_wrapper)
                ret_message = True

            else:
                # resolve a pointer to the requested method.
                method_pointer = None
                try:
                    exec("method_pointer = self.pydbg.%s" % method)
                except:
                    pass

                if method_pointer:
                    try:
                        ret_message = method_pointer(*args, **kwargs)
                    except pdx, x:
                        ret_message = ("exception", x.__str__())

            try:
                self.pickle_send(ret_message)
            except:
                break


########################################################################################################################


# parse command line options.
try:
    opts, args = getopt.getopt(sys.argv[1:], "h:p:", ["host=","port="])
except getopt.GetoptError:
    err(USAGE)

host = "0.0.0.0"
port = 7373

for o, a in opts:
    if o in ("-h", "--host"): host = a
    if o in ("-p", "--port"): port = int(a)

try:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
except:
    sys.stderr.write("Unable to bind to %s:%d\n" % (host, port))
    sys.exit(1)

while 1:
    log("waiting for connection")

    (client, client_address) = server.accept()

    server_thread = pydbg_server_thread(client, client_address)

    try:
        server_thread.start()
    except:
        log("client disconnected")
########NEW FILE########
__FILENAME__ = stack_integrity_monitor
#!c:\python\python.exe

"""
Stack Integrity Monitor
Copyright (C) 2007 Pedram Amini <pedram.amini@gmail.com>

$Id: stack_integrity_monitor.py 214 2007-08-23 05:48:44Z pedram $

Description:
    A command line utility implemented in under 150 lines of Python code which provides an automated solution to the
    task of tracking down the source of a stack overflow. The main reason stack overflows are exploitable is because
    control information is stored in the same medium as volatile user-controllable data. If we can move or mirror the
    call-chain "out of band", then we can verify the integrity of the stack at run-time. Skipping over the intricate
    details, here is the high level overview of how the utility works:

        1. Instantiate a debugger object and attach to the target program.
        2. Set a breakpoint where we want the trace to start, this can be as simple as setting a break on recv().
        3. Once the breakpoint is hit, set the active thread to single step.
        4. When a CALL instruction is reached, copy the stack and return addresses to an internal "mirror" list.
        5. When a RET instruction is reached, walk through the "mirror" list and verify that the values match the
           actual stack.
        6. When the last saved return address is reached, pop it off the internal "mirror" list.

    If during the stack integrity check a mismatch is found, then not only do we know that a stack overflow has
    occurred, but we know which functions frame the overflow originated in and we can pinpoint the cause of the
    overflow. For more information see:

        http://dvlabs.tippingpoint.com/blog/2007/05/02/pin-pointing-stack-smashes

TODO (performance improvements):
    - replace disasm with byte checks
    - step over rep sequences
"""

import sys
import time
import utils
import pydbgc

from pydbg         import *
from pydbg.defines import *


USAGE = "USAGE: stack_fuck_finder.py <BP ADDR> <PID>"
error = lambda msg: sys.stderr.write("ERROR> " + msg + "\n") or sys.exit(1)


########################################################################################################################
def check_stack_integrity (dbg):
    if not dbg.juju_found:
        for addr, value in dbg.mirror_stack:
            new_value = dbg.flip_endian_dword(dbg.read(addr, 4))

            if new_value != value:
                dbg.juju_found = True

                for a, v in dbg.mirror_stack:
                    if a == addr:
                        print "%08x: %s.%08x --> %08x" % (a, dbg.addr_to_module(v).szModule, v, new_value)
                    else:
                        print "%08x: %s.%08x" % (a, dbg.addr_to_module(v).szModule, v)

                print
                print "STACK INTEGRITY VIOLATON AT: %s.%08x" % (dbg.addr_to_module(dbg.context.Eip).szModule, dbg.context.Eip)
                print "analysis took %d seconds" % (time.time() - dbg.start_time)
                print

                d = pydbgc.PydbgClient(dbg, False)
                d.command_line()

                break


########################################################################################################################
def handler_trace_start (dbg):
    dbg.monitor_tid = dbg.dbg.dwThreadId
    print "starting hit trace on thread %d at 0x%08x" % (dbg.monitor_tid, dbg.context.Eip)
    dbg.single_step(True)

    return DBG_CONTINUE


########################################################################################################################
def handler_breakpoint (dbg):
    if dbg.first_breakpoint:
        return DBG_CONTINUE

    # ignore threads we don't care about that happened to hit one of our breakpoints.
    if dbg.dbg.dwThreadId != dbg.monitor_tid:
        return DBG_CONTINUE

    if dbg.mirror_stack:
        dbg.mirror_stack.pop()

    dbg.single_step(True)
    return DBG_CONTINUE


########################################################################################################################
def handler_single_step (dbg):
    if dbg.dbg.dwThreadId != dbg.monitor_tid:
        return DBG_CONTINUE

    if dbg.juju_found:
        return DBG_CONTINUE

    disasm   = dbg.disasm(dbg.context.Eip)
    ret_addr = dbg.get_arg(0)

    # if the current instruction is in a system DLL and the return address is not, set a breakpoint on it and continue
    # without single stepping.
    if dbg.context.Eip > 0x70000000 and ret_addr < 0x70000000:
        dbg.bp_set(ret_addr)
        return DBG_CONTINUE

    #print "%08x: %s" % (dbg.context.Eip, dbg.disasm(dbg.context.Eip))

    if dbg.mirror_stack and dbg.context.Eip == dbg.mirror_stack[-1][1]:
        dbg.mirror_stack.pop()

    if disasm.startswith("ret"):
        check_stack_integrity(dbg)

    if disasm.startswith("call"):
        dbg.mirror_stack.append((dbg.context.Esp-4, dbg.context.Eip + dbg.instruction.length))

    dbg.single_step(True)
    return DBG_CONTINUE


########################################################################################################################
def handler_access_violation (dbg):
    check_stack_integrity(dbg)

    crash_bin = utils.crash_binning.crash_binning()
    crash_bin.record_crash(dbg)

    print crash_bin.crash_synopsis()
    dbg.terminate_process()


########################################################################################################################
if len(sys.argv) != 3:
    error(USAGE)

try:
    bp_addr = long(sys.argv[1], 16)
    pid     = int(sys.argv[2])
except:
    error(USAGE)

dbg = pydbg()
dbg.mirror_stack = []
dbg.monitor_tid  = 0
dbg.start_time   = time.time()
dbg.juju_found   = False

dbg.set_callback(EXCEPTION_BREAKPOINT,       handler_breakpoint)
dbg.set_callback(EXCEPTION_SINGLE_STEP,      handler_single_step)
dbg.set_callback(EXCEPTION_ACCESS_VIOLATION, handler_access_violation)

dbg.attach(pid)
dbg.bp_set(bp_addr, handler=handler_trace_start, restore=False)
print "watching for hit at %08x" % bp_addr
dbg.run()

########NEW FILE########
__FILENAME__ = struct_spy
#!/usr/bin/env python

# $Id: struct_spy.py 233 2009-02-12 19:01:53Z codyrpierce $

'''
    Struct Spy
    
    Copyright (C) 2006 Cody Pierce <codyrpierce@gmail.com>
    
    Description: This PyDbg will monitor structures being used based on
    their register+offset instruction. It will log all read, writes, and
    values, along with the addresses they occured at. It will then output
    this into a navigable html where you can drill down into the
    structure and its access. 
    
'''

######################################################################
#
# Includes
#
######################################################################

import sys
import os
import string
import struct
import time
import atexit

from pydbg import *
from pydbg.defines import *
from ctypes import *

kernel32 = windll.kernel32

######################################################################
#
# Our data classes
#
######################################################################

class Breakpoint:
    address = 0x00000000
    
    def __init__(self, address):
        self.address = address
        self.hit_count = 0
        self.description = "None"
        self.handler = self.breakpoint_handler
    
    def set_breakpoint(self, dbg):
        dbg.bp_set(self.address)
       
        return True

    def breakpoint_handler(self, dbg):
        
        return DBG_CONTINUE
    
class DbgException:
    current_id = 0
    
    def __init__(self, dbg):
        DbgException.current_id += 1
        self.id = DbgException.current_id
        
        self.address = dbg.exception_address
        self.module = dbg.addr_to_module(self.address).szModule
        
        if dbg.write_violation:
            self.direction = "write"
        else:
            self.direction = "read"
        
        self.violation_address = dbg.violation_address
        self.violation_thread_id = dbg.dbg.dwThreadId
        
        self.context = dbg.context
        self.context_dump = dbg.dump_context(self.context, print_dots=False)
        
        self.disasm = dbg.disasm(self.address)
        self.disasm_around = dbg.disasm_around(self.address)
        
        self.call_stack = dbg.stack_unwind()
        
        self.seh_unwind = dbg.seh_unwind

    def render_text(self, dbg, path):
        filename = "%s.%x" % (path, self.address)
        
        try:
            fh = open(filename + ".txt", "w")
        except:
            print "[!] Problem opening exception file %s" % filename
            sys.exit(-1)
        
        fh.write("\nException [0x%08x]\n" % self.address)
        fh.write("=" * 72)
        fh.write("\nDirection: %s\n" % self.direction)
        fh.write("Disasm: %s\n" % self.disasm)
        fh.write("Context:\n%s\n" % self.context_dump)
        fh.write("Call Stack:\n")
        for addr in self.call_stack:
            fh.write("  %s!0x%08x\n" % (dbg.addr_to_module(addr).szModule, addr))
        fh.write("\n")
        fh.close()
    
    def render_html(self, dbg, path):
        filename = "%s.%x" % (path, self.address)
        
        try:
            fh = open(filename + ".html", "w")
        except:
            print "[!] Problem opening exception file %s" % filename
            sys.exit(-1)
        
        fh.write("<html><head><title>Exception 0x%x</title></head><body><br>" % self.address)
        fh.write("\nException [0x%08x]<br>" % self.address)
        fh.write("=" * 72)
        fh.write("<br>Direction: %s<br>" % self.direction)
        fh.write("Disasm: %s<br>" % self.disasm)
        fh.write("Context:<br><pre>%s</pre><br>" % self.context_dump)
        fh.write("Call Stack:<br>")
        for addr in self.call_stack:
            fh.write("  %s!0x%08x<br>" % (dbg.addr_to_module(addr).szModule, addr))
        fh.write("<br>")
        fh.write("</body></html>")
        fh.close()
        
    def display(self,dbg):
        print "\nException [0x%08x]" % self.address
        print "=" * 72
        print "Direction: %s" % self.direction
        print "Disasm: %s" % self.disasm
        print "Context:\n%s" % self.context_dump
        print "Call Stack:" 
        for addr in self.call_stack:
            print "  %s!0x%08x" % (dbg.addr_to_module(addr).szModule, addr)
        print "\n"

class Offset:
    
    def __init__(self, parent, offset, size=4):
        self.parent = parent
        self.offset = offset
        self.size = size
        self.orig_data = ""
        self.data = ""
        self.dbg_exceptions = []
        self.modifications = []
        self.mod_addr = 0x00000000
        
        self.read_count = 0
        self.write_count = 0
        
        self.last_read = 0x00000000
        self.last_write = 0x00000000
        self.last_exception_id = 0
        self.last_module = 0x00000000
        
        self.handler = self.offset_handler
        
        self.description = "No description"
        
    def offset_handler(self, dbg):
        print "[*] Hit Offset Handler @ [%04d] 0x%08x 0x%08x" % (self.last_exception_id, dbg.exception_address, self.mod_addr)
        
        if dbg.exception_address != self.mod_addr:
            self.modifications.append((self.last_exception_id, dbg.read_process_memory(self.parent.address + self.offset, 4)))
        elif dbg.exception_address == self.mod_addr:
            self.modifications.append((self.last_exception_id, dbg.read_process_memory(self.parent.address + self.offset, 4)))
            #dbg.set_callback(EXCEPTION_SINGLE_STEP, dbg.exception_handler_single_step)
            dbg.single_step(False)
        
        return DBG_CONTINUE
    
    def render_text(self, dbg, path, excepts=True):
        filename = "%s.%x" % (path, self.offset)
        
        try:
            fh = open(filename + ".txt", "w")
        except:
            print "[!] Problem offset opening %s" % filename
            sys.exit(-1)
        
        fh.write("\nOffset [0x%08xx+0x%x]:\n" % (self.parent.address, self.offset))
        fh.write("=" * 72)
        fh.write("\nDescription: %s\n" % self.description)
        fh.write("Address: 0x%08x\n" % (self.parent.address + self.offset))
        fh.write("Size: %d\n" % self.size)
        fh.write("Read Count: %d\n" % self.read_count)
        fh.write("Last Read: 0x%08x\n" % self.last_read)
        fh.write("Write Count: %d\n" % self.write_count)
        fh.write("Last Write: 0x%08x\n" % self.last_write)
        fh.write("Last Module: %s\n" % self.last_module)
        if excepts:
            for dbgexcept in self.dbg_exceptions:
                fh.write("Exception: 0x%08x %s\n" % (dbgexcept.address, dbgexcept.disasm))
                dbgexcept.render_html(dbg, filename)
        fh.write("\n")
        fh.close()
    
    def render_html(self, dbg, path, excepts=True):
        filename = "%s.%x" % (path, self.offset)
        
        try:
            fh = open(filename + ".html", "w")
        except:
            print "[!] Problem offset opening %s" % filename
            sys.exit(-1)
        
        fh.write("<html><head><title>Offset 0x%08x+%x</title></head><body><br>" % (self.parent.address, self.offset))
        fh.write("\nOffset [0x%08x+0x%x]:<br>" % (self.parent.address, self.offset))
        fh.write("=" * 72)
        fh.write("<br>Description: %s<br>" % self.description)
        fh.write("Address: 0x%08x<br>" % (self.parent.address + self.offset))
        fh.write("Size: %d<br>" % self.size)
        fh.write("Read Count: %d<br>" % self.read_count)
        fh.write("Last Read: 0x%08x<br>" % self.last_read)
        fh.write("Write Count: %d<br>" % self.write_count)
        fh.write("Last Write: 0x%08x<br>" % self.last_write)
        fh.write("Last Module: %s<br>" % self.last_module)

        if excepts:
            fh.write("<table cellspacing=10><tr><td>")
            for dbgexcept in self.dbg_exceptions:
                fh.write("[%04d]: <a href=\"%s.%x.html\">0x%08x</a><br>" % (dbgexcept.id, filename.split('/')[-1], dbgexcept.address, dbgexcept.address))
                dbgexcept.render_html(dbg, filename)
            fh.write("</td><td>")
            for dbgexcept in self.dbg_exceptions:
                fh.write("[%.5s]<br>" % dbgexcept.direction)
            fh.write("</td><td>")
            for dbgexcept in self.dbg_exceptions:
                fh.write("%s<br>" % dbgexcept.disasm)
            fh.write("</td><td>")
            for (id,data) in self.modifications:
                fh.write("[%04d] 0x%08x<br>" % (id, struct.unpack("<L", data)[0]))
            fh.write("</td></tr></table>")
        
        fh.write("<br>")
        fh.write("</body></html>")
        fh.close()
        
    def display(self, dbg, excepts=True):
        print "\nOffset [0x%08xx+0x%x]:" % (self.parent.address, self.offset)
        print "=" * 72
        print "Description: %s" % self.description
        print "Address: 0x%08x" % (self.parent.address + self.offset)
        print "Size: %d" % self.size
        print "Read Count: %d" % self.read_count
        print "Last Read: 0x%08x" % self.last_read
        print "Write Count: %d" % self.write_count
        print "Last Write: 0x%08x" % self.last_write
        print "Last Module: %s" % self.last_module
        if excepts:
            for dbgexcept in self.dbg_exceptions:
                dbgexcept.display(dbg)
        print "\n"
    

class Structure:
    
    def __init__(self, address, length, timestamp):
        self.address = address
        self.size = length
        self.timestamp = timestamp
        self.orig_data = ""
        self.data = ""
        self.offsets = []
        self.handler = self.structure_handler
        self.description = "None"
        
    def exists(self, offset):
        for off in offsets:
            if offset == off.offset:
                return True
        
        return False
    
    def add_offset(self, offset):
        off = Offset(self, offset)
        self.offset.append(off)        
    
    def structure_handler(self, dbg):
        #print "[*] Hit Structure Handler"
        
        if not dbg.memory_breakpoint_hit:
            return DBG_CONTINUE
            
        module = dbg.addr_to_module(dbg.exception_address).szModule
        
        if dbg.bp_is_ours_mem(self.address):
            off = dbg.violation_address - self.address
            exists = False
            
            print "[*] Hit @ 0x%08x offset 0x%04x" % (dbg.violation_address, off)
            
            # Do the offset creation
            for o in xrange(0, len(self.offsets)):
                if self.offsets[o].offset == off:
                    offset = self.offsets[o]
                    offset.data = dbg.read_process_memory(dbg.violation_address, 1)
                    exists = True
                    break
            
            if not exists:
                offset = Offset(self, off)
                offset.orig_data = dbg.read_process_memory(dbg.violation_address, 1)
                offset.data = offset.orig_data
            
            dbgexcept = DbgException(dbg)
            offset.last_exception_id = dbgexcept.id
            
            if dbgexcept.direction == "read":
                offset.read_count += 1
                offset.last_read = dbgexcept.address
            else:
                offset.write_count += 1
                offset.last_write = dbgexcept.address
            
            offset.last_module = dbgexcept.module
            
            print "[*] [%s!0x%08x] %s [%s]" % (offset.last_module, dbgexcept.address, dbg.disasm(dbgexcept.address), dbgexcept.direction)
            
            offset.mod_addr = dbgexcept.address + dbg.instruction.length
            offset.dbg_exceptions.append(dbgexcept)
            
            # Store the new offset
            if not exists:
                self.offsets.append(offset)
            else:
                self.offsets[o] = offset
            
            # Get the modification data
            dbg.set_callback(EXCEPTION_SINGLE_STEP, offset.handler)  
            dbg.single_step(True)
            
        return DBG_CONTINUE
    
    def render_text(self, dbg, path, offsets=True):
        filename = "%s.%x" % (path, self.address)
        
        try:
            fh = open(filename + ".txt", "w")
        except:
            print "[!] Problem offset structure %s" % filename
            sys.exit(-1)
        
        fh.write("\nStructure [0x%08x]:\n" % self.address)
        fh.write("=" * 72)
        fh.write("\nAddress: 0x%08x\n" % self.address)
        fh.write("Size: %d\n" % self.size)
        fh.write("\n")
        for offset in self.offsets:
            fh.write("Offset: 0x%08x\n" % offset.offset)
            offset.render_text(dbg, filename)
        fh.write("\n\n")
        fh.close()
    
    def print_dump_html(self, fh, data):
        counter = 0
        pos = 0
        bold = False
        
        for char in data:
            for off in self.offsets:
                if off.offset == pos:
                    bold = True
                    break
                else:
                    bold = False
            
            if counter == 0:
                fh.write("0x%08x: " % pos)
                counter += 1
        
            if counter == 8:
                if bold:
                    fh.write("<b>0x%02x</b>  " % ord(char))
                else:
                    fh.write("0x%02x  " % ord(char))
                counter += 1
            elif counter < 16:
                if bold:
                    fh.write("<b>0x%02x</b> " % ord(char))
                else:
                    fh.write("0x%02x " % ord(char))
                counter += 1
            else:
                if bold:
                    fh.write("<b>0x%02x</b>  " % ord(char))
                else:
                    fh.write("0x%02x  " % ord(char))
                    
                while counter > 0:
                    char = data[pos - counter]
        
                    if counter == 8:
                        if char in string.printable:
                            fh.write("%c " % char)
                        else:
                            fh.write(". ")
                        counter -= 1
                    elif counter > 0:
                        if char in string.printable:
                            fh.write("%c" % char)
                        else:
                            fh.write(".")
                        counter -= 1
                    else:
                        if char in string.printable:
                            fh.write("%c<br>" % char)
                        else:
                            fh.write(".<br>")
                        counter = 0
                fh.write("<br>")
            pos += 1
        
        if counter:
            fh.write(" " * (80 - (counter * 5) + 5 + 1))
        
            if counter <= 8:
                fh.write(" ")
        
            while counter > 0:
                char = data[pos - counter]
        
                if counter == 8:
                    if char in string.printable:
                        fh.write("%c " % char)
                    else:
                        fh.write(". ")
                    counter -= 1
                elif counter > 0:
                    if char in string.printable:
                        fh.write("%c" % char)
                    else:
                        fh.write(".")
                    counter -= 1
                else:
                    if char in string.printable:
                        fh.write("%c<br>" % char)
                    else:
                        fh.write(".<br>")
                    counter = 0
        
        fh.write("<br>")
        
    def render_html(self, dbg, path, offsets=True):
        filename = "%s.%x" % (path, self.address)
        
        try:
            fh = open(filename + ".html", "w")
        except:
            print "[!] Problem offset structure %s" % filename
            sys.exit(-1)
            
        fh.write("<html><head><title>Structure 0x%08x</title></head><body><br>" % self.address)
        fh.write("\n<h2>Structure [0x%08x]:<br></h2>" % self.address)
        fh.write("=" * 72)
        fh.write("<br>Address: 0x%08x<br>" % self.address)
        fh.write("Size: %d<br>" % self.size)
        fh.write("<br>")
        fh.write("<table cellpadding=10><tr><td>")
        fh.write("          ")
        self.offsets.sort(cmp=numeri)
        for offset in self.offsets:
            fh.write("Offset: <a href=\"%s.%x.html\">0x%08x</a><br>" % (filename.split('/')[-1], offset.offset, offset.offset))
            offset.render_html(dbg, filename)
        fh.write("</td><td>")
        for offset in self.offsets:
            fh.write("[0x%02x] -> [0x%02x]<br>" % (struct.unpack("<B", offset.orig_data)[0], struct.unpack("<B", offset.data)[0]))
        fh.write("</td><td>")
        fh.write("<b>Before</b><br>")
        fh.write("<pre>")
        self.print_dump_html(fh, self.orig_data)
        fh.write("</pre>")
        fh.write("<br>")
        fh.write("<b>After</b><br>")
        fh.write("<pre>")
        self.print_dump_html(fh, self.data)
        fh.write("</pre>")
        fh.write("</td></tr></table>")
        fh.write("<br>")
        fh.write("</body></html>")
        fh.close()
        
    def display(self, dbg, offsets=True):
        print "\nStructure [0x%08x]:"
        print "=" * 72
        print "Address: 0x%08x" % self.address
        print "Size: %d" % self.size
        print "\n"
        for offset in self.offsets:
            if offset.write_count > 0:
                offset.display(dbg)
        print "\n\n"
        

######################################################################
#
# Our function breakpoint handlers
#
######################################################################

def handler_breakpoint(dbg):
    if dbg.first_breakpoint:
        # We need to set our code bp
        print "[*] Setting bp @ 0x%08x" % dbg.args["address"]
        
        # Might want to keep this but not for now
        dbg.bp_set(dbg.args["address"], restore=False, handler=handler_our_breakpoint)
        
        return DBG_CONTINUE
    
    return DBG_CONTINUE

def handler_our_breakpoint(dbg):
    if dbg.exception_address != dbg.args["address"]:
        
        return DBG_CONTINUE
    
    register = dbg.args["register"]
    value = get_register(dbg, register)
    
    if not value:
        print "[!] Problem getting %s" % register
        
        return DBG_CONTINUE
    
    print "[*] Hit code bp @ [0x%08x] %s = 0x%08x" % (dbg.exception_address, register, value)
    
    print "[*] Creating Structure(0x%08x, %d)" % (value, dbg.args["size"])
    dbg.structure = Structure(value, dbg.args["size"], dbg.args["timestamp"])
    dbg.structure.orig_data = dbg.read_process_memory(dbg.structure.address, dbg.structure.size)
    
    print "[*] Setting mem bp @ 0x%08x size %d" % (dbg.structure.address, dbg.structure.size)
    dbg.bp_set_mem(dbg.structure.address, dbg.structure.size, handler=dbg.structure.handler)
    
    return DBG_CONTINUE

######################################################################
#
# Various utility routines
#
######################################################################

def get_register(dbg, register):
    
    context = dbg.get_thread_context(dbg.h_thread)

    if   register == "EAX": return context.Eax
    elif register == "EBX": return context.Ebx
    elif register == "ECX": return context.Ecx
    elif register == "EDX": return context.Edx
    elif register == "ESI": return context.Esi
    elif register == "EDI": return context.Edi
    elif register == "ESP": return context.Esp
    elif register == "EBP": return context.Ebp
    elif register == "EIP": return context.Eip
    else: return False
    
    
    return False

def numeri(x, y):
    x = x.offset
    y = y.offset
    
    if   x  < y: return -1
    elif x == y: return 0
    else:        return 1

######################################################################
#
# Various set up routines before exection
#
######################################################################

def attach_target_proc(dbg, procname):
    imagename = procname.rsplit('\\')[-1]
    print "[*] Trying to attach to existing %s" % imagename
    for (pid, name) in dbg.enumerate_processes():
        if imagename in name:
            try:
                print "[*] Attaching to %s (%d)" % (name, pid)
                dbg.attach(pid)
            except:
                print "[!] Problem attaching to %s" % name
                
                return False
            
            return True
    
    try:
        print "[*] Trying to load %s %s" % (procname)
        dbg.load(procname, "")
        
    except:
        print "[!] Problem loading %s" % (procname)
        
        return False
    
    return True

def exitfunc(dbg):
    print "[!] Exiting"
    if dbg:
        print "[!] Cleaning up pydbg"
        if hasattr(dbg, "structure"):
            #dbg.structure.display(dbg)
            dbg.structure.data = dbg.read_process_memory(dbg.structure.address, dbg.structure.size)
            dbg.structure.render_html(dbg, "test" + "/" + dbg.args["timestamp"])
        dbg.cleanup()
        dbg.detach()
        
    sys.exit(0)

######################################################################
#
# Static variables
#
######################################################################
filters = ["kernel32.dll", "user32.dll", "msvcrt.dll", "ntdll.dll"]
dbg = ""

######################################################################
#
# Command line arguments
#
######################################################################

# track.py dps.exe 0x006AC928 ebx 256 [read|write|both]*
if len(sys.argv) < 5:
    print "Usage: %s <process name> <address of bp> <register> <size of struct>" % sys.argv[0]
    
    sys.exit(-1)

procname = sys.argv[1]
address = string.atol(sys.argv[2], 0)
register = sys.argv[3].upper()
size = int(sys.argv[4])
timestamp = time.strftime("%m%d%Y%H%M%S", time.localtime())

dbg = pydbg()
dbg.procname = procname
dbg.args = {"address":address, "register":register, "size":size, "timestamp":timestamp}

dbg.set_callback(EXCEPTION_BREAKPOINT, handler_breakpoint)
atexit.register(exitfunc, dbg)

if not attach_target_proc(dbg, procname):
    print "[!] Couldnt load/attach to %s" % procname
    
    sys.exit(-1)

dbg.debug_event_loop()
########NEW FILE########
__FILENAME__ = tracer_msr_branch
#!c:\python\python.exe

# $Id: tracer_msr_branch.py 194 2007-04-05 15:31:53Z cameron $

import sys

from pydbg import *
from pydbg.defines import *

USAGE = "USAGE: tracer_msr_branch.py <PID>"
error = lambda msg: sys.stderr.write("ERROR> " + msg + "\n") or sys.exit(1)
begin = 0
end   = 0

SysDbgReadMsr  = 16
SysDbgWriteMsr = 17

ULONG     = c_ulong
ULONGLONG = c_ulonglong

class SYSDBG_MSR(Structure):
    _fields_ = [
        ("Address", ULONG),
        ("Data",    ULONGLONG),
]

def read_msr():
    msr = SYSDBG_MSR()
    msr.Address = 0x1D9
    msr.Data = 0xFF

    status = windll.ntdll.NtSystemDebugControl(SysDbgReadMsr,
                                               byref(msr),
                                               sizeof(SYSDBG_MSR),
                                               byref(msr),
                                               sizeof(SYSDBG_MSR),
                                               0);
    print "ret code: %x" % status
    print "%08x.%s" % (msr.Address, dbg.to_binary(msr.Data, 8))

def write_msr():
    msr = SYSDBG_MSR()
    msr.Address = 0x1D9
    msr.Data = 2
    status = windll.ntdll.NtSystemDebugControl(SysDbgWriteMsr,
                                               byref(msr),
                                               sizeof(SYSDBG_MSR),
                                               0,
                                               0,
                                               0);

########################################################################################################################
def handler_breakpoint (dbg):
    global begin, end

    if not begin or not end:
        print "initial breakpoint hit at %08x: %s" % (dbg.exception_address, dbg.disasm(dbg.exception_address))
        print "putting all threads into single step mode"

        for module in dbg.iterate_modules():
            if module.szModule.lower().endswith(".exe"):
                begin = module.modBaseAddr
                end   = module.modBaseAddr + module.modBaseSize
                print "%s %08x -> %08x" % (module.szModule, begin, end)

        for tid in dbg.enumerate_threads():
            print "    % 4d -> setting single step" % tid
            handle = dbg.open_thread(tid)
            dbg.single_step(True, handle)
            write_msr()
            dbg.close_handle(handle)

    elif begin <= dbg.exception_address <= end:
        print "bp: %08x: %s" % (dbg.exception_address, dbg.disasm(dbg.exception_address))

    dbg.single_step(True)
    write_msr()
    return DBG_CONTINUE


########################################################################################################################
def handler_single_step (dbg):
    global begin, end

    disasm    = dbg.disasm(dbg.exception_address)
    ret_addr  = dbg.get_arg(0)
    in_module = False


    if begin <= dbg.exception_address <= end:
        print "ss: %08x: %s" % (dbg.exception_address, disasm)
        in_module = True

    # if the current instructon is 'sysenter', set a breakpoint at the return address to bypass it.
    if disasm == "sysenter":
        dbg.bp_set(ret_addr)

    # if the current instruction is outside the main module and the return instruction is not, set a breakpoint on it
    # and continue without single stepping.
    elif not in_module and begin <= ret_addr <= end and ret_addr != 0:
        dbg.bp_set(ret_addr)

    # otherwise, re-raise the single step flag and continue on.
    else:
        dbg.single_step(True)
        write_msr()

    return DBG_CONTINUE


########################################################################################################################
def handler_new_thread (dbg):
    dbg.single_step(True)
    write_msr()
    return DBG_CONTINUE


if len(sys.argv) != 2:
    error(USAGE)

try:
    pid = int(sys.argv[1])
except:
    error(USAGE)

dbg = pydbg()

dbg.set_callback(EXCEPTION_BREAKPOINT,      handler_breakpoint)
dbg.set_callback(EXCEPTION_SINGLE_STEP,     handler_single_step)
dbg.set_callback(CREATE_THREAD_DEBUG_EVENT, handler_new_thread)

dbg.attach(pid)
dbg.run()

########NEW FILE########
__FILENAME__ = tracer_single_step
#!c:\python\python.exe

# $Id: tracer_single_step.py 194 2007-04-05 15:31:53Z cameron $

import sys

from pydbg import *
from pydbg.defines import *

USAGE = "USAGE: tracer_single_step.py <PID>"
error = lambda msg: sys.stderr.write("ERROR> " + msg + "\n") or sys.exit(1)
begin = 0
end   = 0

########################################################################################################################
def handler_breakpoint (dbg):
    global begin, end

    if not begin or not end:
        print "initial breakpoint hit at %08x: %s" % (dbg.exception_address, dbg.disasm(dbg.exception_address))
        print "putting all threads into single step mode"

        for module in dbg.iterate_modules():
            if module.szModule.lower().endswith(".exe"):
                begin = module.modBaseAddr
                end   = module.modBaseAddr + module.modBaseSize
                print "%s %08x -> %08x" % (module.szModule, begin, end)

        for tid in dbg.enumerate_threads():
            print "    % 4d -> setting single step" % tid
            handle = dbg.open_thread(tid)
            dbg.single_step(True, handle)
            dbg.close_handle(handle)

    elif begin <= dbg.exception_address <= end:
        print "%08x: %s" % (dbg.exception_address, dbg.disasm(dbg.exception_address))

    dbg.single_step(True)
    return DBG_CONTINUE


########################################################################################################################
def handler_single_step (dbg):
    global begin, end

    disasm    = dbg.disasm(dbg.exception_address)
    ret_addr  = dbg.get_arg(0)
    in_module = False

    if begin <= dbg.exception_address <= end:
        print "%08x: %s" % (dbg.exception_address, disasm)
        in_module = True

    # if the current instructon is 'sysenter', set a breakpoint at the return address to bypass it.
    if disasm == "sysenter":
        dbg.bp_set(ret_addr)

    # if the current instruction is outside the main module and the return instruction is not, set a breakpoint on it
    # and continue without single stepping.
    elif not in_module and begin <= ret_addr <= end and ret_addr != 0:
        dbg.bp_set(ret_addr)

    # otherwise, re-raise the single step flag and continue on.
    else:
        dbg.single_step(True)

    return DBG_CONTINUE


########################################################################################################################
def handler_new_thread (dbg):
    dbg.single_step(True)
    return DBG_CONTINUE


if len(sys.argv) != 2:
    error(USAGE)

try:
    pid = int(sys.argv[1])
except:
    error(USAGE)

dbg = pydbg()

dbg.set_callback(EXCEPTION_BREAKPOINT,      handler_breakpoint)
dbg.set_callback(EXCEPTION_SINGLE_STEP,     handler_single_step)
dbg.set_callback(CREATE_THREAD_DEBUG_EVENT, handler_new_thread)

dbg.attach(pid)
dbg.run()

########NEW FILE########
__FILENAME__ = code_coverage
#
# Code Coverage
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: code_coverage.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

# we don't want to make mysql a mandatory module for the utils library.
try:    import MySQLdb
except: pass

import time
import zlib
import cPickle

class __code_coverage_struct__:
    eip         = 0x00000000
    tid         = 0
    num         = 0
    timestamp   = 0
    module      = ""
    base        = 0
    is_function = 0

    # registers and stack values.
    eax = ebx = ecx = edx = edi = esi = ebp = esp = esp_4 = esp_8 = esp_c = esp_10 = 0

    # register dereferences.
    eax_deref = ebx_deref = ecx_deref = edx_deref = edi_deref = esi_deref = ebp_deref = ""

    # stack dereferences.
    esp_deref = esp_4_deref = esp_8_deref = esp_c_deref = esp_10_deref = ""


class code_coverage:
    '''
    The purpose of this class is to provide an easy interface to keeping track of code coverage data. The Process
    Stalker utility for example relies on this class.

    @note: Contains hit list in self.hits.
    '''

    hits        = {}
    num         = 1
    heavy       = None
    mysql       = None
    main_module = "[MAIN]"

    ####################################################################################################################
    def __init__ (self, mysql=None, heavy=False):
        '''
        @type  heavy: Boolean
        @param heavy: (Optional, Def=False) Flag controlling whether or not to save context information at each point.
        '''

        self.hits        = {}
        self.num         = 1
        self.heavy       = heavy
        self.mysql       = mysql
        self.main_module = "[MAIN]"


    ####################################################################################################################
    def add (self, pydbg, is_function):
        '''
        Add the current context to the tracked code coverage.

        @type  pydbg:       PyDbg
        @param pydbg:       Debugger instance
        @type  is_function: Integer (bool 0/1)
        @param is_function: Flag whether or not the current hit occurred at the start of a function.

        @rtype:  code_coverage
        @return: self
        '''

        ccs = __code_coverage_struct__()

        # assume we hit inside the main module, unless we can find the specific module we hit in.
        module = self.main_module
        base   = 0

        # determine the module this hit occured in.
        mod32 = pydbg.addr_to_module(pydbg.context.Eip)

        if mod32:
            module = mod32.szModule.lower()
            base   = mod32.modBaseAddr

        ccs.eip         = pydbg.context.Eip
        ccs.tid         = pydbg.dbg.dwThreadId
        ccs.num         = self.num
        ccs.timestamp   = int(time.time())
        ccs.module      = module
        ccs.base        = base
        ccs.is_function = is_function

        context_list = pydbg.dump_context_list(stack_depth=4, print_dots=True)

        if self.heavy:
            ccs.eax    = pydbg.context.Eax
            ccs.ebx    = pydbg.context.Ebx
            ccs.ecx    = pydbg.context.Ecx
            ccs.edx    = pydbg.context.Edx
            ccs.edi    = pydbg.context.Edi
            ccs.esi    = pydbg.context.Esi
            ccs.ebp    = pydbg.context.Ebp
            ccs.esp    = pydbg.context.Esp
            ccs.esp_4  = context_list["esp+04"]["value"]
            ccs.esp_8  = context_list["esp+08"]["value"]
            ccs.esp_C  = context_list["esp+0c"]["value"]
            ccs.esp_10 = context_list["esp+10"]["value"]

            ccs.eax_deref    = context_list["eax"]
            ccs.ebx_deref    = context_list["ebx"]
            ccs.ecx_deref    = context_list["ecx"]
            ccs.edx_deref    = context_list["edx"]
            ccs.edi_deref    = context_list["edi"]
            ccs.esi_deref    = context_list["esi"]
            ccs.ebp_deref    = context_list["ebp"]
            ccs.esp_deref    = context_list["esp"]
            ccs.esp_4_deref  = context_list["esp+04"]["desc"]
            ccs.esp_8_deref  = context_list["esp+08"]["desc"]
            ccs.esp_c_deref  = context_list["esp+0c"]["desc"]
            ccs.esp_10_deref = context_list["esp+10"]["desc"]

        if not self.hits.has_key(ccs.eip):
            self.hits[ccs.eip] = []

        self.hits[ccs.eip].append(ccs)
        self.num += 1

        return self


    ####################################################################################################################
    def clear_mysql (self, target_id, tag_id):
        '''
        Removes all code coverage hits from target/tag id combination. Expects connection to database to already exist
        via self.mysql.

        @see: connect_mysql(), import_mysql(), export_mysql()

        @type  target_id: Integer
        @param target_id: Name of target currently monitoring code coverage of
        @type  tag_id:    Integer
        @param tag_id:    Name of this code coverage run

        @rtype:  code_coverage
        @return: self
        '''

        cursor = self.mysql.cursor()

        try:
            cursor.execute("DELETE FROM cc_hits WHERE target_id = '%d' AND tag_id = '%d'" % (target_id, tag_id))
        except MySQLdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            print sql
            print

        cursor.close()
        return self


    ####################################################################################################################
    def connect_mysql (self, host, user, passwd):
        '''
        Establish a connection to a MySQL server. This must be called prior to export_mysql() or import_mysql().
        Alternatively, you can connect manually and set the self.mysql member variable.

        @see: export_mysql(), import_mysql()

        @type  host:      String
        @param host:      MySQL hostname or ip address
        @type  user:      String
        @param user:      MySQL username
        @type  passwd:    String
        @param passwd:    MySQL password

        @rtype:  code_coverage
        @return: self
        '''

        self.mysql = MySQLdb.connect(host=host, user=user, passwd=passwd, db="paimei")

        return self


    ####################################################################################################################
    def export_file (self, file_name):
        '''
        Dump the entire object structure to disk.

        @see: import_file()

        @type  file_name:   String
        @param file_name:   File name to export to

        @rtype:             code_coverage
        @return:            self
        '''

        fh = open(file_name, "wb+")
        fh.write(zlib.compress(cPickle.dumps(self, protocol=2)))
        fh.close()

        return self


    ####################################################################################################################
    def export_mysql (self, target_id, tag_id):
        '''
        Export code coverage data to MySQL. Expects connection to database to already exist via self.mysql.

        @see: clear_mysql(), connect_mysql(), import_mysql()

        @type  target_id: Integer
        @param target_id: Name of target currently monitoring code coverage of
        @type  tag_id:    Integer
        @param tag_id:    Name of this code coverage run

        @rtype:  code_coverage
        @return: self
        '''

        cursor = self.mysql.cursor()

        for hits in self.hits.values():
            for ccs in hits:
                sql  = "INSERT INTO cc_hits"
                sql += " SET target_id    = '%d'," % target_id
                sql += "     tag_id       = '%d'," % tag_id
                sql += "     num          = '%d'," % ccs.num
                sql += "     timestamp    = '%d'," % ccs.timestamp
                sql += "     eip          = '%d'," % ccs.eip
                sql += "     tid          = '%d'," % ccs.tid
                sql += "     eax          = '%d'," % ccs.eax
                sql += "     ebx          = '%d'," % ccs.ebx
                sql += "     ecx          = '%d'," % ccs.ecx
                sql += "     edx          = '%d'," % ccs.edx
                sql += "     edi          = '%d'," % ccs.edi
                sql += "     esi          = '%d'," % ccs.esi
                sql += "     ebp          = '%d'," % ccs.ebp
                sql += "     esp          = '%d'," % ccs.esp
                sql += "     esp_4        = '%d'," % ccs.esp_4
                sql += "     esp_8        = '%d'," % ccs.esp_8
                sql += "     esp_c        = '%d'," % ccs.esp_c
                sql += "     esp_10       = '%d'," % ccs.esp_10
                sql += "     eax_deref    = '%s'," % ccs.eax_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     ebx_deref    = '%s'," % ccs.ebx_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     ecx_deref    = '%s'," % ccs.ecx_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     edx_deref    = '%s'," % ccs.edx_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     edi_deref    = '%s'," % ccs.edi_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     esi_deref    = '%s'," % ccs.esi_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     ebp_deref    = '%s'," % ccs.ebp_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     esp_deref    = '%s'," % ccs.esp_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     esp_4_deref  = '%s'," % ccs.esp_4_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     esp_8_deref  = '%s'," % ccs.esp_8_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     esp_c_deref  = '%s'," % ccs.esp_c_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     esp_10_deref = '%s'," % ccs.esp_10_deref.replace("\\", "\\\\").replace("'", "\\'")
                sql += "     is_function  = '%d'," % ccs.is_function
                sql += "     module       = '%s'," % ccs.module
                sql += "     base         = '%d' " % ccs.base

                try:
                    cursor.execute(sql)
                except MySQLdb.Error, e:
                    print "Error %d: %s" % (e.args[0], e.args[1])
                    print sql
                    print

        cursor.close()
        return self


    ####################################################################################################################
    def import_file (self, file_name):
        '''
        Load the entire object structure from disk.

        @see: export_file()

        @type  file_name:   String
        @param file_name:   File name to import from

        @rtype:             code_coverage
        @return:            self
        '''

        fh  = open(file_name, "rb")
        tmp = cPickle.loads(zlib.decompress(fh.read()))
        fh.close()

        self.hits        = tmp.hits
        self.num         = tmp.num
        self.heavy       = tmp.heavy
        self.mysql       = tmp.mysql
        self.main_module = tmp.main_module

        return self


    ####################################################################################################################
    def import_mysql (self, target_id, tag_id):
        '''
        Import code coverage from MySQL. Expects connection to database to already exist via self.mysql.

        @see: clear_mysql(), connect_mysql(), export_mysql()

        @type  target_id: Integer
        @param target_id: Name of target currently monitoring code coverage of
        @type  tag_id:    Integer
        @param tag_id:    Name of this code coverage run

        @rtype:  code_coverage
        @return: self
        '''

        self.reset()

        hits = self.mysql.cursor(MySQLdb.cursors.DictCursor)
        hits.execute("SELECT * FROM cc_hits WHERE target_id='%d' AND tag_id='%d'" % (target_id, tag_id))

        for hit in hits.fetchall():
            ccs = __code_coverage_struct__()

            ccs.eip         = hit["eip"]
            ccs.tid         = hit["tid"]
            ccs.num         = hit["num"]
            ccs.timestamp   = hit["timestamp"]
            ccs.module      = hit["module"]
            ccs.base        = hit["base"]
            ccs.is_function = hit["is_function"]

            if self.heavy:
                ccs.eax    = hit["eax"]
                ccs.ebx    = hit["ebx"]
                ccs.ecx    = hit["ecx"]
                ccs.edx    = hit["edx"]
                ccs.edi    = hit["edi"]
                ccs.esi    = hit["esi"]
                ccs.ebp    = hit["ebp"]
                ccs.esp    = hit["esp"]
                ccs.esp_4  = hit["esp_4"]
                ccs.esp_8  = hit["esp_8"]
                ccs.esp_C  = hit["esp_c"]
                ccs.esp_10 = hit["esp_10"]

                ccs.eax_deref    = hit["eax_deref"]
                ccs.ebx_deref    = hit["ebx_deref"]
                ccs.ecx_deref    = hit["ecx_deref"]
                ccs.edx_deref    = hit["edx_deref"]
                ccs.edi_deref    = hit["edi_deref"]
                ccs.esi_deref    = hit["esi_deref"]
                ccs.ebp_deref    = hit["ebp_deref"]
                ccs.esp_deref    = hit["esp_deref"]
                ccs.esp_4_deref  = hit["esp_4_deref"]
                ccs.esp_8_deref  = hit["esp_8_deref"]
                ccs.esp_C_deref  = hit["esp_c_deref"]
                ccs.esp_10_deref = hit["esp_10_deref"]

            if not self.hits.has_key(ccs.eip):
                self.hits[ccs.eip] = []

            self.hits[ccs.eip].append(ccs)
            self.num += 1

        hits.close()
        return self


    ####################################################################################################################
    def reset (self):
        '''
        Reset the internal counter and hit list dictionary.

        @rtype:  code_coverage
        @return: self
        '''

        self.hits = {}
        self.num  = 1

########NEW FILE########
__FILENAME__ = crash_binning
#
# Crash Binning
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: crash_binning.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import sys
import zlib
import cPickle

class __crash_bin_struct__:
    exception_module    = None
    exception_address   = 0
    write_violation     = 0
    violation_address   = 0
    violation_thread_id = 0
    context             = None
    context_dump        = None
    disasm              = None
    disasm_around       = []
    stack_unwind        = []
    seh_unwind          = []
    extra               = None


class crash_binning:
    '''
    @todo: Add MySQL import/export.
    '''

    bins       = {}
    last_crash = None
    pydbg      = None

    ####################################################################################################################
    def __init__ (self):
        '''
        '''

        self.bins       = {}
        self.last_crash = None
        self.pydbg      = None


    ####################################################################################################################
    def record_crash (self, pydbg, extra=None):
        '''
        Given a PyDbg instantiation that at the current time is assumed to have "crashed" (access violation for example)
        record various details such as the disassemly around the violating address, the ID of the offending thread, the
        call stack and the SEH unwind. Store the recorded data in an internal dictionary, binning them by the exception
        address.

        @type  pydbg: pydbg
        @param pydbg: Instance of pydbg
        @type  extra: Mixed
        @param extra: (Optional, Def=None) Whatever extra data you want to store with this bin
        '''

        self.pydbg = pydbg
        crash = __crash_bin_struct__()

        # add module name to the exception address.
        exception_module = pydbg.addr_to_module(pydbg.dbg.u.Exception.ExceptionRecord.ExceptionAddress)

        if exception_module:
            exception_module = exception_module.szModule
        else:
            exception_module = "[INVALID]"

        crash.exception_module    = exception_module
        crash.exception_address   = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionAddress
        crash.write_violation     = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionInformation[0]
        crash.violation_address   = pydbg.dbg.u.Exception.ExceptionRecord.ExceptionInformation[1]
        crash.violation_thread_id = pydbg.dbg.dwThreadId
        crash.context             = pydbg.context
        crash.context_dump        = pydbg.dump_context(pydbg.context, print_dots=False)
        crash.disasm              = pydbg.disasm(crash.exception_address)
        crash.disasm_around       = pydbg.disasm_around(crash.exception_address, 10)
        crash.stack_unwind        = pydbg.stack_unwind()
        crash.seh_unwind          = pydbg.seh_unwind()
        crash.extra               = extra

        # add module names to the stack unwind.
        for i in xrange(len(crash.stack_unwind)):
            addr   = crash.stack_unwind[i]
            module = pydbg.addr_to_module(addr)

            if module:
                module = module.szModule
            else:
                module = "[INVALID]"

            crash.stack_unwind[i] = "%s:%08x" % (module, addr)


        # add module names to the SEH unwind.
        for i in xrange(len(crash.seh_unwind)):
            (addr, handler) = crash.seh_unwind[i]

            module = pydbg.addr_to_module(handler)

            if module:
                module = module.szModule
            else:
                module = "[INVALID]"

            crash.seh_unwind[i] = (addr, handler, "%s:%08x" % (module, handler))

        if not self.bins.has_key(crash.exception_address):
            self.bins[crash.exception_address] = []

        self.bins[crash.exception_address].append(crash)
        self.last_crash = crash


    ####################################################################################################################
    def crash_synopsis (self, crash=None):
        '''
        For the supplied crash, generate and return a report containing the disassemly around the violating address,
        the ID of the offending thread, the call stack and the SEH unwind. If not crash is specified, then call through
        to last_crash_synopsis() which returns the same information for the last recorded crash.

        @see: crash_synopsis()

        @type  crash: __crash_bin_struct__
        @param crash: (Optional, def=None) Crash object to generate report on

        @rtype:  String
        @return: Crash report
        '''

        if not crash:
            return self.last_crash_synopsis()

        if crash.write_violation:
            direction = "write to"
        else:
            direction = "read from"

        synopsis = "%s:%08x %s from thread %d caused access violation\nwhen attempting to %s 0x%08x\n\n" % \
            (
                crash.exception_module,       \
                crash.exception_address,      \
                crash.disasm,                 \
                crash.violation_thread_id,    \
                direction,                    \
                crash.violation_address       \
            )

        synopsis += crash.context_dump

        synopsis += "\ndisasm around:\n"
        for (ea, inst) in crash.disasm_around:
            synopsis += "\t0x%08x %s\n" % (ea, inst)

        if len(crash.stack_unwind):
            synopsis += "\nstack unwind:\n"
            for entry in crash.stack_unwind:
                synopsis += "\t%s\n" % entry

        if len(crash.seh_unwind):
            synopsis += "\nSEH unwind:\n"
            for (addr, handler, handler_str) in crash.seh_unwind:
                synopsis +=  "\t%08x -> %s\n" % (addr, handler_str)

        return synopsis + "\n"


    ####################################################################################################################
    def export_file (self, file_name):
        '''
        Dump the entire object structure to disk.

        @see: import_file()

        @type  file_name:   String
        @param file_name:   File name to export to

        @rtype:             crash_binning
        @return:            self
        '''

        # null out what we don't serialize but save copies to restore after dumping to disk.
        last_crash = self.last_crash
        pydbg      = self.pydbg

        self.last_crash = self.pydbg = None

        fh = open(file_name, "wb+")
        fh.write(zlib.compress(cPickle.dumps(self, protocol=2)))
        fh.close()

        self.last_crash = last_crash
        self.pydbg      = pydbg

        return self


    ####################################################################################################################
    def import_file (self, file_name):
        '''
        Load the entire object structure from disk.

        @see: export_file()

        @type  file_name:   String
        @param file_name:   File name to import from

        @rtype:             crash_binning
        @return:            self
        '''

        fh  = open(file_name, "rb")
        tmp = cPickle.loads(zlib.decompress(fh.read()))
        fh.close()

        self.bins = tmp.bins

        return self


    ####################################################################################################################
    def last_crash_synopsis (self):
        '''
        For the last recorded crash, generate and return a report containing the disassemly around the violating
        address, the ID of the offending thread, the call stack and the SEH unwind.

        @see: crash_synopsis()

        @rtype:  String
        @return: Crash report
        '''

        if self.last_crash.write_violation:
            direction = "write to"
        else:
            direction = "read from"

        synopsis = "%s:%08x %s from thread %d caused access violation\nwhen attempting to %s 0x%08x\n\n" % \
            (
                self.last_crash.exception_module,       \
                self.last_crash.exception_address,      \
                self.last_crash.disasm,                 \
                self.last_crash.violation_thread_id,    \
                direction,                              \
                self.last_crash.violation_address       \
            )

        synopsis += self.last_crash.context_dump

        synopsis += "\ndisasm around:\n"
        for (ea, inst) in self.last_crash.disasm_around:
            synopsis += "\t0x%08x %s\n" % (ea, inst)

        if len(self.last_crash.stack_unwind):
            synopsis += "\nstack unwind:\n"
            for entry in self.last_crash.stack_unwind:
                synopsis += "\t%s\n" % entry

        if len(self.last_crash.seh_unwind):
            synopsis += "\nSEH unwind:\n"
            for (addr, handler, handler_str) in self.last_crash.seh_unwind:
                try:
                    disasm = self.pydbg.disasm(handler)
                except:
                    disasm = "[INVALID]"

                synopsis +=  "\t%08x -> %s %s\n" % (addr, handler_str, disasm)

        return synopsis + "\n"
########NEW FILE########
__FILENAME__ = hooking
#
# API Hooking Abstraction Helper
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: hooking.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

from pydbg.defines import *

########################################################################################################################
class hook_container:
    '''
    The purpose of this class is to provide an easy interface for hooking the entry and return points of arbitrary
    API calls. The hooking of one or both of the points is optional. Example usage::

        def CreateFileA_on_entry (dbg, args):
            pass

        def CreateFileA_on_return (dbg, args, return_value):
            pass

        h = hooks(dbg)
        h.add(dbg.func_resolve("kernel32", "CreateFileA"), 7, CreateFileA_on_entry, CreateFileA_on_exit)

    This class transparently takes care of various thread-related race conditions.
    '''

    hooks = {}

    ####################################################################################################################
    def __init__ (self):
        self.hooks = {}


    ####################################################################################################################
    def add (self, pydbg, address, num_args, entry_hook=None, exit_hook=None):
        '''
        Add a new hook on the specified API which accepts the specified number of arguments. Optionally specify callback
        functions for hooked API entry / exit events. The entry / exit callback prototypes are::

            entry(dbg, args)

        Where entry receives the active PyDbg instance as well as a list of the arguments passed to the hooked routine::

            exit (dbg, args, return_value)

        Where exit received the active PyDbg instance, a list of the arguments passed to the hooked routine and the
        return value from the hooked routine.

        @type  pydbg:      PyDbg Instance
        @param pydbg:      PyDbg Instance
        @type  address:    Long
        @param address:    Address of function to hook
        @type  num_args:   Integer
        @param num_args:   (Optional, Def=0) Number of arguments in function to hook
        @type  entry_hook: Function Pointer
        @param entry_hook: (Optional, Def=None) Function to call on hooked API entry
        @type  exit_hook:  Function Pointer
        @param exit_hook:  (Optional, Def=None) Function to call on hooked API exit

        @rtype:  hooks
        @return: Self
        '''

        # ensure a hook doesn't already exist at the requested address.
        if address in self.hooks.keys():
            return

        # create a new hook instance and activate it.
        h = hook(address, num_args, entry_hook, exit_hook)
        h.hook(pydbg)

        # save the newly created hook into the internal dictionary.
        self.hooks[address] = h

        return self


    ####################################################################################################################
    def remove (self, pydbg, address):
        '''
        De-activate and remove the hook from the specified API address.

        @type  pydbg:   PyDbg Instance
        @param pydbg:   PyDbg Instance
        @type  address: Long
        @param address: Address of function to remove hook from

        @rtype:  hooks
        @return: Self
        '''

        # ensure the address maps to a valid hook point.
        if address not in self.hooks.keys():
            return

        # de-activate the hook.
        self.hooks[address].unhook(pydbg)

        # remove the hook from the internal dictionary.
        del(self.hooks[address])

        return self


    ####################################################################################################################
    def iterate (self, address):
        '''
        A simple iterator function that can be used to iterate through all hooks. Yielded objects are of type hook().

        @rtype:  hook
        @return: Iterated hook entries.
        '''

        for hook in self.hooks.values():
            yield hook


########################################################################################################################
class hook:
    '''
    This helper class abstracts the activation/deactivation of individual hooks. The class is responsible for
    maintaining the various state variables requires to prevent race conditions.
    '''

    hooks      = None
    address    = 0
    num_args   = 0
    entry_hook = None
    exit_hook  = None
    arguments  = {}
    exit_bps   = {}

    ####################################################################################################################
    def __init__ (self, address, num_args, entry_hook=None, exit_hook=None):
        '''
        Initialize the object with the specified parameters.

        @type  address:    Long
        @param address:    Address of function to hook
        @type  num_args:   Integer
        @param num_args:   (Optional, Def=0) Number of arguments in function to hook
        @type  entry_hook: Function Pointer
        @param entry_hook: (Optional, def=None) Function to call on hooked API entry
        @type  exit_hook:  Function Pointer
        @param exit_hook:  (Optional, def=None) Function to call on hooked API exit
        '''

        self.address    = address
        self.num_args   = num_args
        self.entry_hook = entry_hook
        self.exit_hook  = exit_hook
        self.arguments  = {}
        self.exit_bps   = {}


    ####################################################################################################################
    def hook (self, pydbg):
        '''
        Activate the hook by setting a breakpoint on the previously specified address. Breakpoint callbacks are proxied
        through an internal routine that determines and passes further needed information such as function arguments
        and return value.

        @type  pydbg: PyDbg Instance
        @param pydbg: PyDbg Instance
        '''

        pydbg.bp_set(self.address, restore=True, handler=self.__proxy_on_entry)


    ####################################################################################################################
    def unhook (self, pydbg):
        '''
        De-activate the hook by by removing the breakpoint on the previously specified address.

        @type  pydbg: PyDbg Instance
        @param pydbg: PyDbg Instance
        '''

        pydbg.bp_del(self.address)

        # ensure no breakpoints exist on any registered return addresses.
        for address in self.exit_bps.keys():
            pydbg.bp_del(address)


    ####################################################################################################################
    def __proxy_on_entry (self, pydbg):
        '''
        The breakpoint handler callback is proxied through this routine for the purpose of passing additional needed
        information to the user specified hook_{entry,exit} callback. This routine also allows provides a default
        return value of DBG_CONTINUE in the event that the user specified hook callback does not return a value. This
        allows for further abstraction between hooking and the debugger.

        @type  pydbg: PyDbg
        @param pydbg: Debugger instance

        @rtype:  DWORD
        @return: Debugger continue status
        '''

        continue_status = None

        # retrieve and store the arguments to the hooked function.
        # we categorize arguments by thread id to avoid an entry / exit matching race condition, example:
        #     - thread one enters API, saves arguments
        #     - thread two enters API, overwrites arguments
        #     - thread one exists API and uses arguments from thread two
        tid = pydbg.dbg.dwThreadId
        self.arguments[tid] = []

        for i in xrange(1, self.num_args + 1):
            self.arguments[tid].append(pydbg.get_arg(i))

        # if an entry point callback was specified, call it and grab the return value.
        if self.entry_hook:
            continue_status = self.entry_hook(pydbg, self.arguments[tid])

        # if an exit hook callback was specified, determine the function exit.
        if self.exit_hook:
            function_exit = pydbg.get_arg(0)

            # set a breakpoint on the function exit.
            pydbg.bp_set(function_exit, restore=True, handler=self.__proxy_on_exit)

            # increment the break count for the exit bp.
            # we track the number of breakpoints set on the exit point to avoid a hook exit race condition, ie:
            #     - thread one enters API sets BP on exit point
            #     - thread two enters API sets BP on exit point
            #     - thread one exits API and removes BP from exit point
            #     - thread two misses exit BP
            self.exit_bps[function_exit] = self.exit_bps.get(function_exit, 0) + 1

        # if a return value was not explicitly specified, default to DBG_CONTINUE.
        if continue_status == None:
            continue_status = DBG_CONTINUE

        return continue_status


    ####################################################################################################################
    def __proxy_on_exit (self, pydbg):
        '''
        The breakpoint handler callback is proxied through this routine for the purpose of passing additional needed
        information to the user specified hook_{entry,exit} callback. This routine also allows provides a default
        return value of DBG_CONTINUE in the event that the user specified hook callback does not return a value. This
        allows for further abstraction between hooking and the debugger.

        @type  pydbg:       PyDbg
        @param pydbg:       Debugger instance

        @rtype:  DWORD
        @return: Debugger continue status
        '''

        # if we are in this function, then an exit point callback was specified, call it and grab the return value.
        if pydbg.dbg.dwThreadId not in self.arguments.keys():
            return

        continue_status = self.exit_hook(pydbg, self.arguments[pydbg.dbg.dwThreadId], pydbg.context.Eax)

        # reduce the break count
        self.exit_bps[pydbg.context.Eip] -= 1

        # if the break count is 0, remove the bp from the exit point.
        if self.exit_bps[pydbg.context.Eip] == 0:
            pydbg.bp_del(pydbg.context.Eip)

        # if a return value was not explicitly specified, default to DBG_CONTINUE.
        if continue_status == None:
            continue_status = DBG_CONTINUE

        return continue_status

########NEW FILE########
__FILENAME__ = injection
#
# DLL Injection/Ejection Helper
# Copyright (C) 2007 Justin Seitz <jms@bughunter.ca>
#
# $Id: injection.py 238 2010-04-05 20:40:46Z rgovostes $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Justin Seitz
@license:      GNU General Public License 2.0 or later
@contact:      jms@bughunter.ca
@organization: www.openrce.org
'''

import os.path

from pydbg           import *
from pydbg.defines   import *
from pydbg.my_ctypes import *

# macos compatability.
try:
    kernel32 = windll.kernel32
except:
    kernel32 = CDLL(os.path.join(os.path.dirname(__file__), "libmacdll.dylib"))

########################################################################################################################
class inject:
    '''
    This class abstracts the ability to inject and eject a DLL into a remote process.
    '''

    ####################################################################################################################
    def __init__ (self):
        pass

    ####################################################################################################################
    def inject_dll (self, dll_path, pid):
        '''
        Inject a DLL of your choice into a running process.

        @type    dll_name: String
        @param   dll_name: The path to the DLL you wish to inject
        @type    pid:      Integer
        @param   pid:      The process ID that you wish to inject into

        @raise pdx: An exception is raised on failure.
        '''

        dll_len = len(dll_path)

        # get a handle to the process we are injecting into.
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)

        # now we have to allocate enough bytes for the name and path of our DLL.
        arg_address = kernel32.VirtualAllocEx(h_process, 0, dll_len, VIRTUAL_MEM, PAGE_READWRITE)

        # Write the path of the DLL into the previously allocated space. The pointer returned
        written = c_int(0)
        kernel32.WriteProcessMemory(h_process, arg_address, dll_path, dll_len, byref(written))

        # resolve the address of LoadLibraryA()
        h_kernel32 = kernel32.GetModuleHandleA("kernel32.dll")
        h_loadlib  = kernel32.GetProcAddress(h_kernel32, "LoadLibraryA")

        # wow we try to create the remote thread.
        thread_id = c_ulong(0)
        if not kernel32.CreateRemoteThread(h_process, None, 0, h_loadlib, arg_address, 0, byref(thread_id)):
            # free the opened handles.
            kernel32.CloseHandle(h_process)
            kernel32.CloseHandle(h_kernel32)

            raise pdx("CreateRemoteThread failed, unable to inject the DLL %s into PID: %d." % (dll_path, pid), True)

        # free the opened handles.
        kernel32.CloseHandle(h_process)
        kernel32.CloseHandle(h_kernel32)


    ####################################################################################################################
    def eject_dll (self, dll_name, pid):
        '''
        Eject a loaded DLL from a running process.

        @type    dll_name: String
        @param   dll_name: The name of the DLL you wish to eject
        @type    pid:      Integer
        @param   pid:      The process ID that you want to eject a DLL from

        @raise pdx: An exception is raised on failure.
        '''

        # find the DLL and retrieve its information.
        ejectee = self.get_module_info(dll_name, pid)

        if ejectee == False:
            raise pdx("Couldn't eject DLL %s from PID: %d" % (dll_name, pid))

        # open the process.
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)

        # resolve the address of FreeLibrary()
        h_kernel32 = kernel32.GetModuleHandleA("kernel32.dll")
        h_freelib  = kernel32.GetProcAddress(h_kernel32, "FreeLibrary")

        # now we try to create the remote thread hopefully freeing that DLL, the reason we loop is that
        # FreeLibrary() merely decrements the reference count of the DLL we are freeing. Once the ref count
        # hits 0 it will unmap the DLL from memory
        count = 0
        while count <= ejectee.GlblcntUsage:
            thread_id = c_ulong()
            if not kernel32.CreateRemoteThread(h_process, None, 0, h_freelib, ejectee.hModule, 0, byref(thread_id)):
                # free the opened handles.
                kernel32.CloseHandle(h_process)
                kernel32.CloseHandle(h_kernel32)

                raise pdx("CreateRemoteThread failed, couldn't run FreeLibrary()", True)

            count += 1

        # free the opened handles.
        kernel32.CloseHandle(h_process)
        kernel32.CloseHandle(h_kernel32)


    ##############################################################################
    def get_module_info (self, dll_name, pid):
        '''
        Helper function to retrieve the necessary information for the DLL we wish to eject.

        @type    dll_name: String
        @param   dll_name: The name of the DLL you wish to eject
        @type    pid:      Integer
        @param   pid:      The process ID that you want to eject a DLL from

        @raise pdx: An exception is raised on failure.
        '''

        # we create a snapshot of the current process, this let's us dig out all kinds of useful information, including
        # DLL info. We are really after the reference count so that we can decrement it enough to get rid of the DLL we
        # want unmapped
        current_process = MODULEENTRY32()
        h_snap          = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE,pid)

        # check for a failure to create a valid snapshot
        if h_snap == INVALID_HANDLE_VALUE:
            raise pdx("CreateToolHelp32Snapshot() failed.", True)

        # we have to initiliaze the size of the MODULEENTRY32 struct or this will all fail
        current_process.dwSize = sizeof(current_process)

        # check to make sure we have a valid list
        if not kernel32.Module32First(h_snap, byref(current_process)):
            kernel32.CloseHandle(h_snap)
            raise pdx("Couldn't find a valid reference to the module %s" % dll_name, True)

        # keep looking through the loaded modules to try to find the one specified for ejection.
        while current_process.szModule.lower() != dll_name.lower():
            if not kernel32.Module32Next(h_snap, byref(current_process)):
                kernel32.CloseHandle(h_snap)
                raise pdx("Couldn't find the DLL %s" % dll_name, True)

        # close the handle to the snapshot.
        kernel32.CloseHandle(h_snap)

        # return the MODULEENTRY32 structure of our DLL.
        return current_process

########NEW FILE########
__FILENAME__ = process_stalker
#
# Process Stalker
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: process_stalker.py 194 2007-04-05 15:31:53Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import thread
import sys

sys.path.append("..")

import code_coverage
import crash_binning
import pida

from pydbg import *
from pydbg.defines import *

# wx is not required for this module.
try:    import wx
except: pass

class process_stalker:
    '''
    This class was created to provide portable and re-usable Process Stalker functionality. Currently it is only being
    used by the pstalker PAIMEIconsole module.

    @todo: This utility has really only been used in the pstalker PAIMEIconsole module, it needs to be tested to ensure
           that it can be utilized standalone.
    '''

    FUNCTIONS    = 0
    BASIC_BLOCKS = 1

    attach              = 0
    load                = None
    args                = None
    cc                  = code_coverage.code_coverage()
    depth               = None
    detach              = False
    filter_list         = []
    filtered            = {}
    heavy               = False
    ignore_first_chance = True
    log                 = lambda x: None
    main                = None
    mysql               = None
    pida_modules        = None
    pydbg               = None
    restore             = False
    tag_id              = None
    target_id           = None

    ####################################################################################################################
    def __init__ (self, depth, filter_list, log, main, mysql, pida_modules, pydbg, tag_id, target_id, print_bps=True, \
                        attach=0, load=None, args=None, heavy=False, ignore_first_chance=True, restore=False):
        '''
        Initialize the process stalker object, not all arguments are required.

        @type  depth:               Integer (self.FUNCTIONS=0 or self.BASIC_BLOCKS=1)
        @param depth:               0 for function level stalking, 1 for basic block level stalking
        @type  filter_list:         List
        @param filter_list:         List of (target id, tag id) tuples to filter from stalking
        @type  log:                 Function Pointer
        @param log:                 Pointer to log routine that takes a single parameter, the log message
        @type  main:                String
        @param main:                Name of the main module
        @type  mysql:               MySQLdb Connection
        @param mysql:               Connection to MySQL server
        @type  pida_modules:        Dictionary
        @param pida_modules:        Dictionary of loaded PIDA modules, keyed by module name
        @type  pydbg:               PyDbg
        @param pydbg:               PyDbg instance
        @type  tag_id:              Integer
        @param tag_id:              ID of tag we are storing hits in
        @type  target_id:           Integer
        @param target_id:           ID ot target that contains the tag we are storing hits in
        @type  print_bps:           Boolean
        @param print_bps:           (Optional, def=False) Controls whether or not to log individual breakpoint hits
        @type  attach:              Integer
        @param attach:              (Optional, def=0) Process ID of target to attach to
        @type  load:                String
        @param load:                (Optional, def=None) Command line to executable when loading target
        @type  args:                String
        @param args:                (Optional, def=None) Optional command line arguments to use when loading target
        @type  heavy:               Boolean
        @param heavy:               (Optional, def=False) Controls whether or not context data is recorded
        @type  ignore_first_chance: Boolean
        @param ignore_first_chance: (Optional, def=True) Controls reporting of first chance exceptions
        @type  restore:             Boolean
        @param restore:             (Optional, def=False) Controls whether or not to restore hit breakpoints
        '''

        self.attach              = attach
        self.load                = load
        self.args                = args
        self.cc                  = code_coverage.code_coverage()
        self.depth               = depth
        self.filter_list         = filter_list
        self.filtered            = {}
        self.heavy               = heavy
        self.ignore_first_chance = ignore_first_chance
        self.log                 = log
        self.main                = main
        self.mysql               = mysql
        self.pida_modules        = pida_modules
        self.pydbg               = pydbg
        self.print_bps           = print_bps
        self.restore             = restore
        self.tag_id              = tag_id
        self.target_id           = target_id


    ####################################################################################################################
    def export_mysql (self):
        '''
        Export all the recorded hits to the database.
        '''

        if self.cc.num > 1:
            self.log("Exporting %d hits to MySQL." % (self.cc.num - 1))
            self.cc.mysql = self.mysql
            self.cc.export_mysql(self.target_id, self.tag_id)
            self.cc.reset()


    ####################################################################################################################
    def handler_access_violation (self, dbg):
        '''
        If the shit hits the fan, we want to know about it.
        '''

        # if the user wants to ignore first chance exceptions then do so.
        if self.ignore_first_chance and dbg.dbg.u.Exception.dwFirstChance:
            return DBG_EXCEPTION_NOT_HANDLED

        crash_bin = crash_binning.crash_binning()
        crash_bin.record_crash(dbg)

        self.log(crash_bin.crash_synopsis())
        dbg.terminate_process()
        self.export_mysql()


    ####################################################################################################################
    def handler_breakpoint (self, dbg):
        '''
        The breakpoint handler is of course responsible for logging the code coverage.
        '''

        if dbg.get_attr("first_breakpoint"):
            return DBG_CONTINUE

        if self.print_bps:
            self.log("debugger hit %08x cc #%d" % (dbg.exception_address, self.cc.num))

        is_function = 0
        for module in self.pida_modules.values():
            if module.nodes.has_key(dbg.context.Eip):
                is_function = 1
                break

        self.cc.add(dbg, is_function)

        return DBG_CONTINUE


    ####################################################################################################################
    def handler_load_dll (self, dbg):
        '''
        Generate debug messages on DLL loads and keep track of the last loaded DLL.
        '''

        last_dll = dbg.get_system_dll(-1)
        self.log("Loading 0x%08x %s" % (last_dll.base, last_dll.path))

        self.set_bps(last_dll.name.lower(), last_dll)

        return DBG_CONTINUE


    ####################################################################################################################
    def handler_user_callback (self, dbg):
        '''
        This is my elegant solution to avoiding having to thread out the stalk routine.
        '''

        # wx is not required for this module.
        try:    wx.Yield()
        except: pass

        if self.detach:
            # reset the flag and push data to mysql before we try to detach, in case detaching fails.
            self.detach = False

            self.export_mysql()
            dbg.detach()


    ####################################################################################################################
    def set_bps (self, module, last_dll=None):
        '''
        Set breakpoints in the specified module.

        @type  module:   String
        @param module:   Name of module (exe or dll) to set breakpoints in
        @type  last_dll: PyDbg System DLL Object
        @param last_dll: (Optional, def=None) System DLL instance, required for setting breakpoints in a DLL.
        '''

        if module in self.pida_modules.keys():
            # if we are setting breakpoints in a DLL.
            if last_dll:
                # if a signature is available, ensure we have a match before we start setting breakpoints in the loaded DLL.
                if self.pida_modules[module].signature:
                    if self.pida_modules[module].signature != pida.signature(last_dll.path):
                        self.log("Signature match failed, ignoring DLL")
                        return

                # ensure the pida module is at the appropriate base address.
                self.pida_modules[module].rebase(last_dll.base)

            # otherwise we are setting breakpoints in the main module. determine the base address of the main module
            # and rebase if necessary.
            else:
                for mod32 in self.pydbg.iterate_modules():
                    if mod32.szModule.lower() == module.lower():
                        self.pida_modules[module].rebase(mod32.modBaseAddr)

            #
            # function level tracking.
            #

            if self.depth == self.FUNCTIONS:
                functions = []

                for f in self.pida_modules[module].nodes.values():
                    if f.is_import:
                        continue

                    if self.filtered.has_key(module):
                        if self.filtered[module].count(f.ea_start - self.pida_modules[module].base):
                            continue

                    functions.append(f.ea_start)

                if last_dll: self.log("Setting %d breakpoints on functions in %s" % (len(functions), last_dll.name))
                else:        self.log("Setting %d breakpoints on functions in main module" % len(functions))

                self.pydbg.bp_set(functions, restore=self.restore)

            #
            # basic block level tracking.
            #

            elif self.depth == self.BASIC_BLOCKS:
                basic_blocks = []

                for f in self.pida_modules[module].nodes.values():
                    for bb in f.nodes.values():
                        if self.filtered.has_key(module):
                            if self.filtered[module].count(bb.ea_start - self.pida_modules[module].base):
                                continue

                        basic_blocks.append(bb.ea_start)

                if last_dll: self.log("Setting %d breakpoints on basic blocks in %s" % (len(basic_blocks), last_dll.name))
                else:        self.log("Setting %d breakpoints on basic blocks in main module" % len(basic_blocks))

                self.pydbg.bp_set(basic_blocks, restore=self.restore)


    ####################################################################################################################
    def stalk (self):
        '''
        This is the main routine of the process stalker utility class. Once all the required member variables are set
        you call this routine to get the ball rolling and start stalking.

        @todo: Add sanity checking to ensure all required member variables are set.
        '''

        self.pydbg.set_callback(EXCEPTION_BREAKPOINT,       self.handler_breakpoint)
        self.pydbg.set_callback(LOAD_DLL_DEBUG_EVENT,       self.handler_load_dll)
        self.pydbg.set_callback(EXCEPTION_ACCESS_VIOLATION, self.handler_access_violation)
        self.pydbg.set_callback(USER_CALLBACK_DEBUG_EVENT,  self.handler_user_callback)

        # set the main module name for the code coverage class.
        self.cc.main_module = self.main

        # retrieve the entries to filter from the filter list.
        for (target_id, tag_id) in self.filter_list:
            cc = code_coverage.code_coverage()
            cc.mysql = self.mysql

            cc.import_mysql(target_id, tag_id)

            self.log("Filtering %d points from target id:%d tag id:%d" % (cc.num, target_id, tag_id))

            for hit_list in cc.hits.values():
                for hit in hit_list:
                    if not self.filtered.has_key(hit.module):
                        self.filtered[hit.module] = []

                    if not self.filtered[hit.module].count(hit.eip - hit.base):
                        self.filtered[hit.module].append(hit.eip - hit.base)

        self.cc.heavy = self.heavy

        try:
            if self.load:
                self.pydbg.load(self.load, self.args)
            else:
                self.pydbg.attach(self.attach)
        except pdx, x:
            self.log(x.__str__())
            return

        self.set_bps(self.main)

        try:
            self.pydbg.run()
        except pdx, x:
            self.log(x.__str__())

        self.export_mysql()
########NEW FILE########
__FILENAME__ = udraw_connector
#
# uDraw Connector
# Copyright (C) 2006 Pedram Amini <pedram.amini@gmail.com>
#
# $Id: udraw_connector.py 193 2007-04-05 13:30:01Z cameron $
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# Note: The majority of the uDraw functionality wrapper documentation was ripped directly from:
#
#    http://www.informatik.uni-bremen.de/uDrawGraph/en/index.html
#

'''
@author:       Pedram Amini
@license:      GNU General Public License 2.0 or later
@contact:      pedram.amini@gmail.com
@organization: www.openrce.org
'''

import socket

class udraw_connector:
    '''
    This class provides an abstracted interface for communicating with uDraw(Graph) when it is configured to listen on a
    TCP socket in server mode.

    @todo: Debug various broken routines, abstract more of the uDraw API.
    '''

    command_handlers = {}
    sock             = None

    ####################################################################################################################
    def __init__ (self, host="127.0.0.1", port=2542):
        '''
        '''

        self.command_handlers = {}
        self.sock             = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        # receive the initial notification message.
        self.sock.recv(8)

        self.log = lambda x: None


    ####################################################################################################################
    def change_element_color (self, element, id, color):
        '''
        This command is used to update the attributes of nodes and edges that exist in the current graph.
        '''

        command  = 'graph(change_attr(['
        command += '%s("%08x",[a("COLOR","#%06x")])'   % (element, id, color)
        command += ']))\n'
        self.send(command)


    ####################################################################################################################
    def focus_node (self, node_id, animated=True):
        '''
        Scrolls the visible part of the graph visualization to the node specified by "node_id".

        @todo: This routine is buggy. Appears to only want to work when being called after a call to
               change_element_color(), though the element color change will not actually work. Need to debug.
        '''

        if animated:
            command = 'special(focus_node_animated("%08x"))\n' % node_id
        else:
            command = 'special(focus_node("%08x"))\n' % node_id

        self.send(command)


    ####################################################################################################################
    def graph_new (self, graph):
        '''
        Sends a graph in term representation format to uDraw(Graph) for visualization.
        '''

        command  = 'graph(new_placed('
        command += graph.render_graph_udraw()
        command += '))\n'

        self.send(command)


    ####################################################################################################################
    def graph_update (self, graph):
        '''
        This command can be used to update the structure of the currently loaded graph.

        @todo: This routine is not behaving appropriately, need to debug.
        '''

        command  = "graph(mixed_update("
        command += graph.render_graph_udraw_update()
        command += "))\n"

        self.send(command)


    ####################################################################################################################
    def layout_improve_all (self):
        '''
        This command starts the layout algorithm to improve the visualization quality of the whole graph by reducing
        unnecessary edge crossings and edge bends.
        '''

        command = "menu(layout(improve_all))\n"
        self.send(command)

    ####################################################################################################################
    def message_loop (self, arg1, arg2):
        '''
        This routine should be threaded out. This routine will normally be called in the following fashion::

            thread.start_new_thread(udraw.message_loop, (None, None))

        The arguments to this routine are not currently used and will be ignored.
        '''

        while 1:
            try:
                from_server = self.sock.recv(1024)
                (command, args) = self.parse(from_server)

                if self.command_handlers.has_key(command):
                    self.command_handlers[command](self, args)
            except:
                # connection severed.
                break


    ####################################################################################################################
    def open_survey_view (self):
        '''
        Open a survey view showing the whole graph in a reduced scale.
        '''

        self.send("menu(view(open_survey_view))\n")


    ####################################################################################################################
    def parse (self, answer):
        '''
        '''

        answer = answer.rstrip("\r\n")
        self.log("raw: %s" % answer)

        # extract the answer type.
        command = answer.split('(')[0]
        args    = None

        # if the answer contains a list, extract and convert it into a native Python list.
        if answer.count("["):
            args = answer[answer.index('[')+1:answer.rindex(']')]

            if len(args):
                args = args.replace('"', '')
                args = args.split(',')
            else:
                args = None

        # otherwise, if there are "arguments", grab them as a string.
        elif answer.count("("):
            args = answer[answer.index('(')+2:answer.index(')')-1]

        self.log("parsed command: %s" % command)
        self.log("parsed args:    %s" % args)
        return (command, args)


    ####################################################################################################################
    def scale (self, parameter):
        '''
        Sets the scale to the given parameter which is a percent value that must be from 1 to 100.
        '''

        if parameter in ["full_scale", "full"]:
            parameter = "full_scale"

        elif parameter in ["fit_scale_to_window", "fit"]:
            parameter = fit_scale_to_window

        elif type(parameter) is int:
            parameter = "scale(%d)" % parameter

        else:
            return

        self.send("menu(view(%s))\n" % scale)


    ####################################################################################################################
    def send (self, data):
        '''
        '''

        msg  = "\n----- sending -------------------------------------------------------\n"
        msg += data + "\n"
        msg += "---------------------------------------------------------------------\n\n"

        self.log(msg)
        self.sock.send(data)


    ####################################################################################################################
    def set_command_handler (self, command, callback_func):
        '''
        Set a callback for the specified command. The prototype of the callback routines is::

            func (udraw_connector, args)

        You can register a callback for any command received from the udraw server.

        @type  command:        String
        @param command:        Command string
        @type  callback_func:  Function
        @param callback_func:  Function to call when specified exception code is caught.
        '''

        self.command_handlers[command] = callback_func


    ####################################################################################################################
    def window_background (self, bg):
        '''
        Sets the background of the base window to the color specified by parameter bg. This is a RGB value like
        "#0f331e" in the same format as used for command-line option -graphbg.
        '''

        command = 'window(background("%s"))' % bg
        self.send(command)


    ####################################################################################################################
    def window_status (self, msg):
        '''
        Displays a message in the right footer area of the base window.
        '''

        command = 'window(show_status("%s"))' % msg
        self.send(command)


    ####################################################################################################################
    def window_title (self, msg):
        '''
        Sets the title of the base window to msg.
        '''

        command = 'window(title("%s"))' % msg
        self.send(command)
########NEW FILE########
__FILENAME__ = var_backtrace
from idaapi         import *
from idautils       import *
from idc            import *

from pida    import *
#import pida

import time

'''
Variable backtrace script for IDA.

This does not work independantly of IDA at the moment, but does however rely on the PIDA 
extensions for manipulating varivakes

$Id: var_backtrace.py 194 2007-04-05 15:31:53Z cameron $

'''

ida_log = lambda x: sys.stdout.write(x + "\n")

def extract_internal_registers(operand):
    '''
    Extracts any registers nested inside a reference.
    
    @type   operand:    String
    @param  operand:    The operand to inspect
    
    @rtype:     String List
    @returns:   A list of registers embedded in the given reference
    '''
    stripped = operand.lstrip('[').rstrip(']')
    components = stripped.replace('*', '+').split('+')
    ret_val = []
    for reg in components:
        if not (reg[-1] == "h" and reg.rstrip('h').isdigit()):
            ida_log("adding %s" % reg)
            ret_val.append(reg)
            
    return ret_val

def choose_backtrace_target(ea):
    '''
    Prompts the user for the target operand in the current instruction.
    TODO: allow user to manually enter a target if none are found
    
    @type   ea: DWORD
    @param  ea: The address to search for operands
    
    @rtype:     String
    @returns:   The text representation of the variable to backtrace
    '''
    targets = []
    
    for op_index in xrange(3):
        current_tgt = GetOpnd(ea, op_index)
        if (current_tgt != None and current_tgt != "" and not (current_tgt in targets)):
            targets.append(current_tgt)
            if current_tgt.find('dword ptr [') == 0:
                targets.append(current_tgt.lstrip('dword ptr '))
                targets += extract_internal_registers(current_tgt.lstrip('dword ptr '))
            elif current_tgt[0] == '[' and current_tgt[-1] == ']':
                targets += extract_internal_registers(current_tgt)      
            
    for target in targets:                
        prompt_result = AskYN(1, "Backtrace %s?" % target)
        if prompt_result == -1:
            return None
        elif prompt_result == 1:
            return target
            
    return None
    
def trace_block(heads, initial_target, initial_ea=None):
    '''
    Traces backwards through a basic block looking for adjustments to the 
    target variable.
    
    @type   initial_target: String
    @param  initial_target: The value of the current variable being traced
    
    @type   initial_ea:     DWORD
    @param  initial_ea:     The initial address to begin the trace from. If empty, it will start at the end of the block.
    
    @rtype:     tuple(String,String,DWORD)    
    @returns:   a Tuple consisting of the new target, the type of source if any and the address if a source is found.
    '''
    heads.reverse()    
    target = [initial_target]
    if target[0][0] == '[':
        target.append(extract_internal_registers(target[0])[0]) # only look for the base
    
    # if len(target) > 1:
    #    ida_log("also %s" % target[1])
    
    if initial_ea == None:
        initial_ea = heads[0].ea
    
    ida_log("%08x: starting block trace. %d instructions." % (heads[0].ea, len(heads)))
    
    mod_type = None
    mod_addr = None
    
    for ins in heads:  # Go from the end
        if ins.ea > initial_ea:
            pass
        elif ("eax" in target) and (ins.mnem == "call") and ins.ea != initial_ea:
                # trace into call                
                mod_type = "call"
                mod_addr = ins.ea
                target = None
                break            
                
        elif (ins.mnem == "mov") and (ins.op1 in target):
            target = [ins.op2]            
            if target[0][0] == '[':
                target.append(extract_internal_registers(target[0])[0]) # only look for the base            
            ida_log("%08x: Switched trace to %s" % (ins.ea, target[0]))           
        elif (ins.mnem == "lea") and (ins.op1 in target):
            target = [ins.op2]
            if target[0][0] == '[':
                target.append(extract_internal_registers(target[0])[0]) # only look for the base
            ida_log("%08x: Switched trace to %s" % (ins.ea, target[0]))           
        elif (ins.mnem == "xor") and (ins.op1 in target) and (ins.op2 in target):
            mod_type = "zero"
            mod_addr = ins.ea
            target = None
            break 
        elif (ins.mnem == "pop") and (ins.op1 in target):
            mod_type = "pop"
            mod_addr = ins.ea
            target = None
            break        
            
    if target != None:
        target = target[0]            
        
    return (target, mod_type, mod_addr)
    
    
target = choose_backtrace_target(ScreenEA())

if target == None:
    ida_log("No target chosen")
else:
    ida_log("Target \"%s\" chosen for backtrace" % target)

current_ea = ScreenEA()
    
fn = function(current_ea)
 
bb = fn.find_basic_block(current_ea)
 
target,mod,addr = trace_block(bb.sorted_instructions(), target, current_ea)
kill_count = 0

var_src = {}

if target == None:
    var_src[addr] = mod
else:
    bb_hits = {}    
    bb_targets = {}
    
    new_travel = [bb.function.nodes[edge.src] for edge in bb.function.edges_to(bb.id)]
           
    if (new_travel == None) or (len(new_travel) == 0):
        ida_log("%08x: No blocks found." % bb.start_ea)
    else:
        for block in new_travel:
            ida_log("Adding source: %08x" % block.ea_start)
            bb_targets[block] = target
    
    while len(bb_targets) > 0:
        bb = bb_targets.keys()[0]        
        target = bb_targets[bb]
        del bb_targets[bb]
        
        if not bb.ea_start in bb_hits:
            target,mod,addr = trace_block(bb.sorted_instructions(), target) 
            
            bb_hits[bb.ea_start] = target  
            
            new_travel = [bb.function.nodes[edge.src] for edge in bb.function.edges_to(bb.id)]
           
            if mod != None:
                var_src[addr] = mod
            elif (new_travel == None) or (len(new_travel) == 0):
                if (bb.ea_start == bb.function.ea_start):
                    var_src[bb.ea_start] = "fn_arg:" + target
                else:
                    ida_log("%08x: No blocks found." % bb.ea_start)
            else:
                for block in new_travel:
                    bb_targets[block] = target
            
            
            # kill_count += 1
            if kill_count == 20:
                ida_log("Hit kill count")
                break
                
ida_log("Possible sources detected: %d" % len(var_src))
for key in var_src.keys():
    if var_src[key] == "zero":
        ida_log("%08x: Memory Zeroed" % key)
    elif var_src[key] == "call":
        ida_log("%08x: Return value from CALL" % key)
    elif var_src[key].find("fn_arg") == 0:
        ida_log("%08x: Passed in to the function via %s" % (key ,var_src[key].lstrip("fn_arg:")))
        xrefs = CodeRefsTo(key, 0)
        ida_log("found %d xrefs" % len(xrefs))
########NEW FILE########
__FILENAME__ = __install_requirements
#!c:\python\python.exe

# $Id: __install_requirements.py 194 2007-04-05 15:31:53Z cameron $

import urllib
import os
import shutil

# globals.
downloaded = 0

########################################################################################################################
def urllib_hook (idx, slice, total):
    global downloaded

    downloaded += slice

    completed = int(float(downloaded) / float(total) * 100)

    if completed > 100:
        completed = 100

    print "\tdownloading ... %d%%\r" % completed,


def get_it (url, file_name):
    global downloaded

    downloaded = 0
    u = urllib.urlretrieve(url, reporthook=urllib_hook)
    print
    shutil.move(u[0], file_name)
    os.system("start " + file_name)

########################################################################################################################

try:
    print "looking for ctypes ...",
    import ctypes
    print "FOUND"
except:
    print "NOT FOUND"
    choice = raw_input("\tWant me to get it? ").lower()
    if choice.startswith("y"):
        get_it("http://superb-east.dl.sourceforge.net/sourceforge/ctypes/ctypes-0.9.9.6.win32-py2.4.exe", "installers/ctypes-0.9.9.6.win32-py2.4.exe")

try:
    print "looking for pydot ...",
    import pydot
    print "FOUND"
except:
    print "NOT FOUND"

try:
    print "looking for wxPython ...",
    import wx
    print "FOUND"
except:
    print "NOT FOUND"
    choice = raw_input("\tWant me to get it? ").lower()
    if choice.startswith("y"):
        get_it("http://umn.dl.sourceforge.net/sourceforge/wxpython/wxPython2.6-win32-ansi-2.6.3.2-py24.exe", "installers/wxPython2.6-win32-ansi-2.6.3.2-py24.exe")

try:
    print "looking for MySQLdb ...",
    import MySQLdb
    print "FOUND"
except:
    print "NOT FOUND"
    choice = raw_input("\tWant me to get it? ").lower()
    if choice.startswith("y"):
        get_it("http://superb-east.dl.sourceforge.net/sourceforge/mysql-python/MySQL-python.exe-1.2.1_p2.win32-py2.4.exe", "installers/MySQL-python.exe-1.2.1_p2.win32-py2.4.exe")

try:
    print "looking for GraphViz in default directory ...",
    fh = open("c:\\program files\\graphviz")
    close(fh)
except IOError, e:
    if e.errno == 2:
        print "NOT FOUND"
    else:
        print "FOUND"

try:
    print "looking for Oreas GDE in default directory ...",
    fh = open("c:\\program files\\govisual diagram editor")
    close(fh)
except IOError, e:
    if e.errno == 2:
        print "NOT FOUND"
        choice = raw_input("\tWant me to get it? ").lower()
        if choice.startswith("y"):
            get_it("http://www.oreas.com/download/get_gde_win.php", "installers/gde-win.exe")
    else:
        print "FOUND"

try:
    print "looking for uDraw(Graph) in default directory ...",
    fh = open("c:\\program files\\udraw(graph)")
    close(fh)
except IOError, e:
    if e.errno == 2:
        print "NOT FOUND"
        choice = raw_input("\tWant me to get it? ").lower()
        if choice.startswith("y"):
            get_it("http://www.informatik.uni-bremen.de/uDrawGraph/download/uDrawGraph-3.1.1-0-win32-en.exe", "installers/uDrawGraph-3.1.1-0-win32-en.exe")
    else:
        print "FOUND"

try:
    print "looking for PaiMei -> PyDbg ...",
    import pydbg
    print "FOUND"
except:
    print "NOT FOUND"

try:
    print "looking for PaiMei -> PIDA ...",
    import pida
    print "FOUND"
except:
    print "NOT FOUND"

try:
    print "looking for PaiMei -> pGRAPH ...",
    import pgraph
    print "FOUND"
except:
    print "NOT FOUND"

try:
    print "looking for PaiMei -> Utilities ...",
    import utils
    print "FOUND"
except:
    print "NOT FOUND"

choice = raw_input("\nInstall PaiMei framework libraries to Python site packages? ").lower()
if choice.startswith("y"):
    os.system("start installers/PaiMei-1.1.win32.exe")

print "\nRun __setup_mysql.py to setup database and complete installation. Then run console\PAIMEIconsole.py"

raw_input("\nHit enter to exit installer.")
########NEW FILE########
