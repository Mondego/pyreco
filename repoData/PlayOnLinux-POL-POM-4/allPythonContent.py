__FILENAME__ = configure
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Pâris Quentin
# Copyright (C) 2007-2010 PlayOnLinux Team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os, sys, string, stat, shutil
import wx, time, shlex, subprocess

import wine_versions
import lib.playonlinux as playonlinux
import lib.wine as wine
import lib.Variables as Variables
import lib.lng as lng

class PackageList():
    def __init__(self):
        self.available_packages = [];
        self.loadList();
        
    def loadList(self):
        try :
            self.available_packages = open(Variables.playonlinux_rep+"/configurations/listes/POL_Functions","r").read()
        except IOError as e: # File does not exits ; it will be created when pol is updated
            pass
        
    def getList(self):
        return self.available_packages;
        
    def getCutList(self):
        clist = self.available_packages.split("\n")
        flist = []
        for key in clist:
            if("POL_Install" in key):
                flist.append(key)
        return flist
        
    def getParsedList(self):
        clist = self.getCutList();
        flist = [];
        for key in clist:
            flist.append(PackageList.getNameFromPackageLine(key))
        return flist;
    
    def getNameFromId(self, id):
        return self.getParsedList()[id];
        
    def getPackageFromName(self, selectedPackage):
        broken = False;
        for key in self.getCutList():
            key_split = key.split(":")
            try: 
                if(key_split[1] == selectedPackage): # We found it
                    selectedPackage = key_split[0];
                    broken = True;
                    break;

            except IndexError, e: # Index error : There is no ':' in the line, so the content of the line is the package we want to install. No need to continue
                broken = True;
                break;
            
        if(broken == False):
            selectedPackage = "POL_Install_"+selectedPackage
        return selectedPackage;
    
    
    @staticmethod
    def getNameFromPackageLine(package):
        try:
            realName = package.split(":")[1].replace("POL_Install_","")
        except IndexError, e:
            realName = package.replace("POL_Install_","")
        return realName;
    
    
class Onglets(wx.Notebook):
    # Classe dérivée du wx.Notebook
    
    def __init__(self, parent):
        self.packageList = PackageList();
        self.notebook = wx.Notebook.__init__(self, parent, -1)
        self.typing = False
        self.changing_selection = False

    def ChangeTitle(self, new_title):
        self.s_title = new_title
        self.s_prefix = playonlinux.getPrefix(self.s_title)
        self.changing_selection = True
        self.general_elements["name"].SetValue(new_title)
        self.changing = True

    def winebash(self, command, new_env=None):
        args = shlex.split(command.encode("utf-8","replace"))
        if(self.s_isPrefix == True):
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/winebash", "--prefix", self.s_prefix.encode('utf-8','replace')] + args, env=new_env)
        else:
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/winebash", self.s_title.encode('utf-8','replace')] + args, env=new_env)

    def evt_winecfg(self, event):
        self.winebash("winecfg")

    def evt_uninstall(self, event):
        wx.MessageBox(_("Warning:\n\nThis tool is for advanced users.\nTo uninstall cleanly a program with {0}, you must delete the virtual drive associated").format(os.environ["APPLICATION_TITLE"]),os.environ["APPLICATION_TITLE"])
        self.winebash("uninstaller")

    def evt_regedit(self, event):
        self.winebash("regedit")

    def evt_cmd(self, event):
        # http://bugs.winehq.org/show_bug.cgi?id=10063
        new_env = os.environ
        new_env["LANG"] = "C"

        self.winebash("wineconsole cmd", new_env)

    def evt_taskmgr(self, event):
        self.winebash("taskmgr")

    def evt_rep(self, event):
        try:
            os.remove(os.environ["POL_USER_ROOT"]+"/wineprefix/"+self.s_prefix+"/.update-timestamp")
        except:
            pass
        self.winebash("wineboot")

    def evt_wineboot(self, event):
        self.winebash("wineboot")

    def evt_killall(self, event):
        self.winebash("wineserver -k")

    def evt_config(self, event):
        subprocess.Popen(["bash", Variables.playonlinux_rep+"/configurations/configurators/"+self.s_title])

    def install_package(self, event):
        selectedPackage = self.packageList.getPackageFromName(self.Menu.GetItemText(self.Menu.GetSelection()))

        if(self.s_isPrefix == False):
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/installpolpackages", self.s_title.encode('utf-8','replace'), selectedPackage])
        else:
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/installpolpackages", "--prefix", self.s_prefix.encode('utf-8','replace'), selectedPackage])

    def AddGeneralChamp(self, title, shortname, value, num):
        self.general_elements[shortname+"_text"] = wx.StaticText(self.panelGeneral, -1, title,pos=(15,19+num*40))
        self.general_elements[shortname] = wx.TextCtrl(self.panelGeneral, 200+num, value, pos=(300,23+num*40), size=(250,20))
    #       self.general_elements[shortname].SetValue(value)

    def AddGeneralElement(self, title, shortname, elements, wine, num):
        if(shortname == "wineversion"):
            elements.insert(0,"System")
            wine.insert(0,"System")
            elemsize = (225,25)
        else:
            elemsize = (250,25)

        self.general_elements[shortname+"_text"] = wx.StaticText(self.panelGeneral, -1, title,pos=(15,19+num*40))

        self.general_elements[shortname] = wx.ComboBox(self.panelGeneral, 200+num, style=wx.CB_READONLY,pos=(300,17+num*40),size=elemsize)
        self.general_elements[shortname].AppendItems(elements)
        self.general_elements[shortname].SetValue(elements[0])

        if(shortname == "wineversion"):
            self.addBitmap = wx.Image( Variables.playonlinux_env+"/resources/images/icones/list-add.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
            if(os.environ["POL_OS"] == "Linux"):
                self.general_elements["wineversion_button"] = wx.BitmapButton(self.panelGeneral,601, pos=(527,19+num*40),size=(21,21),bitmap=self.addBitmap)
            if(os.environ["POL_OS"] == "Mac"):
                self.general_elements["wineversion_button"] = wx.BitmapButton(self.panelGeneral,601, pos=(522,15+num*40),size=(21,21),bitmap=self.addBitmap)
            

    def General(self, nom):
        self.panelGeneral = wx.Panel(self, -1)
        self.AddPage(self.panelGeneral, nom)
        self.general_elements = {}
        # Les polices
        if(os.environ["POL_OS"] == "Mac"):
            self.fontTitle = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.caption_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)
        else :
            self.fontTitle = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.caption_font = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)

        self.txtGeneral = wx.StaticText(self.panelGeneral, -1, _("General"), (10,10), wx.DefaultSize)
        self.txtGeneral.SetFont(self.fontTitle)

        self.AddGeneralButton(_("Make a new shortcut from this virtual drive"),"newshort",1)
        self.AddGeneralChamp(_("Name"),"name","",2)
        self.AddGeneralElement(_("Wine version"),"wineversion",[],[],3)
        self.AddGeneralChamp(_("Debug flags"), "winedebug", "", 4)

        self.AddGeneralElement(_("Virtual drive"), "wineprefix", playonlinux.Get_Drives(), playonlinux.Get_Drives(), 5)

        self.AddGeneralChamp(_("Arguments"), "arguments", "", 6)

        self.configurator_title = wx.StaticText(self.panelGeneral, -1, "", (10,294), wx.DefaultSize)
        self.configurator_title.SetFont(self.fontTitle)
        self.configurator_button = wx.Button(self.panelGeneral, 106, _("Run configuration wizard"), pos=(15,324))


        wx.EVT_TEXT(self, 202, self.setname)
        wx.EVT_TEXT(self, 206, self.setargs)
        wx.EVT_TEXT(self, 204, self.setwinedebug)

        wx.EVT_COMBOBOX(self, 203, self.assign)
        wx.EVT_COMBOBOX(self, 205, self.assignPrefix)
        wx.EVT_BUTTON(self, 601, self.Parent.Parent.Parent.WineVersion)

    def Wine(self, nom):
        self.panelWine = wx.Panel(self, -1)
        self.AddPage(self.panelWine, nom)
        # Les polices
        self.txtGeneral = wx.StaticText(self.panelWine, -1, "Wine", (10,10), wx.DefaultSize)
        self.txtGeneral.SetFont(self.fontTitle)

        self.winecfg_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/wine-winecfg.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.winecfg = wx.BitmapButton(self.panelWine, id=100, bitmap=self.winecfg_image,pos=(30, 50), size = (self.winecfg_image.GetWidth()+5, self.winecfg_image.GetHeight()+5))
        self.winecfg_texte = wx.StaticText(self.panelWine, -1, _("Configure Wine"), (32,156), style=wx.ALIGN_CENTER)
        self.winecfg_texte.Wrap(110)
        self.winecfg_texte.SetPosition((self.winecfg_texte.GetPosition()[0]+(105-self.winecfg_texte.GetSize()[0])/2,self.winecfg_texte.GetPosition()[1]))

        self.winecfg_texte.SetFont(self.caption_font)

        self.regedit_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/registry.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.regedit = wx.BitmapButton(self.panelWine, id=101, bitmap=self.regedit_image,pos=(166, 50), size = (self.regedit_image.GetWidth()+5, self.regedit_image.GetHeight()+5))
        self.regedit_texte = wx.StaticText(self.panelWine, -1, _("Registry Editor"), (168,156), style=wx.ALIGN_CENTER)
        self.regedit_texte.Wrap(110)
        self.regedit_texte.SetPosition((self.regedit_texte.GetPosition()[0]+(105-self.regedit_texte.GetSize()[0])/2,self.regedit_texte.GetPosition()[1]))

        self.regedit_texte.SetFont(self.caption_font)


        self.wineboot_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/reboot.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.wineboot = wx.BitmapButton(self.panelWine, id=102, bitmap=self.wineboot_image,pos=(302, 50), size = (self.wineboot_image.GetWidth()+5, self.wineboot_image.GetHeight()+5))
        self.wineboot_texte = wx.StaticText(self.panelWine, -1, _("Windows reboot"), (304,156), style=wx.ALIGN_CENTER)
        self.wineboot_texte.Wrap(110)
        self.wineboot_texte.SetPosition((self.wineboot_texte.GetPosition()[0]+(105-self.wineboot_texte.GetSize()[0])/2,self.wineboot_texte.GetPosition()[1]))
        self.wineboot_texte.SetFont(self.caption_font)


        self.updatep_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/update.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.updatep = wx.BitmapButton(self.panelWine, id=107, bitmap=self.updatep_image,pos=(438, 50), size = (self.wineboot_image.GetWidth()+5, self.updatep_image.GetHeight()+5))
        self.updatep_texte = wx.StaticText(self.panelWine, -1, _("Repair virtual drive"), (440,156), style=wx.ALIGN_CENTER)
        self.updatep_texte.Wrap(110)
        self.updatep_texte.SetPosition((self.updatep_texte.GetPosition()[0]+(105-self.wineboot_texte.GetSize()[0])/2,self.updatep_texte.GetPosition()[1]))
        self.updatep_texte.SetFont(self.caption_font)



        self.cmd_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/console.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.cmd = wx.BitmapButton(self.panelWine, id=103, bitmap=self.cmd_image,pos=(30, 196), size = (self.cmd_image.GetWidth()+5, self.cmd_image.GetHeight()+5))
        self.cmd_texte = wx.StaticText(self.panelWine, -1, _("Command prompt"), (32,302), style=wx.ALIGN_CENTER)
        self.cmd_texte.Wrap(110)
        self.cmd_texte.SetPosition((self.cmd_texte.GetPosition()[0]+(105-self.cmd_texte.GetSize()[0])/2,self.cmd_texte.GetPosition()[1]))
        self.cmd_texte.SetFont(self.caption_font)

        self.taskmgr_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/monitor.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.taskmgr = wx.BitmapButton(self.panelWine, id=104, bitmap=self.taskmgr_image,pos=(166, 196), size = (self.taskmgr_image.GetWidth()+5, self.taskmgr_image.GetHeight()+5))
        self.taskmgr_texte = wx.StaticText(self.panelWine, -1, _("Task manager"), (168,302), style=wx.ALIGN_CENTER)
        self.taskmgr_texte.Wrap(110)
        self.taskmgr_texte.SetPosition((self.taskmgr_texte.GetPosition()[0]+(105-self.taskmgr_texte.GetSize()[0])/2,self.taskmgr_texte.GetPosition()[1]))

        self.taskmgr_texte.SetFont(self.caption_font)

        self.killall_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/stop.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.killall = wx.BitmapButton(self.panelWine, id=105, bitmap=self.killall_image,pos=(302, 196), size = (self.killall_image.GetWidth()+5, self.killall_image.GetHeight()+5))
        self.killall_texte = wx.StaticText(self.panelWine, -1, _("Kill processes"), (304,302), style=wx.ALIGN_CENTER)
        self.killall_texte.Wrap(110)
        self.killall_texte.SetPosition((self.killall_texte.GetPosition()[0]+(105-self.killall_texte.GetSize()[0])/2,self.killall_texte.GetPosition()[1]))
        self.killall_texte.SetFont(self.caption_font)

        self.uninstall_image = wx.Image( Variables.playonlinux_env+"/resources/images/configure/wine-uninstaller.png", wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.uninstall = wx.BitmapButton(self.panelWine, id=108, bitmap=self.uninstall_image,pos=(438, 196), size = (self.wineboot_image.GetWidth()+5, self.uninstall_image.GetHeight()+5))
        self.uninstall_texte = wx.StaticText(self.panelWine, -1, _("Wine uninstaller"), (440,302), style=wx.ALIGN_CENTER)
        self.uninstall_texte.Wrap(110)
        self.uninstall_texte.SetPosition((self.uninstall_texte.GetPosition()[0]+(105-self.wineboot_texte.GetSize()[0])/2,self.uninstall_texte.GetPosition()[1]))
        self.uninstall_texte.SetFont(self.caption_font)


        wx.EVT_BUTTON(self, 100, self.evt_winecfg)
        wx.EVT_BUTTON(self, 101, self.evt_regedit)
        wx.EVT_BUTTON(self, 102, self.evt_wineboot)
        wx.EVT_BUTTON(self, 103, self.evt_cmd)
        wx.EVT_BUTTON(self, 104, self.evt_taskmgr)
        wx.EVT_BUTTON(self, 105, self.evt_killall)
        wx.EVT_BUTTON(self, 106, self.evt_config)
        wx.EVT_BUTTON(self, 107, self.evt_rep)
        wx.EVT_BUTTON(self, 108, self.evt_uninstall)


    def Packages(self, nom):
        self.panelPackages = wx.Panel(self, -1)
        self.txtPackages = wx.StaticText(self.panelPackages, -1, _(nom), (10,10), wx.DefaultSize)
        self.txtPackages.SetFont(self.fontTitle)
        
        self.imagePackages = wx.ImageList(22, 22)
    
            
        self.desPackags = wx.StaticText(self.panelPackages, -1, _("Be careful! Installing one of these components can break your virtual drive."), (10,40), wx.DefaultSize)
            
        self.Menu = wx.TreeCtrl(self.panelPackages, 99, pos=(15,75),size=(530,260), style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|Variables.widget_borders)
        self.Menu.SetSpacing(0);
        self.Menu.SetImageList(self.imagePackages)
        self.imagePackages.RemoveAll()

        self.rootPackages = self.Menu.AddRoot("")
        self.i = 0

        for app in self.packageList.getParsedList():
                self.icon_look_for = Variables.playonlinux_rep+"/configurations/icones/"+self.packageList.getPackageFromName(app)
                if(os.path.exists(self.icon_look_for)):
                    try:
                        self.imagePackages.Add(wx.Bitmap(self.icon_look_for))
                    except:
                        pass
                else:
                    self.imagePackages.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/playonlinux22.png"))
                self.Menu.AppendItem(self.rootPackages, app, self.i)
                self.i = self.i+1
                
        self.PackageButton = wx.Button(self.panelPackages, 98, _("Install"), pos=(20+530-150,345), size=(150,30))


        wx.EVT_TREE_ITEM_ACTIVATED(self, 99, self.install_package)
        wx.EVT_BUTTON(self, 98, self.install_package)


        self.AddPage(self.panelPackages, nom)

    def change_Direct3D_settings(self, param):
        if(self.s_isPrefix == False):
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", self.s_title.encode('utf-8','replace'), "POL_Wine_Direct3D", param, self.display_elements[param].GetValue().encode('utf-8','replace')])
        else:
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", "--prefix", self.s_prefix.encode('utf-8','replace'), "POL_Wine_Direct3D", param, self.display_elements[param].GetValue().encode('utf-8','replace')])

    def change_DirectInput_settings(self, param):
        if(self.s_isPrefix == False):
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", self.s_title.encode('utf-8','replace'), "POL_Wine_DirectInput", param, self.display_elements[param].GetValue().encode('utf-8','replace')])
        else:
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", "--prefix", self.s_prefix.encode('utf-8','replace'), "POL_Wine_DirectInput", param, self.display_elements[param].GetValue().encode('utf-8','replace')])

    def get_current_settings(self, param):
        self.display_elements[param].SetValue(self.settings[param])

    def UpdateVersions(self, arch):
        elements = playonlinux.Get_versions(arch)
        self.general_elements["wineversion"].Clear()
        if(arch == playonlinux.GetSettings("WINE_SYSTEM_ARCH") or (arch == "x86" and playonlinux.GetSettings("WINE_SYSTEM_ARCH") != "amd64")):
            self.general_elements["wineversion"].Append("System")
        self.general_elements["wineversion"].AppendItems(elements)
        version = playonlinux.GetSettings('VERSION',self.s_prefix)
        if(version == ''):
            self.general_elements["wineversion"].SetValue('System')
        else:
            self.general_elements["wineversion"].SetValue(version)

    def UpdateValues(self, selection):
        #print "Test"
        if(self.s_isPrefix == False):
            self.ChangeTitle(selection)
            #self.general_elements["wineversion"].SetValue(wine_versions.GetWineVersion(selection))
            #self.general_elements["wineversion"].Show()
            self.general_elements["wineprefix"].Show()
            self.general_elements["arguments"].Show()
            self.general_elements["arguments_text"].Show()

            #self.general_elements["name"].Show()
            #self.general_elements["wineversion_text"].Show()
            self.general_elements["wineprefix_text"].Show()
            self.general_elements["name"].SetEditable(True)

            #self.general_elements["name_text"].Show()
            self.general_elements["wineprefix"].SetValue(playonlinux.getPrefix(self.s_title))
            self.general_elements["arguments"].SetValue(playonlinux.getArgs(self.s_title))

            self.display_elements["folder_button"].SetLabel(_("Open program's directory"))
            if(os.path.exists(Variables.playonlinux_rep+"configurations/configurators/"+self.s_title)):
                self.configurator_title.Show()
                self.configurator_button.Show()
            else:
                self.configurator_title.Hide()
                self.configurator_button.Hide()
            self.configurator_title.SetLabel("{0} specific configuration".format(self.s_title.encode('utf-8','replace')))
            self.display_elements["pre_run_panel"].Show()
            self.display_elements["pre_run_text"].Show()
        else:
            self.s_prefix = selection
            self.s_title = selection
            #self.general_elements["wineversion"].Hide()
            self.general_elements["wineprefix"].Hide()
            #self.general_elements["name"].Hide()
            self.general_elements["name"].SetEditable(False)
            self.general_elements["name"].SetValue(self.s_prefix)
            self.general_elements["arguments"].Hide()
            self.general_elements["arguments_text"].Hide()
            #self.general_elements["wineversion_text"].Hide()
            self.general_elements["wineprefix_text"].Hide()
            #self.general_elements["name_text"].Hide()
            self.display_elements["folder_button"].SetLabel(_("Open virtual drive's directory"))
            self.configurator_title.Hide()
            self.configurator_button.Hide()
            self.display_elements["pre_run_panel"].Hide()
            self.display_elements["pre_run_text"].Hide()

        self.Refresh()
        self.elements = ["UseGLSL","DirectDrawRenderer","VideoMemorySize","OffscreenRenderingMode","RenderTargetModeLock","Multisampling","StrictDrawOrdering","MouseWarpOverride"]
        self.settings = wine.LoadRegValues(self.s_prefix,self.elements)
        #print self.settings
        self.get_current_settings("UseGLSL")
        self.get_current_settings("DirectDrawRenderer")
        self.get_current_settings("VideoMemorySize")
        self.get_current_settings("OffscreenRenderingMode")
        self.get_current_settings("RenderTargetModeLock")
        self.get_current_settings("Multisampling")
        self.get_current_settings("StrictDrawOrdering")
        self.get_current_settings("MouseWarpOverride")

        self.arch = playonlinux.GetSettings('ARCH',self.s_prefix)
        if(self.arch == ""):
            self.arch = "x86"

        self.UpdateVersions(self.arch)
        self.general_elements["winedebug"].SetValue(playonlinux.GetSettings("WINEDEBUG", self.s_prefix))
        try:
            self.display_elements["pre_run"].SetValue(open(os.environ["POL_USER_ROOT"]+"/configurations/pre_shortcut/"+self.s_title,'r').read())
        except:
            self.display_elements["pre_run"].SetValue("")


    def change_settings(self, event):
        param = event.GetId()
        if(param == 301):
            self.change_Direct3D_settings("UseGLSL")
        if(param == 302):
            self.change_Direct3D_settings("DirectDrawRenderer")
        if(param == 303):
            self.change_Direct3D_settings("VideoMemorySize")
        if(param == 304):
            self.change_Direct3D_settings("OffscreenRenderingMode")
        if(param == 305):
            self.change_Direct3D_settings("RenderTargetModeLock")
        if(param == 306):
            self.change_Direct3D_settings("Multisampling")
        if(param == 307):
            self.change_Direct3D_settings("StrictDrawOrdering")
        if(param == 401):
            self.change_DirectInput_settings("MouseWarpOverride")

    def misc_button(self, event):
        param = event.GetId()
        if(param == 402):
            if(self.s_isPrefix == False):
                playonlinux.open_folder(self.s_title)
            else:
                playonlinux.open_folder_prefix(self.s_prefix)
        if(param == 403):
            if(self.s_isPrefix == False):
                subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", self.s_title.encode('utf-8','replace'), "POL_OpenShell", self.s_title.encode('utf-8','replace')])
            else:
                subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", "--prefix", self.s_prefix.encode('utf-8','replace'), "POL_OpenShell"])

        if(param == 404):
            self.FileDialog = wx.FileDialog(self)
            self.FileDialog.SetDirectory("~")
            self.supported_files = "All|*.exe;*.EXE;*.msi;*.MSI\
            \|Windows executable (*.exe)|*.exe;*.EXE\
            \|Windows install file (*.msi)|*.msi;*MSI"
            self.FileDialog.SetWildcard(self.supported_files)
            self.FileDialog.ShowModal()
            if(self.FileDialog.GetPath() != ""):
                filename = self.FileDialog.GetPath().encode("utf-8","replace")
                dirname = os.path.dirname(filename)
                if(self.s_isPrefix == True):
                    subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", "--prefix", self.s_prefix.encode('utf-8','replace'), "POL_AutoWine", filename], cwd=dirname)
                else:
                    subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", self.s_title.encode('utf-8','replace'), "POL_AutoWine", filename], cwd=dirname)

        if(param == 201):
            if(self.s_isPrefix == False):
                subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", "--init", self.s_title.encode('utf-8','replace'), "POL_SetupWindow_shortcut_creator"])
            else:
                subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/POL_Command", "--init", "--prefix", self.s_prefix.encode('utf-8','replace'), "POL_SetupWindow_shortcut_creator"])

    def AddDisplayElement(self, title, shortname, elements, wine, num):
        elements.insert(0,"Default")
        wine.insert(0,"default")
        elemsize = (230,25)
        self.display_elements[shortname+"_text"] = wx.StaticText(self.panelDisplay, -1, title,pos=(15,19+num*40))

        self.display_elements[shortname] = wx.ComboBox(self.panelDisplay, 300+num, style=wx.CB_READONLY,pos=(300,17+num*40),size=elemsize)
        self.display_elements[shortname].AppendItems(wine)
        self.display_elements[shortname].SetValue(wine[0])
        wx.EVT_COMBOBOX(self, 300+num,  self.change_settings)


    def AddMiscElement(self, title, shortname, elements, wine, num):
        elements.insert(0,"Default")
        wine.insert(0,"default")
        elemsize = (230,25)
        self.display_elements[shortname+"_text"] = wx.StaticText(self.panelMisc, -1, title,pos=(15,19+num*40))

        self.display_elements[shortname] = wx.ComboBox(self.panelMisc, 400+num, style=wx.CB_READONLY,pos=(300,17+num*40),size=elemsize)
        self.display_elements[shortname].AppendItems(wine)
        self.display_elements[shortname].SetValue(wine[0])
        wx.EVT_COMBOBOX(self, 400+num,  self.change_settings)

    def AddMiscButton(self, title, shortname, num):
        self.display_elements[shortname+"_button"] = wx.Button(self.panelMisc, 400+num, "",pos=(15,19+num*40),size=(500,30))
        self.display_elements[shortname+"_button"].SetLabel(title)

        wx.EVT_BUTTON(self, 400+num,  self.misc_button)

    def AddMiscLongText(self, title, shortname, num):
        self.display_elements[shortname+"_text"] = wx.StaticText(self.panelMisc, -1, title,pos=(15,19+num*40))
        self.display_elements[shortname+"_panel"] = wx.Panel(self.panelMisc, -1, size=wx.Size(450,70),pos=(20,44+num*40))

        try:
            content = open(os.environ["POL_USER_ROOT"]+"/configurations/pre_shortcut/"+self.s_title,'r').read()
        except:
            content = ""

        self.display_elements[shortname] = wx.TextCtrl(self.display_elements[shortname+"_panel"], 400+num, content, size=wx.Size(448,68), pos=(2,2), style=Variables.widget_borders|wx.TE_MULTILINE)
        wx.EVT_TEXT(self, 405,  self.edit_shortcut)

    def edit_shortcut(self, event):
        content = self.display_elements["pre_run"].GetValue().encode("utf-8","replace")
        open(os.environ["POL_USER_ROOT"]+"/configurations/pre_shortcut/"+self.s_title,'w').write(content)

    def AddGeneralButton(self, title, shortname, num):
        self.general_elements[shortname+"_button"] = wx.Button(self.panelGeneral, 200+num, "",pos=(15,9+num*40),size=(520,30))
        self.general_elements[shortname+"_button"].SetLabel(title)

        wx.EVT_BUTTON(self, 200+num,  self.misc_button)

    def Display(self, nom):
        self.display_elements = {}
        self.panelDisplay = wx.Panel(self, -1)

        self.txtDisplay = wx.StaticText(self.panelDisplay, -1, _(nom), (10,10), wx.DefaultSize)
        self.txtDisplay.SetFont(self.fontTitle)

        self.AddPage(self.panelDisplay, nom)
        self.AddDisplayElement(_("GLSL Support"),"UseGLSL",["Enabled","Disabled"],["enabled","disabled"],1)
        self.AddDisplayElement(_("Direct Draw Renderer"),"DirectDrawRenderer",["GDI","OpenGL"],["gdi","opengl"],2)
        self.AddDisplayElement(_("Video memory size"),"VideoMemorySize",["32","64","128","256","384","512","768","1024","2048","3072","4096"],["32","64","128","256","384","512","768","1024","2048","3072","4096"],3)
        self.AddDisplayElement(_("Offscreen rendering mode"),"OffscreenRenderingMode",["fbo","backbuffer","pbuffer"],["fbo","backbuffer","pbuffer"],4)
        self.AddDisplayElement(_("Render target mode lock"),"RenderTargetModeLock",["disabeld","readdraw","readtex"],["disabled","readdraw","readtex"],5)
        self.AddDisplayElement(_("Multisampling"),"Multisampling",["Enabled","Disabled"],["enabled","disabled"],6)
        self.AddDisplayElement(_("Strict Draw Ordering"),"StrictDrawOrdering",["enabled","disabled"],["enabled","disabled"],7)


    def Miscellaneous(self, nom):
        self.misc_elements = {}
        self.panelMisc = wx.Panel(self, -1)

        self.txtMisc = wx.StaticText(self.panelMisc, -1, _(nom), (10,10), wx.DefaultSize)
        self.txtMisc.SetFont(self.fontTitle)

        self.AddMiscElement(_("Mouse warp override"),"MouseWarpOverride",["Enabled","Disabled","Force"],["enable","disable","force"],1)
        self.AddMiscButton("","folder",2)
        self.AddMiscButton(_("Open a shell"),"shell",3)
        self.AddMiscButton(_("Run a .exe file in this virtual drive"),"exerun",4)
        self.AddMiscLongText(_("Command to exec before running the program"),"pre_run",5)

        self.AddPage(self.panelMisc, nom)

    def assign(self, event):
        version = self.general_elements["wineversion"].GetValue()
        if(version != 'System'):
            playonlinux.SetSettings('VERSION',version,self.s_prefix)
        else:
            playonlinux.DeleteSettings('VERSION',self.s_prefix)
    def assignPrefix(self, event):
        if(wx.YES == wx.MessageBox(_("Be careful!\nIf you change "+self.s_title+"'s virtual drive, you are likekely to break it.\nDo this only if you know what you are doing.\n\nAre you sure you want to continue?"),os.environ["APPLICATION_TITLE"] ,style=wx.YES_NO | wx.ICON_QUESTION)):
            drive = self.general_elements["wineprefix"].GetValue()
            playonlinux.SetWinePrefix(self.s_title, drive)
        else:
            self.general_elements["wineprefix"].SetValue(self.s_prefix)

    def ReleaseTyping(self, event):
        self.typing = False

    def setargs(self, event):
        new_args = self.general_elements["arguments"].GetValue()
        playonlinux.writeArgs(self.s_title, new_args)

    def setwinedebug(self, event):
        new_winedebug = self.general_elements["winedebug"].GetValue()
        playonlinux.SetSettings('WINEDEBUG', new_winedebug, self.s_prefix)

    def setname(self, event):
        new_name = self.general_elements["name"].GetValue()
        if(self.changing_selection == False):
            self.typing = True
        else:
            self.changing_selection = False

        if(not os.path.exists(Variables.playonlinux_rep+"shortcuts/"+new_name)):
            try:
                os.rename(Variables.playonlinux_rep+"icones/32/"+self.s_title,Variables.playonlinux_rep+"icones/32/"+new_name)
            except:
                pass


            try:
                os.rename(Variables.playonlinux_rep+"icones/full_size/"+self.s_title,Variables.playonlinux_rep+"icones/full_size/"+new_name)
            except:
                pass

            try:
                os.rename(Variables.playonlinux_rep+"configurations/configurators/"+self.s_title,Variables.playonlinux_rep+"configurations/configurators/"+new_name)
            except:
                pass

            try:
                os.rename(Variables.playonlinux_rep+"shortcuts/"+self.s_title,Variables.playonlinux_rep+"shortcuts/"+new_name)
                self.s_title = new_name
                self.s_prefix = playonlinux.getPrefix(self.s_title)
            except:
                pass



            #if(self.changing == False):
            #       self.Parent.Parent.list_software()
            #else:
            #       self.changing = False


class MainWindow(wx.Frame):
    def __init__(self,parent,id,title,shortcut, isPrefix = False):
        wx.Frame.__init__(self, parent, -1, title, size = (800, 450), style = wx.CLOSE_BOX | wx.CAPTION | wx.MINIMIZE_BOX)
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.SetTitle(_('{0} configuration').format(os.environ["APPLICATION_TITLE"]))
        #self.panelFenp = wx.Panel(self, -1)

        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_NOBORDER)

        self.panelEmpty = wx.Panel(self.splitter, -1)
        self.onglets = Onglets(self.splitter)

        self.noselect = wx.StaticText(self.panelEmpty, -1, _('Please select a program or a virtual drive to configure'),pos=(0,150),style=wx.ALIGN_RIGHT)
        self.noselect.SetPosition(((600-self.noselect.GetSize()[0])/2,150))

        self.noselect.Wrap(600)
        if(isPrefix == True):
            self.onglets.s_isPrefix = True
            self.onglets.s_prefix = shortcut
        else:
            self.onglets.s_isPrefix = False
            self.onglets.s_title = shortcut

        self.images = wx.ImageList(16, 16)

        self.splitter_list = wx.SplitterWindow(self.splitter, -1, style=wx.SP_NOBORDER)

        self.list_game = wx.TreeCtrl(self.splitter_list, 900, size = wx.DefaultSize, style=wx.TR_HIDE_ROOT)
        self.control_game = wx.Panel(self.splitter_list, -1)

        self.AddPrefix = wx.Button(self.control_game, 1001, _("New"), pos=(0,0),size=(95+10*Variables.windows_add_playonmac,30))
        self.DelPrefix = wx.Button(self.control_game, 1002, _("Remove"), pos=(100,0), size=(95+10*Variables.windows_add_playonmac,30))

        wx.EVT_BUTTON(self, 1001, self.NewPrefix)
        wx.EVT_BUTTON(self, 1002, self.DeletePrefix)

        self.splitter_list.SplitHorizontally(self.list_game, self.control_game)
        self.splitter_list.SetSashPosition(423)
        self.splitter_list.SetSashGravity(0.94)

        self.list_game.SetSpacing(0);
        self.list_game.SetImageList(self.images)


        self.splitter.SplitVertically(self.splitter_list,self.panelEmpty)
        self.splitter.SetSashPosition(200)

        self.onglets.General(_("General"))
        self.onglets.Wine("Wine")
        self.onglets.Packages(_("Install components"))
        self.onglets.Display(_("Display"))
        self.onglets.Miscellaneous(_("Miscellaneous"))

        self.list_software()

        self.onglets.panelGeneral.Bind(wx.EVT_LEFT_UP, self.onglets.ReleaseTyping)
        wx.EVT_TREE_SEL_CHANGED(self, 900, self.change_program_to_selection)
        #self.change_program(shortcut,isPrefix)

        self.timer = wx.Timer(self, 1)
        self.Bind(wx.EVT_TIMER, self.AutoReload, self.timer)

        self.timer.Start(500)
        self.oldreload = None
        self.oldimg = None
        self.oldpref = None
        self.oldver32 = None
        self.olderver64 = None
        #if(self.onglets.s_isPrefix == False or not self.onglets.s_prefix == "default"):
        self.AutoReload(self)

    def NewPrefix(self, event):
        #self.name = wx.GetTextFromUser(_("Choose the name of the virtual drive"))
        #if(self.name != ""):
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/create_prefix"])

    def DeletePrefix(self, event):
        if(self.onglets.s_isPrefix == True):
            if(self.onglets.s_prefix == "default"):
                wx.MessageBox(_("This virtual drive is protected"), os.environ["APPLICATION_TITLE"])
            else:
                if(wx.YES == wx.MessageBox(_("Are you sure you want to delete {0} virtual drive ?").format(self.onglets.s_prefix.encode("utf-8","replace")).decode("utf-8","replace"), os.environ["APPLICATION_TITLE"], style=wx.YES_NO | wx.ICON_QUESTION)):
                    mylist = os.listdir(Variables.playonlinux_rep+"/shortcuts")
                    for element in mylist:
                        if(playonlinux.getPrefix(element).lower() == self.onglets.s_prefix.lower()):
                            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/uninstall", "--non-interactive", element])
                    self._delete_directory(Variables.playonlinux_rep+"/wineprefix/"+self.onglets.s_prefix)
        else:
            if(wx.YES == wx.MessageBox(_("Are you sure you want to delete {0} ?").format(self.onglets.s_title.encode("utf-8","replace")).decode("utf-8","replace"), os.environ["APPLICATION_TITLE"], style=wx.YES_NO | wx.ICON_QUESTION)):
                subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/uninstall", "--non-interactive", self.onglets.s_title.encode('utf-8', 'replace')])

        self.onglets.s_isPrefix = True
        self.change_program("default",True)
        self.list_game.SelectItem(self.prefixes_item["default"])

    def _delete_directory(self, root_path):
        """
        Remove a directory tree, making sure no directory rights get in the way.
        It assumes everything is owned by the user however.
        """

        # Handle symlink
        if os.path.islink(root_path):
            os.remove(root_path)
            # Shall we warn the user that the target prefix has not been cleared?
        else:
            # need exec right to dereference content
            # need read right to list content
            # need write right to remove content
            needed_dir_rights = stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR

            # topdown=True, the default, is necessary to fix directories rights
            # before trying to list them
            for dirname, dirs, files in os.walk(root_path):
                for dir in dirs:
                    fullpath = os.path.join(dirname, dir)
                    # To speed up the process, only modify metadata when necessary
                    attr = os.lstat(fullpath)
                    if attr.st_mode & needed_dir_rights != needed_dir_rights:
                        print "%s rights need fixing" % fullpath
                        os.chmod(fullpath, needed_dir_rights)

            # Alright, now we should be able to proceed
            shutil.rmtree(root_path)

    def AutoReload(self, event):
        if(self.onglets.typing == False):
            reload = os.path.getmtime(Variables.playonlinux_rep+"/shortcuts")
            if(reload != self.oldreload):
                self.list_software()
                self.oldreload = reload

            reloadimg = os.path.getmtime(Variables.playonlinux_rep+"/icones/32")
            if(reloadimg != self.oldimg):
                self.list_software()
                self.oldimg = reloadimg

            reloadpref = os.path.getmtime(Variables.playonlinux_rep+"/wineprefix")
            if(reloadpref != self.oldpref):
                self.list_software()
                self.oldpref = reloadpref

            reloadver32 = os.path.getmtime(Variables.playonlinux_rep+"/wine/"+Variables.os_name+"-x86/")
            reloadver64 = os.path.getmtime(Variables.playonlinux_rep+"/wine/"+Variables.os_name+"-amd64/")

            if(reloadver32 != self.oldver32 or reloadver64 != self.oldver64):
                self.oldver32 = reloadver32
                self.oldver64 = reloadver64
                self.onglets.UpdateVersions(self.onglets.arch)

    def change_program_to_selection(self, event):
        parent =  self.list_game.GetItemText(self.list_game.GetItemParent(self.list_game.GetSelection()))
        self.current_sel = self.list_game.GetItemText(self.list_game.GetSelection())

        if(parent == "#ROOT#"):
            self.onglets.s_isPrefix = True
        else:
            self.onglets.s_isPrefix = False

        self.change_program(self.current_sel,self.onglets.s_isPrefix)

    def change_program(self, new_prgm,isPrefix = False):
        self.onglets.changing_selection = True
        if(isPrefix == True):
            self.onglets.s_isPrefix = True
            if(self.current_sel == "default"):
                self.splitter.Unsplit()
                self.splitter.SplitVertically(self.splitter_list,self.panelEmpty)
                self.splitter.SetSashPosition(200)
            else:
                self.splitter.Unsplit()
                self.splitter.SplitVertically(self.splitter_list,self.onglets)
                self.splitter.SetSashPosition(200)
        else:
            self.splitter.Unsplit()
            self.splitter.SplitVertically(self.splitter_list,self.onglets)
            self.splitter.SetSashPosition(200)
        self.onglets.UpdateValues(new_prgm)
        self.Refresh()
        self.SetFocus()
        try:
            self.GetTopWindow().Raise()
        except:
            pass

    def list_software(self):
        self.games = os.listdir(Variables.playonlinux_rep+"shortcuts/")
        self.games.sort()

        self.prefixes = os.listdir(Variables.playonlinux_rep+"wineprefix/")
        self.prefixes.sort()

        self.games_item = {}
        self.prefixes_item = {}

        try:
            self.games.remove(".DS_Store")
        except:
            pass

        try:
            self.prefixes.remove(".DS_Store")
        except:
            pass

        self.list_game.DeleteAllItems()
        self.images.RemoveAll()
        root = self.list_game.AddRoot("#ROOT#")

        self.i = 0
        for prefix in self.prefixes:
            if(os.path.isdir(Variables.playonlinux_rep+"wineprefix/"+prefix)):
                self.prefixes_item[prefix] = self.list_game.AppendItem(root, prefix, self.i)

                if(os.path.exists(Variables.playonlinux_rep+"/wineprefix/"+prefix+"/icon")):
                    self.file_icone = Variables.playonlinux_rep+"/wineprefix/"+prefix+"/icon"
                else:
                    try:
                        archdd = playonlinux.GetSettings('ARCH',prefix)
                        if(archdd == "amd64"):
                            archdd = "64"
                        else:
                            archdd = "32"
                    except:
                        archdd = "32"
                    self.file_icone = Variables.playonlinux_env+"/resources/images/menu/virtual_drive_"+archdd+".png"

                try:
                    self.bitmap = wx.Image(self.file_icone)
                    self.bitmap.Rescale(16,16,wx.IMAGE_QUALITY_HIGH)
                    self.bitmap = self.bitmap.ConvertToBitmap()
                    self.images.Add(self.bitmap)
                except:
                    pass

                self.list_game.SetItemBold(self.prefixes_item[prefix], True)

                for game in self.games: #METTRE EN 32x32
                    if(playonlinux.getPrefix(game).lower() == prefix.lower()):
                        if(os.path.exists(Variables.playonlinux_rep+"/icones/32/"+game)):
                            self.file_icone = Variables.playonlinux_rep+"/icones/32/"+game
                        else:
                            self.file_icone = Variables.playonlinux_env+"/etc/playonlinux32.png"

                        try:
                            self.bitmap = wx.Image(self.file_icone)
                            self.bitmap.Rescale(16,16,wx.IMAGE_QUALITY_HIGH)
                            self.bitmap = self.bitmap.ConvertToBitmap()
                            self.images.Add(self.bitmap)
                        except:
                            pass
                        self.i += 1
                        self.games_item[game] = self.list_game.AppendItem(self.prefixes_item[prefix], game, self.i)

                self.i += 1

        self.list_game.ExpandAll()
        try:
            if(self.onglets.s_isPrefix == True):
                self.list_game.SelectItem(self.prefixes_item[self.onglets.s_prefix.encode("utf-8","replace")])
            else:
                self.list_game.SelectItem(self.games_item[self.onglets.s_title.encode("utf-8","replace")])
        except:
            self.onglets.s_isPrefix = True
            self.change_program("default",True)
            self.list_game.SelectItem(self.prefixes_item["default"])

    def app_Close(self, event):
        self.Destroy()

    def apply_settings(self, event):
        self.Destroy()

