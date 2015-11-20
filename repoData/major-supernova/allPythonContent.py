__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# supernova documentation build configuration file, created by
# sphinx-quickstart on Tue May  6 00:28:18 2014.
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
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'supernova'
copyright = u'2014, Major Hayden'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = 'trunk'
# The full version, including alpha/beta/rc tags.
release = 'trunk'

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
htmlhelp_basename = 'supernovadoc'


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
  ('index', 'supernova.tex', u'supernova Documentation',
   u'Major Hayden', 'manual'),
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
    ('index', 'supernova', u'supernova Documentation',
     [u'Major Hayden'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'supernova', u'supernova Documentation',
   u'Major Hayden', 'supernova', 'One line description of project.',
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
__FILENAME__ = colors
#!/usr/bin/env python
#
# Copyright 2014 Major Hayden
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
A little color in the terminal never hurt anybody (I think)
"""


def gwrap(some_string):
    """
    Returns green text
    """
    return "\033[92m%s\033[0m" % some_string


def rwrap(some_string):
    """
    Returns red text
    """
    return "\033[91m%s\033[0m" % some_string

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
#
# Copyright 2014 Major Hayden
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
Takes care of the basic setup of the config files and does some preliminary
sanity checks
"""
try:
    import ConfigParser
except:
    import configparser as ConfigParser

import os
import sys

from . import colors

nova_creds = None


def run_config():
    """
    Runs sanity checks and prepares the global nova_creds variable
    """
    global nova_creds
    check_environment_presets()
    nova_creds = load_supernova_config()


def check_environment_presets():
    """
    Checks for environment variables that can cause problems with supernova
    """
    presets = [x for x in os.environ.copy().keys() if x.startswith('NOVA_') or
               x.startswith('OS_')]
    if len(presets) < 1:
        return True
    else:
        print("_" * 80)
        print("*WARNING* Found existing environment variables that may ",
              "cause conflicts:")
        for preset in presets:
            print("  - %s" % preset)
        print("_" * 80)
        return False


def load_supernova_config():
    """
    Pulls the supernova configuration file and reads it
    """
    xdg_config_home = os.environ.get('XDG_CONFIG_HOME') or \
        os.path.expanduser('~/.config')
    possible_configs = [os.path.join(xdg_config_home, "supernova"),
                        os.path.expanduser("~/.supernova"),
                        ".supernova"]
    supernova_config = ConfigParser.RawConfigParser()

    # Can we successfully read the configuration file?
    try:
        supernova_config.read(possible_configs)
    except:
        msg = """
[%s] A valid supernova configuration file is required.
Ensure that you have a properly configured supernova configuration file called
'.supernova' in your home directory or in your current working directory.
""" % colors.rwrap('Invalid configuration file')
        print(msg)
        sys.exit(1)

    return supernova_config

########NEW FILE########
__FILENAME__ = credentials
#!/usr/bin/env python
#
# Copyright 2014 Major Hayden
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
Handles all of the interactions with the operating system's keyring
"""
from __future__ import print_function

import getpass
import keyring
import re
import sys

try:
    def _input(a):
        input(a)
except:
    def _input(a):
        raw_input(a)


from . import colors


def get_user_password(args):
    """
    Allows the user to print the credential for a particular keyring entry
    to the screen
    """
    username = '%s:%s' % (args.env, args.parameter)

    warnstring = colors.rwrap("__ WARNING ".ljust(80, '_'))
    print("""
%s

If this operation is successful, the credential stored for this username will
be displayed in your terminal as PLAIN TEXT:

  %s

Seriously.  It will just be hanging out there for anyone to see.  If you have
any concerns about having this credential displayed on your screen, press
CTRL-C right now.

%s
""" % (warnstring, username, warnstring))
    print("If you are completely sure you want to display it, type 'yes' and ",
          "press enter:")
    try:
        confirm = _input('')
    except:
        print("")
        sys.exit()

    if confirm != 'yes':
        print("\n[%s] Your keyring was not read or altered." % (
            colors.rwrap("Canceled")))
        return False

    try:
        password = password_get(username)
    except:
        password = None

    if password:
        print("""
[%s] Found credentials for %s: %s
""" % (
            colors.gwrap("Success"), username, password))
        return True
    else:
        print("""
[%s] Unable to retrieve credentials for %s.

It's likely that there aren't any credentials stored for this environment and
parameter combination.  If you want to set a credential, just run this command:

  supernova-keyring -s %s %s
""" % (colors.rwrap("Failed"), username, args.env, args.parameter))
        return False


def pull_env_credential(env, param, value):
    """
    Dissects a keyring credential lookup string from the supernova config file
    and returns the username/password combo
    """
    rex = "USE_KEYRING\[([\x27\x22])(.*)\\1\]"
    if value == "USE_KEYRING":
        username = "%s:%s" % (env, param)
    else:
        global_identifier = re.match(rex, value).group(2)
        username = "%s:%s" % ('global', global_identifier)
    return (username, password_get(username))


def password_get(username=None):
    """
    Retrieves a password from the keychain based on the environment and
    configuration parameter pair.
    """
    try:
        return keyring.get_password('supernova', username).encode('ascii')
    except:
        return False


def set_user_password(args):
    """
    Sets a user's password in the keyring storage
    """
    print("""
[%s] Preparing to set a password in the keyring for:

  - Environment  : %s
  - Parameter    : %s

If this is correct, enter the corresponding credential to store in your keyring
or press CTRL-D to abort:""" % (colors.gwrap("Keyring operation"), args.env,
                                args.parameter))

    # Prompt for a password and catch a CTRL-D
    try:
        password = getpass.getpass('')
    except:
        password = None
        print()

    # Did we get a password from the prompt?
    if not password or len(password) < 1:
        print("\n[%s] No data was altered in your keyring.\n" % (
            colors.rwrap("Canceled")))
        sys.exit()

    # Try to store the password
    username = '%s:%s' % (args.env, args.parameter)
    try:
        store_ok = password_set(username, password)
    except:
        store_ok = False

    if store_ok:
        msg = ("[%s] Successfully stored credentials for %s under the "
               "supernova service.\n")
        print(msg % (colors.gwrap("Success"), username))
    else:
        msg = ("[%s] Unable to store credentials for %s under the "
               "supernova service.\n")
        print(msg % (colors.rwrap("Failed"), username))


def password_set(username=None, password=None):
    """
    Stores a password in a keychain for a particular environment and
    configuration parameter pair.
    """
    try:
        keyring.set_password('supernova', username, password)
        return True
    except:
        return False

########NEW FILE########
__FILENAME__ = executable
#!/usr/bin/env python
#
# Copyright 2014 Major Hayden
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
Contains the functions needed for supernova and supernova-keyring commands
to run
"""
from __future__ import print_function

import argparse
import sys


from . import colors
from . import config
from . import credentials
from . import utils
from . import supernova


# Note(tr3buchet): this is necessary to prevent argparse from requiring the
#                  the 'env' parameter when using -l or --list
class _ListAction(argparse._HelpAction):
    """ListAction used for the -l and --list arguments."""
    def __call__(self, parser, *args, **kwargs):
        """Lists are configured supernova environments."""
        for nova_env in config.nova_creds.sections():
            envheader = '-- %s ' % colors.gwrap(nova_env)
            print(envheader.ljust(86, '-'))
            for param, value in sorted(config.nova_creds.items(nova_env)):
                print('  %s: %s' % (param.upper().ljust(21), value))
        parser.exit()


def run_supernova():
    """
    Handles all of the prep work and error checking for the
    supernova executable.
    """
    config.run_config()

    parser = argparse.ArgumentParser()
    parser.add_argument('-x', '--executable', default='nova',
                        help='command to run instead of nova')
    parser.add_argument('-l', '--list', action=_ListAction,
                        help='list all configured environments')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='show novaclient debug output')
    parser.add_argument('env',
                        help=('environment to run nova against. '
                              'valid options: %s' %
                              sorted(config.nova_creds.sections())))

    # Allow for passing --options all the way through to novaclient
    supernova_args, nova_args = parser.parse_known_args()

    # Did we get any arguments to pass on to nova?
    if not nova_args:
        utils.warn_missing_nova_args()
        sys.exit(1)

    # Is our environment argument a single environment or a supernova group?
    if utils.is_valid_group(supernova_args.env):
        envs = utils.get_envs_in_group(supernova_args.env)
    else:
        envs = [supernova_args.env]

    for env in envs:
        snobj = supernova.SuperNova()
        snobj.nova_env = env
        snobj.run_novaclient(nova_args, supernova_args)


def run_supernova_keyring():
    """
    Handles all of the prep work and error checking for the
    supernova-keyring executable.
    """
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-g', '--get', action='store_true',
                       dest='get_password',
                       help='retrieves credentials from keychain storage')
    group.add_argument('-s', '--set', action='store_true',
                       dest='set_password',
                       help='stores credentials in keychain storage')
    parser.add_argument('env',
                        help='environment to set parameter in')
    parser.add_argument('parameter',
                        help='parameter to set')
    args = parser.parse_args()

    if args.set_password:
        credentials.set_user_password(args)

    if args.get_password:
        credentials.get_user_password(args)

