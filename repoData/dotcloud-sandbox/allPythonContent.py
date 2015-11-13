__FILENAME__ = builder
# -*- coding: utf-8 -*-

"""
builder.builder
~~~~~~~~~~~~~~~

This module implements :class:`Builder` which is the counter part of
:class:`sandbox.Application <udotcloud.sandbox.sources.Application>`.
"""

import errno
import json
import logging
import os
import shutil
import subprocess

from .services import get_service
from ..utils import ignore_eexist
from ..utils.debug import log_success

class Builder(object):
    """Build a service in Docker, from the tarball uploaded by `Sandbox`_.

    :param build_dir: path to the directory where the “application.tar” and
                      “service.tar” tarball can be found.
    """

    def __init__(self, build_dir):
        self._build_dir = build_dir
        self._code_dir = os.path.join(build_dir, "code")
        self._current_dir = os.path.join(build_dir, "current")
        self._app_tarball = os.path.join(build_dir, "application.tar")
        self._svc_tarball = os.path.join(build_dir, "service.tar")

    def _unpack_sources(self):
        logging.debug("Extracting application.tar and service.tar")
        with ignore_eexist():
            os.mkdir(self._code_dir)
        untar_app = subprocess.Popen([
            "tar", "--recursive-unlink",
            "-xf", self._app_tarball,
            "-C", self._code_dir,
        ])
        untar_svc = subprocess.Popen([
            "tar",
            "-xf", self._svc_tarball,
            "-C", self._build_dir
        ])
        untar_svc = untar_svc.wait()
        untar_app = untar_app.wait()
        if untar_svc != 0:
            logging.error(
                "Couldn't extract the environment and the supervisor "
                "configuration (tar returned {0})".format(untar_svc)
            )
        else:
            os.unlink(self._svc_tarball)
        if untar_app != 0:
            logging.error(
                "Couldn't extract the application code "
                "(tar returned {0})".format(untar_app)
            )
        else:
            os.unlink(self._app_tarball)
        if untar_app or untar_svc:
            return False

        logging.debug("Setting up SSH keys")
        ssh_dir = os.path.join(self._build_dir, ".ssh")
        try:
            os.mkdir(ssh_dir, 0700)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise
        try:
            os.unlink(os.path.join(ssh_dir, "authorized_keys2"))
        except OSError as ex:
            if ex.errno != errno.ENOENT:
                raise
        shutil.move(os.path.join(self._build_dir, "authorized_keys2"), ssh_dir)

        definition = os.path.join(self._build_dir, "definition.json")
        logging.debug("Loading service definition from {0}".format(definition))
        with open(definition, "r") as fp:
            self._svc_definition = json.load(fp)
        os.unlink(definition)

        return True

    def build(self):
        """Unpack the sources and start the build.

        The build is started using the right service class from
        :mod:`builder.services <udotcloud.builder.services>`.
        """

        if not self._unpack_sources():
            return False
        service_builder = get_service(
            self._build_dir, self._current_dir, self._svc_definition
        )
        returncode = service_builder.build()
        if returncode == 0:
            log_success("{0} build done for service {1}".format(
                self._svc_definition['type'], self._svc_definition['name']
            ))
        return returncode

########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-

import argparse
import colorama
import logging
import sys

from .builder import Builder
from ..utils.debug import configure_logging

def main():
    colorama.init()

    parser = argparse.ArgumentParser(description=
"""Internal builder for udotcloud.sandbox

This binary knows how to build a single service, of any type, from its sources
(a directory with two tarballs: application.tar —containing the application's
code— and service.tar —containing the service process definitions and
environment—).

This binary is called internally by udotcloud.sandbox and shouldn't be called
manually."""
    )
    parser.add_argument("sources", default=".",
        help="Path to the sources directory"
    )

    args = parser.parse_args()

    configure_logging("-->")

    try:
        builder = Builder(args.sources)
        sys.exit(builder.build())
    except Exception:
        logging.exception("Sorry, the following bug happened:")
    sys.exit(1)

########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-

"""
builder.services
~~~~~~~~~~~~~~~~

This module defines one class per service type. Each class knows how to build a
single type service. Use :func:`get_service` to get the right “builder” class
from a service type.
"""

import copy
import logging
import os
import shutil
import subprocess

from .templates import TemplatesRepository
from ..utils import ignore_eexist, strsignal

class ServiceBase(object):

    SUPERVISOR_PROCESS_TPL = """[program:{name}]
command=/bin/sh -lc "exec {command}"
directory={exec_dir}
stdout_logfile={supervisor_dir}/{name}.log
stderr_logfile={supervisor_dir}/{name}_error.log

"""

    def __init__(self, build_dir, svc_dir, definition):
        self._build_dir = build_dir
        self._svc_dir = svc_dir
        self._definition = definition
        self._type = definition['type']
        self._name = definition['name']
        self._processes = definition['processes']
        self._process = definition['process']
        self._config = definition.get("config", {})
        self._extra_requirements = definition.get("requirements", [])
        self._prebuild_script = definition.get("prebuild")
        self._postbuild_script = definition.get("postbuild")
        self._supervisor_dir = os.path.join(self._build_dir, "supervisor")
        self._supervisor_include = os.path.join(self._build_dir, "supervisor.conf")
        self._profile = os.path.join(self._build_dir, "dotcloud_profile")
        self._sshd_config = os.path.join(self._supervisor_dir, "sshd_config")
        self._templates = TemplatesRepository()

    def _configure(self): pass
    def _install_requirements(self): pass

    def _run_hook(self, hook_script):
        hook_cmd = "chmod +x {0} >/dev/null 2>&1; exec {0}".format(hook_script)
        subprocess.check_call([ "/bin/sh", "-lc", hook_cmd], cwd=self._svc_dir)

    def _hook_prebuild(self):
        if self._prebuild_script:
            logging.info("Running prebuild hook `{0}`".format(self._prebuild_script))
            self._run_hook(self._prebuild_script)

    def _hook_postbuild(self):
        if self._postbuild_script:
            logging.info("Running postbuild hook `{0}`".format(self._postbuild_script))
            self._run_hook(self._postbuild_script)

    def _symlink_current(self):
        approot_dir = os.path.join(
            self._build_dir, "code", self._definition['approot']
        )
        # XXX
        logging.debug("Symlinking {1} from {0}".format(approot_dir, self._svc_dir))
        with ignore_eexist():
            os.symlink(approot_dir, self._svc_dir)

    def _configure_sshd(self):
        with open(self._sshd_config, "w") as fp:
            fp.write(self._templates.render(
                "common", "sshd_config", supervisor_dir=self._supervisor_dir
            ))
        cmds = []
        for algorithm in ["rsa", "dsa", "ecdsa"]:
            keypath = os.path.join(
                self._supervisor_dir, "ssh_host_{0}_key".format(algorithm)
            )
            if not os.path.exists(keypath):
                cmds.append([
                    "ssh-keygen", "-t", algorithm, "-N", "", "-f", keypath
                ])
        logging.info("Generating SSH host keys")
        subprocesses = [subprocess.Popen(cmd) for cmd in cmds]
        for process, cmd in zip(subprocesses, cmds):
            returncode = process.wait()
            if returncode:
                raise subprocess.CalledProcessError(returncode, cmd)

    def _generate_supervisor_configuration(self):
        # The configuration itself will be in ~dotcloud but put all the other
        # supervisor related files in a subdir:
        with ignore_eexist():
            os.mkdir(self._supervisor_dir)
        supervisord_conf = self._templates.render(
            "common", "supervisor.conf", supervisor_dir=self._supervisor_dir
        )
        with open(self._supervisor_include, 'w') as fp:
            fp.write(supervisord_conf)

    def _generate_processes(self):
        with open(self._supervisor_include, "a") as fp:
            if self._processes:
                for name, command in self._processes.iteritems():
                    fp.write(self.SUPERVISOR_PROCESS_TPL.format(
                        name=name, command=command, exec_dir=self._svc_dir,
                        supervisor_dir=self._supervisor_dir
                    ))
            elif self._process:
                fp.write(self.SUPERVISOR_PROCESS_TPL.format(
                    name=self._name, command=self._process,
                    exec_dir=self._svc_dir, supervisor_dir=self._supervisor_dir
                ))

    def build(self):
        logging.debug("Building service {0} ({1}) inside Docker".format(
            self._name, self._type
        ))
        try:
            self._symlink_current()
            self._hook_prebuild()
            self._generate_supervisor_configuration()
            self._generate_processes()
            self._configure_sshd()
            self._configure()
            self._install_requirements()
            self._hook_postbuild()
        except subprocess.CalledProcessError as ex:
            cmd = " ".join(ex.cmd) if isinstance(ex.cmd, list) else ex.cmd
            msg = "Can't build service {0} ({1}): the command " \
                "`{2}` ".format(self._name, self._type, cmd)
            if ex.returncode < 0:
                signum = -ex.returncode
                logging.error(msg + "exited on signal {0} ({1})".format(
                    signum, strsignal(signum)
                ))
            elif ex.returncode == 127:
                logging.error(msg + "was not found")
            else:
                logging.error(msg + "returned {0}".format(ex.returncode))
            return ex.returncode
        return 0

class PythonWorker(ServiceBase):

    def __init__(self, *args, **kwargs):
        ServiceBase.__init__(self, *args, **kwargs)
        self._virtualenv_dir = os.path.join(self._build_dir, "env")
        self._pip = os.path.join(self._virtualenv_dir, "bin", "pip")
        self._pip_cache = os.path.join(self._build_dir, ".pip-cache")
        self._requirements = os.path.join(self._svc_dir, "requirements.txt")
        self._svc_setup_py = os.path.join(self._svc_dir, "setup.py")

    def _configure(self):
        python_version = self._config.get("python_version", "v2.6")[1:]
        logging.info("Configuring {0} ({1}) for Python {2}:".format(
            self._name, self._type, python_version
        ))
        python_version = "python" + python_version
        subprocess.check_call([
            "virtualenv", "-p", python_version, self._virtualenv_dir
        ])
        with open(self._profile, 'a') as profile:
            profile.write("\n. {0}\n".format(
                os.path.join(self._virtualenv_dir, "bin/activate")
            ))

    def _install_requirements(self):
        if os.path.exists(self._requirements):
            logging.info("Installating requirements from requirements.txt:")
            subprocess.check_call([
                self._pip, "install",
                "--download-cache={0}".format(self._pip_cache),
                "-r", self._requirements
            ])
        if self._extra_requirements:
            logging.info(
                "Installating extra requirements from dotcloud.yml: "
                "{0}".format(", ".join(self._extra_requirements))
            )
            subprocess.check_call([
                self._pip, "install",
                "--download-cache={0}".format(self._pip_cache),
                " ".join(self._extra_requirements)
            ])
        if os.path.exists(self._svc_setup_py):
            subprocess.check_call(
                [self._pip, "install", ".", "-U"],
                cwd=self._svc_dir
            )

class Python(PythonWorker):

    UWSGI_VERSION = ">=1.9.10,<1.10"

    def __init__(self, *args, **kwargs):
        PythonWorker.__init__(self, *args, **kwargs)
        self._nginx_conf = os.path.join(self._supervisor_dir, "nginx.conf")

    def _configure(self):
        PythonWorker._configure(self)
        logging.debug("Adding Nginx configuration")
        nginx_conf = self._templates.render(
            "python", "nginx.conf",
            supervisor_dir=self._supervisor_dir,
            svc_dir=self._svc_dir
        )
        with open(self._nginx_conf, "w") as fp:
            fp.write(nginx_conf)
        logging.debug("Adding Nginx and uWSGI to Supervisor")
        uwsgi_inc = self._templates.render(
            "python", "uwsgi.inc",
            supervisor_dir=self._supervisor_dir,
            virtualenv_dir=self._virtualenv_dir,
            exec_dir=self._svc_dir,
            config=self._definition['config']
        )
        nginx_inc = self._templates.render(
            "python", "nginx.inc",
            supervisor_dir=self._supervisor_dir
        )
        with open(self._supervisor_include, "a") as fp:
            fp.write(uwsgi_inc)
            fp.write(nginx_inc)
        logging.debug("Installing uWSGI {0}".format(self.UWSGI_VERSION))
        subprocess.check_call([
            self._pip, "install", "uWSGI {0}".format(self.UWSGI_VERSION)
        ])

