__FILENAME__ = headline
"""Some utility functions for working with headline of Markdown.

Terminologies
- Headline :: The headline entity OR the text of the headline
- Content :: The content under the current headline. It stops after
  encountering a headline with the same or higher level OR EOF.
"""
# Author: Muchenxuan Tong <demon386@gmail.com>

import re
import sublime

try:
    from .utilities import is_region_void
except ValueError:
    from utilities import is_region_void

MATCH_PARENT = 1   # Match headlines at the same or higher level
MATCH_CHILD = 2    # Match headlines at the same or lower level
MATCH_SILBING = 3  # Only Match headlines at the same level.
MATCH_ANY = 4      # Any headlines would be matched.
ANY_LEVEL = -1     # level used when MATCH_ANY is used as match type


def region_of_content_of_headline_at_point(view, from_point):
    """Extract the region of the content of under current headline."""
    _, level = headline_and_level_at_point(view, from_point)
    if level == None:
        return None

    if is_content_empty_at_point(view, from_point):
        return None

    line_num, _ = view.rowcol(from_point)
    content_line_start_point = view.text_point(line_num + 1, 0)

    next_headline, _ = find_headline(view, \
                                     content_line_start_point, \
                                     level, \
                                     True, \
                                     MATCH_PARENT)
    if not is_region_void(next_headline):
        end_pos = next_headline.a - 1
    else:
        end_pos = view.size()
    return sublime.Region(content_line_start_point, end_pos)


def headline_and_level_at_point(view, from_point, search_above_and_down=False):
    """Return the current headline and level.

    If from_point is inside a headline, then return the headline and level.
    Otherwise depends on the argument it might search above and down.
    """
    line_region = view.line(from_point)
    line_content = view.substr(line_region)
    # Update the level in case it's headline.ANY_LEVEL
    level = _extract_level_from_headline(line_content)

    # Search above and down
    if level is None and search_above_and_down:
        # Search above
        headline_region, _ = find_headline(view,\
                                           from_point,\
                                           ANY_LEVEL,
                                           False,
                                           skip_folded=True)
        if not is_region_void(headline_region):
            line_content, level = headline_and_level_at_point(view,\
                                                              headline_region.a)
        # Search down
        if level is None:
            headline_region, _ = find_headline(view,\
                                               from_point,\
                                               ANY_LEVEL,
                                               True,
                                               skip_folded=True)
            if not is_region_void(headline_region):
                line_content, level = headline_and_level_at_point(view, headline_region.a)

    return line_content, level


def _extract_level_from_headline(headline):
    """Extract the level of headline, None if not found.

    """
    re_string = _get_re_string(ANY_LEVEL, MATCH_ANY)
    match = re.match(re_string, headline)

    if match:
        return len(match.group(1))
    else:
        return None


def is_content_empty_at_point(view, from_point):
    """Check if the content under the current headline is empty.

    For implementation, check if next line is a headline a the same
    or higher level.

    """
    _, level = headline_and_level_at_point(view, from_point)
    if level is None:
        raise ValueError("from_point must be inside a valid headline.")

    line_num, _ = view.rowcol(from_point)
    next_line_region = view.line(view.text_point(line_num + 1, 0))
    next_line_content = view.substr(next_line_region)
    next_line_level = _extract_level_from_headline(next_line_content)

    # Note that EOF works too in this case.
    if next_line_level and next_line_level <= level:
        return True
    else:
        return False


def find_headline(view, from_point, level, forward=True, \
                  match_type=MATCH_ANY, skip_headline_at_point=False, \
                  skip_folded=False):
    """Return the region of the next headline or EOF.

    Parameters
    ----------
    view: sublime.view

    from_point: int
        From which to find.

    level: int
        The headline level to match.

    forward: boolean
        Search forward or backward

    match_type: int
        MATCH_SILBING, MATCH_PARENT, MATCH_CHILD or MATCH_ANY.

    skip_headline_at_point: boolean
        When searching whether skip the headline at point

    skip_folded: boolean
        Whether to skip the folded region

    Returns
    -------
    match_region: int
        Matched region, or None if not found.

    match_level: int
        The level of matched headline, or None if not found.

    """
    if skip_headline_at_point:
        # Move the point to the next line if we are
        # current in a headline already.
        from_point = _get_new_point_if_already_in_headline(view, from_point,
                                                           forward)

    re_string = _get_re_string(level, match_type)
    if forward:
        match_region = view.find(re_string, from_point)
    else:
        all_match_regions = view.find_all(re_string)
        match_region = _nearest_region_among_matches_from_point(view, \
                                                                all_match_regions, \
                                                                from_point, \
                                                                False, \
                                                                skip_folded)

    if skip_folded:
        while (_is_region_folded(match_region, view)):
            from_point = match_region.b
            match_region = view.find(re_string, from_point)

    if not is_region_void(match_region):
        if not is_scope_headline(view, match_region.a):
            return find_headline(view, match_region.a, level, forward, \
                                 match_type, True, skip_folded)
        else:
            ## Extract the level of matched headlines according to the region
            headline = view.substr(match_region)
            match_level = _extract_level_from_headline(headline)
    else:
        match_level = None
    return (match_region, match_level)

