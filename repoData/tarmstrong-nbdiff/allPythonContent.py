__FILENAME__ = benchmark
import subprocess
import timeit

def run_diff_once():
    f1 = 'example-notebooks/0/before.ipynb'
    f2 = 'example-notebooks/0/after.ipynb'

    subprocess.call(['nbdiff', '--check', f1, f2])

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('commit')
    args = parser.parse_args()
    t = timeit.Timer('run_diff_once()', setup='from __main__ import run_diff_once')
    measurements = t.repeat(repeat=40, number=1)
    import csv
    import sys
    import arrow
    row = [args.commit, arrow.now().timestamp] + measurements
    csv.writer(sys.stdout).writerow(row)


########NEW FILE########
__FILENAME__ = run_all
import git2json as g
import subprocess as s


BENCH_REPO = '/home/tavish/capstone/nbdiff/.git'
check_added = '1f52ff8b5acaa408948d7a73b07b9dd2554e863a'

HEAD = check_added

commits = g.parse_commits(g.run_git_log(extra_args=[HEAD + '..', '--']).read())
i = 0
for commit in commits:
    if i % 5 == 0:
        s.call(('git --git-dir=' + BENCH_REPO + ' checkout ' + commit).split())
        benchmark_output = s.check_output(['python', 'benchmark.py', commit])
        with open('results.csv', 'a') as out:
            out.write(benchmark_output)
    i += 1

########NEW FILE########
__FILENAME__ = git_adapter
__author__ = 'root'

import sys
import subprocess
from .vcs_adapter import VcsAdapter


class GitAdapter(VcsAdapter):

    def get_modified_notebooks(self):
        # get modified file names
        modified = subprocess.check_output("git ls-files --modified".split())
        fnames = modified.splitlines()

        # get unmerged file info
        unmerged = subprocess.check_output("git ls-files --unmerged".split())
        unmerged_array = [line.split() for line in unmerged.splitlines()]

        # get unmerged file names
        unmerged_array_names = [x[3] for x in unmerged_array]

        # ignore unmerged files, get unique names
        fnames = list(set(fnames) - set(unmerged_array_names))

        nb_diff = []
        for item in fnames:
            head_version_show = subprocess.Popen(
                ['git', 'show', 'HEAD:' + item],
                stdout=subprocess.PIPE
            )

            current_local_notebook = open(item)
            committed_notebook = head_version_show.stdout

            nb_diff.append((current_local_notebook, committed_notebook, item))

        return super(GitAdapter, self).filter_modified_notebooks(nb_diff)

    def get_unmerged_notebooks(self):
        # TODO error handling.

        output = subprocess.check_output("git ls-files --unmerged".split())
        output_array = [line.split() for line in output.splitlines()]

        if len(output_array) % 3 != 0:  # TODO should be something else
            sys.stderr.write(
                "Can't find the conflicting notebook. Quitting.\n")
            sys.exit(-1)

        hash_list = []

        for index in xrange(0, len(output_array), 3):
            local_hash = output_array[index + 1][1]
            base_hash = output_array[index][1]
            remote_hash = output_array[index + 2][1]
            file_name = output_array[index][3]
            hash_list.append((local_hash, base_hash, remote_hash, file_name))

        file_hooks = []

        for hash in hash_list:
            local = subprocess.Popen(
                ['git', 'show', hash[0]],
                stdout=subprocess.PIPE
            )
            base = subprocess.Popen(
                ['git', 'show', hash[1]],
                stdout=subprocess.PIPE
            )
            remote = subprocess.Popen(
                ['git', 'show', hash[2]],
                stdout=subprocess.PIPE
            )
            file_name = hash[3]
            file_hooks.append((local.stdout, base.stdout,
                              remote.stdout, file_name))

        return super(GitAdapter, self).filter_unmerged_notebooks(file_hooks)

    def stage_file(self, file, contents=None):
        if contents is not None:
            with open(file, 'w') as result_file:
                result_file.write(file)
        command = ["git", "add", file]
        return subprocess.call(command)

########NEW FILE########
__FILENAME__ = hg_adapter
__author__ = 'root'


class HgAdapter:

    def get_modified_notebooks(self):
        pass

    def get_unmerged_notebooks(self):
        pass

    def stage_file(self, file, contents=None):
        pass

########NEW FILE########
__FILENAME__ = vcs_adapter
__author__ = 'root'

import re


