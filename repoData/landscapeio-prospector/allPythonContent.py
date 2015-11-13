__FILENAME__ = base

class AdaptorBase(object):

    def adapt_pylint(self, linter):
        pass

    def adapt_mccabe(self, tool):
        pass

    def adapt_pyflakes(self, tool):
        pass

    def adapt_frosted(self, tool):
        pass

    def adapt_pep8(self, style_guide, use_config=True):
        pass

########NEW FILE########
__FILENAME__ = common
from prospector.adaptor.base import AdaptorBase


class CommonAdaptor(AdaptorBase):
    name = 'common-plugin'

    def adapt_pylint(self, linter):
        linter.load_plugin_modules(['pylint_common'])

########NEW FILE########
__FILENAME__ = libraries
from prospector.adaptor.base import AdaptorBase


class DjangoAdaptor(AdaptorBase):
    name = 'django'
    ignore_patterns = (
        '(^|/)migrations(/|$)',
    )

    def adapt_pylint(self, linter):
        linter.load_plugin_modules(['pylint_django'])


class CeleryAdaptor(AdaptorBase):
    name = 'celery'

    def adapt_pylint(self, linter):
        linter.load_plugin_modules(['pylint_celery'])

########NEW FILE########
__FILENAME__ = profile
from prospector.adaptor.base import AdaptorBase
from prospector.profiles.profile import load_profiles
from pylint.utils import UnknownMessage


class ProfileAdaptor(AdaptorBase):

    def __init__(self, profile_names):
        self.profile = load_profiles(profile_names)
        self.name = 'profiles:%s' % ','.join(profile_names)

    def is_tool_enabled(self, tool_name):
        return self.profile.is_tool_enabled(tool_name)

    def adapt_pylint(self, linter):
        disabled = self.profile.get_disabled_messages('pylint')

        for msg_id in disabled:
            try:
                linter.disable(msg_id)

            # pylint: disable=W0704
            except UnknownMessage:
                # If the msg_id doesn't exist in PyLint any more,
                # don't worry about it.
                pass

        options = self.profile.pylint['options']

        for checker in linter.get_checkers():
            if not hasattr(checker, 'options'):
                continue
            for option in checker.options:
                if option[0] in options:
                    checker.set_option(option[0], options[option[0]])

    def adapt_mccabe(self, tool):
        disabled = self.profile.get_disabled_messages('mccabe')

        tool.ignore_codes = tuple(set(
            tool.ignore_codes + tuple(disabled)
        ))

        if 'max-complexity' in self.profile.mccabe['options']:
            tool.max_complexity = \
                self.profile.mccabe['options']['max-complexity']

    def adapt_pyflakes(self, tool):
        disabled = self.profile.get_disabled_messages('pyflakes')

        tool.ignore_codes = tuple(set(
            tool.ignore_codes + tuple(disabled)
        ))

    def adapt_frosted(self, tool):
        disabled = self.profile.get_disabled_messages('frosted')

        tool.ignore_codes = tuple(set(
            tool.ignore_codes + tuple(disabled)
        ))

    def adapt_pep8(self, style_guide, use_config=True):
        if not use_config:
            return

        disabled = self.profile.get_disabled_messages('pep8')

        style_guide.options.ignore = tuple(set(
            style_guide.options.ignore + tuple(disabled)
        ))

        if 'max-line-length' in self.profile.pep8['options']:
            style_guide.options.max_line_length = \
                self.profile.pep8['options']['max-line-length']

########NEW FILE########
__FILENAME__ = autodetect
import os
import re
from prospector.adaptor import LIBRARY_ADAPTORS
from requirements_detector import find_requirements
from requirements_detector.detect import RequirementsNotFound


# see http://docs.python.org/2/reference/lexical_analysis.html#identifiers
_FROM_IMPORT_REGEX = re.compile(r'^\s*from ([\._a-zA-Z0-9]+) import .*$')
_IMPORT_REGEX = re.compile(r'^\s*import ([\._a-zA-Z0-9]+)$')


def find_from_imports(file_contents):
    names = set()
    for line in file_contents.split('\n'):
        match = _IMPORT_REGEX.match(line)
        if match is None:
            match = _FROM_IMPORT_REGEX.match(line)
        if match is None:
            continue
        import_names = match.group(1).split('.')
        for import_name in import_names:
            if import_name in LIBRARY_ADAPTORS:
                names.add(import_name)
    return names


def find_from_path(path):
    names = set()
    max_possible = len(LIBRARY_ADAPTORS.keys())

    for item in os.listdir(path):
        item_path = os.path.abspath(os.path.join(path, item))
        if os.path.isdir(item_path):
            names |= find_from_path(item_path)
        elif not os.path.islink(item_path) and item_path.endswith('.py'):
            with open(item_path) as fip:
                names |= find_from_imports(fip.read())

        if len(names) == max_possible:
            # don't continue on recursing, there's no point!
            break

    return names


def find_from_requirements(path):
    reqs = find_requirements(path)
    names = []
    for requirement in reqs:
        if requirement.name is not None \
                and requirement.name.lower() in LIBRARY_ADAPTORS:
            names.append(requirement.name.lower())
    return names


def autodetect_libraries(path):

    adaptor_names = []

    try:
        adaptor_names = find_from_requirements(path)

    # pylint: disable=W0704
    except RequirementsNotFound:
        pass

    if len(adaptor_names) == 0:
        adaptor_names = find_from_path(path)

    adaptors = []
    for adaptor_name in adaptor_names:
        adaptors.append((adaptor_name, LIBRARY_ADAPTORS[adaptor_name]()))

    return adaptors

