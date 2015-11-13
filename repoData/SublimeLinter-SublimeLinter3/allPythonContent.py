__FILENAME__ = commands
# coding: utf-8
#
# commands.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module implements the Sublime Text commands provided by SublimeLinter."""

import datetime
from fnmatch import fnmatch
import json
import os
import re
import shutil
import subprocess
import tempfile
from textwrap import TextWrapper
from threading import Thread
import time

import sublime
import sublime_plugin

from .lint import highlight, linter, persist, util


def error_command(method):
    """
    A decorator that executes method only if the current view has errors.

    This decorator is meant to be used only with the run method of
    sublime_plugin.TextCommand subclasses.

    A wrapped version of method is returned.

    """

    def run(self, edit, **kwargs):
        vid = self.view.id()

        if vid in persist.errors and persist.errors[vid]:
            method(self, self.view, persist.errors[vid], **kwargs)
        else:
            sublime.message_dialog('No lint errors.')

    return run


def select_line(view, line):
    """Change view's selection to be the given line."""
    point = view.text_point(line, 0)
    sel = view.sel()
    sel.clear()
    sel.add(view.line(point))


class SublimelinterLintCommand(sublime_plugin.TextCommand):

    """A command that lints the current view if it has a linter."""

    def is_enabled(self):
        """
        Return True if the current view can be linted.

        If the view has *only* file-only linters, it can be linted
        only if the view is not dirty.

        Otherwise it can be linted.

        """

        has_non_file_only_linter = False

        vid = self.view.id()
        linters = persist.view_linters.get(vid, [])

        for lint in linters:
            if lint.tempfile_suffix != '-':
                has_non_file_only_linter = True
                break

        if not has_non_file_only_linter:
            return not self.view.is_dirty()

        return True

    def run(self, edit):
        """Lint the current view."""
        from .sublimelinter import SublimeLinter
        SublimeLinter.shared_plugin().lint(self.view.id())


class HasErrorsCommand:

    """
    A mixin class for sublime_plugin.TextCommand subclasses.

    Inheriting from this class will enable the command only if the current view has errors.

    """

    def is_enabled(self):
        """Return True if the current view has errors."""
        vid = self.view.id()
        return vid in persist.errors and len(persist.errors[vid]) > 0


class GotoErrorCommand(sublime_plugin.TextCommand):

    """A superclass for commands that go to the next/previous error."""

    def goto_error(self, view, errors, direction='next'):
        """Go to the next/previous error in view."""
        sel = view.sel()

        if len(sel) == 0:
            sel.add(sublime.Region(0, 0))

        saved_sel = tuple(sel)
        empty_selection = len(sel) == 1 and sel[0].empty()

        # sublime.Selection() changes the view's selection, get the point first
        point = sel[0].begin() if direction == 'next' else sel[-1].end()

        regions = sublime.Selection(view.id())
        regions.clear()

        for error_type in (highlight.WARNING, highlight.ERROR):
            regions.add_all(view.get_regions(highlight.MARK_KEY_FORMAT.format(error_type)))

        region_to_select = None

        # If going forward, find the first region beginning after the point.
        # If going backward, find the first region ending before the point.
        # If nothing is found in the given direction, wrap to the first/last region.
        if direction == 'next':
            for region in regions:
                if (
                    (point == region.begin() and empty_selection and not region.empty())
                    or (point < region.begin())
                ):
                    region_to_select = region
                    break
        else:
            for region in reversed(regions):
                if (
                    (point == region.end() and empty_selection and not region.empty())
                    or (point > region.end())
                ):
                    region_to_select = region
                    break

        # If there is only one error line and the cursor is in that line, we cannot move.
        # Otherwise wrap to the first/last error line unless settings disallow that.
        if region_to_select is None and ((len(regions) > 1 or not regions[0].contains(point))):
            if persist.settings.get('wrap_find', True):
                region_to_select = regions[0] if direction == 'next' else regions[-1]

        if region_to_select is not None:
            self.select_lint_region(self.view, region_to_select)
        else:
            sel.clear()
            sel.add_all(saved_sel)
            sublime.message_dialog('No {0} lint error.'.format(direction))

    @classmethod
    def select_lint_region(cls, view, region):
        """
        Select and scroll to the first marked region that contains region.

        If none are found, the beginning of region is used. The view is
        centered on the calculated region and the region is selected.

        """

        marked_region = cls.find_mark_within(view, region)

        if marked_region is None:
            marked_region = sublime.Region(region.begin(), region.begin())

        sel = view.sel()
        sel.clear()
        sel.add(marked_region)

        # There is a bug in ST3 that prevents the selection from changing
        # when a quick panel is open and the viewport does not change position,
        # so we call our own custom method that works around that.
        util.center_region_in_view(marked_region, view)

    @classmethod
    def find_mark_within(cls, view, region):
        """Return the nearest marked region that contains region, or None if none found."""

        marks = view.get_regions(highlight.MARK_KEY_FORMAT.format(highlight.WARNING))
        marks.extend(view.get_regions(highlight.MARK_KEY_FORMAT.format(highlight.ERROR)))
        marks.sort(key=sublime.Region.begin)

        for mark in marks:
            if mark.contains(region):
                return mark

        return None


class SublimelinterGotoErrorCommand(GotoErrorCommand):

    """A command that selects the next/previous error."""

    @error_command
    def run(self, view, errors, **kwargs):
        """Run the command."""
        self.goto_error(view, errors, **kwargs)


class SublimelinterShowAllErrors(sublime_plugin.TextCommand):

    """A command that shows a quick panel with all of the errors in the current view."""

    @error_command
    def run(self, view, errors):
        """Run the command."""
        self.errors = errors
        self.points = []
        options = []

        for lineno, line_errors in sorted(errors.items()):
            line = view.substr(view.full_line(view.text_point(lineno, 0))).rstrip('\n\r')

            # Strip whitespace from the front of the line, but keep track of how much was
            # stripped so we can adjust the column.
            diff = len(line)
            line = line.lstrip()
            diff -= len(line)

            max_prefix_len = 40

            for column, message in sorted(line_errors):
                # Keep track of the line and column
                point = view.text_point(lineno, column)
                self.points.append(point)

                # If there are more than max_prefix_len characters before the adjusted column,
                # lop off the excess and insert an ellipsis.
                column = max(column - diff, 0)

                if column > max_prefix_len:
                    visible_line = '...' + line[column - max_prefix_len:]
                    column = max_prefix_len + 3  # 3 for ...
                else:
                    visible_line = line

                # Insert an arrow at the column in the stripped line
                code = visible_line[:column] + '➜' + visible_line[column:]
                options.append(['{}  {}'.format(lineno + 1, message), code])

        self.viewport_pos = view.viewport_position()
        self.selection = list(view.sel())

        view.window().show_quick_panel(
            options,
            on_select=self.select_error,
            on_highlight=self.select_error
        )

    def select_error(self, index):
        """Completion handler for the quick panel. Selects the indexed error."""
        if index != -1:
            point = self.points[index]
            GotoErrorCommand.select_lint_region(self.view, sublime.Region(point, point))
        else:
            self.view.set_viewport_position(self.viewport_pos)
            self.view.sel().clear()
            self.view.sel().add_all(self.selection)


class SublimelinterToggleSettingCommand(sublime_plugin.WindowCommand):

    """Command that toggles a setting."""

    def __init__(self, window):
        """Initialize a new instance."""
        super().__init__(window)

    def is_visible(self, **args):
        """Return True if the opposite of the setting is True."""
        if args.get('checked', False):
            return True

        if persist.settings.has_setting(args['setting']):
            setting = persist.settings.get(args['setting'], None)
            return setting is not None and setting is not args['value']
        else:
            return args['value'] is not None

    def is_checked(self, **args):
        """Return True if the setting should be checked."""
        if args.get('checked', False):
            setting = persist.settings.get(args['setting'], False)
            return setting is True
        else:
            return False

    def run(self, **args):
        """Toggle the setting if value is boolean, or remove it if None."""

        if 'value' in args:
            if args['value'] is None:
                persist.settings.pop(args['setting'])
            else:
                persist.settings.set(args['setting'], args['value'], changed=True)
        else:
            setting = persist.settings.get(args['setting'], False)
            persist.settings.set(args['setting'], not setting, changed=True)

        persist.settings.save()


class ChooseSettingCommand(sublime_plugin.WindowCommand):

    """An abstract base class for commands that choose a setting from a list."""

    def __init__(self, window, setting=None, preview=False):
        """Initialize a new instance."""
        super().__init__(window)
        self.setting = setting
        self._settings = None
        self.preview = preview

    def description(self, **args):
        """Return the visible description of the command, used in menus."""
        return args.get('value', None)

    def is_checked(self, **args):
        """Return whether this command should be checked in a menu."""
        if 'value' not in args:
            return False

        item = self.transform_setting(args['value'], matching=True)
        setting = self.setting_value(matching=True)
        return item == setting

    def _get_settings(self):
        """Return the list of settings."""
        if self._settings is None:
            self._settings = self.get_settings()

        return self._settings

    settings = property(_get_settings)

    def get_settings(self):
        """Return the list of settings. Subclasses must override this."""
        raise NotImplementedError

    def transform_setting(self, setting, matching=False):
        """
        Transform the display text for setting to the form it is stored in.

        By default, returns a lowercased copy of setting.

        """
        return setting.lower()

    def setting_value(self, matching=False):
        """Return the current value of the setting."""
        return self.transform_setting(persist.settings.get(self.setting, ''), matching=matching)

    def on_highlight(self, index):
        """If preview is on, set the selected setting."""
        if self.preview:
            self.set(index)

    def choose(self, **kwargs):
        """
        Choose or set the setting.

        If 'value' is in kwargs, the setting is set to the corresponding value.
        Otherwise the list of available settings is built via get_settings
        and is displayed in a quick panel. The current value of the setting
        is initially selected in the quick panel.

        """

        if 'value' in kwargs:
            setting = self.transform_setting(kwargs['value'])
        else:
            setting = self.setting_value(matching=True)

        index = 0

        for i, s in enumerate(self.settings):
            if isinstance(s, (tuple, list)):
                s = self.transform_setting(s[0])
            else:
                s = self.transform_setting(s)

            if s == setting:
                index = i
                break

        if 'value' in kwargs:
            self.set(index)
        else:
            self.previous_setting = self.setting_value()

            self.window.show_quick_panel(
                self.settings,
                on_select=self.set,
                selected_index=index,
                on_highlight=self.on_highlight)

    def set(self, index):
        """Set the value of the setting."""

        if index == -1:
            if self.settings_differ(self.previous_setting, self.setting_value()):
                self.update_setting(self.previous_setting)

            return

        setting = self.selected_setting(index)

        if isinstance(setting, (tuple, list)):
            setting = setting[0]

        setting = self.transform_setting(setting)

        if not self.settings_differ(persist.settings.get(self.setting, ''), setting):
            return

        self.update_setting(setting)

    def update_setting(self, value):
        """Update the setting with the given value."""
        persist.settings.set(self.setting, value, changed=True)
        self.setting_was_changed(value)
        persist.settings.save()

    def settings_differ(self, old_setting, new_setting):
        """Return whether two setting values differ."""
        if isinstance(new_setting, (tuple, list)):
            new_setting = new_setting[0]

        new_setting = self.transform_setting(new_setting)
        return new_setting != old_setting

    def selected_setting(self, index):
        """
        Return the selected setting by index.

        Subclasses may override this if they want to return something other
        than the indexed value from self.settings.

        """

        return self.settings[index]

    def setting_was_changed(self, setting):
        """
        Do something after the setting value is changed but before settings are saved.

        Subclasses may override this if further action is necessary after
        the setting's value is changed.

        """
        pass


def choose_setting_command(setting, preview):
    """Return a decorator that provides common methods for concrete subclasses of ChooseSettingCommand."""

    def decorator(cls):
        def init(self, window):
            super(cls, self).__init__(window, setting, preview)

        def run(self, **kwargs):
            """Run the command."""
            self.choose(**kwargs)

        cls.setting = setting
        cls.__init__ = init
        cls.run = run
        return cls

    return decorator


@choose_setting_command('lint_mode', preview=False)
class SublimelinterChooseLintModeCommand(ChooseSettingCommand):

    """A command that selects a lint mode from a list."""

    def get_settings(self):
        """Return a list of the lint modes."""
        return [[name.capitalize(), description] for name, description in persist.LINT_MODES]

    def setting_was_changed(self, setting):
        """Update all views when the lint mode changes."""
        if setting == 'background':
            from .sublimelinter import SublimeLinter
            SublimeLinter.lint_all_views()
        else:
            linter.Linter.clear_all()


@choose_setting_command('mark_style', preview=True)
class SublimelinterChooseMarkStyleCommand(ChooseSettingCommand):

    """A command that selects a mark style from a list."""

    def get_settings(self):
        """Return a list of the mark styles."""
        return highlight.mark_style_names()


@choose_setting_command('gutter_theme', preview=True)
class SublimelinterChooseGutterThemeCommand(ChooseSettingCommand):

    """A command that selects a gutter theme from a list."""

    def get_settings(self):
        """
        Return a list of all available gutter themes, with 'None' at the end.

        Whether the theme is colorized and is a SublimeLinter or user theme
        is indicated below the theme name.

        """

        settings = self.find_gutter_themes()
        settings.append(['None', 'Do not display gutter marks'])
        self.themes.append('none')

        return settings

    def find_gutter_themes(self):
        """
        Find all SublimeLinter.gutter-theme resources.

        For each found resource, if it doesn't match one of the patterns
        from the "gutter_theme_excludes" setting, return the base name
        of resource and info on whether the theme is a standard theme
        or a user theme, as well as whether it is colorized.

        The list of paths to the resources is appended to self.themes.

        """

        self.themes = []
        settings = []
        gutter_themes = sublime.find_resources('*.gutter-theme')
        excludes = persist.settings.get('gutter_theme_excludes', [])
        pngs = sublime.find_resources('*.png')

        for theme in gutter_themes:
            # Make sure the theme has error.png and warning.png
            exclude = False
            parent = os.path.dirname(theme)

            for name in ('error', 'warning'):
                if '{}/{}.png'.format(parent, name) not in pngs:
                    exclude = True

            if exclude:
                continue

            # Now see if the theme name is in gutter_theme_excludes
            name = os.path.splitext(os.path.basename(theme))[0]

            for pattern in excludes:
                if fnmatch(name, pattern):
                    exclude = True
                    break

            if exclude:
                continue

            self.themes.append(theme)

            try:
                info = json.loads(sublime.load_resource(theme))
                colorize = info.get('colorize', False)
            except ValueError:
                colorize = False

            std_theme = theme.startswith('Packages/SublimeLinter/gutter-themes/')

            settings.append([
                name,
                '{}{}'.format(
                    'SublimeLinter theme' if std_theme else 'User theme',
                    ' (colorized)' if colorize else ''
                )
            ])

        # Sort self.themes and settings in parallel using the zip trick
        settings, self.themes = zip(*sorted(zip(settings, self.themes)))

        # zip returns tuples, convert back to lists
        settings = list(settings)
        self.themes = list(self.themes)

        return settings

    def selected_setting(self, index):
        """Return the theme name with the given index."""
        return self.themes[index]

    def transform_setting(self, setting, matching=False):
        """
        Return a transformed version of setting.

        For gutter themes, setting is a Packages-relative path
        to a .gutter-theme file.

        If matching == False, return the original setting text,
        gutter theme settings are not lowercased.

        If matching == True, return the base name of the filename
        without the .gutter-theme extension.

        """

        if matching:
            return os.path.splitext(os.path.basename(setting))[0]
        else:
            return setting


class SublimelinterToggleLinterCommand(sublime_plugin.WindowCommand):

    """A command that toggles, enables, or disables linter plugins."""

    def __init__(self, window):
        """Initialize a new instance."""
        super().__init__(window)
        self.linters = {}

    def is_visible(self, **args):
        """Return True if the command would show any linters."""
        which = args['which']

        if self.linters.get(which) is None:
            linters = []
            settings = persist.settings.get('linters', {})

            for instance in persist.linter_classes:
                linter_settings = settings.get(instance, {})
                disabled = linter_settings.get('@disable')

                if which == 'all':
                    include = True
                    instance = [instance, 'disabled' if disabled else 'enabled']
                else:
                    include = (
                        which == 'enabled' and not disabled or
                        which == 'disabled' and disabled
                    )

                if include:
                    linters.append(instance)

            linters.sort()
            self.linters[which] = linters

        return len(self.linters[which]) > 0

    def run(self, **args):
        """Run the command."""
        self.which = args['which']

        if self.linters[self.which]:
            self.window.show_quick_panel(self.linters[self.which], self.on_done)

    def on_done(self, index):
        """Completion handler for quick panel, toggle the enabled state of the chosen linter."""
        if index != -1:
            linter = self.linters[self.which][index]

            if isinstance(linter, list):
                linter = linter[0]

            settings = persist.settings.get('linters', {})
            linter_settings = settings.get(linter, {})
            linter_settings['@disable'] = not linter_settings.get('@disable', False)
            persist.settings.set('linters', settings, changed=True)
            persist.settings.save()

        self.linters = {}


class SublimelinterCreateLinterPluginCommand(sublime_plugin.WindowCommand):

    """A command that creates a new linter plugin."""

    def run(self):
        """Run the command."""
        if not sublime.ok_cancel_dialog(
            'You will be asked for the linter name. Please enter the name '
            'of the linter binary (including dashes), NOT the name of the language being linted. '
            'For example, to lint CSS with csslint, the linter name is '
            '“csslint”, NOT “css”.',
            'I understand'
        ):
            return

        self.window.show_input_panel(
            'Linter name:',
            '',
            on_done=self.copy_linter,
            on_change=None,
            on_cancel=None)

    def copy_linter(self, name):
        """Copy the template linter to a new linter with the given name."""

        self.name = name
        self.fullname = 'SublimeLinter-contrib-{}'.format(name)
        self.dest = os.path.join(sublime.packages_path(), self.fullname)

        if os.path.exists(self.dest):
            sublime.error_message('The plugin “{}” already exists.'.format(self.fullname))
            return

        src = os.path.join(sublime.packages_path(), persist.PLUGIN_DIRECTORY, 'linter-plugin-template')
        self.temp_dir = None

        try:
            self.temp_dir = tempfile.mkdtemp()
            self.temp_dest = os.path.join(self.temp_dir, self.fullname)
            shutil.copytree(src, self.temp_dest)

            self.get_linter_language(name, self.configure_linter)

        except Exception as ex:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

            sublime.error_message('An error occurred while copying the template plugin: {}'.format(str(ex)))

    def configure_linter(self, language):
        """Fill out the template and move the linter into Packages."""

        try:
            if language is None:
                return

            if not self.fill_template(self.temp_dir, self.name, self.fullname, language):
                return

            git = util.which('git')

            if git:
                subprocess.call((git, 'init', self.temp_dest))

            shutil.move(self.temp_dest, self.dest)

            util.open_directory(self.dest)
            self.wait_for_open(self.dest)

        except Exception as ex:
            sublime.error_message('An error occurred while configuring the plugin: {}'.format(str(ex)))

        finally:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

    def get_linter_language(self, name, callback):
        """Get the language (python, node, etc.) on which the linter is based."""

        languages = ['javascript', 'python', 'ruby', 'other']
        items = ['Select the language on which the linter is based:']

        for language in languages:
            items.append('    ' + language.capitalize())

        def on_done(index):
            language = languages[index - 1] if index > 0 else None
            callback(language)

        self.window.show_quick_panel(items, on_done)

    def fill_template(self, template_dir, name, fullname, language):
        """Replace placeholders and fill template files in template_dir, return success."""

        # Read per-language info
        path = os.path.join(os.path.dirname(__file__), 'create_linter_info.json')

        with open(path, mode='r', encoding='utf-8') as f:
            try:
                info = json.load(f)
            except Exception as err:
                persist.printf(err)
                sublime.error_message('A configuration file could not be opened, the linter cannot be created.')
                return False

        info = info.get(language, {})
        extra_attributes = []
        comment_re = info.get('comment_re', 'None')
        extra_attributes.append('comment_re = ' + comment_re)

        attributes = info.get('attributes', [])

        for attr in attributes:
            extra_attributes.append(attr.format(name))

        extra_attributes = '\n    '.join(extra_attributes)

        if extra_attributes:
            extra_attributes += '\n'

        extra_steps = info.get('extra_steps', '')

        if isinstance(extra_steps, list):
            extra_steps = '\n\n'.join(extra_steps)

        if extra_steps:
            extra_steps = '\n' + extra_steps + '\n'

        platform = info.get('platform', language.capitalize())

        # Replace placeholders
        placeholders = {
            '__linter__': name,
            '__user__': util.get_user_fullname(),
            '__year__': str(datetime.date.today().year),
            '__class__': self.camel_case(name),
            '__superclass__': info.get('superclass', 'Linter'),
            '__cmd__': '{}@python'.format(name) if language == 'python' else name,
            '__extra_attributes__': extra_attributes,
            '__platform__': platform,
            '__install__': info['installer'].format(name),
            '__extra_install_steps__': extra_steps
        }

        for root, dirs, files in os.walk(template_dir):
            for filename in files:
                extension = os.path.splitext(filename)[1]

                if extension in ('.py', '.md', '.txt'):
                    path = os.path.join(root, filename)

                    with open(path, encoding='utf-8') as f:
                        text = f.read()

                    for placeholder, value in placeholders.items():
                        text = text.replace(placeholder, value)

                    with open(path, mode='w', encoding='utf-8') as f:
                        f.write(text)

        return True

    def camel_case(self, name):
        """Convert and return a name in the form foo-bar to FooBar."""
        camel_name = name[0].capitalize()
        i = 1

        while i < len(name):
            if name[i] == '-' and i < len(name) - 1:
                camel_name += name[i + 1].capitalize()
                i += 1
            else:
                camel_name += name[i]

            i += 1

        return camel_name

    def wait_for_open(self, dest):
        """Wait for new linter window to open in another thread."""

        def open_linter_py():
            """Wait until the new linter window has opened and open linter.py."""

            start = datetime.datetime.now()

            while True:
                time.sleep(0.25)
                delta = datetime.datetime.now() - start

                # Wait a maximum of 5 seconds
                if delta.seconds > 5:
                    break

                window = sublime.active_window()
                folders = window.folders()

                if folders and folders[0] == dest:
                    window.open_file(os.path.join(dest, 'linter.py'))
                    break

        sublime.set_timeout_async(open_linter_py, 0)