class VcsAdapter(object):

    def get_modified_notebooks(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def filter_modified_notebooks(self, file_hooks):
        modified_notebooks = []
        for item in file_hooks:
            if re.search('.ipynb$', item[2]):
                modified_notebooks.append(item)

        return modified_notebooks

    def get_unmerged_notebooks(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def filter_unmerged_notebooks(self, file_hooks):
        unmerged_notebooks = []
        for item in file_hooks:
            if re.search('.ipynb$', item[3]):
                unmerged_notebooks.append(item)

        return unmerged_notebooks

    def stage_file(self, file, contents=None):
        raise NotImplementedError("Subclass must implement abstract method")

########NEW FILE########
__FILENAME__ = commands
'''
Entry points for the nbdiff package.
'''
from __future__ import print_function
import argparse
from .merge import notebook_merge
from .notebook_parser import NotebookParser
import sys
from .notebook_diff import notebook_diff
from .adapter.git_adapter import GitAdapter
from .server.local_server import app
import threading
import webbrowser
import IPython.nbformat.current as nbformat
import IPython.nbformat.reader
try:
    NotJSONError = IPython.nbformat.current.NotJSONError
except AttributeError:
    NotJSONError = IPython.nbformat.reader.NotJSONError


def diff():
    description = '''
    Produce a diffed IPython Notebook from before and after notebooks.

    If no arguments are given, nbdiff looks for modified notebook files in
    the version control system.

    The resulting diff is presented to the user in the browser at
    http://localhost:5000.
    '''
    usage = 'nbdiff [-h] [--check] [--debug] ' +\
            '[--browser=<browser] [before after]'
    parser = argparse.ArgumentParser(
        description=description,
        usage=usage,
    )
    # TODO share this code with merge()
    parser.add_argument(
        '--browser',
        '-b',
        default=None,
        help='Browser to launch nbdiff/nbmerge in',
    )
    parser.add_argument(
        '--check',
        '-c',
        action='store_true',
        default=False,
        help='Run nbdiff algorithm but do not display the result.',
    )
    parser.add_argument(
        '--debug',
        '-d',
        action='store_true',
        default=False,
        help='Pass debug=True to the Flask server to ease debugging.',
    )
    parser.add_argument('before', nargs='?',
                        help='The notebook to diff against.')
    parser.add_argument('after', nargs='?',
                        help='The notebook to compare `before` to.')
    args = parser.parse_args()

    parser = NotebookParser()

    if args.before and args.after:
        invalid_notebooks = []

        try:
            notebook1 = parser.parse(open(args.before))
        except NotJSONError:
            invalid_notebooks.append(args.before)

        try:
            notebook2 = parser.parse(open(args.after))
        except NotJSONError:
            invalid_notebooks.append(args.after)

        if (len(invalid_notebooks) == 0):
            result = notebook_diff(notebook1, notebook2)

            filename_placeholder = "{} and {}".format(args.before, args.after)
            app.add_notebook(result, filename_placeholder)
            if not args.check:
                open_browser(args.browser)
                app.run(debug=args.debug)

        else:
            print('The notebooks could not be diffed.')
            print('There was a problem parsing the following notebook '
                  + 'files:\n' + '\n'.join(invalid_notebooks))
            return -1

    elif not (args.before or args.after):
        # No arguments have been given. Ask version control instead
        git = GitAdapter()

        modified_notebooks = git.get_modified_notebooks()

        if not len(modified_notebooks) == 0:
            invalid_notebooks = []
            for nbook in modified_notebooks:
                try:
                    filename = nbook[2]

                    current_notebook = parser.parse(nbook[0])
                    head_version = parser.parse(nbook[1])

                    result = notebook_diff(head_version, current_notebook)
                    app.add_notebook(result, filename)

                except NotJSONError:
                    invalid_notebooks.append(filename)

            if (len(invalid_notebooks) > 0):
                print('There was a problem parsing the following notebook '
                      + 'files:\n' + '\n'.join(invalid_notebooks))

            if (len(modified_notebooks) == len(invalid_notebooks)):
                print("There are no valid notebooks to diff.")
                return -1

            if not args.check:
                open_browser(args.browser)
                app.run(debug=False)
        else:
            print("No modified files to diff.")
            return 0
    else:
        print ("Invalid number of arguments. Run nbdiff --help")
        return -1


def merge():
    description = '''
    nbmerge is a tool for resolving merge conflicts in IPython Notebook
    files.

    If no arguments are given, nbmerge attempts to find the conflicting
    file in the version control system.

    Positional arguments are available for integration with version
    control systems such as Git and Mercurial.
    '''
    usage = (
        'nbmerge [-h] [--check] [--debug] [--browser=<browser>]'
        '[local base remote [result]]'
    )
    parser = argparse.ArgumentParser(
        description=description,
        usage=usage,
    )
    parser.add_argument('notebook', nargs='*')
    # TODO share this code with diff()
    parser.add_argument(
        '--check',
        '-c',
        action='store_true',
        default=False,
        help='Run nbmerge algorithm but do not display the result.',
    )
    parser.add_argument(
        '--debug',
        '-d',
        action='store_true',
        default=False,
        help='Pass debug=True to the Flask server to ease debugging.',
    )
    parser.add_argument(
        '--browser',
        '-b',
        default=None,
        help='Browser to launch nbdiff/nbmerge in',
    )
    args = parser.parse_args()
    length = len(args.notebook)
    parser = NotebookParser()
    valid_notebooks = False

    # only 'nbmerge' - no files specified with command
    if length == 0:
        git = GitAdapter()
        unmerged_notebooks = git.get_unmerged_notebooks()

        if not len(unmerged_notebooks) == 0:
            invalid_notebooks = []

            for nbook in unmerged_notebooks:
                try:
                    filename = nbook[3]

                    nb_local = parser.parse(nbook[0])
                    nb_base = parser.parse(nbook[1])
                    nb_remote = parser.parse(nbook[2])

                    pre_merged_notebook = notebook_merge(nb_local,
                                                         nb_base, nb_remote)
                    app.add_notebook(pre_merged_notebook, filename)

                except NotJSONError:
                    invalid_notebooks.append(filename)

            if (len(invalid_notebooks) > 0):
                print('There was a problem parsing the following notebook '
                      + 'files:\n' + '\n'.join(invalid_notebooks))

            if (len(unmerged_notebooks) == len(invalid_notebooks)):
                print("There are no valid notebooks to merge.")
                return -1
            else:
                valid_notebooks = True

        else:
            print('There are no files to be merged.')
            return -1

    # files specified with nbmerge command
    elif length == 3 or length == 4:
        invalid_notebooks = []

        if length == 3:
            # hg usage:
            # $ hg merge -t nbmerge <branch>

            # Mercurial gives three arguments:
            # 1. Local / Result (the file in your working directory)
            # 2. Base
            # 3. Remote
            filename = args.notebook[0]  # filename for saving

        elif length == 4:
            # You need to run this before git mergetool will accept nbmerge
            # $ git config mergetool.nbmerge.cmd \
            #        "nbmerge \$LOCAL \$BASE \$REMOTE \$MERGED"
            # and then you can invoke it with:
            # $ git mergetool -t nbmerge
            #
            # Git gives four arguments (these are configurable):
            # 1. Local
            # 2. Base
            # 3. Remote
            # 4. Result (the file in your working directory)
            filename = args.notebook[3]   # filename for saving

        try:
            nb_local = parser.parse(open(args.notebook[0]))
        except NotJSONError:
            invalid_notebooks.append(args.notebook[0])

        try:
            nb_base = parser.parse(open(args.notebook[1]))
        except NotJSONError:
            invalid_notebooks.append(args.notebook[1])

        try:
            nb_remote = parser.parse(open(args.notebook[2]))
        except NotJSONError:
            invalid_notebooks.append(args.notebook[2])

        # local, base and remote are all valid notebooks
        if (len(invalid_notebooks) == 0):
            pre_merged_notebook = notebook_merge(nb_local, nb_base, nb_remote)
            app.add_notebook(pre_merged_notebook, filename)
            valid_notebooks = True

        elif (len(invalid_notebooks) > 0):
                print('There was a problem parsing the following notebook '
                      + 'files:\n' + '\n'.join(invalid_notebooks))
                print("There are no valid notebooks to merge.")
                return -1

    else:
        sys.stderr.write('Incorrect number of arguments. Quitting.\n')
        sys.exit(-1)

    def save_notebook(notebook_result, filename):
        parsed = nbformat.reads(notebook_result, 'json')
        with open(filename, 'w') as targetfile:
            nbformat.write(parsed, targetfile, 'ipynb')

    if (valid_notebooks):
        if not args.check:
            app.shutdown_callback(save_notebook)
            open_browser(args.browser)
            app.run(debug=args.debug)


def open_browser(browser_exe):
    try:
        browser = webbrowser.get(browser_exe)
    except webbrowser.Error:
        browser = None
    if browser:
        b = lambda: browser.open("http://127.0.0.1:5000/0", new=2)
        threading.Thread(target=b).start()

########NEW FILE########
__FILENAME__ = comparable
from .diff import (
    diff,
    create_grid,
    find_matches,
)
import Levenshtein


class BooleanPlus(object):

    def __init__(self, truthfulness, mod):
        self.truth = truthfulness
        self.modified = mod

    def __nonzero__(self):
        '''
        for evaluating as a boolean
        '''
        return self.truth

    def is_modified(self):
        return self.modified


class LineComparator(object):

    def __init__(self, data, check_modified=False):
        self.data = data
        self.check_modified = check_modified

    def __eq__(self, other):
        return self.equal(self.data, other.data)

    def equal(self, line1, line2):
        '''
        return true if exactly equal or if equal but modified,
        otherwise return false
        return type: BooleanPlus
        '''

        eqLine = line1 == line2
        if eqLine:
            return BooleanPlus(True, False)
        else:
            unchanged_count = self.count_similar_words(line1, line2)
            similarity_percent = (
                (2.0 * unchanged_count) /
                (len(line1.split()) + len(line2.split()))
            )
            if similarity_percent >= 0.50:
                return BooleanPlus(True, True)
            return BooleanPlus(False, False)

    def count_similar_words(self, line1, line2):
        words1 = line1.split()
        words2 = line2.split()
        grid = create_grid(words1, words2)
        matches = []

        for colnum in range(len(grid)):
            new_matches = find_matches(grid[colnum], colnum)
            matches = matches + new_matches

        matched_cols = [r[0] for r in matches]
        matched_rows = [r[1] for r in matches]
        unique_cols = set(matched_cols)
        unique_rows = set(matched_rows)

        return min(len(unique_cols), len(unique_rows))


class CellComparator():

    def __init__(self, data, check_modified=False):
        self.data = data
        self.check_modified = check_modified

    def __eq__(self, other):
        return self.equal(self.data, other.data)

    def equal(self, cell1, cell2):
        if not cell1["cell_type"] == cell2["cell_type"]:
            return False
        elif cell1["cell_type"] == "heading":
            if not cell1["level"] == cell2["level"]:
                return False
            else:
                if cell1['source'] == cell2['source']:
                    return True
                result = diff(
                    cell1["source"].split(' '),
                    cell2["source"].split(' ')
                )
                modified = 0.0
                unchanged = 0.0
                for dict in result:
                    if dict['state'] == "added" or dict['state'] == "deleted":
                        modified += 1
                    elif dict['state'] == "unchanged":
                        unchanged += 1
                modifiedness = unchanged/(modified + unchanged)
                if modifiedness >= 0.6:
                    return BooleanPlus(True, True)
                else:
                    return False
        elif self.istextcell(cell1):
            return cell1["source"] == cell2["source"]
        else:
            return self.compare_cells(cell1, cell2)

    def istextcell(self, cell):
        return "source" in cell

    def equaloutputs(self, output1, output2):
        if not len(output1) == len(output2):
            return False
        for i in range(0, len(output1)):
            if not output1[i] == output2[i]:
                return False
        return True

    def compare_cells(self, cell1, cell2):
        '''
        return true if exactly equal or if equal but modified,
        otherwise return false
        return type: BooleanPlus
        '''
        eqlanguage = cell1["language"] == cell2["language"]
        eqinput = cell1["input"] == cell2["input"]
        eqoutputs = self.equaloutputs(cell1["outputs"], cell2["outputs"])

        if eqlanguage and eqinput and eqoutputs:
            return BooleanPlus(True, False)
        elif not self.check_modified:
            return BooleanPlus(False, False)

        input1 = u"".join(cell1['input'])
        input2 = u"".join(cell2['input'])
        similarity_percent = Levenshtein.ratio(input1, input2)
        if similarity_percent >= 0.65:
            return BooleanPlus(True, True)
        return BooleanPlus(False, False)

########NEW FILE########
__FILENAME__ = diff
import itertools as it
import collections

__all__ = ['diff']


def diff(before, after, check_modified=False):
    """Diff two sequences of comparable objects.

    The result of this function is a list of dictionaries containing
    values in ``before`` or ``after`` with a ``state`` of either
    'unchanged', 'added', 'deleted', or 'modified'.

    >>> import pprint
    >>> result = diff(['a', 'b', 'c'], ['b', 'c', 'd'])
    >>> pprint.pprint(result)
    [{'state': 'deleted', 'value': 'a'},
     {'state': 'unchanged', 'value': 'b'},
     {'state': 'unchanged', 'value': 'c'},
     {'state': 'added', 'value': 'd'}]

    Parameters
    ----------
    before : iterable
        An iterable containing values to be used as the baseline version.
    after : iterable
        An iterable containing values to be compared against the baseline.
    check_modified : bool
        Whether or not to check for modifiedness.

    Returns
    -------
    diff_items : A list of dictionaries containing diff information.
    """

    # The grid will be empty if `before` or `after` are
    # empty; this will violate the assumptions made in the rest
    # of this function.
    # If this is the case, we know what the result of the diff is
    # anyways: the contents of the other, non-empty input.
    if len(before) == 0:
        return [
            {'state': 'added', 'value': v}
            for v in after
        ]
    elif len(after) == 0:
        return [
            {'state': 'deleted', 'value': v}
            for v in before
        ]

    grid = create_grid(before, after)

    nrows = len(grid[0])
    ncols = len(grid)
    dps = diff_points(grid)
    result = []
    for kind, col, row in dps:
        if kind == 'unchanged':
            value = before[col]
            result.append({
                'state': kind,
                'value': value,
            })
        elif kind == 'deleted':
            assert col < ncols
            value = before[col]
            result.append({
                'state': kind,
                'value': value,
            })
        elif kind == 'added':
            assert row < nrows
            value = after[row]
            result.append({
                'state': kind,
                'value': value,
            })
        elif check_modified and kind == 'modified':
            result.append({
                'state': kind,
                'originalvalue': before[col],
                'modifiedvalue': after[row],
            })
        elif (not check_modified) and kind == 'modified':
            result.append({
                'state': 'deleted',
                'value': before[col],
            })
            result.append({
                'state': 'added',
                'value': after[row],
            })
        else:
            raise Exception('We should not be here.')
    return result


def diff_points(grid):
    ncols = len(grid)
    nrows = len(grid[0])

    lcs_result = lcs(grid)
    matched_cols = [r[0] for r in lcs_result]
    matched_rows = [r[1] for r in lcs_result]

    cur_col = 0
    cur_row = 0

    result = []
    while cur_col < ncols or cur_row < nrows:
        passfirst = cur_col < ncols and cur_row < nrows
        goodrow = cur_row < nrows
        goodcol = cur_col < ncols
        if passfirst and lcs_result \
                and (cur_col, cur_row) == lcs_result[0]:
            lcs_result.pop(0)
            matched_cols.pop(0)
            matched_rows.pop(0)
            comparison = grid[cur_col][cur_row]
            if hasattr(comparison, 'is_modified') \
                    and comparison.is_modified():
                result.append(('modified', cur_col, cur_row))
            else:
                result.append(('unchanged', cur_col, cur_row))
            cur_col += 1
            cur_row += 1
        elif goodcol and \
                (not matched_cols or cur_col != matched_cols[0]):
            assert cur_col < ncols
            result.append(('deleted', cur_col, None))
            cur_col += 1
        elif goodrow and \
                (not matched_rows or cur_row != matched_rows[0]):
            assert cur_row < nrows
            result.append(('added', None, cur_row))
            cur_row += 1
#        print result

    return result


def create_grid(before, after):
    ncols = len(before)
    nrows = len(after)
    all_comps = [b == a for b, a in it.product(before, after)]
    return [
        all_comps[col*(nrows):col*(nrows)+nrows]
        for col in range(ncols)
    ]


def find_matches(col, colNum):
    result = []
    for j in range(len(col)):
        if col[j]:
            result.append((colNum, j))
    return result


def lcs(grid):
    kcs = find_candidates(grid)
    ks = kcs.keys()
    if len(ks) == 0:
        return []
    highest = max(kcs.keys())
    last_point = kcs[highest][-1]
    cur = highest - 1
    acc = [last_point]
    while cur > 0:
        comp = acc[-1]
        cx, cy = comp
        possibilities = [
            (x, y) for (x, y)
            in reversed(kcs[cur])
            if cx > x and cy > y
        ]
        if len(possibilities) > 0:
            acc.append(possibilities[-1])
        cur -= 1

    return list(reversed(acc))


def process_col(k, col, colNum):
    matches = find_matches(col, colNum)
    d = collections.defaultdict(lambda: [])
    x = 0
    for (i, j) in matches:
        oldx = x
        if not k and not d[1]:
            d[1].append((i, j))
        elif k:
            x = check_match((i, j), k)
            if x is None:
                continue
            x = x
            if x == oldx:
                continue
            d[x].append((i, j))
    return dict(d)


def check_match(point, k):
    result = []
    k_keys = k.keys()
    max_k = max(k_keys)
    new_max_k = max_k + 1
    k_range = k_keys + [new_max_k]
    for x in k_range:
        if x == 1:
            continue

        if point[1] < x-2:
            continue

        above_key = x - 1
        above_x = above_key == new_max_k and \
            10000 or max([l[0] for l in k[above_key]])
        above_y = above_key == new_max_k and \
            10000 or min([l[1] for l in k[above_key]])
        below_key = x - 2
        below_x = below_key < 1 and -1 or max([l[0] for l in k[below_key]])
        below_y = below_key < 1 and -1 or min([l[1] for l in k[below_key]])
        new_x, new_y = point
        if new_x > above_x and new_y < above_y and \
                new_x > below_x and new_y > below_y:
            result.append(x-1)

    below_key = new_max_k - 1
    below_x = below_key == 0 and -1 or max([l[0] for l in k[new_max_k-1]])
    below_y = below_key == 0 and -1 or min([l[1] for l in k[new_max_k-1]])
    new_x, new_y = point
    if new_x > below_x and new_y > below_y:
        result.append(new_max_k)
    if len(result) > 0:
        actual_result = result[0]
        # print result
        assert point[1] >= actual_result-1
        return (result)[0]
    else:
        return None


def add_results(k, result):
    finalResult = collections.defaultdict(lambda: [], k)
    for x in result.keys():
        finalResult[x] = finalResult[x] + result[x]
    return finalResult


def find_candidates(grid):
    k = collections.defaultdict(lambda: [])
    for colNum in range(len(grid)):
        k = add_results(k, process_col(k, grid[colNum], colNum))
    return dict(k)

########NEW FILE########
__FILENAME__ = merge
from . import diff
from . import comparable
from .notebook_diff import (
    diff_result_to_cell,
)
import IPython.nbformat.current as nbformat
import itertools as it
import copy


def merge(local, base, remote, check_modified=False):
    """Generate unmerged series of changes (including conflicts).

    By diffing the two diffs, we find *changes* that are
    on the local branch, the remote branch, or both.
    We arbitrarily choose the "local" branch to be the "before"
    and the "remote" branch to be the "after" in the diff algorithm.

    Therefore:
    If a change is "deleted", that means that it occurs only on
    the local branch. If a change is "added" that means it occurs only on
    the remote branch. If a change is "unchanged", that means it occurs
    in both branches. Either the same addition or same deletion occurred in
    both branches, or the cell was not changed in either branch.

    Parameters
    ----------
    local : list
        A sequence representing the items on the local branch.
    base : dict
        A sequence representing the items on the base branch
    remote : dict
        A sequence representing the items on the remote branch.

    Returns
    -------
    result : A diff result comparing the changes on the local and remote
             branches.
    """
    base_local = diff.diff(base, local, check_modified=check_modified)
    base_remote = diff.diff(base, remote, check_modified=check_modified)
    merge = diff.diff(base_local, base_remote)
    return merge


def notebook_merge(local, base, remote, check_modified=False):
    """Unify three notebooks into a single notebook with merge metadata.

    The result of this function is a valid notebook that can be loaded
    by the IPython Notebook front-end. This function adds additional
    cell metadata that the front-end Javascript uses to render the merge.

    Parameters
    ----------
    local : dict
        The local branch's version of the notebook.
    base : dict
        The last common ancestor of local and remote.
    remote : dict
        The remote branch's version of the notebook.

    Returns
    -------
    nb : A valid notebook containing merge metadata.
    """

    local_cells = get_cells(local)
    base_cells = get_cells(base)
    remote_cells = get_cells(remote)

    rows = []
    current_row = []
    empty_cell = lambda: {
        'cell_type': 'code',
        'language': 'python',
        'outputs': [],
        'prompt_number': 1,
        'text': ['Placeholder'],
        'metadata': {'state': 'empty'}
    }

    diff_of_diffs = merge(local_cells, base_cells, remote_cells)

    # For each item in the higher-order diff, create a "row" that
    # corresponds to a row in the NBDiff interface. A row contains:
    # | LOCAL | BASE | REMOTE |

    for item in diff_of_diffs:
        state = item['state']
        cell = copy.deepcopy(diff_result_to_cell(item['value']))
        if state == 'deleted':
            # This change is between base and local branches.
            # It can be an addition or a deletion.
            if cell['metadata']['state'] == 'unchanged':
                # This side doesn't have the change; wait
                # until we encounter the change to create the row.
                continue
            cell['metadata']['side'] = 'local'
            remote_cell = empty_cell()
            remote_cell['metadata']['side'] = 'remote'
            if cell['metadata']['state'] == 'deleted' \
                    or cell['metadata']['state'] == 'unchanged':
                base_cell = copy.deepcopy(cell)
            else:
                base_cell = empty_cell()
            base_cell['metadata']['side'] = 'base'
            # This change is on the right.
            current_row = [
                cell,
                base_cell,
                remote_cell,
            ]
        elif state == 'added':
            # This change is between base and remote branches.
            # It can be an addition or a deletion.
            cell['metadata']['side'] = 'remote'
            if cell['metadata']['state'] == 'unchanged':
                # This side doesn't have the change; wait
                # until we encounter the change to create the row.
                continue
            if cell['metadata']['state'] == 'deleted':
                base_cell = copy.deepcopy(cell)
                base_cell['metadata']['state'] = 'unchanged'
                local_cell = copy.deepcopy(cell)
                local_cell['metadata']['state'] = 'unchanged'
            else:
                base_cell = empty_cell()
                local_cell = empty_cell()
            base_cell['metadata']['side'] = 'base'
            local_cell['metadata']['side'] = 'local'
            current_row = [
                local_cell,
                base_cell,
                cell,
            ]
        elif state == 'unchanged':
            # The same item occurs between base-local and base-remote.
            # This happens if both branches made the same change, whether
            # that is an addition or deletion. If neither branches
            # changed a given cell, that cell shows up here too.
            cell1 = copy.deepcopy(cell)
            cell3 = copy.deepcopy(cell)
            if cell['metadata']['state'] == 'deleted' \
                    or cell['metadata']['state'] == 'unchanged':
                # If the change is a deletion, the cell-to-be-deleted
                # should in the base as 'unchanged'. The user will
                # choose to make it deleted.
                cell2 = copy.deepcopy(cell)
                cell2['metadata']['state'] = 'unchanged'
            else:
                # If the change is an addition, it should not
                # show in the base; the user must add it to the merged version.
                cell2 = empty_cell()
            cell1['metadata']['side'] = 'local'
            cell2['metadata']['side'] = 'base'
            cell3['metadata']['side'] = 'remote'
            current_row = [
                cell1,
                cell2,
                cell3,
            ]

        rows.append(current_row)

    # Chain all rows together; create a flat array from the nested array.
    # Use the base notebook's notebook-level metadata (title, version, etc.)

    result_notebook = local
    if len(result_notebook['worksheets']) == 0:
        result_notebook['worksheets'] = [nbformat.new_worksheet()]

    new_cell_array = list(it.chain.from_iterable(rows))
    result_notebook['worksheets'][0]['cells'] = new_cell_array

    result_notebook['metadata']['nbdiff-type'] = 'merge'

    return result_notebook


def get_cells(notebook, check_modified=False):
    try:
        cells = [
            comparable.CellComparator(cell, check_modified=check_modified)
            for cell in
            notebook['worksheets'][0]['cells']
        ]
    except IndexError:
        cells = []
    except KeyError:
        cells = []
    return cells

########NEW FILE########
__FILENAME__ = nbdiff
#!/usr/bin/env python
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = notebook_diff
from .diff import diff
from .comparable import CellComparator, LineComparator


def notebook_diff(nb1, nb2, check_modified=True):
    """Unify two notebooks into a single notebook with diff metadata.

    The result of this function is a valid notebook that can be loaded
    by the IPython Notebook front-end. This function adds additional
    cell metadata that the front-end Javascript uses to render the diffs.

    Parameters
    ----------
    nb1 : dict
        An IPython Notebook to use as the baseline version.
    nb2 : dict
        An IPython Notebook to compare against the baseline.
    check_modified : bool
        Whether or not to detect cell modification.

    Returns
    -------
    nb : A valid notebook containing diff metadata.
    """
    nb1_cells = nb1['worksheets'][0]['cells']
    nb2_cells = nb2['worksheets'][0]['cells']

    diffed_nb = cells_diff(nb1_cells, nb2_cells, check_modified=check_modified)
    line_diffs = diff_modified_items(diffed_nb)

    cell_list = list()
    for i, item in enumerate(diffed_nb):
        cell = diff_result_to_cell(item)
        if i in line_diffs:
            cell['metadata']['extra-diff-data'] = line_diffs[i]
        cell_list.append(cell)

    nb1['worksheets'][0]['cells'] = cell_list
    nb1['metadata']['nbdiff-type'] = 'diff'

    return nb1


def diff_modified_items(cellslist):
    result = {}
    for i in range(len(cellslist)):
        if cellslist[i]['state'] == 'modified':
            if cellslist[i]['originalvalue'].data['cell_type'] == 'heading':
                result[i] = diff(
                    cellslist[i]['originalvalue'].data["source"].split(),
                    cellslist[i]['modifiedvalue'].data["source"].split(),
                )
            else:
                result[i] = diff(
                    cellslist[i]['originalvalue'].data["input"].splitlines(),
                    cellslist[i]['modifiedvalue'].data["input"].splitlines(),
                )
    return result


def diff_result_to_cell(item):
    '''diff.diff returns a dictionary with all the information we need,
    but we want to extract the cell and change its metadata.'''
    state = item['state']
    if state == 'modified':
        new_cell = item['modifiedvalue'].data
        old_cell = item['originalvalue'].data
        new_cell['metadata']['state'] = state
        new_cell['metadata']['original'] = old_cell
        cell = new_cell
    else:
        cell = item['value'].data
        cell['metadata']['state'] = state
    return cell


def cells_diff(before_cells, after_cells, check_modified=False):
    '''Diff two arrays of cells.'''
    before_comps = [
        CellComparator(cell, check_modified=check_modified)
        for cell in before_cells
    ]
    after_comps = [
        CellComparator(cell, check_modified=check_modified)
        for cell in after_cells
    ]
    diff_result = diff(
        before_comps,
        after_comps,
        check_modified=check_modified
    )
    return diff_result


def words_diff(before_words, after_words):
    '''Diff the words in two strings.

    This is intended for use in diffing prose and other forms of text
    where line breaks have little semantic value.

    Parameters
    ----------
    before_words : str
        A string to be used as the baseline version.
    after_words : str
        A string to be compared against the baseline.

    Returns
    -------
    diff_result : A list of dictionaries containing diff information.
    '''
    before_comps = before_words.split()
    after_comps = after_words.split()

    diff_result = diff(
        before_comps,
        after_comps
    )
    return diff_result


def lines_diff(before_lines, after_lines, check_modified=False):
    '''Diff the lines in two strings.

    Parameters
    ----------
    before_lines : iterable
        Iterable containing lines used as the baseline version.
    after_lines : iterable
        Iterable containing lines to be compared against the baseline.

    Returns
    -------
    diff_result : A list of dictionaries containing diff information.
    '''
    before_comps = [
        LineComparator(line, check_modified=check_modified)
        for line in before_lines
    ]
    after_comps = [
        LineComparator(line, check_modified=check_modified)
        for line in after_lines
    ]
    diff_result = diff(
        before_comps,
        after_comps,
        check_modified=check_modified
    )
    return diff_result

########NEW FILE########
__FILENAME__ = notebook_parser
import IPython.nbformat.current as current


class NotebookParser(object):
    """Parser for IPython Notebook files."""
    def parse(self, json_data):
        """Parse a notebook .ipynb file.

        Parameters
        ----------
        json_data : file
            A file handle for an .ipynb file.

        Returns
        -------
        nb : An IPython Notebook data structure.
        """
        data = current.read(json_data, 'ipynb')
        json_data.close()
        return data

    # param:
    # json_data_string: raw unicode string
    def parseString(self, json_data_string):
        return current.reads(json_data_string, 'ipynb')

########NEW FILE########
__FILENAME__ = AboutUsCommand
from . import BaseCommand
from flask import render_template


class AboutUsCommand(BaseCommand):

    def process(self, request, filename, db_session):
        return render_template('aboutUs.html')


def newInstance():
    return AboutUsCommand()

########NEW FILE########
__FILENAME__ = ComparisonCommand
from . import BaseCommand
from flask import render_template
from nbdiff.server.database.nbdiffModel import nbdiffModel
from sqlalchemy.exc import OperationalError


class ComparisonCommand(BaseCommand):

    def process(self, request, filename, db_session):

        try:
            nbdiffModelObj = nbdiffModel.query.filter(
                nbdiffModel.id == filename
            ).first()
        except OperationalError:
            print """The database is not initialized.
                Please restart server with argument init_db"""
            errMsg = """There was an error with the database. <br/>
               Please contact administrator to resolve this issue."""
            return render_template('Error.html', err=errMsg)
        except:
            errMsg = """There was an unexpected error with the database. <br/>
                Please try again later. <br/>
                If this problem persists please contact administrator."""
            return render_template('Error.html', err=errMsg)

        # check that nbdiffModelObj exists before redirecting to nbdiff.html.
        # Either the Comparison does not exist or expired from server
        # and was dropped from Database.
        if nbdiffModelObj is None:
            errMsg = """The Merge or Diff is not available. <br/>
                Either the Merge or Diff expired or does not exist. <br/>
                Please return to the Home Page to
                request another comparison."""
            return render_template('Error.html', err=errMsg)
        else:
            return render_template(
                'nbdiff.html',
                project='/',
                base_project_url='/',
                base_kernel_url='/',
                notebook_id=filename,
                local=False
            )


def newInstance():
    return ComparisonCommand()

########NEW FILE########
__FILENAME__ = ContactUsCommand
from . import BaseCommand
from flask import render_template


class ContactUsCommand(BaseCommand):

    def process(self, request, filename, db_session):
        return render_template('contactUs.html')


def newInstance():
    return ContactUsCommand()

########NEW FILE########
__FILENAME__ = DiffCommand
from . import BaseCommand
from flask import redirect, render_template
from ...notebook_parser import NotebookParser
from ...notebook_diff import notebook_diff
from nbdiff.server.database.nbdiffModel import nbdiffModel
from werkzeug.exceptions import BadRequestKeyError
from sqlalchemy.exc import OperationalError
import json
import bitarray
import IPython.nbformat.current as nbformat


class DiffCommand(BaseCommand):

    def process(self, request, filename, db_session):
        errMsg = ""
        parser = NotebookParser()

        try:
            before = request.form['beforeJSON']
            after = request.form['afterJSON']
        except BadRequestKeyError:
            errMsg = """Invalid notebook Diff Request. <br/>
                Please return to the home page and submit the request again."""
            return render_template('Error.html', err=errMsg)

        try:
            nb_before = parser.parseString(before)
        except nbformat.NotJSONError:
            errMsg = errMsg + """The Before notebook contains
                invalid JSON data. <br/>"""
        try:
            nb_after = parser.parseString(after)
        except nbformat.NotJSONError:
            errMsg = errMsg + """The After notebook contains
                invalid JSON data. <br/>"""

        if len(errMsg) == 0:

            diffNotebook = notebook_diff(nb_before, nb_after)

            # bitarray used to convert notebook to binary for BLOB
            ba = bitarray.bitarray()
            ba.fromstring(json.dumps(diffNotebook, indent=2))

            # object to be saved to database
            obj = nbdiffModel(ba.to01())

            # add to database and commit it.
            try:
                db_session.add(obj)
                db_session.commit()
            except OperationalError:
                db_session.rollback()
                print """The database is not initialized.
                    Please restart server with argument init_db"""
                errMsg = """There was an error with the database. <br/>
                   Please contact administrator to resolve this issue."""
                return render_template('Error.html', err=errMsg)
            except:
                db_session.rollback()
                errMsg = """There was an unexpected error with the database.
                    <br/>Please try again later. <br/>
                    If this problem persists please contact administrator."""
                return render_template('Error.html', err=errMsg)

            # return the id of the object.
            nb_id = obj.id

            # redirect is used because we want
            # user to have a easier url to return to.
            return redirect("/Comparison/"+str(nb_id), code=302)
        else:
            return render_template('Error.html', err=errMsg)


def newInstance():
    return DiffCommand()

########NEW FILE########
__FILENAME__ = DiffURLCommand
from . import BaseCommand
from flask import redirect, render_template
from ...notebook_parser import NotebookParser
from ...notebook_diff import notebook_diff
from nbdiff.server.database.nbdiffModel import nbdiffModel
from werkzeug.exceptions import BadRequestKeyError
from sqlalchemy.exc import OperationalError
import urllib2
import json
import bitarray
import IPython.nbformat.current as nbformat


class DiffURLCommand(BaseCommand):

    def process(self, request, filename, db_session):
        errMsg = ""
        parser = NotebookParser()
        # Max Size of a notebook accepted is 20M.
        max_size = 20*1024*1024

        try:
            beforeURL = request.form['beforeURL']
            afterURL = request.form['afterURL']
        except BadRequestKeyError:
            errMsg = """Invalid notebook Diff Request. <br/>
                Please return to the home page and submit the request again."""
            return render_template('Error.html', err=errMsg)

        try:
            beforeFile = urllib2.urlopen(beforeURL)
            if int(beforeFile.info()['Content-Length']) > max_size:
                errMsg = errMsg + """The Before notebook exceeds 20MB.
                    Only notebooks below 20MB are accepted.<br/>"""
        except:
            errMsg = errMsg + """We are unable to access the Before
                notebook file from the given URL.<br/>"""

        try:
            afterFile = urllib2.urlopen(afterURL)
            if int(afterFile.info()['Content-Length']) > max_size:
                errMsg = errMsg + """The After notebook exceeds 20MB.
                    Only notebooks below 20MB are accepted.<br/>"""
        except:
            errMsg = errMsg + """We are unable to access the After
                notebook file from the given URL.<br/>"""

        if len(errMsg) == 0:
            try:
                nb_before = parser.parse(beforeFile)
            except nbformat.NotJSONError:
                errMsg = errMsg + """The Before notebook contains
                    invalid JSON data. <br/>"""
            try:
                nb_after = parser.parse(afterFile)
            except nbformat.NotJSONError:
                errMsg = errMsg + """The After notebook contains
                    invalid JSON data. <br/>"""

            beforeFile.close()
            afterFile.close()

        if len(errMsg) == 0:
            diffedNotebook = notebook_diff(nb_before, nb_after)

            # bitarray used to convert notebook to binary for BLOB
            ba = bitarray.bitarray()
            ba.fromstring(json.dumps(diffedNotebook, indent=2))

            # object to be saved to database
            obj = nbdiffModel(ba.to01())

            # add to database and commit it.
            try:
                db_session.add(obj)
                db_session.commit()
            except OperationalError:
                db_session.rollback()
                print """The database is not initialized.
                    Please restart server with argument init_db."""
                errMsg = """There was an error with the database. <br/>
                   Please contact administrator to resolve this issue."""
                return render_template('Error.html', err=errMsg)
            except:
                db_session.rollback()
                errMsg = """There was an unexpected error with the database.
                    <br/>Please try again later. <br/>
                    If this problem persists please contact administrator."""
                return render_template('Error.html', err=errMsg)

            # return the id of the object.
            nb_id = obj.id

            # redirect is used because we want
            # user to have a easier url to return to.
            return redirect("/Comparison/"+str(nb_id), code=302)
        else:
            return render_template('Error.html', err=errMsg)


def newInstance():
    return DiffURLCommand()

########NEW FILE########
__FILENAME__ = FaqCommand
from . import BaseCommand
from flask import render_template


class FaqCommand(BaseCommand):

    def process(self, request, filename, db_session):
        return render_template('faq.html')


def newInstance():
        return FaqCommand()

########NEW FILE########
__FILENAME__ = MergeCommand
from . import BaseCommand
from flask import redirect, render_template
from ...notebook_parser import NotebookParser
from ...merge import notebook_merge
from nbdiff.server.database.nbdiffModel import nbdiffModel
from werkzeug.exceptions import BadRequestKeyError
from sqlalchemy.exc import OperationalError
import json
import bitarray
import IPython.nbformat.current as nbformat


class MergeCommand(BaseCommand):

    def process(self, request, filename, db_session):

        errMsg = ""
        parser = NotebookParser()

        try:
            local = request.form['localJSON']
            remote = request.form['remoteJSON']
            base = request.form['baseJSON']
        except BadRequestKeyError:
            errMsg = """Invalid notebook Merge Request. <br/>
                Please return to the home page and submit the request again."""
            return render_template('Error.html', err=errMsg)

        try:
            nb_local = parser.parseString(local)
        except nbformat.NotJSONError:
            errMsg = errMsg + """The Local notebook contains
                invalid JSON data. <br/>"""
        try:
            nb_base = parser.parseString(base)
        except nbformat.NotJSONError:
            errMsg = errMsg + """The Base notebook contains
                invalid JSON data. <br/>"""
        try:
            nb_remote = parser.parseString(remote)
        except nbformat.NotJSONError:
            errMsg = errMsg + """The Remote notebook contains
                invalid JSON data. <br/>"""

        if len(errMsg) == 0:

            mergedNotebook = notebook_merge(nb_local, nb_base, nb_remote)

            # bitarray used to convert notebook to binary for BLOB
            ba = bitarray.bitarray()
            ba.fromstring(json.dumps(mergedNotebook, indent=2))

            # object to be saved to database
            obj = nbdiffModel(ba.to01())

            # add to database and commit it.
            try:
                db_session.add(obj)
                db_session.commit()
            except OperationalError:
                db_session.rollback()
                print """The database is not initialized.
                    Please restart server with argument init_db"""
                errMsg = """There was an error with the database. <br/>
                   Please contact administrator to resolve this issue."""
                return render_template('Error.html', err=errMsg)
            except:
                db_session.rollback()
                errMsg = """There was an unexpected error with
                    the database. <br/>Please try again later. <br/>
                    If this problem persists please contact administrator."""
                return render_template('Error.html', err=errMsg)

            # return the id of the object.
            nb_id = obj.id

            # redirect is used because we want user
            # to have a easier url to return to.
            return redirect("/Comparison/"+str(nb_id), code=302)
        else:
            return render_template('Error.html', err=errMsg)


def newInstance():
    return MergeCommand()

########NEW FILE########
__FILENAME__ = MergeURLCommand
from . import BaseCommand
from flask import redirect, render_template
from ...notebook_parser import NotebookParser
from ...merge import notebook_merge
from nbdiff.server.database.nbdiffModel import nbdiffModel
from werkzeug.exceptions import BadRequestKeyError
from sqlalchemy.exc import OperationalError
import urllib2
import json
import bitarray
import IPython.nbformat.current as nbformat


class MergeURLCommand(BaseCommand):

    def process(self, request, filename, db_session):
        errMsg = ""
        parser = NotebookParser()
        # Max Size of a notebook accepted is 20M.
        max_size = 20*1024*1024

        try:
            localURL = request.form['localURL']
            baseURL = request.form['baseURL']
            remoteURL = request.form['remoteURL']
        except BadRequestKeyError:
            errMsg = """Invalid notebook Merge Request.
                <br/>Please return to the home page and
                submit the request again."""
            return render_template('Error.html', err=errMsg)

        try:
            localFile = urllib2.urlopen(localURL)
            if int(localFile.info()['Content-Length']) > max_size:
                errMsg = errMsg + """The Local notebook
                    exceeds 20MB. Only notebooks below
                    20MB are accepted.<br/>"""
        except:
            errMsg = errMsg + """We are unable to access
                the Local notebook file from the
                given URL.<br/>"""

        try:
            baseFile = urllib2.urlopen(baseURL)
            if int(baseFile.info()['Content-Length']) > max_size:
                errMsg = errMsg + """The Base notebook
                    exceeds 20MB. Only notebooks below
                    20MB are accepted.<br/>"""
        except:
            errMsg = errMsg + """We are unable to access
                the Base notebook file from the given
                URL.<br/>"""

        try:
            remoteFile = urllib2.urlopen(remoteURL)
            if int(remoteFile.info()['Content-Length']) > max_size:
                errMsg = errMsg + """The Remote notebook
                    exceeds 20MB. Only notebooks below
                    20MB are accepted.<br/>"""
        except:
            errMsg = errMsg + """We are unable to access
                the Remote notebook file from
                the given URL.<br/>"""

        if len(errMsg) == 0:
            try:
                nb_local = parser.parse(localFile)
            except nbformat.NotJSONError:
                errMsg = errMsg + """The Local notebook
                    contains invalid JSON data. <br/>"""
            try:
                nb_base = parser.parse(baseFile)
            except nbformat.NotJSONError:
                errMsg = errMsg + """The Base notebook
                    contains invalid JSON data. <br/>"""
            try:
                nb_remote = parser.parse(remoteFile)
            except nbformat.NotJSONError:
                errMsg = errMsg + """The Remote notebook
                    contains invalid JSON data. <br/>"""

            localFile.close()
            baseFile.close()
            remoteFile.close()

        if len(errMsg) == 0:
            mergedNotebook = notebook_merge(nb_local, nb_base, nb_remote)

            # bitarray used to convert notebook to binary for BLOB
            ba = bitarray.bitarray()
            ba.fromstring(json.dumps(mergedNotebook, indent=2))

            # object to be saved to database
            obj = nbdiffModel(ba.to01())

            # add to database and commit it.
            try:
                db_session.add(obj)
                db_session.commit()
            except OperationalError:
                db_session.rollback()
                print """The database is not initialized.
                    Please restart server with argument init_db"""
                errMsg = """There was an error with the database. <br/>
                   Please contact administrator to resolve this issue."""
                return render_template('Error.html', err=errMsg)
            except:
                db_session.rollback()
                errMsg = """There was an unexpected error with the database.
                    <br/>Please try again later. <br/>
                    If this problem persists please contact administrator."""
                return render_template('Error.html', err=errMsg)

            # return the id of the object.
            nb_id = obj.id

            # redirect is used because we want users
            # to have a easier url to return to.
            return redirect("/Comparison/"+str(nb_id), code=302)
        else:
            return render_template('Error.html', err=errMsg)


def newInstance():
    return MergeURLCommand()

########NEW FILE########
__FILENAME__ = NotebookRequestCommand
from . import BaseCommand
from nbdiff.server.database.nbdiffModel import nbdiffModel
import bitarray


class NotebookRequestCommand(BaseCommand):

    def process(self, request, filename, db_session):

        # query for the notebook in database.
        nbdiffModelObj = nbdiffModel.query.filter(
            nbdiffModel.id == filename
        ).first()

        # bitarray used to convert BlOB to notebook data.
        notebook = bitarray.bitarray(nbdiffModelObj.notebook).tostring()
        return notebook


def newInstance():
    return NotebookRequestCommand()

########NEW FILE########
__FILENAME__ = ResourceRequestCommand
from . import BaseCommand
from flask import send_from_directory
import os


class ResourceRequestCommand(BaseCommand):

    def process(self, request, filename, db_session):
        return send_from_directory(
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..")
            ) + '/static',
            filename
        )


def newInstance():
    return ResourceRequestCommand()

########NEW FILE########
__FILENAME__ = SaveNotebookCommand
from . import BaseCommand
from flask import make_response
from IPython.nbformat import current
from unicodedata import normalize


class SaveNotebookCommand(BaseCommand):

    def process(self, request, filename, db_session):
        # format for notebook.
        format = u'json'
        data = request.form['download_data']

        try:
            # read notebook and format it.
            nb = current.reads(data.decode('utf-8'), format)
        except:
            return "Unable to save notebook. Invalid JSON data"

        # if notebook has a name we use it else use a generic name
        try:
            name = nb.metadata.name
        except:
            name = "mergedNotebook"
            nb.metadata.name = name

        name = normalize('NFC', nb.metadata.name)

        # uses ipython's current ipynb formatting.
        notebook_formatted = current.writes(nb, format)

        # make a file download response
        response = make_response(notebook_formatted)
        header = "attachment; filename=mergedNotebook.ipynb"
        response.headers["Content-Type"] = "text/plain"
        response.headers["Content-Disposition"] = header

        return response


def newInstance():
    return SaveNotebookCommand()

########NEW FILE########
__FILENAME__ = UploadCommand
from . import BaseCommand
from flask import render_template


class UploadCommand(BaseCommand):

    def process(self, request, filename, db_session):
        return render_template('upload.html')


def newInstance():
    return UploadCommand()

########NEW FILE########
__FILENAME__ = nbdiffModel
from sqlalchemy import Integer, Binary, Column
from nbdiff.server.database import Base


class nbdiffModel(Base):
    __tablename__ = 'nbdiffResult'
    id = Column(Integer, primary_key=True)
    notebook = Column('notebook', Binary)

    def __init__(self, notebook):
        self.notebook = notebook

    def __repr__(self):
        return '<Notebook %r>' % (self.notebook)

########NEW FILE########
__FILENAME__ = local_server
from flask import Flask, render_template, send_from_directory, request
import jinja2
import json
import IPython.html
import os


class NbFlask(Flask):
    jinja_loader = jinja2.FileSystemLoader([
        IPython.html.__path__[0] + '/templates',
        os.path.dirname(os.path.realpath(__file__)) + '/templates'
    ])

    notebooks = []

    def shutdown_callback(self, callback):
        self.shutdown = callback

    def add_notebook(self, nb, fname):
        self.notebooks.append((nb, fname))

app = NbFlask(__name__, static_folder=IPython.html.__path__[0] + '/static')


@app.route('/nbdiff/<path:filename>')
def nbdiff_static(filename):
    return send_from_directory(os.path.dirname(os.path.realpath(__file__))
                               + '/static', filename)


@app.route('/<int:notebookid>')
def home(notebookid):
    return render_template(
        'nbdiff.html',
        project='/',
        base_project_url='/',
        base_kernel_url='/',
        static_url=static_url,
        notebook_id='test_notebook' + str(notebookid),
        notebook_name='test_notebook' + str(notebookid),
        notebookName='test_notebook' + str(notebookid),
        notebook_path='./',
        notebookPath='./',
        num_nbks=str(len(app.notebooks)),
        cur_nbk=str(notebookid),
        local=True,
    )


# IPython 1.1.0
@app.route('/notebooks/test_notebook<int:notebookid>', methods=['GET', 'PUT'])
def notebookjson(notebookid):
    if request.method == 'PUT':
        app.shutdown(request.data, app.notebooks[notebookid][1])
        return ""
    else:
        parsed, filename = app.notebooks[notebookid]
        parsed['metadata']['filename'] = filename
        return json.dumps(parsed)


# IPython 2.0.0
# TODO refactor to handle both URIs with same function.
@app.route('/api/notebooks/test_notebook<int:notebookid>',
           methods=['GET', 'PUT'])
def notebook(notebookid):
    if request.method == 'PUT':
        request_data = json.loads(request.data)
        content = request_data['content']
        app.shutdown(json.dumps(content), app.notebooks[notebookid][1])
        return ""
    else:
        parsed, filename = app.notebooks[notebookid]
        parsed['metadata']['filename'] = filename
        dump = {'content': parsed}
        dump['name'] = 'test_notebook{:d}'.format(notebookid)
        dump['path'] = './'
        dump['type'] = 'notebook'
        return json.dumps(dump)


@app.route('/shutdown')
def shutdown():
    request.environ.get('werkzeug.server.shutdown')()
    return "The server was shutdown."


def static_url(path, **kwargs):
    # FIXME obvious kludge
    if 'underscore' in path or 'backbone' in path:
        return path[:-3]
    else:
        return 'static/' + path


if __name__ == '__main__':
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = remote_server
from flask import Flask, request, render_template
from nbdiff.server.database import db_session
from nbdiff.server.database import init_db
import sys
import jinja2
import IPython.html
import os


# initialize database if argument 'True' is passed
if len(sys.argv) > 1:
    if(sys.argv[1].lower() == "init_db"):
        init_db()


class RemoteNbFlask(Flask):
    jinja_loader = jinja2.FileSystemLoader([
        IPython.html.__path__[0] + '/templates',
        os.path.dirname(os.path.realpath(__file__)) + '/templates'
    ])

    def shutdown_callback(self, callback):
        self.shutdown = callback
        db_session.remove()

app = RemoteNbFlask(
    __name__,
    static_folder=IPython.html.__path__[0] + '/static'
)


def get_class(classname):
    components = classname.split('.')
    try:
        obj = __import__(classname)
    except ImportError:
        raise ImportError

    for comp in components[1:]:
        obj = getattr(obj, comp)
    return obj


def run_command(cmdName, request, filename=None):
    cmd = "nbdiff.server.command."+cmdName+"Command"
    try:
        command = get_class(cmd).newInstance()
    except ImportError:
        errMsg = "404: The page requested does not Exist!"
        return render_template('Error.html', err=errMsg)
    return command.process(request, filename, db_session())


# index
@app.route("/")
def upload():
    return run_command("Upload", request)


# runs depending on different command URL
@app.route("/<path:command>", methods=['GET', 'POST'])
def redirectCommand(command):
    # favicon.ico is a resource requested by Ipython notebook.
    # Since it does not follow command pattern this will
    # redirect to proper command
    if command == "favicon.ico":
        url = "image/favicon.ico"
        return run_command("ResourceRequest", request, url)
    else:
        return run_command(command, request)


# notebook request handler
@app.route('/notebooks/<path:filename>', methods=['GET', 'PUT'])
def notebookRequest(filename):
    return run_command("NotebookRequest", request, filename)


# used to get specific resources in the html pages.
@app.route('/nbdiff/<path:filename>')
def nbdiff_static(filename):
    return run_command("ResourceRequest", request, filename)


# Redirect from Merge, MergeURL, Diff, DiffURL commands.
# Used to simplify URL for users who wish to go back to their comparison.
@app.route('/Comparison/<path:filename>')
def comparisonURL(filename):
    return run_command("Comparison", request, filename)

if __name__ == "__main__":
    app.debug = False
    app.run()

########NEW FILE########
__FILENAME__ = gen_benchmark_notebook
# generate two notebook files that are large enough for benchmarking.

import IPython.nbformat.current as nbformat
import random


def new_code_cell():
    nlines = random.randint(0, 30)
    input = [
        str(random.random())
        for i in range(nlines)
    ]
    code_cell = nbformat.new_code_cell(input=input)
    return code_cell


cells = [
    new_code_cell()
    for i in range(100)
]

worksheet = nbformat.new_worksheet(cells=cells)

nb = nbformat.new_notebook(name='Test Notebook')

nb['worksheets'].append(worksheet)

with open('nb1.ipynb', 'w') as out:
    nbformat.write(nb, out, 'ipynb')


cells = nb['worksheets'][0]['cells']


# Take original notebook and make changes to it
ncells = len(cells)
to_change = [random.choice(list(range(ncells))) for i in range(10)]
for tc in to_change:
    input = cells[tc]['input']
    ninput = len(input)
    to_delete = [random.choice(list(range(ninput))) for i in range(10)]
    for td in to_delete:
        if td < len(input):
            del input[td]
    cells[tc]['input'] = input

ncells = len(cells)
removed = [random.choice(list(range(ncells))) for i in range(10)]
for r in removed:
    if r < len(cells):
        del cells[r]

nb['worksheets'][0]['cells'] = cells


with open('nb2.ipynb', 'w') as out:
    nbformat.write(nb, out, 'ipynb')



########NEW FILE########
__FILENAME__ = make_diff
#!/usr/bin/env python

# Tavish Armstrong (c) 2013
#
# make_diff.py
#
# Make a new git repository, add a notebook, and then modify it.
# nbdiff should then be able to show a diff.


import os
import subprocess
import random
import hashlib
import sys
from util import copy_example_files

SCRIPTS_DIR = os.path.realpath(os.path.dirname(__file__))
EXAMPLE_NOTEBOOKS = os.path.join(SCRIPTS_DIR, 'example-notebooks/diff/')

example_diff_notebooks = os.listdir(EXAMPLE_NOTEBOOKS)

randpart = hashlib.sha1(str(random.random())).hexdigest()[:4]

folder_name = "merge-diff-testfolder-{}".format(randpart)
os.mkdir(folder_name)
os.chdir(folder_name)

subprocess.check_output('git init'.split())


copy_example_files('before.ipynb', EXAMPLE_NOTEBOOKS, example_diff_notebooks)

subprocess.check_output(['git', 'commit', '-am', 'b'])

copy_example_files('after.ipynb',EXAMPLE_NOTEBOOKS, example_diff_notebooks, add=False)

print 'Diffable notebook available in folder: \n' + folder_name


########NEW FILE########
__FILENAME__ = make_merge_conflict
#!/usr/bin/env python

# Tavish Armstrong (c) 2013
#
# make_merge_conflict.py
#
# Make a new directory, initialize a git repository within, and cause a merge conflict.
# Yes. On purpose.

import os
import subprocess
import random
import hashlib
import sys
from util import copy_example_files
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--mercurial', '-m', action='store_true', default=False)

args = parser.parse_args()
MERCURIAL = args.mercurial

VCS_CMD = MERCURIAL and 'hg' or 'git'

SCRIPTS_DIR = os.path.realpath(os.path.dirname(__file__))
EXAMPLE_NOTEBOOKS = os.path.join(SCRIPTS_DIR, 'example-notebooks/merge/')

example_merge_notebooks = os.listdir(EXAMPLE_NOTEBOOKS)

randpart = hashlib.sha1(str(random.random())).hexdigest()[:4]
folder_name = "merge-conflict-testfolder-{}".format(randpart)

os.mkdir(folder_name)
os.chdir(folder_name)

subprocess.check_output([VCS_CMD, 'init'])

copy_example_files('base.ipynb', EXAMPLE_NOTEBOOKS, example_merge_notebooks, vcs_cmd=VCS_CMD)

if MERCURIAL:
    subprocess.check_output(['hg', 'commit', '-A', '-m', 'b'])
    subprocess.check_output('hg bookmark main'.split())
    subprocess.check_output('hg bookmark friend'.split())
    subprocess.check_output('hg update friend'.split())
else:
    subprocess.check_output(['git', 'commit', '-am', 'b'])
    subprocess.check_output('git checkout -b your-friends-branch'.split())


copy_example_files('remote.ipynb', EXAMPLE_NOTEBOOKS, example_merge_notebooks, vcs_cmd=VCS_CMD)

if MERCURIAL:
    subprocess.check_output(['hg', 'commit', '-A', '-m', 'r'], stderr=sys.stdout)
    subprocess.check_output('hg update main'.split())
else:
    subprocess.check_output(['git', 'commit', '-am', 'r'], stderr=sys.stdout)
    subprocess.check_output('git checkout master'.split())

copy_example_files('local.ipynb',EXAMPLE_NOTEBOOKS,  example_merge_notebooks, vcs_cmd=VCS_CMD)

if MERCURIAL:
    subprocess.check_output(['hg', 'commit', '-A', '-m', 'l'])
else:
    subprocess.check_output(['git', 'commit', '-am', 'l'])


try:
    print 'Attempting merge in:\n{}'.format(folder_name)
    if MERCURIAL:
        subprocess.check_output('hg merge friend -t nbmerge'.split())
    else:
        subprocess.check_output('git merge your-friends-branch'.split())
except:
    print 'Conflict!'
    print folder_name



########NEW FILE########
__FILENAME__ = notebook_fileserver
from flask import Flask, render_template, send_from_directory, request
import jinja2
import json
import IPython.html
import os

static = os.path.abspath(os.path.dirname(__file__)) + '/example-notebooks'

app = Flask(
    __name__,
    static_folder=static,
)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

########NEW FILE########
__FILENAME__ = util
import os
import subprocess

def copy_example_files(fname, root, folders, vcs_cmd='git', add=True):
    for nb in folders:
        target_fname = 'test-{id}.ipynb'.format(id=nb)
        with open(target_fname, 'w') as f:
            ipynb_path = os.path.join(root, nb, fname)
            f.write(open(ipynb_path).read())
            if add:
                subprocess.check_output([vcs_cmd, 'add', target_fname])


########NEW FILE########
__FILENAME__ = test_specs
'''
This is an example of a python test
that compares a diff function (in this case
a hardcoded one that doesn't work) to the
reference JSON to check compliance.
'''
from nose.tools import eq_
import json

from nbdiff.diff import diff


def test_diffs():
    test_cases = json.load(open('test_cases_simple.json'))
    for test_case in test_cases:
        def gentest():
            result = diff(test_case['before'], test_case['after'])
            for (expected, actual) in zip(test_case['diff'], result):
                eq_(expected, actual)
        yield gentest


def test_diffs_cells():
    test_cases = json.load(open('test_cases_cells.json'))
    for test_case in test_cases:
        result = diff(test_case['before'], test_case['after'])
        def gentest():
            result = diff(test_case['before'], test_case['after'])
            for (expected, actual) in zip(test_case['diff'], result):
                eq_(expected, actual)
        yield gentest

########NEW FILE########
__FILENAME__ = test_commands
# flake8: noqa
from nbdiff import commands

########NEW FILE########
__FILENAME__ = test_diff
from nose.tools import eq_
import itertools as it

from nbdiff.diff import (
    add_results,
    find_candidates,
    find_matches,
    process_col,
    check_match,
    lcs,
    diff_points,
    create_grid,
    diff,
)


def test_create_grid():
    A = "abcabba"
    B = "cbabac"
    expected = [
        # c      b     a     b      a      c
        [False, False, True, False, True, False],  # a
        [False, True, False, True, False, False],  # b
        [True, False, False, False, False, True],  # c
        [False, False, True, False, True, False],  # a
        [False, True, False, True, False, False],  # b
        [False, True, False, True, False, False],  # b
        [False, False, True, False, True, False]   # a
    ]
    grid = create_grid(A, B)
    eq_(grid, expected)

    A, B = ("cabcdef", "abdef")
    grid = create_grid(A, B)
    assert len([True for col in grid if len(col) == 0]) == 0


# Regression test for bug #183
def test_empty_diff():
    result = diff([], [])
    assert len(result) == 0


# Regression test for bug #183
def test_empty_diff1():
    result = diff(['a'], [])
    assert len(result) == 1


# Regression test for bug #183
def test_empty_diff2():
    result = diff([], ['a'])
    assert len(result) == 1


def test_diff_points():
    A = [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']
    B = [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']

    grid = create_grid(A, B)

    result = diff_points(grid)

    expected = [
        ('deleted', 0, None),
        ('added', None, 0),
        ('unchanged', 1, 1),
        ('unchanged', 2, 2),
        ('deleted', 3, None),
        ('added', None, 3),
    ]
    eq_(result, expected)


def test_find_candidates():
    grid = [
        [False, False, True, False, True, False],
        [False, True, False, True, False, False],
        [True, False, False, False, False, True],
        [False, False, True, False, True, False],
        [False, True, False, True, False, False],
        [False, True, False, True, False, False],
        [False, False, True, False, True, False]
    ]
    result = find_candidates(grid)
    expected = {
        1: [(0, 2), (1, 1), (2, 0)],
        2: [(1, 3), (3, 2), (4, 1)],
        3: [(2, 5), (3, 4), (4, 3), (6, 2)],
        4: [(6, 4)],
    }
    eq_(result, expected)

    grid = [
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True]
    ]
    result = find_candidates(grid)
    expected = {1: [(0, 1)], 2: [(1, 2)]}
    eq_(result, expected)


def test_lcs():
    grid = [
        [False, False, True, False, True, False],
        [False, True, False, True, False, False],
        [True, False, False, False, False, True],
        [False, False, True, False, True, False],
        [False, True, False, True, False, False],
        [False, True, False, True, False, False],
        [False, False, True, False, True, False]
    ]
    result = lcs(grid)
    expected = [(1, 1), (3, 2), (4, 3), (6, 4)]
    eq_(result, expected)

    grid = [
        [False, False, True, False, True, False],
        [False, False, False, True, False, False],
        [True, False, False, False, False, True],
        [False, False, True, False, True, False],
        [False, True, False, True, False, False],
        [False, True, False, True, False, False],
        [False, False, True, False, True, False]
    ]
    result = lcs(grid)
    expected = [(2, 0), (3, 2), (4, 3), (6, 4)]
    eq_(result, expected)

    grid = [
        [True, True, True, True, True, True],
        [True, True, True, True, True, True],
        [True, True, True, True, True, True],
        [True, True, True, True, True, True],
        [True, True, True, True, True, True],
        [True, True, True, True, True, True],
        [True, True, True, True, True, True]
    ]
    result = lcs(grid)
    expected = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
    eq_(result, expected)

    grid = [
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True],
        [False, True, True]
    ]
    result = lcs(grid)
    expected = [(0, 1), (1, 2)]
    eq_(result, expected)


def test_lcs_noequals():
    # See issue #128
    grid = [[False, False], [False, False]]
    result = lcs(grid)
    eq_(result, [])


def test_add_results():
    k = {1: [(0, 2)]}
    newk = {1: [(1, 1)], 2: [(1, 3)]}
    result = add_results(k, newk)
    expected = {1: [(0, 2), (1, 1)], 2: [(1, 3)]}
    eq_(result, expected)


def test_find_matches():
    A = "abcabba"
    B = "cbabac"
    prod = list(it.product(A, B))
    grid = [
        [
            a == b
            for (a, b) in
            prod
        ][i * len(B):i * len(B) + len(B)]
        for i in range(len(A))
    ]
    colNum = 0
    result = find_matches(grid[colNum], colNum)
    expected = [(0, 2), (0, 4)]
    eq_(result, expected)


def test_process_col():
    d = {1: [(0, 2)]}
    a = [False, True, False, True, False, False]
    col = 1
    expected = {1: [(1, 1)], 2: [(1, 3)]}
    result = process_col(d, a, col)
    eq_(result, expected)

    d = {}
    a = [False, True, False, True, False, False]
    col = 1
    expected = {1: [(1, 1)]}
    result = process_col(d, a, col)
    eq_(result, expected)

    d = {1: [(0, 2)]}
    a = [False, True, False, True, False, True]
    col = 1
    expected = {1: [(1, 1)], 2: [(1, 3)]}
    result = process_col(d, a, col)
    eq_(result, expected)

    d = {1: [(0, 2), (1, 1), (2, 0)], 2: [(1, 3)], 3: [(2, 5)]}
    a = [False, False, False, False, True, False]
    col = 3
    expected = {3: [(3, 4)]}
    result = process_col(d, a, col)
    eq_(result, expected)

    grid = [
        [False, True, True],
        [False, True, True],
        [False, True, True],
    ]
    d = {1: [(0, 1)]}
    a = grid[1]
    col = 1
    expected = {2: [(1, 2)]}
    result = process_col(d, a, col)
    eq_(result, expected)

    d = {1: [(0, 1)], 2: [(1, 2)]}
    a = grid[2]
    col = 2
    expected = {}
    result = process_col(d, a, col)
    eq_(result, expected)


def test_check_match():
    point = (1, 3)
    k = {1: [(0, 2)]}
    expected = 2
    result = check_match(point, k)
    eq_(result, expected)

    point = (1, 1)
    k = {1: [(0, 2)]}
    expected = 1
    result = check_match(point, k)
    eq_(result, expected)

    point = (1, 2)
    k = {1: [(0, 2)]}
    expected = None
    result = check_match(point, k)
    eq_(result, expected)

    point = (3, 4)
    k = {1: [(0, 2), (1, 1), (2, 0)], 2: [(1, 3)], 3: [(2, 5)]}
    expected = 3
    result = check_match(point, k)
    eq_(result, expected)

    point = (2, 0)
    k = {1: [(0, 2), (1, 1)], 2: [(1, 3)]}
    expected = 1
    result = check_match(point, k)
    eq_(result, expected)

    point = (5, 1)
    k = {
        1: [(0, 2), (1, 1), (2, 0)],
        2: [(1, 3), (3, 2), (4, 1)],
        3: [(2, 5), (3, 4), (4, 3)]
    }
    expected = None
    result = check_match(point, k)
    eq_(result, expected)

    # print 'boop boop'
    point = (2, 1)
    k = {1: [(0, 1)], 2: [(1, 2)]}
    expected = None
    result = check_match(point, k)
    eq_(result, expected)


def test_modified():
    cell1 = {
        "cell_type": "code",
        "collapsed": False,
        "input": [
            "x",
            "x",
            "x",
            "x",
            "x",
            "x",
            "y"
        ],
        "language": "python",
        "metadata": {
            "slideshow": {
                "slide_type": "fragment"
            }
        },
        "outputs": [
            {
                "output_type": "stream",
                "stream": "stdout",
                "text": [
                    "Hello, world!\n",
                    "Hello, world!\n"
                ]
            }
        ],
        "prompt_number": 29
    }

    cell2 = {
        "cell_type": "code",
        "collapsed": False,
        "input": [
            "x",
            "x",
            "x",
            "x",
            "x",
            "x"
        ],
        "language": "python",
        "metadata": {
            "slideshow": {
                "slide_type": "fragment"
            }
        },
        "outputs": [
            {
                "output_type": "stream",
                "stream": "stdout",
                "text": [
                    "Hello, world!\n",
                    "Hello, world!\n"
                ]
            }
        ],
        "prompt_number": 29
    }

    import nbdiff.comparable as c

    class FakeComparator(object):
        '''Test comparator object. Will compare as modified if it is "close to"
        the specified values'''
        def __init__(self, foo, closeto=[]):
            self.foo = foo
            self.closeto = closeto

        def __eq__(self, other):
            if other.foo in self.closeto:
                return c.BooleanPlus(True, True)
            else:
                return self.foo == other.foo

    # ensure this doesn't crash at the least
    result = diff(['a', 'b', 'c'], ['b', 'c'], check_modified=False)
    assert result[0]['state'] == 'deleted'
    assert result[0]['value'] == 'a'

    # it doesn't break strings when check_modified is True
    diff(['a', 'b', 'c'], ['b', 'c'], check_modified=True)

    # ensure CellComparators do actually produce booleanpluses
    # if they are similar enough
    # TODO this should be in its own test in a separate file.
    c1 = c.CellComparator(cell1, check_modified=True)
    c2 = c.CellComparator(cell2, check_modified=True)

    assert type(c1 == c2) == c.BooleanPlus

    result = diff([c1, c2, c2, c2], [c2, c2, c2, c2], check_modified=True)
    assert result[0]['state'] == 'modified'

    c1 = FakeComparator(1, [2, 3])
    c2 = FakeComparator(2, [1, 3])
    c3 = FakeComparator(10, [])

    c4 = FakeComparator(2, [])
    c5 = FakeComparator(3, [])

    # c1 -> c4
    # c2 -> c5
    # c3 -> deleted
    result = diff([c1, c2, c3], [c4, c5], check_modified=True)

    assert result[0]['state'] == 'modified'
    assert result[1]['state'] == 'modified'
    assert result[2]['state'] == 'deleted'

########NEW FILE########
__FILENAME__ = test_git_adapter
from nbdiff.adapter import git_adapter as g
from pretend import stub


def test_get_modified_notebooks_empty():
    g.subprocess = stub(check_output=lambda cmd: '')
    adapter = g.GitAdapter()
    result = adapter.get_modified_notebooks()
    assert result == []


def test_get_modified_notebooks():
    adapter = g.GitAdapter()

    def check_output_stub(cmd):
        if '--modified' in cmd:
            output = '''foo.ipynb
bar.ipynb
foo.txt
baz.ipynb
'''
            return output
        elif '--unmerged' in cmd:
            return ''.join([
                '100755\thash\t{i}\tfoo.ipynb\n'
                for i in [1, 2, 3]
            ])

    def popen(*args, **kwargs):
        return stub(stdout=stub(read=lambda: ""))

    g.open = lambda fname: stub(read=lambda: "")
    g.subprocess = stub(
        check_output=check_output_stub,
        PIPE='foo',
        Popen=popen,
    )
    result = adapter.get_modified_notebooks()
    assert result[0][2] == 'bar.ipynb'
    assert result[1][2] == 'baz.ipynb'


def test_get_unmerged_notebooks_empty():
    g.subprocess = stub(check_output=lambda cmd: '')
    adapter = g.GitAdapter()
    result = adapter.get_unmerged_notebooks()
    assert result == []


def test_get_unmerged_notebooks():
    adapter = g.GitAdapter()

    def check_output_stub(cmd):
        if '--unmerged' in cmd:
            f1 = ''.join([
                '100755\thash\t{i}\tfoo.ipynb\n'
                for i in [1, 2, 3]
            ])
            f2 = ''.join([
                '100755\thash\t{i}\tbar.ipynb\n'
                for i in [1, 2, 3]
            ])
            f3 = ''.join([
                '100755\thash\t{i}\tfoo.py\n'
                for i in [1, 2, 3]
            ])
            return f1 + f2 + f3

    def popen(*args, **kwargs):
        return stub(stdout=stub(read=lambda: ""))

    g.open = lambda fname: stub(read=lambda: "")
    g.subprocess = stub(
        check_output=check_output_stub,
        PIPE='foo',
        Popen=popen,
    )
    result = adapter.get_unmerged_notebooks()
    assert len(result) == 2
    assert result[0][3] == 'foo.ipynb'
    assert result[1][3] == 'bar.ipynb'

########NEW FILE########
__FILENAME__ = test_local_server
from nbdiff.server.local_server import (
    app,
)


def test_home():
    client = app.test_client()
    result = client.get('/1')
    assert result.status_code == 200


def test_notebookjson():
    client = app.test_client()
    app.add_notebook({'metadata': {}}, 'foo.ipynb')
    result = client.get('/notebooks/test_notebook0')
    assert result.status_code == 200

    def fake_callback(contents, filename):
        fake_callback.called = True

    app.shutdown_callback(fake_callback)
    contents = ''
    result = client.put('/notebooks/test_notebook0', contents)
    assert result.data == "", result
    assert fake_callback.called

########NEW FILE########
__FILENAME__ = test_merge
import IPython.nbformat.current as nbformat

from nbdiff.merge import (
    notebook_merge,
    merge,
)


# Regression test for bug #196
def test_empty_notebook():
    notebook = nbformat.new_notebook()
    notebook2 = nbformat.new_notebook()
    notebook3 = nbformat.new_notebook()
    result = notebook_merge(notebook, notebook2, notebook3)
    assert result['metadata']['nbdiff-type'] == 'merge'


def test_basic_notebook_merge():
    notebook = nbformat.new_notebook()
    code_cell = nbformat.new_code_cell(input=['a', 'b'])
    notebook['worksheets'] = [
        {'cells': [code_cell]}
    ]
    notebook2 = nbformat.new_notebook()
    notebook3 = nbformat.new_notebook()
    code_cell = nbformat.new_code_cell(input=['a', 'b'])
    notebook3['worksheets'] = [
        {'cells': [code_cell]}
    ]
    result = notebook_merge(notebook, notebook2, notebook3)
    result_cells = result['worksheets'][0]['cells']
    state = result_cells[0]['metadata']['state']
    assert state == 'added'


def test_basic_merge():
    lines_local = ['a', 'b', 'c']
    lines_base = ['a', 'b']
    lines_remote = ['a', 'b', 'c']
    result = merge(lines_local, lines_base, lines_remote)
    assert result[0]['state'] == 'unchanged'
    assert result[0]['value']['state'] == 'unchanged'

########NEW FILE########
__FILENAME__ = test_notebook_diff
from nbdiff.comparable import CellComparator
from nbdiff.notebook_diff import (
    cells_diff,
    words_diff,
    lines_diff,
    diff_modified_items,
)


def test_diff_cells0():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']}]
    result = cells_diff(A, B, check_modified=False)

    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'deleted'


def test_diff_cells1():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}]

    result = cells_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'modified'
    assert result[1]['state'] == 'deleted'


