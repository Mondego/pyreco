__FILENAME__ = buildPy2exe
#!/usr/bin/env python
#coding:utf8
from distutils.core import setup
from py2exe.build_exe import py2exe
from string import Template

import syncplay
import sys
import os
import subprocess

p = "C:\\Program Files (x86)\\NSIS\\makensis.exe" #TODO: how to move that into proper place, huh
NSIS_COMPILE = p if os.path.isfile(p) else "makensis.exe"
OUT_DIR = "syncplay v{}".format(syncplay.version)
SETUP_SCRIPT_PATH = "syncplay_setup.nsi"
NSIS_SCRIPT_TEMPLATE = r"""
  !include LogicLib.nsh
  !include nsDialogs.nsh
  !include FileFunc.nsh

  LoadLanguageFile "$${NSISDIR}\Contrib\Language files\English.nlf"
  LoadLanguageFile "$${NSISDIR}\Contrib\Language files\Polish.nlf"
  
  Name "Syncplay $version"
  OutFile "Syncplay $version Setup.exe"
  InstallDir $$PROGRAMFILES\Syncplay
  RequestExecutionLevel admin
  XPStyle on
  Icon resources\icon.ico ;Change DIR
  SetCompressor /SOLID lzma
     
  VIProductVersion "$version.0"
  VIAddVersionKey /LANG=$${LANG_ENGLISH} "ProductName" "Syncplay"
  VIAddVersionKey /LANG=$${LANG_ENGLISH} "FileVersion" "$version.0"
  VIAddVersionKey /LANG=$${LANG_ENGLISH} "LegalCopyright" "Syncplay"
  VIAddVersionKey /LANG=$${LANG_ENGLISH} "FileDescription" "Syncplay"
  
  VIAddVersionKey /LANG=$${LANG_POLISH} "ProductName" "Syncplay"
  VIAddVersionKey /LANG=$${LANG_POLISH} "FileVersion" "$version.0"
  VIAddVersionKey /LANG=$${LANG_POLISH} "LegalCopyright" "Syncplay"
  VIAddVersionKey /LANG=$${LANG_POLISH} "FileDescription" "Syncplay"
  
  LangString ^Associate $${LANG_ENGLISH} "Associate Syncplay with multimedia files."
  LangString ^VLC $${LANG_ENGLISH} "Install Syncplay interface for VLC (requires VLC 2.x.x)"
  LangString ^Shortcut $${LANG_ENGLISH} "Create Shortcuts in following locations:"
  LangString ^StartMenu $${LANG_ENGLISH} "Start Menu"
  LangString ^Desktop $${LANG_ENGLISH} "Desktop"
  LangString ^QuickLaunchBar $${LANG_ENGLISH} "Quick Launch Bar"
  LangString ^UninstConfig $${LANG_ENGLISH} "Delete configuration file."
    
  LangString ^Associate $${LANG_POLISH} "Skojarz Syncplaya z multimediami"
  LangString ^VLC $${LANG_POLISH} "Zainstaluj interface Syncplaya dla VLC(wymaga VLC 2.0.X)"
  LangString ^Shortcut $${LANG_POLISH} "Utworz skroty w nastepujacych miejscach:"
  LangString ^StartMenu $${LANG_POLISH} "Menu Start"
  LangString ^Desktop $${LANG_POLISH} "Pulpit"
  LangString ^QuickLaunchBar $${LANG_POLISH} "Pasek szybkiego uruchamiania"
  LangString ^UninstConfig $${LANG_POLISH} "Usun plik konfiguracyjny."
  
  PageEx license
    LicenseData resources\license.txt
  PageExEnd
  Page custom DirectoryCustom DirectoryCustomLeave
  Page instFiles
  
  UninstPage custom un.installConfirm un.installConfirmLeave
  UninstPage instFiles
  
  Var Dialog
  Var Icon_Syncplay
  Var Icon_Syncplay_Handle
  Var CheckBox_Associate
  Var CheckBox_VLC
  Var CheckBox_StartMenuShortcut
  Var CheckBox_DesktopShortcut
  Var CheckBox_QuickLaunchShortcut
  Var CheckBox_Associate_State
  Var CheckBox_VLC_State
  Var CheckBox_StartMenuShortcut_State
  Var CheckBox_DesktopShortcut_State
  Var CheckBox_QuickLaunchShortcut_State
  Var Button_Browse
  Var Directory
  Var GroupBox_DirSub
  Var Label_Text
  Var Label_Shortcut
  Var Label_Size
  Var Label_Space
  Var Text_Directory
  
  Var Uninst_Dialog
  Var Uninst_Icon
  Var Uninst_Icon_Handle
  Var Uninst_Label_Directory
  Var Uninst_Label_Text
  Var Uninst_Text_Directory
  Var Uninst_CheckBox_Config
  Var Uninst_CheckBox_Config_State
  
  Var Size
  Var SizeHex
  Var AvailibleSpace
  Var AvailibleSpaceGiB
  Var Drive
  Var VLC_Directory
  Var VLC_Version
    
  !macro APP_ASSOCIATE EXT FileCLASS DESCRIPTION COMMANDTEXT COMMAND
    WriteRegStr HKCR ".$${EXT}" "" "$${FileCLASS}"
    WriteRegStr HKCR "$${FileCLASS}" "" `$${DESCRIPTION}`
    WriteRegStr HKCR "$${FileCLASS}\shell" "" "open"
    WriteRegStr HKCR "$${FileCLASS}\shell\open" "" `$${COMMANDTEXT}`
    WriteRegStr HKCR "$${FileCLASS}\shell\open\command" "" `$${COMMAND}`
  !macroend
  
  !macro APP_UNASSOCIATE EXT FileCLASS
    ; Backup the previously associated File class
    ReadRegStr $$R0 HKCR ".$${EXT}" `$${FileCLASS}_backup`
    WriteRegStr HKCR ".$${EXT}" "" "$$R0"
    DeleteRegKey HKCR `$${FileCLASS}`
  !macroend
  
  !macro ASSOCIATE EXT
    !insertmacro APP_ASSOCIATE "$${EXT}" "Syncplay.$${EXT}" "$$INSTDIR\Syncplay.exe,%1%" \
    "Open with Syncplay" "$$INSTDIR\Syncplay.exe $$\"%1$$\""
  !macroend
  
  !macro UNASSOCIATE EXT
    !insertmacro APP_UNASSOCIATE "$${EXT}" "Syncplay.$${EXT}"
  !macroend
  
  ;Prevents from running more than one instance of installer and sets default state of checkboxes
  Function .onInit
    System::Call 'kernel32::CreateMutexA(i 0, i 0, t "myMutex") i .r1 ?e'
    Pop $$R0
    StrCmp $$R0 0 +3
    MessageBox MB_OK|MB_ICONEXCLAMATION "The installer is already running."
      Abort
        
    StrCpy $$CheckBox_Associate_State $${BST_CHECKED}
    StrCpy $$CheckBox_StartMenuShortcut_State $${BST_CHECKED}
    ReadRegStr $$VLC_Version HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player" "VersionMajor"
    $${If} $$VLC_Version == "2"
      StrCpy $$CheckBox_VLC_State $${BST_CHECKED}
    $${EndIf}
    
    Call GetSize
    Call DriveSpace
    Call Language
  FunctionEnd
     
  ;Language selection dialog
  Function Language
    Push ""
    Push $${LANG_ENGLISH}
    Push English
    Push $${LANG_POLISH}
    Push Polski
    Push A ; A means auto count languages
    LangDLL::LangDialog "Installer Language" "Please select the language of the installer"
    Pop $$LANGUAGE
    StrCmp $$LANGUAGE "cancel" 0 +2
      Abort
  FunctionEnd
  
  Function DirectoryCustom
    
    nsDialogs::Create 1018
    Pop $$Dialog
    
    GetFunctionAddress $$R8 DirectoryCustomLeave
    nsDialogs::OnBack $$R8
    
    $${NSD_CreateIcon} 0u 0u 22u 20u ""
    Pop $$Icon_Syncplay
    $${NSD_SetIconFromInstaller} $$Icon_Syncplay $$Icon_Syncplay_Handle
    
    $${NSD_CreateLabel} 25u 0u 241u 34u "$$(^DirText)"
    Pop $$Label_Text
    
    $${NSD_CreateText} 8u 38u 187u 12u "$$INSTDIR" 
    Pop $$Text_Directory
    $${NSD_SetFocus} $$Text_Directory
    
    $${NSD_CreateBrowseButton} 202u 37u 55u 14u "$$(^BrowseBtn)"
    Pop $$Button_Browse
    $${NSD_OnClick} $$Button_Browse DirectoryBrowseDialog
    
    $${NSD_CreateGroupBox} 1u 27u 264u 30u "$$(^DirSubText)"
    Pop $$GroupBox_DirSub

    $${NSD_CreateLabel} 0u 111u 265u 8u "$$(^SpaceRequired)$$SizeMB"
    Pop $$Label_Size
    
    $${NSD_CreateLabel} 0u 122u 265u 8u "$$(^SpaceAvailable)$$AvailibleSpaceGiB.$$AvailibleSpaceGB"
    Pop $$Label_Space
    
    $${NSD_CreateCheckBox} 8u 59u 187u 10u "$$(^Associate)"
    Pop $$CheckBox_Associate
    
    $${NSD_CreateCheckBox} 8u 72u 250u 10u "$$(^VLC)"
    Pop $$CheckBox_VLC
    
    $${NSD_CreateLabel} 8u 85u 187u 10u "$$(^Shortcut)"
    Pop $$Label_Shortcut
    
    $${NSD_CreateCheckbox} 8u 98u 50u 10u "$$(^StartMenu)"
    Pop $$CheckBox_StartMenuShortcut

    $${NSD_CreateCheckbox} 68u 98u 50u 10u "$$(^Desktop)"
    Pop $$CheckBox_DesktopShortcut
    
    $${NSD_CreateCheckbox} 128u 98u 150u 10u "$$(^QuickLaunchBar)"
    Pop $$CheckBox_QuickLaunchShortcut
    
    $${If} $$CheckBox_Associate_State == $${BST_CHECKED}
      $${NSD_Check} $$CheckBox_Associate
    $${EndIf}

    $${If} $$CheckBox_VLC_State == $${BST_CHECKED}
    	$${NSD_Check} $$CheckBox_VLC
    $${EndIf}
    
    $${If} $$CheckBox_StartMenuShortcut_State == $${BST_CHECKED}
    	$${NSD_Check} $$CheckBox_StartMenuShortcut
    $${EndIf}
    
    $${If} $$CheckBox_DesktopShortcut_State == $${BST_CHECKED}
    	$${NSD_Check} $$CheckBox_DesktopShortcut
    $${EndIf}
    
    $${If} $$CheckBox_QuickLaunchShortcut_State == $${BST_CHECKED}
    	$${NSD_Check} $$CheckBox_QuickLaunchShortcut
    $${EndIf}
    
    ReadRegStr $$VLC_Version HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player" "VersionMajor"
    $${If} $$VLC_Version != "2"
      EnableWindow $$CheckBox_VLC 0
    $${EndIf}
    nsDialogs::Show

    $${NSD_FreeIcon} $$Icon_Syncplay_Handle

  FunctionEnd
  
  Function DirectoryCustomLeave
    $${NSD_GetText} $$Text_Directory $$INSTDIR
    $${NSD_GetState} $$CheckBox_Associate $$CheckBox_Associate_State
    $${NSD_GetState} $$CheckBox_VLC $$CheckBox_VLC_State
    $${NSD_GetState} $$CheckBox_StartMenuShortcut $$CheckBox_StartMenuShortcut_State
    $${NSD_GetState} $$CheckBox_DesktopShortcut $$CheckBox_DesktopShortcut_State
    $${NSD_GetState} $$CheckBox_QuickLaunchShortcut $$CheckBox_QuickLaunchShortcut_State
  FunctionEnd
  
  Function DirectoryBrowseDialog
    nsDialogs::SelectFolderDialog $$(^DirBrowseText) 
    Pop $$Directory
    $${If} $$Directory != error
    StrCpy $$INSTDIR $$Directory
    $${NSD_SetText} $$Text_Directory $$INSTDIR
    Call DriveSpace
    $${NSD_SetText} $$Label_Space "$$(^SpaceAvailable)$$AvailibleSpaceGiB.$$AvailibleSpaceGB"
    $${EndIf}
    Abort
  FunctionEnd
  
  Function GetSize
    StrCpy $$Size "$totalSize"
    IntOp $$Size $$Size / 1024
    IntFmt $$SizeHex "0x%08X" $$Size
    IntOp $$Size $$Size / 1024
  FunctionEnd
  
  ;Calculates Free Space on HDD
  Function DriveSpace
    StrCpy $$Drive $$INSTDIR 1
    $${DriveSpace} "$$Drive:\" "/D=F /S=M" $$AvailibleSpace
    IntOp $$AvailibleSpaceGiB $$AvailibleSpace / 1024
    IntOp $$AvailibleSpace $$AvailibleSpace % 1024
    IntOp $$AvailibleSpace $$AvailibleSpace / 102
  FunctionEnd
  
  Function InstallOptions
    $${If} $$CheckBox_Associate_State == $${BST_CHECKED}
      Call Associate
      DetailPrint "Associated Syncplay with multimedia files"
    $${EndIf}
    
    $${If} $$CheckBox_StartMenuShortcut_State == $${BST_CHECKED}
      CreateDirectory $$SMPROGRAMS\Syncplay
      CreateShortCut "$$SMPROGRAMS\Syncplay\Syncplay.lnk" "$$INSTDIR\Syncplay.exe" "" 
      CreateShortCut "$$SMPROGRAMS\Syncplay\Uninstall.lnk" "$$INSTDIR\Uninstall.exe" ""
      WriteINIStr "$$SMPROGRAMS\Syncplay\SyncplayWebsite.url" "InternetShortcut" "URL" "http://syncplay.pl"
    $${EndIf}
    
    $${If} $$CheckBox_DesktopShortcut_State == $${BST_CHECKED}
      CreateShortCut "$$DESKTOP\Syncplay.lnk" "$$INSTDIR\Syncplay.exe" ""
    $${EndIf}
    
    $${If} $$CheckBox_QuickLaunchShortcut_State == $${BST_CHECKED}
      CreateShortCut "$$QUICKLAUNCH\Syncplay.lnk" "$$INSTDIR\Syncplay.exe" ""
    $${EndIf}
    
    $${If} $$CheckBox_VLC_State == $${BST_CHECKED}
      ReadRegStr $$VLC_Directory HKLM "Software\VideoLAN\VLC" "InstallDir"
      SetOutPath $$VLC_Directory\lua\intf
      File resources\lua\intf\syncplay.lua
    $${EndIf}
  FunctionEnd
    
  ;Associates extensions with Syncplay
  Function Associate
    !insertmacro ASSOCIATE avi
    !insertmacro ASSOCIATE mpg
    !insertmacro ASSOCIATE mpeg
    !insertmacro ASSOCIATE mpe
    !insertmacro ASSOCIATE m1v
    !insertmacro ASSOCIATE m2v
    !insertmacro ASSOCIATE mpv2
    !insertmacro ASSOCIATE mp2v
    !insertmacro ASSOCIATE mkv
    !insertmacro ASSOCIATE mp4
    !insertmacro ASSOCIATE m4v
    !insertmacro ASSOCIATE mp4v
    !insertmacro ASSOCIATE 3gp
    !insertmacro ASSOCIATE 3gpp
    !insertmacro ASSOCIATE 3g2
    !insertmacro ASSOCIATE 3pg2
    !insertmacro ASSOCIATE flv
    !insertmacro ASSOCIATE f4v
    !insertmacro ASSOCIATE rm
    !insertmacro ASSOCIATE wmv
    !insertmacro ASSOCIATE swf
    !insertmacro ASSOCIATE rmvb
    !insertmacro ASSOCIATE divx
    !insertmacro ASSOCIATE amv
  FunctionEnd
  
  Function WriteRegistry
    Call GetSize
    WriteRegStr HKLM SOFTWARE\Syncplay "Install_Dir" "$$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "DisplayName" "Syncplay"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "InstallLocation" "$$INSTDIR" 
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "UninstallString" '"$$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "DisplayIcon" "$$INSTDIR\resources\icon.ico"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "Publisher" "Syncplay"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "DisplayVersion" "$version"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "URLInfoAbout" "http://syncplay.pl/"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "NoRepair" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "EstimatedSize" "$$SizeHex"
  FunctionEnd
    
  Function un.installConfirm
    nsDialogs::Create 1018
    Pop $$Uninst_Dialog
    
    $${NSD_CreateIcon} 0u 1u 22u 20u ""
    Pop $$Uninst_Icon
    $${NSD_SetIconFromInstaller} $$Uninst_Icon $$Uninst_Icon_Handle
    
    $${NSD_CreateLabel} 0u 45u 55u 8u "$$(^UninstallingSubText)"
    Pop $$Uninst_Label_Directory
    
    $${NSD_CreateLabel} 25u 0u 241u 34u "$$(^UninstallingText)"
    Pop $$Uninst_Label_Text
    
    ReadRegStr $$INSTDIR HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay" "InstallLocation"
    $${NSD_CreateText} 56u 43u 209u 12u "$$INSTDIR" 
    Pop $$Uninst_Text_Directory
    EnableWindow $$Uninst_Text_Directory 0
    
    $${NSD_CreateCheckBox} 0u 60u 250u 10u "$$(^UninstConfig)"
    Pop $$Uninst_CheckBox_Config
    
    
    nsDialogs::Show
    $${NSD_FreeIcon} $$Uninst_Icon_Handle
  FunctionEnd
  
  Function un.installConfirmLeave
    $${NSD_GetState} $$Uninst_CheckBox_Config $$Uninst_CheckBox_Config_State
  FunctionEnd
  
  Function un.AssociateDel
    !insertmacro UNASSOCIATE avi
    !insertmacro UNASSOCIATE mpg
    !insertmacro UNASSOCIATE mpeg
    !insertmacro UNASSOCIATE mpe
    !insertmacro UNASSOCIATE m1v
    !insertmacro UNASSOCIATE m2v
    !insertmacro UNASSOCIATE mpv2
    !insertmacro UNASSOCIATE mp2v
    !insertmacro UNASSOCIATE mkv
    !insertmacro UNASSOCIATE mp4
    !insertmacro UNASSOCIATE m4v
    !insertmacro UNASSOCIATE mp4v
    !insertmacro UNASSOCIATE 3gp
    !insertmacro UNASSOCIATE 3gpp
    !insertmacro UNASSOCIATE 3g2
    !insertmacro UNASSOCIATE 3pg2
    !insertmacro UNASSOCIATE flv
    !insertmacro UNASSOCIATE f4v
    !insertmacro UNASSOCIATE rm
    !insertmacro UNASSOCIATE wmv
    !insertmacro UNASSOCIATE swf
    !insertmacro UNASSOCIATE rmvb
    !insertmacro UNASSOCIATE divx
    !insertmacro UNASSOCIATE amv      
  FunctionEnd
  
  Function un.InstallOptions
    Delete $$SMPROGRAMS\Syncplay\Syncplay.lnk
    Delete $$SMPROGRAMS\Syncplay\Uninstall.lnk
    Delete $$SMPROGRAMS\Syncplay\SyncplayWebsite.url
    RMDir $$SMPROGRAMS\Syncplay
    Delete $$DESKTOP\Syncplay.lnk
    Delete $$QUICKLAUNCH\Syncplay.lnk
    ReadRegStr $$VLC_Directory HKLM "Software\VideoLAN\VLC" "InstallDir"
    Delete $$VLC_Directory\lua\intf\syncplay.lua
  FunctionEnd
  
  Section "Install"
    SetOverwrite on
    SetOutPath $$INSTDIR
    WriteUninstaller uninstall.exe
    
    $installFiles
    
    Call InstallOptions
    Call WriteRegistry
  SectionEnd
     
  Section "Uninstall"
    Call un.AssociateDel
    Call un.InstallOptions
    $uninstallFiles
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Syncplay"
    DeleteRegKey HKLM SOFTWARE\Syncplay
    Delete $$INSTDIR\uninstall.exe
    RMDir $$INSTDIR\resources
    RMDir $$INSTDIR\lib
    RMDir $$INSTDIR

    $${If} $$Uninst_CheckBox_Config_State == $${BST_CHECKED}
      Delete $$APPDATA\.syncplay
    $${EndIf}
  SectionEnd
"""

class NSISScript(object):
    def create(self):
        fileList, totalSize = self.getBuildDirContents(OUT_DIR)
        print "Total size eq: {}".format(totalSize)
        installFiles = self.prepareInstallListTemplate(fileList) 
        uninstallFiles = self.prepareDeleteListTemplate(fileList)
        
        if(os.path.isfile(SETUP_SCRIPT_PATH)):
            raise RuntimeError("Cannot create setup script, file exists at {}".format(SETUP_SCRIPT_PATH))
        contents =  Template(NSIS_SCRIPT_TEMPLATE).substitute(
                                                              version = syncplay.version,
                                                              uninstallFiles = uninstallFiles,
                                                              installFiles = installFiles,
                                                              totalSize = totalSize,
                                                              )
        with open(SETUP_SCRIPT_PATH, "w") as outfile:
            outfile.write(contents)
        
    def compile(self):
        if(not os.path.isfile(NSIS_COMPILE)):
            return "makensis.exe not found, won't create the installer"
        subproc = subprocess.Popen([NSIS_COMPILE, SETUP_SCRIPT_PATH], env=os.environ)
        subproc.communicate()
        retcode = subproc.returncode
        os.remove(SETUP_SCRIPT_PATH)
        if retcode:
            raise RuntimeError("NSIS compilation return code: %d" % retcode)
   
    def getBuildDirContents(self, path):
        fileList = {}
        totalSize = 0
        for root, _, files in os.walk(path):
            totalSize += sum(os.path.getsize(os.path.join(root, file_)) for file_ in files)
            for file_ in files:
                new_root = root.replace(OUT_DIR, "").strip("\\")
                if(not fileList.has_key(new_root)):
                    fileList[new_root] = []
                fileList[new_root].append(file_)
        return fileList, totalSize          
    
    def prepareInstallListTemplate(self, fileList):
        create = []
        for dir_ in fileList.iterkeys():
            create.append('SetOutPath "$INSTDIR\\{}"'.format(dir_))
            for file_ in fileList[dir_]:
                create.append('FILE "{}\\{}\\{}"'.format(OUT_DIR, dir_, file_))
        return "\n".join(create)
    
    def prepareDeleteListTemplate(self, fileList):
        delete = []
        for dir_ in fileList.iterkeys():
            for file_ in fileList[dir_]:
                delete.append('DELETE "$INSTDIR\\{}\\{}"'.format(dir_, file_))
            delete.append('RMdir "$INSTDIR\\{}"'.format(file_))    
        return "\n".join(delete)
    
class build_installer(py2exe):
    def run(self):
        py2exe.run(self)
        script = NSISScript()
        script.create()
        print "*** compiling the NSIS setup script***"
        script.compile()
        print "*** DONE ***"

guiIcons = ['resources/accept.png', 'resources/arrow_undo.png', 'resources/clock_go.png',
     'resources/control_pause_blue.png', 'resources/cross.png', 'resources/door_in.png',
     'resources/folder_explore.png', 'resources/help.png', 'resources/table_refresh.png',
     'resources/timeline_marker.png','resources/control_play_blue.png',
     'resources/mpc-hc.png','resources/mpc-hc64.png','resources/mplayer.png',
     'resources/mpv.png','resources/vlc.png'
    ]
resources = ["resources/icon.ico", "resources/syncplay.png"]
resources.extend(guiIcons)
intf_resources = ["resources/lua/intf/syncplay.lua"]

common_info = dict(
    name='Syncplay',
    version=syncplay.version,
    author='Uriziel',
    author_email='urizieli@gmail.com',
    description='Syncplay',
)
    
info = dict(
    common_info,
    windows=[{"script":"syncplayClient.py", "icon_resources":[(1, "resources\\icon.ico")], 'dest_base': "Syncplay"}],
    console=['syncplayServer.py'],
    options={'py2exe': {
                         'dist_dir': OUT_DIR,
                         'packages': 'PySide.QtUiTools',
                         'includes': 'twisted, sys, encodings, datetime, os, time, math, PySide, liburl',
                         'excludes': 'venv, _ssl, doctest, pdb, unittest, win32clipboard, win32file, win32pdh, win32security, win32trace, win32ui, winxpgui, win32pipe, win32process, Tkinter',
                         'dll_excludes': 'msvcr71.dll, MSVCP90.dll, POWRPROF.dll',
                         'optimize': 2,
                         'compressed': 1
                         }
             },
    data_files = [("resources", resources),("resources/lua/intf", intf_resources)],
    zipfile = "lib/libsync",
    cmdclass = {"py2exe": build_installer},               
)

sys.argv.extend(['py2exe', '-p win32com ', '-i twisted.web.resource'])
setup(**info)

########NEW FILE########
__FILENAME__ = client
import hashlib
import os.path
import time
import re
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor, task
from syncplay.protocols import SyncClientProtocol
from syncplay import utils, constants
from syncplay.messages import getMessage
import threading
from syncplay.constants import PRIVACY_SENDHASHED_MODE, PRIVACY_DONTSEND_MODE, \
    PRIVACY_HIDDENFILENAME, FILENAME_STRIP_REGEX
import collections

class SyncClientFactory(ClientFactory):
    def __init__(self, client, retry=constants.RECONNECT_RETRIES):
        self._client = client
        self.retry = retry
        self._timesTried = 0
        self.reconnecting = False

    def buildProtocol(self, addr):
        self._timesTried = 0
        return SyncClientProtocol(self._client)

    def startedConnecting(self, connector):
        destination = connector.getDestination()
        message = getMessage("en", "connection-attempt-notification").format(destination.host, destination.port)
        self._client.ui.showMessage(message)

    def clientConnectionLost(self, connector, reason):
        if self._timesTried == 0:
            self._client.onDisconnect()
        if self._timesTried < self.retry:
            self._timesTried += 1
            self._client.ui.showMessage(getMessage("en", "reconnection-attempt-notification"))
            self.reconnecting = True
            reactor.callLater(0.1 * (2 ** self._timesTried), connector.connect)
        else:
            message = getMessage("en", "disconnection-notification")
            self._client.ui.showErrorMessage(message)

    def clientConnectionFailed(self, connector, reason):
        if not self.reconnecting:
            reactor.callLater(0.1, self._client.ui.showErrorMessage, getMessage("en", "connection-failed-notification"), True)
            reactor.callLater(0.1, self._client.stop, True)
        else:
            self.clientConnectionLost(connector, reason)

    def resetRetrying(self):
        self._timesTried = 0

    def stopRetrying(self):
        self._timesTried = self.retry

