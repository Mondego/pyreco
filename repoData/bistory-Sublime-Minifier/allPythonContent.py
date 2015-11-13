__FILENAME__ = basecall
import sublime
import sublime_plugin
import threading
if sublime.version() < '3':
    import urllib2
else:
    import urllib.error

class BaseCall(threading.Thread):

    def __init__(self, sel, string, timeout, level, rm_new_lines):
        self.sel = sel
        self.original = string
        self.timeout = timeout
        self.result = None
        self.level = level
        self.error = None
        self.rm_new_lines = rm_new_lines
        threading.Thread.__init__(self)

    def exec_request(self):
        return

    def run(self):
        if sublime.version() < '3':
            try:
                self.result = self.exec_request()
            except urllib2.HTTPError as e:
                self.error = True
                self.result = 'Minifier Error: HTTP error %s contacting API' % (str(e.code))
            except urllib2.URLError as e:
                self.error = True
                self.result = 'Minifier Error: ' + str(e.reason)
            except UnicodeEncodeError:
                self.error = True
                self.result = 'You can only use ASCII characters'
        else:
            try:
                self.result = self.exec_request()
            except urllib.error.HTTPError as e:
                self.error = True
                self.result = 'Minifier Error: HTTP error %s contacting API' % (str(e.code))
            except urllib.error.URLError as e:
                self.error = True
                self.result = 'Minifier Error: ' + str(e.reason)
            except UnicodeEncodeError:
                self.error = True
                self.result = 'You can only use ASCII characters'
########NEW FILE########
__FILENAME__ = cssminifiercall
import sublime
import re
if sublime.version() < '3':
    import urllib
    import urllib2
    from basecall import BaseCall
else:
    import urllib.request
    import urllib.parse
    from Minifier.compilers.basecall import BaseCall

class CssminifierCall(BaseCall):

    def exec_request(self):
        ua = 'Sublime Text - cssminifier'
        query = {
            'input': self.original }
        url = "http://cssminifier.com/raw"
        
        if sublime.version() < '3':
            data = urllib.urlencode(query)
        
            req = urllib2.Request(url, data, headers = { 'User-Agent': ua, 'Content-Type': 'application/x-www-form-urlencoded' })
            file = urllib2.urlopen(req, timeout=self.timeout)
        else:
            data = urllib.parse.urlencode(query)
            binary_data = data.encode('utf8')
        
            req = urllib.request.Request(url, binary_data, headers = { 'User-Agent': ua, 'Content-Type': 'application/x-www-form-urlencoded' })
            file = urllib.request.urlopen(req, timeout=self.timeout)

        mini_content = file.read().strip()

        if len(mini_content) > 0:
            return re.sub("[\n]+", " ", mini_content) if self.rm_new_lines else mini_content
        else:
            return None

########NEW FILE########
__FILENAME__ = googleclosurecall
import sublime
import re
if sublime.version() < '3':
    import urllib
    import urllib2
    from basecall import BaseCall
else:
    import urllib.request
    import urllib.parse
    from Minifier.compilers.basecall import BaseCall

class GoogleClosureCall(BaseCall):

    def exec_request(self):
        ua = 'Sublime Text - Google Closure'
        query = {
            'js_code': self.original.encode('utf-8'),
            'compilation_level': self.level,
            'output_info': "compiled_code" }
        url = "http://closure-compiler.appspot.com/compile"
        
        if sublime.version() < '3':
            data = urllib.urlencode(query)
        
            req = urllib2.Request(url, data, headers = { 'User-Agent': ua })
            file = urllib2.urlopen(req, timeout=self.timeout)
        else:
            data = urllib.parse.urlencode(query)
            binary_data = data.encode('utf8')
        
            req = urllib.request.Request(url, binary_data, headers = { 'User-Agent': ua })
            file = urllib.request.urlopen(req, timeout=self.timeout)

        mini_content = file.read().strip()

        if len(mini_content) > 0:
            return re.sub("[\n]+", " ", mini_content) if self.rm_new_lines else mini_content
        else:
            return None