def test_diff_cells2():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]

    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]

    result = cells_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'unchanged'


def test_diff_cells3():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,5]\n', u'z = {1} \n', u'\n', u'y']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]

    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [9,8,3]\n', u't = {8, 5, 6} \n', u'w']}
    ]

    result = cells_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'unchanged'
    assert result[2]['state'] == 'added'


def test_diff_cells4():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': []}]
    result = cells_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'


def test_diff_cells5():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    result = cells_diff(A, B, check_modified=True)

    assert result[0]['state'] == 'modified'
    assert result[1]['state'] == 'deleted'


def test_diff_cells6():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hi!\n",
                     "How are you?\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    result = cells_diff(A, B, check_modified=True)

    assert result[0]['state'] == 'modified'
    assert result[1]['state'] == 'deleted'


# different cell type -> different cells
def test_diff_cells7():
    A = [
        {'cell_type': "raw",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hi!\n",
                     "How are you?\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hi!\n",
                     "How are you?\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    result = cells_diff(A, B, check_modified=True)

    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'added'


# different cell language -> modified
def test_diff_cells8():
    A = [
        {'cell_type': "code",
         'language': "julia",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hi!\n",
                     "How are you?\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hi!\n",
                     "How are you?\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    result = cells_diff(A, B, check_modified=True)

    assert result[0]['state'] == 'modified'


def test_diff_lines0():
    A = ['first line', 'second line']
    B = ['first line', 'second line']

    result = lines_diff(A, B)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'unchanged'


def test_diff_lines1():
    A = ['this is a line', 'another line']
    B = ['another line', 'first line']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'unchanged'
    assert result[2]['state'] == 'added'


def test_diff_lines2():
    A = ['this is a line', 'another line']
    B = ['first line', 'another line']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'modified'
    assert result[2]['state'] == 'added'


def test_diff_line3():
    A = ['first line']
    B = ['another new one', 'second one', 'first line']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'added'
    assert result[1]['state'] == 'added'
    assert result[2]['state'] == 'unchanged'


def test_diff_lines4():
    A = ['fist line', 'first line']
    B = ['first lin', 'second one', 'first lin']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'modified'
    assert result[2]['state'] == 'added'
    assert result[3]['state'] == 'added'


def test_diff_lines5():
    A = ['test', ' ']
    B = ['diff']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'


def test_diff_lines6():
    A = ['first line', 'second line']
    B = ['first line', 'first line', 'other line']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'modified'
    assert result[2]['state'] == 'added'


def test_diff_lines7():
    A = ['first line', 'second line']
    B = ['first line', 'first line', 'second line']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'modified'
    assert result[2]['state'] == 'added'


def test_diff_lines8():
    A = ['first line', 'second line']
    B = ['this is a line', 'another one']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'
    assert result[3]['state'] == 'added'


def test_diff_lines9():
    A = ['this is a line']
    B = ['']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'


def test_diff_lines10():
    A = ['']
    B = ['']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'unchanged'


def test_diff_words0():
    A = "word is"
    B = "word is"

    result = words_diff(A, B)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'unchanged'


def test_diff_words1():
    A = "this is a line"
    B = " "

    result = words_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'deleted'
    assert result[3]['state'] == 'deleted'


def test_diff_words2():
    A = "second one"
    B = "first test"

    result = words_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'
    assert result[3]['state'] == 'added'


def test_diff_words3():
    A = "The"
    B = "This"

    result = words_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'added'


def test_diff_words4():
    A = "hello world"
    B = "hello beautiful"

    result = words_diff(A, B)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'


def test_diff():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']}]
    result = cells_diff(A, B, check_modified=False)

    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'deleted'


def test_diff_modified():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}]

    result = cells_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'modified'
    assert result[1]['state'] == 'deleted'


def test_diff_lines_same():
    A = ['first line', 'second line']
    B = ['first line', 'second line']

    result = lines_diff(A, B)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'unchanged'


def test_diff_lines_different():
    A = ['first line', 'second line']
    B = ['this is a line', 'another one']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'
    assert result[3]['state'] == 'added'


def test_diff_words_same():
    A = "word is"
    B = "word is"

    result = words_diff(A, B)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'unchanged'


def test_empty_lines():
    A = ['this is a line']
    B = ['']

    result = lines_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'


def test_empty_words():
    A = "this is a line"
    B = " "

    result = words_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'deleted'
    assert result[3]['state'] == 'deleted'


def test_diff_words_different():
    A = "second one"
    B = "first test"

    result = words_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'
    assert result[3]['state'] == 'added'


def test_diff_word():
    A = "The"
    B = "This"

    result = words_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'added'


def test_diff_word2():
    A = "hello world"
    B = "hello beautiful"

    result = words_diff(A, B)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'deleted'
    assert result[2]['state'] == 'added'


def test_diff_cells_same():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]

    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]

    result = cells_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'unchanged'
    assert result[1]['state'] == 'unchanged'