class SublimelinterPackageControlCommand(sublime_plugin.WindowCommand):

    """
    Abstract superclass for Package Control utility commands.

    Only works if git is installed.

    """

    TAG_RE = re.compile(r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<release>\d+)(?:\+\d+)?')

    def __init__(self, window):
        """Initialize a new instance."""
        super().__init__(window)
        self.git = ''

    def is_visible(self, paths=[]):
        """Return True if any eligible plugin directories are selected."""

        if self.git == '':
            self.git = util.which('git')

        if self.git:
            for path in paths:
                if self.is_eligible_path(path):
                    return True

        return False

    def is_eligible_path(self, path):
        """
        Return True if path is an eligible directory.

        A directory is eligible if it has a messages subdirectory
        and has messages.json.

        """
        return (
            os.path.isdir(path) and
            os.path.isdir(os.path.join(path, 'messages')) and
            os.path.isfile(os.path.join(path, 'messages.json'))
        )

    def get_current_tag(self):
        """
        Return the most recent tag components.

        A tuple of (major, minor, release) is returned, or (1, 0, 0) if there are no tags.
        If the most recent tag does not conform to semver, return (None, None, None).

        """

        tag = util.communicate(['git', 'describe', '--tags', '--abbrev=0']).strip()

        if not tag:
            return (1, 0, 0)

        match = self.TAG_RE.match(tag)

        if match:
            return (int(match.group('major')), int(match.group('minor')), int(match.group('release')))
        else:
            return None


class SublimelinterNewPackageControlMessageCommand(SublimelinterPackageControlCommand):

    """
    This command automates the process of creating new Package Control release messages.

    It creates a new entry in messages.json for the next version
    and creates a new file named messages/<version>.txt.

    """

    COMMIT_MSG_RE = re.compile(r'{{{{(.+?)}}}}')

    def __init__(self, window):
        """Initialize a new instance."""
        super().__init__(window)

    def run(self, paths=[]):
        """Run the command."""

        for path in paths:
            if self.is_eligible_path(path):
                self.make_new_version_message(path)

    def make_new_version_message(self, path):
        """Make a new version message for the repo at the given path."""

        try:
            cwd = os.getcwd()
            os.chdir(path)

            version = self.get_current_tag()

            if version[0] is None:
                return

            messages_path = os.path.join(path, 'messages.json')
            message_path = self.rewrite_messages_json(messages_path, version)

            if os.path.exists(message_path):
                os.remove(message_path)

            with open(message_path, mode='w', encoding='utf-8') as f:
                header = '{} {}'.format(
                    os.path.basename(path),
                    os.path.splitext(os.path.basename(message_path))[0])
                f.write('{}\n{}\n'.format(header, '-' * (len(header) + 1)))
                f.write(self.get_commit_messages_since(version))

            self.window.run_command('open_file', args={'file': message_path})

        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            os.chdir(cwd)

    def rewrite_messages_json(self, messages_path, tag):
        """Add an entry in messages.json for tag, return relative path to the file."""

        with open(messages_path, encoding='utf-8') as f:
            messages = json.load(f)

        major, minor, release = tag
        release += 1
        tag = '{}.{}.{}'.format(major, minor, release)
        message_path = os.path.join('messages', '{}.txt'.format(tag))
        messages[tag] = message_path
        message_path = os.path.join(os.path.dirname(messages_path), message_path)

        with open(messages_path, mode='w', encoding='utf-8') as f:
            messages_json = '{\n'
            sorted_messages = []

            if 'install' in messages:
                install_message = messages.pop('install')
                sorted_messages.append('    "install": "{}"'.format(install_message))

            keys = sorted(map(self.sortable_tag, messages.keys()))

            for _, key in keys:
                sorted_messages.append('    "{}": "{}"'.format(key, messages[key]))

            messages_json += ',\n'.join(sorted_messages)
            messages_json += '\n}\n'
            f.write(messages_json)

        return message_path

    def sortable_tag(self, tag):
        """Return a version tag in a sortable form."""

        if tag == 'install':
            return (tag, tag)

        major, minor, release = tag.split('.')

        if '+' in release:
            release, update = release.split('+')
            update = '+{:04}'.format(int(update))
        else:
            update = ''

        return ('{:04}.{:04}.{:04}{}'.format(int(major), int(minor), int(release), update), tag)

    def get_commit_messages_since(self, version):
        """Return a formatted list of commit messages since the given tagged version."""

        tag = '{}.{}.{}'.format(*version)
        output = util.communicate([
            'git', 'log',
            '--pretty=format:{{{{%w(0,0,0)%s %b}}}}',
            '--reverse', tag + '..'
        ])

        # Split the messages, they are bounded by {{{{ }}}}
        messages = []

        for match in self.COMMIT_MSG_RE.finditer(output):
            messages.append(match.group(1).strip())

        # Wrap the messages
        wrapper = TextWrapper(initial_indent='- ', subsequent_indent='  ')
        messages = list(map(lambda msg: '\n'.join(wrapper.wrap(msg)), messages))
        return '\n\n'.join(messages) + '\n'


class SublimelinterReportCommand(sublime_plugin.WindowCommand):

    """
    A command that displays a report of all errors.

    The scope of the report is all open files in the current window,
    all files in all folders in the current window, or both.

    """

    def run(self, on='files'):
        """Run the command. on determines the scope of the report."""

        output = self.window.new_file()
        output.set_name('{} Error Report'.format(persist.PLUGIN_NAME))
        output.set_scratch(True)

        from .sublimelinter import SublimeLinter
        self.plugin = SublimeLinter.shared_plugin()

        if on == 'files' or on == 'both':
            for view in self.window.views():
                self.report(output, view)

        if on == 'folders' or on == 'both':
            for folder in self.window.folders():
                self.folder(output, folder)

    def folder(self, output, folder):
        """Report on all files in a folder."""

        for root, dirs, files in os.walk(folder):
            for name in files:
                path = os.path.join(root, name)

                # Ignore files over 256K to speed things up a bit
                if os.stat(path).st_size < 256 * 1024:
                    # TODO: not implemented
                    pass

    def report(self, output, view):
        """Write a report on the given view to output."""

        def finish_lint(view, linters, hit_time):
            if not linters:
                return

            def insert(edit):
                if not any(l.errors for l in linters):
                    return

                filename = os.path.basename(linters[0].filename or 'untitled')
                out = '\n{}:\n'.format(filename)

                for lint in sorted(linters, key=lambda lint: lint.name):
                    if lint.errors:
                        out += '\n  {}:\n'.format(lint.name)
                        items = sorted(lint.errors.items())

                        # Get the highest line number so we know how much padding numbers need
                        highest_line = items[-1][0]
                        width = 1

                        while highest_line >= 10:
                            highest_line /= 10
                            width += 1

                        for line, messages in items:
                            for col, message in messages:
                                out += '    {:>{width}}: {}\n'.format(line, message, width=width)

                output.insert(edit, output.size(), out)

            persist.edits[output.id()].append(insert)
            output.run_command('sublimelinter_edit')

        kwargs = {'self': self.plugin, 'view_id': view.id(), 'callback': finish_lint}

        from .sublimelinter import SublimeLinter
        Thread(target=SublimeLinter.lint, kwargs=kwargs).start()

########NEW FILE########
__FILENAME__ = highlight
#
# highlight.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""
This module implements highlighting code with marks.

The following classes are exported:

HighlightSet
Highlight


The following constants are exported:

WARNING - name of warning type
ERROR   - name of error type

MARK_KEY_FORMAT         - format string for key used to mark code regions
GUTTER_MARK_KEY_FORMAT  - format string for key used to mark gutter mark regions
MARK_SCOPE_FORMAT       - format string used for color scheme scope names

"""

import re
import sublime
from . import persist

#
# Error types
#
WARNING = 'warning'
ERROR = 'error'

MARK_KEY_FORMAT = 'sublimelinter-{}-marks'
GUTTER_MARK_KEY_FORMAT = 'sublimelinter-{}-gutter-marks'
MARK_SCOPE_FORMAT = 'sublimelinter.mark.{}'

UNDERLINE_FLAGS = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_EMPTY_AS_OVERWRITE

MARK_STYLES = {
    'outline': sublime.DRAW_NO_FILL,
    'fill': sublime.DRAW_NO_OUTLINE,
    'solid underline': sublime.DRAW_SOLID_UNDERLINE | UNDERLINE_FLAGS,
    'squiggly underline': sublime.DRAW_SQUIGGLY_UNDERLINE | UNDERLINE_FLAGS,
    'stippled underline': sublime.DRAW_STIPPLED_UNDERLINE | UNDERLINE_FLAGS,
    'none': sublime.HIDDEN
}

WORD_RE = re.compile(r'^([-\w]+)')
NEAR_RE_TEMPLATE = r'(?<!"){}({}){}(?!")'


def mark_style_names():
    """Return the keys from MARK_STYLES, sorted and capitalized, with None at the end."""
    names = list(MARK_STYLES)
    names.remove('none')
    names.sort()
    names.append('none')
    return [name.capitalize() for name in names]


class HighlightSet:

    """This class maintains a set of Highlight objects and performs bulk operations on them."""

    def __init__(self):
        """Initialize a new instance."""
        self.all = set()

    def add(self, highlight):
        """Add a Highlight to the set."""
        self.all.add(highlight)

    def draw(self, view):
        """
        Draw all of the Highlight objects in our set.

        Rather than draw each Highlight object individually, the marks in each
        object are aggregated into a new Highlight object, and that object
        is then drawn for the given view.

        """

        if not self.all:
            return

        all = Highlight()

        for highlight in self.all:
            all.update(highlight)

        all.draw(view)

    @staticmethod
    def clear(view):
        """Clear all marks in the given view."""
        for error_type in (WARNING, ERROR):
            view.erase_regions(MARK_KEY_FORMAT.format(error_type))
            view.erase_regions(GUTTER_MARK_KEY_FORMAT.format(error_type))

    def redraw(self, view):
        """Redraw all marks in the given view."""
        self.clear(view)
        self.draw(view)

    def reset(self, view):
        """Clear all marks in the given view and reset the list of marks in our Highlights."""
        self.clear(view)

        for highlight in self.all:
            highlight.reset()


class Highlight:

    """This class maintains error marks and knows how to draw them."""

    def __init__(self, code=''):
        """Initialize a new instance."""
        self.code = code
        self.marks = {WARNING: [], ERROR: []}
        self.mark_style = 'outline'
        self.mark_flags = MARK_STYLES[self.mark_style]

        # Every line that has a mark is kept in this dict, so we know which
        # lines to mark in the gutter.
        self.lines = {}

        # These are used when highlighting embedded code, for example JavaScript
        # or CSS within an HTML file. The embedded code is linted as if it begins
        # at (0, 0), but we need to keep track of where the actual start is within the source.
        self.line_offset = 0
        self.char_offset = 0

        # Linting runs asynchronously on a snapshot of the code. Marks are added to the code
        # during that asynchronous linting, and the markup code needs to calculate character
        # positions given a line + column. By the time marks are added, the actual buffer
        # may have changed, so we can't reliably use the plugin API to calculate character
        # positions. The solution is to calculate and store the character positions for
        # every line when this object is created, then reference that when needed.
        self.newlines = newlines = [0]
        last = -1

        while True:
            last = code.find('\n', last + 1)

            if last == -1:
                break

            newlines.append(last + 1)

        newlines.append(len(code))

    @staticmethod
    def strip_quotes(text):
        """Return text stripped of enclosing single/double quotes."""
        first = text[0]

        if first in ('\'', '"') and text[-1] == first:
            text = text[1:-1]

        return text

    def full_line(self, line):
        """
        Return the start/end character positions for the given line.

        This returns *real* character positions (relative to the beginning of self.code)
        base on the *virtual* line number (adjusted by the self.line_offset).

        """

        # The first line of the code needs the character offset
        if line == 0:
            char_offset = self.char_offset
        else:
            char_offset = 0

        line += self.line_offset
        start = self.newlines[line] + char_offset

        end = self.newlines[min(line + 1, len(self.newlines) - 1)]

        return start, end

    def range(self, line, pos, length=-1, near=None, error_type=ERROR, word_re=None):
        """
        Mark a range of text.

        line and pos should be zero-based. The pos and length argument can be used to control marking:

            - If pos < 0, the entire line is marked and length is ignored.

            - If near is not None, it is stripped of quotes and length = len(near)

            - If length < 0, the nearest word starting at pos is marked, and if
              no word is matched, the character at pos is marked.

            - If length == 0, no text is marked, but a gutter mark will appear on that line.

        error_type determines what type of error mark will be drawn (ERROR or WARNING).

        When length < 0, this method attempts to mark the closest word at pos on the given line.
        If you want to customize the word matching regex, pass it in word_re.

        If the error_type is WARNING and an identical ERROR region exists, it is not added.
        If the error_type is ERROR and an identical WARNING region exists, the warning region
        is removed and the error region is added.

        """

        start, end = self.full_line(line)

        if pos < 0:
            pos = 0
            length = (end - start) - 1
        elif near is not None:
            near = self.strip_quotes(near)
            length = len(near)
        elif length < 0:
            code = self.code[start:end][pos:]
            match = (word_re or WORD_RE).search(code)

            if match:
                length = len(match.group())
            else:
                length = 1

        pos += start
        region = sublime.Region(pos, pos + length)
        other_type = ERROR if error_type == WARNING else WARNING
        i_offset = 0

        for i, mark in enumerate(self.marks[other_type].copy()):
            if mark.a == region.a and mark.b == region.b:
                if error_type == WARNING:
                    return
                else:
                    self.marks[other_type].pop(i - i_offset)
                    i_offset += 1

        self.marks[error_type].append(region)

    def regex(self, line, regex, error_type=ERROR,
              line_match=None, word_match=None, word_re=None):
        """
        Mark a range of text that matches a regex.

        line, error_type and word_re are the same as in range().

        line_match may be a string pattern or a compiled regex.
        If provided, it must have a named group called 'match' that
        determines which part of the source line will be considered
        for marking.

        word_match may be a string pattern or a compiled regex.
        If provided, it must have a named group called 'mark' that
        determines which part of the source line will actually be marked.
        Multiple portions of the source line may match.

        """

        offset = 0

        start, end = self.full_line(line)
        line_text = self.code[start:end]

        if line_match:
            match = re.match(line_match, line_text)

            if match:
                line_text = match.group('match')
                offset = match.start('match')
            else:
                return

        it = re.finditer(regex, line_text)
        results = [
            result.span('mark')
            for result in it
            if word_match is None or result.group('mark') == word_match
        ]

        for start, end in results:
            self.range(line, start + offset, end - start, error_type=error_type)

    def near(self, line, near, error_type=ERROR, word_re=None):
        """
        Mark a range of text near a given word.

        line, error_type and word_re are the same as in range().

        If near is enclosed by quotes, they are stripped. The first occurrence
        of near in the given line of code is matched. If the first and last
        characters of near are word characters, a match occurs only if near
        is a complete word.

        The position at which near is found is returned, or zero if there
        is no match.

        """

        if not near:
            return

        start, end = self.full_line(line)
        text = self.code[start:end]
        near = self.strip_quotes(near)

        # Add \b fences around the text if it begins/ends with a word character
        fence = ['', '']

        for i, pos in enumerate((0, -1)):
            if near[pos].isalnum() or near[pos] == '_':
                fence[i] = r'\b'

        pattern = NEAR_RE_TEMPLATE.format(fence[0], re.escape(near), fence[1])
        match = re.search(pattern, text)

        if match:
            start = match.start(1)
        else:
            start = -1

        if start != -1:
            self.range(line, start, len(near), error_type=error_type, word_re=word_re)
            return start
        else:
            return 0

    def update(self, other):
        """
        Update this object with another Highlight.

        It is assumed that other.code == self.code.

        other's marks and error positions are merged, and this
        object takes the newlines array from other.

        """

        for error_type in (WARNING, ERROR):
            self.marks[error_type].extend(other.marks[error_type])

        # Errors override warnings on the same line
        for line, error_type in other.lines.items():
            current_type = self.lines.get(line)

            if current_type is None or current_type == WARNING:
                self.lines[line] = error_type

        self.newlines = other.newlines

    def set_mark_style(self):
        """Setup the mark style and flags based on settings."""
        self.mark_style = persist.settings.get('mark_style', 'outline')
        self.mark_flags = MARK_STYLES[self.mark_style]

        if not persist.settings.get('show_marks_in_minimap'):
            self.mark_flags |= sublime.HIDE_ON_MINIMAP

    def draw(self, view):
        """
        Draw code and gutter marks in the given view.

        Error, warning and gutter marks are drawn with separate regions,
        since each one potentially needs a different color.

        """
        self.set_mark_style()

        gutter_regions = {WARNING: [], ERROR: []}
        draw_gutter_marks = persist.settings.get('gutter_theme') != 'None'

        if draw_gutter_marks:
            # We use separate regions for the gutter marks so we can use
            # a scope that will not colorize the gutter icon, and to ensure
            # that errors will override warnings.
            for line, error_type in self.lines.items():
                region = sublime.Region(self.newlines[line], self.newlines[line])
                gutter_regions[error_type].append(region)

        for error_type in (WARNING, ERROR):
            if self.marks[error_type]:
                view.add_regions(
                    MARK_KEY_FORMAT.format(error_type),
                    self.marks[error_type],
                    MARK_SCOPE_FORMAT.format(error_type),
                    flags=self.mark_flags
                )

            if draw_gutter_marks and gutter_regions[error_type]:
                if persist.gutter_marks['colorize']:
                    scope = MARK_SCOPE_FORMAT.format(error_type)
                else:
                    scope = 'sublimelinter.gutter-mark'

                view.add_regions(
                    GUTTER_MARK_KEY_FORMAT.format(error_type),
                    gutter_regions[error_type],
                    scope,
                    icon=persist.gutter_marks[error_type]
                )

    @staticmethod
    def clear(view):
        """Clear all marks in the given view."""
        for error_type in (WARNING, ERROR):
            view.erase_regions(MARK_KEY_FORMAT.format(error_type))
            view.erase_regions(GUTTER_MARK_KEY_FORMAT.format(error_type))

    def reset(self):
        """
        Clear the list of marks maintained by this object.

        This method does not clear the marks, only the list.
        The next time this object is used to draw, the marks will be cleared.

        """
        for error_type in (WARNING, ERROR):
            del self.marks[error_type][:]
            self.lines.clear()

    def line(self, line, error_type):
        """Record the given line as having the given error type."""
        line += self.line_offset

        # Errors override warnings, if it's already an error leave it
        if self.lines.get(line) == ERROR:
            return

        self.lines[line] = error_type

    def move_to(self, line, char_offset):
        """
        Move the highlight to the given line and character offset.

        The character offset is relative to the start of the line.
        This method is used to create virtual line numbers
        and character positions when linting embedded code.

        """
        self.line_offset = line
        self.char_offset = char_offset

########NEW FILE########
__FILENAME__ = linter
#
# linter.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""
This module exports linter-related classes.

LinterMeta      Metaclass for Linter classes that does setup when they are loaded.
Linter          The main base class for linters.

"""

