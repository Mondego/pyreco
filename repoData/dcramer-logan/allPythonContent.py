__FILENAME__ = importer
"""
logan.importer
~~~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

import sys
from django.utils.importlib import import_module
from logan.settings import load_settings, create_module

installed = False


def install(name, config_path, default_settings, **kwargs):
    global installed

    if installed:
        # TODO: reinstall
        return

    sys.meta_path.append(LoganImporter(name, config_path, default_settings, **kwargs))
    installed = True


class ConfigurationError(Exception):
    pass


class LoganImporter(object):
    def __init__(self, name, config_path, default_settings=None, allow_extras=True, callback=None):
        self.name = name
        self.config_path = config_path
        self.default_settings = default_settings
        self.allow_extras = allow_extras
        self.callback = callback
        self.validate()

    def __repr__(self):
        return "<%s for '%s' (%s)>" % (type(self), self.name, self.config_path)

    def validate(self):
        # TODO(dcramer): is there a better way to handle validation so it
        # is lazy and actually happens in LoganLoader?
        try:
            execfile(self.config_path, {
                '__file__': self.config_path
            })
        except Exception as e:
            exc_info = sys.exc_info()
            raise ConfigurationError, unicode(e), exc_info[2]

    def find_module(self, fullname, path=None):
        if fullname != self.name:
            return

        return LoganLoader(
            name=self.name,
            config_path=self.config_path,
            default_settings=self.default_settings,
            allow_extras=self.allow_extras,
            callback=self.callback,
        )


class LoganLoader(object):
    def __init__(self, name, config_path, default_settings=None, allow_extras=True, callback=None):
        self.name = name
        self.config_path = config_path
        self.default_settings = default_settings
        self.allow_extras = allow_extras
        self.callback = callback

    def load_module(self, fullname):
        try:
            return self._load_module(fullname)
        except Exception as e:
            exc_info = sys.exc_info()
            raise ConfigurationError, unicode(e), exc_info[2]

    def _load_module(self, fullname):
        # TODO: is this needed?
        if fullname in sys.modules:
            return sys.modules[fullname]  # pragma: no cover

        if self.default_settings:
            default_settings_mod = import_module(self.default_settings)
        else:
            default_settings_mod = None

        settings_mod = create_module(self.name)

        # Django doesn't play too nice without the config file living as a real file, so let's fake it.
        settings_mod.__file__ = self.config_path

        # install the default settings for this app
        load_settings(default_settings_mod, allow_extras=self.allow_extras, settings=settings_mod)

        # install the custom settings for this app
        load_settings(self.config_path, allow_extras=self.allow_extras, settings=settings_mod)

        if self.callback:
            self.callback(settings_mod)

        return settings_mod

########NEW FILE########
__FILENAME__ = runner
"""
logan.runner
~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

from django.core import management
from optparse import OptionParser
import os
import re
import sys

from logan import importer
from logan.settings import create_default_settings


def sanitize_name(project):
    project = project.replace(' ', '-')
    return re.sub('[^A-Z0-9a-z_-]', '-', project)


def parse_args(args):
    """
    This parses the arguments and returns a tuple containing:

    (args, command, command_args)

    For example, "--config=bar start --with=baz" would return:

    (['--config=bar'], 'start', ['--with=baz'])
    """
    index = None
    for arg_i, arg in enumerate(args):
        if not arg.startswith('-'):
            index = arg_i
            break

    # Unable to parse any arguments
    if index is None:
        return (args, None, [])

    return (args[:index], args[index], args[(index + 1):])


