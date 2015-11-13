__FILENAME__ = cli
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.cli
============
command-line entry
"""
import logging
import sys

from aminator.config import Argparser
from aminator.core import Aminator


__all__ = ('run',)
log = logging.getLogger(__name__)


def run():
    import os
    # we throw this one away, real parsing happens later
    # this is just for getting a debug flag for verbose logging.
    # to be extra sneaky, we add a --debug to the REAL parsers so it shows up in help
    # but we don't touch it there :P
    bootstrap_parser = Argparser(add_help=False)
    bootstrap_parser.add_argument('--debug', action='store_true')
    bootstrap_parser.add_argument('-e', "--environment", dest="env")
    args, argv = bootstrap_parser.parse_known_args()
    sys.argv = [sys.argv[0]] + argv
    # add -e argument back argv for when we parse the args again
    if args.env:
        sys.argv.extend(["-e",args.env])
        os.environ["AMINATOR_ENVIRONMENT"] = args.env

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    sys.exit(Aminator(debug=args.debug, envname=args.env).aminate())

def plugin_manager():
    import subprocess
    import requests
    import argparse
    import tempfile
    import tarfile
    import shutil
    import yaml
    import re
    import os

    from cStringIO import StringIO

    parser = argparse.ArgumentParser(description='Aminator plugin install utility')

    parser.add_argument('--branch', help='Which branch to pull the plugin list from. Valid options: production, testing, alpha. Default value: production',
                        default='production', choices=['production', 'testing', 'alpha'], dest='branch', metavar='branch')
    parser.add_argument('--type', help='The type of plugin to search for. Valid options: cloud, volume, blockdevice, provision, distro, finalizer, metrics',
                        choices=['cloud', 'volume', 'blockdevice', 'provision', 'distro', 'finalizer', 'metrics'], dest='type', metavar='plugin-type')
    parser.add_argument('command', help='Command to run. Valid commands: search install list', choices=['search', 'install', 'list'], metavar='command')
    parser.add_argument('name', help='Name of the plugin', metavar='name', nargs='?')
    args = parser.parse_args()

    req = requests.get('https://raw.github.com/aminator-plugins/metadata/%s/plugins.yml' % (args.branch))
    plugins = yaml.load(req.text)

    if args.command == 'search':
        if not args.name:
            print "ERROR: You must supply a keyword to search for"
            sys.exit()

        results = []
        rgx = re.compile(args.name, re.I)
        for name, data in plugins.items():
            m = rgx.search(name)
            if not m:
                for alias in data['aliases']:
                    m = rgx.search(alias)
                    if m:
                        break
            
            if m:
                if args.type and args.type != data['type']:
                    continue
                results.append("Name:        %s\nAliases:     %s\nType:        %s\nDescription: %s" % (name, ", ".join(data['aliases']), data['type'], data['description']))

        if len(results) == 0:
            print "No plugins found for keyword %s" % args.name
        else:
            print "\n----------\n".join(results)

    elif args.command == 'list':
        results = []
        for name, data in plugins.items():
            if args.type and args.type != data['type']:
                continue
            results.append("Name:        %s\nAliases:     %s\nType:        %s\nDescription: %s" % (name, ", ".join(data['aliases']), data['type'], data['description']))

        if len(results) == 0:
            print "No plugins found"
        else:
            print "\n----------\n".join(results)

    elif args.command == 'install':
        if not args.name:
            print "ERROR: You must supply a plugin name to install"
            sys.exit()

        if os.geteuid() != 0:
            print "ERROR: You must run installs as root (or through sudo)"
            sys.exit()

        rgx = re.compile('^%s$' % args.name, re.I)
        plugin = None

        for name, data in plugins.items():
            m = rgx.match(name)
            if not m:
                for alias in data['aliases']:
                    m = rgx.match(alias)
                    if m:
                        plugin = data
                        break
            else:
                plugin = data
        
        if not plugin:
            print "Unable to find a plugin named %s. You should use the search to find the correct name or alias for the plugin you want to install" % args.name
            sys.exit()
        else:
            url = 'https://github.com/aminator-plugins/%s/archive/%s.tar.gz' % (plugin['repo_name'], plugin['branch']) 
            print "Downloading latest version of %s from %s" % (args.name, url)
            req = requests.get(url, stream=True)

            tar = tarfile.open(mode="r:*", fileobj=StringIO(req.raw.read()))

            tmpdir = tempfile.mkdtemp()
            tar.extractall(path=tmpdir)

            install_path = os.path.join(tmpdir, "%s-%s" % (plugin['repo_name'], plugin['branch']))
            exe = subprocess.Popen([sys.executable, 'setup.py', 'install'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=install_path)
            out, err = exe.communicate()
            if exe.returncode > 0:
                outf = open(os.path.join(tmpdir, "install.log"), 'w')
                outf.write(out)
                outf.close()

                errf = open(os.path.join(tmpdir, "install.err"), 'w')
                errf.write(err)
                errf.close()

                print "Plugin installation failed. You should look at install.log and install.err in the installation folder, %s, for the cause of the failure" % tmpdir
            else:
                print "%s plugin installed successfully, removing temp dir %s" % (args.name, tmpdir)
                shutil.rmtree(tmpdir)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.config
===============
aminator configuration, argument handling, and logging setup
"""
import argparse
import logging
import os
import sys
from copy import deepcopy
from datetime import datetime

from aminator.util import randword
try:
    from logging.config import dictConfig
except ImportError:
    # py26
    from logutils.dictconfig import dictConfig

import bunch
from pkg_resources import resource_string, resource_exists

try:
    from yaml import CLoader as Loader # pylint: disable=redefined-outer-name
except ImportError:
    from yaml import Loader

import aminator


__all__ = ()
log = logging.getLogger(__name__)
_action_registries = argparse.ArgumentParser()._registries['action']

RSRC_PKG = 'aminator'
RSRC_DEFAULT_CONF_DIR = 'default_conf'
RSRC_DEFAULT_CONFS = {
    'main': os.path.join(RSRC_DEFAULT_CONF_DIR, 'aminator.yml'),
    'logging': os.path.join(RSRC_DEFAULT_CONF_DIR, 'logging.yml'),
    'environments': os.path.join(RSRC_DEFAULT_CONF_DIR, 'environments.yml'),
}


def init_defaults(argv=None, debug=False):
    argv = argv or sys.argv[1:]
    config = Config.from_defaults()
    config = config.dict_merge(config, Config.from_files(config.config_files.main,
                                                         config.config_root))
    main_parser = Argparser(argv=argv, description='Aminator: bringing AMIs to life', add_help=False,
                            argument_default=argparse.SUPPRESS)
    config.logging = LoggingConfig.from_defaults()
    config.logging = config.dict_merge(config.logging, LoggingConfig.from_files(config.config_files.logging,
                                                                                config.config_root))
    config.environments = EnvironmentConfig.from_defaults()
    config.environments = config.dict_merge(config.environments,
                                            EnvironmentConfig.from_files(config.config_files.environments,
                                                                         config.config_root))
    default_metrics = getattr(config.environments, "metrics", "logger")
    for env in config.environments:
        if isinstance(config.environments[env], dict):
            if "metrics" not in config.environments[env]:
                config.environments[env]["metrics"] = default_metrics

    if config.logging.base.enabled:
        dictConfig(config.logging.base.config.toDict())
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers: handler.setLevel(logging.DEBUG)

    add_base_arguments(parser=main_parser, config=config)
    plugin_parser = Argparser(argv=argv, add_help=True, argument_default=argparse.SUPPRESS,
                              parents=[main_parser])
    log.info('Aminator {0} default configuration loaded'.format(aminator.__version__))
    return config, plugin_parser


class Config(bunch.Bunch):
    """ Base config class """
    resource_package = RSRC_PKG
    resource_default = RSRC_DEFAULT_CONFS['main']

    @classmethod
    def from_yaml(cls, yaml_data, Loader=Loader, *args, **kwargs): # pylint: disable=redefined-outer-name
        return cls(cls.fromYAML(yaml_data, Loader=Loader, *args, **kwargs))

    @classmethod
    def from_pkg_resource(cls, namespace, name, *args, **kwargs):
        config = resource_string(namespace, name)
        if len(config):
            return cls.from_yaml(config, *args, **kwargs)
        else:
            log.warn('Resource for {0}.{1} is empty, returning empty config'.format(namespace, name))

    @classmethod
    def from_file(cls, yaml_file, *args, **kwargs):
        if not os.path.exists(yaml_file):
            log.warn('File {0} not found, returning empty config'.format(yaml_file))
            return cls()
        with open(yaml_file) as f:
            _config = cls.from_yaml(f, *args, **kwargs)
        return _config

    @classmethod
    def from_files(cls, files, config_root="", *args, **kwargs):
        _files = [os.path.expanduser(filename) for filename in files]
        _files = [(x if x.startswith('/') else os.path.join(config_root, x)) for x in _files]
        _files = [filename for filename in _files if os.path.exists(filename)]
        _config = cls()
        for filename in _files:
            _new = cls.from_file(filename, *args, **kwargs)
            _config = cls.dict_merge(_config, _new)
        return _config

    @classmethod
    def from_defaults(cls, namespace=None, name=None, *args, **kwargs):
        if namespace and name and resource_exists(namespace, name):
            _namespace = namespace
            _name = name
        elif (cls.resource_package and cls.resource_default
              and resource_exists(cls.resource_package, cls.resource_default)):
            _namespace = cls.resource_package
            _name = cls.resource_default
        else:
            log.warn('No class resource attributes and no namespace info, returning empty config')
            return cls(*args, **kwargs)
        return cls.from_pkg_resource(_namespace, _name, *args, **kwargs)

    @staticmethod
    def dict_merge(old, new):
        res = deepcopy(old)
        for k, v in new.iteritems():
            if k in res and isinstance(res[k], dict):
                res[k] = Config.dict_merge(res[k], v)
            else:
                res[k] = deepcopy(v)
        return res

    def __call__(self):
        return


class LoggingConfig(Config):
    """ Logging config class """
    resource_default = RSRC_DEFAULT_CONFS['logging']


def configure_datetime_logfile(config, handler):
    try:
        filename_format = config.logging[handler]['filename_format']
    except KeyError:
        log.error('filename_format not configured for handler {0}'.format(handler))
        return

    try:
        pkg = "{0}-{1}".format(os.path.basename(config.context.package.arg), randword(6))
        filename = os.path.join(config.log_root, filename_format.format(pkg, datetime.utcnow()))
    except IndexError:
        log.exception("missing replacement fields in {0}'s filename_format")

    # find handler amongst all the loggers and reassign the filename/stream
    for h in [x for l in logging.root.manager.loggerDict for x in logging.getLogger(l).handlers] + logging.root.handlers:
        if getattr(h, 'name', '') == handler:
            assert isinstance(h, logging.FileHandler)
            h.stream.close()
            h.baseFilename = filename
            h.stream = open(filename, 'a')
            url_template = config.logging[handler].get('web_log_url_template', False)
            if url_template:
                url_attrs = config.context.web_log.toDict()
                url_attrs['logfile'] = os.path.basename(filename)
                url = url_template.format(**url_attrs)
                log.info('Detailed {0} output to {1}'.format(handler, url))
            else:
                log.info('Detailed {0} output to {1}'.format(handler, filename))
            break
    else:
        log.error('{0} handler not found.'.format(handler))


class EnvironmentConfig(Config):
    """ Environment config class """
    resource_default = RSRC_DEFAULT_CONFS['environments']


class PluginConfig(Config):
    """ Plugin config class """
    resource_package = resource_default = None

    @classmethod
    def from_defaults(cls, namespace=None, name=None, *args, **kwargs):
        if not all((namespace, name)):
            raise ValueError('Plugins must specify a namespace and name')
        resource_file = '.'.join((namespace, name, 'yml'))
        resource_path = os.path.join(RSRC_DEFAULT_CONF_DIR, resource_file)
        return super(PluginConfig, cls).from_defaults(namespace=namespace, name=resource_path, *args, **kwargs)


class Argparser(object):
    """ Argument parser class. Holds the keys to argparse """
    def __init__(self, argv=None, *args, **kwargs):
        self._argv = argv or sys.argv[1:]
        self._parser = argparse.ArgumentParser(*args, **kwargs)

    def add_config_arg(self, *args, **kwargs):
        config = kwargs.pop('config', Config())
        _action = kwargs.pop('action', None)
        action = conf_action(config, _action)
        kwargs['action'] = action
        return self.add_argument(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self._parser, attr)


def add_base_arguments(parser, config):
    parser.add_config_arg('arg', metavar='package_spec', config=config.context.package,
                          help='package to aminate. A string resolvable by the native package manager or'
                          ' a file system path or http url to the package file.')
    parser.add_config_arg('-e', '--environment', config=config.context,
                          help='The environment configuration for amination')
    parser.add_config_arg('--preserve-on-error', action='store_true', config=config.context,
                          help='For Debugging. Preserve build chroot on error')
    parser.add_config_arg('--verify-https', action='store_true', config=config.context,
                          help='Specify if one wishes for plugins to verify SSL certs when hitting https URLs')
    parser.add_argument('--version', action='version', version='%(prog)s {0}'.format(aminator.__version__))
    parser.add_argument('--debug', action='store_true', help='Verbose debugging output')


def conf_action(config, action=None):
    """
    class factory function that dynamically creates special ConfigAction
    forms of argparse actions, injecting a config object into the namespace
    """
    action_subclass = _action_registries[action]
    action_class_name = 'ConfigAction_{0}'.format(action_subclass.__name__)

    def _action_call(self, parser, namespace, values, option_string=None):
        return super(self.__class__, self).__call__(parser, config, values, option_string)

    action_class = type(action_class_name, (action_subclass, ), {'__call__': _action_call})
    return action_class

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.core
=============
aminator core amination logic
"""
import logging
import os

from aminator.config import init_defaults, configure_datetime_logfile
from aminator.environment import Environment
from aminator.plugins import PluginManager
from aminator.util.linux import mkdir_p

__all__ = ('Aminator', )
log = logging.getLogger(__name__)


class Aminator(object):
    def __init__(self, config=None, parser=None, plugin_manager=PluginManager, environment=Environment, debug=False, envname=None):
        log.info('Aminator starting...')
        if not all((config, parser)):
            log.debug('Loading default configuration')
            config, parser = init_defaults(debug=debug)
        self.config = config
        self.parser = parser
        log.debug('Configuration loaded')
        if not envname:
            envname = self.config.environments.default
        self.plugin_manager = plugin_manager(self.config, self.parser, plugins=self.config.environments[envname])
        log.debug('Plugins loaded')
        self.parser.parse_args()
        log.debug('Args parsed')

        os.environ["AMINATOR_PACKAGE"] = self.config.context.package.arg

        log.debug('Creating initial folder structure if needed')
        mkdir_p(self.config.log_root)
        mkdir_p(os.path.join(self.config.aminator_root, self.config.lock_dir))
        mkdir_p(os.path.join(self.config.aminator_root, self.config.volume_dir))

        if self.config.logging.aminator.enabled:
            log.debug('Configuring per-package logging')
            configure_datetime_logfile(self.config, 'aminator')

        self.environment = environment()

    def aminate(self):
        with self.environment(self.config, self.plugin_manager) as env:
            ok = env.provision()
            if ok:
                log.info('Amination complete!')
        return 0 if ok else 1

########NEW FILE########
__FILENAME__ = environment
 # -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.environment
====================
The orchestrator
"""
import logging
import yaml

