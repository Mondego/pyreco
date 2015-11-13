__FILENAME__ = availablePrograms
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import os
#internal imports
import paths

def available(programName):
  """ Returns True if the program is available for instalation. """
  return not paths.getProgramSrcDir(programName) == None

def getAvailablePrograms():
  """ Returns a list of program's available for installation. """
  repoPaths = paths.getRepoPaths()
  availablePrograms = []
  for path in repoPaths:
    availablePrograms += os.listdir(path)
  return availablePrograms

########NEW FILE########
__FILENAME__ = commandLineArguments
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import optparse
#internal imports
#import ...

def advancedInstallOptionsGroup(parser):
  """  These are advanced instalation options shared by several commands, install, update ect. """

  advancedOptions = optparse.OptionGroup(parser,"Advanced Options")
  advancedOptions.add_option("--from-cache",action="store_true",default=False,dest="useCache",help="""Use the layer cache while building the program's image.  This is dangerous and therefore dissabled by default.  The layer cache caches certain commands used to build layers.  Since some commands such as "apt-get update" should not be cached we turn this option off by default.""")
  return advancedOptions

class HelpFormatterThatDoesntReformatDescription (optparse.HelpFormatter):
  """Format help with indented section bodies but don't reformat the description.
  """

  def __init__(self,
               indent_increment=2,
               max_help_position=24,
               width=None,
               short_first=1):
      optparse.HelpFormatter.__init__(
          self, indent_increment, max_help_position, width, short_first)

  def format_usage(self, usage):
      return optparse._("Usage: %s\n") % usage

  def format_heading(self, heading):
      return "%*s%s:\n" % (self.current_indent, "", heading)

  def format_description(self, description):
    return description
########NEW FILE########
__FILENAME__ = commands
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import os
#internal imports
import executablePath,paths

nonCommands = {"__init__.py", "__init__.pyc", "subuserlib"}

def getBuiltInSubuserCommands():
  """ Get a list of the names of the built in subuser commands. """
  apparentCommandsSet = set( os.listdir(paths.getSubuserCommandsDir()))
  return list(apparentCommandsSet.difference(nonCommands))

def getExternalSubuserCommands():
  """ Return the list of "external" subuser commands.  These are not built in commands but rather stand alone executables which appear in the user's $PATH and who's names start with "subuser-" """

  def isPathToSubuserCommand(path):
    directory, executableName = os.path.split(path)
    return executableName.startswith("subuser-")

  externalCommandPaths = executablePath.queryPATH(isPathToSubuserCommand)

  externalCommands = []
  subuserPrefixLength=len("subuser-")
  for externalCommandPath in externalCommandPaths: 
    commandDir, executableName = os.path.split(externalCommandPath)
    commandName = executableName[subuserPrefixLength:]
    externalCommands.append(commandName)
  
  return list(set(externalCommands)) # remove duplicate entries

def getSubuserCommands():
  """ Returns a list of commands that may be called by the user. """
  return getBuiltInSubuserCommands() + getExternalSubuserCommands()

def getSubuserCommandPath(command):
  builtInCommandPath = os.path.join(paths.getSubuserCommandsDir(),command)
  if os.path.exists(builtInCommandPath):
    return builtInCommandPath
  else:
    externalCommandPath = executablePath.which("subuser-"+command)
    return externalCommandPath

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import os,inspect,json
#internal imports
#import ...

#The folowing is copied from paths.py in order to avoid a circular import.
home = os.path.expanduser("~")

def getSubuserDir():
  """ Get the toplevel directory for subuser. """
  return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))) # BLEGH!

##########

def getSubuserConfigPaths():
  """ Returns a list of paths to config.json files in order that they should be looked in. """
  configFileInHomeDir = os.path.join(home,".subuser","config.json")
  configFileInEtc = "/etc/subuser/config.json"
  configFileInSubuserDir = os.path.join(getSubuserDir(),"config.json")
  _configsPaths = [configFileInHomeDir,configFileInEtc,configFileInSubuserDir]
  configsPaths = []
  for path in _configsPaths:
    if os.path.exists(path):
      configsPaths.append(path)
  return configsPaths

def _addIfUnrepresented(identifier,path,paths):
  """ Add the tuple to the dictionary if it's key is not yet in the dictionary. """
  if not identifier in paths.keys():
    paths[identifier] = path

def _expandPathInConfig(path,config):
  """ Expand the environment variables in a config settings value given that the setting holds a path. """
  config[path] = os.path.expandvars(config[path])

def __expandPathsInConfig(paths,config):
  for path in paths:
    _expandPathInConfig(path,config)

def _expandPathsInConfig(config):
  """ Go through a freshly loaded config file and expand any environment variables in the paths. """
  os.environ["SUBUSERDIR"] = getSubuserDir()
  __expandPathsInConfig(["bin-dir","installed-programs.json","user-set-permissions-dir","program-home-dirs-dir"],config)

def getConfig():
  """ Returns a dictionary of settings used by subuser. """
  configPaths = getSubuserConfigPaths()
  config = {}
  for _configFile in configPaths:
    with open(_configFile, 'r') as configFile:
      _config = json.load(configFile)
      for identifier,setting in _config.iteritems():
        _addIfUnrepresented(identifier,setting,config)
  _expandPathsInConfig(config)
  return config

########NEW FILE########
__FILENAME__ = describe
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
#import ...
#internal imports
import subuserlib.permissions,subuserlib.availablePrograms,subuserlib.registry,subuserlib.dockerImages,subuserlib.dockerPs