def _get_re_string(level, match_type=MATCH_ANY):
    """Get regular expression string according to match type.

    Return regular expression string, rather than compiled string. Since
    sublime's view.find function needs string.

    Parameters
    ----------
    match_type: int
        MATCH_SILBING, MATCH_PARENT, MATCH_CHILD or ANY_LEVEL.

    """
    if match_type == MATCH_ANY:
        re_string = r'^(#+)\s.*'
    else:
        try:
            if match_type == MATCH_PARENT:
                re_string = r'^(#{1,%d})\s.*' % level
            elif match_type == MATCH_CHILD:
                re_string = r'^(#{%d,})\s.*' % level
            elif match_type == MATCH_SILBING:
                re_string = r'^(#{%d,%d})\s.*' % (level, level)
        except ValueError:
            print("match_type has to be specified if level isn't ANY_LEVE")
    return re_string


def _get_new_point_if_already_in_headline(view, from_point, forward=True):
    line_content = view.substr(view.line(from_point))
    if _extract_level_from_headline(line_content):
        line_num, _ = view.rowcol(from_point)
        if forward:
            return view.text_point(line_num + 1, 0)
        else:
            return view.text_point(line_num, 0) - 1
    else:
        return from_point


def is_scope_headline(view, from_point):
    return view.score_selector(from_point, "markup.heading") > 0 or \
        view.score_selector(from_point, "meta.block-level.markdown") > 0


def _nearest_region_among_matches_from_point(view, all_match_regions, \
                                             from_point, forward=False,
                                             skip_folded=True):
    """Find the nearest matched region among all matched regions.

    None if not found.

    """
    nearest_region = None

    for r in all_match_regions:
        if not forward and r.b <= from_point and \
            (not nearest_region or r.a > nearest_region.a):
            candidate = r
        elif forward and r.a >= from_point and \
            (not nearest_region or r.b < nearest_region.b):
            candidate = r
        else:
            continue
        if skip_folded and not _is_region_folded(candidate, view):
            nearest_region = candidate

    return nearest_region


def _is_region_folded(region, view):
    for i in view.folded_regions():
        if i.contains(region):
            return True
    return False

########NEW FILE########
__FILENAME__ = headline_level
"""This file is contributed by [David Smith](https://github.com/djs070)
"""
import sublime
import sublime_plugin


class ChangeHeadingLevelCommand(sublime_plugin.TextCommand):
    def run(self, edit, up=True):
        for region in self.view.sel():
            line = self.view.line(region)
            if up:
                # Increase heading level
                if not self.view.substr(line)[0] in ['#', ' ']:
                    self.view.insert(edit, line.begin(), " ")
                self.view.insert(edit, line.begin(), "#")
            else:
                # Decrease heading level
                if self.view.substr(line)[0] == '#':
                    self.view.erase(edit, sublime.Region(line.begin(), line.begin() + 1))
                    if self.view.substr(line)[0] == ' ':
                        self.view.erase(edit, sublime.Region(line.begin(), line.begin() + 1))

########NEW FILE########
__FILENAME__ = headline_move
"""This module provides commands for easily moving between headilnes.

The feature is borrowed from [Org-mode](http://org-mode.org).

"""
# Author: Muchenxuan Tong <demon386@gmail.com>

import sublime
import sublime_plugin

try:
    from . import headline
    from .utilities import is_region_void
except ValueError:
    import headline
    from utilities import is_region_void


