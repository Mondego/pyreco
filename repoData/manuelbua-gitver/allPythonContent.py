__FILENAME__ = commands
#!/usr/bin/env python2
# coding=utf-8

"""
Defines gitver commands
"""

import re
import os
import sys
from string import Template

from termcolors import term, bold
from git import get_repo_info
from gitver.storage import KVStore
from sanity import check_gitignore
from defines import CFGDIR, PRJ_ROOT, CFGDIRNAME
from version import gitver_version, gitver_buildid


# file where to store NEXT strings <=> TAG user-defined mappings
NEXT_STORE_FILE = os.path.join(CFGDIR, ".next_store")
TPLDIR = os.path.join(CFGDIR, 'templates')

user_version_matcher = r"v{0,1}(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)" \
                       r"(?:\.(?P<revision>\d+))?$"


#
# helpers
#

def template_path(name):
    """
    Constructs and returns the absolute path for the specified template file
    name.
    """
    return os.path.join(TPLDIR, name)


def parse_templates(cfg, templates, repo, next_custom, preview):
    """
    Parse one or more templates, substitute placeholder variables with
    real values and write the result to the file specified in the template.

    If preview is True, then the output will be written to the stdout while
    informative messages will be output to the stderr.
    """
    for t in templates.split(' '):
        tpath = template_path(t)
        if os.path.exists(tpath):
            with open(tpath, 'r') as fp:
                lines = fp.readlines()

            if len(lines) < 2:
                term.err("The template \"" + t + "\" is not valid, aborting.")
                return

            if not lines[0].startswith('#'):
                term.err("The template \"" + t + "\" doesn't define any valid "
                                                 "output, aborting.")
                return

            output = str(lines[0]).strip(' #\n')

            # resolve relative paths to the project's root
            if not os.path.isabs(output):
                output = os.path.join(PRJ_ROOT, output)

            outdir = os.path.dirname(output)

            if not os.path.exists(outdir):
                term.err("The template output directory \"" + outdir +
                         "\" doesn't exists.")

            term.info("Processing template \"" + bold(t) + "\" for " + output +
                      "...")

            lines = lines[1:]
            xformed = Template("".join(lines))
            vstring = build_version_string(cfg, repo, False, next_custom)
            args = build_format_args(cfg, repo, next_custom)
            keywords = {
                'CURRENT_VERSION': vstring,
                'MAJOR': args['maj'],
                'MINOR': args['min'],
                'PATCH': args['patch'],
                'REV': args['rev'],
                'REV_PREFIX': args['rev_prefix'],
                'BUILD_ID': args['build_id'],
                'FULL_BUILD_ID': args['build_id_full'],
                'COMMIT_COUNT': args['commit_count'],
                'COMMIT_COUNT_STR':
                str(args['commit_count']) if args['commit_count'] > 0 else '',

                'COMMIT_COUNT_PREFIX': args['commit_count_prefix'],
                'META_PR': args['meta_pr'],
                'META_PR_PREFIX': args['meta_pr_prefix']
            }

            try:
                res = xformed.substitute(keywords)
            except KeyError as e:
                term.err("Unknown key \"" + e.message + "\" found, aborting.")
                sys.exit(1)

            if not preview:
                try:
                    fp = open(output, 'w')
                    fp.write(res)
                    fp.close()
                except IOError:
                    term.err("Couldn't write file \"" + output + "\"")
                    sys.exit(1)
            else:
                term.out(res)

            wrote_bytes = len(res) if preview else os.stat(output).st_size
            term.info("Done, " + str(wrote_bytes) + " bytes written.")
        else:
            term.err("Couldn't find the \"" + t + "\" template")
            sys.exit(1)


def parse_user_next_stable(user):
    """
    Parse the specified user-defined string containing the next stable version
    numbers and returns the discretized matches in a dictionary.
    """
    try:
        data = re.match(user_version_matcher, user).groupdict()
        if len(data) < 3:
            raise AttributeError
    except AttributeError:
        return False
    return data


