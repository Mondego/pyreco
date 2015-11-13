__FILENAME__ = buildDebPackage
import urllib2
import os
import os.path 
import sys
import tarfile
from shutil import copytree,ignore_patterns,copy,rmtree
from stat import *
import fnmatch
import re
import hashlib
import gzip
from string import Template
from subprocess import call


tmpDir="/tmp/"

def dlTagFromGitHub(version):
    remoteFile = urllib2.urlopen('https://github.com/mNantern/QTodoTxt/archive/'+version+'.tar.gz')
    contentDisposition=remoteFile.info()['Content-Disposition']
    fileName=contentDisposition.split('=')[1]

    localFile = open(tmpDir+fileName, 'wb')
    localFile.write(remoteFile.read())
    localFile.close()
    return fileName


def uncompressFile(fileName):
    os.chdir(tmpDir)
    bashCmd=" ".join(["tar xzf",tmpDir+fileName,"--exclude-vcs --no-same-permissions"])
    call(bashCmd,shell=True)
    return fileName.rsplit(".",2)[0]

def buildPackageFolder(folderName):
    buildDir=tmpDir+folderName+'_build'
    buildBinDir=buildDir+'/usr/share/qtodotxt/bin/'
    debianDir=buildDir+'/DEBIAN/'

    # Tree structure
    os.makedirs(debianDir)
    os.makedirs(buildDir+'/usr/bin/')
    os.makedirs(buildDir+'/usr/share/doc/qtodotxt')
    os.makedirs(buildDir+'/usr/share/applications')

    #Copy tag folder to build folder except the windows script
    copytree(tmpDir+folderName,buildDir+'/usr/share/qtodotxt',False,ignore_patterns('qtodotxt.pyw'))
    #Fix execution rights on bin folder
    for file in os.listdir(buildBinDir):
        filePath=os.path.join(buildBinDir,file)
        if os.path.isfile(filePath):
            st = os.stat(filePath)
            os.chmod(filePath, st.st_mode | S_IEXEC)

    # Adding copyright file
    copy(scriptDir+'/copyright',buildDir+'/usr/share/doc/qtodotxt/copyright')
    # Adding desktop file
    copy(scriptDir+'/qtodotxt.desktop',buildDir+'/usr/share/applications/qtodotxt.desktop')
    # Adding changelog file
    f_in = open(scriptDir+'/changelog', 'rb')
    f_out = gzip.open(buildDir+'/usr/share/doc/qtodotxt/changelog.gz', 'wb')
    f_out.writelines(f_in)
    f_out.close()
    f_in.close()

    return (buildDir,debianDir)


def makeMd5sums(baseDir,outputFilePath):

    excludes = ['DEBIAN','*.pyc']
    excludes = r'|'.join([fnmatch.translate(x) for x in excludes]) or r'$.'

    outputFile = open(outputFilePath, 'w')

    for (root,dirs,files) in os.walk(baseDir):
        dirs[:] = [d for d in dirs if not re.match(excludes,d)]
        files = [f for f in files if not re.match(excludes,f)]

        for fn in files:
            path = os.path.join(root,fn)
            md5 = hashlib.md5(open(path,'rb').read()).hexdigest()
            relativePath = root.replace(baseDir+'/',"",1) + os.sep + fn
            outputFile.write("%s %s\n" % (md5,relativePath))
            
    outputFile.close()

def generateControl(templateFile,packageVersion,outputFilePath):
    
    templateExp = open(templateFile,'r').read()
    template = Template(templateExp)

    substitute=template.safe_substitute(version=packageVersion)
    open(outputFilePath,'w').write(substitute)
    #Control file must be owned by root
    os.chown(outputFilePath,0,0)

def buildDeb(version,buildDir):
    # Adding symlink to bin folder
    os.chdir(buildDir+'/usr/bin/')
    os.symlink('../share/qtodotxt/bin/qtodotxt','qtodotxt')

    bashCmd=" ".join(["dpkg -b",buildDir,tmpDir+"qtodotxt_"+version+"_all.deb"])
    call(bashCmd,shell=True)

def clean(fileName,folderName):
    # Removing tar.gz
    os.remove(tmpDir+fileName)
    # Removing untar folder
    rmtree(tmpDir+folderName)
    #Removing build folder
    rmtree(tmpDir+folderName+'_build')


version=sys.argv[1]
scriptDir = os.path.dirname(os.path.realpath(sys.argv[0]))
# Step 1: download tag from github
fileName = dlTagFromGitHub(version)

# Step 2: uncompress tag's archive
folderName = uncompressFile(fileName)

# Step 3: build Debian package structure
(buildDir,debianDir)=buildPackageFolder(folderName)

# Step 4: build DEBIAN/md5sums file
makeMd5sums(buildDir,debianDir+'md5sums')

# Step 5: generate DEBIAN/control file
generateControl(scriptDir+'/control.tpl',version,debianDir+'control')

# Step 6: build the deb package
buildDeb(version,buildDir)

# Step 7: clean all the mess
clean(fileName,folderName)

########NEW FILE########
__FILENAME__ = app
import sys

from PySide import QtGui
from qtodotxt.ui.services.dialogs_service import DialogsService
from qtodotxt.ui.services.task_editor_service import TaskEditorService
from qtodotxt.ui.views import MainView
from qtodotxt.ui.controllers import MainController
from qtodotxt.ui.resource_manager import getIcon


def run():
    app = QtGui.QApplication(sys.argv)
    controller = _createController()
    icon = TrayIcon(controller)
    controller.show()
    app.exec_()
    sys.exit()


def _createController():
    window = MainView()
    dialogs_service = DialogsService(window, 'QTodoTxt')
    task_editor_service = TaskEditorService(window)
    return MainController(window, dialogs_service, task_editor_service)


class TrayIcon(QtGui.QSystemTrayIcon):
    def __init__(self, main_controller):
        self._controller = main_controller
        self._initIcon()
        self.show()

    def _initIcon(self):
        view = self._controller.getView()
        icon = getIcon('qtodotxt.ico')
        QtGui.QSystemTrayIcon.__init__(self, icon, view)
        self.activated.connect(self._onActivated)
        self.setToolTip('QTodoTxt')
    
    def _onActivated(self):
        self._controller._tasks_list_controller.createTask()
    
if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = filters
import re


class BaseFilter(object):
    """
    The abstract base class for different kind of task-list filters.

    """
    def __init__(self, text):
        """
        Initialize a new BaseFilter objects.

        The required text argument (str) becomes the "text" instance attribute
        of the object.

        """
        self.text = text

    def isMatch(self, task):
        """
        Determine whether the supplied task (arg 'task') satisfies the filter.

        In this base class, the test always returns True.

        """
        return True

    def __eq__(self, other):
        """
        Evaluates objects as equal if their type and self.text attr are the same.

        """
        if not other:
            return False
        if type(other) == type(self):
            return self.text == other.text
        return False


class IncompleteTasksFilter(BaseFilter):
    """
    Task list filter that removes any completed tasks.

    """
    def __init__(self):
        BaseFilter.__init__(self, 'Incomplete')

    def isMatch(self, task):
        return not task.is_complete


class UncategorizedTasksFilter(BaseFilter):
    """
    Task list filter permitting incomplete tasks without project or context.

    """
    def __init__(self):
        BaseFilter.__init__(self, 'Uncategorized')

    def isMatch(self, task):
        return (not task.is_complete) and (not task.contexts) and (not task.projects)


class CompleteTasksFilter(BaseFilter):
    """
    Task list filter that removes any uncompleted tasks from the list.

    """
    def __init__(self):
        BaseFilter.__init__(self, 'Complete')

    def isMatch(self, task):
        return task.is_complete


class ContextFilter(BaseFilter):
    """
    Task list filter allowing only incomplete tasks with the selected context.

    """

    def __init__(self, context):
        BaseFilter.__init__(self, context)

    def isMatch(self, task):
        return (not task.is_complete) and (self.text in task.contexts)

    def __str__(self):
        return "ContextFilter(%s)" % self.text


class ProjectFilter(BaseFilter):
    """
    Task list filter allowing only incomplete tasks with the selected project.

    """
    def __init__(self, project):
        BaseFilter.__init__(self, project)

    def isMatch(self, task):
        return (not task.is_complete) and (self.text in task.projects)

    def __str__(self):
        return "ProjectFilter(%s)" % self.text


class HasProjectsFilter(BaseFilter):
    """
    Task list filter allowing only incomplete tasks with the selected project.

    """

    def __init__(self):
        BaseFilter.__init__(self, 'Projects')

    def isMatch(self, task):
        return (not task.is_complete) and task.projects

    def __str__(self):
        return "HasProjectsFilter" % self.text


class HasContextsFilter(BaseFilter):
    """
    Task list filter allowing only tasks tagged with some project.

    """

    def __init__(self):
        BaseFilter.__init__(self, 'Contexts')

    def isMatch(self, task):
        return (not task.is_complete) and task.contexts

    def __str__(self):
        return "HasContextsFilter" % self.text