########NEW FILE########
__FILENAME__ = blender
# This module contains the logic for "blending" of errors.
# Since prospector runs multiple tools with overlapping functionality, this
# module exists to merge together equivalent warnings from different tools for
# the same line. For example, both pyflakes and pylint will generate an
# "Unused Import" warning on the same line. This is obviously redundant, so we
# remove duplicates.
from collections import defaultdict

import pkg_resources
import yaml


__all__ = (
    'blend',
    'BLEND_COMBOS',
)


def blend_line(messages, blend_combos=None):
    """
    Given a list of messages on the same line, blend them together so that we
    end up with one message per actual problem. Note that we can still return
    more than one message here if there are two or more different errors for
    the line.
    """
    blend_combos = blend_combos or BLEND_COMBOS
    blend_lists = [[] for _ in range(len(blend_combos))]
    blended = []

    # first we split messages into each of the possible blendable categories
    # so that we have a list of lists of messages which can be blended together
    for message in messages:
        key = (message.source, message.code)
        found = False
        for blend_combo_idx, blend_combo in enumerate(blend_combos):
            if key in blend_combo:
                found = True
                blend_lists[blend_combo_idx].append(message)

        # note: we use 'found=True' here rather than a simple break/for-else
        # because this allows the same message to be put into more than one
        # 'bucket'. This means that the same message from pep8 can 'subsume'
        # two from pylint, for example.

        if not found:
            # if we get here, then this is not a message which can be blended,
            # so by definition is already blended
            blended.append(message)

    # we should now have a list of messages which all represent the same
    # problem on the same line, so we will sort them according to the priority
    # in BLEND and pick the first one
    for blend_combo_idx, blend_list in enumerate(blend_lists):
        if len(blend_list) == 0:
            continue
        blend_list.sort(
            key=lambda msg: blend_combos[blend_combo_idx].index(
                (msg.source, msg.code),
            ),
        )
        blended.append(blend_list[0])

    return blended


def blend(messages, blend_combos=None):
    blend_combos = blend_combos or BLEND_COMBOS

    # group messages by file and then line number
    msgs_grouped = defaultdict(lambda: defaultdict(list))

    for message in messages:
        msgs_grouped[message.location.path][message.location.line].append(
            message,
        )

    # now blend together all messages on the same line
    out = []
    for by_line in msgs_grouped.values():
        for messages_on_line in by_line.values():
            out += blend_line(messages_on_line, blend_combos)

    return out


def get_default_blend_combinations():
    combos = yaml.safe_load(
        pkg_resources.resource_string(__name__, 'blender_combinations.yaml')
    )
    combos = combos.get('combinations', [])

    defaults = []
    for combo in combos:
        toblend = []
        for msg in combo:
            toblend += msg.items()
        defaults.append(tuple(toblend))

    return tuple(defaults)


BLEND_COMBOS = get_default_blend_combinations()

########NEW FILE########
__FILENAME__ = config
import setoptconf as soc

from prospector.__pkginfo__ import get_version
from prospector.adaptor import LIBRARY_ADAPTORS
from prospector.formatters import FORMATTERS
from prospector.tools import TOOLS, DEFAULT_TOOLS


__all__ = (
    'build_manager',
)


def build_manager():
    manager = soc.ConfigurationManager('prospector')

    manager.add(soc.BooleanSetting('autodetect', default=True))
    manager.add(soc.ListSetting('uses', soc.String, default=[]))

    manager.add(soc.BooleanSetting('blending', default=True))
    manager.add(soc.BooleanSetting('common_plugin', default=True))

    manager.add(soc.BooleanSetting('doc_warnings', default=False))
    manager.add(soc.BooleanSetting('test_warnings', default=False))
    manager.add(soc.BooleanSetting('style_warnings', default=True))
    manager.add(soc.BooleanSetting('full_pep8', default=False))
    manager.add(soc.IntegerSetting('max_line_length', default=None))

    manager.add(soc.BooleanSetting('messages_only', default=False))
    manager.add(soc.BooleanSetting('summary_only', default=False))
    manager.add(soc.ChoiceSetting(
        'output_format',
        sorted(FORMATTERS.keys()),
        default='text',
    ))
    manager.add(soc.BooleanSetting('absolute_paths', default=False))

    manager.add(soc.ListSetting(
        'tools',
        soc.Choice(sorted(TOOLS.keys())),
        default=sorted(DEFAULT_TOOLS),
    ))
    manager.add(soc.ListSetting('profiles', soc.String, default=[]))
    manager.add(soc.ChoiceSetting(
        'strictness',
        ['veryhigh', 'high', 'medium', 'low', 'verylow'],
        default='medium',
    ))
    manager.add(soc.ChoiceSetting(
        'external_config',
        ['none', 'merge', 'only'],
        default='only',
    ))

    manager.add(soc.StringSetting('path', default=None))

    manager.add(soc.ListSetting('ignore_patterns', soc.String, default=[]))
    manager.add(soc.ListSetting('ignore_paths', soc.String, default=[]))

    manager.add(soc.BooleanSetting('die_on_tool_error', default=False))

    return manager


def build_default_sources():
    sources = []

    sources.append(build_command_line_source())
    sources.append(soc.EnvironmentVariableSource())
    sources.append(soc.ConfigFileSource((
        '.prospectorrc',
        'setup.cfg',
        'tox.ini',
    )))
    sources.append(soc.ConfigFileSource((
        soc.ConfigDirectory('.prospectorrc'),
        soc.HomeDirectory('.prospectorrc'),
    )))

    return sources