########NEW FILE########
__FILENAME__ = debug
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Pâris Quentin
# Copyright (C) 2007-2010 PlayOnLinux Team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os, sys, string, shutil
import wx, time, shlex
#from subprocess import Popen,PIPE

import wine_versions
import lib.playonlinux as playonlinux
import lib.wine as wine
import lib.Variables as Variables
import lib.lng as lng

class MainWindow(wx.Frame):
    def __init__(self,parent,id,title,logcheck="/dev/null",logtype=None):
        self.logtype = 1
        self.logfile = None
        self.logname = ""

        wx.Frame.__init__(self, parent, -1, title, size = (800, 600+Variables.windows_add_size), style = wx.CLOSE_BOX | wx.CAPTION | wx.MINIMIZE_BOX)
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.SetTitle(_('{0} debugger').format(os.environ["APPLICATION_TITLE"]))
        #self.panelFenp = wx.Panel(self, -1)

        self.prefixes_item = {}
        self.logs_item = {}

        self.splitter = wx.SplitterWindow(self, -1, style=wx.SP_NOBORDER)
        self.panelEmpty = wx.Panel(self.splitter, -1)
        self.panelNotEmpty = wx.Panel(self.splitter, -1)


        self.noselect = wx.StaticText(self.panelEmpty, -1, _('Please select a debug file'),pos=(0,150),style=wx.ALIGN_RIGHT)
        self.noselect.SetPosition(((570-self.noselect.GetSize()[0])/2,250))
        self.noselect.Wrap(500)


        self.images = wx.ImageList(16, 16)

        self.list_game = wx.TreeCtrl(self.splitter, 900, size = wx.DefaultSize, style=wx.TR_HIDE_ROOT)
        wx.EVT_TREE_SEL_CHANGED(self, 900, self.analyseLog)


        self.list_game.SetSpacing(0);
        self.list_game.SetImageList(self.images)


        self.list_software()

        self.throttling = False
        self.line_buffer = ""
        self.timer = wx.Timer(self, 1)
        self.Bind(wx.EVT_TIMER, self.AutoReload, self.timer)
        self.AutoReload(self)
        self.timer.Start(10)
        self.logfile = ""

        # Debug control
        self.panelText = wx.Panel(self.panelNotEmpty, -1, size=(590,500), pos=(2,2)) # Hack, wxpython bug
        self.log_reader = wx.TextCtrl(self.panelText, 100, "", size=wx.Size(590,500), pos=(2,2), style=Variables.widget_borders|wx.TE_RICH2|wx.TE_READONLY|wx.TE_MULTILINE)
        self.openTextEdit = wx.Button(self.panelNotEmpty, 101, _("Locate this logfile"), size=(400,30), pos=(70,512))
        self.reportProblem = wx.Button(self.panelNotEmpty, 102, "", size=(400,30), pos=(70,552))

        if(logcheck == "/dev/null"):
            self.HideLogFile()
        else:
            self.analyseReal(logtype,logcheck)
        wx.EVT_BUTTON(self,101,self.locate)
        wx.EVT_BUTTON(self,102,self.bugReport)

        #self.log_reader.SetDefaultStyle(wx.TextAttr(font=wx.Font(13,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_NORMAL)))

    def bugReport(self, event):
        os.system('env LOGTITLE="'+self.logname+'" bash "'+os.environ["PLAYONLINUX"]+'/bash/bug_report" &')
        self.reportProblem.Enable(False)

    def locate(self, event):
        if(self.logtype == 0):
            dirname = Variables.playonlinux_rep+"wineprefix/"+self.logname+"/"
            filename = 'playonlinux.log'
        if(self.logtype == 1):
            dirname = Variables.playonlinux_rep+"logs/"+self.logname+"/"
            filename = self.logname+".log"
        wx.MessageBox(_("The file is named : {0}").format(filename), os.environ["APPLICATION_TITLE"])

        playonlinux.POL_Open(dirname)

    def ShowLogFile(self):
        self.splitter.Unsplit()
        self.splitter.SplitVertically(self.list_game,self.panelNotEmpty)
        self.splitter.SetSashPosition(200)

    def HideLogFile(self):
        self.splitter.Unsplit()
        self.splitter.SplitVertically(self.list_game,self.panelEmpty)
        self.splitter.SetSashPosition(200)

    def AppendStyledText(self, line):
        ins = self.log_reader.GetInsertionPoint()
        leng = len(line)
        if(leng > 200):
            line=line[0:200]
            leng=200

        self.log_reader.AppendText(line.decode('utf-8','replace'))

        self.bold = wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD)

        if(line[0:5] == "wine:"):
            self.log_reader.SetStyle(ins, ins+5, wx.TextAttr("red", wx.NullColour))

        elif(line[0:6] == "fixme:"):
            self.log_reader.SetStyle(ins, ins+leng, wx.TextAttr(wx.Colour(100,100,100), wx.NullColour))

        elif(self.logtype == 1 and leng > 19 and line[17:20] == " - "):
            self.log_reader.SetStyle(ins, ins+17, wx.TextAttr("black", wx.NullColour, self.bold))
        elif(self.logtype == 0 and leng > 21 and line[19:22] == " - "):
            self.log_reader.SetStyle(ins, ins+19, wx.TextAttr("black", wx.NullColour, self.bold))
        else:
            self.log_reader.SetStyle(ins, ins+leng, wx.TextAttr("black", wx.NullColour))

    def AutoReload(self, event):
        if(self.logfile != "" and self.logfile != None):
            # Max number of lines to display per reload
            # Would be better if adjusted to effective display capability
            max_lines = 20

            circular_buffer = [u'' for i in range(max_lines)]
            index = 0
            # Did we overwrote lines in the circular buffer?
            wrapped_buffer = False
            overwritten_lines = 0

            while True:
                line = self.logfile.readline()
                if not line:
                    # Reached the current bottom of log, disable throttling
                    # Could mean we never disable it if we're overflowed with logs 
                    # from the very beginning
                    self.throttling = True
                    break

                # Line buffering
                self.line_buffer += line
                if line[-1] != '\n':
                    break
                circular_buffer[index] = self.line_buffer
                self.line_buffer = ""

                index += 1
                if wrapped_buffer:
                    overwritten_lines += 1

                # Buffer wrapping
                if index >= max_lines:
                    if not self.throttling:
                        break
                    index = 0
                    wrapped_buffer = True

            if wrapped_buffer:
                if overwritten_lines > 0:
                    self.AppendStyledText("...skipped %d line(s)...\n" % overwritten_lines)
                for k in range(index, max_lines):
                    self.AppendStyledText(circular_buffer[k])
            for k in range(0, index):
                self.AppendStyledText(circular_buffer[k])

    def analyseLog(self, event):
        parent =  self.list_game.GetItemText(self.list_game.GetItemParent(self.list_game.GetSelection()))
        selection =  self.list_game.GetItemText(self.list_game.GetSelection())
        if(parent == _("Virtual drives")):
            parent = 0
        else:
            parent = 1
        self.analyseReal(parent, selection)

    def analyseReal(self, parent, selection):
        self.ShowLogFile()
        self.throttling = False
        self.line_buffer = ""
        self.log_reader.Clear()
        try:
            if(parent == 0):
                checkfile = Variables.playonlinux_rep+"wineprefix/"+selection+"/playonlinux.log"
                self.logfile = open(checkfile, 'r')
                self.logsize = os.path.getsize(checkfile)
                self.logname = selection
                if(self.logsize - 10000 > 0):
                    self.logfile.seek(self.logsize - 10000) # 10 000 latest chars should be sufficient
                self.logtype = 0
                self.reportProblem.Hide()

            if(parent == 1):
                checkfile = Variables.playonlinux_rep+"logs/"+selection+"/"+selection+".log"
                self.logfile = open(checkfile, 'r')
                self.logsize = os.path.getsize(checkfile)
                self.logname = selection
                if(self.logsize - 10000 > 0):
                    self.logfile.seek(self.logsize - 10000) # 10 000 latest chars should be sufficient
                self.logtype = 1
                if(os.environ["DEBIAN_PACKAGE"] == "FALSE"):
                    self.reportProblem.Show()
                    self.reportProblem.Enable(True)
                    self.reportProblem.SetLabel(_("Report a problem about {0}").format(self.logname))


        except:
            pass

    def list_software(self):
        self.prefixes = os.listdir(Variables.playonlinux_rep+"wineprefix/")
        self.prefixes.sort()

        self.logs = os.listdir(Variables.playonlinux_rep+"logs/")
        self.logs.sort()

        try:
            self.prefixes.remove(".DS_Store")
        except:
            pass

        self.list_game.DeleteAllItems()
        self.images.RemoveAll()

        root = self.list_game.AddRoot("")
        self.scripts_entry = self.list_game.AppendItem(root, _("Install scripts"), 1)
        self.prefixes_entry = self.list_game.AppendItem(root, _("Virtual drives"), 0)

        self.file_icone = Variables.playonlinux_env+"/resources/images/icones/generic.png"
        self.bitmap = wx.Image(self.file_icone)
        self.bitmap.Rescale(16,16,wx.IMAGE_QUALITY_HIGH)
        self.bitmap = self.bitmap.ConvertToBitmap()
        self.images.Add(self.bitmap)
        self.images.Add(self.bitmap)


        self.i = 2
        for prefix in self.prefixes:
            if(os.path.isdir(Variables.playonlinux_rep+"wineprefix/"+prefix)):

                if(os.path.exists(Variables.playonlinux_rep+"/wineprefix/"+prefix+"/icon")):
                    self.file_icone = Variables.playonlinux_rep+"/wineprefix/"+prefix+"/icon"
                else:
                    try:
                        archdd = playonlinux.GetSettings('ARCH',prefix)
                        if(archdd == "amd64"):
                            archdd = "64"
                        else:
                            archdd = "32"
                    except:
                        archdd = "32"
                    self.file_icone = Variables.playonlinux_env+"/resources/images/menu/virtual_drive_"+archdd+".png"

                try:
                    self.bitmap = wx.Image(self.file_icone)
                    self.bitmap.Rescale(16,16,wx.IMAGE_QUALITY_HIGH)
                    self.bitmap = self.bitmap.ConvertToBitmap()
                    self.images.Add(self.bitmap)
                except:
                    pass

                self.prefixes_item[prefix] = self.list_game.AppendItem(self.prefixes_entry, prefix, self.i)
                self.i += 1

        for log in self.logs:
            if(not "_" in log and os.path.isdir(Variables.playonlinux_rep+"logs/"+log)):
                self.file_icone =  Variables.playonlinux_env+"/resources/images/menu/manual.png"

                try:
                    self.bitmap = wx.Image(self.file_icone)
                    self.bitmap.Rescale(16,16,wx.IMAGE_QUALITY_HIGH)
                    self.bitmap = self.bitmap.ConvertToBitmap()
                    self.images.Add(self.bitmap)
                except:
                    pass

                self.logs_item[log] = self.list_game.AppendItem(self.scripts_entry, log, self.i)
                self.i += 1

        self.list_game.Collapse(self.scripts_entry)
        self.list_game.Collapse(self.prefixes_entry)
        self.list_game.ExpandAll()
    def app_Close(self, event):
        self.Destroy()

    def apply_settings(self, event):
        self.Destroy()

########NEW FILE########
__FILENAME__ = guiv3
#!/usr/bin/python
# -*- coding:Utf-8 -*-

# Copyright (C) 2008 Pâris Quentin
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.



import wx, wx.animate, os, getopt, sys, urllib, signal, time, string, urlparse, codecs, time, threading, socket
from subprocess import Popen,PIPE
import lib.Variables as Variables
import lib.lng, lib.playonlinux as playonlinux
lib.lng.Lang()


class Download(threading.Thread):
    def __init__(self, url, local):
        threading.Thread.__init__(self)
        self.url = url
        self.local = local
        self.taille_fichier = 0
        self.taille_bloc = 0
        self.nb_blocs = 0
        self.finished = False
        self.start()
        self.failed = False

    def onHook(self, nb_blocs, taille_bloc, taille_fichier):
        self.nb_blocs = nb_blocs
        self.taille_bloc = taille_bloc
        self.taille_fichier = taille_fichier

    def download(self):
        try:
            urllib.urlretrieve(self.url, self.local, reporthook = self.onHook)
        except:
            self.failed = True
        self.finished = True

    def run(self):
        self.download()

class POL_SetupFrame(wx.Frame): #fenêtre principale
    def __init__(self, titre, POL_SetupWindowID, Arg1, Arg2, Arg3):
        wx.Frame.__init__(self, None, -1, title = titre, style = wx.CLOSE_BOX | wx.CAPTION | wx.MINIMIZE_BOX, size = (520, 398+Variables.windows_add_size))
        self.bash_pid = POL_SetupWindowID
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.gauge_i = 0
        self.fichier = ""
        self.last_time = int(round(time.time() * 1000))
        self.ProtectedWindow = False

        # Le fichier de lecture

        if(Arg1 == "None"):
            self.small_image = wx.Bitmap(Variables.playonlinux_env+"/resources/images/setups/default/top.png")
        else:
            self.small_image = wx.Bitmap(Arg1)

        self.small_x = 520 - self.small_image.GetWidth()

        if(Arg2 == "None"):
            if(os.environ["POL_OS"] == "Linux"):
                self.big_image = wx.Bitmap(Variables.playonlinux_env+"/resources/images/setups/default/playonlinux.jpg")
            else:
                self.big_image = wx.Bitmap(Variables.playonlinux_env+"/resources/images/setups/default/playonmac.jpg")
        else:
            self.big_image = wx.Bitmap(Arg2)

        if(Arg3 == "protect"):
            self.ProtectedWindow = True
        self.oldfichier = ""
        
        self.make_gui()

        wx.EVT_CLOSE(self, self.Cancel)

    def make_gui(self):
        # Fonts
        if(os.environ["POL_OS"] == "Mac"):
            self.fontTitre = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.fontText = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)
        else :
            self.fontTitre = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.fontText = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)

        # GUI elements
        self.panel = wx.Panel(self, -1, pos=(0,0), size=((520, 398+Variables.windows_add_size)))
        self.header = wx.Panel(self.panel, -1, style=Variables.widget_borders, size=(522,65))
        self.header.SetBackgroundColour((255,255,255))
        self.footer = wx.Panel(self.panel, -1, size=(522,45), pos=(-1,358), style=Variables.widget_borders)

        # Panels
        self.MainPanel = wx.Panel(self.panel, -1, pos=(150,0), size=(370,356))
        self.MainPanel.SetBackgroundColour((255,255,255))


        # Images
        self.top_image = wx.StaticBitmap(self.header, -1, self.small_image, (self.small_x,0), wx.DefaultSize)
        self.left_image = wx.StaticBitmap(self.panel, -1, self.big_image, (0,0), wx.DefaultSize)


        # Text
        self.titre_header = wx.StaticText(self.header, -1, _('{0} Wizard').format(os.environ["APPLICATION_TITLE"]),pos=(5,5), size=(340,356),style=wx.ST_NO_AUTORESIZE)
        self.titre_header.SetFont(self.fontTitre)
        self.titre_header.SetForegroundColour((0,0,0)) # For dark themes

        self.texte = wx.StaticText(self.panel, -1, "",pos=(20,80),size=(480,275),style=wx.ST_NO_AUTORESIZE)
        self.texte_bis = wx.StaticText(self.panel, -1, "",size=(480,30),style=wx.ST_NO_AUTORESIZE)
        self.titre = wx.StaticText(self.header, -1, "",pos=(20,30), size=(340,356),style=wx.ST_NO_AUTORESIZE)
        self.titre.SetForegroundColour((0,0,0)) # For dark themes

        self.texteP = wx.StaticText(self.MainPanel, -1, "",pos=(5,50))
        self.texteP.SetForegroundColour((0,0,0)) # For dark themes

        self.titreP = wx.StaticText(self.MainPanel, -1,"",pos=(5,5), size=(340,356))
        self.titreP.SetFont(self.fontTitre)
        self.titreP.SetForegroundColour((0,0,0)) # For dark themes

        self.txtEstimation = wx.StaticText(self.panel, -1, "",size=(480,30),style=wx.ST_NO_AUTORESIZE)
        self.register_link = ""


        # Buttons
        

        if(os.environ["POL_OS"] == "Linux"):
            self.CancelButton = wx.Button(self.footer, wx.ID_CANCEL, _("Cancel"), pos=(430,0),size=(85,37))
            self.NextButton = wx.Button(self.footer, wx.ID_FORWARD, _("Next"), pos=(340,0),size=(85,37))
        else:
            self.CancelButton = wx.Button(self.footer, wx.ID_CANCEL, _("Cancel"), pos=(420,-3),size=(85,37))
            self.NextButton = wx.Button(self.footer, wx.ID_FORWARD, _("Next"), pos=(330,-3),size=(85,37))
   
        if(self.ProtectedWindow == True):
            self.CancelButton.Enable(False)
   
            
        self.InfoScript = wx.StaticBitmap(self.footer, -1, wx.Bitmap(os.environ['PLAYONLINUX']+"/resources/images/setups/about.png"), pos=(10,8))
        self.InfoScript.Hide()
        self.script_ID = 0
        self.InfoScript.Bind(wx.EVT_LEFT_DOWN, self.InfoClick)
        self.InfoScript.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

        self.NoButton = wx.Button(self.footer, wx.ID_NO, _("No"), pos=(430,0),size=(85,37))
        self.YesButton = wx.Button(self.footer, wx.ID_YES, _("Yes"), pos=(340,0), size=(85,37))
        self.browse = wx.Button(self.panel, 103, _("Browse"), size=(130,40))
        self.browse_text = wx.StaticText(self.panel, -1, "")
        self.browse_image = wx.StaticBitmap(self.panel, -1, wx.Bitmap(os.environ['PLAYONLINUX']+"/etc/playonlinux.png"))

        # D'autres trucs
        self.champ = wx.TextCtrl(self.panel, 400, "",size=(300,22))

        self.bigchamp = wx.TextCtrl(self.panel, -1, "",size=wx.Size(460,240), pos=(30,105),style=Variables.widget_borders|wx.TE_MULTILINE)
        self.MCheckBox = wx.CheckBox(self.panel, 302, _("I Agree"), pos=(20,325))
        self.PCheckBox = wx.CheckBox(self.panel, 304, _("Show virtual drives"), pos=(20,325))
        self.Menu = wx.ListBox(self.panel, 104, pos=(25,105),size=(460,220), style=Variables.widget_borders)
        self.scrolled_panel = wx.ScrolledWindow(self.panel, -1, pos=(20,100), size=(460,220), style=Variables.widget_borders|wx.HSCROLL|wx.VSCROLL)
        self.scrolled_panel.SetBackgroundColour((255,255,255))
        self.texte_panel = wx.StaticText(self.scrolled_panel, -1, "",pos=(5,5))

        self.gauge = wx.Gauge(self.panel, -1, 50, size=(375, 20))
        self.WaitButton = wx.Button(self.panel, 310, "", size=(250,25))

        
        
        self.animation = wx.StaticBitmap(self.panel, -1, self.GetLoaderFromAngle(1), (228,170))
        self.current_angle = 1
    
        self.images = wx.ImageList(22, 22)
        self.MenuGames = wx.TreeCtrl(self.panel, 111, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|Variables.widget_borders, pos=(25,105),size=(460,220))
        self.MenuGames.SetImageList(self.images)
        self.MenuGames.SetSpacing(0)
        

        # Login
        self.login = wx.StaticText(self.panel, -1, _("Login: "),pos=(20,120),size=(460,20))
        self.password = wx.StaticText(self.panel, -1, _("Password: "),pos=(20,150),size=(460,20))
        self.loginbox =  wx.TextCtrl(self.panel, -1, "",size=(250,22),pos=(200,115))
        self.passbox =  wx.TextCtrl(self.panel, -1, "",size=(250,22),pos=(200,145), style=wx.TE_PASSWORD)
        self.register = wx.HyperlinkCtrl(self.panel, 303, _("Register"), "", pos=(20,180))
        self.register.SetNormalColour(wx.Colour(0,0,0))

        # Fixed Events
        wx.EVT_BUTTON(self, wx.ID_YES, self.release_yes)
        wx.EVT_BUTTON(self, wx.ID_NO, self.release_no)
        wx.EVT_BUTTON(self, wx.ID_CANCEL , self.Cancel)
        wx.EVT_BUTTON(self, 103, self.Parcourir)
        wx.EVT_CHECKBOX(self, 302, self.agree)
        wx.EVT_CHECKBOX(self, 304, self.switch_menu)
        wx.EVT_HYPERLINK(self, 303, self.POL_register)

        # Debug Window
        self.debugImage = wx.StaticBitmap(self.panel, -1, wx.Bitmap(os.environ["PLAYONLINUX"]+"/resources/images/setups/face-sad.png"), (196,130))
        self.debugZone = wx.TextCtrl(self.panel, -1, "",size=wx.Size(440,82), pos=(40,274),style=Variables.widget_borders|wx.TE_MULTILINE|wx.TE_READONLY)

        # Hide all
        self.Destroy_all()
        self.Result = ""
        self.animation.Show()
        self.footer.Hide()
        
        # Set the timer
        self.timer = wx.Timer(self, 3)
        self.Bind(wx.EVT_TIMER, self.TimerAction, self.timer)
        self.timer.Start(100)
        self.Timer_downloading = False
        self.Timer_animate = True
        
    def GetLoaderFromAngle(self, angle):
        if(angle >= 1 and angle <= 12):
            image = wx.Image(Variables.playonlinux_env+"/resources/images/setups/wait/"+str(angle)+".png")
        return image.ConvertToBitmap()
        
    def Destroy_all(self):
        self.footer.Show()
        self.Result = None
        self.header.Hide()
        self.left_image.Hide()
        self.CancelButton.Hide()
        self.MainPanel.Hide()
        self.NextButton.Hide()
        self.NoButton.Hide()
        self.YesButton.Hide()
        self.browse.Hide()
        self.browse_text.Hide()
        self.browse_image.Hide()
        self.champ.Hide()
        self.bigchamp.Hide()
        self.texte.Hide()
        self.texte_bis.Hide()
        self.texteP.Hide()
        self.titre.Hide()
        self.Menu.Hide()
        self.MenuGames.Hide()
        self.scrolled_panel.Hide()
        self.gauge.Hide()
        self.txtEstimation.Hide()
        self.texte_panel.Hide()
        self.MCheckBox.Hide()
        self.PCheckBox.Hide()
        self.NextButton.Enable(True)
        self.login.Hide()
        self.loginbox.Hide()
        self.password.Hide()
        self.passbox.Hide()
        self.register.Hide()
        self.WaitButton.Hide()
        self.MCheckBox.SetValue(False)
        self.PCheckBox.SetValue(False)
        self.animation.Hide()
        self.Timer_animate = False
        self.debugImage.Hide()
        self.debugZone.Hide()
        self.Refresh()

        
    def getResult(self):
        if(self.Result == None):
            return False
        else:
            return self.Result
            
    def TimerAction(self, event):
        ## If the setup window is downloading a file, it is a good occasion to update the progresbar
        if(self.Timer_downloading == True):
            if(self.downloader.taille_bloc != 0):
                downloaded = self.downloader.nb_blocs * self.downloader.taille_bloc
                octetsLoadedB = downloaded / 1048576.0
                octetsLoadedN = str(round(octetsLoadedB, 1))

                # may be -1 on older FTP servers which do not return a file size in response to a retrieval request
                if self.downloader.taille_fichier >= 0:
                    self.gauge.SetRange(self.downloader.taille_fichier)
                
                    try:
                        self.gauge.SetValue(downloaded)
                    except wx._core.PyAssertionError:
                        pass
                    
                    tailleFichierB = self.downloader.taille_fichier / 1048576.0
                    tailleFichierN = str(round(tailleFichierB, 1))
                else:
                    tailleFichierN = "?"

                estimation_txt = octetsLoadedN + " "+_("of")+" " + tailleFichierN + " "+_("MB downloaded")
                self.txtEstimation.SetLabel(estimation_txt)

            if(self.downloader.finished == True):
                if(self.downloader.failed == True):
                    self.release_but_fail(self)
                else:
                    self.release(self)
                self.Timer_downloading = False

        if(self.Timer_animate == True):
            self.current_angle = ((self.current_angle + 1) % 12)
            self.animation.SetBitmap(self.GetLoaderFromAngle(self.current_angle + 1))
            
    ### Theses methods command the window. There are called directly by the server
    def POL_SetupWindow_message(self, message, title):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.DrawCancel()
        self.DrawNext()
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release)

    def POL_SetupWindow_free_presentation(self, message, titre):
        self.Destroy_all()
        self.MainPanel.Show()
        self.titreP.SetLabel(titre.decode("utf8","replace"))
        self.titreP.Wrap(280)

        self.texteP.SetLabel(message.decode("utf8","replace").replace("\\n","\n").replace("\\t","\t"))
        self.texteP.Wrap(360)
        self.texteP.Show()

        self.DrawCancel()
        self.DrawNext()

        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release)
        self.DrawImage()
    
    def POL_SetupWindow_SetID(self, script_id):
        self.InfoScript.Show()
        self.script_ID = script_id

    def POL_SetupWindow_UnsetID(self):
        self.InfoScript.Hide()

    def InfoClick(self, e):
        url = "http://www.playonlinux.com/en/app-"+self.script_ID+".html"
        if(os.environ["POL_OS"] == "Mac"):
            os.system("open "+url+" &")
        else:
            os.system("xdg-open "+url+" &")


    def POL_SetupWindow_textbox(self, message, title, value, maxlength=0):
        try:
            maxlength = int(maxlength)
        except ValueError:
            maxlength = 0

        self.Destroy_all()
        self.DrawDefault(message, title)

        self.space = message.count("\\n")+1

        self.champ.SetPosition((20,85+self.space*16))
        self.champ.SetMaxLength(maxlength if maxlength > 0 else 0)
        self.champ.SetValue(value)
        self.champ.Show()

        self.DrawCancel()
        self.DrawNext()
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_champ)
        wx.EVT_TEXT_ENTER(self, 400, self.release_champ)

    def POL_Debug(self, message, title, value):
        self.POL_SetupWindow_message(message, title)
        self.debugImage.Show()
        self.debugZone.Show()
        self.debugZone.SetValue(value.replace("\\n","\n"))

    def POL_SetupWindow_Pulse(self, value):
        self.gauge.SetValue(int(value)/2)
        self.SendBash()

    def POL_SetupWindow_PulseText(self, value):
        self.texte_bis.SetLabel(value.replace("\\n","\n"))
        self.texte_bis.SetPosition((20,135+self.space*16))
        self.texte_bis.Show()
        self.SendBash()

    def POL_SetupWindow_download(self, message, title, url, localfile): 
        self.Destroy_all()
        self.DrawDefault(message, title)
        self.space = message.count("\\n")+1
        self.gauge.Show()
        self.gauge.SetPosition((70,95+self.space*16))
        self.txtEstimation.SetPosition((20,135+self.space*16))
        self.txtEstimation.Show()
        self.DrawCancel()
        self.DrawNext()
        self.NextButton.Enable(False)
        self.DownloadFile(url, localfile)

    def POL_SetupWindow_wait(self, message, title):
        self.Destroy_all()
        self.DrawDefault(message, title)
        self.NextButton.Enable(False)
        self.animation.Show()
        self.Timer_animate = True
        self.DrawCancel()
        self.DrawNext()
        self.NextButton.Enable(False)
        self.SendBash()

    def POL_SetupWindow_pulsebar(self, message, title):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.NextButton.Enable(False)
        
        self.space = message.count("\\n")+1
        self.gauge.SetPosition((70,95+self.space*16))
        self.gauge.Show()
        
        self.DrawCancel()
        self.DrawNext()
        self.NextButton.Enable(False)
        self.SendBash()
        
    def POL_SetupWindow_wait_b(self, message, title, button_value, command, alert):
        self.POL_SetupWindow_wait(message, title)    
        self.WaitButton.Show()
        self.WaitButton.SetLabel(button_value) 
        self.space = message.count("\\n")+1
        self.WaitButton.SetPosition((135,115+self.space*16))
        self.Bind(wx.EVT_BUTTON, lambda event:
            self.RunCommand(event,command,alert),self.WaitButton)

    def POL_SetupWindow_question(self, message, title):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.YesButton.Show()
        self.NoButton.Show()

    def POL_SetupWindow_menu(self, message, title, liste, cut, numtype=False):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.space = message.count("\\n")+1
        self.areaList = string.split(liste,cut)

        self.Menu.SetPosition((20,85+self.space*16))

        self.Menu.Clear()
        self.Menu.InsertItems(self.areaList,0)
        self.Menu.Select(0)
        self.Menu.Show()

        self.DrawCancel()
        self.DrawNext()

        if(numtype == False):
            wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_menu)
            wx.EVT_LISTBOX_DCLICK(self, 104, self.release_menu)
        else:
            wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_menu_num)
            wx.EVT_LISTBOX_DCLICK(self, 104, self.release_menu_num)

    def POL_SetupWindow_browse(self, message, title, value, directory, supportedfiles):
        self.POL_SetupWindow_textbox(message, title, value)
        self.supportedfiles = supportedfiles
        self.champ.Hide()
        self.directory = directory
        self.browse.SetPosition((195,130))
        self.browse.Show()
        self.NextButton.Enable(False)


    def POL_SetupWindow_login(self, message, title, register_url):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.space = message.count("\\n")+1
        self.register_link = register_url

        self.login.Show()
        self.loginbox.Show()
        self.password.Show()
        self.passbox.Show()
        self.register.Show()

        self.DrawCancel()
        self.DrawNext()

        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_login)

    def POL_SetupWindow_textbox_multiline(self, message, title, value):
        self.Destroy_all()
        self.DrawDefault(message, title)
        self.space = message.count("\\n")+1

        self.bigchamp.SetPosition((20,85+self.space*16))
        self.bigchamp.SetValue(value)

        self.bigchamp.Show()

        self.DrawCancel()
        self.DrawNext()
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_bigchamp)

    def POL_SetupWindow_checkbox_list(self, message, title, liste, cut):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.scrolled_panel.Show()
        self.space = message.count("\\n")+1

        self.scrolled_panel.SetPosition((20,85+self.space*16))
        self.areaList = string.split(liste,cut)

        # We have to destroy all previous items (catching exception in case one is already destroyed)
        self.i = 0
        try:
            while(self.i <= len(self.item_check)):
                self.item_check[self.i].Destroy()
                self.i+=1
        except:
            pass
        self.item_check = []

        # Now we can rebuild safely the widget
        self.i = 0
        while(self.i < len(self.areaList)):
            self.item_check.append(wx.CheckBox(self.scrolled_panel, -1, pos=(0,(self.i*25)),label=str(self.areaList[self.i])))
            self.i+=1

        self.scrolled_panel.SetVirtualSize((0,self.i*(25)))
        self.scrolled_panel.SetScrollRate(0,25)
        self.DrawCancel()
        self.DrawNext()
        self.separator = cut
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_checkboxes)


    def POL_SetupWindow_shortcut_list(self, message, title):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.add_games()

        self.space = message.count("\\n")+1
        self.MenuGames.SetPosition((20,85+self.space*16))
        self.MenuGames.Show()

        self.DrawCancel()
        self.DrawNext()
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_menugame)
        wx.EVT_TREE_ITEM_ACTIVATED(self, 111, self.release_menugame)

    def POL_SetupWindow_icon_menu(self, message, title, items, cut, icon_folder, icon_list):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.add_menu_icons(items, cut, icon_list, icon_folder);

        self.space = message.count("\\n")+1
        self.MenuGames.SetPosition((20,85+self.space*16))
        self.MenuGames.Show()

        self.DrawCancel()
        self.DrawNext()
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_menugame)
        wx.EVT_TREE_ITEM_ACTIVATED(self, 111, self.release_menugame)

    def POL_SetupWindow_prefix_selector(self, message, title):
        self.Destroy_all()
        self.DrawDefault(message, title)

        self.add_games()
        self.MenuGames.Show()

        self.space = message.count("\\n")+1
        self.Menu.SetPosition((20,85+self.space*16))
        self.Menu.Clear()

        self.areaList = os.listdir(Variables.playonlinux_rep+"/wineprefix/")
        self.areaList.sort()

        for file in self.areaList:
            if (str(file[0]) == "."):
                self.areaList.remove(file)

        self.Menu.InsertItems(self.areaList,0)
        self.Menu.Select(0)
        self.Menu.Hide()

        self.DrawCancel()
        self.DrawNext()

        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release_menuprefixes)
        wx.EVT_TREE_ITEM_ACTIVATED(self, 111, self.release_menuprefixes)
        wx.EVT_LISTBOX_DCLICK(self, 104, self.release_menuprefixes)

        self.PCheckBox.Show()


    def POL_SetupWindow_licence(self, message, title, licence_file):
        self.Destroy_all()
        self.DrawDefault(message, title)

        try:
            self.texte_panel.SetLabel(open(licence_file,"r").read())
        except:
            self.texte_panel.SetLabel("E. file not found :"+licence_file)

        self.texte_panel.Wrap(400)
        self.texte_panel.Show()

        self.scrolled_panel.Show()
        self.scrolled_panel.SetVirtualSize(self.texte_panel.GetSize())
        self.scrolled_panel.SetScrollRate(0,25)

        self.MCheckBox.Show()

        self.DrawCancel()
        self.DrawNext()
        self.NextButton.Enable(False)
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release)


    def POL_SetupWindow_file(self, message, title, filetoread):
        self.Destroy_all()
        self.DrawDefault(message, title)

        try:
            self.texte_panel.SetLabel(open(filetoread,"r").read())
        except:
            self.texte_panel.SetLabel("E. File not found")
            
        self.texte_panel.Wrap(400)
        self.texte_panel.Show()

        self.scrolled_panel.Show()
        self.scrolled_panel.SetVirtualSize(self.texte_panel.GetSize())
        self.scrolled_panel.SetScrollRate(0,25)

        self.DrawCancel()
        self.DrawNext()
        wx.EVT_BUTTON(self, wx.ID_FORWARD, self.release)




    def POL_register(self, event):
        if(os.environ["POL_OS"] == "Mac"):
            os.system("open "+self.register_link)
        else:
            os.system("xdg-open "+self.register_link)

    def RunCommand(self, event, command,confirm):
        if(confirm == "0" or wx.YES == wx.MessageBox(confirm.decode("utf-8","replace"), os.environ["APPLICATION_TITLE"], style=wx.YES_NO | wx.ICON_QUESTION)):
            os.system(command+"&");

    def DrawImage(self):
        self.left_image.Show()

    def DrawHeader(self):
        self.header.Show()


    def DrawDefault(self, message, title):
        self.DrawHeader()
        self.texte.SetLabel(message.replace("\\n","\n").replace("\\t","\t"))
        self.texte.Show()
        self.titre.SetLabel(title)
        self.titre.Show()

    def DrawCancel(self):
        self.CancelButton.Show()

    def DrawNext(self):
        self.NextButton.Show()

    def SendBash(self, var=""):
        self.Result = var

    def SendBashT(self, var):
        self.Result = var

    def release(self, event):
        self.SendBash()
        self.NextButton.Enable(False)

    def release_but_fail(self, event):
        self.SendBash("Fail")
        self.NextButton.Enable(False)

    def release_checkboxes(self, event):
        i = 0
        send = []
        while(i < len(self.item_check)):
            if(self.item_check[i].IsChecked() == True):
                send.append(self.areaList[i])
            i += 1
        self.SendBash(string.join(send,self.separator))
        self.NextButton.Enable(False)

    def release_yes(self, event):
        self.SendBash("TRUE")
        self.NextButton.Enable(False)

    def release_no(self, event):
        self.SendBash("FALSE")
        self.NextButton.Enable(False)

    def release_login(self, event):
        self.SendBash(self.loginbox.GetValue().encode("utf-8","replace")+"~"+self.passbox.GetValue().encode("utf-8","replace"))
        self.NextButton.Enable(False)

    def release_champ(self, event):
        self.SendBash(self.champ.GetValue().encode("utf-8","replace"))
        self.NextButton.Enable(False)

    def release_bigchamp(self, event):
        self.SendBashT(self.bigchamp.GetValue().replace("\n","\\n").encode("utf-8","replace"))
        self.NextButton.Enable(False)

    def release_menu(self,event):
        self.SendBash(self.areaList[self.Menu.GetSelection()])
        self.NextButton.Enable(False)

    def release_menu_num(self,event):
        self.SendBash(str(self.Menu.GetSelection()))
        self.NextButton.Enable(False)

    def release_icons(self,event):
        if(self.menu.IsChecked()):
            self.SendBash("MSG_MENU=True")
        if(self.desktop.IsChecked()):
            self.SendBash("MSG_DESKTOP=True")
        if(self.desktop.IsChecked() and self.menu.IsChecked()):
            self.SendBash("MSG_DESKTOP=True\nMSG_MENU=True")
        if(self.desktop.IsChecked() == False and self.menu.IsChecked() == False):
            self.SendBash("Ok")
        self.NextButton.Enable(False)

    def release_menugame(self,event):     
        self.SendBash(self.MenuGames.GetItemText(self.MenuGames.GetSelection()).encode("utf-8","replace"))
        self.NextButton.Enable(False)

    def release_menuprefixes(self,event):
        if(self.PCheckBox.IsChecked() == False): # Alors il faut renvoyer le prefix
            self.SendBash("1~"+self.MenuGames.GetItemText(self.MenuGames.GetSelection()).encode("utf-8","replace"))
        else:
            self.SendBash("2~"+self.areaList[self.Menu.GetSelection()])

        self.NextButton.Enable(False)

    def Cancel(self, event):
        if(self.ProtectedWindow == False):
            self.Destroy()
            time.sleep(0.1)
            os.system("kill -9 -"+self.bash_pid+" 2> /dev/null")
            os.system("kill -9 "+self.bash_pid+" 2> /dev/null") 
        else:
            wx.MessageBox(_("You cannot close this window").format(os.environ["APPLICATION_TITLE"]),_("Error"))

    def add_games(self):
        apps = os.listdir(Variables.playonlinux_rep+"/shortcuts/")
        apps.sort()
        self.images.RemoveAll()
        self.MenuGames.DeleteAllItems()
        self.root = self.MenuGames.AddRoot("")
        i = 0
        for app in apps:
            appfile = Variables.playonlinux_rep+"/shortcuts/"+app
            if(not os.path.isdir(appfile)):
                fichier = open(appfile,"r").read()

                if("POL_Wine " in fichier):
                    if(os.path.exists(Variables.playonlinux_rep+"/icones/32/"+app)):
                        file_icon = Variables.playonlinux_rep+"/icones/32/"+app
                    else:
                        file_icon = Variables.playonlinux_env+"/etc/playonlinux32.png"

                    bitmap = wx.Image(file_icon)
                    bitmap.Rescale(22,22,wx.IMAGE_QUALITY_HIGH)
                    bitmap = bitmap.ConvertToBitmap()
                    self.images.Add(bitmap)
                    self.MenuGames.AppendItem(self.root, app, i)
                    i += 1


    def add_menu_icons(self, items, cut, icon_list, icon_folder):
        elements = items.split(cut)
        icons = icon_list.split(cut)
        
        #self.games.sort()
        self.images.RemoveAll()
        self.MenuGames.DeleteAllItems()
        self.root = self.MenuGames.AddRoot("")
        i = 0
        for index in elements:
            current_icon = icon_folder+"/"+icons[i]
            if(os.path.exists(current_icon)):
                file_icon = current_icon
            else:
                file_icon = Variables.playonlinux_env+"/etc/playonlinux32.png"

            bitmap = wx.Image(file_icon)
            bitmap.Rescale(22,22,wx.IMAGE_QUALITY_HIGH)
            bitmap = bitmap.ConvertToBitmap()
            self.images.Add(bitmap)
            self.MenuGames.AppendItem(self.root, index, i)
            i+=1


    def DemanderPourcent(self, event):
        self.NextButton.Enable(False)
        if self.p.poll() == None:
            self.gauge.Pulse()
        else:
            self.SendBash("Ok")


    def Parcourir(self, event):
        if(self.supportedfiles == "All"):
            self.FileDialog = wx.FileDialog(self.panel)
        else:
            self.FileDialog = wx.FileDialog(self.panel, wildcard=self.supportedfiles)
        self.FileDialog.SetDirectory(self.directory)
        self.FileDialog.ShowModal()
        if(self.FileDialog.GetPath() != ""):
            filePath = self.FileDialog.GetPath().encode("utf-8","replace")
            filePathBaseName = filePath.split("/")[filePath.count("/")]
            self.champ.SetValue(filePath) 
            self.NextButton.Enable(True)
            self.browse_text.Show()
            self.browse_text.SetLabel(filePathBaseName)
            self.browse_text.SetPosition(((520-self.browse_text.GetSize()[0])/2,180))
            
            if(".exe" in filePathBaseName and os.path.getsize(filePath) <= 30*1024*1024):
                try:
                    tmpPath = os.environ['POL_USER_ROOT']+"/tmp/browse"+self.bash_pid+".png"
                    try: os.path.remove(tmpPath)
                    except: pass
                    playonlinux.POL_System("POL_ExtractBiggestIcon \""+filePath+"\" "+tmpPath)
                    if(os.path.exists(tmpPath)):
                        browse_image = wx.Image(tmpPath)
                    else:
                        browse_image = wx.Image(os.environ['PLAYONLINUX']+"/etc/playonlinux.png")
                except:
                    browse_image = wx.Image(os.environ['PLAYONLINUX']+"/etc/playonlinux.png")
            else:
                browse_image = wx.Image(os.environ['PLAYONLINUX']+"/etc/playonlinux.png")
            
            if(browse_image.GetWidth() >= 48):
                browse_image.Rescale(48,48,wx.IMAGE_QUALITY_HIGH)
            browse_image = browse_image.ConvertToBitmap()
    
            self.browse_image.SetBitmap(browse_image)
            self.browse_image.SetPosition(((520-self.browse_image.GetSize()[0])/2,220))
            self.browse_image.Show()

        self.FileDialog.Destroy()


    def DownloadFile(self, url, localB):    #url = url a récupérer, localB le fichier où enregistrer la modification
        if os.path.isdir(localB):
            # localB is a directory, append the filename to use
            # * in a perfect world this should be removed and the
            # client be always responsible for providing the filename
            # it wants/expects
            self.chemin = urlparse.urlsplit(url)[2]
            self.nomFichier = self.chemin.split('/')[-1]
            self.local = localB + self.nomFichier
        else:
            self.local = localB
        self.downloader = Download(url, self.local)
        self.Timer_downloading = True


    def agree(self, event):
        if(self.MCheckBox.IsChecked()):
            self.NextButton.Enable(True)
        else:
            self.NextButton.Enable(False)

    def switch_menu(self, event):
        if(self.PCheckBox.IsChecked()):
            self.Menu.Show()
            self.MenuGames.Hide()
        else:
            self.MenuGames.Show()
            self.Menu.Hide()
        self.Refresh()