class SimpleTextFilter(BaseFilter):
    """
    Task list filter allowing only tasks whose string matches a filter string.

    This filter allows for basic and/or/not conditions in the filter string.
    For the syntax see SimpleTextFilter.isMatch.

    """

    def __init__(self, text):
        BaseFilter.__init__(self, text)

    def isMatch(self, task):
        """
        Return a boolean based on whether the supplied task satisfies self.text.
        TODO: the NOT syntax described below isn't yet implemented

        This filter can handle basic and/or/not conditions. The syntax is as
        follows:

        :AND   :   ',' or whitespace (' ')
        :OR    :   '|'
        :NOT   :   prefixed '~' or '!'  {not yet implemented}

        These operators follow the following order of precedence: OR, AND, NOT.
        So, for example:

        :'work job1 | home':                Either  (matches 'work'
                                                     AND 'job1')
                                            OR      (matches 'home')

        :'norweigan blue ~dead | !parrot':  Either  (matches 'norweigan'
                                                     AND 'blue'
                                                     AND does NOT match 'dead')
                                            OR      (does NOT match 'parrot')

        Since the python re module is used, most of the escaped regex
        characters will also work when attached to one of the (comma- or space-
        delimited) strings. E.g.:
        - \bcleese\b will match 'cleese' but not 'johncleese'
        - 2014-\d\d-07 will match '2014-03-07' but not '2014-ja-07'

        The method can handle parentheses in the search strings. Unlike most
        regex characters, these don't need to be escaped since they are escaped
        automatically. So the search string '(B)' will match '(B) nail its
        feet to the perch'.
        """
        # TODO: implement NOT conditions
        mymatch = False
        comp = re.compile(r'\s*([\(\)\w\\\-]+)[\s,]*', re.U)
        restring = comp.sub(r'^(?=.*\1)', self.text, re.U)
        try:
            if ')' in restring:
                raise re.error  # otherwise adding closing parenth avoids error here
            mymatch = re.search(restring, task.text, re.I | re.U)
        except re.error:
            comp2 = re.compile(r'\s*\((?=[^?])', re.U)
            restring2 = comp2.sub(r'\\(', restring, re.U)
            comp3 = re.compile(r'(?<!\))\)(?=\))', re.U)
            restring3 = comp3.sub(r'\\)', restring2, re.U)
            mymatch = re.search(restring3, task.text, re.I | re.U)

        return mymatch

    def __str__(self):
        return "SimpleTextFilter({})".format(self.text)


class FutureFilter(BaseFilter):

    def __init__(self):
        BaseFilter.__init__(self, 'Future')

    def isMatch(self, task):
        return not task.is_future

    def __str__(self):
        return "FutureFilter " % self.text

########NEW FILE########
__FILENAME__ = settings
import os
import pickle

DEFAULT_SETTINGS_FILE = os.path.expanduser("~/.qtodotxt.cfg")


class Settings(object):
    def __init__(self):
        self._file = DEFAULT_SETTINGS_FILE
        self._data = dict()
            
    def load(self, filename=DEFAULT_SETTINGS_FILE):
        self._file = filename
        if os.path.exists(self._file):
            with open(self._file) as file:
                self._data = pickle.load(file)
            
    def getLastOpenFile(self):
        return self._getData('last_open_file')
    
    def setLastOpenFile(self, last_open_file):
        self._setData('last_open_file', last_open_file)

    def getCreateDate(self):
        return self._getData('add_create_date')

    def setCreateDate(self, addCreationDate):
        self._setData('add_create_date', addCreationDate)

    def getAutoSave(self):
        return self._getData('auto_save')
        
    def setAutoSave(self, autoSave):
        self._setData('auto_save', autoSave)
        
    def getAutoArchive(self):
        return self._getData('auto_archive')
    
    def setAutoArchive(self, autoArchive):
        self._setData('auto_archive', autoArchive)

    def getHideFutureTasks(self):
        return self._getData('hide_future_tasks')

    def setHideFutureTasks(self, hideFutureTasks):
        self._setData('hide_future_tasks', hideFutureTasks)

    def _getData(self, key):
        if self._data:
            return self._data.get(key)
        return None

    def _setData(self, key, value):
        if not self._data:
            self._data = dict()
        self._data[key] = value
        self._save()
    
    def _save(self):
        if self._data:
            with open(self._file, 'w') as file:
                file = open(self._file, 'w') 
                pickle.dump(self._data, file)
########NEW FILE########
__FILENAME__ = task_htmlizer
from datetime import datetime, date
import re


class TaskHtmlizer(object):
    def __init__(self):
        self.priority_colors = dict(
            A='red',
            B='green',
            C='cyan')
        # regex matching creation and completion dates and priority
        self.regex = re.compile(
            r'^(x (?P<completed>\d{4}-\d{2}-\d{2} )?)?(\((?P<priority>[A-Z])\) )?(?P<created>\d{4}-\d{2}-\d{2} )?.*$')

    def task2html(self, task, selected=False):
        text = task.text
        priority = task.priority

        if task.is_complete:
            text = '<s>%s</s>' % text.replace('x ', '', 1)
            # when the task is complete, the Task object has no priority. We find the original priority from the text
            priority = re.match(self.regex, task.text).group('priority')
        for context in task.contexts:
            text = text.replace('@' + context, self._htmlizeContext(context))
        for project in task.projects:
            text = text.replace('+' + project, self._htmlizeProject(project))
        if priority is not None:
            text = text.replace('(%s) ' % priority, self._htmlizePriority(priority))
        else:
            # add 3 spaces, so tasks get evenly aligned when there's no priority
            text = '<tt>&nbsp;&nbsp;&nbsp;</tt>' + text
        if task.due is not None:
            text = text.replace('due:%s' % task.due, self._htmlizeDueDate(task.due))
        if task.threshold is not None:
            text = text.replace('t:%s' % task.threshold, self._htmlizeThresholdDate(task.threshold))
        text = self._htmlizeCreatedCompleted(text, task.text)
        text = self._htmlizeURL(text)
        if selected:
            return '<font color="white">%s</font>' % text
        else:
            return '<font color="black">%s</font>' % text

    def _htmlizeContext(self, context):
        return '<font color="green">@%s</font>' % context

    def _htmlizeProject(self, project):
        return '<font style="color:#64AAD0">+%s</font>' % project

    def _htmlizePriority(self, priority):
        if priority in self.priority_colors:
            color = self.priority_colors[priority]
            return '<font color="%s"><tt>&nbsp;%s&nbsp;</tt></font>' % (color, priority)
        return '<tt>&nbsp;%s&nbsp;</tt>' % priority

    def _htmlizeDueDate(self, dueDateString):
        try:
            due_date = datetime.strptime(dueDateString, '%Y-%m-%d').date()
        except ValueError:
            return '<b><font style="color:red">*** Invalid date format, expected: YYYY-mm-dd! due:%s ***</font></b>' \
                   % dueDateString
        date_now = date.today()
        tdelta = due_date - date_now
        if tdelta.days > 7:
            return '<b>due:%s</b>' % dueDateString
        elif tdelta.days > 0:
            return '<b><font color="orange">due:%s</font></b>' % dueDateString
        else:
            return '<b><font style="color:red">due:%s</font></b>' % dueDateString

    def _htmlizeThresholdDate(self, thresholdDateString):
        try:
            threshold_date = datetime.strptime(thresholdDateString, '%Y-%m-%d').date()
        except ValueError:
            return '<b><font style="color:red">*** Invalid date format, expected: YYYY-mm-dd! t:%s ***</font></b>' \
                   % thresholdDateString
        date_now = date.today()
        tdelta = threshold_date - date_now
        if tdelta.days > 0:
            return '<i><font style="color:grey">t:%s</font></i>' % thresholdDateString
        else:
            return '<font style="color:orange">t:%s</font>' % thresholdDateString

    def _htmlizeURL(self, text):
        regex = re.compile(
            r'((?:http|ftp)s?://'  # TODO what else is supported by xgd-open?
            #TODO add support for user:password@-scheme
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
            r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+))(\s)', re.IGNORECASE)
        return regex.sub(r'<a href="\1">\1</a>\2', text)

    def _htmlizeCreatedCompleted(self, text, raw_text):
        created = ''
        completed = ''
        match = re.match(self.regex, raw_text)
        if match.group("completed"):
            completed = match.group("completed")
            text = text.replace(completed, '', 1)
        if match.group("created"):
            created = match.group("created")
            text = text.replace(created, '', 1)
        if created or completed:
            first = True
            text += ' <font color="gray">('
            if created:
                text += created.rstrip()
                first = False
            if completed:
                if not first:
                    text += ', '
                text += 'completed: %s' % completed.rstrip()
            text = text + ')</font>'

        return text


########NEW FILE########
__FILENAME__ = todolib
import re
import os
import codecs
from datetime import datetime, date

USE_LAST_FILENAME = 1
HIGHER_PRIORITY = 'A'
LOWER_PRIORITY = 'C'


class Error(Exception):
    pass


class ErrorLoadingFile(Error):

    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return self.message


class ErrorSavingFile(Error):

    def __init__(self, message, innerException=None):
        self.message = message
        self.innerException = innerException
        
    def __str__(self):
        lines = [repr(self.message)]
        if self.innerException:
            lines.append(repr(self.innerException))
        return '\n'.join(lines)    


