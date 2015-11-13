__FILENAME__ = config
import os
import sublime
import logging
from logging.handlers import RotatingFileHandler
import tempfile

mm_dir = os.path.dirname(__file__)
sublime_version = int(float(sublime.version()))
settings = None
merge_settings = None

logger = None

def setup_logging():
    try:
        settings = sublime.load_settings('mavensmate.sublime-settings')

        logging.raiseExceptions = False
        logging.basicConfig(level=logging.DEBUG)

        log_location = settings.get('mm_log_location', tempfile.gettempdir())
        logging_handler = RotatingFileHandler(os.path.join(log_location, "mmst.log"), maxBytes=1*1024*1024, backupCount=5)

        #mm log setup
        global logger
        logger = logging.getLogger('mmst')
        logger.setLevel(logging.DEBUG)
        logger.propagate = False 
        logger.addHandler(logging_handler)
    except:
        pass #TODO: need to handle this permission denied error (https://github.com/joeferraro/MavensMate-SublimeText/issues/293)

def debug(msg, obj=None):
    try:
        if obj != None and type(msg) is str:
            logger.debug(msg + ' ', obj)
            print('[MAVENSMATE]: ' + msg + ' ', obj)
        elif obj == None and type(msg) is str:
            logger.debug(msg)
            print('[MAVENSMATE]:',msg)
        else:
            logger.debug(msg)
            print('[MAVENSMATE]:',msg) 
    except:
        if obj != None and type(msg) is str:
            print('[MAVENSMATE]: ' + msg + ' ', obj)
        elif obj == None and type(msg) is str:
            print('[MAVENSMATE]:',msg)
        else:
            print('[MAVENSMATE]:',msg) 
       

########NEW FILE########
__FILENAME__ = install
try:
    import os
    import sys
    import shutil
    import pipes

    install_paths = {
        "darwin" : os.path.expanduser("~/Library/Application Support/Sublime Text 3/Packages/MavensMate"),
        "win32"  : os.path.join(os.environ.get('APPDATA',''), 'Sublime Text 3', 'Packages', 'MavensMate'),
        "cygwin"  : os.path.join(os.environ.get('APPDATA',''), 'Sublime Text 3', 'Packages', 'MavensMate'),
        "linux2" : os.path.expanduser("~/.config/sublime-text-3/Packages/MavensMate")
    }

    user_settings_path = {
        "darwin" : os.path.expanduser("~/Library/Application Support/Sublime Text 3/Packages/User"),
        "win32"  : os.path.join(os.environ.get('APPDATA',''), 'Sublime Text 3', 'Packages', 'User'),
        "cygwin"  : os.path.join(os.environ.get('APPDATA',''), 'Sublime Text 3', 'Packages', 'User'),
        "linux2" : os.path.expanduser("~/.config/sublime-text-3/Packages/User")
    }

    platform            = sys.platform
    install_path        = install_paths[platform]
    user_settings_path  = user_settings_path[platform]
    branch              = 'master'
    git_url             = pipes.quote('http://github.com/joeferraro/MavensMate-SublimeText.git')

    def install_from_source():
        if 'linux' in sys.platform or 'darwin' in sys.platform:
            os.system("git clone --recursive {0} {1}".format(git_url, pipes.quote(install_path)))
            os.chdir(install_path)
            try:
                os.system("git checkout -b {0} origin/{0}".format(pipes.quote(branch)))
            except:
                pass #this is inconsistent, so pass for now
            os.system("git submodule init")
            os.system("git submodule update")
        else:
            os.system('git clone --recursive {0} "{1}"'.format(git_url, install_path))
            os.chdir(install_path)
            try:
                os.system("git checkout -b {0} origin/{0}".format(branch))
            except:
                pass #this is inconsistent, so pass for now
            os.system("git submodule init")
            os.system("git submodule update")

    def install_user_settings():
        if os.path.isfile(user_settings_path+"/mavensmate.sublime-settings") == False:
            if 'linux' in sys.platform or 'darwin' in sys.platform:
                os.system("cp {0} {1}".format(
                    pipes.quote(install_path+"/mavensmate.sublime-settings"), 
                    pipes.quote(user_settings_path)
                ))
            else:
                shutil.copyfile(install_path+"/mavensmate.sublime-settings", user_settings_path)

    def uninstall():
        if 'linux' in sys.platform or 'darwin' in sys.platform:
            os.system("rm -rf {0}".format(pipes.quote(install_path)))
        else:
            #shutil.rmtree('{0}'.format(install_path))
            os.system('rmdir /S /Q \"{}\"'.format(install_path))

    def install():
        uninstall()
        install_from_source()
        install_user_settings()

    if __name__ == '__main__':
        install()
        
except Exception as e:
    print(e)
########NEW FILE########
__FILENAME__ = apex_extensions
valid_extensions = [
    'cls',
    'trigger',
    'object',
    'component',
    'page',
    'workflow',
    'labels',
    'resource',
    'scf',
    'queue',
    'reportType',
    'report',
    'dashboard',
    'layout',
    'weblink',
    'tab',
    'customApplicationComponent',
    'app',
    'letter',
    'email',
    'role',
    'group',
    'homePageComponent',
    'homePageLayout',
    'objectTranslation',
    'flow',
    'profile',
    'permissionset',
    'datacategorygroup',
    'snapshot',
    'remoteSite',
    'site',
    'sharingRules',
    'settings'
]
########NEW FILE########
__FILENAME__ = command_helper
try:
    import MavensMate.util as util
except:
    import util
    
dict = {
    'class'     : ['ApexClass',     'Apex Class'],
    'trigger'   : ['ApexTrigger',   'Apex Trigger'],
    'page'      : ['ApexPage',      'Visualforce Page'],
    'component' : ['ApexComponent', 'Visualforce Component']
}

def get_message(params, operation):
    message = 'Handling requested operation...'
    if operation == 'new_metadata':
        message = 'Creating New '+params['metadata_type']+': ' + params['params']['api_name']
    elif operation == 'synchronize':
        if 'files' in params and len(params['files'])>0:
            kind = params['files'][0]
        elif 'directories' in params and len(params['directories'])>0:
            kind = params['directories'][0]
        else:
            kind = '???'
        message = 'Synchronizing to Server: ' + kind
    elif operation == 'compile':
        if 'files' in params and len(params['files']) == 1:
            what = params['files'][0]
            if '/' in what:
                what = what.split('/')[-1]
            message = 'Compiling: ' + what
        else:
            message = 'Compiling Selected Metadata'
    elif operation == 'compile_project':
        message = 'Compiling Project' 
    elif operation == 'edit_project':
        message = 'Opening Edit Project dialog'  
    elif operation == 'unit_test':
        if 'selected' in params and len(params['selected']) == 1:
            message = "Running Apex Test for " + params['selected'][0]
        else:
            message = 'Opening Apex Test Runner'
    elif operation == 'clean_project':
        message = 'Cleaning Project'
    elif operation == 'deploy':
        message = 'Opening Deploy dialog'
    elif operation == 'execute_apex':
        message = 'Opening Execute Apex dialog'
    elif operation == 'upgrade_project':
        message = 'Your MavensMate project needs to be upgraded. Opening the upgrade UI.'    
    elif operation == 'index_apex_overlays':
        message = 'Indexing Apex Overlays'  
    elif operation == 'index_metadata':
        message = 'Indexing Metadata'  
    elif operation == 'delete':
        if 'files' in params and len(params['files']) == 1:
            what = params['files'][0]
            if '/' in what:
                what = what.split('/')[-1]
            message = 'Deleting: ' + what
        else:
            message = 'Deleting Selected Metadata'
    elif operation == 'refresh':
        if 'files' in params and len(params['files']) == 1:
            what = params['files'][0]
            if '/' in what:
                what = what.split('/')[-1]
            message = 'Refreshing: ' + what
        else:
            message = 'Refreshing Selected Metadata'
    elif operation == 'open_sfdc_url':
        message = 'Opening Selected Metadata'
    elif operation == 'new_apex_overlay':
        message = 'Creating Apex Overlay' 
    elif operation == 'debug_log':
        message = 'Opening debug log interface (this could take a while...)'
    elif operation == 'delete_apex_overlay':
        message = 'Deleting Apex Overlay'  
    elif operation == 'fetch_logs':
        message = 'Fetching Apex Logs (will be placed in project/debug/logs)'  
    elif operation == 'fetch_checkpoints':
        message = 'Fetching Apex Logs (will be placed in project/debug/checkpoints)'  
    elif operation == 'project_from_existing_directory':
        message = 'Opening New Project Dialog'  
    elif operation == 'index_apex':
        message = 'Indexing Project Apex Metadata'
    elif operation == 'test_async':
        if 'classes' in params and len(params['classes']) == 1:
            what = params['classes'][0]
            if '/' in what:
                what = what.split('/')[-1]
            message = 'Running Apex unit tests for: ' + what
        else:
            message = 'Running Apex unit tests for this class...'
    elif operation == 'new_quick_log':
        message = 'Setting up logs for debug users (logs can be configured in project/config/.debug)'
    elif operation == 'run_apex_script':
        message = 'Running Apex script (logs can be found in project/apex-scripts/log)'
    elif operation == 'run_all_tests':
        message = 'Running all tests...'
    return message 
########NEW FILE########
__FILENAME__ = completioncommon
"""
Copyright (c) 2012 Fredrik Ehnbom

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

   1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.

   2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.

   3. This notice may not be removed or altered from any source
   distribution.
"""
import sublime
import sublime_plugin
import re
import subprocess
import time
try:
    import Queue
except:
    import queue as Queue
import threading
import os
import os.path
import imp
import sys

def reload(mod):
    n = mod.__file__
    if n[-1] == 'c':
        n = n[:-1]
    globals()[mod.__name__] = imp.load_source(mod.__name__, n)