def test_diff_cells_different():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,5]\n', u'z = {1} \n', u'\n', u'y']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]

    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [9,8,3]\n', u't = {8, 5, 6} \n', u'w']}
    ]

    result = cells_diff(A, B)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'unchanged'
    assert result[2]['state'] == 'added'


def test_diff_empty():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": []
             }
         ],
         "prompt_number": 29,
         u'input': []}]
    result = cells_diff(A, B, check_modified=True)
    assert result[0]['state'] == 'deleted'
    assert result[1]['state'] == 'deleted'


def test_diff_modified2():
    A = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'm']},
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,3]\n', u'z = {1, 2, 3} \n', u'\n', u'z']}
    ]
    B = [
        {'cell_type': "code",
         'language': "python",
         "outputs": [
             {
                 "output_type": "stream",
                 "stream": "stdout",
                 "text": [
                     "Hello, world!\n",
                     "Hello, world!\n"
                 ]
             }
         ],
         "prompt_number": 29,
         u'input': [u'x = [1,3,4]\n', u'z = {1, 2, 3} \n', u'\n', u'k']}
    ]
    result = cells_diff(A, B, check_modified=True)

    assert result[0]['state'] == 'modified'
    assert result[1]['state'] == 'deleted'


def test_diff_modified_items():
    header_item = {
        'state': 'modified',
        'originalvalue': CellComparator({
            'cell_type': 'heading',
            'source': 'This is a header',
        }),
        'modifiedvalue': CellComparator({
            'cell_type': 'heading',
            'source': 'This is a different header',
        }),
    }
    code_item = {
        'state': 'modified',
        'originalvalue': CellComparator({
            'cell_type': 'code',
            'input': 'x = 10\ny = 10\n',
        }),
        'modifiedvalue': CellComparator({
            'cell_type': 'code',
            'input': 'x = 11\ny = 10\n',
        }),
    }
    cellslist = [
        {'state': 'added', 'value': 'foo'},
        header_item,
        code_item,
    ]
    result = diff_modified_items(cellslist)
    assert 0 not in result
    assert len(result[1]) == 5
    assert len(result[2]) == 3

