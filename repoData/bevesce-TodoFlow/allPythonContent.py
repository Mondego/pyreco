__FILENAME__ = alfredlist
from cgi import escape


class AlfredItemsXML(object):
    def __init__(self):
        self.items = []
        self.pattern = '<item arg="{0}" uid="nouid" valid="{3}"><title>{1}</title><subtitle>{2}</subtitle><icon>iconT.png</icon></item>'

    def append(self, arg, title, subtitle, valid='yes'):
        self.items.append((arg, escape(title), escape(subtitle), valid))

    def __str__(self):
        items = "".join(
            [self.pattern.format(arg, escape(title), escape(subtitle), valid) for arg, title, subtitle, valid in self.items]
            )
        return '<items>' + items + '</items>'

    def __add__(self, other):
        new_alist = AlfredItemsXML()
        new_alist.items = self.items + other.items
        return new_alist

########NEW FILE########
__FILENAME__ = config
add_date_to_done_tag = True  # @done(2013-01-15)
done_tag = '@done'
today_tag = '@today'
inbox = 'Inbox'
tasks_msg = 'Do task'

only_tagged_today = False

# used when `tt`
max_items_from_file = 3

# Paths:
# path to files displayed when using `t`
one_filepath = '/path/to/list'  # '/Users/bvsc/Dropbox/TODO/Today.todo'

# location when you want to store list of active_list
# displayed when using `tt`
active_lists_path = 'path/to/active_projects'  # 'active_projects'

# if your lists are stored in one folder you can put it here,
# so when using `ttt` you won't need to write it
# it's added as prefix to path when script tries to open file
base_path = 'base/path/to/root?'

# if you use one extension for all list you can put it here,
# so when using `ttt` you won't need to write it
# it's added as sufix to path when script tries to open file
standard_extension = '.todo'

########NEW FILE########
__FILENAME__ = todo_activate
from config import active_lists_path
import os


def activate(filepath):
    if not os.path.lexists(filepath):
        print "File doesn't exists\n" + filepath
        return

    try:
        f = open(active_lists_path, 'r')
    except IOError:
        open(active_lists_path, 'w').close()
        f = open(active_lists_path, 'r')
    finally:
        if filepath in f.read():
            print "Project already active " + filepath.split('/')[-1]
            return

    with open(active_lists_path, 'a') as f:
        f.write(filepath + '\n')
        print 'Activated ' + filepath.split('/')[-1]


def deactivate(filepath):
    line_to_putback = []
    with open(active_lists_path, 'r') as f:
        for line in f:
            if line.strip() != filepath:
                line_to_putback.append(line)
    with open(active_lists_path, 'w') as f:
        f.writelines(line_to_putback)
        print 'Deactivated ' + filepath.split('/')[-1]


def list_active():
    with open(active_lists_path, 'r') as f:
        return [line.strip() for line in f]

########NEW FILE########
__FILENAME__ = todo_addtask
import re
from config import inbox


def prepend(path, task):
    with open(path, 'r') as f:
        lines = f.readlines()
        lines.insert(0, '- ' + task + '\n')
    with open(path, 'w') as f:
        f.write("".join(lines))


def append(path, task):
    with open(path, 'a') as f:
        f.write('\n- ' + task)


def insert_into_inbox(path, task):
    """
    Inserts task in the next line to line containing 'Inbox:'
    Task is indented by one more tab than Inbox.
    """
    with open(path, 'r') as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if re.match('\s*' + inbox + ':', line):
                tabs_no = line.find(inbox[0])
                lines.insert(idx + 1, '\t' * tabs_no + '\t- ' + task + '\n')
                break
    with open(path, 'w') as f:
        f.write("".join(lines))

########NEW FILE########
__FILENAME__ = todo_dotask
from config import add_date_to_done_tag, done_tag
from datetime import date
from utils import split_query


def do_task(query):
    """
    decodes query from format used in listing and appends
    @done tag to the end of the line given by it's index
    """
    line_nr, path = split_query(query)

    with open(path, 'r') as f:
        lines = f.readlines()
    line = lines[line_nr][0:-1]
    line += " " + done_tag + \
        ('(' + date.today().isoformat() + ')' if add_date_to_done_tag else '') + \
        '\n'
    lines[line_nr] = line
    with open(path, 'w') as f:
        f.write("".join(lines))

########NEW FILE########
__FILENAME__ = todo_listtasks
import sys
from config import only_tagged_today, today_tag, max_items_from_file, tasks_msg
from utils import is_not_done_task, format_line, create_arg
from alfredlist import AlfredItemsXML as AlfredList
import re


def list_file(path, query='', max_items=0, subtitle=tasks_msg):
    """
    Creates object that represents XML items list of tasks in file given by `path`
    that contains `query` as substring. Max length of list is given by `max_items`,
    0 means all tasks.
    """
    alist = AlfredList()

    if len(sys.argv) > 1:
        query = sys.argv[1].lower()

    items_added = 0
    with open(path, 'r') as f:
        for idx, line in enumerate(f):
            if is_not_done_task(line) and re.search(query, line.lower()):
                should_add = False
                if not only_tagged_today:
                    should_add = True
                else:
                    if today_tag in line:
                        should_add = True
                        line = line.replace(today_tag, '')
                        # when user displays only tasks with @today tag displaying it is reduntant
                if should_add:
                    items_added += 1
                    alist.append(create_arg(path, idx), format_line(line), subtitle)
                if max_items and max_items <= items_added:
                    break
    return alist


def list_files(paths, query='', max_items=max_items_from_file):
    """Creates listing of tasks from multiple files"""
    alist = AlfredList()
    for path in paths:
        subtitle = path.split('/')[-1]
        alist = alist + list_file(path, query, max_items, subtitle)
    return alist

########NEW FILE########
__FILENAME__ = utils
import re


add_date_to_done_tag = True
done_tag = '@done'


def is_not_done_task(line):
    return re.match("^\s*-", line) and line.find(done_tag) == -1


def format_line(line):
    task_ind_idx = line.find('-')
    return line[task_ind_idx + 2:]  # skip '- '


def split_query(query):
    splitted = query.split(';')
    line_nr = int(splitted[0])
    path = ";".join(splitted[1:])
    return line_nr, path


def create_arg(path, idx):
    return '{0};{1}'.format(idx, path)

########NEW FILE########
__FILENAME__ = test
"""Run from directory that contains this file"""

from __future__ import absolute_import
import unittest
import sys
import os.path
import topy as tp
from topy.src.todolist import Task, Note, Project
from topy.src.filterpredicate import parse_predicate
import topy.src.todolist_utils as tu

class TestUtils(unittest.TestCase):
    def test_add_tag(self):
        self.assertEqual('abc @done', tu.add_tag_to_text('abc', 'done'))
        self.assertEqual('abc @done(1)', tu.add_tag_to_text('abc', 'done', 1))
        self.assertEqual('\tabc @done(1)', tu.add_tag_to_text('\tabc ', 'done', 1))

    def test_get_tag_param(self):
        self.assertEqual('1', tu.get_tag_param('abc @done(1)', 'done'))
        self.assertEqual('1', tu.get_tag_param('abc @done(1) fds', 'done'))
        self.assertEqual('1', tu.get_tag_param('@done(1) fds', 'done'))
        self.assertEqual(None, tu.get_tag_param('abc @done', 'done'))

    def test_remove_trailing_tags(self):
        self.assertEqual('abc', tu.remove_trailing_tags('abc @dd @done(1)'))
        self.assertEqual('- abc @kk fds', tu.remove_trailing_tags('- abc @kk fds @done(1) @dd '))  # +
        self.assertEqual('@abc', tu.remove_trailing_tags('@abc'))  # +
        self.assertEqual('abc', tu.remove_trailing_tags('abc'))  # +

    def test_extract_content(self):
        self.assertEqual('abc', tu.extract_content('task', '\t- abc @done @jup'))
        self.assertEqual('abc', tu.extract_content('project', '\tabc: @done @jup'))

    def test_enclose_tags(self):
        self.assertEqual('abc !@done# fds', tu.enclose_tags('abc @done fds', '!', '#'))
        self.assertEqual('abc !@done# ', tu.enclose_tags('abc @done ', '!', '#'))

    def test_remove_tag(self):
        self.assertEqual('abc  fds', tu.remove_tag_from_text('abc @done fds', 'done'))
        self.assertEqual('abc ', tu.remove_tag_from_text('abc @done(fdsf)', 'done'))
        self.assertEqual('abc  fds', tu.remove_tag_from_text('abc @done(fdsf) fds', 'done'))
        self.assertEqual(' abc', tu.remove_tag_from_text('@done(fdsf) abc', 'done'))


class TestsOnItems(unittest.TestCase):
    def _test_item(self, line, query, result=True, constructor=Task):
        item = constructor(line)
        predicate = parse_predicate(query)
        # print item.title.line
        self.assertEqual(
            predicate.test(item),
            result
        )

    def test_words_predicate(self):
        self._test_item('- abc aa a', 'a')
        self._test_item('- abc fds', 'abc')
        self._test_item('- abc fds', 'fds')
        self._test_item('- abc fds', 'abcd', result=False)

    def test_tag_predicate(self):
        self._test_item('- abc @done', '@done')
        self._test_item('@done(2011-11-11) abc', '@done', constructor=Note)
        self._test_item('- abv @done(2011-11-11) fsd', '@done')
        self._test_item('- abv @doner(2011-11-11) fsd', '@done', result=False)

    def test_content(self):
        self._test_item('\t\t- abc', 'content = abc')
        self._test_item('\t\tabc:', 'content = abc', constructor=Project)
        self._test_item('\t\tabc', 'content = abc', constructor=Note)
        self._test_item('\t\tabc', 'content = abcd', constructor=Note, result=False)
        self._test_item('- abc', 'content $ a')
        self._test_item('- abc', 'not content $ d')
        self._test_item('- 123', 'content matches \d\d\d')
        self._test_item('- 123 fd', 'content matches \d+')

    def test_line(self):
        self._test_item('\t\t- abc', 'line =   - abc')
        self._test_item('\t\t- fd abc', 'line $   -')
        self._test_item('\t\tabc: @done', 'line $ :', constructor=Project)
        self._test_item('\t\tfd - abc', 'line $ -', constructor=Note)
        self._test_item('\t\tabc:', 'line = abc:', constructor=Project)
        self._test_item('\t\tabc @done', 'line = "abc @done"', constructor=Note)
        self._test_item('\t\tabc', 'line = abcd', constructor=Note, result=False)
        self._test_item('- abc', 'line $ a')
        self._test_item('- abc', 'not line $ d')

    def test_tag_param(self):
        self._test_item('- d @done(2013-02-23)', '@done < 2013-02-25')
        self._test_item('- d @done(2013-02-23)', '@done > 2013-02-25', result=False)
        self._test_item('- d @done(2013-02-23) fsd', '@done != 2013-02-25')
        self._test_item('- d @done(2013-02-23) fsd', '@done = 2013-02-23')
        self._test_item('- d @done(2013-02-23) fsd', '@done = 2013-02-24', result=False)
        self._test_item('d: @done(zzz)', '@done < a', result=False, constructor=Project)
        self._test_item('d: @done(aaa)', '@done < z', constructor=Project)
        self._test_item('- @done(123)', '@done $ 1')
        self._test_item('- @done(123)', '@done matches \d*')
        self._test_item('- @done', '@done < q', result=False)

    def test_type(self):
        self._test_item('- abc', 'type = task')
        self._test_item('\tabc: @done', 'type = "project"', constructor=Project)
        self._test_item('\tabc @done', 'type = note', constructor=Note)
        self._test_item('\t-abc @done', 'type != note', constructor=Task)
        self._test_item('- abc', 'type < z')

    def test_or_predicate(self):
        self._test_item('- abc', 'a or d')
        self._test_item('- bcd', 'a or d')
        self._test_item('- abc', 'e or d', result=False)

    def test_and_predicate(self):
        self._test_item('- abc d', '(line $ a) and d')
        self._test_item('- bcd', '(line > aaa) and d', result=False)
        self._test_item('- abc', 'e and (type = task)', result=False)

    def test_and_or(self):
        self._test_item('- ac d', '(a or b) and d')
        self._test_item('- ac d', '(a and b) or d')
        self._test_item('- ac d', '(a and b) or g', result=False)

    def test_not_predicate(self):
        self._test_item('- abc', 'not d')
        self._test_item('- bcd', 'not (b and c)', result=False)
        self._test_item('- bcd', 'not b', result=False)


def load_big():
    return tp.from_file('in/big.todo')


class TestsOnFiles(unittest.TestCase):
    def setUp(self):
        self.big = load_big()

    def _test_on_files(self, input_list, out_path, query=''):
        os.path.abspath(out_path)
        if isinstance(input_list, str):
            input_list = tp.from_file(input_list)
        input_list = input_list.filter(query)
        in_txt = input_list.as_plain_text()
        out_txt = open(out_path, 'r').read().strip()
        open('m' + out_path, 'w').write(in_txt)
        # print in_txt
        # print out_txt
        self.assertEqual(in_txt.strip(), out_txt.strip())

    def test_empty(self):
        self._test_on_files('in/empty.todo', 'in/empty.todo')

    def test_one_task(self):
        self._test_on_files('in/one_task.todo', 'in/one_task.todo')

    def test_no_query(self):
        self._test_on_files(self.big, 'in/big.todo')

    def test_index(self):
        self._test_on_files(self.big, 'out/index0.todo', 'index = 0')
        self._test_on_files(self.big, 'out/index2.todo', 'index = 2')

    def test_project(self):
        self._test_on_files(self.big, 'out/ProjectA.todo', 'project = ProjectA')
        self._test_on_files(self.big, 'out/ProjectB.todo', 'project = ProjectB')
        self._test_on_files(self.big, 'out/project-project.todo', 'project $ "project"')
        self._test_on_files(self.big, 'out/notA.todo', 'project != ProjectA')
        self._test_on_files(self.big, 'out/notD.todo', 'not project = ProjectD')

    def test_type(self):
        self._test_on_files(self.big, 'out/only-projects.todo', 'type = "project"')
        self._test_on_files(self.big, 'out/only-tasks.todo', 'type =  task')
        self._test_on_files(self.big, 'out/only-notes.todo', 'type =  note')

    def test_level(self):
        self._test_on_files(self.big, 'out/level0.todo', 'level = 0')
        self._test_on_files(self.big, 'out/level12.todo', 'level < 3')
        self._test_on_files(self.big, 'out/level2up.todo', 'level > 2')

    def test_tags(self):
        self._test_on_files(self.big, 'out/next_and_done.todo', '@next and @done')
        self._test_on_files(self.big, 'out/due.todo', '@due < 2013-04-28')
        self._test_on_files(self.big, 'out/due-and-not-done.todo', '@due < 2013-04-28 and not @done')

    def test_parent(self):
        self._test_on_files(self.big, 'out/parentA.todo', 'parent contains A')

    def test_plus_d(self):
        self._test_on_files(self.big, 'out/task1+d.todo', 'task1 +d')

    def test_misc(self):
        self._test_on_files(self.big, 'out/misc1.todo', 'index = 1 and (@done or level = 1)')
        self._test_on_files(self.big, 'out/misc2.todo', '9 or (7 and not @done)')

    def test_add_remove(self):
        project_id = self.big.find_project_id_by_title('ProjectC')
        tp.add_new_subtask(project_id, 'abc')
        self._test_on_files(self.big, 'out/add_abc.todo')
        self.big.remove(project_id)
        self._test_on_files(self.big, 'out/removeC.todo')
        self.big = load_big()  # restart big
# run
unittest.main()

########NEW FILE########
__FILENAME__ = config
#
# Configuration of topy
#
# You should read README first
#

# File that stores path to your todo lists
# This location keeps up with alfred workflow
# best practices but you can change it
# to wherever you want
files_list_path = '~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data/TodoFlow2/'
files_list_name = 'lists'

# logical operator to join shortened queries
quick_query_abbreviations_conjuction = ' and '  # ' or '

# fill with your own, this is what I use:
quick_query_abbreviations = {
    't': '@today',
    'n': '@next',
    'd': 'not @done',
    'u': '@due',
    's': 'project = Studia',
    'i': 'index = 0',
    'f': '(@today or @next)',
    'q': 'project = Projects and not project = Archive'
}

# add date value when tagging with @done
date_after_done = True

# include project titles in list displayed by alfred
# when searching with `q` keyword
include_project_title_in_alfred = False

# when generating html items are given classes
# define how many different classes (depengin on identation level)
# you want to have
number_of_css_classes = 4

# symbols on icons can be transparent or white
white_symbols_on_icons = False  # True

########NEW FILE########
__FILENAME__ = alfredlist
"""
Module provides simple class to create
Alfred 2 feedback XML.

It's really simple structure so there is no need
to use any advanced xml tools.
"""

from cgi import escape
from uuid import uuid1
from topy.config import white_symbols_on_icons


class AlfredItemsList(object):
    def __init__(self, items=None):
        self.items = items or []
        self.pattern = \
            '<item arg="{arg}" uid="{uid}" valid="{valid}">"' +\
            '<title>{title}</title>' +\
            '<subtitle>{subtitle}</subtitle>' +\
            '<icon>icons/{icon}{w}.png</icon>'.format(
                icon='{icon}',
                w='w' if white_symbols_on_icons else '',
            ) +\
            '</item>'

    def append(
            self,
            arg,
            title,
            subtitle,
            valid='yes',
            icon='iconT',
            uid=None
        ):
        """
        Adds item to list, left uid of every item
        to None to preserve order in list when it's
        displayed in Alfred.
        """
        # using uuid is little hacky but there is no other way to
        # prevent alfred from reordering items than to ensure that
        # uid never repeats
        uid = uid or str(uuid1())
        self.items.append(
            (arg, escape(title), escape(subtitle), valid, icon, uid)
        )

    def __str__(self):
        items = "".join(
            [self.pattern.format(
                arg=arg.encode('utf-8'),
                title=escape(title.encode('utf-8')),
                subtitle=escape(subtitle.encode('utf-8')),
                valid=valid,
                icon=icon,
                uid=uid
                ) for arg, title, subtitle, valid, icon, uid in self.items
            ]
        )
        return '<items>' + items + '</items>'

    def __add__(self, other):
        return AlfredItemsList(self.items + other.items)

########NEW FILE########
__FILENAME__ = colors
"""defines colors used in output"""
defc         = '\033[0m'

red          = '\033[1;31m'
green        = '\033[1;32m'
gray         = '\033[1;30m'
blue         = '\033[1;34m'

yellow       = '\033[1;33m'
magenta      = '\033[1;35m'
cyan         = '\033[1;36m'
white        = '\033[1;37m'
crimson      = '\033[1;38m'

high_red     = '\033[1;41m'
high_green   = '\033[1;42m'
high_brown   = '\033[1;43m'
high_blue    = '\033[1;44m'
high_magenta = '\033[1;45m'
high_cyan    = '\033[1;46m'
high_gray    = '\033[1;47m'
high_crimson = '\033[1;48m'

########NEW FILE########
__FILENAME__ = fileslist
"""
module provides functions to store and retrieve paths of
files with todo lists
"""

from alfredlist import AlfredItemsList
import os
from topy.config import files_list_path, files_list_name

dir_path = os.path.expanduser(files_list_path)
# create directory if it doesn't exist
if not os.path.isdir(dir_path):
    os.mkdir(dir_path)
full_path = dir_path + files_list_name
# create `selection` file if it doesn't exist
try:
    open(full_path, 'r')
except IOError:
    open(full_path, 'w').close()


def change_list(items, change_f):
    # load items from file
    previous = set()
    with open(full_path, 'r') as f:
        text = f.read()
        if text:
            previous = set(text.split('\t'))

    # change items from file using change_f function
    if isinstance(items, str):
        items = set(items.split('\t'))
    new = change_f(previous, items)

    with open(full_path, 'w') as f:
        f.write('\t'.join(new))


def add(items):
    change_list(items, lambda p, i: p.union(i))


def remove(items):
    change_list(items, lambda p, i: p - set(i))


def clear():
    with open(full_path, 'w') as f:
        f.write('')


def to_alfred_xml(query):
    items = None
    with open(full_path, 'r') as f:
        text = f.read()
        if text:
            items = set(text.split('\t'))

    if not items:
        return  # alfred will display "Please wait" subtext

    al = AlfredItemsList()
    # add selected files
    for item in items:
        if query.lower() in item.lower():
            al.append(
                arg=item,
                title='/'.join(item.split('/')[-2:]),
                subtitle='',
                icon='remove'.format(item))
    return al


def to_list():
    with open(full_path, 'r') as f:
        return f.read().split('\t')

########NEW FILE########
__FILENAME__ = filterpredicate
# -*- coding: utf-8 -*-

import re

"""
Predicates for filtering todo list.
Module defines lexer, parser and predicates themself.

Predicate implements method test(text) that returns if
predicate applies to given text.

For example '@today and not @done' returns if text contains
tag @today and not contains tag @done.

grammar of predicates (SLR(1)):

S     -> E1 | E1 +d
E1    -> E1 and E2
       | E2.
E2    -> E2 or E3
       | E3.
E3    -> not E3
       | E4
       | ( E1 ).
E4    -> Argument op Words
       | Words
       | Tag .
Words -> word Words
       | .

those rules are not part of SLR automaton:
op     -> = | != | < | <= | >= | > | matches | contains | $ . ($ is abbreviation for contains)
Tag    -> @ word | EndTag.
EndTag -> (Words) | epsilon.
Argument -> project | line | uniqueid | content | type | level | parent | index | Tag.



Arguments:
- project - check project title
- line - line with whole `-`, and tags
- uniqueid - id of element
- content - line without formatting and trailing tags
- type - "project", task or note
- level - indentation level
- parent - checks parents recursively
- index - index in sublist, starts with 0
- tag parameter - value enclosed in parenthesises after tag
"""


class Token(object):
    operators = ['=', '!=', '<', '<=', '>', '>=', '$', 'matches', 'contains']
    log_ops = ['and', 'or', 'not']
    keywords = ['project', 'line', 'uniqueid', 'content', 'type', 'level', 'parent', 'index']
    tag_prefix = '@'

    def __init__(self, text=None):
        # long switch-case / if:elif chain
        self.text = text
        # set type of token
        if not text:
            self.type = '$'
        elif text in Token.operators:
            self.type = 'op'
        elif text == '+d':
            self.type = 'plusD'
        elif text in Token.log_ops:
            self.type = text
        elif text in Token.keywords:
            self.type = 'arg'
        elif text[0] == Token.tag_prefix:
            self.type = 'tag'
        elif text[0] == '"':
            self.type = 'word'
            self.text = text[1:-1]
        elif text == '(':
            self.type = 'lparen'
        elif text == ')':
            self.type = 'rparen'
        else:
            self.type = 'word'

    def __str__(self):
        return repr(self.text) + ' : ' + self.type


class Lexer(object):
    def __init__(self, input_text):
        self.tokens = Lexer.tokenize(input_text)

    @staticmethod
    def tokenize(input_text):
        """converts input text to list of tokens"""
        tokens = []

        def add_token(text=None):
            if text != '' and text != ' ':
                tokens.append(Token(text))

        idx = 0
        collected = ''
        text_length = len(input_text)

        while idx < text_length + 1:
            # lengthy switch-case like statement
            # that processes input text depending on
            # current char
            if idx == text_length:
                # finish tokenizing
                add_token(collected)  # add remaining collected text
                add_token()  # add end of input token
            elif input_text[idx] == '+':
                if idx + 1 < len(input_text):
                    if input_text[idx + 1] == 'd':
                        add_token(collected)
                        collected = ''
                        add_token('+d')
                        idx += 1
            elif input_text[idx] == ' ':
                # spaces separate but but don't have semantic meaning
                add_token(collected)
                collected = ''
            elif input_text[idx] in ('(', ')'):
                # parenthesises seperate
                add_token(collected)
                collected = ''
                add_token(input_text[idx])
            elif input_text[idx] in ('<', '>', '!'):
                # operators or prefixes of operators
                add_token(collected)
                collected = input_text[idx]
            elif input_text[idx] == '=':
                if collected in ('<', '>', '!'):
                    # "="" preceded by any of this signs is an operator
                    collected += '='
                    add_token(collected)
                else:
                    # "=" by itself is also an operator
                    add_token(collected)
                    add_token('=')
                collected = ''
            elif input_text[idx] == '$':
                add_token(collected)
                add_token('$')
                collected = ''
            elif input_text[idx] == '"':
                # quoted part of input is allways a word
                add_token(collected)
                collected = ''
                next_quotation_mark_idx = input_text.find('"', idx + 1)
                if next_quotation_mark_idx == -1:
                    # when there is no matching quotation mark
                    # end of the input is assumed
                    add_token(input_text[idx:] + '"')
                    idx = text_length - 1  # sets idx to that value so loop finishes in next iteration
                else:
                    add_token(input_text[idx:next_quotation_mark_idx + 1])
                    idx = next_quotation_mark_idx

            else:
                if collected in ('<', '>'):
                    add_token(collected)
                    collected = ''
                collected += input_text[idx]
            idx += 1

        return tokens[::-1]

    def pop(self):
        """pops and returns topmost token"""
        try:
            return self.tokens.pop()
        except IndexError:
            raise ParsingError

    def top(self):
        """returns topmost token"""
        try:
            return self.tokens[-1]
        except IndexError:
            raise ParsingError


class ParsingError(Exception):
    pass


