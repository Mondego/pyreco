__FILENAME__ = ASCII-Decorator
import sublime
import sublime_plugin
import os
import re
import sys
import traceback
import tempfile

ST3 = int(sublime.version()) >= 3000

if not ST3:
    from subfiglet import SublimeFiglet, figlet_paths
    import subcomments
else:
    from .subfiglet import SublimeFiglet, figlet_paths
    from . import subcomments

PACKAGE_LOCATION = os.path.abspath(os.path.dirname(__file__))


class FontPreviewGeneratorCommand(sublime_plugin.WindowCommand):
    def run(self, text):
        # Find directory locations
        font_locations = figlet_paths()

        # Find available fonts
        self.options = []
        for fl in font_locations:
            for f in os.listdir(fl):
                pth = os.path.join(fl, f)
                if os.path.isfile(pth):
                    if f.endswith((".flf", ".tlf")):
                        self.options.append((f[:-4], fl))

        self.options.sort()

        with tempfile.NamedTemporaryFile(mode = 'wb', delete=False, suffix='.txt') as p:
            for font in self.options:
                f = SublimeFiglet(
                    font=font[0], directory=font[1], width=80,
                    justify="auto", direction="auto"
                )
                p.write(("Font: %s Directory: %s\n" % (font[0], font[1])).encode("utf-8"))
                p.write(f.renderText(text).replace('\r\n', '\n').replace('\r', '\n').encode('utf-8'))
                p.write("\n\n".encode("utf-8"))

        self.window.open_file(p.name)


class UpdateFigletPreviewCommand(sublime_plugin.TextCommand):
    """
        A reasonable edit command that works in ST2 and ST3
    """

    preview = None
    def run(
        self, edit, font, directory=None, width=None,
        justify=None, direction=None, use_additional_indent=False,
        flip=None, reverse=None
    ):
        preview = UpdateFigletPreviewCommand.get_buffer()
        if not ST3:
            preview = preview.encode('UTF-8')
        if preview is not None:
            self.view.replace(edit, sublime.Region(0, self.view.size()), preview)
            sel = self.view.sel()
            sel.clear()
            sel.add(sublime.Region(0, self.view.size()))
            self.view.run_command(
                "figlet",
                {
                    "font": font,
                    "directory": directory,
                    "use_additional_indent": use_additional_indent,
                    "insert_as_comment": False,
                    "width": width,
                    "justify": justify,
                    "direction": direction,
                    "flip": flip,
                    "reverse": reverse
                }
            )
            UpdateFigletPreviewCommand.clear_buffer()
            sel.clear()

    @classmethod
    def set_buffer(cls, text):
        cls.preview = text

    @classmethod
    def get_buffer(cls):
        return cls.preview

    @classmethod
    def clear_buffer(cls):
        cls.preview = None