class Custom(ServiceBase):

    SUPERVISOR_PROCESS_TPL = """[program:{name}]
command=/bin/bash -lc "[ -f ~/profile ] && . ~/profile; exec {command}"
directory={exec_dir}
stdout_logfile={supervisor_dir}/{name}.log
stderr_logfile={supervisor_dir}/{name}_error.log

"""

    def __init__(self, *args, **kwargs):
        ServiceBase.__init__(self, *args, **kwargs)
        self._svc_dir = self._build_dir
        self._supervisor_dir = "/home/dotcloud/supervisor"
        self._sshd_config = os.path.join(self._supervisor_dir, "sshd_config")
        self._profile = os.path.join("/home/dotcloud/dotcloud_profile")
        self._buildscript = None
        if "buildscript" in self._definition:
            self._buildscript = os.path.join(
                self._build_dir, "code", self._definition['buildscript']
            )

    def _symlink_current(self): pass

    def _generate_processes(self):
        if self._processes or self._process:
            ServiceBase._generate_processes(self)
            return
        with open(self._supervisor_include, "a") as fp:
            fp.write(self.SUPERVISOR_PROCESS_TPL.format(
                name=self._name, command="~/run",
                exec_dir="/home/dotcloud", supervisor_dir=self._supervisor_dir
            ))

    def _configure(self):
        if not self._buildscript:
            return
        extra_env = copy.copy(os.environ)
        for k, v in self._definition.iteritems():
            k = k.upper()
            if isinstance(v, dict):
                for sk, sv in v.items():
                    extra_env['_'.join(('SERVICE', k, sk.upper()))] = str(sv)
            else:
                extra_env['SERVICE_' + k] = str(v)
        logging.info("Calling buildscript {0} for service {1} ({2})".format(
            self._definition['buildscript'], self._name, self._type
        ))
        subprocess.check_call(
            ["/bin/sh", "-lc", "exec {0}".format(self._buildscript)],
            cwd=os.path.join(self._build_dir, "code"), env=extra_env,
        )
        shutil.move(
            os.path.join(self._build_dir, "dotcloud_profile"), self._profile
        )

def get_service_class(svc_type):
    """Return the right “builder” class for the given service type or None."""

    return {
        "custom": Custom,
        "python": Python,
        "python-worker": PythonWorker
    }.get(svc_type)

def get_service(build_dir, svc_dir, svc_definition):
    """Return the right “builder” object for the given service.

    :param build_dir: directory where the source code has been untared.
    :param svc_dir: directory where the code for the current service is
                    (usually ~/current which points to build_dir + approot).
    :param svc_definition: the definition of the current service (the
                           dictionnary for the current service from
                           dotcloud.yml).
    :raises: ValueError, if no builder exists for this type of service.
    """

    service_class = get_service_class(svc_definition['type'])
    if not service_class:
        raise ValueError("No builder defined for {0} services".format(
            svc_definition['type']
        ))
    return service_class(build_dir, svc_dir, svc_definition)

########NEW FILE########
__FILENAME__ = templates
# -*- coding: utf-8 -*-

import jinja2
import os

class TemplatesRepository(object):

    def __init__(self):
        self._jinja_env = jinja2.Environment(
            loader=jinja2.PackageLoader(__package__, "templates"),
            auto_reload=False
        )

    def render(self, service, name, **kwargs):
        tpl = self._jinja_env.get_template(os.path.join(service, name))
        return tpl.render(**kwargs)

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-

__version__ = "0.0.1"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Sandbox documentation build configuration file, created by
# sphinx-quickstart on Wed May  8 12:01:27 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

