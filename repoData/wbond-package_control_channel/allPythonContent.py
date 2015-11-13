__FILENAME__ = test
#!/usr/bin/env python3

"""Tests for the validity of the channel and repository files.

You can run this script directly or with `python -m unittest` from this or the
root directory. For some reason `nosetests` does not pick up the generated tests
even though they are generated at load time.

Arguments:
    --test-repositories
        Also generates tests for all repositories in `channel.json` (the http
        ones).
"""

import os
import re
import json
import sys
import unittest

from collections import OrderedDict
from functools import wraps
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import urljoin

arglist = ['--test-repositories']
# Exctract used arguments form the commandline an strip them for unittest.main
userargs = [arg for arg in sys.argv if arg in arglist]
for arg in userargs:
    if arg in sys.argv:
        sys.argv.remove(arg)


################################################################################
# Utilities


def _open(filepath, *args, **kwargs):
    """Wrapper function that can search one dir above if the desired file
    does not exist.
    """
    if not os.path.exists(filepath):
        filepath = os.path.join("..", filepath)

    return open(filepath, *args, **kwargs)


def generator_class(cls):
    """Class decorator for classes that use test generating methods.

    A class that is decorated with this function will be searched for methods
    starting with "generate_" (similar to "test_") and then run like a nosetest
    generator.
    Note: The generator function must be a classmethod!

    Generate tests using the following statement:
        yield method, (arg1, arg2, arg3)  # ...
    """
    for name in list(cls.__dict__.keys()):
        generator = getattr(cls, name)
        if not name.startswith("generate_") or not callable(generator):
            continue

        if not generator.__class__.__name__ == 'method':
            raise TypeError("Generator methods must be classmethods")

        # Create new methods for each `yield`
        for sub_call in generator():
            method, params = sub_call

            @wraps(method)
            def wrapper(self, method=method, params=params):
                return method(self, *params)

            # Do not attempt to print lists/dicts with printed lenght of 1000 or
            # more, they are not interesting for us (probably the whole file)
            args = []
            for v in params:
                string = repr(v)
                if len(string) > 1000:
                    args.append('...')
                else:
                    args.append(repr(v))

            mname = method.__name__
            if mname.startswith("_test"):
                mname = mname[1:]
            elif not mname.startswith("test_"):
                mname = "test_" + mname

            # Include parameters in attribute name
            name = "%s(%s)" % (mname, ", ".join(args))
            setattr(cls, name, wrapper)

        # Remove the generator afterwards, it did its work
        delattr(cls, name)

    return cls


def get_package_name(data):
    """Gets "name" from a package with a workaround when it's not defined.

    Use the last part of details url for the package's name otherwise since
    packages must define one of these two keys anyway.
    """
    return data.get('name') or data.get('details').rsplit('/', 1)[-1]


################################################################################
# Tests


