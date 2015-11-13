__FILENAME__ = autocompletion
import config
import mypickle
import screenplay
import util

# manages auto completion information for a single script.
class AutoCompletion:
    def __init__(self):
        # type configs, key = line type, value = Type
        self.types = {}

        # element types
        t = Type(screenplay.SCENE)
        self.types[t.ti.lt] = t

        t = Type(screenplay.CHARACTER)
        self.types[t.ti.lt] = t

        t = Type(screenplay.TRANSITION)
        t.items = [
            "BACK TO:",
            "CROSSFADE:",
            "CUT TO:",
            "DISSOLVE TO:",
            "FADE IN:",
            "FADE OUT",
            "FADE TO BLACK",
            "FLASHBACK TO:",
            "JUMP CUT TO:",
            "MATCH CUT TO:",
            "SLOW FADE TO BLACK",
            "SMASH CUT TO:",
            "TIME CUT:"
            ]
        self.types[t.ti.lt] = t
        
        t = Type(screenplay.SHOT)
        self.types[t.ti.lt] = t

        self.refresh()

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = mypickle.Vars.makeVals(s)

        for t in self.types.itervalues():
            t.load(vals, "AutoCompletion/")

        self.refresh()

    # save config into a string and return that.
    def save(self):
        s = ""

        for t in self.types.itervalues():
            s += t.save("AutoCompletion/")

        return s

    # fix up invalid values and uppercase everything.
    def refresh(self):
        for t in self.types.itervalues():
            tmp = []

            for v in t.items:
                v = util.upper(util.toInputStr(v)).strip()

                if len(v) > 0:
                    tmp.append(v)

            t.items = tmp

    # get type's Type, or None if it doesn't exist.
    def getType(self, lt):
        return self.types.get(lt)

# auto completion info for one element type
class Type:
    cvars = None

    def __init__(self, lt):

        # pointer to TypeInfo
        self.ti = config.lt2ti(lt)

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addBool("enabled", True, "Enabled")
            v.addList("items", [], "Items",
                      mypickle.StrLatin1Var("", "", ""))

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name

        self.cvars.load(vals, prefix, self)

########NEW FILE########
__FILENAME__ = autocompletiondlg
import gutil
import misc
import util

import wx

class AutoCompletionDlg(wx.Dialog):
    def __init__(self, parent, autoCompletion):
        wx.Dialog.__init__(self, parent, -1, "Auto-completion",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.autoCompletion = autoCompletion

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Element:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.elementsCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for t in autoCompletion.types.itervalues():
            self.elementsCombo.Append(t.ti.name, t.ti.lt)

        wx.EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        self.enabledCb = wx.CheckBox(self, -1, "Auto-completion enabled")
        wx.EVT_CHECKBOX(self, self.enabledCb.GetId(), self.OnMisc)
        vsizer.Add(self.enabledCb, 0, wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "Default items:"))

        self.itemsEntry = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE |
                                      wx.TE_DONTWRAP, size = (400, 200))
        wx.EVT_TEXT(self, self.itemsEntry.GetId(), self.OnMisc)
        vsizer.Add(self.itemsEntry, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def OnOK(self, event):
        self.autoCompletion.refresh()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        t = self.autoCompletion.getType(self.lt)

        self.enabledCb.SetValue(t.enabled)

        self.itemsEntry.Enable(t.enabled)
        self.itemsEntry.SetValue("\n".join(t.items))

    def OnMisc(self, event = None):
        t = self.autoCompletion.getType(self.lt)

        t.enabled = bool(self.enabledCb.IsChecked())
        self.itemsEntry.Enable(t.enabled)

        # this is cut&pasted from autocompletion.AutoCompletion.refresh,
        # but I don't want to call that since it does all types, this does
        # just the changed one.
        tmp = []
        for v in misc.fromGUI(self.itemsEntry.GetValue()).split("\n"):
            v = util.toInputStr(v).strip()

            if len(v) > 0:
                tmp.append(v)

        t.items = tmp

########NEW FILE########
__FILENAME__ = cfgdlg
import config
import gutil
import misc
import screenplay
import truetype
import util

import os.path

import wx

# stupid hack to get correct window modality stacking for dialogs
cfgFrame = None

# WX2.6-FIXME: we can delete this when/if we switch to using wxListBook in
# wxWidgets 2.6
class MyListBook(wx.ListBox):
    def __init__(self, parent):
        wx.ListBox.__init__(self, parent, -1)

        wx.EVT_LISTBOX(self, self.GetId(), self.OnPageChange)

    # get a list of all the pages
    def GetPages(self):
        ret = []

        for i in range(self.GetCount()):
            ret.append(self.GetClientData(i))

        return ret

    def AddPage(self, page, name):
        self.Append(name, page)

    # get (w,h) tuple that's big enough to cover all contained pages
    def GetContainingSize(self):
        w, h = 0, 0

        for page in self.GetPages():
            size = page.GetClientSize()
            w = max(w, size.width)
            h = max(h, size.height)

        return (w, h)

    # set all page sizes
    def SetPageSizes(self, w, h):
        for page in self.GetPages():
            page.SetClientSizeWH(w, h)

    def OnPageChange(self, event = None):
        for page in self.GetPages():
            page.Hide()

        panel = self.GetClientData(self.GetSelection())

        # newer wxWidgets versions sometimes return None from the above
        # for some reason when the dialog is closed.
        if panel is None:
            return

        if hasattr(panel, "doForcedUpdate"):
            panel.doForcedUpdate()

        panel.Show()

class CfgDlg(wx.Dialog):
    def __init__(self, parent, cfg, applyFunc, isGlobal):
        wx.Dialog.__init__(self, parent, -1, "",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.cfg = cfg
        self.applyFunc = applyFunc

        global cfgFrame
        cfgFrame = self

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.listbook = MyListBook(self)
        w = util.getTextExtent(self.listbook.GetFont(), "Formatting")[0]
        util.setWH(self.listbook, w + 20, 200)

        hsizer.Add(self.listbook, 0, wx.EXPAND)

        self.panel = wx.Panel(self, -1)

        hsizer.Add(self.panel, 1, wx.EXPAND)

        if isGlobal:
            self.SetTitle("Settings dialog")

            self.AddPage(GlobalAboutPanel, "About")
            self.AddPage(ColorsPanel, "Colors")
            self.AddPage(DisplayPanel, "Display")
            self.AddPage(ElementsGlobalPanel, "Elements")
            self.AddPage(KeyboardPanel, "Keyboard")
            self.AddPage(MiscPanel, "Misc")
        else:
            self.SetTitle("Script settings dialog")

            self.AddPage(ScriptAboutPanel, "About")
            self.AddPage(ElementsPanel, "Elements")
            self.AddPage(FormattingPanel, "Formatting")
            self.AddPage(PaperPanel, "Paper")
            self.AddPage(PDFPanel, "PDF")
            self.AddPage(PDFFontsPanel, "PDF/Fonts")
            self.AddPage(StringsPanel, "Strings")

        size = self.listbook.GetContainingSize()

        hsizer.SetItemMinSize(self.panel, *size)
        self.listbook.SetPageSizes(*size)

        self.listbook.SetSelection(0)

        # it's unclear whether SetSelection sends an event on all
        # platforms or not, so force correct action.
        self.listbook.OnPageChange()

        vsizer.Add(hsizer, 1, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        applyBtn = gutil.createStockButton(self, "Apply")
        hsizer.Add(applyBtn, 0, wx.ALL, 5)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.ALL, 5)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.ALL, 5)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        self.SetSizerAndFit(vsizer)
        self.Layout()
        self.Center()

        wx.EVT_BUTTON(self, applyBtn.GetId(), self.OnApply)
        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def AddPage(self, classObj, name):
        p = classObj(self.panel, -1, self.cfg)
        self.listbook.AddPage(p, name)

    # check for errors in each panel
    def checkForErrors(self):
        for panel in self.listbook.GetPages():
            if hasattr(panel, "checkForErrors"):
                panel.checkForErrors()

    def OnOK(self, event):
        self.checkForErrors()
        self.EndModal(wx.ID_OK)

    def OnApply(self, event):
        self.checkForErrors()
        self.applyFunc(self.cfg)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

class AboutPanel(wx.Panel):
    def __init__(self, parent, id, cfg, text):
        wx.Panel.__init__(self, parent, id)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, text))

        util.finishWindow(self, vsizer, center = False)

class GlobalAboutPanel(AboutPanel):
    def __init__(self, parent, id, cfg):
        s = \
"""This is the config dialog for global settings, which means things
that affect the user interface of the program like interface colors,
keyboard shortcuts, display fonts, and so on.

The settings here are independent of any script being worked on,
and unique to this computer.

None of the settings here have any effect on the generated PDF
output for a script. See Script/Settings for those."""

        AboutPanel.__init__(self, parent, id, cfg, s)

class ScriptAboutPanel(AboutPanel):
    def __init__(self, parent, id, cfg):
        s = \
"""This is the config dialog for script format settings, which means
things that affect the generated PDF output of a script. Things like
paper size, indendation/line widths/font styles for the different
element types, and so on.

The settings here are saved within the screenplay itself.

If you're looking for the user interface settings (colors, keyboard
shortcuts, etc.), those are found in File/Settings."""

        AboutPanel.__init__(self, parent, id, cfg, s)

class DisplayPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Screen fonts:"))

        self.fontsLb = wx.ListBox(self, -1, size = (300, 100))

        for it in ["fontNormal", "fontBold", "fontItalic", "fontBoldItalic"]:
            self.fontsLb.Append("", it)

        vsizer.Add(self.fontsLb, 0, wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        btn = wx.Button(self, -1, "Change")
        wx.EVT_LISTBOX_DCLICK(self, self.fontsLb.GetId(),
            self.OnChangeFont)
        wx.EVT_BUTTON(self, btn.GetId(), self.OnChangeFont)

        self.errText = wx.StaticText(self, -1, "")
        self.origColor = self.errText.GetForegroundColour()

        hsizer.Add(btn)
        hsizer.Add((20, -1))
        hsizer.Add(self.errText, 0, wx.ALIGN_CENTER_VERTICAL)
        vsizer.Add(hsizer, 0, wx.BOTTOM, 20)

        vsizer.Add(wx.StaticText(self, -1, "The settings below apply only"
                                " to 'Draft' view mode."), 0, wx.BOTTOM, 15)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Row spacing:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.spacingEntry = wx.SpinCtrl(self, -1)
        self.spacingEntry.SetRange(*self.cfg.cvars.getMinMax("fontYdelta"))
        wx.EVT_SPINCTRL(self, self.spacingEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.spacingEntry, self.OnKillFocus)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(wx.StaticText(self, -1, "pixels"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 15)

        self.pbRb = wx.RadioBox(self, -1, "Page break lines to show",
            style = wx.RA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "None", "Normal", "Normal + unadjusted   " ])
        vsizer.Add(self.pbRb)

        self.fontsLb.SetSelection(0)
        self.updateFontLb()

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_RADIOBOX(self, self.pbRb.GetId(), self.OnMisc)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wx.GTK gets stuck in
        # some weird state
        event.Skip()

    def OnChangeFont(self, event):
        fname = self.fontsLb.GetClientData(self.fontsLb.GetSelection())
        nfont = getattr(self.cfg, fname)

        fd = wx.FontData()
        nfi = wx.NativeFontInfo()
        nfi.FromString(nfont)
        font = wx.FontFromNativeInfo(nfi)
        fd.SetInitialFont(font)

        dlg = wx.FontDialog(self, fd)
        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()
            if util.isFixedWidth(font):
                setattr(self.cfg, fname, font.GetNativeFontInfo().ToString())

                self.cfg.fontYdelta = util.getFontHeight(font)

                self.cfg2gui()
                self.updateFontLb()
            else:
                wx.MessageBox("The selected font is not fixed width and"
                              " can not be used.", "Error", wx.OK, cfgFrame)

        dlg.Destroy()

    def OnMisc(self, event = None):
        self.cfg.fontYdelta = util.getSpinValue(self.spacingEntry)
        self.cfg.pbi = self.pbRb.GetSelection()

    def updateFontLb(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]

        # keep track if all fonts have the same width
        widths = set()

        for i in range(len(names)):
            nfi = wx.NativeFontInfo()
            nfi.FromString(getattr(self.cfg, self.fontsLb.GetClientData(i)))

            ps = nfi.GetPointSize()
            s = nfi.GetFaceName()

            self.fontsLb.SetString(i, "%s: %s, %d" % (names[i], s, ps))

            f = wx.FontFromNativeInfo(nfi)
            widths.add(util.getTextExtent(f, "iw")[0])

        if len(widths) > 1:
            self.errText.SetLabel("Fonts have different widths")
            self.errText.SetForegroundColour((255, 0, 0))
        else:
            self.errText.SetLabel("Fonts have matching widths")
            self.errText.SetForegroundColour(self.origColor)

    def cfg2gui(self):
        self.spacingEntry.SetValue(self.cfg.fontYdelta)
        self.pbRb.SetSelection(self.cfg.pbi)

class ElementsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Element:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.elementsCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.addTextStyles("Screen", "screen", self))
        hsizer.Add(self.addTextStyles("Print", "export", self), 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        gsizer.Add(wx.StaticText(self, -1, "Empty lines / 10 before:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.SpinCtrl(self, -1)
        tmp.SetRange(*self.cfg.getType(screenplay.ACTION).cvars.getMinMax(
            "beforeSpacing"))
        wx.EVT_SPINCTRL(self, tmp.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(tmp, self.OnKillFocus)
        gsizer.Add(tmp)
        self.beforeSpacingEntry = tmp

        gsizer.Add(wx.StaticText(self, -1, "Empty lines / 10 between:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.SpinCtrl(self, -1)
        tmp.SetRange(*self.cfg.getType(screenplay.ACTION).cvars.getMinMax(
            "intraSpacing"))
        wx.EVT_SPINCTRL(self, tmp.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(tmp, self.OnKillFocus)
        gsizer.Add(tmp)
        self.intraSpacingEntry = tmp

        vsizer.Add(gsizer, 0, wx.BOTTOM, 20)

        gsizer = wx.FlexGridSizer(2, 3, 5, 0)

        gsizer.Add(wx.StaticText(self, -1, "Indent:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.indentEntry = wx.SpinCtrl(self, -1)
        self.indentEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("indent"))
        wx.EVT_SPINCTRL(self, self.indentEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.indentEntry, self.OnKillFocus)
        gsizer.Add(self.indentEntry, 0)

        gsizer.Add(wx.StaticText(self, -1, "characters (10 characters"
            " = 1 inch)"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        gsizer.Add(wx.StaticText(self, -1, "Width:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.widthEntry = wx.SpinCtrl(self, -1)
        self.widthEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("width"))
        wx.EVT_SPINCTRL(self, self.widthEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.widthEntry, self.OnKillFocus)
        gsizer.Add(self.widthEntry, 0)

        gsizer.Add(wx.StaticText(self, -1, "characters (10 characters"
            " = 1 inch)"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        vsizer.Add(gsizer, 0, wx.BOTTOM, 20)

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTextStyles(self, name, prefix, parent):
        hsizer = wx.StaticBoxSizer(wx.StaticBox(parent, -1, name),
                                   wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(2, 2, 0, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.addCheckBox("Caps", prefix, parent, gsizer, pad)
        self.addCheckBox("Italic", prefix, parent, gsizer, pad)
        self.addCheckBox("Bold", prefix, parent, gsizer, pad)
        self.addCheckBox("Underlined", prefix, parent, gsizer, pad)

        hsizer.Add(gsizer, 0, wx.EXPAND)

        return hsizer

    def addCheckBox(self, name, prefix, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        wx.EVT_CHECKBOX(self, cb.GetId(), self.OnStyleCb)
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, prefix + name + "Cb", cb)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        self.cfg2gui()

    def OnStyleCb(self, event):
        tcfg = self.cfg.types[self.lt]

        tcfg.screen.isCaps = self.screenCapsCb.GetValue()
        tcfg.screen.isItalic = self.screenItalicCb.GetValue()
        tcfg.screen.isBold = self.screenBoldCb.GetValue()
        tcfg.screen.isUnderlined = self.screenUnderlinedCb.GetValue()

        tcfg.export.isCaps = self.exportCapsCb.GetValue()
        tcfg.export.isItalic = self.exportItalicCb.GetValue()
        tcfg.export.isBold = self.exportBoldCb.GetValue()
        tcfg.export.isUnderlined = self.exportUnderlinedCb.GetValue()

    def OnMisc(self, event = None):
        tcfg = self.cfg.types[self.lt]

        tcfg.beforeSpacing = util.getSpinValue(self.beforeSpacingEntry)
        tcfg.intraSpacing = util.getSpinValue(self.intraSpacingEntry)
        tcfg.indent = util.getSpinValue(self.indentEntry)
        tcfg.width = util.getSpinValue(self.widthEntry)

    def cfg2gui(self):
        tcfg = self.cfg.types[self.lt]

        self.screenCapsCb.SetValue(tcfg.screen.isCaps)
        self.screenItalicCb.SetValue(tcfg.screen.isItalic)
        self.screenBoldCb.SetValue(tcfg.screen.isBold)
        self.screenUnderlinedCb.SetValue(tcfg.screen.isUnderlined)

        self.exportCapsCb.SetValue(tcfg.export.isCaps)
        self.exportItalicCb.SetValue(tcfg.export.isItalic)
        self.exportBoldCb.SetValue(tcfg.export.isBold)
        self.exportUnderlinedCb.SetValue(tcfg.export.isUnderlined)

        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.beforeSpacingEntry.SetValue(5)
        self.intraSpacingEntry.SetValue(5)
        self.indentEntry.SetValue(5)

        self.beforeSpacingEntry.SetValue(tcfg.beforeSpacing)
        self.intraSpacingEntry.SetValue(tcfg.intraSpacing)
        self.indentEntry.SetValue(tcfg.indent)
        self.widthEntry.SetValue(tcfg.width)

class ColorsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.colorsLb = wx.ListBox(self, -1, size = (300, 250))

        tmp = self.cfg.cvars.color.values()
        tmp.sort(lambda c1, c2: cmp(c1.descr, c2.descr))

        for it in tmp:
            self.colorsLb.Append(it.descr, it.name)

        hsizer.Add(self.colorsLb, 1)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        btn = wx.Button(self, -1, "Change")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnChangeColor)
        vsizer2.Add(btn, 0, wx.BOTTOM, 10)

        btn = wx.Button(self, -1, "Restore default")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnDefaultColor)
        vsizer2.Add(btn)

        hsizer.Add(vsizer2, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.colorSample = misc.MyColorSample(self, -1,
            size = wx.Size(200, 50))
        hsizer.Add(self.colorSample, 1, wx.EXPAND)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.useCustomElemColors = wx.CheckBox(
            self, -1, "Use per-element-type colors")
        wx.EVT_CHECKBOX(self, self.useCustomElemColors.GetId(), self.OnMisc)
        vsizer.Add(self.useCustomElemColors)

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_LISTBOX(self, self.colorsLb.GetId(), self.OnColorLb)
        self.colorsLb.SetSelection(0)
        self.OnColorLb()

    def OnColorLb(self, event = None):
        self.color = self.colorsLb.GetClientData(self.colorsLb.
                                                    GetSelection())
        self.cfg2gui()

    def OnChangeColor(self, event):
        cd = wx.ColourData()
        cd.SetColour(getattr(self.cfg, self.color).toWx())
        dlg = wx.ColourDialog(self, cd)
        dlg.SetTitle(self.colorsLb.GetStringSelection())
        if dlg.ShowModal() == wx.ID_OK:
            setattr(self.cfg, self.color,
                    util.MyColor.fromWx(dlg.GetColourData().GetColour()))
        dlg.Destroy()

        self.cfg2gui()

    def OnDefaultColor(self, event):
        setattr(self.cfg, self.color, self.cfg.cvars.getDefault(self.color))
        self.cfg2gui()

    def OnMisc(self, event = None):
        self.cfg.useCustomElemColors = self.useCustomElemColors.GetValue()

    def cfg2gui(self):
        self.useCustomElemColors.SetValue(self.cfg.useCustomElemColors)

        self.colorSample.SetBackgroundColour(
            getattr(self.cfg, self.color).toWx())
        self.colorSample.Refresh()

class PaperPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = 1

        self.paperSizes = {
            "A4" : (210.0, 297.0),
            "Letter" : (215.9, 279.4),
            "Custom" : (1.0, 1.0)
            }

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(3, 2, 5, 5)

        gsizer.Add(wx.StaticText(self, -1, "Type:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.paperCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for k, v in self.paperSizes.items():
            self.paperCombo.Append(k, v)

        gsizer.Add(self.paperCombo)

        gsizer.Add(wx.StaticText(self, -1, "Width:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.widthEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.widthEntry)
        hsizer.Add(wx.StaticText(self, -1, "mm"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        gsizer.Add(hsizer)

        gsizer.Add(wx.StaticText(self, -1, "Height:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.heightEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.heightEntry)
        hsizer.Add(wx.StaticText(self, -1, "mm"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        gsizer.Add(hsizer)

        vsizer.Add(gsizer, 0, wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Margins"),
                                  wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(4, 5, 5, 5)

        self.addMarginCtrl("Top", self, gsizer)
        self.addMarginCtrl("Bottom", self, gsizer)
        self.addMarginCtrl("Left", self, gsizer)
        self.addMarginCtrl("Right", self, gsizer)

        bsizer.Add(gsizer, 0, wx.EXPAND | wx.ALL, 10)

        vsizer.Add(bsizer, 0, wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "(1 inch = 25.4 mm)"), 0,
                   wx.LEFT, 25)

        self.linesLabel = wx.StaticText(self, -1, "")

        # wxwindows doesn't recalculate sizer size correctly at startup so
        # set initial text
        self.setLines()

        vsizer.Add(self.linesLabel, 0, wx.TOP, 20)

        util.finishWindow(self, vsizer, center = False)

        ptype = "Custom"
        for k, v in self.paperSizes.items():
            if self.eqFloat(self.cfg.paperWidth, v[0]) and \
               self.eqFloat(self.cfg.paperHeight, v[1]):
                ptype = k

        idx = self.paperCombo.FindString(ptype)
        if idx != -1:
            self.paperCombo.SetSelection(idx)

        wx.EVT_COMBOBOX(self, self.paperCombo.GetId(), self.OnPaperCombo)
        self.OnPaperCombo(None)

        wx.EVT_TEXT(self, self.widthEntry.GetId(), self.OnMisc)
        wx.EVT_TEXT(self, self.heightEntry.GetId(), self.OnMisc)

        self.cfg2mm()
        self.cfg2inch()

        self.blockEvents -= 1

    def eqFloat(self, f1, f2):
        return round(f1, 2) == round(f2, 2)

    def addMarginCtrl(self, name, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, name + ":"), 0,
                  wx.ALIGN_CENTER_VERTICAL)

        entry = wx.TextCtrl(parent, -1)
        sizer.Add(entry, 0)
        label = wx.StaticText(parent, -1, "mm")
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)

        entry2 = wx.TextCtrl(parent, -1)
        sizer.Add(entry2, 0, wx.LEFT, 20)
        label2 = wx.StaticText(parent, -1, "inch")
        sizer.Add(label2, 0, wx.ALIGN_CENTER_VERTICAL)

        setattr(self, name.lower() + "EntryMm", entry)
        setattr(self, name.lower() + "EntryInch", entry2)

        wx.EVT_TEXT(self, entry.GetId(), self.OnMarginMm)
        wx.EVT_TEXT(self, entry2.GetId(), self.OnMarginInch)

    def doForcedUpdate(self):
        self.setLines()

    def setLines(self):
        self.cfg.recalc(False)
        self.linesLabel.SetLabel("Lines per page: %d" % self.cfg.linesOnPage)

    def OnPaperCombo(self, event):
        w, h = self.paperCombo.GetClientData(self.paperCombo.GetSelection())

        ptype = self.paperCombo.GetStringSelection()

        if ptype == "Custom":
            self.widthEntry.Enable(True)
            self.heightEntry.Enable(True)
            w = self.cfg.paperWidth
            h = self.cfg.paperHeight
        else:
            self.widthEntry.Disable()
            self.heightEntry.Disable()

        self.widthEntry.SetValue(str(w))
        self.heightEntry.SetValue(str(h))

        self.setLines()

    def OnMisc(self, event):
        if self.blockEvents > 0:
            return

        self.entry2float(self.widthEntry, "paperWidth")
        self.entry2float(self.heightEntry, "paperHeight")

        self.setLines()

    def OnMarginMm(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryMm, "marginTop")
        self.entry2float(self.bottomEntryMm, "marginBottom")
        self.entry2float(self.leftEntryMm, "marginLeft")
        self.entry2float(self.rightEntryMm, "marginRight")

        self.setLines()

        self.cfg2inch()

        self.blockEvents -= 1

    def OnMarginInch(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryInch, "marginTop", 25.4)
        self.entry2float(self.bottomEntryInch, "marginBottom", 25.4)
        self.entry2float(self.leftEntryInch, "marginLeft", 25.4)
        self.entry2float(self.rightEntryInch, "marginRight", 25.4)

        self.setLines()

        self.cfg2mm()

        self.blockEvents -= 1

    def cfg2mm(self):
        self.topEntryMm.SetValue(str(self.cfg.marginTop))
        self.bottomEntryMm.SetValue(str(self.cfg.marginBottom))
        self.leftEntryMm.SetValue(str(self.cfg.marginLeft))
        self.rightEntryMm.SetValue(str(self.cfg.marginRight))

    def cfg2inch(self):
        self.topEntryInch.SetValue(str(self.cfg.marginTop / 25.4))
        self.bottomEntryInch.SetValue(str(self.cfg.marginBottom / 25.4))
        self.leftEntryInch.SetValue(str(self.cfg.marginLeft / 25.4))
        self.rightEntryInch.SetValue(str(self.cfg.marginRight / 25.4))

    def entry2float(self, entry, name, factor = 1.0):
        val = util.str2float(entry.GetValue(), 0.0) * factor
        setattr(self.cfg, name, val)

class FormattingPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1,
            "Leave at least this many lines at the end of a page when\n"
            "breaking in the middle of an element:"), 0, wx.BOTTOM, 5)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        self.addSpin("action", "Action:", self, gsizer, "pbActionLines")
        self.addSpin("dialogue", "Dialogue", self, gsizer, "pbDialogueLines")

        vsizer.Add(gsizer, 0, wx.LEFT, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addSpin("fontSize", "Font size:", self, hsizer, "fontSize")
        vsizer.Add(hsizer, 0, wx.TOP, 20)

        vsizer.Add(wx.StaticText(self, -1, "Scene CONTINUEDs:"), 0,
                   wx.TOP, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sceneContinuedsCb = wx.CheckBox(self, -1, "Include,")
        wx.EVT_CHECKBOX(self, self.sceneContinuedsCb.GetId(), self.OnMisc)
        hsizer.Add(self.sceneContinuedsCb, 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        self.addSpin("sceneContinuedIndent", "indent:", self, hsizer,
                     "sceneContinuedIndent")
        hsizer.Add(wx.StaticText(self, -1, "characters"), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        vsizer.Add(hsizer, 0, wx.LEFT, 5)

        self.scenesCb = wx.CheckBox(self, -1, "Include scene numbers")
        wx.EVT_CHECKBOX(self, self.scenesCb.GetId(), self.OnMisc)
        vsizer.Add(self.scenesCb, 0, wx.TOP, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.lineNumbersCb = wx.CheckBox(self, -1, "Show line numbers (debug)")
        wx.EVT_CHECKBOX(self, self.lineNumbersCb.GetId(), self.OnMisc)
        vsizer.Add(self.lineNumbersCb, 0, wx.TOP, pad)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

    def addSpin(self, name, descr, parent, sizer, cfgName):
        sizer.Add(wx.StaticText(parent, -1, descr), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        entry = wx.SpinCtrl(parent, -1)
        entry.SetRange(*self.cfg.cvars.getMinMax(cfgName))
        wx.EVT_SPINCTRL(self, entry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(entry, self.OnKillFocus)
        sizer.Add(entry, 0)

        setattr(self, name + "Entry", entry)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnMisc(self, event = None):
        self.cfg.pbActionLines = util.getSpinValue(self.actionEntry)
        self.cfg.pbDialogueLines = util.getSpinValue(self.dialogueEntry)
        self.cfg.sceneContinueds = self.sceneContinuedsCb.GetValue()
        self.cfg.sceneContinuedIndent = util.getSpinValue(
            self.sceneContinuedIndentEntry)
        self.cfg.fontSize = util.getSpinValue(self.fontSizeEntry)
        self.cfg.pdfShowSceneNumbers = self.scenesCb.GetValue()
        self.cfg.pdfShowLineNumbers = self.lineNumbersCb.GetValue()

    def cfg2gui(self):
        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.actionEntry.SetValue(5)
        self.dialogueEntry.SetValue(5)
        self.sceneContinuedIndentEntry.SetValue(5)

        self.actionEntry.SetValue(self.cfg.pbActionLines)
        self.dialogueEntry.SetValue(self.cfg.pbDialogueLines)
        self.sceneContinuedsCb.SetValue(self.cfg.sceneContinueds)
        self.sceneContinuedIndentEntry.SetValue(self.cfg.sceneContinuedIndent)
        self.fontSizeEntry.SetValue(self.cfg.fontSize)
        self.scenesCb.SetValue(self.cfg.pdfShowSceneNumbers)
        self.lineNumbersCb.SetValue(self.cfg.pdfShowLineNumbers)

class KeyboardPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, "Commands:"))

        self.commandsLb = wx.ListBox(self, -1, size = (175, 50))

        for cmd in self.cfg.commands:
            self.commandsLb.Append(cmd.name, cmd)

        vsizer2.Add(self.commandsLb, 1)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.RIGHT, 15)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, "Keys:"))

        self.keysLb = wx.ListBox(self, -1, size = (150, 60))
        vsizer2.Add(self.keysLb, 1, wx.BOTTOM, 10)

        btn = wx.Button(self, -1, "Add")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnAdd)
        vsizer2.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.addBtn = btn

        btn = wx.Button(self, -1, "Delete")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnDelete)
        vsizer2.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.deleteBtn = btn

        vsizer2.Add(wx.StaticText(self, -1, "Description:"))

        self.descEntry = wx.TextCtrl(self, -1,
            style = wx.TE_MULTILINE | wx.TE_READONLY, size = (150, 75))
        vsizer2.Add(self.descEntry, 1, wx.EXPAND)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.BOTTOM, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wx.StaticText(self, -1, "Conflicting keys:"), 0, wx.TOP, 10)

        self.conflictsEntry = wx.TextCtrl(self, -1,
            style = wx.TE_MULTILINE | wx.TE_READONLY, size = (50, 75))
        vsizer.Add(self.conflictsEntry, 1, wx.EXPAND)

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_LISTBOX(self, self.commandsLb.GetId(), self.OnCommandLb)
        self.commandsLb.SetSelection(0)
        self.OnCommandLb()

    def OnCommandLb(self, event = None):
        self.cmd = self.commandsLb.GetClientData(self.commandsLb.
                                                 GetSelection())
        self.cfg2gui()

    def OnAdd(self, event):
        dlg = misc.KeyDlg(cfgFrame, self.cmd.name)

        key = None
        if dlg.ShowModal() == wx.ID_OK:
            key = dlg.key
        dlg.Destroy()

        if key:
            kint = key.toInt()
            if kint in self.cmd.keys:
                wx.MessageBox("The key is already bound to this command.",
                              "Error", wx.OK, cfgFrame)

                return

            if key.isValidInputChar():
                wx.MessageBox("You can't bind input characters to commands.",
                              "Error", wx.OK, cfgFrame)

                return

            self.cmd.keys.append(kint)
            self.cfg2gui()

    def OnDelete(self, event):
        sel = self.keysLb.GetSelection()
        if sel != -1:
            key = self.keysLb.GetClientData(sel)
            self.cfg.removeKey(self.cmd, key)
            self.cfg2gui()

    def cfg2gui(self):
        self.cfg.addShiftKeys()
        self.keysLb.Clear()

        for key in self.cmd.keys:
            k = util.Key.fromInt(key)
            self.keysLb.Append(k.toStr(), key)

        self.addBtn.Enable(not self.cmd.isFixed)
        self.deleteBtn.Enable(not self.cmd.isFixed)

        s = self.cmd.desc
        self.descEntry.SetValue(s)
        self.updateConflicts()

    def updateConflicts(self):
        s = self.cfg.getConflictingKeys()
        if s == None:
            s = "None"

        self.conflictsEntry.SetValue(s)

class MiscPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1,
            "Default script directory"), wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.scriptDirEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.scriptDirEntry, 1,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, "Browse")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnBrowse)
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        vsizer.Add(bsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1,
            "PDF viewer application"), wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Path:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.progEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.progEntry, 1, wx.ALIGN_CENTER_VERTICAL)

        btn = wx.Button(self, -1, "Browse")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnBrowsePDF)
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, "Guess")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnGuessPDF)
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Arguments:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.argsEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.argsEntry, 1, wx.ALIGN_CENTER_VERTICAL)

        bsizer.Add(hsizer, 1, wx.EXPAND)

        vsizer.Add(bsizer, 1, wx.EXPAND)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 5
        if misc.isWindows:
            pad = 10

        self.checkListItems = [
            ("capitalize", "Auto-capitalize sentences"),
            ("capitalizeI", "Auto-capitalize i -> I"),
            ("honorSavedPos", "When opening a script, start at last saved position"),
            ("recenterOnScroll", "Recenter screen on scrolling"),
            ("overwriteSelectionOnInsert", "Typing replaces selected text"),
            ("checkOnExport", "Check script for errors before print, export or compare"),
            ]

        self.checkList = wx.CheckListBox(self, -1, size = (-1, 120))

        for it in self.checkListItems:
            self.checkList.Append(it[1])

        vsizer.Add(self.checkList, 0, wx.TOP | wx.BOTTOM, pad)

        wx.EVT_LISTBOX(self, self.checkList.GetId(), self.OnMisc)
        wx.EVT_CHECKLISTBOX(self, self.checkList.GetId(), self.OnMisc)

        self.addSpin("splashTime", "Show splash screen for X seconds:\n"
                     " (0 = disable)", self, vsizer, "splashTime")

        self.addSpin("paginate", "Auto-paginate interval in seconds:\n"
                     " (0 = disable)", self, vsizer, "paginateInterval")

        self.addSpin("wheelScroll", "Lines to scroll per mouse wheel event:",
                     self, vsizer, "mouseWheelLines")

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_TEXT(self, self.scriptDirEntry.GetId(), self.OnMisc)
        wx.EVT_TEXT(self, self.progEntry.GetId(), self.OnMisc)
        wx.EVT_TEXT(self, self.argsEntry.GetId(), self.OnMisc)

    def addSpin(self, name, descr, parent, sizer, cfgName):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, descr), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.SpinCtrl(parent, -1)
        tmp.SetRange(*self.cfg.cvars.getMinMax(cfgName))
        wx.EVT_SPINCTRL(self, tmp.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(tmp, self.OnKillFocus)
        hsizer.Add(tmp)

        sizer.Add(hsizer, 0, wx.BOTTOM, 10)

        setattr(self, name + "Entry", tmp)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnMisc(self, event = None):
        self.cfg.scriptDir = self.scriptDirEntry.GetValue().rstrip("/\\")
        self.cfg.pdfViewerPath = self.progEntry.GetValue()
        self.cfg.pdfViewerArgs = misc.fromGUI(self.argsEntry.GetValue())

        for i, it in enumerate(self.checkListItems):
            setattr(self.cfg, it[0], bool(self.checkList.IsChecked(i)))

        self.cfg.paginateInterval = util.getSpinValue(self.paginateEntry)
        self.cfg.mouseWheelLines = util.getSpinValue(self.wheelScrollEntry)
        self.cfg.splashTime = util.getSpinValue(self.splashTimeEntry)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(
            cfgFrame, defaultPath = self.cfg.scriptDir,
            style = wx.DD_NEW_DIR_BUTTON)

        if dlg.ShowModal() == wx.ID_OK:
            self.scriptDirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnBrowsePDF(self, event):
        dlg = wx.FileDialog(
            cfgFrame, "Choose program",
            os.path.dirname(self.cfg.pdfViewerPath),
            self.cfg.pdfViewerPath, style = wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            self.progEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnGuessPDF(self, event):
        # TODO: there must be a way to find out the default PDF viewer on
        # Linux; we should do that here.

        viewer = util.getWindowsPDFViewer()

        if viewer:
            self.progEntry.SetValue(viewer)
        else:
            wx.MessageBox("Unable to guess. Please set the path manually.",
                          "PDF Viewer", wx.OK, cfgFrame)

    def cfg2gui(self):
        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.paginateEntry.SetValue(5)

        self.scriptDirEntry.SetValue(self.cfg.scriptDir)
        self.progEntry.SetValue(self.cfg.pdfViewerPath)
        self.argsEntry.SetValue(self.cfg.pdfViewerArgs)

        for i, it in enumerate(self.checkListItems):
            self.checkList.Check(i, getattr(self.cfg, it[0]))

        self.paginateEntry.SetValue(self.cfg.paginateInterval)
        self.wheelScrollEntry.SetValue(self.cfg.mouseWheelLines)
        self.splashTimeEntry.SetValue(self.cfg.splashTime)

class ElementsGlobalPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Element:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.elementsCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        self.addTypeCombo("newEnter", "Enter creates", self, gsizer)
        self.addTypeCombo("newTab", "Tab creates", self, gsizer)
        self.addTypeCombo("nextTab", "Tab switches to", self, gsizer)
        self.addTypeCombo("prevTab", "Shift+Tab switches to", self, gsizer)

        vsizer.Add(gsizer)

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTypeCombo(self, name, descr, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, descr + ":"), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        combo = wx.ComboBox(parent, -1, style = wx.CB_READONLY)

        for t in config.getTIs():
            combo.Append(t.name, t.lt)

        sizer.Add(combo)

        wx.EVT_COMBOBOX(self, combo.GetId(), self.OnMisc)

        setattr(self, name + "Combo", combo)

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                   GetSelection())
        self.cfg2gui()

    def OnMisc(self, event = None):
        tcfg = self.cfg.types[self.lt]

        tcfg.newTypeEnter = self.newEnterCombo.GetClientData(
            self.newEnterCombo.GetSelection())
        tcfg.newTypeTab = self.newTabCombo.GetClientData(
            self.newTabCombo.GetSelection())
        tcfg.nextTypeTab = self.nextTabCombo.GetClientData(
            self.nextTabCombo.GetSelection())
        tcfg.prevTypeTab = self.prevTabCombo.GetClientData(
            self.prevTabCombo.GetSelection())

    def cfg2gui(self):
        tcfg = self.cfg.types[self.lt]

        util.reverseComboSelect(self.newEnterCombo, tcfg.newTypeEnter)
        util.reverseComboSelect(self.newTabCombo, tcfg.newTypeTab)
        util.reverseComboSelect(self.nextTabCombo, tcfg.nextTypeTab)
        util.reverseComboSelect(self.prevTabCombo, tcfg.prevTypeTab)

class StringsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        # list of names. each name is both the name of a wx.TextCtrl in
        # this class and the name of a string configuration variable in
        # cfg.
        self.items = []

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(4, 2, 5, 0)

        self.addEntry("strContinuedPageEnd", "(CONTINUED)", self, gsizer)
        self.addEntry("strContinuedPageStart", "CONTINUED:", self, gsizer)
        self.addEntry("strMore", "(MORE)", self, gsizer)
        self.addEntry("strDialogueContinued", " (cont'd)", self, gsizer)

        gsizer.AddGrowableCol(1)
        vsizer.Add(gsizer, 0, wx.EXPAND)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

        for it in self.items:
            wx.EVT_TEXT(self, getattr(self, it).GetId(), self.OnMisc)

    def addEntry(self, name, descr, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, descr), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.TextCtrl(parent, -1)
        sizer.Add(tmp, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        setattr(self, name, tmp)
        self.items.append(name)

    def OnMisc(self, event = None):
        for it in self.items:
            setattr(self.cfg, it, misc.fromGUI(getattr(self, it).GetValue()))

    def cfg2gui(self):
        for it in self.items:
            getattr(self, it).SetValue(getattr(self.cfg, it))

class PDFPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.includeTOCCb = self.addCb("Add table of contents", vsizer, pad)

        self.showTOCCb = self.addCb("Show table of contents on PDF open",
                                    vsizer, pad)

        self.openOnCurrentPageCb = self.addCb("Open PDF on current page",
                                              vsizer, pad)

        self.removeNotesCb = self.addCb(
            "Omit Note elements", vsizer, pad)

        self.outlineNotesCb = self.addCb(
            "  Draw rectangles around Note elements", vsizer, pad)

        self.marginsCb = self.addCb("Show margins (debug)", vsizer, pad)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

    def addCb(self, descr, sizer, pad):
        ctrl = wx.CheckBox(self, -1, descr)
        wx.EVT_CHECKBOX(self, ctrl.GetId(), self.OnMisc)
        sizer.Add(ctrl, 0, wx.TOP, pad)

        return ctrl

    def OnMisc(self, event = None):
        self.cfg.pdfIncludeTOC = self.includeTOCCb.GetValue()
        self.cfg.pdfShowTOC = self.showTOCCb.GetValue()
        self.cfg.pdfOpenOnCurrentPage = self.openOnCurrentPageCb.GetValue()
        self.cfg.pdfRemoveNotes = self.removeNotesCb.GetValue()
        self.cfg.pdfOutlineNotes = self.outlineNotesCb.GetValue()
        self.cfg.pdfShowMargins = self.marginsCb.GetValue()

        self.outlineNotesCb.Enable(not self.cfg.pdfRemoveNotes)

    def cfg2gui(self):
        self.includeTOCCb.SetValue(self.cfg.pdfIncludeTOC)
        self.showTOCCb.SetValue(self.cfg.pdfShowTOC)
        self.openOnCurrentPageCb.SetValue(self.cfg.pdfOpenOnCurrentPage)
        self.removeNotesCb.SetValue(self.cfg.pdfRemoveNotes)
        self.outlineNotesCb.SetValue(self.cfg.pdfOutlineNotes)
        self.marginsCb.SetValue(self.cfg.pdfShowMargins)

class PDFFontsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = True

        # last directory we chose a font from
        self.lastDir = u""

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1,
            "Leave all the fields empty to use the default PDF Courier\n"
            "fonts. This is highly recommended.\n"
            "\n"
            "Otherwise, fill in the font name (e.g. AndaleMono) to use\n"
            "the specified TrueType font. If you want to embed the font\n"
            "in the generated PDF files, fill in the font filename as well.\n"
            "\n"
            "See the manual for the full details.\n"))

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Type:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.typeCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)
            self.typeCombo.Append(pf.name, pf)

        hsizer.Add(self.typeCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 3, 5, 5)
        gsizer.AddGrowableCol(1)

        self.addEntry("nameEntry", "Name:", self, gsizer)
        gsizer.Add((1,1), 0)

        self.addEntry("fileEntry", "File:", self, gsizer)
        btn = wx.Button(self, -1, "Browse")
        gsizer.Add(btn)

        wx.EVT_BUTTON(self, btn.GetId(), self.OnBrowse)

        vsizer.Add(gsizer, 0, wx.EXPAND)

        util.finishWindow(self, vsizer, center = False)

        wx.EVT_COMBOBOX(self, self.typeCombo.GetId(), self.OnTypeCombo)

        self.typeCombo.SetSelection(0)
        self.OnTypeCombo()

        self.blockEvents = False

    # check that all embedded TrueType fonts are OK
    def checkForErrors(self):
        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)

            if pf.filename:
                self.getFontPostscriptName(pf.filename)

    def addEntry(self, name, descr, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, descr), 0,
                  wx.ALIGN_CENTER_VERTICAL)

        entry = wx.TextCtrl(parent, -1)
        sizer.Add(entry, 1, wx.EXPAND)

        setattr(self, name, entry)

        wx.EVT_TEXT(self, entry.GetId(), self.OnMisc)

    def OnMisc(self, event):
        if self.blockEvents:
            return

        self.pf.pdfName = misc.fromGUI(self.nameEntry.GetValue())
        self.pf.filename = self.fileEntry.GetValue()

    def OnBrowse(self, event):
        if self.pf.filename:
            dDir = os.path.dirname(self.pf.filename)
            dFile = os.path.basename(self.pf.filename)
        else:
            dDir = self.lastDir
            dFile = u""

        dlg = wx.FileDialog(cfgFrame, "Choose font file",
            defaultDir = dDir, defaultFile = dFile,
            wildcard = "TrueType fonts (*.ttf;*.TTF)|*.ttf;*.TTF|All files|*",
            style = wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            self.fileEntry.SetValue(dlg.GetPath())
            self.fileEntry.SetInsertionPointEnd()

            fname = dlg.GetPath()

            self.nameEntry.SetValue(self.getFontPostscriptName(fname))
            self.lastDir = os.path.dirname(fname)

        dlg.Destroy()

    def OnTypeCombo(self, event = None):
        self.blockEvents = True

        self.pf = self.typeCombo.GetClientData(self.typeCombo.GetSelection())
        self.cfg2gui()

        self.blockEvents = False

    def cfg2gui(self):
        self.nameEntry.SetValue(self.pf.pdfName)
        self.fileEntry.SetValue(self.pf.filename)
        self.fileEntry.SetInsertionPointEnd()

    # read TrueType font from given file and return its Postscript name,
    # or "" on errors.
    def getFontPostscriptName(self, filename):
        # we load at most 10 MB to avoid a denial-of-service attack by
        # passing around scripts containing references to fonts with
        # filenames like "/dev/zero" etc. no real font that I know of is
        # this big so it shouldn't hurt.
        fontProgram = util.loadFile(filename, cfgFrame, 10 * 1024 * 1024)

        if fontProgram is None:
            return ""

        f = truetype.Font(fontProgram)

        if not f.isOK():
            wx.MessageBox("File '%s'\n"
                          "does not appear to be a valid TrueType font."
                          % filename,
                          "Error", wx.OK, cfgFrame)

            return ""

        if not f.allowsEmbedding():
            wx.MessageBox("Font '%s'\n"
                          "does not allow embedding in its license terms.\n"
                          "You may encounter problems using this font"
                          " embedded." % filename,
                          "Error", wx.OK, cfgFrame)

        return f.getPostscriptName()

########NEW FILE########
__FILENAME__ = characterreport
import gutil
import misc
import pdf
import pml
import screenplay
import util

import wx

def genCharacterReport(mainFrame, sp):
    report = CharacterReport(sp)

    if not report.cinfo:
        wx.MessageBox("No characters speaking found.",
                      "Error", wx.OK, mainFrame)

        return

    charNames = []
    for s in util.listify(report.cinfo, "name"):
        charNames.append(misc.CheckBoxItem(s))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False, charNames,
        "Characters to include:", True)

    ok = False
    if dlg.ShowModal() == wx.ID_OK:
        ok = True

        for i in range(len(report.cinfo)):
            report.cinfo[i].include = charNames[i].selected

    dlg.Destroy()

    if not ok:
        return

    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

class CharacterReport:
    def __init__(self, sp):

        self.sp = sp

        ls = sp.lines

        # key = character name, value = CharInfo
        chars = {}

        name = None
        scene = "(NO SCENE NAME)"

        # how many lines processed for current speech
        curSpeechLines = 0

        for i in xrange(len(ls)):
            line = ls[i]

            if (line.lt == screenplay.SCENE) and\
                   (line.lb == screenplay.LB_LAST):
                scene = util.upper(line.text)

            elif (line.lt == screenplay.CHARACTER) and\
                   (line.lb == screenplay.LB_LAST):
                name = util.upper(line.text)
                curSpeechLines = 0

            elif line.lt in (screenplay.DIALOGUE, screenplay.PAREN) and name:
                ci = chars.get(name)
                if not ci:
                    ci = CharInfo(name, sp)
                    chars[name] = ci

                if scene:
                    ci.scenes[scene] = ci.scenes.get(scene, 0) + 1

                if curSpeechLines == 0:
                    ci.speechCnt += 1

                curSpeechLines += 1

                # PAREN lines don't count as spoken words
                if line.lt == screenplay.DIALOGUE:
                    ci.lineCnt += 1

                    words = util.splitToWords(line.text)

                    ci.wordCnt += len(words)
                    ci.wordCharCnt += reduce(lambda x, y: x + len(y), words,
                                             0)

                ci.pages.addPage(sp.line2page(i))

            else:
                name = None
                curSpeechLines = 0

        # list of CharInfo objects
        self.cinfo = []
        for v in chars.values():
            self.cinfo.append(v)

        self.cinfo.sort(cmpLines)

        self.totalSpeechCnt = self.sum("speechCnt")
        self.totalLineCnt = self.sum("lineCnt")
        self.totalWordCnt = self.sum("wordCnt")
        self.totalWordCharCnt = self.sum("wordCharCnt")

        # information types and what to include
        self.INF_BASIC, self.INF_PAGES, self.INF_LOCATIONS = range(3)
        self.inf = []
        for s in ["Basic information", "Page list", "Location list"]:
            self.inf.append(misc.CheckBoxItem(s))

    # calculate total sum of self.cinfo.{name} and return it.
    def sum(self, name):
        return reduce(lambda tot, ci: tot + getattr(ci, name), self.cinfo, 0)

    def generate(self):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 20.0, 12)

        for ci in self.cinfo:
            if not ci.include:
                continue

            tf.addText(ci.name, fs = 14,
                       style = pml.BOLD | pml.UNDERLINED)

            if self.inf[self.INF_BASIC].selected:
                tf.addText("Speeches: %d, Lines: %d (%.2f%%),"
                    " per speech: %.2f" % (ci.speechCnt, ci.lineCnt,
                    util.pctf(ci.lineCnt, self.totalLineCnt),
                    util.safeDiv(ci.lineCnt, ci.speechCnt)))

                tf.addText("Words: %d, per speech: %.2f,"
                    " characters per: %.2f" % (ci.wordCnt,
                    util.safeDiv(ci.wordCnt, ci.speechCnt),
                    util.safeDiv(ci.wordCharCnt, ci.wordCnt)))

            if self.inf[self.INF_PAGES].selected:
                tf.addWrappedText("Pages: %d, list: %s" % (len(ci.pages),
                    ci.pages), "       ")

            if self.inf[self.INF_LOCATIONS].selected:
                tf.addSpace(2.5)

                for it in util.sortDict(ci.scenes):
                    tf.addText("%3d %s" % (it[1], it[0]),
                               x = tf.margin * 2.0, fs = 10)

            tf.addSpace(5.0)

        return pdf.generate(tf.doc)

# information about one character
class CharInfo:
    def __init__(self, name, sp):
        self.name = name

        self.speechCnt = 0
        self.lineCnt = 0
        self.wordCnt = 0
        self.wordCharCnt = 0
        self.scenes = {}
        self.include = True
        self.pages = screenplay.PageList(sp.getPageNumbers())

def cmpLines(c1, c2):
    ret = cmp(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmp(c1.name, c2.name)

########NEW FILE########
__FILENAME__ = charmapdlg
import gutil
import misc
import util

import wx

class CharMapDlg(wx.Dialog):
    def __init__(self, parent, ctrl):
        wx.Dialog.__init__(self, parent, -1, "Character map")

        self.ctrl = ctrl

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.charMap = MyCharMap(self)
        hsizer.Add(self.charMap)

        self.insertButton = wx.Button(self, -1, " Insert character ")
        hsizer.Add(self.insertButton, 0, wx.ALL, 10)
        wx.EVT_BUTTON(self, self.insertButton.GetId(), self.OnInsert)
        gutil.btnDblClick(self.insertButton, self.OnInsert)

        util.finishWindow(self, hsizer, 0)

    def OnInsert(self, event):
        if self.charMap.selected:
            self.ctrl.OnKeyChar(util.MyKeyEvent(ord(self.charMap.selected)))

class MyCharMap(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1)

        self.selected = None

        # all valid characters
        self.chars = ""

        for i in xrange(256):
            if util.isValidInputChar(i):
                self.chars += chr(i)

        self.cols = 16
        self.rows = len(self.chars) // self.cols
        if len(self.chars) % 16:
            self.rows += 1

        # offset of grid
        self.offset = 5

        # size of a single character cell
        self.cellSize = 32

        # size of the zoomed-in character boxes
        self.boxSize = 60

        self.smallFont = util.createPixelFont(18,
            wx.FONTFAMILY_SWISS, wx.NORMAL, wx.NORMAL)
        self.normalFont = util.createPixelFont(self.cellSize - 2,
            wx.FONTFAMILY_MODERN, wx.NORMAL, wx.BOLD)
        self.bigFont = util.createPixelFont(self.boxSize - 2,
            wx.FONTFAMILY_MODERN, wx.NORMAL, wx.BOLD)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_MOTION(self, self.OnMotion)
        wx.EVT_SIZE(self, self.OnSize)

        util.setWH(self, self.cols * self.cellSize + 2 * self.offset, 460)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wx.EmptyBitmap(size.width, size.height)

    def OnLeftDown(self, event):
        pos = event.GetPosition()

        x = (pos.x - self.offset) // self.cellSize
        y = (pos.y - self.offset) // self.cellSize

        self.selected = None

        if (x >= 0) and (x < self.cols) and (y >= 0) and (y <= self.rows):
            i = y * self.cols + x
            if i < len(self.chars):
                self.selected = self.chars[i]

        self.Refresh(False)

    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event)

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetPen(wx.BLACK_PEN)
        dc.SetTextForeground(wx.BLACK)

        for y in range(self.rows + 1):
            util.drawLine(dc, self.offset, self.offset + y * self.cellSize,
                          self.cols * self.cellSize + 1, 0)

        for x in range(self.cols + 1):
            util.drawLine(dc, self.offset + x * self.cellSize,
                self.offset, 0, self.rows * self.cellSize)

        dc.SetFont(self.normalFont)

        for y in range(self.rows):
            for x in range(self.cols):
                i = y * self.cols + x
                if i < len(self.chars):
                    util.drawText(dc, self.chars[i],
                        x * self.cellSize + self.offset + self.cellSize // 2 + 1,
                        y * self.cellSize + self.offset + self.cellSize // 2 + 1,
                        util.ALIGN_CENTER, util.VALIGN_CENTER)

        y = self.offset + self.rows * self.cellSize
        pad = 5

        if self.selected:
            code = ord(self.selected)

            self.drawCharBox(dc, "Selected:", self.selected, self.offset,
                             y + pad, 75)

            c = util.upper(self.selected)
            if c == self.selected:
                c = util.lower(self.selected)
                if c == self.selected:
                    c = None

            if c:
                self.drawCharBox(dc, "Opposite case:", c, self.offset + 150,
                                 y + pad, 110)

            dc.SetFont(self.smallFont)
            dc.DrawText("Character code: %d" % code, 360, y + pad)

            if code == 32:
                dc.DrawText("Normal space", 360, y + pad + 30)
            elif code == 160:
                dc.DrawText("Non-breaking space", 360, y + pad + 30)

        else:
            dc.SetFont(self.smallFont)
            dc.DrawText("Click on a character to select it.", self.offset,
                        y + pad)

    def drawCharBox(self, dc, text, char, x, y, xinc):
        dc.SetFont(self.smallFont)
        dc.DrawText(text, x, y)

        boxX = x + xinc

        dc.DrawRectangle(boxX, y, self.boxSize, self.boxSize)

        dc.SetFont(self.bigFont)
        util.drawText(dc, char, boxX + self.boxSize // 2 + 1,
            y + self.boxSize // 2 + 1, util.ALIGN_CENTER, util.VALIGN_CENTER)

########NEW FILE########
__FILENAME__ = commandsdlg
import misc
import util

import xml.sax.saxutils as xss
import wx
import wx.html

class CommandsDlg(wx.Frame):
    def __init__(self, cfgGl):
        wx.Frame.__init__(self, None, -1, "Commands",
                          size = (650, 600), style = wx.DEFAULT_FRAME_STYLE)

        self.Center()

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vsizer)

        s = '<table border="1"><tr><td><b>Key(s)</b></td>'\
            '<td><b>Command</b></td></tr>'

        for cmd in cfgGl.commands:
            s += '<tr><td bgcolor="#dddddd" valign="top">'

            if cmd.keys:
                for key in cmd.keys:
                    k = util.Key.fromInt(key)
                    s += "%s<br>" % xss.escape(k.toStr())
            else:
                s += "No key defined<br>"

            s += '</td><td valign="top">'
            s += "%s" % xss.escape(cmd.desc)
            s += "</td></tr>"

        s += "</table>"

        self.html = """
<html><head></head><body>

%s

<pre>
<b>Mouse:</b>

Left click             Position cursor
Left click + drag      Select text
Right click            Unselect

<b>Keyboard shortcuts in Find/Replace dialog:</b>

F                      Find
R                      Replace
</pre>
</body></html>
        """ % s

        htmlWin = wx.html.HtmlWindow(self)
        rep = htmlWin.GetInternalRepresentation()
        rep.SetIndent(0, wx.html.HTML_INDENT_BOTTOM)
        htmlWin.SetPage(self.html)
        htmlWin.SetFocus()

        vsizer.Add(htmlWin, 1, wx.EXPAND)

        id = wx.NewId()
        menu = wx.Menu()
        menu.Append(id, "&Save as...")

        mb = wx.MenuBar()
        mb.Append(menu, "&File")
        self.SetMenuBar(mb)

        wx.EVT_MENU(self, id, self.OnSave)

        self.Layout()

        wx.EVT_CLOSE(self, self.OnCloseWindow)

    def OnCloseWindow(self, event):
        self.Destroy()

    def OnSave(self, event):
        dlg = wx.FileDialog(self, "Filename to save as",
            wildcard = "HTML files (*.html)|*.html|All files|*",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            util.writeToFile(dlg.GetPath(), self.html, self)

        dlg.Destroy()

########NEW FILE########
__FILENAME__ = config
# see fileformat.txt for more detailed information about the various
# defines found here.

from error import *
import misc
import mypickle
import pml
import screenplay
import util

import copy
import wx

# mapping from character to linebreak
_char2lb = {
    '>' : screenplay.LB_SPACE,
    '+' : screenplay.LB_SPACE2,
    '&' : screenplay.LB_NONE,
    '|' : screenplay.LB_FORCED,
    '.' : screenplay.LB_LAST
    }

# reverse to above
_lb2char = {}

# what string each linebreak type should be mapped to.
_lb2str = {
    screenplay.LB_SPACE  : " ",
    screenplay.LB_SPACE2 : "  ",
    screenplay.LB_NONE   : "",
    screenplay.LB_FORCED : "\n",
    screenplay.LB_LAST   : "\n"
    }

# contains a TypeInfo for each element type
_ti = []

# mapping from character to TypeInfo
_char2ti = {}

# mapping from line type to TypeInfo
_lt2ti = {}

# mapping from element name to TypeInfo
_name2ti = {}

# page break indicators. do not change these values as they're saved to
# the config file.
PBI_NONE = 0
PBI_REAL = 1
PBI_REAL_AND_UNADJ = 2

# for range checking above value
PBI_FIRST, PBI_LAST = PBI_NONE, PBI_REAL_AND_UNADJ

# constants for identifying PDFFontInfos
PDF_FONT_NORMAL = "Normal"
PDF_FONT_BOLD = "Bold"
PDF_FONT_ITALIC = "Italic"
PDF_FONT_BOLD_ITALIC = "Bold-Italic"

# scrolling  directions
SCROLL_UP = 0
SCROLL_DOWN = 1
SCROLL_CENTER = 2

# construct reverse lookup tables

for k, v in _char2lb.items():
    _lb2char[v] = k

del k, v

# non-changing information about an element type
class TypeInfo:
    def __init__(self, lt, char, name):

        # line type, e.g. screenplay.ACTION
        self.lt = lt

        # character used in saved scripts, e.g. "."
        self.char = char

        # textual name, e.g. "Action"
        self.name = name

# text type
class TextType:
    cvars = None

    def __init__(self):
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addBool("isCaps", False, "AllCaps")
            v.addBool("isBold", False, "Bold")
            v.addBool("isItalic", False, "Italic")
            v.addBool("isUnderlined", False, "Underlined")

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        self.cvars.load(vals, prefix, self)

# script-specific information about an element type
class Type:
    cvars = None

    def __init__(self, lt):

        # line type
        self.lt = lt

        # pointer to TypeInfo
        self.ti = lt2ti(lt)

        # text types, one for screen and one for export
        self.screen = TextType()
        self.export = TextType()

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # these two are how much empty space to insert a) before the
            # element b) between the element's lines, in units of line /
            # 10.
            v.addInt("beforeSpacing", 0, "BeforeSpacing", 0, 50)
            v.addInt("intraSpacing", 0, "IntraSpacing", 0, 20)

            v.addInt("indent", 0, "Indent", 0, 80)
            v.addInt("width", 5, "Width", 5, 80)

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        s = self.cvars.save(prefix, self)
        s += self.screen.save(prefix + "Screen/")
        s += self.export.save(prefix + "Export/")

        return s

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name

        self.cvars.load(vals, prefix, self)
        self.screen.load(vals, prefix + "Screen/")
        self.export.load(vals, prefix + "Export/")

# global information about an element type
class TypeGlobal:
    cvars = None

    def __init__(self, lt):

        # line type
        self.lt = lt

        # pointer to TypeInfo
        self.ti = lt2ti(lt)

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # what type of element to insert when user presses enter or tab.
            v.addElemName("newTypeEnter", screenplay.ACTION, "NewTypeEnter")
            v.addElemName("newTypeTab", screenplay.ACTION, "NewTypeTab")

            # what element to switch to when user hits tab / shift-tab.
            v.addElemName("nextTypeTab", screenplay.ACTION, "NextTypeTab")
            v.addElemName("prevTypeTab", screenplay.ACTION, "PrevTypeTab")

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name

        self.cvars.load(vals, prefix, self)

# command (an action in the main program)
class Command:
    cvars = None

    def __init__(self, name, desc, defKeys = [], isMovement = False,
                 isFixed = False, isMenu = False,
                 scrollDirection = SCROLL_CENTER):

        # name, e.g. "MoveLeft"
        self.name = name

        # textual description
        self.desc = desc

        # default keys (list of serialized util.Key objects (ints))
        self.defKeys = defKeys

        # is this a movement command
        self.isMovement = isMovement

        # some commands & their keys (Tab, Enter, Quit, etc) are fixed and
        # can't be changed
        self.isFixed = isFixed

        # is this a menu item
        self.isMenu = isMenu

        # which way the command wants to scroll the page
        self.scrollDirection = scrollDirection

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addList("keys", [], "Keys",
                      mypickle.IntVar("", 0, "", 0, 9223372036854775808L))

            v.makeDicts()

        # this is not actually needed but let's keep it for consistency
        self.__class__.cvars.setDefaults(self)

        self.keys = copy.deepcopy(self.defKeys)

    def save(self, prefix):
        if self.isFixed:
            return ""

        prefix += "%s/" % self.name

        if len(self.keys) > 0:
            return self.cvars.save(prefix, self)
        else:
            self.keys.append(0)
            s = self.cvars.save(prefix, self)
            self.keys = []

            return s

    def load(self, vals, prefix):
        if self.isFixed:
            return

        prefix += "%s/" % self.name

        tmp = copy.deepcopy(self.keys)
        self.cvars.load(vals, prefix, self)

        if len(self.keys) == 0:
            # we have a new command in the program not found in the old
            # config file
            self.keys = tmp
        elif self.keys[0] == 0:
            self.keys = []

        # weed out invalid bindings
        tmp2 = self.keys
        self.keys = []

        for k in tmp2:
            k2 = util.Key.fromInt(k)
            if not k2.isValidInputChar():
                self.keys.append(k)

# information about one screen font
class FontInfo:
    def __init__(self):
        self.font = None

        # font width and height
        self.fx = 1
        self.fy = 1

# information about one PDF font
class PDFFontInfo:
    cvars = None

    # list of characters not allowed in pdfNames
    invalidChars = None

    def __init__(self, name, style):
        # our name for the font (one of the PDF_FONT_* constants)
        self.name = name

        # 2 lowest bits of pml.TextOp.flags
        self.style = style

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # name to use in generated PDF file (CourierNew, MyFontBold,
            # etc.). if empty, use the default PDF Courier font.
            v.addStrLatin1("pdfName", "", "Name")

            # filename for the font to embed, or empty meaning don't
            # embed.
            v.addStrUnicode("filename", u"", "Filename")

            v.makeDicts()

            tmp = ""

            for i in range(256):
                # the OpenType font specification 1.4, of all places,
                # contains the most detailed discussion of characters
                # allowed in Postscript font names, in the section on
                # 'name' tables, describing name ID 6 (=Postscript name).
                if (i <= 32) or (i >= 127) or chr(i) in (
                    "[", "]", "(", ")", "{", "}", "<", ">", "/", "%"):
                    tmp += chr(i)

            self.__class__.invalidChars = tmp

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.name

        self.cvars.load(vals, prefix, self)

    # fix up invalid values.
    def refresh(self):
        self.pdfName = util.deleteChars(self.pdfName, self.invalidChars)

        # to avoid confused users not understanding why their embedded
        # font isn't working, put in an arbitrary font name if needed
        if self.filename and not self.pdfName:
            self.pdfName = "SampleFontName"

# per-script config, each script has its own one of these.
class Config:
    cvars = None

    def __init__(self):

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = Type
        self.types = { }

        # element types
        t = Type(screenplay.SCENE)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.screen.isBold = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.ACTION)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        self.types[t.lt] = t

        t = Type(screenplay.CHARACTER)
        t.beforeSpacing = 10
        t.indent = 22
        t.width = 38
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.DIALOGUE)
        t.indent = 10
        t.width = 35
        self.types[t.lt] = t

        t = Type(screenplay.PAREN)
        t.indent = 16
        t.width = 25
        self.types[t.lt] = t

        t = Type(screenplay.TRANSITION)
        t.beforeSpacing = 10
        t.indent = 45
        t.width = 20
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.SHOT)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.ACTBREAK)
        t.beforeSpacing = 10
        t.indent = 25
        t.width = 10
        t.screen.isCaps = True
        t.screen.isBold = True
        t.screen.isUnderlined = True
        t.export.isCaps = True
        t.export.isUnderlined = True
        self.types[t.lt] = t

        t = Type(screenplay.NOTE)
        t.beforeSpacing = 10
        t.indent = 5
        t.width = 55
        t.screen.isItalic = True
        t.export.isItalic = True
        self.types[t.lt] = t

        # pdf font configs, key = PDF_FONT_*, value = PdfFontInfo
        self.pdfFonts = { }

        for name, style in (
            (PDF_FONT_NORMAL, pml.COURIER),
            (PDF_FONT_BOLD, pml.COURIER | pml.BOLD),
            (PDF_FONT_ITALIC, pml.COURIER | pml.ITALIC),
            (PDF_FONT_BOLD_ITALIC, pml.COURIER | pml.BOLD | pml.ITALIC)):
            self.pdfFonts[name] = PDFFontInfo(name, style)

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()

        # font size used for PDF generation, in points
        v.addInt("fontSize", 12, "FontSize", 4, 72)

        # margins
        v.addFloat("marginBottom", 25.4, "Margin/Bottom", 0.0, 900.0)
        v.addFloat("marginLeft", 38.1, "Margin/Left", 0.0, 900.0)
        v.addFloat("marginRight", 25.4, "Margin/Right", 0.0, 900.0)
        v.addFloat("marginTop", 12.7, "Margin/Top", 0.0, 900.0)

        # paper size
        v.addFloat("paperHeight", 297.0, "Paper/Height", 100.0, 1000.0)
        v.addFloat("paperWidth", 210.0, "Paper/Width", 50.0, 1000.0)

        # leave at least this many action lines on the end of a page
        v.addInt("pbActionLines", 2, "PageBreakActionLines", 1, 30)

        # leave at least this many dialogue lines on the end of a page
        v.addInt("pbDialogueLines", 2, "PageBreakDialogueLines", 1, 30)

        # whether scene continueds are enabled
        v.addBool("sceneContinueds", False, "SceneContinueds")

        # scene continued text indent width
        v.addInt("sceneContinuedIndent", 45, "SceneContinuedIndent", -20, 80)

        # whether to include scene numbers
        v.addBool("pdfShowSceneNumbers", False, "ShowSceneNumbers")

        # whether to include PDF TOC
        v.addBool("pdfIncludeTOC", True, "IncludeTOC")

        # whether to show PDF TOC by default
        v.addBool("pdfShowTOC", True, "ShowTOC")

        # whether to open PDF document on current page
        v.addBool("pdfOpenOnCurrentPage", True, "OpenOnCurrentPage")

        # whether to remove Note elements in PDF output
        v.addBool("pdfRemoveNotes", False, "RemoveNotes")

        # whether to draw rectangles around the outlines of Note elements
        v.addBool("pdfOutlineNotes", True, "OutlineNotes")

        # whether to draw rectangle showing margins
        v.addBool("pdfShowMargins", False, "ShowMargins")

        # whether to show line numbers next to each line
        v.addBool("pdfShowLineNumbers", False, "ShowLineNumbers")

        # cursor position, line
        v.addInt("cursorLine", 0, "Cursor/Line", 0, 1000000)

        # cursor position, column
        v.addInt("cursorColumn", 0, "Cursor/Column", 0, 1000000)

        # various strings we add to the script
        v.addStrLatin1("strMore", "(MORE)", "String/MoreDialogue")
        v.addStrLatin1("strContinuedPageEnd", "(CONTINUED)",
                       "String/ContinuedPageEnd")
        v.addStrLatin1("strContinuedPageStart", "CONTINUED:",
                       "String/ContinuedPageStart")
        v.addStrLatin1("strDialogueContinued", " (cont'd)",
                       "String/DialogueContinued")

        v.makeDicts()

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.itervalues():
            t.load(vals, "Element/")

        for pf in self.pdfFonts.itervalues():
            pf.load(vals, "Font/")

        self.recalc()

    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.itervalues():
            s += t.save("Element/")

        for pf in self.pdfFonts.itervalues():
            s += pf.save("Font/")

        return s

    # fix up all invalid config values and recalculate all variables
    # dependent on other variables.
    #
    # if doAll is False, enforces restrictions only on a per-variable
    # basis, e.g. doesn't modify variable v2 based on v1's value. this is
    # useful when user is interactively modifying v1, and it temporarily
    # strays out of bounds (e.g. when deleting the old text in an entry
    # box, thus getting the minimum value), which would then possibly
    # modify the value of other variables which is not what we want.
    def recalc(self, doAll = True):
        for it in self.cvars.numeric.itervalues():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

        for el in self.types.itervalues():
            for it in el.cvars.numeric.itervalues():
                util.clampObj(el, it.name, it.minVal, it.maxVal)

        for it in self.cvars.stringLatin1.itervalues():
            setattr(self, it.name, util.toInputStr(getattr(self, it.name)))

        for pf in self.pdfFonts.itervalues():
            pf.refresh()

        # make sure usable space on the page isn't too small
        if doAll and (self.marginTop + self.marginBottom) >= \
               (self.paperHeight - 100.0):
            self.marginTop = 0.0
            self.marginBottom = 0.0

        h = self.paperHeight - self.marginTop - self.marginBottom

        # how many lines on a page
        self.linesOnPage = int(h / util.getTextHeight(self.fontSize))

    def getType(self, lt):
        return self.types[lt]

    # get a PDFFontInfo object for the given font type (PDF_FONT_*)
    def getPDFFont(self, fontType):
        return self.pdfFonts[fontType]

    # return a tuple of all the PDF font types
    def getPDFFontIds(self):
        return (PDF_FONT_NORMAL, PDF_FONT_BOLD, PDF_FONT_ITALIC,
                PDF_FONT_BOLD_ITALIC)

# global config. there is only ever one of these active.
class ConfigGlobal:
    cvars = None

    def __init__(self):

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = TypeGlobal
        self.types = { }

        # element types
        t = TypeGlobal(screenplay.SCENE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.TRANSITION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.ACTION)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.CHARACTER
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.CHARACTER)
        t.newTypeEnter = screenplay.DIALOGUE
        t.newTypeTab = screenplay.PAREN
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.ACTION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.DIALOGUE)
        t.newTypeEnter = screenplay.CHARACTER
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.PAREN
        t.prevTypeTab = screenplay.ACTION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.PAREN)
        t.newTypeEnter = screenplay.DIALOGUE
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.CHARACTER
        t.prevTypeTab = screenplay.DIALOGUE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.TRANSITION)
        t.newTypeEnter = screenplay.SCENE
        t.newTypeTab = screenplay.TRANSITION
        t.nextTypeTab = screenplay.SCENE
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.SHOT)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.SCENE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.ACTBREAK)
        t.newTypeEnter = screenplay.SCENE
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.SCENE
        t.prevTypeTab = screenplay.SCENE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.NOTE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        # keyboard commands. these must be in alphabetical order.
        self.commands = [
            Command("Abort", "Abort something, e.g. selection,"
                    " auto-completion, etc.", [wx.WXK_ESCAPE], isFixed = True),

            Command("About", "Show the about dialog.", isMenu = True),

            Command("AutoCompletionDlg", "Open the auto-completion dialog.",
                    isMenu = True),

            Command("ChangeToActBreak", "Change current element's style to"
                    " act break.",
                    [util.Key(ord("B"), alt = True).toInt()]),

            Command("ChangeToAction", "Change current element's style to"
                    " action.",
                    [util.Key(ord("A"), alt = True).toInt()]),

            Command("ChangeToCharacter", "Change current element's style to"
                    " character.",
                    [util.Key(ord("C"), alt = True).toInt()]),

            Command("ChangeToDialogue", "Change current element's style to"
                    " dialogue.",
                    [util.Key(ord("D"), alt = True).toInt()]),

            Command("ChangeToNote", "Change current element's style to note.",
                    [util.Key(ord("N"), alt = True).toInt()]),

            Command("ChangeToParenthetical", "Change current element's"
                    " style to parenthetical.",
                    [util.Key(ord("P"), alt = True).toInt()]),

            Command("ChangeToScene", "Change current element's style to"
                    " scene.",
                    [util.Key(ord("S"), alt = True).toInt()]),

            Command("ChangeToShot", "Change current element's style to"
                    " shot."),

            Command("ChangeToTransition", "Change current element's style to"
                    " transition.",
                    [util.Key(ord("T"), alt = True).toInt()]),

            Command("CharacterMap", "Open the character map.",
                    isMenu = True),

            Command("CloseScript", "Close the current script.",
                    [util.Key(23, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("CompareScripts", "Compare two scripts.", isMenu = True),

            Command("Copy", "Copy selected text to the internal clipboard.",
                    [util.Key(3, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("CopySystemCb", "Copy selected text to the system's"
                    " clipboard, unformatted.", isMenu = True),

            Command("CopySystemCbFormatted", "Copy selected text to the system's"
                    " clipboard, formatted.", isMenu = True),

            Command("Cut", "Cut selected text to internal clipboard.",
                    [util.Key(24, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Delete", "Delete the character under the cursor,"
                    " or selected text.", [wx.WXK_DELETE], isFixed = True),

            Command("DeleteBackward", "Delete the character behind the"
                    " cursor.", [wx.WXK_BACK, util.Key(wx.WXK_BACK, shift = True).toInt()], isFixed = True),

            Command("DeleteElements", "Open the 'Delete elements' dialog.",
                    isMenu = True),

            Command("ExportScript", "Export the current script.",
                    isMenu = True),

            Command("FindAndReplaceDlg", "Open the 'Find & Replace' dialog.",
                    [util.Key(6, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("FindNextError", "Find next error in the current script.",
                    [util.Key(5, ctrl = True).toInt()], isMenu = True),

            Command("ForcedLineBreak", "Insert a forced line break.",
                    [util.Key(wx.WXK_RETURN, ctrl = True).toInt(),
                     util.Key(wx.WXK_RETURN, shift = True).toInt(),

                     # CTRL+Enter under wxMSW
                     util.Key(10, ctrl = True).toInt()],
                    isFixed = True),

            Command("Fullscreen", "Toggle fullscreen.",
                    [util.Key(wx.WXK_F11).toInt()], isFixed = True,
                    isMenu = True),

            Command("GotoPage", "Goto to a given page.",
                    [util.Key(7, ctrl = True).toInt()], isFixed = True,
                    isMenu = True),

            Command("GotoScene", "Goto to a given scene.",
                    [util.Key(ord("G"), alt = True).toInt()], isFixed = True,
                    isMenu = True),

            Command("HeadersDlg", "Open the headers dialog.", isMenu = True),

            Command("HelpCommands", "Show list of commands and their key"
                    " bindings.", isMenu = True),

            Command("HelpManual", "Open the manual.", isMenu = True),

            Command("ImportScript", "Import a script.", isMenu = True),

            Command("InsertNbsp", "Insert non-breaking space.",
                    [util.Key(wx.WXK_SPACE, shift = True, ctrl = True).toInt()],
                    isMenu = True),

            Command("LoadScriptSettings", "Load script-specific settings.",
                    isMenu = True),

            Command("LoadSettings", "Load global settings.", isMenu = True),

            Command("LocationsDlg", "Open the locations dialog.",
                    isMenu = True),

            Command("MoveDown", "Move down.", [wx.WXK_DOWN], isMovement = True,
                    scrollDirection = SCROLL_DOWN),

            Command("MoveEndOfLine", "Move to the end of the line or"
                    " finish auto-completion.",
                    [wx.WXK_END], isMovement = True),

            Command("MoveEndOfScript", "Move to the end of the script.",
                    [util.Key(wx.WXK_END, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveLeft", "Move left.", [wx.WXK_LEFT], isMovement = True),

            Command("MovePageDown", "Move one page down.",
                    [wx.WXK_PAGEDOWN], isMovement = True),

            Command("MovePageUp", "Move one page up.",
                    [wx.WXK_PAGEUP], isMovement = True),

            Command("MoveRight", "Move right.", [wx.WXK_RIGHT],
                    isMovement = True),

            Command("MoveSceneDown", "Move one scene down.",
                    [util.Key(wx.WXK_DOWN, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveSceneUp", "Move one scene up.",
                    [util.Key(wx.WXK_UP, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveStartOfLine", "Move to the start of the line.",
                    [wx.WXK_HOME], isMovement = True),

            Command("MoveStartOfScript", "Move to the start of the"
                    " script.",
                    [util.Key(wx.WXK_HOME, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveUp", "Move up.", [wx.WXK_UP], isMovement = True,
                    scrollDirection = SCROLL_UP),

            Command("NameDatabase", "Open the character name database.",
                    isMenu = True),

            Command("NewElement", "Create a new element.", [wx.WXK_RETURN],
                    isFixed = True),

            Command("NewScript", "Create a new script.",
                    [util.Key(14, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("OpenScript", "Open a script.",
                    [util.Key(15, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Paginate", "Paginate current script.", isMenu = True),

            Command("Paste", "Paste text from the internal clipboard.",
                    [util.Key(22, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("PasteSystemCb", "Paste text from the system's"
                    " clipboard.", isMenu = True),

            Command("PrintScript", "Print current script.",
                    [util.Key(16, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Quit", "Quit the program.",
                    [util.Key(17, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Redo", "Redo a change that was reverted through undo.",
                    [util.Key(25, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("ReportCharacter", "Generate character report.",
                    isMenu = True),

            Command("ReportDialogueChart", "Generate dialogue chart report.",
                    isMenu = True),

            Command("ReportLocation", "Generate location report.",
                    isMenu = True),

            Command("ReportScene", "Generate scene report.",
                    isMenu = True),

            Command("ReportScript", "Generate script report.",
                    isMenu = True),

            Command("RevertScript", "Revert current script to the"
                    " version on disk.", isMenu = True),

            Command("SaveScript", "Save the current script.",
                    [util.Key(19, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("SaveScriptAs", "Save the current script to a new file.",
                    isMenu = True),

            Command("SaveScriptSettingsAs", "Save script-specific settings"
                    " to a new file.", isMenu = True),

            Command("SaveSettingsAs", "Save global settings to a new file.",
                    isMenu = True),

            Command("ScriptNext", "Change to next open script.",
                    [util.Key(wx.WXK_TAB, ctrl = True).toInt(),
                     util.Key(wx.WXK_PAGEDOWN, ctrl = True).toInt()],
                    isMenu = True),

            Command("ScriptPrev", "Change to previous open script.",
                    [util.Key(wx.WXK_TAB, shift = True, ctrl = True).toInt(),
                     util.Key(wx.WXK_PAGEUP, ctrl = True).toInt()],
                    isMenu = True),

            Command("ScriptSettings", "Change script-specific settings.",
                    isMenu = True),

            Command("SelectAll", "Select the entire script.", isMenu = True),

            Command("SelectScene", "Select the current scene.",
                    [util.Key(1, ctrl = True).toInt()], isMenu = True),

            Command("SetMark", "Set mark at current cursor position.",
                    [util.Key(wx.WXK_SPACE, ctrl = True).toInt()]),

            Command("Settings", "Change global settings.", isMenu = True),

            Command("SpellCheckerDictionaryDlg",
                    "Open the global spell checker dictionary dialog.",
                    isMenu = True),

            Command("SpellCheckerDlg","Spell check the script.",
                    [util.Key(wx.WXK_F8).toInt()], isMenu = True),

            Command("SpellCheckerScriptDictionaryDlg",
                    "Open the script-specific spell checker dictionary"
                    " dialog.",
                    isMenu = True),

            Command("Tab", "Change current element to the next style or"
                    " create a new element.", [wx.WXK_TAB], isFixed = True),

            Command("TabPrev", "Change current element to the previous"
                    " style.",
                    [util.Key(wx.WXK_TAB, shift = True).toInt()],
                    isFixed = True),

            Command("TitlesDlg", "Open the titles dialog.", isMenu = True),

            Command("ToggleShowFormatting", "Toggle 'Show formatting'"
                    " display.", isMenu = True),

            Command("Undo", "Undo the last change.",
                    [util.Key(26, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("ViewModeDraft", "Change view mode to draft.",
                    isMenu = True),

            Command("ViewModeLayout", "Change view mode to layout.",
                    isMenu = True),

            Command("ViewModeOverviewLarge", "Change view mode to large"
                    " overview.", isMenu = True),

            Command("ViewModeOverviewSmall", "Change view mode to small"
                    " overview.", isMenu = True),

            Command("ViewModeSideBySide", "Change view mode to side by"
                    " side.", isMenu = True),

            Command("Watermark", "Generate watermarked PDFs.",
                    isMenu = True),
            ]

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()

        # how many seconds to show splash screen for on startup (0 = disabled)
        v.addInt("splashTime", 2, "SplashTime", 0, 10)

        # vertical distance between rows, in pixels
        v.addInt("fontYdelta", 18, "FontYDelta", 4, 125)

        # how many lines to scroll per mouse wheel event
        v.addInt("mouseWheelLines", 4, "MouseWheelLines", 1, 50)

        # interval in seconds between automatic pagination (0 = disabled)
        v.addInt("paginateInterval", 1, "PaginateInterval", 0, 10)

        # whether to check script for errors before export / print
        v.addBool("checkOnExport", True, "CheckScriptForErrors")

        # whether to auto-capitalize start of sentences
        v.addBool("capitalize", True, "CapitalizeSentences")

        # whether to auto-capitalize i -> I
        v.addBool("capitalizeI", True, "CapitalizeI")

        # whether to open scripts on their last saved position
        v.addBool("honorSavedPos", True, "OpenScriptOnSavedPos")

        # whether to recenter screen when cursor moves out of it
        v.addBool("recenterOnScroll", False, "RecenterOnScroll")

        # whether to overwrite selected text on typing
        v.addBool("overwriteSelectionOnInsert", True, "OverwriteSelectionOnInsert")

        # whether to use per-elem-type colors (textSceneColor etc.)
        # instead of using textColor for all elem types
        v.addBool("useCustomElemColors", False, "UseCustomElemColors")

        # page break indicators to show
        v.addInt("pbi", PBI_REAL, "PageBreakIndicators", PBI_FIRST,
                    PBI_LAST)

        # PDF viewer program and args. defaults are empty since generating
        # them is a complex process handled by findPDFViewer.
        v.addStrUnicode("pdfViewerPath", u"", "PDF/ViewerPath")
        v.addStrBinary("pdfViewerArgs", "", "PDF/ViewerArguments")

        # fonts. real defaults are set in setDefaultFonts.
        v.addStrBinary("fontNormal", "", "FontNormal")
        v.addStrBinary("fontBold", "", "FontBold")
        v.addStrBinary("fontItalic", "", "FontItalic")
        v.addStrBinary("fontBoldItalic", "", "FontBoldItalic")

        # default script directory
        v.addStrUnicode("scriptDir", misc.progPath, "DefaultScriptDirectory")

        # colors
        v.addColor("text", 0, 0, 0, "TextFG", "Text foreground")
        v.addColor("textHdr", 128, 128, 128, "TextHeadersFG",
                   "Text foreground (headers)")
        v.addColor("textBg", 255, 255, 255, "TextBG", "Text background")
        v.addColor("workspace", 237, 237, 237, "Workspace", "Workspace")
        v.addColor("pageBorder", 202, 202, 202, "PageBorder", "Page border")
        v.addColor("pageShadow", 153, 153, 153, "PageShadow", "Page shadow")
        v.addColor("selected", 200, 200, 200, "Selected", "Selection")
        v.addColor("cursor", 135, 135, 253, "Cursor", "Cursor")
        v.addColor("autoCompFg", 0, 0, 0, "AutoCompletionFG",
                   "Auto-completion foreground")
        v.addColor("autoCompBg", 255, 240, 168, "AutoCompletionBG",
                   "Auto-completion background")
        v.addColor("note", 255, 237, 223, "ScriptNote", "Script note")
        v.addColor("pagebreak", 221, 221, 221, "PageBreakLine",
                   "Page-break line")
        v.addColor("pagebreakNoAdjust", 221, 221, 221,
                   "PageBreakNoAdjustLine",
                   "Page-break (original, not adjusted) line")

        v.addColor("tabText", 50, 50, 50, "TabText", "Tab text")
        v.addColor("tabBorder", 202, 202, 202, "TabBorder",
                   "Tab border")
        v.addColor("tabBarBg", 221, 217, 215, "TabBarBG",
                   "Tab bar background")
        v.addColor("tabNonActiveBg", 180, 180, 180, "TabNonActiveBg", "Tab, non-active")

        for t in getTIs():
            v.addColor("text%s" % t.name, 0, 0, 0, "Text%sFG" % t.name,
                       "Text foreground for %s" % t.name)

        v.makeDicts()

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.itervalues():
            t.load(vals, "Element/")

        for cmd in self.commands:
            cmd.load(vals, "Command/")

        self.recalc()

    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.itervalues():
            s += t.save("Element/")

        for cmd in self.commands:
            s += cmd.save("Command/")

        return s

    # fix up all invalid config values.
    def recalc(self):
        for it in self.cvars.numeric.itervalues():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

    def getType(self, lt):
        return self.types[lt]

    # add SHIFT+Key alias for all keys bound to movement commands, so
    # selection-movement works.
    def addShiftKeys(self):
        for cmd in self.commands:
            if cmd.isMovement:
                nk = []

                for key in cmd.keys:
                    k = util.Key.fromInt(key)
                    k.shift = True
                    ki = k.toInt()

                    if ki not in cmd.keys:
                        nk.append(ki)

                cmd.keys.extend(nk)

    # remove key (int) from given cmd
    def removeKey(self, cmd, key):
        cmd.keys.remove(key)

        if cmd.isMovement:
            k = util.Key.fromInt(key)
            k.shift = True
            ki = k.toInt()

            if ki in cmd.keys:
                cmd.keys.remove(ki)

    # get textual description of conflicting keys, or None if no
    # conflicts.
    def getConflictingKeys(self):
        keys = {}

        for cmd in self.commands:
            for key in cmd.keys:
                if key in keys:
                    keys[key].append(cmd.name)
                else:
                    keys[key] = [cmd.name]

        s = ""
        for k, v in keys.iteritems():
            if len(v) > 1:
                s += "%s:" % util.Key.fromInt(k).toStr()

                for cmd in v:
                    s += " %s" % cmd

                s += "\n"

        if s == "":
            return None
        else:
            return s

    # set default values that vary depending on platform, wxWidgets
    # version, etc. this is not at the end of __init__ because
    # non-interactive uses have no needs for these.
    def setDefaults(self):
        # check keyboard commands are listed in correct order
        commands = [cmd.name for cmd in self.commands]
        commandsSorted = sorted(commands)

        if commands != commandsSorted:
            # for i in range(len(commands)):
            #     if commands[i] != commandsSorted[i]:
            #         print "Got: %s Expected: %s" % (commands[i], commandsSorted[i])

            # if you get this error, you've put a new command you've added
            # in an incorrect place in the command list. uncomment the
            # above lines to figure out where it should be.
            raise ConfigError("Commands not listed in correct order")

        self.setDefaultFonts()
        self.findPDFViewer()

    # set default fonts
    def setDefaultFonts(self):
        fn = ["", "", "", ""]

        if misc.isUnix:
            fn[0] = "Monospace 12"
            fn[1] = "Monospace Bold 12"
            fn[2] = "Monospace Italic 12"
            fn[3] = "Monospace Bold Italic 12"

        elif misc.isWindows:
                fn[0] = "0;-13;0;0;0;400;0;0;0;0;3;2;1;49;Courier New"
                fn[1] = "0;-13;0;0;0;700;0;0;0;0;3;2;1;49;Courier New"
                fn[2] = "0;-13;0;0;0;400;255;0;0;0;3;2;1;49;Courier New"
                fn[3] = "0;-13;0;0;0;700;255;0;0;0;3;2;1;49;Courier New"

        else:
            raise ConfigError("Unknown platform")

        self.fontNormal = fn[0]
        self.fontBold = fn[1]
        self.fontItalic = fn[2]
        self.fontBoldItalic = fn[3]

    # set PDF viewer program to the best one found on the machine.
    def findPDFViewer(self):
        # list of programs to look for. each item is of the form (name,
        # args). if name is an absolute path only that exact location is
        # looked at, otherwise PATH is searched for the program (on
        # Windows, all paths are interpreted as absolute). args is the
        # list of arguments for the program.
        progs = []

        if misc.isUnix:
            progs = [
                (u"/usr/local/Adobe/Acrobat7.0/bin/acroread", "-tempFile"),
                (u"acroread", "-tempFile"),
                (u"xpdf", ""),
                (u"evince", ""),
                (u"gpdf", ""),
                (u"kpdf", ""),
                (u"okular", ""),
                ]
        elif misc.isWindows:
            # get value via registry if possible, or fallback to old method.
            viewer = util.getWindowsPDFViewer()

            if viewer:
                self.pdfViewerPath = viewer
                self.pdfViewerArgs = ""

                return

            progs = [
                (ur"C:\Program Files\Adobe\Reader 11.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Reader 10.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Reader 9.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Reader 8.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 7.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 6.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 5.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 4.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Foxit Software\Foxit Reader\Foxit Reader.exe",
                 ""),
                ]
        else:
            pass

        success = False

        for name, args in progs:
            if misc.isWindows or (name[0] == u"/"):
                if util.fileExists(name):
                    success = True

                    break
            else:
                name = util.findFileInPath(name)

                if name:
                    success = True

                    break

        if success:
            self.pdfViewerPath = name
            self.pdfViewerArgs = args

# config stuff that are wxwindows objects, so can't be in normal
# ConfigGlobal (deepcopy dies)
class ConfigGui:

    # constants
    constantsInited = False
    bluePen = None
    redColor = None
    blackColor = None

    def __init__(self, cfgGl):

        if not ConfigGui.constantsInited:
            ConfigGui.bluePen = wx.Pen(wx.Colour(0, 0, 255))
            ConfigGui.redColor = wx.Colour(255, 0, 0)
            ConfigGui.blackColor = wx.Colour(0, 0, 0)

            ConfigGui.constantsInited = True

        # convert cfgGl.MyColor -> cfgGui.wx.Colour
        for it in cfgGl.cvars.color.itervalues():
            c = getattr(cfgGl, it.name)
            tmp = wx.Colour(c.r, c.g, c.b)
            setattr(self, it.name, tmp)

        # key = line type, value = wx.Colour
        self._lt2textColor = {}

        for t in getTIs():
            self._lt2textColor[t.lt] = getattr(self, "text%sColor" % t.name)

        self.textPen = wx.Pen(self.textColor)
        self.textHdrPen = wx.Pen(self.textHdrColor)

        self.workspaceBrush = wx.Brush(self.workspaceColor)
        self.workspacePen = wx.Pen(self.workspaceColor)

        self.textBgBrush = wx.Brush(self.textBgColor)
        self.textBgPen = wx.Pen(self.textBgColor)

        self.pageBorderPen = wx.Pen(self.pageBorderColor)
        self.pageShadowPen = wx.Pen(self.pageShadowColor)

        self.selectedBrush = wx.Brush(self.selectedColor)
        self.selectedPen = wx.Pen(self.selectedColor)

        self.cursorBrush = wx.Brush(self.cursorColor)
        self.cursorPen = wx.Pen(self.cursorColor)

        self.noteBrush = wx.Brush(self.noteColor)
        self.notePen = wx.Pen(self.noteColor)

        self.autoCompPen = wx.Pen(self.autoCompFgColor)
        self.autoCompBrush = wx.Brush(self.autoCompBgColor)
        self.autoCompRevPen = wx.Pen(self.autoCompBgColor)
        self.autoCompRevBrush = wx.Brush(self.autoCompFgColor)

        self.pagebreakPen = wx.Pen(self.pagebreakColor)
        self.pagebreakNoAdjustPen = wx.Pen(self.pagebreakNoAdjustColor,
                                           style = wx.DOT)

        self.tabTextPen = wx.Pen(self.tabTextColor)
        self.tabBorderPen = wx.Pen(self.tabBorderColor)

        self.tabBarBgBrush = wx.Brush(self.tabBarBgColor)
        self.tabBarBgPen = wx.Pen(self.tabBarBgColor)

        self.tabNonActiveBgBrush = wx.Brush(self.tabNonActiveBgColor)
        self.tabNonActiveBgPen = wx.Pen(self.tabNonActiveBgColor)

        # a 4-item list of FontInfo objects, indexed by the two lowest
        # bits of pml.TextOp.flags.
        self.fonts = []

        for fname in ["fontNormal", "fontBold", "fontItalic",
                      "fontBoldItalic"]:
            fi = FontInfo()

            s = getattr(cfgGl, fname)

            # evil users can set the font name to empty by modifying the
            # config file, and some wxWidgets ports crash hard when trying
            # to create a font from an empty string, so we must guard
            # against that.
            if s:
                nfi = wx.NativeFontInfo()
                nfi.FromString(s)
                nfi.SetEncoding(wx.FONTENCODING_ISO8859_1)

                fi.font = wx.FontFromNativeInfo(nfi)

                # likewise, evil users can set the font name to "z" or
                # something equally silly, resulting in an
                # invalid/non-existent font. on wxGTK2 and wxMSW we can
                # detect this by checking the point size of the font.
                # wxGTK1 chooses some weird chinese font and I can't find
                # a way to detect that, but it's irrelevant since we'll
                # rip out support for it in a few months.
                if fi.font.GetPointSize() == 0:
                    fi.font = None

            # if either of the above failures happened, create a dummy
            # font and use it. this sucks but is preferable to crashing or
            # displaying an empty screen.
            if not fi.font:
                fi.font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL,
                                  encoding = wx.FONTENCODING_ISO8859_1)
                setattr(cfgGl, fname, fi.font.GetNativeFontInfo().ToString())

            fx, fy = util.getTextExtent(fi.font, "O")

            fi.fx = max(1, fx)
            fi.fy = max(1, fy)

            self.fonts.append(fi)

    # TextType -> FontInfo
    def tt2fi(self, tt):
        return self.fonts[tt.isBold | (tt.isItalic << 1)]

    # line type -> wx.Colour
    def lt2textColor(self, lt):
        return self._lt2textColor[lt]

def _conv(dict, key, raiseException = True):
    val = dict.get(key)
    if (val == None) and raiseException:
        raise ConfigError("key '%s' not found from '%s'" % (key, dict))

    return val

# get TypeInfos
def getTIs():
    return _ti

def char2lb(char, raiseException = True):
    return _conv(_char2lb, char, raiseException)

def lb2char(lb):
    return _conv(_lb2char, lb)

def lb2str(lb):
    return _conv(_lb2str, lb)

def char2lt(char, raiseException = True):
    ti = _conv(_char2ti, char, raiseException)

    if ti:
        return ti.lt
    else:
        return None

def lt2char(lt):
    return _conv(_lt2ti, lt).char

def name2ti(name, raiseException = True):
    return _conv(_name2ti, name, raiseException)

def lt2ti(lt):
    return _conv(_lt2ti, lt)

def _init():

    for lt, char, name in (
        (screenplay.SCENE,      "\\", "Scene"),
        (screenplay.ACTION,     ".",  "Action"),
        (screenplay.CHARACTER,  "_",  "Character"),
        (screenplay.DIALOGUE,   ":",  "Dialogue"),
        (screenplay.PAREN,      "(",  "Parenthetical"),
        (screenplay.TRANSITION, "/",  "Transition"),
        (screenplay.SHOT,       "=",  "Shot"),
        (screenplay.ACTBREAK,   "@",  "Act break"),
        (screenplay.NOTE,       "%",  "Note")
        ):

        ti = TypeInfo(lt, char, name)

        _ti.append(ti)
        _lt2ti[lt] = ti
        _char2ti[char] = ti
        _name2ti[name] = ti

_init()

########NEW FILE########
__FILENAME__ = dialoguechart
import gutil
import misc
import pdf
import pml
import screenplay
import util

import wx

def genDialogueChart(mainFrame, sp):
    # TODO: would be nice if this behaved like the other reports, i.e. the
    # junk below would be inside the class, not outside. this would allow
    # testcases to be written. only complication is the minLines thing
    # which would need some thinking.

    inf = []
    for it in [ ("Characters with < 10 lines", None),
                ("Sorted by: First appearance", cmpFirst),
                ("Sorted by: Last appearance", cmpLast),
                ("Sorted by: Number of lines spoken", cmpCount),
                ("Sorted by: Name", cmpName)
                ]:
        inf.append(misc.CheckBoxItem(it[0], cdata = it[1]))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", inf,
                           "Information to include:", False)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()

        return

    dlg.Destroy()

    minLines = 1
    if not inf[0].selected:
        minLines = 10

    chart = DialogueChart(sp, minLines)

    if not chart.cinfo:
        wx.MessageBox("No characters speaking found.", "Error", wx.OK,
                      mainFrame)

        return

    del inf[0]

    if len(misc.CheckBoxItem.getClientData(inf)) == 0:
        wx.MessageBox("Can't disable all output.", "Error", wx.OK,
                      mainFrame)

        return

    data = chart.generate(inf)

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

class DialogueChart:
    def __init__(self, sp, minLines):

        self.sp = sp

        ls = sp.lines

        # PageInfo's for each page, 0-indexed.
        self.pages = []

        for i in xrange(len(sp.pages) - 1):
            self.pages.append(PageInfo())

        # map of CharInfo objects. key = name, value = CharInfo.
        tmpCinfo = {}

        name = "UNKNOWN"

        for i in xrange(len(ls)):
            pgNr = sp.line2page(i) -1
            pi = self.pages[pgNr]
            line = ls[i]

            pi.addLine(line.lt)

            if (line.lt == screenplay.CHARACTER) and\
                   (line.lb == screenplay.LB_LAST):
                name = util.upper(line.text)

            elif line.lt == screenplay.DIALOGUE:
                pi.addLineToSpeaker(name)

                ci = tmpCinfo.get(name)

                if ci:
                    ci.addLine(pgNr)
                else:
                    tmpCinfo[name] = CharInfo(name, pgNr)

            elif line.lt != screenplay.PAREN:
                name = "UNKNOWN"

        # CharInfo's.
        self.cinfo = []
        for v in tmpCinfo.values():
            if v.lineCnt >= minLines:
                self.cinfo.append(v)

        # start Y of page markers
        self.pageY = 20.0

        # where dialogue density bars start and how tall they are
        self.barY = 30.0
        self.barHeight = 15.0

        # chart Y pos
        self.chartY = 50.0

        # how much to leave empty on each side (mm)
        self.margin = 10.0

        # try point sizes 10,9,8,7,6 until all characters fit on the page
        # (if 6 is still too big, too bad)
        size = 10
        while 1:
            # character font size in points
            self.charFs = size

            # how many mm in Y direction for each character
            self.charY = util.getTextHeight(self.charFs)

            # height of chart
            self.chartHeight = len(self.cinfo) * self.charY

            if size <= 6:
                break

            if (self.chartY + self.chartHeight) <= \
                   (sp.cfg.paperWidth - self.margin):
                break

            size -= 1

        # calculate maximum length of character name, and start position
        # of chart from that

        maxLen = 0
        for ci in self.cinfo:
            maxLen = max(maxLen, len(ci.name))
        maxLen = max(10, maxLen)

        charX = util.getTextWidth(" ", pml.COURIER, self.charFs)

        # chart X pos
        self.chartX = self.margin + maxLen * charX + 3

        # width of chart
        self.chartWidth = sp.cfg.paperHeight - self.chartX - self.margin

        # page contents bar legends' size and position
        self.legendWidth = 23.0
        self.legendHeight = 23.0
        self.legendX = self.margin + 2.0
        self.legendY = self.barY + self.barHeight - self.legendHeight

        # margin from legend border to first item
        self.legendMargin = 2.0

        # spacing from one legend item to next
        self.legendSpacing = 5.0

        # spacing from one legend item to next
        self.legendSize = 4.0

    def generate(self, cbil):
        doc = pml.Document(self.sp.cfg.paperHeight,
                           self.sp.cfg.paperWidth)

        for it in cbil:
            if it.selected:
                self.cinfo.sort(it.cdata)
                doc.add(self.generatePage(it.text, doc))

        return pdf.generate(doc)

    def generatePage(self, title, doc):
        pg = pml.Page(doc)

        pg.add(pml.TextOp(title, doc.w / 2.0, self.margin, 18,
            pml.BOLD | pml.ITALIC | pml.UNDERLINED, util.ALIGN_CENTER))

        pageCnt = len(self.pages)
        mmPerPage = max(0.1, self.chartWidth / pageCnt)

        pg.add(pml.TextOp("Page:", self.chartX - 1.0, self.pageY - 5.0, 10))

        # draw backround for every other row. this needs to be done before
        # drawing the grid.
        for i in range(len(self.cinfo)):
            y = self.chartY + i * self.charY

            if (i % 2) == 1:
                pg.add(pml.PDFOp("0.93 g"))
                pg.add(pml.RectOp(self.chartX, y, self.chartWidth,
                                  self.charY))
                pg.add(pml.PDFOp("0.0 g"))

        # line width to use
        lw = 0.25

        pg.add(pml.PDFOp("0.5 G"))

        # dashed pattern
        pg.add(pml.PDFOp("[2 2] 0 d"))

        # draw grid and page markers
        for i in xrange(pageCnt):
            if (i == 0) or ((i + 1) % 10) == 0:
                x = self.chartX + i * mmPerPage
                pg.add(pml.TextOp("%d" % (i + 1), x, self.pageY,
                                  10, align = util.ALIGN_CENTER))
                if i != 0:
                    pg.add(pml.genLine(x, self.chartY, 0, self.chartHeight,
                                        lw))


        pg.add(pml.RectOp(self.chartX, self.chartY, self.chartWidth,
                          self.chartHeight, pml.NO_FILL, lw))

        pg.add(pml.PDFOp("0.0 G"))

        # restore normal line pattern
        pg.add(pml.PDFOp("[] 0 d"))

        # legend for page content bars
        pg.add(pml.RectOp(self.legendX, self.legendY,
            self.legendWidth, self.legendHeight, pml.NO_FILL, lw))

        self.drawLegend(pg, 0, 1.0, "Other", lw)
        self.drawLegend(pg, 1, 0.7, "Character", lw)
        self.drawLegend(pg, 2, 0.5, "Dialogue", lw)
        self.drawLegend(pg, 3, 0.3, "Action", lw)

        # page content bars
        for i in xrange(pageCnt):
            x = self.chartX + i * mmPerPage
            y = self.barY + self.barHeight
            pi = self.pages[i]
            tlc = pi.getTotalLineCount()

            pg.add(pml.PDFOp("0.3 g"))
            pct = util.safeDivInt(pi.getLineCount(screenplay.ACTION), tlc)
            barH = self.barHeight * pct
            pg.add(pml.RectOp(x, y - barH, mmPerPage, barH))
            y -= barH

            pg.add(pml.PDFOp("0.5 g"))
            pct = util.safeDivInt(pi.getLineCount(screenplay.DIALOGUE), tlc)
            barH = self.barHeight * pct
            pg.add(pml.RectOp(x, y - barH, mmPerPage, barH))
            y -= barH

            pg.add(pml.PDFOp("0.7 g"))
            pct = util.safeDivInt(pi.getLineCount(screenplay.CHARACTER), tlc)
            barH = self.barHeight * pct
            pg.add(pml.RectOp(x, y - barH, mmPerPage, barH))
            y -= barH


        pg.add(pml.PDFOp("0.0 g"))

        # rectangle around page content bars
        pg.add(pml.RectOp(self.chartX, self.barY, self.chartWidth,
                         self.barHeight, pml.NO_FILL, lw))

        for i in range(len(self.cinfo)):
            y = self.chartY + i * self.charY
            ci = self.cinfo[i]

            pg.add(pml.TextOp(ci.name, self.margin, y + self.charY / 2.0,
                self.charFs, valign = util.VALIGN_CENTER))

            for i in xrange(pageCnt):
                pi = self.pages[i]
                cnt = pi.getSpeakerLineCount(ci.name)

                if cnt > 0:
                    h = self.charY * (float(cnt) / self.sp.cfg.linesOnPage)

                    pg.add(pml.RectOp(self.chartX + i * mmPerPage,
                        y + (self.charY - h) / 2.0, mmPerPage, h))

        return pg

    # draw a single legend for page content bars
    def drawLegend(self, pg, pos, color, name, lw):
        x = self.legendX + self.legendMargin
        y = self.legendY + self.legendMargin + pos * self.legendSpacing

        pg.add(pml.PDFOp("%f g" % color))

        pg.add(pml.RectOp(x, y, self.legendSize, self.legendSize,
                          pml.STROKE_FILL, lw))

        pg.add(pml.PDFOp("0.0 g"))

        pg.add(pml.TextOp(name, x + self.legendSize + 2.0, y, 6))


# keeps track of information for one page
class PageInfo:
    def __init__(self):
        # how many lines of each type this page contains. key = line type,
        # value = int. note that if value would be 0, this doesn't have
        # the key at all, so use the helper functions below.
        self.lineCounts = {}

        # total line count
        self.totalLineCount = -1

        # how many lines each character speaks on this page. key =
        # character name, value = int. note that if someone doesn't speak
        # they have no entry.
        self.speakers = {}

    # add one line of given type.
    def addLine(self, lt):
        self.lineCounts[lt] = self.getLineCount(lt) + 1

    # get number of lines of given type.
    def getLineCount(self, lt):
        return self.lineCounts.get(lt, 0)

    # get total number of lines.
    def getTotalLineCount(self):
        if self.totalLineCount == -1:
            self.totalLineCount = sum(self.lineCounts.itervalues(), 0)

        return self.totalLineCount

    # get number of lines of given type.
    def getLineCount(self, lt):
        return self.lineCounts.get(lt, 0)

    # add one dialogue line for given speaker.
    def addLineToSpeaker(self, name):
        self.speakers[name] = self.getSpeakerLineCount(name) + 1

    # get number of lines of dialogue for given character.
    def getSpeakerLineCount(self, name):
        return self.speakers.get(name, 0)

# keeps track of each character's dialogue lines.
class CharInfo:
    def __init__(self, name, firstPage):
        self.name = name
        self.firstPage = firstPage
        self.lastPage = firstPage
        self.lineCnt = 1

    # add a line at given page.
    def addLine(self, page):
        self.lastPage = page
        self.lineCnt += 1

def cmpCount(c1, c2):
    ret = cmp(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmpFirst(c1, c2)

def cmpCountThenName(c1, c2):
    ret = cmp(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)

def cmpFirst(c1, c2):
    ret = cmp(c1.firstPage, c2.firstPage)

    if ret != 0:
        return ret
    else:
        return cmpLastRev(c1, c2)

def cmpLast(c1, c2):
    ret = cmp(c1.lastPage, c2.lastPage)

    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)

def cmpLastRev(c1, c2):
    ret = cmp(c2.lastPage, c1.lastPage)

    if ret != 0:
        return ret
    else:
        return cmpCountThenName(c1, c2)

def cmpName(c1, c2):
    return cmp(c1.name, c2.name)

########NEW FILE########
__FILENAME__ = error
# exception classes

class TrelbyError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

class ConfigError(TrelbyError):
    def __init__(self, msg):
        TrelbyError.__init__(self, msg)

class MiscError(TrelbyError):
    def __init__(self, msg):
        TrelbyError.__init__(self, msg)

########NEW FILE########
__FILENAME__ = finddlg
import config
import gutil
import misc
import undo
import util

import wx

class FindDlg(wx.Dialog):
    def __init__(self, parent, ctrl):
        wx.Dialog.__init__(self, parent, -1, "Find & Replace",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.WANTS_CHARS)

        self.ctrl = ctrl

        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(2, 2, 5, 20)
        gsizer.AddGrowableCol(1)

        gsizer.Add(wx.StaticText(self, -1, "Find what:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.findEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        gsizer.Add(self.findEntry, 0, wx.EXPAND)

        gsizer.Add(wx.StaticText(self, -1, "Replace with:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.replaceEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        gsizer.Add(self.replaceEntry, 0, wx.EXPAND)

        vsizer.Add(gsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.matchWholeCb = wx.CheckBox(self, -1, "Match whole word only")
        vsizer2.Add(self.matchWholeCb, 0, wx.TOP, pad)

        self.matchCaseCb = wx.CheckBox(self, -1, "Match case")
        vsizer2.Add(self.matchCaseCb, 0, wx.TOP, pad)

        hsizer2.Add(vsizer2, 0, wx.EXPAND | wx.RIGHT, 10)

        self.direction = wx.RadioBox(self, -1, "Direction",
                                    choices = ["Up", "Down"])
        self.direction.SetSelection(1)

        hsizer2.Add(self.direction, 1, 0)

        vsizer.Add(hsizer2, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.extraLabel = wx.StaticText(self, -1, "Search in:")
        vsizer.Add(self.extraLabel)

        self.elements = wx.CheckListBox(self, -1)

        # sucky wxMSW doesn't support client data for checklistbox items,
        # so we have to store it ourselves
        self.elementTypes = []

        for t in config.getTIs():
            self.elements.Append(t.name)
            self.elementTypes.append(t.lt)

        vsizer.Add(self.elements, 1, wx.EXPAND)

        hsizer.Add(vsizer, 1, wx.EXPAND)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        find = wx.Button(self, -1, "&Find next")
        vsizer.Add(find, 0, wx.EXPAND | wx.BOTTOM, 5)

        replace = wx.Button(self, -1, "&Replace")
        vsizer.Add(replace, 0, wx.EXPAND | wx.BOTTOM, 5)

        replaceAll = wx.Button(self, -1, " Replace all ")
        vsizer.Add(replaceAll, 0, wx.EXPAND | wx.BOTTOM, 5)

        self.moreButton = wx.Button(self, -1, "")
        vsizer.Add(self.moreButton, 0, wx.EXPAND | wx.BOTTOM, 5)

        hsizer.Add(vsizer, 0, wx.EXPAND | wx.LEFT, 30)

        wx.EVT_BUTTON(self, find.GetId(), self.OnFind)
        wx.EVT_BUTTON(self, replace.GetId(), self.OnReplace)
        wx.EVT_BUTTON(self, replaceAll.GetId(), self.OnReplaceAll)
        wx.EVT_BUTTON(self, self.moreButton.GetId(), self.OnMore)

        gutil.btnDblClick(find, self.OnFind)
        gutil.btnDblClick(replace, self.OnReplace)

        wx.EVT_TEXT(self, self.findEntry.GetId(), self.OnText)

        wx.EVT_TEXT_ENTER(self, self.findEntry.GetId(), self.OnFind)
        wx.EVT_TEXT_ENTER(self, self.replaceEntry.GetId(), self.OnFind)

        wx.EVT_CHAR(self, self.OnCharMisc)
        wx.EVT_CHAR(self.findEntry, self.OnCharEntry)
        wx.EVT_CHAR(self.replaceEntry, self.OnCharEntry)
        wx.EVT_CHAR(find, self.OnCharButton)
        wx.EVT_CHAR(replace, self.OnCharButton)
        wx.EVT_CHAR(replaceAll, self.OnCharButton)
        wx.EVT_CHAR(self.moreButton, self.OnCharButton)
        wx.EVT_CHAR(self.matchWholeCb, self.OnCharMisc)
        wx.EVT_CHAR(self.matchCaseCb, self.OnCharMisc)
        wx.EVT_CHAR(self.direction, self.OnCharMisc)
        wx.EVT_CHAR(self.elements, self.OnCharMisc)

        util.finishWindow(self, hsizer, center = False)

        self.loadState()
        self.findEntry.SetFocus()

    def loadState(self):
        self.findEntry.SetValue(self.ctrl.findDlgFindText)
        self.findEntry.SetSelection(-1, -1)

        self.replaceEntry.SetValue(self.ctrl.findDlgReplaceText)

        self.matchWholeCb.SetValue(self.ctrl.findDlgMatchWholeWord)
        self.matchCaseCb.SetValue(self.ctrl.findDlgMatchCase)

        self.direction.SetSelection(int(not self.ctrl.findDlgDirUp))

        count = self.elements.GetCount()
        tmp = self.ctrl.findDlgElements

        if (tmp == None) or (len(tmp) != count):
            tmp = [True] * self.elements.GetCount()

        for i in range(count):
            self.elements.Check(i, tmp[i])

        self.showExtra(self.ctrl.findDlgUseExtra)
        self.Center()

    def saveState(self):
        self.getParams()

        self.ctrl.findDlgFindText = misc.fromGUI(self.findEntry.GetValue())
        self.ctrl.findDlgReplaceText = misc.fromGUI(
            self.replaceEntry.GetValue())
        self.ctrl.findDlgMatchWholeWord = self.matchWhole
        self.ctrl.findDlgMatchCase = self.matchCase
        self.ctrl.findDlgDirUp = self.dirUp
        self.ctrl.findDlgUseExtra = self.useExtra

        tmp = []
        for i in range(self.elements.GetCount()):
            tmp.append(bool(self.elements.IsChecked(i)))

        self.ctrl.findDlgElements = tmp

    def OnMore(self, event):
        self.showExtra(not self.useExtra)

    def OnText(self, event):
        if self.ctrl.sp.mark:
            self.ctrl.sp.clearMark()
            self.ctrl.updateScreen()

    def OnCharEntry(self, event):
        self.OnChar(event, True, False)

    def OnCharButton(self, event):
        self.OnChar(event, False, True)

    def OnCharMisc(self, event):
        self.OnChar(event, False, False)

    def OnChar(self, event, isEntry, isButton):
        kc = event.GetKeyCode()

        if kc == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_OK)
            return

        if kc == wx.WXK_RETURN:
            if isButton:
                event.Skip()
                return
            else:
                self.OnFind()
                return

        if isEntry:
            event.Skip()
        else:
            if kc < 256:
                if chr(kc) == "f":
                    self.OnFind()
                elif chr(kc) == "r":
                    self.OnReplace()
                else:
                    event.Skip()
            else:
                event.Skip()

    def showExtra(self, flag):
        self.extraLabel.Show(flag)
        self.elements.Show(flag)

        self.useExtra = flag

        if flag:
            self.moreButton.SetLabel("<<< Less")
            pos = self.elements.GetPosition()

            # don't know of a way to get the vertical spacing of items in
            # a wx.CheckListBox, so estimate it at font height + 5 pixels,
            # which is close enough on everything I've tested.
            h = pos.y + len(self.elementTypes) * \
                (util.getFontHeight(self.elements.GetFont()) + 5) + 15
        else:
            self.moreButton.SetLabel("More >>>")
            h = max(self.extraLabel.GetPosition().y,
                    self.moreButton.GetPosition().y +
                    self.moreButton.GetClientSize().height + 5)

        self.SetSizeHints(self.GetClientSize().width, h)
        util.setWH(self, h = h)

    def getParams(self):
        self.dirUp = self.direction.GetSelection() == 0
        self.matchWhole = self.matchWholeCb.IsChecked()
        self.matchCase = self.matchCaseCb.IsChecked()

        if self.useExtra:
            self.elementMap = {}
            for i in range(self.elements.GetCount()):
                self.elementMap[self.elementTypes[i]] = \
                    self.elements.IsChecked(i)

    def typeIncluded(self, lt):
        if not self.useExtra:
            return True

        return self.elementMap[lt]

    def OnFind(self, event = None, autoFind = False):
        if not autoFind:
            self.getParams()

        value = misc.fromGUI(self.findEntry.GetValue())
        if not self.matchCase:
            value = util.upper(value)

        if value == "":
            return

        self.searchWidth = len(value)

        if self.dirUp:
            inc = -1
        else:
            inc = 1

        line = self.ctrl.sp.line
        col = self.ctrl.sp.column
        ls = self.ctrl.sp.lines

        if (line == self.searchLine) and (col == self.searchColumn):
            text = ls[line].text

            col += inc
            if col >= len(text):
                line += 1
                col = 0
            elif col < 0:
                line -= 1
                if line >= 0:
                    col = max(len(ls[line].text) - 1, 0)

        fullSearch = False
        if inc > 0:
            if (line == 0) and (col == 0):
                fullSearch = True
        else:
            if (line == (len(ls) - 1)) and (col == (len(ls[line].text))):
                fullSearch = True

        self.searchLine = -1

        while True:
            found = False

            while True:
                if (line >= len(ls)) or (line < 0):
                    break

                if self.typeIncluded(ls[line].lt):
                    text = ls[line].text
                    if not self.matchCase:
                        text = util.upper(text)

                    if inc > 0:
                        res = text.find(value, col)
                    else:
                        res = text.rfind(value, 0, col + 1)

                    if res != -1:
                        if not self.matchWhole or (
                            util.isWordBoundary(text[res - 1 : res]) and
                            util.isWordBoundary(text[res + len(value) :
                                                     res + len(value) + 1])):

                            found = True

                            break

                line += inc
                if inc > 0:
                    col = 0
                else:
                    if line >= 0:
                        col = max(len(ls[line].text) - 1, 0)

            if found:
                self.searchLine = line
                self.searchColumn = res
                self.ctrl.sp.gotoPos(line, res)
                self.ctrl.sp.setMark(line, res + self.searchWidth - 1)

                if not autoFind:
                    self.ctrl.makeLineVisible(line)
                    self.ctrl.updateScreen()

                break
            else:
                if autoFind:
                    break

                if fullSearch:
                    wx.MessageBox("Search finished without results.",
                                  "No matches", wx.OK, self)

                    break

                if inc > 0:
                    s1 = "end"
                    s2 = "start"
                    restart = 0
                else:
                    s1 = "start"
                    s2 = "end"
                    restart = len(ls) - 1

                if wx.MessageBox("Search finished at the %s of the script. Do\n"
                                 "you want to continue at the %s of the script?"
                                 % (s1, s2), "Continue?",
                                 wx.YES_NO | wx.YES_DEFAULT, self) == wx.YES:
                    line = restart
                    fullSearch = True
                else:
                    break

        if not autoFind:
            self.ctrl.updateScreen()

    def OnReplace(self, event = None, autoFind = False):
        if self.searchLine == -1:
            return False

        value = util.toInputStr(misc.fromGUI(self.replaceEntry.GetValue()))
        ls = self.ctrl.sp.lines

        sp = self.ctrl.sp
        u = undo.SinglePara(sp, undo.CMD_MISC, self.searchLine)

        ls[self.searchLine].text = util.replace(
            ls[self.searchLine].text, value,
            self.searchColumn, self.searchWidth)

        sp.rewrapPara(sp.getParaFirstIndexFromLine(self.searchLine))

        self.searchLine = -1

        diff = len(value) - self.searchWidth

        if not self.dirUp:
            sp.column += self.searchWidth + diff
        else:
            sp.column -= 1

            if sp.column < 0:
                sp.line -= 1

                if sp.line < 0:
                    sp.line = 0
                    sp.column = 0

                    self.searchLine = 0
                    self.searchColumn = 0
                    self.searchWidth = 0
                else:
                    sp.column = len(ls[sp.line].text)

        sp.clearMark()
        sp.markChanged()

        u.setAfter(sp)
        sp.addUndo(u)

        self.OnFind(autoFind = autoFind)

        return True

    def OnReplaceAll(self, event = None):
        self.getParams()

        if self.searchLine == -1:
            self.OnFind(autoFind = True)

        count = 0
        while self.OnReplace(autoFind = True):
            count += 1

        if count != 0:
            self.ctrl.makeLineVisible(self.ctrl.sp.line)
            self.ctrl.updateScreen()

        wx.MessageBox("Replaced %d matches" % count, "Results", wx.OK, self)

########NEW FILE########
__FILENAME__ = fontinfo
import pml

# character widths and general font information for each font. acquired
# from the PDF font metrics. ((width / 1000) * point_size) / 72.0 = how
# many inches wide that character is.
#
# all Courier-* fonts have characters 600 units wide.

# get the FontMetrics object for the given style
def getMetrics(style):
    # the "& 15" gets rid of the underline flag
    return _fontMetrics[style & 15]

class FontMetrics:
    def __init__(self, fontWeight, flags, bbox, italicAngle, ascent, descent,
                 capHeight, stemV, stemH, xHeight, widths):

        # character widths in an array of 256 integers, or None for the
        # Courier fonts.
        self.widths = widths

        # see the PDF spec for the details on what these are.
        self.fontWeight = fontWeight
        self.flags = flags
        self.bbox = bbox
        self.italicAngle = italicAngle
        self.ascent = ascent
        self.descent = descent
        self.capHeight = capHeight
        self.stemV = stemV
        self.stemH = stemH
        self.xHeight = xHeight

    # calculate width of 'text' in 'size', and return it in 1/72 inch
    # units.
    def getTextWidth(self, text, size):
        widths = self.widths

        # Courier
        if not widths:
            return 0.6 * (size * len(text))

        total = 0
        for ch in text:
            total += widths[ord(ch)]

        return (total / 1000.0) * size

_fontMetrics = {

    pml.COURIER : FontMetrics(
    fontWeight = 400, flags = 35, bbox = (-23, -250, 715, 805),
    italicAngle = 0, ascent = 629, descent = -157, capHeight = 562,
    stemV = 51, stemH = 51, xHeight = 426, widths = None),

    pml.COURIER | pml.BOLD : FontMetrics(
    fontWeight = 700, flags = 35, bbox = (-113, -250, 749, 801),
    italicAngle = 0, ascent = 629, descent = -157, capHeight = 562,
    stemV = 106, stemH = 84, xHeight = 439, widths = None),

    pml.COURIER | pml.ITALIC : FontMetrics(
    fontWeight = 400, flags = 99, bbox = (-27, -250, 849, 805),
    italicAngle = -12, ascent = 629, descent = -157, capHeight = 562,
    stemV = 51, stemH = 51, xHeight = 426, widths = None),

    pml.COURIER | pml.BOLD | pml.ITALIC : FontMetrics(
    fontWeight = 700, flags = 99, bbox = (-57, -250, 869, 801),
    italicAngle = -12, ascent = 629, descent = -157, capHeight = 562,
    stemV = 106, stemH = 84, xHeight = 439, widths = None),


    pml.HELVETICA : FontMetrics(
    fontWeight = 400, flags = 32, bbox = (-166, -225, 1000, 931),
    italicAngle = 0, ascent = 718, descent = -207, capHeight = 718,
    stemV = 88, stemH = 76, xHeight = 523, widths = [
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    278, 278, 355, 556, 556, 889, 667, 191,
    333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556,
    556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778,
    722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944,
    667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556,
    556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722,
    500, 500, 500, 334, 260, 334, 584, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 333, 556, 556, 556, 556, 260, 556,
    333, 737, 370, 556, 584, 545, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278,
    333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722,
    667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584,
    778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500,
    556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584,
    611, 556, 556, 556, 556, 500, 556, 500
    ]),

    pml.HELVETICA | pml.BOLD : FontMetrics(
    fontWeight = 700, flags = 32, bbox = (-170, -228, 1003, 962),
    italicAngle = 0, ascent = 718, descent = -207, capHeight = 718,
    stemV = 140, stemH = 118, xHeight = 532, widths = [
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    278, 333, 474, 556, 556, 889, 722, 238,
    333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556,
    556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778,
    722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944,
    667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611,
    611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778,
    556, 556, 500, 389, 280, 389, 584, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 333, 556, 556, 556, 556, 280, 556,
    333, 737, 370, 556, 584, 564, 737, 333,
    400, 584, 333, 333, 333, 611, 556, 278,
    333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722,
    667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584,
    778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556,
    556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 584,
    611, 611, 611, 611, 611, 556, 611, 556,
    ]),

    pml.HELVETICA | pml.ITALIC : FontMetrics(
    fontWeight = 400, flags = 96, bbox = (-170, -225, 1116, 931),
    italicAngle = -12, ascent = 718, descent = -207, capHeight = 718,
    stemV = 88, stemH = 76, xHeight = 523, widths = [
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    278, 278, 355, 556, 556, 889, 667, 191,
    333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556,
    556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778,
    722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944,
    667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556,
    556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722,
    500, 500, 500, 334, 260, 334, 584, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 545, 545, 545, 545, 545, 545, 545,
    545, 333, 556, 556, 556, 556, 260, 556,
    333, 737, 370, 556, 584, 545, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278,
    333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722,
    667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584,
    778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500,
    556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584,
    611, 556, 556, 556, 556, 500, 556, 500,
    ]),

    pml.HELVETICA | pml.BOLD | pml.ITALIC : FontMetrics(
    fontWeight = 700, flags = 96, bbox = (-174, -228, 1114, 962),
    italicAngle = -12, ascent = 718, descent = -207, capHeight = 718,
    stemV = 140, stemH = 118, xHeight = 532, widths = [
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    278, 333, 474, 556, 556, 889, 722, 238,
    333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556,
    556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778,
    722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944,
    667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611,
    611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778,
    556, 556, 500, 389, 280, 389, 584, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 564, 564, 564, 564, 564, 564, 564,
    564, 333, 556, 556, 556, 556, 280, 556,
    333, 737, 370, 556, 584, 564, 737, 333,
    400, 584, 333, 333, 333, 611, 556, 278,
    333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722,
    667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584,
    778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556,
    556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 584,
    611, 611, 611, 611, 611, 556, 611, 556,
    ]),


    pml.TIMES_ROMAN : FontMetrics(
    fontWeight = 400, flags = 34, bbox = (-168, -218, 1000, 898),
    italicAngle = 0, ascent = 683, descent = -217, capHeight = 662,
    stemV = 84, stemH = 28, xHeight = 450, widths = [
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    250, 333, 408, 500, 500, 833, 778, 180,
    333, 333, 500, 564, 250, 333, 250, 278,
    500, 500, 500, 500, 500, 500, 500, 500,
    500, 500, 278, 278, 564, 564, 564, 444,
    921, 722, 667, 667, 722, 611, 556, 722,
    722, 333, 389, 722, 611, 889, 722, 722,
    556, 722, 667, 556, 611, 722, 722, 944,
    722, 722, 611, 333, 278, 333, 469, 500,
    333, 444, 500, 444, 500, 444, 333, 500,
    500, 278, 278, 500, 278, 778, 500, 500,
    500, 500, 333, 389, 278, 500, 500, 722,
    500, 500, 444, 480, 200, 480, 541, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 516, 516, 516, 516, 516, 516, 516,
    516, 333, 500, 500, 500, 500, 200, 500,
    333, 760, 276, 500, 564, 516, 760, 333,
    400, 564, 300, 300, 333, 500, 453, 250,
    333, 300, 310, 500, 750, 750, 750, 444,
    722, 722, 722, 722, 722, 722, 889, 667,
    611, 611, 611, 611, 333, 333, 333, 333,
    722, 722, 722, 722, 722, 722, 722, 564,
    722, 722, 722, 722, 722, 722, 556, 500,
    444, 444, 444, 444, 444, 444, 667, 444,
    444, 444, 444, 444, 278, 278, 278, 278,
    500, 500, 500, 500, 500, 500, 500, 564,
    500, 500, 500, 500, 500, 500, 500, 500,
    ]),

    pml.TIMES_ROMAN | pml.BOLD : FontMetrics(
    fontWeight = 700, flags = 34, bbox = (-168, -218, 1000, 935),
    italicAngle = 0, ascent = 683, descent = -217, capHeight = 676,
    stemV = 139, stemH = 44, xHeight = 461, widths = [
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    250, 333, 555, 500, 500, 1000, 833, 278,
    333, 333, 500, 570, 250, 333, 250, 278,
    500, 500, 500, 500, 500, 500, 500, 500,
    500, 500, 333, 333, 570, 570, 570, 500,
    930, 722, 667, 722, 722, 667, 611, 778,
    778, 389, 500, 778, 667, 944, 722, 778,
    611, 778, 722, 556, 667, 722, 722, 1000,
    722, 722, 667, 333, 278, 333, 581, 500,
    333, 500, 556, 444, 556, 444, 333, 500,
    556, 278, 333, 556, 278, 833, 556, 500,
    556, 556, 444, 389, 333, 556, 500, 722,
    500, 500, 444, 394, 220, 394, 520, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 540, 540, 540, 540, 540, 540, 540,
    540, 333, 500, 500, 500, 500, 220, 500,
    333, 747, 300, 500, 570, 540, 747, 333,
    400, 570, 300, 300, 333, 556, 540, 250,
    333, 300, 330, 500, 750, 750, 750, 500,
    722, 722, 722, 722, 722, 722, 1000, 722,
    667, 667, 667, 667, 389, 389, 389, 389,
    722, 722, 778, 778, 778, 778, 778, 570,
    778, 722, 722, 722, 722, 722, 611, 556,
    500, 500, 500, 500, 500, 500, 722, 444,
    444, 444, 444, 444, 278, 278, 278, 278,
    500, 556, 500, 500, 500, 500, 500, 570,
    500, 556, 556, 556, 556, 500, 556, 500,
    ]),

    pml.TIMES_ROMAN | pml.ITALIC : FontMetrics(
    fontWeight = 400, flags = 98, bbox = (-169, -217, 1010, 883),
    italicAngle = -15.5, ascent = 683, descent = -217, capHeight = 653,
    stemV = 76, stemH = 32, xHeight = 441, widths = [
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    250, 333, 420, 500, 500, 833, 778, 214,
    333, 333, 500, 675, 250, 333, 250, 278,
    500, 500, 500, 500, 500, 500, 500, 500,
    500, 500, 333, 333, 675, 675, 675, 500,
    920, 611, 611, 667, 722, 611, 611, 722,
    722, 333, 444, 667, 556, 833, 667, 722,
    611, 722, 611, 500, 556, 722, 611, 833,
    611, 556, 556, 389, 278, 389, 422, 500,
    333, 500, 500, 444, 500, 444, 278, 500,
    500, 278, 278, 444, 278, 722, 500, 500,
    500, 500, 389, 389, 278, 500, 444, 667,
    444, 444, 389, 400, 275, 400, 541, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 513, 513, 513, 513, 513, 513, 513,
    513, 389, 500, 500, 500, 500, 275, 500,
    333, 760, 276, 500, 675, 513, 760, 333,
    400, 675, 300, 300, 333, 500, 523, 250,
    333, 300, 310, 500, 750, 750, 750, 500,
    611, 611, 611, 611, 611, 611, 889, 667,
    611, 611, 611, 611, 333, 333, 333, 333,
    722, 667, 722, 722, 722, 722, 722, 675,
    722, 722, 722, 722, 722, 556, 611, 500,
    500, 500, 500, 500, 500, 500, 667, 444,
    444, 444, 444, 444, 278, 278, 278, 278,
    500, 500, 500, 500, 500, 500, 500, 675,
    500, 500, 500, 500, 500, 444, 500, 444,
    ]),

    pml.TIMES_ROMAN | pml.BOLD | pml.ITALIC : FontMetrics(
    fontWeight = 700, flags = 98, bbox = (-200, -218, 996, 921),
    italicAngle = -15, ascent = 683, descent = -217, capHeight = 669,
    stemV = 121, stemH = 42, xHeight = 462, widths = [
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    250, 389, 555, 500, 500, 833, 778, 278,
    333, 333, 500, 570, 250, 333, 250, 278,
    500, 500, 500, 500, 500, 500, 500, 500,
    500, 500, 333, 333, 570, 570, 570, 500,
    832, 667, 667, 667, 722, 667, 667, 722,
    778, 389, 500, 667, 611, 889, 722, 722,
    611, 722, 667, 556, 611, 722, 667, 889,
    667, 611, 611, 333, 278, 333, 570, 500,
    333, 500, 500, 444, 500, 444, 333, 500,
    556, 278, 278, 500, 278, 778, 556, 500,
    500, 500, 389, 389, 278, 556, 444, 667,
    500, 444, 389, 348, 220, 348, 570, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 523, 523, 523, 523, 523, 523, 523,
    523, 389, 500, 500, 500, 500, 220, 500,
    333, 747, 266, 500, 606, 523, 747, 333,
    400, 570, 300, 300, 333, 576, 500, 250,
    333, 300, 300, 500, 750, 750, 750, 500,
    667, 667, 667, 667, 667, 667, 944, 667,
    667, 667, 667, 667, 389, 389, 389, 389,
    722, 722, 722, 722, 722, 722, 722, 570,
    722, 722, 722, 722, 722, 611, 611, 500,
    500, 500, 500, 500, 500, 500, 722, 444,
    444, 444, 444, 444, 278, 278, 278, 278,
    500, 556, 500, 500, 500, 500, 500, 570,
    500, 556, 556, 556, 556, 444, 500, 444,
    ])
    }

########NEW FILE########
__FILENAME__ = gutil
from error import *
import misc
import util

import os
import tempfile

import wx

# this contains misc GUI-related functions

# since at least GTK 1.2's single-selection listbox is buggy in that if we
# don't deselect the old item manually, it does multiple selections, we
# have this function that does the following:
#
#  1) deselects current selection, if any
#  2) select the item with the given index
def listBoxSelect(lb, index):
    old = lb.GetSelection()

    if  old!= -1:
        lb.SetSelection(old, False)

    lb.SetSelection(index, True)

# add (name, cdata) to the listbox at the correct place, determined by
# cmp(cdata1, cdata2).
def listBoxAdd(lb, name, cdata):
    for i in range(lb.GetCount()):
        if cmp(cdata, lb.GetClientData(i)) < 0:
            lb.InsertItems([name], i)
            lb.SetClientData(i, cdata)

            return

    lb.Append(name, cdata)

# create stock button.
def createStockButton(parent, label):
    # wxMSW does not really have them: it does not have any icons and it
    # inconsistently adds the shortcut key to some buttons, but not to
    # all, so it's better not to use them at all on Windows.
    if misc.isUnix:
        ids = {
            "OK" : wx.ID_OK,
            "Cancel" : wx.ID_CANCEL,
            "Apply" : wx.ID_APPLY,
            "Add" : wx.ID_ADD,
            "Delete" : wx.ID_DELETE,
            "Preview" : wx.ID_PREVIEW
            }

        return wx.Button(parent, ids[label])
    else:
        return wx.Button(parent, -1, label)

# wxWidgets has a bug in 2.6 on wxGTK2 where double clicking on a button
# does not send two wx.EVT_BUTTON events, only one. since the wxWidgets
# maintainers do not seem interested in fixing this
# (http://sourceforge.net/tracker/index.php?func=detail&aid=1449838&group_id=9863&atid=109863),
# we work around it ourselves by binding the left mouse button double
# click event to the same callback function on the buggy platforms.
def btnDblClick(btn, func):
    if misc.isUnix:
        wx.EVT_LEFT_DCLICK(btn, func)

# show PDF document 'pdfData' in an external viewer program. writes out a
# temporary file, first deleting all old temporary files, then opens PDF
# viewer application. 'mainFrame' is used as a parent for message boxes in
# case there are any errors.
def showTempPDF(pdfData, cfgGl, mainFrame):
    try:
        try:
            util.removeTempFiles(misc.tmpPrefix)

            fd, filename = tempfile.mkstemp(prefix = misc.tmpPrefix,
                                            suffix = ".pdf")

            try:
                os.write(fd, pdfData)
            finally:
                os.close(fd)

            util.showPDF(filename, cfgGl, mainFrame)

        except IOError, (errno, strerror):
            raise MiscError("IOError: %s" % strerror)

    except TrelbyError, e:
        wx.MessageBox("Error writing temporary PDF file: %s" % e,
                      "Error", wx.OK, mainFrame)

########NEW FILE########
__FILENAME__ = headers
import pml
import util

# a script's headers.
class Headers:

    def __init__(self):
        # list of HeaderString objects
        self.hdrs = []

        # how many empty lines after the headers
        self.emptyLinesAfter = 1

    # create standard headers
    def addDefaults(self):
        h = HeaderString()
        h.text = "${PAGE}."
        h.align = util.ALIGN_RIGHT
        h.line = 1

        self.hdrs.append(h)

    # return how many header lines there are. includes number of empty
    # lines after possible headers.
    def getNrOfLines(self):
        nr = 0

        for h in self.hdrs:
            nr = max(nr, h.line)

        if nr > 0:
            nr += self.emptyLinesAfter

        return nr

    # add headers to given page. 'pageNr' must be a string.
    def generatePML(self, page, pageNr, cfg):
        for h in self.hdrs:
            h.generatePML(page, pageNr, cfg)

# a single header string
class HeaderString:
    def __init__(self):

        # which line, 1-based
        self.line = 1

        # x offset, in characters
        self.xoff = 0

        # contents of string
        self.text = ""

        # whether this is centered in the horizontal direction
        self.align = util.ALIGN_CENTER

        # style flags
        self.isBold = False
        self.isItalic = False
        self.isUnderlined = False

    def generatePML(self, page, pageNr, cfg):
        fl = 0

        if self.isBold:
            fl |= pml.BOLD

        if self.isItalic:
            fl |= pml.ITALIC

        if self.isUnderlined:
            fl |= pml.UNDERLINED

        if self.align == util.ALIGN_LEFT:
            x = cfg.marginLeft
        elif self.align == util.ALIGN_CENTER:
            x = (cfg.marginLeft + (cfg.paperWidth - cfg.marginRight)) / 2.0
        else:
            x = cfg.paperWidth - cfg.marginRight

        fs = cfg.fontSize

        if self.xoff != 0:
            x += util.getTextWidth(" ", pml.COURIER, fs) * self.xoff

        y = cfg.marginTop + (self.line - 1) * util.getTextHeight(fs)

        text = self.text.replace("${PAGE}", pageNr)

        page.add(pml.TextOp(text, x, y, fs, fl, self.align))

    # parse information from s, which must be a string created by __str__,
    # and set object state accordingly. keeps default settings on any
    # errors, does not throw any exceptions.
    #
    # sample of the format: '1,0,r,,${PAGE}.'
    def load(self, s):
        a = util.fromUTF8(s).split(",", 4)

        if len(a) != 5:
            return

        self.line = util.str2int(a[0], 1, 1, 5)
        self.xoff = util.str2int(a[1], 0, -100, 100)

        l, c, self.isBold, self.isItalic, self.isUnderlined = \
            util.flags2bools(a[2], "lcbiu")

        if l:
            self.align = util.ALIGN_LEFT
        elif c:
            self.align = util.ALIGN_CENTER
        else:
            self.align = util.ALIGN_RIGHT

        self.text = a[4]

    def __str__(self):
        s = "%d,%d," % (self.line, self.xoff)

        if self.align == util.ALIGN_LEFT:
            s += "l"
        elif self.align == util.ALIGN_CENTER:
            s += "c"
        else:
            s += "r"

        s += util.bools2flags("biu", self.isBold, self.isItalic,
                              self.isUnderlined)

        s += ",,%s" % self.text

        return util.toUTF8(s)

########NEW FILE########
__FILENAME__ = headersdlg
import gutil
import headers
import misc
import pdf
import pml
import util

import wx

class HeadersDlg(wx.Dialog):
    def __init__(self, parent, headers, cfg, cfgGl, applyFunc):
        wx.Dialog.__init__(self, parent, -1, "Headers",
                           style = wx.DEFAULT_DIALOG_STYLE)

        self.headers = headers
        self.cfg = cfg
        self.cfgGl = cfgGl
        self.applyFunc = applyFunc

        # whether some events are blocked
        self.block = False

        self.hdrIndex = -1
        if len(self.headers.hdrs) > 0:
            self.hdrIndex = 0

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Empty lines after headers:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)

        self.elinesEntry = wx.SpinCtrl(self, -1)
        self.elinesEntry.SetRange(0, 5)
        wx.EVT_SPINCTRL(self, self.elinesEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.elinesEntry, self.OnKillFocus)
        hsizer.Add(self.elinesEntry, 0, wx.LEFT, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM,
                   10)

        tmp = wx.StaticText(self, -1, "Strings:")
        vsizer.Add(tmp)

        self.stringsLb = wx.ListBox(self, -1, size = (200, 100))
        vsizer.Add(self.stringsLb, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addBtn = gutil.createStockButton(self, "Add")
        hsizer.Add(self.addBtn)
        wx.EVT_BUTTON(self, self.addBtn.GetId(), self.OnAddString)
        gutil.btnDblClick(self.addBtn, self.OnAddString)

        self.delBtn = gutil.createStockButton(self, "Delete")
        hsizer.Add(self.delBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.delBtn.GetId(), self.OnDeleteString)
        gutil.btnDblClick(self.delBtn, self.OnDeleteString)

        vsizer.Add(hsizer, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Text:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)

        self.textEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.textEntry, 1, wx.LEFT, 10)
        wx.EVT_TEXT(self, self.textEntry.GetId(), self.OnMisc)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        vsizer.Add(wx.StaticText(self, -1,
            "'${PAGE}' will be replaced by the page number."), 0,
            wx.ALIGN_CENTER | wx.TOP, 5)

        hsizerTop = wx.BoxSizer(wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(3, 2, 5, 0)

        gsizer.Add(wx.StaticText(self, -1, "Header line:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)

        self.lineEntry = wx.SpinCtrl(self, -1)
        self.lineEntry.SetRange(1, 5)
        wx.EVT_SPINCTRL(self, self.lineEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.lineEntry, self.OnKillFocus)
        gsizer.Add(self.lineEntry)

        gsizer.Add(wx.StaticText(self, -1, "X offset (characters):"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.xoffEntry = wx.SpinCtrl(self, -1)
        self.xoffEntry.SetRange(-100, 100)
        wx.EVT_SPINCTRL(self, self.xoffEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.xoffEntry, self.OnKillFocus)
        gsizer.Add(self.xoffEntry)

        gsizer.Add(wx.StaticText(self, -1, "Alignment:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.alignCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for it in [ ("Left", util.ALIGN_LEFT), ("Center", util.ALIGN_CENTER),
                    ("Right", util.ALIGN_RIGHT) ]:
            self.alignCombo.Append(it[0], it[1])

        gsizer.Add(self.alignCombo)
        wx.EVT_COMBOBOX(self, self.alignCombo.GetId(), self.OnMisc)

        hsizerTop.Add(gsizer)

        bsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, -1, "Style"), wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.addCheckBox("Bold", self, vsizer2, pad)
        self.addCheckBox("Italic", self, vsizer2, pad)
        self.addCheckBox("Underlined", self, vsizer2, pad)

        bsizer.Add(vsizer2)

        hsizerTop.Add(bsizer, 0, wx.LEFT, 40)

        vsizer.Add(hsizerTop, 0, wx.TOP, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        previewBtn = gutil.createStockButton(self, "Preview")
        hsizer.Add(previewBtn)

        applyBtn = gutil.createStockButton(self, "Apply")
        hsizer.Add(applyBtn, 0, wx.LEFT, 10)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, previewBtn.GetId(), self.OnPreview)
        wx.EVT_BUTTON(self, applyBtn.GetId(), self.OnApply)
        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        wx.EVT_LISTBOX(self, self.stringsLb.GetId(), self.OnStringsLb)

        # list of widgets that are specific to editing the selected string
        self.widList = [ self.textEntry, self.xoffEntry, self.alignCombo,
                         self.lineEntry, self.boldCb, self.italicCb,
                         self.underlinedCb ]

        self.updateGui()

        self.textEntry.SetFocus()

    def addCheckBox(self, name, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        wx.EVT_CHECKBOX(self, cb.GetId(), self.OnMisc)
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, name.lower() + "Cb", cb)

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnApply(self, event):
        self.applyFunc(self.headers)

    def OnPreview(self, event):
        doc = pml.Document(self.cfg.paperWidth, self.cfg.paperHeight)

        pg = pml.Page(doc)
        self.headers.generatePML(pg, "42", self.cfg)

        fs = self.cfg.fontSize
        chY = util.getTextHeight(fs)

        y = self.cfg.marginTop + self.headers.getNrOfLines() * chY

        pg.add(pml.TextOp("Mindy runs away from the dinosaur, but trips on"
            " the power", self.cfg.marginLeft, y, fs))

        pg.add(pml.TextOp("cord. The raptor approaches her slowly.",
            self.cfg.marginLeft, y + chY, fs))

        doc.add(pg)

        tmp = pdf.generate(doc)
        gutil.showTempPDF(tmp, self.cfgGl, self)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnStringsLb(self, event = None):
        self.hdrIndex = self.stringsLb.GetSelection()
        self.updateHeaderGui()

    def OnAddString(self, event):
        h = headers.HeaderString()
        h.text = "new string"

        self.headers.hdrs.append(h)
        self.hdrIndex = len(self.headers.hdrs) - 1

        self.updateGui()

    def OnDeleteString(self, event):
        if self.hdrIndex == -1:
            return

        del self.headers.hdrs[self.hdrIndex]
        self.hdrIndex = min(self.hdrIndex, len(self.headers.hdrs) - 1)

        self.updateGui()

    # update listbox
    def updateGui(self):
        self.stringsLb.Clear()

        self.elinesEntry.SetValue(self.headers.emptyLinesAfter)

        self.delBtn.Enable(self.hdrIndex != -1)

        for h in self.headers.hdrs:
            self.stringsLb.Append(h.text)

        if self.hdrIndex != -1:
            self.stringsLb.SetSelection(self.hdrIndex)

        self.updateHeaderGui()

    # update selected header stuff
    def updateHeaderGui(self):
        if self.hdrIndex == -1:
            for w in self.widList:
                w.Disable()

            self.textEntry.SetValue("")
            self.lineEntry.SetValue(1)
            self.xoffEntry.SetValue(0)
            self.boldCb.SetValue(False)
            self.italicCb.SetValue(False)
            self.underlinedCb.SetValue(False)

            return

        self.block = True

        h = self.headers.hdrs[self.hdrIndex]

        for w in self.widList:
            w.Enable(True)

        self.textEntry.SetValue(h.text)
        self.xoffEntry.SetValue(h.xoff)

        util.reverseComboSelect(self.alignCombo, h.align)
        self.lineEntry.SetValue(h.line)

        self.boldCb.SetValue(h.isBold)
        self.italicCb.SetValue(h.isItalic)
        self.underlinedCb.SetValue(h.isUnderlined)

        self.block = False

    def OnMisc(self, event = None):
        self.headers.emptyLinesAfter = util.getSpinValue(self.elinesEntry)

        if (self.hdrIndex == -1) or self.block:
            return

        h = self.headers.hdrs[self.hdrIndex]

        h.text = util.toInputStr(misc.fromGUI(self.textEntry.GetValue()))
        self.stringsLb.SetString(self.hdrIndex, h.text)

        h.xoff = util.getSpinValue(self.xoffEntry)
        h.line = util.getSpinValue(self.lineEntry)
        h.align = self.alignCombo.GetClientData(self.alignCombo.GetSelection())

        h.isBold = self.boldCb.GetValue()
        h.isItalic = self.italicCb.GetValue()
        h.isUnderlined = self.underlinedCb.GetValue()

########NEW FILE########
__FILENAME__ = locationreport
import gutil
import misc
import pdf
import pml
import scenereport
import screenplay
import util

import wx

def genLocationReport(mainFrame, sp):
    report = LocationReport(scenereport.SceneReport(sp))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False)

    ok = False
    if dlg.ShowModal() == wx.ID_OK:
        ok = True

    dlg.Destroy()

    if not ok:
        return

    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

class LocationReport:
    # sr = SceneReport
    def __init__(self, sr):
        # TODO: have this construct SceneReport internally

        self.sp = sr.sp

        # key = scene name, value = LocationInfo. note that multiple keys
        # can point to the same LocationInfo.
        locations = {}

        # like locations, but this one stores per-scene information
        self.scenes = {}

        # make grouped scenes point to the same LocationInfos.
        for sceneList in self.sp.locations.locations:
            li = LocationInfo(self.sp)

            for scene in sceneList:
                locations[scene] = li

        # merge scene information for locations and store scene
        # information
        for si in sr.scenes:
            locations.setdefault(si.name, LocationInfo(self.sp)).addScene(si)

            self.scenes.setdefault(si.name, LocationInfo(self.sp)).\
                 addScene(si)

        # remove empty LocationInfos, sort them and store to a list
        tmp = []
        for li in locations.itervalues():
            if (len(li.scenes) > 0) and (li not in tmp):
                tmp.append(li)

        def sortFunc(o1, o2):
            ret = cmp(o2.lines, o1.lines)

            if ret != 0:
                return ret
            else:
                return cmp(o1.scenes[0], o2.scenes[0])

        tmp.sort(sortFunc)

        self.locations = tmp

        # information about what to include (and yes, the comma is needed
        # to unpack the list)
        self.INF_SPEAKERS, = range(1)
        self.inf = []
        for s in ["Speakers"]:
            self.inf.append(misc.CheckBoxItem(s))

    def generate(self):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 15.0, 12)

        scriptLines = sum([li.lines for li in self.locations])

        for li in self.locations:
            tf.addSpace(5.0)

            # list of (scenename, lines_in_scene) tuples, which we sort in
            # DESC(lines_in_scene) ASC(scenename) order.
            tmp = [(scene, self.scenes[scene].lines) for scene in li.scenes]

            # PY2.4: this should work (test it):
            #  tmp.sort(key=itemgetter(0))
            #  tmp.sort(key=itemgetter(1) reverse=True)
            tmp.sort(lambda x, y: cmp(x[0], y[0]))
            tmp.reverse()
            tmp.sort(lambda x, y: cmp(x[1], y[1]))
            tmp.reverse()

            for scene, lines in tmp:
                if len(tmp) > 1:
                    pct = " (%d%%)" % util.pct(lines, li.lines)
                else:
                    pct = ""

                tf.addText("%s%s" % (scene, pct), style = pml.BOLD)

            tf.addSpace(1.0)

            tf.addWrappedText("Lines: %d (%d%% action, %d%% of script),"
                " Scenes: %d, Pages: %d (%s)" % (li.lines,
                util.pct(li.actionLines, li.lines),
                util.pct(li.lines, scriptLines), li.sceneCount,
                len(li.pages), li.pages), "  ")


            if self.inf[self.INF_SPEAKERS].selected:
                tf.addSpace(2.5)

                for it in util.sortDict(li.chars):
                    tf.addText("     %3d  %s" % (it[1], it[0]))

        return pdf.generate(tf.doc)

# information about one location
class LocationInfo:
    def __init__(self, sp):
        # number of scenes
        self.sceneCount = 0

        # scene names, e.g. ["INT. MOTEL ROOM - NIGHT", "EXT. MOTEL -
        # NIGHT"]
        self.scenes = []

        # total lines, excluding scene lines
        self.lines = 0

        # action lines
        self.actionLines = 0

        # page numbers
        self.pages = screenplay.PageList(sp.getPageNumbers())

        # key = character name (upper cased), value = number of dialogue
        # lines
        self.chars = {}

    # add a scene. si = SceneInfo
    def addScene(self, si):
        if si.name not in self.scenes:
            self.scenes.append(si.name)

        self.sceneCount += 1
        self.lines += si.lines
        self.actionLines += si.actionLines
        self.pages += si.pages

        for name, dlines in si.chars.iteritems():
            self.chars[name] = self.chars.get(name, 0) + dlines

########NEW FILE########
__FILENAME__ = locations
import mypickle
import util

# manages location-information for a single screenplay. a "location" is a
# single place that can be referred to using multiple scene names, e.g.
#  INT. MOTEL ROOM - DAY
#  INT. MOTEL ROOM - DAY - 2 HOURS LATER
#  INT. MOTEL ROOM - NIGHT
class Locations:
    cvars = None

    def __init__(self):
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addList("locations", [], "Locations",
                      mypickle.ListVar("", [], "",
                                       mypickle.StrLatin1Var("", "", "")))

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

        # self.locations is a list of lists of strings, where the inner
        # lists list scene names to combine into one location. e.g.
        # [
        #  [
        #   "INT. ROOM 413 - DAY",
        #   "INT. ROOM 413 - NIGHT"
        #  ]
        # ]

    # load from string 's'. does not throw any exceptions and silently
    # ignores any errors.
    def load(self, s):
        self.cvars.load(self.cvars.makeVals(s), "", self)

    # save to a string and return that.
    def save(self):
        return self.cvars.save("", self)

    # refresh location list against the given scene names (in the format
    # returned by Screenplay.getSceneNames()). removes unknown and
    # duplicate scenes from locations, and if that results in a location
    # with 0 scenes, removes that location completely. also upper-cases
    # all the scene names, sorts the lists, first each location list's
    # scenes, and then the locations based on the first scene of the
    # location.
    def refresh(self, sceneNames):
        locs = []

        added = {}

        for sceneList in self.locations:
            scenes = []

            for scene in sceneList:
                name = util.upper(scene)

                if (name in sceneNames) and (name not in added):
                    scenes.append(name)
                    added[name] = None

            if scenes:
                scenes.sort()
                locs.append(scenes)

        locs.sort()

        self.locations = locs

########NEW FILE########
__FILENAME__ = locationsdlg
import gutil
import locations
import util

import wx

class LocationsDlg(wx.Dialog):
    def __init__(self, parent, sp):
        wx.Dialog.__init__(self, parent, -1, "Locations",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.sp = sp

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Locations:")
        vsizer.Add(tmp)

        self.locationsLb = wx.ListBox(self, -1, size = (450, 200))
        vsizer.Add(self.locationsLb, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addBtn = gutil.createStockButton(self, "Add")
        hsizer.Add(self.addBtn)
        wx.EVT_BUTTON(self, self.addBtn.GetId(), self.OnAdd)

        self.delBtn = gutil.createStockButton(self, "Delete")
        hsizer.Add(self.delBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.delBtn.GetId(), self.OnDelete)

        vsizer.Add(hsizer, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        tmp = wx.StaticText(self, -1, "Scenes:")
        vsizer.Add(tmp)

        self.scenesLb = wx.ListBox(self, -1, size = (450, 200),
                                   style = wx.LB_EXTENDED)
        vsizer.Add(self.scenesLb, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        self.fillGui()

    def OnOK(self, event):
        # master list
        ml = []

        # sub-list
        sl = []

        for i in range(self.locationsLb.GetCount()):
            scene = self.locationsLb.GetClientData(i)

            if scene:
                sl.append(scene)
            elif sl:
                ml.append(sl)
                sl = []

        self.sp.locations.locations = ml
        self.sp.locations.refresh(self.sp.getSceneNames())

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnAdd(self, event):
        selected = self.scenesLb.GetSelections()

        if not selected:
            wx.MessageBox("No scenes selected in the lower list.", "Error",
                          wx.OK, self)

            return

        locIdx = self.locationsLb.GetSelection()

        # if user has selected a separator line, treat it as no selection
        if (locIdx != -1) and\
               (self.locationsLb.GetClientData(locIdx) == None):
            locIdx = -1

        addSep = False

        for idx in selected:
            scene = self.scenesLb.GetClientData(idx)

            # insert at selected position, or at the bottom if a new group
            if locIdx != -1:
                self.locationsLb.InsertItems([scene], locIdx)
                self.locationsLb.SetClientData(locIdx, scene)
                gutil.listBoxSelect(self.locationsLb, locIdx)
            else:
                addSep = True
                self.locationsLb.Append(scene, scene)
                locIdx = self.locationsLb.GetCount() - 1
                gutil.listBoxSelect(self.locationsLb, locIdx)

        if addSep:
            self.locationsLb.Append("-" * 40, None)

        # we need these to be in sorted order, which they probably are,
        # but wxwidgets documentation doesn't say that, so to be safe we
        # sort it ourselves. and as tuples can't be sorted, we change it
        # to a list first.
        selected = [it for it in selected]
        selected.sort()

        for i in range(len(selected)):
            self.scenesLb.Delete(selected[i] - i)

    def OnDelete(self, event):
        scene = None
        idx = self.locationsLb.GetSelection()

        if idx != -1:
            scene = self.locationsLb.GetClientData(idx)

        if scene == None:
            wx.MessageBox("No scene selected in the upper list.", "Error",
                          wx.OK, self)

            return

        gutil.listBoxAdd(self.scenesLb, scene, scene)
        self.locationsLb.Delete(idx)

        # was the last item we looked at a separator
        lastWasSep = False

        # go through locations, remove first encountered double separator
        # (appears when a location group is deleted completely)
        for i in range(self.locationsLb.GetCount()):
            cdata = self.locationsLb.GetClientData(i)

            if lastWasSep and (cdata == None):
                self.locationsLb.Delete(i)

                break

            lastWasSep = cdata == None

        # if it goes completely empty, remove the single separator line
        if (self.locationsLb.GetCount() == 1) and\
           (self.locationsLb.GetClientData(0) == None):
            self.locationsLb.Delete(0)

    def fillGui(self):
        self.sp.locations.refresh(self.sp.getSceneNames())

        separator = "-" * 40
        added = {}

        for locList in self.sp.locations.locations:
            for scene in locList:
                self.locationsLb.Append(scene, scene)
                added[scene] = None

            self.locationsLb.Append(separator, None)

        sceneNames = sorted(self.sp.getSceneNames().keys())

        for scene in sceneNames:
            if scene not in added:
                self.scenesLb.Append(scene, scene)

########NEW FILE########
__FILENAME__ = misc
# -*- coding: iso-8859-1 -*-

import gutil
import opts
import util

import os
import os.path
import sys

import wx

TAB_BAR_HEIGHT = 24

version = "2.3-dev"

def init(doWX = True):
    global isWindows, isUnix, unicodeFS, wxIsUnicode, doDblBuf, \
           progPath, confPath, tmpPrefix

    # prefix used for temp files
    tmpPrefix = "trelby-tmp-"

    isWindows = False
    isUnix = False

    if wx.Platform == "__WXMSW__":
        isWindows = True
    else:
        isUnix = True

    # are we using a Unicode build of wxWidgets
    wxIsUnicode = "unicode" in wx.PlatformInfo

    # does this platform support using Python's unicode strings in various
    # filesystem calls; if not, we need to convert filenames to UTF-8
    # before using them.
    unicodeFS = isWindows

    # wxGTK2 does not need us to do double buffering ourselves, others do
    doDblBuf = not isUnix

    # stupid hack to keep testcases working, since they don't initialize
    # opts (the doWX name is just for similarity with util)
    if not doWX or opts.isTest:
        progPath = u"."
        confPath = u".trelby"
    else:
        if isUnix:
            progPath = unicode(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "UTF-8")

            confPath = unicode(os.environ["HOME"], "UTF-8") + u"/.trelby"
        else:
            progPath = getPathFromRegistry()

            confPath = util.getWindowsUnicodeEnvVar(u"USERPROFILE") + ur"\Trelby\conf"

            if not os.path.exists(confPath):
                os.makedirs(confPath)

def getPathFromRegistry():
    registryPath = r"Software\Microsoft\Windows\CurrentVersion\App Paths\trelby.exe"

    try:
        import _winreg

        regPathKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, registryPath)
        regPathValue, regPathType = _winreg.QueryValueEx(regPathKey, "Path")

        if regPathType == _winreg.REG_SZ:
            return regPathValue
        else:
            raise TypeError

    except:
        wx.MessageBox("There was an error reading the following registry key: %s.\n"
                      "You may need to reinstall the program to fix this error." %
                      registryPath, "Error", wx.OK)
        sys.exit()

# convert s, which is returned from the wxWidgets GUI and is an Unicode
# string, to a normal string.
def fromGUI(s):
    return s.encode("ISO-8859-1", "ignore")

# convert s, which is an Unicode string, to an object suitable for passing
# to Python's file APIs. this is either the Unicode string itself, if the
# platform supports Unicode-based APIs (and Python has implemented support
# for it), or the Unicode string converted to UTF-8 on other platforms.
def toPath(s):
    if unicodeFS:
        return s
    else:
        return s.encode("UTF-8")

# return bitmap created from the given file. argument is as for
# getFullPath.
def getBitmap(filename):
    return wx.Bitmap(getFullPath(filename))

# return the absolute path of a file under the install dir. so passing in
# "resources/blaa.png" might return "/opt/trelby/resources/blaa.png" for
# example.
def getFullPath(relative):
    return progPath + "/" + relative

class MyColorSample(wx.Window):
    def __init__(self, parent, id, size):
        wx.Window.__init__(self, parent, id, size = size)

        wx.EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        w, h = self.GetClientSizeTuple()
        br = wx.Brush(self.GetBackgroundColour())
        dc.SetBrush(br)
        dc.DrawRectangle(0, 0, w, h)

# Custom "exit fullscreen" button for our tab bar. Used so that we have
# full control over the button's size.
class MyFSButton(wx.Window):
    def __init__(self, parent, id, getCfgGui):
        wx.Window.__init__(self, parent, id, size = (TAB_BAR_HEIGHT, TAB_BAR_HEIGHT))

        self.getCfgGui = getCfgGui
        self.fsImage = getBitmap("resources/fullscreen.png")

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_LEFT_DOWN(self, self.OnMouseDown)

    def OnPaint(self, event):
        cfgGui = self.getCfgGui()
        dc = wx.PaintDC(self)

        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.tabNonActiveBgBrush)
        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawRectangle(0, 0, w, h)

        off = (h - self.fsImage.GetHeight()) // 2
        dc.DrawBitmap(self.fsImage, off, off)

    def OnMouseDown(self, event):
        clickEvent = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.GetId())
        clickEvent.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(clickEvent)

# custom status control
class MyStatus(wx.Window):
    WIDTH = 280
    X_ELEDIVIDER = 100

    def __init__(self, parent, id, getCfgGui):
        wx.Window.__init__(self, parent, id, size = (MyStatus.WIDTH, TAB_BAR_HEIGHT),
                           style = wx.FULL_REPAINT_ON_RESIZE)

        self.getCfgGui = getCfgGui

        self.page = 0
        self.pageCnt = 0
        self.elemType = ""
        self.tabNext = ""
        self.enterNext = ""

        self.elementFont = util.createPixelFont(
            TAB_BAR_HEIGHT // 2 + 6, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)

        self.font = util.createPixelFont(
            TAB_BAR_HEIGHT // 2 + 2, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)

        wx.EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        cfgGui = self.getCfgGui()

        cy = (TAB_BAR_HEIGHT - 1) // 2
        xoff = 5

        dc = wx.PaintDC(self)
        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.tabBarBgBrush)
        dc.SetPen(cfgGui.tabBarBgPen)
        dc.DrawRectangle(0, 0, w, h)

        dc.SetPen(cfgGui.tabTextPen)
        dc.SetTextForeground(cfgGui.tabTextColor)

        pageText = "Page %d / %d" % (self.page, self.pageCnt)
        dc.SetFont(self.font)

        util.drawText(dc, pageText, MyStatus.WIDTH - xoff, cy,
            util.ALIGN_RIGHT, util.VALIGN_CENTER)

        s1 = "%s [Enter]" % self.enterNext
        s2 = "%s [Tab]" % self.tabNext

        x = MyStatus.X_ELEDIVIDER + xoff
        dc.DrawText(s1, x, 0)
        dc.DrawText(s2, x, cy)

        x = xoff
        s = "%s" % self.elemType
        dc.SetFont(self.elementFont)
        util.drawText(dc, s, x, cy, valign = util.VALIGN_CENTER)

        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawLine(0, h-1, w, h-1)

        for x in (MyStatus.X_ELEDIVIDER, 0):
            dc.DrawLine(x, 0, x, h-1)

    def SetValues(self, page, pageCnt, elemType, tabNext, enterNext):
        self.page = page
        self.pageCnt = pageCnt
        self.elemType = elemType
        self.tabNext = tabNext
        self.enterNext = enterNext

        self.Refresh(False)


# our own version of a tab control, which exists for two reasons: it does
# not care where it is physically located, which allows us to combine it
# with other controls on a horizontal row, and it consumes less vertical
# space than wx.Notebook. note that this control is divided into two parts,
# MyTabCtrl and MyTabCtrl2, and both must be created.
class MyTabCtrl(wx.Window):
    def __init__(self, parent, id, getCfgGui):
        style = wx.FULL_REPAINT_ON_RESIZE
        wx.Window.__init__(self, parent, id, style = style)

        self.getCfgGui = getCfgGui

        # pages, i.e., [wx.Window, name] lists. note that 'name' must be an
        # Unicode string.
        self.pages = []

        # index of selected page
        self.selected = -1

        # index of first visible tab
        self.firstTab = 0

        # how much padding to leave horizontally at the ends of the
        # control, and within each tab
        self.paddingX = 10

        # starting Y-pos of text in labels
        self.textY = 5

        # width of a single tab
        self.tabWidth = 150

        # width, height, spacing, y-pos of arrows
        self.arrowWidth = 8
        self.arrowHeight = 13
        self.arrowSpacing = 3
        self.arrowY = 5

        # initialized in OnPaint since we don't know our height yet
        self.font = None
        self.boldFont = None

        self.SetMinSize(wx.Size(
                self.paddingX * 2 + self.arrowWidth * 2 + self.arrowSpacing +\
                    self.tabWidth + 5,
                TAB_BAR_HEIGHT))

        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_LEFT_DCLICK(self, self.OnLeftDown)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

    # get the ctrl that the tabbed windows should use as a parent
    def getTabParent(self):
        return self.ctrl2

    # get page count
    def getPageCount(self):
        return len(self.pages)

    # get selected page index
    def getSelectedPageIndex(self):
        return self.selected

    # get given page
    def getPage(self, i):
        return self.pages[i][0]

    # MyTabCtrl2 uses this to register itself with us
    def add2(self, ctrl2):
        self.ctrl2 = ctrl2

    # add page
    def addPage(self, page, name):
        self.pages.append([page, name])

        # the new page must be given the correct size and position
        self.setPageSizes()
        page.MoveXY(0, 0)

        self.selectPage(len(self.pages) - 1)

    # set all page's sizes
    def setPageSizes(self):
        size = self.ctrl2.GetClientSize()

        for p in self.pages:
            p[0].SetClientSizeWH(size.width, size.height)

    # select given page
    def selectPage(self, page):
        self.selected = page

        for i in range(len(self.pages)):
            w = self.pages[i][0]

            if i == self.selected:
                w.Show()
            else:
                w.Hide()

        self.pageChangeFunc(self.selected)
        self.makeSelectedTabVisible()
        self.Refresh(False)

    # delete given page
    def deletePage(self, i):
        self.pages[i][0].Destroy()
        del self.pages[i]

        self.selectPage(util.clamp(i, 0, len(self.pages) - 1))

    # try to change the first visible tag by the given amount.
    def scroll(self, delta):
        newFirstTab = self.firstTab + delta

        if (newFirstTab >= 0) and (newFirstTab < len(self.pages)):
            self.firstTab = newFirstTab
            self.Refresh(False)

    # calculate the maximum number of tabs that we could show with our
    # current size.
    def calcMaxVisibleTabs(self):
        w = self.GetClientSizeTuple()[0]

        w -= self.paddingX * 2
        w -= self.arrowWidth * 2 + self.arrowSpacing

        # leave at least 2 pixels between left arrow and last tab
        w -= 2

        w //= self.tabWidth

        # if by some freak accident we're so small that the above results
        # in w being negative or positive but too small, guard against us
        # ever returning < 1.
        return max(1, w)

    # get last visible tab
    def getLastVisibleTab(self):
        return util.clamp(self.firstTab + self.calcMaxVisibleTabs() - 1,
                          maxVal = len(self.pages) - 1)

    # make sure selected tab is visible
    def makeSelectedTabVisible(self):
        maxTab = self.getLastVisibleTab()

        # if already visible, no need to do anything
        if (self.selected >= self.firstTab) and (self.selected <= maxTab):
            return

        # otherwise, position the selected tab as far right as possible
        self.firstTab = util.clamp(
            self.selected - self.calcMaxVisibleTabs() + 1,
            0)

    # set text for tab 'i' to 's'
    def setTabText(self, i, s):
        self.pages[i][1] = s
        self.Refresh(False)

    # set function to call when page changes. the function gets a single
    # integer argument, the index of the new page.
    def setPageChangedFunc(self, func):
        self.pageChangeFunc = func

    def OnLeftDown(self, event):
        x = event.GetPosition().x

        if x < self.paddingX:
            return

        w = self.GetClientSizeTuple()[0]

        # start of left arrow
        lx = w - 1 - self.paddingX - self.arrowWidth - self.arrowSpacing \
             - self.arrowWidth + 1

        if x < lx:
            page, pageOffset = divmod(x - self.paddingX, self.tabWidth)
            page += self.firstTab

            if page < len(self.pages):
                hitX = pageOffset >= (self.tabWidth - self.paddingX * 2)

                if hitX:
                    panel = self.pages[page][0]
                    if not panel.ctrl.canBeClosed():
                        return

                    if self.getPageCount() > 1:
                        self.deletePage(page)
                    else:
                        panel.ctrl.createEmptySp()
                        panel.ctrl.updateScreen()
                else:
                    self.selectPage(page)
        else:
            if x < (lx + self.arrowWidth):
                self.scroll(-1)

            # start of right arrow
            rx = lx + self.arrowWidth + self.arrowSpacing

            if (x >= rx) and (x < (rx + self.arrowWidth)) and \
                   (self.getLastVisibleTab() < (len(self.pages) - 1)):
                self.scroll(1)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wx.EmptyBitmap(size.width, size.height)

    def OnEraseBackground(self, event):
        pass

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        cfgGui = self.getCfgGui()

        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.tabBarBgBrush)
        dc.SetPen(cfgGui.tabBarBgPen)
        dc.DrawRectangle(0, 0, w, h)

        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawLine(0,h-1,w,h-1)

        xpos = self.paddingX

        tabW = self.tabWidth
        tabH = h - 2
        tabY = h - tabH

        if not self.font:
            textH = h - self.textY - 1
            self.font = util.createPixelFont(
                textH, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
            self.boldFont = util.createPixelFont(
                textH, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD)

        maxTab = self.getLastVisibleTab()

        for i in range(self.firstTab, maxTab + 1):
            dc.SetFont(self.font)
            p = self.pages[i]

            dc.DestroyClippingRegion()
            dc.SetClippingRegion(xpos, tabY, tabW, tabH)
            dc.SetPen(cfgGui.tabBorderPen)

            if i == self.selected:
                points=((6,1),(tabW-8,1),(tabW-6,2),(tabW-2,tabH),(0,tabH),(4,2))
                dc.SetBrush(cfgGui.workspaceBrush)
            else:
                points=((5,2),(tabW-8,2),(tabW-6,3),(tabW-2,tabH-1),(0,tabH-1),(3,3))
                dc.SetBrush(cfgGui.tabNonActiveBgBrush)

            dc.DrawPolygon(points,xpos,tabY)

            # clip the text to fit within the tabs
            dc.DestroyClippingRegion()
            dc.SetClippingRegion(xpos, tabY, tabW - self.paddingX * 3, tabH)

            dc.SetPen(cfgGui.tabTextPen)
            dc.SetTextForeground(cfgGui.tabTextColor)
            dc.DrawText(p[1], xpos + self.paddingX, self.textY)

            dc.DestroyClippingRegion()
            dc.SetFont(self.boldFont)
            dc.DrawText("�", xpos + tabW - self.paddingX * 2, self.textY)

            xpos += tabW

        # start of right arrow
        rx = w - 1 - self.paddingX - self.arrowWidth + 1

        if self.firstTab != 0:
            dc.DestroyClippingRegion()
            dc.SetPen(cfgGui.tabTextPen)

            util.drawLine(dc, rx - self.arrowSpacing - 1, self.arrowY,
                          0, self.arrowHeight)
            util.drawLine(dc, rx - self.arrowSpacing - 2, self.arrowY,
                          -self.arrowWidth + 1, self.arrowHeight // 2 + 1)
            util.drawLine(dc, rx - self.arrowSpacing - self.arrowWidth,
                          self.arrowY + self.arrowHeight // 2,
                          self.arrowWidth - 1, self.arrowHeight // 2 + 1)

        if maxTab < (len(self.pages) - 1):
            dc.DestroyClippingRegion()
            dc.SetPen(cfgGui.tabTextPen)

            util.drawLine(dc, rx, self.arrowY, 0, self.arrowHeight)
            util.drawLine(dc, rx + 1, self.arrowY, self.arrowWidth - 1,
                          self.arrowHeight // 2 + 1)
            util.drawLine(dc, rx + 1, self.arrowY + self.arrowHeight - 1,
                          self.arrowWidth - 1, -(self.arrowHeight // 2 + 1))

# second part of MyTabCtrl
class MyTabCtrl2(wx.Window):
    def __init__(self, parent, id, tabCtrl):
        wx.Window.__init__(self, parent, id)

        # MyTabCtrl
        self.tabCtrl = tabCtrl

        self.tabCtrl.add2(self)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        self.tabCtrl.setPageSizes()

    # we have an OnPaint handler that does nothing in a feeble attempt in
    # trying to make sure that in the cases when this does get called, as
    # little (useless) work as possible is done.
    def OnPaint(self, event):
        dc = wx.PaintDC(self)

# dialog that shows two lists of script names, allowing user to choose one
# from both. stores indexes of selections in members named 'sel1' and
# 'sel2' when OK is pressed. 'items' must have at least two items.
class ScriptChooserDlg(wx.Dialog):
    def __init__(self, parent, items):
        wx.Dialog.__init__(self, parent, -1, "Choose scripts",
                           style = wx.DEFAULT_DIALOG_STYLE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        self.addCombo("first", "Compare script", self, gsizer, items, 0)
        self.addCombo("second", "to", self, gsizer, items, 1)

        vsizer.Add(gsizer)

        self.forceCb = wx.CheckBox(self, -1, "Use same configuration")
        self.forceCb.SetValue(True)
        vsizer.Add(self.forceCb, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def addCombo(self, name, descr, parent, sizer, items, sel):
        al = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT
        if sel == 1:
            al |= wx.ALIGN_RIGHT

        sizer.Add(wx.StaticText(parent, -1, descr), 0, al, 10)

        combo = wx.ComboBox(parent, -1, style = wx.CB_READONLY)
        util.setWH(combo, w = 200)

        for s in items:
            combo.Append(s)

        combo.SetSelection(sel)

        sizer.Add(combo)

        setattr(self, name + "Combo", combo)

    def OnOK(self, event):
        self.sel1 = self.firstCombo.GetSelection()
        self.sel2 = self.secondCombo.GetSelection()
        self.forceSameCfg = bool(self.forceCb.GetValue())

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

# CheckBoxDlg below handles lists of these
class CheckBoxItem:
    def __init__(self, text, selected = True, cdata = None):
        self.text = text
        self.selected = selected
        self.cdata = cdata

    # return dict which has keys for all selected items' client data.
    # takes a list of CheckBoxItem's as its parameter. note: this is a
    # static function.
    @staticmethod
    def getClientData(cbil):
        tmp = {}

        for i in range(len(cbil)):
            cbi = cbil[i]

            if cbi.selected:
                tmp[cbi.cdata] = None

        return tmp

# shows one or two (one if cbil2 = None) checklistbox widgets with
# contents from cbil1 and possibly cbil2, which are lists of
# CheckBoxItems. btns[12] are bools for whether or not to include helper
# buttons. if OK is pressed, the incoming lists' items' selection status
# will be modified.
class CheckBoxDlg(wx.Dialog):
    def __init__(self, parent, title, cbil1, descr1, btns1,
                 cbil2 = None, descr2 = None, btns2 = None):
        wx.Dialog.__init__(self, parent, -1, title,
                           style = wx.DEFAULT_DIALOG_STYLE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.cbil1 = cbil1
        self.list1 = self.addList(descr1, self, vsizer, cbil1, btns1, True)

        if cbil2 != None:
            self.cbil2 = cbil2
            self.list2 = self.addList(descr2, self, vsizer, cbil2, btns2,
                                      False, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def addList(self, descr, parent, sizer, items, doBtns, isFirst, pad = 0):
        sizer.Add(wx.StaticText(parent, -1, descr), 0, wx.TOP, pad)

        if doBtns:
            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            if isFirst:
                funcs = [ self.OnSet1, self.OnClear1, self.OnToggle1 ]
            else:
                funcs = [ self.OnSet2, self.OnClear2, self.OnToggle2 ]

            tmp = wx.Button(parent, -1, "Set")
            hsizer.Add(tmp)
            wx.EVT_BUTTON(self, tmp.GetId(), funcs[0])

            tmp = wx.Button(parent, -1, "Clear")
            hsizer.Add(tmp, 0, wx.LEFT, 10)
            wx.EVT_BUTTON(self, tmp.GetId(), funcs[1])

            tmp = wx.Button(parent, -1, "Toggle")
            hsizer.Add(tmp, 0, wx.LEFT, 10)
            wx.EVT_BUTTON(self, tmp.GetId(), funcs[2])

            sizer.Add(hsizer, 0, wx.TOP | wx.BOTTOM, 5)

        tmp = wx.CheckListBox(parent, -1)

        longest = -1
        for i in range(len(items)):
            it = items[i]

            tmp.Append(it.text)
            tmp.Check(i, it.selected)

            if isFirst:
                if longest != -1:
                    if len(it.text) > len(items[longest].text):
                        longest = i
                else:
                    longest = 0

        w = -1
        if isFirst:
            h = len(items)
            if longest != -1:
                w = util.getTextExtent(tmp.GetFont(),
                                       "[x] " + items[longest].text)[0] + 15
        else:
            h = min(10, len(items))

        # don't know of a way to get the vertical spacing of items in a
        # wx.CheckListBox, so estimate it at font height + 5 pixels, which
        # is close enough on everything I've tested.
        h *= util.getFontHeight(tmp.GetFont()) + 5
        h += 5
        h = max(25, h)

        util.setWH(tmp, w, h)
        sizer.Add(tmp, 0, wx.EXPAND)

        return tmp

    def storeResults(self, cbil, ctrl):
        for i in range(len(cbil)):
            cbil[i].selected = bool(ctrl.IsChecked(i))

    def setAll(self, ctrl, state):
        for i in range(ctrl.GetCount()):
            ctrl.Check(i, state)

    def toggle(self, ctrl):
        for i in range(ctrl.GetCount()):
            ctrl.Check(i, not ctrl.IsChecked(i))

    def OnSet1(self, event):
        self.setAll(self.list1, True)

    def OnClear1(self, event):
        self.setAll(self.list1, False)

    def OnToggle1(self, event):
        self.toggle(self.list1)

    def OnSet2(self, event):
        self.setAll(self.list2, True)

    def OnClear2(self, event):
        self.setAll(self.list2, False)

    def OnToggle2(self, event):
        self.toggle(self.list2)

    def OnOK(self, event):
        self.storeResults(self.cbil1, self.list1)

        if hasattr(self, "list2"):
            self.storeResults(self.cbil2, self.list2)

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

# shows a multi-line string to the user in a scrollable text control.
class TextDlg(wx.Dialog):
    def __init__(self, parent, text, title):
        wx.Dialog.__init__(self, parent, -1, title,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tc = wx.TextCtrl(self, -1, size = wx.Size(400, 200),
                         style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_LINEWRAP)
        tc.SetValue(text)
        vsizer.Add(tc, 1, wx.EXPAND);

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        okBtn = gutil.createStockButton(self, "OK")
        vsizer.Add(okBtn, 0, wx.ALIGN_CENTER)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

# helper function for using TextDlg
def showText(parent, text, title = "Message"):
    dlg = TextDlg(parent, text, title)
    dlg.ShowModal()
    dlg.Destroy()

# ask user for a single-line text input.
class TextInputDlg(wx.Dialog):
    def __init__(self, parent, text, title, validateFunc = None):
        wx.Dialog.__init__(self, parent, -1, title,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.WANTS_CHARS)

        # function to call to validate the input string on OK. can be
        # None, in which case it is not called. if it returns "", the
        # input is valid, otherwise the string it returns is displayed in
        # a message box and the dialog is not closed.
        self.validateFunc = validateFunc

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, text), 1, wx.EXPAND | wx.BOTTOM, 5)

        self.tc = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        vsizer.Add(self.tc, 1, wx.EXPAND);

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 5)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        wx.EVT_TEXT_ENTER(self, self.tc.GetId(), self.OnOK)

        wx.EVT_CHAR(self.tc, self.OnCharEntry)
        wx.EVT_CHAR(cancelBtn, self.OnCharButton)
        wx.EVT_CHAR(okBtn, self.OnCharButton)

        self.tc.SetFocus()

    def OnCharEntry(self, event):
        self.OnChar(event, True)

    def OnCharButton(self, event):
        self.OnChar(event, False)

    def OnChar(self, event, isEntry):
        kc = event.GetKeyCode()

        if kc == wx.WXK_ESCAPE:
            self.OnCancel()

        elif (kc == wx.WXK_RETURN) and isEntry:
                self.OnOK()

        else:
            event.Skip()

    def OnOK(self, event = None):
        self.input = fromGUI(self.tc.GetValue())

        if self.validateFunc:
            msg = self.validateFunc(self.input)

            if msg:
                wx.MessageBox(msg, "Error", wx.OK, self)

                return

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event = None):
        self.EndModal(wx.ID_CANCEL)

# asks the user for a keypress and stores it.
class KeyDlg(wx.Dialog):
    def __init__(self, parent, cmdName):
        wx.Dialog.__init__(self, parent, -1, "Key capture",
                           style = wx.DEFAULT_DIALOG_STYLE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Press the key combination you\n"
            "want to bind to the command\n'%s'." % cmdName))

        tmp = KeyDlgWidget(self, -1, (1, 1))
        vsizer.Add(tmp)

        util.finishWindow(self, vsizer)

        tmp.SetFocus()

# used by KeyDlg
class KeyDlgWidget(wx.Window):
    def __init__(self, parent, id, size):
        wx.Window.__init__(self, parent, id, size = size,
                           style = wx.WANTS_CHARS)

        wx.EVT_CHAR(self, self.OnKeyChar)

    def OnKeyChar(self, ev):
        p = self.GetParent()
        p.key = util.Key.fromKE(ev)
        p.EndModal(wx.ID_OK)

# handles the "Most recently used" list of files in a menu.
class MRUFiles:
    def __init__(self, maxCount):
        # max number of items
        self.maxCount = maxCount

        # items (Unicode strings)
        self.items = []

        for i in range(self.maxCount):
            id = wx.NewId()

            if i == 0:
                # first menu id
                self.firstId = id
            elif i == (self.maxCount - 1):
                # last menu id
                self.lastId = id

    # use given menu. this must be called before any "add" calls.
    def useMenu(self, menu, menuPos):
        # menu to use
        self.menu = menu

        # position in menu to add first item at
        self.menuPos = menuPos

        # if we already have items, add them to the menu (in reverse order
        # to maintain the correct ordering)
        tmp = self.items
        tmp.reverse()
        self.items = []

        for it in tmp:
            self.add(it)

    # return (firstMenuId, lastMenuId).
    def getIds(self):
        return (self.firstId, self.lastId)

    # add item.
    def add(self, s):
        # remove old menu items
        for i in range(self.getCount()):
            self.menu.Delete(self.firstId + i)

        # if item already exists, remove it
        try:
            i = self.items.index(s)
            del self.items[i]
        except ValueError:
            pass

        # add item to top of list
        self.items.insert(0, s)

        # prune overlong list
        if self.getCount() > self.maxCount:
            self.items = self.items[:self.maxCount]

        # add new menu items
        for i in range(self.getCount()):
            self.menu.Insert(self.menuPos + i, self.firstId + i,
                             "&%d %s" % (
                i + 1, os.path.basename(self.get(i))))

    # return number of items.
    def getCount(self):
        return len(self.items)

    # get item number 'i'.
    def get(self, i):
        return self.items[i]

########NEW FILE########
__FILENAME__ = myimport
import config
import gutil
import misc
import screenplay
import util

from lxml import etree
import wx

import StringIO
import re
import zipfile

# special linetype that means that indent contains action and scene lines,
# and scene lines are the ones that begin with "EXT." or "INT."
SCENE_ACTION = -2

# special linetype that means don't import those lines; useful for page
# numbers etc
IGNORE = -3

#like importTextFile, but for Adobe Story files.
def importAstx(fileName, frame):
    # astx files are xml files. The textlines can be found under
    # AdobeStory/document/stream/section/scene/paragraph which contain
    # one or more textRun/break elements, to be joined. The paragraph
    # attribute "element" gives us the element style.

    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    elemMap = {
        "Action" : screenplay.ACTION,
        "Character" : screenplay.CHARACTER,
        "Dialog" : screenplay.DIALOGUE,
        "Parenthetical" : screenplay.PAREN,
        "SceneHeading" : screenplay.SCENE,
        "Shot" : screenplay.SHOT,
        "Transition" : screenplay.TRANSITION,
    }

    try:
        root = etree.XML(data)
    except etree.XMLSyntaxError, e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, items):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not items[-1] and (len(items) > 1):
            items = items[:-1]

        for s in items[:-1]:
            lines.append(screenplay.Line(
                    screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(screenplay.Line(
                screenplay.LB_LAST, eleType, util.cleanInput(items[-1])))

    for para in root.xpath("/AdobeStory/document/stream/section/scene/paragraph"):
        lt = elemMap.get(para.get("element"), screenplay.ACTION)

        items = []
        s = u""

        for text in para:
            if text.tag == "textRun" and text.text:
                s += text.text
            elif text.tag == "break":
                items.append(s.rstrip())
                s = u""

        items.append(s.rstrip())

        addElem(lt, items)

    if not lines:
        wx.MessageBox("File has no content.", "Error", wx.OK, frame)
        return None

    return lines

# like importTextFile, but for fadein files.
def importFadein(fileName, frame):
    # Fadein file is a zipped document.xml file.
    # the .xml is in open screenplay format:
    # http://sourceforge.net/projects/openscrfmt/files/latest/download

    # the 5 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    buf = StringIO.StringIO(data)

    try:
        z = zipfile.ZipFile(buf)
        f = z.open("document.xml")
        content = f.read()
        z.close()
    except:
        wx.MessageBox("File is not a valid .fadein file.", "Error", wx.OK, frame)
        return None

    if not content:
        wx.MessageBox("Script seems to be empty.", "Error", wx.OK, frame)
        return None

    elemMap = {
        "Action" : screenplay.ACTION,
        "Character" : screenplay.CHARACTER,
        "Dialogue" : screenplay.DIALOGUE,
        "Parenthetical" : screenplay.PAREN,
        "Scene Heading" : screenplay.SCENE,
        "Shot" : screenplay.SHOT,
        "Transition" : screenplay.TRANSITION,
    }

    try:
        root = etree.XML(content)
    except etree.XMLSyntaxError, e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, lns):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not lns[-1] and (len(lns) > 1):
            lns = lns[:-1]

        for s in lns[:-1]:
            lines.append(screenplay.Line(
                    screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(screenplay.Line(
                screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

    # removes html formatting from s, and returns list of lines.
    # if s is None, return a list with single empty string.
    re_rem = [r'<font[^>]*>', r'<size[^>]*>', r'<bgcolor[^>]*>']
    rem = ["<b>", "</b>", "<i>", "</i>", "<u>",
           "</u>", "</font>", "</size>", "</bgcolor>"]
    def sanitizeStr(s):
        if s:
            s = u"" + s
            for r in re_rem:
                s = re.sub(r, "", s)
            for r in rem:
                s = s.replace(r,"")

            if s:
                return s.split("<br>")
            else:
                return [u""]
        else:
            return [u""]

    for para in root.xpath("paragraphs/para"):
        # check for notes/synopsis, import as Note.
        if para.get("note"):
            lt = screenplay.NOTE
            items = sanitizeStr(u"" + para.get("note"))
            addElem(lt, items)

        if para.get("synopsis"):
            lt = screenplay.NOTE
            items = sanitizeStr(u"" + para.get("synopsis"))
            addElem(lt, items)

        # look for the <style> and <text> tags. Bail if no <text> found.
        styl = para.xpath("style")
        txt = para.xpath("text")
        if txt:
            if styl:
                lt = elemMap.get(styl[0].get("basestylename"), screenplay.ACTION)
            else:
                lt = screenplay.ACTION

            items = sanitizeStr(txt[0].text)

            if (lt == screenplay.PAREN) and items and (items[0][0] != "("):
                items[0] = "(" + items[0]
                items[-1] = items[-1] + ")"
        else:
            continue

        addElem(lt, items)

    if len(lines) == 0:
        wx.MessageBox("The file contains no importable lines", "Error", wx.OK, frame)
        return None

    return lines

# like importTextFile, but for Celtx files.
def importCeltx(fileName, frame):
    # Celtx files are zipfiles, and the script content is within a file
    # called "script-xxx.html", where xxx can be random.

    # the 5 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    buf = StringIO.StringIO(data)

    try:
        z = zipfile.ZipFile(buf)
    except:
        wx.MessageBox("File is not a valid Celtx script file.", "Error", wx.OK, frame)
        return None

    files = z.namelist()
    scripts = [s for s in files if s.startswith("script") ]

    if len(scripts) == 0:
        wx.MessageBox("Unable to find script in this Celtx file.", "Error", wx.OK, frame)
        return None

    f = z.open(scripts[0])
    content = f.read()
    z.close()

    if not content:
        wx.MessageBox("Script seems to be empty.", "Error", wx.OK, frame)
        return None

    elemMap = {
        "action" : screenplay.ACTION,
        "character" : screenplay.CHARACTER,
        "dialog" : screenplay.DIALOGUE,
        "parenthetical" : screenplay.PAREN,
        "sceneheading" : screenplay.SCENE,
        "shot" : screenplay.SHOT,
        "transition" : screenplay.TRANSITION,
        "act" : screenplay.ACTBREAK,
    }

    try:
        parser = etree.HTMLParser()
        root = etree.XML(content, parser)
    except etree.XMLSyntaxError, e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

    lines = []

    def addElem(eleType, lns):
        # if elem ends in a newline, last line is empty and useless;
        # get rid of it
        if not lns[-1] and (len(lns) > 1):
            lns = lns[:-1]

        for s in lns[:-1]:
            lines.append(screenplay.Line(
                    screenplay.LB_FORCED, eleType, util.cleanInput(s)))

        lines.append(screenplay.Line(
                screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

    for para in root.xpath("/html/body/p"):
        items = []
        for line in para.itertext():
            items.append(unicode(line.replace("\n", " ")))

        lt = elemMap.get(para.get("class"), screenplay.ACTION)

        if items:
            addElem(lt, items)

    if len(lines) == 0:
        wx.MessageBox("The file contains no importable lines", "Error", wx.OK, frame)
        return None

    return lines

# like importTextFile, but for Final Draft files.
def importFDX(fileName, frame):
    elemMap = {
        "Action" : screenplay.ACTION,
        "Character" : screenplay.CHARACTER,
        "Dialogue" : screenplay.DIALOGUE,
        "Parenthetical" : screenplay.PAREN,
        "Scene Heading" : screenplay.SCENE,
        "Shot" : screenplay.SHOT,
        "Transition" : screenplay.TRANSITION,
    }

    # the 5 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 5000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    try:
        root = etree.XML(data)
        lines = []

        def addElem(eleType, eleText):
            lns = eleText.split("\n")

            # if elem ends in a newline, last line is empty and useless;
            # get rid of it
            if not lns[-1] and (len(lns) > 1):
                lns = lns[:-1]

            for s in lns[:-1]:
                lines.append(screenplay.Line(
                        screenplay.LB_FORCED, eleType, util.cleanInput(s)))

            lines.append(screenplay.Line(
                    screenplay.LB_LAST, eleType, util.cleanInput(lns[-1])))

        for para in root.xpath("Content//Paragraph"):
            addedNote = False
            et = para.get("Type")

            # Check for script notes
            s = u""
            for notes in para.xpath("ScriptNote/Paragraph/Text"):
                if notes.text:
                    s += notes.text

                # FD has AdornmentStyle set to "0" on notes with newline.
                if notes.get("AdornmentStyle") == "0":
                    s += "\n"

            if s:
                addElem(screenplay.NOTE, s)
                addedNote = True

            # "General" has embedded Dual Dialogue paragraphs inside it;
            # nothing to do for the General element itself.
            #
            # If no type is defined (like inside scriptnote), skip.
            if (et == "General") or (et is None):
                continue

            s = u""
            for text in para.xpath("Text"):
                # text.text is None for paragraphs with no text, and +=
                # blows up trying to add a string object and None, so
                # guard against that
                if text.text:
                    s += text.text

            # don't remove paragraphs with no text, unless that paragraph
            # contained a scriptnote
            if s or not addedNote:
                lt = elemMap.get(et, screenplay.ACTION)
                addElem(lt, s)

        if len(lines) == 0:
            wx.MessageBox("The file contains no importable lines", "Error", wx.OK, frame)
            return None

        return lines

    except etree.XMLSyntaxError, e:
        wx.MessageBox("Error parsing file: %s" %e, "Error", wx.OK, frame)
        return None

# import Fountain files.
# http://fountain.io
def importFountain(fileName, frame):
    # regular expressions for fountain markdown.
    # https://github.com/vilcans/screenplain/blob/master/screenplain/richstring.py
    ire = re.compile(
            # one star
            r'\*'
            # anything but a space, then text
            r'([^\s].*?)'
            # finishing with one star
            r'\*'
            # must not be followed by star
            r'(?!\*)'
        )
    bre = re.compile(
            # two stars
            r'\*\*'
            # must not be followed by space
            r'(?=\S)'
            # inside text
            r'(.+?[*_]*)'
            # finishing with two stars
            r'(?<=\S)\*\*'
        )
    ure = re.compile(
            # underline
            r'_'
            # must not be followed by space
            r'(?=\S)'
            # inside text
            r'([^_]+)'
            # finishing with underline
            r'(?<=\S)_'
        )
    boneyard_re = re.compile('/\\*.*?\\*/', flags=re.DOTALL)

    # random magicstring used to escape literal star '\*'
    literalstar = "Aq7RR"

    # returns s with markdown formatting removed.
    def unmarkdown(s):
        s = s.replace("\\*", literalstar)
        for style in (bre, ire, ure):
            s = style.sub(r'\1', s)
        return s.replace(literalstar, "*")

    data = util.loadFile(fileName, frame, 1000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)
        return None

    inf = []
    inf.append(misc.CheckBoxItem("Import titles as action lines."))
    inf.append(misc.CheckBoxItem("Remove unsupported formatting markup."))
    inf.append(misc.CheckBoxItem("Import section/synopsis as notes."))

    dlg = misc.CheckBoxDlg(frame, "Fountain import options", inf,
        "Import options:", False)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        return None

    importTitles = inf[0].selected
    removeMarkdown = inf[1].selected
    importSectSyn = inf[2].selected

    # pre-process data - fix newlines, remove boneyard.
    data = util.fixNL(data)
    data = boneyard_re.sub('', data)
    prelines = data.split("\n")
    for i in xrange(len(prelines)):
        try:
            util.toLatin1(prelines[i])
        except:
            prelines[i] = util.cleanInput(u"" + prelines[i].decode('UTF-8', "ignore"))
    lines = []

    tabWidth = 4
    lns = []
    sceneStartsList = ("INT", "EXT", "EST", "INT./EXT", "INT/EXT", "I/E", "I./E")
    TWOSPACE = "  "
    skipone = False

    # First check if title lines are present:
    c = 0
    while c < len(prelines):
        if prelines[c] != "":
            c = c+1
        else:
            break

    # prelines[0:i] are the first bunch of lines, that could be titles.
    # Our check for title is simple:
    #   - the line does not start with 'fade'
    #   - the first line has a single ':'

    if c > 0:
        l = util.toInputStr(prelines[0].expandtabs(tabWidth).lstrip().lower())
        if not l.startswith("fade") and l.count(":") == 1:
            # these are title lines. Now do what the user requested.
            if importTitles:
                # add TWOSPACE to all the title lines.
                for i in xrange(c):
                    prelines[i] += TWOSPACE
            else:
                #remove these lines
                prelines = prelines[c+1:]

    for l in prelines:
        if l != TWOSPACE:
            lines.append(util.toInputStr(l.expandtabs(tabWidth)))
        else:
            lines.append(TWOSPACE)

    linesLen = len(lines)

    def isPrevEmpty():
        if lns and lns[-1].text == "":
            return True
        return False

    def isPrevType(ltype):
        return (lns and lns[-1].lt == ltype)

    # looks ahead to check if next line is not empty
    def isNextEmpty(i):
        return  (i+1 < len(lines) and lines[i+1] == "")

    def getPrevType():
        if lns:
            return lns[-1].lt
        else:
            return screenplay.ACTION

    def isParen(s):
        return (s.startswith('(') and s.endswith(')'))

    def isScene(s):
        if s.endswith(TWOSPACE):
            return False
        if s.startswith(".") and not s.startswith(".."):
            return True
        tmp = s.upper()
        if (re.match(r'^(INT|EXT|EST)[ .]', tmp) or
            re.match(r'^(INT\.?/EXT\.?)[ .]', tmp) or
            re.match(r'^I/E[ .]', tmp)):
            return True
        return False

    def isTransition(s):
        return ((s.isupper() and s.endswith("TO:")) or
                (s.startswith(">") and not s.endswith("<")))

    def isCentered(s):
        return s.startswith(">") and s.endswith("<")

    def isPageBreak(s):
        return s.startswith('===') and s.lstrip('=') == ''

    def isNote(s):
        return s.startswith("[[") and s.endswith("]]")

    def isSection(s):
        return s.startswith("#")

    def isSynopsis(s):
        return s.startswith("=") and not s.startswith("==")

    # first pass - identify linetypes
    for i in range(linesLen):
        if skipone:
            skipone = False
            continue

        s = lines[i]
        sl = s.lstrip()
        # mark as ACTION by default.
        line = screenplay.Line(screenplay.LB_FORCED, screenplay.ACTION, s)

        # Start testing lines for element type. Go in order:
        # Scene Character, Paren, Dialog, Transition, Note.

        if s == "" or isCentered(s) or isPageBreak(s):
            # do nothing - import as action.
            pass

        elif s == TWOSPACE:
            line.lt = getPrevType()

        elif isScene(s):
            line.lt = screenplay.SCENE
            if sl.startswith('.'):
                line.text = sl[1:]
            else:
                line.text = sl

        elif isTransition(sl) and isPrevEmpty() and isNextEmpty(i):
            line.lt = screenplay.TRANSITION
            if line.text.startswith('>'):
                line.text = sl[1:].lstrip()

        elif s.isupper() and isPrevEmpty() and not isNextEmpty(i):
            line.lt = screenplay.CHARACTER
            if s.endswith(TWOSPACE):
                line.lt = screenplay.ACTION

        elif isParen(sl) and (isPrevType(screenplay.CHARACTER) or
                                isPrevType(screenplay.DIALOGUE)):
            line.lt = screenplay.PAREN

        elif (isPrevType(screenplay.CHARACTER) or
             isPrevType(screenplay.DIALOGUE) or
             isPrevType(screenplay.PAREN)):
            line.lt = screenplay.DIALOGUE

        elif isNote(sl):
            line.lt = screenplay.NOTE
            line.text = sl.strip('[]')

        elif isSection(s) or isSynopsis(s):
            if not importSectSyn:
                if isNextEmpty(i):
                    skipone = True
                continue

            line.lt = screenplay.NOTE
            line.text = sl.lstrip('=#')

        if line.text == TWOSPACE:
            pass

        elif line.lt != screenplay.ACTION:
            line.text = line.text.lstrip()

        else:
            tmp = line.text.rstrip()
            # we don't support center align, so simply add required indent.
            if isCentered(tmp):
                tmp = tmp[1:-1].strip()
                width = frame.panel.ctrl.sp.cfg.getType(screenplay.ACTION).width
                if len(tmp) < width:
                    tmp = ' ' * ((width - len(tmp)) // 2) + tmp
            line.text = tmp

        if removeMarkdown:
            line.text = unmarkdown(line.text)
            if line.lt == screenplay.CHARACTER and line.text.endswith('^'):
                line.text = line.text[:-1]

        lns.append(line)

    ret = []

    # second pass helper functions.
    def isLastLBForced():
        return ret and ret[-1].lb == screenplay.LB_FORCED

    def makeLastLBLast():
        if ret:
            ret[-1].lb = screenplay.LB_LAST

    def isRetPrevType(t):
        return ret and ret[-1].lt == t

    # second pass - remove unneeded empty lines, and fix the linebreaks.
    for ln in lns:
        if ln.text == '':
            if isLastLBForced():
                makeLastLBLast()
            else:
                ret.append(ln)

        elif not isRetPrevType(ln.lt):
            makeLastLBLast()
            ret.append(ln)

        else:
            ret.append(ln)

    makeLastLBLast()
    return ret

# import text file from fileName, return list of Line objects for the
# screenplay or None if something went wrong. returned list always
# contains at least one line.
def importTextFile(fileName, frame):

    # the 1 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 1000000)

    if data == None:
        return None

    if len(data) == 0:
        wx.MessageBox("File is empty.", "Error", wx.OK, frame)

        return None

    data = util.fixNL(data)
    lines = data.split("\n")

    tabWidth = 4

    # key = indent level, value = Indent
    indDict = {}

    for i in range(len(lines)):
        s = util.toInputStr(lines[i].rstrip().expandtabs(tabWidth))

        # don't count empty lines towards indentation statistics
        if s.strip() == "":
            lines[i] = ""

            continue

        cnt = util.countInitial(s, " ")

        ind = indDict.get(cnt)
        if not ind:
            ind = Indent(cnt)
            indDict[cnt] = ind

        tmp = s.upper()

        if util.multiFind(tmp, ["EXT.", "INT."]):
            ind.sceneStart += 1

        if util.multiFind(tmp, ["CUT TO:", "DISSOLVE TO:"]):
            ind.trans += 1

        if re.match(r"^ +\(.*\)$", tmp):
            ind.paren += 1

        ind.lines.append(s.lstrip())
        lines[i] = s

    if len(indDict) == 0:
        wx.MessageBox("File contains only empty lines.", "Error", wx.OK, frame)

        return None

    # scene/action indent
    setType(SCENE_ACTION, indDict, lambda v: v.sceneStart)

    # indent with most lines is dialogue in non-pure-action scripts
    setType(screenplay.DIALOGUE, indDict, lambda v: len(v.lines))

    # remaining indent with lines is character most likely
    setType(screenplay.CHARACTER, indDict, lambda v: len(v.lines))

    # transitions
    setType(screenplay.TRANSITION, indDict, lambda v: v.trans)

    # parentheticals
    setType(screenplay.PAREN, indDict, lambda v: v.paren)

    # some text files have this type of parens:
    #
    #        JOE
    #      (smiling and
    #       hopping along)
    #
    # this handles them.
    parenIndent = findIndent(indDict, lambda v: v.lt == screenplay.PAREN)
    if parenIndent != -1:
        paren2Indent = findIndent(indDict,
            lambda v, var: (v.lt == -1) and (v.indent == var),
            parenIndent + 1)

        if paren2Indent != -1:
            indDict[paren2Indent].lt = screenplay.PAREN

    # set line type to ACTION for any indents not recognized
    for v in indDict.itervalues():
        if v.lt == -1:
            v.lt = screenplay.ACTION

    dlg = ImportDlg(frame, indDict.values())

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()

        return None

    dlg.Destroy()

    ret = []

    for i in range(len(lines)):
        s = lines[i]
        cnt = util.countInitial(s, " ")
        s = s.lstrip()
        sUp = s.upper()

        if s:
            lt = indDict[cnt].lt

            if lt == IGNORE:
                continue

            if lt == SCENE_ACTION:
                if s.startswith("EXT.") or s.startswith("INT."):
                    lt = screenplay.SCENE
                else:
                    lt = screenplay.ACTION

            if ret and (ret[-1].lt != lt):
                ret[-1].lb = screenplay.LB_LAST

            if lt == screenplay.CHARACTER:
                if sUp.endswith("(CONT'D)"):
                    s = sUp[:-8].rstrip()

            elif lt == screenplay.PAREN:
                if s == "(continuing)":
                    s = ""

            if s:
                line = screenplay.Line(screenplay.LB_SPACE, lt, s)
                ret.append(line)

        elif ret:
            ret[-1].lb = screenplay.LB_LAST

    if len(ret) == 0:
        ret.append(screenplay.Line(screenplay.LB_LAST, screenplay.ACTION))

    # make sure the last line ends an element
    ret[-1].lb = screenplay.LB_LAST

    return ret

# go through indents, find the one with maximum value in something, and
# set its linetype to given lt.
def setType(lt, indDict, func):
    maxCount = 0
    found = -1

    for v in indDict.itervalues():
        # don't touch indents already set
        if v.lt != -1:
            continue

        val = func(v)

        if val > maxCount:
            maxCount = val
            found = v.indent

    if found != -1:
        indDict[found].lt = lt

# go through indents calling func(it, *vars) on each. return indent count
# for the indent func returns True, or -1 if it returns False for each.
def findIndent(indDict, func, *vars):
    for v in indDict.itervalues():
        if func(v, *vars):
            return v.indent

    return -1

# information about one indent level in imported text files.
class Indent:
    def __init__(self, indent):

        # indent level, i.e. spaces at the beginning
        self.indent = indent

        # lines with this indent, leading spaces removed
        self.lines = []

        # assigned line type, or -1 if not assigned yet.
        self.lt = -1

        # how many of the lines start with "EXT." or "INT."
        self.sceneStart = 0

        # how many of the lines have "CUT TO:" or "DISSOLVE TO:"
        self.trans = 0

        # how many of the lines have a form of "^ +\(.*)$", i.e. are most
        # likely parentheticals
        self.paren = 0


class ImportDlg(wx.Dialog):
    def __init__(self, parent, indents):
        wx.Dialog.__init__(self, parent, -1, "Adjust styles",
                           style = wx.DEFAULT_DIALOG_STYLE)

        indents.sort(lambda i1, i2: -cmp(len(i1.lines), len(i2.lines)))

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Input:")
        vsizer.Add(tmp)

        self.inputLb = wx.ListBox(self, -1, size = (400, 200))
        for it in indents:
            self.inputLb.Append("%d lines (indented %d characters)" %
                                (len(it.lines), it.indent), it)

        vsizer.Add(self.inputLb, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Style:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.styleCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        self.styleCombo.Append("Scene / Action", SCENE_ACTION)
        for t in config.getTIs():
            self.styleCombo.Append(t.name, t.lt)

        self.styleCombo.Append("Ignore", IGNORE)

        util.setWH(self.styleCombo, w = 150)

        hsizer.Add(self.styleCombo, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.TOP | wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "Lines:"))

        self.linesEntry = wx.TextCtrl(self, -1, size = (400, 200),
            style = wx.TE_MULTILINE | wx.TE_DONTWRAP)
        vsizer.Add(self.linesEntry, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_COMBOBOX(self, self.styleCombo.GetId(), self.OnStyleCombo)
        wx.EVT_LISTBOX(self, self.inputLb.GetId(), self.OnInputLb)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        self.inputLb.SetSelection(0)
        self.OnInputLb()

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnInputLb(self, event = None):
        self.selected = self.inputLb.GetClientData(self.inputLb.GetSelection())

        util.reverseComboSelect(self.styleCombo, self.selected.lt)
        self.linesEntry.SetValue("\n".join(self.selected.lines))

    def OnStyleCombo(self, event):
        self.selected.lt = self.styleCombo.GetClientData(
            self.styleCombo.GetSelection())

########NEW FILE########
__FILENAME__ = mypager
import screenplay
import pml

# used to iteratively add PML pages to a document
class Pager:
    def __init__(self, cfg):
        self.doc = pml.Document(cfg.paperWidth, cfg.paperHeight)

        # used in several places, so keep around
        self.charIndent = cfg.getType(screenplay.CHARACTER).indent
        self.sceneIndent = cfg.getType(screenplay.SCENE).indent

        # current scene number
        self.scene = 0

        # number of CONTINUED:'s lines added for current scene
        self.sceneContNr = 0

########NEW FILE########
__FILENAME__ = mypickle
import config
import util

import copy

# keep track about one object's variables
class Vars:
    def __init__(self):
        self.cvars = []

    def __iter__(self):
        for v in self.cvars:
            yield v

    # make various dictionaries pointing to the config variables.
    def makeDicts(self):
        self.all = self.getDict()
        self.color = self.getDict(ColorVar)
        self.numeric = self.getDict(NumericVar)
        self.stringLatin1 = self.getDict(StrLatin1Var)

    # return dictionary containing given type of variable objects, or all
    # if typeObj is None.
    def getDict(self, typeObj = None):
        tmp = {}

        for it in self.cvars:
            if not typeObj or isinstance(it, typeObj):
                tmp[it.name] = it

        return tmp

    # get default value of a setting
    def getDefault(self, name):
        return self.all[name].defVal

    # get minimum value of a numeric setting
    def getMin(self, name):
        return self.numeric[name].minVal

    # get maximum value of a numeric setting
    def getMax(self, name):
        return self.numeric[name].maxVal

    # get minimum and maximum value of a numeric setting as a (min,max)
    # tuple.
    def getMinMax(self, name):
        return (self.getMin(name), self.getMax(name))

    def setDefaults(self, obj):
        for it in self.cvars:
            setattr(obj, it.name, copy.deepcopy(it.defVal))

    # transform string 's' (loaded from file) into a form suitable for
    # load() to take.
    @staticmethod
    def makeVals(s):
        tmp = util.fixNL(s).split("\n")

        vals = {}
        for it in tmp:
            if it.find(":") != -1:
                name, v = it.split(":", 1)
                vals[name] = v

        return vals

    def save(self, prefix, obj):
        s = ""

        for it in self.cvars:
            if it.name2:
                s += it.toStr(getattr(obj, it.name), prefix + it.name2)

        return s

    def load(self, vals, prefix, obj):
        for it in self.cvars:
            if it.name2:
                name = prefix + it.name2
                if vals.has_key(name):
                    res = it.fromStr(vals, vals[name], name)
                    setattr(obj, it.name, res)
                    del vals[name]

    def addVar(self, var):
        self.cvars.append(var)

    def addBool(self, *params):
        self.addVar(BoolVar(*params))

    def addColor(self, name, r, g, b, name2, descr):
        self.addVar(ColorVar(name + "Color", util.MyColor(r, g, b),
                             "Color/" + name2, descr))

    def addFloat(self, *params):
        self.addVar(FloatVar(*params))

    def addInt(self, *params):
        self.addVar(IntVar(*params))

    def addStrLatin1(self, *params):
        self.addVar(StrLatin1Var(*params))

    def addStrUnicode(self, *params):
        self.addVar(StrUnicodeVar(*params))

    def addStrBinary(self, *params):
        self.addVar(StrBinaryVar(*params))

    def addElemName(self, *params):
        self.addVar(ElementNameVar(*params))

    def addList(self, *params):
        self.addVar(ListVar(*params))

class ConfVar:
    # name2 is the name to use while saving/loading the variable. if it's
    # empty, the variable is not loaded/saved, i.e. is used only
    # internally.
    def __init__(self, name, defVal, name2):
        self.name = name
        self.defVal = defVal
        self.name2 = name2

class BoolVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, str(bool(val)))

    def fromStr(self, vals, val, prefix):
        return val == "True"

class ColorVar(ConfVar):
    def __init__(self, name, defVal, name2, descr):
        ConfVar.__init__(self, name, defVal, name2)
        self.descr = descr

    def toStr(self, val, prefix):
        return "%s:%d,%d,%d\n" % (prefix, val.r, val.g, val.b)

    def fromStr(self, vals, val, prefix):
        v = val.split(",")
        if len(v) != 3:
            return copy.deepcopy(self.defVal)

        r = util.str2int(v[0], 0, 0, 255)
        g = util.str2int(v[1], 0, 0, 255)
        b = util.str2int(v[2], 0, 0, 255)

        return util.MyColor(r, g, b)

class NumericVar(ConfVar):
    def __init__(self, name, defVal, name2, minVal, maxVal):
        ConfVar.__init__(self, name, defVal, name2)
        self.minVal = minVal
        self.maxVal = maxVal

class FloatVar(NumericVar):
    def __init__(self, name, defVal, name2, minVal, maxVal, precision = 2):
        NumericVar.__init__(self, name, defVal, name2, minVal, maxVal)
        self.precision = precision

    def toStr(self, val, prefix):
        return "%s:%.*f\n" % (prefix, self.precision, val)

    def fromStr(self, vals, val, prefix):
        return util.str2float(val, self.defVal, self.minVal, self.maxVal)

class IntVar(NumericVar):
    def __init__(self, name, defVal, name2, minVal, maxVal):
        NumericVar.__init__(self, name, defVal, name2, minVal, maxVal)

    def toStr(self, val, prefix):
        return "%s:%d\n" % (prefix, val)

    def fromStr(self, vals, val, prefix):
        return util.str2int(val, self.defVal, self.minVal, self.maxVal)

# ISO-8859-1 (Latin 1) string.
class StrLatin1Var(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, util.toUTF8(val))

    def fromStr(self, vals, val, prefix):
        return util.fromUTF8(val)

# Unicode string.
class StrUnicodeVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, val.encode("UTF-8"))

    def fromStr(self, vals, val, prefix):
        return val.decode("UTF-8", "ignore")

# binary string, can contain anything. characters outside of printable
# ASCII (and \ itself) are encoded as \XX, where XX is the hex code of the
# character.
class StrBinaryVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, util.encodeStr(val))

    def fromStr(self, vals, val, prefix):
        return util.decodeStr(val)

# screenplay.ACTION <-> "Action"
class ElementNameVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, config.lt2ti(val).name)

    def fromStr(self, vals, val, prefix):
        ti = config.name2ti(val)

        if ti:
            return ti.lt
        else:
            return self.defVal

class ListVar(ConfVar):
    def __init__(self, name, defVal, name2, itemType):
        ConfVar.__init__(self, name, defVal, name2)

        # itemType is an instance of one of the *Var classes, and is the
        # type of item contained in the list.
        self.itemType = itemType

    def toStr(self, val, prefix):
        s = ""

        s += "%s:%d\n" % (prefix, len(val))

        i = 1
        for v in val:
            s += self.itemType.toStr(v, prefix + "/%d" % i)
            i += 1

        return s

    def fromStr(self, vals, val, prefix):
        # 1000 is totally arbitrary, increase if needed
        count = util.str2int(val, -1, -1, 1000)
        if count == -1:
            return copy.deepcopy(self.defVal)

        tmp = []
        for i in range(1, count + 1):
            name = prefix + "/%d" % i

            if vals.has_key(name):
                res = self.itemType.fromStr(vals, vals[name], name)
                tmp.append(res)
                del vals[name]

        return tmp

########NEW FILE########
__FILENAME__ = namearray
import array
import collections

class NameArray:
    def __init__(self):
        self.maxCount = 205000
        self.count = 0

        self.name = [None] * self.maxCount
        self.type = array.array('B')
        self.type.fromstring(chr(0) * self.maxCount)

        # 0 = female, 1 = male
        self.sex = array.array('B')
        self.sex.fromstring(chr(0) * self.maxCount)

        # key = type name, value = count of names for that type
        self.typeNamesCnt = collections.defaultdict(int)

        # key = type name, value = integer id for that type
        self.typeId = {}

        # type names indexed by their integer id
        self.typeNamesById = []

    def append(self, name, type, sex):
        if self.count >= self.maxCount:
            for i in range(1000):
                self.name.append(None)
                self.type.append(0)
                self.sex.append(0)

            self.maxCount += 1000

        typeId = self.addType(type)

        self.name[self.count] = name
        self.type[self.count] = typeId
        self.sex[self.count] = 0 if sex == "F" else 1

        self.count += 1

    def addType(self, type):
        self.typeNamesCnt[type] += 1

        typeId = self.typeId.get(type)

        if typeId is None:
            typeId = len(self.typeNamesById)
            self.typeId[type] = typeId
            self.typeNamesById.append(type)

        return typeId

########NEW FILE########
__FILENAME__ = namesdlg
import misc
import namearray
import util

import wx

# NameArray, or None if not loaded
nameArr = None

# if not already loaded, read the name database from disk and store it.
# returns False on errors.
def readNames(frame):
    global nameArr

    if nameArr:
        # already loaded
        return True

    try:
        data = util.loadMaybeCompressedFile(u"names.txt", frame)
        if not data:
            return False

        res = namearray.NameArray()
        nameType = None

        for line in data.splitlines():
            ch = line[0]
            if ch == "#":
                continue
            elif ch == "N":
                nameType = line[1:]
            elif ch in ("M", "F"):
                if not nameType:
                    raise Exception("No name type set before line: '%s'" % line)
                res.append(line[1:], nameType, ch)
            else:
                raise Exception("Unknown linetype for line: '%s'" % line)

        nameArr = res

        return True

    except Exception, e:
        wx.MessageBox("Error loading name database: %s" % str(e),
                      "Error", wx.OK, frame)


        return False

class NamesDlg(wx.Dialog):
    def __init__(self, parent, ctrl):
        wx.Dialog.__init__(self, parent, -1, "Character name database",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.ctrl = ctrl

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Search in:"))

        self.typeList = wx.ListCtrl(self, -1,
            style = wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)

        self.typeList.InsertColumn(0, "Count")
        self.typeList.InsertColumn(1, "Type")

        for i in range(len(nameArr.typeNamesById)):
            typeName = nameArr.typeNamesById[i]

            self.typeList.InsertStringItem(i, str(nameArr.typeNamesCnt[typeName]))
            self.typeList.SetStringItem(i, 1, typeName)
            self.typeList.SetItemData(i, i)

        self.typeList.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.typeList.SetColumnWidth(1, wx.LIST_AUTOSIZE)

        w = 0
        w += self.typeList.GetColumnWidth(0)
        w += self.typeList.GetColumnWidth(1)

        util.setWH(self.typeList, w + 15, 425)

        self.typeList.SortItems(self.CmpFreq)
        self.selectAllTypes()
        vsizer.Add(self.typeList, 1, wx.EXPAND | wx.BOTTOM, 5)

        selectAllBtn = wx.Button(self, -1, "Select all")
        vsizer.Add(selectAllBtn)

        hsizer.Add(vsizer, 0, wx.EXPAND)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        searchBtn = wx.Button(self, -1, "Search")
        wx.EVT_BUTTON(self, searchBtn.GetId(), self.OnSearch)
        vsizer2.Add(searchBtn, 0, wx.BOTTOM | wx.TOP, 10)

        self.searchEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        vsizer2.Add(self.searchEntry, 0, wx.EXPAND)

        tmp = wx.Button(self, -1, "Insert")
        wx.EVT_BUTTON(self, tmp.GetId(), self.OnInsertName)
        vsizer2.Add(tmp, 0, wx.BOTTOM | wx.TOP, 10)

        hsizer2.Add(vsizer2, 1, wx.RIGHT, 10)

        self.nameRb = wx.RadioBox(self, -1, "Name",
            style = wx.RA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "begins with", "contains", "ends in" ])
        hsizer2.Add(self.nameRb)

        self.sexRb = wx.RadioBox(self, -1, "Sex",
            style = wx.RA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "Male", "Female", "Both" ])
        self.sexRb.SetSelection(2)
        hsizer2.Add(self.sexRb, 0, wx.LEFT, 5)

        vsizer.Add(hsizer2, 0, wx.EXPAND | wx.ALIGN_CENTER)

        vsizer.Add(wx.StaticText(self, -1, "Results:"))

        self.list = MyListCtrl(self)
        vsizer.Add(self.list, 1, wx.EXPAND | wx.BOTTOM, 5)

        self.foundLabel = wx.StaticText(self, -1, "",
            style = wx.ALIGN_CENTRE | wx.ST_NO_AUTORESIZE)
        vsizer.Add(self.foundLabel, 0, wx.EXPAND)

        hsizer.Add(vsizer, 20, wx.EXPAND | wx.LEFT, 10)

        wx.EVT_TEXT_ENTER(self, self.searchEntry.GetId(), self.OnSearch)
        wx.EVT_BUTTON(self, selectAllBtn.GetId(), self.selectAllTypes)
        wx.EVT_LIST_COL_CLICK(self, self.typeList.GetId(), self.OnHeaderClick)

        util.finishWindow(self, hsizer)

        self.OnSearch()
        self.searchEntry.SetFocus()

    def selectAllTypes(self, event = None):
        for i in range(len(nameArr.typeNamesById)):
            self.typeList.SetItemState(i, wx.LIST_STATE_SELECTED,
                                       wx.LIST_STATE_SELECTED)

    def OnHeaderClick(self, event):
        if event.GetColumn() == 0:
            self.typeList.SortItems(self.CmpFreq)
        else:
            self.typeList.SortItems(self.CmpType)

    def CmpFreq(self, i1, i2):
        return nameArr.typeNamesCnt[nameArr.typeNamesById[i2]] - nameArr.typeNamesCnt[nameArr.typeNamesById[i1]]

    def CmpType(self, i1, i2):
        return cmp(nameArr.typeNamesById[i1], nameArr.typeNamesById[i2])

    def OnInsertName(self, event):
        item = self.list.GetNextItem(-1, wx.LIST_NEXT_ALL,
                                     wx.LIST_STATE_SELECTED)

        if item == -1:
            return

        # this seems to return column 0's text, which is lucky, because I
        # don't see a way of getting other columns' texts...
        name = self.list.GetItemText(item)

        for ch in name:
            self.ctrl.OnKeyChar(util.MyKeyEvent(ord(ch)))

    def OnSearch(self, event = None):
        l = []

        wx.BeginBusyCursor()

        s = util.lower(misc.fromGUI(self.searchEntry.GetValue()))
        sex = self.sexRb.GetSelection()
        nt = self.nameRb.GetSelection()

        selTypes = {}
        item = -1

        while 1:
            item = self.typeList.GetNextItem(item, wx.LIST_NEXT_ALL,
                wx.LIST_STATE_SELECTED)

            if item == -1:
                break

            selTypes[self.typeList.GetItemData(item)] = True

        if len(selTypes) == len(nameArr.typeNamesCnt):
            doTypes = False
        else:
            doTypes = True

        for i in xrange(nameArr.count):
            if (sex != 2) and (sex == nameArr.sex[i]):
                continue

            if doTypes and nameArr.type[i] not in selTypes:
                continue

            if s:
                name = util.lower(nameArr.name[i])

                if nt == 0:
                    if not name.startswith(s):
                        continue
                elif nt == 1:
                    if name.find(s) == -1:
                        continue
                elif nt == 2:
                    if not name.endswith(s):
                        continue

            l.append(i)

        self.list.items = l
        self.list.SetItemCount(len(l))
        self.list.EnsureVisible(0)

        wx.EndBusyCursor()

        self.foundLabel.SetLabel("%d names found." % len(l))

class MyListCtrl(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1,
            style = wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL |
                    wx.LC_HRULES | wx.LC_VRULES)

        self.sex = ["Female", "Male"]

        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Type")
        self.InsertColumn(2, "Sex")
        self.SetColumnWidth(0, 120)
        self.SetColumnWidth(1, 120)

        # we can't use wx.LIST_AUTOSIZE since this is a virtual control,
        # so calculate the size ourselves since we know the longest string
        # possible.
        w = util.getTextExtent(self.GetFont(), "Female")[0] + 15
        self.SetColumnWidth(2, w)

        util.setWH(self, w = 120*2 + w + 25)

    def OnGetItemText(self, item, col):
        n = self.items[item]

        if col == 0:
            return nameArr.name[n]
        elif col == 1:
            return nameArr.typeNamesById[nameArr.type[n]]
        elif col == 2:
            return self.sex[nameArr.sex[n]]

        # shouldn't happen
        return ""

    # for some reason this must be overridden as well, otherwise we get
    # assert failures under windows.
    def OnGetItemImage(self, item):
        return -1

########NEW FILE########
__FILENAME__ = opts
import sys

# TODO: Python, at least up to 2.4, does not support Unicode command line
# arguments on Windows. Since UNIXes use UTF-8, just assume all command
# line arguments are UTF-8 for now, and silently ignore any coding errors
# that may result on Windows in some cases.
def init():
    global isTest, conf, filenames

    # script filenames to load
    filenames = []

    # name of config file to use, or None
    conf = None

    # are we in test mode
    isTest = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == "--test":
            isTest = True
        elif arg == "--conf":
            if (i + 1) < len(sys.argv):
                conf = unicode(sys.argv[i + 1], "UTF-8", "ignore")
                i += 1
        else:
            filenames.append(unicode(arg, "UTF-8", "ignore"))

        i += 1

########NEW FILE########
__FILENAME__ = pdf
import fontinfo
import pml
import util

# PDF transform matrixes where key is the angle from x-axis
# in counter-clockwise direction.
TRANSFORM_MATRIX = {
    45 : (1, 1, -1, 1),
    90 : (0, 1, -1, 0),
}

# users should only use this.
def generate(doc):
    tmp = PDFExporter(doc)
    return tmp.generate()

# An abstract base class for all PDF drawing operations.
class PDFDrawOp:

    # write PDF drawing operations corresponding to the PML object pmlOp
    # to output (util.String). pe = PDFExporter.
    def draw(self, pmlOp, pageNr, output, pe):
        raise Exception("draw not implemented")

class PDFTextOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        if pmlOp.toc:
            pmlOp.toc.pageObjNr = pe.pageObjs[pageNr].nr

        # we need to adjust y position since PDF uses baseline of text as
        # the y pos, but pml uses top of the text as y pos. The Adobe
        # standard Courier family font metrics give 157 units in 1/1000
        # point units as the Descender value, thus giving (1000 - 157) =
        # 843 units from baseline to top of text.

        # http://partners.adobe.com/asn/tech/type/ftechnotes.jsp contains
        # the "Font Metrics for PDF Core 14 Fonts" document.

        x = pe.x(pmlOp.x)
        y = pe.y(pmlOp.y) - 0.843 * pmlOp.size

        newFont = "F%d %d" % (pe.getFontNr(pmlOp.flags), pmlOp.size)
        if newFont != pe.currentFont:
            output += "/%s Tf\n" % newFont
            pe.currentFont = newFont

        if pmlOp.angle is not None:
            matrix = TRANSFORM_MATRIX.get(pmlOp.angle)

            if matrix:
                output += "BT\n"\
                    "%f %f %f %f %f %f Tm\n"\
                    "(%s) Tj\n"\
                    "ET\n" % (matrix[0], matrix[1], matrix[2], matrix[3],
                              x, y, pe.escapeStr(pmlOp.text))
            else:
                # unsupported angle, don't print it.
                pass
        else:
            output += "BT\n"\
                "%f %f Td\n"\
                "(%s) Tj\n"\
                "ET\n" % (x, y, pe.escapeStr(pmlOp.text))

        if pmlOp.flags & pml.UNDERLINED:

            undLen = fontinfo.getMetrics(pmlOp.flags).getTextWidth(
                pmlOp.text, pmlOp.size)

            # all standard PDF fonts have the underline line 100 units
            # below baseline with a thickness of 50
            undY = y - 0.1 * pmlOp.size

            output += "%f w\n"\
                      "%f %f m\n"\
                      "%f %f l\n"\
                      "S\n" % (0.05 * pmlOp.size, x, undY, x + undLen, undY)

class PDFLineOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        p = pmlOp.points

        pc = len(p)

        if pc < 2:
            print "LineOp contains only %d points" % pc

            return

        output += "%f w\n"\
                  "%s m\n" % (pe.mm2points(pmlOp.width), pe.xy(p[0]))

        for i in range(1, pc):
            output += "%s l\n" % (pe.xy(p[i]))

        if pmlOp.isClosed:
            output += "s\n"
        else:
            output += "S\n"

class PDFRectOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        if pmlOp.lw != -1:
            output += "%f w\n" % pe.mm2points(pmlOp.lw)

        output += "%f %f %f %f re\n" % (
            pe.x(pmlOp.x),
            pe.y(pmlOp.y) - pe.mm2points(pmlOp.height),
            pe.mm2points(pmlOp.width), pe.mm2points(pmlOp.height))

        if pmlOp.fillType == pml.NO_FILL:
            output += "S\n"
        elif pmlOp.fillType == pml.FILL:
            output += "f\n"
        elif pmlOp.fillType == pml.STROKE_FILL:
            output += "B\n"
        else:
            print "Invalid fill type for RectOp"

class PDFQuarterCircleOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        sX = pmlOp.flipX and -1 or 1
        sY = pmlOp.flipY and -1 or 1

        # the literature on how to emulate quarter circles with Bezier
        # curves is sketchy, but the one thing that is clear is that the
        # two control points have to be on (1, A) and (A, 1) (on a unit
        # circle), and empirically choosing A to be half of the radius
        # results in the best looking quarter circle.
        A = pmlOp.radius * 0.5

        output += "%f w\n"\
                  "%s m\n" % (pe.mm2points(pmlOp.width),
                              pe.xy((pmlOp.x - pmlOp.radius * sX, pmlOp.y)))

        output += "%f %f %f %f %f %f c\n" % (
            pe.x(pmlOp.x - pmlOp.radius * sX), pe.y(pmlOp.y - A * sY),
            pe.x(pmlOp.x - A * sX), pe.y(pmlOp.y - pmlOp.radius * sY),
            pe.x(pmlOp.x), pe.y(pmlOp.y - pmlOp.radius * sY))

        output += "S\n"

class PDFArbitraryOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        output += "%s\n" % pmlOp.cmds

# used for keeping track of used fonts
class FontInfo:
    def __init__(self, name):
        self.name = name

        # font number (the name in the /F PDF command), or -1 if not used
        self.number = -1

        # PDFObject that contains the /Font object for this font, or None
        self.pdfObj = None

# one object in a PDF file
class PDFObject:
    def __init__(self, nr, data = ""):
        # PDF object number
        self.nr = nr

        # all data between 'obj/endobj' tags, excluding newlines
        self.data = data

        # start position of object, stored in the xref table. initialized
        # when the object is written out (by the caller of write).
        self.xrefPos = -1

    # write object to output (util.String).
    def write(self, output):
        output += "%d 0 obj\n" % self.nr
        output += self.data
        output += "\nendobj\n"

class PDFExporter:
    # see genWidths
    _widthsStr = None

    def __init__(self, doc):
        # pml.Document
        self.doc = doc

    # generate PDF document and return it as a string
    def generate(self):
        #lsdjflksj = util.TimerDev("generate")
        doc = self.doc

        # fast lookup of font information
        self.fonts = {
            pml.COURIER : FontInfo("Courier"),
            pml.COURIER | pml.BOLD: FontInfo("Courier-Bold"),
            pml.COURIER | pml.ITALIC: FontInfo("Courier-Oblique"),
            pml.COURIER | pml.BOLD | pml.ITALIC:
              FontInfo("Courier-BoldOblique"),

            pml.HELVETICA : FontInfo("Helvetica"),
            pml.HELVETICA | pml.BOLD: FontInfo("Helvetica-Bold"),
            pml.HELVETICA | pml.ITALIC: FontInfo("Helvetica-Oblique"),
            pml.HELVETICA | pml.BOLD | pml.ITALIC:
              FontInfo("Helvetica-BoldOblique"),

            pml.TIMES_ROMAN : FontInfo("Times-Roman"),
            pml.TIMES_ROMAN | pml.BOLD: FontInfo("Times-Bold"),
            pml.TIMES_ROMAN | pml.ITALIC: FontInfo("Times-Italic"),
            pml.TIMES_ROMAN | pml.BOLD | pml.ITALIC:
              FontInfo("Times-BoldItalic"),
            }

        # list of PDFObjects
        self.objects = []

        # number of fonts used
        self.fontCnt = 0

        # PDF object count. it starts at 1 because the 'f' thingy in the
        # xref table is an object of some kind or something...
        self.objectCnt = 1

        pages = len(doc.pages)

        self.catalogObj = self.addObj()
        self.infoObj = self.createInfoObj()
        pagesObj = self.addObj()

        # we only create this when needed, in genWidths
        self.widthsObj = None

        if doc.tocs:
            self.outlinesObj = self.addObj()

            # each outline is a single PDF object
            self.outLineObjs = []

            for i in xrange(len(doc.tocs)):
                self.outLineObjs.append(self.addObj())

            self.outlinesObj.data = ("<< /Type /Outlines\n"
                                     "/Count %d\n"
                                     "/First %d 0 R\n"
                                     "/Last %d 0 R\n"
                                     ">>" % (len(doc.tocs),
                                             self.outLineObjs[0].nr,
                                             self.outLineObjs[-1].nr))

            outlinesStr = "/Outlines %d 0 R\n" % self.outlinesObj.nr

            if doc.showTOC:
                outlinesStr += "/PageMode /UseOutlines\n"

        else:
            outlinesStr = ""

        # each page has two PDF objects: 1) a /Page object that links to
        # 2) a stream object that has the actual page contents.
        self.pageObjs = []
        self.pageContentObjs = []

        for i in xrange(pages):
            self.pageObjs.append(self.addObj("<< /Type /Page\n"
                                             "/Parent %d 0 R\n"
                                             "/Contents %d 0 R\n"
                                             ">>" % (pagesObj.nr,
                                                     self.objectCnt + 1)))
            self.pageContentObjs.append(self.addObj())

        if doc.defPage != -1:
            outlinesStr += "/OpenAction [%d 0 R /XYZ null null 0]\n" % (
                self.pageObjs[0].nr + doc.defPage * 2)

        self.catalogObj.data = ("<< /Type /Catalog\n"
                                "/Pages %d 0 R\n"
                                "%s"
                                ">>" % (pagesObj.nr, outlinesStr))

        for i in xrange(pages):
            self.genPage(i)

        kids = util.String()
        kids += "["
        for obj in self.pageObjs:
            kids += "%d 0 R\n" % obj.nr
        kids += "]"

        fontStr = ""
        for fi in self.fonts.itervalues():
            if fi.number != -1:
                fontStr += "/F%d %d 0 R " % (fi.number, fi.pdfObj.nr)

        pagesObj.data = ("<< /Type /Pages\n"
                         "/Kids %s\n"
                         "/Count %d\n"
                         "/MediaBox [0 0 %f %f]\n"
                         "/Resources << /Font <<\n"
                         "%s >> >>\n"
                         ">>" % (str(kids), pages, self.mm2points(doc.w),
                                 self.mm2points(doc.h), fontStr))

        if doc.tocs:
            for i in xrange(len(doc.tocs)):
                self.genOutline(i)

        return self.genPDF()

    def createInfoObj(self):
        version = self.escapeStr(self.doc.version)

        if self.doc.uniqueId:
            extra = "/Keywords (%s)\n" % self.doc.uniqueId
        else:
            extra = ""

        return self.addObj("<< /Creator (Trelby %s)\n"
                           "/Producer (Trelby %s)\n"
                           "%s"
                           ">>" % (version, version, extra))

    # create a PDF object containing a 256-entry array for the widths of a
    # font, with all widths being 600
    def genWidths(self):
        if self.widthsObj:
            return

        if not self.__class__._widthsStr:
            self.__class__._widthsStr = "[%s]" % ("600 " * 256).rstrip()

        self.widthsObj = self.addObj(self.__class__._widthsStr)

    # generate a single page
    def genPage(self, pageNr):
        pg = self.doc.pages[pageNr]

        # content stream
        cont = util.String()

        self.currentFont = ""

        for op in pg.ops:
            op.pdfOp.draw(op, pageNr, cont, self)

        self.pageContentObjs[pageNr].data = self.genStream(str(cont))

    # generate outline number 'i'
    def genOutline(self, i):
        toc = self.doc.tocs[i]
        obj = self.outLineObjs[i]

        if i != (len(self.doc.tocs) - 1):
            nextStr = "/Next %d 0 R\n" % (obj.nr + 1)
        else:
            nextStr = ""

        if i != 0:
            prevStr = "/Prev %d 0 R\n" % (obj.nr - 1)
        else:
            prevStr = ""

        obj.data = ("<< /Parent %d 0 R\n"
                    "/Dest [%d 0 R /XYZ %f %f 0]\n"
                    "/Title (%s)\n"
                    "%s"
                    "%s"
                    ">>" % (
            self.outlinesObj.nr, toc.pageObjNr, self.x(toc.op.x),
            self.y(toc.op.y), self.escapeStr(toc.text),
            prevStr, nextStr))

    # generate a stream object's contents. 's' is all data between
    # 'stream/endstream' tags, excluding newlines.
    def genStream(self, s, isFontStream = False):
        compress = True

        # embedded TrueType font program streams for some reason need a
        # Length1 entry that records the uncompressed length of the stream
        if isFontStream:
            lenStr = "/Length1 %d\n" % len(s)
        else:
            lenStr = ""

        filterStr = " "
        if compress:
            s = s.encode("zlib")
            filterStr = "/Filter /FlateDecode\n"

        return ("<< /Length %d\n%s%s>>\n"
                "stream\n"
                "%s\n"
                "endstream" % (len(s), lenStr, filterStr, s))

    # add a new object and return it. 'data' is all data between
    # 'obj/endobj' tags, excluding newlines.
    def addObj(self, data = ""):
        obj = PDFObject(self.objectCnt, data)
        self.objects.append(obj)
        self.objectCnt += 1

        return obj

    # write out object to 'output' (util.String)
    def writeObj(self, output, obj):
        obj.xrefPos = len(output)
        obj.write(output)

    # write a xref table entry to 'output' (util.String), using position
    # 'pos, generation 'gen' and type 'typ'.
    def writeXref(self, output, pos, gen = 0, typ = "n"):
        output += "%010d %05d %s \n" % (pos, gen, typ)

    # generate PDF file and return it as a string
    def genPDF(self):
        data = util.String()

        data += "%PDF-1.5\n"

        for obj in self.objects:
            self.writeObj(data, obj)

        xrefStartPos = len(data)

        data += "xref\n0 %d\n" % self.objectCnt
        self.writeXref(data, 0, 65535, "f")

        for obj in self.objects:
            self.writeXref(data, obj.xrefPos)

        data += "\n"

        data += ("trailer\n"
                 "<< /Size %d\n"
                 "/Root %d 0 R\n"
                 "/Info %d 0 R\n>>\n" % (
            self.objectCnt, self.catalogObj.nr, self.infoObj.nr))

        data += "startxref\n%d\n%%%%EOF\n" % xrefStartPos

        return str(data)

    # get font number to use for given flags. also creates the PDF object
    # for the font if it does not yet exist.
    def getFontNr(self, flags):
        # the "& 15" gets rid of the underline flag
        fi = self.fonts.get(flags & 15)

        if not fi:
            print "PDF.getfontNr: invalid flags %d" % flags

            return 0

        if fi.number == -1:
            fi.number = self.fontCnt
            self.fontCnt += 1

            # the "& 15" gets rid of the underline flag
            pfi = self.doc.fonts.get(flags & 15)

            if not pfi:
                fi.pdfObj = self.addObj("<< /Type /Font\n"
                                        "/Subtype /Type1\n"
                                        "/BaseFont /%s\n"
                                        "/Encoding /WinAnsiEncoding\n"
                                        ">>" % fi.name)
            else:
                self.genWidths()

                fi.pdfObj = self.addObj("<< /Type /Font\n"
                                        "/Subtype /TrueType\n"
                                        "/BaseFont /%s\n"
                                        "/Encoding /WinAnsiEncoding\n"
                                        "/FirstChar 0\n"
                                        "/LastChar 255\n"
                                        "/Widths %d 0 R\n"
                                        "/FontDescriptor %d 0 R\n"
                                        ">>" % (pfi.name, self.widthsObj.nr,
                                                self.objectCnt + 1))

                fm = fontinfo.getMetrics(flags)

                if pfi.fontProgram:
                    fpStr = "/FontFile2 %d 0 R\n" % (self.objectCnt + 1)
                else:
                    fpStr = ""

                # we use a %s format specifier for the italic angle since
                # it sometimes contains integers, sometimes floating point
                # values.
                self.addObj("<< /Type /FontDescriptor\n"
                            "/FontName /%s\n"
                            "/FontWeight %d\n"
                            "/Flags %d\n"
                            "/FontBBox [%d %d %d %d]\n"
                            "/ItalicAngle %s\n"
                            "/Ascent %s\n"
                            "/Descent %s\n"
                            "/CapHeight %s\n"
                            "/StemV %s\n"
                            "/StemH %s\n"
                            "/XHeight %d\n"
                            "%s"
                            ">>" % (pfi.name,
                                    fm.fontWeight,
                                    fm.flags,
                                    fm.bbox[0], fm.bbox[1],
                                    fm.bbox[2], fm.bbox[3],
                                    fm.italicAngle,
                                    fm.ascent,
                                    fm.descent,
                                    fm.capHeight,
                                    fm.stemV,
                                    fm.stemH,
                                    fm.xHeight,
                                    fpStr))

                if pfi.fontProgram:
                    self.addObj(self.genStream(pfi.fontProgram, True))

        return fi.number

    # escape string
    def escapeStr(self, s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # convert mm to points (1/72 inch).
    def mm2points(self, mm):
        # 2.834 = 72 / 25.4
        return mm * 2.83464567

    # convert x coordinate
    def x(self, x):
        return self.mm2points(x)

    # convert y coordinate
    def y(self, y):
        return self.mm2points(self.doc.h - y)

    # convert xy, which is (x, y) pair, into PDF coordinates, and format
    # it as "%f %f", and return that.
    def xy(self, xy):
        x = self.x(xy[0])
        y = self.y(xy[1])

        return "%f %f" % (x, y)

########NEW FILE########
__FILENAME__ = pml
# PML is short for Page Modeling Language, our own neat little PDF-wannabe
# format for expressing a script's complete contents in a neutral way
# that's easy to render to almost anything, e.g. PDF, Postscript, Windows
# GDI, etc.
#

# A PML document is a collection of pages plus possibly some metadata.
# Each page is a collection of simple drawing commands, executed
# sequentially in the order given, assuming "complete overdraw" semantics
# on the output device, i.e. whatever is drawn completely covers things it
# is painted on top of.

# All measurements in PML are in (floating point) millimeters.

import misc
import pdf
import util

import textwrap

# text flags. don't change these unless you know what you're doing.
NORMAL = 0
BOLD   = 1
ITALIC = 2
COURIER = 0
TIMES_ROMAN = 4
HELVETICA = 8
UNDERLINED = 16

# fill types
NO_FILL = 0
FILL = 1
STROKE_FILL = 2

# A single document.
class Document:

    # (w, h) is the size of each page.
    def __init__(self, w, h):
        self.w = w
        self.h = h

        # a collection of Page objects
        self.pages = []

        # a collection of TOCItem objects
        self.tocs = []

        # user-specified fonts, if any. key = 2 lowest bits of
        # TextOp.flags, value = pml.PDFFontInfo
        self.fonts = {}

        # whether to show TOC by default on document open
        self.showTOC = False

        # page number to display on document open, or -1
        self.defPage = -1

        # when running testcases, misc.version does not exist, so store a
        # dummy value in that case, correct value otherwise.
        self.version = getattr(misc, "version", "dummy_version")

        # a random string to embed in the PDF; only used by watermarked
        # PDFs
        self.uniqueId = None

    def add(self, page):
        self.pages.append(page)

    def addTOC(self, toc):
        self.tocs.append(toc)

    def addFont(self, style, pfi):
        self.fonts[style] = pfi

class Page:
    def __init__(self, doc):

        # link to containing document
        self.doc = doc

        # a collection of Operation objects
        self.ops = []

    def add(self, op):
        self.ops.append(op)

    def addOpsToFront(self, opsList):
        self.ops = opsList + self.ops

# Table of content item (Outline item, in PDF lingo)
class TOCItem:
    def __init__(self, text, op):
        # text to show in TOC
        self.text = text

        # pointer to the TextOp that this item links to (used to get the
        # correct positioning information)
        self.op = op

        # the PDF object number of the page we point to
        self.pageObjNr = -1

# information about one PDF font
class PDFFontInfo:
    def __init__(self, name, fontProgram):
        # name to use in generated PDF file ("CourierNew", "MyFontBold",
        # etc.). if empty, use the default PDF font.
        self.name = name

        # the font program (in practise, the contents of the .ttf file for
        # the font), or None, in which case the font is not embedded.
        self.fontProgram = fontProgram

# An abstract base class for all drawing operations.
class DrawOp:
    pass

# Draw text string 'text', at position (x, y) mm from the upper left
# corner of the page. Font used is 'size' points, and Courier / Times/
# Helvetica as indicated by the flags, possibly being bold / italic /
# underlined. angle is None, or an integer from 0 to 360 that gives the
# slant of the text counter-clockwise from x-axis.
class TextOp(DrawOp):
    pdfOp = pdf.PDFTextOp()

    def __init__(self, text, x, y, size, flags = NORMAL | COURIER,
                 align = util.ALIGN_LEFT, valign = util.VALIGN_TOP,
                 line = -1, angle = None):
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.flags = flags
        self.angle = angle

        # TOCItem, by default we have none
        self.toc = None

        # index of line in Screenplay.lines, or -1 if some other text.
        # only used when drawing display, pdf output doesn't use this.
        self.line = line

        if align != util.ALIGN_LEFT:
            w = util.getTextWidth(text, flags, size)

            if align == util.ALIGN_CENTER:
                self.x -= w / 2.0
            elif align == util.ALIGN_RIGHT:
                self.x -= w

        if valign != util.VALIGN_TOP:
            h = util.getTextHeight(size)

            if valign == util.VALIGN_CENTER:
                self.y -= h / 2.0
            elif valign == util.VALIGN_BOTTOM:
                self.y -= h

# Draw consecutive lines. 'points' is a list of (x, y) pairs (minimum 2
# pairs) and 'width' is the line width, with 0 being the thinnest possible
# line. if 'isClosed' is True, the last point on the list is connected to
# the first one.
class LineOp(DrawOp):
    pdfOp = pdf.PDFLineOp()

    def __init__(self, points, width, isClosed = False):
        self.points = points
        self.width = width
        self.isClosed = isClosed

# helper function for creating simple lines
def genLine(x, y, xd, yd, width):
    return LineOp([(x, y), (x + xd, y + yd)], width)

# Draw a rectangle, possibly filled, with specified lineWidth (which can
# be -1 if fillType is FILL). (x, y) is position of upper left corner.
class RectOp(DrawOp):
    pdfOp = pdf.PDFRectOp()

    def __init__(self, x, y, width, height, fillType = FILL, lineWidth = -1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.fillType = fillType
        self.lw = lineWidth

# Draw a quarter circle centered at (x, y) with given radius and line
# width. By default it will be the upper left quadrant of a circle, but
# using the flip[XY] parameters you can choose other quadrants.
class QuarterCircleOp(DrawOp):
    pdfOp = pdf.PDFQuarterCircleOp()

    def __init__(self, x, y, radius, width, flipX = False, flipY = False):
        self.x = x
        self.y = y
        self.radius = radius
        self.width = width
        self.flipX = flipX
        self.flipY = flipY

# Arbitrary PDF commands. Should not have whitespace in the beginning or
# the end. Should be used only for non-critical things like tweaking line
# join styles etc, because non-PDF renderers will ignore these.
class PDFOp(DrawOp):
    pdfOp = pdf.PDFArbitraryOp()

    def __init__(self, cmds):
        self.cmds = cmds

# create a PML document containing text (possibly linewrapped) divided
# into pages automatically.
class TextFormatter:
    def __init__(self, width, height, margin, fontSize):
        self.doc = Document(width, height)

        # how much to leave empty on each side (mm)
        self.margin = margin

        # font size
        self.fontSize = fontSize

        # number of chararacters that fit on a single line
        self.charsToLine = int((width - margin * 2.0) /
                               util.getTextWidth(" ", COURIER, fontSize))

        self.createPage()

    # add new empty page, select it as current, reset y pos
    def createPage(self):
        self.pg = Page(self.doc)

        self.doc.add(self.pg)
        self.y = self.margin

    # add blank vertical space, unless we're at the top of the page
    def addSpace(self, mm):
        if self.y > self.margin:
            self.y += mm

    # add text
    def addText(self, text, x = None, fs = None, style = NORMAL):
        if x == None:
            x = self.margin

        if fs == None:
            fs = self.fontSize

        yd = util.getTextHeight(fs)

        if (self.y + yd) > (self.doc.h - self.margin):
            self.createPage()

        self.pg.add(TextOp(text, x, self.y, fs, style))

        self.y += yd

    # wrap text into lines that fit on the page, using Courier and default
    # font size and style, and add the lines. 'indent' is the text to
    # prefix lines other than the first one with.
    def addWrappedText(self, text, indent):
        tmp = textwrap.wrap(text, self.charsToLine,
                subsequent_indent = indent)

        for s in tmp:
            self.addText(s)

########NEW FILE########
__FILENAME__ = scenereport
import gutil
import misc
import pdf
import pml
import screenplay
import util

import wx

def genSceneReport(mainFrame, sp):
    report = SceneReport(sp)

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False)

    ok = False
    if dlg.ShowModal() == wx.ID_OK:
        ok = True

    dlg.Destroy()

    if not ok:
        return

    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

class SceneReport:
    def __init__(self, sp):
        self.sp = sp

        # list of SceneInfos
        self.scenes = []

        line = 0
        while 1:
            if line >= len(sp.lines):
                break

            startLine, endLine = sp.getSceneIndexesFromLine(line)

            si = SceneInfo(sp)
            si.read(sp, startLine, endLine)
            self.scenes.append(si)

            line = endLine + 1

        # we don't use these, but ScriptReport does
        lineSeq = [si.lines for si in self.scenes]
        self.longestScene = max(lineSeq)
        self.avgScene = sum(lineSeq) / float(len(self.scenes))

        # information about what to include (and yes, the comma is needed
        # to unpack the list)
        self.INF_SPEAKERS, = range(1)
        self.inf = []
        for s in ["Speakers"]:
            self.inf.append(misc.CheckBoxItem(s))

    def generate(self):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 15.0, 12)

        for si in self.scenes:
            tf.addSpace(5.0)

            tf.addText("%-4s %s" % (si.number, si.name), style = pml.BOLD)

            tf.addSpace(1.0)

            tf.addText("     Lines: %d (%s%% action), Pages: %d"
                " (%s)" % (si.lines, util.pct(si.actionLines, si.lines),
                len(si.pages), si.pages))

            if self.inf[self.INF_SPEAKERS].selected:
                tf.addSpace(2.5)

                for it in util.sortDict(si.chars):
                    tf.addText("     %3d  %s" % (it[1], it[0]))

        return pdf.generate(tf.doc)

# information about one scene
class SceneInfo:
    def __init__(self, sp):
        # scene number, e.g. "42A"
        self.number = None

        # scene name, e.g. "INT. MOTEL ROOM - NIGHT"
        self.name = None

        # total lines, excluding scene lines
        self.lines = 0

        # action lines
        self.actionLines = 0

        # page numbers
        self.pages = screenplay.PageList(sp.getPageNumbers())

        # key = character name (upper cased), value = number of dialogue
        # lines
        self.chars = {}

    # read information for scene within given lines.
    def read(self, sp, startLine, endLine):
        self.number = sp.getSceneNumber(startLine)

        ls = sp.lines

        # TODO: handle multi-line scene names
        if ls[startLine].lt == screenplay.SCENE:
            s = util.upper(ls[startLine].text)

            if len(s.strip()) == 0:
                self.name = "(EMPTY SCENE NAME)"
            else:
                self.name = s
        else:
            self.name = "(NO SCENE NAME)"

        self.pages.addPage(sp.line2page(startLine))

        line = startLine

        # skip over scene headers
        while (line <= endLine) and (ls[line].lt == screenplay.SCENE):
            line = sp.getElemLastIndexFromLine(line) + 1

        if line > endLine:
            # empty scene
            return

        # re-define startLine to be first line after scene header
        startLine = line

        self.lines = endLine - startLine + 1

        # get number of action lines and store page information
        for i in range(startLine, endLine + 1):
            self.pages.addPage(sp.line2page(i))

            if ls[i].lt == screenplay.ACTION:
                self.actionLines += 1

        line = startLine
        while 1:
            line = self.readSpeech(sp, line, endLine)
            if line >= endLine:
                break

    # read information for one (or zero) speech, beginning at given line.
    # return line number of the last line of the speech + 1, or endLine +
    # 1 if no speech found.
    def readSpeech(self, sp, line, endLine):
        ls = sp.lines

        # find start of speech
        while (line < endLine) and (ls[line].lt != screenplay.CHARACTER):
            line += 1

        if line >= endLine:
            # no speech found, or CHARACTER was on last line, leaving no
            # space for dialogue.
            return endLine

        # TODO: handle multi-line character names
        s = util.upper(ls[line].text)
        if len(s.strip()) == 0:
            name = "(EMPTY CHARACTER NAME)"
        else:
            name = s

        # skip over character name
        line = sp.getElemLastIndexFromLine(line) + 1

        # dialogue lines
        dlines = 0

        while 1:
            if line > endLine:
                break

            lt = ls[line].lt

            if lt == screenplay.DIALOGUE:
                dlines += 1
            elif lt != screenplay.PAREN:
                break

            line += 1

        if dlines > 0:
            self.chars[name] = self.chars.get(name, 0) + dlines

        return line

########NEW FILE########
__FILENAME__ = screenplay
# -*- coding: utf-8 -*-

# linebreak types

LB_SPACE = 1

# we don't use this anymore, but we have to keep it in order to be able to
# load old scripts
LB_SPACE2 = 2

LB_NONE = 3
LB_FORCED = 4
LB_LAST = 5

# line types
SCENE = 1
ACTION = 2
CHARACTER = 3
DIALOGUE = 4
PAREN = 5
TRANSITION = 6
SHOT = 7
NOTE = 8
ACTBREAK = 9

import autocompletion
import config
import error
import headers
import locations
import mypager
import pdf
import pml
import spellcheck
import titles
import undo
import util

import codecs
import copy
import difflib
import re
import sys
import time

from lxml import etree

# screenplay
class Screenplay:
    def __init__(self, cfgGl):
        self.autoCompletion = autocompletion.AutoCompletion()
        self.headers = headers.Headers()
        self.locations = locations.Locations()
        self.titles = titles.Titles()
        self.scDict = spellcheck.Dict()

        self.lines = [ Line(LB_LAST, SCENE) ]

        self.cfgGl = cfgGl
        self.cfg = config.Config()

        # cursor position: line and column
        self.line = 0
        self.column = 0

        # first line shown on screen. use getTopLine/setTopLine to access
        # this.
        self._topLine = 0

        # Mark object if selection active, or None.
        self.mark = None

        # FIXME: document these
        self.pages = [-1, 0]
        self.pagesNoAdjust = [-1, 0]

        # time when last paginated
        self.lastPaginated = 0.0

        # list of active auto-completion strings
        self.acItems = None

        # selected auto-completion item (only valid when acItems contains
        # something)
        self.acSel = -1

        # max nr of auto comp items displayed at once
        self.acMax = 10

        # True if script has had changes done to it after
        # load/save/creation.
        self.hasChanged = False

        # first/last undo objects (undo.Base)
        self.firstUndo = None
        self.lastUndo = None

        # value of this, depending on the user's last action:
        #  undo: the undo object that was used
        #  redo: the next undo object from the one that was used
        #  anything else: None
        self.currentUndo = None

        # estimated amount of memory used by undo objects, in bytes
        self.undoMemoryUsed = 0

    def isModified(self):
        if not self.hasChanged:
            return False

        # nothing of value is ever lost by not saving a completely empty
        # script, and it's annoying getting warnings about unsaved changes
        # on those, so don't do that

        return (len(self.lines) > 1) or bool(self.lines[0].text)

    def markChanged(self, state = True):
        self.hasChanged = state

    def cursorAsMark(self):
        return Mark(self.line, self.column)

    # return True if the line is a parenthetical and not the first line of
    # that element (such lines need an extra space of indenting).
    def needsExtraParenIndent(self, line):
        return (self.lines[line].lt == PAREN) and not self.isFirstLineOfElem(line)

    def getSpacingBefore(self, i):
        if i == 0:
            return 0

        tcfg = self.cfg.types[self.lines[i].lt]

        if self.lines[i - 1].lb == LB_LAST:
            return tcfg.beforeSpacing
        else:
            return tcfg.intraSpacing

    # we implement our own custom deepcopy because it's 8-10x faster than
    # the generic one (times reported by cmdSpeedTest using a 119-page
    # screenplay):
    #
    # ╭─────────────────────────────┬─────────┬────────╮
    # │                             │ Generic │ Custom │
    # ├─────────────────────────────┼─────────┼────────┤
    # │ Intel Core Duo T2050 1.6GHz │  0.173s │ 0.020s │
    # │ Intel i5-2400 3.1GHz        │  0.076s │ 0.007s │
    # ╰─────────────────────────────┴─────────┴────────╯
    def __deepcopy__(self, memo):
        sp = Screenplay(self.cfgGl)
        sp.cfg = copy.deepcopy(self.cfg)

        sp.autoCompletion = copy.deepcopy(self.autoCompletion)
        sp.headers = copy.deepcopy(self.headers)
        sp.locations = copy.deepcopy(self.locations)
        sp.titles = copy.deepcopy(self.titles)
        sp.scDict = copy.deepcopy(self.scDict)

        sp.lines = [Line(ln.lb, ln.lt, ln.text) for ln in self.lines]

        # "open PDF on current page" breaks on scripts we're removing
        # notes from before printing if we don't copy these
        sp.line = self.line
        sp.column = self.column

        return sp

    # save script to a string and return that
    def save(self):
        self.cfg.cursorLine = self.line
        self.cfg.cursorColumn = self.column

        output = util.String()

        output += codecs.BOM_UTF8
        output += "#Version 3\n"

        output += "#Begin-Auto-Completion \n"
        output += self.autoCompletion.save()
        output += "#End-Auto-Completion \n"

        output += "#Begin-Config \n"
        output += self.cfg.save()
        output += "#End-Config \n"

        output += "#Begin-Locations \n"
        output += self.locations.save()
        output += "#End-Locations \n"

        output += "#Begin-Spell-Checker-Dict \n"
        output += self.scDict.save()
        output += "#End-Spell-Checker-Dict \n"

        pgs = self.titles.pages
        for pg in xrange(len(pgs)):
            if pg != 0:
                output += "#Title-Page \n"

            for i in xrange(len(pgs[pg])):
                output += "#Title-String %s\n" % str(pgs[pg][i])

        for h in self.headers.hdrs:
            output += "#Header-String %s\n" % str(h)

        output += "#Header-Empty-Lines %d\n" % self.headers.emptyLinesAfter

        output += "#Start-Script \n"

        for i in xrange(len(self.lines)):
            output += util.toUTF8(str(self.lines[i]) + "\n")

        return str(output)

    # load script from string s and return a (Screenplay, msg) tuple,
    # where msgs is string (possibly empty) of warnings about the loading
    # process. fatal errors are indicated by raising a MiscError. note
    # that this is a static function.
    @staticmethod
    def load(s, cfgGl):
        if s[0:3] != codecs.BOM_UTF8:
            raise error.MiscError("File is not a Trelby screenplay.")

        lines = s[3:].splitlines()

        sp = Screenplay(cfgGl)

        # remove default empty line
        sp.lines = []

        if len(lines) < 2:
            raise error.MiscError("File has too few lines to be a valid\n"
                                  "screenplay file.")

        key, version = Screenplay.parseConfigLine(lines[0])
        if not key or (key != "Version"):
            raise error.MiscError("File doesn't seem to be a proper\n"
                                  "screenplay file.")

        if version not in ("1", "2", "3"):
            raise error.MiscError("File uses fileformat version '%s',\n"
                                  "which is not supported by this version\n"
                                  "of the program." % version)

        version = int(version)

        # current position at 'lines'
        index = 1

        s, index = Screenplay.getConfigPart(lines, "Auto-Completion", index)
        if s:
            sp.autoCompletion.load(s)

        s, index = Screenplay.getConfigPart(lines, "Config", index)
        if s:
            sp.cfg.load(s)

        s, index = Screenplay.getConfigPart(lines, "Locations", index)
        if s:
            sp.locations.load(s)

        s, index = Screenplay.getConfigPart(lines, "Spell-Checker-Dict",
                                            index)
        if s:
            sp.scDict.load(s)

        # used to keep track that element type only changes after a
        # LB_LAST line.
        prevType = None

        # did we encounter unknown lb types
        unknownLb = False

        # did we encounter unknown element types
        unknownTypes = False

        # did we encounter unknown config lines
        unknownConfigs = False

        # have we seen the Start-Script line. defaults to True in old
        # files which didn't have it.
        startSeen = version < 3

        for i in xrange(index, len(lines)):
            s = lines[i]

            if len(s) < 2:
                raise error.MiscError("Line %d is too short." % (i + 1))

            if s[0] == "#":
                key, val = Screenplay.parseConfigLine(s)
                if not key:
                    raise error.MiscError("Line %d has invalid syntax for\n"
                                          "config line." % (i + 1))

                if key == "Title-Page":
                    sp.titles.pages.append([])

                elif key == "Title-String":
                    if len(sp.titles.pages) == 0:
                        sp.titles.pages.append([])

                    tmp = titles.TitleString([])
                    tmp.load(val)
                    sp.titles.pages[-1].append(tmp)

                elif key == "Header-String":
                    tmp = headers.HeaderString()
                    tmp.load(val)
                    sp.headers.hdrs.append(tmp)

                elif key == "Header-Empty-Lines":
                    sp.headers.emptyLinesAfter = util.str2int(val, 1, 0, 5)

                elif key == "Start-Script":
                    startSeen = True

                else:
                    unknownConfigs = True

            else:
                if not startSeen:
                    unknownConfigs = True

                    continue

                lb = config.char2lb(s[0], False)
                lt = config.char2lt(s[1], False)
                text = util.toInputStr(util.fromUTF8(s[2:]))

                # convert unknown lb types into LB_SPACE
                if lb == None:
                    lb = LB_SPACE
                    unknownLb = True

                # convert unknown types into ACTION
                if lt == None:
                    lt = ACTION
                    unknownTypes = True

                if prevType and (lt != prevType):
                    raise error.MiscError("Line %d has invalid element"
                                          " type." % (i + 1))

                line = Line(lb, lt, text)
                sp.lines.append(line)

                if lb != LB_LAST:
                    prevType = lt
                else:
                    prevType = None

        if not startSeen:
            raise error.MiscError("Start-Script line not found.")

        if len(sp.lines) == 0:
            raise error.MiscError("File doesn't contain any screenplay"
                                  " lines.")

        if sp.lines[-1].lb != LB_LAST:
            raise error.MiscError("Last line doesn't end an element.")

        if cfgGl.honorSavedPos:
            sp.line = sp.cfg.cursorLine
            sp.column = sp.cfg.cursorColumn
            sp.validatePos()

        sp.reformatAll()
        sp.paginate()
        sp.titles.sort()
        sp.locations.refresh(sp.getSceneNames())

        msgs = []

        if unknownLb:
            msgs.append("Screenplay contained unknown linebreak types.")

        if unknownTypes:
            msgs.append("Screenplay contained unknown element types. These"
                        " have been converted to Action elements.")

        if unknownConfigs:
            msgs.append("Screenplay contained unknown information. This"
                        " probably means that the file was created with a"
                        " newer version of this program.\n\n"
                        "  You'll lose that information if you save over"
                        " the existing file.")

        return (sp, "\n\n".join(msgs))

    # lines is an array of strings. if lines[startIndex] == "Begin-$name
    # ", this searches for a string of "End-$name ", takes all the strings
    # between those two, joins the lines into a single string (lines
    # separated by a "\n") and returns (string,
    # line-index-after-the-end-line). returns ("", startIndex) if
    # startIndex does not contain the start line or startIndex is too big
    # for 'lines'. raises error.MiscError on errors.
    @staticmethod
    def getConfigPart(lines, name, startIndex):
        if (startIndex >= len(lines)) or\
               (lines[startIndex] != ("#Begin-%s " % name)):
            return ("", startIndex)

        try:
            endIndex = lines.index("#End-%s " % name, startIndex)
        except ValueError:
            raise error.MiscError("#End-%s not found" % name)

        return ("\n".join(lines[startIndex + 1:endIndex]), endIndex + 1)

    # parse a line containing a config-value in the format detailed in
    # fileformat.txt. line must have newline stripped from the end
    # already. returns a (key, value) tuple. if line doesn't match the
    # format, (None, None) is returned.
    @staticmethod
    def parseConfigLine(s):
        m = re.match("#([a-zA-Z0-9\-]+) (.*)", s)

        if m:
            return (m.group(1), m.group(2))
        else:
            return (None, None)

    # apply new config.
    def applyCfg(self, cfg):
        self.firstUndo = None
        self.lastUndo = None
        self.currentUndo = None
        self.undoMemoryUsed = 0

        self.cfg = copy.deepcopy(cfg)
        self.cfg.recalc()
        self.reformatAll()
        self.paginate()

        self.markChanged()

    # return script config as a string.
    def saveCfg(self):
        return self.cfg.save()

    # generate formatted text and return it as a string. if 'dopages' is
    # True, marks pagination in the output.
    def generateText(self, doPages):
        ls = self.lines

        output = util.String()

        for p in xrange(1, len(self.pages)):
            start, end = self.page2lines(p)

            if doPages and (p != 1):
                s = "%s %d. " % ("-" * 30, p)
                s += "-" * (60 - len(s))
                output += "\n%s\n\n" % s

            for i in xrange(start, end + 1):
                line = ls[i]
                tcfg = self.cfg.getType(line.lt)

                if tcfg.export.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if (i != 0) and (not doPages or (i != start)):
                    output += (self.getSpacingBefore(i) // 10) * "\n"

                if text and self.needsExtraParenIndent(i):
                    text = " " + text

                output += " " * tcfg.indent + text + "\n"

        return str(output)

    # generate HTML output and return it as a string, optionally including
    # notes.
    def generateHtml(self, includeNotes = True):
        ls = self.lines

        # We save space by shorter class names in html.
        htmlMap = {
            ACTION : "ac",
            CHARACTER : "ch",
            DIALOGUE : "di",
            PAREN : "pa",
            SCENE : "sc",
            SHOT : "sh",
            TRANSITION : "tr",
            NOTE : "nt",
            ACTBREAK : "ab",
        }

        # html header for files
        htmlHeader = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Exported Screenplay</title>
<style type="text/css">
body {background: #ffffff; color: #000000; text-align: center;}
pre, p {font: 12px/14px Courier, "Courier New", monospace !important;}
pre {text-align: left !important; letter-spacing: 0 !important; margin-top: 0px !important; margin-bottom: 0px !important;}
p {text-align: center;}
.title, .footer {margin: 15px;}
.spcenter {margin: 0 auto; width: 500px;}
.sc, .ab {font-weight: bold !important;}
.nt {color: blue; font-style: italic !important;}
</style>
</head>
<body>
"""
        htmlFooter = """<p class = "footer">***<br>
Generated with <a href="http://www.trelby.org">Trelby</a>.</p>
</body>
</html>"""

        content = etree.Element("div")
        content.set("class","spcenter")

        # title pages
        for page in self.titles.pages:
            for ts in page:
                for s in ts.items:
                    para = etree.SubElement(content, "p")
                    para.set("class", "title")
                    para.text = unicode(s, "ISO-8859-1")

            para = etree.SubElement(content, "p")
            para.set("class", "title")
            para.text = "***"

        for i in range(len(ls)):
            line = ls[i]

            if not includeNotes and (line.lt == NOTE):
                continue

            tcfg = self.cfg.getType(line.lt)
            if tcfg.export.isCaps:
                text = util.upper(line.text)
            else:
                text = line.text

            if text and self.needsExtraParenIndent(i):
                text = " " + text

            text = " " * tcfg.indent + text

            # do we need space before this line?
            lineSpaces = self.getSpacingBefore(i) // 10

            for num in range(lineSpaces):
                para = etree.SubElement(content, "pre")
                para.set("class", htmlMap[line.lt])
                para.text = " "

            # and now the line text
            para = etree.SubElement(content, "pre")
            para.set("class", htmlMap[line.lt])
            para.text = unicode(text, "ISO-8859-1")

        bodyText = etree.tostring(content, encoding='UTF-8', pretty_print=True)

        return htmlHeader + bodyText + htmlFooter

    # Return screenplay as list of tuples of the form (elType, elText).
    # forced linebreaks are represented as \n characters.
    def getElementsAsList(self):
        ls = self.lines
        eleList = []
        curLine = ""

        for line in ls:
            lineType = line.lt
            lineText = line.text

            if self.cfg.getType(line.lt).export.isCaps:
                lineText = util.upper(lineText)

            curLine += lineText

            if line.lb == LB_LAST:
                eleList.append((lineType, curLine))
                curLine = ""
            elif line.lb == LB_SPACE:
                curLine += " "
            elif line.lb == LB_FORCED:
                curLine += "\n"

        return eleList

    # Generate a Final Draft XML file and return as string.
    def generateFDX(self):
        eleList = self.getElementsAsList()
        fd = etree.Element("FinalDraft")
        fd.set("DocumentType", "Script")
        fd.set("Template", "No")
        fd.set("Version", "1")
        content = etree.SubElement(fd, "Content")

        xmlMap = {
            ACTION : "Action",
            CHARACTER : "Character",
            DIALOGUE : "Dialogue",
            PAREN : "Parenthetical",
            SCENE : "Scene Heading",
            SHOT : "Shot",
            TRANSITION : "Transition",
            NOTE : "Action",
            ACTBREAK : "New Act",
        }

        for ele in eleList:
            typ, txt = ele
            if typ == NOTE:
                dummyPara = etree.SubElement(content, "Paragraph")
                dummyPara.set("Type", xmlMap[typ])
                scriptnote = etree.SubElement(dummyPara, "ScriptNote")
                scriptnote.set("ID", "1")
                para = etree.SubElement(scriptnote, "Paragraph")
            else:
                para = etree.SubElement(content, "Paragraph")
                para.set("Type", xmlMap[typ])

            paratxt = etree.SubElement(para, "Text")
            paratxt.text = unicode(txt, "ISO-8859-1")

        # FD does not recognize "New Act" by default. It needs an
        # ElementSettings element added.
        eleSet = etree.SubElement(fd, "ElementSettings")
        eleSet.set("Type", xmlMap[ACTBREAK])
        eleSetFont = etree.SubElement(eleSet, "FontSpec")
        eleSetFont.set("Style", "Underline+AllCaps")
        eleSetPara = etree.SubElement(eleSet, "ParagraphSpec")
        eleSetPara.set("Alignment","Center")

        return etree.tostring(
            fd, xml_declaration=True, encoding='UTF-8', pretty_print=True)

    # generate Fountain and return it as a string.
    def generateFountain(self):
        eleList = self.getElementsAsList()
        flines = []
        TWOSPACE = "  "
        sceneStartsList = ("INT", "EXT", "EST", "INT./EXT", "INT/EXT", "I/E", "I./E")


        # does s look like a fountain scene line:
        def looksLikeScene(s):
            s = s.upper()
            looksGood = False
            for t in sceneStartsList:
                if s.startswith(t):
                    looksGood = True
                    break
            return looksGood

        for ele in eleList:
            typ, txt = ele
            lns = txt.split("\n")

            #ensure last element of flines is empty for some types.
            if typ in (SCENE, ACTION, CHARACTER, TRANSITION, SHOT, ACTBREAK, NOTE):
                if flines and flines[-1] != "":
                    flines.append("")

            # special handling of some elements.
            if typ == SCENE:
                # if the line would not be recognized as Scene by fountain,
                # append a "." so it is forced as a scene line.
                if not looksLikeScene(txt):
                    txt = "." + txt

            elif typ == ACTION:
                tmp = []
                for ln in lns:
                    if ln and (ln.isupper() or looksLikeScene(txt)):
                        tmp.append(ln + TWOSPACE)
                    else:
                        tmp.append(ln)
                txt = "\n".join(tmp)

            elif typ == TRANSITION:
                if not txt.endswith("TO:"):
                    txt = "> " + txt

            elif typ == DIALOGUE:
                tmp = []
                for ln in lns:
                    if not ln:
                        tmp.append(TWOSPACE)
                    else:
                        tmp.append(ln)
                txt = "\n".join(tmp)

            elif typ == NOTE:
                txt = "[[" + txt + "]]"

            elif typ == ACTBREAK:
                txt = ">" + txt + "<"

            elif typ == SHOT:
                txt += TWOSPACE

            flines.append(txt)

        return util.toUTF8("\n".join(flines))

    # generate RTF and return it as a string.
    def generateRTF(self):
        ls = self.lines
        s = util.String()

        s += r"{\rtf1\ansi\deff0{\fonttbl{\f0\fmodern Courier;}}" + "\n"

        s+= "{\\stylesheet\n"

        mt = util.mm2twips
        fs = self.cfg.fontSize

        # since some of our units (beforeSpacing, indent, width) are
        # easier to handle if we assume normal font size, this is a scale
        # factor from actual font size to normal font size
        sf = fs / 12.0

        for ti in config.getTIs():
            t = self.cfg.getType(ti.lt)
            tt = t.export

            # font size is expressed as font size * 2 in RTF
            tmp = " \\fs%d" % (fs * 2)

            if tt.isCaps:
                tmp += r" \caps"

            if tt.isBold:
                tmp += r" \b"

            if tt.isItalic:
                tmp += r" \i"

            if tt.isUnderlined:
                tmp += r" \ul"

            # some hairy conversions going on here...
            tmp += r" \li%d\ri%d" % (sf * t.indent * 144,
                mt(self.cfg.paperWidth) -
                      (mt(self.cfg.marginLeft + self.cfg.marginRight) +
                      (t.indent + t.width) * 144 * sf))

            tmp += r" \sb%d" % (sf * t.beforeSpacing * 24)

            s += "{\\s%d%s %s}\n" % (ti.lt, tmp, ti.name)

        s += "}\n"

        s += r"\paperw%d\paperh%d\margt%d\margr%d\margb%d\margl%d" % (
            mt(self.cfg.paperWidth), mt(self.cfg.paperHeight),
            mt(self.cfg.marginTop), mt(self.cfg.marginRight),
            mt(self.cfg.marginBottom), mt(self.cfg.marginLeft))
        s += "\n"

        s += self.titles.generateRTF()

        length = len(ls)
        i = 0

        magicslash = "TRELBY-MAGIC-SLASH"

        while i < length:
            lt = ls[i].lt
            text = ""

            while 1:
                ln = ls[i]
                i += 1

                lb = ln.lb
                text += ln.text

                if lb in (LB_SPACE, LB_NONE):
                    text += config.lb2str(lb)
                elif lb == LB_FORCED:
                    text += magicslash + "line "
                elif lb == LB_LAST:
                    break
                else:
                    raise error.MiscError("Unknown line break style %d"
                                          " in generateRTF" % lb)

            s += (r"{\pard \s%d " % lt) + util.escapeRTF(text).replace(
                magicslash, "\\") + "}{\\par}\n"

        s += "}"

        return str(s)

    # generate PDF and return it as a string. assumes paginate/reformat is
    # 100% correct for the screenplay. isExport is True if this is an
    # "export to file" operation, False if we're just going to launch a
    # PDF viewer with the data.
    def generatePDF(self, isExport):
        return pdf.generate(self.generatePML(isExport))

    # Same arguments as generatePDF, but returns a PML document.
    def generatePML(self, isExport):
        pager = mypager.Pager(self.cfg)
        self.titles.generatePages(pager.doc)

        pager.doc.showTOC = self.cfg.pdfShowTOC

        if not isExport and self.cfg.pdfOpenOnCurrentPage:
            pager.doc.defPage = len(self.titles.pages) + \
                                self.line2page(self.line) - 1

        for i in xrange(1, len(self.pages)):
            pg = self.generatePMLPage(pager, i, True, True)

            if pg:
                pager.doc.add(pg)
            else:
                break

        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)

            if pf.pdfName:
                # TODO: it's nasty calling loadFile from here since it
                # uses wxMessageBox. dialog stacking order is also wrong
                # since we don't know the frame to give. so, we should
                # remove references to wxMessageBox from util and instead
                # pass in an ErrorHandlerObject to all functions that need
                # it. then the GUI program can use a subclass of that that
                # stores the frame pointer inside it, and testing
                # framework / other non-interactive uses can use a version
                # that logs errors to stderr / raises an exception /
                # whatever.

                if pf.filename != u"":
                    # we load at most 10 MB to avoid a denial-of-service
                    # attack by passing around scripts containing
                    # references to fonts with filenames like "/dev/zero"
                    # etc. no real font that I know of is this big so it
                    # shouldn't hurt.
                    fontProgram = util.loadFile(pf.filename, None,
                                                10 * 1024 * 1024)
                else:
                    fontProgram = None

                pager.doc.addFont(pf.style,
                                  pml.PDFFontInfo(pf.pdfName, fontProgram))

        return pager.doc

    # generate one page of PML data and return it.
    #
    # if forPDF is True, output is meant for PDF generation.
    #
    # if doExtra is False, omits headers and other stuff that is
    # automatically added, i.e. outputs only actual screenplay lines. also
    # text style/capitalization is not done 100% correctly. this should
    # only be True for callers that do not show the results in any way,
    # just calculate things based on text positions.
    #
    # can also return None, which means pagination is not up-to-date and
    # the given page number doesn't point to a valid page anymore, and the
    # caller should stop calling this since all pages have been generated
    # (assuming 1-to-n calling sequence).
    def generatePMLPage(self, pager, pageNr, forPDF, doExtra):
        #lsdjflksj = util.TimerDev("generatePMLPage")

        cfg = self.cfg
        ls = self.lines

        fs = cfg.fontSize
        chX = util.getTextWidth(" ", pml.COURIER, fs)
        chY = util.getTextHeight(fs)
        length = len(ls)

        start = self.pages[pageNr - 1] + 1

        if start >= length:
            # text has been deleted at end of script and pagination has
            # not been updated.
            return None

        # pagination may not be up-to-date, so any overflow text gets
        # dumped onto the last page which may thus be arbitrarily long.
        if pageNr == (len(self.pages) - 1):
            end = length - 1
        else:
            # another side-effect is that if text is deleted at the end,
            # self.pages can point to lines that no longer exist, so we
            # need to clamp it.
            end = util.clamp(self.pages[pageNr], maxVal = length - 1)

        pg = pml.Page(pager.doc)

        # what line we're on, counted from first line after top
        # margin, units = line / 10
        y = 0

        if pageNr != 1:
            if doExtra:
                self.headers.generatePML(pg, str(pageNr), cfg)
            y += self.headers.getNrOfLines() * 10

            if cfg.sceneContinueds and not self.isFirstLineOfScene(start):
                if doExtra:
                    s = cfg.strContinuedPageStart
                    if pager.sceneContNr != 0:
                        s += " (%d)" % (pager.sceneContNr + 1)

                    pg.add(pml.TextOp(s,
                        cfg.marginLeft + pager.sceneIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

                    pager.sceneContNr += 1

                    if cfg.pdfShowSceneNumbers:
                        self.addSceneNumbers(pg, "%d" % pager.scene,
                            cfg.getType(SCENE).width, y, chX, chY)

                y += 20

            if self.needsMore(start - 1):
                if doExtra:
                    pg.add(pml.TextOp(self.getPrevSpeaker(start) +
                        cfg.strDialogueContinued,
                        cfg.marginLeft + pager.charIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

                y += 10

        for i in xrange(start, end + 1):
            line = ls[i]
            tcfg = cfg.getType(line.lt)

            if i != start:
                y += self.getSpacingBefore(i)

            typ = pml.NORMAL

            if doExtra:
                if forPDF:
                    tt = tcfg.export
                else:
                    tt = tcfg.screen

                if tt.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if tt.isBold:
                    typ |= pml.BOLD
                if tt.isItalic:
                    typ |= pml.ITALIC
                if tt.isUnderlined:
                    typ |= pml.UNDERLINED
            else:
                text = line.text

            extraIndent = 1 if self.needsExtraParenIndent(i) else 0

            to = pml.TextOp(text,
                cfg.marginLeft + (tcfg.indent + extraIndent) * chX,
                cfg.marginTop + (y / 10.0) * chY, fs, typ, line = i)

            pg.add(to)

            if forPDF and (tcfg.lt == NOTE) and cfg.pdfOutlineNotes:
                offset = chX / 2.0
                nx = cfg.marginLeft + tcfg.indent * chX
                ny = cfg.marginTop + (y / 10.0) * chY
                nw = tcfg.width * chX
                lw = 0.25

                pg.add(pml.genLine(nx - offset, ny, 0.0, chY, lw))
                pg.add(pml.genLine(nx + nw + offset, ny, 0.0, chY, lw))

                if self.isFirstLineOfElem(i):
                    pg.add(pml.QuarterCircleOp(nx, ny, offset, lw))
                    pg.add(pml.genLine(nx, ny - offset, nw, 0.0, lw))
                    pg.add(pml.QuarterCircleOp(nx + nw, ny, offset, lw, True))

                    pg.add(pml.TextOp("Note",
                        (nx + nx + nw) / 2.0, ny - offset, 6, pml.ITALIC,
                        util.ALIGN_CENTER, util.VALIGN_BOTTOM))

                if self.isLastLineOfElem(i):
                    pg.add(pml.QuarterCircleOp(nx, ny + chY, offset, lw,
                                               False, True))
                    pg.add(pml.genLine(nx, ny + chY + offset, nw, 0.0, lw))
                    pg.add(pml.QuarterCircleOp(nx + nw, ny + chY, offset, lw,
                                               True, True))

            if doExtra and (tcfg.lt == SCENE) and self.isFirstLineOfElem(i):
                pager.sceneContNr = 0

                if cfg.pdfShowSceneNumbers:
                    pager.scene += 1
                    self.addSceneNumbers(pg, "%d" % pager.scene, tcfg.width,
                                         y, chX, chY)

                if cfg.pdfIncludeTOC:
                    if cfg.pdfShowSceneNumbers:
                        s = "%d %s" % (pager.scene, text)
                    else:
                        s = text

                    to.toc = pml.TOCItem(s, to)
                    pager.doc.addTOC(to.toc)

            if doExtra and cfg.pdfShowLineNumbers:
                pg.add(pml.TextOp("%02d" % (i - start + 1),
                    cfg.marginLeft - 3 * chX,
                    cfg.marginTop + (y / 10.0) * chY, fs))

            y += 10

        if self.needsMore(end):
            if doExtra:
                pg.add(pml.TextOp(cfg.strMore,
                        cfg.marginLeft + pager.charIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

            y += 10

        if cfg.sceneContinueds and not self.isLastLineOfScene(end):
            if doExtra:
                pg.add(pml.TextOp(cfg.strContinuedPageEnd,
                        cfg.marginLeft + cfg.sceneContinuedIndent * chX,
                        cfg.marginTop + (y / 10.0 + 1.0) * chY, fs))

            y += 10

        if forPDF and cfg.pdfShowMargins:
            lx = cfg.marginLeft
            rx = cfg.paperWidth - cfg.marginRight
            uy = cfg.marginTop
            dy = cfg.paperHeight - cfg.marginBottom

            pg.add(pml.LineOp([(lx, uy), (rx, uy), (rx, dy), (lx, dy)],
                              0, True))

        return pg

    def addSceneNumbers(self, pg, s, width, y, chX, chY):
        cfg = self.cfg

        pg.add(pml.TextOp(s, cfg.marginLeft - 6 * chX,
             cfg.marginTop + (y / 10.0) * chY, cfg.fontSize))
        pg.add(pml.TextOp(s, cfg.marginLeft + (width + 1) * chX,
            cfg.marginTop + (y / 10.0) * chY, cfg.fontSize))

    # get topLine, clamping it to the valid range in the process.
    def getTopLine(self):
        self._topLine = util.clamp(self._topLine, 0, len(self.lines) - 1)

        return self._topLine

    # set topLine, clamping it to the valid range.
    def setTopLine(self, line):
        self._topLine = util.clamp(line, 0, len(self.lines) - 1)

    def reformatAll(self):
        # doing a reformatAll while we have undo history will completely
        # break undo, so that can't be allowed.
        assert not self.firstUndo

        #sfdlksjf = util.TimerDev("reformatAll")

        line = 0

        while 1:
            line += self.rewrapPara(line)
            if line >= len(self.lines):
                break

    # reformat part of the screenplay. par1 is line number of paragraph to
    # start at, par2 the same for the ending one, inclusive.
    def reformatRange(self, par1, par2):
        ls = self.lines

        # add special tag to last paragraph we'll reformat
        ls[par2].reformatMarker = 0
        end = False

        line = par1
        while 1:
            if hasattr(ls[line], "reformatMarker"):
                del ls[line].reformatMarker
                end = True

            line += self.rewrapPara(line)
            if end:
                break

    # wraps a single line into however many lines are needed, according to
    # the type's width. doesn't modify the input line, returns a list of
    # new lines.
    def wrapLine(self, line):
        ret = []
        width = self.cfg.getType(line.lt).width
        isParen = line.lt == PAREN

        # text remaining to be wrapped
        text = line.text

        while 1:
            # reduce parenthetical width by 1 from second line onwards
            if isParen and ret:
                w = width - 1
            else:
                w = width

            if len(text) <= w:
                ret.append(Line(line.lb, line.lt, text))
                break
            else:
                i = text.rfind(" ", 0, w + 1)

                if i == w:

                    # we allow space characters to go over the line
                    # length, for two reasons:
                    #
                    # 1) it is impossible to get the behavior right
                    # otherwise in situations where a line ends in two
                    # spaces and the user inserts a non-space character at
                    # the end of the line. the cursor must be positioned
                    # at the second space character for this to work
                    # right, and the only way to get that is to allow
                    # spaces to go over the normal line length.
                    #
                    # 2) doing this results in no harm, since space
                    # characters print as empty, so they don't overwrite
                    # anything.

                    i += 1
                    while text[i:i + 1] == " ":
                        i += 1

                    if i == len(text):
                        ret.append(Line(line.lb, line.lt, text))

                        break
                    else:
                        ret.append(Line(LB_SPACE, line.lt, text[0:i - 1]))
                        text = text[i:]

                elif i >= 0:
                    ret.append(Line(LB_SPACE, line.lt, text[0:i]))
                    text = text[i + 1:]

                else:
                    ret.append(Line(LB_NONE, line.lt, text[0:w]))
                    text = text[w:]

        return ret

    # rewrap paragraph starting at given line. returns the number of lines
    # in the wrapped paragraph. if line1 is -1, rewraps paragraph
    # containing self.line. maintains cursor position correctness.
    def rewrapPara(self, line1 = -1):
        ls = self.lines

        if line1 == -1:
            line1 = self.getParaFirstIndexFromLine(self.line)

        line2 = line1

        while ls[line2].lb not in (LB_LAST, LB_FORCED):
            line2 += 1

        if (self.line >= line1) and (self.line <= line2):
            # cursor is in this paragraph, save its offset from the
            # beginning of the paragraph
            cursorOffset = 0

            for i in range(line1, line2 + 1):
                if i == self.line:
                    cursorOffset += self.column

                    break
                else:
                    cursorOffset += len(ls[i].text) + \
                                    len(config.lb2str(ls[i].lb))
        else:
            cursorOffset = -1

        s = ls[line1].text
        for i in range(line1 + 1, line2 + 1):
            s += config.lb2str(ls[i - 1].lb)
            s += ls[i].text

        tmp = Line(ls[line2].lb, ls[line1].lt, s)
        wrappedLines = self.wrapLine(tmp)
        ls[line1:line2 + 1] = wrappedLines

        # adjust cursor position
        if cursorOffset != -1:
            for i in range(line1, line1 + len(wrappedLines)):
                ln = ls[i]
                llen = len(ln.text) + len(config.lb2str(ln.lb))

                if cursorOffset < llen:
                    self.line = i
                    self.column = min(cursorOffset, len(ln.text))
                    break
                else:
                    cursorOffset -= llen

        elif self.line >= line1:
            # cursor position is below current paragraph, modify its
            # linenumber appropriately
            self.line += len(wrappedLines) - (line2 - line1 + 1)

        return len(wrappedLines)

    # rewraps paragraph previous to current one.
    def rewrapPrevPara(self):
        line = self.getParaFirstIndexFromLine(self.line)

        if line == 0:
            return

        line = self.getParaFirstIndexFromLine(line - 1)
        self.rewrapPara(line)

    # rewrap element starting at given line. if line is -1, rewraps
    # element containing self.line.
    def rewrapElem(self, line = -1):
        ls = self.lines

        if line == -1:
            line = self.getElemFirstIndex()

        while 1:
            line += self.rewrapPara(line)

            if ls[line - 1].lb == LB_LAST:
                break

    def isFirstLineOfElem(self, line):
        return (line == 0) or (self.lines[line - 1].lb == LB_LAST)

    def isLastLineOfElem(self, line):
        return self.lines[line].lb == LB_LAST

    def isOnlyLineOfElem(self, line):
        # this is just "isLastLineOfElem(line) and isFirstLineOfElem(line)"
        # inlined here, since it's 130% faster this way.
        return (self.lines[line].lb == LB_LAST) and \
               ((line == 0) or (self.lines[line - 1].lb == LB_LAST))

    # get first index of paragraph
    def getParaFirstIndexFromLine(self, line):
        ls = self.lines

        while 1:
            tmp = line - 1

            if tmp < 0:
                break

            if ls[tmp].lb in (LB_LAST, LB_FORCED):
                break

            line -= 1

        return line

    # get last index of paragraph
    def getParaLastIndexFromLine(self, line):
        ls = self.lines

        while 1:
            if ls[line].lb in (LB_LAST, LB_FORCED):
                break

            if (line + 1) >= len(ls):
                break

            line += 1

        return line

    def getElemFirstIndex(self):
        return self.getElemFirstIndexFromLine(self.line)

    def getElemFirstIndexFromLine(self, line):
        ls = self.lines

        while 1:
            tmp = line - 1

            if tmp < 0:
                break

            if ls[tmp].lb == LB_LAST:
                break

            line -= 1

        return line

    def getElemLastIndex(self):
        return self.getElemLastIndexFromLine(self.line)

    def getElemLastIndexFromLine(self, line):
        ls = self.lines

        while 1:
            if ls[line].lb == LB_LAST:
                break

            if (line + 1) >= len(ls):
                break

            line += 1

        return line

    def getElemIndexes(self):
        return self.getElemIndexesFromLine(self.line)

    def getElemIndexesFromLine(self, line):
        return (self.getElemFirstIndexFromLine(line),
                self.getElemLastIndexFromLine(line))

    def isFirstLineOfScene(self, line):
        if line == 0:
            return True

        ls = self.lines

        if ls[line].lt != SCENE:
            return False

        l = ls[line - 1]

        return (l.lt != SCENE) or (l.lb == LB_LAST)

    def isLastLineOfScene(self, line):
        ls = self.lines

        if ls[line].lb != LB_LAST:
            return False

        if line == (len(ls) - 1):
            return True

        return ls[line + 1].lt == SCENE

    def getTypeOfPrevElem(self, line):
        line = self.getElemFirstIndexFromLine(line)
        line -= 1

        if line < 0:
            return None

        return self.lines[line].lt

    def getTypeOfNextElem(self, line):
        line = self.getElemLastIndexFromLine(line)
        line += 1

        if line >= len(self.lines):
            return None

        return self.lines[line].lt

    def getSceneIndexes(self):
        return self.getSceneIndexesFromLine(self.line)

    def getSceneIndexesFromLine(self, line):
        top, bottom = self.getElemIndexesFromLine(line)
        ls = self.lines

        while 1:
            if ls[top].lt in (SCENE, ACTBREAK):
                break

            tmp = top - 1
            if tmp < 0:
                break

            top = self.getElemIndexesFromLine(tmp)[0]

        while 1:
            tmp = bottom + 1
            if tmp >= len(ls):
                break

            if ls[tmp].lt in (SCENE, ACTBREAK):
                break

            bottom = self.getElemIndexesFromLine(tmp)[1]

        return (top, bottom)

    # return scene number for the given line. if line is -1, return 0.
    def getSceneNumber(self, line):
        ls = self.lines
        sc = SCENE
        scene = 0

        for i in xrange(line + 1):
            if (ls[i].lt == sc) and self.isFirstLineOfElem(i):
                scene += 1

        return scene

    # return how many elements one must advance to get from element
    # containing line1 to element containing line2. line1 must be <=
    # line2, and either line can be anywhere in their respective elements.
    # returns 0 if they're in the same element, 1 if they're in
    # consecutive elements, etc.
    def elemsDistance(self, line1, line2):
        ls = self.lines

        count = 0
        line = line1

        while line < line2:
            if ls[line].lb == LB_LAST:
                count += 1

            line += 1

        return count

    # returns true if 'line', which must be the last line on a page, needs
    # (MORE) after it and the next page needs a "SOMEBODY (cont'd)".
    def needsMore(self, line):
        ls = self.lines

        return ls[line].lt in (DIALOGUE, PAREN)\
           and (line != (len(ls) - 1)) and\
           ls[line + 1].lt in (DIALOGUE, PAREN)

    # starting at line, go backwards until a line with type of CHARACTER
    # and lb of LAST is found, and return that line's text, possibly
    # upper-cased if CHARACTER's config for export says so.
    def getPrevSpeaker(self, line):
        ls = self.lines

        while 1:
            if line < 0:
                return "UNKNOWN"

            ln = ls[line]

            if (ln.lt == CHARACTER) and (ln.lb == LB_LAST):
                s = ln.text

                if self.cfg.getType(CHARACTER).export.isCaps:
                    s = util.upper(s)

                return s

            line -= 1

    # return total number of characters in script
    def getCharCount(self):
        return sum([len(ln.text) for ln in self.lines])

    def paginate(self):
        #sfdlksjf = util.TimerDev("paginate")

        self.pages = [-1]
        self.pagesNoAdjust = [-1]

        ls = self.lines
        cfg = self.cfg

        length = len(ls)
        lastBreak = -1

        # fast aliases for stuff
        lbl = LB_LAST
        ct = cfg.types
        hdrLines = self.headers.getNrOfLines()

        i = 0
        while 1:
            lp = cfg.linesOnPage * 10

            if i != 0:
                lp -= hdrLines * 10

                # decrease by 2 if we have to put a "CONTINUED:" on top of
                # this page.
                if cfg.sceneContinueds and not self.isFirstLineOfScene(i):
                    lp -= 20

                # decrease by 1 if we have to put a "WHOEVER (cont'd)" on
                # top of this page.
                if self.needsMore(i - 1):
                    lp -= 10

            # just a safeguard
            lp = max(50, lp)

            pageLines = 0
            if i < length:
                pageLines = 10

                # advance i until it points to the last line to put on
                # this page (before adjustments)

                while i < (length - 1):

                    pageLines += 10
                    if ls[i].lb == lbl:
                        pageLines += ct[ls[i + 1].lt].beforeSpacing
                    else:
                        pageLines += ct[ls[i + 1].lt].intraSpacing

                    if pageLines > lp:
                        break

                    i += 1

            if i >= (length - 1):
                if pageLines != 0:
                    self.pages.append(length - 1)
                    self.pagesNoAdjust.append(length - 1)

                break

            self.pagesNoAdjust.append(i)

            line = ls[i]

            if line.lt == SCENE:
                i = self.removeDanglingElement(i, SCENE, lastBreak)

            elif line.lt == SHOT:
                i = self.removeDanglingElement(i, SHOT, lastBreak)
                i = self.removeDanglingElement(i, SCENE, lastBreak)

            elif line.lt == ACTION:
                if line.lb != LB_LAST:
                    first = self.getElemFirstIndexFromLine(i)

                    if first > (lastBreak + 1):
                        linesOnThisPage = i - first + 1
                        if linesOnThisPage < cfg.pbActionLines:
                            i = first - 1

                        i = self.removeDanglingElement(i, SCENE,
                                                       lastBreak)

            elif line.lt == CHARACTER:
                i = self.removeDanglingElement(i, CHARACTER, lastBreak)
                i = self.removeDanglingElement(i, SCENE, lastBreak)

            elif line.lt in (DIALOGUE, PAREN):

                if line.lb != LB_LAST or\
                       self.getTypeOfNextElem(i) in (DIALOGUE, PAREN):

                    cutDialogue = False
                    cutParen = False
                    while 1:
                        oldI = i
                        line = ls[i]

                        if line.lt == PAREN:
                            i = self.removeDanglingElement(i, PAREN,
                              lastBreak)
                            cutParen = True

                        elif line.lt == DIALOGUE:
                            if cutParen:
                                break

                            first = self.getElemFirstIndexFromLine(i)

                            if first > (lastBreak + 1):
                                linesOnThisPage = i - first + 1

                                # do we need to reserve one line for (MORE)
                                reserveLine = not (cutDialogue or cutParen)

                                val = cfg.pbDialogueLines
                                if reserveLine:
                                    val += 1

                                if linesOnThisPage < val:
                                    i = first - 1
                                    cutDialogue = True
                                else:
                                    if reserveLine:
                                        i -= 1
                                    break
                            else:
                                # leave space for (MORE)
                                i -= 1
                                break

                        elif line.lt == CHARACTER:
                            i = self.removeDanglingElement(i, CHARACTER,
                                                           lastBreak)
                            i = self.removeDanglingElement(i, SCENE,
                                                           lastBreak)

                            break

                        else:
                            break

                        if i == oldI:
                            break

            # make sure no matter how buggy the code above is, we always
            # advance at least one line per page
            i = max(i, lastBreak + 1)

            self.pages.append(i)
            lastBreak = i

            i += 1

        self.lastPaginated = time.time()

    def removeDanglingElement(self, line, lt, lastBreak):
        ls = self.lines
        startLine = line

        while 1:
            if line < (lastBreak + 2):
                break

            ln = ls[line]

            if ln.lt != lt:
                break

            # only remove one element at most, to avoid generating
            # potentially thousands of pages in degenerate cases when
            # script only contains scenes or characters or something like
            # that.
            if (line != startLine) and (ln.lb == LB_LAST):
                break

            line -= 1

        return line

    # convert element(s) to given type
    #  - if multiple elements are selected, all are changed
    #  - if not, the change is applied to element under cursor.
    def convertTypeTo(self, lt, saveUndo):
        ls = self.lines
        selection = self.getMarkedLines()

        if selection:
            startSection, endSection = selection
            selectedElems = self.elemsDistance(startSection, endSection) + 1
        else:
            startSection, endSection = self.getElemIndexes()
            selectedElems = 1

        currentLine = startSection

        if saveUndo:
            u = undo.ManyElems(
                self, undo.CMD_MISC, currentLine, selectedElems, selectedElems)

        while currentLine <= endSection:
            first, last = self.getElemIndexesFromLine(currentLine)

            # if changing away from PAREN containing only "()", remove it
            if (first == last) and (ls[first].lt == PAREN) and\
                   (ls[first].text == "()"):
                ls[first].text = ""

                if first == self.line:
                    self.column = 0

            for i in range(first, last + 1):
                ls[i].lt = lt

            # if changing empty element to PAREN, add "()"
            if (first == last) and (ls[first].lt == PAREN) and\
                   (len(ls[first].text) == 0):
                ls[first].text = "()"

                if first == self.line:
                    self.column = 1

            currentLine = last + 1

        if selection:
            self.clearMark()

            # this is moderately complex because we need to deal with
            # forced linebreaks; reformatRange wants paragraph indexes but
            # we are converting elements, so we must find the indexes of
            # the a) first paragraph of the first selected element and b)
            # last paragraph of the last selected element

            self.reformatRange(
                self.getElemFirstIndexFromLine(startSection),
                self.getParaFirstIndexFromLine(self.getElemLastIndexFromLine(endSection)))
        else:
            self.rewrapElem(first)

        self.markChanged()

        if saveUndo:
            u.setAfter(self)
            self.addUndo(u)

    # join lines 'line' and 'line + 1' and position cursor at the join
    # position.
    def joinLines(self, line):
        ls = self.lines
        ln = ls[line]

        pos = len(ln.text)
        ln.text += ls[line + 1].text
        ln.lb = ls[line + 1].lb

        self.setLineTypes(line + 1, ln.lt)
        del ls[line + 1]

        self.line = line
        self.column = pos

    # split current line at current column position.
    def splitLine(self):
        ln = self.lines[self.line]

        s = ln.text
        preStr = s[:self.column]
        postStr = s[self.column:]
        newLine = Line(ln.lb, ln.lt, postStr)
        ln.text = preStr
        ln.lb = LB_FORCED
        self.lines.insert(self.line + 1, newLine)

        self.line += 1
        self.column = 0
        self.markChanged()

    # split element at current position. newType is type to give to the
    # new element.
    def splitElement(self, newType):
        ls = self.lines

        if self.mark:
            self.clearMark()

            return

        u = undo.ManyElems(self, undo.CMD_MISC, self.line, 1, 2)

        if not self.acItems:
            if self.isAtEndOfParen():
                self.column += 1
        else:
            ls[self.line].text = self.acItems[self.acSel]
            self.column = len(ls[self.line].text)

        self.splitLine()
        ls[self.line - 1].lb = LB_LAST

        self.convertTypeTo(newType, False)

        self.rewrapPara()
        self.rewrapPrevPara()
        self.markChanged()

        u.setAfter(self)
        self.addUndo(u)

    # delete character at given position and optionally position
    # cursor there.
    def deleteChar(self, line, column, posCursor = True):
        s = self.lines[line].text
        self.lines[line].text = s[:column] + s[column + 1:]

        if posCursor:
            self.column = column
            self.line = line

    # set line types from 'line' to the end of the element to 'lt'.
    def setLineTypes(self, line, lt):
        ls = self.lines

        while 1:
            ln = ls[line]

            ln.lt = lt
            if ln.lb == LB_LAST:
                break

            line += 1

    def line2page(self, line):
        return self.line2pageReal(line, self.pages)

    def line2pageNoAdjust(self, line):
        return self.line2pageReal(line, self.pagesNoAdjust)

    def line2pageReal(self, line, p):
        lo = 1
        hi = len(p) - 1

        while lo != hi:
            mid = (lo + hi) // 2

            if line <= p[mid]:
                hi = mid
            else:
                lo = mid + 1

        return lo

    # return (startLine, endLine) for given page number (1-based). if
    # pageNr is out of bounds, it is clamped to the valid range. if
    # pagination is out of date and the lines no longer exist, they are
    # clamped to the valid range as well.
    def page2lines(self, pageNr):
        pageNr = util.clamp(pageNr, 1, len(self.pages) - 1)
        last = len(self.lines) - 1

        return (util.clamp(self.pages[pageNr - 1] + 1, 0, last),
                util.clamp(self.pages[pageNr], 0, last))

    # return a list of all page numbers as strings.
    def getPageNumbers(self):
        pages = []

        for p in xrange(1, len(self.pages)):
            pages.append(str(p))

        return pages

    # return a list of all scene locations in a [(sceneNumber, startLine),
    # ...] format. if script does not start with a scene line, that scene
    # is not included in this list. note that the sceneNumber in the
    # returned list is a string, not a number.
    def getSceneLocations(self):
        ls = self.lines
        sc = SCENE
        scene = 0
        ret = []

        for i in xrange(len(ls)):
            if (ls[i].lt == sc) and self.isFirstLineOfElem(i):
                scene += 1
                ret.append((str(scene), i))

        return ret

    # return a dictionary of all scene names (single-line text elements
    # only, upper-cased, values = None).
    def getSceneNames(self):
        names = {}

        for ln in self.lines:
            if (ln.lt == SCENE) and (ln.lb == LB_LAST):
                names[util.upper(ln.text)] = None

        return names

    # return a dictionary of all character names (single-line text
    # elements only, lower-cased, values = None).
    def getCharacterNames(self):
        names = {}

        ul = util.lower

        for ln in self.lines:
            if (ln.lt == CHARACTER) and (ln.lb == LB_LAST):
                names[ul(ln.text)] = None

        return names

    # get next word, starting at (line, col). line must be valid, but col
    # can point after the line's length, in which case the search starts
    # at (line + 1, 0). returns (word, line, col), where word is None if
    # at end of script, and (line, col) point to the start of the word.
    # note that this only handles words that are on a single line.
    def getWord(self, line, col):
        ls = self.lines

        while 1:
            if ((line < 0) or (line >= len(ls))):
                return (None, 0, 0)

            s = ls[line].text

            if col >= len(s):
                line += 1
                col = 0

                continue

            ch = s[col : col + 1]

            if not util.isWordBoundary(ch):
                word = ch
                startCol = col
                col += 1

                while col < len(s):
                    ch = s[col : col + 1]

                    if util.isWordBoundary(ch):
                        break

                    word += ch
                    col += 1

                return (word, line, startCol)

            else:
                col += 1

    # returns True if we're at second-to-last character of PAREN element,
    # and last character is ")"
    def isAtEndOfParen(self):
        ls = self.lines

        return self.isLastLineOfElem(self.line) and\
           (ls[self.line].lt == PAREN) and\
           (ls[self.line].text[self.column:] == ")")

    # returns True if pressing TAB at current position would make a new
    # element, False if it would just change element's type.
    def tabMakesNew(self):
        l = self.lines[self.line]

        if self.isAtEndOfParen():
            return True

        if (l.lb != LB_LAST) or (self.column != len(l.text)):
            return False

        if (len(l.text) == 0) and self.isOnlyLineOfElem(self.line):
            return False

        return True

    # if auto-completion is active, clear it and return True. otherwise
    # return False.
    def clearAutoComp(self):
        if not self.acItems:
            return False

        self.acItems = None

        return True

    def fillAutoComp(self):
        ls = self.lines

        lt = ls[self.line].lt
        t = self.autoCompletion.getType(lt)

        if t and t.enabled:
            self.acItems = self.getMatchingText(ls[self.line].text, lt)
            self.acSel = 0

    # page up (dir == -1) or page down (dir == 1) was pressed and we're in
    # auto-comp mode, handle it.
    def pageScrollAutoComp(self, dir):
        if len(self.acItems) > self.acMax:

            if dir < 0:
                self.acSel -= self.acMax

                if self.acSel < 0:
                    self.acSel = len(self.acItems) - 1

            else:
                self.acSel = (self.acSel + self.acMax) % len(self.acItems)

    # get a list of strings (single-line text elements for now) that start
    # with 'text' (not case sensitive) and are of of type 'type'. also
    # mixes in the type's default items from config. ignores current line.
    def getMatchingText(self, text, lt):
        text = util.upper(text)
        t = self.autoCompletion.getType(lt)
        ls = self.lines
        matches = {}
        last = None

        for i in range(len(ls)):
            if (ls[i].lt == lt) and (ls[i].lb == LB_LAST):
                upstr = util.upper(ls[i].text)

                if upstr.startswith(text) and i != self.line:
                    matches[upstr] = None
                    if i < self.line:
                        last = upstr

        for s in t.items:
            upstr = util.upper(s)

            if upstr.startswith(text):
                matches[upstr] = None

        if last:
            del matches[last]

        mlist = matches.keys()
        mlist.sort()

        if last:
            mlist.insert(0, last)

        return mlist

    # returns pair (start, end) of marked lines, inclusive. if mark is
    # after the end of the script (text has been deleted since setting
    # it), returns a valid pair (by truncating selection to current
    # end). returns None if no lines marked.
    def getMarkedLines(self):
        if not self.mark:
            return None

        mark = min(len(self.lines) - 1, self.mark.line)

        if self.line < mark:
            return (self.line, mark)
        else:
            return (mark, self.line)

    # returns pair (start, end) (inclusive) of marked columns for the
    # given line (line must be inside the marked lines). 'marked' is the
    # value returned from getMarkedLines. if marked column is invalid
    # (text has been deleted since setting the mark), returns a valid pair
    # by truncating selection as needed. returns None on errors.
    def getMarkedColumns(self, line, marked):
        if not self.mark:
            return None

        # line is not marked at all
        if (line < marked[0]) or (line > marked[1]):
            return None

        ls = self.lines

        # last valid offset for given line's text
        lvo = max(0, len(ls[line].text) - 1)

        # only one line marked
        if (line == marked[0]) and (marked[0] == marked[1]):
            c1 = min(self.mark.column, self.column)
            c2 = max(self.mark.column, self.column)

        # line is between end lines, so totally marked
        elif (line > marked[0]) and (line < marked[1]):
            c1 = 0
            c2 = lvo

        # line is first line marked
        elif line == marked[0]:

            if line == self.line:
                c1 = self.column

            else:
                c1 = self.mark.column

            c2 = lvo

        # line is last line marked
        elif line == marked[1]:

            if line == self.line:
                c2 = self.column

            else:
                c2 = self.mark.column

            c1 = 0

        # should't happen
        else:
            return None

        c1 = util.clamp(c1, 0, lvo)
        c2 = util.clamp(c2, 0, lvo)

        return (c1, c2)

    # checks if a line is marked. 'marked' is the value returned from
    # getMarkedLines.
    def isLineMarked(self, line, marked):
        return (line >= marked[0]) and (line <= marked[1])

    # get selected text as a ClipData object, optionally deleting it from
    # the script. if nothing is selected, returns None.
    def getSelectedAsCD(self, doDelete):
        marked = self.getMarkedLines()

        if not marked:
            return None

        ls = self.lines

        cd = ClipData()

        for i in xrange(marked[0], marked[1] + 1):
            c1, c2 = self.getMarkedColumns(i, marked)

            ln = ls[i]

            cd.lines.append(Line(ln.lb, ln.lt, ln.text[c1:c2 + 1]))

        cd.lines[-1].lb = LB_LAST

        if not doDelete:
            return cd

        u = undo.AnyDifference(self)

        # range of lines, inclusive, that we need to totally delete
        del1 = sys.maxint
        del2 = -1

        # delete selected text from the lines
        for i in xrange(marked[0], marked[1] + 1):
            c1, c2 = self.getMarkedColumns(i, marked)

            ln = ls[i]
            ln.text = ln.text[0:c1] + ln.text[c2 + 1:]

            if i == marked[0]:
                endCol = c1

            # if we removed all text, mark this line to be deleted
            if len(ln.text) == 0:
                del1 = min(del1, i)
                del2 = max(del2, i)

        # adjust linebreaks
        if marked[0] == marked[1]:

            # user has selected text from a single line only

            ln = ls[marked[0]]

            # if it is a single-line element, we never need to modify
            # its linebreak
            if not self.isOnlyLineOfElem(marked[0]):
                # if we're totally deleting the line and it's the last
                # line of a multi-line element, mark the preceding
                # line as the new last line of the element.

                if not ln.text and self.isLastLineOfElem(marked[0]):
                    ls[marked[0] - 1].lb = LB_LAST

        else:

            # now find the line whose linebreak we need to adjust. if
            # the starting line is not completely removed, it is that,
            # otherwise it is the preceding line, unless we delete the
            # first line of the element, in which case there's nothing
            # to adjust.
            if ls[marked[0]].text:
                ln = ls[marked[0]]
            else:
                if not self.isFirstLineOfElem(marked[0]):
                    ln = ls[marked[0] - 1]
                else:
                    ln = None

            if ln:
                # if the selection ends by removing completely the
                # last line of an element, we need to mark the
                # element's new end, otherwise we must set it to
                # LB_NONE so that the new element is reformatted
                # properly.
                if self.isLastLineOfElem(marked[1]) and \
                       not ls[marked[1]].text:
                    ln.lb = LB_LAST
                else:
                    ln.lb = LB_NONE

        # if we're joining two elements we have to change the line
        # types for the latter element (starting from the last marked
        # line, because everything before that will get deleted
        # anyway) to that of the first element.
        self.setLineTypes(marked[1], ls[marked[0]].lt)

        del ls[del1:del2 + 1]

        self.clearMark()

        if len(ls) == 0:
            ls.append(Line(LB_LAST, SCENE))

        self.line = min(marked[0], len(ls) - 1)
        self.column = min(endCol, len(ls[self.line].text))

        self.rewrapElem()
        self.markChanged()

        u.setAfter(self)
        self.addUndo(u)

        return cd

    # paste data into script. clines is a list of Line objects.
    def paste(self, clines):
        if len(clines) == 0:
            return

        u = undo.AnyDifference(self)

        inLines = []
        i = 0

        # wrap all paragraphs into single lines
        while 1:
            if i >= len(clines):
                break

            ln = clines[i]

            newLine = Line(LB_LAST, ln.lt)

            while 1:
                ln = clines[i]
                i += 1

                newLine.text += ln.text

                if ln.lb in (LB_LAST, LB_FORCED):
                    break

                newLine.text += config.lb2str(ln.lb)

            newLine.lb = ln.lb
            inLines.append(newLine)

        # shouldn't happen, but...
        if len(inLines) == 0:
            return

        ls = self.lines

        # where we need to start wrapping
        wrap1 = self.getParaFirstIndexFromLine(self.line)

        ln = ls[self.line]

        atEnd = self.column == len(ln.text)

        if (len(ln.text) == 0) and self.isOnlyLineOfElem(self.line):
            ln.lt = inLines[0].lt

        ln.text = ln.text[:self.column] + inLines[0].text + \
                  ln.text[self.column:]
        self.column += len(inLines[0].text)

        if len(inLines) != 1:

            if not atEnd:
                self.splitLine()
                ls[self.line - 1].lb = inLines[0].lb
                ls[self.line:self.line] = inLines[1:]
                self.line += len(inLines) - 2

                # FIXME: pasting a multi-paragraph ACTION where first line
                # has FORCED lb, in middle of a CHARACTER block, breaks
                # things

            else:
                ls[self.line + 1:self.line + 1] = inLines[1:]
                self.line += len(inLines) - 1

                # FIXME: this doesn't modify .lb, and pasting a
                # multi-paragraph ACTION at end of line in CHARACTER block
                # where that line ends in forced linebreak breaks things.

            self.column = len(ls[self.line].text)

        # FIXME: copy/paste, when copying elements containing forced
        # linebreaks, converts them to end of element? this seems like a
        # bug...

        self.reformatRange(wrap1, self.getParaFirstIndexFromLine(self.line))

        u.setAfter(self)
        self.addUndo(u)

        self.clearMark()
        self.clearAutoComp()
        self.markChanged()

    # returns true if a character, inserted at current position, would
    # need to be capitalized as a start of a sentence.
    def capitalizeNeeded(self):
        if not self.cfgGl.capitalize:
            return False

        ls = self.lines
        line = self.line
        column = self.column

        text = ls[line].text
        if (column < len(text)) and (text[column] != " "):
            return False

        # go backwards at most 4 characters, looking for "!?.", and
        # breaking on anything other than space or ".

        cnt = 1
        while 1:
            column -= 1

            char = None

            if column < 0:
                line -= 1

                if line < 0:
                    return True

                lb = ls[line].lb

                if lb == LB_LAST:
                    return True

                elif lb == LB_SPACE:
                    char = " "
                    column = len(ls[line].text)

                else:
                    text = ls[line].text
                    column = len(text) - 1

                    if column < 0:
                        return True
            else:
                text = ls[line].text

            if not char:
                char = text[column]

            if cnt == 1:
                # must be preceded by a space
                if char != " ":
                    return False
            else:
                if char in (".", "?", "!"):
                    return True
                elif char not in (" ", "\""):
                    return False

            cnt += 1

            if cnt > 4:
                break

        return False

    # find next error in screenplay, starting at given line. returns
    # (line, msg) tuple, where line is -1 if no error was found and the
    # line number otherwise where the error is, and msg is a description
    # of the error
    def findError(self, line):
        ls = self.lines
        cfg = self.cfg

        # type of previous line, or None when a new element starts
        prevType = None

        msg = None
        while 1:
            if line >= len(ls):
                break

            ln = ls[line]
            tcfg = cfg.getType(ln.lt)

            isFirst = self.isFirstLineOfElem(line)
            isLast = self.isLastLineOfElem(line)
            isOnly = isFirst and isLast

            prev = self.getTypeOfPrevElem(line)
            next = self.getTypeOfNextElem(line)

            # notes are allowed to contain empty lines, because a) they do
            # not appear in the final product b) they're basically
            # free-format text anyway, and people may want to format them
            # however they want

            if (len(ln.text) == 0) and (ln.lt != NOTE):
                msg = "Empty line."
                break

            if (len(ln.text.strip("  ")) == 0) and (ln.lt != NOTE):
                msg = "Empty line (contains only spaces)."
                break

            if (ln.lt == PAREN) and isOnly and (ln.text == "()"):
                msg = "Empty parenthetical."
                break

            if ln.text != util.toInputStr(ln.text):
                msg = "Line contains invalid characters (BUG)."
                break

            if len(ln.text.rstrip(" ")) > tcfg.width:
                msg = "Line is too long (BUG)."
                break

            if ln.lt == CHARACTER:
                if isLast and next and next not in (PAREN, DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(next).ti.name, tcfg.ti.name)
                    break

            if ln.lt == PAREN:
                if isFirst and prev and prev not in (CHARACTER, DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (tcfg.ti.name, cfg.getType(prev).ti.name)
                    break

            if ln.lt == DIALOGUE:
                if isFirst and prev and prev not in (CHARACTER, PAREN):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (tcfg.ti.name, cfg.getType(prev).ti.name)
                    break

            if prevType:
                if ln.lt != prevType:
                    msg = "Element contains lines with different line"\
                          " types (BUG)."
                    break

            if ln.lb == LB_LAST:
                prevType = None
            else:
                prevType = ln.lt

            line += 1

        if not msg:
            line = -1

        return (line, msg)

    # compare this script to sp2 (Screenplay), return a PDF file (as a
    # string) of the differences, or None if the scripts are identical.
    def compareScripts(self, sp2):
        s1 = self.generateText(False).split("\n")
        s2 = sp2.generateText(False).split("\n")

        dltTmp = difflib.unified_diff(s1, s2, lineterm = "")

        # get rid of stupid delta generator object that doesn't allow
        # subscription or anything else really. also expands hunk
        # separators into three lines.
        dlt = []
        i = 0
        for s in dltTmp:
            if i >= 3:
                if s[0] == "@":
                    dlt.extend(["1", "2", "3"])
                else:
                    dlt.append(s)

            i += 1

        if len(dlt) == 0:
            return None

        dltTmp = dlt

        # now, generate changed-lines for single-line diffs
        dlt = []
        for i in xrange(len(dltTmp)):
            s = dltTmp[i]

            dlt.append(s)

            # this checks that we've just added a sequence of lines whose
            # first characters are " -+", where " " means '"not -" or
            # missing line', and that we're either at end of list or next
            # line does not start with "+".

            if (s[0] == "+") and \
               (i != 0) and (dltTmp[i - 1][0] == "-") and (
                (i == 1) or (dltTmp[i - 2][0] != "-")) and (
                (i == (len(dltTmp) - 1)) or (dltTmp[i + 1][0] != "+")):

                # generate line with "^" character at every position that
                # the lines differ

                s1 = dltTmp[i - 1]
                s2 = dltTmp[i]

                minCnt = min(len(s1), len(s2))
                maxCnt = max(len(s1), len(s2))

                res = "^"

                for i in range(1, minCnt):
                    if s1[i] != s2[i]:
                        res += "^"
                    else:
                        res += " "

                res += "^" * (maxCnt - minCnt)

                dlt.append(res)

        tmp = ["  Color information:", "1", "-  Deleted lines",
               "+  Added lines",
               "^  Positions of single-line changes (marked with ^)", "1",
               "2", "2", "3"]
        tmp.extend(dlt)
        dlt = tmp

        cfg = self.cfg
        chY = util.getTextHeight(cfg.fontSize)

        doc = pml.Document(cfg.paperWidth, cfg.paperHeight)

        # how many lines put on current page
        y = 0

        pg = pml.Page(doc)

        # we need to gather text ops for each page into a separate list
        # and add that list to the page only after all other ops are
        # added, otherwise the colored bars will be drawn partially over
        # some characters.
        textOps = []

        for s in dlt:

            if y >= cfg.linesOnPage:
                pg.ops.extend(textOps)
                doc.add(pg)

                pg = pml.Page(doc)

                textOps = []
                y = 0

            if s[0] == "1":
                pass

            elif s[0] == "3":
                pass

            elif s[0] == "2":
                pg.add(pml.PDFOp("0.75 g"))
                w = 50.0
                pg.add(pml.RectOp(doc.w / 2.0 - w / 2.0, cfg.marginTop +
                    y * chY + chY / 4, w, chY / 2.0))
                pg.add(pml.PDFOp("0.0 g"))

            else:
                color = ""

                if s[0] == "-":
                    color = "1.0 0.667 0.667"
                elif s[0] == "+":
                    color = "0.667 1.0 0.667"
                elif s[0] == "^":
                    color = "1.0 1.0 0.467"

                if color:
                    pg.add(pml.PDFOp("%s rg" % color))
                    pg.add(pml.RectOp(cfg.marginLeft, cfg.marginTop + y * chY,
                        doc.w - cfg.marginLeft - 5.0, chY))
                    pg.add(pml.PDFOp("0.0 g"))

                textOps.append(pml.TextOp(s[1:], cfg.marginLeft,
                    cfg.marginTop + y * chY, cfg.fontSize))

            y += 1

        pg.ops.extend(textOps)
        doc.add(pg)

        return pdf.generate(doc)

    # move to line,col, and if mark is True, set mark there
    def gotoPos(self, line, col, mark = False):
        self.clearAutoComp()

        self.line = line
        self.column = col

        if mark and not self.mark:
            self.setMark(line, col)

    # remove all lines whose element types are in tdict as keys.
    def removeElementTypes(self, tdict, saveUndo):
        self.clearAutoComp()

        if saveUndo:
            u = undo.FullCopy(self)

        lsNew = []
        lsOld = self.lines
        sl = self.line

        # how many lines were removed from above the current line
        # (inclusive)
        cnt = 0

        for i in xrange(len(lsOld)):
            l = lsOld[i]

            if l.lt not in tdict:
                lsNew.append(l)
            else:
                if i <= sl:
                    cnt += 1

        self.line -= cnt

        if len(lsNew) == 0:
            lsNew.append(Line(LB_LAST, SCENE))

        self.lines = lsNew

        self.validatePos()
        self.clearMark()
        self.markChanged()

        if saveUndo:
            u.setAfter(self)
            self.addUndo(u)

    # set mark at given position
    def setMark(self, line, column):
        self.mark = Mark(line, column)

    # clear mark
    def clearMark(self):
        self.mark = None

    # if doIt is True and mark is not yet set, set it at current position.
    def maybeMark(self, doIt):
        if doIt and not self.mark:
            self.setMark(self.line, self.column)

    # make sure current line and column are within the valid bounds.
    def validatePos(self):
        self.line = util.clamp(self.line, 0, len(self.lines) - 1)
        self.column = util.clamp(self.column, 0,
                                 len(self.lines[self.line].text))

    # this must be called after each command (all functions named fooCmd
    # are commands)
    def cmdPost(self, cs):
        # TODO: is this needed?
        self.column = min(self.column, len(self.lines[self.line].text))

        if cs.doAutoComp == cs.AC_DEL:
            self.clearAutoComp()
        elif cs.doAutoComp == cs.AC_REDO:
            self.fillAutoComp()

    # helper function for calling commands. name is the name of the
    # command, e.g. "moveLeft".
    def cmd(self, name, char = None, count = 1):
        for i in range(count):
            cs = CommandState()

            if char:
                cs.char = char

            getattr(self, name + "Cmd")(cs)
            self.cmdPost(cs)

    # call addCharCmd for each character in s. ONLY MEANT TO BE USED IN
    # TEST CODE.
    def cmdChars(self, s):
        for char in s:
            self.cmd("addChar", char = char)

    def moveLeftCmd(self, cs):
        self.maybeMark(cs.mark)

        if self.column > 0:
            self.column -= 1
        else:
            if self.line > 0:
                self.line -= 1
                self.column = len(self.lines[self.line].text)

    def moveRightCmd(self, cs):
        self.maybeMark(cs.mark)

        if self.column != len(self.lines[self.line].text):
            self.column += 1
        else:
            if self.line < (len(self.lines) - 1):
                self.line += 1
                self.column = 0

    def moveUpCmd(self, cs):
        if not self.acItems:
            self.maybeMark(cs.mark)

            if self.line > 0:
                self.line -= 1

        else:
            self.acSel -= 1

            if self.acSel < 0:
                self.acSel = len(self.acItems) - 1

            cs.doAutoComp = cs.AC_KEEP

    def moveDownCmd(self, cs):
        if not self.acItems:
            self.maybeMark(cs.mark)

            if self.line < (len(self.lines) - 1):
                self.line += 1

        else:
            self.acSel = (self.acSel + 1) % len(self.acItems)

            cs.doAutoComp = cs.AC_KEEP

    def moveLineEndCmd(self, cs):
        if self.acItems:
            self.lines[self.line].text = self.acItems[self.acSel]
        else:
            self.maybeMark(cs.mark)

        self.column = len(self.lines[self.line].text)

    def moveLineStartCmd(self, cs):
        self.maybeMark(cs.mark)

        self.column = 0

    def moveStartCmd(self, cs):
        self.maybeMark(cs.mark)

        self.line = 0
        self.setTopLine(0)
        self.column = 0

    def moveEndCmd(self, cs):
        self.maybeMark(cs.mark)

        self.line = len(self.lines) - 1
        self.column = len(self.lines[self.line].text)

    def moveSceneUpCmd(self, cs):
        self.maybeMark(cs.mark)

        tmpUp = self.getSceneIndexes()[0]

        if self.line != tmpUp:
            self.line = tmpUp
        else:
            tmpUp -= 1
            if tmpUp >= 0:
                self.line = self.getSceneIndexesFromLine(tmpUp)[0]

        self.column = 0

    def moveSceneDownCmd(self, cs):
        self.maybeMark(cs.mark)

        tmpBottom = self.getSceneIndexes()[1]
        self.line = min(len(self.lines) - 1, tmpBottom + 1)
        self.column = 0

    def deleteBackwardCmd(self, cs):
        u = None
        mergeUndo = False

        # only merge with the previous item in undo history if:
        #   -we are not in middle of undo/redo
        #   -previous item is "delete backward"
        #   -cursor is exactly where it was left off by the previous item
        if (not self.currentUndo and self.lastUndo and
            (self.lastUndo.getType() == undo.CMD_DEL_BACKWARD) and
            (self.lastUndo.endPos == self.cursorAsMark())):
            u = self.lastUndo
            mergeUndo = True

        if self.column != 0:
            if not mergeUndo:
                u = undo.ManyElems(self, undo.CMD_DEL_BACKWARD, self.line, 1, 1)

            self.deleteChar(self.line, self.column - 1)
            self.markChanged()
            cs.doAutoComp = cs.AC_REDO
        else:
            if self.line != 0:
                ln = self.lines[self.line - 1]

                # delete at start of the line of the first line of the
                # element means "join up with previous element", so is a
                # 2->1 change. otherwise we just delete a character from
                # current element so no element count change.
                if ln.lb == LB_LAST:
                    u = undo.ManyElems(self, undo.CMD_MISC, self.line - 1, 2, 1)
                    mergeUndo = False
                else:
                    if not mergeUndo:
                        u = undo.ManyElems(self, undo.CMD_DEL_BACKWARD, self.line, 1, 1)

                if ln.lb == LB_NONE:
                    self.deleteChar(self.line - 1, len(ln.text) - 1,
                                    False)

                self.joinLines(self.line - 1)

                self.markChanged()

        self.rewrapElem()

        if u:
            if mergeUndo:
                self.addMergedUndo(u)
            else:
                u.setAfter(self)
                self.addUndo(u)

    def deleteForwardCmd(self, cs):
        u = None
        mergeUndo = False

        # only merge with the previous item in undo history if:
        #   -we are not in middle of undo/redo
        #   -previous item is "delete forward"
        #   -cursor is exactly where it was left off by the previous item
        if (not self.currentUndo and self.lastUndo and
            (self.lastUndo.getType() == undo.CMD_DEL_FORWARD) and
            (self.lastUndo.endPos == self.cursorAsMark())):
            u = self.lastUndo
            mergeUndo = True

        if self.column != len(self.lines[self.line].text):
            if not mergeUndo:
                u = undo.ManyElems(self, undo.CMD_DEL_FORWARD, self.line, 1, 1)

            self.deleteChar(self.line, self.column)
            self.markChanged()
            cs.doAutoComp = cs.AC_REDO
        else:
            if self.line != (len(self.lines) - 1):
                ln = self.lines[self.line]

                # delete at end of the line of the last line of the
                # element means "join up with next element", so is a 2->1
                # change. otherwise we just delete a character from
                # current element so no element count change.
                if ln.lb == LB_LAST:
                    u = undo.ManyElems(self, undo.CMD_MISC, self.line, 2, 1)
                    mergeUndo = False
                else:
                    if not mergeUndo:
                        u = undo.ManyElems(self, undo.CMD_DEL_FORWARD, self.line, 1, 1)

                if ln.lb == LB_NONE:
                    self.deleteChar(self.line + 1, 0, False)

                self.joinLines(self.line)

                self.markChanged()

        self.rewrapElem()

        if u:
            if mergeUndo:
                self.addMergedUndo(u)
            else:
                u.setAfter(self)
                self.addUndo(u)

    # aborts stuff, like selection, auto-completion, etc
    def abortCmd(self, cs):
        self.clearMark()

    # select all text of current scene
    def selectSceneCmd(self, cs):
        l1, l2 = self.getSceneIndexes()

        self.setMark(l1, 0)

        self.line = l2
        self.column = len(self.lines[l2].text)

    # select all text of the screenplay. sets mark at beginning and moves
    # cursor to the end.
    def selectAllCmd(self, cs):
        self.setMark(0, 0)

        self.line = len(self.lines) - 1
        self.column = len(self.lines[self.line].text)

    def insertForcedLineBreakCmd(self, cs):
        u = undo.ManyElems(self, undo.CMD_MISC, self.line, 1, 1)

        self.splitLine()

        self.rewrapPara()
        self.rewrapPrevPara()

        u.setAfter(self)
        self.addUndo(u)

    def splitElementCmd(self, cs):
        tcfg = self.cfgGl.getType(self.lines[self.line].lt)
        self.splitElement(tcfg.newTypeEnter)

    def setMarkCmd(self, cs):
        self.setMark(self.line, self.column)

    # either creates a new element or converts the current one to
    # nextTypeTab, depending on circumstances.
    def tabCmd(self, cs):
        if self.mark:
            self.clearMark()

            return

        tcfg = self.cfgGl.getType(self.lines[self.line].lt)

        if self.tabMakesNew():
            self.splitElement(tcfg.newTypeTab)
        else:
            self.convertTypeTo(tcfg.nextTypeTab, True)

    # switch current element to prevTypeTab.
    def toPrevTypeTabCmd(self, cs):
        if self.mark:
            self.clearMark()

            return

        tcfg = self.cfgGl.getType(self.lines[self.line].lt)
        self.convertTypeTo(tcfg.prevTypeTab, True)

    # add character cs.char if it's a valid one.
    def addCharCmd(self, cs):
        char = cs.char

        if len(char) != 1:
            return

        kc = ord(char)

        if not util.isValidInputChar(kc):
            return

        isSpace = char == " "

        # only merge with the previous item in undo history if:
        #   -we are not in middle of undo/redo
        #   -previous item is "add character"
        #   -cursor is exactly where it was left off by the previous item
        #
        # in addition, to get word-level undo, not element-level undo, we
        # want to merge all spaces with the word preceding them, but stop
        # merging when a new word begins. this is implemented by the
        # following algorith:
        #
        # lastUndo    char       merge
        # --------    -------    -----
        # non-space   non-space  Y
        # non-space   space      Y      <- change type of lastUndo to space
        # space       space      Y
        # space       non-space  N

        if (not self.currentUndo and self.lastUndo and
            (self.lastUndo.getType() in (undo.CMD_ADD_CHAR, undo.CMD_ADD_CHAR_SPACE)) and
            (self.lastUndo.endPos == self.cursorAsMark()) and
            not ((self.lastUndo.getType() == undo.CMD_ADD_CHAR_SPACE) and not isSpace)):

            u = self.lastUndo
            mergeUndo = True

            if isSpace:
                u.cmdType = undo.CMD_ADD_CHAR_SPACE
        else:
            mergeUndo = False

            if isSpace:
                u = undo.SinglePara(self, undo.CMD_ADD_CHAR_SPACE, self.line)
            else:
                u = undo.SinglePara(self, undo.CMD_ADD_CHAR, self.line)

        if self.capitalizeNeeded():
            char = util.upper(char)

        ls = self.lines
        s = ls[self.line].text

        if self.cfgGl.capitalizeI and (self.column > 0):
            s = ls[self.line].text

            if s[self.column - 1] == "i":
                if not util.isAlnum(char):
                    doIt = False

                    if self.column > 1:
                        if not util.isAlnum(s[self.column - 2]):
                            doIt = True
                    else:
                        if (self.line == 0) or \
                               (ls[self.line - 1].lb != LB_NONE):
                            doIt = True

                    if doIt:
                        s = util.replace(s, "I", self.column - 1, 1)

        s = s[:self.column] + char + s[self.column:]
        ls[self.line].text = s
        self.column += 1

        tmp = s.upper()
        if (tmp == "EXT.") or (tmp == "INT."):
            if self.isOnlyLineOfElem(self.line):
                ls[self.line].lt = SCENE
        elif (tmp == "(") and\
             ls[self.line].lt in (DIALOGUE, CHARACTER) and\
             self.isOnlyLineOfElem(self.line):
            ls[self.line].lt = PAREN
            ls[self.line].text = "()"

        self.rewrapPara()
        self.markChanged()

        cs.doAutoComp = cs.AC_REDO

        if mergeUndo:
            self.addMergedUndo(u)
        else:
            u.setAfter(self)
            self.addUndo(u)

    def toSceneCmd(self, cs):
        self.convertTypeTo(SCENE, True)

    def toActionCmd(self, cs):
        self.convertTypeTo(ACTION, True)

    def toCharacterCmd(self, cs):
        self.convertTypeTo(CHARACTER, True)

    def toDialogueCmd(self, cs):
        self.convertTypeTo(DIALOGUE, True)

    def toParenCmd(self, cs):
        self.convertTypeTo(PAREN, True)

    def toTransitionCmd(self, cs):
        self.convertTypeTo(TRANSITION, True)

    def toShotCmd(self, cs):
        self.convertTypeTo(SHOT, True)

    def toActBreakCmd(self, cs):
        self.convertTypeTo(ACTBREAK, True)

    def toNoteCmd(self, cs):
        self.convertTypeTo(NOTE, True)

    # return True if we can undo
    def canUndo(self):
        return bool(
            # undo history exists
            self.lastUndo

            # and we either:
            and (
                # are not in the middle of undo/redo
                not self.currentUndo or

                # or are, but can still undo more
                self.currentUndo.prev))

    # return True if we can redo
    def canRedo(self):
        return bool(self.currentUndo)

    def addUndo(self, u):
        if self.currentUndo:
            # new edit action while navigating undo history; throw away
            # any undo history after current point

            if self.currentUndo.prev:
                # not at beginning of undo history; cut off the rest
                self.currentUndo.prev.next = None
                self.lastUndo = self.currentUndo.prev
            else:
                # beginning of undo history; throw everything away
                self.firstUndo = None
                self.lastUndo = None

            self.currentUndo = None

            # we threw away an unknown number of undo items, so we must go
            # through all of the remaining ones and recalculate how much
            # memory is used
            self.undoMemoryUsed = 0

            tmp = self.firstUndo

            while tmp:
                self.undoMemoryUsed += tmp.memoryUsed()
                tmp = tmp.next

        if not self.lastUndo:
            # no undo history at all yet
            self.firstUndo = u
            self.lastUndo = u
        else:
            self.lastUndo.next = u
            u.prev = self.lastUndo
            self.lastUndo = u

        self.undoMemoryUsed += u.memoryUsed()

        # trim undo history until the estimated memory usage is small
        # enough
        while ((self.firstUndo is not self.lastUndo) and
               (self.undoMemoryUsed >= 5000000)):

            tmp = self.firstUndo
            tmp.next.prev = None
            self.firstUndo = tmp.next

            # it shouldn't be technically necessary to reset this, but it
            # might make the GC's job easier, and helps detecting bugs if
            # somebody somehow tries to access this later on
            tmp.next = None

            self.undoMemoryUsed -= tmp.memoryUsed()

        self.currentUndo = None

    def addMergedUndo(self, u):
        assert u is self.lastUndo

        memoryUsedBefore = u.memoryUsed()
        u.setAfter(self)
        memoryUsedAfter = u.memoryUsed()
        memoryUsedDiff = memoryUsedAfter - memoryUsedBefore

        self.undoMemoryUsed += memoryUsedDiff

    def undoCmd(self, cs):
        if not self.canUndo():
            return

        # the action to undo
        if self.currentUndo:
            u = self.currentUndo.prev
        else:
            u = self.lastUndo

        u.undo(self)
        self.currentUndo = u

        self.clearMark()
        self.markChanged()

    def redoCmd(self, cs):
        if not self.canRedo():
            return

        self.currentUndo.redo(self)
        self.currentUndo = self.currentUndo.next

        self.clearMark()
        self.markChanged()

    # check script for internal consistency. raises an AssertionError on
    # errors. ONLY MEANT TO BE USED IN TEST CODE.
    def _validate(self):
        # type of previous line, or None when a new element starts
        prevType = None

        # there must be at least one line
        assert len(self.lines) > 0

        # cursor position must be valid
        assert self.line >= 0
        assert self.line < len(self.lines)
        assert self.column >= 0
        assert self.column <= len(self.lines[self.line].text)

        for ln in self.lines:
            tcfg = self.cfg.getType(ln.lt)

            # lines should not contain invalid characters
            assert ln.text == util.toInputStr(ln.text)

            # lines shouldn't be longer than the type's maximum width,
            # unless the extra characters are all spaces
            assert len(ln.text.rstrip(" ")) <= tcfg.width

            # lines with LB_NONE linebreaks that end in a space should be
            # LB_SPACE instead
            if ln.lb == LB_NONE:
                assert not ln.text.endswith(" ")

            if prevType:
                assert ln.lt == prevType

            if ln.lb == LB_LAST:
                prevType = None
            else:
                prevType = ln.lt

# one line in a screenplay
class Line:
    def __init__(self, lb = LB_LAST, lt = ACTION, text = ""):

        # line break type
        self.lb = lb

        # line type
        self.lt = lt

        # text
        self.text = text

    def __str__(self):
        return config.lb2char(self.lb) + config.lt2char(self.lt)\
               + self.text

    def __ne__(self, other):
        return ((self.lt != other.lt) or (self.lb != other.lb) or
                (self.text != other.text))

    # opposite of __str__. NOTE: only meant for storing data internally by
    # the program! NOT USABLE WITH EXTERNAL INPUT DUE TO COMPLETE LACK OF
    # ERROR CHECKING!
    @staticmethod
    def fromStr(s):
        return Line(config.char2lb(s[0]), config.char2lt(s[1]), s[2:])

# used to keep track of selected area. this marks one of the end-points,
# while the other one is the current position.
class Mark:
    def __init__(self, line, column):
        self.line = line
        self.column = column

    def __eq__(self, other):
        return (self.line == other.line) and (self.column == other.column)

# data held in internal clipboard.
class ClipData:
    def __init__(self):

        # list of Line objects
        self.lines = []

# stuff we need when handling commands in Screenplay.
class CommandState:

    # what to do about auto-completion
    AC_DEL, AC_REDO, AC_KEEP = range(3)

    def __init__(self):

        self.doAutoComp = self.AC_DEL

        # only used for inserting characters, in which case this is the
        # character to insert in a string form.
        self.char = None

        # True if this is a movement command and we should set mark at the
        # current position before moving (note that currently this is just
        # set if shift is down)
        self.mark = False

        # True if we need to make current line visible
        self.needsVisifying = True

# keeps a collection of page numbers from a given screenplay, and allows
# formatting of the list intelligently, e.g. "4-7, 9, 11-16".
class PageList:
    def __init__(self, allPages):
        # list of all pages in the screenplay, in the format returned by
        # Screenplay.getPageNumbers().
        self.allPages = allPages

        # key = page number (str), value = unused
        self.pages = {}

    # add page to page list if it's not already there
    def addPage(self, page):
        self.pages[str(page)] = True

    def __len__(self):
        return len(self.pages)

    # merge two PageLists
    def __iadd__(self, other):
        for pg in other.pages.keys():
            self.addPage(pg)

        return self

    # return textual representation of pages where consecutive pages are
    # formatted as "x-y". example: "3, 5-8, 11".
    def __str__(self):
        # one entry for each page from above, containing True if that page
        # is contained in this PageList object
        hasPage = []

        for p in self.allPages:
            hasPage.append(p in self.pages.keys())

        # finished string
        s = ""

        # start index of current range, or -1 if no range in progress
        rangeStart = -1

        for i in xrange(len(self.allPages)):
            if rangeStart != -1:
                if not hasPage[i]:

                    # range ends

                    if i != (rangeStart + 1):
                        s += "-%s" % self.allPages[i - 1]

                    rangeStart = -1
            else:
                if hasPage[i]:
                    if s:
                        s += ", "

                    s += self.allPages[i]
                    rangeStart = i

        last = len(self.allPages) - 1

        # finish last range if needed
        if (rangeStart != -1) and (rangeStart != last):
            s += "-%s" % self.allPages[last]

        return s

########NEW FILE########
__FILENAME__ = scriptreport
import characterreport
import config
import gutil
import pdf
import pml
import scenereport
import screenplay
import util

def genScriptReport(mainFrame, sp):
    report = ScriptReport(sp)
    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

class ScriptReport:
    def __init__(self, sp):
        self.sp = sp
        self.sr = scenereport.SceneReport(sp)
        self.cr = characterreport.CharacterReport(sp)

    def generate(self):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 15.0, 12)

        ls = self.sp.lines

        total = len(ls)
        tf.addText("Total lines in script: %5d" % total)

        tf.addSpace(2.0)

        for t in config.getTIs():
            cnt = sum([1 for line in ls if line.lt == t.lt])
            tf.addText("        %13s:  %4d (%d%%)" % (t.name, cnt,
                                                      util.pct(cnt, total)))

        tf.addSpace(4.0)

        intLines = sum([si.lines for si in self.sr.scenes if
                        util.upper(si.name).startswith("INT.")])
        extLines = sum([si.lines for si in self.sr.scenes if
                        util.upper(si.name).startswith("EXT.")])

        tf.addText("Interior / exterior scenes: %d%% / %d%%" % (
            util.pct(intLines, intLines + extLines),
            util.pct(extLines, intLines + extLines)))

        tf.addSpace(4.0)

        tf.addText("Max / avg. scene length in lines: %d / %.2f" % (
            self.sr.longestScene, self.sr.avgScene))

        # lengths of action elements
        actions = []

        # length of current action element
        curLen = 0

        for ln in ls:
            if curLen > 0:
                if ln.lt == screenplay.ACTION:
                    curLen += 1

                    if ln.lb == screenplay.LB_LAST:
                        actions.append(curLen)
                        curLen = 0
                else:
                    actions.append(curLen)
                    curLen = 0
            else:
                if ln.lt == screenplay.ACTION:
                    curLen = 1

        if curLen > 0:
            actions.append(curLen)

        tf.addSpace(4.0)

        # avoid divide-by-zero
        if len(actions) > 0:
            maxA = max(actions)
            avgA = sum(actions) / float(len(actions))
        else:
            maxA = 0
            avgA = 0.0

        tf.addText("Max / avg. action element length in lines: %d / %.2f" % (
            maxA, avgA))

        tf.addSpace(4.0)

        tf.addText("Speaking characters: %d" % len(self.cr.cinfo))

        return pdf.generate(tf.doc)

########NEW FILE########
__FILENAME__ = spellcheck
import mypickle
import util

import wx

# words loaded from dict_en.dat.
gdict = set()

# key = util.getWordPrefix(word), value = set of words beginning with
# that prefix (only words in gdict)
prefixDict = {}

# load word dictionary. returns True on success or if it's already loaded,
# False on errors.
def loadDict(frame):
    if gdict:
        return True

    s = util.loadMaybeCompressedFile(u"dict_en.dat", frame)
    if not s:
        return False

    lines = s.splitlines()

    chars = "abcdefghijklmnopqrstuvwxyz"

    for ch1 in chars:
        for ch2 in chars:
            prefixDict[ch1 + ch2] = set()

    gwp = util.getWordPrefix

    for word in lines:
        # theoretically, we should do util.lower(util.toInputStr(it)), but:
        #
        #  -user's aren't supposed to modify the file
        #
        #  -it takes 1.35 secs, compared to 0.56 secs if we don't, on an
        #   1.33GHz Athlon
        gdict.add(word)

        if len(word) > 2:
            prefixDict[gwp(word)].add(word)

    return True

# dictionary, a list of known words that the user has specified.
class Dict:
    cvars = None

    def __init__(self):
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addList("wordsList", [], "Words",
                      mypickle.StrLatin1Var("", "", ""))

            v.makeDicts()

        self.__class__.cvars.setDefaults(self)

        # we have wordsList that we use for saving/loading, and words,
        # which we use during normal operation. it's possible we should
        # introduce a mypickle.SetVar...

        # key = word, lowercased, value = None
        self.words = {}

    # load from string 's'. does not throw any exceptions and silently
    # ignores any errors.
    def load(self, s):
        self.cvars.load(self.cvars.makeVals(s), "", self)

        self.words = {}

        for w in self.wordsList:
            self.words[w] = None

        self.refresh()

    # save to a string and return that.
    def save(self):
        self.wordsList = self.get()

        return self.cvars.save("", self)

    # fix up invalid values.
    def refresh(self):
        ww = {}

        for w in self.words.keys():
            w = self.cleanWord(w)

            if w:
                ww[w] = None

        self.words = ww

    # returns True if word is known
    def isKnown(self, word):
        return word in self.words

    # add word
    def add(self, word):
        word = self.cleanWord(word)

        if word:
            self.words[word] = None

    # set words from a list
    def set(self, words):
        self.words = {}

        for w in words:
            self.add(w)

    # get a sorted list of all the words.
    def get(self):
        keys = self.words.keys()
        keys.sort()

        return keys

    # clean up word in all possible ways and return it, or an empty string
    # if nothing remains.
    def cleanWord(self, word):
        word = util.splitToWords(util.lower(util.toInputStr(word)))

        if len(word) == 0:
            return ""

        return word[0]

# spell check a script
class SpellChecker:
    def __init__(self, sp, gScDict):
        self.sp = sp

        # user's global dictionary (Dict)
        self.gScDict = gScDict

        # key = word found in character names, value = None
        self.cnames = {}

        for it in sp.getCharacterNames():
            for w in util.splitToWords(it):
                self.cnames[w] = None

        self.word = None
        self.line = self.sp.line

        # we can't use the current column, because if the cursor is in the
        # middle of a word, we flag the partial word as misspelled.
        self.col = 0

    # find next possibly misspelled word and store its location. returns
    # True if such a word found.
    def findNext(self):
        line = self.line
        col = self.col

        # clear these so there's no chance of them left pointing to
        # something, we return False, and someone tries to access them
        # anyhow.
        self.word = None
        self.line = 0
        self.col = 0

        while 1:
            word, line, col = self.sp.getWord(line, col)

            if not word:
                return False

            if not self.isKnown(word):
                self.word = word
                self.line = line
                self.col = col

                return True

            col += len(word)

    # return True if word is a known word.
    def isKnown(self, word):
        word = util.lower(word)

        return word in gdict or \
               word in self.cnames or \
               self.sp.scDict.isKnown(word) or \
               self.gScDict.isKnown(word) or \
               word.isdigit()

# Calculates the Levenshtein distance between a and b.
def lev(a, b):
    n, m = len(a), len(b)

    if n > m:
        # Make sure n <= m, to use O(min(n, m)) space
        a, b = b, a
        n, m = m, n

    current = range(n + 1)

    for i in range(1, m + 1):
        previous, current = current, [i] + [0] * m

        for j in range(1, n + 1):
            add, delete = previous[j] + 1, current[j - 1] + 1

            change = previous[j - 1]

            if a[j - 1] != b[i - 1]:
                change += 1

            current[j] = min(add, delete, change)

    return current[n]

########NEW FILE########
__FILENAME__ = spellcheckcfgdlg
import gutil
import misc
import util

import wx

class SCDictDlg(wx.Dialog):
    def __init__(self, parent, scDict, isGlobal):
        wx.Dialog.__init__(self, parent, -1, "Spell checker dictionary",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.scDict = scDict

        vsizer = wx.BoxSizer(wx.VERTICAL)

        if isGlobal:
            s = "Global words:"
        else:
            s = "Script-specific words:"

        vsizer.Add(wx.StaticText(self, -1, s))

        self.itemsEntry = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE |
                                     wx.TE_DONTWRAP, size = (300, 300))
        vsizer.Add(self.itemsEntry, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        self.cfg2gui()

        util.finishWindow(self, vsizer)

        wx.EVT_TEXT(self, self.itemsEntry.GetId(), self.OnMisc)
        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def OnOK(self, event):
        self.scDict.refresh()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnMisc(self, event):
        self.scDict.set(misc.fromGUI(self.itemsEntry.GetValue()).split("\n"))

    def cfg2gui(self):
        self.itemsEntry.SetValue("\n".join(self.scDict.get()))

########NEW FILE########
__FILENAME__ = spellcheckdlg
import config
import misc
import spellcheck
import undo
import util

import wx

class SpellCheckDlg(wx.Dialog):
    def __init__(self, parent, ctrl, sc, gScDict):
        wx.Dialog.__init__(self, parent, -1, "Spell checker",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.WANTS_CHARS)

        self.ctrl = ctrl

        # spellcheck.SpellCheck
        self.sc = sc

        # user's global spell checker dictionary
        self.gScDict = gScDict

        # have we added any words to global dictionary
        self.changedGlobalDict = False

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Word:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.replaceEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        hsizer.Add(self.replaceEntry, 1, wx.EXPAND)

        vsizer.Add(hsizer, 1, wx.EXPAND | wx.BOTTOM, 15)

        gsizer = wx.FlexGridSizer(2, 2, 10, 10)
        gsizer.AddGrowableCol(1)

        replaceBtn = wx.Button(self, -1, "&Replace")
        gsizer.Add(replaceBtn)

        addScriptBtn = wx.Button(self, -1, "Add to &script dictionary")
        gsizer.Add(addScriptBtn, 0, wx.EXPAND)

        skipBtn = wx.Button(self, -1, "S&kip")
        gsizer.Add(skipBtn)

        addGlobalBtn = wx.Button(self, -1, "Add to &global dictionary")
        gsizer.Add(addGlobalBtn, 0, wx.EXPAND)

        vsizer.Add(gsizer, 0, wx.EXPAND, 0)

        suggestBtn = wx.Button(self, -1, "S&uggest replacement")
        vsizer.Add(suggestBtn, 0, wx.EXPAND | wx.TOP, 10)

        wx.EVT_TEXT_ENTER(self, self.replaceEntry.GetId(), self.OnReplace)

        wx.EVT_BUTTON(self, replaceBtn.GetId(), self.OnReplace)
        wx.EVT_BUTTON(self, addScriptBtn.GetId(), self.OnAddScript)
        wx.EVT_BUTTON(self, addGlobalBtn.GetId(), self.OnAddGlobal)
        wx.EVT_BUTTON(self, skipBtn.GetId(), self.OnSkip)
        wx.EVT_BUTTON(self, suggestBtn.GetId(), self.OnSuggest)

        wx.EVT_CHAR(self, self.OnChar)
        wx.EVT_CHAR(self.replaceEntry, self.OnChar)
        wx.EVT_CHAR(replaceBtn, self.OnChar)
        wx.EVT_CHAR(addScriptBtn, self.OnChar)
        wx.EVT_CHAR(skipBtn, self.OnChar)
        wx.EVT_CHAR(addGlobalBtn, self.OnChar)
        wx.EVT_CHAR(suggestBtn, self.OnChar)

        util.finishWindow(self, vsizer)

        self.showWord()

    def showWord(self):
        self.ctrl.sp.line = self.sc.line
        self.ctrl.sp.column = self.sc.col
        self.ctrl.sp.setMark(self.sc.line, self.sc.col + len(self.sc.word) - 1)

        self.replaceEntry.SetValue(self.sc.word)

        self.ctrl.makeLineVisible(self.sc.line)
        self.ctrl.updateScreen()

    def gotoNext(self, incCol = True):
        if incCol:
            self.sc.col += len(self.sc.word)

        if not self.sc.findNext():
            wx.MessageBox("No more incorrect words found.", "Results",
                          wx.OK, self)

            self.EndModal(wx.ID_OK)

            return

        self.showWord()

    def OnChar(self, event):
        kc = event.GetKeyCode()

        if kc == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_OK)

            return

        event.Skip()

    def OnReplace(self, event):
        if not self.sc.word:
            return

        sp = self.ctrl.sp
        u = undo.SinglePara(sp, undo.CMD_MISC, self.sc.line)

        word = util.toInputStr(misc.fromGUI(self.replaceEntry.GetValue()))
        ls = sp.lines

        sp.gotoPos(self.sc.line, self.sc.col)

        ls[self.sc.line].text = util.replace(
            ls[self.sc.line].text, word,
            self.sc.col, len(self.sc.word))

        sp.rewrapPara(sp.getParaFirstIndexFromLine(self.sc.line))

        # rewrapping a paragraph can have moved the cursor, so get the new
        # location of it, and then advance past the just-changed word
        self.sc.line = sp.line
        self.sc.col = sp.column + len(word)

        sp.clearMark()
        sp.markChanged()

        u.setAfter(sp)
        sp.addUndo(u)

        self.gotoNext(False)

    def OnSkip(self, event = None, autoFind = False):
        if not self.sc.word:
            return

        self.gotoNext()

    def OnAddScript(self, event):
        if not self.sc.word:
            return

        self.ctrl.sp.scDict.add(self.sc.word)
        self.ctrl.sp.markChanged()
        self.gotoNext()

    def OnAddGlobal(self, event):
        if not self.sc.word:
            return

        self.gScDict.add(self.sc.word)
        self.changedGlobalDict = True

        self.gotoNext()

    def OnSuggest(self, event):
        if not self.sc.word:
            return

        isAllCaps = self.sc.word == util.upper(self.sc.word)
        isCapitalized = self.sc.word[:1] == util.upper(self.sc.word[:1])

        word = util.lower(self.sc.word)

        wl = len(word)
        wstart = word[:2]
        d = 500
        fifo = util.FIFO(5)
        wx.BeginBusyCursor()

        for w in spellcheck.prefixDict[util.getWordPrefix(word)]:
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        for w in self.gScDict.words.iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        for w in self.ctrl.sp.scDict.words.iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        items = fifo.get()

        wx.EndBusyCursor()

        if len(items) == 0:
            wx.MessageBox("No similar words found.", "Results",
                          wx.OK, self)

            return

        dlg = wx.SingleChoiceDialog(
            self, "Most similar words:", "Suggestions", items)

        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetSelection()

            newWord = items[sel]

            if isAllCaps:
                newWord = util.upper(newWord)
            elif isCapitalized:
                newWord = util.capitalize(newWord)

            self.replaceEntry.SetValue(newWord)

        dlg.Destroy()

    # if w2 is closer to w1 in Levenshtein distance than d, add it to
    # fifo. return min(d, new_distance).
    def tryWord(self, w1, w1len, w2, d, fifo):
        if abs(w1len - len(w2)) > 3:
            return d

        d2 = spellcheck.lev(w1, w2)

        if d2 <= d:
            fifo.add(w2)

            return d2

        return d


########NEW FILE########
__FILENAME__ = splash
# -*- coding: utf-8 -*-

import misc
import util

import random
import sys

import wx

class Quote:
    def __init__(self, source, lines):
        # unicode string
        self.source = source

        # list of unicode strings
        self.lines = lines

class SplashWindow(wx.Frame):
    inited = False

    # Quote objects
    quotes = []

    def __init__(self, parent, delay):
        wx.Frame.__init__(
            self, parent, -1, "Splash",
            style = wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER)

        if not SplashWindow.inited:
            SplashWindow.inited = True
            wx.Image_AddHandler(wx.JPEGHandler())

            self.loadQuotes(parent)

        self.pickRandomQuote()

        self.pic = misc.getBitmap("resources/logo.jpg")

        if self.pic.Ok():
            w, h = (self.pic.GetWidth(), self.pic.GetHeight())
        else:
            w, h = (375, 300)

        util.setWH(self, w, h)
        self.CenterOnScreen()

        self.textColor = wx.Colour(0, 0, 0)

        self.font = util.createPixelFont(
            14, wx.FONTFAMILY_MODERN, wx.NORMAL, wx.NORMAL)

        self.quoteFont = util.createPixelFont(
            16, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)

        self.sourceFont = util.createPixelFont(
            15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.NORMAL)

        if delay != -1:
            self.timer = wx.Timer(self)
            wx.EVT_TIMER(self, -1, self.OnTimer)
            self.timer.Start(delay, True)

        wx.EVT_LEFT_DOWN(self, self.OnClick)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_CLOSE(self, self.OnCloseWindow)

    def OnClick(self, event):
        self.Close()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        dc.SetFont(self.font)
        dc.SetTextForeground(self.textColor)

        if self.pic.Ok():
            dc.DrawBitmap(self.pic, 0, 0, False)

        util.drawText(dc, "Version %s" % (misc.version),
                      200, 170, util.ALIGN_RIGHT)

        util.drawText(dc, "http://www.trelby.org/", 200, 185, util.ALIGN_RIGHT)

        if self.quote:
            dc.SetFont(self.sourceFont)
            dc.DrawText(self.quote.source, 50, 280)

            dc.SetFont(self.quoteFont)

            for i,line in enumerate(self.quote.lines):
                x = 10
                y = 260 - (len(self.quote.lines) - i - 1) * 17

                if i == 0:
                    dc.DrawText(u"“", x - 5, y)

                if i == (len(self.quote.lines) - 1):
                    line = line + u"”"

                dc.DrawText(line, x, y)


    def OnTimer(self, event):
        self.timer.Stop()
        self.Close()

    def OnCloseWindow(self, event):
        self.Destroy()
        self.Refresh()

    def pickRandomQuote(self):
        if not SplashWindow.quotes:
            self.quote = None
        else:
            self.quote = random.choice(SplashWindow.quotes)

    @staticmethod
    def loadQuotes(parent):
        try:
            data = util.loadFile(misc.getFullPath("resources/quotes.txt"), parent)
            if data is None:
                return

            data = data.decode("utf-8")
            lines = data.splitlines()

            quotes = []

            # lines saved for current quote being processed
            tmp = []

            for i,line in enumerate(lines):
                if line.startswith(u"#") or not line.strip():
                    continue

                if line.startswith(u"  "):
                    if not tmp:
                        raise Exception("No lines defined for quote at line %d" % (i + 1))

                    if len(tmp) > 3:
                        raise Exception("Too many lines defined for quote at line %d" % (i + 1))

                    quotes.append(Quote(line.strip(), tmp))
                    tmp = []
                else:
                    tmp.append(line.strip())

            if tmp:
                raise Exception("Last quote does not have source")

            SplashWindow.quotes = quotes

        except Exception, e:
            wx.MessageBox("Error loading quotes: %s" % str(e),
                          "Error", wx.OK, parent)

########NEW FILE########
__FILENAME__ = titles
import pml
import util

# a script's title pages.
class Titles:

    def __init__(self):
        # list of lists of TitleString objects
        self.pages = []

    # create semi-standard title page
    def addDefaults(self):
        a = []

        y = 105.0
        a.append(TitleString(["UNTITLED SCREENPLAY"], y = y, size = 24,
                             isBold = True, font = pml.HELVETICA))
        a.append(TitleString(["by", "", "My Name Here"], y = y + 15.46))

        x = 15.0
        y = 240.0
        a.append(TitleString(["123/456-7890", "no.such@thing.com"], x, y + 8.46, False))

        self.pages.append(a)

    # add title pages to doc.
    def generatePages(self, doc):
        for page in self.pages:
            pg = pml.Page(doc)

            for s in page:
                s.generatePML(pg)

            doc.add(pg)

    # return a (rough) RTF fragment representation of title pages
    def generateRTF(self):
        s = util.String()

        for page in self.pages:
            for p in page:
                s += p.generateRTF()

            s += "\\page\n"

        return str(s)

    # sort the title strings in y,x order (makes editing them easier
    # and RTF output better)
    def sort(self):
        def tmpfunc(a, b):
            return cmp(a.y, b.y) or cmp(a.x, b.x)

        for page in self.pages:
            page.sort(tmpfunc)

# a single string displayed on a title page
class TitleString:
    def __init__(self, items, x = 0.0, y = 0.0, isCentered = True,
                 isBold = False, size = 12, font = pml.COURIER):

        # list of text strings
        self.items = items

        # position
        self.x = x
        self.y = y

        # size in points
        self.size = size

        # whether this is centered in the horizontal direction
        self.isCentered = isCentered

        # whether this is right-justified (xpos = rightmost edge of last
        # character)
        self.isRightJustified = False

        # style flags
        self.isBold = isBold
        self.isItalic = False
        self.isUnderlined = False

        # font
        self.font = font

    def getStyle(self):
        fl = self.font

        if self.isBold:
            fl |= pml.BOLD

        if self.isItalic:
            fl |= pml.ITALIC

        if self.isUnderlined:
            fl |= pml.UNDERLINED

        return fl

    def getAlignment(self):
        if self.isCentered:
            return util.ALIGN_CENTER
        elif self.isRightJustified:
            return util.ALIGN_RIGHT
        else:
            return util.ALIGN_LEFT

    def setAlignment(self, align):
        if align == util.ALIGN_CENTER:
            self.isCentered = True
            self.isRightJustified = False
        elif align == util.ALIGN_RIGHT:
            self.isCentered = False
            self.isRightJustified = True
        else:
            self.isCentered = False
            self.isRightJustified = False

    def generatePML(self, page):
        y = self.y

        for line in self.items:
            x = self.x

            if self.isCentered:
                x = page.doc.w / 2.0

            page.add(pml.TextOp(line, x, y, self.size,
                                self.getStyle(), self.getAlignment()))

            y += util.getTextHeight(self.size)

    # return a (rough) RTF fragment representation of this string
    def generateRTF(self):
        s = ""

        for line in self.items:
            tmp = "\\fs%d" % (self.size * 2)

            if self.isCentered:
                tmp += " \qc"
            elif self.isRightJustified:
                tmp += " \qr"

            if self.isBold:
                tmp += r" \b"

            if self.isItalic:
                tmp += r" \i"

            if self.isUnderlined:
                tmp += r" \ul"

            s += r"{\pard\plain%s %s}{\par}" % (tmp, util.escapeRTF(line))

        return s

    # parse information from s, which must be a string created by __str__,
    # and set object state accordingly. keeps default settings on any
    # errors, does not throw any exceptions.
    #
    # sample of the format: '0.000000,70.000000,24,cb,Helvetica,,text here'
    def load(self, s):
        a = util.fromUTF8(s).split(",", 6)

        if len(a) != 7:
            return

        self.x = util.str2float(a[0], 0.0)
        self.y = util.str2float(a[1], 0.0)
        self.size = util.str2int(a[2], 12, 4, 288)

        self.isCentered, self.isRightJustified, self.isBold, self.isItalic, \
            self.isUnderlined = util.flags2bools(a[3], "crbiu")

        tmp = { "Courier" : pml.COURIER,
                "Helvetica" : pml.HELVETICA,
                "Times" : pml.TIMES_ROMAN }

        self.font = tmp.get(a[4], pml.COURIER)
        self.items = util.unescapeStrings(a[6])

    def __str__(self):
        s = "%f,%f,%d," % (self.x, self.y, self.size)

        s += util.bools2flags("crbiu", self.isCentered, self.isRightJustified, self.isBold,
                               self.isItalic, self.isUnderlined)
        s += ","

        if self.font == pml.COURIER:
            s += "Courier"
        elif self.font == pml.HELVETICA:
            s += "Helvetica"
        else:
            s += "Times"

        s += ",,%s" % util.escapeStrings(self.items)

        return util.toUTF8(s)

########NEW FILE########
__FILENAME__ = titlesdlg
import gutil
import misc
import pdf
import pml
import titles
import util

import copy

import wx

class TitlesDlg(wx.Dialog):
    def __init__(self, parent, titles, cfg, cfgGl):
        wx.Dialog.__init__(self, parent, -1, "Title pages",
                           style = wx.DEFAULT_DIALOG_STYLE)

        self.titles = titles
        self.cfg = cfg
        self.cfgGl = cfgGl

        # whether some events are blocked
        self.block = False

        self.setPage(0)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.pageLabel = wx.StaticText(self, -1, "")
        vsizer.Add(self.pageLabel, 0, wx.ADJUST_MINSIZE)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        tmp = wx.Button(self, -1, "Add")
        hsizer.Add(tmp)
        wx.EVT_BUTTON(self, tmp.GetId(), self.OnAddPage)
        gutil.btnDblClick(tmp, self.OnAddPage)

        self.delPageBtn = wx.Button(self, -1, "Delete")
        hsizer.Add(self.delPageBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.delPageBtn.GetId(), self.OnDeletePage)
        gutil.btnDblClick(self.delPageBtn, self.OnDeletePage)

        self.moveBtn = wx.Button(self, -1, "Move")
        hsizer.Add(self.moveBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.moveBtn.GetId(), self.OnMovePage)
        gutil.btnDblClick(self.moveBtn, self.OnMovePage)

        self.nextBtn = wx.Button(self, -1, "Next")
        hsizer.Add(self.nextBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.nextBtn.GetId(), self.OnNextPage)
        gutil.btnDblClick(self.nextBtn, self.OnNextPage)

        vsizer.Add(hsizer, 0, wx.TOP, 5)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM,
                   10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Strings:")
        vsizer2.Add(tmp)

        self.stringsLb = wx.ListBox(self, -1, size = (200, 150))
        vsizer2.Add(self.stringsLb)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.addBtn = gutil.createStockButton(self, "Add")
        hsizer2.Add(self.addBtn)
        wx.EVT_BUTTON(self, self.addBtn.GetId(), self.OnAddString)
        gutil.btnDblClick(self.addBtn, self.OnAddString)

        self.delBtn = gutil.createStockButton(self, "Delete")
        hsizer2.Add(self.delBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.delBtn.GetId(), self.OnDeleteString)
        gutil.btnDblClick(self.delBtn, self.OnDeleteString)

        vsizer2.Add(hsizer2, 0, wx.TOP, 5)

        hsizer.Add(vsizer2)

        self.previewCtrl = TitlesPreview(self, self, self.cfg)
        util.setWH(self.previewCtrl, 150, 150)
        hsizer.Add(self.previewCtrl, 1, wx.EXPAND | wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Text:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.textEntry = wx.TextCtrl(
            self, -1, style = wx.TE_MULTILINE | wx.TE_DONTWRAP, size = (200, 75))
        hsizer.Add(self.textEntry, 1, wx.LEFT, 10)
        wx.EVT_TEXT(self, self.textEntry.GetId(), self.OnMisc)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        # TODO: should use FlexGridSizer, like headersdlg, to get neater
        # layout

        hsizerTop = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Alignment:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.alignCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for it in [ ("Left", util.ALIGN_LEFT), ("Center", util.ALIGN_CENTER),
                    ("Right", util.ALIGN_RIGHT) ]:
            self.alignCombo.Append(it[0], it[1])

        hsizer.Add(self.alignCombo, 0, wx.LEFT, 10)
        wx.EVT_COMBOBOX(self, self.alignCombo.GetId(), self.OnMisc)

        vsizer2.Add(hsizer, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "X / Y Pos (mm):"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.xEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.xEntry, 0, wx.LEFT, 10)
        wx.EVT_TEXT(self, self.xEntry.GetId(), self.OnMisc)
        self.yEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.yEntry, 0, wx.LEFT, 10)
        wx.EVT_TEXT(self, self.yEntry.GetId(), self.OnMisc)

        vsizer2.Add(hsizer, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Font / Size:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.fontCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for it in [ ("Courier", pml.COURIER), ("Helvetica", pml.HELVETICA),
                    ("Times-Roman", pml.TIMES_ROMAN) ]:
            self.fontCombo.Append(it[0], it[1])

        hsizer.Add(self.fontCombo, 0, wx.LEFT, 10)
        wx.EVT_COMBOBOX(self, self.fontCombo.GetId(), self.OnMisc)

        self.sizeEntry = wx.SpinCtrl(self, -1, size = (50, -1))
        self.sizeEntry.SetRange(4, 288)
        wx.EVT_SPINCTRL(self, self.sizeEntry.GetId(), self.OnMisc)
        wx.EVT_KILL_FOCUS(self.sizeEntry, self.OnKillFocus)
        hsizer.Add(self.sizeEntry, 0, wx.LEFT, 10)

        vsizer2.Add(hsizer, 0, wx.TOP, 10)

        hsizerTop.Add(vsizer2)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Style"),
                                   wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.addCheckBox("Bold", self, vsizer2, pad)
        self.addCheckBox("Italic", self, vsizer2, pad)
        self.addCheckBox("Underlined", self, vsizer2, pad)

        bsizer.Add(vsizer2)

        hsizerTop.Add(bsizer, 0, wx.LEFT, 20)

        vsizer.Add(hsizerTop, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        self.previewBtn = gutil.createStockButton(self, "Preview")
        hsizer.Add(self.previewBtn)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, self.previewBtn.GetId(), self.OnPreview)
        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        wx.EVT_LISTBOX(self, self.stringsLb.GetId(), self.OnStringsLb)

        # list of widgets that are specific to editing the selected string
        self.widList = [ self.textEntry, self.xEntry, self.alignCombo,
                         self.yEntry, self.fontCombo, self.sizeEntry,
                         self.boldCb, self.italicCb, self.underlinedCb ]

        self.updateGui()

        self.textEntry.SetFocus()

    def addCheckBox(self, name, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        wx.EVT_CHECKBOX(self, cb.GetId(), self.OnMisc)
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, name.lower() + "Cb", cb)

    def OnOK(self, event):
        self.titles.sort()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnPreview(self, event):
        doc = pml.Document(self.cfg.paperWidth, self.cfg.paperHeight)

        self.titles.generatePages(doc)
        tmp = pdf.generate(doc)
        gutil.showTempPDF(tmp, self.cfgGl, self)

    # set given page. 'page' can be an invalid value.
    def setPage(self, page):
        # selected page index or -1
        self.pageIndex = -1

        if self.titles.pages:
            self.pageIndex = 0

            if (page >= 0) and (len(self.titles.pages) > page):
                self.pageIndex = page

        # selected string index or -1
        self.tsIndex = -1

        if self.pageIndex == -1:
            return

        if len(self.titles.pages[self.pageIndex]) > 0:
            self.tsIndex = 0

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnStringsLb(self, event = None):
        self.tsIndex = self.stringsLb.GetSelection()
        self.updateStringGui()

    def OnAddPage(self, event):
        self.titles.pages.append([])
        self.setPage(len(self.titles.pages) - 1)

        self.updateGui()

    def OnDeletePage(self, event):
        del self.titles.pages[self.pageIndex]
        self.setPage(0)

        self.updateGui()

    def OnMovePage(self, event):
        newIndex = (self.pageIndex + 1) % len(self.titles.pages)

        self.titles.pages[self.pageIndex], self.titles.pages[newIndex] = (
            self.titles.pages[newIndex], self.titles.pages[self.pageIndex])

        self.setPage(newIndex)

        self.updateGui()

    def OnNextPage(self, event):
        self.setPage((self.pageIndex + 1) % len(self.titles.pages))

        self.updateGui()

    def OnAddString(self, event):
        if self.pageIndex == -1:
            return

        if self.tsIndex != -1:
            ts = copy.deepcopy(self.titles.pages[self.pageIndex][self.tsIndex])
            ts.y += util.getTextHeight(ts.size)
        else:
            ts = titles.TitleString(["new string"], 0.0, 100.0)

        self.titles.pages[self.pageIndex].append(ts)
        self.tsIndex = len(self.titles.pages[self.pageIndex]) - 1

        self.updateGui()

    def OnDeleteString(self, event):
        if (self.pageIndex == -1) or (self.tsIndex == -1):
            return

        del self.titles.pages[self.pageIndex][self.tsIndex]
        self.tsIndex = min(self.tsIndex,
                           len(self.titles.pages[self.pageIndex]) - 1)

        self.updateGui()

    # update page/string listboxes and selection
    def updateGui(self):
        self.stringsLb.Clear()

        pgCnt = len(self.titles.pages)

        self.delPageBtn.Enable(pgCnt > 0)
        self.moveBtn.Enable(pgCnt > 1)
        self.nextBtn.Enable(pgCnt > 1)
        self.previewBtn.Enable(pgCnt > 0)

        if self.pageIndex != -1:
            page = self.titles.pages[self.pageIndex]

            self.pageLabel.SetLabel("Page: %d / %d" % (self.pageIndex + 1,
                                                       pgCnt))
            self.addBtn.Enable(True)
            self.delBtn.Enable(len(page) > 0)

            for s in page:
                self.stringsLb.Append("--".join(s.items))

            if self.tsIndex != -1:
                self.stringsLb.SetSelection(self.tsIndex)
        else:
            self.pageLabel.SetLabel("No pages.")
            self.addBtn.Disable()
            self.delBtn.Disable()

        self.updateStringGui()

        self.previewCtrl.Refresh()

    # update selected string stuff
    def updateStringGui(self):
        if self.tsIndex == -1:
            for w in self.widList:
                w.Disable()

            self.textEntry.SetValue("")
            self.xEntry.SetValue("")
            self.yEntry.SetValue("")
            self.sizeEntry.SetValue(12)
            self.boldCb.SetValue(False)
            self.italicCb.SetValue(False)
            self.underlinedCb.SetValue(False)

            return

        self.block = True

        ts = self.titles.pages[self.pageIndex][self.tsIndex]

        for w in self.widList:
            w.Enable(True)

        if ts.isCentered:
            self.xEntry.Disable()

        self.textEntry.SetValue("\n".join(ts.items))

        self.xEntry.SetValue("%.2f" % ts.x)
        self.yEntry.SetValue("%.2f" % ts.y)

        util.reverseComboSelect(self.alignCombo, ts.getAlignment())

        util.reverseComboSelect(self.fontCombo, ts.font)
        self.sizeEntry.SetValue(ts.size)

        self.boldCb.SetValue(ts.isBold)
        self.italicCb.SetValue(ts.isItalic)
        self.underlinedCb.SetValue(ts.isUnderlined)

        self.block = False

        self.previewCtrl.Refresh()

    def OnMisc(self, event = None):
        if (self.tsIndex == -1) or self.block:
            return

        ts = self.titles.pages[self.pageIndex][self.tsIndex]

        ts.items = [util.toInputStr(s) for s in
                    misc.fromGUI(self.textEntry.GetValue()).split("\n")]

        self.stringsLb.SetString(self.tsIndex, "--".join(ts.items))

        ts.x = util.str2float(self.xEntry.GetValue(), 0.0)
        ts.y = util.str2float(self.yEntry.GetValue(), 0.0)

        ts.setAlignment(self.alignCombo.GetClientData(self.alignCombo.GetSelection()))
        self.xEntry.Enable(not ts.isCentered)

        ts.size = util.getSpinValue(self.sizeEntry)
        ts.font = self.fontCombo.GetClientData(self.fontCombo.GetSelection())

        ts.isBold = self.boldCb.GetValue()
        ts.isItalic = self.italicCb.GetValue()
        ts.isUnderlined = self.underlinedCb.GetValue()

        self.previewCtrl.Refresh()


class TitlesPreview(wx.Window):
    def __init__(self, parent, ctrl, cfg):
        wx.Window.__init__(self, parent, -1)

        self.cfg = cfg
        self.ctrl = ctrl

        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        wx.EVT_PAINT(self, self.OnPaint)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wx.EmptyBitmap(size.width, size.height)

    def OnEraseBackground(self, event):
        pass

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        # widget size
        ww, wh = self.GetClientSizeTuple()

        dc.SetBrush(wx.Brush(self.GetBackgroundColour()))
        dc.SetPen(wx.Pen(self.GetBackgroundColour()))
        dc.DrawRectangle(0, 0, ww, wh)

        # aspect ratio of paper
        aspect = self.cfg.paperWidth / self.cfg.paperHeight

        # calculate which way we can best fit the paper on screen
        h = wh
        w = int(aspect * wh)

        if w > ww:
            w = ww
            h = int(ww / aspect)

        # offset of paper
        ox = (ww - w) // 2
        oy = (wh - h) // 2

        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(ox, oy, w, h)

        if self.ctrl.pageIndex != -1:
            page = self.ctrl.titles.pages[self.ctrl.pageIndex]

            for i in range(len(page)):
                ts = page[i]

                # text height in mm
                textHinMM = util.getTextHeight(ts.size)

                textH = int((textHinMM / self.cfg.paperHeight) * h)
                textH = max(1, textH)
                y = ts.y

                for line in ts.items:
                    # people may have empty lines in between non-empty
                    # lines to achieve double spaced lines; don't draw a
                    # rectangle for lines consisting of nothing but
                    # whitespace

                    if line.strip():
                        textW = int((util.getTextWidth(line, ts.getStyle(),
                            ts.size) / self.cfg.paperWidth) * w)
                        textW = max(1, textW)

                        if ts.isCentered:
                            xp = w // 2 - textW // 2
                        else:
                            xp = int((ts.x / self.cfg.paperWidth) * w)

                        if ts.isRightJustified:
                            xp -= textW

                        if i == self.ctrl.tsIndex:
                            dc.SetPen(wx.RED_PEN)
                            dc.SetBrush(wx.RED_BRUSH)
                        else:
                            dc.SetPen(wx.BLACK_PEN)
                            dc.SetBrush(wx.BLACK_BRUSH)

                        yp = int((y / self.cfg.paperHeight) * h)

                        dc.DrawRectangle(ox + xp, oy + yp, textW, textH)

                    y += textHinMM


########NEW FILE########
__FILENAME__ = trelby
# -*- coding: iso-8859-1 -*-

from error import *
import autocompletiondlg
import cfgdlg
import characterreport
import charmapdlg
import commandsdlg
import config
import dialoguechart
import finddlg
import gutil
import headersdlg
import locationreport
import locationsdlg
import misc
import myimport
import mypickle
import namesdlg
import opts
import pml
import scenereport
import scriptreport
import screenplay
import spellcheck
import spellcheckdlg
import spellcheckcfgdlg
import splash
import titlesdlg
import util
import viewmode
import watermarkdlg

import copy
import datetime
import os
import os.path
import signal
import sys
import time
import wx

from functools import partial

#keycodes
KC_CTRL_A = 1
KC_CTRL_B = 2
KC_CTRL_D = 4
KC_CTRL_E = 5
KC_CTRL_F = 6
KC_CTRL_N = 14
KC_CTRL_P = 16
KC_CTRL_V = 22

VIEWMODE_DRAFT,\
VIEWMODE_LAYOUT,\
VIEWMODE_SIDE_BY_SIDE,\
VIEWMODE_OVERVIEW_SMALL,\
VIEWMODE_OVERVIEW_LARGE,\
= range(5)

def refreshGuiConfig():
    global cfgGui

    cfgGui = config.ConfigGui(cfgGl)

def getCfgGui():
    return cfgGui

# keeps (some) global data
class GlobalData:
    def __init__(self):

        self.confFilename = misc.confPath + "/default.conf"
        self.stateFilename = misc.confPath + "/state"
        self.scDictFilename = misc.confPath + "/spell_checker_dictionary"

        # current script config path
        self.scriptSettingsPath = misc.confPath

        # global spell checker (user) dictionary
        self.scDict = spellcheck.Dict()

        # recently used files list
        self.mru = misc.MRUFiles(5)

        if opts.conf:
            self.confFilename = opts.conf

        v = self.cvars = mypickle.Vars()

        v.addInt("posX", 0, "PositionX", -20, 9999)
        v.addInt("posY", 0, "PositionY", -20, 9999)

        # linux has bigger font by default so it needs a wider window
        defaultW = 750
        if misc.isUnix:
            defaultW = 800

        v.addInt("width", defaultW, "Width", 500, 9999)

        v.addInt("height", 830, "Height", 300, 9999)
        v.addInt("viewMode", VIEWMODE_DRAFT, "ViewMode", VIEWMODE_DRAFT,
                 VIEWMODE_OVERVIEW_LARGE)

        v.addList("files", [], "Files",
                  mypickle.StrUnicodeVar("", u"", ""))

        v.makeDicts()
        v.setDefaults(self)

        self.height = min(self.height,
            wx.SystemSettings_GetMetric(wx.SYS_SCREEN_Y) - 50)

        self.vmDraft = viewmode.ViewModeDraft()
        self.vmLayout = viewmode.ViewModeLayout()
        self.vmSideBySide = viewmode.ViewModeSideBySide()
        self.vmOverviewSmall = viewmode.ViewModeOverview(1)
        self.vmOverviewLarge = viewmode.ViewModeOverview(2)

        self.setViewMode(self.viewMode)

        self.makeConfDir()

    def makeConfDir(self):
        makeDir = not util.fileExists(misc.confPath)

        if makeDir:
            try:
                os.mkdir(misc.toPath(misc.confPath), 0755)
            except OSError, (errno, strerror):
                wx.MessageBox("Error creating configuration directory\n"
                              "'%s': %s" % (misc.confPath, strerror),
                              "Error", wx.OK, None)

    # set viewmode, the parameter is one of the VIEWMODE_ defines.
    def setViewMode(self, viewMode):
        self.viewMode = viewMode

        if viewMode == VIEWMODE_DRAFT:
            self.vm = self.vmDraft
        elif viewMode == VIEWMODE_LAYOUT:
            self.vm = self.vmLayout
        elif viewMode == VIEWMODE_SIDE_BY_SIDE:
            self.vm = self.vmSideBySide
        elif viewMode == VIEWMODE_OVERVIEW_SMALL:
            self.vm = self.vmOverviewSmall
        else:
            self.vm = self.vmOverviewLarge

    # load from string 's'. does not throw any exceptions and silently
    # ignores any errors.
    def load(self, s):
        self.cvars.load(self.cvars.makeVals(s), "", self)
        self.mru.items = self.files

    # save to a string and return that.
    def save(self):
        self.files = self.mru.items

        return self.cvars.save("", self)

    # save global spell checker dictionary to disk
    def saveScDict(self):
        util.writeToFile(self.scDictFilename, self.scDict.save(), mainFrame)

class MyPanel(wx.Panel):

    def __init__(self, parent, id):
        wx.Panel.__init__(
            self, parent, id,
            # wxMSW/Windows does not seem to support
            # wx.NO_BORDER, which sucks
            style = wx.WANTS_CHARS | wx.NO_BORDER)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.scrollBar = wx.ScrollBar(self, -1, style = wx.SB_VERTICAL)
        self.ctrl = MyCtrl(self, -1)

        hsizer.Add(self.ctrl, 1, wx.EXPAND)
        hsizer.Add(self.scrollBar, 0, wx.EXPAND)

        wx.EVT_COMMAND_SCROLL(self, self.scrollBar.GetId(),
                              self.ctrl.OnScroll)

        wx.EVT_SET_FOCUS(self.scrollBar, self.OnScrollbarFocus)

        self.SetSizer(hsizer)

    # we never want the scrollbar to get the keyboard focus, pass it on to
    # the main widget
    def OnScrollbarFocus(self, event):
        self.ctrl.SetFocus()

class MyCtrl(wx.Control):

    def __init__(self, parent, id):
        style = wx.WANTS_CHARS | wx.FULL_REPAINT_ON_RESIZE | wx.NO_BORDER
        wx.Control.__init__(self, parent, id, style = style)

        self.panel = parent

        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_LEFT_UP(self, self.OnLeftUp)
        wx.EVT_LEFT_DCLICK(self, self.OnLeftDown)
        wx.EVT_RIGHT_DOWN(self, self.OnRightDown)
        wx.EVT_MOTION(self, self.OnMotion)
        wx.EVT_MOUSEWHEEL(self, self.OnMouseWheel)
        wx.EVT_CHAR(self, self.OnKeyChar)

        self.createEmptySp()
        self.updateScreen(redraw = False)

    def OnChangeType(self, event):
        cs = screenplay.CommandState()

        lt = idToLTMap[event.GetId()]

        self.sp.convertTypeTo(lt, True)
        self.sp.cmdPost(cs)

        if cs.needsVisifying:
            self.makeLineVisible(self.sp.line)

        self.updateScreen()

    def clearVars(self):
        self.mouseSelectActive = False

        # find dialog stored settings
        self.findDlgFindText = ""
        self.findDlgReplaceText = ""
        self.findDlgMatchWholeWord= False
        self.findDlgMatchCase = False
        self.findDlgDirUp = False
        self.findDlgUseExtra = False
        self.findDlgElements = None

    def createEmptySp(self):
        self.clearVars()
        self.sp = screenplay.Screenplay(cfgGl)
        self.sp.titles.addDefaults()
        self.sp.headers.addDefaults()
        self.setFile(None)
        self.refreshCache()

    # update stuff that depends on configuration / view mode etc.
    def refreshCache(self):
        self.chX = util.getTextWidth(" ", pml.COURIER, self.sp.cfg.fontSize)
        self.chY = util.getTextHeight(self.sp.cfg.fontSize)

        self.pageW = gd.vm.getPageWidth(self)

        # conversion factor from mm to pixels
        self.mm2p = self.pageW / self.sp.cfg.paperWidth

        # page width and height on screen, in pixels
        self.pageW = int(self.pageW)
        self.pageH = int(self.mm2p * self.sp.cfg.paperHeight)

    def getCfgGui(self):
        return cfgGui

    def loadFile(self, fileName):
        s = util.loadFile(fileName, mainFrame)
        if s == None:
            return

        try:
            (sp, msg) = screenplay.Screenplay.load(s, cfgGl)
        except TrelbyError, e:
            wx.MessageBox("Error loading file:\n\n%s" % e, "Error",
                          wx.OK, mainFrame)

            return

        if msg:
            misc.showText(mainFrame, msg, "Warning")

        self.clearVars()
        self.sp = sp
        self.setFile(fileName)
        self.refreshCache()

        # saved cursor position might be anywhere, so we can't just
        # display the first page
        self.makeLineVisible(self.sp.line)

    # save script to given filename. returns True on success.
    def saveFile(self, fileName):
        fileName = util.ensureEndsIn(fileName, ".trelby")

        if util.writeToFile(fileName, self.sp.save(), mainFrame):
            self.setFile(fileName)
            self.sp.markChanged(False)
            gd.mru.add(fileName)

            return True
        else:
            return False

    def importFile(self, fileName):
        if fileName.endswith("fdx"):
            lines = myimport.importFDX(fileName, mainFrame)
        elif fileName.endswith("celtx"):
            lines = myimport.importCeltx(fileName, mainFrame)
        elif fileName.endswith("astx"):
            lines = myimport.importAstx(fileName, mainFrame)
        elif fileName.endswith("fountain"):
            lines = myimport.importFountain(fileName, mainFrame)
        elif fileName.endswith("fadein"):
            lines = myimport.importFadein(fileName, mainFrame)
        else:
            lines = myimport.importTextFile(fileName, mainFrame)

        if not lines:
            return

        self.createEmptySp()

        self.sp.lines = lines
        self.sp.reformatAll()
        self.sp.paginate()
        self.sp.markChanged(True)

    # generate exportable text from given screenplay, or None.
    def getExportText(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include page markers"))

        dlg = misc.CheckBoxDlg(mainFrame, "Output options", inf,
                               "Options:", False)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()

            return None

        return sp.generateText(inf[0].selected)

    def getExportHtml(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include Notes"))

        dlg = misc.CheckBoxDlg(mainFrame, "Output options", inf,
                               "Options:", False)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()

            return None

        return sp.generateHtml(inf[0].selected)

    def setFile(self, fileName):
        self.fileName = fileName
        if fileName:
            self.setDisplayName(os.path.basename(fileName))
        else:
            self.setDisplayName(u"untitled")

        self.setTabText()
        mainFrame.setTitle(self.fileNameDisplay)

    def setDisplayName(self, name):
        i = 1
        while 1:
            if i == 1:
                tmp = name
            else:
                tmp = name + "-%d" % i

            matched = False

            for c in mainFrame.getCtrls():
                if c == self:
                    continue

                if c.fileNameDisplay == tmp:
                    matched = True

                    break

            if not matched:
                break

            i += 1

        self.fileNameDisplay = tmp

    def setTabText(self):
        mainFrame.setTabText(self.panel, self.fileNameDisplay)

    # texts = gd.vm.getScreen(self, False)[0], or None, in which case it's
    # called in this function.
    def isLineVisible(self, line, texts = None):
        if texts == None:
            texts = gd.vm.getScreen(self, False)[0]

        # paranoia never hurts
        if len(texts) == 0:
            return False

        return (line >= texts[0].line) and (line <= texts[-1].line)

    def makeLineVisible(self, line, direction = config.SCROLL_CENTER):
        texts = gd.vm.getScreen(self, False)[0]

        if self.isLineVisible(line, texts):
            return

        gd.vm.makeLineVisible(self, line, texts, direction)

    def adjustScrollBar(self):
        height = self.GetClientSize().height

        # rough approximation of how many lines fit onto the screen.
        # accuracy is not that important for this, so we don't even care
        # about draft / layout mode differences.
        approx = int(((height / self.mm2p) / self.chY) / 1.3)

        self.panel.scrollBar.SetScrollbar(self.sp.getTopLine(), approx,
            len(self.sp.lines) + approx - 1, approx)

    def clearAutoComp(self):
        if self.sp.clearAutoComp():
            self.Refresh(False)

    # returns true if there are no contents at all and we're not
    # attached to any file
    def isUntouched(self):
        if self.fileName or (len(self.sp.lines) > 1) or \
           (len(self.sp.lines[0].text) > 0):
            return False
        else:
            return True

    def updateScreen(self, redraw = True, setCommon = True):
        self.adjustScrollBar()

        if setCommon:
            self.updateCommon()

        if redraw:
            self.Refresh(False)

    # update GUI elements shared by all scripts, like statusbar etc
    def updateCommon(self):
        cur = cfgGl.getType(self.sp.lines[self.sp.line].lt)

        if self.sp.tabMakesNew():
            tabNext = "%s" % cfgGl.getType(cur.newTypeTab).ti.name
        else:
            tabNext = "%s" % cfgGl.getType(cur.nextTypeTab).ti.name

        enterNext = cfgGl.getType(cur.newTypeEnter).ti.name

        page = self.sp.line2page(self.sp.line)
        pageCnt = self.sp.line2page(len(self.sp.lines) - 1)

        mainFrame.statusCtrl.SetValues(page, pageCnt, cur.ti.name, tabNext, enterNext)

        canUndo = self.sp.canUndo()
        canRedo = self.sp.canRedo()

        mainFrame.menuBar.Enable(ID_EDIT_UNDO, canUndo)
        mainFrame.menuBar.Enable(ID_EDIT_REDO, canRedo)

        mainFrame.toolBar.EnableTool(ID_EDIT_UNDO, canUndo)
        mainFrame.toolBar.EnableTool(ID_EDIT_REDO, canRedo)

    # apply per-script config
    def applyCfg(self, newCfg):
        self.sp.applyCfg(newCfg)

        self.refreshCache()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    # apply global config
    def applyGlobalCfg(self, newCfgGl, writeCfg = True):
        global cfgGl

        oldCfgGl = cfgGl

        cfgGl = copy.deepcopy(newCfgGl)

        # if user has ventured from the old default directory, keep it as
        # the current one, otherwise set the new default as current.
        if misc.scriptDir == oldCfgGl.scriptDir:
            misc.scriptDir = cfgGl.scriptDir

        cfgGl.recalc()
        refreshGuiConfig()
        mainFrame.updateKbdCommands()

        for c in mainFrame.getCtrls():
            c.sp.cfgGl = cfgGl
            c.refreshCache()
            c.makeLineVisible(c.sp.line)
            c.adjustScrollBar()

        self.updateScreen()

        # in case tab colors have been changed
        mainFrame.tabCtrl.Refresh(False)
        mainFrame.statusCtrl.Refresh(False)
        mainFrame.noFSBtn.Refresh(False)
        mainFrame.toolBar.SetBackgroundColour(cfgGui.tabBarBgColor)

        if writeCfg:
            util.writeToFile(gd.confFilename, cfgGl.save(), mainFrame)

        mainFrame.checkFonts()

    def applyHeaders(self, newHeaders):
        self.sp.headers = newHeaders
        self.sp.markChanged()
        self.OnPaginate()

    # return an exportable, paginated Screenplay object, or None if for
    # some reason that's not possible / wanted. 'action' is the name of
    # the action, e.g. "export" or "print", that'll be done to the script,
    # and is used in dialogue with the user if needed.
    def getExportable(self, action):
        if cfgGl.checkOnExport:
            line = self.sp.findError(0)[0]

            if line != -1:
                if wx.MessageBox(
                    "The script seems to contain errors.\n"
                    "Are you sure you want to %s it?" % action, "Confirm",
                     wx.YES_NO | wx.NO_DEFAULT, mainFrame) == wx.NO:

                    return None

        sp = self.sp
        if sp.cfg.pdfRemoveNotes:
            sp = copy.deepcopy(self.sp)
            sp.removeElementTypes({screenplay.NOTE : None}, False)

        sp.paginate()

        return sp

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        if misc.doDblBuf:
            size = self.GetClientSize()

            sb = wx.EmptyBitmap(size.width, size.height)
            old = getattr(self.__class__, "screenBuf", None)

            if (old == None) or (old.GetDepth() != sb.GetDepth()) or \
               (old.GetHeight() != sb.GetHeight()) or \
               (old.GetWidth() != sb.GetWidth()):
                self.__class__.screenBuf = sb

        self.makeLineVisible(self.sp.line)

    def OnLeftDown(self, event, mark = False):
        if not self.mouseSelectActive:
            self.sp.clearMark()
            self.updateScreen()

        pos = event.GetPosition()
        line, col = gd.vm.pos2linecol(self, pos.x, pos.y)

        self.mouseSelectActive = True

        if line is not None:
            self.sp.gotoPos(line, col, mark)
            self.updateScreen()

    def OnLeftUp(self, event):
        self.mouseSelectActive = False

        # to avoid phantom selections (Windows sends some strange events
        # sometimes), check if anything worthwhile is actually selected.
        cd = self.sp.getSelectedAsCD(False)

        if not cd or ((len(cd.lines) == 1) and (len(cd.lines[0].text) < 2)):
            self.sp.clearMark()

    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event, mark = True)

    def OnRightDown(self, event):
        # No popup in the overview modes.
        if gd.viewMode in (VIEWMODE_OVERVIEW_SMALL, VIEWMODE_OVERVIEW_LARGE):
            return

        pos = event.GetPosition()
        line, col = gd.vm.pos2linecol(self, pos.x, pos.y)

        if self.sp.mark:
            m = mainFrame.rightClickMenuWithCut
        else:
            m = mainFrame.rightClickMenu

            if line is not None and (line != self.sp.line):
                self.sp.gotoPos(line, col, False)
                self.updateScreen()

        self.PopupMenu(m)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            delta = -cfgGl.mouseWheelLines
        else:
            delta = cfgGl.mouseWheelLines

        self.sp.setTopLine(self.sp.getTopLine() + delta)
        self.updateScreen()

    def OnScroll(self, event):
        pos = self.panel.scrollBar.GetThumbPosition()
        self.sp.setTopLine(pos)
        self.sp.clearAutoComp()
        self.updateScreen()

    def OnPaginate(self):
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnAutoCompletionDlg(self):
        dlg = autocompletiondlg.AutoCompletionDlg(mainFrame,
            copy.deepcopy(self.sp.autoCompletion))

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.autoCompletion = dlg.autoCompletion
            self.sp.markChanged()

        dlg.Destroy()

    def OnTitlesDlg(self):
        dlg = titlesdlg.TitlesDlg(mainFrame, copy.deepcopy(self.sp.titles),
                                  self.sp.cfg, cfgGl)

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.titles = dlg.titles
            self.sp.markChanged()

        dlg.Destroy()

    def OnHeadersDlg(self):
        dlg = headersdlg.HeadersDlg(mainFrame,
            copy.deepcopy(self.sp.headers), self.sp.cfg, cfgGl,
                                    self.applyHeaders)

        if dlg.ShowModal() == wx.ID_OK:
            self.applyHeaders(dlg.headers)

        dlg.Destroy()

    def OnLocationsDlg(self):
        dlg = locationsdlg.LocationsDlg(mainFrame, copy.deepcopy(self.sp))

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.locations = dlg.sp.locations
            self.sp.markChanged()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self):
        dlg = spellcheckcfgdlg.SCDictDlg(mainFrame,
            copy.deepcopy(self.sp.scDict), False)

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.scDict = dlg.scDict
            self.sp.markChanged()

        dlg.Destroy()

    def OnWatermark(self):
        dlg = watermarkdlg.WatermarkDlg(
            mainFrame, self.sp, self.fileNameDisplay.replace(".trelby", ""))
        dlg.ShowModal()
        dlg.Destroy()

    def OnReportDialogueChart(self):
        self.sp.paginate()
        dialoguechart.genDialogueChart(mainFrame, self.sp)

    def OnReportCharacter(self):
        self.sp.paginate()
        characterreport.genCharacterReport(mainFrame, self.sp)

    def OnReportLocation(self):
        self.sp.paginate()
        locationreport.genLocationReport(mainFrame, self.sp)

    def OnReportScene(self):
        self.sp.paginate()
        scenereport.genSceneReport(mainFrame, self.sp)

    def OnReportScript(self):
        self.sp.paginate()
        scriptreport.genScriptReport(mainFrame, self.sp)

    def OnCompareScripts(self):
        if mainFrame.tabCtrl.getPageCount() < 2:
            wx.MessageBox("You need at least two scripts open to"
                          " compare them.", "Error", wx.OK, mainFrame)

            return

        items = []
        for c in mainFrame.getCtrls():
            items.append(c.fileNameDisplay)

        dlg = misc.ScriptChooserDlg(mainFrame, items)

        sel1 = -1
        sel2 = -1
        if dlg.ShowModal() == wx.ID_OK:
            sel1 = dlg.sel1
            sel2 = dlg.sel2
            force = dlg.forceSameCfg

        dlg.Destroy()

        if sel1 == -1:
            return

        if sel1 == sel2:
            wx.MessageBox("You can't compare a script to itself.", "Error",
                          wx.OK, mainFrame)

            return

        c1 = mainFrame.tabCtrl.getPage(sel1).ctrl
        c2 = mainFrame.tabCtrl.getPage(sel2).ctrl

        sp1 = c1.getExportable("compare")
        sp2 = c2.getExportable("compare")

        if not sp1 or not sp2:
            return

        if force:
            sp2 = copy.deepcopy(sp2)
            sp2.cfg = copy.deepcopy(sp1.cfg)
            sp2.reformatAll()
            sp2.paginate()

        s = sp1.compareScripts(sp2)

        if s:
            gutil.showTempPDF(s, cfgGl, mainFrame)
        else:
            wx.MessageBox("The scripts are identical.", "Results", wx.OK,
                          mainFrame)

    def canBeClosed(self):
        if self.sp.isModified():
            if wx.MessageBox("The script has been modified. Are you sure\n"
                             "you want to discard the changes?", "Confirm",
                             wx.YES_NO | wx.NO_DEFAULT, mainFrame) == wx.NO:
                return False

        return True

    # page up (dir == -1) or page down (dir == 1) was pressed, handle it.
    # cs = CommandState.
    def pageCmd(self, cs, dir):
        if self.sp.acItems:
            cs.doAutoComp = cs.AC_KEEP
            self.sp.pageScrollAutoComp(dir)

            return

        texts, dpages = gd.vm.getScreen(self, False)

        # if user has scrolled with scrollbar so that cursor isn't seen,
        # just make cursor visible and don't move
        if not self.isLineVisible(self.sp.line, texts):
            gd.vm.makeLineVisible(self, self.sp.line, texts)
            cs.needsVisifying = False

            return

        self.sp.maybeMark(cs.mark)
        gd.vm.pageCmd(self, cs, dir, texts, dpages)

    def OnRevertScript(self):
        if self.fileName:
            if not self.canBeClosed():
                return

            self.loadFile(self.fileName)
            self.updateScreen()

    def OnUndo(self):
        self.sp.cmd("undo")
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnRedo(self):
        self.sp.cmd("redo")
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    # returns True if something was deleted
    def OnCut(self, doUpdate = True, doDelete = True, copyToClip = True):
        marked = self.sp.getMarkedLines()

        if not marked:
            return False

        cd = self.sp.getSelectedAsCD(doDelete)

        if copyToClip:
            mainFrame.clipboard = cd

        if doUpdate:
            self.makeLineVisible(self.sp.line)
            self.updateScreen()

        return doDelete

    def OnCopy(self):
        self.OnCut(doDelete = False)

    def OnCopySystem(self, formatted = False):
        cd = self.sp.getSelectedAsCD(False)

        if not cd:
            return

        tmpSp = screenplay.Screenplay(cfgGl)
        tmpSp.lines = cd.lines

        if formatted:
            # have to call paginate, otherwise generateText will not
            # process all the text
            tmpSp.paginate()
            s = tmpSp.generateText(False)
        else:
            s = util.String()

            for ln in tmpSp.lines:
                txt = ln.text

                if tmpSp.cfg.getType(ln.lt).export.isCaps:
                    txt = util.upper(txt)

                s += txt + config.lb2str(ln.lb)

            s = str(s).replace("\n", os.linesep)

        if wx.TheClipboard.Open():
            wx.TheClipboard.UsePrimarySelection(False)

            wx.TheClipboard.Clear()
            wx.TheClipboard.AddData(wx.TextDataObject(s))
            wx.TheClipboard.Flush()

            wx.TheClipboard.Close()

    def OnPaste(self, clines = None):
        if not clines:
            cd = mainFrame.clipboard

            if not cd:
                return

            clines = cd.lines

        self.sp.paste(clines)

        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnPasteSystemCb(self):
        s = ""

        if wx.TheClipboard.Open():
            wx.TheClipboard.UsePrimarySelection(False)

            df = wx.DataFormat(wx.DF_TEXT)

            if wx.TheClipboard.IsSupported(df):
                data = wx.TextDataObject()
                wx.TheClipboard.GetData(data)
                s = util.cleanInput(data.GetText())

            wx.TheClipboard.Close()

        s = util.fixNL(s)

        if len(s) == 0:
            return

        inLines = s.split("\n")

        # shouldn't be possible, but...
        if len(inLines) == 0:
            return

        lines = []

        for s in inLines:
            if s:
                lines.append(screenplay.Line(screenplay.LB_LAST,
                                             screenplay.ACTION, s))

        self.OnPaste(lines)

    def OnSelectScene(self):
        self.sp.cmd("selectScene")

        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSelectAll(self):
        self.sp.cmd("selectAll")

        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnGotoScene(self):
        self.sp.paginate()
        self.clearAutoComp()

        scenes = self.sp.getSceneLocations()

        def validateFunc(s):
            if s in [x[0] for x in scenes]:
                return ""
            else:
                return "Invalid scene number."

        dlg = misc.TextInputDlg(mainFrame, "Enter scene number (%s - %s):" %\
            (scenes[0][0], scenes[-1][0]), "Goto scene", validateFunc)

        if dlg.ShowModal() == wx.ID_OK:
            for it in scenes:
                if it[0] == dlg.input:
                    self.sp.line = it[1]
                    self.sp.column = 0

                    break

        # we need to refresh the screen in all cases because pagination
        # might have changed
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnGotoPage(self):
        self.sp.paginate()
        self.clearAutoComp()

        pages = self.sp.getPageNumbers()

        def validateFunc(s):
            if s in pages:
                return ""
            else:
                return "Invalid page number."

        dlg = misc.TextInputDlg(mainFrame, "Enter page number (%s - %s):" %\
            (pages[0], pages[-1]), "Goto page", validateFunc)

        if dlg.ShowModal() == wx.ID_OK:
            page = int(dlg.input)
            self.sp.line = self.sp.page2lines(page)[0]
            self.sp.column = 0

        # we need to refresh the screen in all cases because pagination
        # might have changed
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnInsertNbsp(self):
        self.OnKeyChar(util.MyKeyEvent(160))

    def OnFindNextError(self):
        self.clearAutoComp()

        line, msg = self.sp.findError(self.sp.line)

        if line != -1:
            self.sp.line = line
            self.sp.column = 0

            self.makeLineVisible(self.sp.line)
            self.updateScreen()

        else:
            msg = "No errors found."

        wx.MessageBox(msg, "Results", wx.OK, mainFrame)

    def OnFind(self):
        self.sp.clearMark()
        self.clearAutoComp()
        self.updateScreen()

        dlg = finddlg.FindDlg(mainFrame, self)
        dlg.ShowModal()
        dlg.saveState()
        dlg.Destroy()

        self.sp.clearMark()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSpellCheckerDlg(self):
        self.sp.clearMark()
        self.clearAutoComp()

        wasAtStart = self.sp.line == 0

        wx.BeginBusyCursor()

        if not spellcheck.loadDict(mainFrame):
            wx.EndBusyCursor()

            return

        sc = spellcheck.SpellChecker(self.sp, gd.scDict)
        found = sc.findNext()

        wx.EndBusyCursor()

        if not found:
            s = ""

            if not wasAtStart:
                s = "\n\n(Starting position was not at\n"\
                    "the beginning of the script.)"
            wx.MessageBox("Spell checker found no errors." + s, "Results",
                          wx.OK, mainFrame)

            return

        dlg = spellcheckdlg.SpellCheckDlg(mainFrame, self, sc, gd.scDict)
        dlg.ShowModal()

        if dlg.changedGlobalDict:
            gd.saveScDict()

        dlg.Destroy()

        self.sp.clearMark()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnDeleteElements(self):
        # even though Screenplay.removeElementTypes does this as well, do
        # it here so that screen is cleared from the auto-comp box before
        # we open the dialog
        self.clearAutoComp()

        types = []
        for t in config.getTIs():
            types.append(misc.CheckBoxItem(t.name, False, t.lt))

        dlg = misc.CheckBoxDlg(mainFrame, "Delete elements", types,
                               "Element types to delete:", True)

        ok = False
        if dlg.ShowModal() == wx.ID_OK:
            ok = True

            tdict = misc.CheckBoxItem.getClientData(types)

        dlg.Destroy()

        if not ok or (len(tdict) == 0):
            return

        self.sp.removeElementTypes(tdict, True)
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSave(self):
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveScriptAs()

    def OnSaveScriptAs(self):
        if self.fileName:
            dDir = os.path.dirname(self.fileName)
            dFile = os.path.basename(self.fileName)
        else:
            dDir = misc.scriptDir
            dFile = u""

        dlg = wx.FileDialog(mainFrame, "Filename to save as",
            defaultDir = dDir,
            defaultFile = dFile,
            wildcard = "Trelby files (*.trelby)|*.trelby|All files|*",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnExportScript(self):
        sp = self.getExportable("export")
        if not sp:
            return

        dlg = wx.FileDialog(mainFrame, "Filename to export as",
            misc.scriptDir,
            wildcard = "PDF|*.pdf|"
                       "RTF|*.rtf|"
                       "Final Draft XML|*.fdx|"
                       "HTML|*.html|"
                       "Fountain|*.fountain|"
                       "Formatted text|*.txt",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()

            choice = dlg.GetFilterIndex()
            if choice == 0:
                data = sp.generatePDF(True)
                suffix = ".pdf"
            elif choice == 1:
                data = sp.generateRTF()
                suffix = ".rtf"
            elif choice == 2:
                data = sp.generateFDX()
                suffix = ".fdx"
            elif choice == 3:
                data = self.getExportHtml(sp)
                suffix = ".html"
            elif choice == 4:
                data = sp.generateFountain()
                suffix = ".fountain"
            else:
                data = self.getExportText(sp)
                suffix = ".txt"

            fileName = util.ensureEndsIn(dlg.GetPath(), suffix)

            if data:
                util.writeToFile(fileName, data, mainFrame)

        dlg.Destroy()

    def OnPrint(self):
        sp = self.getExportable("print")
        if not sp:
            return

        s = sp.generatePDF(False)
        gutil.showTempPDF(s, cfgGl, mainFrame)

    def OnSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(cfgGl),
                            self.applyGlobalCfg, True)

        if dlg.ShowModal() == wx.ID_OK:
            self.applyGlobalCfg(dlg.cfg)

        dlg.Destroy()

    def OnScriptSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(self.sp.cfg),
                            self.applyCfg, False)

        if dlg.ShowModal() == wx.ID_OK:
            self.applyCfg(dlg.cfg)

        dlg.Destroy()

    def cmdAbort(self, cs):
        self.sp.abortCmd(cs)

    def cmdChangeToAction(self, cs):
        self.sp.toActionCmd(cs)

    def cmdChangeToCharacter(self, cs):
        self.sp.toCharacterCmd(cs)

    def cmdChangeToDialogue(self, cs):
        self.sp.toDialogueCmd(cs)

    def cmdChangeToNote(self, cs):
        self.sp.toNoteCmd(cs)

    def cmdChangeToParenthetical(self, cs):
        self.sp.toParenCmd(cs)

    def cmdChangeToScene(self, cs):
        self.sp.toSceneCmd(cs)

    def cmdChangeToShot(self, cs):
        self.sp.toShotCmd(cs)

    def cmdChangeToActBreak(self,cs):
        self.sp.toActBreakCmd(cs)

    def cmdChangeToTransition(self, cs):
        self.sp.toTransitionCmd(cs)

    def cmdDelete(self, cs):
        if not self.sp.mark:
            self.sp.deleteForwardCmd(cs)
        else:
            self.OnCut(doUpdate = False, copyToClip = False)

    def cmdDeleteBackward(self, cs):
        if not self.sp.mark:
            self.sp.deleteBackwardCmd(cs)
        else:
            self.OnCut(doUpdate = False, copyToClip = False)

    def cmdForcedLineBreak(self, cs):
        self.sp.insertForcedLineBreakCmd(cs)

    def cmdMoveDown(self, cs):
        self.sp.moveDownCmd(cs)

    def cmdMoveEndOfLine(self, cs):
        self.sp.moveLineEndCmd(cs)

    def cmdMoveEndOfScript(self, cs):
        self.sp.moveEndCmd(cs)

    def cmdMoveLeft(self, cs):
        self.sp.moveLeftCmd(cs)

    def cmdMovePageDown(self, cs):
        self.pageCmd(cs, 1)

    def cmdMovePageUp(self, cs):
        self.pageCmd(cs, -1)

    def cmdMoveRight(self, cs):
        self.sp.moveRightCmd(cs)

    def cmdMoveSceneDown(self, cs):
        self.sp.moveSceneDownCmd(cs)

    def cmdMoveSceneUp(self, cs):
        self.sp.moveSceneUpCmd(cs)

    def cmdMoveStartOfLine(self, cs):
        self.sp.moveLineStartCmd(cs)

    def cmdMoveStartOfScript(self, cs):
        self.sp.moveStartCmd(cs)

    def cmdMoveUp(self, cs):
        self.sp.moveUpCmd(cs)

    def cmdNewElement(self, cs):
        self.sp.splitElementCmd(cs)

    def cmdSetMark(self, cs):
        self.sp.setMarkCmd(cs)

    def cmdTab(self, cs):
        self.sp.tabCmd(cs)

    def cmdTabPrev(self, cs):
        self.sp.toPrevTypeTabCmd(cs)

    def cmdSpeedTest(self, cs):
        import undo
        self.speedTestUndo = []

        def testUndoFullCopy():
            u = undo.FullCopy(self.sp)
            u.setAfter(self.sp)
            self.speedTestUndo.append(u)

        def testReformatAll():
            self.sp.reformatAll()

        def testPaginate():
            self.sp.paginate()

        def testUpdateScreen():
            self.updateScreen()
            self.Update()

        def testAddRemoveChar():
            self.OnKeyChar(util.MyKeyEvent(ord("a")))
            self.OnKeyChar(util.MyKeyEvent(wx.WXK_BACK))

        def testDeepcopy():
            copy.deepcopy(self.sp)

        # contains (name, func) tuples
        tests = []

        for name, var in locals().iteritems():
            if callable(var):
                tests.append((name, var))

        tests.sort()
        count = 100

        print "-" * 20

        for name, func in tests:
            t = time.time()

            for i in xrange(count):
                func()

            t = time.time() - t

            print "%.5f seconds per %s" % (t / count, name)

        print "-" * 20

        # it's annoying having the program ask if you want to save after
        # running these tests, so pretend the script hasn't changed
        self.sp.markChanged(False)

    def cmdTest(self, cs):
        pass

    def OnKeyChar(self, ev):
        kc = ev.GetKeyCode()

        #print "kc: %d, ctrl/alt/shift: %d, %d, %d" %\
        #      (kc, ev.ControlDown(), ev.AltDown(), ev.ShiftDown())

        cs = screenplay.CommandState()
        cs.mark = bool(ev.ShiftDown())
        scrollDirection = config.SCROLL_CENTER

        if not ev.ControlDown() and not ev.AltDown() and \
               util.isValidInputChar(kc):
            # WX2.6-FIXME: we should probably use GetUnicodeKey() (dunno
            # how to get around the isValidInputChar test in the preceding
            # line, need to test what GetUnicodeKey() returns on
            # non-input-character events)

            addChar = True

            # If there's something selected, either remove it, or clear selection.
            if self.sp.mark and cfgGl.overwriteSelectionOnInsert:
                if not self.OnCut(doUpdate = False, copyToClip = False):
                    self.sp.clearMark()
                    addChar = False

            if addChar:
                cs.char = chr(kc)

                if opts.isTest and (cs.char == "�"):
                    self.loadFile(u"sample.trelby")
                elif opts.isTest and (cs.char == "�"):
                    self.cmdTest(cs)
                elif opts.isTest and (cs.char == "�"):
                    self.cmdSpeedTest(cs)
                else:
                    self.sp.addCharCmd(cs)

        else:
            cmd = mainFrame.kbdCommands.get(util.Key(kc,
                ev.ControlDown(), ev.AltDown(), ev.ShiftDown()).toInt())

            if cmd:
                scrollDirection = cmd.scrollDirection
                if cmd.isMenu:
                    getattr(mainFrame, "On" + cmd.name)()
                    return
                else:
                    getattr(self, "cmd" + cmd.name)(cs)
            else:
                ev.Skip()
                return

        self.sp.cmdPost(cs)

        if cfgGl.paginateInterval > 0:
            now = time.time()

            if (now - self.sp.lastPaginated) >= cfgGl.paginateInterval:
                self.sp.paginate()

                cs.needsVisifying = True

        if cs.needsVisifying:
            self.makeLineVisible(self.sp.line, scrollDirection)

        self.updateScreen()

    def OnPaint(self, event):
        #ldkjfldsj = util.TimerDev("paint")

        ls = self.sp.lines

        if misc.doDblBuf:
            dc = wx.BufferedPaintDC(self, self.screenBuf)
        else:
            dc = wx.PaintDC(self)

        size = self.GetClientSize()
        marked = self.sp.getMarkedLines()
        lineh = gd.vm.getLineHeight(self)
        posX = -1
        cursorY = -1

        # auto-comp FontInfo
        acFi = None

        # key = font, value = ([text, ...], [(x, y), ...], [wx.Colour, ...])
        texts = {}

        # lists of underline-lines to draw, one for normal text and one
        # for header texts. list objects are (x, y, width) tuples.
        ulines = []
        ulinesHdr = []

        strings, dpages = gd.vm.getScreen(self, True, True)

        dc.SetBrush(cfgGui.workspaceBrush)
        dc.SetPen(cfgGui.workspacePen)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawLine(0,0,0,size.height)

        if not dpages:
            # draft mode; draw an infinite page
            lx = util.clamp((size.width - self.pageW) // 2, 0)
            rx = lx + self.pageW

            dc.SetBrush(cfgGui.textBgBrush)
            dc.SetPen(cfgGui.textBgPen)
            dc.DrawRectangle(lx, 5, self.pageW, size.height - 5)

            dc.SetPen(cfgGui.pageBorderPen)
            dc.DrawLine(lx, 5, lx, size.height)
            dc.DrawLine(rx, 5, rx, size.height)

        else:
            dc.SetBrush(cfgGui.textBgBrush)
            dc.SetPen(cfgGui.pageBorderPen)
            for dp in dpages:
                dc.DrawRectangle(dp.x1, dp.y1, dp.x2 - dp.x1 + 1,
                                 dp.y2 - dp.y1 + 1)

            dc.SetPen(cfgGui.pageShadowPen)
            for dp in dpages:
                # + 2 because DrawLine doesn't draw to end point but stops
                # one pixel short...
                dc.DrawLine(dp.x1 + 1, dp.y2 + 1, dp.x2 + 1, dp.y2 + 1)
                dc.DrawLine(dp.x2 + 1, dp.y1 + 1, dp.x2 + 1, dp.y2 + 2)

        for t in strings:
            i = t.line
            y = t.y
            fi = t.fi
            fx = fi.fx

            if i != -1:
                l = ls[i]

                if l.lt == screenplay.NOTE:
                    dc.SetPen(cfgGui.notePen)
                    dc.SetBrush(cfgGui.noteBrush)

                    nx = t.x - 5
                    nw = self.sp.cfg.getType(l.lt).width * fx + 10

                    dc.DrawRectangle(nx, y, nw, lineh)

                    dc.SetPen(cfgGui.textPen)
                    util.drawLine(dc, nx - 1, y, 0, lineh)
                    util.drawLine(dc, nx + nw, y, 0, lineh)

                    if self.sp.isFirstLineOfElem(i):
                        util.drawLine(dc, nx - 1, y - 1, nw + 2, 0)

                    if self.sp.isLastLineOfElem(i):
                        util.drawLine(dc, nx - 1, y + lineh,
                                      nw + 2, 0)

                if marked and self.sp.isLineMarked(i, marked):
                    c1, c2 = self.sp.getMarkedColumns(i, marked)

                    dc.SetPen(cfgGui.selectedPen)
                    dc.SetBrush(cfgGui.selectedBrush)

                    dc.DrawRectangle(t.x + c1 * fx, y, (c2 - c1 + 1) * fx,
                        lineh)

                if mainFrame.showFormatting:
                    dc.SetPen(cfgGui.bluePen)
                    util.drawLine(dc, t.x, y, 0, lineh)

                    extraIndent = 1 if self.sp.needsExtraParenIndent(i) else 0

                    util.drawLine(dc,
                        t.x + (self.sp.cfg.getType(l.lt).width - extraIndent) * fx,
                        y, 0, lineh)

                    dc.SetTextForeground(cfgGui.redColor)
                    dc.SetFont(cfgGui.fonts[pml.NORMAL].font)
                    dc.DrawText(config.lb2char(l.lb), t.x - 10, y)

                if not dpages:
                    if cfgGl.pbi == config.PBI_REAL_AND_UNADJ:
                        if self.sp.line2pageNoAdjust(i) != \
                               self.sp.line2pageNoAdjust(i + 1):
                            dc.SetPen(cfgGui.pagebreakNoAdjustPen)
                            util.drawLine(dc, 0, y + lineh - 1,
                                size.width, 0)

                    if cfgGl.pbi in (config.PBI_REAL,
                                   config.PBI_REAL_AND_UNADJ):
                        thisPage = self.sp.line2page(i)

                        if thisPage != self.sp.line2page(i + 1):
                            dc.SetPen(cfgGui.pagebreakPen)
                            util.drawLine(dc, 0, y + lineh - 1,
                                size.width, 0)

                if i == self.sp.line:
                    posX = t.x
                    cursorY = y
                    acFi = fi
                    dc.SetPen(cfgGui.cursorPen)
                    dc.SetBrush(cfgGui.cursorBrush)
                    dc.DrawRectangle(t.x + self.sp.column * fx, y, fx, fi.fy)

            if len(t.text) != 0:
                tl = texts.get(fi.font)
                if tl == None:
                    tl = ([], [], [])
                    texts[fi.font] = tl

                tl[0].append(t.text)
                tl[1].append((t.x, y))
                if t.line != -1:
                    if cfgGl.useCustomElemColors:
                        tl[2].append(cfgGui.lt2textColor(ls[t.line].lt))
                    else:
                        tl[2].append(cfgGui.textColor)
                else:
                    tl[2].append(cfgGui.textHdrColor)

                if t.isUnderlined:
                    if t.line != -1:
                        uli = ulines
                    else:
                        uli = ulinesHdr

                    uli.append((t.x, y + lineh - 1,
                               len(t.text) * fx - 1))

        if ulines:
            dc.SetPen(cfgGui.textPen)

            for ul in ulines:
                util.drawLine(dc, ul[0], ul[1], ul[2], 0)

        if ulinesHdr:
            dc.SetPen(cfgGui.textHdrPen)

            for ul in ulinesHdr:
                util.drawLine(dc, ul[0], ul[1], ul[2], 0)

        for tl in texts.iteritems():
            gd.vm.drawTexts(self, dc, tl)

        if self.sp.acItems and (cursorY > 0):
            self.drawAutoComp(dc, posX, cursorY, acFi)

    def drawAutoComp(self, dc, posX, cursorY, fi):
        ac = self.sp.acItems
        asel = self.sp.acSel

        offset = 5
        selBleed = 2

        # scroll bar width
        sbw = 10

        size = self.GetClientSize()

        dc.SetFont(fi.font)

        show = min(self.sp.acMax, len(ac))
        doSbw = show < len(ac)

        startPos = (asel // show) * show
        endPos = min(startPos + show, len(ac))
        if endPos == len(ac):
            startPos = max(0, endPos - show)

        w = 0
        for i in range(len(ac)):
            tw = dc.GetTextExtent(ac[i])[0]
            w = max(w, tw)

        w += offset * 2
        h = show * fi.fy + offset * 2

        itemW = w - offset * 2 + selBleed * 2
        if doSbw:
            w += sbw + offset * 2
            sbh = h - offset * 2 + selBleed * 2

        posY = cursorY + fi.fy + 5

        # if the box doesn't fit on the screen in the normal position, put
        # it above the current line. if it doesn't fit there either,
        # that's just too bad, we don't support window sizes that small.
        if (posY + h) > size.height:
            posY = cursorY - h - 1

        dc.SetPen(cfgGui.autoCompPen)
        dc.SetBrush(cfgGui.autoCompBrush)
        dc.DrawRectangle(posX, posY, w, h)

        dc.SetTextForeground(cfgGui.autoCompFgColor)

        for i in range(startPos, endPos):
            if i == asel:
                dc.SetPen(cfgGui.autoCompRevPen)
                dc.SetBrush(cfgGui.autoCompRevBrush)
                dc.SetTextForeground(cfgGui.autoCompBgColor)
                dc.DrawRectangle(posX + offset - selBleed,
                    posY + offset + (i - startPos) * fi.fy - selBleed,
                    itemW,
                    fi.fy + selBleed * 2)
                dc.SetTextForeground(cfgGui.autoCompBgColor)
                dc.SetPen(cfgGui.autoCompPen)
                dc.SetBrush(cfgGui.autoCompBrush)

            dc.DrawText(ac[i], posX + offset, posY + offset +
                        (i - startPos) * fi.fy)

            if i == asel:
                dc.SetTextForeground(cfgGui.autoCompFgColor)

        if doSbw:
            dc.SetPen(cfgGui.autoCompPen)
            dc.SetBrush(cfgGui.autoCompRevBrush)
            util.drawLine(dc, posX + w - offset * 2 - sbw,
                posY, 0, h)
            dc.DrawRectangle(posX + w - offset - sbw,
                posY + offset - selBleed + int((float(startPos) /
                     len(ac)) * sbh),
                sbw, int((float(show) / len(ac)) * sbh))

class MyFrame(wx.Frame):

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, name = "Trelby")

        if misc.isUnix:
            # automatically reaps zombies
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        self.clipboard = None
        self.showFormatting = False

        self.SetSizeHints(gd.cvars.getMin("width"),
                          gd.cvars.getMin("height"))

        self.MoveXY(gd.posX, gd.posY)
        self.SetSize(wx.Size(gd.width, gd.height))

        util.removeTempFiles(misc.tmpPrefix)

        self.mySetIcons()
        self.allocIds()

        fileMenu = wx.Menu()
        fileMenu.Append(ID_FILE_NEW, "&New\tCTRL-N")
        fileMenu.Append(ID_FILE_OPEN, "&Open...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, "&Save\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, "Save &As...")
        fileMenu.Append(ID_FILE_CLOSE, "&Close\tCTRL-W")
        fileMenu.Append(ID_FILE_REVERT, "&Revert")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_IMPORT, "&Import...")
        fileMenu.Append(ID_FILE_EXPORT, "&Export...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_PRINT, "&Print (via PDF)\tCTRL-P")
        fileMenu.AppendSeparator()

        tmp = wx.Menu()

        tmp.Append(ID_SETTINGS_CHANGE, "&Change...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_LOAD, "Load...")
        tmp.Append(ID_SETTINGS_SAVE_AS, "Save as...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_SC_DICT, "&Spell checker dictionary...")
        settingsMenu = tmp

        fileMenu.AppendMenu(ID_FILE_SETTINGS, "Se&ttings", tmp)

        fileMenu.AppendSeparator()
        # "most recently used" list comes in here
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXIT, "E&xit\tCTRL-Q")

        editMenu = wx.Menu()
        editMenu.Append(ID_EDIT_UNDO, "&Undo\tCTRL-Z")
        editMenu.Append(ID_EDIT_REDO, "&Redo\tCTRL-Y")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_CUT, "Cu&t\tCTRL-X")
        editMenu.Append(ID_EDIT_COPY, "&Copy\tCTRL-C")
        editMenu.Append(ID_EDIT_PASTE, "&Paste\tCTRL-V")
        editMenu.AppendSeparator()

        tmp = wx.Menu()
        tmp.Append(ID_EDIT_COPY_TO_CB, "&Unformatted")
        tmp.Append(ID_EDIT_COPY_TO_CB_FMT, "&Formatted")

        editMenu.AppendMenu(ID_EDIT_COPY_SYSTEM, "C&opy (system)", tmp)
        editMenu.Append(ID_EDIT_PASTE_FROM_CB, "P&aste (system)")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_SELECT_SCENE, "&Select scene")
        editMenu.Append(ID_EDIT_SELECT_ALL, "Select a&ll")
        editMenu.Append(ID_EDIT_GOTO_PAGE, "&Goto page...\tCTRL-G")
        editMenu.Append(ID_EDIT_GOTO_SCENE, "Goto sc&ene...\tALT-G")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_INSERT_NBSP, "Insert non-breaking space")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FIND, "&Find && Replace...\tCTRL-F")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_DELETE_ELEMENTS, "&Delete elements...")

        viewMenu = wx.Menu()
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_DRAFT, "&Draft")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_LAYOUT, "&Layout")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_SIDE_BY_SIDE, "&Side by side")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_OVERVIEW_SMALL,
                                 "&Overview - Small")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_OVERVIEW_LARGE,
                                 "O&verview - Large")

        if gd.viewMode == VIEWMODE_DRAFT:
            viewMenu.Check(ID_VIEW_STYLE_DRAFT, True)
        elif gd.viewMode == VIEWMODE_LAYOUT:
            viewMenu.Check(ID_VIEW_STYLE_LAYOUT, True)
        elif gd.viewMode == VIEWMODE_SIDE_BY_SIDE:
            viewMenu.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)
        elif gd.viewMode == VIEWMODE_OVERVIEW_SMALL:
            viewMenu.Check(ID_VIEW_STYLE_OVERVIEW_SMALL, True)
        else:
            viewMenu.Check(ID_VIEW_STYLE_OVERVIEW_LARGE, True)

        viewMenu.AppendSeparator()
        viewMenu.AppendCheckItem(ID_VIEW_SHOW_FORMATTING, "&Show formatting")
        viewMenu.Append(ID_VIEW_FULL_SCREEN, "&Fullscreen\tF11")

        scriptMenu = wx.Menu()
        scriptMenu.Append(ID_SCRIPT_FIND_ERROR, "&Find next error")
        scriptMenu.Append(ID_SCRIPT_PAGINATE, "&Paginate")
        scriptMenu.AppendSeparator()
        scriptMenu.Append(ID_SCRIPT_AUTO_COMPLETION, "&Auto-completion...")
        scriptMenu.Append(ID_SCRIPT_HEADERS, "&Headers...")
        scriptMenu.Append(ID_SCRIPT_LOCATIONS, "&Locations...")
        scriptMenu.Append(ID_SCRIPT_TITLES, "&Title pages...")
        scriptMenu.Append(ID_SCRIPT_SC_DICT, "&Spell checker dictionary...")
        scriptMenu.AppendSeparator()

        tmp = wx.Menu()

        tmp.Append(ID_SCRIPT_SETTINGS_CHANGE, "&Change...")
        tmp.AppendSeparator()
        tmp.Append(ID_SCRIPT_SETTINGS_LOAD, "&Load...")
        tmp.Append(ID_SCRIPT_SETTINGS_SAVE_AS, "&Save as...")
        scriptMenu.AppendMenu(ID_SCRIPT_SETTINGS, "&Settings", tmp)
        scriptSettingsMenu = tmp

        reportsMenu = wx.Menu()
        reportsMenu.Append(ID_REPORTS_SCRIPT_REP, "Sc&ript report")
        reportsMenu.Append(ID_REPORTS_LOCATION_REP, "&Location report...")
        reportsMenu.Append(ID_REPORTS_SCENE_REP, "&Scene report...")
        reportsMenu.Append(ID_REPORTS_CHARACTER_REP, "&Character report...")
        reportsMenu.Append(ID_REPORTS_DIALOGUE_CHART, "&Dialogue chart...")

        toolsMenu = wx.Menu()
        toolsMenu.Append(ID_TOOLS_SPELL_CHECK, "&Spell checker...")
        toolsMenu.Append(ID_TOOLS_NAME_DB, "&Name database...")
        toolsMenu.Append(ID_TOOLS_CHARMAP, "&Character map...")
        toolsMenu.Append(ID_TOOLS_COMPARE_SCRIPTS, "C&ompare scripts...")
        toolsMenu.Append(ID_TOOLS_WATERMARK, "&Generate watermarked PDFs...")

        helpMenu = wx.Menu()
        helpMenu.Append(ID_HELP_COMMANDS, "&Commands...")
        helpMenu.Append(ID_HELP_MANUAL, "&Manual")
        helpMenu.AppendSeparator()
        helpMenu.Append(ID_HELP_ABOUT, "&About...")

        self.menuBar = wx.MenuBar()
        self.menuBar.Append(fileMenu, "&File")
        self.menuBar.Append(editMenu, "&Edit")
        self.menuBar.Append(viewMenu, "&View")
        self.menuBar.Append(scriptMenu, "Scr&ipt")
        self.menuBar.Append(reportsMenu, "&Reports")
        self.menuBar.Append(toolsMenu, "Too&ls")
        self.menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(self.menuBar)

        self.toolBar = self.CreateToolBar(wx.TB_VERTICAL)

        def addTB(id, iconFilename, toolTip):
            self.toolBar.AddLabelTool(
                id, "", misc.getBitmap("resources/%s" % iconFilename),
                shortHelp=toolTip)

        addTB(ID_FILE_NEW, "new.png", "New script")
        addTB(ID_FILE_OPEN, "open.png", "Open Script..")
        addTB(ID_FILE_SAVE, "save.png", "Save..")
        addTB(ID_FILE_SAVE_AS, "saveas.png", "Save as..")
        addTB(ID_FILE_CLOSE, "close.png", "Close Script")
        addTB(ID_TOOLBAR_SCRIPTSETTINGS, "scrset.png", "Script settings")
        addTB(ID_FILE_PRINT, "pdf.png", "Print (via PDF)")

        self.toolBar.AddSeparator()

        addTB(ID_FILE_IMPORT, "import.png", "Import a text script")
        addTB(ID_FILE_EXPORT, "export.png", "Export script")

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_UNDO, "undo.png", "Undo")
        addTB(ID_EDIT_REDO, "redo.png", "Redo")

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_FIND, "find.png", "Find / Replace")
        addTB(ID_TOOLBAR_VIEWS, "layout.png", "View mode")
        addTB(ID_TOOLBAR_REPORTS, "report.png", "Script reports")
        addTB(ID_TOOLBAR_TOOLS, "tools.png", "Tools")
        addTB(ID_TOOLBAR_SETTINGS, "settings.png", "Global settings")

        self.toolBar.SetBackgroundColour(cfgGui.tabBarBgColor)
        self.toolBar.Realize()

        wx.EVT_MOVE(self, self.OnMove)
        wx.EVT_SIZE(self, self.OnSize)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vsizer)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.noFSBtn = misc.MyFSButton(self, -1, getCfgGui)
        self.noFSBtn.SetToolTipString("Exit fullscreen")
        self.noFSBtn.Show(False)
        hsizer.Add(self.noFSBtn)

        wx.EVT_BUTTON(self, self.noFSBtn.GetId(), self.ToggleFullscreen)

        self.tabCtrl = misc.MyTabCtrl(self, -1, getCfgGui)
        hsizer.Add(self.tabCtrl, 1, wx.EXPAND)

        self.statusCtrl = misc.MyStatus(self, -1, getCfgGui)
        hsizer.Add(self.statusCtrl)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        tmp = misc.MyTabCtrl2(self, -1, self.tabCtrl)
        vsizer.Add(tmp, 1, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND)


        gd.mru.useMenu(fileMenu, 14)

        wx.EVT_MENU_HIGHLIGHT_ALL(self, self.OnMenuHighlight)

        self.tabCtrl.setPageChangedFunc(self.OnPageChange)

        # see OnRightDown
        self.rightClickMenu = wx.Menu()
        self.rightClickMenuWithCut = wx.Menu()

        for m in (self.rightClickMenu, self.rightClickMenuWithCut):
            tmp = wx.Menu()

            tmp.Append(ID_ELEM_TO_SCENE, "&Scene")
            tmp.Append(ID_ELEM_TO_ACTION, "&Action")
            tmp.Append(ID_ELEM_TO_CHARACTER, "&Character")
            tmp.Append(ID_ELEM_TO_PAREN, "&Parenthetical")
            tmp.Append(ID_ELEM_TO_DIALOGUE, "&Dialogue")
            tmp.Append(ID_ELEM_TO_TRANSITION, "&Transition")
            tmp.Append(ID_ELEM_TO_SHOT, "Sh&ot")
            tmp.Append(ID_ELEM_TO_ACTBREAK, "Act &break")
            tmp.Append(ID_ELEM_TO_NOTE, "&Note")

            m.AppendSubMenu(tmp, "Element type")
            m.AppendSeparator()

            if m is self.rightClickMenuWithCut:
                m.Append(ID_EDIT_CUT, "Cut")
                m.Append(ID_EDIT_COPY, "Copy")

            m.Append(ID_EDIT_PASTE, "Paste")

        wx.EVT_MENU(self, ID_FILE_NEW, self.OnNewScript)
        wx.EVT_MENU(self, ID_FILE_OPEN, self.OnOpen)
        wx.EVT_MENU(self, ID_FILE_SAVE, self.OnSave)
        wx.EVT_MENU(self, ID_FILE_SAVE_AS, self.OnSaveScriptAs)
        wx.EVT_MENU(self, ID_FILE_IMPORT, self.OnImportScript)
        wx.EVT_MENU(self, ID_FILE_EXPORT, self.OnExportScript)
        wx.EVT_MENU(self, ID_FILE_CLOSE, self.OnCloseScript)
        wx.EVT_MENU(self, ID_FILE_REVERT, self.OnRevertScript)
        wx.EVT_MENU(self, ID_FILE_PRINT, self.OnPrint)
        wx.EVT_MENU(self, ID_SETTINGS_CHANGE, self.OnSettings)
        wx.EVT_MENU(self, ID_SETTINGS_LOAD, self.OnLoadSettings)
        wx.EVT_MENU(self, ID_SETTINGS_SAVE_AS, self.OnSaveSettingsAs)
        wx.EVT_MENU(self, ID_SETTINGS_SC_DICT, self.OnSpellCheckerDictionaryDlg)
        wx.EVT_MENU(self, ID_FILE_EXIT, self.OnExit)
        wx.EVT_MENU(self, ID_EDIT_UNDO, self.OnUndo)
        wx.EVT_MENU(self, ID_EDIT_REDO, self.OnRedo)
        wx.EVT_MENU(self, ID_EDIT_CUT, self.OnCut)
        wx.EVT_MENU(self, ID_EDIT_COPY, self.OnCopy)
        wx.EVT_MENU(self, ID_EDIT_PASTE, self.OnPaste)
        wx.EVT_MENU(self, ID_EDIT_COPY_TO_CB, self.OnCopySystemCb)
        wx.EVT_MENU(self, ID_EDIT_COPY_TO_CB_FMT, self.OnCopySystemCbFormatted)
        wx.EVT_MENU(self, ID_EDIT_PASTE_FROM_CB, self.OnPasteSystemCb)
        wx.EVT_MENU(self, ID_EDIT_SELECT_SCENE, self.OnSelectScene)
        wx.EVT_MENU(self, ID_EDIT_SELECT_ALL, self.OnSelectAll)
        wx.EVT_MENU(self, ID_EDIT_GOTO_PAGE, self.OnGotoPage)
        wx.EVT_MENU(self, ID_EDIT_GOTO_SCENE, self.OnGotoScene)
        wx.EVT_MENU(self, ID_EDIT_INSERT_NBSP, self.OnInsertNbsp)
        wx.EVT_MENU(self, ID_EDIT_FIND, self.OnFind)
        wx.EVT_MENU(self, ID_EDIT_DELETE_ELEMENTS, self.OnDeleteElements)
        wx.EVT_MENU(self, ID_VIEW_STYLE_DRAFT, self.OnViewModeChange)
        wx.EVT_MENU(self, ID_VIEW_STYLE_LAYOUT, self.OnViewModeChange)
        wx.EVT_MENU(self, ID_VIEW_STYLE_SIDE_BY_SIDE, self.OnViewModeChange)
        wx.EVT_MENU(self, ID_VIEW_STYLE_OVERVIEW_SMALL, self.OnViewModeChange)
        wx.EVT_MENU(self, ID_VIEW_STYLE_OVERVIEW_LARGE, self.OnViewModeChange)
        wx.EVT_MENU(self, ID_VIEW_SHOW_FORMATTING, self.OnShowFormatting)
        wx.EVT_MENU(self, ID_VIEW_FULL_SCREEN, self.ToggleFullscreen)
        wx.EVT_MENU(self, ID_SCRIPT_FIND_ERROR, self.OnFindNextError)
        wx.EVT_MENU(self, ID_SCRIPT_PAGINATE, self.OnPaginate)
        wx.EVT_MENU(self, ID_SCRIPT_AUTO_COMPLETION, self.OnAutoCompletionDlg)
        wx.EVT_MENU(self, ID_SCRIPT_HEADERS, self.OnHeadersDlg)
        wx.EVT_MENU(self, ID_SCRIPT_LOCATIONS, self.OnLocationsDlg)
        wx.EVT_MENU(self, ID_SCRIPT_TITLES, self.OnTitlesDlg)
        wx.EVT_MENU(self, ID_SCRIPT_SC_DICT,
                    self.OnSpellCheckerScriptDictionaryDlg)
        wx.EVT_MENU(self, ID_SCRIPT_SETTINGS_CHANGE, self.OnScriptSettings)
        wx.EVT_MENU(self, ID_SCRIPT_SETTINGS_LOAD, self.OnLoadScriptSettings)
        wx.EVT_MENU(self, ID_SCRIPT_SETTINGS_SAVE_AS, self.OnSaveScriptSettingsAs)
        wx.EVT_MENU(self, ID_REPORTS_DIALOGUE_CHART, self.OnReportDialogueChart)
        wx.EVT_MENU(self, ID_REPORTS_CHARACTER_REP, self.OnReportCharacter)
        wx.EVT_MENU(self, ID_REPORTS_SCRIPT_REP, self.OnReportScript)
        wx.EVT_MENU(self, ID_REPORTS_LOCATION_REP, self.OnReportLocation)
        wx.EVT_MENU(self, ID_REPORTS_SCENE_REP, self.OnReportScene)
        wx.EVT_MENU(self, ID_TOOLS_SPELL_CHECK, self.OnSpellCheckerDlg)
        wx.EVT_MENU(self, ID_TOOLS_NAME_DB, self.OnNameDatabase)
        wx.EVT_MENU(self, ID_TOOLS_CHARMAP, self.OnCharacterMap)
        wx.EVT_MENU(self, ID_TOOLS_COMPARE_SCRIPTS, self.OnCompareScripts)
        wx.EVT_MENU(self, ID_TOOLS_WATERMARK, self.OnWatermark)
        wx.EVT_MENU(self, ID_HELP_COMMANDS, self.OnHelpCommands)
        wx.EVT_MENU(self, ID_HELP_MANUAL, self.OnHelpManual)
        wx.EVT_MENU(self, ID_HELP_ABOUT, self.OnAbout)

        wx.EVT_MENU_RANGE(self, gd.mru.getIds()[0], gd.mru.getIds()[1],
                          self.OnMRUFile)

        wx.EVT_MENU_RANGE(self, ID_ELEM_TO_ACTION, ID_ELEM_TO_TRANSITION,
                          self.OnChangeType)

        def addTBMenu(id, menu):
            wx.EVT_MENU(self, id, partial(self.OnToolBarMenu, menu=menu))

        addTBMenu(ID_TOOLBAR_SETTINGS, settingsMenu)
        addTBMenu(ID_TOOLBAR_SCRIPTSETTINGS, scriptSettingsMenu)
        addTBMenu(ID_TOOLBAR_REPORTS, reportsMenu)
        addTBMenu(ID_TOOLBAR_VIEWS, viewMenu)
        addTBMenu(ID_TOOLBAR_TOOLS, toolsMenu)

        wx.EVT_CLOSE(self, self.OnCloseWindow)
        wx.EVT_SET_FOCUS(self, self.OnFocus)

        self.Layout()

    def init(self):
        self.updateKbdCommands()
        self.panel = self.createNewPanel()

    def mySetIcons(self):
        wx.Image_AddHandler(wx.PNGHandler())

        ib = wx.IconBundle()

        for sz in ("16", "32", "64", "128", "256"):
            ib.AddIcon(wx.IconFromBitmap(misc.getBitmap("resources/icon%s.png" % sz)))

        self.SetIcons(ib)

    def allocIds(self):
        names = [
            "ID_EDIT_UNDO",
            "ID_EDIT_REDO",
            "ID_EDIT_COPY",
            "ID_EDIT_COPY_SYSTEM",
            "ID_EDIT_COPY_TO_CB",
            "ID_EDIT_COPY_TO_CB_FMT",
            "ID_EDIT_CUT",
            "ID_EDIT_DELETE_ELEMENTS",
            "ID_EDIT_FIND",
            "ID_EDIT_GOTO_SCENE",
            "ID_EDIT_GOTO_PAGE",
            "ID_EDIT_INSERT_NBSP",
            "ID_EDIT_PASTE",
            "ID_EDIT_PASTE_FROM_CB",
            "ID_EDIT_SELECT_ALL",
            "ID_EDIT_SELECT_SCENE",
            "ID_FILE_CLOSE",
            "ID_FILE_EXIT",
            "ID_FILE_EXPORT",
            "ID_FILE_IMPORT",
            "ID_FILE_NEW",
            "ID_FILE_OPEN",
            "ID_FILE_PRINT",
            "ID_FILE_REVERT",
            "ID_FILE_SAVE",
            "ID_FILE_SAVE_AS",
            "ID_FILE_SETTINGS",
            "ID_HELP_ABOUT",
            "ID_HELP_COMMANDS",
            "ID_HELP_MANUAL",
            "ID_REPORTS_CHARACTER_REP",
            "ID_REPORTS_DIALOGUE_CHART",
            "ID_REPORTS_LOCATION_REP",
            "ID_REPORTS_SCENE_REP",
            "ID_REPORTS_SCRIPT_REP",
            "ID_SCRIPT_AUTO_COMPLETION",
            "ID_SCRIPT_FIND_ERROR",
            "ID_SCRIPT_HEADERS",
            "ID_SCRIPT_LOCATIONS",
            "ID_SCRIPT_PAGINATE",
            "ID_SCRIPT_SC_DICT",
            "ID_SCRIPT_SETTINGS",
            "ID_SCRIPT_SETTINGS_CHANGE",
            "ID_SCRIPT_SETTINGS_LOAD",
            "ID_SCRIPT_SETTINGS_SAVE_AS",
            "ID_SCRIPT_TITLES",
            "ID_SETTINGS_CHANGE",
            "ID_SETTINGS_LOAD",
            "ID_SETTINGS_SAVE_AS",
            "ID_SETTINGS_SC_DICT",
            "ID_TOOLS_CHARMAP",
            "ID_TOOLS_COMPARE_SCRIPTS",
            "ID_TOOLS_NAME_DB",
            "ID_TOOLS_SPELL_CHECK",
            "ID_TOOLS_WATERMARK",
            "ID_VIEW_SHOW_FORMATTING",
            "ID_VIEW_STYLE_DRAFT",
            "ID_VIEW_STYLE_LAYOUT",
            "ID_VIEW_STYLE_OVERVIEW_LARGE",
            "ID_VIEW_STYLE_OVERVIEW_SMALL",
            "ID_VIEW_STYLE_SIDE_BY_SIDE",
            "ID_TOOLBAR_SETTINGS",
            "ID_TOOLBAR_SCRIPTSETTINGS",
            "ID_TOOLBAR_REPORTS",
            "ID_TOOLBAR_VIEWS",
            "ID_TOOLBAR_TOOLS",
            "ID_VIEW_FULL_SCREEN",
            "ID_ELEM_TO_ACTION",
            "ID_ELEM_TO_CHARACTER",
            "ID_ELEM_TO_DIALOGUE",
            "ID_ELEM_TO_NOTE",
            "ID_ELEM_TO_PAREN",
            "ID_ELEM_TO_SCENE",
            "ID_ELEM_TO_SHOT",
            "ID_ELEM_TO_ACTBREAK",
            "ID_ELEM_TO_TRANSITION",
            ]

        g = globals()

        for n in names:
            g[n] = wx.NewId()

        # see OnChangeType
        g["idToLTMap"] = {
            ID_ELEM_TO_SCENE : screenplay.SCENE,
            ID_ELEM_TO_ACTION : screenplay.ACTION,
            ID_ELEM_TO_CHARACTER : screenplay.CHARACTER,
            ID_ELEM_TO_DIALOGUE : screenplay.DIALOGUE,
            ID_ELEM_TO_PAREN : screenplay.PAREN,
            ID_ELEM_TO_TRANSITION : screenplay.TRANSITION,
            ID_ELEM_TO_SHOT : screenplay.SHOT,
            ID_ELEM_TO_ACTBREAK : screenplay.ACTBREAK,
            ID_ELEM_TO_NOTE : screenplay.NOTE,
            }

    def createNewPanel(self):
        newPanel = MyPanel(self.tabCtrl.getTabParent(), -1)
        self.tabCtrl.addPage(newPanel, u"")
        newPanel.ctrl.setTabText()
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Trelby - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)

        if i != -1:
            # strip out ".trelby" suffix from tab names (it's a bit
            # complicated since if we open the same file multiple times,
            # we have e.g. "foo.trelby" and "foo.trelby<2>", so actually
            # we just strip out ".trelby" if it's found anywhere in the
            # string)

            s = text.replace(".trelby", "")
            self.tabCtrl.setTabText(i, s)

    # iterates over all tabs and finds out the corresponding page number
    # for the given panel.
    def findPage(self, panel):
        for i in range(self.tabCtrl.getPageCount()):
            p = self.tabCtrl.getPage(i)
            if p == panel:
                return i

        return -1

    # get list of MyCtrl objects for all open scripts
    def getCtrls(self):
        l = []

        for i in range(self.tabCtrl.getPageCount()):
            l.append(self.tabCtrl.getPage(i).ctrl)

        return l

    # returns True if any open script has been modified
    def isModifications(self):
        for c in self.getCtrls():
            if c.sp.isModified():
                return True

        return False

    def updateKbdCommands(self):
        cfgGl.addShiftKeys()

        if cfgGl.getConflictingKeys() != None:
            wx.MessageBox("You have at least one key bound to more than one\n"
                          "command. The program will not work correctly until\n"
                          "you fix this.",
                          "Warning", wx.OK, self)

        self.kbdCommands = {}

        for cmd in cfgGl.commands:
            if not (cmd.isFixed and cmd.isMenu):
                for key in cmd.keys:
                    self.kbdCommands[key] = cmd

    # open script, in the current tab if it's untouched, or in a new one
    # otherwise
    def openScript(self, filename):
        if not self.tabCtrl.getPage(self.findPage(self.panel))\
               .ctrl.isUntouched():
            self.panel = self.createNewPanel()

        self.panel.ctrl.loadFile(filename)
        self.panel.ctrl.updateScreen()
        gd.mru.add(filename)

    def checkFonts(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]
        failed = []

        for i, fi in enumerate(cfgGui.fonts):
            if not util.isFixedWidth(fi.font):
                failed.append(names[i])

        if failed:
            wx.MessageBox(
                "The fonts listed below are not fixed width and\n"
                "will cause the program not to function correctly.\n"
                "Please change the fonts at File/Settings/Change.\n\n"
                + "\n".join(failed), "Error", wx.OK, self)

    # If we get focus, pass it on to ctrl.
    def OnFocus(self, event):
        self.panel.ctrl.SetFocus()

    def OnMenuHighlight(self, event):
        # default implementation modifies status bar, so we need to
        # override it and do nothing
        pass

    def OnPageChange(self, page):
        self.panel = self.tabCtrl.getPage(page)
        self.panel.ctrl.SetFocus()
        self.panel.ctrl.updateCommon()
        self.setTitle(self.panel.ctrl.fileNameDisplay)

    def selectScript(self, toNext):
        current = self.tabCtrl.getSelectedPageIndex()
        pageCnt = self.tabCtrl.getPageCount()

        if toNext:
            pageNr = current + 1
        else:
            pageNr = current - 1

        if pageNr == -1:
            pageNr = pageCnt - 1
        elif pageNr == pageCnt:
            pageNr = 0

        if pageNr == current:
            # only one tab, nothing to do
            return

        self.tabCtrl.selectPage(pageNr)

    def OnScriptNext(self, event = None):
        self.selectScript(True)

    def OnScriptPrev(self, event = None):
        self.selectScript(False)

    def OnNewScript(self, event = None):
        self.panel = self.createNewPanel()

    def OnMRUFile(self, event):
        i = event.GetId() - gd.mru.getIds()[0]
        self.openScript(gd.mru.get(i))

    def OnOpen(self, event = None):
        dlg = wx.FileDialog(self, "File to open",
            misc.scriptDir,
            wildcard = "Trelby files (*.trelby)|*.trelby|All files|*",
            style = wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()
            self.openScript(dlg.GetPath())

        dlg.Destroy()

    def OnSave(self, event = None):
        self.panel.ctrl.OnSave()

    def OnSaveScriptAs(self, event = None):
        self.panel.ctrl.OnSaveScriptAs()

    def OnImportScript(self, event = None):
        dlg = wx.FileDialog(self, "File to import",
            misc.scriptDir,
            wildcard = "Importable files (*.txt;*.fdx;*.celtx;*.astx;*.fountain;*.fadein)|" +
                       "*.fdx;*.txt;*.celtx;*.astx;*.fountain;*.fadein|" +
                       "Formatted text files (*.txt)|*.txt|" +
                       "Final Draft XML(*.fdx)|*.fdx|" +
                       "Celtx files (*.celtx)|*.celtx|" +
                       "Adobe Story XML files (*.astx)|*.astx|" +
                       "Fountain files (*.fountain)|*.fountain|" +
                       "Fadein files (*.fadein)|*.fadein|" +
                       "All files|*",
            style = wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()

            if not self.tabCtrl.getPage(self.findPage(self.panel))\
                   .ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.importFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnExportScript(self, event = None):
        self.panel.ctrl.OnExportScript()

    def OnCloseScript(self, event = None):
        if not self.panel.ctrl.canBeClosed():
            return

        if self.tabCtrl.getPageCount() > 1:
            self.tabCtrl.deletePage(self.tabCtrl.getSelectedPageIndex())
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevertScript(self, event = None):
        self.panel.ctrl.OnRevertScript()

    def OnPrint(self, event = None):
        self.panel.ctrl.OnPrint()

    def OnSettings(self, event = None):
        self.panel.ctrl.OnSettings()

    def OnLoadSettings(self, event = None):
        dlg = wx.FileDialog(self, "File to open",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                c = config.ConfigGlobal()
                c.load(s)
                gd.confFilename = dlg.GetPath()

                self.panel.ctrl.applyGlobalCfg(c, False)

        dlg.Destroy()

    def OnSaveSettingsAs(self, event = None):
        dlg = wx.FileDialog(self, "Filename to save as",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), cfgGl.save(), self):
                gd.confFilename = dlg.GetPath()

        dlg.Destroy()

    def OnUndo(self, event = None):
        self.panel.ctrl.OnUndo()

    def OnRedo(self, event = None):
        self.panel.ctrl.OnRedo()

    def OnCut(self, event = None):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event = None):
        self.panel.ctrl.OnCopy()

    def OnCopySystemCb(self, event = None):
        self.panel.ctrl.OnCopySystem(formatted = False)

    def OnCopySystemCbFormatted(self, event = None):
        self.panel.ctrl.OnCopySystem(formatted = True)

    def OnPaste(self, event = None):
        self.panel.ctrl.OnPaste()

    def OnPasteSystemCb(self, event = None):
        self.panel.ctrl.OnPasteSystemCb()

    def OnSelectScene(self, event = None):
        self.panel.ctrl.OnSelectScene()

    def OnSelectAll(self, event = None):
        self.panel.ctrl.OnSelectAll()

    def OnGotoPage(self, event = None):
        self.panel.ctrl.OnGotoPage()

    def OnGotoScene(self, event = None):
        self.panel.ctrl.OnGotoScene()

    def OnFindNextError(self, event = None):
        self.panel.ctrl.OnFindNextError()

    def OnFind(self, event = None):
        self.panel.ctrl.OnFind()

    def OnInsertNbsp(self, event = None):
        self.panel.ctrl.OnInsertNbsp()

    def OnDeleteElements(self, event = None):
        self.panel.ctrl.OnDeleteElements()

    def OnToggleShowFormatting(self, event = None):
        self.menuBar.Check(ID_VIEW_SHOW_FORMATTING,
            not self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING))
        self.showFormatting = not self.showFormatting
        self.panel.ctrl.Refresh(False)

    def OnShowFormatting(self, event = None):
        self.showFormatting = self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        self.panel.ctrl.Refresh(False)

    def OnViewModeDraft(self):
        self.menuBar.Check(ID_VIEW_STYLE_DRAFT, True)
        self.OnViewModeChange()

    def OnViewModeLayout(self):
        self.menuBar.Check(ID_VIEW_STYLE_LAYOUT, True)
        self.OnViewModeChange()

    def OnViewModeSideBySide(self):
        self.menuBar.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)
        self.OnViewModeChange()

    def OnViewModeOverviewSmall(self):
        self.menuBar.Check(ID_VIEW_STYLE_OVERVIEW_SMALL, True)
        self.OnViewModeChange()

    def OnViewModeOverviewLarge(self):
        self.menuBar.Check(ID_VIEW_STYLE_OVERVIEW_LARGE, True)
        self.OnViewModeChange()

    def OnViewModeChange(self, event = None):
        if self.menuBar.IsChecked(ID_VIEW_STYLE_DRAFT):
            mode = VIEWMODE_DRAFT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_LAYOUT):
            mode = VIEWMODE_LAYOUT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_SIDE_BY_SIDE):
            mode = VIEWMODE_SIDE_BY_SIDE
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_OVERVIEW_SMALL):
            mode = VIEWMODE_OVERVIEW_SMALL
        else:
            mode = VIEWMODE_OVERVIEW_LARGE

        gd.setViewMode(mode)

        for c in self.getCtrls():
            c.refreshCache()

        c = self.panel.ctrl
        c.makeLineVisible(c.sp.line)
        c.updateScreen()

    def ToggleFullscreen(self, event = None):
        self.noFSBtn.Show(not self.IsFullScreen())
        self.ShowFullScreen(not self.IsFullScreen(), wx.FULLSCREEN_ALL)
        self.panel.ctrl.SetFocus()

    def OnPaginate(self, event = None):
        self.panel.ctrl.OnPaginate()

    def OnAutoCompletionDlg(self, event = None):
        self.panel.ctrl.OnAutoCompletionDlg()

    def OnTitlesDlg(self, event = None):
        self.panel.ctrl.OnTitlesDlg()

    def OnHeadersDlg(self, event = None):
        self.panel.ctrl.OnHeadersDlg()

    def OnLocationsDlg(self, event = None):
        self.panel.ctrl.OnLocationsDlg()

    def OnSpellCheckerDictionaryDlg(self, event = None):
        dlg = spellcheckcfgdlg.SCDictDlg(self, copy.deepcopy(gd.scDict),
                                         True)

        if dlg.ShowModal() == wx.ID_OK:
            gd.scDict = dlg.scDict
            gd.saveScDict()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self, event = None):
        self.panel.ctrl.OnSpellCheckerScriptDictionaryDlg()

    def OnWatermark(self, event = None):
        self.panel.ctrl.OnWatermark()

    def OnScriptSettings(self, event = None):
        self.panel.ctrl.OnScriptSettings()

    def OnLoadScriptSettings(self, event = None):
        dlg = wx.FileDialog(self, "File to open",
            defaultDir = gd.scriptSettingsPath,
            wildcard = "Script setting files (*.sconf)|*.sconf|All files|*",
            style = wx.OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                cfg = config.Config()
                cfg.load(s)
                self.panel.ctrl.applyCfg(cfg)

                gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnSaveScriptSettingsAs(self, event = None):
        dlg = wx.FileDialog(self, "Filename to save as",
            defaultDir = gd.scriptSettingsPath,
            wildcard = "Script setting files (*.sconf)|*.sconf|All files|*",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), self.panel.ctrl.sp.saveCfg(), self):
                gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnReportCharacter(self, event = None):
        self.panel.ctrl.OnReportCharacter()

    def OnReportDialogueChart(self, event = None):
        self.panel.ctrl.OnReportDialogueChart()

    def OnReportLocation(self, event = None):
        self.panel.ctrl.OnReportLocation()

    def OnReportScene(self, event = None):
        self.panel.ctrl.OnReportScene()

    def OnReportScript(self, event = None):
        self.panel.ctrl.OnReportScript()

    def OnSpellCheckerDlg(self, event = None):
        self.panel.ctrl.OnSpellCheckerDlg()

    def OnNameDatabase(self, event = None):
        if not namesdlg.readNames(self):
            wx.MessageBox("Error opening name database.", "Error",
                          wx.OK, self)

            return

        dlg = namesdlg.NamesDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCharacterMap(self, event = None):
        dlg = charmapdlg.CharMapDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self, event = None):
        self.panel.ctrl.OnCompareScripts()

    def OnChangeType(self, event):
        self.panel.ctrl.OnChangeType(event)

    def OnHelpCommands(self, event = None):
        dlg = commandsdlg.CommandsDlg(cfgGl)
        dlg.Show()

    def OnHelpManual(self, event = None):
        wx.LaunchDefaultBrowser("file://" + misc.getFullPath("manual.html"))

    def OnAbout(self, event = None):
        win = splash.SplashWindow(self, -1)
        win.Show()

    def OnToolBarMenu(self, event, menu):
        self.PopupMenu(menu)

    def OnCloseWindow(self, event):
        doExit = True
        if event.CanVeto() and self.isModifications():
            if wx.MessageBox("You have unsaved changes. Are\n"
                             "you sure you want to exit?", "Confirm",
                             wx.YES_NO | wx.NO_DEFAULT, self) == wx.NO:
                doExit = False

        if doExit:
            util.writeToFile(gd.stateFilename, gd.save(), self)
            util.removeTempFiles(misc.tmpPrefix)
            self.Destroy()
            myApp.ExitMainLoop()
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)

    def OnMove(self, event):
        gd.posX, gd.posY = self.GetPositionTuple()
        event.Skip()

    def OnSize(self, event):
        gd.width, gd.height = self.GetSizeTuple()
        event.Skip()

class MyApp(wx.App):

    def OnInit(self):
        global cfgGl, mainFrame, gd

        if (wx.MAJOR_VERSION != 2) or (wx.MINOR_VERSION != 8):
            wx.MessageBox("You seem to have an invalid version\n"
                          "(%s) of wxWidgets installed. This\n"
                          "program needs version 2.8." %
                          wx.VERSION_STRING, "Error", wx.OK)
            sys.exit()

        misc.init()
        util.init()

        gd = GlobalData()

        if misc.isWindows:
            major = sys.getwindowsversion()[0]
            if major < 5:
                wx.MessageBox("You seem to have a version of Windows\n"
                              "older than Windows 2000, which is the minimum\n"
                              "requirement for this program.", "Error", wx.OK)
                sys.exit()

        if not misc.wxIsUnicode:
            wx.MessageBox("You seem to be using a non-Unicode build of\n"
                          "wxWidgets. This is not supported.",
                          "Error", wx.OK)
            sys.exit()

        # by setting this, we don't have to convert from 8-bit strings to
        # Unicode ourselves everywhere when we pass them to wxWidgets.
        wx.SetDefaultPyEncoding("ISO-8859-1")

        os.chdir(misc.progPath)

        cfgGl = config.ConfigGlobal()
        cfgGl.setDefaults()

        if util.fileExists(gd.confFilename):
            s = util.loadFile(gd.confFilename, None)

            if s:
                cfgGl.load(s)
        else:
            # we want to write out a default config file at startup for
            # various reasons, if no default config file yet exists
            util.writeToFile(gd.confFilename, cfgGl.save(), None)

        refreshGuiConfig()

        # cfgGl.scriptDir is the directory used on startup, while
        # misc.scriptDir is updated every time the user opens something in
        # a different directory.
        misc.scriptDir = cfgGl.scriptDir

        if util.fileExists(gd.stateFilename):
            s = util.loadFile(gd.stateFilename, None)

            if s:
                gd.load(s)

        gd.setViewMode(gd.viewMode)

        if util.fileExists(gd.scDictFilename):
            s = util.loadFile(gd.scDictFilename, None)

            if s:
                gd.scDict.load(s)

        mainFrame = MyFrame(None, -1, "Trelby")
        mainFrame.init()

        for arg in opts.filenames:
            mainFrame.openScript(arg)

        mainFrame.Show(True)

        # windows needs this for some reason
        mainFrame.panel.ctrl.SetFocus()

        self.SetTopWindow(mainFrame)

        mainFrame.checkFonts()

        if cfgGl.splashTime > 0:
            win = splash.SplashWindow(mainFrame, cfgGl.splashTime * 1000)
            win.Show()
            win.Raise()

        return True

def main():
    global myApp

    opts.init()

    myApp = MyApp(0)
    myApp.MainLoop()

########NEW FILE########
__FILENAME__ = truetype
import struct
unpack = struct.unpack

OFFSET_TABLE_SIZE = 12
TABLE_DIR_SIZE = 16
NAME_TABLE_SIZE = 6
NAME_RECORD_SIZE = 12

class ParseError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

def check(val):
    if not val:
        raise ParseError("")

# a parser for TrueType/OpenType fonts.
# http://www.microsoft.com/typography/otspec/default.htm contained the
# spec at the time of the writing.
class Font:

    # load font from string s, which is the whole contents of a font file
    def __init__(self, s):
        # is this a valid font
        self.ok = False

        # parse functions for tables, and a flag for whether each has been
        # parsed successfully
        self.parseFuncs = {
            "head" : [self.parseHead, False],
            "name" : [self.parseName, False],
            "OS/2" : [self.parseOS2, False]
            }

        try:
            self.parse(s)
        except (struct.error, ParseError), e:
            self.error = e

            return

        self.ok = True

    # check if font was parsed correctly. none of the other
    # (user-oriented) functions can be called if this returns False.
    def isOK(self):
        return self.ok

    # get font's Postscript name.
    def getPostscriptName(self):
        return self.psName

    # returns True if font allows embedding.
    def allowsEmbedding(self):
        return self.embeddingOK

    # parse whole file
    def parse(self, s):
        version, self.tableCnt = unpack(">LH", s[:6])

        check(version == 0x00010000)

        offset = OFFSET_TABLE_SIZE

        for i in range(self.tableCnt):
            self.parseTag(offset, s)
            offset += TABLE_DIR_SIZE

        for name, func in self.parseFuncs.iteritems():
            if not func[1]:
                raise ParseError("Table %s missing/invalid" % name)

    # parse a single tag
    def parseTag(self, offset, s):
        tag, checkSum, tagOffset, length = unpack(">4s3L",
            s[offset : offset + TABLE_DIR_SIZE])

        check(tagOffset >= (OFFSET_TABLE_SIZE +
                            self.tableCnt * TABLE_DIR_SIZE))

        func = self.parseFuncs.get(tag)
        if func:
            func[0](s[tagOffset : tagOffset + length])
            func[1] = True

    # parse head table
    def parseHead(self, s):
        magic = unpack(">L", s[12:16])[0]

        check(magic == 0x5F0F3CF5)

    # parse name table
    def parseName(self, s):
        fmt, nameCnt, storageOffset = unpack(">3H", s[:NAME_TABLE_SIZE])

        check(fmt == 0)

        storage = s[storageOffset:]
        offset = NAME_TABLE_SIZE

        for i in range(nameCnt):
            if self.parseNameRecord(s[offset : offset + NAME_RECORD_SIZE],
                                    storage):
                return

            offset += NAME_RECORD_SIZE

        raise ParseError("No Postscript name found")

    # parse a single name record. s2 is string storage. returns True if
    # this record is a valid Postscript name.
    def parseNameRecord(self, s, s2):
        platformID, encodingID, langID, nameID, strLen, strOffset = \
                    unpack(">6H", s)

        if nameID != 6:
            return False

        if (platformID == 1) and (encodingID == 0) and (langID == 0):
            # Macintosh, 1-byte strings

            self.psName = unpack("%ds" % strLen,
                                 s2[strOffset : strOffset + strLen])[0]

            return True

        elif (platformID == 3) and (encodingID == 1) and (langID == 0x409):
            # Windows, UTF-16BE

            tmp = unpack("%ds" % strLen,
                                 s2[strOffset : strOffset + strLen])[0]

            self.psName = tmp.decode("UTF-16BE", "ignore").encode(
                "ISO-8859-1", "ignore")

            return True

        return False

    def parseOS2(self, s):
        fsType = unpack(">H", s[8:10])[0]

        # the font embedding bits are a mess, the meanings have changed
        # over time in the TrueType/OpenType specs. this is the least
        # restrictive interpretation common to them all.
        self.embeddingOK = (fsType & 0xF) != 2

########NEW FILE########
__FILENAME__ = undo
import screenplay

import zlib

# Which command uses which undo object:
#
# command                type
# -------                ------
#
# removeElementTypes     FullCopy
# addChar                SinglePara (possibly merged)
#   charmap
#   namesDlg
# spellCheck             SinglePara
# findAndReplace         SinglePara
# NewElement             ManyElems(1, 2)
# Tab:
#   (end of elem)        ManyElems(1, 2)
#   (middle of elem)     ManyElems(1, 1)
# TabPrev                ManyElems(1, 1)
# insertForcedLineBreak  ManyElems(1, 1)
# deleteForward:
#   (not end of elem)    ManyElems(1, 1) (possibly merged)
#   (end of elem)        ManyElems(2, 1)
# deleteBackward:
#   (not start of elem)  ManyElems(1, 1) (possibly merged)
#   (start of elem)      ManyElems(2, 1)
# convertTypeTo          ManyElems(N, N)
# cut                    AnyDifference
# paste                  AnyDifference


# extremely rough estimate for the base memory usage of a single undo
# object, WITHOUT counting the actual textual differences stored inside
# it. so this figure accounts for the Python object overhead, member
# variable overhead, memory allocation overhead, etc.
#
# this figure does not need to be very accurate.
BASE_MEMORY_USAGE = 1500

# possible command types. only used for possibly merging consecutive
# edits.
(CMD_ADD_CHAR,
 CMD_ADD_CHAR_SPACE,
 CMD_DEL_FORWARD,
 CMD_DEL_BACKWARD,
 CMD_MISC) = range(5)

# convert a list of Screenplay.Line objects into an unspecified, but
# compact, form of storage. storage2lines will convert this back to the
# original form.
#
# the return type is a tuple: (numberOfLines, ...). the number and type of
# elements after the first is of no concern to the caller.
#
# implementation notes:
#
#   tuple[1]: bool; True if tuple[2] is zlib-compressed
#
#   tuple[2]: string; the line objects converted to their string
#   representation and joined by the "\n" character
#
def lines2storage(lines):
    if not lines:
        return (0,)

    lines = [str(ln) for ln in lines]
    linesStr = "\n".join(lines)

    # instead of having an arbitrary cutoff figure ("compress if < X
    # bytes"), always compress, but only use the compressed version if
    # it's shorter than the non-compressed one.

    linesStrCompressed = zlib.compress(linesStr, 6)

    if len(linesStrCompressed) < len(linesStr):
        return (len(lines), True, linesStrCompressed)
    else:
        return (len(lines), False, linesStr)

# see lines2storage.
def storage2lines(storage):
    if storage[0] == 0:
        return []

    if storage[1]:
        linesStr = zlib.decompress(storage[2])
    else:
        linesStr = storage[2]

    return [screenplay.Line.fromStr(s) for s in linesStr.split("\n")]

# how much memory is used by the given storage object
def memoryUsed(storage):
    # 16 is a rough estimate for the first two tuple members' memory usage

    if storage[0] == 0:
        return 16

    return 16 + len(storage[2])

# abstract base class for storing undo history. concrete subclasses
# implement undo/redo for specific actions taken on a screenplay.
class Base:
    def __init__(self, sp, cmdType):
        # cursor position before the action
        self.startPos = sp.cursorAsMark()

        # type of action; one of the CMD_ values
        self.cmdType = cmdType

        # prev/next undo objects in the history
        self.prev = None
        self.next = None

    # set cursor position after the action
    def setEndPos(self, sp):
        self.endPos = sp.cursorAsMark()

    def getType(self):
        return self.cmdType

    # rough estimate of how much memory is used by this undo object. can
    # be overridden by subclasses that need something different.
    def memoryUsed(self):
        return (BASE_MEMORY_USAGE + memoryUsed(self.linesBefore) +
                memoryUsed(self.linesAfter))

    # default implementation for undo. can be overridden by subclasses
    # that need something different.
    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        sp.lines[self.elemStartLine : self.elemStartLine + self.linesAfter[0]] = \
            storage2lines(self.linesBefore)

    # default implementation for redo. can be overridden by subclasses
    # that need something different.
    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines[self.elemStartLine : self.elemStartLine + self.linesBefore[0]] = \
            storage2lines(self.linesAfter)

# stores a full copy of the screenplay before/after the action. used by
# actions that modify the screenplay globally.
#
# we store the line data as compressed text, not as a list of Line
# objects, because it takes much less memory to do so. figures from a
# 32-bit machine (a 64-bit machine wastes even more space storing Line
# objects) from speedTest for a 120-page screenplay (Casablanca):
#
#   -Line objects:         1,737 KB, 0.113s
#   -text, not compressed:   267 KB, 0.076s
#   -text, zlib fastest(1):  127 KB, 0.090s
#   -text, zlib medium(6):   109 KB, 0.115s
#   -text, zlib best(9):     107 KB, 0.126s
#   -text, bz2 best(9):       88 KB, 0.147s
class FullCopy(Base):
    def __init__(self, sp):
        Base.__init__(self, sp, CMD_MISC)

        self.elemStartLine = 0
        self.linesBefore = lines2storage(sp.lines)

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        self.linesAfter = lines2storage(sp.lines)
        self.setEndPos(sp)


# stores a single modified paragraph
class SinglePara(Base):
    # line is any line belonging to the modified paragraph. there is no
    # requirement for the cursor to be in this paragraph.
    def __init__(self, sp, cmdType, line):
        Base.__init__(self, sp, cmdType)

        self.elemStartLine = sp.getParaFirstIndexFromLine(line)
        endLine = sp.getParaLastIndexFromLine(line)

        self.linesBefore = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

    def setAfter(self, sp):
        # if all we did was modify a single paragraph, the index of its
        # starting line can not have changed, because that would mean one of
        # the paragraphs above us had changed as well, which is a logical
        # impossibility. so we can find the dimensions of the modified
        # paragraph by starting at the first line.

        endLine = sp.getParaLastIndexFromLine(self.elemStartLine)

        self.linesAfter = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

        self.setEndPos(sp)


# stores N modified consecutive elements
class ManyElems(Base):
    # line is any line belonging to the first modified element. there is
    # no requirement for the cursor to be in this paragraph.
    # nrOfElemsStart is how many elements there are before the edit
    # operaton and nrOfElemsEnd is how many there are after. so an edit
    # operation splitting an element would pass in (1, 2) while an edit
    # operation combining two elements would pass in (2, 1).
    def __init__(self, sp, cmdType, line, nrOfElemsStart, nrOfElemsEnd):
        Base.__init__(self, sp, cmdType)

        self.nrOfElemsEnd = nrOfElemsEnd

        self.elemStartLine, endLine = sp.getElemIndexesFromLine(line)

        # find last line of last element to include in linesBefore
        for i in range(nrOfElemsStart - 1):
            endLine = sp.getElemLastIndexFromLine(endLine + 1)

        self.linesBefore = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

    def setAfter(self, sp):
        endLine = sp.getElemLastIndexFromLine(self.elemStartLine)

        for i in range(self.nrOfElemsEnd - 1):
            endLine = sp.getElemLastIndexFromLine(endLine + 1)

        self.linesAfter = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

        self.setEndPos(sp)

# stores a single block of changed lines by diffing before/after states of
# a screenplay
class AnyDifference(Base):
    def __init__(self, sp):
        Base.__init__(self, sp, CMD_MISC)

        self.linesBefore = [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in sp.lines]

    def setAfter(self, sp):
        self.a, self.b, self.x, self.y = mySequenceMatcher(self.linesBefore, sp.lines)

        self.removed = lines2storage(self.linesBefore[self.a : self.b])
        self.inserted = lines2storage(sp.lines[self.x : self.y])

        self.setEndPos(sp)

        del self.linesBefore

    def memoryUsed(self):
        return (BASE_MEMORY_USAGE + memoryUsed(self.removed) +
                memoryUsed(self.inserted))

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        sp.lines[self.x : self.y] = storage2lines(self.removed)

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines[self.a : self.b] = storage2lines(self.inserted)


# Our own implementation of difflib.SequenceMatcher, since the actual one
# is too slow for our custom needs.
#
# l1, l2 = lists to diff. List elements must have __ne__ defined.
#
# Return a, b, x, y such that l1[a:b] could be replaced with l2[x:y] to
# convert l1 into l2.
def mySequenceMatcher(l1, l2):
    len1 = len(l1)
    len2 = len(l2)

    if len1 >= len2:
        bigger = l1
        smaller = l2
        bigLen = len1
        smallLen = len2
        l1Big = True
    else:
        bigger = l2
        smaller = l1
        bigLen = len2
        smallLen = len1
        l1Big = False

    i = 0
    a = b = 0

    m1found = m2found = False

    while a < smallLen:
        if not m1found and (bigger[a] != smaller[a]):
            b = a
            m1found = True

            break

        a += 1

    if not m1found:
        a = b = smallLen

    num = smallLen - a + 1
    i = 1
    c = bigLen
    d = smallLen

    while (i <= num) and (i <= smallLen):
        c = bigLen - i + 1
        d = smallLen - i + 1

        if bigger[-i] != smaller[-i]:
            m2found = True

            break

        i += 1

    if not l1Big:
        a, c, b, d = a, d, b, c

    return a, c, b, d

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-

from error import *

import datetime
import glob
import gzip
import misc
import os
import re
import tempfile
import time

import StringIO


import wx

# alignment values
ALIGN_LEFT    = 0
ALIGN_CENTER  = 1
ALIGN_RIGHT   = 2
VALIGN_TOP    = 1
VALIGN_CENTER = 2
VALIGN_BOTTOM = 3

# this has to be below the ALIGN stuff, otherwise things break due to
# circular dependencies
import fontinfo

# mappings from lowercase to uppercase letters for different charsets
_iso_8859_1_map = {
    97 : 65, 98 : 66, 99 : 67, 100 : 68, 101 : 69,
    102 : 70, 103 : 71, 104 : 72, 105 : 73, 106 : 74,
    107 : 75, 108 : 76, 109 : 77, 110 : 78, 111 : 79,
    112 : 80, 113 : 81, 114 : 82, 115 : 83, 116 : 84,
    117 : 85, 118 : 86, 119 : 87, 120 : 88, 121 : 89,
    122 : 90, 224 : 192, 225 : 193, 226 : 194, 227 : 195,
    228 : 196, 229 : 197, 230 : 198, 231 : 199, 232 : 200,
    233 : 201, 234 : 202, 235 : 203, 236 : 204, 237 : 205,
    238 : 206, 239 : 207, 240 : 208, 241 : 209, 242 : 210,
    243 : 211, 244 : 212, 245 : 213, 246 : 214, 248 : 216,
    249 : 217, 250 : 218, 251 : 219, 252 : 220, 253 : 221,
    254 : 222
    }

# current mappings, 256 chars long.
_to_upper = ""
_to_lower = ""

# translate table for converting strings to only contain valid input
# characters
_input_tbl = ""

# translate table that converts A-Z -> a-z, keeps a-z as they are, and
# converts everything else to z.
_normalize_tbl = ""

# identity table that maps each character to itself. used by deleteChars.
_identity_tbl = ""

# map some fancy unicode characters to their nearest ASCII/Latin-1
# equivalents so when people import text it's not mangled to uselessness
_fancy_unicode_map = {
    ord(u"‘") : u"'",
    ord(u"’") : u"'",
    ord(u"“") : u'"',
    ord(u"”") : u'"',
    ord(u"—") : u"--",
    ord(u"–") : u"-",
    }

# permanent memory DC to get text extents etc
permDc = None

def init(doWX = True):
    global _to_upper, _to_lower, _input_tbl, _normalize_tbl, _identity_tbl, \
           permDc

    # setup ISO-8859-1 case-conversion stuff
    tmpUpper = []
    tmpLower = []

    for i in range(256):
        tmpUpper.append(i)
        tmpLower.append(i)

    for k, v in _iso_8859_1_map.iteritems():
        tmpUpper[k] = v
        tmpLower[v] = k

    for i in range(256):
        _to_upper += chr(tmpUpper[i])
        _to_lower += chr(tmpLower[i])

    # valid input string stuff
    for i in range(256):
        if isValidInputChar(i):
            _input_tbl += chr(i)
        else:
            _input_tbl += "|"

    for i in range(256):
        # "a" - "z"
        if (i >= 97) and (i <= 122):
            ch = chr(i)
        # "A" - "Z"
        elif (i >= 65) and (i <= 90):
            # + 32 ("A" - "a") lowercases it
            ch = chr(i + 32)
        else:
            ch = "z"

        _normalize_tbl += ch

    _identity_tbl = "".join([chr(i) for i in range(256)])

    if doWX:
        # dunno if the bitmap needs to be big enough to contain the text
        # we're measuring...
        permDc = wx.MemoryDC()
        permDc.SelectObject(wx.EmptyBitmap(512, 32))

# like string.upper/lower/capitalize, but we do our own charset-handling
# that doesn't need locales etc
def upper(s):
    return s.translate(_to_upper)

def lower(s):
    return s.translate(_to_lower)

def capitalize(s):
    return upper(s[:1]) + s[1:]

# return 's', which must be a unicode string, converted to a ISO-8859-1
# 8-bit string. characters not representable in ISO-8859-1 are discarded.
def toLatin1(s):
    return s.encode("ISO-8859-1", "ignore")

# return 's', which must be a string of ISO-8859-1 characters, converted
# to UTF-8.
def toUTF8(s):
    return unicode(s, "ISO-8859-1").encode("UTF-8")

# return 's', which must be a string of UTF-8 characters, converted to
# ISO-8859-1, with characters not representable in ISO-8859-1 discarded
# and any invalid UTF-8 sequences ignored.
def fromUTF8(s):
    return s.decode("UTF-8", "ignore").encode("ISO-8859-1", "ignore")

# returns True if kc (key-code) is a valid character to add to the script.
def isValidInputChar(kc):
    # [0x80, 0x9F] = unspecified control characters in ISO-8859-1, added
    # characters like euro etc in windows-1252. 0x7F = backspace, 0xA0 =
    # non-breaking space, 0xAD = soft hyphen.
    return (kc >= 32) and (kc <= 255) and not\
           ((kc >= 0x7F) and (kc < 0xA0)) and (kc != 0xAD)

# return s with all non-valid input characters converted to valid input
# characters, except form feeds, which are just deleted.
def toInputStr(s):
    return s.translate(_input_tbl, "\f")

# replace fancy unicode characters with their ASCII/Latin1 equivalents.
def removeFancyUnicode(s):
    return s.translate(_fancy_unicode_map)

# transform external input (unicode) into a form suitable for having in a
# script
def cleanInput(s):
    return toInputStr(toLatin1(removeFancyUnicode(s)))

# replace s[start:start + width] with toInputStr(new) and return s
def replace(s, new, start, width):
    return s[0 : start] + toInputStr(new) + s[start + width:]

# delete all characters in 'chars' (a string) from s and return that.
def deleteChars(s, chars):
    return s.translate(_identity_tbl, chars)

# returns s with all possible different types of newlines converted to
# unix newlines, i.e. a single "\n"
def fixNL(s):
    return s.replace("\r\n", "\n").replace("\r", "\n")

# clamps the given value to a specific range. both limits are optional.
def clamp(val, minVal = None, maxVal = None):
    ret = val

    if minVal != None:
        ret = max(ret, minVal)

    if maxVal != None:
        ret = min(ret, maxVal)

    return ret

# like clamp, but gets/sets value directly from given object
def clampObj(obj, name, minVal = None, maxVal = None):
    setattr(obj, name, clamp(getattr(obj, name), minVal, maxVal))

# convert given string to float, clamping it to the given range
# (optional). never throws any exceptions, return defVal (possibly clamped
# as well) on any errors.
def str2float(s, defVal, minVal = None, maxVal = None):
    val = defVal

    try:
        val = float(s)
    except (ValueError, OverflowError):
        pass

    return clamp(val, minVal, maxVal)

# like str2float, but for ints.
def str2int(s, defVal, minVal = None, maxVal = None, radix = 10):
    val = defVal

    try:
        val = int(s, radix)
    except ValueError:
        pass

    return clamp(val, minVal, maxVal)

# extract 'name' field from each item in 'seq', put it in a list, and
# return that list.
def listify(seq, name):
    l = []
    for it in seq:
        l.append(getattr(it, name))

    return l

# return percentage of 'val1' of 'val2' (both ints) as an int (50% -> 50
# etc.), or 0 if val2 is 0.
def pct(val1, val2):
    if val2 != 0:
        return (100 * val1) // val2
    else:
        return 0

# return percentage of 'val1' of 'val2' (both ints/floats) as a float (50%
# -> 50.0 etc.), or 0.0 if val2 is 0.0
def pctf(val1, val2):
    if val2 != 0.0:
        return (100.0 * val1) / val2
    else:
        return 0.0

# return float(val1) / val2, or 0.0 if val2 is 0.0
def safeDiv(val1, val2):
    if val2 != 0.0:
        return float(val1) / val2
    else:
        return 0.0

# return float(val1) / val2, or 0.0 if val2 is 0
def safeDivInt(val1, val2):
    if val2 != 0:
        return float(val1) / val2
    else:
        return 0.0

# for each character in 'flags', starting at beginning, checks if that
# character is found in 's'. if so, appends True to a tuple, False
# otherwise. returns that tuple, whose length is of course is len(flags).
def flags2bools(s, flags):
    b = ()

    for f in flags:
        if s.find(f) != -1:
            b += (True,)
        else:
            b += (False,)

    return b

# reverse of flags2bools. is given a number of objects, if each object
# evaluates to true, chars[i] is appended to the return string. len(chars)
# == len(bools) must be true.
def bools2flags(chars, *bools):
    s = ""

    if len(chars) != len(bools):
        raise TypeError("bools2flags: chars and bools are not equal length")

    for i in range(len(chars)):
        if bools[i]:
            s += chars[i]

    return s

# return items, which is a list of ISO-8859-1 strings, as a single string
# with \n between each string. any \ characters in the individual strings
# are escaped as \\.
def escapeStrings(items):
    return "\\n".join([s.replace("\\", "\\\\") for s in items])

# opposite of escapeStrings. takes in a string, returns a list of strings.
def unescapeStrings(s):
    if not s:
        return []

    items = []

    tmp = ""
    i = 0
    while i < (len(s) - 1):
        ch = s[i]

        if ch != "\\":
            tmp += ch
            i += 1
        else:
            ch = s[i + 1]

            if ch == "n":
                items.append(tmp)
                tmp = ""
            else:
                tmp += ch

            i += 2

    if i < len(s):
        tmp += s[i]
        items.append(tmp)

    return items

# return s encoded so that all characters outside the range [32,126] (and
# "\\") are escaped.
def encodeStr(s):
    ret = ""

    for ch in s:
        c = ord(ch)

        # ord("\\") == 92 == 0x5C
        if c == 92:
            ret += "\\5C"
        elif (c >= 32) and (c <= 126):
            ret += ch
        else:
            ret += "\\%02X" % c

    return ret

# reverse of encodeStr. if string contains invalid escapes, they're
# silently and arbitrarily replaced by something.
def decodeStr(s):
    return re.sub(r"\\..", _decodeRepl, s)

# converts "\A4" style matches to their character values.
def _decodeRepl(mo):
    val = str2int(mo.group(0)[1:], 256, 0, 256, 16)

    if val != 256:
        return chr(val)
    else:
        return ""

# return string s escaped for use in RTF.
def escapeRTF(s):
    return s.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")

# convert mm to twips (1/1440 inch = 1/20 point).
def mm2twips(mm):
    # 56.69291 = 1440 / 25.4
    return mm * 56.69291

# TODO: move all GUI stuff to gutil

# return True if given font is a fixed-width one.
def isFixedWidth(font):
    return getTextExtent(font, "iiiii")[0] == getTextExtent(font, "OOOOO")[0]

# get extent of 's' as (w, h)
def getTextExtent(font, s):
    permDc.SetFont(font)

    # if we simply return permDc.GetTextExtent(s) from here, on some
    # versions of Windows we will incorrectly reject as non-fixed width
    # fonts (through isFixedWidth) some fonts that actually are fixed
    # width. it's especially bad because one of them is our default font,
    # "Courier New".
    #
    # these are the widths we get for the strings below for Courier New, italic:
    #
    # iiiii 40
    # iiiiiiiiii 80
    # OOOOO 41
    # OOOOOOOOOO 81
    #
    # we can see i and O are both 8 pixels wide, so the font is
    # fixed-width, but for whatever reason, on the O variants there is one
    # additional pixel returned in the width, no matter what the length of
    # the string is.
    #
    # to get around this, we actually call GetTextExtent twice, once with
    # the actual string we want to measure, and once with the string
    # duplicated, and take the difference between those two as the actual
    # width. this handily negates the one-extra-pixel returned and gives
    # us an accurate way of checking if a font is fixed width or not.
    #
    # it's a bit slower but this is not called from anywhere that's
    # performance critical.

    w1, h = permDc.GetTextExtent(s)
    w2 = permDc.GetTextExtent(s + s)[0]

    return (w2 - w1, h)

# get height of font in pixels
def getFontHeight(font):
    permDc.SetFont(font)
    return permDc.GetTextExtent("_\xC5")[1]

# return how many mm tall given font size is.
def getTextHeight(size):
    return (size / 72.0) * 25.4

# return how many mm wide given text is at given style with given size.
def getTextWidth(text, style, size):
    return (fontinfo.getMetrics(style).getTextWidth(text, size) / 72.0) * 25.4

# create a font that's height is at most 'height' pixels. other parameters
# are the same as in wx.Font's constructor.
def createPixelFont(height, family, style, weight):
    fs = 6

    selected = fs
    closest = 1000
    over = 0

    # FIXME: what's this "keep trying even once we go over the max height"
    # stuff? get rid of it.
    while 1:
        fn = wx.Font(fs, family, style, weight,
                     encoding = wx.FONTENCODING_ISO8859_1)
        h = getFontHeight(fn)
        diff = height -h

        if diff >= 0:
            if diff < closest:
                closest = diff
                selected = fs
        else:
            over += 1

        if (over >= 3) or (fs > 144):
            break

        fs += 2

    return wx.Font(selected, family, style, weight,
                   encoding = wx.FONTENCODING_ISO8859_1)

def reverseComboSelect(combo, clientData):
    for i in range(combo.GetCount()):
        if combo.GetClientData(i) == clientData:
            if combo.GetSelection() != i:
                combo.SetSelection(i)

            return True

    return False

# set widget's client size. if w or h is -1, that dimension is not changed.
def setWH(ctrl, w = -1, h = -1):
    size = ctrl.GetClientSize()

    if w != -1:
        size.width = w

    if h != -1:
        size.height = h

    ctrl.SetMinSize(wx.Size(size.width, size.height))
    ctrl.SetClientSizeWH(size.width, size.height)

# wxMSW doesn't respect the control's min/max values at all, so we have to
# implement this ourselves
def getSpinValue(spinCtrl):
    tmp = clamp(spinCtrl.GetValue(), spinCtrl.GetMin(), spinCtrl.GetMax())
    spinCtrl.SetValue(tmp)

    return tmp

# return True if c is not a word character, i.e. is either empty, not an
# alphanumeric character or a "'", or is more than one character.
def isWordBoundary(c):
    if len(c) != 1:
        return True

    if c == "'":
        return False

    return not isAlnum(c)

# return True if c is an alphanumeric character
def isAlnum(c):
    return unicode(c, "ISO-8859-1").isalnum()

# make sure s (unicode) ends in suffix (case-insensitively) and return
# that. suffix must already be lower-case.
def ensureEndsIn(s, suffix):
    if s.lower().endswith(suffix):
        return s
    else:
        return s + suffix

# return string 's' split into words (as a list), using isWordBoundary.
def splitToWords(s):
    tmp = ""

    for c in s:
        if isWordBoundary(c):
            tmp += " "
        else:
            tmp += c

    return tmp.split()

# return two-character prefix of s, using characters a-z only. len(s) must
# be at least 2.
def getWordPrefix(s):
    return s[:2].translate(_normalize_tbl)

# return count of how many 'ch' characters 's' begins with.
def countInitial(s, ch):
    cnt = 0

    for i in range(len(s)):
        if s[i] != ch:
            break

        cnt += 1

    return cnt

# searches string 's' for each item of list 'seq', returning True if any
# of them were found.
def multiFind(s, seq):
    for it in seq:
        if s.find(it) != -1:
            return True

    return False

# put everything from dictionary d into a list as (key, value) tuples,
# then sort the list and return that. by default sorts by "desc(value)
# asc(key)", but a custom sort function can be given
def sortDict(d, sortFunc = None):
    def tmpSortFunc(o1, o2):
        ret = cmp(o2[1], o1[1])

        if ret != 0:
            return ret
        else:
            return cmp(o1[0], o2[0])

    if sortFunc == None:
        sortFunc = tmpSortFunc

    tmp = []
    for k, v in d.iteritems():
        tmp.append((k, v))

    tmp.sort(sortFunc)

    return tmp

# an efficient FIFO container of fixed size. can't contain None objects.
class FIFO:
    def __init__(self, size):
        self.arr = [None] * size

        # index of next slot to fill
        self.next = 0

    # add item
    def add(self, obj):
        self.arr[self.next] = obj
        self.next += 1

        if self.next >= len(self.arr):
            self.next = 0

    # get contents as a list, in LIFO order.
    def get(self):
        tmp = []

        j = self.next - 1

        for i in range(len(self.arr)):
            if j < 0:
                j = len(self.arr) - 1

            obj = self.arr[j]

            if  obj != None:
                tmp.append(obj)

            j -= 1

        return tmp

# DrawLine-wrapper that makes it easier when the end-point is just
# offsetted from the starting point
def drawLine(dc, x, y, xd, yd):
    dc.DrawLine(x, y, x + xd, y + yd)

# draws text aligned somehow. returns a (w, h) tuple of the text extent.
def drawText(dc, text, x, y, align = ALIGN_LEFT, valign = VALIGN_TOP):
    w, h = dc.GetTextExtent(text)

    if align == ALIGN_CENTER:
        x -= w // 2
    elif align == ALIGN_RIGHT:
        x -= w

    if valign == VALIGN_CENTER:
        y -= h // 2
    elif valign == VALIGN_BOTTOM:
        y -= h

    dc.DrawText(text, x, y)

    return (w, h)

# create pad sizer for given window whose controls are in topSizer, with
# 'pad' pixels of padding on each side, resize window to correct size, and
# optionally center it.
def finishWindow(window, topSizer, pad = 10, center = True):
    padSizer = wx.BoxSizer(wx.VERTICAL)
    padSizer.Add(topSizer, 1, wx.EXPAND | wx.ALL, pad)
    window.SetSizerAndFit(padSizer)
    window.Layout()

    if center:
        window.Center()

# wx.Colour replacement that can safely be copy.deepcopy'd
class MyColor:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def toWx(self):
        return wx.Colour(self.r, self.g, self.b)

    @staticmethod
    def fromWx(c):
        o = MyColor(0, 0, 0)

        o.r = c.Red()
        o.g = c.Green()
        o.b = c.Blue()

        return o

# fake key event, supports same operations as the real one
class MyKeyEvent:
    def __init__(self, kc = 0):
        # keycode
        self.kc = kc

        self.controlDown = False
        self.altDown = False
        self.shiftDown = False

    def GetKeyCode(self):
        return self.kc

    def ControlDown(self):
        return self.controlDown

    def AltDown(self):
        return self.altDown

    def ShiftDown(self):
        return self.shiftDown

    def Skip(self):
        pass

# one key press
class Key:
    keyMap = {
        1 : "A",
        2 : "B",
        3 : "C",
        4 : "D",
        5 : "E",
        6 : "F",
        7 : "G",

        # CTRL+Enter = 10 in Windows
        10 : "Enter (Windows)",

        11 : "K",
        12 : "L",
        14 : "N",
        15 : "O",
        16 : "P",
        17 : "Q",
        18 : "R",
        19 : "S",
        20 : "T",
        21 : "U",
        22 : "V",
        23 : "W",
        24 : "X",
        25 : "Y",
        26 : "Z",
        wx.WXK_BACK : "Backspace",
        wx.WXK_TAB : "Tab",
        wx.WXK_RETURN : "Enter",
        wx.WXK_ESCAPE : "Escape",
        wx.WXK_DELETE : "Delete",
        wx.WXK_END : "End",
        wx.WXK_HOME : "Home",
        wx.WXK_LEFT : "Left",
        wx.WXK_UP : "Up",
        wx.WXK_RIGHT : "Right",
        wx.WXK_DOWN : "Down",
        wx.WXK_PAGEUP : "Page up",
        wx.WXK_PAGEDOWN : "Page down",
        wx.WXK_INSERT : "Insert",
        wx.WXK_F1 : "F1",
        wx.WXK_F2 : "F2",
        wx.WXK_F3 : "F3",
        wx.WXK_F4 : "F4",
        wx.WXK_F5 : "F5",
        wx.WXK_F6 : "F6",
        wx.WXK_F7 : "F7",
        wx.WXK_F8 : "F8",
        wx.WXK_F9 : "F9",
        wx.WXK_F10 : "F10",
        wx.WXK_F11 : "F11",
        wx.WXK_F12 : "F12",
        wx.WXK_F13 : "F13",
        wx.WXK_F14 : "F14",
        wx.WXK_F15 : "F15",
        wx.WXK_F16 : "F16",
        wx.WXK_F17 : "F17",
        wx.WXK_F18 : "F18",
        wx.WXK_F19 : "F19",
        wx.WXK_F20 : "F20",
        wx.WXK_F21 : "F21",
        wx.WXK_F22 : "F22",
        wx.WXK_F23 : "F23",
        wx.WXK_F24 : "F24",
        }

    def __init__(self, kc, ctrl = False, alt = False, shift = False):

        # we don't want to handle ALT+a/ALT+A etc separately, so uppercase
        # input char combinations
        if (kc < 256) and (ctrl or alt):
            kc = ord(upper(chr(kc)))

        # even though the wxWidgets documentation clearly states that
        # CTRL+[A-Z] should be returned as keycodes 1-26, wxGTK2 2.6 does
        # not do this (wxGTK1 and wxMSG do follow the documentation).
        #
        # so, we normalize to the wxWidgets official form here if necessary.

        # "A" - "Z"
        if ctrl and (kc >= 65) and (kc <= 90):
            kc -= 64

        # ASCII/Latin-1 keycode (0-255) or one of the wx.WXK_ constants (>255)
        self.kc = kc

        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift

    # returns True if key is a valid input character
    def isValidInputChar(self):
        return not self.ctrl and not self.alt and isValidInputChar(self.kc)

    # toInt/fromInt serialize/deserialize to/from a 35-bit integer, laid
    # out like this:
    # bits 0-31:  keycode
    #        32:  Control
    #        33:  Alt
    #        34:  Shift

    def toInt(self):
        return (self.kc & 0xFFFFFFFFL) | (self.ctrl << 32L) | \
               (self.alt << 33L) | (self.shift << 34L)

    @staticmethod
    def fromInt(val):
        return Key(val & 0xFFFFFFFFL, (val >> 32) & 1, (val >> 33) & 1,
                   (val >> 34) & 1)

    # construct from wx.KeyEvent
    @staticmethod
    def fromKE(ev):
        return Key(ev.GetKeyCode(), ev.ControlDown(), ev.AltDown(),
                   ev.ShiftDown())

    def toStr(self):
        s = ""

        if self.ctrl:
            s += "CTRL+"

        if self.alt:
            s += "ALT+"

        if self.shift:
            s += "SHIFT+"

        if isValidInputChar(self.kc):
            if self.kc == wx.WXK_SPACE:
                s += "Space"
            else:
                s += chr(self.kc)
        else:
            kname = self.__class__.keyMap.get(self.kc)

            if kname:
                s += kname
            else:
                s += "UNKNOWN(%d)" % self.kc

        return s

# a string-like object that features reasonably fast repeated appends even
# for large strings, since it keeps each appended string as an item in a
# list.
class String:
    def __init__(self, s = None):

        # byte count of data appended
        self.pos = 0

        # list of strings
        self.data = []

        if s:
            self += s

    def __len__(self):
        return self.pos

    def __str__(self):
        return "".join(self.data)

    def __iadd__(self, s):
        s2 = str(s)

        self.data.append(s2)
        self.pos += len(s2)

        return self

# load at most maxSize (all if -1) bytes from 'filename', returning the
# data as a string or None on errors. pops up message boxes with 'frame'
# as parent on errors.
def loadFile(filename, frame, maxSize = -1):
    ret = None

    try:
        f = open(misc.toPath(filename), "rb")

        try:
            ret = f.read(maxSize)
        finally:
            f.close()

    except IOError, (errno, strerror):
        wx.MessageBox("Error loading file '%s': %s" % (
                filename, strerror), "Error", wx.OK, frame)
        ret = None

    return ret

# like loadFile, but if file doesn't exist, tries to load a .gz compressed
# version of it.
def loadMaybeCompressedFile(filename, frame):
    doGz = False

    if not fileExists(filename):
        filename += ".gz"
        doGz = True

    s = loadFile(filename, frame)
    if s is None:
        return None

    if not doGz:
        return s

    buf = StringIO.StringIO(s)

    # python's gzip module throws almost arbitrary exceptions in various
    # error conditions, so the only safe thing to do is to catch
    # everything.
    try:
        f = gzip.GzipFile(mode = "r", fileobj = buf)
        return f.read()
    except:
        wx.MessageBox("Error loading file '%s': Decompression failed" % \
                          filename, "Error", wx.OK, frame)

        return None

# write 'data' to 'filename', popping up a messagebox using 'frame' as
# parent on errors. returns True on success.
def writeToFile(filename, data, frame):
    try:
        f = open(misc.toPath(filename), "wb")

        try:
            f.write(data)
        finally:
            f.close()

        return True

    except IOError, (errno, strerror):
        wx.MessageBox("Error writing file '%s': %s" % (
                filename, strerror), "Error", wx.OK, frame)

        return False

def removeTempFiles(prefix):
    files = glob.glob(tempfile.gettempdir() + "/%s*" % prefix)

    for fn in files:
        try:
            os.remove(fn)
        except OSError:
            continue

# return True if given file exists.
def fileExists(filename):
    try:
        os.stat(misc.toPath(filename))
    except OSError:
        return False

    return True

# look for file 'filename' in all the directories listed in 'dirs', which
# is a list of absolute directory paths. if found, return the absolute
# filename, otherwise None.
def findFile(filename, dirs):
    for d in dirs:
        if d[-1] != u"/":
            d += u"/"

        path = d + filename

        if fileExists(path):
            return path

    return None

# look for file 'filename' in all the directories listed in $PATH. if
# found, return the absolute filename, otherwise None.
def findFileInPath(filename):
    dirs = os.getenv("PATH")
    if not dirs:
        return None

    # I have no idea how one should try to cope if PATH contains entries
    # with non-UTF8 characters, so just ignore any errors
    dirs = unicode(dirs, "UTF-8", "ignore").split(u":")

    # only accept absolute paths. this strips out things like "~/bin/"
    # etc.
    dirs = [d for d in dirs if d and d[0] == u"/"]

    return findFile(filename, dirs)

# simple timer class for use during development only
class TimerDev:

    # how many TimerDev instances are currently in existence
    nestingLevel = 0

    def __init__(self, msg = ""):
        self.msg = msg
        self.__class__.nestingLevel += 1
        self.t = time.time()

    def __del__(self):
        self.t = time.time() - self.t
        self.__class__.nestingLevel -= 1
        print "%s%s took %.5f seconds" % (" " * self.__class__.nestingLevel,
                                          self.msg, self.t)

# Get the Windows default PDF viewer path from registry and return that,
# or None on errors.
def getWindowsPDFViewer():
    try:
        import _winreg

        # HKCR/.pdf: gives the class of the PDF program.
        # Example : AcroRead.Document or FoxitReader.Document

        key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, ".pdf")
        pdfClass = _winreg.QueryValue(key, "")

        # HKCR/<class>/shell/open/command: the path to the PDF viewer program
        # Example: "C:\Program Files\Acrobat 8.0\acroread.exe" "%1"

        key2 = _winreg.OpenKey(
            _winreg.HKEY_CLASSES_ROOT, pdfClass + r"\shell\open\command")

        # Almost every PDF program out there accepts passing the PDF path
        # as the argument, so we don't parse the arguments from the
        # registry, just get the program path.

        path = _winreg.QueryValue(key2, "").split('"')[1]

        if fileExists(path):
            return path
    except:
        pass

    return None

# get a windows environment variable in its native unicode format, or None
# if not found
def getWindowsUnicodeEnvVar(name):
    import ctypes

    n = ctypes.windll.kernel32.GetEnvironmentVariableW(name, None, 0)

    if n == 0:
        return None

    buf = ctypes.create_unicode_buffer(u"\0" * n)
    ctypes.windll.kernel32.GetEnvironmentVariableW(name, buf, n)

    return buf.value

# show PDF file.
def showPDF(filename, cfgGl, frame):
    def complain():
        wx.MessageBox("PDF viewer application not found.\n\n"
                      "You can change your PDF viewer\n"
                      "settings at File/Settings/Change/Misc.",
                      "Error", wx.OK, frame)

    pdfProgram = cfgGl.pdfViewerPath
    pdfArgs = cfgGl.pdfViewerArgs

    # If configured pdf viewer does not exist, try finding one
    # automatically
    if not fileExists(pdfProgram):
        found = False

        if misc.isWindows:
            regPDF = getWindowsPDFViewer()

            if regPDF:
                wx.MessageBox(
                    "Currently set PDF viewer (%s) was not found.\n"
                    "Change this in File/Settings/Change/Misc.\n\n"
                    "Using the default PDF viewer for Windows instead:\n"
                    "%s" % (pdfProgram, regPDF),
                    "Warning", wx.OK, frame)

                pdfProgram = regPDF
                pdfArgs = ""

                found = True

        if not found:
            complain()

            return

    # on Windows, Acrobat complains about "invalid path" if we
    # give the full path of the program as first arg, so give a
    # dummy arg.
    args = ["pdf"] + pdfArgs.split() + [filename]

    # there's a race condition in checking if the path exists, above, and
    # using it, below. if the file disappears between those two we get an
    # OSError exception from spawnv, so we need to catch it and handle it.

    # TODO: spawnv does not support Unicode paths as of this moment
    # (Python 2.4). for now, convert it to UTF-8 and hope for the best.
    try:
        os.spawnv(os.P_NOWAIT, pdfProgram.encode("UTF-8"), args)
    except OSError:
        complain()

########NEW FILE########
__FILENAME__ = viewmode
# -*- coding: iso-8859-1 -*-

import config
import mypager
import pml
import util

import wx

# Number of lines the smooth scroll will try to search. 15-20 is a good
# number to use with the layout mode margins we have.
MAX_JUMP_DISTANCE = 17

# a piece of text on screen.
class TextString:
    def __init__(self, line, text, x, y, fi, isUnderlined):

        # if this object is a screenplay line, this is the index of the
        # corresponding line in the Screenplay.lines list. otherwise this
        # is -1 (used for stuff like CONTINUED: etc).
        self.line = line

        # x,y coordinates in pixels from widget's topleft corner
        self.x = x
        self.y = y

        # text and its config.FontInfo and underline status
        self.text = text
        self.fi = fi
        self.isUnderlined = isUnderlined

# a page shown on screen.
class DisplayPage:
    def __init__(self, pageNr, x1, y1, x2, y2):

        # page number (index in MyCtrl.pages)
        self.pageNr = pageNr

        # coordinates in pixels
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

# caches pml.Pages for operations that repeatedly construct them over and
# over again without the page contents changing.
class PageCache:
    def __init__(self, ctrl):
        self.ctrl = ctrl

        # cached pages. key = pageNr, value = pml.Page
        self.pages = {}

    def getPage(self, pager, pageNr):
        pg = self.pages.get(pageNr)

        if not pg:
            pg = self.ctrl.sp.generatePMLPage(pager, pageNr, False, False)
            self.pages[pageNr] = pg

        return pg

# View Mode, i.e. a way of displaying the script on screen. this is an
# abstract superclass.
class ViewMode:

    # get a description of what the current screen contains. returns
    # (texts, dpages), where texts = [TextString, ...], dpages =
    # [DisplayPage, ...]. dpages is None if draft mode is in use or
    # doExtra is False. doExtra has same meaning as for generatePMLPage
    # otherwise. pageCache, if given, is used in layout mode to cache PML
    # pages. it should only be given when doExtra = False as the cached
    # pages aren't accurate down to that level.
    #
    # partial lines (some of the the text is clipped off-screen) are only
    # included in the results if 'partials' is True.
    #
    # lines in 'texts' have to be in monotonically increasing order, and
    # this has to always return at least one line.
    def getScreen(self, ctrl, doExtra, partials = False, pageCache = None):
        raise Exception("getScreen not implemented")

    # return height for one line on screen
    def getLineHeight(self, ctrl):
        raise Exception("getLineHeight not implemented")

    # return width of one page in (floating point) pixels
    def getPageWidth(self, ctrl):
        raise Exception("getPageWidth not implemented")

    # see MyCtrl.OnPaint for what tl is. note: this is only a default
    # implementation, feel free to override this.
    def drawTexts(self, ctrl, dc, tl):
        dc.SetFont(tl[0])
        dc.DrawTextList(tl[1][0], tl[1][1], tl[1][2])

    # determine what (line, col) is at position (x, y) (screen
    # coordinates) and return that, or (None, None) if (x, y) points
    # outside a page.
    def pos2linecol(self, ctrl, x, y):
        raise Exception("pos2linecol not implemented")

    # make line, which is not currently visible, visible. texts =
    # self.getScreen(ctrl, False)[0].
    def makeLineVisible(self, ctrl, line, texts, direction = config.SCROLL_CENTER):
        raise Exception("makeLineVisible not implemented")

    # handle page up (dir == -1) or page down (dir == 1) command. cursor
    # is guaranteed to be visible when this is called, and auto-completion
    # to be off. cs = CommandState. texts and dpages are the usual.
    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        raise Exception("pageCmd not implemented")

    # semi-generic implementation, for use by Draft and Layout modes.
    def pos2linecolGeneric(self, ctrl, x, y):
        sel = None
        lineh = self.getLineHeight(ctrl)

        for t in self.getScreen(ctrl, False, True)[0]:
            if t.line == -1:
                continue

            sel = t

            if (t.y + lineh) > y:
                break

        if sel == None:
            return (None, None)

        line = sel.line
        l = ctrl.sp.lines[line]

        column = util.clamp(int((x - sel.x) / sel.fi.fx), 0, len(l.text))

        return (line, column)

    # semi-generic implementation, for use by Draft and Layout modes.
    def makeLineVisibleGeneric(self, ctrl, line, texts, direction, jumpAhead):
        if not ctrl.sp.cfgGl.recenterOnScroll and (direction != config.SCROLL_CENTER):
            if self._makeLineVisibleHelper(ctrl, line, direction, jumpAhead):
                return

        # smooth scrolling not in operation (or failed), recenter screen
        ctrl.sp.setTopLine(max(0, int(line - (len(texts) * 0.5))))

        if not ctrl.isLineVisible(line):
            ctrl.sp.setTopLine(line)

    # helper function for makeLineVisibleGeneric
    def _makeLineVisibleHelper(self, ctrl, line, direction, jumpAhead):
        startLine = ctrl.sp.getTopLine()
        sign = 1 if (direction == config.SCROLL_DOWN) else -1
        i = 1

        while not ctrl.isLineVisible(line):
            ctrl.sp.setTopLine(startLine + i * sign)
            i += jumpAhead

            if i > MAX_JUMP_DISTANCE:
                return False

        return True

    # semi-generic implementation, for use by Draft and Layout modes.
    def pageCmdGeneric(self, ctrl, cs, dir, texts, dpages):
        if dir > 0:
            line = texts[-1].line
            ctrl.sp.line = line
            ctrl.sp.setTopLine(line)
        else:
            tl = ctrl.sp.getTopLine()
            if tl == texts[-1].line:
                ctrl.sp.setTopLine(tl - 5)
            else:
                ctrl.sp.line = tl

                pc = PageCache(ctrl)

                while 1:
                    tl = ctrl.sp.getTopLine()
                    if tl == 0:
                        break

                    texts = self.getScreen(ctrl, False, False, pc)[0]
                    lastLine = texts[-1].line

                    if ctrl.sp.line > lastLine:
                        # line scrolled off screen, back up one line
                        ctrl.sp.setTopLine(tl + 1)
                        break

                    ctrl.sp.setTopLine(tl - 1)

            cs.needsVisifying = False

# Draft view mode. No fancy page break layouts, just text lines on a plain
# background.
class ViewModeDraft(ViewMode):

    def getScreen(self, ctrl, doExtra, partials = False, pageCache = None):
        cfg = ctrl.sp.cfg
        cfgGui = ctrl.getCfgGui()

        width, height = ctrl.GetClientSizeTuple()
        ls = ctrl.sp.lines
        y = 15
        i = ctrl.sp.getTopLine()

        marginLeft = int(ctrl.mm2p * cfg.marginLeft)
        cox = util.clamp((width - ctrl.pageW) // 2, 0)
        fyd = ctrl.sp.cfgGl.fontYdelta
        length = len(ls)

        texts = []

        while (y < height) and (i < length):
            y += int((ctrl.sp.getSpacingBefore(i) / 10.0) * fyd)

            if y >= height:
                break

            if not partials and ((y + fyd) > height):
                break

            l = ls[i]
            tcfg = cfg.getType(l.lt)

            if tcfg.screen.isCaps:
                text = util.upper(l.text)
            else:
                text = l.text

            fi = cfgGui.tt2fi(tcfg.screen)

            extraIndent = 1 if ctrl.sp.needsExtraParenIndent(i) else 0

            texts.append(TextString(i, text,
                cox + marginLeft + (tcfg.indent + extraIndent) * fi.fx, y, fi,
                tcfg.screen.isUnderlined))

            y += fyd
            i += 1

        return (texts, [])

    def getLineHeight(self, ctrl):
        return ctrl.sp.cfgGl.fontYdelta

    def getPageWidth(self, ctrl):
        # this is not really used for much in draft mode, as it has no
        # concept of page width, but it's safer to return something
        # anyway.
        return (ctrl.sp.cfg.paperWidth / ctrl.chX) *\
               ctrl.getCfgGui().fonts[pml.NORMAL].fx

    def pos2linecol(self, ctrl, x, y):
        return self.pos2linecolGeneric(ctrl, x, y)

    def makeLineVisible(self, ctrl, line, texts, direction = config.SCROLL_CENTER):
        self.makeLineVisibleGeneric(ctrl, line, texts, direction, jumpAhead = 1)

    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        self.pageCmdGeneric(ctrl, cs, dir, texts, dpages)

# Layout view mode. Pages are shown with the actual layout they would
# have.
class ViewModeLayout(ViewMode):

    def getScreen(self, ctrl, doExtra, partials = False, pageCache = None):
        cfgGui = ctrl.getCfgGui()
        textOp = pml.TextOp

        texts = []
        dpages = []

        width, height = ctrl.GetClientSizeTuple()

        # gap between pages (pixels)
        pageGap = 10
        pager = mypager.Pager(ctrl.sp.cfg)

        mm2p = ctrl.mm2p
        fontY = cfgGui.fonts[pml.NORMAL].fy

        cox = util.clamp((width - ctrl.pageW) // 2, 0)

        y = 0
        topLine = ctrl.sp.getTopLine()
        pageNr = ctrl.sp.line2page(topLine)

        if doExtra and ctrl.sp.cfg.pdfShowSceneNumbers:
            pager.scene = ctrl.sp.getSceneNumber(
                ctrl.sp.page2lines(pageNr)[0] - 1)

        # find out starting place (if something bugs, generatePMLPage
        # below could return None, but it shouldn't happen...)
        if pageCache:
            pg = pageCache.getPage(pager, pageNr)
        else:
            pg = ctrl.sp.generatePMLPage(pager, pageNr, False, doExtra)

        topOfPage = True
        for op in pg.ops:
            if not isinstance(op, textOp) or (op.line == -1):
                continue

            if op.line == topLine:
                if not topOfPage:
                    y = -int(op.y * mm2p)
                else:
                    y = pageGap

                break
            else:
                topOfPage = False

        # create pages, convert them to display format, repeat until
        # script ends or we've filled the display.

        done = False
        while 1:
            if done or (y >= height):
                break

            if not pg:
                pageNr += 1
                if pageNr >= len(ctrl.sp.pages):
                    break

                # we'd have to go back an arbitrary number of pages to
                # get an accurate number for this in the worst case,
                # so disable it altogether.
                pager.sceneContNr = 0

                if pageCache:
                    pg = pageCache.getPage(pager, pageNr)
                else:
                    pg = ctrl.sp.generatePMLPage(pager, pageNr, False,
                                                 doExtra)
                if not pg:
                    break

            dp = DisplayPage(pageNr, cox, y, cox + ctrl.pageW,
                             y + ctrl.pageH)
            dpages.append(dp)

            pageY = y

            for op in pg.ops:
                if not isinstance(op, textOp):
                    continue

                ypos = int(pageY + op.y * mm2p)

                if ypos < 0:
                    continue

                y = max(y, ypos)

                if (y >= height) or (not partials and\
                                     ((ypos + fontY) > height)):
                    done = True
                    break

                texts.append(TextString(op.line, op.text,
                                        int(cox + op.x * mm2p), ypos,
                                        cfgGui.fonts[op.flags & 3],
                                        op.flags & pml.UNDERLINED))

            y = pageY + ctrl.pageH + pageGap
            pg = None

        # if user has inserted new text causing the script to overflow
        # the last page, we need to make the last page extra-long on
        # the screen.
        if dpages and texts and (pageNr >= (len(ctrl.sp.pages) - 1)):

            lastY = texts[-1].y + fontY
            if lastY >= dpages[-1].y2:
                dpages[-1].y2 = lastY + 10

        return (texts, dpages)

    def getLineHeight(self, ctrl):
        # the + 1.0 avoids occasional non-consecutive backgrounds for
        # lines.
        return int(ctrl.chY * ctrl.mm2p + 1.0)

    def getPageWidth(self, ctrl):
        return (ctrl.sp.cfg.paperWidth / ctrl.chX) *\
               ctrl.getCfgGui().fonts[pml.NORMAL].fx

    def pos2linecol(self, ctrl, x, y):
        return self.pos2linecolGeneric(ctrl, x, y)

    def makeLineVisible(self, ctrl, line, texts, direction = config.SCROLL_CENTER):
        self.makeLineVisibleGeneric(ctrl, line, texts, direction, jumpAhead = 3)

    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        self.pageCmdGeneric(ctrl, cs, dir, texts, dpages)

# Side by side view mode. Pages are shown with the actual layout they
# would have, as many pages at a time as fit on the screen, complete pages
# only, in a single row.
class ViewModeSideBySide(ViewMode):

    def getScreen(self, ctrl, doExtra, partials = False, pageCache = None):
        cfgGui = ctrl.getCfgGui()
        textOp = pml.TextOp

        texts = []
        dpages = []

        width, height = ctrl.GetClientSizeTuple()

        mm2p = ctrl.mm2p

        # gap between pages (+ screen left edge)
        pageGap = 10

        # how many pages fit on screen
        pageCnt = max(1, (width - pageGap) // (ctrl.pageW + pageGap))

        pager = mypager.Pager(ctrl.sp.cfg)

        topLine = ctrl.sp.getTopLine()
        pageNr = ctrl.sp.line2page(topLine)

        if doExtra and ctrl.sp.cfg.pdfShowSceneNumbers:
            pager.scene = ctrl.sp.getSceneNumber(
                ctrl.sp.page2lines(pageNr)[0] - 1)

        pagesDone = 0

        while 1:
            if (pagesDone >= pageCnt) or (pageNr >= len(ctrl.sp.pages)):
                break

            # we'd have to go back an arbitrary number of pages to get an
            # accurate number for this in the worst case, so disable it
            # altogether.
            pager.sceneContNr = 0

            if pageCache:
                pg = pageCache.getPage(pager, pageNr)
            else:
                pg = ctrl.sp.generatePMLPage(pager, pageNr, False,
                                             doExtra)
            if not pg:
                break

            sx = pageGap + pagesDone * (ctrl.pageW + pageGap)
            sy = pageGap

            dp = DisplayPage(pageNr, sx, sy, sx + ctrl.pageW,
                             sy + ctrl.pageH)
            dpages.append(dp)

            for op in pg.ops:
                if not isinstance(op, textOp):
                    continue

                texts.append(TextString(op.line, op.text,
                    int(sx + op.x * mm2p), int(sy + op.y * mm2p),
                    cfgGui.fonts[op.flags & 3], op.flags & pml.UNDERLINED))

            pageNr += 1
            pagesDone += 1

        return (texts, dpages)

    def getLineHeight(self, ctrl):
        # the + 1.0 avoids occasional non-consecutive backgrounds for
        # lines.
        return int(ctrl.chY * ctrl.mm2p + 1.0)

    def getPageWidth(self, ctrl):
        return (ctrl.sp.cfg.paperWidth / ctrl.chX) *\
               ctrl.getCfgGui().fonts[pml.NORMAL].fx

    def pos2linecol(self, ctrl, x, y):
        lineh = self.getLineHeight(ctrl)
        ls = ctrl.sp.lines

        sel = None

        for t in self.getScreen(ctrl, False)[0]:
            if t.line == -1:
                continue

            # above or to the left
            if (x < t.x) or (y < t.y):
                continue

            # below
            if y > (t.y + lineh - 1):
                continue

            # to the right
            w = t.fi.fx * (len(ls[t.line].text) + 1)
            if x > (t.x + w - 1):
                continue

            sel = t
            break

        if sel == None:
            return (None, None)

        line = sel.line
        l = ls[line]

        column = util.clamp(int((x - sel.x) / sel.fi.fx), 0, len(l.text))

        return (line, column)

    def makeLineVisible(self, ctrl, line, texts, direction = config.SCROLL_CENTER):
        ctrl.sp.setTopLine(line)

    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        if dir < 0:
            pageNr = dpages[0].pageNr - len(dpages)
        else:
            pageNr = dpages[-1].pageNr + 1

        line = ctrl.sp.page2lines(pageNr)[0]

        ctrl.sp.line = line
        ctrl.sp.setTopLine(line)
        cs.needsVisifying = False

# Overview view mode. Very small pages with unreadable text are displayed
# in a grid.
class ViewModeOverview(ViewMode):
    def __init__(self, size):

        # each character is size x size pixels.
        self.size = size

    def getScreen(self, ctrl, doExtra, partials = False, pageCache = None):
        cfgGui = ctrl.getCfgGui()
        textOp = pml.TextOp

        texts = []
        dpages = []

        width, height = ctrl.GetClientSizeTuple()

        # gap between pages (+ screen left/top edge), both vertical/
        # horizontal (pixels)
        pageGap = 10

        # how many columns and rows
        cols = max(1, (width - pageGap) // (ctrl.pageW + pageGap))
        rows = max(1, (height - pageGap) // (ctrl.pageH + pageGap))
        pageCnt = cols * rows

        pager = mypager.Pager(ctrl.sp.cfg)
        fi = config.FontInfo()
        fi.font = cfgGui.fonts[pml.NORMAL].font
        fi.fx = fi.fy = self.size

        mm2p = ctrl.mm2p

        pageNr = ctrl.sp.line2page(ctrl.sp.getTopLine())
        pagesDone = 0

        while 1:
            if (pagesDone >= pageCnt) or (pageNr >= len(ctrl.sp.pages)):
                break

            if pageCache:
                pg = pageCache.getPage(pager, pageNr)
            else:
                pg = ctrl.sp.generatePMLPage(pager, pageNr, False,
                                             doExtra)
            if not pg:
                break

            xi = pagesDone % cols
            yi = pagesDone // cols

            sx = pageGap + xi * (ctrl.pageW + pageGap)
            sy = pageGap + yi * (ctrl.pageH + pageGap)

            dp = DisplayPage(pageNr, sx, sy, sx + ctrl.pageW,
                             sy + ctrl.pageH)
            dpages.append(dp)

            for op in pg.ops:
                if not isinstance(op, textOp):
                    continue

                texts.append(TextString(op.line, op.text,
                    int(sx + op.x * mm2p), int(sy + op.y * mm2p),
                    fi, False))

            pageNr += 1
            pagesDone += 1

        return (texts, dpages)

    def getLineHeight(self, ctrl):
        return self.size

    def getPageWidth(self, ctrl):
        return (ctrl.sp.cfg.paperWidth / ctrl.chX) * self.size

    def drawTexts(self, ctrl, dc, tl):
        for i in xrange(len(tl[1][0])):
            dc.SetPen(wx.Pen(tl[1][2][i]))

            s = tl[1][0][i]
            sx, sy = tl[1][1][i]

            for j in xrange(len(s)):
                if s[j] not in (" ", "�"):
                    off = sx + j * self.size

                    for x in range(self.size):
                        for y in range(self.size):
                            dc.DrawPoint(off + x, sy + y)

    # since the cursor is basically invisible anyway, we just return
    # (line, 0) where line = first line on the clicked page.
    def pos2linecol(self, ctrl, x, y):
        for dp in self.getScreen(ctrl, False)[1]:
            if (x < dp.x1) or (x > dp.x2) or (y < dp.y1) or (y > dp.y2):
                continue

            return (ctrl.sp.page2lines(dp.pageNr)[0], 0)

        return (None, None)

    def makeLineVisible(self, ctrl, line, texts, direction = config.SCROLL_CENTER):
        ctrl.sp.setTopLine(line)

    # not implemented for overview mode at least for now.
    def pageCmd(self, ctrl, cs, dir, texts, dpages):
        cs.needsVisifying = False

########NEW FILE########
__FILENAME__ = watermarkdlg
import pdf
import pml
import random
import util

import wx

# The watermark tool dialog.
class WatermarkDlg(wx.Dialog):
    # sp - screenplay object, from which to generate PDF
    # prefix - prefix name for the PDF files (unicode)
    def __init__(self, parent, sp, prefix):
        wx.Dialog.__init__(self, parent, -1, "Watermarked PDFs generator",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.frame = parent
        self.sp = sp

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Directory to save in:"), 0)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.dirEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.dirEntry, 1, wx.EXPAND)

        btn = wx.Button(self, -1, "Browse")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnBrowse)
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        vsizer.Add(wx.StaticText(self, -1, "Filename prefix:"), 0)
        self.filenamePrefix = wx.TextCtrl(self, -1, prefix)
        vsizer.Add(self.filenamePrefix, 0, wx.EXPAND | wx.BOTTOM, 5)

        vsizer.Add(wx.StaticText(self, -1, "Watermark font size:"), 0)
        self.markSize = wx.SpinCtrl(self, -1, size=(60, -1))
        self.markSize.SetRange(20, 80)
        self.markSize.SetValue(40)
        vsizer.Add(self.markSize, 0, wx.BOTTOM, 5)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        vsizer.Add(wx.StaticText(self, -1, "Common mark:"), 0)
        self.commonMark = wx.TextCtrl(self, -1, "Confidential")
        vsizer.Add(self.commonMark, 0, wx.EXPAND| wx.BOTTOM, 5)

        vsizer.Add(wx.StaticText(self, -1, "Watermarks (one per line):"))
        self.itemsEntry = wx.TextCtrl(
            self, -1, style = wx.TE_MULTILINE | wx.TE_DONTWRAP,
            size = (300, 200))
        vsizer.Add(self.itemsEntry, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        closeBtn = wx.Button(self, -1, "Close")
        hsizer.Add(closeBtn, 0)
        hsizer.Add((1, 1), 1)
        generateBtn = wx.Button(self, -1, "Generate PDFs")
        hsizer.Add(generateBtn, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, closeBtn.GetId(), self.OnClose)
        wx.EVT_BUTTON(self, generateBtn.GetId(), self.OnGenerate)

        self.dirEntry.SetFocus()

    @staticmethod
    def getUniqueId(usedIds):
        while True:
            uid = ""

            for i in range(8):
                uid += '%02x' % random.randint(0, 255)

            if uid in usedIds:
                continue

            usedIds.add(uid)

            return uid

    def OnGenerate(self, event):
        watermarks = self.itemsEntry.GetValue().split("\n")
        common = self.commonMark.GetValue()
        directory = self.dirEntry.GetValue()
        fontsize = self.markSize.GetValue()
        fnprefix = self.filenamePrefix.GetValue()

        watermarks = set(watermarks)

        # keep track of ids allocated so far, just on the off-chance we
        # randomly allocated the same id twice
        usedIds = set()

        if not directory:
            wx.MessageBox("Please set directory.", "Error", wx.OK, self)
            self.dirEntry.SetFocus()
            return

        count = 0

        for item in watermarks:
            s = item.strip()

            if not s:
                continue

            basename = item.replace(" ", "-")
            fn = directory + "/" + fnprefix + '-' + basename + ".pdf"
            pmldoc = self.sp.generatePML(True)

            ops = []

            # almost-not-there gray
            ops.append(pml.PDFOp("0.85 g"))

            if common:
                wm = pml.TextOp(
                    util.cleanInput(common),
                    self.sp.cfg.marginLeft + 20, self.sp.cfg.paperHeight * 0.45,
                    fontsize, pml.BOLD, angle = 45)
                ops.append(wm)

            wm = pml.TextOp(
                util.cleanInput(s),
                self.sp.cfg.marginLeft + 20, self.sp.cfg.paperHeight * 0.6,
                fontsize, pml.BOLD, angle = 45)
            ops.append(wm)

            # ...and back to black
            ops.append(pml.PDFOp("0.0 g"))

            for page in pmldoc.pages:
                page.addOpsToFront(ops)

            pmldoc.uniqueId = self.getUniqueId(usedIds)

            pdfdata = pdf.generate(pmldoc)

            if not util.writeToFile(fn, pdfdata, self):
                wx.MessageBox("PDF generation aborted.", "Error", wx.OK, self)
                return
            else:
                count += 1

        if count > 0:
            wx.MessageBox("Generated %d files in directory %s." %
                          (count, directory), "PDFs generated",
                          wx.OK, self)
        else:
            wx.MessageBox("No watermarks specified.", "Error", wx.OK, self)

    def OnClose(self, event):
        self.EndModal(wx.OK)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(
            self.frame, style = wx.DD_NEW_DIR_BUTTON)

        if dlg.ShowModal() == wx.ID_OK:
            self.dirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

########NEW FILE########
__FILENAME__ = addchar
import screenplay as scr
import u

# tests adding characters, i.e. normal typing

def testSpaceAtEOL():
    sp = u.load()
    sp.cmd("moveDown", count = 3)
    sp.cmd("moveLineEnd")
    sp.cmd("addChar", char = "z")
    sp.cmd("addChar", char = " ")
    assert sp.lines[3].text.endswith("z ")
    sp.cmd("addChar", char = "x")
    assert (sp.line == 4) and (sp.column == 1)
    assert sp.lines[3].lb == scr.LB_SPACE
    assert sp.lines[4].lb == scr.LB_LAST
    assert sp.lines[3].text.endswith("wouldz")
    assert sp.lines[4].text.startswith("x be")

def testNbspAtEOL():
    sp = u.load()
    sp.cmd("moveDown", count = 3)
    sp.cmd("moveLineEnd")
    sp.cmd("addChar", char = chr(160))
    sp.cmd("addChar", char = "a")
    assert sp.lines[3].text.endswith("mind")
    assert sp.lines[4].text.startswith("would%sa" % chr(160))
    assert (sp.line == 4) and (sp.column == 7)
    assert sp.lines[3].lb == scr.LB_SPACE
    assert sp.lines[4].lb == scr.LB_LAST

# FIXME: lot more tests

########NEW FILE########
__FILENAME__ = changetype
import u
import screenplay as scr

# test changing type of one element
def testChangeOneElem():
    sp = u.load()
    ls = sp.lines

    sp.cmd("moveDown")

    sp.cmd("tab")
    assert ls[1].lt == scr.CHARACTER

    sp.cmd("toPrevTypeTab")
    assert ls[1].lt == scr.ACTION

    functionMap = {
        "toScene" : scr.SCENE,
        "toCharacter" : scr.CHARACTER,
        "toAction" : scr.ACTION,
        "toDialogue" : scr.DIALOGUE,
        "toParen" : scr.PAREN,
        "toShot" : scr.SHOT,
        "toNote" : scr.NOTE,
        "toTransition" : scr.TRANSITION,
    }

    for (func, ele) in functionMap.items():
        sp.cmd(func)

        assert ls[0].lt == scr.SCENE

        i = 1
        while 1:
            assert ls[i].lt == ele

            if ls[i].lb == scr.LB_LAST:
                break

            i += 1

        assert ls[i + 1].lt == scr.CHARACTER

# test that when text belonging to multiple elements is selected, changing
# type changes all of those elements
def testChangeManyElemes():
    sp = u.load()
    ls = sp.lines

    # select second and third elements
    sp.cmd("moveDown")
    sp.cmd("setMark")
    sp.cmd("moveDown", count = 4)

    sp.cmd("toTransition")

    assert ls[0].lt == scr.SCENE

    for i in range(1, 13):
        assert ls[i].lt == scr.TRANSITION

    assert ls[11].lb == scr.LB_LAST
    assert ls[12].lb == scr.LB_LAST

    assert ls[13].lt == scr.DIALOGUE


########NEW FILE########
__FILENAME__ = copypaste
import screenplay as scr
import u

# tests delete commands

# we had a bug where pasting on an empty line right after a forced
# linebreak would think "oh, I'm in an empty element, I'll just change the
# linetype of this line and be done with it", which is wrong, because the
# linetypes of the lines above were not changed, and now you had an
# element with multiple different linetypes. the right thing to do is not
# change the linetypes at all unless the entire element is empty.
def testPasteAfterForcedLineBreak():
    sp = u.new()

    sp.cmd("addChar", char = "E")
    assert sp.lines[0].lt != scr.CHARACTER

    sp.cmd("insertForcedLineBreak")
    sp.paste([scr.Line(text = "Tsashkataar", lt = scr.CHARACTER)])

    assert len(sp.lines) == 2
    assert (sp.line == 1) and (sp.column == 11)
    assert sp.lines[0].text == "E"
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].lb == scr.LB_FORCED
    assert sp.lines[1].text == "Tsashkataar"
    assert sp.lines[1].lt == scr.SCENE
    assert sp.lines[1].lb == scr.LB_LAST

    sp._validate()

# FIXME: lot more tests

########NEW FILE########
__FILENAME__ = cut
import screenplay as scr
import config
import u

# tests deleting selected areas of text

def testBasic():
    sp = u.load()

    sp.cmd("setMark")
    sp.getSelectedAsCD(True)

    assert sp.lines[0].lb == scr.LB_LAST
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].text == "xt. stonehenge - night"

def testLastDelete():
    sp = u.load()

    sp.cmd("moveEnd")
    sp.cmd("setMark")
    sp.cmd("moveUp", count = 4)
    sp.cmd("moveLineStart")

    # we used to have a bug where if we deleted e.g. the last two lines of
    # the script, and that element was longer, we didn't mark the
    # third-last line as LB_LAST, and then it crashed in rewrapPara.
    sp.getSelectedAsCD(True)

def testEndPrevPara():
    sp = u.load()

    sp.cmd("moveDown", count = 4)
    sp.cmd("moveLineEnd")
    sp.cmd("setMark")
    sp.cmd("moveLineStart")
    sp.cmd("moveUp")

    sp.getSelectedAsCD(True)

    # test that when deleting the last lines of an element we correctly
    # flag the preceding line as the new last line.

    assert sp.lines[2].lb == scr.LB_LAST
    assert sp.lines[3].lt == scr.CHARACTER

# we used to have a bug where joining two elements when the latter one
# contained a forced linebreak didn't convert it properly to the preceding
# element's type.
def testForcedLb():
    sp = u.load()

    sp.cmd("moveDown", count = 2)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp", count = 2)
    sp.cmd("moveLineEnd")
    sp.cmd("setMark")
    sp.cmd("moveRight")
    sp.getSelectedAsCD(True)
    sp._validate()

# we used to have a bug where if we deleted the first line of an element
# plus at least some of the later lines, the rest of the element was
# erroneously joined to the preceding element.
def testFirstDelete():
    sp = u.load()

    sp.cmd("moveDown")
    sp.cmd("setMark")
    sp.cmd("moveDown")
    sp.getSelectedAsCD(True)

    assert sp.lines[0].lb == scr.LB_LAST
    assert sp.lines[0].lt == scr.SCENE

    assert sp.lines[1].lb == scr.LB_SPACE
    assert sp.lines[1].lt == scr.ACTION
    assert sp.lines[1].lt == scr.ACTION
    assert sp.lines[1].text == "lmost zero. Only at brief moments do we catch sight of the"

    sp._validate()

# test that when joining two elements of different type, the latter of
# which contains forced linebreaks, that the whole of the latter element
# is rewrapped correctly.
def testTypeConvert():
    sp = u.load()

    sp.cmd("toTransition")
    sp.cmd("moveDown", count = 3)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp")
    sp.cmd("setMark")
    sp.cmd("moveLeft")
    sp.getSelectedAsCD(True)

    sp._validate()

########NEW FILE########
__FILENAME__ = delete
import screenplay as scr
import u

# tests delete commands

def testBackStart():
    sp = u.load()
    sp.cmd("deleteBackward")
    assert (sp.line == 0) and (sp.column == 0)
    assert sp.lines[0].text == "ext. stonehenge - night"

def testBack():
    sp = u.load()
    sp.cmd("moveRight")
    sp.cmd("deleteBackward")
    assert (sp.line == 0) and (sp.column == 0)
    assert sp.lines[0].text == "xt. stonehenge - night"

def testBackJoinElements():
    sp = u.load()
    sp.cmd("moveDown")
    sp.cmd("deleteBackward")
    assert (sp.line == 0) and (sp.column == 23)
    assert sp.lines[0].text == "ext. stonehenge - nightA blizzard rages."\
           " Snow is everywhere"

def testBackLbSpace():
    sp = u.load()
    sp.gotoPos(16, 60)
    sp.cmd("addChar", char = " ")
    assert sp.lines[16].lb == scr.LB_SPACE
    sp.cmd("moveDown")
    sp.cmd("moveLineStart")
    sp.cmd("deleteBackward")
    assert (sp.line == 17) and (sp.column == 0)
    assert sp.lines[16].lb == scr.LB_SPACE
    assert sp.lines[16].text == "A calm night, with the ocean almost still."\
           " Two fishermen are"
    assert sp.lines[17].text == "smoking at the rear deck."

def testBackLbNone():
    sp = u.load()

    sp.gotoPos(20, 0)
    assert sp.lines[19].lb == scr.LB_NONE
    sp.cmd("deleteBackward")
    assert (sp.line == 19) and (sp.column == 34)
    assert sp.lines[19].text == "Aye,it'snightslikethisthatmakemeree"
    assert sp.lines[20].text == "mber why I love being a fisherman."
    assert sp.lines[19].lb == scr.LB_NONE
    sp.cmd("moveRight", count = 3)
    sp.cmd("addChar", char = " ")
    sp.cmd("moveLeft", count = 2)
    sp.cmd("deleteBackward")
    assert (sp.line == 19) and (sp.column == 34)
    assert sp.lines[19].text == "Aye,it'snightslikethisthatmakemerem"
    assert sp.lines[20].text == "ber why I love being a fisherman."
    assert sp.lines[19].lb == scr.LB_SPACE

def testBackLbForced():
    sp = u.load()

    sp.gotoPos(34, 0)
    assert sp.lines[33].lb == scr.LB_FORCED
    sp.cmd("deleteBackward")
    assert (sp.line == 33) and (sp.column == 6)
    assert sp.lines[33].text == "brightyellow package at their feet."
    assert sp.lines[33].lb == scr.LB_LAST

# test that when joining two elements of different type, the latter of
# which contains forced linebreaks, that the whole of the latter element
# is rewrapped correctly.
def testBackLbForcedTypeConvert():
    sp = u.load()

    sp.cmd("toTransition")
    sp.cmd("moveDown", count = 3)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp")
    sp.cmd("deleteBackward")

    sp._validate()

# FIXME: more tests for forward deletion

# test that when joining two elements of different type, the latter of
# which contains forced linebreaks, that the whole of the latter element
# is rewrapped correctly.
def testForwardLbForcedTypeConvert():
    sp = u.load()

    sp.cmd("toTransition")
    sp.cmd("moveDown", count = 3)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp", count = 2)
    sp.cmd("moveLineEnd")
    sp.cmd("deleteForward")

    sp._validate()

########NEW FILE########
__FILENAME__ = do_tests
#!/usr/bin/env python
# ut:ignore

# FIXME: handle KeyboardInterrupt so testing can be aborted

import glob
import optparse
import os
import re
import sys
import time
import traceback
import types

VERSION = 0.1

def main():
    parser = optparse.OptionParser(version = "%%prog %s" % VERSION)
    parser.add_option("--file", dest="file", help="FILE to test")
    parser.add_option("--function", dest="func", help="FUNCTION to test")
    parser.add_option("--file-at-a-time", action="store_true", dest="faat",
        default = False, help="run tests from each file in the same"
        " process (faster, but coarser if tests fail)")

    (opts, args) = parser.parse_args()

    if opts.file:
        doTest(opts)
    else:
        doTests(opts)

# returns a list of all function names from the given file that start with
# "test".
def getTestFuncs(filename):
    funcs = {}

    f = open(filename, "r")

    for line in f:
        mo = re.match("def (test[a-zA-Z0-9_]*)\(", line)

        if mo:
            name = mo.group(1)

            if name in funcs:
                sys.exit("Error: Function '%s' defined twice." % name)

            funcs[name] = None

    return list(funcs)

# read lines from file 'filename' until one starting with not '#' is
# found, looking for strings matching 'ut:key=val', and storing the
# results in a dictionary which is returned. a missing '=val' part is
# indicated by None as the key's value.
def getFlags(filename):
    fp = open(filename, "r")

    ret = {}
    while 1:
        s = fp.readline()
        if not s or (s[0] != "#"):
            break

        # FIXME: very lame, make this actually work as the documentation
        # says.

        if s.find("ut:ignore") != -1:
            ret["ignore"] = None

    fp.close()

    return ret

# run tests from a single file, either all of them or a specific one.
def doTest(opts):
    # FIXME
    sys.path.insert(0, "../src")

    # strip .py suffix
    name = opts.file[0:-3]

    exec("import %s" % name)

    mod = eval("%s" % name)
    attr = dir(mod)

    if "init" in attr:
        mod.init()

    if opts.faat:
        funcs = getTestFuncs(opts.file)
    else:
        funcs = [opts.func]

    if not funcs:
        print "[--- No tests found in %s ---]" % name
        sys.exit(1)

    for f in funcs:
        print "[Testing %s:%s]" % (name, f)
        getattr(mod, f)()

# run all tests
def doTests(opts):
    # FIXME
    sys.path.insert(0, "../src")

    # total number of tests (files)
    cntTotal = 0

    # number of tests (files) that failed
    cntFailed = 0

    t = time.time()

    # FIXME: allow specifying which files to test

    fnames = sorted(glob.glob("*.py"))

    for fname in fnames:
        flags = getFlags(fname)

        if flags.has_key("ignore"):
            continue

        # strip .py suffix
        name = fname[0:-3]

        if opts.faat:
            # FIXME
            ret = os.system("./do_tests.py --file %s --file-at-a-time" % (
                fname))

            cntTotal += 1
            if ret != 0:
                cntFailed += 1
        else:
            funcs = getTestFuncs(fname)

            if not funcs:
                print "[--- No tests found in %s ---]" % name
                cntTotal += 1
                cntFailed += 1

            for f in funcs:
                # FIXME
                ret = os.system("./do_tests.py --file %s --function %s" % (
                    fname, f))

                cntTotal += 1
                if ret != 0:
                    cntFailed += 1

    t = time.time() - t

    if opts.faat:
        s = "files"
    else:
        s = "tests"

    print "Tested %d %s, out of which %d failed, in %.2f seconds" % (
        cntTotal, s, cntFailed, t)

main()

########NEW FILE########
__FILENAME__ = ismodified
import screenplay as scr
import config
import u

# tests isModified updating

def testInitial():
    sp = u.load()
    assert not sp.isModified()

def testAddChar():
    sp = u.load()
    sp.cmd("addChar", char = "a")
    assert sp.isModified()

def testDeleteBackwardsStart():
    sp = u.load()
    sp.cmd("deleteBackward")
    assert not sp.isModified()

def testDeleteBackwards():
    sp = u.load()
    sp.cmd("moveRight")
    sp.cmd("deleteBackward")
    assert sp.isModified()

def testDelete():
    sp = u.load()
    sp.cmd("deleteForward")
    assert sp.isModified()

def testDeleteEnd():
    sp = u.load()
    sp.cmd("moveEnd")
    sp.cmd("deleteForward")
    assert not sp.isModified()

# waste of time to test all move commands, test just one
def testMoveRight():
    sp = u.load()
    sp.cmd("moveRight")
    assert not sp.isModified()

def testForcedLineBreak():
    sp = u.load()
    sp.cmd("insertForcedLineBreak")
    assert sp.isModified()

def testSplitElement():
    sp = u.load()
    sp.cmd("splitElement")
    assert sp.isModified()

def testTab():
    sp = u.load()
    sp.cmd("tab")
    assert sp.isModified()

def testToPrevTypeTab():
    sp = u.load()
    sp.cmd("toPrevTypeTab")
    assert sp.isModified()

def testConvert():
    sp = u.load()
    sp.cmd("toNote")
    assert sp.isModified()

def testPaste():
    sp = u.load()
    sp.paste([scr.Line(text = "yo")])
    assert sp.isModified()

def testRemoveElementTypes():
    sp = u.load()
    sp.removeElementTypes({ scr.ACTION : 0 }, False)
    assert sp.isModified()

def testApplyCfg():
    sp = u.load()
    sp.applyCfg(config.Config())
    assert sp.isModified()

def testCut():
    sp = u.load()
    sp.cmd("setMark")
    sp.cmd("moveRight")
    sp.getSelectedAsCD(True)
    assert sp.isModified()

########NEW FILE########
__FILENAME__ = join_elems
import screenplay as scr
import u

# tests element joining

# we used to have a bug where if the latter element contained a forced
# linebreak the result was invalid. this one tests the case where the
# forced linebreak is on the first line of the element, the second one
# where it is on the third line.
def testForcedLb():
    sp = u.new()

    sp.cmd("addChar", char = "a")
    sp.cmd("splitElement")
    sp.cmd("toDialogue")
    sp.cmd("addChar", char = "b")
    sp.cmd("insertForcedLineBreak")
    sp.cmd("addChar", char = "c")
    sp.cmd("moveLeft")
    sp.cmd("moveUp")
    sp.cmd("deleteBackward")

    assert len(sp.lines) == 2
    assert (sp.line == 0) and (sp.column == 1)
    assert sp.lines[0].text == "AB"
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].lb == scr.LB_FORCED
    assert sp.lines[1].text == "c"
    assert sp.lines[1].lt == scr.SCENE
    assert sp.lines[1].lb == scr.LB_LAST

def testForcedLb2():
    sp = u.new()

    sp.cmd("addChar", char = "a")
    sp.cmd("splitElement")
    sp.cmd("toTransition")
    sp.cmdChars("line 1///////////// ")
    sp.cmdChars("line 2///////////// ")
    sp.cmdChars("line 3")
    sp.cmd("insertForcedLineBreak")
    sp.cmdChars("line 4")
    sp.gotoPos(1, 0)
    sp.cmd("deleteBackward")

    assert len(sp.lines) == 2
    assert (sp.line == 0) and (sp.column == 1)
    assert sp.lines[0].text == "ALine 1///////////// line 2///////////// line 3"
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].lb == scr.LB_FORCED
    assert sp.lines[1].text == "line 4"
    assert sp.lines[1].lt == scr.SCENE
    assert sp.lines[1].lb == scr.LB_LAST

########NEW FILE########
__FILENAME__ = movement
import u

# tests movement commands

def testMoveRight():
    sp = u.load()
    sp.cmd("moveRight")
    assert sp.column == 1
    sp.cmd("moveLineEnd")
    sp.cmd("moveRight")
    assert (sp.line == 1) and (sp.column == 0)
    sp.cmd("moveEnd")
    sp.cmd("moveRight")
    assert (sp.line == 158) and (sp.column == 5)

def testMoveLeft():
    sp = u.load()
    sp.cmd("moveLeft")
    assert (sp.line == 0) and (sp.column == 0)
    sp.cmd("moveDown")
    sp.cmd("moveLeft")
    assert (sp.line == 0) and (sp.column == 23)
    sp.cmd("moveLineStart")
    assert sp.column == 0

def testMoveUp():
    sp = u.load()
    sp.cmd("moveUp")
    assert (sp.line == 0) and (sp.column == 0)
    sp.cmd("moveDown")
    sp.cmd("moveLineEnd")
    sp.cmd("moveUp")
    assert (sp.line == 0) and (sp.column == 23)

def testMoveDown():
    sp = u.load()
    sp.cmd("moveDown")
    assert sp.line == 1
    sp.cmd("moveDown")
    sp.cmd("moveDown")
    sp.cmd("moveLineEnd")
    sp.cmd("moveDown")
    assert (sp.line == 4) and (sp.column == 31)
    sp.cmd("moveEnd")
    sp.cmd("moveDown")
    assert sp.line == 158

def testMoveLineEnd():
    sp = u.load()
    sp.cmd("moveLineEnd")
    assert sp.column == 23

def testMoveLineStart():
    sp = u.load()
    sp.cmd("moveRight")
    sp.cmd("moveLineStart")
    assert sp.column == 0

def testMoveEnd():
    sp = u.load()
    sp.cmd("moveEnd")
    assert (sp.line == 158) and (sp.column == 5)

def testMoveStart():
    sp = u.load()
    sp.cmd("moveEnd")
    sp.cmd("moveStart")
    assert (sp.line == 0) and (sp.column == 0)

def testMoveSceneUp():
    sp = u.load()
    sp.cmd("moveSceneUp")
    assert (sp.line == 0) and (sp.column == 0)
    sp.gotoPos(18, 1)
    sp.cmd("moveSceneUp")
    assert (sp.line == 14) and (sp.column == 0)
    sp.cmd("moveSceneUp")
    assert (sp.line == 0) and (sp.column == 0)

    # make sure we don't go before the start trying to find scenes
    sp.cmd("toAction")
    sp.cmd("moveSceneUp")
    assert (sp.line == 0) and (sp.column == 0)

def testMoveSceneDown():
    sp = u.load()
    sp.cmd("moveSceneDown")
    assert (sp.line == 14) and (sp.column == 0)
    sp.cmd("moveDown")
    sp.cmd("moveSceneDown")
    assert (sp.line == 30) and (sp.column == 0)
    sp.cmd("moveEnd")
    sp.cmd("moveSceneDown")
    assert (sp.line == 158) and (sp.column == 0)

########NEW FILE########
__FILENAME__ = pagelist
import screenplay as scr
import u

# test screenplay.PageList

# helper test function.
def ch(allPages, pages, res):
    pl = scr.PageList(allPages)

    for p in pages:
        pl.addPage(p)

    assert str(pl) == res

def testBasic():
    u.init()

    # "1" .. "119"
    allPages = [str(p) for p in range(120)[1:]]

    # test basic stuff
    ch([], [], "")
    ch(allPages, [], "")
    ch(allPages, [-42, 167], "")
    ch(allPages, [1], "1")
    ch(allPages, [1, 2], "1-2")
    ch(allPages, [6, 7, 8], "6-8")
    ch(allPages, [6, 7, 8, 118], "6-8, 118")
    ch(allPages, [6, 7, 8, 119], "6-8, 119")
    ch(allPages, [6, 7, 8, 118, 119], "6-8, 118-119")

    # test that int/str makes no difference
    ch(allPages, [1, 2, 3, 5, 7, 9, 42, 43, 44], "1-3, 5, 7, 9, 42-44")
    ch(allPages, ["1", "2", "3", "5", "7", "9", "42", "43", "44"],
       "1-3, 5, 7, 9, 42-44")
    ch(allPages, ["1", 2, "3", 5, "7", 9, "42", 43, "44"],
       "1-3, 5, 7, 9, 42-44")

def testFancy():
    u.init()

    allPages = ["1A", "3", "4B", "4C", "4D", "5", "6", "6A", "7", "7B"]

    ch(allPages, ["1A", "3", "4C", "6", "6A", "7", "7B"], "1A-3, 4C, 6-7B")
    ch(allPages, ["1A", "7B"], "1A, 7B")
    ch(allPages, ["1A", 7, "7B"], "1A, 7-7B")

########NEW FILE########
__FILENAME__ = t_characterreport
import characterreport
import u

# tests character report (just that it runs without exceptions, for now)

def testBasic():
    sp = u.load()
    report = characterreport.CharacterReport(sp)
    data = report.generate()

    # try to catch cases where generate returns something other than a PDF
    # document
    assert len(data) > 200
    assert data[:8] == "%PDF-1.5"

########NEW FILE########
__FILENAME__ = t_locationreport
import locationreport
import scenereport
import u

# tests location report (just that it runs without exceptions, for now)

def testBasic():
    sp = u.load()
    report = locationreport.LocationReport(scenereport.SceneReport(sp))
    data = report.generate()

    # try to catch cases where generate returns something other than a PDF
    # document
    assert len(data) > 200
    assert data[:8] == "%PDF-1.5"

########NEW FILE########
__FILENAME__ = t_locations
import locations
import u

# test locations.Locations

# helper test function.
def ch(locsOld, scenes, locsNew):
    loc = locations.Locations()
    loc.locations = locsOld

    loc.refresh(scenes)

    assert loc.locations == locsNew

def test():
    u.init()

    scenes = {
        "INT. MOTEL ROOM - DAY" : None,
        "INT. MOTEL ROOM - NIGHT" : None,
        "EXT. PALACE - DAY" : None,
        "EXT. SHOPFRONT - DAY" : None
        }

    ch([], {}, [])
    ch([], scenes, [])
    ch([["nosuchthingie"]], {}, [])
    ch([["nosuchthingie"]], scenes, [])

    ch([["int. motel Room - day"]], scenes, [["INT. MOTEL ROOM - DAY"]])

    ch([["int. motel Room - day", "nosuchthingie"]], scenes,
       [["INT. MOTEL ROOM - DAY"]])

    ch([["int. motel Room - day", "int. motel Room - day"]], scenes,
       [["INT. MOTEL ROOM - DAY"]])

    ch([["INT. MOTEL ROOM - DAY", "EXT. SHOPFRONT - DAY"]], scenes,
       [["EXT. SHOPFRONT - DAY", "INT. MOTEL ROOM - DAY"]])

    ch([["INT. MOTEL ROOM - DAY"],
        ["INT. MOTEL ROOM - NIGHT", "EXT. PALACE - DAY"]], scenes,
       [["EXT. PALACE - DAY", "INT. MOTEL ROOM - NIGHT"],
        ["INT. MOTEL ROOM - DAY"]])

########NEW FILE########
__FILENAME__ = t_random
#!/usr/bin/env python
# ut:ignore

# runs random operations on a Screenplay as a way of trying to find bugs.
# note that this is not part of the normal test run, this has to be run
# manually.

import random
import sys
import traceback

# FIXME
sys.path.insert(0, "../src")

import u

# generates, stores, saves, loads, and runs operations against a
# Screenplay object.
class Ops:
    def __init__(self):
        # a list of Op objects
        self.ops = []

        # a Screenplay object
        self.sp = None

        # index of next operation to run
        self.nextPos = 0

    # run next operation. returns True when more operations are waiting to
    # be run, False otherwise.
    def run(self):
        self.sp = self.ops[self.nextPos].run(self.sp)
        self.nextPos += 1

        return self.nextPos < len(self.ops)

    # add given Operation.
    def add(self, op):
        self.ops.append(op)

    # return self.ops as a text string
    def save(self):
        s = ""

        for op in self.ops:
            s += op.save() + "\n"

        return s

    # construct a new Ops from the given string.
    @staticmethod
    def load(s):
        self = Ops()

        for line in s.splitlines():
            if not line.startswith("#"):
                self.ops.append(Op.load(line))

        return self

# a single operation
class Op:
    funcs = [
        "abort",
        "addChar",
        "deleteBackward",
        "deleteForward",
        "insertForcedLineBreak",
        "moveDown",
        "moveEnd",
        "moveLeft",
        "moveLineEnd",
        "moveLineStart",
        "moveRight",
        "moveSceneDown",
        "moveSceneUp",
        "moveStart",
        "moveUp",
        "redo",
        "selectAll",
        "selectScene",
        "setMark",
        "splitElement",
        "tab",
        "toActBreak",
        "toAction",
        "toCharacter",
        "toDialogue",
        "toNote",
        "toParen",
        "toPrevTypeTab",
        "toScene",
        "toShot",
        "toTransition",
        "undo",
        ]

    # FIXME: not tested editing commands:
    #   -removeElementTypes
    #   -cut (getSelectedAsCD(True))
    #   -paste

    def __init__(self, name = None):
        # name of operation
        self.name = name

        # arguments to operation. currently a list of ints, but it's
        # probable we need another class, Arg, that can represent an
        # arbitrary argument.
        self.args = []

    # run this operation against the given screenplay. returns either sp
    # or a new Screenplay object (if the operation is NEW/LOAD).
    def run(self, sp):
        if self.name == "NEW":
            return u.new()
        elif self.name == "LOAD":
            return u.load()

        if self.args:
            sp.cmd(self.name, chr(self.args[0]))
        else:
            sp.cmd(self.name)

        return sp

    # get a random operation.
    # FIXME: this should have different probabilities for different
    # operations.
    @staticmethod
    def getRandom():
        self = Op()

        f = self.__class__.funcs
        self.name = f[random.randint(0, len(f) - 1)]

        if self.name == "addChar":
            self.args.append(random.randint(0, 255))

        return self

    # return self as a text string
    def save(self):
        s = self.name

        for arg in self.args:
            s += ",%s" % str(arg)

        return s

    # construct a new Ops from the given string.
    @staticmethod
    def load(s):
        vals = s.split(",")

        self = Op()
        self.name = vals[0]
        for i in range(1, len(vals)):
            self.args.append(int(vals[i]))

        return self

# run random operations forever
def runRandomOps():
    cnt = 0
    while True:
        rounds = max(1, int(random.gauss(15000, 4000)))
        print "Count %d (%d rounds)" % (cnt, rounds)

        ops = Ops()
        failed = False

        # every 10th time, test operations on an empty script
        if (cnt % 10) == 0:
            ops.add(Op("NEW"))
        else:
            ops.add(Op("LOAD"))

        for i in xrange(rounds):
            if i != 0:
                ops.add(Op.getRandom())

            try:
                ops.run()
                # FIXME: add a --validate option
                ops.sp._validate()
            except KeyboardInterrupt:
                raise
            except:
                print " Failed, saving..."
                save(ops, cnt)
                failed = True

                break

        if not failed:
            try:
                ops.sp._validate()
                s = ops.sp.save()
                u.loadString(s)
            except KeyboardInterrupt:
                raise
            except:
                print " Failed in save/load, saving..."
                save(ops, cnt)

        cnt += 1

# run ops from given file
def runOpsFromFile(filename):
    f = open(filename, "r")
    s = f.read()
    f.close()

    ops = Ops.load(s)

    while 1:
        more = ops.run()

        # FIXME: add a --validate option
        ops.sp._validate()

        if not more:
            break

# save information about failed ops.
def save(ops, cnt):
    f = open("%d.ops" % cnt, "w")

    tbLines = traceback.format_exception(*sys.exc_info())

    for l in tbLines:
        # traceback lines contain embedded newlines so it gets a bit
        # complex escaping every line with # and keeping the formatting
        # correct.
        f.write("#" + l.rstrip().replace("\n", "\n#") + "\n")

    f.write(ops.save())
    f.close()

    f = open("%d.trelby" % cnt, "w")
    f.write(ops.sp.save())
    f.close()

def main():
    if len(sys.argv) == 1:
        runRandomOps()
    else:
        runOpsFromFile(sys.argv[1])

main()

########NEW FILE########
__FILENAME__ = t_scenereport
import scenereport
import u

# tests scene report (just that it runs without exceptions, for now)

def testBasic():
    sp = u.load()
    report = scenereport.SceneReport(sp)
    data = report.generate()

    # try to catch cases where generate returns something other than a PDF
    # document
    assert len(data) > 200
    assert data[:8] == "%PDF-1.5"

########NEW FILE########
__FILENAME__ = t_scriptreport
import scriptreport
import u

# tests script report (just that it runs without exceptions, for now)

def testBasic():
    sp = u.load()
    report = scriptreport.ScriptReport(sp)
    data = report.generate()

    # try to catch cases where generate returns something other than a PDF
    # document
    assert len(data) > 200
    assert data[:8] == "%PDF-1.5"

########NEW FILE########
__FILENAME__ = t_util
# -*- coding: iso-8859-1 -*-

import u
import util

# test util stuff

def testReplace():
    u.init()

    ur = util.replace

    assert ur("", "", 0, 0) == ""
    assert ur("", "jep", 0, 0) == "jep"
    assert ur("yo", "bar", 0, 0) == "baryo"
    assert ur("yo", "bar", 0, 1) == "baro"
    assert ur("yo", "bar", 1, 0) == "ybaro"
    assert ur("yo", "bar", 1, 1) == "ybar"
    assert ur("yo", "bar", 2, 0) == "yobar"
    assert ur("yo", "ba\tr", 2, 0) == "yoba|r"

def testSplitToWords():
    u.init()

    us = util.splitToWords

    assert us("") == []
    assert us("yo") == ["yo"]
    assert us("yo foo") == ["yo", "foo"]
    assert us("�ksy y�") == ["�ksy", "y�"]
    assert us("Mixed CASE") == ["Mixed", "CASE"]
    assert us("out-of-nowhere, a monkey appears, bearing fruit!") == [
        "out", "of", "nowhere", "a", "monkey", "appears", "bearing", "fruit"]
    assert us("don't assume -- it blaa") == ["don't", "assume", "it", "blaa"]
    assert us("a''b--c|d�e") == ["a''b", "c", "d", "e"]

def testToUTF8():
    u.init()

    t = util.toUTF8

    assert t("") == ""
    assert t("yo") == "yo"
    assert t("y�") == "yö"

def testFromUTF8():
    u.init()

    f = util.fromUTF8

    assert f("") == ""
    assert f("yo") == "yo"
    assert f("yö") == "y�"
    assert f("y�12345") == "y12345"
    assert f("a\xE2\x82\xACb") == "ab"

def testEscapeStrings():
    u.init()

    data = [
        ([], ""),
        (["a"], "a"),
        (["a", "b"], "a\\nb"),
        (["a", "b", "cc"], "a\\nb\\ncc"),
        (["foo\\bar", "blaa"], "foo\\\\bar\\nblaa"),
        (["a\\n", "c"], "a\\\\n\\nc"),
        (["a\\", "b"], "a\\\\\\nb"),
        ]

    for items,s in data:
        assert util.escapeStrings(items) == s
        assert util.unescapeStrings(s) == items

########NEW FILE########
__FILENAME__ = u
# ut:ignore

import config
import misc
import screenplay
import util

initDone = False

def init():
    global initDone

    if not initDone:
        misc.init(False)
        util.init(False)

        initDone = True

# return new, empty Screenplay
def new():
    init()

    return screenplay.Screenplay(config.ConfigGlobal())

# load script from the given file
def load(filename = "test.trelby"):
    init()

    return screenplay.Screenplay.load(open(filename, "r").read(),
                                      config.ConfigGlobal())[0]

# load script from given string
def loadString(s):
    init()

    return screenplay.Screenplay.load(s, config.ConfigGlobal())[0]


########NEW FILE########
__FILENAME__ = validate
import screenplay as scr
import u

# tests that Screenplay._validate() finds all errors it's supposed to

# helper function that asserts if sp._validate() does not assert
def v(sp):
    try:
        sp._validate()
    except AssertionError:
        return

    assert 0

def testEmpty():
    sp = u.new()
    sp._validate()
    sp.lines = []
    v(sp)

def testCursorPos():
    sp = u.new()

    sp._validate()

    sp.line = -1
    v(sp)

    sp.line = 5
    v(sp)

    sp.line = 0

    sp.column = -1
    v(sp)

    sp.column = 5
    v(sp)

    sp.column = 0

    sp._validate()

def testInvalidChars():
    sp = u.new()
    sp._validate()
    sp.lines[0].text = chr(9)
    v(sp)

def testTooLongLine():
    sp = u.new()
    sp._validate()
    sp.lines[0].text = "a" * 100
    v(sp)

def testElemChangesType():
    sp = u.load()
    sp._validate()
    sp.lines[1].lt = scr.SCENE
    v(sp)

########NEW FILE########
__FILENAME__ = add_words
#!/usr/bin/env python
# add words to ../dict_en.dat in the correct place

import sys

if len(sys.argv) < 2:
    raise Exception("add_word.py word1 word2...")

sys.path.insert(0, "../src")

import misc
import util

util.init(False)
misc.init(False)

s = util.loadFile("../dict_en.dat", None)
if s == None:
    raise Exception("error")

words = {}
lines = s.splitlines()

for it in lines:
    words[util.lower(it)] = None

for arg in sys.argv[1:]:
    words[util.lower(arg)] = None

words = words.keys()
words.sort()

f = open("../dict_en.dat", "wb")
for w in words:
    f.write("%s\n" % w)

f.close()

########NEW FILE########