class SyncplayClient(object):
    def __init__(self, playerClass, ui, config):
        self.lastLeftTime = 0
        self.lastLeftUser = u""
        self.protocolFactory = SyncClientFactory(self)
        self.ui = UiManager(self, ui)
        self.userlist = SyncplayUserlist(self.ui, self)
        self._protocol = None
        self._player = None
        if(config['room'] == None or config['room'] == ''):
            config['room'] = config['name']  # ticket #58
        self.defaultRoom = config['room']
        self.playerPositionBeforeLastSeek = 0.0
        self.setUsername(config['name'])
        self.setRoom(config['room'])
        if(config['password']):
            config['password'] = hashlib.md5(config['password']).hexdigest()
        self._serverPassword = config['password']
        if(not config['file']):
            self.__getUserlistOnLogon = True
        else:
            self.__getUserlistOnLogon = False
        self._playerClass = playerClass
        self._config = config

        self._running = False
        self._askPlayerTimer = None

        self._lastPlayerUpdate = None
        self._playerPosition = 0.0
        self._playerPaused = True

        self._lastGlobalUpdate = None
        self._globalPosition = 0.0
        self._globalPaused = 0.0
        self._userOffset = 0.0
        self._speedChanged = False

        self._warnings = self._WarningManager(self._player, self.userlist, self.ui)
        if constants.LIST_RELATIVE_CONFIGS and self._config.has_key('loadedRelativePaths') and self._config['loadedRelativePaths']:
            self.ui.showMessage(getMessage("en", "relative-config-notification").format("; ".join(self._config['loadedRelativePaths'])), noPlayer=True, noTimestamp=True)

    def initProtocol(self, protocol):
        self._protocol = protocol

    def destroyProtocol(self):
        if(self._protocol):
            self._protocol.drop()
        self._protocol = None

    def initPlayer(self, player):
        self._player = player
        self.scheduleAskPlayer()

    def scheduleAskPlayer(self, when=constants.PLAYER_ASK_DELAY):
        self._askPlayerTimer = task.LoopingCall(self.askPlayer)
        self._askPlayerTimer.start(when)

    def askPlayer(self):
        if(not self._running):
            return
        if(self._player):
            self._player.askForStatus()
        self.checkIfConnected()

    def checkIfConnected(self):
        if(self._lastGlobalUpdate and self._protocol and time.time() - self._lastGlobalUpdate > constants.PROTOCOL_TIMEOUT):
            self._lastGlobalUpdate = None
            self.ui.showErrorMessage(getMessage("en", "server-timeout-error"))
            self._protocol.drop()
            return False
        return True

    def _determinePlayerStateChange(self, paused, position):
        pauseChange = self.getPlayerPaused() != paused and self.getGlobalPaused() != paused
        _playerDiff = abs(self.getPlayerPosition() - position)
        _globalDiff = abs(self.getGlobalPosition() - position)
        seeked = _playerDiff > constants.SEEK_THRESHOLD and _globalDiff > constants.SEEK_THRESHOLD
        return pauseChange, seeked

    def updatePlayerStatus(self, paused, position):
        position -= self.getUserOffset()
        pauseChange, seeked = self._determinePlayerStateChange(paused, position)
        self._playerPosition = position
        self._playerPaused = paused
        if(self._lastGlobalUpdate):
            self._lastPlayerUpdate = time.time()
            if((pauseChange or seeked) and self._protocol):
                if(seeked):
                    self.playerPositionBeforeLastSeek = self.getGlobalPosition()
                self._protocol.sendState(self.getPlayerPosition(), self.getPlayerPaused(), seeked, None, True)

    def getLocalState(self):
        paused = self.getPlayerPaused()
        if self._config['dontSlowDownWithMe']:
            position = self.getGlobalPosition()
        else:
            position = self.getPlayerPosition()
        pauseChange, _ = self._determinePlayerStateChange(paused, position)
        if(self._lastGlobalUpdate):
            return position, paused, _, pauseChange
        else:
            return None, None, None, None

    def _initPlayerState(self, position, paused):
        if(self.userlist.currentUser.file):
            self.setPosition(position)
            self._player.setPaused(paused)
            madeChangeOnPlayer = True
            return madeChangeOnPlayer

    def _rewindPlayerDueToTimeDifference(self, position, setBy):
        hideFromOSD = not constants.SHOW_SAME_ROOM_OSD
        self.setPosition(position)
        self.ui.showMessage(getMessage("en", "rewind-notification").format(setBy), hideFromOSD)
        madeChangeOnPlayer = True
        return madeChangeOnPlayer

    def _serverUnpaused(self, setBy):
        hideFromOSD = not constants.SHOW_SAME_ROOM_OSD
        self._player.setPaused(False)
        madeChangeOnPlayer = True
        self.ui.showMessage(getMessage("en", "unpause-notification").format(setBy), hideFromOSD)
        return madeChangeOnPlayer

    def _serverPaused(self, setBy):
        hideFromOSD = not constants.SHOW_SAME_ROOM_OSD
        if constants.SYNC_ON_PAUSE == True:
            self.setPosition(self.getGlobalPosition())
        self._player.setPaused(True)
        madeChangeOnPlayer = True
        if (self.lastLeftTime < time.time() - constants.OSD_DURATION) or (hideFromOSD == True):
            self.ui.showMessage(getMessage("en", "pause-notification").format(setBy), hideFromOSD)
        else:
            self.ui.showMessage(getMessage("en", "left-paused-notification").format(self.lastLeftUser, setBy), hideFromOSD)
        return madeChangeOnPlayer

    def _serverSeeked(self, position, setBy):
        hideFromOSD = not constants.SHOW_SAME_ROOM_OSD
        if(self.getUsername() <> setBy):
            self.playerPositionBeforeLastSeek = self.getPlayerPosition()
            self.setPosition(position)
            madeChangeOnPlayer = True
        else:
            madeChangeOnPlayer = False
        message = getMessage("en", "seek-notification").format(setBy, utils.formatTime(self.playerPositionBeforeLastSeek), utils.formatTime(position))
        self.ui.showMessage(message, hideFromOSD)
        return madeChangeOnPlayer

    def _slowDownToCoverTimeDifference(self, diff, setBy):
        hideFromOSD = not constants.SHOW_SLOWDOWN_OSD
        if(constants.SLOWDOWN_KICKIN_THRESHOLD < diff and not self._speedChanged):
            self._player.setSpeed(constants.SLOWDOWN_RATE)
            self._speedChanged = True
            self.ui.showMessage(getMessage("en", "slowdown-notification").format(setBy), hideFromOSD)
        elif(self._speedChanged and diff < constants.SLOWDOWN_RESET_THRESHOLD):
            self._player.setSpeed(1.00)
            self._speedChanged = False
            self.ui.showMessage(getMessage("en", "revert-notification"), hideFromOSD)
        madeChangeOnPlayer = True
        return madeChangeOnPlayer

    def _changePlayerStateAccordingToGlobalState(self, position, paused, doSeek, setBy):
        madeChangeOnPlayer = False
        pauseChanged = paused != self.getGlobalPaused()
        diff = self.getPlayerPosition() - position
        if(self._lastGlobalUpdate is None):
            madeChangeOnPlayer = self._initPlayerState(position, paused)
        self._globalPaused = paused
        self._globalPosition = position
        self._lastGlobalUpdate = time.time()
        if (doSeek):
            madeChangeOnPlayer = self._serverSeeked(position, setBy)
        if (diff > constants.REWIND_THRESHOLD and not doSeek and not self._config['rewindOnDesync'] == False):
            madeChangeOnPlayer = self._rewindPlayerDueToTimeDifference(position, setBy)
        if (self._player.speedSupported and not doSeek and not paused and not self._config['slowOnDesync'] == False):
            madeChangeOnPlayer = self._slowDownToCoverTimeDifference(diff, setBy)
        if (paused == False and pauseChanged):
            madeChangeOnPlayer = self._serverUnpaused(setBy)
        elif (paused == True and pauseChanged):
            madeChangeOnPlayer = self._serverPaused(setBy)
        return madeChangeOnPlayer

    def _executePlaystateHooks(self, position, paused, doSeek, setBy, messageAge):
        if(self.userlist.hasRoomStateChanged() and not paused):
            self._warnings.checkWarnings()
            self.userlist.roomStateConfirmed()

    def updateGlobalState(self, position, paused, doSeek, setBy, messageAge):
        if(self.__getUserlistOnLogon):
            self.__getUserlistOnLogon = False
            self.getUserList()
        madeChangeOnPlayer = False
        if(not paused):
            position += messageAge
        if(self._player):
            madeChangeOnPlayer = self._changePlayerStateAccordingToGlobalState(position, paused, doSeek, setBy)
        if(madeChangeOnPlayer):
            self.askPlayer()
        self._executePlaystateHooks(position, paused, doSeek, setBy, messageAge)

    def getUserOffset(self):
        return self._userOffset

    def setUserOffset(self, time):
        self._userOffset = time
        self.setPosition(self.getGlobalPosition())
        self.ui.showMessage(getMessage("en", "current-offset-notification").format(self._userOffset))

    def onDisconnect(self):
        if(self._config['pauseOnLeave']):
            self.setPaused(True)

    def removeUser(self, username):
        if(self.userlist.isUserInYourRoom(username)):
            self.onDisconnect()
        self.userlist.removeUser(username)

    def getPlayerPosition(self):
        if(not self._lastPlayerUpdate):
            if(self._lastGlobalUpdate):
                return self.getGlobalPosition()
            else:
                return 0.0
        position = self._playerPosition
        if(not self._playerPaused):
            diff = time.time() - self._lastPlayerUpdate
            position += diff
        return position

    def getPlayerPaused(self):
        if(not self._lastPlayerUpdate):
            if(self._lastGlobalUpdate):
                return self.getGlobalPaused()
            else:
                return True
        return self._playerPaused

    def getGlobalPosition(self):
        if not self._lastGlobalUpdate:
            return 0.0
        position = self._globalPosition
        if not self._globalPaused:
            position += time.time() - self._lastGlobalUpdate
        return position

    def getGlobalPaused(self):
        if(not self._lastGlobalUpdate):
            return True
        return self._globalPaused

    def updateFile(self, filename, duration, path):
        if not path:
            return
        try:
            size = os.path.getsize(path)
        except OSError:  # file not accessible (stream?)
            size = 0
        rawfilename = filename
        filename, size = self.__executePrivacySettings(filename, size)
        self.userlist.currentUser.setFile(filename, duration, size)
        self.sendFile()

    def __executePrivacySettings(self, filename, size):
        if (self._config['filenamePrivacyMode'] == PRIVACY_SENDHASHED_MODE):
            filename = utils.hashFilename(filename)
        elif (self._config['filenamePrivacyMode'] == PRIVACY_DONTSEND_MODE):
            filename = PRIVACY_HIDDENFILENAME
        if (self._config['filesizePrivacyMode'] == PRIVACY_SENDHASHED_MODE):
            size = utils.hashFilesize(size)
        elif (self._config['filesizePrivacyMode'] == PRIVACY_DONTSEND_MODE):
            size = 0
        return filename, size

    def sendFile(self):
        file_ = self.userlist.currentUser.file
        if(self._protocol and self._protocol.logged and file_):
            self._protocol.sendFileSetting(file_)

    def setUsername(self, username):
        if username and username <> "":
            self.userlist.currentUser.username = username
        else:
            import random
            random.seed()
            random_number = random.randrange(1000, 9999)
            self.userlist.currentUser.username = "Anonymous" + str(random_number)

    def getUsername(self):
        return self.userlist.currentUser.username

    def setRoom(self, roomName):
        self.userlist.currentUser.room = roomName

    def sendRoom(self):
        room = self.userlist.currentUser.room
        if(self._protocol and self._protocol.logged and room):
            self._protocol.sendRoomSetting(room)
            self.getUserList()

    def getRoom(self):
        return self.userlist.currentUser.room

    def getUserList(self):
        if(self._protocol and self._protocol.logged):
            self._protocol.sendList()

    def showUserList(self):
        self.userlist.showUserList()

    def getPassword(self):
        return self._serverPassword

    def setPosition(self, position):
        position += self.getUserOffset()
        if(self._player and self.userlist.currentUser.file):
            if(position < 0):
                position = 0
                self._protocol.sendState(self.getPlayerPosition(), self.getPlayerPaused(), True, None, True)
            self._player.setPosition(position)

    def setPaused(self, paused):
        if(self._player and self.userlist.currentUser.file):
            self._player.setPaused(paused)

    def start(self, host, port):
        if self._running:
            return
        self._running = True
        if self._playerClass:
            self._playerClass.run(self, self._config['playerPath'], self._config['file'], self._config['playerArgs'])
            self._playerClass = None
        self.protocolFactory = SyncClientFactory(self)
        port = int(port)
        reactor.connectTCP(host, port, self.protocolFactory)
        reactor.run()

    def stop(self, promptForAction=False):
        if not self._running:
            return
        self._running = False
        if self.protocolFactory:
            self.protocolFactory.stopRetrying()
        self.destroyProtocol()
        if self._player:
            self._player.drop()
        if self.ui:
            self.ui.drop()
        reactor.callLater(0.1, reactor.stop)
        if(promptForAction):
            self.ui.promptFor(getMessage("en", "enter-to-exit-prompt"))

    class _WarningManager(object):
        def __init__(self, player, userlist, ui):
            self._player = player
            self._userlist = userlist
            self._ui = ui
            self._warnings = {
                            "room-files-not-same": {
                                                     "timer": task.LoopingCall(self.__displayMessageOnOSD, ("room-files-not-same"),),
                                                     "displayedFor": 0,
                                                    },
                            "alone-in-the-room": {
                                                     "timer": task.LoopingCall(self.__displayMessageOnOSD, ("alone-in-the-room"),),
                                                     "displayedFor": 0,
                                                    },
                            }
        def checkWarnings(self):
            self._checkIfYouReAloneInTheRoom()
            self._checkRoomForSameFiles()

        def _checkRoomForSameFiles(self):
            if (not self._userlist.areAllFilesInRoomSame()):
                self._ui.showMessage(getMessage("en", "room-files-not-same"), True)
                if(constants.SHOW_OSD_WARNINGS and not self._warnings["room-files-not-same"]['timer'].running):
                    self._warnings["room-files-not-same"]['timer'].start(constants.WARNING_OSD_MESSAGES_LOOP_INTERVAL, True)
            elif(self._warnings["room-files-not-same"]['timer'].running):
                self._warnings["room-files-not-same"]['timer'].stop()

        def _checkIfYouReAloneInTheRoom(self):
            if (self._userlist.areYouAloneInRoom()):
                self._ui.showMessage(getMessage("en", "alone-in-the-room"), True)
                if(constants.SHOW_OSD_WARNINGS and not self._warnings["alone-in-the-room"]['timer'].running):
                    self._warnings["alone-in-the-room"]['timer'].start(constants.WARNING_OSD_MESSAGES_LOOP_INTERVAL, True)
            elif(self._warnings["alone-in-the-room"]['timer'].running):
                self._warnings["alone-in-the-room"]['timer'].stop()

        def __displayMessageOnOSD(self, warningName):
            if (constants.OSD_WARNING_MESSAGE_DURATION > self._warnings[warningName]["displayedFor"]):
                self._ui.showOSDMessage(getMessage("en", warningName), constants.WARNING_OSD_MESSAGES_LOOP_INTERVAL)
                self._warnings[warningName]["displayedFor"] += constants.WARNING_OSD_MESSAGES_LOOP_INTERVAL
            else:
                self._warnings[warningName]["displayedFor"] = 0
                self._warnings[warningName]["timer"].stop()



class SyncplayUser(object):
    def __init__(self, username=None, room=None, file_=None):
        self.username = username
        self.room = room
        self.file = file_

    def setFile(self, filename, duration, size):
        file_ = {
                 "name": filename,
                 "duration": duration,
                 "size":size
                 }
        self.file = file_

    def isFileSame(self, file_):
        if(not self.file):
            return False
        sameName = utils.sameFilename(self.file['name'], file_['name'])
        sameSize = utils.sameFilesize(self.file['size'], file_['size'])
        sameDuration = utils.sameFileduration(self.file['duration'], file_['duration'])
        return sameName and sameSize and sameDuration

    def __lt__(self, other):
        return self.username.lower() < other.username.lower()

    def __repr__(self, *args, **kwargs):
        if(self.file):
            return "{}: {} ({}, {})".format(self.username, self.file['name'], self.file['duration'], self.file['size'])
        else:
            return "{}".format(self.username)

class SyncplayUserlist(object):
    def __init__(self, ui, client):
        self.currentUser = SyncplayUser()
        self._users = {}
        self.ui = ui
        self._client = client
        self._roomUsersChanged = True

    def isRoomSame(self, room):
        if (room and self.currentUser.room and self.currentUser.room == room):
            return True
        else:
            return False

    def __showUserChangeMessage(self, username, room, file_, oldRoom=None):
        if(room):
            if self.isRoomSame(room) or self.isRoomSame(oldRoom):
                showOnOSD = constants.SHOW_SAME_ROOM_OSD
            else:
                showOnOSD = constants.SHOW_DIFFERENT_ROOM_OSD
            hideFromOSD = not showOnOSD
        if(room and not file_):
            message = getMessage("en", "room-join-notification").format(username, room)
            self.ui.showMessage(message, hideFromOSD)
        elif (room and file_):
            duration = utils.formatTime(file_['duration'])
            message = getMessage("en", "playing-notification").format(username, file_['name'], duration)
            if(self.currentUser.room <> room or self.currentUser.username == username):
                message += getMessage("en", "playing-notification/room-addendum").format(room)
            self.ui.showMessage(message, hideFromOSD)
            if(self.currentUser.file and not self.currentUser.isFileSame(file_) and self.currentUser.room == room):
                message = getMessage("en", "file-different-notification").format(username)
                self.ui.showMessage(message, not constants.SHOW_OSD_WARNINGS)
                differences = []
                differentName = not utils.sameFilename(self.currentUser.file['name'], file_['name'])
                differentSize = not utils.sameFilesize(self.currentUser.file['size'], file_['size'])
                differentDuration = not utils.sameFileduration(self.currentUser.file['duration'], file_['duration'])
                if(differentName):
                    differences.append("filename")
                if(differentSize):
                    differences.append("size")
                if(differentDuration):
                    differences.append("duration")
                message = getMessage("en", "file-differences-notification") + ", ".join(differences)
                self.ui.showMessage(message, not constants.SHOW_OSD_WARNINGS)

    def addUser(self, username, room, file_, noMessage=False):
        if(username == self.currentUser.username):
            return
        user = SyncplayUser(username, room, file_)
        self._users[username] = user
        if(not noMessage):
            self.__showUserChangeMessage(username, room, file_)
        self.userListChange()

    def removeUser(self, username):
        hideFromOSD = not constants.SHOW_DIFFERENT_ROOM_OSD
        if(self._users.has_key(username)):
            user = self._users[username]
            if user.room:
                if self.isRoomSame(user.room):
                    hideFromOSD = not constants.SHOW_SAME_ROOM_OSD
        if(self._users.has_key(username)):
            self._users.pop(username)
            message = getMessage("en", "left-notification").format(username)
            self.ui.showMessage(message, hideFromOSD)
            self._client.lastLeftTime = time.time()
            self._client.lastLeftUser = username
        self.userListChange()

    def __displayModUserMessage(self, username, room, file_, user, oldRoom):
        if (file_ and not user.isFileSame(file_)):
            self.__showUserChangeMessage(username, room, file_, oldRoom)
        elif (room and room != user.room):
            self.__showUserChangeMessage(username, room, None, oldRoom)

    def modUser(self, username, room, file_):
        if(self._users.has_key(username)):
            user = self._users[username]
            oldRoom = user.room if user.room else None
            self.__displayModUserMessage(username, room, file_, user, oldRoom)
            user.room = room
            if file_:
                user.file = file_
        elif(username == self.currentUser.username):
            self.__showUserChangeMessage(username, room, file_)
        else:
            self.addUser(username, room, file_)
        self.userListChange()

    def areAllFilesInRoomSame(self):
        for user in self._users.itervalues():
            if(user.room == self.currentUser.room and user.file and not self.currentUser.isFileSame(user.file)):
                return False
        return True

    def areYouAloneInRoom(self):
        for user in self._users.itervalues():
            if(user.room == self.currentUser.room):
                return False
        return True

    def isUserInYourRoom(self, username):
        for user in self._users.itervalues():
            if(user.username == username and user.room == self.currentUser.room):
                return True
        return False

    def userListChange(self):
        self._roomUsersChanged = True
        self.ui.userListChange()

    def roomStateConfirmed(self):
        self._roomUsersChanged = False

    def hasRoomStateChanged(self):
        return self._roomUsersChanged

    def showUserList(self):
        rooms = {}
        for user in self._users.itervalues():
            if(user.room not in rooms):
                rooms[user.room] = []
            rooms[user.room].append(user)
        if(self.currentUser.room not in rooms):
                rooms[self.currentUser.room] = []
        rooms[self.currentUser.room].append(self.currentUser)
        rooms = self.sortList(rooms)
        self.ui.showUserList(self.currentUser, rooms)

    def clearList(self):
        self._users = {}

    def sortList(self, rooms):
        for room in rooms:
            rooms[room] = sorted(rooms[room])
        rooms = collections.OrderedDict(sorted(rooms.items(), key=lambda s: s[0].lower()))
        return rooms

class UiManager(object):
    def __init__(self, client, ui):
        self._client = client
        self.__ui = ui
        self.lastError = ""

    def showMessage(self, message, noPlayer=False, noTimestamp=False):
        if(not noPlayer): self.showOSDMessage(message)
        self.__ui.showMessage(message, noTimestamp)

    def showUserList(self, currentUser, rooms):
        self.__ui.showUserList(currentUser, rooms)

    def showOSDMessage(self, message, duration=constants.OSD_DURATION):
        if(constants.SHOW_OSD and self._client._player):
            self._client._player.displayMessage(message, duration * 1000)

    def showErrorMessage(self, message, criticalerror=False):
        if message <> self.lastError: # Avoid double call bug
            self.lastError = message
            self.__ui.showErrorMessage(message, criticalerror)

    def promptFor(self, prompt):
        return self.__ui.promptFor(prompt)

    def userListChange(self):
        self.__ui.userListChange()

    def markEndOfUserlist(self):
        self.__ui.markEndOfUserlist()

    def drop(self):
        self.__ui.drop()

########NEW FILE########
__FILENAME__ = clientManager
from syncplay.ui.ConfigurationGetter import ConfigurationGetter
from syncplay import ui
from syncplay.messages import getMessage

class SyncplayClientManager(object):
    def run(self):
        config = ConfigurationGetter().getConfiguration()
        from syncplay.client import SyncplayClient #Imported later, so the proper reactor is installed
        interface = ui.getUi(graphical=not config["noGui"])
        syncplayClient = SyncplayClient(config["playerClass"], interface, config)
        if(syncplayClient):
            interface.addClient(syncplayClient)
            syncplayClient.start(config['host'], config['port'])
        else:
            interface.showErrorMessage(getMessage("en", "unable-to-start-client-error"), True)
        

########NEW FILE########
__FILENAME__ = constants
#You might want to change these
DEFAULT_PORT = 8999
OSD_DURATION = 3
OSD_WARNING_MESSAGE_DURATION = 15
MPC_OSD_POSITION = 2 #Right corner, 1 for left
MPLAYER_OSD_LEVEL = 1
UI_TIME_FORMAT = "[%X] "
CONFIG_NAMES = [".syncplay", "syncplay.ini"] #Syncplay searches first to last
DEFAULT_CONFIG_NAME_WINDOWS = "syncplay.ini"
DEFAULT_CONFIG_NAME_LINUX = ".syncplay" 
RECENT_CLIENT_THRESHOLD = "1.2.8" #This and higher considered 'recent' clients (no warnings)
WARN_OLD_CLIENTS = True #Use MOTD to inform old clients to upgrade
SHOW_OSD = True # Sends Syncplay messages to media player OSD
SHOW_OSD_WARNINGS = True # Show warnings if playing different file, alone in room
SHOW_SLOWDOWN_OSD = True # Show notifications of slowing down / reverting on time difference
SHOW_SAME_ROOM_OSD = True  # Show OSD notifications for events relating to room user is in
SHOW_DIFFERENT_ROOM_OSD = False # Show OSD notifications for events relating to room user is not in
LIST_RELATIVE_CONFIGS = True # Print list of relative configs loaded
SHOW_CONTACT_INFO = True # Displays dev contact details below list in GUI
SHOW_BUTTON_LABELS = True # If disabled, only shows icons for main GUI buttons
SHOW_TOOLTIPS = True

#Changing these might be ok
REWIND_THRESHOLD = 4
SEEK_THRESHOLD = 1
SLOWDOWN_RATE = 0.95
SLOWDOWN_KICKIN_THRESHOLD = 1.5
SLOWDOWN_RESET_THRESHOLD = 0.1
DIFFFERENT_DURATION_THRESHOLD = 2.5
PROTOCOL_TIMEOUT = 12.5
RECONNECT_RETRIES = 10
SERVER_STATE_INTERVAL = 1
WARNING_OSD_MESSAGES_LOOP_INTERVAL = 1
SHOW_REWIND_ON_DESYNC_CHECKBOX = False
MERGE_PLAYPAUSE_BUTTONS = False
SYNC_ON_PAUSE = True # Client seek to global position - subtitles may disappear on some media players
#Usually there's no need to adjust these
FILENAME_STRIP_REGEX = u"[-~_\.\[\](): ]" 
COMMANDS_UNDO = ["u", "undo", "revert"]
COMMANDS_LIST = ["l", "list", "users"]
COMMANDS_PAUSE = ["p", "play", "pause"]
COMMANDS_ROOM = ["r", "room"]
COMMANDS_HELP = ['help', 'h', '?', '/?', r'\?']
MPC_MIN_VER = "1.6.4"
VLC_MIN_VERSION = "2.0.0"
VLC_INTERFACE_MIN_VERSION = "0.2.0"
MPC_PATHS = [
             r"C:\Program Files (x86)\MPC-HC\mpc-hc.exe",
             r"C:\Program Files\MPC-HC\mpc-hc.exe",
             r"C:\Program Files\MPC-HC\mpc-hc64.exe",
             r"C:\Program Files\Media Player Classic - Home Cinema\mpc-hc.exe",
             r"C:\Program Files\Media Player Classic - Home Cinema\mpc-hc64.exe",
             r"C:\Program Files (x86)\Media Player Classic - Home Cinema\mpc-hc.exe",
             r"C:\Program Files (x86)\K-Lite Codec Pack\Media Player Classic\mpc-hc.exe",
             r"C:\Program Files\K-Lite Codec Pack\Media Player Classic\mpc-hc.exe",
             r"C:\Program Files (x86)\Combined Community Codec Pack\MPC\mpc-hc.exe",
             r"C:\Program Files\Combined Community Codec Pack\MPC\mpc-hc.exe",
             r"C:\Program Files\MPC HomeCinema (x64)\mpc-hc64.exe",
             ]
MPLAYER_PATHS = ["mplayer2", "mplayer"]
MPV_PATHS = ["mpv", "/opt/mpv/mpv", r"C:\Program Files\mpv\mpv.exe", r"C:\Program Files\mpv-player\mpv.exe", r"C:\Program Files (x86)\mpv\mpv.exe", r"C:\Program Files (x86)\mpv-player\mpv.exe","/Applications/mpv.app/Contents/MacOS/mpv"]
VLC_PATHS = [
             r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
             r"C:\Program Files\VideoLAN\VLC\vlc.exe",
             "/Applications/VLC.app/Contents/MacOS/VLC"
            ]

VLC_ICONPATH = "vlc.png"
MPLAYER_ICONPATH = "mplayer.png"
MPV_ICONPATH = "mpv.png"
MPC_ICONPATH = "mpc-hc.png"
MPC64_ICONPATH = "mpc-hc64.png"

#Changing these is usually not something you're looking for
PLAYER_ASK_DELAY = 0.1
PING_MOVING_AVERAGE_WEIGHT = 0.85
MPC_OPEN_MAX_WAIT_TIME = 10
MPC_LOCK_WAIT_TIME = 0.2
MPC_RETRY_WAIT_TIME = 0.01
MPC_MAX_RETRIES = 30
MPC_PAUSE_TOGGLE_DELAY = 0.05
VLC_OPEN_MAX_WAIT_TIME = 15
VLC_MIN_PORT = 10000
VLC_MAX_PORT = 55000

#These are not changes you're looking for
MPLAYER_SLAVE_ARGS = [ '-slave', '--hr-seek=always', '-nomsgcolor', '-msglevel', 'all=1:global=4:cplayer=4']
# --quiet works with both mpv 0.2 and 0.3
MPV_SLAVE_ARGS = ['--slave-broken', '--hr-seek=always', '--quiet']
VLC_SLAVE_ARGS = ['--extraintf=luaintf','--lua-intf=syncplay','--no-quiet','--no-input-fast-seek']
VLC_SLAVE_NONOSX_ARGS = ['--no-one-instance','--no-one-instance-when-started-from-file']
MPLAYER_ANSWER_REGEX = "^ANS_([a-zA-Z_-]+)=(.+)$"
VLC_ANSWER_REGEX = r"(?:^(?P<command>[a-zA-Z_]+)(?:\: )?(?P<argument>.*))"
UI_COMMAND_REGEX = r"^(?P<command>[^\ ]+)(?:\ (?P<parameter>.+))?"
UI_OFFSET_REGEX = r"^(?:o|offset)\ ?(?P<sign>[/+-])?(?P<time>\d{1,4}(?:[^\d\.](?:\d{1,6})){0,2}(?:\.(?:\d{1,3}))?)$"
UI_SEEK_REGEX = r"^(?:s|seek)?\ ?(?P<sign>[+-])?(?P<time>\d{1,4}(?:[^\d\.](?:\d{1,6})){0,2}(?:\.(?:\d{1,3}))?)$"
PARSE_TIME_REGEX = r'(:?(?:(?P<hours>\d+?)[^\d\.])?(?:(?P<minutes>\d+?))?[^\d\.])?(?P<seconds>\d+?)(?:\.(?P<miliseconds>\d+?))?$'
SERVER_MAX_TEMPLATE_LENGTH = 10000
PRIVACY_SENDRAW_MODE = "SendRaw"
PRIVACY_SENDHASHED_MODE = "SendHashed"
PRIVACY_DONTSEND_MODE = "DoNotSend"
PRIVACY_HIDDENFILENAME = "**Hidden filename**"

