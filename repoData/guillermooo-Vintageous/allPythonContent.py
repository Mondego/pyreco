__FILENAME__ = build

########NEW FILE########
__FILENAME__ = builder
from fnmatch import fnmatch
from itertools import chain
from zipfile import ZipFile
from zipfile import ZIP_DEFLATED
import argparse
import glob
import json
import os


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
RESERVED = ['manifest.json', 'dist']


parser = argparse.ArgumentParser(
                    description="Builds .sublime-package archives.")
parser.add_argument('-d', dest='target_dir', default='./dist',
                    help="output directory")
parser.add_argument('--release', dest='release', default='dev',
                    help="type of build (e.g. 'dev', 'release'...)")


def get_manifest():
    path = os.path.join(PROJECT_ROOT, 'manifest.json')
    with open(path) as f:
        return json.load(f)


def unwanted(fn, pats):
    return any(fnmatch(fn, pat) for pat in pats + RESERVED)


def ifind_files(patterns):
    for fn in (fn for (pat, exclude) in patterns
                                     for fn in glob.iglob(pat)
                                     if not unwanted(fn, exclude)):
        yield fn


def build(target_dir="dist", release="dev"):
    manifest = get_manifest()
    name = manifest['name'] + '.sublime-package'

    target_dir = os.path.join(PROJECT_ROOT, target_dir)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    target_file = os.path.join(target_dir, name)
    if os.path.exists(target_file):
        os.unlink(target_file)

    with ZipFile(target_file, 'a', compression=ZIP_DEFLATED) as package:
        for fn in ifind_files(manifest['include'][release]):
            package.write(fn)


if __name__ == '__main__':
    args = parser.parse_args()
    build(args.target_dir, args.release)

########NEW FILE########
__FILENAME__ = check
"""
check for common build errors
"""

import json
import os
import sys


_this_dir = os.path.dirname(__file__)
_parent = os.path.realpath(os.path.join(_this_dir, '..'))


def check_messages():
    _messages = os.path.realpath(os.path.join(_parent, 'messages.json'))
    _messages_dir = os.path.realpath(os.path.join(_parent, 'messages'))

    msg_paths = None
    try:
        with open(_messages, 'r') as f:
            msg_paths = json.load(f)
    except Exception as e:
        print('syntax error in messages.json')
        print('=' * 80)
        print(e)
        print('=' * 80)
        sys.exit(1)

    def exists(path):
        if os.path.exists(os.path.join(_parent, path)):
            return True

    def is_name_correct(key, path):
        name = os.path.basename(path)
        return (key == os.path.splitext(name)[0])

    # is there a file for each message?
    for (key, rel_path) in msg_paths.items():
        if not is_name_correct(key, rel_path):
            print('file name not correct: {0} ==> {1}'.format(key, rel_path))
            sys.exit(1)

        if not exists(rel_path):
            print('message file not found: {0}'.format(rel_path))
            sys.exit(1)


if __name__ == '__main__':
    check_messages()

########NEW FILE########
__FILENAME__ = make_version
# import argparse
import glob
import os
import shutil
import json
from subprocess import check_output
from subprocess import PIPE
from datetime import datetime


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)


def report_vcs(path):
    """
    Returns `git` or `hg` depending on the revision control system found under
    @path. Returns `None` if no repository is found.

    @path
      Root directory to start searching for a vcs repository.
    """
    assert os.path.exists(path), 'bad arguments'
    if os.path.exists(os.path.join(path, '.git')):
        return 'git'
    if os.path.exists(os.path.join(path, '.hg')):
        return 'hg'


def get_latest_tag(vcs=None):
    if vcs == 'git':
        try:
            out = check_output(['git', 'describe', '--tags'], shell=True)
        except Exception as e:
            print('git command failed')
            print(e)
            return
        else:
            return out.decode('ascii').rsplit('-', 2)[0]

    raise NotImplementedError('unknown vcs: ' + vcs)


def get_commit_messages(vcs=None, since_tag=None):
    """
    Returns a list of commmit summary lines.

    @vcs
      Name of vcs used: `hg` or `git`.

    @since_tag
      Get messages from this tag to the repo's head.
    """
    assert vcs == 'git', 'unsupported vcs: ' + vcs
    assert since_tag, 'bad arguments'
    try:
        out = check_output(
                    'git log "{0}^{{}}..HEAD" --format=%s'.format(since_tag),
                    shell=True)
    except Exception as e:
        print('git command failed')
        raise
    else:
        return out.decode('utf-8').replace('\r', '').split('\n')


def make_message_file(old_tag, new_tag):
    """
    Creates a new messages/<new_tag>.txt file to announce thew new version.
    """
    # TODO: For now, we simply copy the latest announcement file and use that
    #       as a template.
    try:
        with open(os.path.join(PROJECT_ROOT,
                  'messages/{0}.txt'.format(old_tag)), 'r') as f:
            with open(os.path.join(PROJECT_ROOT,
                      'messages/{0}.txt'.format(new_tag)), 'w') as ff:
                ff.write(f.read())
    except Exception as e:
        print('failed at creating new announcement file under messages/')
        raise e
    else:
        assert os.path.exists(os.path.join(PROJECT_ROOT,
                              'messages/{0}.txt'.format(new_tag))), 'cannot find new announcement file'
        print('created messages/{0}.txt announcement draft'.format(new_tag))


def update_changelog(new_tag):
    assert os.path.exists(os.path.join(PROJECT_ROOT, 'CHANGES.txt')), 'cannot find changelog file'
    path = os.path.join(PROJECT_ROOT, 'CHANGES.txt')
    heading = '{0} - {1}\n\n'.format(new_tag,
                                     datetime.now().strftime("%d-%m-%Y"))

    vcs = report_vcs(PROJECT_ROOT)
    tag = get_latest_tag(vcs)

    try:
        with open(path, 'r') as original:
            try:
                with open(os.path.join(PROJECT_ROOT,
                          'CHANGES_NEW.txt'), 'w') as n:
                    n.write(heading)
                    for line in get_commit_messages(vcs, tag):
                        n.write("\t- [DRAFT] {0}\n".format(line))
                    n.write('\n')
                    n.write(original.read())
            except Exception as e:
                try:
                    os.unlink(os.path.join(PROJECT_ROOT, 'CHANGES_NEW.txt'))
                except:
                    print('could not delete CHANGES_NEW.txt temp fle.')
                finally:
                    raise e
    finally:
        shutil.move(os.path.join(PROJECT_ROOT, 'CHANGES_NEW.txt'),
                    os.path.join(PROJECT_ROOT, 'CHANGES.txt'),)


def increment_version_number(tag, major=False, minor=False, build=True):
    major_label, minor_label, build_label = tag.split('.')
    if major:
        new_tag = '.'.join([major_label, str(int(minor_label) + 1), '0'])
    elif minor:
        new_tag = '.'.join([str(int(minor_label) + 1), '0', '0'])
    elif build:
        new_tag = '.'.join([major_label, minor_label,
                            str(int(build_label) + 1)])
    return new_tag


def update_package_control_files(tag):
    json_data = None
    with open(os.path.join(PROJECT_ROOT, 'messages.json'), 'r') as f:
        json_data = json.load(f)
        json_data[tag] = 'messages/{0}.txt'.format(tag)

    assert json_data is not None, 'expected json data'

    with open(os.path.join(PROJECT_ROOT, 'messages.json'), 'w') as f:
        json.dump(json_data, f, indent=True)


def make_files(major=False, minor=False, build=True):
    tag = get_latest_tag(report_vcs(PROJECT_ROOT))
    new_tag = increment_version_number(tag, major, minor, build)
    make_message_file(tag, new_tag)
    update_changelog(new_tag)
    update_package_control_files(new_tag)


def main():
    vcs = report_vcs(PROJECT_ROOT)
    tag = get_latest_tag(vcs)
    msgs = get_commit_messages(vcs, tag)
    make_files()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = toplist
import argparse
import json
import os
import plistlib


THIS_DIR = os.path.abspath(os.path.dirname(__file__))


parser = argparse.ArgumentParser(
                    description="Builds .tmLanguage files out of .JSON-tmLanguage files.")
parser.add_argument('-s', dest='source',
                    help="source .JSON-tmLanguage file")

def build(source):
    with open(source, 'r') as f:
        json_data = json.load(f)
        plistlib.writePlist(json_data, os.path.splitext(source)[0] + '.tmLanguage')


if __name__ == '__main__':
    args = parser.parse_args()
    if args.source:
        build(args.source)

########NEW FILE########
__FILENAME__ = builder
from fnmatch import fnmatch
from itertools import chain
from zipfile import ZipFile
from zipfile import ZIP_DEFLATED
import argparse
import glob
import json
import os


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
RESERVED = ['manifest.json', 'dist']


def get_manifest():
    path = os.path.join(THIS_DIR, 'manifest.json')
    with open(path) as f:
        return json.load(f)


def unwanted(fn, pats):
    return any(fnmatch(fn, pat) for pat in pats + RESERVED)


def ifind_files(patterns):
    for fn in (fn for (pat, exclude) in patterns
                                     for fn in glob.iglob(pat)
                                     if not unwanted(fn, exclude)):
        yield fn


def build(target_dir="./dist", release="dev"):
    manifest = get_manifest()
    name = manifest['name'] + '.sublime-package'

    target_dir = os.path.join(THIS_DIR, target_dir)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    target_file = os.path.join(target_dir, name)
    if os.path.exists(target_file):
        os.unlink(target_file)

    with ZipFile(target_file, 'a', compression=ZIP_DEFLATED) as package:
        for fn in ifind_files(manifest['include'][release]):
            package.write(fn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        description="Builds .sublime-package archives.")
    parser.add_argument('-d', dest='target_dir', default='./dist',
                        help="output directory")
    parser.add_argument('--release', dest='release', default='dev',
                        help="type of build (e.g. 'dev', 'release'...)")
    args = parser.parse_args()
    build(args.target_dir, args.release)

########NEW FILE########
__FILENAME__ = completions
import sublime
import sublime_plugin

import glob
import os
import re

RX_CMD_LINE_CD = re.compile(r'^(?P<cmd>:\s*cd!?)\s+(?P<path>.*)$')
RX_CMD_LINE_WRITE = re.compile(r'^(?P<cmd>:\s*w(?:rite)?!?)\s+(?P<path>.*)$')
RX_CMD_LINE_EDIT = re.compile(r'^(?P<cmd>:\s*e(?:dit)?!?)\s+(?P<path>.*)$')
RX_CMD_LINE_VSPLIT = re.compile(r'^(?P<cmd>:\s*vs(?:plit)?!?)\s+(?P<path>.*)$')


COMPLETIONS_FILE = 1
COMPLETIONS_DIRECTORY = 2

completion_types = [
    (RX_CMD_LINE_CD, True),
    (RX_CMD_LINE_WRITE, True),
    (RX_CMD_LINE_EDIT, False),
    (RX_CMD_LINE_VSPLIT, False),
]

RX_CMD_LINE_SET_LOCAL = re.compile(r'^(?P<cmd>:\s*setl(?:ocal)?\??)\s+(?P<setting>.*)$')
RX_CMD_LINE_SET_GLOBAL = re.compile(r'^(?P<cmd>:\s*se(?:t)?\??)\s+(?P<setting>.*)$')


completion_settings = [
    (RX_CMD_LINE_SET_LOCAL, None),
    (RX_CMD_LINE_SET_GLOBAL, None),
]


def iter_paths(prefix=None, from_dir=None, only_dirs=False):
    if prefix:
        start_at = os.path.expandvars(os.path.expanduser(prefix))
        # TODO: implement env var completion.
        if not prefix.startswith(('%', '$', '~')):
            start_at = os.path.join(from_dir, prefix)
            start_at = os.path.expandvars(os.path.expanduser(start_at))

        prefix_split = os.path.split(prefix)
        prefix_len = len(prefix_split[1])
        if ('/' in prefix and not prefix_split[0]):
            prefix_len = 0

        for path in glob.iglob(start_at + '*'):
            if not only_dirs or os.path.isdir(path):
                suffix = ('/' if os.path.isdir(path) else '')
                item = os.path.split(path)[1]
                yield prefix + (item + suffix)[prefix_len:]
    else:
        prefix = from_dir
        start_at = os.path.expandvars(os.path.expanduser(prefix))
        stuff = glob.iglob(start_at + "*")
        for path in glob.iglob(start_at + '*'):
            if not only_dirs or os.path.isdir(path):
                yield path[len(start_at):] + ('' if not os.path.isdir(path) else '/')


def parse(text):
    found = None
    for (pattern, only_dirs) in completion_types:
        found = pattern.search(text)
        if found:
            return found.groupdict()['cmd'], found.groupdict()['path'], only_dirs
    return (None, None, None)


def escape(path):
    return path.replace(' ', '\\ ')


def unescape(path):
    return path.replace('\\ ', ' ')


def wants_fs_completions(text):
    return parse(text)[0] is not None


def parse_for_setting(text):
    found = None
    for (pattern, _) in completion_settings:
        found = pattern.search(text)
        if found:
            return found.groupdict()['cmd'], found.groupdict().get('setting'), None
    return (None, None, None)


def wants_setting_completions(text):
    return parse_for_setting(text)[0] is not None

########NEW FILE########
__FILENAME__ = ex_command_parser
"""a simple 'parser' for :ex commands
"""

from collections import namedtuple
import re
from itertools import takewhile

from Vintageous.ex import ex_error
from Vintageous.ex import parsers


# Data used to parse strings into ex commands and map them to an actual
# Sublime Text command.
#
#   command
#       The Sublime Text command to be executed.
#   invocations
#       Tuple of regexes representing valid calls for this command.
#   error_on
#       Tuple of error codes. The parsed command is checked for errors based
#       on this information.
#       For example: on_error=(ex_error.ERR_TRAILING_CHARS,) would make the
#       command fail if it was followed by any arguments.
ex_cmd_data = namedtuple('ex_cmd_data', 'command invocations error_on')

# Holds a parsed ex command data.
# TODO: elaborate on params info.
EX_CMD = namedtuple('ex_command', 'name command forced args parse_errors line_range can_have_range')

# Address that can only appear after a command.
POSTFIX_ADDRESS = r'[.$]|(?:/.*?(?<!\\)/|\?.*?(?<!\\)\?){1,2}|[+-]?\d+|[\'][a-zA-Z0-9<>]'
ADDRESS_OFFSET = r'[-+]\d+'
# Can only appear standalone.
OPENENDED_SEARCH_ADDRESS = r'^[/?].*'

# ** IMPORTANT **
# Vim's documentation on valid addresses is wrong. For postfixed addresses,
# as in :copy10,20, only the left end is parsed and used; the rest is discarded
# and not even errors are thrown if the right end is bogus, like in :copy10XXX.
EX_POSTFIX_ADDRESS = re.compile(
                        r'''(?x)
                            ^(?P<address>
                                (?:
                                 # A postfix address...
                                 (?:%(address)s)
                                 # optionally followed by offsets...
                                 (?:%(offset)s)*
                                )|
                                # or an openended search-based address.
                                %(openended)s
                            )
                        ''' %  {'address':      POSTFIX_ADDRESS,
                                'offset':       ADDRESS_OFFSET,
                                'openended':    OPENENDED_SEARCH_ADDRESS}
                        )


EX_COMMANDS = {
    ('write', 'w'): ex_cmd_data(
                                command='ex_write_file',
                                invocations=(
                                    re.compile(r'^\s*$'),
                                    re.compile(r'(?P<plusplus_args> *\+\+[a-zA-Z0-9_]+)* *(?P<operator>>>) *(?P<target_redirect>.+)?'),
                                    # fixme: raises an error when it shouldn't
                                    re.compile(r'(?P<plusplus_args> *\+\+[a-zA-Z0-9_]+)* *!(?P<subcmd>.+)'),
                                    re.compile(r'(?P<plusplus_args> *\+\+[a-zA-Z0-9_]+)* *(?P<file_name>.+)?'),
                                ),
                                error_on=()
                                ),
    ('wall', 'wa'): ex_cmd_data(
                                command='ex_write_all',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('pwd', 'pw'): ex_cmd_data(
                                command='ex_print_working_dir',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS)
                                ),
    ('buffers', 'buffers'): ex_cmd_data(
                                command='ex_prompt_select_open_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('files', 'files'): ex_cmd_data(
                                command='ex_prompt_select_open_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('ls', 'ls'): ex_cmd_data(
                                command='ex_prompt_select_open_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('registers', 'reg'): ex_cmd_data(
                                command='ex_list_registers',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('map', 'map'): ex_cmd_data(
                                command='ex_map',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('omap', 'omap'): ex_cmd_data(
                                command='ex_omap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('vmap', 'vmap'): ex_cmd_data(
                                command='ex_vmap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('nmap', 'nmap'): ex_cmd_data(
                                command='ex_nmap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('unmap', 'unmap'): ex_cmd_data(
                                command='ex_unmap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('ounmap', 'ounmap'): ex_cmd_data(
                                command='ex_ounmap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('vunmap', 'vunmap'): ex_cmd_data(
                                command='ex_vunmap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('nunmap', 'nunmap'): ex_cmd_data(
                                command='ex_nunmap',
                                invocations=(re.compile(r"(?P<cmd>^.+$)"),),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('abbreviate', 'ab'): ex_cmd_data(
                                command='ex_abbreviate',
                                invocations=(
                                    re.compile(r'^$'),
                                    re.compile(r'^(?P<short>.+?) (?P<full>.+)$'),
                                    ),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('unabbreviate', 'una'): ex_cmd_data(
                                command='ex_unabbreviate',
                                invocations=(
                                    re.compile(r'^(?P<short>.+)$'),
                                    ),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('quit', 'q'): ex_cmd_data(
                                command='ex_quit',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('qall', 'qa'): ex_cmd_data(
                                command='ex_quit_all',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    # TODO: add invocations
    ('wq', 'wq'): ex_cmd_data(
                                command='ex_write_and_quit',
                                invocations=(),
                                error_on=()
                                ),
    ('read', 'r'): ex_cmd_data(
                                command='ex_read_shell_out',
                                invocations=(
                                    # xxx: works more or less by chance. fix the command code
                                    re.compile(r'(?P<plusplus> *\+\+[a-zA-Z0-9_]+)* *(?P<name>.+)'),
                                    re.compile(r' *!(?P<name>.+)'),
                                ),
                                # fixme: add error category for ARGS_REQUIRED
                                error_on=()
                                ),
    ('enew', 'ene'): ex_cmd_data(
                                command='ex_new_file',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('ascii', 'as'): ex_cmd_data(
                                # This command is implemented in Packages/Vintage.
                                command='show_ascii_info',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS)
                                ),
    # vim help doesn't say this command takes any args, but it does
    ('file', 'f'): ex_cmd_data(
                                command='ex_file',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('move', 'move'): ex_cmd_data(
                                command='ex_move',
                                invocations=(
                                   EX_POSTFIX_ADDRESS,
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_ADDRESS_REQUIRED,)
                                ),
    ('copy', 'co'): ex_cmd_data(
                                command='ex_copy',
                                invocations=(
                                   EX_POSTFIX_ADDRESS,
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_ADDRESS_REQUIRED,)
                                ),
    ('t', 't'): ex_cmd_data(
                                command='ex_copy',
                                invocations=(
                                   EX_POSTFIX_ADDRESS,
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_ADDRESS_REQUIRED,)
                                ),
    ('substitute', 's'): ex_cmd_data(
                                command='ex_substitute',
                                invocations=(re.compile(r'(?P<pattern>.+)'),
                                ),
                                error_on=()
                                ),
    ('&&', '&&'): ex_cmd_data(
                                command='ex_double_ampersand',
                                # We don't want to mantain flag values here, so accept anything and
                                # let :substitute handle the values.
                                invocations=(re.compile(r'(?P<flags>.+?)\s*(?P<count>[0-9]+)'),
                                             re.compile(r'\s*(?P<flags>.+?)\s*'),
                                             re.compile(r'\s*(?P<count>[0-9]+)\s*'),
                                             re.compile(r'^$'),
                                ),
                                error_on=()
                                ),
    ('shell', 'sh'): ex_cmd_data(
                                command='ex_shell',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS),
                                ),
    ('vsplit', 'vs'): ex_cmd_data(
                                command='ex_vsplit',
                                invocations=(
                                    re.compile(r'^$'),
                                    re.compile(r'^\s*(?P<file_name>.+)$'),
                                ),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('unvsplit', 'unvsplit'): ex_cmd_data(
                                command='ex_unvsplit',
                                invocations=(
                                    re.compile(r'^$'),
                                ),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS,)
                                ),
    ('delete', 'd'): ex_cmd_data(
                                command='ex_delete',
                                invocations=(
                                    re.compile(r' *(?P<register>[a-zA-Z0-9])? *(?P<count>\d+)?'),
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('global', 'g'): ex_cmd_data(
                                command='ex_global',
                                invocations=(
                                    re.compile(r'(?P<pattern>.+)'),
                                ),
                                error_on=()
                                ),
    ('print', 'p'): ex_cmd_data(
                                command='ex_print',
                                invocations=(
                                    re.compile(r'\s*(?P<count>\d+)?\s*(?P<flags>[l#p]+)?'),
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('Print', 'P'): ex_cmd_data(
                                command='ex_print',
                                invocations=(
                                    re.compile(r'\s*(?P<count>\d+)?\s*(?P<flags>[l#p]+)?'),
                                ),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    ('browse', 'bro'): ex_cmd_data(
                                command='ex_browse',
                                invocations=(),
                                error_on=(ex_error.ERR_NO_BANG_ALLOWED,
                                          ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_TRAILING_CHARS,)
                                ),
    ('edit', 'e'): ex_cmd_data(
                                command='ex_edit',
                                invocations=(re.compile(r"^$"),
                                             re.compile(r"^(?P<file_name>.+)$"),
                                ),
                                error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('cquit', 'cq'): ex_cmd_data(
                                command='ex_cquit',
                                invocations=(),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,
                                          ex_error.ERR_NO_BANG_ALLOWED,)
                                ),
    # TODO: implement all arguments, etc.
    ('xit', 'x'): ex_cmd_data(
                                command='ex_exit',
                                invocations=(),
                                error_on=()
                                ),
    # TODO: implement all arguments, etc.
    ('exit', 'exi'): ex_cmd_data(
                                command='ex_exit',
                                invocations=(),
                                error_on=()
                                ),
    ('only', 'on'): ex_cmd_data(
                                command='ex_only',
                                invocations=(re.compile(r'^$'),),
                                error_on=(ex_error.ERR_TRAILING_CHARS,
                                          ex_error.ERR_NO_RANGE_ALLOWED,)
                                ),
    ('new', 'new'): ex_cmd_data(
                                command='ex_new',
                                invocations=(re.compile(r'^$',),
                                ),
                                error_on=(ex_error.ERR_TRAILING_CHARS,)
                                ),
    ('yank', 'y'): ex_cmd_data(
                                command='ex_yank',
                                invocations=(re.compile(r'^(?P<register>\d|[a-z])$'),
                                             re.compile(r'^(?P<register>\d|[a-z]) (?P<count>\d+)$'),
                                ),
                                error_on=(),
                                ),
    (':', ':'): ex_cmd_data(
                        command='ex_goto',
                        invocations=(re.compile(r'^$'),
                        ),
                        error_on=(),
                        ),
    ('!', '!'): ex_cmd_data(
                        command='ex_shell_out',
                        invocations=(
                                re.compile(r'(?P<shell_cmd>.+)$'),
                        ),
                        # FIXME: :!! is a different command to :!
                        error_on=(ex_error.ERR_NO_BANG_ALLOWED,),
                        ),

    # Use buffer commands to switch tabs
    ('bprevious', 'bp'): ex_cmd_data(command='ex_tab_prev',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('bnext', 'bn'): ex_cmd_data(command='ex_tab_next',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),

    ('tabedit', 'tabe'): ex_cmd_data(
                                    command='ex_tab_open',
                                    invocations=(
                                        re.compile(r'^(?P<file_name>.+)$'),
                                    ),
                                    error_on=(ex_error.ERR_NO_RANGE_ALLOWED,),
                                    ),
    ('tabnext', 'tabn'): ex_cmd_data(command='ex_tab_next',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tabprev', 'tabp'): ex_cmd_data(command='ex_tab_prev',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tabfirst', 'tabf'): ex_cmd_data(command='ex_tab_first',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tablast', 'tabl'): ex_cmd_data(command='ex_tab_last',
                                     invocations=(),
                                     error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                     ),
    ('tabonly', 'tabo'): ex_cmd_data(command='ex_tab_only',
                                     invocations=(),
                                     error_on=(
                                        ex_error.ERR_NO_RANGE_ALLOWED,
                                        ex_error.ERR_TRAILING_CHARS,)
                                     ),
    ('cd', 'cd'): ex_cmd_data(command='ex_cd',
                              invocations=(re.compile(r'^$'),
                                           re.compile(r'^(?P<path>.+)$'),
                              ),
                              error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                              ),

    ('cdd', 'cdd'): ex_cmd_data(command='ex_cdd',
                              invocations=(re.compile(r'^(?P<path>.+)$'),),
                              error_on=(ex_error.ERR_NO_RANGE_ALLOWED,
                                        ex_error.ERR_TRAILING_CHARS,)
                              ),
    ('setlocal', 'setl'): ex_cmd_data(command='ex_set_local',
                                  invocations=(re.compile(r'^(?P<option>\w+\??)(?:(?P<operator>[+-^]?=)(?P<value>.*))?$'),),
                                  error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                  ),
    ('set', 'se'): ex_cmd_data(command='ex_set',
                                  invocations=(re.compile(r'^(?P<option>\w+\??)(?:(?P<operator>[+-^]?=)(?P<value>.*))?$'),),
                                  error_on=(ex_error.ERR_NO_RANGE_ALLOWED,)
                                  ),
}


def find_command(cmd_name):
    partial_matches = [name for name in EX_COMMANDS.keys()
                                            if name[0].startswith(cmd_name)]
    if not partial_matches: return None
    full_match = [(ln, sh) for (ln, sh) in partial_matches
                                                if cmd_name in (ln, sh)]
    if full_match:
        return full_match[0]
    else:
        return partial_matches[0]


def parse_command(cmd):
    cmd_name = cmd.strip()
    if len(cmd_name) > 1:
        cmd_name = cmd_name[1:]
    elif not cmd_name == ':':
        return None

    parser = parsers.cmd_line.CommandLineParser(cmd[1:])
    r_ = parser.parse_cmd_line()

    command = r_['commands'][0]['cmd']
    bang = r_['commands'][0]['forced']
    args = r_['commands'][0]['args']
    cmd_data = find_command(command)
    if not cmd_data:
        return
    cmd_data = EX_COMMANDS[cmd_data]
    can_have_range = ex_error.ERR_NO_RANGE_ALLOWED not in cmd_data.error_on

    cmd_args = {}
    for pattern in cmd_data.invocations:
        found_args = pattern.search(args)
        if found_args:
            found_args = found_args.groupdict()
            # get rid of unset arguments so they don't clobber defaults
            found_args = dict((k, v) for k, v in found_args.items() if v is not None)
            cmd_args.update(found_args)
            break

    parse_errors = []
    for err in cmd_data.error_on:
        if err == ex_error.ERR_NO_BANG_ALLOWED and bang:
            parse_errors.append(ex_error.ERR_NO_BANG_ALLOWED)
        if err == ex_error.ERR_TRAILING_CHARS and args:
            parse_errors.append(ex_error.ERR_TRAILING_CHARS)
        if err == ex_error.ERR_NO_RANGE_ALLOWED and r_['range']['text_range']:
            parse_errors.append(ex_error.ERR_NO_RANGE_ALLOWED)
        if err == ex_error.ERR_INVALID_RANGE and not cmd_args:
            parse_errors.append(ex_error.ERR_INVALID_RANGE)
        if err == ex_error.ERR_ADDRESS_REQUIRED and not cmd_args:
            parse_errors.append(ex_error.ERR_ADDRESS_REQUIRED)

    return EX_CMD(name=command,
                    command=cmd_data.command,
                    forced=bang,
                    args=cmd_args,
                    parse_errors=parse_errors,
                    line_range=r_['range'],
                    can_have_range=can_have_range,)

########NEW FILE########
__FILENAME__ = ex_error
"""
This module lists error codes and error display messages along with
utilities to handle them.
"""

import sublime


ERR_UNKNOWN_COMMAND = 492 # Command can't take arguments.
ERR_TRAILING_CHARS = 488 # Unknown command.
ERR_NO_BANG_ALLOWED = 477 # Command doesn't allow !.
ERR_INVALID_RANGE = 16 # Invalid range.
ERR_INVALID_ADDRESS = 14 # Invalid range.
ERR_NO_RANGE_ALLOWED = 481 # Command can't take a range.
ERR_UNSAVED_CHANGES = 37 # The buffer has been modified but not saved.
ERR_ADDRESS_REQUIRED = 14 # Command needs an address.
ERR_OTHER_BUFFER_HAS_CHANGES = 445 # :only, for example, may trigger this
ERR_CANT_MOVE_LINES_ONTO_THEMSELVES = 134
ERR_CANT_FIND_DIR_IN_CDPATH = 344


ERR_MESSAGES = {
    ERR_TRAILING_CHARS: 'Traling characters.',
    ERR_UNKNOWN_COMMAND: 'Not an editor command.',
    ERR_NO_BANG_ALLOWED: 'No ! allowed.',
    ERR_INVALID_RANGE: 'Invalid range.',
    ERR_INVALID_ADDRESS: 'Invalid address.',
    ERR_NO_RANGE_ALLOWED: 'No range allowed.',
    ERR_UNSAVED_CHANGES: 'There are unsaved changes.',
    ERR_ADDRESS_REQUIRED: 'Invalid address.',
    ERR_OTHER_BUFFER_HAS_CHANGES: "Other buffer contains changes.",
    ERR_CANT_MOVE_LINES_ONTO_THEMSELVES: "Move lines into themselves.",
    ERR_CANT_FIND_DIR_IN_CDPATH: "Can't fin directory in 'cdpath'.",
}


def get_error_message(error_code):
    return ERR_MESSAGES.get(error_code, '')


def display_error(error_code, arg='', log=False):
    err_fmt = "Vintageous: E%d %s"
    if arg:
        err_fmt += " (%s)" % arg
    msg = get_error_message(error_code)
    sublime.status_message(err_fmt % (error_code, msg))


def handle_not_implemented():
    sublime.status_message('Vintageous: Not implemented')

########NEW FILE########
__FILENAME__ = ex_location
import sublime

# from Vintageous.ex_range import calculate_relative_ref

def get_line_nr(view, point):
    """Return 1-based line number for `point`.
    """
    return view.rowcol(point)[0] + 1


# TODO: Move this to sublime_lib; make it accept a point or a region.
def find_eol(view, point):
    return view.line(point).end()


# TODO: Move this to sublime_lib; make it accept a point or a region.
def find_bol(view, point):
    return view.line(point).begin()


# TODO: make this return None for failures.
def find_line(view, start=0, end=-1, target=0):
    """Do binary search to find :target: line number.

    Return: If `target` is found, `Region` comprising entire line no. `target`.
            If `target`is not found, `-1`.
    """

    # Don't bother if sought line is beyond buffer boundaries.
    if  target < 0 or target > view.rowcol(view.size())[0] + 1:
        return -1

    if end == -1:
        end = view.size()

    lo, hi = start, end
    while lo <= hi:
        middle = lo + (hi - lo) / 2
        if get_line_nr(view, middle) < target:
            lo = find_eol(view, middle) + 1
        elif get_line_nr(view, middle) > target:
            hi = find_bol(view, middle) - 1
        else:
            return view.full_line(middle)
    return -1


def search_in_range(view, what, start, end, flags=0):
    match = view.find(what, start, flags)
    if match and ((match.begin() >= start) and (match.end() <= end)):
        return True


def find_last_match(view, what, start, end, flags=0):
    """Find last occurrence of `what` between `start`, `end`.
    """
    match = view.find(what, start, flags)
    new_match = None
    while match:
        new_match = view.find(what, match.end(), flags)
        if new_match and new_match.end() <= end:
            match = new_match
        else:
            return match


def reverse_search(view, what, start=0, end=-1, flags=0):
    """Do binary search to find `what` walking backwards in the buffer.
    """
    if end == -1:
        end = view.size()
    end = find_eol(view, view.line(end).a)

    last_match = None

    lo, hi = start, end
    while True:
        middle = (lo + hi) / 2
        line = view.line(middle)
        middle, eol = find_bol(view, line.a), find_eol(view, line.a)

        if search_in_range(view, what, middle, hi, flags):
            lo = middle
        elif search_in_range(view, what, lo, middle - 1, flags):
            hi = middle -1
        else:
            return calculate_relative_ref(view, '.')

        # Don't search forever the same line.
        if last_match and line.contains(last_match):
            match = find_last_match(view, what, lo, hi, flags=flags)
            return view.rowcol(match.begin())[0] + 1

        last_match = sublime.Region(line.begin(), line.end())


def search(view, what, start_line=None, flags=0):
    # TODO: don't make start_line default to the first sel's begin(). It's
    # confusing. ???
    if start_line:
        start = view.text_point(start_line, 0)
    else:
        start = view.sel()[0].begin()
    reg = view.find(what, start, flags)
    if not reg is None:
        row = (view.rowcol(reg.begin())[0] + 1)
    else:
        row = calculate_relative_ref(view, '.', start_line=start_line)
    return row

########NEW FILE########
__FILENAME__ = ex_range
"""helpers to manage :ex mode ranges
"""

from collections import namedtuple
import sublime


class VimRange(object):
    """Encapsulates calculation of view regions based on supplied raw range info.
    """
    def __init__(self, view, range_info, default=None):
        self.view = view
        self.default = default
        self.range_info = range_info

    def blocks(self):
        """Returns a list of blocks potentially encompassing multiple lines.
        Returned blocks don't end in a newline char.
        """
        regions, visual_regions = new_calculate_range(self.view, self.range_info)
        blocks = []
        for a, b in regions:
            r = sublime.Region(self.view.text_point(a - 1, 0),
                               self.view.line(self.view.text_point(b - 1, 0)).end())
            if self.view.substr(r) == '':
                pass
            elif self.view.substr(r)[-1] == "\n":
                if r.begin() != r.end():
                    r = sublime.Region(r.begin(), r.end() - 1)
            blocks.append(r)
        return blocks

    def lines(self):
        """Return a list of lines.
        Returned lines don't end in a newline char.
        """
        lines = []
        for block in self.blocks():
            lines.extend(self.view.split_by_newlines(block))
        return lines


EX_RANGE = namedtuple('ex_range', 'left left_offset separator right right_offset')


def calculate_relative_ref(view, where, start_line=None):
    if where == '$':
        return view.rowcol(view.size())[0] + 1
    if where == '.':
        if start_line:
            return view.rowcol(view.text_point(start_line, 0))[0] + 1
        return view.rowcol(view.sel()[0].begin())[0] + 1


def new_calculate_search_offsets(view, searches, start_line):
    last_line = start_line
    for search in searches:
        if search[0] == '/':
            last_line = ex_location.search(view, search[1], start_line=last_line)
        elif search[0] == '?':
            end = view.line(view.text_point(start_line, 0)).end()
            last_line = ex_location.reverse_search(view, search[1], end=end)
        last_line += search[2]
    return last_line


def calculate_address(view, a):
    fake_range = dict(left_ref=a['ref'],
                      left_offset=a['offset'],
                      left_search_offsets=a['search_offsets'],
                      sep=None,
                      right_ref=None,
                      right_offset=None,
                      right_search_offsets=[]
                      # todo: 'text_range' key missing
                    )

    a, _ =  new_calculate_range(view, fake_range)[0][0] or -1
    # FIXME: 0 should be a valid address?
    if not (0 < a <= view.rowcol(view.size())[0] + 1):
        return None
    return a - 1


def new_calculate_range(view, r):
    """Calculates line-based ranges (begin_row, end_row) and returns
    a tuple: a list of ranges and a boolean indicating whether the ranges
    where calculated based on a visual selection.
    """

    # FIXME: make sure this works with whitespace between markers, and doublecheck
    # with Vim to see whether '<;>' is allowed.
    # '<,>' returns all selected line blocks
    if r['left_ref'] == "'<" and r['right_ref'] == "'>":
        all_line_blocks = []
        for sel in view.sel():
            start = view.rowcol(sel.begin())[0] + 1
            end = view.rowcol(sel.end())[0] + 1
            if view.substr(sel.end() - 1) == '\n':
                end -= 1
            all_line_blocks.append((start, end))
        return all_line_blocks, True

    # todo: '< and other marks
    if r['left_ref'] and (r['left_ref'].startswith("'") or (r['right_ref'] and r['right_ref'].startswith("'"))):
        return []

    # todo: don't mess up with the received ranged. Also, % has some strange
    # behaviors that should be easy to replicate.
    if r['left_ref'] == '%' or r['right_ref'] == '%':
        r['left_offset'] = 1
        r['right_ref'] = '$'

    current_line = None
    lr = r['left_ref']
    if lr is not None:
        current_line = calculate_relative_ref(view, lr)
    loffset = r['left_offset']
    if loffset:
        current_line = current_line or 0
        current_line += loffset

    searches = r['left_search_offsets']
    if searches:
        current_line = new_calculate_search_offsets(view, searches, current_line or calculate_relative_ref(view, '.'))
    left = current_line

    current_line = None
    rr = r['right_ref']
    if rr is not None:
        current_line = calculate_relative_ref(view, rr)
    roffset = r['right_offset']
    if roffset:
        current_line = current_line or 0
        current_line += roffset

    searches = r['right_search_offsets']
    if searches:
        current_line = new_calculate_search_offsets(view, searches, current_line or calculate_relative_ref(view, '.'))
    right = current_line

    if not right:
        right = left

    # todo: move this to the parsing phase? Do all vim commands default to '.' as a range?
    if not any([left, right]):
        left = right = calculate_relative_ref(view, '.')

    # todo: reverse range automatically if needed
    return [(left, right)], False

# Avoid circular import.
# from vex import ex_location

########NEW FILE########
__FILENAME__ = cmd_line
import re

EOF = -1

COMMA = ','
SEMICOLON = ';'
LINE_REF_SEPARATORS = (COMMA, SEMICOLON)

default_range_info = dict(left_ref=None,
                          left_offset=None,
                          left_search_offsets=[],
                          separator=None,
                          right_ref=None,
                          right_offset=None,
                          right_search_offsets=[],
                          text_range='')


class ParserBase(object):
    def __init__(self, source):
        self.c = ''
        self.source = source
        self.result = default_range_info.copy()
        self.n = -1
        self.consume()

    def consume(self):
        if self.c == EOF:
            raise SyntaxError("End of file reached.")
        if self.n == -1 and not self.source:
            self.c = EOF
            return
        else:
            self.n += 1
            if self.n >= len(self.source):
                self.c = EOF
                return
            self.c = self.source[self.n]


class VimParser(ParserBase):
    STATE_NEUTRAL = 0
    STATE_SEARCH_OFFSET = 1

    def __init__(self, *args, **kwargs):
        self.state = VimParser.STATE_NEUTRAL
        self.current_side = 'left'
        ParserBase.__init__(self, *args, **kwargs)

    def parse_full_range(self):
        # todo: make sure that parse_range throws error for unknown tokens
        self.parse_range()
        sep = self.match_one(',;')
        if sep:
            if not self.result[self.current_side + '_offset'] and not self.result[self.current_side + '_ref']:
                self.result[self.current_side + '_ref'] = '.'
            self.consume()
            self.result['separator'] = sep
            self.current_side = 'right'
            self.parse_range()

        if self.c != EOF and not (self.c.isalpha() or self.c in '&!'):
            raise SyntaxError("E492 Not an editor command.")

        return self.result

    def parse_range(self):
        if self.c == EOF:
            return self.result
        line_ref = self.consume_if_in(list('.%$'))
        if line_ref:
            self.result[self.current_side + "_ref"] = line_ref
        while self.c != EOF:
            if self.c == "'":
                self.consume()
                if self.c != EOF and not (self.c.isalpha() or self.c in ("<", ">")):
                    raise SyntaxError("E492 Not an editor command.")
                self.result[self.current_side + "_ref"] = "'%s" % self.c
                self.consume()
            elif self.c in ".$%%'" and not self.result[self.current_side + "_ref"]:
                if (self.result[self.current_side + "_search_offsets"] or
                    self.result[self.current_side + "_offset"]):
                        raise SyntaxError("E492 Not an editor command.")
            elif self.c.startswith(tuple("01234567890+-")):
                offset = self.match_offset()
                self.result[self.current_side + '_offset'] = offset
            elif self.c.startswith(tuple('/?')):
                self.state = VimParser.STATE_SEARCH_OFFSET
                search_offests = self.match_search_based_offsets()
                self.result[self.current_side + "_search_offsets"] = search_offests
                self.state = VimParser.STATE_NEUTRAL
            elif self.c not in ':,;&!' and not self.c.isalpha():
                raise SyntaxError("E492 Not an editor command.")
            else:
                break

            if (self.result[self.current_side + "_ref"] == '%' and
                (self.result[self.current_side + "_offset"] or
                 self.result[self.current_side + "_search_offsets"])):
                    raise SyntaxError("E492 Not an editor command.")

        end = max(0, min(self.n, len(self.source)))
        self.result['text_range'] = self.source[:end]
        return self.result

    def consume_if_in(self, items):
        rv = None
        if self.c in items:
            rv = self.c
            self.consume()
        return rv

    def match_search_based_offsets(self):
        offsets = []
        while self.c != EOF and self.c.startswith(tuple('/?')):
            new_offset = []
            new_offset.append(self.c)
            search = self.match_one_search_offset()
            new_offset.append(search)
            # numeric_offset = self.consume_while_match('^[0-9+-]') or '0'
            numeric_offset = self.match_offset()
            new_offset.append(numeric_offset)
            offsets.append(new_offset)
        return offsets

    def match_one_search_offset(self):
        search_kind = self.c
        rv = ''
        self.consume()
        while self.c != EOF and self.c != search_kind:
            if self.c == '\\':
                self.consume()
                if self.c != EOF:
                    rv += self.c
                    self.consume()
            else:
                rv += self.c
                self.consume()
        if self.c == search_kind:
            self.consume()
        return rv

    def match_offset(self):
        offsets = []
        sign = 1
        is_num_or_sign = re.compile('^[0-9+-]')
        while self.c != EOF and is_num_or_sign.match(self.c):
            if self.c in '+-':
                signs = self.consume_while_match('^[+-]')
                if self.state == VimParser.STATE_NEUTRAL and len(signs) > 1 and not self.result[self.current_side + '_ref']:
                    self.result[self.current_side + '_ref'] = '.'
                if self.c != EOF and self.c.isdigit():
                    if self.state == VimParser.STATE_NEUTRAL and not self.result[self.current_side + '_ref']:
                        self.result[self.current_side + '_ref'] = '.'
                    sign = -1 if signs[-1] == '-' else 1
                    signs = signs[:-1] if signs else []
                subtotal = 0
                for item in signs:
                    subtotal += 1 if item == '+' else -1
                offsets.append(subtotal)
            elif self.c.isdigit():
                nr = self.consume_while_match('^[0-9]')
                offsets.append(sign * int(nr))
                sign = 1
            else:
                break

        return sum(offsets)
        # self.result[self.current_side + '_offset'] = sum(offsets)

    def match_one(self, seq):
        if self.c != EOF and self.c in seq:
            return self.c


    def consume_while_match(self, regex):
        rv = ''
        r = re.compile(regex)
        while self.c != EOF and r.match(self.c):
            rv += self.c
            self.consume()
        return rv


class CommandLineParser(ParserBase):
    def __init__(self, source, *args, **kwargs):
        ParserBase.__init__(self, source, *args, **kwargs)
        self.range_parser = VimParser(source)
        self.result = dict(range=None, commands=[], errors=[])

    def parse_cmd_line(self):
        try:
            rng = self.range_parser.parse_full_range()
        except SyntaxError as e:
            rng = None
            self.result["errors"].append(str(e))
            return self.result

        self.result['range'] = rng
        # sync up with range parser the dumb way
        self.n = self.range_parser.n
        self.c = self.range_parser.c
        while self.c != EOF and self.c == ' ':
            self.consume()
        self.parse_commands()

        if not self.result['commands'][0]['cmd']:
            self.result['commands'][0]['cmd'] = ':'
        return self.result

    def parse_commands(self):
        name = ''
        cmd = {}
        while self.c != EOF:
            if self.c.isalpha() and '&' not in name:
                name += self.c
                self.consume()
            elif self.c == '&' and (not name or name == '&'):
                name += self.c
                self.consume()
            else:
                break

        if not name and self.c  == '!':
            name = '!'
            self.consume()

        cmd['cmd'] = name
        cmd['forced'] = self.c == '!'
        if cmd['forced']:
            self.consume()

        while self.c != EOF and self.c == ' ':
            self.consume()
        cmd['args'] = ''
        if not self.c == EOF:
            cmd['args'] = self.source[self.n:]
        self.result['commands'].append(cmd)


class AddressParser(ParserBase):
    STATE_NEUTRAL = 1
    STATE_SEARCH_OFFSET = 2

    def __init__(self, source, *args, **kwargs):
        ParserBase.__init__(self, source, *args, **kwargs)
        self.result = dict(ref=None, offset=None, search_offsets=[])
        self.state = AddressParser.STATE_NEUTRAL

    def parse(self):
        if self.c == EOF:
            return self.result
        ref = self.consume_if_in(list('.$'))
        if ref:
            self.result["ref"] = ref

        while self.c != EOF:
            if self.c in '0123456789+-':
                rv = self.match_offset()
                self.result['offset'] = rv
            elif self.c in '?/':
                rv = self.match_search_based_offsets()
                self.result['search_offsets'] = rv

        return self.result

    def match_search_based_offsets(self):
        offsets = []
        while self.c != EOF and self.c.startswith(tuple('/?')):
            new_offset = []
            new_offset.append(self.c)
            search = self.match_one_search_offset()
            new_offset.append(search)
            # numeric_offset = self.consume_while_match('^[0-9+-]') or '0'
            numeric_offset = self.match_offset()
            new_offset.append(numeric_offset)
            offsets.append(new_offset)
        return offsets

    def match_one_search_offset(self):
        search_kind = self.c
        rv = ''
        self.consume()
        while self.c != EOF and self.c != search_kind:
            if self.c == '\\':
                self.consume()
                if self.c != EOF:
                    rv += self.c
                    self.consume()
            else:
                rv += self.c
                self.consume()
        if self.c == search_kind:
            self.consume()
        return rv

    def match_offset(self):
        offsets = []
        sign = 1
        is_num_or_sign = re.compile('^[0-9+-]')
        while self.c != EOF and is_num_or_sign.match(self.c):
            if self.c in '+-':
                signs = self.consume_while_match('^[+-]')
                if self.state == AddressParser.STATE_NEUTRAL and len(signs) > 0 and not self.result['ref']:
                    self.result['ref'] = '.'
                if self.c != EOF and self.c.isdigit():
                    sign = -1 if signs[-1] == '-' else 1
                    signs = signs[:-1] if signs else []
                subtotal = 0
                for item in signs:
                    subtotal += 1 if item == '+' else -1
                offsets.append(subtotal)
            elif self.c.isdigit():
                nr = self.consume_while_match('^[0-9]')
                offsets.append(sign * int(nr))
                sign = 1
            else:
                break

        return sum(offsets)

    def match_one(self, seq):
        if self.c != EOF and self.c in seq:
            return self.c


    def consume_while_match(self, regex):
        rv = ''
        r = re.compile(regex)
        while self.c != EOF and r.match(self.c):
            rv += self.c
            self.consume()
        return rv

    def consume_if_in(self, items):
        rv = None
        if self.c in items:
            rv = self.c
            self.consume()
        return rv

########NEW FILE########
__FILENAME__ = g_cmd
from Vintageous.ex.parsers.parsing import RegexToken
from Vintageous.ex.parsers.parsing import Lexer
from Vintageous.ex.parsers.parsing import EOF


class GlobalLexer(Lexer):
    DELIMITER = RegexToken(r'[^a-zA-Z0-9 ]')
    WHITE_SPACE = ' \t'

    def __init__(self):
        self.delimiter = None

    def _match_white_space(self):
        while self.c != EOF and self.c in self.WHITE_SPACE:
            self.consume()

    def _match_pattern(self):
        buf = []
        while self.c != EOF and self.c != self.delimiter:
            if self.c == '\\':
                buf.append(self.c)
                self.consume()
                if self.c in '\\':
                    # Don't store anything, we're escaping \.
                    self.consume()
                elif self.c == self.delimiter:
                    # Overwrite the \ we've just stored.
                    buf[-1] = self.delimiter
                    self.consume()

                if self.c == EOF:
                    break
            else:
                buf.append(self.c)
                self.consume()

        return ''.join(buf)

    def _parse_long(self):
        buf = []

        self.delimiter = self.c
        self.consume()

        buf.append(self._match_pattern())

        self.consume()
        buf.append(self.string[self.cursor:])

        return buf

    def _do_parse(self):
        if not self.c in self.DELIMITER:
            raise SyntaxError("expected delimiter, got '%s'" % self.c)
        return self._parse_long()


def split(s):
    return GlobalLexer().parse(s)

########NEW FILE########
__FILENAME__ = parsing
import re

EOF = -1


class Lexer(object):
    def __init__(self):
        self.c = None # current character
        self.cursor = 0
        self.string = None

    def _reset(self):
        self.c = None
        self.cursor = 0
        self.string = None

    def consume(self):
        self.cursor += 1
        if self.cursor >= len(self.string):
            self.c = EOF
        else:
            self.c = self.string[self.cursor]

    def _do_parse(self):
        pass

    def parse(self, string):
        if not isinstance(string, str):
            raise TypeError("Can only parse strings.")
        self._reset()
        self.string = string
        if not string:
            self.c = EOF
        else:
            self.c = string[0]
        return self._do_parse()


class RegexToken(object):
    def __init__(self, value):
        self.regex = re.compile(value)

    def __contains__(self, value):
        return self.__eq__(value)

    def __eq__(self, other):
        return bool(self.regex.match(other))

########NEW FILE########
__FILENAME__ = s_cmd
from Vintageous.ex.parsers.parsing import RegexToken
from Vintageous.ex.parsers.parsing import Lexer
from Vintageous.ex.parsers.parsing import EOF


class SubstituteLexer(Lexer):
    DELIMITER = RegexToken(r'[^a-zA-Z0-9 ]')
    WHITE_SPACE = ' \t'
    FLAG = 'giI'

    def __init__(self):
        self.delimiter = None

    def _match_white_space(self):
        while self.c != EOF and self.c in self.WHITE_SPACE:
            self.consume()

    def _match_count(self):
        buf = []
        while self.c != EOF and self.c.isdigit():
            buf.append(self.c)
            self.consume()
        return ''.join(buf)

    def _match_flags(self):
        buf = []
        while self.c != EOF and self.c in self.FLAG:
            if self.c in self.FLAG:
                buf.append(self.c)
            self.consume()
        return ''.join(buf)

    def _match_pattern(self):
        buf = []
        while self.c != EOF and self.c != self.delimiter:
            if self.c == '\\':
                buf.append(self.c)
                self.consume()
                if self.c in '\\':
                    # Don't store anything, we're escaping \.
                    self.consume()
                elif self.c == self.delimiter:
                    # Overwrite the \ we've just stored.
                    buf[-1] = self.delimiter
                    self.consume()

                if self.c == EOF:
                    break
            else:
                buf.append(self.c)
                self.consume()

        return ''.join(buf)

    def _parse_short(self):
        buf = []
        if self.c == EOF:
            return ['', ''] # no flags, no count

        if self.c.isalpha():
            buf.append(self._match_flags())
            self._match_white_space()
        else:
            buf.append('')

        if self.c != EOF and self.c.isdigit():
            buf.append(self._match_count())
            self._match_white_space()
        else:
            buf.append('')

        if self.c != EOF:
            raise SyntaxError("Trailing characters.")

        return buf

    def _parse_long(self):
        buf = []

        self.delimiter = self.c
        self.consume()

        if self.c == EOF:
            return ['', '', '', '']

        buf.append(self._match_pattern())

        if self.c != EOF:
            # We're at a separator now --we MUST be.
            self.consume()
            buf.append(self._match_pattern())
        else:
            buf.append('')

        if self.c != EOF:
            self.consume()

        if self.c != EOF and self.c in self.FLAG:
            buf.append(self._match_flags())
        else:
            buf.append('')

        if self.c != EOF:
            self._match_white_space()
            buf.append(self._match_count())
        else:
            buf.append('')

        self._match_white_space()
        if self.c != EOF:
            raise SyntaxError("Trailing characters.")

        return buf

    def _do_parse(self):
        self._match_white_space()
        if self.c != EOF and self.c in self.DELIMITER:
            return self._parse_long()
        else:
            return self._parse_short()


def split(s):
    return SubstituteLexer().parse(s)

########NEW FILE########
__FILENAME__ = test_cmdline
import unittest
from Vintageous.ex.parsers import cmd_line


class ParserBase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.parser = cmd_line.ParserBase("foo")

    def testIsInitCorrect(self):
        self.assertEqual(self.parser.source, "foo")
        self.assertEqual(self.parser.c, "f")

    def testCanConsume(self):
        rv = []
        while self.parser.c != cmd_line.EOF:
            rv.append(self.parser.c)
            self.parser.consume()
        self.assertEqual(rv, list("foo"))

    def testCanConsumeEmpty(self):
        parser = cmd_line.ParserBase('')
        self.assertEqual(parser.c, cmd_line.EOF)


class VimParser(unittest.TestCase):
    def testCanParseEmptyInput(self):
        parser = cmd_line.VimParser('')
        rv = parser.parse_range()
        self.assertEqual(rv, cmd_line.default_range_info)

    def testCanMatchMinusSignOffset(self):
        parser = cmd_line.VimParser('-')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = -1
        expected['text_range'] = '-'
        self.assertEqual(rv, expected)

    def testCanMatchPlusSignOffset(self):
        parser = cmd_line.VimParser('+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 1
        expected['text_range'] = '+'
        self.assertEqual(rv, expected)

    def testCanMatchMultiplePlusSignsOffset(self):
        parser = cmd_line.VimParser('++')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 2
        expected['text_range'] = '++'
        self.assertEqual(rv, expected)

    def testCanMatchMultipleMinusSignsOffset(self):
        parser = cmd_line.VimParser('--')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = -2
        expected['text_range'] = '--'
        self.assertEqual(rv, expected)

    def testCanMatchPositiveIntegerOffset(self):
        parser = cmd_line.VimParser('+100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100
        expected['text_range'] = "+100"
        self.assertEqual(rv, expected)

    def testCanMatchMultipleSignsAndPositiveIntegetOffset(self):
        parser = cmd_line.VimParser('++99')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100
        expected['text_range'] = '++99'
        self.assertEqual(rv, expected)

    def testCanMatchMultipleSignsAndNegativeIntegerOffset(self):
        parser = cmd_line.VimParser('--99')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = -100
        expected['text_range'] = '--99'
        self.assertEqual(rv, expected)

    def testCanMatchPlusSignBeforeNegativeInteger(self):
        parser = cmd_line.VimParser('+-101')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = -100
        expected['text_range'] = '+-101'
        self.assertEqual(rv, expected)

    def testCanMatchPostFixMinusSign(self):
        parser = cmd_line.VimParser('101-')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 100
        expected['text_range'] = '101-'
        self.assertEqual(rv, expected)

    def testCanMatchPostfixPlusSign(self):
        parser = cmd_line.VimParser('99+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 100
        expected['text_range'] = '99+'
        self.assertEqual(rv, expected)

    def testCanMatchCurrentLineSymbol(self):
        parser = cmd_line.VimParser('.')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['text_range'] = '.'
        self.assertEqual(rv, expected)

    def testCanMatchLastLineSymbol(self):
        parser = cmd_line.VimParser('$')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['text_range'] = '$'
        self.assertEqual(rv, expected)

    def testCanMatchWholeBufferSymbol(self):
        parser = cmd_line.VimParser('%')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['text_range'] = '%'
        self.assertEqual(rv, expected)

    def testCanMatchMarkRef(self):
        parser = cmd_line.VimParser("'a")
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = "'a"
        expected['text_range'] = "'a"
        self.assertEqual(rv, expected)

    def testCanMatchUppsercaseMarkRef(self):
        parser = cmd_line.VimParser("'A")
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = "'A"
        expected['text_range'] = "'A"
        self.assertEqual(rv, expected)

    def testMarkRefsMustBeAlpha(self):
        parser = cmd_line.VimParser("'0")
        self.assertRaises(SyntaxError, parser.parse_range)

    def testWholeBufferSymbolCannotHavePostfixOffsets(self):
        parser = cmd_line.VimParser('%100')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testWholeBufferSymbolCannotHavePrefixOffsets(self):
        parser = cmd_line.VimParser('100%')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testCurrentLineSymbolCannotHavePrefixOffsets(self):
        parser = cmd_line.VimParser('100.')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testLastLineSymbolCannotHavePrefixOffsets(self):
        parser = cmd_line.VimParser('100$')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testLastLineSymbolCanHavePostfixNoSignIntegerOffsets(self):
        parser = cmd_line.VimParser('$100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_offset'] = 100
        expected['text_range'] = '$100'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHavePostfixSignedIntegerOffsets(self):
        parser = cmd_line.VimParser('$+100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_offset'] = 100
        expected['text_range'] = '$+100'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHavePostfixSignOffsets(self):
        parser = cmd_line.VimParser('$+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_offset'] = 1
        expected['text_range'] = '$+'
        self.assertEqual(rv, expected)

    def testCurrentLineSymbolCanHavePostfixNoSignIntegerOffsets(self):
        parser = cmd_line.VimParser('.100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100
        expected['text_range'] = '.100'
        self.assertEqual(rv, expected)

    def testCurrentLineSymbolCanHavePostfixSignedIntegerOffsets(self):
        parser = cmd_line.VimParser('.+100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 100
        expected['text_range'] = '.+100'
        self.assertEqual(rv, expected)

    def testCurrentLineSymbolCanHavePostfixSignOffsets(self):
        parser = cmd_line.VimParser('.+')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 1
        expected['text_range'] = '.+'
        self.assertEqual(rv, expected)

    def testCanMatchSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 0]]
        expected['text_range'] = '/foo/'
        self.assertEqual(rv, expected)

    def testCanMatchReverseSearchBasedOffsets(self):
        parser = cmd_line.VimParser('?foo?')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo', 0]]
        expected['text_range'] = '?foo?'
        self.assertEqual(rv, expected)

    def testCanMatchReverseSearchBasedOffsetsWithPostfixOffset(self):
        parser = cmd_line.VimParser('?foo?100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo', 100]]
        expected['text_range'] = '?foo?100'
        self.assertEqual(rv, expected)

    def testCanMatchReverseSearchBasedOffsetsWithSignedIntegerOffset(self):
        parser = cmd_line.VimParser('?foo?-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo', -100]]
        expected['text_range'] = '?foo?-100'
        self.assertEqual(rv, expected)

    def testCanMatchSearchBasedOffsetsWithPostfixOffset(self):
        parser = cmd_line.VimParser('/foo/100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 100]]
        expected['text_range'] = '/foo/100'
        self.assertEqual(rv, expected)

    def testCanMatchSearchBasedOffsetsWithSignedIntegerOffset(self):
        parser = cmd_line.VimParser('/foo/-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', -100]]
        expected['text_range'] = '/foo/-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsCanEscapeForwardSlash(self):
        parser = cmd_line.VimParser('/foo\/-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo/-100', 0]]
        expected['text_range'] = '/foo\/-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsCanEscapeQuestionMark(self):
        parser = cmd_line.VimParser('?foo\?-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['?', 'foo?-100', 0]]
        expected['text_range'] = '?foo\?-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsCanEscapeBackSlash(self):
        parser = cmd_line.VimParser('/foo\\\\?-100')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo\\?-100', 0]]
        expected['text_range'] = '/foo\\\\?-100'
        self.assertEqual(rv, expected)

    def testSearchBasedOffsetsEscapeAnyUnknownEscapeSequence(self):
        parser = cmd_line.VimParser('/foo\\h')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'fooh', 0]]
        expected['text_range'] = '/foo\\h'
        self.assertEqual(rv, expected)

    def testCanHaveMultipleSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo//bar/?baz?')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 0],
                                           ['/', 'bar', 0],
                                           ['?', 'baz', 0],
                                          ]
        expected['text_range'] = '/foo//bar/?baz?'
        self.assertEqual(rv, expected)

    def testCanHaveMultipleSearchBasedOffsetsWithInterspersedNumericOffets(self):
        parser = cmd_line.VimParser('/foo/100/bar/+100--+++?baz?')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_search_offsets'] = [['/', 'foo', 100],
                                           ['/', 'bar', 101],
                                           ['?', 'baz', 0],
                                          ]
        expected['text_range'] = '/foo/100/bar/+100--+++?baz?'
        self.assertEqual(rv, expected)

    def testWholeBufferSymbolCannotHavePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('%/foo/')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testCurrentLineSymbolCannotHavePrefixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/.')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testLastLineSymbolCannotHavePrefixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/$')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testWholeBufferSymbolCannotHavePrefixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('/foo/%')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testCurrentLineSymbolCanHavePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('./foo/+10')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_search_offsets'] = [['/', 'foo', 10]]
        expected['text_range'] = './foo/+10'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHavePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('$?foo?+10')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_search_offsets'] = [['?', 'foo', 10]]
        expected['text_range'] = '$?foo?+10'
        self.assertEqual(rv, expected)

    def testLastLineSymbolCanHaveMultiplePostfixSearchBasedOffsets(self):
        parser = cmd_line.VimParser('$?foo?+10/bar/100/baz/')
        rv = parser.parse_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['left_search_offsets'] = [['?', 'foo', 10],
                                           ['/', 'bar', 100],
                                           ['/', 'baz', 0],
                                          ]
        expected['text_range'] = '$?foo?+10/bar/100/baz/'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegers(self):
        parser = cmd_line.VimParser('100,100')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_offset'] = 100
        expected['separator'] = ','
        expected['right_offset'] = 100
        expected['text_range'] = '100,100'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersWithOffsets(self):
        parser = cmd_line.VimParser('+100++--+;++100-')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 101
        expected['separator'] = ';'
        expected['right_ref'] = '.'
        expected['right_offset'] = 100
        expected['text_range'] = '+100++--+;++100-'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_1(self):
        parser = cmd_line.VimParser('%,%')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['separator'] = ','
        expected['right_ref'] = '%'
        expected['text_range'] = '%,%'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_2(self):
        parser = cmd_line.VimParser('.,%')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['separator'] = ','
        expected['right_ref'] = '%'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_2(self):
        parser = cmd_line.VimParser('%,.')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['separator'] = ','
        expected['right_ref'] = '.'
        expected['text_range'] = '%,.'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_3(self):
        parser = cmd_line.VimParser('$,%')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['separator'] = ','
        expected['right_ref'] = '%'
        expected['text_range'] = '$,%'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_4(self):
        parser = cmd_line.VimParser('%,$')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '%'
        expected['separator'] = ','
        expected['right_ref'] = '$'
        expected['text_range'] = '%,$'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_5(self):
        parser = cmd_line.VimParser('$,.')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '$'
        expected['separator'] = ','
        expected['right_ref'] = '.'
        expected['text_range'] = '$,.'
        self.assertEqual(rv, expected)

    def testCanMatchFullRangeOfIntegersSymbols_6(self):
        parser = cmd_line.VimParser('.,$')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['separator'] = ','
        expected['right_ref'] = '$'
        expected['text_range'] = '.,$'
        self.assertEqual(rv, expected)

    def testFullRangeCanMatchCommandOnly(self):
        parser = cmd_line.VimParser('foo')
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        self.assertEqual(rv, expected)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_1(self):
        parser = cmd_line.VimParser('100.,%')
        self.assertRaises(SyntaxError, parser.parse_range)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_2(self):
        parser = cmd_line.VimParser('%,100$')
        self.assertRaises(SyntaxError, parser.parse_full_range)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_3(self):
        parser = cmd_line.VimParser('%,100.')
        self.assertRaises(SyntaxError, parser.parse_full_range)

    def testInFullRangeLineSymbolsCannotHavePrefixOffsets_4(self):
        parser = cmd_line.VimParser('100%,.')
        self.assertRaises(SyntaxError, parser.parse_full_range)

    def testComplexFullRange(self):
        parser = cmd_line.VimParser(".++9/foo\\bar/100?baz?--;'b-100?buzz\\\\\\??+10")
        rv = parser.parse_full_range()
        expected = cmd_line.default_range_info.copy()
        expected['left_ref'] = '.'
        expected['left_offset'] = 10
        expected['left_search_offsets'] = [['/', 'foobar', 100], ['?', 'baz', -2]]
        expected['separator'] = ';'
        expected['right_ref'] = "'b"
        expected['right_offset'] = -100
        expected['right_search_offsets'] = [['?', 'buzz\\?', 10]]
        expected['text_range'] = ".++9/foo\\bar/100?baz?--;'b-100?buzz\\\\\\??+10"
        self.assertEqual(rv, expected)

    def testFullRangeMustEndInAlpha(self):
        parser = cmd_line.VimParser('100%,.(')
        self.assertRaises(SyntaxError, parser.parse_full_range)


class TestCaseCommandLineParser(unittest.TestCase):
    def testCanParseCommandOnly(self):
        parser = cmd_line.CommandLineParser('foo')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"foo", "args":"", "forced": False}],
                errors=[]
            )
        self.assertEqual(rv, expected)

    def testCanParseWithErrors(self):
        parser = cmd_line.CommandLineParser('10$foo')
        rv = parser.parse_cmd_line()
        expected = dict(
                range=None,
                commands=[],
                errors=['E492 Not an editor command.']
            )
        self.assertEqual(rv, expected)

    def testCanParseCommandWithArgs(self):
        parser = cmd_line.CommandLineParser('foo! bar 100')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"foo", "args":"bar 100", "forced": True}],
                errors=[]
            )
        self.assertEqual(rv, expected)

    def testCanParseCommandWithArgsAndRange(self):
        parser = cmd_line.CommandLineParser('100foo! bar 100')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected_range['left_offset'] = 100
        expected_range['text_range'] = '100'
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"foo", "args":"bar 100", "forced": True}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseDoubleAmpersandCommand(self):
        parser = cmd_line.CommandLineParser('&&')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"&&", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseAmpersandCommand(self):
        parser = cmd_line.CommandLineParser('&')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"&", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseBangCommand(self):
        parser = cmd_line.CommandLineParser('!')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"!", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)

    def testCanParseBangCommandWithRange(self):
        parser = cmd_line.CommandLineParser('.!')
        rv = parser.parse_cmd_line()
        expected_range = cmd_line.default_range_info.copy()
        expected_range['text_range'] = '.'
        expected_range['left_ref'] = '.'
        expected = dict(
                range=expected_range,
                commands=[{"cmd":"!", "args":"", "forced": False}],
                errors=[],
            )
        self.assertEqual(rv, expected)


class TestAddressParser(unittest.TestCase):
    def testCanParseSymbolAddress_1(self):
        parser = cmd_line.AddressParser('.')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': None}
        self.assertEqual(rv, expected)

    def testCanParseSymbolAddress_2(self):
        parser = cmd_line.AddressParser('$')
        rv = parser.parse()
        expected = {'ref': '$', 'search_offsets': [], 'offset': None}
        self.assertEqual(rv, expected)

    def testCanParseOffsetOnItsOwn(self):
        parser = cmd_line.AddressParser('100')
        rv = parser.parse()
        expected = {'ref': None, 'search_offsets': [], 'offset': 100}
        self.assertEqual(rv, expected)

    def testCanParseSignsOnTheirOwn(self):
        parser = cmd_line.AddressParser('++')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': 2}
        self.assertEqual(rv, expected)

    def testCanParseSignAndNumber(self):
        parser = cmd_line.AddressParser('+1')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': 1}
        self.assertEqual(rv, expected)

    def testCanParseSymbolAndOffset(self):
        parser = cmd_line.AddressParser('.+1')
        rv = parser.parse()
        expected = {'ref': '.', 'search_offsets': [], 'offset': 1}
        self.assertEqual(rv, expected)

    def testCanParseSearchOffset(self):
        parser = cmd_line.AddressParser('/foo bar')
        rv = parser.parse()
        expected = {'ref': None, 'search_offsets': [['/', 'foo bar', 0]], 'offset': None}
        self.assertEqual(rv, expected)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = linux
import os
import subprocess
from subprocess import PIPE


def run_and_wait(view, cmd):
    term = view.settings().get('VintageousEx_linux_terminal')
    term = term or os.path.expandvars("$COLORTERM") or os.path.expandvars("$TERM")
    subprocess.Popen([
            term, '-e',
            "bash -c \"%s; read -p 'Press RETURN to exit.'\"" % cmd]).wait()


def run_and_read(view, cmd):
    out, err = subprocess.Popen([cmd], stdout=PIPE, shell=True).communicate()
    try:
        return (out or err).decode('utf-8')
    except AttributeError:
        return ''


def filter_region(view, text, command):
    shell = view.settings().get('VintageousEx_linux_shell')
    shell = shell or os.path.expandvars("$SHELL")
    p = subprocess.Popen([shell, '-c', 'echo "%s" | %s' % (text, command)],
                         stdout=subprocess.PIPE)
    return p.communicate()[0][:-1].decode('utf-8')

########NEW FILE########
__FILENAME__ = osx
import os
import subprocess
from subprocess import PIPE


def run_and_wait(view, cmd):
    term = view.settings().get('VintageousEx_osx_terminal')
    term = term or os.path.expandvars("$COLORTERM") or os.path.expandvars("$TERM")
    subprocess.Popen([
            term, '-e',
            "bash -c \"%s; read -p 'Press RETURN to exit.'\"" % cmd]).wait()


def run_and_read(view, cmd):
    out, err = subprocess.Popen([cmd], stdout=PIPE, shell=True).communicate()
    try:
        return (out or err).decode('utf-8')
    except AttributeError:
        return ''


def filter_region(view, text, command):
    shell = view.settings().get('VintageousEx_osx_shell')
    shell = shell or os.path.expandvars("$SHELL")
    p = subprocess.Popen([shell, '-c', 'echo "%s" | %s' % (text, command)],
                         stdout=subprocess.PIPE)
    return p.communicate()[0][:-1]

########NEW FILE########
__FILENAME__ = windows
import subprocess
from subprocess import PIPE
import os
import tempfile


try:
    import ctypes
except ImportError:
    import plat
    if plat.HOST_PLATFORM == plat.WINDOWS:
        raise EnvironmentError("ctypes module missing for Windows.")
    ctypes = None


def get_startup_info():
    # Hide the child process window.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def run_and_wait(view, cmd):
    subprocess.Popen(['cmd.exe', '/c', cmd + '&& pause']).wait()


def run_and_read(view, cmd):
    out, err = subprocess.Popen(['cmd.exe', '/c', cmd],
                                stdout=PIPE,
                                shell=True,
                                startupinfo=get_startup_info()).communicate()
    try:
        return (out or err).decode(get_oem_cp()).replace('\r\n', '\n')
    except AttributeError:
        return ''


def filter_region(view, txt, command):
    try:
        contents = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        contents.write(txt.encode('utf-8'))
        contents.close()

        script = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
        script.write(('@echo off\ntype %s | %s' % (contents.name, command)).encode('utf-8'))
        script.close()

        p = subprocess.Popen([script.name],
                             stdout=subprocess.PIPE,
                             startupinfo=get_startup_info())

        rv = p.communicate()
        return rv[0].decode(get_oem_cp()).replace('\r\n', '\n')[:-1].strip()
    finally:
        os.remove(script.name)
        os.remove(contents.name)


def get_oem_cp():
    codepage = ctypes.windll.kernel32.GetOEMCP()
    return str(codepage)

########NEW FILE########
__FILENAME__ = shell
import sublime

import Vintageous.ex.plat as plat
import Vintageous.ex.plat.linux
import Vintageous.ex.plat.osx
import Vintageous.ex.plat.windows


def run_and_wait(view, cmd):
    if plat.HOST_PLATFORM == plat.WINDOWS:
        plat.windows.run_and_wait(view, cmd)
    elif plat.HOST_PLATFORM == plat.LINUX:
        plat.linux.run_and_wait(view, cmd)
    elif plat.HOST_PLATFORM == plat.OSX:
        plat.osx.run_and_wait(view, cmd)
    else:
        raise NotImplementedError


def run_and_read(view, cmd):
    if plat.HOST_PLATFORM == plat.WINDOWS:
        return plat.windows.run_and_read(view, cmd)
    elif plat.HOST_PLATFORM == plat.LINUX:
        return plat.linux.run_and_read(view, cmd)
    elif plat.HOST_PLATFORM == plat.OSX:
        return plat.osx.run_and_read(view, cmd)
    else:
        raise NotImplementedError


def filter_thru_shell(view, edit, regions, cmd):
    # XXX: make this a ShellFilter class instead
    if plat.HOST_PLATFORM == plat.WINDOWS:
        filter_func = plat.windows.filter_region
    elif plat.HOST_PLATFORM == plat.LINUX:
        filter_func = plat.linux.filter_region
    elif plat.HOST_PLATFORM == plat.OSX:
        filter_func = plat.osx.filter_region
    else:
        raise NotImplementedError

    # Maintain text size delta as we replace each selection going forward.
    # We can't simply go in reverse because cursor positions will be incorrect.
    accumulated_delta = 0
    new_points = []
    for r in regions:
        r_shifted = sublime.Region(r.begin() + accumulated_delta, r.end() + accumulated_delta)
        rv = filter_func(view, view.substr(r_shifted), cmd)
        view.replace(edit, r_shifted, rv)
        new_points.append(r_shifted.a)
        accumulated_delta += len(rv) - r_shifted.size()

    # Switch to normal mode and move cursor(s) to beginning of replacement(s)
    view.run_command('vi_enter_normal_mode')
    view.sel().clear()
    view.sel().add_all(new_points)

########NEW FILE########
__FILENAME__ = ex_commands
import sublime
import sublime_plugin

import os
import stat
import re
import subprocess

from Vintageous.ex import ex_error
from Vintageous.ex import ex_range
from Vintageous.ex import parsers
from Vintageous.ex import shell
from Vintageous.ex.plat.windows import get_oem_cp
from Vintageous.ex.plat.windows import get_startup_info
from Vintageous.state import State
from Vintageous.vi import abbrev
from Vintageous.vi import utils
from Vintageous.vi.constants import MODE_NORMAL
from Vintageous.vi.constants import MODE_VISUAL
from Vintageous.vi.constants import MODE_VISUAL_LINE
from Vintageous.vi.mappings import Mappings
from Vintageous.vi.settings import set_global
from Vintageous.vi.settings import set_local
from Vintageous.vi.sublime import has_dirty_buffers
from Vintageous.vi.utils import IrreversibleTextCommand
from Vintageous.vi.utils import modes


GLOBAL_RANGES = []
CURRENT_LINE_RANGE = {'left_ref': '.', 'left_offset': 0,
                      'left_search_offsets': [], 'right_ref': None,
                      'right_offset': 0, 'right_search_offsets': []}


def changing_cd(f, *args, **kwargs):
    def inner(*args, **kwargs):
        try:
            state = State(args[0].view)
        except AttributeError:
            state = State(args[0].window.active_view())

        old = os.getcwd()
        try:
            # FIXME: Under some circumstances, like when switching projects to
            # a file whose _cmdline_cd has not been set, _cmdline_cd might
            # return 'None'. In such cases, change to the actual current
            # directory as a last measure. (We should probably fix this anyway).
            os.chdir(state.settings.vi['_cmdline_cd'] or old)
            f(*args, **kwargs)
        finally:
            os.chdir(old)
    return inner


def gather_buffer_info(v):
    """gathers data to be displayed by :ls or :buffers
    """
    path = v.file_name()
    if path:
        parent, leaf = os.path.split(path)
        parent = os.path.basename(parent)
        path = os.path.join(parent, leaf)
    else:
        path = v.name() or str(v.buffer_id())
        leaf = v.name() or 'untitled'

    status = []
    if not v.file_name():
        status.append("t")
    if v.is_dirty():
        status.append("*")
    if v.is_read_only():
        status.append("r")

    if status:
        leaf += ' (%s)' % ', '.join(status)
    return [leaf, path]


def get_region_by_range(view, line_range=None, as_lines=False):
    # If GLOBAL_RANGES exists, the ExGlobal command has been run right before
    # the current command, and we know we must process these lines.
    global GLOBAL_RANGES
    if GLOBAL_RANGES:
        rv = GLOBAL_RANGES[:]
        GLOBAL_RANGES = []
        return rv

    if line_range:
        vim_range = ex_range.VimRange(view, line_range)
        if as_lines:
            return vim_range.lines()
        else:
            return vim_range.blocks()


class ExTextCommandBase(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def line_range_to_text(self, line_range):
        line_block = get_region_by_range(self.view, line_range=line_range)
        line_block = [self.view.substr(r) for r in line_block]
        return '\n'.join(line_block) + '\n'

    def serialize_sel(self):
        sels = [(r.a, r.b) for r in list(self.view.sel())]
        self.view.settings().set('ex_data', {'prev_sel': sels})

    def deserialize_sel(self, name='next_sel'):
        return self.view.settings().get('ex_data')[name] or []

    def set_sel(self):
        sel = self.deserialize_sel()
        self.view.sel().clear()
        self.view.sel().add_all([sublime.Region(b) for (a, b) in sel])

    def set_next_sel(self, data):
        self.view.settings().set('ex_data', {'next_sel': data})

    def set_mode(self):
        state = State(self.view)
        state.enter_normal_mode()
        self.view.run_command('vi_enter_normal_mode')

    def run(self, edit, *args, **kwargs):
        self.serialize_sel()
        self.run_ex_command(edit, *args, **kwargs)
        self.set_sel()
        self.set_mode()


class ExAddressableCommandMixin(object):
    def get_address(self, address):
        # FIXME: We must fix the parser.
        if address == '0':
            return 0
        address_parser = parsers.cmd_line.AddressParser(address)
        parsed_address = address_parser.parse()
        address = ex_range.calculate_address(self.view, parsed_address)
        return address


class ExGoto(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None):
        if not line_range['text_range']:
            # No-op: user issued ":".
            return
        ranges, _ = ex_range.new_calculate_range(self.view, line_range)
        a, b = ranges[0]
        # FIXME: This should be handled by the parser.
        # FIXME: In Vim, 0 seems to equal 1 in ranges.
        b = b if line_range['text_range'] != '0' else 1
        state = State(self.view)
        # FIXME: In Visual mode, goto line does some weird stuff.
        if state.mode == MODE_NORMAL:
            # TODO: push all this code down to ViGoToLine?
            self.view.window().run_command('_vi_add_to_jump_list')
            self.view.run_command('_vi_go_to_line', {'line': b, 'mode': state.mode})
            self.view.window().run_command('_vi_add_to_jump_list')
            self.view.show(self.view.sel()[0])
        elif state.mode in (MODE_VISUAL, MODE_VISUAL_LINE) and line_range['right_offset']:
            # TODO: push all this code down to ViGoToLine?
            self.view.window().run_command('_vi_add_to_jump_list')
            # FIXME: The parser fails with '<,'>100. 100 is not the right_offset, but an argument.
            b = self.view.rowcol(self.view.sel()[0].b - 1)[0] + line_range['right_offset'] + 1
            self.view.run_command('_vi_go_to_line', {'line': b, 'mode': state.mode})
            self.view.window().run_command('_vi_add_to_jump_list')
            self.view.show(self.view.sel()[0])


class ExShellOut(sublime_plugin.TextCommand):
    """Ex command(s): :!cmd, :'<,>'!cmd

    Run cmd in a system's shell or filter selected regions through external
    command.
    """

    @changing_cd
    def run(self, edit, line_range=None, shell_cmd=''):
        try:
            if line_range['text_range']:
                shell.filter_thru_shell(
                                view=self.view,
                                edit=edit,
                                regions=get_region_by_range(self.view, line_range=line_range),
                                cmd=shell_cmd)
            else:
                # TODO: Read output into output panel.
                # shell.run_and_wait(self.view, shell_cmd)
                out = shell.run_and_read(self.view, shell_cmd)

                output_view = self.view.window().create_output_panel('vi_out')
                output_view.settings().set("line_numbers", False)
                output_view.settings().set("gutter", False)
                output_view.settings().set("scroll_past_end", False)
                output_view = self.view.window().create_output_panel('vi_out')
                output_view.run_command('append', {'characters': out,
                                                   'force': True,
                                                   'scroll_to_end': True})
                self.view.window().run_command("show_panel", {"panel": "output.vi_out"})
        except NotImplementedError:
            ex_error.handle_not_implemented()


class ExShell(IrreversibleTextCommand):
    """Ex command(s): :shell

    Opens a shell at the current view's directory. Sublime Text keeps a virtual
    current directory that most of the time will be out of sync with the actual
    current directory. The virtual current directory is always set to the
    current view's directory, but it isn't accessible through the API.
    """
    def open_shell(self, command):
        return subprocess.Popen(command, cwd=os.getcwd())

    @changing_cd
    def run(self):
        if sublime.platform() == 'linux':
            term = self.view.settings().get('VintageousEx_linux_terminal')
            term = term or os.environ.get('COLORTERM') or os.environ.get("TERM")
            if not term:
                sublime.status_message("Vintageous: Not terminal name found.")
                return
            try:
                self.open_shell([term, '-e', 'bash']).wait()
            except Exception as e:
                print(e)
                sublime.status_message("Vintageous: Error while executing command through shell.")
                return
        elif sublime.platform() == 'osx':
            term = self.view.settings().get('VintageousEx_osx_terminal')
            term = term or os.environ.get('COLORTERM') or os.environ.get("TERM")
            if not term:
                sublime.status_message("Vintageous: Not terminal name found.")
                return
            try:
                self.open_shell([term, '-e', 'bash']).wait()
            except Exception as e:
                print(e)
                sublime.status_message("Vintageous: Error while executing command through shell.")
                return
        elif sublime.platform() == 'windows':
            self.open_shell(['cmd.exe', '/k']).wait()
        else:
            # XXX OSX (make check explicit)
            ex_error.handle_not_implemented()


class ExReadShellOut(sublime_plugin.TextCommand):
    @changing_cd
    def run(self, edit, line_range=None, name='', plusplus_args='', forced=False):
        target_line = self.view.line(self.view.sel()[0].begin())
        if line_range['text_range']:
            range = max(ex_range.calculate_range(self.view, line_range=line_range)[0])
            target_line = self.view.line(self.view.text_point(range, 0))
        target_point = min(target_line.b + 1, self.view.size())

        # Cheat a little bit to get the parsing right:
        #   - forced == True means we need to execute a command
        if forced:
            if sublime.platform() == 'linux':
                for s in self.view.sel():
                    # TODO: make shell command configurable.
                    the_shell = self.view.settings().get('linux_shell')
                    the_shell = the_shell or os.path.expandvars("$SHELL")
                    if not the_shell:
                        sublime.status_message("Vintageous: No shell name found.")
                        return
                    try:
                        p = subprocess.Popen([the_shell, '-c', name],
                                                            stdout=subprocess.PIPE)
                    except Exception as e:
                        print(e)
                        sublime.status_message("Vintageous: Error while executing command through shell.")
                        return
                    self.view.insert(edit, s.begin(), p.communicate()[0][:-1].decode('utf-8'))
            elif sublime.platform() == 'windows':
                for s in self.view.sel():
                    p = subprocess.Popen(['cmd.exe', '/C', name],
                                            stdout=subprocess.PIPE,
                                            startupinfo=get_startup_info()
                                            )
                    cp = 'cp' + get_oem_cp()
                    rv = p.communicate()[0].decode(cp)[:-2].strip()
                    self.view.insert(edit, s.begin(), rv)
            else:
                ex_error.handle_not_implemented()
        # Read a file into the current view.
        else:
            # According to Vim's help, :r should read the current file's content
            # if no file name is given, but Vim doesn't do that.
            # TODO: implement reading a file into the buffer.
            ex_error.handle_not_implemented()
            return


class ExPromptSelectOpenFile(sublime_plugin.TextCommand):
    """Ex command(s): :ls, :files

    Shows a quick panel listing the open files only. Provides concise
    information about the buffers's state: 'transient', 'unsaved'.
    """
    def run(self, edit):
        self.file_names = [gather_buffer_info(v)
                                        for v in self.view.window().views()]
        self.view.window().show_quick_panel(self.file_names, self.on_done)

    def on_done(self, idx):
        if idx == -1: return
        sought_fname = self.file_names[idx]
        for v in self.view.window().views():
            if v.file_name() and v.file_name().endswith(sought_fname[1]):
                self.view.window().focus_view(v)
            # XXX Base all checks on buffer id?
            elif sought_fname[1].isdigit() and \
                                        v.buffer_id() == int(sought_fname[1]):
                self.view.window().focus_view(v)


class ExMap(sublime_plugin.TextCommand):
    """
    Remaps keys.
    """
    def run(self, edit, mode=None, count=None, cmd=''):
        try:
            keys, command = cmd.lstrip().split(' ', 1)
        except ValueError:
            sublime.status_message('Vintageous: Bad mapping format')
            return
        else:
            mappings = Mappings(State(self.view))
            mappings.add(modes.NORMAL, keys, command)
            mappings.add(modes.OPERATOR_PENDING, keys, command)
            mappings.add(modes.VISUAL, keys, command)


class ExUnmap(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=None, cmd=''):
        mappings = Mappings(State(self.view))
        try:
            mappings.remove(modes.NORMAL, cmd)
            mappings.remove(modes.OPERATOR_PENDING, cmd)
            mappings.remove(modes.VISUAL, cmd)
        except KeyError:
            sublime.status_message('Vintageous: Mapping not found.')


class ExNmap(sublime_plugin.TextCommand):
    """
    Remaps keys.
    """
    def run(self, edit, mode=None, count=None, cmd=''):
        keys, command = cmd.lstrip().split(' ', 1)
        mappings = Mappings(State(self.view))
        mappings.add(modes.NORMAL, keys, command)


class ExNunmap(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=None, cmd=''):
        mappings = Mappings(State(self.view))
        try:
            mappings.remove(modes.NORMAL, cmd)
        except KeyError:
            sublime.status_message('Vintageous: Mapping not found.')


class ExOmap(sublime_plugin.TextCommand):
    """
    Remaps keys.
    """
    def run(self, edit, mode=None, count=None, cmd=''):
        keys, command = cmd.lstrip().split(' ', 1)
        mappings = Mappings(State(self.view))
        mappings.add(modes.OPERATOR_PENDING, keys, command)


class ExOunmap(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=None, cmd=''):
        mappings = Mappings(State(self.view))
        try:
            mappings.remove(modes.OPERATOR_PENDING, cmd)
        except KeyError:
            sublime.status_message('Vintageous: Mapping not found.')


class ExVmap(sublime_plugin.TextCommand):
    """
    Remaps keys.
    """
    def run(self, edit, mode=None, count=None, cmd=''):
        keys, command = cmd.lstrip().split(' ', 1)
        mappings = Mappings(State(self.view))
        mappings.add(modes.VISUAL, keys, command)
        mappings.add(modes.VISUAL_LINE, keys, command)
        mappings.add(modes.VISUAL_BLOCK, keys, command)


class ExVunmap(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=None, cmd=''):
        mappings = Mappings(State(self.view))
        try:
            mappings.remove(modes.VISUAL, cmd)
            mappings.remove(modes.VISUAL_LINE, cmd)
            mappings.remove(modes.VISUAL_BLOCK, cmd)
        except KeyError:
            sublime.status_message('Vintageous: Mapping  not found.')


class ExAbbreviate(sublime_plugin.TextCommand):
    def run(self, edit, short=None, full=None):
        if not (short and full):
            self.show_abbreviations()
            return

        abbrev.Store().set(short, full)

    def show_abbreviations(self):
        abbrevs = ['{0} --> {1}'.format(item['trigger'], item['contents'])
                                                    for item in
                                                    abbrev.Store().get_all()]

        self.view.window().show_quick_panel(abbrevs,
                                            None, # Simply show the list.
                                            flags=sublime.MONOSPACE_FONT)


class ExUnabbreviate(sublime_plugin.TextCommand):
    def run(self, edit, short):
        if not short:
            return

        abbrev.Store().erase(short)


class ExPrintWorkingDir(IrreversibleTextCommand):
    @changing_cd
    def run(self):
        state = State(self.view)
        sublime.status_message(os.getcwd())


class ExWriteFile(sublime_plugin.WindowCommand):
    @changing_cd
    def run(self,
            line_range=None,
            forced=False,
            file_name='',
            plusplus_args='',
            operator='',
            target_redirect='',
            subcmd=''):

        if file_name and target_redirect:
            sublime.status_message('Vintageous: Too many arguments.')
            return

        appending = operator == '>>'
        a_range = line_range['text_range']
        self.view = self.window.active_view()
        content = get_region_by_range(self.view, line_range=line_range) if a_range else \
                        [sublime.Region(0, self.view.size())]

        read_only = False
        if self.view.file_name():
            mode = os.stat(self.view.file_name())
            read_only = (stat.S_IMODE(mode.st_mode) & stat.S_IWUSR !=
                                                                stat.S_IWUSR)

        if target_redirect:
            target = self.window.new_file()
            target.set_name(target_redirect)
        elif file_name:

            def report_error(msg):
                sublime.status_message('Vintageous: %s' % msg)

            file_path = os.path.abspath(os.path.expanduser(file_name))

            if os.path.exists(file_path) and (file_path != self.view.file_name()):
                # TODO add w! flag
                # TODO: Hook this up with ex error handling (ex/errors.py).
                msg = "File '{0}' already exists.".format(file_path)
                report_error(msg)
                return

            if not os.path.exists(os.path.dirname(file_path)):
                msg = "Directory '{0}' does not exist.".format(os.path.dirname(file_path))
                report_error(msg)
                return

            try:
                # FIXME: We need to do some work with encodings here, don't we?
                with open(file_path, 'w+') as temp_file:
                    for frag in reversed(content):
                        temp_file.write(self.view.substr(frag))
                    temp_file.close()
                    sublime.status_message("Vintageous: Saved {0}".format(file_path))

                    row, col = self.view.rowcol(self.view.sel()[0].b)
                    encoded_fn = "{0}:{1}:{2}".format(file_path, row + 1, col + 1)
                    self.view.set_scratch(True)
                    w = self.window
                    w.run_command('close')
                    w.open_file(encoded_fn, sublime.ENCODED_POSITION)
                    return
            except IOError as e:
                report_error( "Failed to create file '%s'." % file_name )
                return

            window = self.window
            window.open_file(file_path)
            return
        else:
            target = self.view

            if (read_only or self.view.is_read_only()) and not forced:
                utils.blink()
                sublime.status_message("Vintageous: Can't write read-only file.")
                return

        start = 0 if not appending else target.size()
        prefix = '\n' if appending and target.size() > 0 else ''

        if appending or target_redirect:
            for frag in reversed(content):
                target.run_command('append', {'characters': prefix + self.view.substr(frag) + '\n'})
        elif a_range:
            start_deleting = 0
            text = ''
            for frag in content:
                text += self.view.substr(frag) + '\n'
            start_deleting = len(text)
            self.view.run_command('ex_replace_file', {'start': 0, 'end': 0, 'with_what': text})
        else:
            dirname = os.path.dirname(self.view.file_name())
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            self.window.run_command('save')

        # This may unluckily prevent the user from seeing ST's feedback about saving the current
        # file.
        state = State(self.window.active_view())
        if state.mode != MODE_NORMAL:
            state.enter_normal_mode()
            self.window.run_command('vi_enter_normal_mode')


class ExReplaceFile(sublime_plugin.TextCommand):
    def run(self, edit, start, end, with_what):
        self.view.replace(edit, sublime.Region(0, self.view.size()), with_what)


class ExWriteAll(sublime_plugin.WindowCommand):
    @changing_cd
    def run(self, forced=False):
        for v in self.window.views():
            v.run_command('save')


class ExNewFile(sublime_plugin.WindowCommand):
    @changing_cd
    def run(self, forced=False):
        self.window.run_command('new_file')


class ExFile(sublime_plugin.TextCommand):
    def run(self, edit, forced=False):
        # XXX figure out what the right params are. vim's help seems to be
        # wrong
        if self.view.file_name():
            fname = self.view.file_name()
        else:
            fname = 'untitled'

        attrs = ''
        if self.view.is_read_only():
            attrs = 'readonly'

        if self.view.is_dirty():
            attrs = 'modified'

        lines = 'no lines in the buffer'
        if self.view.rowcol(self.view.size())[0]:
            lines = self.view.rowcol(self.view.size())[0] + 1

        # fixme: doesn't calculate the buffer's % correctly
        if not isinstance(lines, str):
            vr = self.view.visible_region()
            start_row, end_row = self.view.rowcol(vr.begin())[0], \
                                              self.view.rowcol(vr.end())[0]
            mid = (start_row + end_row + 2) / 2
            percent = float(mid) / lines * 100.0

        msg = fname
        if attrs:
            msg += " [%s]" % attrs
        if isinstance(lines, str):
            msg += " -- %s --"  % lines
        else:
            msg += " %d line(s) --%d%%--" % (lines, int(percent))

        sublime.status_message('Vintageous: %s' % msg)


class ExMove(ExTextCommandBase, ExAddressableCommandMixin):
    def run_ex_command(self, edit, line_range=CURRENT_LINE_RANGE, forced=False, address=''):
        # make sure we have a default range
        if ('text_range' not in line_range) or not line_range['text_range']:
            line_range['text_range'] = '.'

        address = self.get_address(address)
        if address is None:
            ex_error.display_error(ex_error.ERR_INVALID_ADDRESS)
            return

        if address != 0:
            dest = self.view.line(self.view.text_point(address, 0)).end() + 1
        else:
            dest = 0

        # Don't move lines onto themselves.
        for sel in self.view.sel():
            if sel.contains(dest):
                ex_error.display_error(ex_error.ERR_CANT_MOVE_LINES_ONTO_THEMSELVES)
                return

        text = self.line_range_to_text(line_range)
        if dest > self.view.size():
            dest = self.view.size()
            text = '\n' + text[:-1]
        self.view.insert(edit, dest, text)

        for r in reversed(get_region_by_range(self.view, line_range)):
            self.view.erase(edit, self.view.full_line(r))

        new_address = address
        if address < self.view.rowcol(self.view.sel()[0].b)[0]:
            new_pt = self.view.text_point(new_address + 1, 0)
            new_address = self.view.rowcol(new_pt + len(text) - 1)[0]
        next_sel = self.view.text_point(new_address, 0)
        self.set_next_sel([(next_sel, next_sel)])


class ExCopy(ExTextCommandBase, ExAddressableCommandMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run_ex_command(self, edit, line_range=CURRENT_LINE_RANGE,
                       forced=False, address=''):
        address = self.get_address(address)
        if address is None:
            ex_error.display_error(ex_error.ERR_INVALID_ADDRESS)
            return

        if address != 0:
            dest = self.view.line(self.view.text_point(address, 0)).end() + 1
        else:
            dest = address

        text = self.line_range_to_text(line_range)
        if dest > self.view.size():
            dest = self.view.size()
            text = '\n' + text[:-1]

        self.view.insert(edit, dest, text)

        cursor_dest = self.view.line(dest + len(text) - 1).begin()
        self.set_next_sel([(cursor_dest, cursor_dest)])


class ExOnly(sublime_plugin.TextCommand):
    """ Command: :only
    """
    def run(self, edit, forced=False):
        if not forced:
            if has_dirty_buffers(self.view.window()):
                ex_error.display_error(ex_error.ERR_OTHER_BUFFER_HAS_CHANGES)
                return

        w = self.view.window()
        current_id = self.view.id()
        for v in w.views():
            if v.id() != current_id:
                if forced and v.is_dirty():
                    v.set_scratch(True)
                w.focus_view(v)
                w.run_command('close')


class ExDoubleAmpersand(sublime_plugin.TextCommand):
    """ Command :&&
    """
    def run(self, edit, line_range=None, flags='', count=''):
        self.view.run_command('ex_substitute', {'line_range': line_range,
                                                'pattern': flags + count})


class ExSubstitute(sublime_plugin.TextCommand):
    most_recent_pat = None
    most_recent_flags = ''
    most_recent_replacement = ''

    def run(self, edit, line_range=None, pattern=''):

        # :s
        if not pattern:
            pattern = ExSubstitute.most_recent_pat
            replacement = ExSubstitute.most_recent_replacement
            flags = ''
            count = 0
        # :s g 100 | :s/ | :s// | s:/foo/bar/g 100 | etc.
        else:
            try:
                parts = parsers.s_cmd.split(pattern)
            except SyntaxError as e:
                sublime.status_message("Vintageous: (substitute) %s" % e)
                print("Vintageous: (substitute) %s" % e)
                return
            else:
                if len(parts) == 4:
                    # This is a full command in the form :s/foo/bar/g 100 or a
                    # partial version of it.
                    (pattern, replacement, flags, count) = parts
                else:
                    # This is a short command in the form :s g 100 or a partial
                    # version of it.
                    (flags, count) = parts
                    pattern = ExSubstitute.most_recent_pat
                    replacement = ExSubstitute.most_recent_replacement

        if not pattern:
            pattern = ExSubstitute.most_recent_pat
        else:
            ExSubstitute.most_recent_pat = pattern
            ExSubstitute.most_recent_replacement = replacement
            ExSubstitute.most_recent_flags = flags

        computed_flags = 0
        computed_flags |= re.IGNORECASE if (flags and 'i' in flags) else 0
        try:
            pattern = re.compile(pattern, flags=computed_flags)
        except Exception as e:
            sublime.status_message("Vintageous [regex error]: %s ... in pattern '%s'" % (e.message, pattern))
            print("Vintageous [regex error]: %s ... in pattern '%s'" % (e.message, pattern))
            return

        replace_count = 0 if (flags and 'g' in flags) else 1

        target_region = get_region_by_range(self.view, line_range=line_range, as_lines=True)
        for r in reversed(target_region):
            line_text = self.view.substr(self.view.line(r))
            rv = re.sub(pattern, replacement, line_text, count=replace_count)
            self.view.replace(edit, self.view.line(r), rv)


class ExDelete(ExTextCommandBase):
    def select(self, regions, register):
        self.view.sel().clear()
        to_store = []
        for r in regions:
            self.view.sel().add(r)
            if register:
                to_store.append(self.view.substr(self.view.full_line(r)))

        if register:
            text = ''.join(to_store)
            if not text.endswith('\n'):
                text = text + '\n'

            state = State(self.view)
            state.registers[register] = [text]

    def run_ex_command(self, edit, line_range=None, register='', count=''):
        # XXX somewhat different to vim's behavior
        line_range = line_range if line_range else CURRENT_LINE_RANGE
        if line_range.get('text_range') == '0':
            # FIXME: This seems to be a bug in the parser or get_region_by_range.
            # We should be settings 'left_ref', not 'left_offset'.
            line_range['left_offset'] = 1
            line_range['text_range'] = '1'
        rs = get_region_by_range(self.view, line_range=line_range)

        self.select(rs, register)

        self.view.run_command('split_selection_into_lines')
        self.view.run_command(
                    'run_macro_file',
                    {'file': 'Packages/Default/Delete Line.sublime-macro'})

        self.set_next_sel([(rs[0].a, rs[0].a)])


class ExGlobal(sublime_plugin.TextCommand):
    """Ex command(s): :global

    :global filters lines where a pattern matches and then applies the supplied
    action to all those lines.

    Examples:
        :10,20g/FOO/delete

        This command deletes all lines between line 10 and line 20 where 'FOO'
        matches.

        :g:XXX:s!old!NEW!g

        This command replaces all instances of 'old' with 'NEW' in every line
        where 'XXX' matches.

    By default, :global searches all lines in the buffer.

    If you want to filter lines where a pattern does NOT match, add an
    exclamation point:

        :g!/DON'T TOUCH THIS/delete
    """
    most_recent_pat = None
    def run(self, edit, line_range=None, forced=False, pattern=''):

        if not line_range['text_range']:
            line_range['text_range'] = '%'
            line_range['left_ref'] = '%'
        try:
            global_pattern, subcmd = parsers.g_cmd.split(pattern)
        except ValueError:
            msg = "Vintageous: Bad :global pattern. (%s)" % pattern
            sublime.status_message(msg)
            print(msg)
            return

        if global_pattern:
            ExGlobal.most_recent_pat = global_pattern
        else:
            global_pattern = ExGlobal.most_recent_pat

        # Make sure we always have a subcommand to exectute. This is what
        # Vim does too.
        subcmd = subcmd or 'print'

        rs = get_region_by_range(self.view, line_range=line_range, as_lines=True)

        for r in rs:
            try:
                match = re.search(global_pattern, self.view.substr(r))
            except Exception as e:
                msg = "Vintageous (global): %s ... in pattern '%s'" % (str(e), global_pattern)
                sublime.status_message(msg)
                print(msg)
                return
            if (match and not forced) or (not match and forced):
                GLOBAL_RANGES.append(r)

        # don't do anything if we didn't found any target ranges
        if not GLOBAL_RANGES:
            return
        self.view.window().run_command('vi_colon_input',
                              {'cmd_line': ':' +
                                    str(self.view.rowcol(r.a)[0] + 1) +
                                    subcmd})


class ExPrint(sublime_plugin.TextCommand):
    def run(self, edit, line_range=None, count='1', flags=''):
        if not count.isdigit():
            flags, count = count, ''
        rs = get_region_by_range(self.view, line_range=line_range)
        to_display = []
        for r in rs:
            for line in self.view.lines(r):
                text = self.view.substr(line)
                if '#' in flags:
                    row = self.view.rowcol(line.begin())[0] + 1
                else:
                    row = ''
                to_display.append((text, row))

        v = self.view.window().new_file()
        v.set_scratch(True)
        if 'l' in flags:
            v.settings().set('draw_white_space', 'all')
        for t, r in to_display:
            v.insert(edit, v.size(), (str(r) + ' ' + t + '\n').lstrip())


class ExQuitCommand(sublime_plugin.WindowCommand):
    """Ex command(s): :quit
    Closes the window.

        * Don't close the window if there are dirty buffers
          TODO:
          (Doesn't make too much sense if hot_exit is on, though.)
          Although ST's window command 'exit' would take care of this, it
          displays a modal dialog, so spare ourselves that.
    """
    def run(self, forced=False, count=1, flags=''):
        v = self.window.active_view()
        if forced:
            v.set_scratch(True)
        if v.is_dirty():
            sublime.status_message("There are unsaved changes!")
            return

        self.window.run_command('close')
        if len(self.window.views()) == 0:
            self.window.run_command('close')
            return

        # Close the current group if there aren't any views left in it.
        if not self.window.views_in_group(self.window.active_group()):
            self.window.run_command('ex_unvsplit')


class ExQuitAllCommand(sublime_plugin.WindowCommand):
    """Ex command(s): :qall
    Close all windows and then exit Sublime Text.

    If there are dirty buffers, exit only if :qall!.
    """
    def run(self, forced=False):
        if forced:
            for v in self.window.views():
                if v.is_dirty():
                    v.set_scratch(True)
        elif has_dirty_buffers(self.window):
            sublime.status_message("There are unsaved changes!")
            return

        self.window.run_command('close_all')
        self.window.run_command('exit')


class ExWriteAndQuitCommand(sublime_plugin.TextCommand):
    """Ex command(s): :wq

    Write and then close the active buffer.
    """
    def run(self, edit, line_range=None, forced=False):
        # TODO: implement this
        if forced:
            ex_error.handle_not_implemented()
            return
        if self.view.is_read_only():
            sublime.status_message("Can't write a read-only buffer.")
            return
        if not self.view.file_name():
            sublime.status_message("Can't save a file without name.")
            return

        self.view.run_command('save')
        self.view.window().run_command('ex_quit')


class ExBrowse(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().run_command('prompt_open_file')


class ExEdit(IrreversibleTextCommand):
    """Ex command(s): :e <file_name>

    Reverts unsaved changes to the buffer.

    If there's a <file_name>, open it for editing.
    """
    @changing_cd
    def run(self, forced=False, file_name=None):
        if file_name:
            file_name = os.path.expanduser(os.path.expandvars(file_name))
            if self.view.is_dirty() and not forced:
                ex_error.display_error(ex_error.ERR_UNSAVED_CHANGES)
                return
            file_name = os.path.expanduser(file_name)
            if os.path.isdir(file_name):
                sublime.status_message('Vintageous: "{0}" is a directory'.format(file_name))
                return

            message = ''

            if not os.path.isabs(file_name):
                file_name = os.path.join(
                                State(self.view).settings.vi['_cmdline_cd'],
                                file_name)

            if not os.path.exists(file_name):
                message = '[New File]'
                path = os.path.dirname(file_name)
                if path and not os.path.exists(path):
                    message = '[New DIRECTORY]'
                self.view.window().open_file(file_name)

                # TODO: Collect message and show at the end of the command.
                def show_message():
                    sublime.status_message('Vintageous: "{0}" {1}'.format((file_name, message)))
                sublime.set_timeout(show_message, 250)
                return
        else:
            if forced or not self.view.is_dirty():
                self.view.run_command('revert')
                return
            elif not file_name and self.view.is_dirty():
                ex_error.display_error(ex_error.ERR_UNSAVED_CHANGES)
                return

        if forced or not self.view.is_dirty():
            self.view.window().open_file(file_name)
            return
        ex_error.display_error(ex_error.ERR_UNSAVED_CHANGES)


class ExCquit(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.window().run_command('exit')


class ExExit(sublime_plugin.TextCommand):
    """Ex command(s): :x[it], :exi[t]

    Like :wq, but write only when changes have been made.

    TODO: Support ranges, like :w.
    """
    def run(self, edit, line_range=None, mode=None, count=1):
        w = self.view.window()

        if w.active_view().is_dirty():
            w.run_command('save')

        w.run_command('close')

        if len(w.views()) == 0:
            w.run_command('exit')


class ExListRegisters(sublime_plugin.TextCommand):
    """Lists registers in quick panel and saves selected to `"` register.

       In Vintageous, registers store lists of values (due to multiple selections).
    """

    def run(self, edit):
        def show_lines(line_count):
            lines_display = '... [+{0}]'.format(line_count - 1)
            return lines_display if line_count > 1 else ''

        state = State(self.view)
        pairs = [(k, v) for (k, v) in state.registers.to_dict().items() if v]
        pairs = [(k, repr(v[0]), len(v)) for (k, v) in pairs]
        pairs = ['"{0}  {1}  {2}'.format(k, v, show_lines(lines)) for (k, v, lines) in pairs]

        self.view.window().show_quick_panel(pairs, self.on_done, flags=sublime.MONOSPACE_FONT)

    def on_done(self, idx):
        """Save selected value to `"` register."""
        if idx == -1:
            return

        state = State(self.view)
        value = list(state.registers.to_dict().values())[idx]
        state.registers['"'] = value


class ExNew(sublime_plugin.TextCommand):
    """Ex command(s): :new

    Create a new buffer.

    TODO: Create new buffer by splitting the screen.
    """
    @changing_cd
    def run(self, edit, line_range=None):
        self.view.window().run_command('new_file')


class ExYank(sublime_plugin.TextCommand):
    """Ex command(s): :y[ank]
    """

    def run(self, edit, line_range, register=None, count=None):
        if not register:
            register = '"'

        regs = get_region_by_range(self.view, line_range)
        text = '\n'.join([self.view.substr(line) for line in regs]) + '\n'

        state = State(self.view)
        state.registers[register] = [text]
        if register == '"':
            state.registers['0'] = [text]



class TabControlCommand(sublime_plugin.WindowCommand):
    def run(self, command, file_name=None, forced=False):
        window = self.window
        selfview = window.active_view()
        max_index = len(window.views())
        (group, index) = window.get_view_index(selfview)
        if (command == "open"):
            if file_name is None:  # TODO: file completion
                window.run_command("show_overlay", {"overlay": "goto", "show_files": True, })
            else:
                cur_dir = os.path.dirname(selfview.file_name())
                window.open_file(os.path.join(cur_dir, file_name))
        elif command == "next":
            window.run_command("select_by_index", {"index": (index + 1) % max_index}, )
        elif command == "prev":
            window.run_command("select_by_index", {"index": (index + max_index - 1) % max_index, })
        elif command == "last":
            window.run_command("select_by_index", {"index": max_index - 1, })
        elif command == "first":
            window.run_command("select_by_index", {"index": 0, })
        elif command == "only":
            for view in window.views_in_group(group):
                if view.id() != selfview.id():
                    window.focus_view(view)
                    window.run_command("ex_quit", {"forced": forced})
            window.focus_view(selfview)
        else:
            sublime.status_message("Unknown TabControl Command")


class ExTabOpenCommand(sublime_plugin.WindowCommand):
    def run(self, file_name=None):
        self.window.run_command("tab_control", {"command": "open", "file_name": file_name}, )


class ExTabNextCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "next"}, )


class ExTabPrevCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "prev"}, )


class ExTabLastCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "last"}, )


class ExTabFirstCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command("tab_control", {"command": "first"}, )


class ExTabOnlyCommand(sublime_plugin.WindowCommand):
    def run(self, forced=False):
        self.window.run_command("tab_control", {"command": "only", "forced": forced, }, )


class ExCdCommand(IrreversibleTextCommand):
    """Ex command(s): :cd [<path>|%:h]

    Print or change the current directory.

    :cd without an argument behaves as in Unix for all platforms.
    """
    @changing_cd
    def run(self, path=None, forced=False):
        if self.view.is_dirty() and not forced:
            ex_error.display_error(ex_error.ERR_UNSAVED_CHANGES)
            return

        state = State(self.view)

        if not path:
            state.settings.vi['_cmdline_cd'] = os.path.expanduser("~")
            self.view.run_command('ex_print_working_dir')
            return

        # TODO: It seems there a few symbols that are always substituted when they represent a
        # filename. We should have a global method of substiting them.
        if path == '%:h':
            fname = self.view.file_name()
            if fname:
                state.settings.vi['_cmdline_cd'] = os.path.dirname(fname)
                self.view.run_command('ex_print_working_dir')
            return

        path = os.path.realpath(os.path.expandvars(os.path.expanduser(path)))
        if not os.path.exists(path):
            # TODO: Add error number in ex_error.py.
            ex_error.display_error(ex_error.ERR_CANT_FIND_DIR_IN_CDPATH)
            return

        state.settings.vi['_cmdline_cd'] = path
        self.view.run_command('ex_print_working_dir')


class ExCddCommand(IrreversibleTextCommand):
    """Ex command(s) [non-standard]: :cdd

    Non-standard command to change the current directory to the active
    view's path.:

    In Sublime Text, the current directory doesn't follow the active view, so
    it's convenient to be able to align both easily.

    (This command may be removed at any time.)
    """
    def run(self, forced=False):
        if self.view.is_dirty() and not forced:
            ex_error.display_error(ex_error.ERR_UNSAVED_CHANGES)
            return
        path = os.path.dirname(self.view.file_name())
        state = State(self.view)
        try:
            state.settings.vi['_cmdline_cd'] = path
            self.view.run_command('ex_print_working_dir')
        except IOError:
            ex_error.display_error(ex_error.ERR_CANT_FIND_DIR_IN_CDPATH)


class ExVsplit(sublime_plugin.WindowCommand):
    MAX_SPLITS = 4
    LAYOUT_DATA = {
        1: {"cells": [[0,0, 1, 1]], "rows": [0.0, 1.0], "cols": [0.0, 1.0]},
        2: {"cells": [[0,0, 1, 1], [1, 0, 2, 1]], "rows": [0.0, 1.0], "cols": [0.0, 0.5, 1.0]},
        3: {"cells": [[0,0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1]], "rows": [0.0, 1.0], "cols": [0.0, 0.33, 0.66, 1.0]},
        4: {"cells": [[0,0, 1, 1], [1, 0, 2, 1], [2, 0, 3, 1], [3,0, 4, 1]], "rows": [0.0, 1.0], "cols": [0.0, 0.25, 0.50, 0.75, 1.0]},
    }
    def run(self, file_name=None):
        groups = self.window.num_groups()
        if groups >= ExVsplit.MAX_SPLITS:
            sublime.status_message("Vintageous: Can't create more groups.")
            return

        old_view = self.window.active_view()
        pos = ":{0}:{1}".format(*old_view.rowcol(old_view.sel()[0].b))
        current_file_name = old_view.file_name() + pos
        self.window.run_command('set_layout', ExVsplit.LAYOUT_DATA[groups + 1])

        # TODO: rename this param.
        if file_name:
            existing = self.window.find_open_file(file_name)
            pos = ''
            if existing:
                pos = ":{0}:{1}".format(*existing.rowcol(existing.sel()[0].b))
            self.open_file(file_name + pos)
            return

        # No file name provided; clone current view into new group.
        self.open_file(current_file_name)

    def open_file(self, file_name):
        flags = (sublime.FORCE_GROUP | sublime.ENCODED_POSITION)
        self.window.open_file(file_name, group=(self.window.num_groups() - 1),
                              flags=flags)


class ExUnvsplit(sublime_plugin.WindowCommand):
    def run(self):
        groups = self.window.num_groups()
        if groups == 1:
            sublime.status_message("Vintageous: Can't delete more groups.")
            return

        # If we don't do this, cloned views will be moved to the previous group and kept around.
        # We want to close them instead.
        self.window.run_command('close')
        self.window.run_command('set_layout', ExVsplit.LAYOUT_DATA[groups - 1])


class ExSetLocal(IrreversibleTextCommand):
    def run(self, option=None, operator=None, value=None):
        if option.endswith('?'):
            ex_error.handle_not_implemented()
            return
        try:
            set_local(self.view, option, value)
        except KeyError:
            sublime.status_message("Vintageuos: No such option.")
        except ValueError:
            sublime.status_message("Vintageous: Invalid value for option.")


class ExSet(IrreversibleTextCommand):
    def run(self, option=None, operator=None, value=None):
        if option.endswith('?'):
            ex_error.handle_not_implemented()
            return
        try:
            set_global(self.view, option, value)
        except KeyError:
            sublime.status_message("Vintageuos: No such option.")
        except ValueError:
            sublime.status_message("Vintageous: Invalid value for option.")

########NEW FILE########
__FILENAME__ = ex_main
import sublime
import sublime_plugin

import os

from Vintageous.ex import ex_error
from Vintageous.ex.ex_command_parser import EX_COMMANDS
from Vintageous.ex.ex_command_parser import parse_command
from Vintageous.ex.completions import iter_paths
from Vintageous.ex.completions import parse
from Vintageous.ex.completions import parse_for_setting
from Vintageous.ex.completions import wants_fs_completions
from Vintageous.ex.completions import wants_setting_completions
from Vintageous.vi.settings import iter_settings
from Vintageous.vi.sublime import show_ipanel
from Vintageous.vi.utils import modes
from Vintageous.state import State
from Vintageous.vi.utils import mark_as_widget


def plugin_loaded():
    v = sublime.active_window().active_view()
    state = State(v)
    d = os.path.dirname(v.file_name()) if v.file_name() else os.getcwd()
    state.settings.vi['_cmdline_cd'] = d


COMPLETIONS = sorted([x[0] for x in EX_COMMANDS.keys()])

EX_HISTORY_MAX_LENGTH = 20
EX_HISTORY = {
    'cmdline': [],
    'searches': []
}


def update_command_line_history(item, slot_name):
    if len(EX_HISTORY[slot_name]) >= EX_HISTORY_MAX_LENGTH:
        EX_HISTORY[slot_name] = EX_HISTORY[slot_name][1:]
    if item in EX_HISTORY[slot_name]:
        EX_HISTORY[slot_name].pop(EX_HISTORY[slot_name].index(item))
    EX_HISTORY[slot_name].append(item)


class ViColonInput(sublime_plugin.WindowCommand):
    # Indicates whether the user issued the call.
    interactive_call = True
    def is_enabled(self):
        return bool(self.window.active_view())

    def __init__(self, window):
        sublime_plugin.WindowCommand.__init__(self, window)

    def run(self, initial_text=':', cmd_line=''):
        # non-interactive call
        if cmd_line:
            self.non_interactive = True
            self.on_done(cmd_line)
            return

        FsCompletion.invalidate()

        state = State(self.window.active_view())
        if state.mode in (modes.VISUAL, modes.VISUAL_LINE):
            initial_text = ":'<,'>" + initial_text[1:]

        v = mark_as_widget(show_ipanel(self.window,
                                       initial_text=initial_text,
                                       on_done=self.on_done,
                                       on_change=self.on_change))
        v.set_syntax_file('Packages/Vintageous/VintageousEx Cmdline.tmLanguage')
        v.settings().set('gutter', False)
        v.settings().set('rulers', [])

        state.reset_during_init = False

    def on_change(self, s):
        if ViColonInput.interactive_call:
            cmd, prefix, only_dirs = parse(s)
            if cmd:
                FsCompletion.prefix = prefix
                FsCompletion.is_stale = True
            cmd, prefix, _ = parse_for_setting(s)
            if cmd:
                ViSettingCompletion.prefix = prefix
                ViSettingCompletion.is_stale = True

            if not cmd:
                return
        ViColonInput.interactive_call = True

    def on_done(self, cmd_line):
        if not getattr(self, 'non_interactive', None):
            update_command_line_history(cmd_line, 'cmdline')
        else:
            self.non_interactive = False
        ex_cmd = parse_command(cmd_line)
        print(ex_cmd)

        if ex_cmd and ex_cmd.parse_errors:
            ex_error.display_error(ex_cmd.parse_errors[0])
            return
        if ex_cmd and ex_cmd.name:
            if ex_cmd.can_have_range:
                ex_cmd.args["line_range"] = ex_cmd.line_range
            if ex_cmd.forced:
                ex_cmd.args['forced'] = ex_cmd.forced
            self.window.run_command(ex_cmd.command, ex_cmd.args)
        else:
            ex_error.display_error(ex_error.ERR_UNKNOWN_COMMAND, cmd_line)


class ViColonRepeatLast(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return ((len(self.window.views()) > 0) and
                (len(EX_HISTORY['cmdline']) > 0))

    def run(self):
        self.window.run_command('vi_colon_input',
                                {'cmd_line': EX_HISTORY['cmdline'][-1]})


class ExCompletionsProvider(sublime_plugin.EventListener):
    CACHED_COMPLETIONS = []
    CACHED_COMPLETION_PREFIXES = []

    def on_query_completions(self, view, prefix, locations):
        if view.score_selector(0, 'text.excmdline') == 0:
            return []

        if len(prefix) + 1 != view.size():
            return []

        if prefix and prefix in self.CACHED_COMPLETION_PREFIXES:
            return self.CACHED_COMPLETIONS

        compls = [x for x in COMPLETIONS if x.startswith(prefix) and
                                            x != prefix]
        self.CACHED_COMPLETION_PREFIXES = [prefix] + compls
        # S3 can only handle lists, not iterables.
        self.CACHED_COMPLETIONS = list(zip([prefix] + compls,
                                           compls + [prefix]))

        return self.CACHED_COMPLETIONS


class CycleCmdlineHistory(sublime_plugin.TextCommand):
    HISTORY_INDEX = None
    def run(self, edit, backwards=False):
        if CycleCmdlineHistory.HISTORY_INDEX is None:
            CycleCmdlineHistory.HISTORY_INDEX = -1 if backwards else 0
        else:
            CycleCmdlineHistory.HISTORY_INDEX += -1 if backwards else 1

        if CycleCmdlineHistory.HISTORY_INDEX == len(EX_HISTORY['cmdline']) or \
            CycleCmdlineHistory.HISTORY_INDEX < -len(EX_HISTORY['cmdline']):
                CycleCmdlineHistory.HISTORY_INDEX = -1 if backwards else 0

        self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, 0, \
                EX_HISTORY['cmdline'][CycleCmdlineHistory.HISTORY_INDEX])


class HistoryIndexRestorer(sublime_plugin.EventListener):
    def on_deactivated(self, view):
        # Because views load asynchronously, do not restore history index
        # .on_activated(), but here instead. Otherwise, the .score_selector()
        # call won't yield the desired results.
        if view.score_selector(0, 'text.excmdline') > 0:
            CycleCmdlineHistory.HISTORY_INDEX = None


class WriteFsCompletion(sublime_plugin.TextCommand):
    def run(self, edit, cmd, completion):
        if self.view.score_selector(0, 'text.excmdline') == 0:
            return

        ViColonInput.interactive_call = False
        self.view.sel().clear()
        self.view.replace(edit, sublime.Region(0, self.view.size()),
                          cmd + ' ' + completion)
        self.view.sel().add(sublime.Region(self.view.size()))


class FsCompletion(sublime_plugin.TextCommand):
    # Last user-provided path string.
    prefix = ''
    frozen_dir = ''
    is_stale = False
    items = None

    @staticmethod
    def invalidate():
        FsCompletion.prefix = ''
        FsCompletion.frozen_dir = ''
        FsCompletion.is_stale = True
        FsCompletion.items = None


    def run(self, edit):
        if self.view.score_selector(0, 'text.excmdline') == 0:
            return

        state = State(self.view)
        FsCompletion.frozen_dir = (FsCompletion.frozen_dir or
                                   (state.settings.vi['_cmdline_cd'] + '/'))

        cmd, prefix, only_dirs = parse(self.view.substr(self.view.line(0)))
        if not cmd:
            return

        if not (FsCompletion.prefix or FsCompletion.items) and prefix:
            FsCompletion.prefix = prefix
            FsCompletion.is_stale = True

        if prefix == '..':
            FsCompletion.prefix = '../'
            self.view.run_command('write_fs_completion', {
                                                    'cmd': cmd,
                                                    'completion': '../'})

        if prefix == '~':
            path = os.path.expanduser(prefix) + '/'
            FsCompletion.prefix = path
            self.view.run_command('write_fs_completion', {
                                                    'cmd': cmd,
                                                    'completion': path})
            return

        if (not FsCompletion.items) or FsCompletion.is_stale:
            FsCompletion.items = iter_paths(from_dir=FsCompletion.frozen_dir,
                                            prefix=FsCompletion.prefix,
                                            only_dirs=only_dirs)
            FsCompletion.is_stale = False

        try:
            self.view.run_command('write_fs_completion', {
                                    'cmd': cmd,
                                    'completion': next(FsCompletion.items)
                                 })
        except StopIteration:
            FsCompletion.items = iter_paths(prefix=FsCompletion.prefix,
                                            from_dir=FsCompletion.frozen_dir,
                                            only_dirs=only_dirs)
            self.view.run_command('write_fs_completion', {
                                    'cmd': cmd,
                                    'completion': FsCompletion.prefix
                                  })


class ViSettingCompletion(sublime_plugin.TextCommand):
    # Last user-provided path string.
    prefix = ''
    is_stale = False
    items = None

    @staticmethod
    def invalidate():
        ViSettingCompletion.prefix = ''
        is_stale = True
        items = None

    def run(self, edit):
        if self.view.score_selector(0, 'text.excmdline') == 0:
            return

        cmd, prefix, _ = parse_for_setting(self.view.substr(self.view.line(0)))
        if not cmd:
            return
        if (ViSettingCompletion.prefix is None) and prefix:
            ViSettingCompletion.prefix = prefix
            ViSettingCompletion.is_stale = True
        elif ViSettingCompletion.prefix is None:
            ViSettingCompletion.items = iter_settings('')
            ViSettingCompletion.is_stale = False

        if not ViSettingCompletion.items or ViSettingCompletion.is_stale:
            ViSettingCompletion.items = iter_settings(ViSettingCompletion.prefix)
            ViSettingCompletion.is_stale = False

        try:
            self.view.run_command('write_fs_completion',
                                  {'cmd': cmd,
                                   'completion': next(ViSettingCompletion.items)})
        except StopIteration:
            try:
                ViSettingCompletion.items = iter_settings(ViSettingCompletion.prefix)
                self.view.run_command('write_fs_completion',
                                      {'cmd': cmd,
                                       'completion': next(ViSettingCompletion.items)})
            except StopIteration:
                return

class CmdlineContextProvider(sublime_plugin.EventListener):
    """
    Provides contexts for the cmdline input panel.
    """
    def on_query_context(self, view, key, operator, operand, match_all):
        if view.score_selector(0, 'text.excmdline') == 0:
            return

        if key == 'vi_cmdline_at_fs_completion':
            value = wants_fs_completions(view.substr(view.line(0)))
            value = value and view.sel()[0].b == view.size()
            if operator == sublime.OP_EQUAL:
                if operand == True:
                    return value
                elif operand == False:
                    return not value

        if key == 'vi_cmdline_at_setting_completion':
            value = wants_setting_completions(view.substr(view.line(0)))
            value = value and view.sel()[0].b == view.size()
            if operator == sublime.OP_EQUAL:
                if operand == True:
                    return value
                elif operand == False:
                    return not value

########NEW FILE########
__FILENAME__ = ex_motions
import sublime
import sublime_plugin

class _vi_cmd_line_a(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(1))


class _vi_cmd_line_k(sublime_plugin.TextCommand):
    def run(self, edit):
        text = self.view.substr(sublime.Region(0, self.view.sel()[0].b))
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(self.view.size()))

########NEW FILE########
__FILENAME__ = jump_list_cmds
"""Adds jump list functionality.

   Wraps Sublime Text's own jump list.
"""


import sublime
import sublime_plugin

from Default.history_list import get_jump_history


class _vi_add_to_jump_list(sublime_plugin.WindowCommand):
    def run(self):
        get_jump_history(self.window.id()).push_selection(self.window.active_view())
        hl = get_jump_history(self.window.id())

########NEW FILE########
__FILENAME__ = modelines
import sublime
import sublime_plugin

import re


MODELINE_PREFIX_TPL = "%s\\s*(st|sublime): "
DEFAULT_LINE_COMMENT = '#'
MULTIOPT_SEP = '; '
MAX_LINES_TO_CHECK = 50
LINE_LENGTH = 80
MODELINES_REG_SIZE = MAX_LINES_TO_CHECK * LINE_LENGTH


def is_modeline(prefix, line):
    return bool(re.match(prefix, line))


def gen_modelines(view):
    topRegEnd = min(MODELINES_REG_SIZE, view.size())
    candidates = view.lines(sublime.Region(0, view.full_line(topRegEnd).end()))

    # Consider modelines at the end of the buffer too.
    # There might be overlap with the top region, but it doesn't matter because
    # it means the buffer is tiny.
    pt = view.size() - MODELINES_REG_SIZE
    bottomRegStart = pt if pt > -1 else 0
    candidates += view.lines(sublime.Region(bottomRegStart, view.size()))

    prefix = build_modeline_prefix(view)
    modelines = (view.substr(c) for c in candidates if is_modeline(prefix, view.substr(c)))

    for modeline in modelines:
        yield modeline


def gen_raw_options(modelines):
    for m in modelines:
        opt = m.partition(':')[2].strip()
        if MULTIOPT_SEP in opt:
            for subopt in (s for s in opt.split(MULTIOPT_SEP)):
                yield subopt
        else:
            yield opt


def gen_modeline_options(view):
    modelines = gen_modelines(view)
    for opt in gen_raw_options(modelines):
        name, sep, value = opt.partition(' ')
        yield view.settings().set, name.rstrip(':'), value.rstrip(';')


def get_line_comment_char(view):
    commentChar = ""
    commentChar2 = ""
    try:
        for pair in view.meta_info("shellVariables", 0):
            if pair["name"] == "TM_COMMENT_START":
                commentChar = pair["value"]
            if pair["name"] == "TM_COMMENT_START_2":
                commentChar2 = pair["value"]
            if commentChar and commentChar2:
                break
    except TypeError:
        pass

    if not commentChar2:
        return re.escape(commentChar.strip())
    else:
        return "(" + re.escape(commentChar.strip()) + "|" + re.escape(commentChar2.strip()) + ")"

def build_modeline_prefix(view):
    lineComment = get_line_comment_char(view).lstrip() or DEFAULT_LINE_COMMENT
    return (MODELINE_PREFIX_TPL % lineComment)


def to_json_type(v):
    """"Convert string value to proper JSON type.
    """
    if v.lower() in ('true', 'false'):
        v = v[0].upper() + v[1:].lower()

    try:
        return eval(v, {}, {})
    except:
        raise ValueError("Could not convert to JSON type.")


class ExecuteSublimeTextModeLinesCommand(sublime_plugin.EventListener):
    """This plugin provides a feature similar to vim modelines.
    Modelines set options local to the view by declaring them in the
    source code file itself.

        Example:
        mysourcecodefile.py
        # sublime: gutter false
        # sublime: translate_tab_to_spaces true

    The top as well as the bottom of the buffer is scanned for modelines.
    MAX_LINES_TO_CHECK * LINE_LENGTH defines the size of the regions to be
    scanned.
    """
    def do_modelines(self, view):
        for setter, name, value in gen_modeline_options(view):
            if name == 'x_syntax':
                view.set_syntax_file(value)
            else:
                try:
                    setter(name, to_json_type(value))
                except ValueError as e:
                    sublime.status_message("[SublimeModelines] Bad modeline detected.")
                    print ("[SublimeModelines] Bad option detected: %s, %s" % (name, value))
                    print ("[SublimeModelines] Tip: Keys cannot be empty strings.")

    def on_load(self, view):
        self.do_modelines(view)

    def on_post_save(self, view):
        self.do_modelines(view)

########NEW FILE########
__FILENAME__ = plugins
from Vintageous.vi.utils import modes


mappings = {
   modes.NORMAL: {},
   modes.OPERATOR_PENDING: {},
   modes.VISUAL: {},
   modes.VISUAL_LINE: {},
   modes.VISUAL_BLOCK: {},
   modes.SELECT: {},
}

classes = {}


def register(seq, modes, *args, **kwargs):
    """
    Registers a 'key sequence' to 'command' mapping with Vintageous.

    The registered key sequence must be known to Vintageous. The
    registered command must be a ViMotionDef or ViOperatorDef.

    The decorated class is instantiated with `*args` and `**kwargs`.

    @keys
      A list of (`mode`, `sequence`) pairs to map the decorated
      class to.
    """
    def inner(cls):
        for mode in modes:
                mappings[mode][seq] = cls(*args, **kwargs)
                classes[cls.__name__] = cls
        return cls
    return inner

########NEW FILE########
__FILENAME__ = state
from collections import Counter

import sublime

from Vintageous import local_logger
from Vintageous.vi import utils
from Vintageous.vi.utils import input_types
from Vintageous.vi.contexts import KeyContext
from Vintageous.vi.dot_file import DotFile
from Vintageous.vi.marks import Marks
from Vintageous.vi.registers import Registers
from Vintageous.vi.settings import SettingsManager
from Vintageous.vi.utils import directions
from Vintageous.vi.utils import is_view
from Vintageous.vi.utils import is_ignored
from Vintageous.vi.utils import is_ignored_but_command_mode
from Vintageous.vi.utils import modes
from Vintageous.vi import cmd_defs
from Vintageous.vi import cmd_base
# !! Avoid error due to sublime_plugin.py:45 expectations.
from Vintageous.plugins import plugins as user_plugins


_logger = local_logger(__name__)


def _init_vintageous(view, new_session=False):
    """
    Initializes global data. Runs at startup and every time a view gets
    activated, loaded, etc.

    @new_session
      Whether we're starting up Sublime Text. If so, volatile data must be
      wiped.
    """

    if not is_view(view):
        # Abort if we got a widget, panel...
        _logger().info(
            '[_init_vintageous] ignoring view: {0}'.format(
                view.name() or view.file_name() or '<???>'))
        try:
            # XXX: All this seems to be necessary here.
            if not is_ignored_but_command_mode(view):
                view.settings().set('command_mode', False)
                view.settings().set('inverse_caret_state', False)
            view.settings().erase('vintage')
            if is_ignored(view):
                # Someone has intentionally disabled Vintageous, so let the user know.
                sublime.status_message(
                    'Vintageous: Vim emulation disabled for the current view')
        except AttributeError:
            _logger().info(
                '[_init_vintageous] probably received the console view')
        except Exception:
            _logger().error('[_init_vintageous] error initializing view')
        finally:
            return

    state = State(view)

    if not state.reset_during_init:
        # Probably exiting from an input panel, like when using '/'. Don't
        # reset the global state, as it may contain data needed to complete
        # the command that's being built.
        state.reset_during_init = True
        return

    # Non-standard user setting.
    reset = state.settings.view['vintageous_reset_mode_when_switching_tabs']
    # XXX: If the view was already in normal mode, we still need to run the
    # init code. I believe this is due to Sublime Text (intentionally) not
    # serializing the inverted caret state and the command_mode setting when
    # first loading a file.
    # If the mode is unknown, it might be a new file. Let normal mode setup
    # continue.
    if not reset and (state.mode not in (modes.NORMAL, modes.UNKNOWN)):
        return

    # If we have no selections, add one.
    if len(state.view.sel()) == 0:
        state.view.sel().add(sublime.Region(0))

    state.logger.info('[_init_vintageous] running init')

    if state.mode in (modes.VISUAL, modes.VISUAL_LINE):
        # TODO: Don't we need to pass a mode here?
        view.window().run_command('_enter_normal_mode', {'from_init': True})

    elif state.mode in (modes.INSERT, modes.REPLACE):
        # TODO: Don't we need to pass a mode here?
        view.window().run_command('_enter_normal_mode', {'from_init': True})

    elif (view.has_non_empty_selection_region() and
          state.mode != modes.VISUAL):
            # Runs, for example, when we've performed a search via ST3 search
            # panel and we've pressed 'Find All'. In this case, we want to
            # ensure a consistent state for multiple selections.
            # TODO: We could end up with multiple selections in other ways
            #       that bypass _init_vintageous.
            state.mode = modes.VISUAL

    else:
        # This may be run when we're coming from cmdline mode.
        pseudo_visual = view.has_non_empty_selection_region()
        mode = modes.VISUAL if pseudo_visual else state.mode
        # TODO: Maybe the above should be handled by State?
        state.enter_normal_mode()
        view.window().run_command('_enter_normal_mode', {'mode': mode,
                                                         'from_init': True})

    state.reset_command_data()
    if new_session:
        state.reset_volatile_data()

        # Load settings.
        DotFile.from_user().run()


# TODO: Implement this
plugin_manager = None


# TODO: Test me.
def plugin_loaded():
    view = sublime.active_window().active_view()
    _init_vintageous(view, new_session=True)


# TODO: Test me.
def plugin_unloaded():
    view = sublime.active_window().active_view()
    try:
        view.settings().set('command_mode', False)
        view.settings().set('inverse_caret_state', False)
    except AttributeError:
        _logger().warn(
            'could not access sublime.active_window().active_view().settings '
            ' while unloading')
        pass


class State(object):
    """
    Manages global state needed to build commands and control modes, etc.

    Usage:
      Before using it, always instantiate with the view commands are going to
      target. `State` uses view.settings() and window.settings() for data
      storage.
    """

    registers = Registers()
    marks = Marks()
    context = KeyContext()

    def __init__(self, view):
        self.view = view
        # We have multiple types of settings: vi-specific (settings.vi) and
        # regular ST view settings (settings.view) and window settings
        # (settings.window).
        # TODO: Make this a descriptor. Why isn't it?
        self.settings = SettingsManager(self.view)

        _logger().info(
            '[State] is .view an ST:Vintageous widget: {0}:{1}'.format(
                bool(self.settings.view['is_widget']),
                bool(self.settings.view['is_vintageous_widget'])))

    @property
    def glue_until_normal_mode(self):
        """
        Indicates that editing commands should be grouped together in a single
        undo step once the user requests `_enter_normal_mode`.

        This property is *VOLATILE*; it shouldn't be persisted between
        sessions.
        """
        # FIXME: What happens when we have an incomplete command and we switch
        #        views? We should clean up.
        # TODO: Make this a window setting.
        return self.settings.vi['_vintageous_glue_until_normal_mode'] or False

    @glue_until_normal_mode.setter
    def glue_until_normal_mode(self, value):
        self.settings.vi['_vintageous_glue_until_normal_mode'] = value

    @property
    def gluing_sequence(self):
        """
        Indicates whether `PressKeys` is running a command and is grouping all
        of the edits in one single undo step.

        This property is *VOLATILE*; it shouldn't be persisted between
        sessions.
        """
        # TODO: Store this as a window setting.
        return self.settings.vi['_vintageous_gluing_sequence'] or False

    @gluing_sequence.setter
    def gluing_sequence(self, value):
        self.settings.vi['_vintageous_gluing_sequence'] = value

    @property
    def non_interactive(self):
        # FIXME: This property seems to do the same as gluing_sequence.
        """
        Indicates whether `PressKeys` is running a command and no interactive
        prompts should be used (for example, by the '/' motion.)

        This property is *VOLATILE*; it shouldn't be persisted between
        sessions.
        """
        # TODO: Store this as a window setting.
        return self.settings.vi['_vintageous_non_interactive'] or False

    @non_interactive.setter
    def non_interactive(self, value):
        if not isinstance(value, bool):
            raise ValueError('expected bool')

        self.settings.vi['_vintageous_non_interactive'] = value

    @property
    def last_character_search(self):
        """
        Last character used as input for 'f' or 't'.
        """
        return self.settings.window['_vintageous_last_character_search'] or ''

    @last_character_search.setter
    def last_character_search(self, value):
        self.settings.window['_vintageous_last_character_search'] = value

    @property
    def last_char_search_command(self):
        """
        ',' and ';' change directions depending on whether 'f' or 't' was
        issued previously.

        Returns the name of the last character search command, namely one of:
        vi_f, vi_t, vi_big_f, vi_big_t.
        """
        ok = self.settings.window['_vintageous_last_char_search_command']
        return ok or 'vi_f'

    @last_char_search_command.setter
    def last_char_search_command(self, value):
        # FIXME: It isn't working.
        self.settings.window['_vintageous_last_char_search_command'] = value

    @property
    def capture_register(self):
        """
        Returns `True` if `State` is expecting a register name next.
        """
        return self.settings.vi['capture_register'] or False

    @capture_register.setter
    def capture_register(self, value):
        self.settings.vi['capture_register'] = value

    @property
    def last_buffer_search(self):
        """
        Returns the last string used by buffer search commands such as '/' and
        '?'.
        """
        return self.settings.window['_vintageous_last_buffer_search'] or ''

    @last_buffer_search.setter
    def last_buffer_search(self, value):
        self.settings.window['_vintageous_last_buffer_search'] = value

    @property
    def reset_during_init(self):
        # Some commands gather user input through input panels. An input panel
        # is just a view, so when it's closed, the previous view gets
        # activated and Vintageous init code runs. In this case, however, we
        # most likely want the global state to remain unchanged. This variable
        # helps to signal this.
        #
        # For an example, see the '_vi_slash' command.
        value = self.settings.window['_vintageous_reset_during_init']
        if not isinstance(value, bool):
            return True
        return value

    @reset_during_init.setter
    def reset_during_init(self, value):
        if not isinstance(value, bool):
            raise ValueError('expected a bool')

        self.settings.window['_vintageous_reset_during_init'] = value

    # This property isn't reset automatically. _enter_normal_mode mode must
    # take care of that so it can repeat the commands issues while in
    # insert mode.
    @property
    def normal_insert_count(self):
        """
        Count issued to 'i' or 'a', etc. These commands enter insert mode.
        If passed a count, they must repeat the commands issued while in
        insert mode.
        """
        return self.settings.vi['normal_insert_count'] or '1'

    @normal_insert_count.setter
    def normal_insert_count(self, value):
        self.settings.vi['normal_insert_count'] = value

    # TODO: Make these simple properties that access settings descriptors?
    @property
    def sequence(self):
        """
        Sequence of keys that build the command.
        """
        return self.settings.vi['sequence'] or ''

    @sequence.setter
    def sequence(self, value):
        self.settings.vi['sequence'] = value

    @property
    def partial_sequence(self):
        """
        Sometimes we need to store a partial sequence to obtain the commands'
        full name. Such is the case of `gD`, for example.
        """
        return self.settings.vi['partial_sequence'] or ''

    @partial_sequence.setter
    def partial_sequence(self, value):
        self.settings.vi['partial_sequence'] = value

    @property
    def mode(self):
        """
        Current mode. It isn't guaranteed that the underlying view's .sel()
        will be in a consistent state (for example, that it will at least
        have one non-empty region in visual mode.
        """
        return self.settings.vi['mode'] or modes.UNKNOWN

    @mode.setter
    def mode(self, value):
        self.settings.vi['mode'] = value

    @property
    def action(self):
        val = self.settings.vi['action'] or None
        if val:
            cls = getattr(cmd_defs, val['name'], None)
            if cls is None:
                cls = user_plugins.classes[val['name']]
            return cls.from_json(val['data'])

    @action.setter
    def action(self, value):
        v = value.serialize() if value else None
        self.settings.vi['action'] = v

    @property
    def motion(self):
        val = self.settings.vi['motion'] or None
        if val:
            # TODO: Encapsulate further.
            cls = getattr(cmd_defs, val['name'])
            return cls.from_json(val['data'])

    @motion.setter
    def motion(self, value):
        v = value.serialize() if value else None
        self.settings.vi['motion'] = v

    @property
    def motion_count(self):
        return self.settings.vi['motion_count'] or ''

    @motion_count.setter
    def motion_count(self, value):
        self.settings.vi['motion_count'] = value

    @property
    def action_count(self):
        return self.settings.vi['action_count'] or ''

    @action_count.setter
    def action_count(self, value):
        self.settings.vi['action_count'] = value

    @property
    def repeat_data(self):
        """
        Stores (type, cmd_name_or_key_seq, , mode) so '.' can use them.

        `type` may be 'vi' or 'native'. `vi`-commands are executed VIA_PANEL
        `PressKeys`, while `native`-commands are executed via .run_command().
        """
        return self.settings.vi['repeat_data'] or None

    @repeat_data.setter
    def repeat_data(self, value):
        self.logger.info("setting repeat data {0}".format(value))
        self.settings.vi['repeat_data'] = value

    @property
    def last_macro(self):
        """
        Stores the last recorded macro.
        """
        return self.settings.window['_vintageous_last_macro'] or None

    @last_macro.setter
    def last_macro(self, value):
        """
        Stores the last recorded macro.
        """
        # FIXME: Check that we're storing a valid macro?
        self.settings.window['_vintageous_last_macro'] = value

    @property
    def recording_macro(self):
        return self.settings.window['_vintageous_recording_macro'] or False

    @recording_macro.setter
    def recording_macro(self, value):
        # FIXME: Check that we're storing a bool?
        self.settings.window['_vintageous_recording_macro'] = value

    @property
    def count(self):
        """
        Calculates the actual count for the current command.
        """
        c = 1
        if self.action_count and not self.action_count.isdigit():
            raise ValueError('action count must be a digit')

        if self.motion_count and not self.motion_count.isdigit():
            raise ValueError('motion count must be a digit')

        if self.action_count:
            c = int(self.action_count) or 1

        if self.motion_count:
            c *= (int(self.motion_count) or 1)

        if c < 1:
            raise ValueError('count must be greater than 0')

        return c

    @property
    def xpos(self):
        """
        Stores the current xpos for carets.
        """
        return self.settings.vi['xpos'] or 0

    @xpos.setter
    def xpos(self, value):
        if not isinstance(value, int):
            raise ValueError('xpos must be an int')

        self.settings.vi['xpos'] = value

    @property
    def visual_block_direction(self):
        """
        Stores the current visual block direction for the current selection.
        """
        return self.settings.vi['visual_block_direction'] or directions.DOWN

    @visual_block_direction.setter
    def visual_block_direction(self, value):
        if not isinstance(value, int):
            raise ValueError('visual_block_direction must be an int')

        self.settings.vi['visual_block_direction'] = value

    @property
    def logger(self):
        # FIXME: potentially very slow?
        # return get_logger()
        global _logger
        return _logger()

    @property
    def register(self):
        """
        Stores the current open register, as requested by the user.
        """
        # TODO: Maybe unify with Registers?
        # TODO: Validate register name?
        return self.settings.vi['register'] or '"'

    @register.setter
    def register(self, value):
        if len(str(value)) > 1:
            raise ValueError('register must be an character')

        self.logger.info('opening register {0}'.format(value))
        self.settings.vi['register'] = value
        self.capture_register = False

    @property
    def must_collect_input(self):
        """
        Returns `True` if state must collect input for the current motion or
        operator.
        """
        if self.motion and self.action:
            if self.motion.accept_input:
                return True

            return (self.action.accept_input and
                    self.action.input_parser.type == input_types.AFTER_MOTION)

        if (self.action and
            self.action.accept_input and
            self.action.input_parser.type == input_types.INMEDIATE):
                return True

        if self.motion:
            return self.motion and self.motion.accept_input

    @property
    def must_update_xpos(self):
        if self.motion and self.motion.updates_xpos:
            return True

        if self.action and self.action.updates_xpos:
            return True

    def pop_parser(self):
        # parsers = self.input_parsers
        # current = parsers.pop()
        # self.input_parsers = parsers
        # return current
        return None

    def enter_normal_mode(self):
        self.mode = modes.NORMAL

    def enter_visual_mode(self):
        self.mode = modes.VISUAL

    def enter_visual_line_mode(self):
        self.mode = modes.VISUAL_LINE

    def enter_insert_mode(self):
        self.mode = modes.INSERT

    def enter_replace_mode(self):
        self.mode = modes.REPLACE

    def enter_select_mode(self):
        self.mode = modes.SELECT

    def enter_visual_block_mode(self):
        self.mode = modes.VISUAL_BLOCK

    def reset_sequence(self):
        self.sequence = ''

    def display_status(self):
        msg = "{0} {1}"
        mode_name = modes.to_friendly_name(self.mode)
        mode_name = '-- {0} --'.format(mode_name) if mode_name else ''
        sublime.status_message(msg.format(mode_name, self.sequence))

    def reset_partial_sequence(self):
        self.partial_sequence = ''

    def reset_register_data(self):
        self.register = '"'
        self.capture_register = False

    def must_scroll_into_view(self):
        return (self.motion and self.motion.scroll_into_view)

    def scroll_into_view(self):
        v = sublime.active_window().active_view()
        # Make sure we show the first caret on the screen, but don't show
        # its surroundings.
        v.show(v.sel()[0], False)

    def reset_command_data(self):
        # Resets all temporary data needed to build a command or partial
        # command to their default values.
        self.update_xpos()
        if self.must_scroll_into_view():
            self.scroll_into_view()
        self.action and self.action.reset()
        self.action = None
        self.motion and self.motion.reset()
        self.motion = None
        self.action_count = ''
        self.motion_count = ''

        self.reset_sequence()
        self.reset_partial_sequence()
        self.reset_register_data()

    def update_xpos(self, force=False):
        if self.must_update_xpos or force:
            try:
                sel = self.view.sel()[0]
                pos = sel.b
                # TODO: we should check the current mode instead.
                if not sel.empty():
                    if sel.a < sel.b:
                        pos -= 1
                r = sublime.Region(self.view.line(pos).a, pos)
                counter = Counter(self.view.substr(r))
                tab_size = self.view.settings().get('tab_size')
                xpos = (self.view.rowcol(pos)[1] +
                        ((counter['\t'] * tab_size) - counter['\t']))
            except Exception as e:
                print(e)
                print('Vintageous: Error when setting xpos. Defaulting to 0.')
                self.xpos = 0
                return
            else:
                self.xpos = xpos

    def reset(self):
        # TODO: Remove this when we've ported all commands. This is here for
        # retrocompatibility.
        self.reset_command_data()

    def reset_volatile_data(self):
        """
        Resets window- or application-wide data to their default values when
        starting a new Vintageous session.
        """
        self.glue_until_normal_mode = False
        self.view.run_command('unmark_undo_groups_for_gluing')
        self.gluing_sequence = False
        self.non_interactive = False
        self.reset_during_init = True

    def _set_parsers(self, command):
        """
        Returns `True` if we've had to run an immediate parser via an input
        panel.
        """
        if command.accept_input:
            return self._run_parser_via_panel(command)

    def _run_parser_via_panel(self, command):
        """
        Returns `True` if the current parser needs to be run via a panel.

        If needed, it runs the input-panel-based parser.
        """
        if command.input_parser.type == input_types.VIA_PANEL:
            if self.non_interactive:
                return False
            sublime.active_window().run_command(command.input_parser.command)
            return True
        return False

    def process_user_input2(self, key):
        assert self.must_collect_input, "call only if input is required"

        _logger().info('[State] processing input {0}'.format(key))

        if self.motion and self.motion.accept_input:
            motion = self.motion
            # TODO: Rmove this.
            val = motion.accept(key)
            self.motion = motion
            return val

        action = self.action
        val = action.accept(key)
        self.action = action
        return val

    def set_command(self, command):
        """
        Sets the current command to @command.

        @command
          A command definition as found in `keys.py`.
        """
        assert isinstance(command, cmd_base.ViCommandDefBase), \
            'ViCommandDefBase expected, got {0}'.format(type(command))

        if isinstance(command, cmd_base.ViMotionDef):
            if self.runnable():
                # We already have a motion, so this looks like an error.
                raise ValueError('too many motions')

            self.motion = command
            if self.mode == modes.OPERATOR_PENDING:
                self.mode = modes.NORMAL

            if self._set_parsers(command):
                return

        elif isinstance(command, cmd_base.ViOperatorDef):
            if self.runnable():
                # We already have an action, so this looks like an error.
                raise ValueError('too many actions')

            self.action = command
            if (self.action.motion_required and
                not self.in_any_visual_mode()):
                    self.mode = modes.OPERATOR_PENDING

            if self._set_parsers(command):
                return

        else:
            self.logger.info("[State] command: {0}".format(command))
            raise ValueError('unexpected command type')

    def in_any_visual_mode(self):
        return (self.mode in (modes.VISUAL,
                              modes.VISUAL_LINE,
                              modes.VISUAL_BLOCK))

    def can_run_action(self):
        if (self.action and
            (not self.action['motion_required'] or
             self.in_any_visual_mode())):
                return True

    def get_visual_repeat_data(self):
        """
        Returns the data needed to repeat a visual mode command in normal mode.
        """
        if self.mode not in (modes.VISUAL, modes.VISUAL_LINE):
            return

        first_sel = self.view.sel()[0]
        lines = (utils.row_at(self.view, first_sel.end()) -
                 utils.row_at(self.view, first_sel.begin()))
        if lines > 0:
            chars = self.view.rowcol(first_sel.end())[1]
        else:
            chars = first_sel.size()

        return (lines, chars, self.mode)

    def restore_visual_data(self, data):
        row_count, chars, old_mode = data
        first_sel = self.view.sel()[0]
        if old_mode == modes.VISUAL:
            if (data[0] > 0):
                end = self.view.text_point(
                    self.view.rowcol(first_sel.b)[0] + data[0],
                    data[1])
            else:
                end = first_sel.b + data[1]
            self.view.sel().add(sublime.Region(first_sel.b, end))
            self.mode = modes.VISUAL

        elif old_mode == modes.VISUAL_LINE:
            row_count, _, old_mode = data
            begin = self.view.line(first_sel.b).a
            end = self.view.text_point(utils.row_at(self.view, begin) +
                                       (row_count - 1), 0)
            end = self.view.full_line(end).b
            self.view.sel().add(sublime.Region(begin, end))
            self.mode = modes.VISUAL_LINE
        else:
            pass

    def runnable(self):
        """
        Returns `True` if we can run the state data as it is.
        """
        if self.must_collect_input:
            return False

        if self.action and self.motion:
            if self.mode != modes.NORMAL:
                raise ValueError('wrong mode')
            return True

        if self.can_run_action():
            if self.mode == modes.OPERATOR_PENDING:
                raise ValueError('wrong mode')
            return True

        if self.motion:
            if self.mode == modes.OPERATOR_PENDING:
                raise ValueError('wrong mode')
            return True

        return False

    def eval(self):
        """
        Run data as a command if possible.
        """
        if self.runnable():
            if self.action and self.motion:
                action_cmd = self.action.translate(self)
                motion_cmd = self.motion.translate(self)
                self.logger.info(
                    '[State] full command, switching to internal normal mode')
                self.mode = modes.INTERNAL_NORMAL

                # TODO: Make a requirement that motions and actions take a
                # 'mode' param.
                if 'mode' in action_cmd['action_args']:
                    action_cmd['action_args']['mode'] = modes.INTERNAL_NORMAL

                if 'mode' in motion_cmd['motion_args']:
                    motion_cmd['motion_args']['mode'] = modes.INTERNAL_NORMAL

                args = action_cmd['action_args']
                args['count'] = 1
                # let the action run the motion within its edit object so that
                # we don't need to worry about grouping edits to the buffer.
                args['motion'] = motion_cmd
                self.logger.info(
                    '[Stage] motion in motion+action: {0}'.format(motion_cmd))

                if self.glue_until_normal_mode and not self.gluing_sequence:
                    # We need to tell Sublime Text now that it should group
                    # all the next edits until we enter normal mode again.
                    sublime.active_window().run_command(
                        'mark_undo_groups_for_gluing')

                sublime.active_window().run_command(action_cmd['action'], args)
                if not self.non_interactive:
                    if self.action.repeatable:
                        self.repeat_data = ('vi', str(self.sequence),
                                            self.mode, None)
                self.reset_command_data()
                return

            if self.motion:
                motion_cmd = self.motion.translate(self)
                self.logger.info(
                    '[State] lone motion cmd: {0}'.format(motion_cmd))

                # We know that all motions are subclasses of ViTextCommandBase,
                # so it's safe to call them from the current view.
                # TODO: State should know about each command's type hierarchy.
                #       Example:
                #           runner = self.resolve_runner('_vi_dollar')
                #           # runner ==> view.run_command
                self.view.run_command(motion_cmd['motion'],
                                      motion_cmd['motion_args'])

            if self.action:
                action_cmd = self.action.translate(self)
                self.logger.info('[Stage] lone action cmd '.format(action_cmd))
                if self.mode == modes.NORMAL:
                    self.logger.info(
                        '[State] switching to internal normal mode')
                    self.mode = modes.INTERNAL_NORMAL

                    if 'mode' in action_cmd['action_args']:
                        action_cmd['action_args']['mode'] = \
                            modes.INTERNAL_NORMAL
                elif self.mode in (modes.VISUAL, modes.VISUAL_LINE):
                    self.view.add_regions('visual_sel', list(self.view.sel()))

                # Some commands, like 'i' or 'a', open a series of edits that
                # need to be grouped together unless we are gluing a larger
                # sequence through PressKeys. For example, aFOOBAR<Esc> should
                # be grouped atomically, but not inside a sequence like
                # iXXX<Esc>llaYYY<Esc>, where we want to group the whole
                # sequence instead.
                if self.glue_until_normal_mode and not self.gluing_sequence:
                    sublime.active_window().run_command(
                        'mark_undo_groups_for_gluing')

                seq = self.sequence
                visual_repeat_data = self.get_visual_repeat_data()
                action = self.action

                sublime.active_window().run_command(action_cmd['action'],
                                                    action_cmd['action_args'])

                if not (self.gluing_sequence and self.glue_until_normal_mode):
                    if action.repeatable:
                        self.repeat_data = ('vi', seq, self.mode,
                                            visual_repeat_data)

            self.logger.info(
                'running command: action: {0} motion: {1}'.format(self.action,
                                                                  self.motion))

            if self.mode == modes.INTERNAL_NORMAL:
                self.enter_normal_mode()
            self.reset_command_data()

########NEW FILE########
__FILENAME__ = test_vi_big_b
from collections import namedtuple

from Vintageous.vi.utils import modes
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content sel params expected actual_func msg')

TESTS = (
    test_data(content='abc', sel=[[(0, 2), (0, 2)]],
              params={'mode': modes.NORMAL}, expected=[(0, 0), (0, 0)],
              actual_func=first_sel,  msg='moves to BOF from single word in file (normal mode)'),
    test_data(content='abc abc', sel=[[(0, 4), (0, 4)]],
              params={'mode': modes.NORMAL},  expected=[(0, 0), (0, 0)],
              actual_func=first_sel,  msg='moves to BOF from second word start (normal mode)'),
    test_data(content='abc a', sel=[[(0, 4), (0, 4)]],
              params={'mode': modes.NORMAL}, expected=[(0, 0), (0, 0)],
              actual_func=first_sel,  msg='moves to BOF from second word start (1-char long) (normal mode)'),

    test_data(content='abc abc', sel=[[(0, 5), (0, 5)]],
              params={'mode': modes.NORMAL, 'count': 2}, expected=[(0, 0), (0, 0)],
              actual_func=first_sel, msg='moves to BOF from second word (count 2) (normal mode)'),

    test_data(content='abc abc', sel=[[(0, 5), (0, 5)]],
              params={'mode': modes.NORMAL, 'count': 10}, expected=[(0, 0), (0, 0)],
              actual_func=first_sel, msg='moves to BOF from second word (excessive count) (normal mode)'),

    test_data(content='abc', sel=[[(0, 2), (0, 3)]],
              params={'mode': modes.VISUAL}, expected=[(0, 3), (0, 0)],
              actual_func=first_sel, msg='moves to BOF from single word in file (visual mode)'),
    test_data(content='abc abc', sel=[[(0, 4), (0, 5)]],
              params={'mode': modes.VISUAL},  expected=[(0, 5), (0, 0)],
              actual_func=first_sel, msg='moves to BOF from second word start (visual mode)'),
    test_data(content='abc a', sel=[[(0, 4), (0, 5)]],
              params={'mode': modes.VISUAL}, expected=[(0, 5), (0, 0)],
              actual_func=first_sel, msg='moves to BOF from second word start (1-char long) (visual mode)'),

    test_data(content='abc abc', sel=[[(0, 4), (0, 7)]],
              params={'mode': modes.VISUAL}, expected=[(0, 4), (0, 5)],
              actual_func=first_sel, msg='moves to word start from 1-word selection (visual mode)'),
    test_data(content='abc abc', sel=[[(0, 0), (0, 8)]],
              params={'mode': modes.VISUAL}, expected=[(0, 0), (0, 5)],
              actual_func=first_sel, msg='moves to previous word start from multiword selection (visual mode)'),
    )


class Test_vi_b(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.content)
            for region in data.sel:
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_big_b', data.params)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            actual = data.actual_func(self.view)
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test_vi_big_p
import sublime

from collections import namedtuple

from Vintageous.vi.utils import modes
from Vintageous.vi import registers

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content regions in_register params expected msg')

R = sublime.Region

TESTS = (
    # INTERNAL NORMAL MODE
    test_data(content='abc',
              regions=[[(0, 0), (0, 0)]],
              in_register=['xxx'], params={'mode': modes.INTERNAL_NORMAL, 'count': 1},
              expected=('xxxabc', R(2, 2)), msg='failed in {0}'),

    # INTERNAL NORMAL MODE - linewise
    test_data(content='abc',
              regions=[[(0, 0), (0, 0)]],
              in_register=['xxx\n'], params={'mode': modes.INTERNAL_NORMAL, 'count': 1},
              expected=('xxx\nabc', R(0, 0)), msg='failed in {0}'),

    # VISUAL MODE
    test_data(content='abc',
              regions=[[(0, 0), (0, 3)]],
              in_register=['xxx'], params={'mode': modes.VISUAL, 'count': 1},
              expected=('xxx', R(2, 2)), msg='failed in {0}'),

    # VISUAL MODE - linewise
    test_data(content='aaa bbb ccc',
              regions=[[(0, 4), (0, 7)]],
              in_register=['xxx\n'], params={'mode': modes.VISUAL, 'count': 1},
              expected=('aaa \nxxx\n ccc', R(5, 5)), msg='failed in {0}'),
)


class Test__vi_big_p(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.content)
            for region in data.regions:
                add_sel(self.view, self.R(*region))

            self.view.settings().set('vintageous_use_sys_clipboard', False)
            registers._REGISTER_DATA['"'] = data.in_register

            self.view.run_command('_vi_big_p', data.params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual_1 = self.view.substr(self.R(0, self.view.size()))
            actual_2 = self.view.sel()[0]
            self.assertEqual(data.expected[0], actual_1, msg.format(i))
            self.assertEqual(data.expected[1], actual_2, msg.format(i))

########NEW FILE########
__FILENAME__ = test__ctrl_x_and__ctrl_a
import unittest
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected msg')

TESTS = (
    test_data('abc aaa100bbb abc', [[(0, 0), (0, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa110bbb abc', ''),
    test_data('abc aaa-100bbb abc', [[(0, 0), (0, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa-90bbb abc', ''),

    test_data('abc aaa100bbb abc', [[(0, 8), (0, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa110bbb abc', ''),
    test_data('abc aaa-100bbb abc', [[(0, 8), (0, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa-90bbb abc', ''),

    test_data('abc aaa100bbb abc\nabc aaa100bbb abc', [[(0, 0), (0, 0)], [(1, 0), (1, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa110bbb abc\nabc aaa110bbb abc', ''),
    test_data('abc aaa-100bbb abc\nabc aaa-100bbb abc', [[(0, 0), (0, 0)], [(1, 0), (1, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa-90bbb abc\nabc aaa-90bbb abc', ''),

    test_data('abc aaa100bbb abc\nabc aaa100bbb abc', [[(0, 8), (0, 8)], [(1, 8), (1, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa110bbb abc\nabc aaa110bbb abc', ''),
    test_data('abc aaa-100bbb abc\nabc aaa-100bbb abc', [[(0, 0), (0, 0)], [(1, 8), (1, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10}, 'abc aaa-90bbb abc\nabc aaa-90bbb abc', ''),

    test_data('abc aaa100bbb abc', [[(0, 0), (0, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa90bbb abc', ''),
    test_data('abc aaa-100bbb abc', [[(0, 0), (0, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa-110bbb abc', ''),

    test_data('abc aaa100bbb abc', [[(0, 8), (0, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa90bbb abc', ''),
    test_data('abc aaa-100bbb abc', [[(0, 8), (0, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa-110bbb abc', ''),

    test_data('abc aaa100bbb abc\nabc aaa100bbb abc', [[(0, 0), (0, 0)], [(1, 0), (1, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa90bbb abc\nabc aaa90bbb abc', ''),
    test_data('abc aaa-100bbb abc\nabc aaa-100bbb abc', [[(0, 0), (0, 0)], [(1, 0), (1, 0)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa-110bbb abc\nabc aaa-110bbb abc', ''),

    test_data('abc aaa100bbb abc\nabc aaa100bbb abc', [[(0, 8), (0, 8)], [(1, 8), (1, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa90bbb abc\nabc aaa90bbb abc', ''),
    test_data('abc aaa-100bbb abc\nabc aaa-100bbb abc', [[(0, 0), (0, 0)], [(1, 8), (1, 8)]], {'mode':modes.INTERNAL_NORMAL, 'count': 10, 'subtract': True}, 'abc aaa-110bbb abc\nabc aaa-110bbb abc', ''),

    # TODO: Test with sels on same line.
    # TODO: Test with standalone number.
    # TODO: Test with number followed by suffix.
)


class Test__vi_ctrl_x(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_modify_numbers', data.cmd_params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual = self.view.substr(self.R(0, self.view.size()))
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_antilambda
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected msg')

TESTS = (
    test_data('    abc',                   [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 1}, 'abc',               'failed in {0}'),
    test_data('        abc',               [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 1}, '    abc',           'failed in {0}'),
    test_data('    abc\n    abc',          [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 2}, 'abc\nabc',          'failed in {0}'),
    test_data('    abc\n    abc\n    abc', [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 3}, 'abc\nabc\nabc',     'failed in {0}'),
    test_data('    abc\n    abc\n    abc', [[(0, 0), (0, 0)], [(1, 0), (1, 0)]], {'mode': modes.INTERNAL_NORMAL, 'count': 1}, 'abc\nabc\n    abc', 'failed in {0}'),
)


class Test__vi_double_antilambda(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                add_sel(self.view, self.R(*region))

            self.view.run_command('_vi_less_than_less_than', data.cmd_params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual = self.view.substr(self.R(0, self.view.size()))
            self.assertEqual(data.expected, actual, msg.format(i))

########NEW FILE########
__FILENAME__ = test__vi_b
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected actual_func msg')

TESTS_NORMAL_MODE_SINGLE_SEL = (
    test_data(initial_text='abc',     regions=[[(0, 2), (0, 2)]], cmd_params={'mode': modes.NORMAL},  expected=[(0, 0), (0, 0)], actual_func=first_sel,  msg=''),
    test_data(initial_text='abc abc', regions=[[(0, 4), (0, 4)]], cmd_params={'mode': modes.NORMAL},  expected=[(0, 0), (0, 0)], actual_func=first_sel,  msg=''),
    test_data(initial_text='abc a',   regions=[[(0, 4), (0, 4)]], cmd_params={'mode': modes.NORMAL},  expected=[(0, 0), (0, 0)], actual_func=first_sel,  msg=''),
    )

TESTS_VISUAL_MODE_SINGLE_SEL_START_LEN_1 = (
    test_data(initial_text='abc',   regions=[[(0, 2), (0, 3)]], cmd_params={'mode': modes.VISUAL},  expected=[(0, 3), (0, 0)], actual_func=first_sel,  msg=''),
    test_data(initial_text='abc a', regions=[[(0, 4), (0, 5)]], cmd_params={'mode': modes.VISUAL},  expected=[(0, 5), (0, 0)], actual_func=first_sel,  msg=''),
    )

TESTS = TESTS_NORMAL_MODE_SINGLE_SEL + TESTS_VISUAL_MODE_SINGLE_SEL_START_LEN_1


class Test_vi_b(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_b', data.cmd_params)

            msg = "failed at test index {0} {1}".format(i, data.msg)
            actual = data.actual_func(self.view)
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_big_a
"""
Tests for o motion (visual kind).
"""

from Vintageous.vi.utils import modes

from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


class Test_vi_big_a_InNormalMode_SingleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R(0, 2))

        self.view.run_command('_vi_big_a', {'mode': modes.INTERNAL_NORMAL, 'count': 1})
        self.assertEqual(self.R(3, 3), first_sel(self.view))


class Test_vi_big_a_InNormalMode_MultipleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc\nabc')
        self.clear_sel()
        self.view.sel().add(self.R((0, 1), (0, 1)))
        self.view.sel().add(self.R((1, 1), (1, 1)))

        self.view.run_command('_vi_big_a', {'mode': modes.INTERNAL_NORMAL, 'count': 1})

        self.assertEqual(self.R(3, 3), first_sel(self.view))
        self.assertEqual(self.R((1, 3), (1, 3)), second_sel(self.view))


class Test_vi_big_a_InVisualMode_SingleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 2)))

        self.view.run_command('_vi_big_a', {'mode': modes.VISUAL, 'count': 1})

        self.assertEqual(self.R(2, 2), first_sel(self.view))


class Test_vi_big_a_InVisualMode_MultipleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc\nabc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 2)))
        self.view.sel().add(self.R((1, 1), (1, 2)))

        self.view.run_command('_vi_big_a', {'mode': modes.VISUAL, 'count': 1})

        self.assertEqual(self.R(2, 2), first_sel(self.view))
        self.assertEqual(self.R((1, 2), (1, 2)), second_sel(self.view))


class Test_vi_big_a_InVisualLineMode_SingleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 3)))

        self.view.run_command('_vi_big_a', {'mode': modes.VISUAL_LINE, 'count': 1})

        self.assertEqual(self.R(3, 3), first_sel(self.view))


class Test_vi_big_a_InVisualLineMode_MultipleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc\nabc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 4)))
        self.view.sel().add(self.R((1, 0), (1, 3)))

        self.view.run_command('_vi_big_a', {'mode': modes.VISUAL_LINE, 'count': 1})

        self.assertEqual(self.R(3, 3), first_sel(self.view))
        self.assertEqual(self.R((1, 3), (1, 3)), second_sel(self.view))


class Test_vi_big_a_InVisualBlockMode_SingleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 2)))

        self.view.run_command('_vi_big_a', {'mode': modes.VISUAL_BLOCK, 'count': 1})

        self.assertEqual(self.R(2, 2), first_sel(self.view))


class Test_vi_big_a_InVisualBlockMode_MultipleSel(ViewTest):
    def testMovesCaretToEol(self):
        self.write('abc\nabc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 2)))
        self.view.sel().add(self.R((1, 0), (1, 2)))

        self.view.run_command('_vi_big_a', {'mode': modes.VISUAL_BLOCK, 'count': 1})

        self.assertEqual(self.R(2, 2), first_sel(self.view))
        self.assertEqual(self.R((1, 2), (1, 2)), second_sel(self.view))

########NEW FILE########
__FILENAME__ = test__vi_big_f
from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.vi.utils import modes


class Test_vi_big_f_InVisualMode(ViewTest):
    def testCanSearch_OppositeEndSmaller_NoCrossOver(self):
        self.write('foo bar\n')
        self.clear_sel()
        add_sel(self.view, self.R((0, 2), (0, 6)))

        self.view.run_command('_vi_reverse_find_in_line', {'mode': modes.VISUAL, 'count': 1, 'char': 'b', 'inclusive': True})
        self.assertEqual(self.R((0, 2), (0, 4)), first_sel(self.view))

########NEW FILE########
__FILENAME__ = test__vi_big_g
from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


class Test_vi_big_g_InNormalMode(ViewTest):
    def testCanMoveInNormalMode(self):
        self.write('abc\nabc')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_big_g', {'mode': modes.NORMAL, 'count': 1})
        self.assertEqual(self.R(6, 6), first_sel(self.view))

    def testGoToHardEofIfLastLineIsEmpty(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_big_g', {'mode': modes.NORMAL, 'count': 1})
        self.assertEqual(self.R(8, 8), first_sel(self.view))


class Test_vi_big_g_InVisualMode(ViewTest):
    def testCanMoveInVisualMode(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(a=0, b=1)

        self.view.run_command('_vi_big_g', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(0, 8), first_sel(self.view))


class Test_vi_big_g_InInternalNormalMode(ViewTest):
    def testCanMoveInModeInternalNormal(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R(1, 1))

        self.view.run_command('_vi_big_g', {'mode': modes.INTERNAL_NORMAL, 'count': 1})
        self.assertEqual(self.R(0, 8), first_sel(self.view))

    def testOperatesLinewise(self):
        self.write('abc\nabc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 1)))

        self.view.run_command('_vi_big_g', {'mode': modes.INTERNAL_NORMAL, 'count': 1})
        self.assertEqual(self.R((0, 3), (2, 4)), first_sel(self.view))


class Test_vi_big_g_InVisualLineMode(ViewTest):
    def testCanMoveInModeVisualLine(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(a=0, b=4)

        self.view.run_command('_vi_big_g', {'mode': modes.VISUAL_LINE, 'count': 1})
        self.assertEqual(self.R(0, 8), first_sel(self.view))


########NEW FILE########
__FILENAME__ = test__vi_big_i
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected actual_func msg')

TESTS = (
    test_data('abc',           [[(0, 0), (0, 2)]],                   {'mode': modes.INTERNAL_NORMAL}, [(0, 0), (0, 0)], first_sel, ''),
    test_data('abc\nabc',      [[(0, 1), (0, 1)], [(1, 1), (1, 1)]], {'mode': modes.INTERNAL_NORMAL}, [(0, 0), (0, 0)], first_sel, ''),
    test_data('abc\nabc',      [[(0, 1), (0, 1)], [(1, 1), (1, 1)]], {'mode': modes.INTERNAL_NORMAL}, [(1, 0), (1, 0)], second_sel, ''),
    test_data('abc',           [[(0, 0), (0, 2)]],                   {'mode': modes.VISUAL},           [(0, 0), (0, 0)], first_sel, ''),
    test_data('abc\nabc',      [[(0, 1), (0, 2)], [(1, 1), (1, 2)]], {'mode': modes.VISUAL},           [(0, 0), (0, 0)], first_sel, ''),
    test_data('abc\nabc',      [[(0, 1), (0, 2)], [(1, 1), (1, 2)]], {'mode': modes.VISUAL},           [(1, 0), (1, 0)], second_sel, ''),
    test_data('abc\nabc\nabc', [[(0, 0), (1, 4)]],                   {'mode': modes.VISUAL_LINE},      [(0, 0), (0, 0)], first_sel, ''),
    test_data('abc\nabc\nabc', [[(1, 0), (2, 4)]],                   {'mode': modes.VISUAL_LINE},      [(1, 0), (1, 0)], first_sel, ''),
    test_data('abc\nabc',      [[(0, 2), (0, 3)], [(1, 2), (1, 3)]], {'mode': modes.VISUAL_BLOCK},     [(0, 2), (0, 2)], first_sel, ''),
    test_data('abc\nabc',      [[(0, 2), (0, 3)], [(1, 2), (1, 3)]], {'mode': modes.VISUAL_BLOCK},     [(1, 2), (1, 2)], second_sel, ''),
)


class Test_vi_big_i(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            set_text(self.view, data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_big_i', data.cmd_params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual = data.actual_func(self.view)
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_big_j
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected msg')

TESTS = (
    test_data('abc\nabc\nabc',                           [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 1}, 'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 1}, 'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 2}, 'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 2}, 'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 3}, 'abc abc abc',         'should join 3 lines'),
    test_data('abc\n    abc\n    abc',                   [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 3}, 'abc abc abc',         'should join 3 lines'),
    test_data('abc\nabc\nabc\nabc\nabc',                 [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 5}, 'abc abc abc abc abc', 'should join 5 lines'),
    test_data('abc\n    abc\n    abc\n    abc\n    abc', [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 5}, 'abc abc abc abc abc', 'should join 5 lines'),
    test_data('abc\n\n',                                 [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 3}, 'abc ',                'should join 3 lines and add one trailing space'),
    test_data('\n\nabc',                                 [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 3}, 'abc',                 'should join 3 lines without adding any spaces'),
    test_data('abc \n    abc  \n  abc',                  [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 3}, 'abc abc  abc',        'should join 3 lines with leading spaces removed but trailing spaces intact'),
    test_data('   abc\nabc   ',                          [[(0, 0), (0, 0)]],                   {'mode': modes.INTERNAL_NORMAL, 'count': 1}, '   abc abc   ',       'should join 2 lines with leading spaces of first line and trailing spaces of last line intact'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (0, 1)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (0, 1)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (0, 1)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (0, 1)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (1, 1)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (1, 1)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(1, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\n    abc\nabc',                       [[(1, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc\nabc',        'should join 2 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (2, 1)]],                   {'mode': modes.VISUAL},                       'abc abc abc',         'should join 3 lines'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (2, 1)]],                   {'mode': modes.VISUAL},                       'abc abc abc',         'should join 3 lines'),
    test_data('abc\nabc\nabc',                           [[(2, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc abc',         'should join 3 lines'),
    test_data('abc\n    abc\nabc',                       [[(2, 1), (0, 0)]],                   {'mode': modes.VISUAL},                       'abc abc abc',         'should join 3 lines'),
    test_data('abc\nabc\nabc',                           [[(0, 0), (1, 1)]],                   {'mode': modes.VISUAL, 'count': 3},           'abc abc\nabc',        'should join 2 lines - count shouldn\'t matter'),
    test_data('abc\n    abc\nabc',                       [[(0, 0), (1, 1)]],                   {'mode': modes.VISUAL, 'count': 3},           'abc abc\nabc',        'should join 2 lines - count shouldn\'t matter'),
    test_data('   abc\nabc   ',                          [[(0, 0), (1, 5)]],                   {'mode': modes.VISUAL},                       '   abc abc   ',       'should join 2 lines with leading spaces of first line and trailing spaces of last line intact'),
    test_data('    abc\n\n\n',                           [[(0, 0), (3, 0)]],                   {'mode': modes.VISUAL_LINE},                  '    abc \n',          'should join 4 lines'),
    test_data('    abc  \n   abc\nabc',                  [[(0, 0), (0, 1)], [(1, 0), (1, 1)]], {'mode': modes.VISUAL_BLOCK},                 '    abc  abc\nabc',   'should join 2 lines'),
)


class Test_vi_big_j(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                add_sel(self.view, self.R(*region))

            self.view.run_command('_vi_big_j', data.cmd_params)

            actual = self.view.substr(self.R(0, self.view.size()))
            msg = "[{0}] {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_big_s
import unittest

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.vi.utils import modes


class Test_vi_big_s_InModeInternalNormal(ViewTest):
    def testDeletesWholeLine(self):
        self.write(''.join(('foo bar\nfoo bar\nfoo bar\n',)))
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 7)))

        self.view.run_command('_vi_big_s_action', {'mode': modes.INTERNAL_NORMAL})
        self.assertEqual(self.view.substr(self.R(0, self.view.size())), 'foo bar\n\nfoo bar\n')

    def testReindents(self):
        content = """\tfoo bar
foo bar
foo bar
"""
        self.write(content)
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 7)))

        self.view.run_command('_vi_big_s_action', {'mode': modes.INTERNAL_NORMAL})
        expected = """\t foo bar
\tfoo bar
"""
        self.assertEqual(self.view.substr(self.R(0, self.view.size())), '\tfoo bar\n\t\nfoo bar\n')

    @unittest.skip("Implement")
    def testCanDeleteWithCount(self):
        self.assertTrue(False)

########NEW FILE########
__FILENAME__ = test__vi_cc
import unittest
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))

def  first_sel_wrapper(test):
    return first_sel(test.view)


test_data = namedtuple('test_data', 'cmd initial_text regions cmd_params expected actual_func msg')
region_data = namedtuple('region_data', 'regions')

TESTS_INTERNAL_NORMAL = (
    # MOTION
    test_data(cmd='_vi_cc_motion', initial_text='foo bar\nfoo bar\nfoo bar\n', regions=[[(1, 2), (1, 2)]], cmd_params={'mode': modes.INTERNAL_NORMAL},
              expected=region_data([(1, 0), (1, 7)]), actual_func=first_sel_wrapper, msg='selects whole line'),

    # OPERATOR
    test_data(cmd='_vi_cc_action', initial_text='foo bar\nfoo bar\nfoo bar\n',      regions=[[(1, 0), (1, 0)]], cmd_params={'mode': modes.INTERNAL_NORMAL},
              expected='foo bar\n\nfoo bar\n', actual_func=get_text,  msg=''),

    test_data(cmd='_vi_cc_action', initial_text='\tfoo bar\n\tfoo bar\nfoo bar\n',  regions=[[(1, 0), (1, 0)]], cmd_params={'mode': modes.INTERNAL_NORMAL},
              expected='\tfoo bar\n\t\nfoo bar\n', actual_func=get_text,  msg=''),
    )


TESTS = TESTS_INTERNAL_NORMAL


class Test_vi_cc_motion(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command(data.cmd, data.cmd_params)

            msg = "failed at test index {0} {1}".format(i, data.msg)
            actual = data.actual_func(self)

            if isinstance(data.expected, region_data):
                self.assertEqual(self.R(*data.expected.regions), actual, msg)
            else:
                self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_dd
import unittest

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


class Test_vi_dd_action_InNormalMode(ViewTest):
    def testDeletesLastLine(self):
        self.write('abc\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((2, 0), (2, 0)))

        # TODO: We should probably test these two commands separately.
        self.view.run_command('_vi_dd_motion', {'mode': modes.INTERNAL_NORMAL, 'count': 1})
        self.view.run_command('_vi_dd_action', {'mode': modes.INTERNAL_NORMAL})

        expected = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, 'abc\nabc')

########NEW FILE########
__FILENAME__ = test__vi_dollar
import unittest
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))

def  first_sel_wrapper(test):
    return first_sel(test.view)


test_data = namedtuple('test_data', 'cmd initial_text regions cmd_params expected actual_func msg')
region_data = namedtuple('region_data', 'regions')

TESTS_INTERNAL_NORMAL = (
    # NORMAL mode
    test_data(cmd='_vi_dollar', initial_text='abc\nabc\n', regions=[[(0, 0), (0, 0)]], cmd_params={'mode': modes.NORMAL},
              expected=region_data([(0, 2), (0, 2)]), actual_func=first_sel_wrapper, msg=''),

    test_data(cmd='_vi_dollar', initial_text=('abc\n' * 10), regions=[[(0, 0), (0, 0)]], cmd_params={'mode': modes.NORMAL, 'count': 5},
              expected=region_data([18, 18]), actual_func=first_sel_wrapper, msg=''),

    test_data(cmd='_vi_dollar', initial_text=('abc\n\nabc\n'), regions=[[4, 4]], cmd_params={'mode': modes.NORMAL, 'count': 1},
              expected=region_data([4, 4]), actual_func=first_sel_wrapper, msg='should not move on empty line'),

    # VISUAL mode
    test_data(cmd='_vi_dollar', initial_text='abc\nabc\n', regions=[[0, 1]], cmd_params={'mode': modes.VISUAL},
              expected=region_data([0, 4]), actual_func=first_sel_wrapper, msg=''),

    test_data(cmd='_vi_dollar', initial_text=('abc\n' * 10), regions=[[0, 1]], cmd_params={'mode': modes.VISUAL, 'count': 5},
              expected=region_data([0, 20]), actual_func=first_sel_wrapper, msg=''),

    test_data(cmd='_vi_dollar', initial_text=('abc\n\nabc\n'), regions=[[4, 5]], cmd_params={'mode': modes.VISUAL, 'count': 1},
              expected=region_data([4, 5]), actual_func=first_sel_wrapper, msg=''),

    test_data(cmd='_vi_dollar', initial_text=('abc\nabc\n'), regions=[[6, 1]], cmd_params={'mode': modes.VISUAL, 'count': 1},
              expected=region_data([6, 3]), actual_func=first_sel_wrapper, msg='can move in visual mode with reversed sel no cross over'),

    test_data(cmd='_vi_dollar', initial_text=('abc\nabc\n'), regions=[[3, 2]], cmd_params={'mode': modes.VISUAL, 'count': 1},
              expected=region_data([2, 4]), actual_func=first_sel_wrapper, msg='can move in visual mode with revesed sel at eol'),

    test_data(cmd='_vi_dollar', initial_text=('abc\nabc\n'), regions=[[5, 4]], cmd_params={'mode': modes.VISUAL, 'count': 2},
              expected=region_data([4, 8]), actual_func=first_sel_wrapper, msg='can move in visual mode with revesed sel cross over'),

    test_data(cmd='_vi_dollar', initial_text=('abc\nabc\nabc\n'), regions=[[0, 4]], cmd_params={'mode': modes.VISUAL_LINE, 'count': 1},
              expected=region_data([0, 4]), actual_func=first_sel_wrapper, msg='can move in visual mode with revesed sel cross over'),

    test_data(cmd='_vi_dollar', initial_text='abc\nabc\n', regions=[[0, 0]], cmd_params={'mode': modes.INTERNAL_NORMAL},
              expected=region_data([0, 3]), actual_func=first_sel_wrapper, msg=''),

    test_data(cmd='_vi_dollar', initial_text='abc\nabc\nabc\nabc\n', regions=[[0, 0]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 3},
              expected=region_data([0, 12]), actual_func=first_sel_wrapper, msg=''),
    )


TESTS = TESTS_INTERNAL_NORMAL


class Test_vi_dollar(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command(data.cmd, data.cmd_params)

            msg = "failed at test index {0} {1}".format(i, data.msg)
            actual = data.actual_func(self)

            if isinstance(data.expected, region_data):
                self.assertEqual(self.R(*data.expected.regions), actual, msg)
            else:
                self.assertEqual(data.expected, actual, msg)
########NEW FILE########
__FILENAME__ = test__vi_e
from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


# The heavy lifting is done by units.* functions, but we refine some cases in the actual motion
# command, so we need to test for that too here.
class Test_vi_e_InNormalMode(ViewTest):
    def testMoveToEndOfWord_OnLastLine(self):
        self.write('abc\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((2, 0), (2, 0)))

        self.view.run_command('_vi_e', {'mode': modes.NORMAL, 'count': 1})

        self.assertEqual(self.R((2, 2), (2, 2)), first_sel(self.view))

    def testMoveToEndOfWord_OnMiddleLine_WithTrailingWhitespace(self):
        self.write('abc\nabc   \nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 2), (1, 2)))

        self.view.run_command('_vi_e', {'mode': modes.NORMAL, 'count': 1})

        self.assertEqual(self.R((2, 2), (2, 2)), first_sel(self.view))

    def testMoveToEndOfWord_OnLastLine_WithTrailingWhitespace(self):
        self.write('abc\nabc\nabc   ')
        self.clear_sel()
        self.add_sel(self.R((2, 0), (2, 0)))

        self.view.run_command('_vi_e', {'mode': modes.NORMAL, 'count': 1})

        self.assertEqual(self.R((2, 2), (2, 2)), first_sel(self.view))

        self.view.run_command('_vi_e', {'mode': modes.NORMAL, 'count': 1})

        self.assertEqual(self.R((2, 5), (2, 5)), first_sel(self.view))

########NEW FILE########
__FILENAME__ = test__vi_g_g
from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


class Test_vi_g_g_InNormalMode(ViewTest):
    def testCanMoveInNormalMode(self):
        self.write('abc\nabc')
        self.clear_sel()
        self.add_sel(self.R(5, 5))

        self.view.run_command('_vi_gg', {'mode': modes.NORMAL})
        self.assertEqual(self.R(0, 0), first_sel(self.view))

    def testGoToHardEofIfLastLineIsEmpty(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R(5, 5))

        self.view.run_command('_vi_gg', {'mode': modes.NORMAL})
        self.assertEqual(self.R(0, 0), first_sel(self.view))


class Test_vi_g_g_InVisualMode(ViewTest):
    def testCanMoveInVisualMode(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R((0, 1), (0, 2)))

        self.view.run_command('_vi_gg', {'mode': modes.VISUAL})
        self.assertEqual(self.R((0, 2), (0, 0)), first_sel(self.view))

    def testCanMoveInVisualMode_Reversed(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R((0, 2), (0, 1)))

        self.view.run_command('_vi_gg', {'mode': modes.VISUAL})
        self.assertEqual(self.R((0, 2), (0, 0)), first_sel(self.view))


class Test_vi_g_g_InInternalNormalMode(ViewTest):
    def testCanMoveInModeInternalNormal(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R(1, 1))

        self.view.run_command('_vi_gg', {'mode': modes.INTERNAL_NORMAL})
        self.assertEqual(self.R(4, 0), first_sel(self.view))


class Test_vi_g_g_InVisualLineMode(ViewTest):
    def testCanMoveInModeVisualLine(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 4)))

        self.view.run_command('_vi_gg', {'mode': modes.VISUAL_LINE})
        self.assertEqual(self.R((0, 0), (0, 4)), first_sel(self.view))

    def testExtendsSelection(self):
        self.write('abc\nabc\n')
        self.clear_sel()
        self.add_sel(self.R((0, 4), (0, 8)))

        self.view.run_command('_vi_gg', {'mode': modes.VISUAL_LINE})
        self.assertEqual(self.R((0, 0), (0, 8)), first_sel(self.view))


########NEW FILE########
__FILENAME__ = test__vi_h
from Vintageous.vi.utils import modes

from collections import namedtuple

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'cmd initial_text regions cmd_params expected actual_func msg')
region_data = namedtuple('region_data', 'regions')


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))

def  first_sel_wrapper(test):
    return first_sel(test.view)


TESTS_MODES = (
    # NORMAL mode
    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 1]], cmd_params={'mode': modes.NORMAL},
              expected=region_data([0, 0]), actual_func=first_sel_wrapper, msg='should move back one char (normal mode)'),
    test_data(cmd='_vi_h', initial_text='foo bar baz', regions=[[1, 1]], cmd_params={'mode': modes.NORMAL, 'count': 10},
              expected=region_data([0, 0]), actual_func=first_sel_wrapper, msg='should move back one char with count (normal mode)'),
    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 1]], cmd_params={'mode': modes.NORMAL, 'count': 10000},
              expected=region_data([0, 0]), actual_func=first_sel_wrapper, msg='should move back one char with large count (normal mode)'),

    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 1]], cmd_params={'mode': modes.INTERNAL_NORMAL},
              expected=region_data([1, 0]), actual_func=first_sel_wrapper, msg='should select one char (internal normal mode)'),
    test_data(cmd='_vi_h', initial_text='foo bar baz', regions=[[10, 10]], cmd_params={'mode': modes.INTERNAL_NORMAL},
              expected=region_data([10, 9]), actual_func=first_sel_wrapper, msg='should select one char from eol (internal normal mode)'),
    test_data(cmd='_vi_h', initial_text='foo bar baz', regions=[[1, 1]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 10000},
              expected=region_data([1, 0]), actual_func=first_sel_wrapper, msg='should select one char large count (internal normal mode)'),

    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 2]], cmd_params={'mode': modes.VISUAL},
              expected=region_data([2, 0]), actual_func=first_sel_wrapper, msg='should select one char (visual mode)'),
    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 3]], cmd_params={'mode': modes.VISUAL, 'count': 1},
              expected=region_data([1, 2]), actual_func=first_sel_wrapper, msg='should deselect one char (visual mode)'),
    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 3]], cmd_params={'mode': modes.VISUAL, 'count': 2},
              expected=region_data([2, 0]), actual_func=first_sel_wrapper, msg='should go back two chars (visual mode) crossing over'),

    test_data(cmd='_vi_h', initial_text='abc', regions=[[1, 3]], cmd_params={'mode': modes.VISUAL, 'count': 100},
              expected=region_data([2, 0]), actual_func=first_sel_wrapper, msg='can move reversed cross over large count visual mode'),
    test_data(cmd='_vi_h', initial_text='foo bar fuzz buzz', regions=[[11, 12]], cmd_params={'mode': modes.VISUAL, 'count': 10},
              expected=region_data([12, 1]), actual_func=first_sel_wrapper, msg='can move with count visual mode'),
    test_data(cmd='_vi_h', initial_text='abc\n', regions=[[1, 2]], cmd_params={'mode': modes.VISUAL, 'count': 10000},
              expected=region_data([2, 0]), actual_func=first_sel_wrapper, msg='stops at left end'),

)


TESTS = TESTS_MODES


class Test_vi_h(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command(data.cmd, data.cmd_params)

            msg = "failed at test index {0} {1}".format(i, data.msg)
            actual = data.actual_func(self)

            if isinstance(data.expected, region_data):
                self.assertEqual(self.R(*data.expected.regions), actual, msg)
            else:
                self.assertEqual(data.expected, actual, msg)
########NEW FILE########
__FILENAME__ = test__vi_j
from Vintageous.vi.utils import modes

from collections import namedtuple

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


# TODO: Test against folded regions.
# TODO: Ensure that we only create empty selections while testing. Add assert_all_sels_empty()?
test_data = namedtuple('test_data', 'cmd initial_text regions cmd_params expected actual_func msg')
region_data = namedtuple('region_data', 'regions')


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))


def  first_sel_wrapper(test):
    return first_sel(test.view)


TESTS_MODES = (
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[1, 1]], cmd_params={'mode': modes.NORMAL, 'xpos': 1},
              expected=region_data([(1, 1), (1, 1)]), actual_func=first_sel_wrapper, msg='move one line down'),
    test_data(cmd='_vi_j', initial_text=(''.join('abc\n' * 60)), regions=[[1, 1]], cmd_params={'mode': modes.NORMAL, 'count': 50, 'xpos': 1},
              expected=region_data([(50, 1), (50, 1)]), actual_func=first_sel_wrapper, msg='move many lines down'),
    test_data(cmd='_vi_j', initial_text=(''.join('abc\n' * 60)), regions=[[1, 1]], cmd_params={'mode': modes.NORMAL, 'count': 50, 'xpos': 1},
              expected=region_data([(50, 1), (50, 1)]), actual_func=first_sel_wrapper, msg='move many lines down'),
    test_data(cmd='_vi_j', initial_text='foo\nfoo bar\nfoo bar', regions=[[1, 1]], cmd_params={'mode': modes.NORMAL, 'count': 1, 'xpos': 1},
              expected=region_data([(1, 1), (1, 1)]), actual_func=first_sel_wrapper, msg='move onto longer line'),
    test_data(cmd='_vi_j', initial_text='foo bar\nfoo\nbar', regions=[[5, 5]], cmd_params={'mode': modes.NORMAL, 'count': 1, 'xpos': 5},
              expected=region_data([(1, 2), (1, 2)]), actual_func=first_sel_wrapper, msg='move onto shorter line'),
    test_data(cmd='_vi_j', initial_text='\nfoo\nbar', regions=[[0, 0]], cmd_params={'mode': modes.NORMAL, 'count': 1, 'xpos': 0},
              expected=region_data([(1, 0), (1, 0)]), actual_func=first_sel_wrapper, msg='move from empty line'),

    test_data(cmd='_vi_j', initial_text='\n\nbar', regions=[[0, 0]], cmd_params={'mode': modes.NORMAL, 'count': 1, 'xpos': 0},
              expected=region_data([(1, 0), (1, 0)]), actual_func=first_sel_wrapper, msg='move from empty line'),
    test_data(cmd='_vi_j', initial_text='foo\nbar\nbaz', regions=[[0, 0]], cmd_params={'mode': modes.NORMAL, 'count': 1, 'xpos': 0},
              expected=region_data([(1, 0), (1, 0)]), actual_func=first_sel_wrapper, msg='move from empty line'),

    test_data(cmd='_vi_j', initial_text='abc\nabc', regions=[[1, 2]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 1), (1, 2)]), actual_func=first_sel_wrapper, msg='move onto next line (VISUAL)'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[10, 1]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 10), (1, 1)]), actual_func=first_sel_wrapper, msg='move from empty line'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[6, 1]], cmd_params={'mode': modes.VISUAL, 'count': 2, 'xpos': 1},
              expected=region_data([(0, 5), (2, 2)]), actual_func=first_sel_wrapper, msg='move from empty line'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[6, 1]], cmd_params={'mode': modes.VISUAL, 'count': 100, 'xpos': 1},
              expected=region_data([(0, 5), (2, 2)]), actual_func=first_sel_wrapper, msg='xxxx'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[6, 1]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 1},
              expected=region_data([(1, 2), (1, 1)]), actual_func=first_sel_wrapper, msg='move from different line to home position'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[6, 5]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 5), (2, 2)]), actual_func=first_sel_wrapper, msg='move from empty line'),
    test_data(cmd='_vi_j', initial_text=('abc\n' * 60), regions=[[1, 2]], cmd_params={'mode': modes.VISUAL, 'count': 50, 'xpos': 1},
              expected=region_data([(0, 1), (50, 2)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo\nfoo bar\nfoo bar', regions=[[1, 2]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 1), (1, 2)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo bar\nfoo\nbar', regions=[[5, 6]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 5},
              expected=region_data([(0, 5), (1, 4)]), actual_func=first_sel_wrapper, msg='move from longer to shorter'),
    test_data(cmd='_vi_j', initial_text='\nfoo\nbar', regions=[[0, 1]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 0},
              expected=region_data([(0, 0), (1, 1)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='\n\nbar', regions=[[0, 1]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 0},
              expected=region_data([(0, 0), (1, 1)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo\nbar\nbaz', regions=[[1, 2]], cmd_params={'mode': modes.VISUAL, 'count': 10000, 'xpos': 1},
              expected=region_data([(0, 1), (2, 2)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[1, 1]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 0), (1, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text=('abc\n' * 60), regions=[[1, 1]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 50, 'xpos': 1},
              expected=region_data([(0, 0), (50, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo\nfoo bar\nfoo bar', regions=[[1, 1]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 0), (1, 8)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo bar\nfoo\nbar', regions=[[5, 5]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 1, 'xpos': 5},
              expected=region_data([(0, 0), (1, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='\nfoo\nbar', regions=[[0, 0]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 1, 'xpos': 0},
              expected=region_data([(0, 0), (1, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='\n\nbar', regions=[[0, 0]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 1, 'xpos': 0},
              expected=region_data([(0, 0), (1, 1)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo\nbar\nbaz', regions=[[1, 1]], cmd_params={'mode': modes.INTERNAL_NORMAL, 'count': 10000, 'xpos': 1},
              expected=region_data([(0, 0), (2, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='abc\nabc\nabc', regions=[[0, 4]], cmd_params={'mode': modes.VISUAL_LINE, 'count': 1, 'xpos': 1},
              expected=region_data([(0, 0), (1, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text=('abc\n' * 60), regions=[[0, 4]], cmd_params={'mode': modes.VISUAL_LINE, 'count': 50, 'xpos': 1},
              expected=region_data([(0, 0), (50, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='\nfoo\nbar', regions=[[0, 1]], cmd_params={'mode': modes.VISUAL_LINE, 'count': 1, 'xpos': 0},
              expected=region_data([(0, 0), (1, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='\n\nbar', regions=[[1, 0]], cmd_params={'mode': modes.VISUAL_LINE, 'count': 1, 'xpos': 0},
              expected=region_data([(0, 0), (1, 1)]), actual_func=first_sel_wrapper, msg='move many lines'),
    test_data(cmd='_vi_j', initial_text='foo\nbar\nbaz', regions=[[0, 4]], cmd_params={'mode': modes.VISUAL_LINE, 'count': 10000, 'xpos': 1},
              expected=region_data([(0, 0), (2, 4)]), actual_func=first_sel_wrapper, msg='move many lines'),
    )


TESTS = TESTS_MODES

test = namedtuple('simple_test', 'content regions kwargs expected msg')

MORE_TESTS = (
    test(content='''aaa
bbb
''',
    regions=((1,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 1}, expected=((1, 1), (1, 1)), msg='from same length'),

    test(content='''

''',
    regions=((0,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 0}, expected=((1, 0), (1, 0)), msg='from empty to empty'),

    test(content='''aaa

''',
    regions=((2,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 2}, expected=((1, 0), (1,0)), msg='from longer to empty'),

    test(content='''
aaa
''',
    regions=((0,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 0}, expected=((1, 0), (1, 0)), msg='from empty to longer'),

    test(content='''aaa
aaa bbb
''',
    regions=((2,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 2}, expected=((1, 2), (1, 2)), msg='from shorter to longer'),

    test(content='''aaa bbb
aaa
''',
    regions=((6,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 6}, expected=((1, 2), (1, 2)), msg='from longer to shorter'),

    test(content='''aaa bbb ccc
\t\taaa
''',
    regions=((8,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 8}, expected=((1, 2), (1, 2)), msg='xpos with tabs'),

    test(content='''aaa bbb ccc
aaa
''',
    regions=((8,),), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 1000}, expected=((1, 2), (1, 2)), msg='xpos stops at eol'),

    # VISUAL MODE
    test(content='''
aaa
''',
    regions=((0, 1),), kwargs={'mode': modes.VISUAL, 'count': 1, 'xpos': 0}, expected=((0, 0), (1, 1)), msg='from empty to non-empty (visual)'),
)


class Test_vi_j(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command(data.cmd, data.cmd_params)

            msg = "failed at test index {0} {1}".format(i, data.msg)
            actual = data.actual_func(self)

            if isinstance(data.expected, region_data):
                self.assertEqual(self.R(*data.expected.regions), actual, msg)
            else:
                self.assertEqual(data.expected, actual, msg)


class Test_vi_j_new(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(MORE_TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.content)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_j', data.kwargs)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            actual = self.view.sel()[0]
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_k
from Vintageous.vi.utils import modes

from collections import namedtuple

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


# TODO: Test against folded regions.
# TODO: Ensure that we only create empty selections while testing. Add assert_all_sels_empty()?
# TODO: Test different values for xpos in combination with the starting col.
test_data = namedtuple('test_data', 'cmd initial_text regions cmd_params expected actual_func msg')
region_data = namedtuple('region_data', 'regions')


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))

def  first_sel_wrapper(test):
    return first_sel(test.view)


TESTS_MODES = (
    # NORMAL mode
    test_data(cmd='_vi_k', initial_text='abc\nabc', regions=[[(1, 1), (1, 1)]], cmd_params={'mode': modes.NORMAL, 'xpos': 1},
              expected=region_data([(0, 1), (0, 1)]), actual_func=first_sel_wrapper, msg='should move up one line (normal mode)'),
    test_data(cmd='_vi_k', initial_text='abc\nabc\nabc', regions=[[(2, 1), (2, 1)]], cmd_params={'mode': modes.NORMAL, 'xpos': 1, 'count': 2},
              expected=region_data([(0, 1), (0, 1)]), actual_func=first_sel_wrapper, msg='should move up two lines (normal mode)'),
    test_data(cmd='_vi_k', initial_text='foo bar\nfoo', regions=[[(1, 1), (1, 1)]], cmd_params={'mode': modes.NORMAL, 'xpos': 1},
              expected=region_data([(0, 1), (0, 1)]), actual_func=first_sel_wrapper, msg='should move up one line onto longer line (normal mode)'),

    test_data(cmd='_vi_k', initial_text='foo\nfoo bar', regions=[[(1, 5), (1, 5)]], cmd_params={'mode': modes.NORMAL, 'xpos': 5},
              expected=region_data([(0, 2), (0, 2)]), actual_func=first_sel_wrapper, msg='should move onto shorter line (mode normal)'),
    test_data(cmd='_vi_k', initial_text='foo\n\n', regions=[[(1, 0), (1, 0)]], cmd_params={'mode': modes.NORMAL, 'xpos': 1},
              expected=region_data([(0, 1), (0, 1)]), actual_func=first_sel_wrapper, msg='should be able to move from empty line (mode normal)'),
    test_data(cmd='_vi_k', initial_text='\n\n\n', regions=[[(1, 0), (1, 0)]], cmd_params={'mode': modes.NORMAL, 'xpos': 0},
              expected=region_data([(0, 0), (0, 0)]), actual_func=first_sel_wrapper, msg='should move from empty line to empty line (mode normal)'),
    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(2, 1), (2, 1)]], cmd_params={'mode': modes.NORMAL, 'xpos': 1, 'count': 100},
              expected=region_data([(0, 1), (0, 1)]), actual_func=first_sel_wrapper, msg='should not move too far (mode normal)'),

    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(1, 1), (1, 2)]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 2},
              expected=region_data([(1, 2), (0, 2)]), actual_func=first_sel_wrapper, msg='move one line (visual mode)'),
    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(2, 1), (2, 2)]], cmd_params={'mode': modes.VISUAL, 'count': 1, 'xpos': 2},
              expected=region_data([(2, 2), (1, 2)]), actual_func=first_sel_wrapper, msg='move opposite end greater with sel of size 1 (visual mode)'),
    test_data(cmd='_vi_k', initial_text='foo\nfoo\nbaz', regions=[[(1, 1), (1, 3)]], cmd_params={'mode': modes.VISUAL, 'xpos': 3},
              expected=region_data([(1, 2), (0, 3)]), actual_func=first_sel_wrapper, msg='move opposite end smaller with sel of size 2'),
    test_data(cmd='_vi_k', initial_text='foobar\nbarfoo\nbuzzfizz\n', regions=[[(1, 1), (1, 4)]], cmd_params={'mode': modes.VISUAL, 'xpos': 3},
              expected=region_data([(1, 2), (0, 3)]), actual_func=first_sel_wrapper, msg='move opposite end smaller with sel of size 3'),
    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(0, 1), (2, 1)]], cmd_params={'mode': modes.VISUAL, 'xpos': 1},
              expected=region_data([(0, 1), (1, 2)]), actual_func=first_sel_wrapper, msg='move opposite end smaller different lines no cross over'),

    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(1, 0), (2, 1)]], cmd_params={'mode': modes.VISUAL, 'xpos': 0},
              expected=region_data([(1, 0), (1, 1)]), actual_func=first_sel_wrapper, msg='move opposite end smaller different lines cross over xpos at 0'),
    test_data(cmd='_vi_k', initial_text='foo bar\nfoo bar\nfoo bar\n', regions=[[(1, 4), (2, 4)]], cmd_params={'mode': modes.VISUAL, 'xpos': 4, 'count': 2},
              expected=region_data([(1, 5), (0, 4)]), actual_func=first_sel_wrapper, msg='move opposite end smaller different lines cross over non 0 xpos'),
    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(0, 1), (1, 1)]], cmd_params={'mode': modes.VISUAL, 'xpos': 0, 'count': 1},
              expected=region_data([(0, 2), (0, 0)]), actual_func=first_sel_wrapper, msg='move back to same line same xpos'),

    test_data(cmd='_vi_k', initial_text='foo\nbar\nbaz\n', regions=[[(0, 2), (1, 0)]], cmd_params={'mode': modes.VISUAL, 'xpos': 0, 'count': 1},
              expected=region_data([(0, 3), (0, 0)]), actual_func=first_sel_wrapper, msg='move back to same line opposite end has greater xpos'),
    test_data(cmd='_vi_k', initial_text=(''.join(('foo\n',) * 50)), regions=[[(20, 2), (20, 1)]], cmd_params={'mode': modes.VISUAL, 'xpos': 1, 'count': 10},
              expected=region_data([(20, 2), (10, 1)]), actual_func=first_sel_wrapper, msg='move many opposite end greater from same line'),
    test_data(cmd='_vi_k', initial_text=(''.join(('foo\n',) * 50)), regions=[[(21, 2), (20, 1)]], cmd_params={'mode': modes.VISUAL, 'xpos': 1, 'count': 10},
              expected=region_data([(21, 2), (10, 1)]), actual_func=first_sel_wrapper, msg='move many opposite end greater from same line'),

    )


TESTS = TESTS_MODES


class Test_vi_h(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command(data.cmd, data.cmd_params)

            msg = "failed at test index {0} {1}".format(i, data.msg)
            actual = data.actual_func(self)

            if isinstance(data.expected, region_data):
                self.assertEqual(self.R(*data.expected.regions), actual, msg)
            else:
                self.assertEqual(data.expected, actual, msg)


test = namedtuple('simple_test', 'content regions kwargs expected msg')

MORE_TESTS = (
    test(content='''aaa
bbb
''',
    regions=((1, 1), (1, 1)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 1}, expected=((0, 1), (0, 1)), msg='from same length'),

    test(content='''

''',
    regions=((1, 0), (1, 0)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 0}, expected=((0, 0), (0, 0)), msg='from empty to empty'),

    test(content='''
aaa
''',
    regions=((1, 2), (1, 2)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 2}, expected=((0, 0), (0,0)), msg='from longer to empty'),

    test(content='''aaa

''',
    regions=((1, 0), (1, 0)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 0}, expected=((0, 0), (0, 0)), msg='from empty to longer'),

    test(content='''aaa bbb
aaa
''',
    regions=((1, 2), (1, 2)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 2}, expected=((0, 2), (0, 2)), msg='from shorter to longer'),

    test(content='''aaa
aaa bbb
''',
    regions=((1, 6), (1, 6)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 6}, expected=((0, 2), (0, 2)), msg='from longer to shorter'),

    test(content='''\t\taaa
aaa bbb ccc
''',
    regions=((1, 8), (1, 8)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 8}, expected=((0, 2), (0, 2)), msg='xpos with tabs'),

    test(content='''aaa
aaa bbb ccc
''',
    regions=((1, 8), (1, 8)), kwargs={'mode': modes.NORMAL, 'count': 1, 'xpos': 1000}, expected=((0, 2), (0, 2)), msg='xpos stops at eol'),

    # VISUAL
    test(content='''aaa

ccc
''',
    regions=(((1, 0), (1, 1)),), kwargs={'mode': modes.VISUAL, 'count': 1, 'xpos': 0}, expected=((1, 1), (0, 0)), msg='from empty to non-empty (visual)'),

    test(content='''aaa bbb ccc ddd
aaa bbb ccc ddd
''',
    regions=(((0, 6), (1, 2)),), kwargs={'mode': modes.VISUAL, 'count': 1, 'xpos': 2}, expected=((0, 7), (0, 2)), msg='from empty to non-empty (visual)'),
)


class Test_vi_k_new(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(MORE_TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.content)
            for region in data.regions:
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_k', data.kwargs)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            actual = self.view.sel()[0]
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_l
from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


class Test_vi_l_InNormalMode(ViewTest):
    def testCanMoveInNormalMode(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_l', {'mode': modes.NORMAL, 'count': 1})
        self.assertEqual(self.R(1, 1), first_sel(self.view))

    def testCanMoveInNormalModeWithCount(self):
        self.write('foo bar baz')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_l', {'mode': modes.NORMAL, 'count': 10})
        self.assertEqual(self.R(10, 10), first_sel(self.view))

    def testStopsAtRightEndInNormalMode(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_l', {'mode': modes.NORMAL, 'count': 10000})
        self.assertEqual(self.R(2, 2), first_sel(self.view))


class Test_vi_l_InInternalNormalMode(ViewTest):
    def testCanMoveInInternalNormalMode(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_l', {'mode': modes.INTERNAL_NORMAL, 'count': 1})
        self.assertEqual(self.R(0, 1), first_sel(self.view))

    def testCanMoveInInternalNormalModeWithCount(self):
        self.write('foo bar baz')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_l', {'mode': modes.INTERNAL_NORMAL, 'count': 10})
        self.assertEqual(self.R(0, 10), first_sel(self.view))

    def testStopsAtRightEndInInternalNormalMode(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=0, b=0)

        self.view.run_command('_vi_l', {'mode': modes.INTERNAL_NORMAL, 'count': 10000})
        self.assertEqual(self.R(0, 3), first_sel(self.view))


class Test_vi_l_InVisualMode(ViewTest):
    def testCanMove(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=0, b=1)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(0, 2), first_sel(self.view))

    def testCanMoveReversedNoCrossOver(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=2, b=0)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(2, 1), first_sel(self.view))

    def testCanMoveReversedMinimal(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(a=1, b=0)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(0, 2), first_sel(self.view))

    def testCanMoveReversedCrossOver(self):
        self.write('foo bar baz')
        self.clear_sel()
        self.add_sel(a=5, b=0)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 5})
        self.assertEqual(self.R(4, 6), first_sel(self.view))

    def testCanMoveReversedDifferentLines(self):
        self.write('foo\nbar\n')
        self.clear_sel()
        self.add_sel(a=5, b=1)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(5, 2), first_sel(self.view))

    def testStopsAtEolDifferentLinesReversed(self):
        self.write('foo\nbar\n')
        self.clear_sel()
        self.add_sel(a=5, b=3)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(5, 3), first_sel(self.view))

    def testStopsAtEolDifferentLinesReversedLargeCount(self):
        self.write('foo\nbar\n')
        self.clear_sel()
        self.add_sel(a=5, b=3)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 100})
        self.assertEqual(self.R(5, 3), first_sel(self.view))

    def testCanMoveWithCount(self):
        self.write('foo bar fuzz buzz')
        self.clear_sel()
        self.add_sel(a=0, b=1)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 10})
        self.assertEqual(self.R(0, 11), first_sel(self.view))

    def testStopsAtRightEnd(self):
        self.write('abc\n')
        self.clear_sel()
        self.add_sel(a=0, b=1)

        self.view.run_command('_vi_l', {'mode': modes.VISUAL, 'count': 10000})
        self.assertEqual(self.R(0, 4), first_sel(self.view))

########NEW FILE########
__FILENAME__ = test__vi_percent
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected actual_func msg')

TESTS = (
    test_data('abc (abc) abc', [[(0, 6), (0, 7)]], {'mode': modes.VISUAL},           [(0, 7), (0, 4)], first_sel, ''),
    test_data('abc (abc) abc', [[(0, 7), (0, 6)]], {'mode': modes.VISUAL},           [(0, 7), (0, 4)], first_sel, ''),
    test_data('abc (abc) abc', [[(0, 6), (0, 6)]], {'mode': modes.INTERNAL_NORMAL}, [(0, 7), (0, 4)], first_sel, ''),
    test_data('abc (abc) abc', [[(0, 8), (0, 8)]], {'mode': modes.INTERNAL_NORMAL}, [(0, 9), (0, 4)], first_sel, ''),
    test_data('abc (abc) abc', [[(0, 4), (0, 4)]], {'mode': modes.INTERNAL_NORMAL}, [(0, 4), (0, 9)], first_sel, ''),
    test_data('abc (abc) abc', [[(0, 0), (0, 0)]], {'mode': modes.INTERNAL_NORMAL}, [(0, 0), (0, 9)], first_sel, ''),
    # TODO: test multiline brackets, etc.
)


class Test__vi_percent(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            self.write(data.initial_text)
            for region in data.regions:
                self.clear_sel()
                self.add_sel(self.R(*region))

            self.view.run_command('_vi_percent', data.cmd_params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual = data.actual_func(self.view)
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test__vi_s
"""
Tests for o motion (visual kind).
"""

import unittest

from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL
from Vintageous.vi.constants import MODE_NORMAL
from Vintageous.vi.constants import MODE_VISUAL
from Vintageous.vi.constants import MODE_VISUAL_LINE

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


# unittest.skip("Command doesn't exist as such.")
# class Test_vi_s_InNormalMode(ViewTest):
#     def testChangesModes(self):
#         set_text(self.view, 'abc')
#         add_sel(self.view, self.R((0, 2), (0, 0)))

#         self.view.run_command('_vi_s', {'mode': MODE_NORMAL, 'count': 1})
#         self.assertEqual(self.view.settings().get('vintage')['mode'], MODE_VISUAL_LINE)


# class Test_vi_s_InInternalNormalMode(ViewTest):
#     def testCanMoveInInternalNormalMode(self):
#         set_text(self.view, 'abc')
#         add_sel(self.view, self.R((0, 2), (0, 0)))

#         self.view.run_command('_vi_s', {'mode': _MODE_INTERNAL_NORMAL, 'count': 1})
#         self.assertEqual(self.R(2, 0), first_sel(self.view))


# class Test_vi_s_InVisualMode(ViewTest):
#     def testCanMove(self):
#         set_text(self.view, 'abc')
#         add_sel(self.view, self.R(0, 2))

#         self.view.run_command('_vi_s', {'mode': MODE_VISUAL, 'count': 1})
#         self.assertEqual(self.R(2, 0), first_sel(self.view))


# class Test_vi_s_InVisualLineMode(ViewTest):
#     def testCanMove(self):
#         set_text(self.view, 'abc\ndef')
#         add_sel(self.view, self.R(0, 4))

#         self.view.run_command('_vi_s', {'mode': MODE_VISUAL_LINE, 'count': 1})
#         self.assertEqual(self.R(4, 0), first_sel(self.view))

########NEW FILE########
__FILENAME__ = test__vi_visual_o
"""
Tests for o motion (visual kind).
"""

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


class Test_vi_visual_o_InNormalMode(ViewTest):
    def testDoesntDoAnything(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R((0, 2), (0, 0)))

        self.view.run_command('_vi_visual_o', {'mode': modes.NORMAL, 'count': 1})
        self.assertEqual(self.R(2, 0), first_sel(self.view))


class Test_vi_visual_o_InInternalNormalMode(ViewTest):
    def testCanMoveInInternalNormalMode(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R((0, 2), (0, 0)))

        self.view.run_command('_vi_visual_o', {'mode': modes.INTERNAL_NORMAL, 'count': 1})
        self.assertEqual(self.R(2, 0), first_sel(self.view))


class Test_vi_visual_o_InVisualMode(ViewTest):
    def testCanMove(self):
        self.write('abc')
        self.clear_sel()
        self.add_sel(self.R(0, 2))

        self.view.run_command('_vi_visual_o', {'mode': modes.VISUAL, 'count': 1})
        self.assertEqual(self.R(2, 0), first_sel(self.view))


class Test_vi_visual_o_InVisualLineMode(ViewTest):
    def testCanMove(self):
        self.write('abc\ndef')
        self.clear_sel()
        self.add_sel(self.R(0, 4))

        self.view.run_command('_vi_visual_o', {'mode': modes.VISUAL_LINE, 'count': 1})
        self.assertEqual(self.R(4, 0), first_sel(self.view))

########NEW FILE########
__FILENAME__ = test__vi_zero
from collections import namedtuple

from Vintageous.vi.utils import modes

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import second_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'initial_text regions cmd_params expected actual_func msg')

TESTS = (
    test_data('abc',      [[(0, 2), (0, 2)]], {'mode': modes.NORMAL}, [(0, 0), (0, 0)], first_sel, ''),
    test_data('abc',      [[(0, 2), (0, 2)]], {'mode': modes.INTERNAL_NORMAL}, [(0, 2), (0, 0)], first_sel, ''),
    test_data('abc\nabc', [[(0, 2), (1, 3)]], {'mode': modes.VISUAL},           [(0, 2), (1, 1)], first_sel, ''),
    test_data('abc\nabc', [[(1, 3), (0, 2)]], {'mode': modes.VISUAL},           [(1, 3), (0, 0)], first_sel, ''),

    # TODO: Test multiple sels.
)


class Test__vi_zero(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.view.sel().clear()

            set_text(self.view, data.initial_text)
            for region in data.regions:
                add_sel(self.view, self.R(*region))

            self.view.run_command('_vi_zero', data.cmd_params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual = data.actual_func(self.view)
            self.assertEqual(self.R(*data.expected), actual, msg)

########NEW FILE########
__FILENAME__ = test_commands

########NEW FILE########
__FILENAME__ = test_copy
from Vintageous.vi.utils import modes

from Vintageous.state import State

from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.ex_commands import CURRENT_LINE_RANGE


class Test_ex_copy_Copying_InNormalMode_SingleLine_DefaultStart(ViewTest):
    def testCanCopyDefaultLineRange(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '3'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\nxxx\nabc'
        self.assertEqual(expected, actual)

    def testCanCopyToEof(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '4'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\nabc\nxxx'
        self.assertEqual(expected, actual)

    def testCanCopyToBof(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '0'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'xxx\nabc\nxxx\nabc\nabc'
        self.assertEqual(expected, actual)

    def testCanCopyToEmptyLine(self):
        self.write('abc\nxxx\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '4'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\n\nxxx\nabc'
        self.assertEqual(expected, actual)

    def testCanCopyToSameLine(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '2'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nxxx\nabc\nabc'
        self.assertEqual(expected, actual)


class Test_ex_copy_Copying_InNormalMode_MultipleLines(ViewTest):
    def setUp(self):
        super().setUp()
        self.range = {'left_ref': '.','left_offset': 0, 'left_search_offsets': [],
                      'right_ref': '.', 'right_offset': 1, 'right_search_offsets': []}

    def testCanCopyDefaultLineRange(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '4', 'line_range': self.range})

        expected = 'abc\nxxx\nxxx\nabc\nxxx\nxxx\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToEof(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '5', 'line_range': self.range})

        expected = 'abc\nxxx\nxxx\nabc\nabc\nxxx\nxxx'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToBof(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '0', 'line_range': self.range})

        expected = 'xxx\nxxx\nabc\nxxx\nxxx\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToEmptyLine(self):
        self.write('abc\nxxx\nxxx\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '5', 'line_range': self.range})

        expected = 'abc\nxxx\nxxx\nabc\n\nxxx\nxxx\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToSameLine(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '2', 'line_range': self.range})

        expected = 'abc\nxxx\nxxx\nxxx\nxxx\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)


class Test_ex_copy_InNormalMode_CaretPosition(ViewTest):
    def testCanRepositionCaret(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'address': '3'})

        actual = list(self.view.sel())
        expected = [self.R((3, 0), (3, 0))]
        self.assertEqual(expected, actual)


class Test_ex_copy_ModeTransition(ViewTest):
    def testFromNormalModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        state = State(self.view)
        state.enter_normal_mode()

        self.view.run_command('vi_enter_normal_mode')
        prev_mode = state.mode

        self.view.run_command('ex_copy', {'address': '3'})

        state = State(self.view)
        new_mode = state.mode
        self.assertEqual(prev_mode, new_mode, modes.NORMAL)

    def testFromVisualModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 1)))

        state = State(self.view)
        state.enter_visual_mode()
        prev_mode = state.mode

        self.view.run_command('ex_copy', {'address': '3'})

        state = State(self.view)
        new_mode = state.mode
        self.assertNotEqual(prev_mode, new_mode)
        self.assertEqual(new_mode, modes.NORMAL)

########NEW FILE########
__FILENAME__ = test_delete
import unittest

from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL
from Vintageous.vi.constants import MODE_NORMAL
from Vintageous.vi.constants import MODE_VISUAL
from Vintageous.vi.constants import MODE_VISUAL_LINE

from Vintageous.state import State

from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.ex_commands import CURRENT_LINE_RANGE


class Test_ex_delete_Deleting_InNormalMode_SingleLine_DefaultStart(ViewTest):
    def testCanDeleteDefaultLineRange(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_delete')

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nabc'
        self.assertEqual(expected, actual)

    def testCanDeleteAtEof_NoNewLine(self):
        self.write('abc\nabc\nabc\nxxx')
        self.clear_sel()
        self.add_sel(self.R((3, 0), (3, 0)))

        r = CURRENT_LINE_RANGE.copy()
        r['left_ref'] = '4'
        self.view.run_command('ex_delete', {'line_range': r})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nabc\n'
        self.assertEqual(expected, actual)

    def testCanDeleteAtEof_NewLine(self):
        self.write('abc\nabc\nabc\nxxx\n')
        self.clear_sel()
        self.add_sel(self.R((3, 0), (3, 0)))

        r = CURRENT_LINE_RANGE.copy()
        r['left_ref'] = '4'
        self.view.run_command('ex_delete', {'line_range': r})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nabc\n'
        self.assertEqual(expected, actual)

    def testCanDeleteZeroLineRange(self):
        self.write('xxx\nabc\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        r = CURRENT_LINE_RANGE.copy()
        r['text_range'] = '0'
        # If we don't do this, it will default to '.' and the test will fail.
        r['left_ref'] = '0'
        self.view.run_command('ex_delete', {'line_range': r})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nabc'
        self.assertEqual(expected, actual)

    def testCanDeleteEmptyLine(self):
        self.write('abc\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        r = CURRENT_LINE_RANGE.copy()
        r['right_ref'] = None
        r['left_ref'] = None
        r['text_range'] = '3'
        r['left_offset'] = 3
        self.view.run_command('ex_delete', {'line_range': r})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nabc'
        self.assertEqual(expected, actual)


@unittest.skip("Fixme")
class Test_ex_delete_Deleting_InNormalMode_MultipleLines(ViewTest):
    def setUp(self):
        super().setUp()
        self.range = {'left_ref': None,'left_offset': None, 'left_search_offsets': [],
                      'right_ref': None, 'right_offset': None, 'right_search_offsets': [],
                      'separator': ','}

    def testCanDeleteTwoLines(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 0)))

        self.range['left_offset'] = 2
        self.range['right_offset'] = 3
        self.range['text_range'] = '2,3'
        self.view.run_command('ex_delete', {'line_range': self.range})

        expected = 'abc\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanDeleteThreeLines(self):
        self.write('abc\nxxx\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 0)))

        self.range['left_offset'] = 2
        self.range['right_offset'] = 4
        self.range['text_range'] = '2,4'
        self.view.run_command('ex_delete', {'line_range': self.range})

        expected = 'abc\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    # TODO: fix this
    def testCanDeleteMultipleEmptyLines(self):
        self.write('abc\n\n\n\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((0, 0), (0, 0)))

        self.range['left_offset'] = 2
        self.range['right_offset'] = 4
        self.range['text_range'] = '2,4'
        self.view.run_command('ex_delete', {'line_range': self.range})

        expected = 'abc\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)


class Test_ex_delete_InNormalMode_CaretPosition(ViewTest):
    def setUp(self):
        super().setUp()
        self.range = {'left_ref': None,'left_offset': None, 'left_search_offsets': [],
                      'right_ref': None, 'right_offset': None, 'right_search_offsets': [],
                      'separator': ','}

    def testCanRepositionCaret(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((3, 0), (3, 0)))

        self.range['left_offset'] = 2
        self.range['text_range'] = '2,4'
        self.view.run_command('ex_delete', {'line_range': self.range})

        actual = list(self.view.sel())
        expected = [self.R((1, 0), (1, 0))]
        self.assertEqual(expected, actual)

    # TODO: test with multiple selections.


class Test_ex_delete_ModeTransition(ViewTest):
    def setUp(self):
        super().setUp()
        self.range = {'left_ref': None,'left_offset': None, 'left_search_offsets': [],
                      'right_ref': None, 'right_offset': None, 'right_search_offsets': [],
                      'separator': ','}

    def testFromNormalModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        state = State(self.view)
        state.enter_normal_mode()

        self.view.run_command('vi_enter_normal_mode')
        prev_mode = state.mode

        self.range['left_offset'] = 2
        self.range['text_range'] = '2'
        self.view.run_command('ex_delete', {'line_range': self.range})

        state = State(self.view)
        new_mode = state.mode
        self.assertEqual(prev_mode, new_mode)

    def testFromVisualModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 1)))

        state = State(self.view)
        state.enter_visual_mode()
        prev_mode = state.mode

        self.range['left_ref'] = "'<"
        self.range['right_ref'] = "'>"
        self.range['text_range'] = "'<,'>"
        self.view.run_command('ex_delete', {'line_range': self.range})

        state = State(self.view)
        new_mode = state.mode
        self.assertNotEqual(prev_mode, new_mode)
        self.assertEqual(new_mode, MODE_NORMAL)

########NEW FILE########
__FILENAME__ = test_global
import unittest

from Vintageous.ex.parsers.g_cmd import GlobalLexer


class TestGlobalLexer(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.lexer = GlobalLexer()

    def testCanMatchFullPattern(self):
        actual = self.lexer.parse(r'/foo/p#')
        self.assertEqual(actual, ['foo', 'p#'])

    def testCanMatchEmtpySearch(self):
        actual = self.lexer.parse(r'//p#')
        self.assertEqual(actual, ['', 'p#'])

    def testCanEscapeCharactersInSearchPattern(self):
        actual = self.lexer.parse(r'/\/foo\//p#')
        self.assertEqual(actual, ['/foo/', 'p#'])

    def testCanEscapeBackSlashes(self):
        actual = self.lexer.parse(r'/\\/p#')
        self.assertEqual(actual, ['\\', 'p#'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_location
import sublime

import unittest

from Vintageous.ex.ex_location import get_line_nr
from Vintageous.ex.ex_location import find_eol
from Vintageous.ex.ex_location import find_bol
from Vintageous.ex.ex_location import find_line
from Vintageous.ex.ex_location import search_in_range
from Vintageous.ex.ex_location import find_last_match
from Vintageous.ex.ex_location import reverse_search
from Vintageous.ex.ex_range import calculate_relative_ref


class TestHelpers(unittest.TestCase):
    @unittest.skip('todo: revise tests')
    def testGetCorrectLineNumber(self):
        self.assertEquals(get_line_nr(g_test_view, 1000), 19)

    @unittest.skip('todo: revise tests')
    def testfind_bolAndEol(self):
        values = (
            (find_eol(g_test_view, 1000), 1062),
            (find_eol(g_test_view, 2000), 2052),
            (find_bol(g_test_view, 1000), 986),
            (find_bol(g_test_view, 2000), 1981),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)


class TestSearchHelpers(unittest.TestCase):
    @unittest.skip('todo: revise tests')
    def testForwardSearch(self):
        values = (
            (find_line(g_test_view, target=30), sublime.Region(1668, 1679)),
            (find_line(g_test_view, target=1000), -1),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    @unittest.skip('todo: revise tests')
    def testSearchInRange(self):
        values = (
            (search_in_range(g_test_view, 'THIRTY', 1300, 1800), True),
            (search_in_range(g_test_view, 'THIRTY', 100, 100), None),
            (search_in_range(g_test_view, 'THIRTY', 100, 1000), None),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    @unittest.skip('todo: revise tests')
    def testFindLastMatch(self):
        values = (
            (find_last_match(g_test_view, 'Lorem', 0, 1200), sublime.Region(913, 918)),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    @unittest.skip('todo: revise tests')
    def testReverseSearch(self):
        values = (
            (reverse_search(g_test_view, 'THIRTY'), 30),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    @unittest.skip('todo: revise tests')
    def testReverseSearchNonMatchesReturnCurrentLine(self):
        self.assertEquals(g_test_view.rowcol(g_test_view.sel()[0].a)[0], 0)
        values = (
            (reverse_search(g_test_view, 'FOOBAR'), 1),
        )

        select_line(g_test_view, 10)
        values += (
            (reverse_search(g_test_view, 'FOOBAR'), 10),
        )

        select_line(g_test_view, 100)
        values += (
            (reverse_search(g_test_view, 'FOOBAR'), 100),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    @unittest.skip('todo: revise tests')
    def testCalculateRelativeRef(self):
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 1)
        self.assertEquals(calculate_relative_ref(g_test_view, '$'), 538)

        select_line(g_test_view, 100)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 100)

        select_line(g_test_view, 200)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 200)

    def setUp(self):
        super().setUp()
        select_line(g_test_view, 1)

    def tearDown(self):
        select_line(g_test_view, 1)

########NEW FILE########
__FILENAME__ = test_move
import unittest

from Vintageous.vi.utils import modes

from Vintageous.state import State

from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.ex_commands import CURRENT_LINE_RANGE


class Test_ex_move_Moving_InNormalMode_SingleLine_DefaultStart(ViewTest):
    def testCanMoveDefaultLineRange(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '3'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nxxx\nabc'
        self.assertEqual(expected, actual)

    def testCanMoveToEof(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '4'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\nabc\nxxx'
        self.assertEqual(expected, actual)

    def testCanMoveToBof(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '0'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'xxx\nabc\nabc\nabc'
        self.assertEqual(expected, actual)

    def testCanMoveToEmptyLine(self):
        self.write('abc\nxxx\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '4'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nabc\n\nxxx\nabc'
        self.assertEqual(expected, actual)

    def testCanMoveToSameLine(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '2'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\nabc'
        self.assertEqual(expected, actual)


class Test_ex_move_Moveing_InNormalMode_MultipleLines(ViewTest):
    def setUp(self):
        super().setUp()
        self.range = {'left_ref': '.','left_offset': 0, 'left_search_offsets': [],
                      'right_ref': '.', 'right_offset': 1, 'right_search_offsets': []}

    def testCanMoveDefaultLineRange(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '4', 'line_range': self.range})

        expected = 'abc\nabc\nxxx\nxxx\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanMoveToEof(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '5', 'line_range': self.range})

        expected = 'abc\nabc\nabc\nxxx\nxxx'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanMoveToBof(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '0', 'line_range': self.range})

        expected = 'xxx\nxxx\nabc\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanMoveToEmptyLine(self):
        self.write('abc\nxxx\nxxx\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '5', 'line_range': self.range})

        expected = 'abc\nabc\n\nxxx\nxxx\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    @unittest.skip("Not implemented")
    def testCanMoveToSameLine(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '2', 'line_range': self.range})

        expected = 'abc\nxxx\nxxx\nxxx\nxxx\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)


class Test_ex_move_InNormalMode_CaretPosition(ViewTest):
    def testCanRepositionCaret(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_move', {'address': '3'})

        actual = list(self.view.sel())
        expected = [self.R((2, 0), (2, 0))]
        self.assertEqual(expected, actual)

    # TODO: test with multiple selections.


class Test_ex_move_ModeTransition(ViewTest):
    def testFromNormalModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        state = State(self.view)
        state.enter_normal_mode()

        self.view.run_command('vi_enter_normal_mode')
        prev_mode = state.mode

        self.view.run_command('ex_move', {'address': '3'})

        state = State(self.view)
        new_mode = state.mode
        self.assertEqual(prev_mode, new_mode)

    def testFromVisualModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 1)))

        state = State(self.view)
        state.enter_visual_mode()
        prev_mode = state.mode

        self.view.run_command('ex_move', {'address': '3'})

        state = State(self.view)
        new_mode = state.mode
        self.assertNotEqual(prev_mode, new_mode)

########NEW FILE########
__FILENAME__ = test_range
import unittest
import re

from Vintageous.ex.ex_range import EX_RANGE
from Vintageous.ex.ex_range import new_calculate_range
from Vintageous.ex.ex_range import calculate_relative_ref
from Vintageous.ex.ex_range import calculate_address


class TestCalculateRelativeRef(unittest.TestCase):
    def StartUp(self):
        select_bof(g_test_view)

    def tearDown(self):
        select_bof(g_test_view)

    @unittest.skip('TODO: revise test')
    def testCalculateRelativeRef(self):
        values = (
            (calculate_relative_ref(g_test_view, '.'), 1),
            (calculate_relative_ref(g_test_view, '.', start_line=100), 101),
            (calculate_relative_ref(g_test_view, '$'), 538),
            (calculate_relative_ref(g_test_view, '$', start_line=100), 538),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    @unittest.skip('TODO: revise test')
    def testCalculateRelativeRef2(self):
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 1)
        self.assertEquals(calculate_relative_ref(g_test_view, '$'), 538)

        select_line(g_test_view, 100)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 100)

        select_line(g_test_view, 200)
        self.assertEquals(calculate_relative_ref(g_test_view, '.'), 200)


class TestCalculatingRanges(unittest.TestCase):
    @unittest.skip('TODO: revise test')
    def testCalculateCorrectRange(self):
        values = (
            (new_calculate_range(g_test_view, '0'), [(0, 0)]),
            (new_calculate_range(g_test_view, '1'), [(1, 1)]),
            (new_calculate_range(g_test_view, '1,1'), [(1, 1)]),
            (new_calculate_range(g_test_view, '%,1'), [(1, 538)]),
            (new_calculate_range(g_test_view, '1,%'), [(1, 538)]),
            (new_calculate_range(g_test_view, '1+99,160-10'), [(100, 150)]),
            (new_calculate_range(g_test_view, '/THIRTY/+10,100'), [(40, 100)]),
        )

        select_line(g_test_view, 31)
        values += (
            (new_calculate_range(g_test_view, '10,/THIRTY/'), [(10, 31)]),
            (new_calculate_range(g_test_view, '10;/THIRTY/'), [(10, 30)]),
        )

        for actual, expected in values:
            self.assertEquals(actual, expected)

    def tearDown(self):
        select_bof(g_test_view)


class CalculateAddress(unittest.TestCase):
    def setUp(self):
        super().setUp()
        select_eof(g_test_view)

    def tearDown(self):
        select_bof(g_test_view)

    @unittest.skip('TODO: revise test')
    def testCalculateAddressCorrectly(self):
        values = (
            (dict(ref='100', offset=None, search_offsets=[]), 99),
            (dict(ref='200', offset=None, search_offsets=[]), 199),
        )

        for v, expected in values:
            self.assertEquals(calculate_address(g_test_view, v), expected)

    @unittest.skip('TODO: revise test')
    def testOutOfBoundsAddressShouldReturnNone(self):
        address = dict(ref='1000', offset=None, search_offsets=[])
        self.assertEquals(calculate_address(g_test_view, address), None)

    @unittest.skip('TODO: revise test')
    def testInvalidAddressShouldReturnNone(self):
        address = dict(ref='XXX', offset=None, search_offsets=[])
        self.assertRaises(AttributeError, calculate_address, g_test_view, address)

########NEW FILE########
__FILENAME__ = test_shell_out
import unittest
import os

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import ViewTest

import Vintageous.ex.plat as plat
from Vintageous.ex.ex_command_parser import parse_command

class Test_ex_shell_out_no_input(ViewTest):
    @unittest.skipIf(os.name == 'nt', 'not supported on Windows')
    def testCommandOutput(self):
        test_string = 'Testing!'
        test_command_line = ':!echo "' + test_string + '"'
        ex_cmd = parse_command(test_command_line)
        ex_cmd.args['line_range'] = ex_cmd.line_range

        output_panel = self.view.window().get_output_panel('vi_out')
        self.view.run_command(ex_cmd.command, ex_cmd.args)

        actual = output_panel.substr(self.R(0, output_panel.size()))
        expected = test_string + '\n'
        self.assertEqual(expected, actual)

    @unittest.skipIf(os.name != 'nt', 'Windows')
    def testCommandOutput(self):
        test_string = 'Testing!'
        test_command_line = ':!echo "' + test_string + '"'
        ex_cmd = parse_command(test_command_line)
        ex_cmd.args['line_range'] = ex_cmd.line_range

        output_panel = self.view.window().get_output_panel('vi_out')
        self.view.run_command(ex_cmd.command, ex_cmd.args)

        actual = output_panel.substr(self.R(0, output_panel.size()))
        expected = '\\"{0}\\"\n'.format(test_string)
        self.assertEqual(expected, actual)

    def tearDown(self):
        self.view.window().run_command(
                            'show_panel', {'panel': 'output.vintageous.tests'}
                            )


class Test_ex_shell_out_filter_through_shell(ViewTest):
    @staticmethod
    def getWordCountCommand():
        if plat.HOST_PLATFORM == plat.WINDOWS:
            return None
        else:
            return 'wc -w'

    @unittest.skipIf(os.name == 'nt', 'Windows')
    def testSimpleFilterThroughShell(self):
        word_count_command = self.__class__.getWordCountCommand()
        # TODO implement test for Windows.
        if not word_count_command:
            return True
        self.view.sel().clear()
        self.write('One two three four\nfive six seven eight\nnine ten.')
        self.add_sel(self.R((0, 8), (1, 3)))

        test_command_line = ":'<,'>!" + word_count_command
        ex_cmd = parse_command(test_command_line)
        ex_cmd.args['line_range'] = ex_cmd.line_range

        self.view.run_command(ex_cmd.command, ex_cmd.args)

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = '8\nnine ten.'
        self.assertEqual(expected, actual)
        self.assertEqual(1, len(self.view.sel()))
        cursor = get_sel(self.view, 0)
        self.assertEqual(cursor.begin(), cursor.end())
        self.assertEqual(self.view.text_point(0, 0), cursor.begin())

    @unittest.skipIf(os.name == 'nt', 'Windows')
    def testMultipleFilterThroughShell(self):
        word_count_command = self.__class__.getWordCountCommand()
        # TODO implement test for Windows.
        if not word_count_command:
            return True
        self.view.sel().clear()
        self.write('''Beginning of test!
One two three four
five six seven eight
nine ten.
These two lines shouldn't be replaced
by the command.
One two three four five six
seven eight nine
ten
eleven
twelve
End of Test!
''')
        # Two selections touching all numeric word lines.
        self.add_sel(self.R((1, 11), (3, 1)))
        self.add_sel(self.R((6, 1), (10, 5)))

        test_command_line = ":'<,'>!" + word_count_command
        ex_cmd = parse_command(test_command_line)
        ex_cmd.args['line_range'] = ex_cmd.line_range

        self.view.run_command(ex_cmd.command, ex_cmd.args)

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = '''Beginning of test!
10
These two lines shouldn't be replaced
by the command.
12
End of Test!
'''
        self.assertEqual(expected, actual)
        self.assertEqual(2, len(self.view.sel()))
        cursor0 = get_sel(self.view, 0)
        cursor1 = get_sel(self.view, 1)
        self.assertEqual(cursor0.begin(), cursor0.end())
        self.assertEqual(cursor1.begin(), cursor1.end())
        self.assertEqual(self.view.text_point(1, 0), cursor0.begin())
        self.assertEqual(self.view.text_point(4, 0), cursor1.begin())


########NEW FILE########
__FILENAME__ = test_substitute
import unittest

from Vintageous.ex.parsers.s_cmd import SubstituteLexer
from Vintageous.ex.parsers.parsing import RegexToken
from Vintageous.ex.parsers.parsing import Lexer
from Vintageous.ex.parsers.parsing import EOF


class TestRegexToken(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.token = RegexToken("f[o]+")

    def testCanTestMembership(self):
        self.assertTrue("fo" in self.token)
        self.assertTrue("foo" in self.token)

    def testCanTestEquality(self):
        self.assertTrue("fo" == self.token)


class TestLexer(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.lexer = Lexer()

    def testEmptyInputSetsCursorToEOF(self):
        self.lexer.parse('')
        self.assertEqual(self.lexer.c, EOF)

    def testDoesReset(self):
        c, cursor, string = self.lexer.c, self.lexer.cursor, self.lexer.string
        self.lexer.parse('')
        self.lexer._reset()
        self.assertEqual(c, self.lexer.c)
        self.assertEqual(cursor, self.lexer.cursor)
        self.assertEqual(string, self.lexer.string)

    def testCursorIsPrimed(self):
        self.lexer.parse("foo")
        self.assertEqual(self.lexer.c, 'f')

    def testCanConsume(self):
        self.lexer.parse("foo")
        self.lexer.consume()
        self.assertEqual(self.lexer.c, 'o')
        self.assertEqual(self.lexer.cursor, 1)

    def testCanReachEOF(self):
        self.lexer.parse("f")
        self.lexer.consume()
        self.assertEqual(self.lexer.c, EOF)

    def testPassingInJunk(self):
        self.assertRaises(TypeError, self.lexer.parse, 100)
        self.assertRaises(TypeError, self.lexer.parse, [])


class TestSubstituteLexer(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.lexer = SubstituteLexer()

    def testCanParseEmptyInput(self):
        actual = self.lexer.parse('')

        self.assertEqual(actual, ['', ''])

    def testCanParseShortFormWithFlagsOnly(self):
        one_flag = self.lexer.parse(r'g')
        many_flags = self.lexer.parse(r'gi')

        self.assertEqual(one_flag, ['g', ''])
        self.assertEqual(many_flags, ['gi', ''])

    def testCanParseShortFormWithCountOnly(self):
        actual = self.lexer.parse(r'100')

        self.assertEqual(actual, ['', '100'])

    def testCanParseShortFormWithFlagsAndCount(self):
        actual_1 = self.lexer.parse(r'gi100')
        actual_2 = self.lexer.parse(r'  gi  100  ')

        self.assertEqual(actual_1, ['gi', '100'])
        self.assertEqual(actual_2, ['gi', '100'])

    def testThrowErrorIfCountIsFollowedByAnything(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"100gi")

    def testThrowErrorIfShortFormIsFollowedByAnythingOtherThanFlagsOrCount(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"x")

    def testCanParseOneSeparatorOnly(self):
        actual = self.lexer.parse(r"/")

        self.assertEqual(actual, ['', '', '', ''])

    def testCanParseTwoSeparatorsOnly(self):
        actual = self.lexer.parse(r"//")

        self.assertEqual(actual, ['', '', '', ''])

    def testCanParseThreeSeparatorsOnly(self):
        actual = self.lexer.parse(r"///")

        self.assertEqual(actual, ['', '', '', ''])

    def testCanParseOnlySearchPattern(self):
        actual = self.lexer.parse(r"/foo")

        self.assertEqual(actual, ['foo', '', '', ''])

    def testCanParseOnlyReplacementString(self):
        actual = self.lexer.parse(r"//foo")

        self.assertEqual(actual, ['', 'foo', '', ''])

    def testCanParseOnlyFlags(self):
        actual = self.lexer.parse(r"///gi")

        self.assertEqual(actual, ['', '', 'gi', ''])

    def testCanParseOnlyCount(self):
        actual = self.lexer.parse(r"///100")

        self.assertEqual(actual, ['', '', '', '100'])

    def testCanParseOnlyFlagsAndCount(self):
        actual = self.lexer.parse(r"///gi100")

        self.assertEqual(actual, ['', '', 'gi', '100'])

    def testThrowIfFlagsAndCountAreReversed(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"///100gi")

    def testThrowIfFlagsAndCountAreInvalid(self):
        self.assertRaises(SyntaxError, self.lexer.parse, r"///x")

    def testCanEscapeDelimiter(self):
        actual = self.lexer.parse(r"/foo\/")

        self.assertEqual(actual, ['foo/', '', '', ''])

    def testCanEscapeDelimiterComplex(self):
        actual = self.lexer.parse(r"/foo\//hello")

        self.assertEqual(actual, ['foo/', 'hello', '', ''])

########NEW FILE########
__FILENAME__ = test_entering_normal_mode
import unittest

from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL
from Vintageous.vi.constants import MODE_NORMAL
from Vintageous.vi.constants import MODE_VISUAL
from Vintageous.vi.constants import MODE_VISUAL_LINE
from Vintageous.state import State
# from Vintageous.vi.actions import vi_r

from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


class Test_vi_enter_normal_mode__SingleSelection__LeftRoRight(ViewTest):
    def testCaretEndsInExpectedRegion(self):
        self.write('foo bar\nfoo bar\nfoo bar\n')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 3)))

        State(self.view).mode = MODE_VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': MODE_VISUAL})
        self.assertEqual(self.R((1, 2), (1, 2)), first_sel(self.view))


class Test_vi_enter_normal_mode__SingleSelection__RightToLeft(ViewTest):

    def testCaretEndsInExpectedRegion(self):
        self.write(''.join(('foo bar\nfoo bar\nfoo bar\n',)))
        self.clear_sel()
        self.add_sel(self.R((1, 3), (1, 0)))

        self.state.mode = MODE_VISUAL

        self.view.run_command('_enter_normal_mode', {'mode': MODE_VISUAL})
        self.assertEqual(self.R((1, 0), (1, 0)), first_sel(self.view))


class Test_vi_r__SingleSelection__RightToLeft(ViewTest):
    @unittest.skip("must fix this")
    def testCaretEndsInExpectedRegion(self):
        self.write(''.join(('foo bar\nfoo bar\nfoo bar\n',)))
        self.clear_sel()
        self.add_sel(self.R((1, 3), (1, 0)))

        state = State(self.view)
        state.enter_visual_mode()

        # TODO: we should bypass vi_r and define the values directly.
        data = CmdData(state)
        # data = vi_r(data)
        data['action']['args']['character'] = 'X'

        self.view.run_command('vi_run', data)

        self.assertEqual(self.R((1, 0), (1, 0)), first_sel(self.view))

########NEW FILE########
__FILENAME__ = test_state
import unittest
from unittest import mock
from unittest.mock import call

import sublime

from Vintageous import state
from Vintageous.vi.utils import modes
from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import make_region
from Vintageous.tests import ViewTest
from Vintageous.vi.cmd_base import cmd_types
from Vintageous.vi import cmd_defs


class StateTestCase(ViewTest):
    def setUp(self):
        super().setUp()


class Test_State(StateTestCase):
    def test_is_in_any_visual_mode(self):
        self.assertEqual(self.state.in_any_visual_mode(), False)

        self.state.mode = modes.NORMAL
        self.assertEqual(self.state.in_any_visual_mode(), False)
        self.state.mode = modes.VISUAL
        self.assertEqual(self.state.in_any_visual_mode(), True)
        self.state.mode = modes.VISUAL_LINE
        self.assertEqual(self.state.in_any_visual_mode(), True)
        self.state.mode = modes.VISUAL_BLOCK
        self.assertEqual(self.state.in_any_visual_mode(), True)

    def testCanInitialize(self):
        s = state.State(self.view)
        # Make sure the actual usage of Vintageous doesn't change the pristine
        # state. This isn't great, though.
        self.view.window().settings().erase('_vintageous_last_char_search_command')
        self.view.window().settings().erase('_vintageous_last_character_search')
        self.view.window().settings().erase('_vintageous_last_buffer_search')

        self.assertEqual(s.sequence, '')
        self.assertEqual(s.partial_sequence, '')
        self.assertEqual(s.mode, modes.NORMAL)
        self.assertEqual(s.action, None)
        self.assertEqual(s.motion, None)
        self.assertEqual(s.action_count, '')
        self.assertEqual(s.glue_until_normal_mode, False)
        self.assertEqual(s.gluing_sequence, False)
        self.assertEqual(s.last_character_search, '')
        self.assertEqual(s.last_char_search_command, 'vi_f')
        self.assertEqual(s.non_interactive, False)
        self.assertEqual(s.capture_register, False)
        self.assertEqual(s.last_buffer_search, '')
        self.assertEqual(s.reset_during_init, True)

    def test_must_scroll_into_view(self):
        self.assertFalse(self.state.must_scroll_into_view())

        motion = cmd_defs.ViGotoSymbolInFile()
        self.state.motion = motion
        self.assertTrue(self.state.must_scroll_into_view())


class Test_State_Mode_Switching(StateTestCase):
    def test_enter_normal_mode(self):
        self.assertEqual(self.state.mode, modes.NORMAL)
        self.state.mode = modes.UNKNOWN
        self.assertNotEqual(self.state.mode, modes.NORMAL)
        self.state.enter_normal_mode()
        self.assertEqual(self.state.mode, modes.NORMAL)

    def test_enter_visual_mode(self):
        self.assertEqual(self.state.mode, modes.NORMAL)
        self.state.enter_visual_mode()
        self.assertEqual(self.state.mode, modes.VISUAL)

    def test_enter_insert_mode(self):
        self.assertEqual(self.state.mode, modes.NORMAL)
        self.state.enter_insert_mode()
        self.assertEqual(self.state.mode, modes.INSERT)


class Test_State_Resetting_State(StateTestCase):
    def test_reset_sequence(self):
        self.state.sequence = 'x'
        self.state.reset_sequence()
        self.assertEqual(self.state.sequence, '')

    def test_reset_partial_sequence(self):
        self.state.partial_sequence = 'x'
        self.state.reset_partial_sequence()
        self.assertEqual(self.state.partial_sequence, '')

    def test_reset_command_data(self):
        self.state.sequence = 'abc'
        self.state.partial_sequence = 'x'
        self.state.user_input = 'f'
        self.state.action = cmd_defs.ViReplaceCharacters()
        self.state.motion = cmd_defs.ViGotoSymbolInFile()
        self.state.action_count = '10'
        self.state.motion_count = '100'
        self.state.register = 'a'
        self.state.capture_register = True

        self.state.reset_command_data()

        self.assertEqual(self.state.action, None)
        self.assertEqual(self.state.motion, None)
        self.assertEqual(self.state.action_count, '')
        self.assertEqual(self.state.motion_count, '')

        self.assertEqual(self.state.sequence, '')
        self.assertEqual(self.state.partial_sequence, '')
        self.assertEqual(self.state.register, '"')
        self.assertEqual(self.state.capture_register, False)


class Test_State_Resetting_Volatile_Data(StateTestCase):
    def test_reset_volatile_data(self):
        self.state.glue_until_normal_mode = True
        self.state.gluing_sequence = True
        self.state.non_interactive = True
        self.state.reset_during_init = False

        self.state.reset_volatile_data()

        self.assertFalse(self.state.glue_until_normal_mode)
        self.assertFalse(self.state.gluing_sequence)
        self.assertFalse(self.state.non_interactive)
        self.assertTrue(self.state.reset_during_init)


class Test_State_counts(StateTestCase):
    def testCanRetrieveGoodActionCount(self):
        self.state.action_count = '10'
        self.assertEqual(self.state.count, 10)

    def testFailsIfBadActionCount(self):
        self.state.action_count = 'x'
        self.assertRaises(ValueError, lambda: self.state.count)

    def testFailsIfBadMotionCount(self):
        self.state.motion_count = 'x'
        self.assertRaises(ValueError, lambda: self.state.count)

    def testCountIsNeverLessThan1(self):
        self.state.motion_count = '0'
        self.assertEqual(self.state.count, 1)
        self.state.motion_count = '-1'
        self.assertRaises(ValueError, lambda: self.state.count)

    def testCanRetrieveGoodMotionCount(self):
        self.state.motion_count = '10'
        self.assertEqual(self.state.count, 10)

    def testCanRetrieveGoodCombinedCount(self):
        self.state.motion_count = '10'
        self.state.action_count = '10'
        self.assertEqual(self.state.count, 100)


class Test_State_Mode_Names(unittest.TestCase):
    def testModeName(self):
        self.assertEqual(modes.COMMAND_LINE, 'mode_command_line')
        self.assertEqual(modes.INSERT, 'mode_insert')
        self.assertEqual(modes.INTERNAL_NORMAL, 'mode_internal_normal')
        self.assertEqual(modes.NORMAL, 'mode_normal')
        self.assertEqual(modes.OPERATOR_PENDING, 'mode_operator_pending')
        self.assertEqual(modes.VISUAL, 'mode_visual')
        self.assertEqual(modes.VISUAL_BLOCK, 'mode_visual_block')
        self.assertEqual(modes.VISUAL_LINE, 'mode_visual_line')


class Test_State_Runnability(StateTestCase):
    def test_can_run_action(self):
        self.assertEqual(self.state.can_run_action(), None)

        self.state.mode = modes.VISUAL
        self.assertEqual(self.state.can_run_action(), None)

        self.state.action = cmd_defs.ViDeleteByChars()
        self.state.mode = modes.VISUAL
        self.assertEqual(self.state.can_run_action(), True)

        self.state.action = cmd_defs.ViDeleteLine()
        self.state.mode = modes.VISUAL
        self.assertEqual(self.state.can_run_action(), True)

        self.state.mode = modes.NORMAL
        self.state.action = cmd_defs.ViDeleteByChars()
        self.assertEqual(self.state.can_run_action(), None)

        self.state.mode = modes.NORMAL
        self.state.action = cmd_defs.ViDeleteLine()
        self.assertEqual(self.state.can_run_action(), True)

    def test_runnable_IfActionAndMotionAvailable(self):
        self.state.mode = modes.NORMAL
        self.state.action = cmd_defs.ViDeleteLine()
        self.state.motion = cmd_defs.ViMoveRightByChars()
        self.assertEqual(self.state.runnable(), True)

        self.state.mode = 'junk'
        self.state.action = cmd_defs.ViDeleteByChars()
        self.state.motion = cmd_defs.ViMoveRightByChars()
        self.assertRaises(ValueError, self.state.runnable)

    def test_runnable_IfMotionAvailable(self):
        self.state.mode = modes.NORMAL
        self.state.motion = cmd_defs.ViMoveRightByChars()
        self.assertEqual(self.state.runnable(), True)

        self.state.mode = modes.OPERATOR_PENDING
        self.state.motion = cmd_defs.ViMoveRightByChars()
        self.assertRaises(ValueError, self.state.runnable)

    def test_runnable_IfActionAvailable(self):
        self.state.mode = modes.NORMAL
        self.state.action = cmd_defs.ViDeleteLine()
        self.assertEqual(self.state.runnable(), True)

        self.state.action = cmd_defs.ViDeleteByChars()
        self.assertEqual(self.state.runnable(), False)

        self.state.mode = modes.OPERATOR_PENDING
        # ensure we can run the action
        self.state.action = cmd_defs.ViDeleteLine()
        self.assertRaises(ValueError, self.state.runnable)


class Test_State_set_command(StateTestCase):
    def testRaiseErrorIfUnknownCommandType(self):
        fake_command = {'type': 'foo'}
        self.assertRaises(AssertionError, self.state.set_command, fake_command)

    def testRaisesErrorIfTooManyMotions(self):
        self.state.motion = cmd_defs.ViMoveRightByChars()

        self.assertRaises(ValueError, self.state.set_command, cmd_defs.ViMoveRightByChars())

    def testChangesModeForLoneMotion(self):
        self.state.mode = modes.OPERATOR_PENDING

        motion = cmd_defs.ViMoveRightByChars()
        self.state.set_command(motion)

        self.assertEqual(self.state.mode, modes.NORMAL)

    def testRaisesErrorIfTooManyActions(self):
        self.state.motion = cmd_defs.ViDeleteLine()

        self.assertRaises(ValueError, self.state.set_command, cmd_defs.ViDeleteLine())

    def testChangesModeForLoneAction(self):
        operator = cmd_defs.ViDeleteByChars()

        self.state.set_command(operator)

        self.assertEqual(self.state.mode, modes.OPERATOR_PENDING)

########NEW FILE########
__FILENAME__ = test_a_word
import unittest

from Vintageous.vi.constants import MODE_NORMAL
from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL

from Vintageous.tests import ViewTest
from Vintageous.tests import set_text
from Vintageous.tests import add_sel

from Vintageous.vi.text_objects import a_word


class Test_a_word_InInternalNormalMode_Inclusive(ViewTest):
    def testReturnsFullWord_CountOne(self):
        set_text(self.view, 'foo bar baz\n')
        r = self.R(5, 5)
        add_sel(self.view, r)

        reg = a_word(self.view, r.b)
        self.assertEqual('bar ', self.view.substr(reg))

    def testReturnsWordAndPrecedingWhiteSpace_CountOne(self):
        set_text(self.view, '(foo bar) baz\n')
        r = self.R(5, 5)
        add_sel(self.view, r)

        reg = a_word(self.view, r.b)
        self.assertEqual(' bar', self.view.substr(reg))

    def testReturnsWordAndAllPrecedingWhiteSpace_CountOne(self):
        set_text(self.view, '(foo   bar) baz\n')
        r = self.R(8, 8)
        add_sel(self.view, r)

        reg = a_word(self.view, r.b)
        self.assertEqual('   bar', self.view.substr(reg))

########NEW FILE########
__FILENAME__ = test_big_word
# from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL
from Vintageous.vi.constants import MODE_NORMAL
# from Vintageous.vi.constants import MODE_VISUAL
# from Vintageous.vi.constants import MODE_VISUAL_LINE

from collections import namedtuple

from Vintageous.tests import ViewTest
from Vintageous.tests import set_text
from Vintageous.tests import add_sel

from Vintageous.vi.units import next_big_word_start
from Vintageous.vi.units import big_word_starts
from Vintageous.vi.units import CLASS_VI_INTERNAL_WORD_START

# TODO: Test against folded regions.
# TODO: Ensure that we only create empty selections while testing. Add assert_all_sels_empty()?
test_data = namedtuple('test_data', 'initial_text region expected msg')
region_data = namedtuple('region_data', 'regions')


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))

def  first_sel_wrapper(test):
    return first_sel(test.view)


TESTS_MOVE_FORWARD = (
    test_data(initial_text='  foo bar\n', region=(0, 0), expected=2, msg=''),
    test_data(initial_text='  (foo)\n', region=(0, 0), expected=2, msg=''),
    test_data(initial_text='  \n\n\n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='  \n  \n\n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='  \n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='   ', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='   \nfoo\nbar', region=(0, 0), expected=4, msg=''),
    test_data(initial_text='   \n foo\nbar', region=(0, 0), expected=4, msg=''),
    test_data(initial_text='  a foo bar\n', region=(0, 0), expected=2, msg=''),
    test_data(initial_text='  \na\n\n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='  \n a\n\n', region=(0, 0), expected=3, msg=''),

    test_data(initial_text='(foo) bar\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo) (bar)\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n\n\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n  \n\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)', region=(0, 0), expected=5, msg=''),
    test_data(initial_text='(foo)\nbar\nbaz', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n bar\nbaz', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo) a bar\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\na\n\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n a\n\n', region=(0, 0), expected=6, msg=''),
)


class Test_big_word_all(ViewTest):
    def testAll(self):
        set_text(self.view, '  foo bar\n')

        for (i, data) in enumerate(TESTS_MOVE_FORWARD):
            self.view.sel().clear()

            self.write(data.initial_text)
            r = self.R(*data.region)
            self.add_sel(r)

            pt = next_big_word_start(self.view, r.b)
            self.assertEqual(pt, data.expected, 'failed at test index {0}'.format(i))


class Test_next_big_word_start_InNormalMode_FromWord(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '(foo) bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToPunctuationStart(self):
        set_text(self.view, '(foo) (bar)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToEmptyLine(self):
        set_text(self.view, '(foo)\n\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToWhitespaceLine(self):
        set_text(self.view, '(foo)\n  \n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToEofWithNewline(self):
        set_text(self.view, '(foo)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToEof(self):
        set_text(self.view, '(foo)')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 5)

    def testToOneWordLine(self):
        set_text(self.view, '(foo)\nbar\nbaz')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '(foo)\n bar\nbaz')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneCharWord(self):
        set_text(self.view, '(foo) a bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneCharLine(self):
        set_text(self.view, '(foo)\na\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '(foo)\n a\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)


class Test_next_big_word_start_InNormalMode_FromPunctuationStart(ViewTest):
    def testToWordStart(self):
        set_text(self.view, ':foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 5)

    def testToPunctuationStart(self):
        set_text(self.view, ': (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEmptyLine(self):
        set_text(self.view, ':\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToWhitespaceLine(self):
        set_text(self.view, ':\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEofWithNewline(self):
        set_text(self.view, ':\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEof(self):
        set_text(self.view, ':')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneWordLine(self):
        set_text(self.view, ':\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, ':\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharWord(self):
        set_text(self.view, ':a bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharLine(self):
        set_text(self.view, ':\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, ':\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)


class Test_next_big_word_start_InNormalMode_FromEmptyLine(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '\nfoo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToPunctuationStart(self):
        set_text(self.view, '\n (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEmptyLine(self):
        set_text(self.view, '\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToWhitespaceLine(self):
        set_text(self.view, '\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEofWithNewline(self):
        set_text(self.view, '\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEof(self):
        set_text(self.view, '')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 0)

    def testToOneWordLine(self):
        set_text(self.view, '\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharWord(self):
        set_text(self.view, '\na bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLine(self):
        set_text(self.view, '\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)


class Test_next_big_word_start_InNormalMode_FromPunctuation(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '::foo\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToPunctuationStart(self):
        set_text(self.view, ':: (foo)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEmptyLine(self):
        set_text(self.view, '::\n\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToWhitespaceLine(self):
        set_text(self.view, '::\n  \n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEofWithNewline(self):
        set_text(self.view, '::\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEof(self):
        set_text(self.view, '::')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneWordLine(self):
        set_text(self.view, '::\nbar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharWord(self):
        set_text(self.view, '::a bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharLine(self):
        set_text(self.view, '::\na\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n a\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)


class Test_next_big_word_start_InInternalNormalMode_FromWhitespace(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '  \n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '  \n foo')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_next_big_word_start_InInternalNormalMode_FromWordStart(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, 'foo\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)


class Test_next_big_word_start_InInternalNormalMode_FromWord(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '(foo)\n  ')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 5)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '(foo)\n bar')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 5)


class Test_next_big_word_start_InInternalNormalMode_FromPunctuationStart(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '.\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '.\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)


class Test_next_big_word_start_InInternalNormalMode_FromPunctuation(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '::\n  ')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n bar')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_next_big_word_start_InInternalNormalMode_FromEmptyLine(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 0)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 0)


class Test_big_word_starts_InNormalMode(ViewTest):
    def testMove1(self):
        set_text(self.view, '(foo) bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b)
        self.assertEqual(pt, 6)

    def testMove2(self):
        set_text(self.view, '(foo) bar fizz\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=2)
        self.assertEqual(pt, 10)

    def testMove10(self):
        set_text(self.view, ''.join(('(foo) bar\n',) * 5))
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=9)
        self.assertEqual(pt, 46)


class Test_big_word_starts_InInternalNormalMode_FromEmptyLine(ViewTest):
    # We can assume the stuff tested for normal mode applies to internal normal mode, so we
    # don't bother with that. Instead, we only test the differing behavior when advancing by
    # word starts in internal normal.
    def testMove1ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n (bar)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)

    def testMove2ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n (bar)')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=2, internal=True)
        self.assertEqual(pt, 6)

    def testMove1ToWhitespaceLine(self):
        set_text(self.view, '\n  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=1, internal=True)
        self.assertEqual(pt, 1)

    def testMove2ToOneWordLine(self):
        set_text(self.view, '\n(foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

    def testMove3AndSwallowLastNewlineChar(self):
        set_text(self.view, '\nfoo\n (bar)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=3)
        self.assertEqual(pt, 12)

    def testMove2ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n(foo)\n  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)


class Test_big_word_starts_InInternalNormalMode_FromOneWordLine(ViewTest):
    # We can assume the stuff tested for normal mode applies to internal normal mode, so we
    # don't bother with that. Instead, we only test the differing behavior when advancing by
    # word starts in internal normal.
    def testMove2ToEol(self):
        set_text(self.view, 'foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=1)
        self.assertEqual(pt, 3)

    def testMove2ToLineWithLeadingWhiteSpaceFromWordStart(self):
        set_text(self.view, '(foo)\n\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

    def testMove2ToEmptyLineFromWord(self):
        set_text(self.view, '(foo)\n\nbar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 6)

    def testMove2ToOneWordLineFromWordStart(self):
        set_text(self.view, '(foo)\nbar\nccc\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 10)

    def testMove2ToOneWordLineFromWord(self):
        set_text(self.view, '(foo)\nbar\nccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 9)

    def testMove2ToWhitespaceline(self):
        set_text(self.view, '(foo)\n  \nccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 12)

    def testMove2ToWhitespacelineFollowedByLeadingWhitespaceFromWord(self):
        set_text(self.view, '(foo)\n  \n ccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 13)

    def testMove2ToWhitespacelineFollowedByLeadingWhitespaceFromWordStart(self):
        set_text(self.view, '(foo)\n  \n ccc\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 14)


class Test_big_word_starts_InInternalNormalMode_FromLine(ViewTest):
    def testMove2ToEol(self):
        set_text(self.view, 'foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

########NEW FILE########
__FILENAME__ = test_big_word_reverse
import unittest
from collections import namedtuple

from Vintageous.vi.text_objects import word_reverse
from Vintageous.vi.utils import modes
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content args expected msg')


TESTS = (
    test_data(content='abc',           args=(2, 1), expected=0, msg='find word start from the middle of a word'),
    test_data(content='abc abc abc',   args=(8, 1), expected=4, msg='find word start from next word'),
    test_data(content='abc abc abc',   args=(8, 2), expected=0, msg='find word start from next word (count: 2)'),
    test_data(content='abc\nabc\nabc', args=(8, 1), expected=4, msg='find word start from different line'),
    test_data(content='abc\n\nabc',    args=(5, 1), expected=4, msg='stop at empty line'),
    test_data(content='abc a abc',     args=(6, 1), expected=4, msg='stop at single-char word'),
    test_data(content='(abc) abc',     args=(6, 1), expected=0, msg='skip over punctuation simple'),
    test_data(content='abc.(abc)',     args=(6, 1), expected=0, msg='skip over punctuation complex'),
    test_data(content='abc == abc',     args=(7, 1), expected=4, msg='stop at isolated punctuation word'),
)


class Test_word_reverse(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            self.write(data.content)
            actual = word_reverse(self.view, *data.args, big=True)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test_find_paragraph_text_object
import unittest

from Vintageous.vi.constants import MODE_NORMAL
from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL

from Vintageous.tests import ViewTest
from Vintageous.tests import set_text
from Vintageous.tests import add_sel

from Vintageous.vi.text_objects import find_paragraph_text_object


class Test_find_paragraph_text_object_InInternalNormalMode_Inclusive(ViewTest):
    def testReturnsFullParagraph_CountOne(self):
        text = (
            'line 1 in paragraph 1',
            'line 2 in paragraph 1',
            'line 3 in paragraph 1',
            '',
            'line 1 in paragraph 2',
            'line 2 in paragraph 2',
            'line 3 in paragraph 2',
            '',
            'line 1 in paragraph 3',
            'line 2 in paragraph 3',
            'line 3 in paragraph 3',
        )
        set_text(self.view, '\n'.join(text))
        r = self.R((4, 2), (4, 2))
        add_sel(self.view, r)

        expected = (
            '\nline 1 in paragraph 2\n',
            'line 2 in paragraph 2\n',
            'line 3 in paragraph 2\n',
            )

        reg = find_paragraph_text_object(self.view, r)
        self.assertEqual(''.join(expected), self.view.substr(reg))

    # def testReturnsWordAndPrecedingWhiteSpace_CountOne(self):
    #     set_text(self.view, '(foo bar) baz\n')
    #     r = self.R(5, 5)
    #     add_sel(self.view, r)

    #     reg = a_word(self.view, r.b)
    #     self.assertEqual(' bar', self.view.substr(reg))

    # def testReturnsWordAndAllPrecedingWhiteSpace_CountOne(self):
    #     set_text(self.view, '(foo   bar) baz\n')
    #     r = self.R(8, 8)
    #     add_sel(self.view, r)

    #     reg = a_word(self.view, r.b)
    #     self.assertEqual('   bar', self.view.substr(reg))


class Test_find_paragraph_text_object_InInternalNormalMode_Exclusive(ViewTest):
    def testReturnsFullParagraph_CountOne(self):
        text = (
            'line 1 in paragraph 1',
            'line 2 in paragraph 1',
            'line 3 in paragraph 1',
            '',
            'line 1 in paragraph 2',
            'line 2 in paragraph 2',
            'line 3 in paragraph 2',
            '',
            'line 1 in paragraph 3',
            'line 2 in paragraph 3',
            'line 3 in paragraph 3',
        )
        set_text(self.view, '\n'.join(text))
        r = self.R((4, 2), (4, 2))
        add_sel(self.view, r)

        expected = (
            'line 1 in paragraph 2\n',
            'line 2 in paragraph 2\n',
            'line 3 in paragraph 2\n',
            )

        reg = find_paragraph_text_object(self.view, r, inclusive=False)
        self.assertEqual(''.join(expected), self.view.substr(reg))

    # def testReturnsWordAndPrecedingWhiteSpace_CountOne(self):
    #     set_text(self.view, '(foo bar) baz\n')
    #     r = self.R(5, 5)
    #     add_sel(self.view, r)

    #     reg = a_word(self.view, r.b)
    #     self.assertEqual(' bar', self.view.substr(reg))

    # def testReturnsWordAndAllPrecedingWhiteSpace_CountOne(self):
    #     set_text(self.view, '(foo   bar) baz\n')
    #     r = self.R(8, 8)
    #     add_sel(self.view, r)

    #     reg = a_word(self.view, r.b)
    #     self.assertEqual('   bar', self.view.substr(reg))

########NEW FILE########
__FILENAME__ = test_keys
import unittest
from collections import namedtuple

import sublime

from Vintageous import state
from Vintageous.vi.utils import modes
from Vintageous.vi.utils import translate_char
from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import make_region
from Vintageous.tests import ViewTest
from Vintageous.tests import ViewTest
from Vintageous.vi.keys import to_bare_command_name
from Vintageous.vi.keys import KeySequenceTokenizer
from Vintageous.vi.keys import seqs


_tests_tokenizer = (
    ('p',            'p',            'lower letter key'),
    ('P',            'P',            'upper case letter key'),
    ('<C-p>',        '<C-p>',        'ctrl-modified lower case letter key'),
    ('<C-P>',        '<C-P>',        'ctrl-modified upper case letter key'),
    ('<C-S-.>',      '<C-S-.>',      'ctrl-shift modified period key'),
    ('<Esc>',        '<esc>',        'esc key title case'),
    ('<esc>',        '<esc>',        'esc key lowercase'),
    ('<eSc>',        '<esc>',        'esc key mixed case'),
    ('<lt>',         '<lt>',         'less than key'),
    ('<HOME>',       '<home>',       'less than key'),
    ('<enD>',        '<end>',        'less than key'),
    ('<uP>',         '<up>',         'less than key'),
    ('<DoWn>',       '<down>',       'less than key'),
    ('<left>',       '<left>',       'less than key'),
    ('<RigHt>',      '<right>',      'less than key'),
    ('<Space>',      '<space>',      'space key'),
    ('<c-Space>',    '<C-space>',    'ctrl-space key'),
    ('0',            '0',            'zero key'),
    ('<c-m-.>',      '<C-M-.>',      'ctrl-alt-period key'),
    ('<tab>',        '<tab>',        'tab key'),
)


class Test_KeySequenceTokenizer_tokenize_one(ViewTest):
    def parse(self, input_):
        tokenizer = KeySequenceTokenizer(input_)
        return tokenizer.tokenize_one()

    def testAll(self):
        for (i, t) in enumerate(_tests_tokenizer):
            input_, expected, msg = t
            self.assertEqual(self.parse(input_), expected, "{0} - {1}".format(i, msg))


_tests_iter_tokenize = (
    ('pp',         ['p', 'p'],                     'sequence'),
    ('<C-p>',      ['<C-p>'],                      'sequence'),
    ('<C-P>x',     ['<C-P>', 'x'],                 'sequence'),
    ('<C-S-.>',    ['<C-S-.>'],                    'sequence'),
    ('<Esc>ai',    ['<esc>', 'a', 'i'],            'sequence'),
    ('<lt><lt>',   ['<lt>', '<lt>'],               'sequence'),
    ('<DoWn>abc.', ['<down>', 'a', 'b', 'c', '.'], 'sequence'),
    ('0<down>',    ['0', '<down>'],                'sequence'),
    ('<c-m-.>',    ['<C-M-.>'],                    'sequence'),
)


class Test_KeySequenceTokenizer_iter_tokenize(ViewTest):
    def parse(self, input_):
        tokenizer = KeySequenceTokenizer(input_)
        return list(tokenizer.iter_tokenize())

    def testAll(self):
        for (i, t) in enumerate(_tests_iter_tokenize):
            input_, expected, msg = t
            self.assertEqual(self.parse(input_), expected, "{0} - {1}".format(i, msg))


_command_name_tests = (
    ('daw', 'daw', ''),
    ('2daw', 'daw', ''),
    ('d2aw', 'daw', ''),
    ('2d2aw', 'daw', ''),
    ('"a2d2aw', 'daw', ''),
    ('"12d2aw', 'daw', ''),
    ('<f7>', '<f7>', ''),
    ('10<f7>', '<f7>', ''),
    ('"a10<f7>', '<f7>', ''),
    ('"a10<f7>', '<f7>', ''),
    ('"210<f7>', '<f7>', ''),
    ('0', '0', ''),
)


class Test_to_bare_command_name(ViewTest):
    def transform(self, input_):
        return to_bare_command_name(input_)

    def testAll(self):
        for (i, t) in enumerate(_command_name_tests):
            input_, expected, msg = t
            self.assertEqual(self.transform(input_), expected, "{0} - {1}".format(i, msg))


_tranlation_tests = (
    ('<enter>', '\n', ''),
    ('<cr>', '\n', ''),
    ('<sp>', ' ', ''),
    ('<space>', ' ', ''),
    ('<lt>', '<', ''),
    ('a', 'a', ''),
)


class Test_translate_char(ViewTest):
    def testAll(self):
        for (i, t) in enumerate(_tranlation_tests):
            input_, expected, msg = t
            self.assertEqual(translate_char(input_), expected, "{0} - {1}".format(i, msg))


seq_test = namedtuple('seq_test', 'actual expected')


TESTS_KNOWN_SEQUENCES = (
    seq_test(actual=seqs.A,          expected='a'),
    seq_test(actual=seqs.ALT_CTRL_P, expected='<C-M-p>'),
    seq_test(actual=seqs.AMPERSAND , expected='&'),
    seq_test(actual=seqs.AW,         expected='aw'),
    seq_test(actual=seqs.B,          expected='b'),
    seq_test(actual=seqs.BACKSPACE,  expected='<bs>'),
    seq_test(actual=seqs.GE,         expected='ge'),
    seq_test(actual=seqs.G_BIG_E,    expected='gE'),
    seq_test(actual=seqs.UP,         expected='<up>'),
    seq_test(actual=seqs.DOWN,       expected='<down>'),
    seq_test(actual=seqs.LEFT,       expected='<left>'),
    seq_test(actual=seqs.RIGHT,      expected='<right>'),
    seq_test(actual=seqs.HOME,       expected='<home>'),
    seq_test(actual=seqs.END,        expected='<end>'),
    seq_test(actual=seqs.BACKTICK,   expected='`'),
    seq_test(actual=seqs.BIG_A,      expected='A'),
    seq_test(actual=seqs.SPACE,      expected='<space>'),
    seq_test(actual=seqs.BIG_B,      expected='B'),
    seq_test(actual=seqs.CTRL_E,     expected='<C-e>'),
    seq_test(actual=seqs.CTRL_Y,     expected='<C-y>'),
    seq_test(actual=seqs.BIG_C,      expected='C'),
    seq_test(actual=seqs.BIG_D,      expected='D'),
    seq_test(actual=seqs.GH,         expected='gh'),
    seq_test(actual=seqs.G_BIG_H,    expected='gH'),
    seq_test(actual=seqs.BIG_E,      expected='E'),
    seq_test(actual=seqs.BIG_F,      expected='F'),
    seq_test(actual=seqs.BIG_G,      expected='G'),
    seq_test(actual=seqs.CTRL_W,     expected='<C-w>'),
    seq_test(actual=seqs.CTRL_W_Q,   expected='<C-w>q'),

    seq_test(actual=seqs.CTRL_W_V,        expected='<C-w>v'),
    seq_test(actual=seqs.CTRL_W_L,        expected='<C-w>l'),
    seq_test(actual=seqs.CTRL_W_BIG_L,    expected='<C-w>L'),
    seq_test(actual=seqs.CTRL_K,          expected='<C-k>'),
    seq_test(actual=seqs.CTRL_K_CTRL_B,   expected='<C-k><C-b>'),
    seq_test(actual=seqs.CTRL_BIG_F,      expected='<C-F>'),
    seq_test(actual=seqs.CTRL_BIG_P,      expected='<C-P>'),
    seq_test(actual=seqs.CTRL_W_H,        expected='<C-w>h'),
    seq_test(actual=seqs.Q,               expected='q'),
    seq_test(actual=seqs.AT,              expected='@'),
    seq_test(actual=seqs.CTRL_W_BIG_H,    expected='<C-w>H'),
    seq_test(actual=seqs.BIG_H,           expected='H'),

    seq_test(actual=seqs.G_BIG_J,         expected='gJ'),
    seq_test(actual=seqs.CTRL_R,          expected='<C-r>'),
    seq_test(actual=seqs.CTRL_R_EQUAL,    expected='<C-r>='),
    seq_test(actual=seqs.CTRL_A,          expected='<C-a>'),
    seq_test(actual=seqs.CTRL_I,          expected='<C-i>'),
    seq_test(actual=seqs.CTRL_O,          expected='<C-o>'),
    seq_test(actual=seqs.CTRL_X,          expected='<C-x>'),
    seq_test(actual=seqs.CTRL_X_CTRL_L,   expected='<C-x><C-l>'),
    seq_test(actual=seqs.Z,               expected='z'),
    seq_test(actual=seqs.Z_ENTER,         expected='z<cr>'),
    seq_test(actual=seqs.ZT,              expected='zt'),
    seq_test(actual=seqs.ZZ,              expected='zz'),
    seq_test(actual=seqs.Z_MINUS,         expected='z-'),
    seq_test(actual=seqs.ZB,              expected='zb'),

    seq_test(actual=seqs.BIG_I,                expected='I'),
    seq_test(actual=seqs.BIG_Z_BIG_Z,          expected='ZZ'),
    seq_test(actual=seqs.BIG_Z_BIG_Q,          expected='ZQ'),
    seq_test(actual=seqs.GV,                   expected='gv'),
    seq_test(actual=seqs.BIG_J,                expected='J'),
    seq_test(actual=seqs.BIG_K,                expected='K'),
    seq_test(actual=seqs.BIG_L,                expected='L'),
    seq_test(actual=seqs.BIG_M,                expected='M'),
    seq_test(actual=seqs.BIG_N,                expected='N'),
    seq_test(actual=seqs.BIG_O,                expected='O'),
    seq_test(actual=seqs.BIG_P,                expected='P'),
    seq_test(actual=seqs.BIG_Q,                expected='Q'),
    seq_test(actual=seqs.BIG_R,                expected='R'),
    seq_test(actual=seqs.BIG_S,                expected='S'),
    seq_test(actual=seqs.BIG_T,                expected='T'),
    seq_test(actual=seqs.BIG_U,                expected='U'),
    seq_test(actual=seqs.BIG_V,                expected='V'),
    seq_test(actual=seqs.BIG_W,                expected='W'),
    seq_test(actual=seqs.BIG_X,                expected='X'),
    seq_test(actual=seqs.BIG_Y,                expected='Y'),
    seq_test(actual=seqs.BIG_Z,                expected='Z'),
    seq_test(actual=seqs.C,                    expected= 'c'),
    seq_test(actual=seqs.CC,                   expected='cc'),
    seq_test(actual=seqs.COLON,                expected=':'),
    seq_test(actual=seqs.COMMA,                expected=','),
    seq_test(actual=seqs.CTRL_D,               expected='<C-d>'),
    seq_test(actual=seqs.CTRL_F12,             expected='<C-f12>'),
    seq_test(actual=seqs.CTRL_L,               expected='<C-l>'),
    seq_test(actual=seqs.CTRL_B,               expected='<C-b>'),
    seq_test(actual=seqs.CTRL_F,               expected='<C-f>'),
    seq_test(actual=seqs.CTRL_G,               expected='<C-g>'),
    seq_test(actual=seqs.CTRL_P,               expected='<C-p>'),
    seq_test(actual=seqs.CTRL_U,               expected='<C-u>'),
    seq_test(actual=seqs.CTRL_V,               expected='<C-v>'),
    seq_test(actual=seqs.D,                    expected='d'),
    seq_test(actual=seqs.DD,                   expected='dd'),
    seq_test(actual=seqs.DOLLAR,               expected='$'),
    seq_test(actual=seqs.DOT,                  expected='.'),
    seq_test(actual=seqs.DOUBLE_QUOTE,         expected='"'),
    seq_test(actual=seqs.E,                    expected='e'),
    seq_test(actual=seqs.ENTER,                expected='<cr>'),
    seq_test(actual=seqs.SHIFT_ENTER,          expected='<S-cr>'),
    seq_test(actual=seqs.EQUAL,                expected='='),
    seq_test(actual=seqs.EQUAL_EQUAL,          expected='=='),
    seq_test(actual=seqs.ESC,                  expected='<esc>'),
    seq_test(actual=seqs.F,                    expected='f'),
    seq_test(actual=seqs.F1,                   expected='<f1>'),
    seq_test(actual=seqs.F10,                  expected='<f10>'),
    seq_test(actual=seqs.F11,                  expected='<f11>'),
    seq_test(actual=seqs.F12,                  expected='<f12>'),
    seq_test(actual=seqs.F13,                  expected='<f13>'),
    seq_test(actual=seqs.F14,                  expected='<f14>'),
    seq_test(actual=seqs.F15,                  expected='<f15>'),
    seq_test(actual=seqs.F2,                   expected='<f2>'),
    seq_test(actual=seqs.F3,                   expected='<f3>'),
    seq_test(actual=seqs.SHIFT_F2,             expected='<S-f2>'),
    seq_test(actual=seqs.SHIFT_F3,             expected='<S-f3>'),
    seq_test(actual=seqs.SHIFT_F4,             expected='<S-f4>'),
    seq_test(actual=seqs.F4,                   expected='<f4>'),
    seq_test(actual=seqs.F5,                   expected='<f5>'),
    seq_test(actual=seqs.F6,                   expected='<f6>'),
    seq_test(actual=seqs.F7,                   expected='<f7>'),
    seq_test(actual=seqs.F8,                   expected='<f8>'),
    seq_test(actual=seqs.F9,                   expected='<f9>'),
    seq_test(actual=seqs.CTRL_F2,              expected='<C-f2>'),
    seq_test(actual=seqs.CTRL_SHIFT_F2,        expected='<C-S-f2>'),
    seq_test(actual=seqs.G,                    expected='g'),
    seq_test(actual=seqs.G_BIG_D,              expected='gD'),
    seq_test(actual=seqs.G_BIG_U,              expected='gU'),
    seq_test(actual=seqs.G_BIG_U_BIG_U,        expected='gUU'),
    seq_test(actual=seqs.G_BIG_U_G_BIG_U,      expected='gUgU'),
    seq_test(actual=seqs.G_TILDE,              expected='g~'),
    seq_test(actual=seqs.G_TILDE_G_TILDE,      expected='g~g~'),
    seq_test(actual=seqs.G_TILDE_TILDE,        expected='g~~'),
    seq_test(actual=seqs.G_UNDERSCORE,         expected='g_'),
    seq_test(actual=seqs.GD,                   expected='gd'),
    seq_test(actual=seqs.GG,                   expected='gg'),
    seq_test(actual=seqs.GJ,                   expected='gj'),
    seq_test(actual=seqs.GK,                   expected='gk'),
    seq_test(actual=seqs.GQ,                   expected='gq'),
    seq_test(actual=seqs.GT,                   expected='gt'),
    seq_test(actual=seqs.G_BIG_T,              expected= 'gT'),
    seq_test(actual=seqs.GM,                   expected= 'gm'),
    seq_test(actual=seqs.GU,                   expected= 'gu'),
    seq_test(actual=seqs.GUGU,                 expected= 'gugu'),
    seq_test(actual=seqs.GUU,                  expected= 'guu'),
    seq_test(actual=seqs.GREATER_THAN,         expected= '>'),
    seq_test(actual=seqs.GREATER_THAN_GREATER_THAN, expected= '>>'),
    seq_test(actual=seqs.H,                      expected= 'h'),
    seq_test(actual=seqs.HAT,                    expected= '^'),
    seq_test(actual=seqs.I,                      expected= 'i'),
    seq_test(actual=seqs.J,                      expected= 'j'),
    seq_test(actual=seqs.K,                      expected= 'k'),
    seq_test(actual=seqs.L,                      expected= 'l'),
    seq_test(actual=seqs.LEFT_BRACE,             expected= '{'),
    seq_test(actual=seqs.LEFT_SQUARE_BRACKET,    expected= '['),
    seq_test(actual=seqs.LEFT_PAREN,             expected= '('),
    seq_test(actual=seqs.LESS_THAN,              expected= '<lt>'),
    seq_test(actual=seqs.LESS_THAN_LESS_THAN,    expected= '<lt><lt>'),
    seq_test(actual=seqs.M,                      expected= 'm'),
    seq_test(actual=seqs.N,                      expected= 'n'),
    seq_test(actual=seqs.O,                      expected= 'o'),
    seq_test(actual=seqs.P,                      expected= 'p'),
    seq_test(actual=seqs.OCTOTHORP,              expected= '#'),
    seq_test(actual=seqs.PAGE_DOWN,              expected= 'pagedown'),
    seq_test(actual=seqs.PAGE_UP,                expected= 'pageup'),
    seq_test(actual=seqs.PERCENT,                expected= '%'),
    seq_test(actual=seqs.PIPE,                   expected= '|'),
    seq_test(actual=seqs.QUESTION_MARK,          expected= '?'),
    seq_test(actual=seqs.QUOTE,                  expected= "'"),
    seq_test(actual=seqs.QUOTE_QUOTE,            expected= "''"),
    seq_test(actual=seqs.R,                      expected= 'r'),
    seq_test(actual=seqs.RIGHT_BRACE,            expected= '}'),
    seq_test(actual=seqs.RIGHT_SQUARE_BRACKET,   expected= ']'),
    seq_test(actual=seqs.RIGHT_PAREN,            expected= ')'),
    seq_test(actual=seqs.S,                      expected= 's'),
    seq_test(actual=seqs.SEMICOLON,              expected= ';'),
    seq_test(actual=seqs.SHIFT_CTRL_F12,         expected= '<C-S-f12>'),
    seq_test(actual=seqs.SLASH,                  expected= '/'),
    seq_test(actual=seqs.STAR,                   expected= '*'),
    seq_test(actual=seqs.T,                      expected= 't'),
    seq_test(actual=seqs.TAB,                    expected= '<tab>'),
    seq_test(actual=seqs.TILDE,                  expected='~'),
    seq_test(actual=seqs.U,                      expected='u'),
    seq_test(actual=seqs.UNDERSCORE,             expected='_'),
    seq_test(actual=seqs.V,                      expected='v'),
    seq_test(actual=seqs.W,                      expected='w'),
    seq_test(actual=seqs.X,                      expected='x'),
    seq_test(actual=seqs.Y,                      expected='y'),
    seq_test(actual=seqs.YY,                     expected='yy'),
    seq_test(actual=seqs.ZERO,                   expected='0'),
)


class Test_KeySequenceNames(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS_KNOWN_SEQUENCES):
            self.assertEqual(data.actual, data.expected,
                             "failed at index {0}".format(i))

    def testAllKeySequenceNamesAreTested(self):
        tested_seqs = [k.actual for k in TESTS_KNOWN_SEQUENCES]
        self.assertEqual(sorted(tested_seqs),
                         sorted([v for (k, v) in seqs.__dict__.items()
                                if k.isupper()]))

########NEW FILE########
__FILENAME__ = test_mappings
import unittest

import sublime

from Vintageous.state import State
from Vintageous.vi.utils import modes
from Vintageous.vi.mappings import Mappings
from Vintageous.vi.mappings import _mappings
from Vintageous.vi.mappings import mapping_status
from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import make_region
from Vintageous.tests import ViewTest
from Vintageous.vi.cmd_base import cmd_types


adding_tests = (
    (modes.NORMAL,               'G', 'G_', 'adding to normal mode'),
    (modes.VISUAL,               'G', 'G_', 'adding to visual mode'),
    (modes.OPERATOR_PENDING,     'G', 'G_', 'adding to operator pending mode'),
    (modes.VISUAL_LINE,          'G', 'G_', 'adding to visual line mode'),
    (modes.VISUAL_BLOCK,         'G', 'G_', 'adding to visual block mode'),
)


class Test_Mappings_AddingAndRemoving(ViewTest):
    def setUp(self):
        super().setUp()
        self.mappings = Mappings(self.state)
        self.mappings.clear()

    def testCanAdd(self):
        for (i, data) in enumerate(adding_tests):
            mode, keys, target, msg = data
            self.mappings.add(mode, keys, target)
            self.assertEqual(_mappings[mode][keys], {'name': target, 'type': cmd_types.USER}, '{0} [{1}] failed'.format(msg, i))
            self.mappings.clear()

    def testCanRemove(self):
        for (i, data) in enumerate(adding_tests):
            mode, keys, target, msg = data
            self.mappings.add(mode, keys, target)
            self.mappings.remove(mode, keys)

        self.assertFalse(_mappings[modes.NORMAL])
        self.assertFalse(_mappings[modes.VISUAL])
        self.assertFalse(_mappings[modes.VISUAL_LINE])
        self.assertFalse(_mappings[modes.VISUAL_BLOCK])


expanding_tests = (
    ((modes.NORMAL, 'G',     'G_'),     ('G',      'G',     'G_',   '',   'G',      mapping_status.COMPLETE)),
    ((modes.NORMAL, '<C-m>', 'daw'),    ('<C-m>',  '<C-m>', 'daw',  '',   '<C-m>',  mapping_status.COMPLETE)),
    ((modes.NORMAL, '<C-m>', 'daw'),    ('<C-m>x', '<C-m>', 'daw',  'x',  '<C-m>x', mapping_status.COMPLETE)),
    ((modes.NORMAL, 'xxA',   'daw'),    ('xx',     'xx',    '',     '',   'xx',     mapping_status.INCOMPLETE)),
)


class Test_Mapping_Expanding(ViewTest):
    def setUp(self):
        super().setUp()
        self.mappings = Mappings(self.state)
        self.mappings.clear()

    def testCanExpand(self):
        for (i, data) in enumerate(expanding_tests):
            setup_data, test_data = data

            mode, keys, new_mapping = setup_data
            self.mappings.add(mode, keys, new_mapping)

            self.state.mode = modes.NORMAL

            seq, expected_head, expected_mapping, expected_tail, expected_full, expected_status = test_data
            result = self.mappings.expand_first(seq)

            self.assertEqual(result.head, expected_head, '[{0}] head failed'.format(i))
            self.assertEqual(result.tail, expected_tail, '[{0}] tail failed'.format(i))
            self.assertEqual(result.mapping, expected_mapping, '[{0}] mapping failed'.format(i))
            self.assertEqual(result.sequence, expected_full, '[{0}] sequence failed'.format(i))
            self.assertEqual(result.status, expected_status, '[{0}] status failed'.format(i))

            self.mappings.clear()

########NEW FILE########
__FILENAME__ = test_marks
import unittest

import sublime

from Vintageous.tests import ViewTest
from Vintageous.vi import marks
from Vintageous.state import State
from Vintageous.tests import make_region
from Vintageous.tests import set_text
from Vintageous.tests import add_sel


# XXX: Use the mock module instead?
##################################################
class View(object):
    def __init__(self, id_, fname, buffer_id=0):
        self.view_id = id_
        self.fname = fname
        self._buffer_id = buffer_id

    def file_name(self):
        return self.fname

    def buffer_id(self):
        return self._buffer_id

class Window(object):
    pass
##################################################


class MarksTests(ViewTest):
    def setUp(self):
        super().setUp()
        marks._MARKS = {}
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0, 0))
        self.marks = State(self.view).marks

    def testCanSetMark(self):
        self.marks.add('a', self.view)
        expected_win, expected_view, expected_region = (self.view.window(), self.view, (0, 0))
        actual_win, actual_view, actual_region = marks._MARKS['a']
        self.assertEqual((actual_win.id(), actual_view.view_id, actual_region),
                         (expected_win.id(), expected_view.view_id, expected_region))

    def testCanRetrieveMarkInTheCurrentBufferAsTuple(self):
        self.marks.add('a', self.view)
        # The caret's at the beginning of the buffer.
        self.assertEqual(self.marks.get_as_encoded_address('a'), sublime.Region(0, 0))

    def testCanRetrieveMarkInTheCurrentBufferAsTuple2(self):
        set_text(self.view, ''.join(('foo bar\n') * 10))
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(30, 30))
        self.marks.add('a', self.view)
        self.assertEqual(self.marks.get_as_encoded_address('a'), sublime.Region(24, 24))

    def testCanRetrieveMarkInADifferentBufferAsEncodedMark(self):
        view = View(id_=self.view.view_id + 1, fname=r'C:\foo.txt')

        marks._MARKS['a'] = (Window(), view, (0, 0))
        expected = "{0}:{1}".format(r'C:\foo.txt', "0:0")
        self.assertEqual(self.marks.get_as_encoded_address('a'), expected)

    def testCanRetrieveMarkInAnUntitledBufferAsEncodedMark(self):
        view = View(id_=self.view.view_id + 1, fname='', buffer_id=999)

        marks._MARKS['a'] = (Window(), view, (0, 0))
        expected = "<untitled {0}>:{1}".format(999, "0:0")
        self.assertEqual(self.marks.get_as_encoded_address('a'), expected)

    def testCanRetrieveSingleQuoteMark(self):
        location = self.marks.get_as_encoded_address("'")
        self.assertEqual(location, '<command _vi_double_single_quote>')

########NEW FILE########
__FILENAME__ = test_move_by_word_ends
import unittest
from collections import namedtuple

import sublime

from Vintageous.vi.units import word_ends
from Vintageous.vi.utils import modes
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content args kwargs expected msg')

R = sublime.Region


TESTS = (
    test_data(content='cat dog bee', args=(0,), kwargs={}, expected=3, msg="find current word's end"),
    test_data(content='  cat dog bee', args=(0,), kwargs={}, expected=5, msg="find current word's end from white space"),
    test_data(content='a dog bee', args=(0,), kwargs={}, expected=5, msg="find next word's end from 1-char word"),
    test_data(content='a. dog bee', args=(0,), kwargs={}, expected=2, msg="find next word's end in contiguous punctuation"),

    test_data(content='cat dog bees', args=(0,), kwargs={'count': 3}, expected=12, msg="find current word's end (count: 3)"),
    test_data(content='a dog bees', args=(0,), kwargs={'count': 3}, expected=10, msg="find next word's end from 1-char word (count: 3)"),
    test_data(content='a. dog bees', args=(0,), kwargs={'count': 3}, expected=11, msg="find next word's end in contiguous punctuation (count: 3)"),
    test_data(content='a.dog bee', args=(0,), kwargs={}, expected=2, msg="find next word's end in interspersed punctuation"),
)

TESTS_BIG = (
    test_data(content='cat dog bee', args=(0,), kwargs={'big': True}, expected=3, msg="find current word's end"),
    test_data(content='  cat dog bee', args=(0,), kwargs={}, expected=5, msg="find current word's end from white space"),
    test_data(content='a dog bee', args=(0,), kwargs={'big': True}, expected=5, msg="find next word's end from 1-char word"),
    test_data(content='a. dog bee', args=(0,), kwargs={'big': True}, expected=2, msg="find next word's end in contiguous punctuation"),

    test_data(content='cat dog bees', args=(0,), kwargs={'big': True, 'count': 3}, expected=12, msg="find current word's end (count: 3)"),
    test_data(content='a dog bees', args=(0,), kwargs={'big': True, 'count': 3}, expected=10, msg="find next word's end from 1-char word (count: 3)"),
    test_data(content='a. dog bee ants', args=(0,), kwargs={'big': True, 'count': 3}, expected=10, msg="find next word's end in contiguous punctuation (count: 3)"),
    test_data(content='a. (dog) bee, ants', args=(0,), kwargs={'big': True, 'count': 3}, expected=13, msg="find next word's skipping over many punctuation signs (count: 3)"),
)


class Test_WordEnds(ViewTest):
    def test_word_ends(self):
        for (i, data) in enumerate(TESTS):
            self.write(data.content)
            actual = word_ends(self.view, *data.args, **data.kwargs)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

    def test_big_word_ends(self):
        for (i, data) in enumerate(TESTS_BIG):
            self.write(data.content)
            actual = word_ends(self.view, *data.args, **data.kwargs)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test_registers
import unittest
import builtins

import sublime

from unittest import mock
from Vintageous.vi import registers
from Vintageous.vi.registers import Registers
from Vintageous.vi.settings import SettingsManager
from Vintageous.state import State
from Vintageous.tests import ViewTest


class TestCaseRegistersConstants(unittest.TestCase):
    def testUnnamedConstantValue(self):
        self.assertEqual(registers.REG_UNNAMED, '"')

    def testSmallDeleteConstantValue(self):
        self.assertEqual(registers.REG_SMALL_DELETE, '-')

    def testBlackHoleConstantValue(self):
        self.assertEqual(registers.REG_BLACK_HOLE, '_')

    def testLastInsertedTextConstantValue(self):
        self.assertEqual(registers.REG_LAST_INSERTED_TEXT, '.')

    def testFileNameConstantValue(self):
        self.assertEqual(registers.REG_FILE_NAME, '%')

    def testAltFileNameConstantValue(self):
        self.assertEqual(registers.REG_ALT_FILE_NAME, '#')

    def testExpressionConstantValue(self):
        self.assertEqual(registers.REG_EXPRESSION, '=')

    def testSysClipboard1ConstantValue(self):
        self.assertEqual(registers.REG_SYS_CLIPBOARD_1, '*')

    def testSysClipboard2ConstantValue(self):
        self.assertEqual(registers.REG_SYS_CLIPBOARD_2, '+')

    def testSysClipboardAllConstantValue(self):
        self.assertEqual(registers.REG_SYS_CLIPBOARD_ALL,
                             (registers.REG_SYS_CLIPBOARD_1,
                              registers.REG_SYS_CLIPBOARD_2,))

    def testValidRegisterNamesConstantValue(self):
        names = tuple("{0}".format(c) for c in "abcdefghijklmnopqrstuvwxyz")
        self.assertEqual(registers.REG_VALID_NAMES, names)

    def testValidNumberNamesConstantValue(self):
        names = tuple("{0}".format(c) for c in "0123456789")
        self.assertEqual(registers.REG_VALID_NUMBERS, names)

    def testSysClipboardAllConstantValue(self):
        self.assertEqual(registers.REG_SPECIAL,
                             (registers.REG_UNNAMED,
                              registers.REG_SMALL_DELETE,
                              registers.REG_BLACK_HOLE,
                              registers.REG_LAST_INSERTED_TEXT,
                              registers.REG_FILE_NAME,
                              registers.REG_ALT_FILE_NAME,
                              registers.REG_SYS_CLIPBOARD_1,
                              registers.REG_SYS_CLIPBOARD_2,))

    def testAllConstantValue(self):
        self.assertEqual(registers.REG_ALL,
                            (registers.REG_SPECIAL +
                             registers.REG_VALID_NUMBERS +
                             registers.REG_VALID_NAMES))


class TestCaseRegisters(ViewTest):
    def setUp(self):
        super().setUp()
        sublime.set_clipboard('')
        registers._REGISTER_DATA = {}
        self.view.settings().erase('vintage')
        self.view.settings().erase('vintageous_use_sys_clipboard')
        # self.regs = Registers(view=self.view,
                              # settings=SettingsManager(view=self.view))
        self.regs = State(self.view).registers

    def testCanInitializeClass(self):
        self.assertEqual(self.regs.view, self.view)
        self.assertTrue(getattr(self.regs, 'settings'))

    def testCanSetUnanmedRegister(self):
        self.regs._set_default_register(["foo"])
        self.assertEqual(registers._REGISTER_DATA[registers.REG_UNNAMED],
                         ["foo"])

    def testSettingLongRegisterNameThrowsAssertionError(self):
        self.assertRaises(AssertionError, self.regs.set, "aa", "foo")

    def testSettingNonListValueThrowsAssertionError(self):
        self.assertRaises(AssertionError, self.regs.set, "a", "foo")

    @unittest.skip("Not implemented.")
    def testUnknownRegisterNameThrowsException(self):
        # XXX Doesn't pass at the moment.
        self.assertRaises(Exception, self.regs.set, "~", "foo")

    def testRegisterDataIsAlwaysStoredAsString(self):
        self.regs.set('"', [100])
        self.assertEqual(registers._REGISTER_DATA[registers.REG_UNNAMED],
                         ["100"])

    def testSettingBlackHoleRegisterDoesNothing(self):
        registers._REGISTER_DATA[registers.REG_UNNAMED] = ["bar"]
        # In this case it doesn't matter whether we're setting a list or not,
        # because we are discarding the value anyway.
        self.regs.set(registers.REG_BLACK_HOLE, "foo")
        self.assertTrue(registers.REG_BLACK_HOLE not in registers._REGISTER_DATA)
        self.assertTrue(registers._REGISTER_DATA[registers.REG_UNNAMED], ["bar"])

    def testSettingExpressionRegisterDoesntPopulateUnnamedRegister(self):
        self.regs.set("=", [100])
        self.assertTrue(registers.REG_UNNAMED not in registers._REGISTER_DATA)
        self.assertEqual(registers._REGISTER_DATA[registers.REG_EXPRESSION],
                        ["100"])

    def testCanSetNormalRegisters(self):
        for name in registers.REG_VALID_NAMES:
            self.regs.set(name, [name])

        for number in registers.REG_VALID_NUMBERS:
            self.regs.set(number, [number])

        for name in registers.REG_VALID_NAMES:
            self.assertEqual(registers._REGISTER_DATA[name], [name])

        for number in registers.REG_VALID_NUMBERS:
            self.assertEqual(registers._REGISTER_DATA[number], [number])

    def testSettingNormalRegisterSetsUnnamedRegisterToo(self):
        self.regs.set('a', [100])
        self.assertEqual(registers._REGISTER_DATA[registers.REG_UNNAMED], ['100'])

        self.regs.set('0', [200])
        self.assertEqual(registers._REGISTER_DATA[registers.REG_UNNAMED], ['200'])

    def testSettingRegisterSetsClipboardIfNeeded(self):
        self.regs.settings.view['vintageous_use_sys_clipboard'] = True
        self.regs.set('a', [100])
        self.assertEqual(sublime.get_clipboard(), '100')

    def testCanAppendToSingleValue(self):
        self.regs.set('a', ['foo'])
        self.regs.append_to('A', ['bar'])
        self.assertEqual(registers._REGISTER_DATA['a'], ['foobar'])

    def testCanAppendToMultipleBalancedValues(self):
        self.regs.set('a', ['foo', 'bar'])
        self.regs.append_to('A', ['fizz', 'buzz'])
        self.assertEqual(registers._REGISTER_DATA['a'], ['foofizz', 'barbuzz'])

    def testCanAppendToMultipleValuesMoreExistingValues(self):
        self.regs.set('a', ['foo', 'bar'])
        self.regs.append_to('A', ['fizz'])
        self.assertEqual(registers._REGISTER_DATA['a'], ['foofizz', 'bar'])

    def testCanAppendToMultipleValuesMoreNewValues(self):
        self.regs.set('a', ['foo'])
        self.regs.append_to('A', ['fizz', 'buzz'])
        self.assertEqual(registers._REGISTER_DATA['a'], ['foofizz', 'buzz'])

    def testAppendingSetsDefaultRegister(self):
        self.regs.set('a', ['foo'])
        self.regs.append_to('A', ['bar'])
        self.assertEqual(registers._REGISTER_DATA[registers.REG_UNNAMED],
                         ['foobar'])

    def testAppendSetsClipboardIfNeeded(self):
        self.regs.settings.view['vintageous_use_sys_clipboard'] = True
        self.regs.set('a', ['foo'])
        self.regs.append_to('A', ['bar'])
        self.assertEqual(sublime.get_clipboard(), 'foobar')

    def testGetDefaultToUnnamedRegister(self):
        registers._REGISTER_DATA['"'] = ['foo']
        self.view.settings().set('vintageous_use_sys_clipboard', False)
        self.assertEqual(self.regs.get(), ['foo'])

    def testGettingBlackHoleRegisterReturnsNone(self):
        self.assertEqual(self.regs.get(registers.REG_BLACK_HOLE), None)

    def testCanGetFileNameRegister(self):
        fname = self.regs.get(registers.REG_FILE_NAME)
        self.assertEqual(fname, [self.view.file_name()])

    def testCanGetClipboardRegisters(self):
        self.regs.set(registers.REG_SYS_CLIPBOARD_1, ['foo'])
        self.assertEqual(self.regs.get(registers.REG_SYS_CLIPBOARD_1), ['foo'])
        self.assertEqual(self.regs.get(registers.REG_SYS_CLIPBOARD_2), ['foo'])

        self.regs.set(registers.REG_SYS_CLIPBOARD_2, ['bar'])
        self.assertEqual(self.regs.get(registers.REG_SYS_CLIPBOARD_1), ['bar'])
        self.assertEqual(self.regs.get(registers.REG_SYS_CLIPBOARD_2), ['bar'])

    def testGetSysClipboardAlwaysIfRequested(self):
        self.regs.settings.view['vintageous_use_sys_clipboard'] = True
        sublime.set_clipboard('foo')
        self.assertEqual(self.regs.get(), ['foo'])

    def testGettingExpressionRegisterClearsExpressionRegister(self):
        registers._REGISTER_DATA[registers.REG_EXPRESSION] = ['100']
        self.view.settings().set('vintageous_use_sys_clipboard', False)
        self.assertEqual(self.regs.get(), ['100'])
        self.assertEqual(registers._REGISTER_DATA[registers.REG_EXPRESSION], '')

    def testCanGetNumberRegister(self):
        registers._REGISTER_DATA['5'] = ['foo']
        self.assertEqual(self.regs.get('5'), ['foo'])

    def testCanGetRegisterEvenIfRequestingItThroughACapitalLetter(self):
        registers._REGISTER_DATA['a'] = ['foo']
        self.assertEqual(self.regs.get('A'), ['foo'])

    def testCanGetRegistersWithDictSyntax(self):
        registers._REGISTER_DATA['a'] = ['foo']
        self.assertEqual(self.regs.get('a'), self.regs['a'])

    def testCanSetRegistersWithDictSyntax(self):
        self.regs['a'] = ['100']
        self.assertEqual(self.regs['a'], ['100'])

    def testCanAppendToRegisteWithDictSyntax(self):
        self.regs['a'] = ['100']
        self.regs['A'] = ['100']
        self.assertEqual(self.regs['a'], ['100100'])

    def testCanConvertToDict(self):
        self.regs['a'] = ['100']
        self.regs['b'] = ['200']
        values = {name: self.regs.get(name) for name in registers.REG_ALL}
        values.update({'a': ['100'], 'b': ['200']})
        self.assertEqual(self.regs.to_dict(), values)

    def testGettingEmptyRegisterReturnsNone(self):
        self.assertEqual(self.regs.get('a'), None)

    def testCanSetSmallDeleteRegister(self):
        self.regs[registers.REG_SMALL_DELETE] = ['foo']
        self.assertEqual(registers._REGISTER_DATA[registers.REG_SMALL_DELETE], ['foo'])

    def testCanGetSmallDeleteRegister(self):
        registers._REGISTER_DATA[registers.REG_SMALL_DELETE] = ['foo']
        self.assertEqual(self.regs.get(registers.REG_SMALL_DELETE), ['foo'])


class Test_get_selected_text(ViewTest):
    def setUp(self):
        super().setUp()
        sublime.set_clipboard('')
        registers._REGISTER_DATA = {}
        self.view.settings().erase('vintage')
        self.view.settings().erase('vintageous_use_sys_clipboard')
        self.regs = State(self.view).registers
        self.regs.view = mock.Mock()

    def testExtractsSubstrings(self):
        self.regs.view.sel.return_value = [10, 20, 30]

        class vi_cmd_data:
            _synthetize_new_line_at_eof = False
            _yanks_linewise = False

        self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(self.regs.view.substr.call_count, 3)

    def testReturnsFragments(self):
        self.regs.view.sel.return_value = [10, 20, 30]
        self.regs.view.substr.side_effect = lambda x: x

        class vi_cmd_data:
            _synthetize_new_line_at_eof = False
            _yanks_linewise = False

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, [10, 20, 30])

    def testCanSynthetizeNewLineAtEof(self):
        self.regs.view.substr.return_value = "AAA"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]
        self.regs.view.size.return_value = 0

        class vi_cmd_data:
            _synthetize_new_line_at_eof = True
            _yanks_linewise = False

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["AAA", "AAA\n"])

    def testDoesntSynthetizeNewLineAtEofIfNotNeeded(self):
        self.regs.view.substr.return_value = "AAA\n"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]
        self.regs.view.size.return_value = 0

        class vi_cmd_data:
            _synthetize_new_line_at_eof = True
            _yanks_linewise = False

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["AAA\n", "AAA\n"])

    def testDoesntSynthetizeNewLineAtEofIfNotAtEof(self):
        self.regs.view.substr.return_value = "AAA"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]
        self.regs.view.size.return_value = 100

        class vi_cmd_data:
            _synthetize_new_line_at_eof = True
            _yanks_linewise = False

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["AAA", "AAA"])

    def testCanYankLinewise(self):
        self.regs.view.substr.return_value = "AAA"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]

        class vi_cmd_data:
            _synthetize_new_line_at_eof = False
            _yanks_linewise = True

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["AAA\n", "AAA\n"])

    def testDoesNotYankLinewiseIfNonEmptyStringFollowedByNewLine(self):
        self.regs.view.substr.return_value = "AAA\n"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]

        class vi_cmd_data:
            _synthetize_new_line_at_eof = False
            _yanks_linewise = True

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["AAA\n", "AAA\n"])

    def testYankLinewiseIfEmptyStringFollowedByNewLine(self):
        self.regs.view.substr.return_value = "\n"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]

        class vi_cmd_data:
            _synthetize_new_line_at_eof = False
            _yanks_linewise = True

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["\n\n", "\n\n"])

    def testYankLinewiseIfTwoTrailingNewLines(self):
        self.regs.view.substr.return_value = "\n\n"
        self.regs.view.sel.return_value = [sublime.Region(10, 10), sublime.Region(10, 10)]

        class vi_cmd_data:
            _synthetize_new_line_at_eof = False
            _yanks_linewise = True

        rv = self.regs.get_selected_text(vi_cmd_data)
        self.assertEqual(rv, ["\n\n\n", "\n\n\n"])


class Test_yank(ViewTest):
    def setUp(self):
        super().setUp()
        sublime.set_clipboard('')
        registers._REGISTER_DATA = {}
        self.view.settings().erase('vintage')
        self.view.settings().erase('vintageous_use_sys_clipboard')
        self.regs = State(self.view).registers
        self.regs.view = mock.Mock()

    def testDontYankIfWeDontHaveTo(self):
        class vi_cmd_data:
            _can_yank = False
            _populates_small_delete_register = False

        self.regs.yank(vi_cmd_data)
        self.assertEqual(registers._REGISTER_DATA, {})

    def testYanksToUnnamedRegisterIfNoRegisterNameProvided(self):
        class vi_cmd_data:
            _can_yank = True
            _synthetize_new_line_at_eof = False
            _yanks_linewise = True
            register = None
            _populates_small_delete_register = False

        with mock.patch.object(self.regs, 'get_selected_text') as gst:
            gst.return_value = ['foo']
            self.regs.yank(vi_cmd_data)
            self.assertEqual(registers._REGISTER_DATA, {'"': ['foo']})

    def testYanksToRegisters(self):
        class vi_cmd_data:
            _can_yank = True
            _populates_small_delete_register = False

        with mock.patch.object(self.regs, 'get_selected_text') as gst:
            gst.return_value = ['foo']
            self.regs.yank(vi_cmd_data, register='a')
            self.assertEqual(registers._REGISTER_DATA, {'"': ['foo'], 'a': ['foo']})

    def testCanPopulateSmallDeleteRegister(self):
        class vi_cmd_data:
            _can_yank = True
            _populates_small_delete_register = True

        with mock.patch.object(builtins, 'all') as a, \
             mock.patch.object(self.regs, 'get_selected_text') as gst:
                gst.return_value = ['foo']
                self.regs.view.sel.return_value = range(1)
                a.return_value = True
                self.regs.yank(vi_cmd_data)
                self.assertEqual(registers._REGISTER_DATA, {'"': ['foo'], '-': ['foo']})

    def testDoesNotPopulateSmallDeleteRegisterIfWeShouldNot(self):
        class vi_cmd_data:
            _can_yank = False
            _populates_small_delete_register = False

        with mock.patch.object(builtins, 'all') as a, \
             mock.patch.object(self.regs, 'get_selected_text') as gst:
                gst.return_value = ['foo']
                self.regs.view.sel.return_value = range(1)
                a.return_value = False
                self.regs.yank(vi_cmd_data)
                self.assertEqual(registers._REGISTER_DATA, {})


########NEW FILE########
__FILENAME__ = test_settings
import unittest

from Vintageous.tests import ViewTest
from Vintageous.vi.settings import SettingsManager
from Vintageous.vi.settings import SublimeSettings
from Vintageous.vi.settings import VI_OPTIONS
from Vintageous.vi.settings import vi_user_setting
from Vintageous.vi.settings import VintageSettings
from Vintageous.vi.settings import SCOPE_VIEW
from Vintageous.vi.settings import SCOPE_VI_VIEW
from Vintageous.vi.settings import SCOPE_VI_WINDOW
from Vintageous.vi.settings import SCOPE_WINDOW
from Vintageous.vi.settings import set_generic_view_setting
from Vintageous.vi.settings import opt_bool_parser
from Vintageous.vi.settings import set_minimap
from Vintageous.vi.settings import set_sidebar
from Vintageous.vi.settings import opt_rulers_parser


class TestSublimeSettings(ViewTest):
    def setUp(self):
      super().setUp()
      self.view.settings().erase('foo')
      self.setts = SublimeSettings(view=self.view)

    def testCanInitializeClass(self):
      self.assertEqual(self.setts.view, self.view)

    def testCanSetSetting(self):
      self.assertEqual(self.view.settings().get('foo'), None)
      self.assertEqual(self.setts['foo'], None)

      self.setts['foo'] = 100
      self.assertEqual(self.view.settings().get('foo'), 100)

    def testCanGetSetting(self):
      self.setts['foo'] = 100
      self.assertEqual(self.setts['foo'], 100)

    def testCanGetNonexistingKey(self):
      self.assertEqual(self.setts['foo'], None)


class TestVintageSettings(ViewTest):
  def setUp(self):
      super().setUp()
      self.view.settings().erase('vintage')
      self.setts = VintageSettings(view=self.view)

  def testCanInitializeClass(self):
      self.assertEqual(self.setts.view, self.view)
      self.assertEqual(self.view.settings().get('vintage'), {})

  def testCanSetSetting(self):
      self.assertEqual(self.setts['foo'], None)

      self.setts['foo'] = 100
      self.assertEqual(self.view.settings().get('vintage')['foo'], 100)

  def testCanGetSetting(self):
      self.setts['foo'] = 100
      self.assertEqual(self.setts['foo'], 100)

  def testCanGetNonexistingKey(self):
      self.assertEqual(self.setts['foo'], None)


class TestSettingsManager(ViewTest):
  def setUp(self):
      super().setUp()
      self.view.settings().erase('vintage')
      self.settsman = SettingsManager(view=self.view)

  def testCanInitializeClass(self):
      self.assertEqual(self.view, self.settsman.v)

  def testCanAccessViSsettings(self):
      self.settsman.vi['foo'] = 100
      self.assertEqual(self.settsman.vi['foo'], 100)

  def testCanAccessViewSettings(self):
      self.settsman.view['foo'] = 100
      self.assertEqual(self.settsman.view['foo'], 100)


class TestViEditorSettings(ViewTest):
  def setUp(self):
      super().setUp()
      self.view.settings().erase('vintage')
      self.view.settings().erase('vintageous_hlsearch')
      self.view.settings().erase('vintageous_foo')
      self.view.window().settings().erase('vintageous_foo')
      self.settsman = VintageSettings(view=self.view)

  def testKnowsAllSettings(self):
      all_settings = [
          'hlsearch',
          'magic',
          'incsearch',
          'ignorecase',
          'autoindent',
          'showminimap',
          'rulers',
          'showsidebar',
          'visualbell',
      ]

      self.assertEqual(sorted(all_settings), sorted(list(VI_OPTIONS.keys())))

  def testSettingsAreCorrectlyDefined(self):
      KNOWN_OPTIONS = {
          'hlsearch':    vi_user_setting(scope=SCOPE_VI_VIEW,    values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
          'magic':       vi_user_setting(scope=SCOPE_VI_VIEW,    values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
          'incsearch':   vi_user_setting(scope=SCOPE_VI_VIEW,    values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
          'ignorecase':  vi_user_setting(scope=SCOPE_VI_VIEW,    values=(True, False, '0', '1'), default=False, parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
          'autoindent':  vi_user_setting(scope=SCOPE_VI_VIEW,    values=(True, False, '0', '1'), default=True,  parser=None,              action=set_generic_view_setting, negatable=False),
          'showminimap': vi_user_setting(scope=SCOPE_WINDOW,     values=(True, False, '0', '1'), default=True,  parser=None,              action=set_minimap,              negatable=True),
          'visualbell':  vi_user_setting(scope=SCOPE_VI_WINDOW,  values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
          'rulers':      vi_user_setting(scope=SCOPE_VIEW,       values=None,                    default=[],    parser=opt_rulers_parser, action=set_generic_view_setting, negatable=False),
          'showsidebar': vi_user_setting(scope=SCOPE_WINDOW,     values=(True, False, '0', '1'), default=True,  parser=None,              action=set_sidebar,              negatable=True),
      }

      self.assertEqual(len(KNOWN_OPTIONS), len(VI_OPTIONS))
      for (k, v) in KNOWN_OPTIONS.items():
          self.assertEqual(VI_OPTIONS[k], v)

  def testCanRetrieveDefaultValue(self):
      self.assertEqual(self.settsman['hlsearch'], True)

  def testCanRetrieveDefaultValueIfSetValueIsInvalid(self):
      self.settsman.view.settings().set('vintageous_hlsearch', 100)
      self.assertEqual(self.settsman['hlsearch'], True)

  def testCanRetrieveWindowLevelSettings(self):
      # TODO: use mock to patch dict
      VI_OPTIONS['foo'] = vi_user_setting(scope=SCOPE_WINDOW, values=(100,), default='bar', parser=None, action=None, negatable=False)
      self.settsman.view.window().settings().set('vintageous_foo', 100)
      self.assertEqual(self.settsman['foo'], 100)
      del VI_OPTIONS['foo']

  @unittest.skip("Not implemented")
  def testCanDiscriminateWindowSettingsFromViewSettings(self):
      pass
      # TODO: use mock to patch dict
      # TODO: Scopes must be consulted in order from bottom to top: VIEW, WINDOW.
      # VI_OPTIONS['foo'] = vi_user_setting(scope=SCOPE_WINDOW, values=(True, False), default='bar', parser=None)
      # VI_OPTIONS['foo'] = vi_user_setting(scope=SCOPE_VIEW, values=(True, False), default='buzz', parser=None)


# class Test_get_option(unittest.TestCase):
#   def setUp(self):
#       TestsState.view.settings().erase('vintage')
#       TestsState.view.settings().erase('vintageous_foo')
#       self.vi_settings = VintageSettings(view=TestsState.view)

#   def testDefaultScopeIsView(self):
#       VI_OPTIONS['foo'] = vi_user_setting(scope=None, values=(100,), default='bar', parser=None, action=None, negatable=False)
#       self.vi_settings.view.settings().set('vintageous_foo', 100)
#       self.assertEqual(self.vi_settings['foo'], 100)
#       del VI_OPTIONS['foo']

#   def testReturnsDefaultValueIfUnset(self):
#       VI_OPTIONS['foo'] = vi_user_setting(scope=None, values=(100,), default='bar', parser=None, action=None, negatable=False)
#       self.assertEqual(self.vi_settings['foo'], 'bar')
#       del VI_OPTIONS['foo']

#   def testReturnsDefaultValueIfSetToWrongValue(self):
#       VI_OPTIONS['foo'] = vi_user_setting(scope=None, values=(100,), default='bar', parser=None, action=None, negatable=False)
#       self.vi_settings.view.settings().set('vintageous_foo', 'maraca')
#       self.assertEqual(self.vi_settings['foo'], 'bar')
#       del VI_OPTIONS['foo']

#   def testReturnsCorrectValue(self):
#       VI_OPTIONS['foo'] = vi_user_setting(scope=None, values=(100, 200), default='bar', parser=None, action=None, negatable=False)
#       self.vi_settings.view.settings().set('vintageous_foo', 200)
#       self.assertEqual(self.vi_settings['foo'], 200)
#       del VI_OPTIONS['foo']

#   def testCanReturnWindowLevelSetting(self):
#       VI_OPTIONS['foo'] = vi_user_setting(scope=SCOPE_WINDOW, values=(100,), default='bar', parser=None, action=None, negatable=False)
#       self.vi_settings.view.window().settings().set('vintageous_foo', 100)
#       self.assertEqual(self.vi_settings['foo'], 100)
#       del VI_OPTIONS['foo']

#   def testCanReturnViewLevelSetting(self):
#       VI_OPTIONS['foo'] = vi_user_setting(scope=SCOPE_VIEW, values=(100,), default='bar', parser=None, action=None, negatable=False)
#       self.vi_settings.view.settings().set('vintageous_foo', 100)
#       self.assertEqual(self.vi_settings['foo'], 100)
#       del VI_OPTIONS['foo']

########NEW FILE########
__FILENAME__ = test_tag_text_object
import unittest
from collections import namedtuple

import sublime

from Vintageous.vi.text_objects import previous_begin_tag
from Vintageous.vi.text_objects import find_containing_tag
from Vintageous.vi.text_objects import next_end_tag
from Vintageous.vi.utils import modes
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content args expected msg')

R = sublime.Region


TESTS_SEARCH_TAG_FORWARD = (
    test_data(content='<a>foo', args={'start': 0}, expected=(R(0, 3), 'a', False), msg='find tag'),
    test_data(content='<a>foo', args={'start': 1}, expected=(None, None, None), msg="don't find tag"),
    test_data(content='<a>foo</a>', args={'start': 1}, expected=(R(6, 10), 'a', True), msg='find other tag'),

    test_data(content='<a hey="ho">foo', args={'start': 0}, expected=(R(0, 12), 'a', False), msg='find tag with attributes'),
)

TESTS_SEARCH_TAG_BACKWARD = (
    test_data(content='<a>foo', args={'pattern': r'</?(a) *?.*?>', 'start': 0, 'end': 6}, expected=(R(0, 3), 'a', True), msg='find tag'),
    test_data(content='<a>foo', args={'pattern': r'</?(a) *?.*?>', 'start': 0, 'end': 0}, expected=(None, None, None), msg="don't find tag"),
    test_data(content='</a>foo', args={'pattern': r'</?(a) *?.*?>', 'start': 0, 'end': 6}, expected=(R(0, 4), 'a', False), msg='find a closing tag'),
    test_data(content='<a>foo</a>', args={'pattern': r'</?(a) *?.*?>', 'start': 0, 'end': 5}, expected=(R(0, 3), 'a', True), msg='find other tag'),

    test_data(content='<a hey="ho">foo', args={'pattern': r'</?(a) *?.*?>', 'start': 0, 'end': 14}, expected=(R(0, 12), 'a', True), msg='find tag with attributes'),
)


class Test_TagSearch(ViewTest):
    def test_next_unbalanced_end_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_SEARCH_TAG_FORWARD):
            self.write(data.content)
            actual = next_end_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

    def test_previous_unbalanced_begin_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_SEARCH_TAG_BACKWARD):
            self.write(data.content)
            actual = previous_begin_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)


TESTS_CONTAINING_TAG = (
    test_data(content='<a>foo</a>', args={'start': 4}, expected=(R(0, 3), R(6, 10), 'a'), msg='find tag'),
    test_data(content='<div>foo</div>', args={'start': 5}, expected=(R(0, 5), R(8, 14), 'div'), msg='find long tag'),
    test_data(content='<div class="foo">foo</div>', args={'start': 17}, expected=(R(0, 17), R(20, 26), 'div'), msg='find tag with attributes'),

    test_data(content='<div>foo</div>', args={'start': 2}, expected=(R(0, 5), R(8, 14), 'div'), msg='find tag from within start tag'),
    test_data(content='<div>foo</div>', args={'start': 13}, expected=(R(0, 5), R(8, 14), 'div'), msg='find tag from within end tag'),
)

class Test_FindContainingTag(ViewTest):
    def test_find_containing_tag(self):
        self.view.set_syntax_file('Packages/HTML/HTML.tmLanguage')
        for (i, data) in enumerate(TESTS_CONTAINING_TAG):
            self.write(data.content)
            actual = find_containing_tag(self.view, **data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test_text_objects
import unittest

from Vintageous.tests import set_text
from Vintageous.tests import add_sel
from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.vi.text_objects import find_prev_lone_bracket
from Vintageous.vi.text_objects import find_next_lone_bracket
from Vintageous.vi.search import reverse_search_by_pt


class Test_find_prev_lone_bracket_SingleLine_Flat(ViewTest):
    def testReturnsNoneIfNoPreviousLoneBracket(self):
        set_text(self.view, 'abc')

        region = find_prev_lone_bracket(self.view, 1, ('\\{', '\\}'))
        self.assertIsNone(region)

    # TODO: Fix this.
    # Vim finds the current opening bracket if the caret is at its index.
    def testCanFindPreviousLoneBracketAtSelfPosition(self):
        set_text(self.view,'a{b}c')
        add_sel(self.view, self.R(1, 1))

        region = find_prev_lone_bracket(self.view, 1, ('\\{', '\\}'))
        self.assertEqual(region, self.R(1, 2))

    def testCanFindPreviousLoneBracketAtBof(self):
        set_text(self.view,'{ab}c')

        region = find_prev_lone_bracket(self.view, 2, ('\\{', '\\}'))
        self.assertEqual(region, self.R(0, 1))

    def testReturnsNoneIfNoPreviousLoneBracketButLineHasBrackets(self):
        set_text(self.view,'abc{ab}c')

        region = find_prev_lone_bracket(self.view, 2, ('\\{', '\\}'))
        self.assertEqual(region, None)

    def testFindsUnbalancedBracket(self):
        set_text(self.view,'a{bc')

        region = find_prev_lone_bracket(self.view, 3, ('\\{', '\\}'))
        self.assertEqual(region, self.R(1, 2))


class Test_find_prev_lone_bracket_SingleLine_Nested(ViewTest):
    def testFindsOuterFromRhs(self):
        set_text(self.view, 'foo {bar {foo} bar}')

        region = find_prev_lone_bracket(self.view, 16, ('\\{', '\\}'))
        self.assertEqual(region, self.R(4, 5))

    def testFindsOuterFromLhs(self):
        set_text(self.view, 'foo {bar {foo} bar}')

        region = find_prev_lone_bracket(self.view, 7, ('\\{', '\\}'))
        self.assertEqual(region, self.R(4, 5))

    def testFindsInner(self):
        set_text(self.view, 'foo {bar {foo} bar}')

        region = find_prev_lone_bracket(self.view, 13, ('\\{', '\\}'))
        self.assertEqual(region, self.R(9, 10))

    def testFindsOuterIfUnbalancedOuter(self):
        set_text(self.view, 'foo {bar {foo} bar')

        region = find_prev_lone_bracket(self.view, 16, ('\\{', '\\}'))
        self.assertEqual(region, self.R(4, 5))

    def testFindsInnerIfUnbalancedOuter(self):
        set_text(self.view, 'foo {bar {foo} bar')

        region = find_prev_lone_bracket(self.view, 12, ('\\{', '\\}'))
        self.assertEqual(region, self.R(9, 10))


class Test_find_prev_lone_bracket_MultipleLines_Flat(ViewTest):
    def testReturnsNoneIfNoPreviousLoneBracket(self):
        set_text(self.view, 'foo\nbar')

        region = find_prev_lone_bracket(self.view, 5, ('\\{', '\\}'))
        self.assertIsNone(region)

    # TODO: Fix this.
    # Vim finds the current opening bracket if the caret is at its index.
    def testCanFindPreviousLoneBracketAtSelfPosition(self):
        set_text(self.view,'a{\nb}c')
        add_sel(self.view, self.R(1, 1))

        region = find_prev_lone_bracket(self.view, 1, ('\\{', '\\}'))
        self.assertEqual(region, self.R(1, 2))

    def testCanFindPreviousLoneBracketAtBof(self):
        set_text(self.view,'{a\nb}c')

        region = find_prev_lone_bracket(self.view, 2, ('\\{', '\\}'))
        self.assertEqual(region, self.R(0, 1))

    def testReturnsNoneIfNoPreviousLoneBracketButLineHasBrackets(self):
        set_text(self.view,'abc{a\nb}c')

        region = find_prev_lone_bracket(self.view, 2, ('\\{', '\\}'))
        self.assertIsNone(region)

    def testFindsUnbalancedBracket(self):
        set_text(self.view,'a{\nbc')

        region = find_prev_lone_bracket(self.view, 4, ('\\{', '\\}'))
        self.assertEqual(region, self.R(1, 2))


class Test_find_prev_lone_bracket_MultipleLines_Nested(ViewTest):
    def testFindsOuterFromRhs(self):
        set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo}')

        region = find_prev_lone_bracket(self.view, 20, ('\\{', '\\}'))
        self.assertEqual(region, self.R(4, 5))

    def testFindsOuterFromLhs(self):
        set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo}')

        region = find_prev_lone_bracket(self.view, 7, ('\\{', '\\}'))
        self.assertEqual(region, self.R(4, 5))

    def testFindsInner(self):
        set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo}')

        region = find_prev_lone_bracket(self.view, 13, ('\\{', '\\}'))
        self.assertEqual(region, self.R(9, 10))

    def testFindsOuterIfUnbalancedOuter(self):
        set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo')

        region = find_prev_lone_bracket(self.view, 20, ('\\{', '\\}'))
        self.assertEqual(region, self.R(4, 5))

    def testFindsInnerIfUnbalancedOuter(self):
        set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo')

        region = find_prev_lone_bracket(self.view, 16, ('\\{', '\\}'))
        self.assertEqual(region, self.R(9, 10))


class Test_find_find_next_lone_bracket_MultipleLines_Nested(ViewTest):
    # def testFindsOuterFromRhs(self):
    #     set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo}')

    #     region = find_next_lone_bracket(self.view, 20, ('\\{', '\\}'))
    #     self.assertEqual(region, self.R(4, 5))

    # def testFindsOuterFromLhs(self):
    #     set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo}')

    #     region = find_next_lone_bracket(self.view, 8, ('\\{', '\\}'))
    #     self.assertEqual(region, self.R(4, 5))

    def testFindsOuterFromLhs_DeeplyNested(self):
        set_text(self.view, 'foo {bar\n{foo\nbar {foo} bar}\nfoo}')

        region = find_next_lone_bracket(self.view, 7, ('\\{', '\\}'))
        self.assertEqual(region, self.R(32, 33))

    # def testFindsInner(self):
    #     set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo}')

    #     region = find_next_lone_bracket(self.view, 13, ('\\{', '\\}'))
    #     self.assertEqual(region, self.R(9, 10))

    # def testFindsOuterIfUnbalancedOuter(self):
    #     set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo')

    #     region = find_next_lone_bracket(self.view, 20, ('\\{', '\\}'))
    #     self.assertEqual(region, self.R(4, 5))

    # def testFindsInnerIfUnbalancedOuter(self):
    #     set_text(self.view, 'foo {bar\n{foo\nbar}\nfoo')

    #     region = find_next_lone_bracket(self.view, 16, ('\\{', '\\}'))
    #     self.assertEqual(region, self.R(9, 10))

########NEW FILE########
__FILENAME__ = test_word
import unittest

# from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL
from Vintageous.vi.constants import MODE_NORMAL
# from Vintageous.vi.constants import MODE_VISUAL
# from Vintageous.vi.constants import MODE_VISUAL_LINE

from Vintageous.tests import ViewTest
from Vintageous.tests import set_text
from Vintageous.tests import add_sel

from Vintageous.vi.units import next_word_start
from Vintageous.vi.units import word_starts
from Vintageous.vi.units import CLASS_VI_INTERNAL_WORD_START


class Test_next_word_start_InNormalMode_FromWhitespace(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '  foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToPunctuationStart(self):
        set_text(self.view, '  (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEmptyLine(self):
        set_text(self.view, '  \n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToWhitespaceLine(self):
        set_text(self.view, '  \n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEofWithNewline(self):
        set_text(self.view, '  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEof(self):
        set_text(self.view, '   ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneWordLine(self):
        set_text(self.view, '   \nfoo\nbar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '   \n foo\nbar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharWord(self):
        set_text(self.view, '  a foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharLine(self):
        set_text(self.view, '  \na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '  \n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)


class Test_next_word_start_InNormalMode_FromWordStart(ViewTest):
    def testToWordStart(self):
        set_text(self.view, 'foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToPunctuationStart(self):
        set_text(self.view, 'foo (bar)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToEmptyLine(self):
        set_text(self.view, 'foo\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToWhitespaceLine(self):
        set_text(self.view, 'foo\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToEofWithNewline(self):
        set_text(self.view, 'foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToEof(self):
        set_text(self.view, 'foo')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneWordLine(self):
        set_text(self.view, 'foo\nbar\nbaz')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n bar\nbaz')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharWord(self):
        set_text(self.view, 'foo a bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharLine(self):
        set_text(self.view, 'foo\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)


class Test_next_word_start_InNormalMode_FromWord(ViewTest):
    def testToWordStart(self):
        set_text(self.view, 'foo bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToPunctuationStart(self):
        set_text(self.view, 'foo (bar)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToEmptyLine(self):
        set_text(self.view, 'foo\n\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToWhitespaceLine(self):
        set_text(self.view, 'foo\n  \n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToEofWithNewline(self):
        set_text(self.view, 'foo\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToEof(self):
        set_text(self.view, 'foo')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneWordLine(self):
        set_text(self.view, 'foo\nbar\nbaz')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n bar\nbaz')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharWord(self):
        set_text(self.view, 'foo a bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharLine(self):
        set_text(self.view, 'foo\na\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n a\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 4)


class Test_next_word_start_InNormalMode_FromPunctuationStart(ViewTest):
    def testToWordStart(self):
        set_text(self.view, ':foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToPunctuationStart(self):
        set_text(self.view, ': (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEmptyLine(self):
        set_text(self.view, ':\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToWhitespaceLine(self):
        set_text(self.view, ':\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEofWithNewline(self):
        set_text(self.view, ':\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEof(self):
        set_text(self.view, ':')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneWordLine(self):
        set_text(self.view, ':\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, ':\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharWord(self):
        set_text(self.view, ':a bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLine(self):
        set_text(self.view, ':\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, ':\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)


class Test_next_word_start_InNormalMode_FromEmptyLine(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '\nfoo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToPunctuationStart(self):
        set_text(self.view, '\n (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEmptyLine(self):
        set_text(self.view, '\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToWhitespaceLine(self):
        set_text(self.view, '\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEofWithNewline(self):
        set_text(self.view, '\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEof(self):
        set_text(self.view, '')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 0)

    def testToOneWordLine(self):
        set_text(self.view, '\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharWord(self):
        set_text(self.view, '\na bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLine(self):
        set_text(self.view, '\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 1)


class Test_next_word_start_InNormalMode_FromPunctuation(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '::foo\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToPunctuationStart(self):
        set_text(self.view, ':: (foo)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEmptyLine(self):
        set_text(self.view, '::\n\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToWhitespaceLine(self):
        set_text(self.view, '::\n  \n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEofWithNewline(self):
        set_text(self.view, '::\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEof(self):
        set_text(self.view, '::')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneWordLine(self):
        set_text(self.view, '::\nbar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharWord(self):
        set_text(self.view, '::a bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharLine(self):
        set_text(self.view, '::\na\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n a\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b)
        self.assertEqual(pt, 3)


class Test_next_word_start_InInternalNormalMode_FromWhitespace(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '  \n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '  \n foo')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_next_word_start_InInternalNormalMode_FromWordStart(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, 'foo\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)


class Test_next_word_start_InInternalNormalMode_FromWord(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, 'foo\n  ')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n bar')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)


class Test_next_word_start_InInternalNormalMode_FromPunctuationStart(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '.\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '.\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)


class Test_next_word_start_InInternalNormalMode_FromPunctuation(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '::\n  ')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n bar')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_next_word_start_InInternalNormalMode_FromEmptyLine(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_words_InNormalMode(ViewTest):
    def testMove1(self):
        set_text(self.view, 'foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b)
        self.assertEqual(pt, 4)

    def testMove2(self):
        set_text(self.view, 'foo bar fizz\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, count=2)
        self.assertEqual(pt, 8)

    def testMove10(self):
        set_text(self.view, ''.join(('foo bar\n',) * 5))
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, count=9)
        self.assertEqual(pt, 36)


class Test_words_InInternalNormalMode_FromEmptyLine(ViewTest):
    # We can assume the stuff tested for normal mode applies to internal normal mode, so we
    # don't bother with that. Instead, we only test the differing behavior when advancing by
    # word starts in internal normal.
    def testMove1ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)

    def testMove2ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, count=2, internal=True)
        self.assertEqual(pt, 6)

    def testMove1ToWhitespaceLine(self):
        set_text(self.view, '\n  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, count=1, internal=True)
        self.assertEqual(pt, 1)

    def testMove2ToOneWordLine(self):
        set_text(self.view, '\nfoo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 5)

    def testMove3AndSwallowLastNewlineChar(self):
        set_text(self.view, '\nfoo\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=3)
        self.assertEqual(pt, 10)

    def testMove2ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\nfoo\n  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 5)


class Test_words_InInternalNormalMode_FromOneWordLine(ViewTest):
    # We can assume the stuff tested for normal mode applies to internal normal mode, so we
    # don't bother with that. Instead, we only test the differing behavior when advancing by
    # word starts in internal normal.
    def testMove1ToEol(self):
        set_text(self.view, 'foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=1)
        self.assertEqual(pt, 3)

    def testMove2ToLineWithLeadingWhiteSpaceFromWordStart(self):
        set_text(self.view, 'foo\n\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 5)

    def testMove2ToEmptyLineFromWord(self):
        set_text(self.view, 'foo\n\nbar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 4)

    def testMove2ToOneWordLineFromWordStart(self):
        set_text(self.view, 'foo\nbar\nccc\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 8)

    def testMove2ToOneWordLineFromWord(self):
        set_text(self.view, 'foo\nbar\nccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

    def testMove2ToWhitespaceline(self):
        set_text(self.view, 'foo\n  \nccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 10)

    def testMove2ToWhitespacelineFollowedByLeadingWhitespaceFromWord(self):
        set_text(self.view, 'foo\n  \n ccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 11)

    def testMove2ToWhitespacelineFollowedByLeadingWhitespaceFromWordStart(self):
        set_text(self.view, 'foo\n  \n ccc\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 12)


class Test_words_InInternalNormalMode_FromOneCharLongWord(ViewTest):
    def testMove1ToEol(self):
        set_text(self.view, 'x\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=1)
        self.assertEqual(pt, 1)


class Test_words_InInternalNormalMode_FromLine(ViewTest):
    def testMove2ToEol(self):
        set_text(self.view, 'foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

########NEW FILE########
__FILENAME__ = test_word_reverse
import unittest
from collections import namedtuple

from Vintageous.vi.text_objects import word_reverse
from Vintageous.vi.utils import modes
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content args expected msg')


TESTS = (
    test_data(content='abc',           args=(2, 1), expected=0, msg='find word start from the middle of a word'),
    test_data(content='abc abc abc',   args=(8, 1), expected=4, msg='find word start from next word'),
    test_data(content='abc abc abc',   args=(8, 2), expected=0, msg='find word start from next word (count: 2)'),
    test_data(content='abc\nabc\nabc', args=(8, 1), expected=4, msg='find word start from different line'),
    test_data(content='abc\n\nabc',    args=(5, 1), expected=4, msg='stop at empty line'),
    test_data(content='abc a abc',     args=(6, 1), expected=4, msg='stop at single-char word'),
    test_data(content='(abc) abc',     args=(6, 1), expected=4, msg='skip over punctuation simple'),
    test_data(content='abc.(abc)',     args=(5, 1), expected=3, msg='skip over punctuation complex'),
    test_data(content='abc == abc',    args=(7, 1), expected=4, msg='stop at isolated punctuation word'),
)


class Test_word_reverse(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            self.write(data.content)
            actual = word_reverse(self.view, *data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test_word_start_reverse
import unittest
from collections import namedtuple

from Vintageous.vi.text_objects import word_end_reverse
from Vintageous.vi.utils import modes
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest


test_data = namedtuple('test_data', 'content args expected msg')


TESTS = (
    test_data(content='abc',           args=(2, 1), expected=0, msg='go to bof from first word'),
    test_data(content='abc abc abc',   args=(8, 1), expected=6, msg='go to previous word end'),
    test_data(content='abc abc abc',   args=(8, 2), expected=2, msg='go to previous word end (count: 2)'),
    test_data(content='abc\nabc\nabc', args=(8, 1), expected=6, msg='go to previous word end over white space'),
    test_data(content='abc\n\nabc',    args=(5, 1), expected=3, msg='stop at empty line'),
    test_data(content='abc a abc',     args=(6, 1), expected=4, msg='stop at single-char word'),
    test_data(content='abc == abc',    args=(7, 1), expected=5, msg='stop at isolated punctuation word'),
    test_data(content='abc =',         args=(4, 1), expected=2, msg='stop at word end from isolated punctuation'),
    test_data(content='abc abc.abc',   args=(7, 1), expected=6, msg='stop at previous word end from contiguous punctuation'),

    test_data(content='abc abc.abc',   args=(10, 1, True), expected=2, msg='skip over punctuation'),
    test_data(content='abc ',          args=(3, 1), expected=2, msg='stop at previous word end if starting from contiguous space'),
)


class Test_word_end_reverse(ViewTest):
    def testAll(self):
        for (i, data) in enumerate(TESTS):
            self.write(data.content)
            actual = word_end_reverse(self.view, *data.args)

            msg = "failed at test index {0}: {1}".format(i, data.msg)
            self.assertEqual(data.expected, actual, msg)

########NEW FILE########
__FILENAME__ = test_runner
import sublime
import sublime_plugin

import os
import unittest
import contextlib


class __vi_tests_write_buffer(sublime_plugin.TextCommand):
    """Replaces the buffer's content with the specified `text`.

       `text`: Text to be written to the buffer.
    """
    def run(self, edit, text=''):
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)


class __vi_tests_erase_all(sublime_plugin.TextCommand):
    """Replaces the buffer's content with the specified `text`.
    """
    def run(self, edit):
        self.view.erase(edit, sublime.Region(0, self.view.size()))


class OutputPanel(object):
    def __init__(self, name, file_regex='', line_regex='', base_dir=None,
                 word_wrap=False, line_numbers=False, gutter=False,
                 scroll_past_end=False,
                 syntax='Packages/Text/Plain text.tmLanguage',
                 ):

        self.name = name
        self.window = sublime.active_window()

        if not hasattr(self, 'output_view'):
            # Try not to call get_output_panel until the regexes are assigned
            self.output_view = self.window.create_output_panel(self.name)

        # Default to the current file directory
        if (not base_dir and self.window.active_view() and
            self.window.active_view().file_name()):
                base_dir = os.path.dirname(
                        self.window.active_view().file_name()
                        )

        self.output_view.settings().set('result_file_regex', file_regex)
        self.output_view.settings().set('result_line_regex', line_regex)
        self.output_view.settings().set('result_base_dir', base_dir)
        self.output_view.settings().set('word_wrap', word_wrap)
        self.output_view.settings().set('line_numbers', line_numbers)
        self.output_view.settings().set('gutter', gutter)
        self.output_view.settings().set('scroll_past_end', scroll_past_end)
        self.output_view.settings().set('syntax', syntax)

        # Call create_output_panel a second time after assigning the above
        # settings, so that it'll be picked up as a result buffer
        self.window.create_output_panel(self.name)

    def write(self, s):
        f = lambda: self.output_view.run_command('append', {'characters': s})
        sublime.set_timeout(f, 0)

    def flush(self):
        pass

    def show(self):
        self.window.run_command(
                            'show_panel', {'panel': 'output.' + self.name}
                            )

    def close(self):
        pass


class RunVintageousTests(sublime_plugin.WindowCommand):

    @contextlib.contextmanager
    def chdir(self, path=None):
        old_path = os.getcwd()
        if path is not None:
            assert os.path.exists(path), "'path' is invalid"
            os.chdir(path)
        yield
        if path is not None:
            os.chdir(old_path)

    def run(self, **kwargs):
        with self.chdir(kwargs.get('working_dir')):
            p = os.path.join(os.getcwd(), 'tests')
            suite = unittest.TestLoader().discover(p)

            file_regex = r'^\s*File\s*"([^.].*?)",\s*line\s*(\d+),.*$'
            display = OutputPanel('vintageous.tests', file_regex=file_regex)
            display.show()
            runner = unittest.TextTestRunner(stream=display, verbosity=1)

            def run_and_display():
                runner.run(suite)
                display.show()

            sublime.set_timeout_async(run_and_display, 0)

########NEW FILE########
__FILENAME__ = toplist
import argparse
import json
import os
import plistlib


THIS_DIR = os.path.abspath(os.path.dirname(__file__))

def build(source):
    with open(source, 'r') as f:
        json_data = json.load(f)
        plistlib.writePlist(json_data, os.path.splitext(source)[0] + '.tmLanguage')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        description="Builds .tmLanguage files out of .JSON-tmLanguage files.")
    parser.add_argument('-s', dest='source',
                        help="source .JSON-tmLanguage file")
    args = parser.parse_args()
    if args.source:
        build(args.source)

########NEW FILE########
__FILENAME__ = abbrev
"""
Abbreviations.
"""

import sublime
import sublime_plugin

import os
import json


def abbrevs_path():
    path = os.path.join(sublime.packages_path(),
                        'User/_vintageous_abbrev.sublime-completions')
    return os.path.normpath(path)


def load_abbrevs():
    path = abbrevs_path()
    decoded_json = None
    if os.path.exists(path):
        with open(path, 'r') as f:
            decoded_json = json.load(f)
    return decoded_json or {'completions': []}


def save_abbrevs(data):
    # TODO: Make entries temporary unless !mksession is used or something like that.
    # TODO: Enable contexts for abbrevs?
    path = abbrevs_path()
    with open(path, 'w') as f:
        json.dump(data, f)

class Store(object):
    """
    Manages storage for abbreviations.
    """
    def set(self, short, full):
        abbrevs = load_abbrevs()
        idx = self.contains(abbrevs, short)
        if idx is not None:
            abbrevs['completions'][idx] = dict(trigger=short, contents=full)
        else:
            abbrevs['completions'].append(dict(trigger=short, contents=full))
        save_abbrevs(abbrevs)

    def get(self, short):
        raise NotImplementedError()

    def get_all(self):
        abbrevs = load_abbrevs()
        for item in abbrevs['completions']:
            yield item

    def contains(self, data, short):
        # TODO: Inefficient.
        for (i, completion) in enumerate(data['completions']):
            if completion['trigger'] == short:
                return i
        return None

    def erase(self, short):
        data = load_abbrevs()
        idx = self.contains(data, short)
        if idx is not None:
            del data['completions'][idx]
            save_abbrevs(data)

########NEW FILE########
__FILENAME__ = cmd_base
class cmd_types:
    """
    Types of command.
    """
    MOTION          = 1
    ACTION          = 2
    ANY             = 3
    OTHER           = 4
    USER            = 5
    OPEN_NAME_SPACE = 6


class ViCommandDefBase(object):
    """
    Base class for all Vim commands.
    """

    _serializable = ['_inp',]

    def __init__(self):
        self.input_parser = None
        self._inp = ''

    def __getitem__(self, key):
        # XXX: For compatibility. Should be removed eventually.
        return self.__dict__[key]

    @property
    def accept_input(self):
        return False

    @property
    def inp(self):
        """
        Current input for this command.
        """
        return self._inp

    def accept(self, key):
        """
        Processes input for this command.
        """
        _name = self.__class__.__name__
        assert self.input_parser, '{0} does not provide an input parser'.format(_name)
        raise NotImplementedError(
                '{0} must implement .accept()'.format(_name))

    def reset(self):
        self._inp = ''

    def translate(self, state):
        """
        Returns the command as a valid Json object containing all necessary
        data to be run by Vintageous. This is usually the last step before
        handing the command off to ST.

        Every motion and operator must override this method.

        @state
          The current state.
        """
        raise NotImplementedError('command {0} must implement .translate()'
                                              .format(self.__class__.__name__)
                                              )

    @classmethod
    def from_json(cls, data):
        """
        Instantiates a command from a valid Json object representing one.

        @data
          Serialized command data as provided by .serialize().
        """
        instance = cls()
        instance.__dict__.update(data)
        return instance

    def serialize(self):
        """
        Returns a valid Json object representing this command in a format
        Vintageous uses internally.
        """
        data = {'name': self.__class__.__name__,
                'data': {k: v for k, v in self.__dict__.items()
                              if k in self._serializable}
                }
        return data


class ViMissingCommandDef(ViCommandDefBase):
    def translate(self):
        raise TypeError(
            'ViMissingCommandDef should not be used as a runnable command'
            )


class ViMotionDef(ViCommandDefBase):
    """
    Base class for all motions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updates_xpos = False
        self.scroll_into_view = False
        self.type = cmd_types.MOTION


class ViOperatorDef(ViCommandDefBase):
    """
    Base class for all operators.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updates_xpos = False
        self.scroll_into_view = False
        self.motion_required = False
        self.type = cmd_types.ACTION
        self.repeatable = False

########NEW FILE########
__FILENAME__ = cmd_defs
"""
Vim commands used internally by Vintageous that also produce ST commands.

These are the core implementations for all Vim commands.
"""

from Vintageous.vi.utils import modes
from Vintageous.vi.inputs import input_types
from Vintageous.vi.inputs import parser_def
from Vintageous.vi import inputs
from Vintageous.vi import utils
from Vintageous.vi.cmd_base import ViOperatorDef
from Vintageous.vi.cmd_base import ViMotionDef
from Vintageous.vi.cmd_base import ViMissingCommandDef
from Vintageous.vi import keys
from Vintageous.vi.keys import seqs

import sublime_plugin


_MODES_MOTION = (modes.NORMAL, modes.OPERATOR_PENDING, modes.VISUAL,
                 modes.VISUAL_LINE, modes.VISUAL_BLOCK)

_MODES_ACTION = (modes.NORMAL, modes.VISUAL, modes.VISUAL_LINE,
                 modes.VISUAL_BLOCK)



@keys.assign(seq=seqs.D, modes=_MODES_ACTION)
class ViDeleteByChars(ViOperatorDef):
    """
    Vim: `d`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_d'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.BIG_O, modes=_MODES_ACTION)
class ViInsertLineBefore(ViOperatorDef):
    """
    Vim: `O`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        state.glue_until_normal_mode = True

        cmd = {}
        cmd['action'] = '_vi_big_o'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.O, modes=_MODES_ACTION)
class ViInsertLineAfter(ViOperatorDef):
    """
    Vim: `o`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = False

    def translate(self, state):
        cmd = {}

        # XXX: Create a separate command?
        if state.mode in (modes.VISUAL, modes.VISUAL_LINE):
            cmd['action'] = '_vi_visual_o'
            cmd['action_args'] = {'mode': state.mode, 'count': 1}

        else:
            state.glue_until_normal_mode = True

            cmd = {}
            cmd['action'] = '_vi_o'
            cmd['action_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.X, modes=_MODES_ACTION)
class ViRightDeleteChars(ViOperatorDef):
    """
    Vim: `x`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_x'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.S, modes=_MODES_ACTION)
class ViSubstituteChar(ViOperatorDef):
    """
    Vim: `s`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        # XXX: Handle differently from State?
        state.glue_until_normal_mode = True

        cmd = {}
        cmd['action'] = '_vi_s'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.Y, modes=_MODES_ACTION)
class ViYankByChars(ViOperatorDef):
    """
    Vim: `y`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_y'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.EQUAL, modes=_MODES_ACTION)
class ViReindent(ViOperatorDef):
    """
    Vim: `=`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_equal'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.GREATER_THAN, modes=_MODES_ACTION)
class ViIndent(ViOperatorDef):
    """
    Vim: `>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_greater_than'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.LESS_THAN, modes=_MODES_ACTION)
class ViUnindent(ViOperatorDef):
    """
    Vim: `<`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_less_than'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.C, modes=_MODES_ACTION)
class ViChangeByChars(ViOperatorDef):
    """
    Vim: `c`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        state.glue_until_normal_mode = True

        cmd = {}
        cmd['action'] = '_vi_c'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.U, modes=_MODES_ACTION)
class ViUndo(ViOperatorDef):
    """
    Vim: `u`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}

        if state.mode in (modes.VISUAL,
                          modes.VISUAL_LINE,
                          modes.VISUAL_BLOCK):
            cmd['action'] = '_vi_visual_u'
            cmd['action_args'] = {'count': state.count, 'mode': state.mode}
            return cmd

        cmd['action'] = '_vi_u'
        cmd['action_args'] = {'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_R, modes=_MODES_ACTION)
class ViRedo(ViOperatorDef):
    """
    Vim: `C-r`
    """

    def __init__(self, inclusive=False, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_r'
        cmd['action_args'] = {'count': state.count, 'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.BIG_D, modes=_MODES_ACTION)
class ViDeleteToEol(ViOperatorDef):
    """
    Vim: `D`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_big_d'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.BIG_C, modes=_MODES_ACTION)
class ViChangeToEol(ViOperatorDef):
    """
    Vim: `C`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        state.glue_until_normal_mode = True

        cmd = {}
        cmd['action'] = '_vi_big_c'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register
                              }
        return cmd


@keys.assign(seq=seqs.G_BIG_U_BIG_U, modes=_MODES_ACTION)
@keys.assign(seq=seqs.G_BIG_U_G_BIG_U, modes=_MODES_ACTION)
class ViChangeToUpperCaseByLines(ViOperatorDef):
    """
    Vim: `gUU`, `gUgU`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_big_u_big_u'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CC, modes=_MODES_ACTION)
class ViChangeLine(ViOperatorDef):
    """
    Vim: `cc`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        state.glue_until_normal_mode = True

        cmd = {}
        cmd['action'] = '_vi_cc_action'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.DD, modes=_MODES_ACTION)
class ViDeleteLine(ViOperatorDef):
    """
    Vim: `dd`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_dd_action'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_R, modes=_MODES_ACTION)
class ViEnterReplaceMode(ViOperatorDef):
    """
    Vim: `R`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_enter_replace_mode'
        cmd['action_args'] = {}
        state.glue_until_normal_mode = True
        return cmd


@keys.assign(seq=seqs.GREATER_THAN_GREATER_THAN, modes=_MODES_ACTION)
class ViIndentLine(ViOperatorDef):
    """
    Vim: `>>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_greater_than_greater_than'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.GUGU, modes=_MODES_ACTION)
@keys.assign(seq=seqs.GUU, modes=_MODES_ACTION)
class ViChangeToLowerCaseByLines(ViOperatorDef):
    """
    Vim: `guu`, `gugu`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_guu'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.GU, modes=_MODES_ACTION)
class ViChangeToLowerCaseByChars(ViOperatorDef):
    """
    Vim: `gu`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_gu'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.EQUAL_EQUAL, modes=_MODES_ACTION)
class ViReindentLine(ViOperatorDef):
    """
    Vim: `==`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_equal_equal'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.LESS_THAN_LESS_THAN, modes=_MODES_ACTION)
class ViUnindentLine(ViOperatorDef):
    """
    Vim: `<<`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_less_than_less_than'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.YY, modes=_MODES_ACTION)
@keys.assign(seq=seqs.BIG_Y, modes=_MODES_ACTION)
class ViYankLine(ViOperatorDef):
    """
    Vim: `yy`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_yy'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.G_TILDE_TILDE, modes=_MODES_ACTION)
class ViInvertCaseByLines(ViOperatorDef):
    """
    Vim: `g~~`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_tilde_g_tilde'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.TILDE, modes=_MODES_ACTION)
class ViForceInvertCaseByChars(ViOperatorDef):
    """
    Vim: `~`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_tilde'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_S, modes=_MODES_ACTION)
class ViSubstituteByLines(ViOperatorDef):
    """
    Vim: `S`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_big_s_action'
        cmd['action_args'] = {'mode': state.mode, 'count': 1, 'register': state.register}
        state.glue_until_normal_mode = True
        return cmd


@keys.assign(seq=seqs.G_TILDE, modes=_MODES_ACTION)
class ViInvertCaseByChars(ViOperatorDef):
    """
    Vim: `g~`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_tilde'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


# TODO: Duplicated.
@keys.assign(seq=seqs.G_BIG_U, modes=_MODES_ACTION)
class ViChangeToUpperCaseByChars(ViOperatorDef):
    """
    Vim: `gU`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.motion_required = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_big_u'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_J, modes=_MODES_ACTION + (modes.SELECT,))
class ViJoinLines(ViOperatorDef):
    """
    Vim: `J`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}

        if state.mode == modes.SELECT:
            # Exits select mode.
            cmd['action'] = '_vi_select_big_j'
            cmd['action_args'] = {'mode': state.mode, 'count': state.count}
            return cmd

        cmd['action'] = '_vi_big_j'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_X, modes=_MODES_ACTION)
class ViDecrement(ViOperatorDef):
    """
    Vim: `C-x`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_modify_numbers'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'subtract': True,
                              }
        return cmd


@keys.assign(seq=seqs.CTRL_A, modes=_MODES_ACTION)
class ViIncrement(ViOperatorDef):
    """
    Vim: `C-a`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_modify_numbers'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.G_BIG_J, modes=_MODES_ACTION)
class ViJoinLinesNoSeparator(ViOperatorDef):
    """
    # FIXME: Doesn't work.
    Vim: `gJ`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_big_j'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count, 'separator': None}
        return cmd


@keys.assign(seq=seqs.V, modes=_MODES_ACTION)
class ViEnterVisualMode(ViOperatorDef):
    """
    Vim: `v`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_enter_visual_mode'
        cmd['action_args'] = {'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.Z_ENTER, modes=_MODES_ACTION)
@keys.assign(seq=seqs.ZT, modes=_MODES_ACTION)
class ViScrollToScreenTop(ViOperatorDef):
    """
    Vim: `z<CR>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_z_enter'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.ZB, modes=_MODES_ACTION)
class ViScrollToScreenBottom(ViOperatorDef):
    """
    Vim: `zb`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_z_minus'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.ZZ, modes=_MODES_ACTION)
class ViScrollToScreenCenter(ViOperatorDef):
    """
    Vim: `zz`
    """

    # TODO: z- and zb are different.
    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_zz'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.GQ, modes=_MODES_ACTION)
class ViReformat(ViOperatorDef):
    """
    Vim: `gq`
    """

    # TODO: z- and zb are different.
    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.motion_required = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_gq'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.P, modes=_MODES_ACTION)
class ViPasteAfter(ViOperatorDef):
    """
    Vim: `p`
    """

    # TODO: z- and zb are different.
    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_p'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }

        return cmd


@keys.assign(seq=seqs.BIG_P, modes=_MODES_ACTION)
class ViPasteBefore(ViOperatorDef):
    """
    Vim: `P`
    """

    # TODO: z- and zb are different.
    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.repeatable = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_big_p'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              }

        return cmd


@keys.assign(seq=seqs.BIG_X, modes=_MODES_ACTION)
class ViLeftDeleteChar(ViOperatorDef):
    """
    Vim: `X`
    """

    # TODO: z- and zb are different.
    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_big_x'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count, 'register': state.register}

        return cmd


@keys.assign(seq=seqs.CTRL_W_L, modes=_MODES_ACTION)
class ViSendViewToRightPane(ViOperatorDef):
    """
    Vim: `<C-W-L>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_w_big_l'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_W_H, modes=_MODES_ACTION)
class ViSendViewToLeftPane(ViOperatorDef):
    """
    Vim: `<C-W-H>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_w_big_h'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.GT, modes=_MODES_ACTION)
class ViActivateNextTab(ViOperatorDef):
    """
    Vim: `gt`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_gt'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.G_BIG_T, modes=_MODES_ACTION)
class ViActivatePreviousTab(ViOperatorDef):
    """
    Vim: `gT`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_big_t'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_W_L, modes=_MODES_ACTION)
class ViActivatePaneToTheRight(ViOperatorDef):
    """
    Vim: `<C-W-l>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_w_l'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_W_H, modes=_MODES_ACTION)
class ViActivatePaneToTheLeft(ViOperatorDef):
    """
    Vim: `<C-W-h>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_w_h'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_W_V, modes=_MODES_ACTION)
class ViSplitVertically(ViOperatorDef):
    """
    Vim: `<C-W-v>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_w_v'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_W_Q, modes=_MODES_ACTION)
class ViDestroyCurrentPane(ViOperatorDef):
    """
    Vim: `<C-W-q>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_w_q'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_V, modes=_MODES_ACTION)
class ViEnterVisualLineMode(ViOperatorDef):
    """
    Vim: `V`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_enter_visual_line_mode'
        cmd['action_args'] = {'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.GV, modes=_MODES_ACTION)
class ViRestoreVisualSelections(ViOperatorDef):
    """
    Vim: `gv`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_gv'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.CTRL_K_CTRL_B, modes=_MODES_ACTION)
class StToggleSidebar(ViOperatorDef):
    """
    Vintageous: `<C-K-b>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'toggle_side_bar'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.CTRL_BIG_F, modes=_MODES_ACTION)
class StFinInFiles(ViOperatorDef):
    """
    Vintageous: `Ctrl+Shift+F`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'show_panel'
        cmd['action_args'] = {'panel': 'find_in_files'}
        return cmd


@keys.assign(seq=seqs.CTRL_O, modes=_MODES_ACTION)
class ViJumpBack(ViOperatorDef):
    """
    Vim: `<C-o>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'jump_back'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.CTRL_I, modes=_MODES_ACTION)
class ViJumpForward(ViOperatorDef):
    """
    Vim: `<C-i>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'jump_forward'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.SHIFT_CTRL_F12, modes=_MODES_ACTION)
class StGotoSymbolInProject(ViOperatorDef):
    """
    Vintageous: `<C-S-f12>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'goto_symbol_in_project'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.CTRL_F12, modes=_MODES_ACTION)
class StGotoSymbolInFile(ViOperatorDef):
    """
    Vintageous: `<C-f12>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'show_overlay'
        cmd['action_args'] = {'overlay': 'goto', 'text': '@'}
        return cmd


@keys.assign(seq=seqs.F12, modes=_MODES_ACTION)
class StGotoDefinition(ViOperatorDef):
    """
    Vintageous: `f12`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'goto_definition'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.CTRL_F2, modes=_MODES_ACTION)
class StToggleBookmark(ViOperatorDef):
    """
    Vintageous: `<C-f2>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'toggle_bookmark'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.CTRL_SHIFT_F2, modes=_MODES_ACTION)
class StClearBookmarks(ViOperatorDef):
    """
    Vintageous: `<C-S-f2>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'clear_bookmarks'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.F2, modes=_MODES_ACTION)
class StPrevBookmark(ViOperatorDef):
    """
    Vintageous: `f2`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'prev_bookmark'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.SHIFT_F2, modes=_MODES_ACTION)
class StNextBookmark(ViOperatorDef):
    """
    Vintageous: `<S-f2>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'next_bookmark'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.DOT, modes=_MODES_ACTION)
class ViRepeat(ViOperatorDef):
    """
    Vim: `.`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_dot'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'repeat_data': state.repeat_data,
                              }
        return cmd


@keys.assign(seq=seqs.CTRL_R, modes=_MODES_ACTION)
class ViOpenRegisterFromInsertMode(ViOperatorDef):
    """
    TODO: Implement this.
    Vim: `<C-r>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_r'
        cmd['action_args'] = {'count': state.count, 'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.CTRL_Y, modes=_MODES_ACTION)
class ViScrollByLinesUp(ViOperatorDef):
    """
    Vim: `<C-y>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_y'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_U, modes=_MODES_ACTION)
class ViUndoLineChanges(ViOperatorDef):
    """
    TODO: Implement this.
    Vim: `U`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}

        if state.mode in (modes.VISUAL,
                          modes.VISUAL_LINE,
                          modes.VISUAL_BLOCK):
            cmd['action'] = '_vi_visual_big_u'
            cmd['action_args'] = {'count': state.count, 'mode': state.mode}
            return cmd

        return {}


@keys.assign(seq=seqs.CTRL_E, modes=_MODES_ACTION)
class ViScrollByLinesDown(ViOperatorDef):
    """
    Vim: `<C-e>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_e'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.F11, modes=_MODES_ACTION)
class StToggleFullScreen(ViOperatorDef):
    """
    Vintageous: `f11`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'toggle_full_screen'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.F7, modes=_MODES_ACTION)
class StBuild(ViOperatorDef):
    """
    Vintageous: `f7`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'build'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.SHIFT_F4, modes=_MODES_ACTION)
class StFindPrev(ViOperatorDef):
    """
    Vintageous: `Ctrl+F4`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'find_prev'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.AT, modes=_MODES_ACTION)
class ViOpenMacrosForRepeating(ViOperatorDef):
    """
    Vim: `@`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '`@` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_at'
        cmd['action_args'] = {'name': self.inp,
                              'count': state.count}
        return cmd


@keys.assign(seq=seqs.Q, modes=_MODES_ACTION)
class ViToggleMacroRecorder(ViOperatorDef):
    """
    Vim: `q`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '`q` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_q'
        cmd['action_args'] = {'name': self.inp}
        return cmd


@keys.assign(seq=seqs.F3, modes=_MODES_ACTION)
class StFindNext(ViOperatorDef):
    """
    Vintageous: `f3`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'find_next'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.F4, modes=_MODES_ACTION)
class StFindNextResult(ViOperatorDef):
    """
    Vintageous: `f4`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'next_result'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.SHIFT_F4, modes=_MODES_ACTION)
class StFindPrevResult(ViOperatorDef):
    """
    Vintageous: `Shift+F4`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'prev_result'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.BIG_Z_BIG_Z, modes=_MODES_ACTION)
class ViQuit(ViOperatorDef):
    """
    TODO: Is this used?
    Vim: `ZZ`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'ex_quit'
        cmd['action_args'] = {'forced': True, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.G_BIG_H, modes=_MODES_ACTION)
class ViEnterSelectModeForSearch(ViOperatorDef):
    """
    Vim: `gH`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_g_big_h'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.SHIFT_F4, modes=_MODES_ACTION)
class StPrevResult(ViOperatorDef):
    """
    Vim: `Shift+F4`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'prev_result'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.GH, modes=_MODES_ACTION)
class ViEnterSelectMode(ViOperatorDef):
    """
    Vim: `gh`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_enter_select_mode'
        cmd['action_args'] = {'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.CTRL_V, modes=_MODES_ACTION)
class ViEnterVisualBlockMode(ViOperatorDef):
    """
    Vim: `<C-v>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_enter_visual_block_mode'
        cmd['action_args'] = {'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.CTRL_P, modes=_MODES_ACTION)
class StShowGotoAnything(ViOperatorDef):
    """
    Vintageous: `<C-p>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'show_overlay'
        cmd['action_args'] = {'overlay': 'goto', 'show_files': True}
        return cmd


@keys.assign(seq=seqs.J, modes=(modes.SELECT,))
class ViAddSelection(ViOperatorDef):
    """
    Vintageous: `<C-p>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_select_j'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.ALT_CTRL_P, modes=_MODES_ACTION)
class StShowSwitchProject(ViOperatorDef):
    """
    Vintageous: `<C-M-p>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'prompt_select_workspace'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.CTRL_BIG_P, modes=_MODES_ACTION)
class StShowCommandPalette(ViOperatorDef):
    """
    Vintageous: `<C-S-p>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'show_overlay'
        cmd['action_args'] = {'overlay': 'command_palette'}
        return cmd


@keys.assign(seq=seqs.I, modes=_MODES_ACTION + (modes.SELECT,))
class ViEnterInserMode(ViOperatorDef):
    """
    Vim: `i`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        state.glue_until_normal_mode = True

        cmd = {}
        cmd['action'] = '_enter_insert_mode'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.ESC, modes=_MODES_ACTION)
class ViEnterNormalMode(ViOperatorDef):
    """
    Vim: `<esc>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_enter_normal_mode'
        cmd['action_args'] = {'mode': state.mode}
        return cmd


@keys.assign(seq=seqs.A, modes=_MODES_ACTION)
class ViInsertAfterChar(ViOperatorDef):
    """
    Vim: `a`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_a'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}

        if state.mode != modes.SELECT:
            state.glue_until_normal_mode = True

        return cmd


@keys.assign(seq=seqs.BIG_A, modes=_MODES_ACTION + (modes.SELECT,))
class ViInsertAtEol(ViOperatorDef):
    """
    Vim: `A`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_big_a'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}

        if state.mode != modes.SELECT:
            state.glue_until_normal_mode = True

        return cmd


@keys.assign(seq=seqs.BIG_I, modes=_MODES_ACTION)
class ViInsertAtBol(ViOperatorDef):
    """
    Vim: `I`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_big_i'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}

        if state.mode != modes.SELECT:
            state.glue_until_normal_mode = True

        return cmd


@keys.assign(seq=seqs.COLON, modes=_MODES_ACTION)
class ViEnterCommandLineMode(ViOperatorDef):
    """
    Vim: `:`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'vi_colon_input'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.F9, modes=_MODES_ACTION)
class StSortLines(ViOperatorDef):
    """
    Vintageous: `f9`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'sort_lines'
        cmd['action_args'] = {'case_sensitive': False}
        return cmd


@keys.assign(seq=seqs.CTRL_G, modes=_MODES_ACTION)
class ViShowFileStatus(ViOperatorDef):
    """
    Vim: `<C-g>`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'ex_file'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.BIG_Z_BIG_Q, modes=_MODES_ACTION)
class ViExitEditor(ViOperatorDef):
    """
    Vim: `ZQ`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'ex_quit'
        cmd['action_args'] = {'forced': True, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_Z_BIG_Z, modes=_MODES_ACTION)
class ViCloseFile(ViOperatorDef):
    """
    Vim: `ZZ`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'ex_exit'
        cmd['action_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.F6, modes=_MODES_ACTION)
class StToggleSpelling(ViOperatorDef):
    """
    Vintageous: `f6`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = 'toggle_setting'
        cmd['action_args'] = {'setting': 'spell_check'}
        return cmd


@keys.assign(seq=seqs.G_BIG_D, modes=_MODES_ACTION)
class ViGotoSymbolInProject(ViOperatorDef):
    """
    Vim: `gD`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['action'] = '_vi_go_to_symbol'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'globally': True}
        return cmd


@keys.assign(seq=seqs.K, modes=(modes.SELECT,))
class ViDeselectInstance(ViOperatorDef):
    """
    Vintageous: `k` (select mode)
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        """
        Non-standard.
        """
        if state.mode != modes.SELECT:
            raise ValueError('bad mode, expected mode_select, got {0}'.format(state.mode))

        cmd = {}
        cmd['action'] = 'soft_undo'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.L, modes=(modes.SELECT,))
class ViSkipInstance(ViOperatorDef):
    """
    Vintageous: `l` (select mode)
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        """
        Non-standard.
        """
        if state.mode != modes.SELECT:
            raise ValueError('bad mode, expected mode_select, got {0}'.format(state.mode))

        cmd = {}
        cmd['action'] = 'find_under_expand_skip'
        cmd['action_args'] = {}
        return cmd


@keys.assign(seq=seqs.GD, modes=_MODES_MOTION)
class ViGotoSymbolInFile(ViMotionDef):
    """
    Vim: `gd`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_go_to_symbol'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'globally': False}
        return cmd


@keys.assign(seq=seqs.L, modes=_MODES_MOTION)
@keys.assign(seq=seqs.RIGHT, modes=_MODES_MOTION)
@keys.assign(seq=seqs.SPACE, modes=_MODES_MOTION)
class ViMoveRightByChars(ViMotionDef):
    """
    Vim: `l`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_l'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.SHIFT_ENTER, modes=_MODES_MOTION)
class ViShiftEnterMotion(ViMotionDef):
    """
    Vim: `<S-CR>`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_shift_enter'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.B, modes=_MODES_MOTION)
class ViMoveByWordsBackward(ViMotionDef):
    """
    Vim: `b`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_b'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BIG_B, modes=_MODES_MOTION)
class ViMoveByBigWordsBackward(ViMotionDef):
    """
    Vim: `B`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_b'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BIG_W, modes=_MODES_MOTION)
class ViMoveByBigWords(ViMotionDef):
    """
    Vim: `W`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_w'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.E, modes=_MODES_MOTION)
class ViMoveByWordEnds(ViMotionDef):
    """
    Vim: `e`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_e'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BIG_H, modes=_MODES_MOTION)
class ViGotoScreenTop(ViMotionDef):
    """
    Vim: `H`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_h'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.GE, modes=_MODES_MOTION)
class ViMoveByWordEndsBackward(ViMotionDef):
    """
    Vim: `ge`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_ge'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.G_BIG_E, modes=_MODES_MOTION)
class ViMoveByBigWordEndsBackward(ViMotionDef):
    """
    Vim: `gE`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_g_big_e'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BIG_L, modes=_MODES_MOTION)
class ViGotoScreenBottom(ViMotionDef):
    """
    Vim: `L`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_l'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BIG_M, modes=_MODES_MOTION)
class ViGotoScreenMiddle(ViMotionDef):
    """
    Vim: `M`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_m'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.CTRL_D, modes=_MODES_MOTION)
class ViMoveHalfScreenDown(ViMotionDef):
    """
    Vim: `<C-d>`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_ctrl_d'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.CTRL_U, modes=_MODES_MOTION)
class ViMoveHalfScreenUp(ViMotionDef):
    """
    Vim: `<C-u>`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_ctrl_u'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.CTRL_F, modes=_MODES_MOTION)
@keys.assign(seq=seqs.PAGE_UP, modes=_MODES_MOTION)
class ViMoveScreenDown(ViMotionDef):
    """
    Vim: `<C-f>`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_ctrl_f'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.CTRL_B, modes=_MODES_MOTION)
@keys.assign(seq=seqs.PAGE_DOWN, modes=_MODES_MOTION)
class ViMoveScreenUp(ViMotionDef):
    """
    Vim: `<C-b>`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_ctrl_b'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BACKTICK, modes=_MODES_MOTION)
class ViGotoExactMarkXpos(ViMotionDef):
    """
    Vim: ```
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '``` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_backtick'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'character': self.inp}
        return cmd


@keys.assign(seq=seqs.DOLLAR, modes=_MODES_MOTION)
@keys.assign(seq=seqs.END, modes=_MODES_MOTION)
class ViMoveToEol(ViMotionDef):
    """
    Vim: `$`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_dollar'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.ENTER, modes=_MODES_MOTION)
class ViMotionEnter(ViMotionDef):
    """
    Vim: `<CR>`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_enter'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.G_UNDERSCORE, modes=_MODES_MOTION)
class ViMoveToSoftEol(ViMotionDef):
    """
    Vim: `g_`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_g__'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.GJ, modes=_MODES_MOTION)
class ViMoveByScreenLineDown(ViMotionDef):
    """
    Vim: `gj`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_gj'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.GK, modes=_MODES_MOTION)
class ViMoveByScreenLineUp(ViMotionDef):
    """
    Vim: `gk`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_gk'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.LEFT_BRACE, modes=_MODES_MOTION)
class ViMoveByBlockUp(ViMotionDef):
    """
    Vim: `{`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_left_brace'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.SEMICOLON, modes=_MODES_MOTION)
class ViRepeatCharSearchForward(ViMotionDef):
    """
    Vim: `;`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        forward = state.last_char_search_command in ('vi_t', 'vi_f')
        inclusive = state.last_char_search_command in ('vi_f', 'vi_big_f')

        cmd['motion'] = ('_vi_find_in_line' if forward
                                            else '_vi_reverse_find_in_line')

        cmd['motion_args'] = {'mode': state.mode, 'count': state.count,
                              'char': state.last_character_search,
                              'change_direction': False,
                              'inclusive': inclusive,
                              'skipping': not inclusive
                              }

        return cmd


@keys.assign(seq=seqs.QUOTE, modes=_MODES_MOTION)
class ViGotoMark(ViMotionDef):
    """
    Vim: `'`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True
        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '`\'` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}

        if self.inp == "'":
            cmd['is_jump'] = True
            cmd['motion'] = '_vi_quote_quote'
            cmd['motion_args'] = {} # {'mode': state.mode, 'count': state.count}
            return cmd

        cmd['is_jump'] = True
        cmd['motion'] = '_vi_quote'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'character': self.inp,
                              }
        return cmd


@keys.assign(seq=seqs.RIGHT_BRACE, modes=_MODES_MOTION)
class ViMoveByBlockDown(ViMotionDef):
    """
    Vim: `}`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_right_brace'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.LEFT_PAREN, modes=_MODES_MOTION)
class ViMoveBySentenceUp(ViMotionDef):
    """
    Vim: `(`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_left_paren'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.RIGHT_PAREN, modes=_MODES_MOTION)
class ViMoveBySentenceDown(ViMotionDef):
    """
    Vim: `)`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_right_paren'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.LEFT_SQUARE_BRACKET, modes=_MODES_MOTION)
class ViMoveBySquareBracketUp(ViMotionDef):
    """
    Vim: `[`
    """
    # TODO: Revise this.
    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_left_square_bracket'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.PERCENT, modes=_MODES_MOTION)
class ViGotoLinesPercent(ViMotionDef):
    """
    Vim: `%`
    """
    # TODO: Revise this.
    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_percent'

        percent = None
        if state.motion_count or state.action_count:
            percent = state.count

        cmd['motion_args'] = {'mode': state.mode, 'percent': percent}

        return cmd


@keys.assign(seq=seqs.COMMA, modes=_MODES_MOTION)
class ViRepeatCharSearchBackward(ViMotionDef):
    """
    Vim: `,`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        forward = state.last_char_search_command in ('vi_t', 'vi_f')
        inclusive = state.last_char_search_command in ('vi_f', 'vi_big_f')

        cmd['motion'] = ('_vi_find_in_line' if not forward
                                            else '_vi_reverse_find_in_line')
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count,
                              'char': state.last_character_search,
                              'change_direction': False,
                              'inclusive': inclusive,
                              'skipping': not inclusive}

        return cmd


@keys.assign(seq=seqs.PIPE, modes=_MODES_MOTION)
class ViMoveByLineCols(ViMotionDef):
    """
    Vim: `|`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_pipe'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.BIG_E, modes=_MODES_MOTION)
class ViMoveByBigWordEnds(ViMotionDef):
    """
    Vim: `E`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_e'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.H, modes=_MODES_MOTION)
@keys.assign(seq=seqs.LEFT, modes=_MODES_MOTION)
@keys.assign(seq=seqs.BACKSPACE, modes=_MODES_MOTION)
class ViMoveLeftByChars(ViMotionDef):
    """
    Vim: `h`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}

        if state.mode == modes.SELECT:
            cmd['motion'] = 'find_under_expand_skip'
            cmd['motion_args'] = {}
            return cmd

        cmd['motion'] = '_vi_h'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.W, modes=_MODES_MOTION)
class ViMoveByWords(ViMotionDef):
    """
    Vim: `w`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_w'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}

        return cmd


@keys.assign(seq=seqs.J, modes=_MODES_MOTION)
@keys.assign(seq=seqs.DOWN, modes=_MODES_MOTION)
class ViMoveDownByLines(ViMotionDef):
    """
    Vim: `j`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_j'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count, 'xpos': state.xpos}
        return cmd


@keys.assign(seq=seqs.K, modes=_MODES_MOTION)
@keys.assign(seq=seqs.UP, modes=_MODES_MOTION)
class ViMoveUpByLines(ViMotionDef):
    """
    Vim: `k`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_k'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'xpos': state.xpos}
        return cmd


@keys.assign(seq=seqs.HAT, modes=_MODES_MOTION)
@keys.assign(seq=seqs.HOME, modes=_MODES_MOTION)
class ViMoveToBol(ViMotionDef):
    """
    Vim: `^`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_hat'
        cmd['motion_args'] = {'count': state.count, 'mode': state.mode}

        return cmd


@keys.assign(seq=seqs.UNDERSCORE, modes=_MODES_MOTION)
class ViMoveToBol(ViMotionDef):
    """
    Vim: `^`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_underscore'
        cmd['motion_args'] = {'count': state.count, 'mode': state.mode}

        return cmd


@keys.assign(seq=seqs.ZERO, modes=_MODES_MOTION)
class ViMoveToHardBol(ViMotionDef):
    """
    Vim: `0`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_zero'
        cmd['motion_args'] = {'count': state.count, 'mode': state.mode}

        return cmd


@keys.assign(seq=seqs.N, modes=_MODES_MOTION)
class ViRepeatSearchForward(ViMotionDef):
    """
    Vim: `;`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_n'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'search_string': state.last_buffer_search}

        return cmd


@keys.assign(seq=seqs.BIG_N, modes=_MODES_MOTION)
class ViRepeatSearchBackward(ViMotionDef):
    """
    Vim: `,`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_big_n'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'search_string': state.last_buffer_search}

        return cmd


@keys.assign(seq=seqs.STAR, modes=_MODES_MOTION)
class ViFindWord(ViMotionDef):
    """
    Vim: `*`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_star'
        cmd['motion_args'] = {'count': state.count, 'mode': state.mode}

        return cmd


@keys.assign(seq=seqs.OCTOTHORP, modes=_MODES_MOTION)
class ViReverseFindWord(ViMotionDef):
    """
    Vim: `#`
    """

    # Trivia: Octothorp seems to be a symbol used in maps to represent a
    #         small village surrounded by eight fields.

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_octothorp'
        cmd['motion_args'] = {'count': state.count, 'mode': state.mode}

        return cmd


@keys.assign(seq=seqs.BIG_Z, modes=_MODES_MOTION)
@keys.assign(seq=seqs.CTRL_K, modes=_MODES_MOTION)
@keys.assign(seq=seqs.CTRL_W, modes=_MODES_MOTION)
@keys.assign(seq=seqs.G, modes=_MODES_MOTION)
@keys.assign(seq=seqs.Z, modes=_MODES_MOTION)
# TODO: This is called a 'submode' in the vim docs.
@keys.assign(seq=seqs.CTRL_X, modes=[modes.INSERT])
# FIXME: This should not be a motion.
class ViOpenNameSpace(ViMotionDef):
    """
    Vim: `g`, `z`, ...
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)

    def translate(self, state):
        return {}


@keys.assign(seq=seqs.DOUBLE_QUOTE, modes=_MODES_MOTION)
class ViOpenRegister(ViMotionDef):
    """
    Vim: `"`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)

    def translate(self, state):
        return {}


@keys.assign(seq=seqs.GG, modes=_MODES_MOTION)
class ViGotoBof(ViMotionDef):
    """
    Vim: `gg`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}
        # cmd['is_jump'] = True

        if state.action_count or state.motion_count:
            cmd['motion'] = '_vi_go_to_line'
            cmd['motion_args'] = {'line': state.count, 'mode': state.mode}
            return cmd

        cmd['motion'] = '_vi_gg'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}
        return cmd


@keys.assign(seq=seqs.BIG_G, modes=_MODES_MOTION)
class ViGotoEof(ViMotionDef):
    """
    Vim: `G`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}

        if state.action_count or state.motion_count:
            cmd['motion'] = '_vi_go_to_line'
            cmd['motion_args'] = {'line': state.count, 'mode': state.mode}
        else:
            cmd['motion'] = '_vi_big_g'
            cmd['motion_args'] = {'mode': state.mode}

        return cmd


@keys.assign(seq=seqs.R, modes=_MODES_ACTION)
class ViReplaceCharacters(ViOperatorDef):
    """
    Vim: `r`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.repeatable = True

        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        translated = utils.translate_char(key)
        assert len(translated) == 1, '`r` only accepts a single char'
        self._inp = translated
        return True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_r'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'register': state.register,
                              'char': self.inp,
                              }
        return cmd


@keys.assign(seq=seqs.M, modes=_MODES_ACTION)
class ViSetMark(ViOperatorDef):
    """
    Vim: `m`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '`m` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_m'
        cmd['action_args'] = {'mode': state.mode,
                              'count': state.count,
                              'character': self.inp,
                              }
        return cmd


@keys.assign(seq=seqs.T, modes=_MODES_MOTION)
@keys.assign(seq=seqs.F, modes=_MODES_MOTION, inclusive=True)
class ViSearchCharForward(ViMotionDef):
    """
    Vim: `f`, `t`
    """

    def __init__(self, inclusive=False, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self._serializable.append('inclusive')
        self.scroll_into_view = True
        self.updates_xpos = True
        self.inclusive = inclusive
        self.input_parser = parser_def(command=inputs.one_char,
                                       interactive_command=None,
                                       input_param=None,
                                       on_done=None,
                                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        translated = utils.translate_char(key)
        assert len(translated) == 1, '`f`, `t`, `F`, `T` only accept a single char'
        self._inp = translated
        return True

    def translate(self, state):
        cmd = {}
        state.last_char_search_command = 'vi_f'
        state.last_character_search =  self.inp
        cmd['motion'] = '_vi_find_in_line'
        cmd['motion_args'] = {'char': self.inp,
                              'mode': state.mode,
                              'count': state.count,
                              'inclusive': self.inclusive,
                              }
        return cmd


@keys.assign(seq=seqs.A, modes=[modes.OPERATOR_PENDING,
                                modes.VISUAL,
                                modes.VISUAL_BLOCK])
class ViATextObject(ViMotionDef):
    """
    Vim: `a`
    """

    def __init__(self, inclusive=False, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.inclusive = inclusive

    # TODO: rename to "vi_a_text_object".
        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '`a` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_select_text_object'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'text_object': self.inp,
                              'inclusive': True,
                              }
        return cmd


@keys.assign(seq=seqs.I, modes=[modes.OPERATOR_PENDING,
                                modes.VISUAL,
                                modes.VISUAL_BLOCK])
class ViITextObject(ViMotionDef):
    """
    Vim: `i`
    """

    def __init__(self, inclusive=False, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self.inclusive = inclusive

        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        assert len(key) == 1, '`i` only accepts a single char'
        self._inp = key
        return True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_select_text_object'
        cmd['motion_args'] = {'mode': state.mode,
                              'count': state.count,
                              'text_object': self.inp,
                              'inclusive': False,
                              }
        return cmd


@keys.assign(seq=seqs.BIG_T, modes=_MODES_MOTION)
@keys.assign(seq=seqs.BIG_F, modes=_MODES_MOTION, inclusive=True)
class ViSearchCharBackward(ViMotionDef):
    """
    Vim: `T`, `F`
    """

    def __init__(self, inclusive=False, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self._serializable.append('inclusive')
        self.scroll_into_view = True
        self.updates_xpos = True
        self.inclusive = inclusive

        self.input_parser = parser_def(command=inputs.one_char,
                       interactive_command=None,
                       input_param=None,
                       on_done=None,
                       type=input_types.INMEDIATE)

    @property
    def accept_input(self):
        return self.inp == ''

    def accept(self, key):
        translated = utils.translate_char(key)
        assert len(translated) == 1, '`t` only accepts a single char'
        self._inp = translated
        return True

    def translate(self, state):
        cmd = {}
        state.last_char_search_command = 'vi_big_f'
        state.last_character_search = self.inp
        cmd['motion'] = '_vi_reverse_find_in_line'
        cmd['motion_args'] = {'char': self.inp,
                              'mode': state.mode,
                              'count': state.count,
                              'inclusive': self.inclusive,
                              }
        return cmd


@keys.assign(seq=seqs.SLASH, modes=_MODES_MOTION)
class ViSearchForward(ViMotionDef):
    """
    Vim: `/`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

        self.input_parser = parser_def(command='_vi_slash',
                                       interactive_command='_vi_slash',
                                       type=input_types.VIA_PANEL,
                                       on_done=None,
                                       input_param='default')

    @property
    def accept_input(self):
        if not self.inp:
            return True
        return not self.inp.lower().endswith('<cr>')

    def accept(self, key):
        self._inp += key
        return True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_slash'
        cmd['motion_args'] = {}

        return cmd


class ViSearchForwardImpl(ViMotionDef):
    """
    Vim: --
    """

    def __init__(self, *args, term='', **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self._inp = term
        self.updates_xpos = True

    def translate(self, state):
        if not self.inp:
            self._inp = state.last_buffer_search
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_slash_impl'
        cmd['motion_args'] = {'search_string': self.inp,
                              'mode': state.mode,
                              'count': state.count,
                              }

        return cmd


@keys.assign(seq=seqs.QUESTION_MARK, modes=_MODES_MOTION)
class ViSearchBackward(ViMotionDef):
    """
    Vim: `?`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

        self.input_parser = parser_def(command='_vi_question_mark',
                                       interactive_command='_vi_question_mark',
                                       type=input_types.VIA_PANEL,
                                       on_done=None,
                                       input_param='default')

    @property
    def accept_input(self):
        if not self.inp:
            return True
        return not self.inp.lower().endswith('<cr>')

    def accept(self, key):
        self._inp += key
        return True

    def translate(self, state):
        cmd = {}
        cmd['motion'] = '_vi_question_mark'
        cmd['motion_args'] = {}
        return cmd


class ViSearchBackwardImpl(ViMotionDef):
    """
    Vim: --
    """

    def __init__(self, *args, term='', **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True
        self._inp = term

    def translate(self, state):
        if not self.inp:
            self._inp = state.last_buffer_search
        cmd = {}
        cmd['is_jump'] = True
        cmd['motion'] = '_vi_question_mark_impl'
        cmd['motion_args'] = {'search_string': self.inp,
                              'mode': state.mode,
                              'count': state.count,
                              }
        return cmd


@keys.assign(seq=seqs.CTRL_X_CTRL_L, modes=[modes.INSERT])
class ViInsertLineWithCommonPrefix(ViOperatorDef):
    """
    Vim: `i_CTRL_X_CTRL_L`
    """

    def __init__(self, *args, **kwargs):
        ViOperatorDef.__init__(self, *args, **kwargs)
        self.scroll_into_view = True
        self.updates_xpos = True

    def translate(self, state):
        cmd = {}
        cmd['action'] = '_vi_ctrl_x_ctrl_l'
        cmd['action_args'] = {'mode': state.mode,
                              'register': state.register,
                              }
        return cmd


@keys.assign(seq=seqs.GM, modes=_MODES_MOTION)
class ViMoveHalfScreenHorizontally(ViMotionDef):
    """
    Vim: `gm`
    """

    def __init__(self, *args, **kwargs):
        ViMotionDef.__init__(self, *args, **kwargs)
        self.updates_xpos = True
        self.scroll_into_view = True

    def translate(self, state):
        cmd = {}

        cmd['motion'] = '_vi_gm'
        cmd['motion_args'] = {'mode': state.mode, 'count': state.count}
        return cmd

########NEW FILE########
__FILENAME__ = constants
# TODO: This module exists solely for retrocompatibility. Delete when possible.

from Vintageous.vi.utils import modes

MODE_INSERT = modes.INSERT
MODE_NORMAL = modes.NORMAL
MODE_VISUAL = modes.VISUAL
MODE_VISUAL_LINE = modes.VISUAL_LINE
# The mode you enter when giving i a count.
MODE_NORMAL_INSERT = modes.NORMAL_INSERT
# Vintageous always runs actions based on selections. Some Vim commands,
# however, behave differently depending on whether the current mode is NORMAL
# or VISUAL. To differentiate NORMAL mode operations (involving only an
# action, or a motion plus an action) from VISUAL mode, we need to add an
# additional mode for handling selections that won't interfere with the actual
# VISUAL mode.
#
# This is _MODE_INTERNAL_NORMAL's job. We consider _MODE_INTERNAL_NORMAL a
# pseudomode, because global state's .mode property should never set to it,
# yet it's set in vi_cmd_data often.
#
# Note that for pure motions we still use plain NORMAL mode.
_MODE_INTERNAL_NORMAL = modes.INTERNAL_NORMAL
MODE_REPLACE = modes.REPLACE
MODE_SELECT = modes.SELECT
MODE_VISUAL_BLOCK = modes.VISUAL_BLOCK


def regions_transformer_reversed(view, f):
    """
    Applies ``f`` to every selection region in ``view`` and replaces the
    existing selections.
    """
    sels = reversed(list(view.sel()))

    new_sels = []
    for s in sels:
        new_sels.append(f(view, s))

    view.sel().clear()
    for ns in new_sels:
        view.sel().add(ns)

########NEW FILE########
__FILENAME__ = contexts
import sublime

# from Vintageous.vi.constants import MODE_NORMAL, MODE_NORMAL_INSERT, MODE_INSERT, ACTIONS_EXITING_TO_INSERT_MODE, MODE_VISUAL_LINE, MODE_VISUAL, MODE_SELECT
# from Vintageous.vi.constants import MODE_VISUAL_BLOCK
from Vintageous.vi.utils import modes
# from Vintageous.vi import constants
from Vintageous.vi import utils
# from Vintageous.vi.constants import action_to_namespace


class KeyContext(object):
    def __get__(self, instance, owner):
        self.state = instance
        return self

    # def vi_must_change_mode(self, key, operator, operand, match_all):
    #     is_normal_mode = self.state.settings.view['command_mode']
    #     is_exit_mode_insert = (self.state.action in ACTIONS_EXITING_TO_INSERT_MODE)
    #     if (is_normal_mode and is_exit_mode_insert):
    #         return self._check(True, operator, operand, match_all)

    #     # Close the ':' panel.
    #     if self.vi_is_cmdline(key, operator, operand, match_all):
    #         # We return False so that vi_esc will be skipped and the default Sublime Text command
    #         # will be triggered instead. When the input panel finally closes, the initialization
    #         # code in state.py will take care of clearing the state so we are left in a consistent
    #         # state.
    #         return False

    #     # If we have primed counts, we have to clear the state.
    #     if self.state.user_provided_count or self.state.motion or self.state.action:
    #         return True

    #     # TODO: Simplify comparisons.
    #     if self.state.mode == MODE_NORMAL_INSERT:
    #         return True

    #     if self.state.mode == MODE_INSERT:
    #         return True

    #     # check if we are NOT in normal mode -- if NOT, we need to change modes
    #     # This covers, for example, SELECT_MODE.
    #     if self.state.mode != MODE_NORMAL:
    #         return True

    #     # Clear non-empty selections if there any.
    #     # For example, this will be the case when we've used select mode (gh).
    #     if not all(r.empty() for r in self.state.view.sel()):
    #         return True

    #     # XXX Actually, if we already are in normal mode, we still need to perform certain
    #     # cleanup tasks, so let the command run anyway.
    #     if self.state.view.get_regions('vi_search'):
    #         return True
    def vi_is_view(self, key, operator, operand, match_all):
        value = utils.is_view(self.state.view)
        return self._check(value, operator, operand, match_all)

    # def vi_must_exit_to_insert_mode(self, key, operator, operand, match_all):
    #     # XXX: This conext most likely not needed any more.
    #     is_normal_mode = self.state.settings.view['command_mode']
    #     is_exit_mode_insert = (self.state.action in ACTIONS_EXITING_TO_INSERT_MODE)
    #     value = (is_normal_mode and is_exit_mode_insert)
    #     return self._check(value, operator, operand, match_all)

    def vi_command_mode_aware(self, key, operator, operand, match_all):
        in_command_mode = self.state.view.settings().get('command_mode')
        is_view = self.vi_is_view(key, operator, operand, match_all)
        value = in_command_mode and is_view
        return self._check(value, operator, operand, match_all)

    def vi_insert_mode_aware(self, key, operator, operand, match_all):
        in_command_mode = self.state.view.settings().get('command_mode')
        is_view = self.vi_is_view(key, operator, operand, match_all)
        value = (not in_command_mode) and is_view
        return self._check(value, operator, operand, match_all)

    def vi_use_ctrl_keys(self, key, operator, operand, match_all):
        value = self.state.settings.view['vintageous_use_ctrl_keys']
        return self._check(value, operator, operand, match_all)

    def vi_is_cmdline(self, key, operator, operand, match_all):
        value = (self.state.view.score_selector(0, 'text.excmdline') != 0)
        return self._check(value, operator, operand, match_all)

    def vi_enable_cmdline_mode(self, key, operator, operand, match_all):
        value = self.state.settings.view['vintageous_enable_cmdline_mode']
        return self._check(value, operator, operand, match_all)

    # def vi_has_incomplete_action(self, key, operator, operand, match_all):
    #     value = any(x for x in (self.state.action, self.state.motion) if
    #                       x in constants.INCOMPLETE_ACTIONS)
    #     return self._check(value, operator, operand, match_all)

    # def vi_has_action(self, key, operator, operand, match_all):
        # value = self.state.action
        # value = value and (value not in constants.INCOMPLETE_ACTIONS)
        # return self._check(value, operator, operand, match_all)

    # def vi_has_motion_count(self, key, operator, operand, match_all):
        # value = self.state.motion_digits
        # return self._check(value, operator, operand, match_all)

    def vi_mode_normal_insert(self, key, operator, operand, match_all):
        value = self.state.mode == modes.NORMAL_INSERT
        return self._check(value, operator, operand, match_all)

    def vi_mode_visual_block(self, key, operator, operand, match_all):
        value = self.state.mode == modes.VISUAL_BLOCK
        return self._check(value, operator, operand, match_all)

    # def vi_mode_cannot_push_zero(self, key, operator, operand, match_all):
        # value = False
        # if operator == sublime.OP_EQUAL:
            # value = not (self.state.motion_digits or
                             # self.state.action_digits)

        # return self._check(value, operator, operand, match_all)

    # def vi_mode_visual_any(self, key, operator, operand, match_all):
    #     value = self.state.mode in (moces.VISUAL_LINE, modes.VIUSAL, modes.VISUAL_BLOCK)
    #     return self._check(value, operator, operand, match_all)

    def vi_mode_select(self, key, operator, operand, match_all):
        value = self.state.mode == modes.SELECT
        return self._check(value, operator, operand, match_all)

    def vi_mode_visual_line(self, key, operator, operand, match_all):
        value = self.state.mode == modes.VISUAL_LINE
        return self._check(value, operator, operand, match_all)

    def vi_mode_insert(self, key, operator, operand, match_all):
        value = self.state.mode == modes.INSERT
        return self._check(value, operator, operand, match_all)

    def vi_mode_visual(self, key, operator, operand, match_all):
        value = self.state.mode == modes.VISUAL
        return self._check(value, operator, operand, match_all)

    def vi_mode_normal(self, key, operator, operand, match_all):
        value = self.state.mode == modes.NORMAL
        return self._check(value, operator, operand, match_all)

    def vi_mode_normal_or_visual(self, key, operator, operand, match_all):
        # XXX: This context is used to disable some keys for VISUALLINE.
        # However, this is hiding some problems in visual transformers that might not be dealing
        # correctly with VISUALLINE.
        normal = self.vi_mode_normal(key, operator, operand, match_all)
        visual = self.vi_mode_visual(key, operator, operand, match_all)
        visual = visual or self.vi_mode_visual_block(key, operator, operand, match_all)
        return self._check((normal or visual), operator, operand, match_all)

    def vi_mode_normal_or_any_visual(self, key, operator, operand, match_all):
        normal_or_visual = self.vi_mode_normal_or_visual(key, operator, operand, match_all)
        visual_line = self.vi_mode_visual_line(key, operator, operand, match_all)
        return self._check((normal_or_visual or visual_line), operator, operand, match_all)

    # def vi_state_next_character_is_user_input(self, key, operator, operand, match_all):
        # value = (self.state.expecting_user_input or
                 # self.state.expecting_register)
        # return self._check(value, operator, operand, match_all)

    # def vi_state_expecting_user_input(self, key, operator, operand, match_all):
        # value = self.state.expecting_user_input
        # return self._check(value, operator, operand, match_all)

    # def vi_state_expecting_register(self, key, operator, operand, match_all):
        # value = self.state.expecting_register
        # return self._check(value, operator, operand, match_all)

    # def vi_mode_can_push_digit(self, key, operator, operand, match_all):
        # motion_digits = not self.state.motion
        # action_digits = self.state.motion
        # value = motion_digits or action_digits
        # return self._check(value, operator, operand, match_all)

    # def vi_is_recording_macro(self, key, operator, operand, match_all):
        # value = self.state.is_recording
        # return self._check(value, operator, operand, match_all)

    # def vi_in_key_namespace(self, key, operator, operand, match_all):
        # has_incomplete_action = self.vi_has_incomplete_action('vi_has_incomplete_action', sublime.OP_EQUAL, True, False)
        # if not has_incomplete_action:
            # return False

        # value = action_to_namespace(self.state.action) or action_to_namespace(self.state.motion)
        # if not value:
            # return False
        # value = value == operand
        # return value
        # return self._check(value, operator, True, match_all)

    # def vi_can_enter_any_visual_mode(self, key, operator, operand, match_all):
    #     sels = self.state.view.sel()
    #     rv = True
    #     for sel in sels:
    #         # We're assuming we are in normal mode.
    #         if sel.b == self.state.view.size() and self.state.view.line(sel.b).empty():
    #             rv = False
    #             break

    #     if not rv:
    #         print("Vintageous: Can't enter visual mode at EOF if last line is empty.")
    #         utils.blink()

    #     return self._check(rv, operator, operand, match_all)

    def check(self, key, operator, operand, match_all):
        func = getattr(self, key, None)
        if func:
            return func(key, operator, operand, match_all)
        else:
            return None

    def _check(self, value, operator, operand, match_all):
        if operator == sublime.OP_EQUAL:
            if operand == True:
                return value
            elif operand == False:
                return not value
        elif operator == sublime.OP_NOT_EQUAL:
            if operand == True:
                return not value
            elif operand == False:
                return value

########NEW FILE########
__FILENAME__ = core
import sublime
import sublime_plugin

from Vintageous.state import State
from Vintageous.vi.utils import IrreversibleTextCommand


class ViTextCommandBase(sublime_plugin.TextCommand):
    """
    Base class form motion and action commands.

    Not all commands need to derive from this base class, but it's
    recommended they do if there isn't any good reason they shouldn't.
    """

    # Yank config data is controlled through class attributes. ===============
    _can_yank = False
    _synthetize_new_line_at_eof = False
    _yanks_linewise = False
    _populates_small_delete_register = False
    #=========================================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def state(self):
        return State(self.view)

    def save_sel(self):
        """
        Saves the current .sel() for later reference.
        """
        self.old_sel = tuple(self.view.sel())

    def is_equal_to_old_sel(self, new_sel):
        try:
            return (tuple((s.a, s.b) for s in self.old_sel) ==
                    tuple((s.a, s.b) for s in tuple(self.view.sel())))
        except AttributeError:
            raise AttributeError('have you forgotten to call .save_sel()?')

    def has_sel_changed(self):
        """
        `True` is the current selection is different to .old_sel as recorded
        by .save_sel().
        """
        return not self.is_equal_to_old_sel(self.view.sel())

    def enter_normal_mode(self, mode):
        """
        Calls the command to enter normal mode.

        @mode: The mode the state was in before calling this method.
        """
        self.view.window().run_command('_enter_normal_mode', {'mode': mode})

    def enter_insert_mode(self, mode):
        """
        Calls the command to enter normal mode.

        @mode: The mode the state was in before calling this method.
        """
        self.view.window().run_command('_enter_insert_mode', {'mode': mode})

    def set_xpos(self, state):
        try:
            xpos = self.view.rowcol(self.view.sel()[0].b)[1]
        except Exception as e:
            print(e)
            raise ValueError('could not set xpos')

        state.xpos = xpos

    def outline_target(self):
        sels = list(self.view.sel())
        sublime.set_timeout(lambda: self.view.erase_regions('vi_training_wheels'), 350)
        self.view.add_regions('vi_training_wheels', sels, 'comment', '', sublime.DRAW_NO_FILL)


class ViMotionCommand(ViTextCommandBase, IrreversibleTextCommand):
    """
    Motions should bypass the undo stack.
    """
    pass


class ViWindowCommandBase(sublime_plugin.WindowCommand):
    """
    Base class form some window commands.

    Not all window commands need to derive from this base class, but it's
    recommended they do if there isn't any good reason they shouldn't.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def state(self):
        return State(self.window.active_view())

########NEW FILE########
__FILENAME__ = dot_file
from Vintageous.vi.utils import get_logger

import sublime

import os


class DotFile(object):
    def __init__(self, path):
        self.path = path
        self.logger = get_logger()

    @staticmethod
    def from_user():
        path = os.path.join(sublime.packages_path(), 'User', '.vintageousrc')
        return DotFile(path)

    def run(self):
        try:
            with open(self.path, 'r') as f:
                for line in f:
                    cmd, args = self.parse(line)
                    if cmd:
                        self.logger.info('[DotFile] running: {0} {1}'.format(cmd, args))
                        sublime.active_window().run_command(cmd, args)
        except FileNotFoundError:
            pass

    def parse(self, line):
        self.logger.info('[DotFile] parsing line: {0}'.format(line))
        if line.startswith((':map ')):
            line = line[len(':map '):]
            return ('ex_map', {'cmd': line.rstrip()})

        if line.startswith((':omap ')):
            line = line[len(':omap '):]
            return ('ex_omap', {'cmd': line.rstrip()})

        if line.startswith((':vmap ')):
            line = line[len(':vmap '):]
            return ('ex_vmap', {'cmd': line.rstrip()})

########NEW FILE########
__FILENAME__ = extend
"""This module provides basic extensibility hooks for external plugins.
"""

from Vintageous.vi.constants import INPUT_FOR_ACTIONS

class PluginManager(object):
    """Collects information from external plugins and manages it.
    """
    def __init__(self):
        self.actions = {}
        # See vi/constants.py (digraphs).
        self.composite_commands = {}
        # See vi/constants.py (INPUT_FOR_MOTIONS)
        self.motion_input_parsers = {}
        # See vi/constants.py (INPUT_FOR_ACTIONS)
        self.action_input_parsers = {}

    # Must be used as a decorator.
    def register_action(self, f):
        self.actions[f.__name__] = f
        return f

    def register_composite_command(self, cc):
        self.composite_commands.update(cc)

    def register_motion_input_parser(self, ip):
        self.motion_input_parsers.update(ip)

    def register_action_input_parser(self, ip):
        INPUT_FOR_ACTIONS.update(ip)
        # self.action_input_parsers.update(ip)

# def plugin_loaded():
#     global plugin_manager
#     plugin_manager = PluginManager()

########NEW FILE########
__FILENAME__ = inputs
from collections import namedtuple

from Vintageous.vi.utils import input_types
from Vintageous.vi import utils


parser_def = namedtuple('parsed_def', 'command interactive_command input_param on_done type')


def get(state, name):
    parser_func = globals().get(name, None)
    if parser_func is None:
        raise ValueError('parser name unknown')
    return parser_func(state)


def one_char(in_):
    """
    Any input (character) satisfies this parser.
    """
    in_ = utils.translate_char(in_)
    return len(in_) == 1


def vi_f(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_big_f(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_big_t(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_t(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


# TODO: rename to "vi_a_text_object".
def vi_inclusive_text_object(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_exclusive_text_object(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_m(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_q(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_at(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_a_text_object(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_i_text_object(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_quote(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p

def vi_r(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done='_vi_r_on_parser_done',
                   type=input_types.INMEDIATE)
    return p
def vi_backtick(state):
    p = parser_def(command=one_char,
                   interactive_command=None,
                   input_param=None,
                   on_done=None,
                   type=input_types.INMEDIATE)
    return p


def vi_slash(state):
    """
    This parse should always be used non-interactively. / usually collects
    its input from an input panel.
    """
    # Any input is valid; we're never satisfied.
    if state.non_interactive:
        return parser_def(command=lambda x: False,
                          interactive_command='_vi_slash',
                          type=input_types.INMEDIATE,
                          on_done='_vi_slash_on_parser_done',
                          input_param='key')
    else:
        return parser_def(command='_vi_slash',
                          interactive_command='_vi_slash',
                          type=input_types.VIA_PANEL,
                          on_done=None,
                          input_param='default')


def vi_question_mark(state):
    """
    This parser should always be used non-interactively. ? usually collects
    its input from an input panel.
    """
    # Any input is valid; we're never satisfied.
    if state.non_interactive:
        return parser_def(command=lambda x: False,
                          interactive_command='_vi_question_mark',
                          type=input_types.INMEDIATE,
                          on_done='_vi_question_mark_on_parser_done',
                          input_param='key')
    else:
        return parser_def(command='_vi_question_mark',
                          interactive_command='_vi_question_mark',
                          type=input_types.VIA_PANEL,
                          on_done=None,
                          input_param='default')

########NEW FILE########
__FILENAME__ = jump_list
_jump_list = []
_jump_list_index = -1
_current_latest = 1


class JumpList(object):
    def __init__(self, state):
        self.state = state

    def add(self, data):
        # data: [filename, line, column, length]
        # FIXME: This is probably very slow; use a different data structure (???).
        _jump_list.insert(0, data)

        if len(_jump_list) > 100:
            _jump_list.pop()

    def reset(self):
        _jump_list_index = -1
        _jump_list = []

    @property
    def previous(self):
        try:
            idx = _jump_list_index
            next_index = idx + 1
            if next_index > 100:
                next_index = 100
            next_index = min(len(_jump_list) - 1, next_index)
            _jump_list_index = next_index
            return _jump_list[next_index]
        except (IndexError, KeyError) as e:
            return None

    @property
    def next(self):
        try:
            idx = _jump_list_index
            next_index = idx - 1
            if next_index < 0:
                next_index = 0
            next_index = min(len(_jump_list) - 1, next_index)
            _jump_list_index = next_index
            return _jump_list[next_index]
        except (IndexError, KeyError) as e:
            return None

    @property
    def latest(self):
        global _current_latest
        try:
            i = 1 if (_current_latest == 0) else 0
            _current_latest = min(len(_jump_list) - 1, i)
            return _jump_list[_current_latest]
        except (IndexError, KeyError) as e:
            return None

########NEW FILE########
__FILENAME__ = keys
import re

from Vintageous import local_logger
from Vintageous.vi.utils import modes
from Vintageous.vi import cmd_base
from Vintageous.plugins import plugins


_logger = local_logger(__name__)


class mapping_scopes:
    """
    Scopes for mappings.
    """
    DEFAULT =      0
    USER =         1
    PLUGIN =       2
    NAME_SPACE =   3
    LEADER =       4
    LOCAL_LEADER = 5


class seqs:
    """
    Vim's built-in key sequences plus Sublime Text 3 staple commands.

    These are the sequences of key presses known to Vintageous. Any other
    sequence pressed will be treated as 'unmapped'.
    """

    A =                            'a'
    ALT_CTRL_P =                   '<C-M-p>'
    AMPERSAND =                    '&'
    AW =                           'aw'
    B =                            'b'
    BACKSPACE =                    '<bs>'
    GE =                           'ge'
    G_BIG_E =                      'gE'
    UP =                           '<up>'
    DOWN =                         '<down>'
    LEFT =                         '<left>'
    RIGHT =                        '<right>'
    HOME =                         '<home>'
    END =                          '<end>'
    BACKTICK =                     '`'
    BIG_A =                        'A'
    SPACE =                        '<space>'
    BIG_B =                        'B'
    CTRL_E =                       '<C-e>'
    CTRL_Y =                       '<C-y>'
    BIG_C =                        'C'
    BIG_D =                        'D'
    GH =                           'gh'
    G_BIG_H =                      'gH'
    BIG_E =                        'E'
    BIG_F =                        'F'
    BIG_G =                        'G'
    CTRL_W =                       '<C-w>'
    CTRL_W_Q =                     '<C-w>q'

    CTRL_W_V =                     '<C-w>v'
    CTRL_W_L =                     '<C-w>l'
    CTRL_W_BIG_L =                 '<C-w>L'
    CTRL_K =                       '<C-k>'
    CTRL_K_CTRL_B =                '<C-k><C-b>'
    CTRL_BIG_F =                   '<C-F>'
    CTRL_BIG_P =                   '<C-P>'
    CTRL_W_H =                     '<C-w>h'
    CTRL_X =                       '<C-x>'
    CTRL_X_CTRL_L =                '<C-x><C-l>'
    Q =                            'q'
    AT =                           '@'
    CTRL_W_BIG_H =                 '<C-w>H'
    BIG_H =                        'H'

    G_BIG_J =                      'gJ'
    CTRL_R=                        '<C-r>'
    CTRL_R_EQUAL =                 '<C-r>='
    CTRL_A =                       '<C-a>'
    CTRL_I =                       '<C-i>'
    CTRL_O =                       '<C-o>'
    CTRL_X =                       '<C-x>'
    Z =                            'z'
    Z_ENTER =                      'z<cr>'
    ZT =                           'zt'
    ZZ =                           'zz'
    Z_MINUS =                      'z-'
    ZB =                           'zb'

    BIG_I =                        'I'
    BIG_Z_BIG_Z =                  'ZZ'
    BIG_Z_BIG_Q =                  'ZQ'
    GV =                           'gv'
    BIG_J =                        'J'
    BIG_K =                        'K'
    BIG_L =                        'L'
    BIG_M =                        'M'
    BIG_N =                        'N'
    BIG_O =                        'O'
    BIG_P =                        'P'
    BIG_Q =                        'Q'
    BIG_R =                        'R'
    BIG_S =                        'S'
    BIG_T =                        'T'
    BIG_U =                        'U'
    BIG_V =                        'V'
    BIG_W =                        'W'
    BIG_X =                        'X'
    BIG_Y =                        'Y'
    BIG_Z =                        'Z'
    C =                            'c'
    CC =                           'cc'
    COLON =                        ':'
    COMMA =                        ','
    CTRL_D =                       '<C-d>'
    CTRL_F12 =                     '<C-f12>'
    CTRL_L =                       '<C-l>'
    CTRL_B =                       '<C-b>'
    CTRL_F =                       '<C-f>'
    CTRL_G =                       '<C-g>'
    CTRL_P =                       '<C-p>'
    CTRL_U =                       '<C-u>'
    CTRL_V =                       '<C-v>'
    D =                            'd'
    DD =                           'dd'
    DOLLAR =                       '$'
    DOT =                          '.'
    DOUBLE_QUOTE =                 '"'
    E =                            'e'
    ENTER =                        '<cr>' # Or rather <Enter>?
    SHIFT_ENTER =                  '<S-cr>'
    EQUAL =                        '='
    EQUAL_EQUAL =                  '=='
    ESC =                          '<esc>'
    F =                            'f'
    F1 =                           '<f1>'
    F10 =                          '<f10>'
    F11 =                          '<f11>'
    F12 =                          '<f12>'
    F13 =                          '<f13>'
    F14 =                          '<f14>'
    F15 =                          '<f15>'
    F2 =                           '<f2>'
    F3 =                           '<f3>'
    SHIFT_F2 =                     '<S-f2>'
    SHIFT_F3 =                     '<S-f3>'
    SHIFT_F4 =                     '<S-f4>'
    F4 =                           '<f4>'
    F5 =                           '<f5>'
    F6 =                           '<f6>'
    F7 =                           '<f7>'
    F8 =                           '<f8>'
    F9 =                           '<f9>'
    CTRL_F2 =                      '<C-f2>'
    CTRL_SHIFT_F2 =                '<C-S-f2>'
    G =                            'g'
    G_BIG_D =                      'gD'
    G_BIG_U =                      'gU'
    G_BIG_U_BIG_U =                'gUU'
    G_BIG_U_G_BIG_U =              'gUgU'
    G_TILDE =                      'g~'
    G_TILDE_G_TILDE =              'g~g~'
    G_TILDE_TILDE =                'g~~'
    G_UNDERSCORE =                 'g_'
    GD =                           'gd'
    GG =                           'gg'
    GJ =                           'gj'
    GK =                           'gk'
    GQ =                           'gq'
    GT =                           'gt'
    G_BIG_T =                      'gT'
    GM =                           'gm'
    GU =                           'gu'
    GUGU =                         'gugu'
    GUU =                          'guu'
    GREATER_THAN =                 '>'
    GREATER_THAN_GREATER_THAN =    '>>'
    H =                            'h'
    HAT =                          '^'
    I =                            'i'
    J =                            'j'
    K =                            'k'
    L =                            'l'
    LEFT_BRACE =                   '{'
    LEFT_SQUARE_BRACKET =          '['
    LEFT_PAREN =                   '('
    LESS_THAN =                    '<lt>'
    LESS_THAN_LESS_THAN =          '<lt><lt>'
    M =                            'm'
    N =                            'n'
    O =                            'o'
    P =                            'p'
    OCTOTHORP =                    '#'
    PAGE_DOWN =                    'pagedown'
    PAGE_UP =                      'pageup'
    PERCENT =                      '%'
    PIPE =                         '|'
    QUESTION_MARK =                '?'
    QUOTE =                        "'"
    QUOTE_QUOTE =                  "''"
    R =                            'r'
    RIGHT_BRACE =                  '}'
    RIGHT_SQUARE_BRACKET =         ']'
    RIGHT_PAREN =                  ')'
    S =                            's'
    SEMICOLON =                    ';'
    SHIFT_CTRL_F12 =               '<C-S-f12>'
    SLASH =                        '/'
    STAR =                         '*'
    T =                            't'
    TAB =                          '<tab>'
    TILDE =                        '~'
    U =                            'u'
    UNDERSCORE =                   '_'
    V =                            'v'
    W =                            'w'
    X =                            'x'
    Y =                            'y'
    YY =                           'yy'
    ZERO =                         '0'


def seq_to_command(state, seq, mode=None):
    """
    Returns the command definition mapped to @seq, or a 'missing' command
    if none is found.

    @mode
        Forces the use of this mode instead of the global state's.
    """
    mode = mode or state.mode

    _logger().info('[seq_to_command] state/seq: {0}/{1}'.format(mode, seq))

    command = None

    if state.mode in plugins.mappings:
        command = plugins.mappings[mode].get(seq, None)

    if not command and state.mode in mappings:
        command = mappings[mode].get(seq, cmd_base.ViMissingCommandDef())
        return command
    elif command:
        return command

    return cmd_base.ViMissingCommandDef()


# Mappings 'key sequence' ==> 'command definition'
#
# 'key sequence' is a sequence of key presses.
#
mappings = {
    modes.INSERT: {},
    modes.NORMAL: {},
    modes.VISUAL: {},
    modes.OPERATOR_PENDING: {},
    modes.VISUAL_LINE: {},
    modes.VISUAL_BLOCK: {},
    modes.SELECT: {},
    '_missing':  dict(name='_missing')
}


# TODO: Add a timeout for ambiguous cmd_base.
# Key sequence to command mapping. Mappings are set by the user.
#
# Returns a partial definition containing the user-pressed keys so that we
# can replay the command exactly as it was typed in.
user_mappings = {
    # 'jkl': dict(name='dd', type=cmd_types.USER),
}


EOF = -2

class key_names:
    """
    Names of special keys.
    """
    BACKSPACE   = '<bs>'
    CR          = '<cr>'
    DOWN        = '<down>'
    END         = '<end>'
    ENTER       = '<enter>'
    ESC         = '<esc>'
    HOME        = '<home>'
    LEFT        = '<left>'
    LESS_THAN   = '<lt>'
    RIGHT       = '<right>'
    SPACE       = '<sp>'
    SPACE_LONG  = '<space>'
    TAB         = '<tab>'
    UP          = '<up>'

    F1          = '<f1>'
    F2          = '<f2>'
    F3          = '<f3>'
    F4          = '<f4>'
    F5          = '<f5>'
    F6          = '<f6>'
    F7          = '<f7>'
    F8          = '<f8>'
    F9          = '<f9>'
    F10         = '<f10>'
    F11         = '<f11>'
    F12         = '<f12>'
    F13         = '<f13>'
    F14         = '<f14>'
    F15         = '<f15>'

    as_list = [
        BACKSPACE,
        CR,
        DOWN,
        END,
        ENTER,
        ESC,
        HOME,
        LEFT,
        LESS_THAN,
        RIGHT,
        SPACE,
        SPACE_LONG,
        TAB,
        UP,

        F1,
        F2,
        F3,
        F4,
        F5,
        F6,
        F7,
        F8,
        F9,
        F10,
        F11,
        F12,
        F13,
        F14,
        F15,
    ]

    max_len = len('<space>')


# TODO: detect counts, registers, marks...
class KeySequenceTokenizer(object):
    """
    Takes in a sequence of key names and tokenizes it.
    """
    def __init__(self, source):
        """
        @source
          A sequence of key names in Vim notation.
        """
        self.idx = -1
        self.source = source
        self.in_named_key = False

    def consume(self):
        self.idx += 1
        if self.idx >= len(self.source):
            self.idx -= -1
            return EOF
        return self.source[self.idx]

    def peek_one(self):
        if (self.idx + 1) >= len(self.source):
            return EOF
        return self.source[self.idx + 1]

    def is_named_key(self, key):
        return key.lower() in key_names.as_list

    def sort_modifiers(self, modifiers):
        """
        Ensures consistency in the order of modifier letters according to:

          c > m > s
        """
        if len(modifiers) == 6:
            modifiers = 'c-m-s-'
        elif len(modifiers) > 2:
            if modifiers.startswith('s-') and modifiers.endswith('c-'):
                modifiers = 'c-s-'
            elif modifiers.startswith('s-') and modifiers.endswith('m-'):
                modifiers = 'm-s-'
            elif modifiers.startswith('m-') and modifiers.endswith('c-'):
                modifiers = 'c-m-'
        return modifiers

    def long_key_name(self):
        self.in_named_key = True
        key_name = ''
        modifiers = ''

        while True:
            c = self.consume()

            if c == EOF:
                raise ValueError("expected '>' at index {0}".format(self.idx))

            elif (c.lower() in ('c', 's', 'm')) and (self.peek_one() == '-'):
                if c.lower() in modifiers.lower():
                    raise ValueError('invalid modifier sequence: {0}'.format(self.source))

                modifiers += c + self.consume()

            elif c == '>' and self.peek_one() == '>':
                modifiers = self.sort_modifiers(modifiers.lower())

                if len(key_name) == 0:
                    return '<' + modifiers.upper() + self.consume() + '>'

                else:
                    raise ValueError('wrong key {0}'.format(key_name))

            elif c == '>':
                modifiers = self.sort_modifiers(modifiers.lower())

                if len(key_name) == 1:
                    if not modifiers:
                        raise ValueError('wrong sequence {0}'.format(self.source))
                    return '<' + modifiers.upper() + key_name + '>'

                elif self.is_named_key('<' + key_name + '>'):
                    self.in_named_key = False
                    return '<' + modifiers.upper() + key_name.lower() + '>'

                else:
                    raise ValueError("'{0}' is not a known key".format(key_name))

            else:
                key_name += c

    def tokenize_one(self):
        c = self.consume()

        if c == '<':
            return self.long_key_name()
        else:
            return c

    def iter_tokenize(self):
        while True:
            token = self.tokenize_one()
            if token == EOF:
                break
            yield token


def to_bare_command_name(seq):
    """
    Strips register and count data from @seq.
    """
    # Special case.
    if seq == '0':
        return seq

    new_seq = re.sub(r'^(?:".)?(?:[1-9]+)?', '', seq)
    # Account for d2d and similar sequences.
    new_seq = list(KeySequenceTokenizer(new_seq).iter_tokenize())

    return ''.join(k for k in new_seq if not k.isdigit())


def assign(seq, modes, *args, **kwargs):
    """
    Registers a 'key sequence' to 'command' mapping with Vintageous.

    The registered key sequence must be known to Vintageous. The
    registered command must be a ViMotionDef or ViOperatorDef.

    The decorated class is instantiated with `*args` and `**kwargs`.

    @keys
      A list of (`mode:tuple`, `sequence:string`) pairs to map the decorated
      class to.
    """
    def inner(cls):
        for mode in modes:
            mappings[mode][seq] = cls(*args, **kwargs)
        return cls
    return inner

########NEW FILE########
__FILENAME__ = macros

########NEW FILE########
__FILENAME__ = mappings
from Vintageous.vi import utils
from Vintageous.vi.keys import mappings
from Vintageous.vi.keys import seq_to_command
from Vintageous.vi.keys import to_bare_command_name
from Vintageous.vi.keys import KeySequenceTokenizer
from Vintageous.vi.utils import modes
from Vintageous.vi.cmd_base import cmd_types


_mappings = {
    modes.INSERT: {},
    modes.NORMAL: {},
    modes.VISUAL: {},
    modes.VISUAL_LINE: {},
    modes.OPERATOR_PENDING: {},
    modes.VISUAL_BLOCK: {},
    modes.SELECT: {},
}


class mapping_status:
    INCOMPLETE = 1
    COMPLETE = 2


class Mapping(object):
    def __init__(self, head, mapping, tail, status):
        self.mapping = mapping
        self.head = head
        self.tail = tail
        self.status = status

    @property
    def sequence(self):
        try:
            return self.head + self.tail
        except TypeError:
            raise ValueError('no mapping found')


class Mappings(object):
    def __init__(self, state):
        self.state = state

    def _get_mapped_seqs(self, mode):
        return sorted(_mappings[mode].keys())

    def _find_partial_match(self, mode, seq):
        return list(x for x in self._get_mapped_seqs(mode)
                            if x.startswith(seq))

    def _find_full_match(self, mode, seq):
        partials = self._find_partial_match(mode, seq)
        try:
            self.state.logger.info("[Mappings] checking partials {0} for {1}".format(partials, seq))
            name = list(x for x in partials if x == seq)[0]
            return (name, _mappings[mode][name])
        except IndexError:
            return (None, None)

    def expand(self, seq):
        pass

    def expand_first(self, seq):
        head = ''

        keys, mapped_to = self._find_full_match(self.state.mode, seq)
        if keys:
            self.state.logger.info("[Mappings] found full command: {0} -> {1}".format(keys, mapped_to))
            return Mapping(seq, mapped_to['name'], seq[len(keys):],
                           mapping_status.COMPLETE)

        for key in KeySequenceTokenizer(seq).iter_tokenize():
            head += key
            keys, mapped_to = self._find_full_match(self.state.mode, head)
            if keys:
                self.state.logger.info("[Mappings] found full command: {0} -> {1}".format(keys, mapped_to))
                return Mapping(head, mapped_to['name'], seq[len(head):],
                               mapping_status.COMPLETE)
            else:
                break

        if self._find_partial_match(self.state.mode, seq):
            self.state.logger.info("[Mappings] found partial command: {0}".format(seq))
            return Mapping(seq, '', '', mapping_status.INCOMPLETE)

        return None

    # XXX: Provisional. Get rid of this as soon as possible.
    def can_be_long_user_mapping(self, key):
        full_match = self._find_full_match(self.state.mode, key)
        partial_matches = self._find_partial_match(self.state.mode, key)
        if partial_matches:
            self.state.logger.info("[Mappings] user mapping found: {0} -> {1}".format(key, partial_matches))
            return (True, full_match[0])
        self.state.logger.info("[Mappings] user mapping not found: {0} -> {1}".format(key, partial_matches))
        return (False, True)

    # XXX: Provisional. Get rid of this as soon as possible.
    def incomplete_user_mapping(self):
        (maybe_mapping, complete) = \
            self.can_be_long_user_mapping(self.state.partial_sequence)
        if maybe_mapping and not complete:
            self.state.logger.info("[Mappings] incomplete user mapping {0}".format(self.state.partial_sequence))
            return True

    def resolve(self, sequence=None, mode=None, check_user_mappings=True):
        """
        Looks at the current global state and returns the command mapped to
        the available sequence. It may be a 'missing' command.

        @sequence
            If a @sequence is passed, it is used instead of the global state's.
            This is necessary for some commands that aren't name spaces but act
            as them (for example, ys from the surround plugin).
        @mode
            If different than `None`, it will be used instead of the global
            state's. This is necessary when we are in operator pending mode
            and we receive a new action. By combining the existing action's
            name with name of the action just received we could find a new
            action.

            For example, this is the case of g~~.
        """
        # we usually need to look at the partial sequence, but some commands do weird things,
        # like ys, which isn't a namespace but behaves as such sometimes.
        seq = sequence or self.state.partial_sequence
        seq = to_bare_command_name(seq)

        # TODO: Use same structure as in mappings (nested dicst).
        command = None
        if check_user_mappings:
            self.state.logger.info('[Mappings] checking user mappings')
            # TODO: We should be able to force a mode here too as, below.
            command = self.expand_first(seq)

        if command:
            self.state.logger.info('[Mappings] {0} equals command: {1}'.format(seq, command))
            return command
            # return {'name': command.mapping, 'type': cmd_types.USER}
        else:
            self.state.logger.info('[Mappings] looking up >{0}<'.format(seq))
            command = seq_to_command(self.state, seq, mode=mode)
            self.state.logger.info('[Mappings] got {0}'.format(command))
            return command


    def add(self, mode, new, target):
        _mappings[mode][new] = {'name': target, 'type': cmd_types.USER}

    def remove(self, mode, new):
        try:
            del _mappings[mode][new]
        except KeyError:
            raise KeyError('mapping not found')

    def clear(self):
        _mappings[modes.NORMAL] = {}
        _mappings[modes.VISUAL] = {}
        _mappings[modes.VISUAL_LINE] = {}
        _mappings[modes.VISUAL_BLOCK] = {}
        _mappings[modes.OPERATOR_PENDING] = {}

########NEW FILE########
__FILENAME__ = marks
import sublime

# store: window, view, rowcol

_MARKS = {}

class Marks(object):
    def __get__(self, instance, owner):
        self.state = instance
        return self

    def add(self, name, view):
        # TODO: support multiple selections
        # TODO: Use id attribute; references might change.
        win, view, rowcol = view.window(), view, view.rowcol(view.sel()[0].b)
        _MARKS[name] = win, view, rowcol

    def get_as_encoded_address(self, name, exact=False):
        if name == "'":
            # Special case...
            return '<command _vi_double_single_quote>'

        win, view, rowcol = _MARKS.get(name, (None,) * 3)
        if win:
            if exact:
                rowcol_encoded = ':'.join(str(i) for i in rowcol)
            else:
                rowcol_encoded = ':'.join(str(i) for i in (rowcol[0], 0))
            fname = view.file_name()

            # Marks set in the same view as the current one are returned as regions. Marks in other
            # views are returned as encoded addresses that Sublime Text understands.
            if view and view.view_id == self.state.view.view_id:
                if not exact:
                    rowcol = (rowcol[0], 0)
                return sublime.Region(view.text_point(*rowcol))
            else:
                # FIXME: Remove buffers when they are closed.
                if fname:
                    return "{0}:{1}".format(fname, rowcol_encoded)
                else:
                    return "<untitled {0}>:{1}".format(view.buffer_id(), rowcol_encoded)


########NEW FILE########
__FILENAME__ = registers
import sublime

import itertools


REG_UNNAMED = '"'
REG_SMALL_DELETE = '-'
REG_BLACK_HOLE = '_'
REG_LAST_INSERTED_TEXT = '.'
REG_FILE_NAME = '%'
REG_ALT_FILE_NAME = '#'
REG_EXPRESSION = '='
REG_SYS_CLIPBOARD_1 = '*'
REG_SYS_CLIPBOARD_2 = '+'
REG_SYS_CLIPBOARD_ALL = (REG_SYS_CLIPBOARD_1, REG_SYS_CLIPBOARD_2)
REG_VALID_NAMES = tuple("{0}".format(c) for c in "abcdefghijklmnopqrstuvwxyz")
REG_VALID_NUMBERS = tuple("{0}".format(c) for c in "0123456789")
REG_SPECIAL = (REG_UNNAMED, REG_SMALL_DELETE, REG_BLACK_HOLE,
               REG_LAST_INSERTED_TEXT, REG_FILE_NAME, REG_ALT_FILE_NAME,
               REG_SYS_CLIPBOARD_1, REG_SYS_CLIPBOARD_2)
REG_ALL = REG_SPECIAL + REG_VALID_NUMBERS + REG_VALID_NAMES

# todo(guillermo): There are more.
# todo(guillermo): "* and "+ don't do what they should in linux


# Registers must be available globally, so store here the data.
_REGISTER_DATA = {}


# todo(guillermooo): Subclass dict properly.
class Registers(object):
    """
    Registers hold global data mainly used by yank, delete and paste.

    This class is meant to be used a descriptor.

        class State(object):
            registers = Registers()
            ...

        state = State()
        state.registers["%"] # now state.registers has access to the
                              # current view.

    And this is how you access registers:

    Setting registers...

        state.registers['a'] = "foo" # => a == "foo"
        state.registers['A'] = "bar" # => a == "foobar"
        state.registers['1'] = "baz" # => 1 == "baz"
        state.registers[1] = "fizz"  # => 1 == "fizz"

    Retrieving registers...

        state.registers['a'] # => "foobar"
        state.registers['A'] # => "foobar" (synonyms)
    """

    def __get__(self, instance, owner):
        self.view = instance.view
        self.settings = instance.settings
        return self
        # This ensures that we can easiy access the active view.
        # return Registers(instance.view, instance.settings)

    def _set_default_register(self, values):
        assert isinstance(values, list)
        # Coerce all values into strings.
        values = [str(v) for v in values]
        # todo(guillermo): could be made a decorator.
        _REGISTER_DATA[REG_UNNAMED] = values

    def _maybe_set_sys_clipboard(self, name, value):
        # We actually need to check whether the option is set to a bool; could
        # be any JSON type.
        if (name in REG_SYS_CLIPBOARD_ALL or
           self.settings.view['vintageous_use_sys_clipboard'] is True):
                # Make sure Sublime Text does the right thing in the presence
                # of multiple selections.
                if len(value) > 1:
                    self.view.run_command('copy')
                else:
                    sublime.set_clipboard(value[0])

    def set(self, name, values):
        """
        Sets an a-z or 0-9 register.

        In order to honor multiple selections in Sublime Text, we need to
        store register data as lists, one per selection. The paste command
        will then make the final decision about what to insert into the buffer
        when faced with unbalanced selection number / availabl e register data.
        """
        # We accept integers as register names.
        name = str(name)
        assert len(str(name)) == 1, "Register names must be 1 char long."

        if name == REG_BLACK_HOLE:
            return

        assert isinstance(values, list), \
            "Register values must be inside a list."
        # Coerce all values into strings.
        values = [str(v) for v in values]

        # Special registers and invalid registers won't be set.
        if (not (name.isalpha() or name.isdigit() or
                 name.isupper() or name == REG_UNNAMED or
                 name in REG_SYS_CLIPBOARD_ALL or
                 name == REG_EXPRESSION or
                 name == REG_SMALL_DELETE)):
                    # Vim fails silently.
                    # raise Exception("Can only set a-z and 0-9 registers.")
                    return None

        _REGISTER_DATA[name] = values

        if name not in (REG_EXPRESSION,):
            self._set_default_register(values)
            self._maybe_set_sys_clipboard(name, values)

    def append_to(self, name, suffixes):
        """
        Appends to an a-z register. `name` must be a capital in A-Z.
        """
        assert len(name) == 1, "Register names must be 1 char long."
        assert name in "ABCDEFGHIJKLMNOPQRSTUVWXYZ", \
            "Can only append to A-Z registers."

        existing_values = _REGISTER_DATA.get(name.lower(), '')
        new_values = itertools.zip_longest(existing_values,
                                           suffixes, fillvalue='')
        new_values = [(prefix + suffix) for (prefix, suffix) in new_values]
        _REGISTER_DATA[name.lower()] = new_values
        self._set_default_register(new_values)
        self._maybe_set_sys_clipboard(name, new_values)

    def get(self, name=REG_UNNAMED):
        # We accept integers or strings a register names.
        name = str(name)
        assert len(str(name)) == 1, "Register names must be 1 char long."

        # Did we request a special register?
        if name == REG_BLACK_HOLE:
            return
        elif name == REG_FILE_NAME:
            try:
                return [self.view.file_name()]
            except AttributeError:
                return ''
        elif name in REG_SYS_CLIPBOARD_ALL:
            return [sublime.get_clipboard()]
        elif ((name not in (REG_UNNAMED, REG_SMALL_DELETE)) and
                (name in REG_SPECIAL)):
            return
        # Special case lumped among these --user always wants the sys
        # clipboard.
        elif ((name == REG_UNNAMED) and
              (self.settings.view['vintageous_use_sys_clipboard'] is True)):
            return [sublime.get_clipboard()]

        # If the expression register holds a value and we're requesting the
        # unnamed register, return the expression register and clear it
        # aftwerwards.
        elif name == REG_UNNAMED and _REGISTER_DATA.get(REG_EXPRESSION, ''):
            value = _REGISTER_DATA[REG_EXPRESSION]
            _REGISTER_DATA[REG_EXPRESSION] = ''
            return value

        # We requested an [a-z0-9"] register.
        try:
            # In Vim, "A and "a seem to be synonyms, so accept either.
            return _REGISTER_DATA[name.lower()]
        except KeyError:
            pass

    def yank(self, vi_cmd_data, register=None):
        # Populate registers if we have to.
        if vi_cmd_data._can_yank:
            if register:
                self[register] = self.get_selected_text(vi_cmd_data)
            else:
                self[REG_UNNAMED] = self.get_selected_text(vi_cmd_data)

        # # XXX: Small register delete. Improve this implementation.
        if vi_cmd_data._populates_small_delete_register:
            is_same_line = (lambda r: self.view.line(r.begin()) ==
                            self.view.line(r.end() - 1))
            if all(is_same_line(x) for x in list(self.view.sel())):
                self[REG_SMALL_DELETE] = self.get_selected_text(vi_cmd_data)

    def get_selected_text(self, vi_cmd_data):
        """Inspect settings and populate registers as needed.
        """
        fragments = [self.view.substr(r) for r in list(self.view.sel())]

        # Add new line at EOF, but don't add too many new lines.
        if (vi_cmd_data._synthetize_new_line_at_eof and
           not vi_cmd_data._yanks_linewise):
            if (not fragments[-1].endswith('\n') and
                # XXX: It appears regions can end beyond the buffer's EOF (?).
               self.view.sel()[-1].b >= self.view.size()):
                    fragments[-1] += '\n'

        if fragments and vi_cmd_data._yanks_linewise:
            for i, f in enumerate(fragments):
                # When should we add a newline character?
                #  * always except when we have a non-\n-only string followed
                # by a newline char.
                if (not f.endswith('\n')) or (f == '\n') or f.endswith('\n\n'):
                    fragments[i] = f + '\n'
        return fragments

    def to_dict(self):
        # XXX: Stopgap solution until we sublass from dict
        return {name: self.get(name) for name in REG_ALL}

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        try:
            if key.isupper():
                self.append_to(key, value)
            else:
                self.set(key, value)
        except AttributeError:
            self.set(key, value)

########NEW FILE########
__FILENAME__ = search
import sublime
import sublime_plugin

import re


def find_in_range(view, term, start, end, flags=0):
    found = view.find(term, start, flags)
    if found and found.b <= end:
        return found


def find_wrapping(view, term, start, end, flags=0, times=1):
    current_sel = view.sel()[0]
    # Search wrapping around the end of the buffer.
    for x in range(times):
        match = find_in_range(view, term, start, end, flags)
        # Start searching in the upper half of the buffer if we aren't doing it yet.
        if not match and start > current_sel.b:
            start = 0
            end = current_sel.a
            match = find_in_range(view, term, start, end, flags)
            if not match:
                return
        # No luck in the whole buffer.
        elif not match:
            return
        start = match.b

    return match


def reverse_find_wrapping(view, term, start, end, flags=0, times=1):
    current_sel = view.sel()[0]
    # Search wrapping around the end of the buffer.
    for x in range(times):
        match = reverse_search(view, term, start, end, flags)
        # Start searching in the lower half of the buffer if we aren't doing it yet.
        if not match and start < current_sel.b:
            start = current_sel.b
            end = view.size()
            match = reverse_search(view, term, start, end, flags)
            if not match:
                return
        # No luck in the whole buffer.
        elif not match:
            return
        end = match.a

    return match


def find_last_in_range(view, term, start, end, flags=0):
    found = find_in_range(view, term, start, end, flags)
    last_found = found
    while found:
        found = find_in_range(view, term, found.b, end, flags)
        if not found or found.b > end:
            break
        last_found = found if found else last_found

    return last_found


# reverse search
def reverse_search(view, term, start, end, flags=0):
    assert isinstance(start, int) or start is None
    assert isinstance(end, int) or end is None

    start = start if (start is not None) else 0
    end = end if (end is not None) else view.size()

    if start < 0 or end > view.size():
        return None

    lo_line = view.full_line(start)
    hi_line = view.full_line(end)

    while True:
        low_row, hi_row = view.rowcol(lo_line.a)[0], view.rowcol(hi_line.a)[0]
        middle_row = (low_row + hi_row) // 2

        middle_line = view.full_line(view.text_point(middle_row, 0))

        lo_region = sublime.Region(lo_line.a, middle_line.b)
        hi_region = sublime.Region(middle_line.b, min(hi_line.b, end))

        if find_in_range(view, term, hi_region.a, hi_region.b, flags):
            lo_line = view.full_line(middle_line.b)
        elif find_in_range(view, term, lo_region.a, lo_region.b, flags):
            hi_line = view.full_line(middle_line.a)
        else:
            return None

        if lo_line == hi_line:
            # we found the line we were looking for, now extract the match.
            return find_last_in_range(view, term, hi_line.a, min(hi_line.b, end), flags)


def reverse_search_by_pt(view, term, start, end, flags=0):
    assert isinstance(start, int) or start is None
    assert isinstance(end, int) or end is None

    start = start if (start is not None) else 0
    end = end if (end is not None) else view.size()

    if start < 0 or end > view.size():
        return None

    lo_line = view.full_line(start)
    hi_line = view.full_line(end)

    while True:
        low_row, hi_row = view.rowcol(lo_line.a)[0], view.rowcol(hi_line.a)[0]
        middle_row = (low_row + hi_row) // 2

        middle_line = view.full_line(view.text_point(middle_row, 0))

        lo_region = sublime.Region(lo_line.a, middle_line.b)
        hi_region = sublime.Region(middle_line.b, min(hi_line.b, end))

        if find_in_range(view, term, hi_region.a, hi_region.b, flags):
            lo_line = view.full_line(middle_line.b)
        elif find_in_range(view, term, lo_region.a, lo_region.b, flags):
            hi_line = view.full_line(middle_line.a)
        else:
            return None

        if lo_line == hi_line:
            # we found the line we were looking for, now extract the match.
            return find_last_in_range(view, term, max(hi_line.a, start), min(hi_line.b, end), flags)


# TODO: Test me.
class BufferSearchBase(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def calculate_flags(self):
        # TODO: Implement smartcase?
        flags = 0
        if self.view.settings().get('vintageous_magic') == False:
             flags |= sublime.LITERAL

        if self.view.settings().get('vintageous_ignorecase') == True:
            flags |= sublime.IGNORECASE

        return flags

    def build_pattern(self, query):
        return query

    def hilite(self, query):
        flags = self.calculate_flags()
        regs = self.view.find_all(self.build_pattern(query), flags)

        if not regs:
            self.view.erase_regions('vi_search')
            return

        # TODO: Re-enable this.
        # if State(self.view).settings.vi['hlsearch'] == False:
        #     return

        self.view.add_regions('vi_search', regs, 'comment', '',
                              sublime.DRAW_NO_FILL)


# TODO: Test me.
class ExactWordBufferSearchBase(BufferSearchBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def calculate_flags(self):
        if self.view.settings().get('vintageous_ignorecase') == True:
            return sublime.IGNORECASE
        return 0

    def get_query(self):
        # TODO: make sure we swallow any leading white space.
        query = self.view.substr(self.view.word(self.view.sel()[0].end()))
        return query

    def build_pattern(self, query):
        return r'\b{0}\b'.format(re.escape(query))

########NEW FILE########
__FILENAME__ = settings
import sublime

import collections
import json

vi_user_setting = collections.namedtuple('vi_editor_setting', 'scope values default parser action negatable')

WINDOW_SETTINGS = [
    'last_buffer_search',
    '_cmdline_cd',
]


SCOPE_WINDOW = 1
SCOPE_VIEW = 2
SCOPE_VI_VIEW = 3
SCOPE_VI_WINDOW = 4


def set_generic_view_setting(view, name, value, opt, globally=False):
    if opt.scope == SCOPE_VI_VIEW:
        name = 'vintageous_' + name
    if not opt.parser:
        if not globally or (opt.scope not in (SCOPE_VI_VIEW, SCOPE_VI_WINDOW)):
            view.settings().set(name, value)
        else:
            prefs = sublime.load_settings('Preferences.sublime-settings')
            prefs.set(name, value)
            sublime.save_settings('Preferences.sublime-settings')
        return
    else:
        if not globally or (opt.scope not in (SCOPE_VI_VIEW, SCOPE_VI_WINDOW)):
            view.settings().set(name, opt.parser(value))
        else:
            name = 'vintageous_' + name
            prefs = sublime.load_settings('Preferences.sublime-settings')
            prefs.set(name, opt.parser(value))
            sublime.save_settings('Preferences.sublime-settings')
        return
    raise ValueError("Vintageous: bad option value")


def set_minimap(view, name, value, opt, globally=False):
    # TODO: Ensure the minimap gets hidden when so desired.
    view.window().run_command('toggle_minimap')


def set_sidebar(view, name, value, opt, globally=False):
    # TODO: Ensure the minimap gets hidden when so desired.
    view.window().run_command('toggle_side_bar')


def opt_bool_parser(value):
    if value.lower() in ('false', 'true', '0', '1', 'yes', 'no'):
        if value.lower() in ('true', '1', 'yes'):
            return True
        return False


def opt_rulers_parser(value):
    try:
        converted = json.loads(value)
        if isinstance(converted, list):
            return converted
        else:
            raise ValueError
    except ValueError:
        raise
    except TypeError:
        raise ValueError


VI_OPTIONS = {
    'autoindent':  vi_user_setting(scope=SCOPE_VI_VIEW,   values=(True, False, '0', '1'), default=True,  parser=None,              action=set_generic_view_setting, negatable=False),
    'hlsearch':    vi_user_setting(scope=SCOPE_VI_VIEW,   values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
    'ignorecase':  vi_user_setting(scope=SCOPE_VI_VIEW,   values=(True, False, '0', '1'), default=False, parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
    'incsearch':   vi_user_setting(scope=SCOPE_VI_VIEW,   values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
    'magic':       vi_user_setting(scope=SCOPE_VI_VIEW,   values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
    'visualbell':  vi_user_setting(scope=SCOPE_VI_WINDOW, values=(True, False, '0', '1'), default=True,  parser=opt_bool_parser,   action=set_generic_view_setting, negatable=True),
    'rulers':      vi_user_setting(scope=SCOPE_VIEW,      values=None,                    default=[],    parser=opt_rulers_parser, action=set_generic_view_setting, negatable=False),
    'showminimap': vi_user_setting(scope=SCOPE_WINDOW,    values=(True, False, '0', '1'), default=True,  parser=None,              action=set_minimap,              negatable=True),
    'showsidebar': vi_user_setting(scope=SCOPE_WINDOW,    values=(True, False, '0', '1'), default=True,  parser=None,              action=set_sidebar,              negatable=True),
}


# For completions.
def iter_settings(prefix=''):
    if prefix.startswith('no'):
        for item in (x for (x, y) in VI_OPTIONS.items() if y.negatable):
            if ('no' + item).startswith(prefix):
                yield 'no' + item
    else:
        for k in sorted(VI_OPTIONS.keys()):
            if (prefix == '') or k.startswith(prefix):
                yield k


def set_local(view, name, value):
    try:
        opt = VI_OPTIONS[name]
        if not value and opt.negatable:
            opt.action(view, name, '1', opt)
            return
        opt.action(view, name, value, opt)
    except KeyError as e:
        if name.startswith('no'):
            try:
                opt = VI_OPTIONS[name[2:]]
                if opt.negatable:
                    opt.action(view, name[2:], '0', opt)
                return
            except KeyError:
                pass
        raise


def set_global(view, name, value):
    try:
        opt = VI_OPTIONS[name]
        if not value and opt.negatable:
            opt.action(view, name, '1', opt, globally=True)
            return
        opt.action(view, name, value, opt, globally=True)
    except KeyError as e:
        if name.startswith('no'):
            try:
                opt = VI_OPTIONS[name[2:]]
                if opt.negatable:
                    opt.action(view, name[2:], '0', opt, globally=True)
                return
            except KeyError:
                pass
        raise


def get_option(view, name):
    # TODO: Should probably return global, local values.
    option_data = VI_OPTIONS[name]
    if option_data.scope == SCOPE_WINDOW:
        value = view.window().settings().get('vintageous_' + name)
    else:
        value = view.settings().get('vintageous_' + name)

    return value if (value in option_data.values) else option_data.default


class SublimeSettings(object):
    """ Helper class for accessing settings values from views """

    def __init__(self, view=None):
        self.view = view

    def __get__(self, instance, owner):
        if instance is not None:
            return SublimeSettings(instance.v)
        return SublimeSettings()

    def __getitem__(self, key):
        return self.view.settings().get(key)

    def __setitem__(self, key, value):
        self.view.settings().set(key, value)


class VintageSettings(object):
    """ Helper class for accessing settings related to Vintage. """

    def __init__(self, view=None):
        self.view = view

        if view is not None and not isinstance(self.view.settings().get('vintage'), dict):
            self.view.settings().set('vintage', dict())

        if view is not None and view.window() is not None and not isinstance(self.view.window().settings().get('vintage'), dict):
            self.view.window().settings().set('vintage', dict())

    def __get__(self, instance, owner):
        if instance is not None:
            return VintageSettings(instance.v)
        return VintageSettings()

    def __getitem__(self, key):

        # Vi editor options.
        if key in VI_OPTIONS:
            return get_option(self.view, key)

        # Vintageous settings.
        try:
            if key not in WINDOW_SETTINGS:
                value = self.view.settings().get('vintage').get(key)
            else:
                value = self.view.window().settings().get('vintage').get(key)
        except (KeyError, AttributeError):
            value = None
        return value

    def __setitem__(self, key, value):
        if key not in WINDOW_SETTINGS:
            setts, target = self.view.settings().get('vintage'), self.view
        else:
            setts, target = self.view.window().settings().get('vintage'), self.view.window()

        setts[key] = value
        target.settings().set('vintage', setts)


class SublimeWindowSettings(object):
    """ Helper class for accessing settings values from views """

    def __init__(self, view=None):
        self.view = view

    def __get__(self, instance, owner):
        if instance is not None:
            return SublimeSettings(instance.v.window())
        return SublimeSettings()

    def __getitem__(self, key):
        return self.view.window().settings().get(key)

    def __setitem__(self, key, value):
        self.view.window().settings().set(key, value)


# TODO: Make this a descriptor; avoid instantiation.
class SettingsManager(object):
    view = SublimeSettings()
    vi = VintageSettings()
    window = SublimeWindowSettings()

    def __init__(self, view):
        self.v = view

########NEW FILE########
__FILENAME__ = sublime
# An assortment of utilities.

from contextlib import contextmanager


@contextmanager
def restoring_sels(view):
    old_sels = list(view.sel())
    yield
    view.sel().clear()
    for s in old_sels:
        # XXX: If the buffer has changed in the meantime, this won't work well.
        view.sel().add(s)


def has_dirty_buffers(window):
    for v in window.views():
        if v.is_dirty():
            return True


def show_ipanel(window, caption='', initial_text='', on_done=None,
                on_change=None, on_cancel=None):
    v = window.show_input_panel(caption, initial_text, on_done, on_change,
                                on_cancel)
    return v


def is_view(view):
    """
    Returns `True` if @view is a normal view.
    """
    return not (is_widget(view) or is_console(view))


def is_widget(view):
    """
    Returns `True` if @view is a widget.
    """
    return view.settings().get('is_widget')


def is_console(view):
    """
    Returns `True` if @view seems to be ST3's console.
    """
    # XXX: Is this reliable?
    return (getattr(view, 'settings') is None)

########NEW FILE########
__FILENAME__ = text_objects
import sublime

from sublime import CLASS_WORD_START
from sublime import CLASS_WORD_END
from sublime import CLASS_PUNCTUATION_START
from sublime import CLASS_PUNCTUATION_END
from sublime import CLASS_LINE_END
from sublime import CLASS_LINE_START
from sublime import CLASS_EMPTY_LINE

from Vintageous.vi.search import reverse_search_by_pt
from Vintageous.vi.search import find_in_range
from Vintageous.vi import units
from Vintageous.vi import utils
from Vintageous.vi import search

import re


RX_ANY_TAG = r'</?([0-9A-Za-z-]+).*?>'
RX_ANY_TAG_NAMED_TPL = r'</?({0}) *?.*?>'
RXC_ANY_TAG = re.compile(r'</?([0-9A-Za-z]+).*?>')
# According to the HTML 5 editor's draft, only 0-9A-Za-z characters can be
# used in tag names. TODO: This won't be enough in Dart Polymer projects,
# for example.
RX_ANY_START_TAG = r'<([0-9A-Za-z]+)(.*?)>'
RX_ANY_END_TAG = r'</.*?>'


ANCHOR_NEXT_WORD_BOUNDARY = CLASS_WORD_START | CLASS_PUNCTUATION_START | \
                            CLASS_LINE_END
ANCHOR_PREVIOUS_WORD_BOUNDARY = CLASS_WORD_END | CLASS_PUNCTUATION_END | \
                                CLASS_LINE_START

WORD_REVERSE_STOPS = CLASS_WORD_START | CLASS_EMPTY_LINE | \
                         CLASS_PUNCTUATION_START
WORD_END_REVERSE_STOPS = CLASS_WORD_END | CLASS_EMPTY_LINE | \
                         CLASS_PUNCTUATION_END



BRACKET = 1
QUOTE = 2
SENTENCE = 3
TAG = 4
WORD = 5
BIG_WORD = 6
PARAGRAPH = 7


PAIRS = {
    '"': (('"', '"'), QUOTE),
    "'": (("'", "'"), QUOTE),
    '`': (('`', '`'), QUOTE),
    '(': (('\\(', '\\)'), BRACKET),
    ')': (('\\(', '\\)'), BRACKET),
    '[': (('\\[', '\\]'), BRACKET),
    ']': (('\\[', '\\]'), BRACKET),
    '{': (('\\{', '\\}'), BRACKET),
    '}': (('\\{', '\\}'), BRACKET),
    '<': (('<', '>'), BRACKET),
    '>': (('<', '>'), BRACKET),
    't': (None, TAG),
    'w': (None, WORD),
    'W': (None, BIG_WORD),
    's': (None, SENTENCE),
    'p': (None, PARAGRAPH),
}


def is_at_punctuation(view, pt):
    next_char = view.substr(pt)
    # FIXME: Wrong if pt is at '\t'.
    return (not (is_at_word(view, pt) or
                 next_char.isspace() or
                 next_char == '\n')
            and next_char.isprintable())


def is_at_word(view, pt):
    next_char = view.substr(pt)
    return (next_char.isalnum() or next_char == '_')


def is_at_space(view, pt):
    return view.substr(pt).isspace()


def get_punctuation_region(view, pt):
   start = view.find_by_class(pt + 1, forward=False,
                              classes=CLASS_PUNCTUATION_START)
   end = view.find_by_class(pt, forward=True,
                            classes=CLASS_PUNCTUATION_END)
   return sublime.Region(start, end)


def get_space_region(view, pt):
    end = view.find_by_class(pt, forward=True,
                             classes=ANCHOR_NEXT_WORD_BOUNDARY)
    return sublime.Region(previous_word_end(view, pt + 1), end)


def previous_word_end(view, pt):
    return view.find_by_class(pt, forward=False,
                              classes=ANCHOR_PREVIOUS_WORD_BOUNDARY)


def next_word_start(view, pt):
    if is_at_punctuation(view, pt):
        # Skip all punctuation surrounding the caret and any trailing spaces.
        end = get_punctuation_region(view, pt).b
        if view.substr(end) in (' ', '\n'):
            end = view.find_by_class(end, forward=True,
                                     classes=ANCHOR_NEXT_WORD_BOUNDARY)
            return end
    elif is_at_space(view, pt):
        # Skip all spaces surrounding the cursor and the text word.
        end = get_space_region(view, pt).b
        if is_at_word(view, end) or is_at_punctuation(view, end):
            end = view.find_by_class(end, forward=True,
                                     classes=CLASS_WORD_END |
                                             CLASS_PUNCTUATION_END |
                                             CLASS_LINE_END)
            return end

    # Skip the word under the caret and any trailing spaces.
    return view.find_by_class(pt, forward=True,
                              classes=ANCHOR_NEXT_WORD_BOUNDARY)


def current_word_start(view, pt):
    if is_at_punctuation(view, pt):
        return get_punctuation_region(view, pt).a
    elif is_at_space(view, pt):
        return get_space_region(view, pt).a
    return view.word(pt).a


def current_word_end(view, pt):
    if is_at_punctuation(view, pt):
        return get_punctuation_region(view, pt).b
    elif is_at_space(view, pt):
        return get_space_region(view, pt).b
    return view.word(pt).b


# See vim :help word for a definition of word.
def a_word(view, pt, inclusive=True, count=1):
    assert count > 0
    start = current_word_start(view, pt)
    end = pt
    if inclusive:
        end = units.word_starts(view, start, count=count, internal=True)

        # If there is no space at the end of our word text object, include any
        # preceding spaces. (Follows Vim behavior.)
        if (not view.substr(end - 1).isspace() and
            view.substr(start - 1).isspace()):
                start = utils.previous_non_white_space_char(
                                                    view, start - 1,
                                                    white_space=' \t') + 1

        # Vim does some inconsistent stuff here...
        if count > 1 and view.substr(end) == '\n':
            end += 1
        return sublime.Region(start, end)

    for x in range(count):
        end = current_word_end(view, end)

    return sublime.Region(start, end)


def big_word_end(view, pt):
    while True:
        if is_at_punctuation(view, pt):
            pt = get_punctuation_region(view, pt).b
        elif is_at_word(view, pt):
            pt = current_word_end(view, pt)
        else:
            break
    return pt


def big_word_start(view, pt):
    while True:
        if is_at_punctuation(view, pt):
            pt = get_punctuation_region(view, pt).a - 1
        elif is_at_word(view, pt):
            pt = current_word_start(view, pt) - 1
        else:
            break
    return pt + 1


def a_big_word(view, pt, inclusive=True, count=1):
    start, end = None, pt
    for x in range(count):
        if is_at_space(view, end):
            if start is None:
                start = get_space_region(view, pt)
            if not inclusive:
                end = get_space_region(view, end).b
            else:
                end = big_word_end(view, get_space_region(view, end).b)

        if is_at_punctuation(view, end):
            if start is None:
                start = big_word_start(view, end)
            end = big_word_end(view, end)
            if inclusive and is_at_space(view, end):
                end = get_space_region(view, end).b

        else:
            if start is None:
                start = big_word_start(view, end)
            end = big_word_end(view, end)
            if inclusive and is_at_space(view, end):
                end = get_space_region(view, end).b

    return sublime.Region(start, end)


def get_text_object_region(view, s, text_object, inclusive=False, count=1):
    try:
        delims, type_ = PAIRS[text_object]
    except KeyError:
        return s

    if type_ == TAG:
        begin_tag, end_tag, _ = find_containing_tag(view, s.b)
        if inclusive:
            return sublime.Region(begin_tag.a, end_tag.b)
        else:
            return sublime.Region(begin_tag.b, end_tag.a)

    if type_ == PARAGRAPH:
        return find_paragraph_text_object(view, s, inclusive)

    if type_ == BRACKET:
        opening = find_prev_lone_bracket(view, s.b, delims)
        closing = find_next_lone_bracket(view, s.b, delims)

        if not (opening and closing):
            return s

        if inclusive:
            return sublime.Region(opening.a, closing.b)
        return sublime.Region(opening.a + 1, closing.b - 1)

    if type_ == QUOTE:
        # Vim only operates on the current line.
        line = view.line(s)
        # FIXME: Escape sequences like \" are probably syntax-dependant.
        prev_quote = reverse_search_by_pt(view, r'(?<!\\\\)' + delims[0],
                                          start=line.a, end=s.b)

        next_quote = find_in_range(view, r'(?<!\\\\)' + delims[0],
                                   start=s.b, end=line.b)

        if next_quote and not prev_quote:
            prev_quote = next_quote
            next_quote = find_in_range(view, r'(?<!\\\\)' + delims[0],
                                       start=prev_quote.b, end=line.b)

        if not (prev_quote and next_quote):
            return s

        if inclusive:
            return sublime.Region(prev_quote.a, next_quote.b)
        return sublime.Region(prev_quote.a + 1, next_quote.b - 1)

    if type_ == WORD:
        w = a_word(view, s.b, inclusive=inclusive, count=count)
        if not w:
            return s
        if s.size() <= 1:
            return w
        return sublime.Region(s.a, w.b)

    if type_ == BIG_WORD:
        w = a_big_word(view, s.b, inclusive=inclusive, count=count)
        if not w:
            return s
        if s.size() <= 1:
            return w
        return sublime.Region(s.a, w.b)

    if type_ == SENTENCE:
        # FIXME: This doesn't work well.
        # TODO: Improve this.
        sentence_start = view.find_by_class(s.b,
                                            forward=False,
                                            classes=sublime.CLASS_EMPTY_LINE)
        sentence_start_2 = reverse_search_by_pt(view, r'[.?!:]\s+|[.?!:]$',
                                                start=0,
                                                end=s.b)
        if sentence_start_2:
            sentence_start = (sentence_start + 1 if (sentence_start >
                                                     sentence_start_2.b)
                                                 else sentence_start_2.b)
        else:
            sentence_start = sentence_start + 1
        sentence_end = find_in_range(view, r'([.?!:)](?=\s))|([.?!:)]$)',
                                     start=s.b,
                                     end=view.size())

        if not (sentence_end):
            return s

        if inclusive:
            return sublime.Region(sentence_start, sentence_end.b)
        else:
            return sublime.Region(sentence_start, sentence_end.b)


    return s


def find_next_lone_bracket(view, start, items, unbalanced=0):
    # TODO: Extract common functionality from here and the % motion instead of
    # duplicating code.
    new_start = start
    for i in range(unbalanced or 1):
        next_closing_bracket = find_in_range(view, items[1],
                                                  start=new_start,
                                                  end=view.size(),
                                                  flags=sublime.IGNORECASE)
        if next_closing_bracket is None:
            # Unbalanced items; nothing we can do.
            return
        new_start = next_closing_bracket.end()

    if view.substr(start) == items[0][-1]:
        start += 1

    nested = 0
    while True:
        next_opening_bracket = find_in_range(view, items[0],
                                              start=start,
                                              end=next_closing_bracket.b,
                                              flags=sublime.IGNORECASE)
        if not next_opening_bracket:
            break
        nested += 1
        start = next_opening_bracket.end()

    if nested > 0:
        return find_next_lone_bracket(view, next_closing_bracket.end(),
                                                  items,
                                                  nested)
    else:
        return next_closing_bracket


def find_prev_lone_bracket(view, start, tags, unbalanced=0):
    # TODO: Extract common functionality from here and the % motion instead of
    # duplicating code.
    new_start = start
    for i in range(unbalanced or 1):
        prev_opening_bracket = reverse_search_by_pt(view, tags[0],
                                                  start=0,
                                                  end=new_start,
                                                  flags=sublime.IGNORECASE)
        if prev_opening_bracket is None:
            # Tag names may be escaped, so slice them.
            if i == 0 and view.substr(start) == tags[0][-1]:
                return sublime.Region(start, start + 1)
            # Unbalanced tags; nothing we can do.
            return
        new_start = prev_opening_bracket.begin()

    nested = 0
    while True:
        next_closing_bracket = reverse_search_by_pt(view, tags[1],
                                              start=prev_opening_bracket.a,
                                              end=start,
                                              flags=sublime.IGNORECASE)
        if not next_closing_bracket:
            break
        nested += 1
        start = next_closing_bracket.begin()

    if nested > 0:
        return find_prev_lone_bracket(view, prev_opening_bracket.begin(),
                                                  tags,
                                                  nested)
    else:
        return prev_opening_bracket


def find_paragraph_text_object(view, s, inclusive=True):
    # TODO: Implement counts.
    begin = view.find_by_class(s.a, forward=False, classes=CLASS_EMPTY_LINE)
    end = view.find_by_class(s.b, forward=True, classes=CLASS_EMPTY_LINE)
    if not inclusive:
        if begin > 0:
            begin += 1
    return sublime.Region(begin, end)


# TODO: Move this to units.py.
def word_reverse(view, pt, count=1, big=False):
    t = pt
    for _ in range(count):
        t = view.find_by_class(t, forward=False, classes=WORD_REVERSE_STOPS)
        if t == 0:
            break

        if big:
            # Skip over punctuation characters.
            while not ((view.substr(t - 1) in '\n\t ') or (t <= 0)):
                t -= 1
    return t


# TODO: Move this to units.py.
def word_end_reverse(view, pt, count=1, big=False):
    t = pt
    for i in range(count):
        if big:
            # Skip over punctuation characters.
            while not ((view.substr(t - 1) in '\n\t ') or (t <= 0)):
                t -= 1

        # `ge` should stop at the previous word end if starting at a space
        # immediately after a word.
        if (i == 0 and
            view.substr(t).isspace() and
            not view.substr(t - 1).isspace()):
                continue

        if (not view.substr(t).isalnum() and
            not view.substr(t).isspace() and
            view.substr(t - 1).isalnum() and
            t > 0):
                pass
        else:
            t = view.find_by_class(t, forward=False, classes=WORD_END_REVERSE_STOPS)
        if t == 0:
            break

    return max(t - 1, 0)


def next_end_tag(view, pattern=RX_ANY_TAG, start=0, end=-1):
    region = view.find(pattern, start, sublime.IGNORECASE)
    if region.a == -1:
        return None, None, None
    match = re.search(pattern, view.substr(region))
    return (region, match.group(1), match.group(0).startswith('</'))


def previous_begin_tag(view, pattern, start=0, end=0):
    assert pattern, 'bad call'
    region = reverse_search_by_pt(view, RX_ANY_TAG, start, end,
                                  sublime.IGNORECASE)
    if not region:
        return None, None, None
    match = re.search(RX_ANY_TAG, view.substr(region))
    return (region, match.group(1), match.group(0)[1] != '/')


def get_region_end(r):
    return {'end': r.end()}


def get_region_begin(r):
    return {'start': 0, 'end': r.begin()}


def get_closest_tag(view, pt):
    while pt > 0 and view.substr(pt) != '<':
        pt -= 1

    if view.substr(pt) != '<':
        return None

    next_tag = view.find(RX_ANY_TAG, pt)
    if next_tag.a != pt:
        return None

    return pt, next_tag


def find_containing_tag(view, start):
    # BUG: fails if start < first begin tag
    # TODO: Should not select tags in PCDATA sections.
    _, closest_tag = get_closest_tag(view, start)
    if not closest_tag:
        return None, None, None

    start = closest_tag.a if ((closest_tag.contains(start)) and
                              (view.substr(closest_tag)[1] == '/')) else start

    search_forward_args = {
        'pattern': RX_ANY_TAG,
        'start': start,
    }
    end_region, tag_name = next_unbalanced_tag(view,
                                 search=next_end_tag,
                                 search_args=search_forward_args,
                                 restart_at=get_region_end)

    if not end_region:
        return None, None, None

    search_backward_args = {
        'pattern': RX_ANY_TAG_NAMED_TPL.format(tag_name),
        'start': 0,
        'end': end_region.a
    }
    begin_region, _ = next_unbalanced_tag(view,
                                 search=previous_begin_tag,
                                 search_args=search_backward_args,
                                 restart_at=get_region_begin)

    if not end_region:
        return None, None, None

    return begin_region, end_region, tag_name


def next_unbalanced_tag(view,
                        search=None,
                        search_args={},
                        restart_at=None,
                        tags=[]):
    assert search and restart_at, 'wrong call'

    region, tag, is_end_tag = search(view, **search_args)

    if not region:
        return None, None

    if not is_end_tag:
        tags.append(tag)
        search_args.update(restart_at(region))
        return next_unbalanced_tag(view,
                                   search,
                                   search_args,
                                   restart_at,
                                   tags)

    if not tags or (tag not in tags):
        return region, tag

    while tag != tags.pop():
        continue

    search_args.update(restart_at(region))
    return next_unbalanced_tag(view,
                               search,
                               search_args,
                               restart_at,
                               tags)

########NEW FILE########
__FILENAME__ = units
from sublime import CLASS_WORD_START
from sublime import CLASS_WORD_END
from sublime import CLASS_PUNCTUATION_START
from sublime import CLASS_PUNCTUATION_END
from sublime import CLASS_EMPTY_LINE
from sublime import CLASS_LINE_END
from sublime import CLASS_LINE_START


from Vintageous.vi.utils import next_non_white_space_char

import re


word_pattern = re.compile('\w')

# Places at which regular words start (for Vim).
CLASS_VI_WORD_START = CLASS_WORD_START | CLASS_PUNCTUATION_START | CLASS_LINE_START
# Places at which *sometimes* words start. Called 'internal' because it's a notion Vim has; not
# obvious.
CLASS_VI_INTERNAL_WORD_START = CLASS_WORD_START | CLASS_PUNCTUATION_START | CLASS_LINE_END
CLASS_VI_WORD_END = CLASS_WORD_END | CLASS_PUNCTUATION_END
CLASS_VI_INTERNAL_WORD_END = CLASS_WORD_END | CLASS_PUNCTUATION_END


def at_eol(view, pt):
    return (view.classify(pt) & CLASS_LINE_END) == CLASS_LINE_END


def at_punctuation(view, pt):
    # FIXME: Not very reliable?
    is_at_eol = at_eol(view, pt)
    is_at_word = at_word(view, pt)
    is_white_space = view.substr(pt).isspace()
    is_at_eof = pt == view.size()
    return not any((is_at_eol, is_at_word, is_white_space, is_at_eof))


def at_word_start(view, pt):
    return (view.classify(pt) & CLASS_WORD_START) == CLASS_WORD_START


def at_word_end(view, pt):
    return (view.classify(pt) & CLASS_WORD_END) == CLASS_WORD_END


def at_punctuation_end(view, pt):
    return (view.classify(pt) & CLASS_PUNCTUATION_END) == CLASS_PUNCTUATION_END


def at_word(view, pt):
    return at_word_start(view, pt) or word_pattern.match(view.substr(pt))


def skip_word(view, pt):
    while True:
        if at_punctuation(view, pt):
            pt = view.find_by_class(pt, forward=True, classes=CLASS_PUNCTUATION_END)
        elif at_word(view, pt):
            pt = view.find_by_class(pt, forward=True, classes=CLASS_WORD_END)
        else:
            break
    return pt


def next_word_start(view, start, internal=False):
    classes = CLASS_VI_WORD_START if not internal else CLASS_VI_INTERNAL_WORD_START
    pt = view.find_by_class(start, forward=True, classes=classes)
    if internal and at_eol(view, pt):
        # Unreachable?
        return pt
    return pt


def next_big_word_start(view, start, internal=False):
    classes = CLASS_VI_WORD_START if not internal else CLASS_VI_INTERNAL_WORD_START
    pt = skip_word(view, start)
    seps = ''
    if internal and at_eol(view, pt):
        return pt
    pt = view.find_by_class(pt, forward=True, classes=classes, separators=seps)
    return pt


def next_word_end(view, start, internal=False):
    classes = CLASS_VI_WORD_END if not internal else CLASS_VI_INTERNAL_WORD_END
    pt = view.find_by_class(start, forward=True, classes=classes)
    if internal and at_eol(view, pt):
        # Unreachable?
        return pt
    return pt


def word_starts(view, start, count=1, internal=False):
    assert start >= 0
    assert count > 0

    pt = start
    for i in range(count):
        # On the last motion iteration, we must do some special stuff if we are still on the
        # starting line of the motion.
        if (internal and (i == count - 1) and
            (view.line(start) == view.line(pt))):
                if view.substr(pt) == '\n':
                    return pt + 1
                return next_word_start(view, pt, internal=True)

        pt = next_word_start(view, pt)
        if not internal or (i != count - 1):
            pt = next_non_white_space_char(view, pt, white_space=' \t')
            while not (view.size() == pt or
                       view.line(pt).empty() or
                       view.substr(view.line(pt)).strip()):
                pt = next_word_start(view, pt)
                pt = next_non_white_space_char(view, pt, white_space=' \t')

    if (internal and (view.line(start) != view.line(pt)) and
       (start != view.line(start).a and not view.substr(view.line(pt - 1)).isspace()) and
         at_eol(view, pt - 1)):
            pt -= 1

    return pt


def big_word_starts(view, start, count=1, internal=False):
    assert start >= 0
    assert count > 0

    pt = start
    for i in range(count):
        if internal and i == count - 1 and view.line(start) == view.line(pt):
            if view.substr(pt) == '\n':
                return pt + 1
            return next_big_word_start(view, pt, internal=True)

        pt = next_big_word_start(view, pt)
        if not internal or i != count - 1:
            pt = next_non_white_space_char(view, pt, white_space=' \t')
            while not (view.size() == pt or
                       view.line(pt).empty() or
                       view.substr(view.line(pt)).strip()):
                pt = next_big_word_start(view, pt)
                pt = next_non_white_space_char(view, pt, white_space=' \t')

    if (internal and (view.line(start) != view.line(pt)) and
       (start != view.line(start).a and not view.substr(view.line(pt - 1)).isspace()) and
         at_eol(view, pt - 1)):
            pt -= 1

    return pt


def word_ends(view, start, count=1, big=False):
    assert start >= 0 and count > 0, 'bad call'

    pt = start
    if not view.substr(start).isspace():
        pt = start + 1

    for i in range(count):
        if big:
            while True:
                pt = next_word_end(view, pt)
                if pt >= view.size() or view.substr(pt).isspace():
                    if pt > view.size():
                        pt = view.size()
                    break
        else:
            pt = next_word_end(view, pt)

    # FIXME: We should return the actual word end and not pt - 1 ??
    return pt

########NEW FILE########
__FILENAME__ = utils
import sublime
import sublime_plugin
from Vintageous.vi.sublime import is_view as sublime_is_view

from contextlib import contextmanager
import logging
import re


logging.basicConfig(level=logging.INFO)


def mark_as_widget(view):
    """
    Marks @view as a widget so we can later inspect that attribute, for
    example, when hiding panels in _vi_enter_normal_mode.

    Used prominently by '/', '?' and ':'.

    XXX: This doesn't always work as we expect. For example, changing
         settings to a panel created instants before does not make those
         settings visible when the panel is activated. Investigate.
         We still need this so that contexts will ignore widgets, though.
         However, the fact that they are widgets should suffice to disable
         Vim keys for them...
    """
    view.settings().set('is_vintageous_widget', True)
    return view


def is_view(view):
    """
    Returns `True` if @view is a normal view as Vintageous understands them.

    It returns `False` for views that have a `__vi_external_disable`
    setting set to `True`.
    """
    return not any((is_widget(view), is_console(view),
                    is_ignored(view), is_ignored_but_command_mode(view)))


def is_ignored(view):
    """
    Returns `True` if the view wants to be ignored by Vintageous.

    Useful for external plugins that don't want Vintageous to be active for
    specific views.
    """
    return view.settings().get('__vi_external_disable', False)


def is_ignored_but_command_mode(view):
    """
    Returns `True` if the view wants to be ignored by Vintageous.

    Useful for external plugins that don't want Vintageous to be active for
    specific views.

    .is_ignored_but_command_mode() differs from .is_ignored() in that here
    we declare that only keys should be disabled, not command mode.
    """
    return view.settings().get('__vi_external_disable_keys', False)


def is_widget(view):
    """
    Returns `True` if the @view is any kind of widget.
    """
    setts = view.settings()
    return (setts.get('is_widget') or setts.get('is_vintageous_widget'))


def is_console(view):
    """
    Returns `True` if @view seems to be ST3's console.
    """
    # XXX: Is this reliable?
    return (getattr(view, 'settings') is None)


def get_logger():
    v = sublime.active_window().active_view()
    level = v.settings().get('vintageous_log_level', 'ERROR')
    # logging.basicConfig(level=_str_to_log_level(level))
    logging.basicConfig(level=0)
    return logging


def get_logging_level():
    v = sublime.active_window().active_view()
    level = v.settings().get('vintageous_log_level', 'ERROR')
    return getattr(logging, level.upper(), logging.ERROR)


def get_user_defined_log_level():
    v = sublime.active_window().active_view()
    level = v.settings().get('vintageous_log_level', 'ERROR')
    return getattr(logging, level.upper(), logging.ERROR)



# Use strings because we need to pass modes as arguments in
# Default.sublime-keymap and it's more readable.
class modes:
    """
    Vim modes.
    """
    COMMAND_LINE = 'mode_command_line'
    INSERT = 'mode_insert'
    INTERNAL_NORMAL = 'mode_internal_normal'
    NORMAL = 'mode_normal'
    OPERATOR_PENDING = 'mode_operator_pending'
    VISUAL = 'mode_visual'
    VISUAL_BLOCK = 'mode_visual_block'
    VISUAL_LINE = 'mode_visual_line'
    UNKNOWN = 'mode_unknown'
    REPLACE = 'mode_replace'
    NORMAL_INSERT = 'mode_normal_insert'
    SELECT ='mode_select'
    CTRL_X = 'mode_control_x'

    @staticmethod
    def to_friendly_name(mode):
        # if name == COMMAND_LINE:
            # return 'INSERT'
        if mode == modes.INSERT:
            return 'INSERT'
        if mode == modes.INTERNAL_NORMAL:
            return ''
        if mode == modes.NORMAL:
            return ''
        if mode == modes.OPERATOR_PENDING:
            return ''
        if mode == modes.VISUAL:
            return 'VISUAL'
        if mode == modes.VISUAL_BLOCK:
            return 'VISUAL BLOCK'
        if mode == modes.VISUAL_LINE:
            return 'VISUAL LINE'
        if mode == modes.UNKNOWN:
            return 'UNKNOWN'
        if mode == modes.REPLACE:
            return 'REPLACE'
        if mode == modes.NORMAL_INSERT:
            return 'INSERT'
        if mode == modes.SELECT:
            return 'SELECT'
        if mode == modes.CTRL_X:
            return 'Mode ^X'
        else:
            return 'REALLY UNKNOWN'


class input_types:
    """
    Types of input parsers.
    """
    INMEDIATE    = 1
    VIA_PANEL    = 2
    AFTER_MOTION = 3


class jump_directions:
    FORWARD = 1
    BACK = 0


def regions_transformer(view, f):
    sels = list(view.sel())
    new = []
    for sel in sels:
        region = f(view, sel)
        if not isinstance(region, sublime.Region):
            raise TypeError('sublime.Region required')
        new.append(region)
    view.sel().clear()
    view.sel().add_all(new)


def row_at(view, pt):
    return view.rowcol(pt)[0]


def col_at(view, pt):
    return view.rowcol(pt)[1]


@contextmanager
def gluing_undo_groups(view, state):
    state.gluing_sequence = True
    view.run_command('mark_undo_groups_for_gluing')
    yield
    view.run_command('glue_marked_undo_groups')
    state.gluing_sequence = False


def blink(times=4, delay=55):
    prefs = sublime.load_settings('Preferences.sublime-settings')
    if prefs.get('vintageous_visualbell') is False:
        return

    v = sublime.active_window().active_view()
    settings = v.settings()
    # Ensure we leave the setting as we found it.
    times = times if (times % 2) == 0 else times + 1

    def do_blink():
        nonlocal times
        if times > 0:
            settings.set('highlight_line', not settings.get('highlight_line'))
            times -= 1
            sublime.set_timeout(do_blink, delay)

    do_blink()


class IrreversibleTextCommand(sublime_plugin.TextCommand):
    """ Base class.

        The undo stack will ignore commands derived from this class. This is
        useful to prevent global state management commands from shadowing
        commands performing edits to the buffer, which are the important ones
        to keep in the undo history.
    """
    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)

    def run_(self, edit_token, kwargs):
        if kwargs and 'event' in kwargs:
            del kwargs['event']

        if kwargs:
            self.run(**kwargs)
        else:
            self.run()

    def run(self, **kwargs):
        pass


class IrreversibleMouseTextCommand(sublime_plugin.TextCommand):
    """ Base class.

        The undo stack will ignore commands derived from this class. This is
        useful to prevent global state management commands from shadowing
        commands performing edits to the buffer, which are the important ones
        to keep in the undo history.

        This command does not discard the 'event' parameter and so can receive
        mouse data.
    """
    def __init__(self, view):
        sublime_plugin.TextCommand.__init__(self, view)

    def run_(self, edit_token, kwargs):
        if kwargs:
            self.run(**kwargs)
        else:
            self.run()

    def run(self, **kwargs):
        pass


def next_non_white_space_char(view, pt, white_space='\t '):
    while (view.substr(pt) in white_space) and (pt <= view.size()):
        pt += 1
    return pt


def previous_non_white_space_char(view, pt, white_space='\t \n'):
    while view.substr(pt) in white_space and pt > 0:
        pt -= 1
    return pt


# deprecated
def previous_white_space_char(view, pt, white_space='\t '):
    while pt >= 0 and view.substr(pt) not in white_space:
        pt -= 1
    return pt


def move_backward_while(view, pt, func):
    while (pt >= 0) and func(pt):
        pt -= 1
    return pt


def is_at_eol(view, reg):
    return view.line(reg.b).b == reg.b


def is_at_bol(view, reg):
    return view.line(reg.b).a == reg.b


def translate_char(char):
    # FIXME: What happens to keys like <home>, <up>, etc? We shouln't be
    #        able to use those in some contexts, like as arguments to f, t...
    if char.lower() in ('<enter>', '<cr>'):
        return '\n'
    elif char.lower() in ('<sp>', '<space>'):
        return ' '
    elif char.lower() == '<lt>':
        return '<'
    elif char.lower() == '<tab>':
        return '\t'
    else:
        return char


@contextmanager
def restoring_sel(view):
    regs = list(view.sel())
    view.sel().clear()
    yield
    view.sel().clear()
    view.sel().add_all(regs)


class directions:
    NONE = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

########NEW FILE########
__FILENAME__ = xactions
# TODO: weird name to avoid init issues with state.py::State.
import sublime
import sublime_plugin

import re
from functools import partial

from Vintageous import local_logger
from Vintageous.state import _init_vintageous
from Vintageous.state import State
from Vintageous.vi import utils
from Vintageous.vi.constants import regions_transformer_reversed
from Vintageous.vi.core import ViTextCommandBase
from Vintageous.vi.core import ViWindowCommandBase
from Vintageous.vi.keys import KeySequenceTokenizer
from Vintageous.vi.keys import to_bare_command_name
from Vintageous.vi.keys import key_names
from Vintageous.vi.mappings import Mappings
from Vintageous.vi import mappings
from Vintageous.vi.utils import gluing_undo_groups
from Vintageous.vi.utils import IrreversibleTextCommand
from Vintageous.vi.utils import is_view
from Vintageous.vi.utils import modes
from Vintageous.vi.utils import regions_transformer
from Vintageous.vi.utils import restoring_sel
from Vintageous.vi import cmd_base
from Vintageous.vi import cmd_defs
from Vintageous.vi import search

_logger = local_logger(__name__)


class _vi_g_big_u(ViTextCommandBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            view.replace(edit, s, view.substr(s).upper())
            # reverse the resulting region so that _enter_normal_mode collapses the
            # selection as we want it.
            return sublime.Region(s.b, s.a)

        if mode not in (modes.INTERNAL_NORMAL,
                        modes.VISUAL,
                        modes.VISUAL_LINE,
                        modes.VISUAL_BLOCK):
            raise ValueError('bad mode: ' + mode)

        if motion is None and mode == modes.INTERNAL_NORMAL:
            raise ValueError('motion data required')

        if mode == modes.INTERNAL_NORMAL:
            self.save_sel()

            self.view.run_command(motion['motion'], motion['motion_args'])

            if self.has_sel_changed():
                regions_transformer(self.view, f)
            else:
                utils.blink()
        else:
                regions_transformer(self.view, f)

        self.enter_normal_mode(mode)


class _vi_gu(ViTextCommandBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            view.replace(edit, s, view.substr(s).lower())
            # reverse the resulting region so that _enter_normal_mode collapses the
            # selection as we want it.
            return sublime.Region(s.b, s.a)

        if mode not in (modes.INTERNAL_NORMAL,
                        modes.VISUAL,
                        modes.VISUAL_LINE,
                        modes.VISUAL_BLOCK):
            raise ValueError('bad mode: ' + mode)

        if motion is None and mode == modes.INTERNAL_NORMAL:
            raise ValueError('motion data required')

        if mode == modes.INTERNAL_NORMAL:
            self.save_sel()

            self.view.run_command(motion['motion'], motion['motion_args'])

            if self.has_sel_changed():
                regions_transformer(self.view, f)
            else:
                utils.blink()
        else:
                regions_transformer(self.view, f)

        self.enter_normal_mode(mode)


class _vi_gq(ViTextCommandBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, edit, mode=None, count=1, motion=None):
        def reverse(view, s):
            return sublime.Region(s.end(), s.begin())

        def shrink(view, s):
            if view.substr(s.b - 1) == '\n':
                return sublime.Region(s.a, s.b - 1)
            return s

        if mode in (modes.VISUAL, modes.VISUAL_LINE):
            # TODO: ST seems to always reformat whole paragraphs with
            #       'wrap_lines'.
            regions_transformer(self.view, shrink)
            regions_transformer(self.view, reverse)
            self.view.run_command('wrap_lines')
            self.enter_normal_mode(mode)
            return

        elif mode == modes.INTERNAL_NORMAL:
            if motion is None:
                raise ValueError('motion data required')

            self.save_sel()

            self.view.run_command(motion['motion'], motion['motion_args'])

            if self.has_sel_changed():
                self.save_sel()
                self.view.run_command('wrap_lines')
                self.view.sel().clear()
                self.view.sel().add_all(self.old_sel)
            else:
                utils.blink()

            self.enter_normal_mode(mode)

        else:
            raise ValueError('bad mode: ' + mode)


class _vi_u(IrreversibleTextCommand):
    def run(self, count=1):
        for i in range(count):
            self.view.run_command('undo')

        if self.view.has_non_empty_selection_region():
            def reverse(view, s):
                return sublime.Region(s.end(), s.begin())

            # TODO: xpos is misaligned after this.
            regions_transformer(self.view, reverse)
            self.view.window().run_command('_enter_normal_mode', {'mode': modes.VISUAL})


class _vi_ctrl_r(IrreversibleTextCommand):
    def run(self, count=1, mode=None):
        for i in range(count):
            self.view.run_command('redo')


class _vi_a(sublime_plugin.TextCommand):
    def run(self, edit, count=1, mode=None):
        def f(view, s):
            if view.substr(s.b) != '\n' and s.b < view.size():
                return sublime.Region(s.b + 1)
            return s

        if mode is None:
            raise ValueError('mode required')

        # TODO: We should probably not define the keys for these modes
        # in the first place.
        elif mode != modes.INTERNAL_NORMAL:
            return

        regions_transformer(self.view, f)
        self.view.window().run_command('_enter_insert_mode')


class _vi_c(ViTextCommandBase):
    def run(self, edit, count=1, mode=None, motion=None, register=None):
        def compact(view, s):
            if view.substr(s).strip():
                pt = utils.previous_non_white_space_char(view, s.b - 1,
                                                         white_space=' \t')
                return sublime.Region(s.a, pt + 1)
            return s

        if mode is None:
            raise ValueError('mode required')

        if (mode == modes.INTERNAL_NORMAL) and (motion is None):
            raise ValueError('motion required')

        self.save_sel()

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])

            # In these cases, Vim treats the motion differently and ignores
            # trailing white space.
            if ((mode == modes.INTERNAL_NORMAL) and
               (motion['motion'] in ('_vi_w', '_vi_big_w'))):
                    regions_transformer(self.view, compact)

            if not self.has_sel_changed():
                self.enter_insert_mode(mode)
                return

        self.view.run_command('right_delete')

        self.enter_insert_mode(mode)


class _enter_normal_mode(ViTextCommandBase):
    """
    The equivalent of pressing the Esc key in Vim.

    @mode
      The mode we're coming from, which should still be the current mode.

    @from_init
      Whether _enter_normal_mode has been called from _init_vintageous. This
      is important to know in order to not hide output panels when the user
      is only navigating files or clicking around, not pressing Esc.
    """
    def run(self, edit, mode=None, from_init=False):
        state = self.state

        self.view.window().run_command('hide_auto_complete')
        self.view.window().run_command('hide_overlay')

        if ((not from_init and (mode == modes.NORMAL) and not state.sequence) or
             not is_view(self.view)):
            # When _enter_normal_mode is requested from _init_vintageous, we
            # should not hide output panels; hide them only if the user
            # pressed Esc and we're not cancelling partial state data, or if a
            # panel has the focus.
            # XXX: We are assuming that state.sequence will always be empty
            #      when we do the check above. Is that so?
            # XXX: The 'not is_view(self.view)' check above seems to be
            #      redundant, since those views should be ignored by
            #      Vintageous altogether.
            self.view.window().run_command('hide_panel', {'cancel': True})

        self.view.settings().set('command_mode', True)
        self.view.settings().set('inverse_caret_state', True)

        # Exit replace mode.
        self.view.set_overwrite_status(False)

        state.enter_normal_mode()
        # XXX: st bug? if we don't do this, selections won't be redrawn
        self.view.run_command('_enter_normal_mode_impl', {'mode': mode})

        if state.glue_until_normal_mode and not state.gluing_sequence:
            if self.view.is_dirty():
                self.view.window().run_command('glue_marked_undo_groups')
                # We're exiting from insert mode or replace mode. Capture
                # the last native command as repeat data.
                state.repeat_data = ('native', self.view.command_history(0)[:2], mode, None)
            else:
                self.view.window().run_command('unmark_undo_groups_for_gluing')
            state.glue_until_normal_mode = False

        if mode == modes.INSERT and int(state.normal_insert_count) > 1:
            # TODO: Calculate size the view has grown by and place the caret
            # after the newly inserted text.
            sels = list(self.view.sel())
            self.view.sel().clear()
            new_sels = [sublime.Region(s.b + 1) if self.view.substr(s.b) != '\n'
                                                else s
                                                for s in sels]
            self.view.sel().add_all(new_sels)
            times = int(state.normal_insert_count) - 1
            state.normal_insert_count = '1'
            self.view.window().run_command('_vi_dot', {
                                'count': times,
                                'mode': mode,
                                'repeat_data': state.repeat_data,
                                })
            self.view.sel().clear()
            self.view.sel().add_all(new_sels)

        state.update_xpos(force=True)
        sublime.status_message('')


class _enter_normal_mode_impl(sublime_plugin.TextCommand):
    def run(self, edit, mode=None):
        def f(view, s):
            _logger().info(
                '[_enter_normal_mode_impl] entering normal mode from {0}'
                .format(mode))
            if mode == modes.INSERT:
                if view.line(s.b).a != s.b:
                    return sublime.Region(s.b - 1)

                return sublime.Region(s.b)

            if mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.b)

            if mode == modes.VISUAL:
                # save selections for gv
                # But only if there are non-empty sels. We might be in visual
                # mode and not have non-empty sels because we've just existed
                # from an action.
                if self.view.has_non_empty_selection_region():
                    self.view.add_regions('visual_sel', list(self.view.sel()))
                if s.a < s.b:
                    r = sublime.Region(s.b - 1)
                    if view.substr(r.b) == '\n':
                        r.b -= 1
                    return sublime.Region(r.b)
                return sublime.Region(s.b)

            if mode in (modes.VISUAL_LINE, modes.VISUAL_BLOCK):
                # save selections for gv
                # But only if there are non-empty sels. We might be in visual
                # mode and not have non-empty sels because we've just existed
                # from an action.
                if self.view.has_non_empty_selection_region():
                    self.view.add_regions('visual_sel', list(self.view.sel()))

                if s.a < s.b:
                    pt = s.b - 1
                    if (view.substr(pt) == '\n') and not view.line(pt).empty():
                        pt -= 1
                    return sublime.Region(pt)
                else:
                    return sublime.Region(s.b)

            if mode == modes.SELECT:
                return sublime.Region(s.begin())

            return sublime.Region(s.b)

        if mode == modes.UNKNOWN:
            return

        if (len(self.view.sel()) > 1) and (mode == modes.NORMAL):
            sel = self.view.sel()[0]
            self.view.sel().clear()
            self.view.sel().add(sel)

        regions_transformer(self.view, f)

        self.view.erase_regions('vi_search')
        self.view.run_command('_vi_adjust_carets', {'mode': mode})


class _enter_select_mode(ViWindowCommandBase):
    def run(self, mode=None, count=1):
        self.state.enter_select_mode()

        view = self.window.active_view()

        # If there are no visual selections, do some work work for the user.
        if not view.has_non_empty_selection_region():
            self.window.run_command('find_under_expand')

        state = State(view)
        state.display_status()


class _enter_insert_mode(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        self.view.settings().set('inverse_caret_state', False)
        self.view.settings().set('command_mode', False)

        self.state.enter_insert_mode()
        self.state.normal_insert_count = str(count)
        self.state.display_status()


class _enter_visual_mode(ViTextCommandBase):
    def run(self, edit, mode=None):

        state = self.state
        if state.mode == modes.VISUAL:
            self.view.run_command('_enter_normal_mode', {'mode': mode})
            return
        self.view.run_command('_enter_visual_mode_impl', {'mode': mode})

        if any(s.empty() for s in self.view.sel()):
            return

        state.enter_visual_mode()
        state.display_status()


class _enter_visual_mode_impl(sublime_plugin.TextCommand):
    """
    Transforms the view's selections. We don't do this inside the
    EnterVisualMode window command because ST seems to neglect to repaint the
    selections. (bug?)
    """
    def run(self, edit, mode=None):
        def f(view, s):
            if mode == modes.VISUAL_LINE:
                return sublime.Region(s.a, s.b)
            else:
                if s.empty() and (s.b == self.view.size()):
                    utils.blink()
                    return s
                return sublime.Region(s.b, s.b + 1)

        regions_transformer(self.view, f)


class _enter_visual_line_mode(ViTextCommandBase):
    def run(self, edit, mode=None):

        state = self.state
        if state.mode == modes.VISUAL_LINE:
            self.view.run_command('_enter_normal_mode', {'mode': mode})
            return

        # FIXME: 'V' from normal mode sets mode to internal normal.
        if mode in (modes.NORMAL, modes.INTERNAL_NORMAL):
            # Abort if we are at EOF -- no newline char to hold on to.
            if any(s.b == self.view.size() for s in self.view.sel()):
                utils.blink()
                return

        self.view.run_command('_enter_visual_line_mode_impl', {'mode': mode})
        state.enter_visual_line_mode()
        state.display_status()


class _enter_visual_line_mode_impl(sublime_plugin.TextCommand):
    """
    Transforms the view's selections.
    """
    def run(self, edit, mode=None):
        def f(view, s):
            if mode == modes.VISUAL:
                if s.a < s.b:
                    if view.substr(s.b - 1) != '\n':
                        return sublime.Region(view.line(s.a).a,
                                              view.full_line(s.b - 1).b)
                    else:
                        return sublime.Region(view.line(s.a).a, s.b)
                else:
                    if view.substr(s.a - 1) != '\n':
                        return sublime.Region(view.full_line(s.a - 1).b,
                                              view.line(s.b).a)
                    else:
                        return sublime.Region(s.a, view.line(s.b).a)
            else:
                return view.full_line(s.b)

        regions_transformer(self.view, f)


class _enter_replace_mode(ViTextCommandBase):
    def run(self, edit):
        def f(view, s):
            return sublime.Region(s.b)

        state = self.state
        state.settings.view['command_mode'] = False
        state.settings.view['inverse_caret_state'] = False
        state.view.set_overwrite_status(True)
        state.enter_replace_mode()
        regions_transformer(self.view, f)
        state.display_status()
        state.reset()


# TODO: Remove this command once we don't need it any longer.
class ToggleMode(ViWindowCommandBase):
    def run(self):
        value = self.window.active_view().settings().get('command_mode')
        self.window.active_view().settings().set('command_mode', not value)
        self.window.active_view().settings().set('inverse_caret_state', not value)
        print("command_mode status:", not value)

        state = self.state
        if not self.window.active_view().settings().get('command_mode'):
            state.mode = modes.INSERT
        sublime.status_message('command mode status: %s' % (not value))


class PressKeys(ViWindowCommandBase):
    """
    Runs sequences of keys representing Vim commands.

    For example: fngU5l

    @keys
        Key sequence to be run.
    @repeat_count
        Count to be applied when repeating through the '.' command.
    @check_user_mappings
        Whether user mappings should be consulted to expand key sequences.
    """
    def run(self, keys, repeat_count=None, check_user_mappings=True):
        state = self.state
        _logger().info("[PressKeys] seq received: {0} mode: {1}"
                                                    .format(keys, state.mode))
        initial_mode = state.mode
        # Disable interactive prompts. For example, to supress interactive
        # input collection in /foo<CR>.
        state.non_interactive = True

        # First, run any motions coming before the first action. We don't keep
        # these in the undo stack, but they will still be repeated via '.'.
        # This ensures that undoing will leave the caret where the  first
        # editing action started. For example, 'lldl' would skip 'll' in the
        # undo history, but store the full sequence for '.' to use.
        leading_motions = ''
        for key in KeySequenceTokenizer(keys).iter_tokenize():
            self.window.run_command('press_key', {
                                'key': key,
                                'do_eval': False,
                                'repeat_count': repeat_count,
                                'check_user_mappings': check_user_mappings
                                })
            if state.action:
                # The last key press has caused an action to be primed. That
                # means there are no more leading motions. Break out of here.
                _logger().info('[PressKeys] first action found in {0}'
                                                      .format(state.sequence))
                state.reset_command_data()
                if state.mode == modes.OPERATOR_PENDING:
                    state.mode = modes.NORMAL
                break

            elif state.runnable():
                # Run any primed motion.
                leading_motions += state.sequence
                state.eval()
                state.reset_command_data()

            else:
                # XXX: When do we reach here?
                state.eval()

        if state.must_collect_input:
            # State is requesting more input, so this is the last command in
            # the sequence and it needs more input.
            self.collect_input()
            return

        # Strip the already run commands.
        if leading_motions:
            if ((len(leading_motions) == len(keys)) and
                (not state.must_collect_input)):
                    return

            _logger().info('[PressKeys] original seq/leading motions: {0}/{1}'
                                               .format(keys, leading_motions))
            keys = keys[len(leading_motions):]
            _logger().info('[PressKeys] seq stripped to {0}'.format(keys))

        if not (state.motion and not state.action):
            with gluing_undo_groups(self.window.active_view(), state):
                try:
                    for key in KeySequenceTokenizer(keys).iter_tokenize():
                        if key.lower() == key_names.ESC:
                            # XXX: We should pass a mode here?
                            self.window.run_command('_enter_normal_mode')
                            continue

                        elif state.mode not in (modes.INSERT, modes.REPLACE):
                            self.window.run_command('press_key', {
                                    'key': key,
                                    'repeat_count': repeat_count,
                                    'check_user_mappings': check_user_mappings
                                    })
                        else:
                            # TODO: remove active_view; window will route the
                            #       cmd.
                            self.window.active_view().run_command('insert', {
                                                           'characters': key})
                    if not state.must_collect_input:
                        return
                finally:
                    state.non_interactive = False
                    # Ensure we set the full command for '.' to use, but don't
                    # store '.' alone.
                    if (leading_motions + keys) not in ('.', 'u', '<C-r>'):
                            state.repeat_data = (
                                        'vi', (leading_motions + keys),
                                        initial_mode, None)

        # We'll reach this point if we have a command that requests input
        # whose input parser isn't satistied. For example, `/foo`. Note that
        # `/foo<CR>`, on the contrary, would have satisfied the parser.
        _logger().info('[PressKeys] unsatisfied parser: {0} {1}'
                                          .format(state.action, state.motion))
        if (state.action and state.motion):
            # We have a parser an a motion that can collect data. Collect data
            # interactively.
            motion_data = state.motion.translate(state) or None

            if motion_data is None:
                utils.blink()
                state.reset_command_data()
                return

            motion_data['motion_args']['default'] = state.motion._inp
            self.window.run_command(motion_data['motion'],
                                    motion_data['motion_args'])
            return

        self.collect_input()

    def collect_input(self):
        try:
            command = None
            if self.state.motion and self.state.action:
                if self.state.motion.accept_input:
                    command = self.state.motion
                else:
                    command = self.state.action
            else:
                command = self.state.action or self.state.motion

            parser_def = command.input_parser
            _logger().info('[PressKeys] last attemp to collect input: {0}'
                                                  .format(parser_def.command))
            if parser_def.interactive_command:
                self.window.run_command(parser_def.interactive_command,
                                        {parser_def.input_param: command._inp}
                                       )
        except IndexError:
            _logger().info('[Vintageous] could not find a command to collect'
                           'more user input')
            utils.blink()
        finally:
            self.state.non_interactive = False


class PressKey(ViWindowCommandBase):
    """
    Core command. It interacts with the global state each time a key is
    pressed.

    @key
        Key pressed.
    @repeat_count
        Count to be used when repeating through the '.' command.
    @do_eval
        Whether to evaluate the global state when it's in a runnable
        state. Most of the time, the default value of `True` should be
        used. Set to `False` when you want to manually control
        the global state's evaluation. For example, this is what the
        PressKeys command does.
    """

    def run(self, key, repeat_count=None, do_eval=True, check_user_mappings=True):
        _logger().info("[PressKey] pressed: {0}".format(key))

        state = self.state

        # If the user has made selections with the mouse, we may be in an
        # inconsistent state. Try to remedy that.
        if (state.view.has_non_empty_selection_region() and
            state.mode not in (modes.VISUAL,
                               modes.VISUAL_LINE,
                               modes.VISUAL_BLOCK,
                               modes.SELECT)):
                _init_vintageous(state.view)


        if key.lower() == '<esc>':
            self.window.run_command('_enter_normal_mode', {'mode': state.mode})
            state.reset_command_data()
            return

        state.sequence += key
        if not state.recording_macro:
            state.display_status()
            # sublime.status_message(state.sequence)
        else:
            sublime.status_message('[Vintageous] Recording')
        if state.capture_register:
            state.register = key
            state.partial_sequence = ''
            return

        # if capturing input, we shall not pass this point
        if state.must_collect_input:
            state.process_user_input2(key)
            if state.runnable():
                _logger().info('[PressKey] state holds a complete command.')
                if do_eval:
                    _logger().info('[PressKey] evaluating complete command')
                    state.eval()
                    state.reset_command_data()
            return

        if repeat_count:
            state.action_count = str(repeat_count)

        if self.handle_counts(key, repeat_count):
            return

        state.partial_sequence += key
        _logger().info("[PressKey] sequence {0}".format(state.sequence))
        _logger().info("[PressKey] partial sequence {0}".format(state.partial_sequence))

        # key_mappings = KeyMappings(self.window.active_view())
        key_mappings = Mappings(state)
        if check_user_mappings and key_mappings.incomplete_user_mapping():
            _logger().info("[PressKey] incomplete user mapping: {0}".format(state.partial_sequence))
            # for example, we may have typed 'aa' and there's an 'aaa' mapping.
            # we need to keep collecting input.
            return

        _logger().info('[PressKey] getting cmd for seq/partial seq in (mode): {0}/{1} ({2})'.format(state.sequence,
                                                                                                    state.partial_sequence,
                                                                                                    state.mode))
        command = key_mappings.resolve(check_user_mappings=check_user_mappings)

        if isinstance(command, cmd_defs.ViOpenRegister):
            _logger().info('[PressKey] requesting register name')
            state.capture_register = True
            return

        # XXX: This doesn't seem to be correct. If we are in OPERATOR_PENDING mode, we should
        # most probably not have to wipe the state.
        if isinstance(command, mappings.Mapping):
            if do_eval:
                new_keys = command.mapping
                if state.mode == modes.OPERATOR_PENDING:
                    command_name = command.mapping
                    new_keys = state.sequence[:-len(state.partial_sequence)] + command.mapping
                reg = state.register
                acount = state.action_count
                mcount = state.motion_count
                state.reset_command_data()
                state.register = reg
                state.motion_count = mcount
                state.action_count = acount
                state.mode = modes.NORMAL
                _logger().info('[PressKey] running user mapping {0} via press_keys starting in mode {1}'.format(new_keys, state.mode))
                self.window.run_command('press_keys', {'keys': new_keys, 'check_user_mappings': False})
            return

        if isinstance(command, cmd_defs.ViOpenNameSpace):
            # Keep collecing input to complete the sequence. For example, we
            # may have typed 'g'.
            _logger().info("[PressKey] opening namespace: {0}".format(state.partial_sequence))
            return

        elif isinstance(command, cmd_base.ViMissingCommandDef):
            bare_seq = to_bare_command_name(state.sequence)

            if state.mode == modes.OPERATOR_PENDING:
                # We might be looking at a command like 'dd'. The first 'd' is
                # mapped for normal mode, but the second is missing in
                # operator pending mode, so we get a missing command. Try to
                # build the full command now.
                #
                # Exclude user mappings, since they've already been given a
                # chance to evaluate.
                command = key_mappings.resolve(sequence=bare_seq,
                                                   mode=modes.NORMAL,
                                                   check_user_mappings=False)
            else:
                command = key_mappings.resolve(sequence=bare_seq)

            if isinstance(command, cmd_base.ViMissingCommandDef):
                _logger().info('[PressKey] unmapped sequence: {0}'.format(state.sequence))
                utils.blink()
                state.mode = modes.NORMAL
                state.reset_command_data()
                return

        if (state.mode == modes.OPERATOR_PENDING and
            isinstance(command, cmd_defs.ViOperatorDef)):
                # TODO: This may be unreachable code by now. ???
                # we're expecting a motion, but we could still get an action.
                # For example, dd, g~g~ or g~~
                # remove counts
                action_seq = to_bare_command_name(state.sequence)
                _logger().info('[PressKey] action seq: {0}'.format(action_seq))
                command = key_mappings.resolve(sequence=action_seq, mode=modes.NORMAL)
                # TODO: Make _missing a command.
                if isinstance(command, cmd_base.ViMissingCommandDef):
                    _logger().info("[PressKey] unmapped sequence: {0}".format(state.sequence))
                    state.reset_command_data()
                    return

                if not command['motion_required']:
                    state.mode = modes.NORMAL

        state.set_command(command)

        _logger().info("[PressKey] '{0}'' mapped to '{1}'".format(state.partial_sequence, command))

        if state.mode == modes.OPERATOR_PENDING:
            state.reset_partial_sequence()

        if do_eval:
            state.eval()

    def handle_counts(self, key, repeat_count):
        """
        Returns `True` if the processing of the current key needs to stop.
        """
        state = State(self.window.active_view())
        if not state.action and key.isdigit():
            if not repeat_count and (key != '0' or state.action_count) :
                _logger().info('[PressKey] action count digit: {0}'.format(key))
                state.action_count += key
                return True

        if (state.action and (state.mode == modes.OPERATOR_PENDING) and
            key.isdigit()):
                if not repeat_count and (key != '0' or state.motion_count):
                    _logger().info('[PressKey] motion count digit: {0}'.format(key))
                    state.motion_count += key
                    return True


class _vi_dot(ViWindowCommandBase):
    def run(self, mode=None, count=None, repeat_data=None):
        state = self.state
        state.reset_command_data()
        if state.mode == modes.INTERNAL_NORMAL:
            state.mode = modes.NORMAL

        if repeat_data is None:
            _logger().info('[_vi_dot] nothing to repeat')
            return

        # TODO: Find out if the user actually meant '1'.
        if count and count == 1:
            count = None

        type_, seq_or_cmd, old_mode, visual_data = repeat_data
        _logger().info('[_vi_dot] type: {0} seq or cmd: {1} old mode: {2}'.format(type_, seq_or_cmd, old_mode))

        if visual_data and (mode != modes.VISUAL):
            state.restore_visual_data(visual_data)
        elif not visual_data and (mode == modes.VISUAL):
            # Can't repeat normal mode commands in visual mode.
            utils.blink()
            return
        elif mode not in (modes.VISUAL, modes.VISUAL_LINE, modes.NORMAL,
                          modes.INTERNAL_NORMAL, modes.INSERT):
            utils.blink()
            return

        if type_ == 'vi':
            self.window.run_command('press_keys', {'keys': seq_or_cmd,
                                                   'repeat_count': count})
        elif type_ == 'native':
            sels = list(self.window.active_view().sel())
            # FIXME: We're not repeating as we should. It's the motion that
            # should receive this count.
            for i in range(count or 1):
                self.window.run_command(*seq_or_cmd)
            # FIXME: What happens in visual mode?
            self.window.active_view().sel().clear()
            self.window.active_view().sel().add_all(sels)
        else:
            raise ValueError('bad repeat data')

        self.window.run_command('_enter_normal_mode', {'mode': mode})
        state.repeat_data = repeat_data
        state.update_xpos()


class _vi_dd_action(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True
    _yanks_linewise = False
    _populates_small_delete_register = False

    def run(self, edit, mode=None, count=1):
        def f(view, s):
            # We've made a selection with _vi_cc_motion just before this.
            if mode == modes.INTERNAL_NORMAL:
                view.erase(edit, s)
                if utils.row_at(self.view, s.a) != utils.row_at(self.view, self.view.size()):
                    pt = utils.next_non_white_space_char(view, s.a, white_space=' \t')
                else:
                    pt = utils.next_non_white_space_char(view,
                                                         self.view.line(s.a).a,
                                                         white_space=' \t')

                return sublime.Region(pt, pt)
            return s

        self.view.run_command('_vi_dd_motion', {'mode': mode, 'count': count})

        state = self.state
        state.registers.yank(self)

        row = [self.view.rowcol(s.begin())[0] for s in self.view.sel()][0]
        regions_transformer_reversed(self.view, f)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(self.view.text_point(row, 0)))


class _vi_dd_motion(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=1):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                end = view.text_point(utils.row_at(self.view, s.b) + (count - 1), 0)
                begin = view.line(s.b).a
                if ((utils.row_at(self.view, end) == utils.row_at(self.view, view.size())) and
                    (view.substr(begin - 1) == '\n')):
                        begin -= 1

                return sublime.Region(begin, view.full_line(end).b)

            return s

        regions_transformer(self.view, f)


class _vi_cc_motion(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                if view.line(s.b).empty():
                    return s

                end = view.text_point(utils.row_at(self.view, s.b) + (count - 1), 0)
                begin = view.line(s.b).a
                begin = utils.next_non_white_space_char(view, begin, white_space=' \t')
                return sublime.Region(begin, view.line(end).b)

            return s

        regions_transformer(self.view, f)


class _vi_cc_action(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True
    _yanks_linewise = False
    _populates_small_delete_register = False

    def run(self, edit, mode=None, count=1, register='"'):
        self.save_sel()
        self.view.run_command('_vi_cc_motion', {'mode': mode, 'count': count})

        state = self.state

        if self.has_sel_changed():
            state.registers.yank(self)
            self.view.run_command('right_delete')

        self.enter_insert_mode(mode)
        self.set_xpos(state)


class _vi_visual_o(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=1):
        def f(view, s):
            # FIXME: In Vim, o doesn't work in modes.VISUAL_LINE, but ST can't move the caret while
            # in modes.VISUAL_LINE, so we enable this for convenience. Change when/if ST can move
            # the caret while in modes.VISUAL_LINE.
            if mode in (modes.VISUAL, modes.VISUAL_LINE):
                return sublime.Region(s.b, s.a)
            return s

        regions_transformer(self.view, f)
        self.view.show(self.view.sel()[0].b, False)


class _vi_yy(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True
    _yanks_linewise = True

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):
            if count > 1:
                row, col = self.view.rowcol(s.b)
                end = view.text_point(row + count - 1, 0)
                return sublime.Region(view.line(s.a).a, view.full_line(end).b)

            return view.full_line(s.b)

        def restore():
            self.view.sel().clear()
            self.view.sel().add_all(list(self.old_sel))

        if mode != modes.INTERNAL_NORMAL:
            utils.blink()
            raise ValueError('wrong mode')

        self.save_sel()
        regions_transformer(self.view, select)

        state = self.state
        self.outline_target()
        state.registers.yank(self, register)
        restore()
        self.enter_normal_mode(mode)


class _vi_y(ViTextCommandBase):

    _can_yank = True
    _populates_small_delete_register = True

    def run(self, edit, mode=None, count=1, motion=None, register=None):
        def f(view, s):
            return sublime.Region(s.end(), s.begin())

        if mode == modes.INTERNAL_NORMAL:
            if motion is None:
                raise ValueError('bad args')
            self.view.run_command(motion['motion'], motion['motion_args'])
            self.outline_target()

        elif mode not in (modes.VISUAL, modes.VISUAL_LINE, modes.VISUAL_BLOCK):
            return

        state = self.state
        state.registers.yank(self, register)
        regions_transformer(self.view, f)
        self.enter_normal_mode(mode)


class _vi_d(ViTextCommandBase):

    _can_yank = True
    _populates_small_delete_register = True

    def run(self, edit, mode=None, count=1, motion=None, register=None):
        def reverse(view, s):
            return sublime.Region(s.end(), s.begin())

        if mode not in (modes.INTERNAL_NORMAL, modes.VISUAL,
                        modes.VISUAL_LINE):
            raise ValueError('wrong mode')

        if mode == modes.INTERNAL_NORMAL and not motion:
            raise ValueError('missing motion')

        if motion:
            self.save_sel()

            self.view.run_command(motion['motion'], motion['motion_args'])

            # The motion has failed, so abort.
            if not self.has_sel_changed():
                utils.blink()
                self.enter_normal_mode(mode)
                return

        state = self.state
        state.registers.yank(self, register)

        self.view.run_command('left_delete')
        self.view.run_command('_vi_adjust_carets')

        self.enter_normal_mode(mode)


class _vi_big_a(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        def f(view, s):
            if mode == modes.VISUAL_BLOCK:
                if self.view.substr(s.b - 1) == '\n':
                    return sublime.Region(s.end() - 1)
                return sublime.Region(s.end())

            elif mode == modes.VISUAL:
                pt = s.b
                if self.view.substr(s.b - 1) == '\n':
                    pt -= 1
                if s.a > s.b:
                    pt = view.line(s.a).a
                return sublime.Region(pt)

            elif mode == modes.VISUAL_LINE:
                if s.a < s.b:
                    if s.b < view.size():
                        return sublime.Region(s.end() - 1)
                    return sublime.Region(s.end())
                return sublime.Region(s.begin())

            elif mode != modes.INTERNAL_NORMAL:
                return s

            if s.b == view.size():
                return s

            hard_eol = self.view.line(s.b).end()
            return sublime.Region(hard_eol, hard_eol)

        if mode == modes.SELECT:
            self.view.window().run_command('find_all_under')
            return

        regions_transformer(self.view, f)

        self.enter_insert_mode(mode)


class _vi_big_i(ViTextCommandBase):
    def run(self, edit, count=1, mode=None):
        def f(view, s):
            if mode == modes.VISUAL_BLOCK:
                return sublime.Region(s.begin())
            elif mode == modes.VISUAL:
                pt = view.line(s.a).a
                if s.a > s.b:
                    pt = s.b
                return sublime.Region(pt)
            elif mode == modes.VISUAL_LINE:
                line = view.line(s.a)
                pt = utils.next_non_white_space_char(view, line.a)
                return sublime.Region(pt)
            elif mode != modes.INTERNAL_NORMAL:
                return s
            line = view.line(s.b)
            pt = utils.next_non_white_space_char(view, line.a)
            return sublime.Region(pt, pt)

        regions_transformer(self.view, f)

        self.enter_insert_mode(mode)


class _vi_m(ViTextCommandBase):
    def run(self, edit, mode=None, count=1, character=None):
        state = self.state
        state.marks.add(character, self.view)

        # TODO: What if we are in visual mode?
        self.enter_normal_mode(mode)


class _vi_quote(ViTextCommandBase):
    """
    """
    def run(self, edit, mode=None, character=None, count=1):
        def f(view, s):
            if mode == modes.VISUAL:
                if s.a <= s.b:
                    if address.b < s.b:
                        return sublime.Region(s.a + 1, address.b)
                    else:
                        return sublime.Region(s.a, address.b)
                else:
                    return sublime.Region(s.a + 1, address.b)

            elif mode == modes.NORMAL:
                return address

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(view.full_line(s.b).b,
                                      view.line(address.b).a)

            return s

        state = self.state
        address = state.marks.get_as_encoded_address(character)

        if address is None:
            return

        if isinstance(address, str):
            if not address.startswith('<command'):
                self.view.window().open_file(address, sublime.ENCODED_POSITION)
            else:
                # We get a command in this form: <command _vi_double_quote>
                self.view.run_command(address.split(' ')[1][:-1])
            return

        regions_transformer(self.view, f)


class _vi_backtick(ViTextCommandBase):
    def run(self, edit, count=1, mode=None, character=None):
        def f(view, s):
            if mode == modes.VISUAL:
                if s.a <= s.b:
                    if address.b < s.b:
                        return sublime.Region(s.a + 1, address.b)
                    else:
                        return sublime.Region(s.a, address.b)
                else:
                    return sublime.Region(s.a + 1, address.b)
            elif mode == modes.NORMAL:
                return address
            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, address.b)

            return s

        state = self.state
        address = state.marks.get_as_encoded_address(character, exact=True)

        if address is None:
            return

        if isinstance(address, str):
            if not address.startswith('<command'):
                self.view.window().open_file(address, sublime.ENCODED_POSITION)
            return

        # This is a motion in a composite command.
        regions_transformer(self.view, f)


class _vi_quote_quote(IrreversibleTextCommand):
    next_command = 'jump_back'

    def run(self):
        current = _vi_quote_quote.next_command
        self.view.window().run_command(current)
        _vi_quote_quote.next_command = ('jump_forward' if (current ==
                                                            'jump_back')
                                                       else 'jump_back')


class _vi_big_d(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True

    def run(self, edit, mode=None, count=1, register=None):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                if count == 1:
                    if view.line(s.b).size() > 0:
                        eol = view.line(s.b).b
                        return sublime.Region(s.b, eol)
                    return s
            return s

        self.save_sel()
        regions_transformer(self.view, f)

        state = self.state
        state.registers.yank(self)

        self.view.run_command('left_delete')

        self.enter_normal_mode(mode)


class _vi_big_c(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True

    def run(self, edit, mode=None, count=1, register=None):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                if count == 1:
                    if view.line(s.b).size() > 0:
                        eol = view.line(s.b).b
                        return sublime.Region(s.b, eol)
                    return s
            return s

        self.save_sel()
        regions_transformer(self.view, f)

        state = self.state
        state.registers.yank(self)

        empty = [s for s  in list(self.view.sel()) if s.empty()]
        self.view.add_regions('vi_empty_sels', empty)
        for r in empty:
            self.view.sel().subtract(r)

        self.view.run_command('right_delete')

        self.view.sel().add_all(self.view.get_regions('vi_empty_sels'))
        self.view.erase_regions('vi_empty_sels')

        self.enter_insert_mode(mode)


class _vi_big_s_action(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True

    def run(self, edit, mode=None, count=1, register=None):
        def sel_line(view, s):
            if mode == modes.INTERNAL_NORMAL:
                if count == 1:
                    if view.line(s.b).size() > 0:
                        eol = view.line(s.b).b
                        begin = view.line(s.b).a
                        begin = utils.next_non_white_space_char(view, begin, white_space=' \t')
                        return sublime.Region(begin, eol)
                    return s
            return s

        regions_transformer(self.view, sel_line)

        state = self.state
        state.registers.yank(self, register)

        empty = [s for s  in list(self.view.sel()) if s.empty()]
        self.view.add_regions('vi_empty_sels', empty)
        for r in empty:
            self.view.sel().subtract(r)

        self.view.run_command('right_delete')

        self.view.sel().add_all(self.view.get_regions('vi_empty_sels'))
        self.view.erase_regions('vi_empty_sels')
        self.view.run_command('reindent', {'force_indent': False})

        self.enter_insert_mode(mode)


class _vi_s(ViTextCommandBase):
    """
    Implementation of Vim's 's' action.
    """
    # Yank config data.
    _can_yank = True
    _populates_small_delete_register = True

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):
            if mode == modes.INTERNAL_NORMAL:
                if view.line(s.b).empty():
                    return sublime.Region(s.b)
                return sublime.Region(s.b, s.b + count)
            return sublime.Region(s.begin(), s.end())

        if mode not in (modes.VISUAL,
                        modes.VISUAL_LINE,
                        modes.VISUAL_BLOCK,
                        modes.INTERNAL_NORMAL):
            # error?
            utils.blink()
            self.enter_normal_mode(mode)

        self.save_sel()

        regions_transformer(self.view, select)

        if not self.has_sel_changed() and mode == modes.INTERNAL_NORMAL:
            self.enter_insert_mode(mode)
            return

        state = self.state
        state.registers.yank(self, register)
        self.view.run_command('right_delete')

        self.enter_insert_mode(mode)


class _vi_x(ViTextCommandBase):
    """
    Implementation of Vim's x action.
    """
    _can_yank = True
    _populates_small_delete_register = True

    def line_end(self, pt):
        return self.view.line(pt).end()

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):
            if mode == modes.INTERNAL_NORMAL:
                limit = self.line_end(s.b)
                return sublime.Region(s.b, min(s.b + count, limit))
            return s

        if mode not in (modes.VISUAL,
                        modes.VISUAL_LINE,
                        modes.VISUAL_BLOCK,
                        modes.INTERNAL_NORMAL):
            # error?
            utils.blink()
            self.enter_normal_mode(mode)

        regions_transformer(self.view, select)
        self.state.registers.yank(self, register)
        self.view.run_command('right_delete')

        self.enter_normal_mode(mode)


class _vi_r(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True
    _populates_small_delete_register = True

    def run(self, edit, mode=None, count=1, register=None, char=None):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                pt = s.b + count
                fragments = view.split_by_newlines(sublime.Region(s.a, pt))

                new_framents = []
                for fr in fragments:
                    new_framents.append(char * len(fr))
                text = '\n'.join(new_framents)

                view.replace(edit, sublime.Region(s.a, pt), text)

                if char == '\n':
                    return sublime.Region(s.b + 1)
                else:
                    return sublime.Region(s.b)

            if mode in (modes.VISUAL, modes.VISUAL_LINE, modes.VISUAL_BLOCK):
                ends_in_newline = (view.substr(s.end() - 1) == '\n')
                fragments = view.split_by_newlines(s)

                new_framents = []
                for fr in fragments:
                    new_framents.append(char * len(fr))
                text = '\n'.join(new_framents)

                if ends_in_newline:
                    text += '\n'

                view.replace(edit, s, text)

                if char == '\n':
                    return sublime.Region(s.begin() + 1)
                else:
                    return sublime.Region(s.begin())

        if char is None:
            raise ValueError('bad parameters')

        char = utils.translate_char(char)

        state = self.state
        state.registers.yank(self, register)
        regions_transformer(self.view, f)

        self.enter_normal_mode(mode)


class _vi_less_than_less_than_motion(sublime_plugin.TextCommand):
    def run(self, edit, count=None, mode=None):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                if count > 1:
                    begin = view.line(s.begin()).a
                    pt = view.text_point(view.rowcol(begin)[0] + (count - 1), 0)
                    end = view.line(pt).b
                    return sublime.Region(begin, end)
            return s

        regions_transformer(self.view, f)


class _vi_less_than_less_than(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=None):
        def f(view, s):
            bol = view.line(s.begin()).a
            pt = utils.next_non_white_space_char(view, bol, white_space='\t ')
            return sublime.Region(pt)

        self.view.run_command('_vi_less_than_less_than_motion', {'mode': mode, 'count': count})
        self.view.run_command('unindent')
        regions_transformer(self.view, f)


class _vi_equal_equal(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        def f(view, s):
            return sublime.Region(s.begin())

        def select():
            s0 = self.view.sel()[0]
            end_row = utils.row_at(self.view, s0.b) + (count - 1)
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(s0.begin(),
                                self.view.text_point(end_row, 1)))

        if count > 1:
            select()

        self.view.run_command('reindent', {'force_indent': False})

        regions_transformer(self.view, f)
        self.enter_normal_mode(mode)


class _vi_greater_than_greater_than(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        def f(view, s):
            bol = view.line(s.begin()).a
            pt = utils.next_non_white_space_char(view, bol, white_space='\t ')
            return sublime.Region(pt)

        def select():
            s0 = self.view.sel()[0]
            end_row = utils.row_at(self.view, s0.b) + (count - 1)
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(s0.begin(),
                                self.view.text_point(end_row, 1)))

        if count > 1:
            select()

        self.view.run_command('indent')

        regions_transformer(self.view, f)
        self.enter_normal_mode(mode)


class _vi_greater_than(ViTextCommandBase):
    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            return sublime.Region(s.begin())

        def indent_from_begin(view, s, level=1):
            block = '\t' if not translate else ' ' * size
            self.view.insert(edit, s.begin(), block * level)
            return sublime.Region(s.begin() + 1)

        if mode == modes.VISUAL_BLOCK:
            translate = self.view.settings().get('translate_tabs_to_spaces')
            size = self.view.settings().get('tab_size')
            indent = partial(indent_from_begin, level=count)

            regions_transformer_reversed(self.view, indent)
            regions_transformer(self.view, f)

            # Restore only the first sel.
            first = self.view.sel()[0]
            self.view.sel().clear()
            self.view.sel().add(first)
            self.enter_normal_mode(mode)
            return

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])
        elif mode not in (modes.VISUAL, modes.VISUAL_LINE):
            utils.blink()
            return

        for i in range(count):
            self.view.run_command('indent')

        regions_transformer(self.view, f)
        self.enter_normal_mode(mode)


class _vi_less_than(ViTextCommandBase):
    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            return sublime.Region(s.begin())

        # Note: Vim does not unindent in visual block mode.

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])
        elif mode not in (modes.VISUAL, modes.VISUAL_LINE):
            utils.blink()
            return

        for i in range(count):
            self.view.run_command('unindent')

        regions_transformer(self.view, f)
        self.enter_normal_mode(mode)


class _vi_equal(ViTextCommandBase):
    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            return sublime.Region(s.begin())

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])
        elif mode not in (modes.VISUAL, modes.VISUAL_LINE):
            utils.blink()
            return

        self.view.run_command('reindent', {'force_indent': False})

        regions_transformer(self.view, f)
        self.enter_normal_mode(mode)


class _vi_big_o(ViTextCommandBase):
    def run(self, edit, count=1, mode=None):
        if mode == modes.INTERNAL_NORMAL:
            self.view.run_command('run_macro_file', {'file': 'res://Packages/Default/Add Line Before.sublime-macro'})

        self.enter_insert_mode(mode)


class _vi_o(ViTextCommandBase):
    def run(self, edit, count=1, mode=None):
        if mode == modes.INTERNAL_NORMAL:
            self.view.run_command('run_macro_file', {'file': 'res://Packages/Default/Add Line.sublime-macro'})

        self.enter_insert_mode(mode)


class _vi_big_x(ViTextCommandBase):

    _can_yank = True
    _populates_small_delete_register = True

    def line_start(self, pt):
        return self.view.line(pt).begin()

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):
            if mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.b, max(s.b - count,
                                               self.line_start(s.b)))
            elif mode == modes.VISUAL:
                if s.a < s.b:
                    return sublime.Region(view.full_line(s.b - 1).b,
                                          view.line(s.a).a)
                return sublime.Region(view.line(s.b).a,
                                      view.full_line(s.a - 1).b)
            return sublime.Region(s.begin(), s.end())

        regions_transformer(self.view, select)

        state = self.state
        state.registers.yank(self, register)

        self.view.run_command('left_delete')

        self.enter_normal_mode(mode)

class _vi_big_p(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True

    def run(self, edit, register=None, count=1, mode=None):
        state = self.state

        if state.mode == modes.VISUAL:
            prev_text = state.registers.get_selected_text(self)

        if register:
            fragments = state.registers[register]
        else:
            # TODO: There should be a simpler way of getting the unnamed register's content.
            fragments = state.registers['"']

        if state.mode == modes.VISUAL:
            # Populate registers with the text we're about to paste.
            state.registers['"'] = prev_text

        # TODO: Enable pasting to multiple selections.
        sel = list(self.view.sel())[0]
        merged_fragments, linewise = self.merge_fragments(fragments)

        if mode == modes.INTERNAL_NORMAL:
            if not linewise:
                self.view.insert(edit, sel.a, merged_fragments)
                self.view.sel().clear()
                pt = sel.a + len(merged_fragments) - 1
                self.view.sel().add(sublime.Region(pt))
            else:
                pt = self.view.line(sel.a).a
                self.view.insert(edit, pt, merged_fragments)
                self.view.sel().clear()
                pt = pt + len(merged_fragments)
                row = utils.row_at(self.view, pt)
                pt = self.view.text_point(row - 1, 0)
                self.view.sel().add(sublime.Region(pt))

        elif mode == modes.VISUAL:
            if not linewise:
                self.view.replace(edit, sel, merged_fragments)
            else:
                pt = sel.a
                if merged_fragments[0] != '\n':
                    merged_fragments = '\n' + merged_fragments
                self.view.replace(edit, sel, merged_fragments)
                self.view.sel().clear()
                row = utils.row_at(self.view, pt + len(merged_fragments))
                pt = self.view.text_point(row - 1, 0)
                self.view.sel().add(sublime.Region(pt))
        else:
            return

        self.enter_normal_mode(mode=mode)

    def merge_fragments(self, fragments):
        joined = ''.join(fragments)
        if '\n' in fragments[0]:
            if joined[-1] != '\n':
                return (joined + '\n'), True
            return joined, True
        return joined, False


class _vi_p(ViTextCommandBase):

    _can_yank = True
    _synthetize_new_line_at_eof = True

    def run(self, edit, register=None, count=1, mode=None):
        state = self.state
        register = register or '"'
        fragments = state.registers[register]
        if not fragments:
            print("Vintageous: Nothing in register \".")
            return

        if state.mode == modes.VISUAL:
            prev_text = state.registers.get_selected_text(self)
            state.registers['"'] = prev_text

        sels = list(self.view.sel())
        # If we have the same number of pastes and selections, map 1:1. Otherwise paste paste[0]
        # to all target selections.
        if len(sels) == len(fragments):
            sel_to_frag_mapped = zip(sels, fragments)
        else:
            sel_to_frag_mapped = zip(sels, [fragments[0],] * len(sels))

        # FIXME: Fix this mess. Separate linewise from charwise pasting.
        pasting_linewise = True
        offset = 0
        paste_locations = []
        for selection, fragment in reversed(list(sel_to_frag_mapped)):
            fragment = self.prepare_fragment(fragment)
            if fragment.startswith('\n'):
                # Pasting linewise...
                # If pasting at EOL or BOL, make sure we paste before the newline character.
                if (utils.is_at_eol(self.view, selection) or
                    utils.is_at_bol(self.view, selection)):
                    l = self.paste_all(edit, selection,
                                       self.view.line(selection.b).b,
                                       fragment,
                                       count)
                    paste_locations.append(l)
                else:
                    l = self.paste_all(edit, selection,
                                   self.view.line(selection.b - 1).b,
                                   fragment,
                                   count)
                    paste_locations.append(l)
            else:
                pasting_linewise = False
                # Pasting charwise...
                # If pasting at EOL, make sure we don't paste after the newline character.
                if self.view.substr(selection.b) == '\n':
                    l = self.paste_all(edit, selection, selection.b + offset,
                                   fragment, count)
                    paste_locations.append(l)
                else:
                    l = self.paste_all(edit, selection, selection.b + offset + 1,
                                   fragment, count)
                    paste_locations.append(l)
                offset += len(fragment) * count

        if pasting_linewise:
            self.reset_carets_linewise(paste_locations)
        else:
            self.reset_carets_charwise(paste_locations, len(fragment))

        self.enter_normal_mode(mode)

    def reset_carets_charwise(self, pts, paste_len):
        # FIXME: Won't work for multiple jagged pastes...
        b_pts = [s.b for s in list(self.view.sel())]
        if len(b_pts) > 1:
            self.view.sel().clear()
            self.view.sel().add_all([sublime.Region(ploc + paste_len - 1,
                                                    ploc + paste_len - 1)
                                    for ploc in pts])
        else:
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(pts[0] + paste_len - 1,
                                               pts[0] + paste_len - 1))

    def reset_carets_linewise(self, pts):
        self.view.sel().clear()

        if self.state.mode == modes.VISUAL_LINE:
            self.view.sel().add_all([sublime.Region(loc) for loc in pts])
            return

        self.view.sel().add_all([sublime.Region(loc + 1) for loc in pts])

    def prepare_fragment(self, text):
        if text.endswith('\n') and text != '\n':
            text = '\n' + text[0:-1]
        return text

    # TODO: Improve this signature.
    def paste_all(self, edit, sel, at, text, count):
        state = self.state
        if state.mode not in (modes.VISUAL, modes.VISUAL_LINE):
            # TODO: generate string first, then insert?
            # Make sure we can paste at EOF.
            at = at if at <= self.view.size() else self.view.size()
            for x in range(count):
                self.view.insert(edit, at, text)

            if '\n' in text:
                with restoring_sel(self.view):
                    delta = len(text) * count
                    r = sublime.Region(at + 1, at + delta)
                    self.view.sel().add(r)
                    self.view.run_command('reindent', {'force_indent': False})

            return at
        else:
            if text.startswith('\n'):
                text = text * count
                if not text.endswith('\n'):
                    text = text + '\n'
            else:
                text = text * count

            if state.mode == modes.VISUAL_LINE:
                if text.startswith('\n'):
                    text = text[1:]

            self.view.replace(edit, sel, text)

            if '\n' in text:
                with restoring_sel(self.view):
                    delta = sel.begin() + len(text)
                    r = sublime.Region(sel.begin() + 1, delta - 1)
                    self.view.sel().add(r)
                    self.view.run_command('reindent', {'force_indent': False})

            return sel.begin()


class _vi_gt(ViWindowCommandBase):
    def run(self, count=1, mode=None):
        self.window.run_command('tab_control', {'command': 'next'})
        self.window.run_command('_enter_normal_mode', {'mode': mode})


class _vi_g_big_t(ViWindowCommandBase):
    def run(self, count=1, mode=None):
        self.window.run_command('tab_control', {'command': 'prev'})
        self.window.run_command('_enter_normal_mode', {'mode': mode})


class _vi_ctrl_w_q(IrreversibleTextCommand):
    def run(self, count=1, mode=None):
        if self.view.is_dirty():
            sublime.status_message('Unsaved changes.')
            return

        self.view.close()


class _vi_ctrl_w_v(IrreversibleTextCommand):
    def run(self, count=1, mode=None):
        self.view.window().run_command('ex_vsplit')


class _vi_ctrl_w_l(IrreversibleTextCommand):
    # TODO: Should be a window command instead.
    # TODO: Should focus the group to the right only, not the 'next' group.
    def run(self, mode=None, count=None):
        w = self.view.window()
        current_group = w.active_group()
        if w.num_groups() > 1:
            w.focus_group(current_group + 1)


class _vi_ctrl_w_big_l(IrreversibleTextCommand):
    def run(self, mode=None, count=1):
        w = self.view.window()
        current_group = w.active_group()
        if w.num_groups() > 1:
            w.set_view_index(self.view, current_group + 1, 0)
            w.focus_group(current_group + 1)


class _vi_ctrl_w_h(IrreversibleTextCommand):
    # TODO: Should be a window command instead.
    # TODO: Should focus the group to the left only, not the 'previous' group.
    def run(self, mode=None, count=1):
        w = self.view.window()
        current_group = w.active_group()
        if current_group > 0:
            w.focus_group(current_group - 1)


class _vi_ctrl_w_big_h(IrreversibleTextCommand):
    def run(self, mode=None, count=1):
        w = self.view.window()
        current_group = w.active_group()
        if current_group > 0:
            w.set_view_index(self.view, current_group - 1, 0)
            w.focus_group(current_group - 1)


class _vi_z_enter(IrreversibleTextCommand):
    def __init__(self, view):
        IrreversibleTextCommand.__init__(self, view)

    def run(self, count=1, mode=None):
        first_sel = self.view.sel()[0]
        current_row = self.view.rowcol(first_sel.b)[0] - 1

        topmost_visible_row, _ = self.view.rowcol(self.view.visible_region().a)

        self.view.run_command('scroll_lines', {'amount': (topmost_visible_row - current_row)})


class _vi_z_minus(IrreversibleTextCommand):
    def __init__(self, view):
        IrreversibleTextCommand.__init__(self, view)

    def run(self, count=1, mode=None):
        first_sel = self.view.sel()[0]
        current_row = self.view.rowcol(first_sel.b)[0]

        bottommost_visible_row, _ = self.view.rowcol(self.view.visible_region().b)

        number_of_lines = (bottommost_visible_row - current_row) - 1

        if number_of_lines > 1:
            self.view.run_command('scroll_lines', {'amount': number_of_lines})


class _vi_zz(IrreversibleTextCommand):
    def __init__(self, view):
        IrreversibleTextCommand.__init__(self, view)

    def run(self, count=1, mode=None):
        first_sel = self.view.sel()[0]
        current_row = self.view.rowcol(first_sel.b)[0]

        topmost_visible_row, _ = self.view.rowcol(self.view.visible_region().a)
        bottommost_visible_row, _ = self.view.rowcol(self.view.visible_region().b)

        middle_row = (topmost_visible_row + bottommost_visible_row) / 2

        self.view.run_command('scroll_lines', {'amount': (middle_row - current_row)})


class _vi_modify_numbers(sublime_plugin.TextCommand):
    """
    Base class for Ctrl-x and Ctrl-a.
    """
    DIGIT_PAT = re.compile('(\D+?)?(-)?(\d+)(\D+)?')
    NUM_PAT = re.compile('\d')

    def get_editable_data(self, pt):
        sign = -1 if (self.view.substr(pt - 1) == '-') else 1
        end = pt
        while self.view.substr(end).isdigit():
            end += 1
        return (sign, int(self.view.substr(sublime.Region(pt, end))),
                sublime.Region(end, self.view.line(pt).b))


    def find_next_num(self, regions):
        # Modify selections that are inside a number already.
        for i, r in enumerate(regions):
            a = r.b
            if self.view.substr(r.b).isdigit():
                while self.view.substr(a).isdigit():
                    a -=1
                regions[i] = sublime.Region(a)

        lines = [self.view.substr(sublime.Region(r.b, self.view.line(r.b).b)) for r in regions]
        matches = [_vi_modify_numbers.NUM_PAT.search(text) for text in lines]
        if all(matches):
            return [(reg.b + ma.start()) for (reg, ma) in zip(regions, matches)]
        return []

    def run(self, edit, count=1, mode=None, subtract=False):
        if mode != modes.INTERNAL_NORMAL:
            return

        # TODO: Deal with octal, hex notations.
        # TODO: Improve detection of numbers.
        regs = list(self.view.sel())

        pts = self.find_next_num(regs)
        if not pts:
            utils.blink()
            return

        count = count if not subtract else -count
        end_sels = []
        for pt in reversed(pts):
            sign, num, tail = self.get_editable_data(pt)

            num_as_text = str((sign * num) + count)
            new_text = num_as_text + self.view.substr(tail)

            offset = 0
            if sign == -1:
                offset = -1
                self.view.replace(edit, sublime.Region(pt - 1, tail.b), new_text)
            else:
                self.view.replace(edit, sublime.Region(pt, tail.b), new_text)

            rowcol = self.view.rowcol(pt + len(num_as_text) - 1 + offset)
            end_sels.append(rowcol)

        self.view.sel().clear()
        for (row, col) in end_sels:
            self.view.sel().add(sublime.Region(self.view.text_point(row, col)))


class _vi_select_big_j(IrreversibleTextCommand):
    """
    Active in select mode. Clears multiple selections and returns to normal
    mode. Should be more convenient than having to reach for Esc.
    """
    def run(self, mode=None, count=1):
        s = self.view.sel()[0]
        self.view.sel().clear()
        self.view.sel().add(s)
        self.view.run_command('_enter_normal_mode', {'mode': mode})


class _vi_big_j(sublime_plugin.TextCommand):
    WHITE_SPACE = ' \t'

    def run(self, edit, mode=None, separator=' ', count=1):
        sels = self.view.sel()
        s = sublime.Region(sels[0].a, sels[-1].b)
        if mode == modes.INTERNAL_NORMAL:
            end_pos = self.view.line(s.b).b
            start = end = s.b
            if count > 2:
                end = self.view.text_point(utils.row_at(self.view, s.b) + (count - 1), 0)
                end = self.view.line(end).b
            else:
                # Join current line and the next.
                end = self.view.text_point(utils.row_at(self.view, s.b) + 1, 0)
                end = self.view.line(end).b
        elif mode in [modes.VISUAL, modes.VISUAL_LINE, modes.VISUAL_BLOCK]:
            if s.a < s.b:
                end_pos = self.view.line(s.a).b
                start = s.a
                if utils.row_at(self.view, s.b - 1) == utils.row_at(self.view, s.a):
                    end = self.view.text_point(utils.row_at(self.view, s.a) + 1, 0)
                else:
                    end = self.view.text_point(utils.row_at(self.view, s.b - 1), 0)
                end = self.view.line(end).b
            else:
                end_pos = self.view.line(s.b).b
                start = s.b
                if utils.row_at(self.view, s.b) == utils.row_at(self.view, s.a - 1):
                    end = self.view.text_point(utils.row_at(self.view, s.a - 1) + 1, 0)
                else:
                    end = self.view.text_point(utils.row_at(self.view, s.a - 1), 0)
                end = self.view.line(end).b
        else:
            return s

        text_to_join = self.view.substr(sublime.Region(start, end))
        lines = text_to_join.split('\n')

        if separator:
            # J
            joined_text = lines[0]
            for line in lines[1:]:
                line = line.lstrip()
                if joined_text and joined_text[-1] not in self.WHITE_SPACE:
                    line = ' ' + line
                joined_text += line
        else:
            # gJ
            joined_text = ''.join(lines)

        self.view.replace(edit, sublime.Region(start, end), joined_text)
        sels.clear()
        sels.add(sublime.Region(end_pos))


class _vi_gv(IrreversibleTextCommand):
    def run(self, mode=None, count=None):
        sels = self.view.get_regions('visual_sel')
        if not sels:
            return

        self.view.window().run_command('_enter_visual_mode', {'mode': mode})
        self.view.sel().clear()
        self.view.sel().add_all(sels)


class _vi_ctrl_e(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=1):
        # TODO: Implement this motion properly; don't use built-in commands.
        # We're using an action because we don't care too much right now and we don't want the
        # motion to utils.blink every time we issue it (it does because the selections don't change and
        # Vintageous rightfully thinks it has failed.)
        if mode == modes.VISUAL_LINE:
            return
        extend = True if mode == modes.VISUAL else False
        self.view.run_command('scroll_lines', {'amount': -1, 'extend': extend})


class _vi_ctrl_y(sublime_plugin.TextCommand):
    def run(self, edit, mode=None, count=1):
        # TODO: Implement this motion properly; don't use built-in commands.
        # We're using an action because we don't care too much right now and we don't want the
        # motion to utils.blink every time we issue it (it does because the selections don't change and
        # Vintageous rightfully thinks it has failed.)
        if mode == modes.VISUAL_LINE:
            return
        extend = True if mode == modes.VISUAL else False
        self.view.run_command('scroll_lines', {'amount': 1, 'extend': extend})


class _vi_ctrl_r_equal(sublime_plugin.TextCommand):
    def run(self, edit, insert=False, next_mode=None):
        def on_done(s):
            state = State(self.view)
            try:
                rv = [str(eval(s, None, None)),]
                if not insert:
                    state.registers[REG_EXPRESSION] = rv
                else:
                    self.view.run_command('insert_snippet', {'contents': str(rv[0])})
                    state.reset()
            except:
                sublime.status_message("Vintageous: Invalid expression.")
                on_cancel()

        def on_cancel():
            state = State(self.view)
            state.reset()

        self.view.window().show_input_panel('', '', on_done, None, on_cancel)


class _vi_q(IrreversibleTextCommand):
    def run(self, name=None, mode=None, count=1):
        # TODO: We ignore the name.
        state = State(self.view)

        if state.recording_macro:
            self.view.run_command('toggle_record_macro')
            cmds = []
            for c in sublime.get_macro():
                cmds.append([c['command'], c['args']])
            state.last_macro = cmds
            state.recording_macro = False
            sublime.status_message('')
            return
        self.view.run_command('toggle_record_macro')
        state.recording_macro = True
        sublime.status_message('[Vintageous] Recording macro...')


class _vi_at(IrreversibleTextCommand):
    def run(self, name=None, mode=None, count=1):
        # TODO: We ignore the name.
        state = State(self.view)

        if not (state.gluing_sequence or state.recording_macro):
            self.view.run_command('mark_undo_groups_for_gluing')

        cmds = state.last_macro
        for i in range(count):

            self.view.run_command('sequence', {'commands': cmds})

        if not (state.gluing_sequence or state.recording_macro):
            self.view.run_command('glue_marked_undo_groups')


class _enter_visual_block_mode(ViTextCommandBase):
    def run(self, edit, mode=None):
        def f(view, s):
            return sublime.Region(s.b, s.b + 1)
        # Handling multiple visual blocks seems quite hard, so ensure we only
        # have one.
        first = list(self.view.sel())[0]
        self.view.sel().clear()
        self.view.sel().add(first)

        state = State(self.view)
        state.enter_visual_block_mode()

        if not self.view.has_non_empty_selection_region():
            regions_transformer(self.view, f)


class _vi_select_j(ViWindowCommandBase):
    def run(self, count=1, mode=None):
        if mode != modes.SELECT:
            raise ValueError('wrong mode')

        for i in range(count):
            self.window.run_command('find_under_expand')


class _vi_tilde(ViTextCommandBase):
    """
    Implemented as if 'notildeopt' was `True`.
    """
    def run(self, edit, count=1, mode=None, motion=None):
        def select(view, s):
            if mode == modes.VISUAL:
                return sublime.Region(s.end(), s.begin())
            return sublime.Region(s.begin(), s.end() + count)

        def after(view, s):
            return sublime.Region(s.begin())

        regions_transformer(self.view, select)
        self.view.run_command('swap_case')

        if mode in (modes.VISUAL, modes.VISUAL_LINE, modes.VISUAL_BLOCK):
            regions_transformer(self.view, after)

        self.enter_normal_mode(mode)


class _vi_g_tilde(ViTextCommandBase):
    def run(self, edit, count=1, mode=None, motion=None):
        def f(view, s):
            return sublime.Region(s.end(), s.begin())

        if motion:
            self.save_sel()

            self.view.run_command(motion['motion'], motion['motion_args'])

            if not self.has_sel_changed():
                utils.blink()
                self.enter_normal_mode(mode)
                return

        self.view.run_command('swap_case')

        if motion:
            regions_transformer(self.view, f)

        self.enter_normal_mode(mode)


class _vi_visual_u(ViTextCommandBase):
    """
    'u' action in visual modes.
    """
    def run(self, edit, mode=None, count=1):
        for s in self.view.sel():
            self.view.replace(edit, s, self.view.substr(s).lower())

        def after(view, s):
            return sublime.Region(s.begin())

        regions_transformer(self.view, after)

        self.enter_normal_mode(mode)


class _vi_visual_big_u(ViTextCommandBase):
    """
    'U' action in visual modes.
    """
    def run(self, edit, mode=None, count=1):
        for s in self.view.sel():
            self.view.replace(edit, s, self.view.substr(s).upper())

        def after(view, s):
            return sublime.Region(s.begin())

        regions_transformer(self.view, after)

        self.enter_normal_mode(mode)


class _vi_g_tilde_g_tilde(ViTextCommandBase):
    def run(self, edit, count=1, mode=None):
        def select(view, s):
            l =  view.line(s.b)
            return sublime.Region(l.end(), l.begin())

        if mode != modes.INTERNAL_NORMAL:
            raise ValueError('wrong mode')

        regions_transformer(self.view, select)
        self.view.run_command('swap_case')
        # Ensure we leave the sel .b end where we want it.
        regions_transformer(self.view, select)

        self.enter_normal_mode(mode)


class _vi_g_big_u_big_u(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        def select(view, s):
            l = view.line(s.b)
            return sublime.Region(l.end(), l.begin())

        def to_upper(view, s):
            view.replace(edit, s, view.substr(s).upper())
            return s

        regions_transformer(self.view, select)
        regions_transformer(self.view, to_upper)
        self.enter_normal_mode(mode)


class _vi_guu(ViTextCommandBase):
    def run(self, edit, mode=None, count=1):
        def select(view, s):
            l = view.line(s.b)
            return sublime.Region(l.end(), l.begin())

        def to_lower(view, s):
            view.replace(edit, s, view.substr(s).lower())
            return s

        regions_transformer(self.view, select)
        regions_transformer(self.view, to_lower)
        self.enter_normal_mode(mode)


class _vi_g_big_h(ViWindowCommandBase):
    """
    Non-standard command.

    After a search has been performed via '/' or '?', selects all matches and
    enters select mode.
    """
    def run(self, mode=None, count=1):
        view = self.window.active_view()

        regs = view.get_regions('vi_search')
        if regs:
            view.sel().add_all(view.get_regions('vi_search'))

            self.state.enter_select_mode()
            self.state.display_status()
            return

        utils.blink()
        sublime.status_message('Vintageous: No available search matches')
        self.state.reset_command_data()


class _vi_ctrl_x_ctrl_l(ViTextCommandBase):
    """
    http://vimdoc.sourceforge.net/htmldoc/insert.html#i_CTRL-X_CTRL-L
    """
    MAX_MATCHES = 20
    def find_matches(self, prefix, end):
        escaped = re.escape(prefix)
        matches = []
        while end > 0:
            match = search.reverse_search(self.view,
                                          r'^\s*{0}'.format(escaped),
                                          0, end, flags=0)
            if (match is None) or (len(matches) == self.MAX_MATCHES):
                break
            line = self.view.line(match.begin())
            end = line.begin()
            text = self.view.substr(line).lstrip()
            if text not in matches:
                matches.append(text)
        return matches

    def run(self, edit, mode=None, register='"'):
        # TODO: Must exit to insert mode. As we're using a quick panel, the
        #       mode is being reset in _init_vintageous.
        assert mode == modes.INSERT, 'bad mode'

        if (len(self.view.sel()) > 1 or
            not self.view.sel()[0].empty()):
                utils.blink()
                return

        s = self.view.sel()[0]
        line_begin = self.view.text_point(utils.row_at(self.view, s.b), 0)
        prefix = self.view.substr(sublime.Region(line_begin, s.b)).lstrip()
        self._matches = self.find_matches(prefix, end=self.view.line(s.b).a)
        if self._matches:
            self.show_matches(self._matches)
            state = State(self.view)
            state.reset_during_init = False
            state.reset_command_data()
            return
        utils.blink()

    def show_matches(self, items):
        self.view.window().show_quick_panel(items, self.replace,
                                            sublime.MONOSPACE_FONT)

    def replace(self, s):
        self.view.run_command('__replace_line',
                              {'with_what': self._matches[s]})
        del self.__dict__['_matches']
        pt = self.view.sel()[0].b
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pt))


class __replace_line(sublime_plugin.TextCommand):
    def run(self, edit, with_what):
        b = self.view.line(self.view.sel()[0].b).a
        pt = utils.next_non_white_space_char(self.view, b, white_space=' \t')
        self.view.replace(edit, sublime.Region(pt, self.view.line(pt).b),
                          with_what)

########NEW FILE########
__FILENAME__ = xmotions
# TODO: weird name to avoid init issues with state.py::State.

import sublime
import sublime_plugin

from itertools import chain
from collections import Counter


from Vintageous import state as state_module
from Vintageous.vi import units
from Vintageous.vi import utils
from Vintageous.vi.core import ViMotionCommand
from Vintageous.vi.keys import mappings
from Vintageous.vi.keys import seqs
from Vintageous.vi.search import BufferSearchBase
from Vintageous.vi.search import ExactWordBufferSearchBase
from Vintageous.vi.search import find_in_range
from Vintageous.vi.search import find_wrapping
from Vintageous.vi.search import reverse_find_wrapping
from Vintageous.vi.search import reverse_search
from Vintageous.vi.search import reverse_search_by_pt
from Vintageous.state import State
from Vintageous.vi.text_objects import get_text_object_region
from Vintageous.vi.utils import col_at
from Vintageous.vi.utils import directions
from Vintageous.vi.utils import IrreversibleTextCommand
from Vintageous.vi.utils import modes
from Vintageous.vi.utils import regions_transformer
from Vintageous.vi.utils import mark_as_widget
from Vintageous.vi import cmd_defs
from Vintageous.vi.text_objects import word_reverse
from Vintageous.vi.text_objects import word_end_reverse
from Vintageous.vi.text_objects import get_closest_tag
from Vintageous.vi.text_objects import find_containing_tag


class _vi_find_in_line(ViMotionCommand):
    """
    Contrary to *f*, *t* does not look past the caret's position, so if
    @character is under the caret, nothing happens.
    """
    def run(self, char=None, mode=None, count=1, change_direction=False,
            inclusive=True, skipping=False):
        def f(view, s):
            eol = view.line(s.b).end()
            if not s.empty():
                eol = view.line(s.b - 1).end()

            match = s

            if (mode in (modes.NORMAL, modes.INTERNAL_NORMAL) and
                not inclusive
               and skipping):
                    # When repeating through ';', we must make sure we skip one
                    # if we are at a match position.
                    if view.substr(match.b + 1) == char:
                        match = sublime.Region(match.b + 1)

            for i in range(count):
                # Define search range as 'rest of the line to the right'.
                if state.mode != modes.VISUAL:
                    search_range = sublime.Region(min(match.b + 1, eol), eol)

                else:
                    search_range = sublime.Region(min(match.b, eol), eol)

                match = find_in_range(view, char,
                                            search_range.a,
                                            search_range.b,
                                            sublime.LITERAL)

                # Count too high or simply no match; break.
                if match is None:
                    return s
                    break

            if (mode == modes.VISUAL) or (mode == modes.INTERNAL_NORMAL):
                if match.a == s.b:
                    return s
                if not inclusive:
                    return sublime.Region(s.a, match.b - 1)
                else:
                    return sublime.Region(s.a, match.b)

            if not inclusive:
                return sublime.Region(match.a - 1)
            else:
                return sublime.Region(match.a)

        if not all([char, mode]):
            print('char', char, 'mode', mode)
            raise ValueError('bad parameters')

        char = utils.translate_char(char)

        state = self.state

        regions_transformer(self.view, f)


class _vi_reverse_find_in_line(ViMotionCommand):
    """Contrary to *F*, *T* does not look past the caret's position, so if ``character`` is right
       before the caret, nothing happens.
    """
    def run(self, char=None, mode=None, count=1, change_direction=False,
            inclusive=True, skipping=False):
        def f(view, s):
            if mode not in (modes.VISUAL, modes.VISUAL_LINE, modes.VISUAL_BLOCK):
                a, b = view.line(s.b).a, s.b

            else:
                a, b = view.line(s.b - 1).a, s.b

            final_offset = -1

            try:
                # search backwards
                for i in range(count):
                    line_text = view.substr(sublime.Region(a, b))
                    found_at = line_text.rindex(char)

                    final_offset = found_at

                    b = view.line(s.a).a + final_offset
            except ValueError:
                pass

            if final_offset > -1:
                pt = view.line(s.b).a + final_offset

                if mode == modes.VISUAL or mode == modes.INTERNAL_NORMAL:
                    if not inclusive:
                        return sublime.Region(s.a, pt + 1)
                    else:
                        return sublime.Region(s.a, pt)

                if not inclusive:
                    return sublime.Region(pt + 1)
                else:
                    return sublime.Region(pt)

            return s

        if not all([char, mode]):
            raise ValueError('bad parameters')

        char = utils.translate_char(char)

        state = self.state
        regions_transformer(self.view, f)


class _vi_slash(ViMotionCommand, BufferSearchBase):
    """
    Collects input for the / motion.
    """
    def run(self, default=''):
        self.state.reset_during_init = False

        # TODO: re-enable this.
        # on_change = self.on_change if state.settings.vi['incsearch'] else None
        on_change = self.on_change

        mark_as_widget(self.view.window().show_input_panel(
                                                            '',
                                                            default,
                                                            self.on_done,
                                                            on_change,
                                                            self.on_cancel))

    def on_done(self, s):
        state = self.state
        state.sequence += s + '<CR>'
        self.view.erase_regions('vi_inc_search')
        state.motion = cmd_defs.ViSearchForwardImpl(term=s)

        # If s is empty, we must repeat the last search.
        state.last_buffer_search = s or state.last_buffer_search
        state.eval()

    def on_change(self, s):
        state = self.state
        flags = self.calculate_flags()
        self.view.erase_regions('vi_inc_search')
        next_hit = find_wrapping(self.view,
                                 term=s,
                                 start=self.view.sel()[0].b + 1,
                                 end=self.view.size(),
                                 flags=flags,
                                 times=state.count)
        if next_hit:
            if state.mode == modes.VISUAL:
                next_hit = sublime.Region(self.view.sel()[0].a, next_hit.a + 1)

            self.view.add_regions('vi_inc_search', [next_hit], 'comment', '')
            if not self.view.visible_region().contains(next_hit.b):
                self.view.show(next_hit.b)

    def on_cancel(self):
        state = self.state
        self.view.erase_regions('vi_inc_search')
        state.reset_command_data()

        if not self.view.visible_region().contains(self.view.sel()[0]):
            self.view.show(self.view.sel()[0])


class _vi_slash_impl(ViMotionCommand, BufferSearchBase):
    def run(self, search_string='', mode=None, count=1):
        def f(view, s):
            if mode == modes.VISUAL:
                return sublime.Region(s.a, match.a + 1)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, match.a)

            elif mode == modes.NORMAL:
                return sublime.Region(match.a, match.a)

            elif mode == modes.VISUAL_LINE:
                return sublime.Region(s.a, view.full_line(match.b - 1).b)

            return s

        # This happens when we attempt to repeat the search and there's no search term stored yet.
        if not search_string:
            return

        # We want to start searching right after the current selection.
        current_sel = self.view.sel()[0]
        start = current_sel.b if not current_sel.empty() else current_sel.b + 1
        wrapped_end = self.view.size()

        # TODO: What should we do here? Case-sensitive or case-insensitive search? Configurable?
        # Search wrapping around the end of the buffer.
        # flags = sublime.IGNORECASE | sublime.LITERAL
        flags = self.calculate_flags()
        match = find_wrapping(self.view, search_string, start, wrapped_end, flags=flags, times=count)
        if not match:
            return

        regions_transformer(self.view, f)
        self.hilite(search_string)



class _vi_l(ViMotionCommand):
    def run(self, mode=None, count=None):
        def f(view, s):
            if mode == modes.NORMAL:
                if view.line(s.b).empty():
                    return s

                x_limit = min(view.line(s.b).b - 1, s.b + count, view.size())
                return sublime.Region(x_limit, x_limit)

            if mode == modes.INTERNAL_NORMAL:
                x_limit = min(view.line(s.b).b, s.b + count)
                x_limit = max(0, x_limit)
                return sublime.Region(s.a, x_limit)

            if mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                if s.a < s.b:
                    x_limit = min(view.full_line(s.b - 1).b, s.b + count)
                    return sublime.Region(s.a, x_limit)

                if s.a > s.b:
                    x_limit = min(view.full_line(s.b).b - 1, s.b + count)
                    if view.substr(s.b) == '\n':
                        return s

                    if view.line(s.a) == view.line(s.b) and count >= s.size():
                        x_limit = min(view.full_line(s.b).b, s.b + count + 1)
                        return sublime.Region(s.a - 1, x_limit)

                    return sublime.Region(s.a, x_limit)

            return s

        regions_transformer(self.view, f)
        state = self.state
        # state.xpos = self.view.rowcol(self.view.sel()[0].b)[1]


class _vi_h(ViMotionCommand):
    def run(self, count=1, mode=None):
        def f(view, s):
            if mode == modes.INTERNAL_NORMAL:
                x_limit = max(view.line(s.b).a, s.b - count)
                return sublime.Region(s.a, x_limit)

            # TODO: Split handling of the two modes for clarity.
            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):

                if s.a < s.b:
                    if mode == modes.VISUAL_BLOCK and self.view.rowcol(s.b - 1)[1] == baseline:
                        return s

                    x_limit = max(view.line(s.b - 1).a + 1, s.b - count)
                    if view.line(s.a) == view.line(s.b - 1) and count >= s.size():
                        x_limit = max(view.line(s.b - 1).a, s.b - count - 1)
                        return sublime.Region(s.a + 1, x_limit)
                    return sublime.Region(s.a, x_limit)

                if s.a > s.b:
                    x_limit = max(view.line(s.b).a, s.b - count)
                    return sublime.Region(s.a, x_limit)

            elif mode == modes.NORMAL:
                x_limit = max(view.line(s.b).a, s.b - count)
                return sublime.Region(x_limit, x_limit)

            # XXX: We should never reach this.
            return s

        # For jagged selections (on the rhs), only those sticking out need to move leftwards.
        # Example ([] denotes the selection):
        #
        #   10 foo bar foo [bar]
        #   11 foo bar foo [bar foo bar]
        #   12 foo bar foo [bar foo]
        #
        #  Only lines 11 and 12 should move when we press h.
        baseline = 0
        if mode == modes.VISUAL_BLOCK:
            sel = self.view.sel()[0]
            if sel.a < sel.b:
                min_ = min(self.view.rowcol(r.b - 1)[1] for r in self.view.sel())
                if any(self.view.rowcol(r.b - 1)[1] != min_ for r in self.view.sel()):
                    baseline = min_

        regions_transformer(self.view, f)
        state = self.state
        # state.xpos = self.view.rowcol(self.view.sel()[0].b)[1]


class _vi_j(ViMotionCommand):
    def folded_rows(self, pt):
        folds = self.view.folded_regions()
        try:
            fold = [f for f in folds if f.contains(pt)][0]
            fold_row_a = self.view.rowcol(fold.a)[0]
            fold_row_b = self.view.rowcol(fold.b - 1)[0]
            # Return no. of hidden lines.
            return (fold_row_b - fold_row_a)
        except IndexError:
            return 0

    def next_non_folded_pt(self, pt):
        # FIXME: If we have two contiguous folds, this method will fail.
        # Handle folded regions.
        folds = self.view.folded_regions()
        try:
            fold = [f for f in folds if f.contains(pt)][0]
            non_folded_row = self.view.rowcol(self.view.full_line(fold.b).b)[0]
            pt = self.view.text_point(non_folded_row, 0)
        except IndexError:
            pass
        return pt

    def calculate_xpos(self, start, xpos):
        size = self.view.settings().get('tab_size')
        if self.view.line(start).empty():
            return start, 0
        else:
            eol = self.view.line(start).b - 1
        pt = 0
        chars = 0
        while (pt < xpos):
            if self.view.substr(start + chars) == '\t':
                pt += size
            else:
                pt += 1
            chars += 1
        pt = min(eol, start + chars)
        return pt, chars

    def run(self, count=1, mode=None, xpos=0, no_translation=False):
        def f(view, s):
            nonlocal xpos
            if mode == modes.NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row + count, view.rowcol(view.size())[0])
                invisible_rows = self.folded_rows(view.line(s.b).b + 1)
                target_pt = view.text_point(target_row + invisible_rows, 0)
                target_pt = self.next_non_folded_pt(target_pt)

                if view.line(target_pt).empty():
                    return sublime.Region(target_pt, target_pt)

                pt = self.calculate_xpos(target_pt, xpos)[0]
                return sublime.Region(pt)

            if mode == modes.INTERNAL_NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row + count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                return sublime.Region(view.line(s.a).a, view.full_line(target_pt).b)

            if mode == modes.VISUAL:
                exact_position = s.b - 1 if (s.a < s.b) else s.b
                current_row = view.rowcol(exact_position)[0]
                target_row = min(current_row + count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                _, xpos = self.calculate_xpos(target_pt, xpos)

                end = min(self.view.line(target_pt).b, target_pt + xpos)
                if s.a < s.b:
                    return sublime.Region(s.a, end + 1)

                if (target_pt + xpos) >= s.a:
                    return sublime.Region(s.a - 1, end + 1)
                return sublime.Region(s.a, target_pt + xpos)


            if mode == modes.VISUAL_LINE:
                if s.a < s.b:
                    current_row = view.rowcol(s.b - 1)[0]
                    target_row = min(current_row + count, view.rowcol(view.size())[0])

                    target_pt = view.text_point(target_row, 0)
                    return sublime.Region(s.a, view.full_line(target_pt).b)

                elif s.a > s.b:
                    current_row = view.rowcol(s.b)[0]
                    target_row = min(current_row + count, view.rowcol(view.size())[0])
                    target_pt = view.text_point(target_row, 0)

                    if target_row > view.rowcol(s.a - 1)[0]:
                        return sublime.Region(view.line(s.a - 1).a, view.full_line(target_pt).b)

                    return sublime.Region(s.a, view.full_line(target_pt).a)

            return s

        state = State(self.view)

        if mode == modes.VISUAL_BLOCK:
            if len(self.view.sel()) == 1:
                state.visual_block_direction = directions.DOWN

            # Don't do anything if we have reversed selections.
            if any((r.b < r.a) for r in self.view.sel()):
                return

            if state.visual_block_direction == directions.DOWN:
                for i in range(count):
                    # FIXME: When there are multiple rectangular selections, S3 considers sel 0 to be the
                    # active one in all cases, so we can't know the 'direction' of such a selection and,
                    # therefore, we can't shrink it when we press k or j. We can only easily expand it.
                    # We could, however, have some more global state to keep track of the direction of
                    # visual block selections.
                    row, rect_b = self.view.rowcol(self.view.sel()[-1].b - 1)

                    # Don't do anything if the next row is empty or too short. Vim does a crazy thing: it
                    # doesn't select it and it doesn't include it in actions, but you have to still navigate
                    # your way through them.
                    # TODO: Match Vim's behavior.
                    next_line = self.view.line(self.view.text_point(row + 1, 0))
                    if next_line.empty() or self.view.rowcol(next_line.b)[1] < rect_b:
                        return

                    max_size = max(r.size() for r in self.view.sel())
                    row, col = self.view.rowcol(self.view.sel()[-1].a)
                    start = self.view.text_point(row + 1, col)
                    new_region = sublime.Region(start, start + max_size)
                    self.view.sel().add(new_region)
                    # FIXME: Perhaps we should scroll into view in a more general way...

                self.view.show(new_region, False)
                return

            else:
                # Must delete last sel.
                self.view.sel().subtract(self.view.sel()[0])
                return

        regions_transformer(self.view, f)


class _vi_k(ViMotionCommand):
    def previous_non_folded_pt(self, pt):
        # FIXME: If we have two contiguous folds, this method will fail.
        # Handle folded regions.
        folds = self.view.folded_regions()
        try:
            fold = [f for f in folds if f.contains(pt)][0]
            non_folded_row = self.view.rowcol(fold.a - 1)[0]
            pt = self.view.text_point(non_folded_row, 0)
        except IndexError:
            pass
        return pt

    def calculate_xpos(self, start, xpos):
        if self.view.line(start).empty():
            return start, 0
        size = self.view.settings().get('tab_size')
        eol = self.view.line(start).b - 1
        pt = 0
        chars = 0
        while (pt < xpos):
            if self.view.substr(start + chars) == '\t':
                pt += size
            else:
                pt += 1
            chars += 1
        pt = min(eol, start + chars)
        return (pt, chars)

    def run(self, count=1, mode=None, xpos=0, no_translation=False):
        def f(view, s):
            nonlocal xpos
            if mode == modes.NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row - count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                target_pt = self.previous_non_folded_pt(target_pt)

                if view.line(target_pt).empty():
                    return sublime.Region(target_pt, target_pt)

                pt, _ = self.calculate_xpos(target_pt, xpos)
                return sublime.Region(pt)

            if mode == modes.INTERNAL_NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row - count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                return sublime.Region(view.full_line(s.a).b, view.line(target_pt).a)

            if mode == modes.VISUAL:
                exact_position = s.b - 1 if (s.a < s.b) else s.b
                current_row = view.rowcol(exact_position)[0]
                target_row = max(current_row - count, 0)
                target_pt = view.text_point(target_row, 0)
                _, xpos = self.calculate_xpos(target_pt, xpos)

                end = min(self.view.line(target_pt).b, target_pt + xpos)
                if s.b >= s.a:
                    if (self.view.line(s.a).contains(s.b - 1) and
                        not self.view.line(s.a).contains(target_pt)):
                            return sublime.Region(s.a + 1, end)
                    else:
                        if (target_pt + xpos) < s.a:
                            return sublime.Region(s.a + 1, end)
                        else:
                            return sublime.Region(s.a, end + 1)
                return sublime.Region(s.a, end)

            if mode == modes.VISUAL_LINE:
                if s.a < s.b:
                    current_row = view.rowcol(s.b - 1)[0]
                    target_row = min(current_row - count, view.rowcol(view.size())[0])
                    target_pt = view.text_point(target_row, 0)

                    if target_row < view.rowcol(s.begin())[0]:
                        return sublime.Region(view.full_line(s.a).b, view.full_line(target_pt).a)

                    return sublime.Region(s.a, view.full_line(target_pt).b)

                elif s.a > s.b:
                    current_row = view.rowcol(s.b)[0]
                    target_row = max(current_row - count, 0)
                    target_pt = view.text_point(target_row, 0)

                    return sublime.Region(s.a, view.full_line(target_pt).a)

        state = State(self.view)

        if mode == modes.VISUAL_BLOCK:
            if len(self.view.sel()) == 1:
                state.visual_block_direction = directions.UP

            # Don't do anything if we have reversed selections.
            if any((r.b < r.a) for r in self.view.sel()):
                return

            if state.visual_block_direction == directions.UP:

                for i in range(count):
                    rect_b = max(self.view.rowcol(r.b - 1)[1] for r in self.view.sel())
                    row, rect_a = self.view.rowcol(self.view.sel()[0].a)
                    previous_line = self.view.line(self.view.text_point(row - 1, 0))
                    # Don't do anything if previous row is empty. Vim does crazy stuff in that case.
                    # Don't do anything either if the previous line can't accomodate a rectangular selection
                    # of the required size.
                    if (previous_line.empty() or
                        self.view.rowcol(previous_line.b)[1] < rect_b):
                            return
                    rect_size = max(r.size() for r in self.view.sel())
                    rect_a_pt = self.view.text_point(row - 1, rect_a)
                    new_region = sublime.Region(rect_a_pt, rect_a_pt + rect_size)
                    self.view.sel().add(new_region)
                    # FIXME: We should probably scroll into view in a more general way.
                    #        Or maybe every motion should handle this on their own.

                self.view.show(new_region, False)
                return

            elif modes.SELECT:
                # Must remove last selection.
                self.view.sel().subtract(self.view.sel()[-1])
                return
            else:
                return

        regions_transformer(self.view, f)


class _vi_k_select(ViMotionCommand):
    def run(self, count=1, mode=None):
        # FIXME: It isn't working.
        if mode != modes.SELECT:
            utils.blink()
            return

        for i in range(count):
            self.view.window().run_command('soft_undo')
            return


class _vi_gg(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == modes.NORMAL:
                return sublime.Region(0)
            elif mode == modes.VISUAL:
                if s.a < s.b:
                    return sublime.Region(s.a + 1, 0)
                else:
                    return sublime.Region(s.a, 0)
            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(view.full_line(s.b).b, 0)
            elif mode == modes.VISUAL_LINE:
                if s.a < s.b:
                    return sublime.Region(0, s.b)
                else:
                    return sublime.Region(0, s.a)
            return s

        self.view.window().run_command('_vi_add_to_jump_list')
        regions_transformer(self.view, f)
        self.view.window().run_command('_vi_add_to_jump_list')


class _vi_go_to_line(ViMotionCommand):
    def run(self, line=None, mode=None):
        line = line if line > 0 else 1
        dest = self.view.text_point(line - 1, 0)

        def f(view, s):
            if mode == modes.NORMAL:
                non_ws = utils.next_non_white_space_char(view, dest)
                return sublime.Region(non_ws, non_ws)
            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(view.line(s.a).a, view.line(dest).b)
            elif mode == modes.VISUAL:
                if dest < s.a and s.a < s.b:
                    return sublime.Region(s.a + 1, dest)
                elif dest < s.a:
                    return sublime.Region(s.a, dest)
                elif dest > s.b and s.a > s.b:
                    return sublime.Region(s.a - 1, dest + 1)
                return sublime.Region(s.a, dest + 1)
            elif mode == modes.VISUAL_LINE:
                if dest < s.a and s.a < s.b:
                    return sublime.Region(view.full_line(s.a).b, dest)
                elif dest < s.a:
                    return sublime.Region(s.a, dest)
                elif dest > s.a and s.a > s.b:
                    return sublime.Region(view.full_line(s.a - 1).a, view.full_line(dest).b)
                return sublime.Region(s.a, view.full_line(dest).b)
            return s

        regions_transformer(self.view, f)

        # FIXME: Bringing the selections into view will be undesirable in many cases. Maybe we
        # should have an optional .scroll_selections_into_view() step during command execution.
        self.view.show(self.view.sel()[0])


class _vi_big_g(ViMotionCommand):
    def run(self, mode=None, count=None):
        def f(view, s):
            if mode == modes.NORMAL:
                pt = eof
                if not view.line(eof).empty():
                    pt = utils.previous_non_white_space_char(view, eof - 1,
                                                         white_space='\n')
                return sublime.Region(pt, pt)
            elif mode == modes.VISUAL:
                return sublime.Region(s.a, eof)
            elif mode == modes.INTERNAL_NORMAL:
                begin = view.line(s.b).a
                begin = max(0, begin - 1)
                return sublime.Region(begin, eof)
            elif mode == modes.VISUAL_LINE:
                return sublime.Region(s.a, eof)

            return s

        self.view.window().run_command('_vi_add_to_jump_list')
        eof = self.view.size()
        regions_transformer(self.view, f)
        self.view.window().run_command('_vi_add_to_jump_list')


class _vi_dollar(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == modes.NORMAL:
                if count > 1:
                    pt = view.line(target_row_pt).b
                else:
                    pt = view.line(s.b).b
                if not view.line(pt).empty():
                    return sublime.Region(pt - 1, pt - 1)
                return sublime.Region(pt, pt)

            elif mode == modes.VISUAL:
                current_line_pt = (s.b - 1) if (s.a < s.b) else s.b
                if count > 1:
                    end = view.full_line(target_row_pt).b
                else:
                    end = s.end()
                    if not end == view.full_line(s.b - 1).b:
                        end = view.full_line(s.b).b
                end = end if (s.a < end) else (end - 1)
                start = s.a if ((s.a < s.b) or (end < s.a)) else s.a - 1
                return sublime.Region(start, end)

            elif mode == modes.INTERNAL_NORMAL:
                if count > 1:
                    pt = view.line(target_row_pt).b
                else:
                    pt = view.line(s.b).b
                if count == 1:
                    return sublime.Region(s.a, pt)
                return sublime.Region(s.a, pt + 1)

            elif mode == modes.VISUAL_LINE:
                # TODO: Implement this. Not too useful, though.
                return s

            return s

        sel = self.view.sel()[0]
        target_row_pt = (sel.b - 1) if (sel.b > sel.a) else sel.b
        if count > 1:
            current_row = self.view.rowcol(target_row_pt)[0]
            target_row = current_row + count - 1
            target_row_pt = self.view.text_point(target_row, 0)

        regions_transformer(self.view, f)


class _vi_w(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == modes.NORMAL:
                pt = units.word_starts(view, start=s.b, count=count)
                if ((pt == view.size()) and (not view.line(pt).empty())):
                    pt = utils.previous_non_white_space_char(view, pt - 1,
                                                             white_space='\n')
                return sublime.Region(pt, pt)

            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                start = (s.b - 1) if (s.a < s.b) else s.b
                pt = units.word_starts(view, start=start, count=count)

                if (s.a > s.b) and (pt >= s.a):
                    return sublime.Region(s.a - 1, pt + 1)
                elif s.a > s.b:
                    return sublime.Region(s.a, pt)
                elif view.size() == pt:
                    pt -= 1
                return sublime.Region(s.a, pt + 1)

            elif mode == modes.INTERNAL_NORMAL:
                a = s.a
                pt = units.word_starts(view, start=s.b, count=count,
                                       internal=True)
                if (not view.substr(view.line(s.a)).strip() and
                   view.line(s.b) != view.line(pt)):
                        a = view.line(s.a).a
                return sublime.Region(a, pt)

            return s

        regions_transformer(self.view, f)


class _vi_big_w(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == modes.NORMAL:
                pt = units.big_word_starts(view, start=s.b, count=count)
                if ((pt == view.size()) and (not view.line(pt).empty())):
                    pt = utils.previous_non_white_space_char(view, pt - 1,
                                                             white_space='\n')
                return sublime.Region(pt, pt)

            elif mode == modes.VISUAL:
                pt = units.big_word_starts(view, start=s.b - 1, count=count)
                if s.a > s.b and pt >= s.a:
                    return sublime.Region(s.a - 1, pt + 1)
                elif s.a > s.b:
                    return sublime.Region(s.a, pt)
                elif (view.size() == pt):
                    pt -= 1
                return sublime.Region(s.a, pt + 1)

            elif mode == modes.INTERNAL_NORMAL:
                a = s.a
                pt = units.big_word_starts(view,
                                           start=s.b,
                                           count=count,
                                           internal=True)
                if (not view.substr(view.line(s.a)).strip() and
                   view.line(s.b) != view.line(pt)):
                        a = view.line(s.a).a
                return sublime.Region(a, pt)

            return s

        regions_transformer(self.view, f)


class _vi_e(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == modes.NORMAL:
                pt = units.word_ends(view, start=s.b, count=count)
                return sublime.Region(pt - 1)

            elif mode == modes.VISUAL:
                pt = units.word_ends(view, start=s.b - 1, count=count)
                if (s.a > s.b) and (pt >= s.a):
                    return sublime.Region(s.a - 1, pt)
                elif (s.a > s.b):
                    return sublime.Region(s.a, pt)
                elif (view.size() == pt):
                    pt -= 1
                return sublime.Region(s.a, pt)

            elif mode == modes.INTERNAL_NORMAL:
                a = s.a
                pt = units.word_ends(view,
                                     start=s.b,
                                     count=count)
                if (not view.substr(view.line(s.a)).strip() and
                   view.line(s.b) != view.line(pt)):
                        a = view.line(s.a).a
                return sublime.Region(a, pt)
            return s

        regions_transformer(self.view, f)


class _vi_zero(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == modes.NORMAL:
                return sublime.Region(view.line(s.b).a)
            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, view.line(s.b).a)
            elif mode == modes.VISUAL:
                if s.a < s.b:
                    return sublime.Region(s.a, view.line(s.b - 1).a + 1)
                else:
                    return sublime.Region(s.a, view.line(s.b).a)
            return s

        regions_transformer(self.view, f)


class _vi_right_brace(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            # TODO: must skip empty paragraphs.
            start = utils.next_non_white_space_char(view, s.b, white_space='\n \t')
            par_as_region = view.expand_by_class(start, sublime.CLASS_EMPTY_LINE)

            if mode == modes.NORMAL:
                min_pt = max(0, min(par_as_region.b, view.size() - 1))
                return sublime.Region(min_pt, min_pt)

            elif mode == modes.VISUAL:
                return sublime.Region(s.a, par_as_region.b + 1)

            elif mode == modes.INTERNAL_NORMAL:
                if view.substr(s.begin()) == '\n':
                    return sublime.Region(s.a, par_as_region.b)
                else:
                    return sublime.Region(s.a, par_as_region.b - 1)

            elif mode == modes.VISUAL_LINE:
                if s.a <= s.b:
                    return sublime.Region(s.a, par_as_region.b + 1)
                else:
                    if par_as_region.b > s.a:
                        return sublime.Region(view.line(s.a - 1).a, par_as_region.b + 1)
                    return sublime.Region(s.a, par_as_region.b)

            return s

        regions_transformer(self.view, f)


class _vi_left_brace(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            # TODO: must skip empty paragraphs.
            start = utils.previous_non_white_space_char(view, s.b - 1, white_space='\n \t')
            par_as_region = view.expand_by_class(start, sublime.CLASS_EMPTY_LINE)

            if mode == modes.NORMAL:
                return sublime.Region(par_as_region.a, par_as_region.a)

            elif mode == modes.VISUAL:
                # FIXME: Improve motion when .b end crosses over .a end: must extend .a end
                # by one.
                if s.a == par_as_region.a:
                    return sublime.Region(s.a, s.a + 1)
                return sublime.Region(s.a, par_as_region.a)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, par_as_region.a)

            elif mode == modes.VISUAL_LINE:
                if s.a <= s.b:
                    if par_as_region.a < s.a:
                        return sublime.Region(view.full_line(s.a).b, par_as_region.a)
                    return sublime.Region(s.a, par_as_region.a + 1)
                else:
                    return sublime.Region(s.a, par_as_region.a)

            return s

        regions_transformer(self.view, f)


class _vi_percent(ViMotionCommand):
    # TODO: Perhaps truly support multiple regions here?
    pairs = (
            ('(', ')'),
            ('[', ']'),
            ('{', '}'),
            ('<', '>'),
    )

    def find_tag(self, pt):
        if (self.view.score_selector(0, 'text.html') == 0 and
            self.view.score_selector(0, 'text.xml') == 0):
                return None

        if any([self.view.substr(pt) in p for p in self.pairs]):
            return None

        _, tag = get_closest_tag(self.view, pt)
        if tag.contains(pt):
            begin_tag, end_tag, _ = find_containing_tag(self.view, pt)
            if begin_tag:
                return begin_tag if end_tag.contains(pt) else end_tag


    def run(self, percent=None, mode=None):
        if percent == None:
            def move_to_bracket(view, s):
                def find_bracket_location(pt):

                    pt = s.b
                    if s.size() > 0 and s.b > s.a:
                        pt = s.b - 1

                    tag = self.find_tag(pt)
                    if tag:
                        return tag.a

                    bracket, brackets, bracket_pt = self.find_a_bracket(pt)
                    if not bracket:
                        return

                    if bracket == brackets[0]:
                        return self.find_balanced_closing_bracket(bracket_pt + 1, brackets)
                    else:
                        return self.find_balanced_opening_bracket(bracket_pt, brackets)

                if mode == modes.VISUAL:
                    b = (s.b - 1) if (s.a < s.b) else s.b
                    found = find_bracket_location(b)
                    if found:
                        end = (found + 1) if (found > s.b) else found
                        end = (end + 1) if end == s.a else end
                        begin = (s.a + 1) if (s.a < s.b) else s.a
                        return sublime.Region(begin, end)

                if mode == modes.VISUAL_LINE:
                    # TODO: Improve handling of s.a < s.b and s.a > s.b cases.
                    a = find_bracket_location(s.begin())
                    if a is not None:
                        a = self.view.full_line(a).b
                        return sublime.Region(s.begin(), a)

                elif mode == modes.NORMAL:
                    a = find_bracket_location(s.b)
                    if a is not None:
                        return sublime.Region(a, a)

                # TODO: According to Vim we must swallow brackets in this case.
                elif mode == modes.INTERNAL_NORMAL:
                    found = find_bracket_location(s.b)
                    if found:
                        if found < s.a:
                            return sublime.Region(s.a + 1, found)
                        else:
                            return sublime.Region(s.a, found + 1)

                return s

            regions_transformer(self.view, move_to_bracket)

            return

        row = self.view.rowcol(self.view.size())[0] * (percent / 100)

        def f(view, s):
            pt = view.text_point(row, 0)
            return sublime.Region(pt, pt)

        regions_transformer(self.view, f)

        # FIXME: Bringing the selections into view will be undesirable in many cases. Maybe we
        # should have an optional .scroll_selections_into_view() step during command execution.
        self.view.show(self.view.sel()[0])

    def find_a_bracket(self, caret_pt):
        """Locates the next bracket after the caret in the current line.
           If None is found, execution must be aborted.
           Returns: (bracket, brackets, bracket_pt)

           Example: ('(', ('(', ')'), 1337))
        """
        caret_row, caret_col = self.view.rowcol(caret_pt)
        line_text = self.view.substr(sublime.Region(caret_pt,
                                                    self.view.line(caret_pt).b))
        try:
            found_brackets = min([(line_text.index(bracket), bracket)
                                        for bracket in chain(*self.pairs)
                                        if bracket in line_text])
        except ValueError:
            return None, None, None

        bracket_a, bracket_b = [(a, b) for (a, b) in self.pairs
                                       if found_brackets[1] in (a, b)][0]
        return (found_brackets[1], (bracket_a, bracket_b),
                self.view.text_point(caret_row, caret_col + found_brackets[0]))

    def find_balanced_closing_bracket(self, start, brackets, unbalanced=0):
        new_start = start
        for i in range(unbalanced or 1):
            next_closing_bracket = find_in_range(self.view, brackets[1],
                                                 start=new_start,
                                                 end=self.view.size(),
                                                 flags=sublime.LITERAL)
            if next_closing_bracket is None:
                # Unbalanced brackets; nothing we can do.
                return
            new_start = next_closing_bracket.end()

        nested = 0
        while True:
            next_opening_bracket = find_in_range(self.view, brackets[0],
                                                 start=start,
                                                 end=next_closing_bracket.end(),
                                                 flags=sublime.LITERAL)
            if not next_opening_bracket:
                break
            nested += 1
            start = next_opening_bracket.end()

        if nested > 0:
            return self.find_balanced_closing_bracket(next_closing_bracket.end(),
                                                      brackets, nested)
        else:
            return next_closing_bracket.begin()

    def find_balanced_opening_bracket(self, start, brackets, unbalanced=0):
        new_start = start
        for i in range(unbalanced or 1):
            prev_opening_bracket = reverse_search_by_pt(self.view, brackets[0],
                                                      start=0,
                                                      end=new_start,
                                                      flags=sublime.LITERAL)
            if prev_opening_bracket is None:
                # Unbalanced brackets; nothing we can do.
                return
            new_start = prev_opening_bracket.begin()

        nested = 0
        while True:
            next_closing_bracket = reverse_search_by_pt(self.view, brackets[1],
                                                  start=prev_opening_bracket.a,
                                                  end=start,
                                                  flags=sublime.LITERAL)
            if not next_closing_bracket:
                break
            nested += 1
            start = next_closing_bracket.begin()

        if nested > 0:
            return self.find_balanced_opening_bracket(prev_opening_bracket.begin(),
                                                      brackets,
                                                      nested)
        else:
            return prev_opening_bracket.begin()


class _vi_big_h(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            if mode == modes.NORMAL:
                non_ws = utils.next_non_white_space_char(view, target)
                return sublime.Region(non_ws, non_ws)
            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a + 1, target)
            elif mode == modes.VISUAL:
                new_target = utils.next_non_white_space_char(view, target)
                return sublime.Region(s.a + 1, new_target)
            else:
                return s

        r = self.view.visible_region()
        row, _ = self.view.rowcol(r.a)
        row += count + 1

        target = self.view.text_point(row, 0)

        regions_transformer(self.view, f)
        self.view.show(target)


class _vi_big_l(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            if mode == modes.NORMAL:
                non_ws = utils.next_non_white_space_char(view, target)
                return sublime.Region(non_ws, non_ws)
            elif mode == modes.INTERNAL_NORMAL:
                if s.b >= target:
                    return sublime.Region(s.a + 1, target)
                return sublime.Region(s.a, target)
            elif mode == modes.VISUAL:
                if s.b >= target:
                    new_target = utils.next_non_white_space_char(view, target)
                    return sublime.Region(s.a + 1, new_target)
                new_target = utils.next_non_white_space_char(view, target)
                return sublime.Region(s.a, new_target + 1)
            else:
                return s

        r = self.view.visible_region()
        row, _ = self.view.rowcol(r.b)
        row -= count + 1

        # XXXX: Subtract 1 so that Sublime Text won't attempt to scroll the line into view, which
        # would be quite annoying.
        target = self.view.text_point(row - 1, 0)

        regions_transformer(self.view, f)
        self.view.show(target)


class _vi_big_m(ViMotionCommand):
    def run(self, count=None, extend=False, mode=None):
        def f(view, s):
            if mode == modes.NORMAL:
                non_ws = utils.next_non_white_space_char(view, target)
                return sublime.Region(non_ws, non_ws)
            elif mode == modes.INTERNAL_NORMAL:
                if s.b >= target:
                    return sublime.Region(s.a + 1, target)
                return sublime.Region(s.a, target)
            elif mode == modes.VISUAL:
                if s.b >= target:
                    new_target = utils.next_non_white_space_char(view, target)
                    return sublime.Region(s.a + 1, new_target)
                new_target = utils.next_non_white_space_char(view, target)
                return sublime.Region(s.a, new_target + 1)
            else:
                return s

        r = self.view.visible_region()
        row_a, _ = self.view.rowcol(r.a)
        row_b, _ = self.view.rowcol(r.b)
        row = ((row_a + row_b) / 2)

        target = self.view.text_point(row, 0)

        regions_transformer(self.view, f)
        self.view.show(target)


class _vi_star(ViMotionCommand, ExactWordBufferSearchBase):
    def run(self, count=1, mode=None, exact_word=True):
        def f(view, s):
            pattern = self.build_pattern(query)
            flags = self.calculate_flags()

            if mode == modes.INTERNAL_NORMAL:
                match = find_wrapping(view,
                                      term=pattern,
                                      start=view.word(s.end()).end(),
                                      end=view.size(),
                                      flags=flags,
                                      times=1)
            else:
                match = find_wrapping(view,
                                      term=pattern,
                                      start=view.word(s.end()).end(),
                                      end=view.size(),
                                      flags=flags,
                                      times=1)

            if match:
                if mode == modes.INTERNAL_NORMAL:
                    return sublime.Region(s.a, match.begin())
                elif state.mode == modes.VISUAL:
                    return sublime.Region(s.a, match.begin())
                elif state.mode == modes.NORMAL:
                    return sublime.Region(match.begin(), match.begin())
            return s

        state = self.state

        query = self.get_query()
        if query:
            self.hilite(query)
            # Ensure n and N can repeat this search later.
            state.last_buffer_search = query

        regions_transformer(self.view, f)


class _vi_octothorp(ViMotionCommand, ExactWordBufferSearchBase):
    def run(self, count=1, mode=None, exact_word=True):
        def f(view, s):
            pattern = self.build_pattern(query)
            flags = self.calculate_flags()

            if mode == modes.INTERNAL_NORMAL:
                match = reverse_find_wrapping(view,
                                              term=pattern,
                                              start=0,
                                              end=start_sel.a,
                                              flags=flags,
                                              times=1)
            else:
                match = reverse_find_wrapping(view,
                                              term=pattern,
                                              start=0,
                                              end=start_sel.a,
                                              flags=flags,
                                              times=1)

            if match:
                if mode == modes.INTERNAL_NORMAL:
                    return sublime.Region(s.b, match.begin())
                elif state.mode == modes.VISUAL:
                    return sublime.Region(s.b, match.begin())
                elif state.mode == modes.NORMAL:
                    return sublime.Region(match.begin(), match.begin())
            return s

        state = self.state

        query = self.get_query()
        if query:
            self.hilite(query)
            # Ensure n and N can repeat this search later.
            state.last_buffer_search = query

        start_sel = self.view.sel()[0]
        regions_transformer(self.view, f)


class _vi_b(ViMotionCommand):
    def run(self, mode=None, count=1):
        def do_motion(view, s):
            if mode == modes.NORMAL:
                pt = word_reverse(self.view, s.b, count)
                return sublime.Region(pt)

            elif mode == modes.INTERNAL_NORMAL:
                pt = word_reverse(self.view, s.b, count)
                return sublime.Region(s.a, pt)

            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_reverse(self.view, s.b - 1, count)
                    if pt < s.a:
                        return sublime.Region(s.a + 1, pt)
                    return sublime.Region(s.a, pt + 1)
                elif s.b < s.a:
                    pt = word_reverse(self.view, s.b, count)
                    return sublime.Region(s.a, pt)

            return s

        regions_transformer(self.view, do_motion)


class _vi_big_b(ViMotionCommand):
    # TODO: Reimplement this.
    def run(self, count=1, mode=None):
        def do_motion(view, s):
            if mode == modes.NORMAL:
                pt = word_reverse(self.view, s.b, count, big=True)
                return sublime.Region(pt)

            elif mode == modes.INTERNAL_NORMAL:
                pt = word_reverse(self.view, s.b, count, big=True)
                return sublime.Region(s.a, pt)

            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_reverse(self.view, s.b - 1, count, big=True)
                    if pt < s.a:
                        return sublime.Region(s.a + 1, pt)
                    return sublime.Region(s.a, pt + 1)
                elif s.b < s.a:
                    pt = word_reverse(self.view, s.b, count, big=True)
                    return sublime.Region(s.a, pt)

            return s

        regions_transformer(self.view, do_motion)


class _vi_underscore(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            if mode == modes.NORMAL:
                current_row, _ = self.view.rowcol(s.b)
                bol = self.view.text_point(current_row + (count - 1), 0)
                bol = utils.next_non_white_space_char(self.view, bol, white_space='\t ')
                return sublime.Region(bol)
            elif mode == modes.INTERNAL_NORMAL:
                current_row, _ = self.view.rowcol(s.b)
                begin = self.view.text_point(current_row, 0)
                end = self.view.text_point(current_row + (count - 1), 0)
                end = self.view.full_line(end).b
                return sublime.Region(begin, end)
            elif mode == modes.VISUAL:
                if self.view.rowcol(s.b)[1] == 0:
                    return s
                bol = self.view.line(s.b - 1).a
                bol = utils.next_non_white_space_char(self.view, bol, white_space='\t ')
                if (s.a < s.b) and (bol < s.a):
                    return sublime.Region(s.a + 1, bol)
                elif (s.a < s.b):
                    return sublime.Region(s.a, bol + 1)
                return sublime.Region(s.a, bol)
            else:
                return s

        regions_transformer(self.view, f)


class _vi_hat(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            if mode == modes.NORMAL:
                bol = self.view.line(s.b).a
                bol = utils.next_non_white_space_char(self.view, bol, white_space='\t ')
                return sublime.Region(bol)
            elif mode == modes.INTERNAL_NORMAL:
                begin = self.view.line(s.b).a
                begin = utils.next_non_white_space_char(self.view, begin, white_space='\t ')
                return sublime.Region(begin, s.b)
            elif mode == modes.VISUAL:
                if self.view.rowcol(s.b)[1] == 0:
                    return s
                bol = self.view.line(s.b - 1).a
                bol = utils.next_non_white_space_char(self.view, bol, white_space='\t ')
                if (s.a < s.b) and (bol < s.a):
                    return sublime.Region(s.a + 1, bol)
                elif (s.a < s.b):
                    return sublime.Region(s.a, bol + 1)
                return sublime.Region(s.a, bol)
            else:
                return s

        regions_transformer(self.view, f)


class _vi_gj(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == modes.NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': True, 'extend': False})
        elif mode == modes.VISUAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': True, 'extend': True})
        elif mode == modes.INTERNAL_NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': True, 'extend': False})


class _vi_gk(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == modes.NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': False, 'extend': False})
        elif mode == modes.VISUAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': False, 'extend': True})
        elif mode == modes.INTERNAL_NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': False, 'extend': False})


class _vi_g__(ViMotionCommand):
    def run(self, count=1, mode=None):
        def f(view, s):
            if mode == modes.NORMAL:
                eol = view.line(s.b).b
                return sublime.Region(eol - 1, eol - 1)

            elif mode == modes.VISUAL:
                eol = view.line(s.b - 1).b
                return sublime.Region(s.a, eol)

            elif mode == modes.INTERNAL_NORMAL:
                eol = view.line(s.b).b
                return sublime.Region(s.a, eol)

            return s

        regions_transformer(self.view, f)


class _vi_ctrl_u(ViMotionCommand):
    def prev_half_page(self, count):

        origin = self.view.sel()[0]

        visible = self.view.visible_region()
        row_a = self.view.rowcol(visible.a)[0]
        row_b = self.view.rowcol(visible.b)[0]

        half_page_span = (row_b - row_a) // 2 * count

        prev_half_page = self.view.rowcol(origin.b)[0] - half_page_span

        pt = self.view.text_point(prev_half_page, 0)
        return sublime.Region(pt, pt), (self.view.rowcol(visible.b)[0] -
                                        self.view.rowcol(pt)[0])

    def run(self, mode=None, count=None):

        def f(view, s):
            if mode == modes.NORMAL:
                return previous

            elif mode == modes.VISUAL:
                return sublime.Region(s.a, previous.b)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, previous.b)

            elif mode == modes.VISUAL_LINE:
                return sublime.Region(s.a, self.view.full_line(previous.b).b)

            return s

        previous, scroll_amount = self.prev_half_page(count)
        regions_transformer(self.view, f)


class _vi_ctrl_d(ViMotionCommand):
    def next_half_page(self, count=1, mode=None):

        origin = self.view.sel()[0]

        visible = self.view.visible_region()
        row_a = self.view.rowcol(visible.a)[0]
        row_b = self.view.rowcol(visible.b)[0]

        half_page_span = (row_b - row_a) // 2 * count

        next_half_page = self.view.rowcol(origin.b)[0] + half_page_span

        pt = self.view.text_point(next_half_page, 0)
        return sublime.Region(pt, pt), (self.view.rowcol(pt)[0] -
                                        self.view.rowcol(visible.a)[0])

    def run(self, mode=None, extend=False, count=None):

        def f(view, s):
            if mode == modes.NORMAL:
                return next

            elif mode == modes.VISUAL:
                return sublime.Region(s.a, next.b)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, next.b)

            elif mode == modes.VISUAL_LINE:
                return sublime.Region(s.a, self.view.full_line(next.b).b)

            return s

        next, scroll_amount = self.next_half_page(count)
        regions_transformer(self.view, f)


class _vi_pipe(ViMotionCommand):
    def col_to_pt(self, pt, nr):
        if self.view.line(pt).size() < nr:
            return self.view.line(pt).b - 1

        row = self.view.rowcol(pt)[0]
        return self.view.text_point(row, nr) - 1

    def run(self, mode=None, count=None):
        def f(view, s):
            if mode == modes.NORMAL:
                pt = self.col_to_pt(pt=s.b, nr=count)
                return sublime.Region(pt, pt)

            elif mode == modes.VISUAL:
                pt = self.col_to_pt(pt=s.b - 1, nr=count)
                if s.a < s.b:
                    if pt < s.a:
                        return sublime.Region(s.a + 1, pt)
                    else:
                        return sublime.Region(s.a, pt + 1)
                else:
                    if pt > s.a:
                        return sublime.Region(s.a - 1, pt + 1)
                    else:
                        return sublime.Region(s.a, pt)

            elif mode == modes.INTERNAL_NORMAL:
                pt = self.col_to_pt(pt=s.b, nr=count)
                if s.a < s.b:
                    return sublime.Region(s.a, pt)
                else:
                    return sublime.Region(s.a + 1, pt)

            return s

        regions_transformer(self.view, f)


class _vi_ge(ViMotionCommand):
    def run(self, mode=None, count=1):
        def to_word_end(view, s):
            if mode == modes.NORMAL:
                pt = word_end_reverse(view, s.b, count)
                return sublime.Region(pt)
            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_end_reverse(view, s.b - 1, count)
                    if pt > s.a:
                        return sublime.Region(s.a, pt + 1)
                    return sublime.Region(s.a + 1, pt)
                pt = word_end_reverse(view, s.b, count)
                return sublime.Region(s.a, pt)
            return s

        regions_transformer(self.view, to_word_end)


class _vi_g_big_e(ViMotionCommand):
    def run(self, mode=None, count=1):
        def to_word_end(view, s):
            if mode == modes.NORMAL:
                pt = word_end_reverse(view, s.b, count, big=True)
                return sublime.Region(pt)
            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_end_reverse(view, s.b - 1, count, big=True)
                    if pt > s.a:
                        return sublime.Region(s.a, pt + 1)
                    return sublime.Region(s.a + 1, pt)
                pt = word_end_reverse(view, s.b, count, big=True)
                return sublime.Region(s.a, pt)
            return s

        regions_transformer(self.view, to_word_end)


class _vi_left_paren(ViMotionCommand):
    def find_previous_sentence_end(self, r):
        sen = r
        pt = utils.previous_non_white_space_char(self.view, sen.a, white_space='\n \t')
        sen = sublime.Region(pt, pt)
        while True:
            sen = self.view.expand_by_class(sen, sublime.CLASS_LINE_END | sublime.CLASS_PUNCTUATION_END)
            if sen.a <= 0 or self.view.substr(sen.begin() - 1) in ('.', '\n', '?', '!'):
                if self.view.substr(sen.begin() - 1) == '.' and not self.view.substr(sen.begin()) == ' ':
                    continue
                return sen

    def run(self, mode=None, count=1):

        def f(view, s):
            # TODO: must skip empty paragraphs.
            sen = self.find_previous_sentence_end(s)

            if mode == modes.NORMAL:
                return sublime.Region(sen.a, sen.a)

            elif mode == modes.VISUAL:
                return sublime.Region(s.a + 1, sen.a +  1)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, sen.a + 1)

            return s

        regions_transformer(self.view, f)



class _vi_right_paren(ViMotionCommand):
    def find_next_sentence_end(self, r):
        sen = r
        non_ws = utils.next_non_white_space_char(self.view, sen.b, '\t \n')
        sen = sublime.Region(non_ws, non_ws)
        while True:
            sen = self.view.expand_by_class(sen, sublime.CLASS_PUNCTUATION_START |
                                                 sublime.CLASS_LINE_END)
            if (sen.b == self.view.size() or
                (self.view.substr(sublime.Region(sen.b, sen.b + 2)).endswith(('. ', '.\t'))) or
                (self.view.substr(sublime.Region(sen.b, sen.b + 1)).endswith(('?', '!'))) or
                (self.view.substr(self.view.line(sen.b)).strip() == '')):
                    if self.view.substr(sen.b) in '.?!':
                        return sublime.Region(sen.a, sen.b + 1)
                    else:
                        if self.view.line(sen.b).empty():
                            return sublime.Region(sen.a, sen.b)
                        else:
                            return self.view.full_line(sen.b)

    def run(self, mode=None, count=1):
        def f(view, s):
            # TODO: must skip empty paragraphs.
            sen = self.find_next_sentence_end(s)

            if mode == modes.NORMAL:
                target = min(sen.b, view.size() - 1)
                return sublime.Region(target, target)

            elif mode == modes.VISUAL:
                # TODO: Must encompass new line char too?
                return sublime.Region(s.a, sen.b)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, sen.b)

            return s

        regions_transformer(self.view, f)


class _vi_question_mark_impl(ViMotionCommand, BufferSearchBase):
    def run(self, search_string, mode=None, count=1, extend=False):
        def f(view, s):
            # FIXME: readjust carets if we searched for '\n'.
            if mode == modes.VISUAL:
                return sublime.Region(s.end(), found.a)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.end(), found.a)

            elif mode == modes.NORMAL:
                return sublime.Region(found.a, found.a)

            elif mode == modes.VISUAL_LINE:
                # FIXME: Ensure that the very first ? search excludes the current line.
                return sublime.Region(s.end(), view.full_line(found.a).a)

            return s

        # This happens when we attempt to repeat the search and there's no search term stored yet.
        if search_string is None:
            return

        flags = self.calculate_flags()
        # FIXME: What should we do here? Case-sensitive or case-insensitive search? Configurable?
        found = reverse_find_wrapping(self.view,
                                      term=search_string,
                                      start=0,
                                      end=self.view.sel()[0].b,
                                      flags=flags,
                                      times=count)

        if not found:
            print("Vintageous: Pattern not found.")
            return

        regions_transformer(self.view, f)
        self.hilite(search_string)
class _vi_question_mark(ViMotionCommand, BufferSearchBase):
    def run(self, default=''):
        self.state.reset_during_init = False
        state = self.state
        on_change = self.on_change if state.settings.vi['incsearch'] else None
        mark_as_widget(self.view.window().show_input_panel(
                                                            '',
                                                            default,
                                                            self.on_done,
                                                            on_change,
                                                            self.on_cancel))

    def on_done(self, s):
        state = self.state
        state.sequence += s + '<CR>'
        self.view.erase_regions('vi_inc_search')
        state.motion = cmd_defs.ViSearchBackwardImpl(term=s)

        # If s is empty, we must repeat the last search.
        state.last_buffer_search = s or state.last_buffer_search
        state.eval()

    def on_change(self, s):
        flags = self.calculate_flags()
        self.view.erase_regions('vi_inc_search')
        state = self.state
        occurrence = reverse_find_wrapping(self.view,
                                 term=s,
                                 start=0,
                                 end=self.view.sel()[0].b,
                                 flags=flags,
                                 times=state.count)
        if occurrence:
            if state.mode == modes.VISUAL:
                occurrence = sublime.Region(self.view.sel()[0].a, occurrence.a)
            self.view.add_regions('vi_inc_search', [occurrence], 'comment', '')
            if not self.view.visible_region().contains(occurrence):
                self.view.show(occurrence)

    def on_cancel(self):
        self.view.erase_regions('vi_inc_search')
        state = self.state
        state.reset_command_data()

        if not self.view.visible_region().contains(self.view.sel()[0]):
            self.view.show(self.view.sel()[0])


class _vi_n(ViMotionCommand):
    # TODO: This is a jump.
    def run(self, mode=None, count=1, search_string=''):
        self.view.run_command('_vi_slash_impl', {'mode': mode, 'count': count, 'search_string': search_string})


class _vi_big_n(ViMotionCommand):
    # TODO: This is a jump.
    def run(self, count=1, mode=None, search_string=''):
        self.view.run_command('_vi_question_mark_impl', {'mode': mode, 'count': count, 'search_string': search_string})


class _vi_big_e(ViMotionCommand):
    def run(self, mode=None, count=1):
        def do_move(view, s):
            if mode == modes.NORMAL:
                pt = units.word_ends(view, s.b, count=count, big=True)
                return sublime.Region(pt - 1)

            elif mode == modes.INTERNAL_NORMAL:
                pt = units.word_ends(view, s.b, count=count, big=True)
                return sublime.Region(pt - 1)

            elif mode in (modes.VISUAL, modes.VISUAL_BLOCK):
                pt = units.word_ends(view, s.b, count=count, big=True)
                if s.a > s.b:
                    if pt > s.a:
                        return sublime.Region(s.a - 1, pt)
                    return sublime.Region(s.a, pt - 1)
                return sublime.Region(s.a, pt)
            return s

        regions_transformer(self.view, do_move)


class _vi_ctrl_f(ViMotionCommand):
    def run(self, mode=None, count=1):
        def extend_to_full_line(view, s):
            return view.full_line(s.b)

        if mode == modes.NORMAL:
            self.view.run_command('move', {'by': 'pages', 'forward': True})
        if mode == modes.VISUAL:
            self.view.run_command('move', {'by': 'pages', 'forward': True, 'extend': True})
        elif mode == modes.VISUAL_LINE:
            self.view.run_command('move', {'by': 'pages', 'forward': True, 'extend': True})
            regions_transformer(self.view, extend_to_full_line)
        elif mode == modes.VISUAL_BLOCK:
            return


class _vi_ctrl_b(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == modes.NORMAL:
            self.view.run_command('move', {'by': 'pages', 'forward': False})
        elif mode != modes.NORMAL:
            return


class _vi_enter(ViMotionCommand):
   def run(self, mode=None, count=1):
        self.view.run_command('_vi_j', {'mode': mode, 'count': count})

        def advance(view, s):
            if mode == modes.NORMAL:
                pt = utils.next_non_white_space_char(view, s.b,
                                                     white_space=' \t')
                return sublime.Region(pt)
            elif mode == modes.VISUAL:
                if s.a < s.b:
                    pt = utils.next_non_white_space_char(view, s.b - 1,
                                                         white_space=' \t')
                    return sublime.Region(s.a, pt + 1)
                pt = utils.next_non_white_space_char(view, s.b,
                                                     white_space=' \t')
                return sublime.Region(s.a, pt)
            return s

        regions_transformer(self.view, advance)


class _vi_shift_enter(ViMotionCommand):
   def run(self, mode=None, count=1):
        self.view.run_command('_vi_ctrl_f', {'mode': mode, 'count': count})


class _vi_select_text_object(ViMotionCommand):
    def run(self, text_object=None, mode=None, count=1, extend=False, inclusive=False):
        def f(view, s):
            # TODO: Vim seems to swallow the delimiters if you give this command a count, which is
            #       a pretty weird behavior.
            if mode == modes.INTERNAL_NORMAL:

                return get_text_object_region(view, s, text_object,
                                              inclusive=inclusive,
                                              count=count)

            if mode == modes.VISUAL:
                return get_text_object_region(view, s, text_object,
                                              inclusive=inclusive,
                                              count=count)

            return s

        regions_transformer(self.view, f)


class _vi_go_to_symbol(ViMotionCommand):
    """Go to local declaration. Differs from Vim because it leverages Sublime Text's ability to
       actually locate symbols (Vim simply searches from the top of the file).
    """
    def find_symbol(self, r, globally=False):
        query = self.view.substr(self.view.word(r))
        fname = self.view.file_name().replace('\\', '/')

        locations = self.view.window().lookup_symbol_in_index(query)
        if not locations:
            return

        try:
            if not globally:
                location = [hit[2] for hit in locations if fname.endswith(hit[1])][0]
                return location[0] - 1, location[1] - 1
            else:
                # TODO: There might be many symbols with the same name.
                return locations[0]
        except IndexError:
            return


    def run(self, count=1, mode=None, globally=False):

        def f(view, s):
            if mode == modes.NORMAL:
                return sublime.Region(location, location)

            elif mode == modes.VISUAL:
                return sublime.Region(s.a + 1, location)

            elif mode == modes.INTERNAL_NORMAL:
                return sublime.Region(s.a, location)

            return s

        current_sel = self.view.sel()[0]
        self.view.sel().clear()
        self.view.sel().add(current_sel)

        location = self.find_symbol(current_sel, globally=globally)
        if not location:
            return

        if globally:
            # Global symbol; simply open the file; not a motion.
            # TODO: Perhaps must be a motion if the target file happens to be
            #       the current one?
            self.view.window().open_file(
                location[0] + ':' + ':'.join([str(x) for x in location[2]]),
                sublime.ENCODED_POSITION)
            return

        # Local symbol; select.
        location = self.view.text_point(*location)
        regions_transformer(self.view, f)


class _vi_gm(ViMotionCommand):
    """
    Vim: `gm`
    """
    def run(self, mode=None, count=1):
        if mode != modes.NORMAL:
            utils.blink()
            return

        def advance(view, s):
            line = view.line(s.b)
            delta = (line.b - s.b) // 2
            return sublime.Region(min(s.b + delta, line.b - 1))

        regions_transformer(self.view, advance)

########NEW FILE########
__FILENAME__ = xsupport
import threading

import sublime
import sublime_plugin

from Vintageous import local_logger
from Vintageous.state import _init_vintageous
from Vintageous.state import State
from Vintageous.vi import utils
from Vintageous.vi.dot_file import DotFile
from Vintageous.vi.utils import modes
from Vintageous.vi.utils import regions_transformer
from Vintageous.vi import cmd_defs


_logger = local_logger(__name__)


class _vi_slash_on_parser_done(sublime_plugin.WindowCommand):
    def run(self, key=None):
        state = State(self.window.active_view())
        state.motion = cmd_defs.ViSearchForwardImpl()
        state.last_buffer_search = state.motion._inp or state.last_buffer_search


class _vi_question_mark_on_parser_done(sublime_plugin.WindowCommand):
    def run(self, key=None):
        state = State(self.window.active_view())
        state.motion = cmd_defs.ViSearchBackwardImpl()
        state.last_buffer_search = state.motion._inp or state.last_buffer_search


# TODO: Test me.
class VintageStateTracker(sublime_plugin.EventListener):
    def on_post_save(self, view):
        # Ensure the carets are within valid bounds. For instance, this is a concern when
        # `trim_trailing_white_space_on_save` is set to true.
        state = State(view)
        view.run_command('_vi_adjust_carets', {'mode': state.mode})

    def on_query_context(self, view, key, operator, operand, match_all):
        vintage_state = State(view)
        return vintage_state.context.check(key, operator, operand, match_all)


# TODO: Test me.
class ViFocusRestorerEvent(sublime_plugin.EventListener):
    def __init__(self):
        self.timer = None

    def action(self):
        self.timer = None

    def on_activated(self, view):
        if self.timer:
            self.timer.cancel()
            # Switching to a different view; enter normal mode.
            _init_vintageous(view)
        else:
            # Switching back from another application. Ignore.
            pass

    def on_new(self, view):
        # Without this, on OS X Vintageous might not initialize correctly if the user leaves
        # the application in a windowless state and then creates a new buffer.
        if sublime.platform() == 'osx':
            _init_vintageous(view)

    def on_load(self, view):
        # Without this, on OS X Vintageous might not initialize correctly if the user leaves
        # the application in a windowless state and then creates a new buffer.
        if sublime.platform() == 'osx':
            try:
                _init_vintageous(view)
            except AttributeError:
                _logger().error(
                    '[VintageStateTracker] .settings() missing during .on_load() for {0}'
                        .format(view.file_name()))

    def on_deactivated(self, view):
        self.timer = threading.Timer(0.25, self.action)
        self.timer.start()


class _vi_adjust_carets(sublime_plugin.TextCommand):
    def run(self, edit, mode=None):
        def f(view, s):
            if mode in (modes.NORMAL, modes.INTERNAL_NORMAL):
                if  ((view.substr(s.b) == '\n' or s.b == view.size())
                     and not view.line(s.b).empty()):
                        # print('adjusting carets')
                        return sublime.Region(s.b - 1)
            return s

        regions_transformer(self.view, f)


class Sequence(sublime_plugin.TextCommand):
    """Required so that mark_undo_groups_for_gluing and friends work.
    """
    def run(self, edit, commands):
        for cmd, args in commands:
            self.view.run_command(cmd, args)


class ResetVintageous(sublime_plugin.WindowCommand):
    def run(self):
        v = self.window.active_view()
        v.settings().erase('vintage')
        _init_vintageous(v)
        print("Package.Vintageous: State reset.")
        sublime.status_message("Vintageous: State reset")


class ForceExitFromCommandMode(sublime_plugin.WindowCommand):
    """
    A sort of a panic button.
    """
    def run(self):
        v = self.window.active_view()
        v.settings().erase('vintage')
        # XXX: What happens exactly when the user presses Esc again now? Which
        #      more are we in?

        v.settings().set('command_mode', False)
        v.settings().set('inverse_caret_state', False)

        print("Vintageous: Exiting from command mode.")
        sublime.status_message("Vintageous: Exiting from command mode.")


class VintageousToggleCtrlKeys(sublime_plugin.WindowCommand):
    def run(self):
        prefs = sublime.load_settings('Preferences.sublime-settings')
        value = prefs.get('vintageous_use_ctrl_keys', False)
        prefs.set('vintageous_use_ctrl_keys', (not value))
        sublime.save_settings('Preferences.sublime-settings')
        status = 'enabled' if (not value) else 'disabled'
        print("Package.Vintageous: Use of Ctrl- keys {0}.".format(status))
        sublime.status_message("Vintageous: Use of Ctrl- keys {0}".format(status))


class ReloadVintageousSettings(sublime_plugin.TextCommand):
    def run(self, edit):
        DotFile.from_user().run()

########NEW FILE########
__FILENAME__ = xsupport_mouse
import sublime
import sublime_plugin

from Vintageous.vi.utils import IrreversibleMouseTextCommand

########NEW FILE########