from distutils.versionpredicate import VersionPredicate
from fnmatch import fnmatch
from functools import lru_cache
import html.entities
from numbers import Number
import os
import re
import shlex
import sublime
from xml.sax.saxutils import unescape

from . import highlight, persist, util

#
# Private constants
#
ARG_RE = re.compile(r'(?P<prefix>@|--?)?(?P<name>[@\w][\w\-]*)(?:(?P<joiner>[=:])(?:(?P<sep>.)(?P<multiple>\+)?)?)?')
BASE_CLASSES = ('PythonLinter',)
HTML_ENTITY_RE = re.compile(r'&(?:(?:#(x)?([0-9a-fA-F]{1,4}))|(\w+));')


class LinterMeta(type):

    """Metaclass for Linter and its subclasses."""

    def __init__(cls, name, bases, attrs):
        """
        Initialize a Linter class.

        When a Linter subclass is loaded by Sublime Text, this method is called.
        We take this opportunity to do some transformations:

        - Compile regex patterns.
        - Convert strings to tuples where necessary.
        - Add a leading dot to the tempfile_suffix if necessary.
        - Build a map between defaults and linter arguments.
        - Add '@python' as an inline setting to PythonLinter subclasses.

        Finally, the class is registered as a linter for its configured syntax.

        """

        if bases:
            setattr(cls, 'disabled', False)

            if name in ('PythonLinter', 'RubyLinter'):
                return

            cls.alt_name = cls.make_alt_name(name)
            cmd = attrs.get('cmd')

            if isinstance(cmd, str):
                setattr(cls, 'cmd', shlex.split(cmd))

            syntax = attrs.get('syntax')

            try:
                if isinstance(syntax, str) and syntax[0] == '^':
                    setattr(cls, 'syntax', re.compile(syntax))
            except re.error as err:
                persist.printf(
                    'ERROR: {} disabled, error compiling syntax: {}'
                    .format(name.lower(), str(err))
                )
                setattr(cls, 'disabled', True)

            if not cls.disabled:
                for regex in ('regex', 'comment_re', 'word_re', 'version_re'):
                    attr = getattr(cls, regex)

                    if isinstance(attr, str):
                        if regex == 'regex' and cls.multiline:
                            setattr(cls, 're_flags', cls.re_flags | re.MULTILINE)

                        try:
                            setattr(cls, regex, re.compile(attr, cls.re_flags))
                        except re.error as err:
                            persist.printf(
                                'ERROR: {} disabled, error compiling {}: {}'
                                .format(name.lower(), regex, str(err))
                            )
                            setattr(cls, 'disabled', True)

            if not cls.disabled:
                if not cls.syntax or (cls.cmd is not None and not cls.cmd) or not cls.regex:
                    persist.printf('ERROR: {} disabled, not fully implemented'.format(name.lower()))
                    setattr(cls, 'disabled', True)

            for attr in ('inline_settings', 'inline_overrides'):
                if attr in attrs and isinstance(attrs[attr], str):
                    setattr(cls, attr, (attrs[attr],))

            # If this class has its own defaults, create an args_map.
            # Otherwise we use the superclass' args_map.
            if 'defaults' in attrs and attrs['defaults']:
                cls.map_args(attrs['defaults'])

            if 'PythonLinter' in [base.__name__ for base in bases]:
                # Set attributes necessary for the @python inline setting
                inline_settings = list(getattr(cls, 'inline_settings') or [])
                setattr(cls, 'inline_settings', inline_settings + ['@python'])

            if persist.plugin_is_loaded:
                # If the plugin has already loaded, then we get here because
                # a linter was added or reloaded. In that case we run reinitialize.
                cls.reinitialize()

            if 'syntax' in attrs and name not in BASE_CLASSES:
                persist.register_linter(cls, name, attrs)

    def map_args(cls, defaults):
        """
        Map plain setting names to args that will be passed to the linter executable.

        For each item in defaults, the key is matched with ARG_RE. If there is a match,
        the key is stripped of meta information and the match groups are stored as a dict
        under the stripped key.

        """

        # Check if the settings specify an argument.
        # If so, add a mapping between the setting and the argument format,
        # then change the name in the defaults to the setting name.
        args_map = {}
        setattr(cls, 'defaults', {})

        for name, value in defaults.items():
            match = ARG_RE.match(name)

            if match:
                name = match.group('name')
                args_map[name] = match.groupdict()

            cls.defaults[name] = value

        setattr(cls, 'args_map', args_map)

    @staticmethod
    def make_alt_name(name):
        """Convert and return a camel-case name to lowercase with dashes."""
        previous = name[0]
        alt_name = previous.lower()

        for c in name[1:]:
            if c.isupper() and previous.islower():
                alt_name += '-'

            alt_name += c.lower()
            previous = c

        return alt_name

    @property
    def name(cls):
        """Return the class name lowercased."""
        return cls.__name__.lower()