log = logging.getLogger(__name__)


class Environment(object):
    """ The environment and orchetrator for amination """
    # TODO: given that this represents a workflow, this should possibly be an entry point

    def _attach_plugins(self):
        log.debug('Attaching plugins to environment {0}'.format(self._name))
        env_config = self._config.environments[self._name]
        for kind, name in env_config.iteritems():
            log.debug('Attaching plugin {0} for {1}'.format(name, kind))
            plugin = self._plugin_manager.find_by_kind(kind, name)
            setattr(self, kind, plugin.obj)
            log.debug('Attached: {0}'.format(getattr(self, kind)))

        kind = "metrics"
        if not getattr(self, kind, None):
            name = self._config.environments.get(kind, "logger")
            plugin = self._plugin_manager.find_by_kind(kind, name)
            setattr(self, kind, plugin.obj)

        log.debug("============= BEGIN YAML representation of loaded configs ===============")
        log.debug(yaml.dump(self._config))
        log.debug("============== END YAML representation of loaded configs ================")

    def provision(self):
        log.info('Beginning amination! Package: {0}'.format(self._config.context.package.arg))
        with self.metrics:                                                     # pylint: disable=no-member
            with self.cloud as cloud:                                          # pylint: disable=no-member
                with self.finalizer(cloud) as finalizer:                       # pylint: disable=no-member
                    with self.volume(self.cloud, self.blockdevice) as volume:  # pylint: disable=no-member
                        with self.distro(volume) as distro:                    # pylint: disable=no-member
                            success = self.provisioner(distro).provision()     # pylint: disable=no-member
                            if not success:
                                log.critical('Provisioning failed!')
                                return False
                        success = finalizer.finalize()
                        if not success:
                            log.critical('Finalizing failed!')
                            return False
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, trc):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        return False

    def __call__(self, config, plugin_manager):
        self._config = config
        self._plugin_manager = plugin_manager
        self._name = self._config.context.get('environment', self._config.environments.default)
        self._config.context['environment'] = self._name
        self._attach_plugins()
        return self

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.exceptions
===================
aminator's exceptions
"""


class AminateException(Exception):
    """ Base Aminator Exception """
    pass


class DeviceException(AminateException):
    """ Errors during device allocation """
    pass


class VolumeException(AminateException):
    """ Errors during volume allocation """
    pass


class ArgumentError(AminateException):
    """ Errors during argument parsing"""


class ProvisionException(AminateException):
    """ Errors during provisioning """


class FinalizerException(AminateException):
    """ Errors during finalizing """

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.base
=====================
Base class(es) for plugin implementations
"""
import logging
import os

from aminator.config import PluginConfig


__all__ = ()
log = logging.getLogger(__name__)


class BasePlugin(object):
    """ Base class for plugins """
    _entry_point = None
    _name = None
    _enabled = True

    def __init__(self):
        if self._entry_point is None:
            raise AttributeError('Plugins must declare their entry point namespace in a _entry_point class attribute')
        if self._name is None:
            raise AttributeError('Plugins must declare their entry point name in a _name class attribute')

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, enable):
        self._enabled = enable

    @property
    def entry_point(self):
        return self._entry_point

    @property
    def name(self):
        return self._name

    @property
    def full_name(self):
        return '{0}.{1}'.format(self.entry_point, self.name)

    def configure(self, config, parser):
        """ Configure the plugin and contribute to command line args """
        log.debug("Configuring plugin {0} for entry point {1}".format(self.name, self.entry_point))
        self._config = config
        self._parser = parser
        self.load_plugin_config()
        if self.enabled:
            self.add_plugin_args()

    def add_plugin_args(self):
        pass

    def load_plugin_config(self):
        entry_point = self.entry_point
        name = self.name
        key = '.'.join((entry_point, name))

        if self._config.plugins.config_root.startswith('~'):
            plugin_conf_dir = os.path.expanduser(self._config.plugins.config_root)

        elif self._config.plugins.config_root.startswith('/'):
            plugin_conf_dir = self._config.plugins.config_root

        else:
            plugin_conf_dir = os.path.join(self._config.config_root,
                                           self._config.plugins.config_root)

        plugin_conf_files = (
            os.path.join(plugin_conf_dir, '.'.join((key, 'yml'))),
        )

        self._config.plugins[key] = PluginConfig.from_defaults(entry_point, name)
        self._config.plugins[key] = PluginConfig.dict_merge(self._config.plugins[key],
                                                            PluginConfig.from_files(plugin_conf_files))
        # allow plugins to be disabled by configuration. Especially important in cases where command line args conflict
        self.enabled = self._config.plugins[key].get('enabled', True)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.blockdevice.base
=================================
Base class(es) for block device manager plugins
"""
import abc
import logging

from aminator.plugins.base import BasePlugin


__all__ = ('BaseBlockDevicePlugin',)
log = logging.getLogger(__name__)


class BaseBlockDevicePlugin(BasePlugin):
    """
    BlockDevicePlugins are context managers and as such, need to implement the context manager protocol
    """
    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.blockdevice'

    @abc.abstractmethod
    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, typ, val, trc):
        if typ: log.exception("Exception: {0}: {1}".format(typ.__name__,val))
        return False

    def __call__(self, cloud):
        """
        By default, BlockDevicePlugins are called using
        with blockdeviceplugin(cloud) as device:
            pass
        Override if need be
        """
        self.cloud = cloud
        return self

########NEW FILE########
__FILENAME__ = linux
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.blockdevice.linux
==================================
basic linux block device manager
"""
import fcntl
import os
import logging
from collections import namedtuple

from aminator.exceptions import DeviceException
from aminator.plugins.blockdevice.base import BaseBlockDevicePlugin
from aminator.util.linux import flock, locked, native_device_prefix
from aminator.util.metrics import raises

__all__ = ('LinuxBlockDevicePlugin',)
log = logging.getLogger(__name__)


BlockDevice = namedtuple('BlockDevice', 'node handle')


class LinuxBlockDevicePlugin(BaseBlockDevicePlugin):
    _name = 'linux'

    def configure(self, config, parser):
        super(LinuxBlockDevicePlugin, self).configure(config, parser)

        block_config = self._config.plugins[self.full_name]

        if self._config.lock_dir.startswith(('/', '~')):
            self._lock_dir = os.path.expanduser(self._config.lock_dir)
        else:
            self._lock_dir = os.path.join(self._config.aminator_root, self._config.lock_dir)

        self._lock_file = self.__class__.__name__

        majors = block_config.device_letters
        self._device_prefix = native_device_prefix(block_config.device_prefixes)
        device_format = '/dev/{0}{1}{2}'

        self._allowed_devices = [device_format.format(self._device_prefix, major, minor)
                                 for major in majors
                                 for minor in xrange(1, 16)]

    def __enter__(self):
        with flock(self._lock_file):
            dev = self.find_available_dev()
        self._dev = dev
        return self._dev.node

    def __exit__(self, typ, val, trc):
        if typ: log.exception("Exception: {0}: {1}".format(typ.__name__,val))
        fcntl.flock(self._dev.handle, fcntl.LOCK_UN)
        self._dev.handle.close()
        return False

    @raises("aminator.blockdevice.linux.find_available_dev.error")
    def find_available_dev(self):
        log.info('Searching for an available block device')
        for dev in self._allowed_devices:
            log.debug('checking if device {0} is available'.format(dev))
            device_lock = os.path.join(self._lock_dir, os.path.basename(dev))
            if os.path.exists(dev):
                log.debug('{0} exists, skipping'.format(dev))
                continue
            elif locked(device_lock):
                log.debug('{0} is locked, skipping'.format(dev))
                continue
            elif self.cloud.is_stale_attachment(dev, self._device_prefix):
                log.debug('{0} is stale, skipping'.format(dev))
                continue
            else:
                log.debug('Device {0} looks good, attempting to lock.'.format(dev))
                fh = open(device_lock, 'a')
                fcntl.flock(fh, fcntl.LOCK_EX)
                log.debug('device locked. fh = {0}, dev = {1}'.format(str(fh), dev))
                log.info('Block device {0} allocated'.format(dev))
                return BlockDevice(dev, fh)
        raise DeviceException('Exhausted all devices, none free')

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.blockdevice.manager
====================================
Block device plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class BlockDevicePluginManager(BasePluginManager):
    """ BlockDevice Plugin Manager """
    _entry_point = 'aminator.plugins.blockdevice'

    @property
    def entry_point(self):
        return self._entry_point

########NEW FILE########
__FILENAME__ = null
# -*- coding: utf-8 -*-

#
#
#  Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.blockdevice.null
==================================
null block device manager
"""
import logging

from aminator.plugins.blockdevice.base import BaseBlockDevicePlugin

__all__ = ('NullBlockDevicePlugin',)
log = logging.getLogger(__name__)


class NullBlockDevicePlugin(BaseBlockDevicePlugin):
    _name = 'null'

    def __enter__(self):
        return '/dev/null'

    def __exit__(self, typ, val, trc):
        if typ: log.exception("Exception: {0}: {1}".format(typ.__name__,val))
        return False

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.cloud.base
===========================
Base class(es) for cloud plugins
"""
import abc
import logging

from aminator.plugins.base import BasePlugin


__all__ = ('BaseCloudPlugin',)
log = logging.getLogger(__name__)


class BaseCloudPlugin(BasePlugin):
    """
    Cloud plugins are context managers to ensure cleanup. They are the interface to cloud objects and operations.
    """

    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.cloud'

    _connection = None

    @abc.abstractmethod
    def connect(self):
        """ Store the resultant connection in the _connection class attribute """

    @abc.abstractmethod
    def allocate_base_volume(self, tag=True):
        """ create a volume object from the base/foundation volume """

    @abc.abstractmethod
    def attach_volume(self, blockdevice, tag=True):
        """ Instructs the cloud provider to attach some sort of volume to the instance """

    @abc.abstractmethod
    def detach_volume(self, blockdevice):
        """ Instructs the cloud provider to detach a given volume from the instance """

    @abc.abstractmethod
    def delete_volume(self):
        """ destroys a volume """

    @abc.abstractmethod
    def snapshot_volume(self, description=None):
        """ creates a snapshot from the attached volume """

    @abc.abstractmethod
    def is_volume_attached(self, blockdevice):
        """ volume attachment status """

    @abc.abstractmethod
    def is_stale_attachment(self, dev, prefix):
        """ checks to see if a given device is a stale attachment """

    @abc.abstractmethod
    def attached_block_devices(self, prefix):
        """
        list any block devices attached to the aminator instance.
        helps blockdevice plugins allocate an os device node
        """

    @abc.abstractmethod
    def add_tags(self, resource_type):
        """ consumes tags and applies them to objects """

    @abc.abstractmethod
    def register_image(self, *args, **kwargs):
        """ Instructs the cloud provider to register a finalized image for launching """

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, typ, val, trc):
        if typ: log.exception("Exception: {0}: {1}".format(typ.__name__,val))
        return False