########NEW FILE########
__FILENAME__ = messages
# coding:utf8
from syncplay import constants

en = {

      # Client notifications
      "relative-config-notification" : "Loaded relative configuration file(s): {}",

      "connection-attempt-notification" : "Attempting to connect to {}:{}",  # Port, IP
      "reconnection-attempt-notification" : "Connection with server lost, attempting to reconnect",
      "disconnection-notification" : "Disconnected from server",
      "connection-failed-notification" : "Connection with server failed",
      "connected-successful-notification" : "Successfully connected to server",
      "retrying-notification" : "%s, Retrying in %d seconds...",  # Seconds

      "rewind-notification" : "Rewinded due to time difference with <{}>",  # User
      "slowdown-notification" : "Slowing down due to time difference with <{}>",  # User
      "revert-notification" : "Reverting speed back to normal",

      "pause-notification" : "<{}> paused",  # User
      "unpause-notification" : "<{}> unpaused",  # User
      "seek-notification" : "<{}> jumped from {} to {}",  # User, from time, to time

      "current-offset-notification" : "Current offset: {} seconds",  # Offset

      "room-join-notification" : "<{}> has joined the room: '{}'",  # User
      "left-notification" : "<{}> has left",  # User
      "left-paused-notification" : "<{}> left, <{}> paused",  # User who left, User who paused
      "playing-notification" : "<{}> is playing '{}' ({})",  # User, file, duration
      "playing-notification/room-addendum" :  " in room: '{}'",  # Room

      "file-different-notification" : "File you are playing appears to be different from <{}>'s",  # User
      "file-differences-notification" : "Your file differs in the following way(s): ",
      "room-files-not-same" : "Not all files played in the room are the same",
      "alone-in-the-room": "You're alone in the room",

      "different-filesize-notification" : " (their file size is different from yours!)",
      "file-played-by-notification" : "File: {} is being played by:",  # File
      "notplaying-notification" : "People who are not playing any file:",
      "userlist-room-notification" :  "In room '{}':",  # Room

      "mplayer-file-required-notification" : "Syncplay using mplayer requires you to provide file when starting",
      "mplayer-file-required-notification/example" : "Usage example: syncplay [options] [url|path/]filename",
      "mplayer2-required" : "Syncplay is incompatible with MPlayer 1.x, please use mplayer2 or mpv",

      "unrecognized-command-notification" : "Unrecognized command",
      "commandlist-notification" : "Available commands:",
      "commandlist-notification/room" : "\tr [name] - change room",
      "commandlist-notification/list" : "\tl - show user list",
      "commandlist-notification/undo" : "\tu - undo last seek",
      "commandlist-notification/pause" : "\tp - toggle pause",
      "commandlist-notification/seek" : "\t[s][+-]time - seek to the given value of time, if + or - is not specified it's absolute time in seconds or min:sec",
      "commandlist-notification/help" : "\th - this help",
      "syncplay-version-notification" : "Syncplay version: {}",  # syncplay.version
      "more-info-notification" : "More info available at: {}",  # projectURL

      "gui-data-cleared-notification" : "Syncplay has cleared the path and window state data used by the GUI.",

      "vlc-version-mismatch": "Warning: You are running VLC version {}, but Syncplay is designed to run on VLC {} and above.",  # VLC version, VLC min version
      "vlc-interface-version-mismatch": "Warning: You are running version {} of the Syncplay interface module for VLC, but Syncplay is designed to run with version {} and above.",  # VLC interface version, VLC interface min version
      "vlc-interface-oldversion-ignored": "Warning: Syncplay detected that an old version version of the Syncplay interface module for VLC was installed in the VLC directory. As such, if you are running VLC 2.0 then it will be ignored in favour of the syncplay.lua module contained within the Syncplay directory, but this will mean that other custom interface scripts and extensions will not work. Please refer to the Syncplay User Guide at http://syncplay.pl/guide/ for instructions on how to install syncplay.lua.",
      "vlc-interface-not-installed": "Warning: The Syncplay interface module for VLC was not found in the VLC directory. As such, if you are running VLC 2.0 then VLC will use the syncplay.lua module contained within the Syncplay directory, but this will mean that other custom interface scripts and extensions will not work. Please refer to the Syncplay User Guide at http://syncplay.pl/guide/ for instructions on how to install syncplay.lua.",

      # Client prompts
      "enter-to-exit-prompt" : "Press enter to exit\n",

      # Client errors
      "missing-arguments-error" : "Some necessary arguments are missing, refer to --help",
      "server-timeout-error" : "Connection with server timed out",
       "mpc-slave-error" : "Unable to start MPC in slave mode!",
       "mpc-version-insufficient-error" : "MPC version not sufficient, please use `mpc-hc` >= `{}`",
       "player-file-open-error" : "Player failed opening file",
       "player-path-error" : "Player path is not set properly",
       "hostname-empty-error" : "Hostname can't be empty",
       "empty-error" : "{} can't be empty",  # Configuration

       "arguments-missing-error" : "Some necessary arguments are missing, refer to --help",

       "unable-to-start-client-error" : "Unable to start client",

       "not-json-error" : "Not a json encoded string\n",
       "hello-arguments-error" : "Not enough Hello arguments\n",
       "version-mismatch-error" : "Mismatch between versions of client and server\n",
       "vlc-error-echo": "VLC error: {}",  # VLC error line
       "vlc-failed-connection": "Failed to connect to VLC. If you have not installed syncplay.lua then please refer to http://syncplay.pl/LUA/ for instructions.",
       "vlc-failed-noscript": "VLC has reported that the syncplay.lua interface script has not been installed. Please refer to http://syncplay.pl/LUA/ for instructions.",
       "vlc-failed-versioncheck": "This version of VLC is not supported by Syncplay. Please use VLC 2.",
       "vlc-failed-other" : "When trying to load the syncplay.lua interface script VLC has provided the following error: {}",  # Syncplay Error

      # Client arguments
      "argument-description" : 'Solution to synchronize playback of multiple MPlayer and MPC-HC instances over the network.',
      "argument-epilog" : 'If no options supplied _config values will be used',
      "nogui-argument" : 'show no GUI',
      "host-argument" : 'server\'s address',
      "name-argument" : 'desired username',
      "debug-argument" : 'debug mode',
      "force-gui-prompt-argument" : 'make configuration prompt appear',
      "no-store-argument" : 'don\'t store values in .syncplay',
      "room-argument" : 'default room',
      "password-argument" : 'server password',
      "player-path-argument" : 'path to your player executable',
      "file-argument" : 'file to play',
      "args-argument" : 'player options, if you need to pass options starting with - prepend them with single \'--\' argument',
      "clear-gui-data-argument" : 'resets path and window state GUI data stored as QSettings',

      # Client labels
      "config-window-title" : "Syncplay configuration",

      "connection-group-title" : "Connection settings",
      "host-label" : "Server address: ",
      "username-label" :  "Username (optional):",
      "password-label" :  "Server password (if any):",
      "room-label" : "Default room: ",

      "media-setting-title" : "Media player settings",
      "executable-path-label" : "Path to media player:",
      "media-path-label" : "Path to media file:",
      "browse-label" : "Browse",

      "more-title" : "Show more settings",
      "privacy-sendraw-option" : "Send raw",
      "privacy-sendhashed-option" : "Send hashed",
      "privacy-dontsend-option" : "Don't send",
      "filename-privacy-label" : "Filename information:",
      "filesize-privacy-label" : "File size information:",
      "slowdown-label" : "Slow down on desync",
      "dontslowwithme-label" : "Never slow down or rewind others",
      "pauseonleave-label" : "Pause when user leaves",
      "rewind-label" : "Rewind on major desync (highly recommended)",
      "alwayshow-label" : "Always show this dialog",
      "donotstore-label" : "Do not store this configuration",

      "help-label" : "Help",
      "run-label" : "Run Syncplay",
      "storeandrun-label" : "Store configuration and run Syncplay",

      "contact-label" : "Have an idea, bug report or feedback? E-mail <a href=\"mailto:dev@syncplay.pl\">dev@syncplay.pl</a>, chat via the <a href=\"https://webchat.freenode.net/?channels=#syncplay\">#Syncplay IRC channel</a> on irc.freenode.net or <a href=\"https://github.com/Uriziel/syncplay/issues/new\">raise an issue via GitHub</a>. Also check out <a href=\"http://syncplay.pl/\">http://syncplay.pl/</a> for info, help and updates.",

      "joinroom-guibuttonlabel" : "Join room",
      "seektime-guibuttonlabel" : "Seek to time",
      "undoseek-guibuttonlabel" : "Undo seek",
      "togglepause-guibuttonlabel" : "Toggle pause",
      "play-guibuttonlabel" : "Play",
      "pause-guibuttonlabel" : "Play",

      "roomuser-heading-label" : "Room / User",
      "fileplayed-heading-label" : "File being played",
      "notifications-heading-label" : "Notifications",
      "userlist-heading-label" : "List of who is playing what",
      "othercommands-heading-label" :  "Other commands",
      "room-heading-label" :  "Room",
      "seek-heading-label" :  "Seek",

      "browseformedia-label" : "Browse for media files",

      "file-menu-label" : "&File", # & precedes shortcut key
      "openmedia-menu-label" : "&Open media file",
      "exit-menu-label" : "E&xit",
      "advanced-menu-label" : "&Advanced",
      "setoffset-menu-label" : "Set &offset",
      "help-menu-label" : "&Help",
      "userguide-menu-label" : "Open user &guide",

      "setoffset-msgbox-label" : "Set offset",
      "offsetinfo-msgbox-label" : "Offset (see http://syncplay.pl/guide/ for usage instructions):",

      # Tooltips

      "host-tooltip" : "Hostname or IP to connect to, optionally including port (e.g. syncplay.pl:8999). Only synchronised with people on same server/port.",
      "username-tooltip" : "Nickname you will be known by. No registration, so can easily change later. Random name generated if none specified.",
      "password-tooltip" : "Passwords are only needed for connecting to private servers.",
      "room-tooltip" : "Room to join upon connection can be almost anything, but you will only be synchronised with people in the same room.",

      "executable-path-tooltip" : "Location of your chosen supported media player (MPC-HC, VLC, mplayer2 or mpv).",
      "media-path-tooltip" : "Location of video or stream to be opened. Necessary for mpv and mplayer2.",

      "more-tooltip" : "Display less frequently used settings.",
      "filename-privacy-tooltip" : "Privacy mode for sending currently playing filename to server.",
      "filesize-privacy-tooltip" : "Privacy mode for sending size of currently playing file to server.",
      "privacy-sendraw-tooltip" : "Send this information without obfuscation. This is the default option with most functionality.",
      "privacy-sendhashed-tooltip" : "Send a hashed version of the information, making it less visible to other clients.",
      "privacy-dontsend-tooltip" : "Do not send this information to the server. This provides for maximum privacy.",
      "slowdown-tooltip" : "Reduce playback rate temporarily when needed to bring you back in sync with other viewers.",
      "dontslowwithme-tooltip" : "Means others do not get slowed down or rewinded if your playback is lagging.",
      "pauseonleave-tooltip" : "Pause playback if you get disconnected or someone leaves from your room.",
      "rewind-tooltip" : "Jump back when needed to get back in sync. Recommended.",
      "alwayshow-tooltip" : "Configuration dialogue is always shown, even when opening a file with Syncplay.",
      "donotstore-tooltip" : "Run Syncplay with the given configuration, but do not permanently store the changes.",

      "help-tooltip" : "Opens the Syncplay.pl user guide.",

      "togglepause-tooltip" : "Pause/unpause media.",
      "play-tooltip" : "Unpause media.",
      "pause-tooltip" : "Pause media.",
      "undoseek-tooltip" : "Seek to where you were before the most recent seek.",
      "joinroom-tooltip" : "Leave current room and joins specified room.",
      "seektime-tooltip" : "Jump to specified time (in seconds / min:sec). Use +/- for relative seek.",

      # In-userlist notes (GUI)
      "differentsize-note" : "Different size!",
      "differentsizeandduration-note" : "Different size and duration!",
      "differentduration-note" : "Different duration!",
      "nofile-note" : "(No file being played)",

      # Server messages to client
      "new-syncplay-available-motd-message" : "<NOTICE> You are using Syncplay {} but a newer version is available from http://syncplay.pl </NOTICE>",  # ClientVersion

      # Server notifications
      "welcome-server-notification" : "Welcome to Syncplay server, ver. {0}",  # version
      "client-connected-room-server-notification" : "{0}({2}) connected to room '{1}'",  # username, host, room
      "client-left-server-notification" : "{0} left server",  # name


      # Server arguments
      "server-argument-description" : 'Solution to synchronize playback of multiple MPlayer and MPC-HC instances over the network. Server instance',
      "server-argument-epilog" : 'If no options supplied _config values will be used',
      "server-port-argument" : 'server TCP port',
      "server-password-argument" : 'server password',
      "server-isolate-room-argument" : 'should rooms be isolated?',
      "server-motd-argument": "path to file from which motd will be fetched",
      "server-messed-up-motd-unescaped-placeholders": "Message of the Day has unescaped placeholders. All $ signs should be doubled ($$).",
      "server-messed-up-motd-too-long": "Message of the Day is too long - maximum of {} chars, {} given.",
      "server-irc-verbose": "Should server actively report changes in rooms",
      "server-irc-config": "Path to irc bot config files",

      # Server errors
      "unknown-command-server-error" : "Unknown command {}",  # message
      "not-json-server-error" : "Not a json encoded string {}",  # message
      "not-known-server-error" : "You must be known to server before sending this command",
      "client-drop-server-error" : "Client drop: {} -- {}",  # host, error
      "password-required-server-error" : "Password required",
      "wrong-password-server-error" : "Wrong password supplied",
      "hello-server-error" : "Not enough Hello arguments",
      "version-mismatch-server-error" : "Mismatch between versions of client and server"


      }

pl = {

      # Client notifications
      "connection-attempt-notification" : "Próba połączenia z {}:{}", # Port, IP
      "reconnection-attempt-notification" : "Połączenie z serwerem zostało przerwane, ponowne łączenie",
      "disconnection-notification" : "Odłączono od serwera",
      "connection-failed-notification" : "Połączenie z serwerem zakończone fiaskiem",

      "rewind-notification" : "Cofnięto z powodu różnicy czasu z <{}>", # User
      "slowdown-notification" : "Zwolniono z powodu różnicy czasu z <{}>", # User
      "revert-notification" : "Przywrócono normalną prędkość odtwarzania",

      "pause-notification" : "<{}> zatrzymał odtwarzanie", # User
      "unpause-notification" : "<{}> wznowił odtwarzanie", # User
      "seek-notification" : "<{}> skoczył z {} do {}", # User, from time, to time

      "current-offset-notification" : "Obecny offset: {} seconds",  # Offset

      "room-join-notification" : "<{}> dołączył do pokoju: '{}'", # User
      "left-notification" : "<{}> wyszedł", # User
      "playing-notification" : "<{}> odtwarza '{}' ({})",  # User, file, duration
      "playing-notification/room-addendum" : " w pokoju: '{}'",  # Room

      "file-different-notification" : "Plik, który odtwarzasz wydaje się być różny od <{}>", # User
      "file-differences-notification" : "Twój plik różni się następującymi parametrami: ",

      "different-filesize-notification" : " (inny rozmiar pliku!)",
      "file-played-by-notification" : "Plik: {} jest odtwarzany przez:",  # File
      "notplaying-notification" : "Osoby, które nie odtwarzają żadnych plików:",
      "userlist-room-notification" :  "W pokoju '{}':",  # Room
      # Client prompts
      "enter-to-exit-prompt" : "Wciśnij Enter, aby zakończyć działanie programu\n",

      # Client errors
      "server-timeout-error" : "Przekroczono czas oczekiwania na odpowiedź serwera"
      }

messages = {
           "en": en,
           "pl": pl
           }

def getMessage(locale, type_):
    if(constants.SHOW_BUTTON_LABELS == False):
        if("-guibuttonlabel" in type_):
            return ""
    if(constants.SHOW_TOOLTIPS == False):
        if("-tooltip" in type_):
            return ""
    if(messages.has_key(locale)):
        if(messages[locale].has_key(type_)):
            return unicode(messages[locale][type_])
    if(messages["en"].has_key(type_)):
        return unicode(messages["en"][type_])
    else:
        raise KeyError()

########NEW FILE########
__FILENAME__ = basePlayer
from syncplay import constants
class BasePlayer(object):
  
    '''
    This method is supposed to 
    execute updatePlayerStatus(paused, position) on client
    Given the arguments: boolean paused and float position in seconds 
    '''
    def askForStatus(self):
        raise NotImplementedError()

    '''
    Display given message on player's OSD or similar means
    '''
    def displayMessage(self, message, duration = (constants.OSD_DURATION*1000)):
        raise NotImplementedError()

    '''
    Cleanup connection with player before syncplay will close down
    '''
    def drop(self):
        raise NotImplementedError()

    '''
    Start up the player, returns its instance
    '''
    @staticmethod
    def run(client, playerPath, filePath, args):
        raise NotImplementedError()

    '''
    @type value: boolean 
    '''
    def setPaused(self, value):
        raise NotImplementedError()

    '''
    @type value: float 
    '''
    def setPosition(self, value):
        raise NotImplementedError()

    '''
    @type value: float 
    '''
    def setSpeed(self, value):
        raise NotImplementedError()
    
    '''
    @type filePath: string 
    '''
    def openFile(self, filePath):
        raise NotImplementedError()
    
    
    '''
    @return: list of strings
    '''
    @staticmethod
    def getDefaultPlayerPathsList():
        raise NotImplementedError()
    
    '''
    @type path: string
    '''
    @staticmethod
    def isValidPlayerPath(path):
        raise NotImplementedError()
        
    '''
    @type path: string
    @return: string
    '''    
    @staticmethod
    def getIconPath(path):
        raise NotImplementedError()
    
    '''
    @type path: string
    @return: string
    '''    
    @staticmethod
    def getExpandedPath(path):
        raise NotImplementedError()
    
    
class DummyPlayer(BasePlayer):

    @staticmethod
    def getDefaultPlayerPathsList():
        return []
    
    @staticmethod
    def isValidPlayerPath(path):
        return False
    
    @staticmethod
    def getIconPath(path):
        return None
    
    @staticmethod
    def getExpandedPath(path):
        return path

########NEW FILE########
__FILENAME__ = mpc
#coding:utf8
import time
import threading
import thread
import win32con, win32api, win32gui, ctypes, ctypes.wintypes #@UnresolvedImport @UnusedImport
from functools import wraps
from syncplay.players.basePlayer import BasePlayer
import re
from syncplay.utils import retry
from syncplay import constants  
from syncplay.messages import getMessage
import os.path

class MpcHcApi:
    def __init__(self):
        self.callbacks = self.__Callbacks()
        self.loadState = None
        self.playState = None
        self.filePlaying = None
        self.fileDuration = None
        self.filePath = None
        self.lastFilePosition = None
        self.version = None
        self.__playpause_warden = False
        self.__locks = self.__Locks()
        self.__mpcExistenceChecking = threading.Thread(target=self.__mpcReadyInSlaveMode, name="Check MPC window")
        self.__mpcExistenceChecking.setDaemon(True)
        self.__listener = self.__Listener(self, self.__locks)
        self.__listener.setDaemon(True)
        self.__listener.start()
        self.__locks.listenerStart.wait()
    
    def waitForFileStateReady(f): #@NoSelf
        @wraps(f)
        def wrapper(self, *args, **kwds):
            if(not self.__locks.fileReady.wait(constants.MPC_LOCK_WAIT_TIME)):
                raise self.PlayerNotReadyException()
            return f(self, *args, **kwds)
        return wrapper
            
    def startMpc(self, path, args=()):
        args = "%s /slave %s" % (" ".join(args), str(self.__listener.hwnd))
        win32api.ShellExecute(0, "open", path, args, None, 1)
        if(not self.__locks.mpcStart.wait(constants.MPC_OPEN_MAX_WAIT_TIME)):
            raise self.NoSlaveDetectedException(getMessage("en", "mpc-slave-error"))
        self.__mpcExistenceChecking.start() 

    def openFile(self, filePath):
        self.__listener.SendCommand(self.CMD_OPENFILE, filePath)
    
    def isPaused(self):
        return (self.playState <> self.__MPC_PLAYSTATE.PS_PLAY and self.playState <> None)
 
    def askForVersion(self):
        self.__listener.SendCommand(self.CMD_GETVERSION)
 
    @waitForFileStateReady
    def pause(self):
        self.__listener.SendCommand(self.CMD_PAUSE)
 
    @waitForFileStateReady
    def playPause(self):
        self.__listener.SendCommand(self.CMD_PLAYPAUSE)
     
    @waitForFileStateReady
    def unpause(self):
        self.__listener.SendCommand(self.CMD_PLAY)
 
    @waitForFileStateReady
    def askForCurrentPosition(self):
        self.__listener.SendCommand(self.CMD_GETCURRENTPOSITION)

    @waitForFileStateReady
    def seek(self, position):
        self.__listener.SendCommand(self.CMD_SETPOSITION, unicode(position))

    @waitForFileStateReady
    def setSpeed(self, rate):
        self.__listener.SendCommand(self.CMD_SETSPEED, unicode(rate))

    def sendOsd(self, message, MsgPos=constants.MPC_OSD_POSITION, DurationMs=(constants.OSD_DURATION*1000)):
        class __OSDDATASTRUCT(ctypes.Structure):
            _fields_ = [
                ('nMsgPos', ctypes.c_int32),
                ('nDurationMS', ctypes.c_int32),
                ('strMsg', ctypes.c_wchar * (len(message) + 1))
            ]    
        cmessage = __OSDDATASTRUCT() 
        cmessage.nMsgPos = MsgPos 
        cmessage.nDurationMS = DurationMs 
        cmessage.strMsg = message
        self.__listener.SendCommand(self.CMD_OSDSHOWMESSAGE, cmessage)
        
    def sendRawCommand(self, cmd, value):
        self.__listener.SendCommand(cmd, value)

    def handleCommand(self, cmd, value):
        if (cmd == self.CMD_CONNECT): 
            self.__listener.mpcHandle = int(value)
            self.__locks.mpcStart.set()
            if(self.callbacks.onConnected): 
                thread.start_new_thread(self.callbacks.onConnected, ())
                
        elif(cmd == self.CMD_STATE):
            self.loadState = int(value)
            fileNotReady = self.loadState == self.__MPC_LOADSTATE.MLS_CLOSING or self.loadState == self.__MPC_LOADSTATE.MLS_LOADING
            if(fileNotReady):
                self.playState = None
                self.__locks.fileReady.clear()
            else:
                self.__locks.fileReady.set()
            if(self.callbacks.onFileStateChange): 
                thread.start_new_thread(self.callbacks.onFileStateChange, (self.loadState,))
            
        elif(cmd == self.CMD_PLAYMODE):
            self.playState = int(value)
            if(self.callbacks.onUpdatePlaystate):  
                thread.start_new_thread(self.callbacks.onUpdatePlaystate, (self.playState,))
            
        elif(cmd == self.CMD_NOWPLAYING):
            value = re.split(r'(?<!\\)\|', value)
            if self.filePath == value[3]:
                return
            self.filePath = value[3]
            self.filePlaying = value[3].split('\\').pop()
            self.fileDuration = float(value[4])
            if(self.callbacks.onUpdatePath): 
                thread.start_new_thread(self.callbacks.onUpdatePath, (self.onUpdatePath,))
            if(self.callbacks.onUpdateFilename): 
                thread.start_new_thread(self.callbacks.onUpdateFilename, (self.filePlaying,))
            if(self.callbacks.onUpdateFileDuration): 
                thread.start_new_thread(self.callbacks.onUpdateFileDuration, (self.fileDuration,))
            
        elif(cmd == self.CMD_CURRENTPOSITION):
            self.lastFilePosition = float(value)
            if(self.callbacks.onGetCurrentPosition): 
                thread.start_new_thread(self.callbacks.onGetCurrentPosition, (self.lastFilePosition,))
        
        elif(cmd == self.CMD_NOTIFYSEEK):
            if(self.lastFilePosition <> float(value)): #Notify seek is sometimes sent twice
                self.lastFilePosition = float(value)
                if(self.callbacks.onSeek): 
                    thread.start_new_thread(self.callbacks.onSeek, (self.lastFilePosition,))
        
        elif(cmd == self.CMD_DISCONNECT):
            if(self.callbacks.onMpcClosed): 
                thread.start_new_thread(self.callbacks.onMpcClosed, (None,))
    
        elif(cmd == self.CMD_VERSION):
            if(self.callbacks.onVersion): 
                self.version = value
                thread.start_new_thread(self.callbacks.onVersion, (value,))
            
    class PlayerNotReadyException(Exception):
        pass
    
    class __Callbacks:
        def __init__(self):
            self.onConnected = None
            self.onSeek = None
            self.onUpdatePath = None
            self.onUpdateFilename = None
            self.onUpdateFileDuration = None
            self.onGetCurrentPosition = None
            self.onUpdatePlaystate = None
            self.onFileStateChange = None
            self.onMpcClosed = None
            self.onVersion = None
            
    class __Locks:
        def __init__(self):
            self.listenerStart = threading.Event()
            self.mpcStart = threading.Event()
            self.fileReady = threading.Event()
            
    def __mpcReadyInSlaveMode(self):
        while(True):
            time.sleep(10)
            if not win32gui.IsWindow(self.__listener.mpcHandle):
                if(self.callbacks.onMpcClosed):
                    self.callbacks.onMpcClosed(None)
                break
               
    CMD_CONNECT = 0x50000000
    CMD_STATE = 0x50000001
    CMD_PLAYMODE = 0x50000002
    CMD_NOWPLAYING = 0x50000003
    CMD_LISTSUBTITLETRACKS = 0x50000004
    CMD_LISTAUDIOTRACKS = 0x50000005
    CMD_CURRENTPOSITION = 0x50000007
    CMD_NOTIFYSEEK = 0x50000008
    CMD_NOTIFYENDOFSTREAM = 0x50000009
    CMD_PLAYLIST = 0x50000006
    CMD_OPENFILE = 0xA0000000
    CMD_STOP = 0xA0000001
    CMD_CLOSEFILE = 0xA0000002
    CMD_PLAYPAUSE = 0xA0000003
    CMD_ADDTOPLAYLIST = 0xA0001000
    CMD_CLEARPLAYLIST = 0xA0001001
    CMD_STARTPLAYLIST = 0xA0001002
    CMD_REMOVEFROMPLAYLIST = 0xA0001003 # TODO
    CMD_SETPOSITION = 0xA0002000
    CMD_SETAUDIODELAY = 0xA0002001
    CMD_SETSUBTITLEDELAY = 0xA0002002
    CMD_SETINDEXPLAYLIST = 0xA0002003 # DOESNT WORK
    CMD_SETAUDIOTRACK = 0xA0002004
    CMD_SETSUBTITLETRACK = 0xA0002005
    CMD_GETSUBTITLETRACKS = 0xA0003000
    CMD_GETCURRENTPOSITION = 0xA0003004
    CMD_JUMPOFNSECONDS = 0xA0003005
    CMD_GETAUDIOTRACKS = 0xA0003001
    CMD_GETNOWPLAYING = 0xA0003002
    CMD_GETPLAYLIST = 0xA0003003
    CMD_TOGGLEFULLSCREEN = 0xA0004000
    CMD_JUMPFORWARDMED = 0xA0004001
    CMD_JUMPBACKWARDMED = 0xA0004002
    CMD_INCREASEVOLUME = 0xA0004003
    CMD_DECREASEVOLUME = 0xA0004004
    CMD_SHADER_TOGGLE = 0xA0004005
    CMD_CLOSEAPP = 0xA0004006
    CMD_OSDSHOWMESSAGE = 0xA0005000
    CMD_VERSION = 0x5000000A
    CMD_DISCONNECT = 0x5000000B
    CMD_PLAY = 0xA0000004
    CMD_PAUSE = 0xA0000005
    CMD_GETVERSION = 0xA0003006
    CMD_SETSPEED = 0xA0004008
    
    class __MPC_LOADSTATE:
        MLS_CLOSED = 0
        MLS_LOADING = 1
        MLS_LOADED = 2
        MLS_CLOSING = 3
    
    class __MPC_PLAYSTATE:
        PS_PLAY = 0
        PS_PAUSE = 1
        PS_STOP = 2
        PS_UNUSED = 3

    class __Listener(threading.Thread):
        def __init__(self, mpcApi, locks):
            self.__mpcApi = mpcApi
            self.locks = locks
            self.mpcHandle = None
            self.hwnd = None
            self.__PCOPYDATASTRUCT = ctypes.POINTER(self.__COPYDATASTRUCT) 
            threading.Thread.__init__(self, name="MPC Listener")
            
        def run(self):   
            message_map = {
                win32con.WM_COPYDATA: self.OnCopyData
            }
            wc = win32gui.WNDCLASS()
            wc.lpfnWndProc = message_map
            wc.lpszClassName = 'MPCApiListener'
            hinst = wc.hInstance = win32api.GetModuleHandle(None)
            classAtom = win32gui.RegisterClass(wc)
            self.hwnd = win32gui.CreateWindow (
                classAtom,
                "ListenerGUI",
                0,
                0,
                0,
                win32con.CW_USEDEFAULT,
                win32con.CW_USEDEFAULT,
                0,
                0,
                hinst,
                None
            )
            self.locks.listenerStart.set()
            win32gui.PumpMessages()
            
      
        def OnCopyData(self, hwnd, msg, wparam, lparam):
            pCDS = ctypes.cast(lparam, self.__PCOPYDATASTRUCT)
            #print "API:\tin>\t 0x%X\t" % int(pCDS.contents.dwData), ctypes.wstring_at(pCDS.contents.lpData)
            self.__mpcApi.handleCommand(pCDS.contents.dwData, ctypes.wstring_at(pCDS.contents.lpData))
    
        def SendCommand(self, cmd, message=u''):
            #print "API:\t<out\t 0x%X\t" % int(cmd), message
            if not win32gui.IsWindow(self.mpcHandle):
                if(self.__mpcApi.callbacks.onMpcClosed):
                    self.__mpcApi.callbacks.onMpcClosed(None)
            cs = self.__COPYDATASTRUCT()
            cs.dwData = cmd;

            if(isinstance(message, (unicode, str))):
                message = ctypes.create_unicode_buffer(message, len(message) + 1)
            elif(isinstance(message, ctypes.Structure)):
                pass
            else:
                raise TypeError
            cs.lpData = ctypes.addressof(message)
            cs.cbData = ctypes.sizeof(message)
            ptr = ctypes.addressof(cs)
            win32api.SendMessage(self.mpcHandle, win32con.WM_COPYDATA, self.hwnd, ptr)    
            
        class __COPYDATASTRUCT(ctypes.Structure):
            _fields_ = [
                ('dwData', ctypes.wintypes.LPARAM),
                ('cbData', ctypes.wintypes.DWORD),
                ('lpData', ctypes.c_void_p)
            ]

