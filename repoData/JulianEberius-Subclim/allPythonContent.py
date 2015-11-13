__FILENAME__ = eclim
'''
This module manages the connection to the Eclim server. It is responsible
for sending the commands and parsing the responses of the server.
It should be independent of any Sublime Text 2 API.

There is one global variable 'eclim_executable' that needs to be set before
using the module. It should point to the "eclim" executable in your Eclipse
directory.
'''
import os
import json
import subprocess
try:
    # Python 3
    from . import subclim_logging
except (ValueError):
    # Python 2
    import subclim_logging

try:
    unicode
except NameError:
    # Python 3
    basestring = str

# points to eclim executable, see module-level comments
eclim_executable = None

log = subclim_logging.getLogger('subclim')


class EclimExecutionException(Exception):
    pass


class NotInEclipseProjectException(Exception):
    pass


def call_eclim(cmdline):
    ''' Generic call to eclim including error-handling '''
    def arg_string(s):
        return "%s %s" % (eclim_executable, s)

    def arg_seq(args):
        a = [eclim_executable]
        a.extend(args)
        return a

    cmd = None
    shell = None
    if isinstance(cmdline, basestring):
        cmd = arg_string(cmdline)
        shell = True
    elif hasattr(cmdline, '__iter__'):
        cmd = arg_seq(cmdline)
        shell = False
    else:
        raise EclimExecutionException('Unknown command line passed. ' + repr(cmd) + ' ' + (type(cmd)))
    log.info('Run: %s', cmd)

    # running with shell=False spawns new command windows for
    # each execution of eclim_executable
    sinfo = None
    if os.name == 'nt' and not shell:
        sinfo = subprocess.STARTUPINFO()
        sinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        sinfo.wShowWindow = subprocess.SW_HIDE

    popen = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, startupinfo=sinfo)
    out, err = popen.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    log.debug("Results:\n" + out)

    # error handling
    if err or "Connection refused" in out:
        error_msg = 'Error connecting to Eclim server: '
        if out:
            error_msg += out
        if err:
            error_msg += err
        if "Connection refused" in out:
            error_msg += " Is Eclipse running?"
        log.error(error_msg)
        raise EclimExecutionException(error_msg)
    return out


def get_context(filename):
    project_path = find_project_dir(filename)
    if not project_path:
        return None, None

    project_path = os.path.abspath(project_path)
    cmd = '-command project_list'
    out = call_eclim(cmd)
    if not out:
        return None, None

    try:
        obj = json.loads(out)
        for item in obj:
            path = os.path.abspath(item['path'])
            if path == project_path:
                relative = os.path.relpath(filename, project_path)
                return item['name'], relative
    except ValueError:
        subclim_logging.show_error_msg("Could not parse Eclim's response. "
                                       "Are you running Eclim version 1.7.3 or greater?")
    return None, None


def find_project_dir(file_dir):
    ''' tries to find a '.project' file as created by Eclipse to mark
    project folders by traversing the directory tree upward from the given
    directory'''
    def traverse_upward(look_for, start_at="."):
        p = os.path.abspath(start_at)

        while True:
            if look_for in os.listdir(p):
                return p
            new_p = os.path.abspath(os.path.join(p, ".."))
            if new_p == p:
                return None
            p = new_p

    if os.path.isfile(file_dir):
        file_dir = os.path.dirname(file_dir)
    return traverse_upward(".project", start_at=file_dir)


def update_java_src(project, filename):
    '''Updates Eclipse's status regarding the given file.'''
    update_cmd = ['-command', 'java_src_update', '-p', project, '-f', filename, '-v']
    out = call_eclim(update_cmd)
    return out


def update_scala_src(project, filename):
    '''Updates Eclipse's status regarding the given file.'''
    update_cmd = ['-command', 'scala_src_update', '-p', project, '-f', filename, '-v']
    out = call_eclim(update_cmd)
    return out


def get_problems(project):
    ''' returns a list of problems that Eclipse found in the given project'''
    get_problems_cmd = ['-command', 'problems', '-p', project]
    out = call_eclim(get_problems_cmd)
    return out


def parse_problems(out):
    '''Turns a problem message into a nice dict-representation'''
    results = {"errors": []}
    try:
        obj = json.loads(out)
        for item in obj:
            filename = os.path.split(item['filename'])[1]
            isError = not item['warning']
            results["errors"].append({"file": filename, "line": item['line'], "message": item['message'], "filepath": item['filename'], "error": isError})
    except Exception as e:
        log.error(e)
        results["errors"].append({"eclim_exception": str(e)})
    return results

########NEW FILE########
__FILENAME__ = generated
#!/usr/bin/env python
import sublime_plugin
try:
    # Python 3
    from . import subclim_logging
    from .subclim_plugin import SubclimBase
except (ValueError):
    # Python 2
    import subclim_logging
    from subclim_plugin import SubclimBase

log = subclim_logging.getLogger("subclim")


class SubclimJavaSrcCompileCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.JavacCommand
    javac -p project'''
    template = {'javac': ['-p project']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcCompileCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaClasspathVariableDeleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.classpath.ClasspathVariableDeleteCommand
    java_classpath_variable_delete -n name'''
    template = {'java_classpath_variable_delete': ['-n name']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaClasspathVariableDeleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaRefactoringUndoCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.refactoring.UndoCommand
    java_refactor_undo [-p]'''
    template = {'java_refactor_undo': ['[-p]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaRefactoringUndoCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSrcClassPrototypeCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.ClassPrototypeCommand
    java_class_prototype -c classname [-p project] [-f file]'''
    template = {'java_class_prototype': ['-c classname', '[-p project]', '[-f file]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcClassPrototypeCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaImplCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.impl.ImplCommand
    java_impl -p project -f file [-o offset] [-e encoding] [-t type] [-s superType] [-m methods]'''
    template = {'java_impl': ['-p project', '-f file', '[-o offset]', '[-e encoding]', '[-t type]', '[-s superType]', '[-m methods]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaImplCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaLog4jValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.log4j.ValidateCommand
    log4j_validate -p project -f file'''
    template = {'log4j_validate': ['-p project', '-f file']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaLog4jValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaConstructorCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.constructor.ConstructorCommand
    java_constructor -p project -f file -o offset [-e encoding] [-r properties]'''
    template = {'java_constructor': ['-p project', '-f file', '-o offset', '[-e encoding]', '[-r properties]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaConstructorCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaDocJavadocCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.doc.JavadocCommand
    javadoc -p project [-f file]'''
    template = {'javadoc': ['-p project', '[-f file]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaDocJavadocCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaBeanPropertiesCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.bean.PropertiesCommand
    java_bean_properties -p project -f file -o offset [-e encoding] -r properties -t type [-i]'''
    template = {'java_bean_properties': ['-p project', '-f file', '-o offset', '[-e encoding]', '-r properties', '-t type', '[-i]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaBeanPropertiesCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaDocSearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.doc.DocSearchCommand
    java_docsearch -n project [-f file] [-o offset] [-e encoding] [-l length] [-p pattern] [-t type] [-x context] [-s scope]'''
    template = {'java_docsearch': ['-n project', '[-f file]', '[-o offset]', '[-e encoding]', '[-l length]', '[-p pattern]', '[-t type]', '[-x context]', '[-s scope]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaDocSearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaIncludeImportOrderCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.include.ImportOrderCommand
    java_import_order -p project'''
    template = {'java_import_order': ['-p project']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaIncludeImportOrderCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSrcDirsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.SrcDirsCommand
    java_src_dirs -p project'''
    template = {'java_src_dirs': ['-p project']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcDirsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSrcFindCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.SrcFindCommand
    java_src_find -c classname [-p project]'''
    template = {'java_src_find': ['-c classname', '[-p project]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcFindCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaHierarchyCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.hierarchy.HierarchyCommand
    java_hierarchy -p project -f file -o offset -e encoding'''
    template = {'java_hierarchy': ['-p project', '-f file', '-o offset', '-e encoding']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaHierarchyCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaLaunchingListVmInstalls(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.launching.ListVmInstalls
    java_list_installs'''
    template = {'java_list_installs': []}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaLaunchingListVmInstalls.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaIncludeImportCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.include.ImportCommand
    java_import -n project -p pattern [-t type]'''
    template = {'java_import': ['-n project', '-p pattern', '[-t type]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaIncludeImportCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaRefactoringRenameCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.refactoring.RenameCommand
    java_refactor_rename -p project -f file -n name -o offset -l length -e encoding [-v] [-d diff]'''
    template = {'java_refactor_rename': ['-p project', '-f file', '-n name', '-o offset', '-l length', '-e encoding', '[-v]', '[-d diff]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaRefactoringRenameCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaRefactoringRedoCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.refactoring.RedoCommand
    java_refactor_redo [-p]'''
    template = {'java_refactor_redo': ['[-p]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaRefactoringRedoCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaCodeCorrectCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.correct.CodeCorrectCommand
    java_correct -p project -f file -l line -o offset [-e encoding] [-a apply]'''
    template = {'java_correct': ['-p project', '-f file', '-l line', '-o offset', '[-e encoding]', '[-a apply]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaCodeCorrectCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaClasspathVariablesCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.classpath.ClasspathVariablesCommand
    java_classpath_variables'''
    template = {'java_classpath_variables': []}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaClasspathVariablesCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaWebxmlValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.webxml.ValidateCommand
    webxml_validate -p project -f file'''
    template = {'webxml_validate': ['-p project', '-f file']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaWebxmlValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaDelegateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.delegate.DelegateCommand
    java_delegate -p project -f file -o offset -e encoding [-t type] [-s superType] [-m methods]'''
    template = {'java_delegate': ['-p project', '-f file', '-o offset', '-e encoding', '[-t type]', '[-s superType]', '[-m methods]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaDelegateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaIncludeImportMissingCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.include.ImportMissingCommand
    java_import_missing -p project -f file'''
    template = {'java_import_missing': ['-p project', '-f file']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaIncludeImportMissingCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaDocCommentCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.doc.CommentCommand
    javadoc_comment -p project -f file -o offset [-e encoding]'''
    template = {'javadoc_comment': ['-p project', '-f file', '-o offset', '[-e encoding]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaDocCommentCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.complete.CodeCompleteCommand
    java_complete -p project -f file -o offset -e encoding -l layout'''
    template = {'java_complete': ['-p project', '-f file', '-o offset', '-e encoding', '-l layout']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSrcUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.SrcUpdateCommand
    java_src_update -p project -f file [-v] [-b]'''
    template = {'java_src_update': ['-p project', '-f file', '[-v]', '[-b]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaCheckstyleCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.checkstyle.CheckstyleCommand
    java_checkstyle -p project -f file'''
    template = {'java_checkstyle': ['-p project', '-f file']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaCheckstyleCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaIncludeUnusedImportsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.include.UnusedImportsCommand
    java_imports_unused -p project -f file'''
    template = {'java_imports_unused': ['-p project', '-f file']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaIncludeUnusedImportsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaClasspathCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.classpath.ClasspathCommand
    java_classpath -p project [-d delimiter]'''
    template = {'java_classpath': ['-p project', '[-d delimiter]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaClasspathCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaFormatCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.format.FormatCommand
    java_format -p project -f file -b boffset -e eoffset'''
    template = {'java_format': ['-p project', '-f file', '-b boffset', '-e eoffset']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaFormatCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaClasspathVariableCreateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.classpath.ClasspathVariableCreateCommand
    java_classpath_variable_create -n name -p path'''
    template = {'java_classpath_variable_create': ['-n name', '-p path']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaClasspathVariableCreateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaJunitJUnitImplCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.junit.JUnitImplCommand
    java_junit_impl -p project -f file [-o offset] [-e encoding] [-t type] [-b baseType] [-s superType] [-m methods]'''
    template = {'java_junit_impl': ['-p project', '-f file', '[-o offset]', '[-e encoding]', '[-t type]', '[-b baseType]', '[-s superType]', '[-m methods]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaJunitJUnitImplCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimAntRunTargetsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.ant.command.run.TargetsCommand
    ant_targets -p project -f file'''
    template = {'ant_targets': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimAntRunTargetsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSrcFileExistsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.SrcFileExistsCommand
    java_src_exists -f file [-p project]'''
    template = {'java_src_exists': ['-f file', '[-p project]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcFileExistsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimAntCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.ant.command.complete.CodeCompleteCommand
    ant_complete -p project -f file -o offset -e encoding'''
    template = {'ant_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimAntCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSrcRunCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.src.JavaCommand
    java -p project [-d] [-c classname] [-w workingdir] [-v vmargs] [-s sysprops] [-e envargs] [-a args]'''
    template = {'java': ['-p project', '[-d]', '[-c classname]', '[-w workingdir]', '[-v vmargs]', '[-s sysprops]', '[-e envargs]', '[-a args]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSrcRunCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimMavenDependencySearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.maven.command.dependency.SearchCommand
    maven_dependency_search -p project -f file -t type -s search'''
    template = {'maven_dependency_search': ['-p project', '-f file', '-t type', '-s search']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimMavenDependencySearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimAntValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.ant.command.validate.ValidateCommand
    ant_validate -p project -f file'''
    template = {'ant_validate': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimAntValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimJavaSearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.jdt.command.search.SearchCommand
    java_search [-n project] [-f file] [-o offset] [-e encoding] [-l length] [-p pattern] [-t type] [-x context] [-s scope] [-i]'''
    template = {'java_search': ['[-n project]', '[-f file]', '[-o offset]', '[-e encoding]', '[-l length]', '[-p pattern]', '[-t type]', '[-x context]', '[-s scope]', '[-i]']}

    def is_visible(self):
        return 'Java.tmLanguage' in self.view.settings().get("syntax")

    def run(self, edit, **kwargs):
        if not self.is_visible():
            return
        out = self.run_template(SubclimJavaSearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimEclipseReloadCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.eclipse.AbstractEclimApplication.ReloadCommand
    reload'''
    template = {'reload': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimEclipseReloadCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreArchiveReadCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.archive.ArchiveReadCommand
    archive_read -f file'''
    template = {'archive_read': ['-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreArchiveReadCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreEclipseJobsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.eclipse.JobsCommand
    jobs [-f family]'''
    template = {'jobs': ['[-f family]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreEclipseJobsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectBuildCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectBuildCommand
    project_build -p project'''
    template = {'project_build': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectBuildCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreSearchLocateFileCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.search.LocateFileCommand
    locate_file -p pattern -s scope [-n project] [-f file]'''
    template = {'locate_file': ['-p pattern', '-s scope', '[-n project]', '[-f file]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreSearchLocateFileCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreSettingsUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.admin.SettingsUpdateCommand
    settings_update [-s settings]'''
    template = {'settings_update': ['[-s settings]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreSettingsUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectDeleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectDeleteCommand
    project_delete -p project'''
    template = {'project_delete': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectDeleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreSettingsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.admin.SettingsCommand
    settings'''
    template = {'settings': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreSettingsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectMoveCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectMoveCommand
    project_move -p project -d dir'''
    template = {'project_move': ['-p project', '-d dir']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectMoveCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreXmlValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.xml.ValidateCommand
    xml_validate -p project -f file [-s]'''
    template = {'xml_validate': ['-p project', '-f file', '[-s]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreXmlValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreEclipseWorkspaceCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.eclipse.WorkspaceCommand
    workspace_dir'''
    template = {'workspace_dir': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreEclipseWorkspaceCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreHistoryRevisionCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.history.HistoryRevisionCommand
    history_revision -p project -f file -r revision'''
    template = {'history_revision': ['-p project', '-f file', '-r revision']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreHistoryRevisionCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectNatureAliasesCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectNatureAliasesCommand
    project_nature_aliases'''
    template = {'project_nature_aliases': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectNatureAliasesCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectUpdateCommand
    project_update -p project [-b buildfile] [-s settings]'''
    template = {'project_update': ['-p project', '[-b buildfile]', '[-s settings]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectOpenCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectOpenCommand
    project_open -p project'''
    template = {'project_open': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectOpenCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectCreateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectCreateCommand
    project_create -f folder [-p name] -n natures [-d depends]'''
    template = {'project_create': ['-f folder', '[-p name]', '-n natures', '[-d depends]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectCreateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectRefreshCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectRefreshCommand
    project_refresh -p project'''
    template = {'project_refresh': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectRefreshCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCorePingCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.admin.PingCommand
    ping'''
    template = {'ping': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCorePingCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectSettingCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectSettingCommand
    project_setting -p project -s setting [-v value]'''
    template = {'project_setting': ['-p project', '-s setting', '[-v value]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectSettingCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreShutdownCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.admin.ShutdownCommand
    shutdown'''
    template = {'shutdown': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreShutdownCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreHistoryClearCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.history.HistoryClearCommand
    history_clear -p project -f file'''
    template = {'history_clear': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreHistoryClearCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreXmlFormatCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.xml.FormatCommand
    xml_format -f file -w linewidth -i indent -m fileformat'''
    template = {'xml_format': ['-f file', '-w linewidth', '-i indent', '-m fileformat']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreXmlFormatCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProblemsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.problems.ProblemsCommand
    problems -p project [-e]'''
    template = {'problems': ['-p project', '[-e]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProblemsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectSettingsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectSettingsCommand
    project_settings [-p project]'''
    template = {'project_settings': ['[-p project]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectSettingsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectNatureAddCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectNatureAddCommand
    project_nature_add -p project -n nature'''
    template = {'project_nature_add': ['-p project', '-n nature']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectNatureAddCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectByResource(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectByResource
    project_by_resource -f file'''
    template = {'project_by_resource': ['-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectByResource.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectLinkResource(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectLinkResource
    project_link_resource -f file'''
    template = {'project_link_resource': ['-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectLinkResource.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreHistoryListCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.history.HistoryListCommand
    history_list -p project -f file'''
    template = {'history_list': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreHistoryListCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectCloseCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectCloseCommand
    project_close -p project'''
    template = {'project_close': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectCloseCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreHistoryAddCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.history.HistoryAddCommand
    history_add -p project -f file'''
    template = {'history_add': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreHistoryAddCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectsCommand
    projects'''
    template = {'projects': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectInfoCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectInfoCommand
    project_info -p project'''
    template = {'project_info': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectInfoCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectListCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectListCommand
    project_list [-n nature]'''
    template = {'project_list': ['[-n nature]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectListCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectNaturesCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectNaturesCommand
    project_natures [-p project]'''
    template = {'project_natures': ['[-p project]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectNaturesCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectRefreshFileCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectRefreshFileCommand
    project_refresh_file -p project -f file'''
    template = {'project_refresh_file': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectRefreshFileCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectImportCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectImportCommand
    project_import -f folder'''
    template = {'project_import': ['-f folder']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectImportCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectNatureRemoveCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectNatureRemoveCommand
    project_nature_remove -p project -n nature'''
    template = {'project_nature_remove': ['-p project', '-n nature']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectNatureRemoveCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimCoreProjectRenameCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.core.command.project.ProjectRenameCommand
    project_rename -p project -n name'''
    template = {'project_rename': ['-p project', '-n name']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimCoreProjectRenameCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicBuildpathsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.buildpath.BuildpathsCommand
    dltk_buildpaths -p project'''
    template = {'dltk_buildpaths': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicBuildpathsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicBuildpathVariableCreateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.buildpath.BuildpathVariableCreateCommand
    dltk_buildpath_variable_create -n name -p path'''
    template = {'dltk_buildpath_variable_create': ['-n name', '-p path']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicBuildpathVariableCreateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicLaunchingInterpretersCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.launching.InterpretersCommand
    dltk_interpreters [-p project] [-n nature]'''
    template = {'dltk_interpreters': ['[-p project]', '[-n nature]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicLaunchingInterpretersCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicLaunchingDeleteInterpreterCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.launching.DeleteInterpreterCommand
    dltk_remove_interpreter -n nature -i interpreter'''
    template = {'dltk_remove_interpreter': ['-n nature', '-i interpreter']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicLaunchingDeleteInterpreterCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicBuildpathVariableDeleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.buildpath.BuildpathVariableDeleteCommand
    dltk_buildpath_variable_delete -n name'''
    template = {'dltk_buildpath_variable_delete': ['-n name']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicBuildpathVariableDeleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicSearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.search.SearchCommand
    dltk_search [-n project] [-f file] [-o offset] [-l length] [-e encoding] [-p pattern] [-t type] [-x context] [-s scope] [-i]'''
    template = {'dltk_search': ['[-n project]', '[-f file]', '[-o offset]', '[-l length]', '[-e encoding]', '[-p pattern]', '[-t type]', '[-x context]', '[-s scope]', '[-i]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicSearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicLaunchingAddInterpreterCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.launching.AddInterpreterCommand
    dltk_add_interpreter -n nature -t type -i interpreter'''
    template = {'dltk_add_interpreter': ['-n nature', '-t type', '-i interpreter']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicLaunchingAddInterpreterCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimDynamicBuildpathVariablesCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltk.command.buildpath.BuildpathVariablesCommand
    dltk_buildpath_variables'''
    template = {'dltk_buildpath_variables': []}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimDynamicBuildpathVariablesCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimPhpSrcUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.pdt.command.src.SrcUpdateCommand
    php_src_update -p project -f file [-v] [-b]'''
    template = {'php_src_update': ['-p project', '-f file', '[-v]', '[-b]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimPhpSrcUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimPhpCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.pdt.command.complete.CodeCompleteCommand
    php_complete -p project -f file -o offset -e encoding'''
    template = {'php_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimPhpCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimPhpSearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.pdt.command.search.SearchCommand
    php_search [-n project] [-f file] [-o offset] [-l length] [-e encoding] [-p pattern] [-t type] [-x context] [-s scope] [-i]'''
    template = {'php_search': ['[-n project]', '[-f file]', '[-o offset]', '[-l length]', '[-e encoding]', '[-p pattern]', '[-t type]', '[-x context]', '[-s scope]', '[-i]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimPhpSearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangSrcUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.src.SrcUpdateCommand
    c_src_update -p project -f file [-v] [-b]'''
    template = {'c_src_update': ['-p project', '-f file', '[-v]', '[-b]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangSrcUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangProjectSourceEntryCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.project.SourceEntryCommand
    c_project_src -p project -a action -d dir [-e excludes]'''
    template = {'c_project_src': ['-p project', '-a action', '-d dir', '[-e excludes]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangProjectSourceEntryCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangProjectSourcePathsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.project.SourcePathsCommand
    c_sourcepaths -p project'''
    template = {'c_sourcepaths': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangProjectSourcePathsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangProjectIncludePathsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.project.IncludePathsCommand
    c_includepaths -p project'''
    template = {'c_includepaths': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangProjectIncludePathsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangSearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.search.SearchCommand
    c_search [-n project] [-f file] [-o offset] [-l length] [-e encoding] [-p pattern] [-t type] [-x context] [-s scope] [-i]'''
    template = {'c_search': ['[-n project]', '[-f file]', '[-o offset]', '[-l length]', '[-e encoding]', '[-p pattern]', '[-t type]', '[-x context]', '[-s scope]', '[-i]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangSearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangProjectConfigurationsCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.project.ConfigurationsCommand
    c_project_configs -p project'''
    template = {'c_project_configs': ['-p project']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangProjectConfigurationsCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangProjectSymbolEntryCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.project.SymbolEntryCommand
    c_project_symbol -p project -a action -l lang -n name [-v value]'''
    template = {'c_project_symbol': ['-p project', '-a action', '-l lang', '-n name', '[-v value]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangProjectSymbolEntryCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangProjectIncludeEntryCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.project.IncludeEntryCommand
    c_project_include -p project -a action -l lang -d dir'''
    template = {'c_project_include': ['-p project', '-a action', '-l lang', '-d dir']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangProjectIncludeEntryCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangCallHierarchyCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.hierarchy.CallHierarchyCommand
    c_callhierarchy -p project -f file -o offset -l length -e encoding'''
    template = {'c_callhierarchy': ['-p project', '-f file', '-o offset', '-l length', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangCallHierarchyCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimClangCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.cdt.command.complete.CodeCompleteCommand
    c_complete -p project -f file -o offset -e encoding -l layout'''
    template = {'c_complete': ['-p project', '-f file', '-o offset', '-e encoding', '-l layout']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimClangCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebXsdValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.validate.XsdValidateCommand
    xsd_validate -p project -f file'''
    template = {'xsd_validate': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebXsdValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebHtmlCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.complete.HtmlCodeCompleteCommand
    html_complete -p project -f file -o offset -e encoding'''
    template = {'html_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebHtmlCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebHtmlValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.validate.HtmlValidateCommand
    html_validate -p project -f file'''
    template = {'html_validate': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebHtmlValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebJavaScriptCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.complete.JavaScriptCodeCompleteCommand
    javascript_complete -p project -f file -o offset -e encoding'''
    template = {'javascript_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebJavaScriptCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebCssValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.validate.CssValidateCommand
    css_validate -p project -f file'''
    template = {'css_validate': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebCssValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebJavaScriptSrcUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.src.JavaScriptSrcUpdateCommand
    javascript_src_update -p project -f file [-v]'''
    template = {'javascript_src_update': ['-p project', '-f file', '[-v]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebJavaScriptSrcUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebCssCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.complete.CssCodeCompleteCommand
    css_complete -p project -f file -o offset -e encoding'''
    template = {'css_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebCssCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebXmlCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.complete.XmlCodeCompleteCommand
    xml_complete -p project -f file -o offset -e encoding'''
    template = {'xml_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebXmlCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimWebDtdValidateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.wst.command.validate.DtdValidateCommand
    dtd_validate -p project -f file'''
    template = {'dtd_validate': ['-p project', '-f file']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimWebDtdValidateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimRubySrcUpdateCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltkruby.command.src.SrcUpdateCommand
    ruby_src_update -p project -f file [-v] [-b]'''
    template = {'ruby_src_update': ['-p project', '-f file', '[-v]', '[-b]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimRubySrcUpdateCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimRubyCodeCompleteCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltkruby.command.complete.CodeCompleteCommand
    ruby_complete -p project -f file -o offset -e encoding'''
    template = {'ruby_complete': ['-p project', '-f file', '-o offset', '-e encoding']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimRubyCodeCompleteCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimRubySearchCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltkruby.command.search.SearchCommand
    ruby_search [-n project] [-f file] [-o offset] [-l length] [-e encoding] [-p pattern] [-t type] [-x context] [-s scope] [-i]'''
    template = {'ruby_search': ['[-n project]', '[-f file]', '[-o offset]', '[-l length]', '[-e encoding]', '[-p pattern]', '[-t type]', '[-x context]', '[-s scope]', '[-i]']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimRubySearchCommand.template, **kwargs)
        log.debug("Results:\n" + out)


class SubclimRubyLaunchingAddInterpreterCommand(sublime_plugin.TextCommand, SubclimBase):
    '''org.eclim.plugin.dltkruby.command.launching.AddInterpreterCommand
    ruby_add_interpreter -n nature -i interpreter'''
    template = {'ruby_add_interpreter': ['-n nature', '-i interpreter']}

    def run(self, edit, **kwargs):
        out = self.run_template(SubclimRubyLaunchingAddInterpreterCommand.template, **kwargs)
        log.debug("Results:\n" + out)

'''
[{'caption': 'Subclim: javac', 'command': 'subclim_java_src_compile'},
 {'caption': 'Subclim: java_classpath_variable_delete',
  'command': 'subclim_java_classpath_variable_delete'},
 {'caption': 'Subclim: java_refactor_undo',
  'command': 'subclim_java_refactoring_undo'},
 {'caption': 'Subclim: java_class_prototype',
  'command': 'subclim_java_src_class_prototype'},
 {'caption': 'Subclim: java_impl', 'command': 'subclim_java_impl'},
 {'caption': 'Subclim: log4j_validate',
  'command': 'subclim_java_log4j_validate'},
 {'caption': 'Subclim: java_constructor',
  'command': 'subclim_java_constructor'},
 {'caption': 'Subclim: javadoc', 'command': 'subclim_java_doc_javadoc'},
 {'caption': 'Subclim: java_bean_properties',
  'command': 'subclim_java_bean_properties'},
 {'caption': 'Subclim: java_docsearch', 'command': 'subclim_java_doc_search'},
 {'caption': 'Subclim: java_import_order',
  'command': 'subclim_java_include_import_order'},
 {'caption': 'Subclim: java_src_dirs', 'command': 'subclim_java_src_dirs'},
 {'caption': 'Subclim: java_src_find', 'command': 'subclim_java_src_find'},
 {'caption': 'Subclim: java_hierarchy', 'command': 'subclim_java_hierarchy'},
 {'caption': 'Subclim: java_list_installs',
  'command': 'subclim_java_launching_list_vm_installs'},
 {'caption': 'Subclim: java_import', 'command': 'subclim_java_include_import'},
 {'caption': 'Subclim: java_refactor_rename',
  'command': 'subclim_java_refactoring_rename'},
 {'caption': 'Subclim: java_refactor_redo',
  'command': 'subclim_java_refactoring_redo'},
 {'caption': 'Subclim: java_correct', 'command': 'subclim_java_code_correct'},
 {'caption': 'Subclim: java_classpath_variables',
  'command': 'subclim_java_classpath_variables'},
 {'caption': 'Subclim: webxml_validate',
  'command': 'subclim_java_webxml_validate'},
 {'caption': 'Subclim: java_delegate', 'command': 'subclim_java_delegate'},
 {'caption': 'Subclim: java_import_missing',
  'command': 'subclim_java_include_import_missing'},
 {'caption': 'Subclim: javadoc_comment',
  'command': 'subclim_java_doc_comment'},
 {'caption': 'Subclim: java_complete',
  'command': 'subclim_java_code_complete'},
 {'caption': 'Subclim: java_src_update', 'command': 'subclim_java_src_update'},
 {'caption': 'Subclim: java_checkstyle', 'command': 'subclim_java_checkstyle'},
 {'caption': 'Subclim: java_imports_unused',
  'command': 'subclim_java_include_unused_imports'},
 {'caption': 'Subclim: java_classpath', 'command': 'subclim_java_classpath'},
 {'caption': 'Subclim: java_format', 'command': 'subclim_java_format'},
 {'caption': 'Subclim: java_classpath_variable_create',
  'command': 'subclim_java_classpath_variable_create'},
 {'caption': 'Subclim: java_junit_impl',
  'command': 'subclim_java_junit_j_unit_impl'},
 {'caption': 'Subclim: ant_targets', 'command': 'subclim_ant_run_targets'},
 {'caption': 'Subclim: java_src_exists',
  'command': 'subclim_java_src_file_exists'},
 {'caption': 'Subclim: ant_complete', 'command': 'subclim_ant_code_complete'},
 {'caption': 'Subclim: java', 'command': 'subclim_java_src_run'},
 {'caption': 'Subclim: maven_dependency_search',
  'command': 'subclim_maven_dependency_search'},
 {'caption': 'Subclim: ant_validate', 'command': 'subclim_ant_validate'},
 {'caption': 'Subclim: java_search', 'command': 'subclim_java_search'},
 {'caption': 'Subclim: reload', 'command': 'subclim_eclipse_reload'},
 {'caption': 'Subclim: archive_read', 'command': 'subclim_core_archive_read'},
 {'caption': 'Subclim: jobs', 'command': 'subclim_core_eclipse_jobs'},
 {'caption': 'Subclim: project_build',
  'command': 'subclim_core_project_build'},
 {'caption': 'Subclim: locate_file',
  'command': 'subclim_core_search_locate_file'},
 {'caption': 'Subclim: settings_update',
  'command': 'subclim_core_settings_update'},
 {'caption': 'Subclim: project_delete',
  'command': 'subclim_core_project_delete'},
 {'caption': 'Subclim: settings', 'command': 'subclim_core_settings'},
 {'caption': 'Subclim: project_move', 'command': 'subclim_core_project_move'},
 {'caption': 'Subclim: xml_validate', 'command': 'subclim_core_xml_validate'},
 {'caption': 'Subclim: workspace_dir',
  'command': 'subclim_core_eclipse_workspace'},
 {'caption': 'Subclim: history_revision',
  'command': 'subclim_core_history_revision'},
 {'caption': 'Subclim: project_nature_aliases',
  'command': 'subclim_core_project_nature_aliases'},
 {'caption': 'Subclim: project_update',
  'command': 'subclim_core_project_update'},
 {'caption': 'Subclim: project_open', 'command': 'subclim_core_project_open'},
 {'caption': 'Subclim: project_create',
  'command': 'subclim_core_project_create'},
 {'caption': 'Subclim: project_refresh',
  'command': 'subclim_core_project_refresh'},
 {'caption': 'Subclim: ping', 'command': 'subclim_core_ping'},
 {'caption': 'Subclim: project_setting',
  'command': 'subclim_core_project_setting'},
 {'caption': 'Subclim: shutdown', 'command': 'subclim_core_shutdown'},
 {'caption': 'Subclim: history_clear',
  'command': 'subclim_core_history_clear'},
 {'caption': 'Subclim: xml_format', 'command': 'subclim_core_xml_format'},
 {'caption': 'Subclim: problems', 'command': 'subclim_core_problems'},
 {'caption': 'Subclim: project_settings',
  'command': 'subclim_core_project_settings'},
 {'caption': 'Subclim: project_nature_add',
  'command': 'subclim_core_project_nature_add'},
 {'caption': 'Subclim: project_by_resource',
  'command': 'subclim_core_project_by_resource'},
 {'caption': 'Subclim: project_link_resource',
  'command': 'subclim_core_project_link_resource'},
 {'caption': 'Subclim: history_list', 'command': 'subclim_core_history_list'},
 {'caption': 'Subclim: project_close',
  'command': 'subclim_core_project_close'},
 {'caption': 'Subclim: history_add', 'command': 'subclim_core_history_add'},
 {'caption': 'Subclim: projects', 'command': 'subclim_core_projects'},
 {'caption': 'Subclim: project_info', 'command': 'subclim_core_project_info'},
 {'caption': 'Subclim: project_list', 'command': 'subclim_core_project_list'},
 {'caption': 'Subclim: project_natures',
  'command': 'subclim_core_project_natures'},
 {'caption': 'Subclim: project_refresh_file',
  'command': 'subclim_core_project_refresh_file'},
 {'caption': 'Subclim: project_import',
  'command': 'subclim_core_project_import'},
 {'caption': 'Subclim: project_nature_remove',
  'command': 'subclim_core_project_nature_remove'},
 {'caption': 'Subclim: project_rename',
  'command': 'subclim_core_project_rename'},
 {'caption': 'Subclim: dltk_buildpaths',
  'command': 'subclim_dynamic_buildpaths'},
 {'caption': 'Subclim: dltk_buildpath_variable_create',
  'command': 'subclim_dynamic_buildpath_variable_create'},
 {'caption': 'Subclim: dltk_interpreters',
  'command': 'subclim_dynamic_launching_interpreters'},
 {'caption': 'Subclim: dltk_remove_interpreter',
  'command': 'subclim_dynamic_launching_delete_interpreter'},
 {'caption': 'Subclim: dltk_buildpath_variable_delete',
  'command': 'subclim_dynamic_buildpath_variable_delete'},
 {'caption': 'Subclim: dltk_search', 'command': 'subclim_dynamic_search'},
 {'caption': 'Subclim: dltk_add_interpreter',
  'command': 'subclim_dynamic_launching_add_interpreter'},
 {'caption': 'Subclim: dltk_buildpath_variables',
  'command': 'subclim_dynamic_buildpath_variables'},
 {'caption': 'Subclim: php_src_update', 'command': 'subclim_php_src_update'},
 {'caption': 'Subclim: php_complete', 'command': 'subclim_php_code_complete'},
 {'caption': 'Subclim: php_search', 'command': 'subclim_php_search'},
 {'caption': 'Subclim: c_src_update', 'command': 'subclim_clang_src_update'},
 {'caption': 'Subclim: c_project_src',
  'command': 'subclim_clang_project_source_entry'},
 {'caption': 'Subclim: c_sourcepaths',
  'command': 'subclim_clang_project_source_paths'},
 {'caption': 'Subclim: c_includepaths',
  'command': 'subclim_clang_project_include_paths'},
 {'caption': 'Subclim: c_search', 'command': 'subclim_clang_search'},
 {'caption': 'Subclim: c_project_configs',
  'command': 'subclim_clang_project_configurations'},
 {'caption': 'Subclim: c_project_symbol',
  'command': 'subclim_clang_project_symbol_entry'},
 {'caption': 'Subclim: c_project_include',
  'command': 'subclim_clang_project_include_entry'},
 {'caption': 'Subclim: c_callhierarchy',
  'command': 'subclim_clang_call_hierarchy'},
 {'caption': 'Subclim: c_complete', 'command': 'subclim_clang_code_complete'},
 {'caption': 'Subclim: xsd_validate', 'command': 'subclim_web_xsd_validate'},
 {'caption': 'Subclim: html_complete',
  'command': 'subclim_web_html_code_complete'},
 {'caption': 'Subclim: html_validate', 'command': 'subclim_web_html_validate'},
 {'caption': 'Subclim: javascript_complete',
  'command': 'subclim_web_java_script_code_complete'},
 {'caption': 'Subclim: css_validate', 'command': 'subclim_web_css_validate'},
 {'caption': 'Subclim: javascript_src_update',
  'command': 'subclim_web_java_script_src_update'},
 {'caption': 'Subclim: css_complete',
  'command': 'subclim_web_css_code_complete'},
 {'caption': 'Subclim: xml_complete',
  'command': 'subclim_web_xml_code_complete'},
 {'caption': 'Subclim: dtd_validate', 'command': 'subclim_web_dtd_validate'},
 {'caption': 'Subclim: ruby_src_update', 'command': 'subclim_ruby_src_update'},
 {'caption': 'Subclim: ruby_complete',
  'command': 'subclim_ruby_code_complete'},
 {'caption': 'Subclim: ruby_search', 'command': 'subclim_ruby_search'},
 {'caption': 'Subclim: ruby_add_interpreter',
  'command': 'subclim_ruby_launching_add_interpreter'}]
'''
########NEW FILE########
__FILENAME__ = generate
#!/usr/bin/env python
'''Let's cheat and generate commands based off of what the help output claims.'''
import sys
import re
from pprint import pprint


remove = ('command', 'plugin', 'AbstractEclimApplication', 'admin')
substitute = {
    'pdt': 'Php',
    'wst': 'Web',
    'jdt': 'Java',
    'cdt': 'Clang',
    'dltk': 'Dynamic',
    'dltkruby': 'Ruby',
    'JavaCommand': 'RunCommand',
    'JavacCommand': 'CompileCommand'
}
packages = {
    'org.eclim.plugin.jdt': 'Java.tmLanguage'
    # more to follow
}


def pairs(items):
    '''magical.'''
    return zip(*[iter(items)] * 2)


def package_name(klass):
    for k in packages.keys():
        if klass.startswith(k):
            return packages[k]
    return None


def plugin_name(klass):
    '''org.eclim.plugin.toolkit.command.dostuff.DoStuffCommand => SubclimToolkitDoStuffCommand'''
    # it ain't perfect, but it'll get the job done
    klass = klass.replace('org.eclim.', '')

    # fancy capitalization
    s = [substitute.get(x, x[0].upper() + x[1:]) for x in klass.split('.') if x not in remove]
    # strip out the last part of the package if it's part of the name
    if s[-2] in s[-1]:
        del s[-2]
    return 'Subclim' + ''.join(s)


def command_name(plugin):
    plugin = re.sub('Command$', '', plugin)
    plugin = plugin[0] + re.sub('([A-Z])', '_\\1', plugin[1:])
    return plugin.lower()


def parse_args(command):
    '''Create a list of arguments from the command output'''
    def append(acc):
        if len(acc) > 0:
            ret[k].append(' '.join(acc))
        return []
    ret = {}
    items = command.split(' ')
    k = items[0]
    ret[k] = []
    acc = []
    for i in items[1:]:
        if i.startswith('-') or i.startswith('[-'):
            acc = append(acc)
        acc.append(i)
    append(acc)
    return ret


def main(args):
    lines = sys.stdin.readlines()
    print '#!/usr/bin/env python'
    print 'import sys, os, string, re, subprocess, sublime, sublime_plugin, subclim_logging'
    print 'from subclim_plugin import SubclimBase'
    print 'log = subclim_logging.getLogger("subclim")'
    print
    for command, klass in pairs(lines):
        klass = klass.strip().replace('class: ', '')
        command = command.strip()
        plugin = plugin_name(klass)
        package = package_name(klass)
        print '#', klass
        print '#', command
        print 'class', plugin + '(sublime_plugin.TextCommand, SubclimBase):'
        print '\ttemplate = ' + repr(parse_args(command))
        if package is not None:
            print '\tdef is_visible(self):'
            print '\t\treturn ' + repr(package) + ' in self.view.settings().get("syntax")'
        print '\tdef run(self, edit, **kwargs):'
        if package is not None:
            print '\t\tif not self.is_visible(): return'
        print '\t\tout = self.run_template(' + plugin + '.template, **kwargs)'
        print '\t\tlog.debug("Results:\\n" + out)'
        print

    sublime_commands = []
    for command, klass in pairs(lines):
        klass = klass.strip().replace('class: ', '')
        command = re.sub(' .*$', '', command.strip())
        sublime_commands.append({'caption': 'Subclim: ' + command, 'command': command_name(plugin_name(klass))})
    pprint(sublime_commands)

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = subclim_logging
import sublime
import sublime_plugin
import logging


def show_error_msg(msg):
    sublime.error_message(msg)


class StatusBarLogHandler(logging.Handler):
    def __init__(self, key, view=None):
        logging.Handler.__init__(self)
        self.key = key
        self.view = view

    def emit(self, record):
        view = self.view
        if view is None:
            w = sublime.active_window()
            if w is not None:
                view = w.active_view()
            else:
                return
        display = self.format(record)
        view.set_status(self.key, str(display))
        # clear error after 5 seconds
        sublime.set_timeout(lambda: view.erase_status(self.key), 5000)
        return


class ViewLogHandler(logging.Handler):
    def __init__(self, name=None, view=None):
        logging.Handler.__init__(self)
        self.name = name
        self.view = None
        if type(view) == sublime.View:
            self.view = view
        return

    def find_views(self, name):
        views = []
        for w in sublime.windows():
            for v in w.views():
                if v.name() == name:
                    views.append(v)
        return views

    # for some reason, if the tab isn't actually active, view.window() returns None
    # so we have to ask the windows if they have the view in them
    def view_active(self, view):
        for w in sublime.windows():
            g, idx = w.get_view_index(view)
            if g == -1 and idx == -1:
                continue
            return True
        # close the view, there's nothing to see here
        view.run_command('close')
        return False

    def create_view(self):
        w = sublime.active_window()
        if w is None:
            return
        v = w.new_file()
        v.set_scratch(True)
        if self.name is not None:
            v.set_name(self.name)
        return v

    def emit(self, record):
        # doing the write in an EventHandler makes ST2 crash
        # so we queue the write out to the main thread
        sublime.set_timeout(lambda: self.write(self.view, record), 50)
        return

    # is there a way to make the edit without forcing the view to activate?
    def write(self, view, record):
        # if we don't yet have an active window, then we really can't log the message
        if sublime.active_window() is None:
            return

        # if we don't know where we're writing to, find it
        if self.view is None and self.name is not None:
            candidates = self.find_views(self.name)
            # print(candidates)
            if len(candidates) > 0:
                self.view = candidates[0]

        # if we still don't know where we're writing to, make it
        # or if the window was previously closed, create a new one
        if self.view is None or not self.view_active(self.view):
            self.view = self.create_view()

        # insert text
        display = self.format(record)
        self.view.run_command('write_log_to_new_file', {'output': display})
        return


def getLogger(name, flush=False):
    '''do the heavy lifting'''
    log = logging.getLogger(name)

    # if we have already set up logging
    if len(log.handlers) > 0:
        if not flush:
            return log
        for h in log.handlers:
            log.removeHandler(h)
    fmt = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')

    # add in a ViewLogHandlder
    handler = ViewLogHandler(name='* ' + name + ' logs *')
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(fmt)
    log.addHandler(handler)

    # add in a status bar handler for errors
    handler = StatusBarLogHandler(name)
    handler.setLevel(logging.ERROR)
    log.addHandler(handler)

    # add in a file handler
    # handler = logging.FileHandler(os.environ['HOME'] + '/' + name + '.log','a')
    # handler.setLevel(logging.DEBUG)
    # handler.setFormatter(fmt)
    # log.addHandler(handler)

    # log.setLevel(logging.DEBUG)
    log.setLevel(logging.ERROR)
    return log


class WriteLogToNewFile(sublime_plugin.TextCommand):
    '''write log output to a new file'''

    def run(self, edit, output):
        self.view.set_read_only(False)
        point = self.view.layout_to_text(self.view.layout_extent())
        self.view.insert(edit, point, str(output) + "\n")
        self.view.set_read_only(True)
        point = self.view.layout_to_text(self.view.layout_extent())
        self.view.show(point)

########NEW FILE########
__FILENAME__ = subclim_plugin
'''Integrates ST2 with Eclim running in an Eclipse instance.
Enables Java completions / go to definition etc'''
import sublime_plugin
import sublime
import re
import os
import json
import threading

try:
    # Python 3
    from . import eclim
    from . import subclim_logging
    import queue
except (ValueError):
    # Python 2
    import eclim
    import subclim_logging
    import Queue as queue

log = subclim_logging.getLogger('subclim')
settings = sublime.load_settings("Subclim.sublime-settings")
auto_complete = settings.get("subclim_auto_complete", True)


def auto_complete_changed():
    global auto_complete
    auto_complete = settings.get("subclim_auto_complete", True)
settings.add_on_change("subclim_auto_complete", auto_complete_changed)


def offset_of_location(view, location):
    '''we should get utf-8 size in bytes for eclim offset'''
    text = view.substr(sublime.Region(0, location))
    cr_size = 0
    if view.line_endings() == 'Windows':
        cr_size = text.count('\n')
    return len(text.encode('utf-8')) + cr_size


# worker thread for async tasks
def worker():
    while True:
        task = tasks.get()
        try:
            task()
        except:
            import traceback
            traceback.print_exc()
        finally:
            tasks.task_done()
tasks = queue.Queue()
t = threading.Thread(target=worker)
t.daemon = True
t.start()


def flatten_command_line(lst):
    '''shallow flatten for sequences of strings'''
    return [i for sub in lst for i in ([sub] if isinstance(sub, basestring) else sub)]


class UnknownSubclimTemplateHandlerException(Exception):
    pass


class SubclimBase(object):
    def __init__(self, *args, **kwargs):
        self.template_handler = SubclimBase.DEFAULT_HANDLER.copy()

    def is_configured(self):
        return check_eclim()

    def find_view(self, view):
        if type(view) == sublime.View:
            return view
        view = getattr(self, 'view', None)
        if type(view) == sublime.View:
            return view
        window = getattr(self, 'window', None)
        if type(window) == sublime.Window:
            return window.active_view()
        return sublime.active_window().active_view()

    def get_relative_path(self, flag, view):
        return (flag, get_context(view)[1])

    def get_project(self, flag, view):
        return (flag, get_context(view)[0])

    def get_cursor(self, flag, view):
        return (flag, str(view.sel()[0].a))

    def get_selection_start(self, flag, view):
        s = view.sel()
        if len(s) == 1 and s[0].a == s[0].b:
            return (flag, '0')
        e = min([min(i.a, i.b) for i in s])
        return (flag, str(e))

    def get_selection_end(self, flag, view):
        s = view.sel()
        if len(s) == 1 and s[0].a == s[0].b:
            return (flag, str(view.layout_to_text(view.layout_extent())))
        e = max([max(i.a, i.b) for i in s])
        return (flag, str(e))

    def get_encoding(self, flag, view):
        enc = view.encoding()
        if enc == "Undefined":
            enc = "utf-8"
        return (flag, enc)

    def get_classname(self, flag, view):
        return (flag, os.path.splitext(view.file_name())[0])

    def build_template(self, template, view=None, **kwargs):
        view = self.find_view(view)
        k = template.keys()[0]
        handler = getattr(self, 'template_handler', SubclimBase.DEFAULT_HANDLER)
        cmdline = ['-command', k]
        for param in template[k]:
            scrub = param.replace('[', '').replace(']', '')
            if ' ' in scrub:
                flag, _ = scrub.split(' ', 1)
            else:
                flag = scrub
            # ignore optional parameters
            if param not in handler:
                if param.startswith('['):
                    log.warn('ignoring missing optional parameter: %s', param)
                    continue
                if flag in kwargs:
                    continue
                log.error('error finding paramter: %s', param)
                raise UnknownSubclimTemplateHandlerException(param)
            cmdline.append(handler[param](self, flag, view))
        return cmdline

    def get_additional_args(self, d):
        '''if we've been passed command line options, add them in'''
        return [((k, v) if v is not None else k) for k, v in d.items() if k.startswith('-')]

    def run_template(self, template, view=None, **kwargs):
        cmdline = self.build_template(template, view, **kwargs)
        cmdline.extend(self.get_additional_args(kwargs))
        return self.run_eclim(cmdline)

    def run_eclim(self, cmdline):
        log.info(cmdline)
        flat = flatten_command_line(cmdline)
        return eclim.call_eclim(flat)

    # each handler called with self, flag, view
    DEFAULT_HANDLER = {
        '-f file': get_relative_path,
        '-p project': get_project,
        '-o offset': get_cursor,
        '-b boffset': get_selection_start,
        '-e eoffset': get_selection_end,
        '-e encoding': get_encoding
        # '-c class' : get_classname
    }


class EclimCommand(sublime_plugin.TextCommand, SubclimBase):
    '''To be run from the python console or other nefariousness'''
    def run(self, edit, **kwargs):
        cmdline = self.get_additional_args(kwargs)
        self.run_eclim(cmdline)


def check_eclim_version():
    out = SubclimBase.run_template({"ping": []}, {})
    m = re.search(r'^eclim\s+(.*)$', out, re.MULTILINE)
    version = int("".join(m.group(1).split(".")))
    if version < 173:
        sublime.error_message("Subclim depends on Eclim 1.7.3 or higher. Please update your Eclim installation.")


def initialize_eclim_module():
    '''Loads the eclim executable path from ST2's settings and sets it
    in the eclim module'''
    s = sublime.load_settings("Subclim.sublime-settings")
    eclim_executable = s.get("eclim_executable_location", None)
    # log.debug('eclim_executable = ' + eclim_executable)
    eclim.eclim_executable = eclim_executable

# when this module is loaded (by ST2), initialize the eclim module
initialize_eclim_module()


def check_eclim(view=None):
    if not eclim.eclim_executable:
        initialize_eclim_module()
    if not eclim.eclim_executable:
        log.error("Eclim executable path not set, call the set_eclim_path command!")
        return False
    return True


def get_context(view):
    s = view.settings()
    project = s.get('subclim.project', None)
    relative_path = s.get('subclim.project_relative_path', None)
    if project is None:
        project, relative_path = eclim.get_context(view.file_name())
        if project is not None:
            s.set('subclim.project', project)
        if relative_path is not None:
            s.set('subclim.project_relative_path', relative_path)
    return project, relative_path


def get_classname(view):
    s = view.settings()
    klass = s.get('subclim.classname', None)
    if klass is None:
        # todo
        return None
    return klass


class SetEclimPath(sublime_plugin.WindowCommand):
    '''Asks the user for the path to the Eclim executable and saves it in
    ST2's prefernces'''
    def run(self):
        default_path = "/path/to/your/eclipse/eclim"
        initialize_eclim_module()
        if eclim.eclim_executable is not None:
            default_path = eclim.eclim_executable

        self.window.show_input_panel(
            "Input path to eclim executable (in your eclipse directory)",
            default_path, self.path_entered, None, None)

    def path_entered(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        s = sublime.load_settings("Subclim.sublime-settings")
        s.set("eclim_executable_location", path)
        sublime.save_settings("Subclim.sublime-settings")
        # re-initialize the eclim module with the new path
        initialize_eclim_module()


class SubclimGoBack(sublime_plugin.TextCommand):

    navigation_stack = []

    def run(self, edit, block=False):
        if len(SubclimGoBack.navigation_stack) > 0:
            self.view.window().open_file(
                SubclimGoBack.navigation_stack.pop(),
                sublime.ENCODED_POSITION)


class JavaGotoDefinition(sublime_plugin.TextCommand):
    '''Asks Eclipse for the definition location and moves ST2 there if found'''

    def run(self, edit, block=False):
        if not check_eclim(self.view):
            return
        project, file = get_context(self.view)
        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)
        locations = self.call_eclim(project, file, offset, word.size())
        locations = self.to_list(locations)

        #  one definition was found and it is in a java file -> go there
        if len(locations) == 1:
            if locations[0]['filename'].endswith("java"):
                self.go_to_location(locations[0])
                return

        # we didnt return correctly, display error in statusbar
        error_msg = "Could not find definition of %s" % self.view.substr(word)
        log.error(error_msg)

    def call_eclim(self, project, filename, offset, ident_len, shell=True):
        eclim.update_java_src(project, filename)

        go_to_cmd = ['-command', 'java_search',
                     '-n', project,
                     '-f', filename,
                     '-o', str(offset),
                     '-e', 'utf-8',
                     '-l', str(ident_len)]
        out = eclim.call_eclim(go_to_cmd)
        return out

    def to_list(self, locations):
        return json.loads(locations)

    def go_to_location(self, loc):
        # save current position
        row, col = self.view.rowcol(self.view.sel()[0].a)
        SubclimGoBack.navigation_stack.append("%s:%d:%d" % (
            self.view.file_name(), row + 1, col + 1))

        # go to new position
        f, l, c = loc['filename'], loc['line'], loc['column']
        path = "%s:%s:%s" % (f, l, c)
        sublime.active_window().open_file(path, sublime.ENCODED_POSITION)


class JavaGotoUsages(JavaGotoDefinition):
    '''Asks Eclipse for the usage locations and moves ST2 there if found'''
    def run(self, edit, block=False):
        if not check_eclim(self.view):
            return
        project, file = get_context(self.view)
        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)
        locations = self.call_eclim(project, file, offset, word.size())
        locations = self.to_list(locations)

        if len(locations) == 1:
            #  one definition was found and it is in a java file -> go there
            if locations[0]['filename'].endswith("java"):
                self.go_to_location(locations[0])
                return
        else:
            #  multiple usages -> show menu
            self.locations = locations
            self.view.window().show_quick_panel(
                [l['message'] for l in self.locations],
                self.location_selected, sublime.MONOSPACE_FONT)

    def location_selected(self, selected_idx):
        self.go_to_location(self.locations[selected_idx])

    def call_eclim(self, project, filename, offset, ident_len, shell=True):
        eclim.update_java_src(project, filename)

        go_to_cmd = ['-command', 'java_search',
                     '-n', project,
                     '-f', filename,
                     '-o', str(offset),
                     '-e', 'utf-8',
                     '-l', str(ident_len),
                     '-x', 'references']
        out = eclim.call_eclim(go_to_cmd)
        return out


class RunClass(object):
    def get_arguments(self, callback):
        s = self.view.settings()
        last_args = s.get('subclim.last_arguments', "")

        def save_and_callback(response):
            s.set('subclim.last_arguments', response)
            callback(response)

        self.view.window().show_input_panel(
            "Arguments",
            last_args, save_and_callback, None, None)

    def display_in_view(self, doc):
        window = self.view.window()
        create_view_in_same_group = False

        v = self.find_runclass_view()
        if not v:
            active_group = window.active_group()
            if not create_view_in_same_group:
                if window.num_groups() == 1:
                    window.run_command('new_pane', {'move': False})
                if active_group == 0:
                    window.focus_group(1)
                else:
                    window.focus_group(active_group-1)

            window.new_file(sublime.TRANSIENT)
            v = window.active_view()
            v.set_name("*run_output*")
            v.set_scratch(True)

        v.set_read_only(False)
        v.run_command("simple_clear_and_insert", {"insert_string": doc})
        v.set_read_only(True)
        window.focus_view(v)

    def find_runclass_view(self):
        '''
        Return view named *run_output* if exists, None otherwise.
        '''
        for w in self.view.window().views():
            if w.name() == "*run_output*":
                return w
        return None

    def call_eclim(self, project, file_name, class_name, args=""):
        eclim.update_java_src(project, file_name)
        go_to_cmd = ['-command', 'java', '-p', project, '-c', class_name, '-a'] + args.split(" ")
        out = eclim.call_eclim(go_to_cmd)
        return out


class JavaRunClass(sublime_plugin.TextCommand, RunClass):
    '''Runs the current class as Java program, good for testing
    small Java-"Scripts"'''

    def run(self, edit, block=False):
        if not check_eclim(self.view):
            return
        project, file_name = get_context(self.view)
        class_name, _ = os.path.splitext(os.path.basename(file_name))
        package_name = self.find_package_name()
        if package_name:
            class_name = package_name + "." + class_name

        def callback(args):
            self.display_in_view("Running %s with %s" % (class_name, " ".join(args)))

            def run_task():
                result = self.call_eclim(project, file_name, class_name, args)
                self.display_in_view(result)
            tasks.put(run_task)

        self.get_arguments(callback)

    def find_package_name(self):
        '''Searches the current file line by line for the
        package definition.'''
        line_regions = self.view.split_by_newlines(
            sublime.Region(0, self.view.size()))
        for line_region in line_regions:
            line = self.view.substr(line_region)
            m = re.search(r'package ([^;]*);', line)
            if m:
                return m.group(1)
        return None


class ScalaRunClass(sublime_plugin.TextCommand, RunClass):
    '''Runs the current class as Scala program, good for testing
    small Scala-"Scripts"'''

    def run(self, edit, block=False):
        if not check_eclim(self.view):
            return

        project, file_name = get_context(self.view)
        class_name = self.find_qualified_scala_name()

        def callback(args):
            self.display_in_view("Running %s with %s" % (class_name, args))

            def run_task():
                result = self.call_eclim(project, file_name, class_name, args)
                self.display_in_view(result)
            tasks.put(run_task)

        self.get_arguments(callback)

    def find_qualified_scala_name(self):
        line_regions = self.view.split_by_newlines(
            sublime.Region(0, self.view.sel()[0].a))

        for line_region in reversed(line_regions):
            line = self.view.substr(line_region)
            m = re.search(r'object ([^\s]*)', line)
            if not m:
                continue
            class_name = m.group(1)
            for line_region in line_regions:
                line = self.view.substr(line_region)
                m = re.search(r'package (.*)$', line)
                if not m:
                    return
                package_name = m.group(1)
                return package_name + "." + class_name


class CompletionProposal(object):
    def __init__(self, name, insert=None, type="None"):
        split = name.split(" ")
        self.name = "%s\t%s" % (split[0], " ".join(split[1:]))
        self.display = self.name
        if insert:
            self.insert = insert
        else:
            self.insert = name
        self.type = "None"

    def __repr__(self):
        return "CompletionProposal: %s %s" % (self.name, self.insert)


class ManualCompletionRequest(sublime_plugin.TextCommand):
    '''Used to request a full Eclim autocompletion when
    auto_complete is turned off'''
    def run(self, edit, block=False):
        JavaCompletions.user_requested = True
        self.view.run_command("save")
        self.view.run_command('auto_complete', {
                              'disable_auto_insert': True,
                              'api_completions_only': True,
                              'next_completion_if_showing': False,
                              })


class JavaCompletions(sublime_plugin.EventListener):
    '''Java/Scala completion provider'''
    # set when the just requested a manual completion, else False
    user_requested = False

    def on_query_completions(self, view, prefix, locations):
        if not (auto_complete or JavaCompletions.user_requested):
            return []
        JavaCompletions.user_requested = False

        c_func = self.complete_func(view)
        if not c_func:
            return []
        if not check_eclim(view):
            return []
        # if we haven't saved yet, push the auto complete to the main thread
        if view.is_dirty():
            sublime.set_timeout(lambda: self.queue_completions(view), 0)
            return []
        project, fn = get_context(view)
        pos = offset_of_location(view, locations[0])

        proposals = self.to_proposals(c_func(project, fn, pos))
        return [(p.display, p.insert) for p in proposals]

    def queue_completions(self, view):
        view.run_command("save")
        view.run_command('auto_complete', {
                         'disable_auto_insert': True,
                         'api_completions_only': True,
                         'next_completion_if_showing': False,
                         })

    def complete_func(self, view):
        syntax = view.settings().get("syntax")
        if "Java.tmLanguage" in syntax:
            return self.call_eclim_java
        elif "Scala.tmLanguage" in syntax:
            return self.call_eclim_scala
        else:
            return None

    def call_eclim_java(self, project, file, offset, shell=True):
        eclim.update_java_src(project, file)
        complete_cmd = "-command java_complete \
                                -p %s \
                                -f %s \
                                -o %i \
                                -e utf-8 \
                                -l compact" % (project, file, offset)
        out = eclim.call_eclim(complete_cmd)
        return out

    def call_eclim_scala(self, project, file, offset, shell=True):
        eclim.update_scala_src(project, file)
        complete_cmd = "-command scala_complete \
                                -p %s \
                                -f %s \
                                -o %i \
                                -e utf-8 \
                                -l compact" % (project, file, offset)
        out = eclim.call_eclim(complete_cmd)
        return out

    def to_proposals(self, eclim_output):
        proposals = []

        completions = json.loads(eclim_output)
        # newer versions of Eclim package the list of completions in a dict
        if isinstance(completions, dict):
            completions = completions['completions']
        for c in completions:
            if not "<br/>" in c['info']:  # no overloads
                proposals.append(CompletionProposal(c['info'], c['completion']))
            else:
                variants = c['info'].split("<br/>")
                param_lists = [re.search(r'\((.*)\)', v) for v in variants]
                param_lists = [x.group(1) for x in param_lists if x]
                props = []
                for idx, pl in enumerate(param_lists):
                    if pl:
                        params = [par.split(" ")[-1] for par in pl.split(", ")]
                        insert = ", ".join(["${%i:%s}" % (i, s)
                                            for i, s in
                                            zip(range(1, len(params) + 1), params)
                                            ])
                        insert = c['completion'] + insert + ")"
                        props.append(CompletionProposal(variants[idx], insert))
                    else:
                        props.append(CompletionProposal(variants[idx], c['completion']))
                proposals.extend(props)
        return proposals


class JavaValidation(sublime_plugin.EventListener):
    '''Show Java errors as found by Eclipse on save and load.
    Will trigger Eclipse compiles.'''

    drawType = 4 | 32
    line_messages = {}

    def __init__(self, *args, **kwargs):
        sublime_plugin.EventListener.__init__(self, *args, **kwargs)
        self.lastCount = {}

    def validation_func(self, view):
        syntax = view.settings().get("syntax")
        if "Java.tmLanguage" in syntax:
            return eclim.update_java_src
        elif "Scala.tmLanguage" in syntax:
            return eclim.update_scala_src
        else:
            return None

    def on_load(self, view):
        validation_func = self.validation_func(view)
        if validation_func:
            buf_id = view.buffer_id()

            def validation_closure():
                try:
                    v = sublime.active_window().active_view()
                except AttributeError:
                    pass
                if v.buffer_id() == buf_id:
                    self.validate(view, validation_func)

            sublime.set_timeout(validation_closure, 1500)

    def on_post_save(self, view):
        validation_func = self.validation_func(view)
        if validation_func:
            self.validate(view, validation_func)

            # sometimes, Eclipse will not report errors instantly
            # check again a bit later
            def validation_closure():
                self.validate(view, validation_func)
            sublime.set_timeout(validation_closure, 1500)

    def validate(self, view, validation_func):
        if not check_eclim(view):
            return
        project, file = get_context(view)
        problems = {}

        def async_validate_task():
            out = validation_func(project, file)
            problems.update(eclim.parse_problems(out))
            sublime.set_timeout(on_validation_finished, 0)

        def on_validation_finished():
            line_messages = JavaValidation.line_messages
            vid = view.id()
            line_messages[vid] = {}
            for e in problems['errors']:
                l_no = int(e['line'])
                if not line_messages[vid].get(l_no, None):
                    line_messages[vid][l_no] = []
                line_messages[vid][l_no].append(e)
            self.visualize(view)
            self.on_selection_modified(view)

        tasks.put(async_validate_task)

    def visualize(self, view):
        view.erase_regions('subclim-errors')
        view.erase_regions('subclim-warnings')
        lines = JavaValidation.line_messages[view.id()]

        outlines = [view.line(view.text_point(lineno - 1, 0))
                    for lineno in lines.keys()
                    if len(list(filter(lambda x: x['error'], lines[lineno]))) > 0]
        view.add_regions(
            'subclim-errors', outlines, 'keyword', 'dot', JavaValidation.drawType)

        outlines = [view.line(view.text_point(lineno - 1, 0))
                    for lineno in lines.keys()
                    if len(list(filter(lambda x: x['error'], lines[lineno]))) <= 0]
        view.add_regions(
            'subclim-warnings', outlines, 'comment', 'dot', JavaValidation.drawType)

    def on_selection_modified(self, view):
        validation_func = self.validation_func(view)
        if validation_func:
            line_messages = JavaValidation.line_messages
            vid = view.id()
            lineno = view.rowcol(view.sel()[0].end())[0] + 1
            if vid in line_messages and lineno in line_messages[vid]:
                view.set_status(
                    'subclim', '; '.join([e['message'] for e in line_messages[vid][lineno]]))
            else:
                view.erase_status('subclim')


class JavaImportClassUnderCursor(sublime_plugin.TextCommand):
    '''Will try to find a suitable class for importing using
    Eclipse's auto import features. Displays a menu if there are
    alternatives.'''

    def run(self, edit, block=False):
        if not check_eclim(self.view):
            return
        project, _file = get_context(self.view)
        pos = self.view.sel()[0]
        word = self.view.word(pos)
        offset = offset_of_location(self.view, word.a)
        self.view.run_command("save")

        class_names = []
        message = []

        def async_find_imports_task():
            import_result = self.call_eclim(project, _file, offset)
            if isinstance(import_result, list):
                class_names.extend(import_result)
            elif isinstance(import_result, dict):
                message.append(import_result['message'])
            elif isinstance(import_result, str):
                message.append(import_result)
            sublime.set_timeout(on_find_imports_finished, 0)

        def on_find_imports_finished():
            if len(message) > 0:
                log.error('\n'.join(message))
                return
            elif len(class_names) > 1:
                self.possible_imports = class_names
                self.show_import_menu()

        tasks.put(async_find_imports_task)

    def call_eclim(self, project, _file, offset):
        eclim.update_java_src(project, _file)
        complete_cmd = "-command java_import \
                                -p %s \
                                -f %s \
                                -o %i \
                                -e utf-8" % (project, _file, offset)
        result = eclim.call_eclim(complete_cmd)
        try:
            result = json.loads(result)
        except ValueError:
            pass
        return result

    def show_import_menu(self):
        self.view.window().show_quick_panel(
            self.possible_imports, self.import_selected,
            sublime.MONOSPACE_FONT)

    def import_selected(self, selected_idx):
        self.view.run_command("java_add_import_class",
                              {'class_name': self.possible_imports[selected_idx]})


class JavaAddImportClass(sublime_plugin.TextCommand):
    '''Will try to add a import statement to the current view.'''

    def run(self, edit, class_name=None):
        import_string = "import " + class_name + ";\n"
        lines = self.view.lines(sublime.Region(0, self.view.size()))
        last_import_region = sublime.Region(-1, -1)
        package_definition = sublime.Region(-1, -1)
        for l in lines:
            l_str = self.view.substr(l)
            if "{" in l_str:
                break
            if "package" in l_str:
                package_definition = l
            if "import" in l_str:
                last_import_region = l

        if last_import_region == sublime.Region(-1, -1):
            last_import_region = package_definition
            import_string = "\n" + import_string
        self.view.insert(edit, last_import_region.b + 1, import_string)


class EclipseProjects(sublime_plugin.WindowCommand):
    '''Open an eclipse project'''
    def __init__(self, *args, **kwargs):
        sublime_plugin.WindowCommand.__init__(self, *args, **kwargs)
        self.projects = {}
        self.project_paths = []

    def run(self):
        if not check_eclim(self.window.active_view()):
            return
        self.projects = {}
        self.project_paths = []
        cmd = "-command projects"
        out = eclim.call_eclim(cmd)
        ps = json.loads(out.strip())
        for p in ps:
            self.projects[p['name']] = p
            self.project_paths.append([p['name'], p['path']])
        self.window.show_quick_panel(self.project_paths, self.on_done)

    def on_done(self, idx):
        name, path = self.project_paths[idx]
        branch, leaf = os.path.split(path)
        # open in finder
        self.window.run_command("open_dir", {"dir": branch, "file": leaf})
        # none of these work.
        # self.window.open_file(path)
        # self.window.run_command("prompt_add_folder", {"dir": path} )
        # self.window.run_command("prompt_add_folder", {"file": path} )
        # self.window.run_command("prompt_add_folder", path)

########NEW FILE########
__FILENAME__ = test_sublime_logging
import logging
from subclim_logging import *
import sublime_plugin


class TestViewLogHandler(sublime_plugin.TextCommand):
    def run(self, edit):
        print 'testing status bar handler'
        self.test_viewlog()

    def test_viewlog(self):
        log = logging.getLogger('test_viewlog2')
        for h in log.handlers:
            log.removeHandler(h)
        handler = ViewLogHandler()
        handler.setLevel(logging.INFO)
        log.addHandler(handler)
        log.debug('Dont see this')
        log.error('This is an error and stuff')


class TestStatusBarLogHandler(sublime_plugin.TextCommand):
    def run(self, edit):
        print 'testing status bar handler'
        self.test_statusbar()

    def test_statusbar(self):
        log = logging.getLogger('test_statusbar')
        for h in log.handlers:
            log.removeHandler(h)
        handler = StatusBarLogHandler('test_statusbar')
        handler.setLevel(logging.ERROR)
        log.addHandler(handler)
        log.debug('Dont see this')
        log.error('This is an error and stuff')

########NEW FILE########