class HeadlineMoveCommand(sublime_plugin.TextCommand):
    def run(self, edit, forward=True, same_level=True):
        """Move between headlines, forward or backward.

        If same_level is true, only move to headline with the same level
        or higher level.

        """
        new_sel = []
        if same_level:
            level_type = headline.MATCH_PARENT
        else:
            level_type = headline.MATCH_ANY

        for region in self.view.sel():
            if same_level:
                _, level = headline.headline_and_level_at_point(self.view,\
                                                                region.a,
                                                                search_above_and_down=True)
                if level is None:
                    return
            else:
                level = headline.ANY_LEVEL

            match_region, _ = headline.find_headline(self.view, \
                                                     region.a, \
                                                     level, \
                                                     forward, \
                                                     level_type, \
                                                     skip_headline_at_point=True,\
                                                     skip_folded=True)

            if is_region_void(match_region):
                return
            new_sel.append(sublime.Region(match_region.a, match_region.a))

        self.adjust_view(new_sel)

    def adjust_view(self, new_sel):
        self.view.sel().clear()
        for region in new_sel:
            self.view.sel().add(region)
            self.view.show(region)

########NEW FILE########
__FILENAME__ = pandoc_render
"""This file is initially forked from
[SublimePandoc](https://github.com/jclement/SublimePandoc)
by [DanielMe](https://github.com/DanielMe/)

@todo naming convention should be foo_bar rather than fooBar.
@bug PDF export doesn't work in my Mac, gonna check it later.

2012-07-02: Muchenxuan Tong changed some stylical errors (with SublimeLinter)
"""

import sublime
import sublime_plugin
import webbrowser
import tempfile
import os
import os.path
import sys
import subprocess
from subprocess import PIPE


class PandocRenderCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        return self.view.score_selector(0, "text.html.markdown") > 0

    def is_visible(self):
        return True

    def run(self, edit, target="pdf", open_after=True, save_result=False):
        if target not in ["html", "docx", "pdf"]:
            raise Exception("Format %s currently unsopported" % target)

        self.setting = sublime.load_settings("SmartMarkdown.sublime-settings")

        encoding = self.view.encoding()
        if encoding == 'Undefined':
            encoding = 'UTF-8'
        elif encoding == 'Western (Windows 1252)':
            encoding = 'windows-1252'
        contents = self.view.substr(sublime.Region(0, self.view.size()))
        contents = contents.encode(encoding)

        file_name = self.view.file_name()
        if file_name:
            os.chdir(os.path.dirname(file_name))

        # write buffer to temporary file
        # This is useful because it means we don't need to save the buffer
        tmp_md = tempfile.NamedTemporaryFile(delete=False, suffix=".md")
        tmp_md.write(contents)
        tmp_md.close()

        # output file...
        suffix = "." + target
        if save_result:
            output_name = os.path.splitext(self.view.file_name())[0] + suffix
            if not self.view.file_name():
                raise Exception("Please safe the buffer before trying to export with pandoc.")
        else:
            output = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            output.close()
            output_name = output.name

        args = self.pandoc_args(target)
        self.run_pandoc(tmp_md.name, output_name, args)

        if open_after:
            self.open_result(output_name, target)
        #os.unlink(tmp_md.name)

    def run_pandoc(self, infile, outfile, args):
        cmd = ['pandoc'] + args
        cmd += [infile, "-o", outfile]

        # Merge the path in settings
        setting_path = self.setting.get("tex_path", [])
        for p in setting_path:
            if p not in os.environ["PATH"]:
                os.environ["PATH"] += ":" + p

        try:
            # Use the current directory as working dir whenever possible
            file_name = self.view.file_name()
            if file_name:
                working_dir = os.path.dirname(file_name)
                p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE,
                                     cwd=working_dir)

            else:
                p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
            p.wait()
            out, err = p.communicate()
            if err:
                raise Exception("Command: %s\n" % " ".join(cmd) + "\nErrors: " + err)
        except Exception as e:
            sublime.error_message("Fail to generate output.\n{0}".format(e))

    def pandoc_args(self, target):
        """
        Create a list of arguments for the pandoc command
        depending on the target.
        TODO: Actually do something sensible here
        """
        # Merge the args in settings
        args = self.setting.get("pandoc_args", [])

        if target == "pdf":
            args += self.setting.get("pandoc_args_pdf", [])
        if target == "html":
            args += self.setting.get("pandoc_args_html", []) + ['-t', 'html5']
        if target == "docx":
            args += self.setting.get("pandoc_args_docx", []) + ['-t', 'docx']
        return args

    def open_result(self, outfile, target):
        if target == "html":
            webbrowser.open_new_tab(outfile)
        elif sys.platform == "win32":
            os.startfile(outfile)
        elif "mac" in sys.platform or "darwin" in sys.platform:
            os.system("open %s" % outfile)
            print(outfile)
        elif "posix" in sys.platform or "linux" in sys.platform:
            os.system("xdg-open %s" % outfile)