class FigletFavoritesCommand( sublime_plugin.TextCommand ):
    def run( self, edit ):
        self.undo = False
        settings = sublime.load_settings('ASCII Decorator.sublime-settings')

        favorites = settings.get("favorite_fonts", [])

        if len(favorites) == 0:
            return

        self.fonts = []

        for f in favorites:
            if "font" not in f or "name" not in f:
                continue

            self.fonts.append(
                {
                    "name": f.get("name"),
                    "font": f.get("font"),
                    "comment": f.get("comment", True),
                    "comment_style": f.get("comment_style", "block"),
                    "width": f.get("width", 80),
                    "direction": f.get("direction", "auto"),
                    "justify": f.get("justify", "auto"),
                    "indent": f.get("indent", True),
                    "flip": f.get("flip", False),
                    "reverse": f.get("reverse", False)
                }
            )

        # Prepare and show quick panel
        if len(self.fonts):
            if not ST3:
                self.view.window().show_quick_panel(
                    [f["name"] for f in self.fonts],
                    self.apply_figlet
                )
            else:
                self.view.window().show_quick_panel(
                    [f["name"] for f in self.fonts],
                    self.apply_figlet,
                    on_highlight=self.preview if bool(settings.get("show_preview", False)) else None
                )

    def preview(self, value):
        """
            Preview the figlet output (ST3 only)
        """

        if value != -1:
            # Find the first good selection to preview
            sel = self.view.sel()
            example = None
            for s in sel:
                if s.size():
                    example = self.view.substr(s)
                    break
            if example is None:
                return

            # Create output panel and set to current syntax
            view = self.view.window().get_output_panel('figlet_preview')
            view.settings().set("draw_white_space", "none")
            self.view.window().run_command("show_panel", {"panel": "output.figlet_preview"})

            font = self.fonts[value]

            # Preview
            UpdateFigletPreviewCommand.set_buffer(example)
            view.run_command(
                "update_figlet_preview",
                {
                    "font": font.get("font"),
                    "use_additional_indent": font.get("indent"),
                    "width": font.get("width"),
                    "justify": font.get("justify"),
                    "direction": font.get("direction"),
                    "flip": font.get("flip"),
                    "reverse": font.get("reverse")
                }
            )

    def apply_figlet(self, value):
        """
            Run and apply pyfiglet on the selections in the view
        """

        # Hide the preview panel if shown
        self.view.window().run_command("hide_panel", {"panel": "output.figlet_preview"})

        # Apply figlet
        if value != -1:
            font = self.fonts[value]
            self.view.run_command(
                "figlet",
                {
                    "font": font.get("font"),
                    "insert_as_comment": font.get("comment"),
                    "comment_style": font.get("comment_style"),
                    "use_additional_indent": font.get("indent"),
                    "width": font.get("width"),
                    "justify": font.get("justify"),
                    "direction": font.get("direction"),
                    "flip": font.get("flip"),
                    "reverse": font.get("reverse")
                }
            )

    def is_enabled(self):
        enabled = False
        for s in self.view.sel():
            if s.size():
                enabled = True
        return enabled


class FigletMenuCommand( sublime_plugin.TextCommand ):
    def run( self, edit ):
        self.undo = False
        settings = sublime.load_settings('ASCII Decorator.sublime-settings')

        # Find directory locations
        font_locations = figlet_paths()

        # Find available fonts
        self.options = []
        for fl in font_locations:
            for f in os.listdir(fl):
                pth = os.path.join(fl, f)
                if os.path.isfile(pth):
                    if f.endswith((".flf", ".tlf")):
                        self.options.append(f)

        self.options.sort()

        # Prepare and show quick panel
        if len(self.options):
            if not ST3:
                self.view.window().show_quick_panel(
                    [o[:-4] for o in self.options],
                    self.apply_figlet
                )
            else:
                self.view.window().show_quick_panel(
                    [o[:-4] for o in self.options],
                    self.apply_figlet,
                    on_highlight=self.preview if bool(settings.get("show_preview", False)) else None
                )

    def preview(self, value):
        """
            Preview the figlet output (ST3 only)
        """

        if value != -1:
            # Find the first good selection to preview
            sel = self.view.sel()
            example = None
            for s in sel:
                if s.size():
                    example = self.view.substr(s)
                    break
            if example is None:
                return

            # Create output panel and set to current syntax
            view = self.view.window().get_output_panel('figlet_preview')
            view.settings().set("draw_white_space", "none")
            self.view.window().run_command("show_panel", {"panel": "output.figlet_preview"})

            # Preview
            UpdateFigletPreviewCommand.set_buffer(example)
            view.run_command(
                "update_figlet_preview",
                {
                    "font": self.options[value][:-4]
                }
            )

    def apply_figlet(self, value):
        """
            Run and apply pyfiglet on the selections in the view
        """

        # Hide the preview panel if shown
        self.view.window().run_command("hide_panel", {"panel": "output.figlet_preview"})

        # Apply figlet
        if value != -1:
            self.view.run_command(
                "figlet",
                {
                    "font": self.options[value][:-4]
                }
            )

    def is_enabled(self):
        enabled = False
        for s in self.view.sel():
            if s.size():
                enabled = True
        return enabled