class Linter(metaclass=LinterMeta):

    """
    The base class for linters.

    Subclasses must at a minimum define the attributes syntax, cmd, and regex.

    """

    #
    # Public attributes
    #

    # The syntax that the linter handles. May be a string or
    # list/tuple of strings. Names should be all lowercase.
    syntax = ''

    # A string, list, tuple or callable that returns a string, list or tuple, containing the
    # command line (with arguments) used to lint.
    cmd = ''

    # If the name of the executable cannot be determined by the first element of cmd
    # (for example when cmd is a method that dynamically generates the command line arguments),
    # this can be set to the name of the executable used to do linting.
    #
    # Once the executable's name is determined, its existence is checked in the user's path.
    # If it is not available, the linter is disabled.
    executable = None

    # If the executable is available, this is set to the full path of the executable.
    # If the executable is not available, it is set an empty string.
    # Subclasses should consider this read only.
    executable_path = None

    # Some linter plugins have version requirements as far as the linter executable.
    # The following three attributes can be defined to define the requirements.
    # version_args is a string/list/tuple that represents the args used to get
    # the linter executable's version as a string.
    version_args = None

    # A regex pattern or compiled regex used to match the numeric portion of the version
    # from the output of version_args. It must contain a named capture group called
    # "version" that captures only the version, including dots but excluding a prefix
    # such as "v".
    version_re = None

    # A string which describes the version requirements, suitable for passing to
    # the distutils.versionpredicate.VersionPredicate constructor, as documented here:
    # http://pydoc.org/2.5.1/distutils.versionpredicate.html
    # Only the version requirements (what is inside the parens) should be
    # specified here, do not include the package name or parens.
    version_requirement = None

    # A regex pattern used to extract information from the executable's output.
    regex = ''

    # Set to True if the linter outputs multiline error messages. When True,
    # regex will be created with the re.MULTILINE flag. Do NOT rely on setting
    # the re.MULTILINE flag within the regex yourself, this attribute must be set.
    multiline = False

    # If you want to set flags on the regex *other* than re.MULTILINE, set this.
    re_flags = 0

    # The default type assigned to non-classified errors. Should be either
    # highlight.ERROR or highlight.WARNING.
    default_type = highlight.ERROR

    # Linters usually report errors with a line number, some with a column number
    # as well. In general, most linters report one-based line numbers and column
    # numbers. If a linter uses zero-based line numbers or column numbers, the
    # linter class should define this attribute accordingly.
    line_col_base = (1, 1)

    # If the linter executable cannot receive from stdin and requires a temp file,
    # set this attribute to the suffix of the temp file (with or without leading '.').
    # If the suffix needs to be mapped to the syntax of a file, you may make this
    # a dict that maps syntax names (all lowercase, as used in the syntax attribute),
    # to tempfile suffixes. The syntax used to lookup the suffix is the mapped
    # syntax, after using "syntax_map" in settings. If the view's syntax is not
    # in this map, the class' syntax will be used.
    #
    # Some linters can only work from an actual disk file, because they
    # rely on an entire directory structure that cannot be realistically be copied
    # to a temp directory (e.g. javac). In such cases, set this attribute to '-',
    # which marks the linter as "file-only". That will disable the linter for
    # any views that are dirty.
    tempfile_suffix = None

    # Linters may output to both stdout and stderr. By default stdout and sterr are captured.
    # If a linter will never output anything useful on a stream (including when
    # there is an error within the linter), you can ignore that stream by setting
    # this attribute to the other stream.
    error_stream = util.STREAM_BOTH

    # Many linters look for a config file in the linted file’s directory and in
    # all parent directories up to the root directory. However, some of them
    # will not do this if receiving input from stdin, and others use temp files,
    # so looking in the temp file directory doesn’t work. If this attribute
    # is set to a tuple of a config file argument and the name of the config file,
    # the linter will automatically try to find the config file, and if it is found,
    # add the config file argument to the executed command.
    #
    # Example: config_file = ('--config', '.jshintrc')
    #
    config_file = None

    # Tab width
    tab_width = 1

    # If a linter can be used with embedded code, you need to tell SublimeLinter
    # which portions of the source code contain the embedded code by specifying
    # the embedded scope selectors. This attribute maps syntax names
    # to embedded scope selectors.
    #
    # For example, the HTML syntax uses the scope `source.js.embedded.html`
    # for embedded JavaScript. To allow a JavaScript linter to lint that embedded
    # JavaScript, you would set this attribute to {'html': 'source.js.embedded.html'}.
    selectors = {}

    # If a linter reports a column position, SublimeLinter highlights the nearest
    # word at that point. You can customize the regex used to highlight words
    # by setting this to a pattern string or a compiled regex.
    word_re = None

    # If you want to provide default settings for the linter, set this attribute.
    # If a setting will be passed as an argument to the linter executable,
    # you may specify the format of the argument here and the setting will
    # automatically be passed as an argument to the executable. The format
    # specification is as follows:
    #
    # <prefix><name><joiner>[<sep>[+]]
    #
    # - <prefix>: Either empty, '@', '-' or '--'.
    # - <name>: The name of the setting.
    # - <joiner>: Either '=' or ':'. If <prefix> is empty or '@', <joiner> is ignored.
    #   Otherwise, if '=', the setting value is joined with <name> by '=' and
    #   passed as a single argument. If ':', <name> and the value are passed
    #   as separate arguments.
    # - <sep>: If the argument accepts a list of values, <sep> specifies
    #   the character used to delimit the list (usually ',').
    # - +: If the setting can be a list of values, but each value must be
    #   passed as a separate argument, terminate the setting with '+'.
    #
    # After the format is parsed, the prefix and suffix are removed and the
    # setting is replaced with <name>.
    defaults = None

    # Linters may define a list of settings that can be specified inline.
    # As with defaults, you can specify that an inline setting should be passed
    # as an argument by using a prefix and optional suffix. However, if
    # the same setting was already specified as an argument in defaults,
    # you do not need to use the prefix or suffix here.
    #
    # Within a file, the actual inline setting name is '<linter>-setting', where <linter>
    # is the lowercase name of the linter class.
    inline_settings = None

    # Many linters allow a list of options to be specified for a single setting.
    # For example, you can often specify a list of errors to ignore.
    # This attribute is like inline_settings, but inline values will override
    # existing values instead of replacing them, using the override_options method.
    inline_overrides = None

    # If the linter supports inline settings, you need to specify the regex that
    # begins a comment. comment_re should be an unanchored pattern (no ^)
    # that matches everything through the comment prefix, including leading whitespace.
    #
    # For example, to specify JavaScript comments, you would use the pattern:
    #    r'\s*/[/*]'
    # and for python:
    #    r'\s*#'
    comment_re = None

    # Some linters may want to turn a shebang into an inline setting.
    # To do so, set this attribute to a callback which receives the first line
    # of code and returns a tuple/list which contains the name and value for the
    # inline setting, or None if there is no match.
    shebang_match = None

    #
    # Internal class storage, do not set
    #
    RC_SEARCH_LIMIT = 3
    errors = None
    highlight = None
    lint_settings = None
    env = None
    disabled = False
    executable_version = None

    @classmethod
    def initialize(cls):
        """
        Perform class-level initialization.

        If subclasses override this, they should call super().initialize() first.

        """
        pass

    @classmethod
    def reinitialize(cls):
        """
        Perform class-level initialization after plugins have been loaded at startup.

        This occurs if a new linter plugin is added or reloaded after startup.
        Subclasses may override this to provide custom behavior, then they must
        call cls.initialize().

        """
        cls.initialize()

    def __init__(self, view, syntax):
        """Initialize a new instance."""
        self.view = view
        self.syntax = syntax
        self.code = ''
        self.highlight = highlight.Highlight()
        self.ignore_matches = None

    @property
    def filename(self):
        """Return the view's file path or '' if unsaved."""
        return self.view.file_name() or ''

    @property
    def name(self):
        """Return the class name lowercased."""
        return self.__class__.__name__.lower()

    @classmethod
    def clear_settings_caches(cls):
        """Clear lru caches for this class' methods."""
        cls.get_view_settings.cache_clear()
        cls.get_merged_settings.cache_clear()

    @classmethod
    def settings(cls):
        """Return the default settings for this linter, merged with the user settings."""

        if cls.lint_settings is None:
            linters = persist.settings.get('linters', {})
            cls.lint_settings = (cls.defaults or {}).copy()
            cls.lint_settings.update(linters.get(cls.name, {}))

        return cls.lint_settings

    @staticmethod
    def meta_settings(settings):
        """Return a dict with the items in settings whose keys begin with '@'."""
        return {key: value for key, value in settings.items() if key.startswith('@')}

    @lru_cache(maxsize=None)
    def get_view_settings(self, no_inline=False):
        """
        Return a union of all settings specific to this linter, related to the given view.

        The settings are merged in the following order:

        default settings
        user settings
        project settings
        user + project meta settings
        rc settings
        rc meta settings
        shebang or inline settings (overrides)

        """

        settings = self.get_merged_settings()

        if not no_inline:
            inline_settings = {}

            if self.shebang_match:
                eol = self.code.find('\n')

                if eol != -1:
                    setting = self.shebang_match(self.code[0:eol])

                    if setting is not None:
                        inline_settings[setting[0]] = setting[1]

            if self.comment_re and (self.inline_settings or self.inline_overrides):
                inline_settings.update(util.inline_settings(
                    self.comment_re,
                    self.code,
                    prefix=self.name,
                    alt_prefix=self.alt_name
                ))

            settings = self.merge_inline_settings(settings.copy(), inline_settings)

        return settings

    @lru_cache(maxsize=None)
    def get_merged_settings(self):
        """
        Return a union of all non-inline settings specific to this linter, related to the given view.

        The settings are merged in the following order:

        default settings
        user settings
        project settings
        user + project meta settings
        rc settings
        rc meta settings

        """

        # Start with the overall project settings. Note that when
        # files are loaded during quick panel preview, it can happen
        # that they are linted without having a window.
        window = self.view.window()

        if window:
            data = window.project_data() or {}
            project_settings = data.get(persist.PLUGIN_NAME, {})
        else:
            project_settings = {}

        # Merge global meta settings with project meta settings
        meta = self.meta_settings(persist.settings.settings)
        meta.update(self.meta_settings(project_settings))

        # Get the linter's project settings, update them with meta settings
        project_settings = project_settings.get('linters', {}).get(self.name, {})
        project_settings.update(meta)

        # Update the linter's settings with the project settings
        settings = self.merge_project_settings(self.settings().copy(), project_settings)

        # Update with rc settings
        self.merge_rc_settings(settings)

        self.replace_settings_tokens(settings)
        return settings

    def replace_settings_tokens(self, settings):
        """Replace tokens with values in settings."""
        def recursive_replace(expressions, mutable_input):
            for k, v in mutable_input.items():
                if type(v) is dict:
                    recursive_replace(expressions, mutable_input[k])
                elif type(v) is list:
                    for exp in expressions:
                        if exp['is_regex']:
                            mutable_input[k] = [
                                exp['token'].sub(exp['value'], i)
                                for i in mutable_input[k]
                            ]
                        else:
                            mutable_input[k] = [
                                i.replace(exp['token'], exp['value'])
                                for i in mutable_input[k]
                            ]
                elif type(v) is str:
                    for exp in expressions:
                        if exp['is_regex']:
                            mutable_input[k] = exp['token'].sub(exp['value'], mutable_input[k])
                        else:
                            mutable_input[k] = mutable_input[k].replace(exp['token'], exp['value'])

        # Go through and expand the supported path tokens in place.
        # Supported tokens, in the order they are expanded:
        # ${project}: the project's base directory, if available.
        # ${directory}: the dirname of the current view's file.
        # ${env:<x>}: the environment variable 'x'.
        # ${home}: the user's $HOME directory.
        #
        # ${project} and ${directory} expansion are dependent on
        # having a window.

        # Expressions are evaluated in list order.
        expressions = []
        window = self.view.window()

        if window:
            view = window.active_view()

            if window.project_file_name():
                project = os.path.dirname(window.project_file_name())

                expressions.append({
                    'is_regex': False,
                    'token': '${project}',
                    'value': project})

            expressions.append({
                'is_regex': False,
                'token': '${directory}',
                'value': (
                    os.path.dirname(view.file_name()) if
                    view and view.file_name() else "FILE NOT ON DISK")})

        expressions.append({
            'is_regex': True,
            'token': re.compile(r'\${env:(?P<variable>[^}]+)}'),
            'value': (
                lambda m: os.getenv(m.group('variable')) if
                os.getenv(m.group('variable')) else
                "%s NOT SET" % m.group('variable'))})

        expressions.append({
            'is_regex': False,
            'token': '${home}',
            'value': re.escape(os.getenv('HOME') or 'HOME NOT SET')})

        recursive_replace(expressions, settings)

    def merge_rc_settings(self, settings):
        """
        Merge .sublimelinterrc settings with settings.

        Searches for .sublimelinterrc in, starting at the directory of the linter's view.
        The search is limited to rc_search_limit directories. If found, the meta settings
        and settings for this linter in the rc file are merged with settings.

        """

        search_limit = persist.settings.get('rc_search_limit', self.RC_SEARCH_LIMIT)
        rc_settings = util.get_view_rc_settings(self.view, limit=search_limit)

        if rc_settings:
            meta = self.meta_settings(rc_settings)
            rc_settings = rc_settings.get('linters', {}).get(self.name, {})
            rc_settings.update(meta)
            settings.update(rc_settings)

    def merge_inline_settings(self, view_settings, inline_settings):
        """
        Return view settings merged with inline settings.

        view_settings is merged with inline_settings specified by
        the class attributes inline_settings and inline_overrides.
        view_settings is updated in place and returned.

        """

        for setting, value in inline_settings.items():
            if self.inline_settings and setting in self.inline_settings:
                view_settings[setting] = value
            elif self.inline_overrides and setting in self.inline_overrides:
                options = view_settings[setting]
                sep = self.args_map.get(setting, {}).get('sep')

                if sep:
                    kwargs = {'sep': sep}
                    options = options or ''
                else:
                    kwargs = {}
                    options = options or ()

                view_settings[setting] = self.override_options(options, value, **kwargs)

        return view_settings

    def merge_project_settings(self, view_settings, project_settings):
        """
        Return this linter's view settings merged with the current project settings.

        Subclasses may override this if they wish to do something more than
        replace view settings with inline settings of the same name.
        The settings object may be changed in place.

        """
        view_settings.update(project_settings)
        return view_settings

    def override_options(self, options, overrides, sep=','):
        """
        Return a list of options with overrides applied.

        If you want inline settings to override but not replace view settings,
        this method makes it easier. Given a set or sequence of options and some
        overrides, this method will do the following:

        - Copies options into a set.
        - Split overrides into a list if it's a string, using sep to split.
        - Iterates over each value in the overrides list:
            - If it begins with '+', the value (without '+') is added to the options set.
            - If it begins with '-', the value (without '-') is removed from the options set.
            - Otherwise the value is added to the options set.
        - The options set is converted to a list and returned.

        For example, given the options 'E101,E501,W' and the overrides
        '-E101,E202,-W,+W324', we would end up with 'E501,E202,W324'.

        """

        if isinstance(options, str):
            options = options.split(sep) if options else ()
            return_str = True
        else:
            return_str = False

        modified_options = set(options)

        if isinstance(overrides, str):
            overrides = overrides.split(sep)

        for override in overrides:
            if not override:
                continue
            elif override[0] == '+':
                modified_options.add(override[1:])
            elif override[0] == '-':
                modified_options.discard(override[1:])
            else:
                modified_options.add(override)

        if return_str:
            return sep.join(modified_options)
        else:
            return list(modified_options)

    @classmethod
    def assign(cls, view, linter_name=None, reset=False):
        """
        Assign linters to a view.

        If reset is True, the list of linters for view is completely rebuilt.

        can_lint for each known linter class is called to determine
        if the linter class can lint the syntax for view. If so, a new instance
        of the linter class is assigned to the view, unless linter_name is non-empty
        and does not match the 'name' attribute of any of the view's linters.

        Each view has its own linters so that linters can store persistent data
        about a view.

        """

        vid = view.id()
        persist.views[vid] = view
        syntax = persist.get_syntax(view)

        if not syntax:
            cls.remove(vid)
            return

        view_linters = persist.view_linters.get(vid, set())
        linters = set()

        for name, linter_class in persist.linter_classes.items():
            if not linter_class.disabled and linter_class.can_lint(syntax):

                if reset:
                    instantiate = True
                else:
                    linter = None

                    for l in view_linters:
                        if name == l.name:
                            linter = l
                            break

                    if linter is None:
                        instantiate = True
                    else:
                        # If there is an existing linter and no linter_name was passed,
                        # leave it. If linter_name was passed, re-instantiate only if
                        # the linter's name matches linter_name.
                        instantiate = linter_name == linter.name

                if instantiate:
                    linter = linter_class(view, syntax)

                linters.add(linter)

        if linters:
            persist.view_linters[vid] = linters
        elif reset and not linters and vid in persist.view_linters:
            del persist.view_linters[vid]

    @classmethod
    def remove(cls, vid):
        """Remove a the mapping between a view and its set of linters."""

        if vid in persist.view_linters:
            for linters in persist.view_linters[vid]:
                linters.clear()

            del persist.view_linters[vid]

    @classmethod
    def reload(cls):
        """Assign new instances of linters to views."""

        # Merge linter default settings with user settings
        for name, linter in persist.linter_classes.items():
            linter.lint_settings = None

        for vid, linters in persist.view_linters.items():
            for linter in linters:
                linter.clear()
                persist.view_linters[vid].remove(linter)
                linter_class = persist.linter_classes[linter.name]
                linter = linter_class(linter.view, linter.syntax)
                persist.view_linters[vid].add(linter)

    @classmethod
    def apply_to_all_highlights(cls, action):
        """Apply an action to the highlights of all views."""

        def apply(view):
            highlights = persist.highlights.get(view.id())

            if highlights:
                getattr(highlights, action)(view)

        util.apply_to_all_views(apply)

    @classmethod
    def clear_all(cls):
        """Clear highlights and errors in all views."""
        cls.apply_to_all_highlights('reset')
        persist.errors.clear()

    @classmethod
    def redraw_all(cls):
        """Redraw all highlights in all views."""
        cls.apply_to_all_highlights('redraw')

    @classmethod
    def text(cls, view):
        """Return the entire text of a view."""
        return view.substr(sublime.Region(0, view.size()))

    @classmethod
    def get_view(cls, vid):
        """Return the view object with the given id."""
        return persist.views.get(vid)

    @classmethod
    def get_linters(cls, vid):
        """Return a tuple of linters for the view with the given id."""
        if vid in persist.view_linters:
            return tuple(persist.view_linters[vid])

        return ()

    @classmethod
    def get_selectors(cls, vid, syntax):
        """
        Return scope selectors and linters for the view with the given id.

        For each linter assigned to the view with the given id, if it
        has selectors, return a tuple of the selector and the linter.

        """
        selectors = []

        for linter in cls.get_linters(vid):
            if syntax in linter.selectors:
                selectors.append((linter.selectors[syntax], linter))

            if '*' in linter.selectors:
                selectors.append((linter.selectors['*'], linter))

        return selectors

    @classmethod
    def lint_view(cls, view, filename, code, hit_time, callback):
        """
        Lint the given view.

        This is the top level lint dispatcher. It is called
        asynchronously. The following checks are done for each linter
        assigned to the view:

        - Check if the linter has been disabled in settings.
        - Check if the filename matches any patterns in the "excludes" setting.

        If a linter fails the checks, it is disabled for this run.
        Otherwise, if the mapped syntax is not in the linter's selectors,
        the linter is run on the entirety of code.

        Then the set of selectors for all linters assigned to the view is
        aggregated, and for each selector, if it occurs in sections,
        the corresponding section is linted as embedded code.

        A list of the linters that ran is returned.

        """

        if not code:
            return

        vid = view.id()
        linters = persist.view_linters.get(vid)

        if not linters:
            return

        disabled = set()
        syntax = persist.get_syntax(persist.views[vid])

        for linter in linters:
            # First check to see if the linter can run in the current lint mode.
            if linter.tempfile_suffix == '-' and view.is_dirty():
                disabled.add(linter)
                continue

            # Because get_view_settings is expensive, we use an lru_cache
            # to cache its results. Before each lint, reset the cache.
            linter.clear_settings_caches()
            view_settings = linter.get_view_settings(no_inline=True)

            # We compile the ignore matches for a linter on each run,
            # clear the cache first.
            linter.ignore_matches = None

            if view_settings.get('@disable'):
                disabled.add(linter)
                continue

            if filename:
                filename = os.path.realpath(filename)
                excludes = util.convert_type(view_settings.get('excludes', []), [])

                if excludes:
                    matched = False

                    for pattern in excludes:
                        if fnmatch(filename, pattern):
                            persist.debug(
                                '{} skipped \'{}\', excluded by \'{}\''
                                .format(linter.name, filename, pattern)
                            )
                            matched = True
                            break

                    if matched:
                        disabled.add(linter)
                        continue

            if syntax not in linter.selectors and '*' not in linter.selectors:
                linter.reset(code, view_settings)
                linter.lint(hit_time)

        selectors = Linter.get_selectors(vid, syntax)

        for selector, linter in selectors:
            if linter in disabled:
                continue

            linters.add(linter)
            regions = []

            for region in view.find_by_selector(selector):
                regions.append(region)

            linter.reset(code, view_settings)
            errors = {}

            for region in regions:
                line_offset, col = view.rowcol(region.begin())
                linter.highlight.move_to(line_offset, col)
                linter.code = code[region.begin():region.end()]
                linter.errors = {}
                linter.lint(hit_time)

                for line, line_errors in linter.errors.items():
                    errors[line + line_offset] = line_errors

            linter.errors = errors

        # Remove disabled linters
        linters = list(linters - disabled)

        # Merge our result back to the main thread
        callback(cls.get_view(vid), linters, hit_time)

    def compile_ignore_match(self, pattern):
        """Return the compiled pattern, log the error if compilation fails."""
        try:
            return re.compile(pattern)
        except re.error as err:
            persist.printf(
                'ERROR: {}: invalid ignore_match: "{}" ({})'
                .format(self.name, pattern, str(err))
            )
            return None

    def compiled_ignore_matches(self, ignore_match):
        """
        Compile the "ignore_match" linter setting as an optimization.

        If it's a string, return a list with a single compiled regex.
        If it's a list, return a list of the compiled regexes.
        If it's a dict, return a list only of the regexes whose key
        matches the file's extension.

        """

        if isinstance(ignore_match, str):
            regex = self.compile_ignore_match(ignore_match)
            return [regex] if regex else []

        elif isinstance(ignore_match, list):
            matches = []

            for match in ignore_match:
                regex = self.compile_ignore_match(match)

                if regex:
                    matches.append(regex)

            return matches

        elif isinstance(ignore_match, dict):
            if not self.filename:
                return []

            ext = os.path.splitext(self.filename)[1].lower()

            if not ext:
                return []

            # Try to match the extension, then the extension without the dot
            ignore_match = ignore_match.get(ext, ignore_match.get(ext[1:]))

            if ignore_match:
                return self.compiled_ignore_matches(ignore_match)
            else:
                return []

        else:
            return []

    def reset(self, code, settings):
        """Reset a linter to work on the given code and filename."""
        self.errors = {}
        self.code = code
        self.highlight = highlight.Highlight(self.code)

        if self.ignore_matches is None:
            ignore_match = settings.get('ignore_match')

            if ignore_match:
                self.ignore_matches = self.compiled_ignore_matches(ignore_match)
            else:
                self.ignore_matches = []

    @classmethod
    def which(cls, cmd):
        """Call util.which with this class' module and return the result."""
        return util.which(cmd, module=getattr(cls, 'module', None))

    def get_cmd(self):
        """
        Calculate and return a tuple/list of the command line to be executed.

        The cmd class attribute may be a string, a tuple/list, or a callable.
        If cmd is callable, it is called. If the result of the method is
        a string, it is parsed into a list with shlex.split.

        Otherwise the result of build_cmd is returned.

        """
        if callable(self.cmd):
            cmd = self.cmd()

            if isinstance(cmd, str):
                cmd = shlex.split(cmd)

            return self.insert_args(cmd)
        else:
            return self.build_cmd()

    def build_cmd(self, cmd=None):
        """
        Return a tuple with the command line to execute.

        We start with cmd or the cmd class attribute. If it is a string,
        it is parsed with shlex.split.

        If the first element of the command line matches [script]@python[version],
        and '@python' is in the aggregated view settings, util.which is called
        to determine the path to the script and given version of python. This
        allows settings to override the version of python used.

        Otherwise, if self.executable_path has already been calculated, that
        is used. If not, the executable path is located with util.which.

        If the path to the executable can be determined, a list of extra arguments
        is built with build_args. If the cmd contains '*', it is replaced
        with the extra argument list, otherwise the extra args are appended to
        cmd.

        """

        cmd = cmd or self.cmd

        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        else:
            cmd = list(cmd)

        which = cmd[0]
        have_path, path = self.context_sensitive_executable_path(cmd)

        if have_path:
            # Returning None means the linter runs code internally
            if path == '<builtin>':
                return None
        elif self.executable_path:
            path = self.executable_path

            if isinstance(path, (list, tuple)) and None in path:
                path = None
        else:
            path = self.which(which)

        if not path:
            persist.printf('ERROR: {} cannot locate \'{}\''.format(self.name, which))
            return ''

        cmd[0:1] = util.convert_type(path, [])
        return self.insert_args(cmd)

    def context_sensitive_executable_path(self, cmd):
        """
        Calculate the context-sensitive executable path, return a tuple of (have_path, path).

        Subclasses may override this to return a special path.

        """
        return False, None

    def insert_args(self, cmd):
        """Insert user arguments into cmd and return the result."""
        args = self.build_args(self.get_view_settings())
        cmd = list(cmd)

        if '*' in cmd:
            i = cmd.index('*')

            if args:
                cmd[i:i + 1] = args
            else:
                cmd.pop(i)
        else:
            cmd += args

        return cmd

    def get_user_args(self, settings=None):
        """Return any args the user specifies in settings as a list."""

        if settings is None:
            settings = self.get_merged_settings()

        args = settings.get('args', [])

        if isinstance(args, str):
            args = shlex.split(args)
        else:
            args = args[:]

        return args

    def build_args(self, settings):
        """
        Return a list of args to add to cls.cmd.

        First any args specified in the "args" linter setting are retrieved.
        Then the args map (built by map_args during class construction) is
        iterated. For each item in the args map:

        - Check to see if the arg is in settings, which is the aggregated
          default/user/view settings. If arg is not in settings or is a meta
          setting (beginning with '@'), it is skipped.

        - If the arg has no prefix, it is skipped.

        - Get the setting value. If it is None or an empty string/list, skip this arg.

        - If the setting value is a non-empty list and the arg was specified
          as taking a single list of values, join the values.

        - If the setting value is a non-empty string or the boolean True,
          convert it into a single-element list with that value.

        Once a list of values is built, iterate over the values to build
        the args list:

        - Start with the prefix and arg name.
        - If the joiner is '=', join '=' and the value and append to the args.
        - If the joiner is ':', append the arg and value as separate args.

        Finally, if the config_file attribute is set and the user has not
        set the config_file arg in the linter's "args" setting, try to
        locate the config file and if found add the config file arg.

        Return the arg list.

        """

        args = self.get_user_args(settings)
        args_map = getattr(self, 'args_map', {})

        for setting, arg_info in args_map.items():
            prefix = arg_info['prefix']

            if setting not in settings or setting[0] == '@' or prefix is None:
                continue

            values = settings[setting]

            if values is None:
                continue
            elif isinstance(values, (list, tuple)):
                if values:
                    # If the values can be passed as a single list, join them now
                    if arg_info['sep'] and not arg_info['multiple']:
                        values = [str(value) for value in values]
                        values = [arg_info['sep'].join(values)]
                else:
                    continue
            elif isinstance(values, str):
                if values:
                    values = [values]
                else:
                    continue
            elif isinstance(values, Number):
                if values is False:
                    continue
                else:
                    values = [values]
            else:
                # Unknown type
                continue

            for value in values:
                if prefix == '@':
                    args.append(str(value))
                else:
                    arg = prefix + arg_info['name']
                    joiner = arg_info['joiner']

                    if joiner == '=':
                        args.append('{}={}'.format(arg, value))
                    elif joiner == ':':
                        args.append(arg)
                        args.append(str(value))

        if self.config_file:
            if self.config_file[0] not in args and self.filename:
                config = util.find_file(
                    os.path.dirname(self.filename),
                    self.config_file[1],
                    aux_dirs=self.config_file[2:]
                )

                if config:
                    args += [self.config_file[0], config]

        return args

    def build_options(self, options, type_map, transform=None):
        """
        Build a list of options to be passed directly to a linting method.

        This method is designed for use with linters that do linting directly
        in code and need to pass a dict of options.

        options is the starting dict of options. For each of the settings
        listed in self.args_map:

        - See if the setting name is in view settings.

        - If so, and the value is non-empty, see if the setting
          name is in type_map. If so, convert the value to the type
          of the value in type_map.

        - If transform is not None, pass the name to it and assign to the result.

        - Add the name/value pair to options.

        """

        view_settings = self.get_view_settings()

        for name, info in self.args_map.items():
            value = view_settings.get(name)

            if value:
                value = util.convert_type(value, type_map.get(name), sep=info.get('sep'))

                if value is not None:
                    if transform:
                        name = transform(name)

                    options[name] = value

    def lint(self, hit_time):
        """
        Perform the lint, retrieve the results, and add marks to the view.

        The flow of control is as follows:

        - Get the command line. If it is an empty string, bail.
        - Run the linter.
        - If the view has been modified since the original hit_time, stop.
        - Parse the linter output with the regex.
        - Highlight warnings and errors.

        """

        if self.disabled:
            return

        if self.filename and os.path.exists(self.filename):
            cwd = os.getcwd()
            os.chdir(os.path.dirname(self.filename))

        if self.cmd is None:
            cmd = None
        else:
            cmd = self.get_cmd()

            if cmd is not None and not cmd:
                return

        output = self.run(cmd, self.code)

        if self.filename:
            os.chdir(cwd)

        if not output:
            return

        # If the view has been modified since the lint was triggered, no point in continuing.
        if hit_time is not None and persist.last_hit_times.get(self.view.id(), 0) > hit_time:
            return

        if persist.debug_mode():
            stripped_output = output.replace('\r', '').rstrip()
            persist.printf('{} output:\n{}'.format(self.name, stripped_output))

        for match, line, col, error, warning, message, near in self.find_errors(output):
            if match and message and line is not None:
                if self.ignore_matches:
                    ignore = False

                    for ignore_match in self.ignore_matches:
                        if ignore_match.match(message):
                            ignore = True

                            if persist.debug_mode():
                                persist.printf(
                                    '{} ({}): ignore_match: "{}" == "{}"'
                                    .format(
                                        self.name,
                                        os.path.basename(self.filename) or '<unsaved>',
                                        ignore_match.pattern,
                                        message
                                    )
                                )
                            break

                    if ignore:
                        continue

                if error:
                    error_type = highlight.ERROR
                elif warning:
                    error_type = highlight.WARNING
                else:
                    error_type = self.default_type

                if col is not None:
                    # Pin the column to the start/end line offsets
                    start, end = self.highlight.full_line(line)
                    col = max(min(col, (end - start) - 1), 0)

                    # Adjust column numbers to match the linter's tabs if necessary
                    if self.tab_width > 1:
                        code_line = self.code[start:end]
                        diff = 0

                        for i in range(len(code_line)):
                            if code_line[i] == '\t':
                                diff += (self.tab_width - 1)

                            if col - diff <= i:
                                col = i
                                break

                if col is not None:
                    self.highlight.range(line, col, near=near, error_type=error_type, word_re=self.word_re)
                elif near:
                    col = self.highlight.near(line, near, error_type=error_type, word_re=self.word_re)
                else:
                    if (
                        persist.settings.get('no_column_highlights_line') or
                        persist.settings.get('gutter_theme') == 'none'
                    ):
                        pos = -1
                    else:
                        pos = 0

                    self.highlight.range(line, pos, length=0, error_type=error_type, word_re=self.word_re)

                self.error(line, col, message, error_type)

    def draw(self):
        """Draw the marks from the last lint."""
        self.highlight.draw(self.view)

    @staticmethod
    def clear_view(view):
        """Clear marks, status and all other cached error info for the given view."""

        view.erase_status('sublimelinter')
        highlight.Highlight.clear(view)

        if view.id() in persist.errors:
            del persist.errors[view.id()]

    def clear(self):
        """Clear marks, status and all other cached error info for the given view."""
        self.clear_view(self.view)

    # Helper methods

    @classmethod
    @lru_cache(maxsize=None)
    def can_lint(cls, syntax):
        """
        Determine if a linter class can lint the given syntax.

        This method is called when a view has not had a linter assigned
        or when its syntax changes.

        The following tests must all pass for this method to return True:

        1. syntax must match one of the syntaxes the linter defines.
        2. If the linter uses an external executable, it must be available.
        3. If there is a version requirement and the executable is available,
           its version must fulfill the requirement.
        4. can_lint_syntax must return True.

        """

        can = False
        syntax = syntax.lower()

        if cls.syntax:
            if isinstance(cls.syntax, (tuple, list)):
                can = syntax in cls.syntax
            elif cls.syntax == '*':
                can = True
            elif isinstance(cls.syntax, str):
                can = syntax == cls.syntax
            else:
                can = cls.syntax.match(syntax) is not None

        if can:
            if cls.executable_path is None:
                executable = ''

                if not callable(cls.cmd):
                    if isinstance(cls.cmd, (tuple, list)):
                        executable = (cls.cmd or [''])[0]
                    elif isinstance(cls.cmd, str):
                        executable = cls.cmd

                if not executable and cls.executable:
                    executable = cls.executable

                if executable:
                    cls.executable_path = cls.which(executable) or ''

                    if (
                        cls.executable_path is None or
                        (isinstance(cls.executable_path, (tuple, list)) and None in cls.executable_path)
                    ):
                        cls.executable_path = ''
                elif cls.cmd is None:
                    cls.executable_path = '<builtin>'
                else:
                    cls.executable_path = ''

            status = None

            if cls.executable_path:
                can = cls.fulfills_version_requirement()

                if not can:
                    status = ''  # Warning was already printed

            if can:
                can = cls.can_lint_syntax(syntax)

            if can:
                settings = persist.settings
                disabled = (
                    settings.get('@disabled') or
                    settings.get('linters', {}).get(cls.name, {}).get('@disable', False)
                )
                status = '{} activated: {}{}'.format(
                    cls.name,
                    cls.executable_path,
                    ' (disabled in settings)' if disabled else ''
                )
            elif status is None:
                status = 'WARNING: {} deactivated, cannot locate \'{}\''.format(cls.name, executable)

            if status:
                persist.printf(status)

        return can

    @classmethod
    def can_lint_syntax(cls, syntax):
        """
        Return whether a linter can lint a given syntax.

        Subclasses may override this if the built in mechanism in can_lint
        is not sufficient. When this method is called, cls.executable_path
        has been set. If it is '', that means the executable was not specified
        or could not be found.

        """
        return cls.executable_path != ''

    @classmethod
    def fulfills_version_requirement(cls):
        """
        Return whether the executable fulfills version_requirement.

        When this is called, cls.executable_path has been set.

        """

        cls.executable_version = None

        if cls.executable_path == '<builtin>':
            if callable(getattr(cls, 'get_module_version', None)):
                if not(cls.version_re and cls.version_requirement):
                    return True

                cls.executable_version = cls.get_module_version()

                if cls.executable_version:
                    persist.debug('{} version: {}'.format(cls.name, cls.executable_version))
                else:
                    persist.printf('WARNING: {} unable to determine module version'.format(cls.name))
            else:
                return True
        elif not(cls.version_args is not None and cls.version_re and cls.version_requirement):
            return True

        if cls.executable_version is None:
            cls.executable_version = cls.get_executable_version()

        if cls.executable_version:
            predicate = VersionPredicate(
                '{} ({})'.format(cls.name.replace('-', '.'), cls.version_requirement)
            )

            if predicate.satisfied_by(cls.executable_version):
                persist.debug(
                    '{}: ({}) satisfied by {}'
                    .format(cls.name, cls.version_requirement, cls.executable_version)
                )
                return True
            else:
                persist.printf(
                    'WARNING: {} deactivated, version requirement ({}) not fulfilled by {}'
                    .format(cls.name, cls.version_requirement, cls.executable_version)
                )

        return False

    @classmethod
    def get_executable_version(cls):
        """Extract and return the string version of the linter executable."""

        args = cls.version_args

        if isinstance(args, str):
            args = shlex.split(args)
        else:
            args = list(args)

        if isinstance(cls.executable_path, str):
            cmd = [cls.executable_path]
        else:
            cmd = list(cls.executable_path)

        cmd += args
        persist.debug('{} version query: {}'.format(cls.name, ' '.join(cmd)))

        version = util.communicate(cmd, output_stream=util.STREAM_BOTH)
        match = cls.version_re.search(version)

        if match:
            version = match.group('version')
            persist.debug('{} version: {}'.format(cls.name, version))
            return version
        else:
            persist.printf('WARNING: no {} version could be extracted from:\n{}'.format(cls.name, version))
            return None

    @staticmethod
    def replace_entity(match):
        """Return the character corresponding to an HTML entity."""
        number = match.group(2)

        if number:
            hex = match.group(1) is not None
            result = chr(int(number, 16 if hex else 10))
        else:
            entity = match.group(3)
            result = unescape(entity, html.entities.html5)

        return result

    def error(self, line, col, message, error_type):
        """Add a reference to an error/warning on the given line and column."""
        self.highlight.line(line, error_type)

        # Some linters use html entities in error messages, decode them
        message = HTML_ENTITY_RE.sub(self.replace_entity, message)

        # Strip trailing CR, space and period
        message = ((col or 0), str(message).rstrip('\r .'))

        if line in self.errors:
            self.errors[line].append(message)
        else:
            self.errors[line] = [message]

    def find_errors(self, output):
        """
        A generator which matches the linter's regex against the linter output.

        If multiline is True, split_match is called for each non-overlapping
        match of self.regex. If False, split_match is called for each line
        in output.

        """

        if self.multiline:
            errors = self.regex.finditer(output)

            if errors:
                for error in errors:
                    yield self.split_match(error)
            else:
                yield self.split_match(None)
        else:
            for line in output.splitlines():
                yield self.split_match(self.regex.match(line.rstrip()))

    def split_match(self, match):
        """
        Split a match into the standard elements of an error and return them.

        If subclasses need to modify the values returned by the regex, they
        should override this method, call super(), then modify the values
        and return them.

        """

        if match:
            items = {'line': None, 'col': None, 'error': None, 'warning': None, 'message': '', 'near': None}
            items.update(match.groupdict())
            line, col, error, warning, message, near = [
                items[k] for k in ('line', 'col', 'error', 'warning', 'message', 'near')
            ]

            if line is not None:
                line = int(line) - self.line_col_base[0]

            if col is not None:
                if col.isdigit():
                    col = int(col) - self.line_col_base[1]
                else:
                    col = len(col)

            return match, line, col, error, warning, message, near
        else:
            return match, None, None, None, None, '', None

    def run(self, cmd, code):
        """
        Execute the linter's executable or built in code and return its output.

        If a linter uses built in code, it should override this method and return
        a string as the output.

        If a linter needs to do complicated setup or will use the tmpdir
        method, it will need to override this method.

        """
        if persist.debug_mode():
            persist.printf('{}: {} {}'.format(self.name,
                                              os.path.basename(self.filename or '<unsaved>'),
                                              cmd or '<builtin>'))

        if self.tempfile_suffix:
            if self.tempfile_suffix != '-':
                return self.tmpfile(cmd, code)
            else:
                return self.communicate(cmd)
        else:
            return self.communicate(cmd, code)

    def get_tempfile_suffix(self):
        """Return the mapped tempfile_suffix."""
        if self.tempfile_suffix:
            if isinstance(self.tempfile_suffix, dict):
                suffix = self.tempfile_suffix.get(persist.get_syntax(self.view), self.syntax)
            else:
                suffix = self.tempfile_suffix

            if not suffix.startswith('.'):
                suffix = '.' + suffix

            return suffix
        else:
            return ''

    # popen wrappers

    def communicate(self, cmd, code=''):
        """Run an external executable using stdin to pass code and return its output."""
        if '@' in cmd:
            cmd[cmd.index('@')] = self.filename
        elif not code:
            cmd.append(self.filename)

        return util.communicate(
            cmd,
            code,
            output_stream=self.error_stream,
            env=self.env)

    def tmpfile(self, cmd, code, suffix=''):
        """Run an external executable using a temp file to pass code and return its output."""
        return util.tmpfile(
            cmd,
            code,
            self.filename,
            suffix or self.get_tempfile_suffix(),
            output_stream=self.error_stream,
            env=self.env)

    def tmpdir(self, cmd, files, code):
        """Run an external executable using a temp dir filled with files and return its output."""
        return util.tmpdir(
            cmd,
            files,
            self.filename,
            code,
            output_stream=self.error_stream,
            env=self.env)

    def popen(self, cmd, env=None):
        """Run cmd in a subprocess with the given environment and return the output."""
        return util.popen(
            cmd,
            env=env,
            extra_env=self.env,
            output_stream=self.error_stream)