def printInfo(program,showProgramStatus):
  """ Print information about a given program to standard output. """
  registry = subuserlib.registry.getRegistry()

  if not subuserlib.availablePrograms.available(program):
    print(program + " does not exist.\n")
    return

  permissions = subuserlib.permissions.getPermissions(program)
  print(program+":")
  print(" Description: "+permissions["description"])
  print(" Maintainer: "+permissions["maintainer"])

  if not subuserlib.registry.isProgramInstalled(program):
    print(" Installed: False")
  else:
    print(" Installed: True")
    if showProgramStatus:
      print(" Running: "+str(subuserlib.dockerPs.isProgramRunning(program)))
      if "last-update-time" in permissions.keys():
        print(" Needs update: "+str(not permissions["last-update-time"] == registry[program]["last-update-time"]))

  if subuserlib.permissions.getExecutable(permissions):
    print(" Executable: "+subuserlib.permissions.getExecutable(permissions))
  else:
    print(" Is a library")
  if subuserlib.permissions.getSharedHome(permissions):
    print(" Shares it's home directory with: "+subuserlib.permissions.getSharedHome(permissions))
  # TODO print dependencies.
  if not subuserlib.permissions.getUserDirs(permissions)==[]:
    print(" Has access to the following user directories: '~/"+"' '~/".join(subuserlib.permissions.getUserDirs(permissions))+"'")
  if not subuserlib.permissions.getSystemDirs(permissions)==[]:
    print(" Can read from the following system directories: '"+"' '".join(subuserlib.permissions.getSystemDirs(permissions))+"'")
  if subuserlib.permissions.getX11(permissions):
    print(" Can display X11 windows.")
  if subuserlib.permissions.getGraphicsCard(permissions):
    print(" Can access your graphics-card directly for OpenGL tasks.")
  if subuserlib.permissions.getSoundCard(permissions):
    print(" Has access to your soundcard, can play sounds/record sound.")
  if subuserlib.permissions.getWebcam(permissions):
    print(" Can access your computer's webcam/can see you.")
  if subuserlib.permissions.getInheritWorkingDirectory(permissions):
    print(" Can access the directory from which it was launched.")
  if subuserlib.permissions.getAllowNetworkAccess(permissions):
    print(" Can access the network/internet.")
  if subuserlib.permissions.getPrivileged(permissions):
    print(" Is fully privileged.  NOTE: Highly insecure!")

########NEW FILE########
__FILENAME__ = docker
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import sys,os,getpass,grp,subprocess
#internal imports
import subprocessExtras,executablePath

def getDockerExecutable():
  """ Return the name of the docker executable. Exits and displays a user friendly error message if docker is not setup correctly. """
  if executablePath.which("docker.io"): # Docker is called docker.io on debian.
    return "docker.io"
  if executablePath.which("docker"):
    return "docker"
  sys.exit("""Error: Docker is not installed.

For instalation instructions see <https://www.docker.io/gettingstarted/#h_installation>""")
  if not os.path.exists("/var/run/docker.pid"):
    sys.exit("""Error: Docker is not running.  You can launch it as root with:

# docker -d
""")
 
  username = getpass.getuser()
  if not username in grp.getgrnam("docker").gr_mem:
    sys.exit("""Error: You are not a member of the docker group.

To learn how to become a member of the docker group please watch this video: <http://www.youtube.com/watch?v=ahgRx5U4V7E>""")


def runDocker(args):
  """ Run docker with the given command line arguments. """
  return subprocess.call([getDockerExecutable()]+args)

def getDockerOutput(args):
  """ Run docker with the given command line arguments and return it's output. """
  return subprocess.check_output([getDockerExecutable()]+args)

def runDockerAndExitIfItFails(args):
  """ Run docker with the given command line arguments.  If the command returns a non-zero exit code, exit with an error message. """
  subprocessExtras.subprocessCheckedCall([getDockerExecutable()]+args)

########NEW FILE########
__FILENAME__ = dockerImages
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import subprocess,json,sys
#internal imports
import subprocessExtras,availablePrograms,docker

def askToInstallProgram(programName):
  """ Asks the user if they want to install the given program.  If they say yes, install it, if they decline exit."""
  if not availablePrograms.available(programName):
    sys.exit(programName+" does not exist.")
  if raw_input(programName+" is not installed. Do you want to install it now [y/n]?") == "y":
    subprocessExtras.subprocessCheckedCall(["subuser","install",programName])
  else:
    sys.exit()

def getImageTagOfInstalledProgram(program):
  """ Return a tag refering to the the docker image for an installed program.
If that program is not yet installed, install it.
  """
  if not isProgramsImageInstalled(program):
    askToInstallProgram(program)
  return "subuser-"+program

def isProgramsImageInstalled(program):
  """ Return True if the programs image tag is installed.  False otherwise. """
  return not (getImageID("subuser-"+program) == None)

def inspectImage(imageTag):
  """ Returns a dictionary coresponding to the json outputed by docker inspect. """
  try:
    dockerInspectOutput = docker.getDockerOutput(["inspect",imageTag])
  except subprocess.CalledProcessError:
    return None
  imageInfo = json.loads(dockerInspectOutput)
  return imageInfo[0]

def getImageID(imageTag):
  """ Returns the ID(as a string) of an image given that image's lable. If no image has the given lable, return None."""
  imageInfo = inspectImage(imageTag)
  if imageInfo:
    return imageInfo["id"]
  else:
    return None

def getContainerImageTag(containerID):
  inspectOutput = docker.getDockerOutput(["inspect",containerID])
  containerInfo = json.loads(inspectOutput)
  return containerInfo[0]["Config"]["Image"]
########NEW FILE########
__FILENAME__ = dockerPs
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
#import ...
#internal imports
import docker,dockerImages

def getRunningSubuserPrograms():
  """ Returns a list of the currently running subuser programs. """
  psOutput = docker.getDockerOutput(["ps","-q"])
  runningContainerIDs = filter(len,psOutput.split("\n")) #We filter out emty strings
  runningSubuserPrograms = set()
  for container in runningContainerIDs:
    containerImageTag = dockerImages.getContainerImageTag(container)
    subuserPrefix = "subuser-"
    if containerImageTag.startswith(subuserPrefix):
      runningSubuserPrograms.add(containerImageTag[len(subuserPrefix):])
  return list(runningSubuserPrograms)

def isProgramRunning(name):
  """ Returns True if the program is currently running. """
  return name in getRunningSubuserPrograms()