def build_format_args(cfg, repo_info, next_custom=None):
    """
    Builds the formatting arguments by processing the specified repository
    information and returns them.

    If a tag defines pre-release metadata, this will have the precedence
    over any existing user-defined string.
    """
    in_next = repo_info['count'] > 0
    has_next_custom = next_custom is not None and len(next_custom) > 0

    vmaj = repo_info['maj']
    vmin = repo_info['min']
    vpatch = repo_info['patch']
    vrev = repo_info['rev']
    vcount = repo_info['count']
    vpr = repo_info['pr']
    vbuildid = repo_info['build-id']
    has_pr = vpr is not None
    has_rev = vrev is not None

    # pre-release metadata in a tag has precedence over user-specified
    # NEXT strings
    if in_next and has_next_custom and not has_pr:
        u = parse_user_next_stable(next_custom)
        if not u:
            term.err("Invalid custom NEXT version numbers detected!")
            sys.exit(1)
        vmaj = u['maj']
        vmin = u['min']
        vpatch = u['patch']
        vrev = u['revision']
        has_rev = vrev is not None

    meta_pr = vpr if has_pr else \
        cfg['default_meta_pr_in_next'] if in_next and has_next_custom else \
        cfg['default_meta_pr_in_next_no_next'] if in_next else ''

    args = {
        'maj': vmaj,
        'min': vmin,
        'patch': vpatch,
        'rev': vrev if has_rev else '',
        'rev_prefix': '.' if has_rev else '',
        'meta_pr': meta_pr,
        'meta_pr_prefix': cfg['meta_pr_prefix'] if len(meta_pr) > 0 else '',
        'commit_count': vcount if vcount > 0 else '',
        'commit_count_prefix': cfg['commit_count_prefix'] if vcount > 0 else '',
        'build_id': vbuildid,
        'build_id_full': repo_info['full-build-id']
    }

    return args


def build_version_string(cfg, repo, promote=False, next_custom=None):
    """
    Builds the final version string by processing the specified repository
    information, optionally handling version promotion.

    Version promotion will just return the user-specified next version string,
    if any is present, else an empty string will be returned.
    """
    in_next = repo['count'] > 0
    has_next_custom = next_custom is not None and len(next_custom) > 0

    if promote:
        if has_next_custom:
            # simulates next real version after proper tagging
            version = next_custom
            return version
        else:
            return ''

    fmt = cfg['format'] if not in_next else cfg['format_next']
    return fmt % build_format_args(cfg, repo, next_custom)


#
# commands
#

def cmd_version(cfg, args):
    """
    Generates gitver's version string and license information and prints it
    to the stdout.
    """
    v = ('v' + gitver_version) if gitver_version is not None else 'n/a'
    b = gitver_buildid if gitver_buildid is not None else 'n/a'
    term.out("This is gitver " + bold(v))
    term.out("Full build ID is " + bold(b))
    from gitver import __license__
    term.out(__license__)


def cmd_init(cfg, args):
    """
    Initializes the current repository by creating the gitver's configuration
    directory and creating the default configuration file, if none is present.

    Multiple executions of this command will regenerate the default
    configuration file whenever it's not found.
    """
    from config import create_default_configuration_file
    i = 0

    if not os.path.exists(CFGDIR):
        i += 1
        os.makedirs(CFGDIR)

    if not os.path.exists(TPLDIR):
        i += 1
        os.makedirs(TPLDIR)

    # try create the default configuration file
    wrote_cfg = create_default_configuration_file()

    if wrote_cfg:
        term.out("gitver has been initialized and configured.")
    else:
        term.warn("gitver couldn't create the default configuration file, "
                  "does it already exist?")


def cmd_current(cfg, args):
    """
    Generates the current version string, depending on the state of the
    repository and prints it to the stdout.
    """
    next_store = KVStore(NEXT_STORE_FILE)
    repo_info = get_repo_info()
    last_tag = repo_info['last-tag']
    has_next_custom = next_store.has(last_tag)
    next_custom = next_store.get(last_tag) if has_next_custom else None
    term.out(build_version_string(cfg, repo_info, False, next_custom))


