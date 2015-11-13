__FILENAME__ = base_log
# -*- coding: utf-8 -*-


class BaseLog(object):

    def __init__(self, logger=None):
        self._logger = logger

    def _log_debug(self, message):
        if self._logger:
            self._logger.debug(self._log_template.format(message))

    def _log_info(self, message):
        if self._logger:
            self._logger.info(self._log_template.format(message))

    def _log_warning(self, message):
        if self._logger:
            self._logger.warning(self._log_template.format(message))

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
import logging
import os
import re
import socket
import warnings

from conf_d import Configuration
from beaver.utils import eglob
from beaver.glob_safe_config_parser import GlobSafeConfigParser

class BeaverConfig():

    def __init__(self, args, logger=None):
        self._logger = logger or logging.getLogger(__name__)
        self._logger.debug('Processing beaver portion of config file %s' % args.config)

        self._section_defaults = {
            'add_field': '',
            'add_field_env': '',
            'debug': '0',
            'discover_interval': '15',
            'encoding': 'utf_8',

            # should be a python regex of files to remove
            'exclude': '',
            'format': '',

            # throw out empty lines instead of shipping them
            'ignore_empty': '0',

            # allow ignoring copytruncate results
            'ignore_truncate': '0',

            # buffered tokenization
            # we string-escape the delimiter later so that we can put escaped characters in our config file
            'delimiter': '\n',
            'size_limit': '',

            # multiline events support. Default is disabled
            'multiline_regex_after': '',
            'multiline_regex_before': '',

            'message_format': '',
            'sincedb_write_interval': '15',
            'stat_interval': '1',
            'start_position': 'end',
            'tags': '',
            'tail_lines': '0',
            'type': '',
        }

        self._main_defaults = {
            'mqtt_clientid': 'mosquitto',
            'mqtt_host': 'localhost',
            'mqtt_port': '1883',
            'mqtt_topic': '/logstash',
            'mqtt_keepalive': '60',
            'rabbitmq_host': os.environ.get('RABBITMQ_HOST', 'localhost'),
            'rabbitmq_port': os.environ.get('RABBITMQ_PORT', '5672'),
            'rabbitmq_ssl': '0',
            'rabbitmq_ssl_key': '',
            'rabbitmq_ssl_cert': '',
            'rabbitmq_ssl_cacert': '',
            'rabbitmq_vhost': os.environ.get('RABBITMQ_VHOST', '/'),
            'rabbitmq_username': os.environ.get('RABBITMQ_USERNAME', 'guest'),
            'rabbitmq_password': os.environ.get('RABBITMQ_PASSWORD', 'guest'),
            'rabbitmq_queue': os.environ.get('RABBITMQ_QUEUE', 'logstash-queue'),
            'rabbitmq_exchange_type': os.environ.get('RABBITMQ_EXCHANGE_TYPE', 'direct'),
            'rabbitmq_exchange_durable': os.environ.get('RABBITMQ_EXCHANGE_DURABLE', '0'),
            'rabbitmq_queue_durable': os.environ.get('RABBITMQ_QUEUE_DURABLE', '0'),
            'rabbitmq_ha_queue': os.environ.get('RABBITMQ_HA_QUEUE', '0'),
            'rabbitmq_key': os.environ.get('RABBITMQ_KEY', 'logstash-key'),
            'rabbitmq_exchange': os.environ.get('RABBITMQ_EXCHANGE', 'logstash-exchange'),
            'redis_url': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
            'redis_namespace': os.environ.get('REDIS_NAMESPACE', 'logstash:beaver'),
            'redis_password': '',
            'sqs_aws_access_key': '',
            'sqs_aws_secret_key': '',
            'sqs_aws_region': 'us-east-1',
            'sqs_aws_queue': '',
            'tcp_host': '127.0.0.1',
            'tcp_port': '9999',
            'tcp_ssl_enabled': '0',
            'tcp_ssl_verify': '0',
            'tcp_ssl_cacert': '',
            'tcp_ssl_cert': '',
            'udp_host': os.environ.get('UDP_HOST', '127.0.0.1'),
            'udp_port': os.environ.get('UDP_PORT', '9999'),
            'zeromq_address': os.environ.get('ZEROMQ_ADDRESS', 'tcp://localhost:2120'),
            'zeromq_pattern': 'push',
            'zeromq_hwm': os.environ.get('ZEROMQ_HWM', ''),

            # exponential backoff
            'respawn_delay': '3',
            'max_failure': '7',

            # interprocess queue max size before puts block
            'max_queue_size': '100',

            # time in seconds before updating the file mapping
            'update_file_mapping_time': '',  # deprecated
            'discover_interval': '15',

            # time in seconds from last command sent before a queue kills itself
            'queue_timeout': '60',

            # kill and respawn worker process after given number of seconds
            'refresh_worker_process': '',

            # time in seconds to wait on queue.get() block before raising Queue.Empty exception
            'wait_timeout': '5',

            # path to sincedb sqlite db
            'sincedb_path': '',

            # 0 for logstash version < 1.2, 1 for logstash >= 1.2
            'logstash_version': '',

            # ssh tunnel support
            'ssh_key_file': '',
            'ssh_tunnel': '',
            'ssh_tunnel_port': '',
            'ssh_remote_host': '',
            'ssh_remote_port': '',
            'ssh_options': '',
            'subprocess_poll_sleep': '1',

            # the following can be passed via argparse
            'zeromq_bind': os.environ.get('BEAVER_MODE', 'bind' if os.environ.get('BIND', False) else 'connect'),
            'files': os.environ.get('BEAVER_FILES', ''),
            'format': os.environ.get('BEAVER_FORMAT', 'json'),
            'fqdn': '0',
            'hostname': '',
            'output': '',
            'path': os.environ.get('BEAVER_PATH', '/var/log'),
            'transport': os.environ.get('BEAVER_TRANSPORT', 'stdout'),  # this needs to be passed to the import class somehow

            # Path to individual file configs. These override any sections in the main beaver.ini file
            'confd_path': '/etc/beaver/conf.d',

            # the following are parsed before the config file is parsed
            # but may be useful at runtime
            'config': '/dev/null',
            'debug': '0',
            'daemonize': '0',
            'pid': '',
        }

        self._configfile = args.config
        self._config_parser = GlobSafeConfigParser
        self._globbed = []
        self._parse(args)
        for key in self._beaver_config:
            self._logger.debug('[CONFIG] "{0}" => "{1}"'.format(key, self._beaver_config.get(key)))

        self._update_files()
        self._check_for_deprecated_usage()

    def beaver_config(self):
        return self._beaver_config

    def get(self, key, default=None):
        return self._beaver_config.get(key, default)

    def set(self, key, value):
        self._beaver_config[key] = value

    def get_field(self, field, filename):
        return self._files.get(os.path.realpath(filename), self._section_defaults)[field]

    def addglob(self, globname, globbed):
        if globname not in self._globbed:
            self._logger.debug('Adding glob {0}'.format(globname))
            config = self._file_config[globname]
            self._file_config[globname] = config
            for key in config:
                self._logger.debug('Config: "{0}" => "{1}"'.format(key, config[key]))
        else:
            config = self._file_config.get(globname)

        for filename in globbed:
            self._files[filename] = config
        self._globbed.append(globname)

    def getfilepaths(self):
        return self._files.keys()

    def getglobs(self):
        globs = []
        [globs.extend([name, self._file_config[name].get('exclude')]) for name in self._file_config]
        return dict(zip(globs[0::2], globs[1::2]))

    def use_ssh_tunnel(self):
        required = [
            'ssh_key_file',
            'ssh_tunnel',
            'ssh_tunnel_port',
            'ssh_remote_host',
            'ssh_remote_port',
        ]

        has = len(filter(lambda x: self.get(x) is not None, required))
        if has > 0 and has != len(required):
            self._logger.warning('Missing {0} of {1} required config variables for ssh'.format(len(required) - has, len(required)))

        return has == len(required)

    def _check_for_deprecated_usage(self):
        env_vars = [
            'RABBITMQ_HOST',
            'RABBITMQ_PORT',
            'RABBITMQ_VHOST',
            'RABBITMQ_USERNAME',
            'RABBITMQ_PASSWORD',
            'RABBITMQ_QUEUE',
            'RABBITMQ_EXCHANGE_TYPE',
            'RABBITMQ_EXCHANGE_DURABLE',
            'RABBITMQ_KEY',
            'RABBITMQ_EXCHANGE',
            'REDIS_URL',
            'REDIS_NAMESPACE',
            'UDP_HOST',
            'UDP_PORT',
            'ZEROMQ_ADDRESS',
            'BEAVER_FILES',
            'BEAVER_FORMAT',
            'BEAVER_MODE',
            'BEAVER_PATH',
            'BEAVER_TRANSPORT',
        ]

        deprecated_env_var_usage = []

        for e in env_vars:
            v = os.environ.get(e, None)
            if v is not None:
                deprecated_env_var_usage.append(e)

        if len(deprecated_env_var_usage) > 0:
            warnings.simplefilter('default')
            warnings.warn('ENV Variable support will be removed by version 20. Stop using: {0}'.format(', '.join(deprecated_env_var_usage)), DeprecationWarning)

        update_file_mapping_time = self.get('update_file_mapping_time')
        if update_file_mapping_time:
            self.set('discover_interval', update_file_mapping_time)
            warnings.simplefilter('default')
            warnings.warn('"update_file_mapping_time" has been supersceded by "discover_interval". Stop using: "update_file_mapping_time', DeprecationWarning)

    def _parse(self, args):
        def _main_parser(config):
            transpose = ['config', 'confd_path', 'debug', 'daemonize', 'files', 'format', 'fqdn', 'hostname', 'path', 'pid', 'transport']
            namspace_dict = vars(args)
            for key in transpose:
                if key not in namspace_dict or namspace_dict[key] is None or namspace_dict[key] == '':
                    continue

                config[key] = namspace_dict[key]

            if args.mode:
                config['zeromq_bind'] = args.mode

            # HACK: Python 2.6 ConfigParser does not properly
            #       handle non-string values
            for key in config:
                if config[key] == '':
                    config[key] = None

            require_bool = ['debug', 'daemonize', 'fqdn', 'rabbitmq_exchange_durable', 'rabbitmq_queue_durable',
                            'rabbitmq_ha_queue', 'rabbitmq_ssl', 'tcp_ssl_enabled', 'tcp_ssl_verify']

            for key in require_bool:
                config[key] = bool(int(config[key]))

            require_int = [
                'max_failure',
                'max_queue_size',
                'queue_timeout',
                'rabbitmq_port',
                'respawn_delay',
                'subprocess_poll_sleep',
                'refresh_worker_process',
                'tcp_port',
                'udp_port',
                'wait_timeout',
                'zeromq_hwm',
                'logstash_version',
            ]
            for key in require_int:
                if config[key] is not None:
                    config[key] = int(config[key])

            require_float = [
                'update_file_mapping_time',
                'discover_interval',
            ]

            for key in require_float:
                if config[key] is not None:
                    config[key] = float(config[key])

            if config.get('format') == 'null':
                config['format'] = 'raw'

            if config['files'] is not None and type(config['files']) == str:
                config['files'] = config['files'].split(',')

            if config['path'] is not None:
                config['path'] = os.path.realpath(config['path'])
                if not os.path.isdir(config['path']):
                    raise LookupError('{0} does not exist'.format(config['path']))

            if config.get('hostname') is None:
                if config.get('fqdn') is True:
                    config['hostname'] = socket.getfqdn()
                else:
                    config['hostname'] = socket.gethostname()

            if config.get('sincedb_path'):
                config['sincedb_path'] = os.path.realpath(config.get('sincedb_path'))

            if config['zeromq_address'] and type(config['zeromq_address']) == str:
                config['zeromq_address'] = [x.strip() for x in config.get('zeromq_address').split(',')]

            if config.get('ssh_options') is not None:
                csv = config.get('ssh_options')
                config['ssh_options'] = []
                if csv == str:
                    for opt in csv.split(','):
                        config['ssh_options'].append('-o %s' % opt.strip())
            else:
                config['ssh_options'] = []

            config['globs'] = {}

            return config

        def _section_parser(config, raise_exceptions=True):
            '''Parse a given INI-style config file using ConfigParser module.
            Stanza's names match file names, and properties are defaulted as in
            http://logstash.net/docs/1.1.1/inputs/file

            Config file example:

            [/var/log/syslog]
            type: syslog
            tags: sys,main

            [/var/log/auth]
            type: syslog
            ;tags: auth,main
            '''

            fields = config.get('add_field', '')
            if type(fields) != dict:
                try:
                    if type(fields) == str:
                        fields = filter(None, fields.split(','))
                    if len(fields) == 0:
                        config['fields'] = {}
                    elif (len(fields) % 2) == 1:
                        if raise_exceptions:
                            raise Exception('Wrong number of values for add_field')
                    else:
                        fieldkeys = fields[0::2]
                        fieldvalues = [[x] for x in fields[1::2]]
                        config['fields'] = dict(zip(fieldkeys, fieldvalues))
                except TypeError:
                    config['fields'] = {}

            if 'add_field' in config:
                del config['add_field']

            envFields = config.get('add_field_env', '')
            if type(envFields) != dict:
                try:
                    if type(envFields) == str:
                        envFields = envFields.replace(" ","")
                        envFields = filter(None, envFields.split(','))
                    if len(envFields) == 0:
                        config['envFields'] = {}
                    elif (len(envFields) % 2) == 1:
                        if raise_exceptions:
                            raise Exception('Wrong number of values for add_field_env')
                    else:
                        envFieldkeys = envFields[0::2]
                        envFieldvalues = []
                        for x in envFields[1::2]:
                            envFieldvalues.append(os.environ.get(x))
                        config['fields'].update(dict(zip(envFieldkeys, envFieldvalues)))
                except TypeError:
                    config['envFields'] = {}

            if 'add_field_env' in config:
                del config['add_field_env']

            try:
                tags = config.get('tags', '')
                if type(tags) == str:
                    tags = filter(None, tags.split(','))
                if len(tags) == 0:
                    tags = []
                config['tags'] = tags
            except TypeError:
                config['tags'] = []

            if config.get('format') == 'null':
                config['format'] = 'raw'

            file_type = config.get('type', None)
            if not file_type:
                config['type'] = 'file'

            require_bool = ['debug', 'ignore_empty', 'ignore_truncate']
            for k in require_bool:
                config[k] = bool(int(config[k]))

            config['delimiter'] = config['delimiter'].decode('string-escape')

            if config['multiline_regex_after']:
                config['multiline_regex_after'] = re.compile(config['multiline_regex_after'])
            if config['multiline_regex_before']:
                config['multiline_regex_before'] = re.compile(config['multiline_regex_before'])

            require_int = ['sincedb_write_interval', 'stat_interval', 'tail_lines']
            for k in require_int:
                config[k] = int(config[k])

            return config

        conf = Configuration(
            name='beaver',
            path=self._configfile,
            main_defaults=self._main_defaults,
            section_defaults=self._section_defaults,
            main_parser=_main_parser,
            section_parser=_section_parser,
            path_from_main='confd_path',
            config_parser=self._config_parser
        )

        config = conf.raw()
        self._beaver_config = config['beaver']
        self._file_config = config['sections']

        self._main_parser = _main_parser(self._main_defaults)
        self._section_defaults = _section_parser(self._section_defaults, raise_exceptions=False)

        self._files = {}
        for section in config['sections']:
            globs = eglob(section, config['sections'][section].get('exclude', ''))
            if not globs:
                self._logger.debug('Skipping glob due to no files found: %s' % section)
                continue

            for globbed_file in globs:
                self._files[os.path.realpath(globbed_file)] = config['sections'][section]

    def _update_files(self):
        globs = self.get('files', default=[])
        files = self.get('files', default=[])

        if globs:
            globs = dict(zip(globs, [None]*len(globs)))
        else:
            globs = {}

        try:
            files.extend(self.getfilepaths())
            globs.update(self.getglobs())
        except AttributeError:
            files = self.getfilepaths()
            globs = self.getglobs()

        self.set('globs', globs)
        self.set('files', files)

        for f in files:
            if f not in self._file_config:
                self._file_config[f] = self._section_defaults