def build_command_line_source():
    parser_options = {
        'description': 'Performs static analysis of Python code',
    }

    options = {
        'autodetect': {
            'flags': ['-A', '--no-autodetect'],
            'help': 'Turn off auto-detection of frameworks and libraries used.'
                    ' By default, autodetection will be used. To specify'
                    ' manually, see the --uses option.',
        },
        'uses': {
            'flags': ['-u', '--uses'],
            'help': 'A list of one or more libraries or frameworks that the'
                    ' project users. Possible values are: %s. This will be'
                    ' autodetected by default, but if autodetection doesn\'t'
                    ' work, manually specify them using this flag.' % (
                        ', '.join(sorted(LIBRARY_ADAPTORS.keys())),
                    )
        },
        'blending': {
            'flags': ['-B', '--no-blending'],
            'help': 'Turn off blending of messages. Prospector will merge'
                    ' together messages from different tools if they represent'
                    ' the same error. Use this option to see all unmerged'
                    ' messages.',
        },
        'common_plugin': {
            'flags': ['--no-common-plugin'],
        },
        'doc_warnings': {
            'flags': ['-D', '--doc-warnings'],
            'help': 'Include warnings about documentation.',
        },
        'test_warnings': {
            'flags': ['-T', '--test-warnings'],
            'help': 'Also check test modules and packages.',
        },
        'style_warnings': {
            'flags': ['-8', '--no-style-warnings'],
            'help': 'Don\'t create any warnings about style. This disables the'
                    ' PEP8 tool and similar checks for formatting.',
        },
        'full_pep8': {
            'flags': ['-F', '--full-pep8'],
            'help': 'Enables every PEP8 warning, so that all PEP8 style'
                    ' violations will be reported.',
        },
        'max_line_length': {
            'flags': ['--max-line-length'],
            'help': 'The maximum line length allowed. This will be set by the strictness if no'
                    ' value is explicitly specified'

        },
        'messages_only': {
            'flags': ['-M', '--messages-only'],
            'help': 'Only output message information (don\'t output summary'
                    ' information about the checks)',
        },
        'summary_only': {
            'flags': ['-S', '--summary-only'],
            'help': 'Only output summary information about the checks (don\'t'
                    'output message information)',
        },
        'output_format': {
            'flags': ['-o', '--output-format'],
            'help': 'The output format. Valid values are: %s' % (
                ', '.join(sorted(FORMATTERS.keys())),
            ),
        },
        'absolute_paths': {
            'help': 'Whether to output absolute paths when referencing files'
                    'in messages. By default, paths will be relative to the'
                    'project path',
        },
        'tools': {
            'flags': ['-t', '--tool'],
            'help': 'A list of tools to run. Possible values are: %s. By'
            ' default, the following tools will be run: %s' % (
                ', '.join(sorted(TOOLS.keys())),
                ', '.join(sorted(DEFAULT_TOOLS)),
            ),
        },
        'profiles': {
            'flags': ['-P', '--profile'],
            'help': 'The list of profiles to load. A profile is a certain'
                    ' \'type\' of behaviour for prospector, and is represented'
                    ' by a YAML configuration file. A full path to the YAML'
                    ' file describing the profile must be provided.',
        },
        'strictness': {
            'flags': ['-s', '--strictness'],
            'help': 'How strict the checker should be. This affects how'
                    ' harshly the checker will enforce coding guidelines. The'
                    ' default value is "medium", possible values are'
                    ' "veryhigh", "high", "medium", "low" and "verylow".',
        },
        'external_config': {
            'flags': ['-e', '--external-config'],
            'help': 'Determines how prospector should behave when'
                    ' configuration already exists for a tool. By default,'
                    ' prospector will use existing configuration. A value of'
                    ' "merge" will cause prospector to merge existing config'
                    ' and its own config, and "none" means that prospector'
                    ' will use only its own config.',
        },
        'ignore_patterns': {
            'flags': ['-I', '--ignore-patterns'],
            'help': 'A list of paths to ignore, as a list of regular'
                    ' expressions. Files and folders will be ignored if their'
                    ' full path contains any of these patterns.',
        },
        'ignore_paths': {
            'flags': ['-i', '--ignore-paths'],
            'help': 'A list of file or directory names to ignore. If the'
                    ' complete name matches any of the items in this list, the'
                    ' file or directory (and all subdirectories) will be'
                    ' ignored.',
        },
        'die_on_tool_error': {
            'flags': ['--die-on-tool-error'],
            'help': 'If a tool fails to run, prospector will try to carry on.'
                    ' Use this flag to cause prospector to die and raise the'
                    ' exception the tool generated. Mostly useful for'
                    ' development on prospector.',
        },
        'path': {
            'flags': ['-p', '--path'],
            'help': 'The path to a Python project to inspect. Defaults to PWD'
                    ' if not specified. Note: This command line argument is'
                    ' deprecated and will be removed in a future update. Please'
                    ' use the positional PATH argument instead.'
        }
    }

    positional = (
        ('checkpath', {
            'help': 'The path to a Python project to inspect. Defaults to PWD'
                    '  if not specified.',
            'metavar': 'PATH',
            'nargs': '*',
        }),
    )

    return soc.CommandLineSource(
        options=options,
        version=get_version(),
        parser_options=parser_options,
        positional=positional,
    )

########NEW FILE########
__FILENAME__ = base

__all__ = (
    'Formatter',
)


# pylint: disable=R0903
class Formatter(object):
    def __init__(self, summary, messages):
        self.summary = summary
        self.messages = messages

    def render(self, summary=True, messages=True):
        pass

########NEW FILE########
__FILENAME__ = emacs
from prospector.formatters.text import TextFormatter


__all__ = (
    'EmacsFormatter',
)


class EmacsFormatter(TextFormatter):
    def render_message(self, message):
        output = []

        output.append('%s:%s :' % (
            message.location.path,
            message.location.line,
        ))

        output.append(
            '    L%s:%s %s: %s - %s' % (
                message.location.line or '-',
                message.location.character if message.location.line else '-',
                message.location.function,
                message.source,
                message.code,
            )
        )

        output.append('    %s' % message.message)

        return '\n'.join(output)

