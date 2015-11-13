__FILENAME__ = cli
from optparse import OptionParser, make_option
import sys

class CLI(object):

    color = {
        "PINK": "",
        "BLUE": "",
        "CYAN": "",
        "GREEN": "",
        "YELLOW": "",
        "RED": "",
        "END": "",
    }

    @staticmethod
    def show_colors():
        CLI.color = {
            "PINK": "\033[35m",
            "BLUE": "\033[34m",
            "CYAN": "\033[36m",
            "GREEN": "\033[32m",
            "YELLOW": "\033[33m",
            "RED": "\033[31m",
            "END": "\033[0m",
        }

    @staticmethod
    def parse(args=None):
        parser = OptionParser(option_list=CLI.options_to_parser())
        parser.add_option("-v", "--version",
                action="store_true",
                dest="simple_db_migrate_version",
                default=False,
                help="Displays simple-db-migrate's version and exit.")
        return parser.parse_args(args)

    @classmethod
    def options_to_parser(cls):
        return (
        make_option("-c", "--config",
                dest="config_file",
                default=None,
                help="Use a specific config file. If not provided, will search for 'simple-db-migrate.conf' in the current directory."),

        make_option("-l", "--log-level",
                dest="log_level",
                default=1,
                help="Log level: 0-no log; 1-migrations log; 2-statement execution log (default: %default)"),

        make_option("--log-dir",
                dest="log_dir",
                default=None,
                help="Directory to save the log files of execution"),

        make_option("--force-old-migrations", "--force-execute-old-migrations-versions",
                action="store_true",
                dest="force_execute_old_migrations_versions",
                default=False,
                help="Forces the use of the old migration files even if the destination version is the same as current destination "),

        make_option("--force-files", "--force-use-files-on-down",
                action="store_true",
                dest="force_use_files_on_down",
                default=False,
                help="Forces the use of the migration files instead of using the field sql_down stored on the version table in database downgrade operations "),

        make_option("-m", "--migration",
                dest="schema_version",
                default=None,
                help="Schema version to migrate to. If not provided will migrate to the last version available in the migrations directory."),

        make_option("-n", "--create", "--new",
                dest="new_migration",
                default=None,
                help="Create migration file with the given nickname. The nickname should contain only lowercase characters and underscore '_'. Example: 'create_table_xyz'."),

        make_option("-p", "--paused-mode",
                action="store_true",
                dest="paused_mode",
                default=False,
                help="Execute in 'paused' mode. In this mode you will need to press <enter> key in order to execute each SQL command, making it easier to see what is being executed and helping debug. When paused mode is enabled, log level is automatically set to [2]."),

        make_option("--color",
                action="store_true",
                dest="show_colors",
                default=False,
                help="Output with beautiful colors."),

        make_option("--drop", "--drop-database-first",
                action="store_true",
                dest="drop_db_first",
                default=False,
                help="Drop database before running migrations to create everything from scratch. Useful when the database schema is corrupted and the migration scripts are not working."),

        make_option("--show-sql",
                action="store_true",
                dest="show_sql",
                default=False,
                help="Show all SQL statements executed."),

        make_option("--show-sql-only",
                action="store_true",
                dest="show_sql_only",
                default=False,
                help="Show all SQL statements that would be executed but DON'T execute them in the database."),

        make_option("--label",
                dest="label_version",
                default=None,
                help="Give this label the migrations executed or execute a down to him."),

        make_option("--password",
                dest="password",
                default=None,
                help="Use this password to connect to database, to auto."),

        make_option("--env", "--environment",
                dest="environment",
                default="",
                help="Use this environment to get specific configurations."),

        make_option("--utc-timestamp",
                action="store_true",
                dest="utc_timestamp",
                default=False,
                help="Use utc datetime value on the name of migration when creating one."),

        make_option("--db-engine",
                dest="database_engine",
                default=None,
                help="Set each engine to use as sgdb (mysql, oracle, mssql). (default: 'mysql')"),

        make_option("--db-version-table",
                dest="database_version_table",
                default=None,
                help="Set the name of the table used to save migrations history. (default: '__db_version__')"),

        make_option("--db-user",
                dest="database_user",
                default=None,
                help="Set the username to connect to database."),

        make_option("--db-password",
                dest="database_password",
                default=None,
                help="Set the password to connect to database."),

        make_option("--db-host",
                dest="database_host",
                default=None,
                help="Set the host where the database is."),

        make_option("--db-port",
                dest="database_port",
                default=None,
                type="int",
                help="Set the port where the database is."),

        make_option("--db-name",
                dest="database_name",
                default=None,
                help="Set the name of the database."),

        make_option("--db-migrations-dir",
                dest="database_migrations_dir",
                default=None,
                help="List of directories where migrations are separated by a colon"),
        )

    @classmethod
    def error_and_exit(cls, msg):
        cls.msg("[ERROR] %s\n" % msg, "RED")
        sys.exit(1)

    @classmethod
    def info_and_exit(cls, msg):
        cls.msg("%s\n" % msg, "BLUE")
        sys.exit(0)

    @classmethod
    def msg(cls, msg, color="CYAN"):
        print "%s%s%s" % (cls.color[color], msg, cls.color["END"])

########NEW FILE########
__FILENAME__ = config
import os
import ast
from helpers import Utils

class Config(object):

    def __init__(self, inital_config=None):
        self._config = inital_config or {}
        for key in self._config.keys():
            self._config[key.lower()] = self._config.pop(key)

    def __repr__(self):
        return str(self._config)

    #default_value was assigned as !@#$%&* to be more easy to check when the default value is None, empty string or False
    def get(self, config_key, default_value='!@#$%&*'):
        config_key = config_key.lower()
        return Config._get(self._config, config_key, default_value)

    def put(self, config_key, config_value):
        config_key = config_key.lower()
        if config_key in self._config:
            raise Exception("the configuration key '%s' already exists and you cannot override any configuration" % config_key)
        self._config[config_key] = config_value

    def update(self, config_key, config_value):
        config_key = config_key.lower()
        if config_key in self._config:
            value = self.get(config_key)
            self.remove(config_key)
            config_value = config_value or value
        self.put(config_key, config_value)

    def remove(self, config_key):
        try:
            config_key = config_key.lower()
            del self._config[config_key]
        except KeyError:
            raise Exception("invalid configuration key ('%s')" % config_key)

    #default_value was assigned as !@#$%&* to be more easy to check when the default value is None, empty string or False
    @staticmethod
    def _get(_dict, key, default_value='!@#$%&*'):
        try:
            if ((_dict[key] is None) and (default_value != '!@#$%&*')):
                return default_value
            return _dict[key]
        except KeyError:
            if default_value != '!@#$%&*':
                return default_value
            raise Exception("invalid key ('%s')" % key)

    @staticmethod
    def _parse_migrations_dir(dirs, config_dir=''):
        abs_dirs = []
        for _dir in dirs.split(':'):
            if os.path.isabs(_dir):
                abs_dirs.append(_dir)
            elif config_dir == '':
                abs_dirs.append(os.path.abspath(_dir))
            else:
                abs_dirs.append(os.path.abspath('%s/%s' % (config_dir, _dir)))
        return abs_dirs

class FileConfig(Config):

    def __init__(self, config_file="simple-db-migrate.conf", environment=''):
        # read configuration
        settings = Utils.get_variables_from_file(config_file)

        super(FileConfig, self).__init__(inital_config=settings)

        if environment:
            prefix = environment + "_"
            for key in self._config.keys():
                if key.startswith(prefix):
                    self.update(key[len(prefix):], self.get(key))

        self.update("utc_timestamp", ast.literal_eval(str(self.get("utc_timestamp", 'False'))))

        migrations_dir = self.get("database_migrations_dir", None)
        if migrations_dir:
            config_dir = os.path.split(config_file)[0]
            self.update("database_migrations_dir", FileConfig._parse_migrations_dir(migrations_dir, config_dir))

########NEW FILE########
__FILENAME__ = exceptions
class MigrationException(Exception):
    def __init__(self, msg=None, sql=None):
        self.msg = msg
        if not msg:
            self.msg = 'error executing migration'
        self.sql = sql
        
    def __str__(self):
        if self.sql:
            self.details = '[ERROR DETAILS] SQL command was:\n%s' % self.sql
            return '%s\n\n%s' % (self.msg, self.details)
    
        return self.msg

########NEW FILE########
__FILENAME__ = dbmigrate
#-*- coding:utf-8 -*-

import os
import fnmatch
from optparse import make_option

from django import db
from django.conf import settings
from django.core.management.base import BaseCommand

import simple_db_migrate

class Command(BaseCommand):
    help = "Migrate databases."
    args = "[db_migrate_options]"

    option_list = BaseCommand.option_list + simple_db_migrate.cli.CLI.options_to_parser() + (
        make_option(
            '--database', action='store', dest='database',
            default=getattr(db, 'DEFAULT_DB_ALIAS', 'default'),
            help='Nominates a database to synchronize. Defaults to the "default" database.'
        ),
    )

    def handle(self, *args, **options):
        if not options.get('database_migrations_dir'):
            options['database_migrations_dir'] = Command._locate_migrations()

        for key in ['host', 'name', 'user', 'password']:
            options_key = 'database_' + key
            if options.get(options_key) == None:
                options[options_key] = Command._get_database_option(options, key)

        simple_db_migrate.run(options=options)

    @staticmethod
    def _get_database_option(options, key):
        # Handles Django 1.2+ database settings
        if hasattr(settings, 'DATABASES'):
            return settings.DATABASES[options.get('database')].get(key.upper(), '')
        # Fallback for Django 1.1 or lower
        return getattr(settings, 'DATABASE_' + key.upper(), None)

    @staticmethod
    def _locate_migrations():
        files = Command._locate_resource_dirs("migrations", "*.migration")

        if hasattr(settings, 'OTHER_MIGRATION_DIRS'):
            other_dirs = settings.OTHER_MIGRATION_DIRS
            if not isinstance(other_dirs, (tuple, list)):
                raise TypeError, 'The setting "OTHER_MIGRATION_DIRS" must be a tuple or a list'
            files.extend(other_dirs)

        return ':'.join(files)

    @staticmethod
    def _locate_resource_dirs(complement, pattern):
        _dirs = []
        for app in settings.INSTALLED_APPS:
            fromlist = ""

            app_parts = app.split(".")
            if len(app_parts) > 1:
                fromlist = ".".join(app_parts[1:])

            module = __import__(app, fromlist=fromlist)
            app_dir = os.path.abspath("/" + "/".join(module.__file__.split("/")[1:-1]))

            resource_dir = os.path.join(app_dir, complement)

            if os.path.exists(resource_dir) and Command._locate_files(resource_dir, pattern):
                _dirs.append(resource_dir)

        return _dirs

    @staticmethod
    def _locate_files(root, pattern):
        return_files = []
        for path, _dirs, files in os.walk(root):
            for filename in fnmatch.filter(files, pattern):
                return_files.append(os.path.join(path, filename))
        return return_files

########NEW FILE########
__FILENAME__ = helpers
import os
import sys
import tempfile

class Lists(object):

    @staticmethod
    def subtract(list_a, list_b):
        return [l for l in list_a if l not in list_b]

class Utils(object):

    @staticmethod
    def count_occurrences(string):
        count = {}
        for char in string:
            count[char] = count.get(char, 0) + 1
        return count

    @staticmethod
    def get_variables_from_file(full_filename, file_encoding='utf-8'):
        path, filename = os.path.split(full_filename)
        temp_abspath = None

        global_dict = globals().copy()
        local_dict = {}

        try:
            # add settings dir from path
            sys.path.insert(0, path)

            execfile(full_filename, global_dict, local_dict)
        except IOError:
            raise Exception("%s: file not found" % full_filename)
        except Exception, e:
            try:
                f = open(full_filename, "rU")
                content = f.read()
                f.close()

                temp_abspath = "%s/%s" %(tempfile.gettempdir().rstrip('/'), filename)
                f = open(temp_abspath, "w")
                f.write('#-*- coding:%s -*-\n%s' % (file_encoding, content))
                f.close()

                execfile(temp_abspath, global_dict, local_dict)
            except Exception, e:
                raise Exception("error interpreting config file '%s': %s" % (filename, str(e)))
        finally:
            #erase temp and compiled files
            if temp_abspath and os.path.isfile(temp_abspath):
                os.remove(temp_abspath)

            # remove settings dir from path
            if path in sys.path:
                sys.path.remove(path)

        return local_dict

########NEW FILE########
__FILENAME__ = log
import logging
import os
from datetime import datetime

class LOG(object):
    logger = None
    def __init__(self, log_dir):
        if log_dir:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            self.logger = logging.getLogger('simple-db-migrate')

            now = datetime.now()
            filename = "%s/%s.log" %(os.path.abspath(log_dir), now.strftime("%Y%m%d%H%M%S"))
            hdlr = logging.FileHandler(filename)
            formatter = logging.Formatter('%(message)s')
            hdlr.setFormatter(formatter)
            self.logger.addHandler(hdlr)
            self.logger.setLevel(logging.DEBUG)

    def debug(self, msg):
        if self.logger:
            self.logger.debug(msg)

    def info(self, msg):
        if self.logger:
            self.logger.info(msg)

    def error(self, msg):
        if self.logger:
            self.logger.error(msg)

    def warn(self, msg):
        if self.logger:
            self.logger.warn(msg)

########NEW FILE########
__FILENAME__ = main
from cli import CLI
from log import LOG
from core import Migration, SimpleDBMigrate
from helpers import Lists
from config import Config

"""
The sgbd class should implement the following methods
- change(self, sql, new_db_version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None)
  executes the migration (up or down) and records the change on version table
- get_all_schema_migrations(self)
  return all migrations saved on version table
- get_all_schema_versions(self)
  return all versions saved on version table
- get_current_schema_version(self)
  return the current schema version
- get_version_id_from_version_number(self, version)
  return the id from an specific version
- get_version_number_from_label(self, label)
  return the version of the last migration executed under the label
"""

class Main(object):

    def __init__(self, config, sgdb=None):
        Main._check_configuration(config)

        self.cli = CLI()
        self.config = config
        self.log = LOG(self.config.get("log_dir", None))

        self.sgdb = sgdb
        if self.sgdb is None and not self.config.get("new_migration", None):
            if self.config.get("database_engine") == 'mysql':
                from mysql import MySQL
                self.sgdb = MySQL(config)
            elif self.config.get("database_engine") == 'oracle':
                from oracle import Oracle
                self.sgdb = Oracle(config)
            elif self.config.get("database_engine") == 'mssql':
                from mssql import MSSQL
                self.sgdb = MSSQL(config)
            else:
                raise Exception("engine not supported '%s'" % self.config.get("database_engine"))

        self.db_migrate = SimpleDBMigrate(self.config)

    def execute(self):
        self._execution_log('\nStarting DB migration on host/database "%s/%s" with user "%s"...' % (self.config.get('database_host'), self.config.get('database_name'), self.config.get('database_user')), "PINK", log_level_limit=1)        
        if self.config.get("new_migration", None):
            self._create_migration()
        else:
            self._migrate()
        self._execution_log("\nDone.\n", "PINK", log_level_limit=1)

    @staticmethod
    def _check_configuration(config):
        if not isinstance(config, Config):
            raise Exception("config must be an instance of simple_db_migrate.config.Config")

        required_configs = ['database_host', 'database_name', 'database_user', 'database_password', 'database_migrations_dir', 'database_engine', 'schema_version']
        if config.get("new_migration", None):
            required_configs = ['database_migrations_dir']

        for key in required_configs:
            #check if config has the key, if do not have will raise exception
            config.get(key)

    def _create_migration(self):
        migrations_dir = self.config.get("database_migrations_dir")
        new_file = Migration.create(self.config.get("new_migration", None), migrations_dir[0], self.config.get("database_script_encoding", "utf-8"), self.config.get("utc_timestamp", False))
        self._execution_log("- Created file '%s'" % (new_file), log_level_limit=1)

    def _migrate(self):
        destination_version = self._get_destination_version()
        current_version = self.sgdb.get_current_schema_version()

        # do it!
        self._execute_migrations(current_version, destination_version)

    def _get_destination_version(self):
        label_version = self.config.get("label_version", None)
        schema_version = self.config.get("schema_version", None)

        destination_version = None
        destination_version_by_label = None
        destination_version_by_schema = None

        if label_version is not None:
            destination_version_by_label = self.sgdb.get_version_number_from_label(label_version)
            """
            if specified label exists at database and schema version was not specified,
            is equivalent to run simple-db-migrate with schema_version equals to the version with specified label
            """
            if destination_version_by_label is not None and schema_version is None:
                schema_version = destination_version_by_label
                self.config.update("schema_version", destination_version_by_label)

        if schema_version is not None and self.sgdb.get_version_id_from_version_number(schema_version):
            destination_version_by_schema = schema_version

        if label_version is None:
            if schema_version is None:
                destination_version = self.db_migrate.latest_version_available()
            elif destination_version_by_schema is None:
                destination_version = schema_version
            else:
                destination_version = destination_version_by_schema
        else:
            if schema_version is None:
                destination_version = self.db_migrate.latest_version_available()
            elif (destination_version_by_label is None) or (destination_version_by_schema == destination_version_by_label):
                destination_version = schema_version

        if (destination_version_by_schema is not None) and (destination_version_by_label is not None) and (destination_version_by_schema != destination_version_by_label):
            raise Exception("label (%s) and schema_version (%s) don't correspond to the same version at database" % (label_version, schema_version))

        if (schema_version is not None and label_version is not None) and ((destination_version_by_schema is not None and destination_version_by_label is None) or (destination_version_by_schema is None and destination_version_by_label is not None)):
            raise Exception("label (%s) or schema_version (%s), only one of them exists in the database" % (label_version, schema_version))

        if destination_version is not '0' and not (self.db_migrate.check_if_version_exists(destination_version) or self.sgdb.get_version_id_from_version_number(destination_version)):
            raise Exception("version not found (%s)" % destination_version)

        return destination_version

    def _get_migration_files_to_be_executed(self, current_version, destination_version, is_migration_up):
        if current_version == destination_version and not self.config.get("force_execute_old_migrations_versions", False):
            return []

        schema_migrations = self.sgdb.get_all_schema_migrations()

        # migration up
        if is_migration_up:
            available_migrations = self.db_migrate.get_all_migrations()
            remaining_migrations = Lists.subtract(available_migrations, schema_migrations)
            remaining_migrations_to_execute = [migration for migration in remaining_migrations if migration.version <= destination_version]
            return remaining_migrations_to_execute

        # migration down...
        destination_version_id = self.sgdb.get_version_id_from_version_number(destination_version)
        try:
            migration_versions = self.db_migrate.get_all_migration_versions()
        except:
            migration_versions = []
        down_migrations_to_execute = [migration for migration in schema_migrations if migration.id > destination_version_id]
        force_files = self.config.get("force_use_files_on_down", False)
        for migration in down_migrations_to_execute:
            if not migration.sql_down or force_files:
                if migration.version not in migration_versions:
                    raise Exception("impossible to migrate down: one of the versions was not found (%s)" % migration.version)
                migration_tmp = self.db_migrate.get_migration_from_version_number(migration.version)
                migration.sql_up = migration_tmp.sql_up
                migration.sql_down = migration_tmp.sql_down
                migration.file_name = migration_tmp.file_name

        down_migrations_to_execute.reverse()
        return down_migrations_to_execute

    def _execute_migrations(self, current_version, destination_version):
        """
        passed a version:
            this version don't exists in the database and is younger than the last version -> do migrations up until this version
            this version don't exists in the database and is older than the last version -> do nothing, is a unpredictable behavior
            this version exists in the database and is older than the last version -> do migrations down until this version

        didn't pass a version -> do migrations up until the last available version
        """

        is_migration_up = True
        # check if a version was passed to the program
        if self.config.get("schema_version"):
            # if was passed and this version is present in the database, check if is older than the current version
            destination_version_id = self.sgdb.get_version_id_from_version_number(destination_version)
            if destination_version_id:
                current_version_id = self.sgdb.get_version_id_from_version_number(current_version)
                # if this version is previous to the current version in database, then will be done a migration down to this version
                if current_version_id > destination_version_id:
                    is_migration_up = False
            # if was passed and this version is not present in the database and is older than the current version, raise an exception
            # cause is trying to go down to something that never was done
            elif current_version > destination_version:
                raise Exception("Trying to migrate to a lower version wich is not found on database (%s)" % destination_version)

        # getting only the migration sql files to be executed
        migrations_to_be_executed = self._get_migration_files_to_be_executed(current_version, destination_version, is_migration_up)

        self._execution_log("- Current version is: %s" % current_version, "GREEN", log_level_limit=1)

        if migrations_to_be_executed is None or len(migrations_to_be_executed) == 0:
            self._execution_log("- Destination version is: %s" % current_version, "GREEN", log_level_limit=1)
            self._execution_log("\nNothing to do.\n", "PINK", log_level_limit=1)
            return

        self._execution_log("- Destination version is: %s" % (is_migration_up and migrations_to_be_executed[-1].version or destination_version), "GREEN", log_level_limit=1)

        up_down_label = is_migration_up and "up" or "down"
        if self.config.get("show_sql_only", False):
            self._execution_log("\nWARNING: database migrations are not being executed ('--showsqlonly' activated)", "YELLOW", log_level_limit=1)
        else:
            self._execution_log("\nStarting migration %s!" % up_down_label, log_level_limit=1)

        self._execution_log("*** versions: %s\n" % ([ migration.version for migration in migrations_to_be_executed]), "CYAN", log_level_limit=1)

        sql_statements_executed = []
        for migration in migrations_to_be_executed:
            sql = is_migration_up and migration.sql_up or migration.sql_down

            if not self.config.get("show_sql_only", False):
                self._execution_log("===== executing %s (%s) =====" % (migration.file_name, up_down_label), log_level_limit=1)

                label = None
                if is_migration_up:
                    label = self.config.get("label_version", None)

                try:
                    self.sgdb.change(sql, migration.version, migration.file_name, migration.sql_up, migration.sql_down, is_migration_up, self._execution_log, label)
                except Exception, e:
                    self._execution_log("===== ERROR executing %s (%s) =====" % (migration.abspath, up_down_label), log_level_limit=1)
                    raise e

                # paused mode
                if self.config.get("paused_mode", False):
                    raw_input("* press <enter> to continue... ")

            # recording the last statement executed
            sql_statements_executed.append(sql)

        if self.config.get("show_sql", False) or self.config.get("show_sql_only", False):
            self._execution_log("__________ SQL statements executed __________", "YELLOW", log_level_limit=1)
            for sql in sql_statements_executed:
                self._execution_log(sql, "YELLOW", log_level_limit=1)
            self._execution_log("_____________________________________________", "YELLOW", log_level_limit=1)

    def _execution_log(self, msg, color="CYAN", log_level_limit=2):
        if self.config.get("log_level", 1) >= log_level_limit:
            CLI.msg(msg, color)
        self.log.debug(msg)

########NEW FILE########
__FILENAME__ = mssql
from core import Migration
from core.exceptions import MigrationException
from helpers import Utils