########NEW FILE########
__FILENAME__ = tail
# -*- coding: utf-8 -*-
import multiprocessing
import Queue
import signal
import os
import time

from beaver.config import BeaverConfig
from beaver.run_queue import run_queue
from beaver.ssh_tunnel import create_ssh_tunnel
from beaver.utils import REOPEN_FILES, setup_custom_logger
from beaver.worker.tail_manager import TailManager


def run(args=None):
    logger = setup_custom_logger('beaver', args)

    beaver_config = BeaverConfig(args, logger=logger)
    if beaver_config.get('logstash_version') not in [0, 1]:
        raise LookupError("Invalid logstash_version")

    queue = multiprocessing.JoinableQueue(beaver_config.get('max_queue_size'))

    manager_proc = None
    ssh_tunnel = create_ssh_tunnel(beaver_config, logger=logger)

    def queue_put(*args):
        return queue.put(*args)

    def queue_put_nowait(*args):
        return queue.put_nowait(*args)

    def cleanup(signalnum, frame):
        if signalnum is not None:
            sig_name = tuple((v) for v, k in signal.__dict__.iteritems() if k == signalnum)[0]
            logger.info("{0} detected".format(sig_name))
            logger.info("Shutting down. Please wait...")
        else:
            logger.info('Worker process cleanup in progress...')

        try:
            queue_put_nowait(("exit", ()))
        except Queue.Full:
            pass

        if manager_proc is not None:
            try:
                manager_proc.terminate()
                manager_proc.join()
            except RuntimeError:
                pass

        if ssh_tunnel is not None:
            logger.info("Closing ssh tunnel...")
            ssh_tunnel.close()

        if signalnum is not None:
            logger.info("Shutdown complete.")
            return os._exit(signalnum)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGQUIT, cleanup)

    def create_queue_consumer():
        process_args = (queue, beaver_config, logger)
        proc = multiprocessing.Process(target=run_queue, args=process_args)

        logger.info("Starting queue consumer")
        proc.start()
        return proc

    def create_queue_producer():
        manager = TailManager(
            beaver_config=beaver_config,
            queue_consumer_function=create_queue_consumer,
            callback=queue_put,
            logger=logger
        )
        manager.run()

    while 1:

        try:

            if REOPEN_FILES:
                logger.debug("Detected non-linux platform. Files will be reopened for tailing")

            t = time.time()
            while True:
                if manager_proc is None or not manager_proc.is_alive():
                    logger.info('Starting worker...')
                    t = time.time()
                    manager_proc = multiprocessing.Process(target=create_queue_producer)
                    manager_proc.start()
                    logger.info('Working...')
                manager_proc.join(10)

                if beaver_config.get('refresh_worker_process'):
                    if beaver_config.get('refresh_worker_process') < time.time() - t:
                        logger.info('Worker has exceeded refresh limit. Terminating process...')
                        cleanup(None, None)

        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -*-
import multiprocessing
import Queue
import signal
import os
import time

from beaver.config import BeaverConfig
from beaver.run_queue import run_queue
from beaver.ssh_tunnel import create_ssh_tunnel
from beaver.utils import setup_custom_logger, REOPEN_FILES
from beaver.worker.worker import Worker

def run(args=None):
    logger = setup_custom_logger('beaver', args)

    beaver_config = BeaverConfig(args, logger=logger)
    if beaver_config.get('logstash_version') not in [0, 1]:
        raise LookupError("Invalid logstash_version")

    queue = multiprocessing.Queue(beaver_config.get('max_queue_size'))

    worker_proc = None
    ssh_tunnel = create_ssh_tunnel(beaver_config, logger=logger)

    def cleanup(signalnum, frame):
        if signalnum is not None:
            sig_name = tuple((v) for v, k in signal.__dict__.iteritems() if k == signalnum)[0]
            logger.info('{0} detected'.format(sig_name))
            logger.info('Shutting down. Please wait...')
        else:
            logger.info('Worker process cleanup in progress...')

        try:
            queue.put_nowait(('exit', ()))
        except Queue.Full:
            pass

        if worker_proc is not None:
            try:
                worker_proc.terminate()
                worker_proc.join()
            except RuntimeError:
                pass

        if ssh_tunnel is not None:
            logger.info('Closing ssh tunnel...')
            ssh_tunnel.close()

        if signalnum is not None:
            logger.info('Shutdown complete.')
            return os._exit(signalnum)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGQUIT, cleanup)

    def create_queue_consumer():
        process_args = (queue, beaver_config, logger)
        proc = multiprocessing.Process(target=run_queue, args=process_args)

        logger.info('Starting queue consumer')
        proc.start()
        return proc

    def create_queue_producer():
        worker = Worker(beaver_config, queue_consumer_function=create_queue_consumer, callback=queue.put, logger=logger)
        worker.loop()

    while 1:

        try:
            if REOPEN_FILES:
                logger.debug('Detected non-linux platform. Files will be reopened for tailing')

            t = time.time()
            while True:
                if worker_proc is None or not worker_proc.is_alive():
                    logger.info('Starting worker...')
                    t = time.time()
                    worker_proc = multiprocessing.Process(target=create_queue_producer)
                    worker_proc.start()
                    logger.info('Working...')
                worker_proc.join(10)

                if beaver_config.get('refresh_worker_process'):
                    if beaver_config.get('refresh_worker_process') < time.time() - t:
                        logger.info('Worker has exceeded refresh limit. Terminating process...')
                        cleanup(None, None)

        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = glob_safe_config_parser
# -*- coding: utf-8 -*-
import ConfigParser
import re

"""
Allows use of square brackets in .ini section names, which are used in some globs.
Based off of python 2.6 ConfigParser.RawConfigParser source code with a few modifications.
http://hg.python.org/cpython/file/8c4d42c0dc8e/Lib/configparser.py
"""
class GlobSafeConfigParser(ConfigParser.RawConfigParser):

    OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'
        r'\s*(?P<vi>[:=])\s*'       
        r'(?P<value>.*)$'           
        )

    def _read(self, fp, fpname):
        cursect = None
        optname = None
        lineno = 0
        e = None
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                continue
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            else:
                try:
                  value = line[:line.index(';')].strip()
                except ValueError:
                  value = line.strip()

                if  value[0]=='[' and value[-1]==']' and len(value)>2:
                    sectname = value[1:-1]
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    elif sectname == "DEFAULT":
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        cursect['__name__'] = sectname
                        self._sections[sectname] = cursect
                    optname = None
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                else:
                    mo = self.OPTCRE.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if vi in ('=', ':') and ';' in optval:
                            pos = optval.find(';')
                            if pos != -1 and optval[pos-1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                    else:
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, repr(line))
        if e:
            raise e

########NEW FILE########
__FILENAME__ = pidfile
# -*- coding: utf-8 -*-
import fcntl
import os


class PidFile(object):
    """Context manager that locks a pid file.  Implemented as class
    not generator because daemon.py is calling .__exit__() with no parameters
    instead of the None, None, None specified by PEP-343.

    From http://code.activestate.com/recipes/577911-context-manager-for-a-daemon-pid-file/
    """

    def __init__(self, path):
        """Initializes path for pidfile"""
        self.path = os.path.realpath(path)
        self.pidfile = None

    def __enter__(self):
        """Writes the pid of the current process to the path"""
        self.pidfile = open(self.path, 'a+')
        try:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise SystemExit('Already running according to {0}'.format(self.path))
        self.pidfile.seek(0)
        self.pidfile.truncate()
        self.pidfile.write(str(os.getpid()))
        self.pidfile.flush()
        self.pidfile.seek(0)
        return self.pidfile

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        """Removes the pid for the current process"""
        try:
            self.pidfile.close()
        except IOError as err:
            # ok if file was just closed elsewhere
            if err.errno != 9:
                raise
        os.remove(self.path)

########NEW FILE########
__FILENAME__ = run_queue
# -*- coding: utf-8 -*-
import Queue
import signal
import sys
import time

from beaver.transports import create_transport
from beaver.transports.exception import TransportException
from unicode_dammit import unicode_dammit


def run_queue(queue, beaver_config, logger=None):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGQUIT, signal.SIG_DFL)

    last_update_time = int(time.time())
    queue_timeout = beaver_config.get('queue_timeout')
    wait_timeout = beaver_config.get('wait_timeout')

    transport = None
    try:
        logger.debug('Logging using the {0} transport'.format(beaver_config.get('transport')))
        transport = create_transport(beaver_config, logger=logger)

        failure_count = 0
        while True:
            if not transport.valid():
                logger.info('Transport connection issues, stopping queue')
                break

            if int(time.time()) - last_update_time > queue_timeout:
                logger.info('Queue timeout of "{0}" seconds exceeded, stopping queue'.format(queue_timeout))
                break

            try:
                command, data = queue.get(block=True, timeout=wait_timeout)
                if command == "callback":
                    last_update_time = int(time.time())
                    logger.debug('Last update time now {0}'.format(last_update_time))
            except Queue.Empty:
                logger.debug('No data')
                continue

            if command == 'callback':
                if data.get('ignore_empty', False):
                    logger.debug('removing empty lines')
                    lines = data['lines']
                    new_lines = []
                    for line in lines:
                        message = unicode_dammit(line)
                        if len(message) == 0:
                            continue
                        new_lines.append(message)
                    data['lines'] = new_lines

                if len(data['lines']) == 0:
                    logger.debug('0 active lines sent from worker')
                    continue

                while True:
                    try:
                        transport.callback(**data)
                        break
                    except TransportException:
                        failure_count = failure_count + 1
                        if failure_count > beaver_config.get('max_failure'):
                            failure_count = beaver_config.get('max_failure')

                        sleep_time = beaver_config.get('respawn_delay') ** failure_count
                        logger.info('Caught transport exception, reconnecting in %d seconds' % sleep_time)

                        try:
                            transport.invalidate()
                            time.sleep(sleep_time)
                            transport.reconnect()
                            if transport.valid():
                                failure_count = 0
                                logger.info('Reconnected successfully')
                        except KeyboardInterrupt:
                            logger.info('User cancelled respawn.')
                            transport.interrupt()
                            sys.exit(0)
            elif command == 'addglob':
                beaver_config.addglob(*data)
                transport.addglob(*data)
            elif command == 'exit':
                break
    except KeyboardInterrupt:
        logger.debug('Queue Interruped')
        if transport is not None:
            transport.interrupt()

        logger.debug('Queue Shutdown')