def configure_app(config_path=None, project=None, default_config_path=None,
                  default_settings=None, settings_initializer=None,
                  settings_envvar=None, initializer=None, allow_extras=True,
                  config_module_name=None, runner_name=None):
    """
    :param project: should represent the canonical name for the project, generally
        the same name it assigned in distutils.
    :param default_config_path: the default location for the configuration file.
    :param default_settings: default settings to load (think inheritence).
    :param settings_initializer: a callback function which should return a string
        representing the default settings template to generate.
    :param initializer: a callback function which will be executed before the command
        is executed. It is passed a dictionary of various configuration attributes.
    """

    project_filename = sanitize_name(project)

    if default_config_path is None:
        default_config_path = '~/%s/%s.conf.py' % (project_filename, project_filename)

    if settings_envvar is None:
        settings_envvar = project_filename.upper() + '_CONF'

    if config_module_name is None:
        config_module_name = project_filename + '_config'

    # normalize path
    if settings_envvar in os.environ:
        default_config_path = os.environ.get(settings_envvar)
    else:
        default_config_path = os.path.normpath(os.path.abspath(os.path.expanduser(default_config_path)))

    if not config_path:
        config_path = default_config_path

    config_path = os.path.expanduser(config_path)

    if not os.path.exists(config_path):
        if runner_name:
            raise ValueError("Configuration file does not exist. Use '%s init' to initialize the file." % (runner_name,))
        raise ValueError("Configuration file does not exist at %r" % (config_path,))

    os.environ['DJANGO_SETTINGS_MODULE'] = config_module_name

    def settings_callback(settings):
        if initializer is None:
            return

        try:
            initializer({
                'project': project,
                'config_path': config_path,
                'settings': settings,
            })
        except Exception:
            # XXX: Django doesn't like various errors in this path
            import sys
            import traceback
            traceback.print_exc()
            sys.exit(1)

    importer.install(
        config_module_name, config_path, default_settings,
        allow_extras=allow_extras, callback=settings_callback)

    # HACK(dcramer): we need to force access of django.conf.settings to
    # ensure we don't hit any import-driven recursive behavior
    from django.conf import settings
    hasattr(settings, 'INSTALLED_APPS')


def run_app(**kwargs):
    sys_args = sys.argv

    # The established command for running this program
    runner_name = os.path.basename(sys_args[0])

    args, command, command_args = parse_args(sys_args[1:])

    if not command:
        print "usage: %s [--config=/path/to/settings.py] [command] [options]" % runner_name
        sys.exit(1)

    default_config_path = kwargs.get('default_config_path')

    parser = OptionParser()

    # The ``init`` command is reserved for initializing configuration
    if command == 'init':
        (options, opt_args) = parser.parse_args()

        settings_initializer = kwargs.get('settings_initializer')

        config_path = os.path.expanduser(' '.join(opt_args[1:]) or default_config_path)

        if os.path.exists(config_path):
            resp = None
            while resp not in ('Y', 'n'):
                resp = raw_input('File already exists at %r, overwrite? [nY] ' % config_path)
                if resp == 'n':
                    print "Aborted!"
                    return

        try:
            create_default_settings(config_path, settings_initializer)
        except OSError, e:
            raise e.__class__, 'Unable to write default settings file to %r' % config_path

        print "Configuration file created at %r" % config_path

        return

    parser.add_option('--config', metavar='CONFIG')

    (options, logan_args) = parser.parse_args(args)

    config_path = options.config

    configure_app(config_path=config_path, **kwargs)

    management.execute_from_command_line([runner_name, command] + command_args)

    sys.exit(0)

if __name__ == '__main__':
    run_app()