########NEW FILE########
__FILENAME__ = smart_folding
"""Smart folding is a feature borrowed from [Org-mode](http://org-mode.org).

It enables folding / unfolding the headlines by simply pressing TAB on headlines.

Global headline folding / unfolding is recommended to be trigged by Shift + TAB,
at anywhere.

"""
# Author: Muchenxuan Tong <demon386@gmail.com>

import re

import sublime
import sublime_plugin

try:
    from . import headline
    from .utilities import is_region_void
except ValueError:
    import headline
    from utilities import is_region_void


HEADLINE_PATTERN = re.compile(r'^(#+)\s.*')


class SmartNewLineCommand(sublime_plugin.TextCommand):
    """Changes behavior of default 'insert line after'
       Puts new line after folding mark if any.
    """
    def run(self, edit):
        points = []
        for s in self.view.sel():
            r = self.view.full_line(s)
            if headline._is_region_folded(r.b + 1, self.view):
                i = headline.region_of_content_of_headline_at_point(self.view, s.b)
            else:
                i = sublime.Region(r.a, r.b - 1)
            points.append(i)
            self.view.insert(edit, i.b, '\n')
        self.view.sel().clear()
        for p in points:
            self.view.sel().add(p.b + 1)


class SmartFoldingCommand(sublime_plugin.TextCommand):
    """Smart folding is used to fold / unfold headline at the point.

    It's designed to bind to TAB key, and if the current line is not
    a headline, a \t would be inserted.

    """
    def run(self, edit):
        ever_matched = False
        for region in self.view.sel():
            matched = self.fold_or_unfold_headline_at_point(region.a)
            if matched:
                ever_matched = True
        if not ever_matched:
            for r in self.view.sel():
                self.view.insert(edit, r.a, '\t')
                self.view.show(r)

    def fold_or_unfold_headline_at_point(self, from_point):
        """Smart folding of the current headline.

        Unfold only when it's totally folded. Otherwise fold it.

        """
        _, level = headline.headline_and_level_at_point(self.view,
                                                        from_point)
        # Not a headline, cancel
        if level is None or not headline.is_scope_headline(self.view, from_point):
            return False

        content_region = headline.region_of_content_of_headline_at_point(self.view,
                                                                         from_point)
        # If the content is empty, Nothing needs to be done.
        if content_region is None:
            # Return True because there is a headline anyway.
            return True

        # Check if content region is folded to decide the action.
        if self.is_region_totally_folded(content_region):
            self.unfold_yet_fold_subheads(content_region, level)
        else:
            self.view.fold(sublime.Region(content_region.a - 1, content_region.b))
        return True

    def is_region_totally_folded(self, region):
        """Decide if the region is folded. Treat empty region as folded."""
        if (region is None) or (region.a == region.b):
            return True

        for i in self.view.folded_regions():
            if i.contains(region):
                return True
        return False

    def unfold_yet_fold_subheads(self, region, level):
        """Unfold the region while keeping the subheadlines folded."""
        ## First unfold all
        self.view.unfold(region)
        ## Fold subheads
        child_headline_region, _ = headline.find_headline(self.view, region.a, level, True, \
                                                          headline.MATCH_CHILD)

        while (not is_region_void(child_headline_region) and child_headline_region.b <= region.b):
            child_content_region = headline.region_of_content_of_headline_at_point(self.view,
                                                                                   child_headline_region.a)
            if child_content_region is not None:
                self.view.fold(sublime.Region(child_content_region.a - 1, child_content_region.b))
                search_start_point = child_content_region.b
            else:
                search_start_point = child_headline_region.b

            child_headline_region, _ = headline.find_headline(self.view, \
                                                              search_start_point, level, True, \
                                                              headline.MATCH_CHILD,
                                                              skip_headline_at_point=True)