class MPCHCAPIPlayer(BasePlayer):
    speedSupported = False
    
    def __init__(self, client):
        from twisted.internet import reactor
        self.reactor = reactor
        self.__client = client
        self._mpcApi = MpcHcApi()
        self._mpcApi.callbacks.onUpdateFilename = lambda _: self.__makePing()
        self._mpcApi.callbacks.onMpcClosed = lambda _: self.reactor.callFromThread(self.__client.stop, (False),)
        self._mpcApi.callbacks.onFileStateChange = lambda _: self.__lockAsking()
        self._mpcApi.callbacks.onUpdatePlaystate = lambda _: self.__unlockAsking()
        self._mpcApi.callbacks.onGetCurrentPosition = lambda _: self.__onGetPosition()
        self._mpcApi.callbacks.onVersion = lambda _: self.__versionUpdate.set()
        self.__switchPauseCalls = False
        self.__preventAsking = threading.Event()
        self.__positionUpdate = threading.Event()
        self.__versionUpdate = threading.Event()
        self.__fileUpdate = threading.RLock()
        self.__versionUpdate.clear()
        
    def drop(self):
        self.__preventAsking.set()
        self.__positionUpdate.set()
        self.__versionUpdate.set()
        self._mpcApi.sendRawCommand(MpcHcApi.CMD_CLOSEAPP, "")

    @staticmethod
    def run(client, playerPath, filePath, args):
        args.extend(['/open', '/new'])
        mpc = MPCHCAPIPlayer(client)
        mpc._mpcApi.callbacks.onConnected = lambda: mpc.initPlayer(filePath if(filePath) else None)
        mpc._mpcApi.startMpc(MPCHCAPIPlayer.getExpandedPath(playerPath), args)
        client.initPlayer(mpc)
        return mpc

    def __lockAsking(self):
        self.__preventAsking.clear()
        
    def __unlockAsking(self):
        self.__preventAsking.set()
    
    def __onGetPosition(self):
        self.__positionUpdate.set()
    
    def setSpeed(self, value):
        try:
            self._mpcApi.setSpeed(value)
        except MpcHcApi.PlayerNotReadyException:
            self.setSpeed(value)
            
    def __dropIfNotSufficientVersion(self):
        self._mpcApi.askForVersion()
        if(not self.__versionUpdate.wait(0.1) or not self._mpcApi.version):
            self.reactor.callFromThread(self.__client.ui.showErrorMessage, getMessage("en", "mpc-version-insufficient-error").format(constants.MPC_MIN_VER), True)
            self.reactor.callFromThread(self.__client.stop, True)
            
    def __testMpcReady(self):
        if(not self.__preventAsking.wait(10)):
            raise Exception(getMessage("en", "player-file-open-error"))
        
    def __makePing(self):
        try:
            self.__testMpcReady()
            self._mpcApi.callbacks.onUpdateFilename = lambda _: self.__handleUpdatedFilename()
            self.__handleUpdatedFilename()
            self.askForStatus()
        except Exception, err:
            self.reactor.callFromThread(self.__client.ui.showErrorMessage, err.message, True)
            self.reactor.callFromThread(self.__client.stop)
            
    def initPlayer(self, filePath): 
        self.__dropIfNotSufficientVersion()
        if(not self._mpcApi.version):
            return
        self.__mpcVersion = self._mpcApi.version.split('.')
        if(self.__mpcVersion[0:3] == ['1', '6', '4']):
            self.__switchPauseCalls = True
        if(self.__mpcVersion[0:3] >= ['1', '6', '5']):
            self.speedSupported = True            
        if(filePath):
            self.openFile(filePath)
    
    def openFile(self, filePath):
        self._mpcApi.openFile(filePath)
        
    def displayMessage(self, message, duration = (constants.OSD_DURATION*1000)):
        self._mpcApi.sendOsd(message, constants.MPC_OSD_POSITION, duration)

    @retry(MpcHcApi.PlayerNotReadyException, constants.MPC_MAX_RETRIES, constants.MPC_RETRY_WAIT_TIME, 1)
    def setPaused(self, value):
        if self._mpcApi.filePlaying:
            if self.__switchPauseCalls:
                value = not value
            if value:
                self._mpcApi.pause()
            else:
                self._mpcApi.unpause()
            
    @retry(MpcHcApi.PlayerNotReadyException, constants.MPC_MAX_RETRIES, constants.MPC_RETRY_WAIT_TIME, 1)
    def setPosition(self, value):
        if self._mpcApi.filePlaying:
            self._mpcApi.seek(value)
        
    def __getPosition(self):
        self.__positionUpdate.clear()
        self._mpcApi.askForCurrentPosition()
        self.__positionUpdate.wait(constants.MPC_LOCK_WAIT_TIME)
        return self._mpcApi.lastFilePosition
    
    @retry(MpcHcApi.PlayerNotReadyException, constants.MPC_MAX_RETRIES, constants.MPC_RETRY_WAIT_TIME, 1)
    def askForStatus(self):
        if(self._mpcApi.filePlaying and self.__preventAsking.wait(0) and self.__fileUpdate.acquire(0)):
            self.__fileUpdate.release()
            position = self.__getPosition()
            paused = self._mpcApi.isPaused()
            position = float(position)
            if(self.__preventAsking.wait(0) and self.__fileUpdate.acquire(0)):
                self.__client.updatePlayerStatus(paused, position)
                self.__fileUpdate.release()
            return
        self.__echoGlobalStatus()
            
    def __echoGlobalStatus(self):
        self.__client.updatePlayerStatus(self.__client.getGlobalPaused(), self.__client.getGlobalPosition())

    def __forcePause(self):
        for _ in xrange(constants.MPC_MAX_RETRIES):
            self.setPaused(True)
            time.sleep(constants.MPC_RETRY_WAIT_TIME)
        
    def __refreshMpcPlayState(self):
        for _ in xrange(2): 
            self._mpcApi.playPause()
            time.sleep(constants.MPC_PAUSE_TOGGLE_DELAY)

    def _setPausedAccordinglyToServer(self):
        self.__forcePause()
        self.setPaused(self.__client.getGlobalPaused())
        if(self._mpcApi.isPaused() <> self.__client.getGlobalPaused()):
            self.__refreshMpcPlayState()
            if(self._mpcApi.isPaused() <> self.__client.getGlobalPaused()):
                self.__setUpStateForNewlyOpenedFile()
    
    @retry(MpcHcApi.PlayerNotReadyException, constants.MPC_MAX_RETRIES, constants.MPC_RETRY_WAIT_TIME, 1)                
    def __setUpStateForNewlyOpenedFile(self):
        self._setPausedAccordinglyToServer()
        self._mpcApi.seek(self.__client.getGlobalPosition())
 
    def __handleUpdatedFilename(self):
        with self.__fileUpdate:
            self.__setUpStateForNewlyOpenedFile()
            args = (self._mpcApi.filePlaying, self._mpcApi.fileDuration, self._mpcApi.filePath)
            self.reactor.callFromThread(self.__client.updateFile, *args)

    def sendCustomCommand(self, cmd, val):
        self._mpcApi.sendRawCommand(cmd, val)
        
    @staticmethod
    def getDefaultPlayerPathsList():
        return constants.MPC_PATHS
    
    @staticmethod
    def getIconPath(path):
        if(MPCHCAPIPlayer.getExpandedPath(path).lower().endswith(u'mpc-hc64.exe'.lower())):
            return constants.MPC64_ICONPATH
        else:
            return constants.MPC_ICONPATH
    
    @staticmethod
    def isValidPlayerPath(path):
        if(MPCHCAPIPlayer.getExpandedPath(path)):
            return True
        return False

    @staticmethod
    def getExpandedPath(path):
        if(os.path.isfile(path)):
            if(path.lower().endswith(u'mpc-hc.exe'.lower()) or path.lower().endswith(u'mpc-hc64.exe'.lower())):
                return path
        if(os.path.isfile(path + u"mpc-hc.exe")):
            path += u"mpc-hc.exe"
            return path
        if(os.path.isfile(path + u"\\mpc-hc.exe")):
            path += u"\\mpc-hc.exe"
            return path
        if(os.path.isfile(path + u"mpc-hc64.exe")):
            path += u"mpc-hc64.exe"
            return path
        if(os.path.isfile(path + u"\\mpc-hc64.exe")):
            path += u"\\mpc-hc64.exe"
            return path

########NEW FILE########
__FILENAME__ = mplayer
import subprocess
import re
import threading
from syncplay.players.basePlayer import BasePlayer
from syncplay import constants
from syncplay.messages import getMessage
import os

class MplayerPlayer(BasePlayer):
    speedSupported = True
    RE_ANSWER = re.compile(constants.MPLAYER_ANSWER_REGEX)
    SLAVE_ARGS = constants.MPLAYER_SLAVE_ARGS
    POSITION_QUERY = 'time_pos'
    OSD_QUERY = 'osd_show_text'

    def __init__(self, client, playerPath, filePath, args):
        from twisted.internet import reactor
        self.reactor = reactor
        self._client = client
        self._paused = None
        self._duration = None
        self._filename = None
        self._filepath = None
        try:
            self._listener = self.__Listener(self, playerPath, filePath, args)
        except ValueError:
            self._client.ui.showMessage(getMessage("en", "mplayer-file-required-notification"))
            self._client.ui.showMessage(getMessage("en", "mplayer-file-required-notification/example"))
            self.reactor.callFromThread(self._client.stop, (True),)
            return
        self._listener.setDaemon(True)
        self._listener.start()

        self._durationAsk = threading.Event()
        self._filenameAsk = threading.Event()
        self._pathAsk = threading.Event()

        self._positionAsk = threading.Event()
        self._pausedAsk = threading.Event()

        self._preparePlayer()

    def _fileUpdateClearEvents(self):
        self._durationAsk.clear()
        self._filenameAsk.clear()
        self._pathAsk.clear()

    def _fileUpdateWaitEvents(self):
        self._durationAsk.wait()
        self._filenameAsk.wait()
        self._pathAsk.wait()

    def _onFileUpdate(self):
        self._fileUpdateClearEvents()
        self._getFilename()
        self._getLength()
        self._getFilepath()
        self._fileUpdateWaitEvents()
        self._client.updateFile(self._filename, self._duration, self._filepath)

    def _preparePlayer(self):
        self.reactor.callFromThread(self._client.initPlayer, (self),)
        self._onFileUpdate()

    def askForStatus(self):
        self._positionAsk.clear()
        self._pausedAsk.clear()
        self._getPaused()
        self._getPosition()
        self._positionAsk.wait()
        self._pausedAsk.wait()
        self._client.updatePlayerStatus(self._paused, self._position)

    def _setProperty(self, property_, value):
        self._listener.sendLine("set_property {} {}".format(property_, value))

    def _getProperty(self, property_):
        self._listener.sendLine("get_property {}".format(property_))

    def displayMessage(self, message, duration=(constants.OSD_DURATION * 1000)):
        self._listener.sendLine(u'{} "{!s}" {} {}'.format(self.OSD_QUERY, message, duration, constants.MPLAYER_OSD_LEVEL).encode('utf-8'))

    def setSpeed(self, value):
        self._setProperty('speed', "{:.2f}".format(value))

    def openFile(self, filePath):
        self._listener.sendLine(u'loadfile {}'.format(self._quoteArg(filePath)))
        self._onFileUpdate()
        if self._client.getGlobalPaused():
            self._listener.sendLine('pause')
        self.setPosition(self._client.getGlobalPosition())

    def setPosition(self, value):
        self._position = value
        self._setProperty(self.POSITION_QUERY, "{}".format(value))

    def setPaused(self, value):
        if self._paused <> value:
            self._listener.sendLine('pause')

    def _getFilename(self):
        self._getProperty('filename')

    def _getLength(self):
        self._getProperty('length')

    def _getFilepath(self):
        self._getProperty('path')

    def _getPaused(self):
        self._getProperty('pause')

    def _getPosition(self):
        self._getProperty(self.POSITION_QUERY)

    def _quoteArg(self, arg):
        arg = arg.replace('\\', '\\\\')
        arg = arg.replace("'", "\\'")
        arg = arg.replace('"', '\\"')
        return u'"{}"'.format(arg)

    def lineReceived(self, line):
        match = self.RE_ANSWER.match(line)
        if not match:
            return
        name, value = match.group(1).lower(), match.group(2)
        if(name == self.POSITION_QUERY):
            self._position = float(value)
            self._positionAsk.set()
        elif(name == "pause"):
            self._paused = bool(value == 'yes')
            self._pausedAsk.set()
        elif(name == "length"):
            self._duration = float(value)
            self._durationAsk.set()
        elif(name == "path"):
            self._filepath = value
            self._pathAsk.set()
        elif(name == "filename"):
            self._filename = value.decode('utf-8')
            self._filenameAsk.set()

    @staticmethod
    def run(client, playerPath, filePath, args):
        mplayer = MplayerPlayer(client, MplayerPlayer.getExpandedPath(playerPath), filePath, args)
        return mplayer

    @staticmethod
    def getDefaultPlayerPathsList():
        l = []
        for path in constants.MPLAYER_PATHS:
            p = MplayerPlayer.getExpandedPath(path)
            if p:
                l.append(p)
        return l

    @staticmethod
    def getIconPath(path):
        return constants.MPLAYER_ICONPATH

    @staticmethod
    def isValidPlayerPath(path):
        if("mplayer" in path and MplayerPlayer.getExpandedPath(path)):
            return True
        return False

    @staticmethod
    def getExpandedPath(playerPath):
        if not os.path.isfile(playerPath):
            if os.path.isfile(playerPath + u"mplayer.exe"):
                playerPath += u"mplayer.exe"
                return playerPath
            elif os.path.isfile(playerPath + u"\\mplayer.exe"):
                playerPath += u"\\mplayer.exe"
                return playerPath
        if os.access(playerPath, os.X_OK):
            return playerPath
        for path in os.environ['PATH'].split(':'):
            path = os.path.join(os.path.realpath(path), playerPath)
            if os.access(path, os.X_OK):
                return path

    def notMplayer2(self):
        print getMessage("en", "mplayer2-required")
        self._listener.sendLine('quit')
        self.reactor.callFromThread(self._client.stop, (True),)

    def _takeLocksDown(self):
        self._durationAsk.set()
        self._filenameAsk.set()
        self._pathAsk.set()
        self._positionAsk.set()
        self._pausedAsk.set()

    def drop(self):
        self._listener.sendLine('quit')
        self._takeLocksDown()
        self.reactor.callFromThread(self._client.stop, (False),)

    class __Listener(threading.Thread):
        def __init__(self, playerController, playerPath, filePath, args):
            self.__playerController = playerController
            if(not filePath):
                raise ValueError()
            if '://' not in filePath:
                if not os.path.isfile(filePath) and 'PWD' in os.environ:
                    filePath = os.environ['PWD'] + os.path.sep + filePath
                filePath = os.path.realpath(filePath)

            call = [playerPath, filePath]
            call.extend(playerController.SLAVE_ARGS)
            if(args):
                call.extend(args)
            # At least mpv may output escape sequences which result in syncplay
            # trying to parse something like
            # "\x1b[?1l\x1b>ANS_filename=blah.mkv". Work around this by
            # unsetting TERM.
            env = os.environ.copy()
            if 'TERM' in env:
                del env['TERM']
            self.__process = subprocess.Popen(call, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.__getCwd(filePath, env), env=env)
            threading.Thread.__init__(self, name="MPlayer Listener")


        def __getCwd(self, filePath, env):
            if os.path.isfile(filePath):
                cwd = os.path.dirname(filePath)
            elif 'HOME' in env:
                cwd = env['HOME']
            elif 'APPDATA' in env:
                cwd = env['APPDATA']
            else:
                cwd = None
            return cwd

        def run(self):
            line = self.__process.stdout.readline()
            if("MPlayer 1" in line):
                self.__playerController.notMplayer2()
            else:
                line = line.rstrip("\r\n")
                self.__playerController.lineReceived(line)
            while(self.__process.poll() is None):
                line = self.__process.stdout.readline()
                line = line.rstrip("\r\n")
                self.__playerController.lineReceived(line)
            self.__playerController.drop()

        def sendLine(self, line):
            try:
                line = (line.decode('utf8') + u"\n").encode('utf8')
                self.__process.stdin.write(line)
            except IOError:
                pass

########NEW FILE########
__FILENAME__ = mpv
from syncplay.players.mplayer import MplayerPlayer
from syncplay import constants
import os

class MpvPlayer(MplayerPlayer):
    SLAVE_ARGS = constants.MPV_SLAVE_ARGS
    POSITION_QUERY = 'time-pos'
    OSD_QUERY = 'show_text'

    def _setProperty(self, property_, value):
        self._listener.sendLine("no-osd set {} {}".format(property_, value))

    def setPaused(self, value):
        if self._paused <> value:
            self._listener.sendLine('cycle pause')

    @staticmethod
    def run(client, playerPath, filePath, args):
        return MpvPlayer(client, MpvPlayer.getExpandedPath(playerPath), filePath, args)

    @staticmethod
    def getDefaultPlayerPathsList():
        l = []
        for path in constants.MPV_PATHS:
            p = MpvPlayer.getExpandedPath(path)
            if p:
                l.append(p)
        return l

    @staticmethod
    def isValidPlayerPath(path):
        if("mpv" in path and MpvPlayer.getExpandedPath(path)):
            return True
        return False

    @staticmethod
    def getExpandedPath(playerPath):
        if not os.path.isfile(playerPath):
            if os.path.isfile(playerPath + u"mpv.exe"):
                playerPath += u"mpv.exe"
                return playerPath
            elif os.path.isfile(playerPath + u"\\mpv.exe"):
                playerPath += u"\\mpv.exe"
                return playerPath
        if os.access(playerPath, os.X_OK):
            return playerPath
        for path in os.environ['PATH'].split(':'):
            path = os.path.join(os.path.realpath(path), playerPath)
            if os.access(path, os.X_OK):
                return path

    @staticmethod
    def getIconPath(path):
        return constants.MPV_ICONPATH

########NEW FILE########
__FILENAME__ = playerFactory
import syncplay.players

class PlayerFactory(object):
    def __init__(self):
        self._players = syncplay.players.getAvailablePlayers()
        
    def getAvailablePlayerPaths(self):
        l = []
        for player in self._players:
            l.extend(player.getDefaultPlayerPathsList())
        return l
    
    def getPlayerByPath(self, path):
        for player in self._players:
            if(player.isValidPlayerPath(path)):
                return player
                
    def getPlayerIconByPath(self, path):
        for player in self._players:
            if(player.isValidPlayerPath(path)):
                return player.getIconPath(path)
        return None
    
    def getExpandedPlayerPathByPath(self, path):
        for player in self._players:
            if(player.isValidPlayerPath(path)):
                return player.getExpandedPath(path)
        return None

########NEW FILE########
__FILENAME__ = vlc
import subprocess
import re
import threading
from syncplay.players.basePlayer import BasePlayer
from syncplay import constants, utils
import os
import sys
import random
import socket
import asynchat, asyncore
import urllib
from syncplay.messages import getMessage
import time