########NEW FILE########
__FILENAME__ = ec2
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.cloud.ec2
==========================
ec2 cloud provider
"""
import logging
from time import sleep

from boto.ec2 import connect_to_region, EC2Connection
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from boto.ec2.image import Image
from boto.ec2.instance import Instance
from boto.ec2.volume import Volume
from boto.exception import EC2ResponseError
from boto.utils import get_instance_metadata
from decorator import decorator
from os import environ

from aminator.config import conf_action
from aminator.exceptions import FinalizerException, VolumeException
from aminator.plugins.cloud.base import BaseCloudPlugin
from aminator.util import retry
from aminator.util.linux import device_prefix, native_block_device, os_node_exists
from aminator.util.metrics import timer, raises, succeeds, lapse


__all__ = ('EC2CloudPlugin',)
log = logging.getLogger(__name__)


def registration_retry(ExceptionToCheck=(EC2ResponseError,), tries=3, delay=1, backoff=1, logger=None):
    """
    a slightly tweaked form of aminator.util.retry for handling retries on image registration
    """
    if logger is None:
        logger = log

    @decorator
    def _retry(f, *args, **kwargs):
        _tries, _delay = tries, delay
        total_tries = _tries
        args, kwargs = args, kwargs
        while _tries > 0:
            try:
                return f(*args, **kwargs)
            except ExceptionToCheck, e:
                if e.error_code == 'InvalidAMIName.Duplicate':
                    log.debug('Duplicate AMI Name {0}, retrying'.format(kwargs['name']))
                    attempt = abs(_tries - (total_tries + 1))
                    kwargs['name'] = kwargs.pop('name') + str(attempt)
                    log.debug('Trying name {0}'.format(kwargs['name']))
                    sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
                else:
                    for (code, msg) in e.errors:
                        log.critical('EC2ResponseError: {0}: {1}.'.format(code, msg))
                        return False
        log.critical('Failed to register AMI')
        return False
    return _retry


class EC2CloudPlugin(BaseCloudPlugin):
    _name = 'ec2'

    def add_metrics(self, metric_base_name, cls, func_name):
        newfunc = succeeds("{0}.count".format(metric_base_name), self)(
            raises("{0}.error".format(metric_base_name), self)(
                timer("{0}.duration".format(metric_base_name), self)(
                    getattr(cls,func_name)
                )
            )
        )
        setattr(cls, func_name, newfunc)

    def __init__(self):
        super(EC2CloudPlugin,self).__init__()
        # wrap each of the functions so we can get timer and error metrics
        for ec2func in ["create_volume", "create_tags", "register_image", "get_all_images"]:
            self.add_metrics("aminator.cloud.ec2.connection.{0}".format(ec2func), EC2Connection, ec2func)
        for volfunc in ["add_tag", "attach", "create_snapshot", "delete", "detach", "update"]:
            self.add_metrics("aminator.cloud.ec2.volume.{0}".format(volfunc), Volume, volfunc)
        for imgfunc in ["update"]:
            self.add_metrics("aminator.cloud.ec2.image.{0}".format(imgfunc), Image, imgfunc)
        for insfunc in ["update"]:
            self.add_metrics("aminator.cloud.ec2.instance.{0}".format(insfunc), Instance, insfunc)

    def add_plugin_args(self, *args, **kwargs):
        context = self._config.context
        base_ami = self._parser.add_argument_group(title='Base AMI', description='EITHER AMI id OR name, not both!')
        base_ami_mutex = base_ami.add_mutually_exclusive_group(required=True)
        base_ami_mutex.add_argument('-b', '--base-ami-name', dest='base_ami_name',
                                    action=conf_action(config=context.ami),
                                    help='The name of the base AMI used in provisioning')
        base_ami_mutex.add_argument('-B', '--base-ami-id', dest='base_ami_id',
                                    action=conf_action(config=context.ami),
                                    help='The id of the base AMI used in provisioning')
        cloud = self._parser.add_argument_group(title='EC2 Options', description='EC2 Connection Information')
        cloud.add_argument('-r', '--region', dest='region', help='EC2 region (default: us-east-1)',
                           action=conf_action(config=context.cloud))
        cloud.add_argument('--boto-secure', dest='is_secure',  help='Connect via https',
                           action=conf_action(config=context.cloud, action='store_true'))
        cloud.add_argument('--boto-debug', dest='boto_debug', help='Boto debug output',
                           action=conf_action(config=context.cloud, action='store_true'))

    def configure(self, config, parser):
        super(EC2CloudPlugin, self).configure(config, parser)
        host = config.context.web_log.get('host', False)
        if not host:
            md = get_instance_metadata()
            pub, ipv4 = 'public-hostname', 'local-ipv4'
            config.context.web_log['host'] = md[pub] if pub in md else md[ipv4]

    def connect(self, **kwargs):
        if self._connection:
            log.warn('Already connected to EC2')
        else:
            log.info('Connecting to EC2')
            self._connect(**kwargs)

    def _connect(self, **kwargs):
        cloud_config = self._config.plugins[self.full_name]
        context = self._config.context
        self._instance_metadata = get_instance_metadata()
        instance_region = self._instance_metadata['placement']['availability-zone'][:-1]
        region = kwargs.pop('region',
                            context.get('region',
                                        cloud_config.get('region',
                                                         instance_region)))
        log.debug('Establishing connection to region: {0}'.format(region))

        context.cloud.setdefault('boto_debug', False)
        if context.cloud.boto_debug:
            from aminator.config import configure_datetime_logfile
            configure_datetime_logfile(self._config, 'boto')
            kwargs['debug'] = 1
            log.debug('Boto debug logging enabled')
        else:
            logging.getLogger('boto').setLevel(logging.INFO)
        if 'is_secure' not in kwargs:
            kwargs['is_secure'] = context.get('is_secure',
                                              cloud_config.get('is_secure',
                                                               True))
        self._connection = connect_to_region(region, **kwargs)
        log.info('Aminating in region {0}'.format(region))

    def allocate_base_volume(self, tag=True):
        cloud_config = self._config.plugins[self.full_name]
        context = self._config.context

        self._volume = Volume(connection=self._connection)

        rootdev = context.base_ami.block_device_mapping[context.base_ami.root_device_name]
        self._volume.id = self._connection.create_volume(size=rootdev.size, zone=self._instance.placement,
                                                         snapshot=rootdev.snapshot_id).id
        if not self._volume_available():
            log.critical('{0}: unavailable.')
            return False

        if tag:
            tags = {
                'purpose': cloud_config.get('tag_ami_purpose', 'amination'),
                'status': 'busy',
                'ami': context.base_ami.id,
                'ami-name': context.base_ami.name,
                'arch': context.base_ami.architecture,
            }
            self._connection.create_tags([self._volume.id], tags)
        self._volume.update()
        log.debug('Volume {0} created'.format(self._volume.id))

    @retry(VolumeException, tries=2, delay=1, backoff=2, logger=log)
    def attach_volume(self, blockdevice, tag=True):
        self.allocate_base_volume(tag=tag)
        # must do this as amazon still wants /dev/sd*
        ec2_device_name = blockdevice.replace('xvd', 'sd')
        log.debug('Attaching volume {0} to {1}:{2}({3})'.format(self._volume.id, self._instance.id, ec2_device_name,
                                                                blockdevice))
        self._volume.attach(self._instance.id, ec2_device_name)
        if not self.is_volume_attached(blockdevice):
            log.debug('{0} attachment to {1}:{2}({3}) timed out'.format(self._volume.id, self._instance.id,
                                                                        ec2_device_name, blockdevice))
            self._volume.add_tag('status', 'used')
            # trigger a retry
            raise VolumeException('Timed out waiting for {0} to attach to {1}:{2}'.format(self._volume.id,
                                                                                          self._instance.id,
                                                                                          blockdevice))
        log.debug('Volume {0} attached to {1}:{2}'.format(self._volume.id, self._instance.id, blockdevice))

    def is_volume_attached(self, blockdevice):
        try:
            self._volume_attached(blockdevice)
        except VolumeException:
            log.debug('Timed out waiting for volume {0} to attach to {1}:{2}'.format(self._volume.id,
                                                                                     self._instance.id, blockdevice))
            return False
        return True

    @retry(VolumeException, tries=10, delay=1, backoff=2, logger=log)
    def _volume_attached(self, blockdevice):
        status = self._volume.update()
        if status != 'in-use':
            raise VolumeException('Volume {0} not yet attached to {1}:{2}'.format(self._volume.id,
                                                                                  self._instance.id, blockdevice))
        elif not os_node_exists(blockdevice):
            raise VolumeException('{0} does not exist yet.'.format(blockdevice))
        else:
            return True

    def snapshot_volume(self, description=None):
        context = self._config.context
        if not description:
            description = context.snapshot.get('description', '')
        log.debug('Creating snapshot with description {0}'.format(description))
        self._snapshot = self._volume.create_snapshot(description)
        if not self._snapshot_complete():
            log.critical('Failed to create snapshot')
            return False
        else:
            log.debug('Snapshot complete. id: {0}'.format(self._snapshot.id))
            return True

    def _state_check(self, obj, state):
        obj.update()
        classname = obj.__class__.__name__
        if classname in ('Snapshot', 'Volume'):
            return obj.status == state
        else:
            return obj.state == state

    @retry(VolumeException, tries=600, delay=0.5, backoff=1.5, logger=log)
    def _wait_for_state(self, resource, state):
        if self._state_check(resource, state):
            log.debug('{0} reached state {1}'.format(resource.__class__.__name__, state))
            return True
        else:
            raise VolumeException('Timed out waiting for {0} to get to {1}({2})'.format(resource.id,
                                                                                     state,
                                                                                     resource.status))
    @lapse("aminator.cloud.ec2.ami_available.duration")
    def _ami_available(self):
        return self._wait_for_state(self._ami, 'available')

    @lapse("aminator.cloud.ec2.snapshot_completed.duration")
    def _snapshot_complete(self):
        return self._wait_for_state(self._snapshot, 'completed')

    @lapse("aminator.cloud.ec2.volume_available.duration")
    def _volume_available(self):
        return self._wait_for_state(self._volume, 'available')

    def detach_volume(self, blockdevice):
        log.debug('Detaching volume {0} from {1}'.format(self._volume.id, self._instance.id))
        self._volume.detach()
        if not self._volume_detached(blockdevice):
            raise VolumeException('Time out waiting for {0} to detach from {1]'.format(self._volume.id,
                                                                                       self._instance.id))
        log.debug('Successfully detached volume {0} from {1}'.format(self._volume.id, self._instance.id))

    @retry(VolumeException, tries=7, delay=1, backoff=2, logger=log)
    def _volume_detached(self, blockdevice):
        status = self._volume.update()
        if status != 'available':
            raise VolumeException('Volume {0} not yet detached from {1}'.format(self._volume.id, self._instance.id))
        elif os_node_exists(blockdevice):
            raise VolumeException('Device node {0} still exists'.format(blockdevice))
        else:
            return True

    def delete_volume(self):
        log.debug('Deleting volume {0}'.format(self._volume.id))
        self._volume.delete()
        return self._volume_deleted()

    def _volume_deleted(self):
        try:
            self._volume.update()
        except EC2ResponseError, e:
            if e.code == 'InvalidVolume.NotFound':
                log.debug('Volume {0} successfully deleted'.format(self._volume.id))
                return True
            return False

    def is_stale_attachment(self, dev, prefix):
        log.debug('Checking for stale attachment. dev: {0}, prefix: {1}'.format(dev, prefix))
        if dev in self.attached_block_devices(prefix) and not os_node_exists(dev):
            log.debug('{0} is stale, rejecting'.format(dev))
            return True
        log.debug('{0} not stale, using'.format(dev))
        return False

    @registration_retry(tries=3, delay=1, backoff=1)
    def _register_image(self, **ami_metadata):
        context = self._config.context
        ami = Image(connection=self._connection)
        ami.id = self._connection.register_image(**ami_metadata)
        if ami.id is None:
            return False
        else:
            while True:
                # spin until Amazon recognizes the AMI ID it told us about
                try:
                    sleep(2)
                    ami.update()
                    break
                except EC2ResponseError, e:
                    if e.error_code == 'InvalidAMIID.NotFound':
                        log.debug('{0} not found, retrying'.format(ami.id))
                    else:
                        raise e
            log.info('AMI registered: {0} {1}'.format(ami.id, ami.name))
            context.ami.image = self._ami = ami
            return True

    def register_image(self, *args, **kwargs):
        context = self._config.context
        vm_type = context.ami.get("vm_type", "paravirtual")
        if 'manifest' in kwargs:
            ami_metadata = {
                'name': context.ami.name,
                'description': context.ami.description,
                'image_location': kwargs['manifest'],
                'virtualization_type': vm_type
            }
        else:
            # args will be [block_device_map, root_block_device]
            block_device_map, root_block_device = args[:2]
            bdm = self._make_block_device_map(block_device_map, root_block_device)
            ami_metadata = {
                'name': context.ami.name,
                'description': context.ami.description,
                'block_device_map': bdm,
                'root_device_name': root_block_device,
                'kernel_id': context.base_ami.kernel_id,
                'ramdisk_id': context.base_ami.ramdisk_id,
                'architecture': context.base_ami.architecture,
                'virtualization_type': vm_type
            }
            if vm_type == "hvm":
                del ami_metadata['kernel_id']
                del ami_metadata['ramdisk_id']

        if not self._register_image(**ami_metadata):
            return False
        return True

    def _make_block_device_map(self, block_device_map, root_block_device):
        bdm = BlockDeviceMapping(connection=self._connection)
        bdm[root_block_device] = BlockDeviceType(snapshot_id=self._snapshot.id,
                                                 delete_on_termination=True)
        for (os_dev, ec2_dev) in block_device_map:
            bdm[os_dev] = BlockDeviceType(ephemeral_name=ec2_dev)
        return bdm

    @retry(FinalizerException, tries=3, delay=1, backoff=2, logger=log)
    def add_tags(self, resource_type):
        context = self._config.context

        log.debug('Adding tags for resource type {0}'.format(resource_type))

        tags = context[resource_type].get('tags', None)
        if not tags:
            log.critical('Unable to locate tags for {0}'.format(resource_type))
            return False

        instance_var = '_' + resource_type
        try:
            instance = getattr(self, instance_var)
        except Exception:
            log.exception('Unable to find local instance var {0}'.format(instance_var))
            log.critical('Tagging failed')
            return False
        else:
            try:
                self._connection.create_tags([instance.id], tags)
            except EC2ResponseError:
                log.exception('Error creating tags for resource type {0}, id {1}'.format(resource_type, instance.id))
                raise FinalizerException('Error creating tags for resource type {0}, id {1}'.format(resource_type,
                                                                                                    instance.id))
            else:
                log.debug('Successfully tagged {0}({1})'.format(resource_type, instance.id))
                instance.update()
                tagstring = '\n'.join('='.join((key, val)) for (key, val) in tags.iteritems())
                log.debug('Tags: \n{0}'.format(tagstring))
                return True

    def attached_block_devices(self, prefix):
        log.debug('Checking for currently attached block devices. prefix: {0}'.format(prefix))
        self._instance.update()
        if device_prefix(self._instance.block_device_mapping.keys()[0]) != prefix:
            return dict((native_block_device(dev, prefix), mapping)
                        for (dev, mapping) in self._instance.block_device_mapping.iteritems())
        return self._instance.block_device_mapping

    def _resolve_baseami(self):
        log.info('Resolving base AMI')
        context = self._config.context
        cloud_config = self._config.plugins[self.full_name]
        try:
            ami_id = context.ami.get('base_ami_name', cloud_config.get('base_ami_name', None))
            if ami_id is None:
                ami_id = context.ami.get('base_ami_id', cloud_config.get('base_ami_id', None))
                if ami_id is None:
                    raise RuntimeError('Must configure or provide either a base ami name or id')
                else:
                    context.ami['ami_id'] = ami_id
                    log.info('looking up base AMI with ID {0}'.format(ami_id))
                    baseami = self._connection.get_all_images(image_ids=[ami_id])[0]
            else:
                log.info('looking up base AMI with name {0}'.format(ami_id))
                baseami = self._connection.get_all_images(filters={'name': ami_id})[0]
        except IndexError:
            raise RuntimeError('Could not locate base AMI with identifier: {0}'.format(ami_id))
        log.info('Successfully resolved {0.name}({0.id})'.format(baseami))
        context['base_ami'] = baseami

    def __enter__(self):
        self.connect()
        self._resolve_baseami()
        self._instance = Instance(connection=self._connection)
        self._instance.id = get_instance_metadata()['instance-id']
        self._instance.update()

        
        context = self._config.context
        if context.ami.get("base_ami_name",None):
            environ["AMINATOR_BASE_AMI_NAME"] = context.ami.base_ami_name
        if context.ami.get("base_ami_id",None):
            environ["AMINATOR_BASE_AMI_ID"] = context.ami.base_ami_id

        if context.cloud.get("region", None):
            environ["AMINATOR_REGION"] = context.cloud.region

        return self

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.cloud.manager
==============================
Cloud plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class CloudPluginManager(BasePluginManager):
    """ Cloud Plugin Manager """
    _entry_point = 'aminator.plugins.cloud'

    @property
    def entry_point(self):
        return self._entry_point

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.distro.base
=================================
Base class(es) for OS distributions plugins
"""
import abc
import logging