class TestContainer(object):
    """Contains tests that the generators can easily access (when subclassing).

    Does not contain tests itself, must be used as mixin with unittest.TestCase.
    """

    package_key_types_map = {
        'name': str,
        'details': str,
        'description': str,
        'releases': list,
        'homepage': str,
        'author': str,
        'readme': str,
        'issues': str,
        'donate': str,
        'buy': str,
        'previous_names': list,
        'labels': list
    }

    d_reg = r'''^ (https:// github\.com/ [^/]+/ [^/]+ (/tree/ .+ (?<!/)
                                                      |/tags
                                                      |/)?
                  |https:// bitbucket\.org/ [^/]+/ [^/]+ (/src/ .+ (?<!/)
                                                         |\#tags
                                                         |/)?
                  ) $'''
    # Strip multilines for better debug info on failures
    details_regex = re.compile(' '.join(d_reg.split()), re.X)

    def _test_repository_keys(self, include, data):
        self.assertTrue(2 <= len(data) <= 3, "Unexpected number of keys")
        self.assertIn('schema_version', data)
        self.assertEqual(data['schema_version'], '2.0')

        listkeys = [k for k in ('packages', 'includes') if k in data]
        self.assertGreater(len(listkeys), 0)
        for k in listkeys:
            self.assertIsInstance(data[k], list)

    def _test_repository_package_order(self, include, data):
        m = re.search(r"(?:^|/)(0-9|[a-z])\.json$", include)
        if not m:
            self.fail("Include filename does not match")

        # letter = include[-6]
        letter = m.group(1)
        packages = []
        for pdata in data['packages']:
            pname = get_package_name(pdata)
            if pname in packages:
                self.fail("Package names must be unique: " + pname)
            else:
                packages.append(pname)

            # TODO?: Test for *all* "previous_names"

        # Check if in the correct file
        for package_name in packages:
            if letter == '0-9':
                self.assertTrue(package_name[0].isdigit())
            else:
                self.assertEqual(package_name[0].lower(), letter,
                                 "Package inserted in wrong file")

        # Check package order
        self.assertEqual(packages, sorted(packages, key=str.lower),
                         "Packages must be sorted alphabetically (by name)")

    def _test_repository_indents(self, include, contents):
        for i, line in enumerate(contents.splitlines()):
            self.assertRegex(line, r"^\t*\S",
                             "Indent must be tabs in line %d" % (i + 1))

    def _test_package(self, include, data):
        for k, v in data.items():
            self.assertIn(k, self.package_key_types_map)
            self.assertIsInstance(v, self.package_key_types_map[k], k)

            if k in ('homepage', 'readme', 'issues', 'donate', 'buy'):
                self.assertRegex(v, '^https?://')

            if k == 'details':
                self.assertRegex(v, self.details_regex,
                                 'The details url is badly formatted or '
                                 'invalid')

            # Test for invalid characters (on file systems)
            if k == 'name':
                # Invalid on Windows (and sometimes problematic on UNIX)
                self.assertNotRegex(v, r'[/?<>\\:*|"\x00-\x19]')
                # Invalid on OS X (or more precisely: hidden)
                self.assertFalse(v.startswith('.'))

        if 'details' not in data:
            for key in ('name', 'homepage', 'author', 'releases'):
                self.assertIn(key, data, '%r is required if no "details" URL '
                                         'provided' % key)

    def _test_release(self, package_name, data, main_repo=True):
        # Fail early
        if main_repo:
            self.assertIn('details', data,
                          'A release must have a "details" key if it is in the '
                          'main repository. For custom releases, a custom '
                          'repository.json file must be hosted elsewhere.')
            for req in ('url', 'version', 'date'):
                self.assertNotIn(req, data,
                                 'The version, date and url keys should not be '
                                 'used in the main repository since a pull '
                                 'request would be necessary for every release')

        elif not 'details' in data:
            for req in ('url', 'version', 'date'):
                self.assertIn(req, data,
                              'A release must provide "url", "version" and '
                              '"date" keys if it does not specify "details"')

        else:
            for req in ('url', 'version', 'date'):
                self.assertNotIn(req, data,
                                 'The key "%s" is redundant when "details" is '
                                 'specified' % req)

        self.assertIn('sublime_text', data,
                      'A sublime text version selector is required')

        for k, v in data.items():
            self.assertIn(k, ('details', 'sublime_text', 'platforms',
                              'version', 'date', 'url'))

            if k == 'date':
                self.assertRegex(v, r"^\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d$")

            if k == 'url':
                self.assertRegex(v, r'^https?://')

            if k == 'details':
                self.assertRegex(v, self.details_regex,
                                 'The details url is badly formatted or '
                                 'invalid')

            if k == 'sublime_text':
                self.assertRegex(v, '^(\*|<=?\d{4}|>=?\d{4})$',
                                 'sublime_text must be `*` or of the form '
                                 '<relation><version> '
                                 'where <relation> is one of {<, <=, >, >=} '
                                 'and <version> is a 4 digit number')

            if k == 'platforms':
                self.assertIsInstance(v, (str, list))
                if isinstance(v, str):
                    v = [v]
                for plat in v:
                    self.assertRegex(plat,
                                     r"^\*|(osx|linux|windows)(-x(32|64))?$")

    def _test_error(self, msg, e=None):
        if e:
            if isinstance(e, HTTPError):
                self.fail("%s: %s" % (msg, e))
            else:
                self.fail("%s: %r" % (msg, e))
        else:
            self.fail(msg)

    @classmethod
    def _fail(cls, *args):
        return cls._test_error, args


@generator_class
class ChannelTests(TestContainer, unittest.TestCase):
    maxDiff = None

    with _open('channel.json') as f:
        j = json.load(f)

    def test_channel_keys(self):
        keys = sorted(self.j.keys())
        self.assertEqual(keys, ['repositories', 'schema_version'])

        self.assertEqual(self.j['schema_version'], '2.0')
        self.assertIsInstance(self.j['repositories'], list)

        for repo in self.j['repositories']:
            self.assertIsInstance(repo, str)

    def test_channel_repo_order(self):
        repos = self.j['repositories']
        self.assertEqual(repos, sorted(repos, key=str.lower),
                         "Repositories must be sorted alphabetically")

    @classmethod
    def generate_repository_tests(cls):
        if not "--test-repositories" in userargs:
            # Only generate tests for all repositories (those hosted online)
            # when run with "--test-repositories" parameter.
            return

        for repository in cls.j['repositories']:
            if repository.startswith('.'):
                continue
            if not repository.startswith("http"):
                cls._fail("Unexcpected repository url: %s" % repository)

            yield from cls._include_tests(repository)

    @classmethod
    def _include_tests(cls, url):
        print("fetching %s" % url)

        # Download the repository
        try:
            with urlopen(url) as f:
                source = f.read().decode("utf-8")
        except Exception as e:
            yield cls._fail("Downloading %s failed" % url, e)
            return

        if not source:
            yield cls._fail("%s is empty" % url)
            return

        # Parse the repository
        try:
            data = json.loads(source)
        except Exception as e:
            yield cls._fail("Could not parse %s" % url, e)
            return

        # Check for the schema version first (and generator failures it's
        # badly formatted)
        if 'schema_version' not in data:
            yield cls._fail("No schema_version found in %s" % url)
            return
        schema = float(data['schema_version'])
        if schema not in (1.0, 1.1, 1.2, 2.0):
            yield cls._fail("Unrecognized schema version %s in %s"
                            % (schema, url))
            return
        # Do not generate 1000 failing tests for not yet updated repos
        if schema != 2.0:
            print("schema version %s, skipping" % data['schema_version'])
            return

        # `url` is for output during tests only
        yield cls._test_repository_keys, (url, data)

        if 'packages' in data:
            for package in data['packages']:
                yield cls._test_package, (url, package)

                package_name = get_package_name(package)

                if 'releases' in package:
                    for release in package['releases']:
                        (yield cls._test_release,
                            ("%s (%s)" % (package_name, url),
                             release, False))
        if 'includes' in data:
            for include in data['includes']:
                i_url = urljoin(url, include)
                yield from cls._include_tests(i_url)