def areProgramsRunning(programs):
  """ Returns True if at least one of the listed programs is currently running. """
  return not (set(getRunningSubuserPrograms())&set(programs)) == set()
########NEW FILE########
__FILENAME__ = executablePath
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import os
#internal imports
#import ...

def isExecutable(fpath):
  """ Returns true if the given filepath points to an executable file. """
  return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

# Origonally taken from: http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
  fpath, fname = os.path.split(program)

  if not fpath == '':
    if isExecutable(program):
      return program
  else:
    def matchesProgram(path):
      fpath,fname = os.path.split(path)
      return program == fname
    programMatches = queryPATH(matchesProgram)
    if len(programMatches) > 0:
      return programMatches[0]
   
  return None

def queryPATH(test):
  """ Search the PATH for an executable.

Given a function which takes an absoulte filepath and returns True when the filepath matches the query, return a list of full paths to matched files. """
  matches = []
  def appendIfMatches(exeFile):
    if isExecutable(exeFile):
      if test(exeFile):
        matches.append(exeFile)

  for path in os.environ["PATH"].split(os.pathsep):
    path = path.strip('"')
    if os.path.exists(path):
      for fileInPath in os.listdir(path):
        exeFile = os.path.join(path, fileInPath)
        appendIfMatches(exeFile)

  return matches

########NEW FILE########
__FILENAME__ = install
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import sys,os,stat
#internal imports
import permissions,paths,installTime,registry,dockerImages,docker,subprocessExtras

def installExecutable(programName):
  """
Install a trivial executable script into the PATH which launches the subser program.
  """
  redirect="""#!/bin/bash
subuser run """+programName+""" $@
"""
  executablePath=paths.getExecutablePath(programName)
  with open(executablePath, 'w') as file_f:
    file_f.write(redirect)
    st = os.stat(executablePath)
    os.chmod(executablePath, stat.S_IMODE(st.st_mode) | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def installFromBaseImage(programName,programSrcDir):
  """
Build a docker base image using a script and then install that base image.
  """
  buildImageScriptPath = paths.getBuildImageScriptPath(programSrcDir)
  print("""\nATTENTION!

  Installing <"""+programName+"""> requires that the following shell script be run on your computer: <"""+buildImageScriptPath+"""> If you do not trust this shell script do not run it as it may be faulty or malicious!

  - Do you want to view the full contents of this shell script [v]?
  - Do you want to continue? (Type "run" to run the shell script)
  - To quit, press [q].

  [v/run/Q]: """)
  try:
    userInput = sys.stdin.readline().strip()
  except KeyboardInterrupt:
    sys.exit("\nOperation aborted.  Exiting.")

  if userInput == "v":
    print('\n===================== SCRIPT CODE =====================\n')
    with open(buildImageScriptPath, 'r') as file_f:
      print(file_f.read())
    print('\n===================== END SCRIPT CODE =====================\n')
    return installFromBaseImage(programName,programSrcDir)
  
  if userInput == "run":
    #Do the installation via SCRIPT
    st = os.stat(buildImageScriptPath)
    os.chmod(buildImageScriptPath, stat.S_IMODE(st.st_mode) | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    subprocessExtras.subprocessCheckedCall([buildImageScriptPath])
    return

  sys.exit("Will not run install script.  Nothing to do.  Exiting.")

def installFromDockerfile(programName, programSrcDir, useCache):
  if useCache:
    cacheArg = "--no-cache=false"
  else:
    cacheArg = "--no-cache=true"
  dockerImageDir = os.path.join(programSrcDir,"docker-image")
  docker.runDockerAndExitIfItFails(["build","--rm",cacheArg,"--tag=subuser-"+programName+"",dockerImageDir])

def installProgram(programName, useCache):
  """
  Build the docker image associated with a program and create a tiny executable to add that image to your path.
  """
  print("Installing "+programName+" ...")
  programSrcDir = paths.getProgramSrcDir(programName)
  _DockerfilePath = paths.getDockerfilePath(programSrcDir)
  # Check if we use a 'Dockerfile' or a 'BuildImage.sh'
  if os.path.isfile(paths.getBuildImageScriptPath(programSrcDir)):
    installFromBaseImage(programName,programSrcDir)
  elif os.path.isfile(_DockerfilePath):
    installFromDockerfile(programName,programSrcDir,useCache)
  else:
    sys.exit("No buildfile found: There needs to be a 'Dockerfile' or a 'BuildImage.sh' in the docker-image directory.")

  _permissions = permissions.getPermissions(programName)

  # Create a small executable that just calls the real executable in the docker image.
  if 'executable' in _permissions:
    installExecutable(programName)

  try:
    lastUpdateTime = _permissions["last-update-time"]
  except KeyError:
    lastUpdateTime = installTime.currentTimeString()

  imageID = dockerImages.getImageID("subuser-"+programName)
  registry.registerProgram(programName, lastUpdateTime, imageID)

def installProgramAndDependencies(programName, useCache):
  """
  Build the dependencytree and install bottom->up
  """
  if dockerImages.isProgramsImageInstalled(programName):
    print(programName+" is already installed.")
  else:
    #get dependencytree and install bottom->up
    dependencyTree = reversed(registry.getDependencyTree(programName))
    programsToBeInstalled = []
    for dependency in dependencyTree:
      if not dockerImages.isProgramsImageInstalled(dependency):
        programsToBeInstalled.append(dependency)

    print("The following programs will be installed.")
    for program in programsToBeInstalled:
      print(program)

    for program in programsToBeInstalled:
      installProgram(program, useCache)

########NEW FILE########
__FILENAME__ = installTime
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import time
#internal imports
import permissions,availablePrograms,paths

installTimeFormat = "%Y-%m-%d-%H:%M"

def currentTimeString():
  """ Return the current time formatted as per spec. """
  return time.strftime(installTimeFormat ,time.gmtime(time.time()))

def markProgramAsNeedingUpdate(programName):
  if not availablePrograms.available(programName):
    print(programName+ " is not the name of any known program.  Cannot mark it as having an update.")
    print("\nAvailable programs are: ")
    print(' '.join(availablePrograms.getAvailablePrograms()))
  else:
    permissions_ = permissions.getPermissions(programName)
    permissions_["last-update-time"] = currentTimeString()
    permissions.setPermissions(programName,permissions_)

########NEW FILE########
__FILENAME__ = paths
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import os,sys,inspect,json
#internal imports
import permissions,config,repositories

home = os.path.expanduser("~") 

def getSubuserDir():
  """ Get the toplevel directory for subuser. """
  return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))) # BLEGH!

