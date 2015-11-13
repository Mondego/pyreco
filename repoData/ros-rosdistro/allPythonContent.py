__FILENAME__ = distro_to_rosinstall
#! /usr/bin/env python

import os
import sys
import yaml
from rospkg.distro import load_distro, distro_uri

def translate(distro, translate_dir):
    d = load_distro(distro_uri(distro))
    repo_list = d.get_stacks(True)
    for name, item in repo_list.iteritems():
        if item.vcs_config.type == 'svn':
            rosinstall = [{item.vcs_config.type: \
                           {'local-name': item.name,
                            'uri': item.vcs_config.anon_dev}}]
        else:
            rosinstall = [{item.vcs_config.type: \
                           {'local-name': item.name,
                            'uri': item.vcs_config.anon_repo_uri,
                            'version': item.vcs_config.dev_branch}}]

        path = os.path.join(translate_dir, "%s.rosinstall" % item.name)
        with open(path, 'w+') as f:
            print "writing to %s" % path
            yaml.safe_dump(rosinstall, f, default_flow_style=False)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print "Use %s distro install_folder" % sys.argv[0]
        sys.exit()
    translate(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = add_devel_repo
#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys
import yaml

from sort_yaml import sort_yaml_data


def add_devel_repository(yaml_file, name, vcs_type, url, version=None):
    data = yaml.load(open(yaml_file, 'r'))
    if data['type'] == 'gbp':
        add_devel_repository_fuerte(yaml_file, data, name, vcs_type, url, version)
        return

    if data['type'] != 'source':
        raise RuntimeError('The passed .yaml file is neither of type "source" nor "gbp"')

    if name in data['repositories']:
        raise RuntimeError('Repository with name "%s" is already in the .yaml file' % name)

    data['repositories'][name] = {
        'type': vcs_type,
        'url': url,
        'version': version,
    }
    try:
        from rosdistro.verify import _to_yaml, _yaml_header_lines
    except ImportError as e:
        raise ImportError(str(e) + ' - you need to install the latest version of python-rosdistro.')
    data = _to_yaml(data)
    data = '\n'.join(_yaml_header_lines('source')) + '\n' + data
    with open(yaml_file, 'w') as f:
        f.write(data)


def add_devel_repository_fuerte(yaml_file, data, name, vcs_type, url, version):
    if data['type'] != 'devel':
        raise RuntimeError('The passed .yaml file is not of type "devel"')
    if name in data['repositories']:
        raise RuntimeError('Repository with name "%s" is already in the .yaml file' % name)
    values = {
        'type': vcs_type,
        'url': url,
    }
    if version is None and vcs_type != 'svn':
        raise RuntimeError('All repository types except SVN require a version attribute')
    if version is not None:
        if vcs_type == 'svn':
            raise RuntimeError('SVN repository must not have a version attribute but must contain the version in the URL')
    values['version'] = version
    data['repositories'][name] = values
    sort_yaml_data(data)
    yaml.dump(data, file(yaml_file, 'w'), default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Insert a repository into the .yaml file.')
    parser.add_argument('yaml_file', help='The yaml file to update')
    parser.add_argument('name', help='The unique name of the repo')
    parser.add_argument('type', help='The type of the repository (i.e. "git", "hg", "svn")')
    parser.add_argument('url', help='The url of the repository')
    parser.add_argument('version', nargs='?', help='The version')
    args = parser.parse_args()

    try:
        add_devel_repository(args.yaml_file, args.name, args.type, args.url, args.version)
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)

########NEW FILE########
__FILENAME__ = add_release_repo
#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys
import yaml

from sort_yaml import sort_yaml_data


def add_release_repository(yaml_file, name, url, version):
    data = yaml.load(open(yaml_file, 'r'))
    if data['type'] == 'gbp':
        add_release_repository_fuerte(yaml_file, data, name, url, version)
        return

    raise RuntimeError('The passed .yaml file is not of type "gbp" and it is not supported for Groovy or newer')


def add_release_repository_fuerte(yaml_file, data, name, url, version):
    if name in data['repositories']:
        raise RuntimeError('Repository with name "%s" is already in the .yaml file' % name)
    data['repositories'][name] = {
        'url': url,
        'version': version,
    }
    sort_yaml_data(data)
    yaml.dump(data, file(yaml_file, 'w'), default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Insert a git-buildpackage repository into the .yaml file.')
    parser.add_argument('yaml_file', help='The yaml file to update')
    parser.add_argument('name', help='The unique name of the repo')
    parser.add_argument('url', help='The url of the GBP repository')
    parser.add_argument('version', help='The version')
    args = parser.parse_args()

    try:
        add_release_repository(args.yaml_file, args.name, args.url, args.version)
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)

########NEW FILE########
__FILENAME__ = check_rosdep
#!/usr/bin/env python
import re
import yaml
import argparse
import sys

indent_atom = '  '

# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (eg. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#
# With modifications
#           (C) 2013 Paul M <pmathieu@willowgarage.com>

codeCodes = {
    'black':    '0;30',     'bright gray':  '0;37',
    'blue':     '0;34',     'white':        '1;37',
    'green':    '0;32',     'bright blue':  '1;34',
    'cyan':     '0;36',     'bright green': '1;32',
    'red':      '0;31',     'bright cyan':  '1;36',
    'purple':   '0;35',     'bright red':   '1;31',
    'yellow':   '0;33',     'bright purple':'1;35',
    'dark gray':'1;30',     'bright yellow':'1;33',
    'normal':   '0'
}

def printc(text, color):
    """Print in color."""
    if sys.stdout.isatty():
        print "\033["+codeCodes[color]+"m"+text+"\033[0m"
    else:
        print text

def print_test(msg):
    printc(msg, 'yellow')

def print_err(msg):
    printc('  ERR: ' + msg, 'red')

def no_trailing_spaces(buf):
    clean = True
    for i, l in enumerate(buf.split('\n')):
        if re.search(r' $', l) is not None:
            print_err("trailing space line %u" % (i+1))
            clean = False
    return clean

def generic_parser(buf, cb):
    ilen = len(indent_atom)
    stringblock = False
    strlvl = 0
    lvl = 0
    clean = True

    for i, l in enumerate(buf.split('\n')):
        if l == '':
            continue
        if re.search(r'^\s*#', l) is not None:
            continue
        try:
            s = re.search(r'(?!' + indent_atom + ')(\w|\?)', l).start()
        except:
            print_err("line %u: %s" % (i, l))
            raise
        if stringblock:
            if int(s / ilen) > strlvl:
                continue
            stringblock = False
        lvl = s / ilen
        opts = {'lvl': lvl, 's': s}
        if not cb(i, l, opts):
            clean = False
        if re.search(r'\|$|\?$|^\s*\?', l) is not None:
            stringblock = True
            strlvl = lvl
    return clean


def correct_indent(buf):
    ilen = len(indent_atom)
    def fun(i, l, o):
        s = o['s']
        olvl = fun.lvl
        lvl = o['lvl']
        fun.lvl = lvl
        if s % ilen > 0:
            print_err("invalid indentation level line %u: %u" % (i+1, s))
            return False
        if lvl > olvl + 1:
            print_err("too much indentation line %u" % (i+1))
            return False
        return True
    fun.lvl = 0
    return generic_parser(buf, fun)

def check_brackets(buf):
    excepts = ['uri', 'md5sum']
    def fun(i, l, o):
        m = re.match(r'^(?:' + indent_atom + r')*([^:]*):\s*(\w.*)$', l)
        if m is not None and m.groups()[0] not in excepts:
            print_err("list not in square brackets line %u" % (i+1))
            return False
        return True
    return generic_parser(buf, fun)

def check_order(buf):
    def fun(i, l, o):
        lvl = o['lvl']
        st = fun.namestack
        while len(st) > lvl + 1:
            st.pop()
        if len(st) < lvl + 1:
            st.append('')
        if re.search(r'^\s*\?', l) is not None:
            return True
        m = re.match(r'^(?:' + indent_atom + r')*([^:]*):.*$', l)
        prev = st[lvl]
        try:
            item = m.groups()[0]
        except:
            print('woops line %d' % i)
            raise
        st[lvl] = item
        if item < prev:
            print_err("list out of order line %u" % (i+1))
            return False
        return True
    fun.namestack = ['']
    return generic_parser(buf, fun)


def main(fname):
    with open(fname) as f:
        buf = f.read()

    def my_assert(val):
        if not val:
            my_assert.clean = False
    my_assert.clean = True

    # here be tests.
    ydict = None
    try:
        ydict = yaml.load(buf)
    except Exception:
        pass
    if ydict != {}:
        print_test("checking for trailing spaces...")
        my_assert(no_trailing_spaces(buf))
        print_test("checking for incorrect indentation...")
        my_assert(correct_indent(buf))
        print_test("checking for non-bracket package lists...")
        my_assert(check_brackets(buf))
        print_test("checking for item order...")
        my_assert(check_order(buf))
        print_test("building yaml dict...")
    else:
        print_test("skipping file with empty dict contents...")
    try:
        ydict = yaml.load(buf)

        # ensure that values don't contain whitespaces
        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(key)
                    walk(value)
            if isinstance(node, list):
                for value in node:
                    walk(value)
            if isinstance(node, str) and re.search(r'\s', node):
                    print_err("value '%s' must not contain whitespaces" % node)
                    my_assert(False)
        walk(ydict)

    except Exception as e:
        print_err("could not build the dict: %s" % (str(e)))
        my_assert(False)

    if not my_assert.clean:
        printc("there were errors, please correct the file", 'bright red')
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether yaml syntax corresponds to ROS rules')
    parser.add_argument('infile', help='input rosdep YAML file')
    args = parser.parse_args()

    if not main(args.infile):
        sys.exit(1)



########NEW FILE########
__FILENAME__ = check_rosdistro
#!/usr/bin/env python
import re
import yaml
import argparse
import sys

indent_atom = '  '

# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (eg. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#
# With modifications
#           (C) 2013 Paul M <pmathieu@willowgarage.com>

codeCodes = {
    'black':    '0;30',     'bright gray':  '0;37',
    'blue':     '0;34',     'white':        '1;37',
    'green':    '0;32',     'bright blue':  '1;34',
    'cyan':     '0;36',     'bright green': '1;32',
    'red':      '0;31',     'bright cyan':  '1;36',
    'purple':   '0;35',     'bright red':   '1;31',
    'yellow':   '0;33',     'bright purple':'1;35',
    'dark gray':'1;30',     'bright yellow':'1;33',
    'normal':   '0'
}

def printc(text, color):
    """Print in color."""
    if sys.stdout.isatty():
        print "\033["+codeCodes[color]+"m"+text+"\033[0m"
    else:
        print text

def print_test(msg):
    printc(msg, 'yellow')

def print_err(msg):
    printc('  ERR: ' + msg, 'red')

def no_trailing_spaces(buf):
    clean = True
    for i, l in enumerate(buf.split('\n')):
        if re.search(r' $', l) is not None:
            print_err("trailing space line %u" % (i+1))
            clean = False
    return clean

def generic_parser(buf, cb):
    ilen = len(indent_atom)
    stringblock = False
    strlvl = 0
    lvl = 0
    clean = True

    for i, l in enumerate(buf.split('\n')):
        if l == '':
            continue
        if re.search(r'^\s*#', l) is not None:
            continue
        try:
            s = re.search(r'(?!' + indent_atom + ')(\w|\?)', l).start()
        except:
            print_err("line %u: %s" % (i, l))
            raise
        if stringblock:
            if int(s / ilen) > strlvl:
                continue
            stringblock = False
        lvl = s / ilen
        opts = {'lvl': lvl, 's': s}
        if not cb(i, l, opts):
            clean = False
        if re.search(r'\|$|\?$|^\s*\?', l) is not None:
            stringblock = True
            strlvl = lvl
    return clean


def correct_indent(buf):
    ilen = len(indent_atom)
    def fun(i, l, o):
        s = o['s']
        olvl = fun.lvl
        lvl = o['lvl']
        fun.lvl = lvl
        if s % ilen > 0:
            print_err("invalid indentation level line %u: %u" % (i+1, s))
            return False
        if lvl > olvl + 1:
            print_err("too much indentation line %u" % (i+1))
            return False
        return True
    fun.lvl = 0
    return generic_parser(buf, fun)

def check_brackets(buf):
    excepts = ['uri', 'md5sum']
    def fun(i, l, o):
        m = re.match(r'^(?:' + indent_atom + r')*([^:]*):\s*(\w.*)$', l)
        if m is not None and m.groups()[0] not in excepts:
            print_err("list not in square brackets line %u" % (i+1))
            return False
        return True
    return generic_parser(buf, fun)

def check_order(buf):
    def fun(i, l, o):
        lvl = o['lvl']
        st = fun.namestack
        while len(st) > lvl + 1:
            st.pop()
        if len(st) < lvl + 1:
            st.append('')
        if re.search(r'^\s*\?', l) is not None:
            return True
        m = re.match(r'^(?:' + indent_atom + r')*([^:]*):.*$', l)
        prev = st[lvl]
        try:
            item = m.groups()[0]
        except:
            print('woops line %d' % i)
            raise
        st[lvl] = item
        if item < prev:
            print_err("list out of order line %u" % (i+1))
            return False
        return True
    fun.namestack = ['']
    return generic_parser(buf, fun)


def main(fname):
    with open(fname) as f:
        buf = f.read()

    def my_assert(val):
        if not val:
            my_assert.clean = False
    my_assert.clean = True

    try:
        ydict = yaml.load(buf)
    except Exception as e:
        print_err("could not build the dict: %s" % (str(e)))
        my_assert(False)

    if 'release-name' not in ydict and isinstance(ydict, dict) and 'fuerte' not in ydict.keys():
        print_err("The file does not contain a 'release-name'. (Only files for Fuerte and older are supported by this script)")
    else:
        print_test("checking for trailing spaces...")
        my_assert(no_trailing_spaces(buf))
        print_test("checking for incorrect indentation...")
        my_assert(correct_indent(buf))
        print_test("checking for item order...")
        my_assert(check_order(buf))
        print_test("building yaml dict...")

    if not my_assert.clean:
        printc("there were errors, please correct the file", 'bright red')
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether yaml syntax corresponds to ROS rules')
    parser.add_argument('infile', help='input rosdep YAML file')
    args = parser.parse_args()

    if not main(args.infile):
        sys.exit(1)



########NEW FILE########
__FILENAME__ = check_rosdistro_repos
#!/usr/bin/env python

from __future__ import print_function

import argparse
import subprocess
import sys

from rosdistro import get_distribution_file, get_index, get_index_url


def check_git_repo(url, version):
    cmd = ['git', 'ls-remote', url]
    try:
        output = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid git repo url')

    if version:
        for line in output.splitlines():
            if line.endswith('/%s' % version):
                return
        raise RuntimeError('version not found')


def check_hg_repo(url, version):
    cmd = ['hg', 'identify', url]
    if version:
        cmd.extend(['-r', version])
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if not version:
            raise RuntimeError('not a valid hg repo url')
        cmd = ['hg', 'identify', url]
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('not a valid hg repo url')
        raise RuntimeError('version not found')


def check_svn_repo(url, version):
    cmd = ['svn', '--non-interactive', '--trust-server-cert', 'info', url]
    if version:
        cmd.extend(['-r', version])
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid svn repo url')


def main(repo_type, rosdistro_name):
    index = get_index(get_index_url())
    try:
        distribution_file = get_distribution_file(index, rosdistro_name)
    except RuntimeError as e:
        print("Could not load distribution file for distro '%s': %s" % (rosdistro_name, e), file=sys.stderr)
        return False

    for repo_name in sorted(distribution_file.repositories.keys()):
        sys.stdout.write('.')
        sys.stdout.flush()
        repo = distribution_file.repositories[repo_name]
        if repo_type == 'doc':
            repo = repo.doc_repository
        if repo_type == 'source':
            repo = repo.source_repository
        if not repo:
            continue
        try:
            if (repo.type == 'git'):
                check_git_repo(repo.url, repo.version)
            elif (repo.type == 'hg'):
                check_hg_repo(repo.url, repo.version)
            elif (repo.type == 'svn'):
                check_svn_repo(repo.url, repo.version)
            else:
                print()
                print("Unknown type '%s' for repository '%s'" % (repo.type, repo.name), file=sys.stderr)
        except RuntimeError as e:
            print()
            print("Could not fetch repository '%s': %s (%s) [%s]" % (repo.name, repo.url, repo.version, e), file=sys.stderr)
    print()

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether the referenced branches for the doc/source repositories exist')
    parser.add_argument('repo_type', choices=['doc', 'source'], help='The repository type')
    parser.add_argument('rosdistro_name', help='The ROS distro name')
    args = parser.parse_args()

    if not main(args.repo_type, args.rosdistro_name):
        sys.exit(1)

########NEW FILE########
__FILENAME__ = check_rosdistro_urls
#!/usr/bin/env python

from __future__ import print_function

import argparse
import sys

from rosdistro import get_distribution_file, get_index


def main(index_url, rosdistro_name):
    index = get_index(index_url)
    try:
        distribution_file = get_distribution_file(index, rosdistro_name)
    except RuntimeError as e:
        print("Could not load distribution file for distro '%s': %s" % (rosdistro_name, e), file=sys.stderr)
        return False

    success = True
    for repo_name in sorted(distribution_file.repositories.keys()):
        sys.stdout.write('.')
        sys.stdout.flush()
        repo = distribution_file.repositories[repo_name]
        repos = [repo.release_repository, repo.source_repository, repo.doc_repository]
        for repo in [r for r in repos if r]:
            if repo.url.startswith('file://'):
                print()
                print("Repository '%s' with url '%s' must not be a local 'file://' url" % (repo_name, repo.url), file=sys.stderr)
                success = False
            if repo.type == 'git':
                prefixes = ['http://github.com/', 'git@github.com:']
                for prefix in prefixes:
                    if repo.url.startswith(prefix):
                        print()
                        print("Repository '%s' with url '%s' must use 'https://github.com/%s' instead" % (repo_name, repo.url, repo.url[len(prefix):]), file=sys.stderr)
                        success = False
                for prefix in prefixes + ['https://github.com/']:
                    if repo.url.startswith(prefix) and not repo.url.endswith('.git'):
                        print()
                        print("Repository '%s' with url '%s' should end with `.git` but does not." % (repo_name, repo.url))
                        success = False
    print()

    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether the referenced URLs have the expected pattern for known hosts')
    parser.add_argument('index_url', help='The url of the index.yaml file')
    parser.add_argument('rosdistro_name', help='The ROS distro name')
    args = parser.parse_args()

    if not main(args.index_url, args.rosdistro_name):
        sys.exit(1)

########NEW FILE########
__FILENAME__ = clean_rosdep_yaml
#!/usr/bin/env python

import yaml
import argparse
import re

dont_bracket = ['uri', 'md5sum']

def paddify(s, l):
    a = s.split('\n')
    buf = ''
    pad = '  ' * l
    for i, r in enumerate(a[:-1]):
        buf += "%s%s\n" % (pad, r)
    return buf

def quote_if_necessary(s):
    if type(s) is list:
        return [quote_if_necessary(a) for a in s]
    return re.search('{a: (.*)}\n', yaml.dump({'a': s})).group(1)

def prn(n, nm, lvl):
    pad = '  ' * lvl
    if isinstance(n, list):
        return "%s%s: [%s]\n" % (pad, nm, ', '.join(quote_if_necessary(n)))
    elif n is None:
        return "%s%s:\n" % (pad, nm)
    elif isinstance(n, str):
        if len(n.split('\n')) > 1:
            return "%s%s: |\n%s" % (pad, nm, paddify(n, lvl+1))
        else:
            if nm in dont_bracket:
                return "%s%s: %s\n" % (pad, nm, quote_if_necessary(n))
            return "%s%s: [%s]\n" % (pad, nm, ', '.join(quote_if_necessary(n.split())))
    buf = "%s%s:\n" % (pad, nm)
    for a in sorted(n.keys()):
        buf += prn(n[a], a, lvl+1)
    return buf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cleans a rosdep YAML file to a correct format')
    parser.add_argument('infile', help='input rosdep YAML file')
    parser.add_argument('outfile', help='output YAML file to be written')
    args = parser.parse_args()

    with open(args.infile) as f:
        iny = yaml.load(f.read())

    buf = ''
    for a in sorted(iny):
        buf += prn(iny[a], a, 0)

    with open(args.outfile, 'w') as f:
        f.write(buf)

########NEW FILE########
__FILENAME__ = sort_yaml
#!/usr/bin/env python

from __future__ import print_function

import argparse
import sys
import yaml


def sort_yaml(yaml_file):
    data = yaml.load(open(yaml_file, 'r'))
    if 'version' in data:
        print('This script does not support the new rosdistro yaml files', file=sys.stderr)
        sys.exit(1)
    sort_yaml_data(data)
    yaml.dump(data, file(yaml_file, 'w'), default_flow_style=False)


def sort_yaml_data(data):
    # sort lists
    if isinstance(data, list):
        data.sort()
    # recurse into each value of a dict
    elif isinstance(data, dict):
        for k in data:
            sort_yaml_data(data[k])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sort the .yaml file in place.')
    parser.add_argument('yaml_file', help='The .yaml file to update')
    args = parser.parse_args()
    sort_yaml(args.yaml_file)

########NEW FILE########
__FILENAME__ = yaml2rosinstall
#!/usr/bin/env python

from __future__ import print_function
import argparse
import os
import sys
import yaml


def convert_yaml_to_rosinstall(yaml_file, rosinstall_file):
    data = yaml.load(open(yaml_file, 'r'))
    data = convert_yaml_data_to_rosinstall_data(data)
    yaml.dump(data, file(rosinstall_file, 'w'), default_flow_style=False)


def convert_yaml_data_to_rosinstall_data(data):
    rosinstall_data = []
    for name in sorted(data['repositories'].keys()):
        values = data['repositories'][name]
        repo = {}
        repo['local-name'] = name
        repo['uri'] = values['url']
        if 'version' in values:
            repo['version'] = values['version']
        # fallback type is git for gbp repositories
        vcs_type = values['type'] if 'type' in values else 'git'
        rosinstall_data.append({vcs_type: repo})
    return rosinstall_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert a .yaml file into a .rosinstall file.')
    parser.add_argument('yaml_file', help='The .yaml file to convert')
    parser.add_argument('rosinstall_file', nargs='?', help='The generated .rosinstall file (default: same name as .yaml file except extension)')
    args = parser.parse_args()

    if args.rosinstall_file is None:
        path_without_ext, _ = os.path.splitext(args.yaml_file)
        args.rosinstall_file = path_without_ext + '.rosinstall'

    try:
        convert_yaml_to_rosinstall(args.yaml_file, args.rosinstall_file)
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)