class File(object):
    def __init__(self):
        self.newline = '\n'
        self.tasks = []
        self.filename = None
    
    def load(self, filename):
        if filename.strip() == '':
            raise Error("Trying to load a file with an empty filename.")
        self.filename = filename
        lines = self._loadLinesFromFile(filename)
        self._createTasksFromLines(lines)

    def _createTasksFromLines(self, lines):
        self.tasks = []
        for line in lines:
            task_text = line.strip()
            if task_text:
                task = Task(task_text)
                self.tasks.append(task)

    def _loadLinesFromFile(self, filename):
        lines = []
        fd = None
        try:
            fd = codecs.open(filename, 'r', 'utf-8')
            lines = fd.readlines()
            fd.close()
        except IOError as e:
            raise ErrorLoadingFile(str(e))
        finally:
            if fd:
                fd.close()
        return lines

    def save(self, filename=USE_LAST_FILENAME):
        if filename == USE_LAST_FILENAME:
            filename = self.filename
        if not filename:
            raise ErrorSavingFile("Filename is None")
        self.filename = filename
        self.tasks.sort(compareTasks)
        self._saveTasks()
        
    def _saveTasks(self):
        fd = None
        try:
            fd = open(self.filename, 'w')
            lines = [(task.text.encode('utf8') + self.newline) for task in self.tasks]
            fd.writelines(lines)
        except IOError as e:
            raise ErrorSavingFile("Error saving to file '%s'" % self.filename, e)
        finally:
            if fd:
                fd.close()
                
    def saveDoneTask(self, task):
        fdDone = None
        doneFilename = os.path.join(os.path.dirname(self.filename), 'done.txt')
        try:
            fdDone = open(doneFilename, 'a')
            fdDone.write(task.text.encode('utf8') + self.newline)
        except IOError as e:
            raise ErrorSavingFile("Error saving to file '%s'" % doneFilename, e)
        finally:
            if fdDone:
                fdDone.close()

    def getAllCompletedContexts(self):
        contexts = dict()
        for task in self.tasks:
            if task.is_complete:
                for context in task.contexts:
                    if context in contexts:
                        contexts[context] += 1
                    else:
                        contexts[context] = 1
        return contexts

    def getAllCompletedProjects(self):
        projects = dict()
        for task in self.tasks:
            if task.is_complete:
                for project in task.projects:
                    if project in projects:
                        projects[project] += 1
                    else:
                        projects[project] = 1
        return projects

    def getAllContexts(self):
        contexts = dict()
        for task in self.tasks:
            if not task.is_complete:
                for context in task.contexts:
                    if context in contexts:
                        contexts[context] += 1
                    else:
                        contexts[context] = 1
        return contexts

    def getAllProjects(self):
        projects = dict()
        for task in self.tasks:
            if not task.is_complete:
                for project in task.projects:
                    if project in projects:
                        projects[project] += 1
                    else:
                        projects[project] = 1
        return projects

    def getTasksCounters(self):
        counters = dict({'Pending': 0,
                         'Uncategorized': 0,
                         'Contexts': 0,
                         'Projects': 0,
                         'Complete': 0})
        for task in self.tasks:
            if not task.is_complete:
                counters['Pending'] += 1
                nbProjects = len(task.projects)
                nbContexts = len(task.contexts)
                if nbProjects > 0:
                    counters['Projects'] += 1
                if nbContexts > 0:
                    counters['Contexts'] += 1
                if nbContexts == 0 and nbProjects == 0:
                    counters['Uncategorized'] += 1
            else:
                counters['Complete'] += 1
        return counters    


class Task(object):
    
    def __init__(self, line):
        self.reset()
        if line:
            self.parseLine(line)
            
    def reset(self):
        self.contexts = []
        self.projects = []
        self.priority = None
        self.is_complete = False
        self.is_future = False
        self._text = ''
        self.due = None
        self.threshold = None

    def parseLine(self, line):
        words = line.split(' ')
        i = 0
        while i < len(words):
            self.parseWord(words[i], i)
            i += 1
        
        self._text = ' '.join(words)

    def parseWord(self, word, index):
        if index == 0:
            if word == 'x':
                self.is_complete = True
            elif re.search('^\([A-Z]\)$', word):
                self.priority = word[1]
        if len(word) > 1:
            if word.startswith('@'):
                self.contexts.append(word[1:])
            elif word.startswith('+'):
                self.projects.append(word[1:])
            elif word.startswith('due:'):
                self.due = word[4:]
            elif word.startswith('t:'):
                self.threshold = word[2:]
                try:
                    self.is_future = datetime.strptime(self.threshold, '%Y-%m-%d').date() > date.today()
                except ValueError:
                    self.is_future = False

    def _getText(self):
        return self._text
    
    def _setText(self, line):
        self.reset()
        if line:
            self.parseLine(line)
            
    def increasePriority(self):
        if self.priority is None:
            self.priority = LOWER_PRIORITY
            self.text = '(%s) %s' % (LOWER_PRIORITY, self.text)
        elif self.priority == HIGHER_PRIORITY:
            self.priority = None
            self.text = self.text[4:]
        else:
            newPriority = chr(ord(self.priority)-1)
            self.text = re.sub('^\(%s\) ' % self.priority, '(%s) ' % newPriority, self.text)
            self.priority = newPriority

    def decreasePriority(self):
        if self.priority is None:
            self.priority = HIGHER_PRIORITY
            self.text = '(%s) %s' % (HIGHER_PRIORITY, self.text)
        elif self.priority == LOWER_PRIORITY:
            self.text = self.text[4:]
            self.priority = None
        else:
            newPriority = chr(ord(self.priority)+1)
            self.text = re.sub('^\(%s\) ' % self.priority, '(%s) ' % newPriority, self.text)
            self.priority = newPriority
    text = property(_getText, _setText)


def compareTasks(task1, task2):
    comparison = compareTasksByCompleteness(task1, task2)
    if comparison != 0:
        return comparison
    comparison = compareTasksByPriority(task1, task2)
    if comparison != 0:
        return comparison
    return cmp(task1.text, task2.text)


def compareTasksByPriority(task1, task2):
    if task1.priority is None:
        if task2.priority is None:
            return 0
        else:
            return 1
    else:
        if task2.priority is None:
            return -1
        else:
            return cmp(task1.priority, task2.priority)


def compareTasksByCompleteness(task1, task2):
    if task1.is_complete == task2.is_complete:
        return 0
    elif task2.is_complete:
        return -1
    else:
        return 1


def filterTasks(filters, tasks):
    if None in filters:
        return tasks
    
    filteredTasks = []
    for task in tasks:
        for filter in filters:
            if filter.isMatch(task):
                filteredTasks.append(task)
                break
    return filteredTasks
########NEW FILE########
__FILENAME__ = run-coverage
import os

os.system('coverage run run-tests.py')
os.system('coverage html -d .testOutput/html')
os.system(os.path.join('.testOutput', 'html', 'index.html'))

########NEW FILE########
__FILENAME__ = run-tests
import sys
import os
import unittest
import doctest

testsdir = os.path.abspath(os.path.dirname(__file__))
root = os.path.join(testsdir, '..', '..')
sys.path.insert(0, os.path.abspath(root))

tests = unittest.defaultTestLoader.discover('.', pattern='test*.py')


def run_doctests(testsdir):
    exit_code = 0
    for filename in os.listdir(testsdir):
        fullname = os.path.join(testsdir, filename)
        if filename.endswith('.doctest'):
            print "- Running", fullname
            result = doctest.testfile(fullname, module_relative=False)
            print "  => ran {0} results, {1} failed".format(result.attempted, result.failed)
            exit_code += result.failed
        elif os.path.isdir(fullname):
            exit_code += run_doctests(fullname)

    return exit_code

if __name__ == "__main__":
    exit_code = 0

    print "========================================"
    print "Running Unittests"
    print "========================================"
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if not result.wasSuccessful():
        exit_code = 1

    print "========================================"
    print "Running Doctests"
    print "========================================"
    doctests_exit_code = run_doctests(testsdir)
    if exit_code == 0:
        exit_code = doctests_exit_code

    if exit_code == 0:
        print "========================================"
        print "Unit tests passed successfuly"
        print "========================================"
    else:
        print "========================================"
        print "Unit tests failed"
        print "========================================"

    sys.exit(exit_code)


########NEW FILE########
__FILENAME__ = test_filters_tree_controller
import unittest
from PySide import QtCore

from qtodotxt.lib import todolib
from qtodotxt.lib.filters import IncompleteTasksFilter, ContextFilter, ProjectFilter
from qtodotxt.ui.controllers import FiltersTreeController