def cmd_info(cfg, args):
    """
    Generates version string and repository information and prints it to the
    stdout.
    """
    next_store = KVStore(NEXT_STORE_FILE)
    repo_info = get_repo_info()
    last_tag = repo_info['last-tag']

    has_next_custom = next_store.has(last_tag)
    next_custom = next_store.get(last_tag) if has_next_custom else None

    if has_next_custom:
        nvn = term.next(next_custom)
    else:
        nvn = "none, defaulting to " + \
              term.next("-" + cfg['default_meta_pr_in_next_no_next']) + \
              " suffix"

    term.out("Most recent tag: " + term.tag(last_tag))

    if repo_info['pr'] is None and repo_info['count'] > 0:
        term.out("Using NEXT defined as: " + nvn)
        term.out("(Pre-release metadata: none)")
    elif repo_info['pr'] is not None:
        term.out("(NEXT defined as: " + nvn + ")")
        term.out("Using pre-release metadata: " +
                 term.tag(str(repo_info['pr'])))

    term.out("Current build ID: " + term.tag(repo_info['full-build-id']))

    promoted = build_version_string(cfg, repo_info, True, next_custom)
    term.out(
        "Current version: " + "v" +
        term.ver(build_version_string(
            cfg, repo_info, False, next_custom)) +
        (" => v" + term.prom(promoted) if len(promoted) > 0 else '')
    )


def cmd_list_templates(cfg, args):
    """
    Generates a list of available templates by inspecting the gitver's template
    directory and prints it to the stdout.
    """
    tpls = [f for f in os.listdir(TPLDIR) if os.path.isfile(template_path(f))]
    if len(tpls) > 0:
        term.out("Available templates:")
        for t in tpls:
            term.out("    " + bold(t) + " (" + template_path(t) + ")")
    else:
        term.out("No templates available in " + TPLDIR)


def __cmd_build_template(cfg, args, preview=False):
    """
    Internal-only function used for avoiding code duplication between
    template-operating functions.

    See cmd_build_template and cmd_preview_template for the full docs.
    """
    next_store = KVStore(NEXT_STORE_FILE)
    repo_info = get_repo_info()
    last_tag = repo_info['last-tag']
    has_next_custom = next_store.has(last_tag)
    next_custom = next_store.get(last_tag) if has_next_custom else None
    parse_templates(cfg, args.templates, repo_info, next_custom, preview)


def cmd_build_template(cfg, args):
    """
    Performs placeholder variables substitution on the templates specified by
    the @param args parameter and write the result to each respective output
    file specified by the template itself.
    """
    __cmd_build_template(cfg, args)


def cmd_preview_template(cfg, args):
    """
    Performs placeholder variables substitution on the templates specified by
    the @param args parameter and prints the result to the stdout.
    """
    __cmd_build_template(cfg, args, True)


def cmd_next(cfg, args):
    """
    Sets and defines the next stable version string for the most recent and
    reachable tag.

    The string should be supplied in the format "maj.min.patch[.revision]",
    where angular brackets denotes an optional value.

    All values are expected to be decimal numbers without leading zeros.
    """
    next_store = KVStore(NEXT_STORE_FILE)
    repo_info = get_repo_info()

    last_tag = repo_info['last-tag']

    vn = args.next_version_numbers
    user = parse_user_next_stable(vn)
    if not user:
        term.err("Please specify valid version numbers.\nThe expected "
                 "format is <MAJ>.<MIN>.<PATCH>[.<REVISION>], e.g. v0.0.1, "
                 "0.0.1 or 0.0.2.1")
        sys.exit(1)

    custom = "%d.%d.%d" % (int(user['maj']), int(user['min']), int(user['patch']))

    if user['revision'] is not None:
        custom += ".%d" % (int(user['revision']))

    next_store.set(last_tag, custom).save()
    term.out("Set NEXT version string to " + term.next(custom) +
             " for the current tag " + term.tag(last_tag))