class MSSQL(object):

    def __init__(self, config=None, mssql_driver=None):
        self.__mssql_script_encoding = config.get("database_script_encoding", "utf8")
        self.__mssql_encoding = config.get("database_encoding", "utf8")
        self.__mssql_host = config.get("database_host")
        self.__mssql_port = config.get("database_port", 1433)
        self.__mssql_user = config.get("database_user")
        self.__mssql_passwd = config.get("database_password")
        self.__mssql_db = config.get("database_name")
        self.__version_table = config.get("database_version_table")

        self.__mssql_driver = mssql_driver
        if not mssql_driver:
            import _mssql
            self.__mssql_driver = _mssql

        if config.get("drop_db_first"):
            self._drop_database()

        self._create_database_if_not_exists()
        self._create_version_table_if_not_exists()

    def __mssql_connect(self, connect_using_database_name=True):
        try:
            conn = self.__mssql_driver.connect(server=self.__mssql_host, port=self.__mssql_port, user=self.__mssql_user, password=self.__mssql_passwd, charset=self.__mssql_encoding)
            if connect_using_database_name:
                conn.select_db(self.__mssql_db)
            return conn
        except Exception, e:
            raise Exception("could not connect to database: %s" % e)

    def __execute(self, sql, execution_log=None):
        db = self.__mssql_connect()
        curr_statement = None
        try:
            statments = MSSQL._parse_sql_statements(sql)
            if len(sql.strip(' \t\n\r')) != 0 and len(statments) == 0:
                raise Exception("invalid sql syntax '%s'" % sql)

            for statement in statments:
                curr_statement = statement
                db.execute_non_query(statement)
                affected_rows = db.rows_affected
                if execution_log:
                    execution_log("%s\n-- %d row(s) affected\n" % (statement, affected_rows and int(affected_rows) or 0))
        except Exception, e:
            db.cancel()
            raise MigrationException("error executing migration: %s" % e, curr_statement)
        finally:
            db.close()

    @classmethod
    def _parse_sql_statements(cls, migration_sql):
        all_statements = []
        last_statement = ''

        for statement in migration_sql.split(';'):
            if len(last_statement) > 0:
                curr_statement = '%s;%s' % (last_statement, statement)
            else:
                curr_statement = statement

            count = Utils.count_occurrences(curr_statement)
            single_quotes = count.get("'", 0)
            double_quotes = count.get('"', 0)
            left_parenthesis = count.get('(', 0)
            right_parenthesis = count.get(')', 0)

            if single_quotes % 2 == 0 and double_quotes % 2 == 0 and left_parenthesis == right_parenthesis:
                all_statements.append(curr_statement)
                last_statement = ''
            else:
                last_statement = curr_statement

        return [s.strip() for s in all_statements if ((s.strip() != "") and (last_statement == ""))]

    def _drop_database(self):
        db = self.__mssql_connect(False)
        try:
            db.execute_non_query("if exists ( select 1 from sysdatabases where name = '%s' ) drop database %s;" % (self.__mssql_db, self.__mssql_db))
        except Exception, e:
            raise Exception("can't drop database '%s'; \n%s" % (self.__mssql_db, str(e)))
        finally:
            db.close()

    def _create_database_if_not_exists(self):
        db = self.__mssql_connect(False)
        db.execute_non_query("if not exists ( select 1 from sysdatabases where name = '%s' ) create database %s;" % (self.__mssql_db, self.__mssql_db))
        db.close()

    def _create_version_table_if_not_exists(self):
        # create version table
        sql = "if not exists ( select 1 from sysobjects where name = '%s' and type = 'u' ) create table %s ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT);" % (self.__version_table, self.__version_table)
        self.__execute(sql)

        # check if there is a register there
        db = self.__mssql_connect()
        count = db.execute_scalar("select count(*) from %s;" % self.__version_table)
        db.close()

        # if there is not a version register, insert one
        if count == 0:
            sql = "insert into %s (version) values ('0');" % self.__version_table
            self.__execute(sql)

    def __change_db_version(self, version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None):
        params = []
        params.append(version)

        if up:
            # moving up and storing history
            sql = "insert into %s (version, label, name, sql_up, sql_down) values (%%s, %%s, %%s, %%s, %%s);" % (self.__version_table)
            params.append(label_version)
            params.append(migration_file_name)
            params.append(sql_up and sql_up.encode(self.__mssql_script_encoding) or "")
            params.append(sql_down and sql_down.encode(self.__mssql_script_encoding) or "")
        else:
            # moving down and deleting from history
            sql = "delete from %s where version = %%s;" % (self.__version_table)

        db = self.__mssql_connect()
        try:
            db.execute_non_query(sql.encode(self.__mssql_script_encoding), tuple(params))
            if execution_log:
                execution_log("migration %s registered\n" % (migration_file_name))
        except Exception, e:
            db.cancel()
            raise MigrationException("error logging migration: %s" % e, migration_file_name)
        finally:
            db.close()

    def change(self, sql, new_db_version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None):
        self.__execute(sql, execution_log)
        self.__change_db_version(new_db_version, migration_file_name, sql_up, sql_down, up, execution_log, label_version)

    def get_current_schema_version(self):
        db = self.__mssql_connect()
        version = db.execute_scalar("select top 1 version from %s order by id desc" % self.__version_table) or 0
        db.close()
        return version

    def get_all_schema_versions(self):
        versions = []
        db = self.__mssql_connect()
        db.execute_query("select version from %s order by id;" % self.__version_table)
        all_versions = db
        for version in all_versions:
            versions.append(version['version'])
        db.close()
        versions.sort()
        return versions

    def get_version_id_from_version_number(self, version):
        db = self.__mssql_connect()
        result = db.execute_row("select id from %s where version = '%s' order by id desc;" % (self.__version_table, version))
        _id = result and int(result['id']) or None
        db.close()
        return _id

    def get_version_number_from_label(self, label):
        db = self.__mssql_connect()
        result = db.execute_row("select version from %s where label = '%s' order by id desc" % (self.__version_table, label))
        version = result and result['version'] or None
        db.close()
        return version

    def get_all_schema_migrations(self):
        migrations = []
        db = self.__mssql_connect()
        db.execute_query("select id, version, label, name, cast(sql_up as text) as sql_up, cast(sql_down as text) as sql_down from %s order by id;" % self.__version_table)
        all_migrations = db
        for migration_db in all_migrations:
            migration = Migration(id = int(migration_db['id']),
                                  version = migration_db['version'] and str(migration_db['version']) or None,
                                  label = migration_db['label'] and str(migration_db['label']) or None,
                                  file_name = migration_db['name'] and str(migration_db['name']) or None,
                                  sql_up = Migration.ensure_sql_unicode(migration_db['sql_up'], self.__mssql_script_encoding),
                                  sql_down = Migration.ensure_sql_unicode(migration_db['sql_down'], self.__mssql_script_encoding))
            migrations.append(migration)
        db.close()
        return migrations

########NEW FILE########
__FILENAME__ = mysql
from core import Migration
from core.exceptions import MigrationException
from helpers import Utils

class MySQL(object):

    def __init__(self, config=None, mysql_driver=None):
        self.__mysql_script_encoding = config.get("database_script_encoding", "utf8")
        self.__mysql_encoding = config.get("database_encoding", "utf8")
        self.__mysql_host = config.get("database_host")
        self.__mysql_port = config.get("database_port", 3306)
        self.__mysql_user = config.get("database_user")
        self.__mysql_passwd = config.get("database_password")
        self.__mysql_db = config.get("database_name")
        self.__version_table = config.get("database_version_table")

        self.__mysql_driver = mysql_driver
        if not mysql_driver:
            import MySQLdb
            self.__mysql_driver = MySQLdb

        if config.get("drop_db_first"):
            self._drop_database()

        self._create_database_if_not_exists()
        self._create_version_table_if_not_exists()

    def __mysql_connect(self, connect_using_database_name=True):
        try:
            conn = self.__mysql_driver.connect(host=self.__mysql_host, port=self.__mysql_port, user=self.__mysql_user, passwd=self.__mysql_passwd)

            conn.set_character_set(self.__mysql_encoding)

            if connect_using_database_name:
                conn.select_db(self.__mysql_db)
            return conn
        except Exception, e:
            raise Exception("could not connect to database: %s" % e)

    def __execute(self, sql, execution_log=None):
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor._defer_warnings = True
        curr_statement = None
        try:
            statments = MySQL._parse_sql_statements(sql)
            if len(sql.strip(' \t\n\r')) != 0 and len(statments) == 0:
                raise Exception("invalid sql syntax '%s'" % sql)

            for statement in statments:
                curr_statement = statement
                affected_rows = cursor.execute(statement.encode(self.__mysql_script_encoding))
                if execution_log:
                    execution_log("%s\n-- %d row(s) affected\n" % (statement, affected_rows and int(affected_rows) or 0))
            cursor.close()
            db.commit()
        except Exception, e:
            db.rollback()
            raise MigrationException("error executing migration: %s" % e, curr_statement)
        finally:
            db.close()

    def __change_db_version(self, version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None):
        if up:
            if not label_version:
                label_version = "NULL"
            else:
                label_version = "\"%s\"" % (str(label_version))
            # moving up and storing history
            sql = "insert into %s (version, label, name, sql_up, sql_down) values (\"%s\", %s, \"%s\", \"%s\", \"%s\");" % (self.__version_table, str(version), label_version, migration_file_name, sql_up.replace('"', '\\"'), sql_down.replace('"', '\\"'))
        else:
            # moving down and deleting from history
            sql = "delete from %s where version = \"%s\";" % (self.__version_table, str(version))

        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor._defer_warnings = True
        try:
            cursor.execute(sql.encode(self.__mysql_script_encoding))
            cursor.close()
            db.commit()
            if execution_log:
                execution_log("migration %s registered\n" % (migration_file_name))
        except Exception, e:
            db.rollback()
            raise MigrationException("error logging migration: %s" % e, migration_file_name)
        finally:
            db.close()

    @classmethod
    def _parse_sql_statements(cls, migration_sql):
        all_statements = []
        last_statement = ''

        for statement in migration_sql.split(';'):
            if len(last_statement) > 0:
                curr_statement = '%s;%s' % (last_statement, statement)
            else:
                curr_statement = statement

            count = Utils.count_occurrences(curr_statement)
            single_quotes = count.get("'", 0)
            double_quotes = count.get('"', 0)
            left_parenthesis = count.get('(', 0)
            right_parenthesis = count.get(')', 0)

            if single_quotes % 2 == 0 and double_quotes % 2 == 0 and left_parenthesis == right_parenthesis:
                all_statements.append(curr_statement)
                last_statement = ''
            else:
                last_statement = curr_statement

        return [s.strip() for s in all_statements if ((s.strip() != "") and (last_statement == ""))]

    def _drop_database(self):
        db = self.__mysql_connect(False)
        try:
            db.query("set foreign_key_checks=0; drop database if exists `%s`;" % self.__mysql_db)
        except Exception, e:
            raise Exception("can't drop database '%s'; \n%s" % (self.__mysql_db, str(e)))
        finally:
            db.close()

    def _create_database_if_not_exists(self):
        db = self.__mysql_connect(False)
        db.query("create database if not exists `%s`;" % self.__mysql_db)
        db.close()

    def _create_version_table_if_not_exists(self):
        # create version table
        sql = "create table if not exists %s ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default \"0\", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id));" % self.__version_table
        self.__execute(sql)

        # check if there is a register there
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select count(*) from %s;" % self.__version_table)
        count = cursor.fetchone()[0]
        cursor.close()
        db.close()

        # if there is not a version register, insert one
        if count == 0:
            sql = "insert into %s (version) values (\"0\");" % self.__version_table
            self.__execute(sql)

    def change(self, sql, new_db_version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None):
        self.__execute(sql, execution_log)
        self.__change_db_version(new_db_version, migration_file_name, sql_up, sql_down, up, execution_log, label_version)

    def get_current_schema_version(self):
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select version from %s order by id desc limit 0,1;" % self.__version_table)
        version = cursor.fetchone()[0]
        cursor.close()
        db.close()
        return version

    def get_all_schema_versions(self):
        versions = []
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select version from %s order by id;" % self.__version_table)
        all_versions = cursor.fetchall()
        for version in all_versions:
            versions.append(version[0])
        cursor.close()
        db.close()
        versions.sort()
        return versions

    def get_version_id_from_version_number(self, version):
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select id from %s where version = '%s' order by id desc;" % (self.__version_table, version))
        result = cursor.fetchone()
        _id = result and int(result[0]) or None
        cursor.close()
        db.close()
        return _id

    def get_version_number_from_label(self, label):
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select version from %s where label = '%s' order by id desc" % (self.__version_table, label))
        result = cursor.fetchone()
        version = result and result[0] or None
        cursor.close()
        db.close()
        return version

    def get_all_schema_migrations(self):
        migrations = []
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select id, version, label, name, sql_up, sql_down from %s order by id;" % self.__version_table)
        all_migrations = cursor.fetchall()
        for migration_db in all_migrations:
            migration = Migration(id = int(migration_db[0]),
                                  version = migration_db[1] and str(migration_db[1]) or None,
                                  label = migration_db[2] and str(migration_db[2]) or None,
                                  file_name = migration_db[3] and str(migration_db[3]) or None,
                                  sql_up = Migration.ensure_sql_unicode(migration_db[4], self.__mysql_script_encoding),
                                  sql_down = Migration.ensure_sql_unicode(migration_db[5], self.__mysql_script_encoding))
            migrations.append(migration)
        cursor.close()
        db.close()
        return migrations

########NEW FILE########
__FILENAME__ = oracle
import os
import re
import sys

from core import Migration
from core.exceptions import MigrationException
from helpers import Utils
from getpass import getpass
from cli import CLI

class Oracle(object):
    __re_objects = re.compile("(?ims)(?P<pre>.*?)(?P<principal>create[ \n\t\r]*(or[ \n\t\r]+replace[ \n\t\r]*)?(trigger|function|procedure|package|package body).*?)\n[ \n\t\r]*/([ \n\t\r]+(?P<pos>.*)|$)")
    __re_anonymous = re.compile("(?ims)(?P<pre>.*?)(?P<principal>(declare[ \n\t\r]+.*?)?begin.*?\n[ \n\t\r]*)/([ \n\t\r]+(?P<pos>.*)|$)")
    __re_comments_multi_line = re.compile("(?P<pre>(^|[^\"\'])[ ]*)/\*[^+][^\*]*[^/]*\*/")
    __re_comments_single_line = re.compile("(?P<pre>(^|[^\"\'])[ ]*)--[^+].*(?=\n|$)")

    def __init__(self, config=None, driver=None, get_pass=getpass, std_in=sys.stdin):
        self.__script_encoding = config.get("database_script_encoding", "utf8")
        self.__encoding = config.get("database_encoding", "American_America.UTF8")
        self.__host = config.get("database_host")
        self.__port = config.get("database_port", 1521)
        self.__user = config.get("database_user")
        self.__passwd = config.get("database_password")
        self.__db = config.get("database_name")
        self.__version_table = config.get("database_version_table")

        self.__driver = driver
        if not driver:
            import cx_Oracle
            self.__driver = cx_Oracle

        self.get_pass = get_pass
        self.std_in = std_in

        os.environ["NLS_LANG"] = self.__encoding

        if config.get("drop_db_first"):
            self._drop_database()

        self._create_database_if_not_exists()
        self._create_version_table_if_not_exists()

    def __connect(self):
        try:
            dsn = self.__db
            if self.__host:
                dsn = self.__driver.makedsn(self.__host, self.__port, self.__db)

            return self.__driver.connect(dsn=dsn, user=self.__user, password=self.__passwd)
        except Exception, e:
            raise Exception("could not connect to database: %s" % e)

    def __execute(self, sql, execution_log=None):
        conn = self.__connect()
        cursor = conn.cursor()
        curr_statement = None
        try:
            statments = Oracle._parse_sql_statements(sql)
            if len(sql.strip(' \t\n\r')) != 0 and len(statments) == 0:
                raise Exception("invalid sql syntax '%s'" % sql)

            for statement in statments:
                curr_statement = statement.encode(self.__script_encoding)
                cursor.execute(curr_statement)
                affected_rows = max(cursor.rowcount, 0)
                if execution_log:
                    execution_log("%s\n-- %d row(s) affected\n" % (curr_statement, affected_rows))
            cursor.close()
            conn.commit()
            conn.close()
        except Exception, e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise MigrationException(("error executing migration: %s" % e), curr_statement)

    def __change_db_version(self, version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None):
        params = {}
        params['version'] = version

        conn = self.__connect()
        cursor = conn.cursor()

        if up:
            # moving up and storing history
            sql = "insert into %s (id, version, label, name, sql_up, sql_down) values (%s_seq.nextval, :version, :label, :migration_file_name, :sql_up, :sql_down)" % (self.__version_table, self.__version_table)
            sql_up = sql_up and sql_up.encode(self.__script_encoding) or ""
            v_sql_up = cursor.var( self.__driver.CLOB, len(sql_up))
            v_sql_up.setvalue( 0, sql_up )
            params['sql_up'] = sql_up

            sql_down = sql_down and sql_down.encode(self.__script_encoding) or ""
            v_sql_down = cursor.var( self.__driver.CLOB, len(sql_down))
            v_sql_down.setvalue( 0, sql_down )
            params['sql_down'] = sql_down

            params['migration_file_name'] = migration_file_name
            params['label'] = label_version
        else:
            # moving down and deleting from history
            sql = "delete from %s where version = :version" % (self.__version_table)

        try:
            cursor.execute(sql.encode(self.__script_encoding), params)
            cursor.close()
            conn.commit()
            if execution_log:
                execution_log("migration %s registered\n" % (migration_file_name))
        except Exception, e:
            conn.rollback()
            raise MigrationException(("error logging migration: %s" % e), migration_file_name)
        finally:
            conn.close()

    @classmethod
    def _parse_sql_statements(self, migration_sql):
        all_statements = []
        last_statement = ''

        #remove comments
        migration_sql = Oracle.__re_comments_multi_line.sub("\g<pre>", migration_sql)
        migration_sql = Oracle.__re_comments_single_line.sub("\g<pre>", migration_sql)

        match_stmt = Oracle.__re_objects.match(migration_sql)
        if not match_stmt:
            match_stmt = Oracle.__re_anonymous.match(migration_sql)

        if match_stmt and match_stmt.re.groups > 0:
            if match_stmt.group('pre'):
                all_statements = all_statements + Oracle._parse_sql_statements(match_stmt.group('pre'))
            if match_stmt.group('principal'):
                all_statements.append(match_stmt.group('principal'))
            if match_stmt.group('pos'):
                all_statements = all_statements + Oracle._parse_sql_statements(match_stmt.group('pos'))

        else:
            for statement in migration_sql.split(';'):
                if len(last_statement) > 0:
                    curr_statement = '%s;%s' % (last_statement, statement)
                else:
                    curr_statement = statement

                count = Utils.count_occurrences(curr_statement)
                single_quotes = count.get("'", 0)
                double_quotes = count.get('"', 0)
                left_parenthesis = count.get('(', 0)
                right_parenthesis = count.get(')', 0)

                if single_quotes % 2 == 0 and double_quotes % 2 == 0 and left_parenthesis == right_parenthesis:
                    all_statements.append(curr_statement)
                    last_statement = ''
                else:
                    last_statement = curr_statement

        return [s.strip() for s in all_statements if ((s.strip() != "") and (last_statement == ""))]

    def _drop_database(self):
        sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % (self.__user.upper(), self.__user.upper(), self.__user.upper())

        conn = self.__connect()
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()

            failed_sqls = ''
            for row in rows:
                drop_sql = row[0]
                try:
                    self.__execute(drop_sql)
                except Exception, e:
                    failed_sqls = failed_sqls + "can't execute drop command '%s' in database '%s', %s\n" % (drop_sql, self.__db, str(e).strip())

            if failed_sqls != '':
                CLI.msg('\nThe following drop commands failed:\n%s' % (failed_sqls), "RED")
                CLI.msg('\nDo you want to continue anyway (y/N):', "END")
                to_continue = self.std_in.readline().strip()
                if to_continue.upper() != 'Y':
                    raise Exception("can't drop database objects for user '%s'" % (self.__user) )

        except Exception, e:
            self._verify_if_exception_is_invalid_user(e)
        finally:
            cursor.close()
            conn.close()


    def _create_database_if_not_exists(self):
        try:
            conn = self.__connect()
            conn.close()
        except Exception, e:
            self._verify_if_exception_is_invalid_user(e)

    def _verify_if_exception_is_invalid_user(self, exception):
        if 'ORA-01017' in exception.__str__():
            CLI.msg('\nPlease inform dba user/password to connect to database "%s"\nUser:' % (self.__host), "END")
            dba_user = self.std_in.readline().strip()
            passwd = self.get_pass()
            conn = self.__driver.connect(dsn=self.__host, user=dba_user, password=passwd)
            cursor = conn.cursor()
            try:
                cursor.execute("create user %s identified by %s" % (self.__user, self.__passwd))
                cursor.execute("grant connect, resource to %s" % (self.__user))
                cursor.execute("grant create public synonym to %s" % (self.__user))
                cursor.execute("grant drop public synonym to %s" % (self.__user))
            except Exception, e:
                raise Exception("check error: %s" % e)
            finally:
                cursor.close()
                conn.close()
        else:
            raise exception

    def _create_version_table_if_not_exists(self):
        # create version table
        try:
            sql = "select version from %s" % self.__version_table
            self.__execute(sql)
        except Exception:
            sql = "create table %s ( id number(11) not null, version varchar2(20) default '0' NOT NULL, label varchar2(255), name varchar2(255), sql_up clob, sql_down clob, CONSTRAINT %s_pk PRIMARY KEY (id) ENABLE)" % (self.__version_table, self.__version_table)
            self.__execute(sql)
            try:
                self.__execute("drop sequence %s_seq" % self.__version_table)
            finally:
                self.__execute("create sequence %s_seq start with 1 increment by 1 nomaxvalue" % self.__version_table)

        # check if there is a register there
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("select count(*) from %s" % self.__version_table)
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # if there is not a version register, insert one
        if count == 0:
            sql = "insert into %s (id, version) values (%s_seq.nextval, '0')" % (self.__version_table, self.__version_table)
            self.__execute(sql)

    def change(self, sql, new_db_version, migration_file_name, sql_up, sql_down, up=True, execution_log=None, label_version=None):
        self.__execute(sql, execution_log)
        self.__change_db_version(new_db_version, migration_file_name, sql_up, sql_down, up, execution_log, label_version)

    def get_current_schema_version(self):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("select version from %s order by id desc" % self.__version_table)
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return version

    def get_all_schema_versions(self):
        versions = []
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("select version from %s order by id" % self.__version_table)
        all_versions = cursor.fetchall()
        for version in all_versions:
            versions.append(version[0])
        cursor.close()
        conn.close()
        versions.sort()
        return versions

    def get_version_id_from_version_number(self, version):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("select id from %s where version = '%s' order by id desc" % (self.__version_table, version))
        result = cursor.fetchone()
        _id = result and int(result[0]) or None
        cursor.close()
        conn.close()
        return _id

    def get_version_number_from_label(self, label):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("select version from %s where label = '%s' order by id desc" % (self.__version_table, label))
        result = cursor.fetchone()
        version = result and result[0] or None
        cursor.close()
        conn.close()
        return version

    def get_all_schema_migrations(self):
        migrations = []
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("select id, version, label, name, sql_up, sql_down from %s order by id" % self.__version_table)
        all_migrations = cursor.fetchall()
        for migration_db in all_migrations:
            migration = Migration(id = int(migration_db[0]),
                                  version = migration_db[1] and str(migration_db[1]) or None,
                                  label = migration_db[2] and str(migration_db[2]) or None,
                                  file_name = migration_db[3] and str(migration_db[3]) or None,
                                  sql_up = Migration.ensure_sql_unicode(migration_db[4] and migration_db[4].read() or None, self.__script_encoding),
                                  sql_down = Migration.ensure_sql_unicode(migration_db[5] and migration_db[5].read() or None, self.__script_encoding))
            migrations.append(migration)
        cursor.close()
        conn.close()
        return migrations

########NEW FILE########
__FILENAME__ = cli_test
import unittest
from mock import patch
from StringIO import StringIO
from simple_db_migrate.cli import CLI