def getRepoPaths():
  """
  Return a list of paths to the subuser repositories.
  """
  try:
    _repositories = repositories.getRepositories()
    repoPaths = []
    for repo,info in _repositories.iteritems():
      repoPaths.append(info["path"])
    return repoPaths
  except KeyError:
    sys.exit("Looking up repo-paths failed. Your repositories.json file is invalid.")

def getProgramSrcDir(programName):
  """
  Get the directory where the "source" of the application is stored.  That is the permissions list and the docker-image directory.

Returns None if the program cannot be found.

  """
  for repoPath in getRepoPaths():
   programSourceDir = os.path.join(repoPath,programName)
   if os.path.exists(programSourceDir):
     return programSourceDir
  return None

def getExecutablePath(progName):
  """
  Get the path to the executable that we will be installing.
  """
  return os.path.join(config.getConfig()["bin-dir"],progName)

def getPermissionsFilePath(programName):
  """ Return the path to the given programs permissions file.
Returns None if no permission file is found.
 """
  userPermissionsPath = os.path.join(config.getConfig()["user-set-permissions-dir"],programName,"permissions.json")
  if os.path.exists(userPermissionsPath):
    return userPermissionsPath
  else:
    sourceDir = getProgramSrcDir(programName)
    if not sourceDir == None:
      return os.path.join(sourceDir,"permissions.json")
    else:
      return None

def getProgramRegistryPath():
  """ Return the path to the list of installed programs json file. """
  return config.getConfig()["installed-programs.json"]

def getProgramHomeDirOnHost(programName):
  """ Each program has it's own home directory(or perhaps a shared one).
          This directory has two absolute paths:
            The path to the directory as it appears on the host machine,
            and the path to the directory in the docker container.
          Return the path to the directory as it appears on the host macine. """
  programPermissions = permissions.getPermissions(programName)
  sharedHome = permissions.getSharedHome(programPermissions)
  if sharedHome:
    return os.path.join(config.getConfig()["program-home-dirs-dir"],sharedHome)
  else:
    return os.path.join(config.getConfig()["program-home-dirs-dir"],programName)

def getDockersideScriptsPath():
  return os.path.join(getSubuserDir(),"logic","dockerside-scripts")

def getBuildImageScriptPath(programSrcDir):
  """
  Get path to the BuildImage.sh. From the program's docker-image directory.
  """
  return os.path.join(programSrcDir,"docker-image","BuildImage.sh")

def getDockerfilePath(programSrcDir):
  """
  Get path to the Dockerfile From the program's docker-image directory.
  """
  return os.path.join(programSrcDir,"docker-image","Dockerfile")

def getSubuserCommandsDir():
  """ Return the path to the directory where the individual built-in subuser command executables are stored. """
  return os.path.join(getSubuserDir(),"logic","subuserCommands")
########NEW FILE########
__FILENAME__ = permissions
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import json,os,sys,collections
#internal imports
import paths

allProgramsMustHavePermissions = "All subuser programs must have a permissions.json file as defined by the permissions.json standard: <https://github.com/subuser-security/subuser/blob/master/docs/permissions-dot-json-file-format.md>"

def getPermissions(programName):
  """ Return the permissions for the given program. """
  # read permissions.json file
  permissionsFilePath = paths.getPermissionsFilePath(programName)
  if permissionsFilePath == None:
    sys.exit("The permissions.json file for the program "+programName+" does not exist.  "+allProgramsMustHavePermissions)
  with open(permissionsFilePath, 'r') as file_f:
    try:
      permissions=json.load(file_f, object_pairs_hook=collections.OrderedDict)
    except ValueError:
      sys.exit("The permissions.json file for the program "+programName+" is not valid json.  "+allProgramsMustHavePermissions)
    return permissions

def setPermissions(programName,permissions):
  """ Set the permissions of a given program.
  Warning, will mess up the formatting of the json file.
  """
  permissionsFilePath = paths.getPermissionsFilePath(programName)
  with open(permissionsFilePath, 'w') as file_f:
    json.dump(permissions,file_f,indent=1, separators=(',', ': '))

def hasExecutable(programName):
  """ Return True if the program has an executable associated with it. """
  try:
    getPermissions(programName)["executable"]
    return True
  except KeyError:
    return False

# Getters with defaults from subuser/docs/permissions-dot-json-file-format.md

def getLastUpdateTime(permissions):
  """ Returns the last-update-time of the program in the repo.  This basically works like a version number but is less semantic. """
  return permissions.get("last-update-time",None)

def getExecutable(permissions):
  """ Either returns the path to the program's executable or None if it is a library. """
  return permissions.get("executable",None)

def getSharedHome(permissions):
  """ Either returns the name of the program this program shares it's home dir with or None if it doesn't share it's home dir. """
  return permissions.get("shared-home",None)

def getDependency(permissions):
  """ Either returns the name of the program this program depends on or None if this program has no dependency. """
  return permisssions.get("dependency",None)

def getUserDirs(permissions):
  """ Either returns the user directories this program has access to or an empty list if this program cannot access any user directories. """
  return permissions.get("user-dirs",[])

def getSystemDirs(permissions):
  """ Either returns the system directories this program can read from or an empty list if this program cannot read from any system directories. """
  return permissions.get("system-dirs",[])

def getX11(permissions):
  """ Can this program display X11 windows? """
  return permissions.get("x11",False)