class FigletDefaultCommand( sublime_plugin.TextCommand ):
    def run(self, edit):
        settings = sublime.load_settings('ASCII Decorator.sublime-settings')
        font = settings.get('ascii_decorator_font', "slant")
        self.view.run_command("figlet", {"font": font})

    def is_enabled(self):
        enabled = False
        for s in self.view.sel():
            if s.size():
                enabled = True
        return enabled


class FigletCommand( sublime_plugin.TextCommand ):
    """
        @todo Load Settings...
        Iterate over selections
            convert selection to ascii art
            preserve OS line endings and spaces/tabs
            update selections
    """

    def run(
        self, edit, font, directory=None,
        insert_as_comment=None, use_additional_indent=None, comment_style=None,
        width=80, justify=None, direction=None, flip=None, reverse=None
    ):
        self.edit = edit
        newSelections = []
        self.init(
            font, directory, insert_as_comment, use_additional_indent,
            comment_style, width, justify, direction, flip, reverse
        )

        # Loop through user selections.
        for currentSelection in self.view.sel():
            # Decorate the selection to ASCII Art.
            if currentSelection.size():
                newSelections.append( self.decorate( self.edit, currentSelection ) )
            else:
                newSelections.append(currentSelection)

        # Clear selections since they've been modified.
        self.view.sel().clear()

        for newSelection in newSelections:
            self.view.sel().add( newSelection )

    def init(
        self, font, directory, insert_as_comment, use_additional_indent,
        comment_style, width, justify, direction, flip, reverse
    ):
        """
            Read plugin settings
        """

        settings = sublime.load_settings('ASCII Decorator.sublime-settings')

        if use_additional_indent is not None:
            self.insert_as_comment = insert_as_comment
        else:
            self.insert_as_comment = settings.get("default_insert_as_comment", False)

        if use_additional_indent is not None:
            self.use_additional_indent = use_additional_indent
        else:
            self.use_additional_indent = settings.get("default_insert_as_comment", False)

        self.comment_style = settings.get("default_comment_style_preference", "block") if comment_style is None else comment_style
        if self.comment_style is None or self.comment_style not in ["line", "block"]:
            self.comment_style = "line"

        self.width = settings.get('default_width', 80) if width is None else int(width)

        self.justify = settings.get('default_justify', "auto") if width is None else justify
        if self.justify not in ["auto", "center", "left", "right"]:
            self.justify = "auto"

        self.direction = settings.get('default_direction', "auto") if width is None else direction
        if self.direction not in ["auto", "left-to-right", "right-to-left"]:
            self.direction = "auto"

        self.flip = flip if flip is not None else False
        self.reverse = reverse if reverse is not None else False

        self.font = font
        self.directory = directory

    def decorate( self, edit, currentSelection ):
        """
            Take input and use FIGlet to convert it to ASCII art.
            Normalize converted ASCII strings to use proper line endings and spaces/tabs.
        """

        # Convert the input range to a string, this represents the original selection.
        original = self.view.substr( currentSelection );

        font_locations = figlet_paths() if self.directory is None else [self.directory]

        # Find where the font resides
        directory = None
        found = False
        for fl in font_locations:
            pth = os.path.join(fl, self.font)
            for ext in (".flf", ".tlf"):
                directory = fl
                if os.path.exists(pth + ext):
                    found = True
                    break
            if found is True:
                break

        # Convert the input string to ASCII Art.
        assert found is True
        f = SublimeFiglet(
            directory=directory, font=self.font, width=self.width,
            justify=self.justify, direction=self.direction
        )
        output = f.renderText( original )
        if self.reverse is True:
            output = output.reverse()
        if self.flip is True:
            output = output.flip()

        if not ST3:
            output = output.decode("utf-8", "replace")

        # Normalize line endings based on settings.
        output = self.normalize_line_endings( output )
        # Normalize whitespace based on settings.
        output = self.fix_whitespace( original, output, currentSelection )

        self.view.replace( edit, currentSelection, output )

        return sublime.Region( currentSelection.begin(), currentSelection.begin() + len(output) )

    def normalize_line_endings(self, string):
        # Sublime buffers only use '\n', but then normalize all line-endings to
        # the appropriate ending on save.
        string = string.replace('\r\n', '\n').replace('\r', '\n')
        return string

    def fix_whitespace(self, original, prefixed, sel):
        """
            Determine leading whitespace and comments if desired.
        """

        # Determine the indent of the CSS rule
        (row, col) = self.view.rowcol(sel.begin())
        indent_region = self.view.find('^\s+', self.view.text_point(row, 0))
        if indent_region and self.view.rowcol(indent_region.begin())[0] == row:
            indent = self.view.substr(indent_region)
        else:
            indent = ''

        # Strip whitespace from the prefixed version so we get it right
        #prefixed = prefixed.strip()
        #prefixed = re.sub(re.compile('^\s+', re.M), '', prefixed)

        # Get comments for current syntax if desired
        comment = ('',)
        if self.insert_as_comment:
            comments = subcomments.get_comment(self.view, sel.begin())
            if len(comments[0]):
                comment = comments[0][0]
            if (self.comment_style == "block" or len(comments[0]) == 0) and len(comments[1]):
                comment = comments[1][0]

        # Indent the prefixed version to the right level
        settings = self.view.settings()
        use_spaces = settings.get('translate_tabs_to_spaces')
        tab_size = int(settings.get('tab_size', 8))

        # Determine if additional indentation is desired
        if self.use_additional_indent:
            indent_characters = '\t'
            if use_spaces:
                indent_characters = ' ' * tab_size
        else:
            indent_characters = ''

        # Prefix the text with desired indentation level, and comments if desired
        if len(comment) > 1:
            prefixed = prefixed.replace('\n', '\n' + indent + indent_characters)
            prefixed = comment[0] + '\n' + indent + indent_characters + prefixed + '\n' + indent + comment[1] + '\n'
        else:
            prefixed = prefixed.replace('\n', '\n' + indent + comment[0] + indent_characters)
            prefixed = comment[0] + indent_characters + prefixed  # add needed indent for first line

        match = re.search('^(\s*)', original)
        prefix = match.groups()[0]
        match = re.search('(\s*)\Z', original)
        suffix = match.groups()[0]
        return prefixed