parsehelp = imp.load_source("parsehelp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "parsehelp.py"))
reload(parsehelp)
language_regex = re.compile("(?<=source\.)[\w+\-#]+")
member_regex = re.compile("(([a-zA-Z_]+[0-9_]*)|([\)\]])+)(\.)$")


class CompletionCommonDotComplete(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            self.view.insert(edit, region.end(), ".")
        caret = self.view.sel()[0].begin()
        line = self.view.substr(sublime.Region(self.view.word(caret-1).a, caret))
        if member_regex.search(line) != None:
            self.view.run_command("hide_auto_complete")
            sublime.set_timeout(self.delayed_complete, 1)

    def delayed_complete(self):
        self.view.run_command("auto_complete")


class CompletionCommon(object):

    def __init__(self, settingsfile, workingdir):
        self.settingsfile = settingsfile
        self.completion_proc = None
        self.completion_cmd = None
        self.data_queue = Queue.Queue()
        self.workingdir = workingdir
        self.debug = False

    def get_settings(self):
        return sublime.load_settings(self.settingsfile)

    def get_setting(self, key, default=None):
        try:
            s = sublime.active_window().active_view().settings()
            if s.has(key):
                return s.get(key)
        except:
            pass
        return self.get_settings().get(key, default)

    def expand_path(self, value, window=None, checkExists=True):
        if window == None:
            # Views can apparently be window less, in most instances getting
            # the active_window will be the right choice (for example when
            # previewing a file), but the one instance this is incorrect
            # is during Sublime Text 2 session restore. Apparently it's
            # possible for views to be windowless then too and since it's
            # possible that multiple windows are to be restored, the
            # "wrong" one for this view might be the active one and thus
            # ${project_path} will not be expanded correctly.
            #
            # This will have to remain a known documented issue unless
            # someone can think of something that should be done plugin
            # side to fix this.
            window = sublime.active_window()

        get_existing_files = \
            lambda m: [path \
                for f in window.folders() \
                for path in [os.path.join(f, m.group('file'))] \
                if checkExists and os.path.exists(path) or not checkExists
            ]
        value = re.sub(r'\${project_path:(?P<file>[^}]+)}', lambda m: len(get_existing_files(m)) > 0 and get_existing_files(m)[0] or m.group('file'), value)
        value = re.sub(r'\${env:(?P<variable>[^}]+)}', lambda m: os.getenv(m.group('variable')) if os.getenv(m.group('variable')) else "%s_NOT_SET" % m.group('variable'), value)
        value = re.sub(r'\${home}', os.getenv('HOME') if os.getenv('HOME') else "HOME_NOT_SET", value)
        value = re.sub(r'\${folder:(?P<file>[^}]+)}', lambda m: os.path.dirname(m.group('file')), value)
        value = value.replace('\\', '/')

        return value

    def get_cmd(self):
        return None

    def show_error(self, msg):
        sublime.error_message(msg)

    def __err_func(self):
        exc = self.__curr_exception
        sublime.set_timeout(lambda: self.show_error(exc), 0)
        self.__curr_exception = None

    def error_thread(self):
        try:
            err_re = re.compile(r"^(Error|Exception)(\s+caught)?:\s+")
            stack_re = re.compile(r".*\(.*\)$")
            self.__curr_exception = None
            while True:
                if self.completion_proc.poll() != None:
                    break
                line = self.completion_proc.stderr.readline().decode(sys.getdefaultencoding())
                if line:
                    line = line.strip()
                else:
                    line = ""
                if err_re.search(line):
                    self.__curr_exception = line
                elif self.__curr_exception:
                    if line != ";;--;;":
                        self.__curr_exception += "\n\t" + line
                    else:
                        self.__err_func()
                if self.debug:
                    print("stderr: %s" % (line))
        finally:
            pass

    def completion_thread(self):
        try:
            while True:
                if self.completion_proc.poll() != None:
                    break
                read = self.completion_proc.stdout.readline().strip().decode(sys.getdefaultencoding())
                if read:
                    self.data_queue.put(read)
                    if self.debug:
                        print("stdout: %s" % read)
        finally:
            #print("completion_proc: %d" % (completion_proc.poll()))
            self.data_queue.put(";;--;;")
            self.data_queue.put(";;--;;exit;;--;;")
            self.completion_cmd = None
            #print("no longer running")

    def run_completion(self, cmd, stdin=None):
        self.debug = self.get_setting("completioncommon_debug", False)
        realcmd = self.get_cmd()
        if not self.completion_proc or realcmd != self.completion_cmd or self.completion_proc.poll() != None:
            if self.completion_proc:
                if self.completion_proc.poll() == None:
                    self.completion_proc.stdin.write("-quit\n")
                while self.data_queue.get() != ";;--;;exit;;--;;":
                    continue

            self.completion_cmd = realcmd
            self.completion_proc = subprocess.Popen(
                realcmd,
                cwd=self.workingdir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
                )
            t = threading.Thread(target=self.completion_thread)
            t.start()
            t = threading.Thread(target=self.error_thread)
            t.start()
        towrite = cmd + "\n"
        if stdin:
            towrite += stdin + "\n"
        if self.debug:
            for line in towrite.split("\n"):
                print("stdin: %s" % line)
        self.completion_proc.stdin.write(towrite.encode(sys.getdefaultencoding()))
        stdout = ""
        while True:
            try:
                read = self.data_queue.get(timeout=5.0)
                if read == None:
                    # We timed out... Try forcing the process to restart
                    # which might possibly help with out of sync issues
                    self.completion_cmd = None

                if read == ";;--;;" or read == None:
                    break
                stdout += read+"\n"
            except:
                break
        return stdout

    def get_language(self, view=None):
        if view == None:
            view = sublime.active_window().active_view()
        caret = view.sel()[0].a
        scope = view.scope_name(caret).strip()
        language = language_regex.search(scope)
        if language == None:
            if scope.endswith("jsp"):
                return "jsp"
            return None
        return language.group(0)

    def is_supported_language(self, view):
        return False

    def get_packages(self, data, thispackage, type):
        return []

    def find_absolute_of_type(self, data, full_data, type, template_args=[]):
        thispackage = re.search("[ \t]*package (.*);", data)
        if thispackage is None:
            thispackage = ""
        else:
            thispackage = thispackage.group(1)
        sepchar = "$"
        if self.get_language() == "cs":
            sepchar = "+"
            thispackage = re.findall(r"\s*namespace\s+([\w\.]+)\s*{", parsehelp.remove_preprocessing(data), re.MULTILINE)
            thispackage = ".".join(thispackage)

        match = re.search(r"class %s(\s|$)" % type, full_data)
        if not match is None:
            # This type is defined in this file so figure out the nesting
            full_data = parsehelp.remove_empty_classes(parsehelp.collapse_brackets(parsehelp.remove_preprocessing(full_data[:match.start()])))
            regex = re.compile(r"\s*class\s+([^\s{]+)(?:\s|$)")
            add = ""
            for m in re.finditer(regex, full_data):
                if len(add):
                    add = "%s%s%s" % (add, sepchar, m.group(1))
                else:
                    add = m.group(1)

            if len(add):
                type = "%s%s%s" % (add, sepchar, type)
            # Class is defined in this file, return package of the file
            if len(thispackage) == 0:
                return type
            return "%s.%s" % (thispackage, type)

        packages = self.get_packages(data, thispackage, type)
        packages.append(";;--;;")

        output = self.run_completion("-findclass;;--;;%s" % (type), "\n".join(packages)).strip()
        if len(output) == 0 and "." in type:
            return self.find_absolute_of_type(data, full_data, type.replace(".", sepchar), template_args)
        return output

    def complete_class(self, absolute_classname, prefix, template_args=""):
        stdout = self.run_completion("-complete;;--;;%s;;--;;%s%s%s" % (absolute_classname, prefix, ";;--;;" if len(template_args) else "", template_args))
        stdout = stdout.split("\n")[:-1]
        members = [tuple(line.split(";;--;;")) for line in stdout]
        ret = []
        for member in members:
            if len(member) == 3:
                member = (member[0], member[1], int(member[2]))
            if member not in ret:
                ret.append(member)
        return sorted(ret, key=lambda a: a[0])

    def get_return_type(self, absolute_classname, prefix, template_args=""):
        #print(absolute_classname)
        #print(prefix)
        #print(template_args)
        stdout = self.run_completion("-returntype;;--;;%s;;--;;%s%s%s" % (absolute_classname, prefix, ";;--;;" if len(template_args) else "", template_args))
        ret = stdout.strip()
        match = re.search("(\[L)?([^;]+)", ret)
        if match:
            return match.group(2)
        return ret

    def patch_up_template(self, data, full_data, template):
        if template == None:
            return None
        ret = []
        for param in template:
            name = self.find_absolute_of_type(data, full_data, param[0], param[1])
            ret.append((name, self.patch_up_template(data, full_data, param[1])))
        return ret

    def return_completions(self, comp):
        if self.get_setting("completioncommon_inhibit_sublime_completions", True):
            return (comp, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        return comp

    def is_static(self, mod):
        return (mod&(1<<0)) != 0

    def is_private(self, mod):
        return (mod&(1<<1)) != 0

    def is_protected(self, mod):
        return (mod&(1<<2)) != 0

    def is_public(self, mod):
        return (mod&(1<<3)) != 0

    def filter(self, typename, var, isstatic, data, indata):
        ret = []
        if len(indata) > 0 and len(indata[0]) == 2:
            # Filtering info not available
            return indata

        mypackage = None
        lang = self.get_language()
        if lang == "java" or lang == "jsp":
            mypackage = parsehelp.extract_package(data)
        else:
            mypackage = parsehelp.extract_namespace(data)
            if mypackage != None:
                mypackage = mypackage.replace("::", ".")
        if mypackage == None:
            mypackage = ""
        idx = typename.rfind(".")
        if idx == -1:
            idx = 0
        typepackage = typename[:idx]
        samepackage = mypackage == typepackage

        for disp, ins, mod in indata:
            public = self.is_public(mod)
            static = self.is_static(mod)
            accessible = public or (samepackage and not self.is_private(mod))

            if var == "this":
                ret.append((disp, ins))
            elif isstatic and static and accessible:
                ret.append((disp, ins))
            elif not isstatic and accessible:
                ret.append((disp, ins))
        return ret

    def on_query_completions(self, view, prefix, locations):
        bs = time.time()
        start = time.time()
        #if not self.is_supported_language(view):
        #    return []
        line = view.substr(sublime.Region(view.full_line(locations[0]).begin(), locations[0]))
        before = line
        if len(prefix) > 0:
            before = line[:-len(prefix)]
        if re.search("[ \t]+$", before):
            before = ""
        elif re.search("\.$", before):
            # Member completion
            data = view.substr(sublime.Region(0, locations[0]-len(prefix)))
            full_data = view.substr(sublime.Region(0, view.size()))
            typedef = parsehelp.get_type_definition(data)
            if typedef == None:
                return self.return_completions([])
            line, column, typename, var, tocomplete = typedef
            print('typedef: ', typedef)
            # TODO: doesn't understand arrays at the moment
            tocomplete = tocomplete.replace("[]", "")

            if typename is None:
                # This is for completing for example "System."
                # or "String." or other static calls/variables
                typename = var
                var = None
            start = time.time()
            template = parsehelp.solve_template(typename)
            if template[1]:
                template = template[1]
            else:
                template = ""
            template = self.patch_up_template(data, full_data, template)
            typename = re.sub("(<.*>)|(\[.*\])", "", typename)
            oldtypename = typename
            typename = self.find_absolute_of_type(data, full_data, typename, template)
            if typename == "":
                # Possibly a member of the current class
                clazz = parsehelp.extract_class(data)
                if clazz != None:
                    var = "this"
                    typename = self.find_absolute_of_type(data, full_data, clazz, template)
                    tocomplete = "." + oldtypename + tocomplete

            end = time.time()
            print("absolute is %s (%f ms)" % (typename, (end-start)*1000))
            if typename == "":
                return self.return_completions([])

            tocomplete = tocomplete[1:]  # skip initial .
            if len(tocomplete):
                # Just to make sure that the var isn't "this"
                # because in the end it isn't "this" we are
                # completing, but something else
                var = None

            isstatic = False
            if len(tocomplete) == 0 and var == None:
                isstatic = True
            start = time.time()
            idx = tocomplete.find(".")
            while idx != -1:
                sub = tocomplete[:idx]
                idx2 = sub.find("(")
                if idx2 >= 0:
                    sub = sub[:idx2]
                    count = 1
                    for i in range(idx+1, len(tocomplete)):
                        if tocomplete[i] == '(':
                            count += 1
                        elif tocomplete[i] == ')':
                            count -= 1
                            if count == 0:
                                idx = tocomplete.find(".", i)
                                break
                tempstring = ""
                if template:
                    for param in template:
                        if len(tempstring):
                            tempstring += ";;--;;"
                        tempstring += parsehelp.make_template(param)
                if "<" in sub and ">" in sub:
                    temp = parsehelp.solve_template(sub)
                    temp2 = self.patch_up_template(data, full_data, temp[1])
                    temp = (temp[0], temp2)
                    temp = parsehelp.make_template(temp)
                    sub = "%s%s" % (temp, sub[sub.rfind(">")+1:])

                n = self.get_return_type(typename, sub, tempstring)
                print("%s%s.%s = %s" % (typename, "<%s>" % tempstring if len(tempstring) else "", sub, n))
                if len(n) == 0:
                    return self.return_completions([])
                n = parsehelp.get_base_type(n)
                template = parsehelp.solve_template(n)
                typename = template[0]
                if self.get_language() == "cs" and len(template) == 3:
                    typename += "`%d+%s" % (len(template[1]), parsehelp.make_template(template[2]))
                template = template[1]
                tocomplete = tocomplete[idx+1:]
                idx = tocomplete.find(".")
            end = time.time()
            print("finding what to complete took %f ms" % ((end-start) * 1000))

            template_args = ""
            if template:
                for param in template:
                    if len(template_args):
                        template_args += ";;--;;"
                    template_args += parsehelp.make_template(param)

            print("completing %s%s.%s" % (typename, "<%s>" % template_args if len(template_args) else "", prefix))
            start = time.time()
            ret = self.complete_class(typename, prefix, template_args)
            ret = self.filter(typename, var, isstatic, data, ret)
            end = time.time()
            print("completion took %f ms" % ((end-start)*1000))
            be = time.time()
            print("total %f ms" % ((be-bs)*1000))
            if self.get_setting("completioncommon_shorten_names", True):
                old = ret
                ret = []
                regex = re.compile("([\\w\\.]+\\.)*")
                for display, insert in old:
                    olddisplay = display
                    display = regex.sub("", display)
                    while olddisplay != display:
                        olddisplay = display
                        display = regex.sub("", display)
                    ret.append((display, insert))
            return self.return_completions(ret)
        return []

    def on_query_context(self, view, key, operator, operand, match_all):
        print('context')
        if key == "completion_common.is_code":
            caret = view.sel()[0].a
            scope = view.scope_name(caret).strip()
            return re.search("(string.)|(comment.)", scope) == None

########NEW FILE########
__FILENAME__ = mm_interface
import sublime
import threading
import json
import pipes 
import subprocess
import os
import sys
import time
import html.parser
import re
try:
    from .threads import ThreadTracker
    from .threads import ThreadProgress
    from .threads import PanelThreadProgress
    from .printer import PanelPrinter
    from .mm_merge import MavensMateDiffThread
    import MavensMate.lib.command_helper as command_helper
    from MavensMate.lib.mm_response_handlers import MMResultHandler
    import MavensMate.util as util
    import MavensMate.config as config
except:
    from lib.threads import ThreadTracker
    from lib.threads import ThreadProgress
    from lib.threads import PanelThreadProgress
    from lib.printer import PanelPrinter
    from lib.mm_merge import MavensMateDiffThread
    import lib.command_helper as command_helper
    import util

sublime_version = int(float(sublime.version()))
settings = sublime.load_settings('mavensmate.sublime-settings')
html_parser = html.parser.HTMLParser()
debug = config.debug

#prepares and submits a threaded call to the mm executable
def call(operation, use_mm_panel=True, **kwargs):
    debug('Calling mm_interface')
    debug('OPERATION: '+operation)
    debug(kwargs)

    settings = sublime.load_settings('mavensmate.sublime-settings')
    
    if settings.get("mm_debug_mode") and not os.path.isfile(settings.get("mm_python_location")):
        active_window_id = sublime.active_window().id()
        printer = PanelPrinter.get(active_window_id)
        printer.show()
        message = '[OPERATION FAILED]: Could not find your system python install. Please set the location at mm_python_location'
        printer.write('\n'+message+'\n')
        return

    if 'darwin' in sys.platform:
        if not os.path.isfile(settings.get('mm_location')) and settings.get('mm_debug_mode') == False:
            active_window_id = sublime.active_window().id()
            printer = PanelPrinter.get(active_window_id)
            printer.show()
            message = '[OPERATION FAILED]: Could not find MavensMate.app. Download MavensMate.app from mavensmate.com and place in /Applications. Also, please ensure mm_app_location and mm_location are set properly in Sublime Text (MavensMate --> Settings --> User)'
            printer.write('\n'+message+'\n')
            return

    if 'linux' in sys.platform:
        if not os.path.isfile(settings.get('mm_subl_location')):
            active_window_id = sublime.active_window().id()
            printer = PanelPrinter.get(active_window_id)
            printer.show()
            message = '[OPERATION FAILED]: Could not locate Sublime Text "subl" executable. Please set mm_subl_location to location of "subl" on the disk.'
            printer.write('\n'+message+'\n')
            return

    if 'win32' in sys.platform:
        if not os.path.isfile(settings.get('mm_windows_subl_location')):
            active_window_id = sublime.active_window().id()
            printer = PanelPrinter.get(active_window_id)
            printer.show()
            message = '[OPERATION FAILED]: Could not locate Sublime Text. Please set mm_windows_subl_location to location of sublime_text.exe on the disk.'
            printer.write('\n'+message+'\n')
            return

    if not util.valid_workspace():
        active_window_id = sublime.active_window().id()
        printer = PanelPrinter.get(active_window_id)
        printer.show()
        message = '[OPERATION FAILED]: Please ensure mm_workspace is set to existing location(s) on your local drive'
        printer.write('\n'+message+'\n')
        return

    window, view = util.get_window_and_view_based_on_context(kwargs.get('context', None))

    #if it's a legacy project, need to intercept the call and open the upgrade ui
    #TODO: this should probably be handled in mm
    if operation != 'new_project' and operation != 'new_project_from_existing_directory' and util.is_project_legacy(window) == True:
        operation = 'upgrade_project'
    


    threads = []
    thread = MavensMateTerminalCall(
        operation, 
        project_name=util.get_project_name(window), 
        active_file=util.get_active_file(), 
        params=kwargs.get('params', None),
        context=kwargs.get('context', None),
        message=kwargs.get('message', None),
        use_mm_panel=use_mm_panel,
        process_id=util.get_random_string(10),
        mm_location=settings.get('mm_location'),
        callback=kwargs.get('callback', None)
    )
    if operation == 'index_apex':
        thread.daemon = True
    threads.append(thread)        
    thread.start()

#thread that calls out to the mm tool
#pushes to background threads and reads the piped response
class MavensMateTerminalCall(threading.Thread):
    def __init__(self, operation, **kwargs):
        self.operation      = operation #operation being requested
        self.project_name   = kwargs.get('project_name', None)
        self.active_file    = kwargs.get('active_file', None)
        self.params         = kwargs.get('params', None)
        self.context        = kwargs.get('context', None)
        self.mm_location    = kwargs.get('mm_location', None)
        self.message        = kwargs.get('message', None)
        self.view           = None
        self.window         = None
        self.printer        = None
        self.process_id     = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.use_mm_panel   = kwargs.get('use_mm_panel', False)
        self.result         = None #result of operation
        self.callback       = handle_result
        self.alt_callback   = kwargs.get('callback', None) #this is a callback requested by a command
        self.window_id      = None
        self.status_region  = None

        self.settings = sublime.load_settings('mavensmate.sublime-settings')
        self.define_sublime_context()
        self.printer = PanelPrinter.get(self.window.id())

        if self.message == None:
            self.message = command_helper.get_message(self.params, self.operation)
        
        if self.project_name == None:
            self.project_name = util.get_project_name(self.window)

        if self.use_mm_panel:
            self.printer.show()
            self.printer.writeln(' ')
            self.printer.writeln('                                                                          ')
            self.printer.writeln('Operation: '+self.message)
            self.printer.writeln('Timestamp: '+self.process_id)
            self.printer.writeln('   Result:           ')
        elif 'index' not in self.operation:
            ThreadProgress(self, self.message, 'Operation complete')

        threading.Thread.__init__(self)

    #ensures the thread has proper context (related to a specific window and/or view)
    def define_sublime_context(self):
        try:
            if isinstance(self.context, sublime.View):
                self.view = self.context
                self.window = self.view.window()
            elif isinstance(self.context, sublime.Window):
                self.window = self.context
                self.view = self.window.active_view()
            else:
                self.window = sublime.active_window()
                self.view = self.window.active_view() 
        except:
            self.window = sublime.active_window()
            self.view = self.window.active_view()

    def get_arguments(self, ui=False, html=False):
        args = {
            '-o'        : self.operation,
            '--html'    : html
        }
        if self.settings.get('mm_verbose', False):
            args['--verbose'] = True
        if sublime_version >= 3000:
            args['-c'] = 'SUBLIME_TEXT_3'
        else:
            args['-c'] = 'SUBLIME_TEXT_2'
        ui_operations = [
            'edit_project', 
            'new_project', 
            'unit_test', 
            'deploy', 
            'execute_apex', 
            'upgrade_project', 
            'new_project_from_existing_directory', 
            'debug_log', 
            'project_health_check',
            'github'
        ]
        if self.operation in ui_operations:
            args['--ui'] = True

        arg_string = []
        for x in args.keys():
            if args[x] != None and args[x] != True and args[x] != False:
                arg_string.append(x + ' ' + args[x] + ' ')
            elif args[x] == True or args[x] == None:
                arg_string.append(x + ' ')
        stripped_string = ''.join(arg_string).strip()
        return stripped_string

    def submit_payload(self, process):
        o = self.operation
        
        if o == 'new_metadata':
            # unique payload parameters
            payload = {
                'project_name'                  : self.project_name,
                'metadata_type'                 : self.params.get('metadata_type', None),
                'github_template'               : self.params.get('github_template', None),
                'params'                        : self.params.get('params', [])
            }
            workspace = util.get_project_settings().get("workspace")
            if workspace != None:
                payload['workspace'] = util.get_project_settings().get("workspace")
            else:
                payload['workspace'] = os.path.dirname(util.mm_project_directory())
        else:
            payload = {}
            
            if o != 'new_project' and o != 'new_project_from_existing_directory':
                payload['project_name'] = self.project_name
                workspace = util.get_project_settings().get("workspace")
                if workspace != None:
                    payload['workspace'] = util.get_project_settings().get("workspace")
                else:
                    payload['workspace'] = os.path.dirname(util.mm_project_directory())
        
            #open type
            if o == 'open_sfdc_url':
                payload['type'] = self.params.get('type', 'edit')
            
            if o == 'run_apex_script':
                payload['script_name'] = self.params.get('script_name', None)
                payload['return_log'] = False

            ##catch all
            if self.params != None:
                for key in self.params:
                    if key not in payload:
                        payload[key] = self.params[key]
                
        #debug('>>>>>> ',payload)    

        if type(payload) is dict:
            payload = json.dumps(payload)  
        debug(payload)  
        try:
            process.stdin.write(payload)
        except:
            process.stdin.write(payload.encode('utf-8'))
        process.stdin.close()

    def kill(self):
        #TODO: need to do some cleanup here
        ThreadTracker.set_current(self.window_id, None)

    def calculate_process_region(self):
        process_region = self.printer.panel.find(self.process_id,0)
        self.status_region = self.printer.panel.find('   Result: ',process_region.begin())

    def run(self):
        if self.use_mm_panel:
            if sys.version_info >= (3, 0):
                self.calculate_process_region()
            PanelThreadProgress(self)

        #last_thread = ThreadTracker.get_last_added(self.window)
        ThreadTracker.add(self)

        if self.settings.get('mm_debug_mode') or 'darwin' not in sys.platform:
            python_path = self.settings.get('mm_python_location')
            if 'darwin' in sys.platform or self.settings.get('mm_debug_location') != None:
                mm_loc = self.settings.get('mm_debug_location')
            else:
                mm_loc = os.path.join(config.mm_dir,"mm","mm.py") #mm.py is bundled with sublime text plugin
            
            if 'linux' in sys.platform or 'darwin' in sys.platform:
                #osx, linux
                debug('executing mm terminal call:')
                debug("{0} {1} {2}".format(python_path, pipes.quote(mm_loc), self.get_arguments()))
                process = subprocess.Popen('\'{0}\' \'{1}\' {2}'.format(python_path, mm_loc, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            else:
                #windows
                if self.settings.get('mm_debug_mode', False):
                    #user wishes to use system python
                    python_path = self.settings.get('mm_python_location')
                    process = subprocess.Popen('"{0}" "{1}" {2}'.format(python_path, mm_loc, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                else:
                    python_path = os.path.join(os.environ["ProgramFiles"],"MavensMate","App","python.exe")
                    if not os.path.isfile(python_path):
                        python_path = python_path.replace("Program Files", "Program Files (x86)")
                    debug('executing mm terminal call:')
                    debug('"{0}" -E "{1}" {2}'.format(python_path, mm_loc, self.get_arguments()))
                    process = subprocess.Popen('"{0}" -E "{1}" {2}'.format(python_path, mm_loc, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        else:
            debug('executing mm terminal call:')
            debug("{0} {1}".format(pipes.quote(self.mm_location), self.get_arguments()))
            process = subprocess.Popen("{0} {1}".format(self.mm_location, self.get_arguments()), cwd=sublime.packages_path(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        self.submit_payload(process)
        if process.stdout is not None: 
            mm_response = process.stdout.readlines()
        elif process.stderr is not None:
            mm_response = process.stderr.readlines()
        try:
            response_body = '\n'.join(mm_response)
        except:
            strs = []
            for line in mm_response:
                strs.append(line.decode('utf-8'))   
            response_body = '\n'.join(strs)

        debug('response from mm: ' + response_body)
        self.result = response_body
        if self.operation == 'compile':
            compile_callback(self, response_body)
        
        #if self.operation == 'new_apex_overlay' or self.operation == 'delete_apex_overlay':
        #    sublime.set_timeout(lambda : index_overlays(self.window), 100)
        
        #if self.callback != None:
        #    debug(self.callback)
        #    self.callback(response_body)

        if sys.version_info >= (3, 0):
            self.calculate_process_region()
            
        ThreadTracker.remove(self)

#handles the result of the mm script
def handle_result(operation, process_id, printer, res, thread):
    try:
        context = {
            "operation"      : operation,
            "process_id"     : process_id,
            "printer"        : printer,
            "result"         : res,
            "thread"         : thread
        }
        result_handler = MMResultHandler(context)
        result_handler.execute()
        #del result_handler
        sublime.set_timeout(lambda: delete_result_handler(result_handler), 5000)
    except Exception as e:
        raise e

def delete_result_handler(handler):
    del handler

def compile_callback(thread, result):
    try:
        result = json.loads(result)
        if 'success' in result and result['success'] == True:
            util.clear_marked_line_numbers(thread.view)
            #if settings.get('mm_autocomplete') == True: 
            sublime.set_timeout(lambda: index_apex_code(thread), 100)
        elif 'State' in result and result['State'] == 'Completed':
            util.clear_marked_line_numbers(thread.view)
            #if settings.get('mm_autocomplete') == True: 
            sublime.set_timeout(lambda: index_apex_code(thread), 100)
    except BaseException as e:
        debug('Issue handling compile result in callback')
        debug(e) 

def index_overlays(window):
    pending_threads = ThreadTracker.get_pending(window)
    run_index_thread = True
    for t in pending_threads:
        if t.operation == 'index_apex_overlays':
            run_index_thread = False
            break
    if run_index_thread:
        call('index_apex_overlays', False)

def index_apex_code(thread):
    pending_threads = ThreadTracker.get_pending(thread.window)
    run_index_thread = True
    for t in pending_threads:
        if t.operation == 'index_apex':
            run_index_thread = False
            break
    if run_index_thread:
        params = {
            "files" : thread.params.get('files', [])
        }
        call('index_apex', False, params=params)  

########NEW FILE########
__FILENAME__ = mm_merge
import sublime
import sublime_plugin
import difflib
import re
import os
import subprocess
import threading
from xml.dom import minidom

import MavensMate.config as config

# hack for ST3 to make module load properly
try:
    lock = __file__ + '.lock'

    if not os.path.exists(lock):
        print("forcing MavensMate Diff to reload itself")
        handle = open(lock, 'w')
        handle.write('')
        handle.close()

        handle = open(__file__, 'r')
        contents = handle.read()
        handle.close()

        handle = open(__file__, 'w')
        handle.write(contents)
        handle.close();
    else:
        os.remove(lock)
except:
    print("could not force MavensMate Diff to reload")
# end hack

mmDiffView = None

def executeShellCmd(exe, cwd):
    print ("Cmd: %s" % (exe))
    print ("Dir: %s" % (cwd))

    p = subprocess.Popen(exe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, shell=True)

    for line in p.stdout.readlines():
        line = str(line, 'utf-8')
        line = re.sub('(^\s+$)|(\s+$)', '', line)

        if line != '':
            yield line


class MavensMateDiffer():

    def process(self, line0, line1, line2):
        if line0 == None:
            return

        change = line0[0]
        line0 = line0[2:len(line0)]

        part = None

        if change == '+':
            part = {'+': line0, '-': '', 'change': '+', 'intraline': '', 'intralines': {'+': [], '-': []}}

        elif change == '-':
            part = {'-': line0, '+': '', 'change': '-', 'intraline': '', 'intralines': {'+': [], '-': []}}

        elif change == ' ':
            part = line0

        elif change == '?':
            return

        if isinstance(part, str) and (self.lastIdx in self.data) and isinstance(self.data[self.lastIdx], str):
            self.data[self.lastIdx] += part
        else:
            if isinstance(part, dict):
                if line1 and line1[0] == '?':
                    part['intraline'] = change

                if self.lastIdx >= 0:
                    last = self.data[self.lastIdx]
                else:
                    last = None

                if isinstance(last, dict):
                    skip = False

                    im_p = last['intraline'] == '-' and part['change'] == '+'
                    im_ip = last['intraline'] == '-' and part['intraline'] == '+'
                    m_ip = last['change'] == '-' and part['intraline'] == '+'

                    if im_p or im_ip or m_ip:
                        self.data[self.lastIdx]['+'] += part['+']
                        self.data[self.lastIdx]['-'] += part['-']
                        self.data[self.lastIdx]['intraline'] = '!'
                        skip = True
                    elif part['intraline'] == '' and last['intraline'] == '':
                        nextIntraline = None
                        if line2 and line2[0] == '?':
                            nextIntraline = line1[0]

                        if nextIntraline == '+' and part['change'] == '-':
                            self.data.append(part)
                            self.lastIdx += 1
                            skip = True
                        else:
                            self.data[self.lastIdx]['+'] += part['+']
                            self.data[self.lastIdx]['-'] += part['-']
                            skip = True

                    if not skip:
                        self.data.append(part)
                        self.lastIdx += 1
                else:
                    self.data.append(part)
                    self.lastIdx += 1
            else:
                self.data.append(part)
                self.lastIdx += 1

    def difference(self, text1, text2):
        self.data = []
        self.lastIdx = -1
        gen = difflib.Differ().compare(text1.splitlines(1), text2.splitlines(1))

        line0 = None
        line1 = None
        line2 = None

        try:
            line0 = gen.next()
            line1 = gen.next()
        except:
            pass

        inFor = False

        for line2 in gen:
            self.process(line0, line1, line2)
            line0 = line1
            line1 = line2
            inFor = True

        self.process(line0, line1, None)

        if not inFor:
            self.process(line1, line2, None)

        self.process(line2, None, None)

        return self.data


class MavensMateDifferScrollSync():
    left = None
    right = None
    scrollingView = None
    viewToSync = None
    lastPosLeft = None
    lastPosRight = None
    isRunning = False
    last = None
    targetPos = None

    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.sync()

    def sync(self):
        beginLeft = self.left.viewport_position()
        beginRight = self.right.viewport_position()

        if not self.isRunning:
            if beginLeft[0] != beginRight[0] or beginLeft[1] != beginRight[1]:
                if self.lastPosLeft == None or (self.lastPosLeft[0] != beginLeft[0] or self.lastPosLeft[1] != beginLeft[1]):
                    self.isRunning = True
                    self.scrollingView = self.left
                    self.viewToSync = self.right

                elif self.lastPosRight == None or (self.lastPosRight[0] != beginRight[0] or self.lastPosRight[1] != beginRight[1]):
                    self.isRunning = True
                    self.scrollingView = self.right
                    self.viewToSync = self.left

        else:
            pos = self.scrollingView.viewport_position()

            if self.targetPos == None and self.last != None and pos[0] == self.last[0] and pos[1] == self.last[1]:
                ve = self.viewToSync.viewport_extent()
                le = self.viewToSync.layout_extent()

                self.targetPos = (max(0, min(pos[0], le[0] - ve[0])), max(0, min(pos[1], le[1] - ve[1])))
                self.viewToSync.set_viewport_position(self.targetPos)

            elif self.targetPos != None:
                poss = self.viewToSync.viewport_position()

                if poss[0] == self.targetPos[0] and poss[1] == self.targetPos[1]:
                    self.isRunning = False
                    self.targetPos = None
                    self.scrollingView = None
                    self.viewToSync = None

            self.last = pos

        self.lastPosRight = beginRight
        self.lastPosLeft = beginLeft

        if self.left.window() != None and self.right.window() != None:
            sublime.set_timeout(self.sync, 100)

class MavensMateDiffViewEraseCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.erase(edit, sublime.Region(0, self.view.size()))

class MavensMateDiffViewAppend(sublime_plugin.TextCommand):
    def run(self, edit, text):
        self.view.insert(edit, self.view.size(), text)

class MavensMateDiffViewReplaceCommand(sublime_plugin.TextCommand):
    def run(self, edit, begin, end, text):
        print('running replace command!')
        self.view.replace(edit, sublime.Region(begin, end), text)

class MavensMateDiffView():
    left = None
    right = None
    origin_window = None
    window = None
    currentDiff = -1
    regions = []
    currentRegion = None
    scrollSyncRunning = False
    lastLeftPos = None
    lastRightPos = None
    diff = None
    createdPositions = False
    lastSel = {'regionLeft': None, 'regionRight': None}
    leftEnabled = True
    rightEnabled = True

    def __init__(self, window, left, right, diff, leftTmp=False, rightTmp=False):
        print('viewing diff')
        #print(window)
        #print(left)
        #print(right)
        #print(diff)
        #print(leftTmp)
        #print(rightTmp)
        self.origin_window = window
        window.run_command('new_window')
        self.window = sublime.active_window()
        self.diff = diff
        self.leftTmp = leftTmp
        self.rightTmp = rightTmp

        if (config.merge_settings.get('hide_side_bar')):
            self.window.run_command('toggle_side_bar')

        self.window.set_layout({
            "cols": [0.0, 0.5, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
        })

        if not isinstance(left, sublime.View):
            self.left = self.window.open_file(left)
            self.leftEnabled = False
        else:
            self.left = self.window.open_file(left.file_name())

        if not isinstance(right, sublime.View):
            self.right = self.window.open_file(right)
            #self.rightEnabled = False
        else:
            self.right = self.window.open_file(right.file_name())

        if not self.rightEnabled and self.rightTmp:
            self.right.set_syntax_file(self.left.settings().get('syntax'))

        if not self.leftEnabled and self.leftTmp:
            self.left.set_syntax_file(self.right.settings().get('syntax'))

        self.left.set_scratch(True)
        self.right.set_scratch(True)

        self.clear()

    def clear(self):
        if self.rightTmp and os.path.exists(self.right.file_name()):
            os.remove(self.right.file_name())

        if self.leftTmp and os.path.exists(self.left.file_name()):
            os.remove(self.left.file_name())

    def enlargeCorrespondingPart(self, part1, part2):
        linesPlus = part1.splitlines()
        linesMinus = part2.splitlines()

        diffLines = len(linesPlus) - len(linesMinus)

        if diffLines < 0:  # linesPlus < linesMinus
            for i in range(-diffLines):
                linesPlus.append('?')

        elif diffLines > 0:  # linesPlus > linesMinus
            for i in range(diffLines):
                linesMinus.append('?')

        result = []

        result.append("\n".join(linesPlus) + "\n")
        result.append("\n".join(linesMinus) + "\n")

        return result

    def loadDiff(self):
        #print('LOADING DIFF!!!!!!')
        self.window.set_view_index(self.right, 1, 0)
        sublime.set_timeout(lambda: self.insertDiffContents(self.diff), 5)

    def insertDiffContents(self, diff):
        left = self.left
        right = self.right

        # edit = left.begin_edit(0, '')
        # left.erase(edit, sublime.Region(0, left.size()))
        # left.end_edit(edit)
        left.run_command('mavens_mate_diff_view_erase')
        right.run_command('mavens_mate_diff_view_erase')
        # edit = right.begin_edit(0, '')
        # right.erase(edit, sublime.Region(0, right.size()))
        # right.end_edit(edit)

        regions = []
        i = 0

        for part in diff:
            if not isinstance(part, dict):
                left.run_command('mavens_mate_diff_view_append', {'text': part})
                right.run_command('mavens_mate_diff_view_append', {'text': part})
                # edit = left.begin_edit(0, '')
                # left.insert(edit, left.size(), part)
                # left.end_edit(edit)

                # edit = right.begin_edit(0, '')
                # right.insert(edit, right.size(), part)
                # right.end_edit(edit)
            else:
                ignore = False

                if config.merge_settings.get('ignore_whitespace'):
                    trimRe = '(^\s+)|(\s+$)'
                    #print('>>>>> START ',re.sub(trimRe, '', part['+']))
                    #print('>>>>> END ',re.sub(trimRe, '', part['-']))
                    if re.sub(trimRe, '', part['+'], flags=re.MULTILINE) == re.sub(trimRe, '', part['-'], flags=re.MULTILINE):
                        ignore = True

                if ignore:
                    # edit = left.begin_edit(0, '')
                    # left.insert(edit, left.size(), part['-'])
                    # left.end_edit(edit)
                    left.run_command('mavens_mate_diff_view_append', {'text': part['-']})
                    right.run_command('mavens_mate_diff_view_append', {'text': part['+']})
                    # edit = right.begin_edit(0, '')
                    # right.insert(edit, right.size(), part['+'])
                    # right.end_edit(edit)
                    continue

                pair = {
                    'regionLeft': None,
                    'regionRight': None,
                    'name': 'diff' + str(i),
                    'mergeLeft': part['+'][:],
                    'mergeRight': part['-'][:],
                    'intralines': {'left': [], 'right': []}
                }

                i += 1

                # edit = left.begin_edit(0, '')
                leftStart = left.size()

                if part['+'] != '' and part['-'] != '' and part['intraline'] != '':
                    inlines = list(difflib.Differ().compare(part['-'].splitlines(1), part['+'].splitlines(1)))
                    begins = {'+': 0, '-': 0}
                    lastLen = 0
                    lastChange = None

                    for inline in inlines:
                        change = inline[0:1]
                        inline = inline[2:len(inline)]
                        inlineLen = len(inline)

                        if change != '?':
                            begins[change] += inlineLen
                            lastLen = inlineLen
                            lastChange = change
                        else:
                            for m in re.finditer('([+-^]+)', inline):
                                sign = m.group(0)[0:1]

                                if sign == '^':
                                    sign = lastChange

                                start = begins[sign] - lastLen + m.start()
                                end = begins[sign] - lastLen + m.end()

                                part['intralines'][sign].append([start, end])

                enlarged = self.enlargeCorrespondingPart(part['+'], part['-'])

                # left.insert(edit, leftStart, enlarged[1])
                # left.end_edit(edit)
                left.run_command('mavens_mate_diff_view_append', {'text': enlarged[1]})

                # edit = right.begin_edit(0, '')
                rightStart = right.size()
                # right.insert(edit, rightStart, enlarged[0])
                # right.end_edit(edit)
                right.run_command('mavens_mate_diff_view_append', {'text': enlarged[0]})

                pair['regionLeft'] = sublime.Region(leftStart, leftStart + len(left.substr(sublime.Region(leftStart, left.size()))))
                pair['regionRight'] = sublime.Region(rightStart, rightStart + len(right.substr(sublime.Region(rightStart, right.size()))))

                if pair['regionLeft'] != None and pair['regionRight'] != None:
                    for position in part['intralines']['-']:
                        change = sublime.Region(leftStart + position[0], leftStart + position[1])
                        pair['intralines']['left'].append(change)

                    for position in part['intralines']['+']:
                        change = sublime.Region(rightStart + position[0], rightStart + position[1])
                        pair['intralines']['right'].append(change)

                    regions.append(pair)

        for pair in regions:
            self.createDiffRegion(pair)

        self.createdPositions = True

        self.regions = regions
        sublime.set_timeout(lambda: self.selectDiff(0), 100)  # for some reason this fixes the problem to scroll both views to proper position after loading diff

        self.left.set_read_only(True)
        self.right.set_read_only(True)
        MavensMateDifferScrollSync(self.left, self.right)

    def createDiffRegion(self, region):
        rightScope = leftScope = config.merge_settings.get('diff_region_scope')

        if region['mergeLeft'] == '':
            rightScope = config.merge_settings.get('diff_region_removed_scope')
            leftScope = config.merge_settings.get('diff_region_added_scope')
        elif region['mergeRight'] == '':
            leftScope = config.merge_settings.get('diff_region_removed_scope')
            rightScope = config.merge_settings.get('diff_region_added_scope')

        if not self.createdPositions:
            print('intralines' + region['name'], region['intralines']['left'], config.merge_settings.get('diff_region_change_scope'))
            print('intralines' + region['name'], region['intralines']['right'], config.merge_settings.get('diff_region_change_scope'))
            self.left.add_regions('intralines' + region['name'], region['intralines']['left'], config.merge_settings.get('diff_region_change_scope'))
            self.right.add_regions('intralines' + region['name'], region['intralines']['right'], config.merge_settings.get('diff_region_change_scope'))

        self.left.add_regions(region['name'], [region['regionLeft']], leftScope, config.merge_settings.get('diff_region_gutter_icon'), sublime.DRAW_OUTLINED)
        self.right.add_regions(region['name'], [region['regionRight']], rightScope, config.merge_settings.get('diff_region_gutter_icon'), sublime.DRAW_OUTLINED)

    def createSelectedRegion(self, region):
        self.left.add_regions(region['name'], [region['regionLeft']], config.merge_settings.get('selected_diff_region_scope'), config.merge_settings.get('selected_diff_region_gutter_icon'))
        self.right.add_regions(region['name'], [region['regionRight']], config.merge_settings.get('selected_diff_region_scope'), config.merge_settings.get('selected_diff_region_gutter_icon'))

    def selectDiff(self, diffIndex):
        if diffIndex >= 0 and diffIndex < len(self.regions):
            self.left.sel().clear()
            self.left.sel().add(sublime.Region(0, 0))
            self.right.sel().clear()
            self.right.sel().add(sublime.Region(0, 0))

            if self.currentRegion != None:
                self.createDiffRegion(self.currentRegion)

            self.currentRegion = self.regions[diffIndex]
            self.createSelectedRegion(self.currentRegion)

            self.currentDiff = diffIndex

            self.left.show_at_center(sublime.Region(self.currentRegion['regionLeft'].begin(), self.currentRegion['regionLeft'].begin()))
            if not config.merge_settings.get('ignore_whitespace'):  # @todo: temporary fix for loosing view sync while ignore_whitespace is true
                self.right.show_at_center(sublime.Region(self.currentRegion['regionRight'].begin(), self.currentRegion['regionRight'].begin()))

    def selectDiffUnderSelection(self, selection, side):
        if self.createdPositions:
            if selection[0].begin() == 0 and selection[0].end() == 0:  # this fixes strange behavior with regions
                return

            for i in range(len(self.regions)):
                if self.regions[i][side].contains(selection[0]):
                    self.selectDiff(i)
                    break

    def checkForClick(self, view):
        side = None

        if view.id() == self.left.id():
            side = 'regionLeft'
        elif view.id() == self.right.id():
            side = 'regionRight'

        if side != None:
            sel = [r for r in view.sel()]

            if self.lastSel[side]:
                if sel == self.lastSel[side]:  # previous selection equals current so it means this was a mouse click!
                    self.selectDiffUnderSelection(view.sel(), side)

            self.lastSel[side] = sel

    def goUp(self):
        self.selectDiff(self.currentDiff - 1)

    def goDown(self):
        self.selectDiff(self.currentDiff + 1)

    def mergeDisabled(self, direction):
        print('checking if merge is disabled: ', direction)
        print(not self.rightEnabled and direction == '>>') or (not self.leftEnabled and direction == '<<')
        return (not self.rightEnabled and direction == '>>') or (not self.leftEnabled and direction == '<<')

    def merge(self, direction, mergeAll):
        print('mm merging!', direction)
        
        target_is_server_copy = False

        if self.mergeDisabled(direction):
            return

        if mergeAll:
            print('merging all!', direction)
            while len(self.regions) > 0:
                self.merge(direction, False)
            return

        if (self.currentRegion != None):
            lenLeft = self.left.size()
            lenRight = self.right.size()
            if direction == '<<':
                source = self.right
                target = self.left
                sourceRegion = self.currentRegion['regionRight']
                targetRegion = self.currentRegion['regionLeft']
                contents = self.currentRegion['mergeLeft']

            elif direction == '>>':
                target_is_server_copy = True
                source = self.left
                target = self.right
                sourceRegion = self.currentRegion['regionLeft']
                targetRegion = self.currentRegion['regionRight']
                contents = self.currentRegion['mergeRight']

            target.set_scratch(True)

            target.set_read_only(False)
            source.set_read_only(False)

            print('about to run target command', target)
            # edit = target.begin_edit(0, '')
            # target.replace(edit, targetRegion, contents)
            # target.end_edit(edit)
            target.run_command('mavens_mate_diff_view_replace', {'begin': targetRegion.begin(), 'end': targetRegion.end(), 'text': contents})

            # edit = source.begin_edit(0, '')
            # source.replace(edit, sourceRegion, contents)
            # source.end_edit(edit)
            print('about to run source command', source)
            source.run_command('mavens_mate_diff_view_replace', {'begin': sourceRegion.begin(), 'end': sourceRegion.end(), 'text': contents})

            diffLenLeft = self.left.size() - lenLeft
            diffLenRight = self.right.size() - lenRight

            source.erase_regions(self.currentRegion['name'])
            target.erase_regions(self.currentRegion['name'])
            source.erase_regions('intralines' + self.currentRegion['name'])
            target.erase_regions('intralines' + self.currentRegion['name'])

            target.set_scratch(False)

            del self.regions[self.currentDiff]

            for i in range(self.currentDiff, len(self.regions)):
                self.regions[i]['regionLeft'] = self.moveRegionBy(self.regions[i]['regionLeft'], diffLenLeft)
                self.regions[i]['regionRight'] = self.moveRegionBy(self.regions[i]['regionRight'], diffLenRight)

                # for j in range(self.currentDiff, len(self.regions[i]['intralines']['left'])):
                #     self.regions[i]['intralines']['left'][j] = self.moveRegionBy(self.regions[i]['intralines']['left'][j], diffLenLeft)

                # for j in range(self.currentDiff, len(self.regions[i]['intralines']['right'])):
                #     self.regions[i]['intralines']['right'][j] = self.moveRegionBy(self.regions[i]['intralines']['right'][j], diffLenRight)

                if i != self.currentDiff:
                    self.createDiffRegion(self.regions[i])

            #explicitly save the "server/local copy" version (for ux purposes)
            #if target_is_server_copy:
            source.run_command("save")
            target.run_command("save")

            target.set_read_only(True)
            source.set_read_only(True)

            if self.currentDiff > len(self.regions) - 1:
                self.currentDiff = len(self.regions) - 1

            self.currentRegion = None

            if self.currentDiff >= 0:
                self.selectDiff(self.currentDiff)
            else:
                self.currentDiff = -1

            #merge is over
            if self.currentDiff == -1:
                file_name = None
                if target_is_server_copy:
                    file_name = source.file_name()
                else:
                    file_name = target.file_name()
                args = {
                    "files"     : [file_name]
                }
                self.origin_window.run_command('force_compile_file', args)
                sublime.set_timeout(lambda: self.window.run_command('close_window'), 0)

            self.window.focus_view(target)

    def moveRegionBy(self, region, by):
        return sublime.Region(region.begin() + by, region.end() + by)

    def abandonUnmergedDiffs(self, side):
        if side == 'left':
            view = self.left
            regionKey = 'regionLeft'
            contentKey = 'mergeRight'
        elif side == 'right':
            view = self.right
            regionKey = 'regionRight'
            contentKey = 'mergeLeft'

        view.set_read_only(False)
        #edit = view.begin_edit(0, '')

        for i in range(len(self.regions)):
            sizeBefore = view.size()
            #view.replace(edit, self.regions[i][regionKey], self.regions[i][contentKey])
            view.run_command('mavens_mate_diff_view_replace', {'begin': self.regions[i][regionKey].begin(), 'end': self.regions[i][regionKey].end(), 'text': self.regions[i][contentKey]})
            sizeDiff = view.size() - sizeBefore

            if sizeDiff != 0:
                for j in range(i, len(self.regions)):
                    self.regions[j][regionKey] = sublime.Region(self.regions[j][regionKey].begin() + sizeDiff, self.regions[j][regionKey].end() + sizeDiff)

        #view.end_edit(edit)
        view.set_read_only(True)


class ThreadProgress():
    def __init__(self, thread, message):
        self.th = thread
        self.msg = message
        self.add = 1
        self.size = 8
        self.speed = 100
        sublime.set_timeout(lambda: self.run(0), self.speed)

    def run(self, i):
        if not self.th.is_alive():
            if hasattr(self.th, 'result') and not self.th.result:
                sublime.status_message('')
            return

        before = i % self.size
        after = (self.size - 1) - before

        sublime.status_message('%s [%s=%s]' % (self.msg, ' ' * before, ' ' * after))

        if not after:
            self.add = -1
        if not before:
            self.add = 1

        i += self.add

        sublime.set_timeout(lambda: self.run(i), self.speed)

class MavensMateDiffThread(threading.Thread):
    def __init__(self, window, left, right, leftTmp=False, rightTmp=False):
        self.window = window
        self.left = left
        self.right = right
        self.leftTmp = leftTmp
        self.rightTmp = rightTmp

        #self.text1 = self.left.substr(sublime.Region(0, self.left.size()))

        if not isinstance(self.left, sublime.View):
            self.text1 = open(self.left, 'rb').read().decode('utf-8', 'replace')
        else:
            self.text1 = self.left.substr(sublime.Region(0, self.left.size()))
            if self.left.is_dirty():
                self.leftTmp = True

        if not isinstance(self.right, sublime.View):
            self.text2 = open(self.right, 'rb').read().decode('utf-8', 'replace')
        else:
            self.text2 = self.right.substr(sublime.Region(0, self.right.size()))
            if self.right.is_dirty():
                self.rightTmp = True

        # print('left: ', self.left)
        # print('right: ', self.right)
        # print('ltmp: ', self.leftTmp)
        # print('rtmp: ', self.rightTmp)

        threading.Thread.__init__(self)

    def run(self):
        ThreadProgress(self, 'Computing differences')

        global mmDiffView

        differs = False

        if config.merge_settings.get('ignore_crlf'):
            self.text1 = re.sub('\r\n', '\n', self.text1)
            self.text2 = re.sub('\r\n', '\n', self.text2)

            self.text1 = re.sub('\r', '\n', self.text1)
            self.text2 = re.sub('\r', '\n', self.text2)

        if config.merge_settings.get('ignore_whitespace'):
            regexp = re.compile('(^\s+)|(\s+$)', re.MULTILINE)
            if re.sub(regexp, '', self.text1) != re.sub(regexp, '', self.text2):
                differs = True
        elif self.text1 != self.text2:
            differs = True

        if not differs:
            sublime.error_message('There is no difference between files')
            if self.leftTmp and not isinstance(self.left, sublime.View):
                os.remove(self.left)
            if self.rightTmp and not isinstance(self.right, sublime.View):
                os.remove(self.right)
            
            args = {
                "files"     : [self.left.file_name()]
            }
            self.window.run_command('force_compile_file', args)
            
            return

        diff = MavensMateDiffer().difference(self.text1, self.text2)
        def inner():
            global mmDiffView
            mmDiffView = MavensMateDiffView(self.window, self.left, self.right, diff, self.leftTmp, self.rightTmp)

        sublime.set_timeout(inner, 100)

class MavensMateDiffCommand(sublime_plugin.WindowCommand):
    viewsPaths = []
    viewsList = []
    itemsList = []
    commits = []
    window = None
    view = None

    def is_enabled(self):
        view = sublime.active_window().active_view();
        if mmDiffView and  mmDiffView.left and mmDiffView.right and view and (view.id() == mmDiffView.left.id() or view.id() == mmDiffView.right.id()):
            return False
        if mmDiffView:
            return True
        else:
            return False

    def getComparableFiles(self):
        self.viewsList = []
        self.viewsPaths = []
        active = self.window.active_view()

        allViews = self.window.views()
        ratios = []
        if config.merge_settings.get('intelligent_files_sort'):
            original = os.path.split(active.file_name())

        for view in allViews:
            if view.file_name() != None and view.file_name() != active.file_name() and (not config.merge_settings.get('same_syntax_only') or view.settings().get('syntax') == active.settings().get('syntax')):
                f = view.file_name()

                ratio = 0

                if config.merge_settings.get('intelligent_files_sort'):
                    ratio = difflib.SequenceMatcher(None, original[1], os.path.split(f)[1]).ratio()

                ratios.append({'ratio': ratio, 'file': f, 'dirname': ''})

        ratiosLength = len(ratios)

        if ratiosLength > 0:
            ratios = sorted(ratios, key=self.cmp_to_key(self.sortFiles))

            if config.merge_settings.get('compact_files_list'):
                for i in range(ratiosLength):
                    for j in range(ratiosLength):
                        if i != j:
                            sp1 = os.path.split(ratios[i]['file'])
                            sp2 = os.path.split(ratios[j]['file'])

                            if sp1[1] == sp2[1]:
                                ratios[i]['dirname'] = self.getFirstDifferentDir(sp1[0], sp2[0])
                                ratios[j]['dirname'] = self.getFirstDifferentDir(sp2[0], sp1[0])

            for f in ratios:
                self.viewsPaths.append(f['file'])
                self.viewsList.append(self.prepareListItem(f['file'], f['dirname']))

            sublime.set_timeout(lambda: self.window.show_quick_panel(self.viewsList, self.onListSelect), 0) #timeout for ST3
        else:
            # if config.merge_settings.get('same_syntax_only'):
            #     syntax = re.match('(.+)\.tmLanguage$', os.path.split(active.settings().get('syntax'))[1])
            #     if syntax != None:
            #         sublime.error_message('There are no other open ' + syntax.group(1) + ' files to compare')
            #         return

            sublime.error_message('There are no other open files to compare')

    def run(self):
        self.window = sublime.active_window()
        self.active = self.window.active_view()

        if not self.active or self.active.file_name() is None:
            return

        sp = os.path.split(self.active.file_name())

        def onMenuSelect(index):
            if index == 0:
                self.getComparableFiles()

        items = ['Compare to other file...']

        if len(items) > 1:
            sublime.set_timeout(lambda: self.window.show_quick_panel(items, onMenuSelect), 0)
        else:
            self.getComparableFiles()

    def displayQuickPanel(self, commitStack, callback):
        sublime.status_message('')

        self.itemsList = []
        self.commits = []
        for item in commitStack:
            self.commits.append(item['commit'])
            itm = [item['commit'][0:10] + ' @ ' + item['date'], item['author']]
            line = ""
            if len(item['msg']) > 0:
                line = re.sub('(^\s+)|(\s+$)', '', item['msg'][0])
            
            itm.append(line)

            self.itemsList.append(itm)

        self.window.show_quick_panel(self.itemsList, callback)

    def prepareListItem(self, name, dirname):
        if config.merge_settings.get('compact_files_list'):
            sp = os.path.split(name)

            if dirname != None and dirname != '':
                dirname = ' / ' + dirname
            else:
                dirname = ''

            if (len(sp[0]) > 56):
                p1 = sp[0][0:20]
                p2 = sp[0][-36:]
                return [sp[1] + dirname, p1 + '...' + p2]
            else:
                return [sp[1] + dirname, sp[0]]
        else:
            return name

    def getFirstDifferentDir(self, a, b):
        a1 = re.split('[/\\\]', a)
        a2 = re.split('[/\\\]', b)

        len2 = len(a2) - 1

        for i in range(len(a1)):
            if i > len2 or a1[i] != a2[i]:
                return a1[i]

    def cmp_to_key(self, mycmp):
        class K(object):
            def __init__(self, obj, *args):
                self.obj = obj
            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0
            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0
            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0
            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0
            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0
            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0
        return K

    def sortFiles(self, a, b):
        d = b['ratio'] - a['ratio']

        if d == 0:
            return 0
        if d < 0:
            return -1
        if d > 0:
            return 1

    def onListSelect(self, itemIndex):
        if itemIndex > -1:
            allViews = self.window.views()
            compareTo = None
            for view in allViews:
                if (view.file_name() == self.viewsPaths[itemIndex]):
                    compareTo = view
                    break

            if compareTo != None:
                global mmDiffView

                th = MavensMateDiffThread(self.window, self.window.active_view(), compareTo)
                th.start()


class MavensMateDiffGoUpCommand(sublime_plugin.WindowCommand):
    def run(self):
        if mmDiffView != None:
            mmDiffView.goUp()

    def is_visible(self):
        view = sublime.active_window().active_view();
        if mmDiffView and mmDiffView.left and mmDiffView.right and view and (view.id() == mmDiffView.left.id() or view.id() == mmDiffView.right.id()):
            return True

        return False

    def is_enabled(self):
        return self.is_visible() and len(mmDiffView.regions) > 1 and mmDiffView.currentDiff > 0


class MavensMateDiffGoDownCommand(sublime_plugin.WindowCommand):
    def run(self):
        if mmDiffView != None:
            mmDiffView.goDown()

    def is_visible(self):
        view = sublime.active_window().active_view();
        if mmDiffView and mmDiffView.left and mmDiffView.right and view and (view.id() == mmDiffView.left.id() or view.id() == mmDiffView.right.id()):
            return True

        return False

    def is_enabled(self):
        return self.is_visible() and mmDiffView.currentDiff < len(mmDiffView.regions) - 1


class MavensMateDiffMergeLeftCommand(sublime_plugin.WindowCommand):
    def run(self, mergeAll=False):
        if mmDiffView != None:
            mmDiffView.merge('<<', mergeAll)

    def is_visible(self):
        view = sublime.active_window().active_view();
        if mmDiffView and mmDiffView.left and mmDiffView.right and view and (view.id() == mmDiffView.left.id() or view.id() == mmDiffView.right.id()) and not mmDiffView.mergeDisabled('<<'):
            return True

        return False

    def is_enabled(self):
        return self.is_visible() and len(mmDiffView.regions) > 0

class MavensMateDiffMergeRightCommand(sublime_plugin.WindowCommand):
    def run(self, mergeAll=False):
        if mmDiffView != None:
            mmDiffView.merge('>>', mergeAll)

    def is_visible(self):
        view = sublime.active_window().active_view();
        if mmDiffView and mmDiffView.left and mmDiffView.right and view and (view.id() == mmDiffView.left.id() or view.id() == mmDiffView.right.id()) and not mmDiffView.mergeDisabled('>>'):
            return True

        return False

    def is_enabled(self):
        return self.is_visible() and len(mmDiffView.regions) > 0
        
class MavensMateDiffSelectedFiles(sublime_plugin.WindowCommand):
    def run(self, files):
        allViews = self.window.views()
        for view in allViews:
            if view.file_name() == files[0]:
                files[0] = view

            if view.file_name() == files[1]:
                files[1] = view

        th = MavensMateDiffThread(self.window, files[0], files[1])
        th.start()

    def is_enabled(self, files):
        return len(files) == 2

class MavensMateDiffFromSidebar(sublime_plugin.WindowCommand):
    def is_enabled(self, files):
        return len(files) == 1

    def run(self, files):
        sublime.active_window().open_file(files[0], sublime.TRANSIENT)
        sublime.active_window().run_command('mavens_mate_diff')

class MavensMateDiffOverwriteServerCopy(sublime_plugin.WindowCommand):
    def run(self):
        if mmDiffView != None:
            args = {
                "files"     : [mmDiffView.left.file_name()]
            }
            mmDiffView.origin_window.run_command('force_compile_file', args)
            sublime.set_timeout(lambda: mmDiffView.window.run_command('close_window'), 0)

    def is_enabled(self):
        if mmDiffView == None:
            return False
        elif mmDiffView.window == None:
            return False
        else:
            return True

class MavensMateDiffListener(sublime_plugin.EventListener):
    left = None
    right = None

    def on_load(self, view):
        global mmDiffView

        if mmDiffView != None:
            if view.id() == mmDiffView.left.id():
                #print("Left file: " + view.file_name())
                self.left = view

            elif view.id() == mmDiffView.right.id():
                #print("Right file: " + view.file_name())
                self.right = view

            if self.left != None and self.right != None:
                mmDiffView.loadDiff()
                self.left = None
                self.right = None

    def on_pre_save(self, view):
        global mmDiffView

        if (mmDiffView):
            if view.id() == mmDiffView.left.id():
                mmDiffView.abandonUnmergedDiffs('left')

            elif view.id() == mmDiffView.right.id():
                mmDiffView.abandonUnmergedDiffs('right')

    def on_post_save(self, view):
        global mmDiffView

        if mmDiffView and (view.id() == mmDiffView.left.id() or view.id() == mmDiffView.right.id()):
            if mmDiffView.currentDiff == -1: #done diffing
                mmDiffView.clear()
                wnd = view.window()
                if view.id() == mmDiffView.left.id():
                    args = {
                        "files"     : [mmDiffView.left.file_name()]
                    }
                    mmDiffView.origin_window.run_command('force_compile_file', args)
                #if wnd:
                    sublime.set_timeout(lambda: wnd.run_command('close_window'), 0)

    def on_pre_close(self, view):
        global mmDiffView
        wnd = view.window()
        if mmDiffView != None:
            wnd.run_command("save_all")

    def on_close(self, view):
        global mmDiffView

        if mmDiffView != None:
            if view.id() == mmDiffView.left.id():
                mmDiffView.clear()
                wnd = mmDiffView.right.window()
                if wnd != None:
                    sublime.set_timeout(lambda: wnd.run_command('close_window'), 0)
                mmDiffView = None

            elif view.id() == mmDiffView.right.id():
                mmDiffView.clear()
                wnd = mmDiffView.left.window()
                if wnd != None:
                    sublime.set_timeout(lambda: wnd.run_command('close_window'), 0)
                mmDiffView = None

    def on_selection_modified(self, view):
        if mmDiffView:
            mmDiffView.checkForClick(view)
########NEW FILE########
__FILENAME__ = mm_response_handlers
import sublime
import threading
import json
import pipes 
import subprocess
import os
import sys
import time
import html.parser
import re
from .threads import ThreadTracker
from .threads import ThreadProgress
from .threads import PanelThreadProgress
from .printer import PanelPrinter
from .mm_merge import MavensMateDiffThread
import MavensMate.lib.command_helper as command_helper
import MavensMate.util as util
import MavensMate.config as config
sublime_version = int(float(sublime.version()))
settings = sublime.load_settings('mavensmate.sublime-settings')
html_parser = html.parser.HTMLParser()
debug = config.debug

class MMResultHandler(object):

    def __init__(self, context):
        self.operation           = context.get("operation", None)
        self.process_id          = context.get("process_id", None)
        self.printer             = context.get("printer", None)
        self.thread              = context.get("thread", None)
        self.result              = context.get("result", None)
        self.process_region      = self.printer.panel.find(self.process_id,0)
        self.status_region       = self.printer.panel.find('   Result: ',self.process_region.begin())

        self.isValidJSONResponse = True
        try:
            json_response = json.loads(self.result)
            self.result = json_response
        except:
            self.isValidJSONResponse = False

    def execute(self):
        #describe_object
        if self.result == None:
            self.__print_to_panel("[OPERATION FAILED]: No response from mm. Please enable logging (http://mavensmate.com/Plugins/Sublime_Text/Plugin_Logging) and post relevant log(s) to a new issue at https://github.com/joeferraro/MavensMate")
        else:
            try:
                if self.operation == 'compile' or self.operation == 'compile_project':
                    self.__handle_compile_response()
                elif self.operation == "test_async" or self.operation == "run_all_tests":
                    self.__handle_test_result()
                elif self.operation == "run_apex_script":
                    self.__handle_apex_script_result()
                elif self.operation == "new_metadata":
                    self.__handle_new_metadata()
                elif self.operation == "get_coverage":
                    self.__handle_coverage_result()
                elif self.operation == "coverage_report":
                    self.__handle_coverage_report_result()
                elif self.operation == "get_org_wide_test_coverage":
                    self.__handle_org_wide_coverage_result()
                else:
                    self.__handle_generic_command_result()
            except:
                self.__print_result()

            self.__finish()

    def __handle_compile_response(self, **kwargs):  
        debug("HANDLING COMPILE!")
        debug(self.result)

        #diffing with server
        if 'actions' in self.result and util.to_bool(self.result['success']) == False:
            diff_merge_settings = config.settings.get('mm_diff_server_conflicts', False)
            if diff_merge_settings:
                if sublime.ok_cancel_dialog(self.result["body"], self.result["actions"][0].title()):
                    self.__print_to_panel("Diffing with server")
                    th = MavensMateDiffThread(self.thread.window, self.thread.view, self.result['tmp_file_path'])
                    th.start()
                else:
                    self.__print_to_panel(self.result["actions"][1].title())
            else:
                if sublime.ok_cancel_dialog(self.result["body"], "Overwrite Server Copy"):
                    self.__print_to_panel("Overwriting server copy")
                    self.thread.params['action'] = 'overwrite'
                    if kwargs.get("callback", None) != None:
                        sublime.set_timeout(lambda: self.callback('compile', params=self.thread.params), 100)   
                else:
                    self.__print_to_panel(self.result["actions"][1].title())
        else:
            try:
                if 'State' in self.result and self.result['State'] == 'Error' and 'ErrorMsg' in self.result:
                    self.__print_to_panel("[OPERATION FAILED]: {0}\n\n{1}".format(self.result['ErrorMsg'], 'If you are having difficulty compiling, try toggling the mm_compile_with_tooling_api setting to \'false\' or cleaning your project.'))
                elif 'State' in self.result and self.result['State'] == 'Failed' and 'CompilerErrors' in self.result:
                    #here we're parsing a response from the tooling endpoint
                    errors = json.loads(self.result['CompilerErrors'])
                    if type(errors) is not list:
                        errors = [errors]
                    if len(errors) > 0:
                        for e in errors:
                            line_col = ""
                            line, col = 1, 1
                            if 'line' in e:
                                line = int(e['line'])
                                line_col = ' (Line: '+str(line)
                            if 'column' in e:
                                col = int(e['column'])
                                line_col += ', Column: '+str(col)
                            if len(line_col):
                                line_col += ')'

                            #scroll to the line and column of the exception
                            #if settings.get('mm_compile_scroll_to_error', True):
                            #open file, if already open it will bring it to focus
                            #view = sublime.active_window().open_file(self.thread.active_file)
                            view = self.thread.view
                            pt = view.text_point(line-1, col-1)
                            view.sel().clear()
                            view.sel().add(sublime.Region(pt))
                            view.show(pt)
                            problem = e['problem']
                            problem = html_parser.unescape(problem)
                            file_base_name = e['name']
                            #if self.thread.window.active_view().name():
                            current_active_view = sublime.active_window().active_view()
                            if current_active_view.file_name() != None:
                                current_active_view_file_name = os.path.basename(current_active_view.file_name())
                                if "." in current_active_view_file_name:
                                    current_active_view_file_name = current_active_view_file_name.split(".")[0]
                                debug(current_active_view_file_name)
                                debug(file_base_name)
                                if current_active_view_file_name != file_base_name:
                                    #this is the tooling api throwing a compile error against a different file
                                    msg = "[COMPILE FAILED]: ({0}) {1} {2}".format(file_base_name, problem, line_col)
                                    msg += "\n\nThe Tooling API has failed to compile a separate element of metadata in your current MetadataContainer. You can either:"
                                    msg += "\n1. Fix the compilation error on "+file_base_name
                                    msg += "\n2. Reset your MetadataContainer to clear this error: MavensMate > Utilities > Reset MetadataContainer"
                                    self.__print_to_panel(msg)
                                elif current_active_view_file_name == file_base_name:
                                    util.mark_line_numbers(self.thread.view, [line], "bookmark")
                                    self.__print_to_panel("[COMPILE FAILED]: ({0}) {1} {2}".format(file_base_name, problem, line_col))
                    elif "ErrorMsg" in self.result:
                        msg = ''
                        if 'object has been modified on server' in self.result['ErrorMsg']:
                            msg = self.result['ErrorMsg'] + '. You may try resetting your MetadataContainer to clear this error: MavensMate > Utilities > Reset MetadataContainer.'
                        else:
                            msg = self.result['ErrorMsg']
                        self.__print_to_panel("[COMPILE FAILED]: {0}".format(msg))

                elif 'success' in self.result and util.to_bool(self.result['success']) == False and (('messages' in self.result or 'Messages' in self.result) or 'details' in self.result):
                    if 'details' in self.result and 'componentFailures' in self.result['details']:
                        self.result['messages'] = self.result['details'].pop('componentFailures')
                    elif 'Messages' in self.result:
                        self.result['messages'] = self.result.pop('Messages')
                    
                    #here we're parsing a response from the metadata endpoint
                    failures = None
                    messages = self.result['messages']
                    if type( messages ) is not list:
                        messages = [messages]

                    problems = 0
                    for m in messages:
                        if 'problem' in m:
                            problems += 1
                            break

                    if problems == 0: #must not have been a compile error, must be a test run error
                        if 'runTestResult' in self.result:
                            if 'runTestResult' in self.result and 'failures' in self.result['runTestResult'] and type( self.result['runTestResult']['failures'] ) == list:
                                failures = self.result['runTestResult']['failures']
                            elif 'failures' in self.result['runTestResult']:
                                failures = [self.result['runTestResult']['failures']]
                            
                            if failures != None:
                                msg = ' [DEPLOYMENT FAILED]:'
                                for f in failures: 
                                    msg += f['name'] + ', ' + f['methodName'] + ': ' + f['message'] + '\n'
                                    self.__print_to_panel(msg)
                        elif 'run_test_result' in self.result:
                            if 'run_test_result' in self.result and 'failures' in self.result['run_test_result'] and type( self.result['run_test_result']['failures'] ) == list:
                                failures = self.result['run_test_result']['failures']
                            elif 'failures' in self.result['run_test_result']:
                                failures = [self.result['run_test_result']['failures']]
                            
                            if failures != None:
                                msg = ' [DEPLOYMENT FAILED]:'
                                for f in failures: 
                                    msg += f['name'] + ', ' + f['methodName'] + ': ' + f['message'] + '\n'
                                self.__print_to_panel(msg)
                    else: #compile error, build error message
                        msg = ""
                        for m in messages:
                            if "success" in m and m["success"] == False:
                                line_col = ""
                                if 'lineNumber' in m:
                                    line_col = ' (Line: '+m['lineNumber']
                                    util.mark_line_numbers(self.thread.view, [int(float(m['lineNumber']))], "bookmark")
                                if 'columnNumber' in m:
                                    line_col += ', Column: '+m['columnNumber']
                                if len(line_col) > 0:
                                    line_col += ')'
                                filename = m['fileName']
                                filename = re.sub(r'unpackaged/[A-Z,a-z]*/', '', filename)
                                msg += filename + ': ' + m['problem'] + line_col + "\n"

                        self.__print_to_panel('[DEPLOYMENT FAILED]: ' + msg)
                        
                elif 'success' in self.result and self.result["success"] == False and 'line' in self.result:
                    #this is a response from the apex compile api
                    line_col = ""
                    line, col = 1, 1
                    if 'line' in self.result:
                        line = int(self.result['line'])
                        line_col = ' (Line: '+str(line)
                        util.mark_line_numbers(self.thread.view, [line], "bookmark")
                    if 'column' in self.result:
                        col = int(self.result['column'])
                        line_col += ', Column: '+str(col)
                    if len(line_col):
                        line_col += ')'

                    #scroll to the line and column of the exception
                    if settings.get('mm_compile_scroll_to_error', True):
                        #open file, if already open it will bring it to focus
                        #view = sublime.active_window().open_file(self.thread.active_file)
                        view = self.thread.view
                        pt = view.text_point(line-1, col-1)
                        view.sel().clear()
                        view.sel().add(sublime.Region(pt))
                        view.show(pt)

                        self.__print_to_panel('[COMPILE FAILED]: ' + self.result['problem'] + line_col)
                elif 'success' in self.result and util.to_bool(self.result['success']) == True and 'Messages' in self.result and len(self.result['Messages']) > 0:
                    msg = ' [Operation completed Successfully - With Compile Errors]\n'
                    msg += '[COMPILE ERRORS] - Count:\n'
                    for m in self.result['Messages']:
                        msg += ' FileName: ' + m['fileName'] + ': ' + m['problem'] + 'Line: ' + m['lineNumber']
                    self.__print_to_panel(msg)
                elif 'success' in self.result and util.to_bool(self.result['success']) == True:
                    self.__print_to_panel("Success")
                elif 'success' in self.result and util.to_bool(self.result['success']) == False and 'body' in self.result:
                    self.__print_to_panel('[OPERATION FAILED]: ' + self.result['body'])
                elif 'success' in self.result and util.to_bool(self.result['success']) == False:
                    self.__print_to_panel('[OPERATION FAILED]')
                else:
                    self.__print_to_panel("Success")
            except Exception as e:
                debug(e)
                debug(type(self.result))
                msg = ""
                if type(self.result) is dict:
                    if 'body' in self.result:
                        msg = self.result["body"]
                    else:
                        msg = json.dumps(self.result)
                elif type(self.result) is str:
                    try:
                        m = json.loads(self.result)
                        msg = m["body"]
                    except:
                        msg = self.result
                else:
                    msg = "Check Sublime Text console for error and report issue to MavensMate-SublimeText GitHub project."
                self.__print_to_panel('[OPERATION FAILED]: ' + msg)

    def __handle_coverage_result(self):
        if self.result == []:
            self.__print_to_panel("No coverage information for the requested Apex Class")
        elif 'records' in self.result and self.result["records"] == []:
            self.__print_to_panel("No coverage information for the requested Apex Class")
        else:
            if 'records' in self.result:
                self.result = self.result['records']
            if type(self.result) is list:
                record = self.result[0]
            else:
                record = self.result
            msg = str(record["percentCovered"]) + "%"
            util.mark_uncovered_lines(self.thread.view, record["Coverage"]["uncoveredLines"])
            self.__print_to_panel('[PERCENT COVERED]: ' + msg)
 
    def __handle_org_wide_coverage_result(self):
        if 'PercentCovered' not in self.result:
            self.__print_to_panel("No coverage information available")
        else:
            msg = str(self.result["PercentCovered"]) + "%"
            self.__print_to_panel('[ORG-WIDE TEST COVERAGE]: ' + msg)

    def __handle_coverage_report_result(self):
        if self.result == []:
            self.__print_to_panel("No coverage information available")
        elif 'records' in self.result and self.result["records"] == []:
            self.__print_to_panel("No coverage information available")
        else:
            if 'records' in self.result:
                self.result = self.result['records']
            apex_names = []
            new_dict = {}
            for record in self.result:
                apex_names.append(record["ApexClassOrTriggerName"])
                new_dict[record["ApexClassOrTriggerName"]] = record
            apex_names.sort()
            cls_msg = "Apex Classes:\n"
            trg_msg = "Apex Triggers:\n"
            for apex_name in apex_names:
                msg = ''
                record = new_dict[apex_name]
                coverage_key = ''
                if record["percentCovered"] == 0:
                    coverage_key = ' !!'
                elif record["percentCovered"] < 75:
                    coverage_key = ' !'
                if record["ApexClassOrTrigger"] == "ApexClass":
                    apex_name += '.cls'
                else:
                    apex_name += '.trigger'
                coverage_bar = '[{0}{1}] {2}%'.format('='*(round(record["percentCovered"]/10)), ' '*(10-(round(record["percentCovered"]/10))), record["percentCovered"])
                msg += '   - '+apex_name+ ':'
                msg += '\n'
                msg += '      - coverage: '+coverage_bar + "\t("+str(record["NumLinesCovered"])+"/"+str(record["NumLinesCovered"]+record["NumLinesUncovered"])+")"+coverage_key 
                msg += '\n'
                if record["ApexClassOrTrigger"] == "ApexClass":
                    cls_msg += msg
                else:
                    trg_msg += msg
            self.__print_to_panel('Success')
            new_view = self.thread.window.new_file()
            new_view.set_scratch(True)
            new_view.set_name("Apex Code Coverage")
            if "linux" in sys.platform or "darwin" in sys.platform:
                new_view.set_syntax_file(os.path.join("Packages","YAML","YAML.tmLanguage"))
            else:
                new_view.set_syntax_file(os.path.join("Packages/YAML/YAML.tmLanguage"))
            sublime.set_timeout(new_view.run_command('generic_text', {'text': cls_msg+trg_msg }), 1)

    def __print_result(self):
        msg = ''
        if type(self.result) is dict and 'body' in self.result:
           msg += '[RESPONSE FROM MAVENSMATE]: '+self.result['body']
        elif self.result != None and self.result != "" and (type(self.result) is str or type(self.result) is bytes):
            msg += '[OPERATION FAILED]: Whoops, unable to parse the response. Please enable logging (http://mavensmate.com/Plugins/Sublime_Text/Plugin_Logging) and post relevant log(s) to a new issue at https://github.com/joeferraro/MavensMate-SublimeText\n'
            msg += '[RESPONSE FROM MAVENSMATE]: '+self.result
        else:
            msg += '[OPERATION FAILED]: Whoops, unable to parse the response. Please enable logging (http://mavensmate.com/Plugins/Sublime_Text/Plugin_Logging) and post relevant log(s) to a new issue at https://github.com/joeferraro/MavensMate-SublimeText\n'
            msg += '[RESPONSE FROM MAVENSMATE]: '+json.dumps(self.result, indent=4)
        #debug(self.result)
        self.__print_to_panel(msg)

    def __print_to_panel(self, msg):
        self.printer.panel.run_command('write_operation_status', {'text': msg, 'region': self.__get_print_region() })

    def __get_print_region(self):
        return [self.status_region.end(), self.status_region.end()+10]  

    def __finish(self):
        try:
            if 'success' in self.result and util.to_bool(self.result['success']) == True:
                if self.printer != None and len(ThreadTracker.get_pending_mm_panel_threads(self.thread.window)) == 0:
                    self.printer.hide() 
            elif 'State' in self.result and self.result['State'] == 'Completed' and len(ThreadTracker.get_pending_mm_panel_threads(self.thread.window)) == 0:
                if self.printer != None:
                    self.printer.hide()
            if self.operation == 'refresh':            
                sublime.set_timeout(lambda: sublime.active_window().active_view().run_command('revert'), 200)
                util.clear_marked_line_numbers()
        except:
            pass #TODO

    def __handle_new_metadata(self):
        self.__handle_compile_response()
        if 'success' in self.result and util.to_bool(self.result['success']) == True:
            if 'messages' in self.result or 'details' in self.result:
                if 'details' in self.result and 'componentSuccesses' in self.result['details']:
                    self.result['messages'] = self.result['details'].pop('componentSuccesses')
                if type(self.result['messages']) is not list:
                    self.result['messages'] = [self.result['messages']]
                for m in self.result['messages']:
                    if 'package.xml' not in m['fileName']:
                        file_name = m['fileName']
                        location = os.path.join(util.mm_project_directory(),file_name.replace('unpackaged/', 'src/'))
                        sublime.active_window().open_file(location)
                        break

    def __handle_generic_command_result(self):
        if self.result["success"] == True:
            self.__print_to_panel("Success")
        elif self.result["success"] == False:
            message = "[OPERATION FAILED]: "+self.result["body"]
            self.__print_to_panel(message)
        try:
            if self.thread.alt_callback != None:
                self.thread.alt_callback(self.result["body"])
        except:
            pass

    def __handle_apex_script_result(self):
        if self.result["success"] == True and self.result["compiled"] == True:
            self.__print_to_panel("Success")
            self.thread.window.open_file(self.result["log_location"], sublime.TRANSIENT)
        elif self.result["success"] == False:
            message = "[OPERATION FAILED]: "
            if "compileProblem" in self.result and self.result["compileProblem"] != None:
                message += "[Line: "+str(self.result["line"]) + ", Column: "+str(self.result["column"])+"] " + self.result["compileProblem"] + "\n"
            if "exceptionMessage" in self.result and self.result["exceptionMessage"] != None:
                message += self.result["exceptionMessage"] + "\n"
            if "exceptionStackTrace" in self.result and self.result["exceptionStackTrace"] != None:
                message += self.result["exceptionStackTrace"] + "\n"
            self.__print_to_panel(message)

    def __handle_test_result(self):
        responses = []
        if len(self.result) == 1:
            res = self.result[0]
            response_string = ""
            if 'detailed_results' in res:
                all_tests_passed = True
                for r in res['detailed_results']:
                    if r["Outcome"] != "Pass":
                        all_tests_passed = False
                        break

                if all_tests_passed:
                    response_string += '[TEST RESULT]: PASS'
                else:
                    response_string += '[TEST RESULT]: FAIL'
                
                for r in res['detailed_results']:
                    if r["Outcome"] == "Pass":
                        pass #dont need to write anything here...
                    else:
                        response_string += '\n\n'
                        rstring = " METHOD RESULT "
                        rstring += "\n"
                        rstring += "{0} : {1}".format(r["MethodName"], r["Outcome"])
                        
                        if "StackTrace" in r and r["StackTrace"] != None:
                            rstring += "\n\n"
                            rstring += " STACK TRACE "
                            rstring += "\n"
                            rstring += r["StackTrace"]
                        
                        if "Message" in r and r["Message"] != None:
                            rstring += "\n\n"
                            rstring += " MESSAGE "
                            rstring += "\n"
                            rstring += r["Message"]
                            rstring += "\n"
                        #responses.append("{0} | {1} | {2} | {3}\n".format(r["MethodName"], r["Outcome"], r["StackTrace"], r["Message"]))
                        responses.append(rstring)
                response_string += "\n\n".join(responses)
                self.__print_to_panel(response_string)
                self.printer.scroll_to_bottom()
            else:
                self.__print_to_panel(json.dumps(self.result))
        elif len(self.result) > 1:
            #run multiple tests
            response_string = ''
            for res in self.result:
                if 'detailed_results' in res:
                    all_tests_passed = True
                    for r in res['detailed_results']:
                        if r["Outcome"] != "Pass":
                            all_tests_passed = False
                            break

                    if all_tests_passed:
                        response_string += res['ApexClass']['Name']+':\n\tTEST RESULT: PASS'
                    else:
                        response_string += res['ApexClass']['Name']+':\n\tTEST RESULT: FAIL'
                    
                    for r in res['detailed_results']:
                        if r["Outcome"] == "Pass":
                            pass #dont need to write anything here...
                        else:
                            response_string += '\n\n'
                            response_string += "\t METHOD RESULT "
                            response_string += "\t\n"
                            response_string += "\t{0} : {1}".format(r["MethodName"], r["Outcome"])
                            
                            if "StackTrace" in r and r["StackTrace"] != None:
                                response_string += "\n\n"
                                response_string += "\t STACK TRACE "
                                response_string += "\t\n"
                                response_string += "\t"+r["StackTrace"].replace("\n","\t\n")
                            
                            if "Message" in r and r["Message"] != None:
                                response_string += "\n\n"
                                response_string += "\t MESSAGE "
                                response_string += "\t\n"
                                response_string += "\t"+r["Message"].replace("\n","\t\n")
                                response_string += "\n"
                response_string += "\n\n"
            #self.__print_to_panel(response_string)
            #self.printer.scroll_to_bottom()

            self.__print_to_panel('Success')
            new_view = self.thread.window.new_file()
            new_view.set_scratch(True)
            new_view.set_name("Run All Tests Result")
            if "linux" in sys.platform or "darwin" in sys.platform:
                new_view.set_syntax_file(os.path.join("Packages","YAML","YAML.tmLanguage"))
                new_view.set_syntax_file(os.path.join("Packages","MavensMate","sublime","panel","MavensMate.hidden-tmLanguage"))
            else:
                new_view.set_syntax_file(os.path.join("Packages/MavensMate/sublime/panel/MavensMate.hidden-tmLanguage"))

            sublime.set_timeout(new_view.run_command('generic_text', {'text': response_string }), 1)

        elif 'body' in self.result:
            self.__print_to_panel(json.dumps(self.result['body']))

########NEW FILE########
__FILENAME__ = parsehelp
"""
Copyright (c) 2012 Fredrik Ehnbom

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

   1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.

   2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.

   3. This notice may not be removed or altered from any source
   distribution.
"""
import re

__DEBUG = False
if __DEBUG:
    __indent = ""
    def debug(func):
        import time
        def __wrapped(*args):
            global __indent
            s = time.time()
            __indent += "\t"
            ret = func(*args)
            e = time.time()
            __indent = __indent[:-1]
            print("%s%s took %f ms" % (__indent, func.__name__, 1000*(e-s)))
            return ret
        return __wrapped
else:
    def debug(func):
        return func

@debug
def count_brackets(data):
    even = 0
    for i in range(len(data)):
        if data[i] == '{':
            even += 1
        elif data[i] == '}':
            even -= 1
    return even


@debug
def collapse_generic(before, open, close):
    i = len(before)
    count = 0
    end = -1
    min = 0
    while i >= 0:
        a = before.rfind(open, 0, i)
        b = before.rfind(close, 0, i)
        i = max(a, b)
        if i == -1:
            break
        if before[i] == close:
            count += 1
            if end == -1:
                end = i
        elif before[i] == open:
            count -= 1
            if count < min:
                min = count

        if count == min and end != -1:
            before = "%s%s" % (before[:i+1], before[end:])
            end = -1
    return before

@debug
def collapse_getter_setters(before):
    after = re.sub(r'\s*{\s*get\s*;\s*set\s*;\s*}', ';', before)
    after = re.sub(r'\s*{\s*get\s*;\s*private set\s*;\s*}', ';', after)
    after = re.sub(r'\s*{\s*private get\s*;\s*private set\s*;\s*}', ';', after)
    after = re.sub(r'\s*{\s*private get\s*;\s*set\s*;\s*}', ';', after)
    return after

@debug
def collapse_brackets(before):
    return collapse_generic(before, "{", "}")


@debug
def collapse_parenthesis(before):
    return collapse_generic(before, '(', ')')


@debug
def collapse_square_brackets(before):
    return collapse_generic(before, '[', ']')


@debug
def collapse_ltgt(before):
    i = len(before)
    count = 0
    end = -1
    min = 0
    while i >= 0:
        a = before.rfind(">", 0, i)
        b = before.rfind("<", 0, i)
        i = max(a, b)
        if i == -1:
            break
        if before[i] == '>':
            collapse = True
            if i > 0 and before[i-1] == '>':
                # Don't want to collapse a statement such as 'std::cout << "hello world!!" << std::endl;
                data = before[:i-1]
                match = re.search(r"([\w\s,.:<]+)$", data)
                if match:
                    if match.group(1).count("<") < 2:
                        collapse = False
                else:
                    collapse = False

            if not collapse or before[i-1] == '-' or \
                    (before[i-1] == ' ' and i >=2 and before[i-2] != '>'):
                i -= 1
            else:
                count += 1
                if end == -1:
                    end = i
        elif before[i] == '<':
            if i > 0 and (before[i-1] == '<' or before[i-1] == ' '):
                i -= 1
            else:
                count -= 1
                if count == min and end != -1:
                    before = "%s%s" % (before[:i+1], before[end:])
                    end = -1
                if count < min:
                    min = count
    return before


@debug
def collapse_strings(before):
    i = len(before)
    count = 0
    end = -1
    while i >= 0:
        i = before.rfind("'", 0, i)
        if i == -1:
            break
        if before[i] == "'":
            if i > 0 and before[i-1] == '\\':
                i -= 1
            elif count > 0:
                before = "%s%s" % (before[:i+1], before[end:])
                count = 0
            else:
                count += 1
                end = i
    return before


@debug
def extract_completion(before):
    before = collapse_getter_setters(before)
    before = collapse_parenthesis(before)
    before = collapse_square_brackets(before)
    before = collapse_ltgt(before)
    before = before.split("\n")[-1]
    before = before.split(";")[-1]
    before = re.sub(r"^\s+", r"", before)
    ret = ""
    while True:
        match = re.search(r"((\.|\->)?([^|.,\ \[\]\(\)\t]+(\(\)|\[\])*)(\.|\->))$", before)
        if not match:
            break
        ret = match.group(3) + match.group(5) + ret
        before = before[:-len(match.group(3))-len(match.group(5))].strip()

    return ret

@debug
def extract_completion_objc(before):
    before = collapse_parenthesis(before)
    before = before.split("\n")[-1]
    before = before.split(";")[-1]
    before = re.sub(r"^\s+", r"", before)
    ret = ""
    while True:
        match = re.search(r"([\w\[\]\.\-> ]+([ \t]+|->|.))$", before)
        if not match:
            match = re.search(r"([\w\[\]]+\s+)$", before)
        if not match:
            break
        ret = match.group(1) + ret
        before = before[:-len(match.group(1))]
    return ret

_keywords = ["trigger", "insert", "update", "delete", "upsert", "return", "new", "delete", "class", "define", "using", "void", "template", "public:", "protected:", "private:", "public", "private", "protected", "typename", "in", "case", "default", "goto", "typedef", "struct", "else"]


@debug
def extract_package(data):
    data = remove_preprocessing(data)
    match = re.search(r"package\s([\w.]+);", data)
    if match:
        return match.group(1)
    return None


@debug
def extract_used_namespaces(data):
    regex = re.compile(r"\s*using\s+(namespace\s+)?([^;]+)", re.MULTILINE)
    ret = []
    for match in regex.finditer(data):
        toadd = match.group(2)
        if match.group(1) == None:
            toadd = toadd[:toadd.rfind("::")]
        ret.append(toadd)
    return ret


@debug
def extract_namespace(data):
    data = remove_preprocessing(data)
    data = collapse_brackets(data)
    data = collapse_square_brackets(data)
    data = remove_namespaces(data)
    regex = re.compile(r"namespace\s+([^{\s]+)\s*\{", re.MULTILINE)
    ret = ""
    for match in regex.finditer(data):
        if len(ret):
            ret += "::"
        ret += match.group(1)
    if len(ret.strip()) == 0:
        ret = None
    if ret == None:
        data = remove_functions(data)
        regex = re.compile(r"(\w+)::(\w+)::")
        match = regex.search(data)
        if match:
            ret = match.group(1)
    return ret

@debug
def extract_class_from_function(data):
    data = remove_preprocessing(data)
    data = collapse_brackets(data)
    data = collapse_square_brackets(data)
    data = collapse_parenthesis(data)
    data = remove_functions(data)
    ret = None
    for match in re.finditer(r"(.*?)(\w+)::~?(\w+)\s*\(\)(\s+const)?[^{};]*\{", data, re.MULTILINE):
        ret = match.group(2)

    return ret


@debug
def extract_class(data):
    data = remove_preprocessing(data)
    data = collapse_brackets(data)
    data = collapse_square_brackets(data)
    data = collapse_strings(data)
    data = remove_classes(data)
    regex = re.compile(r"class\s+([^;{\s:]+)\s*(:|;|\{|extends|implements)", re.MULTILINE)
    ret = None
    for match in regex.finditer(data):
        ret = match.group(1)
    if ret == None and "@implementation" in data:
        regex = re.compile(r"@implementation\s+(\w+)", re.MULTILINE)
        for match in regex.finditer(data):
            ret = match.group(1)
    return ret


@debug
def extract_inheritance(data, classname):
    data = remove_preprocessing(data)
    data = collapse_brackets(data)
    data = collapse_square_brackets(data)
    data = remove_classes(data)
    regex = re.compile(r"class\s+%s\s*(:|extends)\s+([^\s,{]+)" % classname, re.MULTILINE)
    match = regex.search(data)
    if match != None:
        return match.group(2)
    return None


@debug
def remove_classes(data):
    regex = re.compile(r"class\s+[^{]+{\}\s*;?", re.MULTILINE)
    return regex.sub("", data)


@debug
def remove_functions(data):
    # First remove for-loops
    data = sub(r"""(?:\s|^)for\s*\([^;{}]*;[^;{}]*;[^{}]*\)\s*\{\}""", data)
    regex = sub(r"""(?x)
            (?:[^\s,{};()]+\s+)?            # Possible return type. Optional because it will then
                                            # remove # while loops, preprocessor macros, constructors,
                                            # destructors, etc
            [^\s,;{}]+\s*\([^{};]*\)        # function name + possible space + parenthesis
            [^;{]*                          # Any extras like initializers, const, etc
            \{\}""", data)
    return regex


@debug
def remove_namespaces(data):
    regex = re.compile(r"\s*namespace\s+[^{]+\s*\{\}\s*", re.MULTILINE)
    return regex.sub("", data)


@debug
def sub(exp, data):
    regex = re.compile(exp, re.MULTILINE|re.DOTALL)
    while True:
        olddata = data
        data = regex.sub("", data)
        if olddata == data:
            break
    return data


@debug
def remove_preprocessing(data):
    data = data.replace("\\\n", " ")
    data = data.replace(",", " ")
    data = sub(r"\#\s*define[^\n]+\n", data)
    data = sub(r"\#\s*(ifndef|ifdef|if|endif|else|elif|pragma|include)[^\n]*\n", data)
    data = sub(r"//[^\n]+\n", data)
    data = sub(r"/\*.*?\*/", data)
    return data


@debug
def remove_includes(data):
    regex = re.compile(r"""\#\s*include\s+(<|")[^>"]+(>|")""")
    while True:
        old = data
        data = regex.sub("", data)
        if old == data:
            break
    return data

_invalid = r"""\(\s\{,\*\&\-\+\/;=%\)\"!"""
_endpattern = r"\;|,|\)|=|\[|\(\)\s*\;|:\s+"


@debug
def patch_up_variable(origdata, data, origtype, var, ret):
    type = origtype
    var = re.sub(r"\s*=\s*[^;,\)]+", "", var)
    curlybracere = re.compile(r"\s*(\S+)\s*({})\s*(\S*)", re.MULTILINE)
    for var in var.split(","):
        var = var.strip()
        pat = r"%s\s*([^;{]*)%s\s*(%s)" % (re.escape(origtype), re.escape(var), _endpattern)
        end = re.search(pat, data)
        if end.group(2) == "[":
            type += re.search(r"([\[\]]+)", data[end.start():]).group(1)
        i = var.find("[]")
        if i != -1:
            type += var[i:]
            var = var[:i]
        if "<" in type and ">" in type:
            s = r"(%s.+%s)(const)?[^{};]*(%s)" % (type[:type.find("<")+1], type[type.find(">"):], var)
            regex = re.compile(s)
            match = None
            for m in regex.finditer(origdata):
                match = m
            type = match.group(1)
        match = curlybracere.search(var)
        if match:
            if match.group(3):
                var = match.group(3)
                type += " %s" % match.group(1)
            else:
                var = match.group(1)
        ret.append((type, var))

@debug
def extract_variables(data):
    origdata = data
    data = remove_preprocessing(data)
    data = remove_includes(data)
    data = collapse_getter_setters(data)
    data = collapse_brackets(data)
    data = collapse_square_brackets(data)
    data = collapse_strings(data)
    data = collapse_ltgt(data)
    data = remove_functions(data)
    data = remove_namespaces(data)
    data = remove_classes(data)
    data = re.sub(r"\([^)]*?\)\s*(?=;)", "()", data, re.MULTILINE)
    data = re.sub(r"\s*case\s+[\w:]*[^:]:[^:]", "", data, re.MULTILINE)
    data = re.sub(r"\s*default:\s*", "", data, re.MULTILINE)
    data = re.sub(r"template\s*<>", "", data, re.MULTILINE)
    data = re.sub(r"\s{2,}", " ", data, re.MULTILINE)

    # first get any variables inside of the function declaration
    funcdata = ";".join(re.findall(r"\(([^)]+\))", data, re.MULTILINE))
    pattern = r"\s*((static\s*)?(struct\s*)?\b(const\s*)?[^%s]+[\s*&]+(const)?[\s*&]*)(\b[^%s]+)\s*(?=,|\)|=)" % (_invalid, _invalid)
    funcvars = re.findall(pattern, funcdata, re.MULTILINE)
    ret = []
    for m in funcvars:
        type = get_base_type(m[0])
        if type in _keywords:
            continue
        patch_up_variable(origdata, data, m[0].strip(), m[5].strip(), ret)

    # Next, take care of all other variables
    data = collapse_parenthesis(data)

    pattern = r"""(?x)
        (^|,|\(|;|\{)\s*
            (
                (static\s*)?
                (struct\s*)?
                \b(const\s*)?\b
                [^%s]+
                [\s*&]+
                (const)?
                [\s*&]*
            )                   # type name
            (\b[^;()]+)\s*      # variable name
            (?=%s)""" % (_invalid, _endpattern)
    regex = re.compile(pattern, re.MULTILINE)

    for m in regex.finditer(data):
        if m.group(2) == None:
            continue
        type = get_base_type(m.group(2))
        if type in _keywords:
            continue
        type = m.group(2).strip()
        var = m.group(7).strip()
        patch_up_variable(origdata, data, type, var, ret)
    return ret


@debug
def dereference(typename):
    if "*" in typename:
        return typename.replace("*", "", 1)
    elif "[]" in typename:
        return typename.replace("[]", "", 1)
    return typename


@debug
def is_pointer(typename):
    return "*" in typename or "[]" in typename


@debug
def get_pointer_level(typename):
    return typename.count("*") + typename.count("[]")


@debug
def get_base_type(data):
    data = re.sub(r"(\s+|^)const(\s|$)", " ", data)
    data = re.sub(r"(\s|^)static(\s|$)", " ", data)
    data = re.sub(r"(\s+|^)struct(\s|$)", " ", data)
    data = data.strip()
    data = data.replace("&", "").replace("*", "").replace("[]", "")
    data = data.strip()
    return data


@debug
def get_var_type(data, var):
    regex = re.compile(r"(const\s*)?\b([^%s]+[ \s\*\&]+)(\s*[^%s]+\,\s*)*(%s)\s*(\[|\(|\;|,|\)|=|:|in\s+)" % (_invalid, _invalid, re.escape(var)), re.MULTILINE)
    origdata = data
    data = remove_preprocessing(data)
    data = collapse_getter_setters(data)
    data = collapse_ltgt(data)
    data = collapse_brackets(data)
    data = collapse_square_brackets(data)
    data = collapse_strings(data)
    data = remove_functions(data)
    #print(data)
    match = None

    for m in regex.finditer(data):
        t = m.group(2).strip()
        if t in _keywords:
            continue
        match = m
    if match and match.group(2):
        type = match.group(2)
        if match.group(1):
            type = match.group(1) + type
        pat = r"(%s)([^%s]+,\s*)*(%s)" % (re.escape(type), _invalid, re.escape(match.group(4)))
        regex = re.compile(pat)
        for m in regex.finditer(data):
            match = m
        key = get_base_type(match.group(1))
        if "<>" in key:
            key = match.group(1)
            name = key[:key.find("<")]
            end = key[key.find(">")+1:]
            regex = re.compile(r"(%s<.+>%s\s*)([^%s]+,\s*)*(%s)" % (name, end, _invalid, var))
            match = None
            for m in regex.finditer(origdata):
                key = get_base_type(m.group(1))
                if key in _keywords:
                    continue
                match = m
            if match:
                data = origdata[match.start(1):match.end(1)]
                i = len(data)-1
                count = 0
                while i > 0:
                    a = data.rfind(">", 0, i)
                    b = data.rfind("<", 0, i)
                    i = max(a, b)
                    if i == -1:
                        break
                    if data[i] == ">":
                        count += 1
                    elif data[i] == "<":
                        count -= 1
                        if count == 0:
                            data = data[i:]
                            break
                regex = re.compile(r"(%s%s)([^%s]+,\s*)*(%s)" % (name, data, _invalid, var))
                for m in regex.finditer(origdata):
                    match = m
    else:
        match = None

    if match and match.group(1):
        # Just so that it reports the correct location in the file
        pat = r"(%s)([^%s],)*(%s)\s*(\[|\(|\;|,|\)|=)" % (re.escape(match.group(1)), _invalid, re.escape(match.group(3)))
        regex = re.compile(pat)
        for m in regex.finditer(origdata):
            match = m
    return match


@debug
def remove_empty_classes(data):
    data = sub(r"\s*class\s+[^\{]+\s*\{\}", data)
    return data


@debug
def get_var_tocomplete(iter, data):
    var = None
    end = None
    tocomplete = ""
    for m in iter:
        if var != None and m.start(0) != end:
            var = None
            tocomplete = ""

        if len(tocomplete):
            tocomplete += m.group(1)
        tocomplete += m.group(2)
        if var == None:
            var = m.group(1)
        end = m.end(2)
    if "<>" in tocomplete:
        before = re.escape(tocomplete[:tocomplete.find("<")]).replace("\(\)", "\(.*?\)")
        after = re.escape(tocomplete[tocomplete.rfind(">")+1:]).replace("\(\)", "\(.*?\)")
        regex = re.compile(r"(%s<.+>%s)" % (before, after), re.MULTILINE)
        match = None
        for m in regex.finditer(data):
            match = m
        tocomplete = collapse_brackets(collapse_parenthesis(match.group(1)))
    return var, tocomplete


@debug
def get_type_definition(data):
    before = extract_completion(data)
    var, tocomplete = None, None
    objc = False
    if len(before) == 0 and "[" in data:
        before = extract_completion_objc(data)
        objc = True

    if not objc:
        var, tocomplete = get_var_tocomplete(re.finditer(r"(\w+(?:[^\.\-,+*/:]*))(\.|->|::|[ \t])", before), data)

    if var == None or objc:
        var, tocomplete = get_var_tocomplete(re.finditer(r"\[?([^ \.\-:]+)((?:[ \t]|\.|->|::).*)", before), data)
        var = re.sub(r"^\[*", "", var)

    extra = ""
    if var.endswith("[]"):
        extra = var[var.find("["):]
        var = var[:var.find("[")]

    if var == "this" or var == "self":
        clazz = extract_class(data)
        if clazz == None:
            clazz = extract_class_from_function(data)
        line = column = -1  # TODO
        return line, column, clazz, var, tocomplete
    elif var == "super":
        clazz = extract_class(data)
        if clazz:
            sup = extract_inheritance(data, clazz)
            return -1, -1, sup, var, tocomplete
    elif tocomplete.startswith("::"):
        return -1, -1, var, None, tocomplete
    else:
        match = get_var_type(data, var)
    if match == None:
        return -1, -1, var, None, extra+tocomplete
    line = data[:match.start(3)].count("\n") + 1
    column = len(data[:match.start(3)].split("\n")[-1])+1
    typename = match.group(1).strip()

    end = re.search(r"^\s*([^;,=\(\):]*)(;|,|=|\(|\)|:)", data[match.end(3):])
    if end and end.group(1).startswith("["):
        end = collapse_square_brackets(data[match.end(3)+end.start(1):match.end(3)+end.end(1)]).strip()
        typename += end

    return line, column, typename, var, extra+tocomplete


@debug
def template_split(data):
    if data == None:
        return None
    ret = []
    origdata = data
    data = collapse_ltgt(data)
    data = [a.strip() for a in data.split(",")]
    exp = ""
    for var in data:
        exp += r"(%s)\s*,?\s*" % (re.escape(var).replace("\\<\\>", "<.*>").strip())

    match = re.search(exp, origdata)
    ret = list(match.groups())

    return ret


@debug
def solve_template(typename):
    args = []
    template = re.search(r"([^<]+)(<(.+)>)?((::|.)(.+))?$", typename)
    args = template_split(template.group(3))
    if args:
        for i in range(len(args)):
            if "<" in args[i]:
                args[i] = solve_template(args[i])
            else:
                args[i] = (args[i], None)
    if template.group(6):
        return template.group(1), args, solve_template(template.group(6))
    return template.group(1), args


@debug
def make_template(data, concat="."):
    if data[1] != None:
        ret = ""
        for param in data[1]:
            sub = make_template(param, concat)
            if len(ret):
                ret += ", "
            ret += sub
        temp = "%s<%s%s>" % (data[0], ret, ' ' if ret[-1] == '>' else '')
        if len(data) == 3:
            temp += concat + make_template(data[2], concat)
        return temp
    return data[0]


@debug
def extract_line_until_offset(data, offset):
    return data[:offset+1].split("\n")[-1]


@debug
def extract_line_at_offset(data, offset):
    if offset < 0 or offset >= len(data) or data[offset] == "\n":
        return ""
    line = data[:offset+1].count("\n")
    return data.split("\n")[line]


@debug
def extract_word_at_offset(data, offset):
    line, column = get_line_and_column_from_offset(data, offset)
    line = extract_line_at_offset(data, offset)
    begin = 0
    end = 0
    match = re.search(r"\b\w*$", line[0:column])
    if match:
        begin = match.start()
    else:
        return ""
    match = re.search(r"^\w*", line[begin:])
    if match:
        end = begin+match.end()
    word = line[begin:end]
    return word


@debug
def extract_extended_word_at_offset(data, offset):
    line, column = get_line_and_column_from_offset(data, offset)
    line = extract_line_at_offset(data, offset)
    match = re.search(r"^\w*", line[column:])
    if match:
        column = column + match.end()
    extword = line[0:column]
    return extword


@debug
def get_line_and_column_from_offset(data, offset):
    data = data[:offset].split("\n")
    line = len(data)
    column = len(data[-1]) + 1
    return line, column


@debug
def get_offset_from_line_and_column(data, line, column):
    data = data.split("\n")
    if line == 1:
        column -= 1
    offset = len("\n".join(data[:line-1])) + column
    return offset

########NEW FILE########
__FILENAME__ = printer
import sublime
import os
import unicodedata
import time

try:
    import MavensMate.config as config
    import MavensMate.util as util
    from .threads import ThreadTracker
except:
    import config
    import util
    from lib.threads import ThreadTracker

settings = sublime.load_settings('mavensmate.sublime-settings')

#class representing the MavensMate activity/debug panel in Sublime Text
class PanelPrinter(object):
    printers = {}

    def __init__(self):
        self.name = 'MavensMate-OutputPanel'
        self.visible = False
        self.hide_panel = settings.get('mm_hide_panel_on_success', 1)
        self.hide_time = settings.get('mm_hide_panel_time', 1)
        self.queue = []
        self.strings = {}
        self.just_error = False
        self.capture = False
        self.input = None
        self.input_start = None
        self.on_input_complete = None
        self.original_view = None

    @classmethod
    def get(cls, window_id):
        printer = cls.printers.get(window_id)
        if not printer:
            printer = PanelPrinter()
            printer.window_id = window_id
            printer.init()
            cls.printers[window_id] = printer
            printer.write('MavensMate for Sublime Text v'+util.get_version_number()+'\n')
        return printer

    def error(self, string):
        callback = lambda : self.error_callback(string)
        sublime.set_timeout(callback, 1)

    def error_callback(self, string):
        string = str(string)
        self.reset_hide()
        self.just_error = True
        sublime.error_message('MavensMate: ' + string)

    def hide(self, thread = None):
        settings = sublime.load_settings('mavensmate.sublime-settings')
        hide = settings.get('mm_hide_panel_on_success', True)
        if hide == True:
            hide_time = time.time() + float(hide)
            self.hide_time = hide_time
            sublime.set_timeout(lambda : self.hide_callback(hide_time, thread), int(hide * 300))

    def hide_callback(self, hide_time, thread):
        if thread:
            last_added = ThreadTracker.get_last_added(self.window_id)
            if thread != last_added:
                return
        if self.visible and self.hide_time and hide_time == self.hide_time:
            if not self.just_error:
                self.window.run_command('hide_panel')
            self.just_error = False

    def init(self):
        if not hasattr(self, 'panel'):
            self.window = sublime.active_window()
            self.panel = self.window.get_output_panel(self.name)
            self.panel.set_read_only(True)
            self.panel.settings().set('syntax', 'Packages/MavensMate/sublime/panel/MavensMate.hidden-tmLanguage')
            self.panel.settings().set('color_scheme', 'Packages/MavensMate/sublime/panel/MavensMate.hidden-tmTheme')
            self.panel.settings().set('word_wrap', True)
            self.panel.settings().set('gutter', True)
            self.panel.settings().set('line_numbers', True)

    def reset_hide(self):
        self.hide_time = None

    def show(self, force = False):
        self.init()
        settings = sublime.load_settings('mavensmate.sublime-settings')
        hide = settings.get('hide_output_panel', 1)
        
        # TODO
        # if settings.get('mm_compile_scroll_to_error', True):
        #     view = self.window.active_view()
        #     pt = view.text_point(line-1, col-1)
        #     view.sel().clear()
        #     view.sel().add(sublime.Region(pt))
        #     view.show(pt)

        if force or hide != True or not isinstance(hide, bool):
            self.visible = True
            self.window.run_command('show_panel', {'panel': 'output.' + self.name})

    def prepare_string(self, string, key, writeln=False):
        if len(string):
            try:
                if not isinstance(string, unicode):
                    string = unicode(string, 'UTF-8', errors='strict')
            except:
                if type(string) is not str:
                    string = str(string, 'utf-8')
            if os.name != 'nt':
                string = unicodedata.normalize('NFC', string)
            if writeln:
                string = string+"\n"
            self.strings[key].append(string)

    def write(self, string, key = 'sublime_mm', finish = False):
        if not len(string) and not finish:
            return
        if key not in self.strings:
            self.strings[key] = []
            self.queue.append(key)
        
        self.prepare_string(string, key)
        
        if finish:
            self.strings[key].append(None)
        sublime.set_timeout(self.write_callback, 0)
        return key

    def writeln(self, string, key = 'sublime_mm', finish = False):
        if not len(string) and not finish:
            return
        if key not in self.strings:
            self.strings[key] = []
            self.queue.append(key)
        
        self.prepare_string(string, key, True)
        
        if finish:
            self.strings[key].append(None)
        sublime.set_timeout(self.write_callback, 0)
        return key

    def scroll_to_bottom(self):
        size = self.panel.size()
        sublime.set_timeout(lambda : self.panel.show(size, True), 2)

    def write_callback(self):
        if config.sublime_version >= 3000:
            found = False
            for key in self.strings.keys():
                if len(self.strings[key]):
                    found = True
            if not found:
                return
            string = self.strings[key].pop(0)
            self.panel.run_command('mavens_mate_output_text', {'text': string})
            
            size = self.panel.size()
            sublime.set_timeout(lambda : self.panel.show(size, True), 2)

            return
        else:
            found = False
            for key in self.strings.keys():
                if len(self.strings[key]):
                    found = True
            if not found:
                return
            read_only = self.panel.is_read_only()
            if read_only:
                self.panel.set_read_only(False)
            edit = self.panel.begin_edit()
            keys_to_erase = []
            for key in list(self.queue):
                while len(self.strings[key]):
                    string = self.strings[key].pop(0)
                    if string == None:
                        self.panel.erase_regions(key)
                        keys_to_erase.append(key)
                        continue
                    if key == 'sublime_mm':
                        point = self.panel.size()
                    else:
                        regions = self.panel.get_regions(key)
                        if not len(regions):
                            point = self.panel.size()
                        else:
                            region = regions[0]
                            point = region.b + 1
                    if point == 0 and string[0] == '\n':
                        string = string[1:]
                    self.panel.insert(edit, point, string)
                    if key != 'sublime_mm':
                        point = point + len(string) - 1
                        region = sublime.Region(point, point)
                        self.panel.add_regions(key, [region], '')
        
            for key in keys_to_erase:
                if key in self.strings:
                    del self.strings[key]
                try:
                    self.queue.remove(key)
                except ValueError:
                    pass
            
            self.panel.end_edit(edit)
            if read_only:
                self.panel.set_read_only(True)
            size = self.panel.size()
            sublime.set_timeout(lambda : self.panel.show(size, True), 2)


########NEW FILE########
__FILENAME__ = reloader
import sys
import sublime
st_version = 3

# With the way ST3 works, the sublime module is not "available" at startup
# which results in an empty version number
if sublime.version() == '' or int(sublime.version()) > 3000:
    st_version = 3
    from imp import reload

# Python allows reloading modules on the fly, which allows us to do live upgrades.
# The only caveat to this is that you have to reload in the dependency order.
#
# Thus is module A depends on B and we don't reload B before A, when A is reloaded
# it will still have a reference to the old B. Thus we hard-code the dependency
# order of the various Package Control modules so they get reloaded properly.
#
# There are solutions for doing this all programatically, but this is much easier
# to understand.

reload_mods = []
for mod in sys.modules:
    if mod[0:15].lower().replace(' ', '_') == 'mavensmate.lib.' and sys.modules[mod] != None:
        #print(mod[0:15].lower().replace(' ', '_'))
        reload_mods.append(mod)

# print(reload_mods)

mod_prefix = 'lib'
if st_version == 3:
    mod_prefix = 'MavensMate.' + mod_prefix

mods_load_order = [
    '',
    '.apex_extensions',
    '.command_helper',
    '.commands',
    '.mm_interface',
    '.printer',
    '.threads',
    '.times',
    '.upgrader',
    '.usage_reporter',
    '.views',
    '.mm_merge',
    '.completioncommon',
    '.vf',
    '.parsehelp',
    '.resource_bundle',
    '.mm_response_handlers'
]

for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        reload(sys.modules[mod])

########NEW FILE########
__FILENAME__ = resource_bundle
import os
import sublime
import sys
import shutil
import zipfile

try:
    from .threads import ThreadTracker
    from .threads import ThreadProgress
    from .threads import PanelThreadProgress
    from .printer import PanelPrinter
    import MavensMate.lib.command_helper as command_helper
    import MavensMate.util as util
    import MavensMate.lib.mm_interface as mm
except:
    from lib.threads import ThreadTracker
    from lib.threads import ThreadProgress
    from lib.threads import PanelThreadProgress
    from lib.printer import PanelPrinter
    import lib.command_helper as command_helper
    import util

#creates resource-bundles for the static resource(s) selected        
def create(self, files, refresh=False):
    for file in files:
        fileName, fileExtension = os.path.splitext(file)
        if fileExtension != '.resource':
            sublime.message_dialog("You can only create resource bundles for static resources")
            return
    
    printer = PanelPrinter.get(self.window.id())
    printer.show()
    if refresh:
        printer.write('\nRefreshing Resource Bundle(s)\n')
    else:
        printer.write('\nCreating Resource Bundle(s)\n')

    if not os.path.exists(os.path.join(util.mm_project_directory(),'resource-bundles')):
        os.makedirs(os.path.join(util.mm_project_directory(),'resource-bundles'))

    for f in files:
        fileName, fileExtension = os.path.splitext(f)
        if sys.platform == "win32":
            baseFileName = fileName.split("\\")[-1]
        else:
            baseFileName = fileName.split("/")[-1]
        if not refresh:
            if os.path.exists(os.path.join(util.mm_project_directory(),'resource-bundles',baseFileName+fileExtension)):
                printer.write('[OPERATION FAILED]: The resource bundle already exists\n')
                return
        if sys.platform == "win32":
            fz = zipfile.ZipFile(f, 'r')
            for fileinfo in fz.infolist():
                path = os.path.join(util.mm_project_directory(),'resource-bundles',baseFileName+fileExtension)
                directories = fileinfo.filename.split('/')
                #directories = fileinfo.filename.split('\\')
                for directory in directories:
                    if directory.startswith('__MACOSX'):
                        continue
                    path = os.path.join(path, directory)
                    if directory == directories[-1]: break # the file
                    if not os.path.exists(path):
                        os.makedirs(path)
                try:
                    outputfile = open(path, "wb")
                    shutil.copyfileobj(fz.open(fileinfo.filename), outputfile)
                except:
                    pass
        else:
            cmd = 'unzip \''+f+'\' -d \''+util.mm_project_directory()+'/resource-bundles/'+baseFileName+fileExtension+'\''
            os.system(cmd)

    printer.write('[Resource bundle creation complete]\n')
    printer.hide()
    util.send_usage_statistics('Create Resource Bundle') 

def deploy(bundle_name):
    if '.resource' not in bundle_name:
        bundle_name = bundle_name + '.resource'
    message = 'Bundling and deploying to server: ' + bundle_name
    # delete existing sr
    if os.path.exists(os.path.join(util.mm_project_directory(),"src","staticresources",bundle_name)):
        os.remove(os.path.join(util.mm_project_directory(),"src","staticresources",bundle_name))
    # zip bundle to static resource dir 
    os.chdir(os.path.join(util.mm_project_directory(),"resource-bundles",bundle_name))
    if 'darwin' in sys.platform or 'linux' in sys.platform:
        #cmd = "zip -r -X '"+util.mm_project_directory()+"/src/staticresources/"+bundle_name+"' *"      
        #os.system(cmd)
        zip_file = util.zip_directory(os.path.join(util.mm_project_directory(),"resource-bundles",bundle_name), os.path.join(util.mm_project_directory(),"src","staticresources",bundle_name))
    elif 'win32' in sys.platform:
        zip_file = util.zip_directory(os.path.join(util.mm_project_directory(),"resource-bundles",bundle_name), os.path.join(util.mm_project_directory(),"src","staticresources",bundle_name))
    print(zip_file)
    if zip_file.endswith(".zip"):
        os.rename(zip_file, zip_file[:-4])
    #compile
    file_path = os.path.join(util.mm_project_directory(),"src","staticresources",bundle_name)
    params = {
        "files" : [file_path]
    }
    mm.call('compile', params=params, message=message)
    util.send_usage_statistics('Deploy Resource Bundle')


def refresh(self, dirs):
    files = []
    for d in dirs:
        static_resource_location = os.path.join(util.mm_project_directory(), "src", "staticresources", os.path.basename(d))
        if os.path.isfile(static_resource_location):
            files.append(static_resource_location)
    create(self, files, True)


########NEW FILE########
__FILENAME__ = config
import logging
import os.path
import sys
import tempfile 
import sublime
from logging.handlers import RotatingFileHandler

logger = None

def __get_base_path():
    if hasattr(sys, 'frozen'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.dirname(__file__))

def __get_is_frozen():
    if hasattr(sys, 'frozen'):
        return True
    else:
        return False

def setup_logging():
    try:
        settings = sublime.load_settings('mavensmate.sublime-settings')

        logging.raiseExceptions = False
        logging.basicConfig(level=logging.DEBUG)

        log_location = settings.get('mm_log_location', tempfile.gettempdir())
        logging_handler = RotatingFileHandler(os.path.join(log_location, "mmui.log"), maxBytes=1*1024*1024, backupCount=5)

        #mm log setup
        global logger
        logger = logging.getLogger('mmui')
        logger.setLevel(logging.DEBUG)
        logger.propagate = False 
        logger.addHandler(logging_handler)
    except:
        pass #todo: https://github.com/joeferraro/MavensMate-SublimeText/issues/293

def debug(msg, obj=None):
    try:
        if obj != None and type(msg) is str:
            logger.debug(msg + ' ', obj)
            print('[MAVENSMATE UI]: ' + msg + ' ', obj)
        elif obj == None and type(msg) is str:
            logger.debug(msg)
            print('[MAVENSMATE UI]:',msg)
        else:
            logger.debug(msg)
            print('[MAVENSMATE UI]:',msg) 
    except:
        if obj != None and type(msg) is str:
            print('[MAVENSMATE UI]: ' + msg + ' ', obj)
        elif obj == None and type(msg) is str:
            print('[MAVENSMATE UI]:',msg)
        else:
            print('[MAVENSMATE UI]:',msg) 
       
mm_path = None
frozen = __get_is_frozen()
base_path = __get_base_path()
########NEW FILE########
__FILENAME__ = endpoints
import urllib.parse
from urllib.parse import urlparse
import sys
import json
sys.path.append('../')
import MavensMate.lib.server.lib.util as util
from MavensMate.lib.server.lib.util import BackgroundWorker
import MavensMate.lib.server.lib.config as gc

# async_request_queue holds list of active async requests
async_request_queue = {}

####################
## ASYNC REQUESTS ##
####################

def project_request(request_handler):
    '''
        POST /project
        {
            "project_name"  : "my project name"
            "username"      : "mm@force.com",
            "password"      : "force",
            "org_type"      : "developer",
            "package"       : {
                "ApexClass"     : "*",
                "ApexTrigger"   : ["Trigger1", "Trigger2"]
            }
        }
    '''
    run_async_operation(request_handler, 'new_project')

def project_existing_request(request_handler):
    '''
        POST /project/existing
        {
            "project_name"  : "my project name"
            "username"      : "mm@force.com",
            "password"      : "force",
            "org_type"      : "developer",
            "directory"     : "/path/to/project",
            "action"        : "existing"
        }
    '''
    run_async_operation(request_handler, 'new_project_from_existing_directory')

def project_edit_request(request_handler):
    '''
        POST /project/edit
        (body same as project_request)
    '''
    run_async_operation(request_handler, 'edit_project')

def project_upgrade_request(request_handler):
    '''
        POST /project/upgrade
        {
            "project_name"  : "my project name"
            "username"      : "mm@force.com",
            "password"      : "force",
            "org_type"      : "developer"
        }
    '''
    run_async_operation(request_handler, 'upgrade_project')

def execute_apex_request(request_handler):
    '''
        POST /apex/execute
        {
            "project_name"    : "my project name"
            "log_level"       : "DEBUG",
            "log_category"    : "APEX_CODE",
            "body"            : "String foo = 'bar';",
        }
    '''
    run_async_operation(request_handler, 'execute_apex')


def deploy_request(request_handler):
    '''
        POST /project/deploy
        call to deploy metadata to a server
        {
            "check_only"            : true,
            "rollback_on_error"     : true,
            "destinations"          : [
                {
                    "username"              : "username1@force.com",
                    "org_type"              : "developer"
                }
            ],
            "package"               : {
                "ApexClass" : "*"
            }
        }
    '''
    run_async_operation(request_handler, 'deploy')

def unit_test_request(request_handler):
    '''
        POST /project/unit_test
        {
            "classes" : [
                "UnitTestClass1", "UnitTestClass2"
            ],
            "run_all_tests" : false
        }
    '''
    gc.debug('in unit test method!')
    run_async_operation(request_handler, 'unit_test')
    
def metadata_index_request(request_handler):
    '''
        call to update the project .metadata index
    '''
    run_async_operation(request_handler, 'index_metadata')

def new_log_request(request_handler):
    '''
        call to create a new debug log
    '''
    run_async_operation(request_handler, 'new_log')

def metadata_list_request_async(request_handler):
    '''
        GET /metadata/list
        {
            "sid"             : "",
            "metadata_type"   : "",
            "murl"            : ""
        }
        call to get a list of metadata of a certain type
    '''
    run_async_operation(request_handler, 'list_metadata')

def generic_endpoint(request_handler):
    request_id = util.generate_request_id()
    params, json_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker(params["command"], params, False, request_id, json_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def generic_async_endpoint(request_handler):
    #params, raw_post_body, plugin_client = get_request_params(request_handler)
    run_async_operation(request_handler, None)


##########################
## SYNCHRONOUS REQUESTS ##
##########################

def get_active_session_request(request_handler):
    '''
        GET /session?username=mm@force.com&password=force&org_type=developer
    '''
    request_id = util.generate_request_id()
    params, json_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('get_active_session', params, False, request_id, json_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def update_credentials_request(request_handler):
    '''
        POST /project/creds
        {
            "project_name"  : "my project name"
            "username"      : "mm@force.com",
            "password"      : "force",
            "org_type"      : "developer",
        }
        NOTE: project name should not be updated, as it is used to find the project in question
        TODO: maybe we assign a unique ID to each project which will give users the flexibility
              to change the project name??
        TODO: we may need to implement a "clean" flag which will clean the project after creds
              have been updated
    '''
    request_id = util.generate_request_id()
    params, raw_post_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('update_credentials', params, False, request_id, raw_post_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def project_edit_subscription(request_handler):
    '''
        POST /project/subscription
        {
            "project_name"  : "my project name"
            "subscription"  : ["ApexClass", "ApexPage"]
        }
    '''
    request_id = util.generate_request_id()
    params, raw_post_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('update_subscription', params, False, request_id, raw_post_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)


def connections_list_request(request_handler):
    request_id = util.generate_request_id()
    params, raw_post_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('list_connections', params, False, request_id, raw_post_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def connections_new_request(request_handler):
    request_id = util.generate_request_id()
    params, raw_post_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('new_connection', params, False, request_id, raw_post_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def connections_delete_request(request_handler):
    request_id = util.generate_request_id()
    params, raw_post_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('delete_connection', params, False, request_id, raw_post_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def metadata_list_request(request_handler):
    '''
        GET /metadata/list
        {
            "sid"             : "",
            "metadata_type"   : "",
            "murl"            : ""
        }
        call to get a list of metadata of a certain type
    '''
    request_id = util.generate_request_id()
    params, json_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('list_metadata', params, False, request_id, json_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response)

def get_metadata_index(request_handler):
    '''
        GET /project/get_index
        {
            "project_name"  : "my project name",
            "keyword"       : "mykeyword" //optional
        }
        call to get the metadata index for a project
    '''
    request_id = util.generate_request_id()
    params, json_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('get_indexed_metadata', params, False, request_id, json_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response) 

def refresh_metadata_index(request_handler):
    '''
        GET /project/get_index/refresh
        {
            "project_name"      : "my project name",
            "metadata_types"    : ["ApexClass"]
        }
        call to refresh a certain type of metadata
    '''
    request_id = util.generate_request_id()
    params, json_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('refresh_metadata_index', params, False, request_id, json_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response) 

def connect_to_github(request_handler):
    '''
        POST /github/connect
        {
            "username"      : "myusername",
            "password"      : "mypassword"
        }
    '''
    request_id = util.generate_request_id()
    params, json_body, plugin_client = get_request_params(request_handler)
    worker_thread = BackgroundWorker('sign_in_with_github', params, False, request_id, json_body, plugin_client)
    worker_thread.start()
    worker_thread.join()
    response = worker_thread.response
    respond(request_handler, response) 

##########################
## END REQUEST HANDLERS ##
##########################


def run_async_operation(request_handler, operation_name):
    gc.debug('>>> running an async operation')
    request_id = util.generate_request_id()
    params, raw_post_body, plugin_client = get_request_params(request_handler)
    if operation_name == None and "command" in params:
        operation_name = params["command"]
    gc.debug(request_id)
    gc.debug(params)
    gc.debug(raw_post_body)
    
    worker_thread = BackgroundWorker(operation_name, params, True, request_id, raw_post_body, plugin_client)
    gc.debug('worker created')
    worker_thread.start()
    gc.debug('worker thread started')
    async_request_queue[request_id] = worker_thread
    gc.debug('placed into queue')

    return respond_with_async_request_id(request_handler, request_id)

#client polls this servlet to determine whether the request is done
#if the request IS done, it will respond with the body of the request
def status_request(request_handler):
    gc.debug('>>> status request')
    params, json_string, plugin_client = get_request_params(request_handler)
    gc.debug('>>> params: ')
    gc.debug(params)
    try:
        request_id = params['id']
    except:
        request_id = params['id'][0]
    gc.debug('>>> request id: ' + request_id)
    gc.debug('>>> async queue: ')
    gc.debug(async_request_queue)

    if request_id not in async_request_queue:
        response = { 'status' : 'error', 'id' : request_id, 'body' : 'Request ID was not found in async request queue.' }
        response_body = json.dumps(response)
        respond(request_handler, response_body, 'text/json')
    else:
        async_thread = async_request_queue[request_id]
        gc.debug('found thread in request queue, checking if alive')
        gc.debug(async_thread.is_alive())
        if async_thread.is_alive():
            gc.debug('>>> request is not ready')
            respond_with_async_request_id(request_handler, request_id)
        elif async_thread.is_alive() == False:
            gc.debug('>>> request is ready, returning response')
            async_request_queue.pop(request_id, None)
            respond(request_handler, async_thread.response, 'text/json')

def add_to_request_queue(request_id, p, q):
    async_request_queue[request_id] = { 'process' : p, 'queue' : q }

def get_request_params(request_handler):
    #print ('>>>>>> ', request_handler.path)
    #print ('>>>>>> ', request_handler.command)
    #print ('>>>>>> ', request_handler.headers)
    plugin_client = request_handler.headers.get('mm_plugin_client', 'SUBLIME_TEXT_2')
    if request_handler.command == 'POST':
        data_string = request_handler.rfile.read(int(request_handler.headers['Content-Length']))
        #print('>>>>>>> ', data_string)
        postvars = json.loads(data_string.decode('utf-8'))
        if 'package' in postvars:
            postvars['package'] = json.dumps(postvars['package'])
        return postvars, data_string, plugin_client
    elif request_handler.command == 'GET':
        params = urllib.parse.parse_qs(urlparse(request_handler.path).query) 
        #parse_qs(urlparse(request_handler.path).query)
        for key in params:
            if '[]' in key:
                params[key] = params[key]
            else:
                params[key] = params[key][0]
        return_params = {}
        for key in params:
            if '[]' in key:
                return_params[key.replace('[]','')] = params[key]
            else:
                return_params[key] = params[key]       
        json_string = json.dumps(return_params)
        return params, json_string, plugin_client

def process_request_in_background(worker):
    worker.run()




######################
## RESPONSE METHODS ##
######################

#this returns the request id after an initial async request
def respond_with_async_request_id(request_handler, request_id):
    response = { 'status' : 'pending', 'id' : request_id }
    json_response_body = json.dumps(response)
    gc.debug(json_response_body)
    respond(request_handler, json_response_body, 'text/json')

def respond(request_handler, body, type='text/json'):
    request_handler.send_response(200)
    request_handler.send_header('Content-type', type)
    request_handler.send_header('Access-Control-Allow-Origin', '*')
    request_handler.end_headers()
    request_handler.wfile.write(body.encode('utf-8'))
    return



##################
## PATH MAPPING ##
##################

mappings = {
    '/status'                   : { 'GET'   : status_request },     
    '/project'                  : { 'POST'  : project_request }, 
    '/project/edit'             : { 'POST'  : project_edit_request }, 
    '/project/subscription'     : { 'POST'  : project_edit_subscription }, 
    '/project/creds'            : { 'POST'  : update_credentials_request },
    '/project/deploy'           : { 'POST'  : deploy_request },
    '/project/unit_test'        : { 'POST'  : unit_test_request },
    '/project/get_index'        : { 'POST'  : get_metadata_index },
    '/project/refresh_index'    : { 'POST'  : refresh_metadata_index },    
    '/project/index'            : { 'POST'  : metadata_index_request },
    '/project/conns/list'       : { 'GET'   : connections_list_request },
    '/project/conns/new'        : { 'POST'  : connections_new_request },
    '/project/conns/delete'     : { 'POST'  : connections_delete_request },
    '/project/upgrade'          : { 'POST'  : project_upgrade_request },
    '/project/existing'         : { 'POST'  : project_existing_request },
    '/project/new_log'          : { 'POST'  : new_log_request },
    '/session'                  : { 'GET'   : get_active_session_request },
    '/apex/execute'             : { 'POST'  : execute_apex_request },
    '/metadata/list'            : { 'GET'   : metadata_list_request },
    '/metadata/list/async'      : { 'GET'   : metadata_list_request_async },
    '/github/connect'           : { 'POST'  : connect_to_github },
    '/generic'                  : { 'POST'  : generic_endpoint },
    '/generic/async'            : { 'POST'  : generic_async_endpoint }
}

########NEW FILE########
__FILENAME__ = handler
#import BaseHTTPServer
from http.server import BaseHTTPRequestHandler
import MavensMate.lib.server.lib.config as config

class Handler(BaseHTTPRequestHandler):
  # set mappings - dict of dicts - ex: {'/' : {'GET' : test}}
  # meaning, path / with GET request will map to test handler
    mappings = {}

    def main_handler(self, method='GET'):
        # get request url (without url params) and remove trailing /
        config.debug('>>> handling request')
        config.debug(self.path)

        request_url = self.path.split('?')[0]
        if request_url is not '/':
            request_url = request_url.rstrip('/')

        handler = None
        try:
            handler = self.mappings[request_url][method]
            #config.debug(handler)
        except KeyError:
            # no mapping found for the request
            self.send_response(404)
            self.end_headers()
            return

        try:
            handler(self)
        except KeyError:
            # method not found
            self.send_response(501)
            self.end_headers()
            return

    def do_GET(self):
        self.main_handler('GET')
        return

    def do_POST(self):
        print(self)
        self.main_handler('POST')
        return

    #to enable CORS
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', "*")
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "accept,origin,mm_plugin_client,content-type")
        self.send_header('Content-Length',0)
        self.send_header('Connection','close')
        self.end_headers()
        return

    def log_message(self, format, *args):
        return
########NEW FILE########
__FILENAME__ = server
import sys
import os
import BaseHTTPServer
import handler
import config
import lib.config as gc

server = None

def run(context_path='', port=9000):
    gc.debug('>>> starting local MavensMate server!')
    # set current working dir on python path
    base_dir = os.path.normpath(os.path.abspath(os.path.curdir))
    sys.path.insert(0, base_dir)
    handler.Handler.mappings = config.mappings
    server = BaseHTTPServer.HTTPServer((context_path, port), handler.Handler)
    server.serve_forever()

def stop():
    print('[MAVENSMATE] shutting down local MavensMate server')
    server.shutdown()
########NEW FILE########
__FILENAME__ = server_threaded
import sys
import os
import MavensMate.lib.server.lib.handler as handler
import MavensMate.lib.server.lib.endpoints as endpoints
import MavensMate.lib.server.lib.config as gc
import threading
import socketserver
from http.server import HTTPServer
#from BaseHTTPServer import HTTPServer
server = None

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def run(context_path='', port=9000):
    gc.debug('>>> starting threaded MavensMate server!')
    base_dir = os.path.normpath(os.path.abspath(os.path.curdir))
    sys.path.insert(0, base_dir)
    handler.Handler.mappings = endpoints.mappings
    server = ThreadedHTTPServer((context_path, port), handler.Handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    #server.serve_forever()

def stop():
    print('[MAVENSMATE] shutting down local MavensMate server')
    server.shutdown()
    #os.system("kill -9 `fuser -n tcp 9000`")
########NEW FILE########
__FILENAME__ = util
import os
import sys
import random
import string
import json
import threading
import subprocess
import pipes
import sublime
import MavensMate.lib.server.lib.config as global_config
import MavensMate.config as config

#this function is only used on async requests
def generate_request_id():
    return get_random_string()

def get_random_string(size=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def generate_error_response(message):
    res = {
        "success"   : False,
        "body_type" : "text",
        "body"      : message
    }
    return json.dumps(res)

#the main job of the backgroundworker is to submit a request for work to be done by mm
class BackgroundWorker(threading.Thread):
    def __init__(self, operation, params, async, request_id=None, payload=None, plugin_client='SUBLIME_TEXT_2'):
        self.operation      = operation
        self.params         = params
        self.request_id     = request_id
        self.async          = async
        self.payload        = payload
        self.plugin_client  = plugin_client
        self.response       = None
        self.mm_path        = sublime.load_settings('mavensmate.sublime-settings').get('mm_location')
        self.debug_mode     = sublime.load_settings('mavensmate.sublime-settings').get('mm_debug_mode')
        threading.Thread.__init__(self)

    def run(self):
        mm_response = None
        args = self.get_arguments()
        global_config.debug('>>> running thread arguments on next line!')
        global_config.debug(args)
        if self.debug_mode or 'darwin' not in sys.platform:
            print(self.payload)
            python_path = sublime.load_settings('mavensmate.sublime-settings').get('mm_python_location')

            if 'darwin' in sys.platform or sublime.load_settings('mavensmate.sublime-settings').get('mm_debug_location') != None:
                mm_loc = sublime.load_settings('mavensmate.sublime-settings').get('mm_debug_location')
            else:
                mm_loc = os.path.join(config.mm_dir,"mm","mm.py")
            #p = subprocess.Popen("{0} {1} {2}".format(python_path, pipes.quote(mm_loc), args), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        
            if 'linux' in sys.platform or 'darwin' in sys.platform:
                #osx, linux
                p = subprocess.Popen('\'{0}\' \'{1}\' {2}'.format(python_path, mm_loc, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            else:
                #windows
                if sublime.load_settings('mavensmate.sublime-settings').get('mm_debug_mode', False):
                    #user wishes to use system python
                    python_path = sublime.load_settings('mavensmate.sublime-settings').get('mm_python_location')
                    p = subprocess.Popen('"{0}" "{1}" {2}'.format(python_path, mm_loc, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                else:
                    python_path = os.path.join(os.environ["ProgramFiles"],"MavensMate","App","python.exe")
                    if not os.path.isfile(python_path):
                        python_path = python_path.replace("Program Files", "Program Files (x86)")
                    p = subprocess.Popen('"{0}" -E "{1}" {2}'.format(python_path, mm_loc, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

            #process = subprocess.Popen("{0} {1} {2}".format(python_path, pipes.quote(mm_loc), self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        else:
            p = subprocess.Popen("{0} {1}".format(pipes.quote(self.mm_path), args), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        #print("PAYLOAD: ",self.payload)
        #print("PAYLOAD TYPE: ",type(self.payload))
        if self.payload != None and type(self.payload) is str:
            self.payload = self.payload.encode('utf-8')
        p.stdin.write(self.payload)
        p.stdin.close()
        if p.stdout is not None: 
            mm_response = p.stdout.readlines()
        elif p.stderr is not None:
            mm_response = p.stderr.readlines()
        
        #response_body = '\n'.join(mm_response.decode('utf-8'))
        strs = []
        for line in mm_response:
            strs.append(line.decode('utf-8'))   
        response_body = '\n'.join(strs)

        global_config.debug('>>> got a response body')
        global_config.debug(response_body)

        if '--html' not in args:
            try:
                valid_json = json.loads(response_body)
            except:
                response_body = generate_error_response(response_body)

        self.response = response_body
         
    def get_arguments(self):
        args = {}
        args['-o'] = self.operation #new_project, get_active_session
        args['-c'] = self.plugin_client

        if self.operation == 'new_project':
            pass
        elif self.operation == 'checkout_project':
            pass  
        elif self.operation == 'get_active_session':
            pass 
        elif self.operation == 'update_credentials':
            pass
        elif self.operation == 'execute_apex':
            pass
        elif self.operation == 'deploy':
            args['--html'] = None
        elif self.operation == 'unit_test' or self.operation == 'test_async':
            args['--html'] = None
        elif self.operation == 'project_health_check':
            args['--html'] = None    
        #elif self.operation == 'index_metadata':
        #    args['--html'] = None    
                
        arg_string = []
        for x in args.keys():
            if args[x] != None:
                arg_string.append(x + ' ' + args[x] + ' ')
            else:
                arg_string.append(x + ' ')
        stripped_string = ''.join(arg_string).strip()
        return stripped_string
########NEW FILE########
__FILENAME__ = mmserver
# -*- coding: utf-8 -*-
import argparse
import MavensMate.lib.server.lib.server_threaded as server_threaded
import MavensMate.lib.server.lib.config as config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mmpath') 
    args = parser.parse_args()
    config.mm_path = args.mmpath
    try:
        server_threaded.run()
    except:
        config.debug("Server at port 9000 already running")

if __name__ == '__main__':
    main() 
########NEW FILE########
__FILENAME__ = server
"""
    Responsible for starting MavensMate UI server
"""
########NEW FILE########
__FILENAME__ = threads
import sublime
import threading
import sys

class HookedThread(threading.Thread):

    def __init__(self):
        run_old = self.run

        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise 
            except:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook
        threading.Thread.__init__(self)

class ThreadTracker(object):
    pending_threads = {}
    current_thread = {}

    @classmethod
    def add(cls, thread):
        #print('adding thread')
        thread_window_id = thread.window.id()
        if thread_window_id not in cls.pending_threads:
            cls.pending_threads[thread_window_id] = [thread]
        else:
            cls.pending_threads[thread_window_id].append(thread)

    @classmethod
    def remove(cls, thread):
        #print('removing thread from:')
        #print(cls.pending_threads)
        thread_window_id = thread.window.id()
        if thread_window_id in cls.pending_threads:
            pending_window_threads = cls.pending_threads[thread_window_id]
            if thread in pending_window_threads: pending_window_threads.remove(thread)
        
    @classmethod
    def get_last_added(cls, window):
        try:
            return cls.pending_threads.get(window.id())[0]
        except:
            return None
            
    @classmethod
    def set_current(cls, window, thread):
        cls.current_thread[window.id()] = thread

    @classmethod
    def get_current(cls, window):
        return cls.current_thread.get(window.id())

    #TODO: sometimes dead threads get stuck. thread.is_alive() will be false for those
    @classmethod
    def get_pending(cls, window):
        if window.id() in cls.pending_threads:
            threads_pending_in_window = cls.pending_threads[window.id()]
            threads_pending_in_window = [x for x in threads_pending_in_window if x.is_alive()]
            cls.pending_threads[window.id()] = threads_pending_in_window
            return cls.pending_threads[window.id()]
        else:
            return []

    @classmethod
    def get_pending_mm_panel_threads(cls, window):
        if window.id() in cls.pending_threads:
            ts = []
            for t in cls.pending_threads[window.id()]:
                if t.use_mm_panel and t.is_alive():
                    ts.append(t)
            return ts
        else:
            return []

def unset_current_thread(fn):

    def handler(self, *args, **kwargs):
        result = fn(self, *args, **kwargs)
        ThreadTracker.set_current(self.window_id, None)
        return result

    return handler

class PanelThreadProgress():
    """
    Animates an indicator, [=   ], in the MavensMate panel while a thread runs

    :param thread:
        The thread to track for activity

    :param message:
        The message to display next to the activity indicator

    :param success_message:
        The message to display once the thread is complete
    """

    def __init__(self, thread, success_message="TESTING", callback=None):
        self.thread = thread
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        self.callback = None
        sublime.set_timeout(lambda: self.run(0), 50)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'result'):
                #thread is done, we need to handle the result
                self.thread.callback(self.thread.operation, self.thread.process_id, self.thread.printer, self.thread.result, self.thread)
                if self.thread.alt_callback != None:
                    self.thread.alt_callback(self.thread.context)
                #self.thread.printer.panel.run_command('write_operation_status', {'text': self.thread.result, 'region': [self.thread.status_region.end(), self.thread.status_region.end()+10] })
                return
            if self.callback != None:
                self.callback()
            return

        #print(">>> POLLING PROGRESS")
        #we need to recalculate this every run in case a thread has responded and added
        #text to the panel
        process_region = self.thread.printer.panel.find(self.thread.process_id,0)
        status_region = self.thread.printer.panel.find('Result: ',process_region.begin())
        
        before = i % self.size
        after = (self.size - 1) - before

        text = '%s[%s=%s]' % \
            ('', ' ' * before, ' ' * after)

        self.thread.printer.panel.run_command('write_operation_status', {'text': text, 'region': [status_region.end(), status_region.end()+10] })

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 50)

class ThreadProgress():
    """
    Animates an indicator, [=   ], in the status area while a thread runs

    :param thread:
        The thread to track for activity

    :param message:
        The message to display next to the activity indicator

    :param success_message:
        The message to display once the thread is complete
    """

    def __init__(self, thread, message, success_message, callback=None):
        self.thread = thread
        self.message = message
        self.success_message = success_message
        self.addend = 1
        self.size = 8
        self.callback = None
        sublime.set_timeout(lambda: self.run(0), 100)

    def run(self, i):
        if not self.thread.is_alive():
            if hasattr(self.thread, 'result') and not self.thread.result:
                sublime.status_message('')
                return
            sublime.status_message(self.success_message)
            if self.callback != None:
                self.callback()
            return

        before = i % self.size
        after = (self.size - 1) - before

        sublime.status_message('%s [%s=%s]' % \
            (self.message, ' ' * before, ' ' * after))

        if not after:
            self.addend = -1
        if not before:
            self.addend = 1
        i += self.addend

        sublime.set_timeout(lambda: self.run(i), 100)
########NEW FILE########
__FILENAME__ = times
import datetime
import re
import math
import time

def timestamp_to_string(timestamp, format):
    date = datetime.datetime.fromtimestamp(timestamp)
    return good_strftime(date, format)
########NEW FILE########
__FILENAME__ = upgrader
import threading
import json
import os
import sys
import subprocess
import time
try:
    import plistlib
except:
    pass


try:
    from .threads import ThreadTracker
    from .threads import ThreadProgress
    from .threads import PanelThreadProgress
except ImportError as e:
    print("[MAVENSMATE] import error: ", e)

try: 
    import urllib
except ImportError:
    import urllib.request as urllib
import sublime

def execute(printer):
    threads = []
    thread = ManualUpgrader(printer)
    threads.append(thread)        
    thread.start()

def handle_result(operation, process_id, printer, result, thread):
    process_region = printer.panel.find(process_id,0)
    status_region = printer.panel.find('Result:',process_region.begin())
    printer.panel.run_command('write_operation_status', {'text': result, 'region': [status_region.end(), status_region.end()+10] })
    printer.scroll_to_bottom()

class ManualUpgrader(threading.Thread):
    def __init__(self, printer):
        self.printer        = printer
        self.operation      = "upgrade"
        self.process_id     = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())
        self.result         = None
        self.callback       = handle_result
        self.alt_callback   = None
        self.status_region  = None

        self.printer.show()
        self.printer.writeln(' ')
        self.printer.writeln('==============================================')
        self.printer.writeln("Reloading MavensMate for Sublime Text Plugin. You will need to restart Sublime Text when update is complete. If you have any issues updating, open a terminal and run the python installer script located here: https://raw.github.com/joeferraro/MavensMate-SublimeText/master/install.py. Example (from the terminal): $ python install.py")
        self.printer.writeln('Timestamp: '+self.process_id)

        threading.Thread.__init__(self)

    def run(self):
        if 'linux' in sys.platform or 'darwin' in sys.platform:
            ThreadProgress(self, "Updating MavensMate for Sublime Text", 'MavensMate update complete. Please restart Sublime Text.')
            process = None
            
            updater_path = os.path.join(sublime.packages_path(),"MavensMate","install.py")
            settings = sublime.load_settings('mavensmate.sublime-settings')
            python_location = settings.get("mm_python_location")
            process = subprocess.Popen('"{0}" "{1}"'.format(python_location, updater_path), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        
            mm_response = ""
            if process != None:
                if process.stdout is not None: 
                    mm_response = process.stdout.readlines()
                elif process.stderr is not None:
                    mm_response = process.stderr.readlines()
                try:
                    response_body = '\n'.join(mm_response)
                except:
                    strs = []
                    for line in mm_response:
                        strs.append(line.decode('utf-8'))   
                    response_body = '\n'.join(strs)

            print('[MAVENSMATE] response from upgrader: ' + response_body)
            self.result = response_body

class AutomaticUpgrader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        try:
            json_data = open(os.path.join(sublime.packages_path(),"MavensMate","packages.json"))
            data = json.load(json_data)
            json_data.close()
            current_version = data["packages"][0]["platforms"]["osx"][0]["version"]
            if 'linux' in sys.platform:
                response = os.popen('curl https://raw.github.com/joeferraro/MavensMate-SublimeText/master/packages.json').read()
            else:
                response = urllib.request.urlopen('https://raw.github.com/joeferraro/MavensMate-SublimeText/master/packages.json').read().decode('utf-8')
            j = json.loads(response)
            latest_version = j["packages"][0]["platforms"]["osx"][0]["version"]
            release_notes = "\n\nRelease Notes: "
            try:
                release_notes += j["packages"][0]["platforms"]["osx"][0]["release_notes"] + "\n\n"
            except:
                release_notes = ""

            installed_version_int = int(float(current_version.replace(".", "")))
            server_version_int = int(float(latest_version.replace(".", "")))

            needs_update = False
            if server_version_int > installed_version_int:
                needs_update = True
            
            if needs_update == True:
                if 'linux' in sys.platform:
                    sublime.message_dialog("A new version of MavensMate for Sublime Text ("+latest_version+") is available."+release_notes+"To update, select MavensMate > Update MavensMate from the Sublime Text menu.")
                elif 'darwin' in sys.platform:
                    sublime.message_dialog("A new version of MavensMate for Sublime Text ("+latest_version+") is available."+release_notes+"To update, select MavensMate > Update MavensMate from the Sublime Text menu.")
                else: #windows
                    if sublime.ok_cancel_dialog("A new version of MavensMate for Sublime Text ("+latest_version+") is available."+release_notes+"Would you like to update?"):
                        updater_path = os.path.join(os.environ["ProgramFiles"],"MavensMate","MavensMate-SublimeText.exe")
                        if not os.path.isfile(updater_path):
                            updater_path = updater_path.replace("Program Files", "Program Files (x86)")
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        subprocess.Popen('"{0}"'.format(updater_path), startupinfo=startupinfo)
            else:
                if 'darwin' in sys.platform:
                    settings = sublime.load_settings('mavensmate.sublime-settings')
                    mm_app_location = settings.get("mm_app_location")
                    plist_path = mm_app_location+"/Contents/Info.plist"

                    plist = plistlib.readPlist(plist_path)
                    version_number = plist['CFBundleVersion']
                    installed_version_int = int(float(version_number.replace(".", "")))
                    if installed_version_int <= 383:
                        sublime.message_dialog("A new version of MavensMate.app is available and we strongly encourage you to update. If you are running 0.38.0, you likely need to manually download and re-install from mavensmate.com.")

        except BaseException as e:
            # import traceback
            # import sys
            # traceback.print_exc(file=sys.stdout)            
            print('[MAVENSMATE] skipping update check')
            print(e)
########NEW FILE########
__FILENAME__ = usage_reporter
import threading
import json
import plistlib
import sublime
import os
import sys
try:
    import MavensMate.config as config
except:
    import config
try: 
    import urllib
except ImportError:
    import urllib.request as urllib
try:
    from uuid import getnode as get_mac
except:
    pass


class UsageReporter(threading.Thread):
    def __init__(self, action):
        self.action = action
        self.response = None
        threading.Thread.__init__(self)

    def run(self):
        try:
            settings = sublime.load_settings('mavensmate.sublime-settings')
            ip_address = ''
            try:
                #get ip address
                if 'linux' in sys.platform:
                    ip_address = os.popen('curl http://ip.42.pl/raw').read()
                else:
                    ip_address = urllib.request.urlopen('http://ip.42.pl/raw').read()
            except:
                ip_address = 'unknown'

            #get current version of mavensmate
            #print(os.path.join(config.mm_dir,"packages.json"))
            json_data = open(os.path.join(config.mm_dir,"packages.json"))
            data = json.load(json_data)
            json_data.close()
            current_version = data["packages"][0]["platforms"]["osx"][0]["version"]

            mm_version = ''
            if 'darwin' in sys.platform:
                try:
                    dic = plistlib.readPlist(os.path.join(settings.get('mm_app_location'), 'Contents', 'Info.plist'))
                    if 'CFBundleVersion' in dic:
                        mm_version = dic['CFBundleVersion']
                except BaseException as e:
                    print(e)
                    pass

            if ip_address == None:
                ip_address = 'unknown'        
            try:
                mac = str(get_mac())
            except:
                mac = 'unknown'
            if 'linux' in sys.platform:
                b = 'foo=bar&ip_address='+ip_address+'&action='+self.action+'&platform='+sys.platform+'&version='+current_version+'&mac_address='+mac
                req = os.popen("curl https://mavensmate.appspot.com/usage -d='"+b+"'").read()
                self.response = req
            else:
                b = 'mac_address='+mac+'&version='+current_version+'&ip_address='+ip_address.decode('utf-8')+'&action='+self.action+'&mm_version='+mm_version+'&platform='+sys.platform
                b = b.encode('utf-8')
                #post to usage servlet
                headers = { "Content-Type":"application/x-www-form-urlencoded" }
                handler = urllib.request.HTTPSHandler(debuglevel=0)
                opener = urllib.request.build_opener(handler)
                req = urllib.request.Request("https://mavensmate.appspot.com/usage", data=b, headers=headers)
                self.response = opener.open(req).read()
        except Exception as e: 
            #traceback.print_exc(file=sys.stdout)
            print('[MAVENSMATE] failed to send usage statistic')
            print(e)

########NEW FILE########
__FILENAME__ = vf
tag_list = [
  "apex:actionFunction",
  "apex:actionPoller",
  "apex:actionRegion",
  "apex:actionStatus",
  "apex:actionSupport",
  "apex:areaSeries",
  "apex:attribute",
  "apex:axis",
  "apex:barSeries",
  "apex:canvasApp",
  "apex:chart",
  "apex:chartLabel",
  "apex:chartTips",
  "apex:column",
  "apex:commandButton",
  "apex:commandLink",
  "apex:component",
  "apex:componentBody",
  "apex:composition",
  "apex:dataList",
  "apex:dataTable",
  "apex:define",
  "apex:detail",
  "apex:dynamicComponent",
  "apex:emailPublisher",
  "apex:enhancedList",
  "apex:facet",
  "apex:flash",
  "apex:form",
  "apex:gaugeSeries",
  "apex:iframe",
  "apex:image",
  "apex:include",
  "apex:includeScript",
  "apex:inlineEditSupport",
  "apex:inputCheckbox",
  "apex:inputField",
  "apex:inputFile",
  "apex:inputHidden",
  "apex:inputSecret",
  "apex:inputText",
  "apex:inputTextarea",
  "apex:insert",
  "apex:legend",
  "apex:lineSeries",
  "apex:listViews",
  "apex:logCallPublisher",
  "apex:message",
  "apex:messages",
  "apex:outputField",
  "apex:outputLabel",
  "apex:outputLink",
  "apex:outputPanel",
  "apex:outputText",
  "apex:page",
  "apex:pageBlock",
  "apex:pageBlockButtons",
  "apex:pageBlockSection",
  "apex:pageBlockSectionItem",
  "apex:pageBlockTable",
  "apex:pageMessage",
  "apex:pageMessages",
  "apex:panelBar",
  "apex:panelBarItem",
  "apex:panelGrid",
  "apex:panelGroup",
  "apex:param",
  "apex:pieSeries",
  "apex:radarSeries",
  "apex:relatedList",
  "apex:repeat",
  "apex:scatterSeries",
  "apex:scontrol",
  "apex:sectionHeader",
  "apex:selectCheckboxes",
  "apex:selectList",
  "apex:selectOption",
  "apex:selectOptions",
  "apex:selectRadio",
  "apex:stylesheet",
  "apex:tab",
  "apex:tabPanel",
  "apex:toolbar",
  "apex:toolbarGroup",
  "apex:variable",
  "apex:vote",
  "chatter:feed",
  "chatter:feedWithFollowers",
  "chatter:follow",
  "chatter:followers",
  "chatter:newsfeed",
  "chatter:userPhotoUpload",
  "chatteranswers:allfeeds",
  "chatteranswers:changepassword",
  "chatteranswers:forgotpassword",
  "chatteranswers:forgotpasswordconfirm",
  "chatteranswers:help",
  "chatteranswers:login",
  "chatteranswers:registration",
  "chatteranswers:singleitemfeed",
  "flow:interview",
  "ideas:detailOutputLink",
  "ideas:listOutputLink",
  "ideas:profileListOutputLink",
  "knowledge:articleCaseToolbar",
  "knowledge:articleList",
  "knowledge:articleRendererToolbar",
  "knowledge:articleTypeList",
  "knowledge:categoryList",
  "liveAgent:clientChat",
  "liveAgent:clientChatAlertMessage",
  "liveAgent:clientChatEndButton",
  "liveAgent:clientChatInput",
  "liveAgent:clientChatLog",
  "liveAgent:clientChatMessages",
  "liveAgent:clientChatQueuePosition",
  "liveAgent:clientChatSaveButton",
  "liveAgent:clientChatSendButton",
  "liveAgent:clientChatStatusMessage",
  "messaging:attachment",
  "messaging:emailHeader",
  "messaging:emailTemplate",
  "messaging:htmlEmailBody",
  "messaging:plainTextEmailBody",
  "site:googleAnalyticsTracking",
  "site:previewAsAdmin",
  "social:profileViewer",
  "support:caseArticles",
  "support:caseFeed",
  "support:clickToDial",
  "support:portalPublisher"
]

tag_defs = {
  "apex:attribute": {
    "simple": True,
    "attribs": {
      "access": {
        "type": "String"
      },
      "assignTo": {
        "type": "Object"
      },
      "default": {
        "type": "String"
      },
      "description": {
        "type": "String"
      },
      "encode": {
        "type": "Boolean"
      },
      "id": {
        "type": "String"
      },
      "name": {
        "type": "String"
      },
      "required": {
        "type": "Boolean"
      },
      "type": {
        "type": "String"
      }
    }
  },
  "apex:actionFunction": {
    "simple": True,
    "attribs": {
      "action": {
        "type": "ApexPages.Action"
      },
      "focus": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "name": {
        "type": "String"
      },
      "onbeforedomupdate": {
        "type": "String"
      },
      "oncomplete": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "status": {
        "type": "String"
      },
      "timeout": {
        "type": "Integer"
      }
    }
  },
  "apex:actionPoller": {
    "simple": True,
    "attribs": {
      "action": {
        "type": "ApexPages.Action"
      },
      "enabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "interval": {
        "type": "Integer"
      },
      "oncomplete": {
        "type": "String"
      },
      "onsubmit": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "status": {
        "type": "String"
      },
      "timeout": {
        "type": "Integer"
      }
    }
  },
  "apex:actionRegion": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "renderRegionOnly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:actionStatus": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "for": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "layout": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onstart": {
        "type": "String"
      },
      "onstop": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "startStyle": {
        "type": "String"
      },
      "startStyleClass": {
        "type": "String"
      },
      "startText": {
        "type": "String"
      },
      "stopStyle": {
        "type": "String"
      },
      "stopStyleClass": {
        "type": "String"
      },
      "stopText": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:actionSupport": {
    "simple": True,
    "attribs": {
      "action": {
        "type": "ApexPages.Action"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "disableDefault": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "event": {
        "type": "String"
      },
      "focus": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "onbeforedomupdate": {
        "type": "String"
      },
      "oncomplete": {
        "type": "String"
      },
      "onsubmit": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "status": {
        "type": "String"
      },
      "timeout": {
        "type": "Integer"
      }
    }
  },
  "apex:areaSeries": {
    "simple": False,
    "attribs": {
      "axis": {
        "type": "String"
      },
      "colorSet": {
        "type": "String"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "highlightLineWidth": {
        "type": "Integer"
      },
      "highlightOpacity": {
        "type": "String"
      },
      "highlightStrokeColor": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "opacity": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "showInLegend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      },
      "xField": {
        "type": "String"
      },
      "yField": {
        "type": "String"
      }
    }
  },
  "apex:axis": {
    "simple": False,
    "attribs": {
      "dashSize": {
        "type": "Integer"
      },
      "fields": {
        "type": "String"
      },
      "grid": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "gridFill": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "margin": {
        "type": "Integer"
      },
      "maximum": {
        "type": "Integer"
      },
      "minimum": {
        "type": "Integer"
      },
      "position": {
        "type": "String",
        "values": [
          "bottom",
          "gauge",
          "left",
          "radial",
          "right",
          "top"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "steps": {
        "type": "Integer"
      },
      "title": {
        "type": "String"
      },
      "type": {
        "type": "String",
        "values": [
          "Category",
          "Gauge",
          "Numeric",
          "Radial"
        ]
      }
    }
  },
  "apex:barSeries": {
    "simple": False,
    "attribs": {
      "axis": {
        "type": "String"
      },
      "colorSet": {
        "type": "String"
      },
      "colorsProgressWithinSeries": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "groupGutter": {
        "type": "Integer"
      },
      "gutter": {
        "type": "Integer"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "highlightColor": {
        "type": "String"
      },
      "highlightLineWidth": {
        "type": "Integer"
      },
      "highlightOpacity": {
        "type": "String"
      },
      "highlightStroke": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "orientation": {
        "type": "String",
        "values": [
          "horizontal",
          "vertical"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "showInLegend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "stacked": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      },
      "xField": {
        "type": "String"
      },
      "xPadding": {
        "type": "Integer"
      },
      "yField": {
        "type": "String"
      },
      "yPadding": {
        "type": "Integer"
      }
    }
  },
  "apex:canvasApp": {
    "simple": True,
    "attribs": {
      "applicationName": {
        "type": "String"
      },
      "border": {
        "type": "String"
      },
      "canvasId": {
        "type": "String"
      },
      "containerId": {
        "type": "String"
      },
      "developerName": {
        "type": "String"
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "maxHeight": {
        "type": "String"
      },
      "maxWidth": {
        "type": "String"
      },
      "namespacePrefix": {
        "type": "String"
      },
      "onCanvasAppError": {
        "type": "String"
      },
      "onCanvasAppLoad": {
        "type": "String"
      },
      "parameters": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "scrolling": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:chart": {
    "simple": False,
    "attribs": {
      "animate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "background": {
        "type": "String"
      },
      "colorSet": {
        "type": "String"
      },
      "data": {
        "type": "Object"
      },
      "floating": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "height": {
        "type": "String"
      },
      "hidden": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "legend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "name": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "renderTo": {
        "type": "String"
      },
      "resizable": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "theme": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:chartLabel": {
    "simple": True,
    "attribs": {
      "color": {
        "type": "String"
      },
      "display": {
        "type": "String",
        "values": [
          "insideEnd",
          "insideStart",
          "middle",
          "none",
          "outside",
          "over",
          "rotate",
          "under"
        ]
      },
      "field": {
        "type": "String"
      },
      "font": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "minMargin": {
        "type": "Integer"
      },
      "orientation": {
        "type": "String",
        "values": [
          "horizontal",
          "vertical"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "rotate": {
        "type": "Integer"
      }
    }
  },
  "apex:chartTips": {
    "simple": True,
    "attribs": {
      "height": {
        "type": "Integer"
      },
      "id": {
        "type": "String"
      },
      "labelField": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "trackMouse": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "valueField": {
        "type": "String"
      },
      "width": {
        "type": "Integer"
      }
    }
  },
  "apex:column": {
    "simple": True,
    "attribs": {
      "breakBefore": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "colspan": {
        "type": "Integer"
      },
      "dir": {
        "type": "String"
      },
      "footerClass": {
        "type": "String"
      },
      "footerValue": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "headerValue": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rowspan": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:commandButton": {
    "simple": True,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "action": {
        "type": "ApexPages.Action"
      },
      "alt": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "image": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "oncomplete": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "status": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "timeout": {
        "type": "Integer"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:commandLink": {
    "simple": True,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "action": {
        "type": "ApexPages.Action"
      },
      "charset": {
        "type": "String"
      },
      "coords": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "hreflang": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "oncomplete": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rel": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "rev": {
        "type": "String"
      },
      "shape": {
        "type": "String"
      },
      "status": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "target": {
        "type": "String"
      },
      "timeout": {
        "type": "Integer"
      },
      "title": {
        "type": "String"
      },
      "type": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:composition": {
    "simple": False,
    "attribs": {
      "rendered": {
        "type": "String"
      },
      "template": {
        "type": "ApexPages.PageReference"
      }
    }
  },
  "apex:dataList": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "first": {
        "type": "Integer"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rows": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "type": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      },
      "var": {
        "type": "String"
      }
    }
  },
  "apex:dataTable": {
    "simple": False,
    "attribs": {
      "align": {
        "type": "String"
      },
      "bgcolor": {
        "type": "String"
      },
      "border": {
        "type": "String"
      },
      "captionClass": {
        "type": "String"
      },
      "captionStyle": {
        "type": "String"
      },
      "cellpadding": {
        "type": "String"
      },
      "cellspacing": {
        "type": "String"
      },
      "columnClasses": {
        "type": "String"
      },
      "columns": {
        "type": "Integer"
      },
      "columnsWidth": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "first": {
        "type": "Integer"
      },
      "footerClass": {
        "type": "String"
      },
      "frame": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onRowClick": {
        "type": "String"
      },
      "onRowDblClick": {
        "type": "String"
      },
      "onRowMouseDown": {
        "type": "String"
      },
      "onRowMouseMove": {
        "type": "String"
      },
      "onRowMouseOut": {
        "type": "String"
      },
      "onRowMouseOver": {
        "type": "String"
      },
      "onRowMouseUp": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rowClasses": {
        "type": "String"
      },
      "rows": {
        "type": "Integer"
      },
      "rules": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "summary": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      },
      "var": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:define": {
    "simple": False,
    "attribs": {
      "name": {
        "type": "String"
      }
    }
  },
  "apex:detail": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "inlineEdit": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "oncomplete": {
        "type": "String"
      },
      "relatedList": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "relatedListHover": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rerender": {
        "type": "Object"
      },
      "showChatter": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "subject": {
        "type": "String"
      },
      "title": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:dynamicComponent": {
    "simple": True,
    "attribs": {
      "componentValue": {
        "type": "UIComponent"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:enhancedList": {
    "simple": True,
    "attribs": {
      "customizable": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "height": {
        "type": "Integer"
      },
      "id": {
        "type": "String"
      },
      "listId": {
        "type": "String"
      },
      "oncomplete": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "rowsPerPage": {
        "type": "Integer"
      },
      "type": {
        "type": "String"
      },
      "width": {
        "type": "Integer"
      }
    }
  },
  "apex:facet": {
    "simple": False,
    "attribs": {
      "name": {
        "type": "String"
      }
    }
  },
  "apex:flash": {
    "simple": False,
    "attribs": {
      "flashvars": {
        "type": "String"
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "loop": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "play": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "src": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:form": {
    "simple": False,
    "attribs": {
      "accept": {
        "type": "String"
      },
      "acceptcharset": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "enctype": {
        "type": "String"
      },
      "forceSSL": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onreset": {
        "type": "String"
      },
      "onsubmit": {
        "type": "String"
      },
      "prependId": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "target": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:gaugeSeries": {
    "simple": False,
    "attribs": {
      "colorSet": {
        "type": "String"
      },
      "dataField": {
        "type": "String"
      },
      "donut": {
        "type": "Integer"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "labelField": {
        "type": "String"
      },
      "needle": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:iframe": {
    "simple": True,
    "attribs": {
      "frameborder": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "scrolling": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "src": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:image": {
    "simple": True,
    "attribs": {
      "alt": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "ismap": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "lang": {
        "type": "String"
      },
      "longdesc": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "url": {
        "type": "String"
      },
      "usemap": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:include": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "pageName": {
        "type": "ApexPages.PageReference"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:includeScript": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:inlineEditSupport": {
    "simple": True,
    "attribs": {
      "changedStyleClass": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "event": {
        "type": "String"
      },
      "hideOnEdit": {
        "type": "Object"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "resetFunction": {
        "type": "String"
      },
      "showOnEdit": {
        "type": "Object"
      }
    }
  },
  "apex:inputCheckbox": {
    "simple": True,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "selected": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:inputField": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "taborderhint": {
        "type": "Integer"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:inputFile": {
    "simple": False,
    "attribs": {
      "accept": {
        "type": "String"
      },
      "accessKey": {
        "type": "String"
      },
      "alt": {
        "type": "String"
      },
      "contentType": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "fileName": {
        "type": "String"
      },
      "fileSize": {
        "type": "Integer"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "java:\/\/java.lang.Boolean"
      },
      "size": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleclass": {
        "type": "String"
      },
      "tabindex": {
        "type": "Integer"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Blob"
      }
    }
  },
  "apex:inputHidden": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:inputSecret": {
    "simple": True,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "alt": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "maxlength": {
        "type": "Integer"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "readonly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "redisplay": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "size": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:inputText": {
    "simple": True,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "alt": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "maxlength": {
        "type": "Integer"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "size": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:inputTextarea": {
    "simple": True,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "cols": {
        "type": "Integer"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "readonly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "richText": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rows": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:insert": {
    "simple": False,
    "attribs": {
      "name": {
        "type": "String"
      }
    }
  },
  "apex:legend": {
    "simple": False,
    "attribs": {
      "font": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "padding": {
        "type": "Integer"
      },
      "position": {
        "type": "String",
        "values": [
          "bottom",
          "left",
          "right",
          "top"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "spacing": {
        "type": "Integer"
      }
    }
  },
  "apex:lineSeries": {
    "simple": False,
    "attribs": {
      "axis": {
        "type": "String"
      },
      "fill": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "fillColor": {
        "type": "String"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "highlightStrokeWidth": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "markerFill": {
        "type": "String"
      },
      "markerSize": {
        "type": "Integer"
      },
      "markerType": {
        "type": "String",
        "values": [
          "circle",
          "cross"
        ]
      },
      "opacity": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "showInLegend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "smooth": {
        "type": "Integer"
      },
      "strokeColor": {
        "type": "String"
      },
      "strokeWidth": {
        "type": "String"
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      },
      "xField": {
        "type": "String"
      },
      "yField": {
        "type": "String"
      }
    }
  },
  "apex:listViews": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "type": {
        "type": "String"
      }
    }
  },
  "apex:message": {
    "simple": True,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "for": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:messages": {
    "simple": True,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "globalOnly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "layout": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:outputField": {
    "simple": True,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:outputLabel": {
    "simple": False,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "escape": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "for": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:outputLink": {
    "simple": False,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "charset": {
        "type": "String"
      },
      "coords": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "hreflang": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rel": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rev": {
        "type": "String"
      },
      "shape": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "target": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "type": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:outputPanel": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "layout": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:outputText": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "escape": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:page": {
    "simple": False,
    "attribs": {
      "action": {
        "type": "ApexPages.Action"
      },
      "apiVersion": {
        "type": "double"
      },
      "applyBodyTag": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "applyHtmlTag": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "cache": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "contentType": {
        "type": "String"
      },
      "controller": {
        "type": "String"
      },
      "deferLastCommandUntilReady": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "docType": {
        "type": "String"
      },
      "expires": {
        "type": "Integer"
      },
      "extensions": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "language": {
        "type": "String"
      },
      "manifest": {
        "type": "String"
      },
      "name": {
        "type": "String"
      },
      "pageStyle": {
        "type": "String"
      },
      "readOnly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "recordSetVar": {
        "type": "String"
      },
      "renderAs": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "setup": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "showChat": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "showHeader": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "sidebar": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "standardController": {
        "type": "String"
      },
      "standardStylesheets": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "tabStyle": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "wizard": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:pageBlock": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "helpTitle": {
        "type": "String"
      },
      "helpUrl": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "mode": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "tabStyle": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:pageBlockButtons": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "location": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:pageBlockSection": {
    "simple": False,
    "attribs": {
      "collapsible": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "columns": {
        "type": "Integer"
      },
      "dir": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "showHeader": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:pageBlockSectionItem": {
    "simple": False,
    "attribs": {
      "dataStyle": {
        "type": "String"
      },
      "dataStyleClass": {
        "type": "String"
      },
      "dataTitle": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "helpText": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "labelStyle": {
        "type": "String"
      },
      "labelStyleClass": {
        "type": "String"
      },
      "labelTitle": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onDataclick": {
        "type": "String"
      },
      "onDatadblclick": {
        "type": "String"
      },
      "onDatakeydown": {
        "type": "String"
      },
      "onDatakeypress": {
        "type": "String"
      },
      "onDatakeyup": {
        "type": "String"
      },
      "onDatamousedown": {
        "type": "String"
      },
      "onDatamousemove": {
        "type": "String"
      },
      "onDatamouseout": {
        "type": "String"
      },
      "onDatamouseover": {
        "type": "String"
      },
      "onDatamouseup": {
        "type": "String"
      },
      "onLabelclick": {
        "type": "String"
      },
      "onLabeldblclick": {
        "type": "String"
      },
      "onLabelkeydown": {
        "type": "String"
      },
      "onLabelkeypress": {
        "type": "String"
      },
      "onLabelkeyup": {
        "type": "String"
      },
      "onLabelmousedown": {
        "type": "String"
      },
      "onLabelmousemove": {
        "type": "String"
      },
      "onLabelmouseout": {
        "type": "String"
      },
      "onLabelmouseover": {
        "type": "String"
      },
      "onLabelmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:pageBlockTable": {
    "simple": False,
    "attribs": {
      "align": {
        "type": "String"
      },
      "border": {
        "type": "String"
      },
      "captionClass": {
        "type": "String"
      },
      "captionStyle": {
        "type": "String"
      },
      "cellpadding": {
        "type": "String"
      },
      "cellspacing": {
        "type": "String"
      },
      "columnClasses": {
        "type": "String"
      },
      "columns": {
        "type": "Integer"
      },
      "columnsWidth": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "first": {
        "type": "Integer"
      },
      "footerClass": {
        "type": "String"
      },
      "frame": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onRowClick": {
        "type": "String"
      },
      "onRowDblClick": {
        "type": "String"
      },
      "onRowMouseDown": {
        "type": "String"
      },
      "onRowMouseMove": {
        "type": "String"
      },
      "onRowMouseOut": {
        "type": "String"
      },
      "onRowMouseOver": {
        "type": "String"
      },
      "onRowMouseUp": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rowClasses": {
        "type": "String"
      },
      "rows": {
        "type": "Integer"
      },
      "rules": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "summary": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      },
      "var": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:pageMessage": {
    "simple": False,
    "attribs": {
      "detail": {
        "type": "String"
      },
      "escape": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "severity": {
        "type": "String"
      },
      "strength": {
        "type": "Integer"
      },
      "summary": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:pageMessages": {
    "simple": False,
    "attribs": {
      "escape": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "showDetail": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:panelBar": {
    "simple": False,
    "attribs": {
      "contentClass": {
        "type": "String"
      },
      "contentStyle": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "headerClassActive": {
        "type": "String"
      },
      "headerStyle": {
        "type": "String"
      },
      "headerStyleActive": {
        "type": "String"
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "items": {
        "type": "Object"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "switchType": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      },
      "var": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:panelBarItem": {
    "simple": False,
    "attribs": {
      "contentClass": {
        "type": "String"
      },
      "contentStyle": {
        "type": "String"
      },
      "expanded": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "headerClassActive": {
        "type": "String"
      },
      "headerStyle": {
        "type": "String"
      },
      "headerStyleActive": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "name": {
        "type": "Object"
      },
      "onenter": {
        "type": "String"
      },
      "onleave": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:panelGrid": {
    "simple": False,
    "attribs": {
      "bgcolor": {
        "type": "String"
      },
      "border": {
        "type": "Integer"
      },
      "captionClass": {
        "type": "String"
      },
      "captionStyle": {
        "type": "String"
      },
      "cellpadding": {
        "type": "String"
      },
      "cellspacing": {
        "type": "String"
      },
      "columnClasses": {
        "type": "String"
      },
      "columns": {
        "type": "Integer"
      },
      "dir": {
        "type": "String"
      },
      "footerClass": {
        "type": "String"
      },
      "frame": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rowClasses": {
        "type": "String"
      },
      "rules": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "summary": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:panelGroup": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "layout": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      }
    }
  },
  "apex:param": {
    "simple": True,
    "attribs": {
      "assignTo": {
        "type": "Object"
      },
      "id": {
        "type": "String"
      },
      "name": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:pieSeries": {
    "simple": False,
    "attribs": {
      "colorSet": {
        "type": "String"
      },
      "dataField": {
        "type": "String"
      },
      "donut": {
        "type": "Integer"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "labelField": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "showInLegend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "apex:radarSeries": {
    "simple": False,
    "attribs": {
      "fill": {
        "type": "String"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "markerFill": {
        "type": "String"
      },
      "markerSize": {
        "type": "Integer"
      },
      "markerType": {
        "type": "String",
        "values": [
          "circle",
          "cross"
        ]
      },
      "opacity": {
        "type": "Integer"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "showInLegend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "strokeColor": {
        "type": "String"
      },
      "strokeWidth": {
        "type": "Integer"
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      },
      "xField": {
        "type": "String"
      },
      "yField": {
        "type": "String"
      }
    }
  },
  "apex:relatedList": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "list": {
        "type": "String"
      },
      "pageSize": {
        "type": "Integer"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "subject": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:repeat": {
    "simple": False,
    "attribs": {
      "first": {
        "type": "Integer"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rows": {
        "type": "Integer"
      },
      "value": {
        "type": "Object"
      },
      "var": {
        "type": "String"
      }
    }
  },
  "apex:scatterSeries": {
    "simple": False,
    "attribs": {
      "axis": {
        "type": "String"
      },
      "highlight": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "id": {
        "type": "String"
      },
      "markerFill": {
        "type": "String"
      },
      "markerSize": {
        "type": "Integer"
      },
      "markerType": {
        "type": "String",
        "values": [
          "circle",
          "cross"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendererFn": {
        "type": "String"
      },
      "showInLegend": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "tips": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      },
      "xField": {
        "type": "String"
      },
      "yField": {
        "type": "String"
      }
    }
  },
  "apex:scontrol": {
    "simple": True,
    "attribs": {
      "controlName": {
        "type": "String"
      },
      "height": {
        "type": "Integer"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "scrollbars": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "subject": {
        "type": "Object"
      },
      "width": {
        "type": "Integer"
      }
    }
  },
  "apex:sectionHeader": {
    "simple": True,
    "attribs": {
      "description": {
        "type": "String"
      },
      "help": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "printUrl": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "subtitle": {
        "type": "String"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:selectCheckboxes": {
    "simple": False,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "border": {
        "type": "Integer"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "disabledClass": {
        "type": "String"
      },
      "enabledClass": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "layout": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "readonly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:selectList": {
    "simple": False,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "disabledClass": {
        "type": "String"
      },
      "enabledClass": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "multiselect": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "readonly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "size": {
        "type": "Integer"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:selectOption": {
    "simple": False,
    "attribs": {
      "dir": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "itemDescription": {
        "type": "String"
      },
      "itemDisabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "itemEscaped": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "itemLabel": {
        "type": "String"
      },
      "itemValue": {
        "type": "Object"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:selectOptions": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:selectRadio": {
    "simple": False,
    "attribs": {
      "accesskey": {
        "type": "String"
      },
      "border": {
        "type": "Integer"
      },
      "dir": {
        "type": "String"
      },
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "disabledClass": {
        "type": "String"
      },
      "enabledClass": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "label": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "layout": {
        "type": "String"
      },
      "onblur": {
        "type": "String"
      },
      "onchange": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onfocus": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "onselect": {
        "type": "String"
      },
      "readonly": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "required": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "tabindex": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:stylesheet": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      }
    }
  },
  "apex:tab": {
    "simple": False,
    "attribs": {
      "disabled": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "focus": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "label": {
        "type": "String"
      },
      "labelWidth": {
        "type": "String"
      },
      "name": {
        "type": "Object"
      },
      "onclick": {
        "type": "String"
      },
      "oncomplete": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "ontabenter": {
        "type": "String"
      },
      "ontableave": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "status": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "switchType": {
        "type": "String"
      },
      "timeout": {
        "type": "Integer"
      },
      "title": {
        "type": "String"
      }
    }
  },
  "apex:tabPanel": {
    "simple": False,
    "attribs": {
      "activeTabClass": {
        "type": "String"
      },
      "contentClass": {
        "type": "String"
      },
      "contentStyle": {
        "type": "String"
      },
      "dir": {
        "type": "String"
      },
      "disabledTabClass": {
        "type": "String"
      },
      "headerAlignment": {
        "type": "String"
      },
      "headerClass": {
        "type": "String"
      },
      "headerSpacing": {
        "type": "String"
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "immediate": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "inactiveTabClass": {
        "type": "String"
      },
      "lang": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "selectedTab": {
        "type": "Object"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "switchType": {
        "type": "String"
      },
      "tabClass": {
        "type": "String"
      },
      "title": {
        "type": "String"
      },
      "value": {
        "type": "Object"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:toolbar": {
    "simple": False,
    "attribs": {
      "contentClass": {
        "type": "String"
      },
      "contentStyle": {
        "type": "String"
      },
      "height": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "itemSeparator": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onitemclick": {
        "type": "String"
      },
      "onitemdblclick": {
        "type": "String"
      },
      "onitemkeydown": {
        "type": "String"
      },
      "onitemkeypress": {
        "type": "String"
      },
      "onitemkeyup": {
        "type": "String"
      },
      "onitemmousedown": {
        "type": "String"
      },
      "onitemmousemove": {
        "type": "String"
      },
      "onitemmouseout": {
        "type": "String"
      },
      "onitemmouseover": {
        "type": "String"
      },
      "onitemmouseup": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "separatorClass": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "width": {
        "type": "String"
      }
    }
  },
  "apex:toolbarGroup": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "itemSeparator": {
        "type": "String"
      },
      "location": {
        "type": "String"
      },
      "onclick": {
        "type": "String"
      },
      "ondblclick": {
        "type": "String"
      },
      "onkeydown": {
        "type": "String"
      },
      "onkeypress": {
        "type": "String"
      },
      "onkeyup": {
        "type": "String"
      },
      "onmousedown": {
        "type": "String"
      },
      "onmousemove": {
        "type": "String"
      },
      "onmouseout": {
        "type": "String"
      },
      "onmouseover": {
        "type": "String"
      },
      "onmouseup": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "separatorClass": {
        "type": "String"
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      }
    }
  },
  "apex:variable": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "value": {
        "type": "Object"
      },
      "var": {
        "type": "String"
      }
    }
  },
  "apex:vote": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "objectId": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rerender": {
        "type": "String"
      }
    }
  },
  "c:sitefooter": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "c:siteheader": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "c:sitelogin": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "c:sitepoweredby": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "chatter:feed": {
    "simple": True,
    "attribs": {
      "entityId": {
        "type": "id"
      },
      "feedItemType": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "onComplete": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "showPublisher": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "chatter:feedWithFollowers": {
    "simple": True,
    "attribs": {
      "entityId": {
        "type": "id"
      },
      "id": {
        "type": "String"
      },
      "onComplete": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      },
      "showHeader": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "chatter:follow": {
    "simple": True,
    "attribs": {
      "entityId": {
        "type": "id"
      },
      "id": {
        "type": "String"
      },
      "onComplete": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      }
    }
  },
  "chatter:followers": {
    "simple": True,
    "attribs": {
      "entityId": {
        "type": "id"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "chatter:newsfeed": {
    "simple": True,
    "attribs": {
      "id": {
        "type": "String"
      },
      "onComplete": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "reRender": {
        "type": "Object"
      }
    }
  },
  "chatter:userPhotoUpload": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "showOriginalPhoto": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "flow:interview": {
    "simple": False,
    "attribs": {
      "buttonLocation": {
        "type": "String",
        "values": [
          "both",
          "bottom",
          "top"
        ]
      },
      "buttonStyle": {
        "type": "String"
      },
      "finishLocation": {
        "type": "ApexPages.PageReference"
      },
      "id": {
        "type": "String"
      },
      "interview": {
        "type": "Flow.Interview"
      },
      "name": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "rerender": {
        "type": "Object"
      },
      "showHelp": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "ideas:detailOutputLink": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "ideaId": {
        "type": "String"
      },
      "page": {
        "type": "ApexPages.PageReference"
      },
      "pageNumber": {
        "type": "Integer"
      },
      "pageOffset": {
        "type": "Integer"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      }
    }
  },
  "ideas:listOutputLink": {
    "simple": False,
    "attribs": {
      "category": {
        "type": "String"
      },
      "communityId": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "page": {
        "type": "ApexPages.PageReference"
      },
      "pageNumber": {
        "type": "Integer"
      },
      "pageOffset": {
        "type": "Integer"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "sort": {
        "type": "String"
      },
      "status": {
        "type": "String"
      },
      "stickyAttributes": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      }
    }
  },
  "ideas:profileListOutputLink": {
    "simple": False,
    "attribs": {
      "communityId": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "page": {
        "type": "ApexPages.PageReference"
      },
      "pageNumber": {
        "type": "Integer"
      },
      "pageOffset": {
        "type": "Integer"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "sort": {
        "type": "String"
      },
      "stickyAttributes": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      },
      "style": {
        "type": "String"
      },
      "styleClass": {
        "type": "String"
      },
      "userId": {
        "type": "String"
      }
    }
  },
  "site:googleAnalyticsTracking": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "site:previewAsAdmin": {
    "simple": False,
    "attribs": {
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "social:profileViewer": {
    "simple": False,
    "attribs": {
      "entityId": {
        "type": "id"
      },
      "id": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  },
  "support:clickToDial": {
    "simple": False,
    "attribs": {
      "entityId": {
        "type": "String"
      },
      "id": {
        "type": "String"
      },
      "number": {
        "type": "String"
      },
      "params": {
        "type": "String"
      },
      "rendered": {
        "type": "Boolean",
        "values": [
          "true",
          "false"
        ]
      }
    }
  }
}
########NEW FILE########
__FILENAME__ = views
def get_view_by_group_index(window, group, index):
    groups = {0: {}}
    last_group = 0
    start_index = 0
    iter_index = 0
    original_view = window.active_view()
    original_views = {}
    for iter_group in xrange(window.num_groups()):
        window.focus_group(iter_group)
        original_views[iter_group] = window.active_view()
        groups[iter_group] = {}

    for view in window.views():
        if window.num_groups() == 1:
            groups[group][iter_index] = view
        else:
            window.focus_view(view)
            id = view.id()
            iter_group = last_group
            while iter_group < window.num_groups():
                window.focus_group(iter_group)
                active_view = window.active_view()
                if active_view and active_view.id() == id:
                    if len(groups) == iter_group:
                        groups[iter_group] = {}
                    groups[iter_group][iter_index - start_index] = view
                    break
                iter_group += 1
                last_group = iter_group
                start_index = iter_index

        iter_index += 1

    for iter_group in original_views:
        if not original_views[iter_group]:
            continue
        window.focus_view(original_views[iter_group])

    window.focus_view(original_view)
    return groups[group][index]


def get_all_views(window):
    views = window.views()
    active_view = window.active_view()
    if active_view and active_view.id() not in [ view.id() for view in views ]:
        views.append(active_view)
    return views

########NEW FILE########
__FILENAME__ = mavensmate
# Written by Joe Ferraro (@joeferraro / www.joe-ferraro.com)
import os
import subprocess 
import json
import sys
import re
#dist_dir = os.path.dirname(os.path.abspath(__file__))
#sys.path.insert(0, dist_dir)
from xml.dom.minidom import parse, parseString

if sys.version_info >= (3, 0):
    # Python 3
    import MavensMate.config as config
    import MavensMate.util as util
    import MavensMate.lib.command_helper as command_helper
    import MavensMate.lib.mm_interface as mm
    import MavensMate.lib.upgrader as upgrader
    import MavensMate.lib.resource_bundle as resource_bundle
    import MavensMate.lib.server.lib.server_threaded as server
    import MavensMate.lib.server.lib.config as server_config
    from MavensMate.lib.printer import PanelPrinter
    from MavensMate.lib.threads import ThreadTracker
    import MavensMate.lib.parsehelp as parsehelp
    import MavensMate.lib.vf as vf
    from MavensMate.lib.mm_merge import *
    from MavensMate.lib.completioncommon import *
else:
    # Python 2
    import config
    import util 
    import lib.command_helper as command_helper
    import lib.mm_interface as mm
    import lib.resource_bundle as resource_bundle
    import lib.vf as vf
    from lib.printer import PanelPrinter
    from lib.threads import ThreadTracker
    from lib.mm_merge import *

import sublime
import sublime_plugin

debug = None
settings = sublime.load_settings('mavensmate.sublime-settings')
sublime_version = int(float(sublime.version()))

completioncommon = imp.load_source("completioncommon", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib","completioncommon.py"))
apex_completions = util.parse_json_from_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "apex", "completions.json"))
apex_system_completions = []
for top_level_class_name in apex_completions["publicDeclarations"]["System"].keys():
    apex_system_completions.append((top_level_class_name+"\t[Standard Apex Class]", top_level_class_name))

st_version = 2
# Warn about out-dated versions of ST3
if sublime.version() == '':
    st_version = 3
elif int(sublime.version()) > 3000:
    st_version = 3

if st_version == 3:
    installed_dir, _ = __name__.split('.')
elif st_version == 2:
    installed_dir = os.path.basename(os.getcwd())

reloader_name = 'lib.reloader'

# ST3 loads each package as a module, so it needs an extra prefix
if st_version == 3:
    reloader_name = 'MavensMate.' + reloader_name
    from imp import reload

# Make sure all dependencies are reloaded on upgrade
if reloader_name in sys.modules and sys.version_info >= (3, 0):
    reload(sys.modules[reloader_name])
    from .lib import reloader

try:
    # Python 3
    import MavensMate.lib.reloader as reloader
except (ValueError):
    # Python 2
    import lib.reloader as reloader

def plugin_loaded():
    config.setup_logging()
    server_config.setup_logging()
    global debug
    debug = config.debug
    debug('Loading MavensMate for Sublime Text')
    settings = sublime.load_settings('mavensmate.sublime-settings')
    merge_settings = sublime.load_settings('mavensmate-merge.sublime-settings')
    try:
        server.run(port=settings.get('mm_server_port'))
    except Exception as e:
        debug(e)
    config.settings = settings
    config.merge_settings = merge_settings
    util.package_check()
    util.start_mavensmate_app()  
    util.check_for_updates()
    util.send_usage_statistics('Startup')

####### <--START--> COMMANDS THAT USE THE MAVENSMATE UI ##########

#displays new project dialog
class NewProjectCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        util.check_for_workspace()
        mm.call('new_project', False)
        util.send_usage_statistics('New Project')

#displays edit project dialog
class EditProjectCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('edit_project', False)
        util.send_usage_statistics('Edit Project')

    def is_enabled(command):
        return util.is_mm_project()

#displays unit test dialog
class RunApexUnitTestsCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        active_file = util.get_active_file()
        try:
            if os.path.exists(active_file):
                filename, ext = os.path.splitext(os.path.basename(util.get_active_file()))
                if ext == '.cls':
                    params = {
                        "selected"         : [filename]
                    }
                else:
                    params = {}
            else:
                params = {}
        except:
            params = {}
        mm.call('unit_test', context=command, params=params)
        util.send_usage_statistics('Apex Unit Testing')

    def is_enabled(command):
        return util.is_mm_project()

#launches the execute anonymous UI
class ExecuteAnonymousCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('execute_apex', False)
        util.send_usage_statistics('Execute Anonymous')

    def is_enabled(command):
        return util.is_mm_project()

#displays deploy dialog
class DeployToServerCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('deploy', False)
        util.send_usage_statistics('Deploy to Server')

    def is_enabled(command):
        return util.is_mm_project()

#displays deploy dialog
class NewDebugLogCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('debug_log', True)
        util.send_usage_statistics('New Debug Log')

    def is_enabled(command):
        return util.is_mm_project()

####### <--END--> COMMANDS THAT USE THE MAVENSMATE UI ##########

class MavensStubCommand(sublime_plugin.WindowCommand):
    def run(self):
        return True
    def is_enabled(self):
        return False
    def is_visible(self):
        return not util.is_mm_project();

#deploys the currently active file
class ForceCompileFileMainMenuCommand(sublime_plugin.WindowCommand):
    def run(self, files=None):       
        debug('FORCE COMPILING!')
        if files == None:
            files = [util.get_active_file()]
        params = {
            "files"     : files,
            "action"    : "overwrite"
        }
        mm.call('compile', context=self.window, params=params)
    
    def is_enabled(self):
       return util.is_mm_project();

#deploys the currently active file
class ForceCompileFileCommand(sublime_plugin.WindowCommand):
    def run(self, files=None):       
        debug('FORCE COMPILING!')
        if files == None:
            files = [util.get_active_file()]
        params = {
            "files"     : files,
            "action"    : "overwrite"
        }
        mm.call('compile', context=self.window, params=params)

#deploys the currently active file
class CompileActiveFileCommand(sublime_plugin.WindowCommand):
    def run(self):       
        params = {
            "files" : [util.get_active_file()]
        }
        mm.call('compile', context=self, params=params)

    def is_enabled(command):
        return util.is_mm_file()

    def is_visible(command):
        return util.is_mm_project()

class SyntaxHandler(sublime_plugin.EventListener):
    def on_load_async(self, view):
        try:
            fn = view.file_name()
            ext = util.get_file_extension(fn)
            if ext == '.cls' or ext == '.trigger':
                if "linux" in sys.platform or "darwin" in sys.platform:
                    view.set_syntax_file(os.path.join("Packages","MavensMate","sublime","lang","Apex.tmLanguage"))
                else:
                    view.set_syntax_file(os.path.join("Packages/MavensMate/sublime/lang/Apex.tmLanguage"))
            elif ext == '.page' or ext == '.component':
                if "linux" in sys.platform or "darwin" in sys.platform:
                    view.set_syntax_file(os.path.join("Packages","HTML","HTML.tmLanguage"))
                else:
                    view.set_syntax_file(os.path.join("Packages/HTML/HTML.tmLanguage"))
            elif ext == '.log' and ('/debug/' in fn or '\\debug\\' in fn or '\\apex-scripts\\log\\' in fn or '/apex-scripts/log/' in fn):
                if "linux" in sys.platform or "darwin" in sys.platform:
                    view.set_syntax_file(os.path.join("Packages","MavensMate","sublime","lang","MMLog.tmLanguage"))
                else:
                    view.set_syntax_file(os.path.join("Packages/MavensMate/sublime/lang/MMLog.tmLanguage"))
        except:
            pass

#handles compiling to server on save
class RemoteEdit(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings.get('mm_compile_on_save') == True and util.is_mm_file() == True:
            params = {
                "files" : [util.get_active_file()]
            }
            mm.call('compile', context=view, params=params)

class MenuModifier(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        view.file_name()

#compiles the selected files
class CompileSelectedFilesCommand(sublime_plugin.WindowCommand):
    def run (self, files):
        #print files
        params = {
            "files"         : files
        }
        mm.call('compile', context=self, params=params)
        util.send_usage_statistics('Compile Selected Files')

    def is_visible(self, files):
        return util.is_mm_project()

    def is_enabled(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_mm_file(f):
                    return True
        return False

class RunAllTestsAsyncCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('run_all_tests', context=self)
        util.send_usage_statistics('Run All Tests')

    def is_enabled(command):
        return util.is_mm_project()

#runs apex unit tests using the async api
class RunAsyncApexTestsCommand(sublime_plugin.WindowCommand):
    def run(self):
        active_file = util.get_active_file()
        try:
            if os.path.exists(active_file):
                filename, ext = os.path.splitext(os.path.basename(util.get_active_file()))
                if ext == '.cls':
                    params = {
                        "classes"         : [filename]
                    }
                else:
                    params = {}
            else:
                params = {}
        except:
            params = {}
        mm.call('test_async', context=self, params=params)
        util.send_usage_statistics('Async Apex Test')

    def is_enabled(command):
        return util.is_apex_class_file()

#displays unit test dialog
class GenerateApexTestCoverageReportCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('coverage_report', context=self, message="Generating Apex code coverage report for classes in your project...")
        util.send_usage_statistics('Code Coverage Report')

    def is_enabled(command):
        return util.is_mm_project()

#deploys the currently open tabs
class CompileTabsCommand(sublime_plugin.WindowCommand):
    def run (self):
        params = {
            "files"         : util.get_tab_file_names()
        }
        mm.call('compile', context=self, params=params)
        util.send_usage_statistics('Compile Tabs')

#replaces local copy of metadata with latest server copies
class CleanProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.ok_cancel_dialog("Are you sure you want to clean this project? All local (non-server) files will be deleted and your project will be refreshed from the server", "Clean"):
            mm.call('clean_project', context=self)
            util.send_usage_statistics('Clean Project')

    def is_enabled(command):
        return util.is_mm_project()  

class OpenProjectSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        path = os.path.join(util.mm_project_directory(),util.get_project_name()+'.sublime-settings')
        sublime.active_window().run_command('open_file', {'file': path})

    def is_enabled(command):
        return util.is_mm_project()      

#opens a project in the current workspace
class OpenProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        util.check_for_workspace()
        open_projects = []
        try:
            for w in sublime.windows():
                if len(w.folders()) == 0:
                    continue;
                root = w.folders()[0]
                if util.mm_workspace() not in root:
                    continue
                #project_name = root.split("/")[-1]
                project_name = util.get_file_name_no_extension(root)

                open_projects.append(project_name)
        except:
            pass

        import os
        self.dir_map = {}
        dirs = [] 
        #debug(util.mm_workspace())
        workspaces = util.mm_workspace()
        if type(workspaces) is not list:
            workspaces = [workspaces]

        for w in workspaces:
            for dirname in os.listdir(w):
                if dirname == '.DS_Store' or dirname == '.' or dirname == '..' or dirname == '.logs' : continue
                if dirname in open_projects : continue
                if not os.path.isdir(os.path.join(w,dirname)) : continue
                sublime_project_file = dirname+'.sublime-project'
                for project_content in os.listdir(os.path.join(w,dirname)):
                    if '.' not in project_content: continue
                    if project_content == '.sublime-project':
                        sublime_project_file = '.sublime-project'
                        continue
                dirs.append([dirname, "Workspace: "+os.path.basename(w)])
                self.dir_map[dirname] = [dirname, sublime_project_file, w]
        self.results = dirs
        #debug(self.results)
        self.window.show_quick_panel(dirs, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.picked_project = self.results[picked]
        project_file = self.dir_map[self.picked_project[0]][1]  
        project_name = self.dir_map[self.picked_project[0]][0]
        workspace = self.dir_map[self.picked_project[0]][2]
        project_file_location = os.path.join(workspace,project_name,project_file)
        #debug(project_file_location)
        
        if not os.path.isfile(project_file_location):
            sublime.message_dialog("Cannot find project file for: "+project_name)
            return

        settings = sublime.load_settings('mavensmate.sublime-settings')
        if sys.platform == 'darwin':
            sublime_path = settings.get('mm_plugin_client_location', '/Applications')
            if sublime_version >= 3000:
                if os.path.exists(os.path.join(sublime_path, 'Sublime Text 3.app')):
                    subprocess.Popen("'"+sublime_path+"/Sublime Text 3.app/Contents/SharedSupport/bin/subl' --project '"+project_file_location+"'", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                elif os.path.exists(os.path.join(sublime_path, 'Sublime Text.app')):
                    subprocess.Popen("'"+sublime_path+"/Sublime Text.app/Contents/SharedSupport/bin/subl' --project '"+project_file_location+"'", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            else:
                subprocess.Popen("'/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl' --project '"+project_file_location+"'", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        elif 'linux' in sys.platform:
            subl_location = settings.get('mm_subl_location', '/usr/local/bin/subl')
            subprocess.Popen("'{0}' --project '"+project_file_location+"'".format(subl_location), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        else:
            subl_location = settings.get('mm_windows_subl_location', '/usr/local/bin/subl')
            if not os.path.isfile(subl_location) and "x86" not in subl_location:
                subl_location = subl_location.replace("Program Files", "Program Files (x86)")
            subprocess.Popen('"{0}" --project "{1}"'.format(subl_location, project_file_location), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

class RunApexScriptCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "script_name"         : os.path.basename(util.get_active_file())
        }
        mm.call('run_apex_script', context=self, params=params)
        util.send_usage_statistics('Run Apex Script')

    def is_enabled(command):
        try:
            return "apex-scripts" in util.get_active_file() and '.cls' in util.get_active_file()
        except:
            return False

class NewApexScriptCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        sublime.active_window().show_input_panel("Apex Script Name", "MyScriptName", self.finish, None, None)

    def finish(self, name):
        if not os.path.exists(os.path.join(util.mm_project_directory(), "apex-scripts")):
            os.makedirs(os.path.join(util.mm_project_directory(), "apex-scripts"))

        if ".cls" not in name:
            name = name + ".cls"

        f = open(os.path.join(util.mm_project_directory(), "apex-scripts", name), "w")
        f.close()

        sublime.active_window().open_file(os.path.join(util.mm_project_directory(), "apex-scripts", name))

    def is_enabled(command):
        return util.is_mm_project()

#displays new apex class dialog
class NewApexClassCommand(sublime_plugin.TextCommand):
    
    def __init__(self, *args, **kwargs):
        sublime_plugin.TextCommand.__init__(self, *args, **kwargs)
        self.template_options   = None
        self.github_templates   = None
        self.api_name           = None
        self.github_template    = None

    def run(self, edit, api_name="MyClass", class_type="default"): 
        self.template_options = []
        self.github_templates = util.parse_templates_package("ApexClass")
        for t in self.github_templates:
            self.template_options.append([t["name"], t["description"], "Author: "+t["author"]])
        sublime.active_window().show_quick_panel(self.template_options, self.on_select_from_github_template)
        util.send_usage_statistics('New Apex Class')

    def on_select_from_github_template(self, selection):
        if selection != -1:
            template_name = self.template_options[selection][0]
            for t in self.github_templates:
                if t["name"] == template_name:
                    self.github_template = t
                    break

            sublime.active_window().show_input_panel(util.get_new_metadata_input_label(self.github_template), util.get_new_metadata_input_placeholders(self.github_template), self.finish_github_template_selection, None, None)

    def finish_github_template_selection(self, input):
        template_params = util.get_template_params(self.github_template)
        input_list = [x.strip() for x in input.split(',')]
        template_params_payload = {}
        debug(template_params)
        idx = 0
        for tp in template_params:
            template_params_payload[tp["name"]] = input_list[idx]
            idx = idx + 1
        debug(template_params)
        params = {
            'metadata_type'     : 'ApexClass',
            'github_template'   : self.github_template,
            'params'            : template_params_payload
        }
        mm.call('new_metadata', params=params)


    def is_enabled(self):
        return util.is_mm_project()

#displays new apex trigger dialog
class NewApexTriggerCommand(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        sublime_plugin.TextCommand.__init__(self, *args, **kwargs)
        self.template_options   = None
        self.github_templates   = None
        self.api_name           = None
        self.github_template    = None

    def run(self, edit, api_name="MyAccountTrigger", sobject_name="Account", class_type="default"): 
        self.template_options = []
        self.github_templates = util.parse_templates_package("ApexTrigger")
        for t in self.github_templates:
            self.template_options.append([t["name"], t["description"], "Author: "+t["author"]])
        sublime.active_window().show_quick_panel(self.template_options, self.on_select_from_github_template)
        util.send_usage_statistics('New Apex Trigger')

    def on_select_from_github_template(self, selection):
        if selection != -1:
            template_name = self.template_options[selection][0]
            for t in self.github_templates:
                if t["name"] == template_name:
                    self.github_template = t
                    break

            sublime.active_window().show_input_panel(util.get_new_metadata_input_label(self.github_template), util.get_new_metadata_input_placeholders(self.github_template), self.finish_github_template_selection, None, None)

    def finish_github_template_selection(self, input):
        template_params = util.get_template_params(self.github_template)
        input_list = [x.strip() for x in input.split(',')]
        template_params_payload = {}
        idx = 0
        for tp in template_params:
            template_params_payload[tp["name"]] = input_list[idx]
            idx = idx + 1
        debug(template_params)
        params = {
            'metadata_type'     : 'ApexTrigger',
            'github_template'   : self.github_template,
            'params'            : template_params_payload
        }
        mm.call('new_metadata', params=params)

    def is_enabled(command):
        return util.is_mm_project() 

#displays new apex page dialog
class NewApexPageCommand(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        sublime_plugin.TextCommand.__init__(self, *args, **kwargs)
        self.template_options   = None
        self.github_templates   = None
        self.api_name           = None
        self.github_template    = None

    def run(self, edit, api_name="MyPage", class_type="default"): 
        self.template_options = []
        self.github_templates = util.parse_templates_package("ApexPage")
        for t in self.github_templates:
            self.template_options.append([t["name"], t["description"], "Author: "+t["author"]])
        sublime.active_window().show_quick_panel(self.template_options, self.on_select_from_github_template)
        util.send_usage_statistics('New Visualforce Page')

    def on_select_from_github_template(self, selection):
        if selection != -1:
            template_name = self.template_options[selection][0]
            for t in self.github_templates:
                if t["name"] == template_name:
                    self.github_template = t
                    break

            sublime.active_window().show_input_panel(util.get_new_metadata_input_label(self.github_template), util.get_new_metadata_input_placeholders(self.github_template), self.finish_github_template_selection, None, None)
             
    def finish_github_template_selection(self, input):
        template_params = util.get_template_params(self.github_template)
        input_list = [x.strip() for x in input.split(',')]
        template_params_payload = {}
        idx = 0
        for tp in template_params:
            template_params_payload[tp["name"]] = input_list[idx]
            idx = idx + 1
        debug(template_params)
        params = {
            'metadata_type'     : 'ApexPage',
            'github_template'   : self.github_template,
            'params'            : template_params_payload
        }
        mm.call('new_metadata', params=params)

    def is_enabled(command):
        return util.is_mm_project()

#displays new apex component dialog
class NewApexComponentCommand(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        sublime_plugin.TextCommand.__init__(self, *args, **kwargs)
        self.template_options   = None
        self.github_templates   = None
        self.api_name           = None
        self.github_template    = None

    def run(self, edit, api_name="MyComponent", class_type="default"): 
        self.template_options = []
        self.github_templates = util.parse_templates_package("ApexComponent")
        for t in self.github_templates:
            self.template_options.append([t["name"], t["description"], "Author: "+t["author"]])
        sublime.active_window().show_quick_panel(self.template_options, self.on_select_from_github_template)
        util.send_usage_statistics('New Visualforce Component')

    def on_select_from_github_template(self, selection):
        if selection != -1:
            template_name = self.template_options[selection][0]
            for t in self.github_templates:
                if t["name"] == template_name:
                    self.github_template = t
                    break

            sublime.active_window().show_input_panel(util.get_new_metadata_input_label(self.github_template), util.get_new_metadata_input_placeholders(self.github_template), self.finish_github_template_selection, None, None)

    def finish_github_template_selection(self, input):
        template_params = util.get_template_params(self.github_template)
        input_list = [x.strip() for x in input.split(',')]
        template_params_payload = {}
        idx = 0
        for tp in template_params:
            template_params_payload[tp["name"]] = input_list[idx]
            idx = idx + 1
        debug(template_params)
        params = {
            'metadata_type'     : 'ApexComponent',
            'github_template'   : self.github_template,
            'params'            : template_params_payload
        }
        mm.call('new_metadata', params=params)

    def is_enabled(command):
        return util.is_mm_project()

def check_apex_templates(templates, args, command):
    if "class_type" not in args or args["class_type"] not in templates:
        sublime.error_message(str(args["class_type"])+" is not a valid template, please choose one of: "+str(sorted(templates.keys())))
        sublime.active_window().run_command(command, args)
        return False
    return True

def get_merged_apex_templates(apex_type):
    settings = sublime.load_settings('mavensmate.sublime-settings')
    template_map = settings.get('mm_default_apex_templates_map', {})
    custom_templates = settings.get('mm_apex_templates_map', {})
    if apex_type not in template_map:
        return {}
    if apex_type in custom_templates:
        template_map[apex_type] = dict(template_map[apex_type], **custom_templates[apex_type])
    return template_map[apex_type]

#displays mavensmate panel
class ShowDebugPanelCommand(sublime_plugin.WindowCommand):
    def run(self): 
        if util.is_mm_project() == True:
            PanelPrinter.get(self.window.id()).show(True)

    def is_enabled(command):
        return util.is_mm_project()

#hides mavensmate panel
class HideDebugPanelCommand(sublime_plugin.WindowCommand):
    def run(self):
        if util.is_mm_project() == True:
            PanelPrinter.get(self.window.id()).show(False)

#shows mavensmate info modal
class ShowVersionCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        version = util.get_version_number()
        sublime.message_dialog("MavensMate for Sublime Text v"+version+"\n\nMavensMate for Sublime Text is an open source Sublime Text plugin for Force.com development.\n\nhttp://mavensmate.com")

#refreshes selected directory (or directories)
# if src is refreshed, project is "cleaned"
class RefreshFromServerCommand(sublime_plugin.WindowCommand):
    def run (self, dirs, files):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite the selected files' contents from Salesforce?", "Refresh"):
            if dirs != None and type(dirs) is list and len(dirs) > 0:
                params = {
                    "directories"   : dirs
                }
            elif files != None and type(files) is list and len(files) > 0:
                params = {
                    "files"         : files
                }
            mm.call('refresh', context=self, params=params)
            util.send_usage_statistics('Refresh Selected From Server')

    def is_visible(self, dirs, files):
        return util.is_mm_project()

    # def is_enabled(self, dirs, files):
    #     if dirs != None and type(dirs) is list and len(dirs) > 0:
    #         for d in dirs:
    #             if util.is_config.mm_dir(d):
    #                 return True
    #     if files != None and type(files) is list and len(files) > 0:
    #         for f in files:
    #             if util.util.is_mm_file(f):
    #                 return True
    #     return False

class RefreshActivePropertiesFromServerCommand(sublime_plugin.WindowCommand):
    def run (self):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite the selected files' apex properties from Salesforce?", "Refresh Apex Properties"):
            params = {
                "files"         : [util.get_active_file()]
            }
            mm.call('refresh_properties', context=self, params=params)
            util.send_usage_statistics('Refresh Active Properties From Server')

    def is_visible(self):
        if not util.is_mm_file():
            return False
        filename = util.get_active_file()
        basename = os.path.basename(filename)
        data = util.get_apex_file_properties()
        if not basename in data:
            return True
        elif 'conflict' in data[basename] and data[basename]['conflict'] == True:
            return True
        else:
            return False

class RefreshPropertiesFromServerCommand(sublime_plugin.WindowCommand):
    def run (self, dirs, files):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite the selected files' apex properties from Salesforce?", "Refresh Apex Properties"):
            if dirs != None and type(dirs) is list and len(dirs) > 0:
                params = {
                    "directories"   : dirs
                }
            elif files != None and type(files) is list and len(files) > 0:
                params = {
                    "files"         : files
                }
            mm.call('refresh_properties', context=self, params=params)
            util.send_usage_statistics('Refresh Selected Properties From Server')

    def is_visible(self, dirs, files):
        if not util.is_mm_project():
            return False
        if files != None and type(files) is list and len(files) > 0:
            filename = files[0]
            basename = os.path.basename(filename)
            data = util.get_apex_file_properties()
            if not basename in data:
                return True
            elif 'conflict' in data[basename] and data[basename]['conflict'] == True:
                return True
            else:
                return False
        return True

    def is_enabled(self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            for d in dirs:
                if util.is_mm_dir(d):
                    return True
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_mm_file(f):
                    return True
        return False

#refreshes the currently active file from the server
class RefreshActiveFileCommand(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite this file's contents from Salesforce?", "Refresh"):
            params = {
                "files"         : [util.get_active_file()]
            }
            mm.call('refresh', context=self, params=params)
            util.send_usage_statistics('Refresh Active File From Server')

    def is_visible(self):
        return util.is_mm_file()

#refreshes the currently active file from the server
class SynchronizeActiveMetadataCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "files"         : [util.get_active_file()]
        }
        mm.call('synchronize', context=self, params=params)
        util.send_usage_statistics('Synchronized Active File to Server')

    def is_visible(self):
        return util.is_mm_file()


#opens the apex class, trigger, component or page on the server
class SynchronizeSelectedMetadataCommand(sublime_plugin.WindowCommand):
    def run (self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            params = {
                "directories"   : dirs
            }
        elif files != None and type(files) is list and len(files) > 0:
            params = {
                "files"         : files
            }
        mm.call('synchronize', context=self, params=params)
        util.send_usage_statistics('Synchronized Selected Metadata With Server')

    def is_visible(self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            for d in dirs:
                if util.is_config.mm_dir(d):
                    return True
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_mm_file(f):
                    return True
        return False

#opens the apex class, trigger, component or page on the server
class RunActiveApexTestsCommand(sublime_plugin.WindowCommand):
    def run(self):
        filename, ext = os.path.splitext(os.path.basename(util.get_active_file()))
        params = {
            "selected"         : [filename]
        }
        mm.call('unit_test', context=self, params=params)
        util.send_usage_statistics('Run Apex Tests in Active File')

    def is_visible(self):
        return util.is_apex_class_file()

    def is_enabled(self):
        return util.is_apex_test_file()


#opens the apex class, trigger, component or page on the server
class RunSelectedApexTestsCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if files != None and type(files) is list and len(files) > 0:
            params = {
                "selected"         : []
            }
            for f in files:
                filename, ext = os.path.splitext(os.path.basename(f))
                params['selected'].append(filename)

            mm.call('unit_test', context=self, params=params)
            util.send_usage_statistics('Run Apex Tests in Active File')

    def is_visible(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_class_file(f): 
                    return True
        return False
        
    def is_enabled(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_test_file(f): return True
        return False

#opens the apex class, trigger, component or page on the server
class OpenActiveSfdcUrlCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "files"         : [util.get_active_file()]
        }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Active File On Server')

    def is_visible(self):
        return util.is_mm_file()

    def is_enabled(self):
        return util.is_browsable_file()

#opens the WSDL file for apex webservice classes
class OpenActiveSfdcWsdlUrlCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "files"         : [util.get_active_file()],
            "type"          : "wsdl"
        }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Active WSDL File On Server')

    def is_visible(self):
        return util.is_apex_class_file()

    def is_enabled(self):
        if util.is_apex_webservice_file(): 
            return True
        return False

#opens the apex class, trigger, component or page on the server
class OpenSelectedSfdcUrlCommand(sublime_plugin.WindowCommand):
    def run (self, files):
        if files != None and type(files) is list and len(files) > 0:
            params = {
                "files"         : files
            }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Selected File On Server')

    def is_visible(self, files):
        if not util.is_mm_project: return False
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_browsable_file(f): return True
        return False

#opens the WSDL file for apex webservice classes
class OpenSelectedSfdcWsdlUrlCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if files != None and type(files) is list and len(files) > 0:
            params = {
                "files"         : files,
                "type"          : "wsdl"
            }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Selected WSDL File On Server')

    def is_visible(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_class_file(f): 
                    return True
        return False
        
    def is_enabled(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_webservice_file(f): 
                    return True
        return False

#deletes selected metadata
class DeleteMetadataCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if sublime.ok_cancel_dialog("Are you sure you want to delete the selected files from Salesforce?", "Delete"):
            params = {
                "files" : files
            }
            mm.call('delete', context=self, params=params)
            util.send_usage_statistics('Delete Metadata')

    def is_visible(self):
        return util.is_mm_file()

    def is_enabled(self):
        return util.is_mm_file()

#deletes selected metadata
class RefreshProjectApexSymbols(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_apex', context=self, message="Refreshing Symbol Tables")
        util.send_usage_statistics('Refresh Apex Symbols') 

    def is_enabled(self):
        return util.is_mm_project()

#deletes selected metadata
class RefreshApexSymbols(sublime_plugin.WindowCommand):
    def run(self, files):
        if files != None and type(files) is list and len(files) == 1:
            class_names = []
            for f in files:
                class_names.append(os.path.basename(f).replace(".json",".cls"))
            params = {
                "files" : class_names
            }
            mm.call('index_apex', context=self, params=params, message="Refreshing Symbol Table(s) for selected Apex Classes")
            util.send_usage_statistics('Refresh Apex Symbols') 

    def is_visible(self, files):
        try:
            if not util.is_mm_project():
                return False

            if files != None and type(files) is list and len(files) == 1:
                for f in files:
                    if os.path.join(util.mm_project_directory(),"src","classes") not in f:
                        return False 
                    if "-meta.xml" in f:
                        return False
            elif files != None and type(files) is list and len(files) == 0:
                return False
            
            return True
        except:
            return False

    def is_enabled(self):
        return util.is_mm_project()

#deletes selected metadata
class DeleteActiveMetadataCommand(sublime_plugin.WindowCommand):
    def run(self):
        active_path = util.get_active_file()
        active_file = os.path.basename(active_path)
        if sublime.ok_cancel_dialog("Are you sure you want to delete "+active_file+" file from Salesforce?", "Delete"):
            params = {
                "files" : [active_file]
            }
            result = mm.call('delete', context=self, params=params)
            self.window.run_command("close")
            util.send_usage_statistics('Delete Metadata')

    def is_enabled(self):
        return util.is_mm_file()

    def is_visible(self):
        return util.is_mm_project()

#deletes selected metadata
class DeleteTraceFlagsForThisUser(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('delete_trace_flags', context=self, message="Deleting Trace Flags")
        util.send_usage_statistics('Delete Trace Flags')

    def is_enabled(self):
        return util.is_mm_project()

#attempts to compile the entire project
class CompileProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.ok_cancel_dialog("Are you sure you want to compile the entire project?", "Compile Project"):
            mm.call('compile_project', context=self)
            util.send_usage_statistics('Compile Project')

    def is_enabled(command):
        return util.is_mm_project()

#refreshes the currently active file from the server
class IndexApexFileProperties(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_apex', False, context=self)
        util.send_usage_statistics('Index Apex File Properties')  

    def is_enabled(command):
        return util.is_mm_project()

#indexes the meta data based on packages.xml
class IndexMetadataCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_metadata', True, context=self)
        util.send_usage_statistics('Index Metadata')  

    def is_enabled(command):
        return util.is_mm_project()

class NewQuickLogCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('new_quick_log', True)
        util.send_usage_statistics('New Quick Log')

    def is_enabled(self):
        return util.is_mm_project()

#refreshes the currently active file from the server
class FetchLogsCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('fetch_logs', True)
        util.send_usage_statistics('Fetch Apex Logs') 

    def is_enabled(self):
        return util.is_mm_project() 

#refreshes the currently active file from the server
class FetchCheckpointsCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('fetch_checkpoints', True)
        util.send_usage_statistics('Fetch Apex Checkpoints') 

    def is_enabled(self):
        return util.is_mm_project() 

#when a class or trigger file is opened, adds execution overlay markers if applicable
class HideApexCheckpoints(sublime_plugin.WindowCommand):
    def run(self):
        try:
            util.clear_marked_line_numbers(self.window.active_view(), "overlay")
        except Exception:
            debug('error hidding checkpoints')

    def is_enabled(self):
        return util.is_apex_class_file() 

#when a class or trigger file is opened, adds execution overlay markers if applicable
class ShowApexCheckpoints(sublime_plugin.WindowCommand):
    def run(self):
        debug('attempting to load apex overlays for current file')
        try:
            active_view = self.window.active_view()
            fileName, ext = os.path.splitext(active_view.file_name())
            debug(fileName)
            debug(ext)
            if ext == ".cls" or ext == ".trigger":
                api_name = fileName.split("/")[-1] 
                overlays = util.parse_json_from_file(util.mm_project_directory()+"/config/.overlays")
                lines = []
                for o in overlays:
                    if o['API_Name'] == api_name:
                        lines.append(int(o["Line"]))
                sublime.set_timeout(lambda: util.mark_overlays(active_view, lines), 10)
        except Exception as e:
            debug('execution overlay loader error')
            debug('', e)

    def is_enabled(self):
        return util.is_apex_class_file() 

#deletes overlays
class DeleteApexCheckpointCommand(sublime_plugin.WindowCommand):
    def run(self):
        #options = [['Delete All In This File', '*']]
        options = []
        fileName, ext = os.path.splitext(util.get_active_file())
        if ext == ".cls" or ext == ".trigger":
            self.api_name = fileName.split("/")[-1] 
            overlays = util.get_execution_overlays(util.get_active_file())
            for o in overlays:
                options.append(['Line '+str(o["Line"]), str(o["Id"])])
        self.results = options
        self.window.show_quick_panel(options, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.overlay = self.results[picked]
        params = {
            "id" : self.overlay[1]
        }
        mm.call('delete_apex_overlay', context=self, params=params, message="Deleting checkpoint...", callback=self.reload)
        util.send_usage_statistics('Delete Apex Checkpoint') 

    def reload(self, cmd=None):
        debug("Reloading Apex Checkpoints")
        cmd.window.run_command("show_apex_checkpoints") 

    def is_enabled(self):
        return util.is_apex_class_file()  


#refreshes the currently active file from the server
class IndexApexCheckpointsCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_apex_overlays', False, context=self, callback=self.reload)
        util.send_usage_statistics('Index Apex Overlays')  

    def is_enabled(command):
        return util.is_mm_project()

    def reload(self, cmd=None):
        debug("Reloading Apex Checkpoints")
        cmd.window.run_command("show_apex_checkpoints")

#refreshes the currently active file from the server
class ResetMetadataContainerCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('reset_metadata_container', True, context=self, message="Fetching new MetadataContainer...")
        util.send_usage_statistics('Reset Metadata Container')  

    def is_enabled(command):
        return util.is_mm_project()

#gets apex code coverage for the current class
class GetApexCodeCoverageCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "classes" : [util.get_active_file()] 
        }
        mm.call('get_coverage', True, context=self, message="Retrieving Apex Code Coverage for "+util.get_file_name_no_extension(params["classes"][0]), params=params)
        util.send_usage_statistics('Apex Code Coverage')  

    def is_enabled(command):
        return util.is_apex_class_file()

#gets apex code coverage for the current class
class HideCoverageCommand(sublime_plugin.WindowCommand):
    def run(self):
        util.clear_marked_line_numbers(self.window.active_view(), "no_apex_coverage")
        util.send_usage_statistics('Hide Apex Coverage')  

    def is_enabled(command):
        return util.is_apex_class_file()

#refreshes the currently active file from the server
class GetOrgWideTestCoverageCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('get_org_wide_test_coverage', True, context=self, message="Retrieving org-wide test coverage...")
        util.send_usage_statistics('Org-Wide Apex Code Coverage')  

    def is_enabled(command):
        return util.is_mm_project()

#creates a new overlay
class NewApexCheckpoint(sublime_plugin.WindowCommand):
    def run(self):
        fileName, ext = os.path.splitext(util.get_active_file())
        if ext == ".cls" or ext == ".trigger":
            if ext == '.cls':
                self.object_type = 'ApexClass'
            else: 
                self.object_type = 'ApexTrigger'
            self.api_name = fileName.split("/")[-1] 
            number_of_lines = util.get_number_of_lines_in_file(util.get_active_file())
            lines = list(range(number_of_lines))
            options = []
            lines.pop(0)
            for l in lines:
                options.append(str(l))
            self.results = options
            self.window.show_quick_panel(options, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.line_number = self.results[picked]
        #print self.line_number
        params = {
            "ActionScriptType"      : "None",
            "Object_Type"           : self.object_type,
            "API_Name"              : self.api_name,
            "IsDumpingHeap"         : True,
            "Iteration"             : 1,
            "Line"                  : int(self.line_number)
        }
        #util.mark_overlay(self.line_number) #cant do this here bc it removes the rest of them
        mm.call('new_apex_overlay', context=self, params=params, message="Creating new checkpoint at line "+self.line_number+"...", callback=self.reload)
        util.send_usage_statistics('New Apex Overlay')  

    def reload(self, cmd=None):
        debug("Reloading Apex Checkpoints")
        cmd.window.run_command("show_apex_checkpoints")

    def is_enabled(self):
        return util.is_apex_class_file() 

#right click context menu support for resource bundle creation
class NewResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self, files, dirs):
        if sublime.ok_cancel_dialog("Are you sure you want to create resource bundle(s) for the selected static resource(s)", "Create Resource Bundle(s)"):
            resource_bundle.create(self, files) 
            util.send_usage_statistics('New Resource Bundle (Sidebar)')

    def is_visible(self, files, dirs):
        if not util.is_mm_project():
            return False
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            return False
        is_ok = True
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                basename = os.path.basename(f)
                if "." not in basename:
                    is_ok = False
                    return
                if "." in basename and basename.split(".")[-1] != "resource":
                    is_ok = False
                    break
        return is_ok   

#right click context menu support for resource bundle refresh
class RefreshResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self, dirs, files):
        if sublime.ok_cancel_dialog("This command will refresh the resource bundle(s) based on your local project's corresponding static resource(s). Do you wish to continue?", "Refresh"):
            resource_bundle.refresh(self, dirs) 
            util.send_usage_statistics('Refresh Resource Bundle (Sidebar)')
    def is_visible(self, dirs, files):
        try:
            if files != None and type(files) is list and len(files) > 0:
                return False

            if not util.is_mm_project():
                return False
            is_ok = True
            if dirs != None and type(dirs) is list and len(dirs) > 0:
                for d in dirs:
                    basename = os.path.basename(d)
                    if "." not in basename:
                        is_ok = False
                        break
                    if "." in basename and basename.split(".")[-1] != "resource":
                        is_ok = False
                        break
            return is_ok  
        except:
            return False 

#creates a MavensMate project from an existing directory
class CreateMavensMateProject(sublime_plugin.WindowCommand):
    def run (self, dirs):
        directory = dirs[0]

        if directory.endswith("/src"):
            printer = PanelPrinter.get(self.window.id())
            printer.show()
            printer.write('\n[OPERATION FAILED] You must run this command from the project folder, not the "src" folder\n')
            return            
 
        dir_entries = os.listdir(directory)
        has_source_directory = False
        for entry in dir_entries:
            if entry == "src":
                has_source_directory = True
                break

        if has_source_directory == False:
            printer = PanelPrinter.get(self.window.id())
            printer.show()
            printer.write('\n[OPERATION FAILED] Unable to locate "src" folder\n')
            return
        
        dir_entries = os.listdir(os.path.join(directory,"src"))
        has_package = False
        for entry in dir_entries:
            if entry == "package.xml":
                has_package = True
                break

        if has_package == False:
            printer = PanelPrinter.get(self.window.id())
            printer.show()
            printer.write('\n[OPERATION FAILED] Unable to locate package.xml in src folder \n')
            return        

        params = {
            "directory" : directory
        }
        mm.call('new_project_from_existing_directory', params=params)
        util.send_usage_statistics('New Project From Existing Directory')  

    def is_visible(self, dirs):
        if dirs != None and type(dirs) is list and len(dirs) > 1:
            return False
        if util.is_mm_project():
            return False
        directory = dirs[0]
        if not os.path.isfile(os.path.join(directory, "src", "package.xml")):
            return False
        if not os.path.exists(os.path.join(directory, "src")):
            return False
        return True

#generic handler for writing text to an output panel (sublime text 3 requirement)
class MavensMateOutputText(sublime_plugin.TextCommand):
    def run(self, edit, text, *args, **kwargs):
        size = self.view.size()
        self.view.set_read_only(False)
        self.view.insert(edit, size, text)
        self.view.set_read_only(True)
        self.view.show(size)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return

class WriteOperationStatus(sublime_plugin.TextCommand):
    def run(self, edit, text, *args, **kwargs):
        kw_region = kwargs.get('region', [0,0])
        status_region = sublime.Region(kw_region[0],kw_region[1])
        size = self.view.size()
        self.view.set_read_only(False)
        self.view.replace(edit, status_region, text)
        self.view.set_read_only(True)
        #self.view.show(size)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return

class CancelCurrentCommand(sublime_plugin.WindowCommand):
    
    def run(self):
        current_thread = ThreadTracker.get_current(self.window.id())
        if current_thread:
            current_thread.kill()

    #def is_visible(self, paths = None):
    #    return ThreadTracker.get_current(self.window.id()) != None

#updates MavensMate plugin
class UpdateMeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        if 'darwin' in sys.platform:
            printer = PanelPrinter.get(sublime.active_window().id())
            upgrader.execute(printer)
        elif 'linux' in sys.platform:
            printer = PanelPrinter.get(sublime.active_window().id())
            upgrader.execute(printer)
        elif 'win32' in sys.platform or 'win64' in sys.platform:
            updater_path = os.path.join(os.environ["ProgramFiles"],"MavensMate","MavensMate-SublimeText.exe")
            if not os.path.isfile(updater_path):
                updater_path = updater_path.replace("Program Files", "Program Files (x86)")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen('"{0}"'.format(updater_path), startupinfo=startupinfo)

####### <--START--> COMMANDS THAT ARE NOT *OFFICIALLY* SUPPORTED IN 2.0 BETA ##########

#opens the MavensMate shell
class NewShellCommand(sublime_plugin.TextCommand):
    def run(self, edit): 
        util.send_usage_statistics('New Shell Command')
        sublime.active_window().show_input_panel("MavensMate Command", "", self.on_input, None, None)
    
    def on_input(self, input): 
        try:
            ps = input.split(" ")
            if ps[0] == 'new':
                metadata_type, metadata_name, object_name = '', '', ''
                metadata_type   = ps[1]
                proper_type     = command_helper.dict[metadata_type][0]
                metadata_name   = ps[2]
                if len(ps) > 3:
                    object_name = ps[3]
                options = {
                    'metadata_type'     : proper_type,
                    'metadata_name'     : metadata_name,
                    'object_api_name'   : object_name,
                    'apex_class_type'   : 'Base'
                }
                mm.call('new_metadata', params=options)
            elif ps[0] == 'bundle' or ps[0] == 'b':
                deploy_resource_bundle(ps[1])
            else:
                util.print_debug_panel_message('Unrecognized command: ' + input + '\n')
        except:
            util.print_debug_panel_message('Unrecognized command: ' + input + '\n')

#completions for visualforce
class VisualforceCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        #if user has opted out of autocomplete or this isnt a mm project, ignore it
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings.get('mm_autocomplete') == False or util.is_mm_project() == False:
            return []

        #only run completions for Apex Pages and Components
        ext = util.get_file_extension(view.file_name())
        if ext != '.page' and ext != '.component':
            return []

        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))
        ch2 = view.substr(sublime.Region(pt, pt + 2))
        
        if ch2 == '<a' or ch2 == '<c':
            _completions = []
            for t in vf.tag_list:
                 _completions.append((t, t))
            return _completions

        elif ch == ':':
            debug('SCOPE: ', view.scope_name(pt))
            word = view.substr(view.word(pt))        
            _completions = []
            for t in vf.tag_list:
                if word in t:
                    _completions.append((t, t))
            return _completions

        elif ch == ' ':
            debug('SCOPE: ', view.scope_name(pt))
            scope_names = view.scope_name(pt).split(' ')
            if 'string.quoted.double.html' in scope_names or 'string.quoted.single.html' in scope_names:
                return []

            if 'meta.tag.other.html' in scope_names:
                region_from_top_to_current_word = sublime.Region(0, pt + 1)
                lines = view.lines(region_from_top_to_current_word)
                
                _completions = []
                tag_def = None
                for line in reversed(lines):
                    line_contents = view.substr(line)
                    line_contents = line_contents.replace("\t", "").strip()
                    if line_contents.find('<') == -1: continue #skip the line if the opening bracket isn't in the line
                    tag_def = line_contents.split('<')[-1].split(' ')[0]
                    break

                #debug(tag_def)
                if tag_def in vf.tag_defs:
                    def_entry = vf.tag_defs[tag_def]

                    for key, value in def_entry['attribs'].items():
                        _completions.append((key + '\t(' + value['type'] + ')', key+'="${1:'+value['type']+'}"'))

                    return sorted(_completions)
                else:
                    completion_flags = (
                        sublime.INHIBIT_WORD_COMPLETIONS |
                        sublime.INHIBIT_EXPLICIT_COMPLETIONS
                    )
                    return ([], completion_flags)
            elif 'source.js.embedded.html' in scope_names:
                return []
            else:
                completion_flags = (
                    sublime.INHIBIT_WORD_COMPLETIONS |
                    sublime.INHIBIT_EXPLICIT_COMPLETIONS
                )
                return ([], completion_flags)
        else:
            completion_flags = (
                sublime.INHIBIT_WORD_COMPLETIONS |
                sublime.INHIBIT_EXPLICIT_COMPLETIONS
            )
            return ([], completion_flags)

class SalesforceGenericCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        #if user has opted out of autocomplete or this isnt a mm project, ignore it
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings.get('mm_autocomplete') == False or util.is_mm_project() == False:
            return []

        #only run completions for Apex Triggers and Classes
        ext = util.get_file_extension(view.file_name())
        if ext != '.cls' and ext != '.trigger':
            return []

        # debug('prefix: ',prefix)
        # debug('locations: ',locations)
        # pt1 = locations[0] - len(prefix) + 1
        # right_of_point = view.substr(pt1)
        # debug('right of pt: ',right_of_point)

        #now get the autocomplete context
        #if not dot notation, ignore
        pt = locations[0] - len(prefix) - 1
        # debug(view.scope_name(pt))
        scope_name = view.scope_name(pt)
        #debug(scope_name)
        if 'string.quoted.single.java' in scope_name:
            return []
        #if 'string.quoted.brackets.soql.apex' in scope_name:
        #    return []

        ch = view.substr(sublime.Region(pt, pt + 1))
        if ch == '.' and 'string.quoted.brackets.soql.apex' not in scope_name: return []
        ltr = view.substr(sublime.Region(pt, pt + 2))
        if not ltr.isupper() and 'string.quoted.brackets.soql.apex' not in scope_name: return [] #if not an uppercase letter, ignore

        _completions = []

        if 'string.quoted.brackets.soql.apex' in scope_name:
            return []
            # if ch == '.':
            #     word = view.substr(view.word(pt))
            #     if not word.endswith('__r'):
            #         return []
            #     base_word = word.replace("__r","")
            #     if base_word in util.standard_object_names():
            #         object_name = base_word
            #     else:
            #         object_name = word.replace("__r","__c")
            #     debug("Retrieving field completions for: ",object_name)
            #     return util.get_field_completions(object_name)
            # else:
            #     #debug(view.substr(pt))
            #     #debug(len(view.substr(pt)))
            #     #if view.substr(pt) == " ": #TODO
            #     #    return []
            #     data = view.substr(sublime.Region(0, locations[0]-len(prefix)))
            #     lines = parsehelp.collapse_square_brackets(data).split("\n")
            #     for line in reversed(lines):
            #         stem  = line.split("[")[0]
            #         if "[" in line:
            #             if len(stem.strip()) == 0: continue
            #         words = stem.split()
            #         for word in reversed(words):
            #             if re.match('^[\w-]+$', word) == None:
            #                 continue
            #             vartype = parsehelp.get_var_type(data, word)
            #             if vartype != None:
            #                 object_name = vartype.group(1).strip()
            #                 debug("Retrieving field completions for: ",object_name)
            #                 return util.get_field_completions(object_name)
            #             break
            #         break
            #     return []

        if settings.get('mm_use_org_metadata_for_completions', False):
            if os.path.isfile(os.path.join(util.mm_project_directory(),"config",".org_metadata")): #=> parse org metadata, looking for object names
                jsonData = util.parse_json_from_file(os.path.join(util.mm_project_directory(),"config",".org_metadata"))
                for metadata_type in jsonData:
                    if 'xmlName' in metadata_type and metadata_type['xmlName'] == 'CustomObject':
                        for object_type in metadata_type['children']:
                            _completions.append((object_type['text']+"\t[Sobject Name]", object_type['text']))

        if os.path.isdir(os.path.join(util.mm_project_directory(),"config",".symbols")): #=> get list of classes
            for (dirpath, dirnames, filenames) in os.walk(os.path.join(util.mm_project_directory(),"config",".symbols")):
                for f in filenames:
                    if '-meta.xml' in f: continue
                    class_name = f.replace(".json", "")
                    _completions.append((class_name+"\t[Custom Apex Class]", class_name))
        #debug(apex_system_completions)
        _completions.extend(apex_system_completions)

        return _completions

#completions for force.com-specific use cases
class ApexCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        #if user has opted out of autocomplete or this isnt a mm project, ignore it
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings.get('mm_autocomplete') == False or util.is_mm_project() == False:
            return []

        #only run completions for Apex Triggers and Classes
        ext = util.get_file_extension(view.file_name())
        if ext != '.cls' and ext != '.trigger':
            return []

        full_file_path = os.path.splitext(util.get_active_file())[0]
        base = os.path.basename(full_file_path)
        file_name = os.path.splitext(base)[0] 

        #now get the autocomplete context
        #if not dot notation, ignore
        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))
        if not ch == '.': return []
        scope_name = view.scope_name(pt)
        debug(scope_name)
        if 'string.quoted.brackets.soql.apex' in scope_name:
            return []

        #myVariable.
        #if we cant find myVariable properly, exit out
        word = view.substr(view.word(pt))        
        if word == None or word == '':
            return [] 

        debug('autocomplete word: ', word)
        
        ##OK START COMPLETIONS
        _completions = []
        lower_word = word.lower()
        completion_flags = (
            sublime.INHIBIT_WORD_COMPLETIONS |
            sublime.INHIBIT_EXPLICIT_COMPLETIONS
        )

        data = view.substr(sublime.Region(0, locations[0]-len(prefix)))

        #full_data = view.substr(sublime.Region(0, view.size()))
        typedef = parsehelp.get_type_definition(data)
        debug('autocomplete type definition: ', typedef)

        if '<' not in typedef[2] and '[' not in typedef[2]:
            if '.' in typedef[2] and '<' not in typedef[2]:
                type_parts = typedef[2].split('.')
                typedef_class = type_parts[0] #e.g. ApexPages
                typedef_class_lower = typedef_class.lower()
                typedef_class_extra = type_parts[1] #e.g. StandardController
                typedef_class_extra_lower = typedef_class_extra.lower()
            else:
                typedef_class = typedef[2] #e.g. ApexPages
                typedef_class_lower = typedef_class.lower()
                typedef_class_extra = typedef[4].replace('.','') #e.g. StandardController
                typedef_class_extra_lower = typedef_class_extra.lower()

            if '<' in typedef_class:
                typedef_class_lower = re.sub('\<.*?\>', '', typedef_class_lower)
                typedef_class_lower = re.sub('\<', '', typedef_class_lower)
                typedef_class_lower = re.sub('\>', '', typedef_class_lower)
                typedef_class       = re.sub('\<.*?\>', '', typedef_class)
                typedef_class       = re.sub('\<', '', typedef_class)
                typedef_class       = re.sub('\>', '', typedef_class)

            if '[' in typedef_class:
                typedef_class_lower = re.sub('\[.*?\]', '', typedef_class_lower)
                typedef_class       = re.sub('\[.*?\]', '', typedef_class)
        else:
            if '<' in typedef[2]:
                typedef_class = typedef[2].split('<')[0]
            elif '[' in typedef[2]:
                typedef_class = typedef[2].split('[')[0]
            typedef_class_lower = typedef_class.lower()
            typedef_class_extra = ''
            typedef_class_extra_lower = ''



        debug('autocomplete type: ', typedef_class) #String
        debug('autocomplete type extra: ', typedef_class_extra) #String

        legacy_classes = ['system', 'search', 'limits', 'enum', 'trigger']

        if typedef_class_lower in legacy_classes and os.path.isfile(os.path.join(config.mm_dir,"lib","apex","classes",typedef_class_lower+".json")): #=> apex instance methods
            json_data = open(os.path.join(config.mm_dir,"lib","apex","classes",typedef_class_lower+".json"))
            data = json.load(json_data)
            json_data.close()
            pd = data["static_methods"]
            for method in pd:
                _completions.append((method, method))
            completion_flags = (
                sublime.INHIBIT_WORD_COMPLETIONS |
                sublime.INHIBIT_EXPLICIT_COMPLETIONS
            )
            #return (_completions, completion_flags)
            return sorted(_completions)

        if word == 'Page' and os.path.isdir(os.path.join(util.mm_project_directory(),"src","pages")):
            for (dirpath, dirnames, filenames) in os.walk(os.path.join(util.mm_project_directory(),"src","pages")):
                for f in filenames:
                    if '-meta.xml' in f: continue
                    base_page_name = f.replace(".page", "")
                    _completions.append((base_page_name+"\t[Visualforce Page]", base_page_name))
            completion_flags = (
                sublime.INHIBIT_WORD_COMPLETIONS |
                sublime.INHIBIT_EXPLICIT_COMPLETIONS
            )
            return (_completions, completion_flags)

        if len(typedef[4]) > 1 and '.' in typedef[4]:
            #deeply nested, need to look for properties
            #TODO 
            return []

        apex_class_key = typedef_class
        if apex_class_key == 'DateTime':
            apex_class_key = 'Datetime'

        if apex_class_key in apex_completions["publicDeclarations"] and typedef_class_extra_lower == '':
            apex_class_key = word
            if apex_class_key == 'DateTime':
                apex_class_key = 'Datetime'
            comp_def = apex_completions["publicDeclarations"].get(apex_class_key)
            for i in comp_def:
                _completions.append((i, i))
            return sorted(_completions)
        elif apex_completions["publicDeclarations"].get(apex_class_key) != None:
            top_level = apex_completions["publicDeclarations"].get(typedef_class)
            sub_def = top_level.get(word)
            if sub_def == None:
                sub_def = top_level.get(typedef_class_extra)
            _completions = util.get_symbol_table_completions(sub_def)
            return sorted(_completions)
        elif apex_class_key in apex_completions["publicDeclarations"]["System"]:
            if typedef_class == 'DateTime':
                typedef_class = 'Datetime'
            if word == typedef_class: #static
                comp_def = apex_completions["publicDeclarations"]["System"].get(apex_class_key)
            else: #instance
                comp_def = apex_completions["publicDeclarations"]["System"].get(typedef_class)
            _completions = util.get_symbol_table_completions(comp_def)
            return sorted(_completions)

        ## HANDLE CUSTOM APEX CLASS STATIC METHODS 
        ## MyCustomClass.some_static_method
        elif os.path.isfile(os.path.join(util.mm_project_directory(),"src","classes",word+".cls")):
            try:
                _completions = util.get_apex_completions(word) 
                return sorted(_completions) 
            except:
                return [] 

        if typedef_class_lower == None:
            return []

        ## HANDLE CUSTOM APEX INSTANCE METHOD ## 
        ## MyClass foo = new MyClass()
        ## foo.??  
        symbol_table = util.get_symbol_table(file_name)
        clazz = parsehelp.extract_class(data)
        #inheritance = parsehelp.extract_inheritance(data, clazz)
        
        if symbol_table != None and "innerClasses" in symbol_table and type(symbol_table["innerClasses"] is list and len(symbol_table["innerClasses"]) > 0):
            for ic in symbol_table["innerClasses"]:
                if ic["name"].lower() == typedef_class_lower:
                    _completions = util.get_completions_for_inner_class(ic)
                    return sorted(_completions)  

        if os.path.isfile(os.path.join(util.mm_project_directory(),"src","classes",typedef_class+".cls")): #=> apex classes
            _completions = util.get_apex_completions(typedef_class, typedef_class_extra)
            # if inheritance != None:
            #     _inheritance_completions = util.get_apex_completions(inheritance, None)
            #     _final_completions = _completions + _inheritance_completions
            #else:
            _final_completions = _completions
            return sorted(_final_completions)

        # if inheritance != None:
        #     if os.path.isfile(os.path.join(util.mm_project_directory(),"src","classes",inheritance+".cls")): #=> apex classes
        #         _completions = util.get_apex_completions(inheritance, typedef_class)
        #         return sorted(_completions)
        
        if typedef_class.endswith('__r'):
            typedef_class = typedef_class.replace('__r', '__c')
        if os.path.isfile(os.path.join(util.mm_project_directory(),"src","objects",typedef_class+".object")): #=> object fields from src directory (more info on field metadata, so is primary)
            object_dom = parse(os.path.join(util.mm_project_directory(),"src","objects",typedef_class+".object"))
            for node in object_dom.getElementsByTagName('fields'):
                field_name = ''
                field_type = ''
                for child in node.childNodes:                            
                    if child.nodeName != 'fullName' and child.nodeName != 'type': continue
                    if child.nodeName == 'fullName':
                        field_name = child.firstChild.nodeValue
                    elif child.nodeName == 'type':
                        field_type = child.firstChild.nodeValue
                _completions.append((field_name+" \t"+field_type, field_name))
            return sorted(_completions)
        elif os.path.isfile(os.path.join(util.mm_project_directory(),"config",".org_metadata")) and settings.get('mm_use_org_metadata_for_completions', False): #=> parse org metadata, looking for object fields
            jsonData = util.parse_json_from_file(os.path.join(util.mm_project_directory(),"config",".org_metadata"))
            for metadata_type in jsonData:
                if 'xmlName' in metadata_type and metadata_type['xmlName'] == 'CustomObject':
                    for object_type in metadata_type['children']:
                        if 'text' in object_type and object_type['text'].lower() == typedef_class_lower:
                            for attr in object_type['children']:
                                if 'text' in attr and attr['text'] == 'fields':
                                    for field in attr['children']:
                                        _completions.append((field['text'], field['text']))
            if len(_completions) == 0 and '__c' in typedef_class_lower:
                try:
                    #need to index custom objects here, because it couldnt be found
                    if len(ThreadTracker.get_pending_mm_panel_threads(sublime.active_window())) == 0:
                        params = {
                            'metadata_types' : ['CustomObject']
                        }
                        mm.call('refresh_metadata_index', False, params=params)
                except:
                    debug('Failed to index custom object metadata')
            else:
                _completions.append(('Id', 'Id'))
                return (sorted(_completions), completion_flags)
        else:
            return []

#prompts users to select a static resource to create a resource bundle
class CreateResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self):
        srs = []
        for dirname in os.listdir(os.path.join(util.mm_project_directory(),"src","staticresources")):
            if dirname == '.DS_Store' or dirname == '.' or dirname == '..' or '-meta.xml' in dirname : continue
            srs.append(dirname)
        self.results = srs
        self.window.show_quick_panel(srs, self.panel_done,
            sublime.MONOSPACE_FONT)
    def is_visible(self):
        return util.is_mm_project()

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        ps = []
        ps.append(os.path.join(util.mm_project_directory(),"src","staticresources",self.results[picked]))
        resource_bundle.create(self, ps)

#deploys selected resource bundle to the server
class DeployResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.rbs_map = {}
        rbs = []
        for dirname in os.listdir(os.path.join(util.mm_project_directory(),"resource-bundles")):
            if dirname == '.DS_Store' or dirname == '.' or dirname == '..' : continue
            rbs.append(dirname)
        self.results = rbs
        self.window.show_quick_panel(rbs, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        resource_bundle.deploy(self.results[picked])

#opens a file 
class OpenFileInProject(sublime_plugin.ApplicationCommand):
    def run(self, project_name, file_name, line_number):       
        window = sublime.active_window()
        for w in sublime.windows():
            if w.project_file_name() == None:
                continue
            if project_name+".sublime-project" in w.project_file_name():
                window = w
                break
        window.open_file("{0}:{1}:{2}".format(file_name, line_number, 0), sublime.ENCODED_POSITION)
        view = window.active_view()
        view.erase_regions("health_item")
        if line_number != 0:
            sublime.set_timeout(lambda: self.mark_line(view, line_number), 100)

    def mark_line(self, view, line_number):
        view.add_regions("health_item", [view.line(view.text_point(line_number-1, 0))], "foo", "bookmark", sublime.DRAW_OUTLINED)

class ProjectHealthCheckCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('project_health_check')
        util.send_usage_statistics('Project Health Check')  

    def is_enabled(command):
        return util.is_mm_project()

class ScrubLogCommand(sublime_plugin.WindowCommand):
    def run(self):
        util.send_usage_statistics('Scrub log')  
        active_view = self.window.active_view()
        fileName, ext = os.path.splitext(active_view.file_name())

        lines = []
        new_lines = []

        with open(active_view.file_name()) as f:
            lines = f.readlines()

        for file_line in lines:
            if '|USER_DEBUG|' in file_line and '|DEBUG|' in file_line:
                new_lines.append(file_line)
            elif '|EXCEPTION_THROWN|' in file_line or '|FATAL_ERROR|' in file_line:
                new_lines.append(file_line)

        string = "\n".join(new_lines)
        new_view = self.window.new_file()
        if "linux" in sys.platform or "darwin" in sys.platform:
            new_view.set_syntax_file(os.path.join("Packages","MavensMate","sublime","lang","MMLog.tmLanguage"))
        else:
            new_view.set_syntax_file(os.path.join("Packages/MavensMate/sublime/lang/MMLog.tmLanguage"))
        new_view.set_scratch(True)
        new_view.set_name("Scrubbed Log")
        new_view.run_command('generic_text', {'text': string })


    def is_enabled(command):
        active_view = sublime.active_window().active_view()
        fn, ext = os.path.splitext(active_view.file_name())
        if util.is_mm_project():
            if ext == '.log' and ('/debug/' in fn or '\\debug\\' in fn or '\\apex-scripts\\log\\' in fn or '/apex-scripts/log/' in fn):
                return True
            else:
                return False
        else:
            return False

class ListFieldsForObjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.objects = []
        self.org_metadata = {}
        if os.path.exists(os.path.join(util.mm_project_directory(),"src","objects")): #=> object fields from src directory (more info on field metadata, so is primary)
            for (dirpath, dirnames, filenames) in os.walk(os.path.join(util.mm_project_directory(),"src","objects")):
                for f in filenames:
                    self.objects.append(f.replace(".object",""))
        
        if self.objects == [] and os.path.isfile(os.path.join(util.mm_project_directory(),"config",".org_metadata")): #=> parse org metadata, looking for object names
            self.org_metadata = util.parse_json_from_file(os.path.join(util.mm_project_directory(),"config",".org_metadata"))
            for metadata_type in self.org_metadata:
                if 'xmlName' in metadata_type and metadata_type['xmlName'] == 'CustomObject':
                    for object_type in metadata_type['children']:
                        self.objects.append(object_type['text'])

        self.window.show_quick_panel(self.objects, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        fields = []
        selected_object = self.objects[picked]
        nodes = ['fullName', 'description', 'type', 'label', 'picklist']
        if os.path.isfile(os.path.join(util.mm_project_directory(),"src","objects",selected_object+".object")):
            object_dom = parse(os.path.join(util.mm_project_directory(),"src","objects",selected_object+".object"))
            for node in object_dom.getElementsByTagName('fields'):
                field_name = ''
                field_type = ''
                field_label = ''
                field_description = ''
                field_picklists = ''
                is_picklist = False
                for child in node.childNodes:                            
                    if child.nodeName not in nodes: continue
                    if child.nodeName == 'fullName':
                        field_name = child.firstChild.nodeValue
                    elif child.nodeName == 'type':
                        field_type = child.firstChild.nodeValue
                    elif child.nodeName == 'label':
                        field_label = child.firstChild.nodeValue
                    elif child.nodeName == 'description':
                        field_description = child.firstChild.nodeValue
                        field_description = field_description.replace("\n"," - ")
                    elif child.nodeName == 'picklist':
                        is_picklist = True
                        pvalues = []
                        for picklist_values_tag in child.childNodes:
                            for tag in picklist_values_tag.childNodes:
                                if tag.nodeName == 'fullName':
                                    pvalues.append(tag.firstChild.nodeValue)
                        field_picklists = '\n      - value: '.join(pvalues)

                if field_label == '':
                    field_label = field_name
                field_string = field_label+":\n   - description: "+field_description+"\n   - api_name: "+field_name+"\n   - field_type: "+field_type
                if is_picklist:
                    field_string += "\n   - picklist:"+field_picklists
                fields.append(field_string)
        elif self.org_metadata != {}:
            for metadata_type in self.org_metadata:
               if 'xmlName' in metadata_type and metadata_type['xmlName'] == 'CustomObject':
                   for object_name in metadata_type['children']:
                       if 'text' in object_name and object_name['text'] == selected_object:
                           for attr in object_name['children']:
                               if 'text' in attr and attr['text'] == 'fields':
                                   for field in attr['children']:
                                       fields.append(field['text'])

        string = "Object_Name: "+selected_object+"\n\n"
        string += "\n".join(fields)
        new_view = self.window.new_file()
        if "linux" in sys.platform or "darwin" in sys.platform:
            new_view.set_syntax_file(os.path.join("Packages","YAML","YAML.tmLanguage"))
        else:
            new_view.set_syntax_file(os.path.join("Packages/YAML/YAML.tmLanguage"))
        new_view.set_scratch(True)
        new_view.set_name("Field List: "+selected_object)
        new_view.run_command('generic_text', {'text': string })

    def is_enabled(command):
        return util.is_mm_project()

#generic handler for writing text to an output panel (sublime text 3 requirement)
class GenericTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, text, *args, **kwargs):
        size = self.view.size()
        self.view.set_read_only(False)
        self.view.insert(edit, size, text)
        #self.view.set_read_only(True)
        self.view.show(size)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return

class SignInWithGithub(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('github')
        util.send_usage_statistics('Github Sign In')

    def is_enabled(command):
        return util.is_mm_project()

class ConnectProjectWithGithub(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('github_connect_project')
        util.send_usage_statistics('Github Project Connect')

    def is_enabled(command):
        if util.is_mm_project():
            if os.path.isfile(os.path.join(util.mm_project_directory(),"config",".github")):
                return True
        return False

class ShowSublimeConsole(sublime_plugin.WindowCommand):
    def run(self):
        sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})
########NEW FILE########
__FILENAME__ = util
import sys 
import os
import subprocess
import json
import threading 
import re
#import pipes
import shutil
import codecs
import string
import random
import zipfile
import traceback
from xml.dom.minidom import parse, parseString

# from datetime import datetime, date, time

# try: 
#     import urllib
# except ImportError:
#     import urllib.request as urllib
import urllib.request

if sys.version_info >= (3, 0):
    #python 3
    import MavensMate.config as config
    import MavensMate.lib.apex.apex_extensions as apex_extensions
    from MavensMate.lib.usage_reporter import UsageReporter
    from MavensMate.lib.upgrader import AutomaticUpgrader
    #from MavensMate.lib.printer import PanelPrinter
else:
    #python 2
    import config
    import lib.apex.apex_extensions as apex_extensions
    from lib.usage_reporter import UsageReporter
    from lib.upgrader import AutomaticUpgrader
    #from lib.printer import PanelPrinter

#if os.name != 'nt':
#    import unicodedata

#PLUGIN_DIRECTORY = os.getcwd().replace(os.path.normpath(os.path.join(os.getcwd(), '..', '..')) + os.path.sep, '').replace(os.path.sep, '/')
#for future reference (windows/linux support)
#sublime.packages_path()

import sublime
settings = sublime.load_settings('mavensmate.sublime-settings')
packages_path = sublime.packages_path()
sublime_version = int(float(sublime.version()))

debug = config.debug

def standard_object_names():
    return [
        "Account", "Opportunity", "Contact", "Lead", "Pricebook2", "Product"
    ]

def mm_plugin_location():
    return os.path.join(packages_path,"MavensMate")

def package_check():
    #ensure user settings are installed
    try:
        if not os.path.exists(os.path.join(packages_path,"User","mavensmate.sublime-settings")):
            shutil.copyfile(os.path.join(config.mm_dir,"mavensmate.sublime-settings"), os.path.join(packages_path,"User","mavensmate.sublime-settings"))
    except:
        pass

def is_project_legacy(window=None):
    #debug(mm_project_directory(window))
    settings = sublime.load_settings('mavensmate.sublime-settings')
    if not os.path.exists(os.path.join(mm_project_directory(window),"config",".debug")):
        return True
    if settings.get('mm_mass_index_apex_symbols', True):
        if not os.path.exists(os.path.join(mm_project_directory(window),"config",".symbols")):
            return True
    if not os.path.exists(os.path.join(mm_project_directory(window),get_project_name(window)+'.sublime-settings')):
        return True
    if os.path.exists(os.path.join(mm_project_directory(window),"config","settings.yaml")):
        return True
    elif os.path.exists(os.path.join(mm_project_directory(window),"config",".settings")):
        current_settings = parse_json_from_file(os.path.join(mm_project_directory(window),"config",".settings"))
        if 'subscription' not in current_settings or 'workspace' not in current_settings:
            return True
        else:
            return False
    else:
        return False
 
def parse_json_from_file(location):
    try:
        json_data = open(location)
        data = json.load(json_data)
        json_data.close()
        return data
    except:
        return {}

def parse_templates_package(mtype=None):
    try:
        settings = sublime.load_settings('mavensmate.sublime-settings')
        template_source = settings.get('mm_template_source', 'joeferraro/MavensMate-Templates/master')
        template_location = settings.get('mm_template_location', 'remote')
        if template_location == 'remote':
            if 'linux' in sys.platform:
                response = os.popen('wget https://raw.github.com/{0}/{1} -q -O -'.format(template_source, "package.json")).read()
            else:
                response = urllib.request.urlopen('https://raw.github.com/{0}/{1}'.format(template_source, "package.json")).read().decode('utf-8')
            j = json.loads(response)
        else:
            local_template_path = os.path.join(template_source,"package.json")
            debug(local_template_path)
            j = parse_json_from_file(local_template_path)
            if j == None or j == {}:
                raise Exception('Could not load local templates. Check your "mm_template_source" setting.')
    except Exception as e:
        debug('Failed to load templates, reverting to local template store.')
        debug(e)
        local_template_path = os.path.join(config.mm_dir,"lib","apex","metadata-templates","package.json")
        j = parse_json_from_file(local_template_path)
    if mtype != None:
        return j[mtype]
    else:
        return j


def get_number_of_lines_in_file(file_path):
    f = open(file_path)
    lines = f.readlines()
    f.close()
    return len(lines) + 1

def get_execution_overlays(file_path):
    try:
        response = []
        fileName, ext = os.path.splitext(file_path)
        if ext == ".cls" or ext == ".trigger":
            api_name = fileName.split("/")[-1] 
            overlays = parse_json_from_file(mm_project_directory()+"/config/.overlays")
            for o in overlays:
                if o['API_Name'] == api_name:
                    response.append(o)
        return response
    except:
        return []

def get_random_string(size=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def get_active_file():
    try:
        return sublime.active_window().active_view().file_name()
    except Exception:
        return ''

def get_file_name_no_extension(path):
    base=os.path.basename(path)
    return os.path.splitext(base)[0]

def get_project_name(context=None):
    if context != None:
        if isinstance(context, sublime.View):
            view = context
            window = view.window()
        elif isinstance(context, sublime.Window):
            window = context
            view = window.active_view()
        else:
            window = sublime.active_window()
            view = window.active_view()
    else:
        window = sublime.active_window()
        view = window.active_view()

    if is_mm_project(window):
        if context == None:
            try:
                return os.path.basename(sublime.active_window().folders()[0])
            except:
                return None
        else:
            try:
                return os.path.basename(window.folders()[0])
            except:
                return None
    else:
        return None

def valid_workspace():
    workspace = mm_workspace()
    if workspace == None or workspace == "":
        return False
    elif type(workspace) is list and len(workspace) > 0:
        workspaces = workspace
        for w in workspaces:
            if not os.path.exists(w):
                return False
    elif type(workspace) is list and len(workspace) == 0:
        return False
    elif type(workspace) is not list and not os.path.exists(workspace):
        return False
    return True

def check_for_workspace():
    workspace = mm_workspace()
    if workspace == None or workspace == "":
        #os.makedirs(settings.get('mm_workspace')) we're not creating the directory here bc there's some sort of weird race condition going on
        msg = 'Your [mm_workspace] property is not set. Open \'MavensMate > Settings > User\' or press \'Cmd+Shift+,\' and set this property to the full path of your workspace. Thx!'
        sublime.error_message(msg)  
        raise BaseException

    selected_workspace = None
    if type(workspace) is list and len(workspace) > 0:
        selected_workspace = workspace[0]
    elif type(workspace) is list and len(workspace) == 0:
        msg = 'Your [mm_workspace] directory \''+workspace+'\' does not exist. Please create the directory then try your operation again. Thx!'
        sublime.error_message(msg)  
        raise BaseException
    else:
        selected_workspace = workspace

    if not os.path.exists(selected_workspace):
        #os.makedirs(settings.get('mm_workspace')) we're not creating the directory here bc there's some sort of weird race condition going on
        msg = 'Your [mm_workspace] setting is not configured properly. Please ensure any locations specified in mm_workspace exist on the system, then try your operation again.'
        sublime.error_message(msg)  
        raise BaseException

def sublime_project_file_path():
    project_directory = sublime.active_window().folders()[0]
    if os.path.isfile(os.path.join(project_directory,".sublime-project")):
        return os.path.join(project_directory,".sublime-project")
    elif os.path.isfile(os.path.join(project_directory,get_project_name(),".sublime-project")):
        return os.path.join(project_directory,get_project_name(),".sublime-project")
    else:
        return None 

def get_project_settings(window=None):
    if window == None:
        window = sublime.active_window()
    try:
       return parse_json_from_file(os.path.join(window.folders()[0],"config",".settings"))
    except:
        raise BaseException("Could not load project settings")

# check for mavensmate .settings file
def is_mm_project(window=None):
    if window == None:
        window = sublime.active_window()
    #workspace = mm_workspace();
    #commented out bc it's confusing to users to see commands grayed out with no error 
    #if workspace == "" or workspace == None or not os.path.exists(workspace):
    #    return False
    try:
        if os.path.isfile(os.path.join(window.folders()[0],"config",".settings")):
            return True
        elif os.path.isfile(os.path.join(window.folders()[0],"config","settings.yaml")):
            return True 
        else:
            return False
    except:
        return False

def get_file_extension(filename=None):
    try :
        if not filename: filename = get_active_file()
        fn, ext = os.path.splitext(filename)
        return ext
    except:
        pass
    return None

def get_apex_file_properties():
    return parse_json_from_file(os.path.join(mm_project_directory(),"config",".apex_file_properties"))

def is_mm_file(filename=None):
    try:
        if is_mm_project():
            if not filename: 
                filename = get_active_file()
            project_directory = mm_project_directory(sublime.active_window())
            if os.path.join(project_directory,"src","documents") in filename:
                return True
            if os.path.exists(filename) and os.path.join(project_directory,"src") in filename:
                settings = sublime.load_settings('mavensmate.sublime-settings')
                valid_file_extensions = settings.get("mm_apex_file_extensions", [])
                if get_file_extension(filename) in valid_file_extensions and 'apex-scripts' not in get_active_file():
                    return True
                elif "-meta.xml" in filename:
                    return True
    except Exception as e:
        #traceback.print_exc()
        pass
    return False

def is_mm_dir(directory):
    if is_mm_project():
        if os.path.isdir(directory):
            if os.path.basename(directory) == "src" or os.path.basename(directory) == get_project_name() or os.path.basename(os.path.abspath(os.path.join(directory, os.pardir))) == "src":
                return True
    return False

def is_browsable_file(filename=None):
    try :
        if is_mm_project():
            if not filename: 
                filename = get_active_file()
            if is_mm_file(filename):
                basename = os.path.basename(filename)
                data = get_apex_file_properties()
                if basename in data:
                    return True
                return os.path.isfile(filename+"-meta.xml")
    except:
        pass
    return False

def is_apex_class_file(filename=None):
    if not filename: filename = get_active_file()
    if is_mm_file(filename): 
        f, ext = os.path.splitext(filename)
        if ext == ".cls":
            return True
    return False

def is_apex_test_file(filename=None):
    if not filename: filename = get_active_file()
    if not is_apex_class_file(filename): return False
    with codecs.open(filename, "r", "utf-8") as content_file:
        content = content_file.read()
        p = re.compile("@isTest\s", re.I + re.M)
        if p.search(content):
            return True
        p = re.compile("\sstatic testMethod\s", re.I + re.M)
        if p.search(content):
            return True
    return False

def mark_overlays(view, lines):
    mark_line_numbers(view, lines, "dot", "overlay")

def write_overlays(view, overlay_result):
    result = json.loads(overlay_result)
    if result["totalSize"] > 0:
        for r in result["records"]:
            sublime.set_timeout(lambda: mark_line_numbers(view, [int(r["Line"])], "dot", "overlay"), 100)

def mark_line_numbers(view, lines, icon="dot", mark_type="compile_issue"):
    try:
        view.add_regions(mark_type, [view.line(view.text_point(lines[0]-1, 0))], "invalid.illegal", icon, sublime.DRAW_EMPTY_AS_OVERWRITE)
    except:
        points = [view.text_point(l - 1, 0) for l in lines]
        regions = [sublime.Region(p, p) for p in points]
        view.add_regions(mark_type, regions, "operation.fail", icon, sublime.HIDDEN | sublime.DRAW_EMPTY)

def mark_uncovered_lines(view, lines, icon="bookmark", mark_type="no_apex_coverage"):
    regions = []
    for line in lines:
        regions.append(view.line(view.text_point(line-1, 0)))
    view.add_regions(mark_type, regions, "invalid.illegal", icon, sublime.DRAW_EMPTY_AS_OVERWRITE)

def get_template_params(github_template):
    return github_template["params"]

def get_new_metadata_input_label(github_template):
    if "params" in github_template:
        params = []
        for param in github_template["params"]:
            params.append(param["description"])
        label = ", ".join(params)
    else:
        label = ""
    return label

def get_new_metadata_input_placeholders(github_template):
    if "params" in github_template:
        placeholders = []
        for param in github_template["params"]:
            if "default" in param:
                placeholders.append(param["default"])
        label = ", ".join(placeholders)
    else:
        label = "Default"
    return label

def clear_marked_line_numbers(view, mark_type="compile_issue"):
    try:
        sublime.set_timeout(lambda: view.erase_regions(mark_type), 100)
    except Exception as e:
        debug(e.message)
        debug('no regions to clean up')

def get_window_and_view_based_on_context(context):
    if isinstance(context, sublime.View):
        view = context
        window = view.window()
    elif isinstance(context, sublime.Window):
        window = context
        view = window.active_view()
    else:
        window = sublime.active_window()
        view = window.active_view()
    return window, view

def is_apex_webservice_file(filename=None):
    if not filename: filename = get_active_file()
    if not is_apex_class_file(filename): return False
    with codecs.open(filename, "r", "utf-8") as content_file:
        content = content_file.read()
        p = re.compile("global\s+(abstract\s+)?class\s", re.I + re.M)
        if p.search(content):
            p = re.compile("\swebservice\s", re.I + re.M)
            if p.search(content): return True
    return False

def mm_project_directory(window=None):
    #return sublime.active_window().active_view().settings().get('mm_project_directory') #<= bug
    if window == None:
        window = sublime.active_window()
    folders = window.folders()
    if len(folders) > 0:
        return window.folders()[0]
    else:
        return mm_workspace()

def mm_workspace():
    settings = sublime.load_settings('mavensmate.sublime-settings')
    if settings.get('mm_workspace') != None:
        workspace = settings.get('mm_workspace')
    else:
        workspace = sublime.active_window().active_view().settings().get('mm_workspace')
    return workspace

def print_debug_panel_message(message):
    # printer = PanelPrinter.get(sublime.active_window().id())
    # printer.show()
    # printer.write(message)
    pass

#parses the input from sublime text
def parse_new_metadata_input(input):
    input = input.replace(" ", "")
    if "," in input:
        params = input.split(",")
        api_name = params[0]
        class_type_or_sobject_name = params[1]
        return api_name, class_type_or_sobject_name
    else:
        return input

def to_bool(value):
    """
       Converts 'something' to boolean. Raises exception for invalid formats
           Possible True  values: 1, True, "1", "TRue", "yes", "y", "t"
           Possible False values: 0, False, None, [], {}, "", "0", "faLse", "no", "n", "f", 0.0, ...
    """
    if str(value).lower() in ("yes", "y", "true",  "t", "1"): return True
    if str(value).lower() in ("no",  "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): return False
    raise Exception('Invalid value for boolean conversion: ' + str(value))

def get_tab_file_names():
    tabs = []
    win = sublime.active_window()
    for vw in win.views():
        if vw.file_name() is not None:
            try:
                extension = os.path.splitext(vw.file_name())[1]
                extension = extension.replace(".","")
                if extension in apex_extensions.valid_extensions:
                    tabs.append(vw.file_name())
            except:
                pass
        else:
            pass      # leave new/untitled files (for the moment)
    return tabs 

def get_file_as_string(file_path):
    #debug(file_path)
    try:
        f = codecs.open(file_path, "r", "utf8")
        file_body = f.read()
        f.close()
        return file_body
    except Exception:
        #print "Couldn't open "+str(file_path)+" because: "+e.message
        pass
    return ""
    
def send_usage_statistics(action):
    settings = sublime.load_settings('mavensmate.sublime-settings')
    if settings.get('mm_send_usage_statistics') == True:
        sublime.set_timeout(lambda: UsageReporter(action).start(), 3000)

def refresh_active_view():
    sublime.set_timeout(sublime.active_window().active_view().run_command('revert'), 100)

def check_for_updates():
    settings = sublime.load_settings('mavensmate.sublime-settings')
    if settings.get('mm_check_for_updates') == True:
        sublime.set_timeout(lambda: AutomaticUpgrader().start(), 5000)

def start_mavensmate_app():
    p = subprocess.Popen("pgrep -fl \"MavensMate \"", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    msg = None
    if p.stdout is not None: 
        msg = p.stdout.readlines()
    elif p.stderr is not None:
        msg = p.stdout.readlines() 
    if msg == '' or len(msg) == 0:
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings != None and settings.get('mm_app_location') != None:
           os.system("open '"+settings.get('mm_app_location')+"'")
        else:
           #sublime.error_message("MavensMate.app is not running, please start it from your Applications folder.")
           debug('MavensMate: MavensMate.app is not running, please start it from your Applications folder.')

def get_field_completions(object_name):
    _completions = []
    if os.path.isfile(os.path.join(mm_project_directory(),"src","objects",object_name+".object")): #=> object fields from src directory (more info on field metadata, so is primary)
        object_dom = parse(os.path.join(mm_project_directory(),"src","objects",object_name+".object"))
        for node in object_dom.getElementsByTagName('fields'):
            field_name = ''
            field_type = ''
            for child in node.childNodes:                            
                if child.nodeName != 'fullName' and child.nodeName != 'type': continue
                if child.nodeName == 'fullName':
                    field_name = child.firstChild.nodeValue
                elif child.nodeName == 'type':
                    field_type = child.firstChild.nodeValue
            _completions.append((field_name+" \t"+field_type, field_name))
        return sorted(_completions)
    elif os.path.isfile(os.path.join(mm_project_directory(),"config",".org_metadata")): #=> parse org metadata, looking for object fields
        jsonData = parse_json_from_file(os.path.join(mm_project_directory(),"config",".org_metadata"))
        for metadata_type in jsonData:
            if 'xmlName' in metadata_type and metadata_type['xmlName'] == 'CustomObject':
                for object_type in metadata_type['children']:
                    if 'text' in object_type and object_type['text'].lower() == object_name.lower():
                        for attr in object_type['children']:
                            if 'text' in attr and attr['text'] == 'fields':
                                for field in attr['children']:
                                    _completions.append((field['text'], field['text']))
    return _completions

def get_symbol_table(class_name):
    try:
        if os.path.exists(os.path.join(mm_project_directory(), 'config', '.symbols')):
            class_name_json = os.path.basename(class_name).replace(".cls","json")
            if os.path.exists(os.path.join(mm_project_directory(), 'config', '.symbols', class_name_json+".json")):
                return parse_json_from_file(os.path.join(mm_project_directory(), "config", ".symbols", class_name_json+".json"))

        if not os.path.exists(os.path.join(mm_project_directory(), 'config', '.apex_file_properties')):
            return None

        apex_props = parse_json_from_file(os.path.join(mm_project_directory(), "config", ".apex_file_properties"))
        for p in apex_props.keys():
            if p == class_name+".cls" and 'symbolTable' in apex_props[p]:
                return apex_props[p]['symbolTable']
        return None
    except:
        return None

def get_completions_for_inner_class(symbol_table):
    return get_symbol_table_completions(symbol_table)

def get_symbol_table_completions(symbol_table):
    completions = []
    if 'constructors' in symbol_table:
        for c in symbol_table['constructors']:
            params = []
            if not 'visibility' in c:
                c['visibility'] = 'PUBLIC'
            if 'parameters' in c and type(c['parameters']) is list and len(c['parameters']) > 0:
                for p in c['parameters']:
                    params.append(p["type"] + " " + p["name"])
                paramStrings = []
                for i, p in enumerate(params):
                    paramStrings.append("${"+str(i+1)+":"+params[i]+"}")
                paramString = ", ".join(paramStrings)
                completions.append((c["visibility"] + " " + c["name"]+"("+", ".join(params)+")", c["name"]+"("+paramString+")"))
            else:
                completions.append((c["visibility"] + " " + c["name"]+"()", c["name"]+"()${1:}"))
    if 'properties' in symbol_table:
        for c in symbol_table['properties']:
            if not 'visibility' in c:
                c['visibility'] = 'PUBLIC'
            if "type" in c and c["type"] != None and c["type"] != "null":
                completions.append((c["visibility"] + " " + c["name"] + "\t" + c["type"], c["name"]))
            else:
                completions.append((c["visibility"] + " " + c["name"], c["name"]))
    if 'methods' in symbol_table:
        for c in symbol_table['methods']:
            params = []
            if not 'visibility' in c:
                c['visibility'] = 'PUBLIC'
            if 'parameters' in c and type(c['parameters']) is list and len(c['parameters']) > 0:
                for p in c['parameters']:
                    params.append(p["type"] + " " + p["name"])
            if len(params) == 1:
                completions.append((c["visibility"] + " " + c["name"]+"("+", ".join(params)+") \t"+c['returnType'], c["name"]+"(${1:"+", ".join(params)+"})"))
            elif len(params) > 1:
                paramStrings = []
                for i, p in enumerate(params):
                    paramStrings.append("${"+str(i+1)+":"+params[i]+"}")
                paramString = ", ".join(paramStrings)
                completions.append((c["visibility"] + " " + c["name"]+"("+", ".join(params)+") \t"+c['returnType'], c["name"]+"("+paramString+")"))
            else:
                completions.append((c["visibility"] + " " + c["name"]+"("+", ".join(params)+") \t"+c['returnType'], c["name"]+"()${1:}"))
    if 'innerClasses' in symbol_table:
        for c in symbol_table["innerClasses"]:
            if 'constructors' in c and len(c['constructors']) > 0:
                for con in c['constructors']:
                    if not 'visibility' in con:
                        con['visibility'] = 'PUBLIC'
                    params = []
                    if 'parameters' in con and type(con['parameters']) is list and len(con['parameters']) > 0:
                        for p in con['parameters']:
                            params.append(p["type"] + " " + p["name"])
                        paramStrings = []
                        for i, p in enumerate(params):
                            paramStrings.append("${"+str(i+1)+":"+params[i]+"}")
                        paramString = ", ".join(paramStrings)
                        completions.append((con["visibility"] + " " + con["name"]+"("+", ".join(params)+")", c["name"]+"("+paramString+")"))
                    else:
                        completions.append((con["visibility"] + " " + con["name"]+"()", c["name"]+"()${1:}"))
            else:
                completions.append(("INNER CLASS " + c["name"]+"() \t", c["name"]+"()${1:}"))
    return sorted(completions) 

#returns suggestions based on tooling api symbol table
def get_apex_completions(search_name, search_name_extra=None):
    debug('Attempting to get completions')
    debug('search_name: ',search_name)
    debug('search_name_extra: ',search_name_extra)

    if os.path.exists(os.path.join(mm_project_directory(), 'config', '.symbols')):
        #class_name_json = os.path.basename(class_name).replace(".cls","json")
        if os.path.exists(os.path.join(mm_project_directory(), 'config', '.symbols', search_name+".json")):
            symbol_table = parse_json_from_file(os.path.join(mm_project_directory(), "config", ".symbols", search_name+".json"))
            if search_name_extra == None or search_name_extra == '':
                return get_symbol_table_completions(symbol_table)
            elif 'innerClasses' in symbol_table and len(symbol_table['innerClasses']) > 0:
                for inner in symbol_table['innerClasses']:
                    if inner["name"] == search_name_extra:
                        return get_completions_for_inner_class(inner)

    if not os.path.exists(os.path.join(mm_project_directory(), 'config', '.apex_file_properties')):
        return []

    apex_props = parse_json_from_file(os.path.join(mm_project_directory(), "config", ".apex_file_properties"))

    for p in apex_props.keys():
        if p == search_name+".cls" and 'symbolTable' in apex_props[p] and apex_props[p]["symbolTable"] != None:
            symbol_table = apex_props[p]['symbolTable']
            if search_name_extra == None or search_name_extra == '':
                return get_symbol_table_completions(symbol_table)
            elif 'innerClasses' in symbol_table and len(symbol_table['innerClasses']) > 0:
                for inner in symbol_table['innerClasses']:
                    if inner["name"] == search_name_extra:
                        return get_completions_for_inner_class(inner)
    
    debug('no symbol table found for '+search_name)

def zip_directory(directory_to_zip, where_to_put_zip_file=None):
    return shutil.make_archive(where_to_put_zip_file, 'zip', os.path.join(directory_to_zip))

def get_version_number():
    try:
        json_data = open(os.path.join(config.mm_dir,"packages.json"))
        data = json.load(json_data)
        json_data.close()
        version = data["packages"][0]["platforms"]["osx"][0]["version"]
        return version
    except:
        return ''

class MavensMateParserCall(threading.Thread):
    def __init__(self):
        self.foo = 'bar';

    def run(self):
        pass



########NEW FILE########