def getGraphicsCard(permissions):
  """ Is this program allowed to access the GPU directly(AKA, do OpenGL stuff). """
  return permissions.get("graphics-card",False)

def getSoundCard(permissions):
  """ Can this program access the sound-card? """
  sound = permissions.get("sound-card",False)
  if not sound:
    sound = permissions.get("sound",False) # TODO depricate sound
  return sound

def getWebcam(permissions):
  """ Can this program access the computer's webcam? """
  return permissions.get("webcam",False)

def getInheritWorkingDirectory(permissions):
  """ Can this program access the directory from which it was launched? """
  return permissions.get("inherit-working-directory",False)

def getAllowNetworkAccess(permissions):
  """ Can this program access the network? """
  return permissions.get("allow-network-access",False)

def getStatefulHome(permissions):
  """ Should the state of this program's home directory be saved? """
  return permissions.get("stateful-home",True)

def getAsRoot(permissions):
  """ Should this program be run as the root user WITHIN it's docker container? """
  return permissions.get("as-root",False)

def getPrivileged(permissions):
  """ Is this program to be run in privileged mode? """
  return permissions.get("privileged",False)

########NEW FILE########
__FILENAME__ = printDependencyInfo
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import json
#internal imports
import registry

def printDependencyTables(programs):
  dependencyTable = registry.getDependencyTable(programs, useHasExecutable=False, sortLists=True)
  for program in dependencyTable.keys():
    print(program+":")
    print("    required-by: " + ", ".join(dependencyTable[program]["required-by"]))
    print("    depends-on: " + ", ".join(dependencyTable[program]["depends-on"]))

def printDependencyTableJson(programs):
  dependencyTable =registry.getDependencyTable(programs, useHasExecutable=False, sortLists=True)
  print(json.dumps(dependencyTable))

def printDependencyTrees(programList):
  for program in programList:
    treeString = ''
    for index, dependency in enumerate(registry.getDependencyTree(program)):
      if index > 0:
        treeString = ''.join([treeString, '  ' * index, '|__', dependency, '\n'])
      else:
        treeString = ''.join([treeString, dependency, '\n'])
  
    print(treeString)
  
  
def printDependencyInfo(programList,format):
  if format == 'table':
    printDependencyTables(programList)
  elif format == 'tree':
    printDependencyTrees(programList)
  elif format == 'json':
    printDependencyTableJson(programList)
########NEW FILE########
__FILENAME__ = registry
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

"""
This module provides tools for reading and writting the installed-programs.json file which holds a registry of all installed subuser programs.

To read more about the installed-programs.json file format see docs/installed-programs-dot-json-file-format.md

"""

#external imports
import json,os,sys
#internal imports
import paths,permissions,availablePrograms,dockerImages

def getRegistry():
  """ Return a dictionary of the program registry: installed-programs.json
  registered attributes:
    - last-update-time
    - image-id
    - installed-from

See docs/installed-programs-dot-json-file-format.md

  """
  programRegistry = {}
  programRegistryPath = paths.getProgramRegistryPath()
  if os.path.exists(programRegistryPath):
    with open(programRegistryPath, 'r') as file_f:
      programRegistry = json.load(file_f)

  #Maintaining backwards compat: to be soon removed
  if len(programRegistry) > 0:
    firstProgramName = programRegistry.keys()[0]
    if not isinstance(programRegistry[firstProgramName], dict):
      newProgramRegistry = {}
      for programName, lastUpdateTime in programRegistry.iteritems():
        newProgramRegistry[programName] = {}
        newProgramRegistry[programName]['last-update-time'] = lastUpdateTime
        newProgramRegistry[programName]['image-id'] = dockerImages.getImageID("subuser-"+programName)
      programRegistry = newProgramRegistry
      #save the new one here once and for all
      setInstalledPrograms(programRegistry)
  return programRegistry

def getInstalledPrograms():
  """ Returns a list of installed programs.
  """
  return getRegistry().keys()

def setInstalledPrograms(programRegistry):
  """ Passing this file a dictionary which maps program names to registered items writes that registry to disk, overwritting the previous one.
  registered items:
    - last-update-time
    - image-id
    """
  programRegistryPath = paths.getProgramRegistryPath()
  with open(programRegistryPath, 'w') as file_f:
    json.dump(programRegistry, file_f, indent=1, separators=(',', ': '))

def registerProgram(programName, lastUpdateTime, imageID):
  """ Add a program to the registry.  If it is already in the registry, update its registered items.
  registered items:
    - last-update-time
    - image-id
    """
  programRegistry = getRegistry()
  programRegistry[programName] = {}
  programRegistry[programName]['last-update-time'] = lastUpdateTime
  programRegistry[programName]['image-id'] = imageID
  setInstalledPrograms(programRegistry)

def unregisterProgram(programName):
  """ Remove a program from the registry. """
  programRegistry = getRegistry()
  del programRegistry[programName]
  setInstalledPrograms(programRegistry)

def isProgramInstalled(programName):
  """ Returns true if the program is installed. """
  installedPrograms = getRegistry()
  try:
    installedPrograms[programName]
    return True
  except KeyError:
    return False

def hasInstalledDependencies(programName):
  """ Returns true if there are any program's which depend upon this program installed. """
  for program in getInstalledPrograms():
    try:
      if permissions.getPermissions(program)["dependency"] == programName:
        return True
    except KeyError:
      pass

def getInstalledDependents(programName):
  """ Returns returns a list of any installed programs which depend upon this program. """
  installedDependents = []
  for program in getInstalledPrograms():
    try:
      if permissions.getPermissions(program)["dependency"] == programName:
        installedDependents.append(program)
    except KeyError:
      pass

  return installedDependents

def getDependencyTree(programName):
  """ Returns a dependency tree list of any available program. """
  dependency = ""
  programDependencyTree = [programName]
  programPermissions = permissions.getPermissions(programName)
  dependency = programPermissions.get("dependency", None)
  while dependency:
    if not availablePrograms.available(dependency):
      sys.exit(programName+" depends upon "+dependency+" however "+dependency+" does not exist.")
    programDependencyTree.append(dependency)
    programPermissions = permissions.getPermissions(dependency)
    dependency = programPermissions.get("dependency", None)
  return programDependencyTree