class CLITest(unittest.TestCase):

    def setUp(self):
        self.color = CLI.color

    def tearDown(self):
        CLI.color = self.color

    def test_it_should_define_colors_values_as_empty_strings_by_default(self):
        self.assertEqual("", CLI.color["PINK"])
        self.assertEqual("", CLI.color["BLUE"])
        self.assertEqual("", CLI.color["CYAN"])
        self.assertEqual("", CLI.color["GREEN"])
        self.assertEqual("", CLI.color["YELLOW"])
        self.assertEqual("", CLI.color["RED"])
        self.assertEqual("", CLI.color["END"])

    def test_it_should_define_colors_values_when_asked_to_show_collors(self):
        CLI.show_colors()
        self.assertEqual("\033[35m", CLI.color["PINK"])
        self.assertEqual("\033[34m", CLI.color["BLUE"])
        self.assertEqual("\033[36m", CLI.color["CYAN"])
        self.assertEqual("\033[32m", CLI.color["GREEN"])
        self.assertEqual("\033[33m", CLI.color["YELLOW"])
        self.assertEqual("\033[31m", CLI.color["RED"])
        self.assertEqual("\033[0m", CLI.color["END"])

    @patch('sys.stdout', new_callable=StringIO)
    def test_it_should_exit_with_help_options(self, stdout_mock):
        try:
            CLI.parse(["-h"])
        except SystemExit, e:
            self.assertEqual(0, e.code)
            self.assertTrue(stdout_mock.getvalue().find("Displays simple-db-migrate's version and exit") > 0)

        stdout_mock.buf = ''
        try:
            CLI.parse(["--help"])
        except SystemExit, e:
            self.assertEqual(0, e.code)

    def test_it_should_not_has_a_default_value_for_configuration_file(self):
        self.assertEqual(None, CLI.parse([])[0].config_file)

    def test_it_should_accept_configuration_file_options(self):
        self.assertEqual("file.conf", CLI.parse(["-c", "file.conf"])[0].config_file)
        self.assertEqual("file.conf", CLI.parse(["--config", "file.conf"])[0].config_file)

    def test_it_should_has_a_default_value_for_log_level(self):
        self.assertEqual(1, CLI.parse([])[0].log_level)

    def test_it_should_accept_log_level_options(self):
        self.assertEqual("log_level_value", CLI.parse(["-l", "log_level_value"])[0].log_level)
        self.assertEqual("log_level_value", CLI.parse(["--log-level", "log_level_value"])[0].log_level)

    def test_it_should_not_has_a_default_value_for_log_dir(self):
        self.assertEqual(None, CLI.parse([])[0].log_dir)

    def test_it_should_accept_log_dir_options(self):
        self.assertEqual("log_dir_value", CLI.parse(["--log-dir", "log_dir_value"])[0].log_dir)

    def test_it_should_has_a_default_value_for_force_old_migrations(self):
        self.assertEqual(False, CLI.parse([])[0].force_execute_old_migrations_versions)

    def test_it_should_accept_force_old_migrations_options(self):
        self.assertEqual(True, CLI.parse(["--force-old-migrations"])[0].force_execute_old_migrations_versions)
        self.assertEqual(True, CLI.parse(["--force-execute-old-migrations-versions"])[0].force_execute_old_migrations_versions)

    def test_it_should_has_a_default_value_for_force_files(self):
        self.assertEqual(False, CLI.parse([])[0].force_use_files_on_down)

    def test_it_should_accept_force_files_options(self):
        self.assertEqual(True, CLI.parse(["--force-files"])[0].force_use_files_on_down)
        self.assertEqual(True, CLI.parse(["--force-use-files-on-down"])[0].force_use_files_on_down)

    def test_it_should_not_has_a_default_value_for_schema_version(self):
        self.assertEqual(None, CLI.parse([])[0].schema_version)

    def test_it_should_accept_schema_version_options(self):
        self.assertEqual("schema_version_value", CLI.parse(["-m", "schema_version_value"])[0].schema_version)
        self.assertEqual("schema_version_value", CLI.parse(["--migration", "schema_version_value"])[0].schema_version)

    def test_it_should_not_has_a_default_value_for_new_migration(self):
        self.assertEqual(None, CLI.parse([])[0].new_migration)

    def test_it_should_accept_new_migration_options(self):
        self.assertEqual("new_migration_value", CLI.parse(["-n", "new_migration_value"])[0].new_migration)
        self.assertEqual("new_migration_value", CLI.parse(["--new", "new_migration_value"])[0].new_migration)
        self.assertEqual("new_migration_value", CLI.parse(["--create", "new_migration_value"])[0].new_migration)

    def test_it_should_has_a_default_value_for_paused_mode(self):
        self.assertEqual(False, CLI.parse([])[0].paused_mode)

    def test_it_should_accept_paused_mode_options(self):
        self.assertEqual(True, CLI.parse(["-p"])[0].paused_mode)
        self.assertEqual(True, CLI.parse(["--paused-mode"])[0].paused_mode)

    def test_it_should_has_a_default_value_for_simple_db_migrate_version(self):
        self.assertEqual(False, CLI.parse([])[0].simple_db_migrate_version)

    def test_it_should_accept_simple_db_migrate_version_options(self):
        self.assertEqual(True, CLI.parse(["-v"])[0].simple_db_migrate_version)
        self.assertEqual(True, CLI.parse(["--version"])[0].simple_db_migrate_version)

    def test_it_should_has_a_default_value_for_show_colors(self):
        self.assertEqual(False, CLI.parse([])[0].show_colors)

    def test_it_should_accept_show_colors_options(self):
        self.assertEqual(True, CLI.parse(["--color"])[0].show_colors)

    def test_it_should_has_a_default_value_for_drop_db_first(self):
        self.assertEqual(False, CLI.parse([])[0].drop_db_first)

    def test_it_should_accept_drop_db_first_options(self):
        self.assertEqual(True, CLI.parse(["--drop"])[0].drop_db_first)
        self.assertEqual(True, CLI.parse(["--drop-database-first"])[0].drop_db_first)

    def test_it_should_has_a_default_value_for_show_sql(self):
        self.assertEqual(False, CLI.parse([])[0].show_sql)

    def test_it_should_accept_show_sql_options(self):
        self.assertEqual(True, CLI.parse(["--show-sql"])[0].show_sql)

    def test_it_should_has_a_default_value_for_show_sql_only(self):
        self.assertEqual(False, CLI.parse([])[0].show_sql_only)

    def test_it_should_accept_show_sql_only_options(self):
        self.assertEqual(True, CLI.parse(["--show-sql-only"])[0].show_sql_only)

    def test_it_should_not_has_a_default_value_for_label_version(self):
        self.assertEqual(None, CLI.parse([])[0].label_version)

    def test_it_should_accept_label_version_options(self):
        self.assertEqual("label_version_value", CLI.parse(["--label", "label_version_value"])[0].label_version)

    def test_it_should_not_has_a_default_value_for_password(self):
        self.assertEqual(None, CLI.parse([])[0].password)

    def test_it_should_accept_password_options(self):
        self.assertEqual("password_value", CLI.parse(["--password", "password_value"])[0].password)

    def test_it_should_has_a_default_value_for_environment(self):
        self.assertEqual("", CLI.parse([])[0].environment)

    def test_it_should_accept_environment_options(self):
        self.assertEqual("environment_value", CLI.parse(["--env", "environment_value"])[0].environment)
        self.assertEqual("environment_value", CLI.parse(["--environment", "environment_value"])[0].environment)

    def test_it_should_has_a_default_value_for_utc_timestamp(self):
        self.assertEqual(False, CLI.parse([])[0].utc_timestamp)

    def test_it_should_accept_utc_timestamp_options(self):
        self.assertEqual(True, CLI.parse(["--utc-timestamp"])[0].utc_timestamp)

    def test_it_should_not_has_a_default_value_for_database_engine(self):
        self.assertEqual(None, CLI.parse([])[0].database_engine)

    def test_it_should_accept_database_engine_options(self):
        self.assertEqual("engine_value", CLI.parse(["--db-engine", "engine_value"])[0].database_engine)

    def test_it_should_not_has_a_default_value_for_database_version_table(self):
        self.assertEqual(None, CLI.parse([])[0].database_version_table)

    def test_it_should_accept_database_version_table_options(self):
        self.assertEqual("version_table_value", CLI.parse(["--db-version-table", "version_table_value"])[0].database_version_table)

    def test_it_should_not_has_a_default_value_for_database_user(self):
        self.assertEqual(None, CLI.parse([])[0].database_user)

    def test_it_should_accept_database_user_options(self):
        self.assertEqual("user_value", CLI.parse(["--db-user", "user_value"])[0].database_user)

    def test_it_should_not_has_a_default_value_for_database_password(self):
        self.assertEqual(None, CLI.parse([])[0].database_password)

    def test_it_should_accept_database_password_options(self):
        self.assertEqual("password_value", CLI.parse(["--db-password", "password_value"])[0].database_password)

    def test_it_should_not_has_a_default_value_for_database_host(self):
        self.assertEqual(None, CLI.parse([])[0].database_host)

    def test_it_should_accept_database_host_options(self):
        self.assertEqual("host_value", CLI.parse(["--db-host", "host_value"])[0].database_host)

    def test_it_should_not_has_a_default_value_for_database_port(self):
        self.assertEqual(None, CLI.parse([])[0].database_port)

    def test_it_should_accept_database_port_options(self):
        self.assertEqual(42, CLI.parse(["--db-port", "42"])[0].database_port)

    def test_it_should_not_has_a_default_value_for_database_name(self):
        self.assertEqual(None, CLI.parse([])[0].database_name)

    def test_it_should_accept_database_name_options(self):
        self.assertEqual("name_value", CLI.parse(["--db-name", "name_value"])[0].database_name)

    def test_it_should_not_has_a_default_value_for_migrations_dir(self):
        self.assertEqual(None, CLI.parse([])[0].database_migrations_dir)

    def test_it_should_accept_migrations_dir_options(self):
        self.assertEqual(".:../:/tmp", CLI.parse(["--db-migrations-dir", ".:../:/tmp"])[0].database_migrations_dir)

    @patch('sys.stdout', new_callable=StringIO)
    def test_it_should_call_print_statment_with_the_given_message(self, stdout_mock):
        CLI.msg("message to print")
        self.assertEqual("message to print\n", stdout_mock.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_it_should_call_print_statment_with_the_given_message_and_color_codes_when_colors_are_on(self, stdout_mock):
        CLI.show_colors()
        CLI.msg("message to print")
        self.assertEqual("\x1b[36mmessage to print\x1b[0m\n", stdout_mock.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_it_should_use_color_code_to_the_specified_color(self, stdout_mock):
        CLI.show_colors()
        CLI.msg("message to print", "RED")
        self.assertEqual("\x1b[31mmessage to print\x1b[0m\n", stdout_mock.getvalue())

    @patch('simple_db_migrate.cli.CLI.msg')
    def test_it_should_show_error_message_and_exit(self, msg_mock):
        try:
            CLI.error_and_exit("error test message, dont mind about it :)")
            self.fail("it should not get here")
        except:
            pass
        msg_mock.assert_called_with("[ERROR] error test message, dont mind about it :)\n", "RED")

    @patch('simple_db_migrate.cli.CLI.msg')
    def test_it_should_show_info_message_and_exit(self, msg_mock):
        try:
            CLI.info_and_exit("info test message, dont mind about it :)")
            self.fail("it should not get here")
        except:
            pass
        msg_mock.assert_called_with("info test message, dont mind about it :)\n", "BLUE")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = config_test
import os
import unittest
from simple_db_migrate.config import Config, FileConfig

class ConfigTest(unittest.TestCase):

    def test_it_should_parse_migrations_dir_with_one_relative_dir(self):
        dirs = Config._parse_migrations_dir('.')
        self.assertEqual(1, len(dirs))
        self.assertEqual(os.path.abspath('.'), dirs[0])

    def test_it_should_parse_migrations_dir_with_multiple_relative_dirs(self):
        dirs = Config._parse_migrations_dir('test:migrations:./a/relative/path:another/path')
        self.assertEqual(4, len(dirs))
        self.assertEqual(os.path.abspath('test'), dirs[0])
        self.assertEqual(os.path.abspath('migrations'), dirs[1])
        self.assertEqual(os.path.abspath('./a/relative/path'), dirs[2])
        self.assertEqual(os.path.abspath('another/path'), dirs[3])

    def test_it_should_parse_migrations_dir_with_one_absolute_dir(self):
        dirs = Config._parse_migrations_dir(os.path.abspath('.'))
        self.assertEqual(1, len(dirs))
        self.assertEqual(os.path.abspath('.'), dirs[0])

    def test_it_should_parse_migrations_dir_with_multiple_absolute_dirs(self):
        dirs = Config._parse_migrations_dir('%s:%s:%s:%s' % (
                os.path.abspath('test'), os.path.abspath('migrations'),
                os.path.abspath('./a/relative/path'), os.path.abspath('another/path'))
        )
        self.assertEqual(4, len(dirs))
        self.assertEqual(os.path.abspath('test'), dirs[0])
        self.assertEqual(os.path.abspath('migrations'), dirs[1])
        self.assertEqual(os.path.abspath('./a/relative/path'), dirs[2])
        self.assertEqual(os.path.abspath('another/path'), dirs[3])

    def test_it_should_parse_migrations_dir_with_mixed_relative_and_absolute_dirs(self):
        dirs = Config._parse_migrations_dir('%s:%s:%s:%s' % ('/tmp/test', '.', './a/relative/path', os.path.abspath('another/path')))
        self.assertEqual(4, len(dirs))
        self.assertEqual('/tmp/test', dirs[0])
        self.assertEqual(os.path.abspath('.'), dirs[1])
        self.assertEqual(os.path.abspath('./a/relative/path'), dirs[2])
        self.assertEqual(os.path.abspath('another/path'), dirs[3])

    def test_it_should_parse_migrations_dir_with_relative_dirs_using_config_dir_parameter_as_base_path(self):
        dirs = Config._parse_migrations_dir(
                '%s:%s:%s:%s' % ('/tmp/test', '.', './a/relative/path', os.path.abspath('another/path')),
                config_dir='/base/path_to_relative_dirs'
        )
        self.assertEqual(4, len(dirs))
        self.assertEqual('/tmp/test', dirs[0])
        self.assertEqual('/base/path_to_relative_dirs', dirs[1])
        self.assertEqual('/base/path_to_relative_dirs/a/relative/path', dirs[2])
        self.assertEqual(os.path.abspath('another/path'), dirs[3])


    def test_it_should_return_value_from_a_dict(self):
        _dict = {"some_key": "some_value"}
        self.assertEqual("some_value", Config._get(_dict, "some_key"))

    def test_it_should_return_value_from_a_dict_even_if_a_default_value_given(self):
        _dict = {"some_key": "some_value"}
        self.assertEqual("some_value", Config._get(_dict, "some_key", "default_value"))

    def test_it_should_return_default_value_for_an_none_dict_value(self):
        _dict = {"some_key": None}
        self.assertEqual("default_value", Config._get(_dict, "some_key", "default_value"))

    def test_it_should_return_default_value_for_an_inexistent_dict_value(self):
        _dict = {"some_key": "some_value"}
        self.assertEqual("default_value", Config._get(_dict, "ANOTHER_KEY", "default_value"))

    def test_it_should_raise_exception_for_an_inexistent_dict_value_without_specify_a_default_value(self):
        _dict = {"some_key": "some_value"}
        try:
            Config._get(_dict, "ANOTHER_KEY")
        except Exception, e:
            self.assertEqual("invalid key ('ANOTHER_KEY')", str(e))

    def test_it_should_accept_non_empty_string_and_false_as_default_value(self):
        _dict = {"some_key": "some_value"}
        self.assertEqual(None, Config._get(_dict,"ANOTHER_KEY", None))
        self.assertEqual("", Config._get(_dict,"ANOTHER_KEY", ""))
        self.assertEqual(False, Config._get(_dict,"ANOTHER_KEY", False))

    def test_it_should_save_config_values(self):
        config = Config()
        initial = str(config)
        config.put("some_key", "some_value")
        self.assertNotEqual(initial, str(config))

    def test_it_should_not_update_saved_config_values(self):
        config = Config()
        config.put("some_key", "some_value")
        try:
            config.put("some_key", "another_value")
        except Exception, e:
            self.assertEqual("the configuration key 'some_key' already exists and you cannot override any configuration", str(e))

    def test_it_should_remove_saved_config_values(self):
        config = Config()
        config.put("some_key", "some_value")
        initial = str(config)
        config.remove("some_key")
        self.assertNotEqual(initial, str(config))

    def test_it_should_raise_exception_when_removing_an_inexistent_config_value(self):
        config = Config()
        config.put("some_key", "some_value")
        try:
            config.remove("ANOTHER_KEY")
        except Exception, e:
            self.assertEqual("invalid configuration key ('another_key')", str(e))

    def test_it_should_return_previous_saved_config_values(self):
        config = Config()
        config.put("some_key", "some_value")
        self.assertEqual("some_value", config.get("some_key"))

    def test_it_should_accept_initial_values_as_configuration(self):
        config = Config({"some_key": "some_value"})
        self.assertEqual("some_value", config.get("some_key"))

    def test_it_should_return_default_value_for_an_inexistent_config_value(self):
        config = Config()
        config.put("some_key", "some_value")
        self.assertEqual("default_value", config.get("another_key", "default_value"))

    def test_it_should_raise_exception_for_an_inexistent_config_value_without_specify_a_default_value(self):
        config = Config()
        config.put("some_key", "some_value")
        try:
            config.get("ANOTHER_KEY")
        except Exception, e:
            self.assertEqual("invalid key ('another_key')", str(e))

    def test_it_should_accept_non_empty_string_and_false_as_default_value(self):
        config = Config()
        config.put("some_key", "some_value")
        self.assertEqual(None, config.get("ANOTHER_KEY", None))
        self.assertEqual("", config.get("ANOTHER_KEY", ""))
        self.assertEqual(False, config.get("ANOTHER_KEY", False))

    def test_it_should_update_value_to_a_non_existing_key(self):
        config = Config()
        config.update("some_key", "some_value")
        self.assertEqual("some_value", config.get("some_key"))

    def test_it_should_update_value_to_a_existing_key(self):
        config = Config()
        config.put("some_key", "original_value")
        config.update("some_key", "some_value")
        self.assertEqual("some_value", config.get("some_key"))

    def test_it_should_update_value_to_a_existing_key_keeping_original_value_if_new_value_is_none_false_or_empty_string(self):
        config = Config()
        config.put("some_key", "original_value")
        config.update("some_key", None)
        self.assertEqual("original_value", config.get("some_key"))
        config.update("some_key", False)
        self.assertEqual("original_value", config.get("some_key"))
        config.update("some_key", "")
        self.assertEqual("original_value", config.get("some_key"))

    def test_it_should_transform_keys_to_lower_case(self):
        config = Config()
        config.put("sOmE_kEy", "original_value")
        self.assertEqual("original_value", config.get("SoMe_KeY"))
        config.update("sOMe_kEy", "new_value")
        self.assertEqual("new_value", config.get("some_KEY"))
        config.remove("SOME_KEY")
        self.assertRaises(Exception, config.get, "sOMe_KEY")

    def test_it_should_transform_keys_to_lower_case_on_init(self):
        config = Config({"sOmE_kEy": "original_value"})
        self.assertEqual(["some_key"] ,config._config.keys())

class FileConfigTest(unittest.TestCase):

    def setUp(self):
        config_file = '''
DATABASE_HOST = 'localhost'
DATABASE_USER = 'root'
DATABASE_PASSWORD = ''
DATABASE_NAME = 'migration_example'
ENV1_DATABASE_NAME = 'migration_example_env1'
UTC_TIMESTAMP = True
DATABASE_ANY_CUSTOM_VARIABLE = 'Some Value'
SOME_ENV_DATABASE_ANY_CUSTOM_VARIABLE = 'Other Value'
DATABASE_OTHER_CUSTOM_VARIABLE = 'Value'
'''
        f = open('sample.conf', 'w')
        f.write("%s\nDATABASE_MIGRATIONS_DIR = 'example'" % config_file)
        f.close()

        f = open('sample2.conf', 'w')
        f.write("%s" % config_file)
        f.close()

        f = open('sample.py', 'w')
        f.write('import os\n')
        f.write("%s\nDATABASE_MIGRATIONS_DIR = 'example'" % config_file)
        f.close()

    def tearDown(self):
        os.remove('sample.conf')
        os.remove('sample2.conf')
        os.remove('sample.py')

    def test_it_should_extend_from_config_class(self):
        config = FileConfig(os.path.abspath('sample.conf'))
        self.assertTrue(isinstance(config, Config))

    def test_it_should_read_config_file(self):
        config_path = os.path.abspath('sample.conf')
        config = FileConfig(config_path)
        self.assertEquals(config.get('database_host'), 'localhost')
        self.assertEquals(config.get('database_user'), 'root')
        self.assertEquals(config.get('database_password'), '')
        self.assertEquals(config.get('database_name'), 'migration_example')
        self.assertEquals(config.get("database_migrations_dir"), [os.path.abspath('example')])
        self.assertEquals(config.get('utc_timestamp'), True)

    def test_it_should_use_configuration_by_environment(self):
        config_path = os.path.abspath('sample.conf')
        config = FileConfig(config_path, "env1")
        self.assertEquals('migration_example_env1', config.get('database_name'))
        self.assertEquals('root', config.get('database_user'))

    def test_it_should_stop_execution_when_an_invalid_key_is_requested(self):
        config_path = os.path.abspath('sample.conf')
        config = FileConfig(config_path)
        try:
            config.get('invalid_config')
            self.fail('it should not pass here')
        except Exception, e:
            self.assertEqual("invalid key ('invalid_config')", str(e))

    def test_it_should_get_any_database_custom_variable(self):
        config_path = os.path.abspath('sample.conf')
        config = FileConfig(config_path)
        self.assertEqual('Some Value', config.get('database_any_custom_variable'))

    def test_it_should_get_any_database_custom_variable_using_environment(self):
        config_path = os.path.abspath('sample.conf')
        config = FileConfig(config_path, 'some_env')
        self.assertEqual('Other Value', config.get('database_any_custom_variable'))
        self.assertEqual('Value', config.get('database_other_custom_variable'))

    def test_it_should_accept_a_configuration_file_without_migrations_dir_key(self):
        config_path = os.path.abspath('sample2.conf')
        config = FileConfig(config_path)
        self.assertEqual("no_migrations_dir_key", config.get('migrations_dir', "no_migrations_dir_key"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = core_test
# coding: utf-8
import os
import unittest
from mock import patch, Mock
from simple_db_migrate.core import Migration
from simple_db_migrate.core import SimpleDBMigrate
from tests import BaseTest, create_file, create_migration_file, delete_files, create_config

class SimpleDBMigrateTest(BaseTest):

    def setUp(self):
        super(SimpleDBMigrateTest, self).setUp()
        if not os.path.exists(os.path.abspath('migrations')):
            os.mkdir(os.path.abspath('migrations'))
        self.config = create_config(migrations_dir='.:migrations')
        self.test_migration_files = []

        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115100_01_test_migration.migration', 'foo', 'bar')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('migrations/20090214115200_02_test_migration.migration', 'foo', 'bar')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115300_03_test_migration.migration', 'foo', 'bar')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115400_04_test_migration.migration', 'foo', 'bar')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('migrations/20090214115500_05_test_migration.migration', 'foo', 'bar')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('migrations/20090214115600_06_test_migration.migration', 'foo', 'bar')))

    def test_it_should_use_migrations_dir_from_configuration(self):
        db_migrate = SimpleDBMigrate(self.config)
        self.assertEqual(self.config.get("database_migrations_dir"), db_migrate._migrations_dir)

    def test_it_should_use_script_encoding_from_configuration(self):
        db_migrate = SimpleDBMigrate(self.config)
        self.assertEqual(self.config.get('database_script_encoding'), db_migrate._script_encoding)

    def test_it_should_use_utf8_as_default_script_encoding_from_configuration(self):
        self.config.remove('database_script_encoding')
        db_migrate = SimpleDBMigrate(self.config)
        self.assertEqual('utf-8', db_migrate._script_encoding)

    def test_it_should_get_all_migrations_in_dir(self):
        db_migrate = SimpleDBMigrate(self.config)
        migrations = db_migrate.get_all_migrations()
        self.assertNotEqual(None, migrations)
        self.assertEqual(len(self.test_migration_files), len(migrations))
        for migration in migrations:
            self.assertTrue(migration.abspath in self.test_migration_files)

    @patch('simple_db_migrate.core.Migration.is_file_name_valid')
    def test_it_should_get_only_valid_migrations_in_dir(self, is_file_name_valid_mock):
        def side_effect(args):
            return args != '20090214115100_01_test_migration.migration'
        is_file_name_valid_mock.side_effect = side_effect

        db_migrate = SimpleDBMigrate(self.config)
        migrations = db_migrate.get_all_migrations()
        self.assertEqual(len(self.test_migration_files) - 1, len(migrations))
        for migration in migrations:
            self.assertTrue(migration.abspath in self.test_migration_files)
            self.assertFalse(migration.file_name == '20090214115100_01_test_migration.migration')

        self.assertEqual((len(self.test_migration_files) * 2) - 1, is_file_name_valid_mock.call_count)

    @patch('simple_db_migrate.core.Migration.is_file_name_valid', return_value=True)
    def test_it_should_not_read_files_again_on_subsequent_calls(self, is_file_name_valid_mock):
        db_migrate = SimpleDBMigrate(self.config)
        db_migrate.get_all_migrations()
        self.assertEqual((len(self.test_migration_files) * 2), is_file_name_valid_mock.call_count)

        #make the second call
        db_migrate.get_all_migrations()
        self.assertEqual((len(self.test_migration_files) * 2), is_file_name_valid_mock.call_count)

    def test_it_should_raise_error_if_has_an_invalid_dir_on_migrations_dir_list(self):
        self.config.update("database_migrations_dir", ['invalid_path_it_does_not_exist'])
        db_migrate = SimpleDBMigrate(self.config)
        self.assertRaisesWithMessage(Exception, "directory not found ('%s')" % os.path.abspath('invalid_path_it_does_not_exist'), db_migrate.get_all_migrations)

    @patch('simple_db_migrate.core.Migration.is_file_name_valid', return_value=False)
    def test_it_should_raise_error_if_do_not_have_any_valid_migration(self, is_file_name_valid_mock):
        db_migrate = SimpleDBMigrate(self.config)
        self.assertRaisesWithMessage(Exception, "no migration files found", db_migrate.get_all_migrations)

    def test_it_should_get_all_migration_versions_available(self):
        db_migrate = SimpleDBMigrate(self.config)
        migrations = db_migrate.get_all_migrations()
        expected_versions = []
        for migration in migrations:
            expected_versions.append(migration.version)

        all_versions = db_migrate.get_all_migration_versions()

        self.assertEqual(len(all_versions), len(expected_versions))
        for version in all_versions:
            self.assertTrue(version in expected_versions)

    @patch('simple_db_migrate.core.SimpleDBMigrate.get_all_migrations', return_value=[])
    def test_it_should_use_get_all_migrations_method_to_get_all_migration_versions_available(self, get_all_migrations_mock):
        db_migrate = SimpleDBMigrate(self.config)
        db_migrate.get_all_migration_versions()
        self.assertEqual(1, get_all_migrations_mock.call_count)

    def test_it_should_get_all_migration_versions_up_to_a_version(self):
        db_migrate = SimpleDBMigrate(self.config)
        migration_versions = db_migrate.get_all_migration_versions_up_to('20090214115200')
        self.assertEqual(1, len(migration_versions))
        self.assertEqual('20090214115100', migration_versions[0])

    @patch('simple_db_migrate.core.SimpleDBMigrate.get_all_migration_versions', return_value=[])
    def test_it_should_use_get_all_migrations_versions_method_to_get_all_migration_versions_up_to_a_version(self, get_all_migration_versions_mock):
        db_migrate = SimpleDBMigrate(self.config)
        db_migrate.get_all_migration_versions_up_to('20090214115200')
        self.assertEqual(1, get_all_migration_versions_mock.call_count)

    def test_it_should_check_if_migration_version_exists(self):
        db_migrate = SimpleDBMigrate(self.config)
        self.assertTrue(db_migrate.check_if_version_exists('20090214115100'))
        self.assertFalse(db_migrate.check_if_version_exists('19000101000000'))

    @patch('simple_db_migrate.core.SimpleDBMigrate.get_all_migration_versions', return_value=[])
    def test_it_should_use_get_all_migrations_versions_method_to_check_if_migration_version_exists(self, get_all_migration_versions_mock):
        db_migrate = SimpleDBMigrate(self.config)
        db_migrate.check_if_version_exists('20090214115100')
        self.assertEqual(1, get_all_migration_versions_mock.call_count)

    def test_it_should_not_inform_that_migration_version_exists_just_matching_the_beggining_of_version_number(self):
        db_migrate = SimpleDBMigrate(self.config)
        self.assertFalse(db_migrate.check_if_version_exists('2009'))

    def test_it_should_get_the_latest_version_available(self):
        db_migrate = SimpleDBMigrate(self.config)
        self.assertEqual('20090214115600', db_migrate.latest_version_available())

    @patch('simple_db_migrate.core.SimpleDBMigrate.get_all_migrations', return_value=[Mock(version='xpto')])
    def test_it_should_use_get_all_migrations_versions_method_to_get_the_latest_version_available(self, get_all_migrations_mock):
        db_migrate = SimpleDBMigrate(self.config)
        db_migrate.latest_version_available()
        self.assertEqual(1, get_all_migrations_mock.call_count)

    def test_it_should_get_migration_from_version_number(self):
        db_migrate = SimpleDBMigrate(self.config)
        migration = db_migrate.get_migration_from_version_number('20090214115100')
        self.assertEqual('20090214115100', migration.version)
        self.assertEqual('20090214115100_01_test_migration.migration', migration.file_name)

    def test_it_should_not_get_migration_from_invalid_version_number(self):
        db_migrate = SimpleDBMigrate(self.config)
        migration = db_migrate.get_migration_from_version_number('***invalid***')
        self.assertEqual(None, migration)

    @patch('simple_db_migrate.core.SimpleDBMigrate.get_all_migrations', return_value=[])
    def test_it_should_use_get_all_migrations_versions_method_to_get_migration_from_version_number(self, get_all_migrations_mock):
        db_migrate = SimpleDBMigrate(self.config)
        db_migrate.get_migration_from_version_number('20090214115100')
        self.assertEqual(1, get_all_migrations_mock.call_count)

class MigrationTest(BaseTest):
    def setUp(self):
        create_migration_file('20090214120600_example_file_name_test_migration.migration', sql_up='xxx', sql_down='yyy')
        create_migration_file('20090727104700_test_migration.migration', sql_up='xxx', sql_down='yyy')
        create_migration_file('20090727141400_test_migration.migration', sql_up='xxx', sql_down='yyy')
        create_migration_file('20090727141503_test_migration.migration', sql_up='xxx', sql_down='yyy')
        create_migration_file('20090727141505_01_test_migration.migration', sql_up='xxx', sql_down='yyy')
        create_migration_file('20090727141505_02_test_migration.migration', sql_up='xxx', sql_down='yyy')
        create_migration_file('20090727113900_empty_sql_up_test_migration.migration', sql_up='', sql_down='zzz')
        create_migration_file('20090727113900_empty_sql_down_test_migration.migration', sql_up='zzz', sql_down='')
        create_file('20090727114700_empty_file_test_migration.migration')
        create_file('20090727114700_without_sql_down_test_migration.migration', 'SQL_UP=""')
        create_file('20090727114700_without_sql_up_test_migration.migration', 'SQL_DOWN=""')

    def tearDown(self):
        delete_files('*test_migration.migration')

    def test_it_should_get_migration_version_from_file(self):
        migration = Migration('20090214120600_example_file_name_test_migration.migration')
        self.assertEqual('20090214120600', migration.version)

    def test_it_should_get_basic_properties_when_path_is_relative1(self):
        migration = Migration(file='20090727104700_test_migration.migration')
        self.assertEqual('20090727104700', migration.version)
        self.assertEqual('20090727104700_test_migration.migration', migration.file_name)
        self.assertEqual(os.path.abspath('./20090727104700_test_migration.migration'), migration.abspath)

    def test_it_should_get_basic_properties_when_path_is_relative2(self):
        migration = Migration(file='./20090727104700_test_migration.migration')
        self.assertEqual('20090727104700', migration.version)
        self.assertEqual('20090727104700_test_migration.migration', migration.file_name)
        self.assertEqual(os.path.abspath('./20090727104700_test_migration.migration'), migration.abspath)

    def test_it_should_get_basic_properties_when_path_is_relative3(self):
        here = os.path.dirname(os.path.relpath(__file__))
        migration = Migration(file='%s/../20090727104700_test_migration.migration' % here)
        self.assertEqual('20090727104700', migration.version)
        self.assertEqual('20090727104700_test_migration.migration', migration.file_name)
        self.assertEqual(os.path.abspath('./20090727104700_test_migration.migration'), migration.abspath)

    def test_it_should_get_basic_properties_when_path_is_absolute(self):
        migration = Migration(file=os.path.abspath('./20090727104700_test_migration.migration'))
        self.assertEqual('20090727104700', migration.version)
        self.assertEqual('20090727104700_test_migration.migration', migration.file_name)
        self.assertEqual(os.path.abspath('./20090727104700_test_migration.migration'), migration.abspath)

    def test_it_should_get_sql_up_and_down(self):
        migration = Migration(file='20090727104700_test_migration.migration')
        self.assertEqual(migration.sql_up, 'xxx')
        self.assertEqual(migration.sql_down, 'yyy')

    def test_it_should_get_sql_command_containing_unicode_characters(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='SQL_UP=u"some sql command"\nSQL_DOWN=u"other sql command"')
        migration = Migration(file_name)
        self.assertEqual(u"some sql command", migration.sql_up)
        self.assertEqual(u"other sql command", migration.sql_down)

    def test_it_should_get_sql_command_containing_unicode_characters_and_python_code(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='import os\nSQL_UP=u"some sql command %s" % os.path.abspath(\'.\')\nSQL_DOWN=u"other sql command %s" % os.path.abspath(\'.\')')
        migration = Migration(file_name)
        self.assertEqual(u"some sql command %s" % os.path.abspath('.'), migration.sql_up)
        self.assertEqual(u"other sql command %s" % os.path.abspath('.'), migration.sql_down)

    def test_it_should_get_sql_command_containing_unicode_characters_and_python_code_without_scope(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='SQL_UP=u"some sql command %s" % os.path.abspath(\'.\')\nSQL_DOWN=u"other sql command %s" % os.path.abspath(\'.\')')
        migration = Migration(file_name)
        self.assertEqual(u"some sql command %s" % os.path.abspath('.'), migration.sql_up)
        self.assertEqual(u"other sql command %s" % os.path.abspath('.'), migration.sql_down)

    def test_it_should_get_sql_command_containing_non_ascii_characters(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='SQL_UP=u"some sql command ç"\nSQL_DOWN=u"other sql command ã"'.decode('utf-8'))
        migration = Migration(file_name)
        self.assertEqual(u"some sql command ç", migration.sql_up)
        self.assertEqual(u"other sql command ã", migration.sql_down)

    def test_it_should_get_sql_command_containing_non_ascii_characters_and_python_code(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='import os\nSQL_UP=u"some sql command ç %s" % os.path.abspath(\'.\')\nSQL_DOWN=u"other sql command ã %s" % os.path.abspath(\'.\')'.decode('utf-8')   )
        migration = Migration(file_name)
        self.assertEqual(u"some sql command ç %s" % os.path.abspath('.'), migration.sql_up)
        self.assertEqual(u"other sql command ã %s" % os.path.abspath('.'), migration.sql_down)

    def test_it_should_get_sql_command_containing_non_ascii_characters_and_python_code_without_scope(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='SQL_UP=u"some sql command ç %s" % os.path.abspath(\'.\')\nSQL_DOWN=u"other sql command ã %s" % os.path.abspath(\'.\')'.decode('utf-8'))
        migration = Migration(file_name)
        self.assertEqual(u"some sql command ç %s" % os.path.abspath('.'), migration.sql_up)
        self.assertEqual(u"other sql command ã %s" % os.path.abspath('.'), migration.sql_down)

    def test_it_should_get_sql_command_containing_non_ascii_characters_with_non_utf8_encoding(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='SQL_UP=u"some sql command ç"\nSQL_DOWN=u"other sql command ã"'.decode('iso8859-1'), encoding='iso8859-1')
        migration = Migration(file_name, script_encoding='iso8859-1')
        self.assertEqual(u"some sql command \xc3\xa7", migration.sql_up)
        self.assertEqual(u"other sql command \xc3\xa3", migration.sql_down)

    def test_it_should_get_sql_command_containing_non_ascii_characters_and_python_code_with_non_utf8_encoding(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='import os\nSQL_UP=u"some sql command ç %s" % os.path.abspath(\'.\')\nSQL_DOWN=u"other sql command ã %s" % os.path.abspath(\'.\')'.decode('iso8859-1'), encoding='iso8859-1')
        migration = Migration(file_name, script_encoding='iso8859-1')
        self.assertEqual(u"some sql command \xc3\xa7 %s" % os.path.abspath('.'), migration.sql_up)
        self.assertEqual(u"other sql command \xc3\xa3 %s" % os.path.abspath('.'), migration.sql_down)

    def test_it_should_get_sql_command_containing_non_ascii_characters_and_python_code_without_scope_with_non_utf8_encoding(self):
        file_name = '20090508155742_test_migration.migration'
        create_file(file_name, content='SQL_UP=u"some sql command ç %s" % os.path.abspath(\'.\')\nSQL_DOWN=u"other sql command ã %s" % os.path.abspath(\'.\')'.decode('iso8859-1'), encoding='iso8859-1')
        migration = Migration(file_name, script_encoding='iso8859-1')
        self.assertEqual(u"some sql command \xc3\xa7 %s" % os.path.abspath('.'), migration.sql_up)
        self.assertEqual(u"other sql command \xc3\xa3 %s" % os.path.abspath('.'), migration.sql_down)

    def test_it_should_raise_exception_when_migration_commands_are_empty(self):
        self.assertRaisesWithMessage(Exception, "migration command 'SQL_UP' is empty (%s)" % os.path.abspath('20090727113900_empty_sql_up_test_migration.migration'), Migration, '20090727113900_empty_sql_up_test_migration.migration')
        self.assertRaisesWithMessage(Exception, "migration command 'SQL_DOWN' is empty (%s)" % os.path.abspath('20090727113900_empty_sql_down_test_migration.migration'), Migration, '20090727113900_empty_sql_down_test_migration.migration')

    def test_it_should_raise_exception_when_migration_file_is_empty(self):
        self.assertRaisesWithMessage(Exception, "migration file is incorrect; it does not define 'SQL_UP' or 'SQL_DOWN' (%s)" % os.path.abspath('20090727114700_empty_file_test_migration.migration'), Migration, '20090727114700_empty_file_test_migration.migration')

    def test_it_should_raise_exception_when_migration_file_do_not_have_sql_up_constant(self):
        self.assertRaisesWithMessage(Exception, "migration file is incorrect; it does not define 'SQL_UP' or 'SQL_DOWN' (%s)" % os.path.abspath('20090727114700_without_sql_up_test_migration.migration'), Migration, '20090727114700_without_sql_up_test_migration.migration')

    def test_it_should_raise_exception_when_migration_file_do_not_have_sql_down_constant(self):
        self.assertRaisesWithMessage(Exception, "migration file is incorrect; it does not define 'SQL_UP' or 'SQL_DOWN' (%s)" % os.path.abspath('20090727114700_without_sql_down_test_migration.migration'), Migration, '20090727114700_without_sql_down_test_migration.migration')

    def test_it_should_compare_to_migration_versions_and_tell_which_is_newer(self):
        m1 = Migration('20090727104700_test_migration.migration')
        m2 = Migration('20090727141400_test_migration.migration')
        m3 = Migration('20090727141503_test_migration.migration')
        m4 = Migration('20090727141505_01_test_migration.migration')
        m5 = Migration('20090727141505_02_test_migration.migration')

        self.assertEqual(-1, m1.compare_to(m2))
        self.assertEqual(-1, m2.compare_to(m3))
        self.assertEqual(-1, m1.compare_to(m3))
        self.assertEqual(-1, m4.compare_to(m5))

        self.assertEqual(1, m2.compare_to(m1))
        self.assertEqual(1, m3.compare_to(m2))
        self.assertEqual(1, m3.compare_to(m1))
        self.assertEqual(1, m5.compare_to(m4))

        self.assertEqual(0, m1.compare_to(m1))
        self.assertEqual(0, m2.compare_to(m2))
        self.assertEqual(0, m3.compare_to(m3))
        self.assertEqual(0, m4.compare_to(m4))
        self.assertEqual(0, m5.compare_to(m5))

    def test_it_should_raise_exception_when_file_does_not_exist(self):
        try:
            Migration('20090727104700_this_file_does_not_exist.migration')
        except Exception, e:
            self.assertEqual('migration file does not exist (20090727104700_this_file_does_not_exist.migration)', str(e))

    @patch('simple_db_migrate.core.Migration.is_file_name_valid', return_value=False)
    def test_it_should_raise_exception_when_file_name_is_invalid(self, is_file_name_valid_mock):
        self.assertRaisesWithMessage(Exception, 'invalid migration file name (simple-db-migrate.conf)', Migration, 'simple-db-migrate.conf')
        is_file_name_valid_mock.assert_called_with('simple-db-migrate.conf')

    def test_it_should_validate_if_filename_has_only_alphanumeric_chars_and_migration_extension(self):
        self.assertTrue(Migration.is_file_name_valid('20090214120600_valid_migration_file_name.migration'))
        self.assertFalse(Migration.is_file_name_valid('200902141206000_valid_migration_file_name.migration'))
        self.assertFalse(Migration.is_file_name_valid('20090214120600_invalid_migration_file_name.migration~'))
        self.assertFalse(Migration.is_file_name_valid('simple-db-migrate.conf'))
        self.assertFalse(Migration.is_file_name_valid('abra.cadabra'))
        self.assertFalse(Migration.is_file_name_valid('randomrandomrandom.migration'))
        self.assertFalse(Migration.is_file_name_valid('21420101000000-wrong-separators.migration'))
        self.assertFalse(Migration.is_file_name_valid('2009021401_old_file_name_style.migration'))
        self.assertFalse(Migration.is_file_name_valid('20090214120600_good_name_bad_extension.foo'))
        self.assertFalse(Migration.is_file_name_valid('spamspamspamspamspaam'))

    @patch('simple_db_migrate.core.strftime', return_value='20120303194030')
    def test_it_should_create_migration_file(self, strftime_mock):
        self.assertFalse(os.path.exists('20120303194030_create_a_file_test_migration.migration'))
        Migration.create('create_a_file_test_migration', '.')
        self.assertTrue(os.path.exists('20120303194030_create_a_file_test_migration.migration'))

    @patch('simple_db_migrate.core.strftime', return_value='20120303194030')
    @patch('codecs.open', side_effect=IOError('error when writing'))
    def test_it_should_raise_exception_if_an_error_hapens_when_writing_the_file(self, open_mock, strftime_mock):
        try:
            Migration.create('test_migration')
            self.fail('it should not pass here')
        except Exception, e:
            self.assertEqual("could not create file ('./20120303194030_test_migration.migration')", str(e))

    @patch('simple_db_migrate.core.gmtime', return_value=(2012,03,03,19,40,30,0,0,0))
    def test_it_should_use_gmt_time_when_asked_to_use_utc(self, gmtime_mock):
        Migration.create('test_migration', utc_timestamp=True)
        gmtime_mock.assert_called_once()

    @patch('simple_db_migrate.core.localtime', return_value=(2012,03,03,19,40,30,0,0,0))
    def test_it_should_use_local_time_when_asked_to_not_use_utc(self, localtime_mock):
        Migration.create('test_migration', utc_timestamp=False)
        localtime_mock.assert_called_once()

    @patch('simple_db_migrate.core.Migration.is_file_name_valid', return_value=False)
    @patch('simple_db_migrate.core.strftime', return_value='20120303194030')
    def test_it_should_raise_exception_if_migration_has_a_invalid_name(self, strftime_mock, is_file_name_valid_mock):
        self.assertRaisesWithMessage(Exception, "invalid migration name ('#test_migration'); it should contain only letters, numbers and/or underscores", Migration.create, '#test_migration')
        is_file_name_valid_mock.assert_called_with('20120303194030_#test_migration.migration')

    def test_it_should_return_an_empty_string_if_sql_or_script_encoding_are_invalid(self):
        self.assertEqual('', Migration.ensure_sql_unicode('', ''))
        self.assertEqual('', Migration.ensure_sql_unicode('', "iso8859-1"))
        self.assertEqual('', Migration.ensure_sql_unicode('', None))
        self.assertEqual('', Migration.ensure_sql_unicode('', False))
        self.assertEqual('', Migration.ensure_sql_unicode('sql', ''))
        self.assertEqual('', Migration.ensure_sql_unicode(None, "iso8859-1"))
        self.assertEqual('', Migration.ensure_sql_unicode(False, "iso8859-1"))

    def test_it_should_convert_sql_to_unicode_from_script_encoding(self):
        self.assertEqual(u'sql in iso8859-1', Migration.ensure_sql_unicode('sql in iso8859-1'.encode("iso8859-1"), "iso8859-1"))

    def test_it_should_sort_a_migrations_list(self):
        migrations = []
        migrations.append(Migration('20090727141400_test_migration.migration'))
        migrations.append(Migration('20090214120600_example_file_name_test_migration.migration'))
        migrations.append(Migration('20090727141503_test_migration.migration'))
        migrations.append(Migration('20090727104700_test_migration.migration'))

        sorted_migrations = Migration.sort_migrations_list(migrations)
        self.assertEqual('20090214120600', sorted_migrations[0].version)
        self.assertEqual('20090727104700', sorted_migrations[1].version)
        self.assertEqual('20090727141400', sorted_migrations[2].version)
        self.assertEqual('20090727141503', sorted_migrations[3].version)

    def test_it_should_sort_a_migrations_list_in_rerverse_order(self):
        migrations = []
        migrations.append(Migration('20090727141400_test_migration.migration'))
        migrations.append(Migration('20090214120600_example_file_name_test_migration.migration'))
        migrations.append(Migration('20090727141503_test_migration.migration'))
        migrations.append(Migration('20090727104700_test_migration.migration'))

        sorted_migrations = Migration.sort_migrations_list(migrations, reverse=True)
        self.assertEqual('20090727141503', sorted_migrations[0].version)
        self.assertEqual('20090727141400', sorted_migrations[1].version)
        self.assertEqual('20090727104700', sorted_migrations[2].version)
        self.assertEqual('20090214120600', sorted_migrations[3].version)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = exceptions_test
import unittest
from simple_db_migrate.core.exceptions import MigrationException

class MigrationExceptionTest(unittest.TestCase):

    def test_it_should_use_default_message(self):
        exception = MigrationException()
        self.assertEqual('error executing migration', str(exception))

    def test_it_should_use_custom_message(self):
        exception = MigrationException('custom error message')
        self.assertEqual('custom error message', str(exception))

    def test_it_should_use_default_message_and_sql_command(self):
        exception = MigrationException(sql='sql command executed')
        self.assertEqual('error executing migration\n\n[ERROR DETAILS] SQL command was:\nsql command executed', str(exception))

    def test_it_should_use_custom_message_and_sql_command(self):
        exception = MigrationException(sql='sql command executed', msg='custom error message')
        self.assertEqual('custom error message\n\n[ERROR DETAILS] SQL command was:\nsql command executed', str(exception))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = helpers_test
import unittest
import os
import sys
from simple_db_migrate.helpers import Lists, Utils

class ListsTest(unittest.TestCase):

    def test_it_should_subtract_lists(self):
        a = ["a", "b", "c", "d", "e", "f"]
        b = ["a", "b", "c", "e"]
        result = Lists.subtract(a, b)

        self.assertEquals(len(result), 2)
        self.assertEquals(result[0], "d")
        self.assertEquals(result[1], "f")

    def test_it_should_subtract_lists2(self):
        a = ["a", "b", "c", "e"]
        b = ["a", "b", "c", "d", "e", "f"]

        result = Lists.subtract(a, b)

        self.assertEquals(len(result), 0)

class UtilsTest(unittest.TestCase):

    def setUp(self):
        config_file = '''
DATABASE_HOST = 'localhost'
DATABASE_USER = 'root'
DATABASE_PASSWORD = ''
DATABASE_NAME = 'migration_example'
ENV1_DATABASE_NAME = 'migration_example_env1'
DATABASE_MIGRATIONS_DIR = 'example'
UTC_TIMESTAMP = True
DATABASE_ANY_CUSTOM_VARIABLE = 'Some Value'
SOME_ENV_DATABASE_ANY_CUSTOM_VARIABLE = 'Other Value'
DATABASE_OTHER_CUSTOM_VARIABLE = 'Value'
'''
        f = open('sample.conf', 'w')
        f.write(config_file)
        f.close()

        f = open('sample.py', 'w')
        f.write('import os\n')
        f.write(config_file)
        f.close()

    def tearDown(self):
        os.remove('sample.conf')
        os.remove('sample.py')

    def test_it_should_count_chars_in_a_string(self):
        word = 'abbbcd;;;;;;;;;;;;;;'
        count = Utils.count_occurrences(word)
        self.assertEqual( 1, count.get('a', 0))
        self.assertEqual( 3, count.get('b', 0))
        self.assertEqual(14, count.get(';', 0))
        self.assertEqual( 0, count.get('%', 0))

    def test_it_should_extract_variables_from_a_config_file(self):
        variables = Utils.get_variables_from_file(os.path.abspath('sample.conf'))
        self.assertEqual('root', variables['DATABASE_USER'])
        self.assertEqual('migration_example_env1', variables['ENV1_DATABASE_NAME'])
        self.assertEqual('migration_example', variables['DATABASE_NAME'])
        self.assertEqual('example', variables['DATABASE_MIGRATIONS_DIR'])
        self.assertEqual(True, variables['UTC_TIMESTAMP'])
        self.assertEqual('localhost', variables['DATABASE_HOST'])
        self.assertEqual('', variables['DATABASE_PASSWORD'])

    def test_it_should_extract_variables_from_a_config_file_with_py_extension(self):
        variables = Utils.get_variables_from_file(os.path.abspath('sample.py'))
        self.assertEqual('root', variables['DATABASE_USER'])
        self.assertEqual('migration_example_env1', variables['ENV1_DATABASE_NAME'])
        self.assertEqual('migration_example', variables['DATABASE_NAME'])
        self.assertEqual('example', variables['DATABASE_MIGRATIONS_DIR'])
        self.assertEqual(True, variables['UTC_TIMESTAMP'])
        self.assertEqual('localhost', variables['DATABASE_HOST'])
        self.assertEqual('', variables['DATABASE_PASSWORD'])

    def test_it_should_not_change_python_path(self):
        original_paths = []
        for path in sys.path:
            original_paths.append(path)

        Utils.get_variables_from_file(os.path.abspath('sample.py'))

        self.assertEqual(original_paths, sys.path)


    def test_it_should_raise_exception_config_file_has_a_sintax_problem(self):
        f = open('sample.py', 'a')
        f.write('\nimport some_not_imported_module\n')
        f.close()
        try:
            Utils.get_variables_from_file(os.path.abspath('sample.py'))
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("error interpreting config file 'sample.py': No module named some_not_imported_module", str(e))

    def test_it_should_raise_exception_config_file_not_exists(self):
        try:
            Utils.get_variables_from_file(os.path.abspath('unexistent.conf'))
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("%s: file not found" % os.path.abspath('unexistent.conf'), str(e))

    def test_it_should_delete_compiled_module_file(self):
        Utils.get_variables_from_file(os.path.abspath('sample.py'))
        self.assertFalse(os.path.exists(os.path.abspath('sample.pyc')))

########NEW FILE########
__FILENAME__ = log_test
import unittest
import os
import logging
from datetime import datetime
from mock import patch, call, Mock
from simple_db_migrate.log import LOG
from tests import BaseTest, delete_files

class LogTest(BaseTest):
    def tearDown(self):
        super(LogTest, self).tearDown()
        delete_files('log_dir_test/path/subpath/*.log')
        if os.path.exists('log_dir_test/path/subpath'):
            os.rmdir('log_dir_test/path/subpath')
        if os.path.exists('log_dir_test/path'):
            os.rmdir('log_dir_test/path')
        if os.path.exists('log_dir_test'):
            os.rmdir('log_dir_test')

    def test_it_should_not_raise_error_if_log_dir_is_not_specified(self):
        try:
            log = LOG(None)
            log.debug('debug message')
            log.info('info message')
            log.error('error message')
            log.warn('warn message')
        except:
            self.fail("it should not get here")

    @patch('os.makedirs', side_effect=os.makedirs)
    def test_it_should_create_log_dir_if_does_not_exists(self, makedirs_mock):
        LOG('log_dir_test/path/subpath')
        expected_calls = [
            call('log_dir_test/path/subpath'),
            call('log_dir_test/path', 511),
            call('log_dir_test', 511)
        ]
        self.assertEqual(expected_calls, makedirs_mock.mock_calls)

    def test_it_should_create_a_logger(self):
        log = LOG('log_dir_test/path/subpath')
        self.assertTrue(isinstance(log.logger, logging.Logger))
        self.assertEqual(logging.DEBUG, log.logger.level)
        self.assertTrue(isinstance(log.logger.handlers[0], logging.FileHandler))
        self.assertEqual("%s/%s.log" %(os.path.abspath('log_dir_test/path/subpath'), datetime.now().strftime("%Y%m%d%H%M%S")), log.logger.handlers[0].baseFilename)
        self.assertTrue(isinstance(log.logger.handlers[0].formatter, logging.Formatter))
        self.assertEqual('%(message)s', log.logger.handlers[0].formatter._fmt)

    def test_it_should_use_logger_methods(self):
        log = LOG('log_dir_test/path/subpath')
        log.logger = Mock()
        log.debug('debug message')
        log.logger.debug.assert_called_with('debug message')
        log.info('info message')
        log.logger.info.assert_called_with('info message')
        log.error('error message')
        log.logger.error.assert_called_with('error message')
        log.warn('warn message')
        log.logger.warn.assert_called_with('warn message')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = main_test
import unittest
import os
import re
from StringIO import StringIO
from mock import patch, call, Mock
from simple_db_migrate.core import Migration
from simple_db_migrate.main import Main
from simple_db_migrate.config import Config
from tests import BaseTest, create_migration_file

class MainTest(BaseTest):
    def setUp(self):
        super(MainTest, self).setUp()
        self.initial_config = {
            'database_host': 'localhost',
            'database_name': 'test',
            'database_user': 'user',
            'database_password': 'password',
            'database_migrations_dir': ['.'],
            'database_engine': 'engine',
            'schema_version': None
        }
        if not os.path.exists(os.path.abspath('migrations')):
            os.mkdir(os.path.abspath('migrations'))
        self.test_migration_files = []

        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115100_01_test_migration.migration', 'foo 1', 'bar 1')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('migrations/20090214115200_02_test_migration.migration', 'foo 2', 'bar 2')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115300_03_test_migration.migration', 'foo 3', 'bar 3')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115400_04_test_migration.migration', 'foo 4', 'bar 4')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('migrations/20090214115500_05_test_migration.migration', 'foo 5', 'bar 5')))
        self.test_migration_files.append(os.path.abspath(create_migration_file('migrations/20090214115600_06_test_migration.migration', 'foo 6', 'bar 6')))

    def test_it_should_raise_error_if_a_required_config_to_migrate_is_missing(self):
        self.assertRaisesWithMessage(Exception, "invalid key ('database_host')", Main, config=Config())
        self.assertRaisesWithMessage(Exception, "invalid key ('database_name')", Main, config=Config({'database_host': ''}))
        self.assertRaisesWithMessage(Exception, "invalid key ('database_user')", Main, config=Config({'database_host': '', 'database_name': ''}))
        self.assertRaisesWithMessage(Exception, "invalid key ('database_password')", Main, config=Config({'database_host': '', 'database_name': '', 'database_user': ''}))
        self.assertRaisesWithMessage(Exception, "invalid key ('database_migrations_dir')", Main, config=Config({'database_host': '', 'database_name': '', 'database_user': '', 'database_password': ''}))
        self.assertRaisesWithMessage(Exception, "invalid key ('database_engine')", Main, config=Config({'database_host': '', 'database_name': '', 'database_user': '', 'database_password': '', 'database_migrations_dir': ''}))
        self.assertRaisesWithMessage(Exception, "invalid key ('schema_version')", Main, config=Config({'database_host': '', 'database_name': '', 'database_user': '', 'database_password': '', 'database_migrations_dir': '', 'database_engine':''}))

    def test_it_should_raise_error_if_a_required_config_to_create_migration_is_missing(self):
        self.assertRaisesWithMessage(Exception, "invalid key ('database_migrations_dir')", Main, config=Config({'new_migration': 'new'}))
        try:
            Main(Config({'new_migration': 'new', 'database_migrations_dir': ''}))
        except:
            self.fail("it should not get here")

    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG')
    @patch('simple_db_migrate.main.CLI')
    def test_it_should_use_the_other_utilities_classes(self, cli_mock, log_mock, simpledbmigrate_mock):
        config = Config(self.initial_config)
        Main(sgdb=Mock(), config=config)
        self.assertEqual(1, cli_mock.call_count)
        log_mock.assert_called_with(None)
        simpledbmigrate_mock.assert_called_with(config)

    @patch('simple_db_migrate.main.LOG')
    def test_it_should_use_log_dir_from_config(self, log_mock):
        self.initial_config.update({'log_dir':'.', "database_migrations_dir":['.']})
        Main(sgdb=Mock(), config=Config(self.initial_config))
        log_mock.assert_called_with('.')

    @patch('simple_db_migrate.mysql.MySQL')
    def test_it_should_use_mysql_class_if_choose_this_engine(self, mysql_mock):
        self.initial_config.update({'log_dir':'.', 'database_engine': 'mysql', "database_migrations_dir":['.']})
        config=Config(self.initial_config)
        Main(config=config)
        mysql_mock.assert_called_with(config)

    @patch('simple_db_migrate.oracle.Oracle')
    def test_it_should_use_oracle_class_if_choose_this_engine(self, oracle_mock):
        self.initial_config.update({'log_dir':'.', 'database_engine': 'oracle', "database_migrations_dir":['.']})
        config=Config(self.initial_config)
        Main(config=config)
        oracle_mock.assert_called_with(config)

    @patch('simple_db_migrate.mssql.MSSQL')
    def test_it_should_use_mssql_class_if_choose_this_engine(self, mssql_mock):
        self.initial_config.update({'log_dir':'.', 'database_engine': 'mssql', "database_migrations_dir":['.']})
        config=Config(self.initial_config)
        Main(config=config)
        mssql_mock.assert_called_with(config)

    def test_it_should_raise_error_if_config_is_not_an_instance_of_simple_db_migrate_config(self):
        self.assertRaisesWithMessage(Exception, "config must be an instance of simple_db_migrate.config.Config", Main, config={})

    def test_it_should_raise_error_if_choose_an_invalid_engine(self):
        self.initial_config.update({'log_dir':'.', 'database_engine': 'invalid_engine'})
        config=Config(self.initial_config)
        self.assertRaisesWithMessage(Exception, "engine not supported 'invalid_engine'", Main, config=config)

    def test_it_should_ignore_engine_configuration_if_asked_to_create_a_new_migration(self):
        self.initial_config.update({'new_migration':'new_test_migration', 'database_engine': 'invalid_engine', "database_migrations_dir":['.']})
        config=Config(self.initial_config)
        try:
            Main(config)
        except:
            self.fail("it should not get here")

    @patch('simple_db_migrate.main.Main._execution_log')
    @patch('simple_db_migrate.main.Migration.create', return_value='created_file')
    def test_it_should_create_migration_if_option_is_activated_by_the_user(self, migration_mock, _execution_log_mock):
        self.initial_config.update({'new_migration':'new_test_migration', 'database_engine': 'invalid_engine', "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call("- Created file 'created_file'", log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        migration_mock.assert_called_with('new_test_migration', 'migrations', 'utf-8', False)

    @patch('simple_db_migrate.main.Migration.create', return_value='created_file')
    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG')
    @patch('simple_db_migrate.main.CLI')
    def test_it_should_create_new_migration_with_utc_timestamp(self, cli_mock, log_mock, simpledbmigrate_mock, migration_mock):
        self.initial_config.update({'new_migration':'new_test_migration', 'database_engine': 'invalid_engine', "database_migrations_dir":['migrations', '.'], 'utc_timestamp': True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(), config=config)
        main.execute()
        migration_mock.assert_called_with('new_test_migration', 'migrations', 'utf-8', True)

    @patch('simple_db_migrate.main.Migration.create', return_value='created_file')
    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG')
    @patch('simple_db_migrate.main.CLI')
    def test_it_should_create_new_migration_with_different_encoding(self, cli_mock, log_mock, simpledbmigrate_mock, migration_mock):
        self.initial_config.update({'new_migration':'new_test_migration', 'database_engine': 'invalid_engine', "database_migrations_dir":['migrations', '.'], 'database_script_encoding': 'iso8859-1'})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(), config=config)
        main.execute()
        migration_mock.assert_called_with('new_test_migration', 'migrations', 'iso8859-1', False)

    @patch('simple_db_migrate.main.Main._execution_log')
    @patch('simple_db_migrate.main.Main._migrate')
    def test_it_should_migrate_db_if_create_migration_option_is_not_activated_by_user(self, migrate_mock, _execution_log_mock):
        config=Config(self.initial_config)
        main = Main(config=config, sgdb=Mock())
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        self.assertEqual(1, migrate_mock.call_count)

    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG.debug')
    @patch('simple_db_migrate.main.CLI')
    def test_it_should_write_the_message_to_log(self, cli_mock, log_mock, simpledbmigrate_mock):
        main = Main(sgdb=Mock(), config=Config(self.initial_config))
        main._execution_log('message to log')

        log_mock.assert_called_with('message to log')

    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG')
    @patch('simple_db_migrate.main.CLI.msg')
    def test_it_should_write_the_message_to_cli(self, cli_mock, log_mock, simpledbmigrate_mock):
        main = Main(sgdb=Mock(), config=Config(self.initial_config))
        main._execution_log('message to log', color='RED', log_level_limit=1)

        cli_mock.assert_called_with('message to log', 'RED')

    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG')
    @patch('simple_db_migrate.main.CLI.msg')
    def test_it_should_write_the_message_to_cli_using_default_color(self, cli_mock, log_mock, simpledbmigrate_mock):
        self.initial_config.update({'log_level':3})
        main = Main(sgdb=Mock(), config=Config(self.initial_config))
        main._execution_log('message to log')

        cli_mock.assert_called_with('message to log', 'CYAN')

    @patch('simple_db_migrate.main.Main._execute_migrations')
    @patch('simple_db_migrate.main.Main._get_destination_version', return_value='destination_version')
    @patch('simple_db_migrate.main.SimpleDBMigrate')
    @patch('simple_db_migrate.main.LOG')
    @patch('simple_db_migrate.main.CLI')
    def test_it_should_get_current_and_destination_versions_and_execute_migrations(self, cli_mock, log_mock, simpledbmigrate_mock, _get_destination_version_mock, execute_migrations_mock):
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'current_schema_version'}), config=Config(self.initial_config))
        main.execute()
        execute_migrations_mock.assert_called_with('current_schema_version', 'destination_version')

    def test_it_should_get_destination_version_when_user_informs_a_specific_version(self):
        self.initial_config.update({"schema_version":"20090214115300", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_id_from_version_number.return_value':None}), config=config)
        self.assertEqual("20090214115300", main._get_destination_version())
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_get_destination_version_when_user_does_not_inform_a_specific_version(self):
        self.initial_config.update({"database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(), config=config)
        self.assertEqual("20090214115600", main._get_destination_version())

    def test_it_should_raise_exception_when_get_destination_version_and_version_does_not_exist_on_database_or_on_migrations_dir(self):
        self.initial_config.update({"schema_version":"20090214115900", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_id_from_version_number.return_value':None}), config=config)
        self.assertRaisesWithMessage(Exception, 'version not found (20090214115900)', main.execute)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115900')
        self.assertEqual(2, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_get_destination_version_when_user_informs_a_label_and_it_does_not_exists_in_database(self):
        self.initial_config.update({"label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':None}), config=config)
        self.assertEqual("20090214115600", main._get_destination_version())
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')

    def test_it_should_get_destination_version_when_user_informs_a_specific_version_and_it_exists_on_database(self):
        self.initial_config.update({"schema_version":"20090214115300", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_id_from_version_number.return_value':3}), config=config)
        self.assertEqual("20090214115300", main._get_destination_version())
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_get_destination_version_when_user_informs_a_label_and_a_version_and_it_does_not_exists_in_database(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':None, 'get_version_id_from_version_number.return_value':None}), config=config)
        self.assertEqual("20090214115300", main._get_destination_version())
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)


    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[])
    def test_it_should_do_migration_down_if_a_label_and_a_version_were_specified_and_both_of_them_are_present_at_database_and_correspond_to_same_migration(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115600', 'get_version_number_from_label.return_value':'20090214115300', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115300', False)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[])
    def test_it_should_do_migration_down_if_a_label_and_a_version_were_specified_and_both_of_them_are_present_at_database_and_correspond_to_same_migration_and_force_execute_old_migrations_versions_is_set(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.'], "force_execute_old_migrations_versions": True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115600', 'get_version_number_from_label.return_value':'20090214115300', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115300', False)

    def test_it_should_get_destination_version_and_update_config_when_user_informs_a_label_and_it_exists_in_database(self):
        self.initial_config.update({"schema_version":None, "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':'20090214115300', 'get_version_id_from_version_number.return_value':3}), config=config)
        self.assertEqual("20090214115300", main._get_destination_version())
        self.assertEqual("20090214115300", config.get("schema_version"))
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_raise_exception_when_get_destination_version_and_version_and_label_point_to_a_different_migration_on_database(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':'20090214115400', 'get_version_id_from_version_number.return_value':3}), config=config)
        self.assertRaisesWithMessage(Exception, "label (test_label) and schema_version (20090214115300) don't correspond to the same version at database", main.execute)
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_raise_exception_when_get_destination_version_and_version_exists_on_database_and_label_not(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':None, 'get_version_id_from_version_number.return_value':3}), config=config)
        self.assertRaisesWithMessage(Exception, "label (test_label) or schema_version (20090214115300), only one of them exists in the database", main.execute)
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_raise_exception_when_get_destination_version_and_label_exists_on_database_and_version_not(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':'20090214115400', 'get_version_id_from_version_number.return_value':None}), config=config)
        self.assertRaisesWithMessage(Exception, "label (test_label) or schema_version (20090214115300), only one of them exists in the database", main.execute)
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_raise_exception_when_get_destination_version_and_version_and_label_point_to_a_different_migration_on_database_and_force_execute_old_migrations_versions_is_set(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.'], "force_execute_old_migrations_versions":True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':'20090214115400', 'get_version_id_from_version_number.return_value':3}), config=config)
        self.assertRaisesWithMessage(Exception, "label (test_label) and schema_version (20090214115300) don't correspond to the same version at database", main.execute)
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_raise_exception_when_get_destination_version_and_version_exists_on_database_and_label_not_and_force_execute_old_migrations_versions_is_set(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.'], "force_execute_old_migrations_versions":True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':None, 'get_version_id_from_version_number.return_value':3}), config=config)
        self.assertRaisesWithMessage(Exception, "label (test_label) or schema_version (20090214115300), only one of them exists in the database", main.execute)
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    def test_it_should_raise_exception_when_get_destination_version_and_label_exists_on_database_and_version_not_and_force_execute_old_migrations_versions_is_set(self):
        self.initial_config.update({"schema_version":"20090214115300", "label_version":"test_label", "database_migrations_dir":['migrations', '.'], "force_execute_old_migrations_versions":True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_version_number_from_label.return_value':'20090214115400', 'get_version_id_from_version_number.return_value':None}), config=config)
        self.assertRaisesWithMessage(Exception, "label (test_label) or schema_version (20090214115300), only one of them exists in the database", main.execute)
        main.sgdb.get_version_number_from_label.assert_called_with('test_label')
        self.assertEqual(1, main.sgdb.get_version_number_from_label.call_count)
        main.sgdb.get_version_id_from_version_number.assert_called_with('20090214115300')
        self.assertEqual(1, main.sgdb.get_version_id_from_version_number.call_count)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[])
    def test_it_should_migrate_database_with_migration_is_up(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version": None, "label_version": None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115300', 'get_version_id_from_version_number.return_value':None}), config=config)
        main.execute()
        files_to_be_executed_mock.assert_called_with('20090214115300', '20090214115600', True)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[])
    def test_it_should_migrate_database_with_migration_is_down_when_specify_a_version_older_than_that_on_database(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version": '20090214115200', "label_version": None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115300', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()
        files_to_be_executed_mock.assert_called_with('20090214115300', '20090214115200', False)

    def test_it_should_raise_error_when_specify_a_version_older_than_the_current_database_version_and_is_not_present_on_database(self):
        self.initial_config.update({"schema_version": '20090214115100', "label_version": None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115300', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'Trying to migrate to a lower version wich is not found on database (20090214115100)', main.execute)

    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_just_log_message_when_dont_have_any_migration_to_execute(self, _execution_log_mock):
        self.initial_config.update({"schema_version": None, "label_version": None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.return_value':None}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('\nNothing to do.\n', 'PINK', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[])
    def test_it_should_do_migration_down_if_a_label_was_specified_and_a_version_was_not_specified_and_label_is_present_at_database(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":None, "label_version":"test_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115600', 'get_version_number_from_label.return_value':'20090214115300', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115300', False)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[])
    def test_it_should_do_migration_down_if_a_label_was_specified_and_a_version_was_not_specified_and_label_is_present_at_database_and_force_execute_old_migrations_versions_is_set(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":None, "label_version":"test_label", "database_migrations_dir":['migrations', '.'], "force_execute_old_migrations_versions":True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115600', 'get_version_number_from_label.return_value':'20090214115300', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115300', False)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05"), Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_only_log_sql_commands_when_show_sql_only_is_set_and_is_up(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115600', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql_only':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115600', 'GREEN', log_level_limit=1),
            call("\nWARNING: database migrations are not being executed ('--showsqlonly' activated)", 'YELLOW', log_level_limit=1),
            call("*** versions: ['20090214115500', '20090214115600']\n", 'CYAN', log_level_limit=1),
            call('__________ SQL statements executed __________', 'YELLOW', log_level_limit=1),
            call('sql up 05', 'YELLOW', log_level_limit=1),
            call('sql up 06', 'YELLOW', log_level_limit=1),
            call('_____________________________________________', 'YELLOW', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115400', '20090214115600', True)
        self.assertEqual(0, main.sgdb.change.call_count)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06"), Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_only_log_sql_commands_when_show_sql_only_is_set_and_is_down(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115400', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql_only':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115400', 'GREEN', log_level_limit=1),
            call("\nWARNING: database migrations are not being executed ('--showsqlonly' activated)", 'YELLOW', log_level_limit=1),
            call("*** versions: ['20090214115600', '20090214115500']\n", 'CYAN', log_level_limit=1),
            call('__________ SQL statements executed __________', 'YELLOW', log_level_limit=1),
            call('sql down 06', 'YELLOW', log_level_limit=1),
            call('sql down 05', 'YELLOW', log_level_limit=1),
            call('_____________________________________________', 'YELLOW', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115400', False)
        self.assertEqual(0, main.sgdb.change.call_count)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05"), Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_execute_sql_commands_when_show_sql_only_is_not_set_and_is_up(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115600', "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('\nStarting migration up!', log_level_limit=1),
            call("*** versions: ['20090214115500', '20090214115600']\n", 'CYAN', log_level_limit=1),
            call('===== executing 20090214115500_05_test_migration.migration (up) =====', log_level_limit=1),
            call('===== executing 20090214115600_06_test_migration.migration (up) =====', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115400', '20090214115600', True)
        expected_calls = [
            call('sql up 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', True, _execution_log_mock, None),
            call('sql up 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', True, _execution_log_mock, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06"), Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_execute_sql_commands_when_show_sql_only_is_not_set_and_is_down(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115400', "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('\nStarting migration down!', log_level_limit=1),
            call("*** versions: ['20090214115600', '20090214115500']\n", 'CYAN', log_level_limit=1),
            call('===== executing 20090214115600_06_test_migration.migration (down) =====', log_level_limit=1),
            call('===== executing 20090214115500_05_test_migration.migration (down) =====', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115400', False)
        expected_calls = [
            call('sql down 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', False, _execution_log_mock, None),
            call('sql down 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', False, _execution_log_mock, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05"), Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_execute_and_log_sql_commands_when_show_sql_is_set_and_is_up(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115600', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('\nStarting migration up!', log_level_limit=1),
            call("*** versions: ['20090214115500', '20090214115600']\n", 'CYAN', log_level_limit=1),
            call('===== executing 20090214115500_05_test_migration.migration (up) =====', log_level_limit=1),
            call('===== executing 20090214115600_06_test_migration.migration (up) =====', log_level_limit=1),
            call('__________ SQL statements executed __________', 'YELLOW', log_level_limit=1),
            call('sql up 05', 'YELLOW', log_level_limit=1),
            call('sql up 06', 'YELLOW', log_level_limit=1),
            call('_____________________________________________', 'YELLOW', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115400', '20090214115600', True)
        expected_calls = [
            call('sql up 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', True, _execution_log_mock, None),
            call('sql up 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', True, _execution_log_mock, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06"), Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_execute_and_log_sql_commands_when_show_sql_is_set_and_is_down(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115400', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('\nStarting migration down!', log_level_limit=1),
            call("*** versions: ['20090214115600', '20090214115500']\n", 'CYAN', log_level_limit=1),
            call('===== executing 20090214115600_06_test_migration.migration (down) =====', log_level_limit=1),
            call('===== executing 20090214115500_05_test_migration.migration (down) =====', log_level_limit=1),
            call('__________ SQL statements executed __________', 'YELLOW', log_level_limit=1),
            call('sql down 06', 'YELLOW', log_level_limit=1),
            call('sql down 05', 'YELLOW', log_level_limit=1),
            call('_____________________________________________', 'YELLOW', log_level_limit=1),
            call('\nDone.\n', 'PINK', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115400', False)
        expected_calls = [
            call('sql down 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', False, _execution_log_mock, None),
            call('sql down 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', False, _execution_log_mock, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05"), Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06")])
    def test_it_should_apply_label_to_executed_sql_commands_when_a_label_was_specified_and_is_up(self, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":None, "label_version":"new_label", "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_version_number_from_label.return_value':None, 'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        expected_calls = [
            call('sql up 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', True, main._execution_log, 'new_label'),
            call('sql up 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', True, main._execution_log, 'new_label')
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05"), Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_raise_exception_and_stop_process_when_an_error_occur_on_executing_sql_commands_and_is_up(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115600', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.side_effect':Exception('error when executin sql'), 'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'error when executin sql', main.execute)

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('\nStarting migration up!', log_level_limit=1),
            call("*** versions: ['20090214115500', '20090214115600']\n", 'CYAN', log_level_limit=1),
            call('===== executing 20090214115500_05_test_migration.migration (up) =====', log_level_limit=1),
            call('===== ERROR executing  (up) =====', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115400', '20090214115600', True)
        expected_calls = [
            call('sql up 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', True, _execution_log_mock, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06"), Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05")])
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_raise_exception_and_stop_process_when_an_error_occur_on_executing_sql_commands_and_is_down(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115400', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.side_effect':Exception('error when executin sql'), 'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'error when executin sql', main.execute)

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
            call('- Current version is: 20090214115600', 'GREEN', log_level_limit=1),
            call('- Destination version is: 20090214115400', 'GREEN', log_level_limit=1),
            call('\nStarting migration down!', log_level_limit=1),
            call("*** versions: ['20090214115600', '20090214115500']\n", 'CYAN', log_level_limit=1),
            call('===== executing 20090214115600_06_test_migration.migration (down) =====', log_level_limit=1),
            call('===== ERROR executing  (down) =====', log_level_limit=1)
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115400', False)
        expected_calls = [
            call('sql down 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', False, _execution_log_mock, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', side_effect=Exception('error getting migrations to execute'))
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_raise_exception_and_stop_process_when_an_error_occur_on_getting_migrations_to_execute_and_is_up(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115600', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'error getting migrations to execute', main.execute)

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115400', '20090214115600', True)
        expected_calls = [
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', side_effect=Exception('error getting migrations to execute'))
    @patch('simple_db_migrate.main.Main._execution_log')
    def test_it_should_raise_exception_and_stop_process_when_an_error_occur_on_getting_migrations_to_execute_and_is_down(self, _execution_log_mock, files_to_be_executed_mock):
        self.initial_config.update({"schema_version":'20090214115400', "label_version":None, "database_migrations_dir":['migrations', '.'], 'show_sql':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'error getting migrations to execute', main.execute)

        expected_calls = [
            call('\nStarting DB migration on host/database "localhost/test" with user "user"...', 'PINK', log_level_limit=1),
        ]
        self.assertEqual(expected_calls, _execution_log_mock.mock_calls)
        files_to_be_executed_mock.assert_called_with('20090214115600', '20090214115400', False)
        expected_calls = [
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('sys.stdin', return_value="\n", **{'readline.return_value':"\n"})
    @patch('sys.stdout', new_callable=StringIO)
    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05"), Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06")])
    def test_it_should_pause_execution_after_each_migration_when_paused_mode_is_set_and_is_up(self, files_to_be_executed_mock, stdout_mock, stdin_mock):
        self.initial_config.update({"schema_version":'20090214115600', "label_version":None, "database_migrations_dir":['migrations', '.'], 'paused_mode':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115400', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        self.assertEqual(2, stdout_mock.getvalue().count("* press <enter> to continue..."))

        expected_calls = [
            call('sql up 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', True, main._execution_log, None),
            call('sql up 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', True, main._execution_log, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    @patch('sys.stdin', return_value="\n", **{'readline.return_value':"\n"})
    @patch('sys.stdout', new_callable=StringIO)
    @patch('simple_db_migrate.main.Main._get_migration_files_to_be_executed', return_value=[Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="sql up 06", sql_down="sql down 06"), Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05")])
    def test_it_should_pause_execution_after_each_migration_when_paused_mode_is_set_and_is_down(self, files_to_be_executed_mock, stdout_mock, stdin_mock):
        self.initial_config.update({"schema_version":'20090214115400', "label_version":None, "database_migrations_dir":['migrations', '.'], 'paused_mode':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'change.return_value':None, 'get_current_schema_version.return_value':'20090214115600', 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        main.execute()

        self.assertEqual(2, stdout_mock.getvalue().count("* press <enter> to continue..."))

        expected_calls = [
            call('sql down 06', '20090214115600', '20090214115600_06_test_migration.migration', 'sql up 06', 'sql down 06', False, main._execution_log, None),
            call('sql down 05', '20090214115500', '20090214115500_05_test_migration.migration', 'sql up 05', 'sql down 05', False, main._execution_log, None)
        ]
        self.assertEqual(expected_calls, main.sgdb.change.mock_calls)

    def test_it_should_return_an_empty_list_of_files_to_execute_if_current_and_destiny_version_are_equals(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_all_schema_versions.return_value':['20090214115100', '20090214115200', '20090214115300', '20090214115600']}), config=config)
        self.assertEqual([], main._get_migration_files_to_be_executed('20090214115600', '20090214115600', True))

    def test_it_should_return_an_empty_list_of_files_to_execute_if_current_and_destiny_version_are_equals_and_has_new_files_to_execute(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_all_schema_versions.return_value':['20090214115100', '20090214115200', '20090214115300']}), config=config)
        self.assertEqual([], main._get_migration_files_to_be_executed('20090214115300', '20090214115300', True))

    def test_it_should_check_if_has_any_old_files_to_execute_if_current_and_destiny_version_are_equals_and_force_old_migrations_is_set(self):
        all_schema_migrations = [
            Migration(file_name="20090214115100_01_test_migration.migration", version="20090214115100", sql_up="foo 1", sql_down="bar 1", id=1),
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="foo 2", sql_down="bar 2", id=2),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="foo 3", sql_down="bar 3", id=3),
            Migration(file_name="20090214115600_06_test_migration.migration", version="20090214115600", sql_up="foo 6", sql_down="bar 6", id=6),
        ]

        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.'], 'force_execute_old_migrations_versions':True})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115100', '20090214115200', '20090214115300', '20090214115600']}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115600', '20090214115600', True)

        self.assertEqual(2, len(migrations))
        self.assertEqual('20090214115400_04_test_migration.migration', migrations[0].file_name)
        self.assertEqual('20090214115500_05_test_migration.migration', migrations[1].file_name)

    def test_it_should_check_if_has_any_old_files_to_execute_if_current_and_destiny_version_are_different(self):
        all_schema_migrations = [
            Migration(file_name="20090214115100_01_test_migration.migration", version="20090214115100", sql_up="foo 1", sql_down="bar 1", id=1),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="foo 3", sql_down="bar 3", id=3),
        ]

        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115100', '20090214115300']}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115300', '20090214115500', True)

        self.assertEqual(3, len(migrations))
        self.assertEqual('20090214115200_02_test_migration.migration', migrations[0].file_name)
        self.assertEqual('20090214115400_04_test_migration.migration', migrations[1].file_name)
        self.assertEqual('20090214115500_05_test_migration.migration', migrations[2].file_name)

    def test_it_should_return_migrations_with_same_version_to_execute(self):
        self.test_migration_files.append(os.path.abspath(create_migration_file('20090214115400_04_1_same_version_test_migration.migration', 'foo 4_1', 'bar 4_1')))

        all_schema_migrations = [
            Migration(file_name="20090214115100_01_test_migration.migration", version="20090214115100", sql_up="foo 1", sql_down="bar 1", id=1),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="foo 3", sql_down="bar 3", id=3),
        ]

        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115100', '20090214115300']}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115300', '20090214115500', True)

        self.assertEqual(4, len(migrations))
        self.assertEqual('20090214115200_02_test_migration.migration', migrations[0].file_name)
        self.assertEqual('20090214115400_04_1_same_version_test_migration.migration', migrations[1].file_name)
        self.assertEqual('20090214115400_04_test_migration.migration', migrations[2].file_name)
        self.assertEqual('20090214115500_05_test_migration.migration', migrations[3].file_name)

    def test_it_should_return_an_empty_list_of_files_to_execute_if_current_and_destiny_version_are_equals_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="sql up 03", sql_down="sql down 03", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115300', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertEqual([], main._get_migration_files_to_be_executed('20090214115400', '20090214115400', False))

    def test_it_should_get_all_schema_migrations_to_check_wich_one_has_to_be_removed_if_current_and_destiny_version_are_equals_and_is_down_and_force_old_migrations_is_set(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.'], 'force_execute_old_migrations_versions':True})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="sql up 03", sql_down="sql down 03", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115300', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertEqual([], main._get_migration_files_to_be_executed('20090214115400', '20090214115400', False))

    def test_it_should_get_all_schema_migrations_to_check_wich_one_has_to_be_removed_if_current_and_destiny_version_are_different_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="sql up 03", sql_down="sql down 03", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115300', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertEqual([all_schema_migrations[-1], all_schema_migrations[-2]], main._get_migration_files_to_be_executed('20090214115400', '20090214115200', False))

    def test_it_should_get_all_schema_migrations_to_check_wich_one_has_to_be_removed_if_one_of_migration_file_does_not_exists_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115301_03_test_migration.migration", version="20090214115301", sql_up="sql up 03.1", sql_down="sql down 03.1", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115301', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertEqual([all_schema_migrations[-1], all_schema_migrations[-2]], main._get_migration_files_to_be_executed('20090214115400', '20090214115200', False))

    def test_it_should_not_fail_when_there_is_no_migrations_files_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['no_migrations']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115301_03_test_migration.migration", version="20090214115301", sql_up="sql up 03.1", sql_down="sql down 03.1", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115301', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertEqual([all_schema_migrations[-1], all_schema_migrations[-2]], main._get_migration_files_to_be_executed('20090214115400', '20090214115200', False))

    def test_it_should_get_sql_down_from_file_if_sql_down_is_empty_on_database_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="sql up 03", sql_down="", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115300', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115400', '20090214115200', False)
        self.assertEqual([all_schema_migrations[-1], all_schema_migrations[-2]], migrations)
        self.assertEqual(u"sql down 04", migrations[0].sql_down)
        self.assertEqual(u"bar 3", migrations[1].sql_down)

    def test_it_should_get_sql_down_from_file_if_force_use_files_is_set_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.'], 'force_use_files_on_down':True})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115300_03_test_migration.migration", version="20090214115300", sql_up="sql up 03", sql_down="sql down 03", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115300', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115400', '20090214115200', False)
        self.assertEqual([all_schema_migrations[-1], all_schema_migrations[-2]], migrations)
        self.assertEqual(u"bar 4", migrations[0].sql_down)
        self.assertEqual(u"bar 3", migrations[1].sql_down)

    def test_it_should_raise_exception_and_stop_process_when_a_migration_has_an_empty_sql_down_and_migration_file_is_not_present_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115301_03_test_migration.migration", version="20090214115301", sql_up="sql up 03.1", sql_down="", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115301', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'impossible to migrate down: one of the versions was not found (20090214115301)', main._get_migration_files_to_be_executed, '20090214115400', '20090214115200', False)

    def test_it_should_raise_exception_and_stop_process_when_a_migration_file_is_not_present_and_force_files_is_set_and_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.'], 'force_use_files_on_down':True})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115301_03_test_migration.migration", version="20090214115301", sql_up="sql up 03.1", sql_down="sql down 03.1", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115301', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        self.assertRaisesWithMessage(Exception, 'impossible to migrate down: one of the versions was not found (20090214115301)', main._get_migration_files_to_be_executed, '20090214115400', '20090214115200', False)

    def test_it_should_return_migrations_with_same_version_to_execute_when_is_down(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115301_03_test_migration.migration", version="20090214115301", sql_up="sql up 03.1", sql_down="sql down 03.1", id=3),
            Migration(file_name="20090214115400_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4),
            Migration(file_name="20090214115400_04_1_same_version_test_migration.migration", version="20090214115400", sql_up="sql up 04.1", sql_down="sql down 04.1", id=5)
        ]
        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115301', '20090214115400', '20090214115400'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115400', '20090214115200', False)

        self.assertEqual(3, len(migrations))
        self.assertEqual('20090214115400_04_1_same_version_test_migration.migration', migrations[0].file_name)
        self.assertEqual('20090214115400_04_test_migration.migration', migrations[1].file_name)
        self.assertEqual('20090214115301_03_test_migration.migration', migrations[2].file_name)

    def test_it_should_return_migrations_without_same_version_to_execute_when_is_down_and_the_duplicated_version_is_the_destination(self):
        self.initial_config.update({"schema_version":None, "label_version":None, "database_migrations_dir":['migrations', '.']})
        config=Config(self.initial_config)
        all_schema_migrations = [
            Migration(file_name="20090214115200_02_test_migration.migration", version="20090214115200", sql_up="sql up 02", sql_down="sql down 02", id=2),
            Migration(file_name="20090214115301_03_test_migration.migration", version="20090214115301", sql_up="sql up 03.1", sql_down="sql down 03.1", id=3),
            Migration(file_name="20090214115300_04_test_migration.migration", version="20090214115400", sql_up="sql up 04", sql_down="sql down 04", id=4),
            Migration(file_name="20090214115400_04_1_same_version_test_migration.migration", version="20090214115400", sql_up="sql up 04.1", sql_down="sql down 04.1", id=5),
            Migration(file_name="20090214115500_05_test_migration.migration", version="20090214115500", sql_up="sql up 05", sql_down="sql down 05", id=6)
        ]

        def get_version_id_from_version_number_side_effect(args):
            return [migration.id for migration in Migration.sort_migrations_list(all_schema_migrations, reverse=True) if migration.version == str(args)][0]

        main = Main(sgdb=Mock(**{'get_all_schema_migrations.return_value':all_schema_migrations, 'get_all_schema_versions.return_value':['20090214115200', '20090214115301', '20090214115400', '20090214115400', '20090214115500'], 'get_version_id_from_version_number.side_effect':get_version_id_from_version_number_side_effect}), config=config)
        migrations = main._get_migration_files_to_be_executed('20090214115500', '20090214115400', False)

        self.assertEqual(1, len(migrations))
        self.assertEqual('20090214115500_05_test_migration.migration', migrations[0].file_name)


def get_version_id_from_version_number_side_effect(args):
    if str(args) == '20090214115100':
        return None
    match = re.match("[0-9]{11}([0-9])[0-9]{2}", str(args))
    return int(match.group(1))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = mssql_test
import unittest
import sys
import simple_db_migrate.core
from mock import patch, Mock, MagicMock, call
from simple_db_migrate.mssql import MSSQL
from tests import BaseTest

class MSSQLTest(BaseTest):

    def setUp(self):
        super(MSSQLTest, self).setUp()
        self.execute_returns = {'select count(*) from __db_version__;': 0}
        self.close_returns = {}
        self.last_execute_command = '';
        self.config_dict = {'database_script_encoding': 'utf8',
                   'database_encoding': 'utf8',
                   'database_host': 'somehost',
                   'database_user': 'root',
                   'database_password': 'pass',
                   'database_name': 'migration_test',
                   'database_version_table': '__db_version__',
                   'drop_db_first': False
                }

        self.config_mock = MagicMock(spec_set=dict, wraps=self.config_dict)
        self.db_mock = MagicMock(**{"execute_scalar": Mock(side_effect=self.execute_side_effect),
                               "execute_non_query": Mock(side_effect=self.execute_side_effect),
                               "execute_query": Mock(side_effect=self.execute_side_effect),
                               "execute_row": Mock(side_effect=self.execute_side_effect),
                               "close": Mock(side_effect=self.close_side_effect),
                               "__iter__":Mock(side_effect=self.iter_side_effect)})
        self.db_driver_mock = Mock(**{"connect.return_value": self.db_mock})

    @patch.dict('sys.modules', _mssql=MagicMock())
    def test_it_should_use_mssql_as_driver(self):
        MSSQL(self.config_mock)
        self.assertNotEqual(0, sys.modules['_mssql'].connect.call_count)

    @patch.dict('sys.modules', _mssql=MagicMock())
    def test_it_should_use_default_port(self):
        MSSQL(self.config_mock)
        self.assertEqual(call(user='root', password='pass', charset='utf8', port=1433, server='somehost'), sys.modules['_mssql'].connect.call_args)

    @patch.dict('sys.modules', _mssql=MagicMock())
    def test_it_should_use_given_configuration(self):
        self.config_dict['database_port'] = 9876
        MSSQL(self.config_mock)
        self.assertEqual(call(user='root', password='pass', charset='utf8', port=9876, server='somehost'), sys.modules['_mssql'].connect.call_args)

    def test_it_should_stop_process_when_an_error_occur_during_connect_database(self):
        self.db_driver_mock.connect.side_effect = Exception("error when connecting")

        try:
            MSSQL(self.config_mock, self.db_driver_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("could not connect to database: error when connecting", str(e))

        self.assertEqual(0, self.db_mock.close.call_count)
        self.assertEqual(0, self.db_mock.execute_scalar.call_count)
        self.assertEqual(0, self.db_mock.execute_non_query.call_count)
        self.assertEqual(0, self.db_mock.execute_query.call_count)


    def test_it_should_create_database_and_version_table_on_init_if_not_exists(self):
        MSSQL(self.config_mock, self.db_driver_mock)

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(4, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_drop_database_on_init_if_its_asked(self):
        self.config_dict["drop_db_first"] = True

        MSSQL(self.config_mock, self.db_driver_mock)

        expected_query_calls = [
            call("if exists ( select 1 from sysdatabases where name = 'migration_test' ) drop database migration_test;"),
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_stop_process_when_an_error_occur_during_drop_database(self):
        self.config_dict["drop_db_first"] = True
        self.db_mock.execute_non_query.side_effect = Exception("error when dropping")

        try:
            MSSQL(self.config_mock, self.db_driver_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("can't drop database 'migration_test'; \nerror when dropping", str(e))

        expected_query_calls = [
            call("if exists ( select 1 from sysdatabases where name = 'migration_test' ) drop database migration_test;")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.assertEqual(1, self.db_mock.close.call_count)


    def test_it_should_execute_migration_up_and_update_schema_version(self):
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        mssql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;")

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')"),
            call('create table spam()'),
            call('insert into __db_version__ (version, label, name, sql_up, sql_down) values (%s, %s, %s, %s, %s);', ('20090212112104', None, '20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration', 'create table spam();', 'drop table spam;'))
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_execute_migration_down_and_update_schema_version(self):
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        mssql.change("drop table spam;", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", False)

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')"),
            call('drop table spam'),
            call("delete from __db_version__ where version = %s;", ('20090212112104',))
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_use_label_version_when_updating_schema_version(self):
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        mssql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')"),
            call('create table spam()'),
            call('insert into __db_version__ (version, label, name, sql_up, sql_down) values (%s, %s, %s, %s, %s);', ('20090212112104', 'label', '20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration', 'create table spam();', 'drop table spam;'))
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_raise_whem_migration_sql_has_a_syntax_error(self):
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        self.assertRaisesWithMessage(Exception, "error executing migration: invalid sql syntax 'create table foo(); create table spam());'", mssql.change,
                                     "create table foo(); create table spam());", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam());", "drop table spam;", label_version="label")

    def test_it_should_stop_process_when_an_error_occur_during_database_change(self):
        self.execute_returns["insert into spam"] = Exception("invalid sql")

        try:
            mssql = MSSQL(self.config_mock, self.db_driver_mock)
            mssql.change("create table spam(); insert into spam", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")
        except Exception, e:
            self.assertEqual("error executing migration: invalid sql\n\n[ERROR DETAILS] SQL command was:\ninsert into spam", str(e))
            self.assertTrue(isinstance(e, simple_db_migrate.core.exceptions.MigrationException))

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')"),
            call('create table spam()'),
            call('insert into spam')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(1, self.db_mock.cancel.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_stop_process_when_an_error_occur_during_log_schema_version(self):
        self.execute_returns['insert into __db_version__ (version, label, name, sql_up, sql_down) values (%s, %s, %s, %s, %s);'] = Exception("invalid sql")

        try:
            mssql = MSSQL(self.config_mock, self.db_driver_mock)
            mssql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")
        except Exception, e:
            self.assertEqual('error logging migration: invalid sql\n\n[ERROR DETAILS] SQL command was:\n20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration', str(e))
            self.assertTrue(isinstance(e, simple_db_migrate.core.exceptions.MigrationException))

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')"),
            call('create table spam()'),
            call('insert into __db_version__ (version, label, name, sql_up, sql_down) values (%s, %s, %s, %s, %s);', ('20090212112104', 'label', '20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration', 'create table spam();', 'drop table spam;'))
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(1, self.db_mock.cancel.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;'),
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_log_execution_when_a_function_is_given_when_updating_schema_version(self):
        execution_log_mock = Mock()
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        mssql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", execution_log=execution_log_mock)

        expected_execution_log_calls = [
            call('create table spam()\n-- 1 row(s) affected\n'),
            call('migration 20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration registered\n')
        ]
        self.assertEqual(expected_execution_log_calls, execution_log_mock.mock_calls)

    def test_it_should_get_current_schema_version(self):
        self.execute_returns = {'select count(*) from __db_version__;': 0, 'select top 1 version from __db_version__ order by id desc': "0"}

        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        self.assertEquals("0", mssql.get_current_schema_version())

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;'),
            call("select top 1 version from __db_version__ order by id desc")
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

    def test_it_should_get_all_schema_versions(self):
        expected_versions = []
        expected_versions.append("0")
        expected_versions.append("20090211120001")
        expected_versions.append("20090211120002")
        expected_versions.append("20090211120003")

        db_versions = [{'version':version} for version in expected_versions]

        self.execute_returns = {'select count(*) from __db_version__;': 0, 'select version from __db_version__ order by id;': db_versions}

        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        schema_versions = mssql.get_all_schema_versions()

        self.assertEquals(len(expected_versions), len(schema_versions))
        for version in schema_versions:
            self.assertTrue(version in expected_versions)

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

        expected_execute_calls = [
            call("select version from __db_version__ order by id;")
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_query.mock_calls)

    def test_it_should_get_all_schema_migrations(self):
        expected_versions = []
        expected_versions.append([1, "0", None, None, None, None])
        expected_versions.append([2, "20090211120001", "label", "20090211120001_name", "sql_up", "sql_down"])

        db_versions = [{'id': db_version[0], 'version':db_version[1], 'label':db_version[2], 'name':db_version[3], 'sql_up':db_version[4], 'sql_down':db_version[5]} for db_version in expected_versions]

        self.execute_returns = {'select count(*) from __db_version__;': 0, 'select id, version, label, name, cast(sql_up as text) as sql_up, cast(sql_down as text) as sql_down from __db_version__ order by id;': db_versions}

        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        schema_migrations = mssql.get_all_schema_migrations()

        self.assertEquals(len(expected_versions), len(schema_migrations))
        for index, migration in enumerate(schema_migrations):
            self.assertEqual(migration.id, expected_versions[index][0])
            self.assertEqual(migration.version, expected_versions[index][1])
            self.assertEqual(migration.label, expected_versions[index][2])
            self.assertEqual(migration.file_name, expected_versions[index][3])
            self.assertEqual(migration.sql_up, expected_versions[index][4] and expected_versions[index][4] or "")
            self.assertEqual(migration.sql_down, expected_versions[index][5] and expected_versions[index][5] or "")

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;'),
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

        expected_execute_calls = [
            call('select id, version, label, name, cast(sql_up as text) as sql_up, cast(sql_down as text) as sql_down from __db_version__ order by id;')
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_query.mock_calls)

    def test_it_should_parse_sql_statements(self):
        statements = MSSQL._parse_sql_statements('; ; create table eggs; drop table spam; ; ;')

        self.assertEqual(2, len(statements))
        self.assertEqual('create table eggs', statements[0])
        self.assertEqual('drop table spam', statements[1])

    def test_it_should_parse_sql_statements_with_html_inside(self):
        sql = u"""
        create table eggs;
        INSERT INTO widget_parameter_domain (widget_parameter_id, label, value)
        VALUES ((SELECT MAX(widget_parameter_id)
                FROM widget_parameter),  "Carros", '<div class="box-zap-geral">

            <div class="box-zap box-zap-autos">
                <a class="logo" target="_blank" title="ZAP" href="http://www.zap.com.br/Parceiros/g1/RedirG1.aspx?CodParceriaLink=42&amp;URL=http://www.zap.com.br">');
        drop table spam;
        """
        statements = MSSQL._parse_sql_statements(sql)

        expected_sql_with_html = """INSERT INTO widget_parameter_domain (widget_parameter_id, label, value)
        VALUES ((SELECT MAX(widget_parameter_id)
                FROM widget_parameter),  "Carros", '<div class="box-zap-geral">

            <div class="box-zap box-zap-autos">
                <a class="logo" target="_blank" title="ZAP" href="http://www.zap.com.br/Parceiros/g1/RedirG1.aspx?CodParceriaLink=42&amp;URL=http://www.zap.com.br">')"""

        self.assertEqual(3, len(statements))
        self.assertEqual('create table eggs', statements[0])
        self.assertEqual(expected_sql_with_html, statements[1])
        self.assertEqual('drop table spam', statements[2])

    def test_it_should_get_none_for_a_non_existent_version_in_database(self):
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        ret = mssql.get_version_id_from_version_number('xxx')
        self.assertEqual(None, ret)

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;'),
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

        expected_execute_calls = [
            call("select id from __db_version__ where version = 'xxx' order by id desc;")
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_row.mock_calls)

    def test_it_should_get_most_recent_version_for_a_existent_label_in_database(self):
        self.execute_returns = {'select count(*) from __db_version__;': 0, "select version from __db_version__ where label = 'xxx' order by id desc": {'version':"vesion"}}
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        ret = mssql.get_version_number_from_label('xxx')
        self.assertEqual("vesion", ret)

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;'),
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

        expected_execute_calls = [
            call("select version from __db_version__ where label = 'xxx' order by id desc")
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_row.mock_calls)

    def test_it_should_get_none_for_a_non_existent_label_in_database(self):
        mssql = MSSQL(self.config_mock, self.db_driver_mock)
        ret = mssql.get_version_number_from_label('xxx')
        self.assertEqual(None, ret)

        expected_query_calls = [
            call("if not exists ( select 1 from sysdatabases where name = 'migration_test' ) create database migration_test;"),
            call("if not exists ( select 1 from sysobjects where name = '__db_version__' and type = 'u' ) create table __db_version__ ( id INT IDENTITY(1,1) NOT NULL PRIMARY KEY, version varchar(20) NOT NULL default '0', label varchar(255), name varchar(255), sql_up NTEXT, sql_down NTEXT)"),
            call("insert into __db_version__ (version) values ('0')")
        ]
        self.assertEqual(expected_query_calls, self.db_mock.execute_non_query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select count(*) from __db_version__;'),
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_scalar.mock_calls)

        expected_execute_calls = [
            call("select version from __db_version__ where label = 'xxx' order by id desc")
        ]
        self.assertEqual(expected_execute_calls, self.db_mock.execute_row.mock_calls)

    def side_effect(self, returns, default_value):
        result = returns.get(self.last_execute_command, default_value)
        if isinstance(result, Exception):
            raise result
        return result

    def iter_side_effect(self, *args):
        return iter(self.side_effect(self.execute_returns, []))

    def execute_side_effect(self, *args):
        self.last_execute_command = args[0]
        return self.side_effect(self.execute_returns, 0)

    def close_side_effect(self, *args):
        return self.side_effect(self.close_returns, None)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = mysql_test
import unittest
import sys
import simple_db_migrate.core
from mock import patch, Mock, MagicMock, call
from simple_db_migrate.mysql import MySQL
from tests import BaseTest

class MySQLTest(BaseTest):

    def setUp(self):
        super(MySQLTest, self).setUp()
        self.execute_returns = {}
        self.fetchone_returns = {'select count(*) from __db_version__;': [0]}
        self.close_returns = {}
        self.last_execute_command = '';
        self.config_dict = {'database_script_encoding': 'utf8',
                   'database_encoding': 'utf8',
                   'database_host': 'somehost',
                   'database_user': 'root',
                   'database_password': 'pass',
                   'database_name': 'migration_test',
                   'database_version_table': '__db_version__',
                   'drop_db_first': False
                }

        self.config_mock = MagicMock(spec_set=dict, wraps=self.config_dict)
        self.cursor_mock = Mock(**{"execute": Mock(side_effect=self.execute_side_effect),
                                   "close": Mock(side_effect=self.close_side_effect),
                                   "fetchone": Mock(side_effect=self.fetchone_side_effect)})
        self.db_mock = Mock(**{"cursor.return_value": self.cursor_mock})
        self.db_driver_mock = Mock(**{"connect.return_value": self.db_mock})

    @patch.dict('sys.modules', MySQLdb=MagicMock())
    def test_it_should_use_mysqldb_as_driver(self):
        MySQL(self.config_mock)
        self.assertNotEqual(0, sys.modules['MySQLdb'].connect.call_count)

    @patch.dict('sys.modules', MySQLdb=MagicMock())
    def test_it_should_use_default_port(self):
        MySQL(self.config_mock)
        self.assertEqual(call(passwd='pass', host='somehost', user='root', port=3306), sys.modules['MySQLdb'].connect.call_args)

    @patch.dict('sys.modules', MySQLdb=MagicMock())
    def test_it_should_use_given_configuration(self):
        self.config_dict['database_port'] = 9876
        MySQL(self.config_mock)
        self.assertEqual(call(passwd='pass', host='somehost', user='root', port=9876), sys.modules['MySQLdb'].connect.call_args)

    def test_it_should_stop_process_when_an_error_occur_during_connect_database(self):
        self.db_driver_mock.connect.side_effect = Exception("error when connecting")

        try:
            MySQL(self.config_mock, self.db_driver_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("could not connect to database: error when connecting", str(e))

        self.assertEqual(0, self.db_mock.query.call_count)
        self.assertEqual(0, self.db_mock.commit.call_count)
        self.assertEqual(0, self.db_mock.close.call_count)

        self.assertEqual(0, self.cursor_mock.execute.call_count)
        self.assertEqual(0, self.cursor_mock.close.call_count)


    def test_it_should_create_database_and_version_table_on_init_if_not_exists(self):
        MySQL(self.config_mock, self.db_driver_mock)

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(4, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(3, self.cursor_mock.close.call_count)

    def test_it_should_drop_database_on_init_if_its_asked(self):
        self.config_dict["drop_db_first"] = True

        MySQL(self.config_mock, self.db_driver_mock)

        expected_query_calls = [
            call('set foreign_key_checks=0; drop database if exists `migration_test`;'),
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(3, self.cursor_mock.close.call_count)

    def test_it_should_stop_process_when_an_error_occur_during_drop_database(self):
        self.config_dict["drop_db_first"] = True
        self.db_mock.query.side_effect = Exception("error when dropping")

        try:
            MySQL(self.config_mock, self.db_driver_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("can't drop database 'migration_test'; \nerror when dropping", str(e))

        expected_query_calls = [
            call('set foreign_key_checks=0; drop database if exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.assertEqual(0, self.db_mock.commit.call_count)
        self.assertEqual(1, self.db_mock.close.call_count)

        self.assertEqual(0, self.cursor_mock.execute.call_count)
        self.assertEqual(0, self.cursor_mock.close.call_count)

    def test_it_should_execute_migration_up_and_update_schema_version(self):
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        mysql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;")

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('create table spam()'),
            call('insert into __db_version__ (version, label, name, sql_up, sql_down) values ("20090212112104", NULL, "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;");')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)

    def test_it_should_execute_migration_down_and_update_schema_version(self):
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        mysql.change("drop table spam;", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", False)

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('drop table spam'),
            call('delete from __db_version__ where version = "20090212112104";')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)

    def test_it_should_use_label_version_when_updating_schema_version(self):
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        mysql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('create table spam()'),
            call('insert into __db_version__ (version, label, name, sql_up, sql_down) values ("20090212112104", "label", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;");')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)

    def test_it_should_raise_whem_migration_sql_has_a_syntax_error(self):
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        self.assertRaisesWithMessage(Exception, "error executing migration: invalid sql syntax 'create table foo(); create table spam());'", mysql.change,
                                     "create table foo(); create table spam());", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table foo(); create table spam());", "drop table spam;", label_version="label")

    def test_it_should_stop_process_when_an_error_occur_during_database_change(self):
        self.execute_returns["insert into spam"] = Exception("invalid sql")

        try:
            mysql = MySQL(self.config_mock, self.db_driver_mock)
            mysql.change("create table spam(); insert into spam", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")
        except Exception, e:
            self.assertEqual("error executing migration: invalid sql\n\n[ERROR DETAILS] SQL command was:\ninsert into spam", str(e))
            self.assertTrue(isinstance(e, simple_db_migrate.core.exceptions.MigrationException))

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(1, self.db_mock.rollback.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('create table spam()'),
            call('insert into spam')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(3, self.cursor_mock.close.call_count)

    def test_it_should_stop_process_when_an_error_occur_during_log_schema_version(self):
        self.execute_returns['insert into __db_version__ (version, label, name, sql_up, sql_down) values ("20090212112104", "label", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;");'] = Exception("invalid sql")

        try:
            mysql = MySQL(self.config_mock, self.db_driver_mock)
            mysql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")
        except Exception, e:
            self.assertEqual('error logging migration: invalid sql\n\n[ERROR DETAILS] SQL command was:\n20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration', str(e))
            self.assertTrue(isinstance(e, simple_db_migrate.core.exceptions.MigrationException))

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(1, self.db_mock.rollback.call_count)
        self.assertEqual(3, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('create table spam()'),
            call('insert into __db_version__ (version, label, name, sql_up, sql_down) values ("20090212112104", "label", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;");')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_log_execution_when_a_function_is_given_when_updating_schema_version(self):
        execution_log_mock = Mock()
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        mysql.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", execution_log=execution_log_mock)

        expected_execution_log_calls = [
            call('create table spam()\n-- 0 row(s) affected\n'),
            call('migration 20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration registered\n')
        ]
        self.assertEqual(expected_execution_log_calls, execution_log_mock.mock_calls)

    def test_it_should_get_current_schema_version(self):
        self.fetchone_returns = {'select count(*) from __db_version__;': [0], 'select version from __db_version__ order by id desc limit 0,1;': ["0"]}

        mysql = MySQL(self.config_mock, self.db_driver_mock)
        self.assertEqual("0", mysql.get_current_schema_version())

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('select version from __db_version__ order by id desc limit 0,1;')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_all_schema_versions(self):
        expected_versions = []
        expected_versions.append("0")
        expected_versions.append("20090211120001")
        expected_versions.append("20090211120002")
        expected_versions.append("20090211120003")

        self.cursor_mock.fetchall.return_value = tuple(zip(expected_versions))

        mysql = MySQL(self.config_mock, self.db_driver_mock)
        schema_versions = mysql.get_all_schema_versions()

        self.assertEquals(len(expected_versions), len(schema_versions))
        for version in schema_versions:
            self.assertTrue(version in expected_versions)

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('select version from __db_version__ order by id;')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_all_schema_migrations(self):
        expected_versions = []
        expected_versions.append([1, "0", None, None, None, None])
        expected_versions.append([2, "20090211120001", "label", "20090211120001_name", "sql_up", "sql_down"])

        self.cursor_mock.fetchall.return_value = tuple(expected_versions)

        mysql = MySQL(self.config_mock, self.db_driver_mock)
        schema_migrations = mysql.get_all_schema_migrations()

        self.assertEquals(len(expected_versions), len(schema_migrations))
        for index, migration in enumerate(schema_migrations):
            self.assertEqual(migration.id, expected_versions[index][0])
            self.assertEqual(migration.version, expected_versions[index][1])
            self.assertEqual(migration.label, expected_versions[index][2])
            self.assertEqual(migration.file_name, expected_versions[index][3])
            self.assertEqual(migration.sql_up, expected_versions[index][4] and expected_versions[index][4] or "")
            self.assertEqual(migration.sql_down, expected_versions[index][5] and expected_versions[index][5] or "")

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call('select id, version, label, name, sql_up, sql_down from __db_version__ order by id;')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_parse_sql_statements(self):
        statements = MySQL._parse_sql_statements('; ; create table eggs; drop table spam; ; ;')

        self.assertEqual(2, len(statements))
        self.assertEqual('create table eggs', statements[0])
        self.assertEqual('drop table spam', statements[1])

    def test_it_should_parse_sql_statements_with_html_inside(self):
        sql = u"""
        create table eggs;
        INSERT INTO widget_parameter_domain (widget_parameter_id, label, value)
        VALUES ((SELECT MAX(widget_parameter_id)
                FROM widget_parameter),  "Carros", '<div class="box-zap-geral">

            <div class="box-zap box-zap-autos">
                <a class="logo" target="_blank" title="ZAP" href="http://www.zap.com.br/Parceiros/g1/RedirG1.aspx?CodParceriaLink=42&amp;URL=http://www.zap.com.br">');
        drop table spam;
        """
        statements = MySQL._parse_sql_statements(sql)

        expected_sql_with_html = """INSERT INTO widget_parameter_domain (widget_parameter_id, label, value)
        VALUES ((SELECT MAX(widget_parameter_id)
                FROM widget_parameter),  "Carros", '<div class="box-zap-geral">

            <div class="box-zap box-zap-autos">
                <a class="logo" target="_blank" title="ZAP" href="http://www.zap.com.br/Parceiros/g1/RedirG1.aspx?CodParceriaLink=42&amp;URL=http://www.zap.com.br">')"""

        self.assertEqual(3, len(statements))
        self.assertEqual('create table eggs', statements[0])
        self.assertEqual(expected_sql_with_html, statements[1])
        self.assertEqual('drop table spam', statements[2])

    def test_it_should_get_none_for_a_non_existent_version_in_database(self):
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        ret = mysql.get_version_id_from_version_number('xxx')
        self.assertEqual(None, ret)

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call("select id from __db_version__ where version = 'xxx' order by id desc;")
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_most_recent_version_for_a_existent_label_in_database(self):
        self.fetchone_returns["select version from __db_version__ where label = 'xxx' order by id desc"] = ["vesion", "version2", "version3"]
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        ret = mysql.get_version_number_from_label('xxx')
        self.assertEqual("vesion", ret)

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call("select version from __db_version__ where label = 'xxx' order by id desc")
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_none_for_a_non_existent_label_in_database(self):
        mysql = MySQL(self.config_mock, self.db_driver_mock)
        ret = mysql.get_version_number_from_label('xxx')
        self.assertEqual(None, ret)

        expected_query_calls = [
            call('create database if not exists `migration_test`;')
        ]
        self.assertEqual(expected_query_calls, self.db_mock.query.mock_calls)
        self.db_mock.select_db.assert_called_with('migration_test')
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create table if not exists __db_version__ ( id int(11) NOT NULL AUTO_INCREMENT, version varchar(20) NOT NULL default "0", label varchar(255), name varchar(255), sql_up LONGTEXT, sql_down LONGTEXT, PRIMARY KEY (id))'),
            call('select count(*) from __db_version__;'),
            call('insert into __db_version__ (version) values ("0")'),
            call("select version from __db_version__ where label = 'xxx' order by id desc")
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def side_effect(self, returns, default_value):
        result = returns.get(self.last_execute_command, default_value)
        if isinstance(result, Exception):
            raise result
        return result

    def execute_side_effect(self, *args):
        self.last_execute_command = args[0]
        return self.side_effect(self.execute_returns, 0)

    def fetchone_side_effect(self, *args):
        return self.side_effect(self.fetchone_returns, None)

    def close_side_effect(self, *args):
        return self.side_effect(self.close_returns, None)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = oracle_test
#-*- coding:utf-8 -*-
import unittest
import sys
import simple_db_migrate.core
from mock import patch, Mock, MagicMock, call, sentinel
from simple_db_migrate.oracle import Oracle
from tests import BaseTest

class OracleTest(BaseTest):

    def setUp(self):
        super(OracleTest, self).setUp()
        self.execute_returns = {}
        self.fetchone_returns = {'select count(*) from db_version': [0]}
        self.close_returns = {}
        self.last_execute_command = '';
        self.config_dict = {'database_script_encoding': 'utf8',
                   'database_encoding': 'American_America.UTF8',
                   'database_host': 'somehost',
                   'database_user': 'root',
                   'database_password': 'migration_test',
                   'database_name': 'SID',
                   'database_version_table': 'db_version',
                   'drop_db_first': False
                }

        self.config_mock = MagicMock(spec_set=dict, wraps=self.config_dict)
        self.cursor_mock = Mock(**{"execute": Mock(side_effect=self.execute_side_effect),
                                   "close": Mock(side_effect=self.close_side_effect),
                                   "fetchone": Mock(side_effect=self.fetchone_side_effect),
                                   "rowcount": 0})
        self.db_mock = Mock(**{"cursor.return_value": self.cursor_mock})
        self.db_driver_mock = Mock(**{"connect.return_value": self.db_mock})
        self.stdin_mock = Mock(**{"readline.return_value":"dba_user"})
        self.getpass_mock = Mock(return_value = "dba_password")

    @patch.dict('sys.modules', cx_Oracle=MagicMock())
    def test_it_should_use_cx_Oracle_as_driver(self):
        Oracle(self.config_mock)
        self.assertNotEqual(0, sys.modules['cx_Oracle'].connect.call_count)

    @patch.dict('sys.modules', cx_Oracle=MagicMock())
    def test_it_should_use_default_port(self):
        sys.modules['cx_Oracle'].makedsn.side_effect = self.makedsn_side_effect
        Oracle(self.config_mock)
        self.assertEqual(call(dsn="(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=somehost)(PORT=1521)))(CONNECT_DATA=(SID=SID)))", password='migration_test', user='root'), sys.modules['cx_Oracle'].connect.call_args)

    @patch.dict('sys.modules', cx_Oracle=MagicMock())
    def test_it_should_use_given_configuration(self):
        sys.modules['cx_Oracle'].makedsn.side_effect = self.makedsn_side_effect
        self.config_dict['database_port'] = 9876
        Oracle(self.config_mock)
        self.assertEqual(call(dsn="(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=somehost)(PORT=9876)))(CONNECT_DATA=(SID=SID)))", password='migration_test', user='root'), sys.modules['cx_Oracle'].connect.call_args)

    @patch.dict('sys.modules', cx_Oracle=MagicMock())
    def test_it_should_use_database_name_as_dsn_when_database_host_is_not_set(self):
        self.config_dict['database_host'] = None
        Oracle(self.config_mock)
        self.assertEqual(call(dsn='SID', password='migration_test', user='root'), sys.modules['cx_Oracle'].connect.call_args)

    def test_it_should_stop_process_when_an_error_occur_during_connect_database(self):
        self.db_driver_mock.connect.side_effect = Exception("error when connecting")

        try:
            Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("could not connect to database: error when connecting", str(e))

        self.assertEqual(0, self.db_mock.commit.call_count)
        self.assertEqual(0, self.db_mock.close.call_count)

        self.assertEqual(0, self.cursor_mock.execute.call_count)
        self.assertEqual(0, self.cursor_mock.close.call_count)

    def test_it_should_create_database_and_version_table_on_init_if_not_exists(self):
        self.first_return = Exception("could not connect to database: ORA-01017 invalid user/password")
        def connect_side_effect(*args, **kwargs):
            ret = sentinel.DEFAULT
            if (kwargs['user'] == 'root') and self.first_return:
                ret = self.first_return
                self.first_return = None
                raise ret
            return ret

        self.db_driver_mock.connect.side_effect = connect_side_effect
        self.execute_returns["select version from db_version"] = Exception("Table doesn't exist")

        Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)

        self.assertEqual(8, self.db_driver_mock.connect.call_count)
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(7, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('create user root identified by migration_test'),
            call('grant connect, resource to root'),
            call('grant create public synonym to root'),
            call('grant drop public synonym to root'),
            call('select version from db_version'),
            call("create table db_version ( id number(11) not null, version varchar2(20) default '0' NOT NULL, label varchar2(255), name varchar2(255), sql_up clob, sql_down clob, CONSTRAINT db_version_pk PRIMARY KEY (id) ENABLE)"),
            call('drop sequence db_version_seq'),
            call('create sequence db_version_seq start with 1 increment by 1 nomaxvalue'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')")
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(7, self.cursor_mock.close.call_count)

    def test_it_should_create_version_table_on_init_if_not_exists(self):
        self.execute_returns["select version from db_version"] = Exception("Table doesn't exist")

        Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)

        self.assertEqual(7, self.db_driver_mock.connect.call_count)
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(7, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call("create table db_version ( id number(11) not null, version varchar2(20) default '0' NOT NULL, label varchar2(255), name varchar2(255), sql_up clob, sql_down clob, CONSTRAINT db_version_pk PRIMARY KEY (id) ENABLE)"),
            call('drop sequence db_version_seq'),
            call('create sequence db_version_seq start with 1 increment by 1 nomaxvalue'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')")
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(6, self.cursor_mock.close.call_count)

    def test_it_should_drop_database_on_init_if_its_asked(self):
        select_elements_to_drop_sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % ('ROOT','ROOT','ROOT')

        self.config_dict["drop_db_first"] = True
        self.cursor_mock.fetchall.return_value = [("DELETE TABLE DB_VERSION CASCADE CONSTRAINTS;",),]
        self.execute_returns["select version from db_version"] = Exception("Table doesn't exist")

        Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)

        self.assertEqual(9, self.db_driver_mock.connect.call_count)
        self.assertEqual(5, self.db_mock.commit.call_count)
        self.assertEqual(9, self.db_mock.close.call_count)

        expected_execute_calls = [
            call(select_elements_to_drop_sql),
            call('DELETE TABLE DB_VERSION CASCADE CONSTRAINTS'),
            call('select version from db_version'),
            call("create table db_version ( id number(11) not null, version varchar2(20) default '0' NOT NULL, label varchar2(255), name varchar2(255), sql_up clob, sql_down clob, CONSTRAINT db_version_pk PRIMARY KEY (id) ENABLE)"),
            call('drop sequence db_version_seq'),
            call('create sequence db_version_seq start with 1 increment by 1 nomaxvalue'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')")
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(8, self.cursor_mock.close.call_count)

    def test_it_should_create_user_when_it_does_not_exists_during_drop_database_selecting_elements_to_drop(self):
        select_elements_to_drop_sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % ('ROOT','ROOT','ROOT')

        self.config_dict["drop_db_first"] = True
        self.execute_returns[select_elements_to_drop_sql] = Exception("could not connect to database: ORA-01017 invalid user/password")

        Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)

        self.assertEqual(6, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call(select_elements_to_drop_sql),
            call('create user root identified by migration_test'),
            call('grant connect, resource to root'),
            call('grant create public synonym to root'),
            call('grant drop public synonym to root'),
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')")
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)

    def test_it_should_stop_process_when_an_error_occur_during_create_user(self):
        select_elements_to_drop_sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % ('ROOT','ROOT','ROOT')

        self.config_dict["drop_db_first"] = True
        self.execute_returns[select_elements_to_drop_sql] = Exception("could not connect to database: ORA-01017 invalid user/password")
        self.execute_returns['grant create public synonym to root'] = Exception("error when granting")

        try:
            Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("check error: error when granting", str(e))

        self.assertEqual(2, self.db_driver_mock.connect.call_count)
        self.assertEqual(0, self.db_mock.commit.call_count)
        self.assertEqual(2, self.db_mock.close.call_count)

        expected_execute_calls = [
            call(select_elements_to_drop_sql),
            call('create user root identified by migration_test'),
            call('grant connect, resource to root'),
            call('grant create public synonym to root')
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(2, self.cursor_mock.close.call_count)

    def test_it_should_stop_process_when_an_error_occur_during_drop_database_selecting_elements_to_drop(self):
        select_elements_to_drop_sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % ('ROOT','ROOT','ROOT')

        self.config_dict["drop_db_first"] = True
        self.execute_returns[select_elements_to_drop_sql] = Exception("error when dropping")

        try:
            Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("error when dropping", str(e))

        self.assertEqual(0, self.db_mock.commit.call_count)
        self.assertEqual(1, self.db_mock.close.call_count)

        expected_execute_calls = [
            call(select_elements_to_drop_sql)
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(1, self.cursor_mock.close.call_count)

    def test_it_should_stop_process_when_an_error_occur_during_drop_elements_from_database_and_user_asked_to_stop(self):
        select_elements_to_drop_sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % ('ROOT','ROOT','ROOT')

        self.config_dict["drop_db_first"] = True
        self.cursor_mock.fetchall.return_value = [("DELETE TABLE DB_VERSION CASCADE CONSTRAINTS;",),("DELETE TABLE AUX CASCADE CONSTRAINTS;",)]
        self.execute_returns["DELETE TABLE DB_VERSION CASCADE CONSTRAINTS"] = Exception("error dropping table")
        self.stdin_mock.readline.return_value = "n"

        try:
            Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
            self.fail("it should not get here")
        except Exception, e:
            self.assertEqual("can't drop database objects for user 'root'", str(e))

        self.assertEqual(1, self.db_mock.commit.call_count)
        self.assertEqual(3, self.db_mock.close.call_count)

        expected_execute_calls = [
            call(select_elements_to_drop_sql),
            call('DELETE TABLE DB_VERSION CASCADE CONSTRAINTS'),
            call('DELETE TABLE AUX CASCADE CONSTRAINTS')
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(3, self.cursor_mock.close.call_count)

    def test_it_should_not_stop_process_when_an_error_occur_during_drop_elements_from_database_and_user_asked_to_continue(self):
        select_elements_to_drop_sql = """\
            SELECT 'DROP PUBLIC SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = 'PUBLIC' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP SYNONYM ' || SYNONYM_NAME ||';' FROM ALL_SYNONYMS \
            WHERE OWNER = '%s' AND TABLE_OWNER = '%s' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||';'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE <> 'TABLE' AND OBJECT_TYPE <> 'INDEX' AND \
            OBJECT_TYPE<>'TRIGGER'  AND OBJECT_TYPE<>'LOB' \
            UNION ALL \
            SELECT 'DROP ' || OBJECT_TYPE || ' ' || OBJECT_NAME ||' CASCADE CONSTRAINTS;'   FROM USER_OBJECTS \
            WHERE OBJECT_TYPE = 'TABLE' AND OBJECT_NAME NOT LIKE 'BIN$%%'""" % ('ROOT','ROOT','ROOT')

        self.config_dict["drop_db_first"] = True
        self.cursor_mock.fetchall.return_value = [("DELETE TABLE DB_VERSION CASCADE CONSTRAINTS;",),("DELETE TABLE AUX CASCADE CONSTRAINTS;",)]
        self.execute_returns["DELETE TABLE DB_VERSION CASCADE CONSTRAINTS"] = Exception("error dropping table")
        self.stdin_mock.readline.return_value = "y"

        Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)

        self.assertEqual(3, self.db_mock.commit.call_count)
        self.assertEqual(7, self.db_mock.close.call_count)

        expected_execute_calls = [
            call(select_elements_to_drop_sql),
            call('DELETE TABLE DB_VERSION CASCADE CONSTRAINTS'),
            call('DELETE TABLE AUX CASCADE CONSTRAINTS'),
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')")
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(6, self.cursor_mock.close.call_count)

    def test_it_should_execute_migration_up_and_update_schema_version(self):
        self.db_driver_mock.CLOB = 'X'

        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        oracle.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;")

        self.assertEqual(6, self.db_driver_mock.connect.call_count)
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('create table spam()'),
            call('insert into db_version (id, version, label, name, sql_up, sql_down) values (db_version_seq.nextval, :version, :label, :migration_file_name, :sql_up, :sql_down)', {'label': None, 'sql_up': 'create table spam();', 'version': '20090212112104', 'sql_down': 'drop table spam;', 'migration_file_name': '20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration'})
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)

        expected_var_calls = [
            call('X', 20),
            call().setvalue(0, 'create table spam();'),
            call('X', 16),
            call().setvalue(0, 'drop table spam;')
        ]
        self.assertEqual(expected_var_calls, self.cursor_mock.var.mock_calls)

    def test_it_should_execute_migration_down_and_update_schema_version(self):
        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        oracle.change("drop table spam;", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", False)

        self.assertEqual(6, self.db_driver_mock.connect.call_count)
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('drop table spam'),
            call('delete from db_version where version = :version', {'version': '20090212112104'})
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)


    def test_it_should_use_label_version_when_updating_schema_version(self):
        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        oracle.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")

        self.assertEqual(6, self.db_driver_mock.connect.call_count)
        self.assertEqual(4, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('create table spam()'),
            call('insert into db_version (id, version, label, name, sql_up, sql_down) values (db_version_seq.nextval, :version, :label, :migration_file_name, :sql_up, :sql_down)', {'label': "label", 'sql_up': 'create table spam();', 'version': '20090212112104', 'sql_down': 'drop table spam;', 'migration_file_name': '20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration'})
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(5, self.cursor_mock.close.call_count)

    def test_it_should_raise_whem_migration_sql_has_a_syntax_error(self):
        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        self.assertRaisesWithMessage(Exception, "error executing migration: invalid sql syntax 'create table foo(); create table spam());'", oracle.change,
                                     "create table foo(); create table spam());", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam());", "drop table spam;", label_version="label")

    def test_it_should_stop_process_when_an_error_occur_during_database_change(self):
        self.execute_returns["insert into spam"] = Exception("invalid sql")

        try:
            oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
            oracle.change("create table spam(); insert into spam", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")
        except Exception, e:
            self.assertEqual("error executing migration: invalid sql\n\n[ERROR DETAILS] SQL command was:\ninsert into spam", str(e))
            self.assertTrue(isinstance(e, simple_db_migrate.core.exceptions.MigrationException))

        self.assertEqual(1, self.db_mock.rollback.call_count)
        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('create table spam()'),
            call('insert into spam')
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_stop_process_when_an_error_occur_during_log_schema_version(self):
        self.execute_returns['insert into db_version (id, version, label, name, sql_up, sql_down) values (db_version_seq.nextval, :version, :label, :migration_file_name, :sql_up, :sql_down)'] = Exception("invalid sql")

        try:
            oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
            oracle.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", label_version="label")
        except Exception, e:
            self.assertEqual('error logging migration: invalid sql\n\n[ERROR DETAILS] SQL command was:\n20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration', str(e))
            self.assertTrue(isinstance(e, simple_db_migrate.core.exceptions.MigrationException))

        self.assertEqual(6, self.db_driver_mock.connect.call_count)
        self.assertEqual(1, self.db_mock.rollback.call_count)
        self.assertEqual(3, self.db_mock.commit.call_count)
        self.assertEqual(6, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('create table spam()'),
            call('insert into db_version (id, version, label, name, sql_up, sql_down) values (db_version_seq.nextval, :version, :label, :migration_file_name, :sql_up, :sql_down)', {'label': 'label', 'sql_up': 'create table spam();', 'version': '20090212112104', 'sql_down': 'drop table spam;', 'migration_file_name': '20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration'})
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_log_execution_when_a_function_is_given_when_updating_schema_version(self):
        execution_log_mock = Mock()
        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        oracle.change("create table spam();", "20090212112104", "20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration", "create table spam();", "drop table spam;", execution_log=execution_log_mock)

        expected_execution_log_calls = [
            call('create table spam()\n-- 0 row(s) affected\n'),
            call('migration 20090212112104_test_it_should_execute_migration_down_and_update_schema_version.migration registered\n')
        ]
        self.assertEqual(expected_execution_log_calls, execution_log_mock.mock_calls)


    def test_it_should_get_current_schema_version(self):
        self.fetchone_returns = {'select count(*) from db_version': [0], 'select version from db_version order by id desc': ["0"]}

        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        self.assertEquals("0", oracle.get_current_schema_version())


        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('select version from db_version order by id desc')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_all_schema_versions(self):
        expected_versions = []
        expected_versions.append("0")
        expected_versions.append("20090211120001")
        expected_versions.append("20090211120002")
        expected_versions.append("20090211120003")

        self.cursor_mock.fetchall.return_value = tuple(zip(expected_versions))

        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        schema_versions = oracle.get_all_schema_versions()

        self.assertEquals(len(expected_versions), len(schema_versions))
        for version in schema_versions:
            self.assertTrue(version in expected_versions)

        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('select version from db_version order by id')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_all_schema_migrations(self):
        expected_versions = []
        expected_versions.append([1, "0", None, None, None, None])
        expected_versions.append([2, "20090211120001", "label", "20090211120001_name", Mock(**{"read.return_value":"sql_up"}), Mock(**{"read.return_value":"sql_down"})])

        self.cursor_mock.fetchall.return_value = tuple(expected_versions)

        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        schema_migrations = oracle.get_all_schema_migrations()

        self.assertEquals(len(expected_versions), len(schema_migrations))
        for index, migration in enumerate(schema_migrations):
            self.assertEqual(migration.id, expected_versions[index][0])
            self.assertEqual(migration.version, expected_versions[index][1])
            self.assertEqual(migration.label, expected_versions[index][2])
            self.assertEqual(migration.file_name, expected_versions[index][3])
            self.assertEqual(migration.sql_up, expected_versions[index][4] and expected_versions[index][4].read() or "")
            self.assertEqual(migration.sql_down, expected_versions[index][5] and expected_versions[index][5].read() or "")

        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call('select id, version, label, name, sql_up, sql_down from db_version order by id')
        ]
        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)


    def test_it_should_parse_sql_statements(self):
        #TODO include other types of sql
        sql = "create table eggs; drop table spam; ; ;\
        CREATE OR REPLACE FUNCTION simple \n\
        RETURN VARCHAR2 IS \n\
        BEGIN \n\
        RETURN 'Simple Function'; \n\
        END simple; \n\
        / \n\
        drop table eggs; \n\
        create or replace procedure proc_db_migrate(dias_fim_mes out number) \n\
        as v number; \n\
        begin \n\
            SELECT LAST_DAY(SYSDATE) - SYSDATE \"Days Left\" \n\
            into v \n\
            FROM DUAL; \n\
            dias_fim_mes := v; \n\
        end; \n\
        \t/      \n\
        create OR RePLaCe TRIGGER \"FOLDER_TR\" \n\
        BEFORE INSERT ON \"FOLDER\" \n\
        FOR EACH ROW WHEN \n\
        (\n\
            new.\"FOLDER_ID\" IS NULL \n\
        )\n\
        BEGIN\n\
            SELECT \"FOLDER_SQ\".nextval\n\
            INTO :new.\"FOLDER_ID\"\n\
            FROM dual;\n\
        EnD;\n\
        /\n\
        CREATE OR REPLACE\t PACKAGE pkg_dbm \n\
        AS \n\
        FUNCTION getArea (i_rad NUMBER) \n\
        RETURN NUMBER;\n\
            PROCEDURE p_print (i_str1 VARCHAR2 := 'hello',\n\
            i_str2 VARCHAR2 := 'world', \n\
            i_end VARCHAR2 := '!');\n\
        END;\n\
        / \n\
        CREATE OR REPLACE\n PACKAGE BODY pkg_dbm \n\
        AS \n\
            FUNCTION getArea (i_rad NUMBER) \n\
            RETURN NUMBER \n\
            IS \n\
                v_pi NUMBER := 3.14; \n\
            BEGIN \n\
                RETURN v_pi * (i_rad ** 2); \n\
            END; \n\
            PROCEDURE p_print (i_str1 VARCHAR2 := 'hello', i_str2 VARCHAR2 := 'world', i_end VARCHAR2 := '!') \n\
            IS \n\
            BEGIN \n\
                DBMS_OUTPUT.put_line (i_str1 || ',' || i_str2 || i_end); \n\
            END; \n\
        END; \n\
        / \n\
        DECLARE\n\
            counter NUMBER(10,8) := 2; \r\n\
            pi NUMBER(8,7) := 3.1415926; \n\
            test NUMBER(10,8) NOT NULL := 10;\n\
        BEGIN \n\
            counter := pi/counter; \n\
            pi := pi/3; \n\
            dbms_output.put_line(counter); \n\
            dbms_output.put_line(pi); \n\
        END; \n\
        / \n\
        BEGIN \n\
            dbms_output.put_line('teste de bloco anonimo'); \n\
            dbms_output.put_line(select 1 from dual); \n\
        END; \n\
        / "

        statements = Oracle._parse_sql_statements(sql)

        self.assertEqual(10, len(statements))
        self.assertEqual('create table eggs', statements[0])
        self.assertEqual('drop table spam', statements[1])
        self.assertEqual("CREATE OR REPLACE FUNCTION simple \n\
        RETURN VARCHAR2 IS \n\
        BEGIN \n\
        RETURN 'Simple Function'; \n\
        END simple;", statements[2])
        self.assertEqual('drop table eggs', statements[3])
        self.assertEqual('create or replace procedure proc_db_migrate(dias_fim_mes out number) \n\
        as v number; \n\
        begin \n\
            SELECT LAST_DAY(SYSDATE) - SYSDATE \"Days Left\" \n\
            into v \n\
            FROM DUAL; \n\
            dias_fim_mes := v; \n\
        end;', statements[4])
        self.assertEqual('create OR RePLaCe TRIGGER \"FOLDER_TR\" \n\
        BEFORE INSERT ON \"FOLDER\" \n\
        FOR EACH ROW WHEN \n\
        (\n\
            new.\"FOLDER_ID\" IS NULL \n\
        )\n\
        BEGIN\n\
            SELECT \"FOLDER_SQ\".nextval\n\
            INTO :new.\"FOLDER_ID\"\n\
            FROM dual;\n\
        EnD;', statements[5])
        self.assertEqual("CREATE OR REPLACE\t PACKAGE pkg_dbm \n\
        AS \n\
        FUNCTION getArea (i_rad NUMBER) \n\
        RETURN NUMBER;\n\
            PROCEDURE p_print (i_str1 VARCHAR2 := 'hello',\n\
            i_str2 VARCHAR2 := 'world', \n\
            i_end VARCHAR2 := '!');\n\
        END;", statements[6])
        self.assertEqual("CREATE OR REPLACE\n PACKAGE BODY pkg_dbm \n\
        AS \n\
            FUNCTION getArea (i_rad NUMBER) \n\
            RETURN NUMBER \n\
            IS \n\
                v_pi NUMBER := 3.14; \n\
            BEGIN \n\
                RETURN v_pi * (i_rad ** 2); \n\
            END; \n\
            PROCEDURE p_print (i_str1 VARCHAR2 := 'hello', i_str2 VARCHAR2 := 'world', i_end VARCHAR2 := '!') \n\
            IS \n\
            BEGIN \n\
                DBMS_OUTPUT.put_line (i_str1 || ',' || i_str2 || i_end); \n\
            END; \n\
        END;", statements[7])
        self.assertEqual("DECLARE\n\
            counter NUMBER(10,8) := 2; \r\n\
            pi NUMBER(8,7) := 3.1415926; \n\
            test NUMBER(10,8) NOT NULL := 10;\n\
        BEGIN \n\
            counter := pi/counter; \n\
            pi := pi/3; \n\
            dbms_output.put_line(counter); \n\
            dbms_output.put_line(pi); \n\
        END;", statements[8])
        self.assertEqual("BEGIN \n\
            dbms_output.put_line('teste de bloco anonimo'); \n\
            dbms_output.put_line(select 1 from dual); \n\
        END;", statements[9])

    def test_it_should_remove_comments_when_parse_sql_statments(self):
        sql = u"""-- Teste Migration 1  $ > < = @ # ( comentários -- )
            -- Teste Migration 1 ( comentários na outra linha -- ) */
            DELETE --+ Teste Migration
            FROM TABLE TEST_MIGRATION;
            CREATE TABLE DB_ARQ.TESTE_MIGRATION
            (
                id_teste INT,-- Teste Migration 1 ( comentários -- )
                nome_teste VARCHAR2 (30)
            );-- Teste Migration 1 ( comentários -- )
            INSERT INTO TESTE_MIGRATION VALUES (1, '-- comentário $ > < = @ # no insert');
            -- Teste Migration 1 ( comentários -- )
-- Teste Migration 1 ( comentários -- )"""

        expected_sql_0 = u"""DELETE --+ Teste Migration
            FROM TABLE TEST_MIGRATION"""

        expected_sql_1 = u"""CREATE TABLE DB_ARQ.TESTE_MIGRATION
            (
                id_teste INT,
                nome_teste VARCHAR2 (30)
            )"""

        expected_sql_2 = u"""INSERT INTO TESTE_MIGRATION VALUES (1, '-- comentário $ > < = @ # no insert')"""

        statements = Oracle._parse_sql_statements(sql)

        self.assertEqual(3, len(statements))
        self.assertEqual(expected_sql_0, statements[0])
        self.assertEqual(expected_sql_1, statements[1])
        self.assertEqual(expected_sql_2, statements[2])

        sql = u"""/* Teste Migration 2 ( comentário * ) */
            /*Teste Migration 2  $ > < = @ # ( comentário * )*/
            /* Teste Migration 2
            ( comentário * ) */
            DELETE /*+ Teste Migration */ FROM TEST_MIGRATION;
            CREATE TABLE DB_ARQ.TESTE_MIGRATION
            (/* Teste Migration 2
                ( comentário * ) */
                id_teste INT,
                nome_teste VARCHAR2 (30)
            );/* Teste Migration 2 ( comentário * ) */
            /*Teste Migration 2 ( comentário * ) */
            INSERT INTO TESTE_MIGRATION VALUES (1, '/* comentário $ > < = @ # no insert*/');
            /* Teste Migration 2
            ( comentário * ) */
/* Teste Migration 2 ( comentário * ) */"""

        statements = Oracle._parse_sql_statements(sql)

        expected_sql_0 = u"""DELETE /*+ Teste Migration */ FROM TEST_MIGRATION"""

        expected_sql_2 = u"""INSERT INTO TESTE_MIGRATION VALUES (1, '/* comentário $ > < = @ # no insert*/')"""

        self.assertEqual(3, len(statements))
        self.assertEqual(expected_sql_0, statements[0])
        self.assertEqual(expected_sql_1, statements[1])
        self.assertEqual(expected_sql_2, statements[2])


    def test_it_should_parse_sql_statements_with_html_inside(self):

        sql = u"""
        create table eggs;
        INSERT INTO widget_parameter_domain (widget_parameter_id, label, value)
        VALUES ((SELECT MAX(widget_parameter_id)
                FROM widget_parameter),  "Carros", '<div class="box-zap-geral">

            <div class="box-zap box-zap-autos">
                <a class="logo" target="_blank" title="ZAP" href="http://www.zap.com.br/Parceiros/g1/RedirG1.aspx?CodParceriaLink=42&amp;URL=http://www.zap.com.br">');
        drop table spam;
        """
        statements = Oracle._parse_sql_statements(sql)

        expected_sql_with_html = """INSERT INTO widget_parameter_domain (widget_parameter_id, label, value)
        VALUES ((SELECT MAX(widget_parameter_id)
                FROM widget_parameter),  "Carros", '<div class="box-zap-geral">

            <div class="box-zap box-zap-autos">
                <a class="logo" target="_blank" title="ZAP" href="http://www.zap.com.br/Parceiros/g1/RedirG1.aspx?CodParceriaLink=42&amp;URL=http://www.zap.com.br">')"""

        self.assertEqual(3, len(statements))
        self.assertEqual('create table eggs', statements[0])
        self.assertEqual(expected_sql_with_html, statements[1])
        self.assertEqual('drop table spam', statements[2])

    def test_it_should_get_none_for_a_non_existent_version_in_database(self):
        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        ret = oracle.get_version_id_from_version_number('xxx')

        self.assertEqual(None, ret)

        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call("select id from db_version where version = 'xxx' order by id desc")
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_most_recent_version_for_a_existent_label_in_database(self):
        self.fetchone_returns["select version from db_version where label = 'xxx' order by id desc"] = ["vesion", "version2", "version3"]

        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        ret = oracle.get_version_number_from_label('xxx')

        self.assertEqual("vesion", ret)

        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call("select version from db_version where label = 'xxx' order by id desc")
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def test_it_should_get_none_for_a_non_existent_label_in_database(self):
        oracle = Oracle(self.config_mock, self.db_driver_mock, self.getpass_mock, self.stdin_mock)
        ret = oracle.get_version_number_from_label('xxx')

        self.assertEqual(None, ret)

        self.assertEqual(5, self.db_driver_mock.connect.call_count)
        self.assertEqual(2, self.db_mock.commit.call_count)
        self.assertEqual(5, self.db_mock.close.call_count)

        expected_execute_calls = [
            call('select version from db_version'),
            call('select count(*) from db_version'),
            call("insert into db_version (id, version) values (db_version_seq.nextval, '0')"),
            call("select version from db_version where label = 'xxx' order by id desc")
        ]

        self.assertEqual(expected_execute_calls, self.cursor_mock.execute.mock_calls)
        self.assertEqual(4, self.cursor_mock.close.call_count)

    def side_effect(self, returns, default_value):
        result = returns.get(self.last_execute_command, default_value)
        if isinstance(result, Exception):
            raise result
        return result

    def execute_side_effect(self, *args):
        self.last_execute_command = args[0]
        return self.side_effect(self.execute_returns, 0)

    def fetchone_side_effect(self, *args):
        return self.side_effect(self.fetchone_returns, None)

    def close_side_effect(self, *args):
        return self.side_effect(self.close_returns, None)

    def makedsn_side_effect(self, host, port, sid):
        return "(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=%s)(PORT=%s)))(CONNECT_DATA=(SID=%s)))" % (host, port, sid)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = run_test
import unittest
import simple_db_migrate
import os
import sys
from StringIO import StringIO
from mock import patch, Mock

class RunTest(unittest.TestCase):

    def setUp(self):
        config_file = '''
DATABASE_HOST = os.getenv('DB_HOST') or 'localhost'
DATABASE_USER = os.getenv('DB_USERNAME') or 'root'
DATABASE_PASSWORD = os.getenv('DB_PASSWORD') or ''
DATABASE_NAME = os.getenv('DB_DATABASE') or 'migration_example'
ENV1_DATABASE_NAME = 'migration_example_env1'
DATABASE_MIGRATIONS_DIR = os.getenv('DATABASE_MIGRATIONS_DIR') or 'example'
UTC_TIMESTAMP = os.getenv("UTC_TIMESTAMP") or True
DATABASE_ANY_CUSTOM_VARIABLE = 'Some Value'
SOME_ENV_DATABASE_ANY_CUSTOM_VARIABLE = 'Other Value'
DATABASE_OTHER_CUSTOM_VARIABLE = 'Value'
'''
        f = open('sample.conf', 'w')
        f.write(config_file)
        f.close()
        self.stdout_mock = patch('sys.stdout', new_callable=StringIO)
        self.stdout_mock.start()

    def tearDown(self):
        os.remove('sample.conf')
        if os.path.exists('simple-db-migrate.conf'):
            os.remove('simple-db-migrate.conf')
        self.stdout_mock.stop()

    @patch('codecs.getwriter')
    @patch('sys.stdout', encoding='iso-8859-1')
    def test_it_should_ensure_stdout_is_using_an_utf8_encoding(self, stdout_mock, codecs_mock):
        new_stdout = Mock()
        codecs_mock.return_value = Mock(**{'return_value':new_stdout})

        reload(simple_db_migrate)

        codecs_mock.assert_called_with('utf-8')
        self.assertEqual(new_stdout, sys.stdout)

    @patch('sys.stdout', new_callable=object)
    def test_it_should_not_break_when_sys_stdout_has_not_encoding_property(self, stdout_mock):
        reload(simple_db_migrate)
        self.assertIs(stdout_mock, sys.stdout)

    def test_it_should_define_a_version_string(self):
        self.assertTrue(isinstance(simple_db_migrate.SIMPLE_DB_MIGRATE_VERSION, str))

    @patch('simple_db_migrate.cli.CLI.parse')
    def test_it_should_use_cli_to_parse_arguments(self, parse_mock):
        parse_mock.return_value = (Mock(simple_db_migrate_version=True), [])
        try:
            simple_db_migrate.run_from_argv()
        except SystemExit:
            pass

        parse_mock.assert_called_with(None)

    def test_it_should_print_simple_db_migrate_version_and_exit(self):
        try:
            simple_db_migrate.run_from_argv(["-v"])
        except SystemExit, e:
            self.assertEqual(0, e.code)

        self.assertEqual('simple-db-migrate v%s\n\n' % simple_db_migrate.SIMPLE_DB_MIGRATE_VERSION, sys.stdout.getvalue())

    @patch('simple_db_migrate.cli.CLI.show_colors')
    def test_it_should_activate_use_of_colors(self, show_colors_mock):
        try:
            simple_db_migrate.run_from_argv(["--color"])
        except SystemExit:
            pass

        self.assertEqual(1, show_colors_mock.call_count)

    @patch('simple_db_migrate.cli.CLI.show_colors')
    def test_it_should_print_message_and_exit_when_user_interrupt_execution(self, show_colors_mock):
        show_colors_mock.side_effect = KeyboardInterrupt()
        try:
            simple_db_migrate.run_from_argv(["--color"])
        except SystemExit, e:
            self.assertEqual(0, e.code)

        self.assertEqual('\nExecution interrupted by user...\n\n', sys.stdout.getvalue())

    @patch('simple_db_migrate.cli.CLI.show_colors')
    def test_it_should_print_message_and_exit_when_user_an_error_happen(self, show_colors_mock):
        show_colors_mock.side_effect = Exception('occur an error')
        try:
            simple_db_migrate.run_from_argv(["--color"])
        except SystemExit, e:
            self.assertEqual(1, e.code)

        self.assertEqual('[ERROR] occur an error\n\n', sys.stdout.getvalue())

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    @patch.object(simple_db_migrate.helpers.Utils, 'get_variables_from_file', return_value = {'DATABASE_HOST':'host', 'DATABASE_PORT':'1234', 'DATABASE_USER': 'root', 'DATABASE_PASSWORD':'', 'DATABASE_NAME':'database', 'DATABASE_MIGRATIONS_DIR':'.'})
    def test_it_should_read_configuration_file_using_fileconfig_class_and_execute_with_default_configuration(self, get_variables_from_file_mock, main_mock, execute_mock):
        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf')])

        get_variables_from_file_mock.assert_called_with(os.path.abspath('sample.conf'))

        self.assertEqual(1, execute_mock.call_count)
        execute_mock.assert_called_with()

        self.assertEqual(1, main_mock.call_count)
        config_used = main_mock.call_args[0][0]
        self.assertTrue(isinstance(config_used, simple_db_migrate.config.FileConfig))
        self.assertEqual('mysql', config_used.get('database_engine'))
        self.assertEqual('root', config_used.get('database_user'))
        self.assertEqual('', config_used.get('database_password'))
        self.assertEqual('database', config_used.get('database_name'))
        self.assertEqual('host', config_used.get('database_host'))
        self.assertEqual(1234, config_used.get('database_port'))
        self.assertEqual(False, config_used.get('utc_timestamp'))
        self.assertEqual('__db_version__', config_used.get('database_version_table'))
        self.assertEqual([os.path.abspath('.')], config_used.get("database_migrations_dir"))
        self.assertEqual(None, config_used.get('schema_version'))
        self.assertEqual(False, config_used.get('show_sql'))
        self.assertEqual(False, config_used.get('show_sql_only'))
        self.assertEqual(None, config_used.get('new_migration'))
        self.assertEqual(False, config_used.get('drop_db_first'))
        self.assertEqual(False, config_used.get('paused_mode'))
        self.assertEqual(None, config_used.get('log_dir'))
        self.assertEqual(None, config_used.get('label_version'))
        self.assertEqual(False, config_used.get('force_use_files_on_down'))
        self.assertEqual(False, config_used.get('force_execute_old_migrations_versions'))
        self.assertEqual(1, config_used.get('log_level'))

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    def test_it_should_get_configuration_exclusively_from_args_if_not_use_configuration_file_using_config_class_and_execute_with_default_configuration(self, main_mock, execute_mock):
        simple_db_migrate.run_from_argv(['--db-host', 'host', '--db-port', '4321', '--db-name', 'name', '--db-user', 'user', '--db-password', 'pass', '--db-engine', 'engine', '--db-migrations-dir', '.:/tmp:../migration'])

        self.assertEqual(1, execute_mock.call_count)
        execute_mock.assert_called_with()

        self.assertEqual(1, main_mock.call_count)
        config_used = main_mock.call_args[0][0]
        self.assertTrue(isinstance(config_used, simple_db_migrate.config.Config))
        self.assertEqual('engine', config_used.get('database_engine'))
        self.assertEqual('user', config_used.get('database_user'))
        self.assertEqual('pass', config_used.get('database_password'))
        self.assertEqual('name', config_used.get('database_name'))
        self.assertEqual('host', config_used.get('database_host'))
        self.assertEqual(4321, config_used.get('database_port'))
        self.assertEqual(False, config_used.get('utc_timestamp'))
        self.assertEqual('__db_version__', config_used.get('database_version_table'))
        self.assertEqual([os.path.abspath('.'), '/tmp', os.path.abspath('../migration')], config_used.get("database_migrations_dir"))
        self.assertEqual(None, config_used.get('schema_version'))
        self.assertEqual(False, config_used.get('show_sql'))
        self.assertEqual(False, config_used.get('show_sql_only'))
        self.assertEqual(None, config_used.get('new_migration'))
        self.assertEqual(False, config_used.get('drop_db_first'))
        self.assertEqual(False, config_used.get('paused_mode'))
        self.assertEqual(None, config_used.get('log_dir'))
        self.assertEqual(None, config_used.get('label_version'))
        self.assertEqual(False, config_used.get('force_use_files_on_down'))
        self.assertEqual(False, config_used.get('force_execute_old_migrations_versions'))
        self.assertEqual(1, config_used.get('log_level'))

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    @patch.object(simple_db_migrate.helpers.Utils, 'get_variables_from_file', return_value = {'DATABASE_HOST':'host', 'DATABASE_USER': 'root', 'DATABASE_PASSWORD':'', 'DATABASE_NAME':'database', 'DATABASE_MIGRATIONS_DIR':'.'})
    def test_it_should_use_log_level_as_specified(self, import_file_mock, main_mock, execute_mock):
        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf'), '--log-level', 4])
        config_used = main_mock.call_args[0][0]
        self.assertEqual(4, config_used.get('log_level'))

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    @patch.object(simple_db_migrate.helpers.Utils, 'get_variables_from_file', return_value = {'DATABASE_HOST':'host', 'DATABASE_USER': 'root', 'DATABASE_PASSWORD':'', 'DATABASE_NAME':'database', 'DATABASE_MIGRATIONS_DIR':'.'})
    def test_it_should_use_log_level_as_2_when_in_paused_mode(self, import_file_mock, main_mock, execute_mock):
        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf'), '--pause'])
        config_used = main_mock.call_args[0][0]
        self.assertEqual(2, config_used.get('log_level'))

    @patch('simple_db_migrate.getpass', return_value='password_asked')
    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    @patch.object(simple_db_migrate.helpers.Utils, 'get_variables_from_file', return_value = {'DATABASE_HOST':'host', 'DATABASE_USER': 'root', 'DATABASE_PASSWORD':'<<ask_me>>', 'DATABASE_NAME':'database', 'DATABASE_MIGRATIONS_DIR':'.'})
    def test_it_should_ask_for_password_when_configuration_is_as_ask_me(self, import_file_mock, main_mock, execute_mock, getpass_mock):
        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf')])
        config_used = main_mock.call_args[0][0]
        self.assertEqual('password_asked', config_used.get('database_password'))
        self.assertEqual('\nPlease inform password to connect to database "root@host:database"\n', sys.stdout.getvalue())

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    @patch.object(simple_db_migrate.helpers.Utils, 'get_variables_from_file', return_value = {'DATABASE_HOST':'host', 'DATABASE_USER': 'root', 'DATABASE_PASSWORD':'<<ask_me>>', 'DATABASE_NAME':'database', 'DATABASE_MIGRATIONS_DIR':'.'})
    def test_it_should_use_password_from_command_line_when_configuration_is_as_ask_me(self, import_file_mock, main_mock, execute_mock):
        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf'), '--password', 'xpto_pass'])
        config_used = main_mock.call_args[0][0]
        self.assertEqual('xpto_pass', config_used.get('database_password'))

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    @patch.object(simple_db_migrate.helpers.Utils, 'get_variables_from_file', return_value = {'force_execute_old_migrations_versions':True, 'label_version':'label', 'DATABASE_HOST':'host', 'DATABASE_USER': 'root', 'DATABASE_PASSWORD':'', 'DATABASE_NAME':'database', 'DATABASE_MIGRATIONS_DIR':'.'})
    def test_it_should_use_values_from_config_file_in_replacement_for_command_line(self, import_file_mock, main_mock, execute_mock):
        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf')])
        config_used = main_mock.call_args[0][0]
        self.assertEqual('label', config_used.get('label_version'))
        self.assertEqual(True, config_used.get('force_execute_old_migrations_versions'))

    @patch.object(simple_db_migrate.main.Main, 'execute')
    @patch.object(simple_db_migrate.main.Main, '__init__', return_value=None)
    def test_it_should_check_if_has_a_default_configuration_file(self, main_mock, execute_mock):
        f = open('simple-db-migrate.conf', 'w')
        f.write("DATABASE_HOST = 'host_on_default_configuration_filename'")
        f.close()

        simple_db_migrate.run_from_argv([])
        self.assertEqual(1, main_mock.call_count)
        config_used = main_mock.call_args[0][0]
        self.assertTrue(isinstance(config_used, simple_db_migrate.config.FileConfig))
        self.assertEqual('host_on_default_configuration_filename', config_used.get('database_host'))

        main_mock.reset_mock()

        f = open('sample.conf', 'w')
        f.write("DATABASE_HOST = 'host_on_sample_configuration_filename'")
        f.close()

        simple_db_migrate.run_from_argv(["-c", os.path.abspath('sample.conf')])
        self.assertEqual(1, main_mock.call_count)
        config_used = main_mock.call_args[0][0]
        self.assertTrue(isinstance(config_used, simple_db_migrate.config.FileConfig))
        self.assertEqual('host_on_sample_configuration_filename', config_used.get('database_host'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