########NEW FILE########
__FILENAME__ = gui_server
#!/usr/bin/python
# -*- coding:Utf-8 -*-

# Copyright (C) 2008 Pâris Quentin
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import socket, threading, thread, guiv3 as gui, os, wx, time, random
import string


class gui_server(threading.Thread):
    def __init__(self, parent): 
        threading.Thread.__init__(self)
        self._host = '127.0.0.1'
        self._port = 30000
        self._running = True
        # This dictionnary will contain every created setup window
        self.parent = parent

    def GenCookie(self, length=20, chars=string.letters + string.digits):
        return ''.join([random.SystemRandom().choice(chars) for i in range(length)])

    def handler(self, connection, addr):
        self.temp = "";
        while True:
            self.tempc = connection.recv(2048);
           
            self.temp += self.tempc
            if "\n" in self.tempc:
                break;

        self.result = self.interact(self.temp.replace("\n",""))
        connection.send(self.result)
        try: 
           connection.shutdown(1)
           connection.close()
        except:
           pass
           
    def initServer(self):
        if(self._port  >= 30020):
           print _("Error: Unable to reserve a valid port")
           wx.MessageBox(_("Error: Unable to reserve a valid port"),os.environ["APPLICATION_TITLE"])
           os._exit(0)
           
        try:
           self.acceptor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
           self.acceptor.bind ( ( str(self._host), int(self._port) ) )
           self.acceptor.listen(10)
           os.environ["POL_PORT"] = str(self._port)
           os.environ["POL_COOKIE"] = self.GenCookie()
        except socket.error, msg:       
           self._port += 1
           self.initServer()
        

    def closeServer(self):
        self.acceptor.close()
        self._running = False

    def waitRelease(self, pid):
        result = False
        while(result == False):
            #try:
            if pid in self.parent.windowList:
                try:
                    result = self.parent.windowList[pid].getResult()
                except:
                    break
            else:
                break
            #except: # Object is destroyed
            #    time.sleep(0.1)
            time.sleep(0.1) 
        
        return result

    def interact(self, recvData):
       self.parent.SetupWindowTimer_SendToGui(recvData)
       time.sleep(0.1 + self.parent.SetupWindowTimer_delay/100.) # We divide by 100, because parent.SWT_delay is in ms, and we want a 10x faster
       sentData = recvData.split("\t")
       if(len(sentData) > 2):
           gotData = self.waitRelease(sentData[2])
       else:
           gotData = ""

       return(str(gotData))



    def run(self):
        self.initServer()
        self.i = 0

        while self._running:
            try:
                self.connection, self.addr = self.acceptor.accept()
            except socket.error as (errno, msg):
                if errno == 4: # Interrupted system call
                    continue

            thread.start_new_thread(self.handler, (self.connection,self.addr))
            self.i += 1
            #channel.close()
           



def readAction(object):
    if(object.SetupWindowTimer_action[0] != os.environ["POL_COOKIE"]):
            print "Bad cookie!"
            object.SetupWindowTimer_action = None
            return False

    object.SetupWindowTimer_action = object.SetupWindowTimer_action[1:]

    if(object.SetupWindowTimer_action[0] == "SimpleMessage"):
        if(len(object.SetupWindowTimer_action) == 2):
            wx.MessageBox(object.SetupWindowTimer_action[1],os.environ["APPLICATION_TITLE"])
            object.SetupWindowTimer_action = None
            return False 

    if(object.SetupWindowTimer_action[0] == "POL_Die"):
        if(len(object.SetupWindowTimer_action) == 1):
            object.POLDie()            
            object.SetupWindowTimer_action = None
            return False  

    if(object.SetupWindowTimer_action[0] == "POL_Restart"):
        if(len(object.SetupWindowTimer_action) == 1):
            object.POLRestart()            
            object.SetupWindowTimer_action = None
            return False  

    if(object.SetupWindowTimer_action[0] == 'POL_System_RegisterPID'):
        if(len(object.SetupWindowTimer_action) == 2):
            object.registeredPid.append(int(object.SetupWindowTimer_action[1]))
            object.SetupWindowTimer_action = None
            return False

    if(len(object.SetupWindowTimer_action) <= 1):
        object.SetupWindowTimer_action = None
        return False

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_Init'):
        if(len(object.SetupWindowTimer_action) == 5):
            object.windowList[object.SetupWindowTimer_action[1]] = gui.POL_SetupFrame(os.environ["APPLICATION_TITLE"],object.SetupWindowTimer_action[1],object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4])
            object.windowList[object.SetupWindowTimer_action[1]].Center(wx.BOTH)
            object.windowList[object.SetupWindowTimer_action[1]].Show(True)
            object.windowOpened += 1
    else:
        if(object.SetupWindowTimer_action[1] not in object.windowList):
            print(_("WARNING. Please use POL_SetupWindow_Init first"))
            object.SetupWindowTimer_action = None
            return False 
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_message'):
         if(len(object.SetupWindowTimer_action) == 4):
             object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_message(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_SetID'):
         if(len(object.SetupWindowTimer_action) == 3):
             object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_SetID(object.SetupWindowTimer_action[2])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_UnsetID'):
         if(len(object.SetupWindowTimer_action) == 2):
             object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_UnsetID()

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_shortcut_list'):
         if(len(object.SetupWindowTimer_action) == 4):
             object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_shortcut_list(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3])
             
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_prefix_selector'):
         if(len(object.SetupWindowTimer_action) == 4):
             object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_prefix_selector(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_pulsebar'):
         if(len(object.SetupWindowTimer_action) == 4):
             object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_pulsebar(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_question'):
        if(len(object.SetupWindowTimer_action) == 4):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_question(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_wait'):
        if(len(object.SetupWindowTimer_action) == 4):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_wait(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_wait_bis'):
        if(len(object.SetupWindowTimer_action) == 7):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_wait_b(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5],object.SetupWindowTimer_action[6])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_free_presentation'):
        if(len(object.SetupWindowTimer_action) == 4):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_free_presentation(object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[2])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_textbox'):
        if(len(object.SetupWindowTimer_action) == 6):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_textbox(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5])

    if(object.SetupWindowTimer_action[0] == 'POL_Debug'):
        if(len(object.SetupWindowTimer_action) == 5):
            object.windowList[object.SetupWindowTimer_action[1]].POL_Debug(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_textbox_multiline'):
        if(len(object.SetupWindowTimer_action) == 5):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_textbox_multiline(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4])


    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_browse'):
        if(len(object.SetupWindowTimer_action) == 7):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_browse(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5],object.SetupWindowTimer_action[6])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_download'):
        if(len(object.SetupWindowTimer_action) == 6):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_download(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5])

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_Close'):
        if(len(object.SetupWindowTimer_action) == 2):
            object.windowList[object.SetupWindowTimer_action[1]].Destroy()
            del object.windowList[object.SetupWindowTimer_action[1]]
            object.windowOpened -= 1

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_menu'):
        if(len(object.SetupWindowTimer_action) == 6):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_menu(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5], False)

    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_menu_num'):
        if(len(object.SetupWindowTimer_action) == 6):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_menu(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5], True)
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_checkbox_list'):
        if(len(object.SetupWindowTimer_action) == 6):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_checkbox_list(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5])
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_icon_menu'):
        if(len(object.SetupWindowTimer_action) == 8):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_icon_menu(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4],object.SetupWindowTimer_action[5], object.SetupWindowTimer_action[6], object.SetupWindowTimer_action[7])
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_licence'):
        if(len(object.SetupWindowTimer_action) == 5):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_licence(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4])
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_login'):
        if(len(object.SetupWindowTimer_action) == 5):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_login(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4])
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_file'):
        if(len(object.SetupWindowTimer_action) == 5):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_file(object.SetupWindowTimer_action[2],object.SetupWindowTimer_action[3],object.SetupWindowTimer_action[4])
            
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_pulse'):
        if(len(object.SetupWindowTimer_action) == 3):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_Pulse(object.SetupWindowTimer_action[2])
    
    if(object.SetupWindowTimer_action[0] == 'POL_SetupWindow_set_text'):
        if(len(object.SetupWindowTimer_action) == 3):
            object.windowList[object.SetupWindowTimer_action[1]].POL_SetupWindow_PulseText(object.SetupWindowTimer_action[2])
    
    object.SetupWindowTimer_action = None

########NEW FILE########
__FILENAME__ = install
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2008 Pâris Quentin

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import wx
import os, sys, codecs, string, socket, urllib, urllib2
import wx.html, threading, time, wx.animate

import lib.Variables as Variables, sp
import lib.lng
import lib.playonlinux as playonlinux
from wx.lib.ClickableHtmlWindow import PyClickableHtmlWindow

class Wminiature(wx.Frame):
    def __init__(self,parent,id,title,img):
        wx.Frame.__init__(self, parent, -1, title, size = (800, 600+Variables.windows_add_size))
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.img = wx.StaticBitmap(self, -1, wx.Bitmap(img))

class getDescription(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.getDescription = ""
        self.getDescription_bis = ""
        self.htmlContent = ""
        self.htmlwait = "###WAIT###"
        self.stars = 0
        self.cat = 0
        self.start()
        self.med_miniature = None
        self.miniature = Variables.playonlinux_env+"/resources/images/pol_min.png"
        self.miniature_defaut = Variables.playonlinux_env+"/resources/images/pol_min.png"

    def download(self, game):
        self.getDescription = game


    def run(self):
        self.thread_running = True
        while(self.thread_running):
            if(self.getDescription == ""):
                time.sleep(0.1)
            else:
                self.htmlContent = self.htmlwait;
                time.sleep(0.5)
                self.getDescription_bis = self.getDescription
                self.med_miniature = None
                if(self.getDescription == "about:creator"):
                    self.miniature = self.miniature_defaut
                    self.htmlContent = "Well done !"
                    self.stars = "5"
                else:

                    self.cut = string.split(self.getDescription,":")
                    if(self.cut[0] == "get"):
                        self.miniature = self.miniature_defaut
                        # Description
                        self.htmlContent = "<font color=red><b>WARNING !</b><br />You are going to execute a non-validated script. <br />This functionality has been added to make script testing easier.<br />It can be dangerous for your computer. <br />PlayOnLinux will NOT be reponsible for any damages.</font>"
                        self.stars = "0"
                    else:
                        # Miniatures
                        try :
                            url = os.environ["SITE"]+'/V4_data/repository/screenshot.php?id='+self.getDescription.replace(" ","%20")
                            req = urllib2.Request(url)
                            handle = urllib2.urlopen(req)
                            screenshot_id=handle.read()

                            if(screenshot_id != "0"):
                                url_s1 = 'http://www.playonlinux.com/images/apps/min/'+screenshot_id
                                req = urllib2.Request(url_s1)
                                handle = urllib2.urlopen(req)

                                open(Variables.playonlinux_rep+"/tmp/min"+screenshot_id,"w").write(handle.read())
                                self.miniature = Variables.playonlinux_rep+"/tmp/min"+screenshot_id

                            else:
                                try:
                                    url = os.environ["SITE"]+'/V2_data/miniatures/'+self.getDescription.replace(" ","%20")
                                    req = urllib2.Request(url)
                                    handle = urllib2.urlopen(req)

                                    open(Variables.playonlinux_rep+"/tmp/min","w").write(handle.read())
                                    self.miniature = Variables.playonlinux_rep+"/tmp/min"
                                except:
                                    self.miniature = self.miniature_defaut

                        except :
                            self.miniature = self.miniature_defaut
                            self.med_miniature = None


                        # Description
                        try :
                            url = os.environ["SITE"]+'/V4_data/repository/get_description.php?id='+self.getDescription.replace(" ","%20")
                            req = urllib2.Request(url)
                            handle = urllib2.urlopen(req)
                            self.htmlContent = handle.read()
                            if("<i>No description</i>" in self.htmlContent):
                                self.htmlContent = "<i>"+_("No description")+"</i>"
                        except :
                            self.htmlContent = "<i>"+_("No description")+"</i>"

                        if(self.cat == 12):
                            self.htmlContent += "<br /><br /><font color=red><b>WARNING !</b><br />You are going to execute a beta script. <br />This functionality has been added to make script testing easier.<br />It might not work as expected.</font>"

                        try:
                            if(screenshot_id != 0):
                                try:
                                    url_s2 = 'http://www.playonlinux.com/images/apps/med/'+screenshot_id
                                    req = urllib2.Request(url_s2)
                                    handle = urllib2.urlopen(req)
                                    open(Variables.playonlinux_rep+"/tmp/med"+screenshot_id,"w").write(handle.read())
    
                                    self.med_miniature = Variables.playonlinux_rep+"/tmp/med"+screenshot_id
                                except:
                                    self.med_miniature = None
                            else:
                               self.med_miniature = None
                        except:
                            self.med_miniature = None

                        # Stars
                        try :
                            url = os.environ["SITE"]+'/V4_data/repository/stars.php?n='+self.getDescription.replace(" ","%20")
                            req = urllib2.Request(url)
                            handle = urllib2.urlopen(req)
                            self.stars = handle.read()
                        except :
                            self.stars = "0"


                if(self.getDescription == self.getDescription_bis):
                    self.getDescription = ""


class InstallWindow(wx.Frame):
    def addCat(self, name, icon, iid):
        espace=80;
        if(os.environ["POL_OS"] == "Mac"):
            offset = 10
            w_offset = 5
        else:
            offset = 2
            w_offset = 10


        self.cats_icons[name] = wx.BitmapButton(self.panelButton, 2000+iid, wx.Bitmap(icon), (0,0), style=wx.NO_BORDER)

        self.cats_links[name] = wx.HyperlinkCtrl(self.panelButton, 3000+iid, name, "", pos=(0,52))
        mataille = self.cats_links[name].GetSize()[0]
        mataille2 = self.cats_icons[name].GetSize()[0]
        image_pos = (espace-mataille2)/2+espace*iid;

        self.cats_links[name].SetPosition((espace*iid+espace/2-mataille/2,47))
        self.cats_icons[name].SetPosition((image_pos,offset))

        #self.cats_icons[name].SetSize((espace,100))

        wx.EVT_HYPERLINK(self, 3000+iid, self.AddApps)
        wx.EVT_BUTTON(self, 2000+iid, self.AddApps)

        #self.cats_icons[name].Bind(wx.EVT_LEFT_DOWN, 2000+iid, self.AddApps)
        self.cats_links[name].SetNormalColour(wx.Colour(0,0,0))
        self.cats_links[name].SetVisitedColour(wx.Colour(0,0,0))
        self.cats_links[name].SetHoverColour(wx.Colour(0,0,0))
        self.cats_links[name].SetBackgroundColour((255,255,255))

        self.cats_links[name].SetFont(self.fontText)

    def __init__(self,parent,id,title):
        wx.Frame.__init__(self, parent, -1, title, size = (800, 550+Variables.windows_add_size), style = wx.CLOSE_BOX | wx.CAPTION | wx.MINIMIZE_BOX)
        self.cats_icons = {}
        self.cats_links = {}

        self.description = getDescription()
        self.panelFenp = wx.Panel(self, -1)
        self.panelItems = wx.Panel(self.panelFenp, -1, size=(800,550+Variables.windows_add_size), pos=(0,71))
        self.panelWait = wx.Panel(self.panelFenp, -1, size=(800,550+Variables.windows_add_size), pos=(0,71))
        self.panelWait.Hide()
        self.panelManual = wx.Panel(self.panelFenp, -1, size=(800,550+Variables.windows_add_size), pos=(0,71))
        self.panelManual.Hide()
        self.currentPanel = 0 # [ 1 = manual, 0 = items ]

        # Categories
        self.panelButton = wx.Panel(self.panelFenp, -1, size=(802,69), pos=(-1,-1),style=Variables.widget_borders)
        self.panelButton.SetBackgroundColour((255,255,255))

        if(os.environ["POL_OS"] == "Mac"):
            self.fontText = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)
            self.fontTitre = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
        else :
            self.fontText = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)
            self.fontTitre = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)

        self.addCat(_("Accessories"),Variables.playonlinux_env+"/resources/images/install/32/applications-accessories.png",0)
        self.addCat(_("Development"),Variables.playonlinux_env+"/resources/images/install/32/applications-development.png",1)
        self.addCat(_("Education"),Variables.playonlinux_env+"/resources/images/install/32/applications-science.png",2)
        self.addCat(_("Games"),Variables.playonlinux_env+"/resources/images/install/32/applications-games.png",3)
        self.addCat(_("Graphics"),Variables.playonlinux_env+"/resources/images/install/32/applications-graphics.png",4)
        self.addCat(_("Internet"),Variables.playonlinux_env+"/resources/images/install/32/applications-internet.png",5)
        self.addCat(_("Multimedia"),Variables.playonlinux_env+"/resources/images/install/32/applications-multimedia.png",6)
        self.addCat(_("Office"),Variables.playonlinux_env+"/resources/images/install/32/applications-office.png",7)
        self.addCat(_("Other"),Variables.playonlinux_env+"/resources/images/install/32/applications-other.png",8)
        self.addCat(_("Patches"),Variables.playonlinux_env+"/resources/images/install/32/view-refresh.png",9)


        self.live = 0
        self.openMin = False
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.images_cat = wx.ImageList(22, 22)
        self.imagesapps = wx.ImageList(22, 22)
        #self.list_cat = wx.TreeCtrl(self.panelItems, 105, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|Variables.widget_borders, size=(200, 363), pos=(10,10))
        #self.list_cat.Hide()

        if(os.environ["POL_OS"] == "Mac"):
            self.image_position = (738-160,346-71)
            self.new_size = (196,218-4)
            self.search_offset = 3
        if(os.environ["POL_OS"] == "Linux"):
            self.image_position = (740-160,348-71)
            self.new_size = (200,222-4)
            self.search_offset = 5



        self.image = wx.StaticBitmap(self.panelItems, 108, wx.Bitmap(Variables.playonlinux_env+"/resources/images/pol_min.png"), self.image_position, wx.DefaultSize)
        self.image.Bind(wx.EVT_LEFT_DOWN, self.sizeUpScreen)
        #self.list_cat.SetSpacing(0);
        #self.list_cat.SetImageList(self.images_cat)
        position = 10+self.search_offset;
        #self.searchcaption = wx.StaticText(self.panelItems, -1, _("Search"), (position,82-71+self.search_offset), wx.DefaultSize)
        #position += self.searchcaption.GetSize()[0]+5
        self.searchbox = wx.SearchCtrl(self.panelItems, 110, size=(250,22), pos=(position,9))
        self.searchbox.SetDescriptiveText(_("Search"))
        position += self.searchbox.GetSize()[0]+20

        self.filterscaption = wx.StaticText(self.panelItems, -1, _("Include:"), (position,82-71+self.search_offset), wx.DefaultSize)
        position += self.filterscaption.GetSize()[0]+10

        self.testingChk = wx.CheckBox(self.panelItems, 401, pos=(position,82-71), size=wx.DefaultSize)
        self.testingChk.SetValue(True)
        position += 15+self.search_offset
        self.testingCapt = wx.StaticText(self.panelItems, -1, _("Testing"), (position,82-71+self.search_offset), wx.DefaultSize)
        position += self.testingCapt.GetSize()[0]+10

        self.nocdChk = wx.CheckBox(self.panelItems, 402, pos=(position,82-71), size=wx.DefaultSize)
        position += 15+self.search_offset
        self.noDvDCapt = wx.StaticText(self.panelItems, -1, _("No-cd needed"), (position,82-71+self.search_offset), wx.DefaultSize)

        position += self.noDvDCapt.GetSize()[0]+10

        self.freeChk = wx.CheckBox(self.panelItems, 403, pos=(position,82-71), size=wx.DefaultSize)
        self.freeChk.SetValue(True)
        position += 15+self.search_offset
        self.FreeCapt = wx.StaticText(self.panelItems, -1, _("Commercial"), (position,82-71+self.search_offset), wx.DefaultSize)

        position += self.FreeCapt.GetSize()[0]+10
        self.star_x = position

        self.lasthtml_content = ""
        self.list_apps = wx.TreeCtrl(self.panelItems, 106, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|Variables.widget_borders, size=(550, 385), pos=(15,113-71))
        self.list_apps.SetImageList(self.imagesapps)
        self.list_apps.SetSpacing(0);
        self.stars = 0
        #self.content =  wx.TextCtrl(self.panelItems, 107, pos=(220,301), size=(562,212), style = wx.TE_MULTILINE | wx.TE_RICH2 | wx.CB_READONLY | Variables.widget_borders)
        self.content = PyClickableHtmlWindow(self.panelItems, 107, style=Variables.widget_borders, pos=(580,113-71), size=(200,218))
        
        if(os.environ["POL_OS"] == "Linux"):
            self.button = wx.Button(self.panelItems, wx.ID_CLOSE, _("Cancel"), pos=(736-160, 510-71), size=(100,35))
            self.install_button = wx.Button(self.panelItems, wx.ID_APPLY, _("Install"), pos=(843-160, 510-71), size=(100,35))
            self.update_button = wx.Button(self.panelItems, wx.ID_REFRESH, _("Refresh"), pos=(630-160, 510-71), size=(100,35))
        else:
            self.button = wx.Button(self.panelItems, wx.ID_CLOSE, _("Cancel"), pos=(736-160-10, 510-71-8), size=(100,35))
            self.install_button = wx.Button(self.panelItems, wx.ID_APPLY, _("Install"), pos=(843-160-10, 510-71-8), size=(100,35))
            self.update_button = wx.Button(self.panelItems, wx.ID_REFRESH, _("Refresh"), pos=(630-160-10, 510-71-8), size=(100,35))
        
        
        
        
        self.install_button.Enable(False)

        self.new_panel = wx.Panel(self.panelItems, -1, pos=(740-160,113-71), style=Variables.widget_borders, size=self.new_size)
        self.new_panel.SetBackgroundColour((255,255,255))
        self.animation = wx.animate.GIFAnimationCtrl(self.new_panel, -1, Variables.playonlinux_env+"/resources/images/install/wait_mini.gif", (90,100))
        self.animation.Hide()
        self.new_panel.Hide()


        self.ManualInstall = wx.HyperlinkCtrl(self.panelFenp, 111, _("Install a non-listed program"), "", pos=(10,515))
        self.ManualInstall.SetNormalColour(wx.Colour(0,0,0))

        # Panel wait
        self.animation_wait = wx.animate.GIFAnimationCtrl(self.panelWait, -1, Variables.playonlinux_env+"/resources/images/install/wait.gif", ((800-128)/2,(550-128)/2-71))
        self.percentageText = wx.StaticText(self.panelWait, -1, "", ((800-30)/2,(550-128)/2+128+10-71), wx.DefaultSize)
        self.percentageText.SetFont(self.fontTitre)


        self.timer = wx.Timer(self, 1)
        self.Bind(wx.EVT_TIMER, self.TimerAction, self.timer)
        self.timer.Start(200)


        # panel manual


   # self.AddApps()

        #wx.EVT_TREE_SEL_CHANGED(self, 105, self.AddApps)
        wx.EVT_TREE_SEL_CHANGED(self, 106, self.AppsDetails)
        wx.EVT_BUTTON(self, wx.ID_CLOSE, self.closeapp)
        wx.EVT_BUTTON(self, wx.ID_APPLY, self.installapp)
        wx.EVT_BUTTON(self, wx.ID_REFRESH, self.UpdatePol)
        wx.EVT_CLOSE(self, self.closeapp)
        wx.EVT_TREE_ITEM_ACTIVATED(self, 106, self.installapp)
        wx.EVT_TEXT(self, 110, self.search)
        wx.EVT_HYPERLINK(self, 111, self.manual)

        wx.EVT_CHECKBOX(self, 401, self.CheckBoxReload)
        wx.EVT_CHECKBOX(self, 402, self.CheckBoxReload)
        wx.EVT_CHECKBOX(self, 403, self.CheckBoxReload)

        #wx.EVT_CHECKBOX(self, 111, self.manual)
        #Timer, regarde toute les secondes si il faut actualiser la liste

    def TimerAction(self, event):
        if(self.lasthtml_content != self.description.htmlContent):
            self.SetImg(self.description.miniature)
            self.description.miniature = self.description.miniature_defaut

            self.lasthtml_content = self.description.htmlContent;
            if(self.description.htmlContent == "###WAIT###"):
                self.animation.Show()
                self.animation.Play()
                self.new_panel.Show()
                self.content.Hide()
                self.Refresh()
            else:
                self.animation.Stop()
                self.content.Show()
                self.animation.Hide()
                self.new_panel.Hide()
                self.Refresh()
                self.content.SetPage(self.description.htmlContent)


        if(self.stars != self.description.stars):
            self.show_stars(self.description.stars)
            self.stars = self.description.stars

        #if(self.list_cat.GetItemImage(self.list_cat.GetSelection()) != self.description.cat):
        #       self.description.cat = self.list_cat.GetItemImage(self.list_cat.GetSelection())

        if(self.openMin == True):
            if(self.description.med_miniature != None):
                self.wmin = Wminiature(None, -1, self.list_apps.GetItemText(self.list_apps.GetSelection()), self.description.med_miniature)
                self.wmin.Show()
                self.wmin.Center(wx.BOTH)
                self.openMin = False

    def closeapp(self, event):
        self.description.thread_running = False
        self.Destroy()

    def manual(self, event):
        self.live = 1
        self.installapp(self)

    def show_stars(self, stars):
        self.stars = int(stars)

        try :
            self.star1.Destroy()
        except :
            pass
        try :
            self.star2.Destroy()
        except :
            pass
        try :
            self.star3.Destroy()
        except :
            pass
        try :
            self.star4.Destroy()
        except :
            pass
        try :
            self.star5.Destroy()
        except :
            pass

        self.stars = int(self.stars)
        star_y = 83-71;
        star_x = 832-160;
        if(self.stars >= 1):
            self.star1 = wx.StaticBitmap(self.panelItems, -1, wx.Bitmap(Variables.playonlinux_env+"/etc/star.png"), (5*18+star_x,star_y), wx.DefaultSize)
        if(self.stars >= 2):
            self.star2 = wx.StaticBitmap(self.panelItems, -1, wx.Bitmap(Variables.playonlinux_env+"/etc/star.png"), (4*18+star_x,star_y), wx.DefaultSize)
        if(self.stars >= 3):
            self.star3 = wx.StaticBitmap(self.panelItems, -1, wx.Bitmap(Variables.playonlinux_env+"/etc/star.png"), (3*18+star_x,star_y), wx.DefaultSize)
        if(self.stars >= 4):
            self.star4 = wx.StaticBitmap(self.panelItems, -1, wx.Bitmap(Variables.playonlinux_env+"/etc/star.png"), (2*18+star_x,star_y), wx.DefaultSize)
        if(self.stars == 5):
            self.star5 = wx.StaticBitmap(self.panelItems, -1, wx.Bitmap(Variables.playonlinux_env+"/etc/star.png"), (18+star_x,star_y), wx.DefaultSize)

    def UpdatePol(self, event):
        self.DelApps()
        self.Parent.updater.check()
        playonlinux.SetSettings("LAST_TIMESTAMP","0")

    def installapp(self, event):
        if(self.live == 1):
            InstallApplication = "ExecLiveInstall"
        else:
            InstallApplication = self.list_apps.GetItemText(self.list_apps.GetSelection())
        
        if(InstallApplication == "about:creator"):
            self.EasterEgg = sp.egg(None, -1, "PlayOnLinux Conceptor")
            self.EasterEgg.Show()
            self.EasterEgg.Center(wx.BOTH)
        else:
            if(playonlinux.GetSettings("FIRST_INSTALL_DONE") == ""):
                wx.MessageBox(_("When {0} installs a Windows program: \n\n - Leave the default location\n - Do not tick the checkbox 'Run the program' if asked.").format(os.environ["APPLICATION_TITLE"]),_("Please read this"))
                playonlinux.SetSettings("FIRST_INSTALL_DONE","TRUE")

            if(os.path.exists(Variables.playonlinux_rep+"/configurations/listes/search")):
                content = codecs.open(Variables.playonlinux_rep+"/configurations/listes/search", "r", "utf-8").read().split("\n")
                found = False
                for line in content:
                    split = line.split("~")
                    if(split[0] == InstallApplication):
                        found = True
                        break;
                if(found == True):
                    if(len(split) <= 1):
                        self.UpdatePol(self)
                    else:
                        if(split[1] == "1"):
                            wx.MessageBox(_("This program is currently in testing.\n\nIt might not work as expected. Your feedback, positive or negative, is specially important to improve this installer."),_("Please read this"))
                        if(split[2] == "1"):
                            wx.MessageBox(_("This program contains a protection against copy (DRM) incompatible with emulation.\nThe only workaround is to use a \"no-cd\" patch, but since those can also be used for piracy purposes we won't give any support on this matter."), _("Please read this"))

            os.system("bash \""+Variables.playonlinux_env+"/bash/install\" \""+InstallApplication.encode("utf-8","replace")+"\"&")

        self.Destroy()
        return

    def search(self, event):
        self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/search",'r',"utf-8")
        self.apps = self.apps.readlines()
        self.j = 0;
        while(self.j < len(self.apps)):
            self.apps[self.j] = self.apps[self.j].replace("\n","")
            self.j += 1

        self.j = 0;
        self.k = 0;
        self.user_search =self.searchbox.GetValue()
        self.search_result = []

        while(self.j < len(self.apps)):
            if(string.lower(self.user_search) in string.lower(self.apps[self.j])):
                self.search_result.append(self.apps[self.j])
                self.k = self.k + 1;
            self.j = self.j + 1;

        if(self.user_search == "about:creator"):
            self.search_result.append("about:creator")

        if(len(self.user_search) < 2 or "~" in self.user_search):
            self.search_result = []
        self.user_search_cut = string.split(self.user_search,":")
        if(len(self.user_search_cut) > 1):
            if(self.user_search_cut[0] == "get" and self.user_search_cut[1].isdigit()):
                self.search_result.append(self.user_search)

        if(self.user_search != ""):
            self.WriteApps(self.search_result)
        else:
            self.DelApps()


    def EraseDetails(self):
        self.content.SetValue("");

    def AppsDetails(self, event):
        self.install_button.Enable(True)
        self.application = self.list_apps.GetItemText(self.list_apps.GetSelection())
        self.description.download(self.application)


    def sizeUpScreen(self, event):
        self.openMin = True

    def WriteApps(self, array):
        self.imagesapps.RemoveAll()

        self.DelApps()
        self.root_apps = self.list_apps.AddRoot("")
        self.i = 0
        array.sort()
        for app in array:
            app_array = app.split("~")
            appname = app_array[0]
            try:
                free = int(app_array[3])
                testing = int(app_array[1])
                nocd = int(app_array[2])
            except IndexError:
                free = 0
                testing = 0
                nocd = 0
                
            show = True
            if nocd == 1 and self.nocdChk.IsChecked() == 0:
                show = False
            if free == 0 and self.freeChk.IsChecked() == 0:
                show = False
            if testing == 1 and self.testingChk.IsChecked() == 0:
                show = False

            if(show == True):
                self.icon_look_for = Variables.playonlinux_rep+"/configurations/icones/"+appname
                if(os.path.exists(self.icon_look_for)):
                    try:
                        self.imagesapps.Add(wx.Bitmap(self.icon_look_for))
                    except:
                        pass
                else:
                    self.imagesapps.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/playonlinux22.png"))
                itemId = self.list_apps.AppendItem(self.root_apps, appname, self.i)
                if testing == 1:
                    # (255,255,214) is web site color for beta, but it's not very visible next to plain white,
                    # and red is the color of danger
                    self.list_apps.SetItemBackgroundColour(itemId, (255,214,214))
                self.i = self.i+1

    def DelApps(self):
        self.list_apps.DeleteAllItems()

    def SetImg(self, image):
        self.image.Destroy()
        self.image = wx.StaticBitmap(self.panelItems, 108, wx.Bitmap(image), self.image_position, wx.DefaultSize)
        self.image.Bind(wx.EVT_LEFT_DOWN, self.sizeUpScreen)
        self.image.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.Refresh()

    def ResetImg(self):
        self.SetImg(Variables.playonlinux_env+"/resources/images/pol_min.png")

    def CheckBoxReload(self, event):
        chk_id = event.GetId()
        if(chk_id == 401):
            if(self.testingChk.IsChecked() == 1):
                wx.MessageBox(_("By enabling this, you will have access to testing installers.\n\n{0} cannot ensure that your app will work without any problems").format(os.environ["APPLICATION_TITLE"]),_("Please read this"))
        if(chk_id == 402):
            if(self.nocdChk.IsChecked() == 1):
                wx.MessageBox(_("By enabling this, you will have access to installers for programs that contain protections against copy (DRM) incompatible with emulation.\nThe only workaround is to use \"no-cd\" patches, but since those can also be used for piracy purposes we won't give any support on this matter."), _("Please read this"))

        if(self.searchbox.GetValue() == ""):
            self.AddApps(self, noevent=True)
        else:
            self.search(self)

    def AddApps(self, event, noevent=False):
        self.searchbox.SetValue("")
        #self.cat_selected=self.list_cat.GetItemText(self.list_cat.GetSelection()).encode("utf-8","replace")
        if(noevent == False):
            if(event.GetId() >= 3000):
                self.cat_selected = event.GetId() - 3000
            else:
                self.cat_selected = event.GetId() - 2000

            self.current_cat = self.cat_selected
        else:
            try:
                self.cat_selected = self.current_cat
            except:
                return 0
        if(self.cat_selected == 8):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/0",'r',"utf-8")
        if(self.cat_selected == 3):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/1",'r',"utf-8")
        if(self.cat_selected == 0):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/2",'r',"utf-8")
        if(self.cat_selected == 7):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/3",'r',"utf-8")
        if(self.cat_selected == 5):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/4",'r',"utf-8")
        if(self.cat_selected == 6):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/5",'r',"utf-8")
        if(self.cat_selected == 4):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/6",'r',"utf-8")
        if(self.cat_selected == 1):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/7",'r',"utf-8")
        if(self.cat_selected == 2):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/8",'r',"utf-8")
        if(self.cat_selected == 9):
            self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/9",'r',"utf-8")
        #if(self.cat_selected == 12):
        #       self.apps = codecs.open(Variables.playonlinux_rep+"/configurations/listes/10",'r',"utf-8")


        if(self.cat_selected != -1):
            self.apps = self.apps.readlines()
            self.j = 0
            while(self.j < len(self.apps)):
                self.apps[self.j] = self.apps[self.j].replace("\n","")
                self.j += 1
            self.WriteApps(self.apps)