class VlcPlayer(BasePlayer):
    speedSupported = True
    RE_ANSWER = re.compile(constants.VLC_ANSWER_REGEX)
    SLAVE_ARGS = constants.VLC_SLAVE_ARGS
    if not sys.platform.startswith('darwin'):
         SLAVE_ARGS.extend(constants.VLC_SLAVE_NONOSX_ARGS)
    random.seed()
    vlcport = random.randrange(constants.VLC_MIN_PORT, constants.VLC_MAX_PORT) if (constants.VLC_MIN_PORT < constants.VLC_MAX_PORT) else constants.VLC_MIN_PORT

    def __init__(self, client, playerPath, filePath, args):
        from twisted.internet import reactor
        self.reactor = reactor
        self._client = client
        self._paused = None
        self._duration = None
        self._filename = None
        self._filepath = None
        self._filechanged = False

        self._durationAsk = threading.Event()
        self._filenameAsk = threading.Event()
        self._pathAsk = threading.Event()
        self._positionAsk = threading.Event()
        self._pausedAsk = threading.Event()
        self._vlcready = threading.Event()
        self._vlcclosed = threading.Event()
        try:
            self._listener = self.__Listener(self, playerPath, filePath, args, self._vlcready, self._vlcclosed)
        except ValueError:
            self._client.ui.showErrorMessage(getMessage("en", "vlc-failed-connection"), True)
            self.reactor.callFromThread(self._client.stop, (True),)
            return
        self._listener.setDaemon(True)
        self._listener.start()
        if(not self._vlcready.wait(constants.VLC_OPEN_MAX_WAIT_TIME)):
            self._vlcready.set()
            self._client.ui.showErrorMessage(getMessage("en", "vlc-failed-connection"), True)
            self.reactor.callFromThread(self._client.stop, (True),)
        self.reactor.callFromThread(self._client.initPlayer, (self),)

    def _fileUpdateClearEvents(self):
        self._durationAsk.clear()
        self._filenameAsk.clear()
        self._pathAsk.clear()

    def _fileUpdateWaitEvents(self):
        self._durationAsk.wait()
        self._filenameAsk.wait()
        self._pathAsk.wait()

    def _onFileUpdate(self):
        self._fileUpdateClearEvents()
        self._getFileInfo()
        self._fileUpdateWaitEvents()
        args = (self._filename, self._duration, self._filepath)
        self.reactor.callFromThread(self._client.updateFile, *args)
        self.setPaused(self._client.getGlobalPaused())
        self.setPosition(self._client.getGlobalPosition())

    def askForStatus(self):
        self._filechanged = False
        self._positionAsk.clear()
        self._pausedAsk.clear()
        self._listener.sendLine(".")
        if self._filechanged == False:
            self._positionAsk.wait()
            self._pausedAsk.wait()
            self._client.updatePlayerStatus(self._paused, self._position)
        else:
            self._client.updatePlayerStatus(self._client.getGlobalPaused(), self._client.getGlobalPosition())

    def displayMessage(self, message, duration=constants.OSD_DURATION * 1000):
        duration /= 1000
        self._listener.sendLine('display-osd: {}, {}, {}'.format('top-right', duration, message.encode('ascii', 'ignore'))) #TODO: Proper Unicode support

    def setSpeed(self, value):
        self._listener.sendLine("set-rate: {:.2n}".format(value))

    def setPosition(self, value):
        self._position = value
        self._listener.sendLine("set-position: {:n}".format(value))

    def setPaused(self, value):
        self._paused = value
        self._listener.sendLine('set-playstate: {}'.format("paused" if value else "playing"))

    def getMRL(self, fileURL):
        fileURL = fileURL.replace(u'\\', u'/')
        fileURL = fileURL.encode('utf8')
        fileURL = urllib.quote_plus(fileURL)
        if sys.platform.startswith('win'):
            fileURL = "file:///" + fileURL
        else:
            fileURL = "file://" + fileURL
        fileURL = fileURL.replace("+", "%20")
        return fileURL

    def _isASCII (self, s):
        return all(ord(c) < 128 for c in s)

    def openFile(self, filePath):
        if (self._isASCII(filePath) == True):
            self._listener.sendLine('load-file: {}'.format(filePath.encode('ascii', 'ignore')))
        else:
            fileURL = self.getMRL(filePath)
            self._listener.sendLine('load-file: {}'.format(fileURL))

    def _getFileInfo(self):
        self._listener.sendLine("get-duration")
        self._listener.sendLine("get-filepath")
        self._listener.sendLine("get-filename")

    def lineReceived(self, line):
        match, name, value = self.RE_ANSWER.match(line), "", ""
        if match:
            name, value = match.group('command'), match.group('argument')

        if(line == "filepath-change-notification"):
            self._filechanged = True
            t = threading.Thread(target=self._onFileUpdate)
            t.setDaemon(True)
            t.start()
        elif (name == "filepath" and value != "no-input"):
            self._filechanged = True
            if("file://" in value):
                value = value.replace("file://", "")
                if(not os.path.isfile(value)):
                    value = value.lstrip("/")
            self._filepath = value
            self._pathAsk.set()
        elif(name == "duration" and (value != "no-input")):
            self._duration = float(value.replace(",", "."))
            self._durationAsk.set()
        elif(name == "playstate"):
            self._paused = bool(value != 'playing') if(value != "no-input" and self._filechanged == False) else self._client.getGlobalPaused()
            self._pausedAsk.set()
        elif(name == "position"):
            self._position = float(value.replace(",", ".")) if (value != "no-input" and self._filechanged == False) else self._client.getGlobalPosition()
            self._positionAsk.set()
        elif(name == "filename"):
            self._filechanged = True
            self._filename = value.decode('utf-8')
            self._filenameAsk.set()
        elif(line.startswith("interface-version: ")):
            interface_version = line[19:24]
            if (int(interface_version.replace(".", "")) < int(constants.VLC_INTERFACE_MIN_VERSION.replace(".", ""))):
                self._client.ui.showErrorMessage(getMessage("en", "vlc-interface-version-mismatch").format(str(interface_version), str(constants.VLC_INTERFACE_MIN_VERSION)))
        elif (line[:16] == "VLC media player"):
            vlc_version = line[17:22]
            if (int(vlc_version.replace(".", "")) < int(constants.VLC_MIN_VERSION.replace(".", ""))):
                self._client.ui.showErrorMessage(getMessage("en", "vlc-version-mismatch").format(str(vlc_version), str(constants.VLC_MIN_VERSION)))
            self._vlcready.set()
            self._listener.sendLine("get-interface-version")


    @staticmethod
    def run(client, playerPath, filePath, args):
        vlc = VlcPlayer(client, VlcPlayer.getExpandedPath(playerPath), filePath, args)
        return vlc

    @staticmethod
    def getDefaultPlayerPathsList():
        l = []
        for path in constants.VLC_PATHS:
            p = VlcPlayer.getExpandedPath(path)
            if p:
                l.append(p)
        return l

    @staticmethod
    def isValidPlayerPath(path):
        if("vlc" in path.lower() and VlcPlayer.getExpandedPath(path)):
            return True
        return False

    @staticmethod
    def getIconPath(path):
        return constants.VLC_ICONPATH

    @staticmethod
    def getExpandedPath(playerPath):
        if not os.path.isfile(playerPath):
            if os.path.isfile(playerPath + u"vlc.exe"):
                playerPath += u"vlc.exe"
                return playerPath
            elif os.path.isfile(playerPath + u"\\vlc.exe"):
                playerPath += u"\\vlc.exe"
                return playerPath
        if os.access(playerPath, os.X_OK):
            return playerPath
        for path in os.environ['PATH'].split(':'):
            path = os.path.join(os.path.realpath(path), playerPath)
            if os.access(path, os.X_OK):
                return path

    def drop(self):
        self._vlcclosed.clear()
        self._listener.sendLine('close-vlc')
        self._vlcclosed.wait()
        self._durationAsk.set()
        self._filenameAsk.set()
        self._pathAsk.set()
        self._positionAsk.set()
        self._vlcready.set()
        self._pausedAsk.set()
        self.reactor.callFromThread(self._client.stop, (False),)

    class __Listener(threading.Thread, asynchat.async_chat):
        def __init__(self, playerController, playerPath, filePath, args, vlcReady, vlcClosed):
            self.__playerController = playerController
            call = [playerPath]
            if(filePath):
                if (self.__playerController._isASCII(filePath) == True):
                    call.append(filePath)
                else:
                    call.append(self.__playerController.getMRL(filePath))
            def _usevlcintf(vlcIntfPath, vlcIntfUserPath):
                vlcSyncplayInterfacePath = vlcIntfPath + "syncplay.lua"
                if not os.path.isfile(vlcSyncplayInterfacePath):
                    vlcSyncplayInterfacePath = vlcIntfUserPath + "syncplay.lua"
                if os.path.isfile(vlcSyncplayInterfacePath):
                    with open(vlcSyncplayInterfacePath, 'rU') as interfacefile:
                        for line in interfacefile:
                            if "local connectorversion" in line:
                                interface_version = line[26:31]
                                if (int(interface_version.replace(".", "")) >= int(constants.VLC_INTERFACE_MIN_VERSION.replace(".", ""))):
                                    return True
                                else:
                                    playerController._client.ui.showErrorMessage(getMessage("en", "vlc-interface-oldversion-ignored"))
                                    return False
                playerController._client.ui.showErrorMessage(getMessage("en", "vlc-interface-not-installed"))
                return False
            if sys.platform.startswith('linux'):
                playerController.vlcIntfPath = "/usr/lib/vlc/lua/intf/"
                playerController.vlcIntfUserPath = os.path.join(os.getenv('HOME', '.'), ".local/share/vlc/lua/intf/")
            elif sys.platform.startswith('darwin'):
                playerController.vlcIntfPath = "/Applications/VLC.app/Contents/MacOS/share/lua/intf/"
                playerController.vlcIntfUserPath = os.path.join(os.getenv('HOME', '.'), "Library/Application Support/org.videolan.vlc/lua/intf/")
            else:
                playerController.vlcIntfPath = os.path.dirname(playerPath).replace("\\", "/") + "/lua/intf/"
                playerController.vlcIntfUserPath = os.path.join(os.getenv('APPDATA', '.'), "VLC\\lua\\intf\\")
            playerController.vlcModulePath = playerController.vlcIntfPath + "modules/?.luac"
            if _usevlcintf(playerController.vlcIntfPath, playerController.vlcIntfUserPath) == True:
                playerController.SLAVE_ARGS.append('--lua-config=syncplay={{port=\"{}\"}}'.format(str(playerController.vlcport)))
            else:
                if sys.platform.startswith('linux'):
                    playerController.vlcDataPath = "/usr/lib/syncplay/resources"
                else:
                    playerController.vlcDataPath = utils.findWorkingDir() + "\\resources"
                playerController.SLAVE_ARGS.append('--data-path={}'.format(playerController.vlcDataPath))
                playerController.SLAVE_ARGS.append('--lua-config=syncplay={{modulepath=\"{}\",port=\"{}\"}}'.format(playerController.vlcModulePath, str(playerController.vlcport)))

            call.extend(playerController.SLAVE_ARGS)
            if(args):
                call.extend(args)

            self._vlcready = vlcReady
            self._vlcclosed = vlcClosed
            self.__process = subprocess.Popen(call, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            for line in iter(self.__process.stderr.readline, ''):
                if "[syncplay]" in line:
                    if "Listening on host" in line:
                        break
                    if "Hosting Syncplay" in line:
                        break
                    elif "Couldn't find lua interface" in line:
                        playerController._client.ui.showErrorMessage(getMessage("en", "vlc-failed-noscript").format(line), True)
                        break
                    elif "lua interface error" in line:
                        playerController._client.ui.showErrorMessage(getMessage("en", "vlc-error-echo").format(line), True)
                        break
            threading.Thread.__init__(self, name="VLC Listener")
            asynchat.async_chat.__init__(self)
            self.set_terminator("\n")
            self._ibuffer = []
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sendingData = threading.Lock()

        def initiate_send(self):
            with self._sendingData:
                asynchat.async_chat.initiate_send(self)

        def run(self):
            self._vlcready.clear()
            self.connect(('localhost', self.__playerController.vlcport))
            asyncore.loop()

        def handle_connect(self):
            asynchat.async_chat.handle_connect(self)
            self._vlcready.set()

        def collect_incoming_data(self, data):
            self._ibuffer.append(data)

        def handle_close(self):
            asynchat.async_chat.handle_close(self)
            self.__playerController.drop()

        def found_terminator(self):
#            print "received: {}".format("".join(self._ibuffer))
            self.__playerController.lineReceived("".join(self._ibuffer))
            self._ibuffer = []

        def sendLine(self, line):
            if(self.connected):
#                print "send: {}".format(line)
                try:
                    self.push(line + "\n")
                except:
                    pass
            if(line == "close-vlc"):
                self._vlcclosed.set()

########NEW FILE########
__FILENAME__ = protocols
# coding:utf8
from twisted.protocols.basic import LineReceiver
import json
import syncplay
from functools import wraps
import time
from syncplay.messages import getMessage
from syncplay.constants import PING_MOVING_AVERAGE_WEIGHT


class JSONCommandProtocol(LineReceiver):
    def handleMessages(self, messages):
        for message in messages.iteritems():
            command = message[0]
            if command == "Hello":
                self.handleHello(message[1])
            elif command == "Set":
                self.handleSet(message[1])
            elif command == "List":
                self.handleList(message[1])
            elif command == "State":
                self.handleState(message[1])
            elif command == "Error":
                self.handleError(message[1])
            else:
                self.dropWithError(getMessage("en", "unknown-command-server-error").format(message[1]))  # TODO: log, not drop

    def lineReceived(self, line):
        line = line.strip()
        if not line:
            return
        try:
            messages = json.loads(line)
        except:
            self.dropWithError(getMessage("en", "not-json-server-error").format(line))
            return
        self.handleMessages(messages)

    def sendMessage(self, dict_):
        line = json.dumps(dict_)
        self.sendLine(line)

    def drop(self):
        self.transport.loseConnection()

    def dropWithError(self, error):
        raise NotImplementedError()


class SyncClientProtocol(JSONCommandProtocol):
    def __init__(self, client):
        self._client = client
        self.clientIgnoringOnTheFly = 0
        self.serverIgnoringOnTheFly = 0
        self.logged = False
        self._pingService = PingService()

    def connectionMade(self):
        self._client.initProtocol(self)
        self.sendHello()

    def connectionLost(self, reason):
        self._client.destroyProtocol()

    def dropWithError(self, error):
        self._client.ui.showErrorMessage(error)
        self._client.protocolFactory.stopRetrying()
        self.drop()

    def _extractHelloArguments(self, hello):
        username = hello["username"] if hello.has_key("username") else None
        roomName = hello["room"]["name"] if hello.has_key("room") else None
        version = hello["version"] if hello.has_key("version") else None
        motd = hello["motd"] if hello.has_key("motd") else None
        return username, roomName, version, motd

    def handleHello(self, hello):
        username, roomName, version, motd = self._extractHelloArguments(hello)
        if(not username or not roomName or not version):
            self.dropWithError(getMessage("en", "hello-server-error").format(hello))
        elif(version.split(".")[0:2] != syncplay.version.split(".")[0:2]):
            self.dropWithError(getMessage("en", "version-mismatch-server-error".format(hello)))
        else:
            self._client.setUsername(username)
            self._client.setRoom(roomName)
        self.logged = True
        if(motd):
            self._client.ui.showMessage(motd, True, True)
        self._client.ui.showMessage(getMessage("en", "connected-successful-notification"))
        self._client.sendFile()

    def sendHello(self):
        hello = {}
        hello["username"] = self._client.getUsername()
        password = self._client.getPassword()
        if(password): hello["password"] = password
        room = self._client.getRoom()
        if(room): hello["room"] = {"name" :room}
        hello["version"] = syncplay.version
        self.sendMessage({"Hello": hello})

    def _SetUser(self, users):
        for user in users.iteritems():
            username = user[0]
            settings = user[1]
            room = settings["room"]["name"] if settings.has_key("room") else None
            file_ = settings["file"] if settings.has_key("file") else None
            if(settings.has_key("event")):
                if(settings["event"].has_key("joined")):
                    self._client.userlist.addUser(username, room, file_)
                elif(settings["event"].has_key("left")):
                    self._client.removeUser(username)
            else:
                self._client.userlist.modUser(username, room, file_)

    def handleSet(self, settings):
        for set_ in settings.iteritems():
            command = set_[0]
            if command == "room":
                roomName = set_[1]["name"] if set_[1].has_key("name") else None
                self._client.setRoom(roomName)
            elif command == "user":
                self._SetUser(set_[1])

    def sendSet(self, setting):
        self.sendMessage({"Set": setting})

    def sendRoomSetting(self, roomName, password=None):
        setting = {}
        setting["name"] = roomName
        if(password): setting["password"] = password
        self.sendSet({"room": setting})

    def sendFileSetting(self, file_):
        self.sendSet({"file": file_})
        self.sendList()

    def handleList(self, userList):
        self._client.userlist.clearList()
        for room in userList.iteritems():
            roomName = room[0]
            for user in room[1].iteritems():
                userName = user[0]
                file_ = user[1]['file'] if user[1]['file'] <> {} else None
                self._client.userlist.addUser(userName, roomName, file_, noMessage=True)
        self._client.userlist.showUserList()

    def sendList(self):
        self.sendMessage({"List": None})

    def _extractStatePlaystateArguments(self, state):
        position = state["playstate"]["position"] if state["playstate"].has_key("position") else 0
        paused = state["playstate"]["paused"] if state["playstate"].has_key("paused") else None
        doSeek = state["playstate"]["doSeek"] if state["playstate"].has_key("doSeek") else None
        setBy = state["playstate"]["setBy"] if state["playstate"].has_key("setBy") else None
        return position, paused, doSeek, setBy

    def _handleStatePing(self, state):
        if (state["ping"].has_key("latencyCalculation")):
            latencyCalculation = state["ping"]["latencyCalculation"]
        if ("clientLatencyCalculation" in state["ping"]):
            timestamp = state["ping"]["clientLatencyCalculation"]
            senderRtt = state["ping"]["serverRtt"]
            self._pingService.receiveMessage(timestamp, senderRtt)
        messageAge = self._pingService.getLastForwardDelay()
        return messageAge, latencyCalculation

    def handleState(self, state):
        position, paused, doSeek, setBy = None, None, None, None
        messageAge = 0
        if(state.has_key("ignoringOnTheFly")):
            ignore = state["ignoringOnTheFly"]
            if(ignore.has_key("server")):
                self.serverIgnoringOnTheFly = ignore["server"]
                self.clientIgnoringOnTheFly = 0
            elif(ignore.has_key("client")):
                if(ignore['client']) == self.clientIgnoringOnTheFly:
                    self.clientIgnoringOnTheFly = 0
        if(state.has_key("playstate")):
            position, paused, doSeek, setBy = self._extractStatePlaystateArguments(state)
        if(state.has_key("ping")):
            messageAge, latencyCalculation = self._handleStatePing(state)
        if(position is not None and paused is not None and not self.clientIgnoringOnTheFly):
            self._client.updateGlobalState(position, paused, doSeek, setBy, messageAge)
        position, paused, doSeek, stateChange = self._client.getLocalState()
        self.sendState(position, paused, doSeek, latencyCalculation, stateChange)

    def sendState(self, position, paused, doSeek, latencyCalculation, stateChange=False):
        state = {}
        positionAndPausedIsSet = position is not None and paused is not None
        clientIgnoreIsNotSet = self.clientIgnoringOnTheFly == 0 or self.serverIgnoringOnTheFly != 0
        if(clientIgnoreIsNotSet and positionAndPausedIsSet):
            state["playstate"] = {}
            state["playstate"]["position"] = position
            state["playstate"]["paused"] = paused
            if(doSeek): state["playstate"]["doSeek"] = doSeek
        state["ping"] = {}
        if(latencyCalculation):
            state["ping"]["latencyCalculation"] = latencyCalculation
        state["ping"]["clientLatencyCalculation"] = self._pingService.newTimestamp()
        state["ping"]["clientRtt"] = self._pingService.getRtt()
        if(stateChange):
            self.clientIgnoringOnTheFly += 1
        if(self.serverIgnoringOnTheFly or self.clientIgnoringOnTheFly):
            state["ignoringOnTheFly"] = {}
            if(self.serverIgnoringOnTheFly):
                state["ignoringOnTheFly"]["server"] = self.serverIgnoringOnTheFly
                self.serverIgnoringOnTheFly = 0
            if(self.clientIgnoringOnTheFly):
                state["ignoringOnTheFly"]["client"] = self.clientIgnoringOnTheFly
        self.sendMessage({"State": state})

    def handleError(self, error):
        self.dropWithError(error["message"])  # TODO: more processing and fallbacking

    def sendError(self, message):
        self.sendMessage({"Error": {"message": message}})

class SyncServerProtocol(JSONCommandProtocol):
    def __init__(self, factory):
        self._factory = factory
        self._logged = False
        self.clientIgnoringOnTheFly = 0
        self.serverIgnoringOnTheFly = 0
        self._pingService = PingService()
        self._clientLatencyCalculation = 0
        self._clientLatencyCalculationArrivalTime = 0
        self._watcher = None

    def __hash__(self):
        return hash('|'.join((
            self.transport.getPeer().host,
            str(id(self)),
        )))

    def requireLogged(f):  # @NoSelf
        @wraps(f)
        def wrapper(self, *args, **kwds):
            if(not self._logged):
                self.dropWithError(getMessage("en", "not-known-server-error"))
            return f(self, *args, **kwds)
        return wrapper

    def dropWithError(self, error):
        print getMessage("en", "client-drop-server-error").format(self.transport.getPeer().host, error)
        self.sendError(error)
        self.drop()

    def connectionLost(self, reason):
        self._factory.removeWatcher(self._watcher)

    def isLogged(self):
        return self._logged

    def _extractHelloArguments(self, hello):
        roomName, roomPassword = None, None
        username = hello["username"] if hello.has_key("username") else None
        username = username.strip()
        serverPassword = hello["password"] if hello.has_key("password") else None
        room = hello["room"] if hello.has_key("room") else None
        if(room):
            roomName = room["name"] if room.has_key("name") else None
            roomName = roomName.strip()
            roomPassword = room["password"] if room.has_key("password") else None
        version = hello["version"] if hello.has_key("version") else None
        return username, serverPassword, roomName, roomPassword, version

    def _checkPassword(self, serverPassword):
        if(self._factory.password):
            if(not serverPassword):
                self.dropWithError(getMessage("en", "password-required-server-error"))
                return False
            if(serverPassword != self._factory.password):
                self.dropWithError(getMessage("en", "wrong-password-server-error"))
                return False
        return True

    def handleHello(self, hello):
        username, serverPassword, roomName, roomPassword, version = self._extractHelloArguments(hello)
        if(not username or not roomName or not version):
            self.dropWithError(getMessage("en", "hello-server-error"))
        elif(version.split(".")[0:2] != syncplay.version.split(".")[0:2]):
            self.dropWithError(getMessage("en", "version-mismatch-server-error"))
        else:
            if(not self._checkPassword(serverPassword)):
                return
            self._factory.addWatcher(self, username, roomName, roomPassword)
            self._logged = True
            self.sendHello(version)

    def setWatcher(self, watcher):
        self._watcher = watcher

    def sendHello(self, clientVersion):
        hello = {}
        username = self._watcher.getName()
        hello["username"] = username
        userIp = self.transport.getPeer().host
        room = self._watcher.getRoom()
        if(room): hello["room"] = {"name": room.getName()}
        hello["version"] = syncplay.version
        hello["motd"] = self._factory.getMotd(userIp, username, room, clientVersion)
        self.sendMessage({"Hello": hello})

    @requireLogged
    def handleSet(self, settings):
        for set_ in settings.iteritems():
            command = set_[0]
            if command == "room":
                roomName = set_[1]["name"] if set_[1].has_key("name") else None
                self._factory.setWatcherRoom(self._watcher, roomName)
            elif command == "file":
                self._watcher.setFile(set_[1])

    def sendSet(self, setting):
        self.sendMessage({"Set": setting})

    def sendUserSetting(self, username, room, file_, event):
        room = {"name": room.getName()}
        user = {}
        user[username] = {}
        user[username]["room"] = room
        if(file_):
            user[username]["file"] = file_
        if(event):
            user[username]["event"] = event
        self.sendSet({"user": user})

    def _addUserOnList(self, userlist, watcher):
        room = watcher.getRoom()
        if room:
            if room.getName() not in userlist:
                userlist[room.getName()] = {}
            userFile = { "position": 0, "file": watcher.getFile() if watcher.getFile() else {} }
            userlist[room.getName()][watcher.getName()] = userFile

    def sendList(self):
        userlist = {}
        watchers = self._factory.getAllWatchersForUser(self._watcher)
        for watcher in watchers:
            self._addUserOnList(userlist, watcher)
        self.sendMessage({"List": userlist})

    @requireLogged
    def handleList(self, _):
        self.sendList()

    def sendState(self, position, paused, doSeek, setBy, forced=False):
        if(self._clientLatencyCalculationArrivalTime):
            processingTime = time.time() - self._clientLatencyCalculationArrivalTime
        else:
            processingTime = 0
        playstate = {
                     "position": position if position else 0,
                     "paused": paused,
                     "doSeek": doSeek,
                     "setBy": setBy.getName()
                    }
        ping = {
                "latencyCalculation": self._pingService.newTimestamp(),
                "serverRtt": self._pingService.getRtt()
                }
        if(self._clientLatencyCalculation):
            ping["clientLatencyCalculation"] = self._clientLatencyCalculation + processingTime
            self._clientLatencyCalculation = 0
        state = {
                 "ping": ping,
                 "playstate": playstate,
                }
        if(forced):
            self.serverIgnoringOnTheFly += 1
        if(self.serverIgnoringOnTheFly or self.clientIgnoringOnTheFly):
            state["ignoringOnTheFly"] = {}
            if(self.serverIgnoringOnTheFly):
                state["ignoringOnTheFly"]["server"] = self.serverIgnoringOnTheFly
            if(self.clientIgnoringOnTheFly):
                state["ignoringOnTheFly"]["client"] = self.clientIgnoringOnTheFly
                self.clientIgnoringOnTheFly = 0
        if(self.serverIgnoringOnTheFly == 0 or forced):
            self.sendMessage({"State": state})


    def _extractStatePlaystateArguments(self, state):
        position = state["playstate"]["position"] if state["playstate"].has_key("position") else 0
        paused = state["playstate"]["paused"] if state["playstate"].has_key("paused") else None
        doSeek = state["playstate"]["doSeek"] if state["playstate"].has_key("doSeek") else None
        return position, paused, doSeek

    @requireLogged
    def handleState(self, state):
        position, paused, doSeek, latencyCalculation = None, None, None, None
        if(state.has_key("ignoringOnTheFly")):
            ignore = state["ignoringOnTheFly"]
            if(ignore.has_key("server")):
                if(self.serverIgnoringOnTheFly == ignore["server"]):
                    self.serverIgnoringOnTheFly = 0
            if(ignore.has_key("client")):
                self.clientIgnoringOnTheFly = ignore["client"]
        if(state.has_key("playstate")):
            position, paused, doSeek = self._extractStatePlaystateArguments(state)
        if(state.has_key("ping")):
            latencyCalculation = state["ping"]["latencyCalculation"] if state["ping"].has_key("latencyCalculation") else 0
            clientRtt = state["ping"]["clientRtt"] if state["ping"].has_key("clientRtt") else 0
            self._clientLatencyCalculation = state["ping"]["clientLatencyCalculation"] if state["ping"].has_key("clientLatencyCalculation") else 0
            self._clientLatencyCalculationArrivalTime = time.time()
            self._pingService.receiveMessage(latencyCalculation, clientRtt)
        if(self.serverIgnoringOnTheFly == 0):
            self._watcher.updateState(position, paused, doSeek, self._pingService.getLastForwardDelay())

    def handleError(self, error):
        self.dropWithError(error["message"])  # TODO: more processing and fallbacking

    def sendError(self, message):
        self.sendMessage({"Error": {"message": message}})

class PingService(object):

    def __init__(self):
        self._rtt = 0
        self._fd = 0
        self._avrRtt = 0

    def newTimestamp(self):
        return time.time()

    def receiveMessage(self, timestamp, senderRtt):
        if(not timestamp):
            return
        self._rtt = time.time() - timestamp
        if(self._rtt < 0 or senderRtt < 0):
            return
        if(not self._avrRtt):
            self._avrRtt = self._rtt
        self._avrRtt = self._avrRtt * PING_MOVING_AVERAGE_WEIGHT + self._rtt * (1 - PING_MOVING_AVERAGE_WEIGHT)
        if(senderRtt < self._rtt):
            self._fd = self._avrRtt / 2 + (self._rtt - senderRtt)
        else:
            self._fd = self._avrRtt / 2

    def getLastForwardDelay(self):
        return self._fd

    def getRtt(self):
        return self._rtt

########NEW FILE########
__FILENAME__ = server
import hashlib
from twisted.internet import task, reactor
from twisted.internet.protocol import Factory
import syncplay
from syncplay.protocols import SyncServerProtocol
import time
from syncplay import constants
import threading
from syncplay.messages import getMessage
import codecs
import os
from string import Template
import argparse
from pprint import pprint

class SyncFactory(Factory):
    def __init__(self, password='', motdFilePath=None, isolateRooms=False):
        print getMessage("en", "welcome-server-notification").format(syncplay.version)
        if(password):
            password = hashlib.md5(password).hexdigest()
        self.password = password
        self._motdFilePath = motdFilePath
        if(not isolateRooms):
            self._roomManager = RoomManager()
        else:
            self._roomManager = PublicRoomManager()

    def buildProtocol(self, addr):
        return SyncServerProtocol(self)

    def sendState(self, watcher, doSeek=False, forcedUpdate=False):
        room = watcher.getRoom()
        if room:
            paused, position = room.isPaused(), room.getPosition()
            setBy = room.getSetBy()
            watcher.sendState(position, paused, doSeek, setBy, forcedUpdate)

    def getMotd(self, userIp, username, room, clientVersion):
        oldClient = False
        if constants.WARN_OLD_CLIENTS:
            if int(clientVersion.replace(".", "")) < int(constants.RECENT_CLIENT_THRESHOLD.replace(".", "")):
                oldClient = True
        if(self._motdFilePath and os.path.isfile(self._motdFilePath)):
            tmpl = codecs.open(self._motdFilePath, "r", "utf-8-sig").read()
            args = dict(version=syncplay.version, userIp=userIp, username=username, room=room)
            try:
                motd = Template(tmpl).substitute(args)
                if oldClient:
                    motdwarning = getMessage("en", "new-syncplay-available-motd-message").format(clientVersion)
                    motd = "{}\n{}".format(motdwarning, motd)
                return motd if len(motd) < constants.SERVER_MAX_TEMPLATE_LENGTH else getMessage("en", "server-messed-up-motd-too-long").format(constants.SERVER_MAX_TEMPLATE_LENGTH, len(motd))
            except ValueError:
                return getMessage("en", "server-messed-up-motd-unescaped-placeholders")
        elif oldClient:
            return getMessage("en", "new-syncplay-available-motd-message").format(clientVersion)
        else:
            return ""

    def addWatcher(self, watcherProtocol, username, roomName, roomPassword):
        username = self._roomManager.findFreeUsername(username)
        watcher = Watcher(self, watcherProtocol, username)
        self.setWatcherRoom(watcher, roomName, asJoin=True)

    def setWatcherRoom(self, watcher, roomName, asJoin=False):
        self._roomManager.moveWatcher(watcher, roomName)
        if asJoin:
            self.sendJoinMessage(watcher)
        else:
            self.sendRoomSwitchMessage(watcher)

    def sendRoomSwitchMessage(self, watcher):
        l = lambda w: w.sendSetting(watcher.getName(), watcher.getRoom(), None, None)
        self._roomManager.broadcast(watcher, l)

    def removeWatcher(self, watcher):
        if watcher.getRoom():
            self.sendLeftMessage(watcher)
            self._roomManager.removeWatcher(watcher)

    def sendLeftMessage(self, watcher):
        l = lambda w: w.sendSetting(watcher.getName(), watcher.getRoom(), None, {"left": True})
        self._roomManager.broadcast(watcher, l)

    def sendJoinMessage(self, watcher):
        l = lambda w: w.sendSetting(watcher.getName(), watcher.getRoom(), None, {"joined": True}) if w != watcher else None
        self._roomManager.broadcast(watcher, l)

    def sendFileUpdate(self, watcher, file_):
        l = lambda w: w.sendSetting(watcher.getName(), watcher.getRoom(), watcher.getFile(), None)
        self._roomManager.broadcast(watcher, l)

    def forcePositionUpdate(self, room, watcher, doSeek):
        room = watcher.getRoom()
        paused, position = room.isPaused(), watcher.getPosition()
        setBy = watcher
        room.setPosition(watcher.getPosition(), setBy)
        l = lambda w: w.sendState(position, paused, doSeek, setBy, True)
        self._roomManager.broadcastRoom(watcher, l)

    def getAllWatchersForUser(self, forUser):
        return self._roomManager.getAllWatchersForUser(forUser)

class RoomManager(object):
    def __init__(self):
        self._rooms = {}

    def broadcastRoom(self, sender, whatLambda):
        room = sender.getRoom()
        if room and room.getName() in self._rooms:
            for receiver in room.getWatchers():
                whatLambda(receiver)

    def broadcast(self, sender, whatLambda):
        for room in self._rooms.itervalues():
            for receiver in room.getWatchers():
                whatLambda(receiver)

    def getAllWatchersForUser(self, sender):
        watchers = []
        for room in self._rooms.itervalues():
            for watcher in room.getWatchers():
                watchers.append(watcher)
        return watchers

    def moveWatcher(self, watcher, roomName):
        self.removeWatcher(watcher)
        room = self._getRoom(roomName)
        room.addWatcher(watcher)

    def removeWatcher(self, watcher):
        oldRoom = watcher.getRoom()
        if(oldRoom):
            oldRoom.removeWatcher(watcher)
            self._deleteRoomIfEmpty(oldRoom)

    def _getRoom(self, roomName):
        if roomName in self._rooms:
            return self._rooms[roomName]
        else:
            room = Room(roomName)
            self._rooms[roomName] = room
            return room

    def _deleteRoomIfEmpty(self, room):
        if room.isEmpty() and room.getName() in self._rooms:
            del self._rooms[room.getName()]

    def findFreeUsername(self, username):
        allnames = []
        for room in self._rooms.itervalues():
            for watcher in room.getWatchers():
                allnames.append(watcher.getName().lower())
        while username.lower() in allnames:
            username += '_'
        return username


class PublicRoomManager(RoomManager):
    def broadcast(self, sender, what):
        self.broadcastRoom(sender, what)

    def getAllWatchersForUser(self, sender):
        room = sender.getRoom().getWatchers()

    def moveWatcher(self, watcher, room):
        oldRoom = watcher.room
        l = lambda w: w.sendSetting(watcher.getName(), oldRoom, None, {"left": True})
        self.broadcast(watcher, l)
        RoomManager.watcherSetRoom(self, watcher, room)
        watcher.setFile(watcher.getFile())


class Room(object):
    STATE_PAUSED = 0
    STATE_PLAYING = 1

    def __init__(self, name):
        self._name = name
        self._watchers = {}
        self._playState = self.STATE_PAUSED
        self._setBy = None

    def __str__(self, *args, **kwargs):
        return self.getName()

    def getName(self):
        return self._name

    def getPosition(self):
        if self._watchers:
            watcher = min(self._watchers.values())
            self._setBy = watcher
            return watcher.getPosition()
        else:
            return 0

    def setPaused(self, paused=STATE_PAUSED, setBy=None):
        self._playState = paused
        self._setBy = setBy

    def setPosition(self, position, setBy=None):
        for watcher in self._watchers.itervalues():
            watcher.setPosition(position)
            self._setBy = setBy

    def isPlaying(self):
        return self._playState == self.STATE_PLAYING

    def isPaused(self):
        return self._playState == self.STATE_PAUSED

    def getWatchers(self):
        return self._watchers.values()

    def addWatcher(self, watcher):
        if self._watchers:
            watcher.setPosition(self.getPosition())
        self._watchers[watcher.getName()] = watcher
        watcher.setRoom(self)

    def removeWatcher(self, watcher):
        if(watcher.getName() not in self._watchers):
            return
        del self._watchers[watcher.getName()]
        watcher.setRoom(None)

    def isEmpty(self):
        return not bool(self._watchers)

    def getSetBy(self):
        return self._setBy

class Watcher(object):
    def __init__(self, server, connector, name):
        self._server = server
        self._connector = connector
        self._name = name
        self._room = None
        self._file = None
        self._position = None
        self._lastUpdatedOn = time.time()
        self._sendStateTimer = None
        self._connector.setWatcher(self)
        reactor.callLater(0.1, self._scheduleSendState)

    def setFile(self, file):
        self._file = file
        self._server.sendFileUpdate(self, file)

    def setRoom(self, room):
        self._room = room
        if room is None:
            self._deactivateStateTimer()
        else:
            self._resetStateTimer()
            self._askForStateUpdate(True, True)

    def getRoom(self):
        return self._room

    def getName(self):
        return self._name

    def getFile(self):
        return self._file

    def setPosition(self, position):
        self._position = position

    def getPosition(self):
        if self._position is None:
            return None
        if self._room.isPlaying():
            timePassedSinceSet = time.time() - self._lastUpdatedOn
        else:
            timePassedSinceSet = 0
        return self._position + timePassedSinceSet

    def sendSetting(self, user, room, file_, event):
        self._connector.sendUserSetting(user, room, file_, event)

    def __lt__(self, b):
        if self.getPosition() is None or self._file is None:
            return False
        if b.getPosition is None or b._file is None:
            return True
        return self.getPosition() < b.getPosition()

    def _scheduleSendState(self):
        self._sendStateTimer = task.LoopingCall(self._askForStateUpdate)
        self._sendStateTimer.start(constants.SERVER_STATE_INTERVAL, True)

    def _askForStateUpdate(self, doSeek=False, forcedUpdate=False):
        self._server.sendState(self, doSeek, forcedUpdate)

    def _resetStateTimer(self):
        if self._sendStateTimer:
            if self._sendStateTimer.running:
                self._sendStateTimer.stop()
            self._sendStateTimer.start(constants.SERVER_STATE_INTERVAL)

    def _deactivateStateTimer(self):
        if(self._sendStateTimer and self._sendStateTimer.running):
            self._sendStateTimer.stop()

    def sendState(self, position, paused, doSeek, setBy, forcedUpdate):
        if self._connector.isLogged():
            self._connector.sendState(position, paused, doSeek, setBy, forcedUpdate)
        if time.time() - self._lastUpdatedOn > constants.PROTOCOL_TIMEOUT:
            self._server.removeWatcher(self)
            self._connector.drop()

    def __hasPauseChanged(self, paused):
        if paused is None:
            return False
        return self._room.isPaused() and not paused or not self._room.isPaused() and paused

    def updateState(self, position, paused, doSeek, messageAge):
        pauseChanged = self.__hasPauseChanged(paused)
        self._lastUpdatedOn = time.time()
        if pauseChanged:
            self.getRoom().setPaused(Room.STATE_PAUSED if paused else Room.STATE_PLAYING, self)
        if position is not None:
            if(not paused):
                position += messageAge
            self.setPosition(position)
        if doSeek or pauseChanged:
            self._server.forcePositionUpdate(self._room, self, doSeek)


class ConfigurationGetter(object):
    def getConfiguration(self):
        self._prepareArgParser()
        self._args = self._argparser.parse_args()
        if(self._args.port == None):
            self._args.port = constants.DEFAULT_PORT
        return self._args

    def _prepareArgParser(self):
        self._argparser = argparse.ArgumentParser(description=getMessage("en", "server-argument-description"),
                                         epilog=getMessage("en", "server-argument-epilog"))
        self._argparser.add_argument('--port', metavar='port', type=str, nargs='?', help=getMessage("en", "server-port-argument"))
        self._argparser.add_argument('--password', metavar='password', type=str, nargs='?', help=getMessage("en", "server-password-argument"))
        self._argparser.add_argument('--isolate-rooms', action='store_true', help=getMessage("en", "server-isolate-room-argument"))
        self._argparser.add_argument('--motd-file', metavar='file', type=str, nargs='?', help=getMessage("en", "server-motd-argument"))

########NEW FILE########
__FILENAME__ = ConfigurationGetter
from ConfigParser import SafeConfigParser, DEFAULTSECT
import argparse
import os
import sys
from syncplay import constants, utils
from syncplay.messages import getMessage
from syncplay.players.playerFactory import PlayerFactory
import codecs
try:
    from syncplay.ui.GuiConfiguration import GuiConfiguration
    from PySide import QtGui  # @UnresolvedImport
    from PySide.QtCore import QCoreApplication
except ImportError:
    GuiConfiguration = None

class InvalidConfigValue(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

class ConfigurationGetter(object):
    def __init__(self):
        self._config = {
                        "host": None,
                        "port": constants.DEFAULT_PORT,
                        "name": None,
                        "debug": False,
                        "forceGuiPrompt": True,
                        "noGui": False,
                        "noStore": False,
                        "room": "",
                        "password": None,
                        "playerPath": None,
                        "file": None,
                        "playerArgs": [],
                        "playerClass": None,
                        "slowOnDesync": True,
                        "dontSlowDownWithMe": False,
                        "rewindOnDesync": True,
                        "filenamePrivacyMode": constants.PRIVACY_SENDRAW_MODE,
                        "filesizePrivacyMode": constants.PRIVACY_SENDRAW_MODE,
                        "pauseOnLeave": False,
                        "clearGUIData": False
                        }

        #
        # Custom validation in self._validateArguments
        #
        self._required = [
                          "host",
                          "port",
                          "room",
                          "playerPath",
                          "playerClass",
                         ]

        self._boolean = [
                         "debug",
                         "forceGuiPrompt",
                         "noGui",
                         "noStore",
                         "slowOnDesync",
                         "dontSlowDownWithMe",
                         "pauseOnLeave",
                         "rewindOnDesync",
                         "clearGUIData"
                        ]

        self._iniStructure = {
                        "server_data": ["host", "port", "password"],
                        "client_settings": ["name", "room", "playerPath", "slowOnDesync", "dontSlowDownWithMe", "rewindOnDesync", "forceGuiPrompt", "filenamePrivacyMode", "filesizePrivacyMode", "pauseOnLeave"],
                        }

        #
        # Watch out for the method self._overrideConfigWithArgs when you're adding custom multi-word command line arguments
        #
        self._argparser = argparse.ArgumentParser(description=getMessage("en", "argument-description"),
                                         epilog=getMessage("en", "argument-epilog"))
        self._argparser.add_argument('--no-gui', action='store_true', help=getMessage("en", "nogui-argument"))
        self._argparser.add_argument('-a', '--host', metavar='hostname', type=str, help=getMessage("en", "host-argument"))
        self._argparser.add_argument('-n', '--name', metavar='username', type=str, help=getMessage("en", "name-argument"))
        self._argparser.add_argument('-d', '--debug', action='store_true', help=getMessage("en", "debug-argument"))
        self._argparser.add_argument('-g', '--force-gui-prompt', action='store_true', help=getMessage("en", "force-gui-prompt-argument"))
        self._argparser.add_argument('--no-store', action='store_true', help=getMessage("en", "no-store-argument"))
        self._argparser.add_argument('-r', '--room', metavar='room', type=str, nargs='?', help=getMessage("en", "room-argument"))
        self._argparser.add_argument('-p', '--password', metavar='password', type=str, nargs='?', help=getMessage("en", "password-argument"))
        self._argparser.add_argument('--player-path', metavar='path', type=str, help=getMessage("en", "player-path-argument"))
        self._argparser.add_argument('file', metavar='file', type=str, nargs='?', help=getMessage("en", "file-argument"))
        self._argparser.add_argument('--clear-gui-data', action='store_true', help=getMessage("en", "clear-gui-data-argument"))
        self._argparser.add_argument('_args', metavar='options', type=str, nargs='*', help=getMessage("en", "args-argument"))

        self._playerFactory = PlayerFactory()

    def _validateArguments(self):
        def _isPortValid(varToTest):
            try:
                if (varToTest == "" or varToTest is None):
                    return False
                if (str(varToTest).isdigit() == False):
                    return False
                varToTest = int(varToTest)
                if (varToTest > 65535 or varToTest < 1):
                    return False
                return True
            except:
                return False
        for key in self._boolean:
            if(self._config[key] == "True"):
                self._config[key] = True
            elif(self._config[key] == "False"):
                self._config[key] = False
        for key in self._required:
            if(key == "playerPath"):
                player = self._playerFactory.getPlayerByPath(self._config["playerPath"])
                if(player):
                    self._config["playerClass"] = player
                else:
                    raise InvalidConfigValue("Player path is not set properly")
                if player.__name__ in ['MpvPlayer', 'MplayerPlayer']:
                    if not self._config['file']:
                        raise InvalidConfigValue("File must be selected before starting your player")
            elif(key == "host"):
                self._config["host"], self._config["port"] = self._splitPortAndHost(self._config["host"])
                hostNotValid = (self._config["host"] == "" or self._config["host"] is None)
                portNotValid = (_isPortValid(self._config["port"]) == False)
                if(hostNotValid):
                    raise InvalidConfigValue("Hostname can't be empty")
                elif(portNotValid):
                    raise InvalidConfigValue("Port must be valid")
            elif(self._config[key] == "" or self._config[key] is None):
                raise InvalidConfigValue("{} can't be empty".format(key.capitalize()))

    def _overrideConfigWithArgs(self, args):
        for key, val in vars(args).items():
            if(val):
                if(key == "force_gui_prompt"):
                    key = "forceGuiPrompt"
                if(key == "no_store"):
                    key = "noStore"
                if(key == "player_path"):
                    key = "playerPath"
                if(key == "_args"):
                    key = "playerArgs"
                if(key == "no_gui"):
                    key = "noGui"
                if(key == "clear_gui_data"):
                    key = "clearGUIData"
                self._config[key] = val

    def _splitPortAndHost(self, host):
        port = constants.DEFAULT_PORT if not self._config["port"] else self._config["port"]
        if(host):
            if ':' in host:
                host, port = host.split(':', 1)
                try:
                    port = int(port)
                except ValueError:
                    try:
                        port = port.encode('ascii', 'ignore')
                    except:
                        port = ""
        return host, port

    def _checkForPortableFile(self):
        path = utils.findWorkingDir()
        for name in constants.CONFIG_NAMES:
            if(os.path.isfile(os.path.join(path, name))):
                return os.path.join(path, name)

    def _getConfigurationFilePath(self):
        configFile = self._checkForPortableFile()
        if not configFile:
            for name in constants.CONFIG_NAMES:
                if(configFile and os.path.isfile(configFile)):
                    break
                if(os.name <> 'nt'):
                    configFile = os.path.join(os.getenv('HOME', '.'), name)
                else:
                    configFile = os.path.join(os.getenv('APPDATA', '.'), name)
            if(configFile and not os.path.isfile(configFile)):
                if(os.name <> 'nt'):
                    configFile = os.path.join(os.getenv('HOME', '.'), constants.DEFAULT_CONFIG_NAME_LINUX)
                else:
                    configFile = os.path.join(os.getenv('APPDATA', '.'), constants.DEFAULT_CONFIG_NAME_WINDOWS)

        return configFile

    def _parseConfigFile(self, iniPath, createConfig=True):
        parser = SafeConfigParserUnicode()
        if(not os.path.isfile(iniPath)):
            if(createConfig):
                open(iniPath, 'w').close()
            else:
                return
        parser.readfp(codecs.open(iniPath, "r", "utf_8_sig"))
        for section, options in self._iniStructure.items():
            if(parser.has_section(section)):
                for option in options:
                    if(parser.has_option(section, option)):
                        self._config[option] = parser.get(section, option)

    def _checkConfig(self):
        try:
            self._validateArguments()
        except InvalidConfigValue as e:
            try:
                for key, value in self._promptForMissingArguments(e.message).items():
                    self._config[key] = value
                self._checkConfig()
            except:
                sys.exit()

    def _promptForMissingArguments(self, error=None):
        if(self._config['noGui']):
            print getMessage("en", "missing-arguments-error")
            sys.exit()
        elif(GuiConfiguration):
            gc = GuiConfiguration(self._config, error=error)
            gc.setAvailablePaths(self._playerFactory.getAvailablePlayerPaths())
            gc.run()
            return gc.getProcessedConfiguration()

    def __wasOptionChanged(self, parser, section, option):
        if (parser.has_option(section, option)):
            if (parser.get(section, option) != unicode(self._config[option])):
                return True
        else:
            return True

    def _saveConfig(self, iniPath):
        changed = False
        if(self._config['noStore']):
            return
        parser = SafeConfigParserUnicode()
        parser.readfp(codecs.open(iniPath, "r", "utf_8_sig"))
        for section, options in self._iniStructure.items():
            if(not parser.has_section(section)):
                parser.add_section(section)
                changed = True
            for option in options:
                if(self.__wasOptionChanged(parser, section, option)):
                    changed = True
                parser.set(section, option, unicode(self._config[option]).replace('%', '%%'))
        if(changed):
            parser.write(codecs.open(iniPath, "wb", "utf_8_sig"))


    def _forceGuiPrompt(self):
        try:
            self._validateArguments()
        except InvalidConfigValue:
            pass
        try:
            if(self._config['noGui'] == False):
                for key, value in self._promptForMissingArguments().items():
                    self._config[key] = value
        except GuiConfiguration.WindowClosed:
            sys.exit()


    def __getRelativeConfigLocations(self):
        locations = []
        path = os.path.dirname(os.path.realpath(self._config['file']))
        locations.append(path)
        while path != os.path.dirname(path):
            path = os.path.dirname(path)
            locations.append(path)
        locations.reverse()
        return locations

    def _loadRelativeConfiguration(self):
        locations = self.__getRelativeConfigLocations()
        loadedPaths = []
        for location in locations:
            for name in constants.CONFIG_NAMES:
                path = location + os.path.sep + name
                if(os.path.isfile(path) and (os.name == 'nt' or path != os.path.join(os.getenv('HOME', '.'), constants.DEFAULT_CONFIG_NAME_LINUX))):
                    loadedPaths.append("'" + os.path.normpath(path) + "'")
                    self._parseConfigFile(path, createConfig=False)
                    self._checkConfig()
        return loadedPaths

    def getConfiguration(self):
        iniPath = self._getConfigurationFilePath()
        self._parseConfigFile(iniPath)
        args = self._argparser.parse_args()
        self._overrideConfigWithArgs(args)
        if(self._config['file'] and self._config['file'][:2] == "--"):
            self._config['playerArgs'].insert(0, self._config['file'])
            self._config['file'] = None
        # Arguments not validated yet - booleans are still text values
        if(self._config['forceGuiPrompt'] == "True" or not self._config['file']):
            self._forceGuiPrompt()
        self._checkConfig()
        self._saveConfig(iniPath)
        if(self._config['file']):
            self._config['loadedRelativePaths'] = self._loadRelativeConfiguration()
        if(not self._config['noGui']):
            from syncplay.vendor import qt4reactor
            if QCoreApplication.instance() is None:
                self.app = QtGui.QApplication(sys.argv)
            qt4reactor.install()
        return self._config

class SafeConfigParserUnicode(SafeConfigParser):
    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    key = " = ".join((key, unicode(value).replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
            fp.write("\n")

########NEW FILE########
__FILENAME__ = consoleUI
from __future__ import print_function
import threading
import time 
import syncplay
import re
from syncplay import utils
from syncplay import constants
from syncplay.messages import getMessage
import sys
from syncplay.utils import formatTime

class ConsoleUI(threading.Thread):
    def __init__(self):
        self.promptMode = threading.Event()
        self.PromptResult = ""
        self.promptMode.set()
        self._syncplayClient = None
        threading.Thread.__init__(self, name="ConsoleUI")
        
    def addClient(self, client):
        self._syncplayClient = client
        
    def drop(self):
        pass
    
    def run(self):
        try:
            while True:
                data = raw_input().decode(sys.stdin.encoding)
                data = data.rstrip('\n\r')
                if(not self.promptMode.isSet()):
                    self.PromptResult = data
                    self.promptMode.set()
                elif(self._syncplayClient):
                    self._executeCommand(data)
        except EOFError:
            pass
        
    def promptFor(self, prompt=">", message=""):
        if message <> "":
            print(message)
        self.promptMode.clear()
        print(prompt, end='')
        self.promptMode.wait()
        return self.PromptResult

    def showUserList(self, currentUser, rooms):
        for room in rooms:
            message = u"In room '{}':".format(room)
            self.showMessage(message, True)
            for user in rooms[room]:
                username = "*<{}>*".format(user.username) if user == currentUser else "<{}>".format(user.username)
                if(user.file):
                    message = u"{} is playing:".format(username)
                    self.showMessage(message, True)
                    message = u"    File: '{}' ({})".format(user.file['name'], formatTime(user.file['duration']))
                    if(currentUser.file):
                        if(user.file['name'] == currentUser.file['name'] and user.file['size'] != currentUser.file['size']):
                            message += " (their file size is different from yours!)"
                    self.showMessage(message, True)
                else:
                    message = u"{} is not playing a file".format(username)
                    self.showMessage(message, True)

    def userListChange(self):
        pass

    def showMessage(self, message, noTimestamp=False):
        message = message.encode(sys.stdout.encoding, 'replace')
        if(noTimestamp):
            print(message)
        else:
            print(time.strftime(constants.UI_TIME_FORMAT, time.localtime()) + message)

    def showDebugMessage(self, message):
        print(message)
        
    def showErrorMessage(self, message, criticalerror = False):
        print("ERROR:\t" + message)            

    def _extractSign(self, m):
        if(m):
            if(m == "-"):
                return -1
            else:
                return 1
        else:
            return None
        
    def _tryAdvancedCommands(self, data):
        o = re.match(constants.UI_OFFSET_REGEX, data)
        s = re.match(constants.UI_SEEK_REGEX, data)
        if(o):
            sign = self._extractSign(o.group('sign'))
            t = utils.parseTime(o.group('time'))
            if(t is None):
                return
            if (o.group('sign') == "/"):
                    t =  self._syncplayClient.getPlayerPosition() - t
            elif(sign):
                    t = self._syncplayClient.getUserOffset() + sign * t
            self._syncplayClient.setUserOffset(t)
            return True
        elif s:
            sign = self._extractSign(s.group('sign'))
            t = utils.parseTime(s.group('time'))
            if(t is None):
                return
            if(sign):
                t = self._syncplayClient.getGlobalPosition() + sign * t 
            self._syncplayClient.setPosition(t)
            return True
        return False 
     
    def _executeCommand(self, data):
        command = re.match(constants.UI_COMMAND_REGEX, data)
        if(not command):
            return
        if(command.group('command') in constants.COMMANDS_UNDO):
            tmp_pos = self._syncplayClient.getPlayerPosition()
            self._syncplayClient.setPosition(self._syncplayClient.playerPositionBeforeLastSeek)
            self._syncplayClient.playerPositionBeforeLastSeek = tmp_pos
        elif (command.group('command') in constants.COMMANDS_LIST):
            self._syncplayClient.getUserList()
        elif (command.group('command') in constants.COMMANDS_PAUSE):
            self._syncplayClient.setPaused(not self._syncplayClient.getPlayerPaused())
        elif (command.group('command') in constants.COMMANDS_ROOM):
            room = command.group('parameter')
            if room == None:
                if  self._syncplayClient.userlist.currentUser.file:
                    room = self._syncplayClient.userlist.currentUser.file["name"]
                else:
                    room = self._syncplayClient.defaultRoom

            self._syncplayClient.setRoom(room)
            self._syncplayClient.sendRoom()
        else:
            if(self._tryAdvancedCommands(data)):
                return
            if (command.group('command') not in constants.COMMANDS_HELP):
                self.showMessage(getMessage("en", "unrecognized-command-notification"))
            self.showMessage(getMessage("en", "commandlist-notification"), True)
            self.showMessage(getMessage("en", "commandlist-notification/room"), True)
            self.showMessage(getMessage("en", "commandlist-notification/list"), True)
            self.showMessage(getMessage("en", "commandlist-notification/undo"), True)
            self.showMessage(getMessage("en", "commandlist-notification/pause"), True)
            self.showMessage(getMessage("en", "commandlist-notification/seek"), True)
            self.showMessage(getMessage("en", "commandlist-notification/help"), True)
            self.showMessage(getMessage("en", "syncplay-version-notification").format(syncplay.version), True)
            self.showMessage(getMessage("en", "more-info-notification").format(syncplay.projectURL), True)
    

########NEW FILE########
__FILENAME__ = gui
from PySide import QtGui #@UnresolvedImport
from PySide.QtCore import Qt, QSettings, QSize, QPoint #@UnresolvedImport
from syncplay import utils, constants, version
from syncplay.messages import getMessage
import sys
import time
import re
import os 
from syncplay.utils import formatTime, sameFilename, sameFilesize, sameFileduration

class MainWindow(QtGui.QMainWindow):
    def addClient(self, client):
        self._syncplayClient = client
        self.roomInput.setText(self._syncplayClient.getRoom())
    
    def promptFor(self, prompt=">", message=""):
        #TODO: Prompt user
        return None

    def showMessage(self, message, noTimestamp=False):
        message = unicode(message)
        message = message.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        message = message.replace("&lt;", "<span style=\"color:#367AA9;font-weight:bold;\">&lt;")
        message = message.replace("&gt;", "&gt;</span>")
        message = message.replace("\n", "<br />")
        if(noTimestamp):
            self.newMessage(message + "<br />")
        else:
            self.newMessage(time.strftime(constants.UI_TIME_FORMAT, time.localtime()) + message + "<br />")
    
    def showUserList(self, currentUser, rooms):
        self._usertreebuffer = QtGui.QStandardItemModel()
        self._usertreebuffer.setColumnCount(2)
        self._usertreebuffer.setHorizontalHeaderLabels((getMessage("en", "roomuser-heading-label"),getMessage("en", "fileplayed-heading-label")))
        usertreeRoot = self._usertreebuffer.invisibleRootItem()
        
        for room in rooms:
            roomitem = QtGui.QStandardItem(room)
            if (room == currentUser.room):
                font = QtGui.QFont()
                font.setWeight(QtGui.QFont.Bold)
                roomitem.setFont(font)
            blankitem = QtGui.QStandardItem("")
            roomitem.setFlags(roomitem.flags()  & ~Qt.ItemIsEditable) 
            blankitem.setFlags(blankitem.flags() & ~Qt.ItemIsEditable)
            usertreeRoot.appendRow((roomitem, blankitem))
            for user in rooms[room]:
                useritem = QtGui.QStandardItem(user.username)
                fileitem = QtGui.QStandardItem("")
                if (user.file):
                    fileitem = QtGui.QStandardItem(user.file['name'] + " ("+formatTime(user.file['duration'])+")")
                    if (currentUser.file):                     
                        sameName = sameFilename(user.file['name'], currentUser.file['name'])
                        sameSize = sameFilesize(user.file['size'], currentUser.file['size'])
                        sameDuration = sameFileduration(user.file['duration'], currentUser.file['duration'])
                        sameRoom = room == currentUser.room
                        differentName = not sameName
                        differentSize = not sameSize
                        differentDuration = not sameDuration
                        if (sameName or sameRoom):
                            if (differentSize and sameDuration):
                                fileitem = QtGui.QStandardItem("{} ({}) ({})".format(user.file['name'], formatTime(user.file['duration']), getMessage("en", "differentsize-note")))
                            elif (differentSize and differentDuration):
                                fileitem = QtGui.QStandardItem("{} ({}) ({})".format(user.file['name'], formatTime(user.file['duration']), getMessage("en", "differentsizeandduration-note")))
                            elif (differentDuration):
                                fileitem = QtGui.QStandardItem("{} ({}) ({})".format(user.file['name'], formatTime(user.file['duration']), getMessage("en", "differentduration-note")))
                            if (sameRoom and (differentName or differentSize or differentDuration)):
                                fileitem.setForeground(QtGui.QBrush(QtGui.QColor('red')))
                else:
                    fileitem = QtGui.QStandardItem(getMessage("en", "nofile-note"))
                    if (room == currentUser.room):
                        fileitem.setForeground(QtGui.QBrush(QtGui.QColor('blue')))
                if(currentUser.username == user.username):
                    font = QtGui.QFont()
                    font.setWeight(QtGui.QFont.Bold)
                    useritem.setFont(font)
                useritem.setFlags(useritem.flags()  & ~Qt.ItemIsEditable)
                fileitem.setFlags(fileitem.flags()  & ~Qt.ItemIsEditable)
                roomitem.appendRow((useritem, fileitem))
       
        self.listTreeModel = self._usertreebuffer
        self.listTreeView.setModel(self.listTreeModel)
        self.listTreeView.setItemsExpandable(False)
        self.listTreeView.expandAll()
        self.listTreeView.resizeColumnToContents(0)
        self.listTreeView.resizeColumnToContents(1)
        
    def roomClicked(self, item):
        while(item.parent().row() != -1):
            item = item.parent()
        self.joinRoom(item.sibling(item.row(), 0).data())
    
    def userListChange(self):
        self._syncplayClient.showUserList()
    
    def showDebugMessage(self, message):
        print(message)
        
    def showErrorMessage(self, message, criticalerror = False):
        message = unicode(message)
        if criticalerror:
            QtGui.QMessageBox.critical(self,"Syncplay", message)
        message = message.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        message = message.replace("\n", "<br />")
        message = "<span style=\"color:#FF0000;\">" + message + "</span>"
        self.newMessage(time.strftime(constants.UI_TIME_FORMAT, time.localtime()) + message + "<br />")

    def joinRoom(self, room = None):
        if room == None:
            room = self.roomInput.text()
        if room == "":
            if  self._syncplayClient.userlist.currentUser.file:
                room = self._syncplayClient.userlist.currentUser.file["name"]
            else:
                room = self._syncplayClient.defaultRoom
        self.roomInput.setText(room)
        if(room != self._syncplayClient.getRoom()):
            self._syncplayClient.setRoom(room)
            self._syncplayClient.sendRoom()

    def seekPosition(self):
        s = re.match(constants.UI_SEEK_REGEX, self.seekInput.text())
        if(s):
            sign = self._extractSign(s.group('sign'))
            t = utils.parseTime(s.group('time'))
            if(t is None):
                return
            if(sign):
                t = self._syncplayClient.getGlobalPosition() + sign * t 
            self._syncplayClient.setPosition(t)

        else:
            self.showErrorMessage("Invalid seek value")
        
    def undoSeek(self):
        tmp_pos = self._syncplayClient.getPlayerPosition()
        self._syncplayClient.setPosition(self._syncplayClient.playerPositionBeforeLastSeek)
        self._syncplayClient.playerPositionBeforeLastSeek = tmp_pos
        
    def togglePause(self):
        self._syncplayClient.setPaused(not self._syncplayClient.getPlayerPaused())
        
    def play(self):
        self._syncplayClient.setPaused(False)
        
    def pause(self):
        self._syncplayClient.setPaused(True)
        
    def exitSyncplay(self):
        self._syncplayClient.stop()
            
    def closeEvent(self, event):
        self.exitSyncplay()
        self.saveSettings()
        
    def loadMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        self.mediadirectory = settings.value("mediadir", "")
        settings.endGroup()
                        
    def saveMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        settings.setValue("mediadir", self.mediadirectory)
        settings.endGroup()
        
    def browseMediapath(self):
        self.loadMediaBrowseSettings()
        options = QtGui.QFileDialog.Options()
        if (os.path.isdir(self.mediadirectory)):
            defaultdirectory = self.mediadirectory
        elif (os.path.isdir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.MoviesLocation))):
            defaultdirectory = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.MoviesLocation)
        elif (os.path.isdir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation))):
            defaultdirectory = QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.HomeLocation)
        else:
            defaultdirectory = ""
        browserfilter = "All files (*)"       
        fileName, filtr = QtGui.QFileDialog.getOpenFileName(self,getMessage("en", "browseformedia-label"),defaultdirectory,
                browserfilter, "", options)
        if fileName:
            if sys.platform.startswith('win'):
                fileName = fileName.replace("/","\\")
            self.mediadirectory = os.path.dirname(fileName)
            self.saveMediaBrowseSettings()
            self._syncplayClient._player.openFile(fileName)
            
    def _extractSign(self, m):
        if(m):
            if(m == "-"):
                return -1
            else:
                return 1
        else:
            return None
        
    def setOffset(self):
        newoffset, ok = QtGui.QInputDialog.getText(self,getMessage("en","setoffset-msgbox-label"),
                getMessage("en","offsetinfo-msgbox-label"), QtGui.QLineEdit.Normal,
                "")
        if ok and newoffset != '':
            o = re.match(constants.UI_OFFSET_REGEX, "o " + newoffset)
            if(o):
                sign = self._extractSign(o.group('sign'))
                t = utils.parseTime(o.group('time'))
                if(t is None):
                    return
                if (o.group('sign') == "/"):
                        t =  self._syncplayClient.getPlayerPosition() - t
                elif(sign):
                        t = self._syncplayClient.getUserOffset() + sign * t
                self._syncplayClient.setUserOffset(t)
            else:
                self.showErrorMessage("Invalid offset value")
        
    def openUserGuide(self):
        if sys.platform.startswith('linux'):
            self.QtGui.QDesktopServices.openUrl("http://syncplay.pl/guide/linux/")
        elif sys.platform.startswith('win'):
            self.QtGui.QDesktopServices.openUrl("http://syncplay.pl/guide/windows/")
        else:
            self.QtGui.QDesktopServices.openUrl("http://syncplay.pl/guide/")

    def drop(self):
        self.close()
        
    def addTopLayout(self, window):       
        window.topSplit = QtGui.QSplitter(Qt.Horizontal)

        window.outputLayout = QtGui.QVBoxLayout()
        window.outputbox = QtGui.QTextEdit()
        window.outputbox.setReadOnly(True)  
        window.outputlabel = QtGui.QLabel(getMessage("en", "notifications-heading-label"))
        window.outputFrame = QtGui.QFrame()
        window.outputFrame.setLineWidth(0)
        window.outputFrame.setMidLineWidth(0)
        window.outputLayout.setContentsMargins(0,0,0,0)
        window.outputLayout.addWidget(window.outputlabel)
        window.outputLayout.addWidget(window.outputbox)
        window.outputFrame.setLayout(window.outputLayout)
        
        window.listLayout = QtGui.QVBoxLayout()
        window.listTreeModel = QtGui.QStandardItemModel()
        window.listTreeView = QtGui.QTreeView()
        window.listTreeView.setModel(window.listTreeModel)
        window.listTreeView.doubleClicked.connect(self.roomClicked)
        window.listlabel = QtGui.QLabel(getMessage("en", "userlist-heading-label"))
        window.listFrame = QtGui.QFrame()
        window.listFrame.setLineWidth(0)
        window.listFrame.setMidLineWidth(0)
        window.listLayout.setContentsMargins(0,0,0,0)
        window.listLayout.addWidget(window.listlabel)
        window.listLayout.addWidget(window.listTreeView)
        if constants.SHOW_CONTACT_INFO:
            window.contactLabel = QtGui.QLabel()
            window.contactLabel.setWordWrap(True)
            window.contactLabel.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Sunken)
            window.contactLabel.setLineWidth(1)
            window.contactLabel.setMidLineWidth(0)
            window.contactLabel.setMargin(2)
            window.contactLabel.setText(getMessage("en","contact-label"))
            window.contactLabel.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
            window.contactLabel.setOpenExternalLinks(True)
            window.listLayout.addWidget(window.contactLabel)
        window.listFrame.setLayout(window.listLayout)
        
        window.topSplit.addWidget(window.outputFrame)
        window.topSplit.addWidget(window.listFrame)
        window.topSplit.setStretchFactor(0,4)
        window.topSplit.setStretchFactor(1,5)
        window.mainLayout.addWidget(window.topSplit)
        window.topSplit.setSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Expanding)

    def addBottomLayout(self, window):
        window.bottomLayout = QtGui.QHBoxLayout()

        window.addRoomBox(MainWindow)
        window.addSeekBox(MainWindow)
        window.addMiscBox(MainWindow)

        window.bottomLayout.addWidget(window.roomGroup, Qt.AlignLeft)
        window.bottomLayout.addWidget(window.seekGroup, Qt.AlignLeft)
        window.bottomLayout.addWidget(window.miscGroup, Qt.AlignLeft)

        window.mainLayout.addLayout(window.bottomLayout, Qt.AlignLeft)

    def addRoomBox(self, window):
        window.roomGroup = QtGui.QGroupBox(getMessage("en", "room-heading-label"))
        
        window.roomInput = QtGui.QLineEdit()
        window.roomInput.returnPressed.connect(self.joinRoom)
        window.roomButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'door_in.png'), getMessage("en", "joinroom-guibuttonlabel"))
        window.roomButton.pressed.connect(self.joinRoom)
        window.roomLayout = QtGui.QHBoxLayout()
        window.roomInput.setMaximumWidth(150)

        self.roomButton.setToolTip(getMessage("en", "joinroom-tooltip"))
        
        window.roomLayout.addWidget(window.roomInput)
        window.roomLayout.addWidget(window.roomButton)
        
        window.roomGroup.setLayout(window.roomLayout)
        window.roomGroup.setFixedSize(window.roomGroup.sizeHint())
        
    def addSeekBox(self, window):
        window.seekGroup = QtGui.QGroupBox(getMessage("en", "seek-heading-label"))
        
        window.seekInput = QtGui.QLineEdit()
        window.seekInput.returnPressed.connect(self.seekPosition)
        window.seekButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'clock_go.png'),getMessage("en", "seektime-guibuttonlabel"))
        window.seekButton.pressed.connect(self.seekPosition)

        self.seekButton.setToolTip(getMessage("en", "seektime-tooltip"))
        
        window.seekLayout = QtGui.QHBoxLayout()
        window.seekInput.setMaximumWidth(50)
        window.seekInput.setText("0:00")
        
        window.seekLayout.addWidget(window.seekInput)
        window.seekLayout.addWidget(window.seekButton)
        
        window.seekGroup.setLayout(window.seekLayout)
        window.seekGroup.setFixedSize(window.seekGroup.sizeHint())
        
    def addMiscBox(self, window):
        window.miscGroup = QtGui.QGroupBox(getMessage("en", "othercommands-heading-label"))
        
        window.unseekButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'arrow_undo.png'),getMessage("en", "undoseek-guibuttonlabel"))
        window.unseekButton.pressed.connect(self.undoSeek)
        self.unseekButton.setToolTip(getMessage("en", "undoseek-tooltip"))

        window.miscLayout = QtGui.QHBoxLayout()
        window.miscLayout.addWidget(window.unseekButton)
        if constants.MERGE_PLAYPAUSE_BUTTONS == True:
            window.playpauseButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'control_pause_blue.png'),getMessage("en", "togglepause-guibuttonlabel"))
            window.playpauseButton.pressed.connect(self.togglePause)
            window.miscLayout.addWidget(window.playpauseButton)
            self.playpauseButton.setToolTip(getMessage("en", "togglepause-tooltip"))
        else:
            window.playButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'control_play_blue.png'),getMessage("en", "play-guibuttonlabel"))
            window.playButton.pressed.connect(self.play)
            window.playButton.setMaximumWidth(60)
            window.miscLayout.addWidget(window.playButton)
            window.pauseButton = QtGui.QPushButton(QtGui.QIcon(self.resourcespath + 'control_pause_blue.png'),getMessage("en", "pause-guibuttonlabel"))
            window.pauseButton.pressed.connect(self.pause)
            window.pauseButton.setMaximumWidth(60)
            window.miscLayout.addWidget(window.pauseButton)
            self.playButton.setToolTip(getMessage("en", "play-tooltip"))
            self.pauseButton.setToolTip(getMessage("en", "pause-tooltip"))
        
        window.miscGroup.setLayout(window.miscLayout)
        window.miscGroup.setFixedSize(window.miscGroup.sizeHint())
        

    def addMenubar(self, window):
        window.menuBar = QtGui.QMenuBar()

        window.fileMenu = QtGui.QMenu(getMessage("en", "file-menu-label"), self)
        window.openAction = window.fileMenu.addAction(QtGui.QIcon(self.resourcespath + 'folder_explore.png'), getMessage("en", "openmedia-menu-label"))
        window.openAction.triggered.connect(self.browseMediapath)
        window.exitAction = window.fileMenu.addAction(QtGui.QIcon(self.resourcespath + 'cross.png'), getMessage("en", "file-menu-label"))
        window.exitAction.triggered.connect(self.exitSyncplay)
        window.menuBar.addMenu(window.fileMenu)
        
        window.advancedMenu = QtGui.QMenu(getMessage("en", "advanced-menu-label"), self)
        window.setoffsetAction = window.advancedMenu.addAction(QtGui.QIcon(self.resourcespath + 'timeline_marker.png'),getMessage("en", "setoffset-menu-label"))
        window.setoffsetAction.triggered.connect(self.setOffset)
        window.menuBar.addMenu(window.advancedMenu)
        
        window.helpMenu = QtGui.QMenu(getMessage("en", "help-menu-label"), self)
        window.userguideAction = window.helpMenu.addAction(QtGui.QIcon(self.resourcespath + 'help.png'), getMessage("en", "userguide-menu-label"))
        window.userguideAction.triggered.connect(self.openUserGuide)
        
        window.menuBar.addMenu(window.helpMenu)
        window.mainLayout.setMenuBar(window.menuBar)
    
    def addMainFrame(self, window):
        window.mainFrame = QtGui.QFrame()
        window.mainFrame.setLineWidth(0)
        window.mainFrame.setMidLineWidth(0)
        window.mainFrame.setContentsMargins(0,0,0,0)
        window.mainFrame.setLayout(window.mainLayout)
        
        window.setCentralWidget(window.mainFrame)
        
    def newMessage(self, message):
        self.outputbox.moveCursor(QtGui.QTextCursor.End)
        self.outputbox.insertHtml(message)
        self.outputbox.moveCursor(QtGui.QTextCursor.End)
        
    def resetList(self):
        self.listbox.setText("")
        
    def newListItem(self, item):
        self.listbox.moveCursor(QtGui.QTextCursor.End)
        self.listbox.insertHtml(item)
        self.listbox.moveCursor(QtGui.QTextCursor.End)
        
    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if (urls and urls[0].scheme() == 'file'):
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        rewindFile = False
        if QtGui.QDropEvent.proposedAction(event) == Qt.MoveAction:
            QtGui.QDropEvent.setDropAction(event, Qt.CopyAction) # Avoids file being deleted
            rewindFile = True
        data = event.mimeData()
        urls = data.urls()
        if (urls and urls[0].scheme() == 'file'):
            if sys.platform.startswith('linux'):
                dropfilepath = unicode(urls[0].path())
            else:
                dropfilepath = unicode(urls[0].path().replace("/", "\\"))[1:] # Removes starting slash
            if rewindFile == False:
                self._syncplayClient._player.openFile(dropfilepath)
            else:
                self._syncplayClient.setPosition(0)
                self._syncplayClient._player.openFile(dropfilepath)
                self._syncplayClient.setPosition(0)
    
    def saveSettings(self):
        settings = QSettings("Syncplay", "MainWindow")
        settings.beginGroup("MainWindow")
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        settings.endGroup()
    
    def loadSettings(self):
        settings = QSettings("Syncplay", "MainWindow")
        settings.beginGroup("MainWindow")
        self.resize(settings.value("size", QSize(700, 500)))
        self.move(settings.value("pos", QPoint(200, 200)))
        settings.endGroup()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.QtGui = QtGui
        if sys.platform.startswith('linux'):
            self.resourcespath = utils.findWorkingDir() + "/resources/"
        else:
            self.resourcespath = utils.findWorkingDir() + "\\resources\\"
        self.setWindowTitle("Syncplay v" + version)
        self.mainLayout = QtGui.QVBoxLayout()
        self.addTopLayout(self)
        self.addBottomLayout(self)
        self.addMenubar(self)
        self.addMainFrame(self)
        self.loadSettings()
        self.setWindowIcon(QtGui.QIcon(self.resourcespath + "syncplay.png"))
        self.setWindowFlags(self.windowFlags() & Qt.WindowCloseButtonHint & Qt.WindowMinimizeButtonHint & ~Qt.WindowContextHelpButtonHint)
        self.show()
        self.setAcceptDrops(True)