########NEW FILE########
__FILENAME__ = supernova
#!/usr/bin/env python
#
# Copyright 2014 Major Hayden
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
Contains the actual class that runs novaclient (or the executable chosen by
the user)
"""
from __future__ import print_function


from novaclient import client as novaclient
import os
import re
import subprocess
import sys


from . import colors
from . import utils
from . import config
from . import credentials


class SuperNova(object):
    """
    Gathers information for novaclient and eventually runs it
    """

    def __init__(self):
        config.run_config()
        self.nova_env = None
        self.env = os.environ.copy()

    def prep_nova_creds(self):
        """
        Finds relevant config options in the supernova config and cleans them
        up for novaclient.
        """
        raw_creds = config.nova_creds.items(self.nova_env)
        nova_re = re.compile(r"(^nova_|^os_|^novaclient|^trove_)")

        creds = []
        for param, value in raw_creds:

            # Skip parameters we're unfamiliar with
            if not nova_re.match(param):
                continue

            param = param.upper()

            # Get values from the keyring if we find a USE_KEYRING constant
            if value.startswith("USE_KEYRING"):
                username, credential = credentials.pull_env_credential(
                    self.nova_env, param, value)
            else:
                credential = value.strip("\"'")

            # Make sure we got something valid from the configuration file or
            # the keyring
            if not credential:
                msg = """