########NEW FILE########
__FILENAME__ = rosdep_formatting_test
#!/usr/bin/env python

import os

from scripts.check_rosdep import main as check_rosdep


def test():
    files = os.listdir('rosdep')

    print("""
Running 'scripts/check_rosdep.py' on all *.yaml in the rosdep directory.
If this fails you can run 'scripts/clean_rosdep.py' to help cleanup.
""")

    for f in files:
        fname = os.path.join('rosdep', f)
        if not f.endswith('.yaml'):
            print("Skipping rosdep check of file %s" % fname)
            continue
        print("Checking rosdep file %s" % fname)
        assert check_rosdep(fname)

########NEW FILE########
__FILENAME__ = rosdistro_check_urls_test
#!/usr/bin/env python

import os

from rosdistro import get_index
from scripts.check_rosdistro_urls import main as check_rosdistro_urls

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_rosdistro_urls():
    index_url = 'file://' + FILES_DIR + '/index.yaml'
    index = get_index(index_url)
    failed_distros = []
    for distro_name in index.distributions.keys():
        print("""
Checking if distribution.yaml contains valid urls for known hosting services.
If this fails you can run 'scripts/check_rosdistro_urls.py file://`pwd`/%s %s' to perform the same check locally.
""" % ('index.yaml', distro_name))
        if not check_rosdistro_urls(index_url, distro_name):
            failed_distros.append(distro_name)
    assert not failed_distros, "There were problems with urls in the 'distribution.yaml' file for these distros: %s" % failed_distros