@generator_class
class RepositoryTests(TestContainer, unittest.TestCase):
    maxDiff = None

    with _open('repository.json') as f:
        j = json.load(f, object_pairs_hook=OrderedDict)

    def test_repository_keys(self):
        keys = sorted(self.j.keys())
        self.assertEqual(keys, ['includes', 'packages', 'schema_version'])

        self.assertEqual(self.j['schema_version'], '2.0')
        self.assertEqual(self.j['packages'], [])
        self.assertIsInstance(self.j['includes'], list)

        for include in self.j['includes']:
            self.assertIsInstance(include, str)

    @classmethod
    def generate_include_tests(cls):
        for include in cls.j['includes']:
            try:
                with _open(include) as f:
                    contents = f.read()
                data = json.loads(contents, object_pairs_hook=OrderedDict)
            except Exception as e:
                yield cls._test_error, ("Error while reading %r" % include, e)
                continue

            # `include` is for output during tests only
            yield cls._test_repository_indents, (include, contents)
            yield cls._test_repository_keys, (include, data)
            yield cls._test_repository_package_order, (include, data)

            for package in data['packages']:
                yield cls._test_package, (include, package)

                package_name = get_package_name(package)

                if 'releases' in package:
                    for release in package['releases']:
                        (yield cls._test_release,
                            ("%s (%s)" % (package_name, include), release))


################################################################################
# Main


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = migrator
import json
import re
import os
from collections import OrderedDict
from urllib.request import urlopen


# CONFIGURATION FOR MIGRATION PROCESS
old_repositories_json_path = './repositories.json'
new_channel_path = './channel.json'
new_repository_path = './repository.json'

new_repository_url = './repository.json'
new_repository_subfolder_path = './repository/'

client_auth = os.environ['PACKAGE_CONTROL_AUTH']