########NEW FILE########
__FILENAME__ = grouped
from collections import defaultdict

from prospector.formatters.text import TextFormatter


__all__ = (
    'GroupedFormatter',
)


class GroupedFormatter(TextFormatter):
    def render_messages(self):
        output = [
            'Messages',
            '========',
            '',
        ]

        # pylint: disable=W0108
        groups = defaultdict(lambda: defaultdict(list))

        for message in self.messages:
            groups[message.location.path][message.location.line].append(message)

        for filename in sorted(groups.keys()):
            output.append(filename)

            for line in sorted(groups[filename].keys(), key=lambda x: 0 if x is None else int(x)):
                output.append('  Line: %s' % line)

                for message in groups[filename][line]:
                    output.append(
                        '    %s: %s / %s%s' % (
                            message.source,
                            message.code,
                            message.message,
                            (' (col %s)' % message.location.character) if message.location.character else '',
                        )
                    )

            output.append('')

        return '\n'.join(output)

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import

import json

from datetime import datetime

from prospector.formatters.base import Formatter


__all__ = (
    'JsonFormatter',
)


# pylint: disable=R0903
class JsonFormatter(Formatter):
    def render(self, summary=True, messages=True):
        output = {}

        if summary:
            # we need to slightly change the types and format
            # of a few of the items in the summary to make
            # them play nice with JSON formatting
            munged = {}
            for key, value in self.summary.items():
                if isinstance(value, datetime):
                    munged[key] = str(value)
                else:
                    munged[key] = value
            output['summary'] = munged

        if messages:
            output['messages'] = [m.as_dict() for m in self.messages]

        return json.dumps(output, indent=2)

########NEW FILE########
__FILENAME__ = text
from prospector.formatters.base import Formatter


__all__ = (
    'TextFormatter',
)


# pylint: disable=W0108


class TextFormatter(Formatter):
    summary_labels = (
        ('started', 'Started'),
        ('completed', 'Finished'),
        ('time_taken', 'Time Taken', lambda x: '%s seconds' % x),
        ('formatter', 'Formatter'),
        ('strictness', 'Strictness'),
        ('libraries', 'Libraries Used', lambda x: ', '.join(x)),
        ('tools', 'Tools Run', lambda x: ', '.join(x)),
        ('adaptors', 'Adaptors', lambda x: ', '.join(x)),
        ('message_count', 'Message Found'),
    )

    def render_summary(self):
        output = [
            'Check Information',
            '=================',
        ]

        label_width = max([len(label[1]) for label in self.summary_labels])

        for summary_label in self.summary_labels:
            key = summary_label[0]
            if key in self.summary:
                label = summary_label[1]
                if len(summary_label) > 2:
                    value = summary_label[2](self.summary[key])
                else:
                    value = self.summary[key]
                output.append(
                    '%s: %s' % (
                        label.rjust(label_width),
                        value,
                    )
                )

        return '\n'.join(output)

    # pylint: disable=R0201
    def render_message(self, message):
        output = []

        if message.location.module:
            output.append('%s (%s):' % (
                message.location.module,
                message.location.path
            ))
        else:
            output.append('%s:' % message.location.path)

        output.append(
            '    L%s:%s %s: %s - %s' % (
                message.location.line or '-',
                message.location.character if message.location.line else '-',
                message.location.function,
                message.source,
                message.code,
            )
        )

        output.append('    %s' % message.message)

        return '\n'.join(output)

    def render_messages(self):
        output = [
            'Messages',
            '========',
            '',
        ]

        for message in self.messages:
            output.append(self.render_message(message))
            output.append('')

        return '\n'.join(output)

    def render(self, summary=True, messages=True):
        output = ''
        if summary:
            output = self.render_summary()
        output += '\n\n\n'
        if messages:
            output += self.render_messages()
        return output.strip()

########NEW FILE########
__FILENAME__ = yaml
from __future__ import absolute_import

import yaml

from prospector.formatters.base import Formatter


__all__ = (
    'YamlFormatter',
)


# pylint: disable=R0903
class YamlFormatter(Formatter):
    def render(self, summary=True, messages=True):
        output = {}

        if summary:
            output['summary'] = self.summary

        if messages:
            output['messages'] = [m.as_dict() for m in self.messages]

        return yaml.safe_dump(
            output,
            indent=2,
            default_flow_style=False,
            encoding='utf-8',
            allow_unicode=True,
        )

########NEW FILE########
__FILENAME__ = message
import os


class Location(object):

    def __init__(self, path, module, function, line, character, absolute_path=True):
        self.path = path
        self._path_is_absolute = absolute_path
        self.module = module or None
        self.function = function or None
        self.line = None if line == -1 else line
        self.character = None if line == -1 else character

    def to_absolute_path(self, root):
        if self._path_is_absolute:
            return
        self.path = os.path.abspath(os.path.join(root, self.path))
        self._path_is_absolute = True

    def to_relative_path(self, root):
        if not self._path_is_absolute:
            return
        self.path = os.path.relpath(self.path, root)
        self._path_is_absolute = False

    def as_dict(self):
        return {
            'path': self.path,
            'module': self.module,
            'function': self.function,
            'line': self.line,
            'character': self.character
        }

    def __hash__(self):
        return hash((self.path, self.line, self.character))

    def __eq__(self, other):
        return self.path == other.path and self.line == other.line and self.character == other.character

    def __lt__(self, other):
        if self.path == other.path:
            if self.line == other.line:
                return self.character < other.character
            return (self.line or -1) < (other.line or -1)  # line can be None if it a file-global warning
        return self.path < other.path