########NEW FILE########
__FILENAME__ = reducisauruscall
import sublime
import re
if sublime.version() < '3':
    import urllib
    import urllib2
    from basecall import BaseCall
else:
    import urllib.request
    import urllib.parse
    from Minifier.compilers.basecall import BaseCall

class ReducisaurusCall(BaseCall):

    def exec_request(self):
        ua = 'Sublime Text - Reducisaurus'
        query = {
            'file': self.original }
        url = "http://reducisaurus.appspot.com/css"
        
        if sublime.version() < '3':
            data = urllib.urlencode(query)
        
            req = urllib2.Request(url, data, headers = { 'User-Agent': ua, 'Content-Type': 'application/x-www-form-urlencoded' })
            file = urllib2.urlopen(req, timeout=self.timeout)
        else:
            data = urllib.parse.urlencode(query)
            binary_data = data.encode('utf8')
        
            req = urllib.request.Request(url, binary_data, headers = { 'User-Agent': ua, 'Content-Type': 'application/x-www-form-urlencoded' })
            file = urllib.request.urlopen(req, timeout=self.timeout)

        mini_content = file.read().strip()

        if len(mini_content) > 0:
            return re.sub("[\n]+", " ", mini_content) if self.rm_new_lines else mini_content
        else:
            return None
########NEW FILE########
__FILENAME__ = uglifycall
import sublime
import re
if sublime.version() < '3':
    import urllib
    import urllib2
    from basecall import BaseCall
else:
    import urllib.request
    import urllib.parse
    from Minifier.compilers.basecall import BaseCall

class UglifyCall(BaseCall):

    def exec_request(self):
        ua = 'Sublime Text - Uglify'
        query = {
            'js_code': self.original.encode('utf-8') }
        url = "http://marijnhaverbeke.nl/uglifyjs"
        
        if sublime.version() < '3':
            data = urllib.urlencode(query)
        
            req = urllib2.Request(url, data, headers = { 'User-Agent': ua })
            file = urllib2.urlopen(req, timeout=self.timeout)
        else:
            data = urllib.parse.urlencode(query)
            binary_data = data.encode('utf8')
        
            req = urllib.request.Request(url, binary_data, headers = { 'User-Agent': ua })
            file = urllib.request.urlopen(req, timeout=self.timeout)

        mini_content = file.read().strip()

        if len(mini_content) > 0:
            return re.sub("[\n]+", " ", mini_content) if self.rm_new_lines else mini_content
        else:
            return None
########NEW FILE########
__FILENAME__ = Minify
from os import path

import sublime
import sublime_plugin

if sublime.version() < '3':
    from compilers import GoogleClosureCall, UglifyCall, ReducisaurusCall, CssminifierCall
else:
    from Minifier.compilers import GoogleClosureCall, UglifyCall, ReducisaurusCall, CssminifierCall

