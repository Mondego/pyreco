__FILENAME__ = html_completions
import sublime, sublime_plugin
import re

def match(rex, str):
    m = rex.match(str)
    if m:
        return m.group(0)
    else:
        return None

# This responds to on_query_completions, but conceptually it's expanding
# expressions, rather than completing words.
#
# It expands these simple expressions:
# tag.class
# tag#id
class HtmlCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # Only trigger within HTML
        if not view.match_selector(locations[0],
                "text.html - source - meta.tag, punctuation.definition.tag.begin"):
            return []

        # Get the contents of each line, from the beginning of the line to
        # each point
        lines = [view.substr(sublime.Region(view.line(l).a, l))
            for l in locations]

        # Reverse the contents of each line, to simulate having the regex
        # match backwards
        lines = [l[::-1] for l in lines]

        # Check the first location looks like an expression
        rex = re.compile("([\w-]+)([.#])(\w+)")
        expr = match(rex, lines[0])
        if not expr:
            return []

        # Ensure that all other lines have identical expressions
        for i in xrange(1, len(lines)):
            ex = match(rex, lines[i])
            if ex != expr:
                return []

        # Return the completions
        arg, op, tag = rex.match(expr).groups()

        arg = arg[::-1]
        tag = tag[::-1]
        expr = expr[::-1]

        if op == '.':
            snippet = "<{0} class=\"{1}\">$1</{0}>$0".format(tag, arg)
        else:
            snippet = "<{0} id=\"{1}\">$1</{0}>$0".format(tag, arg)

        return [(expr, snippet)]