def _createEmptyDependencyTable(programList,useHasExecutable):
  dependencyTable = {}
  for program in programList:
    if useHasExecutable:
      if permissions.hasExecutable(program):
        dependencyTable[program] = {"required-by" : [], "depends-on" : [], "has-executable" : True}
      else:
        dependencyTable[program] = {"required-by" : [], "depends-on" : [], "has-executable" : False}
    else:
      dependencyTable[program] = {"required-by" : [], "depends-on" : []}
  return dependencyTable


def _sortFieldsInDependencyTable(dependencyTable):
  for program in dependencyTable.keys():
    dependencyTable[program]["depends-on"] = sorted(dependencyTable[program]["depends-on"])
    dependencyTable[program]["required-by"] = sorted(dependencyTable[program]["required-by"])


def getDependencyTable(programList, useHasExecutable=False, sortLists=False):
  """
  Returns a programName<->dependency info dictionary.

  Arguments:
  - programList: List of available or installed (or a selected list)  of subuser-programs
            (getInstalledPrograms(), or getAvailablePrograms(), or ["firefox", "vim"]
  - useHasExecutable: boolean: if True an additional key "has-executable" will be added to the table
  - sortLists: boolean: if True: required-by, depends-on  will be sorted

  Table format when useHasExecutable is False:
                                { 'programName' : {
                                          "required-by" : [app1, app2],
                                          "depends-on" : [app1, lib3]
                                                                    }
                                }

  Table format when useHasExecutable is True
                                { 'programName' : {
                                          "required-by" : [app1, app2],
                                          "depends-on" : [],
                                          "has-executable" : True
                                                                    }
                                }

  NOTE: The following keys are always present: required-by, depends-on though they may be empty lists
  """

  # Create a dictionary of empty matrices.
  dependencyTable = _createEmptyDependencyTable(programList,useHasExecutable)

  def markAsRequiredBy(program):
    """ Add this program to the "required-by" field of any program that depends upon it. """
    if dependency in dependencyTable.keys():
      dependencyTable[dependency]["required-by"].append(program)

  for program in dependencyTable.keys():
    for dependency in getDependencyTree(program):
      if dependency != program:
        dependencyTable[program]["depends-on"].append(dependency)
        markAsRequiredBy(program)
  #sort if required
  if sortLists:
    _sortFieldsInDependencyTable(dependencyTable)
  return dependencyTable

########NEW FILE########
__FILENAME__ = repositories
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

# TODO, refactor by putting helper functions for both repositories.py and configs.py in one place.

#external imports
import os,inspect,json,collections,sys
#internal imports
#import ...

home = os.path.expanduser("~")

def _getSubuserDir():
  """ Get the toplevel directory for subuser. """
  return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))) # BLEGH!

def _getRepositoryListPaths():
  """ Returns a list of paths to repositories.json files in order that they should be looked in. """
  _repositoryListPaths = []
  _repositoryListPaths.append(os.path.join(home,".subuser","repositories.json"))
  _repositoryListPaths.append("/etc/subuser/repositories.json") # TODO how does this work on windows?
  _repositoryListPaths.append(os.path.join(_getSubuserDir(),"repositories.json"))
  repositoryListPaths = []
  for path in _repositoryListPaths:
   if os.path.exists(path):
    repositoryListPaths.append(path)
  return repositoryListPaths

def _addIfUnrepresented(identifier,path,paths):
  """ Add the tuple to the dictionary if it's key is not yet in the dictionary. """
  if not identifier in paths.keys():
    paths[identifier] = path

def expandVarsInPaths(repositories):
  """ Go through a freshly loaded list of repositories and expand any environment variables in the paths. """
  os.environ["SUBUSERDIR"] = _getSubuserDir()
  for reponame,info in repositories.iteritems():
    info["path"] = os.path.expandvars(info["path"])

def getRepositories():
  """ Returns a dictionary of repositories used by subuser. """
  repositoryListPaths = _getRepositoryListPaths()
  repositories = {}
  for _repositoryListFile in repositoryListPaths:
    with open(_repositoryListFile, 'r') as repositoryListFile:
      try:
        _repositories = json.load(repositoryListFile, object_pairs_hook=collections.OrderedDict)
        for identifier,repository in _repositories.iteritems():
          _addIfUnrepresented(identifier,repository,repositories)
      except ValueError:
        sys.exit("The repositories file is invalid json.")
  expandVarsInPaths(repositories)
  return repositories

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import sys,os,getpass,subprocess,tempfile
#internal imports
import subuserlib.permissions,subuserlib.dockerImages,subuserlib.docker,subuserlib.update

###############################################################
username = getpass.getuser()
cwd = os.getcwd()
home = os.path.expanduser("~")
###############################################################

def getAllowNetworkAccessArgs(permissions):
  if subuserlib.permissions.getAllowNetworkAccess(permissions):
    return ["--networking=true","--dns=8.8.8.8"] # TODO depricate this once the docker folks fix the dns bugs
  else:
    return ["--networking=false"]

def setupHostSubuserHome(home):
  if not os.path.exists(home):
    os.makedirs(home)

def getAndSetupHostSubuserHome(programName,permissions):
  if subuserlib.permissions.getStatefulHome(permissions):
    hostSubuserHome = subuserlib.paths.getProgramHomeDirOnHost(programName)
  else:
    hostSubuserHome = tempfile.mkdtemp(prefix="subuser-"+programName)

  setupHostSubuserHome(hostSubuserHome)
  return hostSubuserHome
 
def makeSystemDirVolumeArgs(systemDirs):
  return ["-v="+systemDir+":"+systemDir+":ro" for systemDir in systemDirs]