class Parser(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.create_parsing_table()
        self.stack = [0]

    def goto(self, state):
        self.parsing_table[self.stack[-2]][state]()

    def create_parsing_table(self):
        # long functions with declaration of parsing table and parser actions

        def shift_gen(state_no):
            def shift():
                """puts lexem and state number on stack"""
                self.stack.append(self.lexer.pop())
                self.stack.append(state_no)
            return shift

        def goto_gen(state_no):
            def goto():
                """puts state number on stack"""
                self.stack.append(state_no)
            return goto

        def err():
            raise ParsingError

        def acc():
            """returns abstrac syntax tree"""
            self.stack.pop()
            return self.stack[-1]

        # reductions, name of the functions contains information about production
        # -> is changed to __, terminals and nonterminals are separated by _
        # left side of production is preceded by `r`

        def rS__E1():
            self.stack.pop()
            self.goto('S')

        def rS__E1_plusD():
            self.stack.pop()
            self.stack.pop()  # +d

            self.stack.pop()
            e1 = self.stack.pop()
            self.stack.append(PlusDescendants(e1))
            self.goto('S')

        def rE3__E4():
            self.stack.pop()
            self.goto('E3')

        def rE1__E2():
            self.stack.pop()
            self.goto('E1')

        def rE2__E3():
            self.stack.pop()
            self.goto('E2')

        def rE3__lparen_E1_rparen():
            self.stack.pop()  # )
            self.stack.pop()

            self.stack.pop()
            e1 = self.stack.pop()

            self.stack.pop()  # (
            self.stack.pop()

            self.stack.append(e1)
            self.goto('E3')

        def rE2__E2_or_E3():
            self.stack.pop()
            e3 = self.stack.pop()

            self.stack.pop()  # or
            self.stack.pop()

            self.stack.pop()
            e2 = self.stack.pop()

            self.stack.append(OrPredicate(e2, e3))
            self.goto('E2')

        def rE4__Words():
            self.stack.pop()
            self.goto('E4')

        def rE1__E1_and_E2():
            self.stack.pop()
            e2 = self.stack.pop()

            self.stack.pop()  # and
            self.stack.pop()

            self.stack.pop()
            e1 = self.stack.pop()

            self.stack.append(AndPredicate(e1, e2))
            self.goto('E1')

        def rE3__not_E3():
            self.stack.pop()
            e3 = self.stack.pop()

            self.stack.pop()  # not
            self.stack.pop()

            self.stack.append(NotPredicate(e3))
            self.goto('E3')

        def rWords__epsilon():
            self.stack.append(WordsPredicate())
            self.goto('Words')

        def rE4__tag_op_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            op = self.stack.pop()

            self.stack.pop()
            arg = self.stack.pop()

            self.stack.append(ArgOpPredicate(arg, words, op))
            self.goto('E4')

        def rE4__arg_op_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            op = self.stack.pop()

            self.stack.pop()
            arg = self.stack.pop()

            self.stack.append(ArgOpPredicate(arg, words, op))
            self.goto('E4')

        def rWords__word_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            word = self.stack.pop()

            self.stack.append(WordsPredicate(word) + words)
            self.goto('Words')

        def rE4__tag():
            self.stack.pop()
            tag = self.stack.pop()

            self.stack.append(TagPredicate(tag))
            self.goto('E4')

        # generated code
        self.parsing_table = {
            0: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": goto_gen(6),
                "E2": goto_gen(5),
                "E3": goto_gen(4),
                "E1": goto_gen(3),
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            1: {
                "$": rE4__Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__Words,
                "lparen": err,
                "not": err,
                "or": rE4__Words,
                "and": rE4__Words,
                "plusD": rE4__Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            2: {
                "$": rE3__E4,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__E4,
                "lparen": err,
                "not": err,
                "or": rE3__E4,
                "and": rE3__E4,
                "plusD": rE3__E4,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            3: {
                "$": rS__E1,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": shift_gen(19),
                "plusD": shift_gen(18),
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            4: {
                "$": rE2__E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE2__E3,
                "lparen": err,
                "not": err,
                "or": rE2__E3,
                "and": rE2__E3,
                "plusD": rE2__E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            5: {
                "$": rE1__E2,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE1__E2,
                "lparen": err,
                "not": err,
                "or": shift_gen(17),
                "and": rE1__E2,
                "plusD": rE1__E2,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            6: {
                "$": acc,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            7: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": goto_gen(16),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            8: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": goto_gen(5),
                "E3": goto_gen(4),
                "E1": goto_gen(15),
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            9: {
                "$": err,
                "word": err,
                "tag": err,
                "op": shift_gen(14),
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            10: {
                "$": rE4__tag,
                "word": err,
                "tag": err,
                "op": shift_gen(13),
                "arg": err,
                "rparen": rE4__tag,
                "lparen": err,
                "not": err,
                "or": rE4__tag,
                "and": rE4__tag,
                "plusD": rE4__tag,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            11: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(12),
            },
            12: {
                "$": rWords__word_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__word_Words,
                "lparen": err,
                "not": err,
                "or": rWords__word_Words,
                "and": rWords__word_Words,
                "plusD": rWords__word_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            13: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(24),
            },
            14: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(23),
            },
            15: {
                "$": err,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": shift_gen(22),
                "lparen": err,
                "not": err,
                "or": err,
                "and": shift_gen(19),
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            16: {
                "$": rE3__not_E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__not_E3,
                "lparen": err,
                "not": err,
                "or": rE3__not_E3,
                "and": rE3__not_E3,
                "plusD": rE3__not_E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            17: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": goto_gen(21),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            18: {
                "$": rS__E1_plusD,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            19: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": goto_gen(20),
                "E3": goto_gen(4),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            20: {
                "$": rE1__E1_and_E2,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE1__E1_and_E2,
                "lparen": err,
                "not": err,
                "or": shift_gen(17),
                "and": rE1__E1_and_E2,
                "plusD": rE1__E1_and_E2,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            21: {
                "$": rE2__E2_or_E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE2__E2_or_E3,
                "lparen": err,
                "not": err,
                "or": rE2__E2_or_E3,
                "and": rE2__E2_or_E3,
                "plusD": rE2__E2_or_E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            22: {
                "$": rE3__lparen_E1_rparen,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__lparen_E1_rparen,
                "lparen": err,
                "not": err,
                "or": rE3__lparen_E1_rparen,
                "and": rE3__lparen_E1_rparen,
                "plusD": rE3__lparen_E1_rparen,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            23: {
                "$": rE4__arg_op_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__arg_op_Words,
                "lparen": err,
                "not": err,
                "or": rE4__arg_op_Words,
                "and": rE4__arg_op_Words,
                "plusD": rE4__arg_op_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            24: {
                "$": rE4__tag_op_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__tag_op_Words,
                "lparen": err,
                "not": err,
                "or": rE4__tag_op_Words,
                "and": rE4__tag_op_Words,
                "plusD": rE4__tag_op_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
        }

    def parse(self):
        """returns parsed predicate, throws ParsingError"""
        lex = self.lexer.top()
        state = self.stack[-1]
        parsed = self.parsing_table[state][lex.type]()
        if parsed:
            return parsed
        else:
            return self.parse()


class OrPredicate(object):
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side

    def test(self, item):
        return self.left_side.test(item) or self.right_side.test(item)

    def __str__(self):
        return "{0} or {1}".format(self.left_side, self.right_side)


class AndPredicate(object):
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side

    def test(self, item):
        return self.left_side.test(item) and self.right_side.test(item)

    def __str__(self):
        return "{0} and {1}".format(self.left_side, self.right_side)


class NotPredicate(object):
    def __init__(self, negated):
        self.negated = negated

    def test(self, item):
        return not self.negated.test(item)

    def __str__(self):
        return "not {0}".format(self.negated)

# all operation are case insensitive
op_functions = {
    '=': lambda x, y: x.lower() == y.lower(),
    '!=': lambda x, y: x.lower() != y.lower(),
    '<': lambda x, y: x.lower() < y.lower(),
    '<=': lambda x, y: x.lower() <= y.lower(),
    '>=': lambda x, y: x.lower() >= y.lower(),
    '>': lambda x, y: x.lower() > y.lower(),
    '$': lambda x, y: y.lower() in x.lower(),
    'matches': lambda x, y: bool(re.match(y, x))
}

op_functions['contains'] = op_functions['$']


class ArgOpPredicate(object):
    def __init__(self, left_side, right_side, op):
        self.left_side = left_side.text
        self.right_side = right_side.words
        self.op = op.text

    def test(self, item):
        # long switch-case / if:elif chain
        # runs different tests depending on self.left_side
        if self.left_side[0] == '@':
            tag_search = '(^|(?<=\s))' + self.left_side + r'\(([^)]*)\)'
            match = re.search(tag_search, item.title.text)
            if match:
                left_side = match.group(2)
            else:
                return False
            r = op_functions[self.op](left_side, self.right_side)
            return r

        elif self.left_side == 'project':
            projects_meets = []
            # if item itself is a project it must be considered
            if item.type == 'project':
                if op_functions[self.op](item.title.content, self.right_side):
                    projects_meets.append(True)
                else:
                    projects_meets.append(False)
            # check chain of parents
            while item.parent_item:
                if (op_functions[self.op](item.parent_item.title.content, self.right_side) and \
                   item.parent_item.type == 'project'):
                    projects_meets.append(True)
                else:
                    projects_meets.append(False)
                item = item.parent_item

            if self.op == '!=':  # != behaves in other way
                return all(projects_meets)
            else:
                return any(projects_meets)

        elif self.left_side == 'line':
            return op_functions[self.op](item.title.line.strip(), self.right_side.strip())
        elif self.left_side == 'uniqueid':
            return op_functions[self.op](str(item.title._id), self.right_side)
        elif self.left_side == 'content':
            return op_functions[self.op](item.title.content, self.right_side)
        elif self.left_side == 'type':
            return op_functions[self.op](item.type, self.right_side)
        elif self.left_side == 'level':
            return op_functions[self.op](str(item.title.indent_level), self.right_side)
        elif self.left_side == 'parent':
            if item.parent_item:
                return op_functions[self.op](item.parent_item.title.content, self.right_side)
            return False
        elif self.left_side == 'index':
            return op_functions[self.op](str(item.index()), self.right_side)

    def __str__(self):
        return "{0} {2} {1}".format(self.left_side, self.right_side, self.op)


class PlusDescendants(object):
    def __init__(self, predicate):
        self.predicate = predicate

    def test(self, item):
        # if predicate is true for any parent it's also true for self
        while item:
            if self.predicate.test(item):
                return True
            item = item.parent_item
        return False

    def str(self):
        return str(self.predicate) + ' +d'


class WordsPredicate(object):
    """if text contains some text as subtext"""
    def __init__(self, words=None):
        self.words = words.text if words else ''

    def test(self, item):
        return self.words.lower() in item.title.text.lower()

    def __str__(self):
        return self.words

    def __add__(self, other):
        new_word = WordsPredicate()
        new_word.words = (self.words + ' ' + other.words).strip()
        return new_word


class TagPredicate(object):
    def __init__(self, tag):
        self.tag = tag.text

    def test(self, item):
        return item.has_tag(self.tag)

    def __str__(self):
        return self.tag


def parse_predicate(text):
    return Parser(Lexer(text)).parse()

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

"""
Main module, provides functions needes to
create TodoList object from plain text files
and operations that use items unique id like
tagging and removing.
"""

from todolist import TodoList, Task, Project
from todolist_parser import Parser
import fileslist as lists
from topy.config import quick_query_abbreviations as abbreviations
from topy.config import quick_query_abbreviations_conjuction as conjuction
import os.path
import subprocess
import todolist as todolist
from filterpredicate import TagPredicate


def from_file(path):
    return Parser.list_from_file(path.strip())


def from_files(paths):
    """
    Constructs todolist from many files,
    content of the file is inserted to project that has
    file name as title

    paths - collection of path or tab separated string
    """
    if isinstance(paths, str):
        paths = paths.split('\t')
    items = []
    for path in paths:
        path = path.rstrip()
        tlist = from_file(path)
        tlist.indent()
        # set file name as project title
        title = os.path.splitext(os.path.basename(path))[0] + ':'
        p = Project(line=title, sub_tasks=tlist)
        p.source = path  # set source to use in `save` function
        items.append(p)
    return TodoList(items)


def do(item_id):
    TodoList.do(item_id)


def tag(item_id, tag, param=None):
    TodoList.tag(item_id, tag, param)


def remove(item_id):
    TodoList.remove(item_id)


def edit(item_id, new_content):
    TodoList.edit(item_id, new_content.decode('utf-8'))


def get_content(item_id):
    return TodoList.get_content(item_id)


def get_text(item_id):
    return TodoList.get_text(item_id)


def tag_dependand_action(item_id):
    item = TodoList.get_item(item_id)

    to_open = ('@mail', '@web', '@file')
    for tag in to_open:
        if item.has_tag(tag):
            action.open(item.get_tag_param(tag))

    content = item.get_content()
    if item.has_any_tags(['@download', '@tvseries', '@comics']):
        action.alfred_search('pb ' + content)
    if item.has_any_tags(['@search', '@research']):
        action.alfred_search('g ' + content)
    action.put_to_clipboard(content)


class action():
    @staticmethod
    def open(to_open):
        subprocess.call('open "{0}"'.format(to_open), shell=True)

    @staticmethod
    def alfred_search(query):
        subprocess.call(
            'osascript -e "tell application \\"Alfred 2\\" to search \\"{0}\\""'.format(query),
            shell=True
        )

    @staticmethod
    def put_to_clipboard(text):
        subprocess.call('echo ' + text + ' | pbcopy', shell=True)


def add_new_subtask(item_id, new_item):
    """
    new_item should be item of type Task, Project, Note or
    string, in that case it's assumed that it's task
    """
    if isinstance(new_item, unicode):
        new_item = TodoList([Task('- ' + new_item)])
    TodoList.items_by_id[item_id].append_subtasks(new_item)


def expand_shortcuts(query):
    if query == '':
        return ''
    if query[0] == ' ':  # no abbreviations
        return query.strip()
    else:
        expanded_query = []
        # expand abbreviations till first space
        first_space_idx = query.find(' ')
        if first_space_idx == -1:
            first_space_idx = len(query)

        for i in range(0, first_space_idx):
            if not query[i] in abbreviations:
                return query.strip()
            expanded_query.append(abbreviations[query[i]])
        expanded_query.append(query[first_space_idx + 1:])
        return conjuction.join(expanded_query)


def archive(tlist, archive_tlist=None):
    """
    moves @done items to first project of title Archive
    assumes that it exsits
    if `archive_tlist` is not specified puts archived items
    to itself
    """
    done = tlist.filter('@done and project != Archive', remove=True)
    done_list = done.deep_copy().flatten()
    if not archive_tlist:
        archive_tlist = tlist
    arch_id = archive_tlist.find_project_id_by_title('Archive')
    TodoList.items_by_id[arch_id].prepend_subtasks(TodoList(done_list))


def save(tlist):
    """
    Use to save changes to individual files of todolist constructed
    by `from_files` function.

    At the moment it's inefficient - function rewrites every file,
    even if todo list from it wasn't modified. If I notice that
    it has influence on workflow I'll improve this.
    """
    for item in tlist.items:
        if hasattr(item, 'source'):
            with open(item.source.strip(), 'w') as f:
                item.sub_tasks.indent(-1)
                f.write(item.sub_tasks.as_plain_text().encode('utf-8'))

########NEW FILE########
__FILENAME__ = todolist
# -*- coding: utf-8 -*-

"""
Module defines main objects of todolist structure:
- TodoList
- Item
- Task
- Project
- Note
- NewLineItem

"""

import re
from cgi import escape
import topy.config as config
from alfredlist import AlfredItemsList
from datetime import date
from filterpredicate import parse_predicate
from todolist_utils import *
import colors


class TodoList(object):
    items_by_id = {}
    _current_id = 0

    @classmethod
    def assign_id(cls, item):
        cls.items_by_id[cls._current_id] = item
        cls._current_id += 1
        return cls._current_id - 1

    @classmethod
    def tag(cls, id_no, tag, param=None):
        cls.items_by_id[id_no].tag(tag, param)

    @classmethod
    def do(cls, id_no):
        cls.items_by_id[id_no].tag(
            'done',
            date.today().isoformat() if config.date_after_done else None
        )

    @classmethod
    def get_item(cls, id_no):
        return cls.items_by_id[id_no]

    @classmethod
    def get_content(cls, id_no):
        return cls.items_by_id[id_no].get_content()

    @classmethod
    def get_text(cls, id_no):
        return cls.items_by_id[id_no].get_text()

    @classmethod
    def remove(cls, id_no):
        cls.items_by_id[id_no].remove_self_from_parent()

    @classmethod
    def edit(cls, id_no, new_content):
        cls.items_by_id[id_no].edit(new_content)

    def __init__(self, items=None):
        self.items = items if items else []
        self.set_parent_list(self.items)
        self.source = None
        self.tags_counters = {}
        self._iter_items_idx = 0

    def __str__(self):
        return self.as_plain_text()

    def __nonzero__(self):
        return bool(self.items)

    def __add__(self, other):
        items = self.items

        first_trailing_newline_idx = len(items) - 1
        while first_trailing_newline_idx > 0 and\
              isinstance(items[first_trailing_newline_idx], NewLineItem):
            first_trailing_newline_idx -= 1
        first_trailing_newline_idx += 1

        items = \
            items[0:first_trailing_newline_idx] +\
            other.items + items[first_trailing_newline_idx:]

        return TodoList(
            items
            )

    def __iter__(self):
        return self

    def next(self):
        if not self.items:
            raise StopIteration
        try:
            return self.items[self._iter_items_idx].next()
        except StopIteration:
            self._iter_items_idx += 1
            if self._iter_items_idx >= len(self.items):
                raise StopIteration
            else:
                return self.items[self._iter_items_idx].next()

    def copy(self):
        return TodoList(self.copy_of_items())

    def deep_copy(self):
        return TodoList(self.deep_copy_of_items())

    def to_file(self, path):
        text = self.as_plain_text(
            colored=False,
            with_ids=False,
            indent=True
        ).code('utf-8')

        with open(path, 'w') as f:
            f.write(text)


    def copy_of_items(self):
        return [item.copy() for item in self.items if item]

    def deep_copy_of_items(self):
        return [item.deep_copy() for item in self.items]

    def remove_item(self, item):
        self.items.remove(item)

    def set_parent_list(self, items):
        for item in items:
            item.parent_list = self

    def add_parent(self, parent):
        for item in self.items:
            item.add_parent(parent)

    def indent(self, level=1):
        for item in self.items:
            item.indent(level)

    def set_indent_level(self, level):
        for item in self.items:
            item.set_indent_level(level)

    def remove_tag(self, tag):
        """removes every occurrence of given tag in list"""
        for item in self.items:
            item.remove_tag(tag)

    def tag_with_parents(self):
        """
        add tag `parents` with `/` separated list of parents
        to every item
        """
        for item in self.items():
            item.tag_with_parents()

    def flatten(self):
        """returns as flat list of items"""
        flattened = []
        for item in self.items:
            flattened += item.flatten()
        return flattened

    def prepend(self, items_list):
        self.set_parent_list(items_list)
        self.items = items_list + self.items

    def append(self, items_list):
        self.set_parent_list(items_list)
        self.items += items_list

    def find_project_id_by_title(self, title):
        """
        returns id of first project of given title in list
        returns None when there is no such item
        """
        filtered = self.filter('content = ' + title + ' and type ="project"')
        for item in filtered.items:
            if item.title.content == title:
                return item.title._id
            else:  # check subtasks recursively
                if item.sub_tasks:
                    q = item.sub_tasks.find_project_id_by_title(title)
                    if q:
                        return q
        return None

    def filter(self, predicate, remove=False):
        """
        returns new list that contains only elements that
        meet predicate.

        Also if `remove` is set to True removes those elements
        from self.
        """
        # parse predicate if it's in string
        if isinstance(predicate, unicode) or isinstance(predicate, str):
            predicate = parse_predicate(predicate)

        filtered_items_with_None = [
            item.filter(predicate, remove) for item in self.items
        ]
        filtered_items = [
            item for item in filtered_items_with_None if item
        ]
        new_list = TodoList(filtered_items)
        return new_list

    def as_plain_text(self, colored=False, with_ids=False, indent=True):
        items_texts_list = [
            item.as_plain_text(colored, with_ids, indent) for item in self.items
        ]
        return "\n".join(items_texts_list)

    def as_alfred_xml(self, include_projects=False, additional_arg=None):
        al = AlfredItemsList()
        for item in self.items:
            al_item = item.as_alfred_xml(include_projects, additional_arg)
            if al_item:  # item returns None if it shouldn't be displayed in alfred
                al += al_item
        return al

    def as_countdown(self, colored=False):
        today = date.today().isoformat()
        only_due = self.filter(
            '((@due and not @done) or (@due >=' + today + ')) and not (@waiting > ' + today + ')'
        )
        items_with_None = [
            item.as_countdown(colored) for item in only_due.items
        ]
        items = [
            item for item in items_with_None if item
        ]
        items.sort()
        return '\n'.join(items)

    def as_markdown(self, emphasise_done=False):
        return "\n".join(
            [item.as_markdown(emphasise_done) for item in self.items]
        )

    def as_html(self):
        items_html = "\n".join([item.as_html() for item in self.items])
        return "<ul>" + items_html + "</ul>"

    def as_full_html(self, css_style=None):
        return u"""
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    {1}
</head>
<body>
<div class="container">
    {0}
</div>
</body>""".format(
    self.as_html(),
    u"""<link href="{0}" rel="stylesheet" type="text/css" />""".format(
        css_style
    ) if css_style else ''
)


class ItemTitle(object):
    def __init__(self, line, line_no, indent_level, typ):
        self.line = line
        self.text = extract_text(typ, line)
        self.content = extract_content(typ, line)
        self.type = typ
        # line, text & content at the moment
        # contain some redundant data

        self._id = TodoList.assign_id(self)
        self.line_no = line_no
        self.indent_level = indent_level

        self.prefix = ''
        self.postfix = ''

        self.colors = {}
        self.colors['ident_color'] = colors.defc
        self.colors['prefix_color'] = colors.defc
        self.colors['text_color'] = colors.defc
        self.colors['postfix_color'] = colors.defc
        self.colors['postfix_color'] = colors.defc
        self.colors['tag_color'] = colors.green

    def deep_copy(self):
        new = ItemTitle(
            line=self.line,
            line_no=0,
            indent_level=self.indent_level,
            typ=self.type
        )
        new.prefix = self.prefix
        new.postfix = self.postfix
        return new

    def set_indent_level(self, level):
        self.indent_level = level

    def remove_indent(self):
        self.indent_level = 0

    def edit(self, new_text):
        self.text = new_text.strip()
        self.content = remove_trailing_tags(self.text)

    def indent(self, level=1):
        self.indent_level += level

    def tag(self, tag_text, param=None):
        self.line = add_tag_to_text(self.line, tag_text, param)
        self.text = add_tag_to_text(self.text, tag_text, param)

    def remove_tag(self, tag):
        self.text = remove_tag_from_text(self.text, tag)
        self.line = remove_tag_from_text(self.line, tag)
        self.content = remove_tag_from_text(self.content, tag)

    def get_text_without_tags(self):
        return remove_tags(self.content)

    def has_tag(self, tag):
        return bool(re.search("(^| )" + tag + "($| |\()", self.text))

    def has_tags(self, tags):
        return all(self.has_tag(tag) for tag in tags)

    def has_any_tags(self, tags):
        return any(self.has_tag(tag) for tag in tags)

    def get_tag_param(self, tag):
        tag_search = '(^|(?<=\s))' + tag + r'\(([^)]*)\)'
        match = re.search(tag_search, self.text)
        if match:
            return match.group(2)

    def is_done(self):
        return bool(re.search(done_tag, self.line))


class Item(object):
    """
    Abstract item on todolist
    """
    def __init__(self, line='', indent_level=None, sub_tasks=None, typ='item'):
        self.title = ItemTitle(line, line_no, indent_level, typ)
        self.parent_item = None  # Project, Task or Note
        self.parent_list = None  # TodoList
        self.type = typ

        self.sub_tasks = sub_tasks
        TodoList.items_by_id[self.title._id] = self

        if self.sub_tasks:
            self.sub_tasks.add_parent(self)

        self._iter_returned_self = False
        self._iter_subtasks_idx = 0

    def __eq__(self, other):
        return self.title == other.title

    def __str__(self):
        return self.as_plain_text()

    def __iter__(self):
        return self

    def next(self):
        if not self._iter_returned_self:
            self._iter_returned_self = True
            return self
        if self._iter_returned_self and not self.sub_tasks:
            raise StopIteration
        else:
            return self.sub_tasks.next()


    def get_content(self):
        return self.title.content

    def get_text(self):
        return self.title.text

    def copy(self):
        new = self.empty()
        new.title = self.title
        new.parent_item = self.parent_item
        new.parent_list = self.parent_list
        new.sub_tasks = self.sub_tasks.copy() if self.sub_tasks else None
        new.type = self.type
        return new

    def deep_copy(self):
        new = self.empty()
        new.title = self.title.deep_copy()
        new.parent_item = self.parent_item
        new.parent_list = self.parent_list
        new.sub_tasks = self.sub_tasks.deep_copy() if self.sub_tasks else None
        new.type = self.type
        return new

    def index(self):
        return self.parent_list.items.index(self)

    def remove_indent(self):
        self.title.remove_indent()

    def indent(self, level=1):
        self.title.indent(level)
        if self.sub_tasks:
            self.sub_tasks.indent(level)

    def tag(self, tag_text, param=None):
        self.title.tag(tag_text, param)

    def tag_with_parents(self):
        self.tag('parents', self.parents_to_str())

    def remove_tag(self, tag):
        self.title.remove_tag(tag)
        if self.sub_tasks:
            self.sub_tasks.remove_tag(tag)

    def has_tag(self, tag):
        return self.title.has_tag(tag)

    def has_tags(self, tags):
        return self.title.has_tags(tags)

    def has_any_tags(self, tags):
        return self.title.has_any_tags(tags)

    def is_nth_with_tag(self, number, tag):
        if not self.has_tag(tag) or self.has_tag('@done'):
            return False
        self_number = self.parent_list.tags_counters.get(tag, 0)
        self.parent_list.tags_counters[tag] = self_number + 1
        if number == self_number:
            return True
        else:
            return False

    def get_tag_param(self, tag):
        return self.title.get_tag_param(tag)

    def parents_to_str(self):
        parents_contents = []
        item = self
        while item.parent_item:
            parents_contents.append(item.parent_item.title.content)
            item = item.parent_item
        return ' / '.join(parents_contents[::-1])

    def add_parent(self, parent):
        self.parent_item = parent

    def remove_self_from_parent(self):
        self.parent_list.remove_item(self)

    def indent_new_subtasks(self, items):
        for item in items.items:
            item.title.set_indent_level(self.title.indent_level + 1)

    def set_indent_level(self, level):
        self.title.indent_level = level
        if self.sub_tasks:
            self.sub_tasks.set_indent_level(level + 1)

    def edit(self, new_content):
        self.title.edit(new_content)

    def prepend_subtasks(self, items):
        self.indent_new_subtasks(items)
        if self.sub_tasks:
            self.sub_tasks = items + self.sub_tasks
        else:
            self.sub_tasks = items

    def append_subtasks(self, items):
        self.indent_new_subtasks(items)
        if self.sub_tasks:
            self.sub_tasks = self.sub_tasks + items
        else:
            self.sub_tasks = items

    def flatten(self):
        self.tag_with_parents()
        flattened = []
        if self.type in ('note', 'task'):
            flattened.append(self.copy())
        if self.sub_tasks:
            flattened += self.sub_tasks.flatten()
        return flattened

    def is_type(self, typ):
        return self.type == typ

    def is_done(self):
        return self.title.is_done()

    def filter(self, predicate, remove=False):
        """
        Returns new item (with the same title object)
        if item itself or any of subtasks meets predicate.

        Subtasks of item are also filtered.

        If `remove` is set to True removes items that meet
        predicate from subtasks.
        """
        new = self.copy()
        if self.sub_tasks:
            new.sub_tasks = self.sub_tasks.filter(predicate, remove)
        meets_prediacate = predicate.test(self)
        if remove and new.sub_tasks:
            for item in new.sub_tasks.items:
                if predicate.test(item):
                    self.sub_tasks.items.remove(item)
        if meets_prediacate or new.sub_tasks:
            return new

    def as_plain_text(self, colored=False, with_ids=False, indent=True):
        actual_colors = get_actual_colors(
            self.title.colors,
            colored,
            self.is_done()
        )
        ptext = (u"{indent}{ident_color}{ident}"
                u"{prefix_color}{prefix}"
                u"{text_color}{text}"
                u"{postfix_color}{postfix}"
                u"{def_color}{sub_tasks}").format(
            ident=(
                (unicode(self.title._id) + ' | ') if with_ids else ''
            ),
            indent=(
                ('\t' * self.title.indent_level) if indent else ''
            ),
            text=wtf(self.title.text, actual_colors),
            prefix=self.title.prefix,
            postfix=self.title.postfix,
            sub_tasks=(
                ('\n' + self.sub_tasks.as_plain_text(
                    colored, with_ids, indent
                )
                )
                if self.sub_tasks else ''
            ),
            # colors
            ident_color=actual_colors['ident_color'],
            prefix_color=actual_colors['prefix_color'],
            text_color=actual_colors['text_color'],
            postfix_color=actual_colors['postfix_color'],
            def_color=(colors.defc if colored else '')
        )

        return ptext

    def as_alfred_xml(self, include_projects=False, additional_arg=None):
        al = AlfredItemsList()
        if self.type != 'project' or include_projects:
            al.append(
                arg=str(self.title._id) + \
                    ((';' + additional_arg) if additional_arg else ''),
                # _id never has `;` in it so it's safe encoding
                title=self.title.text,
                subtitle=self.parents_to_str(),
                icon='done' if self.is_done() else self.type
            )
        if self.sub_tasks:
            al += self.sub_tasks.as_alfred_xml(
                include_projects,
                additional_arg
            )
        return al

    def as_countdown(self, colored=False):
        if not ' @due(' in self.title.text:
            if self.sub_tasks:
                return self.sub_tasks.as_countdown(colored)

        time_left = date_to_countdown(
            get_tag_param(self.title.line, 'due')
        )

        actual_colors = get_actual_colors(
            self.title.colors,
            colored,
            self.is_done(),
            time_left[0] == '-'  # is ooverdue?
        )

        if time_left:
            text = u"{time_left} {text_color}{text}{def_color}{sub_tasks}".format(
                time_left=time_left,
                text=enclose_tags(
                    self.title.text,
                    prefix=actual_colors['tag_color'],
                    postfix=actual_colors['countdown_text']
                ),
                sub_tasks=(
                    ('\n' + self.sub_tasks.as_countdown(colored))
                        if self.sub_tasks else ''
                ),
                text_color=actual_colors['countdown_text'],
                def_color=(colors.defc if colored else '')
                )
            return text
        else:
            return ''

    def as_html(self):
        css_class_level = min(
            config.number_of_css_classes,
            self.title.indent_level
        )

        return u'<li><span class="{type_class}{done_class}">{text}</span>{sub_tasks}</li>'.format(
            type_class=self.type + str(css_class_level),
            done_class=(
                ' done' if self.is_done() else ''
            ),
            sub_tasks=(
                ('\n' + self.sub_tasks.as_html())
                    if self.sub_tasks else ''
            ),
            # text=unicode(self.title.text)
            text=enclose_tags(
                unicode(escape(self.title.text)),
                prefix=u'<span class="tag">',
                postfix=u'</span>'
            ),
        )

    def markdown_indent_level(self):
        if self.parent_item:
            if self.parent_item.type == 'project':
                return 0
            return self.parent_item.markdown_indent_level() + 1
        else:
            return 0

    def as_markdown(self, emphasise_done):
        indent = self.markdown_indent()
        text = enclose_tags(self.title.text, '**', '**')
        if self.is_done() and emphasise_done:
            text = '*' + text + '*'
        title = indent + text
        sub_tasks = ''
        if self.sub_tasks:
            sub_tasks = '\n' + self.sub_tasks.as_markdown()
        return title + sub_tasks


class Project(Item):
    def __init__(self, line='', line_no=0, indent_level=0, sub_tasks=None, typ='project'):
        super(Project, self).__init__(line, line_no, indent_level, sub_tasks, typ)
        self.type = 'project'

        self.title.colors['text_color'] = colors.blue

    def markdown_indent_level(self):
        return 0

    def markdown_indent(self):
        return '\n' + '#' * min(self.title.indent_level + 1, 5) + ' '

    def empty(self):
        return Project()


class Task(Item):
    def __init__(self, line='', line_no=0, indent_level=0, sub_tasks=None, typ='task'):
        super(Task, self).__init__(line, line_no, indent_level, sub_tasks, typ)
        self.title.prefix = '- '
        self.type = 'task'

        self.title.colors['prefix_color'] = colors.blue
        self.title.colors['text_color'] = colors.defc

    def markdown_indent(self):
        return '\t' * self.markdown_indent_level() + '- '

    def empty(self):
        return Task()


class Note(Item):
    def __init__(self, line='', line_no=0, indent_level=0, sub_tasks=None, typ='note'):
        super(Note, self).__init__(line, line_no, indent_level, sub_tasks, typ)
        self.type = 'note'

        self.title.colors['text_color'] = colors.yellow

    def markdown_indent(self):
        return '\n' + '\t' * self.markdown_indent_level()

    def empty(self):
        return Note()


class NewLineItem(object):
    def __init__(self):
        self.title = None

    def __getattr__(self, name):
        """
        most functions of NewLineItem returns None and does
        nothing so they don't have to be implemented
        """
        def f(*args, **kwargs):
            pass
        return f

    def next(self):
        raise StopIteration

    def as_plain_text(self, *args):
        return ''

    def flatten(self, *args, **kwargs):
        return []

    def as_markdown(self, *args):
        return '\n'

    def copy(self):
        return NewLineItem()

    def deep_copy(self):
        return NewLineItem()

    def as_html(self):
        return "<br>"


def wtf(t, actual_colors):
    # try:
        # wtf = {
        #     u'ż': u'ż',
        #     u'ę': u'ę',
        #     u'ó': u'ó',
        #     u'ą': u'ą',
        #     u'ś': u'ś',
        #     u'ń': u'ń',
        #     u'ź': u'ź',
        #     u'ć': u'ć',
        #     u'ń': u'ń',
        # }
        # for k, v in wtf.items():
        #     t = t.replace(k, v)
        return u"{0}".format(enclose_tags(
            t,
            prefix=actual_colors['tag_color'],
            postfix=actual_colors['text_color']
        ))  #
    # except:
        # return 'WW'

########NEW FILE########
__FILENAME__ = todolist_lexer
"""
# Lexer of todo lists.

Token stores its type in string, posible types are:

* $ - end of input
* indent - indentation
* newline - `\n`
* dedent - end of indented text
* task - line tht begins with `\t*- `
* project-title - line that is not task and ends with `:`
(with eventual trailing tags after `:`)
* note - line that is not task or project-title

"""
import re


class Token(object):
    @staticmethod
    def is_task(line):
        return line.strip()[0:2] == '- '

    tag_pattern_without_at = re.compile(r'[^\(\s]*(|\([^)]*\))')
    # defines what can be *after @*
    # Tag -> @ Word | @ Word ( Words ) .
    #
    # first part of regexp defines Word -
    # ensures that there is no white signs and `(` in it
    #
    # second part of regexp defines epsilon | ( Words ) -
    # nothing or `(` everything but `)` followed by `)`
    #

    @staticmethod
    def is_project(line):
        splitted = line.split(':')
        if len(splitted) < 2:  # no `:` in line
            return False
        if line[-1] == ' ':  # trailing space after `:`
            return False
        if splitted[1].strip() != '' and splitted[1][0] != '@':
            return False
        # only tags are allowed after `:`
        after_colon = splitted[-1].split('@')
        only_tags_after_colon = all([
            Token.tag_pattern_without_at.match(tag) for tag in after_colon
        ])
        return only_tags_after_colon

    def __init__(self, line=None, indent_level=0, line_no=0):
        if line:
            self.indent_level = indent_level
            self.line_no = line_no
            self.text = line

            if Token.is_task(line):
                self.type = 'task'
            elif Token.is_project(line):
                self.type = 'project-title'
            else:
                self.type = 'note'
        else:  # if there's no line it's end of input
            self.type = '$'
            self.text = ''


class Dedent(Token):
    def __init__(self):
        self.type = 'dedent'
        self.text = ''


class Indent(Token):
    def __init__(self):
        self.type = 'indent'
        self.text = ''


class NewLine(Token):
    def __init__(self):
        self.type = 'newline'
        self.text = '\n'


class Lexer(object):
    def __init__(self, lines):
        self.tokens = Lexer.tokenize(lines)

    @staticmethod
    def indent_level(text):
        indent_char = '\t'
        level = 0
        while level < len(text) and text[level] == indent_char:
            level += 1
        return level

    @staticmethod
    def tokenize(lines):
        """turns input into tokens"""
        tokens = []
        indent_levels = [0]
        for line_no, line in enumerate(lines):
            if line == '\n':
                tokens.append(NewLine())
                # empty lines are ignored in
                # flow of indents so
                continue

            # generate indent and dedent tokens
            current_level = Lexer.indent_level(line)
            if current_level > indent_levels[-1]:
                indent_levels.append(current_level)
                tokens.append(Indent())
            elif current_level < indent_levels[-1]:
                while current_level < indent_levels[-1]:
                    indent_levels.pop()
                    tokens.append(Dedent())

            tokens.append(Token(line, current_level, line_no))

        # add $ token at the end and return
        return [Token()] + tokens[::-1]

    def top(self):
        """returns token on top of stack"""
        return self.tokens[-1]

    def pop(self):
        """removes token from top of stack and returns it"""
        return self.tokens.pop()

    def consume(self, expected_type):
        """removes token from top of stack
        and raises ParseError if it's not of expected type"""
        if self.tokens.pop().type != expected_type:
            raise ParseError


class ParseError(Exception):
    pass

########NEW FILE########
__FILENAME__ = todolist_parser
"""
# Parser of todo list.

Top-down parser of grammar that is almost LL(1).
Conflict is resolved by prefering production 7 over 5.

## Grammar:

    1. TodoList -> Item TodoList .
    2. Item     -> Task SubTasks
    3.           | Project SubTasks
    4.           | Note SubTasks
    5.           | indent TodoList dedent
    6.           | NewLineItem
    7. SubTasks -> indent TodoList dedent
    8.           | .

"""

from todolist_lexer import Lexer
from todolist import TodoList, NewLineItem, Task, Project, Note


class Parser(object):
    def __init__(self, lexer):
        self.lexer = lexer

    @staticmethod
    def list_from_file(filepath):
        with open(filepath, 'r') as f:
            tlist = Parser(Lexer([l.decode('utf-8') for l in f.readlines()])).parse()
            tlist.source = filepath
            return tlist

    def parse(self):
        def todolist():
            """parse list"""
            type_on_top = self.lexer.top().type
            new_item = None

            type_to_constructor = {
                'task': Task,
                'project-title': Project,
                'note': Note,
            }

            # depending on type on top of input
            # construct appropriate object
            if type_on_top == 'newline':
                self.lexer.pop()
                new_item = NewLineItem()
            elif type_on_top in type_to_constructor:
                new_item = parse_item(type_to_constructor[type_on_top])
            elif type_on_top == 'indent':  # begining of sublist
                new_item = parse_sublist()
            elif type_on_top in ('dedent', '$'):
                return TodoList()

            return TodoList([new_item]) + todolist()

        def parse_item(constructor):
            """parse Project, Task or Note with its subtasks"""
            lex = self.lexer.pop()
            sub_tasks = None
            type_on_top = self.lexer.top().type
            if type_on_top == 'indent':
                sub_tasks = parse_sublist()
            return constructor(
                lex.text,
                lex.line_no,
                lex.indent_level,
                sub_tasks,
                )

        def parse_sublist():
            """parse part that begins with indent token"""
            self.lexer.pop()
            sublist = todolist()
            type_on_top = self.lexer.top().type
            if type_on_top == 'dedent':  # don't eat $
                self.lexer.pop()
            return sublist

        return todolist()

########NEW FILE########
__FILENAME__ = todolist_utils
"""
Module provides functions used by objects in todolist module,
mostly operations on text.
"""

import colors
import re
from datetime import date

# regexpes used in functions:

# ( everything but `)` ) or lookahead for \s or end of line
tag_param_regexp = r'(\(([^)]*)\)|(?=(\s|$)))'
# prepend word (sequence without \s and `(`)
tag_regexp_without_at = r'[^\(\s]*' + tag_param_regexp
tag_pattern_without_at = re.compile(tag_regexp_without_at + r'\Z')
# prepend '@'
tag_pattern = re.compile('(@' + tag_regexp_without_at + ')')

#

def custom_tag_regexp(tag):
    return re.compile('@' + tag + tag_param_regexp)

custom_tag_regexp.param_group = 2
done_tag = custom_tag_regexp('done')


def add_tag_to_text(text, tag, param=None):
    if text[-1] != ' ':
        text += ' '
    if not tag.startswith('@'):
        tag = '@' + tag
    text += tag
    if param:
        text += '({0})'.format(param)
    return text


def get_actual_colors(def_colors, colored, is_done, is_overdue=False):
    """
    What color we want to use in text depends
    on three conditions `colored`, `is_done`, `is_overdue`.

    Function gets one dict of colors `def_colors` and returns
    new dict that have changes colors accorgind to those
    conditions.
    """
    res = {}
    for k in def_colors:
        if not colored:
            res[k] = ''
        elif is_done:
            res[k] = colors.gray
        else:
            res[k] = def_colors[k]
    res['countdown_text'] = colors.defc

    if is_done:
        res['countdown_text'] = colors.gray
        res['tag_color'] = colors.gray
    elif is_overdue:
        res['countdown_text'] = colors.red
        res['tag_color'] = colors.red
    if not colored:
        res['countdown_text'] = ''
        res['tag_color'] = ''
    return res


def get_tag_param(text, tag):
    match = re.search(custom_tag_regexp(tag), text)
    if match:
        return match.group(custom_tag_regexp.param_group)
    return None


def remove_trailing_tags(line):
    sp = re.split('\s@', line)
    idx = len(sp) - 1
    while tag_pattern_without_at.match(sp[idx].strip()):
        idx -= 1
        if idx <= 0:
            break
    idx = max(1, idx + 1)  # don't want empty lines, also, loops goes 1 too far
    return ' @'.join(sp[0:idx])


def remove_tags(line):
    return tag_pattern.sub('', line)


def extract_content(typ, line):
    text = extract_text(typ, line)
    if typ in ('task', 'note'):
        return remove_trailing_tags(text)
    elif typ == 'project':
        splitted = text.split(':')
        return ':'.join(splitted[0:-1])


def extract_text(typ, line):
    stripped = line.strip()
    if typ == 'task':
        return stripped[2:]
    return stripped


def enclose_tags(text, prefix, postfix):
    """
    puts `prefix` before and `postfix` after
    every tag in text
    """
    def f(t):
        return prefix + t.group(1) + postfix
    return re.sub(tag_pattern, f, text)


def remove_tag_from_text(text, tag):
    # TODO: lefts two spaces, maybe fix someday
    tag_pattern = custom_tag_regexp(tag)
    return re.sub(tag_pattern, '', text)


def date_to_countdown(date_iso):
    """
    date should be string formated as in ISO format,
    returns number of days from `date_iso` to today
    as string, when can't calculate this number
    returns `???`
    """
    number_of_digits = 3
    # nice formatting for due dates up to 2,74 years in the future
    try:
        splitted = [int(x) for x in date_iso.split('-')]
        param_date = date(splitted[0], splitted[1], splitted[2])
        today = date.today()
        countdown = str((param_date - today).days)
        return countdown.zfill(number_of_digits)
    except Exception as e:
        # print e
        return '?' * number_of_digits

########NEW FILE########
__FILENAME__ = archive
#!/usr/bin/python
import topy
from config import projects_path, archive_path

def archive(projects_list, archive_list):
    save_projects = False
    if isinstance(projects_list, str):
        projects_list = topy.from_file(projects_path)
        save_projects = True

    save_archive = False
    if isinstance(archive_list, str):
        archive_list = topy.from_file(archive_path)
        save_archive = True

    topy.archive(projects_list, archive_list)

    if save_projects:
        projects_list.to_file(projects_path)
    if save_archive:
        archive_list.to_file(archive_list)

    return projects_list, archive_list

if __name__ == '__main__':
    archive(projects_path, archive_path)

########NEW FILE########
__FILENAME__ = config
import os.path
import sys
sys.path += ['/path/to/topy']

###################### Paths ######################

inbox_path = 'path/to/Inbox.todo'
projects_path = 'path/to/Projects.todo'
onhold_path = 'path/to/Onhold.todo'
archive_path = 'path/to/NOTES/Archive.todo'

# items with given tag can be automatically redirected from inbox to proper file

inbox_tag_to_path = {
    '@music': '/Users/bvsc/Dropbox/TODO/NOTES/$music.todo',
    '@film': '/Users/bvsc/Dropbox/TODO/NOTES/$filmy.todo',
    '@book': '/Users/bvsc/Dropbox/TODO/NOTES/$books.todo',
    '@app': '/Users/bvsc/Dropbox/TODO/NOTES/$apps.todo',
    '@game': '/Users/bvsc/Dropbox/TODO/NOTES/$games.todo',
    '@toy': '/Users/bvsc/Dropbox/TODO/NOTES/$toys&tools.todo',
    '@tool': '/Users/bvsc/Dropbox/TODO/NOTES/$toys&tools.todo'
}

###################################################

#### print_today, print_deadlines, print_next #####

# path to files that contains variable if should print
# I use print_... scripts to put my todo list on
# desktop with Nerdtools and somtimes I want
# to hide it
should_print_path = 'path/to/should_print'

###################################################

###################### tvcal ######################

# http://www.pogdesign.co.uk/cat/
tvcal_url = ''  # link from .iCal
tvseries_project_title = 'TV Series:'

###################################################

################## log to day one #################

logging_in_day_one_for_yesterday = True

# change if you store Day One entries somewhere else
day_one_dir_path = os.path.expanduser(
    '~/Dropbox/Apps/Day One/Journal.dayone/entries/'
)

# title of entry
day_one_entry_title = '# Things I did today #\n\n\n'

day_one_extension = '.doentry'

###################################################

################## update lists ###################

# you can translate it to other language or something
# preserve order
days_of_the_week = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
)

# title of projects that contains tasks that
# shoul be do every day
daily_project_title = 'Daily'

# shoul remove waiting tasks that were moved to
# projects.todo form onhold.todo?
remove_waiting_from_onhold = False

###################################################

########NEW FILE########
__FILENAME__ = count_inbox
from config import inbox_path

done_tag = ' @done'

def count_inbox():
    with open(inbox_path, "r") as f:
        count = 0
        for line in f:
            if line[0] == '_':
                break
            if line[0] == "-" and (line.find(done_tag) == -1):
                count += 1
        if count:
            print(count)
        else:
            print(" ")

count_inbox()

########NEW FILE########
__FILENAME__ = create_reminder
import subprocess

applescript_template = """tell application \\"Reminders\\"
    set r to make new reminder
    set name of r to \\"{name}\\"
    set body of r to \\"{body}\\"
    set remind me date of r to date \\"{reminde_me_date}\\"
end tell"""


def create_reminder(name, body, reminde_me_date):
    reminde_me_date = reminde_me_date.strftime('%d-%m-%Y %H:%M')
    applescript = applescript_template.format(
        name=name,
        body=body,
        reminde_me_date=reminde_me_date,
    )
    cmd = 'echo "{0}" | osascript'.format(applescript)
    subprocess.check_output(
        cmd, shell=True
    )

########NEW FILE########
__FILENAME__ = end_the_day
#!/usr/bin/python
from config import projects_path, inbox_path, onhold_path  # archive_path
import topy
# from archive import archive
from update_lists import update_daily, update_weekly, update_waiting, update_followups
from remind import set_reminders
from tvcal import tvcal
from log_to_day_one import log_to_day_one

all_lists = topy.from_files(topy.lists.to_list())
inbox_file = open(inbox_path, 'a')
onhold_list = topy.from_file(onhold_path)

log_to_day_one(all_lists.deep_copy())
try:
    tvcal(inbox_file)
except:
    pass
update_weekly(onhold_list, inbox_file)
update_waiting(onhold_list, inbox_file)

update_daily(all_lists)
update_followups(all_lists)
set_reminders(all_lists)
topy.save(all_lists)

########NEW FILE########
__FILENAME__ = inbox
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import date
from config import inbox_path, inbox_tag_to_path
import re


def make_re(tag):
    return re.compile('(?:^|\s)(' + tag + ')(?:$|\s)')


def inbox(msg):
    if msg[0] != ' ':
        msg = ' ' + msg
    if msg[-1] != ' ':
        msg += ' '
    to_write = '-' + msg + '@in(' + date.today().isoformat() + ')\n'
    path_to_add = inbox_path
    for tag, path in inbox_tag_to_path.items():
        if make_re(tag).findall(msg):
            path_to_add = path
    with open(path_to_add, 'a') as f:
        f.write(to_write + '\n')

if __name__ == '__main__':
    inbox(" ".join(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = itopy
# -*- coding: utf-8 -*-
#
# Configuration of topy
#
# You should read README first
#
from seamless_dropbox import open
from datetime import date
import re
import console
import webbrowser
from notification import schedule as n

# File that stores path to your todo lists
# This location keeps up with alfred workflow
# best practices but you can change it
# to wherever you want
files_list_path = '/Users/bvsc/Dropbox/TODO/'
files_list_name = 'lists'

# logical operator to join shortened queries
quick_query_abbreviations_conjuction = ' and '  # ' or '

# fill with your own, this is what I use:
quick_query_abbreviations = {
    't': '@today',
    'n': '@next',
    'd': 'not @done',
    'u': '@due',
    's': 'project = Studia',
    'i': 'index = 0',
    'f': '(@today or @next)',
    'q': 'project = Projects and not project = Archive'
}

# add date value when tagging with @done
date_after_done = True

# include project titles in list displayed by alfred
# when searching with `q` keyword
include_project_title_in_alfred = False

# when generating html items are given classes
# define how many different classes (depengin on identation level)
# you want to have
number_of_css_classes = 4

# symbols on icons can be transparent or white
white_symbols_on_icons = False  # True

#################################################
# todolist_utils

"""
Module provides functions used by objects in todolist module,
mostly operations on text.
"""

def set_font(color=(0.00, 0.00, 0.00), size=18, font='dejavusansmono'):
    console.set_font(font, size)
    console.set_color(color)

def set_size(size):
    console.set_font('dejavusansmono', size)

def set_color(c):
    console.set_color(*c)

ctoday = (0.00, 0.50, 0.50)
cnext = (0.00, 0.25, 0.50)
cdue = (1.00, 0.00, 0.50)
cdone = (0.70, 0.70, 0.70)
cnote = (0.30, 0.30, 0.30)
ctask = (0.10, 0.10, 0.10)

# regexpes used in functions:

# ( everything but `)` ) or lookahead for \s or end of line
tag_param_regexp = r'(\(([^)]*)\)|(?=(\s|$)))'
# prepend word (sequence without \s and `(`)
tag_regexp_without_at = r'[^\(\s]*' + tag_param_regexp
tag_pattern_without_at = re.compile(tag_regexp_without_at + r'\Z')
# prepend '@'
tag_pattern = re.compile('(@' + tag_regexp_without_at + ')')

#


def custom_tag_regexp(tag):
    return re.compile('@' + tag + tag_param_regexp)

custom_tag_regexp.param_group = 2
done_tag = custom_tag_regexp('done')


def add_tag_to_text(text, tag, param=None):
    if text[-1] != ' ':
        text += ' '
    text += "@" + tag
    if param:
        text += '({0})'.format(param)
    return text


def get_tag_param(text, tag):
    match = re.search(custom_tag_regexp(tag), text)
    if match:
        return match.group(custom_tag_regexp.param_group)
    return None


def remove_trailing_tags(line):
    sp = re.split('\s@', line)
    idx = len(sp) - 1
    while tag_pattern_without_at.match(sp[idx].strip()):
        idx -= 1
        if idx <= 0:
            break
    idx = max(1, idx + 1)  # don't want empty lines, also, loops goes 1 too far
    return ' @'.join(sp[0:idx])


def extract_content(typ, line):
    text = extract_text(typ, line)
    if typ in ('task', 'note'):
        return remove_trailing_tags(text)
    elif typ == 'project':
        splitted = text.split(':')
        return ':'.join(splitted[0:-1])


def extract_text(typ, line):
    stripped = line.strip()
    if typ == 'task':
        return stripped[2:]
    return stripped


def enclose_tags(text, prefix, postfix):
    """
    puts `prefix` before and `postfix` after
    every tag in text
    """
    def f(t):
        return prefix + t.group(1) + postfix
    return re.sub(tag_pattern, f, text)


def remove_tag_from_text(text, tag):
    # TODO: lefts two spaces, maybe fix someday
    tag_pattern = custom_tag_regexp(tag)
    return re.sub(tag_pattern, '', text)


def date_to_countdown(date_iso):
    """
    date should be string formated as in ISO format,
    returns number of days from `date_iso` to today
    as string, when can't calculate this number
    returns `???`
    """
    number_of_digits = 3
    # nice formatting for due dates up to 2,74 years in the future
    try:
        splitted = [int(x) for x in date_iso.split('-')]
        param_date = date(splitted[0], splitted[1], splitted[2])
        today = date.today()
        countdown = str((param_date - today).days)
        return countdown.zfill(number_of_digits)
    except Exception as e:
        # print e
        return '?' * number_of_digits


# todolist_utils
#################################################
# todolist_lexer

"""
# Lexer of todo lists.

Token stores its type in string, posible types are:

* $ - end of input
* indent - indentation
* newline - `\n`
* dedent - end of indented text
* task - line tht begins with `\t*- `
* project-title - line that is not task and ends with `:`
(with eventual trailing tags after `:`)
* note - line that is not task or project-title

"""


class Token(object):
    @staticmethod
    def is_task(line):
        return line.strip()[0:2] == '- '

    tag_pattern_without_at = re.compile(r'[^\(\s]*(|\([^)]*\))')
    # defines what can be *after @*
    # Tag -> @ Word | @ Word ( Words ) .
    #
    # first part of regexp defines Word -
    # ensures that there is no white signs and `(` in it
    #
    # second part of regexp defines epsilon | ( Words ) -
    # nothing or `(` everything but `)` followed by `)`
    #

    @staticmethod
    def is_project(line):
        splitted = line.split(':')
        if len(splitted) < 2:  # no `:` in line
            return False
        if line[-1] == ' ':  # trailing space after `:`
            return False
        if splitted[1].strip() != '' and splitted[1][0] != '@':
            return False
        # only tags are allowed after `:`
        after_colon = splitted[-1].split('@')
        only_tags_after_colon = all([
            Token.tag_pattern_without_at.match(tag) for tag in after_colon
        ])
        return only_tags_after_colon

    def __init__(self, line=None, indent_level=0, line_no=0):
        if line:
            self.indent_level = indent_level
            self.line_no = line_no
            self.text = line

            if Token.is_task(line):
                self.type = 'task'
            elif Token.is_project(line):
                self.type = 'project-title'
            else:
                self.type = 'note'
        else:  # if there's no line it's end of input
            self.type = '$'
            self.text = ''


class Dedent(Token):
    def __init__(self):
        self.type = 'dedent'
        self.text = ''


class Indent(Token):
    def __init__(self):
        self.type = 'indent'
        self.text = ''


class NewLine(Token):
    def __init__(self):
        self.type = 'newline'
        self.text = '\n'


class Lexer(object):
    def __init__(self, lines):
        self.tokens = Lexer.tokenize(lines)

    @staticmethod
    def indent_level(text):
        indent_char = '\t'
        level = 0
        while level < len(text) and text[level] == indent_char:
            level += 1
        return level

    @staticmethod
    def tokenize(lines):
        """turns input into tokens"""
        tokens = []
        indent_levels = [0]
        for line_no, line in enumerate(lines):
            if line == '':
                tokens.append(NewLine())
                # empty lines are ignored in
                # flow of indents so
                continue

            # generate indent and dedent tokens
            current_level = Lexer.indent_level(line)
            if current_level > indent_levels[-1]:
                indent_levels.append(current_level)
                tokens.append(Indent())
            elif current_level < indent_levels[-1]:
                while current_level < indent_levels[-1]:
                    indent_levels.pop()
                    tokens.append(Dedent())

            tokens.append(Token(line, current_level, line_no))

        # add $ token at the end and return
        return [Token()] + tokens[::-1]

    def top(self):
        """returns token on top of stack"""
        return self.tokens[-1]

    def pop(self):
        """removes token from top of stack and returns it"""
        return self.tokens.pop()

    def consume(self, expected_type):
        """removes token from top of stack
        and raises ParseError if it's not of expected type"""
        if self.tokens.pop().type != expected_type:
            raise ParseError


class ParseError(Exception):
    pass

# todolist_lexer
#################################################
# filterpredicate


"""
Predicates for filtering todo list.
Module defines lexer, parser and predicates themself.

Predicate implements method test(text) that returns if
predicate applies to given text.

For example '@today and not @done' returns if text contains
tag @today and not contains tag @done.

grammar of predicates (SLR(1)):

S     -> E1 | E1 +d
E1    -> E1 and E2
       | E2.
E2    -> E2 or E3
       | E3.
E3    -> not E3
       | E4
       | ( E1 ).
E4    -> Argument op Words
       | Words
       | Tag .
Words -> word Words
       | .

those rules are not part of SLR automaton:
op     -> = | != | < | <= | >= | > | matches | contains | $ . ($ is abbreviation for contains)
Tag    -> @ word | EndTag.
EndTag -> (Words) | epsilon.
Argument -> project | line | uniqueid | content | type | level | parent | index | Tag.



Arguments:
- project - check project title
- line - line with whole `-`, and tags
- uniqueid - id of element
- content - line without formatting and trailing tags
- type - "project", task or note
- level - indentation level
- parent - checks parents recursively
- index - index in sublist, starts with 0
- tag parameter - value enclosed in parenthesises after tag
"""


class TokenF(object):
    operators = ['=', '!=', '<', '<=', '>', '>=', '$', 'matches', 'contains']
    log_ops = ['and', 'or', 'not']
    keywords = ['project', 'line', 'uniqueid', 'content', 'type', 'level', 'parent', 'index']
    tag_prefix = '@'

    def __init__(self, text=None):
        # long switch-case / if:elif chain
        self.text = text
        # set type of token
        if not text:
            self.type = '$'
        elif text in TokenF.operators:
            self.type = 'op'
        elif text == '+d':
            self.type = 'plusD'
        elif text in TokenF.log_ops:
            self.type = text
        elif text in TokenF.keywords:
            self.type = 'arg'
        elif text[0] == TokenF.tag_prefix:
            self.type = 'tag'
        elif text[0] == '"':
            self.type = 'word'
            self.text = text[1:-1]
        elif text == '(':
            self.type = 'lparen'
        elif text == ')':
            self.type = 'rparen'
        else:
            self.type = 'word'

    def __str__(self):
        return repr(self.text) + ' : ' + self.type


class LexerF(object):
    def __init__(self, input_text):
        self.tokens = LexerF.tokenize(input_text)

    @staticmethod
    def tokenize(input_text):
        """converts input text to list of tokens"""
        tokens = []

        def add_token(text=None):
            if text != '' and text != ' ':
                tokens.append(TokenF(text))

        idx = 0
        collected = ''
        text_length = len(input_text)

        while idx < text_length + 1:
            # lengthy switch-case like statement
            # that processes input text depending on
            # current char
            if idx == text_length:
                # finish tokenizing
                add_token(collected)  # add remaining collected text
                add_token()  # add end of input token
            elif input_text[idx] == '+':
                if idx + 1 < len(input_text):
                    if input_text[idx + 1] == 'd':
                        add_token(collected)
                        collected = ''
                        add_token('+d')
                        idx += 1
            elif input_text[idx] == ' ':
                # spaces separate but but don't have semantic meaning
                add_token(collected)
                collected = ''
            elif input_text[idx] in ('(', ')'):
                # parenthesises seperate
                add_token(collected)
                collected = ''
                add_token(input_text[idx])
            elif input_text[idx] in ('<', '>', '!'):
                # operators or prefixes of operators
                add_token(collected)
                collected = input_text[idx]
            elif input_text[idx] == '=':
                if collected in ('<', '>', '!'):
                    # "="" preceded by any of this signs is an operator
                    collected += '='
                    add_token(collected)
                else:
                    # "=" by itself is also an operator
                    add_token(collected)
                    add_token('=')
                collected = ''
            elif input_text[idx] == '$':
                add_token(collected)
                add_token('$')
                collected = ''
            elif input_text[idx] == '"':
                # quoted part of input is allways a word
                add_token(collected)
                collected = ''
                next_quotation_mark_idx = input_text.find('"', idx + 1)
                if next_quotation_mark_idx == -1:
                    # when there is no matching quotation mark
                    # end of the input is assumed
                    add_token(input_text[idx:] + '"')
                    idx = text_length - 1  # sets idx to that value so loop finishes in next iteration
                else:
                    add_token(input_text[idx:next_quotation_mark_idx + 1])
                    idx = next_quotation_mark_idx

            else:
                if collected in ('<', '>'):
                    add_token(collected)
                    collected = ''
                collected += input_text[idx]
            idx += 1

        return tokens[::-1]

    def pop(self):
        """pops and returns topmost token"""
        try:
            return self.tokens.pop()
        except IndexError:
            raise ParsingError

    def top(self):
        """returns topmost token"""
        try:
            return self.tokens[-1]
        except IndexError:
            raise ParsingError


class ParsingError(Exception):
    pass


class ParserF(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.create_parsing_table()
        self.stack = [0]

    def goto(self, state):
        self.parsing_table[self.stack[-2]][state]()

    def create_parsing_table(self):
        # long functions with declaration of parsing table and parser actions

        def shift_gen(state_no):
            def shift():
                """puts lexem and state number on stack"""
                self.stack.append(self.lexer.pop())
                self.stack.append(state_no)
            return shift

        def goto_gen(state_no):
            def goto():
                """puts state number on stack"""
                self.stack.append(state_no)
            return goto

        def err():
            raise ParsingError

        def acc():
            """returns abstrac syntax tree"""
            self.stack.pop()
            return self.stack[-1]

        # reductions, name of the functions contains information about production
        # -> is changed to __, terminals and nonterminals are separated by _
        # left side of production is preceded by `r`

        def rS__E1():
            self.stack.pop()
            self.goto('S')

        def rS__E1_plusD():
            self.stack.pop()
            self.stack.pop()  # +d

            self.stack.pop()
            e1 = self.stack.pop()
            self.stack.append(PlusDescendants(e1))
            self.goto('S')

        def rE3__E4():
            self.stack.pop()
            self.goto('E3')

        def rE1__E2():
            self.stack.pop()
            self.goto('E1')

        def rE2__E3():
            self.stack.pop()
            self.goto('E2')

        def rE3__lparen_E1_rparen():
            self.stack.pop()  # )
            self.stack.pop()

            self.stack.pop()
            e1 = self.stack.pop()

            self.stack.pop()  # (
            self.stack.pop()

            self.stack.append(e1)
            self.goto('E3')

        def rE2__E2_or_E3():
            self.stack.pop()
            e3 = self.stack.pop()

            self.stack.pop()  # or
            self.stack.pop()

            self.stack.pop()
            e2 = self.stack.pop()

            self.stack.append(OrPredicate(e2, e3))
            self.goto('E2')

        def rE4__Words():
            self.stack.pop()
            self.goto('E4')

        def rE1__E1_and_E2():
            self.stack.pop()
            e2 = self.stack.pop()

            self.stack.pop()  # and
            self.stack.pop()

            self.stack.pop()
            e1 = self.stack.pop()

            self.stack.append(AndPredicate(e1, e2))
            self.goto('E1')

        def rE3__not_E3():
            self.stack.pop()
            e3 = self.stack.pop()

            self.stack.pop()  # not
            self.stack.pop()

            self.stack.append(NotPredicate(e3))
            self.goto('E3')

        def rWords__epsilon():
            self.stack.append(WordsPredicate())
            self.goto('Words')

        def rE4__tag_op_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            op = self.stack.pop()

            self.stack.pop()
            arg = self.stack.pop()

            self.stack.append(ArgOpPredicate(arg, words, op))
            self.goto('E4')

        def rE4__arg_op_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            op = self.stack.pop()

            self.stack.pop()
            arg = self.stack.pop()

            self.stack.append(ArgOpPredicate(arg, words, op))
            self.goto('E4')

        def rWords__word_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            word = self.stack.pop()

            self.stack.append(WordsPredicate(word) + words)
            self.goto('Words')

        def rE4__tag():
            self.stack.pop()
            tag = self.stack.pop()

            self.stack.append(TagPredicate(tag))
            self.goto('E4')

        # generated code
        self.parsing_table = {
            0: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": goto_gen(6),
                "E2": goto_gen(5),
                "E3": goto_gen(4),
                "E1": goto_gen(3),
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            1: {
                "$": rE4__Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__Words,
                "lparen": err,
                "not": err,
                "or": rE4__Words,
                "and": rE4__Words,
                "plusD": rE4__Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            2: {
                "$": rE3__E4,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__E4,
                "lparen": err,
                "not": err,
                "or": rE3__E4,
                "and": rE3__E4,
                "plusD": rE3__E4,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            3: {
                "$": rS__E1,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": shift_gen(19),
                "plusD": shift_gen(18),
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            4: {
                "$": rE2__E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE2__E3,
                "lparen": err,
                "not": err,
                "or": rE2__E3,
                "and": rE2__E3,
                "plusD": rE2__E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            5: {
                "$": rE1__E2,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE1__E2,
                "lparen": err,
                "not": err,
                "or": shift_gen(17),
                "and": rE1__E2,
                "plusD": rE1__E2,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            6: {
                "$": acc,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            7: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": goto_gen(16),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            8: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": goto_gen(5),
                "E3": goto_gen(4),
                "E1": goto_gen(15),
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            9: {
                "$": err,
                "word": err,
                "tag": err,
                "op": shift_gen(14),
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            10: {
                "$": rE4__tag,
                "word": err,
                "tag": err,
                "op": shift_gen(13),
                "arg": err,
                "rparen": rE4__tag,
                "lparen": err,
                "not": err,
                "or": rE4__tag,
                "and": rE4__tag,
                "plusD": rE4__tag,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            11: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(12),
            },
            12: {
                "$": rWords__word_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__word_Words,
                "lparen": err,
                "not": err,
                "or": rWords__word_Words,
                "and": rWords__word_Words,
                "plusD": rWords__word_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            13: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(24),
            },
            14: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(23),
            },
            15: {
                "$": err,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": shift_gen(22),
                "lparen": err,
                "not": err,
                "or": err,
                "and": shift_gen(19),
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            16: {
                "$": rE3__not_E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__not_E3,
                "lparen": err,
                "not": err,
                "or": rE3__not_E3,
                "and": rE3__not_E3,
                "plusD": rE3__not_E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            17: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": goto_gen(21),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            18: {
                "$": rS__E1_plusD,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            19: {
                "$": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": goto_gen(20),
                "E3": goto_gen(4),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            20: {
                "$": rE1__E1_and_E2,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE1__E1_and_E2,
                "lparen": err,
                "not": err,
                "or": shift_gen(17),
                "and": rE1__E1_and_E2,
                "plusD": rE1__E1_and_E2,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            21: {
                "$": rE2__E2_or_E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE2__E2_or_E3,
                "lparen": err,
                "not": err,
                "or": rE2__E2_or_E3,
                "and": rE2__E2_or_E3,
                "plusD": rE2__E2_or_E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            22: {
                "$": rE3__lparen_E1_rparen,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__lparen_E1_rparen,
                "lparen": err,
                "not": err,
                "or": rE3__lparen_E1_rparen,
                "and": rE3__lparen_E1_rparen,
                "plusD": rE3__lparen_E1_rparen,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            23: {
                "$": rE4__arg_op_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__arg_op_Words,
                "lparen": err,
                "not": err,
                "or": rE4__arg_op_Words,
                "and": rE4__arg_op_Words,
                "plusD": rE4__arg_op_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            24: {
                "$": rE4__tag_op_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__tag_op_Words,
                "lparen": err,
                "not": err,
                "or": rE4__tag_op_Words,
                "and": rE4__tag_op_Words,
                "plusD": rE4__tag_op_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
        }

    def parse(self):
        """returns parsed predicate, throws ParsingError"""
        lex = self.lexer.top()
        state = self.stack[-1]
        parsed = self.parsing_table[state][lex.type]()
        if parsed:
            return parsed
        else:
            return self.parse()


class OrPredicate(object):
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side

    def test(self, item):
        return self.left_side.test(item) or self.right_side.test(item)

    def __str__(self):
        return "{0} or {1}".format(self.left_side, self.right_side)


class AndPredicate(object):
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side

    def test(self, item):
        return self.left_side.test(item) and self.right_side.test(item)

    def __str__(self):
        return "{0} and {1}".format(self.left_side, self.right_side)


class NotPredicate(object):
    def __init__(self, negated):
        self.negated = negated

    def test(self, item):
        return not self.negated.test(item)

    def __str__(self):
        return "not {0}".format(self.negated)

# all operation are case insensitive
op_functions = {
    '=': lambda x, y: x.lower() == y.lower(),
    '!=': lambda x, y: x.lower() != y.lower(),
    '<': lambda x, y: x.lower() < y.lower(),
    '<=': lambda x, y: x.lower() <= y.lower(),
    '>=': lambda x, y: x.lower() >= y.lower(),
    '>': lambda x, y: x.lower() > y.lower(),
    '$': lambda x, y: y.lower() in x.lower(),
    'matches': lambda x, y: bool(re.match(y, x))
}

op_functions['contains'] = op_functions['$']


class ArgOpPredicate(object):
    def __init__(self, left_side, right_side, op):
        self.left_side = left_side.text
        self.right_side = right_side.words
        self.op = op.text

    def test(self, item):
        # long switch-case / if:elif chain
        # runs different tests depending on self.left_side
        if self.left_side[0] == '@':
            tag_search = '(^|(?<=\s))' + self.left_side + r'\(([^)]*)\)'
            match = re.search(tag_search, item.title.text)
            if match:
                left_side = match.group(2)
            else:
                return False
            r = op_functions[self.op](left_side, self.right_side)
            return r

        elif self.left_side == 'project':
            projects_meets = []
            # if item itself is a project it must be considered
            if item.type == 'project':
                if op_functions[self.op](item.title.content, self.right_side):
                    projects_meets.append(True)
                else:
                    projects_meets.append(False)
            # check chain of parents
            while item.parent_item:
                if (op_functions[self.op](item.parent_item.title.content, self.right_side) and \
                   item.parent_item.type == 'project'):
                    projects_meets.append(True)
                else:
                    projects_meets.append(False)
                item = item.parent_item

            if self.op == '!=':  # != behaves in other way
                return all(projects_meets)
            else:
                return any(projects_meets)

        elif self.left_side == 'line':
            return op_functions[self.op](item.title.line.strip(), self.right_side.strip())
        elif self.left_side == 'uniqueid':
            return op_functions[self.op](str(item.title._id), self.right_side)
        elif self.left_side == 'content':
            return op_functions[self.op](item.title.content, self.right_side)
        elif self.left_side == 'type':
            return op_functions[self.op](item.type, self.right_side)
        elif self.left_side == 'level':
            return op_functions[self.op](str(item.title.indent_level), self.right_side)
        elif self.left_side == 'parent':
            if item.parent_item:
                return op_functions[self.op](item.parent_item.title.content, self.right_side)
            return False
        elif self.left_side == 'index':
            return op_functions[self.op](str(item.index()), self.right_side)

    def __str__(self):
        return "{0} {2} {1}".format(self.left_side, self.right_side, self.op)


class PlusDescendants(object):
    def __init__(self, predicate):
        self.predicate = predicate

    def test(self, item):
        # if predicate is true for any parent it's also true for self
        while item:
            if self.predicate.test(item):
                return True
            item = item.parent_item
        return False

    def str(self):
        return str(self.predicate) + ' +d'


class WordsPredicate(object):
    """if text contains some text as subtext"""
    def __init__(self, words=None):
        self.words = words.text if words else ''

    def test(self, item):
        return self.words.lower() in item.title.text.lower()

    def __str__(self):
        return self.words

    def __add__(self, other):
        new_word = WordsPredicate()
        new_word.words = (self.words + ' ' + other.words).strip()
        return new_word


class TagPredicate(object):
    def __init__(self, tag):
        self.tag = tag.text

    def test(self, item):
        return item.has_tag(self.tag)

    def __str__(self):
        return self.tag


def parse_predicate(text):
    return ParserF(LexerF(text)).parse()

# filterpredicate
#################################################
# todolist
"""
Module defines main objects of todolist structure:
- TodoList
- Item
- Task
- Project
- Note
- NewLineItem

"""

from cgi import escape


class TodoList(object):
    items_by_id = {}
    _current_id = 0

    @classmethod
    def assign_id(cls, item):
        cls.items_by_id[cls._current_id] = item
        cls._current_id += 1
        return cls._current_id - 1

    @classmethod
    def tag(cls, id_no, tag, param=None):
        cls.items_by_id[id_no].tag(tag, param)

    @classmethod
    def do(cls, id_no):
        cls.items_by_id[id_no].tag(
            'done',
            date.today().isoformat() if date_after_done else None
        )

    @classmethod
    def get_item(cls, id_no):
        return cls.items_by_id[id_no]

    @classmethod
    def get_content(cls, id_no):
        return cls.items_by_id[id_no].get_content()

    @classmethod
    def remove(cls, id_no):
        cls.items_by_id[id_no].remove_self_from_parent()

    def __init__(self, items=None):
        self.items = items if items else []
        self.set_parent_list(self.items)
        self.source = None

    def __str__(self):
        return self.as_plain_text()

    def __nonzero__(self):
        return bool(self.items)

    def __add__(self, other):
        items = self.items

        first_trailing_newline_idx = len(items) - 1
        while first_trailing_newline_idx > 0 and\
              isinstance(items[first_trailing_newline_idx], NewLineItem):
            first_trailing_newline_idx -= 1
        first_trailing_newline_idx += 1

        items = \
            items[0:first_trailing_newline_idx] +\
            other.items + items[first_trailing_newline_idx:]

        return TodoList(
            items
            )

    def copy(self):
        return TodoList(self.copy_of_items())

    def deep_copy(self):
        return TodoList(self.deep_copy_of_items())

    def to_file(self, path):
        text = self.as_plain_text(
            with_ids=False,
            indent=True
        ).code('utf-8')

        with open(path, 'w') as f:
            f.write(text)


    def copy_of_items(self):
        return [item.copy() for item in self.items if item]

    def deep_copy_of_items(self):
        return [item.deep_copy() for item in self.items]

    def remove_item(self, item):
        self.items.remove(item)

    def set_parent_list(self, items):
        for item in items:
            item.parent_list = self

    def add_parent(self, parent):
        for item in self.items:
            item.add_parent(parent)

    def indent(self, level=1):
        for item in self.items:
            item.indent(level)

    def set_indent_level(self, level):
        for item in self.items:
            item.set_indent_level(level)

    def remove_tag(self, tag):
        """removes every occurrence of given tag in list"""
        for item in self.items:
            item.remove_tag(tag)

    def tag_with_parents(self):
        """
        add tag `parents` with `/` separated list of parents
        to every item
        """
        for item in self.items():
            item.tag_with_parents()

    def flatten(self):
        """returns as flat list of items"""
        flattened = []
        for item in self.items:
            flattened += item.flatten()
        return flattened

    def prepend(self, items_list):
        self.set_parent_list(items_list)
        self.items = items_list + self.items

    def append(self, items_list):
        self.set_parent_list(items_list)
        self.items += items_list

    def find_project_id_by_title(self, title):
        """
        returns id of first project of given title in list
        returns None when there is no such item
        """
        filtered = self.filter('content = ' + title + ' and type ="project"')
        for item in filtered.items:
            if item.title.content == title:
                return item.title._id
            else:  # check subtasks recursively
                if item.sub_tasks:
                    q = item.sub_tasks.find_project_id_by_title(title)
                    if q:
                        return q
        return None

    def filter(self, predicate, remove=False):
        """
        returns new list that contains only elements that
        meet predicate.

        Also if `remove` is set to True removes those elements
        from self.
        """
        # parse predicate if it's in string
        if isinstance(predicate, unicode) or isinstance(predicate, str):
            predicate = parse_predicate(predicate)

        filtered_items_with_None = [
            item.filter(predicate, remove) for item in self.items
        ]
        filtered_items = [
            item for item in filtered_items_with_None if item
        ]
        new_list = TodoList(filtered_items)
        return new_list

    def as_plain_text(self, with_ids=False, indent=True):
        items_texts_list = [
            item.as_plain_text(with_ids, indent) for item in self.items
        ]
        return "\n".join(items_texts_list)

    def as_notify(self):
            for item in self.items:
                item.as_notify()

    def as_countdown(self):
        today = date.today().isoformat()
        only_due = self.filter(
            '((@due and not @done) or (@due >=' + today + ')) and not (@waiting > ' + today + ')'
        )
        items_with_None = [
            item.as_countdown() for item in only_due.items
        ]
        items = [
            item for item in items_with_None if item
        ]
        items.sort()
        return '\n'.join(items)

    def as_markdown(self, emphasise_done=False):
        return "\n".join(
            [item.as_markdown(emphasise_done) for item in self.items]
        )

    def as_html(self):
        items_html = "\n".join([item.as_html() for item in self.items])
        return "<ul>" + items_html + "</ul>"

    def as_full_html(self, css_style=None):
        return """
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    {1}
</head>
<body>
<div class="container">
    {0}
</div>
</body>""".format(
    self.as_html(),
    """<link href="{0}" rel="stylesheet" type="text/css" />""".format(
        css_style
    ) if css_style else ''
)
    def pythonista_print(self):
        for item in self.items:
            item.pythonista_print()

class ItemTitle(object):
    def __init__(self, line, line_no, indent_level, typ):
        self.line = line
        self.text = extract_text(typ, line)
        self.content = extract_content(typ, line)
        self.type = typ
        # line, text & content at the moment
        # contain some redundant data

        self._id = TodoList.assign_id(self)
        self.line_no = line_no
        self.indent_level = indent_level

        self.prefix = ''
        self.postfix = ''

    def deep_copy(self):
        new = ItemTitle(
            line=self.line,
            line_no=0,
            indent_level=self.indent_level,
            typ=self.type
        )
        new.prefix = self.prefix
        new.postfix = self.postfix
        return new

    def set_indent_level(self, level):
        self.indent_level = level

    def remove_indent(self):
        self.indent_level = 0

    def indent(self, level=1):
        self.indent_level += level

    def tag(self, tag_text, param=None):
        self.line = add_tag_to_text(self.line, tag_text, param)
        self.text = add_tag_to_text(self.text, tag_text, param)

    def remove_tag(self, tag):
        self.text = remove_tag_from_text(self.text, tag)
        self.line = remove_tag_from_text(self.line, tag)
        self.content = remove_tag_from_text(self.content, tag)

    def has_tag(self, tag):
        return bool(re.search("(^| )" + tag + "($| |\()", self.text))

    def has_tags(self, tags):
        return all(self.has_tag(tag) for tag in tags)

    def has_any_tags(self, tags):
        return any(self.has_tag(tag) for tag in tags)

    def get_tag_param(self, tag):
        tag_search = '(^|(?<=\s))' + tag + r'\(([^)]*)\)'
        match = re.search(tag_search, self.text)
        if match:
            return match.group(2)

    def is_done(self):
        return bool(re.search(done_tag, self.line))

    def pythonista_print(self):
        indent = '\t'*self.indent_level
        print indent + self.text
        set_size(12)
        print indent + '/' + str(self._id)


class Item(object):
    """
    Abstract item on todolist
    """
    def __init__(self, line='', line_no=None, indent_level=None, sub_tasks=None, typ='item'):
        self.title = ItemTitle(line, line_no, indent_level, typ)
        self.parent_item = None  # Project, Task or Note
        self.parent_list = None  # TodoList
        self.type = typ

        self.sub_tasks = sub_tasks
        TodoList.items_by_id[self.title._id] = self

        if self.sub_tasks:
            self.sub_tasks.add_parent(self)

    def __eq__(self, other):
        return self.title == other.title

    def __str__(self):
        return self.as_plain_text()

    def get_content(self):
        return self.title.content

    def copy(self):
        new = self.empty()
        new.title = self.title
        new.parent_item = self.parent_item
        new.parent_list = self.parent_list
        new.sub_tasks = self.sub_tasks.copy() if self.sub_tasks else None
        new.type = self.type
        return new

    def deep_copy(self):
        new = self.empty()
        new.title = self.title.deep_copy()
        new.parent_item = self.parent_item
        new.parent_list = self.parent_list
        new.sub_tasks = self.sub_tasks.deep_copy() if self.sub_tasks else None
        new.type = self.type
        return new

    def index(self):
        return self.parent_list.items.index(self)

    def remove_indent(self):
        self.title.remove_indent()

    def indent(self, level=1):
        self.title.indent(level)
        if self.sub_tasks:
            self.sub_tasks.indent(level)

    def tag(self, tag_text, param=None):
        self.title.tag(tag_text, param)

    def tag_with_parents(self):
        self.tag('parents', self.parents_to_str())

    def remove_tag(self, tag):
        self.title.remove_tag(tag)
        if self.sub_tasks:
            self.sub_tasks.remove_tag(tag)

    def has_tag(self, tag):
        return self.title.has_tag(tag)

    def has_tags(self, tags):
        return self.title.has_tags(tags)

    def has_any_tags(self, tags):
        return self.title.has_any_tags(tags)

    def get_tag_param(self, tag):
        return self.title.get_tag_param(tag)

    def parents_to_str(self):
        parents_contents = []
        item = self
        while item.parent_item:
            parents_contents.append(item.parent_item.title.content)
            item = item.parent_item
        return ' / '.join(parents_contents[::-1])

    def add_parent(self, parent):
        self.parent_item = parent

    def remove_self_from_parent(self):
        self.parent_list.remove_item(self)

    def indent_new_subtasks(self, items):
        try:
            for item in items.items:
                item.set_indent_level(self.title.indent_level + 1)
        except:
            items.set_indent_level(self.title.indent_level + 1)

    def set_indent_level(self, level):
        self.title.indent_level = level
        if self.sub_tasks:
            self.sub_tasks.set_indent_level(level + 1)

    def prepend_subtasks(self, items):
        self.indent_new_subtasks(items)
        if self.sub_tasks:
            self.sub_tasks = items + self.sub_tasks
        else:
            self.sub_tasks = items

    def append_subtasks(self, items):
        self.indent_new_subtasks(items)
        if self.sub_tasks:
            self.sub_tasks = self.sub_tasks + items
        else:
            self.sub_tasks = items

    def flatten(self):
        self.tag_with_parents()
        flattened = []
        if self.type in ('note', 'task'):
            flattened.append(self.copy())
        if self.sub_tasks:
            flattened += self.sub_tasks.flatten()
        return flattened

    def is_type(self, typ):
        return self.type == typ

    def is_done(self):
        return self.title.is_done()

    def filter(self, predicate, remove=False):
        """
        Returns new item (with the same title object)
        if item itself or any of subtasks meets predicate.

        Subtasks of item are also filtered.

        If `remove` is set to True removes items that meet
        predicate from subtasks.
        """
        new = self.copy()
        if self.sub_tasks:
            new.sub_tasks = self.sub_tasks.filter(predicate, remove)
        meets_prediacate = predicate.test(self)
        if remove and new.sub_tasks:
            for item in new.sub_tasks.items:
                if predicate.test(item):
                    self.sub_tasks.items.remove(item)
        if meets_prediacate or new.sub_tasks:
            return new

    def as_notify(self):
            if self.sub_tasks:
                self.sub_tasks.as_notify()
            n(str(self.title.text).replace('@today', '').strip())

    def as_plain_text(self, with_ids=False, indent=True):
        ptext = (u"{indent}{ident}"
                u"{prefix}"
                u"{text}"
                u"{postfix}"
                u"{sub_tasks}").format(
            ident=(
                (unicode(self.title._id) + ' | ') if with_ids else ''
            ),
            indent=(
                ('\t' * self.title.indent_level) if indent else ''
            ),
            text=self.title.text,
            prefix=self.title.prefix,
            postfix=self.title.postfix,
            sub_tasks=(
                ('\n' + self.sub_tasks.as_plain_text(
                    with_ids, indent
                )
                )
                if self.sub_tasks else ''
            ),
        )

        return ptext

    def as_countdown(self):
        if not ' @due(' in self.title.text:
            if self.sub_tasks:
                return self.sub_tasks.as_countdown()

        time_left = date_to_countdown(
            get_tag_param(self.title.line, 'due')
        )

        if time_left:
            text = u"{time_left} {text}{sub_tasks}".format(
                time_left=time_left,
                text=self.title.text,
                sub_tasks=(
                    ('\n' + self.sub_tasks.as_countdown())
                        if self.sub_tasks else ''
                ),
                )
            return text
        else:
            return ''

    def as_html(self):
        css_class_level = min(
            number_of_css_classes,
            self.title.indent_level
        )

        return '<li><span class="{type_class}{done_class}">{text}</span>{sub_tasks}</li>'.format(
            type_class=self.type + str(css_class_level),
            done_class=(
                ' done' if self.is_done() else ''
            ),
            sub_tasks=(
                ('\n' + self.sub_tasks.as_html())
                    if self.sub_tasks else ''
            ),
            text=enclose_tags(
                escape(self.title.text),
                prefix='<span class="tag">',
                postfix='</span>'),
            )

    def markdown_indent_level(self):
        if self.parent_item:
            if self.parent_item.type == 'project':
                return 0
            return self.parent_item.markdown_indent_level() + 1
        else:
            return 0

    def as_markdown(self, emphasise_done):
        indent = self.markdown_indent()
        text = enclose_tags(self.title.text, '**', '**')
        if self.is_done() and emphasise_done:
            text = '*' + text + '*'
        title = indent + text
        sub_tasks = ''
        if self.sub_tasks:
            sub_tasks = '\n' + self.sub_tasks.as_markdown()
        return title + sub_tasks

    def pythonista_print(self):
        if self.has_tag('@done'):
            set_color(cdone)
        elif self.has_tag('@due'):
            set_color(cdue)
        elif self.has_tag('@next'):
            set_color(cnext)
        elif self.has_tag('@today'):
            set_color(ctoday)
        else:
            set_color(ctask)
        self.title.pythonista_print()

        if self.sub_tasks:
            self.sub_tasks.pythonista_print()

class Project(Item):
    def __init__(self, line='', line_no=0, indent_level=0, sub_tasks=None, typ='project'):
        super(Project, self).__init__(line, line_no, indent_level, sub_tasks, typ)
        self.type = 'project'
    def as_notify(self):
            if self.sub_tasks:
                self.sub_tasks.as_notify()


    def markdown_indent_level(self):
        return 0

    def markdown_indent(self):
        return '\n' + '#' * min(self.title.indent_level + 1, 5) + ' '

    def empty(self):
        return Project()

    def pythonista_print(self):
        set_size(18+20/(self.title.indent_level+1.))
        super(Project, self).pythonista_print()


class Task(Item):
    def __init__(self, line='', line_no=0, indent_level=0, sub_tasks=None, typ='task'):
        super(Task, self).__init__(line, line_no, indent_level, sub_tasks, typ)
        self.title.prefix = '- '
        self.type = 'task'


    def markdown_indent(self):
        return '\t' * self.markdown_indent_level() + '- '

    def empty(self):
        return Task()

    def pythonista_print(self):
        set_size(18)
        super(Task, self).pythonista_print()

class Note(Item):
    def __init__(self, line='', line_no=0, indent_level=0, sub_tasks=None, typ='note'):
        super(Note, self).__init__(line, line_no, indent_level, sub_tasks, typ)
        self.type = 'note'

    def markdown_indent(self):
        return '\n' + '\t' * self.markdown_indent_level()

    def empty(self):
        return Note()

    def pythonista_print(self):
            set_size(15)
            super(Note, self).pythonista_print()

class NewLineItem(object):
    def __init__(self):
        self.title = None

    def __getattr__(self, name):
        """
        most functions of NewLineItem returns None and does
        nothing so they don't have to be implemented
        """
        def f(*args, **kwargs):
            pass
        return f

    def as_plain_text(self, *args):
        return ''

    def as_notify(self):
            pass

    def flatten(self, *args, **kwargs):
        return []

    def as_markdown(self, *args):
        return '\n'

    def copy(self):
        return NewLineItem()

    def deep_copy(self):
        return NewLineItem()

    def as_html(self):
        return "<br>"

    def pythonista_print(self):
        print ''

# todolist
#################################################
# todolist_parser
"""
# Parser of todo list.

Top-down parser of grammar that is almost LL(1).
Conflict is resolved by prefering production 7 over 5.

## Grammar:

    1. TodoList -> Item TodoList .
    2. Item     -> Task SubTasks
    3.           | Project SubTasks
    4.           | Note SubTasks
    5.           | indent TodoList dedent
    6.           | NewLineItem
    7. SubTasks -> indent TodoList dedent
    8.           | .

"""


class Parser(object):
    def __init__(self, lexer):
        self.lexer = lexer

    @staticmethod
    def list_from_file(filepath):
        with open(filepath.strip(), 'r') as f:
            tlist = Parser(Lexer([l.decode('utf-8') for l in f.readlines()])).parse()
            tlist.source = filepath
            return tlist

    def parse(self):
        def todolist():
            """parse list"""
            type_on_top = self.lexer.top().type
            new_item = None

            type_to_constructor = {
                'task': Task,
                'project-title': Project,
                'note': Note,
            }

            # depending on type on top of input
            # construct appropriate object
            if type_on_top == 'newline':
                self.lexer.pop()
                new_item = NewLineItem()
            elif type_on_top in type_to_constructor:
                new_item = parse_item(type_to_constructor[type_on_top])
            elif type_on_top == 'indent':  # begining of sublist
                new_item = parse_sublist()
            elif type_on_top in ('dedent', '$'):
                return TodoList()

            return TodoList([new_item]) + todolist()

        def parse_item(constructor):
            """parse Project, Task or Note with its subtasks"""
            lex = self.lexer.pop()
            sub_tasks = None
            type_on_top = self.lexer.top().type
            if type_on_top == 'indent':
                sub_tasks = parse_sublist()
            return constructor(
                lex.text,
                lex.line_no,
                lex.indent_level,
                sub_tasks,
                )

        def parse_sublist():
            """parse part that begins with indent token"""
            self.lexer.pop()
            sublist = todolist()
            type_on_top = self.lexer.top().type
            if type_on_top == 'dedent':  # don't eat $
                self.lexer.pop()
            return sublist

        return todolist()
# todolist_parser
#################################################
# fileslist
"""
module provides functions to store and retrieve paths of
files with todo lists
"""
import os

dir_path = os.path.expanduser(files_list_path)

full_path = dir_path + files_list_name
# create `selection` file if it doesn't exist
try:
    open(full_path, 'r')
except IOError:
    open(full_path, 'w').close()


def change_list(items, change_f):
    # load items from file
    previous = set()
    with open(full_path, 'r') as f:
        text = f.read()
        if text:
            previous = set(text.split('\t'))

    # change items from file using change_f function
    if isinstance(items, str):
        items = set(items.split('\t'))
    new = change_f(previous, items)

    with open(full_path, 'w') as f:
        f.write('\t'.join(new))


def add(items):
    change_list(items, lambda p, i: p.union(i))


def remove(items):
    change_list(items, lambda p, i: p - set(i))


def clear():
    with open(full_path, 'w') as f:
        f.write('')


def to_list():
    with open(full_path, 'r') as f:
        return f.read().split('\t')
# fileslist
#################################################
# main
"""
Main module, provides functions needes to
create TodoList object from plain text files
and operations that use items unique id like
tagging and removing.
"""

abbreviations = quick_query_abbreviations
conjuction = quick_query_abbreviations_conjuction
import os.path
import subprocess


def from_file(path):
    return Parser.list_from_file(path)


def from_files(paths):
    """
    Constructs todolist from many files,
    content of the file is inserted to project that has
    file name as title

    paths - collection of path or tab separated string
    """
    if isinstance(paths, str):
        paths = paths.split('\t')
    items = []
    for path in paths:
        tlist = from_file(path)
        tlist.indent()
        # set file name as project title
        title = os.path.splitext(os.path.basename(path))[0] + ':'
        p = Project(line=title, sub_tasks=tlist)
        p.source = path  # set source to use in `save` function
        items.append(p)
    return TodoList(items)


def do(item_id):
    TodoList.do(item_id)


def tag(item_id, tag, param=None):
    TodoList.tag(item_id, tag, param)


def remove_task(item_id):
    TodoList.remove(item_id)


def get_content(item_id):
    return TodoList.get_content(item_id)


from urllib import urlencode, quote_plus
import clipboard

def tag_dependand_action(item_id):
    item = TodoList.get_item(item_id)
    content = item.get_content()

    if item.has_any_tags(['@search', '@research']):
        action.x_callend('bang-on://?' + urlencode({'q': content}))
    elif item.has_tag('@web'):
        action.x_callend(item.get_tag_param('@web'))
    elif item.has_tag('@mail'):
        clipboard.set(content)
        s = 'mailto:{0}'.format(item.get_tag_param('@osoba').split('<')[1][0:-1])
        action.x_callend(s)

finished = False

class action():
    @staticmethod
    def x_call(s):
        webbrowser.open(s)

    @staticmethod
    def x_callend(s):
        global finished
        action.x_call(s)
        finished=True

    @staticmethod
    def open(s):
        webbrowser.open(s)

def add_new_subtask(item_id, new_item):
    """
    new_item should be item of type Task, Project, Note or
    string, in that case it's assumed that it's task
    """
    if isinstance(new_item, unicode) or isinstance(new_item, str):
        new_item = TodoList([Task('- ' + new_item)])
    TodoList.items_by_id[item_id].append_subtasks(new_item)


def expand_shortcuts(query):
    if query == '':
        return ''
    if query[0] == ' ':  # no abbreviations
        return query.strip()
    else:
        expanded_query = []
        # expand abbreviations till first space
        first_space_idx = query.find(' ')
        if first_space_idx == -1:
            first_space_idx = len(query)

        for i in range(0, first_space_idx):
            expanded_query.append(abbreviations[query[i]])
        expanded_query.append(query[first_space_idx + 1:])
        return conjuction.join(expanded_query)


def archive(tlist, archive_tlist=None):
    """
    moves @done items to first project of title Archive
    assumes that it exsits
    if `archive_tlist` is not specified puts archived items
    to itself
    """
    done = tlist.filter('@done and project != Archive', remove=True)
    done_list = done.deep_copy().flatten()
    if not archive_tlist:
        archive_tlist = tlist
    arch_id = archive_tlist.find_project_id_by_title('Archive')
    TodoList.items_by_id[arch_id].prepend_subtasks(TodoList(done_list))


def move(fro, to):
    to_item = TodoList.items_by_id[to]
    for f in fro:
        item = TodoList.items_by_id[f]
        item.remove_self_from_parent()
        to_item.append_subtasks(TodoList([item]))


def save(tlist):
    """
    Use to save changes to individual files of todolist constructed
    by `from_files` function.

    At the moment it's inefficient - function rewrites every file,
    even if todo list from it wasn't modified. If I notice that
    it has influence on workflow I'll improve this.
    """
    for item in tlist.items:
        if hasattr(item, 'source'):
            with open(item.source.strip(), 'w') as f:
                item.sub_tasks.indent(-1)
                f.write(item.sub_tasks.as_plain_text().encode('utf-8'))

t = None
fq = ''

import clipboard

def dispatch(inp):
    i = inp[0]
    r = inp[1:]
    if i == 'q':
        t.filter(expand_shortcuts(r)).pythonista_print()
    elif  i == 'd':
        do(int(r))
        save(t)
        t.filter(fq).pythonista_print()
    elif i == 'c':
        clipboard.set(get_content(int(r)))
    elif i == 'a':
        tag_dependand_action(int(r))
    elif i == 'm':
        fro, to = r.split('>')
        fro = [f.strip() for f in fro.split(' ')]
        fro = [int(f) for f in fro if f]
        to = int(to.strip())
        move(fro, to)
        save(t)
        t.filter(fq).pythonista_print()
    #elif i == '+':
    #   ide, tas = r.partition(' ')[::2]
    #   print ide, tas
    #   ide = int(ide.strip())
    #   add_new_subtask(ide, tas)
    #   save(t)
    #   t.filter(fq).pythonista_print()
    else:
        print inp + '?'

def q(query=''):
    global t
    global fq
    fq = query
    t = from_files(to_list())
    t.filter(query).pythonista_print()
    inp = raw_input()
    while inp != '':
        dispatch(inp)
        if not finished:
            inp = raw_input()
        else:
            break
    set_color((0.,0.,0.))
    console.set_font()


def qq(query):
    global t
    global fq
    fq = query
    t = from_files(to_list())
    return t.filter(query)

########NEW FILE########
__FILENAME__ = log_to_day_one
#!/usr/bin/python
import topy
import uuid
from datetime import date, timedelta
from config import logging_in_day_one_for_yesterday, day_one_dir_path, day_one_entry_title, day_one_extension


def log_to_day_one(tlist):
    uid = str(uuid.uuid1()).replace('-', '').upper()
    log_date = date.today()
    if logging_in_day_one_for_yesterday:
        log_date -= timedelta(days=1)
    log_data_str = log_date.isoformat()
    print log_data_str

    filtered = tlist.filter('@done = ' + log_data_str)
    filtered.remove_tag('done')
    entry_text = day_one_entry_title + \
        filtered.as_markdown(emphasise_done=False)

    full_text = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Creation Date</key>
    <date>{date}</date>
    <key>Entry Text</key>
    <string>{entry_text}</string>
    <key>Starred</key>
    <false/>
    <key>UUID</key>
    <string>{uid}</string>
</dict>
</plist>
""".format(
    uid=uid,
    entry_text=entry_text,
    date=log_date.strftime('%Y-%m-%dT23:59:59Z')
)
    with open(day_one_dir_path + uid + day_one_extension, 'w') as f:
        f.write(full_text)

if __name__ == '__main__':
    log_to_day_one(topy.from_files(topy.lists.to_list()))

########NEW FILE########
__FILENAME__ = open_html
#!/usr/bin/python

import argparse
import sys
import subprocess
import topy

parser = argparse.ArgumentParser(
    description='Open page with todo list in default browser.')

parser.add_argument(
    '-q', '--query',
    type=str,
    action='store',
    nargs=1,
    default=[''],
    help='predicate to filter with'
)

parser.add_argument(
    '-p', '--paths',
    type=str,
    action='store',
    nargs='*',
    default=topy.lists.to_list(),
    help="paths to files containg todo list, "
         "defaults to paths stored in topy.lists "
         "(see config.py)"
)

parser.add_argument(
    '--css',
    type=str,
    action='store',
    nargs=1,
    default=[None],
    help="css stylesheet, only valid with --html"
    )


args = parser.parse_args()
tlist = topy.from_files(args.paths)
filtered = tlist.filter(args.query[0])
css_style = args.css[0]

def open_html(tlist, css_style=None):
    html = tlist.as_full_html(css_style=css_style)
    with open('html/temp.html', 'w') as f:
        f.write(html)
    subprocess.call('open html/temp.html', shell=True)

open_html(filtered, css_style=css_style)

########NEW FILE########
__FILENAME__ = print_deadlines
#!/usr/bin/python
from config import should_print_path as should_print
import topy

t = topy.from_files(topy.lists.to_list())
s = sorted(
    t.as_countdown(colored=True).split('\n')
    )[0:5]

if int(open(should_print).read()):
    print '\n'.join(s)
else:
    print ''

########NEW FILE########
__FILENAME__ = print_next
#!/usr/bin/python
from config import should_print_path as should_print
import topy

t = topy.from_files(topy.lists.to_list())
next = t.filter('@next and not @done and not @today and not project = onhold')
next.remove_tag('next')
if int(open(should_print).read()):
    print next.as_plain_text(colored=True, indent=False)
else:
    print ''


########NEW FILE########
__FILENAME__ = print_today
#!/usr/bin/python
from config import should_print_path as should_print
import topy

t = topy.from_files(topy.lists.to_list())
today_not_done = t.filter('@today and not @done')
today_not_done.remove_tag('today')
if int(open(should_print).read()):
    print today_not_done.as_plain_text(colored=True, indent=False)
else:
    print ''

########NEW FILE########
__FILENAME__ = qr_to_drafts
import qrcode
import os.path

def_path = '~/Desktop/'
def_filename = 'qr'
path = os.path.expanduser(def_path)

drafts_url = "drafts://x-callback-url/create?text={0}&action=Inbox"


def qr_create(text, filename=def_filename):
    img = qrcode.make(
        drafts_url.format(
            text.replace(' ', '%20')
        )
    )
    if not filename.endswith('.png'):
        filename += '.png'
    img.save(path + filename)


if __name__ == '__main__':
    import sys
    qr_create(' '.join(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = qtopy
from itopy import q
import sys
w = ' '.join(sys.argv[1:])
w = w.strip()
print('\n________________________________________')
print(w)
q(w)

########NEW FILE########
__FILENAME__ = remind
from datetime import datetime
from create_reminder import create_reminder
import topy


def set_reminders(todolist):
    for item in todolist.filter('@remind +d'):
        if item.has_tag('@remind'):
            remind_date_str = item.get_tag_param('@remind')
            remind_date = datetime.strptime(remind_date_str, '%Y-%m-%d %H:%M')
            item.remove_tag('remind')
            create_reminder(
                item.title.text,
                item.sub_tasks.as_plain_text(indent=False) if item.sub_tasks else '',
                remind_date,
            )
            item.tag('willremind', param=remind_date_str)

if __name__ == '__main__':
    all_lists = topy.from_files(topy.lists.to_list())
    set_reminders(all_lists)
    topy.save(all_lists)

########NEW FILE########
__FILENAME__ = reminder_in
#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import sys

from config import inbox_path

reminders = json.loads(sys.argv[1].replace('\n', ' '))

res = []

for reminder in reminders:
    r = "- " + reminder["name"]
    if reminder["completed"]:
        r += " @done(" + reminder["completion_date"] + ')'
    if reminder["priority"] != "0":
        r += " @priority(" + reminder["priority"] + ")"
    if reminder["creation_date"] != "missing value":
        r += " @in(" + reminder["creation_date"] + ")"
    if reminder["due_date"] != "missing value":
        r += " @due(" + reminder["due_date"] + ")"
    if reminder["remind_me_date"] != "missing value":
        r += " @waiting(" + reminder["remind_me_date"] + ")"
    if reminder["body"] != "missing value":
        r += "\n\t" + "".join(reminder["body"].split('\n'))
    res.append(r)

f = open(inbox_path, 'a')
f.write("\n".join(res).encode('utf-8') + "\n")
f.close()

########NEW FILE########
__FILENAME__ = TodoFlow
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sublime_plugin, sublime
from datetime import date, timedelta


settings = sublime.load_settings('TodoFlow.sublime-settings')


append_date_to_done = settings.get("append_date_to_done")
today_tag = settings.get("today_tag")
done_tag = settings.get("done_tag")
next_tag = settings.get("next_tag")
excluded_tags = settings.get("excluded_tags")
allways_included_tags = settings.get("allways_included_tags")
default_date_increase = settings.get("default_date_increase")


def is_task(line):
    return line.strip()[0:2] == '- '

# ( everything but `)` ) or lookahead for \s or end of line
tag_param_regexp = r'(\(([^)]*)\)|(?=(\s|$)))'
# prepend word (sequence without \s and `(`)
tag_regexp_without_at = r'[^\(\s]*' + tag_param_regexp
tag_pattern_without_at = re.compile(tag_regexp_without_at)
tag_pattern = re.compile('(@' + tag_regexp_without_at + ')')

next_tag_pattern = re.compile(r'@' + next_tag + r'(?=(\s|$))')
done_tag_pattern = re.compile(r'@' + done_tag + r'(\(([^)]*)\)|(?=(\s|$)))')
today_tag_pattern = re.compile(r'@' + today_tag + r'(?=(\s|$))')


def is_project(line):
    splitted = line.split(':')
    if len(splitted) < 2:  # no `:` in line
        return False
    if line[-1] == u' ':  # trailing space after `:`
        return False
    if splitted[-1].strip() != '' and splitted[-1].strip()[0] != '@':
        return False
    # only tags are allowed after `:`
    after_colon = splitted[-1].split(u'@')
    only_tags_after_colon = all([
        tag_pattern_without_at.match(tag) for tag in after_colon
    ])
    return only_tags_after_colon


def indent_level(text):
    indent_char = u'\t'
    level = 0
    while level < len(text) and text[level] == indent_char:
        level += 1
    return level


class TaskCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        work_on_file(self, edit)

    def process(self, line):
        if re.search(next_tag_pattern, line):
            line = next_tag_pattern.sub('@' + today_tag, line)
        elif re.search(today_tag_pattern, line):
            line = today_tag_pattern.sub(
                '@' + done_tag +
                ('({0})'.format(date.today().isoformat()) if append_date_to_done else ''),
                line
            )
        elif re.search(done_tag_pattern, line):
            line = done_tag_pattern.sub('', line)
        else:
            if line[-1] != ' ':
                line += ' '
            line += '@' + next_tag
        if line[-1] == ' ':
            line = line[0:-1]
        return line


def convert_to_project_line(line):
    splitted = line.split(' ')
    pre = ''
    post = []
    opened_parenthesis = 0
    for i, s in enumerate(splitted[::-1]):
        # print i, s, opened_parenthesis
        if s[-1] == ')':
            opened_parenthesis += 1
        if s[0] == '@':
            post.append(s)
            if '(' in s:
                opened_parenthesis -= 1
        else:
            if opened_parenthesis == 0:
                if i == 0:
                    pre = line
                else:
                    pre = ' '.join(splitted[0:-(i)])
                break
    # print post
    return (pre + ': ' + ' '.join(post)).rstrip()



class NewTaskCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        work_on_file(self, edit)

    def process(self, line):
        level = indent_level(line)
        if is_project(line):
            level += 1
        return line + '\n' + '\t' * level + '- '


class ChangeTypeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        work_on_file(self, edit)

    def process(self, line):
        level = indent_level(line)
        if is_task(line):  # change to project
            print 'task'
            line = '\t' * level + line.strip()[2:]

            # insert `:` before trailing tags
            line = convert_to_project_line(line)

        elif is_project(line):  # change to note
            print 'project'
            splitted = [s for s in line.split(':') if s.strip()]
            line = ':'.join(splitted[0:-1]) + splitted[-1]
            print 'project new:'

        else:  # change to task
            print 'note'
            return '\t' * level + '- ' + line.strip()

        if line[-1] == ' ':
            line = line[0:-1]
        return line


def is_banned_tag(tag):
    for b in [t + '(' for t in excluded_tags]:
        if tag.startswith(b):
            return True
    for b in [t in excluded_tags]:
        if b == tag:
            return True


class AddTagCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.edit = edit
        text = self.view.substr(sublime.Region(0, self.view.size()))
        # find all tags in text
        ## find tags with parameters
        self.tags_list = re.findall(' @[^\(\s]*\([^)]*\)', text)
        ## find tags without parameters
        self.tags_list += re.findall(' @[^\(\s]*\s', text)
        ## strip tags
        self.tags_list = [tag[2:].strip() for tag in self.tags_list]
        ## exlude excluded tags
        self.tags_list = [tag for tag in self.tags_list if not is_banned_tag(tag)]
        ## add versions of tags without parameter
        self.tags_list += [tag[0:tag.find('(')] for tag in self.tags_list if '(' in tag]
        ## add allways included tags
        self.tags_list += allways_included_tags
        ## remove duplicates
        self.tags_list = list(set(self.tags_list))
        # show tags
        self.view.window().show_quick_panel(self.tags_list, self.on_selection)

    def on_selection(self, selection):
        work_on_file(self, self.edit, selection)

    def process(self, line, selection):
        if selection == -1:
            return line
        if line[-1] != ' ':
            line += ' '
        return line + '@' + self.tags_list[selection]


def work_on_file(self, edit, *args):
    # process every line in selection
    # and replace it with result
    for region in self.view.sel():
        line_region = self.view.line(region)
        line = self.view.substr(line_region)
        lines = line.split('\n')
        processed_line = '\n'.join([self.process(each_line, *args) for each_line in lines])
        if processed_line != line:
            self.view.replace(edit, line_region, processed_line)


class IncreaseDateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        change_date(self.view, edit, change=1)


def change_date(view, edit, change=1):
    # change date by `change` value,
    # what is changed (year, month, day)
    # depends on cursor position
    for region in view.sel():
        old_date, date_region, what_selected = find_date(view, region)
        if what_selected == 'nothing':
            new_date = date.today()
        elif what_selected == 'day':
            new_date = old_date + timedelta(days=change)
        elif what_selected == 'month':
            month = old_date.month + change
            if month == 0:
                month = 12
            if month == 13:
                month = 1
            new_date = date(old_date.year, month, old_date.day)
        elif what_selected == 'year':
            new_date = date(old_date.year + change, old_date.month, old_date.day)
        new_date_str = '(' + new_date.isoformat() + ')'
        view.replace(edit, date_region, new_date_str)
        view.sel().subtract(date_region)
        view.sel().add(region)


def find_date(view, region):
    max_iter = 20
    citer = 0
    start = region.begin()

    if (region.end() - region.begin()) == 0:
        x = view.substr(sublime.Region(region.begin(), region.end() + 1))
        if len(x) > 0 and x[-1] == '(':
            print x
            region = sublime.Region(region.begin() + 1, region.end() + 3)
            print view.substr(region)
        else:
            region = sublime.Region(region.begin() - 1, region.end())
    while view.substr(region)[-1] != ')' and view.substr(region)[-1] != '\n':
        citer += 1
        if citer > max_iter:
            break
        region = sublime.Region(region.begin(), region.end() + 1)
    while view.substr(region)[0] != '(' and view.substr(region)[0] != '\n':
        citer += 1
        if citer > max_iter:
            break
        region = sublime.Region(region.begin() - 1, region.end())
    date_str = view.substr(region).strip()

    # what was selcted depends on cursor position in date
    # `|` shows possible cursor positions
    what = default_date_increase     # |(2013-12-31)
    if start > region.begin():       # (|2|0|1|3|-12-31)
        what = 'year'
    if start > region.begin() + 5:   # (2013-|1|2|-31)
        what = 'month'
    if start > region.begin() + 8:   # (2013-12-|3|1|)
        what = 'day'
    if start > region.begin() + 11:  # (2013-12-31)|
        what = default_date_increase
    try:
        ddate = calc_date(date_str)
        return ddate, region, what
    except Exception as e:
        # calc_date fails when date was not selected,
        # so insert new one
        print e
        return date.today(), sublime.Region(start, start), 'nothing'


def calc_date(date_str):
    date_str = date_str[1:-1]
    return date(*(int(x) for x in date_str.split('-')))


class DecreaseDateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        change_date(self.view, edit, change=-1)

########NEW FILE########
__FILENAME__ = switch_should_print
"""change 1 to 0, and 0 to 1"""

from config import should_print_path as should_print

current = int(open(should_print).read())
with open(should_print, 'w') as f:
    f.write(
        str(current ^ 1)
        )

########NEW FILE########
__FILENAME__ = tabs_as_tasks
import subprocess

command = 'cat /Users/bvsc/Dropbox/TODO/scripts/frontSafariTabs.applescript | osascript'
titles_and_urls_raw = subprocess.check_output(command, shell=True)
titles_and_urls = titles_and_urls_raw.split(', ')
task_template = '- {0} @web({1})'

for i in range(0, len(titles_and_urls), 2):
    print task_template.format(
        titles_and_urls[i].strip(),
        titles_and_urls[i + 1].strip()
    )

########NEW FILE########
__FILENAME__ = todify
import notification
from itopy import qq
t = qq('@today and not @done').as_notify()

########NEW FILE########
__FILENAME__ = tvcal
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path += ['/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/']

from config import tvcal_url, inbox_path, tvseries_project_title
from icalendar import Calendar
from urllib2 import urlopen
from datetime import datetime, timedelta
import re
today = datetime.now()
tommorow = today + timedelta(hours=24)


inbox_text = open(inbox_path).read().decode('utf-8')

cal = Calendar.from_ical(urlopen(tvcal_url).read())

season_x_episode_pattern = re.compile('(\d+)x(\d+)')


def s00e00(x00x00):
    return 's{0}e{1}'.format(
        x00x00.group(1).zfill(2),
        x00x00.group(2).zfill(2)
        )


def fix_summary(summary):
    splitted = summary.split(' - ')
    series_title = splitted[0]
    episode_title = splitted[1]
    if 'adventure time' in series_title.lower():
        series_title = re.sub(season_x_episode_pattern, '', series_title)
    else:
        series_title = re.sub(season_x_episode_pattern, s00e00, series_title)
        episode_title = ''

    return (series_title + episode_title).strip()

def tvcal(inbox_file):
    to_inbox = [tvseries_project_title]
    for component in cal.walk():
        if 'summary' in component:
            summary = component['summary']
            dt = component['DTSTART'].dt
            fixed_summary = fix_summary(summary)
            if today <= dt <= tommorow and not fixed_summary in inbox_text:
                to_inbox.append(
                    '\t- ' + fixed_summary + \
                    ' @at(' + str(dt) + ') @tvseries'
                    )
    if len(to_inbox) > 1:
        inbox_file.write('\n' + '\n'.join(to_inbox) + '\n')

if __name__ == '__main__':
    with open(inbox_path, 'a') as inbox_file:
        tvcal(inbox_file)

########NEW FILE########
__FILENAME__ = update_lists
#!/usr/bin/python
from datetime import date, timedelta
import re
from topy import from_file, archive
from config import days_of_the_week, projects_path, onhold_path, inbox_path, daily_project_title, remove_waiting_from_onhold

projects = from_file(projects_path)
onhold = from_file(onhold_path)

def update_daily(projects):
    daily = projects.filter('project = ' + daily_project_title)
    daily.remove_tag('done')
    daily.add_tag('today')


def update_weekly(onhold, inbox):
    today = days_of_the_week[date.today().weekday()]
    waiting = onhold.filter('@weekly = ' + today + ' +d')
    inbox.write('\n' + waiting.as_plain_text().encode('utf-8') + '\n')


def update_waiting(onhold, inbox):
    today = date.today().isoformat()
    waiting = onhold.filter('@waiting <= ' + today + ' +d', remove=remove_waiting_from_onhold)
    inbox.write('\n' + waiting.as_plain_text().encode('utf-8') + '\n')



def update_followups(tasks):
    today = date.today()
    with open(onhold_path, 'a') as f:
        followups = tasks.filter('@followup and @done <= ' + date.today().isoformat())
        for item in followups:
            folowee = item.get_tag_param('@followup')
            if not folowee:
                continue
            days_no_str, folowee_task = folowee.partition(' ')[::2]
            days_no = int(days_no_str)
            when_to_follow = today + timedelta(days=days_no)
            following_param = item.title.get_text_without_tags()
            f.write(
                '- ' + folowee_task + ' @waiting(' + when_to_follow.isoformat() + ') @following(' + following_param + ')\n'
            )


if __name__ == '__main__':
    update_daily(projects)
    with open(inbox_path, 'a') as inbox:
        update_weekly(onhold, inbox)
        update_waiting(onhold, inbox)
        projects.to_file(projects_path)

########NEW FILE########
__FILENAME__ = utopy
#!/usr/bin/python
import itopy as topy
from seamless_dropbox import open
import uuid
from datetime import date, timedelta
import os.path
# import sys
# sys.path += ['/Users/bvsc/Dropbox/TODO/scripts/topy/']

###################### Paths ######################

inbox_path = '/Users/bvsc/Dropbox/TODO/Inbox.todo'
projects_path = '/Users/bvsc/Dropbox/TODO/Projects.todo'
onhold_path = '/Users/bvsc/Dropbox/TODO/Onhold.todo'

###################################################


###################################################

################## log to day one #################

logging_in_day_one_for_yesterday = True

# change if you store Day One entries somewhere else
day_one_dir_path = os.path.expanduser(
    '~/Dropbox/Apps/Day One/Journal.dayone/entries/'
)

# title of entry
day_one_entry_title = '# Things I did today #\n\n\n'

day_one_extension = '.doentry'

###################################################

################## update lists ###################

# you can translate it to other language or something
# preserve order
days_of_the_week = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
)

# title of projects that contains tasks that
# shoul be do every day
daily_project_title = 'Daily'

# shoul remove waiting tasks that were moved to
# projects.todo form onhold.todo?
remove_waiting_from_onhold = False

###################################################





def log_to_day_one(tlist):
    uid = str(uuid.uuid1()).replace('-', '').upper()
    log_date = date.today()
    if logging_in_day_one_for_yesterday:
        log_date -= timedelta(days=1)
    log_data_str = log_date.isoformat()
    print log_data_str

    filtered = tlist.filter(u'@done = ' + log_data_str)
    filtered.remove_tag('done')
    entry_text = day_one_entry_title + \
        filtered.as_markdown(emphasise_done=False)

    full_text = u"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Creation Date</key>
    <date>{date}</date>
    <key>Entry Text</key>
    <string>{entry_text}</string>
    <key>Starred</key>
    <false/>
    <key>UUID</key>
    <string>{uid}</string>
</dict>
</plist>
""".format(
    uid=uid,
    entry_text=entry_text,
    date=log_date.strftime('%Y-%m-%dT23:59:59Z')
)
    with open(day_one_dir_path + uid + day_one_extension, 'w') as f:
        f.write(full_text.encode('utf-8'))


def update_daily(projects):
    daily = projects.filter('project = ' + daily_project_title)
    daily.remove_tag('done')


def update_weekly(onhold, inbox):
    today = days_of_the_week[date.today().weekday()]
    waiting = onhold.filter('@weekly = ' + today + ' +d')
    inbox.write('\n' + waiting.as_plain_text().encode('utf-8'))


def update_waiting(onhold, inbox):
    today = date.today().isoformat()
    waiting = onhold.filter('@waiting <= ' + today + ' +d', remove=remove_waiting_from_onhold)
    print waiting.as_plain_text()
    inbox.write('\n' + waiting.as_plain_text().encode('utf-8'))



all_lists = topy.from_files(topy.to_list())
inbox_file = open(inbox_path, 'a')
# archive_list = topy.from_file(archive_path)
onhold_list = topy.from_file(onhold_path)
print onhold_list.as_plain_text()
log_to_day_one(all_lists.deep_copy())
update_weekly(onhold_list, inbox_file)
update_waiting(onhold_list, inbox_file)
inbox_file.close()

update_daily(all_lists)
# archive(all_lists, archive_list)

# archive_list.to_file(archive_path)
topy.save(all_lists)
print 'done'

########NEW FILE########
__FILENAME__ = config
#
# Configuration of todoflow
#

###################### Paths ######################
# File that stores path to your todo lists
files_list_path = '/Users/bvsc/Dropbox/Notes/__todo/'
files_list_name = 'lists'


inbox_path = '/Users/bvsc/Dropbox/Notes/__todo/_inbox.txt'
projects_path = '/Users/bvsc/Dropbox/Notes/__todo/Projects.taskpaper'
onhold_path = '/Users/bvsc/Dropbox/Notes/__todo/Onhold.taskpaper'
archive_path = '/Users/bvsc/Dropbox/Notes/__todo/NOTES/Archive.taskpaper'

##################### Queries #####################

should_expand_dates = True
should_expand_shortcuts = True

# logical operator to join shortened queries
quick_query_abbreviations_conjuction = ' and '  # ' or '

# fill with your own, this is what I use:
quick_query_abbreviations = {
    't': '@working',
    'n': '@next',
    'd': 'not @done',
    'u': '@due and not (project ? Onhold)',
    's': '@studia+d',
    'a': '((@working or @next) and not @done)+d',
}

# add date value when tagging with @done
date_after_done = True

# char that is before last ':' in project title that indicates that given project is sequential
# only first not @done task in sequential projects is returned in searches
sequential_projects_sufix = ':'

################## HTML printer ##################

# when generating html items are given classes
# define how many different classes (depengin on identation level)
# you want to have
number_of_css_classes = 4

path_to_css = '/Users/bvsc/Dropbox/Projects/todoflow/workflows/html/css/light.css'

tag_to_class = {
    'working': 'green',
    'next': 'blue',
    'due': 'orange',
    'done': 'done',
    'blocked': 'gray',
    'waiting': 'gray',
}

###################### Alfred ######################

# symbols on icons can be transparent or white
white_symbols_on_icons = False  # True

################## log to day one #################

logging_in_day_one_for_yesterday = True

# change if you store Day One entries somewhere else
day_one_dir_path = '/Users/bvsc/Dropbox/apps/day one/Journal.dayone/entries/'

# title of entry
day_one_entry_title = '# Things I did yesterday #\n\n\n'

day_one_extension = '.doentry'

################## update lists ###################

# you can translate it to other language or something
# preserve order
days_of_the_week = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
)

# title of projects that contains tasks that
# shoul be do every day
daily_project_title = '"Daily:"'

###################### Inbox ######################

inbox_tag_to_path = {
    '@music': '/Users/bvsc/Dropbox/Notes/__todo/music.txt',
    '@film': '/Users/bvsc/Dropbox/Notes/__todo/filmy.txt',
    '@book': '/Users/bvsc/Dropbox/Notes/__todo/books.txt',
    '@app': '/Users/bvsc/Dropbox/Notes/__todo/apps.txt',
    '@game': '/Users/bvsc/Dropbox/Notes/__todo/games.txt',
    '@toy': '/Users/bvsc/Dropbox/Notes/__todo/toys and tools.txt',
    '@tool': '/Users/bvsc/Dropbox/Notes/__todo/toys and tools.txt',
    '@food': '/Users/bvsc/Dropbox/Notes/__todo/food and drinks.txt',
    '@idea': '/Users/bvsc/Dropbox/Notes/__todo/ideas.txt',
}

#################### Editorial ####################

path_to_folder_synced_in_editorial = '/Users/bvsc/Dropbox/Notes/'

###################### tvcal ######################

# http://www.pogdesign.co.uk/cat/
tvcal_url = 'http://www.pogdesign.co.uk/cat/generate_ics/bbec20975e1a472a3b76d4b0670fe733'
tvseries_project_title = 'TV Series:'


########NEW FILE########
__FILENAME__ = colorprinter
from todoflow.src.utils import enclose_tags
from todoflow.config import sequential_projects_sufix

class color:
    """defines colors used in output"""
    defc         = '\033[0m'

    red          = '\033[1;31m'
    green        = '\033[1;32m'
    gray         = '\033[1;30m'
    blue         = '\033[1;34m'

    yellow       = '\033[1;33m'
    magenta      = '\033[1;35m'
    cyan         = '\033[1;36m'
    white        = '\033[1;37m'
    crimson      = '\033[1;38m'

    high_red     = '\033[1;41m'
    high_green   = '\033[1;42m'
    high_brown   = '\033[1;43m'
    high_blue    = '\033[1;44m'
    high_magenta = '\033[1;45m'
    high_cyan    = '\033[1;46m'
    high_gray    = '\033[1;47m'
    high_crimson = '\033[1;48m'


class ColorPrinter(object):
    def __init__(self):
        self.seq_counter = [(0, 0)]
        self.prev_tag = color.green
        self.post_tag = color.defc

    def pformat(self, tlist):
        result = []
        for item in tlist:
            if item.type == 'project':
                result.append(color.blue + self.project(item) + color.defc)
            elif item.type == 'seq-project':
                result.append(color.magenta + self.sproject(item) + color.defc)
            elif item.type == 'task':
                result.append(self.task(item))
            elif item.type == 'note':
                result.append(self.note(item))
            elif item.type == 'newline':
                result.append('')
        return '\n'.join(result).encode('utf-8').strip() + '\n'

    def pprint(self, tlist):
        print(self.pformat(tlist))

    def project(self, item):
        return '\t' * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag) + ':'

    def sproject(self, item):
        return '\t' * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag) + sequential_projects_sufix + ':'

    def task(self, item):
        return '\t' * item.indent_level + color.blue + '- ' + color.defc + enclose_tags(item.text, self.prev_tag, self.post_tag)

    def note(self, item):
        return color.yellow + '\t' * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag) + color.defc

########NEW FILE########
__FILENAME__ = dayoneprinter
from todoflow.src.utils import enclose_tags
from todoflow.src.utils import remove_tag
from .plainprinter import PlainPrinter

class DayonePrinter(PlainPrinter):
    def __init__(self):
        self.prev_tag = '**'
        self.post_tag = '**'

    def pformat(self, tlist):
        result = []
        for item in tlist:
            item.text = remove_tag(item.text, 'done')
            if item.type == 'project':
                result.append(self.project(item))
            if item.type == 'seq-project':
                result.append(self.project(item))
            elif item.type == 'task':
                result.append(self.task(item))
            elif item.type == 'note':
                result.append(self.note(item))
            else:
                result.append('')
        return '\n'.join(result).encode('utf-8').strip() + '\n'

    def pprint(self, tlist):
        print(self.pformat(tlist))

    def project(self, item):
        idx = 0
        text = item.text
        while text[idx] == '#':
            idx += 1
        text = text[idx:]
        return '\n' + '#' * (item.indent_level + 1) + ' ' + enclose_tags(text, self.prev_tag, self.post_tag) + ':'

    def task(self, item):
        return '\t' * (item.indent_level - 2) + '- ' + enclose_tags(item.text, self.prev_tag, self.post_tag)

    def note(self, item):
        return '*' + enclose_tags(item.text, self.prev_tag, self.post_tag) + '*'

########NEW FILE########
__FILENAME__ = editorialprinter
from .htmlprinter import HTMLPrinter

from todoflow.config import path_to_folder_synced_in_editorial

class EditorialPrinter(HTMLPrinter):
    def postprocess_item(self, item, text):
        if item.source:
            file_url = item.source.replace(path_to_folder_synced_in_editorial, '')
            return u'<a href="editorial://open/{0}?root=dropbox&command=goto&input={2}:{3}">{1}</a>'.format(
            	file_url, 
            	text, 
            	item.first_char_no,
            	item.first_char_no + \
            		len(item.text) + \
            		item.indent_level + \
            		(1 if item.type == 'task' else 0) + \
            		(-1 if item.type == 'note' else 0),
        	)
        else:
            return text
########NEW FILE########
__FILENAME__ = htmllinkedprinter
from .htmlprinter import HTMLPrinter

class HTMLLinkedPrinter(HTMLPrinter):
    def postprocess_item(self, item, text):
        if item.source:
            return u'<a href="file://{0}">{1}</a>'.format(item.source, text)
        else:
            return text
########NEW FILE########
__FILENAME__ = htmlprinter
#coding: utf-8

from cgi import escape
from todoflow.config import tag_to_class
from todoflow.src.utils import enclose_tags

template = u"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>todoflow</title>

    {1}

</head>

<body>

<ul>
{0}
</ul>

</body>
</html>
"""

class HTMLPrinter(object):
    def __init__(self, csspath='', included_css=False):
        self.csspath = csspath
        self.included_css = included_css

    def pprint(self, tlist):
        print(self.pformat(tlist))

    def pformat(self, tlist):
        result = []
        for item in tlist.items:
            result.append(self.pformat_item(item))
        joind = u'\n'.join(result)
        t = template.format(
            joind,
            self.cssify(),
        ).encode('utf-8')
        return t

    def pformat_item(self, item):
        title = self.titlize(item)
        sublist = [title]
        prefix = '<ul>'
        sufix = '</ul>'
        if item.type == 'seq-project':
            prefix = '<ol>'
            sufix = '</ol>'
        if item.sublist:
            sublist.append(prefix)
            for subitem in item.sublist.items:
                sublist.append(self.pformat_item(subitem))
            sublist.append(sufix + '</a>')
        text = '\n'.join(sublist)
        return self.postprocess_item(item, text)

    def postprocess_item(self, item, text):
        return text

    def titlize(self, item):
        text = self.preprocess_title(item)
        if item.type == 'project':
            return self.projecify(item, text)
        elif item.type == 'seq-project':
            return self.sprojecify(item, text)
        elif item.type == 'task':
            return self.taskify(item, text)
        elif item.type == 'newline':
            return self.newlineify(item, text)
        elif item.type == 'note':
            return self.noteify(item, text)
        return ''

    def preprocess_title(self, item):
        return enclose_tags(escape(item.text), '<span class="tag">', '</span>')

    def get_extra_classes(self, item):
        extra_classes = []
        for tag in tag_to_class:
            if item.has_tag(tag):
                extra_classes.append(tag_to_class[tag])
        return extra_classes

    def projecify(self, item, text):
        extra_classes = self.get_extra_classes(item)
        return u'<li class="project project-{lvl} {extra_classes}">{text}</li>'.format(
            text=text,
            lvl=item.indent_level + 1,
            extra_classes=' '.join(extra_classes)
        )

    def sprojecify(self, item, text):
        extra_classes = self.get_extra_classes(item)
        return u'<li class="project project-{lvl} {extra_classes}">{text}</li>'.format(
            text=text,
            lvl=item.indent_level + 1,
            extra_classes=' '.join(extra_classes)
        )

    def taskify(self, item, text):
        extra_classes = self.get_extra_classes(item)
        return u'<li class="task task-{lvl} {extra_classes}">{text}</li>'.format(
            text=text,
            lvl=item.indent_level + 1,
            extra_classes=' '.join(extra_classes)
        )

    def newlineify(self, item, text):
        return u'<li class="newline">&nbsp;</li>'

    def noteify(self, item, text):
        extra_classes = self.get_extra_classes(item)
        return u'<li class="note note-{lvl} {extra_classes}">{text}</li>'.format(
            text=text,
            lvl=item.indent_level + 1,
            extra_classes=' '.join(extra_classes)
        )

    def cssify(self):
        if self.included_css:
            return u'<style>{0}</style>'.format(self.included_css).encode('utf-8')
        elif self.csspath:
            return u'<style>{0}</style>'.format(open(self.csspath).read().encode('utf-8'))
        else:
            return u'<link rel="style.css" href="{0}" type="text/css" />'.format(self.csspath)

########NEW FILE########
__FILENAME__ = plainprinter
from todoflow.src.utils import enclose_tags
from todoflow.config import sequential_projects_sufix

class PlainPrinter(object):
    def __init__(self, indent_char='\t'):
        self.indent_char = indent_char
        self.prev_tag = ''
        self.post_tag = ''

    def pformat(self, tlist):
        result = []
        for item in tlist:
            if item.type == 'project':
                result.append(self.project(item))
            elif item.type == 'seq-project':
                result.append(self.sproject(item))
            elif item.type == 'task':
                result.append(self.task(item))
            elif item.type == 'note':
                result.append(self.note(item))
            else:
                result.append('')
        try:
            return '\n'.join(result).encode('utf-8').strip() + '\n'
        except TypeError:
            return '\n'.join(result).strip() + '\n'


    def pprint(self, tlist):
        print(self.pformat(tlist))

    def project(self, item):
        return self.indent_char * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag) + ':'

    def sproject(self, item):
        return self.indent_char * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag) + sequential_projects_sufix + ':'

    def task(self, item):
        return self.indent_char * item.indent_level + u'- ' + enclose_tags(item.text, self.prev_tag, self.post_tag)

    def note(self, item):
        return self.indent_char * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag)

########NEW FILE########
__FILENAME__ = plainprinter3
from todoflow.src.utils import enclose_tags

class PlainPrinter3(object):
    def __init__(self, indent_char='\t'):
        # self.seq_counter = [(0, 0)]
        self.indent_char = indent_char
        self.prev_tag = ''
        self.post_tag = ''

    def pformat(self, tlist):
        result = []
        for item in tlist:
            if item.type == 'project':
                result.append(self.project(item))
            elif item.type == 'task':
                result.append(self.task(item))
            elif item.type == 'note':
                result.append(self.note(item))
            else:
                result.append('')

        return '\n'.join(result).strip() + '\n'

    def pprint(self, tlist):
        print(self.pformat(tlist))

    def project(self, item):
        return self.indent_char * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag) + ':'

    def task(self, item):
        return self.indent_char * item.indent_level + u'- ' + enclose_tags(item.text, self.prev_tag, self.post_tag)

    def note(self, item):
        return self.indent_char * item.indent_level + enclose_tags(item.text, self.prev_tag, self.post_tag)

########NEW FILE########
__FILENAME__ = pythonistaprinter
import console
from .plainprinter import PlainPrinter

indent = ' '

class PythonistaPrinter(PlainPrinter):
	def __init__(self):
		super(PythonistaPrinter, self).__init__()

	def pprint(self, tlist):
		for item in tlist:
			if item.type == 'project' or item.type == 'seq-printer':
				self.project(item)
			elif item.type == 'note':
				self.note(item)
			elif item.type == 'task':
				self.ttask(item)
			elif item.type == 'newline':
				self.newline(item)

	def project(self, item):
		console.set_color(0.00, 0.00, 0.00)
		print(indent * item.indent_level + item.text + ':')
		console.set_color()

	def note(self, item):
		print(indent * item.indent_level + item.text)

	def ttask(self, item):
		self.task(item)
		print(indent * item.indent_level + '- ' + item.text)
		console.set_color()

	def task(self, item):
		if item.has_tag('working'):
			console.set_color(0.00, 0.50, 0.50)
		elif item.has_any_tags(['done', 'blocked']):
			console.set_color(0.50, 0.50, 0.50)
		elif item.has_tag('next'):
			console.set_color(0.00, 0.50, 1.00)
		elif item.has_tag('due'):
			console.set_color(1.00, 0.00, 0.50)

	def newline(self, item):
		print('\n')


########NEW FILE########
__FILENAME__ = xmlprinter
"""
Module provides simple class to create
Alfred 2 feedback XML.

It's really simple structure so there is no need
to use any advanced xml tools.
"""

from cgi import escape
from uuid import uuid1
from todoflow.config import white_symbols_on_icons

from .plainprinter import PlainPrinter


class AlfredItemsList(object):
    def __init__(self, items=None):
        self.items = items or []
        self.pattern = \
            '<item arg="{arg}" uid="{uid}" valid="{valid}">"' +\
            '<title>{title}</title>' +\
            '<subtitle>{subtitle}</subtitle>' +\
            '<icon>icons/{icon}{w}.png</icon>'.format(
                icon='{icon}',
                w='w' if white_symbols_on_icons else '',
            ) +\
            '</item>'

    def append(
            self,
            arg,
            title,
            subtitle,
            valid='yes',
            icon='iconT',
            uid=None
        ):
        """
        Adds item to list, left uid of every item
        to None to preserve order in list when it's
        displayed in Alfred.
        """
        # using uuid is little hacky but there is no other way to
        # prevent alfred from reordering items than to ensure that
        # uid never repeats
        uid = uid or str(uuid1())
        self.items.append(
            (arg, escape(title), escape(subtitle), valid, icon, uid)
        )

    def __str__(self):
        items = "".join(
            [self.pattern.format(
                arg=arg.encode('utf-8'),
                title=escape(title.encode('utf-8')),
                subtitle=escape(subtitle.encode('utf-8')),
                valid=valid,
                icon=icon,
                uid=uid
                ) for arg, title, subtitle, valid, icon, uid in self.items
            ]
        )
        return '<items>' + items + '</items>'

    def __add__(self, other):
        return AlfredItemsList(self.items + other.items)


class XMLPrinter(PlainPrinter):
    def __init__(self):
        super(XMLPrinter, self).__init__()

    def pformat(self, tlist, *args):
        al = AlfredItemsList()
        additional_arg = ';'.join(args)
        for item in tlist:
            if item.type == 'project' or item.type == 'seq-project':
                self.seq_counter = [(0, 0)]
            elif item.type in ('task', 'note'):
                al.append(
                    arg=str(item._id) + (';' + additional_arg if additional_arg else ''),
                    title=self.titlize(item),
                    subtitle=item.parents_to_str(),
                    icon=self.iconize(item)
                )
            else:
                pass
        return str(al)

    def pprint(self, tlist, *args):
        print(self.pformat(tlist, *args))

    def titlize(self, item):
        if item.type == 'note':
            return item.text
        elif item.type == 'task':
            return item.text

    def iconize(self, item):
        if item.type == 'note':
            return 'note'
        return 'task'

########NEW FILE########
__FILENAME__ = fileslist
"""
module provides functions to store and retrieve paths of
files with todo lists
"""

# from alfredlist import AlfredItemsList
import os
from todoflow.config import files_list_path, files_list_name

full_path = files_list_path + files_list_name

def change_list(items, change_f):
    # load items from file
    previous = set()
    with open(full_path, 'r') as f:
        text = f.read()
        if text:
            previous = set(text.split('\n'))

    # change items from file using change_f function
    if isinstance(items, str):
        items = set(items.split('\n'))
    new = change_f(previous, items)

    with open(full_path, 'w') as f:
        f.write('\n'.join(new))


def add(items):
    change_list(items, lambda p, i: p.union(i))


def remove(items):
    change_list(items, lambda p, i: p - set(i))


def clear():
    with open(full_path, 'w') as f:
        f.write('')


def to_list():
    try:
        f = open(full_path, 'r', encoding='utf-8', errors='ignore')
    except TypeError:
        f = open(full_path, 'r')
    result = [l for l in f.read().split('\n') if l]
    f.close()
    return result

########NEW FILE########
__FILENAME__ = item
import re

from .todolist import TodoList
from .title import ItemTitle
from todoflow.config import sequential_projects_sufix

class Item(object):
    """
    Abstract item on todo list
    """
    def __init__(self, text='', indent_level=None, sublist=None, typ='item', line_no=0, first_char_no=0):
        self.title = ItemTitle(text, indent_level, typ)
        self.parent_item = None
        self.parent_list = None
        self.type = typ
        self.line_no = line_no
        self.first_char_no = first_char_no
        self.sublist = sublist if sublist else TodoList()
        TodoList.items_by_id[self.title._id] = self

        self.sublist.add_parent(self)

        self._iter_returned_self = False
        self._iter_subtasks_idx = 0
        self.source = ''

    def __eq__(self, other):
        return self.title == other.title

    def __str__(self):
        return '\t' * self.indent_level + self.text

    def get_line(self):
        return self.title.text

    def copy(self):
        new = self.empty()
        new.title = self.title
        new.parent_item = self.parent_item
        new.parent_list = self.parent_list
        new.sublist = self.sublist.copy()
        new.type = self.type
        new.source = self.source
        new.line_no = self.line_no
        new.first_char_no = self.first_char_no
        return new

    def deep_copy(self):
        new = self.empty()
        new.title = self.title.deep_copy()
        new.parent_item = self.parent_item
        new.parent_list = self.parent_list
        new.sublist = self.sublist.deep_copy()
        new.type = self.type
        new.source = self.source
        new.line_no = self.line_no
        new.first_char_no = self.first_char_no
        return new

    def index(self):
        return self.parent_list.items.index(self)

    def indent(self, level=1):
        self.title.indent(level)
        self.sublist.indent(level)

    def tag_with_parents(self):
        self.tag('parents', self.parents_to_str())

    def remove_tag(self, tag):
        self.title.remove_tag(tag)
        self.sublist.remove_tag(tag)

    def is_nth_with_tag(self, number, tag):
        if not self.has_tag(tag) or self.has_tag('@done'):
            return False
        self_number = self.parent_list.tags_counters.get(tag, 0)
        self.parent_list.tags_counters[tag] = self_number + 1
        if number == self_number:
            return True
        else:
            return False

    def parents_to_str(self):
        parents_contents = []
        item = self
        while item.parent_item:
            parents_contents.append(item.parent_item.title.text)
            item = item.parent_item
        return ' / '.join(parents_contents[::-1])

    def get_root(self):
        item = self
        while item.parent_item:
            item = item.parent_item
        return item

    def set_source(self, path):
        self.source = path
        self.sublist.set_source(path)

    def add_parent(self, parent):
        self.parent_item = parent

    def remove_self_from_parent(self):
        self.parent_list.remove_item(self)

    def indent_new_subtasks(self, items):
        for item in items.items:
            item.title.set_indent_level(self.title.indent_level + 1)

    def set_indent_level(self, level):
        self.title.indent_level = level
        self.sublist.set_indent_level(level + 1)

    def prepend_subtasks(self, items):
        self.indent_new_subtasks(items)
        self.sublist = items + self.sublist

    def append_subtasks(self, items):
        self.indent_new_subtasks(items)
        self.sublist = self.sublist + items

    def is_type(self, typ):
        return self.type == typ

    def __getattr__(self, atr):
        return self.title.__getattribute__(atr)

    def filter(self, predicate):
        """
        Returns new item (with the same title object)
        if item itself or any of subtasks meets predicate.

        Subtasks of item are also filtered.
        """
        new = self.copy()
        new.sublist = self.sublist.filter(predicate)
        meets_prediacate = predicate.test(self)
        if meets_prediacate or new.sublist.items:
            return new

    def search(self, predicate):
        result = [self] if predicate.test(self) else []
        for item in self.sublist.items:
            result += (item.search(predicate))
        return result


class Project(Item):
    def __init__(self, text='', indent_level=0, sublist=None, typ='project', line_no=0, first_char_no=0):
        text = text[:-1].strip()
        super(Project, self).__init__(text, indent_level, sublist, typ, line_no, first_char_no)
        self.type = typ

    def empty(self):
        return Project()

    def __str__(self):
        return (
            '\t' * self.indent_level + self.text + ':'
        )


class SeqProject(Item):
    def __init__(self, text='', indent_level=0, sublist=None, typ='seq-project', line_no=0, first_char_no=0):
        text = text[:-(1 + len(sequential_projects_sufix))].strip()
        super(SeqProject, self).__init__(text, indent_level, sublist, typ, line_no, first_char_no)
        self.type = typ

    def empty(self):
        return SeqProject()

    def __str__(self):
        return (
            '\t' * self.indent_level + self.text + sequential_projects_sufix + ':'
        )

    def filter(self, predicate):
        """
        Returns new item (with the same title object)
        if item itself or any of subtasks meets predicate.

        Subtasks of item are also filtered.
        """
        new = self.copy()
        subitem = None
        for item in self.sublist:
        	if item.has_tag('done'):
        		continue
        	subitem = item
        	break
        if subitem and predicate.test(subitem):
        	sublist = TodoList([subitem])
        	new.sublist = sublist
        else:
        	sublist = TodoList()
        	new.sublist = sublist
        meets_prediacate = predicate.test(self)
        if meets_prediacate or new.sublist.items:
            return new

task_prefix = re.compile(r'^\s*- ')


class Task(Item):
    def __init__(self, text='', indent_level=0, sublist=None, typ='task', line_no=0, first_char_no=0):
        text = task_prefix.sub('', text).strip()
        super(Task, self).__init__(text, indent_level, sublist, typ, line_no, first_char_no)
        self.type = typ

    def __str__(self):
        return (
            '\t' * self.indent_level + '- ' + self.text
        )

    def empty(self):
        return Task()


class Note(Item):
    def __init__(self, text='', indent_level=0, sublist=None, typ='note', line_no=0, first_char_no=0):
        text = text.strip()
        super(Note, self).__init__(text, indent_level, sublist, typ, line_no, first_char_no)
        self.type = typ

    def empty(self):
        return Note()


class NewLineItem(Item):
    def __init__(self, text='', indent_level=0, sublist=None, typ='newline', line_no=0, first_char_no=0):
        text = ''
        super(NewLineItem, self).__init__(text, indent_level, sublist, typ, line_no, first_char_no)

    def copy(self):
        return NewLineItem()

    def deep_copy(self):
        return NewLineItem()

########NEW FILE########
__FILENAME__ = lexer
"""
# Lexer of todo lists.

Token stores its type in string, posible types are:

* $ - end of input
* indent - indentation
* newline - `\n`
* dedent - end of indented text
* task - line tht begins with `\t*- `
* project-title - line that is not task and ends with `:`
(with eventual trailing tags after `:`)
* note - line that is not task or project-title

"""
import re
from todoflow.config import sequential_projects_sufix


class Token(object):
    @staticmethod
    def is_task(line):
        return line.strip()[0:2] == '- '

    tag_pattern_without_at = re.compile(r'[^\(\s]*(|\([^)]*\))')
    # defines what can be *after @*
    # Tag -> @ Word | @ Word ( Words ) .
    #
    # first part of regexp defines Word -
    # ensures that there is no white signs and `(` in it
    #
    # second part of regexp defines epsilon | ( Words ) -
    # nothing or `(` everything but `)` followed by `)`
    #

    @staticmethod
    def is_project(line):
        return line.endswith(':')

    @staticmethod
    def is_seq_project(line):
        return line.endswith(sequential_projects_sufix + ':')

    def __init__(self, line=None, indent_level=0, line_no=0, first_char_no=0):
        self.line_no = line_no
        self.first_char_no = first_char_no
        self.indent_level = indent_level
        if line:
            self.text = line

            if Token.is_task(line):
                self.type = 'task'
            elif Token.is_seq_project(line):
                self.type = 'seq-project-title'
            elif Token.is_project(line):
                self.type = 'project-title'
            else:
                self.type = 'note'
        else:  # if there's no line it's end of input
            self.type = 'newline'
            self.text = '\n'


class Dedent(Token):
    def __init__(self):
        self.type = 'dedent'
        self.text = ''
        self.line_no = -1
        self.first_char_no = -1


class Indent(Token):
    def __init__(self):
        self.type = 'indent'
        self.text = ''
        self.line_no = -1
        self.first_char_no = -1


class NewLine(Token):
    def __init__(self, line_no=0, first_char_no=0):
        self.first_char_no = first_char_no
        self.type = 'newline'
        self.text = '\n'
        self.line_no = line_no
        self.indent_level = 0


class EndToken(Token):
    def __init__(self):
        self.type = '$'
        self.text = '' 
        self.line_no = -1
        self.first_char_no = -1
        

class Lexer(object):
    def __init__(self, lines):
        self.tokens = Lexer.tokenize(lines)

    @staticmethod
    def lexer_from_file(filepath):
        with open(filepath, 'r') as f:
            return Lexer([l.decode('utf-8') for l in f.readlines()])

    @staticmethod
    def indent_level(text):
        indent_char = '\t'
        level = 0
        while level < len(text) and text[level] == indent_char:
            level += 1
        return level

    @staticmethod
    def tokenize(lines):
        """turns input into tokens"""
        tokens = []
        indent_levels = [0]
        first_char_no = 0
        line_no = 0
        for line in lines:
            line_no += 1 # count from 1, not from 0
            if line == '\n':
                tokens.append(NewLine(line_no, first_char_no))
                # empty lines are ignored in
                # flow of indents so
                first_char_no += 1
                continue

            # generate indent and dedent tokens
            current_level = Lexer.indent_level(line)
            if current_level > indent_levels[-1]:
                indent_levels.append(current_level)
                tokens.append(Indent())
            elif current_level < indent_levels[-1]:
                while current_level < indent_levels[-1]:
                    indent_levels.pop()
                    tokens.append(Dedent())

            tokens.append(Token(line.rstrip(), current_level, line_no, first_char_no))
            first_char_no += len(line)
        tokens.append(EndToken())
        # add $ token at the end and return
        return tokens[::-1]

    def top(self):
        """returns token on top of stack"""
        return self.tokens[-1]

    def pop(self):
        """removes token from top of stack and returns it"""
        return self.tokens.pop()

    def consume(self, expected_type):
        """removes token from top of stack
        and raises ParseError if it's not of expected type"""
        if self.tokens.pop().type != expected_type:
            raise ParseError


class ParseError(Exception):
    pass

########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-

"""
Main module, provides functions needes to
create TodoList object from plain text files
and operations that use items unique id like
tagging and removing.
"""

import os.path
import re
import subprocess
from datetime import datetime
from . import fileslist as lists
from .todolist import TodoList
from .item import Task, Project, NewLineItem
from .parser import Parser
from todoflow.config import quick_query_abbreviations as abbreviations
from todoflow.config import quick_query_abbreviations_conjuction as conjuction
from todoflow.config import files_list_path, should_expand_dates, should_expand_shortcuts
from todoflow.printers import PlainPrinter



def all_lists():
    return from_files(lists.to_list())


def from_file(path):
    return Parser.list_from_file(path.strip())


def from_files(paths):
    """
    Constructs todolist from many files,
    content of the file is inserted to project that has
    file name as title

    paths - collection of path or tab separated string
    """
    if isinstance(paths, str):
        paths = paths.split('\t')
    items = []
    for path in paths:
        path = path.rstrip()
        tlist = TodoList([NewLineItem()]) + from_file(path)
        tlist.indent()
        # set file name as project title
        title = os.path.splitext(os.path.basename(path))[0] + ':'
        p = Project(text=title, sublist=tlist)
        p.source = path  # set source to use in `save` function
        p.set_source(path)
        items.append(p)
    return TodoList(items)


def from_text(text):
    return Parser.list_from_text(text)


def do(item_id):
    TodoList.do(item_id)


def tag(item_id, tag, param=None):
    TodoList.tag(item_id, tag, param)


def remove(item_id):
    TodoList.remove(item_id)


def get_item(item_id):
    return TodoList.items_by_id[item_id]


def edit(item_id, new_content):
    TodoList.edit(item_id, new_content.decode('utf-8'))


def get_text(item_id):
    return TodoList.get_text(item_id)


def append_subtasks(item_id, new_item):
    """
    new_item should be item of type Task, Project, Note or
    string, in that case it's assumed that it's task
    """
    if isinstance(new_item, unicode) or isinstance(new_item, str):
        new_item = TodoList([Task(new_item)])
    TodoList.items_by_id[item_id].append_subtasks(new_item)

add_new_subtask = append_subtasks


def prepend_subtasks(item_id, new_item):
    """
    new_item should be item of type Task, Project, Note or
    string, in that case it's assumed that it's task
    """
    is_unicode = False
    try:
        is_unicode = isinstance(new_item, unicode)
    except NameError:
        pass

    if is_unicode or isinstance(new_item, str):
        new_item = TodoList([Task(new_item)])
    TodoList.items_by_id[item_id].prepend_subtasks(new_item)


def expand_shortcuts(query):
    if not should_expand_shortcuts:
        return query
    if query == '':
        return ''
    if query[0] == ' ':  # no abbreviations
        return query.strip()
    else:
        expanded_query = []
        # expand abbreviations till first space
        first_space_idx = query.find(' ')
        if first_space_idx == -1:
            first_space_idx = len(query)

        for i in range(0, first_space_idx):
            if not query[i] in abbreviations:
                return query.strip()
            expanded_query.append(abbreviations[query[i]])
        reminder = query[first_space_idx + 1:].strip()
        if reminder:
            expanded_query.append(reminder)
        return conjuction.join(expanded_query)


def expand_dates(query):
    if not should_expand_dates:
        return query
    pdt = None
    try:
        import parsedatetime as pdt
    except ImportError:
        pass
    if pdt:
        c = pdt.Constants()
        c.BirthdayEpoch = 80
        p = pdt.Calendar(c)
        def f(t):
            return datetime(*p.parse(query)[0][:6]).isoformat()
        return re.sub(r'\{[^}]*\}', f, query)
    else:
        return query


def expand_query(query):
    return expand_dates(expand_shortcuts(query))


def save(tlist):
    """
    Use to save changes to individual files of todolist constructed
    by `from_files` function.

    At the moment it's inefficient - function rewrites every file,
    even if todo list from it wasn't modified. If I notice that
    it has influence on workflow I'll improve this.
    """
    for item in tlist.items:
        if hasattr(item, 'source'):
            try:
                f = open(item.source.strip(), 'w', encoding='utf-8', errors='ignore')
            except TypeError:
                f = open(item.source.strip(), 'w')
            item.sublist.dedent()
            text = PlainPrinter().pformat(item.sublist)
            f.write(text)
            f.close()

def editorial_save(tlist):
    """
    **This will fail horribly if used outside Editorial**
    It's not really save, only preparation to it.
    To use only in Editorial.app, it's workaround [this bug](http://omz-forums.appspot.com/editorial/post/5925732018552832)
    that doesn't allow to use simple call to editor.set_files_contents, instead it's required to use Set File Contents block.

    It's annoying.
    """
    import workflow
    import pickle
    paths = []
    path_to_content = {}
    for item in tlist.items: 
        if hasattr(item, 'source'):
            item.sublist.dedent()
            text = PlainPrinter().pformat(item.sublist)
            path = item.source.replace(path_to_folder_synced_in_editorial, '')
            paths.append(path)
            path_to_content[path] = text.decode('utf-8')
    with real_open('content-temp.pickle', 'w') as f:
        pickle.dump(path_to_content, f)
    workflow.set_output('\n'.join(paths))
########NEW FILE########
__FILENAME__ = parser
"""
# Parser of todo list.

Top-down parser of grammar that is almost LL(1).
Conflict is resolved by prefering production 7 over 5.

## Grammar:

    1. TodoList -> Item TodoList .
    2. Item     -> Task SubTasks
    3.           | Project SubTasks
    4.           | SeqProject SubTasks
    5.           | Note SubTasks
    6.           | indent TodoList dedent
    7.           | NewLineItem
    8. SubTasks -> indent TodoList dedent
    9.           | .

"""

from .lexer import Lexer
from .todolist import TodoList
from .item import NewLineItem, Task, Project, Note, SeqProject

class Parser(object):
    def __init__(self, lexer):
        self.lexer = lexer

    @staticmethod
    def list_from_file(filepath):
        try:
            f = open(filepath, 'r', encoding='utf-8', errors='ignore')
        except TypeError:
            f = open(filepath, 'r')
        lines = f.readlines()
        f.close()
        try:
            tlist = Parser(Lexer([l.decode('utf-8') for l in lines])).parse()
        except:
            tlist = Parser(Lexer([l for l in lines])).parse()
        tlist.source = filepath
        return tlist

    @staticmethod
    def list_from_text(text):
        tlist = Parser(Lexer([l.decode('utf-8') for l in text.split('\n')])).parse()
        return tlist

    def parse(self):
        def todolist(newlines_prefix = None):
            """parse list"""
            if not newlines_prefix:
                newlines_prefix = []
            type_on_top = self.lexer.top().type
            new_item = None

            type_to_constructor = {
                'task': Task,
                'seq-project-title': SeqProject,
                'project-title': Project,
                'note': Note,
            }

            # depending on type on top of input
            # construct appropriate object
            newlines = []
            while type_on_top == 'newline':
                nl_lex = self.lexer.pop()
                newlines.append(NewLineItem(nl_lex.line_no, nl_lex.first_char_no))
                type_on_top = self.lexer.top().type
            if type_on_top in type_to_constructor:
                new_item = parse_item(type_to_constructor[type_on_top])
            elif type_on_top == 'indent':  # begining of sublist
                self.lexer.pop()
                new_item = parse_sublist(newlines)
                newlines = []
            elif type_on_top in ('dedent', '$'):
                return TodoList(newlines_prefix + newlines)
            if isinstance(new_item, TodoList):
                return TodoList(newlines_prefix + newlines) + new_item  # + todolist() 
            return TodoList(newlines_prefix + newlines + [new_item]) + todolist()

        def parse_item(constructor):
            """parse Project, Task or Note with its subtasks"""
            lex = self.lexer.pop()
            sublist = None
            type_on_top = self.lexer.top().type
            newlines = []
            while type_on_top == 'newline':
                nl_lex = self.lexer.pop()
                newlines.append(NewLineItem(nl_lex.line_no, nl_lex.first_char_no))
                type_on_top = self.lexer.top().type
            sublist = TodoList(newlines)
            if type_on_top == 'indent':
                self.lexer.pop()
                sublist += parse_sublist()
            return constructor(
                text=lex.text,
                indent_level=lex.indent_level,
                sublist=sublist,
                line_no=lex.line_no,
                first_char_no=lex.first_char_no,
            )

        def parse_sublist(newlines_prefix=None):
            """parse part that begins with indent token"""
            sublist = todolist(newlines_prefix)
            type_on_top = self.lexer.top().type
            if type_on_top == 'dedent':  # don't eat $
                self.lexer.pop()
            return sublist

        return todolist()

########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-

import re

"""
Predicates for filtering todo list.
Module defines lexer, parser and predicates themselfs.

Predicate implements method test(text) that returns if
predicate applies to given text.

For example '@today and not @done' returns if text contains
tag @today and not contains tag @done.

grammar of predicates (SLR(1)):

S     -> E1 | E1 +d
E1    -> E1 and E2
       | E2.
E2    -> E2 or E3
       | E3.
E3    -> not E3
       | E4
       | ( E1 ).
E4    -> Argument op Words
       | Words
       | Tag .
Words -> word Words
       | .

those rules are not part of SLR automaton:
op     -> = | != | < | <= | >= | > | matches | contains | ? . (? is abbreviation for contains)
Tag    -> @ word | EndTag.
EndTag -> (Words) | epsilon.
Argument -> project | line | uniqueid | content | type | level | parent | index | Tag.



Arguments:
- project - check project title
- line - line with whole `-`, and tags
- uniqueid - id of element
- content - line without formatting and trailing tags
- type - "project", task or note
- level - indentation level
- parent - checks parents recursively
- index - index in sublist, starts with 0
- tag parameter - value enclosed in parenthesises after tag
"""


class Token(object):
    operators = ['=', '!=', '<', '<=', '>', '>=', '?', 'matches', 'contains']
    log_ops = ['and', 'or', 'not']
    keywords = ['project', 'line', 'uniqueid', 'content', 'type', 'level', 'parent', 'index']
    tag_prefix = '@'

    def __init__(self, text=None):
        # long switch-case / if:elif chain
        self.text = text
        # set type of token
        if not text:
            self.type = '?'
        elif text in Token.operators:
            self.type = 'op'
        elif text == '+d':
            self.type = 'plusD'
        elif text in Token.log_ops:
            self.type = text
        elif text in Token.keywords:
            self.type = 'arg'
        elif text[0] == Token.tag_prefix:
            self.type = 'tag'
        elif text[0] == '"':
            self.type = 'word'
            self.text = text[1:-1]
        elif text == '(':
            self.type = 'lparen'
        elif text == ')':
            self.type = 'rparen'
        else:
            self.type = 'word'

    def __str__(self):
        return repr(self.text) + ' : ' + self.type


class Lexer(object):
    def __init__(self, input_text):
        self.input_text = input_text
        self.tokens = Lexer.tokenize(input_text)

    @staticmethod
    def tokenize(input_text):
        """converts input text to list of tokens"""
        tokens = []

        def add_token(text=None):
            if text != '' and text != ' ':
                tokens.append(Token(text))

        idx = 0
        collected = ''
        text_length = len(input_text)

        while idx < text_length + 1:
            # lengthy switch-case like statement
            # that processes input text depending on
            # current char
            if idx == text_length:
                # finish tokenizing
                add_token(collected)  # add remaining collected text
                add_token()  # add end of input token
            elif input_text[idx] == '+':
                if idx + 1 < len(input_text):
                    if input_text[idx + 1] == 'd':
                        add_token(collected)
                        collected = ''
                        add_token('+d')
                        idx += 1
            elif input_text[idx] == ' ':
                # spaces separate but but don't have semantic meaning
                add_token(collected)
                collected = ''
            elif input_text[idx] in ('(', ')'):
                # parenthesises seperate
                add_token(collected)
                collected = ''
                add_token(input_text[idx])
            elif input_text[idx] in ('<', '>', '!'):
                # operators or prefixes of operators
                add_token(collected)
                collected = input_text[idx]
            elif input_text[idx] == '=':
                if collected in ('<', '>', '!'):
                    # "="" preceded by any of this signs is an operator
                    collected += '='
                    add_token(collected)
                else:
                    # "=" by itself is also an operator
                    add_token(collected)
                    add_token('=')
                collected = ''
            elif input_text[idx] == '?':
                add_token(collected)
                add_token('?')
                collected = ''
            elif input_text[idx] == '"':
                # quoted part of input is allways a word
                add_token(collected)
                collected = ''
                next_quotation_mark_idx = input_text.find('"', idx + 1)
                if next_quotation_mark_idx == -1:
                    # when there is no matching quotation mark
                    # end of the input is assumed
                    add_token(input_text[idx:] + '"')
                    idx = text_length - 1  # sets idx to that value so loop finishes in next iteration
                else:
                    add_token(input_text[idx:next_quotation_mark_idx + 1])
                    idx = next_quotation_mark_idx

            else:
                if collected in ('<', '>'):
                    add_token(collected)
                    collected = ''
                collected += input_text[idx]
            idx += 1

        return tokens[::-1]

    def pop(self):
        """pops and returns topmost token"""
        try:
            return self.tokens.pop()
        except IndexError:
            print(' '.join([t.type for t in self.tokens]))
            print(self.input_text)
            raise ParsingError

    def top(self):
        """returns topmost token"""
        try:
            return self.tokens[-1]
        except IndexError:
            print(' '.join([t.type for t in self.tokens]))
            print(self.input_text)
            raise ParsingError


class ParsingError(Exception):
    pass


class Parser(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.create_parsing_table()
        self.stack = [0]

    def goto(self, state):
        self.parsing_table[self.stack[-2]][state]()

    def create_parsing_table(self):
        # long functions with declaration of parsing table and parser actions

        def shift_gen(state_no):
            def shift():
                """puts lexem and state number on stack"""
                self.stack.append(self.lexer.pop())
                self.stack.append(state_no)
            return shift

        def goto_gen(state_no):
            def goto():
                """puts state number on stack"""
                self.stack.append(state_no)
            return goto

        def err():
            print(self.lexer.input_text)
            raise ParsingError

        def acc():
            """returns abstrac syntax tree"""
            self.stack.pop()
            return self.stack[-1]

        # reductions, name of the functions contains information about production
        # -> is changed to __, terminals and nonterminals are separated by _
        # left side of production is preceded by `r`

        def rS__E1():
            self.stack.pop()
            self.goto('S')

        def rS__E1_plusD():
            self.stack.pop()
            self.stack.pop()  # +d

            self.stack.pop()
            e1 = self.stack.pop()
            self.stack.append(PlusDescendants(e1))
            self.goto('S')

        def rE3__E4():
            self.stack.pop()
            self.goto('E3')

        def rE1__E2():
            self.stack.pop()
            self.goto('E1')

        def rE2__E3():
            self.stack.pop()
            self.goto('E2')

        def rE3__lparen_E1_rparen():
            self.stack.pop()  # )
            self.stack.pop()

            self.stack.pop()
            e1 = self.stack.pop()

            self.stack.pop()  # (
            self.stack.pop()

            self.stack.append(e1)
            self.goto('E3')

        def rE2__E2_or_E3():
            self.stack.pop()
            e3 = self.stack.pop()

            self.stack.pop()  # or
            self.stack.pop()

            self.stack.pop()
            e2 = self.stack.pop()

            self.stack.append(OrPredicate(e2, e3))
            self.goto('E2')

        def rE4__Words():
            self.stack.pop()
            self.goto('E4')

        def rE1__E1_and_E2():
            self.stack.pop()
            e2 = self.stack.pop()

            self.stack.pop()  # and
            self.stack.pop()

            self.stack.pop()
            e1 = self.stack.pop()

            self.stack.append(AndPredicate(e1, e2))
            self.goto('E1')

        def rE3__not_E3():
            self.stack.pop()
            e3 = self.stack.pop()

            self.stack.pop()  # not
            self.stack.pop()

            self.stack.append(NotPredicate(e3))
            self.goto('E3')

        def rWords__epsilon():
            self.stack.append(WordsPredicate())
            self.goto('Words')

        def rE4__tag_op_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            op = self.stack.pop()

            self.stack.pop()
            arg = self.stack.pop()

            self.stack.append(ArgOpPredicate(arg, words, op))
            self.goto('E4')

        def rE4__arg_op_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            op = self.stack.pop()

            self.stack.pop()
            arg = self.stack.pop()

            self.stack.append(ArgOpPredicate(arg, words, op))
            self.goto('E4')

        def rWords__word_Words():
            self.stack.pop()
            words = self.stack.pop()

            self.stack.pop()
            word = self.stack.pop()

            self.stack.append(WordsPredicate(word) + words)
            self.goto('Words')

        def rE4__tag():
            self.stack.pop()
            tag = self.stack.pop()

            self.stack.append(TagPredicate(tag))
            self.goto('E4')

        # generated code
        self.parsing_table = {
            0: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": goto_gen(6),
                "E2": goto_gen(5),
                "E3": goto_gen(4),
                "E1": goto_gen(3),
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            1: {
                "?": rE4__Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__Words,
                "lparen": err,
                "not": err,
                "or": rE4__Words,
                "and": rE4__Words,
                "plusD": rE4__Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            2: {
                "?": rE3__E4,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__E4,
                "lparen": err,
                "not": err,
                "or": rE3__E4,
                "and": rE3__E4,
                "plusD": rE3__E4,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            3: {
                "?": rS__E1,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": shift_gen(19),
                "plusD": shift_gen(18),
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            4: {
                "?": rE2__E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE2__E3,
                "lparen": err,
                "not": err,
                "or": rE2__E3,
                "and": rE2__E3,
                "plusD": rE2__E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            5: {
                "?": rE1__E2,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE1__E2,
                "lparen": err,
                "not": err,
                "or": shift_gen(17),
                "and": rE1__E2,
                "plusD": rE1__E2,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            6: {
                "?": acc,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            7: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": goto_gen(16),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            8: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": goto_gen(5),
                "E3": goto_gen(4),
                "E1": goto_gen(15),
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            9: {
                "?": err,
                "word": err,
                "tag": err,
                "op": shift_gen(14),
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            10: {
                "?": rE4__tag,
                "word": err,
                "tag": err,
                "op": shift_gen(13),
                "arg": err,
                "rparen": rE4__tag,
                "lparen": err,
                "not": err,
                "or": rE4__tag,
                "and": rE4__tag,
                "plusD": rE4__tag,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            11: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(12),
            },
            12: {
                "?": rWords__word_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__word_Words,
                "lparen": err,
                "not": err,
                "or": rWords__word_Words,
                "and": rWords__word_Words,
                "plusD": rWords__word_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            13: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(24),
            },
            14: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rWords__epsilon,
                "lparen": err,
                "not": err,
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": goto_gen(23),
            },
            15: {
                "?": err,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": shift_gen(22),
                "lparen": err,
                "not": err,
                "or": err,
                "and": shift_gen(19),
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            16: {
                "?": rE3__not_E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__not_E3,
                "lparen": err,
                "not": err,
                "or": rE3__not_E3,
                "and": rE3__not_E3,
                "plusD": rE3__not_E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            17: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": err,
                "E3": goto_gen(21),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            18: {
                "?": rS__E1_plusD,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": err,
                "lparen": err,
                "not": err,
                "or": err,
                "and": err,
                "plusD": err,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            19: {
                "?": rWords__epsilon,
                "word": shift_gen(11),
                "tag": shift_gen(10),
                "op": err,
                "arg": shift_gen(9),
                "rparen": rWords__epsilon,
                "lparen": shift_gen(8),
                "not": shift_gen(7),
                "or": rWords__epsilon,
                "and": rWords__epsilon,
                "plusD": rWords__epsilon,
                "S": err,
                "E2": goto_gen(20),
                "E3": goto_gen(4),
                "E1": err,
                "E4": goto_gen(2),
                "Words": goto_gen(1),
            },
            20: {
                "?": rE1__E1_and_E2,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE1__E1_and_E2,
                "lparen": err,
                "not": err,
                "or": shift_gen(17),
                "and": rE1__E1_and_E2,
                "plusD": rE1__E1_and_E2,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            21: {
                "?": rE2__E2_or_E3,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE2__E2_or_E3,
                "lparen": err,
                "not": err,
                "or": rE2__E2_or_E3,
                "and": rE2__E2_or_E3,
                "plusD": rE2__E2_or_E3,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            22: {
                "?": rE3__lparen_E1_rparen,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE3__lparen_E1_rparen,
                "lparen": err,
                "not": err,
                "or": rE3__lparen_E1_rparen,
                "and": rE3__lparen_E1_rparen,
                "plusD": rE3__lparen_E1_rparen,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            23: {
                "?": rE4__arg_op_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__arg_op_Words,
                "lparen": err,
                "not": err,
                "or": rE4__arg_op_Words,
                "and": rE4__arg_op_Words,
                "plusD": rE4__arg_op_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
            24: {
                "?": rE4__tag_op_Words,
                "word": err,
                "tag": err,
                "op": err,
                "arg": err,
                "rparen": rE4__tag_op_Words,
                "lparen": err,
                "not": err,
                "or": rE4__tag_op_Words,
                "and": rE4__tag_op_Words,
                "plusD": rE4__tag_op_Words,
                "S": err,
                "E2": err,
                "E3": err,
                "E1": err,
                "E4": err,
                "Words": err,
            },
        }

    def parse(self):
        """returns parsed predicate, throws ParsingError"""
        lex = self.lexer.top()
        state = self.stack[-1]
        parsed = self.parsing_table[state][lex.type]()
        if parsed:
            return parsed
        else:
            return self.parse()


class OrPredicate(object):
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side

    def test(self, item):
        return self.left_side.test(item) or self.right_side.test(item)

    def __str__(self):
        return "{0} or {1}".format(self.left_side, self.right_side)


class AndPredicate(object):
    def __init__(self, left_side, right_side):
        self.left_side = left_side
        self.right_side = right_side

    def test(self, item):
        return self.left_side.test(item) and self.right_side.test(item)

    def __str__(self):
        return "{0} and {1}".format(self.left_side, self.right_side)


class NotPredicate(object):
    def __init__(self, negated):
        self.negated = negated

    def test(self, item):
        return not self.negated.test(item)

    def __str__(self):
        return "not {0}".format(self.negated)

# all operation are case insensitive
op_functions = {
    '=': lambda x, y: x.lower() == y.lower(),
    '!=': lambda x, y: x.lower() != y.lower(),
    '<': lambda x, y: x.lower() < y.lower(),
    '<=': lambda x, y: x.lower() <= y.lower(),
    '>=': lambda x, y: x.lower() >= y.lower(),
    '>': lambda x, y: x.lower() > y.lower(),
    '?': lambda x, y: y.lower() in x.lower(),
    'matches': lambda x, y: bool(re.match(y, x))
}

op_functions['contains'] = op_functions['?']


class ArgOpPredicate(object):
    def __init__(self, left_side, right_side, op):
        self.left_side = left_side.text
        self.right_side = right_side.words
        self.op = op.text

    def test(self, item):
        # long switch-case / if:elif chain
        # runs different tests depending on self.left_side
        if self.left_side[0] == '@':
            tag_search = '(^|(?<=\s))' + self.left_side + r'\(([^)]*)\)'
            match = re.search(tag_search, item.title.text)
            if match:
                left_side = match.group(2)
            else:
                return False
            r = op_functions[self.op](left_side, self.right_side)
            return r

        elif self.left_side == 'project':
            projects_meets = []
            # if item itself is a project it must be considered
            if item.type == 'project' or item.type == 'seq-project':
                if op_functions[self.op](item.title.text, self.right_side):
                    projects_meets.append(True)
                else:
                    projects_meets.append(False)
            # check chain of parents
            while item.parent_item:
                if (op_functions[self.op](item.parent_item.title.text, self.right_side) and \
                   item.parent_item.type == 'project'):
                    projects_meets.append(True)
                else:
                    projects_meets.append(False)
                item = item.parent_item

            if self.op == '!=':  # != behaves in other way
                return all(projects_meets)
            else:
                return any(projects_meets)

        elif self.left_side == 'line':
            return op_functions[self.op](item.title.line.strip(), self.right_side.strip())
        elif self.left_side == 'uniqueid':
            return op_functions[self.op](str(item.title._id), self.right_side)
        elif self.left_side == 'content':
            return op_functions[self.op](item.title.text, self.right_side)
        elif self.left_side == 'type':
            return op_functions[self.op](item.type, self.right_side)
        elif self.left_side == 'level':
            return op_functions[self.op](str(item.title.indent_level), self.right_side)
        elif self.left_side == 'parent':
            if item.parent_item:
                return op_functions[self.op](item.parent_item.title.text, self.right_side)
            return False
        elif self.left_side == 'index':
            return op_functions[self.op](str(item.index()), self.right_side)

    def __str__(self):
        return "{0} {2} {1}".format(self.left_side, self.right_side, self.op)


class PlusDescendants(object):
    def __init__(self, predicate):
        self.predicate = predicate

    def test(self, item):
        # if predicate is true for any parent it's also true for self
        while item:
            if self.predicate.test(item):
                return True
            item = item.parent_item
        return False

    def str(self):
        return str(self.predicate) + ' +d'


class WordsPredicate(object):
    """if text contains some text as subtext"""
    def __init__(self, words=None):
        self.words = words.text if words else ''

    def test(self, item):
        return self.words.lower() in item.title.text.lower()

    def __str__(self):
        return self.words

    def __add__(self, other):
        new_word = WordsPredicate()
        new_word.words = (self.words + ' ' + other.words).strip()
        return new_word


class TagPredicate(object):
    def __init__(self, tag):
        self.tag = tag.text

    def test(self, item):
        return item.has_tag(self.tag)

    def __str__(self):
        return self.tag


def parse_predicate(text):
    return Parser(Lexer(text)).parse()

########NEW FILE########
__FILENAME__ = title
from .utils import create_tag_pattern, remove_tags, fix_tag, remove_tag
from . import utils
from .todolist import TodoList

tag_prefix = '@'

class ItemTitle(object):
    def __init__(self, text, indent_level, typ):
        self.text = text.rstrip()
        self._id = TodoList.assign_id(self)
        self.indent_level = indent_level
        self.type = typ
        self.prefix = ''
        self.postfix = ''

    def deep_copy(self):
        new = ItemTitle(
            text=self.text,
            indent_level=self.indent_level,
            typ=self.type
        )
        new.prefix = self.prefix
        new.postfix = self.postfix
        return new

    def set_indent_level(self, level):
        self.indent_level = level

    def remove_indent(self):
        self.indent_level = 0

    def edit(self, new_line):
        self.text = new_line

    def indent(self, level=1):
        self.indent_level += level

    def tag(self, tag_text, param=''):
        self.remove_tag(tag_text)
        if param:
            param = '(' + param + ')'
        else:
            param = ''

        tag_text = tag_text.strip()
        if not tag_text.startswith(tag_prefix):
            tag_text = tag_prefix + tag_text
        if self.type == 'project':
            self.text = self.text.rstrip()[0:-1] + ' ' + tag_text + param + ':'
        else:
            self.text = self.text.rstrip() + ' ' + tag_text + param
        return self.text

    def remove_tag(self, tag):
        self.text = utils.remove_tag(self.text, tag)

    def remove_tag_with_param(self, tag, param):
        tag = fix_tag(tag)
        self.text = self.text.replace(tag + '(' + param + ')', '')
        self.text = self.text.replace(tag + '[' + param + ']', '')
        self.text = self.text.replace(tag + '{' + param + '}', '')

    def get_text_without_tags(self):
        return remove_tags(self.text)

    def get_text(self):
        return self.text

    def has_tag(self, tag):
        return utils.has_tag(self.text, tag)

    def has_tags(self, tags):
        return all(self.has_tag(tag) for tag in tags)

    def has_any_tags(self, tags):
        return any(self.has_tag(tag) for tag in tags)

    def get_tag_param(self, tag):
        return utils.get_tag_param(self.text, tag)

    def replace_tag_param(self, tag, new_param):
        p, _ = create_tag_pattern(tag)
        tag = fix_tag(tag)
        self.text = p.sub(' ' + tag + '(' + new_param + ')', self.text)

    def is_done(self):
        return self.has_tag(tag_prefix + 'done')


########NEW FILE########
__FILENAME__ = todolist
from todoflow.printers.plainprinter import PlainPrinter
from datetime import date
from .query import parse_predicate

done_tag = 'done'

class TodoList(object):
    items_by_id = {}
    _current_id = 0

    @classmethod
    def assign_id(cls, item):
        cls.items_by_id[cls._current_id] = item
        cls._current_id += 1
        return cls._current_id - 1

    @classmethod
    def tag(cls, id_no, tag, param=None):
        cls.items_by_id[id_no].tag(tag, param)

    @classmethod
    def do(cls, id_no):
        cls.items_by_id[id_no].tag(
            done_tag,
            date.today().isoformat()
        )

    @classmethod
    def get_item(cls, id_no):
        return cls.items_by_id[id_no]

    @classmethod
    def get_content(cls, id_no):
        return cls.items_by_id[id_no].get_content()

    @classmethod
    def get_text(cls, id_no):
        return cls.items_by_id[id_no].get_text()

    @classmethod
    def remove(cls, id_no):
        cls.items_by_id[id_no].remove_self_from_parent()

    @classmethod
    def edit(cls, id_no, new_content):
        cls.items_by_id[id_no].edit(new_content)

    def __init__(self, items=None):
        self.items = items if items else []
        self.set_parent_list(self.items)
        self.source = None
        self.tags_counters = {}
        self._iter_items_idx = 0
        self.type = 'list'

    def __iter__(self):
        for item in self.items:
            yield item
            for subitem in item.sublist:
                yield subitem

    def __add__(self, other):
        return TodoList(
            self.items + other.items
        )


    def __str__(self):
        return PlainPrinter().pformat(self)

    def copy(self):
        return TodoList(self.copy_of_items())

    def deep_copy(self):
        return TodoList(self.deep_copy_of_items())

    def copy_of_items(self):
        return [item.copy() for item in self.items if item]

    def deep_copy_of_items(self):
        return [item.deep_copy() for item in self.items]

    def remove_item(self, item):
        self.items.remove(item)

    def set_source(self, path):
        for item in self.items:
            item.set_source(path)

    def set_parent_list(self, items):
        for item in items:
            item.parent_list = self

    def add_parent(self, parent):
        for item in self.items:
            item.add_parent(parent)

    def indent(self, level=1):
        for item in self.items:
            item.indent(level)

    def dedent(self):
        self.indent(-1)

    def set_indent_level(self, level):
        for item in self.items:
            item.set_indent_level(level)

    def remove_tag(self, tag):
        """removes every occurrence of given tag in list"""
        for item in self.items:
            item.remove_tag(tag)

    def add_tag(self, tag, param=None):
        for item in self.items:
            item.tag(tag, param)

    def prepend(self, items_list):
        self.set_parent_list(items_list)
        self.items = items_list + self.items

    def append(self, items_list):
        self.set_parent_list(items_list)
        self.items += items_list

    def fix_predicate(self, predicate):
        # parse predicate if it's in string
        is_unicode = False
        try:
            is_unicode = isinstance(predicate, unicode)
        except NameError:
            pass

        if is_unicode or isinstance(predicate, str):
            predicate = parse_predicate(predicate)
        return predicate

    def filter(self, predicate):
        """
        returns new todolist that contains only elements that
        meet predicate and their parents
        """
        predicate = self.fix_predicate(predicate)
        filtered_items_with_None = [
            item.filter(predicate) for item in self.items
        ]
        filtered_items = [
            item for item in filtered_items_with_None if item
        ]
        new_list = TodoList(filtered_items)
        return new_list

    def search(self, predicate):
        """
        returns list of items that meet search predicate
        """
        predicate = self.fix_predicate(predicate)
        results = []
        for item in self.items:
            results += (item.search(predicate))
        return results
########NEW FILE########
__FILENAME__ = utils
import re

def create_tag_pattern(tag):
    tag = fix_tag(tag)
    return re.compile(r'(?<=\s)' + tag + r'(\([^)]*\)|)(?=(\s|$))')    

def remove_tag(txt, tag):
    p = create_tag_pattern(tag)
    return p.sub('', txt).rstrip()

def add_tag(txt, tag, param=None, index=None):
    tag = fix_tag(tag)
    if param:
        tag += '(' + str(param) + ')'
    if not index:
        txt = append_space(txt)
        return txt + tag
    else:
        first_part = append_space(txt[:index])
        second_part = prepend_space(txt[index:])
        return first_part + tag + second_part

def get_tag_param(txt, tag):
    p = create_tag_pattern(tag)
    match = p.search(txt)
    if not match:
        return None
    return match.group(1)[1:-1]

def has_tag(txt, tag):
    p = create_tag_pattern(tag)
    return bool(p.search(txt))

def append_space(txt):
    if not txt.endswith(' '):
        txt += ' '
    return txt

def prepend_space(txt):
    if not txt.startswith(' '):
        return ' ' + txt
    return txt

def remove_tags(txt):
    for rx in [
        r'\s@[^(\s]*\([^)]*?\)',
        r'\s@[^\[\s]*\[[^)]*?\]',
        r'\s@[^\{\s]*\{[^)]*?\}',
        r'\s@\S*',
    ]:
        p = re.compile(rx)
        txt = p.sub(' ', txt)
    while '  ' in txt:
        txt = txt.replace('  ', ' ')
    return txt.rstrip()


def fix_tag(txt):
    if not txt.startswith('@'):
        return '@' + txt
    else:
        return txt


# ( everything but `)` ) or lookahead for \s or end of line
tag_param_regexp = r'(\(([^)]*)\)|(?=(\s|$)))'
# prepend word (sequence without \s and `(`)
tag_regexp_without_at = r'[^\(\s]+' + tag_param_regexp
tag_pattern_without_at = re.compile(tag_regexp_without_at + r'\Z')
# prepend '@'
tag_pattern = re.compile('(?<!^)(@' + tag_regexp_without_at + ')')

def enclose_tags(text, prefix, postfix):
    """
    puts `prefix` before and `postfix` after
    every tag in text
    """
    def f(t):
        return prefix + t.group(1) + postfix
    return re.sub(tag_pattern, f, text)


def task_cmp(tag):
    def f(task1, task2):
        has_tag1 = has_tag(task1, tag)
        has_tag2 = has_tag(task2, tag)
        if not has_tag1 and not has_tag2:
            return 0
        elif not has_tag1 and has_tag2:
            return -1
        elif has_tag1 and not has_tag2:
            return 1
        else:
            p1 = get_tag_param(task1, tag)
            p2 = get_tag_param(task2, tag)
            return cmp(p1, p2)
    return f


def sort_by_tag(lines, tag):
    return sorted(lines, cmp=task_cmp(tag))
########NEW FILE########
__FILENAME__ = act_on_tag
import todoflow
import subprocess

from todoflow.src.utils import remove_tags
# Actions

def open_action(tag, item):
    path = item.get_tag_param(tag)
    subprocess.check_output('open "{0}"'.format(path), shell=True)
    return True


def alfred_search_action(prefix):
    def f(tag, item):
        query = ' '.join([prefix, remove_tags(item.text)])
        subprocess.call(
            'osascript -e "tell application \\"Alfred 2\\" to search \\"{0}\\""'.format(query),
            shell=True
        )
    return f


def open_website_action(url):
    def f(tag, item):
        full_url = url.format(query=remove_tags(item.text))
        subprocess.call('open "{0}"'.format(full_url), shell=True)
        return True
    return f


def put_to_clipboard_action(tag, item):
    subprocess.call('echo ' + item.text + ' | pbcopy', shell=True)

# Config

tag_to_action = {
    'mail': open_action,
    'web': open_action,
    'file': open_action,
    'search': open_website_action('http://google.com/search?q={query}'),
    'research': open_website_action('http://google.com/search?q={query}'),
    'imgsearch': open_website_action('http://google.com/search?q={query}&source=lnms&tbm=isch'),
    'download': alfred_search_action('pb'),
    'tvseries': alfred_search_action('pb'),
    'comics': alfred_search_action('pb'),
}

# Act on tag

def act_on_tag_id(item_id):
    item = todoflow.get_item(item_id)
    act_on_tag(item)


def act_on_tag(item):
    for tag in tag_to_action:
        if item.has_tag(tag):
            should_continue = tag_to_action[tag](tag, item)
            if not should_continue:
                return
    
########NEW FILE########
__FILENAME__ = alfredq
#!/usr/bin/python
import sys
sys.path.append('/Users/bvsc/Dropbox/Projects')

import todoflow
from todoflow.printers import XMLPrinter

query = ' '.join(sys.argv[1:])
query = todoflow.expand_query(query)

t = todoflow.from_files(todoflow.lists.to_list()).filter(query)
print XMLPrinter().pformat(t)

########NEW FILE########
__FILENAME__ = inbox
# -*- coding: utf-8 -*-
import sys
sys.path.append('/Users/bvsc/Dropbox/Projects')

from datetime import date
import re

# config
from todoflow.config import inbox_path
from todoflow.config import inbox_tag_to_path

def make_re(tag):
    return re.compile('(?:^|\s)(' + tag + ')(?:$|\s|\()')

url_pattern = re.compile('https{0,1}://\S*')


def add_tags(msg):
    return url_pattern.sub(lambda x: '@web(' + x.group(0) + ')', msg)


def inbox(msg):
    wtf = { # I dont know, I have strange problems with encoding in Sublime Text
        'ż': 'ż', # you can probably remove this
        'ę': 'ę',
        'ó': 'ó',
        'ą': 'ą',
        'ś': 'ś',
        'ń': 'ń',
        'ź': 'ź',
        'ć': 'ć',
        'ń': 'ń',
        'Ż': 'Ż',
        'Ó': 'Ó',
        'Ę': 'Ę',
        'Ą': 'Ą',
        'Ź': 'Ź',
        'Ń': 'Ń',
        'Ć': 'Ć',
        'Ś': 'Ś',
    }
    for k, v in wtf.items():
        msg = msg.replace(k, v)
    msg = ' ' + msg.strip().replace('\\n', '\n').replace('\\t', '\t')
    msg = add_tags(msg)
    to_write = "-" + msg + ' @in(' + date.today().isoformat() + ')'

    path_to_add = inbox_path

    for tag, path in inbox_tag_to_path.items():
        if make_re(tag).findall(msg):
            path_to_add = path

    with open(path_to_add, 'r') as f:
        old = f.read()
        if old and not old.endswith('\n'):
            to_write += '\n'
    with open(path_to_add, 'a') as f:
        print path_to_add
        f.write(to_write + '\n')

if __name__ == '__main__':
    inbox(' '.join(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = to_calendar
import todoflow
from todoflow.src.utils import remove_tag
import subprocess
from datetime import datetime

applescript = """tell application "Calendar"
	tell calendar "{calendar}"
		set startDate to current date
		set the year of startDate to {start_year}
		set the month of startDate to {start_month}
		set the day of startDate to {start_day}
		set the hours of startDate to {start_hour}
		set the minutes of startDate to {start_minute}
		set endDate to current date
		set the year of endDate to {end_year}
		set the month of endDate to {end_month}
		set the day of endDate to {end_day}
		set the hours of endDate to {end_hour}
		set the minutes of endDate to {end_minute}
		make new event at end with properties {{summary:"{title}", location:"{location}", start date:startDate, allday event:{allday}, end date:endDate}}
	end tell
end tell
"""

tag_to_calendar = {
	'date': 'Kalendarz',
	'due': 'Deadlines',
}

def create_event(calendar, title, start_date, location='', end_date=None, allday=False):
	if not end_date:
		end_date = start_date
	filled_applescript = applescript.format(
		calendar=calendar,
		title=title,
		location=location,
		start_year=start_date.year,
		start_month=start_date.month,
		start_day=start_date.day,
		start_hour=start_date.hour,
		start_minute=start_date.minute,
		end_year=end_date.year,
		end_month=end_date.month,
		end_day=end_date.day,
		end_hour=end_date.hour,
		end_minute=end_date.minute,
		allday=str(allday).lower(),
	)
	print filled_applescript
	print ''
	cmd = u'echo "{0}" | osascript'.format(filled_applescript.replace('"', '\\"'))
	subprocess.check_output(
	    cmd, shell=True
	)

def parse_dates(task, date_str):
	year, month, day = date_str.split('-')
	year = int(year)
	month = int(month)
	day = int(day)
	start_hour = 0
	end_hour = 0
	start_minute = 0
	end_minute = 0
	allday = True
	if task.has_tag('at'):
		allday = False
		at = task.get_tag_param('at').split('-')
		start_hour, start_minute = at[0].split(':')
		start_hour = int(start_hour)
		start_minute = int(start_minute)
		if len(at) == 2:
			end_hour, end_minute = at[1].split(':')
			end_hour = int(start_hour)
			end_minute = int(start_minute)
		else:
			end_minute = start_minute
			end_hour = start_hour + 1
			if (end_hour > 23):
				end_hour = 23
				end_minute = 59
	start_date = datetime(year, month, day, start_hour, start_minute)
	end_date = datetime(year, month, day, end_hour, end_minute)
	return start_date, end_date, allday


def get_title(task):
	title = task.text
	for tag in ['due', 'date', 'at', 'place']:
		title = remove_tag(title, tag)
	title = title.strip()
	return title

# @due/@date - start date day
# @at(15:00) - start date time
# @at(15:00-16:00) - start date time - end date time
# @place - location
# not @at - allday = true

def create_event_for_task(task):
	calendar = ''
	date_str = ''
	for tag, calendar_for_tag in tag_to_calendar.items():
		if task.has_tag(tag):
			calendar = calendar_for_tag
			date_str = task.get_tag_param(tag)
	location = ''
	if task.has_tag('place'):
		location = task.get_tag_param('place')
	start_date, end_date, allday = parse_dates(task, date_str)
	title = get_title(task)
	print 'CALENDAR:', title, location, 'allday =', allday, start_date, end_date
	create_event(
		calendar=calendar,
		title=title,
		allday=allday,
		start_date=start_date,
		end_date=end_date,
		location=location
	)
	task.tag('calendar')


def create_events_for_list(t):
	for item in t.filter('(@due or @date) and not @calendar'):
		if (item.has_tag('@due') or item.has_tag('@date')) and not item.has_tag('calendar'):
			create_event_for_task(item)


if __name__ == '__main__':
	t = todoflow.all_lists()
	create_events_for_list(t)
	todoflow.save(t)
########NEW FILE########
__FILENAME__ = agenda
#coding: utf-8
#!/usr/bin/python
import sys
import todoflow
import math
from todoflow.printers import EditorialPrinter

import re

# regexpes used in functions:

# ( everything but `)` ) or lookahead for \s or end of line
tag_param_regexp = r'(\(([^)]*)\)|(?=(\s|$)))'
# prepend word (sequence without \s and `(`)
tag_regexp_without_at = r'[^\(\s]+' + tag_param_regexp
tag_pattern_without_at = re.compile(tag_regexp_without_at + r'\Z')
# prepend '@'
tag_pattern = re.compile('(?<!^)(@' + tag_regexp_without_at + ')')

#

def enclose_tags(text, prefix, postfix):
    """
    puts `prefix` before and `postfix` after
    every tag in text
    """
    def f(t):
        return prefix + t.group(1) + postfix
    return re.sub(tag_pattern, f, text)

from datetime import datetime, date

title_length = 80




def htmlify(tag, text, classes=''):
    if not (isinstance(classes, str) or isinstance(classes, unicode)):
        classes = ' '.join(classes)
    return u'<{0} class="{1}">{2}</{0}>'.format(tag, classes, text)


def titleize(title, style):
    return htmlify('h1', title, ('section-title', style))


def print_query(t, title, query, style):
    s = EditorialPrinter().pformat(t.filter(query)).decode('utf-8')
    if s:
        return htmlify(
            'div',
            (titleize(title, style) + u'\n' + s),
            ['agenda-section', style + '-section']
        ).encode('utf-8')
    return ''


def calculate_days_left(item, tag):
    param = item.get_tag_param(tag)
    due_date = datetime.strptime(param, '%Y-%m-%d').date()
    days = (due_date - date.today()).days
    days_str = str(days).zfill(2)
    return days, days_str


def get_style_for_due(days_left, item):
    style = 'far-away'
    if item.has_tag('blocked'):
        style = 'blocked'
    elif days_left <= 2:
        style = 'soon'
    elif days_left <= 7:
        style = 'this-week'
    return ['countdown', style]

from todoflow.config import path_to_folder_synced_in_editorial


def make_linked_text(days_str, item):
    inside_link = htmlify('span', days_str, 'days-number') + ' ' + item.text
    file_url = item.source.replace(path_to_folder_synced_in_editorial, '')
    return u'<a href="editorial://open/{0}?root=dropbox&command=goto&input={2}:{3}">{1}</a>'.format(
                file_url, 
                inside_link, 
                item.first_char_no,
                item.first_char_no + \
                    len(item.text) + \
                    item.indent_level + \
                    (1 if item.type == 'task' else 0) + \
                    (-1 if item.type == 'note' else 0),
            )


def print_deadlines(t, tag, due, title_style, title):
    if not due:
        return
    dues = []
    for item in due:
        if item.has_tag(tag):
            text = enclose_tags(item.text, '<span class="tag">', '</span>')
            days, days_str = calculate_days_left(item, tag)
            style = get_style_for_due(days, item)
            linked_text = make_linked_text(days_str, item)
            dues.append((linked_text, style))
        else:
            pass
    result = titleize(title, title_style) + \
        htmlify('ul', '\n'.join([htmlify('li', text, style) for text, style in sorted(dues)]))
    return result.encode('utf-8')


def print_due(t):
    due = t.filter('@due and not @done and not project ? onhold')
    if not due.items:
          return
    return htmlify(
        'div',
        print_deadlines(t, 'due', due, 'deadlines', 'Deadlines'),
        ['agenda-section', 'deadlines-section']
    ).encode('utf-8')


def print_dates(t):
    due = t.filter('@date and not @done')
    if not  bool(due.items):
            return ''
    return htmlify(
        'div',
        print_deadlines(t, 'date', due, 'dates', 'Dates'),
        ['agenda-section', 'dates-section']
    ).encode('utf-8')
    


t = todoflow.from_files(todoflow.lists.to_list())

query_today = '@working and not @done'
query_next = '@next and not @done and not @working'

html_parts = [
    print_due(t),
    print_dates(t),
    print_query(t, 'Working', query_today, 'working'),
    print_query(t, 'Next', query_next, 'next'),
    '<a class="reload-button" id="reload-button" href="editorial://?command=TF:%20Agenda">Reload</a>',
]

action_out = '\n'.join(html_parts).decode('utf-8')

import workflow
workflow.set_output(action_out)

import editor
if editor.get_theme() == 'Dark':
    css = workflow.get_variable('dark css')
else:
    css = workflow.get_variable('light css')

workflow.set_variable('css', css.decode('utf-8'))

########NEW FILE########
__FILENAME__ = import parsedatetime
path_to_folder_synced_in_editorial = '/Users/bvsc/Dropbox/Notes/'

import seamless_dropbox as sd
import os

path_to_parsedatetime_in_dropbox = 'Scripts/parsedatetime'

base = os.getcwd() + '/parsedatetime'

dirs = [
    '/parsedatetime',
]

for dr in dirs:
    try:
        os.makedirs(base + dr)
    except OSError:
        pass 

files = [
    '/__init__.py',
    '/parsedatetime.py',
    '/pdt_locales.py',
]

for i, name in enumerate(files):
    print i + 1, '/', len(files), name
    t = sd.open(path_to_parsedatetime_in_dropbox + name).read()
    print(base + name)
    f = open(base + name, 'w')
    f.write(t)
    f.close()
print 'done'

########NEW FILE########
__FILENAME__ = import todoflow
path_to_folder_synced_in_editorial = '/Users/bvsc/Dropbox/Notes/'

import seamless_dropbox as sd
import os

path_to_todoflow_in_dropbox = 'Projects/todoflow'


dirs = [
    '/src',
    '/printers',
]

base = os.getcwd() + '/todoflow'

for dr in dirs:
    try:
        os.makedirs(base + dr)
    except OSError:
        pass 

files = [
    '/__init__.py',
    '/config.py',
    '/printers/__init__.py',
    '/printers/colorprinter.py',
    '/printers/dayoneprinter.py',
    '/printers/editorialprinter.py',
    '/printers/htmllinkedprinter.py',
    '/printers/htmlprinter.py',
    '/printers/plainprinter.py',
    '/printers/pythonistaprinter.py',
    '/printers/utils.py',
    '/printers/xmlprinter.py',
    '/README.md',
    '/src/__init__.py',
    '/src/fileslist.py',
    '/src/item.py',
    '/src/lexer.py',
    '/src/main.py',
    '/src/parser.py',
    '/src/query.py',
    '/src/title.py',
    '/src/todolist.py',
    '/src/utils.py',
]


preambule = """
import editor

path_to_folder_synced_in_editorial = '{0}'

def open(name, mode='r'):
    editorial_path = name.replace(path_to_folder_synced_in_editorial, '')
    content = editor.get_file_contents(editorial_path, 'dropbox')
    return FakeFile(content, editorial_path, mode)
    
class FakeFile(object):
    def __init__(self, content, name, mode):
        self.content = content
        self.name = name
        self.mode = mode
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass
        
    def read(self):
        return self.content
        
    def readlines(self):
        return [l + '\\n' for l in self.content.split('\\n')]

    def write(self, content):
        new_content = content
        if self.mode != 'a':
            new_content = self.content + '\\n' + new_content
        editor.set_file_contents (self.name, new_content, 'dropbox')

    def close(self):
        pass
            
""".format(path_to_folder_synced_in_editorial)
print(preambule)

for i, name in enumerate(files):
    print i + 1, '/', len(files), name
    t = sd.open(path_to_todoflow_in_dropbox + name).read()
    print(base + name)
    f = open(base + name, 'w')
    f.write(preambule + t)
    f.close()
print 'done'
########NEW FILE########
__FILENAME__ = htmlq
#!/usr/bin/python

import sys
sys.path.append('/Users/bvsc/Dropbox/Projects')

import todoflow
from todoflow.config import path_to_css
from todoflow.printers import HTMLPrinter, HTMLLinkedPrinter, EditorialPrinter

query = ' '.join(sys.argv[1:])
query = todoflow.expand_query(query)

t = todoflow.from_files(todoflow.lists.to_list()).filter(query)
HTMLLinkedPrinter(path_to_css).pprint(t)

########NEW FILE########
__FILENAME__ = print_agenda
#!/usr/bin/python
import sys
sys.path.append('/Users/bvsc/Dropbox/Projects')

"""defines colors used in output"""
defc         = '\033[0m'

red          = '\033[1;31m'
green        = '\033[1;32m'
gray         = '\033[1;30m'
blue         = '\033[1;34m'

yellow       = '\033[1;33m'
magenta      = '\033[1;35m'
cyan         = '\033[1;36m'
white        = '\033[1;37m'
crimson      = '\033[1;38m'

high_red     = '\033[1;41m'
high_green   = '\033[1;42m'
high_brown   = '\033[1;43m'
high_blue    = '\033[1;44m'
high_magenta = '\033[1;45m'
high_cyan    = '\033[1;46m'
high_gray    = '\033[1;47m'
high_crimson = '\033[1;48m'

import todoflow
import math
from todoflow.printers import ColorPrinter
from datetime import datetime, date
from todoflow.src.utils import enclose_tags

title_length = 80

def titleize(title, high, color):
    spaces_no = title_length - len(title)
    return '\n' +  high + color + ' ' * int(math.floor(spaces_no / 2.)) + title + ' ' * int(math.ceil(spaces_no / 2.)) + defc + '\n'


def print_query(t, title, query, high, color):
    s = ColorPrinter().pformat(t.filter(query))
    if s:
        print titleize(title, high, color)
        print s

def print_due(t):
    print_deadlines(t, 'due', '@due and not @done and not project ? onhold', red, high_red, 'DEADLINES')

def print_dates(t):
    print_deadlines(t, 'date', '@date and not @done', magenta, high_magenta, 'DATES')

def print_deadlines(t, tag, query, highlight_color, title_color, title):
    due = t.search(query)
    dues = []
    if due:
        print titleize(title, title_color, white)
    for item in due:
        param = item.get_tag_param(tag)
        due_date = datetime.strptime(param, '%Y-%m-%d').date()
        days = (due_date - date.today()).days
        days_str = str(days).zfill(2)
        color = white
        if item.has_tag('blocked'):
            color = gray
        elif days <= 2:
            color = highlight_color
        elif days <= 7:
            color = yellow
        text = enclose_tags(item.text, blue, defc)
        dues.append((white + days_str + defc + ' ' + text + defc, color))
    for d, c in sorted(dues):
        print c + d

t = todoflow.all_lists()
print '\n' * 50

print_due(t)
print_dates(t)

query_today = '@working and not @done'
print_query(t, 'WORKING', query_today, high_green, white)

query_next = '@next and not @done and not @working'
print_query(t, 'NEXT', query_next, high_blue, white)

########NEW FILE########
__FILENAME__ = import parsedatetime
path_to_folder_synced_in_editorial = '/Users/bvsc/Dropbox/Notes/'

import seamless_dropbox as sd
import os

path_to_parsedatetime_in_dropbox = 'Scripts/parsedatetime'

base = os.getcwd() + '/parsedatetime'

dirs = [
    '/parsedatetime',
]

for dr in dirs:
    try:
        os.makedirs(base + dr)
    except OSError:
        pass 

files = [
    '/__init__.py',
    '/parsedatetime.py',
    '/pdt_locales.py',
]

for i, name in enumerate(files):
    print i + 1, '/', len(files), name
    t = sd.open(path_to_parsedatetime_in_dropbox + name).read()
    print(base + name)
    f = open(base + name, 'w')
    f.write(preambule + t)
    f.close()
print 'done'

########NEW FILE########
__FILENAME__ = import todoflow
import seamless_dropbox as sd
import os

path_to_todoflow_in_dropbox = 'Projects/todoflow'

dirs = [
    '/src',
    '/printers',
]

base = os.getcwd() + '/todoflow'

for dr in dirs:
    try:
        os.makedirs(base + dr)
    except OSError:
        pass 

files = [
    '/__init__.py',
    '/config.py',
    '/listfiles.py',
    '/printers/__init__.py',
    '/printers/colorprinter.py',
    '/printers/dayoneprinter.py',
    '/printers/editorialprinter.py',
    '/printers/htmllinkedprinter.py',
    '/printers/htmlprinter.py',
    '/printers/plainprinter.py',
    '/printers/pythonistaprinter.py',
    '/printers/utils.py',
    '/printers/xmlprinter.py',
    '/README.md',
    '/src/__init__.py',
    '/src/fileslist.py',
    '/src/item.py',
    '/src/lexer.py',
    '/src/main.py',
    '/src/parser.py',
    '/src/query.py',
    '/src/title.py',
    '/src/todolist.py',
    '/src/utils.py',
]


preambule = 'from seamless_dropbox import open\n\n'

for i, name in enumerate(files):
    print i + 1, '/', len(files), name
    t = sd.open(path_to_todoflow_in_dropbox + name).read()
    print(base + name)
    f = open(base + name, 'w')
    f.write(preambule + t)
    f.close()
print 'done'
########NEW FILE########
__FILENAME__ = print_agenda
#coding: utf-8
#!/usr/bin/python
import sys
import todoflow
import math
from todoflow.src.printers import PythonistaPrinter
from datetime import date, datetime
import re
import console


def print_title(title, color):
    console.set_font(size=32)
    console.set_color(*color)
    print title
    console.set_font()
    console.set_color()


def print_query(t, title, query, color):
    print_title(title, color)
    PythonistaPrinter().pprint(t.filter(query))


def calculate_days_left(item, tag):
    param = item.get_tag_param(tag)
    due_date = datetime.strptime(param, '%Y-%m-%d').date()
    days = (due_date - date.today()).days
    days_str = str(days).zfill(2)
    return days, days_str


def get_color(days_left, item):
    color = ()
    if item.has_tag('blocked'):
        color = (0.4, 0.4, 0.4)
    elif days_left <= 2:
        color = (1.0, 0.1, 0.1)
    elif days_left <= 7:
        color = (0.5, 0.5, 0.5)
    return color


def hcs(font_size=None, color=None):
    if font_size:
        console.set_font('', font_size)
    else:
        console.set_font()
    if color:
        console.set_color(*color)
    else:
        console.set_color()



def print_deadlines(t, query, tag, title_style, title):
    due = t.filter(query)
    if not due:
        return
    dues = []
    for item in due:
        if item.has_tag(tag):
            text = item.text
            days, days_str = calculate_days_left(item, tag)
            dues.append((days_str, text, get_color(days, item)))
        else:
            pass
    print_title(title, title_style)
    for days, text, color in dues:
        hcs(20)
        print days, hcs(color=color), text
        hcs()


t = todoflow.from_files(todoflow.lists.to_list())

query_today = '@working and not @done'
query_next = '@next and not @done and not @working'

print_deadlines(t, '@due and not @done and not @waiting', '@due', (1.0, 0.0, 0.0), 'Deadlines')
print_deadlines(t, '@date and not @done and not @waiting', '@date', (1.0, 1.0, 0.0), 'Dates')
print_query(t, 'Working', query_today, (0.0, 1.0, 1.0))
print_query(t, 'Next', query_next, (0.0, 0.0, 1.0))
########NEW FILE########
__FILENAME__ = qtodoflow
import todoflow
from todoflow.printers import PythonistaPrinter
import sys
q = ' '.join(sys.argv[1:])
q = todoflow.expand_query(q)
print q
t = todoflow.all_lists().filter(q)
PythonistaPrinter().pprint(t)

########NEW FILE########
__FILENAME__ = qr_to_drafts
import qrcode
import os.path
import subprocess

def_path = '~/Desktop/'
def_filename = 'qr'
path = os.path.expanduser(def_path)

drafts_url = "drafts://x-callback-url/create?text={0}&action=Inbox&x-success=scan:"


def qr_create(text, filename=def_filename):
    img = qrcode.make(
        drafts_url.format(
            text.replace(' ', '%20')
        )
    )
    if not filename.endswith('.png'):
        filename += '.png'
    img.save(path + filename)
    subprocess.call('open "' + path + filename + '"', shell=True)

if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        print 'text to qr'
        sys.exit(0)
    qr_create(' '.join(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = agenda_to_reminders
import sys
sys.path.append('/Users/bvsc/Dropbox/Projects')
import todoflow

from datetime import datetime, date

from clear_reminders_list import clear_reminders_list
from create_reminder import create_reminder


def clear_lists():
    print 'clearing'
    to_clear = ['Working', 'Next', 'Deadlines', 'Contexts', 'Inbox']
    for l in to_clear:
        clear_reminders_list(l)
    print 'cleared'


def export_deadlines(t):
    due = t.filter('@due and not @done and not project ? onhold')
    for item in due:
        if item.has_tag('due'):
            param = item.get_tag_param('due')
            due_date = datetime.strptime(param, '%Y-%m-%d')
            if item.has_tag('at'):
                hour_str, minutes_str = item.get_tag_param('at').split(':')
                due_date = due_date.replace(hour=int(hour_str), minute=int(minutes_str))
            else:
                due_date = due_date.replace(hour=23, minute=59)
            create_reminder(item.text, item.parents_to_str(), due_date, 'Deadlines', should_print=True) 


def export_today(t):
    items = t.filter('@working and not @done')
    for item in items:
            if item.has_tag('@working'):
                due_date = datetime.now()
                if item.has_tag('at'):
                    hour_str, minutes_str = item.get_tag_param('at').split(':')
                    due_date = due_date.replace(hour=int(hour_str), minute=int(minutes_str))
                else:
                    due_date = due_date.replace(hour=23, minute=59)
                create_reminder(item.text, item.parents_to_str(), due_date, 'Working', should_print=True)


def export_generic(t, query, tag, list_name):
    items = t.filter(query)
    for item in items:
        if tag:
            if item.has_tag(tag):
                create_reminder(item.text, item.parents_to_str(), reminders_list=list_name, should_print=True)



def export_contexts(t):
    items = t.filter('project ? Contexts')
    for item in items:
        if item.text.startswith('@ ') or item.text == '':
            continue
        create_reminder(item.text, item.parents_to_str(), reminders_list='Contexts', should_print=True)



def export():
    clear_lists()
    t = todoflow.from_files(todoflow.lists.to_list())
    export_deadlines(t)
    export_today(t)
    export_generic(t, '@next and not @done and not @today', '@next', 'Next')
    export_contexts(t)


if __name__ == '__main__':
    export()
    print 'done'
########NEW FILE########
__FILENAME__ = clear_reminders_list
import subprocess

applescript_template = u"""tell application \\"Reminders\\"
    set rs to reminders in list \\"{list_name}\\"
    repeat with r in rs
        delete r
    end repeat
end tell"""


def clear_reminders_list(list_name):
    applescript = applescript_template.format(
        list_name=list_name
    )
    cmd = u'echo "{0}" | osascript'.format(applescript)
    subprocess.check_output(
        cmd, shell=True
    )

########NEW FILE########
__FILENAME__ = create_reminder
import subprocess

applescript_template = u"""tell application \\"Reminders\\"
    set r to make new reminder
    set name of r to \\"{name}\\"
    set body of r to \\"{body}\\"
end tell"""

applescript_template_with_date = u"""tell application \\"Reminders\\"
    set r to make new reminder
    set name of r to \\"{name}\\"
    set body of r to \\"{body}\\"
    set remind me date of r to date \\"{reminde_me_date}\\"
end tell"""

applescript_template_with_list = u"""tell application \\"Reminders\\"
    set mylist to list \\"{list_name}\\"
    tell mylist
        set r to make new reminder
        set name of r to \\"{name}\\"
        set body of r to \\"{body}\\"
    end tell
end tell"""

applescript_template_with_list_and_date = u"""tell application \\"Reminders\\"
    set mylist to list \\"{list_name}\\"
    tell mylist
        set r to make new reminder
        set name of r to \\"{name}\\"
        set body of r to \\"{body}\\"
        set remind me date of r to date \\"{reminde_me_date}\\"
    end tell
end tell"""

def create_reminder(name, body, reminde_me_date=None, reminders_list=None, should_print=False):
    if reminde_me_date and not isinstance(reminde_me_date, str) and not  isinstance(reminde_me_date, unicode):
        reminde_me_date = reminde_me_date.strftime('%d-%m-%Y %H:%M')
            
    if reminders_list and reminde_me_date:
        applescript = applescript_template_with_list_and_date.format(
            name=name,
            body=body,
            reminde_me_date=reminde_me_date,
            list_name = reminders_list
        )
    elif reminde_me_date:
        applescript = applescript_template_with_date.format(
            name=name,
            body=body,
            reminde_me_date=reminde_me_date
        )
    elif reminders_list:
        applescript = applescript_template_with_list.format(
            name=name,
            body=body,
            list_name = reminders_list
        )
    else:
        applescript = applescript_template(
            name=name,
            body=body,
        )

    cmd = u'echo "{0}" | osascript'.format(applescript)
    if should_print:
        print cmd
    subprocess.check_output(
        cmd, shell=True
    )

########NEW FILE########
__FILENAME__ = remind
from datetime import datetime, timedelta, time, date
from create_reminder import create_reminder
from todoflow.printers import PlainPrinter
import todoflow


def set_reminders(todolist):
    for item in todolist.filter('@remind'):
        if item.has_tag('@remind'):
            remind_date_str = item.get_tag_param('@remind')
            at = item.get_tag_param('at') if item.has_tag('at') else '23:59'
            date_str = remind_date_str + ' ' + at
            remind_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            item.remove_tag('remind')
            item.remove_tag('at')
            create_reminder(
                item.title.text,
                PlainPrinter().pformat(item.sublist),
                remind_date,
            )
            item.tag('willremind', param=date_str)
            print 'REMINDER:', item.title.text, remind_date

if __name__ == '__main__':
    t = todoflow.all_lists()
    set_reminders(t)
    todoflow.save(t)

########NEW FILE########
__FILENAME__ = stodoflow
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sublime
import sublime_plugin
from datetime import datetime, date

import sys
sys.path.append('/path/to/parent/of/todoflow')  # TODO: find some better way to ensure that todoflow can be found on python path

import todoflow
from todoflow.printers import PlainPrinter3 as pp
import todoflow.src.utils as u


class MultipleLinesModifierCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            line = self.view.line(region)
            text = self.view.substr(line).rstrip()
            rpl = self.modify(text)
            self.view.replace(edit, line, rpl)
        
        new_selections = []
        for sel in list(self.view.sel()):
            if not sel.empty():
                new_selections.append(sublime.Region(sel.b, sel.b))
            else:
                new_selections.append(sel)
        self.view.sel().clear()
        for sel in new_selections:
            self.view.sel().add(sel)


class TasksToggleCommand(MultipleLinesModifierCommand):
    def modify(sefl, text):
        """
        toggles between tags
        no_tag -> @next -> @working -> @done(date) -> no_tag
        """

        tags_to_toggle = ['next', 'working', 'done']
        tagged_already = False

        if u.has_tag(text, tags_to_toggle[-1]):
            text = u.remove_tag(text, tags_to_toggle[-1])
            tagged_already = True

        for i, tag in enumerate(tags_to_toggle[:-1]):
            if u.has_tag(text, tag):
                text = u.remove_tag(text, tag)
                text = u.add_tag(
                    text,
                    tags_to_toggle[i + 1],
                    param=date.today().isoformat() if tags_to_toggle[i + 1] == 'done' else None
                )
                tagged_already = True
                break
        if not tagged_already:
            text = u.add_tag(text, tags_to_toggle[0])
        return text


def is_project(line):
    return line.endswith(':')


class NewTaskCommand(MultipleLinesModifierCommand):
    def modify(self, line):
        level = indent_level(line)
        if is_project(line):
            level += 1
        r = line + '\n' + '\t' * level + '- '
        return r


def indent_level(text):
    indent_char = u'\t'
    level = 0
    while level < len(text) and text[level] == indent_char:
        level += 1
    return level


class DateChangeCommand(sublime_plugin.TextCommand):
    def change_date(self, edit, change=1):
        # change date by `change` value,
        # what is changed (year, month, day)
        # depends on caret position
        for region in self.view.sel():
            old_date, date_region, what_selected = find_date(self.view, region)
            if what_selected == 'nothing':
                new_date = date.today()
            elif what_selected == 'day':
                new_date = old_date + timedelta(days=change)
            elif what_selected == 'month':
                month = old_date.month + change
                if month == 0:
                    month = 12
                if month == 13:
                    month = 1
                new_date = date(old_date.year, month, old_date.day)
            elif what_selected == 'year':
                new_date = date(old_date.year + change, old_date.month, old_date.day)
            new_date_str = '(' + new_date.isoformat() + ')'
            self.view.replace(edit, date_region, new_date_str)
            self.view.sel().subtract(date_region)
            self.view.sel().add(region)


class IncreaseDateCommand(DateChangeCommand):
    def run(self, edit):
        self.change_date(edit, change=1)


class DecreaseDateCommand(DateChangeCommand):
    def run(self, edit):
        self.change_date(edit, change=-1)



def find_date(view, region):
    max_iter = 20
    citer = 0
    start = region.begin()

    if (region.end() - region.begin()) == 0:
        x = view.substr(sublime.Region(region.begin(), region.end() + 1))
        if len(x) > 0 and x[-1] == '(':
            region = sublime.Region(region.begin() + 1, region.end() + 3)
        else:
            region = sublime.Region(region.begin() - 1, region.end())
    while view.substr(region)[-1] != ')' and view.substr(region)[-1] != '\n':
        citer += 1
        if citer > max_iter:
            break
        region = sublime.Region(region.begin(), region.end() + 1)
    while view.substr(region)[0] != '(' and view.substr(region)[0] != '\n':
        citer += 1
        if citer > max_iter:
            break
        region = sublime.Region(region.begin() - 1, region.end())
    date_str = view.substr(region).strip()

    # what was selcted depends on cursor position in date
    # `|` shows possible caret positions
    what = 'day'                     # |(2013-12-31)
    if start > region.begin():       # (|2|0|1|3|-12-31)
        what = 'year'
    if start > region.begin() + 5:   # (2013-|1|2|-31)
        what = 'month'
    if start > region.begin() + 8:   # (2013-12-|3|1|)
        what = 'day'
    if start > region.begin() + 11:  # (2013-12-31)|
        what = 'day'
    try:
        ddate = calc_date(date_str)
        return ddate, region, what
    except Exception as e:
        # calc_date fails when date was not selected,
        # so insert new one
        return date.today(), sublime.Region(start, start), 'nothing'


def calc_date(date_str):
    date_str = date_str[1:-1]
    return date(*(int(x) for x in date_str.split('-')))


class MoveToProjectCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.tlist = todoflow.all_lists()
        self.projects = []
        self.ids = []
        for project in self.tlist.filter('type = "project"'):
            text = '\t' * project.indent_level + project.text
            self.projects.append(text)
            self.ids.append(project._id)

        self.view.window().show_quick_panel(self.projects, self.append_to_project)

    def append_to_project(self, index):
        if index == -1:
            return
        project_id = self.ids[index]
        for region in self.view.sel():
            line = self.view.line(region)
            text = self.view.substr(line).strip()
            items = text.split('\n')

            for item in items:
                item = strip(item)
                for titem in self.tlist:
                    if titem.text == item:
                        titem.remove_self_from_parent()
                todoflow.prepend_subtasks(project_id, item)

        todoflow.save(self.tlist)


def strip(text):
    text = text.strip()
    if text.startswith('- '):
        text = text[2:]
    if text.endswith(':'):
        text = text[:-1]
    return text
########NEW FILE########
__FILENAME__ = tp
#!/usr/bin/python
import sys
sys.path.append('/Users/bvsc/Dropbox/Projects')

import todoflow
from todoflow.printers import ColorPrinter

query = ' '.join(sys.argv[1:])
query = todoflow.expand_query(query)

t = todoflow.from_files(todoflow.lists.to_list()).filter(query)
print query
print '_' * len(query) + '\n'
ColorPrinter().pprint(t)
print ''

########NEW FILE########
__FILENAME__ = end_the_day
#!/usr/bin/python
import sys
sys.path += ['/Users/bvsc/Dropbox/Projects/todoflow/']
sys.path += ['/Users/bvsc/Dropbox/Projects/']
from todoflow.config import projects_path, inbox_path, onhold_path  # archive_path
import todoflow
import update_lists as ul
from todoflow.workflows.Calendar.to_calendar import create_events_for_list
from todoflow.workflows.Reminders.remind import set_reminders

try:
    from tvcal import tvcal
except Exception as e:
    print e
    print "couldn't reach TV Calendar"
from log_to_day_one import log_to_day_one

all_lists = todoflow.all_lists()
inbox_file = open(inbox_path, 'a')
onhold_list = todoflow.from_file(onhold_path)

log_to_day_one(all_lists.deep_copy())
try:
    tvcal(inbox_file)
except:
    pass

create_events_for_list(all_lists)
set_reminders(all_lists)
ul.update_weekly(onhold_list, inbox_file)
ul.update_waiting(onhold_list, inbox_file)

ul.update_daily(all_lists)
ul.update_followups(all_lists)
ul.update_blocked(all_lists)
ul.update_incremental(all_lists)
todoflow.save(all_lists)

########NEW FILE########
__FILENAME__ = log_to_day_one
#!/usr/bin/python
import todoflow
from todoflow.printers import DayonePrinter
import uuid
from datetime import date, timedelta
from todoflow.config import logging_in_day_one_for_yesterday, day_one_dir_path, day_one_entry_title, day_one_extension
from cgi import escape


def log_to_day_one(tlist):
    uid = str(uuid.uuid1()).replace('-', '').upper()
    log_date = date.today()
    if logging_in_day_one_for_yesterday:
        log_date -= timedelta(days=1)
    log_data_str = log_date.isoformat()
    print log_data_str

    filtered = tlist.filter(u'@done = ' + log_data_str)
    filtered.remove_tag('done')
    entry_text = day_one_entry_title + \
        DayonePrinter().pformat(filtered)

    full_text = u"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Creation Date</key>
    <date>{date}</date>
    <key>Entry Text</key>
    <string>{entry_text}</string>
    <key>Starred</key>
    <false/>
    <key>Tags</key>
    <array>
      <string>todone</string>
    </array>
    <key>UUID</key>
    <string>{uid}</string>
</dict>
</plist>
""".format(
    uid=uid,
    entry_text=escape(entry_text).decode('utf-8'),
    date=log_date.strftime('%Y-%m-%dT23:59:59Z')
)
    with open(day_one_dir_path + uid + day_one_extension, 'w') as f:
        f.write(full_text.encode('utf-8'))

if __name__ == '__main__':
    log_to_day_one(todoflow.from_files(todoflow.lists.to_list()))

########NEW FILE########
__FILENAME__ = tvcal
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path += ['/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/']

from todoflow.config import tvcal_url, inbox_path, tvseries_project_title
from icalendar import Calendar
from urllib2 import urlopen
from datetime import datetime, timedelta
import re
now = datetime.now()
today = datetime(now.year, now.month, now.day)
tommorow = today + timedelta(hours=24)

inbox_text = open(inbox_path).read().decode('utf-8')

raw_cal = urlopen(tvcal_url).read()
cal = Calendar.from_ical(raw_cal)

season_x_episode_pattern = re.compile('(\d+)x(\d+)')


def s00e00(x00x00):
    return 's{0}e{1}'.format(
        x00x00.group(1).zfill(2),
        x00x00.group(2).zfill(2)
    )


def fix_summary(summary):
    splitted = summary.split(' - ')
    series_title = splitted[0]
    episode_title = splitted[1]
    if 'adventure time' in series_title.lower():
        series_title = re.sub(season_x_episode_pattern, '', series_title)
    else:
        series_title = re.sub(season_x_episode_pattern, s00e00, series_title)
        episode_title = ''

    return (series_title + episode_title).strip()


def tvcal(inbox_file):
    to_inbox = []
    for component in cal.walk():
        if 'summary' in component:
            summary = component['summary']
            dt = component['DTSTART'].dt
            fixed_summary = fix_summary(summary)
            if today <= dt <= tommorow and not fixed_summary in inbox_text:
                to_inbox.append(
                    '- ' + fixed_summary +
                    ' @at(' + str(dt) + ') @tvseries'
                )
    if len(to_inbox) > 0:
        to_inbox = '\n'.join(to_inbox)
        print to_inbox
        inbox_file.write('\n' + to_inbox + '\n')

if __name__ == '__main__':
    with open(inbox_path, 'a') as inbox_file:
        tvcal(inbox_file)

########NEW FILE########
__FILENAME__ = update_lists
#!/usr/bin/python
from datetime import date, timedelta
import re
from todoflow import from_file
from todoflow.printers import PlainPrinter
from todoflow.config import days_of_the_week, projects_path, onhold_path, inbox_path, daily_project_title


def update_daily(projects):
    daily = projects.filter('project ? Daily')
    for item in daily:
        if item.type == 'task':
            item.remove_tag('done')
            if not item.has_tag('working'):
                item.tag('working')


def update_weekly(onhold, inbox):
    today = days_of_the_week[date.today().weekday()]
    waiting = onhold.filter('@weekly = ' + today + ' +d')
    txt = PlainPrinter().pformat(waiting)
    inbox.write(txt)
    print txt


def update_waiting(onhold, inbox):
    today = date.today().isoformat()
    waiting = onhold.filter('@waiting <= ' + today + ' +d')
    txt = PlainPrinter().pformat(waiting)
    inbox.write(txt)
    print txt


def update_followups(tasks):
    today = date.today()
    with open(onhold_path, 'a') as f:
        followups = tasks.filter('@followup and @done <= ' + date.today().isoformat())
        for item in followups:
            folowee = item.get_tag_param('@followup')
            if not folowee:
                continue
            days_no_str, folowee_task = folowee.partition(' ')[::2]
            days_no = int(days_no_str)
            when_to_follow = today + timedelta(days=days_no)
            following_param = item.title.get_text_without_tags()
            f.write(
                '- ' + folowee_task + ' @waiting(' + when_to_follow.isoformat() + ') @following(' + following_param + ')\n'
            )


def update_blocked(tasks):
    blockers = tasks.search('@blocker and @done <= ' + date.today().isoformat())
    for blocker in blockers:
        blocker_id = blocker.get_tag_param('@blocker')
        blockeds = tasks.filter('@blocked = ' + blocker_id)
        for blocked in blockeds:
            if blocked.has_tag('@blocked'):
                blocked.remove_tag_with_param('@blocked', blocker_id)


def update_incremental(tasks):
    incrementals = tasks.search('@v')
    for task in incrementals:
        value_int = int(task.get_tag_param('@v'))
        inc = task.get_tag_param('@inc')
        if inc:
            inc_int = int(inc)
            new_value = value_int + inc_int
            task.replace_tag_param('v', str(new_value))


########NEW FILE########
__FILENAME__ = listfiles
import os

def prind(f):
	for filename in os.listdir(f):
		if os.path.isdir(f + filename):
			if not filename.startswith('archive') and filename != 'workflows':
				prind(f + filename + '/')
		elif not filename.endswith('pyc') and not filename.startswith('.'):
			print (f + filename)[1:]

prind('./')


########NEW FILE########
__FILENAME__ = propagate_done
import todoflow

def propagate_tag(item, tag, param=None):
	item.tag(tag, param=param)
	for item in item.sublist:
		propagate_tag(item, tag, param)

t = todoflow.all_lists()
for item in t.search('done'):
	propagate_tag(item, 'done')
todoflow.save(t)

########NEW FILE########