from aminator.plugins.base import BasePlugin

__all__ = ('BaseDistroPlugin',)
log = logging.getLogger(__name__)


class BaseDistroPlugin(BasePlugin):
    """
    Distribution plugins take a volume and prepare it for provisioning.
    They are context managers to ensure resource cleanup
    """

    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.distro'

    @abc.abstractmethod
    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, trace):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        return False

    def __call__(self, mountpoint):
        self._mountpoint = mountpoint
        return self

########NEW FILE########
__FILENAME__ = debian
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.distro.debian
================================
basic debian distro
"""
import logging
import os

from aminator.plugins.distro.linux import BaseLinuxDistroPlugin


__all__ = ('DebianDistroPlugin',)
log = logging.getLogger(__name__)


class DebianDistroPlugin(BaseLinuxDistroPlugin):
    """
    DebianDistroPlugin takes the majority of its behavior from BaseLinuxDistroPlugin
    See BaseLinuxDistroPlugin for details
    """
    _name = 'debian'

    def _deactivate_provisioning_service_block(self):
        """
        Prevent packages installing in the chroot from starting
        For debian based distros, we add /usr/sbin/policy-rc.d
        """
        if not super(DebianDistroPlugin, self)._deactivate_provisioning_service_block():
            return False
        
        config = self._config.plugins[self.full_name]
        path = self._mountpoint + config.get('policy_file_path', '')
        filename = path + "/" + config.get('policy_file')

        if not os.path.isdir(path):
            log.debug("creating %s", path)
            os.makedirs(path)
            log.debug("created %s", path)

        with open(filename, 'w') as f:
            log.debug("writing %s", filename)
            f.write(config.get('policy_file_content'))
            log.debug("wrote %s", filename)

        os.chmod(filename, config.get('policy_file_mode', ''))

        return True

    def _activate_provisioning_service_block(self):
        """
        Remove policy-rc.d file so that things start when the AMI launches
        """
        if not super(DebianDistroPlugin, self)._activate_provisioning_service_block():
            return False

        config = self._config.plugins[self.full_name]

        policy_file = self._mountpoint + "/" + config.get('policy_file_path', '') + "/" + \
            config.get('policy_file', '')

        if os.path.isfile(policy_file):
            log.debug("removing %s", policy_file)
            os.remove(policy_file)
        else:
            log.debug("The %s was missing, this is unexpected as the "
                      "DebianDistroPlugin should manage this file", policy_file)

        return True

########NEW FILE########
__FILENAME__ = linux
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.distro.linux
==================================
Simple base class for cases where there are small distro-specific corner cases
"""
import abc
import logging
import os

from aminator.exceptions import VolumeException
from aminator.plugins.distro.base import BaseDistroPlugin
from aminator.util.linux import lifo_mounts, mount, mounted, MountSpec, unmount
from aminator.util.linux import install_provision_configs, remove_provision_configs
from aminator.util.linux import short_circuit_files, rewire_files
from aminator.util.metrics import fails, timer

__all__ = ('BaseLinuxDistroPlugin',)
log = logging.getLogger(__name__)


class BaseLinuxDistroPlugin(BaseDistroPlugin):
    """
    Most of what goes on between apt and yum provisioning is the same, so we factored that out,
    leaving the differences in the actual implementations
    """
    __metaclass__ = abc.ABCMeta

    def _activate_provisioning_service_block(self):
        """
        Enable service startup so that things work when the AMI starts
        For RHEL-like systems, we undo the short_circuit
        """
        config = self._config.plugins[self.full_name]
        files = config.get('short_circuit_files', [])
        if files:
            if not rewire_files(self._mountpoint, files):
                log.critical('Unable to rewire {0} to {1}')
                return False
            else:
                log.debug('Files rewired successfully')
                return True
        else:
            log.debug('No short circuit files configured, no rewiring done')
        return True

    def _deactivate_provisioning_service_block(self):
        """
        Prevent packages installing the chroot from starting
        For RHEL-like systems, we can use short_circuit which replaces the service call with /bin/true
        """
        config = self._config.plugins[self.full_name]
        files = config.get('short_circuit_files', [])
        if files:
            if not short_circuit_files(self._mountpoint, files):
                log.critical('Unable to short circuit {0} to {1}')
                return False
            else:
                log.debug('Files short-circuited successfully')
                return True
        else:
            log.debug('No short circuit files configured')
            return True

    @fails("aminator.distro.linux.configure_chroot.error")
    @timer("aminator.distro.linux.configure_chroot.duration")
    def _configure_chroot(self):
        config = self._config.plugins[self.full_name]
        log.debug('Configuring chroot at {0}'.format(self._mountpoint))
        if config.get('configure_mounts', True):
            if not self._configure_chroot_mounts():
                log.critical('Configuration of chroot mounts failed')
                return False
        if config.get('provision_configs', True):
            if not self._install_provision_configs():
                log.critical('Installation of provisioning config failed')
                return False

        log.debug("starting short_circuit ")

        #TODO: kvick we should rename 'short_circuit' to something like 'disable_service_start'
        if config.get('short_circuit', False):
            if not self._deactivate_provisioning_service_block():
                log.critical('Failure short-circuiting files')
                return False

        log.debug("finished short_circuit")

        log.debug('Chroot environment ready')
        return True

    def _configure_chroot_mounts(self):
        config = self._config.plugins[self.full_name]
        for mountdef in config.chroot_mounts:
            dev, fstype, mountpoint, options = mountdef
            mountspec = MountSpec(dev, fstype, os.path.join(self._mountpoint, mountpoint.lstrip('/')), options)
            log.debug('Attempting to mount {0}'.format(mountspec))
            if not mounted(mountspec.mountpoint):
                result = mount(mountspec)
                if not result.success:
                    log.critical('Unable to configure chroot: {0.std_err}'.format(result.result))
                    return False
        log.debug('Mounts configured')
        return True

    def _install_provision_configs(self):
        config = self._config.plugins[self.full_name]
        files = config.get('provision_config_files', [])
        if files:
            if not install_provision_configs(files, self._mountpoint):
                log.critical('Error installing provisioning configs')
                return False
            else:
                log.debug('Provision config files successfully installed')
                return True
        else:
            log.debug('No provision config files configured')
            return True

    @fails("aminator.distro.linux.teardown_chroot.error")
    @timer("aminator.distro.linux.teardown_chroot.duration")
    def _teardown_chroot(self):
        config = self._config.plugins[self.full_name]
        log.debug('Tearing down chroot at {0}'.format(self._mountpoint))
        #TODO: kvick we should rename 'short_circuit' to something like 'disable_service_start'
        if config.get('short_circuit', True):
            if not self._activate_provisioning_service_block():
                log.critical('Failure during re-enabling service startup')
                return False
        if config.get('provision_configs', True):
            if not self._remove_provision_configs():
                log.critical('Removal of provisioning config failed')
                return False
        if config.get('configure_mounts', True):
            if not self._teardown_chroot_mounts():
                log.critical('Teardown of chroot mounts failed')
                return False
        log.debug('Chroot environment cleaned')
        return True

    def _teardown_chroot_mounts(self):
        config = self._config.plugins[self.full_name]
        for mountdef in reversed(config.chroot_mounts):
            dev, fstype, mountpoint, options = mountdef
            mountspec = MountSpec(dev, fstype, os.path.join(self._mountpoint, mountpoint.lstrip('/')), options)
            log.debug('Attempting to unmount {0}'.format(mountspec))
            if not mounted(mountspec.mountpoint):
                log.warn('{0} not mounted'.format(mountspec.mountpoint))
                continue
            result = unmount(mountspec.mountpoint)
            if not result.success:
                log.error('Unable to unmount {0.mountpoint}: {1.std_err}'.format(mountspec, result.result))
                return False
        log.debug('Checking for stray mounts')
        for mountpoint in lifo_mounts(self._mountpoint):
            log.debug('Stray mount found: {0}, attempting to unmount'.format(mountpoint))
            result = unmount(mountpoint)
            if not result.success:
                log.error('Unable to unmount {0.mountpoint}: {1.std_err}'.format(mountspec, result.result))
                return False
        log.debug('Teardown of chroot mounts succeeded!')
        return True

    def _remove_provision_configs(self):
        config = self._config.plugins[self.full_name]
        files = config.get('provision_config_files', [])
        if files:
            if not remove_provision_configs(files, self._mountpoint):
                log.critical('Error removing provisioning configs')
                return False
            else:
                log.debug('Provision config files successfully removed')
                return True
        else:
            log.debug('No provision config files configured')
            return True

    def __enter__(self):
        if not self._configure_chroot():
            raise VolumeException('Error configuring chroot')
        return self

    def __exit__(self, exc_type, exc_value, trace):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        if exc_type and self._config.context.get("preserve_on_error", False):
            return False
        if not self._teardown_chroot():
            raise VolumeException('Error tearing down chroot')
        return False

    def __call__(self, mountpoint):
        self._mountpoint = mountpoint
        return self

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.distro.manager
====================================
Provisioner plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class DistroPluginManager(BasePluginManager):
    """OS Distribution Plugin Manager """
    _entry_point = 'aminator.plugins.distro'

    @property
    def entry_point(self):
        return self._entry_point

    @staticmethod
    def check_func(plugin): # pylint: disable=method-hidden
        return True

########NEW FILE########
__FILENAME__ = redhat
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.distro.redhat
================================
basic redhat distro
"""
import logging

from aminator.plugins.distro.linux import BaseLinuxDistroPlugin

__all__ = ('RedHatDistroPlugin',)
log = logging.getLogger(__name__)


class RedHatDistroPlugin(BaseLinuxDistroPlugin):
    """
    RedHatDistroPlugin takes the majority of its behavior from BaseLinuxDistroPlugin
    See BaseLinuxDistroPlugin for details
    """
    _name = 'redhat'

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.finalizer.base
===============================
Base class(es) for finalizer plugins
"""
import abc
import logging

from aminator.plugins.base import BasePlugin


__all__ = ('BaseFinalizerPlugin',)
log = logging.getLogger(__name__)


class BaseFinalizerPlugin(BasePlugin):
    """
    Finalizers handle administrivia post-package-provisioning. Think: registration, tagging, snapshotting, etc.
    They are context managers to ensure resource cleanup
    """

    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.finalizer'

    @abc.abstractmethod
    def finalize(self):
        """ finalize an image """

    def __enter__(self):
        return self

    def __exit__(self, typ, val, trc):
        if typ: log.exception("Exception: {0}: {1}".format(typ.__name__,val))
        return False

    def __call__(self, cloud):
        self._cloud = cloud

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.finalizer.manager
==================================
Finalizer plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class FinalizerPluginManager(BasePluginManager):
    """ Finalizer Plugin Manager """
    _entry_point = 'aminator.plugins.finalizer'

    @property
    def entry_point(self):
        return self._entry_point

########NEW FILE########
__FILENAME__ = tagging_base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.finalizer.tagging_base
======================================
base tagging image finalizer
"""
import logging
from datetime import datetime
import abc

from os import environ
from aminator.config import conf_action
from aminator.exceptions import FinalizerException
from aminator.plugins.finalizer.base import BaseFinalizerPlugin

__all__ = ('TaggingBaseFinalizerPlugin',)
log = logging.getLogger(__name__)


class TaggingBaseFinalizerPlugin(BaseFinalizerPlugin):
    _name = 'tagging_base'

    def add_plugin_args(self):
        context = self._config.context
        tagging = self._parser.add_argument_group(title='AMI Tagging and Naming',
                                                  description='Tagging and naming options for the resultant AMI')
        tagging.add_argument('-s', '--suffix', dest='suffix', action=conf_action(context.ami),
                             help='suffix of ami name, (default yyyymmddHHMM)')
        creator_help = 'The user who is aminating. The resultant AMI will receive a creator tag w/ this user'
        tagging.add_argument('-c', '--creator', dest='creator', action=conf_action(context.ami),
                             help=creator_help)
        tagging.add_argument('--vm-type', dest='vm_type', choices=["paravirtual", "hvm"], action=conf_action(context.ami),
                             help='virtualization type to register image as')
        return tagging

    def _set_metadata(self):
        context = self._config.context
        config = self._config.plugins[self.full_name]

        log.debug('Populating snapshot and ami metadata for tagging and naming')
        creator = context.ami.get('creator',
                                  config.get('creator',
                                             'aminator'))
        context.ami.tags.creator = creator
        context.snapshot.tags.creator = creator

        metadata = context.package.attributes
        metadata['arch'] = context.base_ami.architecture
        metadata['base_ami_name'] = context.base_ami.name
        metadata['base_ami_id'] = context.base_ami.id
        metadata['base_ami_version'] = context.base_ami.tags.get('base_ami_version', '')

        suffix = context.ami.get('suffix', None)
        if not suffix:
            suffix = config.suffix_format.format(datetime.utcnow())

        metadata['suffix'] = suffix

        for tag in config.tag_formats:
            context.ami.tags[tag] = config.tag_formats[tag].format(**metadata)
            context.snapshot.tags[tag] = config.tag_formats[tag].format(**metadata)

        default_description = config.description_format.format(**metadata)
        description = context.snapshot.get('description', default_description)
        context.ami.description = description
        context.snapshot.description = description

    def _add_tags(self, resources):
        context = self._config.context
        context.ami.tags.creation_time = '{0:%F %T UTC}'.format(datetime.utcnow())
        for resource in resources:
            try:
                self._cloud.add_tags(resource)
            except FinalizerException:
                log.exception('Error adding tags to {0}'.format(resource))
                return False
            log.info('Successfully tagged {0}'.format(resource))
        log.info('Successfully tagged objects')
        return True

    def _log_ami_metadata(self):
        context = self._config.context
        for attr in ('id', 'name', 'description', 'kernel_id', 'ramdisk_id', 'virtualization_type',):
            log.info('{0}: {1}'.format(attr, getattr(context.ami.image, attr)))
        for tag_name, tag_value in context.ami.image.tags.iteritems():
            log.info('Tag {0} = {1}'.format(tag_name, tag_value))

    @abc.abstractmethod
    def finalize(self):
        """ finalize an image """

    def __enter__(self):
        context = self._config.context
        if context.ami.get("suffix",None):
            environ["AMINATOR_AMI_SUFFIX"] = context.ami.suffix
        if context.ami.get("creator", None):
            environ["AMINATOR_CREATOR"] = context.ami.creator
        if context.ami.get("vm_type", None):
            environ["AMINATOR_VM_TYPE"] = context.ami.vm_type
        return self

    def __exit__(self, exc_type, exc_value, trace):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        return False

    def __call__(self, cloud):
        self._cloud = cloud
        return self

########NEW FILE########
__FILENAME__ = tagging_ebs
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.finalizer.tagging_ebs
======================================
ebs tagging image finalizer
"""
import logging