class Message(object):

    def __init__(self, source, code, location, message):
        self.source = source
        self.code = code
        self.location = location
        self.message = message

    def to_absolute_path(self, root):
        self.location.to_absolute_path(root)

    def to_relative_path(self, root):
        self.location.to_relative_path(root)

    def as_dict(self):
        return {
            'source': self.source,
            'code': self.code,
            'location': self.location.as_dict(),
            'message': self.message
        }

    def __repr__(self):
        return "%s-%s" % (self.source, self.code)

    def __eq__(self, other):
        if self.location == other.location:
            return self.code == other.code
        else:
            return False

    def __lt__(self, other):
        if self.location == other.location:
            return self.code < other.code
        return self.location < other.location

########NEW FILE########
__FILENAME__ = profile
import os
import yaml
from prospector.tools import TOOLS, DEFAULT_TOOLS


class ProfileNotFound(Exception):
    def __init__(self, name, filepath):
        super(ProfileNotFound, self).__init__()
        self.name = name
        self.filepath = filepath

    def __repr__(self):
        return "Could not find profile %s at %s" % (self.name, self.filepath)


_EMPTY_DATA = {
    'inherits': [],
    'ignore': [],
}


for toolname in TOOLS.keys():
    _EMPTY_DATA[toolname] = {
        'disable': [],
        'enable': [],
        'run': None,
        'options': {}
    }


def load_profiles(names, basedir=None):
    if not isinstance(names, (list, tuple)):
        names = (names,)
    profiles = [_load_profile(name, basedir=basedir)[0] for name in names]
    return merge_profiles(profiles)


def _load_content(name, basedir=None):

    if name.endswith('.yaml'):
        # assume that this is a full path that we can load
        filename = name
    else:
        basedir = basedir or os.path.join(
            os.path.dirname(__file__),
            'profiles',
        )
        filename = os.path.join(basedir, '%s.yaml' % name)

    if not os.path.exists(filename):
        raise ProfileNotFound(name, os.path.abspath(filename))

    with open(filename) as fct:
        return fct.read()


def from_file(name, basedir=None):
    return parse_profile(name, _load_content(name, basedir))


def _load_profile(name, basedir=None, inherits_set=None):
    inherits_set = inherits_set or set()

    profile = parse_profile(name, _load_content(name, basedir))
    inherits_set.add(profile.name)

    for inherited in profile.inherits:
        if inherited not in inherits_set:
            inherited_profile, sub_inherits_set = _load_profile(
                inherited,
                basedir,
                inherits_set,
            )
            profile.merge(inherited_profile)
            inherits_set |= sub_inherits_set

    return profile, inherits_set


def parse_profile(name, contents):
    if name.endswith('.yaml'):
        # this was a full path
        name = os.path.splitext(os.path.basename(name))[0]
    data = yaml.safe_load(contents)
    if data is None:
        # this happens if a completely empty YAML file is passed in to
        # parse_profile, for example
        data = dict(_EMPTY_DATA)
    else:
        data = _merge_dict(_EMPTY_DATA, data, dict1_priority=False)
    return StrictnessProfile(name, data)


def _merge_dict(dict1, dict2, dedup_lists=False, dict1_priority=True):
    newdict = {}
    newdict.update(dict1)

    for key, value in dict2.items():
        if key not in dict1:
            newdict[key] = value
        elif value is None and dict1[key] is not None:
            newdict[key] = dict1[key]
        elif dict1[key] is None and value is not None:
            newdict[key] = value
        elif type(value) != type(dict1[key]):
            raise ValueError("Could not merge conflicting types %s and %s" % (
                type(value),
                type(dict1[key]),
            ))
        elif isinstance(value, dict):
            newdict[key] = _merge_dict(
                dict1[key],
                value,
                dedup_lists,
                dict1_priority,
            )
        elif isinstance(value, (list, tuple)):
            newdict[key] = list(set(dict1[key]) | set(value))
        elif not dict1_priority:
            newdict[key] = value

    return newdict


class StrictnessProfile(object):

    def __init__(self, name, profile_dict):
        self.name = name
        self.inherits = profile_dict['inherits']
        self.ignore = profile_dict['ignore']

        for tool in TOOLS.keys():
            setattr(self, tool, profile_dict[tool])

    def to_profile_dict(self):
        thedict = {
            'inherits': self.inherits,
            'ignore': self.ignore,
        }

        for tool in TOOLS.keys():
            thedict[tool] = getattr(self, tool)

    def get_disabled_messages(self, tool_name):
        disable = getattr(self, tool_name)['disable']
        enable = getattr(self, tool_name)['enable']
        return list(set(disable) - set(enable))

    def merge(self, other_profile):
        self.ignore = list(set(self.ignore + other_profile.ignore))
        self.inherits = list(set(self.inherits + other_profile.inherits))

        for tool in TOOLS.keys():
            merged = _merge_dict(getattr(self, tool), getattr(other_profile, tool))
            setattr(self, tool, merged)

    def is_tool_enabled(self, name):
        run = getattr(self, name)['run']
        if run is None:
            run = name in DEFAULT_TOOLS
        return run


def merge_profiles(profiles):
    merged_profile = profiles[0]
    for profile in profiles[1:]:
        merged_profile.merge(profile)
    return merged_profile

########NEW FILE########
__FILENAME__ = run
import os.path
import re
import sys

from datetime import datetime

from prospector import config as cfg, tools, blender
from prospector.adaptor import LIBRARY_ADAPTORS
from prospector.adaptor.common import CommonAdaptor
from prospector.adaptor.profile import ProfileAdaptor
from prospector.autodetect import autodetect_libraries
from prospector.formatters import FORMATTERS
from prospector.message import Location, Message


__all__ = (
    'Prospector',
    'main',
)