########NEW FILE########
__FILENAME__ = persist
#
# persist.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module provides persistent global storage for other modules."""

from collections import defaultdict
from copy import deepcopy
import json
import os
import re
import sublime
import sys

from . import util

PLUGIN_NAME = 'SublimeLinter'

# Get the name of the plugin directory, which is the parent of this file's directory
PLUGIN_DIRECTORY = os.path.basename(os.path.dirname(os.path.dirname(__file__)))

LINT_MODES = (
    ('background', 'Lint whenever the text is modified'),
    ('load/save', 'Lint only when a file is loaded or saved'),
    ('save only', 'Lint only when a file is saved'),
    ('manual', 'Lint only when requested')
)

SYNTAX_RE = re.compile(r'(?i)/([^/]+)\.tmLanguage$')

DEFAULT_GUTTER_THEME_PATH = 'Packages/SublimeLinter/gutter-themes/Default/Default.gutter-theme'


class Settings:

    """This class provides global access to and management of plugin settings."""

    def __init__(self):
        """Initialize a new instance."""
        self.settings = {}
        self.previous_settings = {}
        self.changeset = set()
        self.plugin_settings = None
        self.on_update_callback = None

    def load(self, force=False):
        """Load the plugin settings."""
        if force or not self.settings:
            self.observe()
            self.on_update()
            self.observe_prefs()

    def has_setting(self, setting):
        """Return whether the given setting exists."""
        return setting in self.settings

    def get(self, setting, default=None):
        """Return a plugin setting, defaulting to default if not found."""
        return self.settings.get(setting, default)

    def set(self, setting, value, changed=False):
        """
        Set a plugin setting to the given value.

        Clients of this module should always call this method to set a value
        instead of doing settings['foo'] = 'bar'.

        If the caller knows for certain that the value has changed,
        they should pass changed=True.

        """
        self.copy()
        self.settings[setting] = value

        if changed:
            self.changeset.add(setting)

    def pop(self, setting, default=None):
        """
        Remove a given setting and return default if it is not in self.settings.

        Clients of this module should always call this method to pop a value
        instead of doing settings.pop('foo').

        """
        self.copy()
        return self.settings.pop(setting, default)

    def copy(self):
        """Save a copy of the plugin settings."""
        self.previous_settings = deepcopy(self.settings)

    def observe_prefs(self, observer=None):
        """Observe changes to the ST prefs."""
        prefs = sublime.load_settings('Preferences.sublime-settings')
        prefs.clear_on_change('sublimelinter-pref-settings')
        prefs.add_on_change('sublimelinter-pref-settings', observer or self.on_prefs_update)

    def observe(self, observer=None):
        """Observer changes to the plugin settings."""
        self.plugin_settings = sublime.load_settings('SublimeLinter.sublime-settings')
        self.plugin_settings.clear_on_change('sublimelinter-persist-settings')
        self.plugin_settings.add_on_change('sublimelinter-persist-settings',
                                           observer or self.on_update)

    def on_update_call(self, callback):
        """Set a callback to call when user settings are updated."""
        self.on_update_callback = callback

    def on_update(self):
        """
        Update state when the user settings change.

        The settings before the change are compared with the new settings.
        Depending on what changes, views will either be redrawn or relinted.

        """

        settings = util.merge_user_settings(self.plugin_settings)
        self.settings.clear()
        self.settings.update(settings)

        if (
            '@disable' in self.changeset or
            self.previous_settings.get('@disable', False) != self.settings.get('@disable', False)
        ):
            need_relint = True
            self.changeset.discard('@disable')
        else:
            need_relint = False

        # Clear the path-related caches if the paths list has changed
        if (
            'paths' in self.changeset or
            (self.previous_settings and
             self.previous_settings.get('paths') != self.settings.get('paths'))
        ):
            need_relint = True
            util.clear_caches()
            self.changeset.discard('paths')

        # Add python paths if they changed
        if (
            'python_paths' in self.changeset or
            (self.previous_settings and
             self.previous_settings.get('python_paths') != self.settings.get('python_paths'))
        ):
            need_relint = True
            self.changeset.discard('python_paths')
            python_paths = self.settings.get('python_paths', {}).get(sublime.platform(), [])

            for path in python_paths:
                if path not in sys.path:
                    sys.path.append(path)

        # If the syntax map changed, reassign linters to all views
        from .linter import Linter

        if (
            'syntax_map' in self.changeset or
            (self.previous_settings and
             self.previous_settings.get('syntax_map') != self.settings.get('syntax_map'))
        ):
            need_relint = True
            self.changeset.discard('syntax_map')
            Linter.clear_all()
            util.apply_to_all_views(lambda view: Linter.assign(view, reset=True))

        if (
            'no_column_highlights_line' in self.changeset or
            self.previous_settings.get('no_column_highlights_line') != self.settings.get('no_column_highlights_line')
        ):
            need_relint = True
            self.changeset.discard('no_column_highlights_line')

        if (
            'gutter_theme' in self.changeset or
            self.previous_settings.get('gutter_theme') != self.settings.get('gutter_theme')
        ):
            self.changeset.discard('gutter_theme')
            self.update_gutter_marks()

        error_color = self.settings.get('error_color', '')
        warning_color = self.settings.get('warning_color', '')

        if (
            ('error_color' in self.changeset or 'warning_color' in self.changeset) or
            (self.previous_settings and error_color and warning_color and
             (self.previous_settings.get('error_color') != error_color or
              self.previous_settings.get('warning_color') != warning_color))
        ):
            self.changeset.discard('error_color')
            self.changeset.discard('warning_color')

            if (
                sublime.ok_cancel_dialog(
                    'You changed the error and/or warning color. '
                    'Would you like to update the user color schemes '
                    'with the new colors?')
            ):
                util.change_mark_colors(error_color, warning_color)

        # If any other settings changed, relint
        if (self.previous_settings or len(self.changeset) > 0):
            need_relint = True

        self.changeset.clear()

        if need_relint:
            Linter.reload()

        if self.previous_settings and self.on_update_callback:
            self.on_update_callback(need_relint)

    def save(self, view=None):
        """
        Regenerate and save the user settings.

        User settings are updated with the default settings and the defaults
        from every linter, and if the user settings are currently being edited,
        the view is updated.

        """

        self.load()

        # Fill in default linter settings
        settings = self.settings
        linters = settings.pop('linters', {})

        for name, linter in linter_classes.items():
            default = linter.settings().copy()
            default.update(linters.pop(name, {}))

            for key, value in (('@disable', False), ('args', []), ('excludes', [])):
                if key not in default:
                    default[key] = value

            linters[name] = default

        settings['linters'] = linters

        filename = '{}.sublime-settings'.format(PLUGIN_NAME)
        user_prefs_path = os.path.join(sublime.packages_path(), 'User', filename)
        settings_views = []

        if view is None:
            # See if any open views are the user prefs
            for window in sublime.windows():
                for view in window.views():
                    if view.file_name() == user_prefs_path:
                        settings_views.append(view)
        else:
            settings_views = [view]

        if settings_views:
            def replace(edit):
                if not view.is_dirty():
                    j = json.dumps({'user': settings}, indent=4, sort_keys=True)
                    j = j.replace(' \n', '\n')
                    view.replace(edit, sublime.Region(0, view.size()), j)

            for view in settings_views:
                edits[view.id()].append(replace)
                view.run_command('sublimelinter_edit')
                view.run_command('save')
        else:
            user_settings = sublime.load_settings('SublimeLinter.sublime-settings')
            user_settings.set('user', settings)
            sublime.save_settings('SublimeLinter.sublime-settings')

    def on_prefs_update(self):
        """Perform maintenance when the ST prefs are updated."""
        util.generate_color_scheme()

    def update_gutter_marks(self):
        """Update the gutter mark info based on the the current "gutter_theme" setting."""

        theme_path = self.settings.get('gutter_theme', DEFAULT_GUTTER_THEME_PATH)
        theme = os.path.splitext(os.path.basename(theme_path))[0]

        if theme_path.lower() == 'none':
            gutter_marks['warning'] = gutter_marks['error'] = ''
            return

        info = None

        for path in (theme_path, DEFAULT_GUTTER_THEME_PATH):
            try:
                info = sublime.load_resource(path)
                break
            except IOError:
                pass

        if info is not None:
            if theme != 'Default' and os.path.basename(path) == 'Default.gutter-theme':
                printf('cannot find the gutter theme \'{}\', using the default'.format(theme))

            path = os.path.dirname(path)

            for error_type in ('warning', 'error'):
                icon_path = '{}/{}.png'.format(path, error_type)
                gutter_marks[error_type] = icon_path

            try:
                info = json.loads(info)
                colorize = info.get('colorize', False)
            except ValueError:
                colorize = False

            gutter_marks['colorize'] = colorize
        else:
            sublime.error_message(
                'SublimeLinter: cannot find the gutter theme "{}",'
                ' and the default is also not available. '
                'No gutter marks will display.'.format(theme)
            )
            gutter_marks['warning'] = gutter_marks['error'] = ''


if 'plugin_is_loaded' not in globals():
    settings = Settings()

    # A mapping between view ids and errors, which are line:(col, message) dicts
    errors = {}

    # A mapping between view ids and HighlightSets
    highlights = {}

    # A mapping between linter class names and linter classes
    linter_classes = {}

    # A mapping between view ids and a set of linter instances
    view_linters = {}

    # A mapping between view ids and views
    views = {}

    # Every time a view is modified, this is updated with a mapping between a view id
    # and the time of the modification. This is checked at various stages of the linting
    # process. If a view has been modified since the original modification, the
    # linting process stops.
    last_hit_times = {}

    edits = defaultdict(list)

    # Info about the gutter mark icons
    gutter_marks = {'warning': 'Default', 'error': 'Default', 'colorize': True}

    # Whether sys.path has been imported from the system.
    sys_path_imported = False

    # Set to true when the plugin is loaded at startup
    plugin_is_loaded = False


def get_syntax(view):
    """Return the view's syntax or the syntax it is mapped to in the "syntax_map" setting."""
    view_syntax = view.settings().get('syntax', '')
    mapped_syntax = ''

    if view_syntax:
        match = SYNTAX_RE.search(view_syntax)

        if match:
            view_syntax = match.group(1).lower()
            mapped_syntax = settings.get('syntax_map', {}).get(view_syntax, '').lower()
        else:
            view_syntax = ''

    return mapped_syntax or view_syntax


def edit(vid, edit):
    """Perform an operation on a view with the given edit object."""
    callbacks = edits.pop(vid, [])

    for c in callbacks:
        c(edit)


def view_did_close(vid):
    """Remove all references to the given view id in persistent storage."""
    if vid in errors:
        del errors[vid]

    if vid in highlights:
        del highlights[vid]

    if vid in view_linters:
        del view_linters[vid]

    if vid in views:
        del views[vid]

    if vid in last_hit_times:
        del last_hit_times[vid]


def debug_mode():
    """Return whether the "debug" setting is True."""
    return settings.get('debug')


def debug(*args):
    """Print args to the console if the "debug" setting is True."""
    if settings.get('debug'):
        printf(*args)


def printf(*args):
    """Print args to the console, prefixed by the plugin name."""
    print(PLUGIN_NAME + ': ', end='')

    for arg in args:
        print(arg, end=' ')

    print()


def import_sys_path():
    """Import system python 3 sys.path into our sys.path."""
    global sys_path_imported

    if plugin_is_loaded and not sys_path_imported:
        # Make sure the system python 3 paths are available to plugins.
        # We do this here to ensure it is only done once.
        sys.path.extend(util.get_python_paths())
        sys_path_imported = True


def register_linter(linter_class, name, attrs):
    """Add a linter class to our mapping of class names <--> linter classes."""
    if name:
        name = name.lower()
        linter_classes[name] = linter_class

        # By setting the lint_settings to None, they will be set the next
        # time linter_class.settings() is called.
        linter_class.lint_settings = None

        # The sublime plugin API is not available until plugin_loaded is executed
        if plugin_is_loaded:
            settings.load(force=True)

            # If a linter is reloaded, we have to reassign that linter to all views
            from . import linter

            # If the linter had previously been loaded, just reassign that linter
            if name in linter_classes:
                linter_name = name
            else:
                linter_name = None

            for view in views.values():
                linter.Linter.assign(view, linter_name=linter_name)

            printf('{} linter reloaded'.format(name))
        else:
            printf('{} linter loaded'.format(name))

########NEW FILE########
__FILENAME__ = python_linter
#
# python_linter.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module exports the PythonLinter subclass of Linter."""

import importlib
import os
import re

from . import linter, persist, util