with open(old_repositories_json_path, encoding='utf-8') as of:
    old_data = json.load(of)
    previous_names = OrderedDict()
    for key, value in old_data['renamed_packages'].items():
        if value not in previous_names:
            previous_names[value] = []
        previous_names[value].append(key)

    names = OrderedDict()
    master_list = OrderedDict()
    repositories = [new_repository_url]
    repositories_from_orgs = []

    repositories_without_orgs = []
    for repository in old_data['repositories']:
        user_match = re.match('https://github.com/([^/]+)$', repository)
        if user_match:
            api_url = 'https://api.github.com/users/%s/repos?per_page=100&%s' % (user_match.group(1), client_auth)
            json_string = urlopen(api_url).read()
            data = json.loads(str(json_string, encoding='utf-8'))
            for repo in data:
                repositories_from_orgs.append(repo['html_url'])
        else:
            repositories_without_orgs.append(repository)

    repositories_to_process = repositories_without_orgs + repositories_from_orgs

    for repository in repositories_to_process:
        repo_match = re.match('https://(github.com|bitbucket.org)/([^/]+)/([^/]+)(?:/tree/([^/]+))?$', repository)

        if repo_match:
            old_name = None
            prev_names = None
            name = repo_match.group(3)
            branch = 'master' if repo_match.group(1) == 'github.com' else 'default'
            if repo_match.group(4):
                branch = repo_match.group(4)

            # BitBucket repos that don't use the branch named "default"
            if name in ['html-crush-switch', 'whocalled', 'jsonlint',
                    'symfonytools-for-sublimetext-2', 'html-compress-and-replace',
                    'sublime-aml', 'quick-rails', 'quickref', 'smartmovetotheeol',
                    'sublime-http-response-headers-snippets', 'sublimesourcetree',
                    'zap-gremlins', 'andrew', 'bootstrap-jade']:
                branch = 'master'

            if name in old_data['package_name_map']:
                old_name = name
                name = old_data['package_name_map'][name]

            # Fixes for bitbucket repos that are using a package_name_map
            if name == 'pythonpep8autoformat':
                old_name = name
                name = 'Python PEP8 Autoformat'
            if name == 'sublimesourcetree':
                old_name = name
                name = 'SourceTree'
            if name == 'sublime-http-response-headers-snippets':
                old_name = name
                name = 'HTTP Response Headers Snippets'
            if name == 'symfonytools-for-sublimetext-2':
                old_name = name
                name = 'SymfonyTools'
            if name == 'statusbarextension':
                old_name = name
                name = 'Status Bar Extension'

            # Skip duplicate sources for packages
            if name in master_list:
                continue

            if name in previous_names:
                prev_names = previous_names[name]

            letter = name[0].lower()
            if letter in [str(num) for num in range(0, 9)]:
                letter = '0-9'

            if letter not in names:
                names[letter] = []

            names[letter].append(name)
            entry = OrderedDict()
            if old_name:
                entry['name'] = name

            # According to the wiki, these are compatible with
            # ST3 without any extra work
            st3_compatiable = [
                'ADBView',
                'AdvancedNewFile',
                'Andrew',
                'AngularJS',
                'AutoBackups',
                'Better CoffeeScript',
                'Case Conversion',
                'CheckBounce',
                'CodeFormatter',
                'ColorPicker',
                'CompleteSharp',
                'ConvertToUTF8',
                'CopyEdit',
                'CriticMarkup',
                'Cscope',
                'CSScomb',
                'CSSFontFamily',
                'CursorRuler',
                'DeleteBlankLines',
                'Djaneiro',
                'DocBlockr',
                'EditorConfig',
                'EditPreferences',
                'ElasticTabstops',
                'Emmet',
                'Expand Selection to Function (JavaScript)',
                'eZ Publish Syntax',
                'File History',
                'Filter Lines',
                'FindKeyConflicts',
                'Floobits',
                'GenerateUUID',
                'GitGutter',
                'google-search',
                'GoSublime',
                'Hex to HSL Color Converter',
                'HighlightWords',
                'Hipster Ipsum',
                'IMESupport',
                'InactivePanes',
                'JavaPropertiesEditor',
                'JavaScript Refactor',
                'JsFormat',
                'JsRun',
                'Laravel Blade Highlighter',
                'LaTeXTools',
                'Less2Css',
                'Local History',
                'MarkAndMove',
                'Marked.app Menu',
                'Mediawiker',
                'memTask',
                'Modific',
                'NaturalSelection',
                'Nettuts+ Fetch',
                'ObjC2RubyMotion',
                'OmniMarkupPreviewer',
                'Open-Include',
                'orgmode',
                'Origami',
                'PackageResourceViewer',
                'Pandown',
                'PersistentRegexHighlight',
                'PgSQL',
                'Phpcs',
                'PHPUnit',
                'PlainTasks',
                'Python PEP8 Autoformat',
                'Rails Latest Migration',
                'Rails Migrations List',
                'Random Text',
                'Ruby Hash Converter',
                'RubyTest',
                'ScalaFormat',
                'Schemr',
                'SelectUntil',
                'SimpleSync',
                'Smart Delete',
                'Solarized Toggle',
                'sublime-github',
                'SublimeAStyleFormatter',
                'SublimeClang',
                'SublimeGDB',
                'SublimeGit',
                'SublimeInsertDatetime',
                'SublimeREPL',
                'SublimeSBT',
                'SublimeTmpl',
                'Surround',
                'SyncedSideBar',
                'Table Editor',
                'Theme - Flatland',
                'Theme - Nil',
                'Theme - Phoenix',
                'Theme - Soda',
                'Themr',
                'TOML',
                'Tradsim',
                'TrailingSpaces',
                'TWiki',
                'URLEncode',
                'View In Browser',
                'Wind',
                'Worksheet',
                'Xdebug',
                'Xdebug Client',
                'Transience',
                'RemoteOpen',
                'Path Tools',
                'WakaTime',
                'AutoSoftWrap',
                'fido',
                'Preference Helper',
                'HTML-CSS-JS Prettify',
                'JSHint Gutter',
                'Vintage Escape',
                'Ruby Pipe Text Processing',
                'Crypto',
                'Preset Command',
                'Sublime​Log',
                'PHP Code Coverage',
                'Status Bar Extension',
                'To Hastebin',
                'Alphpetize',
                'BeautifyRuby',
                'BoundKeys',
                'Evaluate',
                'FindSelected',
                'JSONLint',
                'Pretty JSON',
                'Restructured Text (RST) Snippets',
                'PySide',
                'Diagram',
                'Japanize',
                'SimpleClone',
                'MacTerminal',
                'rsub',
                'Pman',
                'Gist'
            ]

            # These packages have a separate branch for ST3
            st3_with_branch = {
                'BracketHighlighter': 'BH2ST3',
                'BufferScroll': 'st3',
                'ChangeQuotes': 'st3',
                'Ensime': 'ST3',
                'ExportHtml': 'ST3',
                'FavoriteFiles': 'ST3',
                'FileDiffs': 'st3',
                'FuzzyFileNav': 'ST3',
                'Git': 'python3',
                'HexViewer': 'ST3',
                'LineEndings': 'st3',
                'Markdown Preview': 'ST3',
                'Nodejs': 'sublime-text-3',
                'PlistJsonConverter': 'ST3',
                'RegReplace': 'ST3',
                'ScopeHunter': 'ST3',
                'SideBarEnhancements': 'st3',
                'SideBarGit': 'st3',
                'Clipboard Manager': 'st3',
                'SublimeLinter': 'sublime-text-3',
                'Highlight': 'python3',
                'Http Requester': 'st3',
                'SublimePeek': 'ST3',
                'StringUtilities': 'ST3',
                'sublimelint': 'st3',
                'SublimeXiki': 'st3',
                'Tag': 'st3',
                'WordCount': 'st3',
                'Code Runner': 'SublimeText3',
                'Sublimerge': 'sublime-text-3'
            }

            no_python = [
                '3024 Color Scheme',
                '4GL',
                'ABC Notation',
                'ActionScript 3',
                'Additional PHP Snippets',
                'Alternate VIM Navigation',
                'AmpScript Highlighter',
                'AMPScript',
                'AndyPHP',
                'AngelScript',
                'AngularJS (CoffeeScript)',
                'AngularJS Snippets',
                'Ant Buildfile',
                'Ant',
                'APDL (ANSYS) Syntax Highlighting',
                'Aqueducts',
                'AriaTemplates Highlighter',
                'AriaTemplates Snippets',
                'ARM Assembly',
                'Arnold Clark Snippets for Ruby',
                'ASCII Comment Snippets',
                'AsciiDoc',
                'Async Snippets',
                'AVR-ASM-Sublime',
                'Awk',
                'Backbone Baguette',
                'Backbone.js',
                'Backbone.Marionette',
                'Base16 Color Schemes',
                'Behat Features',
                'Behat Snippets',
                'Behat',
                'BEMHTML',
                'BHT-BASIC',
                'Blade Snippets',
                'Blusted Scheme',
                'Boo',
                'Bootstrap 3 Snippets',
                'Boron Color Scheme',
                'Bubububububad and Boneyfied Color Schemes',
                'C# Compile & Run',
                'CakePHP (Native)',
                'CakePHP (tmbundle)',
                'Capybara Snippets',
                'CasperJS',
                'CFeather',
                'Chai Completions',
                'Chaplin.js',
                'Cheetah Syntax Highlighting',
                'Chef',
                'ChordPro',
                'Chuby Ninja Color Scheme',
                'ChucK Syntax',
                'Ciapre Color Scheme',
                'Clay Schubiner Color Schemes',
                'CLIPS Rules',
                'ClosureMyJS',
                'CMake',
                'CMS Made Simple Snippets',
                'Coco R Syntax Highlighting',
                'CodeIgniter 2 ModelController',
                'CodeIgniter Snippets',
                'CodeIgniter Utilities',
                'CoffeeScriptHaml',
                'ColdBox Platform',
                'Color Scheme - Eggplant Parm',
                'Color Scheme - Frontend Delight',
                'Color Scheme - saulhudson',
                'Color Scheme - Sleeplessmind',
                'Color Schemes by carlcalderon',
                'Comment-Snippets',
                'ComputerCraft Package',
                'CoreBuilder',
                'Creole',
                'CSS Media Query Snippets',
                'CSS Snippets',
                'Cube2Media Color Scheme',
                'CUDA C++',
                'CUE Sheet',
                'Dafny',
                'Dark Pastel Color Scheme',
                'Dayle Rees Color Schemes',
                'DBTextWorks',
                'Derby - Bourbon & Neat Autocompletions',
                'DFML (for Dwarf Fortress raws)',
                'Dictionaries',
                'Dimmed Color Scheme',
                'DobDark Color Scheme',
                'Doctrine Snippets',
                'Doctypes',
                'Dogs Colour Scheme',
                'Dotfiles Syntax Highlighting',
                'DotNetNuke Snippets',
                'Drupal Snippets',
                'Drupal',
                'Dust.js',
                'Dylan',
                'eco',
                'ECT',
                'Elixir',
                'Elm Language Support',
                'Ember.js Snippets',
                'Emmet Css Snippets',
                'EmoKid Color Scheme',
                'Enhanced Clojure',
                'Enhanced HTML and CFML',
                'Enlightened Color Scheme',
                'ERB Snippets',
                'Esuna Framework Snippets',
                'Express Color Scheme',
                'ExpressionEngine',
                'F#',
                'Failcoder Color Scheme',
                'FakeImg.pl Image Placeholder Snippet',
                'FarCry',
                'FASM x86',
                'Fat-Free Framework Snippets',
                'fish-shell',
                'FLAC',
                'Flex',
                'Focus',
                'Foundation Snippets',
                'Fountain',
                'FreeMarker',
                'Front End Snippets',
                'Future Funk - Color Scheme',
                'Gaelyk',
                'Gauche',
                'Genesis',
                'Git Config',
                'GMod Lua',
                'Google Closure Library snippets',
                'GoogleTesting',
                'Grandson-of-Obsidian',
                'Grid6',
                'GYP',
                'Haml',
                'Hamlpy',
                'Handlebars',
                'hlsl',
                'Homebrew-formula-syntax',
                'hosts',
                'HTML Compressor',
                'HTML Email Snippets',
                'HTML Mustache',
                'HTML Snippets',
                'HTML5 Doctor CSS Reset snippet',
                'HTML5',
                'HTMLAttributes',
                'IcedCoffeeScript',
                'Idiomatic-CSS-Comments-Snippets',
                'Idoc',
                'ImpactJS',
                'INI',
                'Issues',
                'Jade Snippets',
                'Jade',
                'Java Velocity',
                'JavaScript Console',
                'JavaScript Patterns',
                'JavaScript Snippets',
                'JavaScriptNext - ES6 Syntax',
                'Jinja2',
                'jQuery Mobile Snippets',
                'jQuery Snippets for Coffeescript',
                'jQuery Snippets pack',
                'jQuery',
                'JS Snippets',
                'JsBDD',
                'Julia',
                'knockdown',
                'KnowledgeBase',
                'Kohana 2.x Snippets',
                'Kohana',
                'Koken',
                'Kotlin',
                'KWrite Color Scheme',
                'Language - Up-Goer-5',
                'Laravel 4 Snippets',
                'Laravel Bootstrapper Snippets',
                'Laravel Color Scheme',
                'Laravel Snippets',
                'Lasso',
                'LaTeX Blindtext',
                'LaTeX Track Changes',
                'LaTeX-cwl',
                'Lazy Backbone.js',
                'Ledger syntax highlighting',
                'Legal Document Snippets',
                'LESS',
                'LESS-build',
                'Lift Snippets',
                'lioshi Color Scheme',
                'Liquid',
                'Lithium Snippets',
                'LLVM',
                'Lo-Dash Snippets for CoffeeScript',
                'Logger Snippets',
                'Loom Game Engine',
                'M68k Assembly',
                'Madebyphunky Color Scheme',
                'Mako',
                'Maperitive',
                'Markdown Extended',
                'MasmAssembly',
                'Mason',
                'MelonJS Completions',
                'MinimalFortran',
                'MinkExtension default feature step completions',
                'MIPS Syntax',
                'Mirodark Color Scheme',
                'Missing Palette Commands',
                'Mocha Snippets',
                'MODx Revolution Snippets',
                'Mojolicious',
                'MongoDB - PHP Completions',
                'Mongomapper Snippets',
                'Monokai Blueberry Color Scheme',
                'Monokai Extended',
                'Moscow ML',
                'Mplus',
                'Mreq Color Scheme',
                'MultiLang Color Scheme',
                'Neat Sass Snippets',
                'Nemerle',
                'Neon Theme',
                'NESASM',
                'Nette',
                'nginx',
                'Nimrod',
                'NSIS Autocomplete (Add-ons)',
                'NSIS Autocomplete and Snippets',
                'NSIS',
                'objc .strings syntax language',
                'Oblivion Color Scheme',
                'Oceanic Color Scheme',
                'OpenEdge ABL',
                'OpenGL Shading Language (GLSL)',
                'Papyrus Assembly',
                'PEG.js',
                'Perv - Color Scheme',
                'Phix Color Scheme',
                'PHP Haml',
                'PHP MySQLi connection',
                'PHP-Twig',
                'PHPUnit Completions',
                'PHPUnit Snippets',
                'PKs Color Scheme',
                'Placeholders',
                'Placester',
                'Play 2.0',
                'Pre language syntax highlighting',
                'Processing',
                'Prolog',
                'Puppet',
                'PyroCMS Snippets',
                'Python Auto-Complete',
                'Python Nose Testing Snippets',
                'Racket',
                'Rails Developer Snippets',
                'RailsCasts Colour Scheme',
                'Raydric - Color Scheme',
                'Red Planet Color Scheme',
                'RPM Spec Syntax',
                'RSpec (snippets and syntax)',
                'rspec-snippets',
                'Ruby on Rails snippets',
                'ruby-slim.tmbundle',
                'RubyMotion Autocomplete',
                'RubyMotion Sparrow Framework Autocomplete',
                'Rust',
                'SASS Build',
                'SASS Snippets',
                'Sass',
                'scriptcs',
                'SCSS Snippets',
                'Selenium Snippets',
                'Sencha',
                'Silk Web Toolkit Snippets',
                'SilverStripe',
                'SimpleTesting',
                'Six - Future JavaScript Syntax',
                'SJSON',
                'Slate',
                'SLAX',
                'Smali',
                'Smarty',
                'SML (Standard ML)',
                'Solarized Color Scheme',
                'SourcePawn Syntax Highlighting',
                'SPARC Assembly',
                'Spark',
                'SQF Language',
                'SSH Config',
                'StackMob JS Snippets',
                'Stan',
                'Stylus',
                'SubLilyPond',
                'Sublime-KnockoutJS-Snippets',
                'sublime-MuPAD',
                'SublimeClarion',
                'SublimeDancer',
                'SublimeLove',
                'SublimePeek-R-help',
                'SublimeSL',
                'sublimetext.github.com',
                'Summerfruit Color Scheme',
                'Sundried Color Scheme',
                'Superman Color Scheme',
                'Susy Snippets',
                'Symfony2 Snippets',
                'Syntax Highlighting for Sass',
                'Test Double',
                # Skipped since unsure if themes port well 'Theme - Aqua',
                # Skipped since unsure if themes port well 'Theme - Centurion',
                # Skipped since unsure if themes port well 'Theme - Cobalt2',
                # Skipped since unsure if themes port well 'Theme - Farzher',
                # Skipped since unsure if themes port well 'Theme - Nexus',
                # Skipped since unsure if themes port well 'Theme - Night',
                # Skipped since unsure if themes port well 'Theme - Pseudo OSX',
                # Skipped since unsure if themes port well 'Theme - Reeder',
                # Skipped since unsure if themes port well 'Theme - Refined',
                # Skipped since unsure if themes port well 'Theme - Refresh',
                # Skipped since unsure if themes port well 'Theme - Tech49',
                'Three.js Autocomplete',
                'TideSDK Autocomplete',
                'tipJS Snippets',
                'TJ3-syntax-sublimetext2',
                'Tmux',
                'Todo',
                'TomDoc',
                'Tomorrow Color Schemes',
                'tQuery',
                'TreeTop',
                'Tritium',
                'Tubaina (afc)',
                'Twee',
                'Twig',
                'Twitter Bootstrap ClassNames Completions',
                'Twitter Bootstrap Snippets',
                'TypeScript',
                'Ublime Color Schemes',
                'Underscore.js Snippets',
                'UnindentPreprocessor',
                'Unittest (python)',
                'Unity C# Snippets',
                'Unity3D Build System',
                'Unity3d LeanTween Snippets',
                'Unity3D Shader Highlighter and Snippets',
                'Unity3D Snippets and Completes',
                'Unity3D',
                'UnofficialDocs',
                'Vala',
                'Various Ipsum Snippets',
                'VBScript',
                'VDF',
                'Verilog',
                'VGR-Assistant',
                'Vintage Surround',
                'Vintage-Origami',
                'WebExPert - ColorScheme',
                'WebFocus',
                'Wombat Theme',
                'WooCommerce Autocomplete',
                'Wordpress',
                'World of Warcraft TOC file Syntax',
                'World of Warcraft XML file Syntax',
                'WoW Development',
                'XAML',
                'XpressEngine',
                'XQuery',
                'XSLT Snippets',
                'Yate',
                'Yii Framework Snippets',
                'YUI Compressor',
                'ZenGarden',
                'Zenoss',
                'Zissou Color Schemes',
                'Zurb Foundation 4 Snippets',
                'Mustang Color Scheme',
                'Kimbie Color Scheme'
            ]

            st3_only = [
                'Less Tabs',
                'Toggl Timer',
                'Javatar',
                'WordPress Generate Salts',
                'subDrush',
                'LaTeXing3',
                'Markboard3',
                'Web Inspector 3',
                'PHP Companion',
                'Python IDE',
                'ScalaWorksheet',
                'Vintageous',
                'Strapdown Markdown Preview',
                'StripHTML',
                'MiniPy',
                'Package Bundler',
                'Koan',
                'StickySearch',
                'CodeSearch',
                'Anaconda'
            ]


            compatible_version = '<3000'
            if name in st3_compatiable:
                compatible_version = '*'

            if name in no_python:
                compatible_version = '*'

            if name in st3_only:
                compatible_version = '>=3000'

            entry['details'] = repository

            if repo_match.group(1).lower() == 'github.com':
                release_url = 'https://github.com/%s/%s/tree/%s' % (repo_match.group(2), repo_match.group(3), branch)
            else:
                release_url = 'https://bitbucket.org/%s/%s/src/%s' % (repo_match.group(2), repo_match.group(3), branch)
            entry['releases'] = [
                OrderedDict([
                    ('sublime_text', compatible_version),
                    ('details', release_url)
                ])
            ]

            if name in st3_with_branch:
                if repo_match.group(1).lower() == 'github.com':
                    release_url = 'https://github.com/%s/%s/tree/%s' % (repo_match.group(2), repo_match.group(3), st3_with_branch[name])
                else:
                    release_url = 'https://bitbucket.org/%s/%s/src/%s' % (repo_match.group(2), repo_match.group(3), st3_with_branch[name])
                entry['releases'].append(
                    OrderedDict([
                        ('sublime_text', '>=3000'),
                        ('details', release_url)
                    ])
                )

            if prev_names:
                entry['previous_names'] = prev_names
            master_list[name] = entry

        else:
            repository = repository.replace('http://sublime.wbond.net/', 'https://sublime.wbond.net/')
            repositories.append(repository)