class GlobalFoldingCommand(SmartFoldingCommand):
    """Global folding / unfolding headlines at any point.

    Unfold only when top-level headlines are totally folded.
    Otherwise fold.

    """
    def run(self, edit):
        if self.is_global_folded():
            # Unfold all
            self.unfold_all()
        else:
            self.fold_all()

    def is_global_folded(self):
        """Check if all headlines are folded.
        """
        region, level = headline.find_headline(self.view, 0, \
                                               headline.ANY_LEVEL, True)
        # Treating no heeadline as folded, since unfolded all makes
        # no harm in this situation.
        if is_region_void(region):
            return True

        point = region.a
        # point can be zero
        while (point is not None and region):
            region = headline.region_of_content_of_headline_at_point(self.view, \
                                                                     point)
            if not is_region_void(region):
                point = region.b
            if not self.is_region_totally_folded(region):
                return False
            else:
                region, level = headline.find_headline(self.view, point, \
                                                       headline.ANY_LEVEL, \
                                                       True,
                                                       skip_headline_at_point=True)
                if not is_region_void(region):
                    point = region.a
        return True

    def unfold_all(self):
        self.view.unfold(sublime.Region(0, self.view.size()))
        self.view.show(self.view.sel()[0])

    def fold_all(self):
        region, level = headline.find_headline(self.view, \
                                               0, \
                                               headline.ANY_LEVEL, \
                                               True)

        # At this point, headline region is sure to exist, otherwise it would be
        # treated as gobal folded. (self.is_global_folded() would return True)
        point = region.a
        # point can be zero
        while (point is not None and region):
            region = headline.region_of_content_of_headline_at_point(self.view, \
                                                                     point)
            if not is_region_void(region):
                point = region.b
                self.view.fold(sublime.Region(region.a - 1, region.b))
            region, level = headline.find_headline(self.view, point, \
                                                   headline.ANY_LEVEL,
                                                   True, \
                                                   skip_headline_at_point=True)
            if not is_region_void(region):
                point = region.a
        self.adjust_cursors_and_view()

    def adjust_cursors_and_view(self):
        """After folder, adjust cursors and view.

        If the current point is inside the folded region, move it move
        otherwise it's easy to perform some unintentional editing.

        """
        folded_regions = self.view.folded_regions()
        new_sel = []

        for r in self.view.sel():
            for folded in folded_regions:
                if folded.contains(r):
                    new_sel.append(sublime.Region(folded.b, folded.b))
                    break
            else:
                new_sel.append(r)

        self.view.sel().clear()
        for r in new_sel:
            self.view.sel().add(r)
            self.view.show(r)

########NEW FILE########
__FILENAME__ = smart_list
"""Smart list is used to automatially continue the current list."""
# Author: Muchenxuan Tong <demon386@gmail.com>

import re

import sublime
import sublime_plugin


ORDER_LIST_PATTERN = re.compile(r"(\s*)(\d+)(\.\s+)\S+")
UNORDER_LIST_PATTERN = re.compile(r"(\s*[-+\**]+)(\s+)\S+")
EMPTY_LIST_PATTERN = re.compile(r"(\s*([-+\**]|\d+\.+))\s+$")


class SmartListCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            line_region = self.view.line(region)
            # the content before point at the current line.
            before_point_region = sublime.Region(line_region.a,
                                                 region.a)
            before_point_content = self.view.substr(before_point_region)

            # Disable smart list when folded.
            folded = False
            for i in self.view.folded_regions():
                if i.contains(before_point_region):
                    self.view.insert(edit, region.a, '\n')
                    folded = True
            if folded:
                break

            match = EMPTY_LIST_PATTERN.match(before_point_content)
            if match:
                self.view.erase(edit, before_point_region)
                break

            match = ORDER_LIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + \
                              str(int(match.group(2)) + 1) + \
                              match.group(3)
                self.view.insert(edit, region.a, "\n" + insert_text)
                break

            match = UNORDER_LIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + match.group(2)
                self.view.insert(edit, region.a, "\n" + insert_text)
                break

            self.view.insert(edit, region.a, '\n')
        self.adjust_view()

    def adjust_view(self):
        for region in self.view.sel():
            self.view.show(region)