class PythonLinter(linter.Linter):

    """
    This Linter subclass provides python-specific functionality.

    Linters that check python should inherit from this class.
    By doing so, they automatically get the following features:

    - comment_re is defined correctly for python.

    - A python shebang is returned as the @python:<version> meta setting.

    - Execution directly via a module method or via an executable.

    If the module attribute is defined and is successfully imported,
    whether it is used depends on the following algorithm:

      - If the cmd attribute specifies @python and ST's python
        satisfies that version, the module will be used. Note that this
        check is done during class construction.

      - If the check_version attribute is False, the module will be used
        because the module is not version-sensitive.

      - If the "@python" setting is set and ST's python satisfies
        that version, the module will be used.

      - Otherwise the executable will be used with the python specified
        in the "@python" setting, the cmd attribute, or the default system
        python.

    """

    SHEBANG_RE = re.compile(r'\s*#!(?:(?:/[^/]+)*[/ ])?python(?P<version>\d(?:\.\d)?)')

    comment_re = r'\s*#'

    # If the linter wants to import a module and run a method directly,
    # it should set this attribute to the module name, suitable for passing
    # to importlib.import_module. During class construction, the named module
    # will be imported, and if successful, the attribute will be replaced
    # with the imported module.
    module = None

    # Some python-based linters are version-sensitive, i.e. the python version
    # they are run with has to match the version of the code they lint.
    # If a linter is version-sensitive, this attribute should be set to True.
    check_version = False

    @staticmethod
    def match_shebang(code):
        """Convert and return a python shebang as a @python:<version> setting."""

        match = PythonLinter.SHEBANG_RE.match(code)

        if match:
            return '@python', match.group('version')
        else:
            return None

    shebang_match = match_shebang

    @classmethod
    def initialize(cls):
        """Perform class-level initialization."""

        super().initialize()
        persist.import_sys_path()
        cls.import_module()

    @classmethod
    def reinitialize(cls):
        """Perform class-level initialization after plugins have been loaded at startup."""

        # Be sure to clear _cmd so that import_module will re-import.
        if hasattr(cls, '_cmd'):
            delattr(cls, '_cmd')

        cls.initialize()

    @classmethod
    def import_module(cls):
        """
        Attempt to import the configured module.

        If it could not be imported, use the executable.

        """

        if hasattr(cls, '_cmd'):
            return

        module = getattr(cls, 'module', None)
        cls._cmd = None
        cmd = cls.cmd
        script = None

        if isinstance(cls.cmd, (list, tuple)):
            cmd = cls.cmd[0]

        if module is not None:
            try:
                module = importlib.import_module(module)
                persist.debug('{} imported {}'.format(cls.name, module))

                # If the linter specifies a python version, check to see
                # if ST's python satisfies that version.
                if cmd and not callable(cmd):
                    match = util.PYTHON_CMD_RE.match(cmd)

                    if match and match.group('version'):
                        version, script = match.group('version', 'script')
                        version = util.find_python(version=version, script=script, module=module)

                        # If we cannot find a python or script of the right version,
                        # we cannot use the module.
                        if version[0] is None or script and version[1] is None:
                            module = None

            except ImportError:
                message = '{}import of {} module in {} failed'

                if cls.check_version:
                    warning = 'WARNING: '
                    message += ', linter will not work with python 3 code'
                else:
                    warning = ''
                    message += ', linter will not run using built in python'

                persist.printf(message.format(warning, module, cls.name))
                module = None

            except Exception as ex:
                persist.printf(
                    'ERROR: unknown exception in {}: {}'
                    .format(cls.name, str(ex))
                )
                module = None

        # If no module was specified, or the module could not be imported,
        # or ST's python does not satisfy the version specified, see if
        # any version of python available satisfies the linter. If not,
        # set the cmd to '' to disable the linter.
        can_lint = True

        if not module and cmd and not callable(cmd):
            match = util.PYTHON_CMD_RE.match(cmd)

            if match and match.group('version'):
                can_lint = False
                version, script = match.group('version', 'script')
                version = util.find_python(version=version, script=script)

                if version[0] is not None and (not script or version[1] is not None):
                    can_lint = True

        if can_lint:
            cls._cmd = cls.cmd

            # If there is a module, setting cmd to None tells us to
            # use the check method.
            if module:
                cls.cmd = None
        else:
            persist.printf(
                'WARNING: {} deactivated, no available version of python{} satisfies {}'
                .format(
                    cls.name,
                    ' or {}'.format(script) if script else '',
                    cmd
                ))

            cls.disabled = True

        cls.module = module

    def context_sensitive_executable_path(self, cmd):
        """
        Calculate the context-sensitive executable path, using @python and check_version.

        Return a tuple of (have_path, path).

        Return have_path == False if not self.check_version.
        Return have_path == True if cmd is in [script]@python[version] form.
        Return None for path if the desired version of python/script cannot be found.
        Return '<builtin>' for path if the built-in python should be used.

        """

        if not self.check_version:
            return False, None

        # Check to see if we have a @python command
        match = util.PYTHON_CMD_RE.match(cmd[0])

        if match:
            settings = self.get_view_settings()

            if '@python' in settings:
                script = match.group('script') or ''
                which = '{}@python{}'.format(script, settings.get('@python'))
                path = self.which(which)

                if path:
                    if path[0] == '<builtin>':
                        return True, '<builtin>'
                    elif path[0] is None or script and path[1] is None:
                        return True, None

                return True, path

        return False, None

    @classmethod
    def get_module_version(cls):
        """
        Return the string version of the imported module, without any prefix/suffix.

        This method handles the common case where a module (or one of its parents)
        defines a __version__ string. For other cases, subclasses should override
        this method and return the version string.

        """

        if cls.module:
            module = cls.module

            while True:
                if isinstance(getattr(module, '__version__', None), str):
                    return module.__version__

                if hasattr(module, '__package__'):
                    try:
                        module = importlib.import_module(module.__package__)
                    except ImportError:
                        return None
        else:
            return None

    def run(self, cmd, code):
        """Run the module checker or executable on code and return the output."""
        if self.module is not None:
            use_module = False

            if not self.check_version:
                use_module = True
            else:
                settings = self.get_view_settings()
                version = settings.get('@python')

                if version is None:
                    use_module = cmd is None or cmd[0] == '<builtin>'
                else:
                    version = util.find_python(version=version, module=self.module)
                    use_module = version[0] == '<builtin>'

            if use_module:
                if persist.debug_mode():
                    persist.printf(
                        '{}: {} <builtin>'.format(
                            self.name,
                            os.path.basename(self.filename or '<unsaved>')
                        )
                    )

                try:
                    errors = self.check(code, os.path.basename(self.filename or '<unsaved>'))
                except Exception as err:
                    persist.printf(
                        'ERROR: exception in {}.check: {}'
                        .format(self.name, str(err))
                    )
                    errors = ''

                if isinstance(errors, (tuple, list)):
                    return '\n'.join([str(e) for e in errors])
                else:
                    return errors
            else:
                cmd = self._cmd
        else:
            cmd = self.cmd or self._cmd

        cmd = self.build_cmd(cmd=cmd)

        if cmd:
            return super().run(cmd, code)
        else:
            return ''

    def check(self, code, filename):
        """
        Run a built-in check of code, returning errors.

        Subclasses that provide built in checking must override this method
        and return a string with one more lines per error, an array of strings,
        or an array of objects that can be converted to strings.

        """

        persist.printf(
            '{}: subclasses must override the PythonLinter.check method'
            .format(self.name)
        )

        return ''

########NEW FILE########
__FILENAME__ = queue
#
# queue.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module provides a threaded queue for lint requests."""

from queue import Queue, Empty
import threading
import traceback
import time

from . import persist, util


class Daemon:

    """
    This class provides a threaded queue that dispatches lints.

    The following operations can be added to the queue:

    hit - Queue a lint for a given view
    delay - Queue a delay for a number of milliseconds
    reload - Indicates the main plugin was reloaded

    """

    MIN_DELAY = 0.1
    running = False
    callback = None
    q = Queue()
    last_runs = {}

    def start(self, callback):
        """Start the daemon thread that runs loop."""
        self.callback = callback

        if self.running:
            self.q.put('reload')
        else:
            self.running = True
            threading.Thread(target=self.loop).start()

    def loop(self):
        """Continually check the queue for new items and process them."""

        last_runs = {}

        while True:
            try:
                try:
                    item = self.q.get(block=True, timeout=self.MIN_DELAY)
                except Empty:
                    for view_id, (timestamp, delay) in last_runs.copy().items():
                        # Lint the view if we have gone past the time
                        # at which the lint wants to run.
                        if time.monotonic() > timestamp + delay:
                            self.last_runs[view_id] = time.monotonic()
                            del last_runs[view_id]
                            self.lint(view_id, timestamp)

                    continue

                if isinstance(item, tuple):
                    view_id, timestamp, delay = item

                    if view_id in self.last_runs and timestamp < self.last_runs[view_id]:
                        continue

                    last_runs[view_id] = timestamp, delay

                elif isinstance(item, (int, float)):
                    time.sleep(item)

                elif isinstance(item, str):
                    if item == 'reload':
                        persist.printf('daemon detected a reload')
                        self.last_runs.clear()
                        last_runs.clear()
                else:
                    persist.printf('unknown message sent to daemon:', item)
            except:
                persist.printf('error in SublimeLinter daemon:')
                persist.printf('-' * 20)
                persist.printf(traceback.format_exc())
                persist.printf('-' * 20)

    def hit(self, view):
        """Add a lint request to the queue, return the time at which the request was enqueued."""
        timestamp = time.monotonic()
        self.q.put((view.id(), timestamp, self.get_delay(view)))
        return timestamp

    def delay(self, milliseconds=100):
        """Add a millisecond delay to the queue."""
        self.q.put(milliseconds / 1000.0)

    def lint(self, view_id, timestamp):
        """
        Call back into the main plugin to lint the given view.

        timestamp is used to determine if the view has been modified
        since the lint was requested.

        """
        self.callback(view_id, timestamp)

    def get_delay(self, view):
        """
        Return the delay between a lint request and when it will be processed.

        If the lint mode is not background, there is no delay. Otherwise, if
        a "delay" setting is not available in any of the settings, MIN_DELAY is used.

        """

        if persist.settings.get('lint_mode') != 'background':
            return 0

        delay = (util.get_view_rc_settings(view) or {}).get('delay')

        if delay is None:
            delay = persist.settings.get('delay', self.MIN_DELAY)

        return delay


queue = Daemon()

########NEW FILE########
__FILENAME__ = ruby_linter
#
# ruby_linter.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module exports the RubyLinter subclass of Linter."""

import os
import re
import shlex

from . import linter, persist, util

CMD_RE = re.compile(r'(?P<gem>.+?)@ruby')


class RubyLinter(linter.Linter):

    """
    This Linter subclass provides ruby-specific functionality.

    Linters that check ruby using gems should inherit from this class.
    By doing so, they automatically get the following features:

    - comment_re is defined correctly for ruby.

    - Support for rbenv and rvm (via rvm-auto-ruby).

    """

    comment_re = r'\s*#'

    @classmethod
    def initialize(cls):
        """Perform class-level initialization."""

        super().initialize()

        if cls.executable_path is not None:
            return

        if not callable(cls.cmd) and cls.cmd:
            cls.executable_path = cls.lookup_executables(cls.cmd)
        elif cls.executable:
            cls.executable_path = cls.lookup_executables(cls.executable)

        if not cls.executable_path:
            cls.disabled = True

    @classmethod
    def reinitialize(cls):
        """Perform class-level initialization after plugins have been loaded at startup."""

        # Be sure to clear cls.executable_path so that lookup_executables will run.
        cls.executable_path = None
        cls.initialize()

    @classmethod
    def lookup_executables(cls, cmd):
        """
        Attempt to locate the gem and ruby specified in cmd, return new cmd list.

        The following forms are valid:

        gem@ruby
        gem
        ruby

        If rbenv is installed and the gem is also under rbenv control,
        the gem will be executed directly. Otherwise [ruby <, gem>] will
        be returned.

        If rvm-auto-ruby is installed, [rvm-auto-ruby <, gem>] will be
        returned.

        Otherwise [ruby] or [gem] will be returned.

        """

        ruby = None
        rbenv = util.which('rbenv')

        if not rbenv:
            ruby = util.which('rvm-auto-ruby')

        if not ruby:
            ruby = util.which('ruby')

        if not rbenv and not ruby:
            persist.printf(
                'WARNING: {} deactivated, cannot locate ruby, rbenv or rvm-auto-ruby'
                .format(cls.name, cmd[0])
            )
            return []

        if isinstance(cmd, str):
            cmd = shlex.split(cmd)

        match = CMD_RE.match(cmd[0])

        if match:
            gem = match.group('gem')
        elif cmd[0] != 'ruby':
            gem = cmd[0]
        else:
            gem = ''

        if gem:
            gem_path = util.which(gem)

            if gem_path:
                if (rbenv and
                    ('{0}.rbenv{0}shims{0}'.format(os.sep) in gem_path or
                     (os.altsep and '{0}.rbenv{0}shims{0}'.format(os.altsep in gem_path)))):
                    ruby_cmd = [gem_path]
                else:
                    ruby_cmd = [ruby, gem_path]
            else:
                persist.printf(
                    'WARNING: {} deactivated, cannot locate the gem \'{}\''
                    .format(cls.name, gem)
                )
                return []
        else:
            ruby_cmd = [ruby]

        if cls.env is None:
            # Don't use GEM_HOME with rbenv, it prevents it from using gem shims
            if rbenv:
                cls.env = {}
            else:
                gem_home = util.get_environment_variable('GEM_HOME')

                if gem_home:
                    cls.env = {'GEM_HOME': gem_home}
                else:
                    cls.env = {}

        return ruby_cmd

########NEW FILE########
__FILENAME__ = util
# coding=utf8
#
# util.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module provides general utility methods."""

from functools import lru_cache
from glob import glob
import json
from numbers import Number
import os
import re
import shutil
from string import Template
import sublime
import subprocess
import sys
import tempfile
from xml.etree import ElementTree

#
# Public constants
#
STREAM_STDOUT = 1
STREAM_STDERR = 2
STREAM_BOTH = STREAM_STDOUT + STREAM_STDERR

PYTHON_CMD_RE = re.compile(r'(?P<script>[^@]+)?@python(?P<version>[\d\.]+)?')
VERSION_RE = re.compile(r'(?P<major>\d+)(?:\.(?P<minor>\d+))?')

INLINE_SETTINGS_RE = re.compile(r'(?i).*?\[sublimelinter[ ]+(?P<settings>[^\]]+)\]')
INLINE_SETTING_RE = re.compile(r'(?P<key>[@\w][\w\-]*)\s*:\s*(?P<value>[^\s]+)')

MENU_INDENT_RE = re.compile(r'^(\s+)\$menus', re.MULTILINE)

MARK_COLOR_RE = (
    r'(\s*<string>sublimelinter\.{}</string>\s*\r?\n'
    r'\s*<key>settings</key>\s*\r?\n'
    r'\s*<dict>\s*\r?\n'
    r'\s*<key>foreground</key>\s*\r?\n'
    r'\s*<string>)#.+?(</string>\s*\r?\n)'
)

ANSI_COLOR_RE = re.compile(r'\033\[[0-9;]*m')

UNSAVED_FILENAME = 'untitled'

# Temp directory used to store temp files for linting
tempdir = os.path.join(tempfile.gettempdir(), 'SublimeLinter3')


# settings utils

def merge_user_settings(settings):
    """Return the default linter settings merged with the user's settings."""

    default = settings.get('default', {})
    user = settings.get('user', {})

    if user:
        linters = default.pop('linters', {})
        user_linters = user.get('linters', {})

        for name, data in user_linters.items():
            if name in linters:
                linters[name].update(data)
            else:
                linters[name] = data

        default['linters'] = linters

        user.pop('linters', None)
        default.update(user)

    return default


def inline_settings(comment_re, code, prefix=None, alt_prefix=None):
    r"""
    Return a dict of inline settings within the first two lines of code.

    This method looks for settings in the form [SublimeLinter <name>:<value>]
    on the first or second line of code if the lines match comment_re.
    comment_re should be a compiled regex object whose pattern is unanchored (no ^)
    and matches everything through the comment prefix, including leading whitespace.

    For example, to specify JavaScript comments, you would use the pattern:

    r'\s*/[/*]'

    If prefix or alt_prefix is a non-empty string, setting names must begin with
    the given prefix or alt_prefix to be considered as a setting.

    A dict of matching name/value pairs is returned.

    """

    if prefix:
        prefix = prefix.lower() + '-'

    if alt_prefix:
        alt_prefix = alt_prefix.lower() + '-'

    settings = {}
    pos = -1

    for i in range(0, 2):
        # Does this line start with a comment marker?
        match = comment_re.match(code, pos + 1)

        if match:
            # If it's a comment, does it have inline settings?
            match = INLINE_SETTINGS_RE.match(code, pos + len(match.group()))

            if match:
                # We have inline settings, stop looking
                break

        # Find the next line
        pos = code.find('\n', )

        if pos == -1:
            # If no more lines, stop looking
            break

    if match:
        for key, value in INLINE_SETTING_RE.findall(match.group('settings')):
            if prefix and key[0] != '@':
                if key.startswith(prefix):
                    key = key[len(prefix):]
                elif alt_prefix and key.startswith(alt_prefix):
                    key = key[len(alt_prefix):]
                else:
                    continue

            settings[key] = value

    return settings


def get_view_rc_settings(view, limit=None):
    """Return the rc settings, starting at the parent directory of the given view."""
    filename = view.file_name()

    if filename:
        return get_rc_settings(os.path.dirname(filename))
    else:
        return None


def get_rc_settings(start_dir, limit=None):
    """
    Search for a file named .sublimelinterrc starting in start_dir.

    From start_dir it ascends towards the root directory for a maximum
    of limit directories (including start_dir). If the file is found,
    it is read as JSON and the resulting object is returned. If the file
    is not found, None is returned.

    """

    if not start_dir:
        return

    path = find_file(start_dir, '.sublimelinterrc', limit=limit)

    if path:
        try:
            with open(path, encoding='utf8') as f:
                rc_settings = json.loads(f.read())

            return rc_settings
        except (OSError, ValueError) as ex:
            from . import persist
            persist.printf('ERROR: could not load \'{}\': {}'.format(path, str(ex)))
    else:
        return None


def generate_color_scheme(from_reload=True):
    """Asynchronously call generate_color_scheme_async."""

    # If this was called from a reload of prefs, turn off the prefs observer,
    # otherwise we'll end up back here when ST updates the prefs with the new color.
    if from_reload:
        from . import persist

        def prefs_reloaded():
            persist.settings.observe_prefs()

        persist.settings.observe_prefs(observer=prefs_reloaded)

    # ST crashes unless this is run async
    sublime.set_timeout_async(generate_color_scheme_async, 0)


def generate_color_scheme_async():
    """
    Generate a modified copy of the current color scheme that contains SublimeLinter color entries.

    from_reload is True if this is called from the change callback for user settings.

    The current color scheme is checked for SublimeLinter color entries. If any are missing,
    the scheme is copied, the entries are added, and the color scheme is rewritten to Packages/User.

    """

    prefs = sublime.load_settings('Preferences.sublime-settings')
    scheme = prefs.get('color_scheme')

    if scheme is None:
        return

    scheme_text = sublime.load_resource(scheme)

    # Ensure that all SublimeLinter colors are in the scheme
    scopes = {
        'mark.warning': False,
        'mark.error': False,
        'gutter-mark': False
    }

    for scope in scopes:
        if re.search(MARK_COLOR_RE.format(re.escape(scope)), scheme_text):
            scopes[scope] = True

    if False not in scopes.values():
        return

    # Append style dicts with our styles to the style array
    plist = ElementTree.XML(scheme_text)
    styles = plist.find('./dict/array')

    from . import persist

    for style in COLOR_SCHEME_STYLES:
        color = persist.settings.get('{}_color'.format(style), DEFAULT_MARK_COLORS[style]).lstrip('#')
        styles.append(ElementTree.XML(COLOR_SCHEME_STYLES[style].format(color)))

    # Write the amended color scheme to Packages/User
    original_name = os.path.splitext(os.path.basename(scheme))[0]
    name = original_name + ' (SL)'
    scheme_path = os.path.join(sublime.packages_path(), 'User', name + '.tmTheme')

    with open(scheme_path, 'w', encoding='utf8') as f:
        f.write(COLOR_SCHEME_PREAMBLE)
        f.write(ElementTree.tostring(plist, encoding='unicode'))

    # Set the amended color scheme to the current color scheme
    path = os.path.join('User', os.path.basename(scheme_path))
    prefs.set('color_scheme', packages_relative_path(path))
    sublime.save_settings('Preferences.sublime-settings')


def change_mark_colors(error_color, warning_color):
    """Change SublimeLinter error/warning colors in user color schemes."""

    error_color = error_color.lstrip('#')
    warning_color = warning_color.lstrip('#')

    path = os.path.join(sublime.packages_path(), 'User', '*.tmTheme')
    themes = glob(path)

    for theme in themes:
        with open(theme, encoding='utf8') as f:
            text = f.read()

        if re.search(MARK_COLOR_RE.format(r'mark\.error'), text):
            text = re.sub(MARK_COLOR_RE.format(r'mark\.error'), r'\1#{}\2'.format(error_color), text)
            text = re.sub(MARK_COLOR_RE.format(r'mark\.warning'), r'\1#{}\2'.format(warning_color), text)

            with open(theme, encoding='utf8', mode='w') as f:
                f.write(text)


def install_syntaxes():
    """Asynchronously call install_syntaxes_async."""
    sublime.set_timeout_async(install_syntaxes_async, 0)