from os import environ
from aminator.config import conf_action
from aminator.plugins.finalizer.tagging_base import TaggingBaseFinalizerPlugin
from aminator.util.linux import sanitize_metadata


__all__ = ('TaggingEBSFinalizerPlugin',)
log = logging.getLogger(__name__)


class TaggingEBSFinalizerPlugin(TaggingBaseFinalizerPlugin):
    _name = 'tagging_ebs'

    def add_plugin_args(self):
        tagging = super(TaggingEBSFinalizerPlugin,self).add_plugin_args()
        
        context = self._config.context
        tagging.add_argument('-n', '--name', dest='name', action=conf_action(context.ami),
                             help='name of resultant AMI (default package_name-version-release-arch-yyyymmddHHMM-ebs')

    def _set_metadata(self):
        super(TaggingEBSFinalizerPlugin, self)._set_metadata()
        context = self._config.context
        config = self._config.plugins[self.full_name]
        metadata = context.package.attributes
        ami_name = context.ami.get('name', None)
        if not ami_name:
            ami_name = config.name_format.format(**metadata)

        context.ami.name = sanitize_metadata('{0}-ebs'.format(ami_name))

    def _snapshot_volume(self):
        log.info('Taking a snapshot of the target volume')
        if not self._cloud.snapshot_volume():
            return False
        log.info('Snapshot success')
        return True

    def _register_image(self, block_device_map=None, root_device=None):
        log.info('Registering image')
        config = self._config.plugins[self.full_name]
        if block_device_map is None:
            block_device_map = config.default_block_device_map
        if root_device is None:
            root_device = config.default_root_device
        if not self._cloud.register_image(block_device_map, root_device):
            return False
        log.info('Registration success')
        return True

    def finalize(self):
        log.info('Finalizing image')
        self._set_metadata()

        if not self._snapshot_volume():
            log.critical('Error snapshotting volume')
            return False

        if not self._register_image():
            log.critical('Error registering image')
            return False

        if not self._add_tags(['snapshot', 'ami']):
            log.critical('Error adding tags')
            return False

        log.info('Image registered and tagged')
        self._log_ami_metadata()
        return True

    def __enter__(self):
        context = self._config.context
        environ["AMINATOR_STORE_TYPE"] = "ebs"
        if context.ami.get("name",None):
            environ["AMINATOR_AMI_NAME"] = context.ami.name
        return super(TaggingEBSFinalizerPlugin, self).__enter__()



########NEW FILE########
__FILENAME__ = tagging_s3
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.finalizer.tagging_s3
======================================
s3 tagging image finalizer
"""
import logging
from shutil import rmtree
from os.path import isdir
from os import makedirs, system

from os import environ
from aminator.config import conf_action
from aminator.plugins.finalizer.tagging_base import TaggingBaseFinalizerPlugin
from aminator.util import randword
from aminator.util.linux import sanitize_metadata, monitor_command
from aminator.util.metrics import cmdsucceeds, cmdfails, timer

__all__ = ('TaggingS3FinalizerPlugin',)
log = logging.getLogger(__name__)


class TaggingS3FinalizerPlugin(TaggingBaseFinalizerPlugin):
    _name = 'tagging_s3'

    def add_plugin_args(self):
        tagging = super(TaggingS3FinalizerPlugin,self).add_plugin_args()
        
        context = self._config.context
        tagging.add_argument('-n', '--name', dest='name', action=conf_action(context.ami),
                             help='name of resultant AMI (default package_name-version-release-arch-yyyymmddHHMM-s3')

        tagging.add_argument('--cert', dest='cert', action=conf_action(context.ami),
                             help='The path to the PEM encoded RSA public key certificate file for ec2-bundle-volume')
        tagging.add_argument('--privatekey', dest='privatekey', action=conf_action(context.ami),
                             help='The path to the PEM encoded RSA private key file for ec2-bundle-vol')
        tagging.add_argument('--ec2-user', dest='ec2_user', action=conf_action(context.ami),
                             help='ec2 user id for ec2-bundle-vol')
        tagging.add_argument('--tmpdir', dest='tmpdir', action=conf_action(context.ami),
                             help='temp directory used by ec2-bundle-vol')
        tagging.add_argument('--bucket', dest='bucket', action=conf_action(context.ami),
                             help='the S3 bucket to use for ec2-upload-bundle')
        tagging.add_argument('--break-copy-volume', dest='break_copy_volume', action=conf_action(context.ami, action='store_true'),
                             help='break into shell after copying the volume, for debugging')

    def _set_metadata(self):
        super(TaggingS3FinalizerPlugin, self)._set_metadata()
        context = self._config.context
        config = self._config.plugins[self.full_name]
        metadata = context.package.attributes
        ami_name = context.ami.get('name', None)
        if not ami_name:
            ami_name = config.name_format.format(**metadata)

        context.ami.name = sanitize_metadata('{0}-s3'.format(ami_name))

    def tmpdir(self):
        config = self._config.plugins[self.full_name]
        ami = self._config.context.ami
        return "{0}/{1}".format(ami.get("tmpdir", config.get("default_tmpdir", "/tmp")), ami.name)

    # pylint: disable=access-member-before-definition
    def unique_name(self):
        context = self._config.context
        if hasattr(self, "_unique_name"):
            return self._unique_name
        self._unique_name = "{0}-{1}".format(context.ami.name, randword(6))
        return self._unique_name
        
    def image_location(self):
        return "{0}/{1}".format(self.tmpdir(), self.unique_name())

    @cmdsucceeds("aminator.finalizer.tagging_s3.copy_volume.count")
    @cmdfails("aminator.finalizer.tagging_s3.copy_volume.error")
    @timer("aminator.finalizer.tagging_s3.copy_volume.duration")
    def _copy_volume(self):
        context = self._config.context
        tmpdir=self.tmpdir()
        if not isdir(tmpdir):
            makedirs(tmpdir)
        return monitor_command(["dd", "bs=65536", "if={0}".format(context.volume.dev), "of={1}".format(self.image_location())])

    @cmdsucceeds("aminator.finalizer.tagging_s3.bundle_image.count")
    @cmdfails("aminator.finalizer.tagging_s3.bundle_image.error")
    @timer("aminator.finalizer.tagging_s3.bundle_image.duration")
    def _bundle_image(self):
        context = self._config.context

        config = self._config.plugins[self.full_name]
        block_device_map = config.default_block_device_map
        root_device = config.default_root_device

        bdm = "root={0}".format(root_device)
        for bd in block_device_map:
            bdm += ",{0}={1}".format(bd[1],bd[0])
        bdm += ",ami={0}".format(root_device)
        
        cmd = ['ec2-bundle-image']
        cmd.extend(['-c', context.ami.get("cert", config.default_cert)])
        cmd.extend(['-k', context.ami.get("privatekey", config.default_privatekey)])
        cmd.extend(['-u', context.ami.get("ec2_user", str(config.default_ec2_user))])
        cmd.extend(['-i', self.image_location()])
        cmd.extend(['-d', self.tmpdir()])
        if context.base_ami.architecture:
            cmd.extend(['-r', context.base_ami.architecture])

        vm_type = context.ami.get("vm_type", "paravirtual")
        if vm_type == "paravirtual":
            if context.base_ami.kernel_id:
                cmd.extend(['--kernel', context.base_ami.kernel_id])
            if context.base_ami.ramdisk_id:
                cmd.extend(['--ramdisk', context.base_ami.ramdisk_id])
            cmd.extend(['-B', bdm])
        return monitor_command(cmd)

    @cmdsucceeds("aminator.finalizer.tagging_s3.upload_bundle.count")
    @cmdfails("aminator.finalizer.tagging_s3.upload_bundle.error")
    @timer("aminator.finalizer.tagging_s3.upload_bundle.duration")
    def _upload_bundle(self):
        context = self._config.context

        provider = self._cloud._connection.provider
        ak = provider.get_access_key()
        sk = provider.get_secret_key()
        tk = provider.get_security_token()

        cmd = ['ec2-upload-bundle']
        cmd.extend(['-b', context.ami.bucket])
        cmd.extend(['-a', ak])
        cmd.extend(['-s', sk])
        if tk:
            cmd.extend(['-t', tk])
        cmd.extend(['-m', "{0}.manifest.xml".format(self.image_location())])
        cmd.extend(['--retry'])
        return monitor_command(cmd)

    def _register_image(self):
        context = self._config.context
        log.info('Registering image')
        if not self._cloud.register_image(manifest="{0}/{1}.manifest.xml".format(context.ami.bucket,self.unique_name())):
            return False
        log.info('Registration success')
        return True

    def finalize(self):
        log.info('Finalizing image')
        context = self._config.context
        self._set_metadata()

        ret = self._copy_volume()
        if not ret.success:
            log.debug('Error copying volume, failure:{0.command} :{0.std_err}'.format(ret.result))
            return False

        if context.ami.get('break_copy_volume', False):
            system("bash")
            
        ret = self._bundle_image()
        if not ret.success:
            log.debug('Error bundling image, failure:{0.command} :{0.std_err}'.format(ret.result))
            return False

        ret = self._upload_bundle()
        if not ret.success:
            log.debug('Error uploading bundled volume, failure:{0.command} :{0.std_err}'.format(ret.result))
            return False

        if not self._register_image():
            log.critical('Error registering image')
            return False

        if not self._add_tags(['ami']):
            log.critical('Error adding tags')
            return False

        log.info('Image registered and tagged')
        self._log_ami_metadata()
        return True

    def __enter__(self):
        context = self._config.context

        environ["AMINATOR_STORE_TYPE"] = "s3"
        if context.ami.get("name",None):
            environ["AMINATOR_AMI_NAME"] = context.ami.name
        if context.ami.get("cert", None):
            environ["AMINATOR_CERT"] = context.ami.cert
        if context.ami.get("privatekey", None):
            environ["AMINATOR_PRIVATEKEY"] = context.ami.privatekey
        if context.ami.get("ec2_user", None):
            environ["AMINATOR_EC2_USER"] = context.ami.ec2_user
        if context.ami.get("tmpdir", None):
            environ["AMINATOR_TMPDIR"] = context.ami.tmpdir
        if context.ami.get("bucket", None):
            environ["AMINATOR_BUCKET"] = context.ami.bucket

        return super(TaggingS3FinalizerPlugin, self).__enter__()

    def __exit__(self, exc_type, exc_value, trace):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        # delete tmpdir used by ec2-bundle-vol
        td = self.tmpdir()
        if isdir(td):
            rmtree(td)
        return False
                            

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.manager
========================
Base plugin manager(s) and utils
"""
import abc
import logging

from stevedore.dispatch import NameDispatchExtensionManager


log = logging.getLogger(__name__)


class BasePluginManager(NameDispatchExtensionManager):
    """
    Base plugin manager from which all managers *should* inherit
    Descendents *must* define a _entry_point class attribute
    Descendents *may* define a _check_func class attribute holding a function that determines whether a
    given plugin should or should not be enabled
    """
    __metaclass__ = abc.ABCMeta
    _entry_point = None
    _check_func = None

    def __init__(self, check_func=None, invoke_on_load=True, invoke_args=None, invoke_kwds=None):
        invoke_args = invoke_args or ()
        invoke_kwds = invoke_kwds or {}

        if self._entry_point is None:
            raise AttributeError('Plugin managers must declare their entry point in a class attribute _entry_point')

        check_func = check_func or self._check_func
        if check_func is None:
            check_func = lambda x: True

        super(BasePluginManager, self).__init__(namespace=self.entry_point, check_func=check_func,
                                                invoke_on_load=invoke_on_load, invoke_args=invoke_args,
                                                invoke_kwds=invoke_kwds)

    @property
    def entry_point(self):
        """
        Base plugins for each plugin type must set a _entry_point class attribute to the entry point they
        are responsible for
        """
        return self._entry_point

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.metrics.base
============================
Base class(es) for metrics plugins
"""
import abc
import logging

from aminator.plugins.base import BasePlugin


__all__ = ('BaseMetricsPlugin',)
log = logging.getLogger(__name__)


class BaseMetricsPlugin(BasePlugin):
    """
    """
    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.metrics'

    @abc.abstractmethod
    def increment(self, name, value=1): pass        

    @abc.abstractmethod
    def gauge(self, name, value): pass

    @abc.abstractmethod
    def timer(self, name, seconds): pass

    @abc.abstractmethod
    def start_timer(self, name): pass

    @abc.abstractmethod
    def stop_timer(self, name): pass

    @abc.abstractmethod
    def flush(self): pass

    def add_tag(self, name, value): 
        self.tags[name] = value

    def __init__(self):
        super(BaseMetricsPlugin, self).__init__()
        self.tags = {}

    def __enter__(self):
        setattr(self._config, "metrics", self)
        return self

    def __exit__(self, exc_type, exc_value, trace):
        self.flush()
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        return False

########NEW FILE########
__FILENAME__ = logger
# -*- coding: utf-8 -*-

#
#
#  Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.metrics.logger
=============================
basic logger metrics collector
"""
import logging
from time import time

from aminator.plugins.metrics.base import BaseMetricsPlugin

__all__ = ('LoggerMetricsPlugin',)
log = logging.getLogger(__name__)