# Provide completions that match just after typing an opening angle bracket
class TagCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # Only trigger within HTML
        if not view.match_selector(locations[0],
                "text.html -source -meta.tag, punctuation.definition.tag.begin"):
            return []

        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))
        if ch != '<':
            return []

        return ([
            ("a\tTag", "a href=\"$1\">$2</a>"),
            ("abbr\tTag", "abbr>$1</abbr>"),
            ("acronym\tRemoved", "acronym>$1</acronym>"),
            ("address\tTag", "address>$1</address>"),
            ("applet\tRemoved", "applet>$1</applet>"),
            ("area\tTag", "area>$1</area>"),
            ("article\tHTML5", "article>$1</article>"),
            ("aside\tHTML5", "aside>$1</aside>"),
            ("audio\tHTML5", "audio>$1</audio>"),
            ("b\tTag", "b>$1</b>"),
            ("base\tTag", "base href=\"$1\">"),
            ("big\tRemoved", "big>$1</big>"),
            ("blockquote\tTag", "blockquote>$1</blockquote>"),
            ("body\tTag", "body>$1</body>"),
            ("br\tTag", "br>"),
            ("button\tTag", "button>$1</button>"),
            ("canvas\tHTML5", "canvas width=\"$1\" height=\"$2\">${3:Browser does not support 'canvas' tag.}</canvas>"),
            ("caption\tTag", "caption>$1</caption>"),
            ("cdata\tTag", "cdata>$1</cdata>"),
            ("center\tRemoved", "center>$1</center>"),
            ("cite\tTag", "cite>$1</cite>"),
            ("code\tTag", "code>$1</code>"),
            ("col\tTag", "col>$1</col>"),
            ("colgroup\tTag", "colgroup>$1</colgroup>"),
            ("command\tHTML5", "command>$1</command>"),
            ("datalist\tHTML5", "datalist>$1</datalist>"),
            ("dd\tTag", "dd>$1</dd>"),
            ("del\tTag", "del>$1</del>"),
            ("details\tHTML5", "details>$1</details>"),
            ("dfn\tTag", "dfn>$1</dfn>"),
            ("div\tTag", "div>$1</div>"),
            ("dl\tTag", "dl>$1</dl>"),
            ("dt\tTag", "dt>$1</dt>"),
            ("em\tTag", "em>$1</em>"),
            ("embed\tTag", "embed>"),
            ("fieldset\tTag", "fieldset>$1</fieldset>"),
            ("figure\tHTML5", "figure>$1</figure>"),
            ("font\tRemoved", "font>$1</font>"),
            ("footer\tHTML5", "footer>$1</footer>"),
            ("form\tTag", "form action=\"$1\" method=\"${2:Get/Post}${2/(g$)|(p$)|.*/?1:et:?2:ost/i}\">$3</form>"),
            ("frame\tRemoved", "frame>$1</frame>"),
            ("frameset\tRemoved", "frameset>$1</frameset>"),
            ("h1\tTag", "h1>$1</h1>"),
            ("h2\tTag", "h2>$1</h2>"),
            ("h3\tTag", "h3>$1</h3>"),
            ("h4\tTag", "h4>$1</h4>"),
            ("h5\tTag", "h5>$1</h5>"),
            ("h6\tTag", "h6>$1</h6>"),
            ("head\tTag", "head>$1</head>"),
            ("header\tHTML5", "header>$1</header>"),
            ("hgroup\tHTML5", "hgroup>$1</hgroup>"),
            ("hr\tTag", "hr>"),
            ("html\tTag", "html>$1</html>"),
            ("i\tTag", "i>$1</i>"),
            ("iframe\tTag", "iframe src=\"$1\"></iframe>"),
            ("img\tTag", "img src=\"$1\">"),
            ("input\tTag", "input type=\"$1${1/(b$)|(co$)|(c$)|(dat$)|(da$)|(d$)|(e$)|(f$)|(h$)|(i$)|(m$)|(n$)|(p$)|(ra$)|(r$)|(su$)|(se$)|(s$)|(te$)|(ti$)|(t$)|(u$)|(w$)|.*/?1:utton:?2:lor:?3:heckbox:?4:etime-local:?5:tetime:?6:ate:?7:mail:?8:ile:?9:idden:?10:mage:?11:onth:?12:umber:?13:assword:?14:nge:?15:adio:?16:bmit:?17:arch:?18:elect:?19:xtarea:?20:me:?21:ext:?22:rl:?23:eek/i}\">"),
            ("ins\tTag", "ins>$1</ins>"),
            ("kbd\tTag", "kbd>$1</kbd>"),
            ("keygen\tHTML5", "keygen>$1</keygen>"),
            ("label\tTag", "label>$1</label>"),
            ("legend\tTag", "legend>$1</legend>"),
            ("li\tTag", "li>$1</li>"),
            ("link\tTag", "link rel=\"stylesheet\" type=\"text/css\" href=\"$1\">"),
            ("map\tTag", "map>$1</map>"),
            ("mark\tHTML5", "mark>$1</mark>"),
            ("meta\tTag", "meta>"),
            ("meter\tHTML5", "meter>$1</meter>"),
            ("nav\tHTML5", "nav>$1</nav>"),
            ("noframes\tRemoved", "noframes>$1</noframes>"),
            ("object\tTag", "object>$1</object>"),
            ("ol\tTag", "ol>$1</ol>"),
            ("optgroup\tTag", "optgroup>$1</optgroup>"),
            ("option\tTag", "option>$1</option>"),
            ("output\tHTML5", "output>$1</output>"),
            ("p\tTag", "p>$1</p>"),
            ("param\tTag", "param name=\"$1\" value=\"$2\">"),
            ("pre\tTag", "pre>$1</pre>"),
            ("progress\tHTML5", "progress>$1</progress>"),
            ("ruby\tHTML5", "ruby>$1</ruby>"),
            ("samp\tTag", "samp>$1</samp>"),
            ("script\tTag", "script type=\"${1:text/javascript}\">$2</script>"),
            ("section\tHTML5", "section>$1</section>"),
            ("select\tTag", "select>$1</select>"),
            ("small\tTag", "small>$1</small>"),
            ("span\tTag", "span>$1</span>"),
            ("strong\tTag", "strong>$1</strong>"),
            ("style\tTag", "style type=\"${1:text/css}\">$2</style>"),
            ("sub\tTag", "sub>$1</sub>"),
            ("summary\tHTML5", "summary>$1</summary>"),
            ("sup\tTag", "sup>$1</sup>"),
            ("table\tTag", "table>$1</table>"),
            ("tbody\tTag", "tbody>$1</tbody>"),
            ("td\tTag", "td>$1</td>"),
            ("textarea\tTag", "textarea>$1</textarea>"),
            ("tfoot\tTag", "tfoot>$1</tfoot>"),
            ("th\tTag", "th>$1</th>"),
            ("thead\tTag", "thead>$1</thead>"),
            ("time\tHTML5", "time>$1</time>"),
            ("title\tTag", "title>$1</title>"),
            ("tr\tTag", "tr>$1</tr>"),
            ("tt\tRemoved", "tt>$1</tt>"),
            ("u\tRemoved", "u>$1</u>"),
            ("ul\tTag", "ul>$1</ul>"),
            ("var\tTag", "var>$1</var>"),
            ("video\tTag", "video>$1</video>"),
            ("wbr\tHTML5", "wbr>$1</wbr>")
        ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

########NEW FILE########
__FILENAME__ = LanguageHelp
import sublime, sublime_plugin
import subprocess

# Will open a .chm help file for the function under the cursor (Windows only). The same 
# key-binding can be used (currently for PHP, JavaScript and jQuery) because the command 
# will determine the current syntax.
# Only for standard functions (currently) - not classes/methods, etc.
# You will need to obtain/download a .chm for each language and modify the path in the 
# code that follows.
# 
#     { "keys": ["ctrl+f1"], "command": "language_help" },
# The file hh.exe (or a more recent alternative) needs to be available on your Windows 
# environment-path(s).

# Requires the file 'PyHelp.py' for Python help - which doesn't use a .chm and displays 
# in an output panel. (Edit this file as indicated if this file is not available or required).
PHP_HELP = \
"""hh.exe mk:@MSITStore:C:\\Windows\\Help\\php_enhanced_en.chm::/res/function.%(func)s.html"""
JS_HELP = \
"""hh.exe mk:@MSITStore:C:\\Windows\\Help\\javascript.chm::/jsref_%(func)s.htm"""
jQuery_HELP = \
"""hh.exe mk:@MSITStore:C:\Windows\Help\jQuery-UI-Reference-1.7.chm::/api/%(func)s.htm"""

class LanguageHelpCommand(sublime_plugin.TextCommand):
    proc1 = None
    def run(self, edit):
        curr_view = self.view
        curr_sel = curr_view.sel()[0]
        if curr_view.match_selector(curr_sel.begin(), 'source.php'):
            source = 'PHP'
        elif curr_view.match_selector(curr_sel.begin(), 'source.js.jquery'):
            source = 'JQUERY'
        elif curr_view.match_selector(curr_sel.begin(), 'source.js'):
            source = 'JS'
        # Delete the following 3 lines if the file 'PyHelp.py' is not available:
        elif curr_view.match_selector(curr_sel.begin(), 'source.python'):
            self.view.run_command("py_help")
            return
        else:
            return

        word_end = curr_sel.end()
        if curr_sel.empty():
            word = curr_view.substr(curr_view.word(word_end)).lower()
        else:
            word = curr_view.substr(curr_sel).lower()
        if word is None or len(word) <= 1:
            sublime.status_message('No function selected')
            return
        if source == 'PHP':
            word = word.replace('_', '-')
            HELP = PHP_HELP % { "func": word }
        elif source == 'JQUERY':
            HELP = jQuery_HELP % { "func": word }
        elif source == 'JS':
            HELP = JS_HELP % { "func": word }
        try:
            if self.proc1 is not None:
                self.proc1.kill()
        except Exception:
            pass
        self.proc1 = subprocess.Popen(HELP, shell=False)
########NEW FILE########
__FILENAME__ = PyHelp
import sublime, sublime_plugin
# Works for standard functions and methods.
# Assign a key-binding such as Shift-F1.
# Click into a function or method and press Shift-F1.
# Help will be displayed in an output panel.
# Un-commment the timeout if you wish the panel to disappear after an interval.
class PyHelpCommand(sublime_plugin.TextCommand):
    py_types = (None, 'complex', 'dict', 'file', 'float', 'frozenset',
        'int', 'list', 'long', 'set', 'str', 'tuple', 'unicode', 'xrange',
        'bytearray', 'buffer', 'memoryview', '__builtins__', 'object')
    def run(self, edit):
        curr_view = self.view
        if not curr_view.match_selector(0, 'source.python'): return
        word_end = curr_view.sel()[0].end()
        if curr_view.sel()[0].empty():
            word = curr_view.substr(curr_view.word(word_end)).lower()
        else:
            word = curr_view.substr(curr_view.sel()[0]).lower()
        if word is None or len(word) <= 1:
            sublime.status_message('No word selected')
            return

        libs = curr_view.find_all('^((?:from|import).*$)')
        for lib in libs:
            try:
                exec(curr_view.substr(lib))
            except Exception:
                pass
                
        for obj in PyHelpCommand.py_types:
            try:
                if obj is None:
                    help_text = eval(word + '.__doc__')
                else:
                    help_text = eval(obj + '.' + word + '.__doc__')
                if help_text is not None:
                    self.display_help(help_text)
                    return
            except:
                pass
        line_region = curr_view.line(word_end)
        line_begin = line_region.begin()
        context = curr_view.find('[a-z_0-9\.\(\)]*' + word, line_begin, sublime.IGNORECASE)
        found_txt = curr_view.substr(context)
        try:
            help_text = eval(found_txt + '.__doc__')
        except Exception:
            help_text = None
        if help_text is not None:
            self.display_help(help_text)
        else:
            sublime.status_message('No help available')

    def display_help(self, help_text):
        win = sublime.active_window()
        the_output = win.get_output_panel('help_panel')
        the_output.set_read_only(False)
        edit = the_output.begin_edit()
        the_output.insert(edit, the_output.size(), help_text)
        the_output.end_edit(edit)
        the_output.set_read_only(True)
        win.run_command("show_panel", {"panel": "output." + "help_panel"})
        # sublime.set_timeout(self.hide_help, 5000)

    def hide_help(self):
        sublime.active_window().run_command("hide_panel", {"panel": "output." + "help_panel"})
########NEW FILE########
__FILENAME__ = OrderedFiles
import sublime_plugin
from os import path
from operator import itemgetter
from datetime import datetime

# Lists open files in a quick panel for jumping to, 
# ordered alphabetically or by modified date: index, 0, for alphabetical.
#    { "keys": ["ctrl+alt+x"], "command": "ordered_files", "args": { "index": 0 }  },
#    { "keys": ["ctrl+alt+c"], "command": "ordered_files", "args": { "index": 2 }  },
# Does not work with different groups, windows, or unsaved views (although it could 
# be modified so that it does).

class OrderedFilesCommand(sublime_plugin.WindowCommand):
	def run(self, index):
		OF = OrderedFilesCommand
		OF.file_views = []
		win = self.window
		for vw in win.views():
			if vw.file_name() is not None:
				_, tail = path.split(vw.file_name())
				modified = path.getmtime(vw.file_name())
				OF.file_views.append((tail, vw, modified))
			else:
				pass		# leave new/untitled files (for the moment)
		if index == 0:		# sort by file name (case-insensitive)
			OF.file_views.sort(key = lambda (tail, _, Doh): tail.lower())
			win.show_quick_panel([x for (x, y, z) in OF.file_views], self.on_chosen)
		else:				# sort by modified date (index == 2)
			OF.file_views.sort(key = itemgetter(2))
			win.show_quick_panel([
				(datetime.fromtimestamp(z)).strftime("%d-%m-%y %H:%M ") + x \
				for (x, y, z) in OF.file_views], self.on_chosen)
	def on_chosen(self, index):
		if index != -1:
			self.window.focus_view(OrderedFilesCommand.file_views[index][1])
########NEW FILE########
__FILENAME__ = PythonCompletions
import sublime, sublime_plugin

py_funcs = [
	("__import__()\t__import__ fn", 
		"__import__(${1:name}${2:[, globals, locals, fromlist, level]})$0"),
	("abs()\tabs fn", "abs(${1:number})$0"),
	("all()\tall fn", "all(${1:iterable})$0"),
	("any()\tany fn", "any(${1:iterable})$0"),
	("bin()\tbin fn", "bin(${1:integer})$0"),
	("bool()\tbool fn", "bool(${1:[value]})$0"),
	("bytearray()\tbytearray fn", 
		"bytearray(${1:${2:source}${3:[, encoding]}${4:[, errors]}})$0"),
	("callable()\tcallable fn", "callable(${1:object})$0"),
	("chr()\tchr fn", "chr(${1:integer})$0"),
	("classmethod()\tclassmethod fn", "classmethod(${1:function})$0"),
	("cmp()\tcmp fn", "cmp(${1:x}, ${2:y})$0"),
	("compile()\tcompile fn",
		"compile(${1:source}, ${2:filename}, ${3:mode}${4:[, flags]}${5:[, dont_inherit]})$0"),
	("complex()\tcomplex fn", "complex(${1:real}${2:[, imag]})$0"),
	("delattr()\tdelattr fn", "delattr(${1:object}, ${2:name})$0"),
	("dict()\tdict fn/ctor", "dict(${1:arg})$0"),
	("dir()\tdir fn", "dir(${1:[object]})$0"),
	("divmod()\tdivmod fn", "divmod(${1:a}, ${2:b})$0"),
	("enumerate()\tenumerate fn", "enumerate(${1:sequence}${2:[, start]})$0"),
	("eval()\teval fn", "eval(${1:expression}${2:[, globals]}${3:[, locals]})$0"),
	("execfile()\texecfile fn", "execfile(${1:filename}${2:[, globals]}${3:[, locals]})$0"),
	("file()\tfile fn", "file(${1:filename}${2:[, mode]}${3:[, bufsize]})$0"),
	("filter()\tfilter fn", "filter(${1:function}, ${2:iterable})$0"),
	("float()\tfloat fn/ctor", "float(${1:[x]})$0"),
	("format()\tformat fn", "format(${1:value}${2:[, format_spec]})$0"),
	("frozenset()\tfrozenset fn/ctor", "frozenset(${1:[iterable]})$0"),
	("getattr()\tgetattr fn", "getattr(${1:object}, ${2:name}${3:[, default]})$0"),
	("globals()\tglobals fn", "globals()$0"),
	("hasattr()\thasattr fn", "hasattr(${1:object}, ${2:name})$0"),
	("hash()\thash fn", "hash(${1:object})$0"),
	("help()\thelp fn", "help(${1:[object]})$0"),
	("hex()\thex fn", "hex(${1:x})$0"),
	("id()\tid fn", "id(${1:object})$0"),
	("input()\tinput fn", "input(${1:[prompt]})$0"),
	("int()\tint fn/ctor", "int(${1:x}${2:[, base]})$0"),
	("isinstance()\tisinstance fn", "isinstance(${1:object}, ${2:classinfo})$0"),
	("issubclass()\tissubclass fn", "issubclass(${1:class}, ${2:classinfo})$0"),
	("iter()\titer fn", "iter(${1:o}${2:[, sentinel]})$0"),
	("len()\tlen fn", "len(${1:object})$0"),
	("list()\tlist fn/ctor", "list(${1:[iterable]})$0"),
	("locals()\tlocals fn", "locals()$0"),
	("long()\tlong fn/ctor", "long(${1:x}${2:[, base]})$0"),
	("map()\tmap fn", "map(${1:function}${2:[, iterables]})$0"),
	("max()\tmax fn", "max(${1:iterable}${2:[, args]}${3:[, key]})$0"),
	("memoryview()\tmemoryview fn", "memoryview(${1:object})$0"),
	("min()\tmin fn", "min(${1:iterable}${2:[, args]}${3:[, key]})$0"),
	("next()\tnext fn", "next(${1:iterator}${2:[, default]})$0"),
	("object()\tobject fn", "object()$0"),
	("oct()\toct fn", "oct(${1:integer})$0"),
	("open()\topen fn", "open(${1:filename}${2:[, mode]}${3:[, bufsize]})$0"),
	("ord()\tord fn", "ord(${1:char})$0"),
	("pow()\tpow fn", "pow(${1:x}, ${2:y}${3:[, modulo]})$0"),
	("print()\tprint fn", 
		"print(${1:[object, ...][, sep=' '][, end='\\n'][, file=sys.stdout]})$0"),
	("property()\tproperty fn", "property(${1:[fget[, fset[, fdel[, doc]]]]})$0"),
	("range()\trange fn", "range(${1:[start, ]}${2:stop}${3:[, step]})$0"),
	("raw_input()\traw_input fn", "raw_input(${1:[prompt]})$0"),
	("reduce()\treduce fn", "reduce(${1:function}, ${2:iterable}${3:[, initializer]})$0"),
	("reload()\treload fn", "reload(${1:module})$0"),
	("repr()\trepr fn", "repr(${1:object})$0"),
	("reversed()\treversed fn", "reversed(${1:seq})$0"),
	("round()\tround fn", "round(${1:float}${2:[, digits]})$0"),
	("set()\tset fn/ctor", "set(${1:[iterable]})$0"),
	("setattr()\tsetattr fn", "setattr(${1:object}, ${2:name}, ${3:value})$0"),
	("slice()\tslice fn", "slice(${1:[start, ]}${2:stop}${3:[, step]})$0"),
	("sorted()\tsorted fn", 
		"sorted(${1:iterable}${2:${3:[, cmp]}${4:[, key]}${5:[, reverse]}})$0"),
	("staticmethod()\tstaticmethod fn", "staticmethod(${1:function})$0"),
	("str()\tString fn", "str(${1:object})$0"),
	("sum()\tsum fn", "sum(${1:iterable}${2:[, start]})$0"),
	("super()\tsuper fn", "super(${1:type}${2:[, object/type]})$0"),
	("tuple()\ttuple fn/ctor", "tuple(${1:[iterable]})$0"),
	("type()\ttype fn", "type(${1:object})$0"),
	("type()\ttype ctor", "type(${1:name}, ${2:bases}, ${3:dict})$0"),
	("unichr()\tunichr fn", "unichr(${1:[integer]})$0"),
	("unicode()\tunicode fn", "unicode(${1:[object, ]}${2:encoding}${3:[, errors]})$0"),
	("vars()\tvars fn", "vars(${1:[object]})$0"),
	("xrange()\txrange fn", "xrange(${1:[start, ]}${2:stop}${3:[, step]})$0"),
	("zip()\tzip fn", "zip(${1:iterable})$0")
]

py_members = [ 				# methods and attributes
	("add()\tset", "add(${1:elem})$0"),
	("append()\tMutable", "append(${1:x})$0"),
	("as_integer_ratio()\tfloat", "as_integer_ratio()$0"),
	("bit_length() 3.1\tint/long", "bit_length()$0"),
	("capitalize()\tstring", "capitalize()$0"),
	("center()\tstring", "center(${1:width}${2:[, fillchar]})$0"),
	("clear()\tset/dict", "clear()$0"),
	("close()\tfile", "close()$0"),
	("closed\tfile", "closed$0"),
	("conjugate()\tcomplex", "conjugate()$0"),
	("copy()\tSet/dict", "copy()$0"),
	("count()\tSequence", "count(${1:value})$0"),
	("count()\tstring", "count(${1:substr}${2:[, start]}${3:[, end]})$0"),
	("decode()\tstring", "decode(${1:[encoding]}${2:[, errors]})$0"),
	("difference()\tSet", "difference(${1:other,..})$0"),
	("difference_update()\tset", "difference_update(${1:other,..})$0"),
	("discard()\tset", "discard(${1:elem})$0"),
	("encode()\tstring", "encode(${1:[encoding]}${2:[, errors]})$0"),
	("encoding\tfile", "encoding$0"),
	("endswith()\tstring", "endswith(${1:suffix}${2:[, start]}${3:[, end]})$0"),
	("errors\tfile", "errors$0"),
	("expandtabs()\tstring", "expandtabs(${1:[tabsize]})$0"),
	("extend()\tMutable", "extend(${1:x})$0"),
	("fileno()\tfile", "fileno()$0"),
	("find()\tstring", "find(${1:substr}${2:[, start]}${3:[, end]})$0"),
	("flush()\tfile", "flush()$0"),
	("format()\tstring", "format(${1:*args}, ${2:**kwargs})$0"),
	("format\tmemoryview", "format$0"),
	("fromhex()\tfloat", "fromhex(${1:string})$0"),
	("fromkeys()\tDict", "fromkeys(${1:seq}${2:[, value]})$0"),
	("get()\tdict", "get(${1:key}${2:[, default]})$0"),
	("has_key()\tdict", "has_key(${1:key})$0"),
	("hex()\tfloat", "hex()$0"),
	("index()\tSequence", "index(${1:value}${2:[, start]}${3:[, end]})$0"),
	("insert()\tMutable", "insert(${1:i}, ${2:x})$0"),
	("intersection()\tSet", "intersection(${1:other,..})$0"),
	("intersection_update()\tset", "intersection_update(${1:other,..})$0"),
	("is_integer()\tfloat", "is_integer()$0"),
	("isalnum()\tstring", "isalnum()$0"),
	("isalpha()\tstring", "isalpha()$0"),
	("isatty()\tfile", "isatty()$0"),
	("isdecimal()\tunicode", "isdecimal()$0"),
	("isdigit()\tstring", "isdigit()$0"),
	("isdisjoint()\tSet", "isdisjoint(${1:other})$0"),
	("islower()\tstring", "islower()$0"),
	("isnumeric()\tunicode", "isnumeric()$0"),
	("isspace()\tstring", "isspace()$0"),
	("issubset()\tSet", "issubset(${1:other})$0"),
	("issuperset()\tSet", "issuperset(${1:other})$0"),
	("istitle()\tstring", "istitle()$0"),
	("isupper()\tstring", "isupper()$0"),
	("items()\tdict", "items()$0"),
	("itemsize\tmemoryview", "itemsize$0"),
	("iteritems()\tdict", "iteritems()$0"),
	("iterkeys()\tdict", "iterkeys()$0"),
	("itervalues()\tdict", "itervalues()$0"),
	("join()\tstring", "join(${1:iterable})$0"),
	("keys()\tdict", "keys()$0"),
	("ljust()\tstring", "ljust(${1:width}${2:[, fillchar]})$0"),
	("lower()\tstring", "lower()$0"),
	("lstrip()\tstring", "lstrip(${1:[chars]})$0"),
	("mode\tfile", "mode$0"),
	("name\tfile", "name$0"),
	("ndim\tmemoryview", "ndim$0"),
	("newlines\tfile", "newlines$0"),
	("next()\tfile", "next()$0"),
	("partition()\tstring", "partition(${1:sep})$0"),
	("pop()\tdict", "pop(${:key}${2:[, default]})$0"),
	("pop()\tMutable", "pop(${1:[i]})$0"),
	("pop()\tset", "pop()$0"),
	("popitem()\tdict", "popitem()$0"),
	("read()\tfile", "read(${1:[size]})$0"),
	("readline()\tfile", "readline(${1:[size]})$0"),
	("readlines()\tfile", "readlines(${1:[sizehint]})$0"),
	("readonly\tmemoryview", "readonly$0"),
	("remove()\tMutable", "remove(${1:x})$0"),
	("remove()\tset", "remove(${1:elem})$0"),
	("replace()\tstring", "replace(${1:old}, ${2:new}${3:[, count]})$0"),
	("reverse()\tMutable", "reverse()$0"),
	("rfind()\tstring", "rfind(${1:substr}${2:[, start]}${3:[, end]})$0"),
	("rindex()\tstring", "rindex(${1:substr}${2:[, start]}${3:[, end]})$0"),
	("rjust()\tstring", "rjust(${1:width}${2:[, fillchar]})$0"),
	("rpartition()\tstring", "rpartition(${1:sep})$0"),
	("rsplit()\tstring", "rsplit(${1:[sep]}${2:[, maxsplit]})$0"),
	("rstrip()\tstring", "rstrip(${1:[chars]})$0"),
	("seek()\tfile", "seek(${1:offset}${2:[, whence]})$0"),
	("setdefault()\tdict", "setdefault(${:key}${2:[, default]})$0"),
	("shape\tmemoryview", "shape$0"),
	("softspace\tfile", "softspace$0"),
	("sort()\tMutable", "sort(${1:[cmp]}${2:[, key]}${3:[, reverse]})$0"),
	("split()\tstring", "split(${1:[sep]}${2:[, maxsplit]})$0"),
	("splitlines()\tstring", "splitlines(${1:[keepends]})$0"),
	("startswith()\tstring", "startswith(${1:prefix}${2:[, start]}${3:[, end]})$0"),
	("strides\tmemoryview", "strides$0"),
	("strip()\tstring", "strip(${1:[chars]})$0"),
	("swapcase()\tstring", "swapcase()$0"),
	("symmetric_difference()\tSet", "symmetric_difference(${1:other})$0"),
	("symmetric_difference_update()\tset", "symmetric_difference_update(${1:other})$0"),
	("tell()\tfile", "tell()$0"),
	("title()\tstring", "title()$0"),
	("tobytes()\tmemoryview", "tobytes()$0"),
	("tolist()\tmemoryview", "tolist()$0"),
	("translate()\tstring", "translate(${1:table}${2:[, deletechars]})$0"),
	("truncate()\tfile", "truncate(${1:[size]})$0"),
	("union()\tSet", "union(${1:other,..})$0"),
	("update()\tdict/set", "update(${1:other,..})$0"),
	("upper()\tstring", "upper()$0"),
	("values()\tdict", "values()$0"),
	("viewitems()\tdict", "viewitems()$0"),
	("viewkeys()\tdict", "viewkeys()$0"),
	("viewvalues()\tdict", "viewvalues()$0"),
	("write()\tfile", "write(${1:str})$0"),
	("writelines()\tfile", "writelines(${1:sequence})$0"),
	("zfill()\tstring", "zfill(${1:width})$0")
]

subl_methods = [
	("active_group()\tST Window", "active_group()$0"),
	("active_view()\tST Window", "active_view()$0"),
	("active_view_in_group()\tST Window", "active_view_in_group(${1:group})$0"),
	("active_window()\tsublime", "active_window()$0"),
	("add()\tST RegionSet", "add(${1:region})$0"),
	("add_all()\tST RegionSet", "add_all(${1:region_set})$0"),
	("add_on_change()\tST Settings", "add_on_change(${1:key}, ${2:on_change})$0"),
	("add_regions()\tST View",
		"add_regions(${1:key}${2:[, regions]}, ${3:scope}${4:[, icon]}${5:[, flags]})$0"),
	("arch()\tsublime", "arch()$0"),
	("begin()\tST Region", "begin()$0"),
	("begin_edit()\tST View", "begin_edit(${1:[command]}${2:[, args]})$0"),
	("buffer_id()\tST View", "buffer_id()$0"),
	("clear_on_change()\tST Settings", "clear_on_change(${1:key})$0"),
	("command_history()\tST View", "command_history(${1:[index]}${2:[, modifying_only]})$0"),
	("contains()\tST Region/Set", "contains(${1:region/pt})$0"),
	("cover()\tST Region", "cover(${1:region})$0"),
	("em_width()\tST View", "em_width()$0"),
	("empty()\tST Region", "empty()$0"),
	("encoding()\tST View", "encoding()$0"),
	("end()\tST Region", "end()$0"),
	("end_edit()\tST View", "end_edit(${1:edit})$0"),
	("erase()\tST Settings", "erase(${1:name})$0"),
	("erase()\tST View", "erase(${1:edit}, ${2:region})$0"),
	("erase_regions()\tST View", "erase_regions(${1:key})$0"),
	("erase_status()\tST View", "erase_status(${1:key})$0"),
	("error_message()\tsublime", "error_message(${1:string})$0"),
	("extract_completions()\tST View", "extract_completions(${1:prefix})$0"),
	("extract_scope()\tST View", "extract_scope(${1:point})$0"),
	("file_name()\tST View", "file_name()$0"),
	("find()\tST View", "find(${1:pattern}, ${2:fromPosition}${3:[, flags]})$0"),
	("find_all()\tST View",
		"find_all(${1:pattern}${2:[, flags]}${3:[, format]}${4:[, extractions]})$0"),
	("focus_group()\tST Window", "focus_group(${1:group})$0"),
	("focus_view()\tST Window", "focus_view(${1:view})$0"),
	("fold()\tST View", "fold(${1:region(s)})$0"),
	("folders()\tST Window", "folders()$0"),
	("full_line()\tST View", "full_line(${1:region/pt})$0"),
	("find_by_selector()\tST View", "find_by_selector(${1:selector})$0"),
	("get()\tST Settings", "get(${1:name}${2:[, default]})$0"),
	("get_clipboard()\tsublime", "get_clipboard()$0"),
	("get_output_panel()\tST Window", "get_output_panel(${1:name})$0"),
	("get_regions()\tST View", "get_regions(${1:key})$0"),
	("get_status()\tST View", "get_status(${1:key})$0"),
	("get_view_index()\tST Window", "get_view_index(${1:view})$0"),
	("has()\tST Settings", "has(${1:name})$0"),
	("id()\tST View/Window", "id()$0"),
	("insert()\tST View", "insert(${1:edit}, ${2:point}, ${3:string})$0"),
	("installed_packages_path()\tsublime", "installed_packages_path()$0"),
	("intersection()\tST Region", "intersection(${1:region})$0"),
	("intersects()\tST Region", "intersects(${1:region})$0"),
	("is_dirty()\tST View", "is_dirty()$0"),
	("is_loading()\tST View", "is_loading()$0"),
	("is_read_only()\tST View", "is_read_only()$0"),
	("is_scratch()\tST View", "is_scratch()$0"),
	("layout_extent()\tST View", "layout_extent()$0"),
	("layout_to_text()\tST View", "layout_to_text(${1:vector})$0"),
	("line()\tST View", "line(${1:region/pt})$0"),
	("line_endings()\tST View", "line_endings()$0"),
	("line_height()\tST View", "line_height()$0"),
	("lines()\tST View", "lines(${1:region})$0"),
	("load_settings()\tsublime", "load_settings(${1:base_name})$0"),
	("log_commands()\tsublime", "log_commands(${1:flag})$0"),
	("log_input()\tsublime", "log_input(${1:flag})$0"),
	("match_selector()\tST View", "match_selector(${1:pt}, ${2:scope_string})$0"),
	("message_dialog()\tsublime", "message_dialog(${1:string})$0"),
	("name()\tST View", "name()$0"),
	("new_file()\tST Window", "new_file()$0"),
	("num_groups()\tST Window", "num_groups()$0"),
	("ok_cancel_dialog()\tsublime", "ok_cancel_dialog(${1:string}${2:[, ok_button]})$0"),
	("open_file()\tST Window", "open_file(${1:file_name}${2:[, flags]})$0"),
	("packages_path()\tsublime", "packages_path()$0"),
	("platform()\tsublime", "platform()$0"),
	("Region()\tsublime", "Region(${1:a}, ${2:b})$0"),
	("replace()\tST View", "replace(${1:edit}, ${2:region}, ${3:string})$0"),
	("rowcol()\tST View", "rowcol(${1:point})$0"),
	("run_command()\tsublime/View/Window", "run_command(${1:string}${2:[, args]})$0"),
	("save_settings()\tsublime", "save_settings(${1:base_name})$0"),
	("scope_name()\tST View", "scope_name(${1:point})$0"),
	("score_selector()\tST View/Window", "score_selector(${1:scope/pt}, ${2:selector})$0"),
	("sel()\tST View", "sel()$0"),
	("set()\tST Settings", "set(${1:name}, ${2:value})$0"),
	("set_clipboard()\tsublime", "set_clipboard(${1:string})$0"),
	("set_encoding()\tST View", "set_encoding(${1:encoding})$0"),
	("set_line_endings()\tST View", "set_line_endings(${1:line_endings})$0"),
	("set_name()\tST View", "set_name(${1:name})$0"),
	("set_read_only()\tST View", "set_read_only(${1:value})$0"),
	("set_scratch()\tST View", "set_scratch(${1:value})$0"),
	("set_status()\tST View", "set_status(${1:key}, ${2:value})$0"),
	("set_syntax_file()\tST View", "set_syntax_file(${1:syntax_file})$0"),
	("set_timeout()\tsublime", "set_timeout(${1:callback}, ${2:delay})$0"),
	("set_view_index()\tST Window", "set_view_index(${1:view}, ${2:group}, ${3:index})$0"),
	("settings()\tST View", "settings()$0"),
	("set_viewport_position()\tST View", "set_viewport_position(${1:vector}${2:[, animate]})$0"),
	("show()\tST View", "show(${1:region/pt}${2:[, show_surrounds]})$0"),
	("show_at_center()\tST View", "show_at_center(${1:region/pt})$0"),
	("show_input_panel()\tST Window",
	"show_input_panel(${1:caption}, ${2:initial_text}, ${3:on_done}, ${4:on_change}, ${5:on_cancel})$0"),
	("show_quick_panel()\tST Window",
		"show_quick_panel(${1:items}, ${2:on_done}${3:[, flags]})$0"),
	("size()\tST Region/View", "size()$0"),
	("split_by_newlines()\tST View", "split_by_newlines(${1:region})$0"),
	("status_message()\tsublime", "status_message(${1:string})$0"),
	("substr()\tST View", "substr(${1:region/pt})$0"),
	("subtract()\tST RegionSet", "subtract(${1:region})$0"),
	("text_point()\tST View", "text_point(${1:row}, ${2:col})$0"),
	("text_to_layout()\tST View", "text_to_layout(${1:point})$0"),
	("unfold()\tST View", "unfold(${1:region(s)})$0"),
	("version()\tsublime", "version()$0"),
	("viewport_extent()\tST View", "viewport_extent()$0"),
	("viewport_position()\tST View", "viewport_position()$0"),
	("views()\tST Window", "views()$0"),
	("views_in_group()\tST Window", "views_in_group(${1:group})$0"),
	("visible_region()\tST View", "visible_region()$0"),
	("window()\tST View", "window()$0"),
	("windows()\tsublime", "windows()$0"),
	("word()\tST View", "word(${1:region/pt})$0")
]

sublime_methods_all = list(py_members)
sublime_methods_all.extend(subl_methods)

class PythonCompletions(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		global py_funcs, py_members, subl_methods, subl_methods_all
		if not view.match_selector(locations[0], 'source.python -string -comment -constant'):
			return []
		completions = []
		pt = locations[0] - len(prefix) - 1
		ch = view.substr(sublime.Region(pt, pt + 1)) 	# the character before the trigger
		is_dot = (ch == '.')
		if is_dot: completions = py_members
		if not is_dot: completions = py_funcs
		if view.find("(?:from|import)\s+sublime", 0) is not None and is_dot:
			completions = sublime_methods_all		# include Python methods/attributes
		compl_default = [view.extract_completions(prefix)]
		compl_default = [(item + "\tDefault", item) for sublist in compl_default 
			for item in sublist if len(item) > 3] 		# flatten
		compl_default = list(set(compl_default))		# make unique
		compl_full = list(completions)
		compl_full.extend(compl_default)
		compl_full.sort()
		return (compl_full, sublime.INHIBIT_WORD_COMPLETIONS |
			sublime.INHIBIT_EXPLICIT_COMPLETIONS)
########NEW FILE########
__FILENAME__ = SortTabs
import sublime_plugin
from os import path
from operator import itemgetter

# A simple command to sort current tabs alphabetically (returning focus to the 
# original tab).
# Does not work with different groups or windows. Not catered for unsaved views 
# (although it seems to work okay if there are any). It could be modified to 
# work in these circumstances.
#   { "keys": ["ctrl+alt+b"], "command": "sort_tabs" },
class SortTabsCommand(sublime_plugin.WindowCommand):
	def run(self):
		file_views = []
		win = self.window
		curr_view = win.active_view()
		for vw in win.views():
			_, tail = path.split(vw.file_name() or path.sep)
			group, _ = win.get_view_index(vw)
			file_views.append((tail.lower(), vw, group))
		file_views.sort(key = itemgetter(2, 0))
		moving_index = 0
		for index, (_, vw, group) in enumerate(file_views):
			if index == 0 or group > prev_group:
				moving_index = 0
				prev_group = group
			else:
				moving_index += 1
			win.set_view_index(vw, group, moving_index)
		win.focus_view(curr_view)
########NEW FILE########