########NEW FILE########
__FILENAME__ = irc
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Pâris Quentin
# Copyright (C) 2007-2010 PlayOnLinux Team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os, sys, string, shutil
import wx, time
#from subprocess import Popen,PIPE

import wine_versions
import lib.playonlinux as playonlinux
import lib.wine as wine
import lib.Variables as Variables
import lib.lng as lng
import lib.irc as irc
from wx.lib.ClickableHtmlWindow import PyClickableHtmlWindow

class Onglets(wx.Notebook):
    # Classe dérivée du wx.Notebook
    def __init__(self, parent):
        self.notebook = wx.Notebook.__init__(self, parent, -1)

    def getSettings(self): # Faudra revoir ça dans une future version
        irc_settings = {}

        if(os.environ["POL_OS"] == "Linux"):
            irc_settings['NICKNAME'] = os.environ["USER"]+"-pol"
        else:
            irc_settings['NICKNAME'] = os.environ["USER"]+"-pom"

        irc_settings['AUTOCONNECT'] = "0"
        irc_settings['ALERT'] = "0"
        irc_settings["PLAYSOUND"] = "1"
        if(os.path.exists(Variables.playonlinux_rep+"/configurations/options/irc")):
            ircfile = open(Variables.playonlinux_rep+"/configurations/options/irc","r").readlines()
            self.i = 0

            while(self.i < len(ircfile)):
                line_parsed = string.split(ircfile[self.i].replace("\n","").replace("\r",""),"=")
                irc_settings[line_parsed[0]] = line_parsed[1]
                self.i += 1
        return irc_settings

    def selectChanByText(self, text):
        self.item = self.root_window

        self.ij = 0
        self.texte = None
        while(self.texte != text):
            if(self.ij >= len(irc.chans)):
                return self.window.GetLastChild(self.root_window)

            self.item = self.window.GetNextVisible(self.item)
            self.texte = self.window.GetItemText(self.item)
            self.ij += 1


        return self.item

    def OpenWindow(self):
        #if(nom.lower() not in irc.chans and not "@" in nom and nom != "freenode-connect"):
        #self.old_selection = self.window.GetItemText(self.window.GetSelection())
        self.window.DeleteAllItems()
        self.root_window = self.window.AddRoot("")
        self.i = 0
        while(self.i < len(irc.chans)):
            nom = irc.chans[self.i].lower()
            if("." not in nom and nom != "freenode-connect"):
                if("#" in nom):
                    self.window.AppendItem(self.root_window, nom, 0)
                else:
                    if(nom.lower() == "nickserv" or nom.lower() == "chanserv" or nom.lower() == "botserv"):
                        self.window.AppendItem(self.root_window, nom, 2)
                    else:
                        if(nom.lower() == "playonlinux"):
                            self.window.AppendItem(self.root_window, nom, 3)
                        else:
                            self.window.AppendItem(self.root_window, nom, 1)
                #if(self.i == 0):
                    #self.window.SelectItem(self.window.GetLastChild(self.root_window))
            self.i += 1
        #item = self.selectChanByText(self.old_selection)
        #self.window.SelectItem(item)
            #irc.open_window.append(nom.lower())

    def selectWindow(self, name):
        item = self.selectChanByText(name)
        self.window.SelectItem(item)

    def AjouteIRC(self, nom):
        self.panel = wx.Panel(self, -1)
        self.panels_button = wx.Panel(self.panel, -1)
        self.panels_main = wx.Panel(self.panel, -1)
        self.panels_connexion = wx.Panel(self.panel, -1)
        #self.content =  wx.TextCtrl(self.panel, 107, pos=(0,20), size=(500,300), style = wx.TE_MULTILINE | wx.TE_RICH2 | wx.CB_READONLY | wx.RAISED_BORDER)

        self.content = PyClickableHtmlWindow(self.panels_main, -1, style=wx.RAISED_BORDER)
        self.buddy = wx.TreeCtrl(self.panels_main, 126, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|wx.RAISED_BORDER)
        self.buddy.SetSpacing(0);

        self.window = wx.TreeCtrl(self.panels_main, 127, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|wx.RAISED_BORDER)
        #self.root_window = self.window.AddRoot("")
        self.window.SetSpacing(0);

        self.buddy_images = wx.ImageList(16, 16)
        self.buddy_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/star.png"));
        self.buddy_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/h-star.png"));
        self.buddy_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/playonlinux16.png"));
        self.buddy_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/spacer16.png"));
        self.buddy_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/star.png"));
        self.buddy.SetImageList(self.buddy_images)

        self.window_images = wx.ImageList(16,16)
        self.window_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/internet-group-chat.png"));
        self.window_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/system-users.png"));
        self.window_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/applications-system.png"));
        self.window_images.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/playonlinux16.png"));
        self.window.SetImageList(self.window_images)

        self.buddy.SetSpacing(0);
        self.field =  wx.TextCtrl(self.panels_button, 121, style = wx.TE_MULTILINE)
        self.button = wx.Button(self.panels_button, 122, _("Send"))
        self.connect = wx.Button(self.panels_connexion, 123, _("Connect"), pos=(0,0), size=(150,28))
        self.disconnect = wx.Button(self.panels_connexion, 124, _("Disconnect"), pos=(0,0), size=(150,28))
        self.close = wx.Button(self.panels_connexion, 128, _("Leave"), pos=(155,0), size=(150,28))
        #self.close = wx.BitmapButton(self.panels_connexion, 128, wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/wineserver.png"), pos=(630,0))
        self.settings = self.getSettings()
        self.nickname = wx.TextCtrl(self.panels_connexion, 125, self.settings["NICKNAME"], size=(300,25), pos=(330,2))
        #self.channel_choices = ["#playonlinux-fr","#playonlinux-en","#playonlinux-it","#playonlinux-ru","#playonlinux-pl","#playonlinux-hu","#playonlinux-es"]
        #self.channel_choices.sort()
        #self.channel = wx.ComboBox(self.panels_connexion, 130,  _("Join a channel"), size=(190,28), pos=(510,0), choices=self.channel_choices)
        self.close.Enable(False)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizerInputs = wx.BoxSizer(wx.HORIZONTAL)
        self.sizerMain = wx.BoxSizer(wx.HORIZONTAL)

        self.sizer.Add(self.panels_connexion, 3, wx.EXPAND|wx.ALL, 2)
        self.sizer.Add(self.panels_main, 36, wx.EXPAND|wx.ALL, 2)
        self.sizer.Add(self.panels_button, 4, wx.EXPAND|wx.ALL, 2)

        self.sizerInputs.Add(self.field, 14, wx.EXPAND|wx.ALL, 2)
        self.sizerInputs.Add(self.button, 4, wx.EXPAND|wx.ALL, 2)

        self.sizerMain.Add(self.window, 4, wx.EXPAND|wx.ALL, 2)
        self.sizerMain.Add(self.content, 10, wx.EXPAND|wx.ALL, 2)
        self.sizerMain.Add(self.buddy, 4, wx.EXPAND|wx.ALL, 2)

        self.panel.SetSizer(self.sizer)
        self.panels_button.SetSizer(self.sizerInputs)
        self.panels_main.SetSizer(self.sizerMain)
        self.panel.SetAutoLayout(True)

        self.AddPage(self.panel, nom)
        self.field.Bind(wx.EVT_KEY_UP, self.EventKey)
        self.nickname.Bind(wx.EVT_KEY_UP, self.NicknameKey)
        #self.channel.Bind(wx.EVT_KEY_UP, self.EventChannel)

        wx.EVT_COMBOBOX(self, 130, self.JoinChan)
        wx.EVT_BUTTON(self,  122,  self.EventButton)
        wx.EVT_BUTTON(self,  123,  self.EventStart)
        wx.EVT_BUTTON(self,  124,  self.EventStop)
        wx.EVT_BUTTON(self,  128,  self.EventClose)
        wx.EVT_TREE_ITEM_ACTIVATED(self, 126, self.AddNick)
        #wx.EVT_TREE_ITEM_ACTIVATED(self, 127, self.filtrer)
        #self.disconnect.Enable(False)
        #self.EventStart(self)

    def AddNick(self, event):
        self.buddy_txt = self.buddy.GetItemText(self.buddy.GetSelection()).encode("utf-8","replace")
        irc.join(self.buddy_txt)
        #if(self.buddy_txt not in irc.chans):

        #self.field.SetValue("/msg "+self.buddy_txt+" ")
        #self.OpenWindow(self.buddy_txt)

    def SendMessage(self):
        self.chars = self.field.GetValue().replace('\n','').encode("utf-8","replace")
        if(self.chars):
            self.field.Clear()
            irc.SendMSG(self.chars)
        else:
            self.field.Clear()

    def EventClose(self, event):
        #index = irc.get_index(self.window.GetItemText(self.window.GetSelection()).lower()):
        #print index

        #del irc.messages[index]
        #del irc.names[index]
        #del irc.endnames[index]
        #del irc.chans[index]
        irc.leave_chan(self.window.GetItemText(self.window.GetSelection()).lower())

        self.window.Delete(self.window.GetSelection())
        #self.close.Enable(False)

    def EventStart(self, event):
        irc.Nick = self.nickname.GetValue().encode("utf-8","replace")
        irc.Connexion()

    def EventChannel(self, event):
        if(event.GetKeyCode() == wx.WXK_RETURN):
            self.JoinChan(self)

        event.Skip()

    def JoinChan(self, event):
        my_chan = self.channel.GetValue()
        if(my_chan[0] == "#"):
            if(irc.ircconnected == True):
                irc.join(my_chan)
        self.channel.SetValue(_("Join a channel"))
    def EventStop(self, event):
        irc.stop()

    def EventButton(self, event):
        self.SendMessage()

    def EventKey(self, event):
        if(event.GetKeyCode() == wx.WXK_RETURN):
            self.SendMessage()

        event.Skip()

    def NicknameKey(self, event):
        if(event.GetKeyCode() == wx.WXK_RETURN):
            if(irc.ircconnected == True):
                irc.ChangeNick(self.nickname.GetValue().encode("utf-8","replace"))
            else:
                irc.Connexion()
        event.Skip()


class IrcClient(wx.Frame):
    def __init__(self,parent,title=""):
        wx.Frame.__init__(self, parent, -1, title, size = (700, 500))

        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.timer = wx.Timer(self, 1)
        self.onglets = Onglets(self)
        #self.onglets.hide()
        self.onglets.AjouteIRC(_("Messenger"))
        self.oldreload = ""
        self.oldimg = ""
        self.names = ["~"]
        self.messages = ["~"]
        self.chans = ["~"]
        self.already_connected = False
        self.settings = irc.getSettings()
        self.resized = False
        #self.settings["AUTOCONNECT"] = "TRUE"
        #Timer, regarde toute les secondes si il faut actualiser la liste
        self.Bind(wx.EVT_TIMER, self.AutoReload, self.timer)
        wx.EVT_CLOSE(self, self.CloseIRC)
        self.timer.Start(200)

    def CloseIRC(self, event):
        if(not irc.ircconnected or wx.YES == wx.MessageBox(_('If you close this window, you cannot read further replies. Are you sure that you want to close it?').format(os.environ["APPLICATION_TITLE"]).decode("utf-8","replace"), os.environ["APPLICATION_TITLE"] ,style=wx.YES_NO | wx.ICON_QUESTION)):
            self.onglets.EventStop(self)
            self.Destroy()

    def change_irc_window(self, event):
        #self.irc_user_list(self)
        self.html_reload(self)
        #print self.onglets.window.GetItemText(self.onglets.window.GetSelection())

    def irc_key(self, item):
        if(item[0] == "~"):
            return ("A")
        else:
            if(item[0] == "@" or item[0] == "&"):
                return ("B")
            else :
                if(item[0] == "%"):
                    return ("C")
                else:
                    if(item[0] == "+"):
                        return ("D")
                    else:
                        return string.lower(item[0])

    def html_reload(self, event):
                #print("Refresh html")
        self.window_txt = self.onglets.window.GetItemText(self.onglets.window.GetSelection()).encode("utf-8","replace")
        irc.selected_window = self.window_txt
        self.chat_content = ""
        # On regarde quelle liste on va prendre
        id_liste = irc.get_index(self.window_txt)
        # On ajoute tout
        self.i = 0
        if(len(irc.messages[id_liste]) >= 300):
            del irc.messages[id_liste][0]

        while(self.i < len(irc.messages[id_liste])):
            if(self.i != 0):
                self.chat_content += "\n<br />"
            self.chat_content += irc.messages[id_liste][self.i]
            self.i += 1
        self.onglets.content.SetPage("<html><head></head><body><p align='left'>"+self.chat_content+"</p></body></html>")
        self.onglets.content.Scroll(0,len(irc.messages[id_liste])*2)

    def html_reload_status(self, event):
        self.chat_content = ""
        # On regarde quelle liste on va prendre
        self.i = 0
        if(len(irc.status_messages) >= 300):
            del irc.status_messages[0]

        while(self.i < len(irc.status_messages)):
            self.chat_content += irc.status_messages[self.i]+"<br />\n"
            self.i += 1
        self.onglets.content.SetPage("<html><head></head><body><p align='left'>"+self.chat_content+"</p></body></html>")
        self.onglets.content.Scroll(0,len(irc.status_messages)*2)

    def irc_user_list(self, event):
        self.window_txt = self.onglets.window.GetItemText(self.onglets.window.GetSelection()).encode("utf-8","replace").lower()

        irc.selected_window = self.window_txt
        # On casse tout
        self.onglets.buddy.DeleteAllItems()
        self.buddy_root = self.onglets.buddy.AddRoot("")
        # On regarde quelle liste on va prendre
        id_liste = irc.get_index(self.window_txt)
        # On ajoute tout
        self.user_i = 0
        while(self.user_i < len(irc.names[id_liste])):
            num = 3
            irc.names[id_liste].sort(key=self.irc_key)
            if("@" in irc.names[id_liste][self.user_i] or "&" in irc.names[id_liste][self.user_i]):
                num = 0
            if("~" in irc.names[id_liste][self.user_i]):
                num = 4
            if("%" in irc.names[id_liste][self.user_i]):
                num = 1
            if("+" in irc.names[id_liste][self.user_i]):
                num = 2
            self.onglets.buddy.AppendItem(self.buddy_root, irc.names[id_liste][self.user_i].replace("&","").replace("~","").replace("%","").replace("+","").replace("@",""), num)
            html_hex = irc.GenColor(irc.names[id_liste][self.user_i].replace("&","").replace("~","").replace("%","").replace("+","").replace("@",""))
            self.couleur = [pow(int(html_hex[2],16),2),pow(int(html_hex[3],16),2),pow(int(html_hex[4],16),2)]
            self.onglets.buddy.SetItemTextColour(self.onglets.buddy.GetLastChild(self.buddy_root), wx.Colour(int(self.couleur[0]),int(self.couleur[1]),int(self.couleur[2])))
            self.user_i += 1
        #wx.Yield()

    def AutoReload(self, event):
        if(self.resized == False): # wx 2.9 resizing probem
            self.SetSize((800,500))
            self.resized = True

        self.new_string = irc.string_to_write
        if(irc.ircconnected == True):
            if(self.chans != irc.chans):
                self.onglets.OpenWindow()
                self.chans = irc.chans[:]
                #print "Refresh"
            #else :
            #print str(self.chans)+" --- "+str(irc.chans)

            self.window_txt = self.onglets.window.GetItemText(self.onglets.window.GetSelection()).encode("utf-8","replace").lower()

            if(len(self.window_txt) > 0):
                id_liste = irc.get_index(self.window_txt)
                if(self.window_txt[0] == "#"):
                #print self.names
                    if(irc.names[id_liste] != self.names):
                        self.irc_user_list(self)
                        self.names = irc.names[id_liste][:]

            #if(len(irc.messages) > id_liste+1):

                if(irc.messages[id_liste] != self.messages):
                    self.html_reload(self)
                    self.messages = irc.messages[id_liste][:]

            if(irc.select_window != ""):
                self.onglets.selectWindow(irc.select_window)
                irc.select_window = ""

            if(self.onglets.window.GetItemText(self.onglets.window.GetSelection()) != irc.selected_window):
                irc.selected_window = self.onglets.window.GetItemText(self.onglets.window.GetSelection())

            if(irc.selected_window == "#playonlinux" or irc.selected_window == ""):
                self.onglets.close.Enable(False)
            else:
                self.onglets.close.Enable(True)


            self.onglets.connect.Hide()
            self.onglets.disconnect.Show()
            if(len(self.chans) == 0):
                if(irc.status_messages != self.messages):
                    self.html_reload_status(self)
                    self.messages = irc.status_messages[:]
        else:
            if(irc.status_messages != self.messages):
                self.html_reload_status(self)
                self.messages = irc.status_messages[:]

            self.onglets.buddy.DeleteAllItems()
            self.onglets.window.DeleteAllItems()
            self.onglets.connect.Show()
            self.onglets.disconnect.Hide()
            if(self.settings["AUTOCONNECT"] == "1"):
                if(self.already_connected == False):
                    irc.Nick = self.onglets.nickname.GetValue().encode("utf-8","replace")
                    irc.connect()
                    self.already_connected = True;





irc = irc.IRCClient()