class LoggerMetricsPlugin(BaseMetricsPlugin):
    _name = 'logger'

    def __init__(self):
        super(LoggerMetricsPlugin,self).__init__()
        self.timers = {}

    def increment(self, name, value=1):
        log.debug("Metric {0}: increment {1}, tags: {2}".format(name,value, self.tags))

    def gauge(self, name, value):
        log.debug("Metric {0}: gauge set {1}, tags: {2}".format(name, value, self.tags))

    def timer(self, name, seconds):
        log.debug("Metric {0}: timer {1}s, tags: {2}".format(name, seconds, self.tags)) 

    def start_timer(self, name):
        log.debug("Metric {0}: start timer, tags: {1}".format(name, self.tags))
        self.timers[name] = time()

    def stop_timer(self, name):
        log.debug("Metric {0}: stop timer [{1}s], tags: {2}".format(name, time() - self.timers[name], self.tags))
        del self.timers[name]
    
    def flush(self):
        for name in self.timers:
            log.warn("Metric {0}: timer never stopped, started at {1}, tags: {2}".format(name, self.timers[name], self.tags))

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.metrics.manager
===============================
Metrics plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class MetricsPluginManager(BasePluginManager):
    """ Metrics Plugin Manager """
    _entry_point = 'aminator.plugins.metrics'

    @property
    def entry_point(self):
        return self._entry_point

    @staticmethod
    def check_func(plugin): # pylint: disable=method-hidden
        return True

########NEW FILE########
__FILENAME__ = apt
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.provisioner.apt
================================
basic apt provisioner
"""
import logging
import os

from aminator.plugins.provisioner.base import BaseProvisionerPlugin
from aminator.util.linux import monitor_command, result_to_dict
from aminator.util.metrics import cmdsucceeds, cmdfails, timer, lapse

__all__ = ('AptProvisionerPlugin',)
log = logging.getLogger(__name__)


class AptProvisionerPlugin(BaseProvisionerPlugin):
    """
    AptProvisionerPlugin takes the majority of its behavior from BaseProvisionerPlugin
    See BaseProvisionerPlugin for details
    """
    _name = 'apt'

    def _refresh_repo_metadata(self):
        return self.apt_get_update()

    @cmdsucceeds("aminator.provisioner.apt.provision_package.count")
    @cmdfails("aminator.provisioner.apt.provision_package.error")
    @lapse("aminator.provisioner.apt.provision_package.duration")
    def _provision_package(self):
        result = self._refresh_repo_metadata()
        if not result.success:
            log.critical('Repo metadata refresh failed: {0.std_err}'.format(result.result))
            return result
        context = self._config.context
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        if context.package.get('local_install', False):
            return self.apt_get_localinstall(context.package.arg)
        else:
            return self.apt_get_install(context.package.arg)

    def _store_package_metadata(self):
        context = self._config.context
        config = self._config.plugins[self.full_name]
        metadata = self.deb_package_metadata(context.package.arg, config.get('pkg_query_format', ''), context.package.get('local_install', False))
        for x in config.pkg_attributes:
            if x == 'version' and x in metadata:
                if ':' in metadata[x]:
                    # strip epoch element from version
                    vers = metadata[x]
                    metadata[x] = vers[vers.index(':')+1:]
                if '-' in metadata[x]:
                    # debs include release in version so split
                    # version into version-release to compat w/rpm
                    vers, rel = metadata[x].split('-', 1)
                    metadata[x] = vers
                    metadata['release'] = rel
                else:
                    metadata['release'] = 0
                # this is probably not necessary given above
            metadata.setdefault(x, None)
        context.package.attributes = metadata

    @staticmethod
    def dpkg_install(package):
        return monitor_command(['dpkg', '-i', package])
    
    @classmethod
    def apt_get_localinstall(cls, package):
        """install deb file with dpkg then resolve dependencies
        """
        dpkg_ret = cls.dpkg_install(package)
        if not dpkg_ret.success:
            log.debug('failure:{0.command} :{0.std_err}'.format(dpkg_ret.result))
            apt_ret = cls.apt_get_install('--fix-missing')
            if not apt_ret.success:
                log.debug('failure:{0.command} :{0.std_err}'.format(apt_ret.result))
            return apt_ret
        return dpkg_ret
    
    @staticmethod
    def deb_query(package, queryformat, local=False):
        if local:
            cmd = 'dpkg-deb -W'.split()
            cmd.append('--showformat={0}'.format(queryformat))
        else:
            cmd = 'dpkg-query -W'.split()
            cmd.append('-f={0}'.format(queryformat))
        cmd.append(package)
        return monitor_command(cmd)
    

    @cmdsucceeds("aminator.provisioner.apt.apt_get_update.count")
    @cmdfails("aminator.provisioner.apt.apt_get_update.error")
    @timer("aminator.provisioner.apt.apt_get_update.duration")
    def apt_get_update(self):
        return monitor_command(['apt-get', 'update'])
    
    @classmethod
    def apt_get_install(cls, package):
        return monitor_command(['apt-get', '-y', 'install', package])
    
    @classmethod
    def deb_package_metadata(cls, package, queryformat, local=False):
        return result_to_dict(cls.deb_query(package, queryformat, local))

########NEW FILE########
__FILENAME__ = aptitude
# -*- coding: utf-8 -*-

#
#
#  Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.provisioner.aptitude
================================
basic aptitude provisioner
"""
import logging

from os.path import basename
import re

from aminator.plugins.provisioner.apt import AptProvisionerPlugin
from aminator.util.linux import monitor_command

__all__ = ('AptitudeProvisionerPlugin',)
log = logging.getLogger(__name__)


class AptitudeProvisionerPlugin(AptProvisionerPlugin):
    """
    AptitudeProvisionerPlugin takes the majority of its behavior from AptProvisionerPlugin
    See AptProvisionerPlugin for details
    """
    _name = 'aptitude'

    # overload this method to call aptitude instaed. We use aptitude hold to try 
    # to make the local installed package install without removing it (in case
    # the package has missing dependencies)
    @classmethod
    def apt_get_localinstall(cls, package):
        """install deb file with dpkg then resolve dependencies
        """
        dpkg_ret = cls.dpkg_install(package)
        pkgname = re.sub(r'_.*$', "", basename(package))
        if not dpkg_ret.success:
            log.debug('failure:{0.command} :{0.std_err}'.format(dpkg_ret.result))
            aptitude_ret = cls.aptitude("hold", pkgname)
            if not aptitude_ret.success:
                log.debug('failure:{0.command} :{0.std_err}'.format(aptitude_ret.result))
            apt_ret = super(AptitudeProvisionerPlugin,cls).apt_get_install('--fix-missing')
            if not apt_ret.success:
                log.debug('failure:{0.command} :{0.std_err}'.format(apt_ret.result))
            return apt_ret
        return dpkg_ret

    @staticmethod
    def aptitude(operation, package):
        return monitor_command(["aptitude", "--no-gui", "-y", operation, package])

    # overload this method to call aptitude instead.  But aptitude will not exit with
    # an error code if it failed to install, so we double check that the package installed
    # with the dpkg-query command
    @classmethod
    def apt_get_install(cls,package):
        aptitude_ret = cls.aptitude("install", package)
        if not aptitude_ret.success:
            log.debug('failure:{0.command} :{0.std_err}'.format(aptitude_ret.result))
        query_ret = cls.deb_query(package, '${Package}-${Version}')
        if not query_ret.success:
            log.debug('failure:{0.command} :{0.std_err}'.format(query_ret.result))
        return query_ret

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.provisioner.base
==================================
Simple base class for cases where there are small distro-specific corner cases
"""
import abc
import logging
import os
import shutil

from glob import glob

from aminator.config import conf_action
from aminator.plugins.base import BasePlugin
from aminator.util import download_file
from aminator.util.linux import Chroot, monitor_command


__all__ = ('BaseProvisionerPlugin',)
log = logging.getLogger(__name__)


class BaseProvisionerPlugin(BasePlugin):
    """
    Most of what goes on between apt and yum provisioning is the same, so we factored that out,
    leaving the differences in the actual implementations
    """
    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.provisioner'

    @abc.abstractmethod
    def _provision_package(self):
        """ subclasses must implement package provisioning logic """

    @abc.abstractmethod
    def _store_package_metadata(self):
        """ stuff name, version, release into context """

    def _pre_chroot_block(self):
        """ run commands before entering chroot"""
        pass

    def _post_chroot_block(self):
        """ commands to run after the exiting the chroot"""
        pass

    def add_plugin_args(self, *args, **kwargs):
        context = self._config.context
        prov = self._parser.add_argument_group(title='Provisioning')
        prov.add_argument("-i", "--interactive", dest='interactive', help="interactive session after provivioning", action=conf_action(config=context.package, action="store_true"))

    def provision(self):
        context = self._config.context

        if self._local_install():
            log.info('performing a local install of {0}'.format(context.package.arg))
            context.package.local_install = True
            if not self._stage_pkg():
                log.critical('failed to stage {0}'.format(context.package.arg))
                return False
        else:
            log.info('performing a repo install of {0}'.format(context.package.arg))
            context.package.local_install = False

        log.debug('Pre chroot command block')
        self._pre_chroot_block()

        log.debug('Entering chroot at {0}'.format(self._distro._mountpoint))

        with Chroot(self._distro._mountpoint):
            log.debug('Inside chroot')

            result = self._provision_package()
            
            if context.package.get('interactive', False):
                os.system("bash")

            if not result.success:
                log.critical('Installation of {0} failed: {1.std_err}'.format(context.package.arg, result.result))
                return False
            self._store_package_metadata()
            if context.package.local_install and not context.package.get('preserve', False):
                os.remove(context.package.arg)

            # run scripts that may have been delivered in the package
            scripts_dir = self._config.plugins[self.full_name].get('scripts_dir', '/var/local')
            log.debug('scripts_dir = {0}'.format(scripts_dir))

            if scripts_dir:
                if not self._run_provision_scripts(scripts_dir):
                    return False

        log.debug('Exited chroot')

        log.debug('Post chroot command block')
        self._post_chroot_block()

        log.info('Provisioning succeeded!')
        return True

    def _run_provision_scripts(self, scripts_dir):
        """
        execute every python or shell script found in scripts_dir
            1. run python or shell scripts in lexical order

        :param scripts_dir: path in chroot to look for python and shell scripts
        :return: None
        """

        script_files = sorted( glob(scripts_dir + '/*.py') + glob(scripts_dir + '/*.sh') )
        if not script_files:
            log.debug("no python or shell scripts found in {0}".format(scripts_dir))
        else:
            log.debug('found scripts {0} in {1}'.format(script_files, scripts_dir))
            for script in script_files:
                log.debug('executing script {0}'.format(script))
                if os.access(script, os.X_OK):
                    # script is executable, so just run it
                    result = run_script(script)
                else:
                    if script.endswith('.py'):
                        result = run_script(['python', script])
                    else:
                        result = run_script(['sh', script])
                if not result.success:
                    log.critical("script failed: {0}: {1.std_err}".format(script, result.result))
                    return False
        return True

    def _local_install(self):
        """True if context.package.arg ends with a package extension
        """
        config = self._config
        ext = config.plugins[self.full_name].get('pkg_extension', '')
        if not ext:
            return False

        # ensure extension begins with a dot
        ext = '.{0}'.format(ext.lstrip('.'))

        return config.context.package.arg.endswith(ext)

    def _stage_pkg(self):
        """copy package file into AMI volume.
        """
        context = self._config.context
        context.package.file = os.path.basename(context.package.arg)
        context.package.full_path = os.path.join(self._distro._mountpoint,
                                                 context.package.dir.lstrip('/'),
                                                 context.package.file)
        try:
            if any(protocol in context.package.arg for protocol in ['http://', 'https://']):
                self._download_pkg(context)
            else:
                self._move_pkg(context)
        except Exception:
            log.exception('Error encountered while staging package')
            return False
            # reset to chrooted file path
        context.package.arg = os.path.join(context.package.dir, context.package.file)
        return True

    def _download_pkg(self, context):
        """dowload url to context.package.dir
        """
        pkg_url = context.package.arg
        dst_file_path = context.package.full_path
        log.debug('downloading {0} to {1}'.format(pkg_url, dst_file_path))
        download_file(pkg_url, dst_file_path, context.package.get('timeout', 1),
                      verify_https=context.get('verify_https', False))

    def _move_pkg(self, context):
        src_file = context.package.arg.replace('file://', '')
        dst_file_path = context.package.full_path
        shutil.move(src_file, dst_file_path)

    def __call__(self, distro):
        self._distro = distro
        return self

def run_script(script):
    return monitor_command(script)

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.provisioner.manager
====================================
Provisioner plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class ProvisionerPluginManager(BasePluginManager):
    """ Provisioner Plugin Manager """
    _entry_point = 'aminator.plugins.provisioner'

    @property
    def entry_point(self):
        return self._entry_point

    @staticmethod
    def check_func(plugin): # pylint: disable=method-hidden
        return True

########NEW FILE########
__FILENAME__ = yum
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.provisioner.yum
================================
basic yum provisioner
"""
import logging
import os

from aminator.plugins.provisioner.base import BaseProvisionerPlugin
from aminator.util.linux import monitor_command, result_to_dict
from aminator.util.metrics import cmdsucceeds, cmdfails, lapse

__all__ = ('YumProvisionerPlugin',)
log = logging.getLogger(__name__)


class YumProvisionerPlugin(BaseProvisionerPlugin):
    """
    YumProvisionerPlugin takes the majority of its behavior from BaseProvisionerPlugin
    See BaseProvisionerPlugin for details
    """
    _name = 'yum'

    def _refresh_repo_metadata(self):
        config = self._config.plugins[self.full_name]
        return yum_clean_metadata(config.get('clean_repos', []))

    @cmdsucceeds("aminator.provisioner.yum.provision_package.count")
    @cmdfails("aminator.provisioner.yum.provision_package.error")
    @lapse("aminator.provisioner.yum.provision_package.duration")
    def _provision_package(self):
        result = self._refresh_repo_metadata()
        if not result.success:
            log.critical('Repo metadata refresh failed: {0.std_err}'.format(result.result))
            return result
        context = self._config.context
        if context.package.get('local_install', False):
            return yum_localinstall(context.package.arg)
        else:
            return yum_install(context.package.arg)

    def _store_package_metadata(self):
        context = self._config.context
        config = self._config.plugins[self.full_name]
        metadata = rpm_package_metadata(context.package.arg, config.get('pkg_query_format', ''),
                                        context.package.get('local_install', False))
        for x in config.pkg_attributes:
            metadata.setdefault(x, None)
        context.package.attributes = metadata


def yum_install(package):
    return monitor_command(['yum', '--nogpgcheck', '-y', 'install', package])


def yum_localinstall(path):
    if not os.path.isfile(path):
        log.critical('Package {0} not found'.format(path))
        return None
    return monitor_command(['yum', '--nogpgcheck', '-y', 'localinstall', path])