While connecting to %s, supernova attempted to retrieve a credential
for %s but couldn't find it within the keyring.  If you haven't stored
credentials for %s yet, try running:

    supernova-keyring -s %s
""" % (self.nova_env, username, username, ' '.join(username.split(':')))
                print(msg)
                sys.exit(1)

            creds.append((param, credential))

        return creds

    def prep_shell_environment(self):
        """
        Appends new variables to the current shell environment temporarily.
        """
        for key, value in self.prep_nova_creds():
            self.env[key] = value

    def run_novaclient(self, nova_args, supernova_args):
        """
        Sets the environment variables for novaclient, runs novaclient, and
        prints the output.
        """
        # Get the environment variables ready
        self.prep_shell_environment()

        # Check for a debug override
        if supernova_args.debug:
            nova_args.insert(0, '--debug')

        # Check for OS_EXECUTABLE
        try:
            if self.env['OS_EXECUTABLE']:
                supernova_args.executable = self.env['OS_EXECUTABLE']
        except KeyError:
            pass

        # Print a small message for the user (very helpful for groups)
        msg = "Running %s against %s..." % (supernova_args.executable,
                                            self.nova_env)
        print("[%s] %s " % (colors.gwrap('SUPERNOVA'), msg))

        # Call novaclient and connect stdout/stderr to the current terminal
        # so that any unicode characters from novaclient's list will be
        # displayed appropriately.
        #
        # In other news, I hate how python 2.6 does unicode.
        process = subprocess.Popen([supernova_args.executable] + nova_args,
                                   stdout=sys.stdout,
                                   stderr=sys.stderr,
                                   env=self.env)

        # Don't exit until we're sure the subprocess has exited
        return process.wait()

    def get_novaclient(self, env, client_version=3):
        """
        Returns python novaclient object authenticated with supernova config.
        """
        self.nova_env = env
        assert utils.is_valid_environment(env), "Env %s not found in "\
            "supernova configuration file." % env
        print("Getting novaclient!")
        return novaclient.Client(client_version, **self.prep_python_creds())

    def prep_python_creds(self):
        """
        Prepare credentials for python Client instantiation.
        """
        creds = dict((utils.rm_prefix(k[0].lower()), k[1])
                     for k in self.prep_nova_creds())
        if creds.get('url'):
            creds['auth_url'] = creds.pop('url')
        if creds.get('tenant_name'):
            creds['project_id'] = creds.pop('tenant_name')
        return creds

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#
# Copyright 2014 Major Hayden
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
"""
Contains many of the shared utility functions
"""
from __future__ import print_function

from . import colors
from . import config


def check_deprecated_options(self):
    """
    Hunts for deprecated configuration options from previous SuperNova
    versions.
    """
    creds = config.nova_creds
    if creds.has_option(self.nova_env, 'insecure'):
        print("WARNING: the 'insecure' option is deprecated. ",
              "Consider using NOVACLIENT_INSECURE=1 instead.")


def get_envs_in_group(group_name):
    """
    Takes a group_name and finds any environments that have a SUPERNOVA_GROUP
    configuration line that matches the group_name.
    """
    envs = []
    for section in config.nova_creds.sections():
        if (config.nova_creds.has_option(section, 'SUPERNOVA_GROUP') and
                config.nova_creds.get(section,
                                      'SUPERNOVA_GROUP') == group_name):
            envs.append(section)
    return envs


def is_valid_environment(env):
    """
    Checks to see if the configuration file contains a section for our
    requested environment.
    """
    valid_envs = config.nova_creds.sections()
    return env in valid_envs


def is_valid_group(group_name):
    """
    Checks to see if the configuration file contains a SUPERNOVA_GROUP
    configuration option.
    """
    valid_groups = []
    for section in config.nova_creds.sections():
        if config.nova_creds.has_option(section, 'SUPERNOVA_GROUP'):
            valid_groups.append(config.nova_creds.get(section,
                                                      'SUPERNOVA_GROUP'))
    valid_groups = list(set(valid_groups))
    if group_name in valid_groups:
        return True
    else:
        return False


def print_valid_envs(valid_envs):
    """
    Prints the available environments.
    """
    print("[%s] Your valid environments are:" %
          (colors.gwrap('Found environments')))
    print("%r" % valid_envs)


def warn_missing_nova_args():
    """
    Provides a friendly warning for users who forget to provide commands to
    be passed on to nova.
    """
    msg = """
[%s] No arguments were provided to pass along to nova.
The supernova script expects to get commands structured like this:

  supernova [environment] [command]

Here are some example commands that may help you get started:

  supernova prod list
  supernova prod image-list
  supernova prod keypair-list
"""
    print(msg % colors.rwrap('Missing arguments'))


def rm_prefix(name):
    """
    Removes nova_ os_ novaclient_ prefix from string.
    """
    if name.startswith('nova_'):
        return name[5:]
    elif name.startswith('novaclient_'):
        return name[11:]
    elif name.startswith('os_'):
        return name[3:]
    else:
        return name

########NEW FILE########