def cmd_clean(cfg, args):
    """
    Removes the user-defined next stable version for the most recent and
    reachable tag or for the tag specified by the @param args parameter.
    """
    next_store = KVStore(NEXT_STORE_FILE)
    if len(args.tag) > 0:
        tag = args.tag
    else:
        repo_info = get_repo_info()
        tag = repo_info['last-tag']

    has_custom = next_store.has(tag)
    next_custom = next_store.get(tag) if has_custom else None

    if has_custom:
        next_store.rm(tag).save()
        term.out("Cleaned up custom string version \"" + next_custom +
                 "\" for tag \"" + tag + "\"")
    else:
        term.out("No custom string version found for tag \"" + tag + "\"")


def cmd_cleanall(cfg, args):
    """
    Removes ALL user-defined next stable versions.
    """
    if os.path.exists(NEXT_STORE_FILE):
        os.unlink(NEXT_STORE_FILE)
        term.out("All previously set custom strings have been removed.")
    else:
        term.out("No NEXT custom strings found.")


def cmd_list_next(cfg, args):
    """
    Generates a list of all user-defined next stable versions and prints them
    to the stdout.
    """
    next_store = KVStore(NEXT_STORE_FILE)
    repo_info = get_repo_info()
    last_tag = repo_info['last-tag']
    has_next_custom = next_store.has(last_tag)
    if not next_store.empty():
        def print_item(k, v):
            term.out("    %s => %s" % (term.tag(k), term.next(v)) +
                     (' (*)' if k == last_tag else ''))

        term.out("Currently set NEXT custom strings (*=most recent and "
                 "reachable tag):")
        for tag, vstring in sorted(next_store.items()):
            print_item(tag, vstring)

        if not has_next_custom:
            print_item(last_tag, '<undefined>')

    else:
        term.out("No NEXT custom strings set.")


def cmd_check_gitignore(cfg, args):
    """
    Provides a way to ensure that at least one line in the .gitignore file for
    the current repository defines the '.gitver' directory in some way.

    This means that even a definition such as "!.gitver" will pass the check,
    but this imply some reasoning has been made before declaring something like
    this.
    """
    if check_gitignore():
        term.out("Your .gitignore file looks fine.")
    else:
        term.out("Your .gitignore file doesn't define any rule for the " +
                 CFGDIRNAME + "\nconfiguration directory: it's recommended to "
                 "exclude it from\nthe repository, unless you know what you "
                 "are doing. If you are not\nsure, add this line to your "
                 ".gitignore file:\n\n    " + CFGDIRNAME + "\n")

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python2
# coding=utf-8

"""
The default per-repository configuration
"""

import sys
import json
import string
from os.path import exists, dirname
from gitver.defines import CFGFILE
from termcolors import term, bold

default_config_text = """{
    # automatically generated configuration file
    #
    # These defaults implement Semantic Versioning as described in the latest
    # available documentation at http://semver.org/spec/v2.0.0.html

    # by default, terminal output is NOT colorized for compatibility with older
    # terminal emulators: you may enable this if you like a more modern look
    "use_terminal_colors": false,

    # prevent gitver from storing any information in its configuration directory
    # if the .gitignore file doesn't exclude it from the repository
    "safe_mode": true,

    # default pre-release metadata when commit count > 0 AND
    # no NEXT has been defined
    "default_meta_pr_in_next_no_next": "NEXT",

    # default pre-release metadata when commit count > 0
    "default_meta_pr_in_next": "SNAPSHOT",

    # default pre-release metadata prefix
    "meta_pr_prefix": "-",

    # default commit count prefix
    "commit_count_prefix": ".",

    # Python-based format string variable names are:
    #     maj, min, patch, rev, rev_prefix, meta_pr_prefix, meta_pr,
    #     commit_count_prefix, commit_count, build_id, build_id_full
    #
    # Note that prefixes will be empty strings if their valued counterpart
    # doesn't have a meaningful value (i.e., 0 for commit count, no meta
    # pre-release, ..)

    # format string used to build the current version string when the
    # commit count is 0
    "format": "%(maj)s.%(min)s.%(patch)s%(rev_prefix)s%(rev)s%(meta_pr_prefix)s%(meta_pr)s",

    # format string used to build the current version string when the
    # commit count is > 0
    "format_next": "%(maj)s.%(min)s.%(patch)s%(rev_prefix)s%(rev)s%(meta_pr_prefix)s%(meta_pr)s%(commit_count_prefix)s%(commit_count)s+%(build_id)s"
}"""