class Prospector(object):
    def __init__(self, config, path):
        self.config = config
        self.path = path
        self.adaptors = []
        self.libraries = []
        self.profiles = []
        self.profile_adaptor = None
        self.tool_runners = []
        self.ignores = []

        self._determine_adapters()
        self._determine_profiles()
        self._determine_tool_runners()
        self._determine_ignores()

    def _determine_adapters(self):
        # Bring in the common adaptor
        if self.config.common_plugin:
            self.adaptors.append(CommonAdaptor())

        # Bring in adaptors that we automatically detect are needed
        if self.config.autodetect:
            for name, adaptor in autodetect_libraries(self.path):
                self.libraries.append(name)
                self.adaptors.append(adaptor)

        # Bring in adaptors for the specified libraries
        for name in self.config.uses:
            if name not in self.libraries:
                self.libraries.append(name)
                self.adaptors.append(LIBRARY_ADAPTORS[name]())

    def _determine_profiles(self):
        # Use the strictness profile
        if self.config.strictness:
            self.profiles.append('strictness_%s' % self.config.strictness)

        # Use other specialty profiles based on options
        if not self.config.doc_warnings:
            self.profiles.append('no_doc_warnings')
        if not self.config.test_warnings:
            self.profiles.append('no_test_warnings')
        if not self.config.style_warnings:
            self.profiles.append('no_pep8')
        if self.config.full_pep8:
            self.profiles.append('full_pep8')

        # Use the specified profiles
        self.profiles += self.config.profiles

        self.profile_adaptor = ProfileAdaptor(self.profiles)
        self.adaptors.append(self.profile_adaptor)

    def _determine_tool_runners(self):
        for tool in self.config.tools:
            if self.profile_adaptor.is_tool_enabled(tool):
                self.tool_runners.append(tools.TOOLS[tool]())

    def _determine_ignores(self):
        # Grab ignore patterns from the profile adapter
        ignores = [
            re.compile(ignore)
            for ignore in self.profile_adaptor.profile.ignore
        ]

        # Grab ignore patterns from the options
        ignores += [
            re.compile(patt)
            for patt in self.config.ignore_patterns
        ]

        # Grab ignore paths from the options
        boundary = r"(^|/|\\)%s(/|\\|$)"
        ignores += [
            re.compile(boundary % re.escape(ignore_path))
            for ignore_path in self.config.ignore_paths
        ]

        # Add any specified by the other adaptors
        for adaptor in self.adaptors:
            if hasattr(adaptor.__class__, 'ignore_patterns'):
                ignores += [re.compile(p) for p in adaptor.ignore_patterns]

        self.ignores = ignores

    def process_messages(self, messages):
        for message in messages:
            if self.config.absolute_paths:
                message.to_absolute_path(self.path)
            else:
                message.to_relative_path(self.path)
        if self.config.blending:
            messages = blender.blend(messages)

        return messages

    def execute(self):
        summary = {
            'started': datetime.now(),
            'libraries': self.libraries,
            'strictness': self.config.strictness,
            'profiles': self.profiles,
            'adaptors': [adaptor.name for adaptor in self.adaptors],
            'tools': self.config.tools,
        }

        # Prep the tools.
        for tool in self.tool_runners:
            tool.prepare(self.path, self.ignores, self.config, self.adaptors)

        # Run the tools
        messages = []
        for tool in self.tool_runners:
            try:
                messages += tool.run()
            except Exception:  # pylint: disable=W0703
                if self.config.die_on_tool_error:
                    raise
                else:
                    for name, cls in tools.TOOLS.items():
                        if cls == tool.__class__:
                            toolname = name
                            break
                    else:
                        toolname = 'Unknown'

                    loc = Location(self.path, None, None, None, None)
                    msg = 'Tool %s failed to run (exception was raised)' % (
                        toolname,
                    )
                    message = Message(
                        toolname,
                        'failure',
                        loc,
                        message=msg,
                    )
                    messages.append(message)

        messages = self.process_messages(messages)

        summary['message_count'] = len(messages)
        summary['completed'] = datetime.now()
        delta = (summary['completed'] - summary['started'])
        summary['time_taken'] = '%0.2f' % delta.total_seconds()

        return summary, messages


def main():
    # Get our configuration
    mgr = cfg.build_manager()
    config = mgr.retrieve(*cfg.build_default_sources())

    # Figure out what paths we're prospecting
    if config['path']:
        paths = [config['path']]
    elif mgr.arguments['checkpath']:
        paths = mgr.arguments['checkpath']
    else:
        paths = [os.getcwd()]

    # Make it so
    prospector = Prospector(config, paths[0])
    summary, messages = prospector.execute()

    # Get the output formatter
    summary['formatter'] = config.output_format
    formatter = FORMATTERS[config.output_format](summary, messages)

    # Produce the output
    sys.stdout.write(formatter.render(
        summary=not config.messages_only,
        messages=not config.summary_only,
    ))
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = base