#import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Sandbox'
copyright = u'2013, dotCloud Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.1'
# The full version, including alpha/beta/rc tags.
release = '0.0.1'

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

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
htmlhelp_basename = 'Sandboxdoc'


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
  ('index', 'Sandbox.tex', u'Sandbox Documentation',
   u'dotCloud Inc.', 'manual'),
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
    ('index', 'sandbox', u'Sandbox Documentation',
     [u'dotCloud Inc.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Sandbox', u'Sandbox Documentation',
   u'dotCloud Inc.', 'Sandbox', 'One line description of project.',
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
__FILENAME__ = settings
# Django settings for example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = '/home/dotcloud/data/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = '/home/dotcloud/volatile/static/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'gnv_&fljbxpi$54_ztcta$i+h&dw5q$izdt*#m7j^%m^7e9q9n'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import example.views

urlpatterns = patterns('',
    url(r'^$', example.views.HomeView.as_view()),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
import os

from django.http import HttpResponse
from django.views.generic import View

class HomeView(View):
    
    def get(self, request, *args, **kwargs):
        return HttpResponse("</br>\n".join([
            "{0}={1}".format(k, v) for k, v in os.environ.iteritems()
        ]))

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = wsgi
example/wsgi.py
########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os

from flask import Flask, make_response

logging.basicConfig(level="DEBUG")

app = Flask(__name__)
app.debug = False

@app.before_first_request
def configure_logging():
    if not app.debug:
        stderr_logger = logging.StreamHandler()
        stderr_logger.setLevel(logging.DEBUG)
        app.logger.addHandler(stderr_logger)
        app.logger.setLevel(logging.DEBUG)

@app.route("/", methods=["GET"])
def hello():
    return make_response("</br>\n".join([
        "{0}={1}".format(k, v) for k, v in os.environ.iteritems()
    ]))

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-

import json
import logging
import os
import redis
import sys
import zerorpc

class API(object):

    def __init__(self, redis_url):
        self._redis = redis.StrictRedis.from_url(redis_url, db=0)

    def enqueue(self, value):
        """Enqueue the given value in Redis.

        The value has to be serializable in JSON.
        """

        self._redis.lpush("queue", json.dumps(value))
        return "ok"

    def dequeue(self):
        """Dequeue a value and return it."""

        return self._redis.rpop("queue")

if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    if "DOTCLOUD_DB_REDIS_URL" not in os.environ:
        logging.error("You need to set `DOTCLOUD_DB_REDIS_URL` in the environment")
        sys.exit(1)
    server = zerorpc.Server(API(os.environ['DOTCLOUD_DB_REDIS_URL']))
    logging.info("Binding zeroservice on {0}".format(os.environ['PORT_ZEROSERVICE']))
    server.bind("tcp://0.0.0.0:{0}".format(os.environ['PORT_ZEROSERVICE']))
    server.run()

########NEW FILE########
__FILENAME__ = wsgi
# -*- coding: utf-8

import logging
import os
import redis
import sys

from flask import Flask, make_response

logging.basicConfig(level="DEBUG")

if "DOTCLOUD_DB_REDIS_URL" not in os.environ:
    logging.error("You need to set `DOTCLOUD_DB_REDIS_URL` in the environment")
    sys.exit(1)

app = Flask(__name__)
app.debug = False

redis = redis.StrictRedis.from_url(os.environ['DOTCLOUD_DB_REDIS_URL'])

@app.before_first_request
def configure_logging():
    if not app.debug:
        stderr_logger = logging.StreamHandler()
        stderr_logger.setLevel(logging.DEBUG)
        app.logger.addHandler(stderr_logger)
        app.logger.setLevel(logging.DEBUG)

@app.route("/", methods=["GET"])
def check_queue():
    return make_response("</br>\n".join([
        value for value in redis.lrange("queue", 0, -1)
    ]))

application = app

########NEW FILE########
__FILENAME__ = buildfile
# -*- coding: utf-8 -*-
# Started by François-Xavier Bourlet <fx@dotcloud.com>, Oct 2011.

import copy
import re
import yaml

from StringIO import StringIO
from yaml.nodes import ScalarNode, SequenceNode, MappingNode
from yaml.constructor import SafeConstructor


class SchemaError(Exception):
    pass


class _node_validator(object):

    def __init__(self, _type, subnode=None, optional=False, default=None,
            allowed=None, checks=None):
        self._type = _type
        self._optional = optional
        self._subnode = subnode
        self._default = default
        self._allowed = allowed
        self._checks = checks if checks is not None else []

    @property
    def optional(self):
        return self._optional

    @property
    def subnode(self):
        return self._subnode

    @property
    def default(self):
        return self._default

    @property
    def allowed(self):
        return self._allowed

    @allowed.setter
    def allowed(self, value):
        self._allowed = value

    @property
    def checks(self):
        return self._checks

    def python_type(self, ast_node):
        if type(ast_node) is ScalarNode:
            return type(SafeConstructor().construct_object(ast_node))
        if type(ast_node) is SequenceNode:
            return list
        if type(ast_node) is MappingNode:
            return dict
        raise RuntimeError('Unable to map ast_node type ({0})'.format(type(ast_node)))

    def pretty_type(self, _type):
        if _type is unicode or _type is str:
            return 'string'
        if _type is dict:
            return 'dictionary'
        return _type.__name__

    def raise_error(self, err_msg, ast_node):
        mark = ast_node.start_mark
        msg = "%s in \"%s\", line %d, column %d"   \
            % (err_msg, mark.name, mark.line+1, mark.column+1)
        snippet = mark.get_snippet()
        if snippet is not None:
            msg += ":\n"+snippet
        raise SchemaError(msg)

    def validate(self, ast_node, parent_key=None):
        ast_node_type = self.python_type(ast_node)
        if self._type is str:
            wrong_type = type(ast_node) is not ScalarNode
            ast_node.tag = 'tag:yaml.org,2002:str'  # enforce string type.
        else:
            wrong_type = ast_node_type is not self._type
        if wrong_type:
            if (self.python_type(ast_node) is type(None)):
                msg = 'Expected a type {0} but got nothing'.format(
                        self.pretty_type(self._type))
            else:
                msg = 'Expected a type {0} but got {1} type {2}'.format(
                        self.pretty_type(self._type),
                        'a' if bool(ast_node.value) else 'an empty',
                        self.pretty_type(self.python_type(ast_node)))
            self.raise_error(msg, ast_node)

        if len(self._checks) > 0:
            if ast_node_type is dict:
                value = parent_key
            else:
                value = SafeConstructor().construct_object(ast_node)
            for desc, check in self._checks:
                if not check(value):
                    self.raise_error('Invalid {0} "{1}"'.format(desc,
                        value), ast_node)

        if self._allowed is not None:
            value = SafeConstructor().construct_object(ast_node)
            (desc, allowed_set) = self._allowed
            if value not in allowed_set:
                self.raise_error('Unrecognized {0} "{1}"'.format(desc,
                    value), ast_node)

        if self._subnode is None:
            return

        if self.python_type(ast_node) is dict:
            required_nodes = set(k for k, v in self._subnode.items() if not
                    v.optional)
            for subnode_key, ast_subnode in ast_node.value:
                subnode_key = subnode_key.value
                if '*' in self._subnode:
                    self._subnode['*'].validate(ast_subnode,
                            parent_key=subnode_key)
                    if '*' in required_nodes:
                        required_nodes.remove('*')
                elif subnode_key in self._subnode:  # ignore everything else
                    self._subnode[subnode_key].validate(ast_subnode,
                            parent_key=subnode_key)
                    if subnode_key in required_nodes:
                        required_nodes.remove(subnode_key)
            if len(required_nodes):
                if '*' in required_nodes:
                    msg = '{0} cannot be empty'.format(parent_key)
                else:
                    msg = 'Missing mandatory {0}: "{1}"'.format(
                            'entry' if len(required_nodes) == 1 else 'entries',
                            ', '.join(required_nodes)
                            )
                self.raise_error(msg, ast_node)


def _require(_type, subnode=None, allowed=None, checks=None):
    return _node_validator(_type, subnode, optional=False,
            allowed=allowed, checks=checks)


def _optional(_type, subnode=None, default=None, allowed=None, checks=None):
    return _node_validator(_type, subnode, optional=True, default=default,
            allowed=allowed, checks=checks)


_schema = _require(
    dict,
    {
        '*': _require(
            dict,
            {
                'type': _require(str),
                'approot': _optional(str, default='.'),
                'requirements': _optional(list, default=[]),
                'systempackages': _optional(list, default=[]),
                'environment': _optional(dict, default={}),
                'postinstall': _optional(str, default=''),
                'config': _optional(dict, default={}),
                'instances': _optional(int, default=1),
                'process': _optional(str, default=''),
                'processes': _optional(dict, default={}),
                'ports': _optional(dict, {
                    '*': _optional(str, allowed=('port', set(('http', 'tcp', 'udp'))))
                }, default={}),
                'buildscript': _optional(str),
                'prebuild': _optional(str),
                'postbuild': _optional(str),
                'ruby_version': _optional(str),
            },
            checks=[
                ('service name (must be <= 16 characters)', lambda n: len(n) <= 16),
                ('characters (lowercase alphanum only) for service', lambda n: re.match('^[a-z0-9_]+$', n)),
            ]
        )
    }
)


def validate_ast_schema(ast, valid_services):
    if ast is None:
        raise ValueError('Empty ast!')
    schema = copy.deepcopy(_schema)
    schema.subnode['*'].subnode['type'].allowed = ('service', set(valid_services))
    schema.validate(ast, 'service(s) dict')


VALID_SERVICES = {
    'redis': 'advanced key-value store',
    'python': 'host any Python/WSGI web app: Django, Pylons, Web2py...',
    'ruby': 'host any Ruby/Rack web app: Rails, Sinatra...',
    'perl': 'host any Perl/PSGI web app: Plack, Mojolicious, Dancer...',
    'perl-worker': 'run backgound Perl processes',
    'php': 'host any PHP web app: Drupal, WordPress...',
    'postgis': 'PostgreSQL with the PostGIS extensions',
    'postgresql': 'the world\'s most advanced open source database',
    'mysql': 'the world\'s most popular open source database',
    'mysql-masterslave': 'MySQL Master/Slave replicated deployment',
    'static': 'host static HTTP content',
    'rabbitmq': 'AMQP message queue server',
    'java': 'host any Java servlet (also Clojure, Play!, and much more)',
    'php-worker': 'run background PHP processes',
    'python-worker': 'run background Python processes',
    'smtp': 'authenticated SMTP relay to send e-mails reliably',
    'ruby-worker': 'run background Ruby processes',
    'nodejs': 'run JavaScript processes (including web apps)',
    'mongodb': 'scalable, high-performance, document-oriented database',
    'solr': 'the search server based on the Lucene Java search library',
    'opa': 'the unified language for web 2.0 development',
    'custom': 'custom'
}


def load_build_file(build_file_content, valid_services=VALID_SERVICES):
    """ Load and parse the build description contained in the build file """
    stream = StringIO(build_file_content)
    stream.name = 'dotcloud.yml'  # yaml load will use this property
    # to generate proper error marks.

    yaml_loader = yaml.SafeLoader(stream)

    # Check yaml syntax and load ast
    ast = yaml_loader.get_single_node()

    if ast is None:
        raise ValueError('"dotcloud.yml" is empty!')

    # Validate ast against dotcloud.yml schema.
    validate_ast_schema(ast, valid_services)

    # Now construct python object...
    desc = yaml_loader.construct_document(ast)

    # Force service name to be of type str
    desc = dict((str(k), v) for k, v in desc.iteritems())

    # for each services description
    for service_name, service_desc in desc.iteritems():
        # Check for conflicting options
        if service_desc.get('process') and service_desc.get('processes'):
            raise ValueError(
                'You can\'t have both "process" and "processes" at '
                'the same time in service "{0}"'.format(service_name)
            )

        # Inject defaults values if necessary
        for def_name, def_node in _schema.subnode['*'].subnode.items():
            if def_node.default is None:
                continue
            if def_name not in service_desc:
                service_desc[def_name] = def_node.default

    return desc

########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-

import argparse
import colorama
import errno
import logging
import re
import string
import sys

from .containers import ImageRevSpec, Image
from .exceptions import UnkownImageError
from .sources import Application
from ..utils.debug import configure_logging, log_success

def parse_environment_variables(env_list):
    env_dict = {}
    for var in env_list:
        try:
            key, value = var.split("=")
        except ValueError:
            logging.error(
                "Environment variables should be in the "
                "form KEY=VALUE (got {0})".format(var)
            )
            sys.exit(1)
        if not re.match(r"^[a-zA-Z]\w+", key):
            logging.error("Invalid environment variable name: {0}".format(key))
            sys.exit(1)
        env_dict[key] = value
    return env_dict

def cmd_build(args, application):
    try:
        base_image = Image(ImageRevSpec.parse(args.image)) if args.image else None
    except ValueError as ex:
        logging.error("Can't parse your image revision/name: {0}".format(ex))
        sys.exit(1)
    except UnkownImageError:
        logging.error(
            "The image {0} doesn't exist "
            "(maybe you need to pull it in Docker?)".format(args.image)
        )
        sys.exit(1)

    logging.debug("Starting build with base image: {0}".format(
        base_image.revspec if base_image else "default"
    ))
    result_images = application.build(base_image)
    if result_images:
        log_success("{0} successfully built:\n    - {1}".format(
            application.name,
            "\n    - ".join([
                "{0}: {1}".format(service, image)
                for service, image in result_images.iteritems()
            ])
        ))
        sys.exit(0)
    elif result_images is not None:
        logging.warning("No buildable service found in {0}".format(
            application.name
        ))

def cmd_run(args, application):
    sys.exit(0 if application.run() else 1)

def main():
    colorama.init()

    parser = argparse.ArgumentParser(
        description="""Build and run dotCloud applications locally using Docker.

Since Docker doesn't have orchestration features only stateless services will
be recognized (i.e: database won't be started, and their infos won't be
generated in the environment).
"""
    )
    parser.add_argument("-v", "--verbosity", dest="log_lvl", default="info",
        type=string.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level to use on stderr"
    )

    subparsers = parser.add_subparsers(dest="cmd")

    parser_build = subparsers.add_parser("build",
        help="build Docker images from the given dotCloud application (directory)"
    )
    parser_build.add_argument("-e", "--env", action="append",
        help="Define an environment variable (in the form KEY=VALUE) during the build"
    )
    parser_build.add_argument("-i", "--image",
        help="Specify which Docker image to use as a starting point to build services"
    )
    parser_build.add_argument("application",
        help="Path to your application source directory (where your dotcloud.yml is)",
        default=".", nargs="?"
    )

    parser_run = subparsers.add_parser("run",
        help="run the given dotCloud application, using images previously built "
            "with the build command (EXPERIMENTAL)"
    )
    parser_run.add_argument("application",
        help="Path to your application source directory (where your dotcloud.yml is)",
        default=".", nargs="?"
    )

    args = parser.parse_args()
    configure_logging("==>", args.log_lvl)

    if getattr(args, "env", None):
        env = parse_environment_variables(args.env)
    else:
        env = {}

    try:
        logging.debug("Loading {0}".format(args.application))
        try:
            application = Application(args.application, env)
        except IOError as ex:
            if ex.errno == errno.ENOENT:
                logging.error("Couldn't find a dotcloud.yml in {0}".format(
                    args.application
                ))
            else:
                logging.error("Couldn't load {0}: {1}".format(
                    args.application, ex.strerror
                ))
            sys.exit(1)
        logging.debug("Application's buildfile: {0}".format(application))
        logging.debug("Application's environment: {0}".format(
            application.environment
        ))
        logging.info("{0} successfully loaded with {1} service(s): {2}".format(
            application.name,
            len(application.services),
            ", ".join([
                "{0} ({1})".format(s.name, s.type) for s in application.services
            ])
        ))

        if args.cmd == "build":
            cmd_build(args, application)
        elif args.cmd == "run":
            cmd_run(args, application)
    except Exception:
        logging.exception("Sorry, the following bug happened:")
    sys.exit(1)

########NEW FILE########
__FILENAME__ = containers
# -*- coding: utf-8 -*-

"""
sandbox.containers
~~~~~~~~~~~~~~~~~~

This module implements a Python binding for Docker.

Docker functionnalities are exposed through three different classes:

- :class:`ImageRevSpec`: used to instantiate images;
- :class:`Image`: used to instantiate containers;
- :class:`Container`: used to run and commit new images.
"""

import collections
import contextlib
import copy
import gevent
import gevent.event
import gevent.subprocess
import itertools
import json
import logging
import re

from .exceptions import UnkownImageError, DockerCommandError, DockerNotFoundError
from ..utils import bytes_to_human

class _CatchDockerError(object):
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is gevent.subprocess.CalledProcessError:
            if exc_value.returncode == 127:
                raise DockerNotFoundError()
            raise DockerCommandError(exc_value.output)
        return False

class Container(object):
    """Containers are transitions between two images.
    
    :param revpsec: the :class:`ImageRevSpec` of the image to use.
    :param commit_as: when :meth:`Container.run` is called, commit the resulting image
                      as this given :class:`ImageRevSpec` (otherwise the
                      revspec of the image used to launch the container is
                      re-used).

    .. note:: :attr:`logs` and :attr:`result` are only available once
              :meth:`run` has successfully finished.
    """

    PIPE = gevent.subprocess.PIPE
    STDOUT = gevent.subprocess.STDOUT

    def __init__(self, image, commit_as=None):
        #: The image that will be used to start the container.
        self.image = image
        #: The revspec of the image commited when run finishes.
        self.result = None
        #: The logs from the container when run finishes.
        self.logs = None
        self.commit_as = commit_as
        self._id = None
        #: The return code of the process that was executed in the container.
        self.exit_status = None

    @staticmethod
    def _generate_option_list(option, args):
        """_generate_option_list("-p", [1, 2…]) → ["-p", 1, "-p", 2…]"""
        return list(
            itertools.chain.from_iterable(itertools.product([option], args))
        )

    @classmethod
    def _generate_env_option_list(cls, env):
        return cls._generate_option_list(
            "-e", ["{0}={1}".format(k, v) for k, v in env.iteritems()]
        )

    def _get_container_infos(self, async=False):
        def _inspect_container():
            logging.debug("Inspecting container {0}".format(self._id))
            with _CatchDockerError():
                infos = json.loads(gevent.subprocess.check_output([
                    "docker", "inspect", self._id
                ]).strip())
                # In docker 0.4.1 docker inspect will return a list:
                if isinstance(infos, list):
                    return infos[0]
                return infos
        if async:
            async_result = gevent.event.AsyncResult()
            gevent.spawn(_inspect_container).link(async_result)
            return async_result
        return _inspect_container()

    def install_system_packages(self, packages):
        cmd = "DEBIAN_FRONTEND=noninteractive; " \
            "apt-get update; apt-get -y install {0}; " \
            "apt-get clean; rm -rf /var/lib/apt/lists/*".format(
                " ".join(packages)
            )
        with self.run(["/bin/sh", "-c", cmd]):
            pass

    # XXX: Maybe this should be named to something else to better reflect the
    # fact that it's really an authoring tool, and reduce the confusion with
    # run_stream_logs.
    @contextlib.contextmanager
    def run(self, cmd, as_user=None, env={}, stdin=None, stdout=None, stderr=None):
        """Run the specified command in a new container.

        This is a context manager that returns a :class:`subprocess.Popen`
        instance. When the context manager exit a new image is commited from
        the container and the container is automatically destroyed.

        The new image can be accessed via the :attr:`result` attribute.

        :param cmd: the program to run as a list of arguments.
        :param as_user: run the command under this username or uid.
        :param stdout, stderr: as in :class:`subprocess.Popen` except that you
                               should use Container.PIPE and Container.STDOUT
                               instead of subprocess.PIPE and subprocess.STDOUT.
        :param stdin: either None (close stdin) or Container.PIPE.
        :return: Nothing (this is a context manager) but sets :attr:`result`
                 with the class:`ImageRevSpec` of the resulting image.

        .. warning::

           stdout and stderr currently don't work due to limitations on Docker:
           you can't get the id of container, in a race-condition free way,
           with stdout and stderr enabled on docker run. A workaround would be
           to start a shell in detached mode and then execute the command from
           docker attach, but docker attach doesn't exit correctly when the
           process exits (it hangs on stdin until you try to write something
           which trigger an EBADF in docker).
        """

        logging.debug("Starting {0} in a {1} container as user {2}".format(
            cmd, self.image, as_user or "root"
        ))

        as_user = ["-u", as_user] if as_user else []
        env = self._generate_env_option_list(env)

        try:
            # If stdin is None, start the container in detached mode, this will
            # print the id on stdout, then we simply wait for the container to
            # stop. If stdin is not None, start the container in attached mode
            # without stdout and stderr. This will print the container id on
            # stdout so we can read it.
            if stdin is None:
                with _CatchDockerError():
                    self._id = gevent.subprocess.check_output(
                        ["docker", "run", "-t", "-d"] + as_user
                        + env + [self.image.revision] + cmd
                    ).strip()
                # docker wait prints the number of second we waited, ignore it:
                with open("/dev/null", "w") as ignore:
                    docker = gevent.subprocess.Popen(
                        ["docker", "wait", self._id], stdout=ignore
                    )
            else:
                docker = gevent.subprocess.Popen(
                    ["docker", "run", "-i", "-a", "stdin"]
                    + as_user + env + [self.image.revision] + cmd,
                    stdin=stdin, stdout=self.PIPE
                )
                # readline instead of read is important here, the object behind
                # docker.stdout is actually a socket._fileobject (yes, the real
                # socket module from Python) and its read method returns when
                # its buffer (8192 bytes by default on Python 2.7) is full or
                # when EOF is reached, not when the underlying read system call
                # returns.
                self._id = docker.stdout.readline().strip()
            logging.debug("Started container {0} from {1}".format(
                self._id, self.image
            ))

            yield docker

            # Wait for the process to terminate (if the calling code didn't
            # already do it):
            logging.debug("Waiting for container {0} to terminate".format(
                self._id
            ))
            docker.wait()
            logging.debug("Container {0} stopped".format(self._id))

            # Since we can't get stdout/stderr in realtime for now (see the
            # docstring), let's get the logs instead.
            logs = gevent.subprocess.Popen(
                ["docker", "logs", self._id],
                stdout=self.PIPE,
                stderr=self.STDOUT
            )
            logs = gevent.spawn(logs.communicate)

            container_infos = self._get_container_infos(async=True)

            # Commit a new image from the container
            username = repository = tag = None
            commit = ["docker", "commit", self._id]
            if self.commit_as:
                username = self.commit_as.username
                repository = self.commit_as.repository
                tag = self.commit_as.tag
                if self.commit_as.fqrn:
                    commit.append(self.commit_as.fqrn)
                if tag:
                    commit.append(tag)
            elif self.image.fqrn:
                username = self.image.username
                repository = self.image.repository
                tag = self.image.tag
                commit.append(self.image.fqrn)
                if repository and tag == "latest":
                    commit.append("latest")
            with _CatchDockerError():
                revision = gevent.subprocess.check_output(
                    commit, stderr=self.STDOUT
                ).strip()
            self.result = Image(ImageRevSpec(username, repository, revision, tag))
            logging.debug("Container {0} started from {1} commited as image {2}".format(
                self._id, self.image, self.result
            ))

            logging.debug("Fetching logs from container {0}".format(self._id))
            logs.join()
            with _CatchDockerError():
                # if we raise here, self.logs will stay at None which is wanted
                self.logs = logs.get()[0]
            logging.debug("{0} of logs fetched from container {1}".format(
                bytes_to_human(len(self.logs)), self._id
            ))

            container_infos = container_infos.get()
            self.exit_status = container_infos['State']['ExitCode']
            logging.debug("Container {0} returned {1}".format(
                self._id, self.exit_status
            ))
        finally:
            if self._id:
                # Destroy the container
                logging.debug("Destroying container {0}".format(self._id))
                with _CatchDockerError():
                    gevent.subprocess.check_call(["docker", "rm", self._id])
                logging.debug("Container {0} destroyed".format(self._id))
                self._id = None

    @contextlib.contextmanager
    def run_stream_logs(self, cmd, as_user=None, ports=[], env={}, output=None):
        """Run the specified command and wait for it, logs are streamed.

        This is a context manager that yields a :class:`subprocess.Popen`
        instance. When the context manager exits, it automatically waits for
        the docker command to terminate (if you didn't do it already). The
        object yielded will expose a `ports` attribute which is a dict with the
        ports you defined as keys and the ports they got mapped to, on the host
        public address, as values.

        .. note:: stdout and stderr will be mixed in the logs output, this is
                  currently a limitation of Docker.

        :param cmd: the program to run as a list of arguments.
        :param as_user: run the command under this username or uid.
        :param ports: list of ports in the container to expose on the host.
        :param env: define additional environment variables.
        :param output: stream the logs to this file object or fd (by default
                       they are streamed to stdout), it can also be
                       Container.PIPE.

        .. warning:: due to limitations in Docker (see :meth:`run`), the
                     first lines of output might be lost.
        """

        logging.debug("Starting {0} in a {1} container as user {2}".format(
            cmd, self.image, as_user or "root"
        ))

        as_user = ["-u", as_user] if as_user else []
        ports = self._generate_option_list("-p", [str(p) for p in ports])
        env = self._generate_env_option_list(env)
        try:
            with _CatchDockerError():
                self._id = gevent.subprocess.check_output(
                    ["docker", "run", "-d"] + as_user + env
                    + ports + [self.image.revision] + cmd
                ).strip()
                docker = gevent.subprocess.Popen(
                    ["docker", "attach", self._id],
                    stdout=output, stderr=self.STDOUT
                )
                container_infos = self._get_container_infos()
                port_mapping = container_infos['NetworkSettings']['PortMapping']
                docker.ports = {
                    int(k): int(v) for k, v in port_mapping.iteritems()
                }

            yield docker

            logging.debug("Waiting for container {0} to terminate".format(
                self._id
            ))
            docker.wait()
            logging.debug("Container {0} stopped".format(self._id))
            container_infos = self._get_container_infos()
            self.exit_status = container_infos['State']['ExitCode']
            logging.debug("Container {0} returned {1}".format(
                self._id, self.exit_status
            ))
        finally:
            self._id = None

    def stop(self, wait=10):
        """If the container is running, interrupt it.

        This will send a SIGTERM to the process running inside the container.
        If this process doesn't exit after *wait* seconds then it is killed.
        """

        if self._id:
            with open("/dev/null", "w") as ignore, _CatchDockerError():
                # NOTE: not a big deal if we try to stop a container that's
                # already stopped or doesn't exist anymore, moreover don't set
                # self._id to None after that, run or run_stream_logs need it.
                gevent.subprocess.check_call(
                    ["docker", "stop", "-t", str(wait), self._id],
                    stdout=ignore, stderr=self.STDOUT
                )


_ImageRevSpec = collections.namedtuple(
    "_ImageRevSpec", ["username", "repository", "revision", "tag"]
)
class ImageRevSpec(_ImageRevSpec):
    """Human representation of an image revision in Docker.

    .. attribute:: username

       The username for this revspec or None.

    .. attribute:: repository

       The repository for this revspec or None.

    .. attribute:: revision

       The revision for this revspec or None.

    .. attribute:: tag

       The tag for this revspec or None.

    .. attribute:: fqrn

       The string username/repository if both are set, repository if the
       username is missing, or None if everything is missing (fqrn stands for
       “Fully Qualified Repository Name”).
    """

    def __str__(self):
        s = ""
        if self.username:
            s += "{0}/".format(self.username)
        if self.repository:
            s += self.repository
        if self.tag:
            s += ":{0}".format(self.tag)
            if self.revision:
                s += " ({0})".format(self.revision)
        else:
            if s:
                s += ":"
            s += self.revision
        return s

    # Compare tags or revisions as needed (This allows us to seamlessly resolve
    # a tag into a revision in Image.__init__):
    def __eq__(self, other):
        if self.username == other.username and \
            self.repository == other.repository:
                if not self.revision or not other.revision:
                    return self.tag == other.tag
                return self.revision == other.revision
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def _is_revision(rev):
        return re.match("^({0}{{12}}|{0}{{64}})$".format("[0-9a-fA-F]"), rev)

    @staticmethod
    def _parse_user_and_repo(username_and_repo):
        username = repository = None
        user_separator = username_and_repo.find("/")
        if user_separator != 0:
            if username_and_repo and user_separator != -1:
                username = username_and_repo[:user_separator]
                repository = username_and_repo[user_separator + 1:]
            elif username_and_repo == "<none>":
                repository = None
            else:
                repository = username_and_repo

        return username, repository

    @property
    def fqrn(self):
        if self.username and self.repository:
            return "{0}/{1}".format(self.username, self.repository)
        return self.repository

    @classmethod
    def parse(cls, revspec):
        """Parse a Docker image name and return an :class:`ImageRevSpec` object.

        Docker image names are in the form::

           revspec = [ user "/" ] repo [ ":" ( tag | revision ) ]
                   | revision ;
        """

        username = repository = revision = tag = username_and_repo = None
        revspec_len = len(revspec)
        rev_separator = revspec.find(":")
        user_separator = revspec.find("/")

        if user_separator == revspec_len - 1:
            raise ValueError("Invalid image: {0} (missing repository)".format(
                revspec
            ))
        if rev_separator == revspec_len - 1:
            raise ValueError("Invalid image: {0} (missing revision)".format(
                revspec
            ))

        if rev_separator != -1:
            rev_or_tag = revspec[rev_separator + 1:]
            if cls._is_revision(rev_or_tag):
                revision = rev_or_tag
            else:
                tag = rev_or_tag
            if rev_separator > 0:
                username_and_repo = revspec[:rev_separator]
        elif not cls._is_revision(revspec):
            username_and_repo = revspec
            tag = "latest"
        else:
            revision = revspec
        if username_and_repo:
            username, repository = cls._parse_user_and_repo(username_and_repo)
            if username is None and repository is None:
                raise ValueError("Invalid image: {0} (missing username)".format(
                    revspec
                ))

        if tag and not username_and_repo:
            raise ValueError(
                "Invalid image: {0} (tag without repository)".format(revspec)
            )

        return cls(username, repository, revision, tag)

    @classmethod
    def parse_from_docker(cls, revspec):
        username = repository = revision = tag = None

        if revspec:
            parts = re.split("\s+", revspec, maxsplit=3)
            parts_len = len(parts)
            if not revspec[0].isspace(): # we have an username and/or repo
                username, repository = cls._parse_user_and_repo(parts[0])
                if parts_len >= 2:
                    if cls._is_revision(parts[1]):
                        revision = parts[1]
                    elif parts_len >= 2:
                        tag = None if parts[1] == "<none>" else parts[1]
                        revision = parts[2]
            elif parts_len > 1:
                revision = parts[1]

        if revision and cls._is_revision(revision):
            return cls(username, repository, revision, tag)

        raise ValueError(
            "Invalid image: {0} (can't find the revision)".format(revspec)
        )

class Image(object):
    """Represent an image in Docker. Can be used to start a :class:`Container`.

    :param revspec: :class:`ImageRevSpec` that identify a specific image version.
    :raises: :class:`~udotcloud.sandbox.exceptions.UnkownImageError` If the
             image is not know from the local Docker.

    .. attribute:: revspec

       The :class:`ImageRevSpec` identifying the underlying Docker image.

    .. attribute:: username

       The username for this image or None.

    .. attribute:: repository

       The repository for this image or None.

    .. attribute:: revision

       The revision for this image or None.

    .. attribute:: tag

       The tag for this image or None.

    .. attribute:: fqrn

       The string username/repository if both are set, repository if the
       username is missing, or None if everything is missing (fqrn stands for
       “Fully Qualified Repository Name”).
    """

    def __init__(self, revspec):
        logging.debug("Looking for {0} in docker images".format(revspec))
        with _CatchDockerError():
            images = gevent.subprocess.check_output(
                ["docker", "images"], stderr=gevent.subprocess.STDOUT
            ).splitlines()[1:]
        docker_revspecs = []
        for line in images:
            try:
                docker_revspecs.append(ImageRevSpec.parse_from_docker(line))
            except ValueError as ex:
                logging.warning(str(ex))
        # check that the image exists in Docker, and if so save it (it will
        # have the revision, which might not be the case of the revspec
        # received in argument).
        for docker_revspec in docker_revspecs:
            if revspec == docker_revspec:
                self.revspec = docker_revspec
                return
        raise UnkownImageError(
            "The image {0} doesn't exist "
            "(maybe you need to pull it in Docker?)".format(revspec)
        )

    def __str__(self):
        return self.revspec.__str__()

    def __repr__(self):
        return "<{0}(revspec={1}) at {2:#x}>".format(
            self.__class__.__name__, repr(self.revspec), id(self)
        )

    def __getattr__(self, name):
        if name in ["username", "repository", "revision", "tag", "fqrn"]:
            return getattr(self.revspec, name)
        raise AttributeError("'{0}' object has no attribute '{1}'".format(
            self.__class__.__name__, name
        ))

    # NOTE: This is not perfect: if you instantiate several Image object for
    # the same revision and destroy one of them, the others become invalid, but
    # it will not be catched by this.
    def _check_exists(method):
        def wrapped(self, *args, **kwargs):
            if not self.revspec:
                raise UnkownImageError(
                    "You tried to {0} a destroyed image".format(method.__name__)
                )
            return method(self, *args, **kwargs)
        return wrapped

    @_check_exists
    def instantiate(self, *args, **kwargs):
        return Container(self, *args, **kwargs)

    @_check_exists
    def destroy(self):
        """Remove the image from Docker.

        .. warning::

           Once you have called this method the current object is invalidated
           and you can't call further method on it. If you have multiple
           :class:`Image` objects pointing to the same revision (but with
           different tags for example), and destroy one of them, then the
           others will become invalid too.
        """

        logging.debug("Destroying image {0} from Docker".format(self.revspec))
        with _CatchDockerError():
            gevent.subprocess.check_call([
                "docker", "rmi", self.revspec.revision
            ])
        self.revspec = None

    @_check_exists
    def add_tag(self, tag):
        """Add a new tag to this image.

        :return: the new :class:`Image`.
        """

        logging.debug("Tagging {0} as {1}".format(self.revspec, tag))
        with _CatchDockerError():
            gevent.subprocess.check_call([
                "docker", "tag", self.revspec.revision, self.revspec.fqrn, tag
            ])
        # We can't re-instantiate an Image object, because it might resolve to
        # the wrong revspec when it parses the output of docker images (and
        # it's slower anyway):
        new_image = copy.copy(self)
        new_image.revspec = ImageRevSpec(*(self.revspec[:-1] + (tag,)))
        return new_image

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-

"""
sandbox.exceptions
~~~~~~~~~~~~~~~~~~
"""

class SandboxError(Exception):
    """Base class for all exceptions in the `Sandbox`_ module."""
    pass

class UnkownImageError(SandboxError):
    """Raised when an Image cannot be found in Docker."""
    pass

class DockerError(Exception):
    pass

class DockerNotFoundError(DockerError):
    pass

class DockerCommandError(DockerError):
    pass

########NEW FILE########
__FILENAME__ = sources
# -*- coding: utf-8 -*-

"""
sandbox.sources
~~~~~~~~~~~~~~~

This module implements :class:`Application` which is the counterpart of
:class:`builder.Builder <udotcloud.builder.builder.Builder>`.
"""

import contextlib
import copy
import gevent
import gevent.event
import gevent.subprocess
import itertools
import json
import logging
import os
import pkg_resources
import pprint
import re
import shutil
import signal
import socket
import tempfile
import termios
import time
import yaml

from .. import builder
from .buildfile import load_build_file
from .containers import ImageRevSpec, Image
from .exceptions import UnkownImageError
from .tarfile import Tarball
from ..utils import strsignal

class Application(object):
    """Represents a dotCloud application.

    :param root: source directory of the application.
    :param env: additional environment variables to define for this application.
    """

    def __init__(self, root, env):
        self._root = root
        #: Name of the application
        self.name = os.path.basename(os.path.abspath(root))
        username = os.environ.get("USER", "undefined")
        #: Environment for the application
        self.environment = {
            "DOTCLOUD_PROJECT": self.name,
            "DOTCLOUD_ENVIRONMENT": "default",
            "DOTCLOUD_FLAVOR": "microsandbox",
            "DOTCLOUD_USERNAME": username,
            "DOTCLOUD_EMAIL": os.environ.get(
                "EMAIL", "{0}@{1}".format(username, socket.getfqdn())
            )
        }
        self.environment.update(env)
        with open(os.path.join(self._root, "dotcloud.yml"), "r") as yml:
            self._build_file = load_build_file(yml.read())
        #: List of :class:`Service` in the application
        self.services = [
            Service(self, name, definition)
            for name, definition in self._build_file.iteritems()
        ]
        self._buildable_services = [s for s in self.services if s.buildable]

    def __str__(self):
        return "{0}: {1}".format(self.name, pprint.pformat(self._build_file))

    @staticmethod
    @contextlib.contextmanager
    def _build_dir():
        build_dir = tempfile.mkdtemp(prefix="dotcloud-")
        yield build_dir
        shutil.rmtree(build_dir, ignore_errors=True)

    @staticmethod
    @contextlib.contextmanager
    def _reset_terminal():
        old = termios.tcgetattr(1)
        yield
        termios.tcsetattr(1, termios.TCSAFLUSH, old)

    def _generate_application_tarball(self, app_build_dir):
        logging.debug("Archiving {0} in {1}".format(self.name, app_build_dir))
        app_tarball = Tarball.create_from_files(
            ".",
            os.path.join(app_build_dir, "application.tar"),
            self._root
        )
        app_tarball.wait()
        sandbox_sdist = os.path.join(app_build_dir, "udotcloud.sandbox.tar.gz")
        shutil.copy(
            pkg_resources.resource_filename(
                "udotcloud.sandbox",
                "../dist/udotcloud.sandbox.tar.gz"
            ),
            sandbox_sdist
        )
        bootstrap_script = os.path.join(app_build_dir, "bootstrap.sh")
        shutil.copy(
            pkg_resources.resource_filename(
                "udotcloud.sandbox", "../builder/bootstrap.sh"
            ),
            bootstrap_script
        )
        ssh_keys = os.path.join(app_build_dir, "authorized_keys2")
        with open(ssh_keys, "w") as fp:
            os.fchmod(fp.fileno(), 0600)
            for algorithm in ["rsa", "dsa", "ecdsa"]:
                try:
                    pub_key = os.path.expanduser(
                        "~/.ssh/id_{0}.pub".format(algorithm)
                    )
                    fp.write(open(pub_key, "r").read())
                    logging.info("Picked-up your SSH public key {0}".format(
                        os.path.basename(pub_key)
                    ))
                except IOError:
                    pass

        return [app_tarball.dest, sandbox_sdist, bootstrap_script, ssh_keys]

    def build(self, base_image=None):
        """Build the application using Docker.

        :return: a dictionnary with the service names in keys and the resulting
                 Docker images in values. Returns an empty dictionnary if there
                 is no buildable service in this application (i.e: only
                 databases). Returns None if one service couldn't be built.
        """

        if not self._buildable_services:
            return {}

        if not base_image:
            # TODO: design something to automatically pick a base image.
            logging.error(
                "You need to specify the base image to use via the -i option "
                "(you can pull and try lopter/sandbox-base)"
            )
            return

        with self._build_dir() as build_dir, self._reset_terminal():
            app_files = self._generate_application_tarball(build_dir)
            logging.debug("Starting parallel build for {0} services".format(
                len(self._buildable_services)
            ))
            greenlets = [
                gevent.spawn(s.build, build_dir, app_files, base_image)
                for s in self._buildable_services
            ]
            gevent.joinall(greenlets)
            for service, result in zip(self._buildable_services, greenlets):
                try:
                    if not result.get():
                        return None
                except Exception:
                    logging.exception("Couldn't build service {0} ({1})".format(
                        service.name, service.type
                    ))
                    return None

        return {s.name: s.result_image for s in self.services if s.buildable}

    def run(self):
        """Run the application in Docker using the result of the latest build.

        :raises: :class:`~udotcloud.sandbox.exceptions.UnkownImageError` if the
                 application wasn't correctly built.

        .. note::

           Only buildable services are run, databases won't be started.
           Moreover, keep in mind that postinstall has not been executed during
           the build (postinstall expects to have the databases running).
        """

        def signal_handler(signum):
            logging.info("{0} caught, stopping {1} services…".format(
                strsignal(signum), len(greenlets)
            ))
            gevent.joinall([gevent.spawn(service.stop) for service in services])

        def get_status(service, result):
            try:
                exit_status = result.get(block=False)
                if exit_status == 0:
                    return True
                if len(self._buildable_services) > 1:
                    logging.info("Stopping the other services…")
                    gevent.joinall([
                        gevent.spawn(service.stop) for service in services
                    ])
            except gevent.Timeout:
                return None
            except UnkownImageError:
                logging.error(
                    "Couldn't find the image to run for service {0} ({1}), did "
                    "you build it?".format(service.name, service.type)
                )
            except Exception:
                logging.exception("Couldn't run service {0} ({1})".format(
                    service.name, service.type
                ))
            return False

        stop_ev = gevent.event.Event()
        services = [service for service in self._buildable_services]
        greenlets = [gevent.spawn(service.run, stop_ev) for service in services]
        sigterm_handler = gevent.signal(signal.SIGTERM, signal_handler)
        ret = True
        try:
            while greenlets:
                remaining_greenlets = []
                try:
                    stop_ev.wait()
                    stop_ev.clear()
                    for service, result in zip(self._buildable_services, greenlets):
                        status = get_status(service, result)
                        if status is None:
                            remaining_greenlets.append(result)
                        elif not status:
                            ret = status
                except KeyboardInterrupt:
                    signal_handler(signal.SIGINT)
                greenlets = remaining_greenlets
        finally:
            gevent.signal(signal.SIGTERM, sigterm_handler)
        return ret

class Service(object):
    """Represents a single service within a dotCloud application."""

    CUSTOM_PORTS_RANGE_START = 42800

    def __init__(self, application, name, definition):
        self._application = application
        self.name = name
        self.result_image = None
        for k, v in definition.iteritems():
            setattr(self, k, v)
        # I don't really know what happens in the yaml library but looks like
        # it does some caching and if we don't copy the environment here, the
        # modified version will leak accross unit tests:
        self.environment = copy.copy(self.environment)
        self.environment["DOTCLOUD_SERVICE_NAME"] = self.name
        self.environment["DOTCLOUD_SERVICE_ID"] = 0
        # Let's keep it as real dict too, so we can easily dump it:
        self._definition = definition
        self._definition['environment'] = self.environment
        self._extract_path = "/home/dotcloud"
        if self.type == "custom":
            self._extract_path = "/tmp"
        self.buildable = bool(builder.services.get_service_class(self.type))
        # "Allocate" the custom ports we are going to bind too inside the
        # container
        self._allocate_custom_ports()
        self._container = None

    # XXX This is half broken right now, since we will loose the original
    # protocol of the port (tcp or udp), anyway good enough for now (docker
    # doesn't support udp ports anyway).
    def _allocate_custom_ports(self):
        http_ports_count = self.ports.values().count("http")
        if (not re.match(r"^(custom|.+worker)$", self.type) and http_ports_count) \
            or ("worker" in self.type and http_ports_count > 1):
            logging.warning(
                "A http port was already defined for service "
                "{0} ({1})".format(self.name, self.type)
            )

        ports = {}
        port_number = self.CUSTOM_PORTS_RANGE_START
        for name, proto in self.ports.iteritems():
            ports[name] = str(port_number)
            port_number += 1
        self.ports = ports

    def _result_revspec(self):
        return ImageRevSpec.parse("{0}-{1}:ts-{2}".format(
            self._application.name, self.name, int(time.time())
        ))

    @property
    def _latest_result_revspec(self):
        return ImageRevSpec.parse("{0}-{1}:latest".format(
            self._application.name, self.name
        ))

    def _build_revspec(self):
        return ImageRevSpec(None, None, None, None) # keep build rev anonymous

    def _generate_environment_files(self, svc_build_dir):
        # environment.{json,yml} + .dotcloud_profile
        env_json = os.path.join(svc_build_dir, "environment.json")
        env_yml = os.path.join(svc_build_dir, "environment.yml")
        env_profile = os.path.join(svc_build_dir, "dotcloud_profile")
        env = {
            key: value for key, value in itertools.chain(
                self._application.environment.iteritems(),
                self.environment.iteritems()
            )
        }
        env.update({
            "PORT_{0}".format(name.upper()): port
            for name, port in self.ports.iteritems()
        })
        with open(env_json, 'w') as fp:
            json.dump(env, fp, indent=4)
        with open(env_yml, 'w') as fp:
            yaml.safe_dump(env, fp, indent=4, default_flow_style=False)
        with open(env_profile, 'w') as fp:
            fp.writelines([
                "export {0}={1}\n".format(k, v) for k, v in env.iteritems()
            ])
        return [env_json, env_yml, env_profile]

    def _dump_service_definition(self, svc_build_dir):
        definition = os.path.join(svc_build_dir, "definition.json")
        with open(definition, "w") as fp:
            json.dump(dict(self._definition, name=self.name), fp, indent=4)
        return definition

    def _generate_service_tarball(self, app_build_dir, app_files):
        svc_build_dir = os.path.join(app_build_dir, self.name)
        os.mkdir(svc_build_dir)
        svc_tarball_name = "service.tar"
        app_files_names = [os.path.basename(path) for path in app_files]

        svc_files = self._generate_environment_files(svc_build_dir)
        svc_files.append(self._dump_service_definition(svc_build_dir))
        svc_tarball = Tarball.create_from_files(
            [os.path.basename(path) for path in svc_files],
            os.path.join(svc_build_dir, svc_tarball_name),
            svc_build_dir
        )
        svc_tarball.wait()

        for name, path in zip(app_files_names, app_files):
            os.link(path, os.path.join(svc_build_dir, name))
        app_files_names.append(svc_tarball_name)
        svc_tarball = Tarball.create_from_files(
            app_files_names,
            os.path.join(app_build_dir, "{0}.tar".format(self.name)),
            svc_build_dir
        )
        svc_tarball.wait()
        return svc_tarball

    def _unpack_service_tarball(self, svc_tarball_path, container):
        logging.debug("Extracting code in service {0}".format(self.name))
        with open(svc_tarball_path, "r") as source:
            tar_extract = ["tar", "-xf", "-", "-C", self._extract_path]
            with container.run(tar_extract, stdin=container.PIPE) as dest:
                buf = source.read(8192)
                while buf:
                    dest.stdin.write(buf)
                    buf = source.read(8192)
                dest.stdin.close()

    def build(self, app_build_dir, app_files, base_image):
        logging.info("Building service {0}…".format(self.name))
        # Install system packages
        logging.debug("Installing system packages {0} for service {1}".format(
            ", ".join(self.systempackages), self.name
        ))
        self._container = base_image.instantiate(
            commit_as=self._build_revspec()
        )
        self._container.install_system_packages(self.systempackages)
        svc_tarball = self._generate_service_tarball(app_build_dir, app_files)
        logging.debug("Tarball for service {0} generated at {1}".format(
            self.name, svc_tarball.dest
        ))
        # Upload all the code:
        self._container = self._container.result.instantiate(
            commit_as=self._build_revspec()
        )
        self._unpack_service_tarball(svc_tarball.dest, self._container)
        # Install the builder via the bootstrap script
        self._container = self._container.result.instantiate(
            commit_as=self._build_revspec()
        )
        bootstrap_script = os.path.join(self._extract_path, "bootstrap.sh")
        with self._container.run([bootstrap_script]):
            logging.debug("Installing builder in service {0}".format(self.name))
        logging.debug("Builder bootstrap logs:\n{0}".format(
            self._container.logs
        ))
        if self._container.exit_status != 0:
            logging.warning(
                "Couldn't install the builder in service {0} (bootstrap script "
                "returned {1}".format(self.name, self._container.exit_status)
            )
        # And run it
        self._container = self._container.result.instantiate(
            commit_as=self._result_revspec()
        )
        # Since we don't actually go through login(1) we need to set HOME
        # otherwise, .profile won't be executed by login shells:
        with self._container.run(
            [builder.BUILDER_INSTALL_PATH, self._extract_path],
            env={"HOME": "/home/dotcloud"}, as_user="dotcloud"
        ):
            logging.debug("Running builder in service {0}".format(self.name))
        logging.info("Build logs for {0}:\n{1}".format(
            self.name, self._container.logs
        ))
        if self._container.exit_status != 0:
            logging.error(
                "The build failed on service {0}: the builder returned {1} "
                "(expected 0)".format(self.name, self._container.exit_status)
            )
            return False
        self.result_image = self._container.result
        self.result_image.add_tag("latest")
        self._container = None
        return True

    def run(self, stop_ev):
        try:
            image = Image(self._latest_result_revspec)
            self._container = image.instantiate()
            ports = self.ports.values()
            ports.append(2222)
            if not "worker" in self.type:
                ports.append(8080)
            supervisor_cmd = "exec supervisord -nc {0}".format(os.path.join(
                self._extract_path, "supervisor.conf"
            ))
            logging.info("Starting Supervisor in {0}".format(image))
            with self._container.run_stream_logs(
                ["/bin/sh", "-lc", supervisor_cmd],
                env={"HOME": "/home/dotcloud"},
                as_user="dotcloud",
                ports=ports
            ) as supervisor:
                for port, mapped_port in supervisor.ports.iteritems():
                    if port == 2222:
                        logging.info(
                            "You can ssh on service {0} with: `ssh -p {1} "
                            "dotcloud@<your-docker-host>`".format(
                                self.name, mapped_port
                            )
                        )
                    else:
                        logging.info(
                            "Port {0} on service {1} mapped to {2} on the "
                            "Docker host".format(port, self.name, mapped_port)
                        )
            if self._container.exit_status != 0:
                logging.warning(
                    "Service {0} didn't exit normally (returned "
                    "{1})".format(self.name, self._container.exit_status)
                )
            else:
                logging.info("Service {0} exited".format(self.name))
            exit_status = self._container.exit_status
            self._container = None
            return exit_status
        finally: # Avoid any stupid deadlock
            stop_ev.set()

    def stop(self):
        """If the service is currently running or building, interrupt it."""

        if self._container:
            self._container.stop()

########NEW FILE########
__FILENAME__ = tarfile
# -*- coding: utf-8 -*-

import gevent
import gevent.subprocess

# Previous experience (in Python 2.6.x) has shown that the tarfile module is
# utterly broken, this is why tar is directly used here.

class TarError(Exception):
    pass

class TarCreateError(TarError):
    def __init__(self, returncode, stderr):
        self.message = "tar returned {0}: {1}".format(returncode, stderr)

class Tarball(object):
    """Utility class around :mod:`gevent.subprocess` and the tar command."""

    def __init__(self, dest, tar_process=None):
        self.dest = dest
        self._tar_process = tar_process
        self._stderr = gevent.spawn(tar_process.stderr.read)

    @classmethod
    def create_from_files(cls, files, dest, root_dir=None):
        # The companion method would be extract_from_stream but we don't need
        # it (we are going to use tar directly inside the container).
        cmd = ["tar", "-cf"]
        if isinstance(dest, basestring):
            cmd.append(dest)
            stdout = None
        else:
            cmd.append("-")
            stdout = dest
        if root_dir:
            cmd.extend(["-C", root_dir])
        cmd.extend(files if isinstance(files, list) else [files])

        tar = gevent.subprocess.Popen(
            cmd, stdout=stdout, stderr=gevent.subprocess.PIPE
        )
        return cls(dest, tar)

    def poll(self):
        """Poll the status of the tarball creation.

        :return: True if the tarball has been completely written else False.
        :raise TarCreateError: if tar didn't return 0.
        """

        return False if self.wait(_block=False) is False else True

    def wait(self, _block=True):
        """Wait until the tarball has been entirely written.

        :raise TarCreateError: if tar didn't return 0.
        """

        if _block:
            ret = self._tar_process.wait()
        else:
            ret = self._tar_process.poll()
            if ret is None:
                return False
        stderr = self._stderr.get()
        # as in communicate:
        self._tar_process.stderr.close()
        if self._tar_process.stdout:
            self._tar_process.stdout.close()
        if ret != 0:
            raise TarCreateError(ret, stderr)

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-

__version__ = "0.0.1"

########NEW FILE########
__FILENAME__ = wsgi
def application(environ, start_response):
    status = '200 OK'
    output = "\n".join([
	"<html>",
	"<style rel='stylesheet' type='text/css'>div, h1, table{ text-align: center; } table td { border: solid gray 1px; }</style>",
	"<title>Hello world</title>",
	"<h1>Hello world!</h1>",
	"<table align='center'>" + "\n".join(["<tr><td>{0}</td><td>{1}</td></tr>".format(key, value) for (key, value) in environ.items()]) + "</table>",
	"</html>"
    ])

    response_headers = [('Content-type', 'text/html'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

########NEW FILE########
__FILENAME__ = wsgi
def application(environ, start_response):
    status = '200 OK'
    output = "\n".join([
	"<html>",
	"<style rel='stylesheet' type='text/css'>div, h1, table{ text-align: center; } table td { border: solid gray 1px; }</style>",
	"<title>Hello world</title>",
	"<h1>Hello world!</h1>",
	"<table align='center'>" + "\n".join(["<tr><td>{0}</td><td>{1}</td></tr>".format(key, value) for (key, value) in environ.items()]) + "</table>",
	"</html>"
    ])

    response_headers = [('Content-type', 'text/html'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

########NEW FILE########
__FILENAME__ = test_builder
# -*- coding: utf-8 -*-

import gevent.subprocess
import logging; logging.basicConfig(level="DEBUG")
import os
import shutil
import tempfile
import unittest

from distutils.spawn import find_executable

from udotcloud.sandbox import Application
from udotcloud.builder import Builder
from udotcloud.builder.services import get_service

class TestBuilderCase(unittest.TestCase):

    sources_path = "simple_gunicorn_gevent_app"
    service_name = "api"

    def setUp(self):
        self.builddir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")
        # Fake /home/dotcloud directory:
        self.installdir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")
        self.code_dir = os.path.join(self.installdir, "code")
        self.current_dir = os.path.join(self.installdir, "current")
        self.path = os.path.dirname(__file__)
        self.application = Application(
            os.path.join(self.path, self.sources_path), {}
        )
        self.service = None
        for service in self.application.services:
            if service.name == self.service_name:
                self.service = service
                break
        if self.service is None:
            self.fail("Service {0} isn't defined in {1}".format(
                self.service_name, self.sources_path
            ))
        app_files = self.application._generate_application_tarball(self.builddir)
        svc_tarball = self.service._generate_service_tarball(self.builddir, app_files)
        gevent.subprocess.check_call([
            "tar", "-xf", svc_tarball.dest, "-C", self.installdir
        ])
        self.builder = Builder(self.installdir)

    def tearDown(self):
        shutil.rmtree(self.builddir, ignore_errors=True)
        shutil.rmtree(self.installdir, ignore_errors=True)

class TestBuilderUnpack(TestBuilderCase):

    sources_path = "simple_gunicorn_gevent_app"
    service_name = "api"

    def test_builder_unpack(self):
        self.builder._unpack_sources()

        self.assertTrue(os.path.isdir(self.code_dir))
        self.assertTrue(os.path.exists(os.path.join(self.code_dir, "dotcloud.yml")))
        self.assertFalse(os.path.exists(os.path.join(self.installdir, "application.tar")))

        self.assertTrue(os.path.exists(os.path.join(self.installdir, "environment.json")))
        self.assertTrue(os.path.exists(os.path.join(self.installdir, "environment.yml")))
        self.assertFalse(os.path.exists(os.path.join(self.installdir, "service.tar")))
        self.assertFalse(os.path.exists(os.path.join(self.installdir, "definition.json")))

        self.assertTrue(os.path.exists(os.path.join(self.installdir, ".ssh/authorized_keys2")))

class TestBuilderPythonWorker(TestBuilderCase):

    sources_path = "simple_gunicorn_gevent_app"
    service_name = "api"

    def test_builder_build(self):
        if not find_executable("virtualenv"):
            self.skipTest(
                "You need to install python-virtualenv "
                "to run the Python services unit tests"
            )

        self.builder.build()

        self.assertTrue(os.path.islink(self.current_dir))
        self.assertTrue(os.path.exists(os.path.join(self.current_dir, "dotcloud.yml")))

        self.assertTrue(os.path.exists(os.path.join(self.current_dir, "prebuild")))
        self.assertTrue(os.path.exists(os.path.join(self.current_dir, "postbuild")))

        # Check that the virtualenv activation has been correctly appended to
        # dotcloud_profile:
        dotcloud_profile = open(os.path.join(self.installdir, "dotcloud_profile")).read()
        self.assertIn("DOTCLOUD_SERVICE_ID", dotcloud_profile)
        self.assertEqual(dotcloud_profile.count("env/bin/activate"), 1)

        self.assertTrue(os.path.exists(os.path.join(self.installdir, "supervisor.conf")))
        supervisor_configuration = open(os.path.join(self.installdir, "supervisor.conf")).read()
        self.assertIn("""[program:api]
command=/bin/sh -lc "exec gunicorn -k gevent -b 0.0.0.0:$PORT_WWW -w 2 wsgi:application"
directory={install_dir}/current
stdout_logfile={install_dir}/supervisor/api.log
stderr_logfile={install_dir}/supervisor/api_error.log

""".format(install_dir=self.installdir), supervisor_configuration)
        self.assertIn("/home/dotcloud/current/supervisord.conf", supervisor_configuration)

        virtualenv_bin = os.path.join(self.installdir, "env", "bin")
        installed_packages = gevent.subprocess.Popen(
            [os.path.join(virtualenv_bin, "pip"), "freeze"],
            stdout=gevent.subprocess.PIPE
        )
        python_version = gevent.subprocess.Popen(
            [os.path.join(virtualenv_bin, "python"), "-V"],
            stderr=gevent.subprocess.PIPE
        )
        installed_packages = installed_packages.communicate()[0]
        python_version = python_version.communicate()[1]
        self.assertRegexpMatches(python_version, "^Python 2.7")
        self.assertIn("gunicorn", installed_packages)

class TestBuilderCustom(TestBuilderCase):

    sources_path = "custom_app"
    service_name = "db"

    def test_builder_build(self):
        self.builder._unpack_sources()
        custom_svc_builder = get_service(
            self.builder._build_dir,
            self.builder._current_dir,
            self.builder._svc_definition
        )

        self.assertEqual(custom_svc_builder._supervisor_dir, "/home/dotcloud/supervisor")
        # Reset them to our test directory (otherwise the test suite will try
        # to write in ~dotcloud on your computer).
        custom_svc_builder._supervisor_dir = os.path.join(custom_svc_builder._build_dir, "supervisor")
        custom_svc_builder._sshd_config = os.path.join(custom_svc_builder._supervisor_dir, "sshd_config")
        custom_svc_builder._profile = os.path.join(custom_svc_builder._build_dir, "dotcloud_profile")

        custom_svc_builder.build()

        self.assertFalse(os.path.exists(self.current_dir))

        self.assertTrue(os.path.exists(os.path.join(self.code_dir, "buildscript-stamp")))

        self.assertTrue(os.path.exists(os.path.join(self.installdir, "supervisor.conf")))
        supervisor_configuration = open(os.path.join(self.installdir, "supervisor.conf")).read()
        print supervisor_configuration
        print supervisor_configuration
        self.assertIn("""[program:db]
command=/bin/bash -lc "[ -f ~/profile ] && . ~/profile; exec ~/run"
directory=/home/dotcloud
stdout_logfile={install_dir}/supervisor/db.log
stderr_logfile={install_dir}/supervisor/db_error.log

""".format(install_dir=self.installdir), supervisor_configuration)

class TestBuilderBrokenBuild(TestBuilderCase):

    sources_path = "broken_build"
    service_name = "api"

    def test_builder_build(self):
        self.assertEqual(self.builder.build(), 42)

########NEW FILE########
__FILENAME__ = test_buildfile
# -*- coding: utf-8 -*-
# Started by François-Xavier Bourlet <fx@dotcloud.com>, Oct 2011.

import logging; logging.basicConfig(level="DEBUG")
import unittest

from udotcloud.sandbox.buildfile import load_build_file, SchemaError

class TestBuildFile(unittest.TestCase):


    def test_simple(self):
        build_file = '''
www:
    type: python
    instances: 1
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': '.',
            'config': {},
            'environment': {},
            'instances': 1,
            'postinstall': '',
            'process': '',
            'processes': {},
            'ports': {},
            'requirements': [],
            'systempackages': [],
            'type': 'python'}})


    def test_empty(self):
        build_file = '''
    '''
        with self.assertRaises(ValueError):
            load_build_file(build_file)


    def test_empty2(self):
        build_file = '''
{}
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'service(s) dict cannot be empty in "dotcloud.yml", line 2, column 1')
                raise


    def test_empty_service(self):
        build_file = '''
www: {}
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Missing mandatory entry: "type" in "dotcloud.yml", line 2, column 6')
                raise


    def test_top_error(self):
        build_file = '''
www
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Expected a type dictionary but got a type string in "dotcloud.yml", line 2, column 1')
                raise


    def test_top_error2(self):
        build_file = '''
- www
- lolita
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Expected a type dictionary but got a type list in "dotcloud.yml", line 2, column 1')
                raise


    def test_more(self):
        build_file = '''
www:
    type: python
    approot: 42
    environment:
        caca: lol
    customshit:
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': '42',
            'config': {},
            'customshit': None,
            'environment': {'caca': 'lol'},
            'instances': 1,
            'postinstall': '',
            'process': '',
            'ports': {},
            'processes': {},
            'requirements': [],
            'systempackages': [],
            'type': 'python'}})


    def test_even_more(self):
        build_file = '''
www:
    type: python
    approot: 42
    environment:
        caca: lol
    systempackages:
        - vim
    customshit:
db:
    type: python
    environment:
       MYVAR: "my lovely var"
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(
            desc,
            {
                'db': {
                    'approot': '.',
                    'config': {},
                    'environment': {'MYVAR': 'my lovely var'},
                    'instances': 1,
                    'postinstall': '',
                    'process': '',
                    'ports': {},
                    'processes': {},
                    'requirements': [],
                    'systempackages': [],
                    'type': 'python'
                },
                'www': {
                    'approot': '42',
                    'config': {},
                    'customshit': None,
                    'environment': {'caca': 'lol'},
                    'instances': 1,
                    'process': '',
                    'processes': {},
                    'ports': {},
                    'postinstall': '',
                    'requirements': [],
                    'systempackages': ['vim'],
                    'type': 'python'
                }
            }
        )


    def test_type_error(self):
        build_file = '''
www:
    type: lolita
    instances: 1
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Unrecognized service "lolita" in "dotcloud.yml", line 3, column 11')
                raise


    def test_process_and_processes(self):
        build_file = '''
www:
    type: python
    process: string
    processes:
        a: 1
        b: 2
'''
        with self.assertRaises(ValueError):
            try:
                load_build_file(build_file)
            except ValueError as e:
                self.assertEqual(str(e), 'You can\'t have both "process" and "processes" at the same time in service "www"')
                raise

    def test_custom_build_simple(self):
        build_file = '''
www:
    type: custom
    approot: ./web
    buildscript: builder
    process: ~/myapp.py
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': './web',
            'buildscript': 'builder',
            'config': {},
            'environment': {},
            'ports': {},
            'instances': 1,
            'postinstall': '',
            'processes': {},
            'process': '~/myapp.py',
            'requirements': [],
            'systempackages': [],
            'type': 'custom'}})


    def test_custom_build_port(self):
        build_file = '''
worker:
    type: custom
    buildscript: builder
    process: ~/myapp.py
    ports:
        www: http
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'worker': {'approot': '.',
                'buildscript': 'builder',
                'config': {},
                'environment': {},
                'instances': 1,
                'ports': {'www': 'http'},
                'postinstall': '',
                'process': '~/myapp.py',
                'processes': {},
                'requirements': [],
                'systempackages': [],
                'type': 'custom'}})


    def test_custom_invalid_build_port(self):
        build_file = '''
worker:
    type: custom
    buildscript: builder
    process: ~/myapp.py
    ports:
        www: prout
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Unrecognized port "prout" in "dotcloud.yml", line 7, column 14')
                raise


    def test_custom_build_port_empty(self):
        build_file = '''
worker:
    type: custom
    buildscript: builder
    process: ~/myapp.py
    ports: {}
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'worker': {'approot': '.',
            'buildscript': 'builder',
            'config': {},
            'environment': {},
            'instances': 1,
            'ports': {},
            'postinstall': '',
            'process': '~/myapp.py',
            'processes': {},
            'requirements': [],
            'systempackages': [],
            'type': 'custom'}})


    def test_custom_build_complexe(self):
        build_file = '''
www:
    type: custom
    approot: ./web
    ports:
        www: http
        control: tcp
        collectd: tcp
    ruby_version: 1.9

'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': './web',
            'config': {},
            'environment': {},
            'instances': 1,
            'ports': {
                'www': 'http',
                'control': 'tcp',
                'collectd': 'tcp',
                },
            'postinstall': '',
            'requirements': [],
            'systempackages': [],
            'process': '',
            'processes': {},
            'ruby_version': '1.9',
            'type': 'custom'}})


    def test_service_name_validation(self):
        build_file = '''
    2:
        type: python
    '''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'2': {'approot': '.',
            'config': {},
            'environment': {},
            'ports': {},
            'instances': 1,
            'postinstall': '',
            'process': '',
            'processes': {},
            'requirements': [],
            'systempackages': [],
            'type': 'python'}})

        build_file = '''