########NEW FILE########
__FILENAME__ = irc
#!/usr/bin/python
# -*- coding:Utf-8 -*-
import threading
import Variables
import time
import socket
import string
import os, math
import wx
import re
global allowed_people
global refused_people
allowed_people = []
refused_people = []
class IRCClient(threading.Thread):
    string_to_write = ""
    def __init__(self):
        threading.Thread.__init__(self)
        # https://www.freenode.net/irc_servers.shtml
        self.serveur = "chat.freenode.net"
        self.port = 6667
        self.Nick = Variables.current_user+"-pol"
        self.chanAutoJoin = "#playonlinux"
        self.start()
        self.freenode_tried = False

    def get_list(self, chan):
        if(self.ircconnected == True):
            self.connexion.send('NAMES '+chan+'\r\n')

    def htmlspecialchars(self, string):
        self.string = string.replace("<","&lt;")
        self.string = self.string.replace(">","&gt;")
        return self.string

    def _vivify(self, matchobj):
        url = matchobj.group(1)
        return "<A href=\"%s\">%s</A>" % (url, url)

    def urlvivify(self, string):
        return re.sub(r'((?:[fF][tT][pP]://|[hH][tT][tT][pP][sS]?://|[nN][eE][wW][sS]://)[-a-zA-Z0-9._/%?=&#]*)', self._vivify, string, 0)

    def connect(self): # Se connecte au serveur IRC
        if(self.ircconnected == False):
            self.status_messages.append(self.html_convert(None, "Connecting ...","#AA0000","#AA0000",True))
            try:
                self.connexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connexion.connect((self.serveur, self.port))
                self.ircconnected = True
                self.connexion.send('NICK' + ' ' + self.Nick + '\r\n')
                self.realname = os.environ["APPLICATION_TITLE"]+" Client "+os.environ["VERSION"]
                self.connexion.send('USER' + ' PlayOnLinux ' + self.Nick + ' ' + self.serveur + ' :' + self.realname + '\r\n')
            except:
                self.status_messages.append(self.html_convert(None, "Error! Unable to connect. Check your internet connexion and try again.","#AA0000","#AA0000",True))
                self.stop()
        else:
            self.status_messages.append(self.html_convert(None, "You are in offline-mode","#AA0000","#AA0000",True))


    def getSettings(self):
        irc_settings = {}

        irc_settings['NICKNAME'] = os.environ["USER"]+"-pol"
        irc_settings['AUTOCONNECT'] = "0"
        irc_settings['ALERT'] = "0"
        irc_settings["PLAYSOUND"] = "1"
        if(os.path.exists(Variables.playonlinux_rep+"/configurations/options/irc")):
            ircfile = open(Variables.playonlinux_rep+"/configurations/options/irc","r").readlines()
            self.i = 0

            while(self.i < len(ircfile)):
                line_parsed = string.split(ircfile[self.i].replace("\n","").replace("\r",""),"=")
                irc_settings[line_parsed[0]] = line_parsed[1]
                self.i += 1
        return irc_settings

    def getNick(self, chaine):
        self.nickname = string.split(chaine, "!")
        self.nickname = self.nickname[0]
        self.nickname = self.nickname[1:len(self.nickname)]
        return self.nickname

    def ChangeNick(self, nick):
        if(self.ircconnected == True):
            self.connexion.send("NICK :"+nick+"\r\n")
            self.Nick = nick


    def GenColor(self, pseudo):
        self.colors = ["000","F00","00F","080","008","010","02E","02F","D60","D80","DA0","E00","E40","E50","E70","E80","F24","F42","777"
                       "06F","090","0A0","0AD","0C0","0F0","0CF","150","209","21F","D11","D12","D13","D20","D40","EA0","F27","F43","666"
                       "280","29E","300","30F","32F","34F","36F","470","560","5A0","5AF","5F0","64F","750","800","850","F28","F44","999"
                       "A90","A80","A00","A0F","A1E","A1C","A08","A70","C40","C30","C60","C80","CA0","D10","EC0","EC1","F29","F45","222"
                       "EC2","EC3","ED1","ED0","ED3","F10","F11","F12","F13","F14","F20","F21","F22","F23","F24","F26","F41","090",
                       "F91","F92","F93","F94","F95","F96","F97","F98","F99","F9A","F9A","F9C","F9D","F9E","F9F","0A0","0A1","0A2",
                       "0D0","0D1","0D2","0D3","0D4","0D5","0D6","0D7","0D8","0D9","0DA","0DA","0DC","0DD","0DE","0DF","FE0","FE1",
                       "FE2","FD0","FD1","FD2","160","161","162","163","164","165","166","170","171","173","174","175","176","#AAA"]
        #self.colors.sort()
        self.colors.reverse()

        i = 0
        somme = 0
        max = 0
        while(i < len(pseudo)):
            i += 1
            somme += ord(pseudo[i - 1])*i
            max += 127*i



        num=math.cos(somme * len(self.colors) / max) * len(self.colors)
        num=int(num)
        #print num
        return "0x"+self.colors[num]

    def smile(self, string):
        self.newstring = string
        self.newstring = self.newstring.replace("O:-)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-angel.png'>")
        self.newstring = self.newstring.replace(":-)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-smile.png'>")
        self.newstring = self.newstring.replace(":)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-smile.png'>")
        self.newstring = self.newstring.replace(":-(","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-sad.png'>")
        self.newstring = self.newstring.replace(":(","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-sad.png'>")
        self.newstring = self.newstring.replace(":'(","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-crying.png'>")
        self.newstring = self.newstring.replace("(6)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-devilish.png'>")
        self.newstring = self.newstring.replace("8-)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-glasses.png'>")
        self.newstring = self.newstring.replace(":-O","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-surprise.png'>")
        self.newstring = self.newstring.replace(":-D","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-grin.png'>")
        self.newstring = self.newstring.replace(":D","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-grin.png'> ")
        self.newstring = self.newstring.replace(":-*","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-kiss.png'>")
        self.newstring = self.newstring.replace("(monkey)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-monkey.png'>")
        self.newstring = self.newstring.replace(":-|","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-plain.png'>")
        self.newstring = self.newstring.replace(":|","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-plain.png'> ")
        self.newstring = self.newstring.replace(";-)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-wink.png'> ")
        self.newstring = self.newstring.replace(";)","<img src='"+Variables.playonlinux_env+"/resources/images/emotes/face-wink.png'> ")
        return self.newstring

    def playsound(self):
        settings = self.getSettings()
        if(settings["PLAYSOUND"] == "1"):
            #os.system("playsound "+Variables.playonlinux_env+"/etc/snd/snd.wav & 2> /dev/null > /dev/null")
            sound = wx.Sound(Variables.playonlinux_env+"/resources/sounds/irc.wav")
            sound.Play(wx.SOUND_SYNC)

    def join(self, chan):
        if(chan.lower() not in self.chans and self.ircconnected == True):
            if(chan[0] == "#"):
                self.connexion.send("JOIN :"+chan+"\r\n")
            self.chans.append(chan.lower())
            self.endnames.append(False)
            self.names.append([])
            self.messages.append([])

        self.select_window = chan.lower()

            #self.open_window.append(chan.lower())
            #self.get_list(chan)

    def leave_chan(self, chan):
        if(chan.lower() in self.chans and self.ircconnected == True):
            index = self.get_index(chan)
            if(chan[0] == "#"):
                self.connexion.send("PART :"+chan+"\r\n")

            del self.messages[index]
            del self.names[index]
            del self.endnames[index]
            del self.chans[index]
            self.select_window = self.chanAutoJoin

    def html_convert(self, pseudo, message, pseudocolor='#000000', messagecolor='#000000', action = False):
        tps = time.strftime("%H:%M:%S")
        message = message.replace("  "," &nbsp;")
        message = message.replace("\x1f","")
        message = message.replace("\x02","")
        message = self.htmlspecialchars(message)
        message = self.urlvivify(message)
        message = self.smile(message)
        if(pseudo != None):
            if(action == False):
                return "<font color='"+pseudocolor+"'>("+tps+") <b>"+pseudo+":</b> </font><font color='"+messagecolor+"'>"+message+"</font>"
            else:
                return "<font color='"+pseudocolor+"'>("+tps+") <b>*** "+pseudo+"</b> </font><font color='"+messagecolor+"'>"+message+"</font>"
        else :
            return "<font color='"+messagecolor+"'>("+tps+") "+message+"</font>"
    def get_index(self, content):
        self.boucle = 0
        while(self.boucle < len(self.chans)):
            if(self.chans[self.boucle].lower() == content):
                return self.boucle
            self.boucle +=1

        return -1

    def getMsg(self, array, num=3):
        self.boucle = num
        self.chaine = ""
        while(self.boucle < len(array)):
            self.chaine += array[self.boucle]+" "
            self.boucle += 1
        return self.chaine[1:len(self.chaine)-1]

    def check_access(self, window, i=0):
        print("Try #"+str(i))
        if(window in allowed_people):
            return True
        elif(window in refused_people):
            return False
        else:
            if(i == 0):
                self.connexion.send("PRIVMSG PlayOnLinux :CHECK_ACCESS "+window+"\r\n")
            if(i <= 5):
                time.sleep(1)
                return self.check_access(window, i+1)
            else:
                return False

    def SendMSG(self, message, chan="~current"):
        if(self.ircconnected == False):
            self.status_messages.append(self.html_convert(None, "You are not connected.","#FF0000","#FF0000",True))
        else :
            if(message[0] == "/"): # Une commande
                self.message_parsed = string.split(message," ")
                if(self.message_parsed[0].lower() == "/join" and len(self.message_parsed) > 1):
                    if(self.message_parsed[1][0] == "#"):
                        newchan = self.message_parsed[1].lower()
                    else:
                        newchan = "#"+self.message_parsed[1].lower()
                    self.join(newchan)

                if(self.message_parsed[0].lower() == "/query" and len(self.message_parsed) > 1):
                    newchan = self.message_parsed[1].lower()
                    self.join(newchan)

                if(self.message_parsed[0].lower() == "/kick" and len(self.message_parsed) > 1):
                    user = self.message_parsed[1].lower()
                    if(len(self.message_parsed) > 2):
                        self.i = 2
                        message = ""
                        while(self.i < len(self.message_parsed)):
                            if(self.i != 2):
                                message += " "
                            message += self.message_parsed[self.i]
                            self.i += 1
                    else :
                        message = self.Nick

                    self.connexion.send("KICK "+self.selected_window+" "+user+" "+message+"\r\n")

                if(self.message_parsed[0].lower() == "/nick" and len(self.message_parsed) > 1):
                    self.ChangeNick(self.message_parsed[1])

                if(self.message_parsed[0].lower() == "/me" and len(self.message_parsed) > 1):
                    if(chan == "~current"):
                        window = self.selected_window
                    else:
                        window = chan
                    self.connexion.send("PRIVMSG "+window+" :\x01ACTION "+message.replace("/me ","")+" \x01\r\n")
                    self.index = self.get_index(window)
                    self.messages[self.index].append(self.html_convert(self.Nick,message.replace("/me ",""),"#000088","#000088",True))

                if((self.message_parsed[0].lower() == "/msg" or self.message_parsed[0].lower() == "/privmsg") and len(self.message_parsed) > 2):
                    self.join(self.message_parsed[1].lower())
                    self.i = 2
                    message = ""

                    while(self.i < len(self.message_parsed)):
                        if(self.i != 2):
                            message += " "
                        message += self.message_parsed[self.i]
                        self.i += 1


                    self.connexion.send("PRIVMSG "+self.message_parsed[1].lower()+" :"+message+"\r\n")
                    self.index = self.get_index(self.message_parsed[1].lower())
                    self.messages[self.index].append(self.html_convert(self.Nick,message,"#000088","#000088",True))

            else:
                if(chan == "~current"):
                    window = self.selected_window
                else:
                    window = chan

                if self.check_access(window):
                    self.connexion.send("PRIVMSG "+window+" :"+message+"\r\n")

                    self.index = self.get_index(window)
                    if(window[0] != "#"):
                        self.messages[self.index].append(self.html_convert(self.Nick,message,"#000088"))
                    else:
                        self.messages[self.index].append(self.html_convert(self.Nick,message,str(self.GenColor(self.Nick)).replace("0x","#")))
                else:
                    wx.MessageBox(_("Sorry, this person does not want to receive private messages").format(os.environ["APPLICATION_TITLE"]),_("Error"))

    def filtrer_liste(self, liste):
        self.boucle = 0
        self.new_list = []
        while(self.boucle < len(liste)):
            self.new_list.append(liste[self.boucle].replace("@","").replace("+","").replace("&","").replace("%","").replace("~","").lower())
            self.boucle += 1

        return self.new_list

    def traiter(self, line):
        if(len(self.names) > 1 and "@PlayOnLinux" not in self.names[1] and self.endnames[1] == True):
            self.status_messages.append(self.html_convert(None, _("Sorry {0} messenger service is not available for the moment.\n\nPlease retry later").format(os.environ["APPLICATION_TITLE"]),"#AA0000","#AA0000",True))
            self.stop()

        self.line = string.split(line, " ") # On parse la ligne mot par mot
        # On répond aux pings
        if(self.line[0] and len(self.line) > 1):
            self.message_id = self.line[1]
            if(self.line[0] == "PING"): # PINGS
                self.connexion.send("PONG "+self.line[1]+"\r\n")



            if(self.message_id == '353'): # NAMES
                if(len(self.line) > 4):
                    self.canal = self.line[4].lower()
                    self.canal_index = self.get_index(self.canal)
                    if(self.canal_index != -1):
                        if(self.endnames[self.canal_index] == True):
                            self.names[self.canal_index] = []
                            self.endnames[self.canal_index] = False

                        self.boucle = 5
            #                       self.names[self.canal_index].append(self.message_id[4])
                        while(self.boucle < len(self.line)):
                            if(self.line[self.boucle] != ''):
                                self.names[self.canal_index].append(self.line[self.boucle].replace(":",""))
                            self.boucle +=1

            if(self.message_id == '366'): # END NAMES
                if(len(self.line) > 3):
                    self.canal = self.line[3].lower()
                    self.canal_index = self.get_index(self.canal)
                    if(self.canal_index != -1):
                        self.endnames[self.canal_index] = True

            if(self.message_id == '001'): # CONNECTED
                self.join(self.chanAutoJoin)

            if(self.message_id == '332'): # topic
                self.subject = self.getMsg(self.line, 4)
                if(len(self.line) > 3):
                    self.chan = self.line[3].lower()
                    self.chan_index = self.get_index(self.chan)
                    self.messages[self.chan_index].append(self.html_convert(None,"Welcome to "+self.chan+"","#666666","#666666",True))
                    self.messages[self.chan_index].append(self.html_convert(None,"The topic is : "+self.subject+"","#666666","#666666",True))

            if(self.message_id == 'TOPIC'):
                if(len(self.line) > 2):
                    self.sender = self.getNick(self.line[0])
                    self.chan = self.line[2].lower()
                    self.subject = self.getMsg(self.line)
                    self.messages[self.chan_index].append(self.html_convert(self.sender," has defined the topic : "+self.subject+"","#666666","#666666",True))

            if(self.message_id == '474'): # Banned
                if(len(self.line) > 3):
                    self.chan = self.line[3].lower()
                    self.chan_index = self.get_index(self.chanAutoJoin)

                    if(self.chan == self.chanAutoJoin):
                        self.status_messages.append(self.html_convert(None,"Unable to join the chat : You have been banned","#AA0000","#AA0000",True))
                        self.stop()
                    else:
                        self.messages[self.chan_index].append(self.html_convert(None,"Unable to join "+self.chan+" : You have been banned","#AA0000","#AA0000",True))
                        self.leave_chan(self.chan)
            #[':irc.steredenn.fr', '474', 'tinou-pol', '#playonlinux', ':Cannot', 'join', 'channel', '(+b)']

            if(self.message_id == 'JOIN'):
                if(len(self.line) > 2):
                    self.sender = self.getNick(self.line[0])
                    self.window = self.line[2].lower().replace(":","")
                    self.index = self.get_index(self.window)
                    message = " has joined "+self.window
                    self.messages[self.index].append(self.html_convert(self.sender,message,"#888888","#888888",True))
                    self.get_list(self.chans[self.index])

            if(self.message_id == 'PART'):
                if(len(self.line) > 2):
                    self.sender = self.getNick(self.line[0])
                    self.window = self.line[2].lower().replace(":","")
                    self.index = self.get_index(self.window)
                    message = " has left "+self.window
                    self.messages[self.index].append(self.html_convert(self.sender,message,"#888888","#888888",True))
                    self.get_list(self.chans[self.index])

            if(self.message_id == '401'): # No such nick channels
                if(len(self.line) > 3):
                    self.msg_to = self.line[3]
                    message = " is offline"
                    self.index = self.get_index(self.msg_to)
                    self.messages[self.index].append(self.html_convert(self.msg_to,message,"#888888","#888888",True))

            if(self.message_id == '482'): # No such nick channels
                message = "Your not channel operator"
                self.index = self.get_index(self.selected_window)
                self.messages[self.index].append(self.html_convert(None,message,"#888888","#888888",True))

            if(self.message_id == 'NICK'):
                if(len(self.line) > 2):
                    self.sender = self.getNick(self.line[0])
                    self.new_nick = self.line[2].replace(":","")
                    message = " is known as "+self.new_nick
                    self.i = 0
                    while(self.i < len(self.chans)):
                        if(self.sender.lower() in self.filtrer_liste(self.names[self.i])):
                            self.messages[self.i].append(self.html_convert(self.sender,message,"#888888","#888888",True))
                            self.get_list(self.chans[self.i])
                        self.i += 1

            if(self.message_id == 'MODE'):
                if(len(self.line) > 3):
                    self.chan = self.line[2].lower()
                    if(len(self.line) > 4):
                        self.victime = self.line[4]
                    else:
                        self.victime = None

                    self.index = self.get_index(self.chan)
                    self.sender = self.getNick(self.line[0])

                    if("+v" in self.line[3] or "-v" in self.line[3]):
                        self.get_list(self.chan)

                    if("+o" in self.line[3]):
                        message = " has given operator acces to "+self.victime
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#AA0000","#AA0000",True))
                        self.get_list(self.chan)

                    if("-o" in self.line[3]):
                        message = " has removed operator acces to "+self.victime
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#AA0000","#AA0000",True))
                        self.get_list(self.chan)

                    if("+h" in self.line[3]):
                        message = " has given half-operator acces to "+self.victime
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#AA0000","#AA0000",True))
                        self.get_list(self.chan)

                    if("-h" in self.line[3]):
                        message = " has removed half-operator acces to "+self.victime
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#AA0000","#AA0000",True))
                        self.get_list(self.chan)

                    if("+b" in self.line[3]):
                        message = " has banned "+self.victime
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#AA0000","#AA0000",True))
                        self.get_list(self.chan)

                    if("-b" in self.line[3]):
                        message = " has unbanned "+self.victime
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#AA0000","#AA0000",True))
                        self.get_list(self.chan)

            if(self.message_id == '433'): # Nick already in use
                self.status_messages.append(self.html_convert(None, "Error : Nickname already in use","#FF0000","#FF0000",True))
                self.stop()

            if(self.message_id == '432'): # Nick contain illegal caracteres
                self.status_messages.append(self.html_convert(None, "Error : Nickname contains illegal characters","#FF0000","#FF0000",True))
                self.stop()

            if(self.line[0] == 'ERROR'): # Nick contain illegal caracteres
                self.stop()

            if(self.message_id == "KICK"):
                if(len(self.line) > 3):
                    self.sender = self.getNick(self.line[0])
                    self.kicked = self.line[3]
                    self.chan = self.line[2].lower()
                    self.index = self.get_index(self.chan)
                    self.raison = self.getMsg(self.line,4)
                    self.chan_index = self.get_index(self.chanAutoJoin)

                    if(self.kicked.lower() == self.Nick.lower()):
                        if(self.chan == self.chanAutoJoin):
                            self.status_messages.append(self.html_convert(self.sender," has kicked you from the chat : "+self.raison,"#FF0000","#FF0000",True))
                            self.stop()
                        else :
                            self.messages[self.chan_index].append(self.html_convert(self.sender," has kicked you from "+self.chan+" : "+self.raison,"#FF0000","#FF0000",True))
                            self.leave_chan(self.chan)
                    else :
                        self.messages[self.index].append(self.html_convert(self.sender," has been kicked "+self.kicked+" from "+self.chan+" : "+self.raison,"#888888","#888888",True))
                    self.get_list(self.chan)

            if(self.message_id == 'QUIT'):
                self.sender = self.getNick(self.line[0])
                self.i = 0
                message = " has quit"
                while(self.i < len(self.chans)):
                    if(self.sender.lower() in self.filtrer_liste(self.names[self.i])):
                        self.messages[self.i].append(self.html_convert(self.sender,message,"#888888","#888888",True))
                        self.get_list(self.chans[self.i])
                    self.i += 1

            if(self.message_id == 'PRIVMSG' or self.message_id == 'NOTICE' and len(self.line) > 2):
                self.sender = self.getNick(self.line[0])
                if(self.line[2][0] == "#"):
                    self.window = self.line[2].lower()
                    if(self.Nick.lower() not in self.getMsg(self.line)):
                        self.generated_color = str(self.GenColor(self.sender)).replace("0x","")
                        self.color = "#"+self.generated_color[0]+self.generated_color[0]+self.generated_color[1]+self.generated_color[1]+self.generated_color[2]+self.generated_color[2]# Pseudo normal

                        self.message_color = "#000000"
                    else :
                        self.color = "#EE00EE"
                        self.message_color = "#EE00EE"
                        self.playsound()

                else:
                    if(self.sender.lower() != "playonlinux"):
                        self.color = "#AA0000"
                        self.message_color = "#000000"
                        self.window = self.sender.lower()
                        if(self.window != self.selected_window and not "." in self.window):
                            self.playsound()
                        self.old_window = self.selected_window
                        if(self.window not in self.chans):
                            self.chans.append(self.window)
                            self.endnames.append(False)
                            self.names.append([])
                            self.messages.append([])
                        if(self.old_window != ""):
                            self.select_window = self.old_window

                self.index = self.get_index(self.window)
                if("\x01ACTION" in self.getMsg(self.line)):
                    message = self.getMsg(self.line).replace("\x01","")
                    message = message[6:len(message)]
                    if(self.sender.lower() != "playonlinux"):
                        self.messages[self.index].append(self.html_convert(self.sender,message,"#000088","#000088",True))
                else :
                    message = self.getMsg(self.line)
                    if(self.sender.lower() != "playonlinux"):
                        self.messages[self.index].append(self.html_convert(self.sender,message,self.color,self.message_color))
                    else:
                        message_split = message.split(" ")
                        if(len(message_split) >= 2):
                            if(message_split[0] == "ALLOW"):
                                allowed_people.append(message_split[1])
                            elif(message_split[0] == "DENY"):
                                refused_people.append(message_split[1])

            #print self.names
    def run(self):
        self.ircconnected = False
        self.selected_window = self.chanAutoJoin
        self.names = []
        self.messages = []
        self.chans = []
        self.endnames = []
        self.select_window = ""
        self.status_messages = []
       # self.open_window = []
        while 1:
            if(self.ircconnected == True):
                #select([self.connexion], [], [])
                self.dataRecv = self.connexion.recv(1024)
                self.contentParse_ = string.split(self.dataRecv,"\r\n")
                self.k = 0
                while(self.k < len(self.contentParse_)):
                    if(self.contentParse_[self.k]):
                        self.traiter(self.contentParse_[self.k])
                    self.k += 1
            else:
                time.sleep(0.1)

    def Connexion(self):
        self.connect()

    def stop(self):
        if(self.ircconnected == True):
               # self.zone_append("<font color='#666666'>("+time.strftime("%H:%M:%S")+") Disconnected</font>")
            self.ircconnected = False
            self.status_messages.append(self.html_convert(None, "Disconnected","#AA0000","#AA0000",True))
            self.connexion.send("QUIT :www.playonlinux.com\r\n")
            self.connexion.close()
            self.names = []
            self.messages = []
            self.chans = []
            self.endnames = []

########NEW FILE########
__FILENAME__ = lng
#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
import wxversion
import gettext, Variables as Variables, os
import locale, string

class Lang(object):
    def __init__(self):
        return None

class iLang(object):
    def __init__(self):
        if(os.environ["DEBIAN_PACKAGE"] == "TRUE"):
            languages = os.listdir('/usr/share/locale')
        else:
            languages = os.listdir(Variables.playonlinux_env+'/lang/locale')

        langid = wx.LANGUAGE_DEFAULT
        if(os.environ["DEBIAN_PACKAGE"] == "TRUE"):
            localedir = "/usr/share/locale"
        else:
            localedir = os.path.join(Variables.playonlinux_env, "lang/locale")

        domain = "pol"
        mylocale = wx.Locale(langid)
        mylocale.AddCatalogLookupPathPrefix(localedir)
        mylocale.AddCatalog(domain)

        mytranslation = gettext.translation(domain, localedir, [mylocale.GetCanonicalName()], fallback = True)
        mytranslation.install()

########NEW FILE########
__FILENAME__ = playonlinux
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2007-2010 PlayOnLinux Team

import Variables, os, string
import shlex, pipes, wx

def winpath(script, path):
    #path=os.path.realpath(path)
    if(path[0] != "/"):
        path=os.environ["WorkingDirectory"]+"/"+path
    path = os.path.realpath(path)
    pref = getPrefix(script)
    ver = GetSettings('VERSION',pref)
    arch = GetSettings('ARCH',pref)
    if(arch == ""):
        arch="x86"
    if(ver == ""):
        return(os.popen("env WINEPREFIX='"+os.environ["POL_USER_ROOT"]+"/wineprefix/"+pref+"/' 'wine' winepath -w '"+path+"'").read().replace("\n","").replace("\r",""))
    else:
        return(os.popen("env WINEPREFIX='"+os.environ["POL_USER_ROOT"]+"/wineprefix/"+pref+"/' '"+os.environ["POL_USER_ROOT"]+"/wine/"+Variables.os_name+"-"+arch+"/"+ver+"/bin/wine' winepath -w '"+path+"'").read().replace("\n","").replace("\r",""))

def open_document(path, ext):
    script = GetSettings(ext, '_EXT_')
    if(script == ""):
        wx.MessageBox(_("There is nothing installed to run .{0} files.").format(ext),os.environ["APPLICATION_TITLE"], wx.OK)
    else:
        try:
            os.system("bash "+Variables.playonlinux_env+"/bash/run_app \""+script.encode("utf-8","replace")+"\" \""+winpath(script.encode("utf-8","replace"),path.encode("utf-8","replace"))+"\"&")
        except:
             os.system("bash "+Variables.playonlinux_env+"/bash/run_app \""+script+"\" \""+winpath(script,path)+"\"&")

def GetWineVersion(game):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    fichier = open(cfile,"r").readlines()
    i = 0
    line = ""
    while(i < len(fichier)):
        fichier[i] = fichier[i].replace("\n","")
        if("PATH=" in fichier[i] and "WineVersions" in fichier[i]):
            line = fichier[i].replace("//","/")
        i += 1

    if(line == ""):
        version = "System"
    else:
        version=line.replace("PATH=","").replace("\"","").replace(Variables.playonlinux_rep,"").replace("//","/")
        version = string.split(version,"/")
        version = version[1]

    return(version)

def GetSettings(setting, prefix='_POL_'):
    if(prefix == "_POL_"):
        cfile = Variables.playonlinux_rep+"/playonlinux.cfg"
    elif(prefix == "_EXT_"):
        cfile = Variables.playonlinux_rep+"/extensions.cfg"
    else:
        cfile = Variables.playonlinux_rep+"/wineprefix/"+prefix+"/playonlinux.cfg"

    try:
        fichier = open(cfile,"r").readlines()
    except:
        return("")

    i = 0
    line = ""
    while(i < len(fichier)):
        fichier[i] = fichier[i].replace("\n","")
        if(setting+"=" in fichier[i]):
            line = fichier[i]
            break
        i += 1
    try:
        line = string.split(line,"=")
        return(line[1])
    except:
        return("")

def SetSettings(setting, value, prefix='_POL_'):
    if(prefix == "_POL_"):
        cfile = Variables.playonlinux_rep+"/playonlinux.cfg"
    elif(prefix == "_EXT_"):
        cfile = Variables.playonlinux_rep+"/extensions.cfg"
    else:
        cfile = Variables.playonlinux_rep+"/wineprefix/"+prefix+"/playonlinux.cfg"

    try:
        fichier = open(cfile,"r").readlines()
    except:
        pass
    else:
        i = 0
        line = []
        found = False
        while(i < len(fichier)):
            fichier[i] = fichier[i].replace("\n","")
            if(setting+"=" in fichier[i]):
                line.append(setting+"="+value)
                found = True
            else:
                line.append(fichier[i])
            i += 1
        if(found == False):
            line.append(setting+"="+value)

        try:
            fichier_write = open(cfile,"w")
        except IOError:
            pass
        else:
            i = 0
            while(i < len(line)): # On ecrit
                fichier_write.write(line[i]+"\n")
                i+=1

def DeleteSettings(setting, prefix='_POL_'):
    if(prefix == "_POL_"):
        cfile = Variables.playonlinux_rep+"/playonlinux.cfg"
    elif(prefix == "_EXT_"):
        cfile = Variables.playonlinux_rep+"/extensions.cfg"
    else:
        cfile = Variables.playonlinux_rep+"/wineprefix/"+prefix+"/playonlinux.cfg"

    fichier = open(cfile,"r").readlines()
    i = 0
    line = []
    found = False
    while(i < len(fichier)):
        fichier[i] = fichier[i].replace("\n","")
        if(setting+"=" not in fichier[i]):
            line.append(fichier[i])
        i += 1

    fichier_write = open(cfile,"w")

    i = 0
    while(i < len(line)): # On ecrit
        fichier_write.write(line[i]+"\n")
        i+=1


def getLog(game):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    try:
        fichier = open(cfile,"r").readlines()
    except:
        return None

    for line in fichier:
        line = line.replace("\n","")
        if('#POL_Log=' in line):
            line = string.split(line,"=")
            return(line[1])
    return None

def GetDebugState(game):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    try:
        fichier = open(cfile,"r").readlines()
    except:
        return True

    for line in fichier:
        line = line.replace("\n","")
        if('export WINEDEBUG=' in line):
            if(line == 'export WINEDEBUG="-all"'):
                return False
            else:
                return True
    return False

def SetDebugState(game, prefix, state):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    try:
        fichier = open(cfile,"r").readlines()
    except:
        return False

    lines = []
    for line in fichier:
        line = line.replace("\n","")
        if('export WINEDEBUG=' in line):
            if(state == True):
                line = 'export WINEDEBUG="%s"' % GetSettings('WINEDEBUG', prefix)
            else:
                line = 'export WINEDEBUG="-all"'
        lines.append(line)

    fichier_write = open(cfile,"w")

    i = 0
    while(i < len(lines)): # On ecrit
        fichier_write.write(lines[i]+"\n")
        i+=1

def keynat(string):
    r'''A natural sort helper function for sort() and sorted()
    without using regular expressions or exceptions.

    >>> items = ('Z', 'a', '10th', '1st', '9')
    >>> sorted(items)
    ['10th', '1st', '9', 'Z', 'a']
    >>> sorted(items, key=keynat)
    ['1st', '9', '10th', 'a', 'Z']

    Borrowed from http://code.activestate.com/recipes/285264/#c6
    by paul clinch.

    License is the PSF Python License, http://www.python.org/psf/license/ (GPL compatible)
    '''
    it = type(1)
    r = []
    for c in string:
        if c.isdigit():
            d = int(c)
            if r and type( r[-1] ) == it:
                r[-1] = r[-1] * 10 + d
            else:
                r.append(d)
        else:
            r.append(c.lower())
    return r

def open_folder(software):
    read = open(Variables.playonlinux_rep+"shortcuts/"+software,"r").readlines()

    if not len(read):
        return

    i = 0;
    while(i < len(read)):
        if("cd \"" in read[i]):
            break
        i += 1

    if len(read) == (i):
        return

    AppDir = read[i][3:]
    if AppDir != "":
        if(os.environ["POL_OS"] == "Mac"):
            os.system("open "+AppDir)
        else:
            os.system("xdg-open "+AppDir)

def open_folder_prefix(software):
    AppDir = os.environ["POL_USER_ROOT"]+"/wineprefix/"+software
    if AppDir != "":
        if(os.environ["POL_OS"] == "Mac"):
            os.system("open "+AppDir)
        else:
            os.system("xdg-open "+AppDir)

def VersionLower(version1, version2):
    version1 = string.split(version1, "-")
    version2 = string.split(version2, "-")

    try:
        if(version1[1] != ""):
            dev1 = True
    except:
        dev1 = False

    try:
        if(version2[1] != ""):
            dev2 = True
    except:
        dev2 = False

    if(version1[0] == version2[0]):
        if(dev1 == True and dev2 == False):
            return True
        else:
            return False

    version1 = [ int(digit) for digit in string.split(version1[0],".") ]
    while len(version1) < 3:
        version1.append(0)

    version2 = [ int(digit) for digit in string.split(version2[0],".") ]
    while len(version2) < 3:
        version2.append(0)

    if(version1[0] < version2[0]):
        return True
    elif(version1[0] == version2[0]):
        if(version1[1] < version2[1]):
            return True
        elif(version1[1] == version2[1]):
            if(version1[2] < version2[2]):
                return True
            else:
                return False
        else:
            return False
    else:
        return False

def convertVersionToInt(version): # Code par MulX en Bash, adapte en python par Tinou
    #rajouter pour les vesions de dev -> la version stable peut sortir
    #les personnes qui utilise la version de dev sont quand même informé d'une MAJ
    #ex 3.8.1 < 3.8.2-dev < 3.8.2
    print "Deprecated !"
    if("dev" in version or "beta" in version or "alpha" in version or "rc" in version):
        version = string.split(version,"-")
        version = version[0]
        versionDev = -5
    else:
        versionDev = 0

    version_s = string.split(version,".")
    #on fait des maths partie1 elever au cube et multiplier par 1000
    try:
        versionP1 = int(version_s[0])*int(version_s[0])*int(version_s[0])*1000
    except:
        versionP1 = 0
    try:
        versionP2 = int(version_s[1])*int(version_s[1])*100
    except:
        versionP2 = 0
    try:
        versionP3 = int(version_s[2])*10
    except:
        versionP3 = 0
    return(versionDev + versionP1 + versionP2 + versionP3)

def getPrefix(shortcut): # Get prefix name from shortcut
    if(os.path.isdir(os.environ["POL_USER_ROOT"]+"/shortcuts/"+shortcut)):
        return ""

    fichier = open(os.environ["POL_USER_ROOT"]+"/shortcuts/"+shortcut,'r').read()
    fichier = string.split(fichier,"\n")
    i = 0
    while(i < len(fichier)):
        if("export WINEPREFIX=" in fichier[i]):
            break
        i += 1

    try:
        prefix = string.split(fichier[i],"\"")
        prefix = prefix[1].replace("//","/")
        prefix = string.split(prefix,"/")

        if(os.environ["POL_OS"] == "Mac"):
            index_of_dotPOL = prefix.index("PlayOnMac")
            prefix = prefix[index_of_dotPOL + 2]
        else:
            index_of_dotPOL = prefix.index(".PlayOnLinux")
            prefix = prefix[index_of_dotPOL + 2]
    except:
        prefix = ""

    return prefix


def getArgs(shortcut): # Get prefix name from shortcut
    if(os.path.isdir(os.environ["POL_USER_ROOT"]+"/shortcuts/"+shortcut)):
        return ""

    fichier = open(os.environ["POL_USER_ROOT"]+"/shortcuts/"+shortcut,'r').read()
    fichier = string.split(fichier,"\n")
    i = 0
    while(i < len(fichier)):
        if("POL_Wine " in fichier[i]):
            break
        i += 1

    try:
        args = shlex.split(fichier[i])[2:-1]
        #print args
        args = " ".join([ pipes.quote(x) for x in args])
        #print args
    except:
        args = ""

    return args

def Get_versions(arch='x86'):
    installed_versions = os.listdir(Variables.playonlinux_rep+"/wine/"+Variables.os_name+"-"+arch+"/")
    installed_versions.sort(key=keynat)
    installed_versions.reverse()
    try:
        installed_versions.remove("installed")
    except:
        pass
    return installed_versions

def Get_Drives():
    pref = os.listdir(Variables.playonlinux_rep+"/wineprefix/")
    pref.sort()
    return pref


def SetWinePrefix(game, prefix):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    fichier = open(cfile,"r").readlines()
    i = 0
    line = []
    while(i < len(fichier)): # On retire l'eventuel
        fichier[i] = fichier[i].replace("\n","")
        if("export WINEPREFIX=" not in fichier[i] or "/wineprefix/" not in fichier[i]):
            line.append(fichier[i])
        else:
            line.append("export WINEPREFIX=\""+Variables.playonlinux_rep+"/wineprefix/"+prefix+"\"")
        i += 1

    fichier_write = open(cfile,"w")

    i = 0
    while(i < len(line)): # On ecrit
        fichier_write.write(line[i]+"\n")
        i+=1


def writeArgs(game, args):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    fichier = open(cfile,"r").readlines()
    i = 0
    line = []

    while(i < len(fichier)): # On retire l'eventuel
        fichier[i] = fichier[i].replace("\n","")
        if("POL_Wine " not in fichier[i]):
            line.append(fichier[i])
        else:
            try:
                old_string = shlex.split(fichier[i])
                new_string = shlex.split(str(args))
                new_string = old_string[0:2] + new_string
                new_string = " ".join([ pipes.quote(x) for x in new_string])

                new_string = new_string+' "$@"'
                line.append(new_string)
            except:
                line.append(fichier[i])
        i += 1

    fichier_write = open(cfile,"w")
    i = 0
    while(i < len(line)): # On ecrit
        fichier_write.write(line[i]+"\n")
        i+=1

def POL_Open(arg):
    if(os.environ["POL_OS"] == "Mac"):
        os.system("open \""+arg+"\"&")
    else:
        os.system("xdg-open \""+arg+"\"&")

def POL_Error(message):
    wx.MessageBox(message,_("{0} error").format(os.environ["APPLICATION_TITLE"]))

########NEW FILE########
__FILENAME__ = Variables
#!/usr/bin/env python
# Copyright (C) 2007-2010 PlayOnLinux Team
# Copyright (C) 2011 - Quentin PARIS

import os, random, sys, string
import wx, lib.playonlinux as playonlinux

# Un ptit check
try :
    os.environ["POL_OS"]
except :
    print "ERROR ! Please define POL_OS environment var first."
    os._exit(1)

# Variables mixte 1
os.environ["POL_PORT"] = "0"
os.environ["PLAYONLINUX"] = os.path.realpath(os.path.realpath(__file__)+"/../../../")
os.environ["SITE"] = "http://repository.playonlinux.com"
os.environ["VERSION"] = "4.2.3-dev"
os.environ["POL_ID"] = str(random.randint(1,100000000))
os.environ["WINE_SITE"] = "http://www.playonlinux.com/wine/binaries"
os.environ["GECKO_SITE"] = "http://www.playonlinux.com/wine/gecko"
os.environ["MONO_SITE"] = "http://www.playonlinux.com/wine/mono"
homedir = os.environ["HOME"]

# Debian packagers should switch this to TRUE
# It will disable update alerts, bug reports, statistics
# It will set the good locale directory, and it will use the good msttcorefonts
os.environ["DEBIAN_PACKAGE"] = "FALSE"

# Variables PlayOnMac
if (os.environ["POL_OS"] == "Mac"):
    os.environ["PLAYONMAC"] = os.environ["PLAYONLINUX"]
    os.environ["REPERTOIRE"] = os.environ["HOME"]+"/Library/PlayOnMac/"
    os.environ["APPLICATION_TITLE"] = "PlayOnMac"
    os.environ["POL_DNS"] = "playonmac.com"
    windows_add_size = 20;
    windows_add_playonmac = 1;
    widget_borders = wx.SIMPLE_BORDER
    os_name = "darwin"
    os.environ["POL_WGET"] = "wget --prefer-family=IPv4 -q"

# Variables PlayOnLinux
if (os.environ["POL_OS"] == "Linux"):
    os.environ["REPERTOIRE"] = os.environ["HOME"]+"/.PlayOnLinux/"
    os.environ["APPLICATION_TITLE"] = "PlayOnLinux"
    os.environ["POL_DNS"] = "playonlinux.com"
    windows_add_size = 0;
    windows_add_playonmac = 0;
    widget_borders = wx.RAISED_BORDER
    os_name = "linux"
    if not os.path.exists("/proc/net/if_inet6"):
        os.environ["POL_WGET"] = "wget -q"
    else:
        os.environ["POL_WGET"] = "wget --prefer-family=IPv4 -q"

os.environ["POL_CURL"] = "curl"

archi = string.split(os.environ["MACHTYPE"],"-")
archi = archi[0]

if(archi == "x86_64" and os.environ["POL_OS"] == "Linux"):
    os.environ["AMD64_COMPATIBLE"] = "True"
else:
    os.environ["AMD64_COMPATIBLE"] = "False"

# Variables mixtes
os.environ["POL_USER_ROOT"] = os.environ["REPERTOIRE"]
os.environ["TITRE"] = os.environ["APPLICATION_TITLE"]
os.environ["WINEPREFIX"] = os.environ["REPERTOIRE"]+"/wineprefix/default"
os.environ["OS_NAME"] = os_name

# Wine
os.environ["WINEDLLOVERRIDES"] = "winemenubuilder.exe=d"

# Si DYLD_LIBRARY_PATH n'existe pas, on la defini pour etre sur
try :
    os.environ["DYLD_LIBRARY_PATH"]
except:
    os.environ["DYLD_LIBRARY_PATH"] = ""

# Pareil pour LD
try :
    os.environ["LD_LIBRARY_PATH"]
except:
    os.environ["LD_LIBRARY_PATH"] = ""




if (os.environ["POL_OS"] == "Mac"):
    os.environ["MAGICK_HOME"] = os.environ["PLAYONLINUX"]+"/../unix/image_magick/"

    os.environ["PATH"] = os.environ["PLAYONLINUX"]+"/../unix/wine/bin:" + os.environ["PLAYONLINUX"]+"/../unix/image_magick/bin:" + os.environ["PLAYONLINUX"]+"/../unix/tools/bin/:" + os.environ["PATH"]

    os.environ["LD_LIBRARY_PATH"] =  os.environ["PLAYONLINUX"]+"/../unix/wine/lib/:"  + os.environ["PLAYONLINUX"]+"/../unix/image_magick/lib:"+ os.environ["PLAYONLINUX"]+"/../unix/tools/lib/ld:/usr/X11/lib/:" + os.environ["LD_LIBRARY_PATH"]

    os.environ["DYLD_LIBRARY_PATH"] = os.environ["PLAYONLINUX"]+"/../unix/tools/lib/dyld:" + os.environ["PLAYONLINUX"]+"/../unix/image_magick/lib:"+ os.environ["DYLD_LIBRARY_PATH"]
else:
    # Debian maintainer decided for some reason not to let wineserver binary into PATH...
    for winepath in ('/usr/lib/i386-linux-gnu/wine/bin', '/usr/lib/i386-linux-gnu/wine-unstable/bin', \
                     '/usr/lib32/wine', '/usr/lib32/wine-unstable', \
                     '/usr/lib/wine', '/usr/lib/wine-unstable'):
        if os.path.exists('%s/wineserver' % (winepath,)):
            os.environ["PATH"] += ':%s' % (winepath,)
            break

os.environ["PATH_ORIGIN"] = os.environ["PATH"]
os.environ["LD_PATH_ORIGIN"] = os.environ["LD_LIBRARY_PATH"]
os.environ["DYLDPATH_ORIGIN"] = os.environ["DYLD_LIBRARY_PATH"]

playonlinux_env = os.environ["PLAYONLINUX"]
playonlinux_rep = os.environ["REPERTOIRE"]
version = os.environ["VERSION"]
current_user = os.environ["USER"]

os.environ["WGETRC"] = os.environ["POL_USER_ROOT"]+"/configurations/wgetrc"

