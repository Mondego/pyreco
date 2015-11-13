__FILENAME__ = modules
import os
import imp

class BaseModule(object):

    def __init__(self, module_name, module_dir):
        self.name = module_name
        self.dir = module_dir

        cfg_file = os.path.join(self.dir, "chuck_module.py")
        if os.access(cfg_file, os.R_OK):
            self.cfg = imp.load_source(self.name.replace("-", "_"), cfg_file)
        else:
            self.cfg = None

    def get_priority(self):
        if self.cfg and hasattr(self.cfg, 'priority'):
            return self.cfg.priority
        return 100000
    priority = property(get_priority)

    def get_dependencies(self):
        if self.cfg and hasattr(self.cfg, 'depends'):
            return self.cfg.depends
        return None
    dependencies = property(get_dependencies)

    def get_incompatibles(self):
        if self.cfg and hasattr(self.cfg, 'incompatible_with'):
            return self.cfg.incompatible_with
        return None
    incompatibles = property(get_incompatibles)

    def get_description(self):
        if self.cfg and hasattr(self.cfg, 'description'):
            return self.cfg.description
        return ""
    description = property(get_description)

    def get_post_build(self):
        if self.cfg and hasattr(self.cfg, 'post_build'):
            return self.cfg.post_build
        return None
    post_build = property(get_post_build)

    def get_post_setup(self):
        if self.cfg and hasattr(self.cfg, 'post_setup'):
            return self.cfg.post_build
        return None
    post_setup = property(get_post_setup)

########NEW FILE########
__FILENAME__ = base
import pdb
import shutil
import subprocess
import re
import os
import sys
from signal import signal, SIGINT, SIGILL, SIGTERM, SIGSEGV, SIGABRT, SIGQUIT
from random import choice
from django_chuck.base.modules import BaseModule
#from django_chuck.base import constants


# The base class for all commands

class BaseCommand(object):
    help = "The base class of all chuck commands"

    def got_killed(self, signum=2, frame=None):
        if getattr(self, "delete_project_on_failure") and self.delete_project_on_failure:
            if os.path.exists(self.site_dir):
                print "Deleting project data " + self.site_dir
                shutil.rmtree(self.site_dir)

            if os.path.exists(self.virtualenv_dir):
                print "Deleting virtualenv " + self.virtualenv_dir
                shutil.rmtree(self.virtualenv_dir)

            self.signal_handler()

        sys.exit(1)


    def signal_handler(self):
        """
        Implement this method in your command if you want to do some cleanup
        after being terminated by the user or killed by the system.
        Project and virtualenv dir will get erased automatically.
        """
        pass


    def __init__(self):
        signal(SIGINT, self.got_killed)
        signal(SIGQUIT, self.got_killed)
        signal(SIGILL, self.got_killed)
        signal(SIGABRT, self.got_killed)
        signal(SIGSEGV, self.got_killed)
        signal(SIGTERM, self.got_killed)

        # command arguments will override cfg
        self.args = None

        # config settings
        self.cfg = None

        # dont check that project prefix and name exist?
        self.no_default_checks = False

        # default options
        self.opts = [
            ("project_prefix", {
                "help": "A prefix for the project e.g. customer name. Used to distinguish between site and project dir",
                "default": None,
                "nargs": "?",
            }),

            ("project_name", {
                "help": "The name of the project",
                "default": None,
                "nargs": "?",
            }),

            ("-D", {
                "help": "debug mode",
                "dest": "debug",
                "default": False,
                "action": "store_true",
            }),

            ("-ed", {
                "help": "Your email domain",
                "dest": "email_domain",
                "default": "localhost",
                "nargs": "?",
            }),

            ("-mbs", {
                "help": "Comma separated list of dirs where chuck should look for modules",
                "dest": "module_basedir",
                "default": None,
                "nargs": "?",
            }),

            ("-pb", {
                "help": "The directory where all your projects are stored",
                "dest": "project_basedir",
                "default": None,
                "nargs": "?",
            }),

            ("-pyv", {
                "help": "Python version",
                "dest": "python_version",
                "type": float,
                "default": None,
                "nargs": "?",
            }),

            ("-s", {
                "help": "Django settings module to use after loading virtualenv",
                "dest": "django_settings",
                "default": None,
                "nargs": "?",
            }),

            ("-spb", {
                "help": "The directory on your server where all your projects are stored",
                "dest": "server_project_basedir",
                "default": None,
                "nargs": "?",
            }),

            ("-svb", {
                "help": "The directory on your server where all your virtualenvs are stored",
                "dest": "server_virtualenv_basedir",
                "default": None,
                "nargs": "?",
            }),

            ("-vb", {
                "help": "The directory where all your virtualenvs are stored",
                "dest": "virtualenv_basedir",
                "default": None,
                "nargs": "?",
            }),

            ("-vcs", {
                "help": "Version control system (git, cvs, svn or hg))",
                "dest": "version_control_system",
                "default": "git",
                "nargs": "?",
            }),

            ("-w", {
                "help": "User virtualenv wrapper to create virtualenv",
                "dest": "use_virtualenvwrapper",
                "default": False,
                "action": "store_true",
            }),
        ]


    def arg_or_cfg(self, var):
        """
        Get the value of an parameter or config setting
        """
        try:
            result = getattr(self.args, var)
        except AttributeError:
            result = None

        if not result:
            result = self.cfg.get(var, "")

        return result


    def insert_default_modules(self, module_list):
        """
        Add default modules to your module list
        Ensure that core module is the first module to install
        """
        if self.default_modules:
            for module in reversed(self.default_modules):
                if module not in module_list:
                    module_list.insert(0, module)

        if "core" in module_list:
            del module_list[module_list.index("core")]

        module_list.insert(0, "core")

        return module_list


    def get_install_modules(self):
        """
        Get list of modules to install
        Will insert default module set and resolve module aliases
        """
        try:
            install_modules = re.split("\s*,\s*", self.args.modules)
        except AttributeError:
            install_modules = []
        except TypeError:
            install_modules = []

        install_modules = self.insert_default_modules(install_modules)

        if self.cfg.get("module_aliases"):
            for (module_alias, module_list) in self.cfg.get("module_aliases").items():
                if module_alias in install_modules:
                    module_index = install_modules.index(module_alias)
                    install_modules.pop(module_index)

                    for module in reversed(module_list):
                        install_modules.insert(module_index, module)

        return install_modules

    def get_module_cache(self):
        """
        Return dict of modules with key module name and value base module
        Useful to access modules description, dependency, priority etc
        """
        # Create module dir cache
        module_cache = {}

        for module_basedir in self.module_basedirs:
            for module in os.listdir(module_basedir):
                module_dir = os.path.join(module_basedir, module)
                if os.path.isdir(module_dir) and module not in module_cache.keys():
                    module_cache[module] = BaseModule(module, module_dir)
                    # TODO: Ignore list for folders and filenames
                    if module_cache[module].cfg:
                        self.inject_variables_and_functions(module_cache[module].cfg)
        return module_cache

    def clean_module_list(self, module_list, module_cache):
        """
        Recursivly append dependencies to module list, remove duplicates
        and order modules by priority
        """
        errors = []

        # Add dependencies
        def get_dependencies(module_list):
            to_append = []
            for module_name in module_list:
                module = module_cache.get(module_name)
                if not module:
                    errors.append("Module %s could not be found." % module_name)
                elif module.dependencies:
                    for module_name in module.dependencies:
                        if not module_name in module_list and not module_name in to_append:
                            to_append.append(module_name)
            return to_append

        to_append = get_dependencies(module_list)
        while len(to_append) > 0:
            module_list += to_append
            to_append = get_dependencies(module_list)

        if len(errors) > 0:
            print "\n<<< ".join(errors)
            self.kill_system()

        # Check incompatibilities
        for module_name in module_list:
            module = module_cache.get(module_name)
            if module.incompatibles:
                for module_name in module.incompatibles:
                    if module_name in module_list:
                        errors.append("Module %s is not compatible with module %s" % (module.name, module_name))

        if len(errors) > 0:
            print "\n<<< ".join(errors)
            self.kill_system()

        # Order by priority
        module_list = sorted(module_list, key=lambda module: module_cache.get(module).priority)
        return module_list


    def get_subprocess_kwargs(self):
        return dict(
            shell=True,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )


    def execute(self, command, return_result=False):
        if return_result:
            kwargs = self.get_subprocess_kwargs()

            if return_result:
                kwargs['stdout'] = subprocess.PIPE

            process = subprocess.Popen(command, **kwargs)
            stdout, stderr = process.communicate()

            if stderr:
                print stderr

            if process.returncode != 0:
                print return_result
                self.kill_system()

            return stdout
        else:
            return_code = subprocess.call(command, shell=True)

            if return_code != 0:
                self.kill_system()


    def execute_in_project(self, cmd, return_result=False):
        """
        Execute a shell command after loading virtualenv and loading django settings.
        Parameter return_result decides whether the shell command output should get
        printed out or returned.
        """
        commands = self.get_virtualenv_setup_commands(cmd)
        return self.execute('; '.join(commands), return_result)


    def get_virtualenv_setup_commands(self, cmd):
        if self.use_virtualenvwrapper:
            commands = [
                '. virtualenvwrapper.sh',
                'workon ' + self.site_name,
                ]
        else:
            commands = [
                '. ' + os.path.join(os.path.expanduser(self.virtualenv_dir), "bin", "activate"),
                ]
        commands.append(cmd)
        return commands


    def db_cleanup(self):
        """
        Sync and migrate, delete content types and load fixtures afterwards
        This is for example useful for complete django-cms migrations
        NOTE: This command will not erase your old database!
        """
        # os.chdir(self.site_dir)
        # sys.path.append(self.site_dir)

        # os.environ["DJANGO_SETTINGS_MODULE"] = self.django_settings
        # # __import__(self.django_settings)
        # # #settings.configure(default_settings=self.django_settings)

        # #from django.utils.importlib import import_module
        # #import_module(self.django_settings)

        # from django.db import connection, transaction
        # from django.conf import settings

        # cursor = connection.cursor()

        # if settings.DATABASE_ENGINE.startswith("postgresql"):
        #     cursor.execute("truncate django_content_type cascade;")
        # else:
        #     cursor.execute("DELETE FROM auth_permission;")
        #     cursor.execute("DELETE FROM django_admin_log;")
        #     cursor.execute("DELETE FROM auth_user;")
        #     cursor.execute("DELETE FROM auth_group_permissions;")
        #     cursor.execute("DELETE FROM auth_user_user_permissions;")
        #     cursor.execute("DELETE FROM django_content_type;")
        #     cursor.execute("DELETE FROM django_site;")
        #     cursor.execute("DELETE FROM south_migrationhistory;")

        # transaction.commit_unless_managed()
        # sys.path.pop()

        cmd = """DELETE FROM auth_permission;
        DELETE FROM django_admin_log;
        DELETE FROM auth_user;
        DELETE FROM auth_group_permissions;
        DELETE FROM auth_user_user_permissions;
        DELETE FROM django_content_type;
        DELETE FROM django_site;
        DELETE FROM south_migrationhistory;"""

        self.execute_in_project("echo '" + cmd + "' | django-admin.py dbshell")


    def load_fixtures(self, fixture_file):
        """
        Load a fixtures file
        """
        self.execute_in_project("django-admin.py loaddata " + fixture_file)


    def __getattr__(self, name):
        """
        Get value either from command-line argument or config setting
        """
        result = None

        if name == "cfg":
            result = self.cfg
        elif name == "args":
            result = self.args

        elif name == "project_prefix":
            result = self.arg_or_cfg(name).replace("-", "_")

        elif name == "project_name":
            result = self.arg_or_cfg(name).replace("-", "_")

        elif name == "virtualenv_dir":
            result = os.path.join(os.path.expanduser(self.virtualenv_basedir), self.project_prefix + "-" + self.project_name)

        elif name == "site_dir":
            result = os.path.join(os.path.expanduser(self.project_basedir), self.project_prefix + "-" + self.project_name)

        elif name == "project_dir":
            result = os.path.join(self.site_dir, self.project_name)

        elif name == "delete_project_on_failure":
            result = self.arg_or_cfg(name)

        elif name == "server_project_basedir":
            result = self.arg_or_cfg(name)

            if not result:
                result = "CHANGEME"

        elif name == "server_virtualenv_basedir":
            result = self.arg_or_cfg(name)

            if not result:
                result = "CHANGEME"

        elif name == "django_settings":
            result = self.arg_or_cfg(name)

            if result and not result.startswith(self.project_name):
                result = self.project_name + "." + result
            elif not result:
                result = self.project_name + ".settings.dev"

        elif name == "requirements_file":
            result = self.arg_or_cfg(name)

            if not result:
                result = "requirements_local.txt"

        elif name == "site_name":
            result = self.project_prefix + "-" + self.project_name

        elif name == "python_version":
            result = self.arg_or_cfg(name)

            if not result:
                result = sys.version[0:3]

        elif name == "module_basedirs":
            result = self.arg_or_cfg(name)

            if result and "." in result:
                result[result.index(".")] = self.module_basedir
            elif not result:
                result = [self.module_basedir]

        else:
            result = self.arg_or_cfg(name)

        return result


    def print_header(self, msg):
        """
        Print a header message
        """
        print "\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-"
        print msg
        print "-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-\n"


    def kill_system(self):
        """
        Your computer failed! Let it die!
        """
        msgs = [
            "Your system gave an Chuck incompatible answer!",
            "The system failed to obey Chuck! Terminate!",
            "Chuck stumbled over his feet and the world fell apart.",
            "Your computer lied to Chuck. Now it tastes a roundhouse-kick!",
            "That was a serious failure. May god forgive Chuck doesnt!",
            "Death to the system for being so faulty!",
        ]

        print "\n<<< " + choice(msgs)
        self.got_killed()


    def inject_variables_and_functions(self, victim_class):
        """
        Inject variables and functions to a class
        Used for chuck_setup and chuck_module helpers
        """
        # inject variables
        setattr(victim_class, "virtualenv_dir", self.virtualenv_dir)
        setattr(victim_class, "site_dir", self.site_dir)
        setattr(victim_class, "project_dir", os.path.join(self.site_dir, self.project_name))
        setattr(victim_class, "project_name", self.project_name)
        setattr(victim_class, "site_name", self.site_name)
        #setattr(victim_class, "HIGH", constants.HIGH)
        #setattr(victim_class, "MEDIUM", constants.MEDIUM)
        #setattr(victim_class, "LOW", constants.LOW)

        # inject functions
        setattr(victim_class, "execute_in_project", self.execute_in_project)
        setattr(victim_class, "db_cleanup", self.db_cleanup)
        setattr(victim_class, "load_fixtures", self.load_fixtures)


        return victim_class


    def handle(self, args, cfg):
        """
        This method includes the commands functionality
        """
        self.args = args
        self.cfg = cfg

        if not self.no_default_checks:
            if not self.project_prefix:
                raise ValueError("project_prefix is not defined")

            if not self.project_name:
                raise ValueError("project_name is not defined")

########NEW FILE########
__FILENAME__ = build_snapshot
import fileinput
from django_chuck.commands.base import BaseCommand
import os


class Command(BaseCommand):
    help = "Build a snapshot of the project requirements"

    def __init__(self):
        super(Command, self).__init__()

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        self.print_header("BUILD SNAPSHOT")

        output = self.execute_in_project('pip freeze', return_result=True).split('\n')

        if output:
            self.requirements = {}
            for line in output:
                if line == '':
                    continue
                (app_name, version) = line.split("==")
                self.requirements[app_name] = version

            self.update_requirement_file(os.path.join(self.site_dir, 'requirements/requirements_local.txt'))
            self.update_requirement_file(os.path.join(self.site_dir, 'requirements/requirements_dev.txt'))
            self.update_requirement_file(os.path.join(self.site_dir, 'requirements/requirements_live.txt'))
            self.update_requirement_file(os.path.join(self.site_dir, 'requirements/requirements.txt'))
        else:
            print "<<< Unable to build snapshot. pip freeze returned no result!"


    def update_requirement_file(self, file):
        """
        Replace requirements with explicit installed version
        """
        for line in fileinput.input(file, inplace=1):
            if line.find('-r') >= 0 or line == '\n':
                print line,
                continue
            if line.find('>') > 0:
                index = line.find('>')
            elif line.find('<') > 0:
                index = line.find('<')
            elif line.find('=') > 0:
                index = line.find('=')
            else:
                index = line.find('\n')
            app_name = line[0:index]

            if self.requirements.get(app_name):
                print "%s==%s" % (app_name, self.requirements[app_name])
            else:
                print "%s" % (app_name,)

########NEW FILE########
__FILENAME__ = checkout_source
import os
import sys
import shutil
import tempfile
import subprocess
from django_chuck.commands.base import BaseCommand


class Command(BaseCommand):
    help = "Checkout the source code"

    def __init__(self):
        super(Command, self).__init__()

        self.no_default_checks = True

        self.opts.append((
            "checkout_url", {
                "help": "repository url",
            }))

        self.opts.append((
            "-cd", {
                "help": "destination directory",
                "dest": "checkout_destdir",
                "default": "",
                "nargs": "?"
            }),
        )

        self.opts.append((
            "-b", {
                "help": "branch to checkout / clone",
                "dest": "branch",
                "default": "",
                "nargs": "?"
            }),
        )


    def signal_handler(self):
        if os.path.exists(self.checkout_destdir):
            print "Deleting checkout directory " + self.checkout_destdir
            shutil.rmtree(self.checkout_destdir)


    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        if not self.checkout_url:
            raise ValueError("checkout_url is not defined")

        if not self.checkout_destdir:
            self.checkout_destdir = tempfile.mktemp()

        self.print_header("CHECKOUT SOURCE")

        if os.path.exists(self.checkout_destdir):
            answer = raw_input("Checkout dir exists. Use old source? <Y/n>: ")

            if answer.lower() == "n":
                shutil.rmtree(self.checkout_destdir)
            else:
                return

        if self.version_control_system.lower() == "cvs":
            if self.branch:
                cmd ="cvs checkout -r " + self.branch + " " + self.checkout_url + " " + self.checkout_destdir
            else:
                cmd ="cvs checkout " + self.checkout_url + " " + self.checkout_destdir
        elif self.version_control_system.lower() == "svn":
            cmd = "svn checkout " + self.checkout_url + " " + self.checkout_destdir
        elif self.version_control_system.lower() == "hg":
            if self.branch:
                cmd = "hg clone " + self.checkout_url + " -r " + self.branch + " " + self.checkout_destdir
            else:
                cmd = "hg clone " + self.checkout_url + " " + self.checkout_destdir
        else:
            if self.branch:
                cmd = "git clone " + self.checkout_url + " -b " + self.branch + " " + self.checkout_destdir
            else:
                cmd = "git clone " + self.checkout_url + " " + self.checkout_destdir

        cmd_successful = os.system(cmd)

        if cmd_successful > 0:
            self.kill_system()

########NEW FILE########
__FILENAME__ = create_database
from django_chuck.commands.base import BaseCommand
from django_chuck.commands import sync_database, migrate_database


class Command(BaseCommand):
    help = "Sync and migrate database"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("extra_syncdb_options", {
            "help": "Options to append at syncdb command",
            "nargs": "?",
        }))

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        sync_database.Command().handle(args, cfg)

        if "south" in self.get_install_modules():
            migrate_database.Command().handle(args, cfg)

########NEW FILE########
__FILENAME__ = create_project
from django_chuck.commands.base import BaseCommand
from django_chuck.commands import create_virtualenv, install_modules, install_virtualenv, create_database, build_snapshot

class Command(BaseCommand):
    help = "Start a new project"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("modules", {
            "help": "modules to install",
            "nargs": "?",
        }))

        self.opts.append(("-a", {
            "help": "Comma seperated list of apps that should get installed by pip",
            "dest": "additional_apps",
            "default": None,
            "nargs": "?",
        }))


    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        create_virtualenv.Command().handle(args, cfg)
        install_modules.Command().handle(args, cfg)
        install_virtualenv.Command().handle(args, cfg)
        build_snapshot.Command().handle(args, cfg)
        create_database.Command().handle(args, cfg)


        self.print_header("SUMMARY")

        installed_modules = self.get_install_modules()

        print "Created project with modules " + ", ".join(installed_modules)

        if self.use_virtualenvwrapper:
            print "\nworkon " + self.site_name
        else:
            print "\nsource " + self.virtualenv_dir + "/bin/activate"

            print "cd " + self.site_dir

        print "django-admin.py createsuperuser"

########NEW FILE########
__FILENAME__ = create_virtualenv
import subprocess
from django_chuck.commands.base import BaseCommand
import os
import shutil

class Command(BaseCommand):
    help = "Create virtualenv"

    def __init__(self):
        super(Command, self).__init__()


    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        if os.path.exists(self.virtualenv_dir):
            answer = raw_input("Delete old virtualenv dir? <y/N>: ")

            if not answer.lower() == "y" and not answer.lower() == "j":
                print "Aborting."
                return 0

            shutil.rmtree(self.virtualenv_dir)
            os.makedirs(self.virtualenv_dir)
        else:
            os.makedirs(self.virtualenv_dir)


        self.print_header("CREATE VIRTUALENV")

        if self.use_virtualenvwrapper:
            self.execute(". virtualenvwrapper.sh; mkvirtualenv --no-site-packages " + self.site_name)
            export_dest = open(os.path.join(self.virtualenv_dir, "bin", "postactivate"), "a")
        else:
            self.execute("virtualenv --no-site-packages " + self.virtualenv_dir)
            export_dest = open(os.path.join(self.virtualenv_dir, "bin", "activate"), "a")

        self.print_header("SETUP VIRTUALENV")

        print "Destination: %s" % export_dest.name
        print "Project path: %s" % "export PYTHONPATH=\"" + self.site_dir + "\":$PYTHONPATH"
        export_dest.write("export PYTHONPATH=\"" + self.site_dir + "\":$PYTHONPATH\n")
        if self.django_settings:
            print "Project settings: %s" % "export DJANGO_SETTINGS_MODULE=" + self.django_settings + "\n"
            export_dest.write("export DJANGO_SETTINGS_MODULE=" + self.django_settings + "\n")
        export_dest.close()
########NEW FILE########
__FILENAME__ = install_modules
from django_chuck.commands.base import BaseCommand
import os
import sys
import shutil
from django_chuck.utils import append_to_file, get_files, get_template_engine, compile_template
from random import choice

class Command(BaseCommand):
    help = "Create all modules"

    # Which modules shall be installed
    modules_to_install = []

    # Remember which module were already installed
    installed_modules = []

    # Remember where we can find which module
    module_cache = {}

    # Post build actions
    post_build_actions = []

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("modules", {
            "help": "Comma seperated list of module names (can include pip modules)",
            "default": "core",
            "nargs": "?",
        }))

    def install_module(self, module_name):
        module = self.module_cache.get(module_name, None)

        # Module has post build action? Remember it
        if module.cfg:
            cfg = self.inject_variables_and_functions(module.cfg)
            setattr(cfg, "installed_modules", self.installed_modules)
            if module.post_build:
                self.post_build_actions.append((module.name, module.post_build))

        self.print_header("BUILDING " + module.name)
        self.installed_modules.append(module)

        # For each file in the module dir
        for f in get_files(module.dir):
            if not "chuck_module.py" in f:
                # Absolute path to module file
                input_file = f

                # Relative path to module file
                rel_path_old = f.replace(module.dir, "")

                # Relative path to module file with project_name replaced
                rel_path_new = f.replace(module.dir, "").replace("project", self.project_name)

                # Absolute path to module file in site dir
                output_file = f.replace(module.dir, self.site_dir).replace(rel_path_old, rel_path_new)

                # Apply templates
                print "\t%s -> %s" % (input_file, output_file)
                compile_template(input_file, output_file, self.placeholder, self.site_dir, self.project_dir, self.template_engine, self.debug)

        if module == "core":
            secret_key = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@%^&*(-_=+)') for i in range(50)])
            shutil.move(os.path.join(self.site_dir, ".gitignore_" + self.project_name), os.path.join(self.site_dir, ".gitignore"))
            append_to_file(os.path.join(self.project_dir, "settings", "common.py"), "\nSECRET_KEY = '" + secret_key + "'\n")

        self.installed_modules.append(module.name)


    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        self.installed_modules = []

        # Get module cache
        self.module_cache = self.get_module_cache()

        # Modules to install
        self.modules_to_install = self.get_install_modules()

        # The template engine that is used to compile the project files
        template_engine = get_template_engine(self.site_dir, self.project_dir, cfg.get("template_engine"))

        self.placeholder = {
            "PROJECT_PREFIX": self.project_prefix,
            "PROJECT_NAME": self.project_name,
            "SITE_NAME": self.site_name,
            "MODULE_BASEDIR": self.module_basedir,
            "PYTHON_VERSION": self.python_version,
            "PROJECT_BASEDIR": self.project_basedir,
            "VIRTUALENV_BASEDIR": self.virtualenv_basedir,
            "SERVER_PROJECT_BASEDIR": self.server_project_basedir,
            "SERVER_VIRTUALENV_BASEDIR": self.server_virtualenv_basedir,
            "EMAIL_DOMAIN": self.email_domain,
            "MODULES": ','.join(self.modules_to_install),
        }


        # Project exists
        if os.path.exists(self.site_dir) and not cfg.get("updating"):
            self.print_header("EXISTING PROJECT " + self.site_dir)
            answer = raw_input("Delete old project dir? <y/N>: ")

            if answer.lower() == "y" or answer.lower() == "j":
                shutil.rmtree(self.site_dir)
                os.makedirs(self.site_dir)
            else:
                print "Aborting."
                sys.exit(0)

        # Building a new project
        else:
            os.makedirs(self.site_dir)

        # Clean module list
        self.modules_to_install = self.clean_module_list(self.modules_to_install, self.module_cache)

        # Install each module
        for module in self.modules_to_install:
            self.install_module(module)

        not_installed_modules = [m for m in self.modules_to_install if not m in self.installed_modules]

        if not_installed_modules:
            print "\n<<< The following modules cannot be found " + ",".join(not_installed_modules)
            self.kill_system()

        # we are using notch interactive template engine
        # so we want to remove all chuck keywords after successful build
        if (self.template_engine == "django_chuck.template.notch_interactive.engine" or not self.template_engine) and\
           not self.debug:
            for f in get_files(self.site_dir):
                template_engine.remove_keywords(f)


        # execute post build actions
        if self.post_build_actions:
            self.print_header("EXECUTING POST BUILD ACTIONS")


            for action in self.post_build_actions:
                print ">>> " + action[0]
                try:
                    action[1]()
                    print "\n"
                except Exception, e:
                    print str(e)
                    self.kill_system()



########NEW FILE########
__FILENAME__ = install_virtualenv
from django_chuck.commands.base import BaseCommand
import re
import os


class Command(BaseCommand):
    help = "Install all requirements in virtualenv"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("-a", {
            "help": "Comma seperated list of apps that should get installed by pip",
            "dest": "additional_apps",
            "default": None,
            "nargs": "?",
        }))

        self.opts.append(("-rf", {
            "help": "requirements file to use",
            "dest": "requirements_file",
            "default": "requirements_local.txt",
            "nargs": "?",
        }))



    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        self.print_header("INSTALL VIRTUALENV")
        self.execute_in_project("pip install -r " + os.path.join(self.site_dir, "requirements", self.requirements_file))

        # Install additional apps
        if self.additional_apps:
            for app in re.split("\s*,\s*", self.additional_apps):
                self.execute_in_project("pip install " + app)
########NEW FILE########
__FILENAME__ = list_modules
import os
from django_chuck.commands.base import BaseCommand

class Command(BaseCommand):
    help = "Shows all available modules"

    def __init__(self):
        super(Command, self).__init__()

        # Disable default checks because this command isn't project-related
        self.no_default_checks = True

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        self.print_header("AVAILABLE MODULES")

        for module_basedir in self.module_basedirs:
            for module_name in os.listdir(module_basedir):
                print module_name


########NEW FILE########
__FILENAME__ = migrate_database
from django_chuck.commands.base import BaseCommand
import os

class Command(BaseCommand):
    help = "Migrate database"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("extra_migrate_options", {
            "help": "Options to append at migrate command",
            "nargs": "?",
        }))

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        if not self.django_settings:
            raise ValueError("django_settings is not defined")

        if not self.virtualenv_dir:
            raise ValueError("virtualenv_dir is not defined")

        self.print_header("MIGRATE DATABASE")
        os.chdir(self.site_dir)
        self.execute_in_project("django-admin.py migrate")

########NEW FILE########
__FILENAME__ = rebuild_database
import re
import os
from django_chuck.commands.base import BaseCommand
from django_chuck.commands import sync_database, migrate_database


class Command(BaseCommand):
    help = "Sync, migrate database and load fixtures"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("fixture_files", {
            "help": "Comma separated list of fixture files to load",
            "nargs": "?",
        }))

        self.opts.append(("extra_syncdb_options", {
            "help": "Options to append at syncdb command",
            "nargs": "?",
        }))

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        sync_database.Command().handle(args, cfg)
        migrate_database.Command().handle(args, cfg)

        try:
            if args.fixture_files:
                for fixture_file in re.split("\s*,\s*", args.fixture_files):
                    self.db_cleanup()
                    self.load_fixtures(os.path.join(self.site_dir, "fixtures", fixture_file))
        except AttributeError:
            pass


########NEW FILE########
__FILENAME__ = rebuild_virtualenv
from django_chuck.commands.base import BaseCommand
import shutil
from django_chuck.commands import create_virtualenv, install_virtualenv

class Command(BaseCommand):
    help = "Rebuild virtualenv"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("-a", {
            "help": "Comma seperated list of apps that should get installed by pip",
            "dest": "additional_apps",
            "default": None,
            "nargs": "?",
        }))



    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        self.print_header("REBUILD VIRTUALENV")

        shutil.rmtree(self.virtualenv_dir)
        create_virtualenv.Command().handle(args, cfg)
        install_virtualenv.Command().handle(args, cfg)

########NEW FILE########
__FILENAME__ = search_module
import os
import re
from django_chuck.commands.base import BaseCommand

class Command(BaseCommand):
    help = "Search available modules matching given name or description"

    def __init__(self):
        super(Command, self).__init__()

        # Disable default checks because this command isn't project-related
        self.no_default_checks = True

        self.opts = [("pattern", {
            "help": "search pattern",
            "default": "",
        })]


    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        self.print_header("MATCHING MODULES")

        for (module_name, module) in self.get_module_cache().items():
            if re.search(self.args.pattern, module_name) or \
               re.search(self.args.pattern, module.get_description()):
                print "-------------------------------------------------------------------------------"
                print "[%s]" % (module_name,)
                print "-------------------------------------------------------------------------------"

                if module.get_description():
                    print module.get_description() + "\n"
                else:
                    print "\nNo description available\n\n"
########NEW FILE########
__FILENAME__ = show_info
import os
from django_chuck.commands.base import BaseCommand
import imp

class Command(BaseCommand):
    help = "Shows all available information of a module"

    def __init__(self):
        super(Command, self).__init__()

        # Disable default checks because this command isn't project-related
        self.no_default_checks = True

        # The module name argument's definition
        self.opts= (("module", {
            "help": "A module name",
            "default": None,
            "nargs": "?",
        }), )

    def show_info(self, module, module_dir):

        self.print_header("Module '%s'" % module)

        print "Location: \t%s" % module_dir

        # Determine chuck_module.py's path
        chuck_module_file = os.path.join(module_dir, "chuck_module.py")

        # Checks whether chuck_module.py exists for this module
        if os.access(chuck_module_file, os.R_OK):
            # Import chuck_module.py as <module_name>
            chuck_module = imp.load_source(module.replace("-", "_"), chuck_module_file)

            # Print dependencies if present
            if hasattr(chuck_module, 'depends'):
                print "Dependencies: \t %s" % ', '.join(chuck_module.depends)

            # Print description if present
            if hasattr(chuck_module, 'description'):
                print chuck_module.description

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        module = self.arg_or_cfg('module')

        # Abort if no module name is given.
        if not module:
            print "Please provide a module name!"
            return

        # Iterate over available directories
        module_dir = None
        for module_basedir in self.module_basedirs:
            if module in os.listdir(module_basedir):
                module_dir = os.path.join(module_basedir, module)
                break

        # Abort if no module with the given name exists.
        if not module_dir:
            print "No module with name '%s' found!" % module
            return

        self.show_info(module, module_dir)



########NEW FILE########
__FILENAME__ = sync_database
import os
from django_chuck.commands.base import BaseCommand

class Command(BaseCommand):
    help = "Sync and migrate database"

    def __init__(self):
        super(Command, self).__init__()

        self.opts.append(("extra_syncdb_options", {
            "help": "Options to append at syncdb command",
            "nargs": "?",
        }))

    def handle(self, args, cfg):
        super(Command, self).handle(args, cfg)

        if not self.django_settings:
            raise ValueError("django_settings is not defined")

        self.print_header("SYNC DATABASE")
        os.chdir(self.site_dir)
        self.execute_in_project("django-admin.py syncdb --noinput")

########NEW FILE########
__FILENAME__ = test
import os
import unittest
from mock import Mock
from django_chuck.commands.base import BaseCommand