def dump(data, f):
    json.dump(data, f, indent="\t", separators=(',', ': '))


includes = []

if not os.path.exists(new_repository_subfolder_path):
    os.mkdir(new_repository_subfolder_path)

for letter in names:
    include_path = '%s%s.json' % (new_repository_subfolder_path, letter)
    includes.append(include_path)
    sorted_names = sorted(names[letter], key=str.lower)
    sorted_packages = []
    for name in sorted_names:
        sorted_packages.append(master_list[name])
    with open(include_path, 'w', encoding='utf-8') as f:
        data = OrderedDict([
            ('schema_version', '2.0'),
            ('packages', [])
        ])
        data['packages'] = sorted_packages
        dump(data, f)

with open(new_channel_path, 'w', encoding='utf-8') as f:
    data = OrderedDict()
    data['schema_version'] = '2.0'
    data['repositories'] = repositories
    dump(data, f)

with open(new_repository_path, 'w', encoding='utf-8') as f:
    data = OrderedDict()
    data['schema_version'] = '2.0'
    data['packages'] = []
    data['includes'] = sorted(includes)
    dump(data, f)

########NEW FILE########
__FILENAME__ = non_python_packages
import json
import re
import os
from collections import OrderedDict
from urllib.request import urlopen
from urllib.error import HTTPError