########NEW FILE########
__FILENAME__ = test_remote
# Empty test file just for coverage / syntax-checking purposes
# flake8: noqa

import nbdiff.server.remote_server
import nbdiff.server.database


import nbdiff.server.command.AboutUsCommand
import nbdiff.server.command.ComparisonCommand
import nbdiff.server.command.ContactUsCommand
import nbdiff.server.command.DiffCommand
import nbdiff.server.command.DiffURLCommand
import nbdiff.server.command.FaqCommand
import nbdiff.server.command.MergeCommand
import nbdiff.server.command.MergeURLCommand
import nbdiff.server.command.NotebookRequestCommand
import nbdiff.server.command.ResourceRequestCommand
import nbdiff.server.command.SaveNotebookCommand
import nbdiff.server.command.UploadCommand

########NEW FILE########
__FILENAME__ = test_remote_server
import os
import unittest
import nbdiff.server.command.AboutUsCommand as aucmd
import nbdiff.server.command.ComparisonCommand as ccmd
import nbdiff.server.command.ContactUsCommand as cucmd
import nbdiff.server.command.DiffCommand as dcmd
import nbdiff.server.command.DiffURLCommand as ducmd
import nbdiff.server.command.FaqCommand as fcmd
import nbdiff.server.command.MergeCommand as mcmd
import nbdiff.server.command.MergeURLCommand as mucmd
import nbdiff.server.command.NotebookRequestCommand as nrcmd
import nbdiff.server.command.ResourceRequestCommand as rrcmd
import nbdiff.server.command.SaveNotebookCommand as sncmd
import nbdiff.server.command.UploadCommand as ucmd
import nbdiff.server.remote_server as rs
import nbdiff.server.database as db
import bitarray
from pretend import stub
from nbdiff.server.database.nbdiffModel import nbdiffModel