class ComandsTest(unittest.TestCase):
    def setUp(self):
        test_class = type("Test", (BaseCommand,), {})
        self.test_obj = test_class()
        self.test_obj.cfg = {}
        self.test_obj.arg = {}


    def test_arg_or_cfg(self):
        self.test_obj.arg = {}
        self.test_obj.cfg["project_name"] = "balle was here"
        self.assertEqual(self.test_obj.arg_or_cfg("project_name"), "balle was here")


    def test_insert_default_modules(self):
        self.test_obj.cfg["default_modules"] = ["tick", "trick", "track"]
        self.assertEqual(self.test_obj.insert_default_modules(["donald"]), ["core", "tick", "trick", "track", "donald"])


    def test_get_install_modules(self):
        self.test_obj.args = type("Argh", (object,), {"modules": "simpsons, futurama"})
        self.test_obj.cfg["default_modules"] = ["tick", "trick", "track"]
        self.test_obj.cfg["module_aliases"] = {"simpsons": ["homer", "marge", "bart", "lisa", "maggie"]}
        self.assertEqual(self.test_obj.get_install_modules(), ["core", "tick", "trick", "track", "homer", "marge", "bart", "lisa", "maggie", "futurama"])


    def test_get_module_cache(self):
        from django_chuck.base.modules import BaseModule

        self.test_obj.args = type("Argh", (object,), {})
        self.test_obj.cfg["module_basedirs"] = ["."]
        self.test_obj.cfg["module_basedir"] = "../../modules"

        cache = self.test_obj.get_module_cache()

        self.assertIn("south", cache.keys())
        self.assertIs(type(cache["south"]), BaseModule)
        self.assertIn("South is the defacto standard for database migrations in Django", cache["south"].get_description())


    def test_clean_module_list_dependency(self):
        self.test_obj.args = type("Argh", (object,), {})
        self.test_obj.cfg["module_basedirs"] = ["."]
        self.test_obj.cfg["module_basedir"] = "../../modules"
        cache = self.test_obj.get_module_cache()
        module_list = ["django-cms"]
        clean_modules = self.test_obj.clean_module_list(module_list, cache)

        self.assertIsNot(module_list, clean_modules)
        self.assertIn("html5lib", clean_modules)

    def test_clean_module_list_duplicates(self):
        self.test_obj.args = type("Argh", (object,), {})
        self.test_obj.cfg["module_basedirs"] = ["."]
        self.test_obj.cfg["module_basedir"] = "../../modules"
        cache = self.test_obj.get_module_cache()
        module_list = ["django-cms", "html5lib"]
        clean_modules = self.test_obj.clean_module_list(module_list, cache)

        self.assertEqual(len(filter(lambda x: x == "html5lib", clean_modules)), 1)


    def test_clean_module_list_priority(self):
        self.test_obj.args = type("Argh", (object,), {})
        self.test_obj.cfg["module_basedirs"] = ["."]
        self.test_obj.cfg["module_basedir"] = "../../modules"
        cache = self.test_obj.get_module_cache()
        module_list = ["django-cms", "html5lib"]
        clean_modules = self.test_obj.clean_module_list(module_list, cache)

        self.assertEqual(clean_modules[0], "django-1.3")


    def test_inject_variables_and_functions(self):
        victim_class = type("Victim", (object,), {})

        self.test_obj.cfg["site_dir"] = "site_dir"
        self.test_obj.cfg["project_dir"] = "project_dir"
        self.test_obj.cfg["project_prefix"] = "project_prefix"
        self.test_obj.cfg["project_name"] = "project_name"
        self.test_obj.cfg["project_basedir"] = "project_basedir"

        victim_class = self.test_obj.inject_variables_and_functions(victim_class)

        self.assertEqual(victim_class.virtualenv_dir, "project_prefix-project_name")
        self.assertEqual(victim_class.site_dir, "project_basedir/project_prefix-project_name")
        self.assertEqual(victim_class.project_dir, "project_basedir/project_prefix-project_name/project_name")
        self.assertEqual(victim_class.project_name, "project_name")
        self.assertEqual(victim_class.site_name, "project_prefix-project_name")

        self.assertTrue(getattr(victim_class, "execute_in_project"))
        self.assertTrue(getattr(victim_class, "db_cleanup"))
        self.assertTrue(getattr(victim_class, "load_fixtures"))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = exceptions
class TemplateError(Exception):
    """
    General template error
    """
    __msg = ""

    def __init__(self, what):
        super(TemplateError, self).__init__()
        self.__msg = what

    def __str__(self):
        return str(self.__msg)

########NEW FILE########
__FILENAME__ = base
from django_chuck.utils import find_chuck_module_path

class BaseEngine(object):
    module_basedir = find_chuck_module_path()
    site_dir = ""
    project_dir = ""

    def __init__(self, site_dir, project_dir):
        self.site_dir = site_dir
        self.project_dir = project_dir


    def handle(self, input_file, output_file, placeholder):
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = cheetah_engine
from django_chuck.template.base import BaseEngine
from django_chuck.utils import write_to_file
from Cheetah.Template import Template

class TemplateEngine(BaseEngine):
    def handle(self, input_file, output_file, placeholder):
        with open(input_file, "rb") as f:
            write_to_file(output_file, f.read())

        template = str(Template(output_file, searchList=[placeholder]))

        with open(input_file, "w") as f:
            f.write(template)




########NEW FILE########
__FILENAME__ = mako_engine
from django_chuck.template.base import BaseEngine
from django_chuck.utils import write_to_file
from django_chuck.exceptions import TemplateError

from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import SyntaxException, TemplateLookupException


class TemplateEngine(BaseEngine):
    def handle(self, input_file, output_file, placeholder):
        lookup = TemplateLookup(directories=[self.module_basedir])

        try:
            template = Template(filename=input_file, lookup=lookup).render(**placeholder)
        except TemplateLookupException, e:
            raise TemplateError("Lookup error: " + str(e))
        except SyntaxException, e:
            raise TemplateError("Syntax error: " + str(e))

        write_to_file(output_file, template)

########NEW FILE########
__FILENAME__ = engine
from django_chuck.template.base import BaseEngine
from django_chuck.utils import write_to_file
from django_chuck.exceptions import TemplateError
import os
import re

class TemplateEngine(BaseEngine):
    input_file = ""
    base_file = ""
    extension_file = ""
    line_count = ""
    input = ""
    output = ""

    keyword_patterns = {
        "extends": re.compile(r"#!chuck_extends [\'\"]?(.+)[\'\"]?", re.IGNORECASE),
        "extends_if_exists": re.compile(r"#!chuck_extends_if_exists [\'\"]?(.+)[\'\"]?", re.IGNORECASE),
        "renders": re.compile(r"#!chuck_renders ([\w\d\_\-]+)", re.IGNORECASE),
        "appends": re.compile(r"#!chuck_appends ([\w\d\_\-]+)", re.IGNORECASE),
        "prepends": re.compile(r"#!chuck_prepends ([\w\d\_\-]+)", re.IGNORECASE),
    }


    def get_block_content(self, content, block_name="", keyword="renders"):
        """
        Get the content of a chuck block (chuck_renders, chuck_append, chuck_prepend)
        """
        block_content = ""

        match = re.search(r"#!chuck_" + keyword +" " + re.escape(block_name) + "([\r\n\s]+.*?)#!end",
                          content,
                          re.MULTILINE|re.DOTALL)

        if match:
            block_content = match.group(1)

        return block_content


    def update_block_content(self, block_name, keyword="renders"):
        """
        Update output depending on keyword (append, prepend, renders) from template with block named block_name
        """
        old_block_content = self.get_block_content(self.output, block_name)

        if old_block_content:
            new_block_content = self.get_block_content(self.input, block_name, keyword)

            if new_block_content:
                if keyword == "appends":
                    update_content = old_block_content + new_block_content
                elif keyword == "prepends":
                    update_content = new_block_content + old_block_content
                else:
                    update_content = new_block_content

                self.output = re.sub(r"#!chuck_renders " + block_name + re.escape(old_block_content) + "#!end",
                                     r"#!chuck_renders " + block_name + update_content + "#!end",
                                     self.output,
                                     re.IGNORECASE|re.DOTALL|re.MULTILINE)

            else:
                raise TemplateError("Content of block " + block_name + " cannot be found in file " + self.input_file + " line " + str(self.line_count))
        else:
            raise TemplateError("Block " + block_name + " cannot be found in file " + self.base_file)


    @staticmethod
    def found_keyword_in_line(line):
        """
        Parse keyword in line
        """
        keyword = None
        match = re.search(r"#!chuck_(\w+)", line)

        if match:
            keyword = match.group(1)

        return keyword


    def write_file(self, filename):
        """
        Replace placeholder and write file
        """
        for (var, value) in self.placeholder.items():
            self.output = self.output.replace("$" + var, value)

        write_to_file(filename, self.output)


    def get_real_basefile_path(self):
        """
        Return the real basefile path. Resolve project to dir name.
        """
        base_file = os.path.join(self.site_dir, self.extension_file).rstrip("\"").rstrip("\'").lstrip()

        if self.extension_file.startswith("project"):
            # remove first dir (project) from path
            (tmp_path, tmp_file) = os.path.split(self.extension_file)
            tmp_path = tmp_path.lstrip()
            tmp_dirs = tmp_path.split(os.sep)

            # project dir is not the only dir
            if len(tmp_dirs) > 1:
                tmp_path = os.sep.join(tmp_dirs[1:])
            else:
                tmp_path = ""

            # and add the real project dir
            base_file = os.path.join(self.project_dir, tmp_path, tmp_file)

        return base_file


    def extend_file(self):
        """
        command extends
        """
        # Write old base file
        if self.base_file:
            self.write_file(self.base_file)

        # Remove old extension block
        tmp = self.input.splitlines()
        self.input = "\n".join(tmp[self.line_count:])

        # Load base template
        self.base_file = self.get_real_basefile_path()

        try:
            fh = open(self.base_file, "r")
            self.output = fh.read()
            fh.close()
        except IOError:
            raise TemplateError("Cannot find extension file " + self.base_file + " in file " + self.input_file + " line " + str(self.line_count))


    def handle(self, input_file, output_file, placeholder):
        """
        Render template
        """
        self.base_file = None
        self.input = None
        self.line_count = 0
        self.input_file = input_file
        self.base_file = ""
        self.extension_file = None
        self.output = ""
        self.placeholder = placeholder

        with open(self.input_file, "r") as f:
            self.input = f.read()

        lines = self.input.splitlines()
        self.output = self.input

        for line in lines:
            self.line_count += 1

            # Something to do for chuck?
            keyword = self.found_keyword_in_line(line)

            if keyword:
                if self.keyword_patterns.get(keyword):
                    match = self.keyword_patterns[keyword].match(line)

                    # EXTENDS
                    if match and keyword == "extends":
                        self.extension_file = match.group(1).rstrip("\"").rstrip("\'")
                        self.extend_file()

                    # EXTENDS_IF_EXISTS
                    elif match and keyword == "extends_if_exists":
                        self.extension_file = match.group(1).rstrip("\"").rstrip("\'")

                        if os.path.exists(self.get_real_basefile_path()):
                            self.extend_file()
                        else:
                            self.base_file = None

                    # RENDERS
                    elif match and match.group(1) and keyword == "renders" and self.base_file:
                        self.update_block_content(match.group(1), keyword)

                    # PREPENDS, APPENDS
                    elif match and match.group(1) and (keyword == "prepends" or keyword == "appends") and self.base_file:
                        self.update_block_content(match.group(1), keyword)
                else:
                    raise TemplateError("Unknown keyword " + keyword + " found in file " + self.input_file + " line " + str(self.line_count))

        if self.base_file:
            self.write_file(self.base_file)
        else:
            self.write_file(output_file)



    def remove_keywords(self, input_file):
        """
        Remove chuck keywords from file
        """
        output = []

        with open(input_file, "r") as f:
            for line in f.xreadlines():
                keyword = self.found_keyword_in_line(line)

                if keyword:
                    match = self.keyword_patterns[keyword].search(line)

                    if match:
                        line = re.sub(r"#!chuck_" + keyword + " " + re.escape(match.group(1)) + "\s?\r?\n?", "", line, re.IGNORECASE)

                line = re.sub(r"#!end\s*\r?\n?", "", line, re.IGNORECASE)
                output.append(line)

        with open(input_file, "w") as f:
            f.write("".join(output))

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

import os, sys
from $PROJECT_NAME.settings.custom import *

ugettext = lambda s: s

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_ROOT = os.path.dirname(PROJECT_ROOT)

sys.path.append(SITE_ROOT) # TODO Is this really necessary (i.e. production server)?
sys.path.append(PROJECT_ROOT)
sys.path.append(PROJECT_ROOT + '/apps/')
sys.path.append(PROJECT_ROOT + '/libs/')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

APPEND_SLASH = True

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True



# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(SITE_ROOT, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    #!chuck_renders STATICFILES_DIRS
    os.path.join(PROJECT_ROOT, 'static'),
    #!end
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    #!chuck_renders STATICFILES_FINDERS
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
    #!end
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    #!chuck_renders TEMPLATE_LOADERS
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #!end
)


MIDDLEWARE_CLASSES = (
    #!chuck_renders MIDDLEWARE_CLASSES
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.csrf.CsrfResponseMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #!end
)

TEMPLATE_CONTEXT_PROCESSORS = (
    #!chuck_renders TEMPLATE_CONTEXT_PROCESSORS
    'django.core.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.core.context_processors.media',
    'django.core.context_processors.debug',
    #!end
)

ROOT_URLCONF = '$PROJECT_NAME.urls'

TEMPLATE_DIRS = (
    #!chuck_renders TEMPLATE_DIRS
    os.path.join(PROJECT_ROOT, 'templates'),
    #!end
)

INSTALLED_APPS = (
    #!chuck_renders INSTALLED_APPS
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.admin',
    'django_extensions',

    'south',
    'imagekit',
    'compressor',
    'basic_http_auth',

    'ni_django_utils',
    #!end
)


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# COMPRESSOR
COMPRESS_PRECOMPILERS = (
	('text/less', 'lessc {infile} {outfile}'),
)

#!chuck_renders SETTINGS #!end


########NEW FILE########
__FILENAME__ = extends_common
#!chuck_extends project/common.py

#!chuck_appends MIDDLEWARE_CLASSES
    'cms.middleware.multilingual.MultilingualURLMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
#!end

#!chuck_appends TEMPLATE_CONTEXT_PROCESSORS
    'cms.context_processors.media',
    'sekizai.context_processors.sekizai',
#!end

#!chuck_appends INSTALLED_APPS
    'cms',
    'menus',
    'cms.plugins.text',
    'easy_thumbnails',
    'filer',
    'cmsplugin_filer_file',
    'cmsplugin_filer_folder',
    'cmsplugin_filer_image',
    'cmsplugin_filer_video',

    'mptt',
    'sekizai',

    'ni_djangocms_utils',
    'ni_cmsplugins.better_link',
#!end


#!chuck_appends SETTINGS
CMS_TEMPLATES = (
    ('home.html', ugettext('Home')),
    ('subsite.html', ugettext('Subsite')),
)

CMS_SOFTROOT = False
CMS_MODERATOR = False
CMS_PERMISSION = False
CMS_REDIRECTS = True
CMS_SEO_FIELDS = True
CMS_FLAT_URLS = False
CMS_MENU_TITLE_OVERWRITE = False
CMS_HIDE_UNTRANSLATED = True
CMS_URL_OVERWRITE = False
CMS_SHOW_START_DATE = False
CMS_SHOW_END_DATE = False

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    #'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)
#!end


########NEW FILE########
__FILENAME__ = test
import os
import re
import shutil
import unittest
from engine import TemplateEngine
from django_chuck.exceptions import TemplateError


class TemplateEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = TemplateEngine(os.getcwd() + "/test", os.getcwd() + "/test/project_dir")


    def test_get_block_content(self):
        with open("test/templates/common.py", "r") as f:
            content = f.read()
            block_content = self.engine.get_block_content(content, "MIDDLEWARE_CLASSES")
            self.assertNotIn("#!chuck", block_content)

            block_content = self.engine.get_block_content(content, "SETTINGS")
            self.assertEqual(block_content, " ")

    #
    # TEST BASIC KEYWORDS
    #

    def test_renders(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        self.engine.handle("test/templates/replace.html", "test/project_dir/replace.html", {})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertIn("<html>", content)
            self.assertIn("#!chuck_renders content", content)


    def test_render_multiple_blocks(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        self.engine.handle("test/templates/replace_three_blocks.html", "test/project_dir/replace_three_blocks.html", {})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertIn("<html>", content)
            self.assertIn("#!chuck_renders content", content)
            self.assertIn("lets start", content)
            self.assertIn("MOOOOOH", content)
            self.assertIn("go home", content)


    def test_appends(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        self.engine.handle("test/templates/append.html", "test/project_dir/append.html", {})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertTrue(re.search(r"One must have chaos in oneself to give birth to a dancing star.+The big MOOOOOH has pwned you", content, re.MULTILINE|re.DOTALL), content)


    def test_prepends(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        self.engine.handle("test/templates/prepend.html", "test/project_dir/prepend.html", {})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertTrue(re.search(r"The big MOOOOOH has pwned you.+One must have chaos in oneself to give birth to a dancing star", content, re.MULTILINE|re.DOTALL), content)


    def test_extends_if_exists(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        self.engine.handle("test/templates/extends_if_exists.html", "test/project_dir/extends_if_exists.html", {})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertTrue(re.search(r"One must have chaos in oneself to give birth to a dancing star.+The big MOOOOOH has pwned you", content, re.MULTILINE|re.DOTALL), content)


    def test_placeholder(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        self.engine.handle("test/templates/placeholder.html", "test/project_dir/placeholder.html", {"SOMETHING": "cool things"})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertIn("cool things", content)


    def test_placeholder_without_extend(self):
        shutil.copy("test/templates/placeholder_without_extend.html", "test/project_dir/placeholder_without_extend.html")
        self.engine.handle("test/templates/placeholder_without_extend.html", "test/project_dir/placeholder_without_extend.html", {"SOMETHING": "cool things"})

        with open("test/project_dir/placeholder_without_extend.html") as f:
            content = f.read()
            self.assertIn("cool things", content)


    def test_remove_keywords(self):
        shutil.copy("test/templates/remove_keywords.html", "test/project_dir/remove_keywords.html")
        self.engine.handle("test/project_dir/remove_keywords.html", "test/project_dir/remove_keywords.html", {})
        self.engine.remove_keywords("test/project_dir/remove_keywords.html")

        with open("test/project_dir/remove_keywords.html") as f:
            content = f.read()
            self.assertFalse("#!chuck" in content, content)
            self.assertTrue("chaos" in content, content)



    def test_complex_example(self):
        shutil.copy("test/templates/common.py", "test/project_dir/common.py")

        self.engine.handle("test/templates/extends_common.py", "test/project_dir/extends_common.py", {"PROJECT_NAME": "test"})
        self.engine.remove_keywords("test/project_dir/common.py")

        with open("test/project_dir/common.py") as f:
            content = f.read()
            self.assertIn("# -*- coding", content.splitlines()[0])  # right order
            self.assertIn("CMS_TEMPLATES", content)                 # appends
            self.assertIn("ROOT_URLCONF = 'test.urls'", content)    # placeholder
            self.assertFalse("#!chuck" in content, content)         # removed keywords


    #
    # ADVANCED FEATURES
    #

    def test_extends_two_files(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        shutil.copy("test/templates/base2.html", "test/project_dir/base2.html")

        self.engine.handle("test/templates/extend_two_files.html", "test/project_dir/extend_two_files.html", {})

        with open("test/project_dir/base.html") as f:
            content = f.read()
            self.assertIn("big MOOOOOH", content)
            self.assertIn("#!chuck_renders content", content)

        with open("test/project_dir/base2.html") as f:
            content = f.read()
            self.assertIn("Balle was here", content)
            self.assertIn("#!chuck_renders content", content)



    #
    # ERRORS
    #
    def test_keyword_not_found(self):
        with self.assertRaises(TemplateError):
            self.engine.handle("test/templates/broken_keyword.html", "test/project_dir/broken_keyword.html", {})


    def test_syntax_error(self):
        with self.assertRaises(TemplateError):
            self.engine.handle("test/templates/broken_syntax.html", "test/project_dir/broken_syntax.html", {})


    def test_non_existent_block_name(self):
        with self.assertRaises(TemplateError):
            self.engine.handle("test/templates/broken_block_name.html", "test/project_dir/brocken_block_name.html", {})


    def test_non_existent_base_file(self):
        with self.assertRaises(TemplateError):
            self.engine.handle("test/templates/broken_base_file.html", "test/project_dir/broken_base_file.html", {})

    def test_non_existent_base_file_with_if_exists(self):
        self.engine.handle("test/templates/broken_base_file_with_if_exists.html", "test/project_dir/broken_base_file_with_if_exists.html", {})


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test
import os
import re
import shutil
import unittest
import utils
import django_chuck.template.base
from django_chuck.exceptions import TemplateError


class UtilsTest(unittest.TestCase):
    def setUp(self):
        self.test_file = os.path.join("test", "project_dir", "test_file")

        if os.path.isfile(self.test_file):
            os.unlink(self.test_file)

    def test_get_files(self):
        files = utils.get_files(os.curdir)
        self.assertTrue(len(files) > 0)

        for file in files:
            self.assertTrue(os.path.isfile(file))


    def test_write_to_file(self):
        test_data = "some wicked cool stuff"
        utils.write_to_file(self.test_file, test_data)

        with open(self.test_file, "r") as f:
            self.assertEqual(f.read(), test_data)


    def test_append_to_file(self):
        test_data = "some wicked cool stuff"
        test_data2 = "even more test data"

        utils.write_to_file(self.test_file, test_data)
        utils.append_to_file(self.test_file, test_data2)

        with open(self.test_file, "r") as f:
            self.assertEqual(f.read(), test_data + test_data2)


    def test_find_chuck_module_path(self):
        self.assertTrue(os.path.exists(utils.find_chuck_module_path()))


    def test_find_chuck_command_path(self):
        self.assertTrue(os.path.exists(utils.find_chuck_command_path()))


    def test_find_commands(self):
        self.assertTrue(len(utils.find_commands()) > 0)


    def test_autoload_commands(self):
        import argparse
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        cfg = {}
        cmds = utils.find_commands()

        self.assertTrue(utils.autoload_commands(subparsers, cfg, cmds))


    def test_get_template_engine(self):
        obj = utils.get_template_engine("test", "test/project_dir")
        self.assertTrue(issubclass(obj.__class__, django_chuck.template.base.BaseEngine))


    def test_compile_template_with_extension(self):
        shutil.copy("test/templates/base.html", "test/project_dir/base.html")
        placeholder = {"WHO": "Balle"}

        result = utils.compile_template("test/templates/site.html", "test/project_dir/site.html", placeholder, "test", "test/project_dir")
        self.assertTrue(result)
        self.assertFalse(os.path.isfile("test/project_dir/site.html"))

        with open("test/project_dir/base.html", "r") as f:
            content = f.read()
            self.assertIn("<html>", content)
            self.assertIn("Hello Balle", content)


    def test_compile_template_without_extension(self):
        placeholder = {"WHO": "Balle"}

        result = utils.compile_template("test/templates/placeholder.html", "test/project_dir/placeholder.html", placeholder, "test", "test/project_dir")
        self.assertTrue(os.path.isfile("test/project_dir/placeholder.html"))

        with open("test/project_dir/placeholder.html", "r") as f:
            content = f.read()
            self.assertIn("Hello Balle", content)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import os
import sys
import functools
import django_chuck


def get_files(dir):
    """
    Recursivly read a directory and return list of all files
    """
    files = []

    for (path, subdirs, new_files) in os.walk(dir):
        for new_file in new_files:
            files.append(os.path.join(path, new_file))

    return files


def write_to_file(out_file, data):
    """
    copy data to out_file
    """
    if os.access(out_file, os.W_OK):
        out = open(out_file, "wb")
    else:
        if not os.path.exists(os.path.dirname(out_file)):
            os.makedirs(os.path.dirname(out_file))

        out = open(out_file, "wb")

    out.write(data)
    out.close()


def append_to_file(out_file, data):
    """
    append data to out_file
    """
    if os.access(out_file, os.W_OK):
        out = open(out_file, "ab")
    else:
        if not os.path.exists(os.path.dirname(out_file)):
            os.makedirs(os.path.dirname(out_file))

        out = open(out_file, "ab")

    out.write(data)
    out.close()



def find_chuck_module_path():
    """
    Return path to chuck modules
    """
    return os.path.join(sys.prefix, "share", "django_chuck", "modules")


def find_chuck_command_path():
    """
    Search for path to chuck commands in sys.path
    """
    module_path = None

    for path in sys.path:
        full_path = os.path.join(path, "django_chuck", "commands")

        if os.path.exists(full_path):
            module_path = full_path
            break

    return module_path


def find_commands():
    """
    Find all django chuck commands and create a list of module names
    """
    commands = []
    command_path = find_chuck_command_path()

    if command_path:
        for f in os.listdir(command_path):
            if not f.startswith("_") and f.endswith(".py") and \
               not f == "base.py" and not f == "test.py":
                commands.append(f[:-3])

    return commands


def autoload_commands(subparsers, cfg, command_list):
    """
    Load all commands in command_list and create argument parsers
    """
    for cmd_name in command_list:
        module_name = "django_chuck.commands." + cmd_name
        __import__(module_name)

        if getattr(sys.modules[module_name], "Command"):
            cmd = sys.modules[module_name].Command()
            cmd_parser = subparsers.add_parser(cmd_name, help=cmd.help)

            try:
                for arg in cmd.opts:
                    cmd_parser.add_argument(arg[0], **arg[1])
            except TypeError, e:
                print "Broken argument configuration in command " + cmd_name + " argument " + str(arg)
                print str(e)
                sys.exit(0)


            handle_cmd = functools.partial(cmd.handle, cfg=cfg)
            cmd_parser.set_defaults(func=handle_cmd)

    return True


def get_template_engine(site_dir, project_dir, engine_module=None):
    """
    Get template engine instance
    """
    default_engine = "django_chuck.template.notch_interactive.engine"

    if not engine_module:
        engine_module = default_engine

    try:
        __import__(engine_module)
    except Exception, e:
        print "\n<<< Cannot import template engine " + engine_module
        print e
        sys.exit(0)

    if getattr(sys.modules[engine_module], "TemplateEngine"):
        engine = sys.modules[engine_module].TemplateEngine(site_dir, project_dir)
    else:
        print "<<< Template engine " + engine_module + " must implement class TemplateEngine"
        sys.exit(0)

    return engine


def compile_template(input_file, output_file, placeholder, site_dir, project_dir, engine_obj=None, debug=False):
    """
    Load the template engine and let it deal with the output_file
    Parameter: name of template file, dictionary of placeholder name / value pairs, name of template engine module
    """
    result = True

    if output_file.endswith(".pyc") or \
       output_file.endswith(".mo"):
        return None

    if issubclass(engine_obj.__class__, django_chuck.template.base.BaseEngine):
        engine = engine_obj
    else:
        engine = get_template_engine(site_dir, project_dir)

    try:
        engine.handle(input_file, output_file, placeholder)
    except django_chuck.exceptions.TemplateError, e:
        print "\n<<< TEMPLATE ERROR in file " + input_file + "\n"
        print str(e) + "\n"
        result = False

    return result

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Chuck documentation build configuration file, created by
# sphinx-quickstart on Mon May 14 11:50:54 2012.
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
project = u'Django Chuck'
copyright = u'2012, Notch Interactive GmbH'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
htmlhelp_basename = 'DjangoChuckdoc'


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
  ('index', 'DjangoChuck.tex', u'Django Chuck Documentation',
   u'Notch Interactive GmbH', 'manual'),
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
    ('index', 'djangochuck', u'Django Chuck Documentation',
     [u'Notch Interactive GmbH'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'DjangoChuck', u'Django Chuck Documentation',
   u'Notch Interactive GmbH', 'DjangoChuck', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = example_conf
# Where to put virtualenvs?
virtualenv_basedir="~/work/virtualenvs"

# Where to put project dirs?
project_basedir="~/work/projects"

# Comma seperated list of dirs where Chuck should look for modules.
# . will be replaced with the Django Chuck modules dir
module_basedirs = ["."]

# comma seperated list of modules that always should be installed
default_modules=["core", "south"]

# comma seperated list of app that should additionally get installed
#default_additional_apps = ["south"]

# use virtualenvwrapper?
use_virtualenvwrapper = False

# default django settings module to use
# project_name will be automatically prepended
django_settings = "settings.dev"

# requirements file to install in virtualenv
# default: requirements_local.txt
requirements_file = "requirements_local.txt"

# version control system
# possible values: git, svn, cvs, hg
# default: git
version_control_system = "git"

# the branch you want to checkout / clone
# default is ""
branch = ""

# Python version to use by default
# If not set version of local python interpreter will be used
# python_version = "2.7"

# Where to find virtualenvs on your server?
server_virtualenv_basedir = "/home/www-data/virtualenvs"

# Where to projects on your server?
server_project_basedir = "/home/www-data/sites"

# What is your email domain?
email_domain = "localhost"

# module aliases are a list of modules under a single name
module_aliases = {
    "test": ["unittest", "jenkins"]
}

# Run in debug mode
debug = False

# Dont delete project after failure?
# delete_project_on_failure=False

# Module to use as template engine
# Default: django_chuck.template.notch_interactive.engine
template_engine = "django_chuck.template.notch_interactive.engine"

########NEW FILE########
__FILENAME__ = chuck_module
import os
import subprocess

depends = ['django-compressor']
description = """
Module for CoffeeScript support

Installs the CoffeeScript binary into your virtualenv and adds its path to the django-compressor precompilers setting.
Requires node.js / npm in order to work.

For more information about CoffeeScript:
http://coffeescript.org/

For django-compressor usage information:
http://django_compressor.readthedocs.org
"""


def post_build():
    source = os.path.join(virtualenv_dir, 'node_modules/coffee-script/bin/coffee')
    target = os.path.join(virtualenv_dir, 'bin/coffee')
    subprocess.call(
        'cd '+virtualenv_dir+'; \
        npm install less; \
        ln -s -v '+source+' '+target+';'
        , shell=True)

def post_setup():
    post_build()
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends SETTINGS
COMPRESS_PRECOMPILERS += (
    ('text/coffeescript', 'coffee --compile --stdio'),
)
#!end
########NEW FILE########
__FILENAME__ = chuck_module

priority = 0

description = """
Django Chuck's core module

Defines the default project layout and requires only Django>=1.4.
This is the only module that gets always installed no matter what other configuration you intend to do.

However, you can easily override the core module with your own one.
If you want to have your own defaults, just copy the module folder and put it in a
directory that you expose in your configuration file, preferably before the default folder.

Example location:
/my/absolute/path/to/my_chuck_modules/core

Example configuration:
module_basedirs = ["/my/absolute/path/to/my_chuck_modules/core", "."]

Now you can adjust the contents of the core module to your needs. Read more about
overriding \ customizing modules here:
http://django-chuck.readthedocs.org
"""
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-

import os, sys
from $PROJECT_NAME.settings.custom import *

ugettext = lambda s: s

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_ROOT = os.path.dirname(PROJECT_ROOT)

sys.path.append(SITE_ROOT) # TODO Is this really necessary (i.e. production server)?
sys.path.append(PROJECT_ROOT)
sys.path.append(PROJECT_ROOT + '/apps/')
sys.path.append(PROJECT_ROOT + '/libs/')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

APPEND_SLASH = True

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True



# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(SITE_ROOT, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    #!chuck_renders STATICFILES_DIRS
    os.path.join(PROJECT_ROOT, 'static'),
    #!end
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    #!chuck_renders STATICFILES_FINDERS
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #!end
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    #!chuck_renders TEMPLATE_LOADERS
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #!end
)


MIDDLEWARE_CLASSES = (
    #!chuck_renders MIDDLEWARE_CLASSES
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #!end
)


TEMPLATE_CONTEXT_PROCESSORS = (
    #!chuck_renders TEMPLATE_CONTEXT_PROCESSORS
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.core.context_processors.media',
    'django.core.context_processors.debug',
    #!end
)


AUTHENTICATION_BACKENDS = (
    #!chuck_renders AUTHENTICATION_BACKENDS
    'django.contrib.auth.backends.ModelBackend',
    #!end
)

ROOT_URLCONF = '$PROJECT_NAME.urls'

TEMPLATE_DIRS = (
    #!chuck_renders TEMPLATE_DIRS
    os.path.join(PROJECT_ROOT, 'templates'),
    #!end
)

INSTALLED_APPS = (
    #!chuck_renders INSTALLED_APPS
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.admin',
    #!end
)


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

#!chuck_renders SETTINGS
# Save timestamps in utc
USE_TZ = True

# cickhacking protection
X_FRAME_OPTIONS = 'DENY'
#!end




########NEW FILE########
__FILENAME__ = custom
# -*- coding: utf-8 -*-

INTERNAL_IPS = ('127.0.0.1',)

ADMINS = (
	('Webmaster', 'webmaster@$EMAIL_DOMAIN'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
# TIME_ZONE = 'Europe/Zurich'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

########NEW FILE########
__FILENAME__ = dev
# -*- coding: utf-8 -*-
# These settings are valid for:
# - sites: all
# - environments: dev

import os
from $PROJECT_NAME.settings.common import *

# Debug
DEBUG = True
TEMPLATE_DEBUG = DEBUG

# E-mail
EMAIL_PORT = 1025
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cache
CACHES = {
    #!chuck_renders CACHES
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
    #!end
}

# Database
DATABASES = {
    #!chuck_renders DATABASES
    'default': {
    	'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    	'NAME': os.path.join(SITE_ROOT, 'db','dev.sqlite3'), # Or path to database file if using sqlite3.
    	'USER': '', # Not used with sqlite3.
    	'PASSWORD': '', # Not used with sqlite3.
    	'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
    	'PORT': '', # Set to empty string for default. Not used with sqlite3.
    },
    #!end
}

DEFAULT_CHARSET='utf-8'

#!chuck_renders SETTINGS
#!end

########NEW FILE########
__FILENAME__ = live
# -*- coding: utf-8 -*-
# These settings are valid for:
# - sites: all
# - environments: prod

from $PROJECT_NAME.settings.common import *

# Debugging
DEBUG = False
TEMPLATE_DEBUG = DEBUG

# E-mail
EMAIL_HOST = 'localhost'
SERVER_EMAIL = 'webmaster@$EMAIL_DOMAIN'
DEFAULT_FROM_EMAIL = 'webmaster@EMAIL_DOMAIN'

# Misc
PREPEND_WWW = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# Cache
CACHES = {
    #!chuck_renders CACHES
#    'default': {
#        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#    }
    #!end
}

# Database
DATABASES = {
    #!chuck_renders DATABASES
#    'default': {
#    	'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#    	'NAME': os.path.join(SITE_ROOT, 'db','dev.sqlite3'), # Or path to database file if using sqlite3.
#    	'USER': '', # Not used with sqlite3.
#    	'PASSWORD': '', # Not used with sqlite3.
#    	'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
#    	'PORT': '', # Set to empty string for default. Not used with sqlite3.
#    },
    #!end
}

#!chuck_renders SETTINGS
#!end


########NEW FILE########
__FILENAME__ = stage
# -*- coding: utf-8 -*-
# These settings are valid for:
# - sites: all
# - environments: prod

from $PROJECT_NAME.settings.common import *

# Debugging
DEBUG = False
TEMPLATE_DEBUG = DEBUG

# E-mail
EMAIL_HOST = 'localhost'
SERVER_EMAIL = 'webmaster@$EMAIL_DOMAIN'
DEFAULT_FROM_EMAIL = 'webmaster@$EMAIL_DOMAIN'

# Misc
PREPEND_WWW = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# Cache
CACHES = {
    #!chuck_renders CACHES
#    'default': {
#        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#    }
    #!end
}

# Database
DATABASES = {
    #!chuck_renders DATABASES
#    'default': {
#    	'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#    	'NAME': os.path.join(SITE_ROOT, 'db','dev.sqlite3'), # Or path to database file if using sqlite3.
#    	'USER': '', # Not used with sqlite3.
#    	'PASSWORD': '', # Not used with sqlite3.
#    	'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
#    	'PORT': '', # Set to empty string for default. Not used with sqlite3.
#    },
    #!end
}

#!chuck_renders SETTINGS
#!end

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
#!chuck_renders URL_MODULES #!end

admin.autodiscover()

#!chuck_renders URLS
urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

# static media
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
#!end

########NEW FILE########
__FILENAME__ = chuck_module

priority = 1

description = """
Provides legacy support for Django 1.3.

IMPORTANT:
You always have to list the django-1.3 as the first module to install right after the core.
If you don't you risk to have some serious instability because this module OVERRIDES the default
requirements and parts of the settings files.
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_renders MIDDLEWARE_CLASSES
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.csrf.CsrfResponseMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
#!end

#!chuck_renders TEMPLATE_CONTEXT_PROCESSORS
    'django.core.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.core.context_processors.media',
    'django.core.context_processors.debug',
    #!end

#!chuck_renders SETTINGS #!end

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
#!chuck_renders URL_MODULES #!end

admin.autodiscover()

#!chuck_renders URLS
urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

# static media
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
#!end

########NEW FILE########
__FILENAME__ = chuck_module
depends = ['django-1.3', 'pil', 'html5lib']
description = """
Adds Django CMS to your project.

Please note that as of yet Django CMS is not compatible with Django 1.4 and therefore
needs the django-1.3 module.

Another requirement of Django CMS is django-mptt, but because of the CMS not
being compatible with the latest django-mptt version, it is not listed as a chuck module
requirement. django-mptt will be included as a normal pip requirement (requirements/requirements.txt)
with an explicit call for the latest version that is known to be working with Django CMS.

For further information, visit;
http://docs.django-cms.org
"""
########NEW FILE########
__FILENAME__ = cms_plugins
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
import models
from django.conf import settings

class FilerFilePlugin(CMSPluginBase):
    module = 'Filer'
    model = models.FilerFile
    name = _("File")
    render_template = "cmsplugin_filer_file/file.html"
    text_enabled = True

    def render(self, context, instance, placeholder):
        context.update({
            'object':instance,
            'placeholder':placeholder
        })
        return context

    def icon_src(self, instance):
        file_icon = instance.get_icon_url()
        if file_icon: return file_icon
        return settings.CMS_MEDIA_URL + u"images/plugins/file.png"

plugin_pool.register_plugin(FilerFilePlugin)

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from cmsplugin_filer_file.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'FilerFile'
        db.create_table('cmsplugin_filerfile', (
            ('cmsplugin_ptr', orm['cmsplugin_filer_file.FilerFile:cmsplugin_ptr']),
            ('file', orm['cmsplugin_filer_file.FilerFile:file']),
            ('title', orm['cmsplugin_filer_file.FilerFile:title']),
        ))
        db.send_create_signal('cmsplugin_filer_file', ['FilerFile'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'FilerFile'
        db.delete_table('cmsplugin_filerfile')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cmsplugin_filer_file.filerfile': {
            'Meta': {'db_table': "'cmsplugin_filerfile'"},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'file_field': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_file']

########NEW FILE########
__FILENAME__ = models
from django.utils.translation import ugettext_lazy as _
from django.db import models
from cms.models import CMSPlugin, Page
from django.utils.translation import ugettext_lazy as _
from posixpath import join, basename, splitext, exists
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField
from django.conf import settings


class FilerFile(CMSPlugin):
    """
    Plugin for storing any type of file.
    
    Default template displays download link with icon (if available) and file size.
    
    Icons are searched for within <MEDIA_ROOT>/<CMS_FILE_ICON_PATH> 
    (CMS_FILE_ICON_PATH is a plugin-specific setting which defaults to "<CMS_MEDIA_PATH>/images/file_icons")
    with filenames of the form <file_ext>.<icon_ext>, where <file_ext> is the extension
    of the file itself, and <icon_ext> is one of <CMS_FILE_ICON_EXTENSIONS>
    (another plugin specific setting, which defaults to ('gif', 'png'))
    
    This could be updated to use the mimetypes library to determine the type of file rather than
    storing a separate icon for each different extension.
    
    The icon search is currently performed within get_icon_url; this is probably a performance concern.
    """
    title = models.CharField(_("title"), max_length=255, null=True, blank=True)
    file = FilerFileField()
    
    def get_icon_url(self):
        return self.file.icons['32']
        
    def file_exists(self):
        return exists(self.file.path);
        
    def get_file_name(self):
        return basename(self.file.path)
        
    def get_ext(self):
        return splitext(self.get_file_name())[1][1:]
        
    def __unicode__(self):
        if self.title: 
            return self.title;
        elif self.file:
            # added if, because it raised attribute error when file wasnt defined
            return self.get_file_name();
        return "<empty>"

    search_fields = ('title',)
    
########NEW FILE########
__FILENAME__ = admin

########NEW FILE########
__FILENAME__ = cms_plugins
from os.path import join
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
from django.forms.models import ModelForm
import models
from django.conf import settings
from django.forms.widgets import Media
from filer.models.imagemodels import Image


class FilerFolderPlugin(CMSPluginBase):
    module = 'Filer'
    model = models.FilerFolder
    name = _("Folder")
    render_template = "cmsplugin_filer_folder/folder.html"
    text_enabled = False
    admin_preview = False

    def get_folder_files(self, folder, user):
        qs_files = folder.files.filter(image__isnull=True)
        if user.is_staff:
            return qs_files
        else:
            return qs_files.filter(is_public=True)

    def get_folder_images(self, folder, user):
        qs_files = folder.files.instance_of(Image)
        if user.is_staff:
            return qs_files
        else:
            return qs_files.filter(is_public=True)

    def get_children(self, folder):
        return folder.get_children()


    def render(self, context, instance, placeholder):

        folder_files = self.get_folder_files(instance.folder,
                                             context['request'].user)
        folder_images = self.get_folder_images(instance.folder,
                                               context['request'].user)
        folder_folders = self.get_children(instance.folder)

        context.update({
            'object': instance,
            'folder_files': sorted(folder_files),
            'folder_images': sorted(folder_images),
            'folder_folders': folder_folders,
            'placeholder': placeholder
        })
        return context



plugin_pool.register_plugin(FilerFolderPlugin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FilerFolder'
        db.create_table('cmsplugin_filerfolder', (
            ('cmsplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cms.CMSPlugin'], unique=True, primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('view_option', self.gf('django.db.models.fields.CharField')(default='list', max_length=10)),
            ('folder', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['filer.Folder'])),
        ))
        db.send_create_signal('cmsplugin_filer_folder', ['FilerFolder'])


    def backwards(self, orm):
        
        # Deleting model 'FilerFolder'
        db.delete_table('cmsplugin_filerfolder')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_folder.filerfolder': {
            'Meta': {'object_name': 'FilerFolder', 'db_table': "'cmsplugin_filerfolder'", '_ormbases': ['cms.CMSPlugin']},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'view_option': ('django.db.models.fields.CharField', [], {'default': "'list'", 'max_length': '10'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['cmsplugin_filer_folder']

########NEW FILE########
__FILENAME__ = models
from django.utils.translation import ugettext_lazy as _
from django.db import models
from cms.models import CMSPlugin, Page
from django.utils.translation import ugettext_lazy as _
from posixpath import join, basename, splitext, exists
from filer.fields.folder import FilerFolderField
from django.conf import settings

VIEW_OPTIONS = getattr(settings, 'CMSPLUGIN_FILER_FOLDER_VIEW_OPTIONS', (("list", _("List")),("slideshow",_("Slideshow"))))

class FilerFolder(CMSPlugin):
    """
    Plugin for storing any type of Folder.
    
    Default template displays files store inside this folder.
    """
    title = models.CharField(_("title"), max_length=255, null=True, blank=True)
    view_option = models.CharField(_("view option"),max_length=10,
                            choices=VIEW_OPTIONS, default="list")
    folder = FilerFolderField()
    
        
    def __unicode__(self):
        if self.title: 
            return self.title;
        elif self.folder.name:
            # added if, because it raised attribute error when file wasnt defined
            return self.folder.name;
        return "<empty>"

    search_fields = ('title',)
    

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import ThumbnailOption

class ThumbnailOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'width', 'height')

admin.site.register(ThumbnailOption, ThumbnailOptionAdmin)
########NEW FILE########
__FILENAME__ = cms_plugins
import os
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
import models
from django.conf import settings

from filer.settings import FILER_STATICMEDIA_PREFIX

class FilerImagePlugin(CMSPluginBase):
    module = 'Filer'
    model = models.FilerImage
    name = _("Image")
    render_template = "cmsplugin_filer_image/image.html"
    text_enabled = True
    raw_id_fields = ('image',)
    admin_preview = False
    fieldsets = (
        (None, {
            'fields': ('caption_text', ('image', 'image_url',), 'alt_text',)
        }),
        (_('Image resizing options'), {
            'fields': ('use_autoscale', 'thumbnail_option',)
        }),
        (None, {
            'fields': (('width', 'height',),
                       ('crop', 'upscale',),)
        }),
        (None, {
            'fields': ('alignment',)
        }),
        (_('More'), {
            'classes': ('collapse',),
            'fields': (('free_link', 'page_link', 'file_link', 'original_link'), 'description',)
        }),

    )

    def _get_thumbnail_options(self, context, instance):
        """
        Return the size and options of the thumbnail that should be inserted
        """
        width, height = None, None
        crop, upscale = False, False
        subject_location = False
        placeholder_width = context.get('width', None)
        placeholder_height = context.get('height', None)
        if instance.thumbnail_option:
            # thumbnail option overrides everything else
            if instance.thumbnail_option.width:
                width = instance.thumbnail_option.width
            if instance.thumbnail_option.height:
                height = instance.thumbnail_option.height
            crop = instance.thumbnail_option.crop
            upscale = instance.thumbnail_option.upscale
        else:
            if instance.use_autoscale and placeholder_width:
                # use the placeholder width as a hint for sizing
                width = int(placeholder_width)
            elif instance.width:
                width = instance.width
            if instance.use_autoscale and placeholder_height:
                height = int(placeholder_height)
            elif instance.height:
                height = instance.height
            crop = instance.crop
            upscale = instance.upscale
        if instance.image:
            if instance.image.subject_location:
                subject_location = instance.image.subject_location
            if not height and width:
                # height was not externally defined: use ratio to scale it by the width
                height = int( float(width)*float(instance.image.height)/float(instance.image.width) )
            if not width and height:
                # width was not externally defined: use ratio to scale it by the height
                width = int( float(height)*float(instance.image.width)/float(instance.image.height) )
            if not width:
                # width is still not defined. fallback the actual image width
                width = instance.image.width
            if not height:
                # height is still not defined. fallback the actual image height
                height = instance.image.height
        return {'size': (width, height),
                'crop': crop,
                'upscale': upscale,
                'subject_location': subject_location}

    def get_thumbnail(self, context, instance):
        if instance.image:
            return instance.image.image.file.get_thumbnail(self._get_thumbnail_options(context, instance))

    def render(self, context, instance, placeholder):
        options = self._get_thumbnail_options(context, instance)
        context.update({
            'instance': instance,
            'link': instance.link,
            'opts': options,
            'size': options.get('size',None),
            'placeholder': placeholder
        })
        return context

    def icon_src(self, instance):
        if instance.image:
            if getattr(settings, 'FILER_IMAGE_USE_ICON', False) and '32' in instance.image.icons:
                return instance.image.icons['32']
            else:
                # Fake the context with a reasonable width value because it is not
                # available at this stage
                thumbnail = self.get_thumbnail({'width':200}, instance)
                return thumbnail.url
        else:
            return os.path.normpath(u"%s/icons/missingfile_%sx%s.png" % (FILER_STATICMEDIA_PREFIX, 32, 32,))
plugin_pool.register_plugin(FilerImagePlugin)

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from cmsplugin_filer_image.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'FilerImage'
        db.create_table('cmsplugin_filerimage', (
            ('cmsplugin_ptr', orm['cmsplugin_filer_image.FilerImage:cmsplugin_ptr']),
            ('image', orm['cmsplugin_filer_image.FilerImage:image']),
            ('alt_text', orm['cmsplugin_filer_image.FilerImage:alt_text']),
            ('caption', orm['cmsplugin_filer_image.FilerImage:caption']),
            ('use_autoscale', orm['cmsplugin_filer_image.FilerImage:use_autoscale']),
            ('width', orm['cmsplugin_filer_image.FilerImage:width']),
            ('height', orm['cmsplugin_filer_image.FilerImage:height']),
            ('float', orm['cmsplugin_filer_image.FilerImage:float']),
            ('free_link', orm['cmsplugin_filer_image.FilerImage:free_link']),
            ('page_link', orm['cmsplugin_filer_image.FilerImage:page_link']),
            ('description', orm['cmsplugin_filer_image.FilerImage:description']),
        ))
        db.send_create_signal('cmsplugin_filer_image', ['FilerImage'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'FilerImage'
        db.delete_table('cmsplugin_filerimage')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'db_table': "'cmsplugin_filerimage'"},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']"}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'file_field': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_filerimage_image_url__chg_field_filerimage_image
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FilerImage.image_url'
        db.add_column('cmsplugin_filerimage', 'image_url', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True, blank=True), keep_default=False)

        # Changing field 'FilerImage.image'
        db.alter_column('cmsplugin_filerimage', 'image_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['filer.Image'], null=True, blank=True))


    def backwards(self, orm):
        
        # Deleting field 'FilerImage.image_url'
        db.delete_column('cmsplugin_filerimage', 'image_url')

        # Changing field 'FilerImage.image'
        db.alter_column('cmsplugin_filerimage', 'image_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['filer.Image']))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0003_auto__add_thumbnailoption__add_field_filerimage_thumbnail_option
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ThumbnailOption'
        db.create_table('cmsplugin_filer_image_thumbnailoption', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('width', self.gf('django.db.models.fields.IntegerField')()),
            ('height', self.gf('django.db.models.fields.IntegerField')()),
            ('is_cropped', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_scaled', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('cmsplugin_filer_image', ['ThumbnailOption'])

        # Adding field 'FilerImage.thumbnail_option'
        db.add_column('cmsplugin_filerimage', 'thumbnail_option', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cmsplugin_filer_image.ThumbnailOption'], null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting model 'ThumbnailOption'
        db.delete_table('cmsplugin_filer_image_thumbnailoption')

        # Deleting field 'FilerImage.thumbnail_option'
        db.delete_column('cmsplugin_filerimage', 'thumbnail_option_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'thumbnail_option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cmsplugin_filer_image.ThumbnailOption']", 'null': 'True', 'blank': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'cmsplugin_filer_image.thumbnailoption': {
            'Meta': {'ordering': "('width', 'height')", 'object_name': 'ThumbnailOption'},
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_cropped': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_scaled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0004_auto__del_field_thumbnailoption_is_scaled__del_field_thumbnailoption_i
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'ThumbnailOption.is_scaled'
        db.delete_column('cmsplugin_filer_image_thumbnailoption', 'is_scaled')

        # Deleting field 'ThumbnailOption.is_cropped'
        db.delete_column('cmsplugin_filer_image_thumbnailoption', 'is_cropped')

        # Adding field 'ThumbnailOption.crop'
        db.add_column('cmsplugin_filer_image_thumbnailoption', 'crop', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Adding field 'ThumbnailOption.upscale'
        db.add_column('cmsplugin_filer_image_thumbnailoption', 'upscale', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Adding field 'FilerImage.crop'
        db.add_column('cmsplugin_filerimage', 'crop', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Adding field 'FilerImage.upscale'
        db.add_column('cmsplugin_filerimage', 'upscale', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'ThumbnailOption.is_scaled'
        db.add_column('cmsplugin_filer_image_thumbnailoption', 'is_scaled', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Adding field 'ThumbnailOption.is_cropped'
        db.add_column('cmsplugin_filer_image_thumbnailoption', 'is_cropped', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Deleting field 'ThumbnailOption.crop'
        db.delete_column('cmsplugin_filer_image_thumbnailoption', 'crop')

        # Deleting field 'ThumbnailOption.upscale'
        db.delete_column('cmsplugin_filer_image_thumbnailoption', 'upscale')

        # Deleting field 'FilerImage.crop'
        db.delete_column('cmsplugin_filerimage', 'crop')

        # Deleting field 'FilerImage.upscale'
        db.delete_column('cmsplugin_filerimage', 'upscale')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'float': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'thumbnail_option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cmsplugin_filer_image.ThumbnailOption']", 'null': 'True', 'blank': 'True'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'cmsplugin_filer_image.thumbnailoption': {
            'Meta': {'ordering': "('width', 'height')", 'object_name': 'ThumbnailOption'},
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0005_rename_float_to_alignment
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        db.rename_column('cmsplugin_filerimage', 'float', 'alignment')


    def backwards(self, orm):
        
        db.rename_column('cmsplugin_filerimage', 'alignment', 'float')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alignment': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'thumbnail_option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cmsplugin_filer_image.ThumbnailOption']", 'null': 'True', 'blank': 'True'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'cmsplugin_filer_image.thumbnailoption': {
            'Meta': {'ordering': "('width', 'height')", 'object_name': 'ThumbnailOption'},
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_filerimage_original_link
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FilerImage.original_link'
        db.add_column('cmsplugin_filerimage', 'original_link', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'FilerImage.original_link'
        db.delete_column('cmsplugin_filerimage', 'original_link')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alignment': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'original_link': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'thumbnail_option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cmsplugin_filer_image.ThumbnailOption']", 'null': 'True', 'blank': 'True'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'cmsplugin_filer_image.thumbnailoption': {
            'Meta': {'ordering': "('width', 'height')", 'object_name': 'ThumbnailOption'},
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0007_rename_caption_to_caption_text
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        db.rename_column('cmsplugin_filerimage', 'caption', 'caption_text')


    def backwards(self, orm):

        db.rename_column('cmsplugin_filerimage', 'caption_text', 'caption')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alignment': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'original_link': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'thumbnail_option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cmsplugin_filer_image.ThumbnailOption']", 'null': 'True', 'blank': 'True'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'cmsplugin_filer_image.thumbnailoption': {
            'Meta': {'ordering': "('width', 'height')", 'object_name': 'ThumbnailOption'},
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_filerimage_file_link
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'FilerImage.file_link'
        db.add_column('cmsplugin_filerimage', 'file_link', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='+', null=True, blank=True, to=orm['filer.File']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'FilerImage.file_link'
        db.delete_column('cmsplugin_filerimage', 'file_link_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '15', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_image.filerimage': {
            'Meta': {'object_name': 'FilerImage', 'db_table': "'cmsplugin_filerimage'", '_ormbases': ['cms.CMSPlugin']},
            'alignment': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'caption_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file_link': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'+'", 'null': 'True', 'blank': 'True', 'to': "orm['filer.File']"}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'original_link': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'thumbnail_option': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cmsplugin_filer_image.ThumbnailOption']", 'null': 'True', 'blank': 'True'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'cmsplugin_filer_image.thumbnailoption': {
            'Meta': {'ordering': "('width', 'height')", 'object_name': 'ThumbnailOption'},
            'crop': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'upscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_image']

########NEW FILE########
__FILENAME__ = models
from django.utils.translation import ugettext_lazy as _
from django.db import models
from cms.models import CMSPlugin, Page
from cms.models.fields import PageField
from posixpath import join, basename, splitext, exists
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField
from cms import settings as cms_settings
from django.conf import settings

class FilerImage(CMSPlugin):
    LEFT = "left"
    RIGHT = "right"
    FLOAT_CHOICES = ((LEFT, _("left")),
                     (RIGHT, _("right")),
                     )
    caption_text = models.CharField(_("caption text"), null=True, blank=True, max_length=255)
    image = FilerImageField(null=True, blank=True, default=None, verbose_name=_("image"))
    image_url = models.URLField(_("alternative image url"), verify_exists=False, null=True, blank=True, default=None)
    alt_text = models.CharField(_("alt text"), null=True, blank=True, max_length=255)
    thumbnail_option = models.ForeignKey('ThumbnailOption', null=True, blank=True, verbose_name=_("thumbnail option"))
    use_autoscale = models.BooleanField(_("use automatic scaling"), default=False, 
                                        help_text=_('tries to auto scale the image based on the placeholder context'))
    width = models.PositiveIntegerField(_("width"), null=True, blank=True)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True)
    crop = models.BooleanField(_("crop"), default=True)
    upscale = models.BooleanField(_("upscale"), default=True)
    alignment = models.CharField(_("image alignment"), max_length=10, blank=True, null=True, choices=FLOAT_CHOICES)
    
    free_link = models.CharField(_("link"), max_length=255, blank=True, null=True, 
                                 help_text=_("if present image will be clickable"))
    page_link = PageField(null=True, blank=True, 
                          help_text=_("if present image will be clickable"),
                          verbose_name=_("page link"))
    file_link = FilerFileField(null=True, blank=True, default=None, verbose_name=_("file link"), help_text=_("if present image will be clickable"), related_name='+')
    original_link = models.BooleanField(_("link original image"), default=False, help_text=_("if present image will be clickable"))
    description = models.TextField(_("description"), blank=True, null=True)
    
    class Meta:
        verbose_name = _("filer image")
        verbose_name_plural = _("filer images")
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Make sure that either image or image_url is set
        if (not self.image and not self.image_url) or (self.image and self.image_url):
            raise ValidationError(_('Either an image or an image url must be selected.'))

    
    def __unicode__(self):
        if self.image:
            return self.image.label
        else:
            return unicode( _("Image Publication %(caption)s") % {'caption': self.caption or self.alt} )
        return ''
    @property
    def caption(self):
        if self.image:
            return self.caption_text or self.image.default_caption
        else:
            return self.caption_text
    @property
    def alt(self):
        if self.image:
            return self.alt_text or self.image.default_alt_text or self.image.label
        else:
            return self.alt_text
    @property
    def link(self):
        if self.free_link:
            return self.free_link
        elif self.page_link:
            return self.page_link.get_absolute_url()
        elif self.file_link:
            return self.file_link.url
        elif self.original_link:
            if self.image:
                return self.image.url
            else:
                return self.image_url
        else:
            return ''
        
        
class ThumbnailOption(models.Model):
    """
    This class defines the option use to create the thumbnail.
    """
    name = models.CharField(_("name"), max_length=100)
    width = models.IntegerField(_("width"), help_text=_('width in pixel.'))
    height = models.IntegerField(_("height"), help_text=_('height in pixel.'))
    crop = models.BooleanField(_("crop"), default=True)
    upscale = models.BooleanField(_("upscale"), default=True)
    
    class Meta:
        ordering = ('width', 'height')
        verbose_name = _("thumbnail option")
        verbose_name_plural = _("thumbnail options")
        
    def __unicode__(self):
        return u'%s -- %s x %s' %(self.name, self.width, self.height)
        


########NEW FILE########
__FILENAME__ = cms_plugins
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
import models
from django.conf import settings


class FilerTeaserPlugin(CMSPluginBase):
    """
    TODO: this plugin is becoming very similar to the image plugin... code
          should be re-used somehow.
    """
    module = 'Filer'
    model = models.FilerTeaser
    name = _("Teaser")
    render_template = "cmsplugin_filer_teaser/teaser.html"

    def _get_thumbnail_options(self, context, instance):
        """
        Return the size and options of the thumbnail that should be inserted
        """
        width, height = None, None
        subject_location = False
        placeholder_width = context.get('width', None)
        placeholder_height = context.get('height', None)
        if instance.use_autoscale and placeholder_width:
            # use the placeholder width as a hint for sizing
            width = int(placeholder_width)
        if instance.use_autoscale and placeholder_height:
            height = int(placeholder_height)
        elif instance.width:
            width = instance.width
        if instance.height:
            height = instance.height
        if instance.image:
            if instance.image.subject_location:
                subject_location = instance.image.subject_location
            if not height and width:
                # height was not externally defined: use ratio to scale it by the width
                height = int( float(width)*float(instance.image.height)/float(instance.image.width) )
            if not width and height:
                # width was not externally defined: use ratio to scale it by the height
                width = int( float(height)*float(instance.image.width)/float(instance.image.height) )
            if not width:
                # width is still not defined. fallback the actual image width
                width = instance.image.width
            if not height:
                # height is still not defined. fallback the actual image height
                height = instance.image.height
        return {'size': (width, height),
                'subject_location': subject_location}

    def get_thumbnail(self, context, instance):
        if instance.image:
            return instance.image.image.file.get_thumbnail(self._get_thumbnail_options(context, instance))

    def render(self, context, instance, placeholder):
        options = self._get_thumbnail_options(context, instance)
        context.update({
            'instance': instance,
            'link': instance.link,
            'opts': options,
            'size': options.get('size',None),
            'placeholder': placeholder
        })
        return context
plugin_pool.register_plugin(FilerTeaserPlugin)

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from cmsplugin_filer_teaser.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'FilerTeaser'
        db.create_table('cmsplugin_filerteaser', (
            ('cmsplugin_ptr', orm['cmsplugin_filer_teaser.FilerTeaser:cmsplugin_ptr']),
            ('title', orm['cmsplugin_filer_teaser.FilerTeaser:title']),
            ('image', orm['cmsplugin_filer_teaser.FilerTeaser:image']),
            ('use_autoscale', orm['cmsplugin_filer_teaser.FilerTeaser:use_autoscale']),
            ('width', orm['cmsplugin_filer_teaser.FilerTeaser:width']),
            ('height', orm['cmsplugin_filer_teaser.FilerTeaser:height']),
            ('free_link', orm['cmsplugin_filer_teaser.FilerTeaser:free_link']),
            ('page_link', orm['cmsplugin_filer_teaser.FilerTeaser:page_link']),
            ('description', orm['cmsplugin_filer_teaser.FilerTeaser:description']),
        ))
        db.send_create_signal('cmsplugin_filer_teaser', ['FilerTeaser'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'FilerTeaser'
        db.delete_table('cmsplugin_filerteaser')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'db_table': "'cmsplugin_filerteaser'"},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'file_field': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = 0002_add_teaser_style_choice

from south.db import db
from django.db import models
from cmsplugin_filer_teaser.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'FilerTeaser.style'
        db.add_column('cmsplugin_filerteaser', 'style', orm['cmsplugin_filer_teaser.filerteaser:style'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'FilerTeaser.style'
        db.delete_column('cmsplugin_filerteaser', 'style')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'page': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'db_table': "'cmsplugin_filerteaser'"},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'style': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'file_field': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = 0003_target_blank
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'FilerTeaser.target_blank'
        db.add_column('cmsplugin_filerteaser', 'target_blank', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting field 'FilerTeaser.target_blank'
        db.delete_column('cmsplugin_filerteaser', 'target_blank')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'object_name': 'FilerTeaser', 'db_table': "'cmsplugin_filerteaser'", '_ormbases': ['cms.CMSPlugin']},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'style': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'target_blank': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = 0004_add_optional_external_image_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'FilerTeaser.image_url'
        db.add_column('cmsplugin_filerteaser', 'image_url', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True, blank=True), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting field 'FilerTeaser.image_url'
        db.delete_column('cmsplugin_filerteaser', 'image_url')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'object_name': 'FilerTeaser', 'db_table': "'cmsplugin_filerteaser'", '_ormbases': ['cms.CMSPlugin']},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'style': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'target_blank': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_filerteaser_title
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Changing field 'FilerTeaser.title'
        db.alter_column('cmsplugin_filerteaser', 'title', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True))
    
    
    def backwards(self, orm):
        
        # Changing field 'FilerTeaser.title'
        db.alter_column('cmsplugin_filerteaser', 'title', self.gf('django.db.models.fields.CharField')(max_length=255))
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'object_name': 'FilerTeaser', 'db_table': "'cmsplugin_filerteaser'", '_ormbases': ['cms.CMSPlugin']},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'style': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'target_blank': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_filerteaser_external_image
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'FilerTeaser.external_image'
        db.add_column('cmsplugin_filerteaser', 'external_image', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting field 'FilerTeaser.external_image'
        db.delete_column('cmsplugin_filerteaser', 'external_image')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'menu_login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'object_name': 'FilerTeaser', 'db_table': "'cmsplugin_filerteaser'", '_ormbases': ['cms.CMSPlugin']},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'external_image': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'style': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'target_blank': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }
    
    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = 0006_fix_migration_mess
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'FilerTeaser.external_image'
        db.delete_column('cmsplugin_filerteaser', 'external_image')


    def backwards(self, orm):
        
        # Adding field 'FilerTeaser.external_image'
        db.add_column('cmsplugin_filerteaser', 'external_image', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True), keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.page': {
            'Meta': {'ordering': "('site', 'tree_id', 'lft')", 'object_name': 'Page'},
            'changed_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'created_by': ('django.db.models.fields.CharField', [], {'max_length': '70'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_navigation': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'limit_visibility_in_menu': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'db_index': 'True', 'blank': 'True'}),
            'login_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'moderator_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '1', 'blank': 'True'}),
            'navigation_extenders': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['cms.Page']"}),
            'placeholders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cms.Placeholder']", 'symmetrical': 'False'}),
            'publication_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'publication_end_date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.Page']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'reverse_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'soft_root': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_teaser.filerteaser': {
            'Meta': {'object_name': 'FilerTeaser', 'db_table': "'cmsplugin_filerteaser'", '_ormbases': ['cms.CMSPlugin']},
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'free_link': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'page_link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Page']", 'null': 'True', 'blank': 'True'}),
            'style': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'target_blank': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'use_autoscale': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['cmsplugin_filer_teaser']

########NEW FILE########
__FILENAME__ = models
from django.utils.translation import ugettext_lazy as _
from django.db import models
from cms.models import CMSPlugin
from cms.models.fields import PageField
from filer.fields.image import FilerImageField
from django.conf import settings

CMSPLUGIN_FILER_TEASER_STYLE_CHOICES = getattr( settings, 'CMSPLUGIN_FILER_TEASER_STYLE_CHOICES',() )

class FilerTeaser(CMSPlugin):
    """
    A Teaser
    """
    title = models.CharField(_("title"), max_length=255, blank=True)
    image = FilerImageField(blank=True, null=True, verbose_name=_("image"))
    image_url = models.URLField(_("alternative image url"), verify_exists=False, null=True, blank=True, default=None)
    
    style = models.CharField(_("teaser style"), max_length=255, null=True, blank=True, choices=CMSPLUGIN_FILER_TEASER_STYLE_CHOICES)
    
    use_autoscale = models.BooleanField(_("use automatic scaling"), default=True, 
                                        help_text=_('tries to auto scale the image based on the placeholder context'))
    width = models.PositiveIntegerField(_("width"), null=True, blank=True)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True)
    
    free_link = models.CharField(_("link"), max_length=255, blank=True, null=True, help_text=_("if present image will be clickable"))
    page_link = PageField(null=True, blank=True, help_text=_("if present image will be clickable"), verbose_name=_("page link"))
    description = models.TextField(_("description"), blank=True, null=True)
    
    target_blank = models.BooleanField(_("open link in new window"), default=False)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Make sure that either image or image_url is set
        if self.image and self.image_url:
            raise ValidationError(_('Either an image or an image url must be selected.'))
    
    def __unicode__(self):
        return self.title

    @property
    def link(self):
        try:
            if self.free_link:
                return self.free_link
            elif self.page_link and self.page_link:
                return self.page_link.get_absolute_url()
            else:
                return ''
        except Exception, e:
            print e

########NEW FILE########
__FILENAME__ = cms_plugins
import os
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
from cmsplugin_filer_video import settings
from cmsplugin_filer_video.models import FilerVideo
from cmsplugin_filer_video.forms import VideoForm
from filer.settings import FILER_STATICMEDIA_PREFIX

class FilerVideoPlugin(CMSPluginBase):
    module = 'Filer'
    model = FilerVideo
    name = _("Video")
    form = VideoForm

    render_template = "cmsplugin_filer_video/video.html"
    text_enabled = True

    general_fields = [
        ('movie', 'movie_url'),
        'image',
        ('width', 'height'),
        'auto_play',
        'auto_hide',
        'fullscreen',
        'loop',
    ]
    color_fields = [
        'bgcolor',
        'textcolor',
        'seekbarcolor',
        'seekbarbgcolor',
        'loadingbarcolor',
        'buttonoutcolor',
        'buttonovercolor',
        'buttonhighlightcolor',
    ]

    fieldsets = [
        (None, {
            'fields': general_fields,
        }),
    ]
    if settings.VIDEO_PLUGIN_ENABLE_ADVANCED_SETTINGS:
        fieldsets += [
            (_('Color Settings'), {
                'fields': color_fields,
                'classes': ('collapse',),
            }),
        ]

    class PluginMedia:
        js = ('https://ajax.googleapis.com/ajax/libs/swfobject/2.2/swfobject.js',)

    def render(self, context, instance, placeholder):
        context.update({
            'object': instance,
            'placeholder':placeholder,
        })
        return context

    def icon_src(self, instance):
        return os.path.normpath(u"%s/icons/video_%sx%s.png" % (FILER_STATICMEDIA_PREFIX, 32, 32,))
plugin_pool.register_plugin(FilerVideoPlugin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from cmsplugin_filer_video.models import FilerVideo

class VideoForm(forms.ModelForm):
    
    class Meta:
        model = FilerVideo
        exclude = ('page', 'position', 'placeholder', 'language', 'plugin_type')
########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FilerVideo'
        db.create_table('cmsplugin_filervideo', (
            ('cmsplugin_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['cms.CMSPlugin'], unique=True, primary_key=True)),
            ('movie', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['filer.File'], null=True, blank=True)),
            ('movie_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='filer_video_image', null=True, to=orm['filer.Image'])),
            ('width', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('height', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('auto_play', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('auto_hide', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('fullscreen', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('loop', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('bgcolor', self.gf('django.db.models.fields.CharField')(default='000000', max_length=6)),
            ('textcolor', self.gf('django.db.models.fields.CharField')(default='FFFFFF', max_length=6)),
            ('seekbarcolor', self.gf('django.db.models.fields.CharField')(default='13ABEC', max_length=6)),
            ('seekbarbgcolor', self.gf('django.db.models.fields.CharField')(default='333333', max_length=6)),
            ('loadingbarcolor', self.gf('django.db.models.fields.CharField')(default='828282', max_length=6)),
            ('buttonoutcolor', self.gf('django.db.models.fields.CharField')(default='333333', max_length=6)),
            ('buttonovercolor', self.gf('django.db.models.fields.CharField')(default='000000', max_length=6)),
            ('buttonhighlightcolor', self.gf('django.db.models.fields.CharField')(default='FFFFFF', max_length=6)),
        ))
        db.send_create_signal('cmsplugin_filer_video', ['FilerVideo'])


    def backwards(self, orm):
        
        # Deleting model 'FilerVideo'
        db.delete_table('cmsplugin_filervideo')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cms.cmsplugin': {
            'Meta': {'object_name': 'CMSPlugin'},
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5', 'db_index': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.CMSPlugin']", 'null': 'True', 'blank': 'True'}),
            'placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cms.Placeholder']", 'null': 'True'}),
            'plugin_type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'position': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'publisher_is_draft': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True', 'blank': 'True'}),
            'publisher_public': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'publisher_draft'", 'unique': 'True', 'null': 'True', 'to': "orm['cms.CMSPlugin']"}),
            'publisher_state': ('django.db.models.fields.SmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'cms.placeholder': {
            'Meta': {'object_name': 'Placeholder'},
            'default_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slot': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'cmsplugin_filer_video.filervideo': {
            'Meta': {'object_name': 'FilerVideo', 'db_table': "'cmsplugin_filervideo'", '_ormbases': ['cms.CMSPlugin']},
            'auto_hide': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'auto_play': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'bgcolor': ('django.db.models.fields.CharField', [], {'default': "'000000'", 'max_length': '6'}),
            'buttonhighlightcolor': ('django.db.models.fields.CharField', [], {'default': "'FFFFFF'", 'max_length': '6'}),
            'buttonoutcolor': ('django.db.models.fields.CharField', [], {'default': "'333333'", 'max_length': '6'}),
            'buttonovercolor': ('django.db.models.fields.CharField', [], {'default': "'000000'", 'max_length': '6'}),
            'cmsplugin_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['cms.CMSPlugin']", 'unique': 'True', 'primary_key': 'True'}),
            'fullscreen': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'height': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_video_image'", 'null': 'True', 'to': "orm['filer.Image']"}),
            'loadingbarcolor': ('django.db.models.fields.CharField', [], {'default': "'828282'", 'max_length': '6'}),
            'loop': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'movie': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']", 'null': 'True', 'blank': 'True'}),
            'movie_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'seekbarbgcolor': ('django.db.models.fields.CharField', [], {'default': "'333333'", 'max_length': '6'}),
            'seekbarcolor': ('django.db.models.fields.CharField', [], {'default': "'13ABEC'", 'max_length': '6'}),
            'textcolor': ('django.db.models.fields.CharField', [], {'default': "'FFFFFF'", 'max_length': '6'}),
            'width': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['cmsplugin_filer_video']

########NEW FILE########
__FILENAME__ = models
from cms.models import CMSPlugin
from cmsplugin_filer_video import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from os.path import basename
import re

class FilerVideo(CMSPlugin):
    # player settings
    movie = FilerFileField(verbose_name=_('movie file'), help_text=_('use .flv file or h264 encoded video file'), blank=True, null=True)
    movie_url = models.CharField(_('movie url'), max_length=255, help_text=_('vimeo or youtube video url. Example: http://www.youtube.com/watch?v=YFa59lK-kpo'), blank=True, null=True)
    image = FilerImageField(verbose_name=_('image'), help_text=_('preview image file'), null=True, blank=True, related_name='filer_video_image')
    
    width = models.PositiveSmallIntegerField(_('width'), default=settings.VIDEO_WIDTH)
    height = models.PositiveSmallIntegerField(_('height'), default=settings.VIDEO_HEIGHT)
    
    auto_play = models.BooleanField(_('auto play'), default=settings.VIDEO_AUTOPLAY)
    auto_hide = models.BooleanField(_('auto hide'), default=settings.VIDEO_AUTOHIDE)
    fullscreen = models.BooleanField(_('fullscreen'), default=settings.VIDEO_FULLSCREEN)
    loop = models.BooleanField(_('loop'), default=settings.VIDEO_LOOP)
    
    # plugin settings
    bgcolor = models.CharField(_('background color'), max_length=6, default=settings.VIDEO_BG_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    textcolor = models.CharField(_('text color'), max_length=6, default=settings.VIDEO_TEXT_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    seekbarcolor = models.CharField(_('seekbar color'), max_length=6, default=settings.VIDEO_SEEKBAR_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    seekbarbgcolor = models.CharField(_('seekbar bg color'), max_length=6, default=settings.VIDEO_SEEKBARBG_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    loadingbarcolor = models.CharField(_('loadingbar color'), max_length=6, default=settings.VIDEO_LOADINGBAR_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    buttonoutcolor = models.CharField(_('button out color'), max_length=6, default=settings.VIDEO_BUTTON_OUT_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    buttonovercolor = models.CharField(_('button over color'), max_length=6, default=settings.VIDEO_BUTTON_OVER_COLOR, help_text=_('Hexadecimal, eg ff00cc'))        
    buttonhighlightcolor = models.CharField(_('button highlight color'), max_length=6, default=settings.VIDEO_BUTTON_HIGHLIGHT_COLOR, help_text=_('Hexadecimal, eg ff00cc'))
    
        
    def __unicode__(self):
        if self.movie:
            name = self.movie.path
        else:
            name = self.movie_url
        return u"%s" % basename(name)

    def get_height(self):
        return "%s" % (self.height)
    
    def get_width(self):
        return "%s" % (self.width)    
    
    def get_movie(self):
        if self.movie:
            return self.movie.url
        else:
            return self.movie_url


########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

VIDEO_WIDTH = getattr(settings, "VIDEO_WIDTH", 320)
VIDEO_HEIGHT = getattr(settings, "VIDEO_HEIGHT", 240)

VIDEO_AUTOPLAY = getattr(settings, "VIDEO_AUTOPLAY", False)
VIDEO_AUTOHIDE = getattr(settings, "VIDEO_AUTOHIDE", False)
VIDEO_FULLSCREEN = getattr(settings, "VIDEO_FULLSCREEN", True)
VIDEO_LOOP = getattr(settings, "VIDEO_LOOP", False)

VIDEO_BG_COLOR = getattr(settings, "VIDEO_BG_COLOR", "000000")
VIDEO_TEXT_COLOR = getattr(settings, "VIDEO_TEXT_COLOR", "FFFFFF")
VIDEO_SEEKBAR_COLOR = getattr(settings, "VIDEO_SEEKBAR_COLOR", "13ABEC")
VIDEO_SEEKBARBG_COLOR = getattr(settings, "VIDEO_SEEKBARBG_COLOR", "333333")
VIDEO_LOADINGBAR_COLOR = getattr(settings, "VIDEO_LOADINGBAR_COLOR", "828282")
VIDEO_BUTTON_OUT_COLOR = getattr(settings, "VIDEO_BUTTON_OUT_COLOR", "333333")
VIDEO_BUTTON_OVER_COLOR = getattr(settings, "VIDEO_BUTTON_OVER_COLOR", "000000")
VIDEO_BUTTON_HIGHLIGHT_COLOR = getattr(settings, "VIDEO_BUTTON_HIGHLIGHT_COLOR", "FFFFFF")

VIDEO_PLUGIN_ENABLE_ADVANCED_SETTINGS = getattr(settings, "VIDEO_PLUGIN_ENABLE_ADVANCED_SETTINGS", True)

########NEW FILE########
__FILENAME__ = clipboardadmin
#-*- coding: utf-8 -*-
from django.forms.models import modelform_factory
from django.contrib import admin
from django.http import HttpResponse
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt
from filer import settings as filer_settings
from filer.models import Clipboard, ClipboardItem
from filer.utils.files import handle_upload, UploadException
from filer.utils.loader import load_object


# ModelAdmins
class ClipboardItemInline(admin.TabularInline):
    model = ClipboardItem


class ClipboardAdmin(admin.ModelAdmin):
    model = Clipboard
    inlines = [ClipboardItemInline]
    filter_horizontal = ('files',)
    raw_id_fields = ('user',)
    verbose_name = "DEBUG Clipboard"
    verbose_name_plural = "DEBUG Clipboards"

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(ClipboardAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            url(r'^operations/paste_clipboard_to_folder/$',
                self.admin_site.admin_view(views.paste_clipboard_to_folder),
                name='filer-paste_clipboard_to_folder'),
            url(r'^operations/discard_clipboard/$',
                self.admin_site.admin_view(views.discard_clipboard),
                name='filer-discard_clipboard'),
            url(r'^operations/delete_clipboard/$',
                self.admin_site.admin_view(views.delete_clipboard),
                name='filer-delete_clipboard'),
            # upload does it's own permission stuff (because of the stupid
            # flash missing cookie stuff)
            url(r'^operations/upload/$',
                self.ajax_upload,
                name='filer-ajax_upload'),
        )
        url_patterns.extend(urls)
        return url_patterns

    @csrf_exempt
    def ajax_upload(self, request, folder_id=None):
        """
        receives an upload from the uploader. Receives only one file at the time.
        """
        try:
            upload, filename, is_raw = handle_upload(request)

            # Get clipboad
            clipboard = Clipboard.objects.get_or_create(user=request.user)[0]

            # find the file type
            for filer_class in filer_settings.FILER_FILE_MODELS:
                FileSubClass = load_object(filer_class)
                #TODO: What if there are more than one that qualify?
                if FileSubClass.matches_file_type(filename, upload, request):
                    FileForm = modelform_factory(
                        model = FileSubClass,
                        fields = ('original_filename', 'owner', 'file')
                    )
                    break
            uploadform = FileForm({'original_filename': filename,
                                   'owner': request.user.pk},
                                  {'file': upload})
            if uploadform.is_valid():
                file_obj = uploadform.save(commit=False)
                # Enforce the FILER_IS_PUBLIC_DEFAULT
                file_obj.is_public = filer_settings.FILER_IS_PUBLIC_DEFAULT
                file_obj.save()
                clipboard_item = ClipboardItem(
                                    clipboard=clipboard, file=file_obj)
                clipboard_item.save()
                json_response = {
                    'thumbnail': file_obj.icons['32'],
                    'alt_text': '',
                    'label': unicode(file_obj),
                }
                return HttpResponse(simplejson.dumps(json_response), mimetype='application/json')
            else:
                form_errors = '; '.join(['%s: %s' % (
                    field,
                    ', '.join(errors)) for field, errors in uploadform.errors.items()
                ])
                raise UploadException("AJAX request not valid: form invalid '%s'" % (form_errors,))
        except UploadException, e:
            return HttpResponse(simplejson.dumps({'error': unicode(e)}), mimetype='application/json')


    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

########NEW FILE########
__FILENAME__ = fileadmin
#-*- coding: utf-8 -*-
from django import forms
from django.contrib.admin.util import unquote
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext  as _
from filer import settings
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.models import File


class FileAdminChangeFrom(forms.ModelForm):
    class Meta:
        model = File


class FileAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('label',)
    list_per_page = 10
    search_fields = ['name', 'original_filename', 'sha1', 'description']
    raw_id_fields = ('owner',)
    readonly_fields = ('sha1',)

    # save_as hack, because without save_as it is impossible to hide the
    # save_and_add_another if save_as is False. To show only save_and_continue
    # and save in the submit row we need save_as=True and in
    # render_change_form() override add and change to False.
    save_as = True

    form = FileAdminChangeFrom

    def response_change(self, request, obj):
        """
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        """
        r = super(FileAdmin, self).response_change(request, obj)
        if r['Location']:
            # it was a successful save
            if r['Location'] in ['../']:
                # this means it was a save: redirect to the directory view
                if obj.folder:
                    url = reverse('admin:filer-directory_listing',
                                  kwargs={'folder_id': obj.folder.id})
                else:
                    url = reverse(
                            'admin:filer-directory_listing-unfiled_images')
                return HttpResponseRedirect(url)
            else:
                # this means it probably was a save_and_continue_editing
                pass
        return r

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        extra_context = {'show_delete': True}
        context.update(extra_context)
        return super(FileAdmin, self).render_change_form(
                    request=request, context=context, add=False, change=False,
                    form_url=form_url, obj=obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Overrides the default to enable redirecting to the directory view after
        deletion of a image.

        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it
        impossible to find out the parent folder to redirect to.
        """
        parent_folder = None
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.folder
        except self.model.DoesNotExist:
            obj = None

        r = super(FileAdmin, self).delete_view(
                    request=request, object_id=object_id,
                    extra_context=extra_context)

        url = r.get("Location", None)
        if url in ["../../../../", "../../"]:
            if parent_folder:
                url = reverse('admin:filer-directory_listing',
                                  kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-unfiled_images')
            return HttpResponseRedirect(url)
        return r

    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

if settings.FILER_ENABLE_PERMISSIONS:
    FileAdmin.fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'description')
        }),
        (None, {
            'fields': ('is_public',)
        }),
        (_('Advanced'), {
            'fields': ('file', 'sha1',),
            'classes': ('collapse',),
        }),
    )
else:
    FileAdmin.fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'description')
        }),
        (_('Advanced'), {
            'fields': ('file', 'sha1',),
            'classes': ('collapse',),
        }),
    )

########NEW FILE########
__FILENAME__ = folderadmin
#-*- coding: utf-8 -*-
from django import forms
from django import template
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.util import quote, unquote, get_deleted_objects, capfirst
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db import router
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext, ugettext_lazy
from filer import settings
from filer.admin.forms import CopyFilesAndFoldersForm, ResizeImagesForm, RenameFilesForm
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.admin.tools import popup_status, selectfolder_status, \
    userperms_for_request, check_folder_edit_permissions, check_files_edit_permissions, \
    check_files_read_permissions, check_folder_read_permissions
from filer.models import Folder, FolderRoot, UnfiledImages, \
    ImagesWithMissingData, File, tools, FolderPermission, Image
from filer.settings import FILER_STATICMEDIA_PREFIX, FILER_PAGINATE_BY
from filer.utils.filer_easy_thumbnails import FilerActionThumbnailer
from filer.thumbnail_processors import normalize_subject_location
from django.conf import settings as django_settings
import urllib
import os
import itertools
import inspect


class AddFolderPopupForm(forms.ModelForm):
    folder = forms.HiddenInput()

    class Meta:
        model = Folder
        fields = ('name',)


class FolderAdmin(PrimitivePermissionAwareModelAdmin):
    list_display = ('name',)
    exclude = ('parent',)
    list_per_page = 20
    list_filter = ('owner',)
    search_fields = ['name', 'files__name']
    raw_id_fields = ('owner',)
    save_as = True  # see ImageAdmin
    actions = ['move_to_clipboard', 'files_set_public', 'files_set_private', 'delete_files_or_folders', 'move_files_and_folders', 'copy_files_and_folders', 'resize_images', 'rename_files']

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            return AddFolderPopupForm
        else:
            return super(FolderAdmin, self).get_form(
                                                request, obj=None, **kwargs)

    def save_form(self, request, form, change):
        """
        Given a ModelForm return an unsaved instance. ``change`` is True if
        the object is being changed, and False if it's being added.
        """
        r = form.save(commit=False)
        parent_id = request.REQUEST.get('parent_id', None)
        if parent_id:
            parent = Folder.objects.get(id=parent_id)
            r.parent = parent
        return r

    def response_change(self, request, obj):
        """
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view
        """
        r = super(FolderAdmin, self).response_change(request, obj)
        if r['Location']:
            # it was a successful save
            if r['Location'] in ['../']:
                if obj.parent:
                    url = reverse('admin:filer-directory_listing',
                                  kwargs={'folder_id': obj.parent.id})
                else:
                    url = reverse('admin:filer-directory_listing-root')
                return HttpResponseRedirect(url)
            else:
                # this means it probably was a save_and_continue_editing
                pass
        return r

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        extra_context = {'show_delete': True}
        context.update(extra_context)
        return super(FolderAdmin, self).render_change_form(
                        request=request, context=context, add=False,
                        change=False, form_url=form_url, obj=obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Overrides the default to enable redirecting to the directory view after
        deletion of a folder.

        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it
        impossible to find out the parent folder to redirect to.
        """
        parent_folder = None
        try:
            obj = self.queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.parent
        except self.model.DoesNotExist:
            obj = None

        r = super(FolderAdmin, self).delete_view(
                    request=request, object_id=object_id,
                    extra_context=extra_context)
        url = r.get("Location", None)
        if url in ["../../../../", "../../"]:
            if parent_folder:
                url = reverse('admin:filer-directory_listing',
                                  kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-root')
            return HttpResponseRedirect(url)
        return r

    def icon_img(self, xs):
        return mark_safe(('<img src="%simg/icons/plainfolder_32x32.png" ' + \
                          'alt="Folder Icon" />') % FILER_STATICMEDIA_PREFIX)
    icon_img.allow_tags = True

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(FolderAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            # we override the default list view with our own directory listing
            # of the root directories
            url(r'^$', self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing-root'),
            url(r'^(?P<folder_id>\d+)/list/$',
                self.admin_site.admin_view(self.directory_listing),
                name='filer-directory_listing'),

            url(r'^(?P<folder_id>\d+)/make_folder/$',
                self.admin_site.admin_view(views.make_folder),
                name='filer-directory_listing-make_folder'),
            url(r'^make_folder/$',
                self.admin_site.admin_view(views.make_folder),
                name='filer-directory_listing-make_root_folder'),

            url(r'^images_with_missing_data/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'images_with_missing_data'},
                name='filer-directory_listing-images_with_missing_data'),
            url(r'^unfiled_images/$',
                self.admin_site.admin_view(self.directory_listing),
                {'viewtype': 'unfiled_images'},
                name='filer-directory_listing-unfiled_images'),
        )
        url_patterns.extend(urls)
        return url_patterns

    # custom views
    def directory_listing(self, request, folder_id=None, viewtype=None):
        clipboard = tools.get_user_clipboard(request.user)
        if viewtype == 'images_with_missing_data':
            folder = ImagesWithMissingData()
        elif viewtype == 'unfiled_images':
            folder = UnfiledImages()
        elif folder_id == None:
            folder = FolderRoot()
        else:
            try:
                folder = Folder.objects.get(id=folder_id)
            except Folder.DoesNotExist:
                raise Http404

        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)

        # Remove action checkboxes if there aren't any actions available.
        list_display = list(self.list_display)
        if not actions:
            try:
                list_display.remove('action_checkbox')
            except ValueError:
                pass

        # search
        def filter_folder(qs, terms=[]):
            for term in terms:
                qs = qs.filter(Q(name__icontains=term) | \
                               Q(owner__username__icontains=term) | \
                               Q(owner__first_name__icontains=term) | \
                               Q(owner__last_name__icontains=term))
            return qs

        def filter_file(qs, terms=[]):
            for term in terms:
                qs = qs.filter(Q(name__icontains=term) | \
                               Q(description__icontains=term) | \
                               Q(original_filename__icontains=term) | \
                               Q(owner__username__icontains=term) | \
                               Q(owner__first_name__icontains=term) | \
                               Q(owner__last_name__icontains=term))
            return qs
        q = request.GET.get('q', None)
        if q:
            search_terms = urllib.unquote_plus(q).split(" ")
        else:
            search_terms = []
            q = ''
        limit_search_to_folder = request.GET.get('limit_search_to_folder',
                                                 False) in (True, 'on')

        if len(search_terms) > 0:
            if folder and limit_search_to_folder and not folder.is_root:
                folder_qs = folder.get_descendants()
                file_qs = File.objects.filter(
                                        folder__in=folder.get_descendants())
            else:
                folder_qs = Folder.objects.all()
                file_qs = File.objects.all()
            folder_qs = filter_folder(folder_qs, search_terms)
            file_qs = filter_file(file_qs, search_terms)

            show_result_count = True
        else:
            folder_qs = folder.children.all()
            file_qs = folder.files.all()
            show_result_count = False

        folder_qs = folder_qs.order_by('name')
        file_qs = file_qs.order_by('name')

        folder_children = []
        folder_files = []
        if folder.is_root:
            folder_children += folder.virtual_folders
        for f in folder_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    folder_children.append(f)
                else:
                    pass
            else:
                folder_children.append(f)
        for f in file_qs:
            f.perms = userperms_for_request(f, request)
            if hasattr(f, 'has_read_permission'):
                if f.has_read_permission(request):
                    folder_files.append(f)
                else:
                    pass
            else:
                folder_files.append(f)
        try:
            permissions = {
                'has_edit_permission': folder.has_edit_permission(request),
                'has_read_permission': folder.has_read_permission(request),
                'has_add_children_permission': \
                                folder.has_add_children_permission(request),
            }
        except:
            permissions = {}
        folder_files.sort()
        items = folder_children + folder_files
        paginator = Paginator(items, FILER_PAGINATE_BY)

        # Make sure page request is an int. If not, deliver first page.
        try:
            page = int(request.GET.get('page', '1'))
        except ValueError:
            page = 1

        # Are we moving to clipboard?
        if request.method == 'POST' and '_save' not in request.POST:
            for f in folder_files:
                if "move-to-clipboard-%d" % (f.id,) in request.POST:
                    clipboard = tools.get_user_clipboard(request.user)
                    if f.has_edit_permission(request):
                        tools.move_file_to_clipboard([f], clipboard)
                        return HttpResponseRedirect(request.get_full_path())
                    else:
                        raise PermissionDenied

        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, files_queryset=file_qs, folders_queryset=folder_qs)
                if response:
                    return response
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)

        # Actions with confirmation
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, files_queryset=file_qs, folders_queryset=folder_qs)
                if response:
                    return response

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
        else:
            action_form = None

        selection_note_all = ungettext('%(total_count)s selected',
            'All %(total_count)s selected', paginator.count)

        # If page request (9999) is out of range, deliver last page of results.
        try:
            paginated_items = paginator.page(page)
        except (EmptyPage, InvalidPage):
            paginated_items = paginator.page(paginator.num_pages)
        return render_to_response(
            'admin/filer/folder/directory_listing.html',
            {
                'folder': folder,
                'clipboard_files': File.objects.filter(
                    in_clipboards__clipboarditem__clipboard__user=request.user
                    ).distinct(),
                'paginator': paginator,
                'paginated_items': paginated_items,
                'permissions': permissions,
                'permstest': userperms_for_request(folder, request),
                'current_url': request.path,
                'title': u'Directory listing for %s' % folder.name,
                'search_string': ' '.join(search_terms),
                'q': urllib.quote_plus(q),
                'show_result_count': show_result_count,
                'limit_search_to_folder': limit_search_to_folder,
                'is_popup': popup_status(request),
                'select_folder': selectfolder_status(request),
                # needed in the admin/base.html template for logout links
                'root_path': "/%s" % admin.site.root_path,
                'action_form': action_form,
                'actions_on_top': self.actions_on_top,
                'actions_on_bottom': self.actions_on_bottom,
                'actions_selection_counter': self.actions_selection_counter,
                'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(paginated_items.object_list)},
                'selection_note_all': selection_note_all % {'total_count': paginator.count},
                'media': self.media,
                'enable_permissions': settings.FILER_ENABLE_PERMISSIONS
        }, context_instance=RequestContext(request))

    def response_action(self, request, files_queryset, folders_queryset):
        """
        Handle an admin action. This is called if a request is POSTed to the
        changelist; it returns an HttpResponse if the action was handled, and
        None otherwise.
        """

        # There can be multiple action forms on the page (at the top
        # and bottom of the change list, for example). Get the action
        # whose button was pushed.
        try:
            action_index = int(request.POST.get('index', 0))
        except ValueError:
            action_index = 0

        # Construct the action form.
        data = request.POST.copy()
        data.pop(helpers.ACTION_CHECKBOX_NAME, None)
        data.pop("index", None)

        # Use the action whose button was pushed
        try:
            data.update({'action': data.getlist('action')[action_index]})
        except IndexError:
            # If we didn't get an action from the chosen form that's invalid
            # POST data, so by deleting action it'll fail the validation check
            # below. So no need to do anything here
            pass

        action_form = self.action_form(data, auto_id=None)
        action_form.fields['action'].choices = self.get_action_choices(request)

        # If the form's valid we can handle the action.
        if action_form.is_valid():
            action = action_form.cleaned_data['action']
            select_across = action_form.cleaned_data['select_across']
            func, name, description = self.get_actions(request)[action]

            # Get the list of selected PKs. If nothing's selected, we can't
            # perform an action on it, so bail. Except we want to perform
            # the action explicitly on all objects.
            selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
            if not selected and not select_across:
                # Reminder that something needs to be selected or nothing will happen
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)
                return None

            if not select_across:
                selected_files = []
                selected_folders = []

                for pk in selected:
                    if pk[:5] == "file-":
                        selected_files.append(pk[5:])
                    else:
                        selected_folders.append(pk[7:])

                # Perform the action only on the selected objects
                files_queryset = files_queryset.filter(pk__in=selected_files)
                folders_queryset = folders_queryset.filter(pk__in=selected_folders)

            response = func(self, request, files_queryset, folders_queryset)

            # Actions may return an HttpResponse, which will be used as the
            # response from the POST. If not, we'll be a good little HTTP
            # citizen and redirect back to the changelist page.
            if isinstance(response, HttpResponse):
                return response
            else:
                return HttpResponseRedirect(request.get_full_path())
        else:
            msg = _("No action selected.")
            self.message_user(request, msg)
            return None

    def get_actions(self, request):
        actions = super(FolderAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def move_to_clipboard(self, request, files_queryset, folders_queryset):
        """
        Action which moves the selected files and files in selected folders to clipboard.
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return None

        clipboard = tools.get_user_clipboard(request.user)

        check_files_edit_permissions(request, files_queryset)
        check_folder_edit_permissions(request, folders_queryset)

        # TODO: Display a confirmation page if moving more than X files to clipboard?

        files_count = [0]  # We define it like that so that we can modify it inside the move_files function

        def move_files(files):
            files_count[0] += tools.move_file_to_clipboard(files, clipboard)

        def move_folders(folders):
            for f in folders:
                move_files(f.files)
                move_folders(f.children.all())

        move_files(files_queryset)
        move_folders(folders_queryset)

        self.message_user(request, _("Successfully moved %(count)d files to clipboard.") % {
            "count": files_count[0],
        })

        return None

    move_to_clipboard.short_description = ugettext_lazy("Move selected files to clipboard")

    def files_set_public_or_private(self, request, set_public, files_queryset, folders_queryset):
        """
        Action which enables or disables permissions for selected files and files in selected folders to clipboard (set them private or public).
        """

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method != 'POST':
            return None

        check_files_edit_permissions(request, files_queryset)
        check_folder_edit_permissions(request, folders_queryset)

        files_count = [0]  # We define it like that so that we can modify it inside the set_files function

        def set_files(files):
            for f in files:
                if f.is_public != set_public:
                    f.is_public = set_public
                    f.save()
                    files_count[0] += 1

        def set_folders(folders):
            for f in folders:
                set_files(f.files)
                set_folders(f.children.all())

        set_files(files_queryset)
        set_folders(folders_queryset)

        if set_public:
            self.message_user(request, _("Successfully disabled permissions for %(count)d files.") % {
                "count": files_count[0],
            })
        else:
            self.message_user(request, _("Successfully enabled permissions for %(count)d files.") % {
                "count": files_count[0],
            })

        return None

    def files_set_private(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(request, False, files_queryset, folders_queryset)

    files_set_private.short_description = ugettext_lazy("Enable permissions for selected files")

    def files_set_public(self, request, files_queryset, folders_queryset):
        return self.files_set_public_or_private(request, True, files_queryset, folders_queryset)

    files_set_public.short_description = ugettext_lazy("Disable permissions for selected files")

    def delete_files_or_folders(self, request, files_queryset, folders_queryset):
        """
        Action which deletes the selected files and/or folders.

        This action first displays a confirmation page whichs shows all the
        deleteable files and/or folders, or, if the user has no permission on one of the related
        childs (foreignkeys), a "permission denied" message.

        Next, it delets all selected files and/or folders and redirects back to the folder.
        """
        opts = self.model._meta
        app_label = opts.app_label

        # Check that the user has delete permission for the actual model
        if not self.has_delete_permission(request):
            raise PermissionDenied

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)

        all_protected = []

        # Populate deletable_objects, a data structure of all related objects that
        # will also be deleted.
        # Hopefully this also checks for necessary permissions.
        # TODO: Check if permissions are really verified
        (args, varargs, keywords, defaults) = inspect.getargspec(get_deleted_objects)
        if 'levels_to_root' in args:
            # Django 1.2
            deletable_files, perms_needed_files = get_deleted_objects(files_queryset, files_queryset.model._meta, request.user, self.admin_site, levels_to_root=2)
            deletable_folders, perms_needed_folders = get_deleted_objects(folders_queryset, folders_queryset.model._meta, request.user, self.admin_site, levels_to_root=2)
        else:
            # Django 1.3
            using = router.db_for_write(self.model)
            deletable_files, perms_needed_files, protected_files = get_deleted_objects(files_queryset, files_queryset.model._meta, request.user, self.admin_site, using)
            deletable_folders, perms_needed_folders, protected_folders = get_deleted_objects(folders_queryset, folders_queryset.model._meta, request.user, self.admin_site, using)
            all_protected.extend(protected_files)
            all_protected.extend(protected_folders)

        all_deletable_objects = [deletable_files, deletable_folders]
        all_perms_needed = perms_needed_files.union(perms_needed_folders)

        # The user has already confirmed the deletion.
        # Do the deletion and return a None to display the change list view again.
        if request.POST.get('post'):
            if all_perms_needed:
                raise PermissionDenied
            n = files_queryset.count() + folders_queryset.count()
            if n:
                for f in files_queryset:
                    self.log_deletion(request, f, force_unicode(f))
                    f.delete()
                for f in folders_queryset:
                    self.log_deletion(request, f, force_unicode(f))
                    f.delete()
                self.message_user(request, _("Successfully deleted %(count)d files and/or folders.") % {
                    "count": n,
                })
            # Return None to display the change list page again.
            return None

        if all_perms_needed or all_protected:
            title = _("Cannot delete files and/or folders")
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "instance": current_folder,
            "breadcrumbs_action": _("Delete files and/or folders"),
            "deletable_objects": all_deletable_objects,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": all_perms_needed,
            "protected": all_protected,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the destination folder selection page
        return render_to_response([
            "admin/filer/delete_selected_files_confirmation.html"
        ], context, context_instance=template.RequestContext(request))

    delete_files_or_folders.short_description = ugettext_lazy("Delete selected files and/or folders")

    # Copied from django.contrib.admin.util
    def _format_callback(self, obj, user, admin_site, perms_needed):
        has_admin = obj.__class__ in admin_site._registry
        opts = obj._meta
        if has_admin:
            admin_url = reverse('%s:%s_%s_change'
                                % (admin_site.name,
                                   opts.app_label,
                                   opts.object_name.lower()),
                                None, (quote(obj._get_pk_val()),))
            p = '%s.%s' % (opts.app_label,
                           opts.get_delete_permission())
            if not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
            # Display a link to the admin page.
            return mark_safe(u'%s: <a href="%s">%s</a>' %
                             (escape(capfirst(opts.verbose_name)),
                              admin_url,
                              escape(obj)))
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return u'%s: %s' % (capfirst(opts.verbose_name),
                                force_unicode(obj))

    def _check_copy_perms(self, request, files_queryset, folders_queryset):
        try:
            check_files_read_permissions(request, files_queryset)
            check_folder_read_permissions(request, folders_queryset)
        except PermissionDenied:
            return True
        return False

    def _check_move_perms(self, request, files_queryset, folders_queryset):
        try:
            check_files_read_permissions(request, files_queryset)
            check_folder_read_permissions(request, folders_queryset)
            check_files_edit_permissions(request, files_queryset)
            check_folder_edit_permissions(request, folders_queryset)
        except PermissionDenied:
            return True
        return False

    def _get_current_action_folder(self, request, files_queryset, folders_queryset):
        if files_queryset:
            return files_queryset[0].folder
        elif folders_queryset:
            return folders_queryset[0].parent
        else:
            return None

    def _list_folders_to_copy_or_move(self, request, folders):
        for fo in folders:
            yield self._format_callback(fo, request.user, self.admin_site, set())
            children = list(self._list_folders_to_copy_or_move(request, fo.children.all()))
            children.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(fo.files)])
            if children:
                yield children

    def _list_all_to_copy_or_move(self, request, files_queryset, folders_queryset):
        to_copy_or_move = list(self._list_folders_to_copy_or_move(request, folders_queryset))
        to_copy_or_move.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(files_queryset)])
        return to_copy_or_move

    def _list_all_destination_folders_recursive(self, request, folders_queryset, current_folder, folders, allow_self, level):
        for fo in folders:
            if not allow_self and fo in folders_queryset:
                # We do not allow moving to selected folders or their descendants
                continue

            if not fo.has_read_permission(request):
                continue

            # We do not allow copying/moving back to the folder itself
            enabled = (allow_self or fo != current_folder) and fo.has_add_children_permission(request)
            yield (fo, (mark_safe(("&nbsp;&nbsp;" * level) + force_unicode(fo)), enabled))
            for c in self._list_all_destination_folders_recursive(request, folders_queryset, current_folder, fo.children.all(), allow_self, level + 1):
                yield c

    def _list_all_destination_folders(self, request, folders_queryset, current_folder, allow_self):
        return list(self._list_all_destination_folders_recursive(request, folders_queryset, current_folder, FolderRoot().children, allow_self, 0))

    def _move_files_and_folders_impl(self, files_queryset, folders_queryset, destination):
        for f in files_queryset:
            f.folder = destination
            f.save()
        for f in folders_queryset:
            f.move_to(destination, 'last-child')
            f.save()

    def move_files_and_folders(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_move_perms(request, files_queryset, folders_queryset)
        to_move = self._list_all_to_copy_or_move(request, files_queryset, folders_queryset)
        folders = self._list_all_destination_folders(request, folders_queryset, current_folder, False)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            try:
                destination = Folder.objects.get(pk=request.POST.get('destination'))
            except Folder.DoesNotExist:
                raise PermissionDenied
            folders_dict = dict(folders)
            if destination not in folders_dict or not folders_dict[destination][1]:
                raise PermissionDenied
            # We count only topmost files and folders here
            n = files_queryset.count() + folders_queryset.count()
            if n:
                self._move_files_and_folders_impl(files_queryset, folders_queryset, destination)
                self.message_user(request, _("Successfully moved %(count)d files and/or folders to folder '%(destination)s'.") % {
                    "count": n,
                    "destination": destination,
                })
            return None

        context = {
            "title": _("Move files and/or folders"),
            "instance": current_folder,
            "breadcrumbs_action": _("Move files and/or folders"),
            "to_move": to_move,
            "destination_folders": folders,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the destination folder selection page
        return render_to_response([
            "admin/filer/folder/choose_move_destination.html"
        ], context, context_instance=template.RequestContext(request))

    move_files_and_folders.short_description = ugettext_lazy("Move selected files and/or folders")

    def _rename_file(self, file, form_data, counter, global_counter):
        original_basename, original_extension = os.path.splitext(file.original_filename)
        if file.name:
            current_basename, current_extension = os.path.splitext(file.name)
        else:
            current_basename = ""
            current_extension = ""
        file.name = form_data['rename_format'] % {
                'original_filename': file.original_filename,
                'original_basename': original_basename,
                'original_extension': original_extension,
                'current_filename': file.name or "",
                'current_basename': current_basename,
                'current_extension': current_extension,
                'current_folder': file.folder.name,
                'counter': counter + 1, # 1-based
                'global_counter': global_counter + 1, # 1-based
            }
        file.save()

    def _rename_files(self, files, form_data, global_counter):
        n = 0
        for f in sorted(files):
            self._rename_file(f, form_data, n, global_counter + n)
            n += 1
        return n

    def _rename_folder(self, folder, form_data, global_counter):
        return self._rename_images_impl(folder.files.all(), folder.children.all(), form_data, global_counter)

    def _rename_files_impl(self, files_queryset, folders_queryset, form_data, global_counter):
        n = 0

        for f in folders_queryset:
            n += self._rename_folder(f, form_data, global_counter + n)

        n += self._rename_files(files_queryset, form_data, global_counter + n)

        return n

    def rename_files(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_move_perms(request, files_queryset, folders_queryset)
        to_rename = self._list_all_to_copy_or_move(request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            form = RenameFilesForm(request.POST)
            if form.is_valid():
                if files_queryset.count() + folders_queryset.count():
                    n = self._rename_files_impl(files_queryset, folders_queryset, form.cleaned_data, 0)
                    self.message_user(request, _("Successfully renamed %(count)d files.") % {
                        "count": n,
                    })
                return None
        else:
            form = RenameFilesForm()

        context = {
            "title": _("Rename files"),
            "instance": current_folder,
            "breadcrumbs_action": _("Rename files"),
            "to_rename": to_rename,
            "rename_form": form,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the rename format selection page
        return render_to_response([
            "admin/filer/folder/choose_rename_format.html"
        ], context, context_instance=template.RequestContext(request))

    rename_files.short_description = ugettext_lazy("Rename files")

    def _generate_new_filename(self, filename, suffix):
        basename, extension = os.path.splitext(filename)
        return basename + suffix + extension

    def _copy_file(self, file, destination, suffix, overwrite):
        if overwrite:
            # Not yet implemented as we have to find a portable (for different storage backends) way to overwrite files
            raise NotImplementedError

        # We are assuming here that we are operating on an already saved database objects with current database state available

        filename = self._generate_new_filename(file.file.name, suffix)

        # Due to how inheritance works, we have to set both pk and id to None
        file.pk = None
        file.id = None
        file.save()
        file.folder = destination
        file.file = file._copy_file(filename)
        file.original_filename = self._generate_new_filename(file.original_filename, suffix)
        file.save()

    def _copy_files(self, files, destination, suffix, overwrite):
        for f in files:
            self._copy_file(f, destination, suffix, overwrite)
        return len(files)

    def _get_available_name(self, destination, name):
        count = itertools.count(1)
        original = name
        while destination.contains_folder(name):
            name = "%s_%s" % (original, count.next())
        return name

    def _copy_folder(self, folder, destination, suffix, overwrite):
        if overwrite:
            # Not yet implemented as we have to find a portable (for different storage backends) way to overwrite files
            raise NotImplementedError

        # TODO: Should we also allow not to overwrite the folder if it exists, but just copy into it?

        # TODO: Is this a race-condition? Would this be a problem?
        foldername = self._get_available_name(destination, folder.name)

        old_folder = Folder.objects.get(pk=folder.pk)

        # Due to how inheritance works, we have to set both pk and id to None
        folder.pk = None
        folder.id = None
        folder.name = foldername
        folder.insert_at(destination, 'last-child', True)  # We save folder here

        for perm in FolderPermission.objects.filter(folder=old_folder):
            perm.pk = None
            perm.id = None
            perm.folder = folder
            perm.save()

        return 1 + self._copy_files_and_folders_impl(old_folder.files.all(), old_folder.children.all(), folder, suffix, overwrite)

    def _copy_files_and_folders_impl(self, files_queryset, folders_queryset, destination, suffix, overwrite):
        n = self._copy_files(files_queryset, destination, suffix, overwrite)

        for f in folders_queryset:
            n += self._copy_folder(f, destination, suffix, overwrite)

        return n

    def copy_files_and_folders(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_copy_perms(request, files_queryset, folders_queryset)
        to_copy = self._list_all_to_copy_or_move(request, files_queryset, folders_queryset)
        folders = self._list_all_destination_folders(request, folders_queryset, current_folder, True)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            form = CopyFilesAndFoldersForm(request.POST)
            if form.is_valid():
                try:
                    destination = Folder.objects.get(pk=request.POST.get('destination'))
                except Folder.DoesNotExist:
                    raise PermissionDenied
                folders_dict = dict(folders)
                if destination not in folders_dict or not folders_dict[destination][1]:
                    raise PermissionDenied
                if files_queryset.count() + folders_queryset.count():
                    # We count all files and folders here (recursivelly)
                    n = self._copy_files_and_folders_impl(files_queryset, folders_queryset, destination, form.cleaned_data['suffix'], False)
                    self.message_user(request, _("Successfully copied %(count)d files and/or folders to folder '%(destination)s'.") % {
                        "count": n,
                        "destination": destination,
                    })
                return None
        else:
            form = CopyFilesAndFoldersForm()

        try:
            selected_destination_folder = int(request.POST.get('destination', 0))
        except ValueError:
            selected_destination_folder = 0

        context = {
            "title": _("Copy files and/or folders"),
            "instance": current_folder,
            "breadcrumbs_action": _("Copy files and/or folders"),
            "to_copy": to_copy,
            "destination_folders": folders,
            "selected_destination_folder": selected_destination_folder or current_folder.pk,
            "copy_form": form,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the destination folder selection page
        return render_to_response([
            "admin/filer/folder/choose_copy_destination.html"
        ], context, context_instance=template.RequestContext(request))

    copy_files_and_folders.short_description = ugettext_lazy("Copy selected files and/or folders")

    def _check_resize_perms(self, request, files_queryset, folders_queryset):
        try:
            check_files_read_permissions(request, files_queryset)
            check_folder_read_permissions(request, folders_queryset)
            check_files_edit_permissions(request, files_queryset)
        except PermissionDenied:
            return True
        return False

    def _list_folders_to_resize(self, request, folders):
        for fo in folders:
            children = list(self._list_folders_to_resize(request, fo.children.all()))
            children.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(fo.files) if isinstance(f, Image)])
            if children:
                yield self._format_callback(fo, request.user, self.admin_site, set())
                yield children

    def _list_all_to_resize(self, request, files_queryset, folders_queryset):
        to_resize = list(self._list_folders_to_resize(request, folders_queryset))
        to_resize.extend([self._format_callback(f, request.user, self.admin_site, set()) for f in sorted(files_queryset) if isinstance(f, Image)])
        return to_resize

    def _new_subject_location(self, original_width, original_height, new_width, new_height, x, y, crop):
        # TODO: We could probably do better
        return (round(new_width / 2), round(new_height / 2))

    def _resize_image(self, image, form_data):
        original_width = float(image.width)
        original_height = float(image.height)
        thumbnailer = FilerActionThumbnailer(file=image.file.file, name=image.file.name, source_storage=image.file.source_storage, thumbnail_storage=image.file.source_storage)
        # This should overwrite the original image
        new_image = thumbnailer.get_thumbnail({
            'size': (form_data['width'], form_data['height']),
            'crop': form_data['crop'],
            'upscale': form_data['upscale'],
            'subject_location': image.subject_location,
        })
        from django.db.models.fields.files import ImageFieldFile
        image.file.file = new_image.file
        image.generate_sha1()
        image.save()  # Also gets new width and height

        subject_location = normalize_subject_location(image.subject_location)
        if subject_location:
            (x, y) = subject_location
            x = float(x)
            y = float(y)
            new_width = float(image.width)
            new_height = float(image.height)
            (new_x, new_y) = self._new_subject_location(original_width, original_height, new_width, new_height, x, y, form_data['crop'])
            image.subject_location = "%d,%d" % (new_x, new_y)
            image.save()

    def _resize_images(self, files, form_data):
        n = 0
        for f in files:
            if isinstance(f, Image):
                self._resize_image(f, form_data)
                n += 1
        return n

    def _resize_folder(self, folder, form_data):
        return self._resize_images_impl(folder.files.all(), folder.children.all(), form_data)

    def _resize_images_impl(self, files_queryset, folders_queryset, form_data):
        n = self._resize_images(files_queryset, form_data)

        for f in folders_queryset:
            n += self._resize_folder(f, form_data)

        return n

    def resize_images(self, request, files_queryset, folders_queryset):
        opts = self.model._meta
        app_label = opts.app_label

        current_folder = self._get_current_action_folder(request, files_queryset, folders_queryset)
        perms_needed = self._check_resize_perms(request, files_queryset, folders_queryset)
        to_resize = self._list_all_to_resize(request, files_queryset, folders_queryset)

        if request.method == 'POST' and request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            form = ResizeImagesForm(request.POST)
            if form.is_valid():
                if form.cleaned_data.get('thumbnail_option'):
                    form.cleaned_data['width'] = form.cleaned_data['thumbnail_option'].width
                    form.cleaned_data['height'] = form.cleaned_data['thumbnail_option'].height
                    form.cleaned_data['crop'] = form.cleaned_data['thumbnail_option'].crop
                    form.cleaned_data['upscale'] = form.cleaned_data['thumbnail_option'].upscale
                if files_queryset.count() + folders_queryset.count():
                    # We count all files here (recursivelly)
                    n = self._resize_images_impl(files_queryset, folders_queryset, form.cleaned_data)
                    self.message_user(request, _("Successfully resized %(count)d images.") % {
                         "count": n,
                    })
                return None
        else:
            form = ResizeImagesForm()

        context = {
            "title": _("Resize images"),
            "instance": current_folder,
            "breadcrumbs_action": _("Resize images"),
            "to_resize": to_resize,
            "resize_form": form,
            "cmsplugin_enabled": 'cmsplugin_filer_image' in django_settings.INSTALLED_APPS,
            "files_queryset": files_queryset,
            "folders_queryset": folders_queryset,
            "perms_lacking": perms_needed,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        }

        # Display the resize options page
        return render_to_response([
            "admin/filer/folder/choose_images_resize_options.html"
        ], context, context_instance=template.RequestContext(request))

    resize_images.short_description = ugettext_lazy("Resize selected images")

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.db import models
from django.contrib.admin import widgets
from filer.utils.files import get_valid_filename
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.conf import settings


if 'cmsplugin_filer_image' in settings.INSTALLED_APPS:
    from cmsplugin_filer_image.models import ThumbnailOption


class AsPWithHelpMixin(object):
    def as_p_with_help(self):
        "Returns this form rendered as HTML <p>s with help text formated for admin."
        return self._html_output(
            normal_row=u'<p%(html_class_attr)s>%(label)s %(field)s</p>%(help_text)s',
            error_row=u'%s',
            row_ender='</p>',
            help_text_html=u'<p class="help">%s</p>',
            errors_on_separate_row=True)


class CopyFilesAndFoldersForm(forms.Form, AsPWithHelpMixin):
    suffix = forms.CharField(required=False, help_text=_("Suffix which will be appended to filenames of copied files."))
    # TODO: We have to find a way to overwrite files with different storage backends first.
    #overwrite_files = forms.BooleanField(required=False, help_text=_("Overwrite a file if there already exists a file with the same filename?"))

    def clean_suffix(self):
        valid = get_valid_filename(self.cleaned_data['suffix'])
        if valid != self.cleaned_data['suffix']:
            raise forms.ValidationError(_('Suffix should be a valid, simple and lowercase filename part, like "%(valid)s".') % {'valid': valid})
        return self.cleaned_data['suffix']


class RenameFilesForm(forms.Form, AsPWithHelpMixin):
    rename_format = forms.CharField(required=True)

    def clean_rename_format(self):
        try:
            self.cleaned_data['rename_format'] % {
                'original_filename': 'filename',
                'original_basename': 'basename',
                'original_extension': 'ext',
                'current_filename': 'filename',
                'current_basename': 'basename',
                'current_extension': 'ext',
                'current_folder': 'folder',
                'counter': 42,
                'global_counter': 42,
            }
        except KeyError, e:
            raise forms.ValidationError(_('Unknown rename format value key "%(key)s".') % {'key': e.args[0]})
        except Exception, e:
            raise forms.ValidationError(_('Invalid rename format: %(error)s.') % {'error': e})
        return self.cleaned_data['rename_format']


class ResizeImagesForm(forms.Form, AsPWithHelpMixin):
    if 'cmsplugin_filer_image' in settings.INSTALLED_APPS:
        thumbnail_option = models.ForeignKey(ThumbnailOption, null=True, blank=True, verbose_name=_("thumbnail option")).formfield()
    width = models.PositiveIntegerField(_("width"), null=True, blank=True).formfield(widget=widgets.AdminIntegerFieldWidget)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True).formfield(widget=widgets.AdminIntegerFieldWidget)
    crop = models.BooleanField(_("crop"), default=True).formfield()
    upscale = models.BooleanField(_("upscale"), default=True).formfield()

    def clean(self):
        if not (self.cleaned_data.get('thumbnail_option') or ((self.cleaned_data.get('width') or 0) + (self.cleaned_data.get('height') or 0))):
            if 'cmsplugin_filer_image' in settings.INSTALLED_APPS:
                raise ValidationError(_('Thumbnail option or resize parameters must be choosen.'))
            else:
                raise ValidationError(_('Resize parameters must be choosen.'))
        return self.cleaned_data

########NEW FILE########
__FILENAME__ = imageadmin
#-*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext  as _
from filer import settings as filer_settings
from filer.admin.fileadmin import FileAdmin
from filer.models import Image


class ImageAdminFrom(forms.ModelForm):
    subject_location = forms.CharField(
                    max_length=64, required=False,
                    label=_('Subject location'),
                    help_text=_('Location of the main subject of the scene.'))

    def sidebar_image_ratio(self):
        if self.instance:
            # this is very important. It forces the value to be returned as a
            # string and always with a "." as seperator. If the conversion
            # from float to string is done in the template, the locale will
            # be used and in some cases there would be a "," instead of ".".
            # javascript would parse that to an integer.
            return  "%.6F" % self.instance.sidebar_image_ratio()
        else:
            return ''

    class Meta:
        model = Image

    class Media:
        css = {
            #'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        }
        js = (
            filer_settings.FILER_STATICMEDIA_PREFIX + 'js/raphael.js',
            filer_settings.FILER_STATICMEDIA_PREFIX + 'js/focal_point.js',
        )


class ImageAdmin(FileAdmin):
    form = ImageAdminFrom
    fieldsets = (
        FileAdmin.fieldsets[0],
        (_('Advanced'), {
            'fields': ('default_alt_text', 'default_caption',
                       'author', 'file', 'sha1',),
            'classes': ('collapse',),
        }),
        ('Subject Location', {
            'fields': ('subject_location',),
            'classes': ('collapse',),
        }),
    )

########NEW FILE########
__FILENAME__ = permissionadmin
#-*- coding: utf-8 -*-
from django.contrib import admin
from filer.fields import folder


class PermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': (('type', 'folder',))}),
        (None, {'fields': (('user', 'group', 'everybody'),)}),
        (None, {'fields': (
                    ('can_edit', 'can_read', 'can_add_children')
                    )}
        ),
    )
    raw_id_fields = ('user', 'group',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        db = kwargs.get('using')
        if db_field.name == 'folder':
            kwargs['widget'] = folder.AdminFolderWidget(db_field.rel, using=db)
        return super(PermissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

########NEW FILE########
__FILENAME__ = permissions
#-*- coding: utf-8 -*-
from django.contrib import admin


class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # we don't have a "add" permission... but all adding is handled
        # by special methods that go around these permissions anyway
        # TODO: reactivate return False
        return False

    def has_change_permission(self, request, obj=None):
        if hasattr(obj, 'has_edit_permission'):
            if obj.has_edit_permission(request):
                return True
            else:
                return False
        else:
            return True

    def has_delete_permission(self, request, obj=None):
        # we don't have a specific delete permission... so we use change
        return self.has_change_permission(request, obj)

########NEW FILE########
__FILENAME__ = tools
#-*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied


def popup_status(request):
    return '_popup' in request.REQUEST or 'pop' in request.REQUEST


def selectfolder_status(request):
    return 'select_folder' in request.REQUEST


def popup_param(request):
    if popup_status(request):
        return "?_popup=1"
    else:
        return ""


def check_files_edit_permissions(request, files):
    for f in files:
        if not f.has_edit_permission(request):
            raise PermissionDenied


def check_folder_edit_permissions(request, folders):
    for f in folders:
        if not f.has_edit_permission(request):
            raise PermissionDenied
        check_files_edit_permissions(request, f.files)
        check_folder_edit_permissions(request, f.children.all())


def check_files_read_permissions(request, files):
    for f in files:
        if not f.has_read_permission(request):
            raise PermissionDenied


def check_folder_read_permissions(request, folders):
    for f in folders:
        if not f.has_read_permission(request):
            raise PermissionDenied
        check_files_read_permissions(request, f.files)
        check_folder_read_permissions(request, f.children.all())


def userperms_for_request(item, request):
    r = []
    ps = ['read', 'edit', 'add_children']
    for p in ps:
        attr = "has_%s_permission" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append(p)
    return r

########NEW FILE########
__FILENAME__ = file
#-*- coding: utf-8 -*-
from django import forms
from django.conf import settings as globalsettings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import truncate_words
from filer.models import File
from filer.settings import FILER_STATICMEDIA_PREFIX


class AdminFileWidget(ForeignKeyRawIdWidget):
    choices = None

    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id', 'id_image_x')
        css_id_thumbnail_img = "%s_thumbnail_img" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        related_url = None
        if value:
            try:
                file = File.objects.get(pk=value)
                related_url = file.logical_folder.\
                                get_admin_directory_listing_url_path()
            except Exception:
                pass
        if not related_url:
            related_url = reverse('admin:filer-directory_listing-root')
        params = self.url_parameters()
        if params:
            lookup_url = '?' + '&amp;'.join(
                                ['%s=%s' % (k, v) for k, v in params.items()])
        else:
            lookup_url = ''
        if not 'class' in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # rendering the super for ForeignKeyRawIdWidget on purpose here because
        # we only need the input and none of the other stuff that
        # ForeignKeyRawIdWidget adds
        hidden_input = super(ForeignKeyRawIdWidget, self).render(
                                                            name, value, attrs)
        filer_static_prefix = FILER_STATICMEDIA_PREFIX
        if not filer_static_prefix[-1] == '/':
            filer_static_prefix += '/'
        context = {
            'hidden_input': hidden_input,
            'lookup_url': '%s%s' % (related_url, lookup_url),
            'thumb_id': css_id_thumbnail_img,
            'span_id': css_id_description_txt,
            'object': obj,
            'lookup_name': name,
            'admin_media_prefix': globalsettings.ADMIN_MEDIA_PREFIX,
            'filer_static_prefix': filer_static_prefix,
            'clear_id': '%s_clear' % css_id,
            'id': css_id,
        }
        html = render_to_string('admin/filer/widgets/admin_file.html', context)
        return mark_safe(html)

    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)

    def obj_for_value(self, value):
        try:
            key = self.rel.get_related_field().name
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            obj = None
        return obj

    class Media:
        js = (FILER_STATICMEDIA_PREFIX + 'js/popup_handling.js',)


class AdminFileFormField(forms.ModelChoiceField):
    widget = AdminFileWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        other_widget = kwargs.pop('widget', None)
        forms.Field.__init__(self, widget=self.widget(rel), *args, **kwargs)

    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


class FilerFileField(models.ForeignKey):
    default_form_class = AdminFileFormField
    default_model_class = File

    def __init__(self, **kwargs):
        # we call ForeignKey.__init__ with the Image model as parameter...
        # a FilerImageFiled can only be a ForeignKey to a Image
        self.validate_related_name(kwargs.get('related_name', None))
        return super(FilerFileField, self).__init__(
                                        self.default_model_class, **kwargs)

    def validate_related_name(self, name):
        if not name:
            return
        if name and hasattr(self.default_model_class, name):
            raise ImproperlyConfigured(
                ("%s fields cannot have related name %r, this property " + \
                 "already exists on %s") % (self.__class__.__name__,
                                  name,
                                  self.default_form_class.__name__)
            )

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {
            'form_class': self.default_form_class,
            'rel': self.rel,
        }
        defaults.update(kwargs)
        return super(FilerFileField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

########NEW FILE########
__FILENAME__ = folder
#-*- coding: utf-8 -*-
from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.text import truncate_words
from django.utils.translation import ugettext as _
from filer.models import Folder
from filer.settings import FILER_STATICMEDIA_PREFIX


class AdminFolderWidget(ForeignKeyRawIdWidget):
    choices = None
    input_type = 'hidden'
    is_hidden = True

    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id')
        css_id_folder = "%s_folder" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        required = self.attrs
        if attrs is None:
            attrs = {}
        related_url = reverse('admin:filer-directory_listing-root')
        params = self.url_parameters()
        params['select_folder'] = 1
        if params:
            url = '?' + '&amp;'.join(
                            ['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not 'class' in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        output = []
        if obj:
            output.append(u'Folder: <span id="%s">%s</span>' % (
                                            css_id_description_txt, obj.name))
        else:
            output.append((u'Folder: <span id="%s">' + \
                           u'none selected</span>') % css_id_description_txt)
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append(
            (u'<a href="%s%s" class="related-lookup" id="lookup_id_%s"' + \
             u'onclick="return showRelatedObjectLookupPopup(this);"> ') % \
                (related_url, url, name))
        output.append(('<img src="%simg/admin/selector-search.gif" ' +\
                       'width="16" height="16" alt="%s" /></a>') % (
                                    settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
        output.append('</br>')
        clearid = '%s_clear' % css_id
        output.append(
            (u'<img id="%s" src="%simg/admin/icon_deletelink.gif" ' +\
             u'width="10" height="10" alt="%s" title="%s"/>') % (
                            clearid, settings.ADMIN_MEDIA_PREFIX,
                            _('Clear'), _('Clear')))
        output.append('<br />')
        super_attrs = attrs.copy()
        output.append(super(ForeignKeyRawIdWidget, self).render(
                                                    name, value, super_attrs))
        noimgurl = '%sicons/nofile_32x32.png' % FILER_STATICMEDIA_PREFIX
        js = '''<script type="text/javascript">django.jQuery("#%(id)s").hide();
django.jQuery("#%(id)s_clear").click(function(){
    django.jQuery("#%(id)s").removeAttr("value");
    django.jQuery("#%(foldid)s").attr("src", "%(noimg)s");
    django.jQuery("#%(descid)s").html("");
});
django.jQuery(document).ready(function(){
    var plus = django.jQuery("#add_%(id)s");
    if (plus.length){
        plus.remove();
    }
});
</script>'''
        output.append(js % {'id': css_id, 'foldid': css_id_folder,
                            'noimg': noimgurl,
                            'descid': css_id_description_txt})
        return mark_safe(u''.join(output))

    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)

    def obj_for_value(self, value):
        try:
            key = self.rel.get_related_field().name
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            obj = None
        return obj

    class Media:
        js = (FILER_STATICMEDIA_PREFIX + 'js/popup_handling.js',)


class AdminFolderFormField(forms.ModelChoiceField):
    widget = AdminFolderWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        kwargs.pop('widget', None)
        forms.Field.__init__(self, widget=self.widget(rel), *args, **kwargs)

    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


class FilerFolderField(models.ForeignKey):
    default_form_class = AdminFolderFormField
    default_model_class = Folder

    def __init__(self, **kwargs):
        return super(FilerFolderField, self).__init__(Folder, **kwargs)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {
            'form_class': self.default_form_class,
            'rel': self.rel,
        }
        defaults.update(kwargs)
        return super(FilerFolderField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

########NEW FILE########
__FILENAME__ = image
#-*- coding: utf-8 -*-
from filer.fields.file import AdminFileWidget, AdminFileFormField, \
    FilerFileField
from filer.models import Image


class AdminImageWidget(AdminFileWidget):
    pass


class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget


class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = Image

########NEW FILE########
__FILENAME__ = multistorage_file
#-*- coding: utf-8 -*-
from django.core.files.base import File
from django.core.files.storage import Storage
from easy_thumbnails import fields as easy_thumbnails_fields, \
    files as easy_thumbnails_files
from filer import settings as filer_settings
from filer.utils.filer_easy_thumbnails import ThumbnailerNameMixin


STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_STORAGE,
}
THUMBNAIL_STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_THUMBNAIL_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE,
}


def generate_filename_multistorage(instance, filename):
    if instance.is_public:
        upload_to = filer_settings.FILER_PUBLICMEDIA_UPLOAD_TO
    else:
        upload_to = filer_settings.FILER_PRIVATEMEDIA_UPLOAD_TO

    if callable(upload_to):
        return upload_to(instance, filename)
    else:
        return upload_to


class MultiStorageFieldFile(ThumbnailerNameMixin,
                            easy_thumbnails_files.ThumbnailerFieldFile):
    def __init__(self, instance, field, name):
        File.__init__(self, None, name)
        self.instance = instance
        self.field = field
        self._committed = True
        self.storages = self.field.storages
        self.thumbnail_storages = self.field.thumbnail_storages

    @property
    def storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']

    @property
    def source_storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']

    @property
    def thumbnail_storage(self):
        if self.instance.is_public:
            return self.thumbnail_storages['public']
        else:
            return self.thumbnail_storages['private']


class MultiStorageFileField(easy_thumbnails_fields.ThumbnailerField):
    attr_class = MultiStorageFieldFile

    def __init__(self, verbose_name=None, name=None, upload_to_dict=None,
                 storages=None, thumbnail_storages=None, **kwargs):
        self.storages = storages or STORAGES
        self.thumbnail_storages = thumbnail_storages or THUMBNAIL_STORAGES
        super(easy_thumbnails_fields.ThumbnailerField, self).__init__(
                                      verbose_name=verbose_name, name=name,
                                      upload_to=generate_filename_multistorage,
                                      storage=None, **kwargs)

########NEW FILE########
__FILENAME__ = import_files
#-*- coding: utf-8 -*-
from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand, NoArgsCommand
from filer.models.filemodels import File
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.settings import FILER_IS_PUBLIC_DEFAULT
from optparse import make_option
import os


class FileImporter(object):
    def __init__(self, * args, **kwargs):
        self.path = kwargs.get('path')
        self.base_folder = kwargs.get('base_folder')
        self.verbosity = int(kwargs.get('verbosity', 1))
        self.file_created = 0
        self.image_created = 0
        self.folder_created = 0

    def import_file(self, file, folder):
        """
        Create a File or an Image into the given folder
        """
        try:
            iext = os.path.splitext(file.name)[1].lower()
        except:
            iext = ''
        if iext in ['.jpg', '.jpeg', '.png', '.gif']:
            obj, created = Image.objects.get_or_create(
                                original_filename=file.name,
                                file=file,
                                folder=folder,
                                is_public=FILER_IS_PUBLIC_DEFAULT)
            if created:
                self.image_created += 1
        else:
            obj, created = File.objects.get_or_create(
                                original_filename=file.name,
                                file=file,
                                folder=folder,
                                is_public=FILER_IS_PUBLIC_DEFAULT)
            if created:
                self.file_created += 1
        if self.verbosity >= 2:
            print u"file_created #%s / image_created #%s -- file : %s -- created : %s" % (self.file_created,
                                                        self.image_created,
                                                        obj, created)
        return obj

    def get_or_create_folder(self, folder_names):
        """
        Gets or creates a Folder based the list of folder names in hierarchical
        order (like breadcrumbs).

        get_or_create_folder(['root', 'subfolder', 'subsub folder'])

        creates the folders with correct parent relations and returns the
        'subsub folder' instance.
        """
        if not len(folder_names):
            return None
        current_parent = None
        for folder_name in folder_names:
            current_parent, created = Folder.objects.get_or_create(name=folder_name, parent=current_parent)
            if created:
                self.folder_created += 1
                if self.verbosity >= 2:
                    print u"folder_created #%s folder : %s -- created : %s" % (self.folder_created,
                                                                               current_parent, created)
        return current_parent

    def walker(self, path=None, base_folder=None):
        """
        This method walk a directory structure and create the
        Folders and Files as they appear.
        """
        path = path or self.path
        base_folder = base_folder or self.base_folder
        # prevent trailing slashes and other inconsistencies on path.
        # cast to unicode so that os.walk returns path names in unicode
        # (prevents encoding/decoding errors)
        path = unicode(os.path.normpath(path))
        if base_folder:
            base_folder = unicode(os.path.normpath(base_folder))
            print u"The directory structure will be imported in %s" % (base_folder,)
        if self.verbosity >= 1:
            print u"Import the folders and files in %s" % (path,)
        root_folder_name = os.path.basename(path)
        for root, dirs, files in os.walk(path):
            rel_folders = root.partition(path)[2].strip(os.path.sep).split(os.path.sep)
            while '' in rel_folders:
                rel_folders.remove('')
            if base_folder:
                folder_names = base_folder.split('/') + [root_folder_name] + rel_folders
            else:
                folder_names = [root_folder_name] + rel_folders
            folder = self.get_or_create_folder(folder_names)
            for file in files:
                dj_file = DjangoFile(open(os.path.join(root, file)),
                                     name=file)
                self.import_file(file=dj_file, folder=folder)
        if self.verbosity >= 1:
            print ('folder_created #%s / file_created #%s / ' + \
                   'image_created #%s') % (
                                self.folder_created, self.file_created,
                                self.image_created)


class Command(NoArgsCommand):
    """
    Import directory structure into the filer ::

        manage.py --path=/tmp/assets/images
        manage.py --path=/tmp/assets/news --folder=images
    """

    option_list = BaseCommand.option_list + (
        make_option('--path',
            action='store',
            dest='path',
            default=False,
            help='Import files located in the path into django-filer'),
        make_option('--folder',
            action='store',
            dest='base_folder',
            default=False,
            help='Specify the destination folder in which the directory structure should be imported'),
        )

    def handle_noargs(self, **options):
        file_importer = FileImporter(**options)
        file_importer.walker()

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Image'
        db.create_table('filer_image', (
            ('file_ptr', orm['filer.Image:file_ptr']),
            ('_height', orm['filer.Image:_height']),
            ('_width', orm['filer.Image:_width']),
            ('date_taken', orm['filer.Image:date_taken']),
            ('default_alt_text', orm['filer.Image:default_alt_text']),
            ('default_caption', orm['filer.Image:default_caption']),
            ('author', orm['filer.Image:author']),
            ('must_always_publish_author_credit', orm['filer.Image:must_always_publish_author_credit']),
            ('must_always_publish_copyright', orm['filer.Image:must_always_publish_copyright']),
            ('subject_location', orm['filer.Image:subject_location']),
        ))
        db.send_create_signal('filer', ['Image'])
        
        # Adding model 'ClipboardItem'
        db.create_table('filer_clipboarditem', (
            ('id', orm['filer.ClipboardItem:id']),
            ('file', orm['filer.ClipboardItem:file']),
            ('clipboard', orm['filer.ClipboardItem:clipboard']),
        ))
        db.send_create_signal('filer', ['ClipboardItem'])
        
        # Adding model 'File'
        db.create_table('filer_file', (
            ('id', orm['filer.File:id']),
            ('folder', orm['filer.File:folder']),
            ('file_field', orm['filer.File:file_field']),
            ('_file_type_plugin_name', orm['filer.File:_file_type_plugin_name']),
            ('_file_size', orm['filer.File:_file_size']),
            ('has_all_mandatory_data', orm['filer.File:has_all_mandatory_data']),
            ('original_filename', orm['filer.File:original_filename']),
            ('name', orm['filer.File:name']),
            ('owner', orm['filer.File:owner']),
            ('uploaded_at', orm['filer.File:uploaded_at']),
            ('modified_at', orm['filer.File:modified_at']),
        ))
        db.send_create_signal('filer', ['File'])
        
        # Adding model 'Folder'
        db.create_table('filer_folder', (
            ('id', orm['filer.Folder:id']),
            ('parent', orm['filer.Folder:parent']),
            ('name', orm['filer.Folder:name']),
            ('owner', orm['filer.Folder:owner']),
            ('uploaded_at', orm['filer.Folder:uploaded_at']),
            ('created_at', orm['filer.Folder:created_at']),
            ('modified_at', orm['filer.Folder:modified_at']),
            ('lft', orm['filer.Folder:lft']),
            ('rght', orm['filer.Folder:rght']),
            ('tree_id', orm['filer.Folder:tree_id']),
            ('level', orm['filer.Folder:level']),
        ))
        db.send_create_signal('filer', ['Folder'])
        
        # Adding model 'Clipboard'
        db.create_table('filer_clipboard', (
            ('id', orm['filer.Clipboard:id']),
            ('user', orm['filer.Clipboard:user']),
        ))
        db.send_create_signal('filer', ['Clipboard'])
        
        # Adding model 'FolderPermission'
        db.create_table('filer_folderpermission', (
            ('id', orm['filer.FolderPermission:id']),
            ('folder', orm['filer.FolderPermission:folder']),
            ('type', orm['filer.FolderPermission:type']),
            ('user', orm['filer.FolderPermission:user']),
            ('group', orm['filer.FolderPermission:group']),
            ('everybody', orm['filer.FolderPermission:everybody']),
            ('can_edit', orm['filer.FolderPermission:can_edit']),
            ('can_read', orm['filer.FolderPermission:can_read']),
            ('can_add_children', orm['filer.FolderPermission:can_add_children']),
        ))
        db.send_create_signal('filer', ['FolderPermission'])
        
        # Creating unique_together for [parent, name] on Folder.
        db.create_unique('filer_folder', ['parent_id', 'name'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [parent, name] on Folder.
        db.delete_unique('filer_folder', ['parent_id', 'name'])
        
        # Deleting model 'Image'
        db.delete_table('filer_image')
        
        # Deleting model 'ClipboardItem'
        db.delete_table('filer_clipboarditem')
        
        # Deleting model 'File'
        db.delete_table('filer_file')
        
        # Deleting model 'Folder'
        db.delete_table('filer_folder')
        
        # Deleting model 'Clipboard'
        db.delete_table('filer_clipboard')
        
        # Deleting model 'FolderPermission'
        db.delete_table('filer_folderpermission')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'file_field': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0002_rename_file_field

from south.db import db
from django.db import models
from filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # rename the file field
        db.rename_column('filer_file', 'file_field', '_file')
        
    
    
    def backwards(self, orm):
        
        db.rename_column('filer_file', '_file', 'file_field')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0003_add_description_field

from south.db import db
from django.db import models
from filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'File.description'
        db.add_column('filer_file', 'description', orm['filer.file:description'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'File.description'
        db.delete_column('filer_file', 'description')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            '_file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0004_auto__del_field_file__file__add_field_file_file__add_field_file_is_pub
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Rename field 'file._file'
        db.rename_column('filer_file', '_file', 'file')

        # Adding field 'File.is_public'
        db.add_column('filer_file', 'is_public', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        
        # no need to do this. south just *thinks* something has changed, because it did not know anything about through in earlier versions
        # Removing M2M table for field files on 'clipboard'
        #db.delete_table('filer_clipboard_files')


    def backwards(self, orm):
        
        # Rename field 'file._file'
        db.rename_column('filer_file', 'file', '_file')

        # Deleting field 'File.is_public'
        db.delete_column('filer_file', 'is_public')
        
        # no need to do this. south just *thinks* something has changed, because it did not know anything about through in earlier versions
        
        # Adding M2M table for field files on 'clipboard'
#        db.create_table('filer_clipboard_files', (
#            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
#            ('clipboard', models.ForeignKey(orm['filer.clipboard'], null=False)),
#            ('file', models.ForeignKey(orm['filer.file'], null=False))
#        ))
#        db.create_unique('filer_clipboard_files', ['clipboard_id', 'file_id'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'Meta': {'object_name': 'Clipboard'},
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'in_clipboards'", 'symmetrical': 'False', 'through': "orm['filer.ClipboardItem']", 'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'Meta': {'object_name': 'ClipboardItem'},
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'Meta': {'object_name': 'FolderPermission'},
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_file_sha1__chg_field_file_file
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'File.sha1'
        db.add_column('filer_file', 'sha1', self.gf('django.db.models.fields.CharField')(default='', max_length=40, blank=True), keep_default=False)

        # Changing field 'File.file'
        db.alter_column('filer_file', 'file', self.gf('django.db.models.fields.files.FileField')(max_length=255, null=True))


    def backwards(self, orm):
        
        # Deleting field 'File.sha1'
        db.delete_column('filer_file', 'sha1')

        # Changing field 'File.file'
        db.alter_column('filer_file', 'file', self.gf('django.db.models.fields.files.FileField')())


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'Meta': {'object_name': 'Clipboard'},
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'in_clipboards'", 'symmetrical': 'False', 'through': "orm['filer.ClipboardItem']", 'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'Meta': {'object_name': 'ClipboardItem'},
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'Meta': {'object_name': 'FolderPermission'},
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0006_polymorphic__add_field_file_polymorphic_ctype
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'File.polymorphic_ctype'
        db.add_column('filer_file', 'polymorphic_ctype', self.gf('django.db.models.fields.related.ForeignKey')(related_name='polymorphic_filer.file_set', null=True, to=orm['contenttypes.ContentType']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'File.polymorphic_ctype'
        db.delete_column('filer_file', 'polymorphic_ctype_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'Meta': {'object_name': 'Clipboard'},
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'in_clipboards'", 'symmetrical': 'False', 'through': "orm['filer.ClipboardItem']", 'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'Meta': {'object_name': 'ClipboardItem'},
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'Meta': {'object_name': 'FolderPermission'},
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0007_polymorphic__content_type_data
# encoding: utf-8
import datetime
from django.core.exceptions import ObjectDoesNotExist
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        try:
            image_ct = orm['contenttypes.ContentType'].objects.get(app_label='filer', model='image').id
            file_ct = orm['contenttypes.ContentType'].objects.get(app_label='filer', model='file').id
            for file in orm['filer.file'].objects.all():
                if file._file_type_plugin_name == 'Image':
                    file.polymorphic_ctype_id = image_ct
                else:
                    file.polymorphic_ctype_id = file_ct
                file.save()
        except ObjectDoesNotExist:
            print "No filer contentypes to migrate. This is probably because migrate is running on a new database."


    def backwards(self, orm):
        "Write your backwards methods here."
        image_ct = orm['contenttypes.ContentType'].objects.get(app_label='filer', model='image').id
        for file in orm['filer.file'].objects.all():
            if file.polymorphic_ctype_id == image_ct:
                file._file_type_plugin_name = "Image"
            else:
                file._file_type_plugin_name = None
            file.save()


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'Meta': {'object_name': 'Clipboard'},
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'in_clipboards'", 'symmetrical': 'False', 'through': "orm['filer.ClipboardItem']", 'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'Meta': {'object_name': 'ClipboardItem'},
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'Meta': {'object_name': 'FolderPermission'},
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = 0008_polymorphic__del_field_file__file_type_plugin_name
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'File._file_type_plugin_name'
        db.delete_column('filer_file', '_file_type_plugin_name')


    def backwards(self, orm):
        
        # Adding field 'File._file_type_plugin_name'
        db.add_column('filer_file', '_file_type_plugin_name', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True), keep_default=False)


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'Meta': {'object_name': 'Clipboard'},
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'in_clipboards'", 'symmetrical': 'False', 'through': "orm['filer.ClipboardItem']", 'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'Meta': {'object_name': 'ClipboardItem'},
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'Meta': {'object_name': 'FolderPermission'},
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['filer']

########NEW FILE########
__FILENAME__ = clipboardmodels
#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer.models import filemodels


class Clipboard(models.Model):
    user = models.ForeignKey(auth_models.User, verbose_name=_('user'), related_name="filer_clipboards")
    files = models.ManyToManyField(
                        'File', verbose_name=_('files'), related_name="in_clipboards",
                        through='ClipboardItem')

    def append_file(self, file):
        try:
            # We have to check if file is already in the clipboard as otherwise polymorphic complains
            self.files.get(pk=file.pk)
            return False
        except filemodels.File.DoesNotExist:
            newitem = ClipboardItem(file=file, clipboard=self)
            newitem.save()
            return True

    def empty(self):
        for item in self.bucket_items.all():
            item.delete()
    empty.alters_data = True

    def __unicode__(self):
        return u"Clipboard %s of %s" % (self.id, self.user)

    class Meta:
        app_label = 'filer'
        verbose_name = _('clipboard')
        verbose_name_plural = _('clipboards')


class ClipboardItem(models.Model):
    file = models.ForeignKey('File', verbose_name=_('file'))
    clipboard = models.ForeignKey(Clipboard, verbose_name=_('clipboard'))

    class Meta:
        app_label = 'filer'
        verbose_name = _('clipboard item')
        verbose_name_plural = _('clipboard items')

########NEW FILE########
__FILENAME__ = filemodels
#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer.fields.multistorage_file import MultiStorageFileField
from filer.models import mixins
from filer import settings as filer_settings
from filer.models.foldermodels import Folder
from polymorphic import PolymorphicModel, PolymorphicManager
import hashlib
import os


class FileManager(PolymorphicManager):
    def find_all_duplicates(self):
        r = {}
        for file in self.all():
            if file.sha1:
                q = self.filter(sha1=file.sha1)
                if len(q) > 1:
                    r[file.sha1] = q
        return r

    def find_duplicates(self, file):
        return [i for i in self.exclude(pk=file.pk).filter(sha1=file.sha1)]


class File(PolymorphicModel, mixins.IconsMixin):
    file_type = 'File'
    _icon = "file"
    folder = models.ForeignKey(Folder, verbose_name=_('folder'), related_name='all_files',
                               null=True, blank=True)
    file = MultiStorageFileField(_('file'), null=True, blank=True, max_length=255)
    _file_size = models.IntegerField(_('file size'), null=True, blank=True)

    sha1 = models.CharField(_('sha1'), max_length=40, blank=True, default='')

    has_all_mandatory_data = models.BooleanField(_('has all mandatory data'), default=False, editable=False)

    original_filename = models.CharField(_('original filename'), max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=_('name'))
    description = models.TextField(null=True, blank=True,
                                   verbose_name=_('description'))

    owner = models.ForeignKey(auth_models.User,
                              related_name='owned_%(class)ss',
                              null=True, blank=True, verbose_name=_('owner'))

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    is_public = models.BooleanField(
                    default=filer_settings.FILER_IS_PUBLIC_DEFAULT,
                    verbose_name=_('Permissions disabled'),
                    help_text=_('Disable any permission checking for this ' +\
                                'file. File will be publicly accessible ' +\
                                'to anyone.'))

    objects = FileManager()

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        return True  # I match all files...

    def __init__(self, *args, **kwargs):
        super(File, self).__init__(*args, **kwargs)
        self._old_is_public = self.is_public

    def _move_file(self):
        """
        Move the file from src to dst.
        """
        src_file_name = self.file.name
        dst_file_name = self._meta.get_field('file').generate_filename(
                                                self, self.original_filename)

        if self.is_public:
            src_storage = self.file.storages['private']
            dst_storage = self.file.storages['public']
        else:
            src_storage = self.file.storages['public']
            dst_storage = self.file.storages['private']

        # delete the thumbnail
        # We are toggling the is_public to make sure that easy_thumbnails can
        # delete the thumbnails
        self.is_public = not self.is_public
        self.file.delete_thumbnails()
        self.is_public = not self.is_public
        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = src_storage.open(src_file_name)
        src_file.open()
        self.file = dst_storage.save(dst_file_name,
                                     ContentFile(src_file.read()))
        src_storage.delete(src_file_name)

    def _copy_file(self, destination, overwrite=False):
        """
        Copies the file to a destination files and returns it.
        """

        if overwrite:
            # If the destination file already exists default storage backend
            # does not overwrite it but generates another filename.
            # TODO: Find a way to override this behavior.
            raise NotImplementedError

        src_file_name = self.file.name
        storage = self.file.storages['public' if self.is_public else 'private']

        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = storage.open(src_file_name)
        src_file.open()
        return storage.save(destination, ContentFile(src_file.read()))

    def generate_sha1(self):
        sha = hashlib.sha1()
        self.file.seek(0)
        sha.update(self.file.read())
        self.sha1 = sha.hexdigest()

    def save(self, *args, **kwargs):
        # check if this is a subclass of "File" or not and set
        # _file_type_plugin_name
        if self.__class__ == File:
            # what should we do now?
            # maybe this has a subclass, but is being saved as a File instance
            # anyway. do we need to go check all possible subclasses?
            pass
        elif issubclass(self.__class__, File):
            self._file_type_plugin_name = self.__class__.__name__
        # cache the file size
        try:
            self._file_size = self.file.size
        except:
            pass
        if self._old_is_public != self.is_public and self.pk:
            self._move_file()
            self._old_is_public = self.is_public
        try:
            self.generate_sha1()
        except Exception, e:
            pass
        super(File, self).save(*args, **kwargs)

    @property
    def label(self):
        if self.name in ['', None]:
            text = self.original_filename or 'unnamed file'
        else:
            text = self.name
        text = u"%s" % (text,)
        return text

    def __lt__(self, other):
        return cmp(self.label.lower(), other.label.lower()) < 0

    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')

    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')

    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')

    def has_generic_permission(self, request, type):
        """
        Return true if the current user has permission on this
        image. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated():
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        elif self.folder:
            return self.folder.has_generic_permission(request, type)
        else:
            return False

    def __unicode__(self):
        if self.name in ('', None):
            text = u"%s" % (self.original_filename,)
        else:
            text = u"%s" % (self.name,)
        return text

    def get_admin_url_path(self):
        return urlresolvers.reverse(
            'admin:%s_%s_change' % (self._meta.app_label,
                                    self._meta.module_name,),
            args=(self.pk,)
        )

    @property
    def url(self):
        """
        to make the model behave like a file field
        """
        try:
            r = self.file.url
        except:
            r = ''
        return r

    @property
    def path(self):
        try:
            return self.file.path
        except:
            return ""

    @property
    def size(self):
        return self._file_size or 0

    @property
    def extension(self):
        filetype = os.path.splitext(self.file.name)[1].lower()
        if len(filetype) > 0:
            filetype = filetype[1:]
        return filetype

    @property
    def logical_folder(self):
        """
        if this file is not in a specific folder return the Special "unfiled"
        Folder object
        """
        if not self.folder:
            from filer.models.virtualitems import UnfiledImages
            return UnfiledImages()
        else:
            return self.folder

    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.folder:
            folder_path.extend(self.folder.get_ancestors())
        folder_path.append(self.logical_folder)
        return folder_path

    @property
    def duplicates(self):
        return File.objects.find_duplicates(self)

    class Meta:
        app_label = 'filer'
        verbose_name = _('file')
        verbose_name_plural = _('files')

########NEW FILE########
__FILENAME__ = foldermodels
#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from filer.models import mixins
from filer import settings as filer_settings

import mptt


class FolderManager(models.Manager):
    def with_bad_metadata(self):
        return self.get_query_set().filter(has_all_mandatory_data=False)


class FolderPermissionManager(models.Manager):
    """
    Theses methods are called by introspection from "has_generic_permisison" on
    the folder model.
    """
    def get_read_id_list(self, user):
        """
        Give a list of a Folders where the user has read rights or the string
        "All" if the user has all rights.
        """
        return self.__get_id_list(user, "can_read")

    def get_edit_id_list(self, user):
        return self.__get_id_list(user, "can_edit")

    def get_add_children_id_list(self, user):
        return self.__get_id_list(user, "can_add_children")

    def __get_id_list(self, user, attr):
        if user.is_superuser or not filer_settings.FILER_ENABLE_PERMISSIONS:
            return 'All'
        allow_list = []
        deny_list = []
        group_ids = user.groups.all().values_list('id', flat=True)
        q = Q(user=user) | Q(group__in=group_ids) | Q(everybody=True)
        perms = self.filter(q).order_by('folder__tree_id', 'folder__level',
                                        'folder__lft')
        for perm in perms:
            if perm.folder:
                folder_id = perm.folder.id
            else:
                folder_id = None
            if perm.type == FolderPermission.ALL:
                if getattr(perm, attr):
                    allow_list = list(Folder.objects.all().values_list(
                                                    'id', flat=True))
                else:
                    return []
            if getattr(perm, attr):
                if folder_id not in allow_list:
                    allow_list.append(folder_id)
                if folder_id in deny_list:
                    deny_list.remove(folder_id)
            else:
                if folder_id not in deny_list:
                    deny_list.append(folder_id)
                if folder_id in allow_list:
                    allow_list.remove(folder_id)
            if perm.type == FolderPermission.CHILDREN:
                for id in perm.folder.get_descendants().values_list(
                                                            'id', flat=True):
                    if getattr(perm, attr):
                        if id not in allow_list:
                            allow_list.append(id)
                        if id in deny_list:
                            deny_list.remove(id)
                    else:
                        if id not in deny_list:
                            deny_list.append(id)
                        if id in allow_list:
                            allow_list.remove(id)
        return allow_list


class Folder(models.Model, mixins.IconsMixin):
    """
    Represents a Folder that things (files) can be put into. Folders are *NOT*
    mirrored in the Filesystem and can have any unicode chars as their name.
    Other models may attach to a folder with a ForeignKey. If the related name
    ends with "_files" they will automatically be listed in the
    folder.files list along with all the other models that link to the folder
    in this way. Make sure the linked models obey the AbstractFile interface
    (Duck Type).
    """
    file_type = 'Folder'
    is_root = False
    can_have_subfolders = True
    _icon = 'plainfolder'

    parent = models.ForeignKey('self', verbose_name=('parent'), null=True, blank=True,
                               related_name='children')
    name = models.CharField(_('name'), max_length=255)

    owner = models.ForeignKey(auth_models.User, verbose_name=('owner'),
                              related_name='filer_owned_folders',
                              null=True, blank=True)

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'),auto_now=True)

    objects = FolderManager()

    @property
    def file_count(self):
        if not hasattr(self, '_file_count_cache'):
            self._file_count_cache = self.files.count()
        return self._file_count_cache

    @property
    def children_count(self):
        if not hasattr(self, '_children_count_cache'):
            self._children_count_cache = self.children.count()
        return self._children_count_cache

    @property
    def item_count(self):
        return self.file_count + self.children_count

    @property
    def files(self):
        return self.all_files.all()

    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.parent:
            folder_path.extend(self.parent.get_ancestors())
            folder_path.append(self.parent)
        return folder_path

    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')

    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')

    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')

    def has_generic_permission(self, request, type):
        """
        Return true if the current user has permission on this
        folder. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated():
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        else:
            att_name = "permission_%s_cache" % type
            if not hasattr(self, "permission_user_cache") or \
               not hasattr(self, att_name) or \
               request.user.pk != self.permission_user_cache.pk:

                # This calls methods on the manager i.e. get_read_id_list()
                func = getattr(FolderPermission.objects,
                               "get_%s_id_list" % type)
                permission = func(user)
                self.permission_user_cache = request.user
                if permission == "All" or self.id in permission:
                    setattr(self, att_name, True)
                    self.permission_edit_cache = True
                else:
                    setattr(self, att_name, False)
            return getattr(self, att_name)

    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_folder_change',
                                    args=(self.id,))

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing',
                                    args=(self.id,))

    def __unicode__(self):
        return u"%s" % (self.name,)

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    class Meta:
        unique_together = (('parent', 'name'),)
        ordering = ('name',)
        permissions = (("can_use_directory_listing",
                        "Can use directory listing"),)
        app_label = 'filer'
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

# MPTT registration
try:
    mptt.register(Folder)
except mptt.AlreadyRegistered:
    pass


class FolderPermission(models.Model):
    ALL = 0
    THIS = 1
    CHILDREN = 2

    TYPES = (
        (ALL, _('all items')),
        (THIS, _('this item only')),
        (CHILDREN, _('this item and all children')),
    )
    folder = models.ForeignKey(Folder, verbose_name=('folder'), null=True, blank=True)

    type = models.SmallIntegerField(_('type'), choices=TYPES, default=0)
    user = models.ForeignKey(auth_models.User,
                             related_name="filer_folder_permissions",
                             verbose_name=_("user"), blank=True, null=True)
    group = models.ForeignKey(auth_models.Group,
                              related_name="filer_folder_permissions",
                              verbose_name=_("group"), blank=True, null=True)
    everybody = models.BooleanField(_("everybody"), default=False)

    can_edit = models.BooleanField(_("can edit"), default=True)
    can_read = models.BooleanField(_("can read"), default=True)
    can_add_children = models.BooleanField(_("can add children"), default=True)

    objects = FolderPermissionManager()

    def __unicode__(self):
        if self.folder:
            name = u'%s' % self.folder
        else:
            name = u'All Folders'

        ug = []
        if self.everybody:
            user = 'Everybody'
        else:
            if self.group:
                ug.append(u"Group: %s" % self.group)
            if self.user:
                ug.append(u"User: %s" % self.user)
        usergroup = " ".join(ug)
        perms = []
        for s in ['can_edit', 'can_read', 'can_add_children']:
            if getattr(self, s):
                perms.append(s)
        perms = ', '.join(perms)
        return u"Folder: '%s'->%s [%s] [%s]" % (
                        name, unicode(self.TYPES[self.type][1]),
                        perms, usergroup)

    class Meta:
        verbose_name = _('folder permission')
        verbose_name_plural = _('folder permissions')
        app_label = 'filer'

########NEW FILE########
__FILENAME__ = imagemodels
#-*- coding: utf-8 -*-
from PIL import Image as PILImage
from datetime import datetime
from django.core import urlresolvers
from django.db import models
from django.utils.translation import ugettext_lazy as _
from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.utils.filer_easy_thumbnails import FilerThumbnailer
from filer.utils.pil_exif import get_exif_for_file
import os

class Image(File):
    SIDEBAR_IMAGE_WIDTH = 210
    DEFAULT_THUMBNAILS = {
        'admin_clipboard_icon': {'size': (32, 32), 'crop': True,
                                 'upscale': True},
        'admin_sidebar_preview': {'size': (SIDEBAR_IMAGE_WIDTH, 10000)},
        'admin_directory_listing_icon': {'size': (48, 48),
                                         'crop': True, 'upscale': True},
        'admin_tiny_icon': {'size': (32, 32), 'crop': True, 'upscale': True},
    }
    file_type = 'Image'
    _icon = "image"

    _height = models.IntegerField(null=True, blank=True)
    _width = models.IntegerField(null=True, blank=True)

    date_taken = models.DateTimeField(_('date taken'), null=True, blank=True,
                                      editable=False)

    default_alt_text = models.CharField(_('default alt text'), max_length=255, blank=True, null=True)
    default_caption = models.CharField(_('default caption'), max_length=255, blank=True, null=True)

    author = models.CharField(_('author'), max_length=255, null=True, blank=True)

    must_always_publish_author_credit = models.BooleanField(_('must always publish author credit'), default=False)
    must_always_publish_copyright = models.BooleanField(_('must always publish copyright'), default=False)

    subject_location = models.CharField(_('subject location'), max_length=64, null=True, blank=True,
                                        default=None)

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
      # This was originally in admin/clipboardadmin.py  it was inside of a try
      # except, I have moved it here outside of a try except because I can't
      # figure out just what kind of exception this could generate... all it was
      # doing for me was obscuring errors...
      # --Dave Butler <croepha@gmail.com>
      iext = os.path.splitext(iname)[1].lower()
      return iext in ['.jpg', '.jpeg', '.png', '.gif']

    def save(self, *args, **kwargs):
        if self.date_taken is None:
            try:
                exif_date = self.exif.get('DateTimeOriginal', None)
                if exif_date is not None:
                    d, t = str.split(exif_date.values)
                    year, month, day = d.split(':')
                    hour, minute, second = t.split(':')
                    self.date_taken = datetime(
                                       int(year), int(month), int(day),
                                       int(hour), int(minute), int(second))
            except:
                pass
        if self.date_taken is None:
            self.date_taken = datetime.now()
        self.has_all_mandatory_data = self._check_validity()
        try:
            # do this more efficient somehow?
            self.file.seek(0)
            self._width, self._height = PILImage.open(self.file).size
        except Exception:
            # probably the image is missing. nevermind.
            pass
        super(Image, self).save(*args, **kwargs)

    def _check_validity(self):
        if not self.name:
            return False
        return True

    def sidebar_image_ratio(self):
        if self.width:
            return float(self.width) / float(self.SIDEBAR_IMAGE_WIDTH)
        else:
            return 1.0

    def _get_exif(self):
        if hasattr(self, '_exif_cache'):
            return self._exif_cache
        else:
            if self.file:
                self._exif_cache = get_exif_for_file(self.file.path)
            else:
                self._exif_cache = {}
        return self._exif_cache
    exif = property(_get_exif)

    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')

    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')

    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')

    def has_generic_permission(self, request, type):
        """
        Return true if the current user has permission on this
        image. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated() or not user.is_staff:
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        elif self.folder:
            return self.folder.has_generic_permission(request, type)
        else:
            return False

    @property
    def label(self):
        if self.name in ['', None]:
            return self.original_filename or 'unnamed file'
        else:
            return self.name

    @property
    def width(self):
        return self._width or 0

    @property
    def height(self):
        return self._height or 0

    @property
    def icons(self):
        _icons = {}
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            try:
                thumbnail_options = {
                    'size': (int(size), int(size)),
                    'crop': True,
                    'upscale': True,
                    'subject_location': self.subject_location}
                thumb = self.file.get_thumbnail(thumbnail_options)
                _icons[size] = thumb.url
            except Exception, e:
                # swallow the the exception to avoid to bubble it up
                # in the template {{ image.icons.48 }}
                pass
        return _icons

    @property
    def thumbnails(self):
        _thumbnails = {}
        for name, opts in Image.DEFAULT_THUMBNAILS.items():
            try:
                opts.update({'subject_location': self.subject_location})
                thumb = self.file.get_thumbnail(opts)
                _thumbnails[name] = thumb.url
            except:
                # swallow the exception to avoid it bubbling up
                # to the template {{ image.icons.48 }}
                pass
        return _thumbnails

    @property
    def easy_thumbnails_thumbnailer(self):
        tn = FilerThumbnailer(file=self.file.file, name=self.file.name,
                         source_storage=self.file.source_storage,
                         thumbnail_storage=self.file.thumbnail_storage)
        return tn

    class Meta:
        app_label = 'filer'
        verbose_name = _('image')
        verbose_name_plural = _('images')

########NEW FILE########
__FILENAME__ = mixins
#-*- coding: utf-8 -*-
from filer.settings import FILER_ADMIN_ICON_SIZES, FILER_STATICMEDIA_PREFIX


class IconsMixin(object):
    """
    Can be used on any model that has a _icon attribute. will return a dict
    containing urls for icons of different sizes with that name.
    """
    @property
    def icons(self):
        r = {}
        if getattr(self, '_icon', False):
            for size in FILER_ADMIN_ICON_SIZES:
                r[size] = "%sicons/%s_%sx%s.png" % (
                            FILER_STATICMEDIA_PREFIX, self._icon, size, size)
        return r

########NEW FILE########
__FILENAME__ = tools
#-*- coding: utf-8 -*-
from filer.models import Clipboard


def discard_clipboard(clipboard):
    clipboard.files.clear()


def delete_clipboard(clipboard):
    for file in clipboard.files.all():
        file.delete()


def get_user_clipboard(user):
    if user.is_authenticated():
        clipboard = Clipboard.objects.get_or_create(user=user)[0]
        return clipboard


def move_file_to_clipboard(files, clipboard):
    count = 0
    for file in files:
        if clipboard.append_file(file):
            file.folder = None
            file.save()
            count += 1
    return count


def move_files_from_clipboard_to_folder(clipboard, folder):
    return move_files_to_folder(clipboard.files.all(), folder)


def move_files_to_folder(files, folder):
    for file in files:
        file.folder = folder
        file.save()
    return True

########NEW FILE########
__FILENAME__ = virtualitems
#-*- coding: utf-8 -*-
from django.core import urlresolvers
from django.utils.translation import ugettext_lazy as _
from filer.models import mixins
from filer.models.filemodels import File
from filer.models.foldermodels import Folder


class DummyFolder(mixins.IconsMixin):
    file_type = 'DummyFolder'
    name = "Dummy Folder"
    is_root = True
    is_smart_folder = True
    can_have_subfolders = False
    parent = None
    _icon = "plainfolder"

    @property
    def virtual_folders(self):
        return []

    @property
    def children(self):
        return Folder.objects.none()

    @property
    def files(self):
        return File.objects.none()
    parent_url = None

    @property
    def image_files(self):
        return self.files

    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        return []


class UnfiledImages(DummyFolder):
    name = _("unfiled files")
    is_root = True
    _icon = "unfiled_folder"

    def _files(self):
        return File.objects.filter(folder__isnull=True)
    files = property(_files)

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse(
                            'admin:filer-directory_listing-unfiled_images')


class ImagesWithMissingData(DummyFolder):
    name = _("files with missing metadata")
    is_root = True
    _icon = "incomplete_metadata_folder"

    @property
    def files(self):
        return File.objects.filter(has_all_mandatory_data=False)

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse(
                    'admin:filer-directory_listing-images_with_missing_data')


class FolderRoot(DummyFolder):
    name = _('root')
    is_root = True
    is_smart_folder = False
    can_have_subfolders = True

    @property
    def virtual_folders(self):
        return [UnfiledImages()]

    @property
    def children(self):
        return Folder.objects.filter(parent__isnull=True)
    parent_url = None

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing-root')

########NEW FILE########
__FILENAME__ = base
#-*- coding: utf-8 -*-
from django.utils.encoding import smart_str
import mimetypes
import os


class ServerBase(object):
    def __init__(self, *args, **kwargs):
        pass

    def get_mimetype(self, path):
        return mimetypes.guess_type(path)[0] or 'application/octet-stream'

    def default_headers(self, **kwargs):
        self.save_as_header(**kwargs)
        self.size_header(**kwargs)

    def save_as_header(self, response, **kwargs):
        """
        * if save_as is False the header will not be added
        * if save_as is a filename, it will be used in the header
        * if save_as is None the filename will be determined from the file path
        """
        save_as = kwargs.get('save_as', None)
        if save_as == False:
            return
        file = kwargs.get('file', None)
        filename = None
        if save_as:
            filename = save_as
        else:
            filename = os.path.basename(file.path)
        response['Content-Disposition'] = smart_str(u'attachment; filename=%s' % filename)

    def size_header(self, response, **kwargs):
        size = kwargs.get('size', None)
        #file = kwargs.get('file', None)
        if size:
            response['Content-Length'] = size
        # we should not do this, because it accesses the file. and that might be an expensive operation.
        # elif file and file.size is not None:
        #     response['Content-Length'] = file.size

########NEW FILE########
__FILENAME__ = default
#-*- coding: utf-8 -*-
import os
import stat
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.utils.http import http_date
from django.views.static import was_modified_since
from filer.server.backends.base import ServerBase


class DefaultServer(ServerBase):
    """
    Serve static files from the local filesystem through django.
    This is a bad idea for most situations other than testing.

    This will only work for files that can be accessed in the local filesystem.
    """
    def serve(self, request, file, **kwargs):
        fullpath = file.path
        # the following code is largely borrowed from `django.views.static.serve`
        # and django-filetransfers: filetransfers.backends.default
        if not os.path.exists(fullpath):
            raise Http404('"%s" does not exist' % fullpath)
        # Respect the If-Modified-Since header.
        statobj = os.stat(fullpath)
        mimetype = self.get_mimetype(fullpath)
        if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                                  statobj[stat.ST_MTIME], statobj[stat.ST_SIZE]):
            return HttpResponseNotModified(mimetype=mimetype)
        response = HttpResponse(open(fullpath, 'rb').read(), mimetype=mimetype)
        response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
        self.default_headers(request=request, response=response, file=file, **kwargs)
        return response

########NEW FILE########
__FILENAME__ = nginx
#-*- coding: utf-8 -*-
from django.http import HttpResponse
from filer.server.backends.base import ServerBase


class NginxXAccelRedirectServer(ServerBase):
    """
    This returns a response with only headers set, so that nginx actually does
    the serving
    """
    def __init__(self, location, nginx_location):
        """
        nginx_location
        """
        self.location = location
        self.nginx_location = nginx_location

    def get_nginx_location(self, path):
        return path.replace(self.location, self.nginx_location)

    def serve(self, request, file, **kwargs):
        # we should not use get_mimetype() here, because it tries to access the file in the filesystem.
        #response = HttpResponse(mimetype=self.get_mimetype(file.path))
        response = HttpResponse()
        nginx_path = self.get_nginx_location(file.path)
        response['X-Accel-Redirect'] = nginx_path
        self.default_headers(request=request, response=response, file=file, **kwargs)
        return response

########NEW FILE########
__FILENAME__ = xsendfile
#-*- coding: utf-8 -*-
from django.http import HttpResponse
from filer.server.backends.base import ServerBase


class ApacheXSendfileServer(ServerBase):
    def serve(self, request, file, **kwargs):
        response = HttpResponse()
        response['X-Sendfile'] = file.path

        # This is needed for lighttpd, hopefully this will
        # not be needed after this is fixed:
        # http://redmine.lighttpd.net/issues/2076
        response['Content-Type'] = self.get_mimetype(file.path)

        self.default_headers(request=request, response=response, file=file, **kwargs)
        return response

########NEW FILE########
__FILENAME__ = urls
#-*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from filer import settings as filer_settings

urlpatterns = patterns('filer.server.views',
    url(r'^' + filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url.lstrip('/') + r'(?P<path>.*)$',
        'serve_protected_file',),

    url(r'^' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url.lstrip('/') + r'(?P<path>.*)$',
        'serve_protected_thumbnail',),
)

########NEW FILE########
__FILENAME__ = views
#-*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from easy_thumbnails.files import ThumbnailFile
from filer import settings as filer_settings
from filer.models import File
from filer.utils.filer_easy_thumbnails import thumbnail_to_original_filename

server = filer_settings.FILER_PRIVATEMEDIA_SERVER
thumbnail_server = filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_SERVER


def serve_protected_file(request, path):
    """
    Serve protected files to authenticated users with read permissions.
    """
    try:
        thefile = File.objects.get(file=path, is_public=False)
    except File.DoesNotExist:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    return server.serve(request, file=thefile.file, save_as=False)


def serve_protected_thumbnail(request, path):
    """
    Serve protected thumbnails to authenticated users.
    If the user doesn't have read permissions, redirect to a static image.
    """
    source_path = thumbnail_to_original_filename(path)
    if not source_path:
        raise Http404('File not found')
    try:
        thefile = File.objects.get(file=source_path, is_public=False)
    except File.DoesNotExist:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    try:
        thumbnail = ThumbnailFile(name=path, storage=thefile.file.thumbnail_storage)
        return thumbnail_server.serve(request, thumbnail, save_as=False)
    except Exception:
        raise Http404('File not found')

########NEW FILE########
__FILENAME__ = settings
#-*- coding: utf-8 -*-
from django.conf import settings
from filer.server.backends.default import DefaultServer
from filer.storage import PublicFileSystemStorage, PrivateFileSystemStorage
from filer.utils.loader import load_object, storage_factory
import os
import urlparse

FILER_ENABLE_PERMISSIONS = getattr(settings, 'FILER_ENABLE_PERMISSIONS', False)

FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS = getattr(settings, 'FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS', False)

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 20)

FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', True)

FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', None)
if not FILER_STATICMEDIA_PREFIX:
    FILER_STATICMEDIA_PREFIX = (getattr(settings, 'STATIC_URL', None) or settings.MEDIA_URL) + 'filer/'

FILER_ADMIN_ICON_SIZES = (
        '16', '32', '48', '64',
)

# This is an ordered iterable that describes a list of 
# classes that I should check for when adding files
FILER_FILE_MODELS = getattr(settings, 'FILER_FILE_MODELS',
    (
        'filer.models.imagemodels.Image',
        'filer.models.filemodels.File',
    )
)

# Public media (media accessible without any permission checks)
FILER_PUBLICMEDIA_STORAGE = getattr(
                    settings,
                    'FILER_PUBLICMEDIA_STORAGE',
                    storage_factory(
                        klass=PublicFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         'filer')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  'filer/')
                    ))
FILER_PUBLICMEDIA_UPLOAD_TO = load_object(getattr(settings, 'FILER_PUBLICMEDIA_UPLOAD_TO', 'filer.utils.generate_filename.by_date'))
FILER_PUBLICMEDIA_THUMBNAIL_STORAGE = getattr(
                    settings,
                    'FILER_PUBLICMEDIA_THUMBNAIL_STORAGE',
                    storage_factory(
                        klass=PublicFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         'filer_thumbnails')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  'filer_thumbnails/')
                    ))


# Private media (media accessible through permissions checks)
FILER_PRIVATEMEDIA_STORAGE = getattr(
                    settings,
                    'FILER_PRIVATEMEDIA_STORAGE',
                    storage_factory(
                        klass=PrivateFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         '../smedia/filer/')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  '/smedia/filer/')
                    ))
FILER_PRIVATEMEDIA_UPLOAD_TO = load_object(getattr(settings, 'FILER_PRIVATEMEDIA_UPLOAD_TO',
                                       'filer.utils.generate_filename.by_date'))
FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE = getattr(
                    settings,
                   'FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE',
                    storage_factory(
                        klass=PrivateFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         '../smedia/filer_thumbnails/')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  '/smedia/filer_thumbnails/')
                    ))
FILER_PRIVATEMEDIA_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_SERVER', DefaultServer())
FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_THUMBNAIL_SERVER', DefaultServer())

########NEW FILE########
__FILENAME__ = storage
#-*- coding: utf-8 -*-
from django.core.files.storage import FileSystemStorage


class PublicFileSystemStorage(FileSystemStorage):
    """
    File system storage that saves its files in the filer public directory

    See ``filer.settings`` for the defaults for ``location`` and ``base_url``.
    """
    is_secure = False


class PrivateFileSystemStorage(FileSystemStorage):
    """
    File system storage that saves its files in the filer private directory.
    This directory should NOT be served directly by the web server.

    See ``filer.settings`` for the defaults for ``location`` and ``base_url``.
    """
    is_secure = True

########NEW FILE########
__FILENAME__ = filermedia
#-*- coding: utf-8 -*-
from django.template import Library

register = Library()


def filer_staticmedia_prefix():
    """
    Returns the string contained in the setting FILER_STATICMEDIA_PREFIX.
    """
    try:
        from filer import settings
    except ImportError:
        return ''
    return settings.FILER_STATICMEDIA_PREFIX
filer_staticmedia_prefix = register.simple_tag(filer_staticmedia_prefix)

########NEW FILE########
__FILENAME__ = filer_admin_tags
from django.template import Library

register = Library()


def filer_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """
    context['action_index'] = context.get('action_index', -1) + 1
    return context
filer_actions = register.inclusion_tag("admin/filer/actions.html", takes_context=True)(filer_actions)

########NEW FILE########
__FILENAME__ = filer_image_tags
#-*- coding: utf-8 -*-
from django.template import Library
import re

register = Library()

RE_SIZE = re.compile(r'(\d+)x(\d+)$')


def _recalculate_size(size, index, divisor=0, padding=0,
                      keep_aspect_ratio=False):
    new_one = size[index]
    if divisor:
        new_one = new_one / float(divisor)
    if padding:
        new_one = new_one - padding
    if keep_aspect_ratio:
        new_two = int(float(new_one) * \
                      float(size[int(not index)]) / size[index])
    else:
        new_two = int(size[int(not index)])

    new_one = int(new_one)
    if index:
        return (new_two, new_one)
    return new_one, new_two


def _resize(original_size, index, divisor=0, padding=0,
            keep_aspect_ratio=False):
    if isinstance(original_size, basestring):
        m = RE_SIZE.match(original_size)
        if m:
            original_size = (int(m.group(1)), int(m.group(2)))
        else:
            return original_size
    else:
        try:
            original_size = (int(original_size[0]), int(original_size[1]))
        except (TypeError, ValueError):
            return original_size
    try:
        padding = int(padding)
        divisor = int(divisor)
    except (TypeError, ValueError):
        return original_size
    # Re-calculate size
    new_x, new_y = _recalculate_size(original_size, index, divisor=divisor,
                                     padding=padding,
                                     keep_aspect_ratio=keep_aspect_ratio)
    return (new_x, new_y)


def extra_padding_x(original_size, padding):
    """
    Reduce the width of `original_size` by `padding`
    """
    return _resize(original_size, 0, padding=padding)
extra_padding_x = register.filter(extra_padding_x)


def extra_padding_x_keep_ratio(original_size, padding):
    """
    Reduce the width of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _resize(original_size, 0, padding=padding, keep_aspect_ratio=True)
extra_padding_x_keep_ratio = register.filter(extra_padding_x_keep_ratio)


def extra_padding_y(original_size, padding):
    """
    Reduce the height of `original_size` by `padding`
    """
    return _resize(original_size, 1, padding=padding)
extra_padding_y = register.filter(extra_padding_y)


def extra_padding_y_keep_ratio(original_size, padding):
    """
    Reduce the height of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _resize(original_size, 1, padding=padding, keep_aspect_ratio=True)
extra_padding_y_keep_ratio = register.filter(extra_padding_y_keep_ratio)


def divide_x_by(original_size, divisor):
    return _resize(original_size, 0, divisor=divisor)
devide_x_by = register.filter(divide_x_by)


def divide_y_by(original_size, divisor):
    return _resize(original_size, 1, divisor=divisor)
devide_y_by = register.filter(divide_y_by)


def divide_xy_by(original_size, divisor):
    size = divide_x_by(original_size, divisor=divisor)
    size = divide_y_by(size, divisor=divisor)
    return size
divide_xy_by = register.filter(divide_xy_by)

########NEW FILE########
__FILENAME__ = filer_tags
#-*- coding: utf-8 -*-
from django.template import Library
import math

register = Library()

# The templatetag below is copied from sorl.thumbnail

filesize_formats = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
filesize_long_formats = {
    'k': 'kilo', 'M': 'mega', 'G': 'giga', 'T': 'tera', 'P': 'peta',
    'E': 'exa', 'Z': 'zetta', 'Y': 'yotta',
}


def filesize(bytes, format='auto1024'):
    """
    Returns the number of bytes in either the nearest unit or a specific unit
    (depending on the chosen format method).

    Acceptable formats are:

    auto1024, auto1000
      convert to the nearest unit, appending the abbreviated unit name to the
      string (e.g. '2 KiB' or '2 kB').
      auto1024 is the default format.
    auto1024long, auto1000long
      convert to the nearest multiple of 1024 or 1000, appending the correctly
      pluralized unit name to the string (e.g. '2 kibibytes' or '2 kilobytes').
    kB, MB, GB, TB, PB, EB, ZB or YB
      convert to the exact unit (using multiples of 1000).
    KiB, MiB, GiB, TiB, PiB, EiB, ZiB or YiB
      convert to the exact unit (using multiples of 1024).

    The auto1024 and auto1000 formats return a string, appending the correct
    unit to the value. All other formats return the floating point value.

    If an invalid format is specified, the bytes are returned unchanged.
    """
    format_len = len(format)
    # Check for valid format
    if format_len in (2, 3):
        if format_len == 3 and format[0] == 'K':
            format = 'k%s' % format[1:]
        if not format[-1] == 'B' or format[0] not in filesize_formats:
            return bytes
        if format_len == 3 and format[1] != 'i':
            return bytes
    elif format not in ('auto1024', 'auto1000',
                        'auto1024long', 'auto1000long'):
        return bytes
    # Check for valid bytes
    try:
        bytes = long(bytes)
    except (ValueError, TypeError):
        return bytes

    # Auto multiple of 1000 or 1024
    if format.startswith('auto'):
        if format[4:8] == '1000':
            base = 1000
        else:
            base = 1024
        logarithm = bytes and math.log(bytes, base) or 0
        index = min(int(logarithm) - 1, len(filesize_formats) - 1)
        if index >= 0:
            if base == 1000:
                bytes = bytes and bytes / math.pow(1000, index + 1)
            else:
                bytes = bytes >> (10 * (index))
                bytes = bytes and bytes / 1024.0
            unit = filesize_formats[index]
        else:
            # Change the base to 1000 so the unit will just output 'B' not 'iB'
            base = 1000
            unit = ''
        if bytes >= 10 or ('%.1f' % bytes).endswith('.0'):
            bytes = '%.0f' % bytes
        else:
            bytes = '%.1f' % bytes
        if format.endswith('long'):
            unit = filesize_long_formats.get(unit, '')
            if base == 1024 and unit:
                unit = '%sbi' % unit[:2]
            unit = '%sbyte%s' % (unit, bytes != '1' and 's' or '')
        else:
            unit = '%s%s' % (base == 1024 and unit.upper() or unit,
                             base == 1024 and 'iB' or 'B')

        return '%s %s' % (bytes, unit)

    if bytes == 0:
        return bytes
    base = filesize_formats.index(format[0]) + 1
    # Exact multiple of 1000
    if format_len == 2:
        return bytes / (1000.0 ** base)
    # Exact multiple of 1024
    elif format_len == 3:
        bytes = bytes >> (10 * (base - 1))
        return bytes / 1024.0
register.filter(filesize)

########NEW FILE########
__FILENAME__ = admin
#-*- coding: utf-8 -*-
import os
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.files import File as DjangoFile
from django.contrib.admin import helpers

from filer.models.filemodels import File
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.clipboardmodels import Clipboard
from filer.models.virtualitems import FolderRoot
from filer.models import tools
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image)


class FilerFolderAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
    def tearDown(self):
        self.client.logout()
    def test_filer_app_index_get(self):
        response = self.client.get(reverse('admin:app_list', args=('filer',)))
        self.assertEqual(response.status_code, 200)

    def test_filer_make_root_folder_get(self):
        response = self.client.get(reverse('admin:filer-directory_listing-make_root_folder'))
        self.assertEqual(response.status_code, 200)

    def test_filer_make_root_folder_post(self):
        FOLDER_NAME = "root folder 1"
        self.assertEqual(Folder.objects.count(), 0)
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'),
                                    {
                                        "name":FOLDER_NAME,
                                    })
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, FOLDER_NAME)
        #TODO: not sure why the status code is 200
        self.assertEqual(response.status_code, 200)

    def test_filer_directory_listing_root_empty_get(self):
        response = self.client.post(reverse('admin:filer-directory_listing-root'))
        self.assertEqual(response.status_code, 200)

    def test_filer_directory_listing_root_get(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        response = self.client.post(reverse('admin:filer-directory_listing-root'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['folder'].children.count(), 6)


class FilerImageAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

    def tearDown(self):
        self.client.logout()


class FilerClipboardAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for img in Image.objects.all():
            img.delete()

    def test_filer_upload_file(self):
        self.assertEqual(Image.objects.count(), 0)
        file = DjangoFile(open(self.filename))
        response = self.client.post(reverse('admin:filer-ajax_upload'),
                                    {
                                       'Filename':self.image_name,
                                        'Filedata': file,
                                       'jsessionid':self.client.session.session_key,
                                    })
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename,
                         self.image_name)

class  BulkOperationsMixin(object):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')
        self.create_src_and_dst_folders()
        self.create_image(self.src_folder)

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for img in Image.objects.all():
            img.delete()
        for folder in Folder.objects.all():
            folder.delete()

    def create_src_and_dst_folders(self):
        self.src_folder = Folder(name="Src", parent=None)
        self.src_folder.save()
        self.dst_folder = Folder(name="Dst", parent=None)
        self.dst_folder.save()

    def create_image(self, folder):
        file = DjangoFile(open(self.filename), name=self.image_name)
        self.image_obj = Image.objects.create(owner=self.superuser, original_filename=self.image_name, file=file, folder=folder)
        self.image_obj.save()

class FilerBulkOperationsTests(BulkOperationsMixin, TestCase):
    def test_move_files_and_folders_action(self):
        # TODO: Test recursive (files and folders tree) move

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': self.dst_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 0)
        self.assertEqual(self.dst_folder.files.count(), 1)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.dst_folder.id,
        })
        response = self.client.post(url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': self.src_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)

    def test_move_to_clipboard_action(self):
        # TODO: Test recursive (files and folders tree) move

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'move_to_clipboard',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 0)
        self.assertEqual(self.dst_folder.files.count(), 0)
        clipboard = Clipboard.objects.get(user=self.superuser)
        self.assertEqual(clipboard.files.count(), 1)
        tools.move_files_from_clipboard_to_folder(clipboard, self.src_folder)
        tools.discard_clipboard(clipboard)
        self.assertEqual(clipboard.files.count(), 0)
        self.assertEqual(self.src_folder.files.count(), 1)

    def test_files_set_public_action(self):
        self.image_obj.is_public = False
        self.image_obj.save()
        self.assertEqual(self.image_obj.is_public, False)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'files_set_public',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.is_public, True)

    def test_files_set_private_action(self):
        self.image_obj.is_public = True
        self.image_obj.save()
        self.assertEqual(self.image_obj.is_public, True)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'files_set_private',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.is_public, False)
        self.image_obj.is_public = True
        self.image_obj.save()

    def test_copy_files_and_folders_action(self):
        # TODO: Test recursive (files and folders tree) copy

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        self.assertEqual(self.image_obj.original_filename, 'test_file.jpg')
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'suffix': 'test',
            'destination': self.dst_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 1)
        self.assertEqual(self.src_folder.files[0].id, self.image_obj.id)
        dst_image_obj = self.dst_folder.files[0]
        self.assertEqual(dst_image_obj.original_filename, 'test_filetest.jpg')

class FilerDeleteOperationTests(BulkOperationsMixin, TestCase):
    def test_delete_files_or_folders_action(self):
        self.assertNotEqual(File.objects.count(), 0)
        self.assertNotEqual(Image.objects.count(), 0)
        self.assertNotEqual(Folder.objects.count(), 0)
        url = reverse('admin:filer-directory_listing-root')
        folders = []
        for folder in FolderRoot().children.all():
            folders.append('folder-%d' % (folder.id,))
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: folders,
        })
        self.assertEqual(File.objects.count(), 0)
        self.assertEqual(Image.objects.count(), 0)
        self.assertEqual(Folder.objects.count(), 0)

class FilerResizeOperationTests(BulkOperationsMixin, TestCase):
    def test_resize_images_action(self):
        # TODO: Test recursive (files and folders tree) processing

        self.assertEqual(self.image_obj.width, 800)
        self.assertEqual(self.image_obj.height, 600)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'resize_images',
            'post': 'yes',
            'width': 42,
            'height': 42,
            'crop': True,
            'upscale': False,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.width, 42)
        self.assertEqual(self.image_obj.height, 42)

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from django.test.testcases import TestCase
from filer.fields.image import FilerImageField

class FieldsTests(TestCase):
    def test_related_name_validation(self):
        self.assertRaises(ImproperlyConfigured, FilerImageField, related_name='thumbnails')
        FilerImageField(related_name='not_thumbnails')

########NEW FILE########
__FILENAME__ = general
#-*- coding: utf-8 -*-
from django.test import TestCase
import filer


class GeneralTestCase(TestCase):
    def test_version_is_set(self):
        self.assertTrue(len(filer.get_version())>0)
########NEW FILE########
__FILENAME__ = helpers
#-*- coding: utf-8 -*-
from PIL import Image, ImageChops, ImageDraw

from django.contrib.auth.models import User
from filer.models.foldermodels import Folder
from filer.models.clipboardmodels import Clipboard, ClipboardItem

def create_superuser():
    superuser = User.objects.create_superuser('admin',
                                              'admin@free.fr',
                                              'secret')
    return superuser

def create_folder_structure(depth=2, sibling=2, parent=None):
    """
    This method creates a folder structure of the specified depth.

    * depth: is an integer (default=2)
    * sibling: is an integer (default=2)
    * parent: is the folder instance of the parent.
    """
    if depth > 0 and sibling > 0:
        depth_range = range(1, depth+1)
        depth_range.reverse()
        for d in depth_range:
            for s in range(1,sibling+1):
                name = "folder: %s -- %s" %(str(d), str(s))
                folder = Folder(name=name, parent=parent)
                folder.save()
                create_folder_structure(depth=d-1, sibling=sibling, parent=folder)

def create_clipboard_item(user, file):
    clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=user)
    clipboard_item = ClipboardItem(clipboard=clipboard, file=file)
    return clipboard_item

def create_image(mode='RGB', size=(800, 600)):
    image = Image.new(mode, size)
    draw = ImageDraw.Draw(image)
    x_bit, y_bit = size[0] // 10, size[1] // 10
    draw.rectangle((x_bit, y_bit * 2, x_bit * 7, y_bit * 3), 'red')
    draw.rectangle((x_bit * 2, y_bit, x_bit * 3, y_bit * 8), 'red')
    return image

########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
import os
from django.forms.models import modelform_factory
from django.test import TestCase
from django.core.files import File as DjangoFile

from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.clipboardmodels import Clipboard
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image, create_clipboard_item)
from filer import settings as filer_settings



class FilerApiTests(TestCase):

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for img in Image.objects.all():
            img.delete()

    def create_filer_image(self):
        file = DjangoFile(open(self.filename), name=self.image_name)
        image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=file)
        return image

    def test_create_folder_structure(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        self.assertEqual(Folder.objects.count(), 26)

    def test_create_and_delete_image(self):
        self.assertEqual(Image.objects.count(), 0)
        image = self.create_filer_image()
        image.save()
        self.assertEqual(Image.objects.count(), 1)
        image = Image.objects.all()[0]
        image.delete()
        self.assertEqual(Image.objects.count(), 0)

    def test_upload_image_form(self):
        self.assertEqual(Image.objects.count(), 0)
        file = DjangoFile(open(self.filename), name=self.image_name)
        ImageUploadForm = modelform_factory(Image, fields=('original_filename', 'owner', 'file'))
        upoad_image_form = ImageUploadForm({'original_filename':self.image_name,
                                                'owner': self.superuser.pk},
                                                {'file':file})
        if upoad_image_form.is_valid():
            image = upoad_image_form.save()
        self.assertEqual(Image.objects.count(), 1)

    def test_create_clipboard_item(self):
        image = self.create_filer_image()
        image.save()
        # Get the clipboard of the current user
        clipboard_item = create_clipboard_item(user=self.superuser,
                              file=image)
        clipboard_item.save()
        self.assertEqual(Clipboard.objects.count(), 1)

    def test_create_icons(self):
        image = self.create_filer_image()
        image.save()
        icons = image.icons
        file_basename = os.path.basename(image.file.path)
        self.assertEqual(len(icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            self.assertEqual(os.path.basename(icons[size]),
                             file_basename + u'__%sx%s_q85_crop_upscale.jpg' %(size,size))

    def test_file_upload_public_destination(self):
        """
        Test where an image `is_public` == True is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))

    def test_file_upload_private_destination(self):
        """
        Test where an image `is_public` == False is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))

    def test_file_move_location(self):
        """
        Test the method that move a file between filer_public, filer_private
        and vice et versa
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))

    def test_file_change_upload_to_destination(self):
        """
        Test that the file is actualy move from the private to the public
        directory when the is_public is checked on an existing private file.
        """
        file = DjangoFile(open(self.filename), name=self.image_name)

        image = Image.objects.create(owner=self.superuser,
                                     is_public=False,
                                     original_filename=self.image_name,
                                     file=file)
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))

########NEW FILE########
__FILENAME__ = permissions
#-*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase
from filer import settings as filer_settings
from filer.models.clipboardmodels import Clipboard
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.tests.utils import Mock
from filer.tests.helpers import create_image, create_superuser
import os

class FolderPermissionsTestCase(TestCase):

    def create_fixtures(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

        self.unauth_user = User.objects.create(username='test1')

        self.owner = User.objects.create(username='owner')

        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename), name=self.image_name)
        # This is actually a "file" for filer considerations
        self.image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=self.file)
        self.clipboard = Clipboard.objects.create(user=self.superuser)
        self.clipboard.append_file(self.image)

        self.folder = Folder.objects.create(name='test_folder')

    def test_superuser_has_rights(self):
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.superuser)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_unlogged_user_has_no_rights(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        filer_settings.FILER_ENABLE_PERMISSIONS = True
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.unauth_user)

        result = self.folder.has_read_permission(request)
        filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
        self.assertEqual(result, False)

    def test_unlogged_user_has_rights_when_permissions_disabled(self):
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.unauth_user)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_owner_user_has_rights(self):
        self.create_fixtures()
        # Set owner as the owner of the folder.
        self.folder.owner = self.owner
        request = Mock()
        setattr(request, 'user', self.owner)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

########NEW FILE########
__FILENAME__ = server_backends
#-*- coding: utf-8 -*-
import time
import shutil
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponseNotModified, Http404
from django.test import TestCase
from django.utils.http import http_date
from filer import settings as filer_settings
from filer.models import File
from filer.server.backends.default import DefaultServer
from filer.server.backends.nginx import NginxXAccelRedirectServer
from filer.server.backends.xsendfile import ApacheXSendfileServer
from filer.tests.helpers import create_image
from filer.tests.utils import Mock


class BaseServerBackendTestCase(TestCase):
    def setUp(self):
        original_filename = 'myimage.jpg'
        file_obj = SimpleUploadedFile(
            name=original_filename,
            content=create_image().tostring(),
            content_type='image/jpeg')
        self.filer_file = File.objects.create(
            file=file_obj,
            original_filename=original_filename)
    def tearDown(self):
        # delete all the files
        for location in (
                filer_settings.FILER_PUBLICMEDIA_STORAGE.location,
                filer_settings.FILER_PUBLICMEDIA_THUMBNAIL_STORAGE.location,
                filer_settings.FILER_PRIVATEMEDIA_STORAGE.location,
                filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.location):
            shutil.rmtree(location,ignore_errors=True)


class DefaultServerTestCase(BaseServerBackendTestCase):
    def test_normal(self):
        server = DefaultServer()
        request = Mock()
        request.META = {}
        response = server.serve(request, self.filer_file.file)
        self.assertTrue(response.has_header('Last-Modified'))

    def test_not_modified(self):
        server = DefaultServer()
        request = Mock()
        request.META = {'HTTP_IF_MODIFIED_SINCE': http_date(time.time())}
        response = server.serve(request, self.filer_file.file)
        self.assertTrue(isinstance(response, HttpResponseNotModified))

    def test_missing_file(self):
        server = DefaultServer()
        request = Mock()
        request.META = {}
        os.remove(self.filer_file.file.path)
        self.assertRaises(Http404, server.serve, *(request, self.filer_file.file))


class NginxServerTestCase(BaseServerBackendTestCase):
    def setUp(self):
        super(NginxServerTestCase, self).setUp()
        self.server = NginxXAccelRedirectServer(
            location='mylocation',
            nginx_location=filer_settings.FILER_PUBLICMEDIA_STORAGE.location,
        )

    def test_normal(self):
        request = Mock()
        request.META = {}
        response = self.server.serve(request, self.filer_file.file)
        headers = dict(response.items())
        self.assertTrue(response.has_header('X-Accel-Redirect'))
        self.assertTrue(headers['X-Accel-Redirect'].startswith(self.server.nginx_location))
        # make sure the file object was never opened (otherwise the whole delegating to nginx would kinda
        # be useless)
        self.assertTrue(self.filer_file.file.closed)


    def test_missing_file(self):
        """
        this backend should not even notice if the file is missing.
        """
        request = Mock()
        request.META = {}
        os.remove(self.filer_file.file.path)
        response = self.server.serve(request, self.filer_file.file)
        headers = dict(response.items())
        self.assertTrue(response.has_header('X-Accel-Redirect'))
        self.assertTrue(headers['X-Accel-Redirect'].startswith(self.server.nginx_location))
        self.assertTrue(self.filer_file.file.closed)


class XSendfileServerTestCase(BaseServerBackendTestCase):
    def setUp(self):
        super(XSendfileServerTestCase, self).setUp()
        self.server = ApacheXSendfileServer()

    def test_normal(self):
        request = Mock()
        request.META = {}
        response = self.server.serve(request, self.filer_file.file)
        headers = dict(response.items())
        self.assertTrue(response.has_header('X-Sendfile'))
        self.assertEqual(headers['X-Sendfile'], self.filer_file.file.path)
        # make sure the file object was never opened (otherwise the whole delegating to nginx would kinda
        # be useless)
        self.assertTrue(self.filer_file.file.closed)


    def test_missing_file(self):
        """
        this backend should not even notice if the file is missing.
        """
        request = Mock()
        request.META = {}
        os.remove(self.filer_file.file.path)
        response = self.server.serve(request, self.filer_file.file)
        headers = dict(response.items())
        self.assertTrue(response.has_header('X-Sendfile'))
        self.assertEqual(headers['X-Sendfile'], self.filer_file.file.path)
        # make sure the file object was never opened (otherwise the whole delegating to nginx would kinda
        # be useless)
        self.assertTrue(self.filer_file.file.closed)
########NEW FILE########
__FILENAME__ = tools
#-*- coding: utf-8 -*-
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase
from filer.models import tools
from filer.models.clipboardmodels import Clipboard
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.tests.helpers import create_superuser, create_image
import os

class ToolsTestCase(TestCase):

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for img in Image.objects.all():
            img.delete()

    def create_fixtures(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename), name=self.image_name)
        # This is actually a "file" for filer considerations
        self.image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=self.file)
        self.clipboard = Clipboard.objects.create(user=self.superuser)
        self.clipboard.append_file(self.image)

        self.folder = Folder.objects.create(name='test_folder')

    def test_clear_clipboard_works(self):
        self.create_fixtures()
        self.assertEqual(len(self.clipboard.files.all()), 1)
        tools.discard_clipboard(self.clipboard)
        self.assertEqual(len(self.clipboard.files.all()), 0)

    def test_move_to_clipboard_works(self):
        self.create_fixtures()
        self.assertEqual(len(self.clipboard.files.all()), 1)

        file2 = Image.objects.create(owner=self.superuser,
                                     original_filename='file2',
                                     file=self.file)
        file3 = Image.objects.create(owner=self.superuser,
                                     original_filename='file3',
                                     file=self.file)
        files = [file2, file3]

        tools.move_file_to_clipboard(files, self.clipboard)
        self.assertEqual(len(self.clipboard.files.all()), 3)

    def test_move_from_clipboard_to_folder_works(self):
        self.create_fixtures()
        self.assertEqual(len(self.clipboard.files.all()), 1)

        tools.move_files_from_clipboard_to_folder(self.clipboard, self.folder)
        for file in self.clipboard.files.all():
            self.assertEqual(file.folder, self.folder)

    def test_delete_clipboard_works(self):
        self.create_fixtures()
        self.assertEqual(len(self.clipboard.files.all()), 1)

        tools.delete_clipboard(self.clipboard)
        # Assert there is no file with self.image_name = 'test_file.jpg'
        result = Image.objects.filter(file=self.file)
        self.assertEqual(len(result), 0)

########NEW FILE########
__FILENAME__ = utils
#-*- coding: utf-8 -*-
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase
from filer.tests.helpers import create_image
from filer.utils.loader import load
from filer.utils.zip import unzip
from zipfile import ZipFile
import os

#===============================================================================
# Some target classes for the classloading tests
#===============================================================================
class TestTargetSuperClass(object):
    pass

class TestTargetClass(TestTargetSuperClass):
    pass

#===============================================================================
# Testing the classloader
#===============================================================================
class ClassLoaderTestCase(TestCase):
    ''' Tests filer.utils.loader.load() '''

    def test_loader_loads_strings_properly(self):
        target = 'filer.tests.utils.TestTargetClass'
        result = load(target, None) # Should return an instance
        self.assertEqual(result.__class__, TestTargetClass)

    def test_loader_loads_class(self):
        result = load(TestTargetClass(), TestTargetSuperClass)
        self.assertEqual(result.__class__, TestTargetClass)

    def test_loader_loads_subclass(self):
        result = load(TestTargetClass, TestTargetSuperClass)
        self.assertEqual(result.__class__, TestTargetClass)

#===============================================================================
# Testing the zipping/unzipping of files
#===============================================================================

class ZippingTestCase(TestCase):

    def create_fixtures(self):

        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename), name=self.image_name)

        self.zipfilename = 'test_zip.zip'

        self.zip = ZipFile(self.zipfilename, 'a')
        self.zip.write(self.filename)
        self.zip.close()

    def tearDown(self):
        # Clean up the created zip file
        os.remove(self.zipfilename)
        os.remove(self.filename)

    def test_unzipping_works(self):
        self.create_fixtures()
        result = unzip(self.zipfilename)
        self.assertEqual(result[0][0].name, self.file.name)

########NEW FILE########
__FILENAME__ = thumbnail_processors
#-*- coding: utf-8 -*-
import re
try:
    import Image
    import ImageDraw
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageDraw
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
from easy_thumbnails import processors
from filer.settings import FILER_SUBJECT_LOCATION_IMAGE_DEBUG

RE_SUBJECT_LOCATION = re.compile(r'^(\d+),(\d+)$')


def normalize_subject_location(subject_location):
    if subject_location:
        if isinstance(subject_location, basestring):
            m = RE_SUBJECT_LOCATION.match(subject_location)
            if m:
                return (int(m.group(1)), int(m.group(2)))
        else:
            try:
                return (int(subject_location[0]), int(subject_location[1]))
            except (TypeError, ValueError):
                pass
    return False


def scale_and_crop_with_subject_location(im, size, subject_location=False,
                                         crop=False, upscale=False, **kwargs):
    """
    Like ``easy_thumbnails.processors.scale_and_crop``, but will use the
    coordinates in ``subject_location`` to make sure that that part of the
    image is in the center or at least somewhere on the cropped image.
    Please not that this does *not* work correctly if the image has been
    resized by a previous processor (e.g ``autocrop``).

    ``crop`` needs to be set for this to work, but any special cropping
    parameters will be ignored.
    """
    subject_location = normalize_subject_location(subject_location)
    if not (subject_location and crop):
        # use the normal scale_and_crop
        return processors.scale_and_crop(im, size, crop=crop,
                                         upscale=upscale, **kwargs)

    # for here on we have a subject_location and cropping is on

    # --snip-- this is a copy and paste of the first few
    #          lines of ``scale_and_crop``
    source_x, source_y = [float(v) for v in im.size]
    target_x, target_y = [float(v) for v in size]

    if crop or not target_x or not target_y:
        scale = max(target_x / source_x, target_y / source_y)
    else:
        scale = min(target_x / source_x, target_y / source_y)

    # Handle one-dimensional targets.
    if not target_x:
        target_x = source_x * scale
    elif not target_y:
        target_y = source_y * scale

    if scale < 1.0 or (scale > 1.0 and upscale):
        im = im.resize((int(source_x * scale), int(source_y * scale)),
                       resample=Image.ANTIALIAS)
    # --endsnip-- begin real code

    # ===============================
    # subject location aware cropping
    # ===============================
    # res_x, res_y: the resolution of the possibly already resized image
    res_x, res_y = [float(v) for v in im.size]

    # subj_x, subj_y: the position of the subject (maybe already re-scaled)
    subj_x = res_x * float(subject_location[0]) / source_x
    subj_y = res_y * float(subject_location[1]) / source_y
    ex = (res_x - min(res_x, target_x)) / 2
    ey = (res_y - min(res_y, target_y)) / 2
    fx, fy = res_x - ex, res_y - ey

    # box_width, box_height: dimensions of the target image
    box_width, box_height = fx - ex, fy - ey

    # try putting the box in the center around the subject point
    # (this will be partially outside of the image in most cases)
    tex, tey = subj_x - (box_width / 2), subj_y - (box_height / 2)
    tfx, tfy = subj_x + (box_width / 2), subj_y + (box_height / 2)
    if tex < 0:
        # its out of the img to the left, move both to the right until tex is 0
        tfx = tfx - tex  # tex is negative!
        tex = 0
    elif tfx > res_x:
        # its out of the img to the right
        tex = tex - (tfx - res_x)
        tfx = res_x

    if tey < 0:
        # its out of the img to the top, move both to the bottom until tey is 0
        tfy = tfy - tey  # tey is negative!)
        tey = 0
    elif tfy > res_y:
        # its out of the img to the bottom
        tey = tey - (tfy - res_y)
        tfy = res_y
    if ex or ey:
        crop_box = ((int(tex), int(tey), int(tfx), int(tfy)))
        if FILER_SUBJECT_LOCATION_IMAGE_DEBUG:
            # draw elipse on focal point for Debugging
            draw = ImageDraw.Draw(im)
            esize = 10
            draw.ellipse(((subj_x - esize, subj_y - esize),
                          (subj_x + esize, subj_y + esize)), outline="#FF0000")
        im = im.crop(crop_box)
    return im

########NEW FILE########
__FILENAME__ = filer_easy_thumbnails
#-*- coding: utf-8 -*-
from easy_thumbnails.files import Thumbnailer
import os
import re
from filer import settings as filer_settings

# match the source filename using `__` as the seperator. ``opts_and_ext`` is non
# greedy so it should match the last occurence of `__`.
# in ``ThumbnailerNameMixin.get_thumbnail_name`` we ensure that there is no `__`
# in the opts part.
RE_ORIGINAL_FILENAME = re.compile(r"^(?P<source_filename>.*)__(?P<opts_and_ext>.*?)$")


def thumbnail_to_original_filename(thumbnail_name):
    m = RE_ORIGINAL_FILENAME.match(thumbnail_name)
    if m:
        return m.group(1)
    return None


class ThumbnailerNameMixin(object):
    thumbnail_basedir = ''
    thumbnail_subdir = ''
    thumbnail_prefix = ''
    thumbnail_quality = Thumbnailer.thumbnail_quality
    thumbnail_extension = Thumbnailer.thumbnail_extension
    thumbnail_transparency_extension = Thumbnailer.thumbnail_transparency_extension

    def get_thumbnail_name(self, thumbnail_options, transparent=False):
        """
        A version of ``Thumbnailer.get_thumbnail_name`` that produces a
        reproducable thumbnail name that can be converted back to the original
        filename.
        """
        path, source_filename = os.path.split(self.name)
        if transparent:
            extension = self.thumbnail_transparency_extension
        else:
            extension = self.thumbnail_extension
        extension = extension or 'jpg'

        thumbnail_options = thumbnail_options.copy()
        size = tuple(thumbnail_options.pop('size'))
        quality = thumbnail_options.pop('quality', self.thumbnail_quality)
        initial_opts = ['%sx%s' % size, 'q%s' % quality]

        opts = thumbnail_options.items()
        opts.sort()   # Sort the options so the file name is consistent.
        opts = ['%s' % (v is not True and '%s-%s' % (k, v) or k)
                for k, v in opts if v]

        all_opts = '_'.join(initial_opts + opts)

        basedir = self.thumbnail_basedir
        subdir = self.thumbnail_subdir

        #make sure our magic delimiter is not used in all_opts
        all_opts = all_opts.replace('__', '_')
        filename = u'%s__%s.%s' % (source_filename, all_opts, extension)

        return os.path.join(basedir, path, subdir, filename)


class ActionThumbnailerMixin(object):
    thumbnail_basedir = ''
    thumbnail_subdir = ''
    thumbnail_prefix = ''
    thumbnail_quality = Thumbnailer.thumbnail_quality
    thumbnail_extension = Thumbnailer.thumbnail_extension
    thumbnail_transparency_extension = Thumbnailer.thumbnail_transparency_extension

    def get_thumbnail_name(self, thumbnail_options, transparent=False):
        """
        A version of ``Thumbnailer.get_thumbnail_name`` that returns the original
        filename to resize.
        """
        path, filename = os.path.split(self.name)

        basedir = self.thumbnail_basedir
        subdir = self.thumbnail_subdir

        return os.path.join(basedir, path, subdir, filename)

    def thumbnail_exists(self, thumbnail_name):
        return False


class FilerThumbnailer(ThumbnailerNameMixin, Thumbnailer):
    pass


class FilerActionThumbnailer(ActionThumbnailerMixin, Thumbnailer):
    pass

########NEW FILE########
__FILENAME__ = files
#-*- coding: utf-8 -*-
import os
from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from django.core.files.uploadedfile import SimpleUploadedFile


class UploadException(Exception):
    pass


def handle_upload(request):
    if not request.method == "POST":
        raise UploadException("AJAX request not valid: must be POST")
    if request.is_ajax():
        # the file is stored raw in the request
        is_raw = True
        filename = request.GET.get('qqfile', False) or request.GET.get('filename', False) or ''
        upload = SimpleUploadedFile(name=filename, content=request.raw_post_data)
    else:
        if len(request.FILES) == 1:
            # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
            # ID based on a random number, so it cannot be guessed here in the code.
            # Rather than editing Ajax Upload to pass the ID in the querystring, note that
            # each upload is a separate request so FILES should only have one entry.
            # Thus, we can just grab the first (and only) value in the dict.
            is_raw = False
            upload = request.FILES.values()[0]
            filename = upload.name
        else:
            raise UploadException("AJAX request not valid: Bad Upload")
    return upload, filename, is_raw


def get_valid_filename(s):
    """
    like the regular get_valid_filename, but also slugifies away
    umlauts and stuff.
    """
    s = get_valid_filename_django(s)
    filename, ext = os.path.splitext(s)
    filename = slugify(filename)
    ext = slugify(ext)
    if ext:
        return u"%s.%s" % (filename, ext)
    else:
        return u"%s" % (filename,)

########NEW FILE########
__FILENAME__ = generate_filename
from filer.utils.files import get_valid_filename
from django.utils.encoding import force_unicode, smart_str
import datetime
import os


def by_date(instance, filename):
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    return os.path.join(datepart, get_valid_filename(filename))

########NEW FILE########
__FILENAME__ = loader
#-*- coding: utf-8 -*-
"""
This function is snatched from
https://github.com/ojii/django-load/blob/3058ab9d9d4875589638cc45e84b59e7e1d7c9c3/django_load/core.py#L49
local changes:

* added check for basestring to allow values that are already an object
  or method.

"""
from django.utils.importlib import import_module


def load_object(import_path):
    """
    Loads an object from an 'import_path', like in MIDDLEWARE_CLASSES and the
    likes.

    Import paths should be: "mypackage.mymodule.MyObject". It then imports the
    module up until the last dot and tries to get the attribute after that dot
    from the imported module.

    If the import path does not contain any dots, a TypeError is raised.

    If the module cannot be imported, an ImportError is raised.

    If the attribute does not exist in the module, a AttributeError is raised.
    """
    if not isinstance(import_path, basestring):
        return import_path
    if '.' not in import_path:
        raise TypeError(
            "'import_path' argument to 'django_load.core.load_object' " +\
            "must contain at least one dot.")
    module_name, object_name = import_path.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, object_name)


def storage_factory(klass, location, base_url):
    """
    This factory returns an instance of the storage class provided.
    args:

    * klass: must be inherit from ``django.core.files.storage.Storage``
    * location: is a string representing the PATH similar to MEDIA_ROOT
    * base_url: is a string representing the URL similar to MEDIA_URL
    """
    return klass(location=location, base_url=base_url)

########NEW FILE########
__FILENAME__ = pil_exif
#-*- coding: utf-8 -*-
try:
    import Image
    import ExifTags
except ImportError:
    try:
        from PIL import Image
        from PIL import ExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")


def get_exif(im):
    try:
        exif_raw = im._getexif() or {}
    except:
        return {}
    ret = {}
    for tag, value in exif_raw.items():
        decoded = ExifTags.TAGS.get(tag, tag)
        ret[decoded] = value
    return ret


def get_exif_for_file(file):
    im = Image.open(file, 'r')
    return get_exif(im)


def get_subject_location(exif_data):
    try:
        r = (int(exif_data['SubjectLocation'][0]), int(exif_data['SubjectLocation'][1]),)
    except:
        r = None
    return r

########NEW FILE########
__FILENAME__ = zip
#-*- coding: utf-8 -*-
#import zipfile
# zipfile.open() is only available in Python 2.6, so we use the future version
from django.core.files.uploadedfile import SimpleUploadedFile
from zipfile import ZipFile


def unzip(file):
    """
    Take a path to a zipfile and checks if it is a valid zip file
    and returns...
    """
    files = []
    # TODO: implement try-except here
    zip = ZipFile(file)
    bad_file = zip.testzip()
    if bad_file:
        raise Exception('"%s" in the .zip archive is corrupt.' % bad_file)
    infolist = zip.infolist()
    for zipinfo in infolist:
        if zipinfo.filename.startswith('__'):  # do not process meta files
            continue
        thefile = SimpleUploadedFile(name=zipinfo.filename, content=zip.read(zipinfo))
        files.append((thefile, zipinfo.filename))
    zip.close()
    return files

########NEW FILE########
__FILENAME__ = views
#-*- coding: utf-8 -*-
from django import forms
from django.contrib.admin import widgets
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from models import Folder, Image, Clipboard, tools, FolderRoot
from filer import settings as filer_settings


class NewFolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('name',)
        widgets = {
            'name': widgets.AdminTextInputWidget,
        }


def popup_status(request):
    return '_popup' in request.REQUEST or 'pop' in request.REQUEST


def selectfolder_status(request):
    return 'select_folder' in request.REQUEST


def popup_param(request):
    if popup_status(request):
        return "?_popup=1"
    else:
        return ""


def _userperms(item, request):
    r = []
    ps = ['read', 'edit', 'add_children']
    for p in ps:
        attr = "has_%s_permission" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append(p)
    return r


@login_required
def edit_folder(request, folder_id):
    # TODO: implement edit_folder view
    folder = None
    return render_to_response('admin/filer/folder/folder_edit.html', {
            'folder': folder,
            'is_popup': '_popup' in request.REQUEST or \
                        'pop' in request.REQUEST,
        }, context_instance=RequestContext(request))


@login_required
def edit_image(request, folder_id):
    # TODO: implement edit_image view
    folder = None
    return render_to_response('filer/image_edit.html', {
            'folder': folder,
            'is_popup': '_popup' in request.REQUEST or \
                        'pop' in request.REQUEST,
        }, context_instance=RequestContext(request))


@login_required
def make_folder(request, folder_id=None):
    if not folder_id:
        folder_id = request.REQUEST.get('parent_id', None)
    if folder_id:
        folder = Folder.objects.get(id=folder_id)
    else:
        folder = None

    if request.user.is_superuser:
        pass
    elif folder == None:
        # regular users may not add root folders unless configured otherwise
        if not filer_settings.FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS:
            raise PermissionDenied
    elif not folder.has_add_children_permission(request):
        # the user does not have the permission to add subfolders
        raise PermissionDenied

    if request.method == 'POST':
        new_folder_form = NewFolderForm(request.POST)
        if new_folder_form.is_valid():
            new_folder = new_folder_form.save(commit=False)
            if (folder or FolderRoot()).contains_folder(new_folder.name):
                new_folder_form._errors['name'] = new_folder_form.error_class([_('Folder with this name already exists.')])
            else:
                new_folder.parent = folder
                new_folder.owner = request.user
                new_folder.save()
                return HttpResponse('<script type="text/javascript">' + \
                                    'opener.dismissPopupAndReload(window);' + \
                                    '</script>')
    else:
        new_folder_form = NewFolderForm()
    return render_to_response('admin/filer/folder/new_folder_form.html', {
            'new_folder_form': new_folder_form,
            'is_popup': '_popup' in request.REQUEST or \
                        'pop' in request.REQUEST,
    }, context_instance=RequestContext(request))


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = Image


@login_required
def upload(request):
    return render_to_response('filer/upload.html', {
                    'title': u'Upload files',
                    'is_popup': popup_status(request),
                    }, context_instance=RequestContext(request))


@login_required
def paste_clipboard_to_folder(request):
    if request.method == 'POST':
        folder = Folder.objects.get(id=request.POST.get('folder_id'))
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        if folder.has_add_children_permission(request):
            tools.move_files_from_clipboard_to_folder(clipboard, folder)
            tools.discard_clipboard(clipboard)
        else:
            raise PermissionDenied
    return HttpResponseRedirect('%s%s' % (
                                    request.REQUEST.get('redirect_to', ''),
                                    popup_param(request)))


@login_required
def discard_clipboard(request):
    if request.method == 'POST':
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        tools.discard_clipboard(clipboard)
    return HttpResponseRedirect('%s%s' % (
                                    request.POST.get('redirect_to', ''),
                                    popup_param(request)))


@login_required
def delete_clipboard(request):
    if request.method == 'POST':
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        tools.delete_clipboard(clipboard)
    return HttpResponseRedirect('%s%s' % (
                                    request.POST.get('redirect_to', ''),
                                    popup_param(request)))


@login_required
def clone_files_from_clipboard_to_folder(request):
    if request.method == 'POST':
        clipboard = Clipboard.objects.get(id=request.POST.get('clipboard_id'))
        folder = Folder.objects.get(id=request.POST.get('folder_id'))
        tools.clone_files_from_clipboard_to_folder(clipboard, folder)
    return HttpResponseRedirect('%s%s' % (
                                    request.POST.get('redirect_to', ''),
                                    popup_param(request)))

########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends MIDDLEWARE_CLASSES
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
#!end

#!chuck_appends TEMPLATE_CONTEXT_PROCESSORS
    'cms.context_processors.media',
    'sekizai.context_processors.sekizai',
#!end

#!chuck_appends INSTALLED_APPS
    'cms',
    'menus',
    'cms.plugins.text',
    'easy_thumbnails',
    'filer',
    'cmsplugin_filer_file',
    'cmsplugin_filer_folder',
    'cmsplugin_filer_image',
    'cmsplugin_filer_video',

    'mptt',
    'sekizai',

#!end


#!chuck_appends SETTINGS
CMS_TEMPLATES = (
    ('subsite.html', ugettext('Subsite')),
)

CMS_SOFTROOT = False
CMS_MODERATOR = False
CMS_PERMISSION = False
CMS_REDIRECTS = True
CMS_SEO_FIELDS = True
CMS_FLAT_URLS = False
CMS_MENU_TITLE_OVERWRITE = False
CMS_HIDE_UNTRANSLATED = True
CMS_URL_OVERWRITE = False
CMS_SHOW_START_DATE = False
CMS_SHOW_END_DATE = False

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    #'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)
#!end


########NEW FILE########
__FILENAME__ = urls
#!chuck_extends project/urls.py

#!chuck_appends URLS
urlpatterns += patterns('',
    url(r'^', include('filer.server.urls')),
    url(r'^', include('cms.urls')),
)
#!end

########NEW FILE########
__FILENAME__ = chuck_module

priority = 2
description = """
Adds Django Compressor support to your project.
Compresses and eventually precompiles linked and inline JavaScript or CSS into cached files.

For more information, visit:
http://django_compressor.readthedocs.org/en/latest/
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
'compressor',
#!end

#!chuck_appends STATICFILES_FINDERS
'compressor.finders.CompressorFinder',
#!end

#!chuck_appends SETTINGS
COMPRESS_PRECOMPILERS = ()
#!end
########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds Django Debug Toolbar support to your project.

For more information, visit:
https://github.com/django-debug-toolbar/django-debug-toolbar/blob/master/README.rst
"""
########NEW FILE########
__FILENAME__ = dev
#!chuck_extends project/settings/dev.py

#!chuck_appends SETTINGS
INSTALLED_APPS += ('debug_toolbar',)

# Django debug toolbar
# You have to enable the debug toolbar in a custom settings file because we don't want to enable it for every developer
DEBUG_TOOLBAR_PANELS = (
     'debug_toolbar.panels.version.VersionDebugPanel',
     'debug_toolbar.panels.timer.TimerDebugPanel',
     'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
     'debug_toolbar.panels.headers.HeaderDebugPanel',
     'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
     'debug_toolbar.panels.template.TemplateDebugPanel',
#     'debug_toolbar.panels.sql.SQLDebugPanel',
     'debug_toolbar.panels.signals.SignalDebugPanel',
     'debug_toolbar.panels.logger.LoggingPanel',
)

DEBUG_TOOLBAR_CONFIG = {
     'INTERCEPT_REDIRECTS': False,
     #'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
     'HIDE_DJANGO_SQL': True,
     #'TAG': 'div',
}
#!end

########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds the Django extensions to your project.

For more informations, visit:
http://packages.python.org/django-extensions/
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
    'django_extensions',
#!end

########NEW FILE########
__FILENAME__ = chuck_module
depends = ["pil"]

description = """
Adds Django Imagekit support to your project

For more information, visit:
http://django-imagekit.readthedocs.org/en/latest/
"""

########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
    'imagekit',
#!end

########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds django-mptt support to your project.

For more information:
http://django-mptt.github.com/django-mptt/
"""

########NEW FILE########
__FILENAME__ = common
#!chuck_extends projects/settings/common.py

#!chuck_appends INSTALLED_APPS
    'mptt',
#!end

########NEW FILE########
__FILENAME__ = chuck_module

description = """
Creating delicious REST APIs with Django Tastypie

For more information, visit:
http://django-tastypie.readthedocs.org/en/latest/index.html
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
'tastypie',
#!end
########NEW FILE########
__FILENAME__ = chuck_module
depends = ['mongoengine', 'django-tastypie']
description = """
Enables you to write REST API's for MongoDB-driven applications.

For more information, visit:
http://django-tastypie-mongoengine.readthedocs.org/en/latest/index.html
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
'tastypie_mongoengine',
#!end
########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds Fabric support to your project and creates a default fabfile.

Fabric is a simple, Pythonic tool for remote execution and deployment.

For more information, visit:
http://pypi.python.org/pypi/Fabric
"""

########NEW FILE########
__FILENAME__ = chuck_module
depends = ['django-mptt', 'pil', ]
description = """
Adds FeinCMS to your project.

In the "apps" folder of your project you'll find an example configuration
with an enabled template and some pre-configured content types.

The module ships with ready-to-use TinyMCE files (example and settings), also already activated
in the example implementation.

For more information about FeinCMS, visit:
http://www.feinheit.ch/media/labs/feincms/index.html

For further explanation of the example code, visit:
http://www.feinheit.ch/media/labs/feincms/page.html#activating-the-page-module-and-creating-content-types
"""
########NEW FILE########
__FILENAME__ = models
from django.utils.translation import ugettext_lazy as _

from feincms.module.page.models import Page
from feincms.content.richtext.models import RichTextContent
from feincms.content.medialibrary.v2 import MediaFileContent

Page.register_extensions('datepublisher', 'translations', 'navigation', 'titles', 'translations')
Page.register_templates({
    'title': _('Subsite template'),
    'path': 'subsite.html',
    'regions': (
        ('main', _('Main content area')),
        ('sidebar', _('Sidebar'), 'inherited'),
        ),
    })

Page.create_content_type(RichTextContent)
Page.create_content_type(MediaFileContent, TYPE_CHOICES=(
    ('default', _('default')),
    ('lightbox', _('lightbox')),
))
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
    'mptt',
    'feincms',
    'feincms.module.page',
    'feincms.module.medialibrary',

    'example',
#!end


#!chuck_appends SETTINGS
FEINCMS_RICHTEXT_INIT_CONTEXT = {
    'TINYMCE_JS_URL': os.path.join(STATIC_URL, 'scripts/libs/tiny_mce/tiny_mce.js'),
}
#!end


########NEW FILE########
__FILENAME__ = urls
#!chuck_extends project/urls.py

#!chuck_appends URLS
urlpatterns += patterns('',
    url(r'', include('feincms.urls')),
)
#!end

########NEW FILE########
__FILENAME__ = chuck_module
description = """
Adds html5lib support to your project.

For more information, visit:
http://code.google.com/p/html5lib/
"""

########NEW FILE########
__FILENAME__ = chuck_module
depends = ["unittest"]
description = """
Plug and play integration with the Jenkins Coninuous Integration server.

For more information, visit:
http://www.jenkins-ci.org/
"""
########NEW FILE########
__FILENAME__ = dev
#!chuck_extends project/settings/dev.py

#!chuck_appends SETTINGS
INSTALLED_APPS += ('django_jenkins',)
#PROJECT_APPS = ('',)
JENKINS_TASKS = ( 'django_jenkins.tasks.run_pylint',
                 'django_jenkins.tasks.with_coverage',
                 'django_jenkins.tasks.django_tests',)
#!end

########NEW FILE########
__FILENAME__ = chuck_module
import subprocess
import os

description = """
Installs the latest jQuery version into the static folders at:
<STATIC_URL>/scripts/libs/jquery/jquery.js
<STATIC_URL>/scripts/libs/jquery/jquery.min.js

For more information, visit:
http://jquery.org/
"""

def post_build():

    jquery_dir = os.path.join(project_dir, 'static/scripts/libs/jquery')
    if not os.path.exists(jquery_dir):
        os.makedirs(jquery_dir)
    commands = [
        'cd '+jquery_dir,
        'touch jquery.js',
        'touch jquery.min.js',
        'curl http://code.jquery.com/jquery-latest.js > jquery.js',
        'curl http://code.jquery.com/jquery-latest.min.js > jquery.min.js',
        ]
    kwargs = dict(
        shell=True
    )
    process = subprocess.Popen('; '.join(commands), **kwargs)
    stdout, stderr = process.communicate()
########NEW FILE########
__FILENAME__ = chuck_module
import os
import subprocess

depends = ['django-compressor']
description = """
Module for CoffeeScript support

Installs the CoffeeScript binary into your virtualenv and adds its path to the django-compressor precompilers setting.
Requires node.js / npm in order to work.

For more information about CoffeeScript:
http://coffeescript.org/

For django-compressor usage information:
http://django_compressor.readthedocs.org
"""

def post_build():
    source = os.path.join(virtualenv_dir, 'node_modules/less/bin/lessc')
    target = os.path.join(virtualenv_dir, 'bin/lessc')
    subprocess.call(
        'cd '+virtualenv_dir+'; \
        npm install less; \
        ln -s -v '+source+' '+target+';'
        , shell=True)


def post_setup():
    post_build()
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends SETTINGS
COMPRESS_PRECOMPILERS += (
    ('text/less', 'lessc {infile} {outfile}'),
)
#!end
########NEW FILE########
__FILENAME__ = chuck_module

description = """
A Python Document-Object Mapper for working with MongoDB.

For more information, visit:
http://mongoengine.org/
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends AUTHENTICATION_BACKENDS
    # In case you want to use Mongoengine to handle auth operations
    # uncomment the following:
#   'mongoengine.django.auth.MongoEngineBackend',

#!chuck_appends SETTINGS

import mongoengine
mongoengine.connect('db_$PROJECT_NAME')

# In case you want to use Mongoengine to handle sessions
# uncomment the following:
#   SESSION_ENGINE = 'mongoengine.django.sessions'

# In case you want to use the MongoDB's GridFS feature for storage
# purposes uncomment the following 2 lines:
#   from mongoengine.django.storage import GridFSStorage
#   fs = GridFSStorage()

#!end


########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds support for the Mootools javascript library.

Please note, that as for now, there are no possibilities to build
Mootools from source. This module simply copies the javascript files to
your static folder. Current version: 1.4.5

For more information, visit:
http://mootools.net/
"""
########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds MySQL database settings to your project.

For more information, visit:
http://mysql-python.sourceforge.net/MySQLdb.html
"""
########NEW FILE########
__FILENAME__ = dev
#!chuck_extends project/settings/dev.py

#!chuck_appends DATABASES
#    'default': {
#        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#        'NAME': '$PROJECT_PREFIX_$PROJECT_NAME_devel',                      # Or path to database file if using sqlite3.
#        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_devel',                      # Not used with sqlite3.
#        'PASSWORD': 'notchdevel',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#    },
#!end

########NEW FILE########
__FILENAME__ = live
#!chuck_extends project/settings/live.py

#!chuck_appends DATABASES
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
#!end

########NEW FILE########
__FILENAME__ = stage
#!chuck_extends project/settings/stage.py

#!chuck_appends DATABASES
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '$PROJECT_PREFIX_$PROJECT_NAME_stage',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_stage',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
#!end

########NEW FILE########
__FILENAME__ = chuck_module

description = """
Generates NGiNX virtualhost config.

For more information, visit:
http://nginx.org/
"""
########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds Oracle database settings to your project.

For more information, visit:
http://cx-oracle.sourceforge.net/
"""

########NEW FILE########
__FILENAME__ = dev
#!chuck_extends project/settings/dev.py

#!chuck_appends DATABASES
#    'default': {
#        'ENGINE': 'django.db.backends.oracle', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#        'NAME': 'xe',                      # Or path to database file if using sqlite3.
#        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_devel',                      # Not used with sqlite3.
#        'PASSWORD': 'devel',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#    },
#!end

########NEW FILE########
__FILENAME__ = live
#!chuck_extends project/settings/live.py

#!chuck_appends DATABASES
    'default': {
        'ENGINE': 'django.db.backends.oracle', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'xe',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
#!end

########NEW FILE########
__FILENAME__ = stage
#!chuck_extends project/settings/stage.py

#!chuck_appends DATABASES
    'default': {
        'ENGINE': 'django.db.backends.oracle', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'xe',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_stage',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
#!end

########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds Python Image Library (PIL) support to your project.

Please note, that depending on the image file formats you intend to work with,
the PIL needs additional binaries to behave as expected.

For more information, visit:
http://www.pythonware.com/library/pil/handbook/index.html
"""
########NEW FILE########
__FILENAME__ = chuck_module

description = """
Adds PostgreSQL database settings to your project.

For more information, visit:
http://initd.org/psycopg/
"""

########NEW FILE########
__FILENAME__ = dev
#!chuck_extends project/settings/dev.py

#!chuck_appends DATABASES
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#        'NAME': '$PROJECT_PREFIX_$PROJECT_NAME_devel',                      # Or path to database file if using sqlite3.
#        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_devel',                      # Not used with sqlite3.
#        'PASSWORD': 'devel',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#    },
#!end

########NEW FILE########
__FILENAME__ = live
#!chuck_extends project/settings/live.py

#!chuck_appends DATABASES
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
#!end

########NEW FILE########
__FILENAME__ = stage
#!chuck_extends project/settings/stage.py

#!chuck_appends DATABASES
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_PREFIX_$PROJECT_NAME_live',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    },
#!end

########NEW FILE########
__FILENAME__ = chuck_module
description = """
Adds South support to your project.
Please note that this module installs an explicit version due to errors on Linux.

South is the defacto standard for database migrations in Django.

For more information, visit:
http://south.readthedocs.org/en/latest/
"""
########NEW FILE########
__FILENAME__ = common
#!chuck_extends project/settings/common.py

#!chuck_appends INSTALLED_APPS
    'south',
#!end

########NEW FILE########
__FILENAME__ = chuck_module
import subprocess
import os

depends = ['django-compressor', 'less-css']
description = """
Adds Twitter's Bootstrap CSS library to your project.

Please note, that this module installs the source files of the Bootstrap
library and therefore needs LessCSS and Django Compressor support.

For more information, visit:
http://twitter.github.com/bootstrap/
"""

def post_build():
    bootstrap_dir = os.path.join(project_dir, 'static/bootstrap')
    if not os.path.exists(bootstrap_dir):
        os.makedirs(bootstrap_dir)
    subprocess.call(
        'cd '+site_dir+'; mkdir .src; cd .src; \
        git clone https://github.com/twitter/bootstrap.git; \
        mv -v bootstrap/less '+bootstrap_dir+'; \
        mv -v bootstrap/img '+bootstrap_dir+'; \
        mv -v bootstrap/js '+bootstrap_dir+'; \
        cd ..; rm -rf .src;',
        shell=True)
########NEW FILE########
__FILENAME__ = chuck_module

description = """
Some cool unit testing tools.
"""
########NEW FILE########
__FILENAME__ = dev
#!chuck_extends project/settings/dev.py

#!chuck_appends SETTINGS
INSTALLED_APPS += ('test_utils',)
#!end

########NEW FILE########
__FILENAME__ = test
from common import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '$PROJECT_NAME_test',                      # Or path to database file if using sqlite3.
        'USER': '$PROJECT_NAME_test',                      # Not used with sqlite3.
        'PASSWORD': 'notchtest',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

INSTALLED_APPS += ('django_jenkins', 'test_utils')

PROJECT_APPS = ('',)
JENKINS_TASKS = ( 'django_jenkins.tasks.run_pylint',
                 'django_jenkins.tasks.with_coverage',
                 'django_jenkins.tasks.django_tests',)

#!chuck_renders SETTINGS
#!end

########NEW FILE########
__FILENAME__ = chuck_module


description = """
Generates a config and app file for your uWSGI deployment.

For more information, visit:
http://projects.unbit.it/uwsgi/
"""

########NEW FILE########
__FILENAME__ = django_wsgi
import os
import django.core.handlers.wsgi

os.environ['DJANGO_SETTINGS_MODULE'] = '$PROJECT_NAME.settings.sites.default.prod.live'
application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
__FILENAME__ = django_wsgi
import os
import django.core.handlers.wsgi

os.environ['DJANGO_SETTINGS_MODULE'] = '$PROJECT_NAME.settings.sites.default.prod.stage'
application = django.core.handlers.wsgi.WSGIHandler()

########NEW FILE########