########NEW FILE########
__FILENAME__ = pack_flf
import os
import zipfile
import sys

pth = os.path.dirname(os.path.abspath(sys.argv[0]))

if __name__ == '__main__':
    for f in os.listdir(pth):
        file_pth = os.path.join(pth, f)
        if (
            os.path.isfile(file_pth) and
            f.lower().endswith((".flf", ".tlf")) and
            not zipfile.is_zipfile(file_pth)
        ):
            print("Packing %s..." % file_pth)
            try:
                with zipfile.ZipFile(file_pth + '.zip', 'w', zipfile.ZIP_DEFLATED) as z:
                    z.write(file_pth)
                os.remove(file_pth)
                os.rename(file_pth + '.zip', file_pth)
                print("    Success!")
            except Exception as e:
                print(e)

########NEW FILE########
__FILENAME__ = unpack_flf
import os
import zipfile
import sys

pth = os.path.dirname(os.path.abspath(sys.argv[0]))

if __name__ == '__main__':
    for f in os.listdir(pth):
        file_pth = os.path.join(pth, f)
        if (
            os.path.isfile(file_pth) and
            f.lower().endswith((".flf", ".tlf")) and
            zipfile.is_zipfile(file_pth)
        ):
            print("Unpacking %s..." % file_pth)
            try:
                os.rename(file_pth, file_pth + '.zip')
                with zipfile.ZipFile(file_pth + '.zip', 'r') as z:
                    data = z.read(z.getinfo(z.infolist()[0].filename))
                with open(file_pth, "wb") as f:
                    f.write(data)
                os.remove(file_pth + '.zip')
                print("    Success!")
            except Exception as e:
                print(e)