## Proxy settings
if(playonlinux.GetSettings("PROXY_ENABLED") == "1"):
    if(playonlinux.GetSettings("PROXY_URL") != ""):
        if(playonlinux.GetSettings("PROXY_LOGIN") == ""):
            http_proxy = "http://"+playonlinux.GetSettings("PROXY_URL")+":"+playonlinux.GetSettings("PROXY_PORT")
        else:
            http_proxy = "http://"+playonlinux.GetSettings("PROXY_LOGIN")+":"+playonlinux.GetSettings("PROXY_PASSWORD")+"@"+playonlinux.GetSettings("PROXY_URL")+":"+playonlinux.GetSettings("PROXY_PORT")
        os.environ["http_proxy"] = http_proxy

########NEW FILE########
__FILENAME__ = wine
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2007-2010 PlayOnLinux Team

import Variables, os, string


def LoadRegValues(prefix, values):
    cfile = Variables.playonlinux_rep+"wineprefix/"+prefix+"/user.reg"
    result = {}


    for element in values:
        result[element] = "default"

    try:
        fichier = open(cfile,"r").readlines()
    except:
        return result

    for line in fichier:
        line = line.replace("\n","")
        found = False
        for element in values:
            if(element in line):
                line = line.replace("\"","")
                line = string.split(line, "=")
                line = line[1]
                result[element] = line
                found = True
                break
            #if(found == False):
            #result[element] = "default"
    return(result)

########NEW FILE########
__FILENAME__ = mainwindow
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2008 Pâris Quentin
# Copyright (C) 2007-2057 PlayOnLinux team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
encoding = 'utf-8'

import os, getopt, sys, urllib, signal, string, time, webbrowser, gettext, locale, sys, shutil, subprocess

try :
    os.environ["POL_OS"]
except :
    print "ERROR ! Please define POL_OS environment var first."
    os._exit(1)

if(os.environ["POL_OS"] == "Linux"):
    import wxversion
    wxversion.ensureMinimal('2.8')

import wx, wx.aui
import lib.lng as lng
import lib.playonlinux as playonlinux, lib.Variables as Variables
import guiv3 as gui, install, options, wine_versions as wver, sp, configure, threading, debug, gui_server
import irc as ircgui

# This thread manage updates
class POLWeb(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.sendToStatusBarStr = ""
        self.sendAlertStr = None
        self.Gauge = False
        self.WebVersion = ""
        self.Show = False
        self.perc = -1
        self.updating = True
    def sendToStatusBar(self, message, gauge):
        self.sendToStatusBarStr = message
        self.Gauge = gauge
        self.Show = True

    def sendPercentage(self, n):
        self.perc = n

    def sendAlert(self, message):
        self.sendAlertStr = message

    def LastVersion(self):
        if(os.environ["POL_OS"] == "Mac"):
            fichier_online="version_mac"
        else:
            fichier_online="version2"
        return os.popen(os.environ["POL_WGET"]+' "'+os.environ["SITE"]+'/'+fichier_online+'.php?v='+os.environ["VERSION"]+'" -T 30 -O-','r').read()

    def real_check(self):
        self.WebVersion = self.LastVersion()

        if(self.WebVersion == ""):
            self.sendToStatusBar(_('{0} website is unavailable. Please check your connection').format(os.environ["APPLICATION_TITLE"]), False)
        else:
            self.sendToStatusBar(_("Refreshing {0}").format(os.environ["APPLICATION_TITLE"]), True)
            self.sendPercentage(0)
            self.updating = True
            exe = ['bash',Variables.playonlinux_env+"/bash/pol_update_list"]

            p = subprocess.Popen(exe, stdout=subprocess.PIPE, bufsize=1, preexec_fn=lambda: os.setpgid(os.getpid(), os.getpid()))

            for line in iter(p.stdout.readline, ''):
                try:
                    self.sendPercentage(int(line))
                except ValueError:
                    pass
  
            self.updating = False
            if(playonlinux.VersionLower(os.environ["VERSION"],self.WebVersion)):
                self.sendToStatusBar(_('An updated version of {0} is available').format(os.environ["APPLICATION_TITLE"])+" ("+self.WebVersion+")",False)
                if(os.environ["DEBIAN_PACKAGE"] == "FALSE"):
                    self.sendAlert(_('An updated version of {0} is available').format(os.environ["APPLICATION_TITLE"])+" ("+self.WebVersion+")")
                os.environ["POL_UPTODATE"] = "FALSE"
            else:
                self.Show = False
                self.perc = -1
                os.environ["POL_UPTODATE"] = "TRUE"

        self.wantcheck = False

    def check(self):
        self.wantcheck = True

    def run(self):
        self.check()
        while(1):
            if(self.wantcheck == True):
                self.real_check()
            time.sleep(1)

class MainWindow(wx.Frame):
    def __init__(self,parent,id,title):

        wx.Frame.__init__(self, parent, 1000, title, size = (515,450))
        self.SetMinSize((400,400))
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))

        self.windowList = {}
        self.registeredPid = []
        self.windowOpened = 0

        # Manage updater
        self.updater = POLWeb()
        self.updater.start()

        # These lists contain the dock links and images 
        self.menuElem = {}
        self.menuImage = {}

        # Catch CTRL+C
        signal.signal(signal.SIGINT, self.ForceClose)

        # Window size
        try:
            self.windowWidth = int(playonlinux.GetSettings("MAINWINDOW_WIDTH"))
            self.windowHeight = int(playonlinux.GetSettings("MAINWINDOW_HEIGHT"))
            self.SetSize((self.windowWidth,self.windowHeight))
        except:
            self.windowWidth = 450
            self.windowHeight = 450

        # Window position
        try:
            self.windowx = int(playonlinux.GetSettings("MAINWINDOW_X"))
            self.windowy = int(playonlinux.GetSettings("MAINWINDOW_Y"))
            self.screen_width = wx.Display().GetGeometry()[2]
            self.screen_height = wx.Display().GetGeometry()[3]

            if(self.screen_width >= self.windowx and self.screen_height >= self.windowy):
                self.SetPosition((self.windowx, self.windowy))
            else:
                self.Center(wx.BOTH)
        except:
            self.Center(wx.BOTH)


        try: self.iconSize = int(playonlinux.GetSettings("ICON_SIZE"))
        except: self.iconSize = 32

        self.images = wx.ImageList(self.iconSize, self.iconSize)
        self.imagesEmpty = wx.ImageList(1,1)


        self.sendAlertStr = None

        ## Fonts
        if(os.environ["POL_OS"] == "Mac"):
            self.fontTitre = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.fontText = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)
        else :
            self.fontTitre = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.fontText = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)


        ## List game
        self.list_game = wx.TreeCtrl(self, 105, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT)
        self.list_game.SetSpacing(0);
        self.list_game.SetIndent(5);
        self.list_game.SetImageList(self.images)

        self._mgr = wx.aui.AuiManager(self)
        self.menu_gauche = wx.Panel(self,-1)



        self._mgr.AddPane(self.list_game, wx.CENTER)


        self.filemenu = wx.Menu()
        ### On MacOS X, preference is always on the main menu
        if(os.environ["POL_OS"] == "Mac"):
            prefItem = self.filemenu.Append(wx.ID_PREFERENCES, text = "&Preferences")
            self.Bind(wx.EVT_MENU, self.Options, prefItem)

        ### File menu
        self.filemenu.Append(wx.ID_OPEN, _("Run"))
        self.filemenu.Append(wx.ID_ADD, _("Install"))
        self.filemenu.Append(wx.ID_DELETE, _("Remove"))
        self.filemenu.AppendSeparator()
        self.filemenu.Append(216, _("Donate"))
        self.filemenu.Append(wx.ID_EXIT, _("Exit"))

        ### Display menu
        self.displaymenu = wx.Menu()
        self.icon16 = self.displaymenu.AppendRadioItem(501, _("Small icons"))
        self.icon24 = self.displaymenu.AppendRadioItem(502, _("Medium icons"))
        self.icon32 = self.displaymenu.AppendRadioItem(503, _("Large icons"))
        self.icon48 = self.displaymenu.AppendRadioItem(504, _("Very large icons"))
        if(self.iconSize == 16):
            self.icon16.Check(True)
        if(self.iconSize == 24):
            self.icon24.Check(True)
        if(self.iconSize == 32):
            self.icon32.Check(True)
        if(self.iconSize == 48):
            self.icon48.Check(True)

        self.expertmenu = wx.Menu()

        self.winever_item = wx.MenuItem(self.expertmenu, 107, _("Manage Wine versions"))
        self.winever_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/wine.png"))
        self.expertmenu.AppendItem(self.winever_item)

        if(os.environ["POL_OS"] == "Mac"):
            self.expertmenu.AppendSeparator()
            self.pccd_item = wx.MenuItem(self.expertmenu, 113, _("Read a PC CD-Rom"))
            self.pccd_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/cdrom.png"))
            self.expertmenu.AppendItem(self.pccd_item)

        self.expertmenu.AppendSeparator()

        self.run_item = wx.MenuItem(self.expertmenu, 108, _("Run a local script"))
        self.run_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/run.png"))
        self.expertmenu.AppendItem(self.run_item)

        self.wineserv_item = wx.MenuItem(self.expertmenu, 115, _('Close all {0} software').format(os.environ["APPLICATION_TITLE"]))
        self.wineserv_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/wineserver.png"))
        self.expertmenu.AppendItem(self.wineserv_item)

        self.polshell_item = wx.MenuItem(self.expertmenu, 109, _('{0} console').format(os.environ["APPLICATION_TITLE"]))
        self.polshell_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/polshell.png"))
        self.expertmenu.AppendItem(self.polshell_item)

        self.expertmenu.AppendSeparator()

        self.pol_online = wx.MenuItem(self.expertmenu, 112, os.environ["APPLICATION_TITLE"]+" online")
        self.pol_online.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/playonlinux_online.png"))
        self.expertmenu.AppendItem(self.pol_online)

        self.chat_item = wx.MenuItem(self.expertmenu, 111, _("{0} messenger").format(os.environ["APPLICATION_TITLE"]))
        self.chat_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/people.png"))
        self.expertmenu.AppendItem(self.chat_item)

        self.bug_item = wx.MenuItem(self.expertmenu, 110, _("{0} debugger").format(os.environ["APPLICATION_TITLE"]))
        self.bug_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/bug.png"))
        self.expertmenu.AppendItem(self.bug_item)


        self.optionmenu = wx.Menu()


        self.option_item = wx.MenuItem(self.expertmenu, 211, _("Internet"))
        self.option_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/internet-web-browser.png"))
        self.optionmenu.AppendItem(self.option_item)

        self.option_item = wx.MenuItem(self.expertmenu, 212, _("File associations"))
        self.option_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/extensions.png"))
        self.optionmenu.AppendItem(self.option_item)



        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_ABOUT, _('About {0}').format(os.environ["APPLICATION_TITLE"]))
        self.pluginsmenu = wx.Menu()

        files=os.listdir(Variables.playonlinux_rep+"/plugins")
        files.sort()
        self.plugin_list = []
        self.i = 0
        self.j = 0
        while(self.i < len(files)):
            if(os.path.exists(Variables.playonlinux_rep+"/plugins/"+files[self.i]+"/scripts/menu")):
                if(os.path.exists(Variables.playonlinux_rep+"/plugins/"+files[self.i]+"/enabled")):
                    self.plugin_item = wx.MenuItem(self.expertmenu, 300+self.j, files[self.i])

                    self.icon_look_for = Variables.playonlinux_rep+"/plugins/"+files[self.i]+"/icon"
                    if(os.path.exists(self.icon_look_for)):
                        self.bitmap = wx.Bitmap(self.icon_look_for)
                    else:
                        self.bitmap = wx.Bitmap(Variables.playonlinux_env+"/etc/playonlinux16.png")

                    self.plugin_item.SetBitmap(self.bitmap)
                    self.pluginsmenu.AppendItem(self.plugin_item)
                    wx.EVT_MENU(self, 300+self.j,  self.run_plugin)
                    self.plugin_list.append(files[self.i])
                    self.j += 1
            self.i += 1

        if(self.j > 0):
            self.pluginsmenu.AppendSeparator()

        self.option_item_p = wx.MenuItem(self.expertmenu, 214, _("Plugin manager"))
        self.option_item_p.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/package-x-generic.png"))
        self.pluginsmenu.AppendItem(self.option_item_p)

        self.option_item = wx.MenuItem(self.expertmenu, 214, _("Plugin manager"))
        self.option_item.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/package-x-generic.png"))
        self.optionmenu.AppendItem(self.option_item)


        self.last_string = ""

        self.sb = wx.StatusBar(self, -1 )
        self.sb.SetFieldsCount(2)
        self.sb.SetStatusWidths([self.GetSize()[0], -1])
        self.sb.SetStatusText("", 0)

        if(os.environ["POL_OS"] == "Mac"):
            hauteur = 2;
        else:
            hauteur = 6;
        self.jauge_update = wx.Gauge(self.sb, -1, 100, (self.GetSize()[0]-100, hauteur), size=(100,16))
        self.jauge_update.Pulse()
        self.jauge_update.Hide()
        self.SetStatusBar(self.sb)

        #self.helpmenu = wx.MenuItem()
        #self.helpmenu.Append(wx.ID_ABOUT, _("About"))

        self.menubar = wx.MenuBar()
        self.menubar.Append(self.filemenu, _("File"))
        self.menubar.Append(self.displaymenu, _("Display"))
        self.menubar.Append(self.expertmenu, _("Tools"))
        self.menubar.Append(self.optionmenu, _("Settings"))
        self.menubar.Append(self.pluginsmenu, _("Plugins"))
        self.menubar.Append(self.help_menu, "&Help")

        #self.menubar.Append(self.help_menu, _("About"))
        
        self.SetMenuBar(self.menubar)
        iconSize = (32,32)

        self.toolbar = self.CreateToolBar(wx.TB_TEXT)
        self.toolbar.SetToolBitmapSize(iconSize)
        self.searchbox = wx.SearchCtrl( self.toolbar, 124, style=wx.RAISED_BORDER )
        self.playTool = self.toolbar.AddLabelTool(wx.ID_OPEN, _("Run"), wx.Bitmap(Variables.playonlinux_env+"/resources/images/toolbar/play.png"))
        self.stopTool = self.toolbar.AddLabelTool(123, _("Close"), wx.Bitmap(Variables.playonlinux_env+"/resources/images/toolbar/stop.png"))

        self.toolbar.AddSeparator()
        self.toolbar.AddLabelTool(wx.ID_ADD, _("Install"), wx.Bitmap(Variables.playonlinux_env+"/resources/images/toolbar/install.png"))
        self.removeTool = self.toolbar_remove = self.toolbar.AddLabelTool(wx.ID_DELETE, _("Remove"), wx.Bitmap(Variables.playonlinux_env+"/resources/images/toolbar/delete.png"))
        self.toolbar.AddSeparator()
        self.toolbar.AddLabelTool(121, _("Configure"), wx.Bitmap(Variables.playonlinux_env+"/resources/images/toolbar/configure.png"))

        try: 
                self.toolbar.AddStretchableSpace()
                self.SpaceHack = False
        except:
                # wxpython 2.8 does not support AddStretchableSpace(). This is a dirty workaround for this.
                self.dirtyHack = wx.StaticText(self.toolbar)
                self.SpaceHack = True
                self.toolbar.AddControl( self.dirtyHack ) 
                self.UpdateSearchHackSize()

        try:
                self.toolbar.AddControl( self.searchbox , _("Search")) 
        except:
                self.toolbar.AddControl( self.searchbox ) 
                self.searchbox.SetDescriptiveText(_("Search"))


        self.toolbar.Realize()
        self.Reload(self)
        wx.EVT_MENU(self, wx.ID_OPEN,  self.Run)
        wx.EVT_MENU(self, 123,  self.RKill)

        wx.EVT_MENU(self, wx.ID_ADD,  self.InstallMenu)
        wx.EVT_MENU(self, wx.ID_ABOUT,  self.About)
        wx.EVT_MENU(self,  wx.ID_EXIT,  self.ClosePol)
        wx.EVT_MENU(self,  wx.ID_DELETE,  self.UninstallGame)

        # Display
        wx.EVT_MENU(self, 501,  self.iconDisplay)
        wx.EVT_MENU(self, 502,  self.iconDisplay)
        wx.EVT_MENU(self, 503,  self.iconDisplay)
        wx.EVT_MENU(self, 504,  self.iconDisplay)
        wx.EVT_MENU(self, 505,  self.displayMen)

        # Expert
        wx.EVT_MENU(self, 101,  self.Reload)
        wx.EVT_MENU(self, 107,  self.WineVersion)
        wx.EVT_MENU(self, 108,  self.Executer)
        wx.EVT_MENU(self, 109,  self.PolShell)
        wx.EVT_MENU(self, 110,  self.BugReport)
        wx.EVT_MENU(self, 111,  self.OpenIrc)
        wx.EVT_MENU(self, 112,  self.POLOnline)
        wx.EVT_MENU(self, 113,  self.PCCd)
        wx.EVT_MENU(self, 115,  self.killall)
        wx.EVT_MENU(self, 121,  self.Configure)
        wx.EVT_MENU(self, 122,  self.Package)
        wx.EVT_TEXT(self, 124,  self.Reload)

        #Options
        wx.EVT_MENU(self, 210,  self.Options)
        wx.EVT_MENU(self, 211,  self.Options)
        wx.EVT_MENU(self, 212,  self.Options)
        wx.EVT_MENU(self, 213,  self.Options)
        wx.EVT_MENU(self, 214,  self.Options)
        wx.EVT_MENU(self, 215,  self.Options)

        wx.EVT_MENU(self, 216,  self.donate)

        wx.EVT_CLOSE(self, self.ClosePol)
        wx.EVT_TREE_ITEM_ACTIVATED(self, 105, self.Run)
        wx.EVT_TREE_SEL_CHANGED(self, 105, self.Select)


        # PlayOnLinux main timer
        self.timer = wx.Timer(self, 1)
        self.Bind(wx.EVT_TIMER, self.TimerAction, self.timer)
        self.timer.Start(1000)
        self.Timer_LastShortcutList = None
        self.Timer_LastIconList = None
  
        # SetupWindow timer. The server is in another thread and GUI must be run from the main thread
        self.SetupWindowTimer = wx.Timer(self, 2)
        self.Bind(wx.EVT_TIMER, self.SetupWindowAction, self.SetupWindowTimer)
        self.SetupWindowTimer_action = None
        self.SetupWindowTimer.Start(100)
        self.SetupWindowTimer_delay = 100

        #Pop-up menu for game list: beginning
        wx.EVT_TREE_ITEM_MENU(self, 105, self.RMBInGameList)
        wx.EVT_MENU(self, 230, self.RWineConfigurator)
        wx.EVT_MENU(self, 231, self.RRegistryEditor)
        wx.EVT_MENU(self, 232, self.GoToAppDir)
        wx.EVT_MENU(self, 233, self.ChangeIcon)
        wx.EVT_MENU(self, 234, self.UninstallGame)
        wx.EVT_MENU(self, 235, self.RKill)
        wx.EVT_MENU(self, 236, self.ReadMe)
        self.Bind(wx.EVT_SIZE, self.ResizeWindow)

        self.MgrAddPage()

    def ResizeWindow(self, e):
        self.UpdateGaugePos()
        self.UpdateSearchHackSize()
       
    def UpdateSearchHackSize(self):
        if(self.SpaceHack == True):
            self.dirtyHack.SetLabel("")
            self.dirtyHack.SetSize((50,1))

    def UpdateGaugePos(self):
        if(os.environ["POL_OS"] == "Mac"):
            hauteur = 2;
        else:
            hauteur = 6;
        self.jauge_update.SetPosition((self.GetSize()[0]-100, hauteur))

    def SetupWindowTimer_SendToGui(self, recvData):
        recvData = recvData.split("\t")
        while(self.SetupWindowTimer_action != None):
            time.sleep(0.1)
        self.SetupWindowTimer_action = recvData
        
    def SetupWindow_TimerRestart(self, time):
        if(time != self.SetupWindowTimer_delay):
            self.SetupWindowTimer.Stop()
            self.SetupWindowTimer.Start(time)
            self.SetupWindowTimer_delay = time

    def SetupWindowAction(self, event):
        
        if(self.windowOpened == 0):
            self.SetupWindow_TimerRestart(100)
        else:
            self.SetupWindow_TimerRestart(10)

        if(self.SetupWindowTimer_action != None):                           
            return gui_server.readAction(self)
            
           
    def TimerAction(self, event):
        self.StatusRead()
        
        # We read shortcut folder to see if it has to be rescanned
        currentShortcuts = os.path.getmtime(Variables.playonlinux_rep+"/shortcuts")
        currentIcons = os.path.getmtime(Variables.playonlinux_rep+"/icones/32")
        if(currentShortcuts != self.Timer_LastShortcutList or currentIcons != self.Timer_LastIconList):
            self.Reload(self)
            self.Timer_LastShortcutList = currentShortcuts
            self.Timer_LastIconList = currentIcons
            
    def MgrAddPage(self):
        try:
            self.LoadSize = int(playonlinux.GetSettings("PANEL_SIZE"))
        except:
            self.LoadSize = 150

        try:
            self.LoadPosition = playonlinux.GetSettings("PANEL_POSITION")
        except:
            self.LoadPosition = "LEFT"

        if(self.LoadSize < 20):
            self.LoadSize = 20
        if(self.LoadSize > 1000):
            self.LoadSize = 1000


        if(self.LoadPosition == "LEFT"):
            self._mgr.AddPane(self.menu_gauche, wx.aui.AuiPaneInfo().Name('Actions').Caption('Actions').Left().BestSize((self.LoadSize,400)).Floatable(True).CloseButton(False).TopDockable(False).BottomDockable(False))
        else:
            self._mgr.AddPane(self.menu_gauche, wx.aui.AuiPaneInfo().Name('Actions').Caption('Actions').Right().BestSize((self.LoadSize,400)).Floatable(True).CloseButton(False).TopDockable(False).BottomDockable(False))
        self.menu_gauche.Show()

        self._mgr.Update()

    def displayMen(self, event):
        playonlinux.SetSettings("PANEL_POSITION","LEFT")
        if(self.panDisplay.IsChecked()):
            self.MgrAddPage()

    def StatusRead(self):
        self.sb.SetStatusText(self.updater.sendToStatusBarStr, 0)
        if(self.updater.Gauge == True):
            perc = self.updater.perc
            if(perc == -1):
                self.jauge_update.Pulse()
            else:
                try:
                    self.installFrame.percentageText.SetLabel(str(perc)+" %")
                except:
                    pass
                self.jauge_update.SetValue(perc)
            self.jauge_update.Show()
        else:
            self.jauge_update.Hide()

        if(self.updater.updating == True):
            self.sb.Show()
            try:
                self.installFrame.panelItems.Hide()
                self.installFrame.panelManual.Hide()
                self.installFrame.panelWait.Show()
                try:
                    if(self.playing == False):
                        self.installFrame.animation_wait.Play()
                        self.playing = True
                except:
                    self.playing = False
            except:
                pass
        else:
            self.sb.Hide()
            try:
                if(self.installFrame.currentPanel == 1):
                    self.installFrame.panelManual.Show()
                else:
                    self.installFrame.panelItems.Show()
                self.installFrame.panelWait.Hide()
                self.installFrame.animation_wait.Stop()
                self.playing = False
                self.installFrame.Refresh()
            except:
                pass
                
        if(self.updater.sendAlertStr != self.sendAlertStr):
            wx.MessageBox(self.updater.sendAlertStr, os.environ["APPLICATION_TITLE"])
            self.sendAlertStr = self.updater.sendAlertStr

    def RMBInGameList(self, event):
        self.GameListPopUpMenu = wx.Menu()

        self.ConfigureWine = wx.MenuItem(self.GameListPopUpMenu, 230, _("Configure Wine"))
        self.ConfigureWine.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/run.png"))
        self.GameListPopUpMenu.AppendItem(self.ConfigureWine)

        self.RegistryEditor = wx.MenuItem(self.GameListPopUpMenu, 231, _("Registry Editor"))
        self.RegistryEditor.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/regedit.png"))
        self.GameListPopUpMenu.AppendItem(self.RegistryEditor)

        self.GotoAppDir = wx.MenuItem(self.GameListPopUpMenu, 232, _("Open the application's directory"))
        self.GotoAppDir.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/folder-wine.png"))
        self.GameListPopUpMenu.AppendItem(self.GotoAppDir)

        self.ChangeIcon = wx.MenuItem(self.GameListPopUpMenu, 236, _("Read the manual"))
        self.ChangeIcon.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/manual.png"))
        self.GameListPopUpMenu.AppendItem(self.ChangeIcon)

        self.ChangeIcon = wx.MenuItem(self.GameListPopUpMenu, 233, _("Set the icon"))
        self.ChangeIcon.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/change_icon.png"))
        self.GameListPopUpMenu.AppendItem(self.ChangeIcon)

        self.ChangeIcon = wx.MenuItem(self.GameListPopUpMenu, 234, _("Remove"))
        self.ChangeIcon.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/delete.png"))
        self.GameListPopUpMenu.AppendItem(self.ChangeIcon)

        self.ChangeIcon = wx.MenuItem(self.GameListPopUpMenu, 235, _("Close this application"))
        self.ChangeIcon.SetBitmap(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/media-playback-stop.png"))
        self.GameListPopUpMenu.AppendItem(self.ChangeIcon)

        self.PopupMenu(self.GameListPopUpMenu, event.GetPoint())


    def RWineConfigurator(self, event):
        self.RConfigure(_("Configure Wine"), "nothing")

    def RKill(self, event):
        self.RConfigure(_("KillApp"), "nothing")

    def ReadMe(self, event):
        game_exec = self.GetSelectedProgram()
        if(os.path.exists(os.environ["POL_USER_ROOT"]+"/configurations/manuals/"+game_exec)):
            playonlinux.POL_Open(os.environ["POL_USER_ROOT"]+"/configurations/manuals/"+game_exec)
        else:
            wx.MessageBox(_("No manual found for {0}").format(game_exec), os.environ["APPLICATION_TITLE"])

    def RRegistryEditor(self, event):
        self.RConfigure(_("Registry Editor"), "nothing")

    def run_plugin(self, event):
        game_exec = self.GetSelectedProgram()
        plugin=self.plugin_list[event.GetId()-300]
        try :
            subprocess.Popen(["bash", Variables.playonlinux_rep+"/plugins/"+plugin+"/scripts/menu", game_exec])
        except :
            pass

    def iconDisplay(self, event):
        iconEvent=event.GetId()

        if(iconEvent == 501):
            self.iconSize = 16
        if(iconEvent == 502):
            self.iconSize = 24
        if(iconEvent == 503):
            self.iconSize = 32
        if(iconEvent == 504):
            self.iconSize = 48

        playonlinux.SetSettings("ICON_SIZE",str(self.iconSize))
        self.list_game.SetImageList(self.imagesEmpty)
        self.images.Destroy()
        self.images = wx.ImageList(self.iconSize, self.iconSize)
        self.list_game.SetImageList(self.images)


        self.Reload(self)

    def OpenIrc(self, event):
        self.irc = ircgui.IrcClient(self)
        self.irc.Center(wx.BOTH)
        self.irc.Show(True)

    def UpdateInstructions(self, event):
        if(os.environ["POL_OS"] == "Mac"):
            webbrowser.open("http://www.playonmac.com/en/download.html")
        else:
            webbrowser.open("http://www.playonlinux.com/en/download.html")

    def UpdateGIT(self, event):
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/update_git"])


    def GoToAppDir(self, event):
        self.game_exec = self.GetSelectedProgram()
        playonlinux.open_folder(self.game_exec)

    def ChangeIcon(self, event):
        self.IconDir = Variables.homedir+"/.local/share/icons/"
        self.SupprotedIconExt = "All|*.xpm;*.XPM;*.png;*.PNG;*.ico;*.ICO;*.jpg;*.JPG;*.jpeg;*.JPEG;*.bmp;*.BMP\
        \|XPM (*.xpm)|*.xpm;*.XPM\
        \|PNG (*.png)|*.png;*.PNG\
        \|ICO (*.ico)|*.ico;*.ICO\
        \|JPG (*.jpg)|*.jpg;*.JPG\
        \|BMP (*.bmp)|*.bmp;*.BMP\
        \|JPEG (*.jpeg)|*.jpeg;*JPEG"
        self.IconDialog = wx.FileDialog(self, "Choose a icon file", self.IconDir, "", self.SupprotedIconExt, wx.OPEN | wx.FD_PREVIEW)
        if self.IconDialog.ShowModal() == wx.ID_OK:
            self.IconFilename=self.IconDialog.GetFilename()
            self.IconDirname=self.IconDialog.GetDirectory()
            IconFile=os.path.join(self.IconDirname,self.IconFilename)
            self.RConfigure("IconChange", IconFile)
            self.IconDialog.Destroy()
            #Pop-up menu for game list: ending

    def Select(self, event):
        game_exec = self.GetSelectedProgram()
        self.read = open(Variables.playonlinux_rep+"shortcuts/"+game_exec,"r").readlines()
        self.i = 0;
        self.wine_present = False;
        while(self.i < len(self.read)):
            if("wine " in self.read[self.i]):
                self.wine_present = True;
            self.i += 1

        self.generate_menu(game_exec)
        self.playTool.Enable(True)
        self.stopTool.Enable(True)
        self.removeTool.Enable(True)

    def generate_menu(self, shortcut=None):
        for c in self.menuElem:
            self.menuElem[c].Destroy()

        for c in self.menuImage:
            self.menuImage[c].Destroy()
        try:
            self.menuBitmap.Destroy()
        except:
            pass

        self.menuElem = {}
        self.menuImage = {}

        i = 0;
        self.menuGaucheAddTitle("pol_title", os.environ["APPLICATION_TITLE"], i)
        i+=1
        self.menuGaucheAddLink("pol_prgm_install", _("Install a program"), i,Variables.playonlinux_env+"/resources/images/menu/add.png",self.InstallMenu)
        i+=1
        self.menuGaucheAddLink("pol_prgm_settings", _("Settings"), i,Variables.playonlinux_env+"/resources/images/menu/settings.png",self.Options)
        i+=1
        self.menuGaucheAddLink("pol_prgm_messenger", _("Messenger"), i,Variables.playonlinux_env+"/resources/images/menu/people.png",self.OpenIrc)
        if(os.path.exists(os.environ["PLAYONLINUX"]+"/.git/")):
            i+=1
            self.menuGaucheAddLink("pol_git", _("Update GIT"), i,Variables.playonlinux_env+"/resources/images/menu/update_git.png",self.UpdateGIT)
        elif "POL_UPTODATE" in os.environ and os.environ["POL_UPTODATE"] == "FALSE":
            i+=1
            self.menuGaucheAddLink("pol_update", _("Update instructions"), i,Variables.playonlinux_env+"/resources/images/menu/update_git.png",self.UpdateInstructions)

        if(shortcut != None):
            i+=2
            self.menuGaucheAddTitle("prgm_title", shortcut, i)
            i+=1
            self.menuGaucheAddLink("pol_prgm_run", _("Run"), i,Variables.playonlinux_env+"/resources/images/menu/media-playback-start.png",self.Run)
            i+=1
            self.menuGaucheAddLink("pol_prgm_kill", _("Close"), i,Variables.playonlinux_env+"/resources/images/menu/media-playback-stop.png",self.RKill)
            i+=1
            self.menuGaucheAddLink("pol_prgm_rundebug", _("Debug"), i,Variables.playonlinux_env+"/resources/images/menu/bug.png",self.RunDebug)
            i+=1
            self.menuGaucheAddLink("pol_prgm_reportproblem", _("Report a problem"), i,Variables.playonlinux_env+"/resources/images/menu/bug.png",self.ReportProblem)
            i+=1
            self.menuGaucheAddLink("pol_prgm_configure", _("Configure"), i,Variables.playonlinux_env+"/resources/images/menu/run.png",self.Configure)
            i+=1
            self.menuGaucheAddLink("pol_prgm_shortcut", _("Create a shortcut"), i,Variables.playonlinux_env+"/resources/images/menu/shortcut.png",self.Package)
            i+=1
            self.menuGaucheAddLink("pol_prgm_adddir", _("Open the directory"), i,Variables.playonlinux_env+"/resources/images/menu/folder-wine.png",self.GoToAppDir)

            if(os.path.exists(os.environ["POL_USER_ROOT"]+"/configurations/manuals/"+shortcut)):
                i+=1
                self.menuGaucheAddLink("pol_prgm_readme", _("Read the manual"), i,Variables.playonlinux_env+"/resources/images/menu/manual.png",self.ReadMe)
            i+=1
            self.menuGaucheAddLink("pol_prgm_polvaultsave", _("Save"), i,Variables.playonlinux_env+"/resources/images/menu/polvault.png",self.PolVaultSaveGame)

            i+=1
            self.menuGaucheAddLink("pol_prgm_uninstall", _("Uninstall"), i,Variables.playonlinux_env+"/resources/images/menu/window-close.png",self.UninstallGame)


            self.linksfile = os.environ["POL_USER_ROOT"]+"/configurations/links/"+shortcut
            if(os.path.exists(self.linksfile)):
                self.linksc = open(self.linksfile,"r").read().split("\n")
                for line in self.linksc:
                    if("|" in line):
                        line = line.split("|")
                        i+=1
                        if("PROFILEBUTTON/" in line[0]):
                            line[0] = line[0].replace("PROFILEBUTTON/","")

                        self.menuGaucheAddLink("url_"+str(i), line[0], i,Variables.playonlinux_env+"/resources/images/menu/star.png",None,line[1])

            icon = os.environ["POL_USER_ROOT"]+"/icones/full_size/"+shortcut

            self.perspective = self._mgr.SavePerspective().split("|")
            self.perspective = self.perspective[len(self.perspective) - 2].split("=")

            left_pos = (int(self.perspective[1]) - 50)/2
            if(left_pos <= 0):
                left_pos = (200-48)/2

            if(os.path.exists(icon)):
                try:
                    self.bitmap = wx.Image(icon)
                    if(self.bitmap.GetWidth() >= 48):
                        self.bitmap.Rescale(48,48,wx.IMAGE_QUALITY_HIGH)
                        self.bitmap = self.bitmap.ConvertToBitmap()
                        self.menuBitmap = wx.StaticBitmap(self.menu_gauche, id=-1, bitmap=self.bitmap, pos=(left_pos,20+(i+2)*20))
                except:
                    pass

    def menuGaucheAddTitle(self,id,text,pos):
        self.menuElem[id] = wx.StaticText(self.menu_gauche, -1, text,pos=(5,5+pos*20))
        self.menuElem[id].SetForegroundColour((0,0,0)) # For dark themes
        self.menuElem[id].SetFont(self.fontTitre)


    def menuGaucheAddLink(self,id,text,pos,image,evt,url=None):
        if(os.path.exists(image)):
            menu_icone = image
        else:
            menu_icone = Variables.playonlinux_env+"/etc/playonlinux.png"

        try:
            self.bitmap = wx.Image(menu_icone)
            self.bitmap.Rescale(16,16,wx.IMAGE_QUALITY_HIGH)
            self.bitmap = self.bitmap.ConvertToBitmap()
            self.menuImage[id] = wx.StaticBitmap(self.menu_gauche, id=-1, bitmap=self.bitmap, pos=(10,15+pos*20))

        except:
            pass

        if(url == None):
            self.menuElem[id] = wx.HyperlinkCtrl(self.menu_gauche, 10000+pos, text, "", pos=(35,15+pos*20))
        else:
            self.menuElem[id] = wx.HyperlinkCtrl(self.menu_gauche, 10000+pos, text, url, pos=(35,15+pos*20))

        self.menuElem[id].SetNormalColour(wx.Colour(0,0,0))
        self.menuElem[id].SetVisitedColour(wx.Colour(0,0,0))
        self.menuElem[id].SetHoverColour(wx.Colour(100,100,100))

        if(evt != None):
            wx.EVT_HYPERLINK(self, 10000+pos, evt)

    def donate(self, event):
        if(os.environ["POL_OS"] == "Mac"):
            webbrowser.open("http://www.playonmac.com/en/donate.html")
        else:
            webbrowser.open("http://www.playonlinux.com/en/donate.html")

    def Reload(self, event):
        self.games = os.listdir(Variables.playonlinux_rep+"shortcuts/")
        self.games.sort(key=str.upper)
        
        try:
            self.games.remove(".DS_Store")
        except:
            pass
            
        self.list_game.DeleteAllItems()
        self.images.RemoveAll()
        root = self.list_game.AddRoot("")
        self.i = 0
        if(self.iconSize <= 32):
            self.iconFolder = "32";
        else:
            self.iconFolder = "full_size";
        for game in self.games: #METTRE EN 32x32
            if(self.searchbox.GetValue().encode("utf-8","replace").lower() in game.lower()):
                if(not os.path.isdir(Variables.playonlinux_rep+"/shortcuts/"+game)):
                    if(os.path.exists(Variables.playonlinux_rep+"/icones/"+self.iconFolder+"/"+game)):
                         file_icone = Variables.playonlinux_rep+"/icones/"+self.iconFolder+"/"+game
                    else:
                        file_icone = Variables.playonlinux_env+"/etc/playonlinux.png"

                    try:
                        self.bitmap = wx.Image(file_icone)
                        self.bitmap.Rescale(self.iconSize,self.iconSize,wx.IMAGE_QUALITY_HIGH)
                        self.bitmap = self.bitmap.ConvertToBitmap()
                        self.images.Add(self.bitmap)
                    except:
                        pass
                    
                    item = self.list_game.AppendItem(root, game, self.i)
                    self.i += 1
        self.generate_menu(None)

        if(os.environ["POL_OS"] == "Mac"):
            self.playTool.Enable(False)
            self.stopTool.Enable(False)
            self.removeTool.Enable(False)


    def RConfigure(self, function_to_run, firstargument):
        """Starts polconfigurator remotely."""
        game_exec = self.GetSelectedProgram()
        if game_exec != "":
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/polconfigurator", game_exec, function_to_run, firstargument])
        else:
            wx.MessageBox(_("Please select a program."), os.environ["APPLICATION_TITLE"])


    def Options(self, event):
        onglet=event.GetId()
        try:
            self.optionFrame.SetFocus()
        except:
            self.optionFrame = options.MainWindow(self, -1, _("{0} settings").format(os.environ["APPLICATION_TITLE"]), 2)
            if(onglet == 211):
                self.optionFrame = options.MainWindow(self, -1, _("{0} settings").format(os.environ["APPLICATION_TITLE"]), 0)
            if(onglet == 214):
                self.optionFrame = options.MainWindow(self, -1, _("{0} settings").format(os.environ["APPLICATION_TITLE"]), 1)
            self.optionFrame.Center(wx.BOTH)
            self.optionFrame.Show(True)

    def killall(self, event):
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/killall"])

    def Executer(self, event):
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/expert/Executer"])

    def BugReport(self, event):
        try:
            self.debugFrame.Show()
            self.debugFrame.SetFocus()
        except:
            self.debugFrame = debug.MainWindow(None, -1, _("{0} debugger").format(os.environ["APPLICATION_TITLE"]))
            self.debugFrame.Center(wx.BOTH)
            self.debugFrame.Show()


    def POLOnline(self, event):
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/playonlinux_online"])

    def PCCd(self, event):
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/read_pc_cd"])

    def PolShell(self, event):
        #Variables.run_x_server()
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/expert/PolShell"])

    def Configure(self, event):
        game_exec = self.GetSelectedProgram()
        try:
            self.configureFrame.Show(True)
            self.configureFrame.SetFocus()
            if(game_exec != ""):
                self.configureFrame.change_program(game_exec,False)

        except:
            if(game_exec == ""):
                self.configureFrame = configure.MainWindow(self, -1, _("{0} configuration").format(os.environ["APPLICATION_TITLE"]),"default",True)
            else:
                self.configureFrame = configure.MainWindow(self, -1, _("{0} configuration").format(os.environ["APPLICATION_TITLE"]),game_exec.decode("utf-8","replace"),False)


            self.configureFrame.Center(wx.BOTH)
            self.configureFrame.Show(True)

        #subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/polconfigurator", game_exec])

    def Package(self, event):
        game_exec = self.GetSelectedProgram()
        subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/make_shortcut", game_exec])

    def UninstallGame(self, event):
        game_exec = self.GetSelectedProgram()
        if game_exec != "":
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/uninstall", game_exec])
        else:
            wx.MessageBox(_("Please select a program."), os.environ["APPLICATION_TITLE"])

    def PolVaultSaveGame(self, event):
        game_exec = self.GetSelectedProgram()
        if game_exec != "":
            subprocess.Popen(["bash", Variables.playonlinux_rep+"plugins/PlayOnLinux Vault/scripts/menu", "--app", game_exec])
        else:
            wx.MessageBox(_("Please select a program."), os.environ["APPLICATION_TITLE"])

    def InstallMenu(self, event):
        try:
            self.installFrame.Show(True)
            self.installFrame.SetFocus()
        except:
            self.installFrame = install.InstallWindow(self, -1, _('{0} install menu').format(os.environ["APPLICATION_TITLE"]))
            self.installFrame.Center(wx.BOTH)
            self.installFrame.Show(True)

    def WineVersion(self, event):
        try:
            self.wversion.Show()
            self.wversion.SetFocus()
        except:
            self.wversion = wver.MainWindow(None, -1, _('{0} wine versions manager').format(os.environ["APPLICATION_TITLE"]))
            self.wversion.Center(wx.BOTH)
            self.wversion.Show(True)

    def GetSelectedProgram(self):
        return self.list_game.GetItemText(self.list_game.GetSelection()).encode("utf-8","replace")
        
    def Run(self, event, s_debug=False):

        game_exec = self.GetSelectedProgram()
        game_prefix = playonlinux.getPrefix(game_exec)

        if(s_debug == False):
            playonlinux.SetDebugState(game_exec, game_prefix, False)

        if(os.path.exists(os.environ["POL_USER_ROOT"]+"/wineprefix/"+game_prefix)):
            if(game_exec != ""):
                if(playonlinux.GetDebugState(game_exec)):
                    try:
                        self.debugFrame.analyseReal(0, game_prefix)
                        self.debugFrame.Show()
                        self.debugFrame.SetFocus()
                    except:
                        self.debugFrame = debug.MainWindow(None, -1, _("{0} debugger").format(os.environ["APPLICATION_TITLE"]),game_prefix,0)
                        self.debugFrame.Center(wx.BOTH)
                        self.debugFrame.Show()

                subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/run_app", game_exec])
            else:
                wx.MessageBox(_("Please select a program."), os.environ["APPLICATION_TITLE"])
        else:
            wx.MessageBox(_("The virtual drive associated with {0} ({1}) does no longer exists.").format(game_exec, game_prefix), os.environ["APPLICATION_TITLE"])

    def RunDebug(self, event):
        game_exec = self.GetSelectedProgram()
        game_prefix = playonlinux.getPrefix(game_exec)
        playonlinux.SetDebugState(game_exec, game_prefix, True)
        self.Run(self, True)

    def ReportProblem(self, event):
        game_exec = self.GetSelectedProgram()
        game_log = playonlinux.getLog(game_exec)
        if game_log:
            new_env = os.environ
            new_env["LOGTITLE"] = game_log
            subprocess.Popen(["bash", Variables.playonlinux_env+"/bash/bug_report"], env = new_env)

    def POLDie(self):
        for pid in self.registeredPid:
            os.system("kill -9 -%d 2> /dev/null" % pid)
            os.system("kill -9 %d 2> /dev/null" % pid) 
        app.POLServer.closeServer()
        os._exit(0)

    def POLRestart(self):
        for pid in self.registeredPid:
            os.system("kill -9 -%d 2> /dev/null" % pid)
            os.system("kill -9 %d 2> /dev/null" % pid) 
        app.POLServer.closeServer()
        os._exit(63) # Restart code

    def ForceClose(self, signal, frame): # Catch SIGINT
        print "\nCtrl+C pressed. Killing all processes..."
        self.POLDie()

    def ClosePol(self, event):
        pids = []
        for pid in self.registeredPid:
            try:
                os.kill(pid, 0)
                pid_exists = True
                pids.append(pid)
            except OSError:
                pid_exists = False
            print "Registered PID: %d (%s)" % (pid, 'Present' if pid_exists else 'Missing')
        self.registeredPid = pids

        if(playonlinux.GetSettings("DONT_ASK_BEFORE_CLOSING") == "TRUE" or self.registeredPid == [] or wx.YES == wx.MessageBox(_('Are you sure you want to close all {0} Windows?').format(os.environ["APPLICATION_TITLE"]).decode("utf-8","replace"),os.environ["APPLICATION_TITLE"], style=wx.YES_NO | wx.ICON_QUESTION)):
            self.SizeToSave = self.GetSize();
            self.PositionToSave = self.GetPosition();
            # Save size and position
            playonlinux.SetSettings("MAINWINDOW_WIDTH",str(self.SizeToSave[0]))
            playonlinux.SetSettings("MAINWINDOW_HEIGHT",str(self.SizeToSave[1]-Variables.windows_add_playonmac*56))
            playonlinux.SetSettings("MAINWINDOW_X",str(self.PositionToSave[0]))
            playonlinux.SetSettings("MAINWINDOW_Y",str(self.PositionToSave[1]))
            self._mgr.UnInit()
            # I know, that's very ugly, but I have no choice for the moment
            self.perspective = self._mgr.SavePerspective().split("|")
            self.perspective = self.perspective[len(self.perspective) - 2].split("=")

            self.DockType = self.perspective[0]
            self.mySize = 200
            self.myPosition = "LEFT"

            if(self.DockType == "dock_size(4,0,0)"):
                self.mySize = int(self.perspective[1]) - 2
                self.myPosition = "LEFT"

            if(self.DockType == "dock_size(2,0,1)" or self.DockType == "dock_size(2,0,0)" or "dock_size(2," in self.DockType):
                self.mySize = int(self.perspective[1]) - 2
                self.myPosition = "RIGHT"

            playonlinux.SetSettings("PANEL_SIZE",str(self.mySize))
            playonlinux.SetSettings("PANEL_POSITION",str(self.myPosition))

            self.POLDie()
        return None

    def About(self, event):
        self.aboutBox = wx.AboutDialogInfo()
        if(os.environ["POL_OS"] == "Linux"):
            self.aboutBox.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))


        self.aboutBox.SetName(os.environ["APPLICATION_TITLE"])
        self.aboutBox.SetVersion(Variables.version)
        self.aboutBox.SetDescription(_("Run your Windows programs on "+os.environ["POL_OS"]+" !"))
        self.aboutBox.SetCopyright("© 2007-2013 "+_("PlayOnLinux and PlayOnMac team\nUnder GPL licence version 3"))
        self.aboutBox.AddDeveloper(_("Developer and Website: ")+"Tinou (Pâris Quentin), MulX (Petit Aymeric)")
        self.aboutBox.AddDeveloper(_("Scriptors: ")+"GNU_Raziel")
        self.aboutBox.AddDeveloper(_("Packager: ")+"MulX (Petit Aymeric), Tinou (Pâris Quentin)")
        self.aboutBox.AddDeveloper(_("Icons:")+"Faenza-Icons http://tiheum.deviantart.com/art/Faenza-Icons-173323228")
        self.aboutBox.AddDeveloper(_("The following people contributed to this program: ")+"kiplantt, Salvatos, Minchul")
        self.aboutBox.AddTranslator(_("Translations:"))
        self.aboutBox.AddTranslator(_("Read TRANSLATORS file"))

        if(os.environ["POL_OS"] == "Mac"):
            self.aboutBox.SetWebSite("http://www.playonmac.com")
        else:
            self.aboutBox.SetWebSite("http://www.playonlinux.com")
        wx.AboutBox(self.aboutBox)