def install_syntaxes_async():
    """
    Install fixed syntax packages.

    Unfortunately the scope definitions in some syntax definitions
    (HTML at the moment) incorrectly define embedded scopes, which leads
    to spurious lint errors.

    This method copies all of the syntax packages in fixed_syntaxes to Packages
    so that they override the built in syntax package.

    """

    from . import persist

    plugin_dir = os.path.dirname(os.path.dirname(__file__))
    syntaxes_dir = os.path.join(plugin_dir, 'fixed-syntaxes')

    for syntax in os.listdir(syntaxes_dir):
        # See if our version of the syntax already exists in Packages
        src_dir = os.path.join(syntaxes_dir, syntax)
        version_file = os.path.join(src_dir, 'sublimelinter.version')

        if not os.path.isdir(src_dir) or not os.path.isfile(version_file):
            continue

        with open(version_file, encoding='utf8') as f:
            my_version = int(f.read().strip())

        dest_dir = os.path.join(sublime.packages_path(), syntax)
        version_file = os.path.join(dest_dir, 'sublimelinter.version')

        if os.path.isdir(dest_dir):
            if os.path.isfile(version_file):
                with open(version_file, encoding='utf8') as f:
                    try:
                        other_version = int(f.read().strip())
                    except ValueError:
                        other_version = 0

                persist.debug('found existing {} syntax, version {}'.format(syntax, other_version))
                copy = my_version > other_version
            else:
                copy = sublime.ok_cancel_dialog(
                    'An existing {} syntax definition exists, '.format(syntax) +
                    'and SublimeLinter wants to overwrite it with its own version. ' +
                    'Is that okay?')

        else:
            copy = True

        if copy:
            copy_syntax(syntax, src_dir, my_version, dest_dir)

    update_syntax_map()


def copy_syntax(syntax, src_dir, version, dest_dir):
    """Copy a customized syntax and related files to Packages."""
    from . import persist

    try:
        cached = os.path.join(sublime.cache_path(), syntax)

        if os.path.isdir(cached):
            shutil.rmtree(cached)

        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)

        for filename in os.listdir(src_dir):
            shutil.copy2(os.path.join(src_dir, filename), dest_dir)

        persist.printf('copied {} syntax version {}'.format(syntax, version))
    except OSError as ex:
        persist.printf(
            'ERROR: could not copy {} syntax package: {}'
            .format(syntax, str(ex))
        )


def update_syntax_map():
    """Update the user syntax_map setting with any missing entries from the defaults."""

    from . import persist

    syntax_map = {}
    syntax_map.update(persist.settings.get('syntax_map', {}))
    default_syntax_map = persist.settings.plugin_settings.get('default', {}).get('syntax_map', {})
    modified = False

    for key, value in default_syntax_map.items():
        if key not in syntax_map:
            syntax_map[key] = value
            modified = True
            persist.debug('added syntax mapping: \'{}\' => \'{}\''.format(key, value))

    if modified:
        persist.settings.set('syntax_map', syntax_map)
        persist.settings.save()


# menu utils

def indent_lines(text, indent):
    """Return all of the lines in text indented by prefixing with indent."""
    return re.sub(r'^', indent, text, flags=re.MULTILINE)[len(indent):]


def generate_menus(**kwargs):
    """Asynchronously call generate_menus_async."""
    sublime.set_timeout_async(generate_menus_async, 0)


def generate_menus_async():
    """
    Generate context and Tools SublimeLinter menus.

    This is done dynamically so that we can have a submenu with all
    of the available gutter themes.

    """

    commands = []

    for chooser in CHOOSERS:
        commands.append({
            'caption': chooser,
            'menus': build_submenu(chooser),
            'toggleItems': ''
        })

    menus = []
    indent = MENU_INDENT_RE.search(CHOOSER_MENU).group(1)

    for cmd in commands:
        # Indent the commands to where they want to be in the template.
        # The first line doesn't need to be indented, remove the extra indent.
        cmd['menus'] = indent_lines(cmd['menus'], indent)

        if cmd['caption'] in TOGGLE_ITEMS:
            cmd['toggleItems'] = TOGGLE_ITEMS[cmd['caption']]
            cmd['toggleItems'] = indent_lines(cmd['toggleItems'], indent)

        menus.append(Template(CHOOSER_MENU).safe_substitute(cmd))

    menus = ',\n'.join(menus)
    text = generate_menu('Context', menus)
    generate_menu('Main', text)


def generate_menu(name, menu_text):
    """Generate and return a sublime-menu from a template."""

    from . import persist
    plugin_dir = os.path.join(sublime.packages_path(), persist.PLUGIN_DIRECTORY)
    path = os.path.join(plugin_dir, '{}.sublime-menu.template'.format(name))

    with open(path, encoding='utf8') as f:
        template = f.read()

    # Get the indent for the menus within the template,
    # indent the chooser menus except for the first line.
    indent = MENU_INDENT_RE.search(template).group(1)
    menu_text = indent_lines(menu_text, indent)

    text = Template(template).safe_substitute({'menus': menu_text})
    path = os.path.join(plugin_dir, '{}.sublime-menu'.format(name))

    with open(path, mode='w', encoding='utf8') as f:
        f.write(text)

    return text


def build_submenu(caption):
    """Generate and return a submenu with commands to select a lint mode, mark style, or gutter theme."""

    setting = caption.lower()

    if setting == 'lint mode':
        from . import persist
        names = [mode[0].capitalize() for mode in persist.LINT_MODES]
    elif setting == 'mark style':
        from . import highlight
        names = highlight.mark_style_names()

    commands = []

    for name in names:
        commands.append(CHOOSER_COMMAND.format(setting.replace(' ', '_'), name))

    return ',\n'.join(commands)


# file/directory/environment utils

def climb(start_dir, limit=None):
    """
    Generate directories, starting from start_dir.

    If limit is None or <= 0, stop at the root directory.
    Otherwise return a maximum of limit directories.

    """

    right = True

    while right and (limit is None or limit > 0):
        yield start_dir
        start_dir, right = os.path.split(start_dir)

        if limit is not None:
            limit -= 1


def find_file(start_dir, name, parent=False, limit=None, aux_dirs=[]):
    """
    Find the given file by searching up the file hierarchy from start_dir.

    If the file is found and parent is False, returns the path to the file.
    If parent is True the path to the file's parent directory is returned.

    If limit is None or <= 0, the search will continue up to the root directory.
    Otherwise a maximum of limit directories will be checked.

    If aux_dirs is not empty and the file hierarchy search failed,
    those directories are also checked.

    """

    for d in climb(start_dir, limit=limit):
        target = os.path.join(d, name)

        if os.path.exists(target):
            if parent:
                return d

            return target

    for d in aux_dirs:
        d = os.path.expanduser(d)
        target = os.path.join(d, name)

        if os.path.exists(target):
            if parent:
                return d

            return target


def run_shell_cmd(cmd):
    """Run a shell command and return stdout."""
    proc = popen(cmd, env=os.environ)
    from . import persist

    try:
        timeout = persist.settings.get('shell_timeout', 10)
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out = b''
        persist.printf('shell timed out after {} seconds, executing {}'.format(timeout, cmd))

    return out


def extract_path(cmd, delim=':'):
    """Return the user's PATH as a colon-delimited list."""
    from . import persist
    persist.debug('user shell:', cmd[0])

    out = run_shell_cmd(cmd).decode()
    path = out.split('__SUBL_PATH__', 2)

    if len(path) > 1:
        path = path[1]
        return ':'.join(path.strip().split(delim))
    else:
        persist.printf('Could not parse shell PATH output:\n' + (out if out else '<empty>'))
        sublime.error_message(
            'SublimeLinter could not determine your shell PATH. '
            'It is unlikely that any linters will work. '
            '\n\n'
            'Please see the troubleshooting guide for info on how to debug PATH problems.')
        return ''


def get_shell_path(env):
    """
    Return the user's shell PATH using shell --login.

    This method is only used on Posix systems.

    """

    if 'SHELL' in env:
        shell_path = env['SHELL']
        shell = os.path.basename(shell_path)

        # We have to delimit the PATH output with markers because
        # text might be output during shell startup.
        if shell in ('bash', 'zsh'):
            return extract_path(
                (shell_path, '-l', '-c', 'echo "__SUBL_PATH__${PATH}__SUBL_PATH__"')
            )
        elif shell == 'fish':
            return extract_path(
                (shell_path, '-l', '-c', 'echo "__SUBL_PATH__"; for p in $PATH; echo $p; end; echo "__SUBL_PATH__"'),
                '\n'
            )
        else:
            from . import persist
            persist.printf('Using an unsupported shell:', shell)

    # guess PATH if we haven't returned yet
    split = env['PATH'].split(':')
    p = env['PATH']

    for path in (
        '/usr/bin', '/usr/local/bin',
        '/usr/local/php/bin', '/usr/local/php5/bin'
    ):
        if path not in split:
            p += (':' + path)

    return p


@lru_cache(maxsize=None)
def get_environment_variable(name):
    """Return the value of the given environment variable, or None if not found."""

    if os.name == 'posix':
        value = None

        if 'SHELL' in os.environ:
            shell_path = os.environ['SHELL']

            # We have to delimit the output with markers because
            # text might be output during shell startup.
            out = run_shell_cmd((shell_path, '-l', '-c', 'echo "__SUBL_VAR__${{{}}}__SUBL_VAR__"'.format(name))).strip()

            if out:
                value = out.decode().split('__SUBL_VAR__', 2)[1].strip() or None
    else:
        value = os.environ.get(name, None)

    from . import persist
    persist.debug('ENV[\'{}\'] = \'{}\''.format(name, value))

    return value


def get_path_components(path):
    """Split a file path into its components and return the list of components."""
    components = []

    while path:
        head, tail = os.path.split(path)

        if tail:
            components.insert(0, tail)

        if head:
            if head == os.path.sep or head == os.path.altsep:
                components.insert(0, head)
                break

            path = head
        else:
            break

    return components


def packages_relative_path(path, prefix_packages=True):
    """
    Return a Packages-relative version of path with '/' as the path separator.

    Sublime Text wants Packages-relative paths used in settings and in the plugin API
    to use '/' as the path separator on all platforms. This method converts platform
    path separators to '/'. If insert_packages = True, 'Packages' is prefixed to the
    converted path.

    """

    components = get_path_components(path)

    if prefix_packages and components and components[0] != 'Packages':
        components.insert(0, 'Packages')

    return '/'.join(components)


@lru_cache(maxsize=None)
def create_environment():
    """
    Return a dict with os.environ augmented with a better PATH.

    On Posix systems, the user's shell PATH is added to PATH.

    Platforms paths are then added to PATH by getting the
    "paths" user settings for the current platform. If "paths"
    has a "*" item, it is added to PATH on all platforms.

    """

    from . import persist

    env = {}
    env.update(os.environ)

    if os.name == 'posix':
        env['PATH'] = get_shell_path(os.environ)

    paths = persist.settings.get('paths', {})

    if sublime.platform() in paths:
        paths = convert_type(paths[sublime.platform()], [])
    else:
        paths = []

    if paths:
        env['PATH'] = os.pathsep.join(paths) + os.pathsep + env['PATH']

    from . import persist

    if persist.debug_mode():
        if os.name == 'posix':
            if 'SHELL' in env:
                shell = 'using ' + env['SHELL']
            else:
                shell = 'using standard paths'
        else:
            shell = 'from system'

        if env['PATH']:
            persist.printf('computed PATH {}:\n{}\n'.format(shell, env['PATH'].replace(os.pathsep, '\n')))

    # Many linters use stdin, and we convert text to utf-8
    # before sending to stdin, so we have to make sure stdin
    # in the target executable is looking for utf-8. Some
    # linters (like ruby) need to have LANG and/or LC_CTYPE
    # set as well.
    env['PYTHONIOENCODING'] = 'utf8'
    env['LANG'] = 'en_US.UTF-8'
    env['LC_CTYPE'] = 'en_US.UTF-8'

    return env


def can_exec(path):
    """Return whether the given path is a file and is executable."""
    return os.path.isfile(path) and os.access(path, os.X_OK)


@lru_cache(maxsize=None)
def which(cmd, module=None):
    """
    Return the full path to the given command, or None if not found.

    If cmd is in the form [script]@python[version], find_python is
    called to locate the appropriate version of python. The result
    is a tuple of the full python path and the full path to the script
    (or None if there is no script).

    """

    match = PYTHON_CMD_RE.match(cmd)

    if match:
        args = match.groupdict()
        args['module'] = module
        return find_python(**args)[0:2]
    else:
        return find_executable(cmd)


def extract_major_minor_version(version):
    """Extract and return major and minor versions from a string version."""

    match = VERSION_RE.match(version)

    if match:
        return {key: int(value) if value is not None else None for key, value in match.groupdict().items()}
    else:
        return {'major': None, 'minor': None}


@lru_cache(maxsize=None)
def get_python_version(path):
    """Return a dict with the major/minor version of the python at path."""

    try:
        # Different python versions use different output streams, so check both
        output = communicate((path, '-V'), '', output_stream=STREAM_BOTH)

        # 'python -V' returns 'Python <version>', extract the version number
        return extract_major_minor_version(output.split(' ')[1])
    except Exception as ex:
        from . import persist
        persist.printf(
            'ERROR: an error occurred retrieving the version for {}: {}'
            .format(path, str(ex)))

        return {'major': None, 'minor': None}


@lru_cache(maxsize=None)
def find_python(version=None, script=None, module=None):
    """
    Return the path to and version of python and an optional related script.

    If not None, version should be a string/numeric version of python to locate, e.g.
    '3' or '3.3'. Only major/minor versions are examined. This method then does
    its best to locate a version of python that satisfies the requested version.
    If module is not None, Sublime Text's python version is tested against the
    requested version.

    If version is None, the path to the default system python is used, unless
    module is not None, in which case '<builtin>' is returned.

    If not None, script should be the name of a python script that is typically
    installed with easy_install or pip, e.g. 'pep8' or 'pyflakes'.

    A tuple of the python path, script path, major version, minor version is returned.

    """

    from . import persist
    persist.debug(
        'find_python(version={!r}, script={!r}, module={!r})'
        .format(version, script, module)
    )

    path = None
    script_path = None

    requested_version = {'major': None, 'minor': None}

    if module is None:
        available_version = {'major': None, 'minor': None}
    else:
        available_version = {
            'major': sys.version_info.major,
            'minor': sys.version_info.minor
        }

    if version is None:
        # If no specific version is requested and we have a module,
        # assume the linter will run using ST's python.
        if module is not None:
            result = ('<builtin>', script, available_version['major'], available_version['minor'])
            persist.debug('find_python: <=', repr(result))
            return result

        # No version was specified, get the default python
        path = find_executable('python')
        persist.debug('find_python: default python =', path)
    else:
        version = str(version)
        requested_version = extract_major_minor_version(version)
        persist.debug('find_python: requested version =', repr(requested_version))

        # If there is no module, we will use a system python.
        # If there is a module, a specific version was requested,
        # and the builtin version does not fulfill the request,
        # use the system python.
        if module is None:
            need_system_python = True
        else:
            persist.debug('find_python: available version =', repr(available_version))
            need_system_python = not version_fulfills_request(available_version, requested_version)
            path = '<builtin>'

        if need_system_python:
            if sublime.platform() in ('osx', 'linux'):
                path = find_posix_python(version)
            else:
                path = find_windows_python(version)

            persist.debug('find_python: system python =', path)

    if path and path != '<builtin>':
        available_version = get_python_version(path)
        persist.debug('find_python: available version =', repr(available_version))

        if version_fulfills_request(available_version, requested_version):
            if script:
                script_path = find_python_script(path, script)
                persist.debug('find_python: {!r} path = {}'.format(script, script_path))

                if script_path is None:
                    path = None
        else:
            path = script_path = None

    result = (path, script_path, available_version['major'], available_version['minor'])
    persist.debug('find_python: <=', repr(result))
    return result


def version_fulfills_request(available_version, requested_version):
    """
    Return whether available_version fulfills requested_version.

    Both are dicts with 'major' and 'minor' items.

    """

    # No requested major version is fulfilled by anything
    if requested_version['major'] is None:
        return True

    # If major version is requested, that at least must match
    if requested_version['major'] != available_version['major']:
        return False

    # Major version matches, if no requested minor version it's a match
    if requested_version['minor'] is None:
        return True

    # If a minor version is requested, the available minor version must be >=
    return (
        available_version['minor'] is not None and
        available_version['minor'] >= requested_version['minor']
    )


@lru_cache(maxsize=None)
def find_posix_python(version):
    """Find the nearest version of python and return its path."""

    from . import persist

    if version:
        # Try the exact requested version first
        path = find_executable('python' + version)
        persist.debug('find_posix_python: python{} => {}'.format(version, path))

        # If that fails, try the major version
        if not path:
            path = find_executable('python' + version[0])
            persist.debug('find_posix_python: python{} => {}'.format(version[0], path))

            # If the major version failed, see if the default is available
            if not path:
                path = find_executable('python')
                persist.debug('find_posix_python: python =>', path)
    else:
        path = find_executable('python')
        persist.debug('find_posix_python: python =>', path)

    return path


@lru_cache(maxsize=None)
def find_windows_python(version):
    """Find the nearest version of python and return its path."""

    if version:
        # On Windows, there may be no separately named python/python3 binaries,
        # so it seems the only reliable way to check for a given version is to
        # check the root drive for 'Python*' directories, and try to match the
        # version based on the directory names. The 'Python*' directories end
        # with the <major><minor> version number, so for matching with the version
        # passed in, strip any decimal points.
        stripped_version = version.replace('.', '')
        prefix = os.path.abspath('\\Python')
        prefix_len = len(prefix)
        dirs = glob(prefix + '*')
        from . import persist

        # Try the exact version first, then the major version
        for version in (stripped_version, stripped_version[0]):
            for python_dir in dirs:
                path = os.path.join(python_dir, 'python.exe')
                python_version = python_dir[prefix_len:]
                persist.debug('find_windows_python: matching =>', path)

                # Try the exact version first, then the major version
                if python_version.startswith(version) and can_exec(path):
                    persist.debug('find_windows_python: <=', path)
                    return path

    # No version or couldn't find a version match, try the default python
    path = find_executable('python')
    persist.debug('find_windows_python: <=', path)
    return path


@lru_cache(maxsize=None)
def find_python_script(python_path, script):
    """Return the path to the given script, or None if not found."""
    if sublime.platform() in ('osx', 'linux'):
        return which(script)
    else:
        # On Windows, scripts are .py files in <python directory>/Scripts
        script_path = os.path.join(os.path.dirname(python_path), 'Scripts', script + '-script.py')

        if os.path.exists(script_path):
            return script_path
        else:
            return None


@lru_cache(maxsize=None)
def get_python_paths():
    """
    Return sys.path for the system version of python 3.

    If python 3 cannot be found on the system, [] is returned.

    """

    from . import persist

    python_path = which('@python3')[0]

    if python_path:
        code = r'import sys;print("\n".join(sys.path).strip())'
        out = communicate(python_path, code)
        paths = out.splitlines()

        if persist.debug_mode():
            persist.printf('sys.path for {}:\n{}\n'.format(python_path, '\n'.join(paths)))
    else:
        persist.debug('no python 3 available to augment sys.path')
        paths = []

    return paths


@lru_cache(maxsize=None)
def find_executable(executable):
    """
    Return the path to the given executable, or None if not found.

    create_environment is used to augment PATH before searching
    for the executable.

    """

    env = create_environment()

    for base in env.get('PATH', '').split(os.pathsep):
        path = os.path.join(os.path.expanduser(base), executable)

        # On Windows, if path does not have an extension, try .exe, .cmd, .bat
        if sublime.platform() == 'windows' and not os.path.splitext(path)[1]:
            for extension in ('.exe', '.cmd', '.bat'):
                path_ext = path + extension

                if can_exec(path_ext):
                    return path_ext
        elif can_exec(path):
            return path

    return None


def touch(path):
    """Perform the equivalent of touch on Posix systems."""
    with open(path, 'a'):
        os.utime(path, None)


def open_directory(path):
    """Open the directory at the given path in a new window."""

    cmd = (get_subl_executable_path(), path)
    subprocess.Popen(cmd, cwd=path)


def get_subl_executable_path():
    """Return the path to the subl command line binary."""

    executable_path = sublime.executable_path()

    if sublime.platform() == 'osx':
        suffix = '.app/'
        app_path = executable_path[:executable_path.rfind(suffix) + len(suffix)]
        executable_path = app_path + 'Contents/SharedSupport/bin/subl'

    return executable_path


# popen utils

def combine_output(out, sep=''):
    """Return stdout and/or stderr combined into a string, stripped of ANSI colors."""
    output = sep.join((
        (out[0].decode('utf8') or '') if out[0] else '',
        (out[1].decode('utf8') or '') if out[1] else '',
    ))

    return ANSI_COLOR_RE.sub('', output)


def communicate(cmd, code='', output_stream=STREAM_STDOUT, env=None):
    """
    Return the result of sending code via stdin to an executable.

    The result is a string which comes from stdout, stderr or the
    combining of the two, depending on the value of output_stream.
    If env is not None, it is merged with the result of create_environment.

    """

    out = popen(cmd, output_stream=output_stream, extra_env=env)

    if out is not None:
        code = code.encode('utf8')
        out = out.communicate(code)
        return combine_output(out)
    else:
        return ''