########NEW FILE########
__FILENAME__ = ssh_tunnel
# -*- coding: utf-8 -*-
import os
import signal
import subprocess
import time

from beaver.base_log import BaseLog


def create_ssh_tunnel(beaver_config, logger=None):
    """Returns a BeaverSshTunnel object if the current config requires us to"""
    if not beaver_config.use_ssh_tunnel():
        return None

    logger.info("Proxying transport using through local ssh tunnel")
    return BeaverSshTunnel(beaver_config, logger=logger)


class BeaverSubprocess(BaseLog):
    """General purpose subprocess wrapper"""

    def __init__(self, beaver_config, logger=None):
        """Child classes should build a subprocess via the following method:

           self._subprocess = subprocess.Popen(cmd, stdout=subprocess.PIPE, preexec_fn=os.setsid)

        This will allow us to attach a session id to the spawned child, allowing
        us to send a SIGTERM to the process on close
        """
        super(BeaverSubprocess, self).__init__(logger=logger)
        self._log_template = '[BeaverSubprocess] - {0}'

        self._beaver_config = beaver_config
        self._command = 'sleep 1'
        self._subprocess = None
        self._logger = logger

    def run(self):
        self._log_debug('Running command: {0}'.format(self._command))
        self._subprocess = subprocess.Popen(['/bin/sh', '-c', self._command], preexec_fn=os.setsid)
        self.poll()

    def poll(self):
        """Poll attached subprocess until it is available"""
        if self._subprocess is not None:
            self._subprocess.poll()

        time.sleep(self._beaver_config.get('subprocess_poll_sleep'))

    def close(self):
        """Close child subprocess"""
        if self._subprocess is not None:
            os.killpg(self._subprocess.pid, signal.SIGTERM)
            self._subprocess = None


class BeaverSshTunnel(BeaverSubprocess):
    """SSH Tunnel Subprocess Wrapper"""

    def __init__(self, beaver_config, logger=None):
        super(BeaverSshTunnel, self).__init__(beaver_config, logger=logger)
        self._log_template = '[BeaverSshTunnel] - {0}'

        key_file = beaver_config.get('ssh_key_file')
        tunnel = beaver_config.get('ssh_tunnel')
        tunnel_port = beaver_config.get('ssh_tunnel_port')
        remote_host = beaver_config.get('ssh_remote_host')
        remote_port = beaver_config.get('ssh_remote_port')

        ssh_opts = []
        if self.get_port(tunnel):
            ssh_opts.append('-p {0}'.format(self.get_port(tunnel)))
            tunnel = self.get_host(tunnel)

        ssh_opts.append('-n')
        ssh_opts.append('-N')
        ssh_opts.append('-o BatchMode=yes')
        ssh_opts = ssh_opts + beaver_config.get('ssh_options')

        command = 'while true; do ssh {0} -i "{4}" "{5}" -L "{1}:{2}:{3}"; sleep 10; done'
        self._command = command.format(' '.join(ssh_opts), tunnel_port, remote_host, remote_port, key_file, tunnel)

        self.run()

    def get_host(self, tunnel=None):
        port = self.get_port(tunnel)
        if not port:
            return tunnel

        return tunnel[0:-(len(port) + 1)]

    def get_port(self, tunnel=None):
        host_port = None
        port = None

        if tunnel:
            host_port = tunnel.split('@')[-1]

        if host_port and len(host_port.split(':')) == 2:
            port = host_port.split(':')[-1]

        return port

########NEW FILE########
__FILENAME__ = test_glob_sections
# -*- coding: utf-8 -*-
import unittest 
import os
import glob
from beaver.config import BeaverConfig

class ConfigTests(unittest.TestCase):

    def setUp(self):
        self.config = lambda: None
        self.config.config = 'tests/square_bracket_sections.ini'
        self.config.mode = 'bind'
        self.beaver_config = BeaverConfig(self.config)

    def test_globs(self):
        files = [os.path.realpath(x) for x in glob.glob('tests/logs/0x[0-9]*.log')]
        for file in self.beaver_config.getfilepaths():
            self.assertTrue(file in files)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_transport_config
# -*- coding: utf-8 -*-
import fakeredis
import logging
import mock
import tempfile
import unittest

import beaver
from beaver.config import BeaverConfig
from beaver.transports import create_transport
from beaver.transports.base_transport import BaseTransport


class DummyTransport(BaseTransport):
    pass


with mock.patch('pika.adapters.BlockingConnection', autospec=True) as mock_pika:

    class TransportConfigTests(unittest.TestCase):
        def setUp(self):
            self.logger = logging.getLogger(__name__)

        def _get_config(self, **kwargs):
            empty_conf = tempfile.NamedTemporaryFile(delete=True)
            return BeaverConfig(mock.Mock(config=empty_conf.name, **kwargs))

        @mock.patch('pika.adapters.BlockingConnection', mock_pika)
        def test_builtin_rabbitmq(self):
            beaver_config = self._get_config(transport='rabbitmq')
            transport = create_transport(beaver_config, logger=self.logger)
            self.assertIsInstance(transport, beaver.transports.rabbitmq_transport.RabbitmqTransport)

        @mock.patch('redis.StrictRedis', fakeredis.FakeStrictRedis)
        def test_builtin_redis(self):
            beaver_config = self._get_config(transport='redis')
            transport = create_transport(beaver_config, logger=self.logger)
            self.assertIsInstance(transport, beaver.transports.redis_transport.RedisTransport)

        def test_builtin_stdout(self):
            beaver_config = self._get_config(transport='stdout')
            transport = create_transport(beaver_config, logger=self.logger)
            self.assertIsInstance(transport, beaver.transports.stdout_transport.StdoutTransport)

        def test_builtin_udp(self):
            beaver_config = self._get_config(transport='udp')
            transport = create_transport(beaver_config, logger=self.logger)
            self.assertIsInstance(transport, beaver.transports.udp_transport.UdpTransport)

        def test_builtin_zmq(self):
            beaver_config = self._get_config(transport='zmq')
            transport = create_transport(beaver_config, logger=self.logger)
            self.assertIsInstance(transport, beaver.transports.zmq_transport.ZmqTransport)

        def test_custom_transport(self):
            beaver_config = self._get_config(transport='beaver.tests.test_transport_config.DummyTransport')
            transport = create_transport(beaver_config, logger=self.logger)
            self.assertIsInstance(transport, DummyTransport)

########NEW FILE########
__FILENAME__ = test_zmq_transport
# -*- coding: utf-8 -*-
import mock
import unittest
import tempfile

from beaver.config import BeaverConfig

try:
    from beaver.transports.zmq_transport import ZmqTransport
    skip = False
except ImportError, e:
    if e.message == 'No module named zmq':
        skip = True
    else:
        raise


@unittest.skipIf(skip, 'zmq not installed')
class ZmqTests(unittest.TestCase):

    def setUp(self):
        empty_conf = tempfile.NamedTemporaryFile(delete=True)
        self.beaver_config = BeaverConfig(mock.Mock(config=empty_conf.name))

    def test_pub(self):
        self.beaver_config.set('zeromq_address', ['tcp://localhost:2120'])
        transport = ZmqTransport(self.beaver_config)
        transport.interrupt()
        #assert not transport.zeromq_bind

    def test_bind(self):
        self.beaver_config.set('zeromq_bind', 'bind')
        self.beaver_config.set('zeromq_address', ['tcp://localhost:2120'])
        ZmqTransport(self.beaver_config)
        #assert transport.zeromq_bind

########NEW FILE########
__FILENAME__ = base_transport
# -*- coding: utf-8 -*-
import datetime

# priority: ujson > simplejson > jsonlib2 > json
priority = ['ujson', 'simplejson', 'jsonlib2', 'json']
for mod in priority:
    try:
        json = __import__(mod)
    except ImportError:
        pass
    else:
        break

try:
    import msgpack
except ImportError:
    import msgpack_pure as msgpack


class BaseTransport(object):

    def __init__(self, beaver_config, logger=None):
        """Generic transport configuration
        Will attach the file_config object, setup the
        current hostname, and ensure we have a proper
        formatter for the current transport
        """
        self._beaver_config = beaver_config
        self._current_host = beaver_config.get('hostname')
        self._default_formatter = beaver_config.get('format', 'null')
        self._formatters = {}
        self._is_valid = True
        self._logger = logger

        self._logstash_version = beaver_config.get('logstash_version')
        if self._logstash_version == 0:
            self._fields = {
                'type': '@type',
                'tags': '@tags',
                'message': '@message',
                'file': '@source_path',
                'host': '@source_host',
                'raw_json_fields': ['@message', '@source', '@source_host', '@source_path', '@tags', '@timestamp', '@type'],
            }
        elif self._logstash_version == 1:
            self._fields = {
                'type': 'type',
                'tags': 'tags',
                'message': 'message',
                'file': 'file',
                'host': 'host',
                'raw_json_fields': ['message', 'host', 'file', 'tags', '@timestamp', 'type'],
            }

        def raw_formatter(data):
            return data[self._fields.get('message')]

        def rawjson_formatter(data):
            try:
                json_data = json.loads(data[self._fields.get('message')])
            except ValueError:
                self._logger.warning("cannot parse as rawjson: {0}".format(self._fields.get('message')))
                json_data = json.loads("{}")

            del data[self._fields.get('message')]

            for field in json_data:
                data[field] = json_data[field]

            for field in self._fields.get('raw_json_fields'):
                if field not in data:
                    data[field] = ''

            return json.dumps(data)

        def string_formatter(data):
            return '[{0}] [{1}] {2}'.format(data[self._fields.get('host')], data['@timestamp'], data[self._fields.get('message')])

        self._formatters['json'] = json.dumps
        self._formatters['msgpack'] = msgpack.packb
        self._formatters['raw'] = raw_formatter
        self._formatters['rawjson'] = rawjson_formatter
        self._formatters['string'] = string_formatter

    def addglob(self, globname, globbed):
        """Adds a set of globbed files to the attached beaver_config"""
        self._beaver_config.addglob(globname, globbed)

    def callback(self, filename, lines):
        """Processes a set of lines for a filename"""
        return True

    def format(self, filename, line, timestamp, **kwargs):
        """Returns a formatted log line"""
        formatter = self._beaver_config.get_field('format', filename)
        if formatter not in self._formatters:
            formatter = self._default_formatter

        data = {
            self._fields.get('type'): kwargs.get('type'),
            self._fields.get('tags'): kwargs.get('tags'),
            '@timestamp': timestamp,
            self._fields.get('host'): self._current_host,
            self._fields.get('file'): filename,
            self._fields.get('message'): line
        }

        if self._logstash_version == 0:
            data['@source'] = 'file://{0}'.format(filename)
            data['@fields'] = kwargs.get('fields')
        else:
            data['@version'] = self._logstash_version
            fields = kwargs.get('fields')
            for key in fields:
                data[key] = fields.get(key)

        return self._formatters[formatter](data)

    def get_timestamp(self, **kwargs):
        """Retrieves the timestamp for a given set of data"""
        timestamp = kwargs.get('timestamp')
        if not timestamp:
            now = datetime.datetime.utcnow()
            timestamp = now.strftime("%Y-%m-%dT%H:%M:%S") + ".%03d" % (now.microsecond / 1000) + "Z"

        return timestamp

    def interrupt(self):
        """Allows keyboard interrupts to be
        handled properly by the transport
        """
        return True

    def invalidate(self):
        """Invalidates the current transport"""
        self._is_valid = False

    def reconnect(self):
        """Allows reconnection from when a handled
        TransportException is thrown"""
        return True

    def unhandled(self):
        """Allows unhandled exceptions to be
        handled properly by the transport
        """
        return True

    def valid(self):
        """Returns whether or not the transport can send data"""
        return self._is_valid

########NEW FILE########
__FILENAME__ = exception
# -*- coding: utf-8 -*-


class TransportException(Exception):
    pass

########NEW FILE########
__FILENAME__ = http_transport
# -*- coding: utf-8 -*-
import traceback
import time
import requests

from beaver.transports.base_transport import BaseTransport
from beaver.transports.exception import TransportException


class HttpTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(HttpTransport, self).__init__(beaver_config, logger=logger)

        self._url = beaver_config.get('http_url')
        self._logger.info('Initializing with url of: {0}'.format(self._url))
        self._is_valid = False

        self._connect()

    def _connect(self):
        wait = -1
        while True:
            wait += 1
            time.sleep(wait)
            if wait == 20:
                return False

            if wait > 0:
                self._logger.info('Retrying connection, attempt {0}'.format(wait + 1))

            try:
                #check for a 200 on the url
                self._logger.info('connect: {0}'.format(self._url))
                r = requests.get(self._url)
            except Exception as e:
                self._logger.error('Exception caught validating url connection: ' + str(e))
            else:
                self._logger.info('Connection validated')
                self._is_valid = True
                return True

    def reconnect(self):
        self._connect()

    def invalidate(self):
        """Invalidates the current transport"""
        super(HttpTransport, self).invalidate()
        return False

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        try:
            for line in lines:
                #escape any tab in the message field, assuming json payload
                jsonline = self.format(filename, line, timestamp, **kwargs)
                edata = jsonline.replace('\t', '\\t')
                self._logger.debug('writing to : {0}'.format(self._url))
                self._logger.debug('writing data: {0}'.format(edata))
                r = requests.post(url=self._url, data=edata)
                if r.status_code == 200:
                    res = r.content
                else:
                    self._logger.error('Post returned non 200 http status: {0}/{1}'.format(r.status_code, r.reason))
        except Exception as e:
            self._logger.error('Exception caught in urlopen connection: ' + str(e))

########NEW FILE########
__FILENAME__ = mqtt_transport
# -*- coding: utf-8 -*-
from mosquitto import Mosquitto

from beaver.transports.base_transport import BaseTransport
from beaver.transports.exception import TransportException


class MqttTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        """
        Mosquitto client initilization. Once this this transport is initialized
        it has invoked a connection to the server
        """
        super(MqttTransport, self).__init__(beaver_config, logger=logger)

        self._client = Mosquitto(beaver_config.get('mqtt_clientid'), clean_session=True)
        self._topic = beaver_config.get('mqtt_topic')
        self._client.connect(
            host=beaver_config.get('mqtt_hostname'),
            port=beaver_config.get('mqtt_port'),
            keepalive=beaver_config.get('mqtt_keepalive')
        )

        def on_disconnect(mosq, obj, rc):
            if rc == 0:
                logger.debug('Mosquitto has successfully disconnected')
            else:
                logger.debug('Mosquitto unexpectedly disconnected')

        self._client.on_disconnect = on_disconnect

    def callback(self, filename, lines, **kwargs):
        """publishes lines one by one to the given topic"""
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        for line in lines:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('error')
                    self._client.publish(self._topic, self.format(filename, line, timestamp, **kwargs), 0)
            except Exception, e:
                try:
                    raise TransportException(e.strerror)
                except AttributeError:
                    raise TransportException('Unspecified exception encountered')

    def interrupt(self):
        if self._client:
            self._client.disconnect()

    def unhandled(self):
        return True

########NEW FILE########
__FILENAME__ = rabbitmq_transport
# -*- coding: utf-8 -*-
import pika
import ssl

from beaver.transports.base_transport import BaseTransport
from beaver.transports.exception import TransportException


class RabbitmqTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(RabbitmqTransport, self).__init__(beaver_config, logger=logger)

        self._rabbitmq_config = {}
        config_to_store = [
            'key', 'exchange', 'username', 'password', 'host', 'port', 'vhost',
            'queue', 'queue_durable', 'ha_queue', 'exchange_type', 'exchange_durable',
            'ssl', 'ssl_key', 'ssl_cert', 'ssl_cacert'
        ]

        for key in config_to_store:
            self._rabbitmq_config[key] = beaver_config.get('rabbitmq_' + key)

        self._connection = None
        self._channel = None
        self._connect()

    def _connect(self):

        # Setup RabbitMQ connection
        credentials = pika.PlainCredentials(
            self._rabbitmq_config['username'],
            self._rabbitmq_config['password']
        )
        ssl_options = {
            'keyfile': self._rabbitmq_config['ssl_key'],
            'certfile': self._rabbitmq_config['ssl_cert'],
            'ca_certs': self._rabbitmq_config['ssl_cacert'],
            'ssl_version': ssl.PROTOCOL_TLSv1
        }
        parameters = pika.connection.ConnectionParameters(
            credentials=credentials,
            host=self._rabbitmq_config['host'],
            port=self._rabbitmq_config['port'],
            ssl=self._rabbitmq_config['ssl'],
            ssl_options=ssl_options,
            virtual_host=self._rabbitmq_config['vhost']
        )
        self._connection = pika.adapters.BlockingConnection(parameters)
        self._channel = self._connection.channel()

        # Declare RabbitMQ queue and bindings
        self._channel.queue_declare(
            queue=self._rabbitmq_config['queue'],
            durable=self._rabbitmq_config['queue_durable'],
            arguments={'x-ha-policy': 'all'} if self._rabbitmq_config['ha_queue'] else {}
        )
        self._channel.exchange_declare(
            exchange=self._rabbitmq_config['exchange'],
            exchange_type=self._rabbitmq_config['exchange_type'],
            durable=self._rabbitmq_config['exchange_durable']
        )
        self._channel.queue_bind(
            exchange=self._rabbitmq_config['exchange'],
            queue=self._rabbitmq_config['queue'],
            routing_key=self._rabbitmq_config['key']
        )

        self._is_valid = True;

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        for line in lines:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('error')
                    self._channel.basic_publish(
                        exchange=self._rabbitmq_config['exchange'],
                        routing_key=self._rabbitmq_config['key'],
                        body=self.format(filename, line, timestamp, **kwargs),
                        properties=pika.BasicProperties(
                            content_type='text/json',
                            delivery_mode=1
                        )
                    )
            except UserWarning:
                self._is_valid = False
                raise TransportException('Connection appears to have been lost')
            except Exception, e:
                self._is_valid = False
                try:
                    raise TransportException(e.strerror)
                except AttributeError:
                    raise TransportException('Unspecified exception encountered')  # TRAP ALL THE THINGS!

    def interrupt(self):
        if self._connection:
            self._connection.close()

    def reconnect(self):
        self._connect()

    def unhandled(self):
        return True

########NEW FILE########
__FILENAME__ = redis_transport
# -*- coding: utf-8 -*-
import redis
import traceback
import time
import urlparse

from beaver.transports.base_transport import BaseTransport
from beaver.transports.exception import TransportException


class RedisTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(RedisTransport, self).__init__(beaver_config, logger=logger)

        redis_url = beaver_config.get('redis_url')
        redis_password = beaver_config.get('redis_password')
        self._redis = redis.StrictRedis.from_url(redis_url, socket_timeout=10)
        self._redis_namespace = beaver_config.get('redis_namespace')
        self._is_valid = False

        self._connect()

    def _connect(self):
        wait = -1
        while True:
            wait += 1
            time.sleep(wait)
            if wait == 20:
                return False

            if wait > 0:
                self._logger.info("Retrying connection, attempt {0}".format(wait + 1))

            try:
                self._redis.ping()
                break
            except UserWarning:
                traceback.print_exc()
            except Exception:
                traceback.print_exc()

        self._is_valid = True
        self._pipeline = self._redis.pipeline(transaction=False)

    def reconnect(self):
        self._connect()

    def invalidate(self):
        """Invalidates the current transport"""
        super(RedisTransport, self).invalidate()
        self._redis.connection_pool.disconnect()
        return False

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        for line in lines:
            self._pipeline.rpush(
                self._redis_namespace,
                self.format(filename, line, timestamp, **kwargs)
            )

        try:
            self._pipeline.execute()
        except redis.exceptions.RedisError, e:
            traceback.print_exc()
            raise TransportException(str(e))

########NEW FILE########
__FILENAME__ = sqs_transport
# -*- coding: utf-8 -*-
import boto.sqs
import uuid

from beaver.transports.base_transport import BaseTransport
from beaver.transports.exception import TransportException


class SqsTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(SqsTransport, self).__init__(beaver_config, logger=logger)

        self._access_key = beaver_config.get('sqs_aws_access_key')
        self._secret_key = beaver_config.get('sqs_aws_secret_key')
        self._region = beaver_config.get('sqs_aws_region')
        self._queue_name = beaver_config.get('sqs_aws_queue')

        try:
            if self._access_key is None and self._secret_key is None:
                self._connection = boto.sqs.connect_to_region(self._region)
            else:
                self._connection = boto.sqs.connect_to_region(self._region,
                                                              aws_access_key_id=self._access_key,
                                                              aws_secret_access_key=self._secret_key)

            if self._connection is None:
                self._logger.warn('Unable to connect to AWS - check your AWS credentials')
                raise TransportException('Unable to connect to AWS - check your AWS credentials')

            self._queue = self._connection.get_queue(self._queue_name)

            if self._queue is None:
                raise TransportException('Unable to access queue with name {0}'.format(self._queue_name))
        except Exception, e:
            raise TransportException(e.message)

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        message_batch = []
        for line in lines:
            message_batch.append((uuid.uuid4(), self.format(filename, line, timestamp, **kwargs), 0))
            if len(message_batch) == 10:  # SQS can only handle up to 10 messages in batch send
                self._logger.debug('Flushing 10 messages to SQS queue')
                self._send_message_batch(message_batch)
                message_batch = []

        if len(message_batch) > 0:
            self._logger.debug('Flushing last {0} messages to SQS queue'.format(len(message_batch)))
            self._send_message_batch(message_batch)
        return True

    def _send_message_batch(self, message_batch):
        try:
            result = self._queue.write_batch(message_batch)
            if not result:
                self._logger.error('Error occurred sending messages to SQS queue {0}. result: {1}'.format(
                    self._queue_name, result))
                raise TransportException('Error occurred sending message to queue {0}'.format(self._queue_name))
        except Exception, e:
            self._logger.exception('Exception occurred sending batch to SQS queue')
            raise TransportException(e.message)

    def interrupt(self):
        return True

    def unhandled(self):
        return True

########NEW FILE########
__FILENAME__ = stdout_transport
# -*- coding: utf-8 -*-
from beaver.transports.base_transport import BaseTransport
from beaver.utils import setup_custom_logger


class StdoutTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(StdoutTransport, self).__init__(beaver_config, logger=logger)
        self._stdout = setup_custom_logger('stdout', formatter=False, output=beaver_config.get('output'))

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        for line in lines:
            self._stdout.info(self.format(filename, line, timestamp, **kwargs))

########NEW FILE########
__FILENAME__ = tcp_transport
# -*- coding: utf-8 -*-
import socket
import errno
import ssl
import time

from beaver.transports.base_transport import BaseTransport
from beaver.transports.exception import TransportException


class TcpTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(TcpTransport, self).__init__(beaver_config, logger=logger)

        self._is_valid = False
        self._tcp_host = beaver_config.get('tcp_host')
        self._tcp_port = beaver_config.get('tcp_port')
        self._tcp_ssl_enabled = beaver_config.get('tcp_ssl_enabled')
        self._tcp_ssl_verify = beaver_config.get('tcp_ssl_verify')
        self._tcp_ssl_cacert = beaver_config.get('tcp_ssl_cacert')
        self._tcp_ssl_cert = beaver_config.get('tcp_ssl_cert')

        self._connect()

    def _connect(self):
        wait = -1
        self._logger.debug("SSL enabled for TCP transport? %s" % self._tcp_ssl_enabled)
        while True:
            wait += 1
            time.sleep(wait)

            if wait == 20:
                return False

            if wait > 0:
                self._logger.info("Retrying connection, attempt {0}".format(wait + 1))

            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP
                self._sock.connect((self._tcp_host, int(self._tcp_port)))
                if self._tcp_ssl_enabled:
                    self._logger.debug("SSL wrapping")
                    self._sock = ssl.wrap_socket(self._sock,
                                                 certfile=self._tcp_ssl_cert,
                                                 ssl_version=ssl.PROTOCOL_TLSv1,
                                                 ca_certs=self._tcp_ssl_cacert)

            except Exception as e:
                self._logger.error("Exception caught in socket connection: " + str(e))
            else:
                self._logger.info("Connected")
                self._is_valid = True
                return True

    def reconnect(self):
        self._connect()

    def invalidate(self):
        """Invalidates the current transport"""
        super(TcpTransport, self).invalidate()
        self._sock.close()

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        try:
            for line in lines:
                self._sock.send(self.format(filename, line, timestamp, **kwargs) + "\n")
        except socket.error, e:
            self.invalidate()

            if isinstance(e.args, tuple):
                if e[0] == errno.EPIPE:
                    raise TransportException('Connection appears to have been lost')

            raise TransportException('Socket Error: %s', e.args)
        except Exception:
            self.invalidate()

            raise TransportException('Unspecified exception encountered')  # TRAP ALL THE THINGS!

########NEW FILE########
__FILENAME__ = udp_transport
# -*- coding: utf-8 -*-
import socket

from beaver.transports.base_transport import BaseTransport


class UdpTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(UdpTransport, self).__init__(beaver_config, logger=logger)

        self._sock = socket.socket(socket.AF_INET,  # Internet
                                   socket.SOCK_DGRAM)  # UDP
        self._address = (beaver_config.get('udp_host'), beaver_config.get('udp_port'))

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        for line in lines:
            self._sock.sendto(self.format(filename, line, timestamp, **kwargs), self._address)