www:sdf:
    type: python
'''
        with self.assertRaises(SchemaError):
            try:
                desc = load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Invalid characters (lowercase alphanum only) for service "www:sdf" in "dotcloud.yml", line 3, column 5')
                raise

        build_file = '''
123456789abceswseefsdfsdf:
    type: python
'''
        with self.assertRaises(SchemaError):
            try:
                desc = load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Invalid service name (must be <= 16 characters) "123456789abceswseefsdfsdf" in "dotcloud.yml", line 3, column 5')
                raise

########NEW FILE########
__FILENAME__ = test_containers
# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import random
import string
import unittest

from udotcloud.sandbox.containers import ImageRevSpec, Image
from udotcloud.sandbox.exceptions import UnkownImageError

class ContainerTestCase(unittest.TestCase):

    @staticmethod
    def random_image_name():
        return "{0}:unittest".format("".join(
            random.choice(string.ascii_lowercase) for i in xrange(10)
        ))

    def setUp(self):
        try:
            self.image = Image(ImageRevSpec.parse("lopter/sandbox-base:latest"))
            self.result_revspec = ImageRevSpec.parse(self.random_image_name())
            self.container = self.image.instantiate(commit_as=self.result_revspec)
        except UnkownImageError as ex:
            return self.skipTest(str(ex))

    def tearDown(self):
        if self.container.result:
            self.container.result.destroy()

class TestContainers(ContainerTestCase):

    def test_container_run_no_stdin(self):
        with self.container.run(["pwd"]):
            pass
        self.assertEqual(self.container.logs, "/\r\n")
        self.assertEqual(self.container.result.revspec, self.result_revspec)

    def test_container_run_stdin(self):
        with self.container.run(["cat"], stdin=self.container.PIPE) as cat:
            cat.stdin.write("TRAVERSABLE ")
            cat.stdin.write("WORMHOLE")
            cat.stdin.write("!\n")
            cat.stdin.close() # EOF
        self.assertEqual(self.container.logs, "TRAVERSABLE WORMHOLE!\n")
        self.assertEqual(self.container.result.revspec, self.result_revspec)
        self.assertEqual(self.container.exit_status, 0)

    def test_container_as_user(self):
        with self.container.run(["/bin/ls", "/root"], as_user="nobody"):
            pass
        self.assertIn("Permission denied", self.container.logs)
        self.assertEqual(self.container.exit_status, 2)

    def test_container_run_env(self):
        with self.container.run(["/usr/bin/env"], env={"TOTO": "POUET"}):
            pass
        self.assertIn("TOTO=POUET", self.container.logs)

    def test_container_as_user_stdin(self):
        with self.container.run(["/bin/ls", "/root"], as_user="nobody", stdin=self.container.PIPE) as ls:
            ls.stdin.close()
        self.assertIn("Permission denied", self.container.logs)

    def test_image_tag(self):
        with self.container.run(["pwd"]):
            pass
        self.assertEqual(self.container.result.tag, "unittest")
        tagged = self.container.result.add_tag("foobar")
        self.assertTupleEqual(
            tagged.revspec[:-1], self.container.result.revspec[:-1]
        )
        self.assertEqual(tagged.tag, "foobar")

    def test_run_stop(self):
        with self.container.run(["dd", "if=/dev/zero", "of=/dev/null"]):
            self.container.stop(wait=1)
        self.assertEqual(self.container.exit_status, 137) # SIGKILLED

    def test_run_stream_logs(self):
        with self.container.run_stream_logs(
            ["/bin/sh", "-c", "sleep 1; echo tick"],
            output=self.container.PIPE
        ) as container:
            self.assertIsInstance(container.ports, dict)
            output = container.communicate()[0]
            self.assertIn("tick\n", output)

    def test_run_stream_logs_ports(self):
        with self.container.run_stream_logs(
            ["/bin/sh", "-c", "sleep 1; echo tick"],
            output=self.container.PIPE,
            ports=[22]
        ) as container:
            self.assertIsInstance(container.ports, dict)
            self.assertIn(22, container.ports)
            output = container.communicate()[0]
            self.assertIn("tick\n", output)

    def test_run_stream_logs_env(self):
        with self.container.run_stream_logs(
            ["/bin/sh", "-c", "sleep 1; env"],
            output=self.container.PIPE,
            env={"TOTO": "POUET"}
        ) as container:
            self.assertIsInstance(container.ports, dict)
            output = container.communicate()[0]
            self.assertIn("TOTO=POUET", output)

    def test_run_stream_logs_stop(self):
        with self.container.run_stream_logs(["cat", "/dev/zero"]):
            self.container.stop(wait=1)

########NEW FILE########
__FILENAME__ = test_revspecs
# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import unittest

from udotcloud.sandbox.containers import ImageRevSpec, _ImageRevSpec

class TestRevSpecs(unittest.TestCase):

    human_revspecs = {
        "": None,
        ":": None,
        "/": None,
        "/:": None,
        ":/": None,
        ":1234": None,
        ":33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        "33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        ":71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625": _ImageRevSpec(None, None, "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625", None),
        "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625": _ImageRevSpec(None, None, "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625", None),
        "repo:1234": _ImageRevSpec(None, "repo", None, "1234"),
        "user/repo:1234": _ImageRevSpec("user", "repo", None, "1234"),
        "user/repo": _ImageRevSpec("user", "repo", None, "latest"),
        "repo:71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625": _ImageRevSpec(None, "repo", "71bed3ad1135a3c48c7f85bdcaead44e6bdf2c722caae375764fa38a4949d625", None),
        "user/repo:33b6d177c4bd": _ImageRevSpec("user", "repo", "33b6d177c4bd", None),
        "user/repo:latest": _ImageRevSpec("user", "repo", None, "latest"),
        "user/repo:latest/v1": _ImageRevSpec("user", "repo", None, "latest/v1"),
        "user/repo:latest:v1": _ImageRevSpec("user", "repo", None, "latest:v1"),
        "user/repo/toto": _ImageRevSpec("user", "repo/toto", None, "latest"),
        ":user/repo": None
    }

    # As in the output of docker images
    docker_revspec = {
        "": None,
        "base" : None,
        # The space in front denotes the fac that an username/repo is missing
        # (the output of docker images is tabbed):
        " 33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        " 33b6d177c4bd just now": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        " latest 33b6d177c4bd just now": None,
        "base latest 33b6d177c4bd 3 weeks ago": _ImageRevSpec(None, "base", "33b6d177c4bd", "latest"),
        "<none> <none> 33b6d177c4bd 3 weeks ago": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        "<none> <none> 33b6d177c4bd": _ImageRevSpec(None, None, "33b6d177c4bd", None),
        "base latest 33b6d177c4bd": _ImageRevSpec(None, "base", "33b6d177c4bd", "latest"),
        "base 33b6d177c4bd": _ImageRevSpec(None, "base", "33b6d177c4bd", None),
        "base 33b6d177c4bd 3 weeks ago": _ImageRevSpec(None, "base", "33b6d177c4bd", None),
        "lopter/raring-base 33b6d177c4bd 3 weeks ago": _ImageRevSpec("lopter", "raring-base", "33b6d177c4bd", None),
        "lopter/raring-base latest 33b6d177c4bd 3 weeks ago": _ImageRevSpec("lopter", "raring-base", "33b6d177c4bd", "latest"),
    }

    def test_human_revspecs(self):
        for revspec, expected in self.human_revspecs.iteritems():
            if expected is None:
                with self.assertRaises(ValueError):
                    ImageRevSpec.parse(revspec)
            else:
                result = ImageRevSpec.parse(revspec)
                # We don't want to test ImageRevSpec.__eq__ here:
                self.assertEqual(result.username, expected.username)
                self.assertEqual(result.repository, expected.repository)
                self.assertEqual(result.revision, expected.revision)
                self.assertEqual(result.tag, expected.tag)

    def test_docker_revspecs(self):
        for revspec, expected in self.docker_revspec.iteritems():
            if expected is None:
                with self.assertRaises(ValueError):
                    ImageRevSpec.parse_from_docker(revspec)
            else:
                result = ImageRevSpec.parse_from_docker(revspec)
                self.assertEqual(result.username, expected.username)
                self.assertEqual(result.repository, expected.repository)
                self.assertEqual(result.revision, expected.revision)
                self.assertEqual(result.tag, expected.tag)

########NEW FILE########
__FILENAME__ = test_sources
# -*- coding: utf-8 -*-

import contextlib
import logging; logging.basicConfig(level="DEBUG")
import json
import os
import shutil
import tempfile
import unittest
import yaml

from udotcloud.sandbox import Application
from udotcloud.sandbox.containers import ImageRevSpec, Image

from test_containers import ContainerTestCase

@contextlib.contextmanager
def _destroy_result(container):
    yield
    if container.result:
        container.result.destroy()

class TestApplication(unittest.TestCase):

    def setUp(self):
        self.path = os.path.dirname(__file__)

    def test_load_simple_application(self):
        application = Application(os.path.join(self.path, "simple_python_app"), {})
        self.assertEqual(len(application.services), 1)
        self.assertEqual(application.name, "simple_python_app")
        self.assertEqual(application.services[0].name, "www")
        self.assertEqual(application.services[0].type, "python")

    def test_load_simple_application_trailing_slash(self):
        application = Application(os.path.join(self.path, "simple_python_app") + "/", {})
        self.assertEqual(len(application.services), 1)
        self.assertEqual(application.name, "simple_python_app")
        self.assertEqual(application.services[0].name, "www")
        self.assertEqual(application.services[0].type, "python")

    def test_load_custom_packages_application(self):
        application = Application(os.path.join(self.path, "custom_app"), {})
        self.assertListEqual(application.services[0].systempackages, ["cmake"])

    def test_simple_application_build(self):
        application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {})
        images = application.build(base_image=Image(ImageRevSpec.parse("lopter/sandbox-base:latest")))
        self.assertIsInstance(images, dict)
        result = images.get("api")
        self.assertIsNotNone(result)
        container = result.instantiate(commit_as=ImageRevSpec.parse(
            ContainerTestCase.random_image_name()
        ))
        with _destroy_result(container):
            with container.run(["ls", "/home/dotcloud/current"]):
                pass
            self.assertIn("dotcloud.yml", container.logs)
        container = result.instantiate(commit_as=ImageRevSpec.parse(
            ContainerTestCase.random_image_name()
        ))
        with _destroy_result(container):
            with container.run(["stat", "-c", "%u", "/home/dotcloud/code"]):
                pass
            self.assertIn("1000", container.logs)

    def test_custom_application_build(self):
        application = Application(os.path.join(self.path, "custom_app"), {})
        images = application.build(base_image=Image(ImageRevSpec.parse("lopter/sandbox-base:latest")))
        self.assertIsInstance(images, dict)
        result = images.get("db")
        self.assertIsNotNone(result)
        container = result.instantiate(commit_as=ImageRevSpec.parse(
            ContainerTestCase.random_image_name()
        ))
        with _destroy_result(container):
            with container.run(["ls", "/tmp/code/"]):
                pass
            self.assertIn("dotcloud.yml", container.logs)
            self.assertIn("buildscript-stamp", container.logs)
        container = result.instantiate(commit_as=ImageRevSpec.parse(
            ContainerTestCase.random_image_name()
        ))
        with _destroy_result(container):
            with container.run(["ls", "-R", "/usr/bin"]):
                pass
            self.assertIn("cmake", container.logs)

    def test_mysql_application_build(self):
        application = Application(os.path.join(self.path, "mysql_app"), {})
        images = application.build(base_image=Image(ImageRevSpec.parse("lopter/sandbox-base:latest")))
        self.assertIsInstance(images, dict)
        self.assertEqual(len(images), 0)

    def test_broken_application_build(self):
        application = Application(os.path.join(self.path, "broken_build"), {})
        images = application.build(base_image=Image(ImageRevSpec.parse("lopter/sandbox-base:latest")))
        self.assertEqual(images, None)

    def test_python_application_build(self):
        application = Application(os.path.join(self.path, "simple_python_app"), {})
        images = application.build(base_image=Image(ImageRevSpec.parse("lopter/sandbox-base:latest")))
        self.assertIsInstance(images, dict)
        result = images.get("www")
        self.assertIsNotNone(result)

class TestService(ContainerTestCase):

    def setUp(self):
        ContainerTestCase.setUp(self)
        self.path = os.path.dirname(__file__)
        self.tmpdir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")

    def tearDown(self):
        ContainerTestCase.tearDown(self)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_allocate_custom_ports(self):
        self.application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {})
        self.service = self.application.services[0]
        self.assertDictEqual(self.service.ports, {"www": str(self.service.CUSTOM_PORTS_RANGE_START)})

        self.application = Application(os.path.join(self.path, "simple_python_app"), {})
        self.service = self.application.services[0]
        self.assertDictEqual(self.service.ports, {})

    def test_generate_environment_files(self):
        self.application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {"API_KEY": "42"})
        self.service = self.application.services[0]
        env_json, env_yml, env_profile = self.service._generate_environment_files(self.tmpdir)
        with open(env_json) as fp_json, open(env_yml) as fp_yml, open(env_profile) as fp_profile:
            env_json = json.load(fp_json)
            env_yml = yaml.safe_load(fp_yml)
            env_profile = {}
            for line in fp_profile:
                self.assertTrue(line.startswith("export "))
                key, value = line[len("export "):-1].split("=") # strip export and \n
                env_profile[key] = value
        for env in [env_json, env_yml, env_profile]:
            self.assertEqual(env.get("API_KEY"), "42")
            self.assertEqual(env.get("API_ENDPOINT"), self.service.environment["API_ENDPOINT"])
            self.assertEqual(env.get("DOTCLOUD_PROJECT"), self.application.name)
            self.assertEqual(env.get("DOTCLOUD_SERVICE_NAME"), self.service.name)
            self.assertEqual(env.get("PORT_WWW"), str(self.service.CUSTOM_PORTS_RANGE_START))

    def test_generate_service_tarball(self):
        self.application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {})
        self.service = self.application.services[0]
        application_tarball = os.path.join(self.tmpdir, "application.tar")
        with open(application_tarball, "w") as fp:
            fp.write("Test Content 42\n")
        service_tarball = self.service._generate_service_tarball(self.tmpdir, [application_tarball])
        self.assertTrue(os.path.exists(service_tarball.dest))
        with open(service_tarball.dest, "r") as fp:
            service_tarball = fp.read()
        self.assertIn("Test Content 42\n", service_tarball)
        self.assertIn("DOTCLOUD_SERVICE_NAME", service_tarball)

    def test_unpack_tarball(self):
        self.application = Application(os.path.join(self.path, "simple_gunicorn_gevent_app"), {})
        self.service = self.application.services[0]
        application_tarball = os.path.join(self.tmpdir, "application.tar")
        with open(application_tarball, "w") as fp:
            fp.write("Test Content 42\n")
        service_tarball = self.service._generate_service_tarball(self.tmpdir, [application_tarball])
        self.service._unpack_service_tarball(service_tarball.dest, self.container)
        self.assertIsNotNone(self.container.result)
        result = self.container.result.instantiate()
        with _destroy_result(result):
            with result.run(["ls", "-lFh", self.service._extract_path]):
                pass
            self.assertIn("application.tar", result.logs)
            self.assertIn("service.tar", result.logs)

########NEW FILE########
__FILENAME__ = test_tarfile
# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level="DEBUG")
import gevent
import gevent.subprocess
import os
import shutil
import subprocess
import tempfile
import unittest

from udotcloud.sandbox import tarfile

class TestTarballfile(unittest.TestCase):

    def setUp(self):
        self.path = os.path.dirname(__file__)
        self.tmpdir = tempfile.mkdtemp(prefix="udotcloud", suffix="tests")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_tar_simple_application(self):
        dest=os.path.join(self.tmpdir, "test.tar")
        tarball = tarfile.Tarball.create_from_files(
            "simple_python_app", dest=dest, root_dir=self.path
        )
        tarball.wait()
        self.assertEqual(dest, tarball.dest)
        self.assertTrue(os.path.exists(tarball.dest))

        with open("/dev/null", "w") as blackhole:
            ret = gevent.subprocess.call(
                ["tar", "-xf", tarball.dest, "-C", self.tmpdir],
                stdout=blackhole,
                stderr=subprocess.STDOUT
            )
        self.assertEqual(ret, 0)
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "simple_python_app", "dotcloud.yml"
        )))

    def test_tar_simple_application_to_fp(self):
        extract = gevent.subprocess.Popen(
            ["tar", "-xf", "-", "-C", self.tmpdir], stdin=subprocess.PIPE
        )
        tarball = tarfile.Tarball.create_from_files(
            "simple_python_app", dest=extract.stdin, root_dir=self.path
        )
        self.assertIsNotNone(tarball.dest)
        tarball.wait()
        self.assertEqual(extract.wait(), 0)

        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "simple_python_app", "dotcloud.yml"
        )))

    def test_tar_multiple_files(self):
        extract = gevent.subprocess.Popen(
            ["tar", "-xf", "-", "-C", self.tmpdir], stdin=subprocess.PIPE
        )
        tarball = tarfile.Tarball.create_from_files(
            ["simple_python_app", "custom_app"],
            dest=extract.stdin,
            root_dir=self.path
        )
        self.assertIsNotNone(tarball.dest)
        tarball.wait()
        self.assertEqual(extract.wait(), 0)

        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "simple_python_app", "dotcloud.yml"
        )))
        self.assertTrue(os.path.exists(os.path.join(
            self.tmpdir, "custom_app", "dotcloud.yml"
        )))

########NEW FILE########
__FILENAME__ = test_templates
# -*- coding: utf-8 -*-

import unittest

from udotcloud.builder.templates import TemplatesRepository

class TestTemplatesRepository(unittest.TestCase):

    def test_render(self):
        repository = TemplatesRepository()
        nginx_conf = repository.render(
            "python", "nginx.conf",
            svc_dir="/home/dotcloud/current",
            supervisor_dir="/home/dotcloud/current/supervisor"
        )
        self.assertIn("/home/dotcloud/current/", nginx_conf)

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-

import colorama
import logging
import os
import sys

SUCCESS = logging.CRITICAL + 1 # You always want to display success

class Formatter(logging.Formatter):

    def __init__(self, fmt=None, datefmt=None, arrow_style="==>"):
        logging.Formatter.__init__(self)
        self._enable_colors = os.isatty(sys.stderr.fileno())
        self._arrow_style = arrow_style
        self._color_table = {
            "DEBUG": colorama.Fore.WHITE + colorama.Style.DIM,
            "INFO": colorama.Fore.BLUE + colorama.Style.BRIGHT,
            "WARNING": colorama.Fore.YELLOW + colorama.Style.BRIGHT,
            "ERROR": colorama.Fore.RED + colorama.Style.BRIGHT,
            "CRITICAL": colorama.Fore.RED + colorama.Style.BRIGHT,
            "SUCCESS": colorama.Fore.GREEN + colorama.Style.BRIGHT
        }

    def format(self, record):
        if self._enable_colors:
            s = "{0}{1}{2} ".format(
                self._color_table.get(record.levelname),
                self._arrow_style,
                colorama.Style.RESET_ALL
            )
        else:
            s = "{0} ".format(self._arrow_style)
        return s + logging.Formatter.format(self, record)


def log_success(msg, *args, **kwargs):
    logging.log(SUCCESS, msg, *args, **kwargs)

def configure_logging(arrow_style, level="DEBUG"):
    logging.addLevelName(SUCCESS, "SUCCESS")
    stderr_format = Formatter(arrow_style=arrow_style)
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(stderr_format)
    root_logger = logging.getLogger()
    root_logger.addHandler(stderr_handler)
    root_logger.setLevel(level)

########NEW FILE########