class FakeTreeView(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.filters = []
        self.selectedFilters = []
        
    def addFilter(self, filter, number=0):
        filter.text = "%s (%d)" % (filter.text, number)
        self.filters.append(filter)
        
    def clear(self):
        self.filters = []
        
    def clearSelection(self):
        self.selectedFilters = []
        
    def selectFilter(self, filter):
        if filter not in self.selectedFilters:
            self.selectedFilters.append(filter)
            
    def getSelectedFilters(self):
        return self.selectedFilters
    
    filterSelectionChanged = QtCore.Signal()
    
    def selectAllTasksFilter(self):
        self.selectedFilters = [IncompleteTasksFilter()]
        
    def updateTopLevelTitles(self, counters):
        return
        
        
class Test(unittest.TestCase):
    
    def _createMockFile(self):
        file = todolib.File()
        file.tasks.append(todolib.Task('my task1 @context1'))
        file.tasks.append(todolib.Task('my task2 @context1 @context2'))
        file.tasks.append(todolib.Task('my task3 +project1 @context2'))
        return file
        
    def test_showFilters(self):
        # arrange
        view = FakeTreeView()
        controller = FiltersTreeController(view)
        file = self._createMockFile()
        
        # act
        controller.showFilters(file)
        
        sortedFilter = sorted(view.filters, key=lambda filter: filter.text)
        
        # assert
        self.assertEqual(1, len(view.selectedFilters),
                         'There should be only 1 selected filter (actual: %s)' % view.selectedFilters)
        self.assertIsInstance(view.selectedFilters[0], IncompleteTasksFilter,
                              'selected filter #1 should be instance of IncompleteTasksFilter (actual: %s)'
                              % view.selectedFilters[0])
        
        self.assertEqual(3, len(view.filters), 'There should be 3 filters (actual: %d)' % len(view.filters))
        filter = sortedFilter[0]
        self.assertIsInstance(filter, ContextFilter,
                              'Filter #1 should be instance of ContextFilter (actual: %s)' % str(type(filter)))
        self.assertEqual(filter.text, 'context1 (2)',
                         'Filter #1 text should be "context1" (actual: "%s")' % filter.text)

        filter = sortedFilter[1]
        self.assertIsInstance(filter, ContextFilter,
                              'Filter #2 should be instance of ContextFilter (actual: %s)' % str(type(filter)))
        self.assertEqual(filter.text, 'context2 (2)',
                         'Filter #2 text should be "%s" (actual: context2)' % filter.text)
        
        filter = sortedFilter[2]
        self.assertIsInstance(filter, ProjectFilter,
                              'Filter #2 should be instance of ProjectFilter (actual: %s)' % str(type(filter)))
        self.assertEqual(filter.text, 'project1 (1)', 'Filter #2 text should be "%s" (actual: project1)' % filter.text)
        
    def test_showFilters_afterAddingNewContext(self):
        # arrange
        view = FakeTreeView()
        controller = FiltersTreeController(view)
        file = self._createMockFile()
        controller.showFilters(file)
        original_filter0 = view.filters[0]
        view.clearSelection()
        view.selectFilter(view.filters[0])
        file.tasks[2].text += " @context3"
        
        # act
        controller.showFilters(file)
        
        # assert
        self.assertNotEqual(view.filters[0], original_filter0,
                            'A new filter was not created (expected: %s, actual: %s)' %
                            (view.filters[0], original_filter0))

        # self.assertNotEqual(view.selectedFilters[0], original_filter0, 
        #    'The old selected filter is still selected (expected: %s, actual: %s)' % 
        #        (view.selectedFilters[0], original_filter0))
        
        self.assertEquals(
            4, len(view.filters),
            'There should be 4 filters (actual: %s)' % view.selectedFilters)

        sortedFilter = sorted(view.filters, key=lambda filter: filter.text)

        filter1_text = sortedFilter[0].text
        self.assertEqual("context1 (2)", filter1_text,
                         'Filter #1 context should be "context1 (2)" (actual: "%s")' % filter1_text)

        self.assertEquals(
            1, len(view.selectedFilters),
            'There should be 1 selected filters (actual: %s)' % view.selectedFilters)
        
        expectedSelectedFilters = [sortedFilter[1]]
        self.assertSequenceEqual(
            expectedSelectedFilters,
            view.selectedFilters,
            'Wrong selected filters (expected: %s, actual: %s)' % 
            (str(expectedSelectedFilters), view.selectedFilters))
########NEW FILE########
__FILENAME__ = filters_tree_controller
from PySide import QtCore
from qtodotxt.lib.filters import ContextFilter, ProjectFilter

# class IFiltersTreeView(object):
#    def addFilter(self, filter): pass
#    def clear(self): pass
#    def clearSelection(self): pass
#    def selectFilter(self, filter): pass
#    def getSelectedFilters(self): pass
#    filterSelectionChanged = QtCore.Signal()
#    def selectAllTasksFilter(self): pass    


class FiltersTreeController(QtCore.QObject):
    
    filterSelectionChanged = QtCore.Signal(list)
    
    def __init__(self, view):
        QtCore.QObject.__init__(self)
        self._view = view
        self._view.filterSelectionChanged.connect(self._view_filterSelectionChanged)
        self._is_showing_filters = False
        
    def _view_filterSelectionChanged(self, filters):
        if not self._is_showing_filters:
            self.filterSelectionChanged.emit(filters)
        
    def showFilters(self, file):
        self._is_showing_filters = True
        previouslySelectedFilters = self._view.getSelectedFilters()
        self._view.clearSelection()
        self._view.clear()
        self._addAllContexts(file)
        self._addAllProjects(file)
        self._updateCounter(file)
        self._is_showing_filters = False
        self._reselect(previouslySelectedFilters)

    def _updateCounter(self, file):
        rootCounters = file.getTasksCounters()
        self._view.updateTopLevelTitles(rootCounters)

    def _addAllContexts(self, file):
        contexts = file.getAllContexts()
        for context, number in contexts.iteritems():
            filter = ContextFilter(context)
            self._view.addFilter(filter, number)

    def _addAllProjects(self, file):
        projects = file.getAllProjects()
        for project, number in projects.iteritems():
            filter = ProjectFilter(project)
            self._view.addFilter(filter, number)
        
    def _reselect(self, previouslySelectedFilters):
        for filter in previouslySelectedFilters:
            self._view.selectFilter(filter)
        if not self._view.getSelectedFilters():
            self._view.selectAllTasksFilter()
########NEW FILE########
__FILENAME__ = main_controller
import os
import sys
import argparse

from PySide import QtCore
from PySide import QtGui

from qtodotxt.lib import todolib, settings

from tasks_list_controller import TasksListController
from filters_tree_controller import FiltersTreeController
from qtodotxt.lib.filters import SimpleTextFilter, FutureFilter
from menu_controller import MenuController

FILENAME_FILTERS = ';;'.join([
    'Text Files (*.txt)',
    'All Files (*.*)'])


class MainController(QtCore.QObject):
    def __init__(self, view, dialogs_service, task_editor_service):
        super(MainController, self).__init__()
        self._view = view
        self._dialogs_service = dialogs_service
        self._task_editor_service = task_editor_service
        self._initControllers()
        self._file = todolib.File()
        self._is_modified = False
        self._settings = settings.Settings()
        self._setIsModified(False)
        self._view.closeEventSignal.connect(self._view_onCloseEvent)
        self._args = self._parseArgs()
        timer = QtCore.QTimer(self)
        self.connect(timer, QtCore.SIGNAL("timeout()"), self.autoSave)
        timer.start(10000)

    def autoSave(self):
        if self._settings.getAutoSave():
            self.save()
        
    def _parseArgs(self):
        if len(sys.argv) > 1 and sys.argv[1].startswith('-psn'):
            del sys.argv[1]
        parser = argparse.ArgumentParser(description='QTodoTxt')
        parser.add_argument('-f', '--file', type=str, nargs=1, metavar='TEXTFILE')
        parser.add_argument('-q', '--quickadd', action='store_true',
                            help='opens the add task dialog and exit the application when done')
        return parser.parse_args()
    
    def _initControllers(self):
        self._initFiltersTree()
        self._initTasksList()
        self._initMenuBar()
        self._initFilterText()
    
    def _initMenuBar(self):
        menu = self._view.menuBar()
        self._menu_controller = MenuController(self, menu)

    def exit(self):
        self._view.close()
        sys.exit()

    def getView(self):
        return self._view
    
    def show(self):
        self._view.show()
        self._updateTitle()
        self._settings.load()
        self._updateCreatePref()
        self._updateAutoSavePref()
        self._updateAutoArchivePref()
        self._updateHideFutureTasksPref()

        filename = None
        if self._args.file:
            filename = self._args.file[0]
        else:
            filename = self._settings.getLastOpenFile()

        if filename:
            self.openFileByName(filename)

        if self._args.quickadd:
            self._tasks_list_controller.createTask()
            self.save()
            self.exit()
        
    def _initFiltersTree(self):
        controller = self._filters_tree_controller = \
            FiltersTreeController(self._view.filters_tree_view)
        controller.filterSelectionChanged.connect(
            self._onFilterSelectionChanged)

    def _onFilterSelectionChanged(self, filters):
        # First we filter with filters tree
        treeTasks = todolib.filterTasks(filters, self._file.tasks)
        # Then with our filter text
        filterText = self._view.tasks_view.filter_tasks.getText()
        tasks = todolib.filterTasks([SimpleTextFilter(filterText)], treeTasks)
        # And finally with future filter if needed
        # TODO: refactor all that filters
        if self._settings.getHideFutureTasks():
            tasks = todolib.filterTasks([FutureFilter()], tasks)
        self._tasks_list_controller.showTasks(tasks)

    def _initFilterText(self):
        self._view.tasks_view.filter_tasks.filterTextChanged.connect(
            self._onFilterTextChanged)

    def _onFilterTextChanged(self, text):
        # First we filter with filters tree
        filters = self._filters_tree_controller._view.getSelectedFilters()
        treeTasks = todolib.filterTasks(filters, self._file.tasks)
        # Then with our filter text
        tasks = todolib.filterTasks([SimpleTextFilter(text)], treeTasks)
        # And finally with future filter if needed
        # TODO: refactor all that filters
        if self._settings.getHideFutureTasks():
            tasks = todolib.filterTasks([FutureFilter()], tasks)
        self._tasks_list_controller.showTasks(tasks)
        
    def _initTasksList(self):
        controller = self._tasks_list_controller = \
            TasksListController(self._view.tasks_view.tasks_list_view, self._task_editor_service)
        
        controller.taskCreated.connect(self._tasks_list_taskCreated)
        controller.taskModified.connect(self._tasks_list_taskModified)
        controller.taskDeleted.connect(self._tasks_list_taskDeleted)
        controller.taskArchived.connect(self._tasks_list_taskArchived)

    def _tasks_list_taskDeleted(self, task):
        self._file.tasks.remove(task)
        self._onFileUpdated()

    def _tasks_list_taskCreated(self, task):
        self._file.tasks.append(task)
        self._onFileUpdated()
    
    def _tasks_list_taskModified(self, task):
        self._onFileUpdated()

    def _tasks_list_taskArchived(self, task):
        self._file.saveDoneTask(task)
        self._file.tasks.remove(task)
        self._onFileUpdated()
        
    def _onFileUpdated(self):
        self._filters_tree_controller.showFilters(self._file)
        self._task_editor_service.updateValues(self._file)
        self._setIsModified(True)

    def _canExit(self):
        if not self._is_modified:
            return True
        button = self._dialogs_service.showSaveDiscardOrCancel('Unsaved changes...')
        if button == QtGui.QMessageBox.Save:
            self.save()
            return True
        else:
            return button == QtGui.QMessageBox.Discard
        
    def _view_onCloseEvent(self, closeEvent):
        if self._canExit():
            closeEvent.accept()
        else:
            closeEvent.ignore()

    def _setIsModified(self, is_modified):
        self._is_modified = is_modified
        self._updateTitle()
        self._menu_controller.saveAction.setEnabled(is_modified)
        self._menu_controller.revertAction.setEnabled(is_modified)
        
    def save(self):
        if self._file.filename:
            self._file.save()
            self._setIsModified(False)
        else:
            (filename, ok) = \
                QtGui.QFileDialog.getSaveFileName(self._view, filter=FILENAME_FILTERS)
            if ok and filename:
                self._file.save(filename)
                self._settings.setLastOpenFile(filename)
                self._setIsModified(False)     
                
    def _updateTitle(self):
        title = 'QTodoTxt - '
        if self._file.filename:
            filename = os.path.basename(self._file.filename)
            title += filename
        else:
            title += 'Untitled'
        if self._is_modified:
            title += ' (*)'
        self._view.setWindowTitle(title)
           
    def open(self):
        (filename, ok) = \
            QtGui.QFileDialog.getOpenFileName(self._view, filter=FILENAME_FILTERS)
        
        if ok and filename:
            self.openFileByName(filename)
            
    def new(self):
        if self._canExit():
            self._openFile(todolib.File())

    def revert(self):
        if self._dialogs_service.showConfirm('Revert to saved file (and lose unsaved changes)?'):
            self.openFileByName(self._file.filename)

    def openFileByName(self, filename):
        file = todolib.File()
        try:
            file.load(filename)
        except todolib.ErrorLoadingFile as ex:
            self._dialogs_service.showError(str(ex))
            return
        self._openFile(file)
        self._settings.setLastOpenFile(filename)
        
    def _openFile(self, file):
        self._file = file
        self._setIsModified(False)
        self._filters_tree_controller.showFilters(file)
        self._task_editor_service.updateValues(file)

    def _updateCreatePref(self):
        self._menu_controller.changeCreatedDateState(bool(self._settings.getCreateDate()))

    def _updateAutoSavePref(self):
        self._menu_controller.changeAutoSaveState(bool(self._settings.getAutoSave()))
        
    def _updateAutoArchivePref(self):
        self._menu_controller.changeAutoArchiveState(bool(self._settings.getAutoArchive()))

    def _updateHideFutureTasksPref(self):
        self._menu_controller.changeHideFutureTasksState(bool(self._settings.getHideFutureTasks()))

    def createdDate(self):
        if self._settings.getCreateDate():
            self._settings.setCreateDate(False)
        else:
            self._settings.setCreateDate(True)

    def toggleAutoSave(self):
        if self._settings.getAutoSave():
            self._settings.setAutoSave(False)
        else:
            self._settings.setAutoSave(True)
            
    def toggleAutoArchive(self):
        if self._settings.getAutoArchive():
            self._settings.setAutoArchive(False)
        else:
            self._settings.setAutoArchive(True)

    def toggleHideFutureTasks(self):
        if self._settings.getHideFutureTasks():
            self._settings.setHideFutureTasks(False)
        else:
            self._settings.setHideFutureTasks(True)
        self._onFilterSelectionChanged(self._filters_tree_controller._view.getSelectedFilters())

    def toggleVisible(self):
        if self._view.isMinimized():
            self._view.showNormal()
            self._view.activateWindow()
        else:
            self._view.showMinimized()


########NEW FILE########
__FILENAME__ = menu_controller
from PySide import QtCore
from PySide import QtGui

from qtodotxt.ui.resource_manager import getIcon
from qtodotxt.ui.views import about_view


class MenuController(QtCore.QObject):
    def __init__(self, main_controller, menu):
        super(MenuController, self).__init__()
        self._main_controller = main_controller
        self._menu = menu
        self._initMenuBar()
            
    def _initMenuBar(self):
        self._initFileMenu()
        self._initEditMenu()
        self._initHelpMenu()
        
    def _initFileMenu(self):
        fileMenu = self._menu.addMenu('&File')
        fileMenu.addAction(self._createNewAction())     
        fileMenu.addAction(self._createOpenAction())        
        fileMenu.addAction(self._createSaveAction())
        fileMenu.addAction(self._createRevertAction())
        fileMenu.addSeparator()
        preferenceMenu = fileMenu.addMenu(getIcon('wrench.png'), '&Preferences')
        preferenceMenu.addAction(self._createPreferenceAction())
        preferenceMenu.addAction(self._autoSavePreferenceAction())
        preferenceMenu.addAction(self._autoArchivePreferenceAction())
        preferenceMenu.addAction(self._hideFutureTasksAction())
        fileMenu.addSeparator()
        fileMenu.addAction(self._createExitAction())
     
    def _initEditMenu(self):
        editMenu = self._menu.addMenu('&Edit')
        tlc = self._main_controller._tasks_list_controller
        editMenu.addAction(tlc.createTaskAction)
        editMenu.addAction(tlc.deleteSelectedTasksAction)
        editMenu.addAction(tlc.completeSelectedTasksAction)
        editMenu.addAction(tlc.decreasePrioritySelectedTasksAction)
        editMenu.addAction(tlc.increasePrioritySelectedTasksAction)
        
    def _initHelpMenu(self):
        helpMenu = self._menu.addMenu('&Help')
        helpMenu.addAction(self._createAboutAction())
        
    def _createAboutAction(self):
        action = QtGui.QAction(getIcon('help.png'), '&About', self)
        action.triggered.connect(self._about)
        return action
    
    def _about(self):
        about_view.show(self._menu)
        
    def _createNewAction(self):
        action = QtGui.QAction(getIcon('page.png'), '&New', self)
        # infrequent action, I prefer to use ctrl+n for new task.
        action.setShortcuts(["Ctrl+Shift+N"])
        action.triggered.connect(self._main_controller.new)
        return action
    
    def _createOpenAction(self):
        action = QtGui.QAction(getIcon('folder.png'), '&Open', self)
        action.setShortcuts(["Ctrl+O"])
        action.triggered.connect(self._main_controller.open)
        return action

    def _createSaveAction(self):
        action = QtGui.QAction(getIcon('disk.png'), '&Save', self)
        action.setShortcuts(["Ctrl+S"])
        action.triggered.connect(self._main_controller.save)
        self.saveAction = action
        return action

    def _createRevertAction(self):
        action = QtGui.QAction(getIcon('arrow_rotate_clockwise.png'), '&Revert', self)
        action.triggered.connect(self._main_controller.revert)
        self.revertAction = action
        return action

    def _createPreferenceAction(self):
        action = QtGui.QAction('Add created date', self, checkable=True)
        action.triggered.connect(self._main_controller.createdDate)
        self.prefAction = action
        return action
        
    def _autoSavePreferenceAction(self):
        action = QtGui.QAction('Enable auto save', self, checkable=True)
        action.triggered.connect(self._main_controller.toggleAutoSave)
        self.autoSaveAction = action
        return action

    def _autoArchivePreferenceAction(self):
        action = QtGui.QAction('Enable auto archive', self, checkable=True)
        action.triggered.connect(self._main_controller.toggleAutoArchive)
        self.autoArchiveAction = action
        return action

    def _hideFutureTasksAction(self):
        action = QtGui.QAction('Hide future tasks', self, checkable=True)
        action.triggered.connect(self._main_controller.toggleHideFutureTasks)
        self.hideFutureTasksAction = action
        return action

    def changeAutoSaveState(self, value=False):
        self.autoSaveAction.setChecked(value)
        
    def changeCreatedDateState(self, value=False):
        self.prefAction.setChecked(value)
        
    def changeAutoArchiveState(self, value=False):
        self.autoArchiveAction.setChecked(value)

    def changeHideFutureTasksState(self, value=False):
        self.hideFutureTasksAction.setChecked(value)

    def _createExitAction(self):
        action = QtGui.QAction(getIcon('door_in.png'), 'E&xit', self)
        action.setShortcuts(["Alt+F4"])
        action.triggered.connect(self._main_controller.exit)
        return action
########NEW FILE########
__FILENAME__ = tasks_list_controller
from PySide import QtCore
from PySide import QtGui
from qtodotxt.lib import todolib
from qtodotxt.ui.resource_manager import getIcon
from datetime import date
from qtodotxt.ui.controls.autocomplete_inputdialog import AutoCompleteInputDialog
from qtodotxt.lib import settings


class TasksListController(QtCore.QObject):
    
    taskModified = QtCore.Signal(todolib.Task)
    taskCreated = QtCore.Signal(todolib.Task)
    taskArchived = QtCore.Signal(todolib.Task)
    taskDeleted = QtCore.Signal(todolib.Task)
    
    def __init__(self, view, task_editor_service):
        QtCore.QObject.__init__(self)
        self._view = view
        self._task_editor_service = task_editor_service
        self._view.taskActivated.connect(self.editTask)
        self._initCreateTaskAction()
        self._initDeleteSelectedTasksAction()
        self._initCompleteSelectedTasksAction()
        self._initDecreasePrioritySelectedTasksAction()
        self._initIncreasePrioritySelectedTasksAction()
        self._settings = settings.Settings()
        
    def _initCreateTaskAction(self):
        action = QtGui.QAction(getIcon('add.png'), '&Create Task', self)
        action.setShortcuts(['Insert', 'Ctrl+I', 'Ctrl+N'])
        action.triggered.connect(self.createTask)
        self._view.addListAction(action)
        self.createTaskAction = action
        
    def _initDeleteSelectedTasksAction(self):
        action = QtGui.QAction(getIcon('delete.png'), '&Delete Selected Tasks', self)
        action.setShortcut('Delete')
        action.triggered.connect(self._deleteSelectedTasks)
        self._view.addListAction(action)
        self.deleteSelectedTasksAction = action
        
    def _initCompleteSelectedTasksAction(self):
        action = QtGui.QAction(getIcon('x.png'), 'C&omplete Selected Tasks', self)
        action.setShortcuts(['x', 'c'])
        action.triggered.connect(self._completeSelectedTasks)
        self._view.addListAction(action)
        self.completeSelectedTasksAction = action
        
    def _initDecreasePrioritySelectedTasksAction(self):
        action = QtGui.QAction(getIcon('decrease.png'), 'Decrease priority', self)
        action.setShortcuts(['-', '<'])
        action.triggered.connect(self._decreasePriority)
        self._view.addListAction(action)
        self.decreasePrioritySelectedTasksAction = action
    
    def _initIncreasePrioritySelectedTasksAction(self):
        action = QtGui.QAction(getIcon('increase.png'), 'Increase priority', self)
        action.setShortcuts(['+', '>'])
        action.triggered.connect(self._increasePriority)
        self._view.addListAction(action)
        self.increasePrioritySelectedTasksAction = action

    def completeTask(self, task):
        date_string = date.today().strftime('%Y-%m-%d') 
        if not task.is_complete:
            task.text = 'x %s %s' % (date_string, task.text)
            self._settings.load()
            if self._settings.getAutoArchive():
                self.taskArchived.emit(task)
            else:
                self.taskModified.emit(task)
        
    def _completeSelectedTasks(self):
        tasks = self._view.getSelectedTasks()
        if tasks:
            if self._confirmTasksAction(tasks, 'Complete'):
                for task in tasks:
                    self.completeTask(task)
        
    def _deleteSelectedTasks(self):
        tasks = self._view.getSelectedTasks()
        if tasks:
            if self._confirmTasksAction(tasks, 'Delete'):
                for task in tasks:
                    self._view.removeTask(task)
                    self.taskDeleted.emit(task)

    def _confirmTasksAction(self, tasks, messagePrefix):
        message = None
        if len(tasks) == 1:
            message = '%s "%s"?' % (messagePrefix, tasks[0].text)
        else:
            message = '%s %d tasks?' % (messagePrefix, len(tasks))
         
        result = QtGui.QMessageBox.question(self._view, 'Confirm', message,
                                            buttons=QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                            defaultButton=QtGui.QMessageBox.Yes)
        
        return result == QtGui.QMessageBox.Yes
        
    def _decreasePriority(self):
        tasks = self._view.getSelectedTasks()
        if tasks:
            for task in tasks:
                task.decreasePriority()
                self._view.updateTask(task)
                self.taskModified.emit(task)        
    
    def _increasePriority(self):
        tasks = self._view.getSelectedTasks()
        if tasks:
            for task in tasks:
                task.increasePriority()
                self._view.updateTask(task)
                self.taskModified.emit(task)
        
    def showTasks(self, tasks):
        previouslySelectedTasks = self._view.getSelectedTasks()
        self._view.clear()
        self._sortTasks(tasks)
        for task in tasks:
            self._view.addTask(task)
        self._reselect(previouslySelectedTasks)
        
    def _reselect(self, tasks):
        for task in tasks:
            self._view.selectTaskByText(task.text)            

    def _sortTasks(self, tasks):
        tasks.sort(cmp=todolib.compareTasks)
    
    def _addCreationDate(self, text): 
        date_string = date.today().strftime('%Y-%m-%d')
        if text[:3] in self._task_editor_service._priorities:
            text = '%s %s %s' % (text[:3], date_string, text[4:])
        else:
            text = '%s %s' % (date_string, text)
        return text

    def createTask(self):
        (text, ok) = self._task_editor_service.createTask()
        if ok and text:
            self._settings.load()
            if self._settings.getCreateDate():
                text = self._addCreationDate(text)
            task = todolib.Task(text)
            self._view.addTask(task)
            self._view.clearSelection()
            self._view.selectTask(task)
            self.taskCreated.emit(task)
    
    def editTask(self, task):
        (text, ok) = self._task_editor_service.editTask(task)
        if ok and text:
            if text != task.text:
                task.text = text
                self._view.updateTask(task)
                self.taskModified.emit(task)

########NEW FILE########
__FILENAME__ = autocomplete_inputdialog
import sys
from PySide import QtGui
from autocomplete_lineedit import AutoCompleteEdit


class AutoCompleteInputDialog(QtGui.QDialog):
    def __init__(self, values, parent=None):
        super(AutoCompleteInputDialog, self).__init__(parent)
        self._initUI(values)

    def _initUI(self, values):
        self.setWindowTitle("Task Editor")
        vbox = QtGui.QVBoxLayout()

        self._label = QtGui.QLabel("Task:")
        vbox.addWidget(self._label)

        self._edit = AutoCompleteEdit(values)
        vbox.addWidget(self._edit)
        
        hbox = QtGui.QHBoxLayout()
        okButton = QtGui.QPushButton("Ok")
        okButton.clicked.connect(self.accept)
        cancelButton = QtGui.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.resize(500, 100)

    def textValue(self):
        return self._edit.text()

    def setTextValue(self, text):
        self._edit.setText(text)

    def setLabelText(self, text):
        self._label.setText(text)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    values = ['(A)', '(B)', '(C)', '@home', '@call', '@work', '+qtodotxt', '+sqlvisualizer']
    view = AutoCompleteInputDialog(values)
    view.show()
    sys.exit(app.exec_())
    
    


########NEW FILE########
__FILENAME__ = autocomplete_lineedit
from PySide import QtCore, QtGui


class AutoCompleteEdit(QtGui.QLineEdit):
    def __init__(self, model, separator=' '):
        super(AutoCompleteEdit, self).__init__()
        self._separator = separator
        self._completer = QtGui.QCompleter(model)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.connect(
            self._completer,
            QtCore.SIGNAL('activated(QString)'),
            self._insertCompletion)
        self._keysToIgnore = [QtCore.Qt.Key_Enter,
                              QtCore.Qt.Key_Return,
                              QtCore.Qt.Key_Escape,
                              QtCore.Qt.Key_Tab]

    def _insertCompletion(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        currentText = self.text()
        completionPrefixSize = len(self._completer.completionPrefix())
        textFirstPart = self.cursorPosition() - completionPrefixSize
        textLastPart = textFirstPart + completionPrefixSize
        newtext = currentText[:textFirstPart] + completion + " " + currentText[textLastPart:]
        self.setText(newtext)

    def textUnderCursor(self):
        text = self.text()
        textUnderCursor = ''
        i = self.cursorPosition() - 1
        while i >= 0 and text[i] != self._separator:
            textUnderCursor = text[i] + textUnderCursor
            i -= 1
        return textUnderCursor

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in self._keysToIgnore:
                event.ignore()
                return
        super(AutoCompleteEdit, self).keyPressEvent(event)
        completionPrefix = self.textUnderCursor()
        if completionPrefix != self._completer.completionPrefix():
            self._updateCompleterPopupItems(completionPrefix)
        if len(event.text()) > 0 and len(completionPrefix) > 0:
            if event.key() not in self._keysToIgnore:
                self._completer.complete()
        if len(completionPrefix) == 0:
            self._completer.popup().hide()

    def _updateCompleterPopupItems(self, completionPrefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(completionPrefix)
        self._completer.popup().setCurrentIndex(
            self._completer.completionModel().index(0, 0))

if __name__ == '__main__':
    def demo():
        import sys
        app = QtGui.QApplication(sys.argv)
        values = ['@call', '@bug', '+qtodotxt', '+sqlvisualizer']
        editor = AutoCompleteEdit(values)
        window = QtGui.QWidget()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(editor)
        window.setLayout(hbox)
        window.show()

        sys.exit(app.exec_())

    demo()
########NEW FILE########
__FILENAME__ = resource_manager
import os
import sys
from PySide.QtGui import QIcon


def _getRoot():
    root = ''
    if sys.argv[0].lower().endswith('.exe'):
        root = os.path.dirname(sys.argv[0])
    elif getattr(sys, 'frozen', False):
        root = os.environ['RESOURCEPATH']
    else:
        file = None
        try:
            file = __file__
        except NameError:
            file = sys.argv[0]
        root = os.path.dirname(os.path.abspath(file))
    return root


def __getResourcesRoot():
    return os.path.join(_getRoot(), 'resources')

resources_root = __getResourcesRoot()


def getResourcePath(resource_name):
    return os.path.join(resources_root, resource_name)


def getIcon(resource_name):
    return QIcon(getResourcePath(resource_name))
########NEW FILE########
__FILENAME__ = dialogs_service
from PySide import QtGui


class DialogsService(object):
    
    def __init__(self, parent_window, default_title):
        self._parent_window = parent_window
        self._default_title = default_title
        
    def showMessage(self, message, title=None):
        if not title:
            title = self._default_title
            
        QtGui.QMessageBox.information(self._parent_window, title, message)
    
    def showError(self, message, title=None):
        if not title:
            title = self._default_title + ' - Error'
            
        QtGui.QMessageBox.critical(self._parent_window, title, message)    

    def showSaveDiscardOrCancel(self, message):
        """
        Returns:
            QtGui.QMessageBox.Save or
            QtGui.QMessageBox.Discard or
            QtGui.QMessageBox.Cancel
        """
        dialog = QtGui.QMessageBox(self._parent_window)
        dialog.setWindowTitle('%s - Confirm' % self._default_title)
        dialog.setText(message)
        dialog.setStandardButtons(
            QtGui.QMessageBox.Save | 
            QtGui.QMessageBox.Discard | 
            QtGui.QMessageBox.Cancel)
        return dialog.exec_()

    def showConfirm(self, message):
        result = QtGui.QMessageBox.question(
            self._parent_window
            ,
            '%s - Confirm' % self._default_title,
            message,
            buttons=QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            defaultButton=QtGui.QMessageBox.Yes)
        
        return result == QtGui.QMessageBox.Yes

if __name__ == "__main__":
    app = QtGui.QApplication([])
    service = DialogsService(None, 'Default Title')
    service.showMessage("DialogsService.message()")
    service.showError("DialogsService.error()")
    result = service.showSaveDiscardOrCancel("Unsaved changes...")
    message = 'You clicked '
    if result == QtGui.QMessageBox.Save:
        message += '"Save"'
    elif result == QtGui.QMessageBox.Discard:
        message += '"Discard"'
    else:
        message += '"Cancel"'
    service.showMessage(message)
    service.showConfirm('Sure?')
########NEW FILE########
__FILENAME__ = task_editor_service
from qtodotxt.ui.controls.autocomplete_inputdialog import AutoCompleteInputDialog


class TaskEditorService(object):
    def __init__(self, parent_window):
        self._parent_window = parent_window
        self._priorities = ['(A)', '(B)', '(C)']
        self._resetValues()

    def _resetValues(self):
        self._values = []
        self._completedValues = []
        self._values.extend(self._priorities)

    def updateTodoValues(self, file):
        contexts = file.getAllContexts()
        projects = file.getAllProjects()
        for context in contexts:
            self._values.append('@' + context)
        for project in projects:
            self._values.append('+' + project)

    def updateCompletedValues(self, file):
        contexts = file.getAllCompletedContexts()
        projects = file.getAllCompletedProjects()
        for context in contexts:
            self._completedValues.append('@' + context)
        for project in projects:
            self._completedValues.append('+' + project)

    def updateValues(self, file):
        self._resetValues()
        self.updateTodoValues(file)
        self.updateCompletedValues(file)

    def createTask(self):
        (text, ok) = self._openTaskEditor("Create Task")
        return text, ok
    
    def editTask(self, task):
        (text, ok) = self._openTaskEditor('Edit Task', task)
        return text, ok

    def _openTaskEditor(self, title, task=None):
        uniqlist = list(set(self._completedValues+self._values))
        dialog = AutoCompleteInputDialog(uniqlist, self._parent_window)
        dialog.setWindowTitle(title)
        dialog.setLabelText('Task:')
        dialog.resize(500, 100)
        if task:
            dialog.setTextValue(task.text)
        dialog.setModal(True)
        if dialog.exec_():
            return dialog.textValue(), True
        return None, False


########NEW FILE########
__FILENAME__ = about_view
__version__ = "1.3.0"

description = """<p>QTodoTxt is a cross-platform UI client for todo.txt files
 (see <a href="http://todotxt.com">http://todotxt.com</a>)</p>

<p>Copyright &copy; David Elentok 2011</p>
<p>Copyright &copy; Matthieu Nantern 2013</p>

<h2>Links</h2>
<ul>
<li>Project Page: <a href="https://github.com/mNantern/QTodoTxt">https://github.com/mNantern/QTodoTxt</a></li>
</ul>

<h2>Credits</h2>

<ul>
    <li>Concept by <a href="http://ginatrapani.org/">Gina Trapani</a></li>
    <li>Icons by <a href="http://www.famfamfam.com/lab/icons/silk/">Mark James</a>
        and <a href="http://sekkyumu.deviantart.com/art/Developpers-Icons-63052312">Sekkyumu</a></li>
    <li>Original code by <a href="http://elentok.blogspot.com">David Elentok</a></li>
</ul>

<h2>License</h2>

<p>This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.</p>

<p>This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.</p>

<p>You should have received a copy of the GNU General Public License
along with this program.  If not, see 
&lt;<a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>&gt;.</p>
"""

from PySide import QtGui


def _getAboutText():
    parts = ["<h1>About QTodoTxt %s</h1>\n" % __version__, description]
    return ''.join(parts)


def show(parent=None):
    text = _getAboutText()
    QtGui.QMessageBox.information(parent, 'About QTodoTxt', text)

########NEW FILE########
__FILENAME__ = filters_tree_view
from PySide import QtCore
from PySide import QtGui
from qtodotxt.lib.filters import *
from qtodotxt.ui.resource_manager import getIcon


class FiltersTreeView(QtGui.QWidget):
    
    filterSelectionChanged = QtCore.Signal(list)
    
    def __init__(self, parent=None):
        super(FiltersTreeView, self).__init__(parent)
        self._filterItemByFilterType = dict()
        self._filterIconByFilterType = dict()
        self._treeItemByFilterType = dict()
        self._initUI()

    def getSelectedFilters(self):
        items = self._tree.selectedItems()
        filters = [item.filter for item in items]
        return filters

    def clear(self):
        self._tree.clear()
        self._addDefaultTreeItems(self._tree)
        self._initFilterTypeMappings()

    def clearSelection(self):
        self._tree.clearSelection()

    def addFilter(self, filter, number=0):
        parentItem = self._filterItemByFilterType[type(filter)]
        icon = self._filterIconByFilterType[type(filter)]
        FilterTreeWidgetItem(parentItem, ["%s (%d)" % (filter.text, number)], filter=filter, icon=icon)
        parentItem.setExpanded(True)
        parentItem.sortChildren(0, QtCore.Qt.AscendingOrder)
            
    def updateTopLevelTitles(self, counters):
        nbPending = counters['Pending']
        nbUncategorized = counters['Uncategorized']
        nbContexts = counters['Contexts']
        nbProjects = counters['Projects']
        nbComplete = counters['Complete']
        self._incompleteTasksItem.setText(0, "Pending (%d)" % nbPending)
        self._uncategorizedTasksItem.setText(0, "Uncategorized (%d)" % nbUncategorized)
        self._contextsItem.setText(0, "Contexts (%d)" % nbContexts)
        self._projectsItem.setText(0, "Projects (%d)" % nbProjects)
        self._completeTasksItem.setText(0, "Complete (%d)" % nbComplete)
        
    def selectAllTasksFilter(self):
        self._incompleteTasksItem.setSelected(True)

    def _selectItem(self, item):
        if item:
            item.setSelected(True)
            self._tree.setCurrentItem(item)        

    def _selectContext(self, context):
        item = self._findItem(context, self._contextsItem)
        self._selectItem(item)
              
    def _selectProject(self, project):
        item = self._findItem(project, self._projectsItem)
        self._selectItem(item)

    def _findItem(self, text, parentItem):
        for index in range(parentItem.childCount()):
            child = parentItem.child(index)
            #Remove counter on the tree: context (3) for example
            childText = child.text(0).rpartition(' ')[0]
            if childText == text:
                return child
        return None

    def _initUI(self):
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        self._tree = self._createTreeWidget()
        layout.addWidget(self._tree)

    def _createTreeWidget(self):
        tree = QtGui.QTreeWidget()
        tree.header().hide()
        tree.setSelectionMode(
            QtGui.QAbstractItemView.SelectionMode.ExtendedSelection)
        tree.itemSelectionChanged.connect(self._tree_itemSelectionChanged)
        self._addDefaultTreeItems(tree)
        self._initFilterTypeMappings()
        return tree
        
    def _addDefaultTreeItems(self, tree):
        self._incompleteTasksItem = \
            FilterTreeWidgetItem(None, ['Pending'], IncompleteTasksFilter(), getIcon('time.png'))
        self._uncategorizedTasksItem = \
            FilterTreeWidgetItem(None, ['Uncategorized'], UncategorizedTasksFilter(), getIcon('help.png'))
        self._contextsItem = \
            FilterTreeWidgetItem(None, ['Contexts'], HasContextsFilter(), getIcon('at.png'))
        self._projectsItem = \
            FilterTreeWidgetItem(None, ['Projects'], HasProjectsFilter(), getIcon('plus.png'))
        self._completeTasksItem = \
            FilterTreeWidgetItem(None, ['Complete'], CompleteTasksFilter(), getIcon('x.png'))
        tree.addTopLevelItems([
            self._incompleteTasksItem,
            self._uncategorizedTasksItem,
            self._contextsItem,
            self._projectsItem,
            self._completeTasksItem])
        
    def _initFilterTypeMappings(self):
        self._filterItemByFilterType[ContextFilter] = self._contextsItem
        self._filterItemByFilterType[ProjectFilter] = self._projectsItem
        self._filterIconByFilterType[ContextFilter] = getIcon('at.png')
        self._filterIconByFilterType[ProjectFilter] = getIcon('plus.png')
        self._treeItemByFilterType[IncompleteTasksFilter] = self._incompleteTasksItem
        self._treeItemByFilterType[UncategorizedTasksFilter] = self._uncategorizedTasksItem
        self._treeItemByFilterType[CompleteTasksFilter] = self._completeTasksItem
        self._treeItemByFilterType[HasProjectsFilter] = self._projectsItem
        self._treeItemByFilterType[HasContextsFilter] = self._contextsItem

    def _tree_itemSelectionChanged(self):
        self.filterSelectionChanged.emit(self.getSelectedFilters())

    def selectFilter(self, filter):
        if isinstance(filter, ContextFilter):
            self._selectContext(filter.text)
        elif isinstance(filter, ProjectFilter):
            self._selectProject(filter.text)
        else:
            item = self._treeItemByFilterType[type(filter)]
            self._selectItem(item)


class FilterTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent, strings, filter=None, icon=None):
        QtGui.QTreeWidgetItem.__init__(self, parent, strings)
        self.filter = filter
        if icon:
            self.setIcon(0, icon)

########NEW FILE########
__FILENAME__ = filter_tasks_view
from PySide import QtCore, QtGui


class FilterTasksView(QtGui.QLineEdit):
    
    filterTextChanged = QtCore.Signal(unicode)
    
    def __init__(self, searchIcon, clearIcon, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        
        self._text = ""
    
        self.clearButton = QtGui.QToolButton(self)
        self.clearButton.setIcon(clearIcon)
        self.clearButton.setCursor(QtCore.Qt.ArrowCursor)
        self.clearButton.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        self.clearButton.hide()
        self.clearButton.clicked.connect(self.clear)
        self.textChanged.connect(self.updateText)
    
        self.searchButton = QtGui.QToolButton(self)
        self.searchButton.setIcon(searchIcon)
        self.searchButton.setStyleSheet("QToolButton { border: none; padding: 0px; }")
    
        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        buttonWidth = self.clearButton.sizeHint().width()
        self.setStyleSheet("QLineEdit { padding-left: %spx; padding-right: %spx; } " % (
            self.searchButton.sizeHint().width() + frameWidth + 1, buttonWidth + frameWidth + 1))
        msz = self.minimumSizeHint()
        self.setMinimumSize(max(msz.width(),
                                self.searchButton.sizeHint().width() + buttonWidth + frameWidth * 2 + 2),
                            max(msz.height(), self.clearButton.sizeHint().height() + frameWidth * 2 + 2))
        self.setPlaceholderText("filter")
        
        focusShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        focusShortcut.activated.connect(self.setFocus)

    def resizeEvent(self, event):
        sz = self.clearButton.sizeHint()
        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        self.clearButton.move(self.rect().right() - frameWidth - sz.width(),
                              (self.rect().bottom() + 1 - sz.height()) / 2)
        self.searchButton.move(self.rect().left() + 1, (self.rect().bottom() + 1 - sz.height()) / 2)

    def getText(self):
        return self._text

    def updateText(self, text):
        self._text = text
        self.filterTextChanged.emit(text)
        self.updateCloseButton(bool(text))

    def updateCloseButton(self, visible):
            self.clearButton.setVisible(visible)

########NEW FILE########
__FILENAME__ = main_view
from PySide import QtCore
from PySide import QtGui

from ..resource_manager import getIcon
from filters_tree_view import FiltersTreeView
from tasks_view import TasksView


class MainView(QtGui.QMainWindow):
    
    closeEventSignal = QtCore.Signal(QtGui.QCloseEvent)
        
    def __init__(self, parent=None):
        super(MainView, self).__init__(parent)
        self._initUI()
        
    def show(self):
        super(MainView, self).show()
    
    def _initUI(self):
        
        splitter = QtGui.QSplitter()
        
        self.filters_tree_view = FiltersTreeView(splitter)
        self.tasks_view = TasksView(splitter)
        
        self.setCentralWidget(splitter)

        self.resize(800, 400)
        splitter.setSizes([250, 550])
        self.setWindowIcon(getIcon('qtodotxt.ico'))
                
    def closeEvent(self, closeEvent):
        super(MainView, self).closeEvent(closeEvent)
        self.closeEventSignal.emit(closeEvent)

########NEW FILE########
__FILENAME__ = tasks_list_view
from PySide import QtCore
from PySide import QtGui
from qtodotxt.lib.task_htmlizer import TaskHtmlizer
from qtodotxt.lib import todolib


class TasksListView(QtGui.QListWidget):

    taskActivated = QtCore.Signal(todolib.Task)

    def __init__(self, parent=None):
        super(TasksListView, self).__init__(parent)
        self._task_htmlizer = TaskHtmlizer()
        self._initUI()
        self._oldSelected = []

    def addTask(self, task):
        item = TaskListWidgetItem(task, self)
        label = self._createLabel(task)
        self.setItemWidget(item, label)

    def addListAction(self, action):
        self.addAction(action)

    def _initUI(self):
        self.setSelectionMode(
            QtGui.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.itemDoubleClicked.connect(self._list_itemActivated)
        self.itemSelectionChanged.connect(self._list_itemPressed)

    def _createLabel(self, task):
        label = QtGui.QLabel()
        label.setTextFormat(QtCore.Qt.RichText)
        label.setOpenExternalLinks(True)
        text = self._task_htmlizer.task2html(task)
        label.setText(text)
        return label

    def _findItemByTask(self, task):
        for index in range(self.count()):
            item = self.item(index)
            if item.task == task:
                return item
        return None

    def _findItemByTaskText(self, text):
        for index in range(self.count()):
            item = self.item(index)
            if item.task.text == text:
                return item
        return None

    def updateTask(self, task):
        item = self._findItemByTask(task)
        label = self.itemWidget(item)
        text = self._task_htmlizer.task2html(item.task)
        label.setText(text)

    def _selectItem(self, item):
        if item:
            item.setSelected(True)
            self.setCurrentItem(item)

    def selectTask(self, task):
        item = self._findItemByTask(task)
        self._selectItem(item)

    def selectTaskByText(self, text):
        item = self._findItemByTaskText(text)
        self._selectItem(item)

    def removeTask(self, task):
        item = self._findItemByTask(task)
        if item:
            self._oldSelected.remove(item)
            self.removeItemWidget(item)

    def _list_itemActivated(self, item):
        self.taskActivated.emit(item.task)

    def getSelectedTasks(self):
        items = self.selectedItems()
        return [item.task for item in items]

    def _list_itemPressed(self):
        for oldSelected in self._oldSelected:
            label = self.itemWidget(oldSelected)
            text = self._task_htmlizer.task2html(oldSelected.task, False)
            label.setText(text)
        self._oldSelected = []
        items = self.selectedItems()
        for item in items:
            self._oldSelected.append(item)
            label = self.itemWidget(item)
            text = self._task_htmlizer.task2html(item.task, True)
            label.setText(text)

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return:
            items = self.selectedItems()
            if len(items) > 0:
                self._list_itemActivated(items[-1])
        else:
            QtGui.QListWidget.keyPressEvent(self, event)
            return


class TaskListWidgetItem(QtGui.QListWidgetItem):

    def __init__(self, task, list):
        QtGui.QListWidgetItem.__init__(self, '', list)
        self.task = task

########NEW FILE########
__FILENAME__ = tasks_view
from PySide import QtGui
from filter_tasks_view import FilterTasksView
from tasks_list_view import TasksListView
from qtodotxt.ui.resource_manager import getIcon


class TasksView(QtGui.QWidget):
    
    def __init__(self, parent=None):
        super(TasksView, self).__init__(parent)
        self._initUI()
        
    def _initUI(self):
        layout = QtGui.QGridLayout(self)
        layout.setSpacing(10)
        
        self.filter_tasks = FilterTasksView(getIcon("zoom.png"), getIcon("cross.png"), self)
        self.tasks_list_view = TasksListView(self)
        
        layout.addWidget(self.filter_tasks, 1, 0)
        layout.addWidget(self.tasks_list_view, 2, 0)
        self.setLayout(layout)
########NEW FILE########
__FILENAME__ = task_editor_view
import sys
from PySide import QtCore
from PySide import QtGui


class TaskEditorView(QtGui.QDialog):
    def __init__(self):
        super(TaskEditorView, self).__init__()
        self._initUI()

    def _initUI(self):
        self._edit = QtGui.QLineEdit()
        self.setWindowTitle("Task Editor")
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(QtGui.QLabel("Task:"))
        vbox.addWidget(self._edit)
        
        hbox = QtGui.QHBoxLayout()
        okButton = QtGui.QPushButton("Ok")
        cancelButton = QtGui.QPushButton("Cancel")
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.resize(500, 100)

        self._completer = QtGui.QCompleter(['+one', '+two', '+three'])
        self._edit.setCompleter(self._completer)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    view = TaskEditorView()
    view.show()
    sys.exit(app.exec_())
    
    


########NEW FILE########