def yum_clean_metadata(repos=None):
    clean=['yum', 'clean', 'metadata']
    if repos:
        clean.extend(['--disablerepo', '*', '--enablerepo', ','.join(repos)])
    return monitor_command(clean)


def rpm_query(package, queryformat, local=False):
    cmd = 'rpm -q --qf'.split()
    cmd.append(queryformat)
    if local:
        cmd.append('-p')
    cmd.append(package)
    return monitor_command(cmd)


def rpm_package_metadata(package, queryformat, local=False):
    return result_to_dict(rpm_query(package, queryformat, local))

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.volume.base
============================
Base class(es) for volume plugins
"""
import abc
import logging

from aminator.plugins.base import BasePlugin


__all__ = ('BaseVolumePlugin',)
log = logging.getLogger(__name__)


class BaseVolumePlugin(BasePlugin):
    """
    Volume plugins ask blockdevice for an os block device, the cloud for a volume at
    that block device, mount it, and return the mount point for the provisioner. How they go about it
    is up to the implementor.
    The are context managers to ensure they unmount and clean up resources
    """
    __metaclass__ = abc.ABCMeta
    _entry_point = 'aminator.plugins.volume'

    @abc.abstractmethod
    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, trace):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        return False

    def __call__(self, cloud, blockdevice):
        self._cloud = cloud
        self._blockdevice = blockdevice
        return self

########NEW FILE########
__FILENAME__ = linux
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.volume.linux
=============================
basic linux volume allocator
"""
import logging
import os

from aminator.util import retry
from aminator.util.linux import MountSpec, busy_mount, mount, mounted, unmount
from aminator.exceptions import VolumeException
from aminator.plugins.volume.base import BaseVolumePlugin
from aminator.util.metrics import raises

__all__ = ('LinuxVolumePlugin',)
log = logging.getLogger(__name__)


class LinuxVolumePlugin(BaseVolumePlugin):
    _name = 'linux'

    def _attach(self, blockdevice):
        with blockdevice(self._cloud) as dev:
            self._dev = dev
            self._config.context.volume["dev"] = self._dev
            self._cloud.attach_volume(self._dev)

    def _detach(self):
        self._cloud.detach_volume(self._dev)

    @raises("aminator.volume.linux.mount.error")
    def _mount(self):
        if self._config.volume_dir.startswith(('~', '/')):
            self._volume_root = os.path.expanduser(self._config.volume_dir)
        else:
            self._volume_root = os.path.join(self._config.aminator_root, self._config.volume_dir)
        self._mountpoint = os.path.join(self._volume_root, os.path.basename(self._dev))
        if not os.path.exists(self._mountpoint):
            os.makedirs(self._mountpoint)

        if not mounted(self._mountpoint):
            mountspec = MountSpec(self._dev, None, self._mountpoint, None)
            result = mount(mountspec)
            if not result.success:
                msg = 'Unable to mount {0.dev} at {0.mountpoint}: {1}'.format(mountspec, result.result.std_err)
                log.critical(msg)
                raise VolumeException(msg)
        log.debug('Mounted {0.dev} at {0.mountpoint} successfully'.format(mountspec))

    @raises("aminator.volume.linux.umount.error")
    @retry(VolumeException, tries=6, delay=1, backoff=2, logger=log)
    def _unmount(self):
        if mounted(self._mountpoint):
            if busy_mount(self._mountpoint).success:
                raise VolumeException('Unable to unmount {0} from {1}'.format(self._dev, self._mountpoint))
            result = unmount(self._mountpoint)
            if not result.success:
                raise VolumeException('Unable to unmount {0} from {1}: {2}'.format(self._dev, self._mountpoint,
                                                                                   result.result.std_err))

    def _delete(self):
        self._cloud.delete_volume()

    def __enter__(self):
        self._attach(self._blockdevice)
        self._mount()
        self._config.context.volume["mountpoint"] = self._mountpoint
        return self._mountpoint

    def __exit__(self, exc_type, exc_value, trace):
        if exc_type: log.exception("Exception: {0}: {1}".format(exc_type.__name__,exc_value))
        if exc_type and self._config.context.get("preserve_on_error", False):
            return False
        self._unmount()
        self._detach()
        self._delete()
        return False

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.plugins.volume.manager
===============================
Volume plugin manager(s) and utils
"""
import logging

from aminator.plugins.manager import BasePluginManager


log = logging.getLogger(__name__)


class VolumePluginManager(BasePluginManager):
    """ Volume Plugin Manager """
    _entry_point = 'aminator.plugins.volume'

    @property
    def entry_point(self):
        return self._entry_point

    @staticmethod
    def check_func(plugin): # pylint: disable=method-hidden
        return True

########NEW FILE########
__FILENAME__ = linux
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.util.linux
===================
Linux utility functions
"""

import errno
import logging
from fcntl import flock as _flock
from fcntl import LOCK_EX, LOCK_UN, LOCK_NB
import os
import shutil
import stat
import string
import sys
from copy import copy
from collections import namedtuple
from contextlib import contextmanager

from subprocess import Popen, PIPE
from signal import signal, alarm, SIGALRM
from os import O_NONBLOCK, environ, makedirs
from os.path import isfile, isdir, dirname
from fcntl import fcntl, F_GETFL, F_SETFL
from select import select

from decorator import decorator


log = logging.getLogger(__name__)
MountSpec = namedtuple('MountSpec', 'dev fstype mountpoint options')
CommandResult = namedtuple('CommandResult', 'success result')
Response = namedtuple('Response', ['command', 'std_err', 'std_out', 'status_code'])
# need to scrub anything not in this list from AMI names and other metadata
SAFE_AMI_CHARACTERS = string.ascii_letters + string.digits + '().-/_'


def command(timeout=None, data=None, *cargs, **ckwargs):
    """
    decorator used to define shell commands to be executed via envoy.run
    decorated function should return a list or string representing the command to be executed
    decorated function should return None if a guard fails
    """
    @decorator
    def _run(f, *args, **kwargs):
        _cmd = f(*args, **kwargs)
        assert _cmd is not None, "null command passed to @command decorator"
        return monitor_command(_cmd, timeout)
    return _run



def set_nonblocking(stream):
    fl = fcntl(stream.fileno(), F_GETFL)
    fcntl(stream.fileno(), F_SETFL, fl | O_NONBLOCK)

def monitor_command(cmd, timeout=None):
    cmdStr = cmd
    shell=True
    if isinstance(cmd, list):
        cmdStr = " ".join(cmd)
        shell=False

    assert cmdStr, "empty command passed to monitor_command"

    log.debug('command: {0}'.format(cmdStr))
    
    # sanitize PATH if we are running in a virtualenv
    env = copy(environ)
    if hasattr(sys, "real_prefix"):
        env["PATH"] = string.replace(env["PATH"], "{0}/bin:".format(sys.prefix), "")

    proc = Popen(cmd,stdout=PIPE,stderr=PIPE,close_fds=True,shell=shell,env=env)
    set_nonblocking(proc.stdout)
    set_nonblocking(proc.stderr)

    if timeout: 
        alarm(timeout)
        def handle_sigalarm(*_):
            proc.terminate()
        signal(SIGALRM, handle_sigalarm)

    io = [proc.stdout, proc.stderr]
    
    std_out = ""
    std_err = ""
    while True:
        # if we got eof from all pipes then stop polling
        if not io: break
        reads, _, _ = select(io, [], [])
        for fd in reads:
            buf = fd.read(4096)
            if len(buf) == 0:
                # got eof
                io.remove(fd)
            else:
                if fd == proc.stderr:
                    log.debug("STDERR: {0}".format(buf))
                    std_err += buf
                else:
                    if buf[-1] == "\n":
                        log.debug(buf[:-1])
                    else:
                        log.debug(buf)
                    std_out += buf

    proc.wait()
    alarm(0)
    status_code = proc.returncode
    log.debug("status code: {0}".format(status_code))
    return CommandResult(status_code == 0, Response(cmdStr, std_err, std_out, status_code))

def mounted(path):
    pat = path.strip() + ' '
    with open('/proc/mounts') as mounts:
        return any(pat in mount for mount in mounts)


def fsck(dev):
    return monitor_command(['fsck', '-y', dev])


def mount(mountspec):
    if not any((mountspec.dev, mountspec.mountpoint)):
        log.error('Must provide dev or mountpoint')
        return None

    fstype_arg = options_arg = ''

    if mountspec.fstype:
        if mountspec.fstype == 'bind':
            fstype_flag = '-o'
            # we may need to create the mountpoint if it does not exist
            if isfile(mountspec.dev):
                mountpoint = dirname(mountspec.mountpoint)
            else:
                mountpoint = mountspec.mountpoint
                if not isdir(mountpoint):
                    makedirs(mountpoint)
        else:
            fstype_flag = '-t'
        fstype_arg = '{0} {1}'.format(fstype_flag, mountspec.fstype)

    if mountspec.options:
        options_arg = '-o ' + mountspec.options

    return monitor_command('mount {0} {1} {2} {3}'.format(fstype_arg, options_arg, mountspec.dev, mountspec.mountpoint))

def unmount(dev):
    return monitor_command(['umount', dev])


def busy_mount(mountpoint):
    return monitor_command(['lsof', '-X', mountpoint])


def sanitize_metadata(word):
    chars = list(word)
    for index, char in enumerate(chars):
        if char not in SAFE_AMI_CHARACTERS:
            chars[index] = '_'
    return ''.join(chars)


def keyval_parse(record_sep='\n', field_sep=':'):
    """decorator for parsing CommandResult stdout into key/value pairs returned in a dict
    """
    @decorator
    def _parse(f, *args, **kwargs):
        return result_to_dict(f(*args, **kwargs),record_sep,field_sep)
    return _parse

def result_to_dict(commandResult, record_sep='\n', field_sep=':'):
    metadata = {}
    if commandResult.success:
        for record in commandResult.result.std_out.split(record_sep):
            try:
                key, val = record.split(field_sep, 1)
            except ValueError:
                continue
            metadata[key.strip()] = val.strip()
    else:
        log.debug('failure:{0.command} :{0.std_err}'.format(commandResult.result))
    return metadata
    

class Chroot(object):
    def __init__(self, path):
        self.path = path
        log.debug('Chroot path: {0}'.format(self.path))

    def __enter__(self):
        log.debug('Configuring chroot at {0}'.format(self.path))
        self.real_root = os.open('/', os.O_RDONLY)
        self.cwd = os.getcwd()
        os.chroot(self.path)
        os.chdir('/')
        log.debug('Inside chroot')
        return self

    def __exit__(self, typ, exc, trc):
        if typ: log.exception("Exception: {0}: {1}".format(typ.__name__,exc))
        log.debug('Leaving chroot')
        os.fchdir(self.real_root)
        os.chroot('.')
        os.chdir(self.cwd)
        log.debug('Outside chroot')
        return False


def lifo_mounts(root=None):
    """return list of mount points mounted on 'root'
    and below in lifo order from /proc/mounts."""
    with open('/proc/mounts') as proc_mounts:
        # grab the mountpoint for each mount where we MIGHT match
        mount_entries = [line.split(' ')[1] for line in proc_mounts if root in line]
    if not mount_entries:
        # return an empty list if we didn't match
        return mount_entries
    return [entry for entry in reversed(mount_entries)
            if entry == root or entry.startswith(root + '/')]


def copy_image(src=None, dst=None):
    """dd like utility for copying image files.
       eg.
       copy_image('/dev/sdf1','/mnt/bundles/ami-name.img')
    """
    try:
        src_fd = os.open(src, os.O_RDONLY)
        dst_fd = os.open(dst, os.O_WRONLY | os.O_CREAT, 0644)
        blks = 0
        blksize = 64 * 1024
        log.debug("copying {0} to {1}".format(src,dst))
        while True:
            buf = os.read(src_fd, blksize)
            if len(buf) <= 0:
                log.debug("{0} {1} blocks written.".format(blks,blksize))
                os.close(src_fd)
                os.close(dst_fd)
                break
            out = os.write(dst_fd, buf)
            if out < blksize:
                log.debug('wrote {0} bytes.'.format(out))
            blks += 1
    except OSError as e:
        log.debug("{0}: errno[{1}]: {2}.".format(e.filename, e.errno, e.strerror))
        return False
    return True


@contextmanager
def flock(filename=None):
    """simple blocking exclusive file locker
       eg:
       with flock(lockfilepath):
           ...
    """
    with open(filename, 'a') as fh:
        _flock(fh, LOCK_EX)
        yield
        _flock(fh, LOCK_UN)


def locked(filename=None):
    """
    :param filename:
    :return: True if file is locked.
    """
    with open(filename, 'a') as fh:
        try:
            _flock(fh, LOCK_EX | LOCK_NB)
            ret = False
        except IOError as e:
            log.debug('{0} is locked: {1}'.format(filename, e))
            ret = True
    return ret


def root_check():
    """
    Simple root gate
    :return: errno.EACCESS if not running as root, None if running as root
    """
    if os.geteuid() != 0:
        return errno.EACCES
    return None


def native_device_prefix(prefixes):
    log.debug('Getting the OS-native device prefix from potential prefixes: {0}'.format(prefixes))
    for prefix in prefixes:
        if any(device.startswith(prefix) for device in os.listdir('/sys/block')):
            log.debug('Native prefix is {0}'.format(prefix))
            return prefix
    log.debug('{0} contains no native device prefixes'.format(prefixes))
    return None


def device_prefix(source_device):
    log.debug('Getting prefix for device {0}'.format(source_device))
    # strip off any incoming /dev/ foo
    source_device_name = os.path.basename(source_device)
    # if we have a subdevice/partition...
    if source_device_name[-1].isdigit():
        # then its prefix is the name minus the last TWO chars
        log.debug('Device prefix for {0} is {1}'.format(source_device, source_device_name[:-2:]))
        return source_device_name[:-2:]
    else:
        # otherwise, just strip the last one
        log.debug('Device prefix for {0} is {1}'.format(source_device, source_device_name[:-1:]))
        return source_device_name[:-1:]


def native_block_device(source_device, native_prefix):
    source_device_prefix = device_prefix(source_device)
    if source_device_prefix == native_prefix:
        # we're okay, using the right name already, just return the same name
        return source_device
    else:
        # sub out the bad prefix for the good
        return source_device.replace(source_device_prefix, native_prefix)