########NEW FILE########
__FILENAME__ = smart_table
"""Smart is inspired by the Table behavior of Org-mode.

Markdown itself doesn't support grid table, yet pandoc does.

@todo: add a key binding for converting grid table to the simple one
"""
# Author: Muchenxuan Tong <demon386@gmail.com>
# LICENSE: MIT

import sublime
import sublime_plugin

try:
    from . import table
except ValueError:
    import table


class SmartTable(sublime_plugin.TextCommand):
    def run(self, edit, forward=True):
        new_sel = []
        for r in self.view.sel():
            point = r.a

            for i in self.view.folded_regions():
                if i.contains(sublime.Region(point, point)):
                    return
            t = table.convert_table_at_point_as_list(self.view, point)
            t = table.reformat_table_list(t)
            t_str = table.convert_table_list_to_str(t)

            # Both are 0-based
            cur_row_num, cur_col_num = table.get_point_row_and_col(self.view, point)
            table_row_num = len(t)
            line_num, _ = self.view.rowcol(point)
            start_line_num = line_num - cur_row_num
            start_point = self.view.text_point(line_num - cur_row_num, 0)
            end_line_num = line_num + table_row_num - cur_row_num - 1
            end_line_start_point = self.view.text_point(end_line_num, 0)
            end_point = self.view.line(end_line_start_point).b

            # Erase the previous table region, use the new one for substitution.
            self.view.erase(edit, sublime.Region(start_point, end_point))
            self.view.insert(edit, start_point, t_str)

            if forward:
                if cur_col_num is None or cur_col_num >= len(t[0]) - 1:
                    line_num += 1
                    while(table.is_line_separator(self.view, line_num)):
                        line_num += 1
                    cur_col_num = 0
                else:
                    cur_col_num += 1
            else:
                if cur_col_num is None or cur_col_num <= 0:
                    line_num -= 1
                    while(table.is_line_separator(self.view, line_num)):
                        line_num -= 1
                    cur_col_num = len(t[0]) - 1
                else:
                    cur_col_num -= 1

            # Add a new line when at the end of the table.
            if line_num < start_line_num or line_num > end_line_num:
                col_pos = 0
                if line_num > end_line_num:
                    self.view.insert(edit, self.view.text_point(line_num, 0), "\n")
            else:
                col_pos = self.calculate_col_point(t, cur_col_num)

            new_sel.append(self.view.text_point(line_num, col_pos))

        self.view.sel().clear()
        for r in new_sel:
            self.view.sel().add(r)
            self.view.show(r)

    def calculate_col_point(self, formatted_table, col_num):
        i = 0
        while table.SEPARATOR_PATTERN.match(formatted_table[i][0]):
            i += 1

        cols_length = [len(j) for j in formatted_table[i]]
        point = 2
        for i in range(col_num):
            point += cols_length[i] + 3
        return point

########NEW FILE########
__FILENAME__ = table
"""Utilities function for working with grid table of Pandoc

Terminologies

- Table list :: This is not a list of tables, but rather converting the table as
a nested python list. Each row is a sub-list in the table list.

"""
# Author: Muchenxuan Tong <demon386@gmail.com>
# LICENSE: MIT

import re
import copy

import sublime

try:
    from . import utilities
except ValueError:
    import utilities

TABLE_PATTERN = re.compile(r"\s*\|")
SEPARATOR_PATTERN = re.compile(r"\s*(\+[=-])")


def convert_table_at_point_as_list(view, from_point):
    """Get the table at the point.
    Transform the table to python list.

    Returns
    -------
    table: list
        A nested list representing the table.
    indent: "str" (@todo not impelmented yet)
        String of indentation, used in every row.

    """
    table_above = convert_table_above_or_below_as_list(view, from_point, above=True)
    table_below = convert_table_above_or_below_as_list(view, from_point, above=False)
    row_at_point = convert_row_at_point_as_list(view, from_point)

    table = table_above + [row_at_point] + table_below
    return table


def convert_table_above_or_below_as_list(view, from_point, above):
    """Convert the table above the point as python list.

    Returns
    -------
    table: list
        A nested list representing the table.

    """
    line_num, _ = view.rowcol(from_point)
    line_num += - 1 if above else 1

    line_text = utilities.text_at_line(view, line_num)
    table = []

    while line_text and (TABLE_PATTERN.match(line_text) or
                         SEPARATOR_PATTERN.match(line_text)):
        table.append(_convert_row_text_as_list(line_text))
        line_num += -1 if above else 1
        line_text = utilities.text_at_line(view, line_num)

    if above:
        table = table[::-1]

    return table