def getAndSetupUserDirVolumes(permissions,hostSubuserHome,dry):
  """ Sets up the user directories to be shared between the host user and the subuser-program.
Returns volume arguments to be passed to docker run"""
  def setupUserDirSymlinks(userDirs):
    """ Create symlinks to userdirs in program's home dir. """
    for userDir in userDirs:
      source = os.path.join("/userdirs/",userDir)
      destination = os.path.join(hostSubuserHome,userDir)
      if not os.path.islink(destination):
        os.symlink(source,destination)

  userDirs = subuserlib.permissions.getUserDirs(permissions)
  if not dry:
    setupUserDirSymlinks(userDirs)
  userDirVolumeArgs = makeUserDirVolumeArgs(userDirs)
  return userDirVolumeArgs

def makeUserDirVolumeArgs(userDirs):
  return ["-v="+os.path.join(home,userDir)+":"+os.path.join("/userdirs/",userDir)+":rw" for userDir in userDirs]

def getSetupUserAndRunArgs(permissions):
  if not subuserlib.permissions.getAsRoot(permissions):
    setupUserAndRunPath = "/launch/setupUserAndRun"
    return [setupUserAndRunPath,username]
  else:
    return ["/launch/runCommand","root"]

def getWorkingDirectoryVolumeArg(permissions):
  if subuserlib.permissions.getInheritWorkingDirectory(permissions):
    return ["-v="+cwd+":/home/pwd:rw"]
  else:
    return []

def getDockersideHome(permissions):
  if subuserlib.permissions.getAsRoot(permissions):
    return "/root/"
  else:
    return home

def getAndSetupVolumes(programName,permissions,dry):
  """ 
Sets up the volumes which will be shared between the host and the subuser program.

Returns a list of volume mounting arguments to be passed to docker run.
"""

  hostSubuserHome = getAndSetupHostSubuserHome(programName,permissions) 

  dockersideScriptsPath = subuserlib.paths.getDockersideScriptsPath()
  dockersideBinPath = "/launch"
  dockersidePWDPath = os.path.join("/home","pwd")

  systemDirVolumeArgs = makeSystemDirVolumeArgs(subuserlib.permissions.getSystemDirs(permissions))

  userDirVolumeArgs = getAndSetupUserDirVolumes(permissions,hostSubuserHome,dry)

  workingDirectoryVolumeArg = getWorkingDirectoryVolumeArg(permissions)

  dockersideHome = getDockersideHome(permissions)

  volumeArgs = ["-v="+hostSubuserHome+":"+dockersideHome+":rw"
    ,"-v="+dockersideScriptsPath+":"+dockersideBinPath+":ro"] + workingDirectoryVolumeArg + systemDirVolumeArgs + userDirVolumeArgs

  def cleanUpVolumes():
    if not subuserlib.permissions.getStatefulHome(permissions):
      subprocess.call(["rm","-rf",hostSubuserHome])

  return (volumeArgs,cleanUpVolumes)

def getX11Args(permissions):
  if subuserlib.permissions.getX11(permissions):
    return ["-e","DISPLAY=unix"+os.environ['DISPLAY'],"-v=/tmp/.X11-unix:/tmp/.X11-unix:rw"]
  else:
    return []

def getGraphicsCardArgs(permissions):
  if subuserlib.permissions.getGraphicsCard(permissions):
    return  ["-v=/dev/dri:/dev/dri:rw","--lxc-conf=lxc.cgroup.devices.allow = c 226:* rwm"]
  else:
    return []

def getSoundCardArgs(permissions):
  if subuserlib.permissions.getSoundCard(permissions):
    return  ["-v=/dev/snd:/dev/snd:rw","--lxc-conf=lxc.cgroup.devices.allow = c 116:* rwm"]
  else:
    return []

def getWebcamArgs(permissions):
  if subuserlib.permissions.getWebcam(permissions):
    cameraVolumes = []
    for device in os.listdir("/dev/"):
      if device.startswith("video"):
        cameraVolumes.append("-v=/dev/"+device+":/dev/"+device+":rw")
    return  cameraVolumes+["--lxc-conf=lxc.cgroup.devices.allow = c 81:* rwm"]
  else:
    return []

def getPrivilegedArg(permissions):
  if subuserlib.permissions.getPrivileged(permissions):
    return ["--privileged"]
  else:
    return []

def getDockerArguments(programName,programArgs,dry):
  dockerImageName = subuserlib.dockerImages.getImageTagOfInstalledProgram(programName)
  permissions = subuserlib.permissions.getPermissions(programName)
  allowNetworkAccessArgs = getAllowNetworkAccessArgs(permissions)
  executable = subuserlib.permissions.getExecutable(permissions)
  setupUserAndRunArgs = getSetupUserAndRunArgs(permissions)
  x11Args = getX11Args(permissions)
  graphicsCardArgs = getGraphicsCardArgs(permissions)
  soundCardArgs = getSoundCardArgs(permissions)
  webcamArgs = getWebcamArgs(permissions)
  privilegedArg = getPrivilegedArg(permissions)
  (volumeArgs,cleanUpVolumes) = getAndSetupVolumes(programName,permissions,dry)
  dockerArgs = ["run","-i","-t","--rm"]+allowNetworkAccessArgs+privilegedArg+volumeArgs+x11Args+graphicsCardArgs+soundCardArgs+webcamArgs+[dockerImageName]+setupUserAndRunArgs+[executable]+programArgs
  return (dockerArgs,cleanUpVolumes)

def showDockerCommand(dockerArgs):
  print("""If this wasn't a dry run, the following command would be executed.

Please note: This is for testing purposes only, and this command is not guaranteed to work.""")
  print("docker '"+"' '".join(dockerArgs)+"'")

def runProgram(programName,programArgs,dry=False):
  if subuserlib.update.needsUpdate(programName):
   print("""This program needs to be updated.  You can do so with:

$ subuser update

Trying to run anyways:
""")
  (dockerArgs,cleanUpVolumes) = getDockerArguments(programName,programArgs,dry)
  if not dry:
   subuserlib.docker.runDocker(dockerArgs)
  else:
   showDockerCommand(dockerArgs)
  cleanUpVolumes()

