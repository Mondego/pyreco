__FILENAME__ = autofilename
import sublime
import sublime_plugin
import os
from getimageinfo import getImageInfo

class InsertDimensionsCommand(sublime_plugin.TextCommand):
    this_dir = ''

    def insert_dimension(self,edit,dim,name,tag_scope):
        view = self.view
        sel = view.sel()[0].a
        if name in view.substr(tag_scope):
            reg = view.find('(?<='+name+'\=)\s*\"\d{1,5}', tag_scope.a)
            view.replace(edit, reg, '"'+str(dim))
        else:
            dimension = str(dim)
            view.insert(edit, sel+1, ' '+name+'="'+dimension+'"')

    def get_setting(self,string,view=None):
        if view and view.settings().get(string):
            return view.settings().get(string)
        else:
            return sublime.load_settings('autofilename.sublime-settings').get(string)

    def run(self, edit):
        view = self.view
        view.run_command("commit_completion")
        sel = view.sel()[0].a
        if not 'html' in view.scope_name(sel): return
        scope = view.extract_scope(sel-1)
        tag_scope = view.extract_scope(scope.a-1)

        path = view.substr(scope)
        if path.startswith(("'","\"","(")):
            path = path[1:-1]

        path = path[path.rfind('/'):] if '/' in path else ''
        full_path = self.this_dir + path

        if '<img' in view.substr(tag_scope) and path.endswith(('.png','.jpg','.jpeg','.gif')):
            with open(full_path,'rb') as r:
                read_data = r.read() if path.endswith(('.jpg','.jpeg')) else r.read(24)
            con_type, w, h = getImageInfo(read_data)
            if self.get_setting('afn_insert_width_first',view):
                self.insert_dimension(edit,h,'height',tag_scope)
                self.insert_dimension(edit,w,'width',tag_scope)
            else:
                self.insert_dimension(edit,w,'width',tag_scope)
                self.insert_dimension(edit,h,'height',tag_scope)

class ReloadAutoCompleteCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        view = self.view
        view.run_command('hide_auto_complete')
        view.run_command('left_delete')
        sel = view.sel()[0].a

        scope = view.extract_scope(sel-1)
        scope_text = view.substr(scope)
        slash_pos = scope_text[:sel - scope.a].rfind('/')
        slash_pos += 1 if slash_pos < 0 else 0

        region = sublime.Region(scope.a+slash_pos+1,sel)
        view.sel().add(region)

class FileNameComplete(sublime_plugin.EventListener):
    def on_activated(self,view):
        self.size = view.size()

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "afn_insert_dimensions":
            return self.get_setting('afn_insert_dimensions',view) == operand
        if key == "afn_deleting_slash":
            sel = view.sel()[0]
            valid = self.at_path_end(view) and sel.empty() and view.substr(sel.a-1) == '/'
            return valid == operand

    def at_path_end(self,view):
        sel = view.sel()[0]
        name = view.scope_name(sel.a)
        if sel.empty() and 'string.end' in name:
            return True
        if '.css' in name and view.substr(sel.a) == ')':
            return True
        return False

    def on_selection_modified(self,view):
        if not view.window():
            return
        sel = view.sel()[0]
        if sel.empty() and self.at_path_end(view):
            if view.substr(sel.a-1) == '/' or len(view.extract_scope(sel.a)) < 3:
                view.run_command('auto_complete',
                {'disable_auto_insert': True,
                'next_completion_if_showing': False})

    def fix_dir(self,sdir,fn):
        if fn.endswith(('.png','.jpg','.jpeg','.gif')):
            path = os.path.join(sdir, fn)
            with open(path,'rb') as r:
                read_data = r.read() if path.endswith(('.jpg','.jpeg')) else r.read(24)
            con_type, w, h = getImageInfo(read_data)
            return fn+'\t'+'w:'+ str(w) +" h:" + str(h)
        return fn

    def get_cur_path(self,view,sel):
        scope_contents = view.substr(view.extract_scope(sel-1))
        cur_path = scope_contents.replace('\r\n', '\n').split('\n')[0]
        if cur_path.startswith(("'","\"","(")):
            cur_path = cur_path[1:-1]

        return cur_path[:cur_path.rfind('/')+1] if '/' in cur_path else ''

    def get_setting(self,string,view=None):
        if view and view.settings().get(string):
            return view.settings().get(string)
        else:
            return sublime.load_settings('autofilename.sublime-settings').get(string)

    def on_query_completions(self, view, prefix, locations):
        is_proj_rel = self.get_setting('afn_use_project_root',view)
        valid_scopes = self.get_setting('afn_valid_scopes',view)
        sel = view.sel()[0].a
        completions = []
        
        if "string.regexp.js" in view.scope_name(sel):
            return []

        if not any(s in view.scope_name(sel) for s in valid_scopes):
            return []

        cur_path = self.get_cur_path(view, sel)

        if is_proj_rel:
            this_dir = self.get_setting('afn_proj_root',view)
            if len(this_dir) < 2:
                for f in sublime.active_window().folders():
                    if f in view.file_name():
                        this_dir = f
        else:
            if not view.file_name():
                return
            this_dir = os.path.split(view.file_name())[0]

        this_dir = os.path.join(this_dir, cur_path)

        try:
            dir_files = os.listdir(this_dir)

            for d in dir_files:
                n = d.decode('utf-8')
                if n.startswith('.'): continue
                if not '.' in n: n += '/'
                completions.append((self.fix_dir(this_dir,n), n))
            if completions:
                InsertDimensionsCommand.this_dir = this_dir
            return completions
        except OSError:
            print "AutoFileName: could not find " + this_dir
            return

########NEW FILE########
__FILENAME__ = getimageinfo
import StringIO
import struct

def getImageInfo(data):
    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''

    # handle GIFs
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack("<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif (size >= 2) and data.startswith('\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO.StringIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read(1)
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass

    return content_type, width, height
########NEW FILE########