class ToolBase(object):

    def prepare(self, rootpath, ignore, args, adaptors):
        pass

    def run(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = collector
from __future__ import absolute_import
from pylint.reporters import BaseReporter
from prospector.message import Location, Message


class Collector(BaseReporter):

    name = 'collector'

    def __init__(self):
        BaseReporter.__init__(self, output=None)
        self._messages = []

    def add_message(self, msg_id, location, msg):
        # (* magic is acceptable here)
        # pylint: disable=W0142
        loc = Location(*location)
        message = Message('pylint', msg_id, loc, msg)
        self._messages.append(message)

    def _display(self, layout):
        pass

    def get_messages(self):
        return self._messages

########NEW FILE########
__FILENAME__ = indent_checker
from __future__ import absolute_import

import tokenize
from pylint.checkers import BaseTokenChecker
from pylint.interfaces import ITokenChecker


class IndentChecker(BaseTokenChecker):

    __implements__ = (ITokenChecker,)

    name = 'indentation'
    msgs = {
        'W0313': ('File contains mixed indentation - some lines use tabs, some lines use spaces',
                  'indentation-mixture',
                  'Used when there are some mixed tabs and spaces in a module.'),
        'W0314': ('Line uses %s for indentation, but %s required',
                  'incorrect-indentation',
                  'Used when the indentation of a line does not match the style required by configuration.')
    }
    options = (
        ('indent-strict-spaces',
         {'default': False, 'type': "yn", 'metavar': '<boolean>',
          'help': 'Enforce using only spaces for indentation'}),

        ('indent-strict-tabs',
         {'default': False, 'type': "yn", 'metavar': '<boolean>',
          'help': 'Enforce using only tabs for indentation'})
    )

    def process_tokens(self, tokens):
        tab_count = space_count = 0
        line_num = 0

        for token in tokens:
            if token[0] == tokenize.NEWLINE:
                line_num += 1
                line = token[4]
                if line.startswith('\t'):
                    if self.config.indent_strict_spaces:
                        # we have tabs but are configured to only allow spaces
                        self.add_message('W0314', line=line_num, args=('tabs', 'spaces'))
                    tab_count += 1

                if line.startswith(' '):
                    if self.config.indent_strict_tabs:
                        # we have tabs but are configured to only allow spaces
                        self.add_message('W0314', line=line_num, args=('spaces', 'tabs'))
                    space_count += 1

        if tab_count > 0 and space_count > 0:
            # this file has mixed indentation!
            self.add_message('W0313', line=-1)

########NEW FILE########
__FILENAME__ = linter
from __future__ import absolute_import
import os

from logilab.common.configuration import OptionsManagerMixIn
from pylint.lint import PyLinter


class ProspectorLinter(PyLinter):  # pylint: disable=R0901,R0904

    def __init__(self, ignore, rootpath, *args, **kwargs):
        self._ignore = ignore
        self._rootpath = rootpath

        # set up the standard PyLint linter
        PyLinter.__init__(self, *args, **kwargs)

        # do some additional things!

        # for example, we want to re-initialise the OptionsManagerMixin
        # to supress the config error warning
        # pylint: disable=W0233
        OptionsManagerMixIn.__init__(self, usage=PyLinter.__doc__, quiet=True)

    def expand_files(self, modules):
        expanded = PyLinter.expand_files(self, modules)
        filtered = []
        for module in expanded:
            rel_path = os.path.relpath(module['path'], self._rootpath)
            if any([m.search(rel_path) for m in self._ignore]):
                continue
            filtered.append(module)
        return filtered

########NEW FILE########
__FILENAME__ = __pkginfo__

VERSION = (0, 5, 2)


def get_version():
    return '.'.join([str(v) for v in VERSION])

########NEW FILE########
__FILENAME__ = test_profile
import os
from unittest import TestCase
from prospector.profiles.profile import _merge_dict, merge_profiles, from_file, load_profiles


class TestProfileParsing(TestCase):

    def setUp(self):
        self._basedir = os.path.join(os.path.dirname(__file__), 'profiles')

    def _file_content(self, name):
        path = os.path.join(self._basedir, name)
        with open(path) as f:
            return f.read()

    def test_empty_disable_list(self):
        """
        This test verifies that a profile can still be loaded if it contains
        an empty 'pylint.disable' list
        """
        profile = load_profiles('empty_disable_list', basedir=self._basedir)
        self.assertEqual([], profile.pylint['disable'])

    def test_empty_profile(self):
        """
        Verifies that a completely empty profile can still be parsed and have
        default values
        """
        profile = load_profiles('empty_profile', basedir=self._basedir)
        self.assertEqual([], profile.pylint['disable'])

    def test_inheritance(self):
        profile = load_profiles('inherittest3', basedir=self._basedir)
        disable = profile.pylint['disable']
        disable.sort()
        self.assertEqual(['I0001', 'I0002', 'I0003'], disable)

    def test_profile_merge(self):

        profile1 = from_file('mergetest1', self._basedir)
        profile2 = from_file('mergetest2', self._basedir)
        profile3 = from_file('mergetest3', self._basedir)

        merged = merge_profiles((profile1, profile2, profile3))

        merged_disabled_warnings = merged.pylint['disable']
        merged_disabled_warnings.sort()
        expected = ['C1000', 'C1001', 'E0504', 'W1010', 'W1012']
        self.assertEqual(expected, merged_disabled_warnings)

    def test_ignores(self):
        profile = load_profiles('ignores', basedir=self._basedir)
        self.assertEqual(['^tests/', '/migrations/'].sort(), profile.ignore.sort())

    def test_disable_tool(self):
        profile = load_profiles('pylint_disabled', basedir=self._basedir)
        self.assertFalse(profile.is_tool_enabled('pylint'))
        self.assertTrue(profile.is_tool_enabled('pep8'))

    def test_disable_tool_inheritance(self):
        profile = load_profiles('pep8_and_pylint_disabled', basedir=self._basedir)
        self.assertFalse(profile.is_tool_enabled('pylint'))
        self.assertFalse(profile.is_tool_enabled('pep8'))

    def test_dict_merge(self):
        a = {
            'int': 1,
            'str': 'fish',
            'bool': True,
            'list': [1, 2],
            'dict': {
                'a': 1,
                'b': 2
            }
        }
        b = {
            'int': 2,
            'list': [2, 3],
            'bool': False,
            'dict': {
                'a': 3,
                'c': 4
            }
        }

        expected = {
            'int': 2,
            'str': 'fish',
            'bool': False,
            'list': [1, 2, 3],
            'dict': {
                'a': 3,
                'b': 2,
                'c': 4
            }
        }
        self.assertEqual(expected, _merge_dict(a, b, dedup_lists=True, dict1_priority=False))

        expected = {
            'int': 1,
            'str': 'fish',
            'bool': True,
            'list': [1, 2, 3],
            'dict': {
                'a': 1,
                'b': 2,
                'c': 4
            }
        }
        self.assertEqual(expected, _merge_dict(a, b, dedup_lists=True, dict1_priority=True))

########NEW FILE########
__FILENAME__ = test_autodetect
from unittest import TestCase
from prospector.autodetect import find_from_imports


class FindFromImportsTest(TestCase):

    def _test(self, contents, *expected_names):
        names = find_from_imports(contents)
        self.assertEqual(set(expected_names), names)

    def test_simple_imports(self):
        self._test('from django.db import models', 'django')
        self._test('import django', 'django')
        self._test('from django import db\nfrom celery import task', 'django', 'celery')

    def test_multiple_imports(self):
        self._test('from django.db import (models, \n'
                   '    some, other, stuff)', 'django')

    def test_indented_imports(self):
        self._test('def lala(self):\n    from django.db import models\n    return models.Model', 'django')

########NEW FILE########
__FILENAME__ = test_blender
from unittest import TestCase
from prospector import blender
from prospector.message import Message, Location


class TestBlendLine(TestCase):

    BLEND = (
        (
            ('s1', 's1c01'),
            ('s2', 's2c12')
        ),
        (
            ('s3', 's3c81'),
            ('s1', 's1c04'),
            ('s2', 's2c44')
        )
    )

    def _do_test(self, messages, expected):
        def _msg(source, code):
            loc = Location('path.py', 'path', None, 1, 0)
            return Message(source, code, loc, 'Test Message')

        messages = [_msg(*m) for m in messages]
        expected = set(expected)

        blended = blender.blend_line(messages, TestBlendLine.BLEND)
        result = set([(msg.source, msg.code) for msg in blended])

        self.assertEqual(expected, result)

    def test_blend_line(self):

        messages = (
            ('s2', 's2c12'),
            ('s2', 's2c11'),
            ('s1', 's1c01')
        )

        expected = (
            ('s1', 's1c01'),
            ('s2', 's2c11')  # s2c12 should be blended with s1c01
        )
        self._do_test(messages, expected)

    def test_single_blend(self):
        # these three should be blended together
        messages = (
            ('s1', 's1c04'),
            ('s2', 's2c44'),
            ('s3', 's3c81'),
        )
        # the s3 message is the highest priority
        expected = (
            ('s3', 's3c81'),
        )
        self._do_test(messages, expected)

    def test_nothing_to_blend(self):
        """
        Verifies that messages pass through if there is nothing to blend
        """
        messages = (
            ('s4', 's4c99'),
            ('s4', 's4c01'),
            ('s5', 's5c51'),
            ('s6', 's6c66')
        )
        self._do_test(messages, messages)  # expected = messages

    def test_no_messages(self):
        """
        Ensures that the blending works fine when there are no messages to blend
        """
        self._do_test((), ())


class TestBlend(TestCase):

    BLEND = (
        (
            ('s1', 's1c001'),
            ('s2', 's2c101')
        ),
    )

    def test_multiple_lines(self):
        def _msg(source, code, line_number):
            loc = Location('path.py', 'path', None, line_number, 0)
            return Message(source, code, loc, 'Test Message')

        messages = [
            _msg('s1', 's1c001', 4),
            _msg('s2', 's2c001', 6),
            _msg('s2', 's2c101', 4),
            _msg('s1', 's1c001', 6)
        ]

        result = blender.blend(messages, TestBlend.BLEND)
        result = [(msg.source, msg.code, msg.location.line) for msg in result]
        result = set(result)

        expected = set((
            ('s1', 's1c001', 4),
            ('s1', 's1c001', 6),
            ('s2', 's2c001', 6)
        ))

        self.assertEqual(expected, result)



########NEW FILE########
__FILENAME__ = test_message
from unittest import TestCase
from prospector.message import Location


class LocationOrderTest(TestCase):

    def test_path_order(self):

        locs = [
            Location('/tmp/path/module3.py', 'module3', 'somefunc', 15, 0),
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 10, 0),
            Location('/tmp/path/module2.py', 'module2', 'somefunc', 9, 0)
        ]

        paths = [loc.path for loc in locs]
        expected = sorted(paths)

        self.assertEqual(expected, [loc.path for loc in sorted(locs)])

    def test_line_order(self):

        locs = [
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 15, 0),
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 10, 0),
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 12, 0)
        ]

        lines = [loc.line for loc in locs]
        expected = sorted(lines)

        self.assertEqual(expected, [loc.line for loc in sorted(locs)])

    def test_char_order(self):

        locs = [
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 10, 7),
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 10, 0),
            Location('/tmp/path/module1.py', 'module1', 'somefunc', 10, 2)
        ]

        chars = [loc.character for loc in locs]
        expected = sorted(chars)

        self.assertEqual(expected, [loc.character for loc in sorted(locs)])
########NEW FILE########
__FILENAME__ = test_pylint_tool
import os
from unittest import TestCase
from prospector.tools.pylint import _find_package_paths


class TestPylintTool(TestCase):

    def test_find_packages(self):
        root = os.path.join(os.path.dirname(__file__), 'package_test')
        sys_paths, check_paths = _find_package_paths([], root)

        expected_checks = [os.path.join(os.path.dirname(__file__), p)
                           for p in ('package_test/package1', 'package_test/somedir/package2')]
        expected_sys_paths = [os.path.join(os.path.dirname(__file__), p)
                              for p in ('package_test', 'package_test/somedir')]

        sys_paths = list(sys_paths)

        sys_paths.sort()
        check_paths.sort()
        expected_checks.sort()
        expected_sys_paths.sort()

        self.assertEqual(expected_sys_paths, sys_paths)
        self.assertEqual(expected_checks, check_paths)
########NEW FILE########