class BaseMinifier(sublime_plugin.TextCommand):
    '''Base Minifier'''

    def __init__(self, view):
        self.view = view
        self.window = sublime.active_window()
        self.settings = sublime.load_settings('Minifier.sublime-settings')

    def run(self, edit):

        selections = self.get_selections()
        CompilerCall = self.get_minifier()

        if CompilerCall is None:
            sublime.error_message('Please focus on the file you wish to minify.')
        else:
            threads = []
            for sel in selections:
                selbody = self.view.substr(sel)

                thread = CompilerCall(
                            sel,
                            selbody,
                            timeout=self.settings.get('timeout', 5),
                            level=self.settings.get('optimization_level', 'WHITESPACE_ONLY'),
                            rm_new_lines=self.settings.get('remove_new_lines', False))

                threads.append(thread)
                thread.start()
            
            # Wait for threads
            for thread in threads:
                thread.join()

            selections.clear()
            self.handle_threads(edit, threads, selections, offset=0, i=0, dir=1)

    def get_selections(self):
        selections = self.view.sel()

        # check if the user has any actual selections
        has_selections = False
        for sel in selections:
            if sel.empty() == False:
                has_selections = True

        # if not, add the entire file as a selection
        if not has_selections:
            full_region = sublime.Region(0, self.view.size())
            selections.add(full_region)

        return selections

    def handle_threads(self, edit, threads, selections, offset = 0, i = 0, dir = 1):

        next_threads = []
        for thread in threads:
            if thread.is_alive():
                next_threads.append(thread)
                continue
            if thread.result == False:
                continue
            self.handle_result(edit, thread, selections, offset)
        threads = next_threads

        if len(threads):
            before = i % 8
            after = (7) - before

            dir = -1 if not after else dir
            dir = 1 if not before else dir

            i += dir

            self.view.set_status('minify', '[%s=%s]' % (' ' * before, ' ' * after))

            sublime.set_timeout(lambda: self.handle_threads(edit, threads, selections, offset, i, dir), 100)
            return

        self.view.erase_status('minify')
        sublime.status_message('Successfully minified')

    def handle_result(self, edit, thread, selections, offset):
        sel = thread.sel
        original = thread.original
        result = thread.result

        if thread.error is True:
            sublime.error_message(result)
            return
        elif result is None:
            sublime.error_message('There was an error minifying the file.')
            return

        return thread

    def get_minifier(self):
        current_file = self.view.file_name()

        if current_file is None:
            return None
        else:
            file_parts = path.splitext(current_file)

            if file_parts[1] == '.js':
                compiler = self.settings.get('compiler', 'google_closure')
                compilers = {
                    'google_closure': GoogleClosureCall,
                    'uglify_js': UglifyCall
                }

                return compilers[compiler] if compiler in compilers else compilers['google_closure']
            elif file_parts[1] == '.css':
                compiler = self.settings.get('css_compiler', 'cssminifier')
                compilers = {
                    'reducisaurus': ReducisaurusCall,
                    'cssminifier': CssminifierCall
                }
                return compilers[compiler] if compiler in compilers else compilers['cssminifier']

    def get_new_line(self):
        CR = chr(0x0D)
        LF = chr(0x0A)
        endtypes = {'u': LF, 'w': CR+LF, 'm': CR}
        return endtypes[self.view.line_endings()[0].lower()]


class Minify(BaseMinifier):

    def handle_result(self, edit, thread, selections, offset):
        result = super(Minify, self).handle_result(edit, thread, selections, offset)

        if thread.error is None:
            if sublime.version() < '3':
                editgroup = self.view.begin_edit('minify')

            sel = thread.sel
            result = thread.result
            if offset:
                sel = sublime.Region(thread.sel.begin() + offset, thread.sel.end() + offset)

            if sublime.version() < '3':
                self.view.replace(edit, sel, result)
            else:
                self.view.replace(edit, sel, result.decode("utf-8"))

            if sublime.version() < '3':
                self.view.end_edit(edit)

class MinifyToFile(BaseMinifier):

    def run(self, edit):

        self.selections_completed = 0
        self.output = ""
        self.total_selections = len(self.get_selections())

        super(MinifyToFile, self).run(edit)

    def handle_result(self, edit, thread, selections, offset):

        self.selections_completed += 1

        super(MinifyToFile, self).handle_result(edit, thread, selections, offset)

        if thread.error is None:
            if sublime.version() < '3':
                self.output = self.output + self.get_new_line() + thread.result
            else:
                self.output = self.output + self.get_new_line() + thread.result.decode('utf-8')

            # test if all the selections have been minified. if so, write all the output to the new file
            if self.selections_completed is self.total_selections:

                current_file = self.view.file_name()

                file_parts = path.splitext(current_file)
                min_file_suffix = self.settings.get('min_file_suffix', '.min')

                file_name = file_parts[0] + min_file_suffix + file_parts[1]

                file_path = path.join(
                    path.dirname(current_file),
                    file_name
                )

                if sublime.version() < '3':
                    with open(file_path, 'w+', 0) as min_file:
                        min_file.write(self.output.strip())
                else:
                    with open(file_path, 'wb+', 0) as min_file:
                        min_file.write(bytes(self.output.strip(),'utf-8'))

                print (self.settings.get('open_on_min', True))
                if (self.settings.get('open_on_min', True) == True):
                    self.window.open_file(file_name)
########NEW FILE########