########NEW FILE########
__FILENAME__ = GuiConfiguration
from PySide import QtCore, QtGui
from PySide.QtCore import QSettings, Qt, QCoreApplication
from PySide.QtGui import QApplication, QLineEdit, QCursor, QLabel, QCheckBox, QDesktopServices, QIcon, QImage, QButtonGroup, QRadioButton
from syncplay.players.playerFactory import PlayerFactory

import os
import sys
from syncplay.messages import getMessage
from syncplay import constants

class GuiConfiguration:
    def __init__(self, config, error=None):
        self.config = config
        self._availablePlayerPaths = []
        self.error = error


    def run(self):
        if QCoreApplication.instance() is None:
            self.app = QtGui.QApplication(sys.argv)
        dialog = ConfigDialog(self.config, self._availablePlayerPaths, self.error)
        dialog.exec_()

    def setAvailablePaths(self, paths):
        self._availablePlayerPaths = paths

    def getProcessedConfiguration(self):
        return self.config

    class WindowClosed(Exception):
        pass

class ConfigDialog(QtGui.QDialog):

    pressedclosebutton = False
    moreToggling = False

    def moreToggled(self):
        if self.moreToggling == False:
            self.moreToggling = True

            if self.showmoreCheckbox.isChecked() and self.showmoreCheckbox.isVisible():
                self.showmoreCheckbox.setChecked(False)
                self.moreSettingsGroup.setChecked(True)
                self.moreSettingsGroup.show()
                self.showmoreCheckbox.hide()
                self.saveMoreState(True)
            else:
                self.moreSettingsGroup.setChecked(False)
                self.moreSettingsGroup.hide()
                self.showmoreCheckbox.show()
                self.saveMoreState(False)

            self.moreToggling = False
            self.adjustSize()
            self.setFixedSize(self.sizeHint())

    def runButtonTextUpdate(self):
        if (self.donotstoreCheckbox.isChecked()):
            self.runButton.setText(getMessage("en", "run-label"))
        else:
            self.runButton.setText(getMessage("en", "storeandrun-label"))

    def openHelp(self):
        self.QtGui.QDesktopServices.openUrl("http://syncplay.pl/guide/client/")

    def _tryToFillPlayerPath(self, playerpath, playerpathlist):
        settings = QSettings("Syncplay", "PlayerList")
        settings.beginGroup("PlayerList")
        savedPlayers = settings.value("PlayerList", [])
        if(not isinstance(savedPlayers, list)):
            savedPlayers = []
        playerpathlist = list(set(os.path.normcase(os.path.normpath(path)) for path in set(playerpathlist + savedPlayers)))
        settings.endGroup()
        foundpath = ""

        if playerpath != None and playerpath != "":
            if not os.path.isfile(playerpath):
                expandedpath = PlayerFactory().getExpandedPlayerPathByPath(playerpath)
                if expandedpath != None and os.path.isfile(expandedpath):
                    playerpath = expandedpath

            if os.path.isfile(playerpath):
                foundpath = playerpath
                self.executablepathCombobox.addItem(foundpath)

        for path in playerpathlist:
            if(os.path.isfile(path) and os.path.normcase(os.path.normpath(path)) != os.path.normcase(os.path.normpath(foundpath))):
                self.executablepathCombobox.addItem(path)
                if foundpath == "":
                    foundpath = path

        if foundpath != "":
            settings.beginGroup("PlayerList")
            playerpathlist.append(os.path.normcase(os.path.normpath(foundpath)))
            settings.setValue("PlayerList", list(set(os.path.normcase(os.path.normpath(path)) for path in set(playerpathlist))))
            settings.endGroup()
        return(foundpath)

    def updateExecutableIcon(self):
        currentplayerpath = unicode(self.executablepathCombobox.currentText())
        iconpath = PlayerFactory().getPlayerIconByPath(currentplayerpath)
        if iconpath != None and iconpath != "":
            self.executableiconImage.load(self.resourcespath + iconpath)
            self.executableiconLabel.setPixmap(QtGui.QPixmap.fromImage(self.executableiconImage))
        else:
            self.executableiconLabel.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage()))


    def browsePlayerpath(self):
        options = QtGui.QFileDialog.Options()
        defaultdirectory = ""
        browserfilter = "All files (*)"

        if os.name == 'nt':
            browserfilter = "Executable files (*.exe);;All files (*)"
            if "PROGRAMFILES(X86)" in os.environ:
                defaultdirectory = os.environ["ProgramFiles(x86)"]
            elif "PROGRAMFILES" in os.environ:
                defaultdirectory = os.environ["ProgramFiles"]
            elif "PROGRAMW6432" in os.environ:
                defaultdirectory = os.environ["ProgramW6432"]
        elif sys.platform.startswith('linux'):
            defaultdirectory = "/usr/bin"

        fileName, filtr = QtGui.QFileDialog.getOpenFileName(self,
                "Browse for media player executable",
                defaultdirectory,
                browserfilter, "", options)
        if fileName:
            self.executablepathCombobox.setEditText(os.path.normpath(fileName))

    def loadMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        self.mediadirectory = settings.value("mediadir", "")
        settings.endGroup()

    def saveMediaBrowseSettings(self):
        settings = QSettings("Syncplay", "MediaBrowseDialog")
        settings.beginGroup("MediaBrowseDialog")
        settings.setValue("mediadir", self.mediadirectory)
        settings.endGroup()

    def getMoreState(self):
        settings = QSettings("Syncplay", "MoreSettings")
        settings.beginGroup("MoreSettings")
        morestate = unicode.lower(unicode(settings.value("ShowMoreSettings", "false")))
        settings.endGroup()
        if morestate == "true":
            return(True)
        else:
            return(False)

    def saveMoreState(self, morestate):
        settings = QSettings("Syncplay", "MoreSettings")
        settings.beginGroup("MoreSettings")
        settings.setValue("ShowMoreSettings", morestate)
        settings.endGroup()

    def browseMediapath(self):
        self.loadMediaBrowseSettings()
        options = QtGui.QFileDialog.Options()
        if (os.path.isdir(self.mediadirectory)):
            defaultdirectory = self.mediadirectory
        elif (os.path.isdir(QDesktopServices.storageLocation(QDesktopServices.MoviesLocation))):
            defaultdirectory = QDesktopServices.storageLocation(QDesktopServices.MoviesLocation)
        elif (os.path.isdir(QDesktopServices.storageLocation(QDesktopServices.HomeLocation))):
            defaultdirectory = QDesktopServices.storageLocation(QDesktopServices.HomeLocation)
        else:
            defaultdirectory = ""
        browserfilter = "All files (*)"
        fileName, filtr = QtGui.QFileDialog.getOpenFileName(self, "Browse for media files", defaultdirectory,
                browserfilter, "", options)
        if fileName:
            self.mediapathTextbox.setText(os.path.normpath(fileName))
            self.mediadirectory = os.path.dirname(fileName)
            self.saveMediaBrowseSettings()

    def _saveDataAndLeave(self):
        self.config['host'] = self.hostTextbox.text() if ":" in self.hostTextbox.text() else self.hostTextbox.text() + ":" + unicode(constants.DEFAULT_PORT)
        self.config['name'] = self.usernameTextbox.text()
        self.config['room'] = self.defaultroomTextbox.text()
        self.config['password'] = self.serverpassTextbox.text()
        self.config['playerPath'] = unicode(self.executablepathCombobox.currentText())
        if self.mediapathTextbox.text() == "":
            self.config['file'] = None
        elif os.path.isfile(os.path.abspath(self.mediapathTextbox.text())):
            self.config['file'] = os.path.abspath(self.mediapathTextbox.text())
        else:
            self.config['file'] = unicode(self.mediapathTextbox.text())
        if self.alwaysshowCheckbox.isChecked() == True:
            self.config['forceGuiPrompt'] = True
        else:
            self.config['forceGuiPrompt'] = False
        if self.donotstoreCheckbox.isChecked() == True:
            self.config['noStore'] = True
        else:
            self.config['noStore'] = False
        if self.slowdownCheckbox.isChecked() == True:
            self.config['slowOnDesync'] = True
        else:
            self.config['slowOnDesync'] = False
        if self.dontslowwithmeCheckbox.isChecked() == True:
            self.config['dontSlowDownWithMe'] = True
        else:
            self.config['dontSlowDownWithMe'] = False
        if self.pauseonleaveCheckbox.isChecked() == True:
            self.config['pauseOnLeave'] = True
        else:
            self.config['pauseOnLeave'] = False


        if constants.SHOW_REWIND_ON_DESYNC_CHECKBOX == True:
            if self.rewindCheckbox.isChecked() == True:
                self.config['rewindOnDesync'] = True
            else:
                self.config['rewindOnDesync'] = False

        if self.filenameprivacySendRawOption.isChecked() == True:
            self.config['filenamePrivacyMode'] = constants.PRIVACY_SENDRAW_MODE
        elif self.filenameprivacySendHashedOption.isChecked() == True:
            self.config['filenamePrivacyMode'] = constants.PRIVACY_SENDHASHED_MODE
        elif self.filenameprivacyDontSendOption.isChecked() == True:
            self.config['filenamePrivacyMode'] = constants.PRIVACY_DONTSEND_MODE

        if self.filesizeprivacySendRawOption.isChecked() == True:
            self.config['filesizePrivacyMode'] = constants.PRIVACY_SENDRAW_MODE
        elif self.filesizeprivacySendHashedOption.isChecked() == True:
            self.config['filesizePrivacyMode'] = constants.PRIVACY_SENDHASHED_MODE
        elif self.filesizeprivacyDontSendOption.isChecked() == True:
            self.config['filesizePrivacyMode'] = constants.PRIVACY_DONTSEND_MODE

        self.pressedclosebutton = True
        self.close()
        return

    def closeEvent(self, event):
        if self.pressedclosebutton == False:
            sys.exit()
            raise GuiConfiguration.WindowClosed
            event.accept()

    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if (urls and urls[0].scheme() == 'file'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if (urls and urls[0].scheme() == 'file'):
            if sys.platform.startswith('linux'):
                dropfilepath = unicode(urls[0].path())
            else:
                dropfilepath = unicode(urls[0].path())[1:]  # Removes starting slash
            if dropfilepath[-4:].lower() == ".exe":
                self.executablepathCombobox.setEditText(dropfilepath)
            else:
                self.mediapathTextbox.setText(dropfilepath)

    def __init__(self, config, playerpaths, error):

        from syncplay import utils
        self.config = config
        self.datacleared = False
        if config['clearGUIData'] == True:
            settings = QSettings("Syncplay", "PlayerList")
            settings.clear()
            settings = QSettings("Syncplay", "MediaBrowseDialog")
            settings.clear()
            settings = QSettings("Syncplay", "MainWindow")
            settings.clear()
            settings = QSettings("Syncplay", "MoreSettings")
            settings.clear()
            self.datacleared = True
        self.QtGui = QtGui
        self.error = error
        if sys.platform.startswith('linux'):
            resourcespath = utils.findWorkingDir() + "/resources/"
        else:
            resourcespath = utils.findWorkingDir() + "\\resources\\"
        self.resourcespath = resourcespath

        super(ConfigDialog, self).__init__()

        self.setWindowTitle(getMessage("en", "config-window-title"))
        self.setWindowFlags(self.windowFlags() & Qt.WindowCloseButtonHint & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(QtGui.QIcon(resourcespath + "syncplay.png"))

        if(config['host'] == None):
            host = ""
        elif(":" in config['host']):
            host = config['host']
        else:
            host = config['host'] + ":" + str(config['port'])

        self.connectionSettingsGroup = QtGui.QGroupBox(getMessage("en", "connection-group-title"))
        self.hostTextbox = QLineEdit(host, self)
        self.hostLabel = QLabel(getMessage("en", "host-label"), self)
        self.usernameTextbox = QLineEdit(config['name'], self)
        self.serverpassLabel = QLabel(getMessage("en", "password-label"), self)
        self.defaultroomTextbox = QLineEdit(config['room'], self)
        self.usernameLabel = QLabel(getMessage("en", "username-label"), self)
        self.serverpassTextbox = QLineEdit(config['password'], self)
        self.defaultroomLabel = QLabel(getMessage("en", "room-label"), self)

        self.hostLabel.setToolTip(getMessage("en", "host-tooltip"))
        self.hostTextbox.setToolTip(getMessage("en", "host-tooltip"))
        self.usernameLabel.setToolTip(getMessage("en", "username-tooltip"))
        self.usernameTextbox.setToolTip(getMessage("en", "username-tooltip"))
        self.serverpassLabel.setToolTip(getMessage("en", "password-tooltip"))
        self.serverpassTextbox.setToolTip(getMessage("en", "password-tooltip"))
        self.defaultroomLabel.setToolTip(getMessage("en", "room-tooltip"))
        self.defaultroomTextbox.setToolTip(getMessage("en", "room-tooltip"))

        self.connectionSettingsLayout = QtGui.QGridLayout()
        self.connectionSettingsLayout.addWidget(self.hostLabel, 0, 0)
        self.connectionSettingsLayout.addWidget(self.hostTextbox, 0, 1)
        self.connectionSettingsLayout.addWidget(self.serverpassLabel, 1, 0)
        self.connectionSettingsLayout.addWidget(self.serverpassTextbox, 1, 1)
        self.connectionSettingsLayout.addWidget(self.usernameLabel, 2, 0)
        self.connectionSettingsLayout.addWidget(self.usernameTextbox, 2, 1)
        self.connectionSettingsLayout.addWidget(self.defaultroomLabel, 3, 0)
        self.connectionSettingsLayout.addWidget(self.defaultroomTextbox, 3, 1)
        self.connectionSettingsGroup.setLayout(self.connectionSettingsLayout)

        self.mediaplayerSettingsGroup = QtGui.QGroupBox(getMessage("en", "media-setting-title"))
        self.executableiconImage = QtGui.QImage()
        self.executableiconLabel = QLabel(self)
        self.executableiconLabel.setMinimumWidth(16)
        self.executablepathCombobox = QtGui.QComboBox(self)
        self.executablepathCombobox.setEditable(True)
        self.executablepathCombobox.currentIndexChanged.connect(self.updateExecutableIcon)
        self.executablepathCombobox.setEditText(self._tryToFillPlayerPath(config['playerPath'], playerpaths))
        self.executablepathCombobox.setMinimumWidth(200)
        self.executablepathCombobox.setMaximumWidth(200)
        self.executablepathCombobox.editTextChanged.connect(self.updateExecutableIcon)

        self.executablepathLabel = QLabel(getMessage("en", "executable-path-label"), self)
        self.executablebrowseButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'folder_explore.png'), getMessage("en", "browse-label"))
        self.executablebrowseButton.clicked.connect(self.browsePlayerpath)
        self.mediapathTextbox = QLineEdit(config['file'], self)
        self.mediapathLabel = QLabel(getMessage("en", "media-path-label"), self)
        self.mediabrowseButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'folder_explore.png'), getMessage("en", "browse-label"))
        self.mediabrowseButton.clicked.connect(self.browseMediapath)

        self.executablepathLabel.setToolTip(getMessage("en", "executable-path-tooltip"))
        self.executablepathCombobox.setToolTip(getMessage("en", "executable-path-tooltip"))
        self.mediapathLabel.setToolTip(getMessage("en", "media-path-tooltip"))
        self.mediapathTextbox.setToolTip(getMessage("en", "media-path-tooltip"))

        if constants.SHOW_REWIND_ON_DESYNC_CHECKBOX == True:
            self.rewindCheckbox = QCheckBox(getMessage("en", "rewind-label"))
            self.rewindCheckbox.setToolTip(getMessage("en", "rewind-tooltip"))
        self.mediaplayerSettingsLayout = QtGui.QGridLayout()
        self.mediaplayerSettingsLayout.addWidget(self.executablepathLabel, 0, 0)
        self.mediaplayerSettingsLayout.addWidget(self.executableiconLabel, 0, 1)
        self.mediaplayerSettingsLayout.addWidget(self.executablepathCombobox, 0, 2)
        self.mediaplayerSettingsLayout.addWidget(self.executablebrowseButton, 0, 3)
        self.mediaplayerSettingsLayout.addWidget(self.mediapathLabel, 1, 0)
        self.mediaplayerSettingsLayout.addWidget(self.mediapathTextbox , 1, 2)
        self.mediaplayerSettingsLayout.addWidget(self.mediabrowseButton , 1, 3)
        self.mediaplayerSettingsGroup.setLayout(self.mediaplayerSettingsLayout)

        self.moreSettingsGroup = QtGui.QGroupBox(getMessage("en", "more-title"))

        self.moreSettingsGroup.setCheckable(True)

        self.filenameprivacyLabel = QLabel(getMessage("en", "filename-privacy-label"), self)
        self.filenameprivacyButtonGroup = QButtonGroup()
        self.filenameprivacySendRawOption = QRadioButton(getMessage("en", "privacy-sendraw-option"))
        self.filenameprivacySendHashedOption = QRadioButton(getMessage("en", "privacy-sendhashed-option"))
        self.filenameprivacyDontSendOption = QRadioButton(getMessage("en", "privacy-dontsend-option"))
        self.filenameprivacyButtonGroup.addButton(self.filenameprivacySendRawOption)
        self.filenameprivacyButtonGroup.addButton(self.filenameprivacySendHashedOption)
        self.filenameprivacyButtonGroup.addButton(self.filenameprivacyDontSendOption)

        self.filesizeprivacyLabel = QLabel(getMessage("en", "filesize-privacy-label"), self)
        self.filesizeprivacyButtonGroup = QButtonGroup()
        self.filesizeprivacySendRawOption = QRadioButton(getMessage("en", "privacy-sendraw-option"))
        self.filesizeprivacySendHashedOption = QRadioButton(getMessage("en", "privacy-sendhashed-option"))
        self.filesizeprivacyDontSendOption = QRadioButton(getMessage("en", "privacy-dontsend-option"))
        self.filesizeprivacyButtonGroup.addButton(self.filesizeprivacySendRawOption)
        self.filesizeprivacyButtonGroup.addButton(self.filesizeprivacySendHashedOption)
        self.filesizeprivacyButtonGroup.addButton(self.filesizeprivacyDontSendOption)

        self.slowdownCheckbox = QCheckBox(getMessage("en", "slowdown-label"))
        self.dontslowwithmeCheckbox = QCheckBox(getMessage("en", "dontslowwithme-label"))
        self.pauseonleaveCheckbox = QCheckBox(getMessage("en", "pauseonleave-label"))
        self.alwaysshowCheckbox = QCheckBox(getMessage("en", "alwayshow-label"))
        self.donotstoreCheckbox = QCheckBox(getMessage("en", "donotstore-label"))

        filenamePrivacyMode = config['filenamePrivacyMode']
        if filenamePrivacyMode == constants.PRIVACY_DONTSEND_MODE:
            self.filenameprivacyDontSendOption.setChecked(True)
        elif filenamePrivacyMode == constants.PRIVACY_SENDHASHED_MODE:
            self.filenameprivacySendHashedOption.setChecked(True)
        else:
            self.filenameprivacySendRawOption.setChecked(True)

        filesizePrivacyMode = config['filesizePrivacyMode']
        if filesizePrivacyMode == constants.PRIVACY_DONTSEND_MODE:
            self.filesizeprivacyDontSendOption.setChecked(True)
        elif filesizePrivacyMode == constants.PRIVACY_SENDHASHED_MODE:
            self.filesizeprivacySendHashedOption.setChecked(True)
        else:
            self.filesizeprivacySendRawOption.setChecked(True)

        if config['slowOnDesync'] == True:
            self.slowdownCheckbox.setChecked(True)
        if config['dontSlowDownWithMe'] == True:
            self.dontslowwithmeCheckbox.setChecked(True)

        if constants.SHOW_REWIND_ON_DESYNC_CHECKBOX == True and config['rewindOnDesync'] == True:
            self.rewindCheckbox.setChecked(True)
        if config['pauseOnLeave'] == True:
            self.pauseonleaveCheckbox.setChecked(True)

        self.filenameprivacyLabel.setToolTip(getMessage("en", "filename-privacy-tooltip"))
        self.filenameprivacySendRawOption.setToolTip(getMessage("en", "privacy-sendraw-tooltip"))
        self.filenameprivacySendHashedOption.setToolTip(getMessage("en", "privacy-sendhashed-tooltip"))
        self.filenameprivacyDontSendOption.setToolTip(getMessage("en", "privacy-dontsend-tooltip"))
        self.filesizeprivacyLabel.setToolTip(getMessage("en", "filesize-privacy-tooltip"))
        self.filesizeprivacySendRawOption.setToolTip(getMessage("en", "privacy-sendraw-tooltip"))
        self.filesizeprivacySendHashedOption.setToolTip(getMessage("en", "privacy-sendhashed-tooltip"))
        self.filesizeprivacyDontSendOption.setToolTip(getMessage("en", "privacy-dontsend-tooltip"))

        self.slowdownCheckbox.setToolTip(getMessage("en", "slowdown-tooltip"))
        self.dontslowwithmeCheckbox.setToolTip(getMessage("en", "dontslowwithme-tooltip"))
        self.pauseonleaveCheckbox.setToolTip(getMessage("en", "pauseonleave-tooltip"))
        self.alwaysshowCheckbox.setToolTip(getMessage("en", "alwayshow-tooltip"))
        self.donotstoreCheckbox.setToolTip(getMessage("en", "donotstore-tooltip"))
        self.slowdownCheckbox.setToolTip(getMessage("en", "slowdown-tooltip"))

        self.moreSettingsLayout = QtGui.QGridLayout()

        self.privacySettingsLayout = QtGui.QGridLayout()
        self.privacyFrame = QtGui.QFrame()
        self.privacyFrame.setLineWidth(0)
        self.privacyFrame.setMidLineWidth(0)
        self.privacySettingsLayout.setContentsMargins(0, 0, 0, 0)
        self.privacySettingsLayout.addWidget(self.filenameprivacyLabel, 0, 0)
        self.privacySettingsLayout.addWidget(self.filenameprivacySendRawOption, 0, 1, Qt.AlignRight)
        self.privacySettingsLayout.addWidget(self.filenameprivacySendHashedOption, 0, 2, Qt.AlignRight)
        self.privacySettingsLayout.addWidget(self.filenameprivacyDontSendOption, 0, 3, Qt.AlignRight)
        self.privacySettingsLayout.addWidget(self.filesizeprivacyLabel, 1, 0)
        self.privacySettingsLayout.addWidget(self.filesizeprivacySendRawOption, 1, 1, Qt.AlignRight)
        self.privacySettingsLayout.addWidget(self.filesizeprivacySendHashedOption, 1, 2, Qt.AlignRight)
        self.privacySettingsLayout.addWidget(self.filesizeprivacyDontSendOption, 1, 3, Qt.AlignRight)
        self.privacyFrame.setLayout(self.privacySettingsLayout)

        self.moreSettingsLayout.addWidget(self.privacyFrame, 0, 0, 1, 4)

        self.moreSettingsLayout.addWidget(self.slowdownCheckbox, 2, 0, 1, 4)
        self.moreSettingsLayout.addWidget(self.dontslowwithmeCheckbox, 3, 0, 1, 4)
        if constants.SHOW_REWIND_ON_DESYNC_CHECKBOX == True:
            self.moreSettingsLayout.addWidget(self.rewindCheckbox, 4, 0, 1, 4)
        self.moreSettingsLayout.addWidget(self.pauseonleaveCheckbox, 5, 0, 1, 4)
        self.moreSettingsLayout.addWidget(self.alwaysshowCheckbox, 6, 0, 1, 4)
        self.moreSettingsLayout.addWidget(self.donotstoreCheckbox, 7, 0, 1, 4)

        self.moreSettingsGroup.setLayout(self.moreSettingsLayout)

        self.showmoreCheckbox = QCheckBox(getMessage("en", "more-title"))

        if self.getMoreState() == False:
            self.showmoreCheckbox.setChecked(False)
            self.moreSettingsGroup.hide()
        else:
            self.showmoreCheckbox.hide()
        self.showmoreCheckbox.toggled.connect(self.moreToggled)
        self.moreSettingsGroup.toggled.connect(self.moreToggled)

        if config['forceGuiPrompt'] == True:
            self.alwaysshowCheckbox.setChecked(True)

        self.showmoreCheckbox.setToolTip(getMessage("en", "more-tooltip"))

        self.donotstoreCheckbox.toggled.connect(self.runButtonTextUpdate)

        self.mainLayout = QtGui.QVBoxLayout()
        if error:
            self.errorLabel = QLabel(error, self)
            self.errorLabel.setAlignment(Qt.AlignCenter)
            self.errorLabel.setStyleSheet("QLabel { color : red; }")
            self.mainLayout.addWidget(self.errorLabel)
        self.mainLayout.addWidget(self.connectionSettingsGroup)
        self.mainLayout.addSpacing(12)
        self.mainLayout.addWidget(self.mediaplayerSettingsGroup)
        self.mainLayout.addSpacing(12)
        self.mainLayout.addWidget(self.showmoreCheckbox)
        self.mainLayout.addWidget(self.moreSettingsGroup)
        self.mainLayout.addSpacing(12)

        self.topLayout = QtGui.QHBoxLayout()
        self.helpButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'help.png'), getMessage("en", "help-label"))
        self.helpButton.setToolTip(getMessage("en", "help-tooltip"))
        self.helpButton.setMaximumSize(self.helpButton.sizeHint())
        self.helpButton.pressed.connect(self.openHelp)
        self.runButton = QtGui.QPushButton(QtGui.QIcon(resourcespath + 'accept.png'), getMessage("en", "storeandrun-label"))
        self.runButton.pressed.connect(self._saveDataAndLeave)
        if config['noStore'] == True:
            self.donotstoreCheckbox.setChecked(True)
            self.runButton.setText(getMessage("en", "run-label"))
        self.topLayout.addWidget(self.helpButton, Qt.AlignLeft)
        self.topLayout.addWidget(self.runButton, Qt.AlignRight)
        self.mainLayout.addLayout(self.topLayout)

        self.mainLayout.addStretch(1)
        self.setLayout(self.mainLayout)
        self.runButton.setFocus()
        self.setFixedSize(self.sizeHint())
        self.setAcceptDrops(True)

        if self.datacleared == True:
            QtGui.QMessageBox.information(self, "Syncplay", getMessage("en", "gui-data-cleared-notification"))