def create_tempdir():
    """Create a directory within the system temp directory used to create temp files."""
    if os.path.isdir(tempdir):
        shutil.rmtree(tempdir)

    os.mkdir(tempdir)
    from . import persist
    persist.debug('temp directory:', tempdir)


def tmpfile(cmd, code, filename, suffix='', output_stream=STREAM_STDOUT, env=None):
    """
    Return the result of running an executable against a temporary file containing code.

    It is assumed that the executable launched by cmd can take one more argument
    which is a filename to process.

    The result is a string combination of stdout and stderr.
    If env is not None, it is merged with the result of create_environment.

    """

    if not filename:
        filename = UNSAVED_FILENAME
    else:
        filename = os.path.basename(filename)

    if suffix:
        filename = os.path.splitext(filename)[0] + suffix

    path = os.path.join(tempdir, filename)

    try:
        with open(path, mode='wb') as f:
            if isinstance(code, str):
                code = code.encode('utf-8')

            f.write(code)
            f.flush()

        cmd = list(cmd)

        if '@' in cmd:
            cmd[cmd.index('@')] = path
        else:
            cmd.append(path)

        out = popen(cmd, output_stream=output_stream, extra_env=env)

        if out:
            out = out.communicate()
            return combine_output(out)
        else:
            return ''
    finally:
        os.remove(path)


def tmpdir(cmd, files, filename, code, output_stream=STREAM_STDOUT, env=None):
    """
    Run an executable against a temporary file containing code.

    It is assumed that the executable launched by cmd can take one more argument
    which is a filename to process.

    Returns a string combination of stdout and stderr.
    If env is not None, it is merged with the result of create_environment.

    """

    filename = os.path.basename(filename) if filename else ''
    out = None

    with tempfile.TemporaryDirectory(dir=tempdir) as d:
        for f in files:
            try:
                os.makedirs(os.path.join(d, os.path.dirname(f)))
            except OSError:
                pass

            target = os.path.join(d, f)

            if os.path.basename(target) == filename:
                # source file hasn't been saved since change, so update it from our live buffer
                f = open(target, 'wb')

                if isinstance(code, str):
                    code = code.encode('utf8')

                f.write(code)
                f.close()
            else:
                shutil.copyfile(f, target)

        os.chdir(d)
        out = popen(cmd, output_stream=output_stream, extra_env=env)

        if out:
            out = out.communicate()
            out = combine_output(out, sep='\n')

            # filter results from build to just this filename
            # no guarantee all syntaxes are as nice about this as Go
            # may need to improve later or just defer to communicate()
            out = '\n'.join([
                line for line in out.split('\n') if filename in line.split(':', 1)[0]
            ])
        else:
            out = ''

    return out or ''


def popen(cmd, output_stream=STREAM_BOTH, env=None, extra_env=None):
    """Open a pipe to an external process and return a Popen object."""

    info = None

    if os.name == 'nt':
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE

    if output_stream == STREAM_BOTH:
        stdout = stderr = subprocess.PIPE
    elif output_stream == STREAM_STDOUT:
        stdout = subprocess.PIPE
        stderr = subprocess.DEVNULL
    else:  # STREAM_STDERR
        stdout = subprocess.DEVNULL
        stderr = subprocess.PIPE

    if env is None:
        env = create_environment()

    if extra_env is not None:
        env.update(extra_env)

    try:
        return subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=stdout, stderr=stderr,
            startupinfo=info, env=env)
    except Exception as err:
        from . import persist
        persist.printf('ERROR: could not launch', repr(cmd))
        persist.printf('reason:', str(err))
        persist.printf('PATH:', env.get('PATH', ''))


# view utils

def apply_to_all_views(callback):
    """Apply callback to all views in all windows."""
    for window in sublime.windows():
        for view in window.views():
            callback(view)


# misc utils

def clear_caches():
    """Clear the caches of all methods in this module that use an lru_cache."""
    create_environment.cache_clear()
    which.cache_clear()
    find_python.cache_clear()
    get_python_paths.cache_clear()
    find_executable.cache_clear()


def convert_type(value, type_value, sep=None, default=None):
    """
    Convert value to the type of type_value.

    If the value cannot be converted to the desired type, default is returned.
    If sep is not None, strings are split by sep (plus surrounding whitespace)
    to make lists/tuples, and tuples/lists are joined by sep to make strings.

    """

    if type_value is None or isinstance(value, type(type_value)):
        return value

    if isinstance(value, str):
        if isinstance(type_value, (tuple, list)):
            if sep is None:
                return [value]
            else:
                if value:
                    return re.split(r'\s*{}\s*'.format(sep), value)
                else:
                    return []
        elif isinstance(type_value, Number):
            return float(value)
        else:
            return default

    if isinstance(value, Number):
        if isinstance(type_value, str):
            return str(value)
        elif isinstance(type_value, (tuple, list)):
            return [value]
        else:
            return default

    if isinstance(value, (tuple, list)):
        if isinstance(type_value, str):
            return sep.join(value)
        else:
            return list(value)

    return default


def get_user_fullname():
    """Return the user's full name (or at least first name)."""

    if sublime.platform() in ('osx', 'linux'):
        import pwd
        return pwd.getpwuid(os.getuid()).pw_gecos
    else:
        return os.environ.get('USERNAME', 'Me')


def center_region_in_view(region, view):
    """
    Center the given region in view.

    There is a bug in ST3 that prevents a selection change
    from being drawn when a quick panel is open unless the
    viewport moves. So we get the current viewport position,
    move it down 1.0, center the region, see if the viewport
    moved, and if not, move it up 1.0 and center again.

    """

    x1, y1 = view.viewport_position()
    view.set_viewport_position((x1, y1 + 1.0))
    view.show_at_center(region)
    x2, y2 = view.viewport_position()

    if y2 == y1:
        view.set_viewport_position((x1, y1 - 1.0))
        view.show_at_center(region)


# color-related constants

DEFAULT_MARK_COLORS = {'warning': 'EDBA00', 'error': 'DA2000', 'gutter': 'FFFFFF'}

COLOR_SCHEME_PREAMBLE = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
'''

COLOR_SCHEME_STYLES = {
    'warning': '''
        <dict>
            <key>name</key>
            <string>SublimeLinter Warning</string>
            <key>scope</key>
            <string>sublimelinter.mark.warning</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>#{}</string>
            </dict>
        </dict>
    ''',

    'error': '''
        <dict>
            <key>name</key>
            <string>SublimeLinter Error</string>
            <key>scope</key>
            <string>sublimelinter.mark.error</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>#{}</string>
            </dict>
        </dict>
    ''',

    'gutter': '''
        <dict>
            <key>name</key>
            <string>SublimeLinter Gutter Mark</string>
            <key>scope</key>
            <string>sublimelinter.gutter-mark</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>#FFFFFF</string>
            </dict>
        </dict>
    '''
}


# menu command constants

CHOOSERS = (
    'Lint Mode',
    'Mark Style'
)

CHOOSER_MENU = '''{
    "caption": "$caption",
    "children":
    [
        $menus,
        $toggleItems
    ]
}'''

CHOOSER_COMMAND = '''{{
    "command": "sublimelinter_choose_{}", "args": {{"value": "{}"}}
}}'''

TOGGLE_ITEMS = {
    'Mark Style': '''
{
    "caption": "-"
},
{
    "caption": "No Column Highlights Line",
    "command": "sublimelinter_toggle_setting", "args":
    {
        "setting": "no_column_highlights_line",
        "checked": true
    }
}'''
}

########NEW FILE########
__FILENAME__ = linter
#
# linter.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by __user__
# Copyright (c) __year__ __user__
#
# License: MIT
#

"""This module exports the __class__ plugin class."""

from SublimeLinter.lint import __superclass__, util


class __class__(__superclass__):

    """Provides an interface to __linter__."""

    syntax = ''
    cmd = '__cmd__'
    executable = None
    version_args = '--version'
    version_re = r'(?P<version>\d+\.\d+\.\d+)'
    version_requirement = '>= 1.0'
    regex = r''
    multiline = False
    line_col_base = (1, 1)
    tempfile_suffix = None
    error_stream = util.STREAM_BOTH
    selectors = {}
    word_re = None
    defaults = {}
    inline_settings = None
    inline_overrides = None
    __extra_attributes__
########NEW FILE########
__FILENAME__ = sublimelinter
#
# sublimelinter.py
# Part of SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Ryan Hileman and Aparajita Fishman
#
# Project: https://github.com/SublimeLinter/SublimeLinter3
# License: MIT
#

"""This module provides the SublimeLinter plugin class and supporting methods."""

import os
import re

import sublime
import sublime_plugin

from .lint.linter import Linter
from .lint.highlight import HighlightSet
from .lint.queue import queue
from .lint import persist, util


def plugin_loaded():
    """The ST3 entry point for plugins."""

    persist.plugin_is_loaded = True
    persist.settings.load()
    persist.printf('debug mode:', 'on' if persist.debug_mode() else 'off')
    util.create_tempdir()

    for linter in persist.linter_classes.values():
        linter.initialize()

    plugin = SublimeLinter.shared_plugin()
    queue.start(plugin.lint)

    util.generate_menus()
    util.generate_color_scheme(from_reload=False)
    util.install_syntaxes()

    persist.settings.on_update_call(SublimeLinter.on_settings_updated)

    # This ensures we lint the active view on a fresh install
    window = sublime.active_window()

    if window:
        plugin.on_activated(window.active_view())


class SublimeLinter(sublime_plugin.EventListener):

    """The main ST3 plugin class."""

    # We use this to match linter settings filenames.
    LINTER_SETTINGS_RE = re.compile('^SublimeLinter(-.+?)?\.sublime-settings')

    shared_instance = None

    @classmethod
    def shared_plugin(cls):
        """Return the plugin instance."""
        return cls.shared_instance

    def __init__(self, *args, **kwargs):
        """Initialize a new instance."""
        super().__init__(*args, **kwargs)

        # Keeps track of which views we have assigned linters to
        self.loaded_views = set()

        # Keeps track of which views have actually been linted
        self.linted_views = set()

        # A mapping between view ids and syntax names
        self.view_syntax = {}

        self.__class__.shared_instance = self

    @classmethod
    def lint_all_views(cls):
        """Simulate a modification of all views, which will trigger a relint."""

        def apply(view):
            if view.id() in persist.view_linters:
                cls.shared_instance.hit(view)

        util.apply_to_all_views(apply)

    def lint(self, view_id, hit_time=None, callback=None):
        """
        Lint the view with the given id.

        This method is called asynchronously by persist.Daemon when a lint
        request is pulled off the queue, or called synchronously when the
        Lint command is executed or a file is saved and Show Errors on Save
        is enabled.

        If provided, hit_time is the time at which the lint request was added
        to the queue. It is used to determine if the view has been modified
        since the lint request was queued. If so, the lint is aborted, since
        another lint request is already in the queue.

        callback is the method to call when the lint is finished. If not
        provided, it defaults to highlight().

        """

        # If the view has been modified since the lint was triggered,
        # don't lint again.
        if hit_time is not None and persist.last_hit_times.get(view_id, 0) > hit_time:
            return

        view = Linter.get_view(view_id)

        if view is None:
            return

        filename = view.file_name()
        code = Linter.text(view)
        callback = callback or self.highlight
        Linter.lint_view(view, filename, code, hit_time, callback)

    def highlight(self, view, linters, hit_time):
        """
        Highlight any errors found during a lint of the given view.

        This method is called by Linter.lint_view after linting is finished.

        linters is a list of the linters that ran. hit_time has the same meaning
        as in lint(), and if the view was modified since the lint request was
        made, this method aborts drawing marks.

        If the view has not been modified since hit_time, all of the marks and
        errors from the list of linters are aggregated and drawn, and the status
        is updated.

        """

        vid = view.id()

        # If the view has been modified since the lint was triggered,
        # don't draw marks.
        if hit_time is not None and persist.last_hit_times.get(vid, 0) > hit_time:
            return

        errors = {}
        highlights = persist.highlights[vid] = HighlightSet()

        for linter in linters:
            if linter.highlight:
                highlights.add(linter.highlight)

            if linter.errors:
                for line, errs in linter.errors.items():
                    errors.setdefault(line, []).extend(errs)

        # Keep track of one view in each window that shares view's buffer
        window_views = {}
        buffer_id = view.buffer_id()

        for window in sublime.windows():
            wid = window.id()

            for other_view in window.views():
                if other_view.buffer_id() == buffer_id:
                    vid = other_view.id()
                    persist.highlights[vid] = highlights
                    highlights.clear(other_view)
                    highlights.draw(other_view)
                    persist.errors[vid] = errors

                    if window_views.get(wid) is None:
                        window_views[wid] = other_view

        for view in window_views.values():
            self.on_selection_modified_async(view)

    def hit(self, view):
        """Record an activity that could trigger a lint and enqueue a desire to lint."""

        vid = view.id()
        self.check_syntax(view)
        self.linted_views.add(vid)

        if view.size() == 0:
            for linter in Linter.get_linters(vid):
                linter.clear()

            return

        persist.last_hit_times[vid] = queue.hit(view)

    def check_syntax(self, view):
        """
        Check and return if view's syntax has changed.

        If the syntax has changed, a new linter is assigned.

        """

        vid = view.id()
        syntax = persist.get_syntax(view)

        # Syntax either has never been set or just changed
        if vid not in self.view_syntax or self.view_syntax[vid] != syntax:
            self.view_syntax[vid] = syntax
            Linter.assign(view, reset=True)
            self.clear(view)
            return True
        else:
            return False

    def clear(self, view):
        """Clear all marks, errors and status from the given view."""
        Linter.clear_view(view)

    def is_scratch(self, view):
        """
        Return whether a view is effectively scratch.

        There is a bug (or feature) in the current ST3 where the Find panel
        is not marked scratch but has no window.

        There is also a bug where files opened from within .sublime-package files
        are not marked scratch during the on_activate event, so we have to
        check that a view with a filename actually exists on disk.

        """

        if view.is_scratch() or view.is_read_only() or view.window() is None:
            return True
        elif view.file_name() and not os.path.exists(view.file_name()):
            return True
        else:
            return False

    def view_has_file_only_linter(self, vid):
        """Return True if any linters for the given view are file-only."""
        for lint in persist.view_linters.get(vid, []):
            if lint.tempfile_suffix == '-':
                return True

        return False

    # sublime_plugin.EventListener event handlers

    def on_modified(self, view):
        """Called when a view is modified."""

        if self.is_scratch(view):
            return

        if view.id() not in persist.view_linters:
            syntax_changed = self.check_syntax(view)

            if not syntax_changed:
                return
        else:
            syntax_changed = False

        if syntax_changed or persist.settings.get('lint_mode', 'background') == 'background':
            self.hit(view)
        else:
            self.clear(view)

    def on_activated(self, view):
        """Called when a view gains input focus."""

        if self.is_scratch(view):
            return

        # Reload the plugin settings.
        persist.settings.load()

        self.check_syntax(view)
        view_id = view.id()

        if view_id not in self.linted_views:
            if view_id not in self.loaded_views:
                self.on_new(view)

            if persist.settings.get('lint_mode', 'background') in ('background', 'load/save'):
                self.hit(view)

        self.on_selection_modified_async(view)

    def on_open_settings(self, view):
        """
        Called when any settings file is opened.

        view is the view that contains the text of the settings file.

        """
        if self.is_settings_file(view, user_only=True):
            persist.settings.save(view=view)

    def is_settings_file(self, view, user_only=False):
        """Return True if view is a SublimeLinter settings file."""

        filename = view.file_name()

        if not filename:
            return False

        if not filename.startswith(sublime.packages_path()):
            return False

        dirname, filename = os.path.split(filename)
        dirname = os.path.basename(dirname)

        if self.LINTER_SETTINGS_RE.match(filename):
            if user_only:
                return dirname == 'User'
            else:
                return dirname in (persist.PLUGIN_DIRECTORY, 'User')

    @classmethod
    def on_settings_updated(cls, relint=False):
        """Callback triggered when the settings are updated."""
        if relint:
            cls.lint_all_views()
        else:
            Linter.redraw_all()

    def on_new(self, view):
        """Called when a new buffer is created."""
        self.on_open_settings(view)

        if self.is_scratch(view):
            return

        vid = view.id()
        self.loaded_views.add(vid)
        self.view_syntax[vid] = persist.get_syntax(view)

    def get_focused_view_id(self, view):
        """
        Return the focused view which shares view's buffer.

        When updating the status, we want to make sure we get
        the selection of the focused view, since multiple views
        into the same buffer may be open.

        """
        active_view = view.window().active_view()

        for view in view.window().views():
            if view == active_view:
                return view

    def on_selection_modified_async(self, view):
        """Called when the selection changes (cursor moves or text selected)."""

        if self.is_scratch(view):
            return

        view = self.get_focused_view_id(view)

        if view is None:
            return

        vid = view.id()

        # Get the line number of the first line of the first selection.
        try:
            lineno = view.rowcol(view.sel()[0].begin())[0]
        except IndexError:
            lineno = -1

        if vid in persist.errors:
            errors = persist.errors[vid]

            if errors:
                lines = sorted(list(errors))
                counts = [len(errors[line]) for line in lines]
                count = sum(counts)
                plural = 's' if count > 1 else ''

                if lineno in errors:
                    # Sort the errors by column
                    line_errors = sorted(errors[lineno], key=lambda error: error[0])
                    line_errors = [error[1] for error in line_errors]

                    if plural:
                        # Sum the errors before the first error on this line
                        index = lines.index(lineno)
                        first = sum(counts[0:index]) + 1

                        if len(line_errors) > 1:
                            last = first + len(line_errors) - 1
                            status = '{}-{} of {} errors: '.format(first, last, count)
                        else:
                            status = '{} of {} errors: '.format(first, count)
                    else:
                        status = 'Error: '

                    status += '; '.join(line_errors)
                else:
                    status = '%i error%s' % (count, plural)

                view.set_status('sublimelinter', status)
            else:
                view.erase_status('sublimelinter')

    def on_pre_save(self, view):
        """
        Called before view is saved.

        If a settings file is the active view and is saved,
        copy the current settings first so we can compare post-save.

        """
        if view.window().active_view() == view and self.is_settings_file(view):
            persist.settings.copy()

    def on_post_save(self, view):
        """Called after view is saved."""

        if self.is_scratch(view):
            return

        # First check to see if the project settings changed
        if view.window().project_file_name() == view.file_name():
            self.lint_all_views()
        else:
            # Now see if a .sublimelinterrc has changed
            filename = os.path.basename(view.file_name())

            if filename == '.sublimelinterrc':
                # If it's the main .sublimelinterrc, reload the settings
                rc_path = os.path.join(os.path.dirname(__file__), '.sublimelinterrc')

                if view.file_name() == rc_path:
                    persist.settings.load(force=True)
                else:
                    self.lint_all_views()

            # If a file other than one of our settings files changed,
            # check if the syntax changed or if we need to show errors.
            elif filename != 'SublimeLinter.sublime-settings':
                syntax_changed = self.check_syntax(view)
                vid = view.id()
                mode = persist.settings.get('lint_mode', 'background')
                show_errors = persist.settings.get('show_errors_on_save', False)

                if syntax_changed:
                    self.clear(view)

                    if vid in persist.view_linters:
                        if mode != 'manual':
                            self.lint(vid)
                        else:
                            show_errors = False
                    else:
                        show_errors = False
                else:
                    if (
                        show_errors or
                        mode in ('load/save', 'save only') or
                        mode == 'background' and self.view_has_file_only_linter(vid)
                    ):
                        self.lint(vid)
                    elif mode == 'manual':
                        show_errors = False

                if show_errors and vid in persist.errors and persist.errors[vid]:
                    view.run_command('sublimelinter_show_all_errors')

    def on_close(self, view):
        """Called after view is closed."""

        if self.is_scratch(view):
            return

        vid = view.id()

        if vid in self.loaded_views:
            self.loaded_views.remove(vid)

        if vid in self.linted_views:
            self.linted_views.remove(vid)

        if vid in self.view_syntax:
            del self.view_syntax[vid]

        persist.view_did_close(vid)


class SublimelinterEditCommand(sublime_plugin.TextCommand):

    """A plugin command used to generate an edit object for a view."""

    def run(self, edit):
        """Run the command."""
        persist.edit(self.view.id(), edit)

########NEW FILE########