########NEW FILE########
__FILENAME__ = zmq_transport
# -*- coding: utf-8 -*-
import zmq

from beaver.transports.base_transport import BaseTransport


class ZmqTransport(BaseTransport):

    def __init__(self, beaver_config, logger=None):
        super(ZmqTransport, self).__init__(beaver_config, logger=logger)

        zeromq_addresses = beaver_config.get('zeromq_address')

        self._ctx = zmq.Context()
        if beaver_config.get('zeromq_pattern') == 'pub':
            self._pub = self._ctx.socket(zmq.PUB)
        else:
            self._pub = self._ctx.socket(zmq.PUSH)

        zeromq_hwm = beaver_config.get('zeromq_hwm')
        if zeromq_hwm:
            if hasattr(self._pub, 'HWM'): # ZeroMQ < 3
                self._pub.setsockopt(zmq.HWM, zeromq_hwm)
            else:
                self._pub.setsockopt(zmq.SNDHWM, zeromq_hwm)
                self._pub.setsockopt(zmq.RCVHWM, zeromq_hwm)

        if beaver_config.get('mode') == 'bind':
            for addr in zeromq_addresses:
                self._pub.bind(addr)
        else:
            for addr in zeromq_addresses:
                self._pub.connect(addr)

    def callback(self, filename, lines, **kwargs):
        timestamp = self.get_timestamp(**kwargs)
        if kwargs.get('timestamp', False):
            del kwargs['timestamp']

        for line in lines:
            self._pub.send(self.format(filename, line, timestamp, **kwargs))

    def interrupt(self):
        self._pub.close()
        self._ctx.term()

    def unhandled(self):
        return True

########NEW FILE########
__FILENAME__ = unicode_dammit
# -*- coding: utf-8 -*-
import os
import codecs

CHARSET_ALIASES = {'macintosh': 'mac-roman', 'x-sjis': 'shift-jis'}
ENCODINGS = [
    'windows-1252',
    'iso-8859-1',
    'iso-8859-2',
]


def unicode_dammit(string, logger=None):
    for encoding in ENCODINGS:
        try:
            string = string.strip(os.linesep)
        except UnicodeDecodeError:
            u = _convert_from(string, encoding)
            if u:
                string = u
                break

    return string


def _convert_from(markup, proposed, errors='strict'):
    proposed = _find_codec(proposed)

    try:
        u = _to_unicode(markup, proposed, errors)
        markup = u
    except Exception:
        return None

    return markup


def _to_unicode(self, data, encoding, errors='strict'):
    '''Given a string and its encoding, decodes the string into Unicode.
    %encoding is a string recognized by encodings.aliases'''

    # strip Byte Order Mark (if present)
    if (len(data) >= 4) and (data[:2] == '\xfe\xff') and (data[2:4] != '\x00\x00'):
        encoding = 'utf-16be'
        data = data[2:]
    elif (len(data) >= 4) and (data[:2] == '\xff\xfe') and (data[2:4] != '\x00\x00'):
        encoding = 'utf-16le'
        data = data[2:]
    elif data[:3] == '\xef\xbb\xbf':
        encoding = 'utf-8'
        data = data[3:]
    elif data[:4] == '\x00\x00\xfe\xff':
        encoding = 'utf-32be'
        data = data[4:]
    elif data[:4] == '\xff\xfe\x00\x00':
        encoding = 'utf-32le'
        data = data[4:]
    newdata = unicode(data, encoding, errors)
    return newdata


def _find_codec(self, charset):
    return _codec(CHARSET_ALIASES.get(charset, charset)) \
        or (charset and self._codec(charset.replace('-', ''))) \
        or (charset and self._codec(charset.replace('-', '_'))) \
        or charset


def _codec(self, charset):
    if not charset:
        return charset
    codec = None
    try:
        codecs.lookup(charset)
        codec = charset
    except (LookupError, ValueError):
        pass
    return codec

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import argparse
import glob2
import itertools
import logging
import platform
import re
import os
import sys

import beaver

logging.basicConfig()

MAGIC_BRACKETS = re.compile('({([^}]+)})')
IS_GZIPPED_FILE = re.compile('.gz$')
REOPEN_FILES = 'linux' not in platform.platform().lower()
CAN_DAEMONIZE = sys.platform != 'win32'

cached_regices = {}