def remove_comments(text):
    """
    Removes line comments denoted by sub-strings starting with a '#'
    character from the specified string, construct a new text and returns it.
    """
    data = string.split(text, '\n')
    ret = ''
    for line in data:
        if not line.strip().startswith('#'):
            ret += line
    return ret


default_config = json.loads(remove_comments(default_config_text))


def create_default_configuration_file():
    """
    Creates a default configuration file from the default gitver's
    configuration text string in the predefined gitver's configuration
    directory.
    """
    if not exists(CFGFILE):
        if exists(dirname(CFGFILE)):
            with open(CFGFILE, 'w') as f:
                f.writelines(default_config_text)
                return True
    return False


def load_user_config():
    """
    Returns the gitver's configuration: tries to read the stored configuration
    file and merges it with the default one, ensuring a valid configuration is
    always returned.
    """
    try:

        with open(CFGFILE, 'r') as f:
            data = ''
            for line in f:
                l = line.strip()
                if not l.startswith('#'):
                    data += l
            user = json.loads(data)

    except IOError:
        user = dict()

    except (ValueError, KeyError) as v:
        term.err("An error occured parsing the configuration file \"" +
                 CFGFILE + "\": " + v.message +
                 "\nPlease check its syntax or rename it and generate the "
                 "default one with the " + bold("gitver init") + " command.")
        sys.exit(1)

    # merge user with defaults
    return dict(default_config, **user)

########NEW FILE########
__FILENAME__ = defines
#!/usr/bin/env python2
# coding=utf-8

"""
Project definitions
"""

import os
from gitver.git import project_root

PRJ_ROOT = project_root()

CFGDIRNAME = ".gitver"
CFGDIR = os.path.join(PRJ_ROOT, CFGDIRNAME)
CFGFILE = os.path.join(CFGDIR, "config")
GITIGNOREFILE = os.path.join(PRJ_ROOT, ".gitignore")

########NEW FILE########
__FILENAME__ = git
#!/usr/bin/env python2
# coding=utf-8

"""
git support library
"""

import sys
import re
from gitver.termcolors import term

# check for the sh package
try:
    import sh
    from sh import ErrorReturnCode, CommandNotFound
except ImportError:
    term.err("A dependency is missing, please install the \"sh\" package and "
             "run gitver again.")
    sys.exit(1)

hash_matcher = r".*-g([a-fA-F0-9]+)"
tag_matcher = r"v{0,1}(?P<maj>\d+)\.(?P<min>\d+)\.(?P<patch>\d+)" \
              r"(?:\.(?P<revision>\d+))?[^-]*(?:-(?P<prmeta>[0-9A-Za-z-.]*))?"


def __git_raw(*args):
    """
    @return sh.RunningCommand
    Proxies the specified git command+args and returns it
    """
    return sh.git(args)


def __git(*args):
    """
    Proxies the specified git command+args and returns a cleaned up version
    of the stdout buffer.
    """
    return __git_raw(*args).stdout.replace('\n', '')


def git_version():
    try:
        ver = __git('--version')
    except (CommandNotFound, ErrorReturnCode):
        return ''
    return ver


def project_root():
    try:
        root = __git('rev-parse', '--show-toplevel')
    except ErrorReturnCode:
        return ''
    return root