class PlayOnLinuxApp(wx.App):
    def OnInit(self):
        lng.iLang()
        close = False
        exe_present = False

        os.system("bash "+Variables.playonlinux_env+"/bash/startup")
        self.systemCheck()
        
        for f in  sys.argv[1:]:
            self.MacOpenFile(f)
            if(".exe" in f or ".EXE" in f):
                exe_present = True
            close = True

        if(close == True and exe_present == False):
            os._exit(0)

        self.SetClassName(os.environ["APPLICATION_TITLE"])
        self.SetAppName(os.environ["APPLICATION_TITLE"])


        self.frame = MainWindow(None, -1, os.environ["APPLICATION_TITLE"])
        # Gui Server
        self.POLServer = gui_server.gui_server(self.frame)
        self.POLServer.start()
        
        i = 0
        while(os.environ["POL_PORT"] == "0"):
            time.sleep(0.01)
            if(i >= 300):
                 wx.MessageBox(_("{0} is not able to start PlayOnLinux Setup Window server.").format(os.environ["APPLICATION_TITLE"]),_("Error"))
                 os._exit(0)
                 break
            i+=1 
        os.system("bash \"$PLAYONLINUX/bash/startup_after_server\" &")
   
        self.SetTopWindow(self.frame)
        self.frame.Show(True)
        
        return True

    def _executableFound(self, executable):
        devnull = open('/dev/null', 'wb')
        try:
            returncode = subprocess.call(["which",executable],stdout=devnull)
            return (returncode == 0)
        except:
            return False

    def _singleCheck(self, executable, package, fatal):
        if not self._executableFound(executable):
            message = _("{0} cannot find {1}")
            if package is not None:
                message += _(" (from {2})")

            if fatal:
                verdict = _("You need to install it to continue")
            else:
                verdict = _("You should install it to use {0}")

            wx.MessageBox(("%s\n\n%s" % (message, verdict)).format(os.environ["APPLICATION_TITLE"], executable, package), _("Error"))

            if fatal:
                os._exit(0)

    def singleCheck(self, executable, package=None):
        self._singleCheck(executable, package, False)

    def singleCheckFatal(self, executable, package=None):
        self._singleCheck(executable, package, True)

    def systemCheck(self):
        #### Root uid check
        if(os.popen("id -u").read() == "0\n" or os.popen("id -u").read() == "0"):
            wx.MessageBox(_("{0} is not supposed to be run as root. Sorry").format(os.environ["APPLICATION_TITLE"]),_("Error"))
            os._exit(0)

        #### 32 bits OpenGL check
        try:
            returncode=subprocess.call([os.environ["PLAYONLINUX"]+"/bash/check_gl","x86"])
        except:
            returncode=255
        if(os.environ["POL_OS"] == "Linux" and returncode != 0):
            wx.MessageBox(_("{0} is unable to find 32bits OpenGL libraries.\n\nYou might encounter problem with your games").format(os.environ["APPLICATION_TITLE"]),_("Error"))
            os.environ["OpenGL32"] = "0"
        else:
            os.environ["OpenGL32"] = "1"

        #### 64 bits OpenGL check
        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            try:
                returncode=subprocess.call([os.environ["PLAYONLINUX"]+"/bash/check_gl","amd64"])
            except:
                returncode=255
        if(os.environ["AMD64_COMPATIBLE"] == "True" and os.environ["POL_OS"] == "Linux" and returncode != 0):
            wx.MessageBox(_("{0} is unable to find 64bits OpenGL libraries.\n\nYou might encounter problem with your games").format(os.environ["APPLICATION_TITLE"]),_("Error"))
            os.environ["OpenGL64"] = "0"
        else:
            os.environ["OpenGL64"] = "1"

        #### Filesystem check
        if(os.environ["POL_OS"] == "Linux"):
            try:
                returncode=subprocess.call([os.environ["PLAYONLINUX"]+"/bash/check_fs"])
            except:
                returncode=255
            if(os.environ["POL_OS"] == "Linux" and returncode != 0):
                wx.MessageBox(_("Your filesystem might prevent {0} from running correctly.\n\nPlease open {0} in a terminal to get more details").format(os.environ["APPLICATION_TITLE"]),_("Error"))

        if(os.environ["DEBIAN_PACKAGE"] == "FALSE"):
            if(playonlinux.GetSettings("SEND_REPORT") == ""):
                if(wx.YES == wx.MessageBox(_('Do you want to help {0} to make a compatibility database?\n\nIf you click yes, the following things will be sent to us anonymously the first time you run a Windows program:\n\n- You graphic card model\n- Your OS version\n- If graphic drivers are installed or not.\n\n\nThese information will be very precious for us to help people.').format(os.environ["APPLICATION_TITLE"]).decode("utf-8","replace"), os.environ["APPLICATION_TITLE"],style=wx.YES_NO | wx.ICON_QUESTION)):
                    playonlinux.SetSettings("SEND_REPORT","TRUE")
                else:
                    playonlinux.SetSettings("SEND_REPORT","FALSE")

        #### Other import checks
        self.singleCheckFatal("nc", package="Netcat")
        self.singleCheckFatal("tar")
        self.singleCheckFatal("cabextract")
        self.singleCheckFatal("convert", package="ImageMagick")
        self.singleCheckFatal("wget", package="Wget")
        self.singleCheckFatal("curl", package="cURL")
        
        self.singleCheckFatal("gpg", package="GnuPG")

        if(os.environ["DEBIAN_PACKAGE"] == "FALSE"):
            self.singleCheck("xterm")
        self.singleCheck("gettext.sh", package="gettext")  # gettext-base on Debian
        self.singleCheck("icotool", package="icoutils")
        self.singleCheck("wrestool", package="icoutils")
        self.singleCheck("wine", package="Wine")
        self.singleCheck("unzip", package="InfoZIP")
        self.singleCheck("7z", package="P7ZIP full")  # p7zip-full on Debian

    def BringWindowToFront(self):
        try: # it's possible for this event to come when the frame is closed
            self.GetTopWindow().Raise()
        except:
            pass

    def MacOpenFile(self, filename):
        file_extension = string.split(filename,".")
        file_extension = file_extension[len(file_extension) - 1]
        if(file_extension == "desktop"): # Un raccourcis Linux
            content = open(filename,"r").readlines()
            i = 0
            while(i < len(content)):
                #wx.MessageBox(content[i], "PlayOnLinux", wx.OK)

                if("Path=" in content[i]):
                    cd_app = content[i].replace("Path=","").replace("\n","")
                if("Exec=" in content[i]):
                    exec_app = content[i].replace("Exec=","").replace("\n","")
                i += 1
            if(":\\\\\\\\" in exec_app):
                exec_app = exec_app.replace("\\\\","\\")
            try:
                os.system("cd \""+cd_app+"\" && "+exec_app+" &")
            except:
                pass

        elif(file_extension == "exe" or file_extension == "EXE"):
            os.system("bash \"$PLAYONLINUX/bash/run_exe\" \""+filename+"\" &")

        elif(file_extension == "pol" or file_extension == "POL"):
            if(wx.YES == wx.MessageBox(_('Are you sure you want to  want to install {0} package?').format(filename).decode("utf-8","replace"), os.environ["APPLICATION_TITLE"],style=wx.YES_NO | wx.ICON_QUESTION)):
                os.system("bash \"$PLAYONLINUX/bash/playonlinux-pkg\" -i \""+filename+"\" &")
        else:
            playonlinux.open_document(filename,file_extension.lower())

    def MacOpenURL(self, url):
        if(os.environ["POL_OS"] == "Mac" and "playonlinux://" in url):
            wx.MessageBox(_("You are trying to open a script design for {0}! It might not work as expected").format("PlayOnLinux"), os.environ["APPLICATION_TITLE"])
        if(os.environ["POL_OS"] == "Linux" and "playonmac://" in url):
            wx.MessageBox(_("You are trying to open a script design for {0}! It might not work as expected").format("PlayOnMac"), os.environ["APPLICATION_TITLE"])

        os.system("bash \"$PLAYONLINUX/bash/playonlinux-url_handler\" \""+url+"\" &")

    def MacReopenApp(self):
        #sys.exit()
        self.BringWindowToFront()

# Idea taken from flacon
def setSigchldHandler():
    signal.signal(signal.SIGCHLD, handleSigchld)
    if hasattr(signal, 'siginterrupt'):
        signal.siginterrupt(signal.SIGCHLD, False)

def handleSigchld(number, frame):
    # Apparently some UNIX systems automatically resent the SIGCHLD
    # handler to SIG_DFL.  Reset it just in case.
    setSigchldHandler()

setSigchldHandler()
lng.Lang()

wx.Log_EnableLogging(False)

app = PlayOnLinuxApp(redirect=False)
app.MainLoop()
#sys.exit(0)

########NEW FILE########
__FILENAME__ = options
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Pâris Quentin
# Copyright (C) 2007-2010 PlayOnLinux Team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from asyncore import dispatcher
import wxversion, os, getopt, sys, urllib, signal, socket, string
import wx, time, re
import webbrowser, shutil
import threading, time, codecs
from select import select
#from subprocess import Popen,PIPE

import lib.Variables as Variables
import lib.lng as lng
import lib.playonlinux as playonlinux

class getPlugins(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.thread_message = "#WAIT#"
        self.versions = []
        self.start()

    def download(self, game):
        self.getDescription = game

    def run(self):
        self.thread_running = True
        while(self.thread_running):
            if(self.thread_message == "get"):
                try :
                    url = 'http://mulx.playonlinux.com/wine/linux-i386/LIST'
                    req = urllib2.Request(url)
                    handle = urllib2.urlopen(req)
                    time.sleep(1)
                    available_versions = handle.read()
                    available_versions = string.split(available_versions,"\n")
                    self.i = 0
                    self.versions_ = []
                    while(self.i < len(available_versions) - 1):
                        informations = string.split(available_versions[self.i], ";")
                        version = informations[1]
                        package = informations[0]
                        sha1sum = informations[2]
                        if(not os.path.exists(Variables.playonlinux_rep+"/WineVersions/"+version)):
                            self.versions_.append(version)
                        self.i += 1
                    self.versions_.reverse()
                    self.versions = self.versions_[:]

                    self.thread_message = "Ok"
                except :
                    time.sleep(1)
                    self.thread_message = "Err"
                    self.versions = ["Wine packages website is unavailable"]
            else:
                time.sleep(0.2)


class Onglets(wx.Notebook):
        # Classe dérivée du wx.Notebook
    def __init__(self, parent):
        if(os.environ["POL_OS"] == "Mac"):
            self.fontTitle = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.caption_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)
        else :
            self.fontTitle = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "", wx.FONTENCODING_DEFAULT)
            self.caption_font = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,False, "", wx.FONTENCODING_DEFAULT)


        self.notebook = wx.Notebook.__init__(self, parent, -1)
        self.images_onglets = wx.ImageList(16, 16)
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/input-gaming.png"));
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/internet-group-chat.png"));
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/internet-web-browser.png"));
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/user-desktop.png"));
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/application-x-executable.png"));
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/package-x-generic.png"));
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/resources/images/menu/extensions.png"));

        self.SetImageList(self.images_onglets)


    def browser_test(self, event):
        if(self.Navigator.GetValue() == "Default"):
            webbrowser.open("http://www.playonlinux.com")
        else:
            os.system(self.Navigator.GetValue()+" http://www.playonlinux.com &")

    def term_test(self, event):
        os.system("bash "+Variables.playonlinux_env+"/bash/terminals/"+self.Term.GetValue()+" sleep 2 &")

    def Internet(self, nom):
        self.panelInternet = wx.Panel(self, -1)

        if(os.path.exists(Variables.playonlinux_rep+"/configurations/options/offline")):
            if(open(Variables.playonlinux_rep+"/configurations/options/offline",'r').read() == '1'):
                self.OffLineCheck.SetValue(1)

        self.ProxySettings = wx.StaticText(self.panelInternet, -1, _("Proxy configuration"), (0,0), wx.DefaultSize)
        self.ProxySettings.SetFont(self.fontTitle)

        proxy_settings = {}

        proxy_settings['PROXY_ENABLED'] = playonlinux.GetSettings("PROXY_ENABLED")
        if(proxy_settings['PROXY_ENABLED'] == ""):
            proxy_settings['PROXY_ENABLED'] = "0"
        proxy_settings['PROXY_ADRESS'] = playonlinux.GetSettings("PROXY_URL")
        proxy_settings["PROXY_PORT"] = playonlinux.GetSettings("PROXY_PORT")
        proxy_settings["PROXY_LOGIN"] = playonlinux.GetSettings("PROXY_LOGIN")
        proxy_settings["PROXY_PASS"] = playonlinux.GetSettings("PROXY_PASSWORD")

        self.ProxyCheck = wx.CheckBox(self.panelInternet, 120, _("Set a proxy"),pos=(10,30))
        self.ProxyCheck.SetValue(int(proxy_settings['PROXY_ENABLED']))

        self.ProxyTxtAdresse = wx.StaticText(self.panelInternet, -1, _("Proxy address"), (10,60), wx.DefaultSize)
        self.ProxyAdresse = wx.TextCtrl(self.panelInternet, -1, proxy_settings["PROXY_ADRESS"], pos=(20,80),size=(300,27))

        self.ProxyTxtPort = wx.StaticText(self.panelInternet, -1, _("Proxy port"), (10,120), wx.DefaultSize)
        self.ProxyPort = wx.TextCtrl(self.panelInternet, -1, proxy_settings["PROXY_PORT"], pos=(20,140),size=(80,27))

        self.ProxyTxtLogin = wx.StaticText(self.panelInternet, -1, _("Proxy login"), (10,180), wx.DefaultSize)
        self.ProxyLogin = wx.TextCtrl(self.panelInternet, -1, proxy_settings["PROXY_LOGIN"], pos=(20,200),size=(300,27))

        self.ProxyTxtPass = wx.StaticText(self.panelInternet, -1, _("Proxy password"), (10,240), wx.DefaultSize)
        self.ProxyPass = wx.TextCtrl(self.panelInternet, -1, proxy_settings["PROXY_PASS"], pos=(20,260),size=(300,27), style=wx.TE_PASSWORD)
        self.AddPage(self.panelInternet, nom, imageId=2)
        wx.EVT_CHECKBOX(self, 120, self.proxy_enable)
        self.proxy_enable(self)

    def proxy_enable(self, event):
        if(self.ProxyCheck.IsChecked() == 1):
            self.ProxyAdresse.Enable(True)
            self.ProxyLogin.Enable(True)
            self.ProxyPass.Enable(True)
            self.ProxyPort.Enable(True)
        else:
            self.ProxyAdresse.Enable(False)
            self.ProxyLogin.Enable(False)
            self.ProxyPass.Enable(False)
            self.ProxyPort.Enable(False)



    def LoadPlugins(self):
        self.pluginlist.DeleteAllItems()
        self.pluginImgList.RemoveAll()
        plugins=os.listdir(Variables.playonlinux_rep+"/plugins/")
        self.i = 0

        PluginsRoot = self.pluginlist.AddRoot("")
        plugins.sort()
        while(self.i < len(plugins)):
            self.pluginlist.AppendItem(PluginsRoot, plugins[self.i], self.i)
            if(os.path.exists(Variables.playonlinux_rep+"/plugins/"+plugins[self.i]+"/enabled") == False):
                self.pluginlist.SetItemTextColour(self.pluginlist.GetLastChild(PluginsRoot), wx.Colour(150,150,150))
            self.icon_look_for = Variables.playonlinux_rep+"/plugins/"+plugins[self.i]+"/icon"
            if(os.path.exists(self.icon_look_for)):
                self.pluginImgList.Add(wx.Bitmap(self.icon_look_for))
            else:
                self.pluginImgList.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/playonlinux16.png"))
            self.i += 1
        self.EnablePlugin.Enable(False)
        self.ConfigurePlugin.Enable(False)
        self.DelPlugin.Enable(False)

    def Plugins(self, nom):
        self.panelPlugins= wx.Panel(self, -1)
        self.panels_buttons_plugins = wx.Panel(self.panelPlugins, -1)

        self.sizerPlugins = wx.BoxSizer(wx.VERTICAL)
        self.txtPlugin = wx.StaticText(self.panelPlugins, -1, _("Installed plugins"), size=wx.DefaultSize)
        self.txtPlugin.SetFont(self.fontTitle)
        self.pluginlist = wx.TreeCtrl(self.panelPlugins, 220, style=Variables.widget_borders|wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT)
        self.pluginlist.SetSpacing(0)

        self.pluginImgList = wx.ImageList(16,16)

        self.pluginlist.SetImageList(self.pluginImgList)



        self.sizerPlugins.Add(self.txtPlugin, 1, wx.EXPAND|wx.ALL, 2)
        self.sizerPlugins.Add(self.pluginlist, 7, wx.EXPAND|wx.ALL, 2)

        self.sizerPlugins.Add(self.panels_buttons_plugins, 6, wx.EXPAND|wx.ALL, 2)

        self.panelPlugins.SetSizer(self.sizerPlugins)
        self.panelPlugins.SetAutoLayout(True)
        self.AddPlugin = wx.Button(self.panels_buttons_plugins, wx.ID_ADD, _("Add"), pos=(0,0), size=(100,35))
        self.DelPlugin = wx.Button(self.panels_buttons_plugins, wx.ID_REMOVE, _("Remove"), pos=(100,0), size=(100,35))
        self.ConfigurePlugin = wx.Button(self.panels_buttons_plugins, 212, _("Configure"), pos=(0,38), size=(100,35))
        self.EnablePlugin = wx.Button(self.panels_buttons_plugins, 213, _("Enable"), pos=(100,38), size=(100,35))
        self.txtPlugin = wx.StaticText(self.panels_buttons_plugins, -1, _("Choose a plugin"), size=(300,150), pos=(200,5))

        self.LoadPlugins()

        self.AddPage(self.panelPlugins, nom, imageId=5)

        wx.EVT_TREE_SEL_CHANGED(self, 220, self.choose_plugin)

        wx.EVT_BUTTON(self, 214, self.disable)
        wx.EVT_BUTTON(self, 213, self.enable)
        wx.EVT_BUTTON(self, 212, self.setup_plug)
        wx.EVT_BUTTON(self, wx.ID_REMOVE, self.delete_plug)
        wx.EVT_BUTTON(self, wx.ID_ADD, self.add_plug)

    def generateExts(self):
        self.list_ext.DeleteAllItems()
        i = 0
        self.exts = open(os.environ["POL_USER_ROOT"]+"/extensions.cfg").readlines()
        self.exts.sort()
        for line in self.exts:
            line = line.replace("\n","")
            line = string.split(line,"=")
            liner = "Line %s" % i
            self.list_ext.InsertStringItem(i, liner)
            self.list_ext.SetStringItem(i, 0, line[0])
            self.list_ext.SetStringItem(i, 1, line[1])
            i += 1
        self.app_installed_text.Hide()
        self.app_installed.Hide()
        self.delete_ext.Hide()
        self.app_installed.SetValue("")
        self.app_selected = -1

    def reditExt(self, event):

        playonlinux.SetSettings(self.ext_selected, self.app_installed.GetValue(),'_EXT_')
        self.generateExts()

    def editExt(self, event):
        self.app_installed_text.Show()
        self.app_installed.Show()
        self.delete_ext.Show()

        self.app_selected = string.split(self.exts[event.m_itemIndex],"=")[1]
        self.ext_selected = string.split(self.exts[event.m_itemIndex],"=")[0]

        self.app_installed.SetValue(self.app_selected.replace("\n","").replace("\r",""))

    def delExt(self, event):
        playonlinux.DeleteSettings(self.ext_selected,'_EXT_')
        self.generateExts()

    def newExt(self, event):
        newext = wx.GetTextFromUser(_("What is the extension?"), os.environ["APPLICATION_TITLE"])
        re.sub(r'\W+', '', newext)
        playonlinux.SetSettings(newext, "",'_EXT_')

        self.generateExts()

    def Extensions(self, nom):
        self.panelExt= wx.Panel(self, -1)
        self.list_ext = wx.ListCtrl(self.panelExt, 500, size=(504,350), pos=(1,1), style=wx.LC_REPORT)
        self.list_ext.InsertColumn(0, 'Extension')
        self.list_ext.InsertColumn(1, 'Program associated', width=320)

        self.app_installed_text = wx.StaticText(self.panelExt, pos=(1,388), label=_("Assigned program"))
        self.app_installed = wx.ComboBox(self.panelExt, 501, pos=(170,385),size=(200,25))
        self.delete_ext = wx.Button(self.panelExt, 502, pos=(372,385+2*Variables.windows_add_playonmac), size=(100,25), label=_("Delete"))


        self.add_ext = wx.Button(self.panelExt, 503, pos=(1,359), size=(100,25), label=_("New"))


        self.app_installed_list = os.listdir(os.environ["POL_USER_ROOT"]+"/shortcuts/")
        for i in self.app_installed_list:
            self.app_installed.Append(i)

        self.generateExts()
        self.AddPage(self.panelExt, nom, imageId=6)
        wx.EVT_LIST_ITEM_SELECTED(self, 500, self.editExt)
        wx.EVT_COMBOBOX(self, 501, self.reditExt)
        wx.EVT_BUTTON(self, 502, self.delExt)
        wx.EVT_BUTTON(self, 503, self.newExt)

    def setup_plug(self, event):
        self.current_plugin = self.pluginlist.GetItemText(self.pluginlist.GetSelection())
        self.plugin_path = Variables.playonlinux_rep+"/plugins/"+self.current_plugin
        os.system("bash \""+self.plugin_path+"/scripts/options\" &")

    def add_plug(self, event):
        self.FileDialog = wx.FileDialog(self)
        self.FileDialog.SetDirectory("~")
        self.FileDialog.SetWildcard("POL Packages (*.pol)|*.pol")
        result = self.FileDialog.ShowModal()
        if(result == wx.ID_OK and self.FileDialog.GetPath() != ""):
            if(wx.YES == wx.MessageBox(_("Are you sure you want to install: ").decode("utf-8","replace")+self.FileDialog.GetPath()+"?",os.environ["APPLICATION_TITLE"] ,style=wx.YES_NO | wx.ICON_QUESTION)):
                os.system("bash \""+Variables.playonlinux_env+"/playonlinux-pkg\" -i \""+self.FileDialog.GetPath().encode("utf-8","replace")+"\"")
                self.LoadPlugins()
        self.FileDialog.Destroy()

    def delete_plug(self, event):
        self.current_plugin = self.pluginlist.GetItemText(self.pluginlist.GetSelection())
        self.plugin_path = Variables.playonlinux_rep+"/plugins/"+self.current_plugin
        if(wx.YES == wx.MessageBox(_("Are you sure you want to delete: ").decode("utf-8","replace")+self.current_plugin+"?", os.environ["APPLICATION_TITLE"],style=wx.YES_NO | wx.ICON_QUESTION)):
            shutil.rmtree(self.plugin_path)
            self.LoadPlugins()
    def disable(self, event):
        self.current_plugin = self.pluginlist.GetItemText(self.pluginlist.GetSelection())
        self.plugin_path = Variables.playonlinux_rep+"/plugins/"+self.current_plugin
        os.remove(self.plugin_path+"/enabled")
        self.LoadPlugins()

    def enable(self, event):
        self.current_plugin = self.pluginlist.GetItemText(self.pluginlist.GetSelection())
        self.plugin_path = Variables.playonlinux_rep+"/plugins/"+self.current_plugin
        enab=open(self.plugin_path+"/enabled",'w')
        enab.close()
        self.LoadPlugins()

    def choose_plugin(self, event):
        self.current_plugin = self.pluginlist.GetItemText(self.pluginlist.GetSelection())
        self.plugin_path = Variables.playonlinux_rep+"/plugins/"+self.current_plugin
        if(os.path.exists(self.plugin_path+"/enabled")):
            self.EnablePlugin.Destroy()
            self.EnablePlugin = wx.Button(self.panels_buttons_plugins, 214, _("Disable"), pos=(100,38))
        else:
            self.EnablePlugin.Destroy()
            self.EnablePlugin = wx.Button(self.panels_buttons_plugins, 213, _("Enable"), pos=(100,38))

        if(os.path.exists(self.plugin_path+"/scripts/options")):
            self.ConfigurePlugin.Enable(True)
        else:
            self.ConfigurePlugin.Enable(False)

        if(os.path.exists(self.plugin_path+"/description")):
            self.txtPlugin.Destroy()
            self.txtPlugin = wx.StaticText(self.panels_buttons_plugins, -1, open(self.plugin_path+"/description","r").read(), size=(285,150), pos=(200,5))

        self.DelPlugin.Enable(True)

    def glxinfo(self, event):
        glx = os.popen("glxinfo", "r").read()
        self.txtGLX.SetValue(glx)

    def xorg(self, event):
        glx = open("/etc/X11/xorg.conf", "r").read()
        self.txtGLX.SetValue(glx)

    def glxgears(self, event):
        self.result = os.popen("glxgears", "r").read()
        self.txtGLX.SetValue(self.result)

    def system_info(self, event):
        self.txtGLX.SetValue(os.popen("bash \""+Variables.playonlinux_env+"/bash/system_info\" &", "r").read())

    def SupprimePage(self, index):
        self.DeletePage(index)