########NEW FILE########
__FILENAME__ = subprocessExtras
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import sys,subprocess
#internal imports
#import ...

def subprocessCheckedCall(args, addToErrorInfo=''):
  """ This helper function calls subprocess.check_call and runs sys.exit rather than throwing an error when the program exits with a non-zero exit code.

 Usage:
  subprocessCheckedCall(["docker", "-d"], "ATTENTION: Special added info bla bla")
  """
  try:
    subprocess.check_call(args)
  except Exception as err:
    if addToErrorInfo:
      message = ('''Command <{0}> failed:\n  ERROR: {1}\n    {2}'''.format(' '.join(args), err, addToErrorInfo))
    else:
      message = ('''Command <{0}> failed:\n  ERROR: {1}'''.format(' '.join(args), err))
    sys.exit(message)
    
def subprocessCheckedOutput(args, addToErrorInfo=''):
  """ This function calls subprocess.check_output and uses sys.exit when the call fails rather than throwing an error.

 Usage:
  subprocessCheckedOutput(["docker", "-d"], "ATTENTION: Special added info bla bla")
  """
  try:
    return subprocess.check_output(args)
  except Exception as err:
    if addToErrorInfo:
      message = ('''Command <{0}> failed:\n  ERROR: {1}\n    {2}'''.format(' '.join(args), err, addToErrorInfo))
    else:
      message = ('''Command <{0}> failed:\n  ERROR: {1}'''.format(' '.join(args), err))
    sys.exit(message)

########NEW FILE########
__FILENAME__ = uninstall
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

#external imports
import sys,os,subprocess
#internal imports
import paths,registry,dockerImages,docker

def uninstall(programName):
  print("Uninstalling "+programName)
  if dockerImages.isProgramsImageInstalled(programName):
    while not docker.runDocker(["rmi","subuser-"+programName]) == 0:
      if not raw_input("Once you have solved the problem either type [y] to continue, or [q] to exit: ") == 'y':
        sys.exit()
  if os.path.exists(paths.getExecutablePath(programName)):
    os.remove(paths.getExecutablePath(programName))

  registry.unregisterProgram(programName)
  programHomeDir=paths.getProgramHomeDirOnHost(programName)
  if os.path.exists(programHomeDir):
    print("The program has been uninstalled but it's home directory remains:")
    print(programHomeDir)
  print(programName+" uninstalled successfully.")
########NEW FILE########
__FILENAME__ = update
#!/usr/bin/env python
# This file should be compatible with both Python 2 and 3.
# If it is not, please file a bug report.

# This command updates all or some of the installed subuser programs.

#external imports
import sys,subprocess
#internal imports
import registry,permissions,dockerImages,uninstall,install,subprocessExtras,commandLineArguments,availablePrograms

#####################################################################################
def getProgramsWhosLastUpdateTimesChanged():
  """ Returns a list of progams who's last-update-time has changed since it was installed. """
  programsWhosLastUpdateTimeChanged = []
  _registry = registry.getRegistry()
  for program, registeredInfo in _registry.iteritems():
    availableLastUpdateTime = permissions.getPermissions(program).get("last-update-time",None)
    installedLastUpdateTime = registeredInfo.get("last-update-time",None)
    if not availableLastUpdateTime == installedLastUpdateTime and not availableLastUpdateTime == None:
      programsWhosLastUpdateTimeChanged.append(program)
  return programsWhosLastUpdateTimeChanged

def uninstallProgramsToBeUpdated(programsToBeUpdated):
  programsToBeUninstalled = set(programsToBeUpdated)

  uninstalledPrograms = set([])
  while not programsToBeUninstalled == uninstalledPrograms:
    for program in programsToBeUninstalled:
      if not registry.hasInstalledDependencies(program):
        uninstall.uninstall(program)
        uninstalledPrograms.add(program)

def installProgramsToBeUpdated(programsToBeUpdated):
  for program in programsToBeUpdated:
    if permissions.hasExecutable(program): # Don't install libraries as these might have changed and no longer be needed.  They'll automatically get installed anyways.
      install.installProgramAndDependencies(program, False)

def runUpdate(programsToBeUpdated):
  print("The following programs will be updated:")
  for program in programsToBeUpdated:
    print(program)
  choice = raw_input("Do you want to continue updating [y/n]? " )
  if choice in ["Y","y"]:
    uninstallProgramsToBeUpdated(programsToBeUpdated)
    installProgramsToBeUpdated(programsToBeUpdated)
  else:
    sys.exit()

  while dockerPs.areProgramsRunning(programsToBeUpdated):
    print("PLEASE: close these programs before continuing. If there seem to be containers hanging around when the program isn't even running you might try:")
    print(" $ docker kill <container-id>")
    print("You still need to close:")
    for program in programsToBeUpdated:
      if dockerPs.isProgramRunning(program):
        print(program)
    shouldQuit = raw_input("Press enter to continue(or q to quit): ")
    if shouldQuit == 'q':
      exit()

def updateSomePrograms(programs):
  programsToBeUpdated = set()
  dependencyTable = registry.getDependencyTable(availablePrograms.getAvailablePrograms())
  for program in programs:
    programsToBeUpdated.add(program)
    for dependent in dependencyTable[program]["required-by"]:
      if registry.isProgramInstalled(dependent):
        programsToBeUpdated.add(dependent)
  runUpdate(list(programsToBeUpdated))

def needsUpdate(program):
  """ Returns true if the program or any of it's dependencies need to be updated. """
  _registry = registry.getRegistry()
  dependencyTable = registry.getDependencyTable(availablePrograms.getAvailablePrograms())
  programsToCheck = dependencyTable[program]["depends-on"]
  programsToCheck.append(program)
  for programToCheck in programsToCheck:
    myPermissions = permissions.getPermissions(programToCheck)
    if not permissions.getLastUpdateTime(myPermissions) == _registry[programToCheck]["last-update-time"] and not permissions.getLastUpdateTime(myPermissions) == None:
      return True
  return False

########NEW FILE########