########NEW FILE########
__FILENAME__ = rosdistro_formatting_test
#!/usr/bin/env python

import os

from scripts.check_rosdistro import main as check_rosdist


def test():
    files = os.listdir('releases')

    print("""
Running 'scripts/check_rosdistro.py' on all *.yaml in the releases directory.
If this fails you can run 'scripts/check_rosdistro.py' to perform the same check locally.
""")

    for f in files:
        fname = os.path.join('releases', f)
        if not f.endswith('.yaml'):
            print("Skipping rosdistro check of file %s" % fname)
            continue
        print("Checking rosdistro file %s" % fname)
        assert check_rosdist(fname)

########NEW FILE########
__FILENAME__ = rosdistro_verify_test
import os

from rosdistro.verify import verify_files_identical

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_verify_files_identical():
    print("""
Checking if index.yaml and all referenced files comply to the formatting rules.
If this fails you can run 'rosdistro_reformat index.yaml' to help cleanup.
'rosdistro_reformat' shows the diff between the current files and their expected formatting.
""")

    index_url = 'file://' + FILES_DIR + '/index.yaml'
    assert verify_files_identical(index_url)

########NEW FILE########
__FILENAME__ = test_build_caches
import os

from rosdistro.distribution_cache_generator import generate_distribution_caches

INDEX_YAML = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))


def test_build_caches():
    print("""
Checking if the package.xml files for all packages are fetchable.
If this fails you can run 'rosdistro_build_cache index.yaml' to perform the same check locally.
""")

    generate_distribution_caches(INDEX_YAML)

########NEW FILE########