########NEW FILE########
__FILENAME__ = utils
import time
import re
import datetime
from syncplay import constants
from syncplay.messages import getMessage
import sys
import os
import itertools
import hashlib

def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        excpetions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            try_one_last_time = True
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                    try_one_last_time = False
                    break
                except ExceptionToCheck, e:
                    if logger:
                        msg = getMessage("en", "retrying-notification").format(str(e), mdelay)
                        logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if try_one_last_time:
                return f(*args, **kwargs)
            return
        return f_retry  # true decorator
    return deco_retry

def parseTime(timeStr):
    regex = re.compile(constants.PARSE_TIME_REGEX)
    parts = regex.match(timeStr)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.iteritems():
        if param:
            if(name == "miliseconds"):
                time_params["microseconds"] = int(param) * 1000
            else:
                time_params[name] = int(param)
    return datetime.timedelta(**time_params).total_seconds()

def formatTime(timeInSeconds, weeksAsTitles=True):
    if(timeInSeconds < 0):
        timeInSeconds = -timeInSeconds
        sign = '-'
    else:
        sign = ''
    timeInSeconds = round(timeInSeconds)
    weeks = timeInSeconds // 604800
    if weeksAsTitles and weeks > 0:
        title = weeks
        weeks = 0
    else:
        title = 0
    days = (timeInSeconds % 604800) // 86400
    hours = (timeInSeconds % 86400) // 3600
    minutes = (timeInSeconds % 3600) // 60
    seconds = timeInSeconds % 60
    if(weeks > 0):
        formattedTime = '{0:}{1:.0f}w, {2:.0f}d, {3:02.0f}:{4:02.0f}:{5:02.0f}'.format(sign, weeks, days, hours, minutes, seconds)
    elif(days > 0):
        formattedTime = '{0:}{1:.0f}d, {2:02.0f}:{3:02.0f}:{4:02.0f}'.format(sign, days, hours, minutes, seconds)
    elif(hours > 0):
        formattedTime = '{0:}{1:02.0f}:{2:02.0f}:{3:02.0f}'.format(sign, hours, minutes, seconds)
    else:
        formattedTime = '{0:}{1:02.0f}:{2:02.0f}'.format(sign, minutes, seconds)
    if title > 0:
        formattedTime = "{0:} (Title {1:.0f})".format(formattedTime, title)
    return formattedTime