def convert_row_at_point_as_list(view, from_point):
    """Convert the row at point as a python list.
    """
    line_num, _ = view.rowcol(from_point)
    line_text = utilities.text_at_line(view, line_num)

    return _convert_row_text_as_list(line_text)


def _convert_row_text_as_list(row_text):
    """Convert the text of a row into a python list.

    Paramters
    ---------
    row_text: str
        The text of the row.

    Returns
    -------
    lst: list
        The converted list.

    """
    split_row = row_text.split("|")

    if len(split_row) > 2 and split_row[-1].strip() == "":
        lst = split_row[1:-1]
    else:
        lst = split_row[1:]

    match = SEPARATOR_PATTERN.match(row_text)
    if match:
        lst = [match.group(1)]

    return [i.strip() for i in lst]


def reformat_table_list(table):
    """Reformat & align the table list.

    After this, every column is of the same length,
    and every row is of the same number of column.

    """
    cols_num = max([len(row) for row in table])
    cols_length = _get_cols_length(table, cols_num)

    new_table = []
    for row in table:
        new_row = []
        if not SEPARATOR_PATTERN.match(row[0]):
            for i in range(cols_num):
                try:
                    col = row[i]
                    new_row.append(col + " " * (cols_length[i] - len(col)))
                except:
                    new_row.append(" " * cols_length[i])
        else:
            marker = row[0][1]
            for i in range(cols_num):
                new_row.append(marker * (cols_length[i] + 2))
            # Add a mark for recognization
            new_row[0] = "+" + new_row[0]
        new_table.append(new_row)
    return new_table


def convert_table_list_to_str(table):
    """Convert the python list to str for outputing.

    """
    table_str = ""
    table = copy.deepcopy(table)
    for row in table:
        if SEPARATOR_PATTERN.match(row[0]):
            row[0] = row[0][1:]  # Remove the mark added in reformat_table_list
            row_str = "+"
            for col_str in row:
                row_str += col_str + "+"
        else:
            row_str = "|"
            for col_str in row:
                row_str += " " + col_str + " " + "|"
        table_str += row_str + "\n"
    return table_str[:-1]


def _get_cols_length(table, cols_num):
    """Return the max length of every columns.
    """
    cols_length = [0] * cols_num
    for row in table:
        for (i, col) in enumerate(row):
            col_len = len(col)
            if col_len > cols_length[i]:
                cols_length[i] = col_len
    return cols_length


def get_point_row_and_col(view, from_point):
    """Return the row and col the current point is in the table.
    """
    line_num, _ = view.rowcol(from_point)
    line_num -= 1

    line_text = utilities.text_at_line(view, line_num)
    row_num = 0
    while line_text and (TABLE_PATTERN.match(line_text) or
                         SEPARATOR_PATTERN.match(line_text)):
        row_num += 1
        line_num -= 1
        line_text = utilities.text_at_line(view, line_num)

    line_start_point = view.line(from_point)
    region = sublime.Region(line_start_point.a, from_point)
    precedding_text = view.substr(region)

    split_row = precedding_text.split("|")
    if len(split_row) >= 2:
        col_num = len(split_row) - 2
    elif split_row[0].strip() == "":
        col_num = -1
    else:
        col_num = None
    return (row_num, col_num)


def is_line_separator(view, line_num):
    """Check if the current line is a separator.
    """
    text = utilities.text_at_line(view, line_num)
    if text and SEPARATOR_PATTERN.match(text):
        return True
    else:
        return False

########NEW FILE########
__FILENAME__ = utilities
"""Some utility functions for working with sublime.
"""


def text_at_line(view, line_num):
    """Return the content at line. None if out of boundary."""
    if line_num < 0:
        return None

    max_line_num, _ = view.rowcol(view.size())
    if line_num > max_line_num:
        return None

    point = view.text_point(line_num, 0)
    line_region = view.line(point)
    return view.substr(line_region)

def is_region_void(region):
    if region == None:
        return True
    if region.a == -1 and region.b == -1:
        return True
    return False
########NEW FILE########