st3_compatiable = [
    'ADBView',
    'AdvancedNewFile',
    'Andrew',
    'AngularJS',
    'AutoBackups',
    'Better CoffeeScript',
    'BracketHighlighter',
    'BufferScroll',
    'Case Conversion',
    'ChangeQuotes',
    'CheckBounce',
    'Clipboard Manager',
    'CodeFormatter',
    'ColorPicker',
    'CompleteSharp',
    'ConvertToUTF8',
    'CopyEdit',
    'CriticMarkup',
    'Cscope',
    'CSScomb',
    'CSSFontFamily',
    'CursorRuler',
    'DeleteBlankLines',
    'Djaneiro',
    'DocBlockr',
    'EditorConfig',
    'EditPreferences',
    'ElasticTabstops',
    'Emmet',
    'Ensime',
    'Expand Selection to Function (JavaScript)',
    'ExportHtml',
    'eZ Publish Syntax',
    'FavoriteFiles',
    'File History',
    'FileDiffs',
    'Filter Lines',
    'FindKeyConflicts',
    'Floobits',
    'FuzzyFileNav',
    'GenerateUUID',
    'Git',
    'GitGutter',
    'google-search',
    'GoSublime',
    'Hex to HSL Color Converter',
    'HexViewer',
    'Highlight',
    'HighlightWords',
    'Hipster Ipsum',
    'Http Requester',
    'IMESupport',
    'InactivePanes',
    'JavaPropertiesEditor',
    'JavaScript Refactor',
    'JsFormat',
    'JsRun',
    'Koan',
    'Laravel Blade Highlighter',
    'LaTeXing3',
    'LaTeXTools',
    'Less2Css',
    'LineEndings',
    'Local History',
    'MarkAndMove',
    'Markboard3',
    'Markdown Preview',
    'Marked.app Menu',
    'Mediawiker',
    'memTask',
    'Modific',
    'NaturalSelection',
    'Nettuts+ Fetch',
    'Nodejs',
    'ObjC2RubyMotion',
    'OmniMarkupPreviewer',
    'Open-Include',
    'orgmode',
    'Origami',
    'PackageResourceViewer',
    'Pandown',
    'PersistentRegexHighlight',
    'PgSQL',
    'PHP Companion',
    'Phpcs',
    'PHPUnit',
    'PlainTasks',
    'PlistJsonConverter',
    'Python PEP8 Autoformat',
    'Rails Latest Migration',
    'Rails Migrations List',
    'Random Text',
    'RegReplace',
    'Ruby Hash Converter',
    'RubyTest',
    'ScalaFormat',
    'Schemr',
    'ScopeHunter',
    'SelectUntil',
    'SideBarEnhancements',
    'SideBarGit',
    'SimpleSync',
    'Smart Delete',
    'Solarized Toggle',
    'Strapdown Markdown Preview',
    'StringUtilities',
    'sublime-github',
    'SublimeAStyleFormatter',
    'SublimeClang',
    'SublimeGDB',
    'SublimeGit',
    'SublimeInsertDatetime',
    'sublimelint',
    'SublimeLinter',
    'SublimePeek',
    'SublimeREPL',
    'Sublimerge',
    'SublimeSBT',
    'SublimeTmpl',
    'SublimeXiki',
    'Surround',
    'SyncedSideBar',
    'Table Editor',
    'Tag',
    'Theme - Flatland',
    'Theme - Nil',
    'Theme - Phoenix',
    'Theme - Soda',
    'Themr',
    'TOML',
    'Tradsim',
    'TrailingSpaces',
    'TWiki',
    'URLEncode',
    'View In Browser',
    'Vintageous',
    'Wind',
    'WordCount',
    'Worksheet',
    'Xdebug Client',
    'Xdebug'
]