########NEW FILE########
__FILENAME__ = settings
"""
logan.settings
~~~~~~~~~~~~~~

:copyright: (c) 2012 David Cramer.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

import errno
import imp
import os
import sys
from django.conf import settings as django_settings

__all__ = ('create_default_settings', 'load_settings')

TUPLE_SETTINGS = ('INSTALLED_APPS', 'TEMPLATE_DIRS')


def create_default_settings(filepath, settings_initializer):
    if settings_initializer is not None:
        output = settings_initializer()
    else:
        output = ''

    dirname = os.path.dirname(filepath)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(filepath, 'w') as fp:
        fp.write(output)


def create_module(name, install=True):
    mod = imp.new_module(name)
    if install:
        sys.modules[name] = mod
    return mod


def load_settings(mod_or_filename, silent=False, allow_extras=True,
                  settings=django_settings):
    if isinstance(mod_or_filename, basestring):
        conf = create_module('temp_config', install=False)
        conf.__file__ = mod_or_filename
        try:
            execfile(mod_or_filename, conf.__dict__)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return settings
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
    else:
        conf = mod_or_filename

    add_settings(conf, allow_extras=allow_extras, settings=settings)


def add_settings(mod, allow_extras=True, settings=django_settings):
    """
    Adds all settings that are part of ``mod`` to the global settings object.

    Special cases ``EXTRA_APPS`` to append the specified applications to the
    list of ``INSTALLED_APPS``.
    """
    extras = {}

    for setting in dir(mod):
        if setting == setting.upper():
            setting_value = getattr(mod, setting)
            if setting in TUPLE_SETTINGS and type(setting_value) == str:
                setting_value = (setting_value,)  # In case the user forgot the comma.

            # Any setting that starts with EXTRA_ and matches a setting that is a list or tuple
            # will automatically append the values to the current setting.
            # It might make sense to make this less magical
            if setting.startswith('EXTRA_'):
                base_setting = setting.split('EXTRA_', 1)[-1]
                if isinstance(getattr(settings, base_setting), (list, tuple)):
                    extras[base_setting] = setting_value
                    continue

            setattr(settings, setting, setting_value)

    for key, value in extras.iteritems():
        curval = getattr(settings, key)
        setattr(settings, key, curval + type(curval)(value))

########NEW FILE########
__FILENAME__ = tests
from unittest2 import TestCase

from logan.runner import sanitize_name, parse_args


class SanitizeNameTestCase(TestCase):
    def test_simple(self):
        self.assertEquals(sanitize_name('foo bar'), 'foo-bar')


class ParseArgsTestCase(TestCase):
    def test_no_args(self):
        result = parse_args([])
        self.assertEquals(result, ([], None, []))

    def test_no_command(self):
        result = parse_args(['--foo', '--bar'])
        self.assertEquals(result, (['--foo', '--bar'], None, []))

    def test_no_command_args(self):
        result = parse_args(['--foo', '--bar', 'foo'])
        self.assertEquals(result, (['--foo', '--bar'], 'foo', []))

    def test_no_base_args(self):
        result = parse_args(['foo', '--foo', '--bar'])
        self.assertEquals(result, ([], 'foo', ['--foo', '--bar']))

    def test_mixed_args(self):
        result = parse_args(['-f', 'foo', '--foo', '--bar'])
        self.assertEquals(result, (['-f'], 'foo', ['--foo', '--bar']))

########NEW FILE########
__FILENAME__ = tests
from unittest2 import TestCase

import mock
from logan.settings import add_settings


class AddSettingsTestCase(TestCase):
    def test_does_add_settings(self):
        class NewSettings(object):
            FOO = 'bar'
            BAR = 'baz'

        settings = mock.Mock()
        new_settings = NewSettings()
        add_settings(new_settings, settings=settings)
        self.assertEquals(getattr(settings, 'FOO', None), 'bar')
        self.assertEquals(getattr(settings, 'BAR', None), 'baz')

    def test_extra_settings_dont_get_set(self):
        class NewSettings(object):
            EXTRA_FOO = ('lulz',)

        settings = mock.Mock()
        settings.FOO = ('foo', 'bar')
        new_settings = NewSettings()
        add_settings(new_settings, settings=settings)
        self.assertFalse(settings.EXTRA_FOO.called)

    def test_extra_settings_work_on_tuple(self):
        class NewSettings(object):
            EXTRA_FOO = ('lulz',)

        settings = mock.Mock()
        settings.FOO = ('foo', 'bar')
        new_settings = NewSettings()
        add_settings(new_settings, settings=settings)
        self.assertEquals(getattr(settings, 'FOO', None), ('foo', 'bar', 'lulz'))

    def test_extra_settings_work_on_list(self):
        class NewSettings(object):
            EXTRA_FOO = ['lulz']

        settings = mock.Mock()
        settings.FOO = ['foo', 'bar']
        new_settings = NewSettings()
        add_settings(new_settings, settings=settings)
        self.assertEquals(getattr(settings, 'FOO', None), ['foo', 'bar', 'lulz'])

    def test_extra_settings_work_on_mixed_iterables(self):
        class NewSettings(object):
            EXTRA_FOO = ('lulz',)

        settings = mock.Mock()
        settings.FOO = ['foo', 'bar']
        new_settings = NewSettings()
        add_settings(new_settings, settings=settings)
        self.assertEquals(getattr(settings, 'FOO', None), ['foo', 'bar', 'lulz'])

########NEW FILE########