def count_tag_to_head(tag):
    try:
        c = __git('rev-list', tag + "..HEAD", '--count')
        return int(c)
    except ErrorReturnCode:
        return False


def get_build_id():
    try:
        full_build_id = str(__git('rev-parse', 'HEAD'))
    except ErrorReturnCode:
        return False
    return full_build_id


def last_tag():
    try:
        tag = __git('describe', '--abbrev=0')
    except ErrorReturnCode:
        return False

    return tag


def data_from_tag(tag):
    try:
        data = re.match(tag_matcher, tag).groupdict()
        if len(data) < 3:
            raise AttributeError
    except AttributeError:
        return None
    return data


def min_hash_length():
    """
    Determines the minimum length of an hash string for this repository
    to uniquely describe a commit.
    gitver's minimum length is 7 characters, to avoid frequent hash string
    length variations in fast-growing projects.
    """
    try:
        out = __git_raw('rev-list', '--all', '--abbrev=0',
                        '--abbrev-commit').stdout
    except ErrorReturnCode:
        return 0

    min_accepted = 7

    # build a set of commit hash lengths
    commits = {
        len(commit) for commit in out.split('\n') if len(commit) >= min_accepted
    }

    if len(commits) > 0:
        # pick the max
        return max(commits)

    return min_accepted


def get_repo_info():
    """
    Retrieves raw repository information and returns it for further processing
    """
    hashlen = min_hash_length()
    if not hashlen:
        term.err("Couldn't compute the minimum hash string length")
        sys.exit(1)

    full_build_id = get_build_id()
    if not full_build_id:
        term.err("Couldn't retrieve build id information")
        sys.exit(1)

    tag = last_tag()
    if not tag:
        term.err("Couldn't retrieve the latest tag")
        sys.exit(1)

    data = data_from_tag(tag)
    if data is None:
        term.err("Couldn't retrieve version information from tag \"" + tag +
                 "\".\ngitver expects tags to be in the format "
                 "[v]X.Y.Z[.REVISION][-PRE-RELEASE-METADATA]")
        sys.exit(1)

    vcount = count_tag_to_head(tag)

    return {'maj': data['maj'],
            'min': data['min'],
            'patch': data['patch'],
            'rev': data['revision'],
            'pr': data['prmeta'],
            'count': vcount,
            'full-build-id': full_build_id,
            'build-id': full_build_id[:hashlen],
            'last-tag': tag
    }

########NEW FILE########
__FILENAME__ = sanity
#!/usr/bin/env python2
# coding=utf-8

"""
Implements various sanity checks
"""

import os
import sys
from gitver.termcolors import term, bold
from gitver.defines import PRJ_ROOT, CFGDIR, CFGDIRNAME, GITIGNOREFILE


def check_project_root():
    # tries to determine the project's root directory
    if len(PRJ_ROOT) == 0:
        term.err("Couldn't determine your project's root directory, is this "
                 "a valid git repository?")
        sys.exit(1)


def check_config_dir():
    # checks if configuration directory exists
    if not os.path.exists(CFGDIR):
        term.err("Please run " + bold("gitver init") + " first.")
        sys.exit(1)


def check_gitignore():
    # checks .gitignore for .gitver inclusion
    try:
        gifile = os.path.join(GITIGNOREFILE)
        with open(gifile, 'r') as f:
            if CFGDIRNAME in f.read():
                return True
    except IOError:
        pass

    return False

########NEW FILE########
__FILENAME__ = storage
#!/usr/bin/env python2
# coding=utf-8

"""
Represents one of the simplest form of key-value storage to file
"""

import pickle