class MainWindow(wx.Frame):
    def __init__(self,parent,id,title,onglet):
        wx.Frame.__init__(self, parent, -1, title, size = (505, 550), style = wx.CLOSE_BOX | wx.CAPTION | wx.MINIMIZE_BOX)
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.panelFenp = wx.Panel(self, -1)
        self.panels_buttons = wx.Panel(self.panelFenp, -1)
        self.Apply = wx.Button(self.panels_buttons, wx.ID_APPLY, _("Apply"), pos=(400,0), size=(100,35))
        self.Close = wx.Button(self.panels_buttons, wx.ID_CLOSE, _("Cancel"), pos=(295,0), size=(100,35))
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.onglets = Onglets(self.panelFenp)

        self.sizer.Add(self.onglets, 12, wx.EXPAND|wx.ALL, 2)
        self.sizer.Add(self.panels_buttons, 1, wx.EXPAND|wx.ALL, 2)

        #self.onglets.General(_("General"))
        self.onglets.Internet(_("Internet"))
        #self.onglets.Wine(_("Environment"))
        #self.onglets.System(_("System"))
        self.onglets.Plugins(_("Plugins"))
        self.onglets.Extensions(_("File associations"))

        try:
            self.onglets.SetSelection(onglet)
        except:
            pass

        self.panelFenp.SetSizer(self.sizer)
        self.panelFenp.SetAutoLayout(True)
        wx.EVT_BUTTON(self, wx.ID_APPLY, self.apply_settings)
        wx.EVT_BUTTON(self, wx.ID_CLOSE, self.app_Close)

    def app_Close(self, event):
        self.Destroy()

    def apply_settings(self, event):
        playonlinux.SetSettings("PROXY_ENABLED",str(int(self.onglets.ProxyCheck.IsChecked())))
        if(self.onglets.ProxyCheck.IsChecked()):
            playonlinux.SetSettings("PROXY_URL",self.onglets.ProxyAdresse.GetValue().replace("http://",""))
            playonlinux.SetSettings("PROXY_PORT",self.onglets.ProxyPort.GetValue())
            playonlinux.SetSettings("PROXY_LOGIN",self.onglets.ProxyLogin.GetValue())
            playonlinux.SetSettings("PROXY_PASSWORD",self.onglets.ProxyPass.GetValue())


        wx.MessageBox(_("You must restart {0} for the changes to take effect.").format(os.environ["APPLICATION_TITLE"]), os.environ["APPLICATION_TITLE"], wx.OK)
        self.Destroy()

########NEW FILE########
__FILENAME__ = sp
#!/usr/bin/python
# -*- coding:Utf-8 -*-

# Copyright (C) 2008 Pâris Quentin
# Copyright (C) 2007-2010 PlayOnLinux Team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import base64
import wx, wx.html
import lib.Variables as Variables, sys
import StringIO


class egg(wx.Frame):
    def __init__(self,parent,id,title):
        wx.Frame.__init__(self, parent, -1, title, size = (500, 333))
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        self.img = "/9j/4AAQSkZJRgABAQEASABIAAD/4gxYSUNDX1BST0ZJTEUAAQEAAAxITGlubwIQAABtbnRyUkdC\
    IFhZWiAHzgACAAkABgAxAABhY3NwTVNGVAAAAABJRUMgc1JHQgAAAAAAAAAAAAAAAAAA9tYAAQAA\
    AADTLUhQICAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABFj\
    cHJ0AAABUAAAADNkZXNjAAABhAAAAGx3dHB0AAAB8AAAABRia3B0AAACBAAAABRyWFlaAAACGAAA\
    ABRnWFlaAAACLAAAABRiWFlaAAACQAAAABRkbW5kAAACVAAAAHBkbWRkAAACxAAAAIh2dWVkAAAD\
    TAAAAIZ2aWV3AAAD1AAAACRsdW1pAAAD+AAAABRtZWFzAAAEDAAAACR0ZWNoAAAEMAAAAAxyVFJD\
    AAAEPAAACAxnVFJDAAAEPAAACAxiVFJDAAAEPAAACAx0ZXh0AAAAAENvcHlyaWdodCAoYykgMTk5\
    OCBIZXdsZXR0LVBhY2thcmQgQ29tcGFueQAAZGVzYwAAAAAAAAASc1JHQiBJRUM2MTk2Ni0yLjEA\
    AAAAAAAAAAAAABJzUkdCIElFQzYxOTY2LTIuMQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAWFlaIAAAAAAAAPNRAAEAAAABFsxYWVogAAAAAAAAAAAAAAAA\
    AAAAAFhZWiAAAAAAAABvogAAOPUAAAOQWFlaIAAAAAAAAGKZAAC3hQAAGNpYWVogAAAAAAAAJKAA\
    AA+EAAC2z2Rlc2MAAAAAAAAAFklFQyBodHRwOi8vd3d3LmllYy5jaAAAAAAAAAAAAAAAFklFQyBo\
    dHRwOi8vd3d3LmllYy5jaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
    AAAAAABkZXNjAAAAAAAAAC5JRUMgNjE5NjYtMi4xIERlZmF1bHQgUkdCIGNvbG91ciBzcGFjZSAt\
    IHNSR0IAAAAAAAAAAAAAAC5JRUMgNjE5NjYtMi4xIERlZmF1bHQgUkdCIGNvbG91ciBzcGFjZSAt\
    IHNSR0IAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZGVzYwAAAAAAAAAsUmVmZXJlbmNlIFZpZXdpbmcg\
    Q29uZGl0aW9uIGluIElFQzYxOTY2LTIuMQAAAAAAAAAAAAAALFJlZmVyZW5jZSBWaWV3aW5nIENv\
    bmRpdGlvbiBpbiBJRUM2MTk2Ni0yLjEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHZpZXcAAAAA\
    ABOk/gAUXy4AEM8UAAPtzAAEEwsAA1yeAAAAAVhZWiAAAAAAAEwJVgBQAAAAVx/nbWVhcwAAAAAA\
    AAABAAAAAAAAAAAAAAAAAAAAAAAAAo8AAAACc2lnIAAAAABDUlQgY3VydgAAAAAAAAQAAAAABQAK\
    AA8AFAAZAB4AIwAoAC0AMgA3ADsAQABFAEoATwBUAFkAXgBjAGgAbQByAHcAfACBAIYAiwCQAJUA\
    mgCfAKQAqQCuALIAtwC8AMEAxgDLANAA1QDbAOAA5QDrAPAA9gD7AQEBBwENARMBGQEfASUBKwEy\
    ATgBPgFFAUwBUgFZAWABZwFuAXUBfAGDAYsBkgGaAaEBqQGxAbkBwQHJAdEB2QHhAekB8gH6AgMC\
    DAIUAh0CJgIvAjgCQQJLAlQCXQJnAnECegKEAo4CmAKiAqwCtgLBAssC1QLgAusC9QMAAwsDFgMh\
    Ay0DOANDA08DWgNmA3IDfgOKA5YDogOuA7oDxwPTA+AD7AP5BAYEEwQgBC0EOwRIBFUEYwRxBH4E\
    jASaBKgEtgTEBNME4QTwBP4FDQUcBSsFOgVJBVgFZwV3BYYFlgWmBbUFxQXVBeUF9gYGBhYGJwY3\
    BkgGWQZqBnsGjAadBq8GwAbRBuMG9QcHBxkHKwc9B08HYQd0B4YHmQesB78H0gflB/gICwgfCDII\
    RghaCG4IggiWCKoIvgjSCOcI+wkQCSUJOglPCWQJeQmPCaQJugnPCeUJ+woRCicKPQpUCmoKgQqY\
    Cq4KxQrcCvMLCwsiCzkLUQtpC4ALmAuwC8gL4Qv5DBIMKgxDDFwMdQyODKcMwAzZDPMNDQ0mDUAN\
    Wg10DY4NqQ3DDd4N+A4TDi4OSQ5kDn8Omw62DtIO7g8JDyUPQQ9eD3oPlg+zD88P7BAJECYQQxBh\
    EH4QmxC5ENcQ9RETETERTxFtEYwRqhHJEegSBxImEkUSZBKEEqMSwxLjEwMTIxNDE2MTgxOkE8UT\
    5RQGFCcUSRRqFIsUrRTOFPAVEhU0FVYVeBWbFb0V4BYDFiYWSRZsFo8WshbWFvoXHRdBF2UXiReu\
    F9IX9xgbGEAYZRiKGK8Y1Rj6GSAZRRlrGZEZtxndGgQaKhpRGncanhrFGuwbFBs7G2MbihuyG9oc\
    AhwqHFIcexyjHMwc9R0eHUcdcB2ZHcMd7B4WHkAeah6UHr4e6R8THz4faR+UH78f6iAVIEEgbCCY\
    IMQg8CEcIUghdSGhIc4h+yInIlUigiKvIt0jCiM4I2YjlCPCI/AkHyRNJHwkqyTaJQklOCVoJZcl\
    xyX3JicmVyaHJrcm6CcYJ0kneierJ9woDSg/KHEooijUKQYpOClrKZ0p0CoCKjUqaCqbKs8rAis2\
    K2krnSvRLAUsOSxuLKIs1y0MLUEtdi2rLeEuFi5MLoIuty7uLyQvWi+RL8cv/jA1MGwwpDDbMRIx\
    SjGCMbox8jIqMmMymzLUMw0zRjN/M7gz8TQrNGU0njTYNRM1TTWHNcI1/TY3NnI2rjbpNyQ3YDec\
    N9c4FDhQOIw4yDkFOUI5fzm8Ofk6Njp0OrI67zstO2s7qjvoPCc8ZTykPOM9Ij1hPaE94D4gPmA+\
    oD7gPyE/YT+iP+JAI0BkQKZA50EpQWpBrEHuQjBCckK1QvdDOkN9Q8BEA0RHRIpEzkUSRVVFmkXe\
    RiJGZ0arRvBHNUd7R8BIBUhLSJFI10kdSWNJqUnwSjdKfUrESwxLU0uaS+JMKkxyTLpNAk1KTZNN\
    3E4lTm5Ot08AT0lPk0/dUCdQcVC7UQZRUFGbUeZSMVJ8UsdTE1NfU6pT9lRCVI9U21UoVXVVwlYP\
    VlxWqVb3V0RXklfgWC9YfVjLWRpZaVm4WgdaVlqmWvVbRVuVW+VcNVyGXNZdJ114XcleGl5sXr1f\
    D19hX7NgBWBXYKpg/GFPYaJh9WJJYpxi8GNDY5dj62RAZJRk6WU9ZZJl52Y9ZpJm6Gc9Z5Nn6Wg/\
    aJZo7GlDaZpp8WpIap9q92tPa6dr/2xXbK9tCG1gbbluEm5rbsRvHm94b9FwK3CGcOBxOnGVcfBy\
    S3KmcwFzXXO4dBR0cHTMdSh1hXXhdj52m3b4d1Z3s3gReG54zHkqeYl553pGeqV7BHtje8J8IXyB\
    fOF9QX2hfgF+Yn7CfyN/hH/lgEeAqIEKgWuBzYIwgpKC9INXg7qEHYSAhOOFR4Wrhg6GcobXhzuH\
    n4gEiGmIzokziZmJ/opkisqLMIuWi/yMY4zKjTGNmI3/jmaOzo82j56QBpBukNaRP5GokhGSepLj\
    k02TtpQglIqU9JVflcmWNJaflwqXdZfgmEyYuJkkmZCZ/JpomtWbQpuvnByciZz3nWSd0p5Anq6f\
    HZ+Ln/qgaaDYoUehtqImopajBqN2o+akVqTHpTilqaYapoum/adup+CoUqjEqTepqaocqo+rAqt1\
    q+msXKzQrUStuK4trqGvFq+LsACwdbDqsWCx1rJLssKzOLOutCW0nLUTtYq2AbZ5tvC3aLfguFm4\
    0blKucK6O7q1uy67p7whvJu9Fb2Pvgq+hL7/v3q/9cBwwOzBZ8Hjwl/C28NYw9TEUcTOxUvFyMZG\
    xsPHQce/yD3IvMk6ybnKOMq3yzbLtsw1zLXNNc21zjbOts83z7jQOdC60TzRvtI/0sHTRNPG1EnU\
    y9VO1dHWVdbY11zX4Nhk2OjZbNnx2nba+9uA3AXcit0Q3ZbeHN6i3ynfr+A24L3hROHM4lPi2+Nj\
    4+vkc+T85YTmDeaW5x/nqegy6LzpRunQ6lvq5etw6/vshu0R7ZzuKO6070DvzPBY8OXxcvH/8ozz\
    GfOn9DT0wvVQ9d72bfb794r4Gfio+Tj5x/pX+uf7d/wH/Jj9Kf26/kv+3P9t////2wBDAAEBAQEB\
    AQEBAQEBAQECAgMCAgICAgQDAwIDBQQFBQUEBAQFBgcGBQUHBgQEBgkGBwgICAgIBQYJCgkICgcI\
    CAj/2wBDAQEBAQICAgQCAgQIBQQFCAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgI\
    CAgICAgICAgICAgICAj/wAARCAFNAfQDAREAAhEBAxEB/8QAHwAAAAYDAQEBAAAAAAAAAAAABAUG\
    BwgJAAMKAgEL/8QAYxAAAQIEBAMEBwQFBgcMCAILAQIDBAUGEQAHEiEIMUETIlFhCRQycYGR8BUj\
    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\
    V05Ej1r/2Q=="
        self.img = base64.decodestring(self.img)
        self.img = StringIO.StringIO(self.img)
        self.img = wx.BitmapFromImage(wx.ImageFromStream(self.img))
        self.img = wx.StaticBitmap(self, -1, self.img)

########NEW FILE########
__FILENAME__ = wine_versions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2007 Pâris Quentin
# Copyright (C) 2007-2010 PlayOnLinux Team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import wxversion, os, getopt, sys, urllib, signal, socket, codecs, string, shutil, time, urllib, urllib2
import wx, wx.animate

import lib.Variables as Variables
import lib.lng, threading

if(os.environ["POL_OS"] == "Mac"):
    os_pref = "darwin"
else:
    os_pref = "linux"

lib.lng.Lang()

def SetWineVersion(game, version):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    fichier = open(cfile,"r").readlines()
    i = 0
    line = []
    while(i < len(fichier)): # On retire l'eventuel
        fichier[i] = fichier[i].replace("\n","")
        if("PATH=" not in fichier[i] or "WineVersions" not in fichier[i]):
            line.append(fichier[i])
        i += 1

    fichier_write = open(cfile,"w")

    if(version != "System"): # On insere
        if(os.environ["POL_OS"] == "Mac"):
            line.insert(1,"PATH=\""+Variables.playonlinux_rep+"WineVersions/"+version+"/bin/:$PATH\"")
            line.insert(1,"LD_LIBRARY_PATH=\""+Variables.playonlinux_rep+"WineVersions/"+version+"/lib/:$LD_LIBRARY_PATH\"")
        else:
            line.insert(1,"PATH=\""+Variables.playonlinux_rep+"WineVersions/"+version+"/usr/bin/:$PATH\"")
            line.insert(1,"LD_LIBRARY_PATH=\""+Variables.playonlinux_rep+"WineVersions/"+version+"/usr/lib/:$LD_LIBRARY_PATH\"")


    i = 0
    while(i < len(line)): # On ecrit
        fichier_write.write(line[i]+"\n")
        i+=1

def GetWineVersion(game):
    cfile = Variables.playonlinux_rep+"shortcuts/"+game
    fichier = open(cfile,"r").readlines()
    i = 0
    line = ""
    while(i < len(fichier)):
        fichier[i] = fichier[i].replace("\n","")
        if("PATH=" in fichier[i] and "WineVersions" in fichier[i]):
            line = fichier[i].replace("//","/")
        i += 1

    if(line == ""):
        version = "System"
    else:
        version=line.replace("PATH=","").replace("\"","").replace(Variables.playonlinux_rep,"").replace("//","/")
        version = string.split(version,"/")
        version = version[1]

    return(version)


def keynat(string):
    r'''A natural sort helper function for sort() and sorted()
    without using regular expressions or exceptions.

    >>> items = ('Z', 'a', '10th', '1st', '9')
    >>> sorted(items)
    ['10th', '1st', '9', 'Z', 'a']
    >>> sorted(items, key=keynat)
    ['1st', '9', '10th', 'a', 'Z']

    Borrowed from http://code.activestate.com/recipes/285264/#c6
    by paul clinch.

    License is the PSF Python License, http://www.python.org/psf/license/ (GPL compatible)
    '''
    it = type(1)
    r = []
    for c in string:
        if c.isdigit():
            d = int(c)
            if r and type( r[-1] ) == it:
                r[-1] = r[-1] * 10 + d
            else:
                r.append(d)
        else:
            r.append(c.lower())
    return r

class getVersions(threading.Thread):
    def __init__(self, arch="x86"):
        threading.Thread.__init__(self)
        self.thread_message = "#WAIT#"
        self.versions = []
        self.architecture = arch
        self.start()

    def download(self, game):
        self.getDescription = game

    def run(self):
        self.thread_running = True
        while(self.thread_running):
            if(self.thread_message == "get"):
                wfolder = os_pref+"-"+self.architecture
                try :

                    url = os.environ["WINE_SITE"]+"/"+wfolder+".lst"

                    #print(url)
                    req = urllib2.Request(url)
                    handle = urllib2.urlopen(req, timeout = 2)
                    time.sleep(1)
                    available_versions = handle.read()
                    available_versions = string.split(available_versions,"\n")

                    self.i = 0
                    self.versions_ = []
                    while(self.i < len(available_versions) - 1):
                        informations = string.split(available_versions[self.i], ";")
                        version = informations[1]
                        package = informations[0]
                        sha1sum = informations[2]
                        if(not os.path.exists(Variables.playonlinux_rep+"/wine/"+wfolder+"/"+version)):
                            self.versions_.append(version)
                        self.i += 1
                    self.versions_.reverse()
                    self.versions = self.versions_[:]

                    self.thread_message = "Ok"
                except :
                    time.sleep(1)
                    self.thread_message = "Err"
                    self.versions = ["Wine packages website is unavailable"]

            else:
                time.sleep(0.2)

class Onglets(wx.Notebook):
        # Classe dérivée du wx.Notebook
    def __init__(self, parent):
        self.notebook = wx.Notebook.__init__(self, parent, -1)
        self.images_onglets = wx.ImageList(16, 16)
        self.images_onglets.Add(wx.Bitmap(Variables.playonlinux_env+"/etc/onglet/wine.png"))
        self.SetImageList(self.images_onglets)
        self.panelFenp = {}
        self.imagesapps = {}
        self.imagesapps_i = {}
        self.list_apps = {}
        self.new_panel = {}
        self.list_ver_installed = {}
        self.button_rm = {}
        self.button_in = {}

    def liste_versions(self, arch="x86"):
        if(arch == "amd64"):
            add=100
        else:
            add=0
        self.panelFenp[arch] = wx.Panel(self, -1)
        self.imagesapps[arch] = wx.ImageList(22, 22)
        self.imagesapps_i[arch] = wx.ImageList(22, 22)


        self.list_apps[arch] = wx.TreeCtrl(self.panelFenp[arch], 106+add, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|Variables.widget_borders, size=(320, 300), pos=(10,35))
        self.list_apps[arch].SetImageList(self.imagesapps[arch])
        self.list_apps[arch].SetSpacing(0);

        self.new_panel[arch] = wx.Panel(self.panelFenp[arch], -1, pos=(10,505), size=(100,100))

        self.list_ver_installed[arch] = wx.TreeCtrl(self.panelFenp[arch], 107+add, style=wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT|Variables.widget_borders, size=(320, 300), pos=(400,35))
        self.list_ver_installed[arch].SetImageList(self.imagesapps_i[arch])
        self.list_ver_installed[arch].SetSpacing(0);
        wx.StaticText(self.panelFenp[arch], -1, _("Installed Wine versions: "),(395,10))
        wx.StaticText(self.panelFenp[arch], -1, _("Available Wine versions: "),(5,10))

        self.button_rm[arch] = wx.Button(self.panelFenp[arch], 108+add, "<", pos=(340, 175), size=(50,30))
        self.button_in[arch] = wx.Button(self.panelFenp[arch], 109+add,">", pos=(340, 125), size=(50,30))

        self.button_rm[arch].Enable(False)
        self.button_in[arch].Enable(False)
        self.AddPage(self.panelFenp[arch], _("Wine versions")+" ("+arch+")", imageId=0)






class MainWindow(wx.Frame):
    def __init__(self,parent,id,title):
        self.download32 = getVersions("x86")
        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            self.download64 = getVersions("amd64")

        wx.Frame.__init__(self, parent, -1, title, size = (750, 400+Variables.windows_add_size), style = wx.CLOSE_BOX | wx.CAPTION | wx.MINIMIZE_BOX)
        self.timer = wx.Timer(self, 1)
        self.SetIcon(wx.Icon(Variables.playonlinux_env+"/etc/playonlinux.png", wx.BITMAP_TYPE_ANY))
        #self.panel = wx.Panel(self, -1)

        self.onglets = Onglets(self)
        #self.sizer = wx.BoxSizer(wx.VERTICAL)
        #self.sizer.Add(self.onglets, 15, wx.EXPAND|wx.ALL, 2)

        self.getVersions("x86")
        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            self.getVersions("amd64")
        #self.panel.SetSizer(self.sizer)
        #self.panel.SetAutoLayout(True)

        self.onglets.liste_versions()
        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            self.onglets.liste_versions("amd64")
        self.oldreload32=""

        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            self.oldreload64=""

        self.oldversions32 = []

        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            self.oldversions64 = []

        #self.button = wx.Button(self.panels_buttons, wx.ID_CLOSE, _("Close"), pos=(510, 5), size=wx.DefaultSize)

        wx.EVT_BUTTON(self, wx.ID_CLOSE, self.closeapp)
        wx.EVT_CLOSE(self, self.closeapp)
        wx.EVT_TREE_SEL_CHANGED(self, 106, self.unselect32)
        wx.EVT_TREE_SEL_CHANGED(self, 107, self.unselect32)
        wx.EVT_BUTTON(self, 108, self.delete32)
        wx.EVT_BUTTON(self, 109, self.install32)

        wx.EVT_TREE_SEL_CHANGED(self, 206, self.unselect64)
        wx.EVT_TREE_SEL_CHANGED(self, 207, self.unselect64)
        wx.EVT_BUTTON(self, 208, self.delete64)
        wx.EVT_BUTTON(self, 209, self.install64)

        self.Bind(wx.EVT_TIMER, self.AutoReload, self.timer)
        self.timer.Start(200)

    def AutoReload(self, event):
        reload32 = os.listdir(Variables.playonlinux_rep+"/wine/"+os_pref+"-x86")
        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            reload64 = os.listdir(Variables.playonlinux_rep+"/wine/"+os_pref+"-amd64")
        if(self.download32.thread_message == "Ok" or self.download32.thread_message == "Err"):
            self.onglets.new_panel["x86"].Hide()
            self.WriteVersion()
            self.download32.thread_message = "Wait"

        else:
            if(self.download32.thread_message != "Wait"):
                self.onglets.new_panel["x86"].Show()


        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            if(self.download64.thread_message == "Ok" or self.download64.thread_message == "Err"):
                self.onglets.new_panel["amd64"].Hide()
                self.WriteVersion("amd64")
                self.download64.thread_message = "Wait"
            else:
                if(self.download64.thread_message != "Wait"):
                    self.onglets.new_panel["amd64"].Show()

        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            if(reload64 != self.oldreload64):
                self.getVersions("amd64")
                self.oldreload64 = reload64

        if(reload32 != self.oldreload32):
            self.getVersions()
            self.oldreload32 = reload32

        if(self.download32.versions != self.oldversions32):
            self.oldversions32 = self.download32.versions[:]

        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            if(self.download64.versions != self.oldversions64):
                self.oldversions64 = self.download64.versions[:]



    def sizedirectory(self, path):
        size = 0
        for root, dirs, files in os.walk(path):
            for fic in files:
                size += os.path.getsize(os.path.join(root, fic))
        return size

    def unselect32(self, event):
        if(event.GetId() == 106):
            self.onglets.list_ver_installed["x86"].UnselectAll()
            self.onglets.button_rm["x86"].Enable(False)
            self.onglets.button_in["x86"].Enable(True)
        if(event.GetId() == 107):
            self.onglets.list_apps["x86"].UnselectAll()
            self.onglets.button_rm["x86"].Enable(True)
            self.onglets.button_in["x86"].Enable(False)

    def delete32(self, event):
        version = self.onglets.list_ver_installed["x86"].GetItemText(self.onglets.list_ver_installed["x86"].GetSelection()).encode("utf-8","replace")

        if(wx.YES == wx.MessageBox(_('Are you sure you want to delete wine {0}?').format(version).decode("utf-8","replace"), os.environ["APPLICATION_TITLE"],style=wx.YES_NO | wx.ICON_QUESTION)):
            shutil.rmtree(Variables.playonlinux_rep+"/wine/"+os_pref+"-x86/"+version)

    def install32(self, event):
        install = self.onglets.list_apps["x86"].GetItemText(self.onglets.list_apps["x86"].GetSelection()).encode("utf-8","replace")
        os.system("bash \""+Variables.playonlinux_env+"/bash/install_wver\" "+install+" x86 &")


    def unselect64(self, event):
        if(event.GetId() == 206):
            self.onglets.list_ver_installed["amd64"].UnselectAll()
            self.onglets.button_rm["amd64"].Enable(False)
            self.onglets.button_in["amd64"].Enable(True)
        if(event.GetId() == 207):
            self.onglets.list_apps["amd64"].UnselectAll()
            self.onglets.button_rm["amd64"].Enable(True)
            self.onglets.button_in["amd64"].Enable(False)

    def delete64(self, event):
        version = self.onglets.list_ver_installed["amd64"].GetItemText(self.onglets.list_ver_installed["amd64"].GetSelection()).encode("utf-8","replace")
        if(wx.YES == wx.MessageBox("Are you sure you want to delete wine "+version+"?", style=wx.YES_NO | wx.ICON_QUESTION)):
            shutil.rmtree(Variables.playonlinux_rep+"/wine/"+os_pref+"-amd64/"+version)

    def install64(self, event):
        install = self.onglets.list_apps["amd64"].GetItemText(self.onglets.list_apps["amd64"].GetSelection()).encode("utf-8","replace")
        os.system("bash \""+Variables.playonlinux_env+"/bash/install_wver\" "+install+" amd64 &")

    def getVersions(self, arch="x86"):
        if(arch == "x86"):
            self.download32.thread_message = "get"
        if(arch == "amd64"):
            self.download64.thread_message = "get"


    def WriteVersion(self, arch="x86"):
        self.onglets.imagesapps[arch].RemoveAll()
        self.onglets.imagesapps_i[arch].RemoveAll()
        self.onglets.list_apps[arch].DeleteAllItems()
        self.onglets.list_ver_installed[arch].DeleteAllItems()

        root = self.onglets.list_apps[arch].AddRoot("")
        self.i = 0
        if(arch == "x86"):
            while(self.i < len(self.download32.versions)):
                self.onglets.imagesapps[arch].Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/wine-packages.png"))
                self.onglets.list_apps[arch].AppendItem(root,self.download32.versions[self.i],self.i)
                self.i += 1
        if(arch == "amd64"):
            while(self.i < len(self.download64.versions)):
                self.onglets.imagesapps[arch].Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/wine-packages.png"))
                self.onglets.list_apps[arch].AppendItem(root,self.download64.versions[self.i],self.i)
                self.i += 1

        root2 = self.onglets.list_ver_installed[arch].AddRoot("")
        wfolder = os_pref+"-"+arch

        installed_versions = os.listdir(Variables.playonlinux_rep+"/wine/"+wfolder)
        installed_versions.sort(key=keynat)
        installed_versions.reverse()
        self.i = 0
        self.j = 0
        while(self.i < len(installed_versions)):
            if(os.path.isdir(Variables.playonlinux_rep+"/wine/"+wfolder+"/"+installed_versions[self.i])):
                if(len(os.listdir(Variables.playonlinux_rep+"/wine/"+wfolder+"/"+installed_versions[self.i])) == 0):
                    self.onglets.imagesapps_i[arch].Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/wine-warning.png"))
                else:
                    self.onglets.imagesapps_i[arch].Add(wx.Bitmap(Variables.playonlinux_env+"/etc/install/wine.png"))
                self.onglets.list_ver_installed[arch].AppendItem(root2,installed_versions[self.i],self.j)
                self.j += 1
            self.i += 1
        try :
            if(versions[0] == "Wine packages website is unavailable"):
                self.onglets.list_apps[arch].Enable(False)
                self.onglets.imagesapps[arch].RemoveAll()
        except :
            pass
        self.onglets.button_rm[arch].Enable(False)
        self.onglets.button_in[arch].Enable(False)

    def closeapp(self, event):
        self.download32.thread_running = False
        if(os.environ["AMD64_COMPATIBLE"] == "True"):
            self.download64.thread_running = False

        self.Destroy()

########NEW FILE########
__FILENAME__ = wrapper
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2008 Pâris Quentin

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# PlayOnLinux wrapper
encoding = 'utf-8'

import os, getopt, sys, urllib, signal, string, time, webbrowser, gettext, locale, sys, shutil, subprocess, signal

try :
    os.environ["POL_OS"]
except :
    print "ERROR ! Please define POL_OS environment var first."
    os._exit(1)

if(os.environ["POL_OS"] == "Linux"):
    import wxversion
    wxversion.ensureMinimal('2.8')

import wx
import lib.lng as lng
import lib.playonlinux as playonlinux, lib.Variables as Variables
import guiv3 as gui, install, options, wine_versions as wver, sp, configure, threading, debug, gui_server



class MainWindow(wx.Frame):
    def __init__(self,parent,id,title):

        wx.Frame.__init__(self, parent, 1000, title, size = (0,0), style=wx.NO_BORDER|wx.WS_EX_BLOCK_EVENTS|wx.FRAME_NO_TASKBAR|wx.FRAME_SHAPED) # I know, that's not clean at all
        self.windowList = {}
        self.registeredPid = []
        self.myScript = None

        # Manage updater
        # SetupWindow timer. The server is in another thread and GUI must be run from the main thread
        self.SetupWindowTimer = wx.Timer(self, 1)
        self.Bind(wx.EVT_TIMER, self.SetupWindowAction, self.SetupWindowTimer)
        self.SetupWindowTimer_action = None
        self.SetupWindowTimer.Start(10)
        self.SetupWindowTimer_delay = 10
        self.windowOpened = 0

    def SetupWindowTimer_SendToGui(self, recvData):
        recvData = recvData.split("\t")
        while(self.SetupWindowTimer_action != None):
            time.sleep(0.1)
        self.SetupWindowTimer_action = recvData
        
    def SetupWindowAction(self, event):
        if(self.SetupWindowTimer_action != None):
            return gui_server.readAction(self)
        if(self.myScript.programrunning == False):
            self.POLDie()


    def POLDie(self):
        for pid in self.registeredPid:
            os.system("kill -9 -%d 2> /dev/null" % pid)
            os.system("kill -9 %d 2> /dev/null" % pid) 
        app.POLServer.closeServer()
        os._exit(0)

    def POLRestart(self):
        return False

    def ForceClose(self, signal, frame): # Catch SIGINT
        print "\nCtrl+C pressed. Killing all processes..."
        self.POLDie()

   
class Program(threading.Thread):
        def __init__(self):
                threading.Thread.__init__(self)
                self.start()
                self.programrunning = True

        def run(self):
                self.running = True
                self.chaine = ""
                print "Script started "+sys.argv[1]
                for arg in sys.argv[2:]:
                        self.chaine+=" \""+arg+"\""
                self.proc = subprocess.Popen("bash \""+sys.argv[1]+"\""+self.chaine, shell=True)
                while(self.running == True):
                        self.proc.poll()
                        if(self.proc.returncode != None):
                            self.programrunning = False
                        time.sleep(1)

class PlayOnLinuxApp(wx.App):
    def OnInit(self):
        lng.iLang()

        os.system("bash "+Variables.playonlinux_env+"/bash/startup")

        self.frame = MainWindow(None, -1, os.environ["APPLICATION_TITLE"])
        # Gui Server
        self.POLServer = gui_server.gui_server(self.frame)
        self.POLServer.start()
        
        i = 0
        while(os.environ["POL_PORT"] == "0"):
            time.sleep(0.01)
            if(i >= 300):
                 wx.MessageBox(_("{0} is not able to start POL_SetupWindow_server.").format(os.environ["APPLICATION_TITLE"]),_("Error"))
                 os._exit(0)
                 break
            i+=1 
        self.frame.myScript = Program()
   
        self.SetTopWindow(self.frame)
        self.frame.Show(True)
        self.frame.Hide()
        return True
  

lng.Lang()

app = PlayOnLinuxApp(redirect=False)
app.MainLoop()

########NEW FILE########
__FILENAME__ = test_versionlower
#!/usr/bin/python
import unittest
#import lib.playonlinux as playonlinux
import string

def VersionLower(version1, version2):
    version1 = string.split(version1, "-")
    version2 = string.split(version2, "-")

    try:
        if(version1[1] != ""):
            dev1 = True
    except:
        dev1 = False

    try:
        if(version1[2] != ""):
            dev2 = True
    except:
        dev2 = False

    if(version1[0] == version2[0]):
        if(dev1 == True and dev2 == False):
            return True
        else:
            return False

    version1 = [ int(digit) for digit in string.split(version1[0],".") ]
    version2 = [ int(digit) for digit in string.split(version2[0],".") ]

    if(version1[0] < version2[0]):
        return True
    elif(version1[0] == version2[0]):
        if(version1[1] < version2[1]):
            return True
        elif(version1[1] == version2[1]):
            if(version1[2] < version2[2]):
                return True
            else:
                return False
        else:
            return False
    else:
        return False

class TestVersionLower(unittest.TestCase):

    def test_major_greater(self):
        self.assertTrue(VersionLower("4.0.0", "5.0.0"))

    def test_major_equal(self):
        self.assertFalse(VersionLower("4.0.0", "4.0.0"))

    def test_major_lesser(self):
        self.assertFalse(VersionLower("4.0.0", "3.0.0"))

    def test_minor_greater(self):
        self.assertTrue(VersionLower("4.0.0", "4.1.0"))

    def test_minor_equal(self):
        self.assertFalse(VersionLower("4.1.0", "4.1.0"))

    def test_minor_lesser(self):
        self.assertFalse(VersionLower("4.1.0", "4.0.0"))

    def test_tag_greater(self):
        self.assertTrue(VersionLower("4.0.0", "4.0.1"))

    def test_tag_equal(self):
        self.assertFalse(VersionLower("4.0.1", "4.0.1"))

    def test_tag_lesser(self):
        self.assertFalse(VersionLower("4.0.1", "4.0.0"))

# 4.0.0-dev < 4.0.0 < 4.0.1-dev < 4.0.1
    def test_dev_released(self):
        self.assertTrue(VersionLower("4.0.0-dev", "4.0.0"))
        self.assertFalse(VersionLower("4.0.0", "4.0.0-dev"))

    def test_next_dev(self):
        self.assertTrue(VersionLower("4.0.0", "4.0.1-dev"))
        self.assertFalse(VersionLower("4.0.1-dev", "4.0.0"))

    def test_bug_genant(self):
        self.assertFalse(VersionLower("4.1.10-dev", "4.1.9"))

    def test_ca_marchait_avant(self):
        self.assertFalse(VersionLower("4.0.10-dev", "4.0.9"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
