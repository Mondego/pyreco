__FILENAME__ = application
import scriptcontext
import Rhino
import Rhino.ApplicationSettings.ModelAidSettings as modelaid
import Rhino.Commands.Command as rhcommand
import System.TimeSpan, System.Enum
import System.Windows.Forms.Screen
import datetime
import utility as rhutil


def AddAlias(alias, macro):
    """Adds new command alias to Rhino. Command aliases can be added manually by
    using Rhino's Options command and modifying the contents of the Aliases tab.
    Parameters:
      alias = name of new command alias. Cannot match command names or existing
              aliases.
      macro = The macro to run when the alias is executed.
    Returns:
      True or False indicating success or failure.
    """
    return Rhino.ApplicationSettings.CommandAliasList.Add(alias, macro)


def AddSearchPath(folder, index=-1):
    """Add new path to Rhino's search path list. Search paths can be added by
    using Rhino's Options command and modifying the contents of the files tab.
    Parameters:
      folder = A valid folder, or path, to add.
      index [opt] = Zero-based position in the search path list to insert.
                    If omitted, path will be appended to the end of the
                    search path list.
    """
    return Rhino.ApplicationSettings.FileSettings.AddSearchPath(folder, index)


def AliasCount():
    "Returns number of command aliases in Rhino."
    return Rhino.ApplicationSettings.CommandAliasList.Count


def AliasMacro(alias, macro=None):
    """Returns or modifies the macro of a command alias.
    Parameters:
      alias = The name of an existing command alias.
      macro [opt] = The new macro to run when the alias is executed.
    Returns:
      If a new macro is not specified, the existing macro if successful.
      If a new macro is specified, the previous macro if successful.
      None on error
    """
    rc = Rhino.ApplicationSettings.CommandAliasList.GetMacro(alias)
    if macro:
        Rhino.ApplicationSettings.CommandAliasList.SetMacro(alias, macro)
    if rc is None: return scriptcontext.errorhandler()
    return rc


def AliasNames():
    "Returns a list of command alias names."
    return Rhino.ApplicationSettings.CommandAliasList.GetNames()


def AppearanceColor(item, color=None):
    """Returns or modifies an application interface item's color.
    Parameters:
      item = Item number to either query or modify
             0  = View background
             1  = Major grid line
             2  = Minor grid line
             3  = X-Axis line
             4  = Y-Axis line
             5  = Selected Objects
             6  = Locked Objects
             7  = New layers
             8  = Feedback
             9  = Tracking
             10 = Crosshair
             11 = Text
             12 = Text Background
             13 = Text hover
      color[opt] = The new color value
    Returns:
      if color is not specified, the current item color
      if color is specified, the previous item color
    """
    rc = None
    color = rhutil.coercecolor(color)
    appearance = Rhino.ApplicationSettings.AppearanceSettings
    if item==0:
        rc = appearance.ViewportBackgroundColor
        if color: appearance.ViewportBackgroundColor = color
    elif item==1:
        rc = appearance.GridThickLineColor
        if color: appearance.GridThickLineColor = color
    elif item==2:
        rc = appearance.GridThinLineColor
        if color: appearance.GridThinLineColor = color
    elif item==3:
        rc = appearance.GridXAxisLineColor
        if color: appearance.GridXAxisLineColor = color
    elif item==4:
        rc = appearance.GridYAxisLineColor
        if color: appearance.GridYAxisLineColor = color
    elif item==5:
        rc = appearance.SelectedObjectColor
        if color: appearance.SelectedObjectColor = color
    elif item==6:
        rc = appearance.LockedObjectColor
        if color: appearance.LockedObjectColor = color
    elif item==7:
        rc = appearance.DefaultLayerColor
        if color: appearance.DefaultLayerColor = color
    elif item==8:
        rc = appearance.FeedbackColor
        if color: appearance.FeedbackColor = color
    elif item==9:
        rc = appearance.TrackingColor
        if color: appearance.TrackingColor = color
    elif item==10:
        rc = appearance.CrosshairColor
        if color: appearance.CrosshairColor = color
    elif item==11:
        rc = appearance.CommandPromptTextColor
        if color: appearance.CommandPromptTextColor = color
    elif item==12:
        rc = appearance.CommandPromptBackgroundColor
        if color: appearance.CommandPromptBackgroundColor = color
    elif item==13:
        rc = appearance.CommandPromptHypertextColor
        if color: appearance.CommandPromptHypertextColor = color
    if rc is None: raise ValueError("item is out of range")
    scriptcontext.doc.Views.Redraw()
    return rc


def AutosaveFile(filename=None):
    """Returns or changes the file name used by Rhino's automatic file saving
    Parameters:
      filename [opt] = name of the new autosave file
    Returns:
      if filename is not specified, the name of the current autosave file
      if filename is specified, the name of the previous autosave file
    """
    rc = Rhino.ApplicationSettings.FileSettings.AutosaveFile
    if filename: Rhino.ApplicationSettings.FileSettings.AutosaveFile = filename
    return rc


def AutosaveInterval(minutes=None):
    """Returns or changes how often the document will be saved when Rhino's
    automatic file saving mechanism is enabled
    Parameters:
      minutes [opt] = the number of minutes between saves
    Returns:
      if minutes is not specified, the current interval in minutes
      if minutes is specified, the previous interval in minutes
    """
    rc = Rhino.ApplicationSettings.FileSettings.AutosaveInterval.TotalMinutes
    if minutes:
        timespan = System.TimeSpan.FromMinutes(minutes)
        Rhino.ApplicationSettings.FileSettings.AutosaveInterval = timespan
    return rc


def BuildDate():
    "Returns the builddate of Rhino"
    build = Rhino.RhinoApp.BuildDate
    return datetime.date(build.Year, build.Month, build.Day)


def ClearCommandHistory():
    """Clears contents of Rhino's command history window. You can view the
    command history window by using the CommandHistory command in Rhino.
    """
    Rhino.RhinoApp.ClearCommandHistoryWindow()


__command_serial_numbers = None

def Command(commandString, echo=True):
    """Runs a Rhino command script. All Rhino commands can be used in command
    scripts. The command can be a built-in Rhino command or one provided by a
    3rd party plug-in.
    Parameters:
      commandString = a Rhino command including any arguments
      echo[opt] = the command echo mode
    Returns:
      True or False indicating success or failure
    
    Write command scripts just as you would type the command sequence at the
    command line. A space or a new line acts like pressing <Enter> at the
    command line. For more information, see "Scripting" in Rhino help.

    Note, this function is designed to run one command and one command only.
    Do not combine multiple Rhino commands into a single call to this method.
      WRONG:
        rs.Command("_Line _SelLast _Invert")
      CORRECT:
        rs.Command("_Line")
        rs.Command("_SelLast")
        rs.Command("_Invert")

    Also, the exclamation point and space character ( ! ) combination used by
    button macros and batch-driven scripts to cancel the previous command is
    not valid.
      WRONG:
        rs.Command("! _Line _Pause _Pause")
      CORRECT:
        rs.Command("_Line _Pause _Pause")
    After the command script has run, you can obtain the identifiers of most
    recently created or changed object by calling LastCreatedObjects.
    """
    start = Rhino.DocObjects.RhinoObject.NextRuntimeSerialNumber
    rc = Rhino.RhinoApp.RunScript(commandString, echo)
    end = Rhino.DocObjects.RhinoObject.NextRuntimeSerialNumber
    global __command_serial_numbers
    __command_serial_numbers = None
    if start!=end: __command_serial_numbers = (start,end)
    return rc


def CommandHistory():
    "Returns the contents of Rhino's command history window"
    return Rhino.RhinoApp.CommandHistoryWindowText


def DefaultRenderer(renderer=None):
    "Returns or changes the default render plug-in"
    id = Rhino.Render.Utilities.DefaultRenderPlugInId
    plugins = Rhino.PlugIns.PlugIn.GetInstalledPlugIns()
    rc = plugins[id]
    if renderer:
        id = Rhino.PlugIns.PlugIn.IdFromName(renderer)
        Rhino.Render.Utilities.SetDefaultRenderPlugIn(id)
    return rc


def DeleteAlias(alias):
    """Delete an existing alias from Rhino.
    Parameters:
      alias = the name of an existing alias
    Returns:
      True or False indicating success
    """
    return Rhino.ApplicationSettings.CommandAliasList.Delete(alias)


def DeleteSearchPath(folder):
    """Removes existing path from Rhino's search path list. Search path items
    can be removed manually by using Rhino's options command and modifying the
    contents of the files tab
    Parameters:
      folder = a folder to remove
    Returns:
      True or False indicating success
    """
    return Rhino.ApplicationSettings.FileSettings.DeleteSearchPath(folder)


def DisplayOleAlerts( enable ):
    "Enables/disables OLE Server Busy/Not Responding dialog boxes"
    Rhino.Runtime.HostUtils.DisplayOleAlerts( enable )


def EdgeAnalysisColor(color=None):
    """Returns or modifies edge analysis color displayed by the ShowEdges command
    Parameters:
      color [opt] = the new color
    Returns:
      if color is not specified, the current edge analysis color
      if color is specified, the previous edge analysis color
    """
    rc = Rhino.ApplicationSettings.EdgeAnalysisSettings.ShowEdgeColor
    if color:
        color = rhutil.coercecolor(color, True)
        Rhino.ApplicationSettings.EdgeAnalysisSettings.ShowEdgeColor = color
    return rc


def EdgeAnalysisMode(mode=None):
    """Returns or modifies edge analysis mode displayed by the ShowEdges command
    Parameters:
      mode [opt] = the new display mode. The available modes are
                   0 - display all edges
                   1 - display naked edges
    Returns:
      if mode is not specified, the current edge analysis mode
      if mode is specified, the previous edge analysis mode
    """
    rc = Rhino.ApplicationSettings.EdgeAnalysisSettings.ShowEdges
    if mode==1 or mode==2:
        Rhino.ApplicationSettings.EdgeAnalysisSettings.ShowEdges = mode
    return rc


def EnableAutosave(enable=True):
    """Enables or disables Rhino's automatic file saving mechanism
    Parameters:
      enable = the autosave state
    Returns:
      the previous autosave state
    """
    rc = Rhino.ApplicationSettings.FileSettings.AutosaveEnabled
    if rc!=enable: Rhino.ApplicationSettings.FileSettings.AutosaveEnabled = enable
    return rc


def EnablePlugIn(plugin, enable=None):
    """Enables or disables a Rhino plug-in"""
    id = rhutil.coerceguid(plugin)
    if not id: id = Rhino.PlugIns.PlugIn.IdFromName(plugin)
    rc, loadSilent = Rhino.PlugIns.PlugIn.GetLoadProtection(id)
    if enable is not None:
        Rhino.PlugIns.PlugIn.SetLoadProtection(id, enable)
    return loadSilent


def ExeFolder():
    "Returns the full path to Rhino's executable folder."
    return Rhino.ApplicationSettings.FileSettings.ExecutableFolder


def Exit():
    "Closes the rhino application"
    Rhino.RhinoApp.Exit()


def FindFile(filename):
    """Searches for a file using Rhino's search path. Rhino will look for a
    file in the following locations:
      1. The current document's folder.
      2. Folder's specified in Options dialog, File tab.
      3. Rhino's System folders
    Parameters:
      filename = short file name to search for
    Returns:
      full path on success
    """
    return Rhino.ApplicationSettings.FileSettings.FindFile(filename)


def GetPlugInObject(plug_in):
    """Returns a scriptable object from a specified plug-in. Not all plug-ins
    contain scriptable objects. Check with the manufacturer of your plug-in
    to see if they support this capability.
    Parameters:
      plug_in = name or Id of a registered plug-in that supports scripting.
                If the plug-in is registered but not loaded, it will be loaded
    Returns:
      scriptable object if successful
      None on error
    """
    return Rhino.RhinoApp.GetPlugInObject(plug_in)
  

def InCommand(ignore_runners=True):
    """Determines if Rhino is currently running a command. Because Rhino allows
    for transparent commands (commands run from inside of other commands), this
    method returns the total number of active commands.
    Parameters:
      ignore_runners [opt] = If true, script running commands, such as
          LoadScript, RunScript, and ReadCommandFile will not counted.
    Returns:
      the number of active commands
    """
    ids = rhcommand.GetCommandStack()
    return len(ids)


def InstallFolder():
    "The full path to Rhino's installation folder"
    return Rhino.ApplicationSettings.FileSettings.InstallFolder


def IsAlias(alias):
    """Verifies that a command alias exists in Rhino
    Parameters:
      the name of an existing command alias
    """
    return Rhino.ApplicationSettings.CommandAliasList.IsAlias(alias)


def IsCommand(command_name):
    """Verifies that a command exists in Rhino. Useful when scripting commands
    found in 3rd party plug-ins.
    Parameters:
      command_name = the command name to test
    """
    return rhcommand.IsCommand(command_name)


def IsPlugIn(plugin):
    "Verifies that a plug-in is registered"
    id = rhutil.coerceguid(plugin)
    if not id: id = Rhino.PlugIns.PlugIn.IdFromName(plugin)
    if id:
        rc, loaded, loadprot = Rhino.PlugIns.PlugIn.PlugInExists(id)
        return rc


def IsRunningOnWindows():
    "Returns True if this script is being executed on a Windows platform"
    return Rhino.Runtime.HostUtils.RunningOnWindows


def LastCommandName():
    "Returns the name of the last executed command"
    id = rhcommand.LastCommandId
    return rhcommand.LookupCommandName(id, True)


def LastCommandResult():
    """Returns the result code for the last executed command
    0 = success (command successfully completed)
    1 = cancel (command was cancelled by the user)
    2 = nothing (command did nothing, but was not cancelled)
    3 = failure (command failed due to bad input, computational problem...)
    4 = unknown command (the command was not found)
    """
    return int(rhcommand.LastCommandResult)


def LocaleID():
    """Returns the current language used for the Rhino interface.  The current
    language is returned as a locale ID, or LCID, value.
      1029  Czech
      1031  German-Germany
      1033  English-United States
      1034  Spanish-Spain
      1036  French-France
      1040  Italian-Italy
      1041  Japanese
      1042  Korean
      1045  Polish
    """
    return Rhino.ApplicationSettings.AppearanceSettings.LanguageIdentifier


def Ortho(enable=None):
    """Enables or disables Rhino's ortho modeling aid.
    Parameters:
      enable [opt] = the new enabled status (True or False)
    Returns:
      if enable is not specified, then the current ortho status
      if enable is secified, then the previous ortho status
    """
    rc = modelaid.Ortho
    if enable!=None: modelaid.Ortho = enable
    return rc


def Osnap(enable=None):
    """Enables or disables Rhino's object snap modeling aid.
    Object snaps are tools for specifying points on existing objects.
    Parameters:
      enable [opt] = the new enabled status (True or False)
    Returns:
      if enable is not specified, then the current osnap status
      if enable is secified, then the previous osnap status
    """
    rc = modelaid.Osnap
    if enable!=None: modelaid.Osnap = enable
    return rc


def OsnapDialog(visible=None):
    """Shows or hides Rhino's dockable object snap bar
    Parameters:
      visible [opt] = the new visibility state (True or False)
    Returns:
      if visible is not specified, then the current visible state
      if visible is secified, then the previous visible state
    """
    rc = modelaid.UseHorizontalDialog
    if visible is not None: modelaid.UseHorizontalDialog = visible
    return rc


def OsnapMode(mode=None):
    """Returns or sets the object snap mode. Object snaps are tools for
    specifying points on existing objects
    Parameters:
      mode [opt] = The object snap mode or modes to set. Object snap modes
                   can be added together to set multiple modes
                   0     None
                   2     Near
                   8     Focus
                   32    Center
                   64    Vertex
                   128   Knot
                   512   Quadrant
                   2048  Midpoint
                   8192  Intersection
                   0x20000   End
                   0x80000   Perpendicular
                   0x200000   Tangent
                   0x8000000  Point
    Returns:
      if mode is not specified, then the current object snap mode(s)
      if mode is specified, then the previous object snap mode(s) 
    """
    rc = modelaid.OsnapModes
    if mode is not None:
        modelaid.OsnapModes = System.Enum.ToObject(Rhino.ApplicationSettings.OsnapModes, mode)
    return int(rc)


def Planar(enable=None):
    """Enables or disables Rhino's planar modeling aid
    Parameters:
      enable = the new enable status (True or False)
    Returns:
      if enable is not specified, then the current planar status
      if enable is secified, then the previous planar status
    """
    rc = modelaid.Planar
    if enable is not None: modelaid.Planar = enable
    return rc


def PlugInId(plugin):
    "Returns the identifier of a plug-in given the plug-in name"
    id = Rhino.PlugIns.PlugIn.IdFromName(plugin)
    if id!=System.Guid.Empty: return id


def PlugIns(types=0, status=0):
    """Returns a list of registered Rhino plug-ins
    Parameters:
      types[opt] = type of plug-ins to return. 0=all, 1=render, 2=file export,
        4=file import, 8=digitizer, 16=utility
      status[opt] = 0=both loaded and unloaded, 1=loaded, 2=unloaded
    """
    filter = Rhino.PlugIns.PlugInType.None
    if types&1: filter |= Rhino.PlugIns.PlugInType.Render
    if types&2: filter |= Rhino.PlugIns.PlugInType.FileExport
    if types&4: filter |= Rhino.PlugIns.PlugInType.FileImport
    if types&8: filter |= Rhino.PlugIns.PlugInType.Digitiger
    if types&16: filter |= Rhino.PlugIns.PlugInType.Utility
    if types==0: filter = Rhino.PlugIns.PlugInType.Any
    loaded = (status==0 or status==1)
    unloaded = (status==0 or status==2)
    names = Rhino.PlugIns.PlugIn.GetInstalledPlugInNames(filter, loaded, unloaded)
    return list(names)


def ProjectOsnaps(enable=None):
    """Enables or disables object snap projection
    Parameters:
      enable [opt] = the new enabled status (True or False)
    Returns:
      if enable is not specified, the current object snap projection status
      if enable is specified, the previous object snap projection status
    """
    rc = modelaid.ProjectSnapToCPlane
    if enable is not None: modelaid.ProjectSnapToCPlane = enable
    return rc


def Prompt(message=None):
    """Change Rhino's command window prompt
    Parameters:
      message [opt] = the new prompt
    """
    if message and type(message) is not str:
        strList = [str(item) for item in message]
        message = "".join(strList)
    Rhino.RhinoApp.SetCommandPrompt(message)


def ScreenSize():
    """Returns current width and height, of the screen of the primary monitor.
    Returns:
      Tuple containing two numbers identifying the width and height
    """
    sz = System.Windows.Forms.Screen.PrimaryScreen.Bounds
    return sz.Width, sz.Height


def SdkVersion():
    """Returns version of the Rhino SDK supported by the executing Rhino.
    Rhino SDK versions are 9 digit numbers in the form of YYYYMMDDn.
    """
    return Rhino.RhinoApp.SdkVersion


def SearchPathCount():
    """Returns the number of path items in Rhino's search path list.
    See "Options Files settings" in the Rhino help file for more details.
    """
    return Rhino.ApplicationSettings.FileSettings.SearchPathCount


def SearchPathList():
    """Returns all of the path items in Rhino's search path list.
    See "Options Files settings" in the Rhino help file for more details.
    """
    return Rhino.ApplicationSettings.FileSettings.GetSearchPaths()


def SendKeystrokes(keys=None, add_return=True):
    """Sends a string of printable characters to Rhino's command line
    Parameters:
      keys [opt] = A string of characters to send to the command line.
      add_returns [opt] = Append a return character to the end of the string.
    """
    Rhino.RhinoApp.SendKeystrokes(keys, add_return)


def Snap(enable=None):
    """Enables or disables Rhino's grid snap modeling aid
    Parameters:
      enable [opt] = the new enabled status (True or False)
    Returns:
      if enable is not specified, the current grid snap status
      if enable is specified, the previous grid snap status  
    """
    rc = modelaid.GridSnap
    if enable is not None: modelaid.GridSnap = rc
    return rc


def StatusBarDistance(distance=0):
    "Sets Rhino's status bar distance pane"
    Rhino.UI.StatusBar.SetDistancePane(distance)


def StatusBarMessage(message=None):
    "Sets Rhino's status bar message pane"
    Rhino.UI.StatusBar.SetMessagePane(message)


def StatusBarPoint(point=None):
    "Sets Rhino's status bar point coordinate pane"
    point = rhutil.coerce3dpoint(point)
    if not point: point = Rhino.Geometry.Point3d(0,0,0)
    Rhino.UI.StatusBar.SetPointPane(point)


def StatusBarProgressMeterShow(label, lower, upper, embed_label=True, show_percent=True):
    """Start the Rhino status bar progress meter
    Parameters:
      label = short description of the progesss
      lower = lower limit of the progress meter's range
      upper = upper limit of the progress meter's range
      embed_label[opt] = if True, the label will show inside the meter.
        If false, the label will show to the left of the meter
      show_percent[opt] = show the percent complete
    Returns:
      True or False indicating success or failure
    """
    rc = Rhino.UI.StatusBar.ShowProgressMeter(lower, upper, label, embed_label, show_percent)
    return rc==1


def StatusBarProgressMeterUpdate(position, absolute=True):
    """Set the current position of the progress meter
    Parameters:
      position = new position in the progress meter
      absolute[opt] = position is an absolute or relative
    Returns:
      previous position setting
    """
    return Rhino.UI.StatusBar.UpdateProgressMeter(position, absolute)


def StatusBarProgressMeterHide():
    "Hide the progress meter"
    Rhino.UI.StatusBar.HideProgressMeter()


def TemplateFile(filename=None):
    """Returns or sets Rhino's default template file. This is the file used
    when Rhino starts.
    Parameters:
      filename[opt] = The name of the new default template file (must exist)
    Returns:
      if filename is not specified, then the current default template file
      if filename is specified, then the previous default template file
    """
    rc = Rhino.ApplicationSettings.FileSettings.TemplateFile
    if filename: Rhino.ApplicationSettings.FileSettings.TemplateFile = filename
    return rc


def TemplateFolder(folder=None):
    """Returns or sets the location of Rhino's template folder
    Parameters:
      The location of Rhino's template files. Note, the location must exist
    Returns:
      if folder is not specified, then the current template file folder
      if folder is specified, then the previous template file folder
    """
    rc = Rhino.ApplicationSettings.FileSettings.TemplateFolder
    if folder is not None: Rhino.ApplicationSettings.FileSettings.TemplateFolder = folder
    return rc


def WindowHandle():
    "Returns the windows handle of Rhino's main window"
    return Rhino.RhinoApp.MainWindowHandle()


def WorkingFolder(folder=None):
    """Returns or sets Rhino's working folder (directory).
    The working folder is the default folder for all file operations.
    Parameters:
      folder[opt] = the new working folder
    Returns:
      if folder is not specified, then the current working folder
      if folder is specified, then the previous working folder
    """
    rc = Rhino.ApplicationSettings.FileSettings.WorkingFolder
    if folder is not None: Rhino.ApplicationSettings.FileSettings.WorkingFolder = folder
    return rc

########NEW FILE########
__FILENAME__ = block
import Rhino
import scriptcontext
import utility as rhutil
import math
import System.Guid

def __InstanceObjectFromId(id, raise_if_missing):
    rhobj = rhutil.coercerhinoobject(id, True, raise_if_missing)
    if isinstance(rhobj, Rhino.DocObjects.InstanceObject): return rhobj
    if raise_if_missing: raise ValueError("unable to find InstanceObject")


def AddBlock(object_ids, base_point, name=None, delete_input=False):
    """Adds a new block definition to the document
    Parameters:
      object_ids = objects that will be included in the block
      base_point = 3D base point for the block definition
      name(opt) = name of the block definition. If omitted a name will be
        automatically generated
      delete_input(opt) = if True, the object_ids will be deleted
    Returns:
      name of new block definition on success
    """
    base_point = rhutil.coerce3dpoint(base_point, True)
    if not name:
        name = scriptcontext.doc.InstanceDefinitions.GetUnusedInstanceDefinitionName()
    found = scriptcontext.doc.InstanceDefinitions.Find(name, True)
    objects = []
    for id in object_ids:
        obj = rhutil.coercerhinoobject(id, True)
        if obj.IsReference: return
        ot = obj.ObjectType
        if ot==Rhino.DocObjects.ObjectType.Light: return
        if ot==Rhino.DocObjects.ObjectType.Grip: return
        if ot==Rhino.DocObjects.ObjectType.Phantom: return
        if ot==Rhino.DocObjects.ObjectType.InstanceReference and found:
            uses, nesting = obj.UsesDefinition(found.Index)
            if uses: return
        objects.append(obj)
    if objects:
        geometry = [obj.Geometry for obj in objects]
        attrs = [obj.Attributes for obj in objects]
        rc = scriptcontext.doc.InstanceDefinitions.Add(name, "", base_point, geometry, attrs)
        if rc>=0:
            if delete_input:
                for obj in objects: scriptcontext.doc.Objects.Delete(obj, True)
            scriptcontext.doc.Views.Redraw()
            return name


def BlockContainerCount(block_name):
    """Returns number of block definitions that contain a specified
    block definition
    Parameters:
      block_name = the name of an existing block definition
    """
    return len(BlockContainers(block_name))


def BlockContainers(block_name):
    """Returns names of the block definitions that contain a specified block
    definition.
    Parameters:
      block_name = the name of an existing block definition
    Returns:
      A list of block definition names
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    containers = idef.GetContainers()
    rc = []
    for item in containers:
        if not item.IsDeleted: rc.append(item.Name)
    return rc


def BlockCount():
    "Returns the number of block definitions in the document"
    return scriptcontext.doc.InstanceDefinitions.ActiveCount


def BlockDescription(block_name, description=None):
    """Returns or sets the description of a block definition
    Parameters:
      block_name = the name of an existing block definition
      description[opt] = The new description.
    Returns:
      if description is not specified, the current description
      if description is specified, the previous description
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    rc = idef.Description
    if description: scriptcontext.doc.InstanceDefinitions.Modify( idef, idef.Name, description, True )
    return rc


def BlockInstanceCount(block_name,where_to_look=0):
    """Counts number of instances of the block in the document.
    Nested instances are not included in the count.
    Parameters:
      block_name = the name of an existing block definition
      where_to_look [opt] =
        0 = get top level references in active document.
        1 = get top level and nested references in active document.
        2 = check for references from other instance definitions
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    refs = idef.GetReferences(where_to_look)
    return len(refs)


def BlockInstanceInsertPoint(object_id):
    """Returns the insertion point of a block instance.
    Parameters:
      object_id = The identifier of an existing block insertion object
    Returns:
      list representing 3D point if successful
    """
    instance = __InstanceObjectFromId(object_id, True)
    xf = instance.InstanceXform
    pt = Rhino.Geometry.Point3d.Origin
    pt.Transform(xf)
    return pt


def BlockInstanceName(object_id):
    """Returns the block name of a block instance
    Parameters:
      object_id = The identifier of an existing block insertion object
    """
    instance = __InstanceObjectFromId(object_id, True)
    idef = instance.InstanceDefinition
    return idef.Name


def BlockInstances(block_name):
    """Returns the identifiers of the inserted instances of a block.
    Parameters:
      block_name = the name of an existing block definition
    Returns:
      list of guids identifying the instances of a block
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    instances = idef.GetReferences(0)
    return [item.Id for item in instances]


def BlockInstanceXform(object_id):
    """Returns the location of a block instance relative to the world coordinate
    system origin (0,0,0). The position is returned as a 4x4 transformation
    matrix
    Parameters:
      object_id = The identifier of an existing block insertion object  
    """
    instance = __InstanceObjectFromId(object_id, True)
    return instance.InstanceXform


def BlockNames( sort=False ):
    """Returns the names of all block definitions in the document
    Parameters:
      sort = return a sorted list
    """
    ideflist = scriptcontext.doc.InstanceDefinitions.GetList(True)
    rc = [item.Name for item in ideflist]
    if(sort): rc.sort()
    return rc


def BlockObjectCount(block_name):
    """Returns number of objects that make up a block definition
    Parameters:
      block_name = name of an existing block definition
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    return idef.ObjectCount


def BlockObjects(block_name):
    """Returns identifiers of the objects that make up a block definition
    Parameters:
      block_name = name of an existing block definition
    Returns:
      list of identifiers on success
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    rhobjs = idef.GetObjects()
    return [obj.Id for obj in rhobjs]


def BlockPath(block_name):
    """Returns path to the source of a linked or embedded block definition.
    A linked or embedded block definition is a block definition that was
    inserted from an external file.
    Parameters:
      block_name = name of an existing block definition
    Returns:
      path to the linked block on success
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    return idef.SourceArchive


def BlockStatus(block_name):
    """Returns the status of a linked block. See help for status codes"""
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: return -3
    return int(idef.ArchiveFileStatus)


def DeleteBlock(block_name):
    """Deletes a block definition and all of it's inserted instances.
    Parameters:
      block_name = name of an existing block definition
    Returns:
      True or False indicating success or failure  
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    rc = scriptcontext.doc.InstanceDefinitions.Delete(idef.Index, True, False)
    scriptcontext.doc.Views.Redraw()
    return rc


def ExplodeBlockInstance(object_id):
    """Explodes a block instance into it's geometric components. The
    exploded objects are added to the document
    Parameters:
      object_id = The identifier of an existing block insertion object  
    Returns:
      identifiers for the newly exploded objects on success
    """
    instance = __InstanceObjectFromId(object_id, True)
    rc = scriptcontext.doc.Objects.AddExplodedInstancePieces(instance)
    if rc:
        scriptcontext.doc.Objects.Delete(instance, True)
        scriptcontext.doc.Views.Redraw()
        return rc


def InsertBlock( block_name, insertion_point, scale=(1,1,1), angle_degrees=0, rotation_normal=(0,0,1) ):
    """Inserts a block whose definition already exists in the document
    Parameters:
      block_name = name of an existing block definition
      insertion_point = insertion point for the block
      scale [opt] = x,y,z scale factors
      angle_degrees [opt] = rotation angle in degrees
      rotation_normal [opt] = the axis of rotation.
    Returns:
      id for the block that was added to the doc
    """
    insertion_point = rhutil.coerce3dpoint(insertion_point, True)
    rotation_normal = rhutil.coerce3dvector(rotation_normal, True)
    angle_radians = math.radians(angle_degrees)
    trans = Rhino.Geometry.Transform
    move = trans.Translation(insertion_point[0],insertion_point[1],insertion_point[2])
    scale = trans.Scale(Rhino.Geometry.Plane.WorldXY, scale[0], scale[1], scale[2])
    rotate = trans.Rotation(angle_radians, rotation_normal, Rhino.Geometry.Point3d.Origin)
    xform = move * scale * rotate
    return InsertBlock2( block_name, xform )


def InsertBlock2(block_name, xform):
    """Inserts a block whose definition already exists in the document
    Parameters:
      block_name = name of an existing block definition
      xform = 4x4 transformation matrix to apply
    Returns:
      id for the block that was added to the doc on success
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    xform = rhutil.coercexform(xform, True)
    id = scriptcontext.doc.Objects.AddInstanceObject(idef.Index, xform )
    if id!=System.Guid.Empty:
        scriptcontext.doc.Views.Redraw()
        return id


def IsBlock(block_name):
    """Verifies the existence of a block definition in the document.
    Parameters:
      block_name = name of an existing block definition
    Returns:
      True or False
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    return (idef is not None)


def IsBlockEmbedded(block_name):
    """Verifies a block definition is embedded, or linked, from an external file.
    Parameters:
      block_name = name of an existing block definition
    Returns:
      True or False
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    ut = Rhino.DocObjects.InstanceDefinitionUpdateType
    return (idef.UpdateType==ut.Embedded or idef.UpdateType==ut.LinkedAndEmbedded)


def IsBlockInstance(object_id):
    """Verifies an object is a block instance
    Parameters:
      object_id = The identifier of an existing block insertion object
    Returns:
      True or False
    """
    return  __InstanceObjectFromId(object_id, False) is not None


def IsBlockInUse(block_name, where_to_look=0):
    """Verifies that a block definition is being used by an inserted instance
    Parameters:
      block_name = name of an existing block definition
      where_to_look [opt] = One of the following values
           0 = Check for top level references in active document
           1 = Check for top level and nested references in active document
           2 = Check for references in other instance definitions
    Returns:
      True or False
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    return idef.InUse(where_to_look)


def IsBlockReference(block_name):
    """Verifies that a block definition is from a reference file.
    Parameters:
      block_name = name of an existing block definition
    Returns:
      True or False
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    return idef.IsReference


def RenameBlock( block_name, new_name ):
    """Renames an existing block definition
    Parameters:
      block_name = name of an existing block definition
      new_name = name to change to
    Returns:
      True or False indicating success or failure
    """
    idef = scriptcontext.doc.InstanceDefinitions.Find(block_name, True)
    if not idef: raise ValueError("%s does not exist in InstanceDefinitionsTable"%block_name)
    description = idef.Description
    rc = scriptcontext.doc.InstanceDefinitions.Modify(idef, new_name, description, False)
    return rc

########NEW FILE########
__FILENAME__ = curve
import scriptcontext
import utility as rhutil
import Rhino
import math
import System.Guid, System.Array, System.Enum

def AddArc(plane, radius, angle_degrees):
    """Adds an arc curve to the document
    Parameters:
      plane = plane on which the arc will lie. The origin of the plane will be
        the center point of the arc. x-axis of the plane defines the 0 angle
        direction.
      radius = radius of the arc
      angle_degrees = interval of arc
    Returns:
      id of the new curve object
    """
    plane = rhutil.coerceplane(plane, True)
    radians = math.radians(angle_degrees)
    arc = Rhino.Geometry.Arc(plane, radius, radians)
    rc = scriptcontext.doc.Objects.AddArc(arc)
    if rc==System.Guid.Empty: raise Exception("Unable to add arc to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddArc3Pt(start, end, point_on_arc):
    """Adds a 3-point arc curve to the document
    Parameters:
      start, end = endpoints of the arc
      point_on_arc = a point on the arc
    Returns:
      id of the new curve object
    """
    start = rhutil.coerce3dpoint(start, True)
    end = rhutil.coerce3dpoint(end, True)
    pton = rhutil.coerce3dpoint(point_on_arc, True)
    arc = Rhino.Geometry.Arc(start, pton, end)
    rc = scriptcontext.doc.Objects.AddArc(arc)
    if rc==System.Guid.Empty: raise Exception("Unable to add arc to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddArcPtTanPt(start, direction, end):
    """Adds an arc curve, created from a start point, a start direction, and an
    end point, to the document
    Returns:
      id of the new curve object
    """
    start = rhutil.coerce3dpoint(start, True)
    direction = rhutil.coerce3dvector(direction, True)
    end = rhutil.coerce3dpoint(end, True)
    arc = Rhino.Geometry.Arc(start, direction, end)
    rc = scriptcontext.doc.Objects.AddArc(arc)
    if rc==System.Guid.Empty: raise Exception("Unable to add arc to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddBlendCurve(curves, parameters, reverses, continuities):
    """Makes a curve blend between two curves
    Parameters:
      curves = two curves
      parameters = two curve parameters defining the blend end points
      reverses = two boolean values specifying to use the natural or opposite direction of the curve
      continuities = two numbers specifying continuity at end points
        0 = position, 1 = tangency, 2 = curvature
    Returns:
      identifier of new curve on success
    """
    crv0 = rhutil.coercecurve(curves[0], -1, True)
    crv1 = rhutil.coercecurve(curves[1], -1, True)
    c0 = System.Enum.ToObject(Rhino.Geometry.BlendContinuity, continuities[0])
    c1 = System.Enum.ToObject(Rhino.Geometry.BlendContinuity, continuities[1])
    curve = Rhino.Geometry.Curve.CreateBlendCurve(crv0, parameters[0], reverses[0], c0, crv1, parameters[1], reverses[1], c1)
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddCircle(plane_or_center, radius):
    """Adds a circle curve to the document
    Parameters:
      plane_or_center = plane on which the circle will lie. If a point is
        passed, this will be the center of the circle on the active
        construction plane
      radius = the radius of the circle
    Returns:
      id of the new curve object
    """
    rc = None
    plane = rhutil.coerceplane(plane_or_center, False)
    if plane:
        circle = Rhino.Geometry.Circle(plane, radius)
        rc = scriptcontext.doc.Objects.AddCircle(circle)
    else:
        center = rhutil.coerce3dpoint(plane_or_center, True)
        view = scriptcontext.doc.Views.ActiveView
        plane = view.ActiveViewport.ConstructionPlane()
        plane.Origin = center
        circle = Rhino.Geometry.Circle(plane, radius)
        rc = scriptcontext.doc.Objects.AddCircle(circle)
    if rc==System.Guid.Empty: raise Exception("Unable to add circle to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddCircle3Pt(first, second, third):
    """Adds a 3-point circle curve to the document
    Parameters:
      first, second, third = points on the circle
    Returns:
      id of the new curve object
    """
    start = rhutil.coerce3dpoint(first, True)
    end = rhutil.coerce3dpoint(second, True)
    third = rhutil.coerce3dpoint(third, True)
    circle = Rhino.Geometry.Circle(start, end, third)
    rc = scriptcontext.doc.Objects.AddCircle(circle)
    if rc==System.Guid.Empty: raise Exception("Unable to add circle to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddCurve(points, degree=3):
    """Adds a control points curve object to the document
    Parameters:
      points = a list of points
      degree[opt] = degree of the curve
    Returns:
      id of the new curve object
    """
    points = rhutil.coerce3dpointlist(points, True)
    curve = Rhino.Geometry.Curve.CreateControlPointCurve(points, degree)
    if not curve: raise Exception("unable to create control point curve from given points")
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddEllipse(plane, radiusX, radiusY):
    """Adds an elliptical curve to the document
    Parameters:
      plane = the plane on which the ellipse will lie. The origin of
              the plane will be the center of the ellipse
      radiusX, radiusY = radius in the X and Y axis directions
    Returns:
      id of the new curve object if successful
    """
    plane = rhutil.coerceplane(plane, True)
    ellipse = Rhino.Geometry.Ellipse(plane, radiusX, radiusY)
    rc = scriptcontext.doc.Objects.AddEllipse(ellipse)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddEllipse3Pt(center, second, third):
    """Adds a 3-point elliptical curve to the document
    Parameters:
      center = center point of the ellipse
      second = end point of the x axis
      third  = end point of the y axis
    Returns:
      id of the new curve object if successful
    """
    center = rhutil.coerce3dpoint(center, True)
    second = rhutil.coerce3dpoint(second, True)
    third = rhutil.coerce3dpoint(third, True)
    ellipse = Rhino.Geometry.Ellipse(center, second, third)
    rc = scriptcontext.doc.Objects.AddEllipse(ellipse)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddFilletCurve(curve0id, curve1id, radius=1.0, base_point0=None, base_point1=None):
    """Adds a fillet curve between two curve objects
    Parameters:
      curve0id = identifier of the first curve object
      curve1id = identifier of the second curve object
      radius [opt] = fillet radius
      base_point0 [opt] = base point of the first curve. If omitted,
                          starting point of the curve is used
      base_point1 [opt] = base point of the second curve. If omitted,
                          starting point of the curve is used
    Returns:
      id of the new curve object if successful
    """
    if base_point0: base_point0 = rhutil.coerce3dpoint(base_point0, True)
    else: base_point0 = Rhino.Geometry.Point3d.Unset
    if base_point1: base_point1 = rhutil.coerce3dpoint(base_point1, True)
    else: base_point1 = Rhino.Geometry.Point3d.Unset
    curve0 = rhutil.coercecurve(curve0id, -1, True)
    curve1 = rhutil.coercecurve(curve1id, -1, True)
    crv0_t = 0.0
    if base_point0==Rhino.Geometry.Point3d.Unset:
        crv0_t = curve0.Domain.Min
    else:
        rc, t = curve0.ClosestPoint(base_point0, 0.0)
        if not rc: raise Exception("ClosestPoint failed")
        crv0_t = t
    crv1_t = 0.0
    if base_point1==Rhino.Geometry.Point3d.Unset:
        crv1_t = curve1.Domain.Min
    else:
        rc, t = curve1.ClosestPoint(base_point1, 0.0)
        if not rc: raise Exception("ClosestPoint failed")
        crv1_t = t
    arc = Rhino.Geometry.Curve.CreateFillet(curve0, curve1, radius, crv0_t, crv1_t)
    rc = scriptcontext.doc.Objects.AddArc(arc)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddInterpCrvOnSrf(surface_id, points):
    """Adds an interpolated curve object that lies on a specified
    surface.  Note, this function will not create periodic curves,
    but it will create closed curves.
    Parameters:
      surface_id = identifier of the surface to create the curve on
      points = list of 3D points that lie on the specified surface.
               The list must contain at least 2 points
    Returns:
      id of the new curve object if successful
    """
    surface = rhutil.coercesurface(surface_id, True)
    points = rhutil.coerce3dpointlist(points, True)
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    curve = surface.InterpolatedCurveOnSurface(points, tolerance)
    if not curve: raise Exception("unable to create InterpolatedCurveOnSurface")
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddInterpCrvOnSrfUV(surface_id, points):
    """Adds an interpolated curve object based on surface parameters,
    that lies on a specified surface. Note, this function will not
    create periodic curves, but it will create closed curves.
    Parameters:
      surface_id = identifier of the surface to create the curve on
      points = list of 2D surface parameters. The list must contain
               at least 2 sets of parameters
    Returns:
      id of the new curve object if successful
    """
    surface = rhutil.coercesurface(surface_id, True)
    points = rhutil.coerce2dpointlist(points)
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    curve = surface.InterpolatedCurveOnSurfaceUV(points, tolerance)
    if not curve: raise Exception("unable to create InterpolatedCurveOnSurfaceUV")
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddInterpCurve(points, degree=3, knotstyle=0, start_tangent=None, end_tangent=None):
    """Adds an interpolated curve object to the document. Options exist to make
    a periodic curve or to specify the tangent at the endpoints. The resulting
    curve is a non-rational NURBS curve of the specified degree.
    Parameters:
      points = list containing 3D points to interpolate. For periodic curves,
          if the final point is a duplicate of the initial point, it is
          ignored. The number of control points must be >= (degree+1).
      degree[opt] = The degree of the curve (must be >=1).
          Periodic curves must have a degree >= 2. For knotstyle = 1 or 2,
          the degree must be 3. For knotstyle = 4 or 5, the degree must be odd
      knotstyle[opt]
          0 Uniform knots.  Parameter spacing between consecutive knots is 1.0.
          1 Chord length spacing.  Requires degree = 3 with arrCV1 and arrCVn1 specified.
          2 Sqrt (chord length).  Requires degree = 3 with arrCV1 and arrCVn1 specified.
          3 Periodic with uniform spacing.
          4 Periodic with chord length spacing.  Requires an odd degree value.
          5 Periodic with sqrt (chord length) spacing.  Requires an odd degree value.
      start_tangent [opt] = 3d vector that specifies a tangency condition at the
          beginning of the curve. If the curve is periodic, this argument must be omitted.
      end_tangent [opt] = 3d vector that specifies a tangency condition at the
          end of the curve. If the curve is periodic, this argument must be omitted.
    Returns:
      id of the new curve object if successful
    """
    points = rhutil.coerce3dpointlist(points, True)
    if not start_tangent: start_tangent = Rhino.Geometry.Vector3d.Unset
    start_tangent = rhutil.coerce3dvector(start_tangent, True)
    if not end_tangent: end_tangent = Rhino.Geometry.Vector3d.Unset
    end_tangent = rhutil.coerce3dvector(end_tangent, True)
    knotstyle = System.Enum.ToObject(Rhino.Geometry.CurveKnotStyle, knotstyle)
    curve = Rhino.Geometry.Curve.CreateInterpolatedCurve(points, degree, knotstyle, start_tangent, end_tangent)
    if not curve: raise Exception("unable to CreateInterpolatedCurve")
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddLine(start, end):
    """Adds a line curve to the current model.
    Parameters:
      start, end = end points of the line
    Returns:
      id of the new curve object
    """
    start = rhutil.coerce3dpoint(start, True)
    end = rhutil.coerce3dpoint(end, True)
    rc = scriptcontext.doc.Objects.AddLine(start, end)
    if rc==System.Guid.Empty: raise Exception("Unable to add line to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddNurbsCurve(points, knots, degree, weights=None):
    """Adds a NURBS curve object to the document
    Parameters:
      points = list containing 3D control points
      knots = Knot values for the curve. The number of elements in knots must
          equal the number of elements in points plus degree minus 1
      degree = degree of the curve. must be greater than of equal to 1
      weights[opt] = weight values for the curve. Number of elements should
          equal the number of elements in points. Values must be greater than 0
    """
    points = rhutil.coerce3dpointlist(points, True)
    cvcount = len(points)
    knotcount = cvcount + degree - 1
    if len(knots)!=knotcount:
        raise Exception("Number of elements in knots must equal the number of elements in points plus degree minus 1")
    if weights and len(weights)!=cvcount:
        raise Exception("Number of elements in weights should equal the number of elements in points")
    rational = (weights!=None)
    
    nc = Rhino.Geometry.NurbsCurve(3,rational,degree+1,cvcount)
    for i in xrange(cvcount):
        cp = Rhino.Geometry.ControlPoint()
        cp.Location = points[i]
        if weights: cp.Weight = weights[i]
        nc.Points[i] = cp
    for i in xrange(knotcount): nc.Knots[i] = knots[i]
    rc = scriptcontext.doc.Objects.AddCurve(nc)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPolyline(points, replace_id=None):
    """Adds a polyline curve to the current model
    Parameters:
      points = list of 3D points. Duplicate, consecutive points found in
               the array will be removed. The array must contain at least
               two points. If the array contains less than four points,
               then the first point and the last point must be different.
      replace_id[opt] = If set to the id of an existing object, the object
               will be replaced by this polyline
    Returns:
      id of the new curve object if successful
    """
    points = rhutil.coerce3dpointlist(points, True)
    if replace_id: replace_id = rhutil.coerceguid(replace_id, True)
    rc = System.Guid.Empty
    if replace_id:
        pl = Rhino.Geometry.Polyline(points)
        if scriptcontext.doc.Objects.Replace(replace_id, pl):
            rc = replace_id
    else:
        rc = scriptcontext.doc.Objects.AddPolyline(points)
    if rc==System.Guid.Empty: raise Exception("Unable to add polyline to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddRectangle(plane, width, height):
    """Add a rectangular curve to the document
    Paramters:
      plane = plane on which the rectangle will lie
      width, height = width and height of rectangle as measured along the plane's
        x and y axes
    Returns:
      id of new rectangle
    """
    plane = rhutil.coerceplane(plane, True)
    rect = Rhino.Geometry.Rectangle3d(plane, width, height)
    poly = rect.ToPolyline()
    rc = scriptcontext.doc.Objects.AddPolyline(poly)
    if rc==System.Guid.Empty: raise Exception("Unable to add polyline to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSpiral(point0, point1, pitch, turns, radius0, radius1=None):
    """Adds a spiral or helical curve to the document
    Parameters:
      point0 = helix axis start point or center of spiral
      point1 = helix axis end point or point normal on spiral plane
      pitch = distance between turns. If 0, then a spiral. If > 0 then the
              distance between helix "threads"
      turns = number of turns
      radius0, radius1 = starting and ending radius
    Returns:
      id of new curve on success
    """
    if radius1 is None: radius1 = radius0
    point0 = rhutil.coerce3dpoint(point0, True)
    point1 = rhutil.coerce3dpoint(point1, True)
    dir = point1 - point0
    plane = Rhino.Geometry.Plane(point0, dir)
    point2 = point0 + plane.XAxis
    curve = Rhino.Geometry.NurbsCurve.CreateSpiral(point0, dir, point2, pitch, turns, radius0, radius1)
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSubCrv(curve_id, param0, param1):
    """Add a curve object based on a portion, or interval of an existing curve
    object. Similar in operation to Rhino's SubCrv command
    Parameters:
      curve_id = identifier of a closed planar curve object
      param0, param1 = first and second parameters on the source curve
    Returns:
      id of the new curve object if successful
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    trimcurve = curve.Trim(param0, param1)
    if not trimcurve: raise Exception("unable to trim curve")
    rc = scriptcontext.doc.Objects.AddCurve(trimcurve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def ArcAngle(curve_id, segment_index=-1):
    """Returns the angle of an arc curve object.
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if 
      curve_id identifies a polycurve
    Returns:
      The angle in degrees if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, arc = curve.TryGetArc( Rhino.RhinoMath.ZeroTolerance )
    if not rc: raise Exception("curve is not arc")
    return arc.AngleDegrees


def ArcCenterPoint(curve_id, segment_index=-1):
    """Returns the center point of an arc curve object
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if
      curve_id identifies a polycurve
    Returns:
      The 3D center point of the arc if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, arc = curve.TryGetArc( Rhino.RhinoMath.ZeroTolerance )
    if not rc: raise Exception("curve is not arc")
    return arc.Center


def ArcMidPoint(curve_id, segment_index=-1):
    """Returns the mid point of an arc curve object
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if
      curve_id identifies a polycurve
    Returns:
      The 3D mid point of the arc if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, arc = curve.TryGetArc( Rhino.RhinoMath.ZeroTolerance )
    if not rc: raise Exception("curve is not arc")
    return arc.MidPoint


def ArcRadius(curve_id, segment_index=-1):
    """Returns the radius of an arc curve object
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if 
      curve_id identifies a polycurve
    Returns:
      The radius of the arc if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, arc = curve.TryGetArc( Rhino.RhinoMath.ZeroTolerance )
    if not rc: raise Exception("curve is not arc")
    return arc.Radius


def CircleCenterPoint(curve_id, segment_index=-1, return_plane=False):
    """Returns the center point of a circle curve object
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if
      return_plane [opt] = if True, the circle's plane is returned
      curve_id identifies a polycurve
    Returns:
      The 3D center point of the circle if successful.
      The plane of the circle if return_plane is True
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, circle = curve.TryGetCircle(Rhino.RhinoMath.ZeroTolerance)
    if not rc: raise Exception("curve is not circle")
    if return_plane: return circle.Plane
    return circle.Center


def CircleCircumference(curve_id, segment_index=-1):
    """Returns the circumference of a circle curve object
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if
      curve_id identifies a polycurve
    Returns:
      The circumference of the circle if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, circle = curve.TryGetCircle( Rhino.RhinoMath.ZeroTolerance )
    if not rc: raise Exception("curve is not circle")
    return circle.Circumference

def CircleRadius(curve_id, segment_index=-1):
    """Returns the radius of a circle curve object
    Parameters:
      curve_id = identifier of a curve object
      segment_index [opt] = identifies the curve segment if
      curve_id identifies a polycurve
    Returns:
      The radius of the circle if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, circle = curve.TryGetCircle( Rhino.RhinoMath.ZeroTolerance )
    if not rc: raise Exception("curve is not circle")
    return circle.Radius

def CloseCurve(curve_id, tolerance=-1.0):
    """Closes an open curve object by making adjustments to the end points so
    they meet at a point
    Parameters:
      curve_id = identifier of a curve object
      tolerance[opt] = maximum allowable distance between start and end
          point. If omitted, the current absolute tolerance is used
    Returns:
      id of the new curve object if successful
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if curve.IsClosed: return curve_id
    if tolerance<0.0: tolerance = Rhino.RhinoMath.ZeroTolerance
    if not curve.MakeClosed(tolerance): return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddCurve(curve)
    if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
    scriptcontext.doc.Views.Redraw()
    return rc

def ClosedCurveOrientation(curve_id, direction=(0,0,1)):
    """Determine the orientation (counter-clockwise or clockwise) of a closed,
    planar curve
    Parameters:
      curve_id = identifier of a curve object
      direction[opt] = 3d vector that identifies up, or Z axs, direction of
          the plane to test against
    Returns:
      1 if the curve's orientation is clockwise
      -1 if the curve's orientation is counter-clockwise
      0 if unable to compute the curve's orientation
    """
    curve = rhutil.coercecurve(curve_id, -1 ,True)
    direction = rhutil.coerce3dvector(direction, True)
    if not curve.IsClosed: return 0
    orientation = curve.ClosedCurveOrientation(direction)
    return int(orientation)


def ConvertCurveToPolyline(curve_id, angle_tolerance=5.0, tolerance=0.01, delete_input=False, min_edge_length=0, max_edge_length=0):
    """Convert curve to a polyline curve
    Parameters:
      curve_id = identifier of a curve object
      angle_tolerance [opt] = The maximum angle between curve tangents at line
        endpoints. If omitted, the angle tolerance is set to 5.0.
      tolerance[opt] = The distance tolerance at segment midpoints. If omitted,
        the tolerance is set to 0.01.
      delete_input[opt] = Delete the curve object specified by curve_id. If
        omitted, curve_id will not be deleted.
      min_edge_length[opt] = Minimum segment length
      max_edge_length[opt] = Maximum segment length
    Returns:
      The new curve if successful.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if angle_tolerance<=0: angle_tolerance = 5.0
    angle_tolerance = Rhino.RhinoMath.ToRadians(angle_tolerance)
    if tolerance<=0.0: tolerance = 0.01;
    polyline_curve = curve.ToPolyline( 0, 0, angle_tolerance, 0.0, 0.0, tolerance, min_edge_length, max_edge_length, True)
    if not polyline_curve: return scriptcontext.errorhandler()
    id = System.Guid.Empty
    if delete_input:
        if scriptcontext.doc.Objects.Replace( curve_id, polyline_curve): id = curve_id
    else:
        id = scriptcontext.doc.Objects.AddCurve( polyline_curve )
    if System.Guid.Empty==id: return scriptcontext.errorhandler()
    return id

  
def CurveArcLengthPoint(curve_id, length, from_start=True):
    """Returns the point on the curve that is a specified arc length
    from the start of the curve.
    Parameters:
      curve_id = identifier of a curve object
      length = The arc length from the start of the curve to evaluate.
      from_start[opt] = If not specified or True, then the arc length point is
          calculated from the start of the curve. If False, the arc length
          point is calculated from the end of the curve.
    Returns:
      Point3d if successful
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    curve_length = curve.GetLength()
    if curve_length>=length:
        s = 0.0
        if length==0.0: s = 0.0
        elif length==curve_length: s = 1.0
        else: s = length / curve_length
        dupe = curve.Duplicate()
        if dupe:
            if from_start==False: dupe.Reverse()
            rc, t = dupe.NormalizedLengthParameter(s)
            if rc: return dupe.PointAt(t)
            dupe.Dispose()


def CurveArea(curve_id):
    """Returns area of closed planar curves. The results are based on the
    current drawing units.
    Parameters:
      curve_id = The identifier of a closed, planar curve object.
    Returns:
      List of area information. The list will contain the following information:
        Element  Description
        0        The area. If more than one curve was specified, the
                 value will be the cumulative area.
        1        The absolute (+/-) error bound for the area.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    mp = Rhino.Geometry.AreaMassProperties.Compute(curve, tol)
    return mp.Area, mp.AreaError


def CurveAreaCentroid(curve_id):
    """Returns area centroid of closed, planar curves. The results are based
    on the current drawing units.
    Parameters:
      curve_id = The identifier of a closed, planar curve object.
    Returns:
      Tuple of area centroid information containing the following information:
        Element  Description
        0        The 3d centroid point. If more than one curve was specified,
                 the value will be the cumulative area.
        1        A 3d vector with the absolute (+/-) error bound for the area
                 centroid.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    mp = Rhino.Geometry.AreaMassProperties.Compute(curve, tol)
    return mp.Centroid, mp.CentroidError


def CurveArrows(curve_id, arrow_style=None):
    """Enables or disables a curve object's annotation arrows
    Parameters:
      curve_id = identifier of a curve
      arrow_style[opt] = the style of annotation arrow to be displayed
        0 = no arrows
        1 = display arrow at start of curve
        2 = display arrow at end of curve
        3 = display arrow at both start and end of curve
      Returns:
        if arrow_style is not specified, the current annotation arrow style
        if arrow_style is specified, the previos arrow style
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    rhobj = rhutil.coercerhinoobject(curve_id, True, True)
    attr = rhobj.Attributes
    rc = attr.ObjectDecoration
    if arrow_style is not None:
        if arrow_style==0:
            attr.ObjectDecoration = Rhino.DocObjects.ObjectDecoration.None
        elif arrow_style==1:
            attr.ObjectDecoration = Rhino.DocObjects.ObjectDecoration.StartArrowhead
        elif arrow_style==2:
            attr.ObjectDecoration = Rhino.DocObjects.ObjectDecoration.EndArrowhead
        elif arrow_style==3:
            attr.ObjectDecoration = Rhino.DocObjects.ObjectDecoration.BothArrowhead
        id = rhutil.coerceguid(curve_id, True)
        scriptcontext.doc.Objects.ModifyAttributes(id, attr, True)
        scriptcontext.doc.Views.Redraw()
    if rc==Rhino.DocObjects.ObjectDecoration.None: return 0
    if rc==Rhino.DocObjects.ObjectDecoration.StartArrowhead: return 1
    if rc==Rhino.DocObjects.ObjectDecoration.EndArrowhead: return 2
    if rc==Rhino.DocObjects.ObjectDecoration.BothArrowhead: return 3


def CurveBooleanDifference(curve_id_0, curve_id_1):
    """Calculates the difference between two closed, planar curves and
    adds the results to the document. Note, curves must be coplanar.
    Parameters:
      curve_id_0 = identifier of the first curve object.
      curve_id_1 = identifier of the second curve object.
    Returns:
      The identifiers of the new objects if successful, None on error.
    """
    curve0 = rhutil.coercecurve(curve_id_0, -1, True)
    curve1 = rhutil.coercecurve(curve_id_1, -1, True)
    out_curves = Rhino.Geometry.Curve.CreateBooleanDifference(curve0, curve1)
    curves = []
    if out_curves:
        for curve in out_curves:
            if curve and curve.IsValid:
                rc = scriptcontext.doc.Objects.AddCurve(curve)
                curve.Dispose()
                if rc==System.Guid.Empty: raise Exception("unable to add curve to document")
                curves.append(rc)
    scriptcontext.doc.Views.Redraw()
    return curves


def CurveBooleanIntersection(curve_id_0, curve_id_1):
    """Calculates the intersection of two closed, planar curves and adds
    the results to the document. Note, curves must be coplanar.
    Parameters:
      curve_id_0 = identifier of the first curve object.
      curve_id_1 = identifier of the second curve object.
    Returns:
      The identifiers of the new objects.
    """
    curve0 = rhutil.coercecurve(curve_id_0, -1, True)
    curve1 = rhutil.coercecurve(curve_id_1, -1, True)
    out_curves = Rhino.Geometry.Curve.CreateBooleanIntersection(curve0, curve1)
    curves = []
    if out_curves:
        for curve in out_curves:
            if curve and curve.IsValid:
                rc = scriptcontext.doc.Objects.AddCurve(curve)
                curve.Dispose()
                if rc==System.Guid.Empty: raise Exception("unable to add curve to document")
                curves.append(rc)
    scriptcontext.doc.Views.Redraw()
    return curves


def CurveBooleanUnion(curve_id):
    """Calculate the union of two or more closed, planar curves and
    add the results to the document. Note, curves must be coplanar.
    Parameters:
      curve_id = list of two or more close planar curves identifiers
    Returns:
      The identifiers of the new objects.
    """
    in_curves = [rhutil.coercecurve(id,-1,True) for id in curve_id]
    if len(in_curves)<2: raise ValueException("curve_id must have at least 2 curves")
    out_curves = Rhino.Geometry.Curve.CreateBooleanUnion(in_curves)
    curves = []
    if out_curves:
        for curve in out_curves:
            if curve and curve.IsValid:
                rc = scriptcontext.doc.Objects.AddCurve(curve)
                curve.Dispose()
                if rc==System.Guid.Empty: raise Exception("unable to add curve to document")
                curves.append(rc)
        scriptcontext.doc.Views.Redraw()
    return curves


def CurveBrepIntersect(curve_id, brep_id, tolerance=None):
    """Intersects a curve object with a brep object. Note, unlike the
    CurveSurfaceIntersection function, this function works on trimmed surfaces.
    Parameters:
      curve_id = identifier of a curve object
      brep_id = identifier of a brep object
      tolerance [opt] = distance tolerance at segment midpoints.
                        If omitted, the current absolute tolerance is used.
    Returns:
      List of identifiers for the newly created intersection curve and
      point objects if successful. None on error.            
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    brep = rhutil.coercebrep(brep_id, True)
    if tolerance is None or tolerance<0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    rc, out_curves, out_points = Rhino.Geometry.Intersect.Intersection.CurveBrep(curve, brep, tolerance)
    if not rc: return scriptcontext.errorhandler()
    
    curves = []
    points = []
    for curve in out_curves:
        if curve and curve.IsValid:
            rc = scriptcontext.doc.Objects.AddCurve(curve)
            curve.Dispose()
            if rc==System.Guid.Empty: raise Exception("unable to add curve to document")
            curves.append(rc)
    for point in out_points:
        if point and point.IsValid:
            rc = scriptcontext.doc.Objects.AddPoint(point)
            points.append(rc)
    if not curves and not points: return None
    scriptcontext.doc.Views.Redraw()
    return curves, points


def CurveClosestObject(curve_id, object_ids):
    """Returns the 3D point locations on two objects where they are closest to
    each other. Note, this function provides similar functionality to that of
    Rhino's ClosestPt command.
    Parameters:
      curve_id = identifier of the curve object to test
      object_ids = list of identifiers of point cloud, curve, surface, or
        polysurface to test against
    Returns:
      Tuple containing the results of the closest point calculation.
      The elements are as follows:
        0    The identifier of the closest object.
        1    The 3-D point that is closest to the closest object. 
        2    The 3-D point that is closest to the test curve.
    """
    curve = rhutil.coercecurve(curve_id,-1,True)
    geometry = []
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    for object_id in object_ids:
        rhobj = rhutil.coercerhinoobject(object_id, True, True)
        geometry.append( rhobj.Geometry )
    if not geometry: raise ValueError("object_ids must contain at least one item")
    success, curve_point, geom_point, which_geom = curve.ClosestPoints(geometry, 0.0)
    if success: return object_ids[which_geom], geom_point, curve_point

    
def CurveClosestPoint(curve_id, test_point, segment_index=-1 ):
    """Returns parameter of the point on a curve that is closest to a test point.
    Parameters:
      curve_id = identifier of a curve object
      point = sampling point
      segment_index [opt] = curve segment if curve_id identifies a polycurve
    Returns:
      The parameter of the closest point on the curve
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    point = rhutil.coerce3dpoint(test_point, True)
    rc, t = curve.ClosestPoint(point, 0.0)
    if not rc: raise Exception("ClosestPoint failed")
    return t


def CurveContourPoints(curve_id, start_point, end_point, interval=None):
    """Returns the 3D point locations calculated by contouring a curve object.
    Parameters:
      curve_id = identifier of a curve object.
      start_point = 3D starting point of a center line.
      end_point = 3D ending point of a center line.
      interval [opt] = The distance between contour curves. If omitted, 
      the interval will be equal to the diagonal distance of the object's
      bounding box divided by 50.
    Returns:
      A list of 3D points, one for each contour
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    start_point = rhutil.coerce3dpoint(start_point, True)
    end_point = rhutil.coerce3dpoint(end_point, True)
    if start_point.DistanceTo(end_point)<Rhino.RhinoMath.ZeroTolerance:
        raise Exception("start and end point are too close to define a line")
    if not interval:
        bbox = curve.GetBoundingBox(True)
        diagonal = bbox.Max - bbox.Min
        interval = diagonal.Length / 50.0
    rc = curve.DivideAsContour( start_point, end_point, interval )
    return list(rc)


def CurveCurvature(curve_id, parameter):
    """Returns the curvature of a curve at a parameter. See the Rhino help for
    details on curve curvature
    Parameters:
      curve_id = identifier of the curve
      parameter = parameter to evaluate
    Returns:
      Tuple of curvature information on success
        element 0 = point at specified parameter
        element 1 = tangent vector
        element 2 = center of radius of curvature
        element 3 = radius of curvature
        element 4 = curvature vector
      None on failure
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    point = curve.PointAt(parameter)
    tangent = curve.TangentAt(parameter)
    if tangent.IsTiny(0): return scriptcontext.errorhandler()
    cv = curve.CurvatureAt(parameter)
    k = cv.Length
    if k<Rhino.RhinoMath.SqrtEpsilon: return scriptcontext.errorhandler()
    rv = cv / (k*k)
    circle = Rhino.Geometry.Circle(point, tangent, point + 2.0*rv)
    center = point + rv
    radius = circle.Radius
    return point, tangent, center, radius, cv


def CurveCurveIntersection(curveA, curveB=None, tolerance=-1):
    """Calculates intersection of two curve objects.
    Parameters:
      curveA = identifier of the first curve object.
      curveB = identifier of the second curve object. If omitted, then a
               self-intersection test will be performed on curveA.
      tolerance [opt] = absolute tolerance in drawing units. If omitted,
                        the document's current absolute tolerance is used.
    Returns:
      List of tuples of intersection information if successful.
      The list will contain one or more of the following elements:
        Element Type     Description
        [n][0]  Number   The intersection event type, either Point (1) or Overlap (2).
        [n][1]  Point3d  If the event type is Point (1), then the intersection point 
                         on the first curve. If the event type is Overlap (2), then
                         intersection start point on the first curve.
        [n][2]  Point3d  If the event type is Point (1), then the intersection point
                         on the first curve. If the event type is Overlap (2), then
                         intersection end point on the first curve.
        [n][3]  Point3d  If the event type is Point (1), then the intersection point 
                         on the second curve. If the event type is Overlap (2), then
                         intersection start point on the second curve.
        [n][4]  Point3d  If the event type is Point (1), then the intersection point
                         on the second curve. If the event type is Overlap (2), then
                         intersection end point on the second curve.
        [n][5]  Number   If the event type is Point (1), then the first curve parameter.
                         If the event type is Overlap (2), then the start value of the
                         first curve parameter range.
        [n][6]  Number   If the event type is Point (1), then the first curve parameter.
                         If the event type is Overlap (2), then the end value of the
                         first curve parameter range.
        [n][7]  Number   If the event type is Point (1), then the second curve parameter.
                         If the event type is Overlap (2), then the start value of the
                         second curve parameter range.
        [n][8]  Number   If the event type is Point (1), then the second curve parameter.
                         If the event type is Overlap (2), then the end value of the 
                         second curve parameter range.
    """
    curveA = rhutil.coercecurve(curveA, -1, True)
    if curveB: curveB = rhutil.coercecurve(curveB, -1, True)
    if tolerance is None or tolerance<0.0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    if curveB:
        rc = Rhino.Geometry.Intersect.Intersection.CurveCurve(curveA, curveB, tolerance, 0.0)
    else:
        rc = Rhino.Geometry.Intersect.Intersection.CurveSelf(curveA, tolerance)
    if rc:
        events = []
        for i in xrange(rc.Count):
            event_type = 1
            if( rc[i].IsOverlap ): event_type = 2
            oa = rc[i].OverlapA
            ob = rc[i].OverlapB
            element = (event_type, rc[i].PointA, rc[i].PointA2, rc[i].PointB, rc[i].PointB2, oa[0], oa[1], ob[0], ob[1])
            events.append(element)
        return events


def CurveDegree(curve_id, segment_index=-1):
    """Returns the degree of a curve object.
    Parameters:
      curve_id = identifier of a curve object.
      segment_index [opt] = the curve segment if curve_id identifies a polycurve.
    Returns:
      The degree of the curve if successful. None on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.Degree


def CurveDeviation(curve_a, curve_b):
    """Returns the minimum and maximum deviation between two curve objects
    Parameters:
      curve_a, curve_b = identifiers of two curves
    Returns:
      tuple of deviation information on success
        element 0 = curve_a parameter at maximum overlap distance point
        element 1 = curve_b parameter at maximum overlap distance point
        element 2 = maximum overlap distance
        element 3 = curve_a parameter at minimum overlap distance point
        element 4 = curve_b parameter at minimum overlap distance point
        element 5 = minimum distance between curves
      None on error
    """
    curve_a = rhutil.coercecurve(curve_a, -1, True)
    curve_b = rhutil.coercecurve(curve_b, -1, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    rc = Rhino.Geometry.Curve.GetDistancesBetweenCurves(curve_a, curve_b, tol)
    if not rc[0]: return scriptcontext.errorhandler()
    maxa = rc[2]
    maxb = rc[3]
    maxd = rc[1]
    mina = rc[5]
    minb = rc[6]
    mind = rc[4]
    return maxa, maxb, maxd, mina, minb, mind


def CurveDim(curve_id, segment_index=-1):
    """Returns the dimension of a curve object
    Parameters:
      curve_id = identifier of a curve object.
      segment_index [opt] = the curve segment if curve_id identifies a polycurve.
    Returns:
      The dimension of the curve if successful. None on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.Dimension


def CurveDirectionsMatch(curve_id_0, curve_id_1):
    """Tests if two curve objects are generally in the same direction or if they
    would be more in the same direction if one of them were flipped. When testing
    curve directions, both curves must be either open or closed - you cannot test
    one open curve and one closed curve.
    Parameters:
      curve_id_0 = identifier of first curve object
      curve_id_1 = identifier of second curve object
    Returns:
      True if the curve directions match, otherwise False. 
    """
    curve0 = rhutil.coercecurve(curve_id_0, -1, True)
    curve1 = rhutil.coercecurve(curve_id_1, -1, True)
    return Rhino.Geometry.Curve.DoDirectionsMatch(curve0, curve1)


def CurveDiscontinuity(curve_id, style):   
    """Search for a derivatitive, tangent, or curvature discontinuity in
    a curve object.
    Parameters:
      curve_id = identifier of curve object
      style = The type of continuity to test for. The types of
          continuity are as follows:
          Value    Description
          1        C0 - Continuous function
          2        C1 - Continuous first derivative
          3        C2 - Continuous first and second derivative
          4        G1 - Continuous unit tangent
          5        G2 - Continuous unit tangent and curvature
    Returns:
      List 3D points where the curve is discontinuous
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    dom = curve.Domain
    t0 = dom.Min
    t1 = dom.Max
    points = []
    get_next = True
    while get_next:
        get_next, t = curve.GetNextDiscontinuity(System.Enum.ToObject(Rhino.Geometry.Continuity, style), t0, t1)
        if get_next:
            points.append(curve.PointAt(t))
            t0 = t # Advance to the next parameter
    return points


def CurveDomain(curve_id, segment_index=-1):
    """Returns the domain of a curve object.
    Parameters:
      curve_id = identifier of the curve object
      segment_index[opt] = the curve segment if curve_id identifies a polycurve.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    dom = curve.Domain
    return [dom.Min, dom.Max]


def CurveEditPoints(curve_id, return_parameters=False, segment_index=-1):
    """Returns the edit, or Greville, points of a curve object. 
    For each curve control point, there is a corresponding edit point.
    Parameters:
      curve_id = identifier of the curve object
      return_parameters[opt] = if True, return as a list of curve parameters.
        If False, return as a list of 3d points
      segment_index[opt] = the curve segment is curve_id identifies a polycurve
    Returns:
      curve parameters of 3d points on success
      None on error
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    nc = curve.ToNurbsCurve()
    if not nc: return scriptcontext.errorhandler()
    if return_parameters: return nc.GrevilleParameters()
    return nc.GrevillePoints()


def CurveEndPoint(curve_id, segment_index=-1):
    """Returns the end point of a curve object
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The 3-D end point of the curve if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.PointAtEnd


def CurveFilletPoints(curve_id_0, curve_id_1, radius=1.0, base_point_0=None, base_point_1=None, return_points=True):
    """Find points at which to cut a pair of curves so that a fillet of a
    specified radius fits. A fillet point is a pair of points (point0, point1)
    such that there is a circle of radius tangent to curve curve0 at point0 and
    tangent to curve curve1 at point1. Of all possible fillet points, this
    function returns the one which is the closest to the base point base_point_0,
    base_point_1. Distance from the base point is measured by the sum of arc
    lengths along the two curves. 
    Parameters:
      curve_id_0 = identifier of the first curve object.
      curve_id_1 = identifier of the second curve object.
      radius [opt] = The fillet radius. If omitted, a radius
                     of 1.0 is specified.
      base_point_0 [opt] = The base point on the first curve.
                     If omitted, the starting point of the curve is used.
      base_point_1 [opt] = The base point on the second curve. If omitted,
                     the starting point of the curve is used.
      return_points [opt] = If True (Default), then fillet points are
                     returned. Otherwise, a fillet curve is created and
                     it's identifier is returned.
    Returns:
      If return_points is True, then a list of point and vector values
      if successful. The list elements are as follows:
      
      0    A point on the first curve at which to cut (arrPoint0).
      1    A point on the second curve at which to cut (arrPoint1).
      2    The fillet plane's origin (3-D point). This point is also
           the center point of the fillet
      3    The fillet plane's X axis (3-D vector).
      4    The fillet plane's Y axis (3-D vector).
      5    The fillet plane's Z axis (3-D vector).
      
      If return_points is False, then the identifier of the fillet curve
      if successful.
      None if not successful, or on error.                  
    """
    curve0 = rhutil.coercecurve(curve_id_0, -1, True)
    curve1 = rhutil.coercecurve(curve_id_1, -1, True)
    t0_base = curve0.Domain.Min
    
    if base_point_0:
        rc = curve0.ClosestPoint(base_point_0, t0_base)
        if not rc[0]: return scriptcontext.errorhandler()
    
    t1_base = curve1.Domain.Min
    if base_point_1:
        rc = curve1.ClosestPoint(base_point_1, t1_base)
        if not rc[0]: return scriptcontext.errorhandler()

    r = radius if (radius and radius>0) else 1.0
    rc = Rhino.Geometry.Curve.GetFilletPoints(curve0, curve1, r, t0_base, t1_base)
    if rc[0]:
        point_0 = curve0.PointAt(rc[1])
        point_1 = curve1.PointAt(rc[2])
        return point_0, point_1, rc[3].Origin, rc[3].XAxis, rc[3].YAxis, rc[3].ZAxis
    return scriptcontext.errorhandler()


def CurveFrame(curve_id, parameter, segment_index=-1):
    """Returns the plane at a parameter of a curve. The plane is based on the
    tangent and curvature vectors at a parameter.
    Parameters:
      curve_id = identifier of the curve object.
      parameter = parameter to evaluate.
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The plane at the specified parameter if successful. 
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    domain = curve.Domain
    if not domain.IncludesParameter(parameter):
        tol = scriptcontext.doc.ModelAbsoluteTolerance
        if parameter>domain.Max and (parameter-domain.Max)<=tol:
            parameter = domain.Max
        elif parameter<domain.Min and (domain.Min-parameter)<=tol:
            parameter = domain.Min
        else:
            return scriptcontext.errorhandler()
    rc, frame = curve.FrameAt(parameter)
    if rc and frame.IsValid: return frame
    return scriptcontext.errorhandler()


def CurveKnotCount(curve_id, segment_index=-1):
    """Returns the knot count of a curve object.
    Parameters:
      curve_id = identifier of the curve object.
      segment_index [opt] = the curve segment if curve_id identifies a polycurve.
    Returns:
      The number of knots if successful.
      None if not successful or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    nc = curve.ToNurbsCurve()
    if not nc: return scriptcontext.errorhandler()
    return nc.Knots.Count


def CurveKnots(curve_id, segment_index=-1):
    """Returns the knots, or knot vector, of a curve object
    Parameters:
      curve_id = identifier of the curve object.
      segment_index [opt] = the curve segment if curve_id identifies a polycurve.
    Returns:
      knot values if successful.
      None if not successful or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    nc = curve.ToNurbsCurve()
    if not nc: return scriptcontext.errorhandler()
    rc = [nc.Knots[i] for i in range(nc.Knots.Count)]
    return rc


def CurveLength(curve_id, segment_index=-1, sub_domain=None):
    """Returns the length of a curve object.
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
      sub_domain [opt] = list of two numbers identifing the sub-domain of the
          curve on which the calculation will be performed. The two parameters
          (sub-domain) must be non-decreasing. If omitted, the length of the
          entire curve is returned.
    Returns:
      The length of the curve if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    if sub_domain:
        if len(sub_domain)==2:
            dom = Rhino.Geometry.Interval(sub_domain[0], sub_domain[1])
            return curve.GetLength(dom)
        return scriptcontext.errorhandler()
    return curve.GetLength()


def CurveMidPoint(curve_id, segment_index=-1):
    """Returns the mid point of a curve object.
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The 3D mid point of the curve if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, t = curve.NormalizedLengthParameter(0.5)
    if rc: return curve.PointAt(t)
    return scriptcontext.errorhandler()


def CurveNormal(curve_id, segment_index=-1):
    """Returns the normal direction of the plane in which a planar curve object lies.
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The 3D normal vector if sucessful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    rc, plane = curve.TryGetPlane(tol)
    if rc: return plane.Normal
    return scriptcontext.errorhandler()


def CurveNormalizedParameter(curve_id, parameter):
    """Converts a curve parameter to a normalized curve parameter;
    one that ranges between 0-1
    Parameters:
      curve_id = identifier of the curve object
      parameter = the curve parameter to convert
    Returns:
      normalized curve parameter
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    return curve.Domain.NormalizedParameterAt(parameter)


def CurveParameter(curve_id, parameter):
    """Converts a normalized curve parameter to a curve parameter;
    one within the curve's domain
    Parameters:
      curve_id = identifier of the curve object
      parameter = the normalized curve parameter to convert
    Returns:
      curve parameter
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    return curve.Domain.ParameterAt(parameter)


def CurvePerpFrame(curve_id, parameter):
    """Returns the perpendicular plane at a parameter of a curve. The result
    is relatively parallel (zero-twisting) plane
    Parameters:
      curve_id = identifier of the curve object
      parameter = parameter to evaluate
    Returns:
      Plane on success
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    parameter = float(parameter)
    rc, plane = curve.PerpendicularFrameAt(parameter)
    if rc: return plane


def CurvePlane(curve_id, segment_index=-1):
    """Returns the plane in which a planar curve lies. Note, this function works
    only on planar curves.
    Parameters:
      curve_id = identifier of the curve object
      segment_index[opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The plane in which the curve lies if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    rc, plane = curve.TryGetPlane(tol)
    if rc: return plane
    return scriptcontext.errorhandler()


def CurvePointCount(curve_id, segment_index=-1):
    """Returns the control points count of a curve object.
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      Number of control points if successful.
      None if not successful
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    nc = curve.ToNurbsCurve()
    if nc: return nc.Points.Count
    return scriptcontext.errorhandler()


def CurvePoints(curve_id, segment_index=-1):
    """Returns the control points, or control vertices, of a curve object.
    If the curve is a rational NURBS curve, the euclidean control vertices
    are returned.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    nc = curve.ToNurbsCurve()
    if nc is None: return scriptcontext.errorhandler()
    points = [nc.Points[i].Location for i in xrange(nc.Points.Count)]
    return points


def CurveRadius(curve_id, test_point, segment_index=-1):
    """Returns the radius of curvature at a point on a curve.
    Parameters:
      curve_id = identifier of the curve object
      test_point = sampling point
      segment_index[opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The radius of curvature at the point on the curve if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    point = rhutil.coerce3dpoint(test_point, True)
    rc, t = curve.ClosestPoint(point, 0.0)
    if not rc: return scriptcontext.errorhandler()
    v = curve.CurvatureAt( t )
    k = v.Length
    if k>Rhino.RhinoMath.ZeroTolerance: return 1/k
    return scriptcontext.errorhandler()


def CurveSeam(curve_id, parameter):
    """Adjusts the seam, or start/end, point of a closed curve.
    Parameters:
      curve_id = identifier of the curve object
      parameter = The parameter of the new start/end point. 
                  Note, if successful, the resulting curve's
                  domain will start at dblParameter.
    Returns:
      True or False indicating success or failure.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if (not curve.IsClosed or not curve.Domain.IncludesParameter(parameter)):
        return False
    dupe = curve.Duplicate()
    if dupe:
        dupe.ChangeClosedCurveSeam(parameter)
        curve_id = rhutil.coerceguid(curve_id)
        dupe_obj = scriptcontext.doc.Objects.Replace(curve_id, dupe)
        return dupe_obj is not None
    return False


def CurveStartPoint(curve_id, segment_index=-1, point=None):
    """Returns the start point of a curve object
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
      point [opt] = new start point
    Returns:
      The 3D starting point of the curve if successful.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc = curve.PointAtStart
    if point:
        point = rhutil.coerce3dpoint(point, True)
        if point and curve.SetStartPoint(point):
            curve_id = rhutil.coerceguid(curve_id, True)
            scriptcontext.doc.Objects.Replace(curve_id, curve)
            scriptcontext.doc.Views.Redraw()
    return rc


def CurveSurfaceIntersection(curve_id, surface_id, tolerance=-1, angle_tolerance=-1):
    """Calculates intersection of a curve object with a surface object.
    Note, this function works on the untrimmed portion of the surface.
    Parameters:
      curve_id = The identifier of the first curve object.
      surface_id = The identifier of the second curve object. If omitted,
          the a self-intersection test will be performed on curve.
      tolerance [opt] = The absolute tolerance in drawing units. If omitted, 
          the document's current absolute tolerance is used.
      angle_tolerance [opt] = angle tolerance in degrees. The angle
          tolerance is used to determine when the curve is tangent to the
          surface. If omitted, the document's current angle tolerance is used.
    Returns:
      Two-dimensional list of intersection information if successful.
      The list will contain one or more of the following elements:
        Element Type     Description
        (n, 0)  Number   The intersection event type, either Point(1) or Overlap(2).
        (n, 1)  Point3d  If the event type is Point(1), then the intersection point 
                         on the first curve. If the event type is Overlap(2), then
                         intersection start point on the first curve.
        (n, 2)  Point3d  If the event type is Point(1), then the intersection point
                         on the first curve. If the event type is Overlap(2), then
                         intersection end point on the first curve.
        (n, 3)  Point3d  If the event type is Point(1), then the intersection point 
                         on the second curve. If the event type is Overlap(2), then
                         intersection start point on the surface.
        (n, 4)  Point3d  If the event type is Point(1), then the intersection point
                         on the second curve. If the event type is Overlap(2), then
                         intersection end point on the surface.
        (n, 5)  Number   If the event type is Point(1), then the first curve parameter.
                         If the event type is Overlap(2), then the start value of the
                         first curve parameter range.
        (n, 6)  Number   If the event type is Point(1), then the first curve parameter.
                         If the event type is Overlap(2), then the end value of the
                         curve parameter range.
        (n, 7)  Number   If the event type is Point(1), then the U surface parameter.
                         If the event type is Overlap(2), then the U surface parameter
                         for curve at (n, 5).
        (n, 8)  Number   If the event type is Point(1), then the V surface parameter.
                         If the event type is Overlap(2), then the V surface parameter
                         for curve at (n, 5).
        (n, 9)  Number   If the event type is Point(1), then the U surface parameter.
                         If the event type is Overlap(2), then the U surface parameter
                         for curve at (n, 6).
        (n, 10) Number   If the event type is Point(1), then the V surface parameter.
                         If the event type is Overlap(2), then the V surface parameter
                         for curve at (n, 6).
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    surface = rhutil.coercesurface(surface_id, True)
    if tolerance is None or tolerance<0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    if angle_tolerance is None or angle_tolerance<0:
        angle_tolerance = scriptcontext.doc.ModelAngleToleranceRadians
    else:
        angle_tolerance = math.radians(angle_tolerance)
    rc = Rhino.Geometry.Intersect.Intersection.CurveSurface(curve, surface, tolerance, angle_tolerance)
    if rc:
        events = []
        for i in xrange(rc.Count):
            event_type = 2 if rc[i].IsOverlap else 1
            item = rc[i]
            oa = item.OverlapA
            u,v = item.SurfaceOverlapParameter()
            e = (event_type, item.PointA, item.PointA2, item.PointB, item.PointB2, oa[0], oa[1], u[0], u[1], v[0], v[1])
            events.append(e)
        return events


def CurveTangent(curve_id, parameter, segment_index=-1):
    """Returns a 3D vector that is the tangent to a curve at a parameter.
    Parameters:
      curve_id = identifier of the curve object
      parameter = parameter to evaluate
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      A 3D vector if successful.
      None on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc = Rhino.Geometry.Point3d.Unset
    if curve.Domain.IncludesParameter(parameter):
        return curve.TangentAt(parameter)
    return scriptcontext.errorhandler()


def CurveWeights(curve_id, segment_index=-1):
    """Returns list of weights that are assigned to the control points of a curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index[opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      The weight values of the curve if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    nc = curve
    if type(curve) is not Rhino.Geometry.NurbsCurve:
        nc = curve.ToNurbsCurve()
    if nc is None: return scriptcontext.errorhandler()
    return [pt.Weight for pt in nc.Points]


def DivideCurve(curve_id, segments, create_points=False, return_points=True):
    """Divides a curve object into a specified number of segments.
    Parameters:
      curve_id = identifier of the curve object
      segments = The number of segments.
      create_points [opt] = Create the division points. If omitted or False,
          points are not created.
      return_points [opt] = If omitted or True, points are returned.
          If False, then a list of curve parameters are returned.
    Returns:
      If return_points is not specified or True, then a list containing 3D
      division points.
      If return_points is False, then an array containing division curve
      parameters.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    rc = curve.DivideByCount(segments, True)
    if not rc: return scriptcontext.errorhandler()
    if return_points or create_points:
        outputpoints = [curve.PointAt(t) for t in rc]
        if return_points: rc = outputpoints
        if create_points:
            for point in outputpoints:
                if point.IsValid: scriptcontext.doc.Objects.AddPoint(point)
            scriptcontext.doc.Views.Redraw()
    return rc


def DivideCurveEquidistant(curve_id, distance, create_points=False, return_points=True):
    """Divides a curve such that the linear distance between the points is equal.
    Parameters:
      curve_id = the object's identifier
      distance = linear distance between division points
      create_points[opt] = create the division points
      return_points[opt] = If True, return a list of points.
          If False, return a list of curve parameters
    Returns:
      A list of points or curve parameters based on the value of return_points
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    points = curve.DivideEquidistant(distance)
    if not points: return scriptcontext.errorhandler()
    if create_points:
        for point in points: scriptcontext.doc.Objects.AddPoint(point)
        scriptcontext.doc.Views.Redraw()
    if return_points: return points
    tvals = []
    for point in points:
        rc, t = curve.ClosestPoint(point)
        tvals.append(t)
    return tvals


def DivideCurveLength(curve_id, length, create_points=False, return_points=True):
    """Divides a curve object into segments of a specified length.
    Parameters:
      curve_id = identifier of the curve object
      length = The length of each segment.
      create_points [opt] = Create the division points. If omitted or False,
          points are not created.
      return_points [opt] = If omitted or True, points are returned.
          If False, then a list of curve parameters are returned.
    Returns:
      If return_points is not specified or True, then a list containing 3D
      division points if successful.
      If return_points is False, then an array containing division curve
      parameters if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    rc = curve.DivideByLength(length, True)
    if not rc: return scriptcontext.errorhandler()
    if return_points or create_points:
        outputpoints = [curve.PointAt(t) for t in rc]
        if create_points:
            for point in outputpoints:
                if (point.IsValid): scriptcontext.doc.Objects.AddPoint(point)
        if return_points: rc = outputpoints
    return rc


def EllipseCenterPoint(curve_id):
    """Returns the center point of an elliptical-shaped curve object.
    Parameters:
      curve_id = identifier of the curve object.    
    Returns:
      The 3D center point of the ellipse if successful.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    rc, ellipse = curve.TryGetEllipse()
    if not rc: raise ValueError("curve is not an ellipse")
    return ellipse.Plane.Origin


def EllipseQuadPoints(curve_id):
    """Returns the quadrant points of an elliptical-shaped curve object.
    Parameters:
      curve_id = identifier of the curve object.
    Returns:
      Four 3D points identifying the quadrants of the ellipse
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    rc, ellipse = curve.TryGetEllipse()
    if not rc: raise ValueError("curve is not an ellipse")
    origin = ellipse.Plane.Origin;
    xaxis = ellipse.Radius1 * ellipse.Plane.XAxis;
    yaxis = ellipse.Radius2 * ellipse.Plane.YAxis;
    return (origin-xaxis, origin+xaxis, origin-yaxis, origin+yaxis)


def EvaluateCurve(curve_id, t, segment_index=-1):
    """Evaluates a curve at a parameter and returns a 3D point
    Parameters:
      curve_id = identifier of the curve object
      t = the parameter to evaluate
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.PointAt(t)


def ExplodeCurves(curve_ids, delete_input=False):
    """Explodes, or un-joins, one curves. Polycurves will be exploded into curve
    segments. Polylines will be exploded into line segments. ExplodeCurves will
    return the curves in topological order. 
    Parameters:
      curve_ids = the curve object(s) to explode.
      delete_input[opt] = Delete input objects after exploding.
    Returns:
      List identifying the newly created curve objects
    """
    if( type(curve_ids) is list or type(curve_ids) is tuple ): pass
    else: curve_ids = [curve_ids]
    rc = []
    for id in curve_ids:
        curve = rhutil.coercecurve(id, -1, True)
        pieces = curve.DuplicateSegments()
        if pieces:
            for piece in pieces:
                rc.append(scriptcontext.doc.Objects.AddCurve(piece))
            if delete_input:
                id = rhutil.coerceguid(id, True)
                scriptcontext.doc.Objects.Delete(id, True)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def ExtendCurve(curve_id, extension_type, side, boundary_object_ids):
    """Extends a non-closed curve object by a line, arc, or smooth extension
    until it intersects a collection of objects.
    Parameters:
      curve_id: identifier of curve to extend
      extension_type: 0 = line, 1 = arc, 2 = smooth
      side: 0=extend from the start of the curve, 1=extend from the end of the curve
      boundary_object_ids: curve, surface, and polysurface objects to extend to
    Returns:
      The identifier of the new object if successful.
      None if not successful
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if extension_type==0: extension_type = Rhino.Geometry.CurveExtensionStyle.Line
    elif extension_type==1: extension_type = Rhino.Geometry.CurveExtensionStyle.Arc
    elif extension_type==2: extension_type = Rhino.Geometry.CurveExtensionStyle.Smooth
    else: raise ValueError("extension_type must be 0, 1, or 2")
    
    if side==0: side = Rhino.Geometry.CurveEnd.Start
    elif side==1: side = Rhino.Geometry.CurveEnd.End
    elif side==2: side = Rhino.Geometry.CurveEnd.Both
    else: raise ValueError("side must be 0, 1, or 2")
    
    rhobjs = [rhutil.coercerhinoobject(id) for id in boundary_object_ids]
    if not rhobjs: raise ValueError("boundary_object_ids must contain at least one item")
    geometry = [obj.Geometry for obj in rhobjs]
    newcurve = curve.Extend(side, extension_type, geometry)
    if newcurve and newcurve.IsValid:
        curve_id = rhutil.coerceguid(curve_id, True)
        if scriptcontext.doc.Objects.Replace(curve_id, newcurve):
            scriptcontext.doc.Views.Redraw()
            return curve_id
    return scriptcontext.errorhandler()


def ExtendCurveLength(curve_id, extension_type, side, length):
    """Extends a non-closed curve by a line, arc, or smooth extension for a
    specified distance
    Parameters:
      curve_id: curve to extend
      extension_type: 0 = line, 1 = arc, 2 = smooth
      side: 0=extend from start of the curve, 1=extend from end of the curve
      length: distance to extend
    Returns:
      The identifier of the new object
      None if not successful
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if extension_type==0: extension_type = Rhino.Geometry.CurveExtensionStyle.Line
    elif extension_type==1: extension_type = Rhino.Geometry.CurveExtensionStyle.Arc
    elif extension_type==2: extension_type = Rhino.Geometry.CurveExtensionStyle.Smooth
    else: raise ValueError("extension_type must be 0, 1, or 2")
    
    if side==0: side = Rhino.Geometry.CurveEnd.Start
    elif side==1: side = Rhino.Geometry.CurveEnd.End
    elif side==2: side = Rhino.Geometry.CurveEnd.Both
    else: raise ValueError("side must be 0, 1, or 2")
    newcurve = None
    if length<0: newcurve = curve.Trim(side, -length)
    else: newcurve = curve.Extend(side, length, extension_type)
    if newcurve and newcurve.IsValid:
        curve_id = rhutil.coerceguid(curve_id, True)
        if scriptcontext.doc.Objects.Replace(curve_id, newcurve):
            scriptcontext.doc.Views.Redraw()
            return curve_id
    return scriptcontext.errorhandler()


def ExtendCurvePoint(curve_id, side, point):
    """Extends a non-closed curve by smooth extension to a point
    Parameters:
      curve_id: curve to extend
      side: 0=extend from start of the curve, 1=extend from end of the curve
      point: point to extend to
    Returns:
      The identifier of the new object if successful.
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    point = rhutil.coerce3dpoint(point, True)
    
    if side==0: side = Rhino.Geometry.CurveEnd.Start
    elif side==1: side = Rhino.Geometry.CurveEnd.End
    elif side==2: side = Rhino.Geometry.CurveEnd.Both
    else: raise ValueError("side must be 0, 1, or 2")
    
    extension_type = Rhino.Geometry.CurveExtensionStyle.Smooth
    newcurve = curve.Extend(side, extension_type, point)
    if newcurve and newcurve.IsValid:
        curve_id = rhutil.coerceguid(curve_id, True)
        if scriptcontext.doc.Objects.Replace( curve_id, newcurve ):
            scriptcontext.doc.Views.Redraw()
            return curve_id
    return scriptcontext.errorhandler()


def FairCurve(curve_id, tolerance=1.0):
    """Fairs a curve. Fair works best on degree 3 (cubic) curves. Fair attempts
    to remove large curvature variations while limiting the geometry changes to
    be no more than the specified tolerance. Sometimes several applications of
    this method are necessary to remove nasty curvature problems.
    Parameters:
      curve_id = curve to fair
      tolerance[opt] = fairing tolerance
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    angle_tol = 0.0
    clamp = 0
    if curve.IsPeriodic:
        curve = curve.ToNurbsCurve()
        clamp = 1
    newcurve = curve.Fair(tolerance, angle_tol, clamp, clamp, 100)
    if not newcurve: return False
    curve_id = rhutil.coerceguid(curve_id, True)
    if scriptcontext.doc.Objects.Replace(curve_id, newcurve):
        scriptcontext.doc.Views.Redraw()
        return True
    return False


def FitCurve(curve_id, degree=3, distance_tolerance=-1, angle_tolerance=-1):
    """Reduces number of curve control points while maintaining the curve's same
    general shape. Use this function for replacing curves with many control
    points. For more information, see the Rhino help for the FitCrv command.
    Parameters:
      curve_id = Identifier of the curve object
      degree [opt] = The curve degree, which must be greater than 1.
                     The default is 3.
      distance_tolerance [opt] = The fitting tolerance. If distance_tolerance
          is not specified or <= 0.0, the document absolute tolerance is used.
      angle_tolerance [opt] = The kink smoothing tolerance in degrees. If
          angle_tolerance is 0.0, all kinks are smoothed. If angle_tolerance
          is > 0.0, kinks smaller than angle_tolerance are smoothed. If
          angle_tolerance is not specified or < 0.0, the document angle
          tolerance is used for the kink smoothing.
    Returns:
      The identifier of the new object
      None if not successful, or on error.
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if distance_tolerance is None or distance_tolerance<0:
        distance_tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    if angle_tolerance is None or angle_tolerance<0:
        angle_tolerance = scriptcontext.doc.ModelAngleToleranceRadians
    nc = curve.Fit(degree, distance_tolerance, angle_tolerance)
    if nc:
        rhobj = rhutil.coercerhinoobject(curve_id)
        rc = None
        if rhobj:
            rc = scriptcontext.doc.Objects.AddCurve(nc, rhobj.Attributes)
        else:
            rc = scriptcontext.doc.Objects.AddCurve(nc)
        if rc==System.Guid.Empty: raise Exception("Unable to add curve to document")
        scriptcontext.doc.Views.Redraw()
        return rc
    return scriptcontext.errorhandler()


def InsertCurveKnot(curve_id, parameter, symmetrical=False ):
    """Inserts a knot into a curve object
    Parameters:
      curve_id = identifier of the curve object
      parameter = parameter on the curve
      symmetrical[opt] = if True, then knots are added on both sides of
          the center of the curve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if not curve.Domain.IncludesParameter(parameter): return False
    nc = curve.ToNurbsCurve()
    if not nc: return False
    rc, t = curve.GetNurbsFormParameterFromCurveParameter(parameter)
    if rc:
        rc = nc.Knots.InsertKnot(t,1)
        if rc and symmetrical:
            domain = nc.Domain
            t_sym = domain.T1 - t + domain.T0
            if abs(t_sym)>Rhino.RhinoMath.SqrtEpsilon:
                rc = nc.Knots.InsertKnot(t_sym,1)
        if rc:
            curve_id = rhutil.coerceguid(curve_id)
            rc = scriptcontext.doc.Objects.Replace(curve_id, nc)
            if rc: scriptcontext.doc.Views.Redraw()
    return rc


def IsArc(curve_id, segment_index=-1):
    """Verifies an object is an arc curve
    Parameters:
      curve_id = Identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.IsArc()


def IsCircle(curve_id, segment_index=-1):
    """Verifies an object is a circle curve
    Parameters:
      curve_id = Identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.IsCircle()


def IsCurve(object_id):
    "Verifies an object is a curve"
    curve = rhutil.coercecurve(object_id)
    return curve is not None


def IsCurveClosable(curve_id, tolerance=None):
    """Decide if it makes sense to close off the curve by moving the end point
    to the start point based on start-end gap size and length of curve as
    approximated by chord defined by 6 points
    Parameters:
      curve_id = identifier of the curve object
      tolerance[opt] = maximum allowable distance between start point and end
        point. If omitted, the document's current absolute tolerance is used
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if tolerance is None: tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    return curve.IsClosable(tolerance)


def IsCurveClosed(object_id):
    curve = rhutil.coercecurve(object_id, -1, True)
    return curve.IsClosed


def IsCurveInPlane(object_id, plane=None):
    """Test a curve to see if it lies in a specific plane
    Parameters:
      object_id = the object's identifier
      plane[opt] = plane to test. If omitted, the active construction plane is used
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(object_id, -1, True)
    if not plane:
        plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
    else:
        plane = rhutil.coerceplane(plane, True)
    return curve.IsInPlane(plane, scriptcontext.doc.ModelAbsoluteTolerance)


def IsCurveLinear(object_id, segment_index=-1):
    """Verifies an object is a linear curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(object_id, segment_index, True)
    return curve.IsLinear()


def IsCurvePeriodic(curve_id, segment_index=-1):
    """Verifies an object is a periodic curve object
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    return curve.IsPeriodic


def IsCurvePlanar(curve_id, segment_index=-1):
    """Verifies an object is a planar curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    return curve.IsPlanar(tol)


def IsCurveRational(curve_id, segment_index=-1):
    """Verifies an object is a rational NURBS curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    if isinstance(curve, Rhino.Geometry.NurbsCurve): return curve.IsRational
    return False


def IsEllipse(object_id, segment_index=-1):
    """Verifies an object is an elliptical-shaped curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(object_id, segment_index, True)
    return curve.IsEllipse()


def IsLine(object_id, segment_index=-1):
    """Verifies an object is a line curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(object_id, segment_index, True)
    if isinstance(curve, Rhino.Geometry.LineCurve): return True
    rc, polyline = curve.TryGetPolyline()
    if rc and polyline.Count==2: return True
    return False


def IsPointOnCurve(object_id, point, segment_index=-1):
    """Verifies that a point is on a curve
    Parameters:
      curve_id = identifier of the curve object
      point = the test point
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(object_id, segment_index, True)
    point = rhutil.coerce3dpoint(point, True)
    rc, t = curve.ClosestPoint(point, Rhino.RhinoMath.SqrtEpsilon)
    return rc


def IsPolyCurve(object_id, segment_index=-1):
    """Verifies an object is a PolyCurve curve
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(object_id, segment_index, True)
    return isinstance(curve, Rhino.Geometry.PolyCurve)


def IsPolyline( object_id, segment_index=-1 ):
    """Verifies an object is a Polyline curve object
    Parameters:
      curve_id = identifier of the curve object
      segment_index [opt] = the curve segment if curve_id identifies a polycurve
    Returns:
      True or False
    """
    curve = rhutil.coercecurve(object_id, segment_index, True)
    return isinstance(curve, Rhino.Geometry.PolylineCurve)


def JoinCurves(object_ids, delete_input=False, tolerance=None):
    """Joins multiple curves together to form one or more curves or polycurves
    Parameters:
      object_ids = list of multiple curves
      delete_input[opt] = delete input objects after joining
      tolerance[opt] = join tolerance. If omitted, 2.1 * document absolute
          tolerance is used
    Returns:
      List of Guids representing the new curves
    """
    if len(object_ids)<2: raise ValueError("object_ids must contain at least 2 items")
    curves = [rhutil.coercecurve(id, -1, True) for id in object_ids]
    if tolerance is None:
        tolerance = 2.1 * scriptcontext.doc.ModelAbsoluteTolerance
    newcurves = Rhino.Geometry.Curve.JoinCurves(curves, tolerance)
    rc = []
    if newcurves:
        rc = [scriptcontext.doc.Objects.AddCurve(crv) for crv in newcurves]
    if rc and delete_input:
        for id in object_ids:
            id = rhutil.coerceguid(id, True)
            scriptcontext.doc.Objects.Delete(id, False)
    scriptcontext.doc.Views.Redraw()
    return rc


def LineFitFromPoints(points):
    """Returns a line that was fit through an array of 3D points
    Parameters:
      points = a list of at least two 3D points
    Returns:
      line on success
    """
    points = rhutil.coerce3dpointlist(points, True)
    rc, line = Rhino.Geometry.Line.TryFitLineToPoints(points)
    if rc: return line
    return scriptcontext.errorhandler()


def MakeCurveNonPeriodic(curve_id, delete_input=False):
    """Makes a periodic curve non-periodic. Non-periodic curves can develop
    kinks when deformed
    Parameters:
      curve_id = identifier of the curve object
      delete_input[opt] = delete the input curve
    Returns:
      id of the new or modified curve if successful
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if not curve.IsPeriodic: return scriptcontext.errorhandler()
    nc = curve.ToNurbsCurve()
    if nc is None: return scriptcontext.errorhandler()
    nc.Knots.ClampEnd( Rhino.Geometry.CurveEnd.Both )
    rc = None
    if delete_input:
        if type(curve_id) is Rhino.DocObjects.ObjRef: pass
        else: curve_id = rhutil.coerceguid(curve_id)
        if curve_id:
            rc = scriptcontext.doc.Objects.Replace(curve_id, nc)
            if not rc: return scriptcontext.errorhandler()
            rc = rhutil.coerceguid(curve_id)
    else:
        attrs = None
        if type(scriptcontext.doc) is Rhino.RhinoDoc:
            rhobj = rhutil.coercerhinoobject(curve_id)
            if rhobj: attrs = rhobj.Attributes
        rc = scriptcontext.doc.Objects.AddCurve(nc, attrs)
        if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def MeanCurve(curve0, curve1, tolerance=None):
    """Creates an average curve from two curves
    Parameters:
      curve0, curve1 = identifiers of two curves
      tolerance[opt] = angle tolerance used to match kinks between curves
    Returns:
      id of the new or modified curve if successful
      None on error
    """
    curve0 = rhutil.coercecurve(curve0, -1, True)
    curve1 = rhutil.coercecurve(curve1, -1, True)
    if tolerance is None: tolerance=Rhino.RhinoMath.UnsetValue
    crv = Rhino.Geometry.Curve.CreateMeanCurve(curve0,curve1,tolerance)
    if crv:
        rc = scriptcontext.doc.Objects.AddCurve(crv)
        scriptcontext.doc.Views.Redraw()
        return rc


def MeshPolyline(polyline_id):
    """Creates a polygon mesh object based on a closed polyline curve object.
    The created mesh object is added to the document
    Parameters:
      polyline_id = identifier of the polyline curve object
    Returns:
      identifier of the new mesh object
      None on error
    """
    curve = rhutil.coercecurve(polyline_id, -1, True)
    ispolyline, polyline = curve.TryGetPolyline()
    if not ispolyline: return scriptcontext.errorhandler()
    mesh = Rhino.Geometry.Mesh.CreateFromClosedPolyline(polyline)
    if not mesh: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddMesh(mesh)
    scriptcontext.doc.Views.Redraw()
    return rc


def OffsetCurve(object_id, direction, distance, normal=None, style=1):
    """Offsets a curve by a distance. The offset curve will be added to Rhino
    Parameters:
      object_id = identifier of a curve object
      direction = point describing direction of the offset
      distance = distance of the offset
      normal[opt] = normal of the plane in which the offset will occur.
          If omitted, the normal of the active construction plane will be used
      style[opt] = the corner style
          0 = None, 1 = Sharp, 2 = Round, 3 = Smooth, 4 = Chamfer
    Returns:
      List of ids for the new curves on success
      None on error
    """
    curve = rhutil.coercecurve(object_id, -1, True)
    direction = rhutil.coerce3dpoint(direction, True)
    if normal:
        normal = rhutil.coerce3dvector(normal, True)
    else:
        normal = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane().Normal
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    style = System.Enum.ToObject(Rhino.Geometry.CurveOffsetCornerStyle, style)
    curves = curve.Offset(direction, normal, distance, tolerance, style)
    if curves is None: return scriptcontext.errorhandler()
    rc = [scriptcontext.doc.Objects.AddCurve(curve) for curve in curves]
    scriptcontext.doc.Views.Redraw()
    return rc


def OffsetCurveOnSurface(curve_id, surface_id, distance_or_parameter):
    """Offset a curve on a surface. The source curve must lie on the surface.
    The offset curve or curves will be added to Rhino
    Parameters:
      curve_id, surface_id = curve and surface identifiers
      distance_or_parameter = If a single number is passed, then this is the
        distance of the offset. Based on the curve's direction, a positive value
        will offset to the left and a negative value will offset to the right.
        If a tuple of two values is passed, this is interpreted as the surface
        U,V parameter that the curve will be offset through
    Returns:
      Identifiers of the new curves if successful
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    surface = rhutil.coercesurface(surface_id, True)
    x = None
    if type(distance_or_parameter) is list or type(distance_or_parameter) is tuple:
        x = Rhino.Geometry.Point2d( distance_or_parameter[0], distance_or_parameter[1] )
    else:
        x = float(distance_or_parameter)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    curves = curve.OffsetOnSurface(surface, x, tol)
    if curves is None: return scriptcontext.errorhandler()
    rc = [scriptcontext.doc.Objects.AddCurve(curve) for curve in curves]
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def PlanarClosedCurveContainment(curve_a, curve_b, plane=None, tolerance=None):
    """Determines the relationship between the regions bounded by two coplanar
    simple closed curves
    Parameters:
      curve_a, curve_b = identifiers of two planar, closed curves
      plane[opt] = test plane. If omitted, the currently active construction
        plane is used
      tolerance[opt] = if omitted, the document absolute tolerance is used
    Returns:
      a number identifying the relationship if successful
        0 = the regions bounded by the curves are disjoint
        1 = the two curves intersect
        2 = the region bounded by curve_a is inside of curve_b
        3 = the region bounded by curve_b is inside of curve_a
      None if not successful
    """
    curve_a = rhutil.coercecurve(curve_a, -1, True)
    curve_b = rhutil.coercecurve(curve_b, -1, True)
    if tolerance is None or tolerance<=0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    if plane:
        plane = rhutil.coerceplane(plane)
    else:
        plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
    rc = Rhino.Geometry.Curve.PlanarClosedCurveRelationship(curve_a, curve_b, plane, tolerance)
    return int(rc)


def PlanarCurveCollision(curve_a, curve_b, plane=None, tolerance=None):
    """Determines if two coplanar curves intersect
    Parameters:
      curve_a, curve_b = identifiers of two planar curves
      plane[opt] = test plane. If omitted, the currently active construction
        plane is used
      tolerance[opt] = if omitted, the document absolute tolerance is used
    Returns:
      True if the curves intersect; otherwise False
    """
    curve_a = rhutil.coercecurve(curve_a, -1, True)
    curve_b = rhutil.coercecurve(curve_b, -1, True)
    if tolerance is None or tolerance<=0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    if plane:
        plane = rhutil.coerceplane(plane)
    else:
        plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
    return Rhino.Geometry.Curve.PlanarCurveCollision(curve_a, curve_b, plane, tolerance)


def PointInPlanarClosedCurve(point, curve, plane=None, tolerance=None):
    """Determines if a point is inside of a closed curve, on a closed curve, or
    outside of a closed curve
    Parameters:
      point = text point
      curve = identifier of a curve object
      plane[opt] = plane containing the closed curve and point. If omitted,
          the currently active construction plane is used
      tolerance[opt] = it omitted, the document abosulte tolerance is used
    Returns:
      number identifying the result if successful
          0 = point is outside of the curve
          1 = point is inside of the curve
          2 = point in on the curve
    """
    point = rhutil.coerce3dpoint(point, True)
    curve = rhutil.coercecurve(curve, -1, True)
    if tolerance is None or tolerance<=0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    if plane:
        plane = rhutil.coerceplane(plane)
    else:
        plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
    rc = curve.Contains(point, plane, tolerance)
    if rc==Rhino.Geometry.PointContainment.Unset: raise Exception("Curve.Contains returned Unset")
    if rc==Rhino.Geometry.PointContainment.Outside: return 0
    if rc==Rhino.Geometry.PointContainment.Inside: return 1
    return 2


def PolyCurveCount(curve_id, segment_index=-1):
    """Returns the number of curve segments that make up a polycurve"""
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    if isinstance(curve, Rhino.Geometry.PolyCurve): return curve.SegmentCount
    raise ValueError("curve_id does not reference a polycurve")


def PolylineVertices(curve_id, segment_index=-1):
    "Returns the vertices of a polyline curve on success"
    curve = rhutil.coercecurve(curve_id, segment_index, True)
    rc, polyline = curve.TryGetPolyline()
    if rc: return [pt for pt in polyline]
    raise ValueError("curve_id does not reference a polyline")


def ProjectCurveToMesh(curve_ids, mesh_ids, direction):
    """Projects one or more curves onto one or more surfaces or meshes
    Parameters:
      curve_ids = identifiers of curves to project
      mesh_ids = identifiers of meshes to project onto
      direction = projection direction
    Returns:
      list of identifiers
    """
    curve_ids = rhutil.coerceguidlist(curve_ids)
    mesh_ids = rhutil.coerceguidlist(mesh_ids)
    direction = rhutil.coerce3dvector(direction, True)
    curves = [rhutil.coercecurve(id, -1, True) for id in curve_ids]
    meshes = [rhutil.coercemesh(id, True) for id in mesh_ids]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newcurves = Rhino.Geometry.Curve.ProjectToMesh(curves, meshes, direction, tolerance)
    ids = [scriptcontext.doc.Objects.AddCurve(curve) for curve in newcurves]
    if ids: scriptcontext.doc.Views.Redraw()
    return ids


def ProjectCurveToSurface(curve_ids, surface_ids, direction):
    """Projects one or more curves onto one or more surfaces or polysurfaces
    Parameters:
      curve_ids = identifiers of curves to project
      surface_ids = identifiers of surfaces to project onto
      direction = projection direction
    Returns:
      list of identifiers
    """
    curve_ids = rhutil.coerceguidlist(curve_ids)
    surface_ids = rhutil.coerceguidlist(surface_ids)
    direction = rhutil.coerce3dvector(direction, True)
    curves = [rhutil.coercecurve(id, -1, True) for id in curve_ids]
    breps = [rhutil.coercebrep(id, True) for id in surface_ids]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newcurves = Rhino.Geometry.Curve.ProjectToBrep(curves, breps, direction, tolerance)
    ids = [scriptcontext.doc.Objects.AddCurve(curve) for curve in newcurves]
    if ids: scriptcontext.doc.Views.Redraw()
    return ids


def RebuildCurve(curve_id, degree=3, point_count=10):
    """Rebuilds a curve to a given degree and control point count. For more
    information, see the Rhino help for the Rebuild command.
    Parameters:
      curve_id = identifier of the curve object
      degree[opt] = new degree (must be greater than 0)
      point_count [opt] = new point count, which must be bigger than degree.
    Returns:
      True of False indicating success or failure
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if degree<1: raise ValueError("degree must be greater than 0")
    newcurve = curve.Rebuild(point_count, degree, False)
    if not newcurve: return False
    scriptcontext.doc.Objects.Replace(curve_id, newcurve)
    scriptcontext.doc.Views.Redraw()
    return True


def ReverseCurve(curve_id):
    """Reverses the direction of a curve object. Same as Rhino's Dir command
    Parameters:
      curve_id = identifier of the curve object
    Returns:
      True or False indicating success or failure
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if curve.Reverse():
        curve_id = rhutil.coerceguid(curve_id, True)
        scriptcontext.doc.Objects.Replace(curve_id, curve)
        return True
    return False


def SimplifyCurve(curve_id, flags=0):
    "Replace a curve with a geometrically equivalent polycurve"
    curve = rhutil.coercecurve(curve_id, -1, True)
    _flags = Rhino.Geometry.CurveSimplifyOptions.All
    if( flags&1 ==1 ): _flags = _flags - Rhino.Geometry.CurveSimplifyOptions.SplitAtFullyMultipleKnots
    if( flags&2 ==2 ): _flags = _flags - Rhino.Geometry.CurveSimplifyOptions.RebuildLines
    if( flags&4 ==4 ): _flags = _flags - Rhino.Geometry.CurveSimplifyOptions.RebuildArcs
    if( flags&8 ==8 ): _flags = _flags - Rhino.Geometry.CurveSimplifyOptions.RebuildRationals
    if( flags&16==16 ): _flags = _flags - Rhino.Geometry.CurveSimplifyOptions.AdjustG1
    if( flags&32==32 ): _flags = _flags - Rhino.Geometry.CurveSimplifyOptions.Merge
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    ang_tol = scriptcontext.doc.ModelAngleToleranceRadians
    newcurve = curve.Simplify(_flags, tol, ang_tol)
    if newcurve:
        curve_id = rhutil.coerceguid(curve_id, True)
        scriptcontext.doc.Objects.Replace(curve_id, newcurve)
        scriptcontext.doc.Views.Redraw()
        return True
    return False


def SplitCurve(curve_id, parameter, delete_input=True):
    """Splits, or divides, a curve at a specified parameter. The parameter must
    be in the interior of the curve's domain
    Parameters:
      curve_id = the curve to split
      parameter = one or more parameters to split the curve at
      delete_input[opt] = delete the input curve
    Returns:
      list of new curves on success
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    newcurves = curve.Split(parameter)
    if newcurves is None: return scriptcontext.errorhandler()
    att = None
    rhobj = rhutil.coercerhinoobject(curve_id)
    if rhobj: att = rhobj.Attributes
    rc = [scriptcontext.doc.Objects.AddCurve(crv, att) for crv in newcurves]
    if rc and delete_input:
        id = rhutil.coerceguid(curve_id, True)
        scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def TrimCurve(curve_id, interval, delete_input=True):
    """Trims a curve by removing portions of the curve outside a specified interval
    Paramters:
      curve_id = the curve to trim
      interval = two numbers indentifying the interval to keep. Portions of
        the curve before domain[0] and after domain[1] will be removed. If the
        input curve is open, the interval must be increasing. If the input
        curve is closed and the interval is decreasing, then the portion of
        the curve across the start and end of the curve is returned
      delete_input[opt] = delete the input curve
    Reutrns:
      identifier of the new curve on success
      None on failure
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    if interval[0]==interval[1]: raise ValueError("interval values are equal")
    newcurve = curve.Trim(interval[0], interval[1])
    if not newcurve: return scriptcontext.errorhandler()
    att = None
    rhobj = rhutil.coercerhinoobject(curve_id)
    if rhobj: att = rhobj.Attributes
    rc = scriptcontext.doc.Objects.AddCurve(newcurve, att)
    if delete_input:
        id = rhutil.coerceguid(curve_id, True)
        scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc

########NEW FILE########
__FILENAME__ = dimension
import scriptcontext
import utility as rhutil
import Rhino
import System.Guid
from view import __viewhelper


def AddAlignedDimension(start_point, end_point, point_on_dimension_line, style=None):
    """Adds an aligned dimension object to the document. An aligned dimension
    is a linear dimension lined up with two points
    Parameters:
      start_point: first point of dimension
      end_point: second point of dimension
      point_on_dimension_line: location point of dimension line
      style[opt]: name of dimension style
    Returns:
      identifier of new dimension on success
      None on error
    """
    start = rhutil.coerce3dpoint(start_point, True)
    end = rhutil.coerce3dpoint(end_point, True)
    onpoint = rhutil.coerce3dpoint(point_on_dimension_line, True)
    plane = Rhino.Geometry.Plane(start, end, onpoint)
    success, s, t = plane.ClosestParameter(start)
    start = Rhino.Geometry.Point2d(s,t)
    success, s, t = plane.ClosestParameter(end)
    end = Rhino.Geometry.Point2d(s,t)
    success, s, t = plane.ClosestParameter(onpoint)
    onpoint = Rhino.Geometry.Point2d(s,t)
    ldim = Rhino.Geometry.LinearDimension(plane, start, end, onpoint)
    if not ldim: return scriptcontext.errorhandler()
    ldim.Aligned = True
    rc = scriptcontext.doc.Objects.AddLinearDimension(ldim)
    if rc==System.Guid.Empty: raise Exception("unable to add dimension to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddDimStyle(dimstyle_name=None):
    """Adds a new dimension style to the document. The new dimension style will
    be initialized with the current default dimension style properties.
    Properties:
      dimstyle_name[opt] = name of the new dimension style. If omitted, Rhino
        automatically generates the dimension style name
    Returns:
      name of the new dimension style on success
      None on error
    """
    index = scriptcontext.doc.DimStyles.Add(dimstyle_name)
    if index<0: return scriptcontext.errorhandler()
    ds = scriptcontext.doc.DimStyles[index]
    return ds.Name


def AddLeader(points, view_or_plane=None, text=None):
    """Adds a leader to the document. Leader objects are planar.
    The 3D points passed to this function should be co-planar
    Paramters:
      points = list of (at least 2) 3D points
      view_or_plane[opt] = If a view is specified, points will be constrained
        to the view's construction plane. If a view is not specified, points
        will be constrained to a plane fit through the list of points
      text[opt] = leader's text string
    Returns:
      identifier of the new leader on success
      None on error
    """
    points = rhutil.coerce3dpointlist(points)
    if points is None or len(points)<2: raise ValueError("points must have at least two items")
    rc = System.Guid.Empty
    if not view_or_plane:
        if text is None:
            rc = scriptcontext.doc.Objects.AddLeader(points)
        else:
            if not isinstance(text, str): text = str(text)
            rc = scriptcontext.doc.Objects.AddLeader(text, points)
    else:
        plane = rhutil.coerceplane(view_or_plane)
        if not plane:
            view = __viewhelper(view_or_plane)
            plane = view.ActiveViewport.ConstructionPlane()
        points2d = []
        for point in points:
            cprc, s, t = plane.ClosestParameter( point )
            if not cprc: return scriptcontext.errorhandler()
            points2d.append( Rhino.Geometry.Point2d(s,t) )
        if text is None:
            rc = scriptcontext.doc.Objects.AddLeader(plane, points2d)
        else:
            if not isinstance(text, str): text = str(text)
            rc = scriptcontext.doc.Objects.AddLeader(text, plane, points2d)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def AddLinearDimension(start_point, end_point, point_on_dimension_line):
    """Adds a linear dimension to the document
    Returns:
      identifier of the new object on success
      None on error
    """
    start = rhutil.coerce3dpoint(start_point, True)
    end = rhutil.coerce3dpoint(end_point, True)
    onpoint = rhutil.coerce3dpoint(point_on_dimension_line, True)
    ldim = Rhino.Geometry.LinearDimension.FromPoints(start, end, onpoint)
    if not ldim: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddLinearDimension(ldim)
    if rc==System.Guid.Empty: raise Exception("unable to add dimension to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def CurrentDimStyle( dimstyle_name=None ):
    """
    Returns or changes the current default dimension style
    Parameters:
      dimstyle_name[opt] = name of an existing dimension style to make current
    Returns:
      if dimstyle_name is not specified, name of the current dimension style
      if dimstyle_name is specified, name of the previous dimension style
      None on error
    """
    rc = scriptcontext.doc.DimStyles.CurrentDimensionStyle.Name
    if dimstyle_name:
        ds = scriptcontext.doc.DimStyles.Find(dimstyle_name, True)
        if ds is None: return scriptcontext.errorhandler()
        scriptcontext.doc.DimStyles.SetCurrentDimensionStyleIndex(ds.Index, False)
    return rc


def DeleteDimStyle(dimstyle_name):
    """Removes an existing dimension style from the document. The dimension style
    to be removed cannot be referenced by any dimension objects.
    Parameters:
      dimstyle_name = the name of an unreferenced dimension style
    Returns:
      The name of the deleted dimension style if successful
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle_name, True)
    if ds and scriptcontext.doc.DimStyles.DeleteDimensionStyle(ds.Index, True):
        return dimstyle_name
    return scriptcontext.errorhandler()


def __coerceannotation(object_id):
    annotation_object = rhutil.coercerhinoobject(object_id, True)
    if not isinstance(annotation_object, Rhino.DocObjects.AnnotationObjectBase):
        raise ValueError("object_id does not refer to an Annotation")
    return annotation_object


def DimensionStyle(object_id, dimstyle_name=None):
    """Returns or modifies the dimension style of a dimension object
    Parameters:
      object_id = identifier of the object
      dimstyle_name[opt] = the name of an existing dimension style
    Returns:
      if dimstyle_name is specified, the object's current dimension style name
      if dimstyle_name is not specified, the object's previous dimension style name
      None on error
    """
    annotation_object = __coerceannotation(object_id)
    ds = annotation_object.DimensionStyle
    rc = ds.Name
    if dimstyle_name:
        ds = scriptcontext.doc.DimStyles.Find(dimstyle_name, True)
        if not ds: return scriptcontext.errorhandler()
        annotation = annotation_object.Geometry
        annotation.DimensionStyleIndex = ds.Index
        annotation_object.CommitChanges()
    return rc


def DimensionText(object_id):
    """Returns the text displayed by a dimension object
    Parameters:
      object_id = identifier of the object
    """
    annotation_object = __coerceannotation(object_id)
    return annotation_object.DisplayText


def DimensionUserText(object_id, usertext=None):
    """Returns of modifies the user text string of a dimension object. The user
    text is the string that gets printed when the dimension is defined
    Parameters:
      object_id = identifier of the object
      usertext[opt] = the new user text string value
    Returns:
      if usertext is not specified, the current usertext string
      if usertext is specified, the previous usertext string
    """
    annotation_object = __coerceannotation(object_id)
    rc = annotation_object.Geometry.Text
    if usertext is not None:
        annotation_object.Geometry.Text = usertext
        annotation_object.CommitChanges()
        scriptcontext.doc.Views.Redraw()


def DimensionValue(object_id):
    """Returns the value of a dimension object
    Parameters:
      object_id = identifier of the object
    Returns:
      numeric value of the dimension if successful
    """
    annotation_object = __coerceannotation(object_id)
    return annotation_object.Geometry.NumericValue


def DimStyleAnglePrecision(dimstyle, precision=None):
    """Returns or changes the angle display precision of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      precision[opt] = the new angle precision value. If omitted, the current angle
        precision is returned
    Returns:
      If a precision is not specified, the current angle precision
      If a precision is specified, the previous angle precision
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.AngleResolution
    if precision is not None:
        ds.AngleResolution = precision
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleArrowSize(dimstyle, size=None):
    """Returns or changes the arrow size of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      size[opt] = the new arrow size. If omitted, the current arrow size is returned
    Returns:
      If size is not specified, the current arrow size
      If size is specified, the previous arrow size
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.ArrowLength
    if size is not None:
        ds.ArrowLength = size
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleCount():
    "Returns the number of dimension styles in the document"
    return scriptcontext.doc.DimStyles.Count


def DimStyleExtension(dimstyle, extension=None):
    """Returns or changes the extension line extension of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      extension[opt] = the new extension line extension
    Returns:
      if extension is not specified, the current extension line extension
      if extension is specified, the previous extension line extension
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.ExtensionLineExtension
    if extension is not None:
        ds.ExtensionLineExtension = extension
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleFont(dimstyle, font=None):
    """Returns or changes the font used by a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      font[opt] = the new font face name
    Returns:
      if font is not specified, the current font if successful
      if font is specified, the previous font if successful
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    oldindex = ds.FontIndex
    rc = scriptcontext.doc.Fonts[oldindex].FaceName
    if font:
        newindex = scriptcontext.doc.Fonts.FindOrCreate(font, False, False)
        ds.FontIndex = newindex
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleLeaderArrowSize(dimstyle, size=None):
    """Returns or changes the leader arrow size of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      size[opt] = the new leader arrow size
    Returns:
      if size is not specified, the current leader arrow size
      if size is specified, the previous leader arrow size
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.LeaderArrowLength
    if size is not None:
        ds.LeaderArrowLength = size
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleLengthFactor(dimstyle, factor=None):
    """Returns or changes the length factor of a dimension style. Length factor
    is the conversion between Rhino units and dimension units
    Parameters:
      dimstyle = the name of an existing dimension style
      factor[opt] = the new length factor
    Returns:
      if factor is not defined, the current length factor
      if factor is defined, the previous length factor
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.LengthFactor
    if factor is not None:
        ds.LengthFactor = factor
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleLinearPrecision(dimstyle, precision=None):
    """Returns or changes the linear display precision of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      precision[opt] = the new linear precision value
    Returns:
      if precision is not specified, the current linear precision value
      if precision is specified, the previous linear precision value
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.LengthResolution
    if precision is not None:
        ds.LengthResolution = precision
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleNames(sort=False):
    "Returns the names of all dimension styles in the document"
    rc = [ds.Name for ds in scriptcontext.doc.DimStyles]
    if sort: rc.sort()
    return rc


def DimStyleNumberFormat(dimstyle, format=None):
    """Returns or changes the number display format of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      format[opt] = the new number format
         0 = Decimal
         1 = Fractional
         2 = Feet and inches
    Returns:
      if format is not specified, the current display format
      if format is specified, the previous display format
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = int(ds.LengthFormat)
    if format is not None:
        if format==0: ds.LengthFormat = Rhino.DocObjects.DistanceDisplayMode.Decimal
        if format==1: ds.LengthFormat = Rhino.DocObjects.DistanceDisplayMode.Feet
        if format==2: ds.LengthFormat = Rhino.DocObjects.DistanceDisplayMode.FeetAndInches
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleOffset(dimstyle, offset=None):
    """Returns or changes the extension line offset of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      offset[opt] = the new extension line offset
    Returns:
      if offset is not specified, the current extension line offset
      if offset is specified, the previous extension line offset
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.ExtensionLineOffset
    if offset is not None:
        ds.ExtensionLineOffset = offset
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStylePrefix(dimstyle, prefix=None):
    """Returns or changes the prefix of a dimension style - the text to
    prefix to the dimension text.
    Parameters:
      dimstyle = the name of an existing dimstyle
      prefix[opt] = the new prefix
    Returns:
      if prefix is not specified, the current prefix
      if prefix is specified, the previous prefix
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.Prefix
    if prefix is not None:
        ds.Prefix = prefix
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleSuffix(dimstyle, suffix=None):
    """Returns or changes the suffix of a dimension style - the text to
    append to the dimension text.
    Parameters:
      dimstyle = the name of an existing dimstyle
      suffix[opt] = the new suffix
    Returns:
      if suffix is not specified, the current suffix
      if suffix is specified, the previous suffix
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.Suffix
    if suffix is not None:
        ds.Suffix = suffix
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleTextAlignment(dimstyle, alignment=None):
    """Returns or changes the text alignment mode of a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      alignment[opt] = the new text alignment
          0 = Normal (same as 2)
          1 = Horizontal to view
          2 = Above the dimension line
          3 = In the dimension line
    Returns:
      if alignment is not specified, the current text alignment
      if alignment is specified, the previous text alignment
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = int(ds.TextAlignment)
    if alignment is not None:
        if alignment==0: ds.TextAlignment = Rhino.DocObjects.TextDisplayAlignment.Normal
        if alignment==1: ds.TextAlignment = Rhino.DocObjects.TextDisplayAlignment.Horizontal
        if alignment==2: ds.TextAlignment = Rhino.DocObjects.TextDisplayAlignment.AboveLine
        if alignment==3: ds.TextAlignment = Rhino.DocObjects.TextDisplayAlignment.InLine
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleTextGap(dimstyle, gap=None):
    """Returns or changes the text gap used by a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      gap[opt] = the new text gap
    Returns:
      if gap is not specified, the current text gap
      if gap is specified, the previous text gap
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.TextGap
    if gap is not None:
        ds.TextGap = gap
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def DimStyleTextHeight(dimstyle, height=None):
    """Returns or changes the text height used by a dimension style
    Parameters:
      dimstyle = the name of an existing dimension style
      height[opt] = the new text height
    Returns:
      if height is not specified, the current text height
      if height is specified, the previous text height
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    rc = ds.TextHeight
    if height:
        ds.TextHeight = height
        ds.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def IsAlignedDimension(object_id):
    "Verifies an object is an aligned dimension object"
    annotation_object = __coerceannotation(object_id)
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    if isinstance(geom, Rhino.Geometry.LinearDimension): return geom.Aligned
    return False


def IsAngularDimension(object_id):
    "Verifies an object is an angular dimension object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    return isinstance(geom, Rhino.Geometry.AngularDimension)


def IsDiameterDimension(object_id):
    "Verifies an object is a diameter dimension object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    if isinstance(geom, Rhino.Geometry.RadialDimension):
        return geom.IsDiameterDimension
    return False


def IsDimension(object_id):
    "Verifies an object is a dimension object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    return isinstance(geom, Rhino.Geometry.AnnotationBase)


def IsDimStyle(dimstyle):
    """Verifies the existance of a dimension style in the document
    Parameters:
      dimstyle = the name of a dimstyle to test for
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    return ds is not None


def IsDimStyleReference(dimstyle):
    """Verifies that an existing dimension style is from a reference file
    Parameters:
      dimstyle = the name of an existing dimension style
    """
    ds = scriptcontext.doc.DimStyles.Find(dimstyle, True)
    if ds is None: return scriptcontext.errorhandler()
    return ds.IsReference


def IsLeader(object_id):
    "Verifies an object is a dimension leader object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    return isinstance(geom, Rhino.Geometry.Leader)


def IsLinearDimension(object_id):
    "Verifies an object is a linear dimension object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    return isinstance(geom, Rhino.Geometry.LinearDimension)


def IsOrdinateDimension(object_id):
    "Verifies an object is an ordinate dimension object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    return isinstance(geom, Rhino.Geometry.OrdinateDimension)


def IsRadialDimension(object_id):
    "Verifies an object is a radial dimension object"
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    return isinstance(geom, Rhino.Geometry.RadialDimension)


def LeaderText(object_id, text=None):
    """Returns or modifies the text string of a dimension leader object
    Parameters:
      object_id = the object's identifier
      text[opt] = the new text string
    Returns:
      if text is not specified, the current text string
      if text is specified, the previous text string
      None on error
    """
    id = rhutil.coerceguid(object_id, True)
    annotation_object = scriptcontext.doc.Objects.Find(id)
    geom = annotation_object.Geometry
    if not isinstance(geom, Rhino.Geometry.Leader):
        return scriptcontext.errorhandler()
    rc = annotation_object.DisplayText
    if text is not None:
        geom.TextFormula = text
        annotation_object.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def RenameDimStyle(oldstyle, newstyle):
    """Renames an existing dimension style
    Parameters:
      oldstyle = the name of an existing dimension style
      newstyle = the new dimension style name
    Returns:
      the new dimension style name if successful
      None on error
    """
    ds = scriptcontext.doc.DimStyles.Find(oldstyle, True)
    if not ds: return scriptcontext.errorhandler()
    ds.Name = newstyle
    if ds.CommitChanges(): return newstyle
    return None

########NEW FILE########
__FILENAME__ = document
import scriptcontext
import Rhino
import System.Enum, System.Drawing.Size
import utility as rhutil

def CreatePreviewImage(filename, view=None, size=None, flags=0, wireframe=False):
    """Creates a bitmap preview image of the current model
    Parameters:
      filename = name of the bitmap file to create
      view[opt] = title of the view. If omitted, the active view is used
      size[opt] = two integers that specify width and height of the bitmap
      flags[opt] = Bitmap creation flags. Can be the combination of:
          1 = honor object highlighting
          2 = draw construction plane
          4 = use ghosted shading
      wireframe[opt] = If True then a wireframe preview image. If False,
          a rendered image will be created
    Returns:
      True or False indicating success or failure
    """
    rhview = scriptcontext.doc.Views.ActiveView
    if view is not None:
        rhview = scriptcontext.doc.Views.Find(view, False)
        if rhview is None: return False
    rhsize = rhview.ClientRectangle.Size
    if size: rhsize = System.Drawing.Size(size[0], size[1])
    ignore_highlights = (flags&1)!=1
    drawcplane = (flags&2)==2
    useghostedshading = (flags&4)==4
    if wireframe:
        return rhview.CreateWireframePreviewImage(filename, rhsize, ignore_highlights, drawcplane)
    else:
        return rhview.CreateShadedPreviewImage(filename, rhsize, ignore_highlights, drawcplane, useghostedshading)


def DocumentModified(modified=None):
    """Returns or sets the document's modified flag. This flag indicates whether
    or not any changes to the current document have been made. NOTE: setting the
    document modified flag to False will prevent the "Do you want to save this
    file..." from displaying when you close Rhino.
    Parameters:
      modified [optional] = the modified state, either True or False
    Returns:
      if no modified state is specified, the current modified state
      if a modified state is specified, the previous modified state
    """
    oldstate = scriptcontext.doc.Modified
    if modified is not None and modified!=oldstate:
        scriptcontext.doc.Modified = modified
    return oldstate


def DocumentName():
    "Returns the name of the currently loaded Rhino document (3DM file)"
    return scriptcontext.doc.Name


def DocumentPath():
    "Returns path of the currently loaded Rhino document (3DM file)"
    return scriptcontext.doc.Path


def EnableRedraw(enable=True):
    """Enables or disables screen redrawing
    Returns: previous screen redrawing state
    """
    old = scriptcontext.doc.Views.RedrawEnabled
    if old!=enable: scriptcontext.doc.Views.RedrawEnabled = enable
    return old


def ExtractPreviewImage(filename, modelname=None):
    """Extracts the bitmap preview image from the specified model (.3dm)
    Parameters:
      filename = name of the bitmap file to create. The extension of
         the filename controls the format of the bitmap file created.
         (.bmp, .tga, .jpg, .jpeg, .pcx, .png, .tif, .tiff)
      modelname [opt] = The model (.3dm) from which to extract the
         preview image. If omitted, the currently loaded model is used.
    Returns:
      True or False indicating success or failure
    """
    return scriptcontext.doc.ExtractPreviewImage(filename, modelname)


def IsDocumentModified():
    "Verifies that the current document has been modified in some way"
    return scriptcontext.doc.Modified


def Notes(newnotes=None):
    """Returns or sets the document's notes. Notes are generally created
    using Rhino's Notes command
    Parameters:
      newnotes[opt] = new notes to set
    Returns:
      if newnotes is omitted, the current notes if successful
      if newnotes is specified, the previous notes if successful
    """
    old = scriptcontext.doc.Notes
    if newnotes is not None: scriptcontext.doc.Notes = newnotes
    return old


def ReadFileVersion():
    """Returns the file version of the current document. Use this function to
    determine which version of Rhino last saved the document. Note, this
    function will not return values from referenced or merged files.
    """
    return scriptcontext.doc.ReadFileVersion()


def Redraw():
    "Redraws all views"
    scriptcontext.doc.Views.Redraw()


def RenderAntialias(style=None):
    """Returns or sets render antialias style
    Parameters:
      style[opt] = level of antialiasing (0=none, 1=normal, 2=best)
    Returns:
      if style is not specified, the current antialias style
      if style is specified, the previous antialias style
    """
    rc = scriptcontext.doc.RenderSettings.AntialiasLevel
    if style==0 or style==1 or style==2:
        settings = scriptcontext.doc.RenderSettings
        settings.AntialiasLevel = style
        scriptcontext.doc.RenderSettings = settings
    return rc


def RenderColor(item, color=None):
    """Returns or sets the render ambient light or background color
    Parameters:
      item = 0=ambient light color, 1=background color
      color[opt] = the new color value. If omitted, the curren item color is returned
    Returns:
      if color is not specified, the current item color
      if color is specified, the previous item color
    """
    if item!=0 and item!=1: raise ValueError("item must be 0 or 1")
    if item==0: rc = scriptcontext.doc.RenderSettings.AmbientLight
    else: rc = scriptcontext.doc.RenderSettings.BackgroundColorTop
    if color is not None:
        color = rhutil.coercecolor(color, True)
        settings = scriptcontext.doc.RenderSettings
        if item==0: settings.AmbientLight = color
        else: settings.BackgroundColorTop = color
        scriptcontext.doc.RenderSettings = settings
        scriptcontext.doc.Views.Redraw()
    return rc


def RenderResolution(resolution=None):
    """Returns or sets the render resolution
    Parameters:
      resolution[opt] = width and height of render
    Returns:
      if resolution is not specified, the current resolution width,height
      if resolution is specified, the previous resolution width, height
    """
    rc = scriptcontext.doc.RenderSettings.ImageSize
    if resolution:
        settings = scriptcontext.doc.RenderSettings
        settings.ImageSize = System.Drawing.Size(resolution[0], resolution[1])
        scriptcontext.doc.RenderSettings = settings
    return rc.Width, rc.Height


def RenderSettings(settings=None):
    """Returns or sets render settings
    Parameters:
      settings[opt] = render settings to modify.
        0=none,
        1=create shadows,
        2=use lights on layers that are off,
        4=render curves and isocurves,
        8=render dimensions and text
    Returns:
      if settings are not specified, the current render settings
      if settings are specified, the previous render settings
    """
    rc = 0
    rendersettings = scriptcontext.doc.RenderSettings
    if rendersettings.ShadowmapLevel: rc+=1
    if rendersettings.UseHiddenLights: rc+=2
    if rendersettings.RenderCurves: rc+=4
    if rendersettings.RenderAnnotations: rc+=8
    if settings is not None:
        rendersettings.ShadowmapLevel = (settings & 1)
        rendersettings.UseHiddenLights = (settings & 2)==2
        rendersettings.RenderCurves = (settings & 4)==4
        rendersettings.RenderAnnotations = (settings & 8)==8
        scriptcontext.doc.RenderSettings = rendersettings
    return rc


def UnitAbsoluteTolerance(tolerance=None, in_model_units=True):
    """Resturns or sets the document's absolute tolerance. Absolute tolerance
    is measured in drawing units. See Rhino's document properties command
    (Units and Page Units Window) for details
    Parameters:
      tolerance [opt] = the absolute tolerance to set
      in_model_units[opt] = Return or modify the document's model units (True)
                            or the document's page units (False)
    Returns:
      if tolerance is not specified, the current absolute tolerance
      if tolerance is specified, the previous absolute tolerance
    """
    if in_model_units:
        rc = scriptcontext.doc.ModelAbsoluteTolerance
        if tolerance is not None:
            scriptcontext.doc.ModelAbsoluteTolerance = tolerance
    else:
        rc = scriptcontext.doc.PageAbsoluteTolerance
        if tolerance is not None:
            scriptcontext.doc.PageAbsoluteTolerance = tolerance
    return rc


def UnitAngleTolerance(angle_tolerance_degrees=None, in_model_units=True):
    """Returns or sets the document's angle tolerance. Angle tolerance is
    measured in degrees. See Rhino's DocumentProperties command
    (Units and Page Units Window) for details
    Parameters:
      angle_tolerance_degrees [opt] = the angle tolerance to set
      in_model_units [opt] = Return or modify the document's model units (True)
                             or the document's page units (False)
    Returns:
      if angle_tolerance_degrees is not specified, the current angle tolerance
      if angle_tolerance_degrees is specified, the previous angle tolerance
    """
    if in_model_units:
        rc = scriptcontext.doc.ModelAngleToleranceDegrees
        if angle_tolerance_degrees is not None:
            scriptcontext.doc.ModelAngleToleranceDegrees = angle_tolerance_degrees
    else:
        rc = scriptcontext.doc.PageAngleToleranceDegrees
        if angle_tolerance_degrees is not None:
            scriptcontext.doc.PageAngleToleranceDegrees = angle_tolerance_degrees
    return rc


def UnitRelativeTolerance(relative_tolerance=None, in_model_units=True):
    """Returns or sets the document's relative tolerance. Relative tolerance
    is measured in percent. See Rhino's DocumentProperties command
    (Units and Page Units Window) for details
    Parameters:
      relative_tolerance [opt] = the relative tolerance in percent
      in_model_units [opt] = Return or modify the document's model units (True)
                             or the document's page units (False)
    Returns:
      if relative_tolerance is not specified, the current tolerance in percent
      if relative_tolerance is specified, the previous tolerance in percent
    """
    if in_model_units:
        rc = scriptcontext.doc.ModelRelativeTolerance
        if relative_tolerance is not None:
            scriptcontext.doc.ModelRelativeTolerance = relative_tolerance
    else:
        rc = scriptcontext.doc.PageRelativeTolerance
        if relative_tolerance is not None:
            scriptcontext.doc.PageRelativeTolerance = relative_tolerance
    return rc


def UnitScale(to_system, from_system=None):
  """Returns the scale factor for changing between unit systems.
  Parameters:
    to_system = The unit system to convert to. The unit systems are are:
       0 - No unit system
       1 - Microns (1.0e-6 meters)
       2 - Millimeters (1.0e-3 meters)
       3 - Centimeters (1.0e-2 meters)
       4 - Meters
       5 - Kilometers (1.0e+3 meters)
       6 - Microinches (2.54e-8 meters, 1.0e-6 inches)
       7 - Mils (2.54e-5 meters, 0.001 inches)
       8 - Inches (0.0254 meters)
       9 - Feet (0.3408 meters, 12 inches)
      10 - Miles (1609.344 meters, 5280 feet)
      11 - *Reserved for custom Unit System*
      12 - Angstroms (1.0e-10 meters)
      13 - Nanometers (1.0e-9 meters)
      14 - Decimeters (1.0e-1 meters)
      15 - Dekameters (1.0e+1 meters)
      16 - Hectometers (1.0e+2 meters)
      17 - Megameters (1.0e+6 meters)
      18 - Gigameters (1.0e+9 meters)
      19 - Yards (0.9144  meters, 36 inches)
      20 - Printer point (1/72 inches, computer points)
      21 - Printer pica (1/6 inches, (computer picas)
      22 - Nautical mile (1852 meters)
      23 - Astronomical (1.4959787e+11)
      24 - Lightyears (9.46073e+15 meters)
      25 - Parsecs (3.08567758e+16)
    from_system [opt] = the unit system to convert from (see above). If omitted,
        the document's current unit system is used
  Returns:
    the scale factor for changing between unit systems
  """
  if from_system is None:
      from_system = scriptcontext.doc.ModelUnitSystem
  if type(from_system) is int:
      from_system = System.Enum.ToObject(Rhino.UnitSystem, from_system)
  if type(to_system) is int:
      to_system = System.Enum.ToObject(Rhino.UnitSystem, to_system)
  return Rhino.RhinoMath.UnitScale(from_system, to_system)


def UnitSystem(unit_system=None, scale=False, in_model_units=True):
    """Returns or sets the document's units system. See Rhino's DocumentProperties
    command (Units and Page Units Window) for details
    Parameters:
      unit_system = The unit system to set the document to. The unit systems are:
         0 - No unit system
         1 - Microns (1.0e-6 meters)
         2 - Millimeters (1.0e-3 meters)
         3 - Centimeters (1.0e-2 meters)
         4 - Meters
         5 - Kilometers (1.0e+3 meters)
         6 - Microinches (2.54e-8 meters, 1.0e-6 inches)
         7 - Mils (2.54e-5 meters, 0.001 inches)
         8 - Inches (0.0254 meters)
         9 - Feet (0.3408 meters, 12 inches)
        10 - Miles (1609.344 meters, 5280 feet)
        11 - *Reserved for custom Unit System*
        12 - Angstroms (1.0e-10 meters)
        13 - Nanometers (1.0e-9 meters)
        14 - Decimeters (1.0e-1 meters)
        15 - Dekameters (1.0e+1 meters)
        16 - Hectometers (1.0e+2 meters)
        17 - Megameters (1.0e+6 meters)
        18 - Gigameters (1.0e+9 meters)
        19 - Yards (0.9144  meters, 36 inches)
        20 - Printer point (1/72 inches, computer points)
        21 - Printer pica (1/6 inches, (computer picas)
        22 - Nautical mile (1852 meters)
        23 - Astronomical (1.4959787e+11)
        24 - Lightyears (9.46073e+15 meters)
        25 - Parsecs (3.08567758e+16)
      scale [opt] = Scale existing geometry based on the new unit system.
          If not specified, any existing geometry is not scaled (False)
      in_model_units [opt] = Return or modify the document's model units (True)
          or the document's page units (False). The default is True.
    Returns:
      if unit_system is no specified, then the current unit system
      if unit_system is specified, then the previous unit system
      None on error
    """
    if (unit_system is not None and (unit_system<1 or unit_system>25)):
        raise ValueError("unit_system value of %s is not valid"%unit_system)
    if in_model_units:
        rc = int(scriptcontext.doc.ModelUnitSystem)
        if unit_system is not None:
            unit_system = System.Enum.ToObject(Rhino.UnitSystem, unit_system)
            scriptcontext.doc.AdjustModelUnitSystem(unit_system, scale)
    else:
        rc = int(scriptcontext.doc.PageUnitSystem)
        if unit_system is not None:
            unit_system = System.Enum.ToObject(Rhino.UnitSystem, unit_system)
            scriptcontext.doc.AdjustPageUnitSystem(unit_system, scale)
    return rc

########NEW FILE########
__FILENAME__ = geometry
import scriptcontext
import utility as rhutil
import Rhino
import System.Guid, System.Array


def AddClippingPlane(plane, u_magnitude, v_magnitude, views=None):
    """Create a clipping plane for visibly clipping away geometry in a specific
    view. Note, clipping planes are infinite
    Parameters:
      plane = the plane
      u_magnitude, v_magnitude = size of the plane
      views[opt]= Titles or ids the the view(s) to clip. If omitted, the active
        view is used.
    Returns:
      object identifier on success
      None on failure  
    """
    viewlist = []
    if views:
        if type(views) is System.Guid:
            viewlist.append(views)
        elif type(views) is str:
            modelviews = scriptcontext.doc.Views.GetViewList(True, False)
            rc = None
            for item in modelviews:
                if item.ActiveViewport.Name == views:
                    id = item.ActiveViewportID
                    rc = AddClippingPlane(plane, u_magnitude, v_magnitude, id)
                    break
            return rc
        else:
            if type(views[0]) is System.Guid:
                viewlist = views
            elif( type(views[0]) is str ):
                modelviews = scriptcontext.doc.Views.GetViewList(True,False)
                for viewname in views:
                    for item in modelviews:
                        if item.ActiveViewport.Name==viewname:
                            viewlist.append(item.ActiveViewportID)
                            break
    else:
        viewlist.append(scriptcontext.doc.Views.ActiveView.ActiveViewportID)
    if not viewlist: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddClippingPlane(plane, u_magnitude, v_magnitude, viewlist)
    if rc==System.Guid.Empty: raise Exception("unable to add clipping plane to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPoint(point, y=None, z=None):
    """Adds point object to the document
    Parameters:
      point = x,y,z location of point to add
    Returns:
      Guid for the object that was added to the doc
    """
    if y is not None and z is not None: point = Rhino.Geometry.Point3d(point,y,z)
    point = rhutil.coerce3dpoint(point, True)
    rc = scriptcontext.doc.Objects.AddPoint(point)
    if rc==System.Guid.Empty: raise Exception("unable to add point to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPointCloud(points, colors=None):
    """Adds point cloud object to the document
    Parameters:
      points = list of values where every multiple of three represents a point
      colors[opt] = list of colors to apply to each point
    Returns:
      identifier of point cloud on success
    """
    points = rhutil.coerce3dpointlist(points, True)
    if colors and len(colors)==len(points):
        pc = Rhino.Geometry.PointCloud()
        for i in range(len(points)):
            color = rhutil.coercecolor(colors[i],True)
            pc.Add(points[i],color)
        points = pc
    rc = scriptcontext.doc.Objects.AddPointCloud(points)
    if rc==System.Guid.Empty: raise Exception("unable to add point cloud to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPoints(points):
    """Adds one or more point objects to the document
    Parameters:
      points = list of points
    Returns:
      list of Guid identifiers of the new objects on success
    """
    points = rhutil.coerce3dpointlist(points, True)
    rc = [scriptcontext.doc.Objects.AddPoint(point) for point in points]
    scriptcontext.doc.Views.Redraw()
    return rc


def AddText(text, point_or_plane, height=1.0, font="Arial", font_style=0, justification=None):
    """Adds a text string to the document
    Parameters:
      text = the text to display
      point_or_plane = a 3-D point or the plane on which the text will lie.
          The origin of the plane will be the origin point of the text
      height [opt] = the text height
      font [opt] = the text font
      font_style[opt] = any of the following flags
         0 = normal
         1 = bold
         2 = italic
         3 = bold and italic
      justification[opt] = text justification (see help for values)
    Returns:
      Guid for the object that was added to the doc on success
      None on failure
    """
    if not text: raise ValueError("text invalid")
    if not isinstance(text, str): text = str(text)
    point = rhutil.coerce3dpoint(point_or_plane)
    plane = None
    if not point: plane = rhutil.coerceplane(point_or_plane, True)
    if not plane:
        plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
        plane.Origin = point
    bold = (1==font_style or 3==font_style)
    italic = (2==font_style or 3==font_style)
    id = None
    if justification is None:
        id = scriptcontext.doc.Objects.AddText(text, plane, height, font, bold, italic)
    else:
        just = System.Enum.ToObject(Rhino.Geometry.TextJustification, justification)
        id = scriptcontext.doc.Objects.AddText(text, plane, height, font, bold, italic, just)
    if id==System.Guid.Empty: raise ValueError("unable to add text to document")
    scriptcontext.doc.Views.Redraw()
    return id


def AddTextDot(text, point):
    """Adds an annotation text dot to the document.
    Parameters:
      text = string in dot
      point = A 3D point identifying the origin point.
    Returns:
      The identifier of the new object if successful
      None if not successful, or on error
    """
    point = rhutil.coerce3dpoint(point, True)
    if not isinstance(text, str): text = str(text)
    rc = scriptcontext.doc.Objects.AddTextDot(text, point)
    if id==System.Guid.Empty: raise ValueError("unable to add text dot to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def Area(object_id):
    "Compute the area of a closed curve, hatch, surface, polysurface, or mesh"
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    mp = Rhino.Geometry.AreaMassProperties.Compute(rhobj.Geometry)
    if mp is None: raise Exception("unable to compute area mass properties")
    return mp.Area


def BoundingBox(objects, view_or_plane=None, in_world_coords=True):
    """Returns either world axis-aligned or a construction plane axis-aligned
    bounding box of an object or of several objects
    Parameters:
      objects = The identifiers of the objects
      view_or_plane[opt] = Title or id of the view that contains the
          construction plane to which the bounding box should be aligned -or-
          user defined plane. If omitted, a world axis-aligned bounding box
          will be calculated
      in_world_coords[opt] = return the bounding box as world coordinates or
          construction plane coordinates. Note, this option does not apply to
          world axis-aligned bounding boxes.
    Returns:
      Eight 3D points that define the bounding box. Points returned in counter-
      clockwise order starting with the bottom rectangle of the box.
      None on error
    """
    def __objectbbox(object, xform):
        geom = rhutil.coercegeometry(object, False)
        if not geom:
            pt = rhutil.coerce3dpoint(object, True)
            return Rhino.Geometry.BoundingBox(pt,pt)
        if xform: return geom.GetBoundingBox(xform)
        return geom.GetBoundingBox(True)

    xform = None
    plane = rhutil.coerceplane(view_or_plane)
    if plane is None and view_or_plane:
        view = view_or_plane
        modelviews = scriptcontext.doc.Views.GetStandardRhinoViews()
        for item in modelviews:
            viewport = item.MainViewport
            if type(view) is str and viewport.Name==view:
                plane = viewport.ConstructionPlane()
                break
            elif type(view) is System.Guid and viewport.Id==view:
                plane = viewport.ConstructionPlane()
                break
        if plane is None: return scriptcontext.errorhandler()
    if plane:
        xform = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)
    bbox = Rhino.Geometry.BoundingBox.Empty
    if type(objects) is list or type(objects) is tuple:
        for object in objects:
            objectbbox = __objectbbox(object, xform)
            bbox = Rhino.Geometry.BoundingBox.Union(bbox,objectbbox)
    else:
        objectbbox = __objectbbox(objects, xform)
        bbox = Rhino.Geometry.BoundingBox.Union(bbox,objectbbox)
    if not bbox.IsValid: return scriptcontext.errorhandler()

    corners = list(bbox.GetCorners())
    if in_world_coords and plane is not None:
        plane_to_world = Rhino.Geometry.Transform.ChangeBasis(plane, Rhino.Geometry.Plane.WorldXY)
        for pt in corners: pt.Transform(plane_to_world)
    return corners


def ExplodeText(text_id, delete=False):
    """Creates outline curves for a given text entity
    Parameters:
      text_id: identifier of Text object to explode
      delete[opt]: delete the text object after the curves have been created
    Returns:
      list of outline curves
    """
    rhobj = rhutil.coercerhinoobject(text_id, True, True)
    curves = rhobj.Geometry.Explode()
    attr = rhobj.Attributes
    rc = [scriptcontext.doc.Objects.AddCurve(curve,attr) for curve in curves]
    if delete: scriptcontext.doc.Objects.Delete(rhobj,True)
    scriptcontext.doc.Views.Redraw()
    return rc


def IsClippingPlane(object_id):
    """Verifies that an object is a clipping plane object
    Parameters:
      object_id: the object's identifier
    Returns:
      True if the object with a given id is a clipping plane
    """
    cp = rhutil.coercegeometry(object_id)
    return isinstance(cp, Rhino.Geometry.ClippingPlaneSurface)


def IsPoint(object_id):
    """Verifies an object is a point object.
    Parameters:
      object_id: the object's identifier
    Returns:
      True if the object with a given id is a point
    """
    p = rhutil.coercegeometry(object_id)
    return isinstance(p, Rhino.Geometry.Point)


def IsPointCloud(object_id):
    """Verifies an object is a point cloud object.
    Parameters:
      object_id: the object's identifier
    Returns:
      True if the object with a given id is a point cloud
    """
    pc = rhutil.coercegeometry(object_id)
    return isinstance(pc, Rhino.Geometry.PointCloud)


def IsText(object_id):
    """Verifies an object is a text object.
    Parameters:
      object_id: the object's identifier
    Returns:
      True if the object with a given id is a text object
    """
    text = rhutil.coercegeometry(object_id)
    return isinstance(text, Rhino.Geometry.TextEntity)


def IsTextDot(object_id):
    """Verifies an object is a text dot object.
    Parameters:
      object_id: the object's identifier
    Returns:
      True if the object with a given id is a text dot object
    """
    td = rhutil.coercegeometry(object_id)
    return isinstance(td, Rhino.Geometry.TextDot)


def PointCloudCount(object_id):
    """Returns the point count of a point cloud object
    Parameters:
      object_id: the point cloud object's identifier
    Returns:
      number of points if successful
    """
    pc = rhutil.coercegeometry(object_id, True)
    if isinstance(pc, Rhino.Geometry.PointCloud): return pc.Count


def PointCloudHasHiddenPoints(object_id):
    """Verifies that a point cloud has hidden points
    Parameters:
      object_id: the point cloud object's identifier
    Returns:
      True if cloud has hidden points, otherwise False
    """
    pc = rhutil.coercegeometry(object_id, True)
    if isinstance(pc, Rhino.Geometry.PointCloud): return pc.HiddenPointCount>0


def PointCloudHasPointColors(object_id):
    """Verifies that a point cloud has point colors
    Parameters:
      object_id: the point cloud object's identifier
    Returns:
      True if cloud has point colors, otherwise False
    """
    pc = rhutil.coercegeometry(object_id, True)
    if isinstance(pc, Rhino.Geometry.PointCloud): return pc.ContainsColors


def PointCloudHidePoints(object_id, hidden=[]):
    """Returns or modifies the hidden points of a point cloud object
    Parameters:
      object_id: the point cloud object's identifier
      hidden: list of hidden values if you want to hide certain points
    Returns:
      List of point cloud hidden states
    """
    rhobj = rhutil.coercerhinoobject(object_id)
    if rhobj: pc = rhobj.Geometry
    else: pc = rhutil.coercegeometry(object_id, True)
    if isinstance(pc, Rhino.Geometry.PointCloud):
        rc = None
        if pc.ContainsHiddenFlags: rc = [item.Hidden for item in pc]
        if hidden is None:
            pc.ClearHiddenFlags()
        elif len(hidden)==pc.Count:
            for i in range(pc.Count): pc[i].Hidden = hidden[i]
        if rhobj:
            rhobj.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc


def PointCloudPointColors(object_id, colors=[]):
    """Returns or modifies the point colors of a point cloud object
    Parameters:
      object_id: the point cloud object's identifier
      colors: list of color values if you want to adjust colors
    Returns:
      List of point cloud colors
    """
    rhobj = rhutil.coercerhinoobject(object_id)
    if rhobj: pc = rhobj.Geometry
    else: pc = rhutil.coercegeometry(object_id, True)
    if isinstance(pc, Rhino.Geometry.PointCloud):
        rc = None
        if pc.ContainsColors: rc = [item.Color for item in pc]
        if colors is None:
            pc.ClearColors()
        elif len(colors)==pc.Count:
            for i in range(pc.Count): pc[i].Color = rhutil.coercecolor(colors[i])
        if rhobj:
            rhobj.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc


def PointCloudPoints(object_id):
    """Returns the points of a point cloud object
    Parameters:
      object_id: the point cloud object's identifier
    Returns:
      list of points if successful
    """
    pc = rhutil.coercegeometry(object_id, True)
    if isinstance(pc, Rhino.Geometry.PointCloud): return pc.GetPoints()


def PointCoordinates(object_id, point=None):
    """Returns or modifies the X, Y, and Z coordinates of a point object
    Parameters:
      object_id = The identifier of a point object
      point[opt] = A new 3D point location.
    Returns:
      If point is not specified, the current 3-D point location
      If point is specified, the previous 3-D point location
    """
    point_geometry = rhutil.coercegeometry(object_id, True)
    if isinstance(point_geometry, Rhino.Geometry.Point):
        rc = point_geometry.Location
        if point:
            point = rhutil.coerce3dpoint(point, True)
            id = rhutil.coerceguid(object_id, True)
            scriptcontext.doc.Objects.Replace(id, point)
            scriptcontext.doc.Views.Redraw()
        return rc


def TextDotFont(object_id, fontface=None):
    """Returns or modified the font of a text dot
    Parameters:
      object_id = identifier of a text dot object
      fontface[opt] = new font face name
    Returns:
      If font is not specified, the current text dot font
      If font is specified, the previous text dot font
      None on error
    """
    textdot = rhutil.coercegeometry(object_id, True)
    if isinstance(textdot, Rhino.Geometry.TextDot):
        rc = textdot.FontFace
        if fontface:
            textdot.FontFace = fontface
            id = rhutil.coerceguid(object_id, True)
            scriptcontext.doc.Objects.Replace(id, textdot)
            scriptcontext.doc.Views.Redraw()
        return rc


def TextDotHeight(object_id, height=None):
    """Returns or modified the font height of a text dot
    Parameters:
      object_id = identifier of a text dot object
      height[opt] = new font height
    Returns:
      If height is not specified, the current text dot height
      If height is specified, the previous text dot height
      None on error
    """
    textdot = rhutil.coercegeometry(object_id, True)
    if isinstance(textdot, Rhino.Geometry.TextDot):
        rc = textdot.FontHeight
        if height and height>0:
            textdot.FontHeight = height
            id = rhutil.coerceguid(object_id, True)
            scriptcontext.doc.Objects.Replace(id, textdot)
            scriptcontext.doc.Views.Redraw()
        return rc


def TextDotPoint(object_id, point=None):
    """Returns or modifies the location, or insertion point, on a text dot object
    Parameters:
      object_id = identifier of a text dot object
      point[opt] = A new 3D point location.
    Returns:
      If point is not specified, the current 3-D text dot location
      If point is specified, the previous 3-D text dot location
      None if not successful, or on error
    """
    textdot = rhutil.coercegeometry(object_id, True)
    if isinstance(textdot, Rhino.Geometry.TextDot):
        rc = textdot.Point
        if point:
            textdot.Point = rhutil.coerce3dpoint(point, True)
            id = rhutil.coerceguid(object_id, True)
            scriptcontext.doc.Objects.Replace(id, textdot)
            scriptcontext.doc.Views.Redraw()
        return rc


def TextDotText(object_id, text=None):
    """Returns or modifies the text on a text dot object
    Parameters:
      object_id =tThe identifier of a text dot object
      text [opt] = a new string for the dot
    Returns:
      If text is not specified, the current text dot text
      If text is specified, the previous text dot text
      None if not successful, or on error
    """
    textdot = rhutil.coercegeometry(object_id, True)
    if isinstance(textdot, Rhino.Geometry.TextDot):
        rc = textdot.Text
        if text is not None:
            if not isinstance(text, str): text = str(text)
            textdot.Text = text
            id = rhutil.coerceguid(object_id, True)
            scriptcontext.doc.Objects.Replace(id, textdot)
            scriptcontext.doc.Views.Redraw()
        return rc


def TextObjectFont(object_id, font=None):
    """Returns of modifies the font used by a text object
    Parameters:
      object_id = the identifier of a text object
      font [opt] = the new font face name
    Returns:
      if a font is not specified, the current font face name
      if a font is specified, the previous font face name
      None if not successful, or on error
    """
    annotation = rhutil.coercegeometry(object_id, True)
    if not isinstance(annotation, Rhino.Geometry.TextEntity):
        return scriptcontext.errorhandler()
    fontdata = scriptcontext.doc.Fonts[annotation.FontIndex]
    if fontdata is None: return scriptcontext.errorhandler()
    rc = fontdata.FaceName
    if font:
        index = scriptcontext.doc.Fonts.FindOrCreate( font, fontdata.Bold, fontdata.Italic )
        annotation.FontIndex = index
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, annotation)
        scriptcontext.doc.Views.Redraw()
    return rc


def TextObjectHeight(object_id, height=None):
    """Returns or modifies the height of a text object
    Parameters:
      object_id = the identifier of a text object
      height[opt] = the new text height.
    Returns:
      if height is not specified, the current text height
      if height is specified, the previous text height
      None if not successful, or on error
    """
    annotation = rhutil.coercegeometry(object_id, True)
    if not isinstance(annotation, Rhino.Geometry.TextEntity):
        return scriptcontext.errorhandler()
    rc = annotation.TextHeight
    if height:
        annotation.TextHeight = height
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, annotation)
        scriptcontext.doc.Views.Redraw()
    return rc


def TextObjectPlane(object_id, plane=None):
    """Returns or modifies the plane used by a text object
    Parameters:
      object_id = the identifier of a text object
      plane[opt] = the new text object plane
    Returns:
      if a plane is not specified, the current plane if successful
      if a plane is specified, the previous plane if successful
      None if not successful, or on Error
    """
    annotation = rhutil.coercegeometry(object_id, True)
    if not isinstance(annotation, Rhino.Geometry.TextEntity):
        return scriptcontext.errorhandler()
    rc = annotation.Plane
    if plane:
        annotation.Plane = rhutil.coerceplane(plane, True)
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, annotation)
        scriptcontext.doc.Views.Redraw()
    return rc


def TextObjectPoint(object_id, point=None):
    """Returns or modifies the location of a text object
    Parameters:
      object_id = the identifier of a text object
      point[opt] = the new text object location
    Returns:
      if point is not specified, the 3D point identifying the current location
      if point is specified, the 3D point identifying the previous location
      None if not successful, or on Error
    """
    text = rhutil.coercegeometry(object_id, True)
    if not isinstance(text, Rhino.Geometry.TextEntity):
        return scriptcontext.errorhandler()
    plane = text.Plane
    rc = plane.Origin
    if point:
        plane.Origin = rhutil.coerce3dpoint(point, True)
        text.Plane = plane
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, text)
        scriptcontext.doc.Views.Redraw()
    return rc


def TextObjectStyle(object_id, style=None):
    """Returns or modifies the font style of a text object
    Parameters:
      object_id = the identifier of a text object
      style [opt] = the font style. Can be any of the following flags
         0 = Normal
         1 = Bold
         2 = Italic
    Returns:
      if style is not specified, the current font style
      if style is specified, the previous font style
      None if not successful, or on Error
    """
    annotation = rhutil.coercegeometry(object_id, True)
    if not isinstance(annotation, Rhino.Geometry.TextEntity):
        return scriptcontext.errorhandler()
    fontdata = scriptcontext.doc.Fonts[annotation.FontIndex]
    if fontdata is None: return scriptcontext.errorhandler()
    rc = 0
    if fontdata.Bold: rc += 1
    if fontdata.Italic: rc += 2
    if style is not None and style!=rc:
        index = scriptcontext.doc.Fonts.FindOrCreate( fontdata.FaceName, (style&1)==1, (style&2)==2 )
        annotation.FontIndex = index
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, annotation)
        scriptcontext.doc.Views.Redraw()
    return rc


def TextObjectText(object_id, text=None):
    """Returns or modifies the text string of a text object.
    Parameters:
      object_id = the identifier of a text object
      text [opt] = a new text string
    Returns:
      if text is not specified, the current string value if successful
      if text is specified, the previous string value if successful
      None if not successful, or on error
    """
    annotation = rhutil.coercegeometry(object_id, True)
    if not isinstance(annotation, Rhino.Geometry.TextEntity):
        return scriptcontext.errorhandler()
    rc = annotation.Text
    if text:
        if not isinstance(text, str): text = str(text)
        annotation.Text = text
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, annotation)
        scriptcontext.doc.Views.Redraw()
    return rc

########NEW FILE########
__FILENAME__ = grips
import utility as rhutil
import scriptcontext
import Rhino


def EnableObjectGrips(object_id, enable=True):
    """Enables or disables an object's grips. For curves and surfaces, these are
    also called control points.
    Parameters:
      object_id = identifier of the object
      enable [opt] = if True, the specified object's grips will be turned on.
        Otherwise, they will be turned off
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if enable!=rhobj.GripsOn:
        rhobj.GripsOn = enable
        scriptcontext.doc.Views.Redraw()


def GetObjectGrip(message=None, preselect=False, select=False):
    """Prompts the user to pick a single object grip
    Parameters:
      message [opt] = prompt for picking
      preselect [opt] = allow for selection of pre-selected object grip.
      select [opt] = select the picked object grip.
    Returns:
      tuple defining a grip record.
        grip_record[0] = identifier of the object that owns the grip
        grip_record[1] = index value of the grip
        grip_record[2] = location of the grip
      None on error
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    rc, grip = Rhino.Input.RhinoGet.GetGrip(message)
    if rc!=Rhino.Commands.Result.Success: return scriptcontext.errorhandler()
    if select:
        grip.Select(True, True)
        scriptcontext.doc.Views.Redraw()
    return grip.OwnerId, grip.Index, grip.CurrentLocation


def GetObjectGrips(message=None, preselect=False, select=False):
    """Prompts user to pick one or more object grips from one or more objects.
    Parameters:
      message [opt] = prompt for picking
      preselect [opt] = allow for selection of pre-selected object grips
      select [opt] = select the picked object grips
    Returns:
      list containing one or more grip records. Each grip record is a tuple
        grip_record[0] = identifier of the object that owns the grip
        grip_record[1] = index value of the grip
        grip_record[2] = location of the grip
      None on error
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    getrc, grips = Rhino.Input.RhinoGet.GetGrips(message)
    if getrc!=Rhino.Commands.Result.Success or not grips:
        return scriptcontext.errorhandler()
    rc = []
    for grip in grips:
        id = grip.OwnerId
        index = grip.Index
        location = grip.CurrentLocation
        rc.append((id, index, location))
        if select: grip.Select(True, True)
    if select: scriptcontext.doc.Views.Redraw()
    return rc


def __neighborgrip(i, object_id, index, direction, enable):
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    grips = rhobj.GetGrips()
    if not grips or len(grips)<=index: return scriptcontext.errorhandler()
    grip = grips[index]
    next_grip=None
    if direction==0:
        next_grip = grip.NeighborGrip(i,0,0,False)
    else:
        next_grip = grip.NeighborGrip(0,i,0,False)
    if next_grip and enable:
        next_grip.Select(True)
        scriptcontext.doc.Views.Redraw()
    return next_grip


def NextObjectGrip(object_id, index, direction=0, enable=True):
    """Returns the next grip index from a specified grip index of an object
    Parameters:
      object_id = identifier of the object
      index = zero based grip index from which to get the next grip index
      direction[opt] = direction to get the next grip index (0=U, 1=V)
      enable[opt] = if True, the next grip index found will be selected
    Returns:
      index of the next grip on success, None on failure
    """
    return __neighborgrip(1, object_id, index, direction, enable)


def ObjectGripCount(object_id):
    """Returns number of grips owned by an object
    Parameters:
      object_id = identifier of the object
    Returns:
      number of grips if successful
      None on error  
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    grips = rhobj.GetGrips()
    if not grips: return scriptcontext.errorhandler()
    return grips.Length


def ObjectGripLocation(object_id, index, point=None):
    """Returns or modifies the location of an object's grip
    Parameters:
      object_id = identifier of the object
      index = index of the grip to either query or modify
      point [opt] = 3D point defining new location of the grip
    Returns:
      if point is not specified, the current location of the grip referenced by index
      if point is specified, the previous location of the grip referenced by index
      None on error
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return scriptcontext.errorhandler()
    grips = rhobj.GetGrips()
    if not grips or index<0 or index>=grips.Length:
        return scriptcontext.errorhandler()
    grip = grips[index]
    rc = grip.CurrentLocation
    if point:
        grip.CurrentLocation = rhutil.coerce3dpoint(point, True)
        scriptcontext.doc.Objects.GripUpdate(rhobj, True)
        scriptcontext.doc.Views.Redraw()
    return rc


def ObjectGripLocations(object_id, points=None):
    """Returns or modifies the location of all grips owned by an object. The
    locations of the grips are returned in a list of Point3d with each position
    in the list corresponding to that grip's index. To modify the locations of
    the grips, you must provide a list of points that contain the same number
    of points at grips
    Parameters:
      object_id = identifier of the object
      points [opt] = list of 3D points identifying the new grip locations
    Returns:
      if points is not specified, the current location of all grips
      if points is specified, the previous location of all grips
      None if not successful
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return scriptcontext.errorhandler()
    grips = rhobj.GetGrips()
    if grips is None: return scriptcontext.errorhandler()
    rc = [grip.CurrentLocation for grip in grips]
    if points and len(points)==len(grips):
        points = rhutil.coerce3dpointlist(points, True)
        for i, grip in enumerate(grips):
            point = points[i]
            grip.CurrentLocation = point
        scriptcontext.doc.Objects.GripUpdate(rhobj, True)
        scriptcontext.doc.Views.Redraw()
    return rc


def ObjectGripsOn(object_id):
    """Verifies that an object's grips are turned on
    Parameters:
      object_id = identifier of the object
    Returns:
      True or False indcating Grips state
      None on error
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.GripsOn


def ObjectGripsSelected(object_id):
    """Verifies that an object's grips are turned on and at least one grip
    is selected
    Parameters:
      object_id = identifier of the object
    Returns:
      True or False indicating success or failure
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return False
    grips = rhobj.GetGrips()
    if grips is None: return False
    for grip in grips:
        if grip.IsSelected(False): return True
    return False


def PrevObjectGrip(object_id, index, direction=0, enable=True):
    """Returns the prevoius grip index from a specified grip index of an object
    Parameters:
      object_id = identifier of the object
      index = zero based grip index from which to get the previous grip index
      direction[opt] = direction to get the next grip index (0=U, 1=V)
      enable[opt] = if True, the next grip index found will be selected
    Returns:
      index of the next grip on success, None on failure
    """
    return __neighborgrip(-1, object_id, index, direction, enable)


def SelectedObjectGrips(object_id):
    """Returns a list of grip indices indentifying an object's selected grips
    Parameters:
      object_id = identifier of the object
    Returns:
      list of indices on success
      None on failure or if no grips are selected
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return None
    grips = rhobj.GetGrips()
    rc = []
    if grips:
        for i in xrange(grips.Length):
            if grips[i].IsSelected(False): rc.append(i)
    return rc


def SelectObjectGrip(object_id, index):
    """Selects a single grip owned by an object. If the object's grips are
    not turned on, the grips will not be selected
    Parameters:
      object_id = identifier of the object
      index = index of the grip to select
    Returns:
      True or False indicating success or failure
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return False
    grips = rhobj.GetGrips()
    if grips is None: return False
    if index<0 or index>=grips.Length: return False
    grip = grips[index]
    if grip.Select(True,True)>0:
        scriptcontext.doc.Views.Redraw()
        return True
    return False


def SelectObjectGrips(object_id):
    """Selects an object's grips. If the object's grips are not turned on,
    they will not be selected
    Parameters:
      object_id = identifier of the object
    Returns:
      Number of grips selected on success
      None on failure
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return scriptcontext.errorhandler()
    grips = rhobj.GetGrips()
    if grips is None: return scriptcontext.errorhandler()
    count = 0
    for grip in grips:
        if grip.Select(True,True)>0: count+=1
    if count>0:
        scriptcontext.doc.Views.Redraw()
        return count
    return scriptcontext.errorhandler()


def UnselectObjectGrip(object_id, index):
    """Unselects a single grip owned by an object. If the object's grips are
    not turned on, the grips will not be unselected
    Parameters:
      object_id = identifier of the object
      index = index of the grip to unselect
    Returns:
      True or False indicating success or failure
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return False
    grips = rhobj.GetGrips()
    if grips is None: return False
    if index<0 or index>=grips.Length: return False
    grip = grips[index]
    if grip.Select(False)==0:
        scriptcontext.doc.Views.Redraw()
        return True
    return False


def UnselectObjectGrips(object_id):
    """Unselects an object's grips. Note, the grips will not be turned off.
    Parameters:
      object_id = identifier of the object
    Returns:
      Number of grips unselected on success
      None on failure
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if not rhobj.GripsOn: return scriptcontext.errorhandler()
    grips = rhobj.GetGrips()
    if grips is None: return scriptcontext.errorhandler()
    count = 0
    for grip in grips:
        if grip.Select(False)==0: count += 1
    if count>0:
        scriptcontext.doc.Views.Redraw()
        return count
    return scriptcontext.errorhandler()

########NEW FILE########
__FILENAME__ = group
import scriptcontext
import utility as rhutil

def AddGroup(group_name=None):
    """Adds a new empty group to the document
    Parameters:
      group_name[opt] = name of the new group. If omitted, rhino automatically
          generates the group name
    Returns:
      name of the new group if successful
      None is not successful or on error
    """
    index = -1
    if group_name is None:
        index = scriptcontext.doc.Groups.Add()
    else:
        if not isinstance(group_name, str): group_name = str(group_name)
        index = scriptcontext.doc.Groups.Add( group_name )
    rc = scriptcontext.doc.Groups.GroupName(index)
    if rc is None: return scriptcontext.errorhandler()
    return rc


def AddObjectsToGroup(object_ids, group_name):
    """Adds one or more objects to an existing group.
    Parameters:
      object_ids = list of Strings or Guids representing the object identifiers
      group_name = the name of an existing group
    Returns:
      number of objects added to the group
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    object_ids = rhutil.coerceguidlist(object_ids)
    if index<0 or not object_ids: return 0
    if not scriptcontext.doc.Groups.AddToGroup(index, object_ids): return 0
    return len(object_ids)


def AddObjectToGroup(object_id, group_name):
    """Adds a single object to an existing group.
    Parameters:
      object_id = String or Guid representing the object identifier
      group_name = the name of an existing group
    Returns:
      True or False representing success or failure
    """
    object_id = rhutil.coerceguid(object_id)
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if object_id is None or index<0: return False
    return scriptcontext.doc.Groups.AddToGroup(index, object_id)


def DeleteGroup(group_name):
    """Removes an existing group from the document. Reference groups cannot be
    removed. Deleting a group does not delete the member objects
    Parameters:
      group_name = the name of an existing group
    Returns:
      True or False representing success or failure
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    return scriptcontext.doc.Groups.Delete(index)


def GroupCount():
    "Returns the number of groups in the document"
    return scriptcontext.doc.Groups.Count


def GroupNames():
    """Returns the names of all the groups in the document
    None if no names exist in the document
    """
    names = scriptcontext.doc.Groups.GroupNames(True)
    if names is None: return None
    return list(names)


def HideGroup(group_name):
    """Hides a group of objects. Hidden objects are not visible, cannot be
    snapped to, and cannot be selected
    Parameters:
      group_name = the name of an existing group
    Returns:
      The number of objects that were hidden
    """
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: return 0
    return scriptcontext.doc.Groups.Hide(index);


def IsGroup(group_name):
    """Verifies the existance of a group
    Paramters:
      group_name = the name of the group to check for
    Returns:
      True or False
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    return scriptcontext.doc.Groups.Find(group_name, True)>=0


def IsGroupEmpty(group_name):
    """Verifies that an existing group is empty, or contains no object members
    Parameters:
      group_name = the name of an existing group
    Returns:
      True or False if group_name exists
      None if group_name does not exist
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.Groups.GroupObjectCount(index)>0


def LockGroup(group_name):
    """Locks a group of objects. Locked objects are visible and they can be
    snapped to. But, they cannot be selected
    Parameters:
      group_name = the name of an existing group
    Returns:
      Number of objects that were locked if successful
      None on error
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.Groups.Lock(index);


def RemoveObjectFromAllGroups(object_id):
    """Removes a single object from any and all groups that it is a member.
    Neither the object nor the group can be reference objects
    Parameters:
      object_id = the object identifier
    Returns:
      True or False indicating success or failure
    """
    rhinoobject = rhutil.coercerhinoobject(object_id, True, True)
    if rhinoobject.GroupCount<1: return False
    attrs = rhinoobject.Attributes
    attrs.RemoveFromAllGroups()
    return scriptcontext.doc.Objects.ModifyAttributes(rhinoobject, attrs, True)


def RemoveObjectFromGroup(object_id, group_name):
    """Remove a single object from an existing group
    Parameters:
      object_id = the object identifier
      group_name = the name of an existing group
    Returns:
      True or False indicating success or failure
    """
    count = RemoveObjectsFromGroup(object_id, group_name)
    return not (count is None or count<1)


def RemoveObjectsFromGroup(object_ids, group_name):
    """Removes one or more objects from an existing group
    Parameters:
      object_ids = a list of object identifiers
      group_name = the name of an existing group
    Returns:
      The number of objects removed from the group is successful
      None on error
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: return scriptcontext.errorhandler()
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    objects_removed = 0
    for id in object_ids:
        rhinoobject = rhutil.coercerhinoobject(id, True, True)
        attrs = rhinoobject.Attributes
        attrs.RemoveFromGroup(index)
        if scriptcontext.doc.Objects.ModifyAttributes(rhinoobject, attrs, True):
            objects_removed+=1
    return objects_removed


def RenameGroup(old_name, new_name):
    """Renames an existing group
    Parameters:
      old_name = the name of an existing group
      new_name = the new group name
    Returns:
      the new group name if successful
      None on error
    """
    if not isinstance(old_name, str): old_name = str(old_name)
    index = scriptcontext.doc.Groups.Find(old_name, True)
    if index<0: return scriptcontext.errorhandler()
    if not isinstance(new_name, str): new_name = str(new_name)
    if scriptcontext.doc.Groups.ChangeGroupName(index, new_name):
        return new_name
    return scriptcontext.errorhandler()


def ShowGroup(group_name):
    """Shows a group of previously hidden objects. Hidden objects are not
    visible, cannot be snapped to, and cannot be selected
    Parameters:
      group_name = the name of an existing group
    Returns:
      The number of objects that were shown if successful
      None on error  
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.Groups.Show(index);


def UnlockGroup(group_name):
    """Unlocks a group of previously locked objects. Lockes objects are visible,
    can be snapped to, but cannot be selected
    Parameters:
      group_name = the name of an existing group
    Returns:
      The number of objects that were unlocked if successful
      None on error  
    """
    if not isinstance(group_name, str): group_name = str(group_name)
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.Groups.Unlock(index);

########NEW FILE########
__FILENAME__ = hatch
import scriptcontext
import utility as rhutil
import Rhino
import System.Guid

def AddHatch(curve_id, hatch_pattern=None, scale=1.0, rotation=0.0):
    """Creates a new hatch object from a closed planar curve object
    Parameters:
      curve_id = identifier of the closed planar curve that defines the
          boundary of the hatch object
      hatch_pattern[opt] = name of the hatch pattern to be used by the hatch
          object. If omitted, the current hatch pattern will be used
      scale[opt] = hatch pattern scale factor
      rotation[opt] = hatch pattern rotation angle in degrees.
    Returns:
      identifier of the newly created hatch on success
      None on error
    """
    rc = AddHatches(curve_id, hatch_pattern, scale, rotation)
    if rc: return rc[0]
    return scriptcontext.errorhandler()


def AddHatches(curve_ids, hatch_pattern=None, scale=1.0, rotation=0.0):
    """Creates one or more new hatch objects a list of closed planar curves
    Parameters:
      curve_ids = identifiers of the closed planar curves that defines the
          boundary of the hatch objects
      hatch_pattern[opt] = name of the hatch pattern to be used by the hatch
          object. If omitted, the current hatch pattern will be used
      scale[opt] = hatch pattern scale factor
      rotation[opt] = hatch pattern rotation angle in degrees.
    Returns:
      identifiers of the newly created hatch on success
      None on error
    """
    id = rhutil.coerceguid(curve_ids, False)
    if id: curve_ids = [id]
    index = scriptcontext.doc.HatchPatterns.CurrentHatchPatternIndex
    if hatch_pattern and hatch_pattern!=index:
        if isinstance(hatch_pattern, int):
            index = hatch_pattern
        else:
            index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
        if index<0: return scriptcontext.errorhandler()
    curves = [rhutil.coercecurve(id, -1, True) for id in curve_ids]
    rotation = Rhino.RhinoMath.ToRadians(rotation)
    hatches = Rhino.Geometry.Hatch.Create(curves, index, rotation, scale)
    if not hatches: return scriptcontext.errorhandler()
    ids = []
    for hatch in hatches:
        id = scriptcontext.doc.Objects.AddHatch(hatch)
        if id==System.Guid.Empty: continue
        ids.append(id)
    if not ids: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return ids


def AddHatchPatterns(filename, replace=False):
    """Adds hatch patterns to the document by importing hatch pattern definitions
    from a pattern file.
    Parameters:
      filename = name of the hatch pattern file
      replace[opt] = If hatch pattern names already in the document match hatch
          pattern names in the pattern definition file, then the existing hatch
          patterns will be redefined
    Returns:
      Names of the newly added hatch patterns if successful
      None on error
    """
    patterns = Rhino.DocObjects.HatchPattern.ReadFromFile(filename, True)
    if not patterns: return scriptcontext.errorhandler()
    rc = []
    for pattern in patterns:
         index = scriptcontext.doc.HatchPatterns.Add(pattern)
         if index>=0:
             pattern = scriptcontext.doc.HatchPatterns[index]
             rc.append(pattern.Name)
    if not rc: return scriptcontext.errorhandler()
    return rc


def CurrentHatchPattern(hatch_pattern=None):
    """Returns or sets the current hatch pattern file
    Parameters:
      hatch_pattern[opt] = name of an existing hatch pattern to make current
    Returns:
      if hatch_pattern is not specified, the current hatch pattern
      if hatch_pattern is specified, the previous hatch pattern
      None on error
    """
    rc = scriptcontext.doc.HatchPatterns.CurrentHatchPatternIndex
    if hatch_pattern:
        index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
        if index<0: return scriptcontext.errorhandler()
        scriptcontext.doc.HatchPatterns.CurrentHatchPatternIndex = index
    return rc


def ExplodeHatch(hatch_id, delete=False):
    """Explodes a hatch object into its component objects. The exploded objects
    will be added to the document. If the hatch object uses a solid pattern,
    then planar face Brep objects will be created. Otherwise, line curve objects
    will be created
    Parameters:
      hatch_id = identifier of a hatch object
      delete[opt] = delete the hatch object
    Returns:
      list of identifiers for the newly created objects
      None on error
    """
    rhobj = rhutil.coercerhinoobject(hatch_id, True, True)
    pieces = rhobj.HatchGeometry.Explode()
    if not pieces: return scriptcontext.errorhandler()
    attr = rhobj.Attributes
    rc = []
    for piece in pieces:
        id = None
        if isinstance(piece, Rhino.Geometry.Curve):
            id = scriptcontext.doc.Objects.AddCurve(piece, attr)
        elif isinstance(piece, Rhino.Geometry.Brep):
            id = scriptcontext.doc.Objects.AddBrep(piece, attr)
        if id: rc.append(id)
    if delete: scriptcontext.doc.Objects.Delete(rhobj)
    return rc


def HatchPattern(hatch_id, hatch_pattern=None):
    """Returns or changes a hatch object's hatch pattern
    Paramters:
      hatch_id = identifier of a hatch object
      hatch_pattern[opt] = name of an existing hatch pattern to replace the
          current hatch pattern
    Returns:
      if hatch_pattern is not specified, the current hatch pattern
      if hatch_pattern is specified, the previous hatch pattern
      None on error
    """
    hatchobj = rhutil.coercerhinoobject(hatch_id, True, True)
    if not isinstance(hatchobj, Rhino.DocObjects.HatchObject):
        return scriptcontext.errorhandler()
    old_index = hatchobj.HatchGeometry.PatternIndex
    if hatch_pattern:
        new_index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
        if new_index<0: return scriptcontext.errorhandler()
        hatchobj.HatchGeometry.PatternIndex = new_index
        hatchobj.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return scriptcontext.doc.HatchPatterns[old_index].Name


def HatchPatternCount():
    "Returns the number of hatch patterns in the document"
    return scriptcontext.doc.HatchPatterns.Count


def HatchPatternDescription(hatch_pattern):
    """Returns the description of a hatch pattern. Note, not all hatch patterns
    have descriptions
    Parameters:
      hatch_pattern = name of an existing hatch pattern
    """
    index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.HatchPatterns[index].Description


def HatchPatternFillType(hatch_pattern):
    """Returns the fill type of a hatch pattern.
        0 = solid, uses object color
        1 = lines, uses pattern file definition
        2 = gradient, uses fill color definition
    Parameters:
      hatch_pattern = name of an existing hatch pattern
    """
    index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
    if index<0: return scriptcontext.errorhandler()
    return int(scriptcontext.doc.HatchPatterns[index].FillType)


def HatchPatternNames():
    "Returns the names of all of the hatch patterns in the document"
    rc = []
    for i in range(scriptcontext.doc.HatchPatterns.Count):
        hatchpattern = scriptcontext.doc.HatchPatterns[i]
        if hatchpattern.IsDeleted: continue
        rc.append(hatchpattern.Name)
    return rc

def HatchRotation(hatch_id, rotation=None):
    """Returns or modifies the rotation applied to the hatch pattern when
    it is mapped to the hatch's plane
    Parameters:
      hatch_id = identifier of a hatch object
      rotation[opt] = rotation angle in degrees
    Returns:
      if rotation is not defined, the current rotation angle
      if rotation is specified, the previous rotation angle
      None on error
    """
    hatchobj = rhutil.coercerhinoobject(hatch_id, True, True)
    if not isinstance(hatchobj, Rhino.DocObjects.HatchObject):
        return scriptcontext.errorhandler()
    rc = hatchobj.HatchGeometry.PatternRotation
    rc = Rhino.RhinoMath.ToDegrees(rc)
    if rotation is not None and rotation!=rc:
        rotation = Rhino.RhinoMath.ToRadians(rotation)
        hatchobj.HatchGeometry.PatternRotation = rotation
        hatchobj.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def HatchScale(hatch_id, scale=None):
    """Returns or modifies the scale applied to the hatch pattern when it is
    mapped to the hatch's plane
    Parameters:
      hatch_id = identifier of a hatch object
      scale[opt] = scale factor
    Returns:
      if scale is not defined, the current scale factor
      if scale is defined, the previous scale factor
      None on error
    """
    hatchobj = rhutil.coercerhinoobject(hatch_id)
    if not isinstance(hatchobj, Rhino.DocObjects.HatchObject):
        return scriptcontext.errorhandler()
    rc = hatchobj.HatchGeometry.PatternScale
    if scale and scale!=rc:
        hatchobj.HatchGeometry.PatternScale = scale
        hatchobj.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def IsHatch(object_id):
    """Verifies the existence of a hatch object in the document
    Paramters:
      object_id = identifier of an object
    Returns:
      True or False
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, False)
    return isinstance(rhobj, Rhino.DocObjects.HatchObject)


def IsHatchPattern(name):
    """Verifies the existence of a hatch pattern in the document
    Parameters:
      name = the name of a hatch pattern
    Returns:
      True or False
    """
    return scriptcontext.doc.HatchPatterns.Find(name, True)>=0


def IsHatchPatternCurrent(hatch_pattern):
    """Verifies that a hatch pattern is the current hatch pattern
    Parameters:
      hatch_pattern = name of an existing hatch pattern
    Returns:
      True or False
      None on error
    """
    index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
    if index<0: return scriptcontext.errorhandler()
    return index==scriptcontext.doc.HatchPatterns.CurrentHatchPatternIndex


def IsHatchPatternReference(hatch_pattern):
    """Verifies that a hatch pattern is from a reference file
    Parameters:
      hatch_pattern = name of an existing hatch pattern
    Returns:
      True or False
      None on error
    """
    index = scriptcontext.doc.HatchPatterns.Find(hatch_pattern, True)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.HatchPatterns[index].IsReference

########NEW FILE########
__FILENAME__ = layer
import Rhino.DocObjects.Layer
import scriptcontext
import utility as rhutil
import System.Guid


def __getlayer(name_or_id, raise_if_missing):
    if not name_or_id: raise TypeError("Parameter must be a string or Guid")
    id = rhutil.coerceguid(name_or_id)
    if id: name_or_id = id
    else:
        layer = scriptcontext.doc.Layers.FindByFullPath(name_or_id, True)
        if layer>=0: return scriptcontext.doc.Layers[layer]
    layer = scriptcontext.doc.Layers.Find(name_or_id, True)
    if layer>=0: return scriptcontext.doc.Layers[layer]
    if raise_if_missing: raise ValueError("%s does not exist in LayerTable" % name_or_id)


def AddLayer(name=None, color=None, visible=True, locked=False, parent=None):
    """Add a new layer to the document
    Parameters:
      name[opt]: The name of the new layer. If omitted, Rhino automatically
          generates the layer name.
      color[opt]: A Red-Green-Blue color value or System.Drawing.Color. If
          omitted, the color Black is assigned.
      visible[opt]: layer's visibility
      locked[opt]: layer's locked state
      parent[opt]: name of the new layer's parent layer. If omitted, the new
          layer will not have a parent layer.
    Returns:
      The full name of the new layer if successful.
    """
    layer = Rhino.DocObjects.Layer.GetDefaultLayerProperties()
    if name:
        if not isinstance(name, str): name = str(name)
        layer.Name = name
    color = rhutil.coercecolor(color)
    if color: layer.Color = color
    layer.IsVisible = visible
    layer.IsLocked = locked
    if parent:
        parent = __getlayer(parent, True)
        layer.ParentLayerId = parent.Id
    index = scriptcontext.doc.Layers.Add(layer)
    return scriptcontext.doc.Layers[index].FullPath


def CurrentLayer(layer=None):
    """Returns or changes the current layer
    Parameters:
      layer[opt] = the name or Guid of an existing layer to make current
    Returns:
      If a layer name is not specified, the full name of the current layer
      If a layer name is specified, the full name of the previous current layer
    """
    rc = scriptcontext.doc.Layers.CurrentLayer.FullPath
    if layer:
        layer = __getlayer(layer, True)
        scriptcontext.doc.Layers.SetCurrentLayerIndex(layer.LayerIndex, True)
    return rc


def DeleteLayer(layer):
    """Removes an existing layer from the document. The layer to be removed
    cannot be the current layer. Unlike the PurgeLayer method, the layer must
    be empty, or contain no objects, before it can be removed. Any layers that
    are children of the specified layer will also be removed if they are also
    empty.
    Parameters:
      layer = the name or id of an existing empty layer
    Returns:
      True or False indicating success or failure
    """
    layer = __getlayer(layer, True)
    return scriptcontext.doc.Layers.Delete( layer.LayerIndex, True)


def ExpandLayer( layer, expand ):
    """Expands a layer. Expanded layers can be viewed in Rhino's layer dialog
    Parameters:
      layer = name of the layer to expand
      expand = True to expand, False to collapse
    Returns:
      True or False indicating success or failure
    """
    layer = __getlayer(layer, True)
    if layer.IsExpanded==expand: return True
    layer.IsExpanded = expand
    return scriptcontext.doc.Layers.Modify(layer, layer.LayerIndex, True)


def IsLayer(layer):
    """Verifies the existance of a layer in the document
    Parameter:
      layer = the name or id of a layer to search for
    """
    layer = __getlayer(layer, False)
    return layer is not None


def IsLayerChangeable(layer):
    "Verifies that the objects on a layer can be changed (normal)"
    layer = __getlayer(layer, True)
    rc = layer.IsVisible and not layer.IsLocked
    return rc


def IsLayerChildOf(layer, test):
    """Verifies that a layer is a child of another layer
    Parameters:
      layer = the name or id of the layer to test against
      test = the name or id to the layer to test
    """
    layer = __getlayer(layer, True)
    test = __getlayer(test, True)
    return test.IsChildOf(layer)


def IsLayerCurrent(layer):
    "Verifies that a layer is the current layer"
    layer = __getlayer(layer, True)
    return layer.LayerIndex == scriptcontext.doc.Layers.CurrentLayerIndex


def IsLayerEmpty(layer):
    "Verifies that an existing layer is empty, or contains no objects"
    layer = __getlayer(layer, True)
    rhobjs = scriptcontext.doc.Objects.FindByLayer(layer)
    if not rhobjs: return True
    return False


def IsLayerExpanded(layer):
    """Verifies that a layer is expanded. Expanded layers can be viewed in
    Rhino's layer dialog
    """
    layer = __getlayer(layer, True)
    return layer.IsExpanded   


def IsLayerLocked(layer):
    "Verifies that a layer is locked."
    layer = __getlayer(layer, True)
    return layer.IsLocked


def IsLayerOn(layer):
    "Verifies that a layer is on."
    layer = __getlayer(layer, True)
    return layer.IsVisible


def IsLayerSelectable(layer):
    "Verifies that an existing layer is selectable (normal and reference)"
    layer = __getlayer(layer, True)
    return layer.IsVisible and not layer.IsLocked


def IsLayerParentOf(layer, test):
    """Verifies that a layer is a parent of another layer
    Parameters:
      layer = the name or id of the layer to test against
      test = the name or id to the layer to test
    """
    layer = __getlayer(layer, True)
    test = __getlayer(test, True)
    return test.IsParentOf(layer)


def IsLayerReference(layer):
    "Verifies that a layer is from a reference file."
    layer = __getlayer(layer, True)
    return layer.IsReference


def IsLayerVisible(layer):
    "Verifies that a layer is visible (normal, locked, and reference)"
    layer = __getlayer(layer, True)
    return layer.IsVisible


def LayerChildCount(layer):
    "Returns the number of immediate child layers of a layer"
    layer = __getlayer(layer, True)
    children = layer.GetChildren()
    if children: return len(children)
    return 0


def LayerChildren(layer):
    """Returns the immediate child layers of a layer
    Parameters:
      layer = the name or id of an existing layer
    Returns:
      List of children
    """
    layer = __getlayer(layer, True)
    children = layer.GetChildren()
    if children: return [child.FullPath for child in children]
    return [] #empty list


def LayerColor(layer, color=None):
    """Returns or changes the color of a layer.
    Parameters:
      layer = name or id of an existing layer
      color [opt] = the new color value. If omitted, the current layer color is returned.
    Returns:
      If a color value is not specified, the current color value on success
      If a color value is specified, the previous color value on success
    """
    layer = __getlayer(layer, True)
    rc = layer.Color
    if color:
        color = rhutil.coercecolor(color)
        layer.Color = color
        if scriptcontext.doc.Layers.Modify(layer, layer.LayerIndex, False):
            scriptcontext.doc.Views.Redraw()
    return rc


def LayerCount():
    "Return number of layers in the document"
    return scriptcontext.doc.Layers.ActiveCount


def LayerIds():
    "Return identifiers of all layers in the document"
    return [layer.Id for layer in scriptcontext.doc.Layers]


def LayerLinetype(layer, linetype=None):
    """Return or change the linetype of a layer
    Parameters:
      layer = name of an existing layer
      linetype[opt] = name of a linetype
    Returns:
      If linetype is not specified, name of the current linetype
      If linetype is specified, name of the previous linetype
    """
    layer = __getlayer(layer, True)
    index = layer.LinetypeIndex
    rc = scriptcontext.doc.Linetypes[index].Name
    if linetype:
        if not isinstance(linetype, str): linetype = str(linetype)
        index = scriptcontext.doc.Linetypes.Find(linetype, True)
        if index==-1: return scriptcontext.errorhandler()
        layer.LinetypeIndex = index
        layer.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def LayerLocked(layer, locked=None):
    """Returns or changes the locked mode of a layer
    Parameters:
      layer = name of an existing layer
      locked[opt] = new layer locked mode
    Returns:
      If locked is not specified, the current layer locked mode
      If locked is specified, the previous layer locked mode
    """
    layer = __getlayer(layer, True)
    rc = layer.IsLocked
    if locked!=None and locked!=rc:
        layer.IsLocked = locked
        layer.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def LayerMaterialIndex(layer,index=None):
    """Returns or changes the material index of a layer. A material index of -1
    indicates that no material has been assigned to the layer. Thus, the layer
    will use Rhino's default layer material
    Parameters:
      layer = name of existing layer
    """
    layer = __getlayer(layer, True)
    rc = layer.RenderMaterialIndex
    if index is not None and index>=-1:
        layer.RenderMaterialIndex = index
        layer.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def LayerName(layer_id, fullpath=True):
    """Return the name of a layer given it's identifier
    Parameters:
      layer_id = layer identifier
      fullpath [opt] = return the full path name or short name
    """
    layer = __getlayer(layer_id, True)
    if fullpath: return layer.FullPath
    return layer.Name


def LayerNames(sort=False):
    """Return names of all layers in the document.
    Parameters:
      sort [opt] = return a sorted list of the layer names
    Returns
      list of strings
    """
    rc = []
    for layer in scriptcontext.doc.Layers:
        if not layer.IsDeleted: rc.append(layer.FullPath)
    if sort: rc.sort()
    return rc


def LayerOrder(layer):
    """Returns the current display order index of a layer as displayed in Rhino's
    layer dialog box. A display order index of -1 indicates that the current
    layer dialog filter does not allow the layer to appear in the layer list
    Parameters:
      layer = name of existing layer
    Returns:
      0 based index
    """
    layer = __getlayer(layer, True)
    return layer.SortIndex


def LayerPrintColor(layer, color=None):
    """Returns or changes the print color of a layer. Layer print colors are
    represented as RGB colors.
    Parameters:
      layer = name of existing layer
      color[opt] = new print color
    Returns:
      if color is not specified, the current layer print color
      if color is specified, the previous layer print color
      None on error
    """
    layer = __getlayer(layer, True)
    rc = layer.PlotColor
    if color:
        color = rhutil.coercecolor(color)
        layer.PlotColor = color
        layer.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def LayerPrintWidth(layer, width=None):
    """Returns or changes the print width of a layer. Print width is specified
    in millimeters. A print width of 0.0 denotes the "default" print width.
    Parameters:
      layer = name of existing layer
      width[opt] = new print width
    Returns:
      if width is not specified, the current layer print width
      if width is specified, the previous layer print width
    """
    layer = __getlayer(layer, True)
    rc = layer.PlotWeight
    if width is not None and width!=rc:
        layer.PlotWeight = width
        layer.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def LayerVisible(layer, visible=None, force_visible=False):
    """Returns or changes the visible property of a layer.
    Parameters:
      layer = name of existing layer
      visible[opt] = new visible state
    Returns:
      if visible is not specified, the current layer visibility
      if visible is specified, the previous layer visibility
    """
    layer = __getlayer(layer, True)
    rc = layer.IsVisible
    if visible is not None and visible!=rc:
        if visible and force_visible:
            scriptcontext.doc.Layers.ForceLayerVisible(layer.Id)
        else:
            layer.IsVisible = visible
            layer.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def ParentLayer(layer, parent=None):
    """Return or modify the parent layer of a layer
    Parameters:
      layer = name of an existing layer
      parent[opt] = name of new parent layer. To remove the parent layer,
        thus making a root-level layer, specify an empty string
    Returns:
      If parent is not specified, the name of the current parent layer
      If parent is specified, the name of the previous parent layer
      None if the layer does not have a parent
    """
    layer = __getlayer(layer, True)
    parent_id = layer.ParentLayerId
    oldparent = None
    if parent_id!=System.Guid.Empty:
        oldparentlayer = scriptcontext.doc.Layers.Find(parent_id, False)
        if oldparentlayer is not None:
            oldparentlayer = scriptcontext.doc.Layers[oldparentlayer]
            oldparent = oldparentlayer.FullPath
    if parent is None: return oldparent
    if parent=="":
        layer.ParentLayerId = System.Guid.Empty
    else:
        parent = __getlayer(parent, True)
        layer.ParentLayerId = parent.Id
    layer.CommitChanges()
    return oldparent


def PurgeLayer(layer):
    """Removes an existing layer from the document. The layer will be removed
    even if it contains geometry objects. The layer to be removed cannot be the
    current layer
    empty.
    Parameters:
      layer = the name or id of an existing empty layer
    Returns:
      True or False indicating success or failure
    """
    layer = __getlayer(layer, True)
    rc = scriptcontext.doc.Layers.Purge( layer.LayerIndex, True)
    scriptcontext.doc.Views.Redraw()
    return rc

def RenameLayer(oldname, newname):
    """Renames an existing layer
    Returns: The new layer name if successful
    """
    if oldname and newname:
        layer = __getlayer(oldname, True)
        layer.Name = newname
        layer.CommitChanges()
        return newname

########NEW FILE########
__FILENAME__ = light
import scriptcontext
import utility as rhutil
import Rhino.Geometry
import math


def __coercelight(id, raise_if_missing=False):
    light = rhutil.coercegeometry(id)
    if isinstance(light, Rhino.Geometry.Light): return light
    if raise_if_missing: raise ValueError("unable to retrieve light from %s"%id)


def AddDirectionalLight(start_point, end_point):
    """Adds a new directional light object to the document
    Parameters:
      start_point: starting point of the light
      end_point: ending point and direction of the light
    Returns:
      identifier of the new object if successful
    """
    start = rhutil.coerce3dpoint(start_point, True)
    end = rhutil.coerce3dpoint(end_point, True)
    light = Rhino.Geometry.Light()
    light.LightStyle = Rhino.Geometry.LightStyle.WorldDirectional
    light.Location = start
    light.Direction = end-start
    index = scriptcontext.doc.Lights.Add(light)
    if index<0: raise Exception("unable to add light to LightTable")
    rc = scriptcontext.doc.Lights[index].Id
    scriptcontext.doc.Views.Redraw()
    return rc


def AddLinearLight(start_point, end_point, width=None):
    """Adds a new linear light object to the document
    Parameters:
      start_point: starting point of the light
      end_point: ending point and direction of the light
      width[opt]: width of the light
    Returns:
      identifier of the new object if successful
      None on error
    """
    start = rhutil.coerce3dpoint(start_point, True)
    end = rhutil.coerce3dpoint(end_point, True)
    if width is None:
        radius=0.5
        units = scriptcontext.doc.ModelUnitSystem
        if units!=Rhino.UnitSystem.None:
            scale = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Inches, units)
            radius *= scale
        width = radius
    light = Rhino.Geometry.Light()
    light.LightStyle = Rhino.Geometry.LightStyle.WorldLinear
    light.Location = start
    v = end-start
    light.Direction = v
    light.Length = light.Direction
    light.Width = -light.Width
    plane = Rhino.Geometry.Plane(light.Location, light.Direction)
    xaxis = plane.XAxis
    xaxis.Unitize()
    plane.XAxis = xaxis
    light.Width = xaxis * min(width, v.Length/20)
    #light.Location = start - light.Direction
    index = scriptcontext.doc.Lights.Add(light)
    if index<0: raise Exception("unable to add light to LightTable")
    rc = scriptcontext.doc.Lights[index].Id
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPointLight(point):
    """Adds a new point light object to the document
    Parameters:
      point = the 3d location of the point
    Returns:
      identifier of the new object if successful
    """
    point = rhutil.coerce3dpoint(point, True)
    light = Rhino.Geometry.Light()
    light.LightStyle = Rhino.Geometry.LightStyle.WorldPoint
    light.Location = point
    index = scriptcontext.doc.Lights.Add(light)
    if index<0: raise Exception("unable to add light to LightTable")
    rc = scriptcontext.doc.Lights[index].Id
    scriptcontext.doc.Views.Redraw()
    return rc


def AddRectangularLight(origin, width_point, height_point):
    """Adds a new rectangular light object to the document
    Parameters:
      origin = 3d origin point of the light
      width_point = 3d width and direction point of the light
      height_point = 3d height and direction point of the light
    Returns:
      identifier of the new object if successful
    """
    origin = rhutil.coerce3dpoint(origin, True)
    ptx = rhutil.coerce3dpoint(width_point, True)
    pty = rhutil.coerce3dpoint(height_point, True)
    length = pty-origin
    width = ptx-origin
    normal = Rhino.Geometry.Vector3d.CrossProduct(width, length)
    normal.Unitize()
    light = Rhino.Geometry.Light()
    light.LightStyle = Rhino.Geometry.LightStyle.WorldRectangular
    light.Location = origin
    light.Width = width
    light.Length = length
    light.Direction = normal
    index = scriptcontext.doc.Lights.Add(light)
    if index<0: raise Exception("unable to add light to LightTable")
    rc = scriptcontext.doc.Lights[index].Id
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSpotLight(origin, radius, apex_point):
    """Adds a new spot light object to the document
    Parameters:
      origin = 3d origin point of the light
      radius = radius of the cone
      apex_point = 3d apex point of the light
    Returns:
      identifier of the new object
    """
    origin = rhutil.coerce3dpoint(origin, True)
    apex_point = rhutil.coerce3dpoint(apex_point, True)
    if radius<0: radius=1.0
    light = Rhino.Geometry.Light()
    light.LightStyle = Rhino.Geometry.LightStyle.WorldSpot
    light.Location = apex_point
    light.Direction = origin-apex_point
    light.SpotAngleRadians = math.atan(radius / (light.Direction.Length))
    light.HotSpot = 0.50
    index = scriptcontext.doc.Lights.Add(light)
    if index<0: raise Exception("unable to add light to LightTable")
    rc = scriptcontext.doc.Lights[index].Id
    scriptcontext.doc.Views.Redraw()
    return rc


def EnableLight(object_id, enable=None):
    """Enables or disables a light object
    Parameters:
      object_id = the light object's identifier
      enable[opt] = the light's enabled status
    Returns:
      if enable is not specified, the current enabled status 
      if enable is specified, the previous enabled status
      None on error
    """
    light = __coercelight(object_id, True)
    rc = light.IsEnabled
    if enable is not None and enable!=rc:
        light.IsEnabled = enable
        id = rhutil.coerceguid(object_id)
        if not scriptcontext.doc.Lights.Modify(id, light):
            return scriptcontext.errorhandler()
        scriptcontext.doc.Views.Redraw()
    return rc

def IsDirectionalLight(object_id):
    """Verifies a light object is a directional light
    Parameters:
      object_id = the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsDirectionalLight


def IsLight(object_id):
    """Verifies an object is a light object
    Parameters:
      object_id: the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, False)
    return light is not None


def IsLightEnabled(object_id):
    """Verifies a light object is enabled
    Parameters:
      object_id: the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsEnabled


def IsLightReference(object_id):
    """Verifies a light object is referenced from another file
    Parameters:
      object_id: the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsReference


def IsLinearLight(object_id):
    """Verifies a light object is a linear light
    Parameters:
      object_id = the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsLinearLight


def IsPointLight(object_id):
    """Verifies a light object is a point light
    Parameters:
      object_id = the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsPointLight


def IsRectangularLight(object_id):
    """Verifies a light object is a rectangular light
    Parameters:
      object_id = the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsRectangularLight


def IsSpotLight(object_id):
    """Verifies a light object is a spot light
    Parameters:
      object_id = the light object's identifier
    Returns:
      True or False
    """
    light = __coercelight(object_id, True)
    return light.IsSpotLight


def LightColor(object_id, color=None):
    """Returns or changes the color of a light
    Parameters:
      object_id = the light object's identifier
      color[opt] = the light's new color
    Returns:
      if color is not specified, the current color 
      if color is specified, the previous color
    """
    light = __coercelight(object_id, True)
    rc = light.Diffuse
    if color:
        color = rhutil.coercecolor(color, True)
        if color!=rc:
            light.Diffuse = color
            id = rhutil.coerceguid(object_id, True)
            if not scriptcontext.doc.Lights.Modify(id, light):
                return scriptcontext.errorhandler()
            scriptcontext.doc.Views.Redraw()
    return rc


def LightCount():
    "Returns the number of light objects in the document"
    return scriptcontext.doc.Lights.Count


def LightDirection(object_id, direction=None):
    """Returns or changes the direction of a light object
    Parameters:
      object_id = the light object's identifier
      direction[opt] = the light's new direction
    Returns:
      if direction is not specified, the current direction
      if direction is specified, the previous direction
    """
    light = __coercelight(object_id, True)
    rc = light.Direction
    if direction:
        direction = rhutil.coerce3dvector(direction, True)
        if direction!=rc:
            light.Direction = direction
            id = rhutil.coerceguid(object_id, True)
            if not scriptcontext.doc.Lights.Modify(id, light):
                return scriptcontext.errorhandler()
            scriptcontext.doc.Views.Redraw()
    return rc


def LightLocation(object_id, location=None):
    """Returns or changes the location of a light object
    Parameters:
      object_id = the light object's identifier
      location[opt] = the light's new location
    Returns:
      if location is not specified, the current location
      if location is specified, the previous location
    """
    light = __coercelight(object_id, True)
    rc = light.Location
    if location:
        location = rhutil.coerce3dpoint(location, True)
        if location!=rc:
            light.Location = location
            id = rhutil.coerceguid(object_id, True)
            if not scriptcontext.doc.Lights.Modify(id, light):
                return scriptcontext.errorhandler()
            scriptcontext.doc.Views.Redraw()
    return rc


def LightName(object_id, name=None):
    """Returns or changes the name of a light object
    Parameters:
      object_id = the light object's identifier
      name[opt] = the light's new name
    Returns:
      if name is not specified, the current name
      if name is specified, the previous name
    """
    light = __coercelight(object_id, True)
    rc = light.Name
    if name and name!=rc:
        light.Name = name
        id = rhutil.coerceguid(object_id, True)
        if not scriptcontext.doc.Lights.Modify(id, light):
            return scriptcontext.errorhandler()
        scriptcontext.doc.Views.Redraw()
    return rc


def LightObjects():
    "Returns list of identifiers of light objects in the document"
    count = scriptcontext.doc.Lights.Count
    rc = []
    for i in range(count):
        rhlight = scriptcontext.doc.Lights[i]
        if not rhlight.IsDeleted: rc.append(rhlight.Id)
    return rc


def RectangularLightPlane(object_id):
    """Returns the plane of a rectangular light object
    Parameters:
      object_id = the light object's identifier
    Returns:
      the plane if successful
      None on error
    """
    light = __coercelight(object_id, True)
    if light.LightStyle!=Rhino.Geometry.LightStyle.WorldRectangular:
        return scriptcontext.errorhandler()
    location = light.Location
    length = light.Length
    width = light.Width
    direction = light.Direction
    plane = Rhino.Geometry.Plane(location, length, width)
    return plane, (length.Length, width.Length)


def SpotLightHardness(object_id, hardness=None):
    """Returns or changes the hardness of a spot light. Spotlight hardness
    controls the fully illuminated region.
    Parameters:
      object_id = the light object's identifier
      hardness[opt] = the light's new hardness
    Returns:
      if hardness is not specified, the current hardness
      if hardness is specified, the previous hardness
    """
    light = __coercelight(object_id, True)
    if light.LightStyle!=Rhino.Geometry.LightStyle.WorldSpot:
        return scriptcontext.errorhandler()
    rc = light.HotSpot
    if hardness and hardness!=rc:
        light.HotSpot = hardness
        id = rhutil.coerceguid(object_id, True)
        if not scriptcontext.doc.Lights.Modify(id, light):
            return scriptcontext.errorhandler()
        scriptcontext.doc.Views.Redraw()
    return rc


def SpotLightRadius(object_id, radius=None):
    """Returns or changes the radius of a spot light.
    Parameters:
      object_id = the light object's identifier
      radius[opt] = the light's new radius
    Returns:
      if radius is not specified, the current radius
      if radius is specified, the previous radius
    """
    light = __coercelight(object_id, True)
    if light.LightStyle!=Rhino.Geometry.LightStyle.WorldSpot:
        return scriptcontext.errorhandler()
    radians = light.SpotAngleRadians
    rc = light.Direction.Length * math.tan(radians)
    if radius and radius!=rc:
        radians = math.atan(radius/light.Direction.Length)
        light.SpotAngleRadians = radians
        id = rhutil.coerceguid(object_id, True)
        if not scriptcontext.doc.Lights.Modify(id, light):
            return scriptcontext.errorhandler()
        scriptcontext.doc.Views.Redraw()
    return rc


def SpotLightShadowIntensity(object_id, intensity=None):
    """Returns or changes the shadow intensity of a spot light.
    Parameters:
      object_id = the light object's identifier
      intensity[opt] = the light's new intensity
    Returns:
      if intensity is not specified, the current intensity
      if intensity is specified, the previous intensity
    """
    light = __coercelight(object_id, True)
    if light.LightStyle!=Rhino.Geometry.LightStyle.WorldSpot:
        return scriptcontext.errorhandler()
    rc = light.SpotLightShadowIntensity
    if intensity and intensity!=rc:
        light.SpotLightShadowIntensity = intensity
        id = rhutil.coerceguid(object_id, True)
        if not scriptcontext.doc.Lights.Modify(id, light):
            return scriptcontext.errorhandler()
        scriptcontext.doc.Views.Redraw()
    return rc

########NEW FILE########
__FILENAME__ = line
import scriptcontext
import utility as rhutil
import Rhino


def LineClosestPoint(line, testpoint):
    "Finds the point on an infinite line that is closest to a test point"
    line = rhutil.coerceline(line, True)
    testpoint = rhutil.coerce3dpoint(testpoint, True)
    return line.ClosestPoint(testpoint, False)


def LineCylinderIntersection(line, cylinder_plane, cylinder_height, cylinder_radius):
    """Calculates the intersection of a line and a cylinder
    Parameters:
      line = the line to intersect
      cylinder_plane = base plane of the cylinder
      cylinder_height = height of the cylinder
      cylinder_radius = radius of the cylinder
    Returns:
      list of intersection points (0, 1, or 2 points)
    """
    line = rhutil.coerceline(line, True)
    cylinder_plane = rhutil.coerceplane(cylinder_plane, True)
    circle = Rhino.Geometry.Circle( cylinder_plane, cylinder_radius )
    if not circle.IsValid: raise ValueError("unable to create valid circle with given plane and radius")
    cyl = Rhino.Geometry.Cylinder( circle, cylinder_height )
    if not cyl.IsValid: raise ValueError("unable to create valid cylinder with given circle and height")
    rc, pt1, pt2 = Rhino.Geometry.Intersect.Intersection.LineCylinder(line, cyl)
    if rc==Rhino.Geometry.Intersect.LineCylinderIntersection.None:
        return []
    if rc==Rhino.Geometry.Intersect.LineCylinderIntersection.Single:
        return [pt1]
    return [pt1, pt2]


def LineIsFartherThan(line, distance, point_or_line):
    """Determines if the shortest distance from a line to a point or another
    line is greater than a specified distance
    Returns:
      True if the shortest distance from the line to the other project is
      greater than distance, False otherwise
    """
    line = rhutil.coerceline(line, True)
    test = rhutil.coerceline(point_or_line)
    if not test: test = rhutil.coerce3dpoint(point_or_line, True)
    minDist = line.MinimumDistanceTo(test)
    return minDist>distance


def LineLineIntersection(lineA, lineB):
    """Calculates the intersection of two non-parallel lines. Note, the two
    lines do not have to intersect for an intersection to be found. (see help)
    Parameters:
      lineA, lineB = lines to intersect
    Returns:
      a tuple containing a point on the first line and a point on the second line if successful
      None on error
    """
    lineA = rhutil.coerceline(lineA, True)
    lineB = rhutil.coerceline(lineB, True)
    rc, a, b = Rhino.Geometry.Intersect.Intersection.LineLine(lineA, lineB)
    if not rc: return None
    return lineA.PointAt(a), lineB.PointAt(b)


def LineMaxDistanceTo(line, point_or_line):
    """Finds the longest distance between a line as a finite chord, and a point
    or another line
    """
    line = rhutil.coerceline(line, True)
    test = rhutil.coerceline(point_or_line)
    if test is None: test = rhutil.coerce3dpoint(point_or_line, True)
    return line.MaximumDistanceTo(test)


def LineMinDistanceTo(line, point_or_line):
    """Finds the shortest distance between a line as a finite chord, and a point
    or another line
    """
    line = rhutil.coerceline(line, True)
    test = rhutil.coerceline(point_or_line)
    if test is None: test = rhutil.coerce3dpoint(point_or_line, True)
    return line.MinimumDistanceTo(test)


def LinePlane(line):
    """Returns a plane that contains the line. The origin of the plane is at the start of
    the line. If possible, a plane parallel to the world XY, YZ, or ZX plane is returned
    """
    line = rhutil.coerceline(line, True)
    rc, plane = line.TryGetPlane()
    if not rc: return scriptcontext.errorhandler()
    return plane


def LinePlaneIntersection(line, plane):
    """Calculates the intersection of a line and a plane.
    Parameters:
      line = Two 3D points identifying the starting and ending points of the line to intersect.
      plane = The plane to intersect.
    Returns:
      The 3D point of intersection is successful.
      None if not successful, or on error.
    """
    plane = rhutil.coerceplane(plane, True)
    line_points = rhutil.coerce3dpointlist(line, True)
    line = Rhino.Geometry.Line(line_points[0], line_points[1])
    rc, t = Rhino.Geometry.Intersect.Intersection.LinePlane(line, plane) 
    if  not rc: return scriptcontext.errorhandler()
    return line.PointAt(t)


def LineSphereIntersection(line, sphere_center, sphere_radius):
    """Calculates the intersection of a line and a sphere
    Returns:
      list of intersection points if successful
    """
    line = rhutil.coerceline(line, True)
    sphere_center = rhutil.coerce3dpoint(sphere_center, True)
    sphere = Rhino.Geometry.Sphere(sphere_center, sphere_radius)
    rc, pt1, pt2 = Rhino.Geometry.Intersect.Intersection.LineSphere(line, sphere)
    if rc==Rhino.Geometry.Intersect.LineSphereIntersection.None: return []
    if rc==Rhino.Geometry.Intersect.LineSphereIntersection.Single: return [pt1]
    return [pt1, pt2]


def LineTransform(line, xform):
    """Transforms a line
    Parameters:
      line = the line to transform
      xform = the transformation to apply
    Returns:
      transformed line
    """
    line = rhutil.coerceline(line, True)
    xform = rhutil.coercexform(xform, True)
    success = line.Transform(xform)
    if not success: raise Execption("unable to transform line")
    return line
########NEW FILE########
__FILENAME__ = linetype
import scriptcontext
import utility as rhutil
import Rhino


def __getlinetype(name_or_id):
    id = rhutil.coerceguid(name_or_id)
    if id: name_or_id = id
    linetype = scriptcontext.doc.Linetypes.Find(name_or_id, True)
    if linetype>=0: return scriptcontext.doc.Linetypes[linetype]


def IsLinetype(name_or_id):
    """Verifies the existance of a linetype in the document
    Returns: True or False
    """
    lt = __getlinetype(name_or_id)
    return lt is not None


def IsLinetypeReference(name_or_id):
    """Verifies that an existing linetype is from a reference file
    Returns: True or False
    """
    lt = __getlinetype(name_or_id)
    if lt is None: raise ValueError("unable to coerce %s into linetype"%name_or_id)
    return lt.IsReference


def LinetypeCount():
    "Returns number of linetypes in the document"
    return scriptcontext.doc.Linetypes.Count


def LinetypeNames(sort=False):
    """Returns names of all linetypes in the document
    Parameters:
      sort[opt] = return a sorted list of the linetype names
    Returns
      list of strings if successful
    """
    count = scriptcontext.doc.Linetypes.Count
    rc = []
    for i in xrange(count):
        linetype = scriptcontext.doc.Linetypes[i]
        if not linetype.IsDeleted: rc.append(linetype.Name)
    if sort: rc.sort()
    return rc

########NEW FILE########
__FILENAME__ = material
import Rhino.DocObjects
import scriptcontext
import utility as rhutil
from layer import __getlayer


def AddMaterialToLayer(layer):
    """Add material to a layer and returns the new material's index. If the
    layer already has a material, then the layer's current material index is
    returned
    Parameters:
      layer = name of an existing layer.
    Returns:
      Material index of the layer if successful
      None if not successful or on error
    """
    layer = __getlayer(layer, True)
    if layer.RenderMaterialIndex>-1: return layer.RenderMaterialIndex
    material_index = scriptcontext.doc.Materials.Add()
    layer.RenderMaterialIndex = material_index
    if scriptcontext.doc.Layers.Modify( layer, layer.LayerIndex, True):
        scriptcontext.doc.Views.Redraw()
        return material_index
    return scriptcontext.errorhandler()


def AddMaterialToObject(object_id):
    """Adds material to an object and returns the new material's index. If the
    object already has a material, the the object's current material index is
    returned.
    Parameters:
      object_id = identifier of an object
    Returns:
      material index of the object
    """
    rhino_object = rhutil.coercerhinoobject(object_id, True, True)
    attr = rhino_object.Attributes
    if attr.MaterialSource!=Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject:
        attr.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
        scriptcontext.doc.Objects.ModifyAttributes(rhino_object, attr, True)
        attr = rhino_object.Attributes
    material_index = attr.MaterialIndex
    if material_index>-1: return material_index
    material_index = scriptcontext.doc.Materials.Add()
    attr.MaterialIndex = material_index
    scriptcontext.doc.Objects.ModifyAttributes(rhino_object, attr, True)
    return material_index

    
def CopyMaterial(source_index, destination_index):
    """Copies definition of a source material to a destination material
    Parameters:
      source_index, destination_index = indices of materials to copy
    Returns:
      True or False indicating success or failure
    """
    if source_index==destination_index: return False
    source = scriptcontext.doc.Materials[source_index]
    if source is None: return False
    rc = scriptcontext.doc.Materials.Modify(source, destination_index, True)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def IsMaterialDefault(material_index):
    """Verifies a material is a copy of Rhino's built-in "default" material.
    The default material is used by objects and layers that have not been
    assigned a material.
    Parameters:
      material_index = the zero-based material index
    Returns:
      True or False indicating success or failure
    """
    mat = scriptcontext.doc.Materials[material_index]
    return mat and mat.IsDefaultMaterial


def IsMaterialReference(material_index):
    """Verifies a material is referenced from another file
    Parameters:
      material_index = the zero-based material index
    Returns:
      True or False indicating success or failure
    """
    mat = scriptcontext.doc.Materials[material_index]
    return mat and mat.IsReference


def MatchMaterial(source, destination):
    """Copies the material definition from one material to one or more objects
    Parameters:
      source = source material index -or- identifier of the source object.
        The object must have a material assigned
      destination = indentifier(s) of the destination object(s)
    Returns:
      number of objects that were modified if successful
      None if not successful or on error
    """
    source_id = rhutil.coerceguid(source)
    source_mat = None
    if source_id:
        rhobj = rhutil.coercerhinoobject(source_id, True, True)
        source = rhobj.Attributes.MaterialIndex
    mat = scriptcontext.doc.Materials[source]
    if not mat: return scriptcontext.errorhandler()
    destination_id = rhutil.coerceguid(destination)
    if destination_id: destination = [destination]
    ids = [rhutil.coerceguid(d) for d in destination]
    rc = 0
    for id in ids:
        rhobj = scriptcontext.doc.Objects.Find(id)
        if rhobj:
            rhobj.Attributes.MaterialIndex = source
            rhobj.Attributes.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
            rhobj.CommitChanges()
            rc += 1
    if rc>0: scriptcontext.doc.Views.Redraw()
    return rc


def MaterialBump(material_index, filename=None):
    """Returns or modifies a material's bump bitmap filename
    Parameters:
      material_index = zero based material index
      filename[opt] = the bump bitmap filename
    Returns:
      if filename is not specified, the current bump bitmap filename
      if filename is specified, the previous bump bitmap filename
      None if not successful or on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    texture = mat.GetBumpTexture()
    rc = texture.FileName if texture else ""
    if filename:
        mat.SetBumpTexture(filename)
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialColor(material_index, color=None):
    """Returns or modifies a material's diffuse color.
    Parameters:
      material_index = zero based material index
      color[opt] = the new color value
    Returns:
      if color is not specified, the current material color
      if color is specified, the previous material color
      None on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    rc = mat.DiffuseColor
    color = rhutil.coercecolor(color)
    if color:
        mat.DiffuseColor = color
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialEnvironmentMap(material_index, filename=None):
    """Returns or modifies a material's environment bitmap filename.
    Parameters:
      material_index = zero based material index
      filename[opt] = the environment bitmap filename
    Returns:
      if filename is not specified, the current environment bitmap filename
      if filename is specified, the previous environment bitmap filename
      None if not successful or on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    texture = mat.GetEnvironmentTexture()
    rc = texture.FileName if texture else ""
    if filename:
        mat.SetEnvironmentTexture(filename)
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialName(material_index, name=None):
    """Returns or modifies a material's user defined name
    Parameters:
      material_index = zero based material index
      name[opt] = the new name
    Returns:
      if name is not specified, the current material name
      if name is specified, the previous material name
      None on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    rc = mat.Name
    if name:
        mat.Name = name
        mat.CommitChanges()
    return rc


def MaterialReflectiveColor(material_index, color=None):
    """Returns or modifies a material's reflective color.
    Parameters:
      material_index = zero based material index
      color[opt] = the new color value
    Returns:
      if color is not specified, the current material reflective color
      if color is specified, the previous material reflective color
      None on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    rc = mat.ReflectionColor
    color = rhutil.coercecolor(color)
    if color:
        mat.ReflectionColor = color
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialShine(material_index, shine=None):
    """Returns or modifies a material's shine value
    Parameters:
      material_index = zero based material index
      shine[opt] = the new shine value. A material's shine value ranges from 0.0 to 255.0, with
        0.0 being matte and 255.0 being glossy
    Returns:
      if shine is not specified, the current material shine value
      if shine is specified, the previous material shine value
      None on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    rc = mat.Shine
    if shine:
        mat.Shine = shine
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialTexture(material_index, filename=None):
    """Returns or modifies a material's texture bitmap filename
    Parameters:
      material_index = zero based material index
      filename[opt] = the texture bitmap filename
    Returns:
      if filename is not specified, the current texture bitmap filename
      if filename is specified, the previous texture bitmap filename
      None if not successful or on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    texture = mat.GetBitmapTexture()
    rc = texture.FileName if texture else ""
    if filename:
        mat.SetBitmapTexture(filename)
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialTransparency(material_index, transparency=None):
    """Returns or modifies a material's transparency value
    Parameters:
      material_index = zero based material index
      transparency[opt] = the new transparency value. A material's transparency value ranges from 0.0 to 1.0, with
        0.0 being opaque and 1.0 being transparent
    Returns:
      if transparency is not specified, the current material transparency value
      if transparency is specified, the previous material transparency value
      None on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    rc = mat.Transparency
    if transparency:
        mat.Transparency = transparency
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def MaterialTransparencyMap(material_index, filename=None):
    """Returns or modifies a material's transparency bitmap filename
    Parameters:
      material_index = zero based material index
      filename[opt] = the transparency bitmap filename
    Returns:
      if filename is not specified, the current transparency bitmap filename
      if filename is specified, the previous transparency bitmap filename
      None if not successful or on error
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return scriptcontext.errorhandler()
    texture = mat.GetTransparencyTexture()
    rc = texture.FileName if texture else ""
    if filename:
        mat.SetTransparencyTexture(filename)
        mat.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def ResetMaterial(material_index):
    """Resets a material to Rhino's default material
    Parameters:
      material_index = zero based material index
    Returns:
      True or False indicating success or failure
    """
    mat = scriptcontext.doc.Materials[material_index]
    if mat is None: return False
    rc = scriptcontext.doc.Materials.ResetMaterial(material_index)
    scriptcontext.doc.Views.Redraw()
    return rc

########NEW FILE########
__FILENAME__ = mesh
import scriptcontext
import utility as rhutil
import Rhino
import System.Guid, System.Array, System.Drawing.Color
from view import __viewhelper

def AddMesh(vertices, face_vertices, vertex_normals=None, texture_coordinates=None, vertex_colors=None):
    """Add a mesh object to the document
    Parameters:
      vertices = list of 3D points defining the vertices of the mesh
      face_vertices = list containing lists of 3 or 4 numbers that define the
        vertex indices for each face of the mesh. If the third a fourth vertex
        indices of a face are identical, a triangular face will be created.
      vertex_normals[opt] = list of 3D vectors defining the vertex normals of
        the mesh. Note, for every vertex, there must be a corresponding vertex
        normal
      texture_coordinates[opt] = list of 2D texture coordinates. For every
        vertex, there must be a corresponding texture coordinate
      vertex_colors[opt] = a list of color values. For every vertex,
        there must be a corresponding vertex color
    Returns:
      Identifier of the new object if successful
      None on error
    """
    mesh = Rhino.Geometry.Mesh()
    for a, b, c in vertices: mesh.Vertices.Add(a, b, c)
    for face in face_vertices:
        if len(face)<4:
            mesh.Faces.AddFace(face[0], face[1], face[2])
        else:
            mesh.Faces.AddFace(face[0], face[1], face[2], face[3])
    if vertex_normals:
        count = len(vertex_normals)
        normals = System.Array.CreateInstance(Rhino.Geometry.Vector3f, count)
        for i, normal in enumerate(vertex_normals):
            normals[i] = Rhino.Geometry.Vector3f(normal[0], normal[1], normal[2])
        mesh.Normals.SetNormals(normals)
    if texture_coordinates:
        count = len(texture_coordinates)
        tcs = System.Array.CreateInstance(Rhino.Geometry.Point2f, count)
        for i, tc in enumerate(texture_coordinates):
            tcs[i] = Rhino.Geometry.Point2f(tc[0], tc[1])
        mesh.TextureCoordinates.SetTextureCoordinates(tcs)
    if vertex_colors:
        count = len(vertex_colors)
        colors = System.Array.CreateInstance(System.Drawing.Color, count)
        for i, color in enumerate(vertex_colors):
            colors[i] = rhutil.coercecolor(color)
        mesh.VertexColors.SetColors(colors)
    rc = scriptcontext.doc.Objects.AddMesh(mesh)
    if rc==System.Guid.Empty: raise Exception("unable to add mesh to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPlanarMesh(object_id, delete_input=False):
    """Creates a planar mesh from a closed, planar curve
    Parameters:
      object_id = identifier of a closed, planar curve
      delete_input[opt] = if True, delete the input curve defined by object_id
    Returns:
      id of the new mesh on success
      None on error
    """
    curve = rhutil.coercecurve(object_id, -1, True)
    mesh = Rhino.Geometry.Mesh.CreateFromPlanarBoundary(curve, Rhino.Geometry.MeshingParameters.Default)
    if not mesh: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddMesh(mesh)
    if rc==System.Guid.Empty: raise Exception("unable to add mesh to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def CurveMeshIntersection(curve_id, mesh_id, return_faces=False):
    """Calculates the intersection of a curve object and a mesh object
    Parameters:
      curve_id = identifier of a curve object
      mesh_id = identifier or a mesh object
      return_faces[opt] = return both intersection points and face indices.
        If False, then just the intersection points are returned
    Returns:
      if return_false is omitted or False, then a list of intersection points
      if return_false is True, the a one-dimensional list containing information
        about each intersection. Each element contains the following two elements
        (point of intersection, mesh face index where intersection lies)
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    mesh = rhutil.coercemesh(mesh_id, True)
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    polylinecurve = curve.ToPolyline(0,0,0,0,0.0,tolerance,0.0,0.0,True)
    pts, faceids = Rhino.Geometry.Intersect.Intersection.MeshPolyline(mesh, polylinecurve)
    if not pts: return scriptcontext.errorhandler()
    pts = list(pts)
    if return_faces:
        faceids = list(faceids)
        return zip(pts, faceids)
    return pts


def DisjointMeshCount(object_id):
    """Returns number of meshes that could be created by calling SplitDisjointMesh
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      The number of meshes that could be created
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.DisjointMeshCount


def DuplicateMeshBorder(mesh_id):
    """Creates curves that duplicates a mesh border
    Parameters:
      mesh_id = identifier of a mesh object
    Returns:
      list of curve ids on success
      None on error
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    polylines = mesh.GetNakedEdges()
    rc = []
    if polylines:
        for polyline in polylines:
            id = scriptcontext.doc.Objects.AddPolyline(polyline)
            if id!=System.Guid.Empty: rc.append(id)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def ExplodeMeshes(mesh_ids, delete=False):
    """Explodes a mesh object, or mesh objects int submeshes. A submesh is a
    collection of mesh faces that are contained within a closed loop of
    unwelded mesh edges. Unwelded mesh edges are where the mesh faces that
    share the edge have unique mesh vertices (not mesh topology vertices)
    at both ends of the edge
    Parameters:
      mesh_ids = list of mesh identifiers
      delete[opt] = delete the input meshes
    Returns:
      List of identifiers
    """
    id = rhutil.coerceguid(mesh_ids)
    if id: mesh_ids = [mesh_ids]
    rc = []
    for mesh_id in mesh_ids:
        mesh = rhutil.coercemesh(mesh_id, True)
        if mesh:
            submeshes = mesh.ExplodeAtUnweldedEdges()
            if submeshes:
                for submesh in submeshes:
                    id = scriptcontext.doc.Objects.AddMesh(submesh)
                    if id!=System.Guid.Empty: rc.append(id)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def IsMesh(object_id):
    "Verifies if an object is a mesh"
    mesh = rhutil.coercemesh(object_id)
    return mesh is not None


def IsMeshClosed(object_id):
    """Verifies a mesh object is closed
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.IsClosed


def IsMeshManifold(object_id):
    """Verifies a mesh object is manifold. A mesh for which every edge is shared
    by at most two faces is called manifold. If a mesh has at least one edge
    that is shared by more than two faces, then that mesh is called non-manifold
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    rc = mesh.IsManifold(True)
    return rc[0]


def IsPointOnMesh(object_id, point):
    """Verifies a point is on a mesh
    Parameters:
      object_id = identifier of a mesh object
      point = test point
    """
    mesh = rhutil.coercemesh(object_id, True)
    point = rhutil.coerce3dpoint(point, True)
    max_distance = Rhino.RhinoMath.SqrtEpsilon
    face, pt = mesh.ClosestPoint(point, max_distance)
    return face>=0


def JoinMeshes(object_ids, delete_input=False):
    """Joins two or or more mesh objects together
    Parameters:
      object_ids = identifiers of two or more mesh objects
      delete_input[opt] = delete input after joining
    Returns:
      identifier of newly created mesh on success
    """
    meshes = [rhutil.coercemesh(id,True) for id in object_ids]
    joined_mesh = Rhino.Geometry.Mesh()
    for mesh in meshes: joined_mesh.Append(mesh)
    rc = scriptcontext.doc.Objects.AddMesh(joined_mesh)
    if delete_input:
        for id in object_ids:
            guid = rhutil.coerceguid(id)
            scriptcontext.doc.Objects.Delete(guid,True)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshArea(object_ids):
    """Returns approximate area of one or more mesh objects
    Parameters:
      object_ids = identifiers of one or more mesh objects
    Returns:
      list containing 3 numbers if successful where
        element[0] = number of meshes used in calculation
        element[1] = total area of all meshes
        element[2] = the error estimate
      None if not successful
    """
    id = rhutil.coerceguid(object_ids)
    if id: object_ids = [object_ids]
    meshes_used = 0
    total_area = 0.0
    error_estimate = 0.0
    for id in object_ids:
        mesh = rhutil.coercemesh(id, True)
        if mesh:
            mp = Rhino.Geometry.AreaMassProperties.Compute(mesh)
            if mp:
                meshes_used += 1
                total_area += mp.Area
                error_estimate += mp.AreaError
    if meshes_used==0: return scriptcontext.errorhandler()
    return meshes_used, total_area, error_estimate


def MeshAreaCentroid(object_id):
    """Calculates the area centroid of a mesh object
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      Point3d representing the area centroid if successful
      None on error  
    """
    mesh = rhutil.coercemesh(object_id, True)
    mp = Rhino.Geometry.AreaMassProperties.Compute(mesh)
    if mp is None: return scriptcontext.errorhandler()
    return mp.Centroid


def MeshBooleanDifference(input0, input1, delete_input=True):
    """Performs boolean difference operation on two sets of input meshes
    Parameters:
      input0, input1 = identifiers of meshes
      delete_input[opt] = delete the input meshes
    Returns:
      list of identifiers of new meshes
    """
    id = rhutil.coerceguid(input0)
    if id: input0 = [id]
    id = rhutil.coerceguid(input1)
    if id: input1 = [id]
    meshes0 = [rhutil.coercemesh(id, True) for id in input0]
    meshes1 = [rhutil.coercemesh(id, True) for id in input1]
    if not meshes0 or not meshes1: raise ValueError("no meshes to work with")
    newmeshes = Rhino.Geometry.Mesh.CreateBooleanDifference(meshes0, meshes1)
    rc = []
    for mesh in newmeshes:
        id = scriptcontext.doc.Objects.AddMesh(mesh)
        if id!=System.Guid.Empty: rc.append(id)
    if rc and delete_input:
        input = input0 + input1
        for id in input:
            id = rhutil.coerceguid(id, True)
            scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshBooleanIntersection(input0, input1, delete_input=True):
    """Performs boolean intersection operation on two sets of input meshes
    Parameters:
      input0, input1 = identifiers of meshes
      delete_input[opt] = delete the input meshes
    Returns:
      list of identifiers of new meshes on success
    """
    id = rhutil.coerceguid(input0)
    if id: input0 = [id]
    id = rhutil.coerceguid(input1)
    if id: input1 = [id]
    meshes0 = [rhutil.coercemesh(id, True) for id in input0]
    meshes1 = [rhutil.coercemesh(id, True) for id in input1]
    if not meshes0 or not meshes1: raise ValueError("no meshes to work with")
    newmeshes = Rhino.Geometry.Mesh.CreateBooleanIntersection(meshes0, meshes1)
    rc = []
    for mesh in newmeshes:
        id = scriptcontext.doc.Objects.AddMesh(mesh)
        if id!=System.Guid.Empty: rc.append(id)
    if rc and delete_input:
        input = input0 + input1
        for id in input:
            id = rhutil.coerceguid(id, True)
            scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshBooleanSplit(input0, input1, delete_input=True):
    """Performs boolean split operation on two sets of input meshes
    Parameters:
      input0, input1 = identifiers of meshes
      delete_input[opt] = delete the input meshes
    Returns:
      list of identifiers of new meshes on success
      None on error
    """
    id = rhutil.coerceguid(input0)
    if id: input0 = [id]
    id = rhutil.coerceguid(input1)
    if id: input1 = [id]
    meshes0 = [rhutil.coercemesh(id, True) for id in input0]
    meshes1 = [rhutil.coercemesh(id, True) for id in input1]
    if not meshes0 or not meshes1: raise ValueError("no meshes to work with")
    newmeshes = Rhino.Geometry.Mesh.CreateBooleanSplit(meshes0, meshes1)
    rc = []
    for mesh in newmeshes:
        id = scriptcontext.doc.Objects.AddMesh(mesh)
        if id!=System.Guid.Empty: rc.append(id)
    if rc and delete_input:
        input = input0 + input1
        for id in input:
            id = rhutil.coerceguid(id, True)
            scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshBooleanUnion(mesh_ids, delete_input=True):
    """Performs boolean union operation on a set of input meshes
    Parameters:
      mesh_ids = identifiers of meshes
      delete_input[opt] = delete the input meshes
    Returns:
      list of identifiers of new meshes
    """
    if len(mesh_ids)<2: raise ValueError("mesh_ids must contain at least 2 meshes")
    meshes = [rhutil.coercemesh(id, True) for id in mesh_ids]
    newmeshes = Rhino.Geometry.Mesh.CreateBooleanUnion(meshes)
    rc = []
    for mesh in newmeshes:
        id = scriptcontext.doc.Objects.AddMesh(mesh)
        if id!=System.Guid.Empty: rc.append(id)
    if rc and delete_input:
        for id in mesh_ids:
            id = rhutil.coerceguid(id, True)
            scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshClosestPoint(object_id, point, maximum_distance=None):
    """Returns the point on a mesh that is closest to a test point
    Parameters:
      object_id = identifier of a mesh object
      point = point to test
      maximum_distance[opt] = upper bound used for closest point calculation.
        If you are only interested in finding a point Q on the mesh when
        point.DistanceTo(Q) < maximum_distance, then set maximum_distance to
        that value
    Returns:
      Tuple containing the results of the calculation where
        element[0] = the 3-D point on the mesh
        element[1] = the index of the mesh face on which the 3-D point lies
      None on error
    """
    mesh = rhutil.coercemesh(object_id, True)
    point = rhutil.coerce3dpoint(point, True)
    tolerance=maximum_distance if maximum_distance else 0.0
    face, closest_point = mesh.ClosestPoint(point, tolerance)
    if face<0: return scriptcontext.errorhandler()
    return closest_point, face


def MeshFaceCenters(mesh_id):
    """Returns the center of each face of the mesh object
    Parameters:
      mesh_id = identifier of a mesh object
    Returns:
      list of 3d points defining the center of each face
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    return [mesh.Faces.GetFaceCenter(i) for i in range(mesh.Faces.Count)]


def MeshFaceCount(object_id):
    """Returns total face count of a mesh object
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.Faces.Count


def MeshFaceNormals(mesh_id):
    """Returns the face unit normal for each face of a mesh object
    Paramters:
      mesh_id = identifier of a mesh object
    Returns:
      List of 3D vectors that define the face unit normals of the mesh
      None on error    
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    if mesh.FaceNormals.Count != mesh.Faces.Count:
        mesh.FaceNormals.ComputeFaceNormals()
    rc = []
    for i in xrange(mesh.FaceNormals.Count):
        normal = mesh.FaceNormals[i]
        rc.append(Rhino.Geometry.Vector3d(normal))
    return rc


def MeshFaces(object_id, face_type=True):
    """Returns face vertices of a mesh
    Parameters:
      object_id = identifier of a mesh object
      face_type[opt] = The face type to be returned. True = both triangles
        and quads. False = only triangles
    Returns:
      a list of 3D points that define the face vertices of the mesh. If
      face_type is True, then faces are returned as both quads and triangles
      (4 3D points). For triangles, the third and fourth vertex will be
      identical. If face_type is False, then faces are returned as only
      triangles(3 3D points). Quads will be converted to triangles.
    """
    mesh = rhutil.coercemesh(object_id, True)
    rc = []
    for i in xrange(mesh.Faces.Count):
        getrc, p0, p1, p2, p3 = mesh.Faces.GetFaceVertices(i)
        p0 = Rhino.Geometry.Point3d(p0)
        p1 = Rhino.Geometry.Point3d(p1)
        p2 = Rhino.Geometry.Point3d(p2)
        p3 = Rhino.Geometry.Point3d(p3)
        rc.append( p0 )
        rc.append( p1 )
        rc.append( p2 )
        if face_type:
            rc.append(p3)
        else:
            if p2!=p3:
                rc.append( p2 )
                rc.append( p3 )
                rc.append( p0 )
    return rc


def MeshFaceVertices(object_id):
    """Returns the vertex indices of all faces of a mesh object
    Paramters:
      object_id = identifier of a mesh object
    Returns:
      A list containing tuples of 4 numbers that define the vertex indices for
      each face of the mesh. Both quad and triangle faces are returned. If the
      third and fourth vertex indices are identical, the face is a triangle.
    """
    mesh = rhutil.coercemesh(object_id, True)
    rc = []
    for i in xrange(mesh.Faces.Count):
        face = mesh.Faces.GetFace(i)
        rc.append( (face.A, face.B, face.C, face.D) )
    return rc


def MeshHasFaceNormals(object_id):
    """Verifies a mesh object has face normals
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.FaceNormals.Count>0


def MeshHasTextureCoordinates(object_id):
    """Verifies a mesh object has texture coordinates
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.TextureCoordinates.Count>0


def MeshHasVertexColors(object_id):
    """Verifies a mesh object has vertex colors
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.VertexColors.Count>0


def MeshHasVertexNormals(object_id):
    """Verifies a mesh object has vertex normals
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.Normals.Count>0


def MeshMeshIntersection(mesh1, mesh2, tolerance=None):
    """Calculates the intersections of a mesh object with another mesh object
    Parameters:
      mesh1, mesh2 = identifiers of meshes
      tolerance[opt] = the intersection tolerance
    Returns:
      List of 3d point arrays that define the vertices of the intersection curves
    """
    mesh1 = rhutil.coercemesh(mesh1, True)
    mesh2 = rhutil.coercemesh(mesh2, True)
    if tolerance is None: tolerance = Rhino.RhinoMath.ZeroTolerance
    polylines = Rhino.Geometry.Intersect.Intersection.MeshMeshAccurate(mesh1, mesh2, tolerance)
    if polylines: return list(polylines)
    return []


def MeshNakedEdgePoints(object_id):
    """Identifies the naked edge points of a mesh object. This function shows
    where mesh vertices are not completely surrounded by faces. Joined
    meshes, such as are made by MeshBox, have naked mesh edge points where
    the sub-meshes are joined
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      List of boolean values that represent whether or not a mesh vertex is
      naked or not. The number of elements in the list will be equal to
      the value returned by MeshVertexCount. In which case, the list will
      identify the naked status for each vertex returned by MeshVertices
      None on error
    """
    mesh = rhutil.coercemesh(object_id, True)
    rc = mesh.GetNakedEdgePointStatus()
    return rc


def MeshOffset(mesh_id, distance):
    """Makes a new mesh with vertices offset at a distance in the opposite
    direction of the existing vertex normals
    Parameters:
      mesh_id = identifier of a mesh object
      distance = the distance to offset
    Returns:
      id of the new mesh object if successful
      None on error
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    offsetmesh = mesh.Offset(distance)
    if offsetmesh is None: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddMesh(offsetmesh)
    if rc==System.Guid.Empty: raise Exception("unable to add mesh to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshOutline(object_ids, view=None):
    """Creates polyline curve outlines of mesh objects
    Parameters:
      objects_ids = identifiers of meshes to outline
      view(opt) = view to use for outline direction
    Returns:
      list of polyline curve id on success
    """
    viewport = __viewhelper(view).MainViewport
    meshes = []
    mesh = rhutil.coercemesh(object_ids, False)
    if mesh: meshes.append(mesh)
    else: meshes = [rhutil.coercemesh(id,True) for id in object_ids]
    rc = []
    for mesh in meshes:
        polylines = mesh.GetOutlines(viewport)
        if not polylines: continue
        for polyline in polylines:
            id = scriptcontext.doc.Objects.AddPolyline(polyline)
            rc.append(id)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshQuadCount(object_id):
    """Returns the number of quad faces of a mesh object
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.Faces.QuadCount


def MeshQuadsToTriangles(object_id):
    """Converts a mesh object's quad faces to triangles
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      True or False indicating success or failure
    """
    mesh = rhutil.coercemesh(object_id, True)
    rc = True
    if mesh.Faces.QuadCount>0:
        rc = mesh.Faces.ConvertQuadsToTriangles()
        if rc:
            id = rhutil.coerceguid(object_id, True)
            scriptcontext.doc.Objects.Replace(id, mesh)
            scriptcontext.doc.Views.Redraw()
    return rc


def MeshToNurb(object_id, trimmed_triangles=True, delete_input=False):
    """Duplicates each polygon in a mesh with a NURBS surface. The resulting
    surfaces are then joined into a polysurface and added to the document
    Parameters:
      object_id = identifier of a mesh object
      trimmed_triangles[opt] = if True, triangles in the mesh will be
        represented by a trimmed plane
      delete_input[opt] = delete input object
    Returns:
      list of identifiers for the new breps on success
    """
    mesh = rhutil.coercemesh(object_id, True)
    pieces = mesh.SplitDisjointPieces()
    breps = [Rhino.Geometry.Brep.CreateFromMesh(piece,trimmed_triangles) for piece in pieces]
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    attr = rhobj.Attributes
    ids = [scriptcontext.doc.Objects.AddBrep(brep, attr) for brep in breps]
    if delete_input: scriptcontext.doc.Objects.Delete(rhobj, True)
    scriptcontext.doc.Views.Redraw()
    return ids


def MeshTriangleCount(object_id):
    """Returns number of triangular faces of a mesh
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.Faces.TriangleCount


def MeshVertexColors(mesh_id, colors=0):
    """Returns of modifies vertex colors of a mesh
    Parameters:
      mesh_id = identifier of a mesh object
      colors[opt] = A list of color values. Note, for each vertex, there must
        be a corresponding vertex color. If the value is None, then any
        existing vertex colors will be removed from the mesh
    Returns:
      if colors is not specified, the current vertex colors
      if colors is specified, the previous vertex colors
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    rc = [mesh.VertexColors[i] for i in range(mesh.VertexColors.Count)]
    if colors==0: return rc
    if colors is None:
        mesh.VertexColors.Clear()
    else:
        color_count = len(colors)
        if color_count!=mesh.Vertices.Count:
            raise ValueError("length of colors must match vertex count")
        colors = [rhutil.coercecolor(c) for c in colors]
        mesh.VertexColors.Clear()
        for c in colors: mesh.VertexColors.Add(c)
        id = rhutil.coerceguid(mesh_id, True)
        scriptcontext.doc.Objects.Replace(id, mesh)
    scriptcontext.doc.Views.Redraw()
    return rc


def MeshVertexCount(object_id):
    """Returns the vertex count of a mesh
    Parameters:
      object_id = identifier of a mesh object
    """
    mesh = rhutil.coercemesh(object_id, True)
    return mesh.Vertices.Count


def MeshVertexFaces(mesh_id, vertex_index):
    """Returns the mesh faces that share a specified mesh vertex
    Parameters:
      mesh_id = identifier of a mesh object
      vertex_index = index of the mesh vertex to find faces for
    Returns:
      list of face indices on success
      None on error
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    return mesh.Vertices.GetVertexFaces(vertex_index)


def MeshVertexNormals(mesh_id):
    """Returns the vertex unit normal for each vertex of a mesh
    Parameters:
      mesh_id = identifier of a mesh object
    Returns:
      list of vertex normals, (empty list if no normals exist)
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    count = mesh.Normals.Count
    if count<1: return []
    return [Rhino.Geometry.Vector3d(mesh.Normals[i]) for i in xrange(count)]


def MeshVertices(object_id):
    """Returns the vertices of a mesh
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      list of 3D points
    """
    mesh = rhutil.coercemesh(object_id, True)
    count = mesh.Vertices.Count
    rc = []
    for i in xrange(count):
        vertex = mesh.Vertices[i]
        rc.append(Rhino.Geometry.Point3d(vertex))
    return rc


def MeshVolume(object_ids):
    """
    Returns the approximate volume of one or more closed meshes
    Parameters:
      object_ids = identifiers of one or more mesh objects
    Returns:
      tuple containing 3 numbers if successful where
        element[0] = number of meshes used in volume calculation
        element[1] = total volume of all meshes
        element[2] = the error estimate
      None if not successful
    """
    id = rhutil.coerceguid(object_ids)
    if id: object_ids = [id]
    meshes_used = 0
    total_volume = 0.0
    error_estimate = 0.0
    for id in object_ids:
        mesh = rhutil.coercemesh(id, True)
        mp = Rhino.Geometry.VolumeMassProperties.Compute(mesh)
        if mp:
            meshes_used += 1
            total_volume += mp.Volume
            error_estimate += mp.VolumeError
    if meshes_used==0: return scriptcontext.errorhandler()
    return meshes_used, total_volume, error_estimate


def MeshVolumeCentroid(object_id):
    """Calculates the volume centroid of a mesh
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      Point3d representing the volume centroid
      None on error
    """
    mesh = rhutil.coercemesh(object_id, True)
    mp = Rhino.Geometry.VolumeMassProperties.Compute(mesh)
    if mp: return mp.Centroid
    return scriptcontext.errorhandler()


def PullCurveToMesh(mesh_id, curve_id):
    """Pulls a curve to a mesh. The function makes a polyline approximation of
    the input curve and gets the closest point on the mesh for each point on
    the polyline. Then it "connects the points" to create a polyline on the mesh
    Paramters:
      mesh_id = identifier of mesh that pulls
      curve_id = identifier of curve to pull
    Returns:
      Guid of new curve on success
      None on error
    """
    mesh = rhutil.coercemesh(mesh_id, True)
    curve = rhutil.coercecurve(curve_id, -1, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    polyline = curve.PullToMesh(mesh, tol)
    if not polyline: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddCurve(polyline)
    if rc==System.Guid.Empty: raise Exception("unable to add polyline to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def SplitDisjointMesh(object_id, delete_input=False):
    """Splits up a mesh into its unconnected pieces
    Parameters:
      object_id = identifier of a mesh object
      delete_input [opt] = delete the input object
    Returns:
      list of Guids for the new meshes
    """
    mesh = rhutil.coercemesh(object_id, True)
    pieces = mesh.SplitDisjointPieces()
    rc = [scriptcontext.doc.Objects.AddMesh(piece) for piece in pieces]
    if rc and delete_input:
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def UnifyMeshNormals(object_id):
    """Fixes inconsistencies in the directions of faces of a mesh
    Parameters:
      object_id = identifier of a mesh object
    Returns:
      number of faces that were modified
    """
    mesh = rhutil.coercemesh(object_id, True)
    rc = mesh.UnifyNormals()
    if rc>0:
        id = rhutil.coerceguid(object_id, True)
        scriptcontext.doc.Objects.Replace(id, mesh)
        scriptcontext.doc.Views.Redraw()
    return rc

########NEW FILE########
__FILENAME__ = object
import scriptcontext
import Rhino
import utility as rhutil
import System.Guid, System.Enum
from layer import __getlayer
from view import __viewhelper
import math


def CopyObject(object_id, translation=None):
    """Copies object from one location to another, or in-place.
    Parameters:
      object_id: object to copy
      translation[opt]: translation vector to apply
    Returns:
      id for the copy if successful
      None if not able to copy
    """
    rc = CopyObjects(object_id, translation)
    if rc: return rc[0]


def CopyObjects(object_ids, translation=None):
    """Copies one or more objects from one location to another, or in-place.
    Parameters:
      object_ids: list of objects to copy
      translation [opt]: list of three numbers or Vector3d representing
                         translation vector to apply to copied set
    Returns:
      list of identifiers for the copies if successful
    """
    if translation:
        translation = rhutil.coerce3dvector(translation, True)
        translation = Rhino.Geometry.Transform.Translation(translation)
    else:
        translation = Rhino.Geometry.Transform.Identity
    return TransformObjects(object_ids, translation, True)


def DeleteObject(object_id):
    """Deletes a single object from the document
    Parameters:
      object_id: identifier of object to delete
    Returns:
      True of False indicating success or failure
    """
    object_id = rhutil.coerceguid(object_id, True)
    rc = scriptcontext.doc.Objects.Delete(object_id, True)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def DeleteObjects(object_ids):
    """Deletes one or more objects from the document
    Parameters:
      object_ids: identifiers of objects to delete
    Returns:
      Number of objects deleted
    """
    rc = 0
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    for id in object_ids:
        id = rhutil.coerceguid(id, True)
        if scriptcontext.doc.Objects.Delete(id, True): rc+=1
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def FlashObject(object_ids, style=True):
    """Causes the selection state of one or more objects to change momentarily
    so the object appears to flash on the screen
    Parameters:
      object_ids = identifiers of objects to flash
      style[opt] = If True, flash between object color and selection color.
        If False, flash between visible and invisible
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rhobjs = [rhutil.coercerhinoobject(id, True, True) for id in object_ids]
    if rhobjs: scriptcontext.doc.Views.FlashObjects(rhobjs, style)


def HideObject(object_id):
    """Hides a single object
    Parameters:
      object_id: String or Guid representing id of object to hide
    Returns:
      True of False indicating success or failure
    """
    return HideObjects(object_id)==1


def HideObjects(object_ids):
    """Hides one or more objects
    Parameters:
      object_ids: identifiers of objects to hide
    Returns:
      Number of objects hidden
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rc = 0
    for id in object_ids:
        id = rhutil.coerceguid(id, True)
        if scriptcontext.doc.Objects.Hide(id, False): rc += 1
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def IsLayoutObject(object_id):
    """Verifies that an object is in either page layout space or model space
    Parameters:
      object_id: String or Guid representing id of an object
    Returns:
      True if the object is in page layout space
      False if the object is in model space
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.Attributes.Space == Rhino.DocObjects.ActiveSpace.PageSpace


def IsObject(object_id):
    """Verifies the existance of an object
    Parameters:
      object_id: The identifier of an object
    Returns:
      True if the object exists
      False if the object does not exist
    """
    return rhutil.coercerhinoobject(object_id, True, False) is not None


def IsObjectHidden(object_id):
    """Verifies that an object is hidden. Hidden objects are not visible, cannot
    be snapped to, and cannot be selected
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True if the object is hidden
      False if the object is not hidden
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsHidden


def IsObjectInBox(object_id, box, test_mode=True):
    """Verifies an object's bounding box is inside of another bounding box
    Parameters:
      object_id: String or Guid. The identifier of an object
      box: bounding box to test for containment
      test_mode[opt] = If True, the object's bounding box must be contained by box
        If False, the object's bounding box must be contained by or intersect box
    Returns:
      True if object is inside box
      False is object is not inside box
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    box = rhutil.coerceboundingbox(box, True)
    objbox = rhobj.Geometry.GetBoundingBox(True)
    if test_mode: return box.Contains(objbox)
    union = Rhino.Geometry.BoundingBox.Intersection(box, objbox)
    return union.IsValid


def IsObjectInGroup(object_id, group_name=None):
    """Verifies that an object is a member of a group
    Parameters:
      object_id: The identifier of an object
      group_name[opt]: The name of a group. If omitted, the function
        verifies that the object is a member of any group
    Returns:
      True if the object is a member of the specified group. If a group_name
        was not specified, the object is a member of some group.
      False if the object is not a member of the specified group. If a
        group_name was not specified, the object is not a member of any group
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    count = rhobj.GroupCount
    if count<1: return False
    if not group_name: return True
    index = scriptcontext.doc.Groups.Find(group_name, True)
    if index<0: raise ValueError("%s group does not exist"%group_name)
    group_ids = rhobj.GetGroupList()
    for id in group_ids:
        if id==index: return True
    return False


def IsObjectLocked(object_id):
    """Verifies that an object is locked. Locked objects are visible, and can
    be snapped to, but cannot be selected
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True if the object is locked
      False if the object is not locked
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsLocked


def IsObjectNormal(object_id):
    """Verifies that an object is normal. Normal objects are visible, can be
    snapped to, and can be selected
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True if the object is normal
      False if the object is not normal
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsNormal


def IsObjectReference(object_id):
    """Verifies that an object is a reference object. Reference objects are
    objects that are not part of the current document
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True if the object is a reference object
      False if the object is not a reference object
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsReference


def IsObjectSelectable(object_id):
    """Verifies that an object can be selected
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True or False
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsSelectable(True,False,False,False)


def IsObjectSelected(object_id):
    """Verifies that an object is currently selected
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True if the object is selected
      False if the object is not selected
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsSelected(False)


def IsObjectSolid(object_id):
    """Verifies that an object is a closed, solid object
    Parameters:
      object_id: String or Guid. The identifier of an object
    Returns:
      True if the object is solid
      False if the object is not solid
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    if( isinstance(rhobj, Rhino.DocObjects.BrepObject) or isinstance(rhobj, Rhino.DocObjects.SurfaceObject) ):
        return rhobj.Geometry.IsSolid
    if( isinstance(rhobj, Rhino.DocObjects.MeshObject) ):
        return rhobj.MeshGeometry.IsClosed
    return False


def IsObjectValid(object_id):
    """Verifies that an object's geometry is valid and without error
    Parameters:
      object_id: The identifier of an object
    Returns:
      True if the object is valid
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsValid

def IsVisibleInView(object_id, view=None):
    """Verifies an object is visible in a view"""
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.IsActiveInViewport(__viewhelper(view).MainViewport)


def LockObject(object_id):
    """Locks a single object. Locked objects are visible, and they can be
    snapped to. But, they cannot be selected.
    Parameters:
      object_id: The identifier of an object
    Returns:
      True or False indicating success or failure
    """
    return LockObjects(object_id)==1


def LockObjects(object_ids):
    """Locks one or more objects. Locked objects are visible, and they can be
    snapped to. But, they cannot be selected.
    Parameters:
      object_ids: list of Strings or Guids. The identifiers of objects
    Returns:
      number of objects locked
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rc = 0
    for id in object_ids:
        id = rhutil.coerceguid(id, True)
        if scriptcontext.doc.Objects.Lock(id, False): rc += 1
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def MatchObjectAttributes(target_ids, source_id=None):
    """Matches, or copies the attributes of a source object to a target object
    Parameters:
      target_ids = identifiers of objects to copy attributes to
      source_id[opt] = identifier of object to copy attributes from. If None,
        then the default attributes are copied to the target_ids
    Returns:
      number of objects modified
    """
    id = rhutil.coerceguid(target_ids, False)
    if id: target_ids = [id]
    source_attr = Rhino.DocObjects.ObjectAttributes()
    if source_id:
        source = rhutil.coercerhinoobject(source_id, True, True)
        source_attr = source.Attributes
    rc = 0
    for id in target_ids:
        id = rhutil.coerceguid(id, True)
        if scriptcontext.doc.Objects.ModifyAttributes(id, source_attr, True):
            rc += 1
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def MirrorObject(object_id, start_point, end_point, copy=False):
    """Mirrors a single object
    Parameters:
      object_id: String or Guid. The identifier of an object
      start_point: start of the mirror plane
      end_point: end of the mirror plane
      copy[opt] = copy the object
    Returns:
      Identifier of the mirrored object if successful
      None on error
    """
    rc = MirrorObjects(object_id, start_point, end_point, copy)
    if rc: return rc[0]


def MirrorObjects(object_ids, start_point, end_point, copy=False):
    """Mirrors a list of objects
    Parameters:
      object_ids: identifiers of objects to mirror
      start_point: start of the mirror plane
      end_point: end of the mirror plane
      copy[opt] = copy the objects
    Returns:
      List of identifiers of the mirrored objects if successful
    """
    start_point = rhutil.coerce3dpoint(start_point, True)
    end_point = rhutil.coerce3dpoint(end_point, True)
    vec = end_point-start_point
    if vec.IsTiny(0): raise Exception("start and end points are too close to each other")
    normal = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane().Normal
    vec = Rhino.Geometry.Vector3d.CrossProduct(vec, normal)
    vec.Unitize()
    xf = Rhino.Geometry.Transform.Mirror(start_point, vec)
    rc = TransformObjects(object_ids, xf, copy)
    return rc


def MoveObject(object_id, translation):
    """Moves a single object
    Parameters:
      object_id: String or Guid. The identifier of an object
      translation: list of 3 numbers or Vector3d
    Returns:
      Identifier of the moved object if successful
      None on error
    """
    rc = MoveObjects(object_id, translation)
    if rc: return rc[0]


def MoveObjects(object_ids, translation):
    """Moves one or more objects
    Parameters:
      object_ids: The identifiers objects to move
      translation: list of 3 numbers or Vector3d
    Returns:
      List of identifiers of the moved objects if successful
    """
    translation = rhutil.coerce3dvector(translation, True)
    xf = Rhino.Geometry.Transform.Translation(translation)
    rc = TransformObjects(object_ids, xf)
    return rc


def ObjectColor(object_ids, color=None):
    """Returns of modifies the color of an object. Object colors are represented
    as RGB colors. An RGB color specifies the relative intensity of red, green,
    and blue to cause a specific color to be displayed
    Parameters:
        object_ids = id or ids of object(s)
        color[opt] = the new color value. If omitted, then current object
            color is returned. If object_ids is a list, color is required
    Returns:
        If color value is not specified, the current color value
        If color value is specified, the previous color value
        If object_ids is a list, then the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    rhino_object = None
    rhino_objects = None
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
    else:
        rhino_objects = [rhutil.coercerhinoobject(id, True, True) for id in object_ids]
        if len(rhino_objects)==1:
            rhino_object = rhino_objects[0]
            rhino_objects = None
    if color is None:
        #get the color
        if rhino_objects: raise ValueError("color must be specified when a list of rhino objects is provided")
        return rhino_object.Attributes.DrawColor(scriptcontext.doc)
    color = rhutil.coercecolor(color, True)
    if rhino_objects is not None:
        for rh_obj in rhino_objects:
            attr = rh_obj.Attributes
            attr.ObjectColor = color
            attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
            scriptcontext.doc.Objects.ModifyAttributes( rh_obj, attr, True)
        return len(rhino_objects)
    rc = rhino_object.Attributes.DrawColor(scriptcontext.doc)
    attr = rhino_object.Attributes
    attr.ObjectColor = color
    attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
    scriptcontext.doc.Objects.ModifyAttributes( rhino_object, attr, True )
    scriptcontext.doc.Views.Redraw()
    return rc


def ObjectColorSource(object_ids, source=None):
    """Returns of modifies the color source of an object.
    Paramters:
      object_ids = single identifier of list of identifiers
      source[opt] = new color source
          0 = color from layer
          1 = color from object
          2 = color from material
          3 = color from parent
    Returns:
      if color source is not specified, the current color source
      is color source is specified, the previous color source
      if color_ids is a list, then the number of objects modifief
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhobj = rhutil.coercerhinoobject(id, True, True)
        rc = int(rhobj.Attributes.ColorSource)
        if source is not None:
            rhobj.Attributes.ColorSource = System.Enum.ToObject(Rhino.DocObjects.ObjectColorSource, source)
            rhobj.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc
    else:
        rc = 0
        source = System.Enum.ToObject(Rhino.DocObjects.ObjectColorSource, source)
        for id in object_ids:
            rhobj = rhutil.coercerhinoobject(id, True, True)
            rhobj.Attributes.ColorSource = source
            rhobj.CommitChanges()
            rc += 1
        if rc: scriptcontext.doc.Views.Redraw()
        return rc


def ObjectDescription(object_id):
    """Returns a short text description of an object
    Parameters:
      object_id = identifier of an object
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    return rhobj.ShortDescription(False)


def ObjectGroups(object_id):
    """Returns all of the group names that an object is assigned to
    Parameters:
      object_id = identifier of an object
    Returns:
      list of group names on success
    """
    rhino_object = rhutil.coercerhinoobject(object_id, True, True)
    if rhino_object.GroupCount<1: return []
    group_indices = rhino_object.GetGroupList()
    rc = [scriptcontext.doc.Groups.GroupName(index) for index in group_indices]
    return rc


def ObjectLayer(object_id, layer=None):
    """Returns or modifies the layer of an object
    Parameters:
      object_id = the identifier of the object(s)
      layer[opt] = name of an existing layer
    Returns:
      If a layer is not specified, the object's current layer
      If a layer is specified, the object's previous layer
      If object_id is a list or tuple, the number of objects modified
    """
    if type(object_id) is not str and hasattr(object_id, "__len__"):
        layer = __getlayer(layer, True)
        index = layer.LayerIndex
        for id in object_id:
            obj = rhutil.coercerhinoobject(id, True, True)
            obj.Attributes.LayerIndex = index
            obj.CommitChanges()
        scriptcontext.doc.Views.Redraw()
        return len(object_id)
    obj = rhutil.coercerhinoobject(object_id, True, True)
    if obj is None: return scriptcontext.errorhandler()
    index = obj.Attributes.LayerIndex
    rc = scriptcontext.doc.Layers[index].Name
    if layer:
        layer = __getlayer(layer, True)
        index = layer.LayerIndex
        obj.Attributes.LayerIndex = index
        obj.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def ObjectLayout(object_id, layout=None, return_name=True):
    """Returns or changes the layout or model space of an object
    Parameters:
      object_id = identifier of the object
      layout[opt] = to change, or move, an object from model space to page
        layout space, or from one page layout to another, then specify the
        title or identifier of an existing page layout view. To move an object
        from page layout space to model space, just specify None
      return_name[opt] = If True, the name, or title, of the page layout view
        is returned. If False, the identifier of the page layout view is returned
    Returns:
      if layout is not specified, the object's current page layout view
      if layout is specfied, the object's previous page layout view
      None if not successful
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    rc = None
    if rhobj.Attributes.Space==Rhino.DocObjects.ActiveSpace.PageSpace:
        page_id = rhobj.Attributes.ViewportId
        pageview = scriptcontext.doc.Views.Find(page_id)
        if return_name: rc = pageview.MainViewport.Name
        else: rc = pageview.MainViewport.Id
        if layout is None: #move to model space
            rhobj.Attributes.Space = Rhino.DocObjects.ActiveSpace.ModelSpace
            rhobj.Attributes.ViewportId = System.Guid.Empty
            rhobj.CommitChanges()
            scriptcontext.doc.Views.Redraw()
    else:
        if layout:
            layout = scriptcontext.doc.Views.Find(layout, False)
            if layout is not None and isinstance(layout, Rhino.Display.RhinoPageView):
                rhobj.Attributes.ViewportId = layout.MainViewport.Id
                rhobj.Attributes.Space = Rhino.DocObjects.ActiveSpace.PageSpace
                rhobj.CommitChanges()
                scriptcontext.doc.Views.Redraw()
    return rc


def ObjectLinetype(object_ids, linetype=None):
    """Returns of modifies the linetype of an object
    Parameters:
      object_ids = identifiers of object(s)
      linetype[opt] = name of an existing linetype. If omitted, the current
        linetype is returned. If object_ids is a list of identifiers, this parameter
        is required
    Returns:
      If a linetype is not specified, the object's current linetype
      If linetype is specified, the object's previous linetype
      If object_ids is a list, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        oldindex = scriptcontext.doc.Linetypes.LinetypeIndexForObject(rhino_object)
        if linetype:
            newindex = scriptcontext.doc.Linetypes.Find(linetype, True)
            rhino_object.Attributes.LinetypeSource = Rhino.DocObjects.ObjectLinetypeSource.LinetypeFromObject
            rhino_object.Attributes.LinetypeIndex = newindex
            rhino_object.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return scriptcontext.doc.Linetypes[oldindex].Name

    newindex = scriptcontext.doc.Linetypes.Find(linetype, True)
    if newindex<0: raise Exception("%s does not exist in LineTypes table"%linetype)
    for id in object_ids:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.LinetypeSource = Rhino.DocObjects.ObjectLinetypeSource.LinetypeFromObject
        rhino_object.Attributes.LinetypeIndex = newindex
        rhino_object.CommitChanges()
    scriptcontext.doc.Views.Redraw()
    return len(object_ids)


def ObjectLinetypeSource(object_ids, source=None):
    """Returns of modifies the linetype source of an object
    Parameters:
      object_ids = identifiers of object(s)
      source[opt] = new linetype source. If omitted, the current source is returned.
        If object_ids is a list of identifiers, this parameter is required
          0 = By Layer
          1 = By Object
          3 = By Parent
    Returns:
      If a source is not specified, the object's current linetype source
      If source is specified, the object's previous linetype source
      If object_ids is a list, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        oldsource = rhino_object.Attributes.LinetypeSource
        if source is not None:
            source = System.Enum.ToObject(Rhino.DocObjects.ObjectLinetypeSource, source)
            rhino_object.Attributes.LinetypeSource = source
            rhino_object.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return int(oldsource)
    source = System.Enum.ToObject(Rhino.DocObjects.ObjectLinetypeSource, source)
    for id in object_ids:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.LinetypeSource = source
        rhino_object.CommitChanges()
    scriptcontext.doc.Views.Redraw()
    return len(object_ids)


def ObjectMaterialIndex(object_id):
    """Returns the material index of an object. Rendering materials are stored in
    Rhino's rendering material table. The table is conceptually an array. Render
    materials associated with objects and layers are specified by zero based
    indices into this array.
    Parameters:
      object_id = identifier of an object
    Returns:
      If the return value of ObjectMaterialSource is "material by object", then
      the return value of this function is the index of the object's rendering
      material. A material index of -1 indicates no material has been assigned,
      and that Rhino's internal default material has been assigned to the object.
      None on failure      
    """
    rhino_object = rhutil.coercerhinoobject(object_id, True, True)
    return rhino_object.Attributes.MaterialIndex


def ObjectMaterialSource(object_ids, source=None):
    """Returns or modifies the rendering material source of an object.
    Parameters:
      object_ids = one or more object identifiers
      source [opt] = The new rendering material source. If omitted and a single
        object is provided in object_ids, then the current material source is
        returned. This parameter is required if multiple objects are passed in
        object_ids
        0 = Material from layer
        1 = Material from object
        3 = Material from parent
    Returns:
      If source is not specified, the current rendering material source
      If source is specified, the previous rendering material source
      If object_ids refers to multiple objects, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: # working with single object
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rc = int(rhino_object.Attributes.MaterialSource)
        if source is not None:
            rhino_object.Attributes.MaterialSource = System.Enum.ToObject(Rhino.DocObjects.ObjectMaterialSource, source)
            rhino_object.CommitChanges()
        return rc
    # else working with multiple objects
    if source is None: raise Exception("source is required when object_ids represents multiple objects")
    source = System.Enum.ToObject(Rhino.DocObjects.ObjectMaterialSource, source)
    for id in object_ids:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.MaterialSource = source
        rhino_object.CommitChanges()
    return len(object_ids)


def ObjectName(object_id, name=None):
    """Returns or modifies the name of an object
    Parameters:
      object_id = id or ids of object(s)
      name[opt] = the new object name. If omitted, the current name is returned
    Returns:
      If name is not specified, the current object name
      If name is specified, the previous object name
      If object_id is a list, the number of objects changed
    """
    id = rhutil.coerceguid(object_id, False)
    rhino_object = None
    rhino_objects = None
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
    else:
        rhino_objects = [rhutil.coercerhinoobject(id, True, True) for id in object_id]
        if not rhino_objects: return 0
        if len(rhino_objects)==1:
            rhino_object = rhino_objects[0]
            rhino_objects = None
    if name is None: #get the name
        if rhino_objects: raise Exception("name required when object_id represents multiple objects")
        return rhino_object.Name
    if rhino_objects:
        for rh_obj in rhino_objects:
            attr = rh_obj.Attributes
            attr.Name = name
            scriptcontext.doc.Objects.ModifyAttributes(rh_obj, attr, True)
        return len(rhino_objects)
    rc = rhino_object.Name
    if not type(name) is str: name = str(name)
    rhino_object.Attributes.Name = name
    rhino_object.CommitChanges()
    return rc


def ObjectPrintColor(object_ids, color=None):
    """Returns or modifies the print color of an object
    Parameters:
      object_ids = identifiers of object(s)
      color[opt] = new print color. If omitted, the current color is returned.
    Returns:
      If color is not specified, the object's current print color
      If color is specified, the object's previous print color
      If object_ids is a list or tuple, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rc = rhino_object.Attributes.PlotColor
        if color:
            rhino_object.Attributes.PlotColorSource = Rhino.DocObjects.ObjectPlotColorSource.PlotColorFromObject
            rhino_object.Attributes.PlotColor = rhutil.coercecolor(color, True)
            rhino_object.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc
    for id in object_ids:
        color = rhutil.coercecolor(color, True)
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.PlotColorSource = Rhino.DocObjects.ObjectPlotColorSource.PlotColorFromObject
        rhino_object.Attributes.PlotColor = color
        rhino_object.CommitChanges()
    scriptcontext.doc.Views.Redraw()
    return len(object_ids)


def ObjectPrintColorSource(object_ids, source=None):
    """Returns or modifies the print color source of an object
    Parameters:
      object_ids = identifiers of object(s)
      source[opt] = new print color source
        0 = print color by layer
        1 = print color by object
        3 = print color by parent
    Returns:
      If source is not specified, the object's current print color source
      If source is specified, the object's previous print color source
      If object_ids is a list or tuple, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rc = int(rhino_object.Attributes.PlotColorSource)
        if source is not None:
            rhino_object.Attributes.PlotColorSource = System.Enum.ToObject(Rhino.DocObjects.ObjectPlotColorSource, source)
            rhino_object.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc
    for id in object_ids:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.PlotColorSource = System.Enum.ToObject(Rhino.DocObjects.ObjectPlotColorSource, source)
        rhino_object.CommitChanges()
    scriptcontext.doc.Views.Redraw()
    return len(object_ids)


def ObjectPrintWidth(object_ids, width=None):
    """Returns or modifies the print width of an object
    Parameters:
      object_ids = identifiers of object(s)
      width[opt] = new print width value in millimeters, where width=0 means use
        the default width, and width<0 means do not print (visible for screen display,
        but does not show on print). If omitted, the current width is returned.
    Returns:
      If width is not specified, the object's current print width
      If width is specified, the object's previous print width
      If object_ids is a list or tuple, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rc = rhino_object.Attributes.PlotWeight
        if width is not None:
            rhino_object.Attributes.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
            rhino_object.Attributes.PlotWeight = width
            rhino_object.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc
    for id in object_ids:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
        rhino_object.Attributes.PlotWeight = width
        rhino_object.CommitChanges()
    scriptcontext.doc.Views.Redraw()
    return len(object_ids)


def ObjectPrintWidthSource(object_ids, source=None):
    """Returns or modifies the print width source of an object
    Parameters:
      object_ids = identifiers of object(s)
      source[opt] = new print width source
        0 = print width by layer
        1 = print width by object
        3 = print width by parent
    Returns:
      If source is not specified, the object's current print width source
      If source is specified, the object's previous print width source
      If object_ids is a list or tuple, the number of objects modified
    """
    id = rhutil.coerceguid(object_ids, False)
    if id:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rc = int(rhino_object.Attributes.PlotWeightSource)
        if source is not None:
            rhino_object.Attributes.PlotWeightSource = System.Enum.ToObject(Rhino.DocObjects.ObjectPlotWeightSource, source)
            rhino_object.CommitChanges()
            scriptcontext.doc.Views.Redraw()
        return rc
    for id in object_ids:
        rhino_object = rhutil.coercerhinoobject(id, True, True)
        rhino_object.Attributes.PlotWeightSource = System.Enum.ToObject(Rhino.DocObjects.ObjectPlotWeightSource, source)
        rhino_object.CommitChanges()
    scriptcontext.doc.Views.Redraw()
    return len(object_ids)


def ObjectType(object_id):
    """Returns the object type
    Parameters:
      object_id = identifier of an object
    Returns:
      see help for values
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    geom = rhobj.Geometry
    if isinstance(geom, Rhino.Geometry.Brep) and geom.Faces.Count==1:
        return 8 #surface
    return int(geom.ObjectType)


def OrientObject(object_id, reference, target, flags=0):
    """Orients a single object based on input points
    Parameters:
        object_id = String or Guid. The identifier of an object
        reference = list of 3-D reference points
        target = list of 3-D target points
        flags[opt]: 1 = copy object
                    2 = scale object
    """
    object_id = rhutil.coerceguid(object_id, True)
    from_array = rhutil.coerce3dpointlist(reference)
    to_array = rhutil.coerce3dpointlist(target)
    if from_array is None or to_array is None:
        raise ValueError("Could not convert reference or target to point list")
    from_count = len(from_array)
    to_count = len(to_array)
    if from_count<2 or to_count<2: raise Exception("point lists must have at least 2 values")

    copy = ((flags & 1) == 1)
    scale = ((flags & 2) == 2)
    xform_final = None
    if from_count>2 and to_count>2:
        #Orient3Pt
        from_plane = Rhino.Geometry.Plane(from_array[0], from_array[1], from_array[2])
        to_plane = Rhino.Geometry.Plane(to_array[0], to_array[1], to_array[2])
        if not from_plane.IsValid or not to_plane.IsValid:
            raise Exception("unable to create valid planes from point lists")
        xform_final = Rhino.Geometry.Transform.PlaneToPlane(from_plane, to_plane)
    else:
        #Orient2Pt
        xform_move = Rhino.Geometry.Transform.Translation( to_array[0]-from_array[0] )
        xform_scale = Rhino.Geometry.Transform.Identity
        v0 = from_array[1] - from_array[0]
        v1 = to_array[1] - to_array[0]
        if scale:
            len0 = v0.Length
            len1 = v1.Length
            if len0<0.000001 or len1<0.000001: raise Exception("vector lengths too short")
            scale = len1 / len0
            if abs(1.0-scale)>=0.000001:
                plane = Rhino.Geometry.Plane(from_array[0], v0)
                xform_scale = Rhino.Geometry.Transform.Scale(plane, scale, scale, scale)
        v0.Unitize()
        v1.Unitize()
        xform_rotate = Rhino.Geometry.Transform.Rotation(v0, v1, from_array[0])
        xform_final = xform_move * xform_scale * xform_rotate
    rc = scriptcontext.doc.Objects.Transform(object_id, xform_final, not copy)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def RotateObject(object_id, center_point, rotation_angle, axis=None, copy=False):
    """Rotates a single object
    Parameters:
      object_id: String or Guid. The identifier of an object
      center_point: the center of rotation
      rotation_angle: in degrees
      axis[opt] = axis of rotation, If omitted, the Z axis of the active
        construction plane is used as the rotation axis
      copy[opt] = copy the object
    Returns:
      Identifier of the rotated object if successful
      None on error
    """
    rc = RotateObjects(object_id, center_point, rotation_angle, axis, copy)
    if rc: return rc[0]
    return scriptcontext.errorhandler()


def RotateObjects( object_ids, center_point, rotation_angle, axis=None, copy=False):
    """Rotates multiple objects
    Parameters:
      object_ids: Identifiers of objects to rotate
      center_point: the center of rotation
      rotation_angle: in degrees
      axis[opt] = axis of rotation, If omitted, the Z axis of the active
        construction plane is used as the rotation axis
      copy[opt] = copy the object
    Returns:
      List of identifiers of the rotated objects if successful
    """
    center_point = rhutil.coerce3dpoint(center_point, True)
    if not axis:
        axis = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane().Normal
    axis = rhutil.coerce3dvector(axis, True)
    rotation_angle = Rhino.RhinoMath.ToRadians(rotation_angle)
    xf = Rhino.Geometry.Transform.Rotation(rotation_angle, axis, center_point)
    rc = TransformObjects(object_ids, xf, copy)
    return rc


def ScaleObject(object_id, origin, scale, copy=False):
    """Scales a single object. Can be used to perform a uniform or non-uniform
    scale transformation. Scaling is based on the active construction plane.
    Parameters:
      object_id: The identifier of an object
      origin: the origin of the scale transformation
      scale: three numbers that identify the X, Y, and Z axis scale factors to apply
      copy[opt] = copy the object
    Returns:
      Identifier of the scaled object if successful
      None on error
    """
    rc = ScaleObjects(object_id, origin, scale, copy )
    if rc: return rc[0]
    return scriptcontext.errorhandler()


def ScaleObjects(object_ids, origin, scale, copy=False):
    """Scales one or more objects. Can be used to perform a uniform or non-
    uniform scale transformation. Scaling is based on the active construction plane.
    Parameters:
      object_ids: Identifiers of objects to scale
      origin: the origin of the scale transformation
      scale: three numbers that identify the X, Y, and Z axis scale factors to apply
      copy[opt] = copy the objects
    Returns:
      List of identifiers of the scaled objects if successful
      None on error
    """
    origin = rhutil.coerce3dpoint(origin, True)
    scale = rhutil.coerce3dpoint(scale, True)
    plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
    plane.Origin = origin
    xf = Rhino.Geometry.Transform.Scale(plane, scale.X, scale.Y, scale.Z)
    rc = TransformObjects(object_ids, xf, copy)
    return rc


def SelectObject(object_id):
    """Selects a single object
    Parameters:
      object_id = the identifier of the object to select
    Returns:
      True on success
    """
    rhobj = rhutil.coercerhinoobject(object_id, True, True)
    rhobj.Select(True)
    scriptcontext.doc.Views.Redraw()
    return True


def SelectObjects( object_ids):
    """Selects one or more objects
    Parameters:
      object_ids = list of Guids identifying the objects to select
    Returns:
      number of selected objects
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rc = 0
    for id in object_ids:
        if SelectObject(id)==True: rc += 1
    return rc


def ShearObject(object_id, origin, reference_point, angle_degrees, copy=False):
    """Perform a shear transformation on a single object
    Parameters:
      object_id: String or Guid. The identifier of an object
      origin, reference_point: origin/reference point of the shear transformation
    Returns:
      Identifier of the sheared object if successful
      None on error
    """
    rc = ShearObjects(object_id, origin, reference_point, angle_degrees, copy)
    if rc: return rc[0]


def ShearObjects(object_ids, origin, reference_point, angle_degrees, copy=False):
    """Shears one or more objects
    Parameters:
      object_ids: The identifiers objects to shear
      origin, reference_point: origin/reference point of the shear transformation
    Returns:
      List of identifiers of the sheared objects if successful
    """
    origin = rhutil.coerce3dpoint(origin, True)
    reference_point = rhutil.coerce3dpoint(reference_point, True)
    if (origin-reference_point).IsTiny(): return None
    plane = scriptcontext.doc.Views.ActiveView.MainViewport.ConstructionPlane()
    frame = Rhino.Geometry.Plane(plane)
    frame.Origin = origin
    frame.ZAxis = plane.Normal
    yaxis = reference_point-origin
    yaxis.Unitize()
    frame.YAxis = yaxis
    xaxis = Rhino.Geometry.Vector3d.CrossProduct(frame.ZAxis, frame.YAxis)
    xaxis.Unitize()
    frame.XAxis = xaxis

    world_plane = Rhino.Geometry.Plane.WorldXY
    cob = Rhino.Geometry.Transform.ChangeBasis(world_plane, frame)
    shear2d = Rhino.Geometry.Transform.Identity
    shear2d[0,1] = math.tan(math.radians(angle_degrees))
    cobinv = Rhino.Geometry.Transform.ChangeBasis(frame, world_plane)
    xf = cobinv * shear2d * cob
    rc = TransformObjects(object_ids, xf, copy)
    return rc


def ShowObject(object_id):
    """Shows a previously hidden object. Hidden objects are not visible, cannot
    be snapped to and cannot be selected
    Parameters:
      object_id: String or Guid representing id of object to show
    Returns:
      True of False indicating success or failure
    """
    return ShowObjects(object_id)==1


def ShowObjects(object_ids):
    """Shows one or more objects. Hidden objects are not visible, cannot be
    snapped to and cannot be selected
    Parameters:
      object_ids: list of Strings or Guids representing ids of objects to show
    Returns:
      Number of objects shown
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rc = 0
    for id in object_ids:
        id = rhutil.coerceguid(id, True)
        if scriptcontext.doc.Objects.Show(id, False): rc += 1
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def TransformObject(object_id, matrix, copy=False):
    """Moves, scales, or rotates an object given a 4x4 transformation matrix.
    The matrix acts on the left.
    Parameters:
      object = The identifier of the object.
      matrix = The transformation matrix (4x4 array of numbers).
      copy [opt] = Copy the object.
    Returns:
      The identifier of the transformed object
      None if not successful, or on error
    """
    rc = TransformObjects(object_id, matrix, copy)
    if rc: return rc[0]
    return scriptcontext.errorhandler()

# this is also called by Copy, Scale, Mirror, Move, and Rotate functions defined above
def TransformObjects(object_ids, matrix, copy=False):
    """Moves, scales, or rotates a list of objects given a 4x4 transformation
    matrix. The matrix acts on the left.
    Parameters:
      object_ids = List of object identifiers.
      matrix = The transformation matrix (4x4 array of numbers).
      copy[opt] = Copy the objects
    Returns:
      List of ids identifying the newly transformed objects
    """
    xform = rhutil.coercexform(matrix, True)
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rc = []
    for object_id in object_ids:
        object_id = rhutil.coerceguid(object_id, True)
        id = scriptcontext.doc.Objects.Transform(object_id, xform, not copy)
        if id!=System.Guid.Empty: rc.append(id)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def UnlockObject(object_id):
    """Unlocks an object. Locked objects are visible, and can be snapped to,
    but they cannot be selected.
    Parameters:
      object_id: The identifier of an object
    Returns:
      True or False indicating success or failure
    """
    return UnlockObjects(object_id)==1


def UnlockObjects(object_ids):
    """Unlocks one or more objects. Locked objects are visible, and can be
    snapped to, but they cannot be selected.
    Parameters:
      object_ids: The identifiers of objects
    Returns:
      number of objects unlocked
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    rc = 0
    for id in object_ids:
        id = rhutil.coerceguid(id, True)
        if scriptcontext.doc.Objects.Unlock(id, False): rc += 1
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def UnselectObject(object_id):
    """Unselects a single selected object
    Parameters:
      object_id: String or Guid representing id of object to unselect
    Returns:
      True of False indicating success or failure
    """
    return UnselectObjects(object_id)==1


def UnselectObjects(object_ids):
    """Unselects one or more selected objects.
    Parameters:
      object_ids = identifiers of the objects to unselect.
    Returns:
      The number of objects unselected
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    count = len(object_ids)
    for id in object_ids:
        obj = rhutil.coercerhinoobject(id, True, True)
        obj.Select(False)
    if count: scriptcontext.doc.Views.Redraw()
    return count

########NEW FILE########
__FILENAME__ = plane
import utility as rhutil
import Rhino.Geometry
import scriptcontext
import math

def DistanceToPlane(plane, point):
    "Returns the distance from a 3D point to a plane"
    plane = rhutil.coerceplane(plane, True)
    point = rhutil.coerce3dpoint(point, True)
    return plane.DistanceTo(point)


def EvaluatePlane(plane, parameter):
    """Evaluates a plane at a U,V parameter
    Parameters:
      plane = the plane to evaluate
      parameter = list of two numbers defining the U,V parameter to evaluate
    Returns:
      Point3d on success
    """
    plane = rhutil.coerceplane(plane, True)
    return plane.PointAt(parameter[0], parameter[1])


def IntersectPlanes(plane1, plane2, plane3):
    """Calculates the intersection of three planes
    Returns:
      Point3d on success
      None on error
    """
    plane1 = rhutil.coerceplane(plane1, True)
    plane2 = rhutil.coerceplane(plane2, True)
    plane3 = rhutil.coerceplane(plane3, True)
    rc, point = Rhino.Geometry.Intersect.Intersection.PlanePlanePlane(plane1, plane2, plane3)
    if rc: return point


def MovePlane(plane, origin):
    """Moves the origin of a plane
    Parameters:
      plane = Plane or ConstructionPlane
      origin = Point3d or list of three numbers
    Returns:
      moved plane
    """
    plane = rhutil.coerceplane(plane, True)
    origin = rhutil.coerce3dpoint(origin, True)
    rc = Rhino.Geometry.Plane(plane)
    rc.Origin = origin
    return rc


def PlaneClosestPoint(plane, point, return_point=True):
    """Returns the point on a plane that is closest to a test point.
    Parameters:
      plane = The plane
      point = The 3-D point to test.
      return_point [opt] = If omitted or True, then the point on the plane
         that is closest to the test point is returned. If False, then the
         parameter of the point on the plane that is closest to the test
         point is returned.
    Returns:
      If return_point is omitted or True, then the 3-D point
      If return_point is False, then an array containing the U,V parameters
      of the point
      None if not successful, or on error.
    """
    plane = rhutil.coerceplane(plane, True)
    point = rhutil.coerce3dpoint(point, True)
    if return_point:
        return plane.ClosestPoint(point)
    else:
        rc, s, t = plane.ClosestParameter(point)
        if rc: return s, t


def PlaneCurveIntersection(plane, curve, tolerance=None):
    "Intersect an infinite plane and a curve object"
    plane = rhutil.coerceplane(plane, True)
    curve = rhutil.coercecurve(curve, -1, True)
    if tolerance is None: tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    intersections = Rhino.Geometry.Intersect.Intersection.CurvePlane(curve, plane, tolerance)
    if intersections:
        rc = []
        for intersection in intersections:
            a = 1
            if intersection.IsOverlap: a = 2
            b = intersection.PointA
            c = intersection.PointA2
            d = intersection.PointB
            e = intersection.PointB2
            f = intersection.ParameterA
            g = intersection.ParameterB
            h = intersection.OverlapA[0]
            i = intersection.OverlapA[1]
            j = intersection.OverlapB[0]
            k = intersection.OverlapB[1]
            rc.append( (a,b,c,d,e,f,g,h,i,j,k) )
        return rc


def PlaneEquation(plane):
    """Returns the equation of a plane as a tuple of four numbers. The standard
    equation of a plane with a non-zero vector is Ax+By+Cz+D=0
    """
    plane = rhutil.coerceplane(plane, True)
    rc = plane.GetPlaneEquation()
    return rc[0], rc[1], rc[2], rc[3]


def PlaneFitFromPoints(points):
    """Returns a plane that was fit through an array of 3D points.
    Parameters:
    points = An array of 3D points.
    Returns: 
      The plane if successful
      None if not successful
    """
    points = rhutil.coerce3dpointlist(points, True)
    rc, plane = Rhino.Geometry.Plane.FitPlaneToPoints(points)
    if rc==Rhino.Geometry.PlaneFitResult.Success: return plane


def PlaneFromFrame(origin, x_axis, y_axis):
    """Construct a plane from a point, and two vectors in the plane.
    Parameters:
      origin = A 3D point identifying the origin of the plane.
      x_axis = A non-zero 3D vector in the plane that determines the X axis
               direction.
      y_axis = A non-zero 3D vector not parallel to x_axis that is used
               to determine the Y axis direction. Note, y_axis does not
               have to be perpendicular to x_axis.
    Returns:
      The plane if successful. 
    """
    origin = rhutil.coerce3dpoint(origin, True)
    x_axis = rhutil.coerce3dvector(x_axis, True)
    y_axis = rhutil.coerce3dvector(y_axis, True)
    return Rhino.Geometry.Plane(origin, x_axis, y_axis)


def PlaneFromNormal(origin, normal, xaxis=None):
    """Creates a plane from an origin point and a normal direction vector.
    Parameters:
      origin = A 3D point identifying the origin of the plane.
      normal = A 3D vector identifying the normal direction of the plane.
      xaxis[opt] = optional vector defining the plane's x-axis
    Returns:
      The plane if successful.
    """
    origin = rhutil.coerce3dpoint(origin, True)
    normal = rhutil.coerce3dvector(normal, True)
    rc = Rhino.Geometry.Plane(origin, normal)
    if xaxis:
        xaxis = rhutil.coerce3dvector(xaxis, True)
        xaxis = Rhino.Geometry.Vector3d(xaxis)#prevent original xaxis parameter from being unitized too
        xaxis.Unitize()
        yaxis = Rhino.Geometry.Vector3d.CrossProduct(rc.Normal, xaxis)
        rc = Rhino.Geometry.Plane(origin, xaxis, yaxis)
    return rc


def PlaneFromPoints(origin, x, y):
    """Creates a plane from three non-colinear points
    Parameters:
      origin = origin point of the plane
      x, y = points on the plane's x and y axes
    """
    origin = rhutil.coerce3dpoint(origin, True)
    x = rhutil.coerce3dpoint(x, True)
    y = rhutil.coerce3dpoint(y, True)
    plane = Rhino.Geometry.Plane(origin, x, y)
    if plane.IsValid: return plane


def PlanePlaneIntersection(plane1, plane2):
    """Calculates the intersection of two planes
    Paramters:
      plane1, plane2 = two planes
    Returns:
      two 3d points identifying the starting/ending points of the intersection
      None on error
    """
    plane1 = rhutil.coerceplane(plane1, True)
    plane2 = rhutil.coerceplane(plane2, True)
    rc, line = Rhino.Geometry.Intersect.Intersection.PlanePlane(plane1, plane2)
    if rc: return line.From, line.To


def PlaneSphereIntersection(plane, sphere_plane, sphere_radius):
    """Calculates the intersection of a plane and a sphere
    Parameters:
      plane = the plane to intersect
      sphere_plane = equitorial plane of the sphere. origin of the plane is
        the center of the sphere
      sphere_radius = radius of the sphere
    Returns:
      list of intersection results - see help
      None on error
    """
    plane = rhutil.coerceplane(plane, True)
    sphere_plane = rhutil.coerceplane(sphere_plane, True)
    sphere = Rhino.Geometry.Sphere(sphere_plane, sphere_radius)
    rc, circle = Rhino.Geometry.Intersect.Intersection.PlaneSphere(plane, sphere)
    if rc==Rhino.Geometry.Intersect.PlaneSphereIntersection.Point:
        return 0, circle.Center
    if rc==Rhino.Geometry.Intersect.PlaneSphereIntersection.Circle:
        return 1, circle.Plane, circle.Radius


def PlaneTransform(plane, xform):
    """Transforms a plane
    Parameters:
      plane = Plane to transform
      xform = Transformation to apply
    """
    plane = rhutil.coerceplane(plane, True)
    xform = rhutil.coercexform(xform, True)
    rc = Rhino.Geometry.Plane(plane)
    if rc.Transform(xform): return rc


def RotatePlane(plane, angle_degrees, axis):
    """Rotates a plane
    Parameters:
      plane = Plane to rotate
      angle_degrees = rotation angle in degrees
      axis = Vector3d or list of three numbers
    Returns:
      rotated plane on success
    """
    plane = rhutil.coerceplane(plane, True)
    axis = rhutil.coerce3dvector(axis, True)
    angle_radians = math.radians(angle_degrees)
    rc = Rhino.Geometry.Plane(plane)
    if rc.Rotate(angle_radians, axis): return rc


def WorldXYPlane():
    "Returns Rhino's world XY plane"
    return Rhino.Geometry.Plane.WorldXY


def WorldYZPlane():
    "Returns Rhino's world YZ plane"
    return Rhino.Geometry.Plane.WorldYZ


def WorldZXPlane():
    "Returns Rhino's world ZX plane"
    return Rhino.Geometry.Plane.WorldZX

########NEW FILE########
__FILENAME__ = pointvector
import utility as rhutil
import Rhino
import scriptcontext
import math

def IsVectorParallelTo(vector1, vector2):
    """Compares two vectors to see if they are parallel
    Parameters:
      vector1, vector2 = the vectors to compare
    Returns:
      -1 = the vectors are anti-parallel
      0 = the vectors are not parallel
      1 = the vectors are parallel
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return vector1.IsParallelTo(vector2)


def IsVectorPerpendicularTo(vector1, vector2):
    """Compares two vectors to see if they are perpendicular
    Parameters:
      vector1, vector2 = the vectors to compare
    Returns:
      True if vectors are perpendicular, otherwise False
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return vector1.IsPerpendicularTo(vector2)


def IsVectorTiny(vector):
    """Verifies that a vector is very short. The X,Y,Z elements are <= 1.0e-12
    Parameters:
      vector - the vector to check
    Returns:
      True if the vector is tiny, otherwise False
    """
    vector = rhutil.coerce3dvector(vector, True)
    return vector.IsTiny( 1.0e-12 )


def IsVectorZero(vector):
    """Verifies that a vector is zero, or tiny. The X,Y,Z elements are equal to 0.0
    Parameters:
      vector - the vector to check
    Returns:
      True if the vector is zero, otherwise False
    """
    vector = rhutil.coerce3dvector(vector, True)
    return vector.IsZero


def PointAdd(point1, point2):
    """Adds a 3D point or a 3D vector to a 3D point
    Parameters:
      point1, point2 = the points to add
    Returns:
      the resulting 3D point if successful
    """
    point1 = rhutil.coerce3dpoint(point1, True)
    point2 = rhutil.coerce3dpoint(point2, True)
    return point1+point2


def PointArrayClosestPoint(points, test_point):
    """Finds the point in a list of 3D points that is closest to a test point
    Parameters:
      points = list of points
      test_point = the point to compare against
    Returns:
      index of the element in the point list that is closest to the test point
    """
    points = rhutil.coerce3dpointlist(points, True)
    test_point = rhutil.coerce3dpoint(test_point, True)
    index = Rhino.Collections.Point3dList.ClosestIndexInList(points, test_point)
    if index>=0: return index


def PointArrayTransform(points, xform):
    """Transforms a list of 3D points
    Parameters:
      points = list of 3D points
      xform = transformation to apply
    Returns:
      list of transformed points on success
    """
    points = rhutil.coerce3dpointlist(points, True)
    xform = rhutil.coercexform(xform, True)
    return [xform*point for point in points]


def PointClosestObject(point, object_ids):
    """Finds the object that is closest to a test point
    Parameters:
      point = point to test
      object_id = identifiers of one or more objects
    Returns:
      (closest object_id, point on object) on success
      None on failure
    """
    object_ids = rhutil.coerceguidlist(object_ids)
    point = rhutil.coerce3dpoint(point, True)
    closest = None
    for id in object_ids:
        geom = rhutil.coercegeometry(id, True)
        point_geometry = geom
        if isinstance(point_geometry, Rhino.Geometry.Point):
            distance = point.DistanceTo( point_geometry.Location )
            if closest is None or distance<closest[0]:
                closest = distance, id, point_geometry.Location
            continue
        point_cloud = geom
        if isinstance(point_cloud, Rhino.Geometry.PointCloud):
            index = point_cloud.ClosestPoint(point)
            if index>=0:
                distance = point.DistanceTo( point_cloud[index].Location )
                if closest is None or distance<closest[0]:
                    closest = distance, id, point_cloud[index].Location
            continue
        curve = geom
        if isinstance(curve, Rhino.Geometry.Curve):
            rc, t = curve.ClosestPoint(point)
            if rc:
                distance = point.DistanceTo( curve.PointAt(t) )
                if closest is None or distance<closest[0]:
                    closest = distance, id, curve.PointAt(t)
            continue
        brep = geom
        if isinstance(brep, Rhino.Geometry.Brep):
            brep_closest = brep.ClosestPoint(point)
            distance = point.DistanceTo( brep_closest )
            if closest is None or distance<closest[0]:
                closest = distance, id, brep_closest
            continue
        mesh = geom
        if isinstance(mesh, Rhino.Geometry.Mesh):
            mesh_closest = mesh.ClosestPoint(point)
            distance = point.DistanceTo( mesh_closest )
            if closest is None or distance<closest[0]:
                closest = distance, id, mesh_closest
            continue
    if closest: return closest[1], closest[2]


def PointCompare(point1, point2, tolerance=None):
    """Compares two 3D points
    Parameters:
      point1, point2 = the points to compare
      tolerance [opt] = tolerance to use for comparison. If omitted,
        Rhino's internal zero tolerance is used
    Returns:
      True or False
    """
    point1 = rhutil.coerce3dpoint(point1, True)
    point2 = rhutil.coerce3dpoint(point2, True)
    if tolerance is None: tolerance = Rhino.RhinoMath.ZeroTolerance
    vector = point2-point1
    return vector.IsTiny(tolerance)


def PointDivide(point, divide):
    """Divides a 3D point by a value
    Parameters:
      point = the point to divide
      divide = a non-zero value to divide
    Returns:
      resulting point
    """
    point = rhutil.coerce3dpoint(point, True)
    return point/divide


def PointsAreCoplanar(points, tolerance=1.0e-12):
    """Verifies that a list of 3D points are coplanar
    Parameters:
      points = list of 3D points
      tolerance[opt] = tolerance to use when verifying
    Returns:
      True or False
    """
    points = rhutil.coerce3dpointlist(points, True)
    return Rhino.Geometry.Point3d.ArePointsCoplanar(points, tolerance)


def PointScale(point, scale):
    """Scales a 3D point by a value
    Parameters:
      point = the point to divide
      scale = scale factor to apply
    Returns:
      resulting point on success
    """
    point = rhutil.coerce3dpoint(point, True)
    return point*scale


def PointSubtract(point1, point2):
    """Subtracts a 3D point or a 3D vector from a 3D point
    Parameters:
      point1, point2 = the points to subtract
    Returns:
      the resulting 3D point if successful
    """
    point1 = rhutil.coerce3dpoint(point1, True)
    point2 = rhutil.coerce3dpoint(point2, True)
    v = point1-point2
    return Rhino.Geometry.Point3d(v)

  
def PointTransform(point, xform):
    """Transforms a 3D point
    Paramters:
      point = the point to transform
      xform = a valid 4x4 transformation matrix
    Returns:
      transformed vector on success
    """
    point = rhutil.coerce3dpoint(point, True)
    xform = rhutil.coercexform(xform, True)
    return xform*point


def ProjectPointToMesh(points, mesh_ids, direction):
    """Projects one or more points onto one or more meshes
    Parameters:
      points = one or more 3D points
      mesh_ids = identifiers of one or more meshes
      direction = direction vector to project the points
    Returns:
     list of projected points on success
    """
    pts = rhutil.coerce3dpointlist(points, False)
    if pts is None:
        pts = [rhutil.coerce3dpoint(points, True)]
    direction = rhutil.coerce3dvector(direction, True)
    id = rhutil.coerceguid(mesh_ids, False)
    if id: mesh_ids = [id]
    meshes = [rhutil.coercemesh(id, True) for id in mesh_ids]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    rc = Rhino.Geometry.Intersect.Intersection.ProjectPointsToMeshes(meshes, pts, direction, tolerance)
    return rc


def ProjectPointToSurface(points, surface_ids, direction):
    """Projects one or more points onto one or more surfaces or polysurfaces
    Parameters:
      points = one or more 3D points
      surface_ids = identifiers of one or more surfaces/polysurfaces
      direction = direction vector to project the points
    Returns:
     list of projected points on success
    """
    pts = rhutil.coerce3dpointlist(points)
    if pts is None:
        pts = [rhutil.coerce3dpoint(points, True)]
    direction = rhutil.coerce3dvector(direction, True)
    id = rhutil.coerceguid(surface_ids, False)
    if id: surface_ids = [id]
    breps = [rhutil.coercebrep(id, True) for id in surface_ids]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    return Rhino.Geometry.Intersect.Intersection.ProjectPointsToBreps(breps, pts, direction, tolerance)


def PullPoints(object_id, points):
    """Pulls an array of points to a surface or mesh object. For more
    information, see the Rhino help file Pull command
    Parameters:
      object_id = the identifier of the surface or mesh object that pulls
      points = list of 3D points
    Returns:
      list of 3D points
    """
    id = rhutil.coerceguid(object_id, True)
    points = rhutil.coerce3dpointlist(points, True)
    mesh = rhutil.coercemesh(id, False)
    if mesh:
        points = mesh.PullPointsToMesh(points)
        return list(points)
    brep = rhutil.coercebrep(id, False)
    if brep and brep.Faces.Count==1:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
        points = brep.Faces[0].PullPointsToFace(points, tolerance)
        return list(points)
    return []


def VectorAdd(vector1, vector2):
    """Adds two 3D vectors
    Parameters:
      vector1, vector2 = the vectors to add
    Returns:
      the resulting 3D vector if successful
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return vector1+vector2


def VectorAngle(vector1, vector2):
    "Returns the angle, in degrees, between two 3-D vectors"
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    vector1 = Rhino.Geometry.Vector3d(vector1.X, vector1.Y, vector1.Z)
    vector2 = Rhino.Geometry.Vector3d(vector2.X, vector2.Y, vector2.Z)
    if not vector1.Unitize() or not vector2.Unitize():
        raise ValueError("unable to unitize vector")
    dot = vector1 * vector2
    dot = rhutil.clamp(-1,1,dot)
    radians = math.acos(dot)
    return math.degrees(radians)


def VectorCompare(vector1, vector2):
    """Compares two 3D vectors
    Parameters:
      vector1, vector2 = the vectors to compare
    Returns:
      -1 if vector1 is less than vector2
      0 if vector1 is equal to vector2
      1 if vector1 is greater than vector2
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return vector1.CompareTo(vector2)


def VectorCreate(to_point, from_point):
    """Creates a vector from two 3D points
    Parameters:
      to_point, from_point = the points defining the vector
    Returns:
      the resulting vector if successful
    """
    to_point = rhutil.coerce3dpoint(to_point, True)
    from_point = rhutil.coerce3dpoint(from_point, True)
    return to_point-from_point


def VectorCrossProduct(vector1, vector2):
    """Calculates the cross product of two 3D vectors
    Parameters:
      vector1, vector2 = the vectors to perform cross product on
    Returns:
      the resulting vector if successful
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return Rhino.Geometry.Vector3d.CrossProduct( vector1, vector2 )


def VectorDivide(vector, divide):
    """Divides a 3D vector by a value
    Parameters:
      vector = the vector to divide
      divide = a non-zero value to divide
    Returns:
      resulting vector on success
    """
    vector = rhutil.coerce3dvector(vector, True)
    return vector/divide


def VectorDotProduct(vector1, vector2):
    """Calculates the dot product of two 3D vectors
    Parameters:
      vector1, vector2 = the vectors to perform the dot product on
    Returns:
      the resulting dot product if successful
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return vector1*vector2


def VectorLength(vector):
    "Returns the length of a 3D vector"
    vector = rhutil.coerce3dvector(vector, True)
    return vector.Length


def VectorMultiply(vector1, vector2):
    """Multiplies two 3D vectors
    Parameters:
      vector1, vector2 = the vectors to multiply
    Returns:
      the resulting inner (dot) product if successful
    """
    return VectorDotProduct(vector1, vector2)


def VectorReverse(vector):
    """Reverses the direction of a 3D vector
    Parameters:
      vector = the vector to reverse
    Returns:
      reversed vector on success
    """
    vector = rhutil.coerce3dvector(vector, True)
    rc = Rhino.Geometry.Vector3d(vector.X, vector.Y, vector.Z)
    rc.Reverse()
    return rc


def VectorRotate(vector, angle_degrees, axis):
    """Rotates a 3D vector
    Parameters:
      vector = the vector to rotate
      angle_degrees = rotation angle
      axis = axis of rotation
    Returns:
      rotated vector on success
    """
    vector = rhutil.coerce3dvector(vector, True)
    axis = rhutil.coerce3dvector(axis, True)
    angle_radians = Rhino.RhinoMath.ToRadians(angle_degrees)
    rc = Rhino.Geometry.Vector3d(vector.X, vector.Y, vector.Z)
    if rc.Rotate(angle_radians, axis): return rc


def VectorScale(vector, scale):
    """Scales a 3-D vector
    Parameters:
      vector = the vector to scale
      scale = scale factor to apply
    Returns:
      resulting vector on success
    """
    vector = rhutil.coerce3dvector(vector, True)
    return vector*scale


def VectorSubtract(vector1, vector2):
    """Subtracts two 3D vectors
    Parameters:
      vector1 = the vector to subtract from
      vector2 = the vector to subtract
    Returns:
      the resulting 3D vector
    """
    vector1 = rhutil.coerce3dvector(vector1, True)
    vector2 = rhutil.coerce3dvector(vector2, True)
    return vector1-vector2


def VectorTransform(vector, xform):
    """Transforms a 3D vector
    Paramters:
      vector = the vector to transform
      xform = a valid 4x4 transformation matrix
    Returns:
      transformed vector on success
    """
    vector = rhutil.coerce3dvector(vector, True)
    xform = rhutil.coercexform(xform, True)
    return xform*vector


def VectorUnitize(vector):
    """Unitizes, or normalizes a 3D vector. Note, zero vectors cannot be unitized
    Parameters:
      vector = the vector to unitize
    Returns:
      unitized vector on success
      None on error
    """
    vector = rhutil.coerce3dvector(vector, True)
    rc = Rhino.Geometry.Vector3d(vector.X, vector.Y, vector.Z)
    if rc.Unitize(): return rc

########NEW FILE########
__FILENAME__ = selection
import scriptcontext
import Rhino
import utility as rhutil
import application as rhapp
from layer import __getlayer
from view import __viewhelper


class filter:
    allobjects = 0
    point = 1
    pointcloud = 2
    curve = 4
    surface = 8
    polysurface = 16
    mesh = 32
    light = 256
    annotation = 512
    instance = 4096
    textdot = 8192
    grip = 16384
    detail = 32768
    hatch = 65536
    morph = 13072
    cage = 134217728
    phantom = 268435456
    clippingplane = 536870912
    extrusion = 1073741824


def AllObjects(select=False, include_lights=False, include_grips=False, include_references=False):
    """Returns identifiers of all objects in the document.
    Parameters:
      select[opt] = Select the objects
      include_lights[opt] = Include light objects
      include_grips[opt] = Include grips objects
    Returns:
      List of Guids identifying the objects
    """
    it = Rhino.DocObjects.ObjectEnumeratorSettings()
    it.IncludeLights = include_lights
    it.IncludeGrips = include_grips
    it.NormalObjects = True
    it.LockedObjects = True
    it.HiddenObjects = True
    it.ReferenceObjects = include_references
    e = scriptcontext.doc.Objects.GetObjectList(it)
    object_ids = []
    for object in e:
        if select: object.Select(True)
        object_ids.append(object.Id)
    if object_ids and select: scriptcontext.doc.Views.Redraw()
    return object_ids


def FirstObject(select=False, include_lights=False, include_grips=False):
    """Returns identifier of the first object in the document. The first
    object is the last object created by the user.
    """
    it = Rhino.DocObjects.ObjectEnumeratorSettings()
    it.IncludeLights = include_lights
    it.IncludeGrips = include_grips
    e = scriptcontext.doc.Objects.GetObjectList(it).GetEnumerator()
    if not e.MoveNext(): return None
    object = e.Current
    if object:
        if select: object.Select(True)
        return object.Id


def __FilterHelper(filter):
    geometry_filter = Rhino.DocObjects.ObjectType.None
    if filter & 1:
        geometry_filter |= Rhino.DocObjects.ObjectType.Point
    if filter & 16384:
        geometry_filter |= Rhino.DocObjects.ObjectType.Grip
    if filter & 2:
        geometry_filter |= Rhino.DocObjects.ObjectType.PointSet
    if filter & 4:
        geometry_filter |= Rhino.DocObjects.ObjectType.Curve
    if filter & 8:
        geometry_filter |= Rhino.DocObjects.ObjectType.Surface
    if filter & 16:
        geometry_filter |= Rhino.DocObjects.ObjectType.Brep
    if filter & 32:
        geometry_filter |= Rhino.DocObjects.ObjectType.Mesh
    if filter & 512:
        geometry_filter |= Rhino.DocObjects.ObjectType.Annotation
    if filter & 256:
        geometry_filter |= Rhino.DocObjects.ObjectType.Light
    if filter & 4096:
        geometry_filter |= Rhino.DocObjects.ObjectType.InstanceReference
    if filter & 134217728:
        geometry_filter |= Rhino.DocObjects.ObjectType.Cage
    if filter & 65536:
        geometry_filter |= Rhino.DocObjects.ObjectType.Hatch
    if filter & 131072:
        geometry_filter |= Rhino.DocObjects.ObjectType.MorphControl
    if filter & 2097152:
        geometry_filter |= Rhino.DocObjects.ObjectType.PolysrfFilter
    if filter & 268435456:
        geometry_filter |= Rhino.DocObjects.ObjectType.Phantom
    if filter & 8192:
        geometry_filter |= Rhino.DocObjects.ObjectType.TextDot
    if filter & 32768:
        geometry_filter |= Rhino.DocObjects.ObjectType.Detail
    if filter & 536870912:
        geometry_filter |= Rhino.DocObjects.ObjectType.ClipPlane
    if filter & 1073741824:
        geometry_filter |= Rhino.DocObjects.ObjectType.Extrusion
    return geometry_filter


def GetCurveObject(message=None, preselect=False, select=False):
    """Prompts user to pick or select a single curve object
    Parameters:
      message[opt] = a prompt or message.
      preselect[opt] = Allow for the selection of pre-selected objects.
      select[opt] = Select the picked objects. If False, objects that
        are picked are not selected.
    Returns:
      Tuple containing the following information
        element 0 = identifier of the curve object
        element 1 = True if the curve was preselected, otherwise False
        element 2 = selection method (see help)
        element 3 = selection point
        element 4 = the curve parameter of the selection point
        element 5 = name of the view selection was made
      None if no object picked
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    go = Rhino.Input.Custom.GetObject()
    if message: go.SetCommandPrompt(message)
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go.SubObjectSelect = False
    go.GroupSelect = False
    go.AcceptNothing(True)
    if go.Get()!=Rhino.Input.GetResult.Object: return None
 
    objref = go.Object(0)
    id = objref.ObjectId
    presel = go.ObjectsWerePreselected
    selmethod = 0
    sm = objref.SelectionMethod()
    if Rhino.DocObjects.SelectionMethod.MousePick==sm: selmethod = 1
    elif Rhino.DocObjects.SelectionMethod.WindowBox==sm: selmethod = 2
    elif Rhino.DocObjects.SelectionMethod.CrossingBox==sm: selmethod = 3
    point = objref.SelectionPoint()
    crv, curve_parameter = objref.CurveParameter()
    viewname = go.View().ActiveViewport.Name
    obj = go.Object(0).Object()
    go.Dispose()
    if not select:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    obj.Select(select)
    return id, presel, selmethod, point, curve_parameter, viewname


def GetObject(message=None, filter=0, preselect=False, select=False, custom_filter=None, subobjects=False):
    """Prompts user to pick, or select, a single object.
    Parameters:
      message[opt] = a prompt or message.
      filter[opt] = The type(s) of geometry (points, curves, surfaces, meshes,...)
          that can be selected. Object types can be added together to filter
          several different kinds of geometry. use the filter class to get values
      preselect[opt] =  Allow for the selection of pre-selected objects.
      select[opt] = Select the picked objects.  If False, the objects that are
          picked are not selected.
      subobjects[opt] = If True, subobjects can be selected. When this is the
          case, an ObjRef is returned instead of a Guid to allow for tracking
          of the subobject when passed into other functions
    Returns:
      Identifier of the picked object
      None if user did not pick an object
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    
    class CustomGetObject(Rhino.Input.Custom.GetObject):
        def __init__(self, filter_function):
            self.m_filter_function = filter_function
        def CustomGeometryFilter( self, rhino_object, geometry, component_index ):
            rc = True
            if self.m_filter_function is not None:
                try:
                    rc = self.m_filter_function(rhino_object, geometry, component_index)
                except:
                    rc = True
            return rc
    go = CustomGetObject(custom_filter)
    if message: go.SetCommandPrompt(message)
    geometry_filter = __FilterHelper(filter)
    if filter>0: go.GeometryFilter = geometry_filter
    go.SubObjectSelect = subobjects
    go.GroupSelect = False
    go.AcceptNothing(True)      
    if go.Get()!=Rhino.Input.GetResult.Object: return None
    objref = go.Object(0)
    obj = objref.Object()
    go.Dispose()
    if not select:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    if subobjects: return objref
    obj.Select(select)
    return obj.Id


class __CustomGetObjectEx(Rhino.Input.Custom.GetObject):
    def __init__(self, allowable_geometry):
        self.m_allowable = allowable_geometry
    def CustomGeometryFilter(self, rhino_object, geometry, component_index):
        for id in self.m_allowable:
            if id==rhino_object.Id: return True
        return False

def GetObjectEx(message=None, filter=0, preselect=False, select=False, objects=None):
    """Prompts user to pick, or select a single object
    Parameters:
      message[opt] = a prompt or message.
      filter[opt] = The type(s) of geometry (points, curves, surfaces, meshes,...)
          that can be selected. Object types can be added together to filter
          several different kinds of geometry. use the filter class to get values
      preselect[opt] =  Allow for the selection of pre-selected objects.
      select[opt] = Select the picked objects.  If False, the objects that are
          picked are not selected.
      objects[opt] = list of object identifiers specifying objects that are
          allowed to be selected
    Returns:
      Tuple of information containing the following information
        element 0 = identifier of the object
        element 1 = True if the object was preselected, otherwise False
        element 2 = selection method (see help)
        element 3 = selection point
        element 4 = name of the view selection was made
      None if no object selected
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    go = None
    if objects:
        ids = [rhutil.coerceguid(id, True) for id in objects]
        if ids: go = __CustomGetObjectEx(ids)
    if not go: go = Rhino.Input.Custom.GetObject()
    if message: go.SetCommandPrompt(message)
    geometry_filter = __FilterHelper(filter)
    if filter>0: go.GeometryFilter = geometry_filter
    go.SubObjectSelect = False
    go.GroupSelect = False
    go.AcceptNothing(True)      
    if go.Get()!=Rhino.Input.GetResult.Object: return None
    objref = go.Object(0)
    id = objref.ObjectId
    presel = go.ObjectsWerePreselected
    selmethod = 0
    sm = objref.SelectionMethod()
    if Rhino.DocObjects.SelectionMethod.MousePick==sm: selmethod = 1
    elif Rhino.DocObjects.SelectionMethod.WindowBox==sm: selmethod = 2
    elif Rhino.DocObjects.SelectionMethod.CrossingBox==sm: selmethod = 3
    point = objref.SelectionPoint()
    viewname = go.View().ActiveViewport.Name
    obj = go.Object(0).Object()
    go.Dispose()
    if not select:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    obj.Select(select)
    return id, presel, selmethod, point, viewname


def GetObjects(message=None, filter=0, group=True, preselect=False, select=False, objects=None, minimum_count=1, maximum_count=0, custom_filter=None):
    """Prompts user to pick or select one or more objects.
    Parameters:
      message[opt] = a prompt or message.
      filter[opt] = The type(s) of geometry (points, curves, surfaces, meshes,...)
          that can be selected. Object types can be added together to filter
          several different kinds of geometry. use the filter class to get values
      group[opt] = Honor object grouping.  If omitted and the user picks a group,
          the entire group will be picked (True). Note, if filter is set to a
          value other than 0 (All objects), then group selection will be disabled.
      preselect[opt] =  Allow for the selection of pre-selected objects.
      select[opt] = Select the picked objects.  If False, the objects that are
          picked are not selected.
      objects[opt] = list of objects that are allowed to be selected
      mimimum_count, maximum_count[out] = limits on number of objects allowed to be selected
    Returns
      list of Guids identifying the picked objects
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()

    objects = rhutil.coerceguidlist(objects)
    class CustomGetObject(Rhino.Input.Custom.GetObject):
        def __init__(self, filter_function):
            self.m_filter_function = filter_function
        def CustomGeometryFilter( self, rhino_object, geometry, component_index ):
            if objects and not rhino_object.Id in objects: return False
            rc = True
            if self.m_filter_function is not None:
                try:
                    rc = self.m_filter_function(rhino_object, geometry, component_index)
                except:
                    rc = True
            return rc
    go = CustomGetObject(custom_filter)
    if message: go.SetCommandPrompt(message)
    geometry_filter = __FilterHelper(filter)
    if filter>0: go.GeometryFilter = geometry_filter
    go.SubObjectSelect = False
    go.GroupSelect = group
    go.AcceptNothing(True)
    if go.GetMultiple(minimum_count,maximum_count)!=Rhino.Input.GetResult.Object: return None
    if not select:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    rc = []
    count = go.ObjectCount
    for i in xrange(count):
        objref = go.Object(i)
        rc.append(objref.ObjectId)
        obj = objref.Object()
        if select and obj is not None: obj.Select(select)
    go.Dispose()
    return rc


def GetObjectsEx(message=None, filter=0, group=True, preselect=False, select=False, objects=None):
    """Prompts user to pick, or select one or more objects
    Parameters:
      message[opt] = a prompt or message.
      filter[opt] = The type(s) of geometry (points, curves, surfaces, meshes,...)
          that can be selected. Object types can be added together to filter
          several different kinds of geometry. use the filter class to get values
      group[opt] = Honor object grouping.  If omitted and the user picks a group,
          the entire group will be picked (True). Note, if filter is set to a
          value other than 0 (All objects), then group selection will be disabled.
      preselect[opt] =  Allow for the selection of pre-selected objects.
      select[opt] = Select the picked objects. If False, the objects that are
          picked are not selected.
      objects[opt] = list of object identifiers specifying objects that are
          allowed to be selected
    Returns:
      A list of tuples containing the following information
        element 0 = identifier of the object
        element 1 = True if the object was preselected, otherwise False
        element 2 = selection method (see help)
        element 3 = selection point
        element 4 = name of the view selection was made
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    go = None
    if objects:
        ids = [rhutil.coerceguid(id) for id in objects]
        if ids: go = __CustomGetObjectEx(ids)
    if not go: go = Rhino.Input.Custom.GetObject()
    if message: go.SetCommandPrompt(message)
    geometry_filter = __FilterHelper(filter)
    if filter>0: go.GeometryFilter = geometry_filter
    go.SubObjectSelect = False
    go.GroupSelect = False
    go.AcceptNothing(True)      
    if go.GetMultiple(1,0)!=Rhino.Input.GetResult.Object: return []
    if not select:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    rc = []
    count = go.ObjectCount
    for i in xrange(count):
        objref = go.Object(i)
        id = objref.ObjectId
        presel = go.ObjectsWerePreselected
        selmethod = 0
        sm = objref.SelectionMethod()
        if Rhino.DocObjects.SelectionMethod.MousePick==sm: selmethod = 1
        elif Rhino.DocObjects.SelectionMethod.WindowBox==sm: selmethod = 2
        elif Rhino.DocObjects.SelectionMethod.CrossingBox==sm: selmethod = 3
        point = objref.SelectionPoint()
        viewname = go.View().ActiveViewport.Name
        rc.append( (id, presel, selmethod, point, viewname) )
        obj = objref.Object()
        if select and obj is not None: obj.Select(select)
    go.Dispose()
    return rc


def GetPointCoordinates(message="select points", preselect=False):
    """Prompts the user to select one or more point objects.
    Returns:
      list of 3d coordinates on success
    """
    ids = GetObjects(message, filter.point, preselect=preselect)
    rc = []
    for id in ids:
        rhobj = scriptcontext.doc.Objects.Find(id)
        rc.append(rhobj.Geometry.Location)
    return rc


def GetSurfaceObject(message="select surface", preselect=False, select=False):
    """Prompts the user to select a single surface
    Parameters:
      message[opt] = prompt displayed
      preselect[opt] = allow for preselected objects
      select[opt] = select the picked object
    Returns:
      tuple of information on success
        element 0 = identifier of the surface
        element 1 = True if the surface was preselected, otherwise False
        element 2 = selection method ( see help )
        element 3 = selection point
        element 4 = u,v surface parameter of the selection point
        element 5 = name of the view in which the selection was made
      None on error
    """
    if not preselect:
        scriptcontext.doc.Objects.UnselectAll()
        scriptcontext.doc.Views.Redraw()
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(message)
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Surface
    go.SubObjectSelect = False
    go.GroupSelect = False
    go.AcceptNothing(True)
    if go.Get()!=Rhino.Input.GetResult.Object:
        return scriptcontext.errorhandler()
    objref = go.Object(0)
    rhobj = objref.Object()
    rhobj.Select(select)
    scriptcontext.doc.Views.Redraw()

    id = rhobj.Id
    prepicked = go.ObjectsWerePreselected
    selmethod = objref.SelectionMethod()
    point = objref.SelectionPoint()
    surf, u, v = objref.SurfaceParameter()
    uv = (u,v)
    if not point.IsValid:
        point = None
        uv = None
    view = go.View()
    name = view.ActiveViewport.Name
    go.Dispose()
    return id, prepicked, selmethod, point, uv, name


def HiddenObjects(include_lights=False, include_grips=False, include_references=False):
    """Returns identifiers of all hidden objects in the document. Hidden objects
    are not visible, cannot be snapped to, and cannot be selected
    Parameters:
      include_lights[opt] = include light objects
      include_grips[opt] = include grip objects
    """
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NormalObjects = False
    settings.LockedObjects = False
    settings.HiddenObjects = True
    settings.IncludeLights = include_lights
    settings.IncludeGrips = include_grips
    settings.ReferenceObjects = include_references
    items = scriptcontext.doc.Objects.GetObjectList(settings)
    return [item.Id for item in items]


def InvertSelectedObjects(include_lights=False, include_grips=False, include_references=False):
    """Inverts the current object selection. The identifiers of the newly
    selected objects are returned
    """
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.IncludeLights = include_lights
    settings.IncludeGrips = include_grips
    settings.IncludePhantoms = True
    settings.ReferenceObjects = include_references
    rhobjs = scriptcontext.doc.Objects.GetObjectList(settings)
    rc = []
    for obj in rhobjs:
        if not obj.IsSelected(False) and obj.IsSelectable():
            rc.append(obj.Id)
            obj.Select(True)
        else:
            obj.Select(False)
    scriptcontext.doc.Views.Redraw()
    return rc


def LastCreatedObjects(select=False):
    """Returns identifiers of the objects that were most recently created or changed
    by scripting a Rhino command using the Command function. It is important to
    call this function immediately after calling the Command function as only the
    most recently created or changed object identifiers will be returned
    """
    serial_numbers = rhapp.__command_serial_numbers
    if serial_numbers is None: return scriptcontext.errorhandler()
    serial_number = serial_numbers[0]
    end = serial_numbers[1]
    rc = []
    while serial_number<end:
        obj = scriptcontext.doc.Objects.Find(serial_number)
        if obj and not obj.IsDeleted:
            rc.append(obj.Id)
            if select: obj.Select(True)
        serial_number += 1
    if select==True and rc: scriptcontext.doc.Views.Redraw()
    return rc


def LastObject(select=False, include_lights=False, include_grips=False):
    """Returns the identifier of the last object in the document. The last object
    in the document is the first object created by the user
    Parameters:
      select[opt] = select the object
      include_lights[opt] = include lights in the potential set
      include_grips[opt] = include grips in the potential set
    Returns:
      identifier of the object on success
    """
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.IncludeLights = include_lights
    settings.IncludeGrips = include_grips
    settings.DeletedObjects = False
    rhobjs = scriptcontext.doc.Objects.GetObjectList(settings)
    firstobj = None
    for obj in rhobjs: firstobj = obj
    if firstobj is None: return scriptcontext.errorhandler()
    rc = firstobj.Id
    if select:
        firstobj.Select(True)
        scriptcontext.doc.Views.Redraw()
    return rc


def NextObject(object_id, select=False, include_lights=False, include_grips=False):
    """Returns the identifier of the next object in the document
    Parameters:
      object_id = the identifier of the object from which to get the next object
      select[opt] = select the object
      include_lights[opt] = include lights in the potential set
      include_grips[opt] = include grips in the potential set
    Returns:
      identifier of the object on success
    """
    current_obj = rhutil.coercerhinoobject(object_id, True)
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.IncludeLights = include_lights
    settings.IncludeGrips = include_grips
    settings.DeletedObjects = False
    rhobjs = scriptcontext.doc.Objects.GetObjectList(settings)
    found = False
    for obj in rhobjs:
        if found and obj: return obj.Id
        if obj.Id == current_obj.Id: found = True


def NormalObjects(include_lights=False, include_grips=False):
    """Returns identifiers of all normal objects in the document. Normal objects
    are visible, can be snapped to, and are independent of selection state"""
    iter = Rhino.DocObjects.ObjectEnumeratorSettings()
    iter.NormalObjects = True
    iter.LockedObjects = False
    iter.IncludeLights = include_lights
    iter.IncludeGrips = include_grips
    return [obj.Id for obj in scriptcontext.doc.Objects.GetObjectList(iter)]


def ObjectsByColor(color, select=False, include_lights=False):
    """Returns identifiers of all objects based on color
    Parameters:
      color = color to get objects by
      select[opt] = select the objects
      include_lights[opt] = include lights in the set
    Returns:
      list of identifiers
    """
    color = rhutil.coercecolor(color, True)
    rhino_objects = scriptcontext.doc.Objects.FindByDrawColor(color, include_lights)
    if select:
        for obj in rhino_objects: obj.Select(True)
        scriptcontext.doc.Views.Redraw()
    return [obj.Id for obj in rhino_objects]


def ObjectsByGroup(group_name, select=False):
    """Returns identifiers of all objects based on the objects' group name
    Parameters:
      group_name = name of the group
      select [opt] = select the objects
    Returns:
      list of identifiers on success
    """
    group_index = scriptcontext.doc.Groups.Find(group_name, True)
    if group_index<0: raise ValueError("%s does not exist in GroupTable"%group_name)
    rhino_objects = scriptcontext.doc.Groups.GroupMembers(group_index)
    if not rhino_objects: return []
    if select:
        for obj in rhino_objects: obj.Select(True)
        scriptcontext.doc.Views.Redraw()
    return [obj.Id for obj in rhino_objects]


def ObjectsByLayer(layer_name, select=False):
    """Returns identifiers of all objects based on the objects' layer name
    Parameters:
      layer_name = name of the layer
      select [opt] = select the objects
    Returns:
      list of identifiers
    """
    layer = __getlayer(layer_name, True)
    rhino_objects = scriptcontext.doc.Objects.FindByLayer(layer)
    if not rhino_objects: return []
    if select:
        for rhobj in rhino_objects: rhobj.Select(True)
        scriptcontext.doc.Views.Redraw()
    return [rhobj.Id for rhobj in rhino_objects]


def ObjectsByName(name, select=False, include_lights=False, include_references=False):
    """Returns identifiers of all objects based on user-assigned name
    Parameters:
      name = name of the object or objects
      select[opt] = select the objects
      include_lights[opt] = include light objects
    Returns:
      list of identifiers
    """
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.HiddenObjects = True
    settings.DeletedObjects = False
    settings.IncludeGrips = False
    settings.IncludePhantoms = True
    settings.IncludeLights = include_lights
    settings.NameFilter = name
    settings.ReferenceObjects = include_references
    objects = scriptcontext.doc.Objects.GetObjectList(settings)
    ids = [rhobj.Id for rhobj in objects]
    if ids and select:
        objects = scriptcontext.doc.Objects.GetObjectList(settings)
        for rhobj in objects: rhobj.Select(True)
        scriptcontext.doc.Views.Redraw()
    return ids
   

def ObjectsByType(geometry_type, select=False, state=0):
    """Returns identifiers of all objects based on the objects' geometry type.
    Parameters:
      geometry_type = The type(s) of geometry objects (points, curves, surfaces,
             meshes, etc.) that can be selected. Object types can be
             added together to filter several different kinds of geometry.
              Value        Description
               0           All objects
               1           Point
               2           Point cloud
               4           Curve
               8           Surface or single-face brep
               16          Polysurface or multiple-face
               32          Mesh
               256         Light
               512         Annotation
               4096        Instance or block reference
               8192        Text dot object
               16384       Grip object
               32768       Detail
               65536       Hatch
               131072      Morph control
               134217728   Cage
               268435456   Phantom
               536870912   Clipping plane
      select[opt] = Select the objects
      state[opt] = Object state. See help
    Returns:
      A list of Guids identifying the objects.
    """
    bSurface = False
    bPolySurface = False
    bLights = False
    bGrips = False
    bPhantoms = False
    geometry_filter = __FilterHelper(geometry_type)
    if type(geometry_type) is int and geometry_type==0:
        geometry_filter = Rhino.DocObjects.ObjectType.AnyObject
    if geometry_filter & Rhino.DocObjects.ObjectType.Surface: bSurface = True
    if geometry_filter & Rhino.DocObjects.ObjectType.Brep: bPolySurface = True
    if geometry_filter & Rhino.DocObjects.ObjectType.Light: bLights = True
    if geometry_filter & Rhino.DocObjects.ObjectType.Grip: bGrips = True
    if geometry_filter & Rhino.DocObjects.ObjectType.Phantom: bPhantoms = True

    it = Rhino.DocObjects.ObjectEnumeratorSettings()
    it.DeletedObjects = False
    it.ActiveObjects = True
    it.ReferenceObjects = True
    it.IncludeLights = bLights
    it.IncludeGrips = bGrips
    it.IncludePhantoms = bPhantoms
    if state:
        it.NormalObjects = False
        it.LockedObjects = False
    if state & 1: it.NormalObjects = True
    if state & 2: it.LockedObjects = True
    if state & 4: it.HiddenObjects = True

    object_ids = []
    e = scriptcontext.doc.Objects.GetObjectList(it)
    for object in e:
        bFound = False
        object_type = object.ObjectType
        if object_type==Rhino.DocObjects.ObjectType.Brep and (bSurface or bPolySurface):
            brep = rhutil.coercebrep(object.Id)
            if brep:
                if brep.Faces.Count==1:
                    if bSurface: bFound = True
                else:
                    if bPolySurface: bFound = True
        elif object_type & geometry_filter:
            bFound = True

        if bFound:
            if select: object.Select(True)
            object_ids.append(object.Id)

    if object_ids and select: scriptcontext.doc.Views.Redraw()
    return object_ids
  

def SelectedObjects(include_lights=False, include_grips=False):
    """Returns the identifiers of all objects that are currently selected
    Parameters:
      include_lights [opt] = include light objects
      include_grips [opt] = include grip objects
    Returns:
      list of Guids identifying the objects
    """
    selobjects = scriptcontext.doc.Objects.GetSelectedObjects(include_lights, include_grips)
    return [obj.Id for obj in selobjects]


def UnselectAllObjects():
    """Unselects all objects in the document
    Returns:
      the number of objects that were unselected
    """
    rc = scriptcontext.doc.Objects.UnselectAll()
    if rc>0: scriptcontext.doc.Views.Redraw()
    return rc


def VisibleObjects(view=None, select=False, include_lights=False, include_grips=False):
    """Returns the identifiers of all objects that are visible in a specified view
    Parameters:
      view [opt] = the view to use. If omitted, the current active view is used
      select [opt] = Select the objects
      include_lights [opt] = include light objects
      include_grips [opt] = include grip objects
    Returns:
      list of Guids identifying the objects
    """
    it = Rhino.DocObjects.ObjectEnumeratorSettings()
    it.DeletedObjects = False
    it.ActiveObjects = True
    it.ReferenceObjects = True
    it.IncludeLights = include_lights
    it.IncludeGrips = include_grips
    it.VisibleFilter = True
    it.ViewportFilter = __viewhelper(view).MainViewport

    object_ids = []
    e = scriptcontext.doc.Objects.GetObjectList(it)
    for object in e:
        if select: object.Select(True)
        object_ids.append(object.Id)

    if object_ids and select: scriptcontext.doc.Views.Redraw()
    return object_ids

########NEW FILE########
__FILENAME__ = surface
import scriptcontext
import math
import Rhino
import System.Guid
import utility as rhutil
import object as rhobject

def AddBox(corners):
    """Adds a box shaped polysurface to the document
    Parameters:
      corners = 8 3D points that define the corners of the box. Points need to
        be in counter-clockwise order starting with the bottom rectangle of the box
    Returns:
      identifier of the new object on success
    """
    box = rhutil.coerce3dpointlist(corners, True)
    brep = Rhino.Geometry.Brep.CreateFromBox(box)
    if not brep: raise ValueError("unable to create brep from box")
    rc = scriptcontext.doc.Objects.AddBrep(brep)
    if rc==System.Guid.Empty: raise Exception("unable to add brep to document")
    scriptcontext.doc.Views.Redraw()
    return rc


def AddCone(base, height, radius, cap=True):
    """Adds a cone shaped polysurface to the document
    Parameters:
      base = 3D origin point of the cone or a plane with an apex at the origin
          and normal along the plane's z-axis
      height = 3D height point of the cone if base is a 3D point. The height
          point defines the height and direction of the cone. If base is a
          plane, height is a numeric value
      radius = the radius at the base of the cone
      cap [opt] = cap base of the cone
    Returns:
      identifier of the new object on success
    """
    plane = None
    height_point = rhutil.coerce3dpoint(height)
    if height_point is None:
        plane = rhutil.coerceplane(base, True)
    else:
        base_point = rhutil.coerce3dpoint(base, True)
        normal = base_point - height_point
        height = normal.Length
        plane = Rhino.Geometry.Plane(height_point, normal)
    cone = Rhino.Geometry.Cone(plane, height, radius)
    brep = Rhino.Geometry.Brep.CreateFromCone(cone, cap)
    rc = scriptcontext.doc.Objects.AddBrep(brep)
    scriptcontext.doc.Views.Redraw()
    return rc


def AddCutPlane(object_ids, start_point, end_point, normal=None):
    """Adds a planar surface through objects at a designated location. For more
    information, see the Rhino help file for the CutPlane command
    Parameters:
      objects_ids = identifiers of objects that the cutting plane will
          pass through
      start_point, end_point = line that defines the cutting plane
      normal[opt] = vector that will be contained in the returned planar
          surface. In the case of Rhino's CutPlane command, this is the
          normal to, or Z axis of, the active view's construction plane.
          If omitted, the world Z axis is used
    Returns:
      identifier of new object on success
      None on error
    """
    objects = []
    bbox = Rhino.Geometry.BoundingBox.Unset
    for id in object_ids:
        rhobj = rhutil.coercerhinoobject(id, True, True)
        geometry = rhobj.Geometry
        bbox.Union( geometry.GetBoundingBox(True) )
    start_point = rhutil.coerce3dpoint(start_point, True)
    end_point = rhutil.coerce3dpoint(end_point, True)
    if not bbox.IsValid: return scriptcontext.errorhandler()
    line = Rhino.Geometry.Line(start_point, end_point)
    if normal: normal = rhutil.coerce3dvector(normal, True)
    else: normal = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane().Normal
    surface = Rhino.Geometry.PlaneSurface.CreateThroughBox(line, normal, bbox)
    if surface is None: return scriptcontext.errorhandler()
    id = scriptcontext.doc.Objects.AddSurface(surface)
    if id==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return id


def AddCylinder(base, height, radius, cap=True):
    """Adds a cylinder-shaped polysurface to the document
    Parameters:
      base = The 3D base point of the cylinder or the base plane of the cylinder
      height = if base is a point, then height is a 3D height point of the
        cylinder. The height point defines the height and direction of the
        cylinder. If base is a plane, then height is the numeric height value
        of the cylinder
      radius = radius of the cylinder
      cap[opt] = cap the cylinder
    Returns:
      identifier of new object if successful
      None on error
    """
    cylinder=None
    height_point = rhutil.coerce3dpoint(height)
    if height_point:
        #base must be a point
        base = rhutil.coerce3dpoint(base, True)
        normal = height_point-base
        plane = Rhino.Geometry.Plane(base, normal)
        height = normal.Length
        circle = Rhino.Geometry.Circle(plane, radius)
        cylinder = Rhino.Geometry.Cylinder(circle, height)
    else:
        #base must be a plane
        if type(base) is Rhino.Geometry.Point3d: base = [base.X, base.Y, base.Z]
        base = rhutil.coerceplane(base, True)
        circle = Rhino.Geometry.Circle(base, radius)
        cylinder = Rhino.Geometry.Cylinder(circle, height)
    brep = cylinder.ToBrep(cap, cap)
    id = scriptcontext.doc.Objects.AddBrep(brep)
    if id==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return id


def AddEdgeSrf(curve_ids):
    """Creates a surface from 2, 3, or 4 edge curves
    Parameters:
      curve_ids = list or tuple of curves
    Returns:
      identifier of new object if successful
      None on error
    """
    curves = [rhutil.coercecurve(id, -1, True) for id in curve_ids]
    brep = Rhino.Geometry.Brep.CreateEdgeSurface(curves)
    if brep is None: return scriptcontext.errorhandler()
    id = scriptcontext.doc.Objects.AddBrep(brep)
    if id==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return id


def AddNetworkSrf(curves, continuity=1, edge_tolerance=0, interior_tolerance=0, angle_tolerance=0):
    """Creates a surface from a network of crossing curves
    Parameters:
      curves = curves from which to create the surface
      continuity[opt] = how the edges match the input geometry
        0=loose, 1=position, 2=tangency, 3=curvature
    Returns:
      identifier of new object if successful
    """
    curves = [rhutil.coercecurve(curve, -1, True) for curve in curves]
    surf, err = Rhino.Geometry.NurbsSurface.CreateNetworkSurface(curves, continuity, edge_tolerance, interior_tolerance, angle_tolerance)
    if surf:
        rc = scriptcontext.doc.Objects.AddSurface(surf)
        scriptcontext.doc.Views.Redraw()
        return rc


def AddNurbsSurface(point_count, points, knots_u, knots_v, degree, weights=None):
    """Adds a NURBS surface object to the document
    Parameters:
      point_count = number of control points in the u and v direction
      points = list of 3D points
      knots_u = knot values for the surface in the u direction.
                Must contain point_count[0]+degree[0]-1 elements
      knots_v = knot values for the surface in the v direction.
                Must contain point_count[1]+degree[1]-1 elements
      degree = degree of the surface in the u and v directions.
      weights[opt] = weight values for the surface. The number of elements in
        weights must equal the number of elements in points. Values must be
        greater than zero.
    Returns:
      identifier of new object if successful
      None on error
    """
    if len(points)<(point_count[0]*point_count[1]):
        return scriptcontext.errorhandler()
    ns = Rhino.Geometry.NurbsSurface.Create(3, weights!=None, degree[0]+1, degree[1]+1, point_count[0], point_count[1])
    #add the points and weights
    controlpoints = ns.Points
    index = 0
    for i in range(point_count[0]):
        for j in range(point_count[1]):
            if weights:
                cp = Rhino.Geometry.ControlPoint(points[index], weights[index])
                controlpoints.SetControlPoint(i,j,cp)
            else:
                cp = Rhino.Geometry.ControlPoint(points[index])
                controlpoints.SetControlPoint(i,j,cp)
            index += 1
    #add the knots
    for i in range(ns.KnotsU.Count): ns.KnotsU[i] = knots_u[i]
    for i in range(ns.KnotsV.Count): ns.KnotsV[i] = knots_v[i]
    if not ns.IsValid: return scriptcontext.errorhandler()
    id = scriptcontext.doc.Objects.AddSurface(ns)
    if id==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return id


def AddPipe(curve_id, parameters, radii, blend_type=0, cap=0, fit=False):
    """Creates a single walled surface with a circular profile around a curve
    Parameters:
      curve_id = identifier of rail curve
      parameters, radii = list of radius values at normalized curve parameters
      blend_type = 0(local) or 1(global)
      cap = 0(none), 1(flat), 2(round)
      fit = attempt to fit a single surface
    Returns:
      List of identifiers of new objects created
    """
    rail = rhutil.coercecurve(curve_id, -1, True)
    abs_tol = scriptcontext.doc.ModelAbsoluteTolerance
    ang_tol = scriptcontext.doc.ModelAngleToleranceRadians
    if type(parameters) is int or type(parameters) is float: parameters = [parameters]
    if type(radii) is int or type(radii) is float: radii = [radii]
    parameters = map(float,parameters)
    radii = map(float,radii)
    cap = System.Enum.ToObject(Rhino.Geometry.PipeCapMode, cap)
    breps = Rhino.Geometry.Brep.CreatePipe(rail, parameters, radii, blend_type==0, cap, fit, abs_tol, ang_tol)
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in breps]
    scriptcontext.doc.Views.Redraw()
    return rc


def AddPlanarSrf(object_ids):
    """Creates one or more surfaces from planar curves
    Parameters:
      object_ids = curves to use for creating planar surfaces
    Returns:
      list of surfaces created on success
      None on error
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    curves = [rhutil.coercecurve(id,-1,True) for id in object_ids]
    breps = Rhino.Geometry.Brep.CreatePlanarBreps(curves)
    if breps:
        rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in breps]
        scriptcontext.doc.Views.Redraw()
        return rc


def AddPlaneSurface(plane, u_dir, v_dir):
    """Create a plane surface and add it to the document.
    Parameters:
      plane = The plane.
      u_dir = The magnitude in the U direction.
      v_dir = The magnitude in the V direction.
    Returns:
      The identifier of the new object if successful.
      None if not successful, or on error.
    """
    plane = rhutil.coerceplane(plane, True)
    u_interval = Rhino.Geometry.Interval(0, u_dir)
    v_interval = Rhino.Geometry.Interval(0, v_dir)
    plane_surface = Rhino.Geometry.PlaneSurface(plane, u_interval, v_interval) 
    if plane_surface is None: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddSurface(plane_surface)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def AddLoftSrf(object_ids, start=None, end=None, loft_type=0, simplify_method=0, value=0, closed=False):
    """Adds a surface created by lofting curves to the document.
    - no curve sorting performed. pass in curves in the order you want them sorted
    - directions of open curves not adjusted. Use CurveDirectionsMatch and
      ReverseCurve to adjust the directions of open curves
    - seams of closed curves are not adjusted. Use CurveSeam to adjust the seam
      of closed curves
    Parameters:
      object_ids = ordered list of the curves to loft through
      start [opt] = starting point of the loft
      end [opt] = ending point of the loft
      loft_type [opt] = type of loft. Possible options are:
        0 = Normal. Uses chord-length parameterization in the loft direction
        1 = Loose. The surface is allowed to move away from the original curves
            to make a smoother surface. The surface control points are created
            at the same locations as the control points of the loft input curves.
        2 = Straight. The sections between the curves are straight. This is
            also known as a ruled surface.
        3 = Tight. The surface sticks closely to the original curves. Uses square
            root of chord-length parameterization in the loft direction
        4 = Developable. Creates a separate developable surface or polysurface
            from each pair of curves.
      simplify_method [opt] = Possible options are:
        0 = None. Does not simplify.
        1 = Rebuild. Rebuilds the shape curves before lofting.
        2 = Refit. Refits the shape curves to a specified tolerance
      value [opt] = A value based on the specified style.
        style=1 (Rebuild), then value is the number of control point used to rebuild
        style=1 is specified and this argument is omitted, then curves will be
        rebuilt using 10 control points.
        style=2 (Refit), then value is the tolerance used to rebuild.
        style=2 is specified and this argument is omitted, then the document's
        absolute tolerance us used for refitting.
    Returns:
      Array containing the identifiers of the new surface objects if successful
      None on error
    """
    if loft_type<0 or loft_type>5: raise ValueError("loft_type must be 0-4")
    if simplify_method<0 or simplify_method>2: raise ValueError("simplify_method must be 0-2")

    # get set of curves from object_ids
    curves = [rhutil.coercecurve(id,-1,True) for id in object_ids]
    if len(curves)<2: return scriptcontext.errorhandler()
    if start is None: start = Rhino.Geometry.Point3d.Unset
    if end is None: end = Rhino.Geometry.Point3d.Unset
    start = rhutil.coerce3dpoint(start, True)
    end = rhutil.coerce3dpoint(end, True)
    
    lt = Rhino.Geometry.LoftType.Normal
    if loft_type==1: lt = Rhino.Geometry.LoftType.Loose
    elif loft_type==2: lt = Rhino.Geometry.LoftType.Straight
    elif loft_type==3: lt = Rhino.Geometry.LoftType.Tight
    elif loft_type==4: lt = Rhino.Geometry.LoftType.Developable

    breps = None
    if simplify_method==0:
        breps = Rhino.Geometry.Brep.CreateFromLoft(curves, start, end, lt, closed)
    elif simplify_method==1:
        value = abs(value)
        rebuild_count = int(value)
        breps = Rhino.Geometry.Brep.CreateFromLoftRebuild(curves, start, end, lt, closed, rebuild_count)
    elif simplify_method==2:
        refit = abs(value)
        if refit==0: refit = scriptcontext.doc.ModelAbsoluteTolerance
        breps = Rhino.Geometry.Brep.CreateFromLoftRefit(curves, start, end, lt, closed, refit)
    if not breps: return scriptcontext.errorhandler()

    idlist = []
    for brep in breps:
        id = scriptcontext.doc.Objects.AddBrep(brep)
        if id!=System.Guid.Empty: idlist.append(id)
    if idlist: scriptcontext.doc.Views.Redraw()
    return idlist


def AddRevSrf(curve_id, axis, start_angle=0.0, end_angle=360.0):
    """Create a surface by revolving a curve around an axis
    Parameters:
      curve_id = identifier of profile curve
      axis = line for the rail revolve axis
      start_angle[opt], end_angle[opt] = start and end angles of revolve
    Returns:
      identifier of new object if successful
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    axis = rhutil.coerceline(axis, True)
    start_angle = math.radians(start_angle)
    end_angle = math.radians(end_angle)
    srf = Rhino.Geometry.RevSurface.Create(curve, axis, start_angle, end_angle)
    if not srf: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddSurface(srf)
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSphere(center_or_plane, radius):
    """Add a spherical surface to the document
    Parameters:
      center_or_plane = center point of the sphere. If a plane is input,
        the origin of the plane will be the center of the sphere
      radius = radius of the sphere in the current model units
    Returns:
      intentifier of the new object on success
      None on error
    """
    center = rhutil.coerce3dpoint(center_or_plane)
    if center is None:
        plane = rhutil.coerceplane(center_or_plane, True)
        center = plane.Origin
    sphere = Rhino.Geometry.Sphere(center, radius)
    rc = scriptcontext.doc.Objects.AddSphere(sphere)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSrfContourCrvs(object_id, points_or_plane, interval=None):
    """Adds a spaced series of planar curves resulting from the intersection of
    defined cutting planes through a surface or polysurface. For more
    information, see Rhino help for details on the Contour command
    Parameters:
      object_id = object identifier
      points_or_plane = either a list/tuple of two points or a plane
        if two points, they define the start and end points of a center line
        if a plane, the plane defines the cutting plane
      interval[opt] = distance beween contour curves.
    Returns:
      ids of new curves on success
      None on error
    """
    brep = rhutil.coercebrep(object_id)
    plane = rhutil.coerceplane(points_or_plane)
    curves = None
    if plane:
        curves = Rhino.Geometry.Brep.CreateContourCurves(brep, plane)
    else:
        start = rhutil.coerce3dpoint(points_or_plane[0], True)
        end = rhutil.coerce3dpoint(points_or_plane[1], True)
        if not interval:
            bbox = brep.GetBoundingBox(True)
            v = bbox.Max - bbox.Min
            interval = v.Length / 50.0
        curves = Rhino.Geometry.Brep.CreateContourCurves(brep, start, end, interval)
    rc = []
    for crv in curves:
        id = scriptcontext.doc.Objects.AddCurve(crv)
        if id!=System.Guid.Empty: rc.append(id)
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSrfControlPtGrid(count, points, degree=(3,3)):
    """Creates a surface from a grid of points
    Parameters:
      count = tuple of two numbers defining number of points in the u,v directions
      points = list of 3D points
      degree[opt] = two numbers defining degree of the surface in the u,v directions
    Returns:
      The identifier of the new object if successful.
      None if not successful, or on error.
    """
    points = rhutil.coerce3dpointlist(points, True)
    surf = Rhino.Geometry.NurbsSurface.CreateFromPoints(points, count[0], count[1], degree[0], degree[1])
    if not surf: return scriptcontext.errorhandler()
    id = scriptcontext.doc.Objects.AddSurface(surf)
    if id!=System.Guid.Empty:
        scriptcontext.doc.Views.Redraw()
        return id


def AddSrfPt(points):
    """Creates a new surface from either 3 or 4 control points.
    Parameters:
      points = list of either 3 or 4 control points
    Returns
      The identifier of the new object if successful.
      None if not successful, or on error.
    """
    points = rhutil.coerce3dpointlist(points, True)
    surface=None
    if len(points)==3:
        surface = Rhino.Geometry.NurbsSurface.CreateFromCorners(points[0], points[1], points[2])
    elif len(points)==4:
        surface = Rhino.Geometry.NurbsSurface.CreateFromCorners(points[0], points[1], points[2], points[3])
    if surface is None: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddSurface(surface)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSrfPtGrid(count, points, degree=(3,3), closed=(False,False)):
    """Creates a surface from a grid of points
    Parameters:
      count = tuple of two numbers defining number of points in the u,v directions
      points = list of 3D points
      degree[opt] = two numbers defining degree of the surface in the u,v directions
      closed[opt] = two booleans defining if the surface is closed in the u,v directions
    Returns:
      The identifier of the new object if successful.
      None if not successful, or on error.
    """
    points = rhutil.coerce3dpointlist(points, True)
    surf = Rhino.Geometry.NurbsSurface.CreateThroughPoints(points, count[0], count[1], degree[0], degree[1], closed[0], closed[1])
    if not surf: return scriptcontext.errorhandler()
    id = scriptcontext.doc.Objects.AddSurface(surf)
    if id!=System.Guid.Empty:
        scriptcontext.doc.Views.Redraw()
        return id


def AddSweep1(rail, shapes, closed=False):
    """Adds a surface created through profile curves that define the surface
    shape and one curve that defines a surface edge.
    Parameters:
      rail = identifier of the rail curve
      shapes = one or more cross section shape curves
      closed[opt] = If True, then create a closed surface
    Returns:
      List of new surface objects if successful
      None if not successfule, or on error
    """
    rail = rhutil.coercecurve(rail, -1, True)
    shapes = [rhutil.coercecurve(shape, -1, True) for shape in shapes]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    breps = Rhino.Geometry.Brep.CreateFromSweep(rail, shapes, closed, tolerance)
    if not breps: return scriptcontext.errorhandler()
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in breps]
    scriptcontext.doc.Views.Redraw()
    return rc


def AddSweep2(rails, shapes, closed=False):
    """Adds a surface created through profile curves that define the surface
    shape and two curves that defines a surface edge.
    Parameters:
      rails = identifiers of the two rail curve
      shapes = one or more cross section shape curves
      closed[opt] = If True, then create a closed surface
    Returns:
      List of new surface objects if successful
      None if not successfule, or on error
    """
    rail1 = rhutil.coercecurve(rails[0], -1, True)
    rail2 = rhutil.coercecurve(rails[1], -1, True)
    shapes = [rhutil.coercecurve(shape, -1, True) for shape in shapes]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    breps = Rhino.Geometry.Brep.CreateFromSweep(rail1, rail2, shapes, closed, tolerance)
    if not breps: return scriptcontext.errorhandler()
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in breps]
    scriptcontext.doc.Views.Redraw()
    return rc


def AddTorus(base, major_radius, minor_radius, direction=None):
    """Adds a torus shaped revolved surface to the document
    Parameters:
      base = 3D origin point of the torus or the base plane of the torus
      major_radius, minor_radius = the two radii of the torus
      directions[opt] = A point that defines the direction of the torus when base is a point.
        If omitted, a torus that is parallel to the world XY plane is created
    Returns:
      The identifier of the new object if successful.
      None if not successful, or on error.
    """
    baseplane = None
    basepoint = rhutil.coerce3dpoint(base)
    if basepoint is None:
        baseplane = rhutil.coerceplane(base, True)
        if direction!=None: return scriptcontext.errorhandler()
    if baseplane is None:
        direction = rhutil.coerce3dpoint(direction, False)
        if direction: direction = direction-basepoint
        else: direction = Rhino.Geometry.Vector3d.ZAxis
        baseplane = Rhino.Geometry.Plane(basepoint, direction)
    torus = Rhino.Geometry.Torus(baseplane, major_radius, minor_radius)
    revsurf = torus.ToRevSurface()
    rc = scriptcontext.doc.Objects.AddSurface(revsurf)
    scriptcontext.doc.Views.Redraw()
    return rc


def BooleanDifference(input0, input1, delete_input=True):
    """Performs a boolean difference operation on two sets of input surfaces
    and polysurfaces. For more details, see the BooleanDifference command in
    the Rhino help file
    Parameters:
        input0 = list of surfaces to subtract from
        input1 = list of surfaces to be subtracted
        delete_input[opt] = delete all input objects
    Returns:
        list of identifiers of newly created objects on success
        None on error
    """
    if type(input0) is list or type(input0) is tuple: pass
    else: input0 = [input0]
    
    if type(input1) is list or type(input1) is tuple: pass
    else: input1 = [input1]

    breps0 = [rhutil.coercebrep(id, True) for id in input0]
    breps1 = [rhutil.coercebrep(id, True) for id in input1]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newbreps = Rhino.Geometry.Brep.CreateBooleanDifference(breps0, breps1, tolerance)
    if newbreps is None: return scriptcontext.errorhandler()
    
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in newbreps]
    if delete_input:
        for id in input0: scriptcontext.doc.Objects.Delete(id, True)
        for id in input1: scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def BooleanIntersection(input0, input1, delete_input=True):
    """Performs a boolean intersection operation on two sets of input surfaces
    and polysurfaces. For more details, see the BooleanIntersection command in
    the Rhino help file
    Parameters:
        input0 = list of surfaces
        input1 = list of surfaces
        delete_input[opt] = delete all input objects
    Returns:
        list of identifiers of newly created objects on success
        None on error
    """
    if type(input0) is list or type(input0) is tuple: pass
    else: input0 = [input0]
    
    if type(input1) is list or type(input1) is tuple: pass
    else: input1 = [input1]

    breps0 = [rhutil.coercebrep(id, True) for id in input0]
    breps1 = [rhutil.coercebrep(id, True) for id in input1]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newbreps = Rhino.Geometry.Brep.CreateBooleanIntersection(breps0, breps1, tolerance)
    if newbreps is None: return scriptcontext.errorhandler()
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in newbreps]
    if delete_input:
        for id in input0: scriptcontext.doc.Objects.Delete(id, True)
        for id in input1: scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def BooleanUnion(input, delete_input=True):
    """Performs a boolean union operation on a set of input surfaces and
    polysurfaces. For more details, see the BooleanUnion command in the
    Rhino help file
    Parameters:
        input = list of surfaces to union
        delete_input[opt] = delete all input objects
    Returns:
        list of identifiers of newly created objects on success
        None on error
    """
    if len(input)<2: return scriptcontext.errorhandler()
    breps = [rhutil.coercebrep(id, True) for id in input]
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newbreps = Rhino.Geometry.Brep.CreateBooleanUnion(breps, tolerance)
    if newbreps is None: return scriptcontext.errorhandler()
    
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in newbreps]
    if delete_input:
        for id in input: scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def BrepClosestPoint(object_id, point):
    """Returns the point on a surface or polysurface that is closest to a test
    point. This function works on both untrimmed and trimmed surfaces.
    Parameters:
      object_id = The object's identifier.
      point = The test, or sampling point.
    Returns:
      A tuple of closest point information if successful. The list will
      contain the following information:
      Element     Type             Description
         0        Point3d          The 3-D point at the parameter value of the 
                                   closest point.
         1        (U, V)           Parameter values of closest point. Note, V 
                                   is 0 if the component index type is brep_edge
                                   or brep_vertex. 
         2        (type, index)    The type and index of the brep component that
                                   contains the closest point. Possible types are
                                   brep_face, brep_edge or brep_vertex.
         3        Vector3d         The normal to the brep_face, or the tangent
                                   to the brep_edge.  
      None if not successful, or on error.
    """
    brep = rhutil.coercebrep(object_id, True)
    point = rhutil.coerce3dpoint(point, True)
    rc = brep.ClosestPoint(point, 0.0)
    if rc[0]:
        type = int(rc[2].ComponentIndexType)
        index = rc[2].Index
        return rc[1], (rc[3], rc[4]), (type, index), rc[5]


def CapPlanarHoles(surface_id):
    """Caps planar holes in a surface or polysurface
    Returns:
      True or False indicating success or failure
    """
    brep = rhutil.coercebrep(surface_id, True)
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newbrep = brep.CapPlanarHoles(tolerance)
    if newbrep:
        if newbrep.SolidOrientation == Rhino.Geometry.BrepSolidOrientation.Inward:
            newbrep.Flip()
        surface_id = rhutil.coerceguid(surface_id)
        if surface_id and scriptcontext.doc.Objects.Replace(surface_id, newbrep):
            scriptcontext.doc.Views.Redraw()
            return True
    return False


def DuplicateEdgeCurves(object_id, select=False):
    """Duplicates the edge curves of a surface or polysurface. For more
    information, see the Rhino help file for information on the DupEdge
    command.
    Parameters:
      object_id = The identifier of the surface or polysurface object.
      select [opt] = Select the duplicated edge curves. The default is not
      to select (False).
    Returns:
      A list of Guids identifying the newly created curve objects if successful.
      None if not successful, or on error.
    """
    brep = rhutil.coercebrep(object_id, True)
    out_curves = brep.DuplicateEdgeCurves()
    curves = []
    for curve in out_curves:
        if curve.IsValid:
            rc = scriptcontext.doc.Objects.AddCurve(curve)
            curve.Dispose()
            if rc==System.Guid.Empty: return None
            curves.append(rc)
            if select: rhobject.SelectObject(rc)
    if curves: scriptcontext.doc.Views.Redraw()
    return curves


def DuplicateSurfaceBorder(surface_id):
    """Creates a curve that duplicates a surface or polysurface border
    Parameters:
      surface_id = identifier of a surface
    Returns:
      list of curve ids on success
      None on error
    """
    brep = rhutil.coercebrep(surface_id, True)
    curves = brep.DuplicateEdgeCurves(True)
    if curves is None: return scriptcontext.errorhandler()
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance * 2.1
    curves = Rhino.Geometry.Curve.JoinCurves(curves, tolerance)
    if curves is None: return scriptcontext.errorhandler()
    rc = [scriptcontext.doc.Objects.AddCurve(c) for c in curves]
    scriptcontext.doc.Views.Redraw()
    return rc


def EvaluateSurface(surface_id, u, v):
    "Evaluates a surface at a U,V parameter"
    surface = rhutil.coercesurface(surface_id, True)
    rc = surface.PointAt(u,v)
    if rc.IsValid: return rc
    return scriptcontext.errorhandler()


def ExtendSurface(surface_id, parameter, length, smooth=True):
    """Lengthens an untrimmed surface object
    Parameters:
      surface_id = identifier of a surface
      parameter = tuple of two values definfing the U,V parameter to evaluate.
        The surface edge closest to the U,V parameter will be the edge that is
        extended
      length = amount to extend to surface
      smooth[opt] = If True, the surface is extended smoothly curving from the
        edge. If False, the surface is extended in a straight line from the edge
    Returns:
      True or False indicating success or failure
    """
    surface = rhutil.coercesurface(surface_id, True)
    edge = surface.ClosestSide(parameter[0], parameter[1])
    newsrf = surface.Extend(edge, length, smooth)
    if newsrf:
        surface_id = rhutil.coerceguid(surface_id)
        if surface_id: scriptcontext.doc.Objects.Replace(surface_id, newsrf)
        scriptcontext.doc.Views.Redraw()
    return newsrf is not None


def ExplodePolysurfaces(object_ids, delete_input=False):
    """Explodes, or unjoins, one or more polysurface objects. Polysurfaces
    will be exploded into separate surfaces
    Parameters:
      object_ids = identifiers of polysurfaces to explode
      delete_input[opt] = delete input objects after exploding
    Returns:
      List of identifiers of exploded pieces on success
    """
    id = rhutil.coerceguid(object_ids, False)
    if id: object_ids = [id]
    ids = []
    for id in object_ids:
        brep = rhutil.coercebrep(id, True)
        if brep.Faces.Count>1:
            for i in range(brep.Faces.Count):
                copyface = brep.Faces[i].DuplicateFace(False)
                face_id = scriptcontext.doc.Objects.AddBrep(copyface)
                if face_id!=System.Guid.Empty: ids.append(face_id)
            if delete_input: scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return ids


def ExtractIsoCurve(surface_id, parameter, direction):
    """Extracts isoparametric curves from a surface
    Parameters:
      surface_id = identifier of a surface
      parameter = u,v parameter of the surface to evaluate
      direction
        0 = u, 1 = v, 2 = both
    Returns:
      list of curve ids on success
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    ids = []
    if direction==0 or direction==2:
        curves = None
        if type(surface) is Rhino.Geometry.BrepFace:
            curves = surface.TrimAwareIsoCurve(0, parameter[1])
        else:
            curves = [surface.IsoCurve(0,parameter[1])]
        if curves:
            for curve in curves:
                id = scriptcontext.doc.Objects.AddCurve(curve)
                if id!=System.Guid.Empty: ids.append(id)
    if direction==1 or direction==2:
        curves = None
        if type(surface) is Rhino.Geometry.BrepFace:
            curves = surface.TrimAwareIsoCurve(1, parameter[0])
        else:
            curves = [surface.IsoCurve(1,parameter[0])]
        if curves:
            for curve in curves:
                id = scriptcontext.doc.Objects.AddCurve(curve)
                if id!=System.Guid.Empty: ids.append(id)
    scriptcontext.doc.Views.Redraw()
    return ids


def ExtractSurface(object_id, face_indices, copy=False):
    """Separates or copies a surface or a copy of a surface from a polysurface
    Paramters:
      object_id: polysurface identifier
      face_indices: one or more numbers representing faces
      copy[opt]: If True the faces are copied. If False, the faces are extracted
    Returns:
      identifiers of extracted surface objects on success
    """
    brep = rhutil.coercebrep(object_id, True)
    if hasattr(face_indices, "__getitem__"): pass
    else: face_indices = [face_indices]
    rc = []
    face_indices = sorted(face_indices, reverse=True)
    for index in face_indices:
        face = brep.Faces[index]
        newbrep = face.DuplicateFace(True)
        id = scriptcontext.doc.Objects.AddBrep(newbrep)
        rc.append(id)
    if not copy:
        for index in face_indices: brep.Faces.RemoveAt(index)
        id = rhutil.coerceguid(object_id)
        scriptcontext.doc.Objects.Replace(id, brep)
    scriptcontext.doc.Views.Redraw()
    return rc


def ExtrudeCurve(curve_id, path_id):
    """Creates a surface by extruding a curve along a path
    Parameters:
      curve_id = identifier of the curve to extrude
      path_id = identifier of the path curve
    Returns:
      identifier of new surface on success
      None on error
    """
    curve1 = rhutil.coercecurve(curve_id, -1, True)
    curve2 = rhutil.coercecurve(path_id, -1, True)
    srf = Rhino.Geometry.SumSurface.Create(curve1, curve2)
    rc = scriptcontext.doc.Objects.AddSurface(srf)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def ExtrudeCurvePoint(curve_id, point):
    """Creates a surface by extruding a curve to a point
    Parameters:
      curve_id = identifier of the curve to extrude
      point = 3D point
    Returns:
      identifier of new surface on success
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    point = rhutil.coerce3dpoint(point, True)
    srf = Rhino.Geometry.Surface.CreateExtrusionToPoint(curve, point)
    rc = scriptcontext.doc.Objects.AddSurface(srf)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def ExtrudeCurveStraight(curve_id, start_point, end_point):
    """Create surface by extruding a curve along two points that define a line
    Parameters:
      curve_id = identifier of the curve to extrude
      start_point, end_point = 3D points
    Returns:
      identifier of new surface on success
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    start_point = rhutil.coerce3dpoint(start_point, True)
    end_point = rhutil.coerce3dpoint(end_point, True)
    vec = end_point - start_point
    srf = Rhino.Geometry.Surface.CreateExtrusion(curve, vec)
    rc = scriptcontext.doc.Objects.AddSurface(srf)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def ExtrudeSurface(surface, curve, cap=True):
    """Create surface by extruding along a path curve
    Parameters:
      surface = identifier of the surface to extrude
      curve = identifier of the path curve
      cap[opt] = extrusion is capped at both ends
    Returns:
      identifier of new surface on success
    """
    brep = rhutil.coercebrep(surface, True)
    curve = rhutil.coercecurve(curve, -1, True)
    newbrep = brep.Faces[0].CreateExtrusion(curve, cap)
    if newbrep:
        rc = scriptcontext.doc.Objects.AddBrep(newbrep)
        scriptcontext.doc.Views.Redraw()
        return rc


def FilletSurfaces(surface0, surface1, radius, uvparam0=None, uvparam1=None):
    """Create constant radius rolling ball fillets between two surfaces. Note,
    this function does not trim the original surfaces of the fillets
    Parameters:
      surface0, surface1 = identifiers of first and second surface
      radius = a positive fillet radius
      uvparam0[opt] = a u,v surface parameter of surface0 near where the fillet
        is expected to hit the surface
      uvparam1[opt] = same as uvparam0, but for surface1
    Returns:
      ids of surfaces created on success
      None on error
    """
    surface0 = rhutil.coercesurface(surface0, True)
    surface1 = rhutil.coercesurface(surface1, True)
    uvparam0 = rhutil.coerce2dpoint(uvparam0, True)
    uvparam1 = rhutil.coerce2dpoint(uvparam1, True)
    surfaces = None
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    if uvparam0 and uvparam1:
        surfaces = Rhino.Geometry.Surface.CreateRollingBallFillet(surface0, uvparam0, surface1, uvparam1, radius, tol)
    else:
        surfaces = Rhino.Geometry.Surface.CreateRollingBallFillet(surface0, surface1, radius, tol)
    if not surfaces: return scriptcontext.errorhandler()
    rc = []
    for surf in surfaces:
        rc.append( scriptcontext.doc.Objects.AddSurface(surf) )
    scriptcontext.doc.Views.Redraw()
    return rc


def FlipSurface(surface_id, flip=None):
    """Returns or changes the normal direction of a surface. This feature can
    also be found in Rhino's Dir command
    Parameters:
      surface_id = identifier of a surface object
      flip[opt] = new normal orientation, either flipped(True) or not flipped (False).
    Returns:
      if flipped is not specified, the current normal orientation
      if flipped is specified, the previous normal orientation
      None on error
    """
    brep = rhutil.coercebrep(surface_id, True)
    if brep.Faces.Count>1: return scriptcontext.errorhandler()
    face = brep.Faces[0]
    old_reverse = face.OrientationIsReversed
    if flip!=None and brep.IsSolid==False and old_reverse!=flip:
        brep.Flip()
        surface_id = rhutil.coerceguid(surface_id)
        if surface_id: scriptcontext.doc.Objects.Replace(surface_id, brep)
        scriptcontext.doc.Views.Redraw()
    return old_reverse


def ReverseSurface(surface_id, direction):
    """Reverses U or V directions of a surface, or swaps (transposes) U and V directions.
    Note, unlike the RhinoScript version, this function only works on untrimmed surfaces.
    Parameters:
      surface_id = identifier of a surfaceobject
      direction
        1 = reverse U, 2 = reverse V, 4 = transpose U and V (values can be combined)
    Returns:
      Boolean indicating success or failure
      None on error
    """
    brep = rhutil.coercebrep(surface_id, True)
    if not brep.IsSurface: return scriptcontext.errorhandler()
    if direction == 0: return True
    flipped = brep.Faces[0].OrientationIsReversed
    face = brep.Faces[0].UnderlyingSurface()
    if direction & 1:
        face = face.Reverse(0)
        flipped = not flipped
        if not face: return False
    if direction & 2:
        face = face.Reverse(1)
        flipped = not flipped
        if not face: return False
    if direction & 4:
        face = face.Transpose()
        flipped = not flipped
        if not face: return False
    newbrep = Rhino.Geometry.Brep.TryConvertBrep(face)
    if not newbrep: return scriptcontext.errorhandler()
    if flipped: newbrep.Flip()
    scriptcontext.doc.Objects.Replace(surface_id, newbrep)
    scriptcontext.doc.Views.Redraw()
    return True


def IntersectBreps(brep1, brep2, tolerance=None):
    """Intersects a brep object with another brep object. Note, unlike the
    SurfaceSurfaceIntersection function this function works on trimmed surfaces.
    Parameters:
      brep1 = identifier of first brep object
      brep2 = identifier of second brep object
      tolerance = Distance tolerance at segment midpoints. If omitted,
                  the current absolute tolerance is used.
    Returns:
      List of Guids identifying the newly created intersection curve and
      point objects if successful.
      None if not successful, or on error.
    """
    brep1 = rhutil.coercebrep(brep1, True)
    brep2 = rhutil.coercebrep(brep2, True)
    if tolerance is None or tolerance < 0.0:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    rc = Rhino.Geometry.Intersect.Intersection.BrepBrep(brep1, brep2, tolerance)
    if not rc[0]: return None
    out_curves = rc[1]
    out_points = rc[2]
    merged_curves = Rhino.Geometry.Curve.JoinCurves(out_curves, 2.1 * tolerance)
    
    ids = []
    if merged_curves:
        for curve in merged_curves:
            if curve.IsValid:
                rc = scriptcontext.doc.Objects.AddCurve(curve)
                curve.Dispose()
                if rc==System.Guid.Empty: return scriptcontext.errorhandler()
                ids.append(rc)
    else:
        for curve in out_curves:
            if curve.IsValid:
                rc = scriptcontext.doc.Objects.AddCurve(curve)
                curve.Dispose()
                if rc==System.Guid.Empty: return scriptcontext.errorhandler()
                ids.append(rc)
    for point in out_points:
        rc = scriptcontext.doc.Objects.AddPoint(point)
        if rc==System.Guid.Empty: return scriptcontext.errorhandler()
        ids.append(rc)
    if ids:
        scriptcontext.doc.Views.Redraw()
        return ids


def IntersectSpheres(sphere_plane0, sphere_radius0, sphere_plane1, sphere_radius1):
    """Calculates intersections of two spheres
    Parameters:
      sphere_plane0 = an equatorial plane of the first sphere. The origin of the
        plane will be the center point of the sphere
      sphere_radius0 = radius of the first sphere
      sphere_plane1 = plane for second sphere
      sphere_radius1 = radius for second sphere
    Returns:
      List of intersection results
        element 0 = type of intersection (0=point, 1=circle, 2=spheres are identical)
        element 1 = Point of intersection or plane of circle intersection
        element 2 = radius of circle if circle intersection
      None on error
    """
    plane0 = rhutil.coerceplane(sphere_plane0, True)
    plane1 = rhutil.coerceplane(sphere_plane1, True)
    sphere0 = Rhino.Geometry.Sphere(plane0, sphere_radius0)
    sphere1 = Rhino.Geometry.Sphere(plane1, sphere_radius1)
    rc, circle = Rhino.Geometry.Intersect.Intersection.SphereSphere(sphere0, sphere1)
    if rc==Rhino.Geometry.Intersect.SphereSphereIntersection.Point:
        return [0, circle.Center]
    if rc==Rhino.Geometry.Intersect.SphereSphereIntersection.Circle:
        return [1, circle.Plane, circle.Radius]
    if rc==Rhino.Geometry.Intersect.SphereSphereIntersection.Overlap:
        return [2]
    return scriptcontext.errorhandler()


def IsBrep(object_id):
    """Verifies an object is a Brep, or a boundary representation model, object.
    Parameters:
      object_id = The object's identifier.
    Returns:
      True if successful, otherwise False.
      None on error.
    """
    return rhutil.coercebrep(object_id)!=None


def IsCone(object_id):
    "Determines if a surface is a portion of a cone"
    surface = rhutil.coercesurface(object_id, True)
    return surface.IsCone()


def IsCylinder(object_id):
    "Determines if a surface is a portion of a cone"
    surface = rhutil.coercesurface(object_id, True)
    return surface.IsCylinder()


def IsPlaneSurface(object_id):
    """Verifies an object is a plane surface. Plane surfaces can be created by
    the Plane command. Note, a plane surface is not a planar NURBS surface
    """
    face = rhutil.coercesurface(object_id, True)
    if type(face) is Rhino.Geometry.BrepFace and face.IsSurface:
        return type(face.UnderlyingSurface()) is Rhino.Geometry.PlaneSurface
    return False
    

def IsPointInSurface(object_id, point, strictly_in=False, tolerance=None):
    """Verifies that a point is inside a closed surface or polysurface
    Parameters:
      object_id: the object's identifier
      point: list of three numbers or Point3d. The test, or sampling point
      strictly_in[opt]: If true, the test point must be inside by at least tolerance
      tolerance[opt]: distance tolerance used for intersection and determining
        strict inclusion. If omitted, Rhino's internal tolerance is used
    Returns:
      True if successful, otherwise False
    """
    object_id = rhutil.coerceguid(object_id, True)
    point = rhutil.coerce3dpoint(point, True)
    if object_id==None or point==None: return scriptcontext.errorhandler()
    obj = scriptcontext.doc.Objects.Find(object_id)
    if tolerance is None: tolerance = Rhino.RhinoMath.SqrtEpsilon
    brep = None
    if type(obj)==Rhino.DocObjects.ExtrusionObject:
        brep = obj.ExtrusionGeometry.ToBrep(False)
    elif type(obj)==Rhino.DocObjects.BrepObject:
        brep = obj.BrepGeometry
    elif hasattr(obj, "Geometry"):
        brep = obj.Geometry
    return brep.IsPointInside(point, tolerance, strictly_in)


def IsPointOnSurface(object_id, point):
    """Verifies that a point lies on a surface
    Parameters:
      object_id: the object's identifier
      point: list of three numbers or Point3d. The test, or sampling point
    Returns:
      True if successful, otherwise False
    """
    surf = rhutil.coercesurface(object_id, True)
    point = rhutil.coerce3dpoint(point, True)
    rc, u, v = surf.ClosestPoint(point)
    if rc:
        srf_pt = surf.PointAt(u,v)
        if srf_pt.DistanceTo(point)>scriptcontext.doc.ModelAbsoluteTolerance:
            rc = False
        else:
            rc = surf.IsPointOnFace(u,v) != Rhino.Geometry.PointFaceRelation.Exterior
    return rc


def IsPolysurface(object_id):
    """Verifies an object is a polysurface. Polysurfaces consist of two or more
    surfaces joined together. If the polysurface fully encloses a volume, it is
    considered a solid.
    Parameters:
      object_id: the object's identifier
    Returns:
      True is successful, otherwise False
    """
    brep = rhutil.coercebrep(object_id)
    if brep is None: return False
    return brep.Faces.Count>1


def IsPolysurfaceClosed(object_id):
    """Verifies a polysurface object is closed. If the polysurface fully encloses
    a volume, it is considered a solid.
    Parameters:
      object_id: the object's identifier
    Returns:
      True is successful, otherwise False
    """
    brep = rhutil.coercebrep(object_id, True)
    return brep.IsSolid


def IsSphere(object_id):
    "Determines if a surface is a portion of a sphere"
    surface = rhutil.coercesurface(object_id, True)
    return surface.IsSphere()


def IsSurface(object_id):
    """Verifies an object is a surface. Brep objects with only one face are
    also considered surfaces.
    Parameters:
      object_id = the object's identifier.
    Returns:
      True if successful, otherwise False.
    """
    brep = rhutil.coercebrep(object_id)
    if brep and brep.Faces.Count==1: return True
    surface = rhutil.coercesurface(object_id)
    return (surface!=None)


def IsSurfaceClosed( surface_id, direction ):
    """Verifies a surface object is closed in the specified direction.  If the
    surface fully encloses a volume, it is considered a solid
    Parameters:
      surface_id = identifier of a surface
      direction = 0=U, 1=V
    Returns:
      True or False
    """
    surface = rhutil.coercesurface(surface_id, True)
    return surface.IsClosed(direction)


def IsSurfacePeriodic(surface_id, direction):
    """Verifies a surface object is periodic in the specified direction.
    Parameters:
      surface_id = identifier of a surface
      direction = 0=U, 1=V
    Returns:
      True or False
    """
    surface = rhutil.coercesurface(surface_id, True)
    return surface.IsPeriodic(direction)


def IsSurfacePlanar(surface_id, tolerance=None):
    """Verifies a surface object is planar
    Parameters:
      surface_id = identifier of a surface
      tolerance[opt] = tolerance used when checked. If omitted, the current absolute
        tolerance is used
    Returns:
      True or False
    """
    surface = rhutil.coercesurface(surface_id, True)
    if tolerance is None:
        tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    return surface.IsPlanar(tolerance)


def IsSurfaceRational(surface_id):
    """Verifies a surface object is rational
    Parameters:
      surface_id = the surface's identifier
    """
    surface = rhutil.coercesurface(surface_id, True)
    ns = surface.ToNurbsSurface()
    if ns is None: return False
    return ns.IsRational


def IsSurfaceSingular(surface_id, direction):
    """Verifies a surface object is singular in the specified direction.
    Surfaces are considered singular if a side collapses to a point.
    Parameters:
      surface_id = the surface's identifier
      direction: 0=south, 1=east, 2=north, 3=west
    Returns:
      True or False
    """
    surface = rhutil.coercesurface(surface_id, True)
    return surface.IsSingular(direction)


def IsSurfaceTrimmed(surface_id):
    """Verifies a surface object has been trimmed
    Parameters:
      surface_id = the surface's identifier
    Returns:
      True or False
    """
    brep = rhutil.coercebrep(surface_id, True)
    return not brep.IsSurface


def IsTorus(surface_id):
    "Determines if a surface is a portion of a torus"
    surface = rhutil.coercesurface(surface_id, True)
    return surface.IsTorus()


def JoinSurfaces(object_ids, delete_input=False):
    """Joins two or more surface or polysurface objects together to form one
    polysurface object
    Parameters:
      object_ids = list of object identifiers
    Returns:
      identifier of newly created object on success
      None on failure
    """
    breps = [rhutil.coercebrep(id, True) for id in object_ids]
    if len(breps)<2: return scriptcontext.errorhandler()
    tol = scriptcontext.doc.ModelAbsoluteTolerance * 2.1
    joinedbreps = Rhino.Geometry.Brep.JoinBreps(breps, tol)
    if joinedbreps is None or len(joinedbreps)!=1:
        return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddBrep(joinedbreps[0])
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    if delete_input:
        for id in object_ids:
            id = rhutil.coerceguid(id)
            scriptcontext.doc.Objects.Delete(id, True)
    scriptcontext.doc.Views.Redraw()
    return rc


def MakeSurfacePeriodic(surface_id, direction, delete_input=False):
    """Makes an existing surface a periodic NURBS surface
    Paramters:
      surface_id = the surface's identifier
      direction = The direction to make periodic, either 0=U or 1=V
      delete_input[opt] = delete the input surface
    Returns:
      if delete_input is False, identifier of the new surface
      if delete_input is True, identifer of the modifier surface
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    newsurf = Rhino.Geometry.Surface.CreatePeriodicSurface(surface, direction)
    if newsurf is None: return scriptcontext.errorhandler()
    id = rhutil.coerceguid(surface_id)
    if delete_input:
        scriptcontext.doc.Objects.Replace(id, newsurf)
    else:
        id = scriptcontext.doc.Objects.AddSurface(newsurf)
    scriptcontext.doc.Views.Redraw()
    return id


def OffsetSurface(surface_id, distance, tolerance=None, both_sides=False, create_solid=False):
    """Offsets a trimmed or untrimmed surface by a distance. The offset surface
    will be added to Rhino.
    Parameters:
      surface_id = the surface's identifier
      distance = the distance to offset
      tolerance [opt] = The offset tolerance. Use 0.0 to make a loose offset. Otherwise, the
        document's absolute tolerance is usually sufficient.
      both_sides [opt] = Offset to both sides of the input surface
      create_solid [opt] = Make a solid object
    Returns:
      identifier of the new object if successful
      None on error
    """
    brep = rhutil.coercebrep(surface_id, True)
    face = None
    if brep.Faces.Count == 1: face = brep.Faces[0]
    if face is None: return scriptcontext.errorhandler()
    if tolerance is None: tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    newbrep = Rhino.Geometry.Brep.CreateFromOffsetFace(face, distance, tolerance, both_sides, create_solid)
    if newbrep is None: return scriptcontext.errorhandler()
    rc = scriptcontext.doc.Objects.AddBrep(newbrep)
    if rc==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return rc


def PullCurve(surface, curve, delete_input=False):
    """Pulls a curve object to a surface object
    Parameters:
      surface = the surface's identifier
      curve = the curve's identifier
      delete_input[opt] = should the input items be deleted
    Returns:
      list of new curves if successful
      None on error
    """
    crvobj = rhutil.coercerhinoobject(curve, True, True)
    brep = rhutil.coercebrep(surface, True)
    curve = rhutil.coercecurve(curve, -1, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    curves = Rhino.Geometry.Curve.PullToBrepFace(curve, brep.Faces[0], tol)
    rc = [scriptcontext.doc.Objects.AddCurve(curve) for curve in curves]
    if rc:
        if delete_input and crvobj:
            scriptcontext.doc.Objects.Delete(crvobj, True)
        scriptcontext.doc.Views.Redraw()
        return rc


def RebuildSurface(object_id, degree=(3,3), pointcount=(10,10)):
    """Rebuilds a surface to a given degree and control point count. For more
    information see the Rhino help file for the Rebuild command
    Parameters:
      object_id = the surface's identifier
      degree[opt] = two numbers that identify surface degree in both U and V directions
      pointcount[opt] = two numbers that identify the surface point count in both the U and V directions
    Returns:
      True of False indicating success or failure
    """
    surface = rhutil.coercesurface(object_id, True)
    newsurf = surface.Rebuild( degree[0], degree[1], pointcount[0], pointcount[1] )
    if newsurf is None: return False
    object_id = rhutil.coerceguid(object_id)
    rc = scriptcontext.doc.Objects.Replace(object_id, newsurf)
    if rc: scriptcontext.doc.Views.Redraw()
    return rc


def ShootRay(surface_ids, start_point, direction, reflections=10):
    """Shoots a ray at a collection of surfaces
    Parameters:
      surface_ids = one of more surface identifiers
      start_point = starting point of the ray
      direction = vector identifying the direction of the ray
      reflections[opt] = the maximum number of times the ray will be reflected
    Returns:
      list of reflection points on success
      None on error
    """
    start_point = rhutil.coerce3dpoint(start_point, True)
    direction = rhutil.coerce3dvector(direction, True)
    id = rhutil.coerceguid(surface_ids, False)
    if id: surface_ids = [id]
    ray = Rhino.Geometry.Ray3d(start_point, direction)
    breps = []
    for id in surface_ids:
        brep = rhutil.coercebrep(id)
        if brep: breps.append(brep)
        else:
            surface = rhutil.coercesurface(id, True)
            breps.append(surface)
    if not breps: return scriptcontext.errorhandler()
    points = Rhino.Geometry.Intersect.Intersection.RayShoot(ray, breps, reflections)
    if points:
        rc = []
        rc.append(start_point)
        rc = rc + list(points)
        return rc
    return scriptcontext.errorhandler()


def ShortPath(surface_id, start_point, end_point):
    """Creates the shortest possible curve(geodesic) between two points on a
    surface. For more details, see the ShortPath command in Rhino help
    Parameters:
      surface_id = identifier of a surface
      start_point, end_point = start/end points of the short curve
    Returns:
      identifier of the new surface on success
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    start = rhutil.coerce3dpoint(start_point, True)
    end = rhutil.coerce3dpoint(end_point, True)
    rc_start, u_start, v_start = surface.ClosestPoint(start)
    rc_end, u_end, v_end = surface.ClosestPoint(end)
    if not rc_start or not rc_end: return scriptcontext.errorhandler()
    start = Rhino.Geometry.Point2d(u_start, v_start)
    end = Rhino.Geometry.Point2d(u_end, v_end)
    tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    curve = surface.ShortPath(start, end, tolerance)
    if curve is None: return scriptcontext.errorhandler()
    id = scriptcontext.doc.Objects.AddCurve(curve)
    if id==System.Guid.Empty: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return id


def ShrinkTrimmedSurface(object_id, create_copy=False):
    """Shrinks the underlying untrimmed surfaces near to the trimming
    boundaries. See the ShrinkTrimmedSrf command in the Rhino help.
    Parameters:
      object_id = the surface's identifier
      create_copy[opt] = If True, the original surface is not deleted
    Returns:
      If create_copy is False, True or False indifating success or failure
      If create_copy is True, the identifier of the new surface
      None on error
    """
    brep = rhutil.coercebrep(object_id, True)
    if not brep.Faces.ShrinkFaces(): return scriptcontext.errorhandler()
    rc = None
    object_id = rhutil.coerceguid(object_id)
    if create_copy:
        oldobj = scriptcontext.doc.Objects.Find(object_id)
        attr = oldobj.Attributes
        rc = scriptcontext.doc.Objects.AddBrep(brep, attr)
    else:
        rc = scriptcontext.doc.Objects.Replace(object_id, brep)
    scriptcontext.doc.Views.Redraw()
    return rc


def __GetMassProperties(object_id, area):
    surface = rhutil.coercebrep(object_id)
    if surface is None:
        surface = rhutil.coercesurface(object_id)
        if surface is None: return None
    if area==True: return Rhino.Geometry.AreaMassProperties.Compute(surface)
    if not surface.IsSolid: return None
    return Rhino.Geometry.VolumeMassProperties.Compute(surface)


def SplitBrep(brep_id, cutter_id, delete_input=False):
    """Splits a brep
    Parameters:
      brep = identifier of the brep to split
      cutter = identifier of the brep to split with
    Returns:
      identifiers of split pieces on success
      None on error
    """
    brep = rhutil.coercebrep(brep_id, True)
    cutter = rhutil.coercebrep(cutter_id, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    pieces = brep.Split(cutter, tol)
    if not pieces: return scriptcontext.errorhandler()
    if delete_input:
        brep_id = rhutil.coerceguid(brep_id)
        scriptcontext.doc.Objects.Delete(brep_id, True)
    rc = [scriptcontext.doc.Objects.AddBrep(piece) for piece in pieces]
    scriptcontext.doc.Views.Redraw()
    return rc


def SurfaceArea(object_id):
    """Calculate the area of a surface or polysurface object. The results are
    based on the current drawing units
    Parameters:
      object_id = the surface's identifier
    Returns:
      list of area information on success (area, absolute error bound)
      None on error
    """
    amp = __GetMassProperties(object_id, True)
    if amp: return amp.Area, amp.AreaError


def SurfaceAreaCentroid(object_id):
    """Calculates the area centroid of a surface or polysurface
    Parameters:
      object_id = the surface's identifier
    Returns:
      (Area Centriod, Error bound) on success
      None on error
    """
    amp = __GetMassProperties(object_id, True)
    if amp is None: return scriptcontext.errorhandler()
    return amp.Centroid, amp.CentroidError


def __AreaMomentsHelper(surface_id, area):
    mp = __GetMassProperties(surface_id, area)
    if mp is None: return scriptcontext.errorhandler()
    a = (mp.WorldCoordinatesFirstMoments.X, mp.WorldCoordinatesFirstMoments.Y, mp.WorldCoordinatesFirstMoments.Z)
    b = (mp.WorldCoordinatesFirstMomentsError.X, mp.WorldCoordinatesFirstMomentsError.Y, mp.WorldCoordinatesFirstMomentsError.Z)
    c = (mp.WorldCoordinatesSecondMoments.X, mp.WorldCoordinatesSecondMoments.Y, mp.WorldCoordinatesSecondMoments.Z)
    d = (mp.WorldCoordinatesSecondMomentsError.X, mp.WorldCoordinatesSecondMomentsError.Y, mp.WorldCoordinatesSecondMomentsError.Z)
    e = (mp.WorldCoordinatesProductMoments.X, mp.WorldCoordinatesProductMoments.Y, mp.WorldCoordinatesProductMoments.Z)
    f = (mp.WorldCoordinatesProductMomentsError.X, mp.WorldCoordinatesProductMomentsError.Y, mp.WorldCoordinatesProductMomentsError.Z)
    g = (mp.WorldCoordinatesMomentsOfInertia.X, mp.WorldCoordinatesMomentsOfInertia.Y, mp.WorldCoordinatesMomentsOfInertia.Z)
    h = (mp.WorldCoordinatesMomentsOfInertiaError.X, mp.WorldCoordinatesMomentsOfInertiaError.Y, mp.WorldCoordinatesMomentsOfInertiaError.Z)
    i = (mp.WorldCoordinatesRadiiOfGyration.X, mp.WorldCoordinatesRadiiOfGyration.Y, mp.WorldCoordinatesRadiiOfGyration.Z)
    j = (0,0,0) # need to add error calc to RhinoCommon
    k = (mp.CentroidCoordinatesMomentsOfInertia.X, mp.CentroidCoordinatesMomentsOfInertia.Y, mp.CentroidCoordinatesMomentsOfInertia.Z)
    l = (mp.CentroidCoordinatesMomentsOfInertiaError.X, mp.CentroidCoordinatesMomentsOfInertiaError.Y, mp.CentroidCoordinatesMomentsOfInertiaError.Z)
    m = (mp.CentroidCoordinatesRadiiOfGyration.X, mp.CentroidCoordinatesRadiiOfGyration.Y, mp.CentroidCoordinatesRadiiOfGyration.Z)
    n = (0,0,0) #need to add error calc to RhinoCommon
    return (a,b,c,d,e,f,g,h,i,j,k,l,m,n)


def SurfaceAreaMoments(surface_id):
    """Calculates area moments of inertia of a surface or polysurface object.
    See the Rhino help for "Mass Properties calculation details"
    Parameters:
      surface_id = the surface's identifier
    Returns:
      list of moments and error bounds - see help topic
      None on error
    """
    return __AreaMomentsHelper(surface_id, True)


def SurfaceClosestPoint(surface_id, test_point):
    """Returns U,V parameters of point on a surface that is closest to a test point
    Parameters:
      surface_id = identifier of a surface object
      test_point = sampling point
    Returns:
      The U,V parameters of the closest point on the surface if successful.
      None on error.
    """
    surface = rhutil.coercesurface(surface_id, True)
    point = rhutil.coerce3dpoint(test_point, True)
    rc, u, v = surface.ClosestPoint(point)
    if not rc: return None
    return u,v


def SurfaceCone(surface_id):
    """Returns the definition of a surface cone
    Parameters:
      surface_id = the surface's identifier
    Returns:
      tuple containing the definition of the cone if successful
        element 0 = the plane of the cone. The apex of the cone is at the
            plane's origin and the axis of the cone is the plane's z-axis
        element 1 = the height of the cone
        element 2 = the radius of the cone
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    rc, cone = surface.TryGetCone()
    if not rc: return scriptcontext.errorhandler()
    return cone.Plane, cone.Height, cone.Radius


def SurfaceCurvature(surface_id, parameter):
    """Returns the curvature of a surface at a U,V parameter. See Rhino help
    for details of surface curvature
    Parameters:
      surface_id = the surface's identifier
      parameter = u,v parameter
    Returns:
      tuple of curvature information
        element 0 = point at specified U,V parameter
        element 1 = normal direction
        element 2 = maximum principal curvature
        element 3 = maximum principal curvature direction
        element 4 = minimum principal curvature
        element 5 = minimum principal curvature direction
        element 6 = gaussian curvature
        element 7 = mean curvature
      None if not successful, or on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    if len(parameter)<2: return scriptcontext.errorhandler()
    c = surface.CurvatureAt(parameter[0], parameter[1])
    if c is None: return scriptcontext.errorhandler()
    return c.Point, c.Normal, c.Kappa(0), c.Direction(0), c.Kappa(1), c.Direction(1), c.Gaussian, c.Mean


def SurfaceCylinder(surface_id):
    """Returns the definition of a cylinder surface
    Parameters:
      surface_id = the surface's identifier
    Returns:
      tuple of the cylinder plane, height, radius on success
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    rc, cylinder = surface.TryGetCylinder(tol)
    if rc:
        circle = cylinder.CircleAt(0)
        return circle.Plane, cylinder.TotalHeight, circle.Radius


def SurfaceDegree(surface_id, direction=2):
    """Returns the degree of a surface object in the specified direction
    Parameters:
      surface_id = the surface's identifier
      direction[opt]
        0 = U, 1 = v, 2 = both
    Returns:
      Tuple of two values if direction = 2
      Single number if direction = 0 or 1
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    if direction==0 or direction==1: return surface.Degree(direction)
    if direction==2: return surface.Degree(0), surface.Degree(1)
    return scriptcontext.errorhandler()


def SurfaceDomain(surface_id, direction):
    """Returns the domain of a surface object in the specified direction.
    Parameters:
      surface_id = the surface's identifier
      direction = either 0 = U, or 1 = V
    Returns:
      list containing the domain interval in the specified direction
      None if not successful, or on error
    """
    if direction!=0 and direction!=1: return scriptcontext.errorhandler()
    surface = rhutil.coercesurface(surface_id, True)
    domain = surface.Domain(direction)
    return domain.T0, domain.T1


def SurfaceEditPoints(surface_id, return_parameters=False, return_all=True):
    """Returns the edit, or Greville points of a surface object. For each
    surface control point, there is a corresponding edit point
    Parameters:
      surface_id = the surface's identifier
      return_parameters[opt] = If False, edit points are returned as a list of
        3D points. If True, edit points are returned as a list of U,V surface
        parameters
      return_all[opt] = If True, all surface edit points are returned. If False,
        the function will return surface edit points based on whether or not the
        surface is closed or periodic
    Returns:
      if return_parameters is False, a list of 3D points
      if return_parameters is True, a list of U,V parameters
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    nurb = surface.ToNurbsSurface()
    if not nurb: return scriptcontext.errorhandler()
    ufirst = 0
    ulast = nurb.Points.CountU
    vfirst = 0
    vlast = nurb.Points.CountV
    if not return_all:
        if nurb.IsClosed(0): ulast = nurb.Points.CountU-1
        if nurbs.IsPeriodic(0):
            degree = nurb.Degree(0)
            ufirst = degree/2
            ulast = nurb.Points.CountU-degree+ufirst
        if nurb.IsClosed(1): vlast = nurb.Points.CountV-1
        if nurbs.IsPeriodic(1):
            degree = nurb.Degree(1)
            vfirst = degree/2
            vlast = nurb.Points.CountV-degree+vfirst
    rc = []
    for u in range(ufirst, ulast):
        for v in range(vfirst, vlast):
            pt = nurb.Points.GetGrevillePoint(u,v)
            if not return_parameters: pt = nurb.PointAt(pt.X, pt.Y)
            rc.append(pt)
    return rc


def SurfaceEvaluate(surface_id, parameter, derivative):
    """A general purpose surface evaluator
    Parameters:
      surface_id = the surface's identifier
      parameter = u,v parameter to evaluate
      derivative = number of derivatives to evaluate
    Returns:
      list of derivatives on success
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    success, point, der = surface.Evaluate(parameter[0], parameter[1], derivative)
    if not success: return scriptcontext.errorhandler()
    rc = [point]
    for d in der: rc.append(d)
    return rc


def SurfaceFrame(surface_id, uv_parameter):
    """Returns a plane based on the normal, u, and v directions at a surface
    U,V parameter
    Parameters:
      surface_id = the surface's identifier
      uv_parameter = u,v parameter to evaluate
    Returns:
      plane on success
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    rc, frame = surface.FrameAt(uv_parameter[0], uv_parameter[1])
    if rc: return frame


def SurfaceIsocurveDensity(surface_id, density=None):
    """Returns or sets the isocurve density of a surface or polysurface object.
    An isoparametric curve is a curve of constant U or V value on a surface.
    Rhino uses isocurves and surface edge curves to visualize the shape of a
    NURBS surface
    Parameters:
      surface_id = the surface's identifier
      density[opt] = the isocurve wireframe density. The possible values are
          -1: Hides the surface isocurves
           0: Display boundary and knot wires
           1: Display boundary and knot wires and one interior wire if there
              are no interior knots
         >=2: Display boundary and knot wires and (N+1) interior wires
    Returns:
      If density is not specified, then the current isocurve density if successful
      If density is specified, the the previous isocurve density if successful
      None on error
    """
    rhino_object = rhutil.coercerhinoobject(surface_id, True, True)
    if not isinstance(rhino_object, Rhino.DocObjects.BrepObject):
        return scriptcontext.errorhandler()
    rc = rhino_object.Attributes.WireDensity
    if density is not None:
        if density<0: density = -1
        rhino_object.Attributes.WireDensity = density
        rhino_object.CommitChanges()
        scriptcontext.doc.Views.Redraw()
    return rc


def SurfaceKnotCount(surface_id):
    """Returns the control point count of a surface
      surface_id = the surface's identifier
    Returns:
      (U count, V count) on success
    """
    surface = rhutil.coercesurface(surface_id, True)
    ns = surface.ToNurbsSurface()
    return ns.KnotsU.Count, ns.KnotsV.Count


def SurfaceKnots(surface_id):
    """Returns the knots, or knot vector, of a surface object.
    Parameters:
      surface_id = the surface's identifier
    Returns:
      The list of knot values of the surface if successful. The list will
      contain the following information:
      Element     Description
        0         Knot vector in U direction
        1         Knot vector in V direction
      None if not successful, or on error.
    """
    surface = rhutil.coercesurface(surface_id, True)
    nurb_surf = surface.ToNurbsSurface()
    if nurb_surf is None: return scriptcontext.errorhandler()
    s_knots = [knot for knot in nurb_surf.KnotsU]
    t_knots = [knot for knot in nurb_surf.KnotsV]
    if not s_knots or not t_knots: return scriptcontext.errorhandler()
    return s_knots, t_knots


def SurfaceNormal(surface_id, uv_parameter):
    """Returns 3D vector that is the normal to a surface at a parameter
    Parameters:
      surface_id = the surface's identifier
      uv_parameter = the uv parameter to evaluate
    Returns:
      Normal vector on success
    """
    surface = rhutil.coercesurface(surface_id, True)
    return surface.NormalAt(uv_parameter[0], uv_parameter[1])


def SurfaceNormalizedParameter(surface_id, parameter):
    """Converts surface parameter to a normalized surface parameter; one that
    ranges between 0.0 and 1.0 in both the U and V directions
    Parameters:
      surface_id = the surface's identifier
      parameter = the surface parameter to convert
    Returns:
      normalized surface parameter if successful
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    u_domain = surface.Domain(0)
    v_domain = surface.Domain(1)
    if parameter[0]<u_domain.Min or parameter[0]>u_domain.Max:
        return scriptcontext.errorhandler()
    if parameter[1]<v_domain.Min or parameter[1]>v_domain.Max:
        return scriptcontext.errorhandler()
    u = u_domain.NormalizedParameterAt(parameter[0])
    v = v_domain.NormalizedParameterAt(parameter[1])
    return u,v


def SurfaceParameter(surface_id, parameter):
    """Converts normalized surface parameter to a surface parameter; or
    within the surface's domain
    Parameters:
      surface_id = the surface's identifier
      parameter = the normalized parameter to convert
    Returns:
      surface parameter as tuple on success
    """
    surface = rhutil.coercesurface(surface_id, True)
    x = surface.Domain(0).ParameterAt(parameter[0])
    y = surface.Domain(1).ParameterAt(parameter[1])
    return x, y


def SurfacePointCount(surface_id):
    """Returns the control point count of a surface
      surface_id = the surface's identifier
    Returns:
      (U count, V count) on success
    """
    surface = rhutil.coercesurface(surface_id, True)
    ns = surface.ToNurbsSurface()
    return ns.Points.CountU, ns.Points.CountV


def SurfacePoints(surface_id, return_all=True):
    """Returns the control points, or control vertices, of a surface object
    Parameters:
      surface_id = the surface's identifier
      return_all[opt] = If True all surface edit points are returned. If False,
        the function will return surface edit points based on whether or not
        the surface is closed or periodic
    Returns:
      the control points if successful
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    ns = surface.ToNurbsSurface()
    if ns is None: return scriptcontext.errorhandler()
    rc = []
    for u in range(ns.Points.CountU):
        for v in range(ns.Points.CountV):
            pt = ns.Points.GetControlPoint(u,v)
            rc.append(pt.Location)
    return rc


def SurfaceTorus(surface_id):
    """Returns the definition of a surface torus
    Parameters:
      surface_id = the surface's identifier
    Returns:
      tuple containing the definition of the torus if successful
        element 0 = the base plane of the torus
        element 1 = the major radius of the torus
        element 2 = the minor radius of the torus
      None on error
    """
    surface = rhutil.coercesurface(surface_id, True)
    rc, torus = surface.TryGetTorus()
    if rc: return torus.Plane, torus.MajorRadius, torus.MinorRadius


def SurfaceVolume(object_id):
    """Calculates volume of a closed surface or polysurface
    Parameters:
      object_id = the surface's identifier
    Returns:
      (Volume, Error bound) on success
      None on error
    """
    vmp = __GetMassProperties(object_id, False)
    if vmp: return vmp.Volume, vmp.VolumeError


def SurfaceVolumeCentroid(object_id):
    """Calculates volume centroid of a closed surface or polysurface
    Parameters:
      object_id = the surface's identifier
    Returns:
      (Volume Centriod, Error bound) on success
      None on error
    """
    vmp = __GetMassProperties(object_id, False)
    if vmp: return vmp.Centroid, vmp.CentroidError


def SurfaceVolumeMoments(surface_id):
    """Calculates volume moments of inertia of a surface or polysurface object.
    For more information, see Rhino help for "Mass Properties calculation details"
    Parameters:
      surface_id = the surface's identifier
    Returns:
      list of moments and error bounds - see help topic
      None on error
    """
    return __AreaMomentsHelper(surface_id, False)


def SurfaceWeights(object_id):
    """Returns list of weight values assigned to the control points of a surface.
    The number of weights returned will be equal to the number of control points
    in the U and V directions.
    Parameters:
      object_id = the surface's identifier
    Returns:
      list of weights
      None on error
    """
    surface = rhutil.coercesurface(object_id, True)
    ns = surface.ToNurbsSurface()
    if ns is None: return scriptcontext.errorhandler()
    rc = []
    for u in range(ns.Points.CountU):
        for v in range(ns.Points.CountV):
            pt = ns.Points.GetControlPoint(u,v)
            rc.append(pt.Weight)
    return rc


def TrimBrep(object_id, cutter, tolerance=None):
    """Trims a surface using an oriented cutter
    Parameters:
      object_id = surface or polysurface identifier
      cutter = surface, polysurface, or plane performing the trim
      tolerance[opt] = trimming tolerance. If omitted, the document's absolute
        tolerance is used
    Returns:
      identifiers of retained components on success
    """
    brep = rhutil.coercebrep(object_id, True)
    brep_cutter = rhutil.coercebrep(cutter, False)
    if brep_cutter: cutter = brep_cutter
    else: cutter = rhutil.coerceplane(cutter, True)
    if tolerance is None: tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    breps = brep.Trim(cutter, tolerance)
    rhobj = rhutil.coercerhinoobject(object_id)
    if rhobj:
        attr = rhobj.Attributes
        rc = []
        for i in range(len(breps)):
            if i==0:
                scriptcontext.doc.Objects.Replace(rhobj.Id, breps[i])
                rc.append(rhobj.Id)
            else:
                rc.append(scriptcontext.doc.Objects.AddBrep(breps[i], attr))
    else:
        rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in breps]
    scriptcontext.doc.Views.Redraw()
    return rc


def TrimSurface( surface_id, direction, interval, delete_input=False):
    """Remove portions of the surface outside of the specified interval
    Parameters:
      surface_id = surface identifier
      direction = 0 or 1 (U or V)
      interval = interval of the surface to keep
      delete_input [opt] = should the input surface be deleted
    Returns:
      new surface identifier on success
    """
    surface = rhutil.coercesurface(surface_id, True)
    u = surface.Domain(0)
    v = surface.Domain(1)
    if direction==0:
        u[0] = interval[0]
        u[1] = interval[1]
    else:
        v[0] = interval[0]
        v[1] = interval[1]
    new_surface = surface.Trim(u,v)
    if new_surface:
        rc = scriptcontext.doc.Objects.AddSurface(new_surface)
        if delete_input: scriptcontext.doc.Objects.Delete(rhutil.coerceguid(surface_id), True)
        scriptcontext.doc.Views.Redraw()
        return rc


def UnrollSurface(surface_id, explode=False, following_geometry=None, absolute_tolerance=None, relative_tolerance=None):
    """Flattens a developable surface or polysurface
    Parameters:
      surface_id = the surface's identifier
      explode[opt] = If True, the resulting surfaces ar not joined
      following_geometry[opt] = List of curves, dots, and points which
        should be unrolled with the surface
    Returns:
      List of unrolled surface ids
      if following_geometry is not None, a tuple where item 1
        is the list of unrolled surface ids and item 2 is the
        list of unrolled following geometry
    """
    brep = rhutil.coercebrep(surface_id, True)
    unroll = Rhino.Geometry.Unroller(brep)
    unroll.ExplodeOutput = explode
    if relative_tolerance is None: relative_tolerance = scriptcontext.doc.ModelRelativeTolerance
    if absolute_tolerance is None: absolute_tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    unroll.AbsoluteTolerance = absolute_tolerance
    unroll.RelativeTolerance = relative_tolerance
    if following_geometry:
        for id in following_geometry:
            geom = rhutil.coercegeometry(id)
            unroll.AddFollowingGeometry(geom)
    breps, curves, points, dots = unroll.PerformUnroll()
    if not breps: return None
    rc = [scriptcontext.doc.Objects.AddBrep(brep) for brep in breps]
    new_following = []
    for curve in curves:
        id = scriptcontext.doc.Objects.AddCurve(curve)
        new_following.append(id)
    for point in points:
        id = scriptcontext.doc.Objects.AddPoint(point)
        new_following.append(id)
    for dot in dots:
        id = scriptcontext.doc.Objects.AddTextDot(dot)
        new_following.append(id)
    scriptcontext.doc.Views.Redraw()
    if following_geometry: return rc, new_following
    return rc

########NEW FILE########
__FILENAME__ = toolbar
import Rhino

def CloseToolbarCollection(name, prompt=False):
    """Closes a currently open toolbar collection
    Parameters:
      name = name of a currently open toolbar collection
      prompt[opt] = if True, user will be prompted to save the collection file
        if it has been modified prior to closing
    Returns:
      True or False indicating success or failure
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile: return tbfile.Close(prompt)
    return False


def HideToolbar(name, toolbar_group):
    """Hides a previously visible toolbar group in an open toolbar collection
    Parameters:
      name = name of a currently open toolbar file
      toolbar_group = name of a toolbar group to hide
    Returns:
      True or False indicating success or failure
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        group = tbfile.GetGroup(toolbar_group)
        if group:
            group.Visible = False
            return True
    return False


def IsToolbar(name, toolbar, group=False):
    """Verifies a toolbar (or toolbar group) exists in an open collection file
    Parameters:
      name = name of a currently open toolbar file
      toolbar = name of a toolbar group
      group[opt] = if toolbar parameter is refering to a toolbar group
    Returns:
      True or False indicating success or failure
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        if group: return tbfile.GetGroup(toolbar) != None
        return tbfile.GetToolbar(toolbar) != None
    return False


def IsToolbarCollection(file):
    """Verifies that a toolbar collection is open
    Parameters:
      file = full path to a toolbar collection file
    Returns:
      Rhino-assigned name of the toolbar collection if successful
      None if not successful
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByPath(file)
    if tbfile: return tbfile.Name


def IsToolbarDocked(name, toolbar_group):
    """Verifies that a toolbar group in an open toolbar collection is visible
    Parameters:
      name = name of a currently open toolbar file
      toolbar_group = name of a toolbar group
    Returns:
      True or False indicating success or failure
      None on error
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        group = tbfile.GetGroup(toolbar_group)
        if group: return group.IsDocked


def IsToolbarVisible(name, toolbar_group):
    """Verifies that a toolbar group in an open toolbar collection is visible
    Parameters:
      name = name of a currently open toolbar file
      toolbar_group = name of a toolbar group
    Returns:
      True or False indicating success or failure
      None on error
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        group = tbfile.GetGroup(toolbar_group)
        if group: return group.Visible


def OpenToolbarCollection(file):
    """Opens a toolbar collection file
    Parameters:
      file = full path to the collection file
    Returns:
      Rhino-assigned name of the toolbar collection if successful
      None if not successful
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.Open(file)
    if tbfile: return tbfile.Name


def SaveToolbarCollection(name):
    """Saves an open toolbar collection to disk
    Parameters:
      name = name of a currently open toolbar file
    Returns:
      True or False indicating success or failure
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile: return tbfile.Save()
    return False


def SaveToolbarCollectionAs(name, file):
    """Saves an open toolbar collection to a different disk file
    Parameters:
      name = name of a currently open toolbar file
      file = full path to file name to save to
    Returns:
      True or False indicating success or failure
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile: return tbfile.SaveAs(file)
    return False


def ShowToolbar(name, toolbar_group):
    """Shows a previously hidden toolbar group in an open toolbar collection
    Parameters:
      name = name of a currently open toolbar file
      toolbar_group = name of a toolbar group to show
    Returns:
      True or False indicating success or failure
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        group = tbfile.GetGroup(toolbar_group)
        if group:
            group.Visible = True
            return True
    return False


def ToolbarCollectionCount():
    """Returns number of currently open toolbar collections"""
    return Rhino.RhinoApp.ToolbarFiles.Count


def ToolbarCollectionNames():
    """Returns names of all currently open toolbar collections"""
    return [tbfile.Name for tbfile in Rhino.RhinoApp.ToolbarFiles]


def ToolbarCollectionPath(name):
    """Returns full path to a currently open toolbar collection file
    Parameters:
      name = name of currently open toolbar collection
    Returns:
      full path on success, None on error
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile: return tbfile.Path


def ToolbarCount(name, groups=False):
    """Returns the number of toolbars or groups in a currently open toolbar file
    Parameters:
      name = name of currently open toolbar collection
      groups[opt] = If true, return the number of toolbar groups in the file
    Returns:
      number of toolbars on success, None on error
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        if groups: return tbfile.GroupCount
        return tbfile.ToolbarCount


def ToolbarNames(name, groups=False):
    """Returns the names of all toolbars (or toolbar groups) found in a
    currently open toolbar file
    Parameters:
      name = name of currently open toolbar collection
      groups[opt] = If true, return the names of toolbar groups in the file
    Returns:
      names of all toolbars (or toolbar groups) on success, None on error
    """
    tbfile = Rhino.RhinoApp.ToolbarFiles.FindByName(name, True)
    if tbfile:
        rc = []
        if groups:
            for i in range(tbfile.GroupCount): rc.append(tbfile.GetGroup(i).Name)
        else:
            for i in range(tbfile.ToolbarCount): rc.append(tbfile.GetToolbar(i).Name)
        return rc;

########NEW FILE########
__FILENAME__ = transformation
import scriptcontext
import utility as rhutil
import Rhino
import System.Guid, System.Array
import math
import view as rhview


def IsXformIdentity(xform):
    "Verifies a matrix is the identity matrix"
    xform = rhutil.coercexform(xform, True)
    return xform==Rhino.Geometry.Transform.Identity


def IsXformSimilarity(xform):
    """Verifies a matrix is a similarity transformation. A similarity
    transformation can be broken into a sequence of dialations, translations,
    rotations, and reflections
    """
    xform = rhutil.coercexform(xform, True)
    return xform.SimilarityType!=Rhino.Geometry.TransformSimilarityType.NotSimilarity


def IsXformZero(xform):
    "verifies that a matrix is a zero transformation matrix"
    xform = rhutil.coercexform(xform, True)
    for i in range(4):
        for j in range(4):
            if xform[i,j]!=0: return False
    return True


def XformChangeBasis(initial_plane, final_plane):
    "Returns a change of basis transformation matrix or None on error"
    initial_plane = rhutil.coerceplane(initial_plane, True)
    final_plane = rhutil.coerceplane(final_plane, True)
    xform = Rhino.Geometry.Transform.ChangeBasis(initial_plane, final_plane)
    if not xform.IsValid: return scriptcontext.errorhandler()
    return xform


def XformChangeBasis2(x0,y0,z0,x1,y1,z1):
    """Returns a change of basis transformation matrix of None on error
    Parameters:
      x0,y0,z0 = initial basis
      x1,y1,z1 = final basis
    """
    x0 = rhutil.coerce3dvector(x0, True)
    y0 = rhutil.coerce3dvector(y0, True)
    z0 = rhutil.coerce3dvector(z0, True)
    x1 = rhutil.coerce3dvector(x1, True)
    y1 = rhutil.coerce3dvector(y1, True)
    z1 = rhutil.coerce3dvector(z1, True)
    xform = Rhino.Geometry.Transform.ChangeBasis(x0,y0,z0,x1,y1,z1)
    if not xform.IsValid: return scriptcontext.errorhandler()
    return xform


def XformCompare(xform1, xform2):
    """Compares two transformation matrices
    Parameters:
      xform1, xform2 = matrices to compare
    Returns:
      -1 if xform1<xform2
       1 if xform1>xform2
       0 if xform1=xform2
    """
    xform1 = rhutil.coercexform(xform1, True)
    xform2 = rhutil.coercexform(xform2, True)
    return xform1.CompareTo(xform2)


def XformCPlaneToWorld(point, plane):
    """Transform point from construction plane coordinates to world coordinates
    Parameters:
      point = A 3D point in construction plane coordinates.
      plane = The construction plane
    Returns:
      A 3D point in world coordinates
    """
    point = rhutil.coerce3dpoint(point, True)
    plane = rhutil.coerceplane(plane, True)
    return plane.Origin + point.X*plane.XAxis + point.Y*plane.YAxis + point.Z*plane.ZAxis


def XformDeterminant(xform):
    """Returns the determinant of a transformation matrix. If the determinant
    of a transformation matrix is 0, the matrix is said to be singular. Singular
    matrices do not have inverses.
    """
    xform = rhutil.coercexform(xform, True)
    return xform.Determinant


def XformDiagonal(diagonal_value):
    """Returns a diagonal transformation matrix. Diagonal matrices are 3x3 with
    the bottom row [0,0,0,1]
    """
    return Rhino.Geometry.Transform(diagonal_value)


def XformIdentity():
    "returns the identity transformation matrix"
    return Rhino.Geometry.Transform.Identity


def XformInverse(xform):
    """Returns the inverse of a non-singular transformation matrix
    Returns None on error
    """
    xform = rhutil.coercexform(xform, True)
    rc, inverse = xform.TryGetInverse()
    if not rc: return scriptcontext.errorhandler()
    return inverse


def XformMirror(mirror_plane_point, mirror_plane_normal):
    """Creates a mirror transformation matrix
    Parameters:
      mirror_plane_point = point on the mirror plane
      mirror_plane_normal = a 3D vector that is normal to the mirror plane
    Returns:
      mirror Transform
    """
    point = rhutil.coerce3dpoint(mirror_plane_point, True)
    normal = rhutil.coerce3dvector(mirror_plane_normal, True)
    return Rhino.Geometry.Transform.Mirror(point, normal)


def XformMultiply(xform1, xform2):
    """Multiplies two transformation matrices, where result = xform1 * xform2
    Returns:
      result transformation on success
    """
    xform1 = rhutil.coercexform(xform1, True)
    xform2 = rhutil.coercexform(xform2, True)
    return xform1*xform2


def XformPlanarProjection(plane):
    """Returns a transformation matrix that projects to a plane.
    Parameters
      plane = The plane to project to.
    Returns:
      The 4x4 transformation matrix.
    """
    plane = rhutil.coerceplane(plane, True)
    return Rhino.Geometry.Transform.PlanarProjection(plane)


def XformRotation1(initial_plane, final_plane):
    """Returns a rotation transformation that maps initial_plane to final_plane.
    The planes should be right hand orthonormal planes.
    Returns:
      The 4x4 transformation matrix.
      None on error.
    """
    initial_plane = rhutil.coerceplane(initial_plane, True)
    final_plane = rhutil.coerceplane(final_plane, True)
    xform = Rhino.Geometry.Transform.PlaneToPlane(initial_plane, final_plane)
    if not xform.IsValid: return scriptcontext.errorhandler()
    return xform


def XformRotation2(angle_degrees, rotation_axis, center_point):
    """Returns a rotation transformation
    Returns:
      The 4x4 transformation matrix.
      None on error.
    """
    axis = rhutil.coerce3dvector(rotation_axis, True)
    center = rhutil.coerce3dpoint(center_point, True)
    angle_rad = math.radians(angle_degrees)
    xform = Rhino.Geometry.Transform.Rotation(angle_rad, axis, center)
    if not xform.IsValid: return scriptcontext.errorhandler()
    return xform


def XformRotation3( start_direction, end_direction, center_point ):
    """Calculate the minimal transformation that rotates start_direction to
    end_direction while fixing center_point
    Parameters:
      start_direction, end_direction = 3d vectors
      center_point = the rotation center
    Returns:
      The 4x4 transformation matrix.
      None on error.
    """
    start = rhutil.coerce3dvector(start_direction, True)
    end = rhutil.coerce3dvector(end_direction, True)
    center = rhutil.coerce3dpoint(center_point, True)
    xform = Rhino.Geometry.Transform.Rotation(start, end, center)
    if not xform.IsValid: return scriptcontext.errorhandler()
    return xform


def XformRotation4(x0, y0, z0, x1, y1, z1):
    """Returns a rotation transformation.
    Paramters:
      x0,y0,z0 = Vectors defining the initial orthonormal frame
      x1,y1,z1 = Vectors defining the final orthonormal frame
    Returns:
      The 4x4 transformation matrix.
      None on error.
    """
    x0 = rhutil.coerce3dvector(x0, True)
    y0 = rhutil.coerce3dvector(y0, True)
    z0 = rhutil.coerce3dvector(z0, True)
    x1 = rhutil.coerce3dvector(x1, True)
    y1 = rhutil.coerce3dvector(y1, True)
    z1 = rhutil.coerce3dvector(z1, True)
    xform = Rhino.Geometry.Transform.Rotation(x0,y0,z0,x1,y1,z1)
    if not xform.IsValid: return scriptcontext.errorhandler()
    return xform


def XformScale(scale, point=None):
    """Creates a scale transformation
    Parameters:
      scale = single number, list of 3 numbers, Point3d, or Vector3d
      point[opt] = center of scale. If omitted, world origin is used
    Returns:
      The 4x4 transformation matrix on success
      None on error
    """
    factor = rhutil.coerce3dpoint(scale)
    if factor is None:
        if type(scale) is int or type(scale) is float:
            factor = (scale,scale,scale)
        if factor is None: return scriptcontext.errorhandler()
    if point: point = rhutil.coerce3dpoint(point, True)
    else: point = Rhino.Geometry.Point3d.Origin
    plane = Rhino.Geometry.Plane(point, Rhino.Geometry.Vector3d.ZAxis);
    xf = Rhino.Geometry.Transform.Scale(plane, factor[0], factor[1], factor[2])
    return xf


def XformScreenToWorld(point, view=None, screen_coordinates=False):
    """Transforms a point from either client-area coordinates of the specified view
    or screen coordinates to world coordinates. The resulting coordinates are represented
    as a 3-D point
    Parameters:
      point = 2D point
      view[opt] = title or identifier of a view. If omitted, the active view is used
      screen_coordinates[opt] = if False, point is in client-area coordinates. If True,
      point is in screen-area coordinates
    Returns:
      3D point on success
      None on error
    """
    point = rhutil.coerce2dpoint(point, True)
    view = rhview.__viewhelper(view)
    viewport = view.MainViewport
    xform = viewport.GetTransform(Rhino.DocObjects.CoordinateSystem.Screen, Rhino.DocObjects.CoordinateSystem.World)
    point3d = Rhino.Geometry.Point3d(point.X, point.Y, 0)
    if screen_coordinates:
        screen = view.ScreenRectangle
        point3d.X = point.X - screen.Left
        point3d.Y = point.Y - screen.Top
    point3d = xform * point3d
    return point3d


def XformShear(plane, x, y, z):
    """Returns a shear transformation matrix
    Parameters:
      plane = plane[0] is the fixed point
      x,y,z = each axis scale factor
    Returns:
      The 4x4 transformation matrix on success
    """
    plane = rhutil.coerceplane(plane, True)
    x = rhutil.coerce3dvector(x, True)
    y = rhutil.coerce3dvector(y, True)
    z = rhutil.coerce3dvector(z, True)
    return Rhino.Geometry.Transform.Shear(plane,x,y,z)


def XformTranslation(vector):
    "Creates a translation transformation matrix"
    vector = rhutil.coerce3dvector(vector, True)
    return Rhino.Geometry.Transform.Translation(vector)


def XformWorldToCPlane(point, plane):
    """Transforms a point from world coordinates to construction plane coordinates.
    Parameters:
      point = A 3D point in world coordinates.
      plane = The construction plane
    Returns:
      A 3D point in construction plane coordinates
    """
    point = rhutil.coerce3dpoint(point, True)
    plane = rhutil.coerceplane(plane, True)
    v = point - plane.Origin;
    return Rhino.Geometry.Point3d(v*plane.XAxis, v*plane.YAxis, v*plane.ZAxis)


def XformWorldToScreen(point, view=None, screen_coordinates=False):
    """Transforms a point from world coordinates to either client-area coordinates of
    the specified view or screen coordinates. The resulting coordinates are represented
    as a 2D point
    Parameters:
      point = 3D point in world coordinates
      view[opt] = title or identifier of a view. If omitted, the active view is used
      screen_coordinates[opt] = if False, the function returns the results as
        client-area coordinates. If True, the result is in screen-area coordinates
    Returns:
      2D point on success
      None on error
    """
    point = rhutil.coerce3dpoint(point, True)
    view = rhview.__viewhelper(view)
    viewport = view.MainViewport
    xform = viewport.GetTransform(Rhino.DocObjects.CoordinateSystem.World, Rhino.DocObjects.CoordinateSystem.Screen)
    point = xform * point
    point = Rhino.Geometry.Point2d(point.X, point.Y)
    if screen_coordinates:
        screen = view.ScreenRectangle
        point.X = point.X + screen.Left
        point.Y = point.Y + screen.Top
    return point


def XformZero():
    "Returns a zero transformation matrix"
    return Rhino.Geometry.Transform()
########NEW FILE########
__FILENAME__ = userdata
import scriptcontext
import utility as rhutil

def DeleteDocumentData(section=None, entry=None):
    """Removes user data strings from the current document
    Parameters:
      section = section name. If omitted, all sections and their corresponding
        entries are removed
      entry = entry name. If omitted, all entries for section are removed
    Returns:
      True or False indicating success or failure
    """
    return scriptcontext.doc.Strings.Delete(section, entry)


def DocumentDataCount():
    "Returns the number of user data strings in the current document"
    return scriptcontext.doc.Strings.Count


def GetDocumentData(section=None, entry=None):
    """Returns a user data item from the current document
    Parameters:
      section[opt] = section name. If omitted, all section names are returned
      entry[opt] = entry name. If omitted, all entry names for section are returned
    Returns:
      list of all section names if section name is omitted
      list of all entry names for a section if entry is omitted
      value of the entry if both section and entry are specified
    """
    if section is None:
        rc = scriptcontext.doc.Strings.GetSectionNames()
        if rc: return list(rc)
        return []
    if entry is None:
        rc = scriptcontext.doc.Strings.GetEntryNames(section)
        if rc: return list(rc)
        return []
    return scriptcontext.doc.Strings.GetValue(section, entry)


def GetDocumentUserText(key=None):
    """Returns user text stored in the document
    Parameters:
      key[opt] = key to use for retrieving user text. If empty, all keys are returned
    """
    if key: return scriptcontext.doc.Strings.GetValue(key)
    return [scriptcontext.doc.Strings.GetKey(i) for i in range(scriptcontext.doc.Strings.Count)]


def GetUserText(object_id, key=None, attached_to_geometry=False):
    """Returns user text stored on an object.
    Parameters:
      object_id = the object's identifies
      key[opt] = the key name. If omitted all key names for an object are returned
      attached_to_geometry[opt] = location on the object to retrieve the user text
    Returns:
      if key is specified, the associated value if successful
      if key is not specified, a list of key names if successful
    """
    obj = rhutil.coercerhinoobject(object_id, True, True)
    source = None
    if attached_to_geometry: source = obj.Geometry
    else: source = obj.Attributes
    rc = None
    if key: return source.GetUserString(key)
    userstrings = source.GetUserStrings()
    return [userstrings.GetKey(i) for i in range(userstrings.Count)]


def IsDocumentData():
    """Verifies the current document contains user data
    Returns:
      True or False indicating the presence of Script user data
    """
    return scriptcontext.doc.Strings.Count>0


def IsUserText(object_id):
    """Verifies that an object contains user text
    Returns:
      0 = no user text
      1 = attribute user text
      2 = geometry user text
      3 = both attribute and geometry user text
    """
    obj = rhutil.coercerhinoobject(object_id, True, True)
    rc = 0
    if obj.Attributes.UserStringCount: rc = rc|1
    if obj.Geometry.UserStringCount: rc = rc|2
    return rc


def SetDocumentData(section, entry, value):
    """Adds or sets a user data string to the current document
    Parameters:
      section = the section name
      entry = the entry name
      value  = the string value
    Returns:
      The previous value
    """
    return scriptcontext.doc.Strings.SetString(section, entry, value)


def SetDocumentUserText(key, value=None):
    """Sets or removes user text stored in the document
    Parameters:
      key = key name to set
      value[opt] = The string value to set. If omitted the key/value pair
        specified by key will be deleted
    Returns:
      True or False indicating success
    """
    if value: scriptcontext.doc.Strings.SetString(key,value)
    else: scriptcontext.doc.Strings.Delete(key)
    return True


def SetUserText(object_id, key, value=None, attach_to_geometry=False):
    """Sets or removes user text stored on an object.
    Parameters:
      object_id = the object's identifier
      key = the key name to set
      value[opt] = the string value to set. If omitted, the key/value pair
          specified by key will be deleted
      attach_to_geometry[opt] = location on the object to store the user text
    Returns:
      True or False indicating success or failure 
    """
    obj = rhutil.coercerhinoobject(object_id, True, True)
    if type(key) is not str: key = str(key)
    if value and type(value) is not str: value = str(value)
    if attach_to_geometry: return obj.Geometry.SetUserString(key, value)
    return obj.Attributes.SetUserString(key, value)

########NEW FILE########
__FILENAME__ = userinterface
import Rhino
import utility as rhutil
import scriptcontext
import System.Drawing.Color
import System.Enum
import System.Array
import System.Windows.Forms
import math
from view import __viewhelper


def BrowseForFolder(folder=None, message=None, title=None):
    """Display browse-for-folder dialog allowing the user to select a folder
    Parameters:
      folder[opt] = a default folder
      message[opt] = a prompt or message
      title[opt] = a dialog box title
    Returns:
      selected folder
      None on error
    """
    dlg = System.Windows.Forms.FolderBrowserDialog()
    if folder:
        if not isinstance(folder, str): folder = str(folder)
        dlg.SelectedPath = folder
    if message:
        if not isinstance(message, str): message = str(message)
        dlg.Description = message
    if dlg.ShowDialog()==System.Windows.Forms.DialogResult.OK:
        return dlg.SelectedPath


def CheckListBox(items, message=None, title=None):
    """Displays a list of items in a checkable-style list dialog box
    Parameters:
      items = a list of tuples containing a string and a boolean check state
      message[opt] = a prompt or message
      title[opt] = a dialog box title
    Returns:
      A list of tuples containing the input string in items along with their
      new boolean check value
      None on error      
    """
    checkstates = [item[1] for item in items]
    itemstrs = [str(item[0]) for item in items]
    newcheckstates = Rhino.UI.Dialogs.ShowCheckListBox(title, message, itemstrs, checkstates)
    if newcheckstates:
        rc = zip(itemstrs, newcheckstates)
        return rc
    return scriptcontext.errorhandler()


def ComboListBox(items, message=None, title=None):
    """Displays a list of items in a combo-style list box dialog.
    Parameters:
      items = a list of string
      message[opt] = a prompt of message
      title[opt] = a dialog box title
    Returns:
      The selected item if successful
      None if not successful or on error
    """
    return Rhino.UI.Dialogs.ShowComboListBox(title, message, items)


def EditBox(default_string=None, message=None, title=None):
    """Display dialog box prompting the user to enter a string value. The
    string value may span multiple lines
    """
    rc, text = Rhino.UI.Dialogs.ShowEditBox(title, message, default_string, True)
    return text

def GetAngle(point=None, reference_point=None, default_angle_degrees=0, message=None):
    """Pause for user input of an angle
    Parameters:
      point(opt) = starting, or base point
      reference_point(opt) = if specified, the reference angle is calculated
        from it and the base point
      default_angle_degrees(opt) = a default angle value specified
      message(opt) = a prompt to display
    Returns:
      angle in degree if successful, None on error
    """
    point = rhutil.coerce3dpoint(point)
    if not point: point = Rhino.Geometry.Point3d.Unset
    reference_point = rhutil.coerce3dpoint(reference_point)
    if not reference_point: reference_point = Rhino.Geometry.Point3d.Unset
    default_angle = math.radians(default_angle_degrees)
    rc, angle = Rhino.Input.RhinoGet.GetAngle(message, point, reference_point, default_angle)
    if rc==Rhino.Commands.Result.Success: return math.degrees(angle)


def GetBoolean(message, items, defaults):
    """Pauses for user input of one or more boolean values. Boolean values are
    displayed as click-able command line option toggles
    Parameters:
      message = a prompt
      items = list or tuple of options. Each option is a tuple of three strings
        element 1 = description of the boolean value. Must only consist of letters
          and numbers. (no characters like space, period, or dash
        element 2 = string identifying the false value
        element 3 = string identifying the true value
      defaults = list of boolean values used as default or starting values
    Returns:
      a list of values that represent the boolean values if successful
      None on error
    """
    go = Rhino.Input.Custom.GetOption()
    go.AcceptNothing(True)
    go.SetCommandPrompt( message )
    if type(defaults) is list or type(defaults) is tuple: pass
    else: defaults = [defaults]
    # special case for single list. Wrap items into a list
    if len(items)==3 and len(defaults)==1: items = [items]
    count = len(items)
    if count<1 or count!=len(defaults): return scriptcontext.errorhandler()
    toggles = []
    for i in range(count):
        initial = defaults[i]
        item = items[i]
        offVal = item[1]
        t = Rhino.Input.Custom.OptionToggle( initial, item[1], item[2] )
        toggles.append(t)
        go.AddOptionToggle(item[0], t)
    while True:
        getrc = go.Get()
        if getrc==Rhino.Input.GetResult.Option: continue
        if getrc!=Rhino.Input.GetResult.Nothing: return None
        break
    return [t.CurrentValue for t in toggles]


def GetBox(mode=0, base_point=None, prompt1=None, prompt2=None, prompt3=None):
    """Pauses for user input of a box
    Parameters:
      mode[opt] = The box selection mode.
         0 = All modes
         1 = Corner. The base rectangle is created by picking two corner points
         2 = 3-Point. The base rectangle is created by picking three points
         3 = Vertical. The base vertical rectangle is created by picking three points.
         4 = Center. The base rectangle is created by picking a center point and a corner point
      base_point[opt] = optional 3D base point
      prompt1, prompt2, prompt3 [opt] = optional prompts to set
    Returns:
      list of eight Point3d that define the corners of the box on success
      None is not successful, or on error
    """
    base_point = rhutil.coerce3dpoint(base_point)
    if base_point is None: base_point = Rhino.Geometry.Point3d.Unset
    rc, box = Rhino.Input.RhinoGet.GetBox(mode, base_point, prompt1, prompt2, prompt3)
    if rc==Rhino.Commands.Result.Success: return tuple(box.GetCorners())


def GetColor(color=[0,0,0]):
    """Displays the Rhino color picker dialog allowing the user to select an RGB color
    Parameters:
      color [opt] = a default RGB value. If omitted, the default color is black
    Returns:
      RGB tuple of three numbers on success
      None on error
    """
    color = rhutil.coercecolor(color)
    if color is None: color = System.Drawing.Color.Black
    rc, color = Rhino.UI.Dialogs.ShowColorDialog(color)
    if rc: return color.R, color.G, color.B
    return scriptcontext.errorhandler()


def GetEdgeCurves(message=None, min_count=1, max_count=0, select=False):
    """Prompts the user to pick one or more surface or polysurface edge curves
    Parameters:
      message [optional] = A prompt or message.
      min_count [optional] = minimum number of edges to select.
      max_count [optional] = maximum number of edges to select.
      select [optional] = Select the duplicated edge curves.
    Returns:
      List of (curve id, parent id, selection point)
      None if not successful
    """
    if min_count<0 or (max_count>0 and min_count>max_count): return
    if not message: message = "Select Edges"
    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt(message)
    go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
    go.GeometryAttributeFilter = Rhino.Input.Custom.GeometryAttributeFilter.EdgeCurve
    go.EnablePreSelect(False, True)
    rc = go.GetMultiple(min_count, max_count)
    if rc!=Rhino.Input.GetResult.Object: return
    rc = []
    for i in range(go.ObjectCount):
        edge = go.Object(i).Edge()
        if not edge: continue
        edge = edge.Duplicate()
        curve_id = scriptcontext.doc.Objects.AddCurve(edge)
        parent_id = go.Object(i).ObjectId
        pt = go.Object(i).SelectionPoint()
        rc.append( (curve_id, parent_id, pt) )
    if select:
        for item in rc:
            rhobj = scriptcontext.doc.Objects.Find(item[0])
            rhobj.Select(True)
        scriptcontext.doc.Views.Redraw()
    return rc        


def GetInteger(message=None, number=None, minimum=None, maximum=None):
    """Pauses for user input of a whole number.
    Parameters:
      message [optional] = A prompt or message.
      number [optional] = A default whole number value.
      minimum [optional] = A minimum allowable value.
      maximum [optional] = A maximum allowable value.
    Returns:
       The whole number input by the user if successful.
       None if not successful, or on error
    """
    gi = Rhino.Input.Custom.GetInteger()
    if message: gi.SetCommandPrompt(message)
    if number is not None: gi.SetDefaultInteger(number)
    if minimum is not None: gi.SetLowerLimit(minimum, False)
    if maximum is not None: gi.SetUpperLimit(maximum, False)
    if gi.Get()!=Rhino.Input.GetResult.Number: return scriptcontext.errorhandler()
    rc = gi.Number()
    gi.Dispose()
    return rc


def GetLayer(title="Select Layer", layer=None, show_new_button=False, show_set_current=False):
    """Displays dialog box prompting the user to select a layer
    Parameters:
      title[opt] = dialog box title
      layer[opt] = name of a layer to preselect. If omitted, the current layer will be preselected
      show_new_button, show_set_current[opt] = Optional buttons to show on the dialog
    Returns:
      name of selected layer if successful
      None on error
    """
    layer_index = scriptcontext.doc.Layers.CurrentLayerIndex
    if layer:
        index = scriptcontext.doc.Layers.Find(layer, True)
        if index!=-1: layer_index = index
    rc = Rhino.UI.Dialogs.ShowSelectLayerDialog(layer_index, title, show_new_button, show_set_current, True)
    if rc[0]!=System.Windows.Forms.DialogResult.OK: return None
    layer = scriptcontext.doc.Layers[rc[1]]
    return layer.FullPath


def GetLine(mode=0, point=None, message1=None, message2=None, message3=None):
    """Prompts the user to pick points that define a line
    Parameters:
      mode[opt] = line definition mode. See help file for details
      point[opt] = optional starting point
      message1, message2, message3 = optional prompts
    Returns:
      Tuple of two points on success
      None on error
    """
    gl = Rhino.Input.Custom.GetLine()
    if mode==0: gl.EnableAllVariations(True)
    else: gl.GetLineMode = System.Enum.ToObject( Rhino.Input.Custom.GetLineMode, mode-1 )
    if point:
        point = rhutil.coerce3dpoint(point)
        gl.SetFirstPoint(point)
    if message1: gl.FirstPointPrompt = message1
    if message2: gl.MidPointPrompt = message2
    if message3: gl.SecondPointPromp = message3
    rc, line = gl.Get()
    if rc==Rhino.Commands.Result.Success: return line.From, line.To


def GetMeshFaces(object_id, message="", min_count=1, max_count=0):
    """Prompts the user to pick one or more mesh faces
    Parameters:
      object_id = the mesh object's identifier
      message[opt] = a prompt of message
      min_count[opt] = the minimum number of faces to select
      max_count[opt] = the maximum number of faces to select. If 0, the user must
        press enter to finish selection. If -1, selection stops as soon as there
        are at least min_count faces selected.
    Returns:
      list of mesh face indices on success
      None on error
    """
    scriptcontext.doc.Objects.UnselectAll()
    scriptcontext.doc.Views.Redraw()
    object_id = rhutil.coerceguid(object_id, True)
    def FilterById( rhino_object, geometry, component_index ):
        return object_id == rhino_object.Id
    go = Rhino.Input.Custom.GetObject()
    go.SetCustomGeometryFilter(FilterById)
    if message: go.SetCommandPrompt(message)
    go.GeometryFilter = Rhino.DocObjects.ObjectType.MeshFace
    go.AcceptNothing(True)
    if go.GetMultiple(min_count,max_count)!=Rhino.Input.GetResult.Object: return None
    objrefs = go.Objects()
    rc = [item.GeometryComponentIndex.Index for item in objrefs]
    go.Dispose()
    return rc


def GetMeshVertices(object_id, message="", min_count=1, max_count=0):
    """Prompts the user to pick one or more mesh vertices
    Parameters:
      object_id = the mesh object's identifier
      message[opt] = a prompt of message
      min_count[opt] = the minimum number of vertices to select
      max_count[opt] = the maximum number of vertices to select. If 0, the user must
        press enter to finish selection. If -1, selection stops as soon as there
        are at least min_count vertices selected.
    Returns:
      list of mesh vertex indices on success
      None on error
    """
    scriptcontext.doc.Objects.UnselectAll()
    scriptcontext.doc.Views.Redraw()
    object_id = rhutil.coerceguid(object_id, True)
    class CustomGetObject(Rhino.Input.Custom.GetObject):
        def CustomGeometryFilter( self, rhino_object, geometry, component_index ):
            return object_id == rhino_object.Id
    go = CustomGetObject()
    if message: go.SetCommandPrompt(message)
    go.GeometryFilter = Rhino.DocObjects.ObjectType.MeshVertex
    go.AcceptNothing(True)
    if go.GetMultiple(min_count,max_count)!=Rhino.Input.GetResult.Object: return None
    objrefs = go.Objects()
    rc = [item.GeometryComponentIndex.Index for item in objrefs]
    go.Dispose()
    return rc


def GetPoint(message=None, base_point=None, distance=None, in_plane=False):
    """Pauses for user input of a point.
    Parameters:
      message [opt] = A prompt or message.
      base_point [opt] = list of 3 numbers or Point3d identifying a starting, or base point
      distance  [opt] = constraining distance. If distance is specified, basePoint must also
                        be sepcified.
      in_plane [opt] = constrains the point selections to the active construction plane.
    Returns:
      point on success
      None if no point picked or user canceled
    """
    gp = Rhino.Input.Custom.GetPoint()
    if message: gp.SetCommandPrompt(message)
    base_point = rhutil.coerce3dpoint(base_point)
    if base_point:
        gp.DrawLineFromPoint(base_point,True)
        gp.EnableDrawLineFromPoint(True)
        if distance: gp.ConstrainDistanceFromBasePoint(distance)
    if in_plane: gp.ConstrainToConstructionPlane(True)
    gp.Get()
    if gp.CommandResult()!=Rhino.Commands.Result.Success:
        return scriptcontext.errorhandler()
    pt = gp.Point()
    gp.Dispose()
    return pt


def GetPointOnCurve(curve_id, message=None):
    """Pauses for user input of a point constrainted to a curve object
    Parameters:
      curve_id = identifier of the curve to get a point on
      message [opt] = a prompt of message
    Returns:
      3d point if successful
      None on error
    """
    curve = rhutil.coercecurve(curve_id, -1, True)
    gp = Rhino.Input.Custom.GetPoint()
    if message: gp.SetCommandPrompt(message)
    gp.Constrain(curve, False)
    gp.Get()
    if gp.CommandResult()!=Rhino.Commands.Result.Success:
        return scriptcontext.errorhandler()
    pt = gp.Point()
    gp.Dispose()
    return pt


def GetPointOnMesh(mesh_id, message=None):
    """Pauses for user input of a point constrained to a mesh object
    Parameters:
      mesh_id = identifier of the mesh to get a point on
      message [opt] = a prompt or message
    Returns:
      3d point if successful
      None on error
    """
    mesh_id = rhutil.coerceguid(mesh_id, True)
    if not message: message = "Point"
    cmdrc, point = Rhino.Input.RhinoGet.GetPointOnMesh(mesh_id, message, False)
    if cmdrc==Rhino.Commands.Result.Success: return point


def GetPointOnSurface(surface_id, message=None):
    """Pauses for user input of a point constrained to a surface or polysurface
    object
    Parameters:
      surface_id = identifier of the surface to get a point on
      message [opt] = a prompt or message
    Returns:
      3d point if successful
      None on error
    """
    surfOrBrep = rhutil.coercesurface(surface_id)
    if not surfOrBrep:
        surfOrBrep = rhutil.coercebrep(surface_id, True)
    gp = Rhino.Input.Custom.GetPoint()
    if message: gp.SetCommandPrompt(message)
    if isinstance(surfOrBrep,Rhino.Geometry.Surface):
        gp.Constrain(surfOrBrep,False)
    else:
        gp.Constrain(surfOrBrep, -1, -1, False)
    gp.Get()
    if gp.CommandResult()!=Rhino.Commands.Result.Success:
        return scriptcontext.errorhandler()
    pt = gp.Point()
    gp.Dispose()
    return pt


def GetPoints(draw_lines=False, in_plane=False, message1=None, message2=None, max_points=None, base_point=None):
    """Pauses for user input of one or more points
    Parameters:
      draw_lines [opt] = Draw lines between points
      in_plane[opt] = Constrain point selection to the active construction plane
      message1[opt] = A prompt or message for the first point
      message2[opt] = A prompt or message for the next points
      max_points[opt] = maximum number of points to pick. If not specified, an
                        unlimited number of points can be picked.
      base_point[opt] = a starting or base point
    Returns:
      list of 3d points if successful
      None if not successful or on error
    """
    gp = Rhino.Input.Custom.GetPoint()
    if message1: gp.SetCommandPrompt(message1)
    gp.EnableDrawLineFromPoint( draw_lines )
    if in_plane:
        gp.ConstrainToConstructionPlane(True)
        plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
        gp.Constrain(plane, False)
    getres = gp.Get()
    if gp.CommandResult()!=Rhino.Commands.Result.Success: return None
    prevPoint = gp.Point()
    rc = [prevPoint]
    if max_points is None or max_points>1:
        current_point = 1
        if message2: gp.SetCommandPrompt(message2)
        def GetPointDynamicDrawFunc( sender, args ):
            if len(rc)>1:
                c = Rhino.ApplicationSettings.AppearanceSettings.FeedbackColor
                args.Display.DrawPolyline(rc, c)
        if draw_lines: gp.DynamicDraw += GetPointDynamicDrawFunc
        while True:
            if max_points and current_point>=max_points: break
            if draw_lines: gp.DrawLineFromPoint(prevPoint, True)
            gp.SetBasePoint(prevPoint, True)
            current_point += 1
            getres = gp.Get()
            if getres==Rhino.Input.GetResult.Cancel: break
            if gp.CommandResult()!=Rhino.Commands.Result.Success: return None
            prevPoint = gp.Point()
            rc.append(prevPoint)
    return rc


def GetReal(message="Number", number=None, minimum=None, maximum=None):
    """Pauses for user input of a number.
    Parameters:
      message [optional] = A prompt or message.
      number [optional] = A default number value.
      minimum [optional] = A minimum allowable value.
      maximum [optional] = A maximum allowable value.
    Returns:
       The number input by the user if successful.
       None if not successful, or on error
    """
    gn = Rhino.Input.Custom.GetNumber()
    if message: gn.SetCommandPrompt(message)
    if number is not None: gn.SetDefaultNumber(number)
    if minimum is not None: gn.SetLowerLimit(minimum, False)
    if maximum is not None: gn.SetUpperLimit(maximum, False)
    if gn.Get()!=Rhino.Input.GetResult.Number: return None
    rc = gn.Number()
    gn.Dispose()
    return rc


def GetRectangle(mode=0, base_point=None, prompt1=None, prompt2=None, prompt3=None):
    """Pauses for user input of a rectangle
    Parameters:
      mode[opt] = The rectangle selection mode. The modes are as follows
          0 = All modes
          1 = Corner - a rectangle is created by picking two corner points
          2 = 3Point - a rectangle is created by picking three points
          3 = Vertical - a vertical rectangle is created by picking three points
          4 = Center - a rectangle is created by picking a center point and a corner point
      base_point[opt] = a 3d base point
      prompt1, prompt2, prompt3 = optional prompts
    Returns:
      a tuple of four 3d points that define the corners of the rectangle
      None on error
    """
    mode = System.Enum.ToObject( Rhino.Input.GetBoxMode, mode )
    base_point = rhutil.coerce3dpoint(base_point)
    if( base_point==None ): base_point = Rhino.Geometry.Point3d.Unset
    prompts = ["", "", ""]
    if prompt1: prompts[0] = prompt1
    if prompt2: prompts[1] = prompt2
    if prompt3: prompts[2] = prompt3
    rc, corners = Rhino.Input.RhinoGet.GetRectangle(mode, base_point, prompts)
    if rc==Rhino.Commands.Result.Success: return corners
    return None


def GetString(message=None, defaultString=None, strings=None):
    """Pauses for user input of a string value
    Parameters:
      message [opt]: a prompt or message
      defaultString [opt]: a default value
      strings [opt]: list of strings to be displayed as a click-able command options.
        Note, strings cannot begin with a numeric character
    """
    gs = Rhino.Input.Custom.GetString()
    gs.AcceptNothing(True)
    if message: gs.SetCommandPrompt(message)
    if defaultString: gs.SetDefaultString(defaultString)
    if strings:
        for s in strings: gs.AddOption(s)
    result = gs.Get()
    if result==Rhino.Input.GetResult.Cancel: return None
    if( result == Rhino.Input.GetResult.Option ):
        return gs.Option().EnglishName
    return gs.StringResult()


def ListBox(items, message=None, title=None, default=None):
    """Display a list of items in a list box dialog.
    Parameters:
      items = a list
      message [opt] = a prompt of message
      title [opt] = a dialog box title
      default [opt] = selected item in the list
    Returns:
      The selected item if successful
      None if not successful or on error
    """
    return Rhino.UI.Dialogs.ShowListBox(title, message, items, default)


def MessageBox(message, buttons=0, title=""):
    """Displays a message box. A message box contains a message and
    title, plus any combination of predefined icons and push buttons.
    Parameters:
      message = A prompt or message.
      buttons[opt] = buttons and icon to display. Can be a combination of the
        following flags. If omitted, an OK button and no icon is displayed
        0      Display OK button only.
        1      Display OK and Cancel buttons.
        2      Display Abort, Retry, and Ignore buttons.
        3      Display Yes, No, and Cancel buttons.
        4      Display Yes and No buttons.
        5      Display Retry and Cancel buttons.
        16     Display Critical Message icon.
        32     Display Warning Query icon.
        48     Display Warning Message icon.
        64     Display Information Message icon.
        0      First button is the default.
        256    Second button is the default.
        512    Third button is the default.
        768    Fourth button is the default.
        0      Application modal. The user must respond to the message box
               before continuing work in the current application.
        4096   System modal. The user must respond to the message box
               before continuing work in any application.
      title[opt] = the dialog box title
    Returns:
      A number indicating which button was clicked:
        1      OK button was clicked.
        2      Cancel button was clicked.
        3      Abort button was clicked.
        4      Retry button was clicked.
        5      Ignore button was clicked.
        6      Yes button was clicked.
        7      No button was clicked.
    """
    buttontype = buttons & 0x00000007 #111 in binary
    btn = System.Windows.Forms.MessageBoxButtons.OK
    if buttontype==1: btn = System.Windows.Forms.MessageBoxButtons.OKCancel
    elif buttontype==2: btn = System.Windows.Forms.MessageBoxButtons.AbortRetryIgnore
    elif buttontype==3: btn = System.Windows.Forms.MessageBoxButtons.YesNoCancel
    elif buttontype==4: btn = System.Windows.Forms.MessageBoxButtons.YesNo
    elif buttontype==5: btn = System.Windows.Forms.MessageBoxButtons.RetryCancel
    
    icontype = buttons & 0x00000070
    icon = System.Windows.Forms.MessageBoxIcon.None
    if icontype==16: icon = System.Windows.Forms.MessageBoxIcon.Exclamation
    elif icontype==32: icon = System.Windows.Forms.MessageBoxIcon.Question
    elif icontype==48: icon = System.Windows.Forms.MessageBoxIcon.Warning
    elif icontype==64: icon = System.Windows.Forms.MessageBoxIcon.Information
    
    defbtntype = buttons & 0x00000300
    defbtn = System.Windows.Forms.MessageBoxDefaultButton.Button1
    if defbtntype==256:
        defbtn = System.Windows.Forms.MessageBoxDefaultButton.Button2
    elif defbtntype==512:
        defbtn = System.Windows.Forms.MessageBoxDefaultButton.Button3
    if not isinstance(message, str): message = str(message)
    dlg_result = Rhino.UI.Dialogs.ShowMessageBox(message, title, btn, icon, defbtn)
    if dlg_result==System.Windows.Forms.DialogResult.OK:     return 1
    if dlg_result==System.Windows.Forms.DialogResult.Cancel: return 2
    if dlg_result==System.Windows.Forms.DialogResult.Abort:  return 3
    if dlg_result==System.Windows.Forms.DialogResult.Retry:  return 4
    if dlg_result==System.Windows.Forms.DialogResult.Ignore: return 5
    if dlg_result==System.Windows.Forms.DialogResult.Yes:    return 6
    if dlg_result==System.Windows.Forms.DialogResult.No:     return 7


def PropertyListBox(items, values, message=None, title=None):
    """Displays list of items and their values in a property-style list box dialog
    Parameters:
      items, values = list of string items and their corresponding values
      message [opt] = a prompt or message
      title [opt] = a dialog box title
    Returns:
      a list of new values on success
      None on error
    """
    values = [str(v) for v in values]
    return Rhino.UI.Dialogs.ShowPropertyListBox(title, message, items, values)


def OpenFileName(title=None, filter=None, folder=None, filename=None, extension=None):
    """Displays file open dialog box allowing the user to enter a file name.
    Note, this function does not open the file.
    Parameters:
      title[opt] = A dialog box title.
      filter[opt] = A filter string. The filter must be in the following form:
        "Description1|Filter1|Description2|Filter2||", where "||" terminates filter string.
        If omitted, the filter (*.*) is used.
      folder[opt] = A default folder.
      filename[opt] = a default file name
      extension[opt] = a default file extension
    Returns:
      the file name is successful
      None if not successful, or on error
    """
    fd = Rhino.UI.OpenFileDialog()
    if title: fd.Title = title
    if filter: fd.Filter = filter
    if folder: fd.InitialDirectory = folder
    if filename: fd.FileName = filename
    if extension: fd.DefaultExt = extension
    if fd.ShowDialog()==System.Windows.Forms.DialogResult.OK: return fd.FileName


def OpenFileNames(title=None, filter=None, folder=None, filename=None, extension=None):
    """Displays file open dialog box allowing the user to select one or more file names.
    Note, this function does not open the file.
    Parameters:
      title[opt] = A dialog box title.
      filter[opt] = A filter string. The filter must be in the following form:
        "Description1|Filter1|Description2|Filter2||", where "||" terminates filter string.
        If omitted, the filter (*.*) is used.
      folder[opt] = A default folder.
      filename[opt] = a default file name
      extension[opt] = a default file extension
    Returns:
      list of selected file names
    """
    fd = Rhino.UI.OpenFileDialog()
    if title: fd.Title = title
    if filter: fd.Filter = filter
    if folder: fd.InitialDirectory = folder
    if filename: fd.FileName = filename
    if extension: fd.DefaultExt = extension
    fd.MultiSelect = True
    rc = []
    if fd.ShowDialog()==System.Windows.Forms.DialogResult.OK: rc = fd.FileNames
    return rc


def PopupMenu(items, modes=None, point=None, view=None):
    """Displays a user defined, context-style popup menu. The popup menu can appear
    almost anywhere, and it can be dismissed by either clicking the left or right
    mouse buttons
    Parameters:
      items = list of strings representing the menu items. An empty string or None
        will create a separator
      modes[opt] = List of numbers identifying the display modes. If omitted, all
        modes are enabled.
          0 = menu item is enabled
          1 = menu item is disabled
          2 = menu item is checked
          3 = menu item is disabled and checked
      point[opt] = a 3D point where the menu item will appear. If omitted, the menu
        will appear at the current cursor position
      view[opt] = if point is specified, the view in which the point is computed.
        If omitted, the active view is used
    Returns:
      index of the menu item picked or -1 if no menu item was picked
    """
    screen_point = System.Windows.Forms.Cursor.Position
    if point:
        point = rhutil.coerce3dpoint(point)
        view = __viewhelper(view)
        viewport = view.ActiveViewport
        point2d = viewport.WorldToClient(point)
        screen_point = viewport.ClientToScreen(point2d)
    return Rhino.UI.Dialogs.ShowContextMenu(items, screen_point, modes);


def RealBox(message="", default_number=None, title="", minimum=None, maximum=None):
    """Display a dialog box prompting the user to enter a number
    Returns:
      number on success
      None on error
    """
    if default_number is None: default_number = Rhino.RhinoMath.UnsetValue
    if minimum is None: minimum = Rhino.RhinoMath.UnsetValue
    if maximum is None: maximum = Rhino.RhinoMath.UnsetValue
    rc, number = Rhino.UI.Dialogs.ShowNumberBox(title, message, default_number, minimum, maximum)
    if rc==System.Windows.Forms.DialogResult.OK: return number


def SaveFileName(title=None, filter=None, folder=None, filename=None, extension=None):
    """Display a save dialog box allowing the user to enter a file name.
    Note, this function does not save the file.
    Parameters:
      title[opt] = A dialog box title.
      filter[opt] = A filter string. The filter must be in the following form:
        "Description1|Filter1|Description2|Filter2||", where "||" terminates filter string.
        If omitted, the filter (*.*) is used.
      folder[opt] = A default folder.
      filename[opt] = a default file name
      extension[opt] = a default file extension
    Returns:
      the file name is successful
      None if not successful, or on error
    """
    fd = Rhino.UI.SaveFileDialog()
    if title: fd.Title = title
    if filter: fd.Filter = filter
    if folder: fd.InitialDirectory = folder
    if filename: fd.FileName = filename
    if extension: fd.DefaultExt = extension
    if fd.ShowDialog()==System.Windows.Forms.DialogResult.OK: return fd.FileName


def StringBox(message=None, default_value=None, title=None):
    "Display a dialog box prompting the user to enter a string value."
    rc, text = Rhino.UI.Dialogs.ShowEditBox(title, message, default_value, False)
    if rc!=System.Windows.Forms.DialogResult.OK: return None
    return text

########NEW FILE########
__FILENAME__ = utility
import Rhino
import System.Drawing.Color, System.Array, System.Guid
import time
import System.Windows.Forms.Clipboard
import scriptcontext
import math
import string


def ContextIsRhino():
    """Return True if the script is being executed in the context of Rhino"""
    return scriptcontext.id == 1


def ContextIsGrasshopper():
    """Return True if the script is being executed in a grasshopper component"""
    return scriptcontext.id == 2


def Angle(point1, point2, plane=True):
    """Measures the angle between two points
    Parameters:
      point1, point2: the input points
      plane[opt] = Boolean or Plane
        If True, angle calculation is based on the world coordinate system.
        If False, angle calculation is based on the active construction plane
        If a plane is provided, angle calculation is with respect to this plane
    Returns:
      tuple containing the following elements if successful
        element 0 = the X,Y angle in degrees
        element 1 = the elevation
        element 2 = delta in the X direction
        element 3 = delta in the Y direction
        element 4 = delta in the Z direction
      None if not successful
    """
    pt1 = coerce3dpoint(point1)
    if pt1 is None:
        pt1 = coercerhinoobject(point1)
        if isinstance(pt1, Rhino.DocObjects.PointObject): pt1 = pt1.Geometry.Location
        else: pt1=None
    pt2 = coerce3dpoint(point2)
    if pt2 is None:
        pt2 = coercerhinoobject(point2)
        if isinstance(pt2, Rhino.DocObjects.PointObject): pt2 = pt2.Geometry.Location
        else: pt2=None
    point1 = pt1
    point2 = pt2
    if point1 is None or point2 is None: return scriptcontext.errorhandler()
    vector = point2 - point1
    x = vector.X
    y = vector.Y
    z = vector.Z
    if plane!=True:
        plane = coerceplane(plane)
        if plane is None:
            plane = scriptcontext.doc.Views.ActiveView.ActiveViewport.ConstructionPlane()
        vfrom = point1 - plane.Origin
        vto = point2 - plane.Origin
        x = vto * plane.XAxis - vfrom * plane.XAxis
        y = vto * plane.YAxis - vfrom * plane.YAxis
        z = vto * plane.ZAxis - vfrom * plane.ZAxis
    h = math.sqrt( x * x + y * y)
    angle_xy = math.degrees( math.atan2( y, x ) )
    elevation = math.degrees( math.atan2( z, h ) )
    return angle_xy, elevation, x, y, z


def Angle2(line1, line2):
    """Measures the angle between two lines"""
    line1 = coerceline(line1, True)
    line2 = coerceline(line2, True)
    vec0 = line1.To - line1.From
    vec1 = line2.To - line2.From
    if not vec0.Unitize() or not vec1.Unitize(): return scriptcontext.errorhandler()
    dot = vec0 * vec1
    dot = clamp(-1,1,dot)
    angle = math.acos(dot)
    reflex_angle = 2.0*math.pi - angle
    angle = math.degrees(angle)
    reflex_angle = math.degrees(reflex_angle)
    return angle, reflex_angle


def ClipboardText(text=None):
    """Returns or sets a text string to the Windows clipboard
    Parameters:
      text: [opt] text to set
    Returns:
      if text is not specified, the current text in the clipboard
      if text is specified, the previous text in the clipboard
      None if not successful
    """
    rc = None
    if System.Windows.Forms.Clipboard.ContainsText():
        rc = System.Windows.Forms.Clipboard.GetText()
    if text:
        if not isinstance(text, str): text = str(text)
        System.Windows.Forms.Clipboard.SetText(text)
    return rc


def ColorAdjustLuma(rgb, luma, scale=False):
    """Change the luminance of a red-green-blue value. Hue and saturation are
    not affected
    Parameters:
      rgb = initial rgb value
      luma = The luminance in units of 0.1 percent of the total range. A
          value of luma = 50 corresponds to 5 percent of the maximum luminance
      scale[opt] = if True, luma specifies how much to increment or decrement the
          current luminance. If False, luma specified the absolute luminance.
    Returns:
      modified rgb value if successful
    """
    rgb = coercecolor(rgb, True)
    hsl = Rhino.Display.ColorHSL(rgb)
    luma = luma / 1000.0
    if scale: luma = hsl.L + luma
    hsl.L = luma
    return hsl.ToArgbColor()


def ColorBlueValue(rgb):
    "Retrieves intensity value for the blue component of an RGB color"
    return coercecolor(rgb, True).B


def ColorGreenValue(rgb):
    "Retrieves intensity value for the green component of an RGB color"
    return coercecolor(rgb, True).G


def ColorHLSToRGB(hls):
    "Converts colors from hue-lumanence-saturation to RGB"
    if len(hls)==3:
        hls = Rhino.Display.ColorHSL(hls[0]/240.0, hls[2]/240.0, hls[1]/240.0)
    elif len(hls)==4:
        hls = Rhino.Display.ColorHSL(hls[3]/240.0, hls[0]/240.0, hls[2]/240.0, hls[1]/240.0)
    return hls.ToArgbColor()


def ColorRedValue(rgb):
    "Retrieves intensity value for the red component of an RGB color"
    return coercecolor(rgb, True).R


def ColorRGBToHLS(rgb):
    "Convert colors from RGB to HLS"
    rgb = coercecolor(rgb, True)
    hsl = Rhino.Display.ColorHSL(rgb)
    return hsl.H, hsl.S, hsl.L


def CullDuplicateNumbers(numbers, tolerance=None):
    count = len(numbers)
    if count < 2: return numbers
    if tolerance is None: tolerance = scriptcontext.doc.ModelAbsoluteTolerance
    numbers = sorted(numbers)
    d = numbers[0]
    index = 1
    for step in range(1,count):
        test_value = numbers[index]
        if math.fabs(d-test_value)<=tolerance:
            numbers.pop(index)
        else:
            d = test_value
            index += 1
    return numbers


def CullDuplicatePoints(points, tolerance=-1):
    """Removes duplicates from a list of 3D points.
    Parameters:
      points = A list of 3D points.
      tolerance [opt] = Minimum distance between points. Points within this
        tolerance will be discarded. If omitted, Rhino's internal zero tolerance
        is used.
    Returns:
      list of 3D points with duplicates removed if successful.
      None if not successful
    """
    points = coerce3dpointlist(points, True)
    if tolerance is None or tolerance < 0:
        tolerance = Rhino.RhinoMath.ZeroTolerance
    return list(Rhino.Geometry.Point3d.CullDuplicates(points, tolerance))


def Distance(point1, point2):
    """Measures distance between two 3D points, or between a 3D point and
    an array of 3D points.
    Parameters:
      point1 = The first 3D point.
      point2 = The second 3D point or list of 3-D points.
    Returns:
      If point2 is a 3D point then the distance if successful.
      If point2 is a list of points, then an list of distances if successful.
      None if not successful
    """
    from_pt = coerce3dpoint(point1, True)
    to_pt = coerce3dpoint(point2)
    if to_pt: return (to_pt - from_pt).Length
    # check if we have a list of points
    to_pt = coerce3dpointlist(point2, True)
    distances = [(point - from_pt).Length for point in to_pt]
    if distances: return distances


def GetSettings(filename, section=None, entry=None):
    """Returns string from a specified section in a initialization file.
    Parameters:
      filename = name of the initialization file
      section[opt] = section containing the entry
      entry[opt] = entry whose associated string is to be returned
    Returns:
      If section is not specified, a list containing all section names
      If entry is not specified, a list containing all entry names for a given section
      If section and entry are specied, a value for entry
      None if not successful
    """
    import ConfigParser
    try:
        cp = ConfigParser.ConfigParser()
        cp.read(filename)
        if not section: return cp.sections()
        section = string.lower(section)
        if not entry: return cp.options(section)
        entry = string.lower(entry)
        return cp.get(section, entry)
    except IOError:
        return scriptcontext.errorhander()
    return scriptcontext.errorhandler()


def Polar(point, angle_degrees, distance, plane=None):
    """Returns 3D point that is a specified angle and distance from a 3D point
    Parameters:
      point = the point to transform
      plane[opt] = plane to base the transformation. If omitted, the world
        x-y plane is used
    Returns:
      resulting point is successful
      None on error
    """
    point = coerce3dpoint(point, True)
    angle = math.radians(angle_degrees)
    if plane: plane = coerceplane(plane)
    else: plane = Rhino.Geometry.Plane.WorldXY
    offset = plane.XAxis
    offset.Unitize()
    offset *= distance
    rc = point+offset
    xform = Rhino.Geometry.Transform.Rotation(angle, plane.ZAxis, point)
    rc.Transform(xform)
    return rc


def SimplifyArray(points):
    rc = []
    for point in points:
        point = coerce3dpoint(point, True)
        rc.append(point.X)
        rc.append(point.Y)
        rc.append(point.Z)
    return rc


def Sleep(milliseconds):
    "Suspends execution of a running script for the specified interval"
    time.sleep( milliseconds / 1000.0 )
    Rhino.RhinoApp.Wait() #keep the message pump alive
    

def SortPointList(points, tolerance=None):
    """Sorts list of points so they will be connected in a "reasonable" polyline order
    Parameters:
      points = the points to sort
      tolerance[opt] = minimum distance between points. Points that fall within this tolerance
        will be discarded. If omitted, Rhino's internal zero tolerance is used.
    Returns:
      a list of sorted 3D points if successful
      None on error
    """
    points = coerce3dpointlist(points, True)
    if tolerance is None: tolerance = Rhino.RhinoMath.ZeroTolerance
    return list(Rhino.Geometry.Point3d.SortAndCullPointList(points, tolerance))


def SortPoints(points, ascending=True, order=0):
    "Sorts an array of 3D points"
    def __cmpXYZ( a, b ):
        rc = cmp(a.X, b.X)
        if rc==0: rc = cmp(a.Y, b.Y)
        if rc==0: rc = cmp(a.Z, b.Z)
        return rc
    def __cmpXZY( a, b ):
        rc = cmp(a.X, b.X)
        if rc==0: rc = cmp(a.Z, b.Z)
        if rc==0: rc = cmp(a.Y, b.Y)
        return rc
    def __cmpYXZ( a, b ):
        rc = cmp(a.Y, b.Y)
        if rc==0: rc = cmp(a.X, b.X)
        if rc==0: rc = cmp(a.Z, b.Z)
        return rc
    def __cmpYZX( a, b ):
        rc = cmp(a.Y, b.Y)
        if rc==0: rc = cmp(a.Z, b.Z)
        if rc==0: rc = cmp(a.X, b.X)
        return rc
    def __cmpZXY( a, b ):
        rc = cmp(a.Z, b.Z)
        if rc==0: rc = cmp(a.X, b.X)
        if rc==0: rc = cmp(a.Y, b.Y)
        return rc
    def __cmpZYX( a, b ):
        rc = cmp(a.Z, b.Z)
        if rc==0: rc = cmp(a.Y, b.Y)
        if rc==0: rc = cmp(a.X, b.X)
        return rc
    sortfunc = (__cmpXYZ, __cmpXZY, __cmpYXZ, __cmpYZX, __cmpZXY, __cmpZYX)[order]
    return sorted(points, sortfunc, None, not ascending)


def Str2Pt(point):
    "convert a formatted string value into a 3D point value"
    return coerce3dpoint(point, True)


def clamp(lowvalue, highvalue, value):
    if lowvalue>=highvalue: raise Exception("lowvalue must be less than highvalue")
    if value<lowvalue: return lowvalue
    if value>highvalue: return highvalue
    return value


def fxrange(start, stop, step):
    "float version of the xrange function"
    if step==0: raise ValueError("step must not equal 0")
    x = start
    if start<stop:
        if step<0: raise ValueError("step must be greater than 0")
        while x<=stop:
            yield x
            x+=step
    else:
        if step>0: raise ValueError("step must be less than 0")
        while x>=stop:
            yield x
            x+=step


def frange(start, stop, step):
    "float version of the range function"
    return [x for x in fxrange(start, stop, step)]


def coerce3dpoint(point, raise_on_error=False):
    "Convert input into a Rhino.Geometry.Point3d if possible."
    if type(point) is Rhino.Geometry.Point3d: return point
    if hasattr(point, "__len__") and len(point)==3 and hasattr(point, "__getitem__"):
        try:
            return Rhino.Geometry.Point3d(float(point[0]), float(point[1]), float(point[2]))
        except:
            if raise_on_error: raise
    if type(point) is Rhino.Geometry.Vector3d or type(point) is Rhino.Geometry.Point3f or type(point) is Rhino.Geometry.Vector3f:
        return Rhino.Geometry.Point3d(point.X, point.Y, point.Z)
    if type(point) is str:
        point = point.split(',')
        return Rhino.Geometry.Point3d( float(point[0]), float(point[1]), float(point[2]) )
    if type(point) is System.Guid:
        rhobj = coercerhinoobject(point, raise_on_error)
        if rhobj:
            geom = rhobj.Geometry
            if isinstance(geom, Rhino.Geometry.Point): return geom.Location
    if raise_on_error: raise ValueError("Could not convert %s to a Point3d" % point)


def coerce2dpoint(point, raise_on_error=False):
    "Convert input into a Rhino.Geometry.Point2d if possible."
    if type(point) is Rhino.Geometry.Point2d: return point
    if type(point) is list or type(point) is tuple:
        length = len(point)
        if length==2 and type(point[0]) is not list and type(point[0]) is not Rhino.Geometry.Point2d:
            return Rhino.Geometry.Point2d(point[0], point[1])
    if type(point) is Rhino.Geometry.Vector3d or type(point) is Rhino.Geometry.Point3d:
        return Rhino.Geometry.Point2d(point.X, point.Y)
    if type(point) is str:
        point = point.split(',')
        return Rhino.Geometry.Point2d( float(point[0]), float(point[1]) )
    if raise_on_error: raise ValueError("Could not convert %s to a Point2d" % point)


def coerce3dvector(vector, raise_on_error=False):
    "Convert input into a Rhino.Geometry.Vector3d if possible."
    if type(vector) is Rhino.Geometry.Vector3d: return vector
    point = coerce3dpoint(vector, False)
    if point: return Rhino.Geometry.Vector3d(point.X, point.Y, point.Z)
    if raise_on_error: raise ValueError("Could not convert %s to a Vector3d" % vector)


def coerce3dpointlist(points, raise_on_error=False):
    if isinstance(points, System.Array[Rhino.Geometry.Point3d]):
        return list(points)
    if isinstance(points, Rhino.Collections.Point3dList): return list(points)
    if type(points) is list or type(points) is tuple:
        count = len(points)
        if count>10 and type(points[0]) is Rhino.Geometry.Point3d: return points
        if count>0 and (coerce3dpoint(points[0]) is not None):
            return [coerce3dpoint(points[i], raise_on_error) for i in xrange(count)]
        elif count>2 and type(points[0]) is not list:
            point_count = count/3
            rc = []
            for i in xrange(point_count):
                pt = Rhino.Geometry.Point3d(points[i*3], points[i*3+1], points[i*3+2])
                rc.append(pt)
            return rc
    if raise_on_error: raise ValueError("Could not convert %s to a list of points" % points)


def coerce2dpointlist(points):
    if points is None or isinstance(points, System.Array[Rhino.Geometry.Point2d]):
        return points
    if type(points) is list or type(points) is tuple:
        count = len(points)
        if count>0 and type(points[0]) is Rhino.Geometry.Point2d:
            rc = System.Array.CreateInstance(Rhino.Geometry.Point2d, count)
            for i in xrange(count): rc[i] = points[i]
            return rc
        elif count>1 and type(points[0]) is not list:
            point_count = count/2
            rc = System.Array.CreateInstance(Rhino.Geometry.Point2d,point_count)
            for i in xrange(point_count):
                rc[i] = Rhino.Geometry.Point2d(points[i*2], points[i*2+1])
            return rc
        elif count>0 and type(points[0]) is list:
            point_count = count
            rc = System.Array.CreateInstance(Rhino.Geometry.Point2d,point_count)
            for i in xrange(point_count):
                pt = points[i]
                rc[i] = Rhino.Geometry.Point2d(pt[0],pt[1])
            return rc
        return None
    return None


def coerceplane(plane, raise_on_bad_input=False):
    "Convert input into a Rhino.Geometry.Plane if possible."
    if type(plane) is Rhino.Geometry.Plane: return plane
    if type(plane) is list or type(plane) is tuple:
        length = len(plane)
        if length==3 and type(plane[0]) is not list:
            rc = Rhino.Geometry.Plane.WorldXY
            rc.Origin = Rhino.Geometry.Point3d(plane[0],plane[1],plane[2])
            return rc
        if length==9 and type(plane[0]) is not list:
            origin = Rhino.Geometry.Point3d(plane[0],plane[1],plane[2])
            xpoint = Rhino.Geometry.Point3d(plane[3],plane[4],plane[5])
            ypoint = Rhino.Geometry.Point3d(plane[6],plane[7],plane[8])
            rc     = Rhino.Geometry.Plane(origin, xpoint, ypoint)
            return rc
        if length==3 and (type(plane[0]) is list or type(plane[0]) is tuple):
            origin = Rhino.Geometry.Point3d(plane[0][0],plane[0][1],plane[0][2])
            xpoint = Rhino.Geometry.Point3d(plane[1][0],plane[1][1],plane[1][2])
            ypoint = Rhino.Geometry.Point3d(plane[2][0],plane[2][1],plane[2][2])
            rc     = Rhino.Geometry.Plane(origin, xpoint, ypoint)
            return rc
    if raise_on_bad_input: raise TypeError("%s can not be converted to a Plane"%plane)


def coercexform(xform, raise_on_bad_input=False):
    "Convert input into a Rhino.Transform if possible."
    t = type(xform)
    if t is Rhino.Geometry.Transform: return xform
    if( (t is list or t is tuple) and len(xform)==4 and len(xform[0])==4):
        xf = Rhino.Geometry.Transform()
        for i in range(4):
            for j in range(4):
                xf[i,j] = xform[i][j]
        return xf
    if raise_on_bad_input: raise TypeError("%s can not be converted to a Transform"%xform)


def coerceguid(id, raise_exception=False):
    if type(id) is System.Guid: return id
    if type(id) is str and len(id)>30:
        try:
            id = System.Guid(id)
            return id
        except:
            pass
    if (type(id) is list or type(id) is tuple) and len(id)==1:
        return coerceguid(id[0], raise_exception)
    if type(id) is Rhino.DocObjects.ObjRef: return id.ObjectId
    if isinstance(id,Rhino.DocObjects.RhinoObject): return id.Id
    if raise_exception: raise TypeError("Parameter must be a Guid or string representing a Guid")


def coerceguidlist(ids):
    if ids is None: return None
    rc = []
    if( type(ids) is list or type(ids) is tuple ): pass
    else: ids = [ids]
    for id in ids:
        id = coerceguid(id)
        if id: rc.append(id)
    if rc: return rc


def coerceboundingbox(bbox, raise_on_bad_input=False):
    if type(bbox) is Rhino.Geometry.BoundingBox: return bbox
    points = coerce3dpointlist(bbox)
    if points: return Rhino.Geometry.BoundingBox(points)
    if raise_on_bad_input: raise TypeError("%s can not be converted to a BoundingBox"%bbox)


def coercecolor(c, raise_if_bad_input=False):
    if type(c) is System.Drawing.Color: return c
    if type(c) is list or type(c) is tuple:
        if len(c)==3: return System.Drawing.Color.FromArgb(c[0], c[1], c[2])
        elif len(c)==4: return System.Drawing.Color.FromArgb(c[0], c[1], c[2], c[3])
    if type(c)==type(1): return System.Drawing.Color.FromArgb(c)
    if raise_if_bad_input: raise TypeError("%s can not be converted to a Color"%c)


def coerceline(line, raise_if_bad_input=False):
    if type(line) is Rhino.Geometry.Line: return line
    guid = coerceguid(line, False)
    if guid: line = scriptcontext.doc.Objects.Find(guid).Geometry
    if isinstance(line, Rhino.Geometry.Curve) and line.IsLinear:
        return Rhino.Geometry.Line(line.PointAtStart, line.PointAtEnd)
    points = coerce3dpointlist(line, raise_if_bad_input)
    if points and len(points)>1: return Rhino.Geometry.Line(points[0], points[1])
    if raise_if_bad_input: raise TypeError("%s can not be converted to a Line"%line)


def coercegeometry(id, raise_if_missing=False):
    "attempt to get GeometryBase class from given input"
    if isinstance(id, Rhino.Geometry.GeometryBase): return id
    if type(id) is Rhino.DocObjects.ObjRef: return id.Geometry()
    if isinstance(id, Rhino.DocObjects.RhinoObject): return id.Geometry
    id = coerceguid(id, raise_if_missing)
    if id:
        rhobj = scriptcontext.doc.Objects.Find(id)
        if rhobj: return rhobj.Geometry
    if raise_if_missing: raise ValueError("unable to convert %s into geometry"%id)


def coercebrep(id, raise_if_missing=False):
    "attempt to get polysurface geometry from the document with a given id"
    geom = coercegeometry(id, False)
    if isinstance(geom, Rhino.Geometry.Brep): return geom
    if isinstance(geom, Rhino.Geometry.Extrusion): return geom.ToBrep(True)
    if raise_if_missing: raise ValueError("unable to convert %s into Brep geometry"%id)


def coercecurve(id, segment_index=-1, raise_if_missing=False):
    "attempt to get curve geometry from the document with a given id"
    if isinstance(id, Rhino.Geometry.Curve): return id
    if type(id) is Rhino.DocObjects.ObjRef: return id.Curve()
    id = coerceguid(id, True)
    crvObj = scriptcontext.doc.Objects.Find(id)
    if crvObj:
        curve = crvObj.Geometry
        if curve and segment_index>=0 and type(curve) is Rhino.Geometry.PolyCurve:
            curve = curve.SegmentCurve(segment_index)
        if isinstance(curve, Rhino.Geometry.Curve): return curve
    if raise_if_missing: raise ValueError("unable to convert %s into Curve geometry"%id)


def coercesurface(object_id, raise_if_missing=False):
    "attempt to get surface geometry from the document with a given id"
    if isinstance(object_id, Rhino.Geometry.Surface): return object_id
    if type(object_id) is Rhino.DocObjects.ObjRef: return object_id.Face()
    object_id = coerceguid(object_id, True)
    srfObj = scriptcontext.doc.Objects.Find(object_id)
    if srfObj:
        srf = srfObj.Geometry
        if isinstance(srf, Rhino.Geometry.Surface): return srf
        #single face breps are considered surfaces in the context of scripts
        if isinstance(srf, Rhino.Geometry.Brep) and srf.Faces.Count==1:
            return srf.Faces[0]
    if raise_if_missing: raise ValueError("unable to convert %s into Surface geometry"%object_id)


def coercemesh(object_id, raise_if_missing=False):
    "attempt to get mesh geometry from the document with a given id"
    if type(object_id) is Rhino.DocObjects.ObjRef: return object_id.Mesh()
    if isinstance(object_id, Rhino.Geometry.Mesh): return object_id
    object_id = coerceguid(object_id, raise_if_missing)
    if object_id: 
        meshObj = scriptcontext.doc.Objects.Find(object_id)
        if meshObj:
            mesh = meshObj.Geometry
            if isinstance(mesh, Rhino.Geometry.Mesh): return mesh
    if raise_if_missing: raise ValueError("unable to convert %s into Mesh geometry"%object_id)


def coercerhinoobject(object_id, raise_if_bad_input=False, raise_if_missing=False):
    "attempt to get RhinoObject from the document with a given id"
    if isinstance(object_id, Rhino.DocObjects.RhinoObject): return object_id
    object_id = coerceguid(object_id, raise_if_bad_input)
    if object_id is None: return None
    rc = scriptcontext.doc.Objects.Find(object_id)
    if not rc and raise_if_missing: raise ValueError("%s does not exist in ObjectTable" % object_id)
    return rc

########NEW FILE########
__FILENAME__ = view
import scriptcontext
import utility as rhutil
import Rhino
import System.Enum
import math

def __viewhelper(view):
    if view is None: return scriptcontext.doc.Views.ActiveView
    allviews = scriptcontext.doc.Views.GetViewList(True, True)
    view_id = rhutil.coerceguid(view, False)
    for item in allviews:
        if view_id:
            if item.MainViewport.Id == view_id: return item
        elif item.MainViewport.Name == view:
            return item
    raise ValueError("unable to coerce %s into a view"%view)


def AddDetail(layout_id, corner1, corner2, title=None, projection=1):
    """Add new detail view to an existing layout view
    Parameters:
      layout_id = identifier of an existing layout
      corner1, corner2 = 2d corners of the detail in the layout's unit system
      title[opt] = title of the new detail
      projection[opt] = type of initial view projection for the detail
          1 = parallel top view
          2 = parallel bottom view
          3 = parallel left view
          4 = parallel right view
          5 = parallel front view
          6 = parallel back view
          7 = perspective view
    Returns:
      identifier of the newly created detial on success
      None on error
    """
    layout_id = rhutil.coerceguid(layout_id, True)
    corner1 = rhutil.coerce2dpoint(corner1, True)
    corner2 = rhutil.coerce2dpoint(corner2, True)
    if projection<1 or projection>7: raise ValueError("projection must be a value between 1-7")
    layout = scriptcontext.doc.Views.Find(layout_id)
    if not layout: raise ValueError("no layout found for given layout_id")
    projection = System.Enum.ToObject(Rhino.Display.DefinedViewportProjection, projection)
    detail = layout.AddDetailView(title, corner1, corner2, projection)
    if not detail: return scriptcontext.errorhandler()
    scriptcontext.doc.Views.Redraw()
    return detail.Id


def AddLayout(title=None, size=None):
    """Adds a new page layout view
    Parameters:
      title[opt] = title of new layout
      size[opt] = width and height of paper for the new layout
    Returns:
      id of new layout
    """
    page = None
    if size is None: page = scriptcontext.doc.Views.AddPageView(title)
    else: page = scriptcontext.doc.Views.AddPageView(title, size[0], size[1])
    if page: return page.MainViewport.Id


def AddNamedCPlane(cplane_name, view=None):
    """Adds new named construction plane to the document
    Parameters:
      cplane_name: the name of the new named construction plane
      view:[opt] string or Guid. Title or identifier of the view from which to save
               the construction plane. If omitted, the current active view is used.
    Returns:
      name of the newly created construction plane if successful
      None on error
    """
    view = __viewhelper(view)
    if not cplane_name: raise ValueError("cplane_name is empty")
    plane = view.MainViewport.ConstructionPlane()
    index = scriptcontext.doc.NamedConstructionPlanes.Add(cplane_name, plane)
    if index<0: return scriptcontext.errorhandler()
    return cplane_name


def AddNamedView(name, view=None):
    """Adds a new named view to the document
    Parameters:
      name: the name of the new named view
      view: [opt] the title or identifier of the view to save. If omitted, the current
            active view is saved
    Returns:
      name fo the newly created named view if successful
      None on error
    """
    view = __viewhelper(view)
    if not name: raise ValueError("name is empty")
    viewportId = view.MainViewport.Id
    index = scriptcontext.doc.NamedViews.Add(name, viewportId)
    if index<0: return scriptcontext.errorhandler()
    return name


def CurrentDetail(layout, detail=None, return_name=True):
    """Returns or changes the current detail view in a page layout view
    Parameters:
      layout = title or identifier of an existing page layout view
      detail[opt] = title or identifier the the detail view to set
      return_name[opt] = return title if True, else return identifier
    Returns:
      if detail is not specified, the title or id of the current detail view
      if detail is specified, the title or id of the previous detail view
      None on error
    """
    layout_id = rhutil.coerceguid(layout)
    page = None
    if layout_id is None: page = scriptcontext.doc.Views.Find(layout, False)
    else: page = scriptcontext.doc.Views.Find(layout_id)
    if page is None: return scriptcontext.errorhandler()
    rc = None
    active_viewport = page.ActiveViewport
    if return_name: rc = active_viewport.Name
    else: rc = active_viewport.Id
    if detail:
        id = rhutil.coerceguid(detail)
        if( (id and id==page.MainViewport.Id) or (id is None and detail==page.MainViewport.Name) ):
            page.SetPageAsActive()
        else:
            if id: page.SetActiveDetail(id)
            else: page.SetActiveDetail(detail, False)
    scriptcontext.doc.Views.Redraw()
    return rc


def CurrentView(view=None, return_name=True):
    """Returns or sets the currently active view
    Parameters:
      view:[opt] String or Guid. Title or id of the view to set current.
        If omitted, only the title or identifier of the current view is returned
      return_name:[opt] If True, then the name, or title, of the view is returned.
        If False, then the identifier of the view is returned
    Returns:
      if the title is not specified, the title or id of the current view
      if the title is specified, the title or id of the previous current view
      None on error
    """
    rc = None
    if return_name: rc = scriptcontext.doc.Views.ActiveView.MainViewport.Name
    else: rc = scriptcontext.doc.Views.ActiveView.MainViewport.Id
    if view:
        id = rhutil.coerceguid(view)
        rhview = None
        if id: rhview = scriptcontext.doc.Views.Find(id)
        else: rhview = scriptcontext.doc.Views.Find(view, False)
        if rhview is None: return scriptcontext.errorhandler()
        scriptcontext.doc.Views.ActiveView = rhview
    return rc


def DeleteNamedCPlane(name):
    """Removes a named construction plane from the document
    Parameters:
      name: name of the construction plane to remove
    Returns:
      True or False indicating success or failure
    """
    return scriptcontext.doc.NamedConstructionPlanes.Delete(name)


def DeleteNamedView(name):
    """Removes a named view from the document
    Parameters:
      name: name of the named view to remove
    Returns:
      True or False indicating success or failure
    """
    return scriptcontext.doc.NamedViews.Delete(name)


def DetailLock(detail_id, lock=None):
    """Returns or modifies the projection locked state of a detail
    Parameters:
      detail_id = identifier of a detail object
      lock[opt] = the new lock state
    Returns:
      if lock==None, the current detail projection locked state
      if lock is True or False, the previous detail projection locked state
      None on error
    """
    detail_id = rhutil.coerceguid(detail_id, True)
    detail = scriptcontext.doc.Objects.Find(detail_id)
    if not detail: return scriptcontext.errorhandler()
    rc = detail.DetailGeometry.IsProjectionLocked
    if lock is not None and lock!=rc:
        detail.DetailGeometry.IsProjectionLocked = lock
        detail.CommitChanges()
    return rc


def DetailScale(detail_id, model_length=None, page_length=None):
    """Returns or modifies the scale of a detail object
    Parameters:
      detail_id = identifier of a detail object
      model_length[opt] = a length in the current model units
      page_length[opt] = a length in the current page units
    Returns:
      current page to model scale ratio if model_length and page_length are both None
      previous page to model scale ratio if model_length and page_length are values
      None on error
    """
    detail_id = rhutil.coerceguid(detail_id, True)
    detail = scriptcontext.doc.Objects.Find(detail_id)
    if detail is None: return scriptcontext.errorhandler()
    rc = detail.DetailGeometry.PageToModelRatio
    if model_length or page_length:
        if model_length is None or page_length is None:
            return scriptcontext.errorhandler()
        model_units = scriptcontext.doc.ModelUnitSystem
        page_units = scriptcontext.doc.PageUnitSystem
        if detail.DetailGeometry.SetScale(model_length, model_units, page_length, page_units):
            detail.CommitChanges()
            scriptcontext.doc.Views.Redraw()
    return rc


def IsDetail(layout, detail):
    """Verifies that a detail view exists on a page layout view
    Parameters:
      layout: title or identifier of an existing page layout
      detail: title or identifier of an existing detail view
    Returns:
      True if detail is a detail view
      False if detail is not a detail view
      None on error
    """
    layout_id = rhutil.coerceguid(layout)
    views = scriptcontext.doc.Views.GetViewList(False, True)
    found_layout = None
    for view in views:
        if layout_id:
            if view.MainViewport.Id==layout_id:
                found_layout = view
                break
        elif view.MainViewport.Name==layout:
            found_layout = view
            break
    # if we couldn't find a layout, this is an error
    if found_layout is None: return scriptcontext.errorhandler()
    detail_id = rhutil.coerceguid(detail)
    details = view.GetDetailViews()
    if not details: return False
    for detail_view in details:
        if detail_id:
            if detail_view.Id==detail_id: return True
        else:
            if detail_view.Name==detail: return True
    return False


def IsLayout(layout):
    """Verifies that a view is a page layout view
    Parameters:
      layout: title or identifier of an existing page layout view
    Returns:
      True if layout is a page layout view
      False is layout is a standard, model view
      None on error
    """
    layout_id = rhutil.coerceguid(layout)
    alllayouts = scriptcontext.doc.Views.GetViewList(False, True)
    for layoutview in alllayouts:
        if layout_id:
            if layoutview.MainViewport.Id==layout_id: return True
        elif layoutview.MainViewport.Name==layout: return True
    allmodelviews = scriptcontext.doc.Views.GetViewList(True, False)
    for modelview in allmodelviews:
        if layout_id:
          if modelview.MainViewport.Id==layout_id: return False
        elif modelview.MainViewport.Name==layout: return False
    return scriptcontext.errorhandler()


def IsView(view):
    """Verifies that the specified view exists
    Parameters:
      view: title or identifier of the view
    Returns:
      True of False indicating success or failure
    """
    view_id = rhutil.coerceguid(view)
    if view_id is None and view is None: return False
    allviews = scriptcontext.doc.Views.GetViewList(True, True)
    for item in allviews:
        if view_id:
            if item.MainViewport.Id==view_id: return True
        elif item.MainViewport.Name==view: return True
    return False


def IsViewCurrent(view):
    """Verifies that the specified view is the current, or active view
    Parameters:
      view: title or identifier of the view
    Returns:
      True of False indicating success or failure
    """
    activeview = scriptcontext.doc.Views.ActiveView
    view_id = rhutil.coerceguid(view)
    if view_id: return view_id==activeview.MainViewport.Id
    return view==activeview.MainViewport.Name


def IsViewMaximized(view=None):
    """Verifies that the specified view is maximized (enlarged so as to fill
    the entire Rhino window)
    Paramters:
      view: [opt] title or identifier of the view. If omitted, the current
            view is used
    Returns:
      True of False
    """
    view = __viewhelper(view)
    return view.Maximized


def IsViewPerspective(view):
    """Verifies that the specified view's projection is set to perspective
    Parameters:
      view: title or identifier of the view
    Returns:
      True of False
    """
    view = __viewhelper(view)
    return view.MainViewport.IsPerspectiveProjection


def IsViewTitleVisible(view=None):
    """Verifies that the specified view's title window is visible
    Paramters:
      view: [opt] The title or identifier of the view. If omitted, the current
            active view is used
    Returns:
      True of False
    """
    view = __viewhelper(view)
    return view.MainViewport.TitleVisible


def IsWallpaper(view):
    "Verifies that the specified view contains a wallpaper image"
    view = __viewhelper(view)
    return len(view.MainViewport.WallpaperFilename)>0


def MaximizeRestoreView(view=None):
    """Toggles a view's maximized/restore window state of the specified view
    Parameters:
      view: [opt] the title or identifier of the view. If omitted, the current
            active view is used
    """
    view = __viewhelper(view)
    view.Maximized = not view.Maximized


def NamedCPlane(name):
    """Returns the plane geometry of the specified named construction plane
    Parameters:
      name: the name of the construction plane
    Returns:
      a plane on success
      None on error
    """
    index = scriptcontext.doc.NamedConstructionPlanes.Find(name)
    if index<0: return scriptcontext.errorhandler()
    return scriptcontext.doc.NamedConstructionPlanes[index].Plane


def NamedCPlanes():
    "Returns the names of all named construction planes in the document"
    count = scriptcontext.doc.NamedConstructionPlanes.Count
    rc = [scriptcontext.doc.NamedConstructionPlanes[i].Name for i in range(count)]
    return rc


def NamedViews():
    "Returns the names of all named views in the document"
    count = scriptcontext.doc.NamedViews.Count
    return [scriptcontext.doc.NamedViews[i].Name for i in range(count)]


def RenameView(old_title, new_title):
    """Changes the title of the specified view
    Parameters:
      old_title: the title or identifier of the view to rename
      new_title: the new title of the view
    Returns:
      the view's previous title if successful
      None on error
    """
    if not old_title or not new_title: return scriptcontext.errorhandler()
    old_id = rhutil.coerceguid(old_title)
    foundview = None
    allviews = scriptcontext.doc.Views.GetViewList(True, True)
    for view in allviews:
        if old_id:
            if view.MainViewport.Id==old_id:
                foundview = view
                break
        elif view.MainViewport.Name==old_title:
            foundview = view
            break
    if foundview is None: return scriptcontext.errorhandler()
    old_title = foundview.MainViewport.Name
    foundview.MainViewport.Name = new_title
    return old_title


def RestoreNamedCPlane(cplane_name, view=None):
    """Restores a named construction plane to the specified view.
    Parameters:
      cplane_name: name of the construction plane to restore
      view: [opt] the title or identifier of the view. If omitted, the current
            active view is used
    Returns:
      name of the restored named construction plane if successful
      None on error
    """
    view = __viewhelper(view)
    index = scriptcontext.doc.NamedConstructionPlanes.Find(cplane_name)
    if index<0: return scriptcontext.errorhandler()
    cplane = scriptcontext.doc.NamedConstructionPlanes[index]
    view.MainViewport.PushConstructionPlane(cplane)
    view.Redraw()
    return cplane_name


def RestoreNamedView(named_view, view=None, restore_bitmap=False):
    """Restores a named view to the specified view
    Parameters:
      named_view: name of the named view to restore
      view:[opt] title or id of the view to restore the named view.
           If omitted, the current active view is used
      restore_bitmap: [opt] restore the named view's background bitmap
    Returns:
      name of the restored view if successful
      None on error
    """
    view = __viewhelper(view)
    index = scriptcontext.doc.NamedViews.FindByName(named_view)
    if index<0: return scriptcontext.errorhandler()
    viewinfo = scriptcontext.doc.NamedViews[index]
    if view.MainViewport.PushViewInfo(viewinfo, restore_bitmap):
        view.Redraw()
        return view.MainViewport.Name
    return scriptcontext.errorhandler()


def RotateCamera(view=None, direction=0, angle=None):
    """Rotates a perspective-projection view's camera. See the RotateCamera
    command in the Rhino help file for more details
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
      direction: [opt] the direction to rotate the camera where 0=right, 1=left,
            2=down, 3=up
      angle: [opt] the angle to rotate. If omitted, the angle of rotation
            is specified by the "Increment in divisions of a circle" parameter
            specified in Options command's View tab
    Returns:
      True or False indicating success or failure
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    if angle is None:
        angle = 2.0*math.pi/Rhino.ApplicationSettings.ViewSettings.RotateCircleIncrement
    else:
        angle = Rhino.RhinoMath.ToRadians( abs(angle) )
    target_distance = (viewport.CameraLocation-viewport.CameraTarget)*viewport.CameraZ
    axis = viewport.CameraY
    if direction==0 or direction==2: angle=-angle
    if direction==0 or direction==1:
        if Rhino.ApplicationSettings.ViewSettings.RotateToView:
            axis = viewport.CameraY
        else:
            axis = Rhino.Geometry.Vector3d.ZAxis
    elif direction==2 or direction==3:
        axis = viewport.CameraX
    else:
        return False
    if Rhino.ApplicationSettings.ViewSettings.RotateReverseKeyboard: angle=-angle
    rot = Rhino.Geometry.Transform.Rotation(angle, axis, Rhino.Geometry.Point3d.Origin)
    camUp = rot * viewport.CameraY
    camDir = -(rot * viewport.CameraZ)
    target = viewport.CameraLocation + target_distance*camDir
    viewport.SetCameraLocations(target, viewport.CameraLocation)
    viewport.CameraUp = camUp
    view.Redraw()
    return True


def RotateView(view=None, direction=0, angle=None):
    """Rotates a view. See RotateView command in Rhino help for more information
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view is used
      direction:[opt] the direction to rotate the view where
            0=right, 1=left, 2=down, 3=up
      angle:[opt] angle to rotate. If omitted, the angle of rotation is specified
            by the "Increment in divisions of a circle" parameter specified in
            Options command's View tab
    Returns:
      True or False indicating success or failure
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    if angle is None:
        angle = 2.0*math.pi/Rhino.ApplicationSettings.ViewSettings.RotateCircleIncrement
    else:
        angle = Rhino.RhinoMath.ToRadians( abs(angle) )
    if Rhino.ApplicationSettings.ViewSettings.RotateReverseKeyboard: angle = -angle
    if direction==0: viewport.KeyboardRotate(True, angle)
    elif direction==1: viewport.KeyboardRotate(True, -angle)
    elif direction==2: viewport.KeyboardRotate(False, -angle)
    elif direction==3: viewport.KeyboardRotate(False, angle)
    else: return False
    view.Redraw()
    return True


def ShowGrid(view=None, show=None):
    """Shows or hides a view's construction plane grid
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view is used
      show:[opt] The grid state to set. If omitted, the current grid display state is returned
    Returns:
      If show is not specified, then the grid display state if successful
      If show is specified, then the previous grid display state if successful
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    rc = viewport.ConstructionGridVisible
    if show is not None and rc!=show:
        viewport.ConstructionGridVisible = show
        view.Redraw()
    return rc


def ShowGridAxes(view=None, show=None):
    """Shows or hides a view's construction plane grid axes.
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view
        is used
      show:[opt] The state to set. If omitted, the current grid axes display
        state is returned
    Returns:
      If show is not specified, then the grid axes display state
      If show is specified, then the previous grid axes display state
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    rc = viewport.ConstructionAxesVisible
    if show is not None and rc!=show:
        viewport.ConstructionAxesVisible = show
        view.Redraw()
    return rc


def ShowViewTitle(view=None, show=True):
    """Shows or hides the title window of a view
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view is used
      show:[opt] The state to set.
    """
    view = __viewhelper(view)
    if view is None: return scriptcontext.errorhandler()
    view.TitleVisible = show


def ShowWorldAxes(view=None, show=None):
    """Shows or hides a view's world axis icon
    Parameters:
      view: [opt] title or id of the view. If omitted, the current active view is used
      show: [opt] The state to set.
    Returns:
      If show is not specified, then the world axes display state
      If show is specified, then the previous world axes display state
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    rc = viewport.WorldAxesVisible
    if show is not None and rc!=show:
        viewport.WorldAxesVisible = show
        view.Redraw()
    return rc


def TiltView(view=None, direction=0, angle=None):
    """Tilts a view by rotating the camera up vector. See the TiltView command in
    the Rhino help file for more details.
      view:[opt] title or id of the view. If omitted, the current active view is used
      direction:[opt] the direction to rotate the view where 0=right, 1=left
      angle:[opt] the angle to rotate. If omitted, the angle of rotation is
        specified by the "Increment in divisions of a circle" parameter specified
        in Options command's View tab
    Returns:
      True or False indicating success or failure
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    if angle is None:
        angle = 2.0*math.pi/Rhino.ApplicationSettings.ViewSettings.RotateCircleIncrement
    else:
        angle = Rhino.RhinoMath.ToRadians( abs(angle) )
    
    if Rhino.ApplicationSettings.ViewSettings.RotateReverseKeyboard: angle = -angle
    axis = viewport.CameraLocation - viewport.CameraTarget
    if direction==0: viewport.Rotate(angle, axis, viewport.CameraLocation)
    elif direction==1: viewport.Rotate(-angle, axis, viewport.CameraLocation)
    else: return False
    view.Redraw()
    return True


def ViewCamera(view=None, camera_location=None):
    """Returns or sets the camera location of the specified view
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view is used
      camera_location: [opt] a 3D point identifying the new camera location.
        If omitted, the current camera location is returned
    Returns:
      If camera_location is not specified, the current camera location
      If camera_location is specified, the previous camera location
      None on error    
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.CameraLocation
    if camera_location is None: return rc
    camera_location = rhutil.coerce3dpoint(camera_location)
    if camera_location is None: return scriptcontext.errorhandler()
    view.ActiveViewport.SetCameraLocation(camera_location, True)
    view.Redraw()
    return rc


def ViewCameraLens(view=None, length=None):
    """Returns or sets the 35mm camera lens length of the specified perspective
    projection view.
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view is used
      length:[opt] the new 35mm camera lens length. If omitted, the previous
        35mm camera lens length is returned
    Returns:
      If lens length is not specified, the current lens length
      If lens length is specified, the previous lens length
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.Camera35mmLensLength
    if not length: return rc
    view.ActiveViewport.Camera35mmLensLength = length
    view.Redraw()
    return rc


def ViewCameraPlane(view=None):
    """Returns the orientation of a view's camera.
    Parameters:
      view:[opt] title or id of the view. If omitted, the current active view is used
    Returns:
      the view's camera plane if successful
      None on error
    """
    view = __viewhelper(view)
    rc, frame = view.ActiveViewport.GetCameraFrame()
    if not rc: return scriptcontext.errorhandler()
    return frame


def ViewCameraTarget(view=None, camera=None, target=None):
    """Returns or sets the camera and target positions of the specified view
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
      camera:[opt] 3d point identifying the new camera location. If camera and
         target are not specified, current camera and target locations are returned
      target:[opt] 3d point identifying the new target location. If camera and
         target are not specified, current camera and target locations are returned
    Returns:
      if both camera and target are not specified, then the 3d points containing
        the current camera and target locations is returned
      if either camera or target are specified, then the 3d points containing the
        previous camera and target locations is returned
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.CameraLocation, view.ActiveViewport.CameraTarget
    if not camera and not target: return rc
    if camera: camera = rhutil.coerce3dpoint(camera, True)
    if target: target = rhutil.coerce3dpoint(target, True)
    if camera and target: view.ActiveViewport.SetCameraLocations(target, camera)
    elif camera is None: view.ActiveViewport.SetCameraTarget(target, True)
    else: view.ActiveViewport.SetCameraLocation(camera, True)
    view.Redraw()
    return rc


def ViewCameraUp(view=None, up_vector=None):
    """Returns or sets the camera up direction of a specified
    Parameters:
      view[opt]: title or id of the view. If omitted, the current active view is used
      up_vector[opt]: 3D vector identifying the new camera up direction
    Returns:
      if up_vector is not specified, then the current camera up direction
      if up_vector is specified, then the previous camera up direction
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.CameraUp
    if up_vector:
        view.ActiveViewport.CameraUp = rhutil.coerce3dvector(up_vector, True)
        view.Redraw()
    return rc


def ViewCPlane(view=None, plane=None):
    """Return or set a view's construction plane
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used.
      plane:[opt] the new construction plane if setting
    Returns:
      If a construction plane is not specified, the current construction plane
      If a construction plane is specified, the previous construction plane
    """
    view = __viewhelper(view)
    cplane = view.ActiveViewport.ConstructionPlane()
    if plane:
        plane = rhutil.coerceplane(plane, True)
        view.ActiveViewport.SetConstructionPlane(plane)
        view.Redraw()
    return cplane

def ViewDisplayMode(view=None, mode=None, return_name=True):
    """Return or set a view display mode
    Paramters:
      view: [opt] Title or id of a view. If omitted, active view is used
      mode: [opt] Name or id of a display mode
      return_name: [opt] If true, return display mode name. If False, display mode id
    Returns:
      If mode is specified, the previous mode
      If mode is not specified, the current mode
    """
    view = __viewhelper(view)
    current = view.ActiveViewport.DisplayMode
    if return_name: rc = current.EnglishName
    else: rc = current.Id
    if mode:
        mode_id = rhutil.coerceguid(mode)
        if mode_id:
            desc = Rhino.Display.DisplayModeDescription.GetDisplayMode(mode_id)
        else:
            desc = Rhino.Display.DisplayModeDescription.FindByName(mode)
        if desc: view.ActiveViewport.DisplayMode = desc
        scriptcontext.doc.Views.Redraw()
    return rc


def ViewDisplayModeId(name):
    """Return id of a display mode given it's name"""
    desc = Rhino.Display.DisplayModeDescription.FindByName(name)
    if desc: return desc.Id


def ViewDisplayModeName(mode_id):
    """Return name of a display mode given it's id"""
    mode_id = rhutil.coerceguid(mode_id, True)
    desc = Rhino.Display.DisplayModeDescription.GetDisplayMode(mode_id)
    if desc: return desc.EnglishName


def ViewDisplayModes(return_names=True):
    """Return list of display modes
    Paramters:
      return_name: [opt] If True, return mode names. If False, return ids
    """
    modes = Rhino.Display.DisplayModeDescription.GetDisplayModes()
    if return_names:
        return [mode.EnglishName for mode in modes]
    return [mode.Id for mode in modes]


def ViewNames(return_names=True, view_type=0):
    """Return the names, titles, or identifiers of all views in the document
    Parameters:
      return_names: [opt] if True then the names of the views are returned.
        If False, then the identifiers of the views are returned
      view_type: [opt] the type of view to return
                       0 = standard model views
                       1 = page layout views
                       2 = both standard and page layout views
    Returns:
      list of the view names or identifiers on success
      None on error
    """
    views = scriptcontext.doc.Views.GetViewList(view_type!=1, view_type>0)
    if views is None: return scriptcontext.errorhandler()
    if return_names: return [view.MainViewport.Name for view in views]
    return [view.MainViewport.Id for view in views]


def ViewNearCorners(view=None):
    """Return 3d corners of a view's near clipping plane rectangle. Useful
    in determining the "real world" size of a parallel-projected view
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
    Returns:
      Four Point3d that define the corners of the rectangle (counter-clockwise order)
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.GetNearRect()
    return rc[0], rc[1], rc[2], rc[3]


def ViewProjection(view=None, mode=None):
    """Return or set a view's projection mode.
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
      mode:[opt] the projection mode (1=parallel, 2=perspective)
    Returns:
      if mode is not specified, the current projection mode for the specified view
      if mode is specified, the previous projection mode for the specified view
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    rc = 2
    if viewport.IsParallelProjection: rc = 1
    if mode is None or mode==rc: return rc
    if mode==1: viewport.ChangeToParallelProjection(True)
    elif mode==2: viewport.ChangeToPerspectiveProjection(True, 50)
    else: return
    view.Redraw()
    return rc

def ViewRadius(view=None, radius=None):
    """Returns or sets the radius of a parallel-projected view. Useful
    when you need an absolute zoom factor for a parallel-projected view
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
      radius:[opt] the view radius
    Returns:
      if radius is not specified, the current view radius for the specified view
      if radius is specified, the previous view radius for the specified view
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    if not viewport.IsParallelProjection: return scriptcontext.errorhandler()
    fr = viewport.GetFrustum()
    frus_right = fr[2]
    frus_top = fr[4]
    old_radius = min(frus_top, frus_right)
    if radius is None: return old_radius
    magnification_factor = radius / old_radius
    d = 1.0 / magnification_factor
    viewport.Magnify(d)
    view.Redraw()
    return old_radius


def ViewSize(view=None):
    """Returns the width and height in pixels of the specified view
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
    Returns:
      tuple of two numbers idenfitying width and height
    """
    view = __viewhelper(view)
    cr = view.ClientRectangle
    return cr.Width, cr.Height


def ViewTarget(view=None, target=None):
    """Returns or sets the target location of the specified view
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
      target:[opt] 3d point identifying the new target location. If omitted,
        the current target location is returned
    Returns:
      is target is not specified, then the current target location
      is target is specified, then the previous target location
      None on error
    """
    view = __viewhelper(view)
    viewport = view.ActiveViewport
    old_target = viewport.CameraTarget
    if target is None: return old_target
    target = rhutil.coerce3dpoint(target)
    if target is None: return scriptcontext.errorhandler()
    viewport.SetCameraTarget(target, True)
    view.Redraw()
    return old_target


def ViewTitle(view_id):
    """Returns the name, or title, of a given view's identifier
    Parameters:
      view_id: String or Guid. The identifier of the view
    Returns:
      name or title of the view on success
      None on error
    """
    view_id = rhutil.coerceguid(view_id)
    if view_id is None: return scriptcontext.errorhandler()
    view = scriptcontext.doc.Views.Find(view_id)
    if view is None: return scriptcontext.errorhandler()
    return view.MainViewport.Name


def Wallpaper(view=None, filename=None):
    """Returns or sets the wallpaper bitmap of the specified view. To remove a
    wallpaper bitmap, pass an empty string ""
    Parameters:
      view[opt] = String or Guid. The identifier of the view. If omitted, the
        active view is used
      filename[opt] = Name of the bitmap file to set as wallpaper
    Returns:
      If filename is not specified, the current wallpaper bitmap filename
      If filename is specified, the previous wallpaper bitmap filename
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.WallpaperFilename
    if filename is not None and filename!=rc:
        view.ActiveViewport.SetWallpaper(filename, False)
        view.Redraw()
    return rc


def WallpaperGrayScale(view=None, grayscale=None):
    """Returns or sets the grayscale display option of the wallpaper bitmap in a
    specified view
    Parameters:
      view[opt] = String or Guid. The identifier of the view. If omitted, the
        active view is used
      grayscale[opt] = Display the wallpaper in gray(True) or color (False)
    Returns:
      If grayscale is not specified, the current grayscale display option
      If grayscale is specified, the previous grayscale display option
    """
    view = __viewhelper(view)
    rc = view.ActiveViewport.WallpaperGrayscale
    if grayscale is not None and grayscale!=rc:
        filename = view.ActiveViewport.WallpaperFilename
        view.ActiveViewport.SetWallpaper(filename, grayscale)
        view.Redraw()
    return rc


def WallpaperHidden(view=None, hidden=None):
    """Returns or sets the visibility of the wallpaper bitmap in a specified view
    Parameters:
      view[opt] = String or Guid. The identifier of the view. If omitted, the
        active view is used
      hidden[opt] = Show or hide the wallpaper
    Returns:
      If hidden is not specified, the current hidden state
      If hidden is specified, the previous hidden state
    """
    view = __viewhelper(view)
    rc = not view.ActiveViewport.WallpaperVisible
    if hidden is not None and hidden!=rc:
        filename = view.ActiveViewport.WallpaperFilename
        gray = view.ActiveViewport.WallpaperGrayscale
        view.ActiveViewport.SetWallpaper(filename, gray, not hidden)
        view.Redraw()
    return rc


def ZoomBoundingBox(bounding_box, view=None, all=False):
    """Zooms to the extents of a specified bounding box in the specified view
    Parameters:
      bounding_box: eight points that define the corners of a bounding box
        or a BoundingBox class instance
      view:[opt] title or id of the view. If omitted, current active view is used
      all:[opt] zoom extents in all views
    """
    bbox = rhutil.coerceboundingbox(bounding_box)
    if bbox:
      if all:
          views = scriptcontext.doc.Views.GetViewList(True, True)
          for view in views: view.ActiveViewport.ZoomBoundingBox(bbox)
      else:
          view = __viewhelper(view)
          view.ActiveViewport.ZoomBoundingBox(bbox)
      scriptcontext.doc.Views.Redraw()


def ZoomExtents(view=None, all=False):
    """Zooms to extents of visible objects in the specified view
    Parameters:
      view:[opt] title or id of the view. If omitted, current active view is used
      all:[opt] zoom extents in all views
    """
    if all:
        views = scriptcontext.doc.Views.GetViewList(True, True)
        for view in views: view.ActiveViewport.ZoomExtents()
    else:
        view = __viewhelper(view)
        view.ActiveViewport.ZoomExtents()
    scriptcontext.doc.Views.Redraw()


def ZoomSelected(view=None, all=False):
    """Zoom to extents of selected objects in a view
    Parameters:
      view: [opt] title or id of the view. If omitted, active view is used
      all: [opt] zoom extents in all views
    """
    if all:
        views = scriptcontext.doc.Views.GetViewList(True, True)
        for view in views: view.ActiveViewport.ZoomExtentsSelected()
    else:
        view = __viewhelper(view)
        view.ActiveViewport.ZoomExtentsSelected()
    scriptcontext.doc.Views.Redraw()

########NEW FILE########
__FILENAME__ = AnnotateCurveForm
# The following sample shows how to creates a custom windows form
# with a textbox that can be used to define the text in a new text dot
from System.Windows.Forms import Form, DialogResult, Label, Button, TextBox
from System.Drawing import Point, Size
import rhinoscript.selection
import rhinoscript.geometry

# Our custom form class
class AnnotateForm(Form):
  # build all of the controls in the constructor
  def __init__(self, curveId):
    offset = 10
    self.Text = "Annotate Curve"
    crvlabel = Label(Text="Curve ID = "+str(curveId), AutoSize=True)
    self.Controls.Add(crvlabel)
    width = crvlabel.Right
    pt = Point(crvlabel.Left,crvlabel.Bottom + offset)
    labelstart = Label(Text="Text at start", AutoSize=True)
    labelstart.Location = pt
    self.Controls.Add(labelstart)
    pt.X = labelstart.Right + offset
    inputstart = TextBox(Text="Start")
    inputstart.Location = pt
    self.Controls.Add(inputstart)
    if( inputstart.Right > width ):
      width = inputstart.Right
    self.m_inputstart = inputstart

    pt.X  = labelstart.Left
    pt.Y  = labelstart.Bottom + offset*3
    buttonApply = Button(Text="Apply", DialogResult=DialogResult.OK)
    buttonApply.Location = pt
    self.Controls.Add(buttonApply)
    pt.X = buttonApply.Right + offset
    buttonCancel = Button(Text="Cancel", DialogResult=DialogResult.Cancel)
    buttonCancel.Location = pt
    self.Controls.Add(buttonCancel)
    if( buttonCancel.Right > width ):
      width = buttonCancel.Right
    self.ClientSize = Size(width, buttonCancel.Bottom)
    self.AcceptButton = buttonApply
    self.CancelButton = buttonCancel
  
  def TextAtStart(self):
    return self.m_inputstart.Text


# prompt the user to select a curve
curveId = rhinoscript.selection.GetObject("Select a curve",rhinoscript.selection.filter.curve)
if( curveId==None ):
  print "no curve selected"
else:
  location = rhinoscript.curve.CurveStartPoint(curveId)
  if( location!=None ):
    form = AnnotateForm(curveId)
    if( form.ShowDialog() == DialogResult.OK ):
      # this block of script is run if the user pressed the apply button
      text = form.TextAtStart()
      if( len(text) > 0 ):
        #create a new text dot at the start of the curve
        rhinoscript.geometry.AddTextDot(text, location)

########NEW FILE########
__FILENAME__ = CustomGetPoint
# A Rhino GetPoint that performs some custom dynamic drawing
import Rhino
import System.Drawing.Color
import scriptcontext

def CustomArc3Point():
    # Color to use when drawing dynamic lines
    line_color = System.Drawing.Color.FromArgb(255,0,0)
    arc_color = System.Drawing.Color.FromArgb(150,0,50)

    rc, pt_start = Rhino.Input.RhinoGet.GetPoint("Start point of arc", False)
    if( rc!=Rhino.Commands.Result.Success ): return
    rc, pt_end = Rhino.Input.RhinoGet.GetPoint("End point of arc", False)
    if( rc!=Rhino.Commands.Result.Success ): return

    # This is a function that is called whenever the GetPoint's
    # DynamicDraw event occurs
    def GetPointDynamicDrawFunc( sender, args ):
        #draw a line from the first picked point to the current mouse point
        args.Display.DrawLine(pt_start, args.CurrentPoint, line_color, 2)
        #draw a line from the second picked point to the current mouse point
        args.Display.DrawLine(pt_end, args.CurrentPoint, line_color, 2)
        #draw an arc through these three points
        arc = Rhino.Geometry.Arc(pt_start, args.CurrentPoint, pt_end)
        args.Display.DrawArc(arc, arc_color, 1)

    # Create an instance of a GetPoint class and add a delegate
    # for the DynamicDraw event
    gp = Rhino.Input.Custom.GetPoint()
    gp.DynamicDraw += GetPointDynamicDrawFunc
    gp.Get()
    if( gp.CommandResult() == Rhino.Commands.Result.Success ):
        pt = gp.Point()
        arc = Rhino.Geometry.Arc(pt_start,pt,pt_end)
        scriptcontext.doc.Objects.AddArc(arc)
        scriptcontext.doc.Views.Redraw()


if( __name__ == "__main__" ):
    CustomArc3Point()
########NEW FILE########
__FILENAME__ = MakeCircleWithRhinoCommon
################################################################
# Rhino Python Sample - MakeCircleWithRhinoCommon
#
# The rhinoscript package is provided as a scripting "convenience"
# Python can use all of the classes and functions defined
# in RhinoCommon and the rest of the .NET Framework!!!
#
# This sample creates a circle without using functions in the
# rhinoscript package
#
# Rhino is the base namespace of the RhinoCommon SDK
################################################################
import math
import Rhino
import scriptcontext


# Use a GetPoint to prompt the user to select a point
# If the user doesn't cancel, this function returns a new Circle
# class instance centered at the selection point with a radius of 1
def GetCircleFromUser():
  get_result = Rhino.Input.RhinoGet.GetPoint("Circle center", False)
  if( get_result[0] != Rhino.Commands.Result.Success ):
    print "error getting point"
    return None
  pt = get_result[1]
  print "Got a point at ", pt
  # return a new Circle
  return Rhino.Geometry.Circle( pt, 1 )

# Add some points to the document that are on a circle
def MakeCirclePoints( circle, count ):
  for i in xrange(count):
    #circles parameterized between 0 and 2Pi
    t = float(i) * 2 * math.pi / float(count)
    print t
    pt = circle.PointAt(t)
    scriptcontext.doc.Objects.AddPoint(pt)


######################################
# Functions have been defined above - let's execute some script
#
# Here we check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == '__main__' ):
  print "Python sample script to make a circle curve and plop some points on it"
  circle = GetCircleFromUser()

  if circle == None:
    print "circle is none"
  else:
    print "got a circle"
    scriptcontext.doc.Objects.AddCircle(circle)
    MakeCirclePoints( circle, 10 )
    # redraw everything so we can see what we got
    scriptcontext.doc.Views.Redraw()

  print "Script Complete"

########NEW FILE########
__FILENAME__ = AnnotateCurveEndPoints
# Annotate the endpoints of curve objects
import rhinoscriptsyntax as rs

def AnnotateCurveEndPoints():
    """Annotates the endpoints of curve objects. If the curve is closed
    then only the starting point is annotated.
    """
    # get the curve object
    objectId = rs.GetObject("Select curve", rs.filter.curve)
    if objectId is None: return

    # Add the first annotation
    point = rs.CurveStartPoint(objectId)
    rs.AddPoint(point)
    rs.AddTextDot(point, point)

    # Add the second annotation
    if not rs.IsCurveClosed(objectId):
        point = rs.CurveEndPoint(objectId)
        rs.AddPoint(point)
        rs.AddTextDot(point, point)


# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if __name__ == "__main__":
    AnnotateCurveEndPoints() # Call the function defined above
########NEW FILE########
__FILENAME__ = ArrayPointsOnSurface
# Creates an array of points on a surface
import rhinoscriptsyntax as rs

def ArrayPointsOnSurface():
    # Get the surface object
    surface_id = rs.GetObject("Select surface", rs.filter.surface)
    if surface_id is None: return

    # Get the number of rows
    rows = rs.GetInteger("Number of rows", 2, 2)
    if rows is None: return

    # Get the number of columns
    columns = rs.GetInteger("Number of columns", 2, 2)
    if columns is None: return

    # Get the domain of the surface
    U = rs.SurfaceDomain(surface_id, 0)
    V = rs.SurfaceDomain(surface_id, 1)
    if U is None or V is None: return

    # Add the points
    for i in xrange(0,rows):
        param0 = U[0] + (((U[1] - U[0]) / (rows-1)) * i)
        for j in xrange(0,columns):
            param1 = V[0] + (((V[1] - V[0]) / (columns-1)) * j)
            point = rs.EvaluateSurface(surface_id, param0, param1)
            rs.AddPoint(point)


# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if __name__ == "__main__":
    # call the function defined above
    ArrayPointsOnSurface()
########NEW FILE########
__FILENAME__ = CircleFromLength
# Create a circle from a center point and a circumference.
import rhinoscriptsyntax as rs
import math

def CreateCircle(circumference=None):
    center = rs.GetPoint("Center point of circle")
    if center:
        plane = rs.MovePlane(rs.ViewCPlane(), center)
        length = circumference
        if length is None: length = rs.GetReal("Circle circumference")
        if length and length>0:
            radius = length/(2*math.pi)
            objectId = rs.AddCircle(plane, radius)
            rs.SelectObject(objectId)
            return length
    return None

# Check to see if this file is being executed as the "Main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if __name__ == '__main__':
    CreateCircle()

# NOTE: see UseModule.py sample for using this script as a module
########NEW FILE########
__FILENAME__ = CopyObjectsToLayer
import rhinoscriptsyntax as rs

def CopyObjectsToLayer():
    "Copy selected objects to a different layer"
    # Get the objects to copy
    objectIds = rs.GetObjects("Select objects")
    # Get all layer names
    layerNames = rs.LayerNames()
    if (objectIds==None or layerNames==None): return

    # Make sure select objects are unselected
    rs.UnselectObjects( objectIds )
    
    layerNames.sort()
    # Get the destination layer
    layer = rs.ComboListBox(layerNames, "Destination Layer <" + rs.CurrentLayer() + ">")
    if layer:
        # Add the new layer if necessary
        if( not rs.IsLayer(layer) ): rs.AddLayer(layer)
        # Copy the objects
        newObjectIds = rs.CopyObjects(objectIds)

        # Set the layer of the copied objects
        [rs.ObjectLayer(id, layer) for id in newObjectIds]
        # Select the newly copied objects
        rs.SelectObjects( newObjectIds )

##########################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == "__main__" ):
  #call function defined above
  CopyObjectsToLayer()
########NEW FILE########
__FILENAME__ = CreateShortcut
import rhinoscriptsyntax as rs
import System
from System.IO import Path

def CreateShortcut():
    """
    Create a shortcut to the current document
    NOTE!! This function only runs on Windows
    """
    if( not rs.IsRunningOnWindows() ):
        rs.MessageBox("CreateShortcut.py only runs on Windows", 48, "Script Error")
        return
    
    # Get the document name and path
    name = rs.DocumentName()
    path = rs.DocumentPath()

    # Get the Windows Scripting Host's Shell object
    objShell = System.Activator.CreateInstance(System.Type.GetTypeFromProgID("WScript.Shell"))
    # Get the desktop folder
    desktop = objShell.SpecialFolders("Desktop")
    # Make a new shortcut
    ShellLink = objShell.CreateShortcut(desktop + "\\" + name + ".lnk")
    ShellLink.TargetPath = Path.Combine(path, name)
    ShellLink.WindowStyle = 1
    ShellLink.IconLocation = rs.ExeFolder() + "Rhino4.exe, 0"
    ShellLink.Description = "Shortcut to " + name
    ShellLink.WorkingDirectory = path
    ShellLink.Save()

##########################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == '__main__' ):
    #call function defined above
    CreateShortcut()

########NEW FILE########
__FILENAME__ = CurrentModelInfo
# Displays information about the currently loaded Rhino document.
import rhinoscriptsyntax as rs
from System.IO import Path, File, FileInfo, FileAttributes

# some helper functions for CurrentModelInfo
def __FileAttributes(fullpath):
    "Returns a string describing a file's attributes."
    attr = File.GetAttributes(fullpath)
    if( attr == FileAttributes.Normal ):
        return "Normal"
    rc = ""
    if( attr & FileAttributes.Directory ): rc += "Directory "
    if( attr & FileAttributes.ReadOnly ): rc += "Read Only "
    if( attr & FileAttributes.Hidden ): rc += "Hidden "
    if( attr & FileAttributes.System ): rc += "System "
    if( attr & FileAttributes.Archive ): rc += "Archive "
    if( attr & FileAttributes.Compressed ): rc += "Compressed "
    return rc


def __PrintFileInformation( fullpath ):
    "Displays a file's information."
    fi = FileInfo(fullpath)
    info  = "Full Path:  " + fullpath +"\n"
    info += "File Name:  " + Path.GetFileName(fullpath) + "\n"
    info += "File Attributes:  " + __FileAttributes(fullpath) + "\n"
    info += "Date Created:  " + File.GetCreationTime(fullpath).ToString() + "\n"
    info += "Last Date Accessed:  " + File.GetLastAccessTime(fullpath).ToString() + "\n"
    info += "Last Date Modified:  " + File.GetLastWriteTime(fullpath).ToString() + "\n"
    info += "File Size (Bytes):  " + fi.Length.ToString() + "\n"
    rs.MessageBox( info, 0, "Current Model Information" )


def CurrentModelInfo():
    "Get the current document name and path"
    name = rs.DocumentName()
    path = rs.DocumentPath()
    fileexists = False
    if( path and name ):
        filespec = Path.Combine(path, name)
        fileexists = File.Exists(filespec)
    
    if fileexists:
        __PrintFileInformation(filespec)
    else:
        print "Current model not found. Make sure the model has been saved to disk."


##########################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == "__main__" ):
  #call function defined above
  CurrentModelInfo()
########NEW FILE########
__FILENAME__ = CurveLength
import rhinoscriptsyntax as rs

def CurveLength():
    "Calculate the length of one or more curves"
    # Get the curve objects
    arrObjects = rs.GetObjects("Select Objects", rs.filter.curve, True, True)
    if( arrObjects==None ): return
    rs.UnselectObjects(arrObjects)

    length = 0.0
    count  = 0
    for object in arrObjects:
        if rs.IsCurve(object):
            #Get the curve length
            length += rs.CurveLength(object)
            count += 1
    
    if (count>0):
        print "Curves selected:", count, " Total Length:", length
    
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == "__main__" ):
    CurveLength()

########NEW FILE########
__FILENAME__ = DrawParametricCurve
import rhinoscriptsyntax as rs
import math

# Something really interesting about this script is
# that we are passing a function as a parameter
def DrawParametricCurve(parametric_equation):
    "Create a interpolated curve based on a parametric equation."
    # Get the minimum parameter
    t0 = rs.GetReal("Minimum t value", 0.0)
    if( t0==None ): return
    
    # Get the maximum parameter
    t1 = rs.GetReal("Maximum t value", 1.0)
    if( t1==None ): return

    # Get the number of sampling points to interpolate through
    count = rs.GetInteger("Number of points", 50, 2)
    if count<1: return

    arrPoints = list()
    #Get the first point
    point = parametric_equation(t0)
    arrPoints.append(point)

    #Get the rest of the points
    for x in xrange(1,count-2):
        t = (1.0-(x/count))*t0 + (x/count)*t1
        point = parametric_equation(t)
        arrPoints.append(point)
  
    #Get the last point
    point = parametric_equation(t1)
    arrPoints.append(point)
    
    #Add the curve
    rs.AddInterpCurve(arrPoints)


#Customizable function that solves a parametric equation
def __CalculatePoint(t):
    x = (4*(1-t)+1*t ) * math.sin(3*6.2832*t)
    y = (4*(1-t)+1*t ) * math.cos(3*6.2832*t)
    z = 5*t
    return x,y,z

##########################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == "__main__" ):
    #Call the function passing another function as a parameter
    DrawParametricCurve(__CalculatePoint)

########NEW FILE########
__FILENAME__ = ExportControlPoints
import rhinoscriptsyntax as rs

def ExportControlPoints():
    "Export curve's control points to a text file"
    #pick a curve object
    object_id = rs.GetObject("Select curve", rs.filter.curve)
    
    #get the curve's control points
    points = rs.CurvePoints(object_id)
    if not points: return
    
    #prompt the user to specify a file name
    filter = "Text File (*.txt)|*.txt|All files (*.*)|*.*||"
    filename = rs.SaveFileName("Save Control Points As", filter)
    if not filename: return

    file = open( filename, "w" )
    for pt in points:
        file.write( str(pt.X) )
        file.write( ", " )
        file.write( str(pt.Y) )
        file.write( ", " )
        file.write( str(pt.Z) )
        file.write( "\n" )
    file.close()


##########################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == "__main__" ):
    ExportControlPoints()
########NEW FILE########
__FILENAME__ = ExportPoints
# Export the coordinates of point and point cloud objects to a text file.
import rhinoscriptsyntax as rs

def ExportPoints():
    #Get the points to export
    objectIds = rs.GetObjects("Select Points",rs.filter.point | rs.filter.pointcloud,True,True)
    if( objectIds==None ): return

    #Get the filename to create
    filter = "Text File (*.txt)|*.txt|All Files (*.*)|*.*||"
    filename = rs.SaveFileName("Save point coordinates as", filter)
    if( filename==None ): return
    
    file = open(filename, "w")
    for id in objectIds:
        #process point clouds
        if( rs.IsPointCloud(id) ):
            points = rs.PointCloudPoints(id)
            for pt in points:
                file.writeline(str(pt))
        elif( rs.IsPoint(id) ):
            point = rs.PointCoordinates(id)
            file.writeline(str(point))
    file.close()


##########################################################################
# Here we check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == '__main__' ):
    ExportPoints()

########NEW FILE########
__FILENAME__ = HelloPython
# Basic syntax for writing python scripts
print "Hello Python!"

# <- any line that begins with the pound symbol is a comment

# assign a variable
x=123
# print out the type of the variable
print type(x)
# print out the value of the variable
print x
# combine statements with commas to print a single line
print "x is a", type(x), " and has a value of", x

#loops
# notice that there is a colon at the end of the first line and
# and what is executed has some spaces in front of it
for i in range(1,10):
    print "i=",i

#conditionals
x = 8
for i in xrange(1,x+1):
    if i%2==0:
        print i," is even"
    else:
        print i," is odd"

#functions
def MyFunc(a):
    x = a+2
    print a,"+2=",x

MyFunc(10)

########NEW FILE########
__FILENAME__ = ImportPoints
# Import points from a text file
import rhinoscriptsyntax as rs

def ImportPoints():
    #prompt the user for a file to import
    filter = "Text file (*.txt)|*.txt|All Files (*.*)|*.*||"
    filename = rs.OpenFileName("Open Point File", filter)
    if not filename: return
    
    #read each line from the file
    file = open(filename, "r")
    contents = file.readlines()
    file.close()

    # local helper function    
    def __point_from_string(text):
        items = text.strip("()\n").split(",")
        x = float(items[0])
        y = float(items[1])
        z = float(items[2])
        return x, y, z

    contents = [__point_from_string(line) for line in contents]
    rs.AddPoints(contents)



##########################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
if( __name__ == "__main__" ):
    ImportPoints()
########NEW FILE########
__FILENAME__ = sticky
# The scriptcontext module contains a standard python dictionary called
# sticky which "sticks" around during the running of Rhino. This dictionary
# can be used to save settings between execution of your scripts and then
# get at those saved settings the next time you run your script -OR- from
# a completely different script.
import rhinoscriptsyntax as rs
import scriptcontext


stickyval = 0
# restore stickyval if it has been saved
if scriptcontext.sticky.has_key("my_key"):
    stickyval = scriptcontext.sticky["my_key"]
nonstickyval = 12

print "sticky =", stickyval
print "nonsticky =", nonstickyval

val = rs.GetInteger("give me an integer")
if val:
    stickyval = val
    nonstickyval = val

# save the value for use in the future
scriptcontext.sticky["my_key"] = stickyval


########NEW FILE########
__FILENAME__ = UseModule
# This script uses a function defined in the CircleFromLength.py
# script file
import CircleFromLength

# call the function a few times just for fun using the
# optional parameter
length = CircleFromLength.CreateCircle()
if length is not None and length>0.0:
    for i in range(4):
        CircleFromLength.CreateCircle(length)
########NEW FILE########
__FILENAME__ = scriptcontext
# scriptcontext module
import RhinoPython.Host as __host

'''The Active Rhino document (Rhino.RhinoDoc in RhinoCommon) while a script
is executing. This variable is set by Rhino before the exection of every script.
'''
doc = None


'''Identifies how the script is currently executing
1 = running as standard python script
2 = running inside grasshopper component
3... potential other locations where script could be running
'''
id = 1


'''A dictionary of values that can be reused between execution of scripts
'''
sticky = dict()

def escape_test( throw_exception=True, reset=False ):
    "Tests to see if the user has pressed the escape key"
    rc = __host.EscapePressed(reset)
    if rc and throw_exception:
        raise Exception('escape key pressed')
    return rc
    

def errorhandler():
    '''
    The default error handler called by functions in the rhinoscript package.
    If you want to have your own predefined function called instead of errorhandler,
    replace the scriptcontext.errorhandler value
    '''
    return None

########NEW FILE########