def findWorkingDir():
    frozen = getattr(sys, 'frozen', '')
    if not frozen:
        path = os.path.dirname(os.path.dirname(__file__))
    elif frozen in ('dll', 'console_exe', 'windows_exe'):
        path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    else:
        path = ""
    return path

def limitedPowerset(s, minLength):
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in xrange(len(s), minLength, -1))

def blackholeStdoutForFrozenWindow():
    if getattr(sys, 'frozen', '') == "windows_exe":
        class Stderr(object):
            softspace = 0
            _file = None
            _error = None
            def write(self, text, fname='.syncplay.log'):
                if self._file is None and self._error is None:
                    if(os.name <> 'nt'):
                        path = os.path.join(os.getenv('HOME', '.'), fname)
                    else:
                        path = os.path.join(os.getenv('APPDATA', '.'), fname)
                    self._file = open(path, 'a')
                    #TODO: Handle errors.
                if self._file is not None:
                    self._file.write(text)
                    self._file.flush()
            def flush(self):
                if self._file is not None:
                    self._file.flush()
        sys.stderr = Stderr()
        del Stderr

        class Blackhole(object):
            softspace = 0
            def write(self, text):
                pass
            def flush(self):
                pass
        sys.stdout = Blackhole()
        del Blackhole

# Relate to file hashing / difference checking:

def stripfilename(filename):
    return re.sub(constants.FILENAME_STRIP_REGEX, "", filename)

def hashFilename(filename):
    return hashlib.sha256(stripfilename(filename).encode('utf-8')).hexdigest()[:12]

def hashFilesize(size):
    return hashlib.sha256(str(size)).hexdigest()[:12]

def sameHashed(string1raw, string1hashed, string2raw, string2hashed):
    if string1raw == string2raw:
        return True
    elif string1raw == string2hashed:
        return True
    elif string1hashed == string2raw:
        return True
    elif string1hashed == string2hashed:
        return True

def sameFilename (filename1, filename2):
    if filename1 == constants.PRIVACY_HIDDENFILENAME or filename2 == constants.PRIVACY_HIDDENFILENAME:
        return True
    elif sameHashed(stripfilename(filename1), hashFilename(filename1), stripfilename(filename2), hashFilename(filename2)):
        return True
    else:
        return False

def sameFilesize (filesize1, filesize2):
    if filesize1 == 0 or filesize2 == 0:
        return True
    elif sameHashed(filesize1, hashFilesize(filesize1), filesize2, hashFilesize(filesize2)):
        return True
    else:
        return False

def sameFileduration (duration1, duration2):
    if abs(round(duration1) - round(duration2)) < constants.DIFFFERENT_DURATION_THRESHOLD:
        return True
    else:
        return False

########NEW FILE########
__FILENAME__ = qt4reactor
# Copyright (c) 2001-2011 Twisted Matrix Laboratories.
# See LICENSE for details.


"""
This module provides support for Twisted to be driven by the Qt mainloop.

In order to use this support, simply do the following::
    |  app = QApplication(sys.argv) # your code to init Qt
    |  import qt4reactor
    |  qt4reactor.install()
    
alternatively:

    |  from twisted.application import reactors
    |  reactors.installReactor('qt4')

Then use twisted.internet APIs as usual.  The other methods here are not
intended to be called directly.

If you don't instantiate a QApplication or QCoreApplication prior to
installing the reactor, a QCoreApplication will be constructed
by the reactor.  QCoreApplication does not require a GUI so trial testing
can occur normally.

Twisted can be initialized after QApplication.exec_() with a call to
reactor.runReturn().  calling reactor.stop() will unhook twisted but
leave your Qt application running

API Stability: stable

Maintainer: U{Glenn H Tarbox, PhD<mailto:glenn@tarbox.org>}

Previous maintainer: U{Itamar Shtull-Trauring<mailto:twisted@itamarst.org>}
Original port to QT4: U{Gabe Rudy<mailto:rudy@goldenhelix.com>}
Subsequent port by therve
"""

import sys
import time
from zope.interface import implements
from twisted.internet.interfaces import IReactorFDSet
from twisted.python import log, runtime
from twisted.internet import posixbase
from twisted.python.runtime import platformType, platform

try:
    from PyQt4.QtCore import QSocketNotifier, QObject, SIGNAL, QTimer, QCoreApplication
    from PyQt4.QtCore import QEventLoop
except ImportError:
    from PySide.QtCore import QSocketNotifier, QObject, SIGNAL, QTimer, QCoreApplication
    from PySide.QtCore import QEventLoop


class TwistedSocketNotifier(QObject):
    """
    Connection between an fd event and reader/writer callbacks.
    """

    def __init__(self, parent, reactor, watcher, socketType):
        QObject.__init__(self, parent)
        self.reactor = reactor
        self.watcher = watcher
        fd = watcher.fileno()
        self.notifier = QSocketNotifier(fd, socketType, parent)
        self.notifier.setEnabled(True)
        if socketType == QSocketNotifier.Read:
            self.fn = self.read
        else:
            self.fn = self.write
        QObject.connect(self.notifier, SIGNAL("activated(int)"), self.fn)


    def shutdown(self):
        self.notifier.setEnabled(False)
        self.disconnect(self.notifier, SIGNAL("activated(int)"), self.fn)
        self.fn = self.watcher = None
        self.notifier.deleteLater()
        self.deleteLater()


    def read(self, fd):
        if not self.watcher:
            return
        w = self.watcher
        # doRead can cause self.shutdown to be called so keep a reference to self.watcher
        def _read():
            #Don't call me again, until the data has been read
            self.notifier.setEnabled(False)
            why = None
            try:
                why = w.doRead()
                inRead = True
            except:
                inRead = False
                log.err()
                why = sys.exc_info()[1]
            if why:
                self.reactor._disconnectSelectable(w, why, inRead)
            elif self.watcher:
                self.notifier.setEnabled(True) # Re enable notification following sucessfull read
            self.reactor._iterate(fromqt=True)
        log.callWithLogger(w, _read)

    def write(self, sock):
        if not self.watcher:
            return
        w = self.watcher
        def _write():
            why = None
            self.notifier.setEnabled(False)
            
            try:
                why = w.doWrite()
            except:
                log.err()
                why = sys.exc_info()[1]
            if why:
                self.reactor._disconnectSelectable(w, why, False)
            elif self.watcher:
                self.notifier.setEnabled(True)
            self.reactor._iterate(fromqt=True)
        log.callWithLogger(w, _write)



class QtReactor(posixbase.PosixReactorBase):
    implements(IReactorFDSet)

    def __init__(self):
        self._reads = {}
        self._writes = {}
        self._notifiers = {}
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        QObject.connect(self._timer, SIGNAL("timeout()"), self.iterate)

        if QCoreApplication.instance() is None:
            # Application Object has not been started yet
            self.qApp=QCoreApplication([])
            self._ownApp=True
        else:
            self.qApp = QCoreApplication.instance()
            self._ownApp=False
        self._blockApp = None
        posixbase.PosixReactorBase.__init__(self)


    def _add(self, xer, primary, type):
        """
        Private method for adding a descriptor from the event loop.

        It takes care of adding it if  new or modifying it if already added
        for another state (read -> read/write for example).
        """
        if xer not in primary:
            primary[xer] = TwistedSocketNotifier(None, self, xer, type)


    def addReader(self, reader):
        """
        Add a FileDescriptor for notification of data available to read.
        """
        self._add(reader, self._reads, QSocketNotifier.Read)


    def addWriter(self, writer):
        """
        Add a FileDescriptor for notification of data available to write.
        """
        self._add(writer, self._writes, QSocketNotifier.Write)


    def _remove(self, xer, primary):
        """
        Private method for removing a descriptor from the event loop.

        It does the inverse job of _add, and also add a check in case of the fd
        has gone away.
        """
        if xer in primary:
            notifier = primary.pop(xer)
            notifier.shutdown()

        
    def removeReader(self, reader):
        """
        Remove a Selectable for notification of data available to read.
        """
        self._remove(reader, self._reads)


    def removeWriter(self, writer):
        """
        Remove a Selectable for notification of data available to write.
        """
        self._remove(writer, self._writes)


    def removeAll(self):
        """
        Remove all selectables, and return a list of them.
        """
        rv = self._removeAll(self._reads, self._writes)
        return rv


    def getReaders(self):
        return self._reads.keys()


    def getWriters(self):
        return self._writes.keys()


    def callLater(self,howlong, *args, **kargs):
        rval = super(QtReactor,self).callLater(howlong, *args, **kargs)
        self.reactorInvocation()
        return rval


    def reactorInvocation(self):
        self._timer.stop()
        self._timer.setInterval(0)
        self._timer.start()
        

    def _iterate(self, delay=None, fromqt=False):
        """See twisted.internet.interfaces.IReactorCore.iterate.
        """
        self.runUntilCurrent()
        self.doIteration(delay, fromqt)

    iterate = _iterate

    def doIteration(self, delay=None, fromqt=False):
        'This method is called by a Qt timer or by network activity on a file descriptor'
        
        if not self.running and self._blockApp:
            self._blockApp.quit()
        self._timer.stop()
        delay = max(delay, 1)
        if not fromqt:
            self.qApp.processEvents(QEventLoop.AllEvents, delay * 1000)
        if self.timeout() is None:
            timeout = 0.1
        elif self.timeout() == 0:
            timeout = 0
        else:
            timeout = self.timeout()
        self._timer.setInterval(timeout * 1000)
        self._timer.start()


    def runReturn(self, installSignalHandlers=True):
        self.startRunning(installSignalHandlers=installSignalHandlers)
        self.reactorInvocation()


    def run(self, installSignalHandlers=True):
        if self._ownApp:
            self._blockApp = self.qApp
        else:
            self._blockApp = QEventLoop()
        self.runReturn()
        self._blockApp.exec_()


class QtEventReactor(QtReactor):
    def __init__(self, *args, **kwargs):
        self._events = {}
        super(QtEventReactor, self).__init__()

        
    def addEvent(self, event, fd, action):
        """
        Add a new win32 event to the event loop.
        """
        self._events[event] = (fd, action)


    def removeEvent(self, event):
        """
        Remove an event.
        """
        if event in self._events:
            del self._events[event]


    def doEvents(self):
        handles = self._events.keys()
        if len(handles) > 0:
            val = None
            while val != WAIT_TIMEOUT:
                val = MsgWaitForMultipleObjects(handles, 0, 0, QS_ALLINPUT | QS_ALLEVENTS)
                if val >= WAIT_OBJECT_0 and val < WAIT_OBJECT_0 + len(handles):
                    event_id = handles[val - WAIT_OBJECT_0]
                    if event_id in self._events:
                        fd, action = self._events[event_id]
                        log.callWithLogger(fd, self._runAction, action, fd)
                elif val == WAIT_TIMEOUT:
                    pass
                else:
                    #print 'Got an unexpected return of %r' % val
                    return


    def _runAction(self, action, fd):
        try:
            closed = getattr(fd, action)()
        except:
            closed = sys.exc_info()[1]
            log.deferr()

        if closed:
            self._disconnectSelectable(fd, closed, action == 'doRead')

            
    def timeout(self):
        t = super(QtEventReactor, self).timeout()
        return min(t, 0.01)


    def iterate(self, delay=None):
        """See twisted.internet.interfaces.IReactorCore.iterate.
        """
        self.runUntilCurrent()
        self.doEvents()
        self.doIteration(delay)


def posixinstall():
    """
    Install the Qt reactor.
    """
    p = QtReactor()
    from twisted.internet.main import installReactor
    installReactor(p)


def win32install():
    """
    Install the Qt reactor.
    """
    p = QtEventReactor()
    from twisted.internet.main import installReactor
    installReactor(p)


if runtime.platform.getType() == 'win32':
    from win32event import CreateEvent, MsgWaitForMultipleObjects
    from win32event import WAIT_OBJECT_0, WAIT_TIMEOUT, QS_ALLINPUT, QS_ALLEVENTS
    install = win32install
else:
    install = posixinstall


__all__ = ["install"]


########NEW FILE########
__FILENAME__ = syncplayClient
#!/usr/bin/env python

import site

# libpath

from syncplay.clientManager import SyncplayClientManager
from syncplay.utils import blackholeStdoutForFrozenWindow

if(__name__ == '__main__'):
    blackholeStdoutForFrozenWindow()
    SyncplayClientManager().run()
    

########NEW FILE########
__FILENAME__ = syncplayServer
#!/usr/bin/env python
#coding:utf8

import site

# libpath

from twisted.internet import reactor

from syncplay.server import SyncFactory, ConfigurationGetter

if __name__ == '__main__':
    argsGetter = ConfigurationGetter()
    args = argsGetter.getConfiguration()

    reactor.listenTCP(int(args.port), SyncFactory(args.password, args.motd_file, args.isolate_rooms))
    reactor.run()

########NEW FILE########