def parse_args():
    epilog_example = """
    Beaver provides an lightweight method for shipping local log
    files to Logstash. It does this using either redis, stdin,
    zeromq as the transport. This means you'll need a redis,
    stdin, zeromq input somewhere down the road to get the events.

    Events are sent in logstash's json_event format. Options can
    also be set as environment variables.

    Please see the readme for complete examples.
    """
    parser = argparse.ArgumentParser(description='Beaver logfile shipper', epilog=epilog_example, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--configfile', help='ini config file path', dest='config', default='/dev/null')
    parser.add_argument('-C', '--confd-path', help='path to conf.d directory', dest='confd_path', default='/etc/beaver/conf.d')
    parser.add_argument('-d', '--debug', help='enable debug mode', dest='debug', default=False, action='store_true')
    parser.add_argument('-D', '--daemonize', help='daemonize in the background', dest='daemonize', default=False, action='store_true')
    parser.add_argument('-f', '--files', help='space-separated filelist to watch, can include globs (*.log). Overrides --path argument', dest='files', default=None, nargs='+')
    parser.add_argument('-F', '--format', help='format to use when sending to transport', default=None, dest='format', choices=['json', 'msgpack', 'raw', 'rawjson', 'string'])
    parser.add_argument('-H', '--hostname', help='manual hostname override for source_host', default=None, dest='hostname')
    parser.add_argument('-m', '--mode', help='bind or connect mode', dest='mode', default=None, choices=['bind', 'connect'])
    parser.add_argument('-l', '--logfile', '-o', '--output', help='file to pipe output to (in addition to stdout)', default=None, dest='output')
    parser.add_argument('-p', '--path', help='path to log files', default=None, dest='path')
    parser.add_argument('-P', '--pid', help='path to pid file', default=None, dest='pid')
    parser.add_argument('-t', '--transport', help='log transport method', dest='transport', default=None, choices=['mqtt', 'rabbitmq', 'redis', 'sqs', 'stdout', 'tcp', 'udp', 'zmq', 'http'])
    parser.add_argument('-e', '--experimental', help='use experimental version of beaver', dest='experimental', default=False, action='store_true')
    parser.add_argument('-v', '--version', help='output version and quit', dest='version', default=False, action='store_true')
    parser.add_argument('--fqdn', help='use the machine\'s FQDN for source_host', dest='fqdn', default=False, action='store_true')

    return parser.parse_args()


def setup_custom_logger(name, args=None, output=None, formatter=None, debug=None):
    logger = logging.getLogger(name)
    logger.propagate = False
    if logger.handlers:
        logger.handlers = []

    has_args = args is not None and type(args) == argparse.Namespace
    if debug is None:
        debug = has_args and args.debug is True

    if not logger.handlers:
        if formatter is None:
            formatter = logging.Formatter('[%(asctime)s] %(levelname)-7s %(message)s')

        handler = logging.StreamHandler()
        if output is None and has_args:
            output = args.output

        if output:
            output = os.path.realpath(output)

        if output is not None:
            file_handler = logging.FileHandler(output)
            if formatter is not False:
                file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if formatter is not False:
            handler.setFormatter(formatter)

        logger.addHandler(handler)

    if debug:
        logger.setLevel(logging.DEBUG)
        if hasattr(logging, 'captureWarnings'):
            logging.captureWarnings(True)
    else:
        logger.setLevel(logging.INFO)
        if hasattr(logging, 'captureWarnings'):
            logging.captureWarnings(False)

    logger.debug('Logger level is {0}'.format(logging.getLevelName(logger.level)))

    return logger


def version(args):
    if args.version:
        formatter = logging.Formatter('%(message)s')
        logger = setup_custom_logger('beaver', args=args, formatter=formatter)
        logger.info('Beaver {0}'.format(beaver.__version__))
        sys.exit(0)


def eglob(path, exclude=None):
    """Like glob.glob, but supports "/path/**/{a,b,c}.txt" lookup"""
    fi = itertools.chain.from_iterable
    paths = list(fi(glob2.iglob(d) for d in expand_paths(path)))
    if exclude:
        cached_regex = cached_regices.get(exclude, None)
        if not cached_regex:
            cached_regex = cached_regices[exclude] = re.compile(exclude)
        paths = [x for x in paths if not cached_regex.search(x)]

    return paths


def expand_paths(path):
    """When given a path with brackets, expands it to return all permutations
       of the path with expanded brackets, similar to ant.

       >>> expand_paths('../{a,b}/{c,d}')
       ['../a/c', '../a/d', '../b/c', '../b/d']
       >>> expand_paths('../{a,b}/{a,b}.py')
       ['../a/a.py', '../a/b.py', '../b/a.py', '../b/b.py']
       >>> expand_paths('../{a,b,c}/{a,b,c}')
       ['../a/a', '../a/b', '../a/c', '../b/a', '../b/b', '../b/c', '../c/a', '../c/b', '../c/c']
       >>> expand_paths('test')
       ['test']
       >>> expand_paths('')
    """
    pr = itertools.product
    parts = MAGIC_BRACKETS.findall(path)

    if not path:
        return

    if not parts:
        return [path]

    permutations = [[(p[0], i, 1) for i in p[1].split(',')] for p in parts]
    return [_replace_all(path, i) for i in pr(*permutations)]


def _replace_all(path, replacements):
    for j in replacements:
        path = path.replace(*j)
    return path


def multiline_merge(lines, current_event, re_after, re_before):
    """ Merge multi-line events based.

        Some event (like Python trackback or Java stracktrace) spawn
        on multiple line. This method will merge them using two
        regular expression: regex_after and regex_before.

        If a line match re_after, it will be merged with next line.

        If a line match re_before, it will be merged with previous line.

        This function return a list of complet event. Note that because
        we don't know if an event is complet before another new event
        start, the last event will not be returned but stored in
        current_event. You should pass the same current_event to
        successive call to multiline_merge. current_event is a list
        of lines whose belong to the same event.
    """
    events = []
    for line in lines:
        if re_before and re_before.match(line):
            current_event.append(line)
        elif re_after and current_event and re_after.match(current_event[-1]):
            current_event.append(line)
        else:
            if current_event:
                events.append('\n'.join(current_event))
            current_event.clear()
            current_event.append(line)

    return events

########NEW FILE########
__FILENAME__ = tail
# -*- coding: utf-8 -*-
import collections
import datetime
import errno
import gzip
import io
import os
import sqlite3
import time

from beaver.utils import IS_GZIPPED_FILE, REOPEN_FILES, multiline_merge
from beaver.unicode_dammit import ENCODINGS
from beaver.base_log import BaseLog


class Tail(BaseLog):
    """Follows a single file and outputs new lines from it to a callback
    """

    def __init__(self, filename, callback, position="end", logger=None, beaver_config=None, file_config=None):
        super(Tail, self).__init__(logger=logger)

        self.active = False
        self._callback = callback
        self._fid = None
        self._file = None
        self._filename = filename
        self._last_sincedb_write = None
        self._last_file_mapping_update = None
        self._line_count = 0
        self._log_template = '[' + self._filename + '] - {0}'

        self._sincedb_path = beaver_config.get('sincedb_path')

        self._debug = beaver_config.get_field('debug', filename)  # TODO: Implement me
        self._encoding = beaver_config.get_field('encoding', filename)
        self._fields = beaver_config.get_field('fields', filename)
        self._format = beaver_config.get_field('format', filename)
        self._ignore_empty = beaver_config.get_field('ignore_empty', filename)
        self._ignore_truncate = beaver_config.get_field('ignore_truncate', filename)
        self._message_format = beaver_config.get_field('message_format', filename)  # TODO: Implement me
        self._sincedb_write_interval = beaver_config.get_field('sincedb_write_interval', filename)
        self._start_position = beaver_config.get_field('start_position', filename)
        self._stat_interval = beaver_config.get_field('stat_interval', filename)
        self._tail_lines = beaver_config.get_field('tail_lines', filename)
        self._tags = beaver_config.get_field('tags', filename)
        self._type = beaver_config.get_field('type', filename)

        # The following is for the buffered tokenization
        # Store the specified delimiter
        self._delimiter = beaver_config.get_field("delimiter", filename)
        # Store the specified size limitation
        self._size_limit = beaver_config.get_field("size_limit", filename)
        # The input buffer is stored as an array.  This is by far the most efficient
        # approach given language constraints (in C a linked list would be a more
        # appropriate data structure).  Segments of input data are stored in a list
        # which is only joined when a token is reached, substantially reducing the
        # number of objects required for the operation.
        self._input = collections.deque([])

        # Size of the input buffer
        self._input_size = 0

        # Attribute for multi-line events
        self._current_event = collections.deque([])
        self._last_activity = time.time()
        self._multiline_regex_after = beaver_config.get_field('multiline_regex_after', filename)
        self._multiline_regex_before = beaver_config.get_field('multiline_regex_before', filename)

        self._update_file()
        if self.active:
            self._log_info("watching logfile")

    def __del__(self):
        """Closes all files"""
        self.close()

    def open(self, encoding=None):
        """Opens the file with the appropriate call"""
        try:
            if IS_GZIPPED_FILE.search(self._filename):
                _file = gzip.open(self._filename, 'rb')
            else:
                if encoding:
                    _file = io.open(self._filename, 'r', encoding=encoding, errors='replace')
                elif self._encoding:
                    _file = io.open(self._filename, 'r', encoding=self._encoding, errors='replace')
                else:
                    _file = io.open(self._filename, 'r', errors='replace')
        except IOError, e:
            self._log_warning(str(e))
            _file = None
            self.close()

        return _file

    def close(self):
        """Closes all currently open file pointers"""
        if not self.active:
            return

        self.active = False
        if self._file:
            self._file.close()

        if self._current_event:
            event = '\n'.join(self._current_event)
            self._current_event.clear()
            self._callback_wrapper([event])

    def run(self, once=False):
        while self.active:
            current_time = time.time()
            self._run_pass()

            self._ensure_file_is_good(current_time=current_time)

            self._log_debug('Iteration took {0:.6f}'.format(time.time() - current_time))
            if once:
                break

        if not once:
            self._log_debug('file closed')

    def fid(self):
        return self._fid

    def _buffer_extract(self, data):
        """
        Extract takes an arbitrary string of input data and returns an array of
        tokenized entities, provided there were any available to extract.  This
        makes for easy processing of datagrams using a pattern like:

          tokenizer.extract(data).map { |entity| Decode(entity) }.each do ..."""
        # Extract token-delimited entities from the input string with the split command.
        # There's a bit of craftiness here with the -1 parameter.  Normally split would
        # behave no differently regardless of if the token lies at the very end of the
        # input buffer or not (i.e. a literal edge case)  Specifying -1 forces split to
        # return "" in this case, meaning that the last entry in the list represents a
        # new segment of data where the token has not been encountered
        entities = collections.deque(data.split(self._delimiter, -1))

        # Check to see if the buffer has exceeded capacity, if we're imposing a limit
        if self._size_limit:
            if self.input_size + len(entities[0]) > self._size_limit:
                raise Exception('input buffer full')
            self._input_size += len(entities[0])

        # Move the first entry in the resulting array into the input buffer.  It represents
        # the last segment of a token-delimited entity unless it's the only entry in the list.
        first_entry = entities.popleft()
        if len(first_entry) > 0:
            self._input.append(first_entry)

        # If the resulting array from the split is empty, the token was not encountered
        # (not even at the end of the buffer).  Since we've encountered no token-delimited
        # entities this go-around, return an empty array.
        if len(entities) == 0:
            return []

        # At this point, we've hit a token, or potentially multiple tokens.  Now we can bring
        # together all the data we've buffered from earlier calls without hitting a token,
        # and add it to our list of discovered entities.
        entities.appendleft(''.join(self._input))

        # Now that we've hit a token, joined the input buffer and added it to the entities
        # list, we can go ahead and clear the input buffer.  All of the segments that were
        # stored before the join can now be garbage collected.
        self._input.clear()

        # The last entity in the list is not token delimited, however, thanks to the -1
        # passed to split.  It represents the beginning of a new list of as-yet-untokenized
        # data, so we add it to the start of the list.
        self._input.append(entities.pop())

        # Set the new input buffer size, provided we're keeping track
        if self._size_limit:
            self._input_size = len(self._input[0])

        # Now we're left with the list of extracted token-delimited entities we wanted
        # in the first place.  Hooray!
        return entities

    # Flush the contents of the input buffer, i.e. return the input buffer even though
    # a token has not yet been encountered
    def _buffer_flush(self):
        buf = ''.join(self._input)
        self._input.clear
        return buf

    # Is the buffer empty?
    def _buffer_empty(self):
        return len(self._input) > 0

    def _ensure_file_is_good(self, current_time):
        """Every N seconds, ensures that the file we are tailing is the file we expect to be tailing"""
        if self._last_file_mapping_update and current_time - self._last_file_mapping_update <= self._stat_interval:
            return

        self._last_file_mapping_update = time.time()

        try:
            st = os.stat(self._filename)
        except EnvironmentError, err:
            if err.errno == errno.ENOENT:
                self._log_info('file removed')
                self.close()

        fid = self.get_file_id(st)
        if fid != self._fid:
            self._log_info('file rotated')
            self.close()
        elif self._file.tell() > st.st_size:
            if st.st_size == 0 and self._ignore_truncate:
                self._logger.info("[{0}] - file size is 0 {1}. ".format(fid, self._filename) +
                                  "If you use another tool (i.e. logrotate) to truncate " +
                                  "the file, your application may continue to write to " +
                                  "the offset it last wrote later. In such a case, we'd " +
                                  "better do nothing here")
                return
            self._log_info('file truncated')
            self._update_file(seek_to_end=False)
        elif REOPEN_FILES:
            self._log_debug('file reloaded (non-linux)')
            position = self._file.tell()
            self._update_file(seek_to_end=False)
            if self.active:
                self._file.seek(position, os.SEEK_SET)

    def _run_pass(self):
        """Read lines from a file and performs a callback against them"""
        line_count = 0
        while True:
            try:
                data = self._file.read(4096)
            except IOError, e:
                if e.errno == errno.ESTALE:
                    self.active = False
                    return False

            lines = self._buffer_extract(data)

            if not lines:
                # Before returning, check if an event (maybe partial) is waiting for too long.
                if self._current_event and time.time() - self._last_activity > 1:
                    event = '\n'.join(self._current_event)
                    self._current_event.clear()
                    self._callback_wrapper([event])
                break

            self._last_activity = time.time()

            if self._multiline_regex_after or self._multiline_regex_before:
                # Multiline is enabled for this file.
                events = multiline_merge(
                        lines,
                        self._current_event,
                        self._multiline_regex_after,
                        self._multiline_regex_before)
            else:
                events = lines

            if events:
                self._callback_wrapper(events)

            if self._sincedb_path:
                current_line_count = len(lines)
                if not self._sincedb_update_position(lines=current_line_count):
                    line_count += current_line_count

        if line_count > 0:
            self._sincedb_update_position(lines=line_count, force_update=True)

    def _callback_wrapper(self, lines):
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S") + ".%03d" % (now.microsecond / 1000) + "Z"
        self._callback(('callback', {
            'fields': self._fields,
            'filename': self._filename,
            'format': self._format,
            'ignore_empty': self._ignore_empty,
            'lines': lines,
            'timestamp': timestamp,
            'tags': self._tags,
            'type': self._type,
        }))

    def _seek_to_end(self):
        self._log_debug('seek_to_end')

        if self._sincedb_path:
            sincedb_start_position = self._sincedb_start_position()
            if sincedb_start_position:
                self._start_position = sincedb_start_position

        if self._start_position == 'beginning':
            self._log_debug('no start_position specified')
            return

        line_count = 0

        if str(self._start_position).isdigit():
            self._log_debug('going to start position {0}'.format(self._start_position))
            self._start_position = int(self._start_position)
            for encoding in ENCODINGS:
                line_count, encoded = self._seek_to_position(encoding=encoding, position=True)
                if line_count is None and encoded is None:
                    return

                if encoded:
                    break

        if self._start_position == 'beginning':
            self._log_debug('Bad start position specified')
            return

        if self._start_position == 'end':
            self._log_debug('getting end position')
            for encoding in ENCODINGS:
                line_count, encoded = self._seek_to_position(encoding=encoding)
                if line_count is None and encoded is None:
                    return

                if encoded:
                    break

        current_position = self._file.tell()
        self._log_debug('line count {0}'.format(line_count))
        self._log_debug('current position {0}'.format(current_position))
        self._sincedb_update_position(lines=line_count, force_update=True)

        if self._tail_lines:
            self._log_debug('tailing {0} lines'.format(self._tail_lines))
            lines = self.tail(self._filename, encoding=self._encoding, window=self._tail_lines, position=current_position)
            if lines:
                if self._multiline_regex_after or self._multiline_regex_before:
                    # Multiline is enabled for this file.
                    events = multiline_merge(
                            lines,
                            self._current_event,
                            self._multiline_regex_after,
                            self._multiline_regex_before)
                else:
                    events = lines
                self._callback_wrapper(events)

        return

    def _seek_to_position(self, encoding=None, position=None):
        line_count = 0
        encoded = False
        try:
            while self._file.readline():
                line_count += 1
                if position and line_count == self._start_position:
                    encoded = True
                    break

            if not position:
                encoded = True
        except UnicodeDecodeError:
            self._log_debug('UnicodeDecodeError raised with encoding {0}'.format(self._encoding))
            self._file = self.open(encoding=encoding)
            self._encoding = encoding

        if not self._file:
            return None, None

        if position and line_count != self._start_position:
            self._log_debug('file at different position than {0}, assuming manual truncate'.format(self._start_position))
            self._file.seek(0, os.SEEK_SET)
            self._start_position == 'beginning'

        return line_count, encoded

    def _sincedb_init(self):
        """Initializes the sincedb schema in an sqlite db"""
        if not self._sincedb_path:
            return

        if not os.path.exists(self._sincedb_path):
            self._log_debug('initializing sincedb sqlite schema')
            conn = sqlite3.connect(self._sincedb_path, isolation_level=None)
            conn.execute("""
            create table sincedb (
                fid      text primary key,
                filename text,
                position integer default 1
            );
            """)
            conn.close()

    def _sincedb_update_position(self, lines=0, force_update=False):
        """Retrieves the starting position from the sincedb sql db for a given file
        Returns a boolean representing whether or not it updated the record
        """
        if not self._sincedb_path:
            return False

        current_time = int(time.time())
        if not force_update:
            if self._last_sincedb_write and current_time - self._last_sincedb_write <= self._sincedb_write_interval:
                return False

            if lines == 0:
                return False

        self._sincedb_init()

        old_count = self._line_count
        self._last_sincedb_write = current_time
        self._line_count = old_count + lines
        lines = self._line_count

        self._log_debug('updating sincedb to {0}'.format(lines))

        conn = sqlite3.connect(self._sincedb_path, isolation_level=None)
        cursor = conn.cursor()
        query = 'insert or ignore into sincedb (fid, filename) values (:fid, :filename);'
        cursor.execute(query, {
            'fid': self._fid,
            'filename': self._filename
        })

        query = 'update sincedb set position = :position where fid = :fid and filename = :filename'
        cursor.execute(query, {
            'fid': self._fid,
            'filename': self._filename,
            'position': lines,
        })
        conn.close()

        return True

    def _sincedb_start_position(self):
        """Retrieves the starting position from the sincedb sql db
        for a given file
        """
        if not self._sincedb_path:
            return None

        self._sincedb_init()
        self._log_debug('retrieving start_position from sincedb')
        conn = sqlite3.connect(self._sincedb_path, isolation_level=None)
        cursor = conn.cursor()
        cursor.execute('select position from sincedb where fid = :fid and filename = :filename', {
            'fid': self._fid,
            'filename': self._filename
        })

        start_position = None
        for row in cursor.fetchall():
            start_position, = row

        return start_position

    def _update_file(self, seek_to_end=True):
        """Open the file for tailing"""
        try:
            self.close()
            self._file = self.open()
        except IOError:
            pass
        else:
            if not self._file:
                return

            self.active = True
            try:
                st = os.stat(self._filename)
            except EnvironmentError, err:
                if err.errno == errno.ENOENT:
                    self._log_info('file removed')
                    self.close()

            fid = self.get_file_id(st)
            if not self._fid:
                self._fid = fid

            if fid != self._fid:
                self._log_info('file rotated')
                self.close()
            elif seek_to_end:
                self._seek_to_end()

    def tail(self, fname, encoding, window, position=None):
        """Read last N lines from file fname."""
        if window <= 0:
            raise ValueError('invalid window %r' % window)

        encodings = ENCODINGS
        if encoding:
            encodings = [encoding] + ENCODINGS

        for enc in encodings:
            try:
                f = self.open(encoding=enc)
                if f:
                    return self.tail_read(f, window, position=position)

                return False
            except IOError, err:
                if err.errno == errno.ENOENT:
                    return []
                raise
            except UnicodeDecodeError:
                pass

    @staticmethod
    def get_file_id(st):
        return "%xg%x" % (st.st_dev, st.st_ino)

    @classmethod
    def tail_read(cls, f, window, position=None):
        BUFSIZ = 1024
        # open() was overridden and file was opened in text
        # mode; read() will return a string instead bytes.
        encoded = getattr(f, 'encoding', False)
        CR = '\n' if encoded else b'\n'
        data = '' if encoded else b''
        f.seek(0, os.SEEK_END)
        if position is None:
            position = f.tell()

        block = -1
        exit = False
        read = BUFSIZ

        while not exit:
            step = (block * BUFSIZ) + position
            if step < 0:
                step = 0
                read = ((block + 1) * BUFSIZ) + position
                exit = True

            f.seek(step, os.SEEK_SET)
            newdata = f.read(read)

            data = newdata + data
            if data.count(CR) > window:
                break
            else:
                block -= 1

        return data.splitlines()[-window:]

########NEW FILE########
__FILENAME__ = tail_manager
# -*- coding: utf-8 -*-
import errno
import os
import stat
import time
import signal
import threading

from beaver.utils import eglob
from beaver.base_log import BaseLog
from beaver.worker.tail import Tail


class TailManager(BaseLog):

    def __init__(self, beaver_config, queue_consumer_function, callback, logger=None):
        super(TailManager, self).__init__(logger=logger)
        self._active = False
        self._beaver_config = beaver_config
        self._folder = self._beaver_config.get('path')
        self._callback = callback
        self._create_queue_consumer = queue_consumer_function
        self._discover_interval = beaver_config.get('discover_interval', 15)
        self._log_template = "[TailManager] - {0}"
        self._proc = None
        self._tails = {}
        self._update_time = None

        self._active = True

        signal.signal(signal.SIGTERM, self.close)

    def listdir(self):
        """HACK around not having a beaver_config stanza
        TODO: Convert this to a glob"""
        ls = os.listdir(self._folder)
        return [x for x in ls if os.path.splitext(x)[1][1:] == "log"]

    def watch(self, paths=[]):
        for path in paths:
            if not self._active:
                break

            tail = Tail(
                filename=path,
                beaver_config=self._beaver_config,
                callback=self._callback,
                logger=self._logger
            )

            if tail.active:
                self._tails[tail.fid()] = tail

    def create_queue_consumer_if_required(self, interval=5.0):
        if not (self._proc and self._proc.is_alive()):
            self._proc = self._create_queue_consumer()
        timer = threading.Timer(interval, self.create_queue_consumer_if_required)
        timer.start()

    def run(self, interval=0.1,):

        self.create_queue_consumer_if_required()

        while self._active:
            for fid in self._tails.keys():

                self.update_files()

                self._log_debug("Processing {0}".format(fid))
                if not self._active:
                    break

                self._tails[fid].run(once=True)

                if not self._tails[fid].active:
                    self._tails[fid].close()
                    del self._tails[fid]

            self.update_files()
            time.sleep(interval)

    def update_files(self):
        """Ensures all files are properly loaded.
        Detects new files, file removals, file rotation, and truncation.
        On non-linux platforms, it will also manually reload the file for tailing.
        Note that this hack is necessary because EOF is cached on BSD systems.
        """
        if self._update_time and int(time.time()) - self._update_time < self._discover_interval:
            return

        self._update_time = int(time.time())

        possible_files = []
        files = []
        if len(self._beaver_config.get('globs')) > 0:
            extend_files = files.extend
            for name, exclude in self._beaver_config.get('globs').items():
                globbed = [os.path.realpath(filename) for filename in eglob(name, exclude)]
                extend_files(globbed)
                self._beaver_config.addglob(name, globbed)
                self._callback(("addglob", (name, globbed)))
        else:
            append_files = files.append
            for name in self.listdir():
                append_files(os.path.realpath(os.path.join(self._folder, name)))

        for absname in files:
            try:
                st = os.stat(absname)
            except EnvironmentError, err:
                if err.errno != errno.ENOENT:
                    raise
            else:
                if not stat.S_ISREG(st.st_mode):
                    continue
                append_possible_files = possible_files.append
                fid = self.get_file_id(st)
                append_possible_files((fid, absname))

        # add new ones
        new_files = [fname for fid, fname in possible_files if fid not in self._tails]
        self.watch(new_files)

    def close(self, signalnum=None, frame=None):
        self._running = False
        """Closes all currently open Tail objects"""
        self._log_debug("Closing all tail objects")
        self._active = False
        for fid in self._tails:
            self._tails[fid].close()
        if self._proc is not None and self._proc.is_alive():
            self._proc.terminate()
            self._proc.join()

    @staticmethod
    def get_file_id(st):
        return "%xg%x" % (st.st_dev, st.st_ino)

########NEW FILE########
__FILENAME__ = worker
# -*- coding: utf-8 -*-
import collections
import datetime
import errno
import gzip
import io
import os
import signal
import sqlite3
import stat
import time
import threading

from beaver.utils import IS_GZIPPED_FILE, REOPEN_FILES, eglob, multiline_merge
from beaver.unicode_dammit import ENCODINGS


class Worker(object):
    """Looks for changes in all files of a directory.
    This is useful for watching log file changes in real-time.
    It also supports files rotation.

    Example:

    >>> def callback(filename, lines):
    ...     print filename, lines
    ...
    >>> l = Worker(args, callback, ["log", "txt"])
    >>> l.loop()
    """

    def __init__(self, beaver_config, queue_consumer_function, callback, logger=None):
        """Arguments:

        (FileConfig) @file_config:
            object containing file-related configuration

        (BeaverConfig) @beaver_config:
            object containing global configuration

        (Logger) @logger
            object containing a python logger

        (callable) @callback:
            a function which is called every time a new line in a
            file being watched is found;
            this is called with "filename" and "lines" arguments.
        """
        self._beaver_config = beaver_config
        self._callback = callback
        self._create_queue_consumer = queue_consumer_function
        self._file_map = {}
        self._folder = self._beaver_config.get('path')
        self._last_file_mapping_update = {}
        self._logger = logger
        self._proc = None
        self._sincedb_path = self._beaver_config.get('sincedb_path')
        self._update_time = None
        self._running = True

        if not callable(self._callback):
            raise RuntimeError("Callback for worker is not callable")

        self.update_files()
        self._seek_to_end()
        signal.signal(signal.SIGTERM, self.close)

    def __del__(self):
        """Closes all files"""
        self.close()

    def close(self, signalnum=None, frame=None):
        self._running = False
        """Closes all currently open file pointers"""
        for id, data in self._file_map.iteritems():
            data['file'].close()
        self._file_map.clear()
        if self._proc is not None and self._proc.is_alive():
            self._proc.terminate()
            self._proc.join()


    def listdir(self):
        """List directory and filter files by extension.
        You may want to override this to add extra logic or
        globbling support.
        """
        if self._folder is not None:
            ls = os.listdir(self._folder)
            return [x for x in ls if os.path.splitext(x)[1][1:] == "log"]
        else:
            return []

    def create_queue_consumer_if_required(self, interval=5.0):
        if not (self._proc and self._proc.is_alive()):
            self._proc = self._create_queue_consumer()
        timer = threading.Timer(interval, self.create_queue_consumer_if_required)
        timer.start()

    def loop(self, interval=0.1, async=False):
        """Start the loop.
        If async is True make one loop then return.
        """

        self.create_queue_consumer_if_required()

        while self._running:

            t = time.time()

            if int(time.time()) - self._update_time > self._beaver_config.get('discover_interval'):
                self.update_files()

            self._ensure_files_are_good(current_time=t)

            unwatch_list = []

            for fid, data in self._file_map.iteritems():
                try:
                    self._run_pass(fid, data['file'])
                except IOError, e:
                    if e.errno == errno.ESTALE:
                        unwatch_list.append(fid)

            self.unwatch_list(unwatch_list)

            if async:
                return

            self._logger.debug("Iteration took {0:.6f}".format(time.time() - t))
            time.sleep(interval)

    def _run_pass(self, fid, file):
        """Read lines from a file and performs a callback against them"""
        line_count = 0
        while True:
            try:
                data = file.read(4096)
            except IOError, e:
                if e.errno == errno.ESTALE:
                    self.active = False
                    return False

            lines = self._buffer_extract(data=data, fid=fid)

            if not lines:
                # Before returning, check if an event (maybe partial) is waiting for too long.
                if self._file_map[fid]['current_event'] and time.time() - self._file_map[fid]['last_activity'] > 1:
                    event = '\n'.join(self._file_map[fid]['current_event'])
                    self._file_map[fid]['current_event'].clear()
                    self._callback_wrapper(filename=file.name, lines=[event])
                break

            self._file_map[fid]['last_activity'] = time.time()

            if self._file_map[fid]['multiline_regex_after'] or self._file_map[fid]['multiline_regex_before']:
                # Multiline is enabled for this file.
                events = multiline_merge(
                        lines,
                        self._file_map[fid]['current_event'],
                        self._file_map[fid]['multiline_regex_after'],
                        self._file_map[fid]['multiline_regex_before'])
            else:
                events = lines

            if events:
                self._callback_wrapper(filename=file.name, lines=events)

            if self._sincedb_path:
                current_line_count = len(lines)
                if not self._sincedb_update_position(file, fid=fid, lines=current_line_count):
                    line_count += current_line_count

        if line_count > 0:
            self._sincedb_update_position(file, fid=fid, lines=line_count, force_update=True)

    def _buffer_extract(self, data, fid):
        """
        Extract takes an arbitrary string of input data and returns an array of
        tokenized entities, provided there were any available to extract.  This
        makes for easy processing of datagrams using a pattern like:

          tokenizer.extract(data).map { |entity| Decode(entity) }.each do ..."""
        # Extract token-delimited entities from the input string with the split command.
        # There's a bit of craftiness here with the -1 parameter.  Normally split would
        # behave no differently regardless of if the token lies at the very end of the
        # input buffer or not (i.e. a literal edge case)  Specifying -1 forces split to
        # return "" in this case, meaning that the last entry in the list represents a
        # new segment of data where the token has not been encountered
        entities = collections.deque(data.split(self._file_map[fid]['delimiter'], -1))

        # Check to see if the buffer has exceeded capacity, if we're imposing a limit
        if self._file_map[fid]['size_limit']:
            if self._file_map[fid]['input_size'] + len(entities[0]) > self._file_map[fid]['size_limit']:
                raise Exception('input buffer full')
            self._file_map[fid]['input_size'] += len(entities[0])

        # Move the first entry in the resulting array into the input buffer.  It represents
        # the last segment of a token-delimited entity unless it's the only entry in the list.
        first_entry = entities.popleft()
        if len(first_entry) > 0:
            self._file_map[fid]['input'].append(first_entry)

        # If the resulting array from the split is empty, the token was not encountered
        # (not even at the end of the buffer).  Since we've encountered no token-delimited
        # entities this go-around, return an empty array.
        if len(entities) == 0:
            return []

        # At this point, we've hit a token, or potentially multiple tokens.  Now we can bring
        # together all the data we've buffered from earlier calls without hitting a token,
        # and add it to our list of discovered entities.
        entities.appendleft(''.join(self._file_map[fid]['input']))

        # Now that we've hit a token, joined the input buffer and added it to the entities
        # list, we can go ahead and clear the input buffer.  All of the segments that were
        # stored before the join can now be garbage collected.
        self._file_map[fid]['input'].clear()

        # The last entity in the list is not token delimited, however, thanks to the -1
        # passed to split.  It represents the beginning of a new list of as-yet-untokenized
        # data, so we add it to the start of the list.
        self._file_map[fid]['input'].append(entities.pop())

        # Set the new input buffer size, provided we're keeping track
        if self._file_map[fid]['size_limit']:
            self._file_map[fid]['input_size'] = len(self._file_map[fid]['input'][0])

        # Now we're left with the list of extracted token-delimited entities we wanted
        # in the first place.  Hooray!
        return entities

    # Flush the contents of the input buffer, i.e. return the input buffer even though
    # a token has not yet been encountered
    def _buffer_flush(self, fid):
        buf = ''.join(self._file_map[fid]['input'])
        self._file_map[fid]['input'].clear
        return buf

    # Is the buffer empty?
    def _buffer_empty(self, fid):
        return len(self._file_map[fid]['input']) > 0

    def _seek_to_end(self):
        unwatch_list = []

        # The first time we run the script we move all file markers at EOF.
        # In case of files created afterwards we don't do this.
        for fid, data in self._file_map.iteritems():
            self._logger.debug("[{0}] - getting start position {1}".format(fid, data['file'].name))
            start_position = self._beaver_config.get_field('start_position', data['file'].name)
            is_active = data['active']

            if self._sincedb_path:
                sincedb_start_position = self._sincedb_start_position(data['file'], fid=fid)
                if sincedb_start_position:
                    start_position = sincedb_start_position

            if start_position == "beginning":
                continue

            line_count = 0

            if str(start_position).isdigit():
                self._logger.debug("[{0}] - going to start position {1} for {2}".format(fid, start_position, data['file'].name))
                start_position = int(start_position)
                for encoding in ENCODINGS:
                    try:
                        line_count = 0
                        while data['file'].readline():
                            line_count += 1
                            if line_count == start_position:
                                break
                    except UnicodeDecodeError:
                        self._logger.debug("[{0}] - UnicodeDecodeError raised for {1} with encoding {2}".format(fid, data['file'].name, data['encoding']))
                        data['file'] = self.open(data['file'].name, encoding=encoding)
                        if not data['file']:
                            unwatch_list.append(fid)
                            is_active = False
                            break

                        data['encoding'] = encoding

                    if line_count != start_position:
                        self._logger.debug("[{0}] - file at different position than {1}, assuming manual truncate for {2}".format(fid, start_position, data['file'].name))
                        data['file'].seek(0, os.SEEK_SET)
                        start_position == "beginning"

            if not is_active:
                continue

            if start_position == "beginning":
                continue

            if start_position == "end":
                self._logger.debug("[{0}] - getting end position for {1}".format(fid, data['file'].name))
                for encoding in ENCODINGS:
                    try:
                        line_count = 0
                        while data['file'].readline():
                            line_count += 1
                        break
                    except UnicodeDecodeError:
                        self._logger.debug("[{0}] - UnicodeDecodeError raised for {1} with encoding {2}".format(fid, data['file'].name, data['encoding']))
                        data['file'] = self.open(data['file'].name, encoding=encoding)
                        if not data['file']:
                            unwatch_list.append(fid)
                            is_active = False
                            break

                        data['encoding'] = encoding

            if not is_active:
                continue

            current_position = data['file'].tell()
            self._logger.debug("[{0}] - line count {1} for {2}".format(fid, line_count, data['file'].name))
            self._sincedb_update_position(data['file'], fid=fid, lines=line_count, force_update=True)

            tail_lines = self._beaver_config.get_field('tail_lines', data['file'].name)
            tail_lines = int(tail_lines)
            if tail_lines:
                encoding = data['encoding']

                lines = self.tail(data['file'].name, encoding=encoding, window=tail_lines, position=current_position)
                if lines:
                    if self._file_map[fid]['multiline_regex_after'] or self._file_map[fid]['multiline_regex_before']:
                        # Multiline is enabled for this file.
                        events = multiline_merge(
                                lines,
                                self._file_map[fid]['current_event'],
                                self._file_map[fid]['multiline_regex_after'],
                                self._file_map[fid]['multiline_regex_before'])
                    else:
                        events = lines
                    self._callback_wrapper(filename=data['file'].name, lines=events)

        self.unwatch_list(unwatch_list)

    def _callback_wrapper(self, filename, lines):
        now = datetime.datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S") + ".%03d" % (now.microsecond / 1000) + "Z"
        self._callback(('callback', {
            'fields': self._beaver_config.get_field('fields', filename),
            'filename': filename,
            'format': self._beaver_config.get_field('format', filename),
            'ignore_empty': self._beaver_config.get_field('ignore_empty', filename),
            'lines': lines,
            'timestamp': timestamp,
            'tags': self._beaver_config.get_field('tags', filename),
            'type': self._beaver_config.get_field('type', filename),
        }))

    def _sincedb_init(self):
        """Initializes the sincedb schema in an sqlite db"""
        if not self._sincedb_path:
            return

        if not os.path.exists(self._sincedb_path):
            self._logger.debug('Initializing sincedb sqlite schema')
            conn = sqlite3.connect(self._sincedb_path, isolation_level=None)
            conn.execute("""
            create table sincedb (
                fid      text primary key,
                filename text,
                position integer default 1
            );
            """)
            conn.close()

    def _sincedb_update_position(self, file, fid=None, lines=0, force_update=False):
        """Retrieves the starting position from the sincedb sql db for a given file
        Returns a boolean representing whether or not it updated the record
        """
        if not self._sincedb_path:
            return False

        if not fid:
            fid = self.get_file_id(os.stat(file.name))

        current_time = int(time.time())
        update_time = self._file_map[fid]['update_time']
        if not force_update:
            sincedb_write_interval = self._beaver_config.get_field('sincedb_write_interval', file.name)
            if update_time and current_time - update_time <= sincedb_write_interval:
                return False

            if lines == 0:
                return False

        self._sincedb_init()

        old_count = self._file_map[fid]['line']
        self._file_map[fid]['update_time'] = current_time
        self._file_map[fid]['line'] = old_count + lines
        lines = self._file_map[fid]['line']

        self._logger.debug("[{0}] - updating sincedb for logfile {1} from {2} to {3}".format(fid, file.name, old_count, lines))

        conn = sqlite3.connect(self._sincedb_path, isolation_level=None)
        cursor = conn.cursor()
        query = "insert or ignore into sincedb (fid, filename) values (:fid, :filename);"
        cursor.execute(query, {
            'fid': fid,
            'filename': file.name
        })

        query = "update sincedb set position = :position where fid = :fid and filename = :filename"
        cursor.execute(query, {
            'fid': fid,
            'filename': file.name,
            'position': int(lines),
        })
        conn.close()

        return True

    def _sincedb_start_position(self, file, fid=None):
        """Retrieves the starting position from the sincedb sql db
        for a given file
        """
        if not self._sincedb_path:
            return None

        if not fid:
            fid = self.get_file_id(os.stat(file.name))

        self._sincedb_init()
        conn = sqlite3.connect(self._sincedb_path, isolation_level=None)
        cursor = conn.cursor()
        cursor.execute("select position from sincedb where fid = :fid and filename = :filename", {
            'fid': fid,
            'filename': file.name
        })

        start_position = None
        for row in cursor.fetchall():
            start_position, = row

        return start_position

    def update_files(self):
        """Ensures all files are properly loaded.
        Detects new files, file removals, file rotation, and truncation.
        On non-linux platforms, it will also manually reload the file for tailing.
        Note that this hack is necessary because EOF is cached on BSD systems.
        """
        self._update_time = int(time.time())

        ls = []
        files = []
        if len(self._beaver_config.get('globs')) > 0:
            for name, exclude in self._beaver_config.get('globs').items():
                globbed = [os.path.realpath(filename) for filename in eglob(name, exclude)]
                files.extend(globbed)
                self._beaver_config.addglob(name, globbed)
                self._callback(("addglob", (name, globbed)))
        else:
            for name in self.listdir():
                files.append(os.path.realpath(os.path.join(self._folder, name)))

        for absname in files:
            try:
                st = os.stat(absname)
            except EnvironmentError, err:
                if err.errno != errno.ENOENT:
                    raise
            else:
                if not stat.S_ISREG(st.st_mode):
                    continue
                fid = self.get_file_id(st)
                ls.append((fid, absname))

        # add new ones
        for fid, fname in ls:
            if fid not in self._file_map:
                self.watch(fname)

    def _ensure_files_are_good(self, current_time):
        """Every N seconds, ensures that the file we are tailing is the file we expect to be tailing"""

        # We cannot watch/unwatch in a single iteration
        rewatch_list = []
        unwatch_list = []

        # check existent files
        for fid, data in self._file_map.iteritems():
            filename = data['file'].name
            stat_interval = self._beaver_config.get_field('stat_interval', filename)
            if filename in self._last_file_mapping_update and current_time - self._last_file_mapping_update[filename] <= stat_interval:
                continue

            self._last_file_mapping_update[filename] = time.time()

            try:
                st = os.stat(data['file'].name)
            except EnvironmentError, err:
                if err.errno == errno.ENOENT:
                    unwatch_list.append(fid)
                else:
                    raise
            else:
                if fid != self.get_file_id(st):
                    self._logger.info("[{0}] - file rotated {1}".format(fid, data['file'].name))
                    rewatch_list.append(fid)
                elif data['file'].tell() > st.st_size:
                    if st.st_size == 0 and self._beaver_config.get_field('ignore_truncate', data['file'].name):
                        self._logger.info("[{0}] - file size is 0 {1}. ".format(fid, data['file'].name) +
                                          "If you use another tool (i.e. logrotate) to truncate " +
                                          "the file, your application may continue to write to " +
                                          "the offset it last wrote later. In such a case, we'd " +
                                          "better do nothing here")
                        continue
                    self._logger.info("[{0}] - file truncated {1}".format(fid, data['file'].name))
                    rewatch_list.append(fid)
                elif REOPEN_FILES:
                    self._logger.debug("[{0}] - file reloaded (non-linux) {1}".format(fid, data['file'].name))
                    position = data['file'].tell()
                    fname = data['file'].name
                    data['file'].close()
                    file = self.open(fname, encoding=data['encoding'])
                    if file:
                        file.seek(position)
                        self._file_map[fid]['file'] = file

        self.unwatch_list(unwatch_list)
        self.rewatch_list(rewatch_list)

    def rewatch_list(self, rewatch_list):
        for fid in rewatch_list:
            if fid not in self._file_map:
                continue

            f = self._file_map[fid]['file']
            filename = f.name
            self.unwatch(f, fid)
            self.watch(filename)

    def unwatch_list(self, unwatch_list):
        for fid in unwatch_list:
            if fid not in self._file_map:
                continue

            f = self._file_map[fid]['file']
            self.unwatch(f, fid)

    def unwatch(self, file, fid):
        """file no longer exists; if it has been renamed
        try to read it for the last time in case the
        log rotator has written something in it.
        """
        try:
            if file:
                self._run_pass(fid, file)
                if self._file_map[fid]['current_event']:
                    event = '\n'.join(self._file_map[fid]['current_event'])
                    self._file_map[fid]['current_event'].clear()
                    self._callback_wrapper(filename=file.name, lines=[event])
        except IOError:
            # Silently ignore any IOErrors -- file is gone
            pass

        if file:
            self._logger.info("[{0}] - un-watching logfile {1}".format(fid, file.name))
        else:
            self._logger.info("[{0}] - un-watching logfile".format(fid))

        self._file_map[fid]['file'].close()
        del self._file_map[fid]

    def watch(self, fname):
        """Opens a file for log tailing"""
        try:
            file = self.open(fname, encoding=self._beaver_config.get_field('encoding', fname))
            if file:
                fid = self.get_file_id(os.stat(fname))
        except EnvironmentError, err:
            if err.errno != errno.ENOENT:
                raise
        else:
            if file:
                self._logger.info("[{0}] - watching logfile {1}".format(fid, fname))
                self._file_map[fid] = {
                    'current_event': collections.deque([]),
                    'delimiter': self._beaver_config.get_field('delimiter', fname),
                    'encoding': self._beaver_config.get_field('encoding', fname),
                    'file': file,
                    'input': collections.deque([]),
                    'input_size': 0,
                    'last_activity': time.time(),
                    'line': 0,
                    'multiline_regex_after': self._beaver_config.get_field('multiline_regex_after', fname),
                    'multiline_regex_before': self._beaver_config.get_field('multiline_regex_before', fname),
                    'size_limit': self._beaver_config.get_field('size_limit', fname),
                    'update_time': None,
                    'active': True,
                }

    def open(self, filename, encoding=None):
        """Opens a file with the appropriate call"""
        try:
            if IS_GZIPPED_FILE.search(filename):
                _file = gzip.open(filename, "rb")
            else:
                file_encoding = self._beaver_config.get_field('encoding', filename)
                if encoding:
                    _file = io.open(filename, "r", encoding=encoding, errors='replace')
                elif file_encoding:
                    _file = io.open(filename, "r", encoding=file_encoding, errors='replace')
                else:
                    _file = io.open(filename, "r", errors='replace')
        except IOError, e:
            self._logger.warning(str(e))
            _file = None

        return _file

    def tail(self, fname, encoding, window, position=None):
        """Read last N lines from file fname."""
        if window <= 0:
            raise ValueError('invalid window %r' % window)

        encodings = ENCODINGS
        if encoding:
            encodings = [encoding] + ENCODINGS

        for enc in encodings:
            try:
                f = self.open(fname, encoding=enc)
                if not f:
                    return []
                return self.tail_read(f, window, position=position)
            except IOError, err:
                if err.errno == errno.ENOENT:
                    return []
                raise
            except UnicodeDecodeError:
                pass

    @staticmethod
    def get_file_id(st):
        return "%xg%x" % (st.st_dev, st.st_ino)

    @classmethod
    def tail_read(cls, f, window, position=None):
        BUFSIZ = 1024
        # open() was overridden and file was opened in text
        # mode; read() will return a string instead bytes.
        encoded = getattr(f, 'encoding', False)
        CR = '\n' if encoded else b'\n'
        data = '' if encoded else b''
        f.seek(0, os.SEEK_END)
        if position is None:
            position = f.tell()

        block = -1
        exit = False
        read = BUFSIZ

        while not exit:
            step = (block * BUFSIZ) + position
            if step < 0:
                step = 0
                read = ((block + 1) * BUFSIZ) + position
                exit = True

            f.seek(step, os.SEEK_SET)
            newdata = f.read(read)

            data = newdata + data
            if data.count(CR) > window:
                break
            else:
                block -= 1

        return data.splitlines()[-window:]

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# beaver documentation build configuration file, created by
# sphinx-quickstart on Mon Oct 21 11:21:22 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'beaver'
copyright = u'2013, Jose Diaz-Gonzalez'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '31'
# The full version, including alpha/beta/rc tags.
release = '31'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'beaverdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'beaver.tex', u'beaver Documentation',
   u'Jose Diaz-Gonzalez', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'beaver', u'beaver Documentation',
     [u'Jose Diaz-Gonzalez'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'beaver', u'beaver Documentation',
   u'Jose Diaz-Gonzalez', 'beaver', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
