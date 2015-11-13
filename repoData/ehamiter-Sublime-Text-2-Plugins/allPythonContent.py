__FILENAME__ = blame
import os
import sublime
import sublime_plugin

class BlameCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if len(self.view.file_name()) > 0:  
            folder_name, file_name = os.path.split(self.view.file_name())
            begin_line, begin_column = self.view.rowcol(self.view.sel()[0].begin())
            end_line, end_column = self.view.rowcol(self.view.sel()[0].end())
            begin_line = str(begin_line)
            end_line = str(end_line)
            lines = begin_line + ',' + end_line
            self.view.window().run_command('exec', {'cmd': ['git', 'blame', '-L', lines, file_name], 'working_dir': folder_name})         
            sublime.status_message("git blame -L " + lines + " " + file_name)

    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0

########NEW FILE########
__FILENAME__ = generate_uuid
import sublime_plugin
import uuid


class GenerateUuidCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        u = str(uuid.uuid4())
        for r in self.view.sel():
            self.view.replace(edit, r, u)

########NEW FILE########
__FILENAME__ = googleIt
import sublime
import sublime_plugin
import webbrowser


class googleItCommand(sublime_plugin.TextCommand):

    """
    This will search a word or a selection coupled with the file's
    scope. Default binding recommendation: "ctrl + alt + forward_slash"
    """

    def run(self, edit):
        if len(self.view.file_name()) > 0:
            word = self.view.substr(self.view.word(self.view.sel()[0].begin()))
            scope = self.view.scope_name(self.view.sel()[0].begin()).strip()
            getlang = scope.split('.')
            language = getlang[-1]
            sublime.status_message('googleIt invoked-- ' + 'Scope: ' + scope + \
                ' Word: ' + word + ' Language: ' + language)
            for region in self.view.sel():
                phrase = self.view.substr(region)
                search = 'http://google.com/search?q='
                # Feeling lucky? Use 'http://google.com/search?btnI=1&q=' instead
                if not region.empty():
                    webbrowser.open_new_tab(search + phrase + " " + language)
                else:
                    webbrowser.open_new_tab(search + word + " " + language)
        else:
            pass

    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0

########NEW FILE########
__FILENAME__ = local_validate
import sublime_plugin

class LocalValidateCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        full_link = "x-validator-sac://open?uri=%s" % self.view.file_name()
        self.view.window().run_command('open_url', {"url": full_link})

########NEW FILE########
__FILENAME__ = pep8check
import os
import sublime
import sublime_plugin


class Pep8CheckCommand(sublime_plugin.TextCommand):

    """This will invoke PEP8 checking on the given file.
    pep8.py must be in your system's path for this to work.

    http://pypi.python.org/pypi/pep8

    Options:
    --version            show program's version number and exit
    --help               show this help message and exit
    --verbose            print status messages, or debug with -vv
    --quiet              report only file names, or nothing with -qq
    --repeat             show all occurrences of the same error
    --exclude=patterns   exclude files or directories which match these comma
                         separated patterns (default: .svn,CVS,.bzr,.hg,.git)
    --filename=patterns  when parsing directories, only check filenames
                       matching these comma separated patterns (default: *.py)
    --select=errors      select errors and warnings (e.g. E,W6)
    --ignore=errors      skip errors and warnings (e.g. E4,W)
    --show-source        show source code for each error
    --show-pep8          show text of PEP 8 for each error
    --statistics         count errors and warnings
    --count              print total number of errors and warnings to standard
                       error and set exit code to 1 if total is not null
    --benchmark          measure processing speed
    --testsuite=dir      run regression tests from dir
    --doctest            run doctest on myself
    """

    def run(self, edit):
        if self.view.file_name().endswith('.py'):
            folder_name, file_name = os.path.split(self.view.file_name())
            self.view.window().run_command('exec', {'cmd': ['pep8',         \
                '--repeat', '--verbose', '--ignore=E501', '--show-source',  \
                '--statistics', '--count',                                  \
                 file_name], 'working_dir': folder_name})
            sublime.status_message("pep8 " + file_name)

    def is_enabled(self):
        return self.view.file_name().endswith('.py')

########NEW FILE########
__FILENAME__ = settings_refresh
import sublime
import sublime_plugin


class SettingsRefreshCommand(sublime_plugin.TextCommand):
    '''This will allow you to refresh your settings. Handy 
    for editing color schemes and seeing the changes quickly.
    '''

    def run(self, edit):
        if not self.view.file_name():
            return

        sublime.save_settings("Base File.sublime-settings")
        sublime.status_message('Settings refreshed.')

    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0

########NEW FILE########
__FILENAME__ = speak_to_me
import os
import sublime_plugin


class SpeakToMeCommand(sublime_plugin.TextCommand):
    '''Select some text, activate, and hear it read back to you.
    If you don't select anything, the file's contents will be read.
    '''

    voice = "alex"  # (OS X 10.6 default voice)

    ## More voice choices below:

    ## Female Voices            ## Male Voices
    # Agnes                     # Alex
    # Kathy                     # Bruce
    # Princess                  # Fred
    # Vicki                     # Junior
    # Victoria                  # Ralph

    ## Lion has many new voices-- if you have it, check them out here:
    ## http://goo.gl/iXCIY

    def run(self, edit):
        if not self.view.file_name():
            return

        full_name = self.view.file_name()
        folder_name, file_name = os.path.split(full_name)

        for region in self.view.sel():
            phrase = self.view.substr(region)
            if not region.empty():
                self.view.window().run_command('exec', {'cmd': ['say', '-v', 
                    self.voice, phrase,], 'working_dir': folder_name})         
            else:
                self.view.window().run_command('exec', {'cmd': ['say', '-v', 
                    self.voice, '-f', file_name,], 'working_dir': folder_name})         

    def is_enabled(self):
        return self.view.file_name() and len(self.view.file_name()) > 0

########NEW FILE########