def os_node_exists(dev):
    try:
        mode = os.stat(dev).st_mode
    except OSError:
        return False
    return stat.S_ISBLK(mode)


def install_provision_config(src, dstpath, backup_ext='_aminator'):
    if os.path.isfile(src) or os.path.isdir(src):
        log.debug('Copying {0} from the aminator host to {1}'.format(src, dstpath))
        dst = os.path.join(dstpath.rstrip('/'), src.lstrip('/'))
        log.debug('copying src: {0} dst: {1}'.format(src, dst))
        try:
            if os.path.isfile(dst) or os.path.islink(dst) or os.path.isdir(dst):
                backup = '{0}{1}'.format(dst, backup_ext)
                log.debug('Making backup of {0}'.format(dst))
                try:
                    if os.path.isdir(dst) or os.path.islink(dst):
                        os.rename(dst, backup)
                    elif os.path.isfile(dst):
                        shutil.copy(dst,backup)
                except Exception:
                    log.exception('Error encountered while copying {0} to {1}'.format(dst, backup))
                    return False
            if os.path.isdir(src):
                shutil.copytree(src,dst,symlinks=True)
            else:
                shutil.copy(src,dst)
        except Exception:
            log.exception('Error encountered while copying {0} to {1}'.format(src, dst))
            return False
        log.debug('{0} copied from aminator host to {1}'.format(src, dstpath))
        return True
    else:
        log.critical('File not found: {0}'.format(src))
        return True


def install_provision_configs(files, dstpath, backup_ext='_aminator'):
    for filename in files:
        if not install_provision_config(filename, dstpath, backup_ext):
            return False
    return True


def remove_provision_config(src, dstpath, backup_ext='_aminator'):
    dst = os.path.join(dstpath.rstrip('/'), src.lstrip('/'))
    backup = '{0}{1}'.format(dst, backup_ext)
    try:
        if os.path.isfile(dst) or os.path.islink(dst) or os.path.isdir(dst):
            try:
                if os.path.isdir(dst):
                    log.debug('Removing {0}'.format(dst))
                    shutil.rmtree(dst)
                    log.debug('Provision config {0} removed'.format(dst))
            except Exception:
                log.exception('Error encountered while removing {0}'.format(dst))
                return False

        if os.path.isfile(backup) or os.path.islink(backup) or os.path.isdir(backup):
            log.debug('Restoring {0} to {1}'.format(backup, dst))
            if os.path.isdir(backup) or os.path.islink(backup):
                os.rename(backup, dst)
            elif os.path.isfile(backup):
                shutil.copy(backup,dst)
            log.debug('Restoration of {0} to {1} successful'.format(backup, dst))
        else:
            log.warn('No backup file {0} was found'.format(backup))
    except Exception:
        log.exception('Error encountered while restoring {0} to {1}'.format(backup, dst))
        return False
    return True


def remove_provision_configs(sources, dstpath, backup_ext='_aminator'):
    for filename in sources:
        if not remove_provision_config(filename, dstpath, backup_ext):
            return False
    return True


def short_circuit(root, cmd, ext='short_circuit', dst='/bin/true'):
    fullpath = os.path.join(root.rstrip('/'), cmd.lstrip('/'))
    if os.path.isfile(fullpath):
        try:
            log.debug('Short circuiting {0}'.format(fullpath))
            os.rename(fullpath, '{0}.{1}'.format(fullpath, ext))
            log.debug('{0} renamed to {0}.{1}'.format(fullpath, ext))
            os.symlink(dst, fullpath)
            log.debug('{0} linked to {1}'.format(fullpath, dst))
        except Exception:
            log.exception('Error encountered while short circuiting {0} to {1}'.format(fullpath, dst))
            return False
        else:
            log.debug('short circuited {0} to {1}'.format(fullpath, dst))
            return True
    else:
        log.error('{0} not found'.format(fullpath))
        return False


def short_circuit_files(root, cmds, ext='short_circuit', dst='/bin/true'):
    for cmd in cmds:
        if not short_circuit(root, cmd, ext, dst):
            return False
    return True


def rewire(root, cmd, ext='short_circuit'):
    fullpath = os.path.join(root.rstrip('/'), cmd.lstrip('/'))
    if os.path.isfile('{0}.{1}'.format(fullpath, ext)):
        try:
            log.debug('Rewiring {0}'.format(fullpath))
            os.remove(fullpath)
            os.rename('{0}.{1}'.format(fullpath, ext), fullpath)
            log.debug('{0} rewired'.format(fullpath))
        except Exception:
            log.exception('Error encountered while rewiring {0}'.format(fullpath))
            return False
        else:
            log.debug('rewired {0}'.format(fullpath))
            return True
    else:
        log.error('{0}.{1} not found'.format(fullpath, ext))
        return False


def rewire_files(root, cmds, ext='short_circuit'):
    for cmd in cmds:
        if not rewire(root, cmd, ext):
            return False
    return True


def mkdir_p(path):
    try:
        if os.path.isdir(path):
            return

        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise e

########NEW FILE########
__FILENAME__ = metrics
# -*- coding: utf-8 -*-

#
#
#  Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#

"""
aminator.util.metrics
===================
Metrics utility functions
"""

from time import time

def timer(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            start = time()
            try:
                retval = func(obj, *args, **kwargs)
                (context_obj or obj)._config.metrics.timer(metric_name, time() - start)
            except:
                (context_obj or obj)._config.metrics.timer(metric_name, time() - start)
                raise
            return retval
        return func_2
    return func_1

def lapse(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            (context_obj or obj)._config.metrics.start_timer(metric_name)
            try:
                retval = func(obj, *args, **kwargs)
                (context_obj or obj)._config.metrics.stop_timer(metric_name)
            except:
                (context_obj or obj)._config.metrics.stop_timer(metric_name)
                raise
            return retval
        return func_2
    return func_1

def fails(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            try:
                retval = func(obj, *args, **kwargs)
            except:
                (context_obj or obj)._config.metrics.increment(metric_name)
                raise
            if not retval:
                (context_obj or obj)._config.metrics.increment(metric_name)
            return retval
        return func_2
    return func_1

def cmdfails(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            try:
                retval = func(obj, *args, **kwargs)
            except:
                (context_obj or obj)._config.metrics.increment(metric_name)
                raise
            if not retval or not retval.success:
                (context_obj or obj)._config.metrics.increment(metric_name)
            return retval
        return func_2
    return func_1

def cmdsucceeds(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            retval = func(obj, *args, **kwargs)
            if retval and retval.success:
                (context_obj or obj)._config.metrics.increment(metric_name)
            return retval
        return func_2
    return func_1

def succeeds(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            retval = func(obj, *args, **kwargs)
            if retval:
                (context_obj or obj)._config.metrics.increment(metric_name)
            return retval
        return func_2
    return func_1

def raises(metric_name, context_obj=None):
    def func_1(func):
        def func_2(obj, *args, **kwargs):
            try:
                return func(obj, *args, **kwargs)
            except:
                (context_obj or obj)._config.metrics.increment(metric_name)
                raise
        return func_2
    return func_1
    

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# aminator documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 14 18:38:34 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'aminator'
copyright = u'2013, Netflix, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'aminatordoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'aminator.tex', u'aminator Documentation',
   u'Netflix, Inc.', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'aminator', u'aminator Documentation',
     [u'Netflix, Inc.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'aminator', u'aminator Documentation',
   u'Netflix, Inc.', 'aminator', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = TestAptProvisionerPlugin
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#
import logging
import os

from aminator.util.linux import keyval_parse, Response, CommandResult

from aminator.plugins.provisioner.apt import AptProvisionerPlugin
from aminator.config import Config
from collections import namedtuple

log = logging.getLogger(__name__)
console = logging.StreamHandler()
# add the handler to the root logger
logging.getLogger('').addHandler(console)


class TestAptProvisionerPlugin(object):

    def setup_method(self, method):
        self.config = Config()
        self.config.plugins = Config()

        # TODO: this is fragile as it may depend on the dir the tests were run from
        self.config.plugins['aminator.plugins.provisioner.apt'] = self.config.from_file(yaml_file='aminator/plugins/provisioner/default_conf/aminator.plugins.provisioner.apt.yml')

        log.info(self.config.plugins)
        self.plugin = AptProvisionerPlugin()

        self.plugin._config = self.config

        config = self.plugin._config.plugins['aminator.plugins.provisioner.apt']

        # use /tmp if not configured, ideally to use tempfile, but needs C build
        self.full_path = config.get('mountpoint', '/tmp') + "/" + \
                         config.get('policy_file_path', '/usr/sbin') + "/" + \
                         config.get('policy_file', 'policy-rc.d')

        self.plugin._mountpoint = config.get('mountpoint', '/tmp')

        # cleanup
        if os.path.isfile(self.full_path):
            os.remove(self.full_path)

    def test_disable_enable_service_startup(self):
        assert self.plugin._deactivate_provisioning_service_block()
        assert os.path.isfile(self.full_path)

        with open(self.full_path) as f:
            content = f.readlines()

        # remove whitespace and newlines
        content = map(lambda s: s.strip(), content)
        # also remove whitespace and newlines
        original_content = self.config.plugins['aminator.plugins.provisioner.apt'].get('policy_file_content').splitlines()

        assert original_content == content

        assert self.plugin._activate_provisioning_service_block()
        assert False == os.path.isfile(self.full_path)

    def test_metadata(self):
        """ test that given we get back the metadata we expect
            this first was a problem when the deb Description field had leading whitespace
            which caused the keys to contain leading whitespace
        """

        response = Response()
        response.std_out = """
  Package: helloWorld
  Source: helloWorld
  Version: 1374197704:1.0.0-h357.6ea8a16
  Section: None
  Priority: optional
  Architecture: all
  Provides: helloWorld
  Installed-Size: 102704
  Maintainer: someone@somewhere.org
  Description: helloWorld
   ----------
   Manifest-Version: 1.1
   Implementation-Vendor: Hello, Inc.
   Implementation-Title: helloWorld;1.0.0
   Implementation-Version: 1.0.0
   Label: helloWorld-1.0.0
   Built-By: builder
   Build-Job: JOB-helloWorld
   Build-Date: 2013-07-19_01:33:52
   Build-Number: 357
   Build-Id: 2013-07-18_18-24-53
   Change: 6ea8a16
"""
        package_query_result = CommandResult(True, response)
        result = parse_command_result(package_query_result)

        assert result['Build-Number'] == '357'
        assert result['Build-Job'] == 'JOB-helloWorld'

@keyval_parse()
def parse_command_result(data):
    return data

########NEW FILE########
__FILENAME__ = test_yum_provisioner_plugin
# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#
import logging
import os
from aminator.plugins.provisioner.yum import YumProvisionerPlugin
from aminator.config import Config

log = logging.getLogger(__name__)
console = logging.StreamHandler()
# add the handler to the root logger
logging.getLogger('').addHandler(console)

class TestYumProvisionerPlugin(object):

    def setup_method(self, method):
        self.config = Config()
        self.config.plugins = Config()
        self.config.plugins['aminator.plugins.provisioner.yum'] = self.config.from_file(yaml_file='yum_test.yml')

        self.plugin = YumProvisionerPlugin()
        self.plugin._config = self.config

    def test_deactivate_active_services(self):

        files = self.plugin._config.plugins['aminator.plugins.provisioner.yum'].get('short_circuit_files', [])

        if len(files) != 1:
            raise AttributeError("incorrect number of files specified.  found %d expected 1", len(files))

        filename = files[0]

        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        # cleanup
        if os.path.islink(filename):
            log.debug("removing %s", filename)
            os.remove(filename)

        with open(filename, 'w') as f:
            log.debug("writing %s", filename)
            f.write("test")
            log.debug("wrote %s", filename)

        assert self.plugin._deactivate_provisioning_service_block()
        assert True == os.path.islink('/tmp/sbin/service')
        assert self.plugin._activate_provisioning_service_block()
        assert False == os.path.islink('/tmp/sbin/service')

########NEW FILE########
__FILENAME__ = util
import aminator.util.linux
import unittest
import os
import logging
import shutil
import tempfile

log = logging.getLogger(__name__)
logging.root.addHandler(logging.StreamHandler())
logging.root.setLevel(logging.DEBUG)


class linux_util(unittest.TestCase):
    src_root = tempfile.mkdtemp(dir='/tmp', prefix='src_')
    dst_root = tempfile.mkdtemp(dir='/tmp', prefix='dst_')

    files = ['a', 'b', 'c', 'd', 'Da', 'Db', 'Dc', 'Dd']

    def test_provision_configs(self):
        """ test install_provision_configs and remove_provision_configs against
        self.files.
        Test matrix:
            files    src_exists     dst_exists
            a            y              y
            b            y              n
            c            n              y
            d            n              n
            Da           y              y
            Db           y              n
            Dc           n              y
            Dd           n              n
        """
        # create /dst_root/src_root
        dst_dir = os.path.join(self.dst_root, self.src_root.lstrip('/'))
        os.makedirs(dst_dir)
        # /src_root/{a,b}
        open(os.path.join(self.src_root, 'a'), 'w').close()
        open(os.path.join(self.src_root, 'b'), 'w').close()

        # dirs /src_root/{Da/a,{Db/b}
        os.mkdir(os.path.join(self.src_root, 'Da'))
        open(os.path.join(self.src_root, 'Da', 'a'), 'w').close()
        os.mkdir(os.path.join(self.src_root, 'Db'))
        open(os.path.join(self.src_root, 'Db', 'b'), 'w').close()
        
        # /dst_root/src_root/{a,c}
        open(os.path.join(dst_dir, 'a'), 'w').close()
        open(os.path.join(dst_dir, 'c'), 'w').close()

        # dirs /dst_root/src_root/{Da/a,{Dc/c}
        os.mkdir(os.path.join(dst_dir, 'Da'))
        open(os.path.join(dst_dir, 'Da', 'a'), 'w').close()
        os.mkdir(os.path.join(dst_dir, 'Dc'))
        open(os.path.join(dst_dir, 'Dc', 'c'), 'w').close()

        provision_config_files = [os.path.join(self.src_root, x) for x in self.files]

        install_status = aminator.util.linux.install_provision_configs(provision_config_files, self.dst_root)
        remove_status = aminator.util.linux.remove_provision_configs(provision_config_files, self.dst_root)

        shutil.rmtree(self.src_root)
        shutil.rmtree(self.dst_root)

        assert install_status & remove_status


if __name__ == "__main__":
        unittest.main()

########NEW FILE########