class KVStore(object):
    def __init__(self, storage_file):
        self.__file = storage_file
        self.__data = dict()
        self.load()

    def load(self):
        try:
            fp = open(self.__file, 'r')
            self.__data = pickle.load(fp)
            fp.close()
        except IOError:
            pass

    def save(self):
        if self.__data is not None:
            try:
                fp = open(self.__file, 'w')
                pickle.dump(self.__data, fp)
                fp.close()
            except IOError:
                return False

            return True

        return False

    def items(self):
        return self.__data.items()

    def get(self, key):
        if key in self.__data:
            return self.__data[key]
        return False

    def set(self, key, value):
        self.__data[key] = value
        return self

    def rm(self, key):
        if key in self.__data:
            del self.__data[key]
        return self

    def has(self, key):
        return key in self.__data

    def empty(self):
        return self.count() == 0

    def count(self):
        return len(self.__data)

########NEW FILE########
__FILENAME__ = termcolors
#!/usr/bin/env python2
# coding=utf-8

"""
Provides stdout/stderr output, with optional color output, if supported
"""

import sys
import os


# Color support via ansicolors package
try:
    from colors import color

    def color_tag(text):
        return color(text, fg=231, bg=239, style='bold')

    def color_next(text):
        return color(text, fg=231, bg=28, style='bold')

    def color_version(text):
        return color(text, fg=255, bg=25, style='bold')

    def color_promoted(text):
        return color(text, fg=255, bg=33, style='bold')

    def color_warn(text):
        return color(text, fg=214, style='bold')

    def color_err(text):
        return color(text, fg=196, style='bold')

    def bold(text):
        return color(text, style='bold')

except ImportError:

    def color_tag(text):
        return text

    def color_next(text):
        return text

    def color_version(text):
        return text

    def color_warn(text):
        return text

    def color_err(text):
        return text

    def bold(text):
        return text


class Terminal(object):
    """
    Provides a way to output text to the stdout or stderr, optionally
    with colors.
    """
    def __init__(self):
        self.__use_colors = False
        self.is_quiet = False
        self.is_quiet_err = False

    def enable_colors(self, use_colors):
        self.__use_colors = use_colors

    def set_quiet_flags(self, quiet_stdout, quiet_stderr):
        self.is_quiet = quiet_stdout
        self.is_quiet_err = quiet_stderr

    def __emit(self, text, stream, func=None):
        if self.__use_colors and func is not None:
            stream.write(func(text + os.linesep))
        else:
            stream.write(text + os.linesep)

    def __decorate(self, text, func):
        if self.__use_colors:
            return func(text)
        else:
            return text

    def err(self, text):
        """
        Outputs an ERROR message to the stderr
        """
        if not self.is_quiet_err:
            self.__emit("ERROR: " + text, sys.stderr, color_err)

    def warn(self, text):
        """
        Outputs a WARNING message to the stderr
        """
        if not self.is_quiet_err:
            self.__emit("WARNING: " + text, sys.stderr, color_warn)

    def info(self, text):
        """
        Outputs an INFORMATIVE message to the stderr
        """
        if not self.is_quiet_err:
            self.__emit(text, sys.stderr, None)

    def out(self, text):
        """
        Outputs a message to the stdout
        """
        if not self.is_quiet:
            self.__emit(text, sys.stdout)

    def tag(self, text):
        """
        Decorate the specified text with the TAG color class
        """
        return self.__decorate(text, color_tag)

    def next(self, text):
        """
        Decorate the specified text with the NEXT color class
        """
        return self.__decorate(text, color_next)

    def ver(self, text):
        """
        Decorate the specified text with the VERSION color class
        """
        return self.__decorate(text, color_version)

    def prom(self, text):
        """
        Decorate the specified text with the PROMOTED color class
        """
        return self.__decorate(text, color_promoted)

term = Terminal()

########NEW FILE########
__FILENAME__ = version
#!/usr/bin/env python2
# coding=utf-8

"""
Provides gitver's version by dynamically loading the optional _version module.
"""

gitver_version = None
gitver_buildid = None
gitver_pypi = None

try:
    import _version as v
    gitver_version = v.gitver_version
    gitver_buildid = v.gitver_buildid
    gitver_pypi = v.gitver_pypi
except ImportError:
    pass

########NEW FILE########