app = rs.app.test_client()
parentPath = os.path.abspath(
    os.path.join(
        os.path.realpath(os.path.dirname(__file__)),
        os.pardir
    )
)
SCRIPTS_DIR = os.path.join(parentPath, "scripts")
MERGE_NB_DIR = os.path.join(SCRIPTS_DIR, 'example-notebooks', 'merge', '0')
DIFF_NB_DIR = os.path.join(SCRIPTS_DIR, 'example-notebooks', 'diff', '0')
rs.init_db()


def mock_redirect(path, **kwargs):
    assert "code" in kwargs
    assert kwargs["code"] == 302
    return path


def mock_render_template(filename, **kwargs):
    assert "err" not in kwargs
    return filename


def mock_make_response(data):
    return stub(headers={"Content-Type": '', "Content-Disposition": ''})


class RemoteServerTest(unittest.TestCase):

    def test_run_command(self):
        ucmd.render_template = mock_render_template
        response = rs.run_command("Upload", None)
        assert response == "upload.html"

    def test_get_Class(self):
        cmd = "nbdiff.server.command.UploadCommand"
        module = "module 'nbdiff.server.command.UploadCommand' "
        assert module in str(rs.get_class(cmd))


class AboutUsCommandTest(unittest.TestCase):

    def test_newInstance(self):
        assert isinstance(
            rs.get_class("nbdiff.server.command.AboutUsCommand").newInstance(),
            aucmd.AboutUsCommand
        )

    def test_process(self):
        aucmd.render_template = mock_render_template
        template = aucmd.AboutUsCommand().process(None, None, None)
        assert template == "aboutUs.html"


class ContactUsCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.ContactUsCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            cucmd.ContactUsCommand
        )

    def test_process(self):
        cucmd.render_template = mock_render_template
        template = cucmd.ContactUsCommand().process(None, None, None)
        assert template == "contactUs.html"


class FaqCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.FaqCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            fcmd.FaqCommand
        )

    def test_process(self):
        fcmd.render_template = mock_render_template
        template = fcmd.FaqCommand().process(None, None, None)
        assert template == "faq.html"


class ComparisonCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.ComparisonCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            ccmd.ComparisonCommand
        )

    def test_process(self):
        ccmd.render_template = mock_render_template
        session = db.db_session()
        ba = bitarray.bitarray()
        ba.fromstring("test")
        obj = nbdiffModel(ba.to01())
        session.add(obj)
        session.commit()
        filename = obj.id
        response = ccmd.ComparisonCommand().process(None, filename, session)
        assert response == "nbdiff.html"
        response = app.get("/Comparision/"+str(filename))
        assert response.status == "200 OK"


class DiffCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.DiffCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            dcmd.DiffCommand
        )

    def test_process(self):
        dcmd.render_template = mock_render_template
        dcmd.redirect = mock_redirect
        session = db.db_session()
        beforeStream = open(os.path.join(DIFF_NB_DIR, "before.ipynb"), 'r')
        afterStream = open(os.path.join(DIFF_NB_DIR, "after.ipynb"), 'r')
        request = stub(form={
            'beforeJSON': beforeStream.read(),
            'afterJSON': afterStream.read()
        })
        beforeStream.close()
        beforeStream.close()

        response = dcmd.DiffCommand().process(request, None, session)
        assert "/Comparison/" in response
        split = str.split(response, "/")
        assert split[-1].isdigit()


class DiffURLCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.DiffURLCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            ducmd.DiffURLCommand
        )

    def test_process(self):
        ducmd.redirect = mock_redirect
        ducmd.render_template = mock_render_template
        mainurl = "https://raw.githubusercontent.com/"
        mainurl = mainurl + "tarmstrong/nbdiff/master/scripts/"
        before = mainurl+"example-notebooks/diff/0/before.ipynb"
        after = mainurl+"example-notebooks/diff/0/after.ipynb"
        session = db.db_session()
        request = stub(form={'beforeURL': before, 'afterURL': after})
        response = ducmd.DiffURLCommand().process(request, None, session)
        assert "/Comparison/" in response
        split = str.split(response, "/")
        assert split[-1].isdigit()


class MergeCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.MergeCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            mcmd.MergeCommand
        )

    def test_process(self):
        mcmd.render_template = mock_render_template
        mcmd.redirect = mock_redirect
        session = db.db_session()
        localStream = open(os.path.join(MERGE_NB_DIR, "local.ipynb"), 'r')
        baseStream = open(os.path.join(MERGE_NB_DIR, "base.ipynb"), 'r')
        remoteStream = open(os.path.join(MERGE_NB_DIR, "remote.ipynb"), 'r')
        request = stub(form={
            'localJSON': localStream.read(),
            'baseJSON': baseStream.read(),
            'remoteJSON': remoteStream.read()
        })
        localStream.close()
        baseStream.close()
        remoteStream.close()

        response = mcmd.MergeCommand().process(request, None, session)
        assert "/Comparison/" in response
        split = str.split(response, "/")
        assert split[-1].isdigit()


class MergeURLCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.MergeURLCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            mucmd.MergeURLCommand
        )

    def test_process(self):
        mucmd.redirect = mock_redirect
        mucmd.render_template = mock_render_template
        mainurl = "https://raw.githubusercontent.com/"
        mainurl = mainurl + "tarmstrong/nbdiff/master/scripts/"
        local = mainurl+"example-notebooks/merge/0/local.ipynb"
        base = mainurl+"example-notebooks/merge/0/base.ipynb"
        remote = mainurl+"example-notebooks/merge/0/remote.ipynb"
        session = db.db_session()
        request = stub(form={
            'localURL': local,
            'baseURL': base,
            'remoteURL': remote
        })
        response = mucmd.MergeURLCommand().process(request, None, session)
        assert "/Comparison/" in response
        split = str.split(response, "/")
        assert split[-1].isdigit()


class NotebookRequestCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.NotebookRequestCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            nrcmd.NotebookRequestCommand
        )

    def test_process(self):
        session = db.db_session()
        localStream = open(os.path.join(MERGE_NB_DIR, "local.ipynb"), 'r')
        data = localStream.read()
        ba = bitarray.bitarray()
        ba.fromstring(data)
        obj = nbdiffModel(ba.to01())
        session.add(obj)
        session.commit()
        filename = obj.id
        response = nrcmd.NotebookRequestCommand().process(
            None,
            filename,
            session
        )
        assert response == data
        response = app.get("/notebooks/"+str(filename))
        assert response.data == data


class ResourceRequestCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.ResourceRequestCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            rrcmd.ResourceRequestCommand
        )

    def test_process(self):
        response = app.get("/nbdiff/js/main.js")
        assert response.status == "200 OK"


class SaveNotebookCommandTest(unittest.TestCase):

    def test_newInstance(self):
        classname = "nbdiff.server.command.SaveNotebookCommand"
        assert isinstance(
            rs.get_class(classname).newInstance(),
            sncmd.SaveNotebookCommand
        )

    def test_process(self):
        sncmd.make_response = mock_make_response
        nbStream = open(os.path.join(MERGE_NB_DIR, "base.ipynb"), 'r')
        request = stub(form={'download_data': nbStream.read()})
        nbStream.close()
        response = sncmd.SaveNotebookCommand().process(request, None, None)
        contentDisposition = "attachment; filename=mergedNotebook.ipynb"
        assert response.headers["Content-Disposition"] == contentDisposition


class UploadCommandTest(unittest.TestCase):

    def test_newInstance(self):
        assert isinstance(
            rs.get_class("nbdiff.server.command.UploadCommand").newInstance(),
            ucmd.UploadCommand
        )

    def test_process(self):
        ucmd.render_template = mock_render_template
        template = ucmd.UploadCommand().process(None, None, None)
        assert template == "upload.html"

########NEW FILE########