# CONFIGURATION FOR MIGRATION PROCESS
old_repositories_json_path = './repositories.json'
client_auth = os.environ['PACKAGE_CONTROL_AUTH']
new_repository_url = './repository.json'

requests = 0
five_hundreds = 0

with open(old_repositories_json_path, encoding='utf-8') as of:
    old_data = json.load(of)

    master_list = []
    repositories_from_orgs = []
    repositories_without_orgs = []

    for repository in old_data['repositories']:
        user_match = re.match('https://github.com/([^/]+)$', repository)
        if user_match:
            api_url = 'https://api.github.com/users/%s/repos?per_page=100&%s' % (user_match.group(1), client_auth)
            json_string = urlopen(api_url).read()
            requests += 1
            data = json.loads(str(json_string, encoding='utf-8'))
            for repo in data:
                repositories_from_orgs.append(repo['html_url'])
        else:
            repositories_without_orgs.append(repository)

    repositories_to_process = repositories_without_orgs + repositories_from_orgs

    for repository in repositories_to_process:
        repo_match = re.match('https://(github.com)/([^/]+)/([^/]+)(?:/tree/([^/]+))?$', repository)

        if repo_match:
            old_name = None
            prev_names = None
            user = repo_match.group(2)
            repo = repo_match.group(3)
            name = repo_match.group(3)
            branch = 'master'
            if repo_match.group(4):
                branch = repo_match.group(4)

            if name in old_data['package_name_map']:
                old_name = name
                name = old_data['package_name_map'][name]

            # Skip duplicate sources for packages
            if name in master_list:
                continue

            if name in st3_compatiable:
                continue

            success = False
            while not success:
                try:
                    branch_url = 'https://api.github.com/repos/%s/%s/branches/%s?%s' % (user, repo, branch, client_auth)
                    requests += 1
                    json_string = urlopen(branch_url).read()
                    data = json.loads(str(json_string, encoding='utf-8'))
                    sha = data['commit']['sha']

                    tree_url = 'https://api.github.com/repos/%s/%s/git/trees/%s?%s' % (user, repo, sha, client_auth)
                    requests += 1
                    json_string = urlopen(tree_url).read()
                    data = json.loads(str(json_string, encoding='utf-8'))

                    success = True
                except (HTTPError):
                    five_hundreds += 1
                    print('Requests: %s, 500s: %s' % (requests, five_hundreds))
                    pass

            has_python = False
            for entry in data['tree']:
               if re.search('\.py$', entry['path']) is not None:
                   has_python = True
                   break

            if not has_python:
                print('No python: %s' % name)
            else:
                print('Yes python: %s' % name)

            master_list.append(name)


########NEW FILE########