########NEW FILE########
__FILENAME__ = subcomments
def get_comment(view, pt):
    """
    Ripped from Sublime's Default.comment.py to find comment convention
    """

    shell_vars = view.meta_info("shellVariables", pt)
    if not shell_vars:
        return ([], [])

    # transform the list of dicts into a single dict
    all_vars = {}
    for v in shell_vars:
        if 'name' in v and 'value' in v:
            all_vars[v['name']] = v['value']

    line_comments = []
    block_comments = []

    # transform the dict into a single array of valid comments
    suffixes = [""] + ["_" + str(i) for i in range(1, 10)]
    for suffix in suffixes:
        start = all_vars.setdefault("TM_COMMENT_START" + suffix)
        end = all_vars.setdefault("TM_COMMENT_END" + suffix)

        if start and end is None:
            line_comments.append((start,))
        elif start and end:
            block_comments.append((start, end))

    return (line_comments, block_comments)

########NEW FILE########
__FILENAME__ = subfiglet
import sublime
import os
from zipfile import ZipFile, is_zipfile

ST3 = int(sublime.version()) >= 3000

if not ST3:
    import pyfiglet
else:
    from . import pyfiglet


PACKAGE_LOCATION = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DIR = os.path.join(PACKAGE_LOCATION, "pyfiglet", "fonts")
USER_DIR = None


class SublimeFigletFont(pyfiglet.FigletFont):
    def __init__(self, font=pyfiglet.DEFAULT_FONT, directory=DEFAULT_DIR):
        self.font = font
        self.comment = ''
        self.chars = {}
        self.width = {}
        self.data = self.preloadFont(font, directory)
        self.loadFont()

    @classmethod
    def preloadFont(cls, font, directory=DEFAULT_DIR):
        """
        Load font file into memory. This can be overriden with
        a superclass to create different font sources.
        """

        fontPath = os.path.join(directory, font + '.flf')
        if not os.path.exists(fontPath):
            fontPath = os.path.join(directory, font + '.tlf')
            if not os.path.exists(fontPath):
                raise pyfiglet.FontNotFound("%s doesn't exist" % font)

        if is_zipfile(fontPath):
            z = None
            try:
                z = ZipFile(fontPath, 'r')
                data = z.read(z.getinfo(z.infolist()[0].filename))
                z.close()
                return data.decode('utf-8', 'replace') if ST3 else data
            except Exception as e:
                if z is not None:
                    z.close()
                raise pyfiglet.FontError("couldn't read %s: %s" % (fontPath, e))
        else:
            try:
                with open(fontPath, 'rb') as f:
                    data = f.read()
                return data.decode('utf-8', 'replace') if ST3 else data
            except Exception as e:
                raise pyfiglet.FontError("couldn't open %s: %s" % (fontPath, e))

        raise pyfiglet.FontNotFound(font)

    @classmethod
    def getFonts(cls, directory=DEFAULT_DIR):
        return [font[:-4] for font in os.walk(dir).next()[2] if font.endswith(('.flf', '.tlf'))]


class SublimeFiglet(pyfiglet.Figlet):
    def __init__(
        self, font=pyfiglet.DEFAULT_FONT, direction='auto',
        justify='auto', width=80, directory=DEFAULT_DIR
    ):
        self.font = font
        self._direction = direction
        self._justify = justify
        self.width = width
        self.setFont(directory=directory)
        self.engine = pyfiglet.FigletRenderingEngine(base=self)

    def setFont(self, **kwargs):
        directory = kwargs.get('directory', None)

        if 'font' in kwargs:
            self.font = kwargs['font']

        self.Font = SublimeFigletFont(font=self.font, directory=directory)

    def getFonts(self, directory=DEFAULT_DIR):
        return self.Font.getFonts(directory)


def figlet_paths():
    font_locations = []
    for loc in [USER_DIR, DEFAULT_DIR]:
        if loc is not None:
            font_locations.append(loc)
    return font_locations


def plugin_loaded():
    """
        Create custom doc folder if missing.  Set USER_DIR
        to None if anything goes wrong.
    """

    global USER_DIR
    USER_DIR = os.path.join(sublime.packages_path(), "User", "ASCII Decorator Fonts")

    if not os.path.exists(USER_DIR):
        try:
            os.makedirs(USER_DIR)
        except:
            pass

    if not os.path.exists(USER_DIR):
        USER_DIR = None


if not ST3:
    plugin_loaded()

########NEW FILE########
